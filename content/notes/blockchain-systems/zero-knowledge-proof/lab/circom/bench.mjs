// 計算の回数 N ごとに、証明を作る時間・検証の時間・証明の大きさを 1 つのプロセスの中で測る
import * as snarkjs from "snarkjs";
import { readFileSync } from "node:fs";
const best = async (f, n = 15) => { let m = Infinity; for (let i = 0; i < n; i++) { const t = performance.now(); await f(); m = Math.min(m, performance.now() - t); } return m; };
// circom の数（BN254 のスカラー体）の法
const r = 21888242871839275222246405745257275088548364400416034343698204186575808495617n;
console.log("N\tprove_ms\tverify_ms\tproof_bytes\trecompute_ms");
for (const N of [256, 1024, 4096, 16384, 32000]) {
  const wasm = `c/chain${N}_js/chain${N}.wasm`, zkey = `c/chain${N}.zkey`;
  const vkey = JSON.parse(readFileSync(`c/chain${N}.vkey.json`));
  let res;
  const prove = await best(async () => { res = await snarkjs.groth16.fullProve({ x: "3" }, wasm, zkey); });
  const verify = await best(async () => { if (!await snarkjs.groth16.verify(vkey, res.publicSignals, res.proof)) throw new Error("NG"); });
  // 証明は G1 の点 2 つと G2 の点 1 つ。Solidity の検証に渡す時は 32 バイトの数 8 個
  const bytes = 32 * 8;
  // x を知っている人が同じ計算をやり直す時間
  const recompute = await best(async () => { let t = 3n; for (let i = 0; i < N; i++) t = (t * t + 1n) % r; if (t.toString() !== res.publicSignals[0]) throw new Error("mismatch"); });
  console.log([N, prove.toFixed(0), verify.toFixed(1), bytes, recompute.toFixed(2)].join("\t"));
}
process.exit(0);
