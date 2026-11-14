---
title: "Commit-Reveal - 中身を隠したまま約束し、締め切りの後に明かす"
date: 2026-11-11
draft: false
series: ["技術ノート", "Blockchain Systems"]
tags: ["blockchain-systems", "ethereum", "smart-contract", "commit-reveal", "mev"]
weight: 23
wrapTables: true
topics: ["Smart Contract"]
---

[スマートコントラクト](../smart-contract/)で、入札額を最後まで伏せる封印入札（sealed-bid）のオークションを開くとします。Alice が「50 で入札する」というトランザクションを送ると、そのトランザクションはブロックに入る前に [mempool](../mempool/)（ブロックに入る前のトランザクションを置く場所）を通じてネットワークに広まり、誰でも中身を読めます。

Bob はそれを見てから 51 で入札し、手数料を上乗せすれば、後から送った自分のトランザクションを Alice より前に並べてもらえます。手元のローカルチェーンで試すと、Bob の入札が先に処理され、Alice の入札は「too low」で取り消されました。

コミット・リビール（commit-reveal）は、この問題を 2 回のトランザクションに分けて解く仕組みです。1 回目（コミット）では、値そのものではなく、値と秘密の乱数（salt）を合わせたハッシュ値だけを送ります。締め切りの後の 2 回目（リビール）で値と salt を明かし、コントラクトがハッシュ値を計算し直して、1 回目に送られた値と照合します。以下は、何がいつ公開されるかを時間の流れに沿って並べた図です。

{{< figure src="images/commit-reveal_timeline.webp" alt="左の青い帯がコミットの段、右の黄土の帯がリビールの段で、間に締め切りの破線がある。上の行は誰でも見える公開の情報、下の行は本人だけが持つ手元の情報。コミットの段では、手元の入札額 50 と salt（と送り主のアドレス）から keccak256 で作ったハッシュ値 0x66be… だけが公開される。締め切りの後、入札額 50 と salt が公開の行に出て、その下でコントラクトが照合する" caption="コミットの段ではハッシュ値だけが、リビールの段で中身が公開される" align="center" >}}

上記の図の通り、締め切りまでに公開されるのは 32 バイトのハッシュ値だけです。締め切りの後は新しいコミットを受け付けないので、Bob が Alice の入札額を知った時には、もう自分の入札を変えられません。

<br>

本記事では、手元のローカルチェーンでオークションを動かしながら、コミット・リビールの仕組みと限界を説明します。扱う疑問は次の通りです。

- トランザクションの中身を先に見られると、何が起きるのか。
- ハッシュ値は、どうやって中身を隠したまま約束を固定するのか。
- salt が無いと、なぜ中身が分かってしまうのか。
- 明かさない参加者や、他人のコミットを写す参加者はどう扱うのか。
- [ENS](https://ens.domains/) の名前の登録や Ethereum の乱数（RANDAO）は、この仕組みをどう使っているのか。

時間が来れば本人がいなくても復号できる時限暗号や、ゼロ知識証明で入札額を隠したまま比べる方法は扱いません。

---

### 中身を先に見せられない理由

ブロックチェーンに送ったトランザクションは、送った順に処理されるとは限りません。[MEV](../mev/) のノートで説明した通り、Ethereum のプロトコルは同じ送り主のトランザクションを [nonce](../ethereum-account-model/)（通し番号）の順に並べること以外に、ブロックの中の並び順を定めていません。ブロックを作る者は、受け取った順ではなく、手数料や自分の利益で並び順を決められます。

そのため、mempool で他人のトランザクションを読み、手数料を上乗せして前に割り込む先回り（front-running）ができます。冒頭のオークションでは、Alice のトランザクションでは、引数に入札額がそのまま入っているので、Bob は 1 だけ多い額を入れれば勝てます。

Bitcoin でも、署名を求めない条件に添えた値は mempool で読まれ、手数料を上乗せした置き換えで別の宛先に使われます。手元の regtest で再現した様子は [Bitcoin Script](../bitcoin-script/) にあります。

{{< figure src="images/commit-reveal_frontrun.webp" alt="左の灰色の枠は mempool で、1. Alice の bid(50)、手数料 1 gwei のトランザクションを Bob が読み、2. Bob が bid(51)、手数料 3 gwei のトランザクションを送る。3. ブロックでは手数料の高い順に並び、#0 の Bob の bid(51) が成功し、#1 の Alice の bid(50) が too low で取り消される" caption="mempool で読んだ入札に、手数料を上乗せして割り込む（gwei は 10 億分の 1 ETH）" align="center" >}}

以下では、図の流れを手元のローカルチェーンで再現します。

実験には、[Foundry](https://github.com/foundry-rs/foundry) のローカルノード [Anvil](https://getfoundry.sh/anvil/overview) と Solidity のコンパイラを使いました。ローカルの Anvil だけを使い、公開のネットワークや実際の資産には接続していません。

<details>
<summary>実験の環境と、使ったアカウント</summary>

Anvil 1.7.1 と Solidity コンパイラ 0.8.28 を使い、2026 年 11 月 11 日に、AMD Ryzen AI Max+ 395（RAM 128GB のうち 64GB を GPU に割り当て）の CPU と Python 3.14.4 で実行しました（[lab/output/environment.txt](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/commit-reveal/lab/output/environment.txt)）。EVM の規則は、2024 年のアップグレードの Cancun のものに固定しています。

アカウントは Anvil が既定で作るテスト用のもので、秘密鍵が広く公開されている説明用の無価値な鍵です。

</details>

Anvil は既定ではトランザクションを受け取るたびにブロックを作るので、`--no-mining` で自動のマイニングを止め、トランザクションを mempool に溜めてから手でブロックを作っています。並び順は、手数料の高いトランザクションを先にする Anvil の既定の設定（`--order fees`）です。比較用の、入札額をそのまま受け取るコントラクトは次の通りです。

```solidity
contract OpenAuction {
    address public highestBidder;
    uint256 public highestBid;

    function bid(uint256 amount) external {
        require(amount > highestBid, "too low");
        highestBid = amount;
        highestBidder = msg.sender;
    }
}
```

Alice が [priority fee](../gas-eip-1559/)（ブロックを作る者への上乗せの手数料）1 gwei で `bid(50)` を送った後、Bob は Anvil の `txpool_content`（mempool の中身を返す RPC）から Alice のトランザクションを読み、3 gwei で `bid(51)` を送りました。その後に作ったブロックは次の通りです。

```text
  bob sees in txpool: bid(50) from alice
  block 2:
    #0 bob   tip 3 gwei  bid(51)  -> ok
    #1 alice tip 1 gwei  bid(50)  -> reverted (too low)
  winner bob, highest 51
```

後から送った Bob のトランザクションが 0 番目に並び、Alice のトランザクションは取り消されました。取り消されたトランザクションも、ブロックに入った以上は gas の手数料が掛かります。実験の全体は [lab/run.py](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/commit-reveal/lab/run.py)、出力の全体は [lab/output/output.txt](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/commit-reveal/lab/output/output.txt) にあります。

---

### ハッシュ値で約束を固定する

中身を見せずに、後から中身を変えられない約束を作るには、[ハッシュ関数](../hash-function/)の 2 つの性質を使います。1 つは、ハッシュ値から元の入力を求められない原像計算困難性です。これで、コミットを見た人に中身が伝わらなくなります。

もう 1 つは、同じハッシュ値になる別の入力を見つけられない衝突耐性です。これで、コミットした本人も、後から別の値で一致させることができなくなります。前者を隠す性質（hiding）、後者を縛る性質（binding）と呼びます。

Ethereum のコントラクトでは、ハッシュ関数に [Keccak-256](https://keccak.team/keccak.html) を使うのが一般的です。以下が、コミット・リビールで入札を受け付けるコントラクトです。

```solidity
contract CommitRevealAuction {
    uint256 public constant DEPOSIT = 1 ether;
    uint256 public immutable commitDeadline; // この高さまでのブロックでコミットを受け付ける
    uint256 public immutable revealDeadline; // この高さまでのブロックでリビールを受け付ける

    mapping(address => bytes32) public commitments;
    address public highestBidder;
    uint256 public highestBid;

    constructor(uint256 commitBlocks, uint256 revealBlocks) {
        commitDeadline = block.number + commitBlocks;
        revealDeadline = commitDeadline + revealBlocks;
    }

    function commit(bytes32 commitment) external payable {
        require(block.number <= commitDeadline, "commit closed");
        require(msg.value == DEPOSIT, "deposit");
        require(commitments[msg.sender] == bytes32(0), "already committed");
        commitments[msg.sender] = commitment;
    }

    function reveal(uint256 amount, bytes32 salt) external {
        require(block.number > commitDeadline, "too early");
        require(block.number <= revealDeadline, "reveal closed");
        // 送り主のアドレスもハッシュに含め、他人のコミットを写しても使えないようにする
        require(keccak256(abi.encode(msg.sender, amount, salt)) == commitments[msg.sender], "mismatch");
        delete commitments[msg.sender];
        if (amount > highestBid) {
            highestBid = amount;
            highestBidder = msg.sender;
        }
        payable(msg.sender).transfer(DEPOSIT); // リビールした人にだけ預け金を返す
    }
}
```

締め切りはブロックの高さで決めています。コミットの時に 1 ETH の預け金を受け取り、リビールした人にだけ返します。預け金の役割は後の節で説明します。2 つのコントラクトは 1 つのファイルにまとめて [lab/Auction.sol](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/commit-reveal/lab/Auction.sol) に置いています。説明用の実装で、監査は受けていません。

<br>

ハッシュ値の入力は `abi.encode` で作っています。固定長の値は 32 バイトに揃え、可変長の値には長さを付けて並べるので、区切りの位置が一意に決まります。

一方で、詰めて並べる `abi.encodePacked` は、文字列のような長さの変わる値を 2 つ並べると区切りが消えます。[Solidity の ABI の仕様](https://docs.soliditylang.org/en/v0.8.28/abi-spec.html#non-standard-packed-mode)も、`abi.encodePacked("a", "bc")` と `abi.encodePacked("ab", "c")` が同じバイト列になる例を挙げ、特別な理由が無ければ `abi.encode` を使うよう勧めています。コミットでこの衝突が起きると、同じハッシュ値を別の中身として明かせてしまいます。

---

### salt が要る理由

ハッシュ値から元の入力を求められないのは、入力の候補が十分に多い時だけです。入札額が 1〜10,000 の整数だと分かっていれば、Bob は候補を全部ハッシュして、mempool で見たコミットと比べるだけで済みます。実験の Python では、次の関数で総当たりしています。

```python
def commitment(addr, amount, salt):
    return keccak256(word(addr) + word(amount) + word(salt))  # abi.encode と同じ並び


def brute_force(addr, target, candidates, salt=b'\0' * 32):
    """候補の入札額を全部ハッシュして、mempool で見たコミットと比べる。"""
    start = time.perf_counter()
    for n, amount in enumerate(candidates, 1):
        if commitment(addr, amount, salt) == target:
            return amount, n, time.perf_counter() - start
    return None, len(candidates), time.perf_counter() - start
```

`word` は値を 32 バイトに揃える補助関数、`keccak256` は [EIP-712 のノート](../eip-712/)の実験で使った、Python だけで書いた Keccak-256 です。Alice の送り主のアドレスはトランザクションから分かるので、Bob が知らないのは入札額と salt だけです。

Alice が salt を 0 に固定してコミットすると、次のようになりました。

```text
== (2) commit without salt (salt = 0): bob brute-forces 1..10000
  bob sees commitment 0xa1c192f5c5b92806.. ; found amount=50 after 50 hashes, 0.029 s
  block 8:
    #0 alice tip 1 gwei  reveal(50, 0)  -> ok
    #1 bob   tip 1 gwei  reveal(51, 0x357b03b9..)  -> ok
  winner bob, highest 51
  vote yes/no without salt: found choice=1 after 2 hashes
```

Bob は 50 回のハッシュで Alice の入札額を当て、51 でコミットして勝ちました。コミット・リビールの形をとっていても、salt が無ければ先回りを防げません。最後の行は賛成・反対の投票で、候補が 2 つなので 2 回のハッシュで分かります。

<br>

Alice が 32 バイトの乱数を salt にすると、同じ総当たりでは何も見つかりません。

```text
== (3) commit with a 32-byte random salt
  bob brute-forces 1..10000 with salt=0: found=None after 10000 hashes, 5.691 s
```

Bob が当てるには、入札額に加えて salt の 2^256 通りも試す必要があります。仮に 1 秒に 1 兆回ハッシュできても、2^256 回には 10^57 年以上掛かります。実験の Python の実装は 1 秒に約 1,500 回しかハッシュできませんが、salt が無い場合は候補が 1 万通りでも数秒で終わります。

salt は[推測できない乱数](/notes/security/random-number/)にする必要があります。時刻や連番のように候補を絞れる値では、salt の候補ごとに総当たりされます。また、同じ salt を使い回すと、前回のリビールで公開された salt から次のコミットも総当たりできます。

---

### 写したコミットと明かさない参加者

salt があっても、他人のコミットをそのまま写すことはできます。相手のリビールを mempool で見てから同じ値と salt で明かせば、写したコミットで相手と同じ入札を出せてしまいます。先ほどのコントラクトがハッシュ値の入力に `msg.sender` を含めているのは、これを防ぐためです。

実験では、Bob が Alice のコミットを写し、Carol は 70 でコミットしました。リビールの段では、Bob は mempool で Alice のリビールを読み、同じ引数を高い手数料で先に送っています。

```text
  block 10:
    #0 alice tip 1 gwei  commit(0x66beafdf..)  -> ok
    #1 bob   tip 1 gwei  commit(0x66beafdf..)  -> ok
    #2 carol tip 1 gwei  commit(0xba0da769..)  -> ok
  bob copies alice's pending reveal (amount and salt) with a higher tip
  block 14:
    #0 bob   tip 3 gwei  reveal(50, 0x1426f244..)  -> reverted (mismatch)
    #1 alice tip 1 gwei  reveal(50, 0x1426f244..)  -> ok
  winner alice, highest 50; deposits left in contract 2 ETH (bob and carol did not reveal)
```

Bob のリビールは、自分のアドレスで計算したハッシュ値がコミットと一致せず、`mismatch` で取り消されました。salt は実行ごとに乱数で作るので、出力のハッシュ値は実行のたびに変わります。Alice は自分のリビールで勝っています。

<br>

Carol は 70 でコミットしたのにリビールせず、締め切りが過ぎました。そのため、勝者は 70 の Carol ではなく、50 の Alice になっています。入札額を明かすかどうかは、コミットした本人が締め切りまで選べます。他の人のリビールを見てから、自分が明かす方が得かを決められるわけです。オークションなら負けが分かった入札を明かさずに済み、くじや乱数なら結果が気に入らない時に明かさないことで結果を変えられます。

そこで、コミットの時に預け金を受け取り、明かした人にだけ返すのが一般的です。実験のコントラクトにも、明かさなかった Bob と Carol の預け金 2 ETH が残りました。ただし、預け金は明かさない選択に値段を付けるだけで、その選択自体は無くせません。結果を変えて得られる額が預け金を上回るなら、明かさない方が得になります。

明かす操作を本人に任せることは、時間を隔てた約束としての限界でもあります。著者は weeknotes の「[ブロックチェーンの応用先としてのタイムカプセル](/weeknotes/2026-08-24/#ブロックチェーンの応用先としてのタイムカプセル)」で、10 年後に開く何かを分散したノードで管理する案に触れています。コミット・リビールでは、本人がいなくなれば中身は出てきません。本人がいなくても時間が来れば開ける仕組みには、[Timelock Encryption](/notes/security/timelock-encryption/) のような時限暗号が必要です。

---

### ENS の名前の登録

ENS（Ethereum Name Service）は、`alice.eth` のような名前をアドレスに対応付ける仕組みです。`.eth` の名前を登録するコントラクト ETHRegistrarController は、コミット・リビールで登録を受け付けます。

[ENS のドキュメント](https://docs.ens.domains/registry/eth)によると、この仕組みの目的は、mempool で `register` のトランザクションを見た参加者に先回りされないことです。欲しい名前をいきなり `register` で送ると、mempool でその名前を見た人が先に同じ名前を登録できるからです。

[v1.7.0 のソース](https://github.com/ensdomains/ens-contracts/blob/v1.7.0/contracts/ethregistrar/ETHRegistrarController.sol#L210-L235)では、コミットのハッシュ値を次のように作ります。

```solidity
function makeCommitment(
    Registration calldata registration
) public pure override returns (bytes32 commitment) {
    // （入力の検査は省略）
    return keccak256(abi.encode(registration));
}
```

`Registration` には、名前（label）、所有者（owner）、期間、`secret`、名前の解決先（resolver）などが入ります。`secret` が本記事の salt で、ドキュメントは利用者が作る 32 バイトの乱数としています。名前は辞書の単語のように候補を絞りやすいので、`secret` が無ければ総当たりで当てられます。所有者もハッシュ値の入力に入るので、他人のリビールを写しても、名前は元の所有者に登録されます。

`register` は、コミットから `minCommitmentAge` 以上、`maxCommitmentAge` 未満の時間が経ったことを[確かめます](https://github.com/ensdomains/ens-contracts/blob/v1.7.0/contracts/ethregistrar/ETHRegistrarController.sol#L263-L283)。ドキュメントによると最短は 60 秒で、v1.7.0 の[デプロイのスクリプト](https://github.com/ensdomains/ens-contracts/blob/v1.7.0/deploy/ethregistrar/04_deploy_eth_registrar_controller.ts)では `maxCommitmentAge` が 86400 秒（24 時間）です。

コミットの直後に登録できると、mempool で他人の `register` を見た人が、同じ名前で自分のコミットと `register` を作り、高い手数料で前に割り込ませられます。最短の待ち時間があると、割り込む側の新しいコミットは間に合いません。オークションのような全員共通の締め切りが無い代わりに、コミットごとの待ち時間で同じ役割を果たしています。

---

### RANDAO と最後に明かす人

ブロックチェーンの上で乱数を作るのは難しい問題です。コントラクトの実行は全ノードで同じ結果になる必要があり、ブロックを作る者は前のブロックの情報を選べるからです。

[RANDAO](https://github.com/randao/randao/blob/53f04cd575a3a9026108b4c85c6b583124872853/README.md) は、参加者全員の秘密の値を混ぜて乱数を作るコントラクトの案で、コミット・リビールをそのまま使っています。各参加者は預け金と一緒に秘密の値のハッシュ値を送り、次の段で値を明かします。明かさなかった参加者の預け金は没収され、その回の乱数の生成は失敗します。

[Proof of Stake](../proof-of-stake/) の Ethereum も、この考え方をプロトコルに組み込んでいます。Ethereum では、12 秒ごとの枠（スロット）ごとに、ブロックを作る提案者が 1 人選ばれ、32 スロットをまとめてエポックと呼びます。エポックの終わりの乱数が、先のエポックの提案者を決めるのに使われます。

[consensus-specs v1.6.1](https://github.com/ethereum/consensus-specs/blob/v1.6.1/specs/phase0/beacon-chain.md) の `process_randao` では、ブロックの提案者がエポック（epoch）の番号に BLS 署名（同じ鍵と同じメッセージからは毎回同じ値になる署名）をした値（`randao_reveal`）をブロックに入れ、そのハッシュ値を乱数の蓄積（RANDAO mix）に XOR で混ぜます。

```python
def process_randao(state: BeaconState, body: BeaconBlockBody) -> None:
    epoch = get_current_epoch(state)
    # Verify RANDAO reveal
    proposer = state.validators[get_beacon_proposer_index(state)]
    signing_root = compute_signing_root(epoch, get_domain(state, DOMAIN_RANDAO))
    assert bls.Verify(proposer.pubkey, signing_root, body.randao_reveal)
    # Mix in RANDAO reveal
    mix = xor(get_randao_mix(state, epoch), hash(body.randao_reveal))
    state.randao_mixes[epoch % EPOCHS_PER_HISTORICAL_VECTOR] = mix
```

コミットに当たるのは、事前に登録した公開鍵です。同じ鍵と同じエポックからは同じ署名しか作れないので、提案者は混ぜる値を選べず、事前にハッシュ値を送る段も要りません。それでも、ブロックを出すか出さないかは選べます。

{{< figure src="images/commit-reveal_randao.webp" alt="エポック（32 スロット）の終わりの部分。スロット 29、30 の提案者は値を混ぜ済みで、エポックの最後のスロット 31 の提案者から 2 本の矢印が分かれる。ブロックを出せば乱数 A、出さなければ乱数 B になる。自分の値は出す前から分かるので A と B を先に計算でき、有利な方を選べる代わりに、出さなければ報酬を失う" caption="最後の提案者は、ブロックを出すかどうかで 2 つの結果から選べる" align="center" >}}

上記の図のように、自分の値は出す前から分かるので、提案者は 2 通りの結果を先に計算できます。前節の Carol と同じく、最後に明かす人が結果を選べる問題です。[EIP-4399](https://eips.ethereum.org/EIPS/eip-4399) は、これを提案者 1 人がスロットごとに持つ 1 ビットの影響力と呼び、その代償はブロックを出さないことで失う報酬と手数料だとしています。連続する n スロットの提案者が結託すれば n ビットになります。

この乱数は、コントラクトからは [EVM](../evm/) の `PREVRANDAO` 命令で読めます（The Merge で DIFFICULTY 命令の意味を変えたもので、経緯は [EVM Opcode History](../evm-opcode-history/#命令表の変遷)）。EIP-4399 は、乱数を使うアプリケーションに、締め切りから十分に先のエポックの値を使うよう勧めています。

---

### 利点

- 締め切りまで中身を隠したまま、後から変えられない約束を作れる
- ハッシュ関数と比較だけで実装でき、特別な暗号や信頼できる第三者が要らない
- プロトコルや手数料の仕組みを変えずに、mempool で中身を読む先回りを防げる
- リビールが公開されるので、誰でも照合をやり直して結果を確かめられる

### 欠点

コミット・リビールは、中身を明かす時期を締め切りの後へずらすことで先回りを防ぎます。その代わりに、次の制約があります。

- トランザクションが 2 回要り、gas の手数料と待ち時間が増える
- 明かすかどうかを本人が選べ、預け金では明かさない選択に値段を付けることしかできない
- salt を失うと明かせなくなり、推測できる salt や使い回した salt は総当たりされる
- コミットのトランザクションそのもの（誰が・いつ・いくら預けたか）は隠せない
- 締め切りの長さを決める必要があり、短すぎると混雑時に間に合わず、長すぎると結果が遅れる

### 適さないケース

- 1 回のトランザクションで即座に結果が要る交換や送金
- 参加者が最後の値を出すかどうかで、大きな額が動く乱数（くじの賞金など）
- salt を安全に保管できない利用者に、候補が少ない値を扱わせる場合
- 中身を明かさないまま比べたい場合（入札額を最後まで隠したい場合など）

コミット・リビールが隠すのは締め切りまでで、リビールの後は全員が中身を読めます。最後まで伏せたい場合は、[ゼロ知識証明](../zero-knowledge-proof/)のような別の仕組みを組み合わせる必要があります。
