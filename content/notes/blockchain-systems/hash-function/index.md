---
title: "Hash Function - 4 バイトの keccak256 は、どれか 2 つの名前なら平均 8 万回弱で重なる"
date: 2026-08-10
draft: false
series: ["技術ノート", "Blockchain Systems"]
tags: ["blockchain-systems", "cryptography"]
weight: 3
wrapTables: true
topics: ["Cryptography"]
crossTopics:
  security: ["Cryptography"]
---

ハッシュ関数（hash function）は、長さの決まっていないデータから固定長の値を作る関数です。変換後の値をハッシュ値と呼び、同じ入力からは誰がいつ計算しても同じ値になります。ブロックチェーンでは、取引の識別子、ブロック同士のつながり、アドレス、コントラクトの関数を選ぶ値が、どれもハッシュ値から作られています。

Ethereum のコントラクトを呼ぶ時は、`transfer(address,uint256)` のように関数名と引数の型を並べた文字列を keccak256 というハッシュ関数に通し、得た 32 バイトの先頭 4 バイトで呼ぶ関数を指定します。この 4 バイトを関数セレクター（function selector）と呼びます。

4 バイトは 32 ビットなので、取り得る値は約 43 億通りです。名前を 1 つずつ変えながら keccak256 を計算し、先頭 n ビットが一致するまでの回数を手元で数えました。数えたのは、決まった 1 つの値に当てる探し方と、どれでもよい 2 つが一致する探し方の 2 通りです。

{{< figure src="images/tries.webp" alt="横軸は比べる先頭のビット数 n（8 から 32）、縦軸は一致するまでの試行回数の対数。決まった 1 つの値に当てる探索（赤）は n が 4 増えるごとに 16 倍になり、理論の 2 の n 乗の線に乗る。どれでもよい 2 つが一致する探索（青）は 4 倍ずつしか増えず、32 ビットで平均 77,338 回。32 ビットの赤い星は Poly Network で攻撃者が使った名前 f1121318093 で、f0 から数えて 1,121,318,094 回目、32 スレッドで 93 秒" caption="keccak256 の先頭 n ビットが一致するまでの試行回数（lab/run.sh の実測）" align="center" >}}

32 ビットでは、どれでもよい 2 つの名前が同じセレクターになるまで、200 回の平均で 77,338 回でした。決まった 1 つのセレクターに当てる方は約 43 億回が目安で、赤と青の線は 32 ビットで 5 万倍以上離れます。

2021 年 8 月に [Poly Network](https://poly.network/) から約 6 億 1,100 万ドル相当が流出した攻撃では、攻撃者が `f1121318093` という名前で、狙った関数と同じセレクターを作っていました。f0 から順に試すと、この名前は 1,121,318,094 回目に見つかる最初の一致で、手元の 32 スレッドで 93 秒でした。

コントラクトやウォレットを作る人は、関数セレクターの 4 バイト、アドレスの 20 バイト、取引ハッシュの 32 バイトに毎日出会います。どれも同じ種類の関数から作られていますが、長さが違えば任せられることも違います。また、Ethereum の keccak256 を [Python](https://www.python.org/) 標準の `hashlib.sha3_256` で計算し直すと別の値になり、署名やセレクターの照合が合わない原因になります。

<br>

本記事では、ハッシュ値を使うコードを書く人と、既存のコントラクトでこうした値に出会った人に向けて、次の疑問を順に扱います。

- ハッシュ値が守っているのは、どんな性質か。
- 一致する入力を探すには、何回計算すればよいのか。
- 4 バイトのセレクターは、なぜ攻撃に使えたのか。
- Ethereum の keccak256 と SHA3-256 は同じ関数か。
- 秘密の値を前に付けたハッシュは、なぜ署名の代わりにならないのか。

---

### 3 つの性質

本記事で扱うのは暗号学的ハッシュ関数で、通信の誤り検出に使う CRC（Cyclic Redundancy Check）やハッシュテーブル向けの関数は対象外です。SHA-256 が内部でする計算は [SHA-256](/notes/security/sha-256/) のノートで説明しているので、ここでは使う側から見た違いに絞ります。

ハッシュ値を使う基本の場面は、改竄の検出です。受け取ったデータのハッシュ値を自分で計算し、先に知っている正しいハッシュ値と比べます。一致すれば書き換えられていないとみなすので、元データの複製を手元に持つ必要がありません。

Linux ディストリビューションの配布ページが、イメージと並べて SHA-256 の値を載せているのがこの使い方です。SHA-256 は米国の標準 [FIPS 180-4](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.180-4.pdf) で定められた関数で、ダウンロードした人は [sha256sum](https://www.gnu.org/software/coreutils/manual/html_node/sha2-utilities.html) のようなコマンドで照合します。送金額を書いたファイルの 1 文字を書き換えて照合すると、次のようになります。

```console
$ sha256sum --version
sha256sum (uutils coreutils) 0.10.0
$ printf 'send 1 BTC to Alice\n' > tx.txt
$ sha256sum tx.txt > tx.txt.sha256
$ cat tx.txt.sha256
4a33e87ff753acb1b8305bf2fb21d53035fbb648634b998e348e66baebc7e853  tx.txt
$ printf 'send 9 BTC to Alice\n' > tx.txt
$ sha256sum -c tx.txt.sha256
tx.txt: FAILED
sha256sum: WARNING: 1 computed checksum did NOT match
```

照合に使ったのは記録しておいた 64 文字だけで、書き換える前のファイルは残していません。

ただし、守れるのはデータとハッシュ値の対応だけです。基準のハッシュ値ごと差し替えられれば照合は通るので、正しい値は改竄されにくい経路で先に得ておく必要があります。不一致からは、どこが書き換えられたかも分かりません。

[Bitcoin](https://bitcoin.org/) では、[各ブロックヘッダ](../bitcoin-block/)が直前ヘッダのハッシュ値を含みます。1 つを書き換えると後ろのブロックを全て作り直すことになり、作り直しには [Proof of Work](../proof-of-work/) の計算が掛かるので、基準の値を差し替えにくくなっています。ハッシュ関数がブロックチェーンのどの問題を解いているかは、[Blockchain Basics](../blockchain-basics/) で他の仕組みと並べています。

<br>

照合が成り立つのは、同じハッシュ値になる別の入力を見つけるのが難しいからです。SHA-256 と keccak256 の出力は 256 ビット（32 バイト、16 進で 64 文字）で、取り得る値は 2<sup>256</sup> 通りあります。入力の種類はそれより多いので、同じ値になる入力の組は必ず存在します。この組を衝突（collision）と呼びます。頼っているのは衝突が無いことではなく、見つけるのに現実的でない計算量が必要なことです。

入力が少し違うだけで出力ビットの約半分が変わる雪崩効果（avalanche effect）も、よく知られた性質です。`hello` と `hellp` は、入力で見ると 5 ビットしか違いません。

```console
$ printf hello | sha256sum
2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824  -
$ printf hellp | sha256sum
fdd7585e08c4e2afd71dcabdb4636c89d557a3f42db9e2040c8bbd1708aa4ce7  -
```

2 つの値は 16 進の 64 桁中 63 桁が違い、ビットで数えると 256 ビット中 131 ビットが違います。

ただし、雪崩効果から「狙った値になる入力を効率よく探せない」までは言えません。探しにくさは、攻撃者に何が与えられているかで次の 3 つに分けて考えます。

| 性質 | 攻撃者に与えられるもの | 探すもの |
| --- | --- | --- |
| 原像計算困難性（preimage resistance） | ハッシュ値だけ | その値になる入力 |
| 第二原像計算困難性（second preimage resistance） | 入力とそのハッシュ値 | 同じ値になる別の入力 |
| 衝突耐性（collision resistance） | 何も無い | 同じ値になる入力の組 |

ハッシュ値から元の入力へ戻れないことを一方向性と呼ぶ時は、1 つ目の原像計算困難性を指します。

冒頭に載せた図で、赤は決まった値に当てる探索なので、原像か第二原像を探す攻撃に当たります。青は 2 つの入力をどちらも自分で選べるので、衝突を探す攻撃です。

上で sha256sum を使った照合が直接頼るのは、第二原像計算困難性です。攻撃者の手元には正しいファイルとそのハッシュ値があり、同じ値になる別の内容を探すからです。

Bitcoin で取引を指す txid という識別子も同じで、ブロックに入った他人の取引を txid が同じ別の取引に差し替える攻撃は、第二原像を探す問題になります。一方で、取引を作る本人が同じ txid になる 2 つを最初から仕込むなら、衝突耐性の問題です。

出力が n ビットの理想的なハッシュ関数では、原像と第二原像の探索に約 2<sup>n</sup> 回、衝突の探索に約 2<sup>n/2</sup> 回の計算が必要です。本記事に出てくる長さで並べると次の通りです。

| 出力の長さ | 例 | 決まった値に当てる | どれでもよい 2 つ |
| --- | --- | --- | --- |
| 32 ビット | 関数セレクター | 2<sup>32</sup>（約 43 億） | 2<sup>16</sup>（約 6.6 万） |
| 160 ビット | SHA-1、20 バイトのアドレス | 2<sup>160</sup> | 2<sup>80</sup> |
| 256 ビット | SHA-256、keccak256 | 2<sup>256</sup> | 2<sup>128</sup> |

衝突だけ少なく済むのは、計算した値を溜めておけば、溜めた中のどの 2 つが一致しても成功になるからです。比べる組の数は溜めた個数の 2 乗で増えます。より正確には、衝突までの平均は 2<sup>n/2</sup> の約 1.25 倍で、冒頭に載せた図で青い破線が示すのはこの値です。23 人いれば誕生日が同じ組の現れる確率が 50% を超えるのと同じ数え方で、この探し方を[誕生日攻撃](https://ja.wikipedia.org/wiki/%E8%AA%95%E7%94%9F%E6%97%A5%E6%94%BB%E6%92%83)と呼びます。

---

### 試行回数の実測

冒頭の図は、関数名の候補を f0、f1、f2 と順に作り、後ろに `(bytes,bytes,uint64)` を付けて keccak256 を計算する C のプログラムで数えました。決まった値に当てる探索は、先頭 n ビットが目標と一致した最初の番号を出します。どれでもよい 2 つの探索は、計算したセレクターを表に溜め、溜めた中と一致した時点の回数を出します。

以下は、セレクターを求める関数と、決まった値に当てる探索の抜粋です。Keccak が内部で繰り返す置換 Keccak-f の実装と、どれでもよい 2 つの探索を含む全体は [selector_search.c](lab/selector_search.c)、実行の手順は [run.sh](lab/run.sh) にあります。

```c
/* 136 バイト未満の入力の keccak256 の先頭 4 バイトを、ビッグエンディアンの整数で返す */
static uint32_t selector(const char *msg, size_t len) {
    uint8_t block[136] = {0};
    memcpy(block, msg, len);
    block[len] = 0x01;
    block[135] |= 0x80;
    uint64_t s[25] = {0};
    for (int i = 0; i < 17; i++) {
        uint64_t w;
        memcpy(&w, block + 8 * i, 8);
        s[i] ^= w;
    }
    keccak_f(s);
    uint8_t *o = (uint8_t *)s;
    return ((uint32_t)o[0] << 24) | ((uint32_t)o[1] << 16) | ((uint32_t)o[2] << 8) | o[3];
}

/* target: prefix0, prefix1, ... に suffix を付けて試し、先頭 n ビットが一致した最初の番号を探す */
for (uint64_t base = 0; found == UINT64_MAX; base += chunk * 64) {
#pragma omp parallel for schedule(dynamic, 1) reduction(min : found)
    for (uint64_t c = 0; c < 64; c++) {
        char buf[136];
        for (uint64_t i = base + c * chunk; i < base + (c + 1) * chunk; i++) {
            int len = snprintf(buf, sizeof buf, "%s%" PRIu64 "%s", prefix, i, suffix);
            if ((selector(buf, len) & mask) == (target & mask)) {
                if (i < found) found = i;
                break;
            }
        }
    }
}
```

`selector` の `136`・`0x01`・`0x80` は入力の後ろに足すパディングに関わる値で、keccak256 と SHA3-256 の節で図にします。`17` は 136 バイトを 8 バイトずつ内部状態に混ぜる回数です。

探索の `mask` は先頭 n ビットだけを残す値、`chunk` は 1 つのスレッドが続けて試す番号の数です。`#pragma omp parallel for` で番号の区間を 32 スレッドに分け、一致した番号のうち最小のものを `found` に残します。Poly Network で狙われた `41973cd9` に 32 ビットで当てた結果と、32 ビットでどれでもよい 2 つを探した結果は次の通りです。

```text
$ ./selector_search target 41973cd9 32 f "(bytes,bytes,uint64)"
n=32 tries=1121318094 seconds=93.26 threads=32 selector=41973cd9 name=f1121318093(bytes,bytes,uint64)
$ ./selector_search collide 32 1 "(bytes,bytes,uint64)"
n=32 tries=22741 selector=ac40ac89 a=g1_4931(bytes,bytes,uint64) b=g1_22741(bytes,bytes,uint64)
```

`g1_4931(bytes,bytes,uint64)` と `g1_22741(bytes,bytes,uint64)` は、どちらもセレクターが `ac40ac89` です。どれでもよい 2 つの探索を名前の種を変えて 200 回繰り返すと、回数は次のように散らばりました。

{{< figure src="images/collide32.webp" alt="32 ビットでどれでもよい 2 つが一致するまでの試行回数を 200 回測ったヒストグラム。横軸は千回単位で 0 から 200。平均 77,338 回の縦線の周りに山があり、最小は 2,238 回、最大は 202,482 回" caption="32 ビットでどれでもよい 2 つが一致するまでの回数（200 回）" align="center" >}}

一番遅い回でも 20 万回ほどで、1 秒かかりません。32 ビットの衝突は、運に関係なく無いに等しい手間です。手元の 32 スレッドは 1 秒に 1,200 万回ほど計算できるので、決まった値に当てる探索も、平均の約 43 億回は 6 分ほどです。

冒頭に載せた図では、赤と青の平均がどちらも理論の線と同じ桁に乗りました。ただし、決まった値に当てる探索は 1 つの n で 30 回、28 ビットでは 8 回しか測っていないので、平均は理論の 0.8〜1.4 倍の幅でずれています。手元の測り方で言えるのは、keccak256 の先頭を切った値で理論の見積もりが使えるところまでです。

この速さは、パスワードを総当たりする速さでもあります。パスワードの保存に SHA-256 をそのまま使わず、[bcrypt](https://www.usenix.org/legacy/events/usenix99/provos/provos.pdf) のように計算を意図的に遅くした専用の関数を使うのはこのためです。保存の仕組みは [Authentication](/notes/security/authentication/) のノートにあります。

---

### Poly Network のセレクター衝突

Poly Network は、チェーンをまたいで資産を移す[クロスチェーンブリッジ](../cross-chain-bridge/)です。Ethereum 側には、他のチェーンから届いたメッセージを検証して実行する `EthCrossChainManager` と、メッセージに署名できる keeper の公開鍵などを保存する `EthCrossChainData` の 2 つのコントラクトがありました。

以下、Manager と Data と呼びます。Data の書き換えは所有者だけに許され、その所有者は Manager でした。

Manager は、メッセージに書かれた関数名から次の 1 行でセレクターを作り、宛先のコントラクトを呼んでいました（[当時のコード](https://github.com/polynetwork/eth-contracts/blob/15d84b7f34d2068d7548d5385c3d43c37a7232ba/contracts/core/cross_chain_manager/logic/EthCrossChainManager.sol#L190)）。`_method` はメッセージの送り手が決められる値で、宛先がコントラクトであること以外は検査していません。

```solidity
(success, returnData) = _toContract.call(abi.encodePacked(bytes4(keccak256(abi.encodePacked(_method, "(bytes,bytes,uint64)"))), abi.encode(_args, _fromContractAddr, _fromChainId)));
```

セキュリティ企業 [BlockSec の解析](https://blocksec.com/blog/the-further-analysis-of-the-poly-network-attack)と [rekt.news の解説](https://rekt.news/polynetwork-rekt/)によると、攻撃は次の順に進みました。

1. Ontology から、宛先を Data、関数名を `f1121318093` にしたメッセージを送る。
   Ontology は Poly Network がつなぐチェーンの 1 つです。メッセージは Poly Network のチェーンまで中継され、正規の記録になりました。Ethereum 側の中継は宛先を見て拒否しましたが、攻撃者はその記録を自分で Manager に渡して実行させました。

2. Manager が作ったセレクターが、Data の `putCurEpochConPubKeyBytes(bytes)` と一致する。
   呼び出し元の Manager は Data の所有者なので、所有者だけの検査も通りました。keeper の公開鍵は、攻撃者の鍵に置き換わりました。

3. 攻撃者の鍵で署名したメッセージで、資産を引き出す。
   Ethereum・BNB Smart Chain・Polygon の 3 つのチェーンで、合計約 6 億 1,100 万ドル相当が流出しました。資産は後に攻撃者から返還されています。

{{< figure src="images/poly.webp" alt="上の段は狙われた関数 putCurEpochConPubKeyBytes(bytes) で、keccak256 は 41973cd9ca2c3f7f... 。下の段は攻撃者が送った名前に固定された引数の型を付けた f1121318093(bytes,bytes,uint64) で、keccak256 は 41973cd95e41447f... 。先頭 4 バイトの 41973cd9 だけが一致し、残りの 28 バイトは全く違う" caption="狙われた関数と、攻撃者が送った名前の keccak256（lab/keccak.py で計算）" align="center" >}}

32 バイトのハッシュ値を比べていれば、2 つは全く別の値です。先頭 4 バイトだけを比べたので、Manager は攻撃者の名前を所有者向けの関数として呼びました。攻撃者は固定された引数の型 `(bytes,bytes,uint64)` を変えられないので、どれでもよい 2 つでは足りず、決まった値に当てる探索が必要です。それでも 32 ビットなので、平均でも手元の PC で 6 分ほどの回数です。

<br>

コントラクトを書く言語 Solidity の[コンパイラ](https://github.com/ethereum/solidity/blob/develop/libsolidity/analysis/ContractLevelChecker.cpp)は、1 つのコントラクトの中でセレクターが重なると `Function signature hash collision` のエラーで止めます。しかし、別々のコントラクトにある関数同士は比べません。Poly Network の 2 つの関数も別のコントラクトにありました。

セレクターは呼ぶ関数を選ぶための値で、呼び出しを許すかどうかを判断する値ではありません。問題の根は、送り手が決めた名前で特権を持つコントラクトを呼べたことにあります。Poly Network は 2021 年 12 月に、呼べる宛先と関数を登録制にする検査を[現在のコード](https://github.com/polynetwork/eth-contracts/blob/097214982454bb2e225c2bfba81d28f4852c2203/contracts/core/cross_chain_manager/logic/EthCrossChainManager.sol#L230)に足しています。

---

### 部品ごとの長さ

ブロックチェーンの部品は、3 つの性質のどれかに頼っています。長さと合わせて並べると次の通りです。

| 使う所 | 関数と長さ | 頼る性質 |
| --- | --- | --- |
| Bitcoin で取引の識別子・[Merkle Tree](../bitcoin-merkle-tree/) のルート | SHA-256 を 2 回、256 ビット | 第二原像・衝突耐性 |
| Proof of Work の計算 | SHA-256 を 2 回、256 ビット | 原像に近い性質 |
| [Ethereum のアドレス](../ethereum-address/) | keccak256 の下位 20 バイト | 第二原像・衝突耐性 |
| 公開鍵のハッシュ値に送る Bitcoin の P2PKH アドレス | SHA-256 → [RIPEMD-160](https://homes.esat.kuleuven.be/~bosselae/ripemd160.html)、160 ビット | 原像・第二原像 |
| [commit-reveal](../commit-reveal/) | keccak256、256 ビット | 原像・衝突耐性 |
| [Lightning の支払い](../lightning-network/) | SHA-256、256 ビット | 原像 |
| 関数セレクター | keccak256 の先頭 4 バイト | どれにも頼れない |

Bitcoin がブロックヘッダに SHA-256 を 2 回掛けることは[開発者向けの資料](https://developer.bitcoin.org/reference/block_chain.html)に、P2PKH（Pay to Public Key Hash）の 20 バイトの作り方は [Bitcoin Script](../bitcoin-script/) のノートにあります。

Proof of Work で探すのは、決まった 1 つの値になる入力ではありません。ハッシュ値を 256 ビットの数として読み、合格の基準になる target という値以下に入る入力を探します。ブロックヘッダの nonce という欄を変えながら、計算を繰り返します。

頼っているのは、この範囲に入る入力を総当たりより速く探す方法が知られていないことです。そのため、必要な回数は 2<sup>256</sup> ではなく、target の厳しさで決まります。

残りの部品は、3 つの性質の節で長さごとに並べた回数の表で見積もれます。256 ビットなら、衝突を探す攻撃でも約 2<sup>128</sup> 回で、現実の計算機では終わらない回数です。160 ビットのアドレスでは、衝突を探す攻撃が約 2<sup>80</sup> 回まで下がります。

[EIP-3607](https://eips.ethereum.org/EIPS/eip-3607) は、この 2<sup>80</sup> 回を現実の脅威として扱った提案です。コントラクトのアドレスと、秘密鍵で操作するアカウント（EOA、Externally Owned Account）のアドレスが重なる組は、約 100 億ドルの機材と電気代があれば 1 年ほどで見つかると見積もっています。そこで、コードの置かれたアドレスを送信元とする取引を拒否する規則を足しました。

---

### 理想から外れた関数

2<sup>n</sup> と 2<sup>n/2</sup> は、総当たりより速い方法が無い時の値です。160 ビットを出力する SHA-1 では、2017 年に Google とオランダの研究機関 CWI が約 2<sup>63.1</sup> 回の計算で、内容の違う 2 つの PDF を同じハッシュ値にしました（[SHAttered](https://shattered.io/)）。誕生日攻撃の 2<sup>80</sup> 回より 10 万倍ほど少ない回数です。経緯は [SHA-256](/notes/security/sha-256/) のノートにあります。

一方で、SHA-1 の値から原像を求める現実的な攻撃は公表されておらず、3 つの性質は別々に破られます。MD5 の衝突も、2004 年に Xiaoyun Wang らが[実例](https://eprint.iacr.org/2004/199)を示しています。本記事に出てくる関数で並べると次の通りです。

| 関数 | 出力 | 衝突 | 原像・第二原像 |
| --- | --- | --- | --- |
| MD5 | 128 ビット | 2004 年に実例 | 現実的な攻撃は未公表 |
| SHA-1 | 160 ビット | 2017 年に実例（約 2<sup>63.1</sup> 回） | 現実的な攻撃は未公表 |
| SHA-256・keccak256 | 256 ビット | 近道は未公表 | 近道は未公表 |

NIST（米国国立標準技術研究所）は 2022 年 12 月に、SHA-1 を 2030 年末までに使い終えるよう求めました（[NIST の発表](https://www.nist.gov/news-events/news/2022/12/nist-retires-sha-1-cryptographic-algorithm)）。SHA-256 と keccak256 には、2026 年 11 月の時点でこうした近道は公表されていません。

<br>

衝突耐性が効くのは、攻撃者が 2 つの入力を両方用意できる場面です。[デジタル署名](../digital-signature/)は文書そのものではなくハッシュ値に対して作るので、同じハッシュ値の文書には同じ署名が通ります。2012 年に見つかったマルウェア Flame は、128 ビットのハッシュ関数 [MD5](https://www.rfc-editor.org/rfc/rfc1321) の衝突を使いました。

Microsoft は Terminal Server のライセンス用に、MD5 で署名した[証明書](/notes/security/pki/)を発行していました。Vista より前の Windows ならそのままプログラムの署名に使えましたが、Vista 以降は解釈できない必須の拡張を含むので弾かれます。

攻撃者は、発行を受ける証明書と同じハッシュ値を持ち、プログラムの署名に使える別の証明書を作りました。そのため、Flame のファイルには Microsoft の認証局に連なる正しい署名が付いていました（[MSRC の解説](https://www.microsoft.com/en-us/msrc/blog/2012/06/flame-malware-collision-attack-explained/)）。

<br>

<details>
<summary>Git のコミットの識別子</summary>

開発者が毎日使う [Git](https://git-scm.com/) も、コミットの識別子は SHA-1 です。Git は [2.13 から衝突を検出する SHA-1 の実装](https://git-scm.com/docs/hash-function-transition)に切り替え、SHA-256 のリポジトリも作れるようにしましたが、2026 年 11 月の時点で [git init](https://git-scm.com/docs/git-init) の既定は sha1 のままです。

</details>

<br>

---

### keccak256 と SHA3-256 の違い

[Keccak](https://keccak.team/keccak.html) は NIST の公募で SHA-3 に選ばれた関数で、NIST は 2015 年 8 月に [FIPS 202](https://csrc.nist.gov/pubs/fips/202/final) として標準にしました。その際、入力の後ろに足す区切りのビットが変わりました。Ethereum が採用したのは、変わる前の Keccak-256 です。同じ入力で比べると次のようになります。

{{< figure src="images/padding.webp" alt="空の入力を 136 バイトのブロックに詰めた形の比較。Keccak-256 は先頭が 01、続いて 00 が 134 バイト、最後が 80 で、出力は c5d24601...85a470。SHA3-256 は先頭が 06 で残りは同じ、出力は a7ffc6f8...f8434a。違いは 1 バイトだけだが出力は全く別の値になる" caption="Keccak-256 と SHA3-256 で、最後のブロックを比べる" align="center" >}}

ブロックの長さ 136 バイトは、Keccak が 1 回の置換で取り込む量です。入力の後ろに、Keccak-256 は `01`、SHA3-256 は `06` を置き、ブロック末尾のバイトに `80` を立てます。違うのはこの 1 バイトだけですが、出力は全く別の値になります。図の 2 つの値は、標準ライブラリだけで書いた [keccak.py](lab/keccak.py) で計算しました。SHA3-256 の値は `hashlib.sha3_256` と一致することを `assert` で見ています。

```python
def sponge256(data: bytes, pad: int) -> bytes:
    rate = 136  # 1088 ビット。残りの 512 ビットは外に出さない
    msg = bytearray(data)
    msg.append(pad)  # Keccak-256 は 0x01、SHA3-256 は 0x06
    msg.extend(b"\x00" * (-len(msg) % rate))
    msg[-1] |= 0x80
    s = [0] * 25
    for off in range(0, len(msg), rate):
        for i in range(rate // 8):
            s[i] ^= int.from_bytes(msg[off + 8 * i: off + 8 * i + 8], "little")
        keccak_f(s)
    return b"".join(x.to_bytes(8, "little") for x in s[:4])
```

```text
入力       b'transfer(address,uint256)'
keccak256  a9059cbb2ab09eb219583f4a59a5d0623ade346d962bcd4e46b11da047c9049b
sha3_256   4b40e901eada9ab2d6dfa2a4e5f5088af21b56bb877126cc83f68849c4aa9609
```

[ERC-20](../erc-20/) が定める `transfer` のセレクターは `a9059cbb` で、keccak256 の先頭 4 バイトと一致します。`hashlib.sha3_256` で計算した `4b40e901` を使うと、別の関数を呼ぶか、該当する関数が無いので失敗するか、fallback 関数を持つコントラクトなら fallback が動きます。

Python の標準ライブラリには Keccak-256 が無いので、暗号ライブラリ [PyCryptodome の `Crypto.Hash.keccak`](https://pycryptodome.readthedocs.io/en/latest/src/hash/keccak.html) のような Keccak の名前が付いた実装を使います。どちらを使っているか迷ったら、空の入力を通します。`c5d24601…` が返れば Keccak-256、`a7ffc6f8…` なら SHA3-256 です。

名前で見分けられないのは、Solidity の `keccak256` が古くは `sha3` という名前でも呼べたからです。この別名は Solidity 0.5.0 で使えなくなりました（[0.5.0 の変更点](https://docs.soliditylang.org/en/latest/050-breaking-changes.html)）が、ノードに問い合わせる API である [JSON-RPC の `web3_sha3`](https://ethereum.org/en/developers/docs/apis/json-rpc/) のように名前が残っている所もあります。この API の説明にも、返すのは Keccak-256 で、標準化された SHA3-256 ではないと書かれています。

---

### 秘密を前に付けたハッシュ

API の要求に「秘密の値と本文をつないだもののハッシュ値」を付け、サーバー側で同じ計算をして照合する設計があります。秘密を知らなければ正しい値は作れない、という考えです。ところが SHA-256 では、秘密を知らなくても、本文の後ろに追記した要求の正しい値を作れます。この攻撃を伸長攻撃（length extension attack）と呼びます。

SHA-256 は、入力にパディングを足して 64 バイトのブロックに分け、ブロックを 1 つずつ圧縮関数に通して 32 バイトの内部状態を更新します。最後の内部状態が、そのままハッシュ値になります。パディングは、区切りの `80`、0 の並び、入力の長さで決まります。そのため、ハッシュ値と入力の長さを知っている人は、その値を内部状態として計算を続けられます。

{{< figure src="images/length_extension.webp" alt="上の段はサーバーの計算で、秘密 16 バイト・本文 19 バイト・パディング 29 バイトを圧縮した結果がハッシュ値 c253f0e1... になり、攻撃者にも見える。下の段は攻撃者で、秘密・本文・パディングは計算済みとして飛ばし、c253f0e1... を初期値にして追記 15 バイトとパディング 49 バイトを圧縮する。結果の d273494c... は、サーバーが秘密・本文・パディング・追記をつないで計算する値と同じ" caption="sha256(秘密 ‖ 本文) の値から計算を続ける伸長攻撃" align="center" >}}

図の ‖ は、バイト列をつなぐ記号です。攻撃者は秘密の中身を知りませんが、長さの 16 バイトは知っている前提にしています。長さが分からなくても、候補を順に試せば済みます。以下は、攻撃者がする計算です。`compress` は SHA-256 の圧縮関数を標準ライブラリだけで書いたもので、全体は [length_extension.py](lab/length_extension.py) にあります。

```python
def padding(total_len):
    """SHA-256 が total_len バイトの入力の後ろに足すパディング"""
    return b"\x80" + b"\x00" * ((55 - total_len) % 64) + struct.pack(">Q", total_len * 8)


def extend(tag_hex, known_len, extra):
    """値 tag_hex から計算を再開し、パディングの後ろに extra を足した入力の値を返す"""
    h = list(struct.unpack(">8I", bytes.fromhex(tag_hex)))  # 出力 = 内部状態
    done = known_len + len(padding(known_len))
    data = extra + padding(done + len(extra))
    for off in range(0, len(data), 64):
        h = compress(h, data[off:off + 64])
    return struct.pack(">8I", *h).hex()


# --- 攻撃者側: 本文、その値、秘密の長さ 16 だけを使う ---
tag = sign(body)
extra = b"&amount=1000000"
forged_body = body + padding(16 + len(body)) + extra
forged_tag = extend(tag, 16 + len(body), extra)
```

出力は抜粋で、偽の本文から `\x00` の並びを省いています。

```text
元の本文      b'to=0xA11CE&amount=1'
偽の本文      b'to=0xA11CE&amount=1\x80\x00...\x00\x01\x18&amount=1000000'
sha256 で検証 True
HMAC で検証   False
SHA3 で検証   False
```

`sign` はサーバーの関数で、`sha256(秘密 + 本文)` を返します。偽の本文にはパディングのバイトが混ざりますが、サーバーが後ろの `amount` を採用する作りなら、送金額を書き換えられます。

2009 年には、写真共有サービス Flickr の API が `md5(秘密 + 引数)` で要求に署名させていたため、Thai Duong と Juliano Rizzo が[この方法で署名を偽造できること](https://vnhacker.blogspot.com/2009/09/flickrs-api-signature-forgery.html)を報告しました。MD5 も、SHA-256 と同じく内部状態をそのまま出力する作りです。

<br>

対策は、秘密と本文から値を作る専用の方法である [HMAC](https://www.rfc-editor.org/rfc/rfc2104)（Hash-based Message Authentication Code）を使うことです。HMAC は秘密を混ぜたハッシュをもう一度ハッシュで包むので、外に出た値から内側の計算を続けられません。上の出力の「HMAC で検証」の行の通り、同じ追記は通りませんでした。

Keccak と SHA3-256 では、この攻撃が成り立ちません。内部状態は 1,600 ビットあり、出力に使うのは先頭の 256 ビットだけなので、残りの 1,344 ビットは外に出ません。中でも `sponge256` のコメントで「外に出さない」と書いた 512 ビットは、出力を何ブロック取り出しても現れないので、出力から内部状態を組み立てられません。

[Keccak の設計者](https://keccak.team/keccak_strengths.html)も、伸長攻撃の弱点が無いので、秘密を前に付けるだけで HMAC と同じ役目を果たせると説明しています。それでも、使う関数を後から SHA-256 に替える可能性があるなら、最初から HMAC にしておく方が安全です。

---

### ハッシュ値に出会った時

コードやコントラクトでハッシュ値に出会ったら、まずどの関数かを見ます。名前に `sha3` と付いていても、Ethereum の周りでは Keccak-256 のことが多くあります。空の入力を通せば見分けられます。

次に、何ビットで比べているかと、入力を誰が選べるかを見ます。攻撃者が入力を 2 つとも選べるなら 2<sup>n/2</sup> 回、決まった値に当てるなら 2<sup>n</sup> 回で見積もります。32 ビットはどちらでも手元の PC で終わります。160 ビットの衝突は、EIP-3607 が 2021 年に出した見積もりで、約 100 億ドルの機材と 1 年ほどあれば見つかる回数です。

呼び出しを許すかどうかの判断に、ハッシュ値の一致を使っていないかも見ます。Poly Network では、セレクターが合ったことで特権を持つ関数が呼ばれました。秘密の値と組み合わせて要求を守る時は、自分で連結せずに HMAC を使います。

冒頭に載せた図で赤と青が離れているのは、同じ keccak256 を 32 ビットに切った値でも、攻撃者が何を選べるかで必要な回数が 5 万倍変わるからです。長さが 256 ビットなら、この差は 2<sup>128</sup> 倍ほどに開きます。新しくハッシュ値を比べるコードを書く時は、その値がどちらの線の上にあるかを先に決めてください。
