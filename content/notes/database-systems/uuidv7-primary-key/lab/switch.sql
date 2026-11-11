\set ON_ERROR_STOP on
-- UUIDv4 で 100 万件を入れた表を、途中から UUIDv7 に切り替える
CREATE EXTENSION pgstattuple;
CREATE TABLE t (id uuid DEFAULT uuidv4() PRIMARY KEY, body text NOT NULL);
INSERT INTO t (body) SELECT md5(i::text) FROM generate_series(1, 1000000) AS i;
SELECT leaf_pages, avg_leaf_density FROM pgstatindex('t_pkey');               -- v4 だけの時

ALTER TABLE t ALTER COLUMN id SET DEFAULT uuidv7();
INSERT INTO t (body) SELECT md5(i::text) FROM generate_series(1, 200000) AS i;
SELECT leaf_pages, avg_leaf_density FROM pgstatindex('t_pkey');               -- v7 で 20 万件を足した後

DELETE FROM t WHERE uuid_extract_version(id) = 4;
VACUUM t;
SELECT leaf_pages, avg_leaf_density FROM pgstatindex('t_pkey');               -- v4 の行を消して VACUUM した後

REINDEX INDEX t_pkey;
SELECT leaf_pages, avg_leaf_density FROM pgstatindex('t_pkey');               -- 作り直した後
