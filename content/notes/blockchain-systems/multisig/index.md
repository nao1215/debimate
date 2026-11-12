---
title: "Multisig - 複数の鍵で承認する仕組み"
date: 2026-11-10
draft: false
series: ["技術ノート", "Blockchain Systems"]
tags: ["blockchain", "bitcoin", "multisig", "musig2", "wallet", "security"]
weight: 18
wrapTables: true
topics: ["Transaction / Wallet"]
---

マルチシグ（multisig、multi-signature）は、登録した n 個の鍵のうち m 個の署名が揃った時だけ資産を動かせるようにする仕組みです。「3 個のうち 2 個」なら 2-of-3 と書きます。1 個の鍵を盗まれても送金されず、1 個を失くしても残りの 2 個で資産を動かせます。

使われる場面の代表は、取引所や団体が大きな資産を預かる口座です。担当者 1 人の端末が乗っ取られただけで全額が動く構成は避けたいものの、全員の同意を必須にすると、1 人が鍵を失くした時に資産が動かせなくなります。個人でも、普段の端末・予備の端末・離れた場所の保管用に鍵を分ける用途があります。

{{< figure src="images/multisig_concept.webp" alt="3 列の図。各列の上に署名者 A・B・C の丸が並ぶ。左の列 Bitcoin P2WSH では青いスクリプトの箱が 2-of-3 を検査し、チェーンに残るものは署名 2 個・鍵 3 個。中央の列 Ethereum Safe では黄土色のコントラクトの箱が必要数 2 を検査し、チェーンに残るものは署名 2 個・アドレス 3 個。右の列しきい値署名（MPC）では破線のオフチェーンの箱で署名者が協力し、チェーンに残るものは署名 1 個・鍵 1 個だけ" caption="3 つのやり方で、2-of-3 の規則を検査する場所とチェーンに残るもの" align="center" >}}

上記の図の通り、同じ「3 人のうち 2 人で承認する」構成でも、規則を検査する場所とチェーンに残るものはやり方ごとに違います。Bitcoin では出力に付けたスクリプト（Script）が、Ethereum ではコントラクト（contract）が必要数（threshold）の署名を数えます。どちらもチェーンに署名 2 個と 3 人分の鍵（Safe では所有者のアドレス）が残ります。

後の節で扱うしきい値署名（threshold signature）では、署名者がオフチェーン（off-chain）で協力して 1 個の署名を作るので、チェーンからは 1 人の送金と区別できません。全員の署名が要る場合に限って同じことができる MuSig2 という手順もあり、こちらも後で扱います。

<br>

本記事では、Bitcoin のマルチシグを中心に、m と n が何に備える数なのか、スクリプトが署名をどう数えるのか、署名を 1 個にまとめる MuSig2 や MPC と何が違うのかを説明します。説明の要所は、手元の検証用チェーンで確認します。Ethereum のコントラクトで署名を数える Safe は、[Safe](../safe-multisig/) のノートで扱います。

ウォレットの全体像と鍵の保管は [Wallet](../wallet/)、スクリプトの実行は [Bitcoin Script](../bitcoin-script/)、署名の基礎は [Digital Signature](../digital-signature/) を前提にします。

---

### マルチシグが必要な理由

鍵が 1 個だけのアカウントには、壊れ方が 2 つあります。鍵を盗まれれば攻撃者が送金でき、鍵を失くせば本人も送金できません。m-of-n は、この 2 つに別々の数で備えます。攻撃者は m 個の鍵を盗む必要があり、持ち主は n − m 個まで鍵を失っても資産を動かせます。

| 構成 | 盗まれても耐える鍵の数（m − 1） | 失くしても耐える鍵の数（n − m） |
| --- | --- | --- |
| 1-of-1（通常の鍵） | 0 | 0 |
| 2-of-2 | 1 | 0 |
| 2-of-3 | 1 | 1 |
| 3-of-5 | 2 | 2 |

例えば、[Lightning Network](../lightning-network/) のチャネルは 2-of-2 です。2 人の合意が無ければ資金が動かないことが目的で、相手が応答しなくなった時の備えは、マルチシグとは別に用意します。

<br>

表の数は、鍵がそれぞれ別の場所にある時だけ成り立ちます。3 個の鍵を同じ PC に置けば、その PC が乗っ取られた時点で 3 個とも盗まれ、実質は 1-of-1 です。同じ紙に復元フレーズを書き並べた場合も、同じ金庫に入れた場合も同じです。鍵を分ける軸には、端末（PC・スマートフォン・ハードウェアウォレット）、人（担当者）、場所（自宅・別の拠点）があり、1 つの故障や侵害で m 個が同時に失われない配置を選びます。

---

### Bitcoin の OP_CHECKMULTISIG

Bitcoin の資産は、過去のトランザクションが作った出力（[UTXO](../utxo/)）として記録され、送金はその出力を使うトランザクションです。出力には、その出力を使うための条件が [Bitcoin Script](../bitcoin-script/) で書かれています。Script はスタック（後から積んだものを先に取り出す並び）で動く言語で、使う側が署名などを積み、条件の命令がそれを取り出して検査します。

マルチシグは、この条件に署名を数える命令 OP_CHECKMULTISIG を使ったものです。[BIP-11](https://github.com/bitcoin/bips/blob/master/bip-0011.mediawiki)（BIP は Bitcoin Improvement Proposal、仕様変更の提案文書）が標準の形として定めた条件は、次の 1 行です。

```text
2 <公開鍵A> <公開鍵B> <公開鍵C> 3 OP_CHECKMULTISIG
```

先頭の 2 が m、末尾の 3 が n です。使う側は m 個の署名を積みます。ただし、署名の前にもう 1 個、中身を使わない値（ダミー）を積む決まりがあります。理由は次の小見出しで説明します。

<br>

#### 余分に取り出される 1 個

OP_CHECKMULTISIG を実行する直前のスタックは、次の図の通りです。使う側が積んだダミーと署名の上に、条件の 1 行が m・公開鍵・n を積みます。

{{< figure src="images/multisig_stack.webp" alt="左に積む順。1. 使う側が空（ダミー）、署名 A、署名 B の順に積む。2. 条件の 1 行が 2、鍵 A、鍵 B、鍵 C、3 の順に積む。右に、上が先に取り出されるスタック。上から 1 番目が 3（公開鍵の数 n）、2〜4 番目が鍵 C・B・A（公開鍵 n 個）、5 番目が 2（署名の数 m）、6・7 番目が署名 B・A（署名 m 個）、8 番目が空（余分な 1 個）。右側の括弧が、取り出す塊をまとめている" caption="OP_CHECKMULTISIG の直前のスタックと、取り出す順" align="center" >}}

OP_CHECKMULTISIG は、上から n、公開鍵 n 個、m、署名 m 個を取り出した後、8 番目のダミーをもう 1 個余分に取り出します。これは初期の実装の不具合が、そのまま規則として残ったものです。[Bitcoin Core の実装](https://github.com/bitcoin/bitcoin/blob/v32.1/src/script/interpreter.cpp#L1203-L1212)にも「A bug causes CHECKMULTISIG to consume one extra argument」（不具合で 1 個余分に引数を消費する）というコメントがあります。

<br>

ダミーの中身は検査に使われず、署名の対象にも、使う側が積む値は含まれません（署名で覆うのはトランザクションの入出力などで、積む値はその外にあります）。そのため、トランザクションを中継するノードがダミーの中身を書き換えても、署名は有効なままでした。

中身が変わればトランザクションのバイト列が変わり、トランザクションを識別するハッシュ値（txid）も変わります。送った本人が知らない txid のトランザクションがブロックに入ると、元の txid を前提に作った後続のトランザクションが使えなくなります。この余地をふさぐため、2017 年に有効になった [BIP-147](https://github.com/bitcoin/bips/blob/master/bip-0147.mediawiki) で、ダミーは空のバイト列でなければならない規則になりました。

<br>

#### 署名の並び

OP_CHECKMULTISIG は、署名と公開鍵を並びの端から 1 つずつ照らし合わせ、合わなかった公開鍵は飛ばして、二度と戻りません。そのため、署名はスクリプトに書いた公開鍵と同じ順に並べる必要があります。Bitcoin Core の実装は、上記のスタックの図の通り、最後に積んだ署名 B と、上にある鍵 C から照らし合わせます。

{{< figure src="images/multisig_order.webp" alt="左右 2 つの図。上に鍵 A・B・C、下に署名が 2 個並び、線の上の数字が照らし合わせる順。左は署名を A、B の順に積んだ場合で、1 で最後の署名 B が鍵 C を点線で飛ばし、2 で鍵 B に実線で一致し、3 で署名 A が鍵 A に一致して通る。右は B、A の順に積んだ場合で、1 と 2 で最後の署名 A が鍵 C と B を点線で飛ばした時点で、残る鍵が 1 個で署名 2 個に足りず、赤い × で失敗する" caption="2-of-3 の OP_CHECKMULTISIG が署名と公開鍵を照らし合わせる順" align="center" >}}

公開鍵 A・B・C に対して署名を B、A の順に積むと、最後に積んだ A の署名が公開鍵 C と B を飛ばします。その時点で残る公開鍵は 1 個で、残る署名 2 個を満たせないので失敗します。

---

### 条件をハッシュで預ける P2WSH

送金する側は、受け取る側から渡されたアドレスを元に出力を作ります。上記の条件をそのまま出力に書くと、送金する側が公開鍵 3 個を含む長い条件を受け取り、書き込むことになります。そこで、条件のハッシュ値だけをアドレスとして渡して出力に書き、使う時に条件の本体を出す [P2SH](../bitcoin-script/)（Pay to Script Hash）が使われます。

本記事の実験で使う P2WSH（Pay to Witness Script Hash）は、P2SH と同じ考え方を SegWit に合わせた形式です。SegWit（Segregated Witness）は 2017 年に有効になった仕様変更で、署名などの使う資格の証明は、トランザクションの本体とは別の witness という領域に移りました。

witness は txid の計算に含まれないので、前の節の書き換えでも txid は変わりません。ただし witness まで含めたハッシュ値（wtxid）は変わり、ノードの間でブロックを効率よく中継する仕組みの妨げになります。そのため BIP-147 は、P2WSH にも同じ規則を課しています。

P2WSH を定めた [BIP-141](https://github.com/bitcoin/bips/blob/master/bip-0141.mediawiki) では、出力に条件の本体（witnessScript）の 32 バイトの [SHA-256](/notes/security/sha-256/) を書き、条件の本体と署名は witness に置きます。

{{< figure src="images/multisig_p2wsh.webp" alt="上に出力（scriptPubKey）の箱があり、0 と、条件の本体の SHA-256（32 バイト）が入っている。下に使う時の witness として、空のダミー、署名 A 71 バイト、署名 B 71 バイト、条件の本体 witnessScript 105 バイトの 4 つの箱が並ぶ。条件の本体の箱から出力のハッシュへ、SHA-256 が一致するかを確認する矢印が伸びる。下に、一致したら条件の本体（2 <公開鍵A> <公開鍵B> <公開鍵C> 3 OP_CHECKMULTISIG）を左の 3 個を積んだ状態で実行する、という注記" caption="2-of-3 の P2WSH の出力と、使う時の witness" align="center" >}}

上記の図の通り、出力（scriptPubKey）に残るのは、witness の形式の版を表す 0 と、ハッシュ値だけです。使う時は、witness にダミー・署名 2 個・条件の本体を並べます。検証するノードは、条件の本体のハッシュ値が出力と一致することを確認してから、条件の本体を実行します。図のバイト数は、次の節の実験で記録した値です。

---

### regtest で 2-of-3 を作る

[Bitcoin Core](https://bitcoincore.org/) 32.1 の regtest（手元だけで動く検証用のチェーン）で、署名が 1 個では本当に通らないのか、並びを逆にすると何で失敗するのかを確認しました。コンテナはネットワークに繋がず、鍵は使い捨てのウォレットで作っています。取得したファイルと版は [lab の README](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/multisig/lab/README.txt) に記録しました。

3 個のウォレット a・b・c から公開鍵を 1 個ずつ集め、`wsh(multi(2,a,b,c))` という [descriptor](https://github.com/bitcoin/bips/blob/master/bip-0380.mediawiki)（出力の条件を表す記法）で 2-of-3 の P2WSH を作ります。`wsh(...)` が P2WSH、`multi(2,...)` が OP_CHECKMULTISIG の条件を表します。

署名の受け渡しには、署名前のトランザクションと途中の署名を運ぶ [PSBT](https://github.com/bitcoin/bips/blob/master/bip-0174.mediawiki)（Partially Signed Bitcoin Transaction）を使います。手順は Bitcoin Core の [multisig-tutorial](https://github.com/bitcoin/bitcoin/blob/v32.1/doc/multisig-tutorial.md) と同じです。ただし tutorial は公開鍵を並べ替える `sortedmulti` を使い、本記事は並びを書いた通りに保つ `multi` を使っています。

正しく署名したトランザクションの witness を組み替え、各組み合わせをブロックに入れようとした時の判定を記録しました。要点は次の部分です。

```python
sig_a, sig_b, ws = wit[1], wit[2], wit[3]   # wit = ['', sig_a, sig_b, witnessScript]
cases = [
    ('only sig_a (dummy, sig_a)', ['', sig_a, ws]),
    ('sig_b before sig_a', ['', sig_b, sig_a, ws]),
    ('dummy = 0x01', ['01', sig_a, sig_b, ws]),
    ('no dummy', [sig_a, sig_b, ws]),
]
for label, items in cases:
    print(f'{label:26} ->', verdict(with_witness(full['ab'], items), miner))
```

判定には 2 段階あります。受け取ったトランザクションをブロックに入る前の置き場（mempool）に入れるかどうかは、各ノードのポリシー（policy）で決まります。ポリシーはノードごとに変えられるので、全ノード共通の規則（合意規則）で拒まれるかを知るには、ブロックに入れて試す必要があります。`verdict` は、mempool に拒まれたトランザクションを `generateblock` でブロックに入れ、合意規則での判定を返します。

`with_witness` はトランザクションの witness だけを差し替える関数です。全体は以下です。

<br>

<details>
<summary>bitcoin_multisig.py の全体</summary>

```python
#!/usr/bin/env python3
"""Local regtest only. 2-of-3 P2WSH and 3-of-3 MuSig2 with Bitcoin Core 32.1.

Run through run.sh: the container has no network (--network none) and every
key is generated by a throwaway regtest wallet that is deleted afterwards.
"""
import json
import os
import shutil
import subprocess
import time

BIN = os.environ.get('BITCOIN_BIN', '/opt/bitcoin/bin')
DATA = '/tmp/regtest'


def cli(*args, wallet=None):
    cmd = [f'{BIN}/bitcoin-cli', '-regtest', f'-datadir={DATA}']
    if wallet:
        cmd.append(f'-rpcwallet={wallet}')
    r = subprocess.run(cmd + [str(a) for a in args], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr.strip().splitlines()[-1])
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return r.stdout.strip()


def start():
    shutil.rmtree(DATA, ignore_errors=True)
    os.makedirs(DATA)
    subprocess.check_call([f'{BIN}/bitcoind', '-regtest', f'-datadir={DATA}', '-daemon',
                           '-listen=0', '-dnsseed=0', '-fixedseeds=0', '-fallbackfee=0.0001'],
                          stdout=subprocess.DEVNULL)
    for _ in range(300):
        if os.path.exists(f'{DATA}/regtest/.cookie'):
            break
        time.sleep(0.1)
    cli('-rpcwait', 'getblockcount')


# --- helpers to rewrite the witness of input 0 (segwit serialization) ---
def varint(n):
    return bytes([n]) if n < 0xfd else b'\xfd' + n.to_bytes(2, 'little')


def read_varint(b, i):
    return (b[i], i + 1) if b[i] < 0xfd else (int.from_bytes(b[i + 1:i + 3], 'little'), i + 3)


def with_witness(tx_hex, items):
    b = bytes.fromhex(tx_hex)
    assert b[4:6] == b'\x00\x01'  # segwit marker and flag
    n_in, i = read_varint(b, 6)
    assert n_in == 1
    i += 36
    length, i = read_varint(b, i)
    i += length + 4
    n_out, i = read_varint(b, i)
    for _ in range(n_out):
        i += 8
        length, i = read_varint(b, i)
        i += length
    j = i
    count, j = read_varint(b, j)
    for _ in range(count):
        length, j = read_varint(b, j)
        j += length
    witness = varint(len(items)) + b''.join(varint(len(x)) + x for x in map(bytes.fromhex, items))
    return (b[:i] + witness + b[j:]).hex()


def verdict(raw, miner):
    mempool = cli('testmempoolaccept', json.dumps([raw]))[0]
    if mempool['allowed']:
        return 'accepted'
    try:
        cli('generateblock', miner, json.dumps([raw]))
        return 'BLOCK ACCEPTED (unexpected)'
    except RuntimeError as e:  # consensus check when the tx is put in a block
        msg = str(e)
        return 'block rejected: ' + msg[msg.index('(') + 1:msg.index(')')]


def spend(wallet, dest, change):
    opts = json.dumps({'changeAddress': change})
    return cli('-named', 'walletcreatefundedpsbt', 'inputs=[]',
               f'outputs=[{{"{dest}":0.5}}]', f'options={opts}', wallet=wallet)['psbt']


def main():
    start()
    for w in ('miner', 'a', 'b', 'c'):
        cli('-named', 'createwallet', f'wallet_name={w}')
    miner = cli('getnewaddress', wallet='miner')
    cli('generatetoaddress', 101, miner)
    dest = cli('getnewaddress', wallet='miner')

    # One key per signer wallet; only public keys leave each wallet.
    key = {}
    for w in 'abc':
        info = cli('getaddressinfo', cli('getnewaddress', '', 'bech32', wallet=w), wallet=w)
        path = info['hdkeypath'][2:].replace('h', "'")
        key[w] = f"[{info['hdmasterfingerprint']}/{path}]{info['pubkey']}"

    # ---- 1. 2-of-3 P2WSH ----
    desc = cli('getdescriptorinfo', f"wsh(multi(2,{key['a']},{key['b']},{key['c']}))")['descriptor']
    cli('-named', 'createwallet', 'wallet_name=coord', 'disable_private_keys=true', 'blank=true')
    cli('importdescriptors', json.dumps([{'desc': desc, 'timestamp': 'now'}]), wallet='coord')
    addr = cli('deriveaddresses', desc)[0]
    cli('sendtoaddress', addr, 1, wallet='miner')
    cli('generatetoaddress', 1, miner)
    psbt = spend('coord', dest, addr)
    signed = {w: cli('walletprocesspsbt', psbt, wallet=w)['psbt'] for w in 'abc'}

    print('== 2-of-3 P2WSH')
    ws_hex = cli('decodepsbt', psbt)['inputs'][0]['witness_script']['hex']
    asm = cli('decodescript', ws_hex)['asm'].split()
    print('witnessScript:', ' '.join(x if x.startswith('OP_') or len(x) < 8 else x[:6] + '..' for x in asm))
    print('signed by a only     -> complete =', cli('finalizepsbt', signed['a'])['complete'])
    full = {}
    for pair in ('ab', 'ac', 'bc'):
        fin = cli('finalizepsbt', cli('combinepsbt', json.dumps([signed[p] for p in pair])))
        full[pair] = fin['hex']
        print(f'signed by {pair[0]} and {pair[1]}  -> complete = {fin["complete"]},',
              'mempool =', verdict(fin['hex'], miner))
    tx = cli('decoderawtransaction', full['ab'])
    wit = tx['vin'][0]['txinwitness']
    print('witness items (bytes):', [len(x) // 2 for x in wit], '| weight =', tx['weight'])
    sig_a, sig_b, ws = wit[1], wit[2], wit[3]
    cases = [
        ('only sig_a (dummy, sig_a)', ['', sig_a, ws]),
        ('sig_b before sig_a', ['', sig_b, sig_a, ws]),
        ('dummy = 0x01', ['01', sig_a, sig_b, ws]),
        ('no dummy', [sig_a, sig_b, ws]),
    ]
    for label, items in cases:
        print(f'{label:26} ->', verdict(with_witness(full['ab'], items), miner))

    # ---- 2. 3-of-3 MuSig2 key path (BIP-327 aggregation inside Bitcoin Core) ----
    print('== 3-of-3 MuSig2 (tr(musig(...)))')
    pub = cli('getdescriptorinfo', f"tr(musig({key['a']},{key['b']},{key['c']}))")['descriptor']
    master = {}
    for w in 'abc':
        d = [x['desc'] for x in cli('listdescriptors', 'true', wallet=w)['descriptors']
             if x['desc'].startswith('wpkh(') and not x['internal']][0]
        master[w] = d[5:d.index('/')]  # tprv of the throwaway regtest wallet
    for w in 'abc':
        parts = [f"{master[o]}/{key[o].split('/', 1)[1].split(']')[0]}" if o == w else key[o] for o in 'abc']
        priv = f"tr(musig({','.join(parts)}))"
        priv += '#' + cli('getdescriptorinfo', priv)['checksum']
        cli('-named', 'createwallet', f'wallet_name=m{w}', 'blank=true')
        cli('importdescriptors', json.dumps([{'desc': priv, 'timestamp': 'now'}]), wallet=f'm{w}')
    cli('-named', 'createwallet', 'wallet_name=mcoord', 'disable_private_keys=true', 'blank=true')
    cli('importdescriptors', json.dumps([{'desc': pub, 'timestamp': 'now'}]), wallet='mcoord')
    maddr = cli('deriveaddresses', pub)[0]
    cli('sendtoaddress', maddr, 1, wallet='miner')
    cli('generatetoaddress', 1, miner)
    psbt = spend('mcoord', dest, maddr)
    round1 = cli('combinepsbt', json.dumps([cli('walletprocesspsbt', psbt, wallet=f'm{w}')['psbt'] for w in 'abc']))
    inp = cli('decodepsbt', round1)['inputs'][0]
    print('round 1: pubnonces =', len(inp['musig2_pubnonces']), ', partial sigs =', len(inp.get('musig2_partial_sigs', [])))
    round2 = cli('combinepsbt', json.dumps([cli('walletprocesspsbt', round1, wallet=f'm{w}')['psbt'] for w in 'abc']))
    inp = cli('decodepsbt', round2)['inputs'][0]
    print('round 2: partial sigs =', len(inp['musig2_partial_sigs']))
    fin = cli('finalizepsbt', round2)
    mtx = cli('decoderawtransaction', fin['hex'])
    print('complete =', fin['complete'], ', mempool =', verdict(fin['hex'], miner))
    print('witness items (bytes):', [len(x) // 2 for x in mtx['vin'][0]['txinwitness']], '| weight =', mtx['weight'])

    # ---- 3. single-key P2TR with the same shape (1 input, 2 outputs) ----
    print('== single-key P2TR for comparison')
    cli('-named', 'createwallet', 'wallet_name=solo')
    saddr = cli('getnewaddress', '', 'bech32m', wallet='solo')
    cli('sendtoaddress', saddr, 1, wallet='miner')
    cli('generatetoaddress', 1, miner)
    sp = cli('walletprocesspsbt', spend('solo', dest, saddr), wallet='solo')
    stx = cli('decoderawtransaction', cli('finalizepsbt', sp['psbt'])['hex'])
    print('witness items (bytes):', [len(x) // 2 for x in stx['vin'][0]['txinwitness']], '| weight =', stx['weight'])
    for label, a in (('musig2', maddr), ('single', saddr)):
        spk = cli('getaddressinfo', a, wallet='mcoord' if label == 'musig2' else 'solo')['scriptPubKey']
        print(f'{label} scriptPubKey: {spk[:4]} + {len(spk) // 2 - 2}-byte key')
    cli('stop')


if __name__ == '__main__':
    main()
```

</details>

<br>

実行結果は以下の通りです。txid と公開鍵は実行ごとに変わります。

```text
== 2-of-3 P2WSH
witnessScript: 2 028414.. 022143.. 02b31c.. 3 OP_CHECKMULTISIG
signed by a only     -> complete = False
signed by a and b  -> complete = True, mempool = accepted
signed by a and c  -> complete = True, mempool = accepted
signed by b and c  -> complete = True, mempool = accepted
witness items (bytes): [0, 71, 71, 105] | weight = 754
only sig_a (dummy, sig_a)  -> block rejected: Operation not valid with the current stack size
sig_b before sig_a         -> block rejected: Script evaluated without error but finished with a false/empty top stack element
dummy = 0x01               -> block rejected: Dummy CHECKMULTISIG argument must be zero
no dummy                   -> block rejected: Operation not valid with the current stack size
```

a だけが署名した PSBT は `complete = False` で、トランザクションとして完成しません。2 人の組み合わせは 3 通りとも通り、どの 2 人でも送金できます。

witness を組み替えた 4 通りは、全てブロックに入りませんでした。署名を 1 個にすると、ダミーまで数えた個数が足りずにスタックの不足で止まります。ダミーを抜いた場合も同じエラーで、OP_CHECKMULTISIG が m 個の署名に加えてもう 1 個を必要とすることが分かります。署名の順を逆にした場合は、実行は最後まで進み、結果が偽になって失敗しました。

witness の大きさは `[0, 71, 71, 105]` バイトで、P2WSH の図の通りです。最後の 105 バイトは公開鍵 3 個を含む条件の本体で、使う時に全員の公開鍵がチェーンに出ます。

---

### 署名を 1 個にまとめる MuSig2

ここまでの P2WSH では、署名の数だけ署名がチェーンに載り、全員の公開鍵も出ます。2021 年に有効になった Taproot という仕様変更（[BIP-341](https://github.com/bitcoin/bips/blob/master/bip-0341.mediawiki)）は、ここに別の道を加えました。

Taproot の出力では、Bitcoin が従来使ってきた ECDSA（[Digital Signature](../digital-signature/) で説明した署名方式）に代わり、[Schnorr 署名](https://github.com/bitcoin/bips/blob/master/bip-0340.mediawiki)という別の署名方式を使います。Schnorr 署名は、複数人の公開鍵を組み合わせて 1 個の公開鍵にでき、その鍵に対する署名も各自の計算を合わせて作れる、という性質を持ちます。

[MuSig2](https://github.com/bitcoin/bips/blob/master/bip-0327.mediawiki)（BIP-327）は、この性質を使う手順です。n 人の公開鍵を 1 個の集約鍵にまとめ、n 人が協力して、集約鍵に対する 1 個の Schnorr 署名を作ります。署名は 2 往復で作ります。1 往復目で各自が [nonce（署名ごとに使い捨てる乱数）](/notes/security/nonce/)の公開値を配り、2 往復目で部分署名を配って 1 個の署名にまとめます。

<br>

MuSig2 で作れるのは、全員の署名が要る n-of-n だけです。2-of-3 のように一部の人で署名したい時は、Taproot の出力が持てる予備の条件を使います。

{{< figure src="images/multisig_taproot.webp" alt="上に Taproot の出力があり、32 バイトの鍵 1 個だけが見える。左下は鍵で使う key path で、A・B・C から作る集約鍵への署名 1 個、全員が揃う時（MuSig2）。右下は破線の予備の条件で使う script path で、tapscript・control block・署名 2 個、揃わない時に使い、使った時だけ条件が出る。下に、予備の条件は出力の鍵に埋め込まれ普段は見えない、という注記" caption="Taproot の出力を使う 2 つの道（概念図）" align="center" >}}

上記の図の通り、Taproot の出力に見えるのは 32 バイトの鍵 1 個だけで、予備の条件はその鍵に埋め込まれています。

全員が揃う時は鍵で使い（key path）、集約鍵への署名 1 個を出します。揃わない時は予備の条件で使い（script path）、条件の本体（後述の tapscript）、それが出力の鍵に埋め込まれていることの証明（control block）、2 人の署名を出します。予備の条件がチェーンに出るのは、こちらを使った時だけです。

<br>

予備の条件は Taproot 用のスクリプト（tapscript）で書き、そこでは OP_CHECKMULTISIG が使えません。代わりに、署名を 1 個ずつ検査して数を足していく OP_CHECKSIGADD が [BIP-342](https://github.com/bitcoin/bips/blob/master/bip-0342.mediawiki) で加わりました。

<br>

#### regtest で MuSig2 を試す

Bitcoin Core 32.1 は、descriptor に [BIP-390](https://github.com/bitcoin/bips/blob/master/bip-0390.mediawiki) の `musig()` を書けます。前の実験と同じ 3 人の鍵で `tr(musig(a,b,c))`（Taproot の出力の鍵に a・b・c の集約鍵を使う記法）を作り、PSBT を 2 回往復させて送金しました。

比べるために、1 個の鍵だけの Taproot の出力から、同じ形（入力 1 個、出力 2 個）の送金も作っています。この出力は予備の条件を持たず、Taproot の図の左側（鍵で使う道）だけの形です。コードは上記の bitcoin_multisig.py の後半です。

```text
== 3-of-3 MuSig2 (tr(musig(...)))
round 1: pubnonces = 3 , partial sigs = 0
round 2: partial sigs = 3
complete = True , mempool = accepted
witness items (bytes): [64] | weight = 568
== single-key P2TR for comparison
witness items (bytes): [64] | weight = 568
musig2 scriptPubKey: 5120 + 32-byte key
single scriptPubKey: 5120 + 32-byte key
```

MuSig2 の witness は 64 バイトの署名 1 個だけで、1 個の鍵の送金と同じです。出力の形も、どちらも `51`（witness version 1）と `20`（32 バイトを積む）に 32 バイトの鍵が続くだけです。チェーンを見る人は、この 2 つを区別できません。トランザクションの重さ（weight、手数料の計算に使う大きさ）は 568 で、P2WSH の 2-of-3 の 754 より小さくなりました。

<br>

MuSig2 には、P2WSH に無い注意点があります。1 往復目で配った nonce を別の署名で使い回すと、秘密鍵が漏れる恐れがあります。

BIP-327 は、同じ秘密の nonce で 2 回署名することを禁じています。1 人で署名する時のように nonce を署名する内容から決定的に導くことも、原則として禁じています。他の署名者が自分の nonce を変えてやり直させると、同じ nonce で別の値に署名させられてしまうためです。使い終えた秘密の nonce を消して再利用を防ぐ実装の工夫にも触れています。

---

### MPC・しきい値署名との違い

MuSig2 の n-of-n に対して、m-of-n を 1 個の公開鍵と 1 個の署名で表す方法が、しきい値署名（threshold signature）です。

MPC（Multi-Party Computation、複数の参加者が秘密を明かさずに共同で計算する技術）を使い、参加者は、1 本の秘密鍵を分けたシェア（share）だけを持ちます。署名する時もシェアを 1 か所に集めず、参加者が計算をやり取りして 1 個の署名を作ります。Schnorr 署名のしきい値署名の例が [FROST](https://www.rfc-editor.org/rfc/rfc9591)（RFC 9591）です。

[Shamir's Secret Sharing](/notes/security/shamir-secret-sharing/) も鍵をシェアに分けますが、使う時にはシェアを集めて鍵を復元します。しきい値署名は、鍵を復元せずに署名を作る点が違います。

<br>

MuSig2 との違いは、鍵の作り方です。MuSig2 では各自が独立に作った鍵の公開鍵を集約するため、全員の部分署名が必要です。しきい値署名では 1 本の鍵を分けたシェアを配るので、m 人分のシェアで署名できます。

シェアは参加者が協力して作る方法（DKG、Distributed Key Generation）なら、鍵の全体は一度も存在しません（[FROST の原論文](https://eprint.iacr.org/2020/852)は DKG を含めて提案しています）。配布者が鍵を作って分ける方法もあり、こちらでは一度は鍵の全体が存在します。比べると以下のようになります。

| | Bitcoin P2WSH | [Safe](../safe-multisig/) | MuSig2 | MPC のしきい値署名 |
| --- | --- | --- | --- | --- |
| 規則を検査する場所 | スクリプト | コントラクト | オフチェーン（n-of-n） | オフチェーン（m-of-n） |
| チェーンに出る署名 | m 個 | m 個 | 1 個 | 1 個 |
| 誰が署名したか | チェーンで分かる | チェーンで分かる | 分からない | 分からない |
| 署名者の入れ替え | 資産を新しい出力に移す | 設定を変えるトランザクション | 資産を新しい出力に移す | シェアを配り直す（資産は動かない） |

表の「署名者の入れ替え」の行で P2WSH と MuSig2 が資産を移すのは、公開鍵が出力のハッシュや鍵に固定されているためです。

表の最後の 2 列は、署名者の数と規則がチェーンに記録されません。誰が承認したかを後からチェーンで確かめられず、m の規則はチェーンではなく、鍵の作り方と参加者のソフトウェアで決まります。製品ごとにやり方が違うので、[Wallet](../wallet/) のノートで触れた通り、どの参加者が揃えば署名できるか、事業者が止まった時に復旧できるかを確認する必要があります。

---

### 署名の数で防げないこと

m 個の署名を要求しても、署名者の全員が同じ偽の内容に署名すれば、検査は通ります。署名の数が守るのは鍵を盗まれる場合で、何に署名したかの確認は守りません。全員が同じ Web 画面でトランザクションを作り、同じ表示を見て署名する運用では、画面が改ざんされると全員が同じ偽の内容に署名します。2025 年 2 月の [Bybit の事件](../wallet/#bybitsafe-の承認処理の乗っ取り)はこの例で、Safe の側の仕組みは [Safe](../safe-multisig/#署名の数では防げないこと) のノートで扱います。

<br>

鍵以外に失うと困るものもあります。P2WSH は、使う時に公開鍵 3 個を全て含む条件の本体が必要です。秘密鍵 2 個があっても、3 個目の公開鍵が無いと条件の本体を組み立てられません。ウォレットは条件の本体のハッシュ値から自分の出力を探すので、出力を見つけることも使うこともできなくなります。秘密鍵とは別に、全員の公開鍵と条件を記録した descriptor のバックアップも、各署名者が持つ必要があります。

---

### 利点

- 鍵 1 個の盗難でも、紛失でも資産を失わない構成を作れる
- 承認に複数人を必要とし、1 人の判断や 1 台の端末の侵害だけで送金されない
- P2WSH では、誰が署名したかがチェーンに記録され、後から確認できる
- MuSig2 では、手数料と見た目は 1 個の鍵の送金と同じになる

---

### 欠点

マルチシグは、1 個の鍵に集まっていた権限を複数の鍵に分け、署名を数える規則を加えます。その代わりに、次の制約があります。

- 署名を集める手順が増え、署名者が揃わないと送金が遅れる
- P2WSH は署名と公開鍵の分だけトランザクションが重く、手数料が増える（実験では weight 754 と 568）
- 公開鍵・descriptor のように、鍵以外のバックアップが必要になる
- 署名の数は、何に署名したかの確認を代わりに行わない

---

### 適さないケース

- 少額を頻繁に送る用途で、署名を集める手間が資産の保護に見合わない場合
- 鍵を別の端末・人・場所に分けられず、全ての鍵が同じ環境に集まる場合
- 署名者がトランザクションの内容を自分の端末で確認する手段を持たず、共通の画面の表示を信じるしかない場合
- チェーン上で誰が承認したかを隠したい場合（P2WSH は署名者の数と公開鍵がチェーンに出る）
