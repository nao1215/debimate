import {EvmBatchProcessor} from '@subsquid/evm-processor'
import {TypeormDatabase} from '@subsquid/typeorm-store'
import {Balance} from './model'

// Anvil の JSON-RPC だけを源にする（SQD Network / Portal は使わない）。
const TOKEN = '0x5fbdb2315678afecb367f032d93f642f64180aa3'
const TRANSFER = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
const ZERO = '0x0000000000000000000000000000000000000000'

const processor = new EvmBatchProcessor()
    .setRpcEndpoint({url: process.env.RPC_URL!, rateLimit: 100})
    .setRpcDataIngestionSettings({headPollInterval: 500})
    .setFinalityConfirmation(Number(process.env.FINALITY ?? '10'))
    .setPrometheusPort(Number(process.env.METRICS_PORT ?? '18852'))
    .setBlockRange({from: 0})
    .addLog({address: [TOKEN], topic0: [TRANSFER]})
    .setFields({log: {topics: true, data: true}})

processor.run(new TypeormDatabase({supportHotBlocks: true}), async (ctx) => {
    const deltas = new Map<string, bigint>()
    const add = (a: string, v: bigint) => deltas.set(a, (deltas.get(a) ?? 0n) + v)
    for (const block of ctx.blocks) {
        for (const log of block.logs) {
            if (log.address !== TOKEN || log.topics[0] !== TRANSFER) continue
            const from = '0x' + log.topics[1].slice(26)
            const to = '0x' + log.topics[2].slice(26)
            const value = BigInt(log.data)
            if (from !== ZERO) add(from, -value)
            add(to, value)
        }
    }
    if (deltas.size === 0) return
    const ids = [...deltas.keys()]
    const rows = await ctx.store.findBy(Balance, ids.map(id => ({id})) as any)
    const cur = new Map(rows.map(r => [r.id, r]))
    const out: Balance[] = []
    for (const [id, d] of deltas) {
        const b = cur.get(id) ?? new Balance({id, amount: 0n})
        b.amount += d
        out.push(b)
    }
    await ctx.store.upsert(out)
    const last = ctx.blocks[ctx.blocks.length - 1].header
    ctx.log.info(`handled blocks ${ctx.blocks[0].header.height}..${last.height}, ${deltas.size} addresses`)
})
