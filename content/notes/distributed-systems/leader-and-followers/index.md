---
title: "Leader and Followers - レプリケーションの遅れと Leader の交代"
date: 2026-08-07
draft: false
series: ["技術ノート", "Distributed Systems"]
tags: ["distributed-systems", "coordination"]
weight: 5
wrapTables: true
topics: ["Replication / Coordination"]
---

PostgreSQL や MySQL の read replica、マネージドな DB（データベース）の自動フェイルオーバーは、書き込みを受け付ける 1 台と、その変更を複製する残りの台で動いています。書き込みを受け付ける台を Leader、複製する台を Follower と呼び、この構成を [Leader and Followers](https://martinfowler.com/articles/patterns-of-distributed-systems/leader-follower.html) と呼びます。Leader が落ちた時に Follower の 1 台を新しい Leader に切り替えることをフェイルオーバー、その Follower を Leader にすることを昇格と呼びます。

この構成を使っていると、次の 4 つを当たり前と思いがちです。

- コミットが返った行は、すぐに Follower からも読める
- 同期レプリケーションにすれば、Follower から古い値は読まない
- コミットが返った行は、Leader が落ちても消えない
- 落ちた Leader は、戻ってきても書き込みを受け付けない

手元の PostgreSQL 17 で試すと、4 つとも成り立ちませんでした。以下は、3 つ目と 4 つ目を試した時の様子です。

{{< figure src="images/leader-and-followers_failover.webp" alt="動く図。PostgreSQL 17 の Leader と Follower がそれぞれ 100 行を持つ。0.3 秒で Follower をネットワークから外し、Leader に id=101〜110 の 10 行を書くと、10 行ともコミットが返り Leader は 110 行になる。0.6 秒で Leader を docker kill で落とし、0.8 秒で Follower を昇格させると、新しい Leader は 100 行で id=101〜110 が無い。2.0 秒で古い Leader を起動し直すと Leader のまま起動し、最後のコマでは 2 台の両方に id=500 を書けて、古い Leader は v=1、新しい Leader は v=2 を持つ" caption="Leader を落として Follower を昇格させた時の行数（実測の時刻を 0.2 倍速で再生）" align="center" >}}

Leader が受け付けてコミットを返した 10 行は、昇格した Follower にはありませんでした。さらに、落とした Leader を起動し直すと Leader のまま動き出し、2 台がそれぞれ同じ id に別の値を受け付けました。

この形は実験の中だけの話ではありません。2018 年 10 月 21 日に GitHub で起きた障害では、データセンター間の通信が 43 秒途切れた間に、MySQL の Leader が別のデータセンターへ切り替わりました。

元の Leader には、新しい Leader へ届いていない数秒分の書き込みが残り、[事後の報告](https://github.blog/news-insights/company-news/oct21-post-incident-analysis/)によると、書き込みの多いクラスタの 1 つでは 954 件でした。サービスの劣化は 24 時間 11 分続きました。

<br>

本記事では、read replica やフェイルオーバーを使っている人、これから設定する人に向けて、次の問いに答えます。

- Follower から読むと、書いたばかりの値が見えないのはなぜか。
- 同期レプリケーションにすると、何が変わり、何が残るのか。
- Leader が落ちた時、コミットが返った行はどこへ行くのか。
- 戻ってきた古い Leader は、誰が止めるのか。
- etcd のように Raft で動く Leader は、何が違うのか。

実験では、1 台のマシンに Docker で PostgreSQL 17.11 と etcd v3.5.17 を立てました。

---

### コミットが返る所と、Follower で読める所

複数の台が対等に書き込みを受け付けると、同じ行への 2 つの更新が別々の台に届き、台ごとに届く順番が入れ替わります。どちらが後の更新かを決める場所が無いので、最後に残る値が台ごとに分かれます。書き込みを Leader 1 台に集めると、更新の順番は Leader が受け付けた順の 1 通りに決まり、Follower はその順に適用すれば同じ内容になります。

Leader は、受け付けた変更をまず [WAL（Write-Ahead Log、ログ先行書き込み）](/notes/distributed-systems/write-ahead-log/)に書きます。WAL はデータのファイルを書き換える前に、変更の内容を順に追記するログです。

PostgreSQL の[ストリーミングレプリケーション](https://www.postgresql.org/docs/17/warm-standby.html#STREAMING-REPLICATION)では、Leader がこの WAL を Follower に送り続け、Follower は受け取った WAL を自分のデータに適用します。Follower は Leader と同じ変更を同じ順に適用するので、遅れはあっても同じ内容に追い付きます。

問題は、アプリケーションにコミットが返るのが、この流れのどこかという点です。以下は、WAL が Follower で読めるようになるまでの段階と、コミットが返る所を並べた図です。

{{< figure src="images/leader-and-followers_commit_points.webp" alt="左から、Leader が WAL をディスクに書く、Follower が WAL を受け取り OS に渡す、Follower が WAL をディスクに書く、Follower が WAL を適用し行が読める、の 4 つの箱が矢印で並ぶ。上の青い矢印は COMMIT が返る所で、非同期（既定）は 1 つ目、同期 remote_write は 2 つ目、同期 on は 3 つ目、同期 remote_apply は 4 つ目の箱を指す。下の赤い矢印は Follower から新しい値が読めるのは 4 つ目の箱からで、1 つ目から 4 つ目の手前までの間に Follower を読むと古い値が返る" caption="COMMIT が返る所と、Follower から新しい値が読める所" align="center" >}}

PostgreSQL の既定は非同期で、Leader が自分のディスクに WAL を書いた時点でコミットを返します。WAL を Follower へ送るのはその後です。

同期レプリケーションにすると、Leader は Follower からの返事を待ってからコミットを返します。同期になるのは、Leader の [synchronous_standby_names](https://www.postgresql.org/docs/17/runtime-config-replication.html#GUC-SYNCHRONOUS-STANDBY-NAMES) に Follower の名前を書いた時だけです。そのうえで、どの段階の返事を待つかを [synchronous_commit](https://www.postgresql.org/docs/17/runtime-config-wal.html#GUC-SYNCHRONOUS-COMMIT) の値で決めます。

synchronous_commit は、既定の `on` で Follower がディスクに書いた所まで待ちます。`remote_write` は Follower が WAL を OS に渡した所で返り、ディスクへの書き出しは待ちません。適用して読めるようになるまで待つのは `remote_apply` だけです。

---

### Follower から読むと古い値が返る

図の赤い矢印の間がどれくらいの長さなのかを測りました。Leader で 1 行を `UPDATE` し、コミットが返った直後に、Follower で同じ行を読みます。これを 2000 回繰り返し、Follower が古い値を返した回数を数えました。

```python
for i in range(1, N + 1):
    leader.execute("update t set v = %s where id = 1", (i,))  # autocommit なので 1 文でコミット
    if wait_lsn:
        # 自分の書き込みが入った WAL の位置を覚え、Follower がそこまで適用するのを待つ
        lsn = leader.execute("select pg_current_wal_lsn()").fetchone()[0]
        while not follower.execute(
                "select pg_last_wal_replay_lsn() >= %s::pg_lsn", (lsn,)).fetchone()[0]:
            pass
    v = follower.execute("select v from t where id = 1").fetchone()[0]
    if v != i:
        stale += 1
```

同じマシンの上で、他に負荷も無い状態でも、非同期では 2000 回の全てで古い値が返りました。

{{< figure src="images/leader-and-followers_stale_read.webp" alt="横棒のグラフ。コミットの直後に Follower が古い値を返した割合は、非同期（既定）が 2000 回中 2000 回、同期 on が 2000 回中 1 回、同期 remote_apply が 0 回、非同期で LSN を待つやり方が 0 回。右の列はコミットまでの時間と、書いてから Follower で読み終えるまでの時間の中央値で、非同期が 0.64 ms と 0.71 ms、同期 on が 1.25 ms と 1.33 ms、同期 remote_apply が 1.17 ms と 1.22 ms、非同期で LSN を待つやり方が 0.59 ms と 1.18 ms" caption="コミットの直後に Follower を読んだ 2000 回のうち、古い値が返った回数（時間は中央値）" align="center" >}}

非同期では、書いてから Follower で読み終えるまでが 0.71 ms で、WAL が Follower に届いて適用されるより先に読んでしまいます。遅れがわずかでも、書いた直後に読む処理はその隙間に入ります。フォームを送信した後の画面で自分の投稿が見えない、という不具合は、書き込みを Leader に送り、その直後に表示する画面を Follower から読む構成で起きます。

同期の `on` にしても、2000 回のうち 1 回は古い値が返りました。測り直すと 0 回の時もあり、この回数は毎回変わります。ただ、COMMIT が返る所の図で、`on` は 3 つ目の箱でコミットが返るので、Follower がまだ適用していない短い間は仕組みとして残ります。

`remote_apply` にすると 0 回になり、代わりに全ての書き込みのコミットが 0.64 ms から 1.17 ms に延びました。この差は同じマシンの中で測った値で、Follower が別のデータセンターにあれば、往復の時間がそのまま全てのコミットに足されます。

<br>

#### 自分の書き込みだけを待つ

4 つ目の行は、レプリケーションは非同期のまま、読む側で待つやり方です。コミットの後に Leader で [pg_current_wal_lsn()](https://www.postgresql.org/docs/17/functions-admin.html) を呼んで WAL の位置（LSN、Log Sequence Number）を覚え、Follower の `pg_last_wal_replay_lsn()` がその位置を越えるまで待ってから読みます。

古い値は 0 回で、コミットは非同期のまま 0.59 ms でした。待つのは、書いた本人がその直後に読む時だけで済みます。

書いた本人には自分の書き込みが必ず見える、という保証は [read-your-writes](https://jepsen.io/consistency/models/read-your-writes) と呼ばれます。全ての読み取りに必要な保証ではなく、ほかの人が書いた投稿の一覧のように少し古くても困らない読み取りは、そのまま Follower に回せます。

---

### 同期レプリケーションで残ること

同期にすると、コミットが返った行は Follower のディスクにもあります。その代わり、Follower が返事をしなければ、Leader はコミットを返せません。冒頭の実験と同じく、Follower をネットワークから外してから、同期の `on` で 1 行を書きました。

```text
   0.2s  Follower をネットワークから外した
   0.2s  Leader: insert id=101 ...
   5.2s  5 秒待っても COMMIT が返らない（別の接続から見た行数 100）
```

コミットは返りませんでした。同期の Follower が落ちると、[コミットが完了しないことがあります](https://www.postgresql.org/docs/17/warm-standby.html#SYNCHRONOUS-REPLICATION)。そのため、書き込みを止めたくなければ、同期の候補になる Follower を複数並べます。`synchronous_standby_names = 'ANY 1 (f1, f2)'` のように Follower の名前 f1・f2 を書くと、2 台のうちどちらか 1 台の返事でコミットを返します。

ただし、どちらが返事をしたかは書き込みごとに違います。返事をしなかった方を昇格させると、コミットが返った行が消えます。昇格させるのは WAL を一番先まで受け取った台で、受け取った位置は各 Follower で [`pg_last_wal_receive_lsn()`](https://www.postgresql.org/docs/17/functions-admin.html#FUNCTIONS-RECOVERY-INFO-TABLE) を呼ぶと分かります。

<br>

#### 返らなかったコミットの行方

別の接続から `pg_cancel_backend()` でコミットの待ちを取り消すと、次の警告と一緒にコミットが返りました。

```text
WARNING: canceling wait for synchronous replication due to user request
DETAIL: The transaction has already committed locally, but might not have been replicated to the standby.
```

Leader では、取り消した行が他の接続から見えるようになり、Follower には届いていません。

待ちを取り消さずに Leader を落とした場合も、アプリケーションは接続が切れたというエラーを受け取りますが、Leader を起動し直すとその行がありました。これは PostgreSQL の決まった動きで、返事を待っている間に Leader が再起動すると、待っていたトランザクションは復旧の時にコミット済みになります。

| 書き込みの仕方 | アプリが受け取った結果 | 昇格した Follower | 起動し直した Leader |
|---|---|---|---|
| 非同期 | 10 行ともコミット | 100 行（10 行が無い） | 110 行 |
| 同期 `on` | 接続が切れたエラー | 100 行 | 101 行 |
| 同期 `on` で待ちを取り消す | 警告付きのコミット | 100 行 | 101 行 |

同期にして守れるのは、コミットが返った行は返事をした Follower にもある、という所までです。エラーで返った書き込みは、どこかに残っているかもしれません。エラーを見て書き込みを送り直すなら、二重に書かれても結果が変わらないように、[冪等性](/notes/distributed-systems/idempotency/)を持たせておく必要があります。

---

### Leader が落ちた時に消える行

冒頭の図は、非同期のまま次の手順で動かした結果です。Follower をネットワークから外すのは、WAL が届いていない状態を作るためです。

```python
sh("docker", "network", "disconnect", "lf-net", "lf-follower")
for i in range(101, 111):
    leader.execute("insert into t values (%s, 0)", (i,))   # 10 行ともコミットが返る
subprocess.run(["docker", "kill", "lf-leader"])           # Leader を落とす
sh("docker", "network", "connect", "lf-net", "lf-follower")
follower.execute("select pg_promote()")                   # Follower を Leader に昇格させる
follower.execute("select count(*) from t")                # 100 行
```

PostgreSQL では、Follower の `pg_promote()` で昇格させます。昇格した Follower の行数は 100 で、コミットが返った 10 行がありませんでした。非同期では、WAL を送るのはコミットを返した後なので、送る前に Leader が落ちれば、その分は Follower に届きません。

PostgreSQL では[ログの転送](https://www.postgresql.org/docs/17/warm-standby.html)が既定で非同期なので、Leader が落ちた時には、データを失いうる時間の幅があります。

<br>

#### GitHub の障害

GitHub の障害も、この形でした。GitHub は、MySQL で Leader を切り替える処理を [Orchestrator](https://github.com/openark/orchestrator) に任せていて、Orchestrator 自身は Raft で合意を取ります。

通信が途切れた 43 秒の間に、Orchestrator は Leader を西海岸のデータセンターに移しました。GitHub が使っていた半同期レプリケーションは、Follower の受け取りを待ってからコミットを返す複製で、[対象は同じデータセンターの Follower だけ](https://github.blog/engineering/infrastructure/mysql-high-availability-at-github/)でした。西海岸への複製は待っていなかったので、東海岸の Leader にだけある数秒分の書き込みが残りました。

通信が戻った時には、西海岸の新しい Leader は約 40 分ぶんの書き込みを受け付けていて、単純に東海岸へ戻すこともできませんでした。43 秒の途絶で Orchestrator が Leader を落ちたと判定した経緯は、[ハートビート](/notes/distributed-systems/heartbeat/)のノートで扱っています。

Leader を誰がどう選ぶかと、データをどう複製するかは別の仕組みです。Leader を選ぶ側を Raft にしても、データの複製が非同期なら、コミットが返った書き込みはフェイルオーバーで消えることがあります。

---

### 古い Leader を止めるのは誰か

冒頭の図では、最後のコマで、落とした Leader を `docker start` で起動し直しただけで、Leader として書き込みを受け付けました。PostgreSQL は、自分の他に Leader がいることを知りません。2 台が Leader として別々の書き込みを受け付け、内容が分かれていく状態をスプリットブレイン（split brain）と呼びます。

```text
   2.0s  古い Leader: insert id=500 -> COMMIT が返った（行数 111、id=500 の v=1）
   2.0s  昇格した Follower: insert id=500 -> COMMIT が返った（行数 101、id=500 の v=2）
```

[フェイルオーバー](https://www.postgresql.org/docs/17/warm-standby-failover.html)の後には、古い Leader にもう Leader ではないと伝える仕組みが必要です。PostgreSQL 自身はこの仕組みを持たず、外の道具に任せています。

古い Leader を戻すには、[pg_rewind](https://www.postgresql.org/docs/17/app-pgrewind.html) で新しい Leader とずれた分を巻き戻し、Follower として繋ぎ直します。この時、古い Leader にだけあった id=101〜110 の行は捨てられます。pg_rewind を使うには、古い Leader で `wal_log_hints` かデータのチェックサムを有効にしておく必要があり、どちらも既定では無効です。

<br>

#### 外の道具が止める仕組み

PostgreSQL のフェイルオーバーでよく使われる [Patroni](https://patroni.readthedocs.io/en/latest/dcs_failsafe_mode.html) は、etcd などの Key-Value ストアに、Leader であることを示す期限付きのキーを置きます。Leader はこのキーの期限を更新し続け、更新できなくなったら、期限が切れる前に自分を読み取り専用に落とします。期限が切れると、他の台がキーを取って昇格します。

期限付きの権利で古い持ち主を止める考え方は [Lease](/notes/distributed-systems/lease/) と同じです。通信を仲介する [Ambassador](/notes/software-architecture/ambassador/) のノートでは、戻ってきた古い Redis の master に 99 件を書いて全てを失う様子を再現しています。

自分で組んだフェイルオーバーの手順や、マネージドな DB の設定を見る時は、落とした Leader をそのまま起動し直して、書き込めてしまうかを試すと分かります。

---

### Raft では、外された Leader は書き込めない

[Raft](https://raft.github.io/raft.pdf) は、Leader and Followers の形で複数の台にログを複製する合意アルゴリズムです。[etcd](https://etcd.io/) は Raft で複製する Key-Value ストアで、上の Patroni が Leader のキーを置く先の 1 つです。etcd の 3 台で、PostgreSQL と同じ実験を行いました。Leader をネットワークから外し、外した Leader と残りの 2 台の両方に書き込みます。

{{< figure src="images/leader-and-followers_raft.webp" alt="動く図。etcd の e1・e2・e3 の 3 台で、最初は e1 が term 2 の Leader で k=v1。0.3 秒で e1 をネットワークから外すと、2.1 秒で e1 は過半数と話せずに自分から Leader を降り、2.5 秒で残りの e2 と e3 が e2 を term 3 の Leader に選び、2.6 秒で e2 に書いた k=v-new が e2 と e3 に入る。外した e1 への put k=v-old は待ち続け、5.4 秒で失敗する。e1 から読むと、既定の linearizable は失敗し、serializable は古い v1 を返す。最後のコマでは e1 を戻してから 3 秒後、e1 は term 3 の Follower になり、3 台とも k は v-new で、e1 のログにあった v-old は term 3 のエントリで上書きされている" caption="etcd の 3 台で Leader をネットワークから外した時（実測の時刻を 0.5 倍速で再生）" align="center" >}}

外した e1 への書き込みは、5 秒待った後に失敗し、コミットは返りませんでした。Raft では、Leader は書き込みを自分のログに足した後、過半数の台がそれを受け取ってから初めてコミットを返します。3 台のうち 1 台だけになった e1 は過半数に届かないので、書き込みを受け付けても返事ができません。

PostgreSQL の非同期で起きた、コミットを返してから消える、という順番になりません。過半数の考え方は [Quorum](/notes/distributed-systems/quorum/) で詳しく扱っています。

残りの 2 台は、e1 から定期的に届く合図のハートビートが途絶えてから e2 を新しい Leader に選びました。etcd の[既定](https://etcd.io/docs/v3.5/tuning/)は、ハートビートの間隔が 100 ms、途絶えたと見なすまでが 1000 ms で、外してから新しい Leader が決まるまでの約 2.2 秒は、コミットを返せる台がいなかった時間です。

外された e1 も、外してから 1.8 秒後に、自分から Leader を降りて Follower になっていました。etcd は [CheckQuorum](https://github.com/etcd-io/etcd/blob/v3.5.17/raft/raft.go#L164-L166) という設定を有効にしていて、Leader は、途絶えたと見なすのと同じ 1000 ms の間に過半数と連絡できないと、自分で Leader を降ります。

---

### 任期の番号で古い Leader を見分ける

Leader が選ばれるたびに、任期（term）の番号が 1 つ増えます。e2 は term 3 の Leader で、e1 は term 2 のまま Follower に降りていました。戻ってきた e1 は、自分の term 2 より大きい番号を見て、term 3 で Leader になった e2 に従いました。e1 で動く etcd も、ログにこの順で書き残していました。

```text
stepped down to follower since quorum is not active
became follower at term 2
became follower at term 3
found conflict at index 10 [existing term: 2, conflicting term: 3]
```

PostgreSQL では外の道具が古い Leader を止めましたが、etcd では、過半数と話せない Leader は自分で降り、戻った台はこの番号を見て新しい Leader に従います。番号の大きい側に従わせて古い操作を拒む点は、Lease のノートで扱う fencing token と同じ考え方です。fencing token は、権利を得るたびに増やす番号で、古い番号の操作を拒みます。期限付きキーを使う Patroni と違い、任期の番号は時計に頼りません。

<br>

Leader を選ぶ投票では、各台は 1 つの任期に 1 票しか投じず、当選には過半数の票が必要です。過半数どうしは必ず 1 台を共有するので、1 つの任期に Leader は 2 台立ちません。さらに、各台は候補のログが自分より古ければ投票しません。新しさは、ログの末尾にある任期の番号を先に比べ、同じなら長さで比べます。コミット済みの書き込みは過半数の台が持つので、それを持たない台は過半数の票を集められません。投票した記録は、ディスクに書いてから返事をします。忘れると、再起動の後に同じ任期で 2 票を投じ、Leader が 2 台立ちえます。

<br>

ログの 1 件をエントリと呼びます。外された Leader が自分のログに足したまま、過半数に届かなかったエントリは、戻った後に新しい Leader のログで上書きされます。上に載せたログでは最終行がこれで、e1 に足された v-old のエントリが term 3 のエントリで上書きされました。

一方で、過半数に届いたエントリが、いつもコミット済みになるとは限りません。Raft 論文の 5.4.2 節は、Figure 8 で次の 5 台の例を示しています。

{{< figure src="images/leader-and-followers_overwrite.webp" alt="段階 1 から 4 までを横に並べ、各段階で A から E の 5 台がログの同じ位置に持つエントリの任期を縦に並べた図。段階 1 は A と B が 2。段階 2 は A と B が 2、E が 3。段階 3 は A・B・C が 2 で過半数に届き、E が 3。段階 4 は任期 5 の Leader になった E が上書きし、5 台とも 3 になって任期 2 のエントリが消える。エントリが無い所は点線の「-」" caption="過半数に届いた任期 2 のエントリが、上書きされるまで" align="center" >}}

任期 2 の Leader A が B に配って落ち、任期 3 の Leader E が自分だけに書いて落ちます。任期 4 で戻った A が C に配り、任期 2 のエントリは 3 台に届きます。それでも A が落ちると、E は B・C・D の票を集めて任期 5 の Leader になれます。ログの末尾にある任期は、E が 3 で、B・C の 2 より新しいためです。

そのため Raft の Leader は、自分の任期で足したエントリが過半数に届いた時に初めてコミットを進め、それより前のエントリはまとめてコミット済みにします。自分の任期で足したエントリが過半数に届けば、それを持たない台は投票の検査に落ちて当選できません。

<br>

票が割れて誰も当選しない時に備えて、各台はハートビートを待つ時間を毎回ランダムにずらします。この待ち時間は、メッセージの往復より十分長く、1 台が故障する間隔より十分短いことが Raft の前提です。例えば etcd が既定にしている 1000 ms は、同じ LAN で往復する時間を想定した値です。待ち時間を短くすると、遅れただけの Leader を落ちたと誤って見なして交代が増え、長くすると切り替えが遅れます。

---

### 外された Leader から読む

ただし、読み取りは別です。外された e1 から読むと、etcd が既定とする linearizable の読み取りは失敗しましたが、`--consistency=s` を付けた serializable の読み取りは、古い `v1` を返しました。serializable の読み取りは、[速さと引き換えに古いデータを返しうる](https://etcd.io/docs/v3.5/learning/api_guarantees/)読み方です。

linearizable の読み取りでは、Leader が過半数とハートビートをやり取りして自分がまだ Leader であることを確認してから答えます。e1 はこの時すでに Follower に降りていて、Leader とも過半数とも話せないので答えられません。速さのために手元の値で答える読み取りは、PostgreSQL の Follower と同じく古い値を返します。

この確認が無かった頃の etcd では、Leader から読んでも古い値が返りました。2014 年、Kyle Kingsbury 氏は故障を注入して DB の正しさを調べる [Jepsen](https://jepsen.io/) で、分断で孤立した古い Leader が、自分をまだ Leader だと思って手元の値を返すことを[示しました](https://aphyr.com/posts/316-call-me-maybe-etcd-and-consul)。報告の [issue #741](https://github.com/etcd-io/etcd/issues/741) を受けて、読み取りもログに通す選択肢が足されました。

| 方式 | コミットが返る時点 | Leader が落ちた時 | 戻ってきた古い Leader |
|---|---|---|---|
| PostgreSQL 非同期 | Leader のディスクに書いた時 | 届いていない分が消える | 外の道具が止める |
| PostgreSQL 同期 `on` | Follower のディスクに書いた時 | 返事をした台を昇格させれば残る | 外の道具が止める |
| Raft（etcd） | 過半数が受け取った時 | 返った分は残る | 自分で降り、term を見て従う |

Raft の代わりに払うのは台数と待ち時間です。1 台が落ちても書き込みを続けるには 3 台、2 台なら 5 台が必要で、全ての書き込みが過半数の返事を待ちます。Raft が想定する故障は台の停止と分断で、嘘の値を返す台は想定していません。そうした台まで扱うのは[ビザンチン障害耐性](/notes/distributed-systems/byzantine-fault-tolerance/)の方式です。

どの方式でも、書き込みは全て Leader 1 台を通るので、書き込める量の上限は Leader 1 台で決まります。超えるなら、[Consistent Hashing](/notes/distributed-systems/consistent-hashing/) などでデータをキーで分け、分けた組ごとに Leader を置きます。

<br>

<details><summary>余談: Leader を固定しない Paxos</summary>

Leslie Lamport 氏の合意アルゴリズム Paxos は、Leader を固定せずに、提案された値のうち 1 つだけを選びます。提案する台は値に番号を付けて過半数に受け入れを求め、受け入れる側は、より大きい番号を見たら小さい番号の提案を以後受け入れないと約束します。

ただし、提案する台が 2 台いると、互いに大きい番号を出し合って、どちらの値も選ばれないまま続くことがあります。以下は、その流れを描いた図で、番号は説明用の値です。

{{< figure src="images/leader-and-followers_paxos.webp" alt="左に提案する台 1、右に提案する台 2、中央に受け入れる過半数の台がある。上から順に、台 1 が番号 1 を出し、台 2 が番号 2 を出すと番号 1 は選ばれなくなる。台 1 が番号 3 を出すと番号 2 も選ばれなくなり、台 2 が番号 4 を出すと番号 3 も選ばれなくなる。下に、番号を出し合う限り何も選ばれないまま続くと書かれている" caption="提案する台が 2 台いると、番号を競り合って何も選ばれない" align="center" >}}

[Paxos Made Simple](https://lamport.azurewebsites.net/pubs/paxos-simple.pdf) は、進み続けるために提案する役を 1 台に決めることを 2.4 節で求めています。ログの位置ごとに Paxos を繰り返し、安定した Leader に提案を任せる形は Multi-Paxos と呼ばれ、結局は Leader and Followers の形に戻ってきます。

</details>

<br>

<details><summary>余談: Leader がいない複製と、Leader が複数いる複製</summary>

Leader を置かずに、どの台でも書き込みを受け付ける複製もあります。Amazon が発表した [Dynamo](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf) の流れをくむ [Apache Cassandra](https://cassandra.apache.org/) などで、書く台と読む台の数を重ねて新しい値を拾います。重ねるだけでは書き込みの順序は決まらないので、どちらが新しいかはタイムスタンプなどで別に判定します。この重ね方は、上で触れた Quorum のノートで扱っています。

データセンターごとに Leader を置いて互いに複製する方式もあり、同じ行を 2 か所で同時に書き換えると、後でどちらを残すかを決める必要があります。冒頭の実験で見た id=500 は、この食い違いを Leader and Followers の中で起こしてしまった形です。どちらを残すかを決めなくても同じ状態に揃うデータ型に [CRDT](https://crdt.tech/)（Conflict-free Replicated Data Type）がありますが、扱えるデータの形は限られます。

</details>

<br>

---

### Follower に読み取りを回す前に

read replica やフェイルオーバーを使う時に決めることは 4 つです。

1 つ目は、どの読み取りを Follower に回すかです。書いた本人がその直後に読む画面は、Leader から読むか、LSN を待ってから Follower で読みます。前半の実験では、非同期の Follower は 2000 回中 2000 回、古い値を返しました。

2 つ目は、同期レプリケーションを使うかと、同期の Follower を何台にするかです。同期の Follower が 1 台だけだと、その 1 台が止まるだけで書き込みも止まるので、`ANY 1 (f1, f2)` のように候補を複数並べます。その時、コミットが返った行を持つのは返事をした台だけなので、フェイルオーバーでは WAL を一番先まで受け取った台を昇格させます。

3 つ目は、エラーで返った書き込みの扱いです。同期でも、エラーで返った行が古い Leader に残っていることがあるので、送り直しても二重にならないようにしておきます。

4 つ目は、古い Leader を誰が止めるかです。冒頭の図で最後のコマが示すように、PostgreSQL だけでは、落とした Leader は起動し直すと Leader に戻ります。フェイルオーバーの道具が、更新の止まった Leader を読み取り専用に落とすか、手元で落として起動し直して試しておくと安心です。

実験のスクリプトと出力の全体は [lab/](https://github.com/nao1215/debimate/tree/main/content/notes/distributed-systems/leader-and-followers/lab) にあります。
