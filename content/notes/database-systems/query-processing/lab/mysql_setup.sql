-- Query Processing のノートの実験で使う表（MySQL 8.4、InnoDB）
-- PostgreSQL の events と同じ行を作り、id と同じ値の列 seq に別の索引を付ける。
CREATE DATABASE IF NOT EXISTS lab;
USE lab;
DROP TABLE IF EXISTS events, digits;
CREATE TABLE digits (d int);
INSERT INTO digits VALUES (0),(1),(2),(3),(4),(5),(6),(7),(8),(9);
CREATE TABLE events (id bigint PRIMARY KEY, user_id int NOT NULL, seq bigint, payload varchar(8));
INSERT INTO events
SELECT n, IF(n > 4990000, 1, 2 + (n % 1000)), n, 'x' FROM (
  SELECT 1 + a.d + 10*b.d + 100*c.d + 1000*e.d + 10000*f.d + 100000*g.d + 1000000*h.d AS n
  FROM digits a, digits b, digits c, digits e, digits f, digits g, digits h
) s WHERE n <= 5000000;
CREATE INDEX events_user_id_idx ON events (user_id);
CREATE INDEX events_seq_idx ON events (seq);
ANALYZE TABLE events;
