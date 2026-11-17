-- MySQL には WHERE 付きの索引が無い。同じ確かめ方を MySQL 8.4 で行う
CREATE DATABASE IF NOT EXISTS lab; USE lab;
SELECT '== (1) UNIQUE (email)' AS '';
CREATE TABLE m1 (id int PRIMARY KEY, email varchar(100) NOT NULL, deleted_at datetime NULL, UNIQUE (email));
INSERT INTO m1 VALUES (1, 'a@example.com', now());
INSERT INTO m1 VALUES (2, 'a@example.com', NULL);
INSERT INTO m1 VALUES (3, 'b@example.com', NULL), (4, 'b@example.com', NULL);

SELECT '== (2) UNIQUE (email, deleted_at)' AS '';
CREATE TABLE m2 (id int PRIMARY KEY, email varchar(100) NOT NULL, deleted_at datetime NULL, UNIQUE (email, deleted_at));
INSERT INTO m2 VALUES (1, 'a@example.com', now());
INSERT INTO m2 VALUES (2, 'a@example.com', NULL);
INSERT INTO m2 VALUES (3, 'b@example.com', NULL), (4, 'b@example.com', NULL);
SELECT count(*) AS active_b FROM m2 WHERE email = 'b@example.com' AND deleted_at IS NULL;

SELECT '== (3) 退会済みなら NULL を返す式に一意索引（functional key part）' AS '';
CREATE TABLE m3 (id int PRIMARY KEY, email varchar(100) NOT NULL, deleted_at datetime NULL,
                 UNIQUE KEY email_active ((IF(deleted_at IS NULL, email, NULL))));
INSERT INTO m3 VALUES (1, 'a@example.com', now());
INSERT INTO m3 VALUES (2, 'a@example.com', NULL);
INSERT INTO m3 VALUES (3, 'b@example.com', NULL), (4, 'b@example.com', NULL);
