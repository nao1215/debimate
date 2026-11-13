---
title: "Ambassador - localhost のプロキシに master の切り替えを任せると、書き込みは何秒止まり、何件消えるか"
date: 2026-08-08
draft: false
series: ["技術ノート", "Software Architecture"]
tags: ["software-architecture", "design-pattern"]
weight: 6
wrapTables: true
topics: ["Container Patterns"]
---

アプリの設定を開くと [Redis](https://redis.io/) の宛先が `127.0.0.1:6380` で、同じ Kubernetes の [Pod](https://kubernetes.io/docs/concepts/workloads/pods/) には [HAProxy](https://www.haproxy.org/) のコンテナが動いている。

Redis は、書き込みを受け付ける 1 台の master と、その複製を持ち読み取りだけを受ける replica に分けて組めます。この localhost のプロキシは、master が落ちて別のサーバーに切り替わった時、アプリの書き込みをどこまで守ってくれるのでしょうか。

手元で Redis 3 台と、master の死活を見て replica の 1 台を master に切り替える [Redis Sentinel](https://redis.io/docs/latest/operate/oss_and_stack/management/sentinel/) 3 台を動かし、100ms ごとに 1 回書くアプリを 4 通りの繋ぎ方で並べました。master のコンテナを止め、20 秒後に戻した結果が次の図です。

{{< figure src="images/ambassador_stop.webp" alt="横軸は master の redis-a を止めてからの秒で、4 つのアプリの結果を 100ms ごとのマスで並べた図。直接 IP に繋ぐアプリは 0.2 秒から 20.8 秒まで失敗し続け、a が戻った後の約 10 秒は成功と返るが 99 件すべてが消え、その後は READONLY で拒否される。ライブラリ（Sentinel）は 2.4 秒、ambassador（接続を保つ）は 1.7 秒、ambassador（毎回繋ぐ）は 2.2 秒で書けるようになる。ただし毎回繋ぐアプリは、a が戻ってから replica にされるまでの間、成功と消えたが交互に並び、48 件が消える" caption="master の redis-a を止めて 20 秒後に戻した時の、繋ぎ方ごとの書き込みの結果" align="center" >}}

図の `READONLY` は、replica が書き込みを拒否した時の応答です。図の ambassador は localhost のプロキシで、これを通した 2 つのアプリは、ライブラリと同じく約 2 秒で書けるようになりました。

ところが書くたびに接続を繋ぎ直すアプリは、止めた redis-a が戻って送り先に入った 21.0 秒から、replica にされた 30.7 秒までの約 10 秒間に「成功」と返った 97 件のうち、48 件が最後の master に残っていませんでした。

アプリと同じ実行単位に置き、アプリの代わりに外のサービスと話すプロキシのコンテナを Ambassador と呼びます。実行単位は、まとめて作られ消されるコンテナの集まりで、Kubernetes の Pod や Amazon ECS の [Task](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definitions.html) です。アプリは localhost の 1 つの宛先にだけ繋ぎ、相手が何台あるのか、どれに送るのかは ambassador が決めます。Google Cloud の [Cloud SQL Auth Proxy](https://cloud.google.com/sql/docs/mysql/connect-kubernetes-engine) や、Pod ごとに置く [PgBouncer](https://www.pgbouncer.org/)・[Envoy](https://www.envoyproxy.io/) のように、既存のシステムで出会うことの多い構成です。

<br>

本記事では、ambassador をこれから置く人と、既存のシステムで出会った人に向けて、次の疑問に答えます。

- localhost の先には何があり、アプリから何が見えなくなるのか。
- master が落ちた時、書き込みは繋ぎ方ごとに何秒止まるか。
- ambassador 経由で成功した書き込みが消えるのは、どんな時か。
- master を止めずに切り替えた時は、何が起きるか。
- 消さないための設定は、何と引き換えになるか。

---

### localhost の先にあるもの

以下は、実験の構成を描いた図です。点線の枠は、ネットワークを共有するコンテナの単位で、Kubernetes では Pod がこの単位です。

{{< figure src="images/ambassador_concept.webp" alt="点線の枠の中にアプリと ambassador（HAProxy）の 2 つの箱がある。アプリの宛先は 127.0.0.1:6380 で、localhost の矢印で ambassador に繋がる。ambassador からは書き込みの実線が master の redis-a へ、1 秒ごとの role:master の確認の点線が redis-a・b・c の 3 台へ伸びる。右の Sentinel × 3 は 3 台の Redis を見て、落ちたと決めて昇格させる" caption="アプリと ambassador がネットワークを共有し、localhost の先で master を選ぶ構成" align="center" >}}

同じ Pod のコンテナは、Linux が IP アドレスやポートを分ける単位であるネットワーク名前空間を共有します。そのため、アプリは `127.0.0.1` で隣の ambassador に届きます。

どの実行基盤でもそうなるわけではありません。Amazon ECS で EC2 に置く Linux コンテナは、既定が [bridge モード](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-networking.html)で、同じ Task のコンテナもそれぞれ別のアドレスを持ちます。その場合、アプリは ambassador のアドレスを探して設定に持つ必要があります。Kubernetes が 2015 年に公開したブログ「[The Distributed System ToolKit](https://kubernetes.io/blog/2015/06/the-distributed-system-toolkit-patterns/)」が ambassador の例に挙げたのも、この Redis の構成でした。

ブログの説明では、master と読み取り用の replica からなる Redis の前に ambassador を置けば、アプリは「localhost の Redis」に繋ぐだけで済みます。開発環境では ambassador を外し、同じ localhost のポートで手元の Redis に直接繋げます。宛先が変わらないので、コードも設定も変えずに相手だけを差し替えられ、アプリを単体でテストできます。

ambassador がアプリから隠すのは、相手の台数と、どれが master かという判断です。同じ判断は、アプリに入れるライブラリにも任せられます。Redis では Sentinel に master の場所を聞くクライアントライブラリが各言語にあり、実験では Python 向けの [redis-py](https://github.com/redis/redis-py) が持つ `Sentinel` を使いました。3 つの繋ぎ方の違いは次の通りです。

| 繋ぎ方 | アプリが知る宛先 | master を選ぶもの | 言語ごとの実装 |
|---|---|---|---|
| 直接 IP | master の IP | 誰も選ばない | 不要 |
| ライブラリ | Sentinel の一覧 | ライブラリ | 言語の数だけ必要 |
| ambassador | localhost | ambassador | 1 つで済む |

ambassador の強みは最後の列です。Go と Python と Ruby のアプリが同じ Redis を使っていても、HAProxy の設定は 1 つで済み、アプリのコードに Sentinel は出てきません。

ただし、ambassador を置けば切り替えに追随できるわけではありません。Burns 氏らが 2016 年に出した[論文](https://www.usenix.org/conference/hotcloud16/workshop-program/presentation/burns)が 4.2 節で ambassador の例に挙げた [twemproxy](https://github.com/twitter/twemproxy) は、[memcached](https://memcached.org/) や Redis への要求を複数台に分けるプロキシで、master の切り替わりを見る機能は持ちません。

追随するかどうかは、ambassador の実装と設定で決まります。追随しない実装でも、宛先を書き換える場所はアプリから ambassador の設定に移るので、アプリのコードには触れずに済みます。

一方で、どれが master かを選ぶ根拠は、ambassador の health check に移ります。実験の HAProxy は、各 Redis に `INFO replication` を送り、応答に `role:master` が含まれるサーバーにだけ送ります。

```text
backend redis_master
    option tcp-check
    tcp-check send PING\r\n
    tcp-check expect string +PONG
    tcp-check send info\ replication\r\n
    tcp-check expect string role:master
    tcp-check send QUIT\r\n
    tcp-check expect string +OK
    server redis-a 172.28.0.11:6379 check inter 1s fall 1 rise 1
    server redis-b 172.28.0.12:6379 check inter 1s fall 1 rise 1
    server redis-c 172.28.0.13:6379 check inter 1s fall 1 rise 1
```

`inter 1s fall 1 rise 1` は、1 秒ごとに確認し、1 回失敗したら外し、1 回通ったら戻す設定です。冒頭の図では、4 段目で書き込みが消えていました。この確認が「自分は master だ」と答えるサーバーを全て信じるからです。それを見るために、実験の組み方を先に示します。

<br>

<details><summary>余談: Ambassador という名前</summary>

ambassador は大使の意味で、外との交渉をアプリの代わりに引き受ける役を指しています。上のブログを書いた Brendan Burns 氏らは、翌年の論文「Design Patterns for Container-based Distributed Systems」でも、同じ Pod に置く補助コンテナを [Sidecar](../sidecar/)・Ambassador・[Adapter](../adapter/) の 3 つに分けています。

論文は 4.2 節で、メインのコンテナに向かう通信とそこから出る通信を仲介するコンテナを Ambassador と定義しています。4.3 節の Adapter との対比では、Ambassador はアプリに外の世界を単純化して見せ、Adapter は外の世界にアプリを揃えて見せます。

Microsoft の設計パターン集にも [Ambassador パターン](https://learn.microsoft.com/ja-jp/azure/architecture/patterns/ambassador)として載っています。似た名前の Ambassador Labs の API ゲートウェイ（今の Emissary-ingress）は製品の名前で、本記事のパターンとは別物です。

</details>

<br>

---

### 実験の組み方

[Docker Compose](https://docs.docker.com/reference/compose-file/services/) で Redis 3 台と Sentinel 3 台を動かし、最初の master は redis-a にしました。Sentinel は、master が 1 秒応答しなければ落ちたとみなし、3 台のうち 2 台が同意すると replica の 1 台を master に昇格させます。

ambassador の HAProxy は `network_mode: "service:writer-ambassador"` でアプリのコンテナとネットワークを共有させ、Pod と同じく localhost で届くようにしました。

```yaml
  writer-ambassador:
    build: .
    environment: { MODE: ambassador }
    networks: { lab: { ipv4_address: 172.28.0.33 } }
  ambassador:
    image: haproxy:3.0.5-alpine
    network_mode: "service:writer-ambassador"
    volumes: ["./haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro"]
```

アプリは、通し番号を 100ms ごとに 1 回 `RPUSH` するだけの Python のプログラムで、`MODE` で繋ぎ方を変えます。redis-py が既定で行う再試行は切り、1 回の失敗をそのまま 1 マスに数えます。

```python
import json, os, time
import redis
from redis.sentinel import Sentinel

mode = os.environ["MODE"]
opts = dict(socket_timeout=0.5, socket_connect_timeout=0.5, retry=None)
if mode == "static":
    r = redis.Redis(host="172.28.0.11", port=6379, **opts)
elif mode == "sentinel":
    s = Sentinel([("172.28.0.21", 26379), ("172.28.0.22", 26379), ("172.28.0.23", 26379)],
                 socket_timeout=0.5)
    r = s.master_for("mymaster", **opts)
else:
    r = redis.Redis(host="127.0.0.1", port=6380, **opts)

out = open(f"/out/{mode}.jsonl", "w", buffering=1)
seq = 0
while True:
    t0 = time.time()
    seq += 1
    err = ""
    try:
        r.rpush(f"log:{mode}", seq)
        res = "ok"
    except redis.exceptions.ReadOnlyError as e:
        res, err = "readonly", str(e)
    except redis.exceptions.TimeoutError as e:
        res, err = "timeout", str(e)
    except redis.exceptions.ConnectionError as e:
        res, err = ("readonly" if "slave" in str(e) or "replica" in str(e) else "conn"), str(e)
    except redis.exceptions.RedisError as e:
        res, err = type(e).__name__, str(e)
    finally:
        if mode == "ambassador_new":
            r.connection_pool.disconnect()   # 次の書き込みは新しい接続になる
    out.write(json.dumps({"t": t0, "seq": seq, "res": res, "err": err[:80], "ms": round((time.time() - t0) * 1000)}) + "\n")
    time.sleep(max(0, 0.1 - (time.time() - t0)))
```

`ambassador` と `ambassador_new` は同じ HAProxy に繋ぎ、違いは接続を張ったままにするか、書くたびに切るかだけです。最後に、Sentinel が master と答えるサーバーから `LRANGE` で一覧を読み、「成功」と返った通し番号がそこに無ければ「消えた」と数えます。Compose の全体・実行用のスクリプト・出力は [lab/](https://github.com/nao1215/debimate/tree/main/content/notes/software-architecture/ambassador/lab) にあります。

---

### master が落ちた時

冒頭の図で 0 秒から 20 秒までは、redis-a のコンテナを止めたままの区間です。`summarize.py` で、結果が変わった所だけを並べると次の通りでした。

```text
-- static
   0.23s〜 20.77s  timeout   x41
  20.77s〜 30.68s  ok        x99  うち消えた 99
  30.68s〜 35.55s  readonly  x49
-- sentinel
   0.18s〜  1.69s  timeout   x3
   1.69s〜  2.39s  conn      x7
   2.39s〜 35.55s  ok        x332
-- ambassador
   0.21s〜  1.71s  timeout   x3
   1.71s〜 35.55s  ok        x339
```

Sentinel は 1.3 秒で redis-a が落ちたと決め、2.4 秒で redis-c を新しい master として知らせました。ライブラリは接続が切れるたびに Sentinel に master を聞き直すので、2.4 秒で redis-c に書けるようになっています。

HAProxy は 1.6 秒の確認で、redis-c が `role:master` を返したことを見つけました。Sentinel は redis-c を昇格させた後、昇格したことを自分でも確認してから新しい master を知らせるので、知らせは昇格より遅れます。HAProxy は、その知らせより先に昇格した redis-c を見つけたことになります。接続を保つアプリは 1.7 秒で書けるようになっています。直接 IP を書いたアプリは、止まった redis-a に 0.5 秒の時間切れを繰り返すだけで、切り替わったことを知る手段がありません。

この区間では、ambassador はライブラリと同じ働きをしています。master の場所をアプリの外で決め、アプリは localhost に繋ぎ直すだけで済みました。

<br>

#### 戻ってきた古い master

20.3 秒に redis-a を戻すと、話が変わります。redis-a は止められる前の設定のまま、master として起動しました。Sentinel はすぐには replica に戻さず、redis-a が replica にされたのは戻ってから約 10 秒後でした。

[Sentinel の実装](https://github.com/redis/redis/blob/7.4.1/src/sentinel.c#L2682-L2696)を読むと、replica のはずのサーバーが master を名乗った時は、新しい設定が届くのを待つため、`sentinel_publish_period*4`（既定で 8 秒）の間は手を出しません。その約 10 秒、HAProxy の確認には redis-a も redis-c も `role:master` と答えます。HAProxy のログには、2 台とも送り先に入った様子が残っていました。

```text
 21.04s  Server redis_master/redis-a is UP
 32.06s  Server redis_master/redis-a is DOWN
```

HAProxy は、送り先が 2 台あれば新しい接続を順に振り分けます。ログの 21.0 秒から 32.1 秒までの 11 秒間、書くたびに繋ぎ直すアプリの書き込みは、redis-c と redis-a に交互に届きました。redis-a に届いた分も redis-a は受け付けますが、redis-a が replica にされた時に redis-c の内容で上書きされ、消えます。冒頭の図で、4 段目の赤と灰が縞になっている所です。

30.7 秒に redis-a が replica にされた後も、HAProxy が redis-a を外す 32.1 秒までは、redis-a に届いた書き込みが `READONLY` で拒否されます。4 段目の最後に黄色の縞が続くのは、この 1.4 秒です。

接続を保つアプリは、その接続が redis-c に張られたままだったので、1 件も消えませんでした。同じ ambassador でも、アプリが接続を使い回すかどうかで結果が分かれます。

直接 IP のアプリは、戻ってきた redis-a に 99 件を書き、全てを失いました。古い master が戻ってきて書き込みを受け付けてしまう問題は、ambassador に限らず、[Leader and Followers](/notes/distributed-systems/leader-and-followers/) で扱う古い Leader の締め出しと同じ形です。

---

### 止めずに切り替えた時

次は redis-a を止めず、Sentinel に `SENTINEL FAILOVER` を送って、手で master を切り替えました。メンテナンスで master を移す時の操作です。以下は、各 Redis の役割と HAProxy の送り先、消えた書き込みの数を時刻に沿って再生した図です。

{{< figure src="images/ambassador_failover_anim.webp" alt="動く図。0 秒で切り替えを指示すると、0.3 秒で redis-b が master になるが、redis-a も master のまま書き込みを受け付ける。Sentinel が知らせる master は 6.2 秒まで a のまま。HAProxy の送り先は 1.3 秒から a と b の 2 台になり、13.1 秒で b だけになる。redis-a は 11.3 秒で replica にされ、それまでに成功と返った書き込みのうち、直接 IP・ライブラリ・接続を保つ ambassador の 3 つは約 110 件、毎回繋ぐ ambassador は 60 件が消える" caption="止めずに master を切り替えた時の、役割と消えた書き込みの数（実測の時刻を等倍速で再生）" align="center" >}}

今度はライブラリも含めて、redis-a に繋がっていた 3 つのアプリが、11.3 秒までに約 110 件を失いました。redis-b は 0.3 秒で master になりましたが、redis-a は自分がもう master ではないことを知らされず、書き込みを受け付け続けます。Sentinel が redis-a を replica にして、つないでいたクライアントを切ったのは 11.3 秒です。

ライブラリが助けにならなかったのは、redis-py が Sentinel に master を聞き直すのが、接続が切れた時と `READONLY` を受けた時だけだからです。Redis が示す[クライアントの指針](https://redis.io/docs/latest/develop/reference/sentinel-clients/)も、master を Sentinel に聞くのは繋ぎ直す時としていて、構成が変わった時は Sentinel がクライアントの接続を切って聞き直させます。この実験では、その切断が 11.3 秒まで来ませんでした。redis-a が何も言わずに受け付ける限り、どの繋ぎ方でも書き込みは redis-a に届きます。

<br>

#### READONLY のまま戻らない ambassador

接続を保つ ambassador のアプリは、11.3 秒以降も `READONLY` で拒否され続け、20 秒の終わりまで書けませんでした。

```text
-- ambassador
  -0.99s〜 11.32s  ok        x123  うち消えた 110
  11.32s〜 20.16s  readonly  x89
```

redis-a が replica にされた時、Sentinel は redis-a に繋がる接続を切ります。HAProxy はアプリとの接続も閉じ、アプリは localhost に繋ぎ直します。ところが HAProxy が redis-a を送り先から外したのは 13.1 秒で、繋ぎ直した 11.3 秒の時点では、redis-a はまだ送り先に残っていました。

実験では、繋ぎ直した接続が redis-a に振り分けられ、その接続は HAProxy が redis-a を外した後もそのまま残りました。HAProxy は既定では、外したサーバーにつないだままの接続を切らないからです。アプリは redis-py で普通に作ったクライアントなので、`READONLY` を受けても接続を切らず、同じ接続で書き続けます。

この結果は、張ったままの接続がどのサーバーに振り分けられたかで決まります。HAProxy は起動した直後、最初の確認が済むまで 3 台とも送り先に入れて順に振り分けるので、最初の接続がどのサーバーに張られるかは、その順番次第です。本記事に載せた回では最初の接続が redis-a に張られていました。同じ実験をもう一度回すと、最初の接続が replica の redis-c に振り分けられました。その回は Sentinel が redis-c を新しい master に選んだので、1.4 秒まで `READONLY` で拒否された後は最後まで書けて、消えた書き込みは 0 件でした。

---

### 消さないための設定と、その引き換え

ここまでの 2 つの問題には、それぞれ設定があります。HAProxy の [on-marked-down shutdown-sessions](https://docs.haproxy.org/3.0/configuration.html#5.2-on-marked-down) は、サーバーを送り先から外した時に、そのサーバーへの接続を全て切ります。Redis の [min-replicas-to-write](https://redis.io/docs/latest/operate/oss_and_stack/management/replication/) は、繋がっている replica が指定の数より少ない master に、書き込みを拒否させます。

止めずに切り替える実験を設定ごとに繰り返した結果が、次の図です。

{{< figure src="images/ambassador_failover.webp" alt="止めずに切り替えた時の書き込みの結果を設定ごとに 3 段に並べた図。HAProxy の設定のままでは、3 つのアプリが約 110 件、毎回繋ぐ ambassador が 60 件を失い、接続を保つ ambassador は 11.3 秒以降 READONLY のまま。on-marked-down shutdown-sessions を付けると、接続を保つ ambassador は 11.3 秒以降も書けるが、消えた数は変わらない。min-replicas-to-write 1 では、消えた数は 4 つとも 9 件になり、代わりに約 1.3 秒から最大 11 秒の間、NOREPLICAS で拒否される" caption="止めずに切り替えた時の、設定ごとの書き込みの結果" align="center" >}}

shutdown-sessions を付けると、接続を保つ ambassador は redis-a が replica にされた後も書けるようになりました。ただし、消えた数は 110 件のままです。切れた接続を張り直す先が正しくなるだけで、redis-a が master のふりを続けた 11 秒の書き込みは守れません。

min-replicas-to-write 1 を付けると、消えた数は 4 つのアプリとも 9 件に減りました。切り替えで replica が redis-a から離れると、redis-a は replica を 1 台も持たない master になり、書き込みを `NOREPLICAS` で拒否するからです。残った 9 件は、新しい master が書き込みを受け始めた 0.3 秒から、残りの replica も redis-a から離れるまでの約 1 秒に書いたものです。

ライブラリと接続を保つ ambassador に絞って、3 回の結果を並べると次の通りです。

| 設定 | 消えた数 | ライブラリが書けなかった秒 | 接続を保つ ambassador |
|---|---|---|---|
| 設定のまま | 約 110 | 0 | 11.3 秒から READONLY のまま |
| shutdown-sessions | 約 110 | 0 | 書き続ける |
| min-replicas-to-write 1 | 9 | 約 10 | 1.3 秒から拒否が続く |

その代わり、消えるはずだった書き込みは失敗として返ります。ライブラリのアプリは 1.3 秒から 11.4 秒まで、`NOREPLICAS` で書けませんでした。redis-py は `READONLY` では Sentinel に聞き直しますが、`NOREPLICAS` では聞き直さないので、redis-a が replica にされるまで待たされます。

接続を保つ ambassador のアプリも、1.3 秒から `NOREPLICAS` で拒否されました。11.3 秒に redis-a が replica にされた後は、設定のままの時と同じく `READONLY` に変わり、最後まで戻りません。繋ぎ直した接続が、まだ送り先に残っていた redis-a に振り分けられ、そのまま残ったからです。

Sentinel の[ドキュメント](https://redis.io/docs/latest/operate/oss_and_stack/management/sentinel/)も、この設定には引き換えがあると書いていて、replica が全て止まると master も書き込みを止めます。同じドキュメントは、Redis と Sentinel の組み合わせでは、成功と返した書き込みを失う時間の幅が常に残るとも書いています。複製が非同期で、最後に切り替えた方の内容で上書きするからです。

ambassador の設定で直せたのは、接続の張り直しだけでした。消えるかどうかは、どのサーバーが自分を master と信じているかで決まり、それを正すのは Redis と Sentinel です。

---

### ambassador に出会った時に確認すること

設定ファイルに localhost の宛先を見つけた時に確認することは、4 つあります。

最初に、ambassador の health check が何を見ているかを読みます。実験の `role:master` のように、各サーバーの自己申告だけで選んでいるなら、古い master が戻った時や、止めずに切り替えた時に、送り先が 2 台になります。冒頭の図で 4 段目の縞が出たのは、送り先が 2 台になった 11 秒の間でした。

次に、送り先から外したサーバーにつないだままの接続がどうなるかを見ます。HAProxy の既定では切らないので、接続を保つアプリは古いサーバーに繋がったまま残ります。`on-marked-down shutdown-sessions` が無ければ、付けるかどうかを決めます。

アプリでは、接続を使い回すのか、要求のたびに繋ぐのかを見ます。同じ ambassador でも、冒頭の図では使い回すアプリが 0 件、繋ぎ直すアプリが 48 件を失いました。どちらが安全かは場面で入れ替わり、止めずに切り替えた時は、使い回すアプリの方が `READONLY` のまま戻りませんでした。

書き込みを失って良いかも決めます。キャッシュなら、消えても次の読み込みで作り直せます。消えて困るなら、ambassador ではなく Redis に `min-replicas-to-write` を付け、切り替えの間は書き込みが失敗として返ることを受け入れます。

実験で付けた設定は、HAProxy と Redis でそれぞれ次の通りです。

```text
# HAProxy（server の行ごと）
server redis-a 172.28.0.11:6379 check inter 1s fall 1 rise 1 on-marked-down shutdown-sessions
# Redis（master になり得る全てのサーバー）
min-replicas-to-write 1
min-replicas-max-lag 10
```

`min-replicas-max-lag 10` は、繋がっている replica として数える条件で、最後の応答から 10 秒以内のものだけを数えます。

失敗を受けたアプリは [Retry and Backoff](/notes/distributed-systems/retry-backoff/) の考え方で間隔を空けて送り直します。`INCR` のように値を増やす操作は、1 回目が実は成功していると送り直しで二重に増えるので、[Idempotency](/notes/distributed-systems/idempotency/) で 1 回分に保ちます。

送り直しを ambassador に任せる設定もあります。その場合、ambassador が送り直したことはアプリから見えず、`INCR` が二重に増えても、アプリは 1 回分の成功しか受け取りません。

ambassador は届いた要求が送り直して良い操作かを知らないので、送り直す条件はアプリが伝えます。例えば Envoy は、要求の [x-envoy-retry-on](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/router_filter#x-envoy-retry-on) ヘッダーで、その要求を送り直す条件を指定できます。

<br>

#### ambassador を置く前に

これから置くなら、まず ambassador が必要かを考えます。言語が 1 つで、そのクライアントが Sentinel に対応しているなら、ライブラリでも冒頭の図と同じく約 2 秒で書けるようになりました。ambassador が効くのは、言語が多い時や、TLS や[接続の束ね方](/notes/database-systems/connection-pool/)を 1 か所に寄せたい時です。

相手のプロトコルを扱える ambassador があるかも見ます。実験の HAProxy が master を選べたのは、Redis に `INFO replication` を送って応答を読めたからです。中身を見て選ぶ処理や読み書きの振り分けは、ambassador が対応するプロトコルに限られ、独自のプロトコルで話す相手には使えません。

ambassador を置くと、経路が 1 段増える分の遅延と、Pod ごとに動く分のメモリと CPU が掛かります。その分を嫌ってマシンごとに 1 つだけ置く構成も採れますが、localhost で届く前提が外れ、その ambassador が止まると同じマシンで動く全てのアプリが外と話せなくなります。障害を調べる時、アプリのログに残る宛先は `127.0.0.1:6380` だけで、実際にどのサーバーに書いたかは ambassador のログを見ます。

<br>

#### ambassador が止まった時と起動の前

ambassador が止まれば、アプリは外と話せません。起動の前も同じです。Pod ごとにプロキシを置く [Istio](https://istio.io/) は、アプリの通信を[横取りして](https://docs.cloud.google.com/service-mesh/docs/troubleshooting/troubleshoot-proxy)プロキシに通すので、localhost で呼ぶ ambassador とは繋ぎ方が違いますが、通信がプロキシを通る点は同じです。

その Istio で、アプリのコンテナがプロキシより先に動き出すと、外への単純な通信まで失敗する[報告](https://github.com/istio/istio/issues/11130)がありました。後からコンテナに入って試すと繋がるため、気付くまで数日掛かったユーザーもいます。

Istio は 1.7 でプロキシの準備を待たせる holdApplicationUntilProxyStarts が[入りました](https://istio.io/latest/news/releases/1.7.x/announcing-1.7/change-notes/)。アプリより先に ambassador を起動させる設定と、その実験は [Sidecar](/notes/software-architecture/sidecar/) にまとめています。
