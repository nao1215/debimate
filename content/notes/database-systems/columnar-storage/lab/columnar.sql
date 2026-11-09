-- Columnar Storage のローカル実験（DuckDB CLI で実行する）
-- 作業ディレクトリに約 318 MB のファイルを書き出す。

-- 1. 400 万行の売上データを作る（乱数を使わず hash() で値を散らすので、毎回同じ表になる）
CREATE TABLE sales AS
SELECT
  i AS id,
  TIMESTAMP '2026-01-01' + to_seconds(i * 6) AS ts,
  (['tokyo','osaka','nagoya','fukuoka','sapporo','sendai','hiroshima','naha'])[1 + (hash(i) % 8)::INT] AS region,
  (['paid','paid','paid','refunded','cancelled'])[1 + (hash(i * 7) % 5)::INT] AS status,
  (1 + hash(i * 13) % 10000)::INTEGER AS amount
FROM range(4000000) t(i);

-- 2. 同じ表を CSV と Parquet に書き出す。shuffled は行の順序だけを崩したもの
COPY sales TO 'sales.csv' (HEADER);
COPY sales TO 'sales.parquet' (FORMAT parquet, PARQUET_VERSION v2);
COPY sales TO 'sales_v1.parquet' (FORMAT parquet);  -- 既定の設定（V1）との比較用
COPY (FROM sales ORDER BY hash(id)) TO 'sales_shuffled.parquet' (FORMAT parquet, PARQUET_VERSION v2);
COPY (FROM sales ORDER BY region, id) TO 'sales_by_region.parquet' (FORMAT parquet, PARQUET_VERSION v2);

SELECT filename AS file, size AS bytes FROM read_blob('sales*') ORDER BY size DESC;

-- 3. 列ごとのエンコードと圧縮後の大きさ（33 個の row group の合計）
SELECT path_in_schema AS col, encodings, sum(total_compressed_size) AS bytes
FROM parquet_metadata('sales.parquet') GROUP BY ALL ORDER BY bytes DESC;

SELECT path_in_schema AS col, sum(total_compressed_size) AS shuffled_bytes
FROM parquet_metadata('sales_shuffled.parquet') GROUP BY ALL ORDER BY shuffled_bytes DESC;

SELECT path_in_schema AS col, sum(total_compressed_size) AS by_region_bytes
FROM parquet_metadata('sales_by_region.parquet') GROUP BY ALL ORDER BY by_region_bytes DESC;

-- 4. ts 列の row group ごとの min/max（先頭 3 個）
SELECT row_group_id, row_group_num_rows AS num_rows, stats_min, stats_max
FROM parquet_metadata('sales.parquet') WHERE path_in_schema = 'ts' ORDER BY row_group_id LIMIT 3;

-- 5. クエリごとに、ファイルから読んだバイト数と、触れた row group を数える
CREATE TABLE io (label VARCHAR, path VARCHAR, pos BIGINT, bytes BIGINT);
CREATE MACRO reads() AS TABLE
  SELECT parse_filename(message::JSON->>'path') AS path,
         (message::JSON->>'pos')::BIGINT AS pos,
         (message::JSON->>'bytes')::BIGINT AS bytes
  FROM duckdb_logs WHERE message::JSON->>'op' = 'READ';
-- 計測中のクエリ結果は表示しない（.mode trash）
.mode trash
-- v1.5 は外部ファイルのキャッシュが既定で有効で、2 回目以降の読み込みがログに出ないため無効にする
SET enable_external_file_cache = false;
CALL enable_logging('FileSystem', storage = 'memory');

CALL truncate_duckdb_logs();
SELECT sum(amount) FROM 'sales.csv';
INSERT INTO io SELECT 'A csv: sum(amount)', * FROM reads();

CALL truncate_duckdb_logs();
SELECT sum(amount) FROM 'sales.parquet';
INSERT INTO io SELECT 'B parquet: sum(amount)', * FROM reads();

CALL truncate_duckdb_logs();
SELECT sum(amount) FROM 'sales.parquet'
WHERE ts >= TIMESTAMP '2026-03-01' AND ts < TIMESTAMP '2026-03-02';
INSERT INTO io SELECT 'C parquet: 1 day', * FROM reads();

CALL truncate_duckdb_logs();
SELECT sum(amount) FROM 'sales_shuffled.parquet'
WHERE ts >= TIMESTAMP '2026-03-01' AND ts < TIMESTAMP '2026-03-02';
INSERT INTO io SELECT 'D shuffled: 1 day', * FROM reads();

CALL truncate_duckdb_logs();
SELECT * FROM 'sales.parquet' WHERE id = 2000000;
INSERT INTO io SELECT 'E parquet: id = 2000000', * FROM reads();

CALL disable_logging();
.mode duckbox

-- 読んだ位置を、parquet_metadata の列チャンク（row group × 列）の範囲に当てはめる
CREATE TABLE chunks AS
SELECT parse_filename(file_name) AS path, row_group_id, path_in_schema AS col,
       coalesce(dictionary_page_offset, data_page_offset) AS start_pos,
       coalesce(dictionary_page_offset, data_page_offset) + total_compressed_size AS end_pos
FROM parquet_metadata('sales*.parquet');

SELECT io.label,
       sum(io.bytes) AS bytes_read,
       count(DISTINCT c.row_group_id) AS row_groups,
       string_agg(DISTINCT c.col, ',' ORDER BY c.col) AS cols
FROM io LEFT JOIN chunks c
  ON io.path = c.path AND io.pos >= c.start_pos AND io.pos < c.end_pos
GROUP BY io.label ORDER BY io.label;

-- 6. 実行計画: 列の絞り込み（Projections）と条件（Filters）が PARQUET_SCAN に入っているか
EXPLAIN ANALYZE
SELECT sum(amount) FROM 'sales.parquet'
WHERE ts >= TIMESTAMP '2026-03-01' AND ts < TIMESTAMP '2026-03-02';

-- 7. 経過時間（環境で変わる。2 回目以降の値を見る）
.timer on
SELECT sum(amount) FROM 'sales.csv';
SELECT sum(amount) FROM 'sales.csv';
SELECT sum(amount) FROM 'sales.parquet';
SELECT sum(amount) FROM 'sales.parquet';
.timer off
