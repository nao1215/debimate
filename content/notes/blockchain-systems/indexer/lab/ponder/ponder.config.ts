import { createConfig } from "ponder";
import { TokenAbi } from "./abis/Token";

// Anvil の 1 つ目のアカウントが nonce 0 で作るコントラクトのアドレス
export default createConfig({
  chains: {
    anvil: { id: 31337, rpc: process.env.RPC_URL ?? "http://127.0.0.1:18781", pollingInterval: 200 },
  },
  contracts: {
    Token: { chain: "anvil", abi: TokenAbi, address: "0x5FbDB2315678afecb367f032d93F642f64180aa3", startBlock: 1 },
  },
});
