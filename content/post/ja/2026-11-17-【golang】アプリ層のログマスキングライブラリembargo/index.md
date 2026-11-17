---
title: 【Golang】アプリ層のログマスキングライブラリembargo
type: post
date: 2026-11-17
draft: false
categories:
- プログラミング
- OSS
tags:
- golang
- oss
cover:
  image: images/logo.webp
  alt: Gopher が embargo の看板から顔を出し、看板の email と token の値が黒塗りになっている
  hidden: false
---

Gopher は Renée French 氏によってデザインされ、[CC BY 4.0 ライセンス](https://creativecommons.org/licenses/by/4.0/)が適用されています。

---

### 前書き：パニックログに思いを馳せて

Go 製アプリがログ・エラー報告・アクセスログ・トレースに書き出す時、シークレットと個人情報を隠すライブラリ [nao1215/embargo](https://github.com/nao1215/embargo) をリリースしました。「パニックログからシークレットが漏れる可能性あるよな？」という疑問から開発がスタートしています。

本記事では、embargo が何をするライブラリか、多重防御のどこを担うか、どれだけの種類のシークレットを隠せるか、誤検出をどう減らしたかを順に説明します。後半では、競合との比較と速度、漏洩をテストで見つける embargotest、テスト手法へのこだわり、そして最後に効いてくる知名度と採用実績の話をします。

---

### embargo とは

embargo は、シークレット（API キー・パスワード・トークンなど）と個人情報（メールアドレス・カード番号など）を `[REDACTED]` へ置き換えるライブラリです。ルートのモジュールは、標準ライブラリにしか依存しません。最近は、LLM が脆弱性をバンバン発見するため、ライブラリアップデートが激しいです。なるべく依存関係を持たないように絞りました。また、クロスプラットフォーム（Linux・macOS・Windows）対応です。FreeBSD・OpenBSD・NetBSD はビルドが通ることのみチェックしています。


embargo は、以下の 5 つの役割を持ちます。

| やりたいこと | 機能 |
|---|---|
| 既知のシークレットを表示させない（開発者がシークレットを明示） | `Secret` 型の利用 |
| 構造体・エラーの形を保ったままログに出す | 既存の slog ハンドラーを `NewSlogHandler` でラップ |
| ログ以外に出す JSON（API レスポンスなど）から、シークレットや個人情報を隠す | `Scanner.MaskJSON` |
| エラーメッセージに混ざったクレカ番号など、シークレットを見つける | 38 種類の検出器 |
| 偽のシークレットを仕込んだテストで、ログや HTTP レスポンスへの漏洩を見つける | `embargotest` |

<br>

以下に、既存の slog ハンドラーを `embargo` でラップする例を示します。`User` 型は、タグも `embargo` が提供する型も利用しません。

```go
package main

import (
	"errors"
	"fmt"
	"log/slog"
	"os"

	"github.com/nao1215/embargo"
)

// 既存の型。タグも embargo の型も付けていない
type User struct {
	Name     string
	Email    string
	Password string
}

func main() {
	next := slog.NewJSONHandler(os.Stdout, nil) // 今使っているハンドラー
	logger := slog.New(embargo.NewSlogHandler(next, embargo.NewScanner()))

	user := User{Name: "alice", Email: "alice@example.com", Password: "hunter2"}
	err := fmt.Errorf("charge failed: %w",
		errors.New("card 4111111111111111 declined, Authorization: Bearer ghp_0123456789abcdefghijABCDEFGHIJ012345"))
	logger.Error("checkout", "user", user, "err", err)
	// Output (time は省略):
	// {"level":"ERROR","msg":"checkout","user":{"Name":"alice","Email":"[REDACTED]","Password":"[REDACTED]"},"err":"charge failed: card [REDACTED] declined, Authorization: Bearer [REDACTED]"}

	key := embargo.NewSecret("sk-fake-0123456789")
	fmt.Printf("%v %#v %x %q\n", key, key, key, key)
	// Output:
	// [REDACTED] embargo.Secret[string]([REDACTED]) [REDACTED] [REDACTED]
}
```

上記の例が示すように、slog を `embargo.NewSlogHandler` でラップすると、アウトプットからシークレットや個人情報が隠蔽されます。具体的には、メールアドレスは値の形から、パスワードは Password というキー名から、カード番号と GitHub のトークンはエラーメッセージの中から見つけて、[REDACTED] に置き換えています。`Secret` 型で表現した値（`embargo.NewSecret()`した値）は、`%#v` や `%x` のように書式を変えても中身が出ません。

注目してほしいのは、`user` が JSON の入れ子のまま残っている点です。エラーメッセージも `charge failed: card ... declined` という文脈を保っています。消しすぎたログは障害調査に使えないので、隠すのは値だけにしています。「当たり前では？」と思うかもしれませんが、実装当初は余計なメッセージが隠されることがありました。

---

### 多重防御のうち、アプリ層を担う

シークレットがログに混ざる事故は、頻繁に起きています。例えば、暗号資産 Wallet の Tangem は[モバイルアプリのログに秘密鍵が書かれていた](https://tangem.com/en/blog/post/tangem-resolves-log-issue/)と公表しました。HashiCorp Vault の [CVE-2025-4166](https://discuss.hashicorp.com/t/hcsec-2025-09-vault-may-expose-sensitive-information-in-error-logs-when-processing-malformed-data-with-the-kv-v2-plugin/74717) では、不正な入力の変換エラーにシークレットが入り、エラーログへ出ていました。どの層でシークレットがログに混ざるかは、技術ノート「[Secrets in Logs](/notes/security/log-leak/)」で事例付きで整理しています。

このような漏洩への対策は、1 か所で完結させる必要はありません。以下の図のように、値が書かれてから保存されるまでの間には、いくつもの層があります。多重防御のアプリ層は、「embargo」がデファクトになるように開発を続けています。

{{< figure src="images/layers.webp" alt="左から、アプリケーション（embargo が担う。ログ・エラー報告・アクセスログ・トレースを書く前に隠し、テストで確かめる）、収集・転送（OTel Collector・Fluent Bit・Vector が流れてきた文字列を消す）、保存・閲覧（ログ基盤・監視 SaaS・クラウドの DLP が溜まった後に見つける）、リポジトリ（gitleaks・TruffleHog がコミットされた鍵を見つける）の 4 層が並ぶ" caption="シークレット漏洩対策の層と、embargo が担う範囲" align="center" >}}

なお、[OpenTelemetry Collector の redaction processor](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/processor/redactionprocessor) のように、収集の途中で文字列を消す仕組みは既にあります。リポジトリに紛れ込んだ鍵は [gitleaks](https://github.com/gitleaks/gitleaks) や [TruffleHog](https://github.com/trufflesecurity/trufflehog) が見つけます。これらは別の層を守る道具で、embargo の競合ではありません。


---

### 発見できるシークレットの種類

embargo は、シークレットの種類ごとに検出器を持ち、その総数は2026年11月17日現在で 38 種類です。そのうち 26 種類がデフォルト（`embargo.NewScanner()` を引数無しで呼んだ時）で動きます。各国の個人番号と、ランダムな文字列を見つけるエントロピー判定は、誤検出が増えやすいので明示的に有効にする必要があります。

以下が現状の検出器です。

| 分類 | 検出器の数 | 見つける物 |
|---|---:|---|
| 認証情報 | 9 | URL・DSN のパスワード、`password=` や Authorization ヘッダー、AWS・GitHub・Slack・OpenAI などのトークン、JWT、PEM の秘密鍵 |
| カード | 5 | カード番号、CVV、有効期限、決済トークン、加盟店 ID |
| 銀行 | 6 | IBAN、SWIFT/BIC、米国の ABA ルーティング番号、英国のソートコード、口座番号、ACH のトレース番号 |
| 暗号資産 | 2 | Bitcoin と Ethereum のアドレス |
| 個人情報 | 5 | メールアドレス、IP アドレス、米国と日本の電話番号、マイナンバー（全角数字を含む） |
| 各国の個人番号 | 11 | 米国・英国・インド・ブラジル・中国・韓国・カナダの番号（明示的に有効にした時だけ） |

検出は、正規表現で形式を見るだけではありません。番号の多くは、最後の桁などが残りの桁から計算される「検査数字（check digit）」を持っています。カード番号は [Luhn アルゴリズム](https://en.wikipedia.org/wiki/Luhn_algorithm)、IBAN は MOD 97、マイナンバーは重み付きの MOD 11 で検査数字を確かめます。Ethereum のアドレスは、大文字と小文字が混ざっていれば [EIP-55](https://eips.ethereum.org/EIPS/eip-55) のチェックサム（Keccak-256）まで計算します。形が合うだけの数字を片っ端から隠すと、それは誤検出であり、ログが使い物にならなくなるからです。

各検出は 0〜1 の確度を持ち、例えば検査数字が合わないカード番号は 0.6 になります。既定では、隠す候補の確度の下限が 0 なので、確度が低い候補も含めて全て隠します。下限は
`WithMinConfidence()` で上げられます。検出器ごとの規則と確度は、README の「Matching rules and validation for all 38 kinds」に載せています。

使っているロガーや送信先ごとに、以下のラップ関数があります。ロガーや SDK を初期化する時に一度ラップすれば、以降に書き出す値からシークレットや個人情報が隠されます。


| ロガー・送信先 | ラップ方法 |
|---|---|
| log/slog（TextHandler・JSONHandler など） | `embargo.NewSlogHandler(next, scanner)` |
| [zap](https://github.com/uber-go/zap)・[zerolog](https://github.com/rs/zerolog)・[logrus](https://github.com/sirupsen/logrus) | `embargozap.NewWriteSyncer`・`embargozerolog.NewWriter`・`embargologrus.NewFormatter` |
| net/http のアクセスログ | `embargo.NewHTTPHandler(next, logger, scanner)` |
| gRPC サーバー（unary・stream） | `embargogrpc` のインターセプター |
| [OpenTelemetry](https://opentelemetry.io/) SDK のログと span | `embargootel.NewLogExporter`・`NewSpanExporter` |
| [Sentry](https://sentry.io/) のイベント | `embargosentry.NewBeforeSend(scanner)` |

アダプターは `github.com/nao1215/embargo/adapters/zap` のような別モジュールに分けているので、zap を使わないプロジェクトが zap に依存することはありません。

---

### 誤検出を減らさなければ使われない

マスキングのライブラリで怖いのは、誤検出です。注文番号やリクエスト ID まで `[REDACTED]` になったログでは障害を追えません。

そこで、研究用に公開されているログの集まり [LogHub](https://github.com/logpai/loghub) から 8 種類を利用し、embargo の誤検出を検証しました。シークレットが入っていない筈のシステムログで何かを隠したら、それは誤検出の候補です。以下の図は、開発用に使った 4 種類（Apache・Linux・Android・HDFS、約 8 MB）での結果です。1 GB あたりの値は推定です。ログの種類と検出器の組ごとに、見つかった候補から最大40件を抜き取って 1 件ずつ判定し、誤検出の割合を候補の件数に掛けて換算しています。

{{< figure src="images/false-positives.webp" alt="検出器ごとの 1 GB あたりの誤検出の推定値。改善前は swiftbic が 739,275、pan が 44,210、high_entropy が 31,295、mynumber が 8,072、phone_jp が 2,608、aba_routing が 1,614、credential が 745 で、改善後は全て 0" caption="公開ログで検出器を 1 つずつ動かした時の誤検出（embargo の doc/real-logs.md から作図）" align="center" >}}

改善前の SWIFT/BIC の検出器は、1 GB あたり約74万件も誤検出していました。SWIFT/BIC は銀行コード 4 文字・国コード 2 文字・所在地 2 文字（と支店 3 文字）が並ぶだけの形で、大文字小文字も問いません。試しに LogHub の Apache と HDFS の公式サンプル（各 2,000 行）で改善前の v0.4.0 を動かすと、設定ファイル名 `workers2.properties` の `workers2` や、HDFS のディレクトリ名 `subdir34` が SWIFT/BIC として判定されました。SWIFT/BIC を含む各検出器が周辺の文脈（直前のキー名や識別子の区切り）で見分けるよう直した結果、開発用のログで既定の slog ハンドラーが出す誤検出の推定は、1 GB あたり約83万件から 0 になりました。

ただし、レジスタ値・不正なユーザー名・下線で繋いだ識別子の位置に本物の BIC が書かれていれば、今は見逃します。各国の個人番号の検出では、誤検出が残っています。例えば、米国の SSN は開発用のログで 1 GB あたり約2万件の誤判定があります。さらに、改善に使ったログは既知データであり、未知のログで同じ精度が出る保証はありません。自前のサービスが出すログで確かめたい人向けに、検出結果を種類ごとに数える `embargo --report` コマンドも同梱しています。

---

### 競合との比較

私は競合比較をせずに雰囲気で開発して、痛い目を見ています。CSV などに SQL を実行する [nao1215/sqly](https://github.com/nao1215/sqly) コマンドを宣伝したところ、[DuckDB](https://duckdb.org/) と比較され、存在意義の説明に苦労しました。その反省から、embargo では同種ライブラリより優位に立てる状態を目指しました。目指していますが、まだ完全に優位とは言えない状態です。

比較対象は、以下のとおりです。
- [pii-shield/pii-shield](https://github.com/pii-shield/pii-shield)
- [awslabs/ferret-scan](https://github.com/awslabs/ferret-scan)
- [m-mizutani/masq](https://github.com/m-mizutani/masq)
- [icntswm/go-masker](https://github.com/icntswm/go-masker)
- [samber/slog-formatter](https://github.com/samber/slog-formatter)
- [showa-93/go-mask](https://github.com/showa-93/go-mask)
- [bytedance/godlp](https://github.com/bytedance/godlp)

全てのライブラリに同じ 13 個のシークレットを含むログを流し、出力から元の値が消えたかを調査しました。以下は README から引用した結果です。

{{< figure src="images/scenario-catch.webp" alt="13 個のシナリオで値を隠せた数。embargo 12、pii-shield 10、ferret-scan 9、go-masker 8、masq 6、godlp 5、slog-formatter 3、go-mask 3。下の表は、シナリオごとの masked（隠した）と visible（見えたまま）の内訳" caption="同じ 13 個のシナリオで隠せた数（embargo の README から引用）" align="center" >}}

embargo は 13 個中 12 個を検出しました。ただ、図の内訳を見れば分かる通り、負けている面もあります。タグだけで指定した不透明な値（Opaque value: tag only）は、masq・go-masker・go-mask が検出し、embargo は隠せません。検査数字が合わないカード番号（Invalid card control）は、隠さないのが正解の対照ですが、embargo と masq は書き換えました（embargo は確度 0.6 の候補として隠しています）。

勝ち負けを公平に並べるため、README には相手の強みも書いています。

| 相手 | 相手が優位な点 | embargo が優位な点 |
|---|---|---|
| pii-shield | ロガーを問わず、書き出した行を書き換える。プロセスの外のサイドカーとしても動く | キー名に入った値や、メッセージ中の Bearer トークンも隠す。速い |
| ferret-scan | ロガーを問わず、書き出した行を書き換える。文書や画像も検査できる | 日本の電話番号やトークン類も隠す。桁違いに速い |
| masq | タグで指定した値を隠せる。独自のルールを書ける | キー名やグループ名に入った値も隠し、コンテキストを残す |
| go-masker | タグ指定と、末尾を残す部分マスクがある | 検出器の種類が多い。速い |
| slog-formatter | 決めたフィールドの変換が速い | メッセージ本文中のシークレットも見つける |
| go-mask | マスク済みの構造体のコピーを速く返す | 登録していない値も見つける |
| godlp | メールやカード番号の一部だけを見せる部分マスク | 日本の電話番号やトークン類を隠せる |

<br>

#### サービスに仕込んだ漏洩

上の 13 個は、ログ 1 行ずつの比較です。もう少し現実に寄せて、HTTP サーバーにシークレットを仕込んだ比較もしました。よくあるサービス実装が書きそうな形で、DB の DSN、ラップされたエラー、Authorization ヘッダー、他社の API キーをログに流します。○が隠した、×が漏れたです。

| サービスの出力 | embargo | pii-shield | ferret-scan | masq | go-masker | slog-formatter | go-mask | godlp |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| `password` キーに入ったパスワード | ○ | ○ | ○ | ○ | ○ | ○ | ○ | × |
| DSN を持つ設定の構造体 | ○ | ○ | × | ○ | ○ | × | × | × |
| ラップされたエラーに入った DSN | ○ | ○ | × | ○ | ○ | × | × | × |
| errors.Join で繋いだ DSN と API キー | ○ | ○ | × | × | ○ | × | × | × |
| メッセージ中の Bearer トークン | ○ | ○ | × | × | ○ | × | × | × |
| メッセージ中にある他社の API キー | ○ | ○ | × | × | × | × | × | × |
| ログに書かないリダイレクト URL のクエリ | × | × | × | × | × | × | × | × |

最後の行は、全ライブラリで漏らしています。例えば `Location: https://example.com/callback?token=...` のようにトークンを付けたリダイレクトは、ロガーを通らずにレスポンスのヘッダーとして返り、ブラウザの履歴や途中にあるプロキシのログに残ります。ロガーをラップする方式では、どのライブラリも止められません。ここで効果を発揮するのは、後述する `embargotest` です。出力そのものを調べるので、ロガーを通らない漏洩もテストで落とせます。

---

### 速度比較

遅いライブラリは、嫌われます。ログはリクエストごとに書かれるので、1 行あたり数マイクロ秒の差でも積み重なります。そこで、slog だけ・embargo・pii-shield・masq・go-masker に同じ JSON の slog イベントを通して時間を測りました。以下は README から引用した図です。

{{< figure src="images/log-event-time.webp" alt="リクエスト・メール・カードを含む同じ JSON の slog イベント 1 件あたりの時間。slog のみ 0.40 µs、embargo 1.36 µs、pii-shield v3.0.0 4.69 µs、masq v0.2.3 3.09 µs、go-masker v0.6.1 1.43 µs" caption="ログ 1 件あたりの時間（embargo の README から引用。短いほど速い）" align="center" >}}

イベントの種類を変えた結果は、以下の通りです。単位はマイクロ秒で、AMD Ryzen AI Max+ 395 の 1 スレッド（GOMAXPROCS=1）で 200 ms の計測を10回した中央値です。

| イベント | slog のみ | embargo | go-masker | masq | pii-shield |
|---|---:|---:|---:|---:|---:|
| メールとカードが並ぶ（flat） | 0.40 | 1.36 | 1.43 | 3.09 | 4.69 |
| 入れ子の構造体（nested） | 0.59 | 2.27 | 2.96 | 5.43 | 7.58 |
| map | 1.17 | 3.16 | 3.47 | 5.43 | 6.80 |
| 隠す物が無い（clean） | 0.42 | 1.04 | 1.38 | 2.84 | 4.47 |
| 属性が50個（large50） | 3.80 | 13.90 | 14.00 | 59.19 | 66.52 |

5 種類のイベント全てで、embargo が最も速い結果になりました。時間は go-masker の 0.75〜0.99 倍、masq の 0.23〜0.58 倍、pii-shield の 0.21〜0.46 倍です。表に入れていない ferret-scan は、1 件あたり 456 µs〜6.4 ms 掛かりました。ただし、この計測の embargo は、メールとカード番号の 2 種類の検出器だけを使っています。また、slog が組み立てた JSON を読み直し、キーと入れ子の形を保ったまま値を辿る処理は、文字列として 1 回走査するだけの旧実装の約2.5倍の時間が掛かります。この処理を含めても、5 種類のイベント全てで比較したライブラリより速い結果でした。

検出器の数も速さに効きます。秘密を含まないログに対して、全ての検出器を動かす `WithAll()` は約 65 µs 掛かりますが、`WithKinds(KindEmail)` でメールだけに絞れば、`@` が無いことを確かめて約 0.1 µs で返ります。必要な検出器だけを選べば、その分だけ速くなります。

---

### embargotest は、テストで漏洩を発見する

`Secret` 型でシークレットを隠蔽しても、誰かが `Reveal()`（ラップした値を取り出すメソッド）で取り出した値をログに流せば終わりです。ロガーを通らないケースもあります。そこで embargo には、本番と同じ出力を調べるテスト用のパッケージ `embargotest` を同梱しました。以下は、故意に `Reveal()` した値をログに出すテストです。

```go
func TestSigningFailureKeepsTheKeySecret(t *testing.T) {
	r := embargotest.New(t)
	key := embargo.NewSecret(r.Canary()) // テスト用の偽の鍵
	logger := slog.New(slog.NewJSONHandler(r.Writer("logs"), nil))

	logger.Error("signing failed", "key", key.Reveal()) // 故意に漏らす

	r.ExpectJSON("logs", nil, map[string]string{"msg": "signing failed"}, 1)
	r.Check()
}
```

```text
--- FAIL: TestSigningFailureKeepsTheKeySecret (0.00s)
    leak_test.go:19: embargotest: the fake secret appeared in captured output
FAIL
```

上記のテストで偽の鍵（`key := embargo.NewSecret(r.Canary())`）は、そのままの形でログに出ていません。`r.Canary()` は `[]byte` を返すので、slog の JSONHandler は鍵を `"ZW1iYXJnby1mYWtlLXNlY3JldC0wMTIzNDU2Nzg5YWI="` のように base64 にして書きます。生の値を `bytes.Contains` で探すだけなら、このテストは通ってしまいます。

`embargotest` は、偽の鍵を 16 進・base64・JSON や Go のエスケープに変換した形式まで探すので、この base64 を見つけてテストを失敗させます。embargo が生成する偽の鍵を使うのは、値（偽の鍵）を知っていれば変換後の形式まで探せるからです。

`ExpectJSON` は、`logs` を検査し、`msg` が `signing failed` である JSON が 1 件あることを確かめます（`nil` は JSON の最上位を見る指定）。必要な情報が消されたログは障害調査に使えないので、「漏れていない」と「必要な情報が届いた」を同じテストで確かめる設計にしました。パッケージ全体を見張るなら、以下の 1 行を足すだけです。

```go
func TestMain(m *testing.M) { os.Exit(embargotest.Guard(m)) }
```

`Guard` はパッケージのテストを子プロセスで走らせ、stdout・stderr・既定の slog・子プロセスの出力に、偽の鍵（変換された形を含む）か、検出器が見つけたシークレットや個人情報が出たら、テストを失敗させます。既に masq などでシークレットをマスクしているプロジェクトでも、`embargotest` だけを足せます。

---

### 多様なテスト手法の導入

セキュリティのライブラリは、バグがそのまま漏洩に繋がります。embargo では、[技術ノート「Software Testing」](/notes/software-testing/)で書いてきた手法を総動員しました。以下に、手法と、その手法で捕まえたいバグを示します。

| 手法 | 捕まえたいバグ |
|---|---|
| Example とユニットテスト | README やドキュメントに載せた出力と、実際の出力が食い違う |
| [Property-Based Testing](/notes/software-testing/property-based-testing/) | 手書きの例では試していない番号で、検査数字の計算を誤る |
| [Metamorphic Testing](/notes/software-testing/metamorphic-testing/) | 前後の文脈・エンコード・書式を変えただけで、検出結果が変わる |
| [Quint](/notes/software-testing/quint/) によるモデルの検査 | `Guard` が失敗を取りこぼす、検査前の出力を流してしまう |
| [Lean](https://lean-lang.org/) で証明した参照実装 | 乱数では試しきれない、検査数字や隠す範囲（バイト位置）の計算の誤り |
| [Snapshot Testing](/notes/software-testing/snapshot-testing/) | マスクは正しいが、出力の形が意図せず変わる |
| [Differential Testing](/notes/software-testing/differential-testing/) | 実装と、自分で書いた期待値が、同じ思い込みで揃って間違う（外部の python-stdnum や net/mail と突き合わせる） |
| 構造を考慮した [Fuzzing](/notes/software-testing/fuzzing/) | 壊れた入れ子・引用符付きの認証情報・途中で分割された入力で、落ちる、または漏れる |
| [Mutation Testing](/notes/software-testing/mutation-testing/) | 実装を壊しても落ちない、効いていないテスト |
| 本物のロガー・SDK の出力 | シリアライザーや SDK を通った時に漏れる |
| [CI ベンチマーク（変更前後）](/notes/software-testing/ci-benchmark/) | CI のマシンパワーの差異に埋もれて、性能の劣化を見逃す |

カバレッジは 99.3% です（2026年11月17日、main ブランチの CI での計測）。Mutation Testing の効き目（テストを走らせて結果が出た変異のうち、KILL した割合）は 89.18%、Fuzzing は 13 個のターゲットで合計約221万回実行しています（どちらも2026年11月17日の計測）。CI はカバレッジが 97% を下回る変更を拒否し、定期実行の重い CI では、パッケージごとに記録した Mutation Testing の点を下回っていないかを確かめます。

<br>

#### 脆弱性とサプライチェーンの検査

シークレットを守るライブラリ自体に脆弱性があっては本末転倒なので、静的解析と脆弱性の検査を CI に入れています。

| 検査 | 内容 |
|---|---|
| [govulncheck](https://pkg.go.dev/golang.org/x/vuln/cmd/govulncheck) | 実際に呼んでいる関数の単位で、依存ライブラリと Go 本体にある既知の脆弱性を調べる |
| [Trivy](https://github.com/aquasecurity/trivy) | 全ての go.mod/go.sum を含むファイル一式の脆弱性を調べる |
| [gosec](https://github.com/securego/gosec)・[CodeQL](https://codeql.github.com/) | コードの静的解析で、脆弱な実装を見つける |
| [OpenSSF Scorecard](https://scorecard.dev/viewer/?uri=github.com/nao1215/embargo) | リポジトリの運用（権限・依存の固定・Fuzzing など）を採点する |
| cosign・SLSA provenance | CLI のリリース成果物に署名と、どこでビルドしたかの証明を付ける |

GitHub Actions の action は全てコミットのハッシュで固定し、ロックファイルでも確かめています。Scorecard の点は、2026年11月17日の時点で 10 点満点中 8 点です。脆弱性・依存の固定・Fuzzing・SAST などは満点ですが、コードレビュー（Code-Review）とコントリビューター（Contributors）は 0 点です。1 人で開発している限り、この 2 つは上がりません。

---

### 名前の由来

embargo は報道で使われる単語で、解禁日時まで情報を外に出さない取り決めを指します。シークレットを外に出さないという意味に使えて、さらに go で終わるので採用しました。

「私達は LLM のコンドーム」という発言を最近聞いたので、真っ先に gondom（go + condom）が思い浮かびました。意味的には完璧でした。漏れてはいけないもので、漏れても一発で終わるわけではありません。しかし、重大な事態に繋がります。使えば安心。シークレット漏洩と、もう一つの漏洩。近しいものがあります。MTG 中に「gondom が〜」と話して微妙な雰囲気になる姿が思い浮かんだので、お蔵入りしました。


---

### 最後に：知名度と採用実績が全て

embargo の前身は、2026年2月に作った sensitive というライブラリです（参考：[sensitive を作った話](/post/ja/2026-02-08-sensitiveライブラリを作った話/)）。sensitive の採用を検討してくれた OSS がありましたが、実績が無いという理由で見送られました。セキュリティに関わるライブラリなので、実績で判断されるのは当然です。embargo はその sensitive を改名し、Secret 型と embargotest を加えて作り直した物です。embargo という別リポジトリを作りましたが、機能が弱すぎて sensitive とマージしました。

テストやドキュメントが揃っていることは、LLM 時代には誰でも対応できます。それらは、信頼の証拠になりにくくなりました。最後に効くのは、メンテナンスを続けた期間、他 OSS 開発やコミュニティ活動での実績だと考えています。少しでも採用実績が欲しいので、技術的に詰める作業と並行して、宣伝も適宜やっていきます。本記事もその一環です。LLM 登場前より、OSS を育てるのが難しくなったなと感じる次第です。

Go でアプリを書いている皆さん、`TestMain` に `embargotest.Guard` の 1 行を足すと、テストが出力した stdout・stderr・ログに、シークレットや個人情報らしい値が出ていないかを確かめられます。テストデータの値で落ちる時は、`WithAllowedValues` で許可してください。

```go
package app

import (
	"log/slog"
	"os"
	"testing"

	"github.com/nao1215/embargo/embargotest"
)

func TestMain(m *testing.M) {
	// テストデータとして、わざと出している値は許可する
	os.Exit(embargotest.Guard(m, embargotest.WithAllowedValues("alice@example.com")))
}

func TestSignup(t *testing.T) {
	t.Log("created user alice@example.com") // 許可した値なので落ちない
}

func TestConnect(t *testing.T) {
	dsn := "postgres://app:s3cr3t@db.example/orders"
	slog.Info("connecting", "dsn", dsn) // 既存のコードがうっかり DSN をログに出す
}
```

```text
=== RUN   TestSignup
    app_test.go:17: created user alice@example.com
--- PASS: TestSignup (0.00s)
=== RUN   TestConnect
--- PASS: TestConnect (0.00s)
PASS
embargotest: package leak or scanner failure on stderr; active tests: TestConnect
FAIL	app	0.008s
FAIL
```

個々のテストは PASS でも、DSN のパスワードが stderr に出たので、パッケージ全体が FAIL になります。漏れた行そのものは表示せず、どの出力（stderr）で、どのテストが動いていた時（TestConnect）かだけを示します。テスト名は、特定できない時に `[unavailable]` になることがあります。
