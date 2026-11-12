# Ethereum transaction experiments

Tested on Linux x86_64 with Foundry (anvil / cast) 1.7.1 and Python 3.14.
Put anvil and cast on PATH, then:

  python3 run.py            # -> output/results.json, output/log.txt
  python3 fetch_deversifi.py  # -> output/deversifi.json (read-only, one public RPC call set)

run.py starts its own Anvil on 127.0.0.1:18651 and stops it at the end. It uses
only Anvil's built-in development keys (publicly known values) and no public
network or real funds. It records:

- tamper: a signed type-2 transfer, three same-length rewrites (value, to, chainId;
  to and chainId change 1 byte, value changes 6 of its 8 bytes),
  the signer recovered by `cast decode-transaction`, and the node's answer.
  The rewritten-value transaction is then sent again after funding the recovered
  address with anvil_setBalance.
- fee: base fee pinned to 10 gwei (anvil_setNextBlockBaseFeePerGas), maxFeePerGas
  100 gwei, maxPriorityFeePerGas 1 / 50 / 100 gwei.
- reserve: balance 1.001 ETH, value 1 ETH, three (gasLimit, maxFeePerGas) pairs.
- revert: a call to a contract whose code is PUSH1 0 PUSH1 0 REVERT.

fetch_deversifi.py reads transaction
0x2c9931793876db33b1a9aad123ad4921dfb9cd5e59dbb78ce78f277759587115
(block 13307440, 2021-09-27) from https://eth.drpc.org. It sends nothing.

../figures.py draws the note's figures from output/.
