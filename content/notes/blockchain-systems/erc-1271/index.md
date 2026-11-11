---
title: "ERC-1271 - 秘密鍵を持たないアカウントの署名"
date: 2026-11-11
draft: false
series: ["技術ノート", "Blockchain Systems"]
tags: ["blockchain", "ethereum", "erc-1271", "smart-contract", "account-abstraction", "security"]
weight: 20
wrapTables: true
topics: ["Smart Contract"]
---

[Ethereum](https://ethereum.org/) のアカウントには、[2 つの種類](../ethereum-account-model/)があります。秘密鍵を持つ人が操作する EOA（Externally Owned Account）と、デプロイしたコードで動くコントラクトのアカウント（contract account）です。複数人の承認で動く[マルチシグ](../multisig/)や、署名の方法をコードで決める[スマートアカウント](../erc-4337/)は、後者のコントラクトのアカウントで、秘密鍵を持ちません。

スマートアカウントでは、所有者が持つ EOA の鍵で署名し、アカウントのコードがその署名を確かめる構成がよく使われます。

EOA の利用者がサイトにログインする時、サイトは利用者に署名させ、サーバーやコントラクトで、署名から復元したアドレスが利用者のアドレスと一致するかを比べます。ところが、マルチシグの利用者は同じ方法では本人だと示せません。どんな署名からも、マルチシグのアドレスは復元されないからです。

ERC-1271 は、このようなアカウントに「この署名は自分のものとして有効か」を問い合わせるための関数 `isValidSignature` を定めた規格です。ERC（Ethereum Request for Comments）は、Ethereum のアプリが共通で使う規格の提案です。以下は、署名を検証する側の判定の流れです。

{{< figure src="images/erc-1271_branch.webp" alt="左の枠で、署名者のアドレスにコードがあるかを問う。無いなら上の EOA の枠で、ecrecover(digest, sig) が署名者のアドレスと等しいかを比べる。あるなら下のコントラクト・委任した EOA（ERC-1271）の枠で、署名者の isValidSignature(digest, sig) が 0x1626ba7e を返すかを比べる" caption="署名を検証する側の、コードの有無による分岐" align="center" >}}

上記の図の上の黄土色の枠が EOA の検証で、署名から復元したアドレスを比べます。下の青い枠がコードを持つアカウント（コントラクトのアカウント（contract account）と、後で説明する委任した EOA）の検証で、アカウント自身に問い合わせます。

サーバーで検証する場合も、`eth_call`（取引を送らずにコントラクトの関数を呼ぶ JSON-RPC のメソッド）でアカウントの `isValidSignature` を呼びます。図の中の `0x1626ba7e` は、後の節で説明します。

<br>

本記事では、[Digital Signature](../digital-signature/) の署名と検証、[EIP-712](../eip-712/) の型付きの署名と permit を前提に、次の疑問を順に説明します。

- なぜ署名からコントラクトのアカウントのアドレスは復元されないのか。
- `isValidSignature` は何を返し、何を有効とするかを誰が決めるのか。
- 検証する側が EOA の方法だけで書くと、何が起きるのか。
- まだデプロイされていないアカウントは、どうやって署名を示すのか。

途中では、ローカルのチェーンに学習用のアカウントを置き、2 通りの検証の結果を比べます。

---

### 復元されないアドレス

EOA の署名は、ecrecover という組み込みの関数で検証します。ecrecover は、署名したハッシュ（digest）と署名から公開鍵を求め、そのアドレスを返します。EOA のアドレスは[公開鍵から導かれる](../ethereum-address/)ので、正しい署名なら署名者のアドレスが返ります。

コントラクトのアカウントのアドレスは、デプロイした側のアドレスとその取引数（アカウントの nonce）などから決まり、公開鍵から導かれたものではありません。そのため、どんな署名を ecrecover しても、コントラクトのアカウントのアドレスは返りません。

{{< figure src="images/erc-1271_address.webp" alt="上の黄土色の枠は EOA で、秘密鍵 → 公開鍵 → アドレスと決まり、ecrecover(digest, 署名) も公開鍵を経て同じアドレスになるので一致する。下の青い枠はコントラクトのアカウントで、デプロイした側のアドレスと nonce などからアドレスが決まり、ecrecover(digest, 署名) は所有者の EOA のアドレスを返すので、赤い ≠ で一致しない" caption="アドレスの決まり方と、ecrecover が返すアドレス" align="center" >}}

上記の図の下の枠のように、スマートアカウントの中で実際に署名するのが所有者の EOA だったとしても、ecrecover が返すのは所有者の EOA のアドレスで、アカウントのアドレスではありません。

---

### isValidSignature の約束

[ERC-1271](https://eips.ethereum.org/EIPS/eip-1271) は、検証する側がアカウントに問い合わせる形でこれを解きます。アカウントは次の関数を実装し、署名が有効なら `0x1626ba7e` を返します。

この値は、関数自身の識別子（`isValidSignature(bytes32,bytes)` の keccak256 の先頭 4 バイト。コントラクトはこの 4 バイトで呼ばれた関数を見分ける）です。bool ではなく決まった値を返すのは、検証をより厳しく単純にするためだと、仕様の Rationale は説明しています。

```solidity
function isValidSignature(bytes32 hash, bytes memory signature) external view returns (bytes4 magicValue);
```

何を有効とするかは、アカウントのコードが決めます。所有者 1 人の ECDSA 署名（EOA の署名方式）でも、3 人中 2 人の署名でも、別の署名方式でも構いません。

関数は `view` で状態を変えられませんが、判定はアカウントの状態によって変わります。例えば、所有者を入れ替えれば、同じ署名が後から無効になります。EOA の署名は鍵が同じならいつ検証しても同じ結果ですが、ERC-1271 の署名は検証した時点の結果です。

---

### 検証する側の分岐

検証するコントラクトは、署名者のアドレスにコードがあれば `isValidSignature` を呼び、無ければ ecrecover を使います。冒頭の図の分岐です。[OpenZeppelin Contracts v5.1.0](https://github.com/OpenZeppelin/openzeppelin-contracts/tree/v5.1.0)（MIT ライセンス）の [SignatureChecker](https://github.com/OpenZeppelin/openzeppelin-contracts/blob/v5.1.0/contracts/utils/cryptography/SignatureChecker.sol) は、次のように書いています。

```solidity
function isValidSignatureNow(address signer, bytes32 hash, bytes memory signature) internal view returns (bool) {
    if (signer.code.length == 0) {
        (address recovered, ECDSA.RecoverError err, ) = ECDSA.tryRecover(hash, signature);
        return err == ECDSA.RecoverError.NoError && recovered == signer;
    } else {
        return isValidERC1271SignatureNow(signer, hash, signature);
    }
}
```

`isValidERC1271SignatureNow` は、署名者の `isValidSignature` を呼び、戻り値が `0x1626ba7e` かを比べる関数です。[EIP-712 のノート](../eip-712/)で取り上げた Uniswap の Permit2 も、[SignatureVerification](https://github.com/Uniswap/permit2/blob/cc56ad0f3439c502c246fc5cfcc3db92bb8b7219/src/libraries/SignatureVerification.sol) で同じ分岐をしています。

<br>

なお、2025 年からは EOA にも委任先のコードを付けられます（[EIP-7702](https://eips.ethereum.org/EIPS/eip-7702)。詳しくは [Ethereum のアカウントモデル](../ethereum-account-model/)のノート）。委任を設定した EOA はコードを持つので、この分岐では `isValidSignature` を呼ぶ方に進みます。委任先のコントラクトが `isValidSignature` を実装していなければ、EOA の鍵で正しく署名していても、この検証は失敗します。

---

### ローカルでの検証

EIP-712 のノートと同じ実験（[lab/run.py](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/eip-712/lab/run.py) の 5）で、所有者の EOA の署名なら有効とする学習用のアカウント `StudyAccount` を作りました。

以下では、アカウントの `owner`（所有者の EOA）と、Permit のメッセージの `owner` 欄（承認する側のアドレス）は、「所有者の EOA」と「Permit の owner 欄」と呼び分けます。手元だけで動くノード [Anvil](https://getfoundry.sh/anvil/overview) と、Anvil が既定で作るテスト用のアカウントだけを使います。自作のコントラクトは学習用で、監査していません。

```solidity
contract StudyAccount is IERC1271 {
    address public immutable owner;

    constructor(address owner_) {
        owner = owner_;
    }

    function isValidSignature(bytes32 hash, bytes calldata signature) external view returns (bytes4) {
        (address recovered, ECDSA.RecoverError err, ) = ECDSA.tryRecover(hash, signature);
        if (err == ECDSA.RecoverError.NoError && recovered == owner) {
            return IERC1271.isValidSignature.selector; // 0x1626ba7e
        }
        return 0xffffffff;
    }
}
```

<br>

署名するのは、Permit の owner 欄をこのアカウントにした ERC-2612 の Permit（トークンの利用を署名で承認するメッセージ）で、署名するのは所有者の EOA です。検証には、ecrecover だけで比べる `checkEcrecover` と、上記の SignatureChecker を呼ぶ `checkWith1271` を持つ学習用のコントラクト [SigCheck](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/eip-712/lab/SigCheck.sol) を用います。

以下は run.py の該当部分です。`a.deploy` はコントラクトのデプロイ、`a.call` は [`eth_call`](https://ethereum.org/developers/docs/apis/json-rpc/)（取引を送らずに関数を呼ぶ）で結果か失敗の理由を返す関数、`permit_typed` は Permit の型とドメインを組み立てる関数、`digest` は EIP-712 のハッシュを Python で計算する関数です。

`token` は学習用のトークン、`spender` は承認を受ける側のアカウント、`checker` は SigCheck、`psig` は permit の関数の型で、どれも EIP-712 のノートの実験と同じです。

```python
acct = a.deploy(deployer, 'StudyAccount', acct_owner)
acct_2 = a.deploy(deployer, 'StudyAccount', acct_owner)      # another account, same owner
typed_c = permit_typed(31337, token, acct)                    # Permit with owner = acct
d_c = '0x' + digest(typed_c).hex()
sig_c = a.rpc('eth_signTypedData_v4', acct_owner, typed_c)  # the account's owner EOA signs
bad = sig_c[:-4] + ('1b' if sig_c[-2:] == '1c' else '1c')    # flip v -> another signer
log('ecrecover(digest, sig)', a.call(checker, 'recover(bytes32,bytes)', d_c, sig_c, returns='address'))
log('checkEcrecover(account, ...)', a.call(checker, 'checkEcrecover(address,bytes32,bytes)',
                                           acct, d_c, sig_c, returns='bool'))
log('checkWith1271(account, ...)', a.call(checker, 'checkWith1271(address,bytes32,bytes)',
                                          acct, d_c, sig_c, returns='bool'))
log('account.isValidSignature(digest, sig)',
    a.call(acct, 'isValidSignature(bytes32,bytes)', d_c, sig_c, returns='bytes4'))
log('account.isValidSignature(digest, bad sig)',
    a.call(acct, 'isValidSignature(bytes32,bytes)', d_c, bad, returns='bytes4'))
vc, rc_, sc = int(sig_c[130:132], 16), '0x' + sig_c[2:66], '0x' + sig_c[66:130]
log('token.permit(owner=account, ...)', a.call(token, psig, acct, spender, 100, deadline, vc, rc_, sc))
log('another account of the same owner .isValidSignature',
    a.call(acct_2, 'isValidSignature(bytes32,bytes)', d_c, sig_c, returns='bytes4'))
```

以下は[出力](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/eip-712/lab/output/summary.txt)の 5 です。

```text
# 5. contract account (ERC-1271)
account | 0xCf7Ed3AccA5a467e9e704C703E8D87F634fB0Fc9 | code bytes | 1367
account owner EOA | 0x90F79bf6EB2c4f870365E785982E1f101E93b906
ecrecover(digest, sig) | 0x90F79bf6EB2c4f870365E785982E1f101E93b906
checkEcrecover(account, ...) | false
checkWith1271(account, ...) | true
account.isValidSignature(digest, sig) | 0x1626ba7e
account.isValidSignature(digest, bad sig) | 0xffffffff
token.permit(owner=account, ...) | revert ERC2612InvalidSigner(recovered=0x90F79bf6EB2c4f870365E785982E1f101E93b906, owner=0xCf7Ed3AccA5a467e9e704C703E8D87F634fB0Fc9)
another account of the same owner .isValidSignature | 0x1626ba7e
```

出力の `code bytes` は、アカウントのアドレスにコードが 1367 バイトあることを表し、冒頭の図の下の枠に進む根拠になります。ecrecover で復元されるのは所有者の EOA（`0x90F7…`）で、アカウントのアドレス（`0xCf7E…`）ではありません。そのため、ecrecover だけで比べる `checkEcrecover` は false、コードの有無で分岐する `checkWith1271` は true を返しました。

アカウントの `isValidSignature` は、正しい署名に `0x1626ba7e`、v（署名の末尾の 1 バイト）を変えた署名に `0xffffffff` を返しています。v は、署名から求まる公開鍵の候補のどちらを使うかを選ぶ値なので、変えると別のアドレスが復元されます。

<br>

OpenZeppelin v5.1.0 の `ERC20Permit` も ecrecover だけで比べるので、Permit の owner 欄をアカウントにした permit は失敗（revert）しました。[ERC-2612](https://eips.ethereum.org/EIPS/eip-2612) の仕様が、permit の署名を owner の [secp256k1](https://www.secg.org/sec2-v2.pdf)（EOA の鍵の曲線）の署名と定めているからです。コントラクトのアカウントで署名による承認を使うなら、Permit2 のように ERC-1271 を扱う仕組みが必要です。

同じことは、署名を受け取る他のサービスにも言えます。「署名の検証は ecrecover で済む」と書いたアプリは EOA の署名だけを受け付け、ログインや注文の署名でスマートアカウントの利用者を締め出すことになります。

---

### 別のアカウントでの使い回し

出力の最後の行は、同じ所有者の別の `StudyAccount` も、同じ署名を有効と返した結果です。`StudyAccount` は「所有者の EOA が署名したか」だけを判定し、渡されたハッシュがどのアカウント向けかを見ません。実験のハッシュは Permit のものでしたが、どんなハッシュでも同じです。

この性質が問題になるのは、署名するメッセージにアカウントのアドレスが入っていない時です。例えばログインの文言なら、次の図のようになります。

{{< figure src="images/erc-1271_reuse.webp" alt="左の所有者の EOA が、アカウントのアドレスを含まないログインの文言に 1 回署名する。右の 2 つのアカウントのうち、StudyAccount A（ログインしようとしたアカウント）は isValidSignature で 0x1626ba7e を返し、A としてログインする。赤い StudyAccount B（所有者が同じ別のアカウント）も 0x1626ba7e を返し、B としてもログインできてしまう。下に、isValidSignature は所有者だけを見て、どのアカウント向けかは見ないと書かれている" caption="A のログインのための署名を B も有効と返す" align="center" >}}

上記の図で、A のログインのために署名を受け取ったサイトや、途中で署名を見た第三者は、それを B の署名として示し、B としてログインできます。文言にサイト名が入っていても、アカウントのアドレスが無ければ、同じサイトでの B のログインは防げません。EIP-712 のドメインを使っていても、verifyingContract は検証するアプリのアドレスなので、どのアカウント向けかは区別できません。

<br>

permit では、Permit の owner 欄に A のアドレスが入るので、B の名前で使われることはありません。一方、Permit2 は次の 3 段で使い回しが通ります。

1. Permit2 の型（`PermitSingle` など）は owner を含まず、owner は関数の引数で渡す。
2. そのため、署名するハッシュはどのアカウント向けかに依存しない。
3. 同じ所有者の B の `isValidSignature` も、そのハッシュを所有者の署名として有効と返す。

ただし、Permit2 は nonce を owner・token・spender の組ごとに記録しているので、通るのは B について記録された nonce が署名の nonce と一致する間（例えば B がまだ Permit2 を使っていない時）に限られます。

これを防ぐには、アカウントが判定の前に、自分のアドレスなどを混ぜてハッシュを計算し直します。例えば `keccak256(アカウントのアドレス ‖ hash)` のような形にすれば、次の図のように、A 向けの署名は B では通りません（式は考え方の例で、ERC-7739 の正確な形ではありません）。

{{< figure src="images/erc-1271_rehash.webp" alt="左の所有者の EOA が A 向けに署名する。右の上のアカウント A（アドレスを混ぜる版）は keccak256(A のアドレス ‖ hash) を計算し、署名したハッシュと一致する。下の灰色のアカウント B（アドレスを混ぜる版）は keccak256(B のアドレス ‖ hash) を計算し、別のハッシュになって無効。下に、式は考え方の例で ERC-7739 の正確な形ではないと書かれている" caption="アカウントのアドレスを混ぜたハッシュの計算し直し（考え方の例）" align="center" >}}

上記の図の通り、ハッシュがアカウントごとに変わるので、使い回しは通らなくなります。ただし、計算し直したハッシュは、ウォレットが画面に表示した型付きのデータとずれてしまいます。ウォレットの画面で読める形を保ったまま、その方法を定めようとしているのが [ERC-7739](https://eips.ethereum.org/EIPS/eip-7739) です（2026 年 11 月時点で Draft）。

---

### まだデプロイされていないアカウント

スマートアカウントは、アドレスを先に計算しておき、最初の取引の時にデプロイすることがあります。送り主の nonce によらず、作る前にアドレスが決まるデプロイの方法（[CREATE2](https://eips.ethereum.org/EIPS/eip-1014)）があり、ウォレットはそのアドレスを先に利用者に見せられるからです（仕組みは [ERC-4337 のノート](../erc-4337/)で説明しています）。

しかし、コードの無いアドレスに `isValidSignature` は呼べず、デプロイ前のアカウントはログインの署名を示せません。

[ERC-6492](https://eips.ethereum.org/EIPS/eip-6492)（2026 年 11 月時点で Final）は、この場合の署名の形を定めています。アカウントを作るコントラクト（ファクトリ）のアドレス、その呼び出しデータ、元の署名の 3 つを Solidity の [ABI 形式](https://docs.soliditylang.org/en/v0.8.28/abi-spec.html)（`abi.encode`）でまとめ、その後ろに 32 バイトの `0x6492…6492` を付けます。

{{< figure src="images/erc-1271_6492.webp" alt="上段は ERC-6492 の署名の並びで、青い abi.encode(factory, factoryCalldata, 元の署名) の後ろに、黄土色の末尾 32 バイト 0x6492…6492 が続く。下段は検証する側が 1 回の eth_call の中で行う 3 段階で、1. 末尾を見て 6492 の形と判断、2. ファクトリを呼びデプロイを模擬、3. isValidSignature を元の署名で呼ぶ。eth_call は取引を送らないので、チェーンの状態は変わらない" caption="ERC-6492 の署名の並びと、検証する側の手順" align="center" >}}

上記の図の下段のように、検証する側はこの末尾を見つけたら、1 回の `eth_call` の中で、仕様にある検証用のコントラクト（`ValidateSigOffchain`）は、デプロイせずに生成用のコードごと実行します。このコントラクトは生成の処理の中でファクトリを呼んでデプロイを模擬し、続けて `isValidSignature` を呼びます。`eth_call` は取引を送らないので、チェーンの状態は変わりません。

仕様には、コントラクトの中で検証する方法も載っています。ただ、仕様自身も、コントラクトの中で検証する時はアカウントがデプロイ済みであることが多いので、主な用途はオフチェーンの検証だろうと書いています。

---

### 利点

- ECDSA の鍵を持たないアカウントも、同じ「署名を検証する」呼び出しで扱える。
- 何を有効とするか（複数人の承認、別の署名方式）をアカウントのコードで決められる。
- 所有者の入れ替えなどで、過去の署名を後から無効にできる。

---

### 欠点

- 検証する側が ecrecover だけで書くと、コントラクトのアカウントを受け付けない。ERC-2612 の permit もその 1 つ。
- 判定はアカウントの状態で後から変わるので、ある時点で通った署名が後で通るとは限らない。
- アカウントが自分のアドレスを判定に含めないと、同じ所有者の別のアカウントで署名を使い回される。
- デプロイ前のアカウントには、ERC-6492 のような別の形が要る。
