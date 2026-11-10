---
title: "ERC-1967 / ERC-7201 - プロキシで更新できるコントラクトと storage の配置"
date: 2026-11-10
draft: false
series: ["技術ノート", "Blockchain Systems"]
tags: ["blockchain", "ethereum", "smart-contract", "proxy", "erc-1967", "erc-7201"]
weight: 22
wrapTables: true
topics: ["Smart Contract"]
---

カウンターの `increment()` を 1 回呼んだだけで、そのコントラクトが以後まともな値を返さなくなることがあります。後述の実験では、呼び出しの前に保存領域の slot 0 にあった `0x…5fbdb2315678afecb367f032d93f642f64180aa3` が、呼び出しの後に末尾が `aa4` に増えていました。この値は、カウンターの値ではなく、処理を任せる先のコントラクトのアドレスでした。

アップグレード可能なプロキシ（upgradeable proxy）は、利用者が呼ぶアドレスとデータを固定したまま、処理するコードだけを別のコントラクトに差し替える構成です。上記の事故は、プロキシと差し替え先が保存領域の同じ場所を別の意味で使った時に起きます。

[ERC-1967](https://eips.ethereum.org/EIPS/eip-1967) は、差し替え先のアドレスなどを置く場所を決めた規格です。

[ERC-7201](https://eips.ethereum.org/EIPS/eip-7201) は、コントラクトの変数をまとめて置く場所の計算式と、その注記の書き方を決めた規格です。

資産を預かるコントラクトの開発者は、不具合が見つかっても利用者にアドレスの移行を頼まずに直したいと考えます。一方で、利用者や監査する人は、そのアドレスの中身を誰が差し替えられるのかを確かめる必要があります。以下は、プロキシと 2 つの実装の関係を示した図です。

{{< figure src="images/upgradeable-proxy_concept.svg" alt="利用者はプロキシのアドレスだけを呼ぶ。プロキシの中に slot 0 の owner、slot 1 の balance、名前空間、0x3608… の実装のアドレスが並び、実装のアドレスの欄から DELEGATECALL の矢印が実装 V2 に伸びている。差し替え前の実装 V1 へは点線だけが残る" caption="データはプロキシに残し、実装のアドレスだけを差し替える" align="center" >}}

上記の図のように、データはすべてプロキシ側にあり、実装 V1・V2 はコードだけを提供します。差し替えで変わるのは、黄土色の欄にある 1 つのアドレスです。

<br>

本記事では、[Smart Contract](../smart-contract/) で触れた「あらかじめ用意した更新機構」の中身を説明します。

- コードを変えられないのに、なぜ処理を差し替えられるのか。
- 差し替えた時に、保存されたデータはどう扱われるのか。
- ERC-1967 は、なぜハッシュから 1 を引いた場所を使うのか。
- constructor の代わりに初期化関数を使う理由と、初期化を忘れた事故。
- ERC-7201 の名前空間は、従来の `__gap` と何が違うのか。

後半では、ローカルの開発用ノードで各現象を再現します。複数の実装を関数ごとに切り替える Diamond（[ERC-2535](https://eips.ethereum.org/EIPS/eip-2535)）や、EOA の委任（[EIP-7702](https://eips.ethereum.org/EIPS/eip-7702)）は扱いません。

---

### プロキシが必要な理由

Ethereum では、コントラクトのアドレスに置いたコードを後から書き換える命令がありません。2024 年 3 月のハードフォーク Cancun より前は、`SELFDESTRUCT` と `CREATE2` を組み合わせて同じアドレスに別のコードを置き直す方法がありましたが、それも塞がれました（[Ethereum Address](../ethereum-address/) の metamorphic contract、[Ethereum Hard Forks](../ethereum-hard-forks/) の SELFDESTRUCT）。

不具合を直すために新しいアドレスへ移る方法もあります。しかし、残高や設定は古いアドレスの storage にあり、他のコントラクトや取引所も古いアドレスを登録しています。移行には、データの移し替えと、すべての参照先の変更が必要になります。

そこで、利用者が呼ぶアドレス（プロキシ）と、処理のコード（実装）を分けます。プロキシは自分のコードをほとんど持たず、届いた呼び出しを実装に任せます。実装のアドレスを書き換えれば、利用者から見たアドレスとデータはそのまま、処理だけが新しくなります。

「ブロックチェーンのコントラクトは、一度デプロイしたら変わらない」と思うかもしれません。しかし、変わらないのはアドレスに置かれたコードのバイト列で、プロキシの振る舞いは参照先の差し替えで変わります。利用者が確かめるべきなのは、誰が参照先を差し替えられるのか、差し替えに待ち時間や複数人の承認があるのか、です。

2025 年 2 月の Bybit の事故では、Safe のプロキシの参照先が攻撃者の実装に差し替えられました（[Wallet の過去のセキュリティ事件](../wallet/#bybitsafe-の承認処理の乗っ取り)）。

---

### DELEGATECALL による委譲

プロキシは、[EVM](../evm/) の `DELEGATECALL` という命令で実装を呼びます。通常の `CALL` は、呼び先のコードを呼び先の storage で実行します。`DELEGATECALL` は、呼び先のコードを呼び出し元の storage で実行します。2016 年のハードフォーク Homestead で [EIP-7](https://eips.ethereum.org/EIPS/eip-7) として追加された命令です。

| 命令 | 実行するコード | 読み書きする storage | 実行中の `msg.sender` |
| --- | --- | --- | --- |
| `CALL` | 呼び先 | 呼び先 | 呼び出し元 |
| `DELEGATECALL` | 呼び先 | 呼び出し元 | 呼び出し元を呼んだアカウント |

プロキシはこの性質を使い、実装のコードを自分の storage の上で動かします。プロキシに定義の無い関数が呼ばれると、[Solidity](https://www.soliditylang.org/) の [`fallback` 関数](https://docs.soliditylang.org/en/v0.8.28/contracts.html#fallback-function)が受け取り、同じ入力のまま実装へ `DELEGATECALL` します。実装の関数が `count += 1` を実行すると、増えるのはプロキシの storage の値です。

つまり、実装はコードの置き場所で、データの置き場所はプロキシです。実装のアドレス自身の storage は、通常は使われません。この分担が、後の節の衝突と初期化の問題につながります。

---

### storage の衝突

Solidity は、状態変数を宣言した順に（32 バイトに満たない型は同じ slot に詰めながら）slot 0、1、2 と並べます（[Layout of State Variables in Storage](https://docs.soliditylang.org/en/v0.8.28/internals/layout_in_storage.html)）。親コントラクトの変数は、継承の順に前から並びます。`DELEGATECALL` では、プロキシと実装の両方が、この番号を自分の変数の場所と考えて同じ storage を読みます。ここから、2 種類の衝突が起きます。

1 つ目は、プロキシの変数と実装の変数が同じ slot に載る衝突です。冒頭の例では、プロキシが実装のアドレスを slot 0 に置き、実装のカウンター `count` も slot 0 でした。`count += 1` はアドレスの値に 1 を足し、以後の呼び出しはコードの無いアドレスに委譲されます。

ちなみに、Safe は現在の [v1.5.0](https://github.com/safe-fndn/safe-smart-account/blob/v1.5.0/contracts/common/Singleton.sol) でも実装のアドレスを slot 0 に置いています。実装側の先頭に同じ変数を宣言させ、両者の意味を揃えることで衝突を避けています（[Multisig の Safe](../multisig/)）。

2 つ目は、実装を更新した時に変数の並びがずれる衝突です。例えば、V1 が `owner`、`balance` の順に宣言し、V2 で先頭に `fee` を足すと、V2 は slot 0 を `fee`、slot 1 を `owner` と読みます。後述の実験で V2 に差し替えた直後の値は、以下の通りでした。

{{< figure src="images/upgradeable-proxy_layout.svg" alt="中央がプロキシの storage の slot 0・1・2 で、値は 0x7099…79c8、0x…64、0。左の V1 はそれぞれを owner = 0x7099…79c8、balance = 100、未使用と読む。右の V2Bad は fee = 6.43 × 10^47、owner = 0x…0064、balance = 0 と読む" caption="同じ slot の値を V1 と V2Bad が別の変数として読む" align="center" >}}

上記の図の `fee` は、slot 0 のアドレスを 1 つの整数として読んだ 642829559307850963015472508762062935916233390536 です。

slot の値は差し替えの前後で同じです。変わったのは、実装がそれぞれの slot に付ける意味だけです。そのため、実装を更新してもデータは新しい実装に移りません。データはプロキシに残ったまま、新しい実装の並びで読まれます。

この状態で V2 の `setFee(5)` を呼ぶと slot 0 が 5 になり、末尾に `fee` を足した別の V2 に差し替えても、`owner` は 0x…05 のままでした。

OpenZeppelin の[ガイド](https://docs.openzeppelin.com/upgrades-plugins/writing-upgradeable)も、状態変数の順序と型を変えず、新しい変数は末尾に足すよう求めています。

---

### ERC-1967 の決まった slot

1 つ目の衝突は、プロキシが使う値を実装の変数が並ぶ場所から遠くに置けば避けられます。ERC-1967 は、その場所を次の式で決めています（2019 年作成、状態は Final）。

```solidity
bytes32(uint256(keccak256("eip1967.proxy.implementation")) - 1)
```

| 値 | 文字列 | slot |
| --- | --- | --- |
| 実装のアドレス | `eip1967.proxy.implementation` | `0x3608…2bbc` |
| 管理者のアドレス | `eip1967.proxy.admin` | `0xb531…6103` |
| beacon のアドレス | `eip1967.proxy.beacon` | `0xa3f0…3d50` |

slot は 2 の 256 乗通りあり、Solidity が順に並べる変数は 0 から数えた小さい番号に集まります。Keccak-256（Ethereum が使う[ハッシュ関数](../hash-function/)）の出力は 2 の 256 乗通りの値に散らばるので、その小さい番号の範囲に入る確率は無視できます。

では、ハッシュの値をそのまま使わずに 1 を引くのはなぜでしょうか。Solidity も、mapping の値や可変長配列の中身を `keccak256(キーと slot 番号)` や `keccak256(slot 番号)` の場所に置きます。どちらも、ハッシュの入力（前像）が分かっている場所です。

ERC-1967 は 1 を引くことで、入力が誰にも分からない場所にしています。仕様は、細工したキーを使った mapping の値でこの場所を上書きされないように、前像の無い場所を選んだと説明しています。以下は、実装のアドレスの slot と、その 1 つ隣の slot を並べた図です。

{{< figure src="images/upgradeable-proxy_slot_space.svg" alt="横長の帯が 0 から 2 の 256 乗 − 1 までの slot の空間。左端の小さい番号に Solidity の状態変数、帯の途中に mapping の値の場所が散らばる。0x3608… の位置を拡大すると、0x3608…2bbd は keccak256(\"eip1967.proxy.implementation\") で前像は文字列、その 1 つ下の 0x3608…2bbc がハッシュから 1 を引いた ERC-1967 の slot で、前像は知られていない" caption="ERC-1967 の slot と、その元になったハッシュの slot" align="center" >}}

上記の図の 2 つの slot は隣どうしです。つまり、slot はランダムな値ではなく、文字列から誰でも計算できる定数です。衝突しにくい理由は、コンパイラが並べる小さい番号から遠いことと、1 を引いて前像の無い値にしたことにあります。

ERC-1967 は、値を変えた時に出すイベントも決めています。`Upgraded(address indexed implementation)`、`AdminChanged(address previousAdmin, address newAdmin)`、`BeaconUpgraded(address indexed beacon)` の 3 つです。

置き場所とイベントが決まっているので、外部のツールはコントラクトのコードを解析しなくても、決まった slot を読むだけで実装を見つけられます。仕様も、ブロックエクスプローラーを動機の代表例に挙げています。[Foundry](https://getfoundry.sh/) の `cast implementation` と `cast admin` も、この slot を読むコマンドです。差し替えの履歴は、`Upgraded` のログを追えば分かります。

---

### プロキシの型

ERC-1967 は値の置き場所だけを決め、誰がどの関数で差し替えるかは決めていません。その違いで、主に次の 3 つの型があります。

| 型 | 差し替えの関数の場所 | 特徴 |
| --- | --- | --- |
| Transparent | プロキシ | 管理者の呼び出しはプロキシの管理機能、それ以外は実装に回す |
| UUPS（[ERC-1822](https://eips.ethereum.org/EIPS/eip-1822)） | 実装 | プロキシが小さい。差し替えの関数を持たない実装に更新すると、以後は差し替えられない |
| Beacon | beacon という別のコントラクト | 多数のプロキシが 1 つの beacon から実装のアドレスを読み、まとめて差し替わる |

Transparent が管理者とそれ以外を分けるのは、プロキシの管理用の関数と実装の関数で、関数セレクタ（関数を識別する 4 バイトの値）が重なる問題を避けるためです（[OpenZeppelin の解説](https://www.openzeppelin.com/news/the-transparent-proxy-pattern)）。

Solidity の部品を集めたライブラリ OpenZeppelin Contracts の 5.x にある [TransparentUpgradeableProxy](https://docs.openzeppelin.com/contracts/5.x/api/proxy) は、作成時に管理用のコントラクト ProxyAdmin を専用に作り、そのアドレスを変更できない値にしています。同じ文書は、軽く柔軟な UUPS を推奨する方向に移っているとしています。

[ERC-4337](../erc-4337/) の参照実装の [SimpleAccountFactory](https://github.com/eth-infinitism/account-abstraction/blob/v0.9.0/contracts/accounts/SimpleAccountFactory.sol) も、スマートアカウントのアドレスに OpenZeppelin の `ERC1967Proxy` を置きます。

---

### 初期化関数が必要な理由

通常のコントラクトは、constructor で所有者などの初期値を設定します。しかし、constructor は実装をデプロイする取引の中で、実装のアドレスの storage に対して実行されます。プロキシの storage には何も設定されません。後述の実験では、constructor で `value = 42` とした実装を直接読むと 42、プロキシ経由で読むと 0 でした。

そこで、初期化を普通の関数（initializer）にして、プロキシ経由で 1 回だけ呼びます。OpenZeppelin の `ERC1967Proxy` は、作成時に実装のアドレスと初期化関数の呼び出しを受け取り、同じ取引の中で実行します。2 回目以降の呼び出しは、`initializer` 修飾子が拒否します。

問題は、実装のアドレス自身の storage も初期化されていない点です。実装の初期化関数を第三者が直接呼ぶと、その人が実装の所有者になります。実装の storage は通常使われないので無害に見えますが、所有者の権限で実装を壊せる場合、その実装に頼るすべてのプロキシが止まります。

2017 年 11 月 6 日、Ethereum のクライアントを開発していた [Parity](https://www.parity.io/) の multisig ウォレットが共有していたライブラリで、この形の事故が起きました。ウォレットは処理をライブラリに `DELEGATECALL` で任せていました。ライブラリの [`initWallet`](https://github.com/openethereum/parity-ethereum/blob/v1.8.2/js/src/contracts/snippets/enhanced-wallet.sol#L215-L226) は所有者の数が 0 の時だけ呼べる関数で、ライブラリ自身の storage では所有者が 0 人のままでした。

ある利用者がこれを呼んで所有者になり、`kill` を呼んでライブラリを消しました。`kill` の中身は、Solidity の `suicide`（`selfdestruct` の旧名）です。コードを失ったライブラリに頼るウォレットは、資金を動かせなくなりました。当事者は [GitHub の Issue](https://github.com/openethereum/parity-ethereum/issues/6995) に「I accidentally killed it.（うっかり消してしまった）」と書いています。

2021 年 9 月には、OpenZeppelin Contracts 4.1.0〜4.3.1 の `UUPSUpgradeable` に同じ種類の脆弱性が報告されました（[GHSA-5vp3-v4hc-gx76](https://github.com/OpenZeppelin/openzeppelin-contracts/security/advisories/GHSA-5vp3-v4hc-gx76)）。

[事後報告](https://forum.openzeppelin.com/t/uupsupgradeable-vulnerability-post-mortem/15680)によると、攻撃者は初期化されていない実装を初期化して管理者になり、実装を直接 `upgradeToAndCall` で呼びます。その中の `DELEGATECALL` で `SELFDESTRUCT` を実行すると実装が消え、UUPS では差し替えの関数も実装にあるので、プロキシは直せなくなります。OpenZeppelin は、資金を失ったプロジェクトは把握していないとしています。

対策は 2 つあります。4.3.2 から、差し替えの関数はプロキシ経由の呼び出しだけを受け付けます（`onlyProxy`）。また、[OpenZeppelin のガイド](https://docs.openzeppelin.com/upgrades-plugins/writing-upgradeable)は、実装の constructor で `_disableInitializers()` を呼び、実装の初期化を塞ぐよう勧めています。ちなみに、Cancun 以降の [`SELFDESTRUCT`](https://eips.ethereum.org/EIPS/eip-6780) は、作成と同じ取引の中でなければコードを消しません。

---

### ERC-7201 の名前空間

状態変数を末尾に足す規則だけでは、継承を使う時に足りません。親コントラクトの変数は子より前に並ぶので、親の新しいバージョンが変数を 1 つ足すと、子の変数が全部ずれます。

OpenZeppelin Contracts Upgradeable の 4.x は、親ごとに未使用の配列を置いて場所を予約していました。例えば、[v4.9.6 の OwnableUpgradeable](https://github.com/OpenZeppelin/openzeppelin-contracts-upgradeable/blob/v4.9.6/contracts/access/OwnableUpgradeable.sol) は `uint256[49] private __gap;` を持ちます。変数を足す時は、その分だけ配列を手で縮めます。

ERC-7201（2023 年作成、状態は Final）は、変数を構造体にまとめ、名前から計算した slot を起点に置きます。式は次の通りです。

```solidity
keccak256(abi.encode(uint256(keccak256(id)) - 1)) & ~bytes32(uint256(0xff))
```

`keccak256(id) - 1` は、Solidity が使わない場所として選ばれています。しかし、構造体は複数の slot に広がり、`keccak256(id) + n` には Solidity が使う場所が含まれ得ます。そのため、もう一度ハッシュを取ってから起点にします。最後の `& ~0xff` は下位 8 bit を 0 にし、起点を 256 の倍数に揃えます。仕様は、将来の最適化の可能性のための揃えとしています。

名前空間は、構造体に次の注記を付けて示します。

```solidity
/// @custom:storage-location erc7201:openzeppelin.storage.Ownable
struct OwnableStorage {
    address _owner;
}
```

起点は名前だけから計算するので、親コントラクトの継承の順を入れ替えても、各名前空間の場所は変わりません。後述の実験では、`a` と `b` を持つ 2 つの親の継承の順を入れ替えると slot が入れ替わりました。一方で、名前空間だけを使う実装では、Solidity が並べる変数が 0 個でした。`__gap` のように、親ごとに残りの slot の数を手で数える必要もありません。

ERC-7201 は、計算式と注記の書き方を決めた規約で、新しい命令もハードフォークも必要ありません。起点は定数として埋め込み、`sload` と `sstore` は既存の命令のままです。

Solidity は 0.8.29（2025 年 3 月）で storage の起点を移す `layout at` 指定、0.8.35（2026 年 4 月）で `erc7201` の計算をコンパイラが行う組み込み関数を加えました（[Changelog](https://github.com/ethereum/solidity/blob/develop/Changelog.md)）。どちらもコンパイル時に定数を計算するだけです。

[OpenZeppelin Contracts Upgradeable](https://github.com/OpenZeppelin/openzeppelin-contracts-upgradeable/tree/v5.7.0) は 5.0 からこの形に移りました。本記事で確かめた v5.7.0 では、`OwnableUpgradeable` が `openzeppelin.storage.Ownable`、`Initializable`（定義は OpenZeppelin Contracts 側）が `openzeppelin.storage.Initializable` の名前空間を使っています。

---

### anvil での再現

ここまでの現象は、開発ツール群 Foundry に含まれる開発用ノード [Anvil](https://getfoundry.sh/anvil/overview) で確かめました。公開ネットワークには接続せず、Anvil が用意する公開のテスト用アカウントだけを使います。使用したバージョンは Anvil・cast 1.7.1、solc 0.8.28 で、EVM の規則は 2025 年 5 月のハードフォークである [Prague](https://eips.ethereum.org/EIPS/eip-7600) に固定しています。

コントラクトは 2 つのファイルに分けています。[Study.sol](lab/Study.sol) は本記事のために書いた学習用のコードで、監査していません。[Box.sol](lab/Box.sol) は [OpenZeppelin Contracts](https://github.com/OpenZeppelin/openzeppelin-contracts/tree/v5.7.0) と Contracts Upgradeable の v5.7.0（どちらも MIT ライセンス）を使います。OpenZeppelin のソースはリポジトリに含めず、[run.sh](lab/run.sh) がタグとコミットを確かめて取得します。

以下は、更新で並びがずれる実装と、名前空間を使う実装の抜粋です。

```solidity
contract VaultV1 {
    address public owner;  // slot 0
    uint256 public balance; // slot 1
}

contract VaultV2Bad {
    uint256 public fee;     // slot 0 (was owner)
    address public owner;   // slot 1 (was balance)
    uint256 public balance; // slot 2 (empty)
}

contract NamespacedVault {
    /// @custom:storage-location erc7201:debimate.vault
    struct VaultStorage { address owner; uint256 balance; }
    bytes32 private constant VAULT_LOCATION =
        0xae0e5a2ac921da8c4f0db7a6df576631c5d91fc4de80e3189b369f9d39c30700;
}
```

slot の計算は、Python の標準ライブラリだけで書いた [slots.py](lab/slots.py) が行います。[`hashlib.sha3_256`](https://docs.python.org/3/library/hashlib.html) は Ethereum の Keccak-256 とパディングが異なるので、Keccak を手で実装しています。[run.py](lab/run.py) は、計算した slot を `cast storage` で読んだ値と照合します。以下は、run.py の検査の抜粋です。

```python
impl_slot = erc1967('eip1967.proxy.implementation')
assert storage(proxy, impl_slot) == word(v1.lower())
assert cast('implementation', '--rpc-url', URL, proxy).lower() == v1.lower()

loc = erc7201('debimate.vault')
tx(alice, p3, 'setUp(address,uint256)', alice, 100)
assert storage(p3, loc) == word(alice.lower())
assert int(storage(p3, hex(int(loc, 16) + 1)), 16) == 100

tx(mallory, impl, 'initialize(address)', mallory)   # 第三者が実装を初期化
assert storage(impl, own_slot) == word(mallory.lower())
```

<details>
<summary>run.py の全体（ノードの起動、6 つの検査、後始末）</summary>

```python
#!/usr/bin/env python3
"""Local-only upgradeable proxy experiment. Run through run.sh.

Starts its own loopback-only Anvil (Prague) and stops it on exit.
Accounts are Anvil's public test accounts only. No external RPC is used.
"""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
import urllib.request

from slots import erc1967, erc7201

HERE = Path(__file__).resolve().parent
OUT = HERE / 'output'
OUT.mkdir(exist_ok=True)
TOOLS = {n: os.environ.get(n.upper(), shutil.which(n)) for n in ('anvil', 'cast')}
if not all(TOOLS.values()):
    raise SystemExit('Put anvil and cast on PATH (or set ANVIL, CAST).')
BUILD = json.loads(Path(os.environ['BUILD']).read_text())['contracts']
lines = []


def log(s=''):
    print(s)
    lines.append(s)


def cast(*args, check=True):
    p = subprocess.run([TOOLS['cast'], *map(str, args)], text=True, capture_output=True)
    if check and p.returncode:
        raise RuntimeError(p.stderr)
    return p.stdout.strip() if not p.returncode else 'REVERT ' + p.stderr.strip().splitlines()[-1]


def artifact(name):
    return next(v for k, v in BUILD.items() if k.endswith(':' + name))


with socket.socket() as s:
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
URL = f'http://127.0.0.1:{port}'


def rpc(method, *params):
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
    req = urllib.request.Request(URL, body, {'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=10) as r:
        res = json.load(r)
    if 'error' in res:
        raise RuntimeError(res['error'])
    return res['result']


def send(sender, data, to=None, ok=True):
    tx = {'from': sender, 'data': data, 'gas': hex(3_000_000)}
    if to:
        tx['to'] = to
    h = rpc('eth_sendTransaction', tx)
    for _ in range(200):
        r = rpc('eth_getTransactionReceipt', h)
        if r:
            assert (int(r['status'], 16) == 1) == ok, r
            return r
        time.sleep(0.05)
    raise TimeoutError(h)


def deploy(sender, name, ctor_sig=None, *args):
    code = '0x' + artifact(name)['bin']
    if ctor_sig:
        code += cast('abi-encode', ctor_sig, *args)[2:]
    return send(sender, code)['contractAddress']


def tx(sender, to, sig, *args, ok=True):
    return send(sender, cast('calldata', sig, *args), to, ok)


ERRORS = ('UUPSUnauthorizedCallContext()', 'InvalidInitialization()')


def call(to, sig, *args):
    out = cast('call', '--rpc-url', URL, to, sig, *args, check=False)
    for e in ERRORS:
        if out.startswith('REVERT') and cast('sig', e) in out:
            return 'revert ' + e
    return out


def storage(addr, slot):
    return cast('storage', '--rpc-url', URL, addr, slot)


def word(v):
    return '0x' + v[2:].rjust(64, '0') if isinstance(v, str) else '0x' + f'{v:064x}'


anvil = subprocess.Popen([TOOLS['anvil'], '--host', '127.0.0.1', '--port', str(port),
                          '--hardfork', 'prague', '--silent'])
try:
    for _ in range(100):
        try:
            rpc('eth_chainId')
            break
        except OSError:
            time.sleep(0.1)
    admin, alice, mallory = rpc('eth_accounts')[:3]   # Anvil test accounts 0, 1, 2

    log('== 1. naive proxy: implementation address in slot 0 ==')
    counter = deploy(admin, 'CounterV1')
    naive = deploy(admin, 'NaiveProxy', 'f(address)', counter)
    before = storage(naive, 0)
    assert before == word(counter.lower())
    tx(alice, naive, 'increment()')
    after = storage(naive, 0)
    assert int(after, 16) == int(counter, 16) + 1
    log(f'slot 0 before increment(): {before}')
    log(f'slot 0 after  increment(): {after}')
    raw = rpc('eth_call', {'to': naive, 'data': cast('sig', 'count()')}, 'latest')
    log(f'count() through the proxy now returns: {raw!r} (delegates to an address without code)')
    assert raw == '0x'

    log()
    log('== 2. ERC-1967 slots: Python vs constants in the spec and OpenZeppelin ==')
    impl_slot, admin_slot = erc1967('eip1967.proxy.implementation'), erc1967('eip1967.proxy.admin')
    log(f'implementation  {impl_slot}')
    log(f'admin           {admin_slot}')
    assert impl_slot == '0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
    assert admin_slot == '0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'
    v1 = deploy(admin, 'VaultV1')
    proxy = deploy(admin, 'StudyProxy', 'f(address)', v1)
    assert storage(proxy, impl_slot) == word(v1.lower())
    assert storage(proxy, admin_slot) == word(admin.lower())
    assert cast('implementation', '--rpc-url', URL, proxy).lower() == v1.lower()
    assert cast('admin', '--rpc-url', URL, proxy).lower() == admin.lower()
    log('cast storage / cast implementation / cast admin agree with the computed slots')

    log()
    log('== 3. layout shift on upgrade ==')
    tx(alice, proxy, 'setUp(address,uint256)', alice, 100)
    s0, s1 = storage(proxy, 0), storage(proxy, 1)
    log(f'V1      owner()={call(proxy, "owner()(address)")} balance()={call(proxy, "balance()(uint256)")}')
    log(f'        slot 0={s0}')
    log(f'        slot 1={s1}')
    bad, good = deploy(admin, 'VaultV2Bad'), deploy(admin, 'VaultV2Good')
    r = tx(admin, proxy, 'upgradeTo(address)', bad)
    upgraded = cast('keccak', 'Upgraded(address)')
    assert r['logs'][0]['topics'] == [upgraded, word(bad.lower())]
    log(f'Upgraded(address) topic0={upgraded}')
    log(f'V2Bad   owner()={call(proxy, "owner()(address)")} balance()={call(proxy, "balance()(uint256)")}')
    log(f'        fee()={call(proxy, "fee()(uint256)")}')
    assert storage(proxy, 0) == s0 and storage(proxy, 1) == s1
    log('        slot 0 and slot 1 are unchanged; only the meaning of each slot changed')
    tx(alice, proxy, 'setFee(uint256)', 5)
    tx(admin, proxy, 'upgradeTo(address)', good)
    log(f'V2Good  owner()={call(proxy, "owner()(address)")} balance()={call(proxy, "balance()(uint256)")}'
        ' (after setFee(5) under V2Bad)')
    assert int(storage(proxy, 0), 16) == 5

    log()
    log('== 4. constructor writes to the implementation, not the proxy ==')
    box = deploy(admin, 'CtorBox')
    p2 = deploy(admin, 'StudyProxy', 'f(address)', box)
    log(f'implementation value()={call(box, "value()(uint256)")}  proxy value()={call(p2, "value()(uint256)")}')

    log()
    log('== 5. ERC-7201 namespace ==')
    loc = erc7201('debimate.vault')
    log(f'erc7201:debimate.vault  {loc}')
    ns = deploy(admin, 'NamespacedVault')
    p3 = deploy(admin, 'StudyProxy', 'f(address)', ns)
    tx(alice, p3, 'setUp(address,uint256)', alice, 100)
    assert storage(p3, loc) == word(alice.lower())
    assert int(storage(p3, hex(int(loc, 16) + 1)), 16) == 100
    assert int(storage(p3, 0), 16) == 0
    log(f'slot {loc[:10]}..00 = owner, ..01 = balance 100, slot 0 = 0')
    layout = {n: [(v['label'], int(v['slot'])) for v in artifact(n)['storage-layout']['storage']]
              for n in ('PlainAB', 'PlainBA', 'BoxOpen')}
    for n, v in layout.items():
        log(f'solc storage layout {n:<8} {v}')

    log()
    log('== 6. uninitialized implementation (OpenZeppelin v5.7.0) ==')
    own_slot = erc7201('openzeppelin.storage.Ownable')
    init_slot = erc7201('openzeppelin.storage.Initializable')
    impl = deploy(admin, 'BoxOpen')
    init = cast('calldata', 'initialize(address)', alice)
    oz_proxy = deploy(admin, 'ERC1967Proxy', 'f(address,bytes)', impl, init)
    assert storage(oz_proxy, own_slot) == word(alice.lower())
    log(f'proxy owner()={call(oz_proxy, "owner()(address)")} (alice); impl owner()={call(impl, "owner()(address)")}')
    tx(mallory, impl, 'initialize(address)', mallory)
    log(f'mallory calls impl.initialize(mallory): impl owner()={call(impl, "owner()(address)")}')
    assert storage(impl, own_slot) == word(mallory.lower())
    r = tx(mallory, impl, 'upgradeToAndCall(address,bytes)', impl, '0x', ok=False)
    reason = call(impl, 'upgradeToAndCall(address,bytes)', impl, '0x', '--from', mallory)
    log(f'mallory calls impl.upgradeToAndCall directly: status={int(r["status"], 16)} {reason}')
    log(f'proxy owner() is still {call(oz_proxy, "owner()(address)")}')
    locked = deploy(admin, 'BoxLocked')
    r = tx(mallory, locked, 'initialize(address)', mallory, ok=False)
    log(f'BoxLocked.initialize by mallory: status={int(r["status"], 16)} {call(locked, "initialize(address)", mallory, "--from", mallory)}')
    log(f'BoxLocked Initializable slot = {storage(locked, init_slot)}')
    assert int(storage(locked, init_slot), 16) == 2**64 - 1

    log()
    log('Assertions: PASS')
    (OUT / 'summary.txt').write_text('\n'.join(lines) + '\n')
    (OUT / 'versions.txt').write_text(
        subprocess.check_output([TOOLS['anvil'], '--version'], text=True).splitlines()[0] + '\n')
finally:
    anvil.terminate()
    anvil.wait()
```

</details>

anvil・cast・solc を PATH に置き、次のコマンドで実行します。必要なバージョンと実行条件は [README](lab/README.txt) にも記載しています。

```bash
bash content/notes/blockchain-systems/upgradeable-proxy/lab/run.sh
```

検査は 6 段あり、全て通りました（[出力](lab/output/summary.txt)の末尾が `Assertions: PASS`）。以下は、1 段目の出力です。

```text
== 1. naive proxy: implementation address in slot 0 ==
slot 0 before increment(): 0x0000000000000000000000005fbdb2315678afecb367f032d93f642f64180aa3
slot 0 after  increment(): 0x0000000000000000000000005fbdb2315678afecb367f032d93f642f64180aa4
count() through the proxy now returns: '0x' (delegates to an address without code)
```

<details>
<summary>6 段の出力の全体</summary>

```text
== 1. naive proxy: implementation address in slot 0 ==
slot 0 before increment(): 0x0000000000000000000000005fbdb2315678afecb367f032d93f642f64180aa3
slot 0 after  increment(): 0x0000000000000000000000005fbdb2315678afecb367f032d93f642f64180aa4
count() through the proxy now returns: '0x' (delegates to an address without code)

== 2. ERC-1967 slots: Python vs constants in the spec and OpenZeppelin ==
implementation  0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc
admin           0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103
cast storage / cast implementation / cast admin agree with the computed slots

== 3. layout shift on upgrade ==
V1      owner()=0x70997970C51812dc3A010C7d01b50e0d17dc79C8 balance()=100
        slot 0=0x00000000000000000000000070997970c51812dc3a010c7d01b50e0d17dc79c8
        slot 1=0x0000000000000000000000000000000000000000000000000000000000000064
Upgraded(address) topic0=0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b
V2Bad   owner()=0x0000000000000000000000000000000000000064 balance()=0
        fee()=642829559307850963015472508762062935916233390536 [6.428e47]
        slot 0 and slot 1 are unchanged; only the meaning of each slot changed
V2Good  owner()=0x0000000000000000000000000000000000000005 balance()=100 (after setFee(5) under V2Bad)

== 4. constructor writes to the implementation, not the proxy ==
implementation value()=42  proxy value()=0

== 5. ERC-7201 namespace ==
erc7201:debimate.vault  0xae0e5a2ac921da8c4f0db7a6df576631c5d91fc4de80e3189b369f9d39c30700
slot 0xae0e5a2a..00 = owner, ..01 = balance 100, slot 0 = 0
solc storage layout PlainAB  [('a', 0), ('b', 1)]
solc storage layout PlainBA  [('b', 0), ('a', 1)]
solc storage layout BoxOpen  []

== 6. uninitialized implementation (OpenZeppelin v5.7.0) ==
proxy owner()=0x70997970C51812dc3A010C7d01b50e0d17dc79C8 (alice); impl owner()=0x0000000000000000000000000000000000000000
mallory calls impl.initialize(mallory): impl owner()=0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC
mallory calls impl.upgradeToAndCall directly: status=0 revert UUPSUnauthorizedCallContext()
proxy owner() is still 0x70997970C51812dc3A010C7d01b50e0d17dc79C8
BoxLocked.initialize by mallory: status=0 revert InvalidInitialization()
BoxLocked Initializable slot = 0x000000000000000000000000000000000000000000000000ffffffffffffffff

Assertions: PASS
```

</details>

1 段目は、slot 0 に実装のアドレスを置いたプロキシです。`increment()` の後、アドレスの末尾が `aa3` から `aa4` に変わり、`count()` は空の返り値（`0x`）を返しました。コードの無いアドレスへの `DELEGATECALL` は失敗せず、何も返さずに成功します。そのため、エラーにならないまま壊れます。

2 段目では、Python で計算した 2 つの slot が仕様の値と一致し、プロキシの storage・`cast implementation`・`cast admin` の結果とも一致しました。3 段目は、前の節の表の元になった結果です。V2Bad に差し替えても slot 0 と slot 1 の値は変わらず、`Upgraded` のログの 2 番目の topic には新しい実装のアドレスが入っていました。

5 段目では、名前空間の起点 `0xae0e…0700` に `owner`、その次の slot に `balance` の 100 があり、slot 0 は 0 のままでした。solc が出力した storage の配置では、継承の順を入れ替えた `PlainAB` と `PlainBA` で `a` と `b` の slot が入れ替わり、OpenZeppelin の部品だけで作った `BoxOpen` は空でした。

6 段目は、OpenZeppelin v5.7.0 で初期化を塞がなかった実装です。テスト用アカウント 2（mallory）が実装の `initialize` を直接呼ぶと、実装の所有者になりました。

一方で、実装を直接 `upgradeToAndCall` で呼ぶと `onlyProxy` の検査で拒否され、プロキシの所有者も alice のままでした。constructor で `_disableInitializers()` を呼んだ実装は `initialize` を拒否し、初期化の状態を表す slot には `uint64` の最大値が入っていました。

---

### 利点

- 利用者や他のコントラクトが登録したアドレスを変えずに、不具合を直せる
- 残高などのデータを移し替えずに、処理だけを更新できる
- ERC-1967 の slot を読めば、ツールや利用者が今の実装と管理者を確かめられる
- ERC-7201 で、継承の順や親の変数の追加に左右されない配置にできる

### 欠点

プロキシは、コードを変えられない環境で、差し替えの権限を誰かに持たせることで更新を可能にします。その代わりに、次の制約があります。

- 管理者の鍵や承認の仕組みが破られると、資産を扱うコードごと差し替えられる
- storage の並びを壊す更新でも、コンパイラは誤りを報告しない
- 実装の初期化を忘れると、第三者が実装の所有者になれる
- 呼び出しごとに `DELEGATECALL` が 1 段増え、その分の gas が掛かる
- 利用者は、今のコードだけでなく、将来差し替えられる範囲まで信頼する必要がある

### 適さないケース

- 誰にも変更できないことを利用者に約束したいコントラクト（差し替えの権限を後で放棄する設計を除く）
- 一度だけ使う小さなコントラクトや、アドレスの移行で困る利用者がいない場合
- 管理者の鍵を複数人の承認や待ち時間で守る運用を用意できない場合
