import { Address, BigInt, Bytes } from "@graphprotocol/graph-ts"
import { Transfer as TransferEvent } from "../generated/Token/Token"
import { Balance, Transfer } from "../generated/schema"

function add(addr: Address, delta: BigInt): void {
  let b = Balance.load(addr)
  if (b == null) {
    b = new Balance(addr)
    b.amount = BigInt.zero()
  }
  b.amount = b.amount.plus(delta)
  b.save()
}

export function handleTransfer(e: TransferEvent): void {
  let t = new Transfer(e.transaction.hash.concatI32(e.logIndex.toI32()))
  t.from = e.params.from
  t.to = e.params.to
  t.value = e.params.value
  t.blockNumber = e.block.number
  t.save()
  if (e.params.from != Address.zero()) {
    add(e.params.from, e.params.value.neg())
  }
  add(e.params.to, e.params.value)
}
