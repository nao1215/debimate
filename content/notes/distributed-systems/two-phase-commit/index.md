---
title: "2PC - 2 段階でコミットする分散トランザクションと残るロック"
date: 2026-08-10
draft: false
series: ["技術ノート", "Distributed Systems"]
tags: ["distributed-systems", "transaction"]
weight: 6
wrapTables: true
topics: ["Distributed Transactions"]
crossTopics:
  database-systems: ["Transaction / Concurrency Control"]
---

PostgreSQL で、ポイントの残高を 1 行更新するだけの UPDATE が返ってこなくなりました。ロックを待っているはずなのに、`pg_stat_activity` にはトランザクションを開いたままの接続が 1 つもありません。待たせている相手を `pg_blocking_pids()` で引くとプロセス ID は 0 で、その相手を `pg_terminate_backend()` で切ることもできません。DB を再起動しても、UPDATE はまた待たされます。

{{< figure src="images/two-phase-commit_stuck.webp" alt="動く図。0.2 秒でコーディネータが注文 DB にだけ COMMIT PREPARED を送って止まる。注文 DB はコミット済みになり、ポイント DB は準備済みのまま行のロックを持ち続ける。0.6 秒に始めた別アプリの UPDATE は 10.7 秒に lock_timeout で失敗する。10.7 秒から 11.4 秒の再起動の後もポイント DB は準備済みのままで、再開した UPDATE はまた待つ。15.5 秒に運用者がポイント DB で COMMIT PREPARED を実行すると、UPDATE はすぐに通る" caption="コーディネータが止まった後のポイント DB と、待たされる UPDATE（実測した時刻を 2 倍速で再生）" align="center" >}}

2 相コミット（two-phase commit、2PC）は、複数の DB にまたがる更新で、全部コミットするか全部中止するかに揃える手順です。取りまとめ役をコーディネータ（coordinator）、更新を受け持つ各 DB を参加者（participant）と呼びます。参加者は、コミットの前に準備を済ませ、準備済みのトランザクションとして決定を待ちます。

図は、手元の PostgreSQL 17 で、注文 DB とポイント DB にまたがる 2PC の途中で、コーディネータを止めた時の記録です。行のロックを持っていたのは接続ではなく、ポイント DB に残った準備済みのトランザクションでした。それは再起動しても消えず、運用者が手でコミットするまで、別アプリの UPDATE を止め続けました。

<br>

アプリのコードで直接書くことは少なく、Java の [Jakarta Transactions](https://jakarta.ee/specifications/transactions/)（旧 JTA）のトランザクションマネージャや、MySQL の XA トランザクションを使う所で出会います。

<br>

本記事では、2PC をこれから使う人と、準備済みのトランザクションに既存のシステムで出会った人に向けて、次の疑問に答えます。

- 誰もロックを持っていないように見えるのに、UPDATE が待つのはなぜか。
- 2PC は、なぜコミットを 2 回に分けるのか。
- 準備を終えた参加者は、なぜ自分でコミットも中止も選べないのか。
- 残ったトランザクションは、何を見てどちらに決めるのか。
- 放っておくと、ロックの他に何が起きるのか。
- PostgreSQL と MySQL で、扱いはどう違うのか。

---

### 待たせている相手を探す

実験には、Docker で動かした PostgreSQL 17.11 を 2 台と、MySQL 8.4.11 を使いました。

冒頭の図で止めたコーディネータは、次の SQL を順に送るシェルスクリプトです。注文 DB に注文 42 を足し、ポイント DB で利用者 1 の残高から 300 を引きます。`PREPARE TRANSACTION` が 2PC の準備で、`COMMIT PREPARED` がコミットの決定です。`'order-42'` は、この分散トランザクションに付けた識別子で、2 つの DB で同じ値を使います。

```sql
-- 注文 DB
BEGIN;
INSERT INTO orders VALUES (42, 1, 300);
PREPARE TRANSACTION 'order-42';

-- ポイント DB
BEGIN;
UPDATE points SET balance = balance - 300 WHERE user_id = 1;
PREPARE TRANSACTION 'order-42';

-- 注文 DB にだけ決定を送り、ここでコーディネータが止まる
COMMIT PREPARED 'order-42';
```

この後、別アプリがポイント DB で、利用者 1 の残高に 50 を足す UPDATE を送ると、待たされました。この UPDATE には、ロックを待つ上限として `lock_timeout` を 10 秒に設定しています。待っている間に、冒頭で挙げた順に原因を探していきます。

最初に疑うのは、`BEGIN` したままコミットを忘れた接続です。しかし、`pg_stat_activity` でトランザクションを開いている接続を数えると、0 でした。普通のトランザクションは接続が続く間だけ残り、接続が切れれば中止され、ロックも外れます。実験でも、`BEGIN` と `UPDATE` の後に psql を終わらせると、別の接続から送った UPDATE は 0.1 秒以内に通りました。

次に、待っている UPDATE から相手を引きました。

```sql
SELECT state, wait_event_type, wait_event, pg_blocking_pids(pid)
FROM pg_stat_activity WHERE query LIKE 'UPDATE points%';

SELECT locktype, mode, pid, virtualtransaction
FROM pg_locks WHERE locktype = 'transactionid';
```

```text
active|Lock|transactionid|{0}
transactionid|ExclusiveLock|(null)|5/2
```

1 行目は待っている UPDATE で、行を書き換えたトランザクションの終わりを待っています（`transactionid` のロック）。最後の列は待たせている相手で、[pg_blocking_pids()](https://www.postgresql.org/docs/17/functions-info.html) は 0 を返しました。この 0 は、衝突するロックを持つ準備済みのトランザクションを表します。2 行目はそのロックを持つ側で、3 列目の pid が空です。

0 は接続ではないので、`pg_terminate_backend(0)` は「PID 0 is not a PostgreSQL backend process」（PID 0 は PostgreSQL のバックエンドプロセスではない）という警告を返すだけでした。

最後に、ポイント DB を再起動しました。再起動は 0.6 秒で終わりましたが、準備済みのトランザクションを並べる [pg_prepared_xacts](https://www.postgresql.org/docs/17/view-pg-prepared-xacts.html) には `order-42` が残り、再開した UPDATE はまた待ちました。

```text
[ 10.74] points の PostgreSQL を再起動
[ 11.35] 再起動が終わった
order-42|2026-11-17 03:18:44.604822+00
```

[PREPARE TRANSACTION](https://www.postgresql.org/docs/17/sql-prepare-transaction.html) を実行したトランザクションは、接続から切り離され、状態をディスクに書いて残ります。このトランザクションは、日本語に訳された PostgreSQL の文書ではプリペアドトランザクション（prepared transaction）と呼ばれています。接続を切っても再起動しても消えないのは、壊れた後でもコミットできることを約束するためで、2PC の準備はその約束をする操作です。

---

### コミットを 2 回に分ける理由

約束が必要なのは、参加者に順にコミットを送るだけでは揃わないからです。注文 DB をコミットした後で、ポイント DB が残高の制約違反やディスクの故障でコミットできなかったとします。注文 DB で済ませたコミットは取り消せないので、ポイントを引いていない注文が残ります。

2PC は、コミットの前にもう 1 回やり取りを挟みます。想定する故障はプロセスの停止と通信の途絶で、誤った値を返す [ビザンチン障害](/notes/distributed-systems/byzantine-fault-tolerance/) は扱いません。以下は、コーディネータと参加者 2 つが交わすやり取りを時間の順に左から右へ描いた図です。

{{< figure src="images/two-phase-commit_protocol.webp" alt="コーディネータが参加者 A と B に準備を頼み、A と B は作業中から準備済みに移って「はい」を返す。全員の「はい」が揃うと、コーディネータは「コミットと記録」を書いてから、A と B にコミットを送る。A と B は、はいを返してからコミットが届くまで準備済みの区間にいて、ロックを持って待ち、自分ではコミットも中止も選べない。コーディネータの線の上に、止まる所として ① 記録を書く前、② 記録の後で配る前、③ 配っている途中の 3 つの印がある" caption="2PC の 2 つのフェーズと、参加者が準備済みで待つ区間" align="center" >}}

<br>

#### 準備フェーズ

準備フェーズ（prepare phase）では、コーディネータが各参加者に準備を頼みます。参加者は、コミット以外の作業を全て済ませ、壊れた後でもコミットできるように変更と準備済みの印をディスクに書き、ロックを持ったまま「はい」と答えます。できなければ「いいえ」と答えます。準備の前なら、参加者は制約違反やタイムアウトを理由に、自分から中止できます。

書き込みと「はい」の順番には意味があります。書く前に「はい」と答えてから止まると、再起動した参加者は自分が何を約束したかを知りません。DB の中では、この書き込みに [WAL](/notes/distributed-systems/write-ahead-log/) が使われます。

<br>

#### コミットフェーズ

コミットフェーズ（commit phase）では、コーディネータが全員の答えを見て決めます。全員が「はい」ならコミット、1 つでも「いいえ」か返事が無ければ中止です。コミットに決めたら、その決定を自分のログに書いてから参加者に配ります。この記録を書いた時点で、トランザクション全体のコミットが決まります。

決定を受けた参加者は確認応答（ack）を返し、返ってこない参加者には、コーディネータが記録した決定を再送します。何度送っても同じ決定なので、再送で結果は変わりません。

この手順では、コミットのたびに 2 往復のやり取りと、参加者とコーディネータの両方でディスクへの書き込みが挟まります。参加者が増えれば、やり取りの数もその分だけ増えます。また、1 つでも準備に失敗すれば全体が中止になるので、参加者が増えるほどコミットまで進める見込みは下がります。

この手順は、Jim Gray 氏が 1978 年に出版した講義録「[Notes on Data Base Operating Systems](https://jimgray.azurewebsites.net/papers/dbos.pdf)」の 5.8.3.3 節でも説明されています。

<br>

#### 準備済みの参加者が自分で決められない理由

「はい」と答えた参加者は、図の赤い区間に入ります。この区間では、参加者は自分で中止できません。コーディネータが既にコミットに決め、他の参加者がコミットを終えているかもしれないからです。冒頭の実験では、注文 DB がそうでした。かといって、自分でコミットすることもできません。他の参加者が「いいえ」と答え、コーディネータが中止に決めたかもしれないからです。

この状態を in-doubt と呼びます。参加者どうしで聞き合えば分かりそうですが、PostgreSQL の参加者は他の参加者を知らず、話す相手はコーディネータだけです。

仮に聞き合えたとしても、全員が準備済みのままなら決められません。以下は、全員が準備済みのままコーディネータが止まった 2 つの場合を並べた図です。

{{< figure src="images/two-phase-commit_indoubt.webp" alt="左はコーディネータが記録を書く前に止まった場合で、ログには記録が無く、正しい決定は中止。右は記録を書いた直後に止まった場合で、ログにはコミットがあり、正しい決定はコミット。どちらも参加者から見えるものは、参加者 A と B が準備済みでロックを保持している状態で、同じ" caption="参加者から見ると同じなのに、正しい決定が逆になる 2 つの場合" align="center" >}}

参加者から見えるものは 2 つとも同じなのに、正しい決定は逆です。結局、決定を知っているコーディネータが戻るまで、ロックを持ったまま待つしかありません。Daniel Abadi 氏は、2019 年のブログ「[It's Time to Move on from Two Phase Commit](http://dbmsmusings.blogspot.com/2019/01/its-time-to-move-on-from-two-phase.html)」で、これを blocking problem と呼び、2PC の 2 つの大きな問題の 1 つに挙げています。

それでも、コミットと中止が食い違う結果にはなりません。Jim Gray 氏と Leslie Lamport 氏の論文「[Consensus on Transaction Commit](https://lamport.azurewebsites.net/video/consensus-on-transaction-commit.pdf)」の言葉では、2PC の停止で失われるのは、処理が先に進むという活性（liveness）で、食い違う結果を出さないという安全性（safety）は保たれます。

全員でコミットか中止かを決める手順は合意の一種で、1 台が応答しないだけで全体が待つ期間をどの手順も完全には無くせないことは、[FLP Impossibility](/notes/distributed-systems/flp-impossibility/) のノートで扱っています。

<br>

#### 待つ期間を短くする手順

待つ期間を短くする手順も提案されてきました。[Skeen 氏が 1981 年に示した](https://doi.org/10.1145/582318.582339) 3 相コミット（three-phase commit）は、準備とコミットの間に段を 1 つ足し、コーディネータが止まっても残りの参加者で結論を出せるようにします。ただし、メッセージの遅れに上限があることを前提にしていて、ネットワークが分断されると両側で別の判断をし得ます。

Gray 氏と Lamport 氏の論文が提案する Paxos Commit は、決定の記録をコーディネータ 1 台に置かず、複数台に複製します。複製には、[Leader and Followers](/notes/distributed-systems/leader-and-followers/) のノートで触れた合意アルゴリズムの Paxos を使います。

1 台が止まっても、残りの台から決定を復元できます。複数台の過半数で揃える点は [Quorum](/notes/distributed-systems/quorum/) に似ていますが、全体のコミットには、2PC と同じく全員の「はい」が必要です。

代わりに払うのは台数とやり取りです。F 台の停止に耐えるには 2F + 1 台の記録役を置き、その分だけメッセージが増えます。記録役を 1 台にすると、その 1 台がコーディネータに当たり、2PC と同じ形になります。

---

### 残ったトランザクションをどちらに決めるか

コーディネータが戻らない時は、人が決めることになります。正しい答えは、図の ①〜③ のどこでコーディネータが止まったかで決まります。

| 止まった所 | コーディネータのログ | 準備済みの参加者に送る決定 |
|---|---|---|
| ① 記録を書く前 | コミットの記録が無い | 中止（`ROLLBACK PREPARED`） |
| ② 記録の後、配る前 | コミット | コミット（`COMMIT PREPARED`） |
| ③ 配っている途中 | コミット | 残った参加者だけコミット |

① では、どの参加者にもコミットは届いていないので、中止しても食い違いは起きません。② と ③ では、コミットが決まっているので、残った参加者もコミットするしかありません。どちらの場合も、準備済みの参加者だけを見ても区別は付かず、見るべきなのはコーディネータのログか、決定が届いた他の参加者です。

冒頭の実験は ③ でした。注文 DB を見ると、`order-42` は準備済みの一覧に無く、注文 42 の行がありました。注文 DB はコミット済みなので、ポイント DB にも `COMMIT PREPARED` を送りました。待っていた UPDATE は 0.05 秒後に通り、残高は 1000 から 300 を引いて 50 を足した 750 になりました。

```text
-- 注文 DB: 準備済みの order-42 の数と、注文 42 の行の数
0
1
[ 15.54] orders ではコミット済みなので、points も COMMIT PREPARED
[ 15.59] 待っていた UPDATE が通った
1|750
```

この実験では、0.2 秒から 15.5 秒までの間、注文 42 は見えるのにポイントは減っていませんでした。2PC が揃えるのは最終的な結果で、2 つの DB の変更が見え始める時刻までは揃えません。

運用者がポイント DB だけを見て、`ROLLBACK PREPARED` を選んでいたらどうなるでしょうか。注文はあるのにポイントは引かれていない状態が残ります。2PC が防ぐはずだった食い違いが、人の手で生まれます。

コーディネータの決定を待たずに参加者だけで下す決定は、ヒューリスティック決定（heuristic decision）と呼ばれます。Jakarta Transactions には、その結果、一部がコミットされ一部がロールバックされたことを知らせる [HeuristicMixedException](https://jakarta.ee/specifications/transactions/2.0/apidocs/jakarta/transaction/HeuristicMixedException.html) という例外があります。

実験では、グローバルトランザクション識別子（gid）に注文の番号を入れたので、注文 DB を引くことができました。識別子からコーディネータとその中のトランザクションを辿れるかどうかで、人が決める時の手間が変わります。

---

### 長く残ると VACUUM が回収できない

ロックの他にも、準備済みのトランザクションが残ると困ることがあります。PostgreSQL の [PREPARE TRANSACTION の文書](https://www.postgresql.org/docs/17/sql-prepare-transaction.html)には、準備済みのまま長く置くと VACUUM が領域を回収できなくなり、極端な場合はトランザクション ID の周回を防ぐために DB が止まる、という注意があります。PostgreSQL のトランザクション ID は 32 ビットの番号を使い回すので、古い行を片付けないまま番号が一周すると、行の新旧を区別できなくなります。

ポイント DB で、10 万行を入れて全部消し、すぐに VACUUM を掛けました。準備済みのトランザクションが無い時と、1 つ残っている時と、それを `ROLLBACK PREPARED` で消した後の 3 回です。

{{< figure src="images/two-phase-commit_vacuum.webp" alt="横棒グラフ。準備済みが無い時は 100,000 行を回収。準備済みが 1 つ残っている時は回収 0 行で、100,000 行が残る。ROLLBACK PREPARED の後は 100,000 行を回収" caption="10 万行を消した直後の VACUUM が回収できた行の数" align="center" >}}

```text
-- 準備済みが無い時
tuples: 100000 removed, 0 remain, 0 are dead but not yet removable
-- 準備済みが 1 つ残っている時
tuples: 0 removed, 100000 remain, 100000 are dead but not yet removable
-- ROLLBACK PREPARED の後
tuples: 100000 removed, 0 remain, 0 are dead but not yet removable
```

準備済みのトランザクションは、PostgreSQL から見ればまだ終わっていないトランザクションです。そのため、それより後に消された行の古いバージョンは、まだ誰かが読むかもしれないものとして残されます。古いバージョンと VACUUM の関係は [MVCC と VACUUM](/notes/database-systems/mvcc-vacuum/) のノートで説明しています。`idle in transaction` の接続と違って接続の一覧に現れないので、長いトランザクションを接続の一覧で探す監視には映りません。

---

### PostgreSQL と MySQL の違い

MySQL では、`XA PREPARE` が PostgreSQL の `PREPARE TRANSACTION` に当たります。XA は、トランザクションマネージャが DB を呼び出す方法として X/Open が定めた[仕様](https://pubs.opengroup.org/onlinepubs/009680699/toc.pdf)で、Jakarta Transactions もこの呼び出しで DB を束ねます。同じ実験を MySQL 8.4 でも試しました。

```sql
XA START 'order-42';
UPDATE points SET balance = balance - 300 WHERE user_id = 1;
XA END 'order-42';
XA PREPARE 'order-42';
-- ここで接続が切れる
```

```text
-- XA RECOVER
1	8	0	order-42
ERROR 1205 (HY000) at line 1: Lock wait timeout exceeded; try restarting transaction
[ 10.27] MySQL を再起動
[ 12.76] 再起動が終わった
-- XA RECOVER
1	8	0	order-42
```

`XA RECOVER` の出力は、最後の列が識別子です。接続が切れた後も、再起動の後も、準備済みのトランザクションは `XA RECOVER` に残り、別の接続から送った UPDATE はロック待ちで失敗しました。MySQL でも、準備済みの XA トランザクションは `XA COMMIT` か `XA ROLLBACK` を明示するまで残る[仕様](https://dev.mysql.com/doc/refman/8.4/en/xa-restrictions.html)です。

この振る舞いは昔からではありません。MySQL 5.7.7 より前は、接続が切れたりサーバーを正常に停止したりすると、準備済みの XA トランザクションが中止されていました。2005 年に [Bug #12161](https://bugs.mysql.com/bug.php?id=12161) として報告され、2015 年の 5.7.7 で、準備済みの状態をバイナリログに残すよう直されています。直る前は、「はい」と答えた約束が接続と一緒に消えるので、つなぎ直したコーディネータがコミットを送っても、コミットさせる相手が残っていませんでした。

今の PostgreSQL と MySQL で違うのは、既定の設定です。

| | PostgreSQL 17 | MySQL 8.4 |
|---|---|---|
| 準備の文 | `PREPARE TRANSACTION` | `XA PREPARE` |
| 既定で使えるか | 使えない | 使える |
| 準備済みの一覧 | `pg_prepared_xacts` | `XA RECOVER` |
| 接続が切れた後・再起動の後 | 残る | 残る |
| ロックを待つ上限の既定 | 無し（`lock_timeout` が 0） | 50 秒 |

PostgreSQL は、`max_prepared_transactions` の既定が 0 で、そのままでは `PREPARE TRANSACTION` が「prepared transactions are disabled」（準備済みのトランザクションは無効）で失敗します。文書では、準備済みのトランザクションを追って片付けるトランザクションマネージャが無いなら、0 のままにして、忘れられた準備済みを作らないよう勧められています。

<br>

一方で、ロック待ちの上限（[lock_timeout](https://www.postgresql.org/docs/17/runtime-config-client.html#GUC-LOCK-TIMEOUT)）の既定は 0 で、上限がありません。実験では 10 秒に設定しましたが、既定のままのアプリは、準備済みのトランザクションが片付くまで待ち続けます。MySQL では `innodb_lock_wait_timeout` の既定が 50 秒なので、待ちは 50 秒ごとのエラーとして現れます。

---

### 2PC を使う前に決めること

既に 2PC で動いているシステムを持つ人が最初に確認することは、コーディネータが決定を記録する場所です。冒頭の図で赤い帯を終わらせられたのは、決定を知る誰かが残っていたからでした。トランザクションマネージャのログが消えないストレージにあり、再起動の時に準備済みの参加者を見つけて片付けるかを確認します。

そのうえで、`pg_prepared_xacts` の `prepared`（準備した時刻）や `XA RECOVER` を定期的に見て、一定の時間より古いものを知らせる監視を足します。UPDATE が止まって `pg_blocking_pids()` が 0 を返したら、最初に見るのはこの一覧です。

<br>

サービスをまたぐ更新に 2PC を新しく入れようとしている人は、全ての参加者に、他人が決めるまでロックを持って待つことを求める点を考えます。同じチームが持つ DB どうしなら受け入れられても、別のチームや外部のサービスに準備済みのまま待つことを求めるのは難しいはずです。

待たない代わりに、途中の状態が見えることを受け入れる構成もあります。各サービスが自分の DB でトランザクションを先にコミットし、失敗したら打ち消しの処理で戻すのが [Saga](/notes/distributed-systems/saga/) です。DB の更新と、他のサービスに送るイベントを同じトランザクションで書くのが [Transactional Outbox](/notes/distributed-systems/transactional-outbox/) です。以下は、注文とポイントの例で 3 つを比べた表です。

| | 2PC | Saga | Transactional Outbox |
|---|---|---|---|
| 参加者が待つもの | コーディネータの決定 | 待たない | 待たない |
| 外に見える途中の状態 | 決定を配る間の片方だけ | 後で打ち消す更新も見える | イベントが届くまでの片方 |
| 失敗した時 | 全員が中止する | 打ち消しの処理で戻す | 送信を再試行する |
| 参加者に求めること | 準備に対応した DB | 打ち消しの処理 | 同じイベントを 2 回受けても困らない作り |

送信を再試行すると同じイベントが 2 回届くことがあるので、受け手は [Idempotency](/notes/distributed-systems/idempotency/) のノートで扱う冪等な作りにしておきます。

身近な例では、コーヒー店が Saga に近いやり方で動いています。Gregor Hohpe 氏の「[Starbucks Does Not Use Two-Phase Commit](https://www.enterpriseintegrationpatterns.com/ramblings/18_starbucks.html)」（2004 年）は、店で 2PC を使うと、飲み物ができるまで代金とレシートを台に置いたままレジで待つことになる、と例えています。実際の店は先に代金を受け取り、飲み物を作れなければ返金します。

3 つのどれでも、注文はあるのにポイントがまだ引かれていない時間は生まれます。2PC は、その時間を決定を配る間に絞る代わりに、参加者にロックを持って待たせます。冒頭の図に描いた赤い帯のような待ちを受け入れるか、途中の状態を見せて後から直すことを受け入れるかが、選ぶ時の分かれ目です。

実験のスクリプトと出力の全体は [lab/](https://github.com/nao1215/debimate/tree/main/content/notes/distributed-systems/two-phase-commit/lab) にあります。
