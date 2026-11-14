---
title: "Zero-Knowledge Proof - ハッシュから R を外す、IsZero 回路の制約を 1 行消すと偽の証明が通る"
date: 2026-11-03T00:00:00+09:00
draft: false
series: ["技術ノート", "Blockchain Systems"]
tags: ["blockchain-systems", "zero-knowledge-proof", "circom", "snarkjs"]
weight: 20
wrapTables: true
topics: ["Cryptography"]
crossTopics:
  security: ["Cryptography"]
---

ゼロ知識証明（Zero-Knowledge Proof、ZKP）は、秘密の値を相手に見せずに、「その値を知っている」「その値で計算すると結果がこうなる」と相手に納得させる暗号の手法です。証明を作る側を証明者（prover）、受け取って正しいかを判定する側を検証者（verifier）と呼びます。手元で 2 種類のゼロ知識証明を動かし、秘密を知らない人が偽の証明を作れるかを試した結果が次の図です。

{{< figure src="images/zkp_cover.webp" alt="左は Schnorr の証明を Fiat-Shamir で 1 通にしたもの。チャレンジのハッシュに R を入れないと、秘密鍵を知らずに作った証明が 1000 個中 1000 個とも検証を通り、R を入れると 0 個。右は circom で書いた IsZero 回路の Groth16 証明。制約が 1 つ足りない回路では x = 5 を「0 と等しい」とした証明が検証を通り、制約がそろった回路では通らない" caption="秘密を知らない人が作った偽の証明が、検証を通るかどうか（手元の実験）" align="center" >}}

左は、ハッシュ関数の入力から途中で送る値を 1 つ外しただけで、秘密鍵を知らない人の証明が 1000 個とも通りました。右は、証明者が自由に入れる値を縛る式を回路から 1 行減らしただけで、「5 は 0 と等しい」という嘘の証明が通りました。暗号の数学は破られておらず、実装の漏れだけで起きています。同じ形の穴は実際のライブラリや、暗号資産を預かるコントラクトが使う回路でも見つかっています。

[Rollup](../rollup/) のうち ZK Rollup は、まとめたトランザクションを正しく実行したことを証明して Ethereum に提出します。Google は 2025 年 7 月に、年齢確認に使う目的で、電子身分証明書（mdoc など）から証明を作るライブラリ [longfellow-zk](https://github.com/google/longfellow-zk) を[公開しました](https://blog.google/technology/safety-security/opening-up-zero-knowledge-proof-technology-to-promote-privacy-in-age-assurance/)。使う側からは「検証のコントラクトが true を返したから正しい」としか見えないので、何が保証されていて、どこが壊れやすいのかを知っておく必要があります。

<br>

本記事では、ZK Rollup や本人確認でゼロ知識証明に出会った人、circom などで回路を書こうとしている人に向けて、次の問いに順に答えます。

- 秘密を見せずに、何をどう納得させるのか。
- 秘密を知らない人は、どれくらいの確率でごまかせるのか。
- 検証者に秘密が漏れないと、どの条件で言えるのか。
- やり取りを 1 通の証明にすると、どこが壊れやすいのか。
- 回路で書く証明は、どこで偽造の穴が開くのか。
- 証明の検証は、計算をやり直すより速いのか。

<br>

前半は Schnorr の証明を Python で、後半は回路を書く言語 [circom](https://github.com/iden3/circom) とライブラリ [snarkjs](https://github.com/iden3/snarkjs) で動かします。

---

### 秘密鍵を知っていることの証明

最初に、ゼロ知識証明で一番小さな例を見ます。題材は「公開鍵 P に対応する秘密鍵 x を知っている」ことの証明です。公開鍵は、楕円曲線で決められた基準点 G を x 回足した点 P = x·G で、Bitcoin や Ethereum の鍵と同じ secp256k1 という曲線を使います。P から x を求める問題は離散対数問題と呼ばれ、現実的な時間では解けないと考えられているので、P を公開しても x は分かりません。鍵の作り方と署名は [Digital Signature](../digital-signature/) で説明しています。

x を見せずに「知っている」と示すには、[Claus Schnorr の方式](https://link.springer.com/article/10.1007/BF00196725)では次の 3 つのやり取りをします。

1. 証明者は乱数 k を選び、R = k·G を検証者へ送る。k は秘密のまま。
2. 検証者は乱数 c を選んで返す。この値をチャレンジ（challenge）と呼ぶ。
3. 証明者は s = k + c·x を計算して返す。

検証者は s·G = R + c·P が成り立てば受け入れます。左辺を展開すると s·G = k·G + c·x·G = R + c·P なので、x を知る証明者はいつも通ります。一方で、x を知らない人は、R を送った後に届く c に対して式を満たす s を作れません。

{{< figure src="images/zkp_order.webp" alt="3 列の図。左の本物の対話は、R を送る、検証者がチャレンジ c を返す、s = k + c·x を返す、の順で、c は R の後に決まる。中央のシミュレーターは、c を自分で決め、s を適当に決め、R = s·G − c·P を逆算する。右の R を入れない Fiat-Shamir は、c = H(P, m) を計算し、s を適当に決め、R を逆算するので、誰でも c を先に知れて偽造できる" caption="R・c・s が決まる順。左が本物の対話で、中央と右は x を使わない" align="center" >}}

上の図では、左の列がこの 3 つのやり取りです。最初に R を送って後から変えられないようにすることをコミットメント（commitment）と呼び、[Commit-Reveal](../commit-reveal/) の「先に約束してから明かす」と同じ考え方です。中央と右の列は、後の節で使います。どの列も最後に満たす式は同じで、違うのは c が R の前に決まるか後に決まるかだけです。

---

### ごまかせる確率

x を知らない人が通る確率は、c の取り得る値の数で決まります。チャレンジを 0 か 1 の 1 ビットにすると、偽の証明者は「c = 0 が来る」と賭けて R = k·G を送るか、「c = 1 が来る」と賭けて R = k·G − P を送ります。賭けが当たれば s = k で式を満たせるので、1 回のやり取りでは半分の確率で通ってしまいます。

そこで、このやり取りを何ラウンドも繰り返し、全てに通った時だけ受け入れます。x を知らない 1000 人に 1 ビットのチャレンジを 20 ラウンド出した実測が次の動く図です。

{{< figure src="images/zkp_survivors.webp" alt="1000 個のマス目が赤い状態から始まり、ラウンドごとに勘が外れた人のマスが灰色になる。残りは 1000、499、258、132、62、31、14、8、2、2、1、1、1 と減り、13 ラウンド目で 0 人になる。上に 1/2 の k 乗 × 1000 の理論値を並べて表示する" caption="秘密鍵を知らない 1000 人が、ラウンドごとに減る様子（実測。1 ラウンドを 0.8 秒ずつ表示）" align="center" >}}

残りの人数は 499、258、132 とほぼ半分ずつ減り、13 ラウンド目で 0 人になりました。一方で、x を知る証明者は 200 回試して 200 回とも 20 ラウンド全てに通りました。偽の証明者が残る確率はラウンドごとに半分になるので、20 ラウンドなら約 100 万分の 1 です。

この「x を知る人は必ず通る」ことを完全性（completeness）、「知らない人はほぼ通らない」ことを健全性（soundness）と呼びます。[ethereum.org の解説](https://ethereum.org/en/zero-knowledge-proofs/)によると、ゼロ知識証明の条件は、この 2 つと、検証者に何も漏れないゼロ知識性の 3 つです。

実際に使う Schnorr の証明では、c を 1 ビットではなく 256 ビットの数から選びます。勘で当たる確率は 2 の 256 乗分の 1 になるので、1 ラウンドで済みます。

<br>

#### 1 ビットのチャレンジで試す

実験のコードは Python の標準ライブラリだけで書きました。楕円曲線の足し算と掛け算の定義は長いので省き、偽の証明者が答えるラウンドだけを載せます。コード全体は [schnorr_zk.py](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/zero-knowledge-proof/lab/schnorr_zk.py) にあります。

```python
def verify(pub, R, c, s):
    """s·G = R + c·pub が成り立てば受け入れる。pub は本文の公開鍵 P"""
    return mul(s) == add(R, mul(c, pub))

def cheater_round():
    """秘密鍵を知らない人が、チャレンジを勘で予想して R を作る"""
    guess = secrets.randbelow(2)
    k = secrets.randbelow(N - 1) + 1
    R = mul(k) if guess == 0 else add(mul(k), neg(pub))  # guess=1 なら k·G - pub
    c = secrets.randbelow(2)       # 検証者が R を受け取った後に投げるチャレンジ
    s = k                          # 当たっていれば s = k で通る
    return verify(pub, R, c, s)

alive = 1000
survivors = [alive]
for _ in range(20):
    alive = sum(cheater_round() for _ in range(alive))
    survivors.append(alive)
```

```text
"survivors": [1000, 499, 258, 132, 62, 31, 14, 8, 2, 2, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0]
"honest_20rounds": "200/200"
```

乱数を使うので、残りの人数は実行ごとに少し変わります。

---

### 正直な検証者に何も漏れない理由

健全性だけなら、x をそのまま見せても満たせます。ゼロ知識証明という名前は、検証者がやり取りから x について何も学ばないことに由来します。この性質がゼロ知識性（zero-knowledge）で、[Goldwasser・Micali・Rackoff の 1985 年の論文](https://dl.acm.org/doi/10.1145/22145.22178)が定義しました。

ゼロ知識性は「x を知らない人でも、本物と見分けがつかないやり取りの記録を作れる」ことで示します。記録を作る人をシミュレーター（simulator）と呼びます。R・c・s の順番を示した図で中央に描いたとおり、シミュレーターは c と s を先に決め、最後に R = s·G − c·P を逆算します。こうして作った (R, c, s) は検証の式を必ず満たします。

本物のやり取りと、シミュレーターが作った記録を 1000 組ずつ用意して検証すると、次のようになりました。

```text
"real_transcripts": "1000/1000"
"simulated_transcripts": "1000/1000"
```

どちらも全て通りましたが、検証の式を満たすように作った記録なので、通るのは当然です。見分けがつかないと言えるのは、次のとおり記録の分布が同じだからです。c と s はどちらも、曲線が持つ点の個数より小さい一様な乱数です。本物の R は k を一様に選んだ k·G、シミュレーターの R も一様な点になるので、記録の分布は同じです。x を知らなくても同じ記録を作れるなら、記録を見ても x について何も分かりません。

ただし、シミュレーターは c を一様な乱数で選んでいるので、示せるのは、手順どおりに c を選ぶ正直な検証者に何も漏れないことだけです。

<br>

<details>
<summary>正直でない検証者と、録画した対話</summary>

正直な検証者に何も漏れない性質を honest-verifier zero-knowledge（HVZK）と呼びます。[Damgård の Σ プロトコルの解説](https://www.cs.au.dk/~ivan/Sigma.pdf)によると、c を R に合わせて選ぶ悪意ある検証者に対しても何も漏れないかは、チャレンジが大きい Schnorr では分かっていません。同じ解説によると、次に扱う Fiat-Shamir で c をハッシュから作り、ハッシュを理想的な乱数の関数とみなせば、この問題は消えます。

シミュレーターは本物の対話では通りません。本物の検証者は、R を受け取った後に c を選ぶからです。一方で、対話を録画した動画は、第三者への証明になりません。シミュレーターでも同じ動画を撮れるからです。

</details>

<br>

---

### 1 通の証明にする Fiat-Shamir

ブロックチェーンでは、検証者がその場で c を返す対話はできません。[コントラクト](../smart-contract/)や他のノードは、後から届いた 1 通のデータだけで判定するからです。そこで [Fiat と Shamir の 1986 年の方法](https://link.springer.com/chapter/10.1007/3-540-47721-7_12)では、検証者の代わりに [Hash Function](../hash-function/) で c を作ります。証明者は c = H(R, P, m) を自分で計算し、(R, s) を 1 通のデータとして送ります。m は証明に結び付けたいメッセージです。m を入れないと、同じ証明を別の場面で[使い回せてしまいます](../replay-protection/)。

ハッシュの出力は入力を決めるまで予想できないので、R を決めた後でしか c は分かりません。対話で検証者が R の後に c を選んだのと同じ順番が、ハッシュで守られます。Bitcoin の Taproot で使う [BIP340 の Schnorr 署名](https://github.com/bitcoin/bips/blob/master/bip-0340.mediawiki)はこの方法の実例で、チャレンジを R・公開鍵・メッセージのハッシュから作ります。

<br>

#### R をハッシュに入れない実験

ハッシュに R を入れずに c = H(P, m) とすると、c は R に関係なく誰でも先に計算できます。順番を示した図で右に描いたとおり、シミュレーターと同じ手順で、x を知らなくても検証を通る (R, s) を作れます。偽造した証明を 1000 個作り、R を入れない検証と、R を入れる検証に渡しました。

```python
msg = b"withdraw 1 ETH"
for _ in range(TRIALS):
    # 偽造する人: x を知らない。s を選び、c を求めてから R を逆算する
    s = secrets.randbelow(N)
    c_weak = h(enc(pub), msg)                # R を入れないチャレンジ
    R = add(mul(s), neg(mul(c_weak, pub)))
    weak_ok += verify(pub, R, h(enc(pub), msg), s)
    c_strong = h(enc(R), enc(pub), msg)      # R を入れるチャレンジ（BIP340 と同じ順）
    strong_ok += verify(pub, R, c_strong, s)
```

```text
"forged_weak": "1000/1000"
"forged_strong": "0/1000"
"honest_weak": "1000/1000"
"honest_strong": "1000/1000"
```

R を入れない検証では、偽造した証明が 1000 個とも通りました。x を知る証明者の証明はどちらの検証でも通るので、正しい証明を流すテストだけでは、この穴は見つかりません。

<br>

#### 実際に見つかった Frozen Heart

この穴は実際のライブラリで見つかっています。Trail of Bits は 2022 年 4 月に、Fiat-Shamir のハッシュに公開値を入れていない実装をまとめて [Frozen Heart](https://blog.trailofbits.com/2022/04/13/part-1-coordinated-disclosure-of-vulnerabilities-affecting-girault-bulletproofs-and-plonk/) という名前で公表しました。この公表によると、ハッシュには証明の主張に出てくる全ての公開値と、証明の途中で送る値を入れる必要があります。Schnorr なら P と R が、それに当たります。

対象には、ZenGo の [zk-paillier](https://github.com/ZenGo-X/zk-paillier/commit/dc37e94f8a375a252a44a40cd3ed56e60c588937) にある、合成数を法とする離散対数の証明と、PLONK という方式の実装が含まれます。PLONK の実装では、ConsenSys の [gnark](https://github.com/Consensys/gnark/releases/tag/v0.7.0) と、本記事の後半で使う [snarkjs](https://github.com/iden3/snarkjs/commit/304c18de10da417ea2a60be7598c9022ba750db5) が修正しました。PLONK は後の節で他の方式と比べます。値が決まった範囲に収まることを示す Bulletproofs という方式では、元の論文が勧めていた作り方にも同じ穴がありました。

---

### 回路で書く証明

Schnorr の証明が示せるのは「x を知っている」ことだけです。ZK Rollup のように「このトランザクションを全て実行すると残高がこうなる」と示したい時は、任意の計算を証明できる仕組みが必要です。そのために使われるのが zk-SNARK（Succinct Non-interactive ARgument of Knowledge）です。名前が proof ではなく argument なのは、証明者の計算能力に限りがあることを前提に安全性を示すからです。

計算を証明するには、まず計算を掛け算と足し算のステップに分け、各ステップの入力と出力が満たすべき式を制約（constraint）として並べます。この形を算術回路（arithmetic circuit）と呼びます。後の節で測る「x² + 1 を N 回繰り返す」計算で N = 2 とし、回路にしたのが次の図です。

{{< figure src="images/zkp_circuit.webp" alt="x から掛け算と +1 を通って t1、t1 から掛け算と +1 を通って y になる回路。制約 1 は t1 = x·x + 1、制約 2 は y = t1·t1 + 1 で、掛け算 1 つにつき制約 1 つ。正しい値 x = 3、t1 = 10、y = 101 は 2 つの制約を満たす。嘘の y = 102 は制約 1 を満たすが、制約 2 の 102 ≠ 10·10 + 1 で満たさない。値は全て 77 桁の素数で割った余りで計算する" caption="x² + 1 を 2 回繰り返す計算の回路と、制約に値を当てはめた結果" align="center" >}}

x = 3 なら途中の値 t1 は 10、y は 101 で、2 つの制約をどちらも満たします。y を 102 と偽ると、制約 2 が成り立ちません。証明者は、全ての制約を満たす値の組を知っていると、短い 1 通の証明で示します。この値の組を witness と呼び、図では x・t1・y の 3 つです。検証者が受け取るのは公開した y と証明だけで、x と t1 は見えません。

回路の値は普通の整数ではなく、大きな素数で割った余りで計算します。この数の世界を有限体（finite field）と呼び、本記事の実験で使う snarkjs では素数が 77 桁です。有限体では割り算の結果も整数になります。例えば 1/5 は 0.2 ではなく、5 を掛けると余りが 1 になる 76 桁の整数です。

circom は、この回路を書くための言語です。circom の `<==` は値を代入すると同時に制約を足し、`<--` は値を代入するだけで制約を足しません。`<--` で入れた値は証明者が自由に選べるので、他の行に書いた制約で縛っておく必要があります。

<br>

#### IsZero の実験

入力 x が 0 なら 1、0 でなければ 0 を返す IsZero という回路で試しました。x の逆数 inv を `<--` で入れ、2 つの制約で縛ります。`1 / x` は有限体の割り算なので、x が 0 でなければ整数で求まります。

```circom
pragma circom 2.1.0;
// x が 0 なら out = 1、0 でなければ out = 0
template IsZero() {
    signal input x;
    signal output out;
    signal inv;
    inv <-- x != 0 ? 1 / x : 0;   // 証明者が計算する値（制約にならない）
    out <== 1 - x * inv;          // 制約 1
    x * out === 0;                // 制約 2
}
component main {public [x]} = IsZero();
```

制約 2 の行を消した回路も用意しました。偽の証明者は、`inv <--` の行だけを `inv <-- 0;` に書き換えた回路で witness を作ります。`<--` は制約にならないので、書き換えても回路の制約は変わりません。実際に、コンパイルした制約のファイル（.r1cs）は、書き換えの前後で sha256 が一致しました。

{{< figure src="images/zkp_iszero.webp" alt="偽の証明者が入れた値は x = 5、inv = 0、out = 1。制約が 1 つ足りない回路では、制約 1 の out = 1 − x·inv を 1 = 1 − 5·0 で満たし、制約 2 は書いていないので見ず、「5 は 0 と等しい」が検証を通る。制約がそろった回路では、制約 2 の x·out = 0 が 5·1 = 5 で満たされず、証明を作れない・通らない" caption="x = 5、inv = 0、out = 1 という値が、各制約を満たすか" align="center" >}}

x = 5 で inv = 0 とすると、制約 1 から out = 1 になり、「5 は 0 と等しい」という出力になります。制約 2 があれば 5·1 = 0 が成り立たないので弾かれますが、制約 2 を消した回路では弾く式がありません。Groth16 という zk-SNARK の方式で、snarkjs を使って証明を作り、検証した結果が次の出力です。Groth16 が他の方式とどう違うかは、後の節で比べます。

```text
iszero_bug honest: 公開値 [out, x] = ["0","5"]  検証 OK!
iszero_bug cheat: 公開値 [out, x] = ["1","5"]  検証 OK!
iszero_ok honest: 公開値 [out, x] = ["0","5"]  検証 OK!
iszero_ok cheat: witness を作れない (Assert Failed)
WITNESS IS NOT CORRECT
iszero_ok 偽の witness: 公開値 [out, x] = ["1","5"]  検証 Invalid proof
```

制約が 1 つ足りない回路では、out = 1 の証明が通りました。制約がそろった回路では、witness を作る段階で止まり、偽の witness を直接渡しても検証で `Invalid proof` になりました。この実験は [iszero.sh](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/zero-knowledge-proof/lab/circom/iszero.sh) で再現できます。

<br>

#### Tornado Cash の MiMC

同じ形の穴は、2019 年に [Tornado Cash](https://github.com/tornadocash/tornado-core) で見つかりました。Tornado Cash は、預けた ETH を別のアドレスで引き出せるようにして、送金の経路を隠すコントラクトです。引き出しの証明は、自分の預け入れの記録が、コントラクトが持つ Merkle 木に含まれることを示します。木の根を計算するハッシュ関数 MiMC の回路で、出力が `=` で代入されていました。circomlib の[修正](https://github.com/iden3/circomlib/pull/22)は、この `=` を `<==` に変えたものです。

当時の circom では、信号への `=` も IsZero の実験で使った `<--` と同じく、制約を足しませんでした。[0xPARC の zk-bug-tracker](https://github.com/0xPARC/zk-bug-tracker) によると、証明者はハッシュの出力を自由に選べるので、偽の Merkle 木の根を作り、他人が預けた ETH を引き出せる状態でした。

[Trail of Bits の解説](https://blog.trailofbits.com/2022/09/15/it-pays-to-be-circomspect/)によると、Tornado Cash のチームは他の人に見つかる前に、自分たちでこの穴を使って資金を引き出し、利用者の資金を守りました。Trail of Bits のこの解説は、circom で `<--` を使った所に警告を出す静的解析のツール Circomspect を紹介しています。Merkle 木と根の役割は [Merkle Tree](../merkle-tree/) で説明しています。

<br>

#### 回路を書かない zkVM

回路を手で書かずに、普通のプログラムを動かした過程をそのまま証明する zkVM（zero-knowledge virtual machine）もあります。例えば [RISC Zero](https://dev.risczero.com/api/zkvm) は、Rust で書いて RISC-V 向けにコンパイルしたプログラムが動いた過程を STARK という方式で証明します。STARK の計算を数値で追う解説は、RISC Zero の [STARK by Hand](https://dev.risczero.com/proof-system/stark-by-hand) にあります。制約を 1 行ずつ書く必要は無くなりますが、証明が保証するのは書いたプログラムの条件だけという点は同じです。

例えば、「積が 391 になる 1 より大きい 2 つの整数を知っている」と示すプログラムは、RISC Zero では次のように書けます。秘密の入力 a と b を読み、条件を満たした時だけ積を公開します。

```rust
fn main() {
    let (a, b): (u32, u32) = risc0_zkvm::guest::env::read();
    assert!(a > 1 && b > 1);
    let product = a.checked_mul(b).expect("u32 overflow");
    risc0_zkvm::guest::env::commit(&product);
}
```

`assert!` の行を消せば、1 × 391 でも証明が作れてしまいます。`checked_mul` を普通の掛け算にして[整数の桁あふれ](../utxo/)を許す書き方も、意図と違う条件を証明してしまいます。`commit` で公開の出力（RISC Zero では journal）に書いた値は誰でも読めるので、秘密の a や b をここに書いてはいけません。

<br>

上のプログラムを RISC Zero 3.0.6 で、17 と 23 を入力にして手元の CPU で証明しました。RISC Zero では、証明と journal をまとめたものを receipt と呼び、どのプログラムを動かしたかを示す image ID と組で検証します。image ID はコンパイルしたプログラムから計算するハッシュで、検証する側は、相手が示した値ではなく自分が期待するプログラムの値を使います。

正しい receipt の検証が通った後に、journal の 1 ビットを反転した receipt と、期待する image ID の 1 ビットを反転した検証を試すと、どちらも失敗しました。証明と 3 回の検証で 8.75 秒でした。

```text
verify_expected_image=PASS; public_product=391
tampered_journal=REJECTED
wrong_image_id=REJECTED
```

<br>

<details>
<summary>RISC Zero の偽の receipt と、隠せる範囲</summary>

RISC Zero には、証明を作らずに偽の receipt を返す [dev-mode](https://dev.risczero.com/api/generating-proofs/dev-mode) があります。検証する側も dev-mode で動いていると、この偽の receipt を通します。

実験で使った [host のコード](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/zero-knowledge-proof/lab/risc0/host/src/main.rs)では、ビルドの設定 `disable-dev-mode` で dev-mode を使えなくしたうえで、受け取った receipt が偽物（`InnerReceipt::Fake`）でないことを `assert!` で検査しています。

RISC Zero の [Security Model](https://dev.risczero.com/api/security-model#zero-knowledge-proving) によると、実行を区間に分けて作った証明は、再帰でまとめる前の形だと実行の長さが漏れます。区間の数は実行が長いほど増えるからです。再帰で 1 つにまとめた証明では漏れません。実験では、succinct receipt と呼ばれる、まとめた形を使いました。

同じ資料は、目標とする完全なゼロ知識性について、数学的な証明をまだ書いていないとも明記しています。2026 年 11 月に、実験で使った 3.0 系と 3.1 の文書を読み、どちらも同じ記述でした。

</details>

<br>

---

### 計算をやり直すのと比べる

回路の証明で得られるものは、秘密を隠せることだけではありません。zk-SNARK の S（Succinct）のとおり、証明が小さく、検証が速く済みます。Groth16 では、公開値の数が同じなら、理論上は証明の大きさも検証の手間も計算の大きさによらず一定です。x を秘密にしたまま、x² + 1 を N 回繰り返した結果 y を公開する回路で、N を 256 から 32,000 まで変えて測りました。

{{< figure src="images/zkp_bench.webp" alt="横軸は計算の回数 N（256 から 32,000）、縦軸は対数の時間。証明を作る時間は 33、55、124、394、552 ms と増える。証明を検証する時間は 4.8 から 10.3 ms で、N を 125 倍にしても 5〜10 ms の範囲。x を知る人が計算をやり直す時間は 0.05 から 13.73 ms と N とともに増え、N = 32,000 で検証の時間と同じくらいになる。線は 3 回測った各値の最小で、N = 32,000 を同じ回どうしで比べると、やり直す方が遅いのは 3 回中 2 回。証明の大きさはどの N でも 256 バイト" caption="計算の回数 N と、証明を作る・検証する・やり直す時間（snarkjs の Groth16、3 回測った最小）" align="center" >}}

証明を作る時間は N とともに増えました。検証の時間は、N を 125 倍にしても 5〜10 ms の範囲に収まりましたが、N = 32,000 では、N = 16,384 の 5.4 ms から約 2 倍の 10.3 ms です。同じ N でも、実行ごとに 2 倍ほどぶれました。

x を知っている人が同じ計算をやり直す時間は、0.05 ms から 13.73 ms へ N とともに伸びました。N = 16,384 までは、3 回の計測のどれでも、やり直す方が検証より速く済みました。N = 32,000 では両者が並び、同じ回の計測どうしで比べると、やり直す方が遅かったのは 3 回中 2 回です。

<br>

<details>
<summary>計測の条件</summary>

数値は、他の処理も動いている 32 コアの機械で、15 回の最小を 3 回取り、項目ごとに 3 回の最小を選んだ値です。そのため、図の 1 つの N の値が同じ回の計測とは限りません。

やり直す時間は JavaScript の BigInt で同じ計算を繰り返した時間、検証の時間は Node.js 上の snarkjs で測りました。実行ごとに 2 倍ほどぶれました。測定のコードは [bench.mjs](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/zero-knowledge-proof/lab/circom/bench.mjs) で、3 回分の記録は [bench_runs.tsv](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/zero-knowledge-proof/lab/output/bench_runs.tsv) にあります。

</details>

<br>

#### ZK Rollup で効く所

ZK Rollup が証明を提出するのも、同じ理屈です。Ethereum 本体を L1、その外でトランザクションを処理するチェーンを L2 と呼びます。Ethereum のノードは全てのトランザクションを [EVM](../evm/) で実行し直すので、L2 で処理した数千件のトランザクションをそのまま L1 で実行すると重くなります。代わりに証明を 1 つ検証すれば済むようにするのが ZK Rollup です。

Groth16 の検証は公開値の数に応じて重くなるので、件数によらず手間を抑えられるのは、トランザクションの結果を少ない公開値にまとめた時です。本記事の実験は Node.js 上の snarkjs で、L1 のガスは測っていません。

Groth16 の検証に使う楕円曲線の計算は Ethereum に組み込まれているので、L1 のコントラクトでも安いガスで検証できます。組み込みの経緯は [EVM Opcode History](../evm-opcode-history/) で扱っています。

なお、[ethereum.org の ZK Rollup の解説](https://ethereum.org/developers/docs/scaling/zk-rollups/)によると、有効性の証明を使うだけではトランザクションの中身は秘密になりません。トランザクションのデータは誰でも検証できるように公開されているからです。ZK Rollup で主に効いているのは、ゼロ知識性ではなく、証明が小さく検証が速いという性質のほうです。

<br>

#### zk-SNARK の方式を比べる

zk-SNARK にも方式がいくつかあり、事前の準備と証明の大きさが違います。事前の準備で出てくる trusted setup は、誰も知らない秘密の乱数から、証明の検証に使う公開の値を作る手順です。この乱数を知る人がいれば、どんな偽の証明でも作れます。

| 方式 | 事前の準備 | 証明の大きさ | 採用・実装の例 |
|---|---|---|---|
| [Groth16](https://eprint.iacr.org/2016/260) | 回路ごとの trusted setup | 楕円曲線の点 3 つ | Zcash の Sapling、Tornado Cash |
| [PLONK](https://eprint.iacr.org/2019/953) | 回路によらない trusted setup | 1 KB 未満 | snarkjs、gnark |
| [STARK](https://eprint.iacr.org/2018/046) | 不要（ハッシュだけ） | 数十〜数百 KB | Starknet |
| [Bulletproofs](https://eprint.iacr.org/2017/1066) | 不要 | 1 KB 未満 | Monero の送金額（2022 年からは改良した Bulletproofs+） |

Groth16 の点 3 つは、本記事の実験で使った snarkjs では 256 バイトです。Bulletproofs の大きさは、値が 64 ビットに収まることを示す場合です。

本記事の実験では、trusted setup を手元で 1 人分の乱数から作ったので、実験の外には使えません。実際の運用では大勢が乱数を順に混ぜ、1 人でも乱数を捨てれば安全になる手順を踏みます。この手順はセレモニー（ceremony）と呼ばれます。

[Electric Coin Company の告知](https://electriccoin.co/blog/zcash-counterfeiting-vulnerability-successfully-remediated/)によると、Zcash では 2018 年 3 月に、当時の setup が余分な値を公開していて偽のコインを作れることが、社内の暗号学者に見つかりました。同年 10 月の Sapling で新しい setup と Groth16 に移り、悪用の形跡は見つかっていません。STARK は setup の秘密を持たない代わりに証明が大きく、L1 で検証するガスが高くつきます。

---

### 使う前に見る所

冒頭の図に示した 2 つの偽造は、どちらも正しい証明を流すテストでは見つかりません。ゼロ知識証明を使うライブラリやコントラクトを選ぶ時、自分で回路を書く時は、正しい証明が通ることより、偽の証明が通らないことを見ます。

- Fiat-Shamir のハッシュに、全ての公開値と途中で送る値が入っているか。
- 回路で `<--` を使った値が、他の行に書いた制約で縛られているか。
- 偽の witness を直接渡して、検証が失敗するテストがあるか。
- trusted setup を誰がどう作ったかが、公開されているか。
- 検証に使う鍵と公開値が、自分の期待する値と一致するか。
- 秘密を隠すことが必要なのか、検証が速いだけでよいのか。

秘密を隠す場合も、zkVM の例で公開した 391 から 17 と 23 が分かるように、公開した主張から分かることは隠せません。

隠せる相手も検証者だけで、証明の生成を外部に委託すれば、入力は委託先に見えます。また、証明が保証するのは入力に対して計算が正しいことで、入力が本当の値かは別です。自己申告の生年月日で年齢を証明しても意味が無いので、[信頼できる発行者の署名](/notes/security/pki/)を回路の中で検査するなど、入力と現実を結び付ける条件も回路に入れます。

<br>

秘密を隠す必要が無く、検証する側が入力を全て持っているなら、証明を使うほど計算が大きいかも見直せます。x² + 1 という軽い計算と snarkjs の検証を比べた実験では、N = 16,384 まではやり直す方が速かったからです。どこで逆転するかは、計算 1 回の重さと検証する環境で変わります。

実験のコードと出力は [lab](https://github.com/nao1215/debimate/tree/main/content/notes/blockchain-systems/zero-knowledge-proof/lab) にあります。
