-- 削除フラグを置かず、DELETE した行を別の表に JSON で残す
\set ON_ERROR_STOP 0
\set VERBOSITY terse
CREATE TABLE deleted_record (
  id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  table_name text  NOT NULL,
  object_id  int   NOT NULL,
  data       jsonb NOT NULL,
  deleted_at timestamptz NOT NULL DEFAULT now()
);
CREATE FUNCTION deleted_record_insert() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  INSERT INTO deleted_record (table_name, object_id, data)
  VALUES (TG_TABLE_NAME, OLD.id, to_jsonb(OLD.*));
  RETURN OLD;
END;
$$;

CREATE TABLE products (id int PRIMARY KEY, name text NOT NULL);
CREATE TABLE reservations (id int PRIMARY KEY, product_id int NOT NULL REFERENCES products (id));
CREATE TRIGGER keep AFTER DELETE ON reservations
  FOR EACH ROW EXECUTE FUNCTION deleted_record_insert();
INSERT INTO products VALUES (1, 'カメラ'), (2, '三脚'), (3, 'レンズ');
INSERT INTO reservations VALUES (10, 2), (11, 3);

\echo '-- レンズの予約を取り消す（DELETE）'
DELETE FROM reservations WHERE id = 11;

\echo '-- 冒頭の (A) から deleted_at の条件を外しただけの SQL'
SELECT p.name, count(r.id) AS active_count
FROM products p
LEFT JOIN reservations r ON r.product_id = p.id
GROUP BY p.id, p.name
ORDER BY p.id;

\echo '-- 取り消した予約は deleted_record に残る'
SELECT table_name, object_id, data FROM deleted_record;

\echo '-- 戻す'
INSERT INTO reservations
SELECT * FROM jsonb_populate_record(NULL::reservations,
  (SELECT data FROM deleted_record WHERE table_name = 'reservations' AND object_id = 11));
SELECT * FROM reservations ORDER BY id;

\echo '-- 予約のある商品は消せない（外部キーが効く）'
DELETE FROM products WHERE id = 2;
