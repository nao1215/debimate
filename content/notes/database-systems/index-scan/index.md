---
title: "Index Scan - 索引から表の行に届くまでに何が起きるか"
date: 2026-08-11
draft: false
series: ["技術ノート", "Database Systems"]
tags: ["database-systems", "index"]
weight: 4
---

Index Scan は、索引（インデックス）を辿って条件に一致する行の在り処を求め、そこから表の行を読み出す方法です。DB（データベース）が 1 つの表から行を取り出す手段の 1 つで、表を先頭から順に読む全走査（sequential scan）と対になります。

開発者がこの名前を目にするのは、遅い問い合わせの実行計画を眺めている時ではないでしょうか。実行計画とは、DB がその問い合わせをどの手順で処理すると決めたのかを表す出力で、その手順を選ぶ DB の部品をプランナと呼びます。一覧画面の表示に数秒かかるので索引を足したのに応答時間が戻らない、という場面で開くのがこの出力です。

索引が存在することと、問い合わせがその索引で速くなることは別です。DB は索引を辿った後で表の行を読みに行くことが多く、そこで読むページの枚数が応答時間を大きく左右します。

条件に一致する行が返るまでの流れを以下に示します。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
flowchart LR
    C["WHERE user_id = 42"] --> D["索引を根から降りて<br/>開始位置の葉を決める"]
    D --> L["葉の項目を順に読み<br/>行の在り処を得る"]
    L --> T["表のページを読む"]
    T --> R["結果の行"]
    classDef default fill:#eaf1f5,stroke:#9cabb5,color:#28343b;
```

上記の図の最初の 2 段は索引の中だけで完結し、最後の「表のページを読む」は条件によっては省けます。

本記事では、1 台の DB が B-Tree 系の索引を 1 本引いて `SELECT` の行を取り出す場合を例に、Index Scan が索引と表の間で何をしているのかと、同じ索引で速くなる場合とならない場合の分かれ目を説明します。取り上げる疑問は次の通りです。

- Index Scan は、索引を降りた後に表の行をどう読むのか。
- 同じ 100 行を返す Index Scan で、読むページが 4 枚と 103 枚に分かれるのはなぜか。
- index-only scan と bitmap scan は、表への読み出しをどう減らすのか。
- 索引があっても絞り込みに使いにくいのは、どんな条件なのか。

行を更新した時の索引の維持と、複数の処理が同時に読み書きする時の並行制御には触れません。どの方法を選ぶかを決める枠組みは [Query Processing](/notes/database-systems/query-processing/) のノートにあります。

---

### 前提

前提を 2 つ置きます。1 つ目は、DB が表も索引もページという固定長の区画に区切って管理し、ストレージとの読み書きもページ単位で行うことです。1 枚のページには複数の行が載り、一度読んだページはバッファキャッシュというメモリ上の控えにしばらく残ります。

2 つ目は、B-Tree 系の索引がキーの順に並んだ木で、一番上のノードを根、一番下に並ぶノードを葉と呼ぶことです。探索は根から葉に 1 段ずつ進むので、以降ではこの動きを「降りる」と書きます。木の構造は [B-Tree](/notes/database-systems/b-tree/) のノートで扱っています。

索引と表が別々に置かれる構成も前提に含めます。InnoDB の主キー索引のように葉が行そのものを持つクラスタ化索引では、表を読みに行く段が最初からありません。

`EXPLAIN` に出る名前も、どの取り出し方を備えているかも、DBMS（Database Management System）で違います。例えば、PostgreSQL の `EXPLAIN` では `Index Scan`、SQLite の `EXPLAIN QUERY PLAN` では `SEARCH ... USING INDEX` という行が出ます。そこに `Seq Scan` や `SCAN` が並んでいれば、索引は使われていません。以降では、多くの DBMS で見られる「索引を降りて表の行を読む」形を軸に置き、実装で割れる所は都度断ります。

---

### 索引を降りて表の行を読む流れ

Index Scan の動きは、冒頭の図に示した 3 つの段に分かれます。条件を外れるキーに当たった所で、葉を読み進める段が終わります。

この 3 つを動かすのは実行器です。実行器とは、実行計画の各段を実際に走らせる部分を指します。以下は、最初の 2 行を取り出すまでの往復です。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
sequenceDiagram
    participant E as 実行器
    participant I as 索引
    participant T as 表
    E->>I: 最初の 1 行を要求
    I-->>E: 開始位置の葉の 1 件目
    E->>T: 項目が指すページを読む
    T-->>E: 行を 1 つ返す
    E->>I: 次を要求
    I-->>E: 同じ葉の 2 件目
    E->>T: 別のページを読む
    T-->>E: 行を 1 つ返す
```

上記の図の表への読み出しは、その行が載っているページがバッファキャッシュに残っていればメモリの読み取りで済み、残っていなければストレージへの読み出しになります。

同じ動きは範囲の条件にも使えます。`created_at BETWEEN ... AND ...` なら、開始位置の葉まで 1 度降りた後は、条件を外れるまでキーを順に読み進めるだけです。索引がキーの順に並んでいるので、`ORDER BY` の指定が索引の並び順と一致していれば、その順序をそのまま結果の順序として使えます。

`LIMIT 10` を付けた問い合わせなら、10 行を返した時点で索引を読み進める必要が無くなります。

並べ替え（Sort）やハッシュ表を作る段（Hash）は入力をほぼ全件読むまで 1 行目を返せませんが、Index Scan は途中で止められます。

---

### 索引を引くだけで終わらない理由

索引の葉が持つのは、キーと、そのキーに対応する行を見つけるための情報です。行の全ての列が入っているわけではないので、必要な列の値が索引に無ければ、DB は葉から得た情報を頼りに表のページを読みに行きます。

多くの場合、問題になりやすいのは表のページを読む部分です。木を降りる間に読む索引のページは段数の分だけで、上の段ほどバッファキャッシュに残りやすいからです。

索引の中で隣り合うキーは、表の中でも隣り合うとは限りません。PostgreSQL のヒープ（表の行の本体を格納した領域）のように行を空いた場所に置いていく構成では、表の並びとキーの順序に関係がありません。一致した 100 行が 100 枚の別々のページに載っていれば、表のページを 100 枚読みます。

例えば、同じ 3 件は索引と表で次のように並びます。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
flowchart TB
    subgraph IDX["索引の葉：キーの順に並ぶ"]
        K1["user_id 42<br/>1 件目"]
        K2["user_id 42<br/>2 件目"]
        K3["user_id 42<br/>3 件目"]
    end
    subgraph TBL["表：キー順とは限らない物理配置"]
        P1["ページ 7"]
        P2["ページ 812"]
        P3["ページ 5309"]
    end
    K1 --> P1
    K2 --> P2
    K3 --> P3
    classDef default fill:#eaf1f5,stroke:#9cabb5,color:#28343b;
```

上記の図では、索引を 1 枚読んで得た 3 件のために表を 3 枚読んでいます。

この散らばり具合は、行が挿入・更新されてきた履歴で決まり、問い合わせの書き方では動きません。PostgreSQL は、この散らばり具合を数値にして、列ごとの統計情報（DB が列ごとに集計しておく値の分布などの情報）の 1 つとして `pg_stats` の `correlation` に持っています。

correlation は、列の値の順と表の中での行の並び順がどれだけ一致しているかを -1〜+1 で表し、+1 は同じ順、-1 は逆順、0 付近は無関係に散らばった状態です。プランナは、この値が ±1 に近いほど、ディスクへのランダムアクセスが減るとして、その列への index scan を安く見積もります（[pg_stats](https://www.postgresql.org/docs/current/view-pg-stats.html)）。

PostgreSQL 17.10 で、100 万件の注文を `user_id` の順に並べた表 `orders_sorted` と、同じ行をランダムな順に並べた表 `orders_random` を作り、どちらにも `user_id` の索引を張りました。`correlation` は 1 とほぼ 0 です。

`user_id = 4242` に一致する 100 行の、索引に無い列 `status` を取り出した結果（抜粋）は以下の通りです。散らばった表ではプランナが bitmap scan（表をページの順に読む取り出し方）を選ぶので、`enable_bitmapscan` を off にして両方とも Index Scan に揃えています。

```text
 Index Scan using orders_sorted_user_id_idx on orders_sorted (actual rows=100 loops=1)
   Buffers: shared hit=1 read=3

 Index Scan using orders_random_user_id_idx on orders_random (actual rows=100 loops=1)
   Buffers: shared hit=39 read=64
```

`Buffers` は、その走査で触ったページの延べ枚数です（hit はバッファキャッシュにあった枚数、read はストレージから読んだ枚数）。同じ 100 行を返すのに、並んだ表では 4 枚、散らばった表では 103 枚を読んでいます。索引を降りる分は数枚なので、前に書いた表の 100 枚がほぼそのまま出ています。

一致する行が増えるほど、表のページの読み出しは積み上がります。一方、全走査が読むページの枚数は、条件で絞れた割合、つまり選択性（selectivity）では動きません。そのため、2 つの経路が読む枚数はどこかで入れ替わります。

![選択性を横軸に取った概念図。全走査が読むページ枚数は水平のまま変わらず、Index Scan は右上がりに増えて途中で交わる。一致した行がページに散っている場合は交点が左へ、表の並びとキーの順序が揃っている場合は交点が右へ動く](images/index_scan_crossover.svg)

上記の図に目盛りを置いていないのは、実測ではない概念図で、交点の位置も表の大きさと行の散らばり具合（scattered／clustered）で動くためです。表が小さいほど全走査の読む枚数そのものが少ないので、交点は左へ寄ります。PostgreSQL のドキュメントには、100 行から 1 行を選ぶ例について、その 100 行がおそらく 1 枚のディスクページに収まるので「[there is no plan that can beat sequentially fetching 1 disk page](https://www.postgresql.org/docs/current/indexes-examine.html)」（1 枚のディスクページを順に読むことに勝てる計画は無い）とあります。

ここまでを 1 本にまとめると、Index Scan で読む量はおよそ「索引で読むページ + 表で読むページ」で、選択性と correlation で決まります。読む量を減らす手段は次の 3 つです。

- index-only scan：表で読むページを減らす
- bitmap scan：表のページを読む順序を変える
- `LIMIT`：必要な所で走査を止める

---

### 表への読み出しを減らす index-only scan

必要な列が全て索引に入っていれば、2 段目を省ける場合があります。PostgreSQL ではこの形を index-only scan と呼びます。

ある問い合わせに必要な列が全て入っている索引は、その問い合わせに対する [covering index](https://dev.mysql.com/doc/refman/8.4/en/glossary.html) と呼ばれます。

covering index に当たるかどうかは、索引の種類ではなく問い合わせとの組み合わせで決まります。

取り出す列だけを変えると実行計画がどう動くのかは、手元の SQLite（3.44.4）で確かめられます。張ってある索引は 1 本で、`user_id` と `amount` の 2 列をこの順に並べた複合索引です。

```sql
-- orders は 100 万件。user_id は 1 万種類で、1 つの値につきおよそ 100 行。
-- CREATE INDEX idx_orders_user_amount ON orders(user_id, amount);
EXPLAIN QUERY PLAN SELECT status FROM orders WHERE user_id = 42;
EXPLAIN QUERY PLAN SELECT amount FROM orders WHERE user_id = 42;
```

返ってきた実行計画は次の通りです。

```text
QUERY PLAN
`--SEARCH orders USING INDEX idx_orders_user_amount (user_id=?)

QUERY PLAN
`--SEARCH orders USING COVERING INDEX idx_orders_user_amount (user_id=?)
```

条件も索引も同じで、違うのは取り出す列だけです。`status` は索引に入っていないので表を読む必要があり、`amount` は索引に入っているので `USING COVERING INDEX` に変わりました。SQLite のドキュメントには、この最適化の効果として「[saves one binary search for each row](https://www.sqlite.org/optoverview.html)」（1 行ごとに二分探索を 1 回節約する）とあります。

以下が 2 つの経路の分かれ目です。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
flowchart TB
    Q["WHERE user_id = 42"] --> D{"取り出す列が<br/>索引に揃っているか"}
    D -->|"揃っていない"| A1["索引を降りる"]
    A1 --> A2["表のページを読む"]
    A2 --> R["結果の行"]
    D -->|"揃っている"| B1["索引を降りる"]
    B1 --> R
    classDef default fill:#eaf1f5,stroke:#9cabb5,color:#28343b;
```

上記の図の揃っている経路では、一致する行が多い問い合わせほど「表のページを読む」を省けた時の差が大きくなります。索引に列を足せばこの経路に寄せられるため、PostgreSQL は検索の対象にしない列を索引に載せる `INCLUDE` を用意しています。

表を読まずに済むかどうかは、列が揃っているかだけでは決まりません。PostgreSQL は行を更新・削除しても古い行をしばらく残すので、索引の項目が指す行を今のトランザクションが読んでよいとは限りません。PostgreSQL の索引は、この「見えるかどうか」の情報を持ちません。

そのため、候補の項目を見つけた後で、対応するヒープページの visibility map のビットを確認すると[ドキュメント](https://www.postgresql.org/docs/current/indexes-index-only-scans.html)は説明しています。

visibility map は、ヒープページ 1 枚につき 1 ビットを持つ一覧です。そのページに載る全ての行が、現在と将来の全てのトランザクションから見えると分かっている時にビットが立ちます。以下は、ビットを確認してからの分かれ道です。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
flowchart TB
    F["索引で候補の項目を見つける"] --> V{"対応するヒープページの<br/>visibility map のビット"}
    V -->|"立っている"| A["索引から取り出した値を<br/>そのまま返す"]
    V -->|"立っていない"| B["ヒープの行そのものを読む"]
    classDef default fill:#eaf1f5,stroke:#9cabb5,color:#28343b;
```

上記の図の下の経路が残るので、index-only scan はヒープへの読み出しを大きく減らす形であって、必ず 0 にする形ではありません。実際に何回ヒープを読みに行ったのかは、[`EXPLAIN ANALYZE`](https://www.postgresql.org/docs/current/using-explain.html) の出力に出る `Heap Fetches` で分かります。

---

### 行の位置を集めてページ順に読む bitmap scan

表への読み出しが散らばる問題には、索引から一致した行の位置を先に全部集めて印を付け、その後で表をページの順に読む手もあります。これが bitmap scan で、PostgreSQL では索引 1 本の場合にもこの形が選ばれます。複数の索引を組み合わせる際には、必要な索引をそれぞれ走査して「[prepares a bitmap in memory giving the locations of table rows](https://www.postgresql.org/docs/current/indexes-bitmap-scans.html)」（表の行の位置を示すビットマップをメモリ上に用意する）と説明されています。

このビットマップは、表の中での行の位置の順に並んでいます。どの索引から作っても並び方が同じなので、問い合わせに応じて AND や OR で重ねられます。

例えば、2 本の索引を合成する場合は次の流れになります。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
flowchart LR
    I1["索引 A を走査"] --> B1["行の位置の<br/>ビットマップ"]
    I2["索引 B を走査"] --> B2["行の位置の<br/>ビットマップ"]
    B1 --> AN["AND / OR で合成"]
    B2 --> AN
    AN --> S["表のページを<br/>物理的な順に読む"]
    S --> R["結果の行"]
    classDef default fill:#eaf1f5,stroke:#9cabb5,color:#28343b;
```

上記の図の最後で表を読む順序は、索引に並んでいた順ではなく物理的な順です。同じページに載っている行をまとめて処理でき、ページを何度も読み直す動きが減ります。同じドキュメントは、その代償として「[any ordering of the original indexes is lost](https://www.postgresql.org/docs/current/indexes-bitmap-scans.html)」（元の索引が持っていた順序は失われる）と書き、`ORDER BY` があれば別に整列の段が必要だと続けています。

先頭の 1 行が返るまでの時間も変わります。ビットマップを合成し終えるまで表を読み始められないので、索引を降りた直後に 1 行目が返るという性質は失われます。

ビットマップが割り当てられたメモリに収まらない場合の扱いにも注意が必要です。PostgreSQL は行単位での保持を諦めてページ単位に落とします。そうするとページ内のどの行が一致したかが分からなくなるので、そのページの全ての行で条件を確かめ直します。

---

### 索引があっても絞り込みに使いにくい条件

1 つ目の型は、索引の構造と問い合わせ条件が噛み合わないものです。

| 条件 | なぜ絞り込みに使いにくいか |
| --- | --- |
| 列に関数や演算を掛けている | 通常の列索引に入っているのは元の値なので、計算後の値では葉を辿れない |
| 複合索引の先頭列に条件が無い | 一般には走査する範囲を狭めにくい |

この型は、先ほどの SQLite で再現できます。取り出す列を `SELECT status` に固定したまま条件だけを変えると、`WHERE user_id + 0 = 42` も `WHERE amount = 42` も `SCAN orders` になりました。

`SCAN` は索引の順に辿る場合も含めて全ての行を訪れること、`SEARCH` は表の行の一部だけを訪れることを表します（[SQLite のドキュメント](https://www.sqlite.org/eqp.html)）。絞り込めているかどうかは、この 2 語の差に出ます。

最初の表に挙げた 2 つの条件には、それぞれ回避手段と例外があります。

関数や演算を掛けた条件には、式に張る索引で対応できます。PostgreSQL の[ドキュメント](https://www.postgresql.org/docs/current/indexes-expressional.html)によれば、`lower(col1)` の結果に索引を定義してあれば、`lower(col1) = 'value'` という条件でも索引を使えます。以下は、列と式に張った索引の比較です。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
flowchart LR
    subgraph COL["列に張った索引"]
        direction TB
        Q1["WHERE user_id + 0 = 42"] -.->|"計算後の値では<br/>辿れない"| K1["葉に並ぶのは<br/>user_id の元の値"]
    end
    subgraph EXP["式に張った索引"]
        direction TB
        Q2["WHERE lower(col1) = 'value'"] -->|"辿れる"| K2["葉に並ぶのは<br/>lower(col1) の結果"]
    end
    classDef default fill:#eaf1f5,stroke:#9cabb5,color:#28343b;
```

先頭列に条件が無い場合の制約は、複合索引の並び順から出ています。PostgreSQL は、複合索引が索引の列の任意の部分集合を含む条件で使えるとした上で、「[the index is most efficient when there are constraints on the leading (leftmost) columns](https://www.postgresql.org/docs/current/indexes-multicolumn.html)」（索引が最も効率的なのは、先頭（最も左）の列に制約がある時）としています。

以下は、先ほどの複合索引 `(user_id, amount)` の葉の並びです。`amount` の値は説明用です。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
flowchart LR
    P1["user_id 1<br/>amount 10, 42, 87"] --> P2["user_id 2<br/>amount 7, 42"] --> P3["…"] --> P4["user_id 42<br/>amount 3, 42, 55"]
    N1["user_id = 42<br/>1 か所にまとまる"]:::note -.- P4
    N2["amount = 42<br/>user_id ごとに散る"]:::note -.- P2
    classDef default fill:#eaf1f5,stroke:#9cabb5,color:#28343b;
    classDef note fill:#f7f1e5,stroke:#c5b99b,color:#403c32;
```

先頭列の条件が無くても、索引を読むこと自体はできます。ただし、上記の図の `amount = 42` のように項目が散ると、多くの場合は索引の全体を読む形になり、走査する範囲が絞られません。何を読むのが安いかはそこで改めて見積もられ、表の全走査が選ばれることもあります。

例外として、同じページは skip scan にも触れています。skip scan は、先頭列の取り得る値がごく少ないとプランナが見積もった場合に、その値ごとの等値の条件を内部で作り、「[skip over most of the index](https://www.postgresql.org/docs/current/indexes-multicolumn.html)」（索引の大半を読み飛ばす）形で走査する範囲を減らす方法です。

---

### 見積もりで全走査に負ける条件

2 つ目の型は、索引を使う候補は作れるものの、コストの見積もりで全走査に負けるものです。

| 条件 | なぜ全走査が選ばれるか |
| --- | --- |
| 一致する行が表の大部分を占める | 索引を使う候補より、全走査の方が安いと見積もられる |
| 統計情報が古い | 推定行数が実際とずれ、全走査の方が安いと見積もられる |

上記の表のどちらの行も、見積もりの結果として現れます。実際の行数そのものではなく、統計から見積もった推定行数を材料にコストが計算されるからです。

索引が使われない理由を調べたい時は、PostgreSQL の `enable_seqscan` のような設定を使い、全走査を選びにくくして別の計画が成立するかを確かめます。[ドキュメント](https://www.postgresql.org/docs/current/indexes-examine.html)を踏まえると、それでも全走査が選ばれるなら、条件が索引と噛み合っていないなどのより根本的な理由がある可能性が高いと考えられます。

---

### 利点

- 表の行数が増えても、読む量は表の大きさではなく一致する行数でおおむね決まる
- 索引の並び順をそのまま使えるため、`ORDER BY` の整列を省ける場合がある
- 先頭の数行だけが必要な問い合わせでは、途中で走査を止められる
- 必要な列が索引に揃っていれば、表への読み出しを大きく減らせる

---

### 欠点

Index Scan は、条件に一致する行だけに届く代わりに、表の並びと条件の書き方に左右されます。そのため、次の制約があります。

- 索引と表の 2 か所を読むため、一致する行が増えるほど表を読む回数が積み上がる
- 条件の書き方で索引を使えるかどうかが変わり、些細な違いで実行計画が動く
- 索引を増やすほど、行を更新するたびに書き換える対象が増える

---

### Index Scan の効果が小さくなりやすいケース

- 条件に一致する行が表の大部分を占め、索引を辿った末にほとんどのページを読む場合
- 表が小さく、全体が数ページに収まる場合
- 索引の順序と表の並び順の相関が低く、一致した行が多数のページに散っている場合
- 取り出す列が多く、索引だけでは揃わない場合

1 つ目で影響しているのは選択性です。値の種類が少ない列だから索引が働かない、という話ではありません。値が 2 種類でも、片方が全体の 0.01% しか無ければ、その値で絞り込む問い合わせでは索引で読む量を減らせる場合があります。

3 つ目と 4 つ目は、表や索引の作り方を変えれば効果が戻ることがあります。PostgreSQL の `CLUSTER` のように、索引の順序に合わせて表の行を並べ直す操作を持つ DBMS もあります。

どの手段が選ばれるかを最後に決めるのは、冒頭で触れたプランナです。PostgreSQL のように索引を名指しするヒントを持たない DBMS では、書き手にできるのは選ばれ得る候補を用意する所までだと考えられます。
