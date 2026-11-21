import { ponder } from "ponder:registry";
import { balance } from "ponder:schema";

const ZERO = "0x0000000000000000000000000000000000000000";

ponder.on("Token:Transfer", async ({ event, context }) => {
  const { from, to, value } = event.args;
  if (from !== ZERO) {
    await context.db.insert(balance).values({ address: from, amount: -value })
      .onConflictDoUpdate((row) => ({ amount: row.amount - value }));
  }
  await context.db.insert(balance).values({ address: to, amount: value })
    .onConflictDoUpdate((row) => ({ amount: row.amount + value }));
});
