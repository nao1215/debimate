#!/usr/bin/env bash
# 制約が 1 つ足りない IsZero で、x = 5 を「0 である」と証明できるか試す
set -u
S=node_modules/.bin/snarkjs
echo '{"x": "5"}' > in5.json
for circ in iszero_bug iszero_ok; do
  $S groth16 setup c/$circ.r1cs pot15.ptau c/$circ.zkey >/dev/null
  $S zkey export verificationkey c/$circ.zkey c/$circ.vkey.json >/dev/null
  for prover in honest cheat; do
    wasm=c/${circ}_js/$circ.wasm
    [ $prover = cheat ] && wasm=c/${circ}_cheat_js/${circ}_cheat.wasm
    if ! node c/${circ}_js/generate_witness.js "$wasm" in5.json w.wtns 2>err.txt >/dev/null; then
      echo "$circ $prover: witness を作れない ($(grep -o 'Assert Failed[^.]*' err.txt | head -1))"; continue
    fi
    $S groth16 prove c/$circ.zkey w.wtns proof.json public.json >/dev/null
    ok=$($S groth16 verify c/$circ.vkey.json public.json proof.json | grep -o 'OK!\|Invalid proof')
    echo "$circ $prover: 公開値 [out, x] = $(tr -d ' \n' < public.json)  検証 $ok"
  done
done
# 制約がそろった回路に、偽の witness（out = 1, inv = 0）を直接渡す
node c/iszero_bug_js/generate_witness.js c/iszero_bug_cheat_js/iszero_bug_cheat.wasm in5.json w.wtns >/dev/null
$S wtns check c/iszero_ok.r1cs w.wtns 2>&1 | grep -o 'WITNESS IS NOT CORRECT\|WITNESS CHECKING FINISHED SUCCESSFULLY' | head -1
$S groth16 prove c/iszero_ok.zkey w.wtns proof.json public.json >/dev/null
echo "iszero_ok 偽の witness: 公開値 [out, x] = $(tr -d ' \n' < public.json)  検証 $($S groth16 verify c/iszero_ok.vkey.json public.json proof.json | grep -o 'OK!\|Invalid proof')"
# <-- の行を書き換えた回路（*_cheat）は、元の回路と制約のファイル（.r1cs）が同じか
for circ in iszero_bug iszero_ok; do
  a=$(sha256sum c/$circ.r1cs | cut -c1-16); b=$(sha256sum c/${circ}_cheat.r1cs | cut -c1-16)
  echo "$circ.r1cs と ${circ}_cheat.r1cs の sha256: $a / $b  $([ "$a" = "$b" ] && echo 一致 || echo 不一致)"
done
