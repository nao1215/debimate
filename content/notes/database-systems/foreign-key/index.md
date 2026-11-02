---
title: "Foreign Key - 参照先の存在を DB に保証させる"
date: 2026-08-12
draft: false
series: ["技術ノート", "Database Systems"]
tags: ["database-systems", "data-modeling"]
weight: 8
wrapTables: true
---

外部キー制約（foreign key constraint）は、ある表の列に入っている値が、別の表に実在する行を指していることを DB（データベース）に保証させる仕組みです。[PostgreSQL](https://www.postgresql.org/docs/current/ddl-constraints.html) の定義では、1 つの列または複数の列の組の値が、別の表のいずれかの行に現れる値と一致する必要があります。この保証が保たれている状態を参照整合性（referential integrity）と呼びます。

この制約が必要になる場面の代表は、注文の一覧に「存在しない会員の ID」が混ざった時の調査です。会員別の集計と、注文表を素直に合計した値が食い違います。その ID が `INSERT` の時に入ったのか、会員を消した時に生まれたのかも、後からは辿れません。

例えば、会員（`members`）と注文（`orders`）の関係は以下のようになります。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
erDiagram
    members ||--o{ orders : "member_id が参照する"
    members {
        bigint id PK
        text name
    }
    orders {
        bigint id PK
        bigint member_id FK
        int amount
    }
```

上記の図の `||--o{` は、`members` の 1 行に対して `orders` が 0 行以上ぶら下がる関係を表します。PK は主キー（その表で行を一意に決める列）、FK は外部キーです。参照される `members` を親、参照する `orders` を子と呼びます。

本記事では、1 つの DB の中で表と表を結ぶ外部キー制約を説明します。孤児レコードが生まれる経路から始めて、次の疑問に答えます。

- 外部キーが無いと、参照先の無い行はどんな経路で生まれるのか。
- アプリケーションで親の存在を確かめるだけでは、なぜ足りないのか。
- 確認と書き込みの間に親が消えた時、外部キー制約はどう止めるのか。
- 親の行を消す時、子の行をどう扱うのか。
- 外部キーを張らない場合、誰が参照整合性を守るのか。

サービスをまたいだ参照には、「外部キーを張らない場合に整合性を守る担当」の節でだけ触れます。以降の SQL は PostgreSQL の構文で書きます。

---

### 外部キーが無い時に生まれる孤児レコード

制約は子の表に書きます。参照先の列は、値から 1 行に決まる（重複しない）ことを DB が保証している必要があります。PostgreSQL でこの保証に当たるのは、主キー・一意制約・一意索引（部分索引を除く）のどれかです。索引は、列の値から該当する行の位置を引ける補助の構造です。参照する値が参照先で一意に特定できないと、この `CREATE TABLE` 自体が失敗します。

```sql
CREATE TABLE members (
    id   BIGINT PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE orders (
    id        BIGINT PRIMARY KEY,
    member_id BIGINT NOT NULL REFERENCES members (id),
    amount    INT NOT NULL
);
```

制約を書かなかった場合、`member_id` はただの整数の列になります。DB は、その値が `members` の誰かを指しているかどうかを見ません。参照先の無い子の行は孤児レコードと呼ばれ、次の 2 つの経路で生まれます。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
flowchart TB
    A["存在しない ID で INSERT<br/>member_id = 999"] --> O["孤児レコード<br/>参照先の無い注文"]
    B["親を DELETE<br/>会員 42 を削除"] --> O
    O --> C["INNER JOIN で消える"]
    O --> D["会員別の集計に入らない"]
    O --> E["注文から会員名を引けない"]
    classDef default fill:#eaf1f5,stroke:#9cabb5,color:#28343b;
```

どちらの経路でも、`INSERT` や `DELETE` はエラーを返しません。制約が無いので、DB にとっては正常な書き込みです。孤児が生まれた瞬間には何も起きず、後から読む時に影響が出ます。

```sql
-- 外部キー制約を張っていない orders の場合。members に id = 999 の行は無い
INSERT INTO orders (id, member_id, amount) VALUES (1001, 999, 3000);
```

この行を含む注文表に会員名を付けて一覧する問い合わせを考えます。`orders` と `members` を `INNER JOIN` で繋ぐと、対応する会員の行が無い注文 1001 は結果から落ちます。`orders` を単独で合計した売上とは、3,000 円の差が出ます。

この差が読み取りの誤りではない点が、調査を長引かせる原因になります。どちらの問い合わせも書いた通りに動いており、`JOIN` の結果が正しい以上、DB は矛盾を報告しません。孤児は、探しに行った人にだけ見えます。

---

### アプリケーションでの存在確認が届かない範囲

外部キー制約を張らずに、注文を作る処理の中で会員の存在を確かめる方法もあります。注文 API のコードに `SELECT` を 1 本足せば済む、という判断です。この方法が守れるのは、その処理を通った書き込みだけになります。表を更新する経路が 1 本だとは限りません。

例えば、同じ `orders` を更新し得る経路には次のようなものがあります。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
flowchart LR
    A["注文 API<br/>存在確認あり"] --> T[(orders)]
    B["夜間バッチ<br/>他社データの取り込み"] --> T
    C["管理者が手で流す SQL"] --> T
    D["Migration<br/>表の定義を変える一括処理"] --> T
    E["障害復旧の際の<br/>データ修正"] --> T
    classDef default fill:#eaf1f5,stroke:#9cabb5,color:#28343b;
```

上記の図で存在確認を行うのは注文 API だけです。経路が増えるたびに、同じ検査を書き足す必要があります。書き足し忘れても構文の誤りにはならないので、その経路からの書き込みは DB に止められません。

外部キー制約は、この検査を DB に 1 つ置きます。どの経路から来た `INSERT` でも同じ検査が掛かり、通らない書き込みはエラーで止まります。守れる範囲を広げているのは、検査の内容ではなく検査を置いた位置です。

---

### 存在の確認と書き込みの間に起きる削除

アプリケーションでの存在確認には、経路の数とは別の弱点があります。`SELECT` で親の行を確かめてから `INSERT` するまでの間に、別のトランザクションが親を消せる点です。経路を 1 本に絞り込んでも、この弱点は残ります。

トランザクションは、まとめて成功か失敗かを決める書き込みのひとかたまりで、`COMMIT` で確定します。以下は、2 つのトランザクションが重なった時の順序です。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
sequenceDiagram
    participant A as 注文 API
    participant DB as DB
    participant B as 退会処理
    A->>DB: SELECT id FROM members<br/>WHERE id = 42
    DB-->>A: 1 件ある
    B->>DB: DELETE FROM members<br/>WHERE id = 42
    B->>DB: COMMIT
    A->>DB: INSERT INTO orders<br/>(member_id = 42)
    A->>DB: COMMIT
    Note over A,B: 確認は成功し<br/>結果は孤児レコード
```

上記の図の注文 API は、自分の見た結果に従って正しく動いています。確認した時点では会員 42 が実在し、`INSERT` を出す時点では実在しません。

競合した時にどう振る舞うかは、分離レベル（同時に走るトランザクションどうしが互いの変更をどこまで見るかの設定）・ロックの取り方・DBMS（Database Management System）の実装方式で変わります。これらを工夫して競合を防げても、「`orders.member_id` は必ず `members.id` を指す」という規則を守り続ける責任は、注文を `INSERT` する処理にも会員を `DELETE` する処理にも残ります。分離レベルは [Transaction Isolation](../transaction-isolation/) のノートで扱っています。

外部キー制約を書けば、確認と書き込みを DB が 1 つの操作として扱います。PostgreSQL 17.10 で外部キー制約を張った表に、上記の図の 2 本を流しました。図と違い、退会処理は `DELETE` から `COMMIT` までを 3 秒空け、その途中で注文 API が `INSERT` を出しています。

```text
-- 注文 API 側の psql（抜粋）
INSERT INTO orders (id, member_id, amount) VALUES (1001, 42, 3000);
ERROR:  insert or update on table "orders" violates foreign key constraint "orders_member_id_fkey"
DETAIL:  Key (member_id)=(42) is not present in table "members".
```

外部キーの検査は会員 42 の行にロックを取ろうとするので、`INSERT` は退会処理の `COMMIT` まで待たされ（約 2.5 秒）、会員が消えたと分かった時点でエラーになりました。注文 1001 は入らず、孤児は生まれていません。`COMMIT` が `INSERT` より先なら、待たずに同じエラーで止まります。

---

### 制約を書いても検査されない行

外部キー制約を書いても、全ての行が検査されるとは限りません。まず、制約が有効になっていることが必要です。SQLite のドキュメントには「[Foreign key constraints are disabled by default (for backwards compatibility), so must be enabled separately for each database connection.](https://www.sqlite.org/foreignkeys.html)」（外部キー制約は既定で無効で、接続ごとに有効にする必要がある）とあります。

制約を後から張る場合は、検査の範囲に注意が必要です。PostgreSQL で `NOT VALID` を付けると、制約を足す前からある行の一括検査を省けます。以降の `INSERT` と `UPDATE` には制約が掛かり、既存の行は後から `VALIDATE CONSTRAINT` で検証できます。

参照の列が `NULL` の行も、外部キー制約に違反しません。PostgreSQL には「[Normally, a referencing row need not satisfy the foreign key constraint if any of its referencing columns are null.](https://www.postgresql.org/docs/current/ddl-constraints.html)」（参照する側の列のいずれかが NULL であれば、通常その行は外部キー制約を満たす必要が無い）と書かれています。

`member_id` を `NULL` 可にすると、会員を指さない注文が制約を通ります。上の DDL では `NOT NULL` を付けているので、その行は入りません。

---

### ON DELETE の指定と親子の所有関係

外部キー制約を張ると、親の行を消す操作の意味を決める必要が出ます。`ON DELETE` に何を書くかで、削除が子にどう及ぶのかが変わります。制約の検査は通常は文ごとに行われ、`DEFERRABLE` を付けた制約では `COMMIT` まで遅らせられます。PostgreSQL が用意している指定を整理すると、以下の通りです。

| 指定 | 親を `DELETE` した時 | 注意する点 |
| --- | --- | --- |
| `NO ACTION` | 子が残っていればエラー | 既定。`DEFERRABLE` を付けた制約でだけ検査を遅らせられる |
| `RESTRICT` | 子が残っていればエラー | 検査を遅らせられない。事後の状態が違反にならない操作も拒否する |
| `CASCADE` | 子も一緒に消える | 連鎖は子の子にも続く |
| `SET NULL` | 子は残り、参照の列が `NULL` になる | 参照の列が `NOT NULL` なら、その `DELETE` は失敗する |
| `SET DEFAULT` | 子は残り、参照の列が既定値になる | 既定値が `NULL` 以外なら、その値を持つ親の行が必要 |

`NO ACTION` と `RESTRICT` は、どちらも子が残っていれば親を消せません。検査を遅らせられると、親と子をまとめて差し替える処理を書けます。例えば、親の行をいったん消して同じ ID で入れ直す処理は、途中で一時的に参照先が欠けても、`COMMIT` の時点でそろっていれば違反になりません。`RESTRICT` はこうした操作も拒否します。既定は `NOT DEFERRABLE` なので、上の DDL のままでは検査を遅らせられません。利用できる指定と検査のタイミングは DBMS で違います。

どれを選ぶかは、性能や書きやすさではなく、子の行が親なしで意味を持つかどうかで決まります。以下が判断の分かれ目です。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
flowchart TB
    Q{"親が消えた後、子の行は<br/>単独で意味を持つか"}
    Q -->|"持たない<br/>注文と注文明細"| C["CASCADE<br/>親の一部として消す"]
    Q -->|"持つ<br/>会員と注文"| R["NO ACTION / RESTRICT<br/>消させない"]
    Q -->|"持つが参照は切って良い<br/>担当者と案件"| S["SET NULL<br/>参照だけ外す"]
    classDef default fill:#eaf1f5,stroke:#9cabb5,color:#28343b;
```

上記の図の注文明細は、注文 1 件に含まれる商品ごとの行です。注文が消えれば残す理由が無く、所有している側が消える時に一緒に消える関係なので `CASCADE` が合います。会員と注文は違い、退会しても過去の売上の記録として残す必要があります。案件から担当者への参照のように、相手が居なくなっても行そのものは残したい関係では `SET NULL` が合います。

`CASCADE` を「親を消す時に子を消す手間が省ける指定」として選ぶと、子が親なしで意味を持つかという判断を飛ばしてしまいます。連鎖は子の子にも続くので、会員を 1 行消した結果として、注文と注文明細がまとめて消える構成にもなります。行を残したい要求は、[Soft Delete](../soft-delete/) のノートで扱う設計課題です。

---

### 外部キーを張らない場合に整合性を守る担当

外部キー制約を置かない構成もあります。代表的なのは次の 3 つです。

- 親と子が別のサービスの DB にあり、参照が DB の外をまたぐ
- シャーディング（1 つの表を複数のサーバーに分けて置く構成）で親と子が別のノードにある
- 履歴や監査ログのように、現在の親との参照整合性より、記録した時点の情報をそのまま残すことを優先する

前の 2 つは、制約を置ける場所に親が居ない形です。3 つ目は親が同じ DB に居るので事情が違います。追記しかしないから張れないのではなく、現在の会員との関係を保つ必要が無く、その時点の記録として独立して残すことに意味があるからです。`RESTRICT` で親の削除を止めるのも `CASCADE` で消すのも、この要求には合いません。

3 つ目では、`SET NULL` で参照だけ外す選択も残っています。参照の列を `NOT NULL` にできないことと、消えた相手が誰だったかを別の列に写しておく必要が出ることが、その代償です。記録として残す列を別に持てるなら、外部キー制約を保ったまま行を残せます。

制約を外した場合、参照整合性を守る担当は DB の外に移ります。移し先は、代表的には次の 3 つです。

- 親と子を変更する経路を 1 か所に集め、作成・更新・削除の全部で同じ参照整合性の規約を守る
- 孤児を定期的に検出し、業務の判断で直すか消すかを決める
- 孤児が居る前提で読み、表示を組み立てる処理で欠けた参照を扱う

1 つ目は、注文を作る API を 1 本にするだけでは足りません。会員を消す処理が別にある限り、その処理にも同じ規約を通さないと隙間が残ります。2 つ目の検出は、`LEFT JOIN` で書けます。この結合は対応する会員が無くても注文の行を残し、会員の列を `NULL` にします。

```sql
SELECT o.id, o.member_id
FROM orders o
LEFT JOIN members m ON m.id = o.member_id
WHERE o.member_id IS NOT NULL
  AND m.id IS NULL;
```

`m.id IS NULL` が孤児の条件になるのは、`members.id` が `NOT NULL` の主キーだからです。`o.member_id IS NOT NULL` を足しているのは、初めから誰も参照していない行と、参照先が消えた行を混ぜないためです。2 つは業務上の扱いが違います。

検出は、孤児が生まれることを止めません。見付かった時点で、その注文をどう扱うのかという業務の判断が必要です。3 つ目の「居る前提で読む」は、その判断を読み取りの処理に埋め込む方法で、会員名の欄に「退会済み」と出すような扱いになります。

外部キーを張らない設計は、条件がそろえば妥当な選択です。決めておくことは、参照先の存在を誰がいつ確かめるのか、確かめられなかった行をどう扱うのかの 2 つになります。この 2 つを決めないまま制約を外すと、担当が誰にも割り当てられていない状態になります。

---

### 利点

- 制約が有効である限り、どの経路から来た書き込みでも参照先の無い行が入らない
- 親の削除と子の追加が競合しても、参照整合性の維持を DB に任せられる
- 親を消した時の扱いが表の定義に宣言として残り、経路ごとの実装に散らない
- 表と表の関係が定義から読み取れ、後から構造を辿れる

---

### 欠点

外部キー制約は、参照の検査を DB に寄せます。その分、次の負担と縛りが生じます。

- 子への書き込みのたびに親の存在を確かめるので、書き込みの負担が増える
- 親の削除や更新のたびに子を探すので、子の列に索引が無いと表の走査になる
- 表をまたぐ検査なので、親と子が別のノードに分かれる構成では張りにくい
- 一括での投入や DB の移行で、親から先に入れるという順序の縛りが出る
- `CASCADE` の連鎖が、設計時に想定した範囲を超えて広がることがある

欠点の 2 つ目に挙げた子の列の索引は、DBMS によって扱いが違います。PostgreSQL のドキュメントには「[the declaration of a foreign key constraint does not automatically create an index on the referencing columns](https://www.postgresql.org/docs/current/ddl-constraints.html)」（外部キー制約の宣言は、参照する列に索引を自動では作らない）とあります。

DBMS によっては自動で作るものもあります。索引の有無で親の削除がどう変わるのかを以下の図に示します。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
flowchart LR
    D["DELETE FROM members<br/>WHERE id = 42"] --> Q{"orders.member_id に<br/>索引があるか"}
    Q -->|"ある"| I["索引を引いて<br/>該当する注文を探せる"]
    Q -->|"無い"| S["orders を端から走査して<br/>member_id = 42 を探す"]
    classDef default fill:#eaf1f5,stroke:#9cabb5,color:#28343b;
```

上記の図の索引が無い経路では、子の表が大きくなるほど親を 1 行消す操作が重くなります。索引の構造は [B-Tree](../b-tree/) のノートで扱っています。

欠点の 3 つ目に挙げた、親と子が別のノードに分かれる構成についても、分散を前提に作られた DBMS には外部キーを支援するものがあります。
