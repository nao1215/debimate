Data for the EVM Opcode History note
These scripts read pinned source checkouts; they are not run by a node.

  GETH_SRC=/path/to/go-ethereum bash count_opcodes.sh
    -> output/geth_tables.json (opcodes per instruction set, precompiles per fork)
       needs Go; go-ethereum must be at ddaa6957127ef0c4b7d41e5cbd9c19e260c0a42f.
       zz_count_opcodes_test.go is copied into core/vm, run, and removed.
  EIPS_SRC=/path/to/EIPs ERCS_SRC=/path/to/ERCs python3 eip_graph.py
    -> output/eip_graph.json (category, status and requires from the front matter)
       EIPs at 542e62eb129517130b7facc52bbb9a1f333c711e,
       ERCs at f94e400afdddaa2625c291f71646bde0ef44df9d.
Then python3 ../figures.py redraws images/ (WebP; needs matplotlib, Pillow and google-chrome).

The precompile calls (0x01, 0x02, 0x100) are part of the EVM note's local
experiment: bash content/notes/blockchain-systems/evm/lab/run.sh
