---
title: "Deadlock - 更新順序が逆になると何が起きるか"
date: 2026-08-12
draft: false
series: ["技術ノート", "Database Systems"]
tags: ["database-systems", "transaction"]
weight: 11
wrapTables: true
---

Deadlock（デッドロック）は、2 本以上のトランザクションが互いのロックの解放を待ち、どれも先に進めなくなる状態です。行を更新すると DBMS（Database Management System）はその行にロックを取り、通常はトランザクションが終わるまで解放しません。

開発者がこの名前を目にするのは、エラーログの中ではないでしょうか。PostgreSQL は `deadlock detected`、MySQL は `Deadlock found when trying to get lock; try restarting transaction` を返します。手元で 1 本ずつ動かしている間は出ず、同じ処理が同時に走る本番環境で遭遇しやすいです。

1 行目を更新した後に 2 行目を待っている間も、1 行目のロックは握ったままです。例えば、2 本が同じ 2 行を逆の順で触ると、次の図のようになります。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
sequenceDiagram
    participant A as 送金 A
    participant R1 as 口座 1 の行
    participant R2 as 口座 2 の行
    participant B as 送金 B
    A->>R1: 更新してロックを取る
    B->>R2: 更新してロックを取る
    A->>R2: 更新したい<br/>B の解放を待つ
    B->>R1: 更新したい<br/>A の解放を待つ
    Note over A,B: 互いの解放を待ち<br/>どちらも進まない
```

上記の図の送金 A と送金 B は、互いに相手を待っています。誰が誰を待っているのかを辿ると出発点に戻るため、この関係を循環待ち（circular wait）と呼びます。2 本とは限りません。A が B を待ち、B が C を待ち、C が A を待つ形でも同じく循環します。

本記事では、PostgreSQL の挙動を基本に、デッドロックの終わり方と防ぎ方を説明します。挙動が違う箇所では MySQL と Oracle Database の例も示します。検出の仕組みから再試行まで、次の疑問に答えます。

- DBMS は、デッドロックをどう見付けて終わらせるのか。
- ロックの取得順序を揃えるには、何が必要なのか。
- 同じ 1 行を同じ順序で触る 2 本が、なぜデッドロックするのか。
- 中止されたトランザクションは、どう再試行すれば良いのか。

トランザクションに何を入れるかの判断は [Transaction Scope](../transaction-scope/)、分離レベルは [Transaction Isolation](../transaction-isolation/) の題材とします。

---

### DBMS によるデッドロックの検出と中止

循環待ちができても、結果が壊れるわけではありません。多くの DBMS はこの循環を検出し、関わっているどれかを巻き戻します。

どれが巻き戻されるかは、アプリケーションからは選べず、PostgreSQL でも予測して当てにできるものではありません。

以下は、待ちが起きてから処置に至るまでの流れです。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
flowchart LR
    W["ロック待ちが発生"] --> T["deadlock_timeout まで待つ"]
    T --> U{"その前に<br/>ロックを取得できたか"}
    U -->|"取得できた"| P["処理を続ける"]
    U -->|"まだ待っている"| C{"循環待ちがあるか"}
    C -->|"無い"| H["ロックの解放を待つ"]
    C -->|"ある"| K["1 本を中止"]
    K --> R["呼び出し側が再試行"]
    classDef default fill:#eaf1f5,stroke:#9cabb5,color:#28343b;
```

上記の図の検査は、待つたびに走るわけではありません。PostgreSQL で検査の契機になるのは、待ち時間が `deadlock_timeout` を超えた時です。検査のコストが高いため、[一定時間待ってから調べる設計](https://www.postgresql.org/docs/current/runtime-config-locks.html)で、既定は 1 秒です。

`deadlock_timeout` は検査を始めるまでの時間で、待ちを打ち切る時間ではありません。循環していない待ちは検出の対象外で、別の打ち切り設定が無ければ待ち続けます。[PostgreSQL](https://www.postgresql.org/docs/current/runtime-config-client.html) の `lock_timeout` は既定が 0 で、この打ち切りは無効です。

---

### 中止される範囲

デッドロックで中止される範囲は、PostgreSQL と MySQL の [InnoDB](https://dev.mysql.com/doc/refman/8.4/en/innodb-deadlocks.html)（MySQL のストレージエンジン）ではトランザクション全体、Oracle Database ではデッドロックに関わった 1 文だけです。[Oracle Database](https://docs.oracle.com/en/database/oracle/oracle-database/23/cncpt/data-concurrency-and-consistency.html) で解放されるのはその文に伴うロックの一部で、それ以前の文で取得したロックや変更はトランザクションの中に残ります。

デッドロックの検出と、ロック待ちのタイムアウトは別の仕組みです。InnoDB は検出を設定で止めることもでき、止めた場合はロック待ちのタイムアウトが循環待ちを解く役目を引き受けます。[MySQL](https://dev.mysql.com/doc/refman/8.4/en/innodb-parameters.html) の `innodb_lock_wait_timeout`（既定は 50 秒）を超えた時に巻き戻されるのは、既定では待っていたその 1 文だけで、トランザクション自体は続きます。[MySQL のドキュメント](https://dev.mysql.com/doc/refman/8.4/en/innodb-parameters.html#sysvar_innodb_rollback_on_timeout)によれば、`innodb_rollback_on_timeout` を有効にした場合に限り、トランザクション全体が巻き戻ります。以下は、1 本のトランザクションの中で巻き戻る範囲を並べた図です。

{{< note-panels caption="同じエラー処理でも、どの文まで巻き戻るかを区別します。" >}}
- title: PostgreSQL / InnoDB のデッドロック検出
  steps:
  - 文 1：巻き戻す
  - 文 2：巻き戻す
  - 待っていた文：巻き戻す
- title: InnoDB のロック待ちタイムアウト（既定）/ Oracle Database のデッドロック
  steps:
  - 文 1：残る
  - 文 2：残る
  - 待っていた文：巻き戻す
{{< /note-panels >}}

上記の図の下側の Oracle Database では、通知を受けたトランザクションを通常は明示的に巻き戻し、待ってから巻き戻された文だけを再試行することもできます。

アプリケーション側では、デッドロックのエラーを受けたトランザクションを明示的に巻き戻しておけば、DBMS ごとに巻き戻す範囲が違っても影響を受けません。

---

### ロックの取得順序の統一

冒頭の例で循環待ちを作っているのは、2 本が同じ 2 行を逆の順で取得していることです。代表的な防ぎ方は、ロックを取る順序を全ての経路で揃えることです。以下は、冒頭の 2 本が同じ順でロックを取る場合です。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
sequenceDiagram
    participant A as 送金 A
    participant R1 as 口座 1 の行
    participant R2 as 口座 2 の行
    participant B as 送金 B
    A->>R1: ロックを取る
    B->>R1: A の解放を待つ
    A->>R2: ロックを取る
    Note over A,R2: A が終わり<br/>ロックを解放
    B->>R1: ロックを取る
    B->>R2: ロックを取る
```

上記の図の送金 B は待ちますが、待つ先を辿っても出発点に戻らないので循環待ちになりません。

行へのロックには種類があります。[PostgreSQL](https://www.postgresql.org/docs/current/explicit-locking.html) の行レベルロックは、`FOR KEY SHARE`、`FOR SHARE`、`FOR NO KEY UPDATE`、`FOR UPDATE` の 4 つのモードを持ちます。同じ行に複数のトランザクションが同時にロックを持てるかどうかは、モードの組み合わせで決まります。共存できる組み合わせがある一方、`FOR UPDATE` は他の行レベルロックと競合します。

もう 1 つの条件は、トランザクションの中で 1 つのオブジェクトに最初に取るロックが、そのオブジェクトに必要になる最も制限の強いモードであることです。

以下は、`FOR SHARE` のような競合しにくいモードで同じ行を押さえた 2 本が、更新のために両方とも `FOR UPDATE` に上げようとする場合です。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
sequenceDiagram
    participant A as 送金 A
    participant R as 口座 1 の行
    participant B as 送金 B
    A->>R: 競合しにくい<br/>モードで取る
    B->>R: 競合しにくい<br/>モードで取る
    A->>R: FOR UPDATE に上げたい<br/>B が離すのを待つ
    B->>R: FOR UPDATE に上げたい<br/>A が離すのを待つ
    Note over A,B: 順序が揃っていても<br/>循環待ちになる
```

後で更新する行は、最初の読み取りから `SELECT ... FOR UPDATE` のように必要なモードで取っておくと、この引き上げ待ちを避けられます。

順序を揃える方法として、更新対象を主キーの昇順に並べ替えてから適用する形があります。プレースホルダは PostgreSQL の記法です。

```go
type accountUpdate struct {
	AccountID int64
	Delta     int64
}

// applyUpdates は、口座 ID の昇順で残高を更新する。
// accounts の対象行について、どの呼び出しも同じ順序でロックを取る。
func applyUpdates(ctx context.Context, db *sql.DB, updates []accountUpdate) error {
	sorted := slices.Clone(updates)
	slices.SortFunc(sorted, func(a, b accountUpdate) int {
		return cmp.Compare(a.AccountID, b.AccountID)
	})

	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		return err
	}
	defer func() { _ = tx.Rollback() }()

	for _, u := range sorted {
		res, err := tx.ExecContext(ctx,
			`UPDATE accounts SET balance = balance + $1 WHERE id = $2`,
			u.Delta, u.AccountID)
		if err != nil {
			return err
		}
		n, err := res.RowsAffected()
		if err != nil {
			return err
		}
		if n != 1 {
			return fmt.Errorf("account %d: updated %d rows, want 1", u.AccountID, n)
		}
	}
	return tx.Commit()
}
```

更新した行が 1 件でない場合にエラーを返しているのは、口座が見付からない更新を黙って飛ばすと、片側だけ適用された送金が確定するからです。この関数は 1 回の試行しか行いません。デッドロックで中止された時は、呼び出し側が関数ごと実行し直します。

途中の `UPDATE` で失敗した場合は `defer` に置いた `tx.Rollback()` が走り、それまでに適用した更新も残りません。

並べ替えのキーが主キーである必要はありません。条件は、全ての対象に対して決定的な順序を作れること、その順序に使う値がロック取得中に変わらないこと、全ての経路が同じ規則で並べることです。同順位があり得るキーを使うなら、`priority ASC, id ASC` のように、主キーのような一意な値を最後の比較キーに加えます。

---

### 順序の統一が成り立つ条件

取得順序の統一を成り立たせるには、少なくとも次の 4 つが必要です。

- 競合するロックについて、取得順序を一貫させている。`UPDATE` が暗黙に取るロックも同じ対象に含める
- 1 つの対象に後からより競合の強いモードが必要になるなら、可能な場合は最初からそのモードで取る
- 競合するロックを取り始める前に、対象と取得順序を決められる
- 同じロック対象を共有する全ての経路が、同じ規則を守っている

3 つ目は、競合するロックを取り始める前に順序が定まっていれば足り、トランザクションを始める前に対象が分かっている必要はありません。`WHERE status = 'pending'` のように 1 文で複数行を更新する形が難しいのは、どの順序で対象行に到達するかが、DBMS の選ぶ実行の手順（実行計画。索引を使うか表を順に読むかなど）で変わるからです。`SELECT ... ORDER BY id FOR UPDATE` で対象と順序を確定してから更新するか、決められない処理と割り切って再試行に任せます。

抜けやすいのは 4 つ目です。1 箇所でも別の順序でロックを取る経路が残っていると、その経路と他の経路の間で循環待ちができます。同じ表の中だけの話ではありません。`accounts` から `transfers` の順で触る経路と、`transfers` から `accounts` の順で触る経路があれば、それだけで循環します。バッチ処理や管理画面のように、通常の経路と別に書かれたコードが該当します。

---

### 順序を揃えても残る原因

アプリケーションが取得順序を直接決めやすいのは、自分で明示的にロックする行です。DBMS はそれ以外にも、外部キーの検査や索引の走査に伴ってロックを取るため、その全てを SQL の並べ替えだけで制御できるわけではありません。

1 つのトランザクションが取るロックを分けると、以下のようになります。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
flowchart LR
    T["トランザクションが取るロック"] --> A
    T --> B
    subgraph A["順序を直接決めやすい"]
        R["明示的にロックする行"]
    end
    subgraph B["DBMS の処理に伴って取られる"]
        F["外部キーの検査が触る行"]
        G["索引レコードの隙間<br/>InnoDB の場合"]
    end
    classDef default fill:#eaf1f5,stroke:#9cabb5,color:#28343b;
```

上記の図の下側は、書いた SQL の並べ替えからは順序を制御しにくい部分です。外部キーの検査は、子側の `INSERT` と `UPDATE` に加えて、親側の `DELETE` と親キーの `UPDATE` でも走ります。[MySQL のドキュメント](https://dev.mysql.com/doc/refman/8.4/en/innodb-locks-set.html)によれば、制約の検査が必要な操作は、検査のために見た行に共有のレコードロック（読み取りどうしは共存し、更新とは競合する行のロック）を設定します。

親を消す経路と子を挿入する経路は、SQL の上では別の表を触っています。しかし [Foreign Key](../foreign-key/) を張っていると、ロックの上では同じ行で交わるので、順序を決める時に見落としやすくなります。

同じ処理どうしでも交わります。PostgreSQL 17.10 で、口座 `accounts` を参照する外部キーを持つ `transfers` に 1 行を挿入し、その 1 秒後に口座 1 を `SELECT ... FOR UPDATE` で押さえる処理を 2 本用意し、0.5 秒ずらして走らせました。2 本のロックが重なるのは口座 1 の行だけで、順序も同じです。

```text
-- 中止された側
ERROR:  deadlock detected
CONTEXT:  while locking tuple (0,1) in relation "accounts"

-- 続行した側
 balance
---------
   10000
```

`INSERT` は外部キーの検査で、親である口座 1 の行に `FOR KEY SHARE` を取ります。2 本がこのロックを共有したまま `FOR UPDATE` に上げようとしたので、前に見た引き上げの図と同じ循環になりました。`FOR UPDATE` を書いていても、その前の `INSERT` が先に弱いモードを取っています。口座を `FOR UPDATE` で押さえてから `INSERT` する順にするか、通常の `UPDATE` で口座を更新すると（取るモードが `FOR KEY SHARE` と競合しない `FOR NO KEY UPDATE` になる）、デッドロックは起きませんでした。

索引に並んだキーとキーの間（隙間）へのロックは MySQL の InnoDB の機構で、PostgreSQL には同じ仕組みがありません。隙間にもロックを掛けるのは、条件に合う行が後から挿入されるのを防ぐためです。InnoDB の既定である REPEATABLE READ では、索引を走査する `UPDATE` や `SELECT ... FOR UPDATE` に、索引レコードとその手前の隙間をまとめた [next-key lock](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking.html) が使われます。以下は、その範囲です。キーの値は説明用です。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
flowchart LR
    K1["キー 10"] --- G1
    subgraph NK["next-key lock"]
        direction LR
        G1["隙間<br/>10 と 20 の間"] --- K2["キー 20"]
    end
    K2 --- G2["隙間<br/>20 と 30 の間"] --- K3["キー 30"]
    classDef default fill:#eaf1f5,stroke:#9cabb5,color:#28343b;
```

上記の図の範囲は常に隙間を含むわけではなく、一意索引を一意に定まる条件で検索した場合は、索引レコードだけのロックになります。[分離レベル](../transaction-isolation/)でも変わり、[分離レベルのページ](https://dev.mysql.com/doc/refman/8.4/en/innodb-transaction-isolation-levels.html)によれば、READ COMMITTED では、通常の検索や走査に対する隙間へのロックが大きく減ります。

そのため、順序を揃えてもデッドロックが残る前提で設計します。順序の統一は発生を減らす手段で、無くす手段ではありません。

---

### 再試行まで含めた設計

順序をどれだけ揃えても、中止されたトランザクションを再試行する処理は省けません。再試行を組む時に決めることは 3 つあります。

- 再試行して良い中止かどうかの判別
- 再試行する単位
- 上限の回数と、試行の間隔

判別には、DBMS が返すエラーの識別子を使います。やり直すと通ることがあるのは、デッドロックによる中止と直列化の失敗（SERIALIZABLE などの分離レベルで、同時に走った結果を順に並べ直せないと DBMS が判断した中止）です。PostgreSQL は SQLSTATE の `40P01` をデッドロックに、`40001` を直列化の失敗に割り当てています。MySQL はサーバーのエラー番号 `1213` をデッドロックに割り当てており、その SQLSTATE は `40001` です。SQLSTATE だけで横断的に判定すると、2 つの DBMS で別の事象が同じ値に見えます。

文法の誤りや、入力値に原因がある `NOT NULL` 違反・`CHECK` 違反のような失敗は、同じ入力をそのまま再試行しても解消しません。中止の理由を見ずに一律で再試行すると、こうした失敗を上限まで繰り返します。

`40P01` を受けたトランザクションは、その途中から処理を続けられません。Go の `database/sql` であれば、先の `applyUpdates` のようにトランザクション 1 本を関数に収めておくと、以下のように関数を呼び直すだけで、トランザクション 1 本を丸ごとやり直せます。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
sequenceDiagram
    participant C as 呼び出し側
    participant F as applyUpdates
    participant D as DB
    C->>F: 1 回目
    F->>D: トランザクション
    D-->>F: 40P01 で中止
    F-->>C: エラー
    Note over C: ランダムなずれを<br/>入れて待つ
    C->>F: 2 回目
    F->>D: 新しいトランザクションを<br/>先頭から
```

上記の図の 2 回目は先頭からやり直すので、1 回目に読んだ値も読み直します。待ち時間にずれを入れるのは、高負荷の時ほど多くの処理が同時に失敗しやすく、全てが同じ長さだけ待つと揃って再試行して、また同じロック競合を起こすからです。上限まで試して成功しなかった処理は、業務としての失敗として扱い、利用者にエラーを返すか、後で処理するためのキューに移します。

対処ごとに効く範囲と残る問題を整理すると、以下の通りです。

| 対処 | 効く範囲 | 残る問題 |
| --- | --- | --- |
| 取得順序を揃える | 明示的に順序を決められるロック | 外部キーの検査や隙間など、SQL から順序を制御しにくいロックまでは防ぎ切れない |
| 最初から必要なモードで取る | 同じ行でのモードの引き上げ | 競合しにくいモードで足りる読み取りまで待たせる |
| トランザクションを短くする | ロックを持つ時間と、競合が重なる確率 | 逆順で取得する経路が残っていれば、原因自体は消えない |
| 再試行する | 中止された全てのデッドロック | 応答時間が伸びる。上限に達した時の扱いを決める |

再試行はトランザクションを丸ごとやり直す処理なので、[Transaction Scope](../transaction-scope/) で扱った範囲の決め方がそのまま当てはまります。外部 API の呼び出しが範囲の中にあると、再試行のたびに要求が飛びます。範囲を DB の更新だけに絞っておけば、再試行の副作用は DB の中に閉じます。
