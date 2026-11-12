---
title: "MVCC と VACUUM - 更新で残る古い版と、それを消せなくする長いトランザクション"
date: 2026-11-11
draft: false
series: ["技術ノート", "Database Systems"]
tags: ["database-systems", "transaction", "mvcc", "vacuum"]
weight: 20
wrapTables: true
topics: ["Transaction / Concurrency Control"]
---

MVCC（Multiversion Concurrency Control）は、レコードを更新しても古い内容をすぐには消さず、複数の版を並べて持つことで、読み手と書き手が互いを待たずに済むようにする仕組みです。[PostgreSQL](https://www.postgresql.org/) では、UPDATE は古い版の隣に新しい版を足し、DELETE は版に「消した」という印を付けるだけです。誰からも見えなくなった古い版を後で回収するのが、VACUUM という処理です。

例えば、件数は 10 万件のまま変わらないのに、表のファイルが毎日大きくなっていく DB（データベース）があるとします。調べると VACUUM は動いているのに古い版が 1 件も消えておらず、原因は誰かが開いたまま放置したトランザクションだった、という場面です。以下は、手元の PostgreSQL 17 で、この場面を小さく再現した結果です。10 万件の表の全件を 10 回更新し、表の大きさを記録しました（比べるために、表ごとに自動の VACUUM を止めています）。

{{< figure src="images/mvcc-vacuum_size.webp" alt="横軸は全件を更新した回数で 0 から 10。VACUUM しない表は 1 回ごとに約 13.5 MB ずつ増えて 148 MB になる。毎回 VACUUM する表は 1 回目に 27 MB になった後、増えない。毎回 VACUUM しても、古いスナップショットを持つ接続がある表は、VACUUM しない表と同じ線で 148 MB まで増える" caption="10 万件の全件を 10 回更新した時の表の大きさ" align="center" >}}

スナップショットは、ある時点までに確定（COMMIT）したデータだけが見える、読み取りの視点です。毎回 VACUUM する表は 27 MB で止まりました。一方、毎回 VACUUM しても、別の接続が古いスナップショットを持ったままの表は、VACUUM しない表と同じ 148 MB まで増えました。件数はどの表も 10 万件です。

<br>

本記事では、PostgreSQL 17 で手元に作った表を使って、MVCC が版をどう持ち、VACUUM がそれをいつ消せるのかを説明します。扱う疑問は次の通りです。

- UPDATE と DELETE は、表のブロックの中で何をしているのか。
- VACUUM は何を消し、なぜ表のファイルは小さくならないのか。
- 開いたままのトランザクションは、なぜ VACUUM を止めるのか。
- 自動の VACUUM（autovacuum）は、いつ動くのか。
- VACUUM が追いつかないと、最後に何が起きるのか。

MVCC が読み手に見せる版を選ぶ規則（分離レベル）は、[Transaction Isolation](/notes/database-systems/transaction-isolation/#読み取りの可視性) と [Snapshot Isolation](/notes/database-systems/snapshot-isolation/) のノートで扱っているので、本記事では繰り返しません。MySQL（InnoDB）のように、古い版を表の外（undo log）に置く実装との比較にも深入りしません。

---

### UPDATE は版を足す

PostgreSQL の表は、8 KB のブロックを並べたファイルです。1 つのブロックに、レコードの版（tuple）がいくつも入ります。各版には、その版を作ったトランザクションの ID（`xmin`）と、その版を消したトランザクションの ID（`xmax`、まだ消されていなければ 0）が付いています。トランザクション ID は、書き込みをするトランザクションに 1 つずつ振られる通し番号です。

2 件の口座（id 1 の残高 100、id 2 の残高 500）を入れた表で、id 1 の残高を 200 に更新しました。psql で 1 文ずつ実行すると、文ごとに別のトランザクションとして確定する（自動コミット）ので、INSERT が 741、UPDATE が 742、後の DELETE が 743 になっています。拡張機能 [pageinspect](https://www.postgresql.org/docs/17/pageinspect.html) の `heap_page_items()` は、ブロックの中の版を、見えるかどうかに関係なく全て並べます。

```text
SELECT lp, t_xmin, t_xmax, t_ctid FROM heap_page_items(get_raw_page('acct', 0));
 lp | t_xmin | t_xmax | t_ctid 
----+--------+--------+--------
  1 |    741 |    742 | (0,3)
  2 |    741 |      0 | (0,2)
  3 |    742 |      0 | (0,3)
```

`lp` はブロックの中の版の番号、`t_ctid` は次の版の位置（ブロック 0 の 3 番、のように読みます）で、自分自身を指していれば最新の版です。普通の `SELECT` では id 1 は 1 件しか見えませんが、ブロックの中には 1 番（残高 100）と 3 番（残高 200）の 2 つの版があります。以下は、この 2 つの版と、それを読む側の関係を描いた図です。

{{< figure src="images/mvcc-vacuum_versions.webp" alt="表のブロック 0 に、1 番の版（id 1、残高 100、xmin 741、xmax 742）と、3 番の版（id 1、残高 200、xmin 742、xmax 0）が並び、1 番から 3 番へ矢印が向く。742 の確定より前のスナップショットは 1 番を、後のスナップショットは 3 番を読む" caption="UPDATE の後のブロックの中（id 2 の版は省略）" align="center" >}}

UPDATE を実行したトランザクション 742 は、1 番の中身を書き換えず、`xmax` に自分の ID を書いて、3 番を足しました。742 が確定する前に取ったスナップショットで読むトランザクションは 1 番を、確定した後に取ったスナップショットで読むトランザクションは 3 番を読みます。書き手が古い版を残しておくので、読み手は書き手を待たずに読めます。

続けて id 1 を DELETE すると、3 番の `xmax` に 743 が入るだけで、版はブロックに残りました。

```text
 lp | t_xmin | t_xmax | t_ctid 
----+--------+--------+--------
  1 |    741 |    742 | (0,3)
  2 |    741 |      0 | (0,2)
  3 |    742 |    743 | (0,3)
```

---

### VACUUM が消すもの

`xmax` が付いて、その削除が確定し、今後どのスナップショットからも見えなくなった版を、PostgreSQL の[ドキュメント](https://www.postgresql.org/docs/17/routine-vacuuming.html#VACUUM-FOR-SPACE-RECOVERY)では dead tuple（死んだ版）と呼びます。「どのスナップショットからも見えない」という条件は、後の節で効いてきます。上の DELETE の後で `VACUUM acct` を実行すると、ブロックの中は次のようになりました。

```text
SELECT lp, lp_flags, t_xmin, t_xmax, t_ctid FROM heap_page_items(get_raw_page('acct', 0));
 lp | lp_flags | t_xmin | t_xmax | t_ctid 
----+----------+--------+--------+--------
  1 |        0 |        |        | 
  2 |        1 |    741 |      0 | (0,2)
```

1 番は中身が消えて空き（`lp_flags` が 0。1 は使用中）になり、末尾の 3 番は番号ごと無くなりました（末尾に並んだ空きの番号は詰められます）。生きている id 2 の版だけが残っています。VACUUM は、死んだ版を消し、その版を指す索引の項目も消して、空いた場所を次の INSERT や UPDATE で使えるようにします。

<br>

#### 空いた場所は使い回すが、ファイルは縮まない

冒頭のグラフで、毎回 VACUUM した表が 1 回目に 13.5 MB から 27 MB に増え、そこで止まったのは、このためです。1 回目の UPDATE で、全件の新しい版が足されて 2 倍になります。その後の VACUUM で古い版の場所が空き、2 回目の UPDATE はその空きに新しい版を書きます。古い版と新しい版の 2 組分の場所があれば、それ以上は増えません。

VACUUM は空いた場所を使い回せるようにするだけで、ファイルを小さくはしません（末尾のブロックが丸ごと空き、表のロックがすぐ取れる時は、その分を切り詰めます）。VACUUM しなかった 148 MB の表で確認すると、次の通りでした。

```text
VACUUM しなかった表        148 MB
VACUUM の後               148 MB
もう 1 回、全件を UPDATE    148 MB（空いた場所を使ったので増えない）
VACUUM FULL の後           13 MB
```

[VACUUM FULL](https://www.postgresql.org/docs/17/sql-vacuum.html) は、生きている版だけを新しいファイルに書き写して表を作り直すので、ファイルが元の大きさに戻ります。その代わり、作り直す間は表に最も強いロック（ACCESS EXCLUSIVE）を取り、読み出しも止めます。動いているサービスの表に気軽には使えません。

---

### 古いスナップショットが VACUUM を止める

VACUUM が消せるのは、どのトランザクションからも見えなくなった版だけです。冒頭のグラフの赤の破線では、別の接続で次のトランザクションを開き、表を 1 回読んだまま待たせておきました（実験では、ロックの解放を待たせることで開いたままにしています）。

```sql
BEGIN ISOLATION LEVEL REPEATABLE READ;
SELECT count(*) FROM items_hold;
-- ここで止まったまま
```

REPEATABLE READ では、トランザクションの最初の問い合わせで取ったスナップショットを最後まで使います。このトランザクションは、いつ同じ表をもう一度読むか分かりません。読んだ時には、スナップショットを取った時点の版を返す必要があります。そのため、その時点より後に消された版は、どれも消せません。

この接続のスナップショットは、トランザクション ID 797 より前に確定したものだけが見える状態でした。接続ごとのこの境目は、`pg_stat_activity` の `backend_xmin` で見られ、ここでは 797 でした。以下は、トランザクション ID の軸の上で、どこまでの版を消せるかを描いた図です。

{{< figure src="images/mvcc-vacuum_horizon.webp" alt="トランザクション ID の軸の上に、古いスナップショットの境目 797（backend_xmin と removable cutoff）と、今の ID（817 前後）がある。797 より前に消された版は VACUUM で消せる。797 と今の間に並ぶ 10 回の UPDATE で消された、合わせて 100 万の版は消せない" caption="古いスナップショットより後に消された版は消せない" align="center" >}}

10 回の UPDATE はどれも 797 より後なので、10 回分の古い版は全て消せません。この状態で `VACUUM (VERBOSE)` を実行すると、次の出力になりました。

```text
VACUUM (VERBOSE) items_hold;
INFO:  finished vacuuming "postgres.public.items_hold": index scans: 0
pages: 0 removed, 18966 remain, 18966 scanned (100.00% of total)
tuples: 0 removed, 1100000 remain, 1000000 are dead but not yet removable
removable cutoff: 797, which was 20 XIDs old when operation ended
```

`tuples:` の行は、110 万の版（生きている 10 万と死んだ 100 万）のうち、死んだ 100 万を 1 件も消していない（`0 removed`、`dead but not yet removable`）ことを示します。`removable cutoff: 797` が、消せる版の境目で、`backend_xmin` と同じ値です。VACUUM は表の全 18,966 ブロック（`pages:` の行）を読んだうえで、何も消さずに終わりました。

<br>

待たせていたトランザクションを確定させてから、もう一度 VACUUM を実行すると、次の通りでした。

```text
tuples: 1000000 removed, 100000 remain, 0 are dead but not yet removable
removable cutoff: 828, which was 0 XIDs old when operation ended
```

100 万の版が消え、生きている 10 万件だけが残りました。古いスナップショットは、その表だけでなく、同じ DB の全ての表の VACUUM を止めます。実験でも、毎回 VACUUM の表の計測を、待たせるトランザクションを開く前に済ませる必要がありました。

<br>

#### READ COMMITTED の場合

実験は REPEATABLE READ でしたが、PostgreSQL の既定の分離レベルは READ COMMITTED で、文ごとにスナップショットを取り直し、文が終わると手放します。そのため、読むだけで、カーソルも開いていないトランザクションは、`BEGIN` したまま止まっていても、文を実行していない間は境目を止めません。ただし、1 つの文が何時間も掛かれば、その間は止めます。また、書き込みをしたトランザクションは、自分のトランザクション ID を確定まで持ち続けるので、止まっている間も境目を止めます。

<br>

#### 古いスナップショットを作るもの

実際のサービスで古いスナップショットを作りやすいのは、次のようなものです。

- `BEGIN` したまま、アプリの処理や外部 API の呼び出しを待つトランザクション（`idle in transaction` の状態）のうち、書き込みをした後のもの、カーソルを開いたままのもの、REPEATABLE READ 以上のもの
- 何時間も掛かる集計や、バックアップのための長い読み出し
- 読み取り用の複製（レプリカ）で長い問い合わせを流し、その境目を書き込みを受ける側（プライマリ）に伝える設定（[hot_standby_feedback](https://www.postgresql.org/docs/17/runtime-config-replication.html#GUC-HOT-STANDBY-FEEDBACK)）。プライマリが古い版を消すと、レプリカの問い合わせが読む版が無くなるので、この設定ではプライマリが消すのを待つ
- hot_standby_feedback を使っていたレプリカが止まったまま残った、物理レプリケーションのスロット（複製先がどこまで受け取ったかをプライマリが覚えておく仕組みで、受け取った境目も覚え続ける）。論理レプリケーションのスロットが止めるのは、システムカタログの回収だけ

1 つ目は、トランザクションの範囲を広げすぎた時に起きます（[Transaction Scope](/notes/database-systems/transaction-scope/) のノート）。PostgreSQL には、`idle in transaction` のまま一定の時間が経った接続を切る [idle_in_transaction_session_timeout](https://www.postgresql.org/docs/17/runtime-config-client.html#GUC-IDLE-IN-TRANSACTION-SESSION-TIMEOUT) がありますが、既定は 0（切らない）です。書き込みをしたまま開いたトランザクションは、[Transactional Outbox](/notes/distributed-systems/transactional-outbox/) の行をトランザクション ID で読む relay の送信も止めます。

---

### autovacuum が動く時

VACUUM を人が実行することはほとんどありません。PostgreSQL には、表ごとに死んだ版の数を数え、一定を超えると VACUUM を実行する [autovacuum](https://www.postgresql.org/docs/17/routine-vacuuming.html#AUTOVACUUM) が既定で動いています（冒頭で触れた通り、本記事の実験では表ごとに止めています）。

既定では、死んだ版の数が「50 ＋ 表の件数の 20%」を超えた表が対象になります（`autovacuum_vacuum_threshold` と `autovacuum_vacuum_scale_factor`）。10 万件の表なら 20,050 件です。1 億件の表では 2,000 万件になるので、大きな表ほど、死んだ版が大量に溜まってから動きます。大きな表だけ、この割合を表ごとに小さくする設定がよく使われます。

autovacuum が動いていても、上の節の古いスナップショットがあれば消せません。死んだ版の数が減らないので、autovacuum は同じ表を何度も読み直し、何も消せずに終わります。

---

### トランザクション ID の周回

VACUUM には、もう 1 つ大事な仕事があります。トランザクション ID は 32 ビットの数で、約 40 億で一周します。PostgreSQL は、ある ID から見て約 20 億個前までを過去、20 億個先までを未来として比べます。そのため、版の `xmin` がそのまま残っていると、約 20 億のトランザクションの後、その版は突然「未来に作られた版」になり、見えなくなります。

これを防ぐため、VACUUM は十分に古い版に「凍結した（frozen）」印を付け、どのトランザクションからも過去として見えるようにします（[ドキュメント](https://www.postgresql.org/docs/17/routine-vacuuming.html#VACUUM-FOR-WRAPAROUND)）。表の中で最も古い凍結していない ID が 2 億トランザクション分（`autovacuum_freeze_max_age` の既定）古くなると、autovacuum を止めていても、凍結のための VACUUM が強制的に走ります。

以下は、32 ビットの ID を円で描き、凍結していない古い版が見えなくなる仕組みを示した図です。

{{< figure src="images/mvcc-vacuum_wrap.webp" alt="トランザクション ID を約 40 億で一周する円で描く。今の ID から見て、反時計回りの半周（約 20 億）が過去、時計回りの半周が未来。過去の端の近くにある古い版の xmin は、今の ID がさらに進むと未来の側に入り、見えなくなる。凍結した版は xmin を比べずに常に過去として扱う" caption="32 ビットのトランザクション ID の円" align="center" >}}

周回の手前で、PostgreSQL は段階を踏んで知らせます。残りが 4,000 万トランザクションを切るとログに警告を出し、それでも凍結が追いつかず、残り 300 万トランザクションを切ると、PostgreSQL は新しいトランザクション ID の割り当てを拒否します。書き込みが全て止まり、次のエラーになります。

```text
ERROR:  database is not accepting commands that assign new transaction IDs to avoid wraparound data loss in database "mydb"
```

<br>

#### 実際に止まった例

エラー監視のサービス [Sentry](https://blog.sentry.io/transaction-id-wraparound-in-postgres/) は、2015 年 7 月 20 日、米国の業務時間のほとんどの間止まりました。原因は、この周回を防ぐための VACUUM が追いつかず、書き込みが止まったことでした。

メール配信の Mandrill（Mailchimp のサービス）も、[2019 年 2 月 4 日から 5 日にかけて](https://mailchimp.com/what-we-learned-from-the-recent-mandrill-outage/)、同じ周回の問題で送信が滞りました。Mailchimp の報告によると、ピーク時の負荷でトランザクション ID が上限の半分ほどまで上がることには 2018 年 11 月の時点で気づいていたものの、差し迫った問題ではないと判断していました。

どちらも、普段は見えない VACUUM の遅れが、ある日まとめて書き込みの停止として表に出た例です。手元の DB では、`SELECT datname, age(datfrozenxid) FROM pg_database` で、各 DB の最も古い凍結していない ID がどれだけ古いかを確認できます。

---

### 利点

- 読み手は書き手を待たず、書き手は読み手を待たない
- 長い読み出しの途中でも、始めた時点の一貫した内容を読める
- PostgreSQL では古い版を表の中に残しておくので、更新を取り消す（ROLLBACK）時に元の内容を書き戻す必要が無い

### 欠点

PostgreSQL の MVCC は、古い版を表の中に残すことで、読み手と書き手が互いを待たない仕組みにしています。その代わりに、次の制約があります。

- 更新と削除のたびに死んだ版が残り、VACUUM で回収するまで表と索引が膨らむ
- VACUUM は空いた場所を使い回すだけで、ファイルを小さくするには VACUUM FULL などで表を作り直す必要がある
- 書き込みをしたまま、または古いスナップショットを持ったまま開いているトランザクションが 1 つあるだけで、同じ DB の全ての表の回収が止まる
- トランザクション ID が 32 ビットなので、凍結の VACUUM が追いつかないと書き込みが止まる

### VACUUM の問題が小さくなりやすいケース

- 追記だけで、更新と削除がほとんど無い表（ログや履歴）
- 古いデータを `DELETE` ではなく、パーティションごと捨てる表（[Partitioning](/notes/database-systems/partitioning/) のノート）
- トランザクションが全て短く、`idle in transaction` の接続を監視・切断している DB

実験の SQL・実行用のスクリプト・出力の全体は [lab/](https://github.com/nao1215/debimate/tree/main/content/notes/database-systems/mvcc-vacuum/lab) にあります。
