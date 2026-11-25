---
title: "Quorum - 過半数の重なりで一貫性を保つ書き込みと読み取り"
date: 2026-08-06
draft: false
series: ["技術ノート", "Distributed Systems"]
tags: ["distributed-systems", "coordination"]
weight: 4
wrapTables: true
topics: ["Replication / Coordination"]
---

[Apache Cassandra](https://cassandra.apache.org/) に書き込んだら、アプリケーションに次のエラーが返ってきたとします。同じデータを 3 台のノードに持たせていて、書き込みを受けたノードが、そのうち 2 台の応答を待つ設定（QUORUM）です。同じデータを持つ各台をレプリカ、書き込みを受けて他のレプリカに配るノードを coordinator と呼びます。

```text
WriteTimeout: Error from server: code=1100 [Coordinator node timed out waiting for replica nodes' responses]
message="Operation timed out - received only 1 responses."
info={'consistency': 'QUORUM', 'required_responses': 2, 'received_responses': 1, 'write_type': 'SIMPLE'}
```

書き込みは失敗したように見えます。ところが、その後に読み方によっては、書いたはずの値が返ってきます。以下は、手元の Cassandra 5.0.6 で 3 台のうち 2 台を止め、上のエラーを起こしてから、止めた 2 台を戻すまでの記録です。図の ONE は 1 台だけから読む指定で、hint は止まった台へ後から送り直す書き込みです。どちらも後の節で説明します。

{{< figure src="images/quorum_timeout.webp" alt="動く図。上に経過時間と時間の帯、左に q1・q2・q3 の 3 台と各台が持つ値、右にクライアントから見えたことが時刻付きで並ぶ。0.2 秒に q2 と q3 を止め、v2 を QUORUM で書く。2.2 秒に WriteTimeout が返るが、q1 を ONE で読むと v2 が返る。20.8 秒に q1 が q2 を DOWN と判定し、21.8 秒に q3 も DOWN と判定する。22.0 秒に v3 を QUORUM で書くと Unavailable が返る。22.0 秒に 2 台を戻した直後、q2 を ONE で読むと古い v1、QUORUM で読むと v2 が返る。26.7 秒に hint が届いて 3 台とも v2 になり、最後のコマには、エラーになった v2 は残り、v3 はどの台にも無いと書かれている" caption="QUORUM の書き込みがエラーになった後、3 台が持つ値（実測の時刻を 3 倍速で再生）" align="center" >}}

エラーになった v2 は、書き込みを受け付けた q1 に残り、戻った 2 台にも 5 秒ほどで届いて、最後は 3 台とも v2 になりました。一方、20 秒後に書いた v3 は別のエラー（Unavailable）で失敗し、どの台にも残りませんでした。

2 台の応答を待つ、という設定の「2」が Quorum（クォーラム、定足数）です。同じデータを複数のノードに持たせる構成で、操作を成立させるのに応答が必要なノードの数を指します。多くの場合は過半数で、3 台なら 2 台です。

Cassandra を使っていてこのエラーに出会った人も、[etcd](https://etcd.io/) や [Apache Kafka](https://kafka.apache.org/) の台数を決めようとしている人も、過半数で何が保証され、何が保証されないかを知っておくと、エラーの扱いと台数を決められます。etcd は Kubernetes が設定を保存する Key-Value ストアで、Kafka はメッセージを複製して保存するキューです。

<br>

本記事では、次の疑問に順に答えます。

- 過半数の台が応答すると、何が保証されるのか。
- 何台で組めば、何台まで止まれるのか。
- エラーになった書き込みは、どこに残り、いつ広がるのか。
- WriteTimeout と Unavailable は、何が違うのか。
- エラーになった書き込みは、どう扱えば良いのか。
- Raft・Kafka・Aurora の複製は、何が違うのか。

考える故障はノードの停止とネットワークの分断だけで、誤った値を返すノードは[ビザンチン障害](/notes/distributed-systems/byzantine-fault-tolerance/)の方式が扱います。

---

### 過半数どうしは必ず重なる

過半数を使う理由は、過半数の集まりを 2 つ選ぶと、必ず 1 台は両方に入ることです。例えば 3 台なら 2 台と 2 台、5 台なら 3 台と 3 台で、どう選んでも合計が台数を超えるので、重ならない選び方がありません。

Cassandra のように、どのノードでも書き込みを受け付ける構成では、この重なりを読み書きに使います。冒頭で述べた coordinator は、書き込みを全てのレプリカに送り、決めた数の応答が集まった時点でクライアントに成功を返します。読む時も同じで、決めた数のレプリカから値を集め、新しい方を返します。

レプリカの数を N、書き込みで待つ応答の数を W、読み取りで集める応答の数を R とすると、W + R > N なら、読んだ台のうち少なくとも 1 台は最新の成功した書き込みを受け取っています。以下は、3 台で W と R を変えた時の図です。

{{< figure src="images/quorum_overlap.webp" alt="左右 2 つの枠に q1・q2・q3 の 3 台が並ぶ。左は W=2・R=2 で、書き込みが届いた q1 と q2 が v2、読んだ q2 と q3 のうち q2 が重なり、読む側は v2 を選べる。右は W=1・R=1 で、書き込みが届いたのは q1 だけ、読んだのは q3 だけで重ならず、v1 が返る" caption="書き込みが届いた台と読んだ台が、重なる場合と重ならない場合" align="center" >}}

読み書きの数をこう重ねる考え方は、Gifford 氏の [1979 年の論文](https://doi.org/10.1145/800215.806583)（Weighted Voting for Replicated Data）に遡り、Amazon が社内向けに作った Key-Value ストア Dynamo の[論文](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf)（2007 年）で広く知られました。

Cassandra では、W と R をクエリごとに consistency level で指定します。書き込みが後の読み取りから見える条件は、Cassandra の[公式ドキュメント](https://cassandra.apache.org/doc/latest/cassandra/architecture/dynamo.html)でも `W + R > RF` です。RF（replication factor）はレプリカの数で、上の N に当たります。レプリカが 3 つの時は、次の通りです。

| consistency level | 応答を待つレプリカ | 3 つの時 | 1 台止まった時 |
|---|---|---|---|
| ONE | 1 つ | 1 | 使える |
| QUORUM | 過半数 | 2 | 使える |
| ALL | 全て | 3 | 使えない |

どちらが新しいかは、値に付いた時刻で決めます。Cassandra は書き込みごとにタイムスタンプを付け、読む時に集めた値のうち時刻の新しい方を採ります。そのため、重なりで保証されるのは「最新の書き込みを受け取った台が、読んだ台に含まれる」ことまでで、時刻を付ける側の時計がずれていれば、新しい方の判断を誤ります。

<br>

<details><summary>余談: 同時に来た 2 つの書き込み</summary>

書き込みどうしは W > N / 2 で重なりますが、それが役に立つのは、書く前に今のバージョン番号を集めて次の番号を決める方式です。Gifford 氏の重み付き投票がこの形で、出会った台が、手元の番号と元にした番号が一致する時だけ書き込みを受け付ければ（compare-and-set）、成立するのは 1 つに絞れます。

Cassandra の QUORUM はバージョン番号を読まずに時刻を付けて書くだけなので、同時に来た 2 つの書き込みはどちらも成功を返し、読む時には時刻の新しい方が選ばれます。片方だけを成立させたいなら、`UPDATE ... IF` のような[条件付きの書き込み](https://cassandra.apache.org/doc/latest/cassandra/developing/cql/dml.html#update-statement)を使います。条件の判定に Paxos を使うので、普通の書き込みより遅くなります。

Dynamo は、止まったノードの代わりにレプリカを持つはずのない台へ書く sloppy quorum を使うので、障害の間は読み書きの重なりも保証されません。Cassandra の QUORUM が数えるのは、そのデータを持つはずのレプリカから届いた応答だけです。

</details>

<br>

---

### 何台で組み、何台まで止まれるか

過半数で決めるなら、止まれる台の数は「台数 − 過半数」です。Martin Fowler 氏のサイトにある Unmesh Joshi 氏の [Majority Quorum](https://martinfowler.com/articles/patterns-of-distributed-systems/majority-quorum.html) の解説も、f 台の故障に耐えるには 2f + 1 台が要るとしています。

| 台数 | 過半数 | 止まれる台 |
|---|---|---|
| 1 | 1 | 0 |
| 2 | 2 | 0 |
| 3 | 2 | 1 |
| 4 | 3 | 1 |
| 5 | 3 | 2 |
| 6 | 4 | 2 |

4 台は 3 台と同じく 1 台までしか止まれず、6 台は 5 台と同じ 2 台です。偶数にすると、止まれる台は増えないのに、故障しうる台だけが 1 つ増えます。

ネットワークが分断された時も同じです。4 台が 2 台と 2 台に分かれると、どちらも過半数に届かず、書けません。5 台なら、3 台と 2 台に分かれても 3 台のほうは書けますが、2 台・2 台・1 台に割れると全体が止まります。[etcd の FAQ](https://etcd.io/docs/v3.5/faq/) が台数を奇数にするよう勧めているのは、このためです。台数を増やすと複製先が増えて書き込みが遅くなるので、同じ FAQ は 7 台以下を勧め、多くの場合は 2 台の障害に耐える 5 台で足りるとしています。

Cassandra では、過半数をクラスタの台数ではなく、データごとのレプリカの数で数えます。例えば 6 台のクラスタでも、レプリカの数が 3 なら、データごとに 3 台のうち 2 台が応答すれば足ります。逆に、どこか 2 台が止まれば、その 2 台にレプリカを持つデータだけが QUORUM で読み書きできなくなります。どのデータをどのノードが持つかは、ノードとデータのキーを同じ円の上に並べる [Consistent Hashing](/notes/distributed-systems/consistent-hashing/) で決まります。

データセンターをまたいでレプリカを置くと、QUORUM は遠いデータセンターの応答も待つので、その往復の時間が毎回の待ち時間に加わります。coordinator と同じデータセンターにあるレプリカから過半数を待つ LOCAL_QUORUM があるのは、このためです。

---

### エラーになった書き込みの行方

冒頭の記録を取った実験を説明します。Docker で Cassandra 5.0.6 を 3 台（q1・q2・q3）動かし、レプリカの数を 3 にした表へ、Python の [cassandra-driver](https://github.com/datastax/python-driver) 3.29.2 から書きました。coordinator は q1 に固定し、ドライバーが自動で再試行しないようにしています。

各台がどの値を持つかを見分けるため、読み取りの時に古いレプリカを直す [read repair](https://cassandra.apache.org/doc/latest/cassandra/managing/operating/read_repair.html) と、別の台へ投機的に読みに行く speculative retry は切っています。以下は、止めて書いて読む部分の抜粋です。

```python
write(s1, "v1", CL.ALL)                 # 3 台とも v1

docker("pause", "q2", "q3")             # 2 台のプロセスを止める
write(s1, "v2", CL.QUORUM)              # 2 台の応答を待つ
read(s1, CL.ONE)                        # q1 だけで読む

while nodetool_status().count("\nDN") < 2:
    time.sleep(1)                       # q1 が 2 台を DN（Down）と見なすまで待つ
write(s1, "v3", CL.QUORUM)

docker("unpause", "q2", "q3")           # 2 台を戻し、0.5 秒ごとに各台を読む
```

`docker pause` はコンテナ内のプロセスを凍らせるので、q2 と q3 は落ちたのではなく、返事をしなくなっただけです。出力は次の通りです（抜粋）。

```text
  0.16s  pause q2 q3
  2.16s  write v2 QUORUM: WriteTimeout: ... 'required_responses': 2, 'received_responses': 1
  2.16s  read via q1 ONE: v2
 22.01s  write v3 QUORUM: Unavailable: ... 'required_replicas': 2, 'alive_replicas': 1
 22.04s  unpause q2 q3
 22.21s  ONE q1=v2 q2=v1 q3=v1  QUORUM via q2=v2
 26.71s  ONE q1=v2 q2=v2 q3=v2  QUORUM via q2=v2
```

v2 の書き込みは、ちょうど 2 秒で WriteTimeout になりました。2 秒は、Cassandra 5.0.6 で `write_request_timeout` が既定で持つ値です。Cassandra の書き込みは consistency level に関係なく全てのレプリカに送られ、consistency level は coordinator が何台の応答を待ってから返事をするかを決めるだけです。

そのため、q1 は自分のレプリカに v2 を書き終えていて、q2 と q3 の応答だけが来ませんでした。応答が足りなくても、q1 に書いた v2 はそのまま残ります。

<br>

#### 戻った台に届くまで

2 台を戻した直後、q2 だけで読む（ONE）と古い v1 が返り、同じ q2 を coordinator にして過半数で読む（QUORUM）と v2 が返りました。v2 を持つのは q1 だけなので、この回の q2 は読む相手に q1 を選んでいたことになります。

q2 が自分と q3 を選べば、QUORUM で読んでも v1 が返ります。v2 は q1 の 1 台にしか届いておらず、実際の W は 1 だったからです。W + R > N が保証するのは、W 台に届いた書き込み、つまり成功した書き込みだけです。

q2 と q3 が v2 を持ったのは、戻してから 4.7 秒後でした。Cassandra の coordinator は、応答が来なかったレプリカに宛てた書き込みを手元に hint として保存し、そのレプリカが戻ったら送り直します。この仕組みを [hinted handoff](https://cassandra.apache.org/doc/latest/cassandra/managing/operating/hints.html) と呼び、タイムアウトした書き込みにも hint を残します。

凍っていたのはプロセスだけなので、q2 と q3 に宛てた元の書き込みは、OS が受け取ってソケットに溜めていました。q2 のログを見ると、戻した時にそれを読みましたが、送られてから 23 秒経っていたので古すぎるとして捨てていました。v2 を届けたのは q1 の hint です。以下は、その時の q2 と q1 のログです（抜粋）。MUTATION_REQ は、他の台から届いた書き込みの要求です。

```text
q2: MUTATION_REQ messages were dropped in last 5000 ms: 0 internal and 1 cross node.
    ... Mean cross-node dropped latency: 23016 ms
q1: Finished hinted handoff of file 29f4c1e9-...-2.hints to endpoint /172.22.0.3:7000
q1: Finished hinted handoff of file cb7dde32-...-2.hints to endpoint /172.22.0.4:7000
```

q2 は 23 秒前に送られた書き込みを捨て、その後に q1 が q2（172.22.0.3）と q3（172.22.0.4）へ hint を送り終えています。

こうして、クライアントにはエラーになった v2 が、hint の到着後は 3 台のどこから読んでも返る値になりました。逆に、q1 が故障して hint ごと失われれば、v2 はどこにも広がりません。hint を溜めるのは、既定では止まってから 3 時間（`max_hint_window`）までで、それより長く止まった台には届きません。WriteTimeout の後に v2 が残るかどうかは、クライアントからは分かりません。

<br>

#### 読み取りでも広がる

本記事の実験では read repair を切りましたが、表を既定のまま作ると read repair が働きます。例えば戻した直後の q2 から QUORUM で読み、相手に q1 を選べば、q1 と q2 で値が違うと分かり、q2 に v2 が書き戻されます。エラーになった書き込みは、hint を待たなくても、v2 を持つ台を含めて誰かが QUORUM で読んだだけで、読んだ台へ広がることがあります。

<br>

エラーになった書き込みが広がると、成功した書き込みを消すこともあります。2013 年に Kyle Kingsbury 氏は、故障を注入して DB（データベース）の正しさを調べる [Jepsen](https://jepsen.io/) で、Dynamo に倣った [Riak](https://aphyr.com/posts/285-call-me-maybe-riak) を調べました。本来のレプリカから過半数の応答を求める設定でも、分断を起こしながら 1 つのキーに数を書き足すと、成功を返した 1,971 件のうち 1,807 件が失われました。

少数派で失敗した書き込みが一部のノードに残って読み取りの時に広がり、時刻の新しい方を残す規則で、多数派で成功した書き込みを上書きしたためです。分断の間も少数派の台には書き込みが届き続け、後から書いたものほど時刻が新しくなります。2,000 件を書いた別の試行で、後から必ず同じ結果に併合できるデータ型（[CRDT](https://crdt.tech/)）に任せると、2,000 件全てが残りました。

---

### WriteTimeout と Unavailable の違い

同じ QUORUM の書き込みでも、v3 は Unavailable で失敗し、どの台にも残りませんでした。

| エラー | 返るまで | coordinator が知っていたこと | 書き込み |
|---|---|---|---|
| WriteTimeout | 待つ時間の上限（既定 2 秒）の後 | 送った後に応答が足りなかった | 一部の台に残りうる |
| Unavailable | すぐ | 送る前に、生きている台が足りない | どの台にも送らない |

Unavailable は、coordinator が送る前に「過半数のレプリカが生きていない」と判断した時に返ります。cassandra-driver が再試行の方針を決める[ソースコード](https://github.com/datastax/python-driver/blob/3.29.2/cassandra/policies.py)の説明にも、Unavailable の時は読み書きがどのレプリカにも送られていない、と書かれています。

ただし、q1 が q2 を DOWN と判断したのは、止めてから約 20.6 秒後で、q3 はその 1 秒後でした。応答だけが止まったこの実験では、それまでの約 20 秒間、止まった台も生きていると見なされ、書き込みは送られてから WriteTimeout になります。そのため、障害の始まりでは、まず WriteTimeout が続き、判断が済んでから Unavailable に変わります。

止まった台と判断するまでの時間と、途絶えた応答が「止まった」とは限らない理由は、[Heartbeat](/notes/distributed-systems/heartbeat/) で扱っています。

---

### エラーになった書き込みの扱い

WriteTimeout は「失敗」ではなく、「成功したかどうか分からない」という結果です。アプリケーションは、成功・失敗に加えて、この 3 つ目の結果を扱う必要があります。

素直な対処は、同じ書き込みをもう一度送ることです。`UPDATE kv SET v = 'v2'` のように値を置き換える書き込みなら、2 回届いても結果は同じです。一方、カウンタを 1 増やす `SET c = c + 1` や、リストに足す書き込みは、1 回目が残っていれば 2 回分になります。

何度受け取っても 1 回分の結果に保つ設計は、[Idempotency](/notes/distributed-systems/idempotency/) で扱っています。再試行の間隔は [Retry and Backoff](/notes/distributed-systems/retry-backoff/) の考え方で決めます。

cassandra-driver 3.29.2 は、既定では WriteTimeout になった書き込みを再試行せず、エラーとしてアプリケーションに返します。以下は既定の方針（`RetryPolicy`）の抜粋で、再試行するのは、書き込みの種類（`write_type`）が `BATCH_LOG` で、しかも 1 回目のタイムアウトだけです。`BATCH_LOG` は、複数の書き込みをまとめる BATCH を実行する前に、その中身を記録しておく書き込みです。

```python
def on_write_timeout(self, query, consistency, write_type,
                     required_responses, received_responses, retry_num):
    if retry_num != 0:
        return self.RETHROW, None
    elif write_type == WriteType.BATCH_LOG:
        return self.RETRY, consistency
    else:
        return self.RETHROW, None
```

値を置き換える書き込みでも、再試行は時刻を新しく付け直すので、その間に別のクライアントが書いた値を古い値で上書きすることがあります。再試行するかどうかは、書き込みの中身を見てアプリケーションが決めることです。

<br>

<details><summary>余談: 2 秒で返る失敗を「失敗」と表示した場合</summary>

冒頭の実験で書いた v2 が注文の確定のような書き込みなら、利用者には「保存できませんでした」と表示したのに、止まった台が戻ると、その注文は全ての台から読めるようになります。利用者がもう一度注文すれば、注文は 2 件になります。Cassandra に限らず、応答を待つ時間に上限を設けた書き込みでは、同じことが起こりえます。[2PC](/notes/distributed-systems/two-phase-commit/) で、準備を終えた参加者が最終の決定を待ち続けるのも、成功したかどうか分からない状態を勝手に失敗と見なせないからです。

</details>

<br>

---

### Raft・Kafka・Aurora との比較

決めた数の応答で書き込みを成立させる仕組みは、Cassandra の他にもあります。

[Raft](https://raft.github.io/) は etcd などが使う合意アルゴリズムで、1 台の Leader が書き込みを受けます。Leader が今の任期に受けた書き込みは、Leader を含めて過半数の台が受け取った時点でコミットします。他の台から切り離された Leader への書き込みは、過半数に届かずにタイムアウトします。

その値が戻った後に新しい Leader の値で上書きされる様子は、[Leader and Followers](/notes/distributed-systems/leader-and-followers/) で実験しています。

逆に、過半数に届いただけでは、成功を返した書き込みが残るとは限りません。Leader を選び直した後、新しい Leader は自分のログで他の台を上書きするので、その書き込みを持たない台が Leader になれば消えます。

これを防ぐ規則が 2 つあります。投票する台は、自分よりログの古い候補には票を入れません。また、前の Leader が作った書き込みは、過半数の台に届いただけではコミットしません。[Raft の論文](https://raft.github.io/raft.pdf)は 5.4.2 節で、1 つ目の規則だけでは、前の任期に過半数へ載った書き込みが後から上書きされる筋書きを示しています。

<br>

#### Kafka の ISR

Kafka は過半数を使いません。メッセージをパーティションごとのログ（追記だけで書く記録）に書き、Leader に追いついているレプリカの集まり（ISR）を保ちます。`acks=all` の書き込みは、ISR の全てが受け取った時にコミットします。過半数なら f 台の故障に耐えるには 2f + 1 台が必要ですが、[設計の文書](https://kafka.apache.org/39/design/design/)にある通り、ISR なら f + 1 台で足ります。遅れた台を ISR から外すのは Leader、止まった台を外すのはコントローラーです。

ISR が小さくなりすぎないように、[`min.insync.replicas`](https://kafka.apache.org/39/generated/topic_config.html#topicconfigs_min.insync.replicas) で下限を決めます。既定は 1 で、典型はレプリカ 3 つ・下限 2・`acks=all` です。

Kafka にも、Cassandra と同じ 2 種類の失敗があります。[NotEnoughReplicas](https://kafka.apache.org/39/javadoc/org/apache/kafka/common/errors/NotEnoughReplicasException.html) は、ISR が下限を下回っていて書けなかった時のエラーです。[NotEnoughReplicasAfterAppend](https://kafka.apache.org/39/javadoc/org/apache/kafka/common/errors/NotEnoughReplicasAfterAppendException.html) は、ログに追記した後で ISR の不足に気づいた時のエラーで、説明には「再試行すると重複する」とあります。3 つを並べると次の通りです。

| 仕組み | 書き込みの成立 | 止まれる台 | 送る前に断る | 成功したか不明 |
|---|---|---|---|---|
| Cassandra の QUORUM | レプリカの過半数が応答 | 3 台で 1 台 | Unavailable | WriteTimeout |
| Raft（etcd など） | Leader を含む過半数 | 3 台で 1 台 | － | タイムアウト |
| Kafka の `acks=all` | ISR の全て | 下限を割るまで | NotEnoughReplicas | NotEnoughReplicasAfterAppend |

<br>

#### 過半数より大きい書き込みの数

[Amazon Aurora](https://aws.amazon.com/rds/aurora/) のストレージは、データを 3 つの AZ（Availability Zone、独立した設備の単位）に 2 つずつ、計 6 つ持ち、4 つで書き込み、3 つで読みます。4 + 3 > 6 なので、Dynamo と同じく読み書きが重なります。6 つにしたのは、AZ の障害では 1 つの AZ にあるコピーがまとめて失われるからだと、AWS の[ブログ](https://aws.amazon.com/blogs/database/amazon-aurora-under-the-hood-quorum-and-correlated-failure/)は説明しています。

3 つの AZ に 1 つずつ置いて過半数の 2 つで書く構成では、AZ を 1 つ失った後に別の AZ でも 1 台が止まると、残りは 1 つになって読めません。Aurora は、AZ 1 つに加えて、他の AZ にあるコピーを 1 つ失っても、残る 3 つで読み、失ったコピーを作り直せます。以下は、AZ を失った時に何台残るかの図です。

{{< figure src="images/quorum_aurora.webp" alt="左右 2 つの枠に、AZ 1・AZ 2・AZ 3 がそれぞれ 2 つのコピーを持つ図。左は AZ 1 の 2 つを失い、残り 4 つで書き込みも読み取りもできる。右は AZ 1 の 2 つと AZ 2 の 1 つを失い、残り 3 つで書けないが、読めて修復できる" caption="Aurora の 6 つのコピーと、AZ を失った時に残る数" align="center" >}}

<br>

Raft のように Leader を選んでから値を書く合意の方式でも、過半数は必須ではありません。2016 年の [Flexible Paxos](https://arxiv.org/abs/1608.06696) は、Raft より前からある合意アルゴリズム Paxos について、Leader を選ぶ時に集める台と、値を書く時に集める台が必ず重なれば足りることを示しました。台数を N として 2 つの数の合計が N を超えればよく、W + R > N と同じ形です。過半数は重なりを作る最も簡単な選び方で、必須の条件は重なることのほうです。

---

### 書き込みのエラーを見た時に確認すること

冒頭の WriteTimeout に出会った人も、これから台数を決める人も、確認することは 4 つです。

まず、エラーの種類を分けます。Unavailable はどの台にも送っていないので、失敗として扱えます。WriteTimeout は、冒頭の図で見た v2 のように、後から全ての台で読める値になりえます。cassandra-driver では、2 つは別の例外として届きます。

```python
from cassandra import Unavailable, WriteTimeout

try:
    session.execute(stmt)
except Unavailable:
    ...  # どのレプリカにも送られていない。失敗として扱える
except WriteTimeout as e:
    ...  # 少なくとも e.received_responses 台には残っている。成功したかどうかは分からない
```

この 2 つを同じ「失敗」としてログに出しているなら、分けて記録します。

次に、WriteTimeout の書き込みを再試行して良いかは、書き込みの中身で決めます。値の置き換えなら再試行できますが、増やす・足す書き込みは 2 回分になります。再試行できない書き込みは、要求ごとに一意な ID（冪等キー）を付けて受け取った側で重複を捨てるなど、2 回届いても 1 回分になる形に変えます。

再試行の前に QUORUM で読み直して、書いた値が見えれば、書き込みは残っています。見えなくても、残っていないとは言えません。冒頭の v2 のように 1 台にしか無い値は、読む台の選び方次第で見えず、後から hint で広がることもあるからです。

3 つ目に、読み取りと書き込みの consistency level の組み合わせが W + R > N を満たすかを見ます。例えば、書いた直後の値を読む必要がある所で ONE を使っていれば、古い値が返ります。満たす組み合わせは QUORUM どうしだけではなく、ALL で書いて ONE で読む組み合わせも 3 + 1 > 3 です。ただし、この組み合わせでは 1 台止まっただけで書き込みが全て失敗し、ONE で書いて ALL で読めば読み取りが全て失敗します。読み書きの両方が 1 台の障害に耐えるのは、QUORUM どうしの組み合わせです。

最後に、台数は奇数にし、Cassandra ならクラスタの台数ではなくレプリカの数で、何台まで止まれるかを数えます。

実験のスクリプトと出力の全体は [lab/](https://github.com/nao1215/debimate/tree/main/content/notes/distributed-systems/quorum/lab) にあります。
