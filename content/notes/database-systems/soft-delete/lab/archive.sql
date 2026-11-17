-- 退会から 1 年を過ぎた会員をアーカイブの表へ移す
\set VERBOSITY terse
CREATE TABLE members (id int PRIMARY KEY, email text NOT NULL, deleted_at timestamptz);
CREATE TABLE members_archive (LIKE members INCLUDING ALL);
INSERT INTO members VALUES
  (1, 'a@example.com', now() - interval '2 years'),
  (2, 'b@example.com', now() - interval '1 month'),
  (3, 'c@example.com', NULL);

BEGIN;
INSERT INTO members_archive
  SELECT * FROM members WHERE deleted_at < now() - interval '1 year';
DELETE FROM members WHERE deleted_at < now() - interval '1 year';
COMMIT;

SELECT 'members' AS t, id FROM members UNION ALL SELECT 'members_archive', id FROM members_archive ORDER BY 1, 2;
