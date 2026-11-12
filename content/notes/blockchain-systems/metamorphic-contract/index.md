---
title: "Metamorphic Contract - 同じアドレスでのコードの置き直し"
date: 2026-11-11
draft: false
series: ["技術ノート", "Blockchain Systems"]
tags: ["blockchain", "ethereum", "create2", "selfdestruct", "smart-contract"]
weight: 22
wrapTables: true
topics: ["Smart Contract"]
---

Ethereum の[スマートコントラクト](../smart-contract/)（チェーン上で動くプログラム。以下、コントラクト）には、一度置いたコードを書き換える命令がありません。そのため、利用者は、あるアドレスのコードを読んだり監査の結果を確認したりしてから、そのアドレスに資産を預けたり権限を与えたりします。後からコードが変わらないことが前提です。

metamorphic contract は、この前提を崩す手法です。コントラクトを消す命令 `SELFDESTRUCT` で消してから作り直し、同じアドレスに別のコードを置きます。2024 年 3 月の Ethereum の仕様の更新（Cancun）より前は、この手法が使えました。

<br>

本記事では、この手法が成り立つアドレスの規則を振り返ってから、置き直しの手順、2023 年の Tornado Cash の事故、Cancun で塞がれた理由を順に説明します。最後に、Cancun の前後の仕様で同じ手順を手元のチェーンで動かし、結果を比べます。アドレスの規則そのものは [Ethereum Address](../ethereum-address/) で説明しています。

---

### 前提となるアドレスの規則

コントラクトのアドレスは、作る時に次の 2 つのどちらかの規則で決まります（[Ethereum Address](../ethereum-address/)）。

- `CREATE`: 作り手のアドレスと、作り手の nonce から計算する。コントラクトの nonce は 1 から始まり、`CREATE` のたびに 1 増える。
- `CREATE2`: 作り手のアドレスと、作り手が選ぶ 32 バイトの値 salt と、initcode（作る時に 1 度だけ動き、置くコードを返すプログラム）のハッシュから計算する。

計算したアドレスのアカウントに既にコードがあるか、そのアカウントの nonce が 0 でない場合、作成は失敗します。そのため、同じアドレスに作り直すには、先に今のコントラクトを消す必要があります。

`SELFDESTRUCT` は、Cancun より前は、コントラクトのコードとストレージ（storage）を消し、残高を指定した先へ送る命令でした。アカウントごと消えるので、nonce も消えます。

---

### 置き直しの手順

`CREATE2` だけでは、別のコードを同じアドレスに置けません。置くコードを変えると initcode が変わり、アドレスも変わるからです。そこで、コードに関係なくアドレスが決まる `CREATE` を間に挟みます。本記事では、間に挟むコントラクトを Deployer と呼びます。手順は以下の通りです。

1. ファクトリ（コントラクトを作るためのコントラクト）が `CREATE2` で、固定の salt と initcode から Deployer を作る。Deployer のアドレスは毎回同じになる。
2. Deployer が `CREATE` で V1 を作る。アドレスは Deployer と nonce 1 で計算される。
3. V1 と Deployer を `SELFDESTRUCT` で消す。V1 を消すのは、手順 5 で同じアドレスを空けておくため。Deployer はアカウントごと消えるので、nonce も無くなる。
4. 1 と同じ `CREATE2` で Deployer を作り直す。nonce は再び 1 から始まる。
5. Deployer が `CREATE` で V2 を作る。材料が 2 と同じなので、V1 と同じアドレスに V2 が置かれる。

以下は、この手順を 1 枚にした図です。図の番号は手順の番号です。

{{< figure src="images/metamorphic-contract_concept.webp" alt="ファクトリから 1. CREATE2（salt・initcode 固定）の矢印で Deployer（アドレスは毎回同じ）へ、Deployer から 2・5. CREATE（Deployer・nonce 1）の矢印で置き場所 0xCB8956e6… へ。Deployer の下に「3. Deployer を消す、nonce も消える」と「4. 作り直す、nonce は 1 から」の輪がある。置き場所の下に「2. V1 を置く」「3. V1 を消す」「5. V2 を置く」。下に「2024 年 3 月の Cancun 以降は、手順 3 でアカウントが消えず、手順 4 が失敗する」" caption="Deployer を消して作り直し、同じ置き場所に別のコードを置く" align="center" >}}

要点は、Deployer を消して作り直すと nonce が 1 に戻り、作成先も前と同じアドレスになることです。

V1 と V2 の initcode は違いますが、手順 2 と 5 の `CREATE` の材料には入らないので、アドレスは変わりません。

---

### Tornado Cash のガバナンスの乗っ取り

2023 年 5 月の Tornado Cash の事故では、この手順が使われました（[rekt.news の解析](https://rekt.news/tornado-gov-rekt)）。Tornado Cash は、送金元と送金先のつながりを見えにくくするサービスです。運営の変更は、ガバナンス（トークンの保有者が提案に投票し、可決した提案のコントラクトを実行する仕組み）で決めていました。

1. 攻撃者は、以前の提案と同じ処理だとうたう提案のコントラクトを出した。
2. 投票者は、以前と同じだという説明を信じ、提案は可決された。
3. 攻撃者は提案のコントラクトを消し（置き直しの手順 3）、[同じアドレスに別のコードを置き直した](https://etherscan.io/address/0xC503893b3e3c0C6b909222b45f2a3a259a52752D)（手順 4〜5）。
4. 可決済みの提案として置き直したコードが実行され、ガバナンスの票が攻撃者に集まった。

投票で承認されたのは、投票の時点でそのアドレスにあったコードです。アドレスで提案を指していても、その中身が投票の後も同じとは限りませんでした。

---

### Cancun での変更

2024 年 3 月 13 日の Cancun で有効になった [EIP-6780](https://eips.ethereum.org/EIPS/eip-6780)（EIP は Ethereum の仕様変更の提案）により、`SELFDESTRUCT` でアカウントが消えるのは、コントラクトを作ったのと同じトランザクションの中で呼んだ場合だけになりました。別のトランザクションで呼ばれた `SELFDESTRUCT` は残高を送るだけで、コードも nonce も消しません。

そのため、手順 3 の後も Deployer は残り、手順 4 の `CREATE2` は、消えずに残った Deployer に当たって失敗します。仕様の更新ごとの `SELFDESTRUCT` の違いは、[Ethereum Hard Forks](../ethereum-hard-forks/#selfdestruct-の意味) でも確認しています。

---

### ローカルでの比較

Cancun の前後で、手順 1〜5 の結果が変わるかを確認しました。チェーンには、開発用に PC の中だけで動く Ethereum のノード [Anvil](https://getfoundry.sh/anvil/overview/) を使います。Anvil は、`--hardfork` の指定で、どの仕様の更新までの規則で動くかを選べます。環境と、アドレスを計算する Python のコードは [Ethereum Address の実験](../ethereum-address/#ローカルでの計算と照合)と共通です。

以下は、実験に使ったコントラクト（[Address.sol](../ethereum-address/lab/Address.sol)）の抜粋です。学習用に書いたもので監査しておらず、`kill()` には誰でも呼べるという問題があります。

```solidity
contract Factory {
    // CREATE2 of a Deployer: same salt -> same Deployer address.
    function deployDeployer(bytes32 salt) external returns (address) {
        return address(new Deployer{salt: salt}());
    }
}

contract Deployer {
    // CREATE: the address depends on this Deployer and its nonce (starts at 1).
    function deploy(bytes memory initcode) external returns (address a) {
        assembly {
            a := create(0, add(initcode, 32), mload(initcode))
        }
        require(a != address(0), "create failed");
    }

    function kill() external {
        selfdestruct(payable(msg.sender));
    }
}

contract V1 {
    function version() external pure returns (uint256) {
        return 1;
    }

    function kill() external {
        selfdestruct(payable(msg.sender));
    }
}
```

`V2` は `version()` が 2 を返すほかは `V1` と同じです。コンパイルは、比べる全ての仕様で動くように、Cancun の 1 つ前の [Shanghai](https://ethereum.org/en/history/#shapella) 向けにしました。

<br>

以下は、手順 1〜5 を別々のトランザクションで送る部分で、[run.py](../ethereum-address/lab/run.py) からの抜粋です。`n.send` がトランザクションを送って結果を返し、`ok` はその成否（1 が成功）、`returned_address` は呼び出しが返すアドレスを先に問い合わせる補助関数です。`create2_address` と `create_address` は、Python で計算したアドレスです。

`selector` は呼ぶ関数を指す 4 バイト、`word` は 32 バイトの値、`abi_bytes` はバイト列の引数の符号化、`bins` はコンパイルしたコントラクトの一覧です。`dd` は手順 1 と 4 で Deployer を作る呼び出し、`deploy` は手順 2 と 5 で Deployer に V1・V2 を作らせる呼び出しです。

```python
for fork in ('shanghai', 'cancun', 'prague'):
    n = Node(fork, 31337, fork)
    nodes.append(n)
    factory = created(n.send(None, bins['Factory']))
    dd = selector('deployDeployer(bytes32)') + word(0)
    deployer = returned_address(n, factory, dd)
    assert ok(n.send(factory, dd)) == 1
    assert deployer == create2_address(factory, word(0), bins['Deployer'])
    deploy = selector('deploy(bytes)')
    target = returned_address(n, deployer, deploy + abi_bytes(bins['V1']))
    assert ok(n.send(deployer, deploy + abi_bytes(bins['V1']))) == 1
    assert target == create_address(deployer, 1)
    v_before = int.from_bytes(n.call(target, selector('version()')), 'big')
    assert ok(n.send(target, selector('kill()'))) == 1    # V1 SELFDESTRUCT
    assert ok(n.send(deployer, selector('kill()'))) == 1  # Deployer SELFDESTRUCT
    sizes = f'{n.code_size(target)}/{n.code_size(deployer)} bytes'
    redeploy = ok(n.send(factory, dd))                     # CREATE2 the Deployer again
    if redeploy:
        assert n.nonce(deployer) == 1
    target2 = returned_address(n, deployer, deploy + abi_bytes(bins['V2']))
    assert ok(n.send(deployer, deploy + abi_bytes(bins['V2']))) == 1
    assert target2 == create_address(deployer, 1 if redeploy else 2)
    v_after = int.from_bytes(n.call(target2, selector('version()')), 'big')
    v_old = int.from_bytes(n.call(target, selector('version()')) or bytes(32), 'big')
```

結果は以下の通りです（[出力](../ethereum-address/lab/output/summary.txt)の後半）。`code after kill` は手順 3 の後の V1 と Deployer のコードの大きさ、`v at 1st` は最後に最初のアドレスへ `version()` を呼んだ結果、`status=1` はトランザクションの成功、`status=0` は失敗です。

```text
fork     | 1st target | v | code after kill | redeploy Deployer | 2nd target | v | v at 1st
shanghai | 0xCB8956e6 | 1 | 0/0 bytes       | status=1          | 0xCB8956e6 | 2 | 2
cancun   | 0xCB8956e6 | 1 | 218/930 bytes   | status=0          | 0x673a327D | 2 | 1
prague   | 0xCB8956e6 | 1 | 218/930 bytes   | status=0          | 0x673a327D | 2 | 1
```

以下は、手順の段ごとに、最初のアドレス `0xCB8956e6…` にあるコードを並べた図です。

{{< figure src="images/metamorphic-contract_redeploy.webp" alt="上の段の Shanghai では、0xCB8956e6… のコードが V1（version() = 1）から、消した後の空（0 バイト）を経て V2（version() = 2）に変わる。下の段の Cancun 以降では、消した後も V1 が 218 バイトのまま残り、作り直しの後も V1 のまま。下に赤い × と「Deployer を作り直せない」「V2 は 0x673a327D… へ」" caption="1 つのアドレスにあるコードの移り変わり" align="center" >}}

Shanghai では、`SELFDESTRUCT` の後に V1 も Deployer も 0 バイトになり、同じ `0xCB8956e6…` に V2 が置かれました。Cancun と、次の [Prague](https://ethereum.org/en/history/#pectra) では、コードが残ったまま Deployer の作り直しが失敗し（`status=0`）、V2 は nonce 2 で別のアドレスに作られました。元のアドレスは 1 を返し続けます。

---

### Cancun 以降に残る仕組み

Cancun 以降も、同じトランザクションの中で作って消したアドレスには、後のトランザクションで別のコードを作れます。しかし、そのコードは 1 つのトランザクションの中にしか無かったので、トランザクションをまたいで誰かが確認したコードが差し替わることはありません。

ただし、コードが変わらなくても振る舞いが変わる仕組みは残っています。処理を担うコントラクト（実装）の参照先をストレージに持つ[プロキシ](../upgradeable-proxy/)は、参照先を差し替えると別の処理を行います。また、[EIP-7702](https://eips.ethereum.org/EIPS/eip-7702) で EOA（秘密鍵で操作するアカウント）がコードの実行を任せた委任先も、後から書き換えられます（[Ethereum Account Model](../ethereum-account-model/)）。アドレスのコードを確認する時は、そのコードが別のアドレスの何に処理を任せているかまで見る必要があります。
