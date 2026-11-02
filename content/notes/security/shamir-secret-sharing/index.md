---
title: "Shamir's Secret Sharing - 閾値以上の Share が揃った時だけ Secret を復元する"
date: 2026-08-22
draft: false
series: ["技術ノート", "Security"]
tags: ["security", "cryptography"]
weight: 4
---

Shamir's Secret Sharing（SSS）は、1 つの Secret を n 個の Share に分け、そのうち異なる任意の k 個以上で復元できる秘密分散方式です。復元に必要な個数 k を閾値（threshold）と呼び、`(k, n)` threshold scheme と表します。

例えば、サービスの署名鍵を 1 台に置けば、その端末の故障で鍵を失います。鍵を 5 人全員にコピーすると、1 人分のコピーが漏洩しただけで鍵全体が知られます。`(3, 5)` の SSS なら、Share を 2 個失っても復元でき、2 個まで漏れても Secret の候補は絞れません。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
flowchart LR
    S["Secret"] --> T["(k, n) threshold scheme"]
    T --> A["Share 1"]
    T --> B["Share 2"]
    T --> C["…"]
    T --> D["Share n"]
    A --> J{"集まった Share"}
    B --> J
    C --> J
    D --> J
    J -->|"k 個以上"| R["Secret を復元"]
    J -->|"k-1 個以下"| U["Secret を特定できない"]
    classDef default fill:#eaf1f5,stroke:#9cabb5,color:#28343b;
```

この分岐は Share を持つ人の身元を判定しません。閾値以上の数の Share を集められる主体なら、正規の管理者でも攻撃者でも Secret を復元できます。

本記事では、Secret を Share に分けて復元する手順と、SSS が守らない範囲を説明します。扱う疑問は次の通りです。

- 鍵を 1 か所に置く方法や、全員にコピーする方法では、なぜ足りないのか。
- Share はどのように作り、k 個の点からどう復元するのか。
- x 座標の 0 を整数のまま判定すると、なぜ見逃すのか。
- Share の紛失や漏洩に対して、SSS は何を守らないのか。
- 単純な分割や暗号化と、何が違うのか。

---

### Secret を分散する理由

鍵の保管では、失わないことと漏らさないことを両立させる必要があります。1 か所だけに保管すると紛失に弱く、同じ鍵のコピーを増やすと漏洩の入口も増えます。ファイルを順番に切る方法では、1 個の断片から元データの一部がそのまま読めます。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
flowchart TB
    subgraph O["1 か所だけ"]
        O1["Secret"] --> O2["故障すると復元不能"]
    end
    subgraph C["同じものを複製"]
        C1["Secret のコピー"] --> C2["1 個の漏洩で全体が漏れる"]
    end
    subgraph F["単純に分割"]
        F1["元データを切る"] --> F2["断片から一部が読める"]
    end
    classDef default fill:#eaf1f5,stroke:#9cabb5,color:#28343b;
```

SSS は、n-k 個までの紛失と k-1 個までの漏洩に、別々に耐えられます。

---

### 3 個の Share と 2 次式

`(3, 5)` の k = 3 は、直感的には 2 次式に対応します。Secret を多項式の `x = 0` の値 `q(0)` に置き、0 ではない、異なる 5 個の x 座標で求めた点を Share として配ります。

x 座標が異なる 3 点があれば、それらを通る次数 2 以下の式は 1 本に定まるため、`q(0)` を求められます。2 点しかない場合は、その 2 点を通り、`q(0)` が異なる 2 次式を複数作れます。

次の図は、多項式補間の性質を理解するために実数上で描いた模式図です。実際の SSS の計算は有限体（finite field。有限個の値で計算する体系）上で行います。

![左は 2 個の Share (1, 2) と (2, 4) を通る 2 次曲線を 3 本重ねた図で、3 本の q(0) は -1、1、3 とばらばらになる。右は 3 個目の Share (3, 7) を足した図で、3 点を通る 2 次曲線は 1 本だけになり、q(0) = 1 が Secret として定まる](images/sss_polynomial_intuition.svg)

左の 3 本はどれも同じ 2 個の Share を通るので、Share を持つ側には、どれが元の式なのかを決める手掛かりがありません。

---

### Share の作り方

SSS では、dealer（Share の生成役）が次数 k-1 以下の多項式を作ります。`k = 3` なら `q(x) = a_0 + a_1x + a_2x^2` という 2 次式です。定数項 `a_0` に Secret を入れ、ほかの係数は互いに独立な一様乱数として選びます。

Share は多項式の断片ではなく、異なる x 座標で計算した点 `(x, q(x))` です。SSS の計算は有限体で行うので（理由は後述）、以下は 13 を法として（13 で割った余りで）計算します。Secret を 4、残りの係数を 2 と 3 にすると、`q(x) = 4 + 2x + 3x^2 mod 13` です。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
flowchart LR
    S["Secret 4"] --> A["a0 = 4"]
    R["一様な乱数"] --> B["a1 = 2<br/>a2 = 3"]
    A --> Q["q(x) = 4 + 2x + 3x^2 mod 13"]
    B --> Q
    Q --> P1["(1, 9)"]
    Q --> P2["(2, 7)"]
    Q --> P3["(3, 11)"]
    Q --> P4["(4, 8)"]
    Q --> P5["(5, 11)"]
    classDef default fill:#eaf1f5,stroke:#9cabb5,color:#28343b;
```

| Share | 計算 |
| --- | --- |
| `(1, 9)` | `4 + 2 + 3 = 9` |
| `(2, 7)` | `4 + 4 + 12 = 20 mod 13` |
| `(3, 11)` | `4 + 6 + 27 = 37 mod 13` |
| `(4, 8)` | `4 + 8 + 48 = 60 mod 13` |
| `(5, 11)` | `4 + 10 + 75 = 89 mod 13` |

同じ Secret をもう一度分けても、乱数で選ぶ係数が変われば Share も変わります。dealer が多項式を保存し続ける構成では、dealer だけで元の Share を再生成できます。再生成が不要なら、多項式と Secret を復元できないように消します。

---

### k 個の点からの復元

x 座標が異なる k 個の点があると、次数 k-1 以下で全ての点を通る多項式は 1 本に定まります。

ラグランジュ補間（Lagrange interpolation）は、集めた各点について「自分の x 座標では 1、ほかの x 座標では 0」になる基底多項式を作り、Share の y 値を掛けて足します。Secret だけが目的なら多項式の全係数を求めず、`x = 0` の値 `q(0)` を直接計算できます。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
sequenceDiagram
    participant H as Share 保持者
    participant R as 復元処理
    H->>R: (1, 9)
    H->>R: (2, 7)
    H->>R: (3, 11)
    R->>R: 各点の重みを x = 0 で計算
    R->>R: 3×9 + 10×7 + 1×11 mod 13
    R-->>H: q(0) = 4
```

この例の重み 3、10、1 は、13 を法として計算した値です。この計算では、割り算を逆元（掛けると 1 になる数）の掛け算に置き換えます。例えば `(2, 7)` の重みは `(0-1)(0-3) / ((2-1)(2-3)) = 3 / (-1)` です。-1 は 12 と同じで、`12 × 12 = 144` は 13 で割ると 1 余るので 12 の逆元は 12 です。`3 × 12 = 36` の余りの 10 が重みになります。別の組み合わせの 3 個を選ぶと重みは変わりますが、全て同じ多項式上の点なので `q(0)` は 4 に戻ります。

k-1 個では、Secret の候補ごとに条件を満たす多項式を 1 本ずつ作れます。以下は、この例の Share を 13 を法とする有限体（GF(13)）で数え上げた結果です。

![左は Share (1, 9) と (2, 7) の 2 個だけを持つ場合で、0 から 12 までの 13 個の Secret 候補それぞれに、条件を満たす 2 次式が 1 本ずつ残る棒グラフ。右は Share (3, 11) を足した場合で、候補 4 だけに 1 本残り、他の 12 個は 0 本になる](images/sss_candidates_mod13.svg)

乱数係数を独立かつ一様に選ぶので、k-1 個の Share と整合する多項式は、Secret の候補ごとに同じ本数あります。そのため、k-1 個以下の Share を観測しても、Secret の事前分布（Share を見る前の候補ごとの確率）は変わりません。[Shamir 氏の 1979 年の論文](https://people.cs.pitt.edu/~litman/courses/cs2001/lectures/lecture-02-p612-shamir.pdf)は、候補が事前に等確率なら Share を得た後も確率が変わらないことを `(k, n)` threshold scheme の条件にしています。この安全性は総当たりの計算量に頼るものではなく、Share から情報が得られないことによるものです。

---

### 有限体による偏りの除去

整数は無限にあるので、全ての整数から等確率で係数を選ぶことはできず、何らかの範囲から選ぶことになります。例えば係数を正の数から選ぶと、Share の y 座標から Secret の範囲を推測できます。`q(1) = a_0 + a_1 + a_2` なら、正の係数を足した結果から `a_0` の上限が分かるからです。

有限体では、足し算・引き算・掛け算・0 以外での割り算が、有限個の要素の中で閉じます。値は 13 に達すると 0 に戻るので、整数のような上限の手掛かりが生まれません。

| | 整数上で計算 | 有限体上で計算 |
| --- | --- | --- |
| 値の範囲 | 増え続ける | 有限個に収まる |
| 割り算 | 割り切れない場合がある | 0 以外は逆元で計算できる |
| k-1 個を見た結果 | 係数の選び方によって偏る | 候補ごとの確率が変わらない |

一般には、Secret を有限体の要素として表現・符号化します。素数 p を法とするこの例では、Secret を表現でき、かつ Share の x 座標として異なる非ゼロ要素を n 個取れるほど十分に大きな p を選びます。乱数係数は有限体から一様に選びます。

x 座標が 0 でないことも、有限体の中で確かめます。セキュリティ監査の会社 Trail of Bits が 2021 年 12 月に[公表した脆弱性](https://blog.trailofbits.com/2021/12/21/disclosing-shamirs-secret-sharing-vulnerabilities-and-announcing-zkdocs/)では、暗号資産取引所 Binance の tss-lib などが、参加者が自分で選べる ID を x 座標に使い、0 かどうかを整数のまま判定していました。13 を法とする例なら、x = 13 は判定を通りますが計算の中では 0 と同じなので、その参加者に届く y 座標は `q(0)`、つまり他の参加者の Secret です。

影響を受けたのは、1 人の dealer が分ける構成ではなく、各参加者が自分の多項式で dealer を務め合う閾値署名の鍵の生成です。悪意のある参加者が、他の参加者の秘密鍵を盗めました。

---

### 紛失・漏洩と SSS が守らない範囲

SSS が保証する範囲は、正しく生成された異なる Share の個数で表せます。

| 状況 | 結果 |
| --- | --- |
| n-k 個まで紛失 | 残った k 個で復元できる |
| k 個未満しか残らない | 正規の保持者も復元できない |
| k-1 個まで漏洩 | Secret の候補を絞れない |
| k 個以上漏洩 | 攻撃者も Secret を復元できる |

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
flowchart LR
    subgraph I["SSS が定める範囲"]
        I1["Share の生成"]
        I2["個数による復元条件"]
    end
    subgraph O["別に設計する範囲"]
        O1["誰に渡すか"]
        O2["保持者の Authentication"]
        O3["保存場所の保護"]
        O4["復元後の Secret の消去"]
    end
    I -.- O
    classDef default fill:#eaf1f5,stroke:#9cabb5,color:#28343b;
```

Share 保持者が誰なのかを確かめる処理は [Authentication](../authentication/) です。Share の配布先は Authorization（認可）や配布ポリシーで決め、配送経路と保存場所は別に保護します。

SSS には Share の改竄検出も含まれません。書き換えられた Share が混ざると別の値が Secret として復元され、復元処理だけではそれが誤りだと分かりません。値を置き換えられる経路があるなら、各 Share が正しいかを確かめられる検証可能秘密分散などを別に検討します。復元時には Secret が 1 か所のメモリに現れ、その端末も攻撃対象になります。

---

### 単純分割・暗号化との違い

単純分割は元データの区間を各ファイルに保存します。暗号化は鍵を持つ相手に復号を許し、SSS は threshold 以上の Share を集められる人たちに復元を許します。暗号化だけでは、復号鍵をどこに置くかという問題が残ります。

大きなファイルを SSS で直接分けると、元データと同じくらいの大きさの Share を n 個保管することになります。そのためファイルを共通鍵で暗号化し、小さな共通鍵だけを SSS で分ける構成があります。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
flowchart LR
    F["ファイル"] --> E["共通鍵で暗号化"]
    K["共通鍵"] --> E
    E --> C["暗号文"]
    K --> S["SSS で鍵を分散"]
    S --> H["Share 1 … Share n"]
    classDef default fill:#eaf1f5,stroke:#9cabb5,color:#28343b;
```

この構成では、ファイルの秘匿を暗号方式が担い、共通鍵の復元条件を SSS が担います。「[【TypeScript】ファイルを分割し、任意の分割ファイル数で復元できる nao1215/horcrux を作った話【分霊箱】](/post/ja/2025-10-05-typescript%E3%83%95%E3%82%A1%E3%82%A4%E3%83%AB%E3%82%92%E5%88%86%E5%89%B2%E3%81%97%E4%BB%BB%E6%84%8F%E3%81%AE%E5%88%86%E5%89%B2%E3%83%95%E3%82%A1%E3%82%A4%E3%83%AB%E6%95%B0/)」は、この組み合わせを実装した例です。

---

### 利点

- n-k 個を失っても、残りの Share から復元できる
- k-1 個以下の Share は、Secret の候補を絞る情報を与えない
- k と n を変えることで、漏洩への耐性と回収のしやすさを調整できる

---

### 欠点

- dealer を使う構成では、生成時に dealer が正しく動作することを前提とする
- Share の真正性を別の手段で保証しなければ、攻撃者が改竄した値を復元処理へ紛れ込ませられる
- 復元時には Secret が 1 か所に集まり、その場所が攻撃対象になる
- n 個の Share を保管するため、Secret を直接分けると総量が増える

---

### 適さないケース

- 頻繁に使う鍵について、使用のたびに k 人から Share を回収する必要がある用途
- dealer と復元端末を信頼できず、Share の検証機能も追加できない構成
- k 個の Share を長期にわたって回収できる見込みのない保管用途
