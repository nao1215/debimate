---
title: "Bitcoin Script - 署名を求めない条件は、mempool を見た誰でも使える"
date: 2026-08-10
draft: false
series: ["技術ノート", "Blockchain Systems"]
tags: ["blockchain-systems", "bitcoin"]
weight: 6
wrapTables: true
topics: ["Transaction / Wallet"]
---

Bitcoin Script は、[Bitcoin](https://bitcoin.org/) のトランザクションが作る出力に「このコインを次に使える条件」を書くための、スタックで動く小さな言語です。トランザクションは送金 1 回分の記録で、ネットワークに参加するコンピュータであるノードが検証して中継し、ブロックという単位にまとめてチェーンに記録します。

コインを使う側は条件を満たすデータを添えて送り、各ノードはそのデータと条件を一緒に実行して、最後に真が残れば使って良いと判定します。

次の条件を書いた出力に、1 BTC を送ったとします。`<H>` は、ある値を [SHA-256](/notes/security/sha-256/) に掛けたハッシュ値です。ハッシュ値の元になった値をプリイメージ（preimage）と呼びます。

```text
OP_SHA256 <H> OP_EQUAL
```

この条件は「添えた値の SHA-256 が H と等しければ使える」という意味です。プリイメージを知っている Bob が、このコインを自分宛てに送るトランザクションをネットワークに流しました。このトランザクションがブロックに入るまでの間に、何が起きるでしょうか。

<br>

自分の PC だけで動く Bitcoin のネットワークを regtest と呼びます。手元の regtest で試すと、Bob は受け取れませんでした。ブロックに入る前のトランザクションは、各ノードの mempool という置き場で待ち、誰でも中身を読めます。0.5 秒ごとに mempool を読んでいた監視プログラムが、Bob のトランザクションからプリイメージをコピーし、宛先だけを自分に変えて送り直しました。

ブロックを作る側は手数料の高いトランザクションを選んで入れるので、ノードは同じコインを使うトランザクションが 2 つ届くと、手数料の高い方で置き換えます。そのため、手数料を 10 倍にした監視プログラムのトランザクションが Bob のものを置き換え、5 秒後のブロックに入りました。図の sat は satoshi の略で、1 億分の 1 BTC です。

{{< figure src="images/script_race.webp" alt="上下 2 段の動画。上の条件 A（OP_SHA256 <H> OP_EQUAL）では、0.06 秒に Bob 宛てのトランザクション（手数料 1,000 sat）が mempool に入り、0.64 秒に監視プログラム宛て（手数料 10,000 sat）が入って Bob 宛ては置き換えられる。5.2 秒のブロックには監視プログラム宛てが入り、監視プログラムが 0.9999 BTC を受け取る。下の条件 B（プリイメージと Bob の署名を求める）では、0.58 秒に監視プログラム宛てが署名が合わずに拒否され、5.1 秒のブロックには Bob 宛てが入って Bob が 0.99999 BTC を受け取る" caption="監視プログラムが Bob の送金をコピーした時、ブロックに入ったトランザクション（regtest で実測した時刻を 0.5 倍速で再生）" align="center" >}}

下段の条件 B は、同じプリイメージに加えて Bob の署名を求めます。監視プログラムが同じことをしても、そのトランザクションはノードに受け付けられず、ブロックには Bob のものが入りました。違いは条件に署名の検査があるかどうかだけです。

この挙動は実験の中だけの話ではありません。例えば、2013 年に置かれた「SHA-1 で衝突を見つけた人への懸賞」では、2017 年に解かれた後も、同じ解答で少額を引き出す送金が 2023 年まで続きました。2024 年には、署名を求める条件でも鍵を推測できたために、鍵の範囲を絞った懸賞（puzzle #66）の 6.6 BTC が、解いた人とは別の宛先に渡ったと報告されています。

ハッシュ値で鍵を掛ける条件や懸賞、複数人の署名などの条件を自分で書く開発者は、この差を知っておく必要があります。

<br>

本記事では、次の問いに沿って Bitcoin Script の仕組みを説明します。

- スクリプトはどこに書かれ、ノードはどう実行するのか。
- なぜプリイメージは盗めて、署名があると盗めないのか。
- 実際のチェーンでは、同じ解答の使い回しがどれだけあったのか。
- ブロックに入れられる条件をノードが拒否するのはいつか。
- P2SH・P2WSH・P2TR は、条件の何を後から見せるのか。
- Script で書けない条件は何で、Ethereum と何が違うのか。

---

### 出力に書く条件と、使う時に添えるデータ

Bitcoin のコインは、過去のトランザクションが作った出力として記録されています。[出力](https://developer.bitcoin.org/devguide/transactions.html)は金額と使う条件の組で、まだ使われていない出力を [UTXO](../utxo/) と呼びます。コインを使うトランザクションは、入力で「どの出力を使うか」を指し、その出力の条件を満たすデータを添えます。

条件は、ノードのプログラムに埋め込まれているのではなく、出力のデータとして記録されています。ノードが持つのは「スクリプトを実行して結果を見る」という枠組みだけです。そのため、署名 1 つの条件も、複数人の署名や期限付きの条件も、ノードを書き換えずに同じ枠組みで表せます。

出力に書く条件をロックスクリプト（scriptPubKey）、使う側が添えるデータをアンロックスクリプト（scriptSig）と呼びます。2017 年に有効になった [SegWit](https://github.com/bitcoin/bips/blob/master/bip-0141.mediawiki)（Segregated Witness）以降の形式では、添えるデータは scriptSig ではなく、入力ごとの witness という別の欄に入ります。冒頭の実験も witness を使っています。witness が txid に入らない理由は [Bitcoin Merkle Tree](../bitcoin-merkle-tree/) で扱っています。

Script には変数がありません。命令は 1 つずつ左から実行され、データはスタックに積まれます。`<H>` のようなデータはそのまま積まれ、`OP_` で始まる命令はスタックの上から値を取り出して、結果を積み直します。冒頭の条件 B を実行すると、スタックは次のように変わります。

{{< figure src="images/script_stack.webp" alt="6 列の図。実行前のスタックは下から署名、プリイメージ。OP_SHA256 で一番上が SHA-256 の結果に変わる。<H> で出力の H が積まれる。OP_EQUALVERIFY で 2 個を比べて取り除き、署名だけが残る。<公開鍵> で Bob の公開鍵が積まれる。OP_CHECKSIG で署名を検証し、1（真）が残る。プリイメージが違えば 4 列目、署名が違えば 6 列目で失敗する" caption="条件 B（OP_SHA256 <H> OP_EQUALVERIFY <公開鍵> OP_CHECKSIG）を実行した時のスタック" align="center" >}}

`OP_EQUALVERIFY` は 2 個の値を比べ、違えばその場でスクリプトを失敗させます。`OP_EQUAL` は失敗させずに真偽を積むだけなので、条件 A では比べた結果がそのまま最後の判定になります。`OP_CHECKSIG` は、署名がこの公開鍵で作られ、しかも今のトランザクションに対するものかを検証します。[デジタル署名](../digital-signature/)の検証そのものです。

<br>

古くから使われてきた条件も、同じ 2 段の検査でできています。P2PKH（Pay to Public Key Hash）と呼ばれる形の条件は次の通りです。

```text
OP_DUP OP_HASH160 <公開鍵のハッシュ 20 バイト> OP_EQUALVERIFY OP_CHECKSIG
```

使う側は署名と公開鍵を添えます。`OP_DUP` で公開鍵を複製し、`OP_HASH160`（SHA-256 の後に [RIPEMD-160](https://homes.esat.kuleuven.be/~bosselae/ripemd160.html)）を掛けて出力の 20 バイトと比べ、残った公開鍵で署名を検証します。

複製するのは、`OP_HASH160` が公開鍵をハッシュ値に置き換えてしまい、署名の検証に使う分が無くなるからです。条件 B の「プリイメージの SHA-256 と H を比べる」所が「公開鍵のハッシュと出力の値を比べる」に替わっただけです。P2PKH のアドレスは、この 20 バイトを符号化した文字列です。ハッシュ値の作り方は [Hash Function](../hash-function/) で扱っています。

<br>

他人の公開鍵をコピーして添えると、ハッシュ値の比較は通ります。しかし、その公開鍵に対応する秘密鍵が無ければ正しい署名を作れず、`OP_CHECKSIG` で偽が残ります。公開鍵を知ることと、その出力を使えることは別です。

<br>

#### 繰り返しの無い言語

Script には後ろへ戻る命令がありません。`OP_IF` のような分岐はあり、例えば [BIP-65](https://github.com/bitcoin/bips/blob/master/bip-0065.mediawiki) の `OP_CHECKLOCKTIMEVERIFY` は、指定した時刻やブロック高より後かを見る命令です。分岐とこの命令を組み合わせると、「期限前は 2 人の署名、期限後は 1 人の署名」のような条件を書けます。しかし、どの命令も 1 回しか実行されないので、繰り返しは書けません。

これは意図した制限で、[Bitcoin Wiki](https://en.bitcoin.it/wiki/Script) も、繰り返しを書けないことを意図的な設計として説明しています。全てのノードは、見知らぬ相手が書いたスクリプトを実行する立場にあります。停止しないスクリプトや、実行の手間が際限なく膨らむスクリプトを書けると、トランザクションの検証そのものが攻撃の入り口になります。繰り返しが無いことに加え、命令の数や署名を検証する回数に上限があるので、ノードは実行の手間を前もって見積もれます。

<br>

#### 2 つのスクリプトを別々に実行する

Bitcoin の主な実装である Bitcoin Core では、今の [`VerifyScript`](https://github.com/bitcoin/bitcoin/blob/v32.1/src/script/interpreter.cpp#L2012) は、使う側のデータを先に実行し、残ったスタックの上で出力の条件を実行します。この手順は scriptSig を使う従来の形式に当てはまり、冒頭の実験で使った P2WSH の手順は後の節で説明します。

スクリプトが通っても、それだけでトランザクションが有効になるわけではありません。使う出力がまだ使われていないか、金額が合っているかなどの検査は別に行われます。

2 つを 1 本のスクリプトにつないで実行しない形には、初期の実装で見つかった穴が関わっています。`VerifyScript` のコメントは、[つながずに同じスタックで順に実行する理由](https://github.com/bitcoin/bitcoin/blob/v32.1/src/script/interpreter.cpp#L2026-L2027)として、次の CVE-2010-5141 を挙げています。

0.3.4 までの実装は、scriptSig と scriptPubKey をつないで 1 回で実行していました（[0.3.3 のソース](https://github.com/bitcoin/bitcoin/blob/v0.3.3/script.cpp)）。つなぎ目には `OP_CODESEPARATOR` という区切りの命令が入ります。署名の対象にする範囲の始まりを記録するだけの命令で、スタックは変えません。しかも当時の `OP_RETURN` は「スクリプトの末尾へ飛ぶ」命令でした。

使う側が `OP_1 OP_RETURN` を添えると、1 を積んだ直後に末尾へ飛び、出力の条件は実行されないまま、真が残って成功します。どの出力でも使えてしまう不具合で、2010 年 7 月に試験用のネットワークで見つかり、[CVE-2010-5141](https://en.bitcoin.it/wiki/Common_Vulnerabilities_and_Exposures#CVE-2010-5141) として記録されています。本番のネットワークで悪用された記録はありません。

{{< figure src="images/script_concat.webp" alt="上の段は 0.3.4 まで。OP_1、OP_RETURN、OP_CODESEPARATOR、<公開鍵>、OP_CHECKSIG が 1 列に並び、OP_RETURN から末尾へ赤い矢印が飛んで、点線の 3 つの命令は実行されず、残ったスタック [1] で成功する。下の段は 0.3.7 以降。OP_1、OP_RETURN だけを実行し、0.3.5 から失敗する命令になった OP_RETURN で失敗する。出力の条件は、使う側の命令に飛ばされず必ず実行される" caption="0.3.4 までの実行と今の実行" align="center" >}}

この不具合は 0.3.5 で修正され、[0.3.6 のソース](https://github.com/bitcoin/bitcoin/blob/v0.3.6/script.cpp)では `OP_RETURN` はスクリプトを失敗させる命令になっています。さらに [0.3.7](https://github.com/bitcoin/bitcoin/blob/v0.3.7/script.cpp) で、2 つを別々に実行する `VerifyScript` が入りました。当時の実行順だけを取り出した模型で、使う側のデータごとの結果を並べると次の通りです。

```text
scriptSig                 <=0.3.4 joined  0.3.6 joined  >=0.3.7 separate
owner: sig-by-owner                 True          True              True
attacker: OP_1 OP_RETURN            True         False             False
```

<br>

<details>
<summary>上記の出力を作った模型のコード（Python の標準ライブラリだけ。Bitcoin の実装ではない）</summary>

`OP_CHECKSIG` は、決めた文字列だけを正しい署名とみなす作り物です。見たいのは命令をどの順で実行するかだけなので、署名の計算は省いています。ファイルは [concat_bug.py](lab/concat_bug.py) です。

```python
VALID_SIG = 'sig-by-owner'   # the stub OP_CHECKSIG accepts only this


def run(script, stack, return_jumps):
    pc = 0
    while pc < len(script):
        op = script[pc]
        if op == 'OP_1':
            stack.append(1)
        elif op == 'OP_RETURN':
            if return_jumps:
                pc = len(script)          # 0.3.4 and earlier: skip to the end
                continue
            return False                  # 0.3.6 and later: fail
        elif op == 'OP_CODESEPARATOR':
            pass
        elif op == 'OP_CHECKSIG':
            pub, sig = stack.pop(), stack.pop()
            stack.append(1 if (sig, pub) == (VALID_SIG, 'owner-pubkey') else 0)
        else:
            stack.append(op)              # data push
        pc += 1
    return True


def joined(sig, pub, return_jumps):
    stack = []
    ok = run(sig + ['OP_CODESEPARATOR'] + pub, stack, return_jumps)
    return ok and bool(stack) and stack[-1] == 1


def separate(sig, pub):
    stack = []
    if not run(sig, stack, return_jumps=False):
        return False
    if not run(pub, stack, return_jumps=False):
        return False
    return bool(stack) and stack[-1] == 1
```

</details>

<br>

---

### コピーで使える条件と使えない条件

冒頭の実験は、[Bitcoin Core 32.1](https://bitcoincore.org/en/download/) の regtest を外部と通信しないコンテナの中で動かし、Python から RPC（Remote Procedure Call）で操作しました。

RPC は、ノードに残高の照会やトランザクションの送信を頼むための API です。条件は、条件のハッシュ値だけを出力に置く P2WSH という形の出力に入れました（後の節で説明します）。Bob と監視プログラムの鍵は、その場で作った使い捨てです。

監視プログラムの処理は、mempool を 0.5 秒ごとに読み、狙っている出力を使うトランザクションを見つけたら、witness をそのままコピーして出力だけを自分宛てに変えるものです。以下は [script_race.py](lab/script_race.py) からの抜粋で、`spend` は 1 入力 1 出力のトランザクションを組み立てる補助関数です。

```python
hashlock = b'\xa8' + push(sha256(secret)) + b'\x87'          # OP_SHA256 <H> OP_EQUAL
hashsig = (b'\xa8' + push(sha256(secret2)) + b'\x88'         # OP_SHA256 <H> OP_EQUALVERIFY
           + push(pubkey(d)) + b'\xac')                      # <Bob pubkey> OP_CHECKSIG

# watcher: read the mempool every 0.5 s
for mtxid in cli('getrawmempool'):
    tx = cli('getrawtransaction', mtxid, True)
    vin = tx['vin'][0]
    wit = vin.get('txinwitness', [])
    if vin.get('txid') != txid or not wit or wit[-1] != script.hex():
        continue
    # copy every witness item Bob revealed, change only the output
    w_fee = 10_000
    w_raw = spend(txid, vout, value - w_fee, w_spk, [bytes.fromhex(x) for x in wit])
    res = cli('sendrawtransaction', w_raw, ok=False)
```

結果は冒頭の図で示した通りです。条件 A では、監視プログラムは Bob が送ってから 0.58 秒後に置き換えを送り、ノードはそれを受け付けました。Bob のトランザクションは置き換えを許すという合図（[BIP-125](https://github.com/bitcoin/bips/blob/master/bip-0125.mediawiki) の合図）を出していませんでしたが、それでも置き換えられています。

Bitcoin Core は [28.0](https://bitcoincore.org/en/releases/28.0/) で、合図の無いトランザクションも手数料が高ければ置き換える設定を既定にし、[29.0](https://bitcoincore.org/en/releases/29.0/) でこの設定を外せないようにしました。

条件 B では、監視プログラムのトランザクションは次のエラーで拒否されました。

```text
mempool-script-verify-flag-failed (Signature must be zero for failed CHECK(MULTI)SIG operation), input 0 of 4e2bc27a…
```

署名の検証に失敗したことを表すエラーです。プリイメージはコピーできても、コピーした署名が監視プログラムのトランザクションに合わないからです。

<br>

#### 署名が覆う範囲

署名が合わなくなるのは、署名がトランザクションの中身に対して作られるからです。SegWit の入力では、[BIP-143](https://github.com/bitcoin/bips/blob/master/bip-0143.mediawiki) の手順で、使う出力の参照・金額・条件の本体・全ての出力などからハッシュ値を作り、そのハッシュ値に署名します。条件の本体は witness の最後に置かれますが、scriptCode という名前でこの計算に入ります。署名とプリイメージは、この計算に入りません。

どの入力・出力を対象に含めるかは sighash type という指定で変えられ、実験では全てを含める SIGHASH_ALL を使いました。sighash type は [Digital Signature](../digital-signature/) で説明しています。

{{< figure src="images/script_sighash.webp" alt="左が Bob が送ったトランザクション、右が監視プログラムが作り直したもの。どちらも入力（使う出力 txid:0 と金額 1 BTC）、witness の最後の要素（条件の本体、scriptCode として計算に入る）、witness の残り（署名、プリイメージ）、出力の 4 段。左の入力・条件の本体・出力には「署名が覆う」の括弧、署名とプリイメージには「覆わない」の表示。witness は右へそのままコピーされ、出力は Bob 宛て 0.99999 BTC から監視プログラム宛て 0.9999 BTC に書き換えられる。下に、出力が変わったのでコピーした署名は検証に失敗する、条件 A には署名が無いので出力を変えても検査は全て通る、の注記" caption="署名が覆う範囲と、監視プログラムが書き換えた所" align="center" >}}

上記の図のように、監視プログラムが書き換えたのは出力だけです。条件 B では、出力が変わったことで署名するハッシュ値が変わり、Bob の署名は検証に失敗します。条件 A には署名の検査がありません。条件が見ているのは「H になる値を出したか」だけで、「誰が出したか」も「どこへ送るか」も見ていないので、書き換えたトランザクションも条件を満たします。

つまり、プリイメージのように使う時に明かすしかない値は、明かした瞬間から全員が知る値になります。mempool のトランザクションは、ノードを動かしている誰でも読めます。署名を求めない条件は、プリイメージを最初に明かした人ではなく、そのプリイメージで一番高い手数料を払った人が使える条件だと考える必要があります。

極端な例は常に真を返す条件で、明かす値すら無いので誰でも使えます。出力に置いた条件は後から変えられないので、このような条件に送ったコインは取り戻せません。

[Lightning Network](../lightning-network/) の HTLC（Hashed Time Locked Contract）がプリイメージに加えて受取側の署名を求めるのも、この理由です。Ethereum でも、mempool で読んだ値を使って前に割り込む先回り（front-running）が起き、その対策が [Commit-Reveal](../commit-reveal/) や [MEV](../mev/) で扱う話になります。

---

### 公開された解答を使い回した送金

2013 年 9 月、Bitcoin の開発者 Peter Todd は、SHA-1・SHA-256・RIPEMD-160 などで[衝突を見つけた人へ向けた懸賞](https://gnusha.org/pi/bitcoindev/20130913060758.GC4242@savin/T)を出しました。懸賞のコインは、条件のハッシュ値を出力に置く P2SH という形の出力として置かれています。P2SH は後の節で P2WSH と並べて説明します。SHA-1 に向けた懸賞は、次の条件です。

```text
OP_2DUP OP_EQUAL OP_NOT OP_VERIFY OP_SHA1 OP_SWAP OP_SHA1 OP_EQUAL
```

「異なる 2 つの値で、SHA-1 が等しいものを出せば使える」という意味で、署名の検査はありません。2017 年 2 月 23 日に Google などが [SHA-1 の衝突](https://shattered.io/)を公表し、同じ日のうちに懸賞の 2.49 BTC が引き出されました。

<br>

この話には続きがあります。解答（衝突する 2 つの値）がブロックに記録された後も、この宛先にはコインが送られ続け、そのたびに引き出されました。公開の API でこの宛先の履歴を取ると、次の通りです。

```text
block_time_utc       height  inputs  spent_sat  fee_sat  txid / to
2017-02-23 13:08   454316      10  249153717  1153717  8d31992805518fd6… -> 1EohDhHJT9byKsYhxp5zX6PNkuGhxoEu9r
2017-02-24 03:18   454410       1     100000    20000  709a2cb2f28a15bf… -> p2pk
2017-02-24 22:05   454542       1     250000   125000  61c7144af53cccc0… -> 15jF2i4s4iygCaJwXsWvLt9XeEWW7bWTsR
2017-02-26 16:52   454848       1     100000     3701  31206bcaca9dbf57… -> 3LdEFWVCRky47pVNN824gYgaYwV9S4KzFv
2023-02-22 10:11   777779       1      26400     3695  d0c4aca857939daa… -> bc1qy0zqffuqkxxtrc9ylz6ysm7wjv2cpatc784ug8
2023-02-22 23:00   777856       1       9600     1478  9ec2a0db0c4c3423… -> bc1q49hwsxxtufpn2pvg9nfds3s5wrk5vrl72vxtp0
spent inputs: 23, distinct scriptSig: 1, scriptSig bytes: 655
```

上記は 14 件のうち宛先ごとに 1 件を抜き出したもので、全件は [sha1_bounty.txt](lab/output/sha1_bounty.txt)、取得のコードは [sha1_bounty.py](lab/sha1_bounty.py) にあります。txid はトランザクションの識別子、to は引き出した先のアドレスです。p2pk はアドレスを使わず公開鍵へ直接送る古い形の出力です。

<br>

この宛先にコインが送られるたびに出力が 1 個でき、inputs は 1 件の送金がまとめて使った出力の数です。最初の 1 件はそれまでに溜まった 10 個をまとめて引き出しているので、14 件で 23 個になります。23 個の入力は全て同じ 655 バイトの scriptSig で引き出されていて、宛先は少なくとも 6 通りあります。

宛先の数が人数と同じとは言えませんが、最初に解いた人以外も同じ解答で引き出せたことは、チェーンの記録だけで分かります。2023 年に送られた 2 件も、6 日後と 13 日後に引き出されました。

<br>

#### 鍵を推測できた懸賞

署名がある条件でも、鍵が推測できれば同じことが起きます。puzzle #66 は、P2PKH の出力に置かれた懸賞です。#N の秘密鍵が N ビットの数であることは、2015 年に立った [bitcointalk のスレッド](https://bitcointalk.org/index.php?topic=1306983.0)で参加者が見抜いており、#66 の鍵も 2 の 66 乗より小さい数でした。P2PKH の出力にあるのは公開鍵のハッシュ値だけで、公開鍵は使う時に初めて見えます。

公開鍵が見えない間は、候補の鍵を 1 つずつハッシュに掛けて比べるしかなく、解くまでに長い時間が掛かります。一方、公開鍵が分かれば、範囲の狭い秘密鍵は短時間で求められます。この懸賞は、2024 年 9 月に 6.6 BTC が引き出され、[Hacker News](https://news.ycombinator.com/item?id=41547395) で 437 points（2026-11-13 時点）を集めました。

議論で説明されている流れは、解いた人の送金で公開鍵が mempool に出て、範囲の狭い鍵が公開鍵から短時間で求められ、手数料を上乗せした置き換えが先にブロックに入った、というものです。半年前の 2024 年 4 月には、まさにこの流れを心配する [Issue](https://github.com/bitcoin/bitcoin/issues/29793) が Bitcoin Core に立っていました。署名が守るのは、鍵を推測できない時だけです。

---

### ノードが拒否する正しいスクリプト

ここまでの条件 A は、P2WSH の形で出力に置きました。同じ `OP_SHA256 <H> OP_EQUAL` をハッシュに入れず、そのまま出力の scriptPubKey に書くとどうなるかも試しました。

| 出力の書き方 | `testmempoolaccept` | `generateblock` でブロックに入れる |
| --- | --- | --- |
| 条件をそのまま出力に書く | 拒否（`scriptpubkey`） | 入る |
| P2WSH の形にする | 受け付ける | 入る（冒頭の実験で送金に使用） |

`testmempoolaccept` は、そのトランザクションを mempool に入れるかどうかの判定だけをノードに頼む RPC で、実際には入れません。条件をそのまま書いた出力は `scriptpubkey` という理由で拒否されました。一方で、`generateblock` で直接ブロックに入れると、そのブロックは有効と判定されました。

ブロックに入れて良いかを決める規則（consensus rule）と、各ノードが中継や mempool に入れる時に足す規則（policy、ポリシー）は別物です。Bitcoin Core のポリシーは、P2PKH・P2WSH・P2TR などの決まった形の出力だけを標準とみなし、それ以外の形で出力を作るトランザクションは中継しません。

自分で条件を書く時は、条件を P2WSH や P2TR の形にするのが普通の書き方です。2 つの規則の違いと、ポリシーで拒否されたトランザクションの行方は [Mempool](../mempool/) で扱っています。

---

### 条件を後から見せる P2SH・P2WSH・P2TR

条件をハッシュ値にして出力に置く形は、送る側の手間を減らすために作られました。条件をそのまま出力に書くと、送る側は受け取る側の長い条件を受け取り、そのサイズ分の手数料を払うことになります。

P2SH では、受け取る側がアドレスとして渡すのは条件のハッシュ値だけで、出力は `OP_HASH160 <条件のハッシュ値> OP_EQUAL` だけになります。条件の本体は使う時に添え、ノードは本体のハッシュ値が出力と一致することを見てから本体を実行します。P2SH は条件を縮める仕組みではありません。長い条件を載せる手数料は、送る側ではなく、使う時に受け取る側が払うことになります。主な形を並べると次の通りです。

| 形 | 出力に置くもの | 使う時に見せるもの | 有効になった時期 |
| --- | --- | --- | --- |
| P2PKH | 公開鍵のハッシュ | 公開鍵と署名 | 最初から |
| [P2SH](https://github.com/bitcoin/bips/blob/master/bip-0016.mediawiki)（BIP-16） | 条件のハッシュ（20 バイト） | 条件の本体と、満たすデータ | 2012 年 4 月 |
| [P2WSH](https://github.com/bitcoin/bips/blob/master/bip-0141.mediawiki) | 条件のハッシュ（32 バイト） | 同上（witness に置く） | 2017 年 8 月 |
| [P2TR](https://github.com/bitcoin/bips/blob/master/bip-0341.mediawiki) | 公開鍵 1 個 | 署名か、使った分岐の本体 | 2021 年 11 月 |

P2WSH では、出力は `OP_0 <条件のハッシュ値>` で、scriptSig は空です。ノードは、witness の最後に置かれた条件の本体がこのハッシュ値と一致するかを見てから、残りの witness を積んだスタックで本体を実行します。先に見た、scriptSig の後に出力の条件を実行する手順とは別の経路です。

P2TR（Pay to Taproot）は、普段は 1 個の鍵で作った署名だけで使え、条件の分岐を使う時も、使った分岐の本体だけを見せます。複数の署名を求める条件を P2WSH と P2TR で書き比べた実験は [Multisig](../multisig/) にあります。

<br>

どの形でも、使う時に条件の本体と満たすデータは公開されます。ハッシュ値で隠せるのは「使うまでの間」だけです。SHA-1 の懸賞も P2SH で置かれていましたが、使う時に条件の本体と解答を見せる点は変わらず、一度見せた解答はその後も使い回されました。どの形を選ぶかと、条件に署名を入れることは、別々に決める必要があります。

---

### Script で書けない条件

Script の命令は、スタックの値と、署名の検査を通じたトランザクションの中身しか扱えません。次のような条件は書けません。

- 同じ処理の繰り返し（後ろへ戻る命令が無い）
- 実行をまたいで残る値（残高・回数などの状態）
- 新しい出力の宛先や金額への制限

3 つ目は、条件 A の問題に関わります。「このコインは Bob のアドレスにしか送れない」という条件を Script だけで書ければ、監視プログラムが宛先を変えても失敗させられます。しかし、Script の命令は出力の中身を直接読めないので、宛先を縛るには署名を使うしかありません。

出力の中身を条件に使えるようにする仕組みは covenant と呼ばれ、その材料になる提案として、[BIP-119](https://github.com/bitcoin/bips/blob/master/bip-0119.mediawiki) の `OP_CHECKTEMPLATEVERIFY` や、[BIP-347](https://github.com/bitcoin/bips/blob/master/bip-0347.mediawiki) の `OP_CAT` があります。[Bitcoin Core 32.1 の実装](https://github.com/bitcoin/bitcoin/blob/v32.1/src/script/interpreter.cpp#L467-L482)では、`OP_CAT` は使えない命令のままです。

[Ethereum](https://ethereum.org/) の[スマートコントラクト](../smart-contract/)は、状態を持ち、繰り返しも書けます。その代わりに、実行の手間を [gas](../gas-eip-1559/) で数えて手数料を払い、途中で失敗してもブロックに入って手数料を払う作りになっています。失敗したトランザクションをどう扱うかの違いは、[Ethereum のトランザクション](../ethereum-transaction/)で比べています。Bitcoin は、書ける条件を絞ることで、実行が必ず終わり、出力ごとに独立して検証できる作りを選んでいます。

---

### 条件を書く前に

冒頭の動画で上と下の結果を分けたのは、同じプリイメージを使う条件に、署名の検査があるかどうかだけでした。Bitcoin で自分の条件を書く時は、最初に条件の分岐を 1 つずつ書き出し、それぞれで誰の署名を求めるかを見ます。署名の無い分岐があれば、mempool を見た誰でも使える分岐だと考えます。

次に、求める署名の鍵が推測できない作り方の鍵かを見ます。puzzle #66 のように範囲の狭い鍵は、公開鍵を見せた時点で守れなくなります。使う時に明かすプリイメージも同じで、明かした後は使い回される値として扱い、別の出力に同じ値を使いません。

<br>

最後に、条件を P2WSH か P2TR の形にし、regtest の `testmempoolaccept` でポリシーに通るかを見てから、本番の資金を送ります。冒頭の実験は [run.sh](lab/run.sh) で再現でき、手順は [README.txt](lab/README.txt) にあります。自分の条件でも、鍵を持たない監視プログラムのトランザクションを regtest で送ってみると、どの検査が何を守っているかが、動かすと分かります。
