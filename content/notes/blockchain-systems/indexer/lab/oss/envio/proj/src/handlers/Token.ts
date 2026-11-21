import { indexer } from "envio";

const ZERO = "0x0000000000000000000000000000000000000000";

indexer.onEvent({ contract: "Token", event: "Transfer" }, async ({ event, context }) => {
  const { from, to, value } = event.params;
  if (from.toLowerCase() !== ZERO) {
    const b = await context.Balance.get(from.toLowerCase());
    context.Balance.set({ id: from.toLowerCase(), amount: (b?.amount ?? 0n) - value });
  }
  const r = await context.Balance.get(to.toLowerCase());
  context.Balance.set({ id: to.toLowerCase(), amount: (r?.amount ?? 0n) + value });
});
