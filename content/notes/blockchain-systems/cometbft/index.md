---
title: "CometBFT - 2/3 を超える票で確定し、届かなければ止まる合意エンジン"
date: 2026-11-10
draft: false
series: ["技術ノート", "Blockchain Systems"]
tags: ["blockchain-systems", "consensus", "bft", "cosmos"]
weight: 15
wrapTables: true
topics: ["Consensus / Finality"]
---

[CometBFT](https://github.com/cometbft/cometbft) は、[Cosmos SDK](https://github.com/cosmos/cosmos-sdk) で作られたチェーンなどが使う、BFT（Byzantine Fault Tolerance、嘘をつくノードがいても合意する性質）の合意エンジンです。ブロックの順序を決める部分だけを担い、取引の中身を解釈するアプリケーションとは別のプロセスとして動かせます。

4 台のバリデータ（投票に参加するノード）のうち 2 台を止めると、CometBFT のチェーンは分岐せず、同じ高さで止まります。[Proof of Work（PoW）](../proof-of-work/) のチェーンなら、残ったノードだけで採掘を続け、後で長い方に揃えるところです。

{{< figure src="images/cometbft_concept.svg" alt="左は PoW で、途中から枝分かれしたブロックが捨てられ、長い列が残る。右は CometBFT で、確定したブロックが 1 列に並び、次の高さのブロックは 4 台中 2 台の票しか集まらず 2/3 の線に届かないため、分岐せずに止まる" caption="PoW は分岐して長い方に揃い、CometBFT は分岐せずに止まる" align="center" >}}

<br>

本記事では、CometBFT が 1 つのブロックを確定させる手順と止まる条件について、ローカルで 4 台のネットワークを動かした実測とあわせて説明します。扱う疑問は次の通りです。

- prevote と precommit の 2 段の投票は、それぞれ何を確かめているのか。
- ロックは、どのような食い違いを防ぐのか。
- アプリケーションとの境界である ABCI は、何を分けているのか。
- バリデータが何台止まると、チェーンは止まるのか。止まった後は分岐するのか。

[PBFT](https://www.usenix.org/conference/osdi-99/practical-byzantine-fault-tolerance) を例にした BFT の基礎（3f+1 台が必要な理由、quorum の重なり）は [Byzantine Fault Tolerance](/notes/distributed-systems/byzantine-fault-tolerance/) で説明しています。本記事はその続きで、CometBFT に固有の部分を扱います。

---

### CometBFT と Tendermint Core の関係

CometBFT は、[Tendermint Core](https://github.com/tendermint/tendermint) を fork したソフトウェアです。[CHANGELOG](https://github.com/cometbft/cometbft/blob/v0.38.x/CHANGELOG.md) では、2023 年 2 月 27 日の v0.34.27 が「the first official release of CometBFT - a fork of Tendermint Core」（Tendermint Core を fork した CometBFT の最初の正式リリース）とされ、Tendermint Core v0.34 系との互換を目標にしていました。そのため、合意アルゴリズムの名前は今も Tendermint で、CometBFT はその実装の名前です。

アルゴリズムは、[Tendermint の論文](https://arxiv.org/abs/1807.04938)で定式化されています。PBFT と同じく、嘘をつく側の票の重みが全体の 1/3 未満であることを前提に、2/3 を超える票で決めます。違いは、提案者の交代の扱いです。PBFT は primary が疑わしい時だけ View Change という別の手続きに入りますが、Tendermint は提案者の交代を毎回のラウンドの一部に組み込み、交代のための証明の受け渡しをしません。

2026 年 11 月時点で、CometBFT の main ブランチの README がサポート対象に挙げる系列は v0.38.x で、v0.39 と v0.40 のリリースも公開されています。本記事の説明と実験は v0.38.26 に合わせています。

---

### 高さ・ラウンド・提案者

CometBFT のチェーンは、高さ（height）ごとに 1 つのブロックを決めます。1 つの高さの決定は 1 回以上のラウンド（round）から成り、各ラウンドは propose、prevote、precommit の 3 つの段階を順に進みます。

提案者（proposer）は、ラウンドごとに 1 台が決まります。選び方は、票の重み（voting power）に比例した[重み付きのラウンドロビン](https://github.com/cometbft/cometbft/blob/v0.38.x/spec/consensus/proposer-selection.md)で、乱数は使いません。全員が同じ規則で計算するので、誰が提案者かを相談する必要がありません。

以下は、4 台が正常な場合の 1 ラウンドです。票の重みは全員 10 とし、合計 40 のうち 2/3 を超える 27 以上の票を集めると次に進みます。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
sequenceDiagram
    participant V0 as V0 提案者
    participant V1 as V1
    participant V2 as V2
    participant V3 as V3
    V0->>V1: proposal ブロック B
    V0->>V2: proposal ブロック B
    V0->>V3: proposal ブロック B
    Note over V0,V3: 全員が B を検証し<br/>prevote B を全員に送る
    Note over V0,V3: prevote B が 2/3 を超えたら<br/>precommit B を全員に送る
    Note over V0,V3: precommit B が 2/3 を超えたら<br/>B を高さ h で確定
```

票は全員に直接送るのではなく、隣のノードに中継するゴシップで広がります。そのため、各ノードが 2/3 を超える票を見る時刻は少しずつずれます。

提案が届かない場合や不正な場合は、バリデータは nil に投票し、そのラウンドで確定できなければ次のラウンドに進んで提案者も替わります。v0.38 の既定値では、提案を待つ `timeout_propose` が 3 秒で、ラウンドが 1 つ進むたびに 0.5 秒ずつ伸びます。ただし、prevote と precommit の待ち時間は、投票先を問わず、届いた票の重みの合計が 2/3 を超えてから数え始めます。この違いは、後の実験で止まり方として表れます。

---

### 2 段の投票と即時の確定

prevote は「このラウンドの提案は正しく、これを支持する」という票です。提案を検証できなかったバリデータは、空の票（nil）を送ります。prevote が 2/3 を超えた状態は、ブロックの候補が 1 つに絞れたことを示し、仕様では polka とも呼ばれます。

precommit は「2/3 を超える prevote を自分の目で見た」という票です。prevote だけで確定させると、あるノードは 2/3 を見て確定し、別のノードは見られずに次のラウンドで別のブロックに進む、という食い違いが起き得ます。precommit を挟むと、確定の条件が「2/3 を超える重みのバリデータが、候補が 1 つに絞れたことを確認済み」になり、次節のロックと組み合わせて食い違いを防げます。

precommit が 2/3 を超えたブロックは、その時点で確定します。後のブロックが積み上がるのを待つ必要はありません。ブロックには直前のブロックへの precommit の束（commit）が入り、誰でも署名を検証して確定を確かめられます。

<br>

ここで読み違えやすいのは、2/3 の分母です。数えるのはバリデータの台数ではなく、票の重みの合計です。Cosmos SDK のチェーンでは、預けたトークンの量に応じて重みが決まります。重みが偏っていれば、1 台が止まっただけで 1/3 を超えることもあり、逆に、止まったバリデータの重みの合計が 1/3 未満なら、何台止まってもチェーンは進みます。

---

### ロックによる食い違いの防止

ロック（lock）は、precommit を送ったブロックに、後のラウンドでも投票し続ける約束です。バリデータは 2/3 を超える prevote を見てブロック B に precommit すると、B とそのラウンドを記録します。後のラウンドで別のブロックが提案されても、B より新しいラウンドで別のブロックが 2/3 を超える prevote を集めた証拠が無い限り、そのブロックは支持しません。この時の prevote は、論文の Algorithm 1 では nil、v0.38 の実装ではロックした B です。

ロックが無いと何が起きるかは、4 台のうち V3 が嘘をつく例で確かめられます。ラウンド 0 では、V0 と V1 は時間内に B への 2/3 を超える prevote を見て precommit B を送ります。V2 は B への票が待ち時間のうちに 2/3 を超えなかったので precommit nil を送り、V3 は precommit B を V0 にだけ送ります。ラウンド 1 の提案者は V3 で、別のブロック B′ を提案します。

| 台 | ラウンド 0 の precommit | 見えた precommit B | ラウンド 1 で V3 が B′ を提案した時の prevote |
|---|---|---|---|
| V0 | B（B にロック） | V0・V1・V3 の 3 票で、B を確定 | 次の高さへ進んでいる |
| V1 | B（B にロック） | 2 票で、確定できない | B′ を支持しない（論文では nil、v0.38 では B） |
| V2 | nil | 2 票で、確定できない | B′ |
| V3（嘘つき） | V0 にだけ B | — | B′ |

V0 は高さ h を B で確定しています。ラウンド 1 で B′ が prevote を集めて確定すると、同じ高さに 2 つのブロックができます。ロックがあれば V1 は B′ を支持しないので、B′ の prevote は V2 と V3 の 20 で、27 に届きません。V0 の確定に使った 3 票のうち正直な 2 台（重み 20）がロックしている限り、残りの 20 では別のブロックを確定できない、というのが[仕様の安全性の証明](https://github.com/cometbft/cometbft/blob/v0.38.x/spec/consensus/consensus.md#proof-of-safety)の筋道です。

ロックを外す条件もあります。B より新しいラウンドで別のブロックが 2/3 を超える prevote を集めたことが分かれば、ロックを外してそのブロックを支持できます（v0.38 は nil への 2/3 を超える prevote を見た場合も外します）。論文の Algorithm 1 では、提案者が最後に見た候補とそのラウンド（validValue と validRound）を提案に添えるので、ロックしたバリデータ同士が別々のブロックに固まって止まり続けることを避けられます。

---

### ABCI によるアプリケーションの分離

ABCI（Application BlockChain Interface）は、CometBFT とアプリケーションの間の境界です。CometBFT は取引をバイト列として運ぶだけで、残高や署名の規則は知りません。[CometBFT の入門文書](https://github.com/cometbft/cometbft/blob/v0.38.x/docs/introduction/README.md)は、Bitcoin のような仕組みを ABCI の上に作る場合の分担として、次の例を挙げています。

{{< note-panels caption="CometBFT は順序を決め、アプリケーションは中身を判断します。" >}}
- title: CometBFT
  items:
  - ノード間でブロックと取引を共有する
  - 取引の順序を決め、確定させる
- title: アプリケーション
  items:
  - UTXO（まだ使われていない出力）などの状態を保持する
  - 取引の署名を検証する
  - 存在しない出力の使用を拒否する
  - 状態の問い合わせに答える
{{< /note-panels >}}

[ABCI 2.0](https://github.com/cometbft/cometbft/blob/v0.38.x/spec/abci/abci++_basic_concepts.md)（v0.38 で導入されたインターフェース）では、CometBFT は決まった場面でアプリケーションを呼びます。受け取った取引を mempool（未確定の取引の置き場）に入れる前の `CheckTx`、提案者がブロックを組み立てる時の `PrepareProposal`、提案を検証する時の `ProcessProposal`、確定したブロックを渡す `FinalizeBlock`、状態を保存させる `Commit` が主な呼び出しです。

全てのノードが同じブロックから同じ状態を計算できるように、アプリケーションの処理は決定的である必要があります。乱数、時計、[Go](https://go.dev/) の map の走査順に結果が依存すると、ノードごとに状態がずれます。実験で使う kvstore は、`key=value` の形の取引を受け取って保存するだけの、CometBFT に組み込まれた試験用のアプリケーションです。

---

### 止まる条件と、分岐しない理由

CometBFT の性質は、安全性（safety、確定が食い違わない）と活性（liveness、いずれ確定が進む）を分けると整理できます。

| 前提 | 安全性 | 活性 |
|---|---|---|
| 嘘をつく重みと止まった重みの合計が 1/3 未満 | 守られる | 通信が安定していれば守られる。止まった提案者の番では、ラウンドが 1 つ進む |
| 嘘をつく重みは 1/3 未満だが、止まった重みを合わせると 1/3 以上 | 守られる | 止まる。2/3 を超える票が集まらない |
| 二重署名などをした重みが 1/3 以上 | 保証されない | 保証されない |

2 行目が、BFT のチェーンは止まる、という話の中身です。BFT のチェーンも PoW と同じように、分断された 2 つのグループがそれぞれブロックを作り、後で長い方に揃うと思うかもしれません。しかし CometBFT では、2/3 を超える重みを持てるグループは多くても 1 つなので、確定が進むのはそのグループだけです。2 台ずつに分かれた場合のように、どのグループも 2/3 に届かなければ全体が止まり、確定済みのブロックが巻き戻ることもありません。

一方で、止まるのは票を出さない重みが 1/3 以上の時だけで、1 台止まっただけでは進み続けます。どちらも次の節で実測します。

3 行目は、安全性も無条件ではないことを示します。1/3 以上の重みが規則に反して投票すれば、同じ高さに 2 つの確定ブロックができる場合があります。同じラウンドで矛盾する 2 つの票に署名した二重投票なら、2 つの署名から違反者を特定できます。CometBFT はこれを証拠（evidence）としてブロックに入れてアプリケーションに渡し、罰則を科すかはアプリケーションが決めます。ロックを無視するなど、ラウンドをまたいだ違反は 1 組の署名からは分からず、[仕様](https://github.com/cometbft/cometbft/blob/v0.38.x/spec/consensus/consensus.md#proof-of-fork-accountability)では各バリデータに投票の根拠を示させて特定します。

---

### 4 台のネットワークで止める実験

止まる条件を確かめるために、[公式の Docker イメージ](https://hub.docker.com/r/cometbft/cometbft) `cometbft/cometbft:v0.38.26` で 4 台のバリデータを動かしました。アプリケーションは組み込みの kvstore で、票の重みは全員 10、ノード間の通信は外に出られない Docker のネットワークに閉じています。次の順に状態を変え、1 秒ごとに各ノードの確定済みの高さと、投票中の高さ・ラウンド・段階を記録します。

1. 4 台とも動かす（20 秒）
2. node3 を止める（30 秒）
3. node2 も止める（45 秒）。止めた 3 秒後に、取引 `halted=yes` を node0 に送る
4. node2 と node3 を再起動する（45 秒）
5. node0・node1 と node2・node3 の間の通信を切る（45 秒）
6. 通信を戻す（45 秒）

計測の要点は、各ノードの RPC を同じコンテナの中から呼ぶ部分と、状態を変える手順の並びです。

```python
def sample(node):
    """Return (latest committed height, 'height/round/step' being voted on)."""
    status, cons = rpc(node, "status"), rpc(node, "consensus_state")
    if status is None or cons is None:
        return None
    h, r, step = cons["round_state"]["height/round/step"].split("/")
    hrs = f"{h}/{r}/{STEPS[step]}"
    return int(status["sync_info"]["latest_block_height"]), hrs


phases = [
    ("all 4 up", 20, None),
    ("node3 stopped", 30, lambda: sh("docker", "stop", NODES[3])),
    ("node2,3 stopped", 45, lambda: sh("docker", "stop", NODES[2])),
    ("node2,3 restarted", 45, lambda: sh("docker", "start", NODES[2], NODES[3])),
    ("partition 0,1 | 2,3", 45, lambda: [
        sh("docker", "network", "disconnect", NET, n) for n in NODES[2:]]),
    ("partition healed", 45, lambda: [
        sh("docker", "network", "connect", NET, n) for n in NODES[2:]]),
]
```

<details><summary>run.py の全体（ネットワークの作成・計測・後始末）</summary>

```python
"""Stop, restart and partition validators of a local 4-node CometBFT network.

Requires Docker. Uses only the official cometbft image and the built-in kvstore
app. No host port is published and every network is internal (no internet).
All containers and networks are removed at the end.
"""

import csv
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time

IMAGE = ("cometbft/cometbft:v0.38.26@sha256:"
         "08f635fe1eff3bdcbe9d9a57091811351c55de66fbaa80190b28fe436a08356f")
PREFIX = "note-cometbft"
NET, SIDE_A, SIDE_B = f"{PREFIX}-net", f"{PREFIX}-a", f"{PREFIX}-b"
NODES = [f"{PREFIX}-node{i}" for i in range(4)]
UID = f"{os.getuid()}:{os.getgid()}"


def sh(*args, check=True):
    return subprocess.run(args, check=check, capture_output=True, text=True).stdout.strip()


def rpc(node, path):
    """Call the node's RPC from inside its own container (no published port)."""
    out = sh("docker", "exec", node, "curl", "-s", "-m", "2",
             f"http://127.0.0.1:26657/{path}", check=False)
    try:
        return json.loads(out)["result"]
    except (ValueError, KeyError):
        return None


STEPS = {"1": "NewHeight", "2": "NewRound", "3": "Propose", "4": "Prevote",
         "5": "PrevoteWait", "6": "Precommit", "7": "PrecommitWait", "8": "Commit"}


def votes(node):
    """Prevote / precommit bit arrays of the round the node is stuck in."""
    rs = rpc(node, "dump_consensus_state")["round_state"]
    r = int(rs["round"])
    v = next(x for x in rs["votes"] if int(x["round"]) == r)
    return f"{node} {rs['height']}/{r}/{STEPS[str(rs['step'])]} " \
           f"prevotes {v['prevotes_bit_array']}  precommits {v['precommits_bit_array']}"


def sample(node):
    """Return (latest committed height, 'height/round/step' being voted on)."""
    status, cons = rpc(node, "status"), rpc(node, "consensus_state")
    if status is None or cons is None:
        return None
    h, r, step = cons["round_state"]["height/round/step"].split("/")
    hrs = f"{h}/{r}/{STEPS[step]}"
    return int(status["sync_info"]["latest_block_height"]), hrs


def setup(work):
    for net in (NET, SIDE_A, SIDE_B):
        sh("docker", "network", "create", "--internal", net)
    sh("docker", "run", "--rm", "--user", UID, "-e", "CMTHOME=/net/.gen", "-v",
       f"{work}:/net", "--entrypoint", "cometbft", IMAGE, "testnet", "--v", "4", "--o", "/net",
       "--hostname-prefix", f"{PREFIX}-node", "--populate-persistent-peers")
    for i, node in enumerate(NODES):
        sh("docker", "run", "-d", "--name", node, "--network", NET, "--user", UID,
           "-e", "CMTHOME=/home", "-v", f"{work}/node{i}:/home", "--entrypoint", "cometbft", IMAGE,
           "node", "--home", "/home", "--proxy_app=kvstore")
        # Side networks used only for the 2|2 partition: {0,1} on A, {2,3} on B.
        sh("docker", "network", "connect", SIDE_A if i < 2 else SIDE_B, node)


def teardown():
    for node in NODES:
        sh("docker", "rm", "-f", node, check=False)
    for net in (NET, SIDE_A, SIDE_B):
        sh("docker", "network", "rm", net, check=False)


def wait_height(target, limit=120):
    end = time.time() + limit
    while time.time() < end:
        s = sample(NODES[0])
        if s and s[0] >= target:
            return
        time.sleep(1)
    raise RuntimeError("network did not start")


def run_phase(name, seconds, log, start):
    rows = []
    end = time.time() + seconds
    while time.time() < end:
        t = time.time() - start
        rows.append((t, [sample(n) for n in NODES]))
        log.append((name, *rows[-1]))
        time.sleep(1)
    return rows


def summarize(rows):
    """Blocks committed during the phase and the highest round seen."""
    first = [s[0] for s in rows[0][1] if s]
    last = [s[0] for s in rows[-1][1] if s]
    rounds = [int(s[1].split("/")[1]) for _, ss in rows for s in ss if s]
    return max(last) - max(first), max(rounds)


def first_progress(rows):
    """Seconds from the start of the phase until any node's height increases."""
    base = max(s[0] for s in rows[0][1] if s)
    for t, ss in rows:
        if any(s and s[0] > base for s in ss):
            return t - rows[0][0]
    return None


def chain(node, top):
    """(height, block hash, commit round) for heights 1..top on one node."""
    out = []
    for h in range(1, top + 1):
        c = rpc(node, f"commit?height={h}")
        out.append((h, c["signed_header"]["commit"]["block_id"]["hash"],
                    c["signed_header"]["commit"]["round"]))
    return out


def scenario():
    work = tempfile.mkdtemp(prefix="cometbft-lab-")
    os.chmod(work, 0o775)
    teardown()
    log, result = [], {}
    try:
        setup(work)
        wait_height(3)
        start = time.time()
        phases = [
            ("all 4 up", 20, None),
            ("node3 stopped", 30, lambda: sh("docker", "stop", NODES[3])),
            ("node2,3 stopped", 45, lambda: sh("docker", "stop", NODES[2])),
            ("node2,3 restarted", 45, lambda: sh("docker", "start", NODES[2], NODES[3])),
            ("partition 0,1 | 2,3", 45, lambda: [
                sh("docker", "network", "disconnect", NET, n) for n in NODES[2:]]),
            ("partition healed", 45, lambda: [
                sh("docker", "network", "connect", NET, n) for n in NODES[2:]]),
        ]
        for name, seconds, action in phases:
            if action:
                action()
            if name == "node2,3 stopped":
                time.sleep(3)
                tx = rpc(NODES[0], 'broadcast_tx_sync?tx="halted=yes"')
            rows = run_phase(name, seconds, log, start)
            result[name] = (*summarize(rows), first_progress(rows))
            if name == "node2,3 stopped":
                q = rpc(NODES[0], 'abci_query?data="halted"')
                result["tx"] = tx["hash"], tx["code"], q["response"].get("value")
                result["halt_log"] = sh("docker", "logs", "--since", "25s", NODES[0])
                result["halt_votes"] = [votes(NODES[0])]
            if name == "partition 0,1 | 2,3":
                result["split_votes"] = [votes(NODES[0]), votes(NODES[2])]
            if name == "node2,3 restarted":
                result["resume_log"] = sh("docker", "logs", "--since", f"{seconds + 2}s",
                                          NODES[0])
        q = rpc(NODES[0], 'abci_query?data="halted"')
        found = rpc(NODES[0], f'tx?hash=0x{result["tx"][0]}')
        result["tx_after"] = q["response"].get("value"), found and found["height"]
        top = min(sample(n)[0] for n in NODES)
        chains = [chain(n, top) for n in NODES]
        result["same_chain"] = all(c == chains[0] for c in chains)
        result["top"] = top
        result["late_rounds"] = [(h, r) for h, _, r in chains[0] if r > 0]
    finally:
        teardown()
        subprocess.run(["rm", "-rf", work], check=False)
    return log, result


def trim(line):
    """Drop the long hash fields so a log line fits on screen."""
    keep = [w for w in line.split() if not w.startswith(("hash=", "root=", "module="))]
    return " ".join(keep)


def show(sample_):
    return "-" if sample_ is None else f"{sample_[0]:>4} {sample_[1]:<24}"


def main():
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    print(f"image: {IMAGE}")
    results = []
    for i in range(runs):
        log, res = scenario()
        results.append(res)
        if i == 0:
            with open("timeline.csv", "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["t", "phase"] + [f"{c}{k}" for k in range(4) for c in "hr"])
                for name, t, ss in log:
                    cells = [x for s in ss for x in
                             ((s[0], s[1].split("/")[1]) if s else ("", ""))]
                    w.writerow([f"{t:.1f}", name] + cells)
            print("== run 1 timeline (every 5 s): committed height, height/round/step")
            for k, (name, t, ss) in enumerate(log):
                if k % 5 == 0:
                    cells = " | ".join(f"{show(s):<29}" for s in ss)
                    print(f"{t:6.1f}s {name:<20} {cells}")
            print("== run 1 node0 log while 2 of 4 validators are stopped (last lines)")
            halt = [trim(l) for l in res["halt_log"].splitlines() if "consensus" in l]
            print("\n".join(halt[-6:]) or "(no consensus log lines in the last 25 s)")
            print("\n".join(res["halt_votes"]))
            print("== run 1 votes during the 2|2 partition")
            print("\n".join(res["split_votes"]))
            print("== run 1 node0 log after restarting node2,3 (up to the first commit)")
            lines = [trim(l) for l in res["resume_log"].splitlines()
                     if "Timed out" in l or "finalizing commit" in l]
            first = next((k for k, l in enumerate(lines) if "finalizing" in l), 0)
            print("\n".join(lines[max(0, first - 4):first + 2]))
    print("== per phase over", runs, "runs: blocks committed / max round / s to first block")
    for name in results[0]:
        if not isinstance(results[0][name], tuple) or len(results[0][name]) != 3 \
                or name.startswith("tx"):
            continue
        cells = [results[i][name] for i in range(runs)]
        print(f"{name:<20} " + "  ".join(
            f"{b:>3} / r{r:<2} / {'-' if p is None else f'{p:4.1f}'}" for b, r, p in cells))
    for i, res in enumerate(results, 1):
        print(f"run {i}: tx during halt hash={res['tx'][0][:12]} code={res['tx'][1]} "
              f"query_during_halt={res['tx'][2]} query_after={res['tx_after'][0]} "
              f"included_at_height={res['tx_after'][1]}")
        print(f"run {i}: heights 1..{res['top']} identical on 4 nodes: {res['same_chain']}; "
              f"heights decided after round 0: {res['late_rounds']}")
    rec = [r["node2,3 restarted"][2] for r in results if r["node2,3 restarted"][2]]
    heal = [r["partition healed"][2] for r in results if r["partition healed"][2]]
    for label, xs in (("restart -> first block", rec), ("heal -> first block", heal)):
        if xs:
            print(f"{label}: median {statistics.median(xs):.1f} s "
                  f"(min {min(xs):.1f}, max {max(xs):.1f}, n={len(xs)})")


if __name__ == "__main__":
    main()
```

</details>

[lab/run.py](lab/run.py) を 3 回実行した結果の要点は以下の通りです。各区間で確定したブロックの数・最大のラウンド・最初の確定までの秒数を 3 回分並べ、2 台ずつに分断した間の票の数え方を添えています。

```text
== per phase over 3 runs: blocks committed / max round / s to first block
all 4 up              15 / r0  /  1.6   14 / r0  /  1.7   14 / r0  /  1.8
node3 stopped         11 / r1  /  6.0   12 / r1  /  4.6   11 / r1  /  1.9
node2,3 stopped        0 / r0  / -    0 / r0  / -    0 / r0  / -
node2,3 restarted     30 / r1  /  6.5   29 / r1  /  6.5   29 / r1  /  1.5
partition 0,1 | 2,3    0 / r0  / -    0 / r0  / -    0 / r0  / -
partition healed      26 / r1  / 12.6   25 / r0  / 10.9   26 / r0  /  9.9
== run 1 votes during the 2|2 partition
note-cometbft-node0 63/0/Prevote prevotes BA{4:_xx_} 2/4 = 0.50  precommits BA{4:____} 0/4 = 0.00
note-cometbft-node2 63/0/Prevote prevotes BA{4:x__x} 2/4 = 0.50  precommits BA{4:____} 0/4 = 0.00
restart -> first block: median 6.5 s (min 1.5, max 6.5, n=3)
heal -> first block: median 10.9 s (min 9.9, max 12.6, n=3)
```

<details><summary>1 回目の 5 秒ごとの記録と、3 回分の取引・ハッシュの照合（<a href="lab/output.txt">output.txt</a> の抜粋）</summary>

```text
image: cometbft/cometbft:v0.38.26@sha256:08f635fe1eff3bdcbe9d9a57091811351c55de66fbaa80190b28fe436a08356f
== run 1 timeline (every 5 s): committed height, height/round/step
   0.0s all 4 up                3 4/0/NewHeight            |    3 4/0/Propose              |    3 4/0/Precommit            |    3 5/0/NewHeight           
...
  24.4s node3 stopped          19 20/0/Prevote             |   19 20/0/Precommit           |   19 20/0/Precommit           | -                            
  46.9s node3 stopped          28 29/0/NewHeight           |   28 29/0/Propose             |   28 29/0/Prevote             | -                            
  57.5s node2,3 stopped        31 32/0/Prevote             |   31 32/0/Prevote             | -                             | -                            
  64.3s node2,3 stopped        31 32/0/Prevote             |   31 32/0/Prevote             | -                             | -                            
...
 107.1s node2,3 restarted      32 33/0/Propose             |   32 33/0/Precommit           |   32 34/0/NewHeight           |   33 34/0/NewHeight          
...
 147.5s partition 0,1 | 2,3    62 63/0/Prevote             |   62 63/0/Prevote             |   62 63/0/Propose             |   62 63/0/Propose            
 155.5s partition 0,1 | 2,3    62 63/0/Prevote             |   62 63/0/Prevote             |   62 63/0/Prevote             |   62 63/0/Prevote            
...
 196.1s partition healed       62 63/0/Prevote             |   62 63/0/Prevote             |   62 63/0/Prevote             |   62 63/0/Prevote            
 204.1s partition healed       62 63/1/Propose             |   62 63/1/Propose             |   62 63/1/Precommit           |   62 64/0/NewHeight          
== run 1 node0 log while 2 of 4 validators are stopped (last lines)
(no consensus log lines in the last 25 s)
note-cometbft-node0 32/0/Prevote prevotes BA{4:_xx_} 2/4 = 0.50  precommits BA{4:____} 0/4 = 0.00
== run 1 node0 log after restarting node2,3 (up to the first commit)
I[2026-11-10|09:07:58.007] Timed out dur=1s height=32 round=0 step=RoundStepPrecommitWait
I[2026-11-10|09:07:58.420] finalizing commit of block height=32 num_txs=1
run 1: tx during halt hash=B08723AC684A code=0 query_during_halt=None query_after=eWVz included_at_height=32
run 1: heights 1..89 identical on 4 nodes: True; heights decided after round 0: [(20, 1), (24, 1), (28, 1), (32, 1), (63, 1)]
run 2: tx during halt hash=B08723AC684A code=0 query_during_halt=None query_after=eWVz included_at_height=32
run 2: heights 1..87 identical on 4 nodes: True; heights decided after round 0: [(20, 1), (24, 1), (28, 1), (32, 1), (62, 1)]
run 3: tx during halt hash=B08723AC684A code=0 query_during_halt=None query_after=eWVz included_at_height=34
run 3: heights 1..89 identical on 4 nodes: True; heights decided after round 0: [(22, 1), (26, 1), (30, 1), (34, 1), (63, 1)]
```

</details>

1 回目の各ノードの高さを時間順に並べると、以下の通りです。

{{< figure src="images/cometbft_timeline.svg" alt="4 台が動く間と 3 台が動く間は高さが増え続け、2 台だけの間と 2 台ずつに分断された間は全ノードの高さが横ばいになる。再起動した node3 は止める前の高さから一気に追い付く" caption="1 回目の実験での、各ノードの確定済みの高さ" align="center" >}}

1 台を止めた区間では、高さは増え続けました。止めた node3 は票の重みの 1/4 で、1/3 に届かないからです。ただし、ブロックの間隔は 4 台の時の約 1.4 秒から約 2.6 秒に伸びています。この区間でラウンド 1 で決まった高さが 20・24・28 と 4 つおきに並ぶのは、node3 が提案者の番になったラウンド 0 で提案が届かず、`timeout_propose` の 3 秒を待ってから次のラウンドに進んだからです。

2 台を止めた区間では、3 回とも 45 秒間に 1 つもブロックが確定しませんでした。残った 2 台は、同じ高さのラウンド 0 の prevote の段階に留まり、prevote は `2/4 = 0.50` で 2/3 に届いていません。ラウンドは上がらず、info レベルのログにも合意の行は出ません。prevote の待ち時間は 2/3 を超える票が集まってから数え始めるので、時間切れで次のラウンドに進むきっかけが無いからです。提案者を替えても票を出せるのは同じ 2 台なので、ラウンドを回しても確定には近づきません。

<br>

止まっている間も、node0 は取引を受け付けました（`code=0` は `CheckTx` が通ったことを示します）。しかし、キー `halted` を問い合わせても値は返らず、取引は mempool で待っているだけです。2 台を再起動すると、止まっていた高さ（1 回目は 32）のブロックがラウンド 1 で確定し、そこに取引が入って値 `eWVz`（base64 で `yes`）が読めるようになりました。docker start から最初の確定までは、3 回の中央値で 6.5 秒（1.5〜6.5 秒）でした。

2 台ずつに分断した区間も、結果は同じです。どちらのグループも prevote が `2/4` のまま止まり、自分たちだけでブロックを作り進めることはありませんでした。通信を戻すと、3 回の中央値 10.9 秒（9.9〜12.6 秒）で確定が再開しました。最後に全ノードのブロックハッシュを高さ 1 から比べ、3 回とも 4 台で一致しました。分断の前後で、別々のブロックが確定した高さはありません。

票を出さない重みの割合で 4 つの区間を並べると、以下のようになります。1/3 の線をまたいだ所で、進むか止まるかが分かれています。

{{< figure src="images/cometbft_halt.svg" alt="横軸は票を出さない重みの割合で、1/3 に縦線がある。1/3 より左は青の「確定が進む」、右は黄土色の「全体が止まり、分岐しない」。0 の 4 台は 20 秒で 15 個、1/4 の node3 停止は 30 秒で 11 個のブロックが確定した。1/2 の 2 台停止と 2 台ずつの分断は、どちらも 45 秒で 0 個" caption="票を出さない重みの割合と、実験の各区間での確定の有無" align="center" >}}

なお、時間の値は他の処理で負荷の高いマシンでの実測で、再起動したコンテナの起動とノード同士の再接続の時間を含みます。CometBFT の性能の指標として読むことはできません。

---

### 合意方式の比較

ここまでの性質を他の方式と並べると以下の通りです。PBFT は参加者を固定した論文のアルゴリズム、Ethereum は 2026 年 11 月時点のメインネットの仕組みです。

| 方式 | 票の重みの根拠 | 確定の時点 | 安全性が耐える割合 | 参加者の 1/3 以上が止まるか分断された時 |
|---|---|---|---|---|
| [Proof of Work](../proof-of-work/)（Bitcoin） | 計算量 | 確定は無く、後続のブロックが増えるほど覆りにくくなる | 攻撃者の計算量が過半に届かない | 残った側で採掘が続く。分断中は分岐し、後で計算量の多い列に揃う |
| [Proof of Stake](../proof-of-stake/)（Ethereum） | 預けた ether | checkpoint への 2 段の投票で [finalized](../finality/) | 違反した預け入れが 1/3 未満 | ブロックは作り続け、finalize だけが止まる。長く続くと inactivity leak で再開し、分断が続けば両側で finalize し得る |
| [PBFT](/notes/distributed-systems/byzantine-fault-tolerance/) | 1 台 1 票 | commit の段階で確定 | 嘘つきが台数の 1/3 未満 | 止まる。分岐しない |
| CometBFT | 重み（Cosmos SDK では預けたトークン） | precommit が 2/3 を超えたブロックで即座に確定 | 嘘をつく重みが 1/3 未満 | 止まる。分岐しない |

Ethereum と CometBFT はどちらも預け入れを重みにしますが、票が足りない時の振る舞いが違います。Ethereum はブロックの生成と確定を分け、確定が止まってもブロックを積み続けます。CometBFT はブロックの生成と確定が同じ手順なので、確定が止まるとブロックも止まります。全員の票を集めずに少数への問い合わせを繰り返す方式は [Snowman](../snowman/)、許可した署名者が順番にブロックを作る方式は [Proof of Authority](../proof-of-authority/) で説明しています。

---

### 利点

- precommit が 2/3 を超えたブロックは即座に確定し、確認数を数えて待つ必要が無い
- 確定したブロックは、嘘をつく重みが 1/3 未満である限り巻き戻らない
- 同じラウンドで二重投票したバリデータは、矛盾する 2 つの署名から特定できる
- ABCI の境界により、合意の実装に触れずにアプリケーションを任意の言語で書ける

---

### 欠点

CometBFT は、食い違うくらいなら止まる側を選んでいます。その代わりに、次の制約があります。

- 票の重みの 1/3 以上が止まるか分断されると、ブロックの生成ごと止まる
- 再開には、止まったバリデータの復旧や分断の解消といった外からの対応が必要になる
- 全員の票を全員に届けるので、バリデータの数を大きくしにくい
- アプリケーションが決定的でないと、ノード間で状態がずれる

---

### 適さないケース

- 参加者が非常に多く、誰でも自由に出入りできるネットワーク
- 確定が遅れても、取引の受け付けとブロックの生成を止めたくない用途
- 地理的に広く分かれ、分断が頻繁に起きるネットワークで、各側が独立して動き続ける必要がある場合
