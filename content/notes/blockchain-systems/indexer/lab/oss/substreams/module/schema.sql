CREATE TABLE IF NOT EXISTS transfers (
  id         TEXT PRIMARY KEY,
  block_num  BIGINT NOT NULL,
  block_hash TEXT NOT NULL,
  from_addr  TEXT NOT NULL,
  to_addr    TEXT NOT NULL,
  amount     NUMERIC NOT NULL
);
