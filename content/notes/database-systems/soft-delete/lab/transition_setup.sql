DROP TABLE IF EXISTS member_status_changes, members;
CREATE TABLE members (
  id     int PRIMARY KEY,
  status text NOT NULL CHECK (status IN ('仮登録', '有効', '一時停止', '失効', '退会済み', '強制退会'))
);
CREATE TABLE member_status_changes (
  id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  member_id   int  NOT NULL REFERENCES members (id),
  from_status text,
  to_status   text NOT NULL,
  reason      text,
  changed_by  int,
  changed_at  timestamptz NOT NULL DEFAULT clock_timestamp()
);
INSERT INTO members VALUES (1, '有効');
