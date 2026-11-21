import { onchainTable } from "ponder";

export const balance = onchainTable("balance", (t) => ({
  address: t.hex().primaryKey(),
  amount: t.bigint().notNull(),
}));
