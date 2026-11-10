Mainnet / testnet identification experiments (local only)

Nothing here connects to a public network. Every node runs in a Docker
container started with --network none, and no port is published.
output/ is overwritten by each run.

1. eth_replay.py  (Python 3 standard library + Docker)
   Image: ghcr.io/foundry-rs/foundry:v1.7.1 (anvil, cast), pinned by digest.
   Starts two Anvil nodes with chain ID 1 and 11155111 (the same numbers as
   Ethereum mainnet and Sepolia; they are still empty local chains).
   - reads eth_chainId, net_version and the code at the mainnet USDC address
   - signs an EIP-1559 transfer for chain 1 and sends the same bytes to both
   - signs a pre-EIP-155 legacy transfer (6 fields, v = 27/28) with
     `cast wallet sign --no-hash` and sends the same bytes to both
   The key is Anvil's first default key. It is public: never use it with
   real funds.
   Run: python3 -I eth_replay.py   -> output/eth_replay.txt

2. btc_networks.py  (Python 3 standard library + Docker)
   Binaries: Bitcoin Core 32.1 release from
     https://bitcoincore.org/bin/bitcoin-core-32.1/
   Download bitcoin-32.1-x86_64-linux-gnu.tar.gz and SHA256SUMS, then
     grep x86_64-linux-gnu.tar.gz SHA256SUMS | sha256sum -c
     tar xzf bitcoin-32.1-x86_64-linux-gnu.tar.gz
   (Bitcoin Core does not publish an official Docker image, so the release
   binaries are mounted read-only into python:3.13-slim, pinned by digest.)
   For main, testnet3, testnet4, signet and regtest it starts bitcoind on an
   empty data directory with -connect=0 -dnsseed=0 -fixedseeds=0, and records
   the genesis hash, the bound P2P port, the first 4 bytes of blk00000.dat
   (-blocksxor=0 keeps them readable) and the addresses that pkh(), wpkh()
   and tr() descriptors give for one public key. On regtest it mines 200
   blocks and reads the coinbase value at heights 1, 149, 150 and 200.
   The public key is that of private key 1, which everybody knows.
   Never send coins to these addresses.
   Run: BITCOIN_BIN=/path/to/bitcoin-32.1/bin python3 -I btc_networks.py
        -> output/btc_networks.txt
