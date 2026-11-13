---
title: "Feature Flag - hash() で 10% に出す判定は、3 台のサーバーで 28% のユーザーの答えを変えた"
date: 2026-08-17
draft: false
series: ["技術ノート", "Software Architecture"]
tags: ["software-architecture", "design-pattern"]
weight: 11
wrapTables: true
topics: ["Release / Migration"]
---

まず 10% のユーザーにだけ、新しい決済画面を出すことにしました。Python で次の判定を書き、同じコードを 3 台のサーバーに置きます。

```python
def is_on(user_id: str) -> bool:
    return hash(user_id) % 100 < 10
```

3,000 人のユーザーが、ロードバランサーを通して 6 回ずつ画面を開いたとします。6 回の中で、新しい画面と今の画面が入れ替わったユーザーは何人いるでしょうか。

手元のマシンで、別々に起動した 3 つのサーバーのプロセスを 3 台に見立てて測ると、842 人（28.1%）でした。どのサーバーも 10% 前後のユーザーに新しい画面を出していて、サーバーごとの割合だけを見ると問題はありません。以下は、サーバーの置き方と、判定に使うハッシュ関数を変えて測った結果です。下の 2 段の crc32 は、どのプロセスで計算しても同じ値を返すハッシュ関数です。

{{< figure src="images/feature-flag_flicker.webp" alt="5 つの構成の比較。左はプロセスごとに新しい画面を出した割合で、どの構成も 9.2% から 10.8% の間に並ぶ。右は 6 回の中で答えが変わったユーザーの割合で、3 台のサーバーに hash() を置いた構成が 28.1%、uvicorn --workers 3 に hash() を置いた構成が 25.5%。gunicorn -w 3 に hash() を置いた構成と、crc32 を使った 2 つの構成は 0.0%" caption="どのプロセスも約 10% に出しているのに、答えが変わるユーザーが出る構成がある" align="center" >}}

図の 2 段目は、Python の Web サーバーの uvicorn で、リクエストを処理するプロセス（worker）を 3 つ起動しただけの構成で、マシンは 1 台でも 25.5% のユーザーの答えが変わりました。一方で gunicorn は、同じ 3 プロセスでも 0% です。この差は、hash() の結果がプロセスごとに違うかどうかから来ています。

冒頭の判定のように、デプロイしたコードの中で、新しい機能を有効にするかを実行時に決める仕組みを Feature Flag と呼びます。Feature Toggle とも呼びます。コードを本番に置くデプロイと、ユーザーに見え始める公開を切り離すのが役目です。新しい機能を無効のままデプロイし、社内のユーザーや一部のユーザーから順に有効にし、問題があれば無効へ戻します。そのため、割合で出す判定を自分で書く時も、フラグの管理サービスを選ぶ時も、問われるのは「同じユーザーに、どのサーバーも同じ答えを返すか」です。

<br>

本記事では、Feature Flag をこれから入れる人と、既存のコードで大量のフラグに出会った人に向けて、次の疑問に答えます。

- Feature Flag は、設定ファイルや環境変数と何が違うのか。
- 「10% のユーザーに出す」は、どう決まるのか。
- hash() の答えは、なぜプロセスごとに変わるのか。
- 2 つのフラグを同時に 10% で出すと、誰に当たるのか。
- 使い終えたフラグを残すと、何が起きるのか。

実験は、1 台のマシンで Python 3.14.4・uvicorn 0.38.0・gunicorn 23.0.0 を動かしました。

---

### 設定ファイルや環境変数との違い

Feature Flag の中身は、新旧の処理を分ける if 文です。違いが出るのは、if 文が読む値をどこに置き、いつ変えられるかです。

| 値の置き場所 | 切り替えに必要な操作 | ユーザーごとの切り替え |
|---|---|---|
| コードの定数 | 再デプロイ | 自分で書く |
| 環境変数・設定ファイル | 再起動か再読み込み | 自分で書く |
| フラグを管理するサービス | 管理画面の操作 | 割合・属性の規則がある |

環境変数や設定ファイルの値は、そのプロセスが受けた全てのユーザーに同じです。ユーザーごとに答えを変えるには、冒頭の `is_on()` のように、ユーザーの ID などを受け取って答えを出す関数が必要です。

全てのフラグに管理サービスが必要なわけではありません。Hacker News で 99 points を集めた「[It's OK to hardcode feature flags](https://code.mendhak.com/hardcode-feature-flags/)」は、起動時に JSON を読むだけのフラグなら、変更が普段のレビューとデプロイを通るので単純で安全だと主張しています。

後で紹介する Pete Hodgson 氏の記事も、性質が許すならフラグの値をソース管理に置き、再デプロイで変える形を勧めています。リリースごとに値が決まるので、試験する組み合わせが減るからです。全員を一度に切り替えるだけなら表の 1・2 行目で足り、割合やユーザーの属性で分ける時に、3 行目が持つ規則が効きます。再デプロイ無しで戻せるのも、3 行目のように実行中に値を変えられる構成の時だけで、1 行目の定数なら再デプロイ、2 行目なら再起動か設定の再読み込みが要ります。

<br>

#### 管理サービスと OpenFeature

フラグを管理するサービスの [LaunchDarkly](https://launchdarkly.com/) や、OSS の [Unleash](https://www.getunleash.io/)・[Flipt](https://www.flipt.io/) は、ユーザーを受け取って答えを出す関数を SDK として持ち、割合や属性の規則を管理画面から変えられるようにした製品です。

サービスごとに SDK の API が違うので、アプリケーションのコードを特定の製品に縛らないための共通の API として [OpenFeature](https://openfeature.dev/) があります。OpenFeature の API を各製品の SDK につなぐ部品は、製品ごとに用意する [Provider](https://openfeature.dev/specification/sections/providers/) です。

ただし、共通になるのは呼び出し方だけです。フラグの設定や割合の規則、番号の出し方は、OpenFeature を通しても別の製品へは移りません。後の節で見るように Unleash と LaunchDarkly では番号の出し方が違うので、製品を替えると、同じ 10% でも選ばれる人が変わります。

<br>

#### フラグの寿命

martinfowler.com に Pete Hodgson 氏が書いた「[Feature Toggles (aka Feature Flags)](https://martinfowler.com/articles/feature-toggles.html)」は、フラグを目的で 4 つに分けています。種類によって、消すまでの期間が大きく違います。

| 種類 | 目的 | 寿命 |
|---|---|---|
| Release Toggle | 作りかけの機能を公開まで隠す | 多くは 1〜2 週間ほど |
| Experiment Toggle | A/B テストで利用者を分ける | 結果が出るまで |
| Ops Toggle | 障害や高負荷の時に機能を切る | 多くは短命。長く残すものもある |
| Permissioning Toggle | 有料プランなど権限で機能を分ける | 長いと数年 |

Ops Toggle のうち長く残すものは、停止用のスイッチ（Kill Switch）として使われます。

Release Toggle があると、未完成の機能も無効のまま main に毎日統合でき、長く続くブランチの統合が公開の直前に集中することを避けられます。問題が出た時も、フラグだけを無効にすれば戻せるので、同じビルドに入った別の変更まで再デプロイで戻さずに済みます。ライブラリの更新や、DB のスキーマを変える場合のように、if 文で囲めない変更は、フラグでは一部のユーザーにだけ出せません。そうした変更を顧客の組ごとに順に出す方法は、[Cell-based Architecture](/notes/software-architecture/cell-based-architecture/) の段階的なデプロイが扱っています。

本記事が扱う割合で出すフラグは、主に Release Toggle と Experiment Toggle です。どちらも使い終えたら消す前提のフラグで、消さずに残すと何が起きるかは、後の節で実際の事故を見ます。

<br>

#### 評価に失敗した時の答え

フラグの答えを出す処理を評価と呼びます。OpenFeature が定める[評価の仕様](https://openfeature.dev/specification/sections/flag-evaluation/)では、評価の途中で異常が起きた時、呼び出す側が渡した既定値がそのまま答えになります。既定値を有効と無効のどちらにするかは、フラグごとに決める必要があります。新しい処理を出すフラグなら無効が安全です。一方で、Kill Switch のように有効にすると重い機能を止めるフラグで既定値を無効にすると、管理サービスに繋がらない時は機能を止められません。

---

### 10% に入る人の決め方

割合で出すフラグには、3 つの要件があります。同じユーザーには、どのリクエストでも、どのサーバーでも同じ答えを返すこと。割合を 10% から 20% に上げた時に、10% の時に入っていた人が外れないこと。別のフラグとは、互いに関係無く人を選ぶことです。

`random.random() < 0.1` のようにリクエストごとに乱数を引くと、1 つ目の要件が崩れ、同じユーザーの画面が開くたびに変わります。影響する人数も、割合どおりにはなりません。1% で出した時、10 回開く人が 10 回とも外れる確率は 0.99¹⁰ ≈ 0.904 なので、約 9.6% の人が少なくとも 1 回は新しい画面に当たります。1% で様子を見ているつもりでも、不具合に当たる人は約 10 倍に広がります。

そこで、ユーザーの ID をハッシュ関数に通し、0〜99 の番号を 1 つ決めて、その番号が割合より小さい人だけを有効にします。この番号は、管理サービスの文書ではバケット（bucket）と呼ばれます。番号は ID だけで決まるので、何回聞いても同じで、割合を上げると線を右へ動かすだけになります。

{{< figure src="images/feature-flag_bucket.webp" alt="30 人のユーザーを 0 から 99 の数直線に置いた 4 段の図。1 段目は crc32 で番号を出して 10 未満を有効にし、2 人が黒。2 段目は同じ番号のまま線を 20 に動かし、1 段目の 2 人に加えて 4 人が黒になり、外れた人はいない。3 段目は hash() で番号を出して 10 未満を有効にし、5 人が黒。4 段目は hash() を再起動の後に出し直したもので、番号の並びが全て変わり、3 段目で黒だった 5 人は全員が線の外に移って赤い縁の白になり、別の 2 人が黒になった。番号が同じか隣り合う人は上下にずらして置いた" caption="ユーザーに付いた番号と、有効にする範囲。hash() の段は、起動時に混ぜる乱数を 2 通りに固定して実際の値を使った" align="center" >}}

上の 2 段は、番号の出し方が変わらないので、線を 20 に動かしても 10% の時の 2 人は残ります。下の 2 段は、番号の出し方が起動のたびに変わる場合で、同じ 10% でも別の人が選ばれます。3 段目で有効だった 5 人は、再起動の後は全員が無効になりました。番号が同じか隣り合う人は、上下にずらして描いています。冒頭の 3 台のサーバーは、この 3 段目と 4 段目が同時に動いている状態です。

増やした時に動く人を少なくする考え方は、サーバーを足した時に移るデータを減らす [Consistent Hashing](/notes/distributed-systems/consistent-hashing/) と同じです。Feature Flag では線の位置だけを動かすので、新しく入る人はいても、外れる人は出ません。

---

### hash() の答えはプロセスごとに変わる

Python の hash() は、文字列に対して、プロセスを起動するたびに違う値を返します。[公式ドキュメント](https://docs.python.org/3/reference/datamodel.html#object.__hash__)によると、str と bytes の hash() には予測できない乱数が混ぜられ、1 つのプロセスの中では同じ値でも、起動し直すと変わります。

乱数を混ぜるのは、辞書のキーを狙って衝突させるサービス妨害を防ぐためで、Python 3.3 から既定で有効です。混ぜる乱数は、環境変数 `PYTHONHASHSEED` に値を入れると固定できます。

```console
$ python3 -c 'print(hash("u-00002") % 100)'
87
$ python3 -c 'print(hash("u-00002") % 100)'
72
```

<br>

#### 同じ判定を 5 通りに置いた実験

冒頭の図は、次の Web アプリケーションで測りました。`?user=u-00042` を受け取り、答えたプロセスの ID と、フラグが有効かを返します。環境変数 `FLAG_RULE` で、hash() と [zlib.crc32](https://docs.python.org/3/library/zlib.html#zlib.crc32) を切り替えます。

末尾の `wsgi()` と `asgi()` は、gunicorn と uvicorn がそれぞれ呼び出す入口です。Python の Web サーバーがアプリケーションを呼ぶ規格に WSGI と ASGI の 2 つがあり、gunicorn は前者、uvicorn は後者に従うので、同じ `answer()` を 2 つの形で包んでいます。

```python
import json, os, zlib
from urllib.parse import parse_qs

RULE = os.environ.get("FLAG_RULE", "builtin")
PERCENT = 10


def is_on(user: str) -> bool:
    if RULE == "builtin":
        return hash(user) % 100 < PERCENT
    return zlib.crc32(user.encode()) % 100 < PERCENT


def answer(query: str) -> bytes:
    user = parse_qs(query)["user"][0]
    return json.dumps({"pid": os.getpid(), "on": is_on(user)}).encode()


def wsgi(environ, start_response):  # gunicorn app:wsgi
    body = answer(environ.get("QUERY_STRING", ""))
    start_response("200 OK", [("Content-Type", "application/json")])
    return [body]


async def asgi(scope, receive, send):  # uvicorn app:asgi
    body = answer(scope["query_string"].decode())
    await send({"type": "http.response.start", "status": 200,
                "headers": [(b"content-type", b"application/json")]})
    await send({"type": "http.response.body", "body": body})
```

これを [gunicorn](https://gunicorn.org/) の `-w 3` と [uvicorn](https://uvicorn.dev/) の `--workers 3` で 1 つのポートに起動したものと、worker 1 つの uvicorn を 3 つのポートに起動し、ロードバランサーの代わりに順番に振り分けたものを用意しました。3,000 人が 6 回ずつ聞き、答えが 1 回でも変わったユーザーを数えます。以下は数える部分の抜粋です。

```python
mixed = 0
for user, rows in answers.items():  # rows: そのユーザーが受け取った (pid, on) の 6 件
    if len({on for _, on in rows}) > 1:
        mixed += 1
```

```text
== gunicorn -w 3 (fork), builtin
  users whose answer changed: 0 (0.0%)
== uvicorn --workers 3 (spawn), builtin
  users whose answer changed: 765 (25.5%)
== 3 pods (uvicorn x3, round robin), builtin
  users whose answer changed: 842 (28.1%)
```

出力の 3 pods は 3 台に見立てた 3 つのプロセスで、fork と spawn は worker の起動のしかたです。fork と spawn は次の小見出しで説明します。3 台に分けた構成では、順番に振り分けたので、全員が 3 つのプロセスに 2 回ずつ聞いています。1 人がどのプロセスでも同じ答えを受け取る確率は、全部で有効か全部で無効かの 0.1³ + 0.9³ = 0.73 なので、残りの 27% が入れ替わる計算で、実測の 28.1% と合います。

uvicorn の 25.5% が少し低いのは、どの worker が受けるかを OS が決めるので、6 回で 3 つ全ての worker に当たらなかった人がいるためです。1 人あたりに答えた worker の数は、平均 2.74 個でした。

<br>

#### gunicorn では一致し、uvicorn では一致しない理由

gunicorn は、最初に起動したプロセスが worker を fork で複製します。複製した worker は親の乱数をそのまま引き継ぐので、3 つの worker の hash() は同じ値を返します。uvicorn の `--workers` は、[ソースコード](https://github.com/encode/uvicorn/blob/master/uvicorn/_subprocess.py)のとおり multiprocessing の spawn で worker を起動します。spawn は Python を新しく起動し直すので、worker ごとに乱数が変わります。3 台のサーバーや Kubernetes の 3 つの Pod も、それぞれが別に起動した Python なので、同じことが起きます。

以下は、答えが変わったユーザーの 1 人が、uvicorn の 3 つの worker に 0.5 秒ごとに聞いた時の記録です。

{{< figure src="images/feature-flag_timeline.webp" alt="動く図。ユーザー u-00002 が 0.5 秒ごとに 16 回画面を開き、どの worker が答えたかが 3 本の線の上に順に現れる。worker 1 が答えた 3 回だけが赤い四角の有効で、右の画面には新しい決済画面が出る。worker 2 と worker 3 が答えた 13 回は白い四角の無効で、画面は今の決済画面に戻る" caption="1 人のユーザーが開くたびに、答えた worker で画面が変わる（実測の時刻を 0.5 倍速で再生）" align="center" >}}

画面は、worker 1 が答えた時だけ新しい決済画面になりました。ユーザーから見ると、決済の途中で画面が入れ替わり、問い合わせても再現しない不具合です。

<br>

#### 再起動すると選ばれる人が入れ替わる

gunicorn でも、問題が消えたわけではありません。gunicorn を止めて起動し直し、有効になったユーザーを前後で比べました。

| 番号の出し方 | 前に有効 | 後に有効 | 前後とも有効 |
|---|---|---|---|
| hash() | 321 人 | 299 人 | 31 人（9.7%） |
| crc32 | 286 人 | 286 人 | 286 人（100%） |

hash() では、前に有効だった 321 人のうち、後も有効だったのは 31 人でした。デプロイのたびに、新しい画面を見ていた人のほとんどが今の画面に戻り、別の 1 割が新しい画面を見始めます。前に入っていた人が、乱数が変わった後も 10% に入る確率は 10% なので、ほぼ計算どおりの数です。

`PYTHONHASHSEED` を全てのプロセスで同じ値にすれば、hash() の値は一致します。ただし、hash() の計算方法自体も Python 3.11 で [siphash13 に変わった](https://docs.python.org/3/whatsnew/3.11.html)ように、バージョンを上げると変わることがあります。フラグの番号には、crc32 や SHA-1 のように計算方法が決まっている関数を使う方が安全です。

1 つのリクエストが複数のサービスを通る時は、入口のサービスで 1 回だけ答えを決め、その答えを下流に渡す方法もあります。[分散トレーシング](/notes/distributed-systems/distributed-tracing/)で、リクエストの記録を残すかを入口で決めてヘッダで下流に伝える head sampling と同じ形で、下流のサービスはハッシュを計算し直しません。

---

### 2 つのフラグが同じ 10% に当たる

計算方法の決まったハッシュ関数で番号を揃えれば、冒頭の問題は消えます。ただし、番号をユーザーの ID だけから出していると、別の問題が残ります。同じ判定で、新しい決済画面（new-checkout）と新しい検索（new-search）を同時に 10% に出した場合です。

{{< figure src="images/feature-flag_overlap.webp" alt="400 人のユーザーを 20 かける 20 のマスに並べた 2 つの図。左はユーザーの ID だけから番号を出した場合で、色の付いたマスは全て赤の両方が有効で、10 万人では 10,006 人（10.01%）が両方とも有効。右はフラグの名前とユーザーの ID を混ぜて番号を出した場合で、青の new-checkout だけ有効と黄土色の new-search だけ有効が散らばり、赤は 3 マスだけ。10 万人では 1,034 人（1.03%）" caption="2 つのフラグを同時に 10% で出した時に、両方が有効になるユーザー" align="center" >}}

左の図では、2 つのフラグが全く同じ 10% に当たりました。番号が ID だけで決まるので、どのフラグを 10% で出しても、同じ人が選ばれるからです。この 10% の人は全ての新機能を同時に受け取り、残りの 90% はどれも受け取りません。エラーが増えた時にどのフラグが原因かを切り分けにくく、2 つの A/B テストの結果も互いに混ざります。

右の図は、フラグの名前とユーザーの ID をつないだ文字列から番号を出した場合で、両方に当たる人は 10% × 10% の約 1% になりました。

次が 2 つの出し方で、左右はハッシュ関数に渡す文字列だけが違います。ここからは Unleash の SDK に合わせて、ハッシュ関数を MurmurHash3 にし、番号を 1〜100 で数えます。murmur3_32 は MurmurHash3 を Python で書いたもので、[lab/overlap.py](https://github.com/nao1215/debimate/blob/main/content/notes/software-architecture/feature-flag/lab/overlap.py) に全体があります。

```python
def shared(flag: str, user: str, p: int) -> bool:
    return murmur3_32(user.encode()) % 100 + 1 <= p


def per_flag(flag: str, user: str, p: int) -> bool:
    return murmur3_32(f"{flag}:{user}".encode()) % 100 + 1 <= p
```

`per_flag()` は、Unleash の SDK と同じ計算です。[Node.js の SDK](https://github.com/Unleash/unleash-node-sdk/blob/main/src/strategy/util.ts) は `${groupId}:${id}` を MurmurHash3 に通して 1〜100 の番号を出し、[ドキュメント](https://docs.getunleash.io/reference/stickiness)によると groupId の既定はフラグの名前です。

LaunchDarkly が Go 向けに出している [SDK](https://github.com/launchdarkly/go-server-sdk-evaluation/blob/v3/evaluator_bucketing.go) は、フラグのキー・フラグごとに持つ salt という文字列・ユーザーのキーを `.` でつないで SHA-1 に通します。どちらもフラグの名前を混ぜるので、左の図のような重なりは起きません。逆に、2 つのフラグを同じ人に出したい時は、Unleash なら groupId を揃えます。

右の出し方でも、割合を上げた時に外れる人は出ません。new-checkout を 10% から 20%・50%・100% に上げると、10% の時の 10,143 人は、どの段階でも全員が有効のままでした。

---

### 使い終えたフラグが残した事故

フラグは if 文なので、消す時はフラグと、使わなくなった方のコードを一緒に消す必要があります。全員に公開したなら無効の時に動くコードを消し、公開をやめたなら有効の時に動くコードを消します。

消し忘れたフラグが、別の意味で使い回された事故があります。米国の証券会社 Knight Capital は、2012 年 8 月 1 日の約 45 分で、意図しない注文により 400 万件の売買を成立させ、4 億 6,000 万ドルを超える損失を出しました。成立した売買を約定と呼びます。

この日、ニューヨーク証券取引所（NYSE）は個人投資家の注文を扱う新しい制度 RLP（Retail Liquidity Program）を始め、Knight Capital はそれに対応するコードを入れていました。Knight Capital のフラグは設定ファイルの値ではなく、届いた注文ごとに付く値でした。米国の証券取引委員会（SEC）の[命令書](https://www.sec.gov/litigation/admin/2013/34-70694.pdf)に書かれた経緯は、次の通りです。

1. 約定まで注文を出し続ける昔の機能 Power Peg は、2003 年から使わずにコードだけ残っていた。
2. RLP に対応するため、Power Peg を動かしていたフラグを使い回した。
3. 7 月 27 日から新しいコードを 8 台のサーバーに配布した時、1 台にだけ配布されなかった。
4. 当日、フラグを付けた注文が 8 台目に届き、残っていた Power Peg が止まらずに注文を出し続けた。
5. 対処として 7 台から新しいコードを外すと、その 7 台でも Power Peg が動き、悪化した。

{{< figure src="images/feature-flag_knight.webp" alt="8 台のサーバーを 3 段で並べた図。1 段目は 7 月 27 日からの配布で、7 台に新しいコードの RLP が入り、8 台目は配布されず古いコードのまま。2 段目は 8 月 1 日で、同じフラグを付けた注文が届き、7 台は RLP として処理し、8 台目は Power Peg を動かす。3 段目は対処として 7 台から新しいコードを外した後で、8 台全てが Power Peg を動かす" caption="Knight Capital の 8 台のサーバーで、同じフラグが動かしたコード（SEC の命令書から作図）" align="center" >}}

命令書によると、Power Peg は 1 つの注文を小分けにして出し、約定した株数が注文した株数に達した所で止まる作りでした。2005 年の改修で、この株数を数える処理が別の場所へ移され、その後 Power Peg は試験されていませんでした。8 台目が注文を出し続けたのは、この処理が無かったためです。

冒頭の実験と同じく、同じフラグがサーバーごとに違う答えを出した事故で、違ったのは番号ではなくフラグの意味でした。命令書は、2003 年に Power Peg のコードを本番のサーバーに残したことも、不備の 1 つに挙げています。一方で、1 台だけ配布が漏れたことは、配布した後に二重に確認する手続きがあれば見つけられたと書いています。配布が漏れることは、古いコードを消すだけでは防げません。

消し忘れは、Knight Capital に限った話ではありません。Uber は 2020 年 3 月の[ブログ](https://www.uber.com/blog/piranha/)で、一定期間（例として 8 週間）変更の無いフラグを古いと見なし、フラグと使われなくなったコードを消す変更を自動で作るツール Piranha を紹介しています。このツールで、約 2,000 個の古いフラグを消したそうです。

---

### フラグを入れる前に確認すること

Feature Flag をこれから入れる人も、既存のコードでフラグに出会った人も、確認することは 5 つです。

<br>

#### 番号の出し方

割合で出すなら、番号の出し方を読みます。ユーザーの ID とフラグの名前から、計算方法の決まったハッシュ関数で出していれば、冒頭の図で crc32 を使った構成と同じく、答えはプロセスごとに一致します。自分で書く場合も、管理サービスの SDK を使う場合も、別に起動した 2 つのプロセスに同じユーザーを聞かせ、答えが違うユーザーを数えれば確認できます。次は、Python を 2 回起動し、実験で使った `app.py` から `is_on()` を 3,000 人分ずつ呼ぶ例です。

```python
import subprocess, sys

CODE = "from app import is_on; print(''.join('1' if is_on(f'u-{i:05d}') else '0' for i in range(3000)))"
a, b = (subprocess.run([sys.executable, "-c", CODE], capture_output=True, text=True, check=True).stdout
        for _ in range(2))
print(sum(x != y for x, y in zip(a, b)), "of 3000 users differ")
```

```text
FLAG_RULE=builtin
547 of 3000 users differ
FLAG_RULE=crc32
0 of 3000 users differ
```

出力は、環境変数 `FLAG_RULE` を替えて 2 回実行した結果です。hash() では 547 人の答えが違い、crc32 では 0 人でした。547 人は 3,000 人の約 18% で、片方だけで有効になる確率 2 × 0.1 × 0.9 = 0.18 と合います。1 台の gunicorn での試験では、この違いは見つかりません。

管理サービスから値を配布する構成でも、通信・ポーリングの間隔・キャッシュの分だけ、各プロセスが変更を受け取る時刻はずれます。割合を変えた直後は、しばらくプロセスごとに答えが違うことを前提にします。

<br>

#### 揃える単位

何の単位で揃えるかを決めます。Unleash はこの単位を stickiness と呼び、[ドキュメント](https://docs.getunleash.io/reference/stickiness)によると、既定ではユーザーの ID を使います。ログイン前の利用者のように ID が無い時は sessionId を使い、それも無ければ乱数で決めるので、答えは一致しません。決済のように途中で画面が変わると困る機能では、ログインの前後で答えが変わってよいかも決めておきます。

A/B テストの途中で揃える単位や番号の出し方を変えると、群に入る人が入れ替わり、前後の結果を同じ条件の比較として扱えなくなります。

<br>

#### 消す日と名前

フラグを消す日を決め、名前を使い回しません。Pete Hodgson 氏の記事は、Release Toggle を足す時に、それを消す作業もバックログに積むことを勧めています。消すまでは新旧どちらのコードも試験し続けることになり、フラグが増えるほど、試す組み合わせも増えます。

無効の時に動く既存のコードも、新しいビルドで動くかを見ておく必要があります。Knight Capital の事故は、消さなかったコードと、使い回したフラグの組み合わせで起きました。

<br>

#### 判定を置く場所

既存のコードでよく見るのは、注文の確定・決済の画面・返金のような複数の処理が、同じフラグの値をそれぞれ読んでいる形です。Pete Hodgson 氏の記事は、処理が分かれる箇所を Toggle Point、答えを出すロジックを Toggle Router と呼び、Toggle Point が設定値を直接読んで判断まで抱える形を避けるよう勧めています。判断が各処理に散っていると、割合の規則や管理サービスを変える時に、全ての箇所を直すことになるからです。

次は、判断を 1 か所にまとめた例です。業務の処理は「新しい決済を使うか」を聞くだけで、フラグの名前と評価のしかたは `CheckoutDecisions` の中にしかありません。

```python
class CheckoutDecisions:  # Toggle Router。フラグの名前はここだけに置く
    def __init__(self, flags):
        self.flags = flags

    def use_new_checkout(self, user_id: str) -> bool:
        # 評価できない時は False を返し、今の決済を使う
        return self.flags.is_on("new-checkout", user_id, default=False)


def checkout(cart, user_id: str, decisions: CheckoutDecisions):
    if decisions.use_new_checkout(user_id):  # Toggle Point
        return checkout_v2(cart)
    return checkout_v1(cart)
```

`self.flags` の中身が自分で書いた `is_on()` から管理サービスの SDK や OpenFeature の評価 API に替わっても、`checkout()` は直さずに済みます。ただし、判断をまとめる手間に見合うのは長く残るフラグです。数週間で消す Release Toggle なら、単純な if 文で足ります。

<br>

#### 管理サービスが必要か

最後に、管理サービスが本当に必要かを考えます。全員を一度に切り替えるだけなら、設定ファイルや環境変数で足ります。環境ごとの接続先のように消す予定の無い設定の分岐は、Feature Flag にしません。割合で出す規則が必要になった時に初めて、番号の出し方を持つ SDK が役に立ちます。その時に確認するのが、冒頭の図で右に並べた割合です。

実験のコードと出力の全体は [lab/](https://github.com/nao1215/debimate/tree/main/content/notes/software-architecture/feature-flag/lab) にあります。図の生成元は [figures.py](https://github.com/nao1215/debimate/blob/main/content/notes/software-architecture/feature-flag/figures.py) です。
