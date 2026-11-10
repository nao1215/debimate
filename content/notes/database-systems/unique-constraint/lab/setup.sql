-- 一意制約の無い表と、ある表。どちらも email に索引を張り、検索の速さをそろえる。
DROP TABLE IF EXISTS users_plain, users_unique, violations;
CREATE TABLE users_plain  (id bigserial PRIMARY KEY, email text NOT NULL);
CREATE INDEX ON users_plain (email);
CREATE TABLE users_unique (id bigserial PRIMARY KEY, email text NOT NULL UNIQUE);
-- 一意制約違反（23505）を受け取った回数を記録する。
CREATE TABLE violations (email text NOT NULL);

-- 2 つの表に同じ形の関数で INSERT する。unique 側は 23505 を受け取って記録する。
CREATE OR REPLACE FUNCTION register_plain(e text) RETURNS void AS $$
BEGIN
  INSERT INTO users_plain (email) VALUES (e);
EXCEPTION WHEN unique_violation THEN
  INSERT INTO violations VALUES (e);
END $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION register_unique(e text) RETURNS void AS $$
BEGIN
  INSERT INTO users_unique (email) VALUES (e);
EXCEPTION WHEN unique_violation THEN
  INSERT INTO violations VALUES (e);
END $$ LANGUAGE plpgsql;
