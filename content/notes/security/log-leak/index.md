---
title: "Secrets in Logs - シークレットがログへ漏れる経路は層ごとに違い、後段の消去だけでは止まらない"
date: 2026-11-14
draft: false
series: ["技術ノート", "Security"]
tags: ["security", "logging", "secret-management", "observability", "opentelemetry", "go"]
weight: 15
wrapTables: true
topics: ["Secret Management"]
---

2024 年 12 月 31 日、暗号資産のハードウェアウォレットを販売する Tangem は、モバイルアプリのログに秘密鍵が書かれていたと[公表](https://tangem.com/en/blog/post/tangem-resolves-log-issue/)しました。秘密鍵は、知っていれば持ち主の資産を動かせる値です。

ログは自動では送られません。利用者がアプリからサポートに問い合わせた時に、ログが添付ファイルとしてサポートへ届く作りでした。障害を調べるために集めたログが、その秘密鍵を社外へ届ける経路になっていたわけです。Tangem は資金の流出は無かったと説明し、該当する利用者に新しいウォレットへ資金を移すよう案内しました。

本記事でいうログ漏洩は、シークレットがログ・エラー文・トレース・エラー報告・診断ファイルに書かれ、本来は見られない人の手に渡ることです。シークレット（secret）は、パスワード・秘密鍵・API トークン・セッショントークンのように、知っていれば本人として振る舞える値を指します。

以降は、ログ・エラー応答・トレース・エラー報告のように、値がプロセスの外へ書き出される所を出口と呼びます。ログを書く行で `password` を出していなくても、シークレットは別の層から出口へ入ってきます。

{{< figure src="images/cover.webp" alt="シークレットが混ざる 6 つの層を社外に遠い順で上から並べた図。1 値を文字列にするコード: シークレットを含む値をログへ書く（Twitter・GitHub 2018、Facebook 2019）。2 入力を含むエラー文: 変換に失敗した入力を文に入れる（Vault CVE-2025-4166、Kubernetes CVE-2020-8564）。3 エラー報告とトレースの SDK: エラーを丸ごと外部へ送る（Slope の Sentry、OTel の RecordError の実験）。4 panic とスタックトレース: 引数・クラッシュダンプに残る（Go のスタックの実験、Storm-0558 は未立証に訂正）。5 集めて消すログ基盤: 消す処理の抜けと回帰（Vault CVE-2024-8365、GitHub の npm ログ 2022）。6 診断ファイルを渡す人の手: サポートへ添付する（Okta の HAR 2023、Tangem 2024）" caption="シークレットがログへ混ざる層と、層ごとの事故" align="center" >}}

上の図では、本記事で扱う事故と脆弱性が、シークレットの混ざった層ごとに並んでいます。上の層ほどシークレットを作って使うコードに近く、下の層ほど社外に近くなります。シークレットが全ての層を通るわけではなく、どこか 1 つの層で混ざったシークレットが、その下の層を経て社外に出ます。

どの事故も、ログを書く人がシークレットを出そうとしたわけではありません。値を文字列にする、エラー文に入力を入れる、SDK にエラーを丸ごと渡すといった、普段の書き方の先でシークレットが混ざっています。

<br>

本記事では、図の層を上から順に、実際の事故と原因、その層で効く対策を紹介します。コードとランタイムの層は、Go で漏れ方を再現した実験も載せます。最後に、層をまたいでどの順に手を打つかと、漏れていないことをテストで確認する方法を扱います。

実験のコードと出力は [lab](https://github.com/nao1215/debimate/tree/main/content/notes/security/log-leak/lab) に置きました。シークレットの値は全て `CANARY-` で始まる説明用の偽物で、コードの中では定数 `canary` に入っています。外部のサービスには何も送っていません。

---

### 層 1: 値を文字列にするコード

最も単純な漏れ方は、アプリのコードがシークレットをそのままログに書くことです。2018 年 5 月、[Twitter](https://techcrunch.com/2018/05/03/twitter-password-bug/) は、バグによってハッシュにする前のパスワードが内部のログに書かれていたと公表しました。

同じ月に [GitHub](https://www.bleepingcomputer.com/news/security/github-accidentally-recorded-some-plaintext-passwords-in-its-internal-logs/) も、パスワードのリセットに入ったバグで平文のパスワードを内部のログに書いていたと利用者に通知しています。2019 年 3 月には [Facebook](https://about.fb.com/news/2019/03/keeping-passwords-secure/) が、読める形のパスワードを内部のデータストアに保存していたと公表しました。

どれも、DB に保存するパスワードはハッシュにしていました。漏れたのは、それとは別に値を書き出す経路です。認証の処理を正しく作っても、その途中の値を書くログは別に存在します。

<br>

#### 名前で消すフィルターの限界

ログを書く側で、シークレットを消すフィルターを用意していても漏れます。2022 年 8 月に見つかった件では、暗号資産の Solana を扱うウォレットアプリ Slope から、復元フレーズ（mnemonic）と秘密鍵が、エラー監視サービス [Sentry](https://sentry.io/) に送られていました。送り先は、Slope が自分のサーバーで動かしていたとみられる Sentry です。復元フレーズは、ウォレットが持つ全ての秘密鍵を作り直せる単語の並びで、役割は [Wallet](../../blockchain-systems/wallet/) のノートで扱っています。

この件を受けて、Sentry は `privatekey` や `private_key` という名前の項目を保存しない処理を足したと[公表](https://blog.sentry.io/slope-wallet-solana-hack)しました。項目の名前で消すのは、ログやエラー報告の道具でよく使われる守り方です。ただし、名前で消す仕組みには限界があります。

次のコードは、Go の [log/slog](https://pkg.go.dev/log/slog) の `ReplaceAttr` で、キーが `mnemonic` などの属性（ログの 1 行に付けるキーと値の組）を `[FILTERED]` に置き換えます。`ImportParams` は、ウォレット名と復元フレーズを持つ構造体です。その上で、同じ値を 3 通りの書き方でログに渡します。

```go
deny := []string{"mnemonic", "private_key", "password"}
h := slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{
	ReplaceAttr: func(_ []string, a slog.Attr) slog.Attr {
		if slices.Contains(deny, a.Key) {
			return slog.String(a.Key, "[FILTERED]")
		}
		return a
	},
})
log := slog.New(h)
p := ImportParams{WalletName: "main", Mnemonic: canary}
log.Info("import", "mnemonic", p.Mnemonic)        // キーで消える
log.Info("import", "params", fmt.Sprint(p))       // 文字列にまとめると残る
log.Info("import", "params", fmt.Sprintf("%+v", p))
```

{{< figure src="images/filter.webp" alt="ImportParams（WalletName: main、Mnemonic: CANARY-…）を 3 通りで log.Info に渡す。キー mnemonic で渡すと ReplaceAttr のキーが一致し、ログは mnemonic=[FILTERED] になって消える。fmt.Sprint(p) と fmt.Sprintf(&quot;%+v&quot;, p) をキー params で渡すと、params は対象外なので、ログに CANARY-abandon-ability-able が残る" caption="キーの名前で消すフィルターは、文字列にまとめた値を見分けない" align="center" >}}

フィルターが見ているのはキーの名前だけです。構造体を `fmt.Sprint` で文字列にした時点で、どの部分が復元フレーズだったかという情報は消えます。ログの手前で値を文字列にまとめる 1 行が、フィルターを迂回する経路になります。

<br>

#### この層の対策

この層で効くのは、ログに出して良い項目を選んで書くことです。リクエストや設定、構造体を丸ごと渡さず、`wallet_id` や `mnemonic_len` のように出して良い値だけを属性にします。消す項目を並べる拒否リストは、新しい項目や文字列への変換を見逃します。出す項目を並べる許可リストなら、知らない項目は出ません。

もう 1 つは、シークレットを専用の型で包むことです。Go なら、`fmt`・`slog`・`encoding/json` が表示の時に自動で呼ぶ `String()`・`Format()`・`LogValue()`・`MarshalJSON()` が固定の文字列を返す型にシークレットを入れ、中身は明示したメソッドでしか取り出せないようにします。

ただし、包む前と取り出した後の値は守れません。包んだ型を外側の構造体に入れた時も、フィールドが非公開（名前が小文字で始まる）だと `fmt` は包んだ型のメソッドを呼びません。次の例では、メソッドを 2 つだけ書いています（lab では `LogValue()` も実装しています）。

```go
type Secret struct{ v string }

func (Secret) String() string                { return "<redacted>" }
func (Secret) Format(f fmt.State, verb rune) { _, _ = f.Write([]byte("<redacted>")) }

s := Secret{canary}
fmt.Printf("direct:     %+v\n", s)
fmt.Printf("exported:   %+v\n", struct{ S Secret }{s})
fmt.Printf("unexported: %+v\n", struct{ s Secret }{s})
```

```text
direct:     <redacted>
exported:   {S:<redacted>}
unexported: {s:{v:CANARY-abandon-ability-able}}
```

[fmt](https://pkg.go.dev/fmt) は、非公開フィールドが持つメソッドを呼べないので、中身をそのまま表示しました。型は書き間違いを減らす道具で、漏れないことの証明にはなりません。

---

### 層 2: 入力を含むエラー文

2 つ目の層は、エラー文です。不正な入力を受け取った処理は、何が悪かったかを伝えるために、入力の値をエラー文に入れがちです。その入力がシークレットだった場合、エラー文がそのままログに流れます。

2025 年 5 月、シークレットを保管する製品の [HashiCorp Vault](https://developer.hashicorp.com/vault) に、この形の脆弱性 [CVE-2025-4166](https://discuss.hashicorp.com/t/hcsec-2025-09-vault-may-expose-sensitive-information-in-error-logs-when-processing-malformed-data-with-the-kv-v2-plugin/74717) が公表されました。

KV v2 というシークレットの保管機能に、REST API で形の崩れたデータを送ると、変換のエラー文に書き込もうとしたシークレットが入り、サーバーのログと監査ログ（誰がどの操作をしたかの記録）に残りました。公表された監査ログの例は次の通りです。`<sensitive data>` の所に、書き込もうとしたシークレットが入ります。

```text
"error":"error converting input <sensitive data> for field \"data\": '' expected a map, got 'string'"
```

[Kubernetes の CVE-2020-8564](https://github.com/kubernetes/kubernetes/issues/95622) も同じ形です。形の崩れた Docker の設定ファイルを読んだ時、ログの詳しさ（`-v` の値）を 4 以上にしていると、レジストリの認証情報を含む中身がログに出ました。

エラー文ではありませんが、Vault の [CVE-2020-13223](https://discuss.hashicorp.com/t/hcsec-2020-13-vault-proxy-environment-variable-was-logged-to-stdout/18096) も設定値をそのまま出した似た例です。環境変数 `HTTP_PROXY` の URL を標準出力に書き、URL に含まれるプロキシのユーザー名とパスワードも出ました。

<br>

#### Go 標準ライブラリが返すエラー文

Go の標準ライブラリにも、入力をエラー文に入れる関数があります。偽のシークレットを入れて、次の 3 つを試しました。

```go
_, err := strconv.Atoi(canary)
fmt.Println("strconv.Atoi:", err)
_, err = url.Parse("https://user:" + canary + "@example.com:port/")
fmt.Println("url.Parse:   ", err)
u, _ := url.Parse("https://user:" + canary + "@example.com/")
fmt.Println("URL.String:  ", u.String())
fmt.Println("URL.Redacted:", u.Redacted())
```

```text
strconv.Atoi: strconv.Atoi: parsing "CANARY-abandon-ability-able": invalid syntax
url.Parse:    parse "https://user:CANARY-abandon-ability-able@example.com:port/": invalid port ":port" after host
URL.String:   https://user:CANARY-abandon-ability-able@example.com/
URL.Redacted: https://user:xxxxx@example.com/
```

[strconv.Atoi](https://pkg.go.dev/strconv#Atoi) と [url.Parse](https://pkg.go.dev/net/url#Parse) は、変換に失敗した入力をそのままエラー文に入れました。URL を表示用の文字列にする時は、[URL.Redacted](https://pkg.go.dev/net/url#URL.Redacted) を使えばパスワードが `xxxxx` になります。しかし、URL として読めなかった時のエラー文には、その手当てが届きません。

<br>

#### この層の対策

この層で効くのは、エラーを出口に渡す前に、決めておいた分類に写すことです。`err.Error()` の文字列をそのままログやトレースに入れず、`upstream_request_failed` のような分類コードと、固定の説明だけを出します。元のエラーはアプリ内の制御に使い、外へは出しません。

エラー文の中身は、自分のコードよりも依存するライブラリが決めます。Vault の件は、Vault の開発元でさえ形の崩れた入力の経路を見落としていたことを示しています。正常な入力だけでテストしていると、この層の漏れには気づけません。

---

### 層 3: エラー報告とトレースの SDK

3 つ目の層は、エラー報告やトレースの SDK です。SDK は、渡されたエラーやリクエストの情報を丸ごと集めて、外部のサービスに送ります。層 1 で触れた Slope の復元フレーズも、ログファイルではなく、Sentry へ送るエラー報告として集まっていました。

この件は、2022 年 8 月 2 日から Solana のウォレット[約 8,000 個](https://www.theregister.com/2022/08/04/solana_wallet_slope/)で資金が抜かれた事件の調査で見つかりました。後の集計では 9,000 個を超えています。

[ITPro の報道](https://www.itpro.com/security/hacking/368730/auditors-blame-4-million-cryptocurrency-heist-on-leaky-logging-tech)によると、調査した監査会社は、そのうち約 1,400 個のアドレス（ウォレットを指す公開の ID）が Sentry のログに含まれていたと説明しています。残りのアドレスは説明できず、ログからの窃取が流出全体の原因だったかは、Slope の[声明](https://forkast.news/no-conclusive-evidence-solana-loophole/)でも、監査会社から決定的な証拠は出ていないとされています。

<br>

#### OTel の RecordError

[OpenTelemetry](https://opentelemetry.io/)（OTel）は、ログ・トレース・メトリクスを集める仕様と SDK です。トレースは 1 つのリクエストが通った処理の記録で、span はその中の 1 区間です。span にはイベントと属性を付けられます。詳しくは [Distributed Tracing](../../distributed-systems/distributed-tracing/) のノートで扱っています。

Go の OTel SDK v1.47.0 で、エラーを span に記録する `RecordError` を試しました。span は、記録した span をメモリに貯めるテスト用の部品 `SpanRecorder` に記録し、外へは送りません。引数の `key` と `//go:noinline`・`runtime.KeepAlive` は層 4 で説明する実験用の値と印で、ここではエラー文に入れた `canary` を見ます。

```go
//go:noinline
func record(s trace.Span, key [2]uint64) {
	s.RecordError(errors.New("upstream rejected token "+canary), trace.WithStackTrace(true))
	runtime.KeepAlive(key)
}
```

```text
exception.type=*errors.errorString
exception.message=upstream rejected token CANARY-abandon-ability-able
exception.stacktrace=goroutine 1 [running]:
...
main.record({0x69d538, 0x273c589a25a0}, {0xdeadbeefcafe0001, 0x1122334455667788})
```

`RecordError` は、`err.Error()` の文字列をそのまま `exception.message` という属性に入れました。`WithStackTrace(true)` を付けると、スタックトレースも `exception.stacktrace` に入ります。スタックの行に関数の引数が出る件は、次の層で扱います。

SDK のソースでも、`exception.message` に `err.Error()` を入れていることを確認しました（[span.go](https://github.com/open-telemetry/opentelemetry-go/blob/v1.47.0/sdk/trace/span.go)）。

<br>

#### エラー監視サービス自身のログ

本筋の SDK からは少し外れますが、エラー報告の製品も自分のログで漏らします。自分のサーバーで動かす Sentry（self-hosted）には、[CVE-2024-32474](https://github.com/getsentry/security-advisories/issues/11) がありました。

24.3.0 から 24.4.1 の前までは、ユーザー名とパスワードで認証した時、管理者のパスワードを平文で INFO のログに書いていました。管理者の認証を調べるログに、パスワードを含む検証用のオブジェクトを項目として足した変更が原因で、層 1 の値を丸ごと渡す形と同じです。ログの詳しさを下げる運用では防げない、INFO のログで起きた漏れでした。

<br>

#### この層の対策

この層で効くのは、SDK に生のエラー・リクエスト・設定を渡さないことです。層 2 で写した分類コードと固定の説明だけを SDK に渡します。多くの SDK は送信の直前に呼ばれる関数を持っています。Sentry の Go SDK にある [BeforeSend](https://docs.sentry.io/platforms/go/configuration/filtering/) などがその例ですが、届いた時点でエラーの文は `err.Error()` の文字列になっているので、層 1 のフィルターと同じ限界を持ちます。

送る直前の消去は補助と考え、SDK に渡す値を手前で減らす方を先にします。

---

### 層 4: panic とスタックトレース

4 つ目の層は、ランタイムが出すスタックトレースとクラッシュダンプです。Go のスタックトレースは、関数の引数を要素ごとに 16 進で表示します。値で渡した配列や構造体は、先頭から 10 要素までの中身が出ます。文字列は、指す先の番地と長さだけが出ます。

実際の秘密鍵は `[32]byte` のような配列で値渡しされることがあり、その場合は先頭の 10 バイトが出ます。実験では見やすさのために `[2]uint64` を秘密鍵に見立て、配列を引数に取る関数からスタックを出して、引数がどこに現れるかを比べました。`debug.Stack()` は今のスタックを文字列で返す関数です。

未回復の panic は、recover されずにプログラムを落とす panic です。`//go:noinline` と `runtime.KeepAlive` は、最適化で関数が展開されたり引数が消えたりしないようにする実験用の印です。

```go
//go:noinline
func sign(key [2]uint64, msg string) {
	fmt.Printf("%s", debug.Stack())
	runtime.KeepAlive(key)
}

//go:noinline
func panicSign(key [2]uint64) {
	runtime.KeepAlive(key)
	panic("sign failed")
}
```

{{< figure src="images/stack.webp" alt="秘密鍵に見立てた配列を値で渡し、別々の実行で 4 通りの出力を比べた図。panicSign の panic（GOTRACEBACK 既定）は main.panicSign({0xdeadbeefcafe0001, 0x1122334455667788}) を出す。panicSign の panic（GOTRACEBACK=none）は panic: sign failed だけ。sign の debug.Stack()（GOTRACEBACK=none）は main.sign({0xdeadbeefcafe0001, 0x1122334455667788}, …) を出す。record の RecordError（WithStackTrace(true)）は main.record(…, {0xdeadbeefcafe0001, 0x1122334455667788}) を出す" caption="値で渡した配列の中身は、どの出力に出るか" align="center" >}}

`GOTRACEBACK` は、panic で落ちた時に出すスタックの詳しさを決める環境変数です。`GOTRACEBACK=none` を付けると、未回復の panic はメッセージだけになりました。しかし、同じ設定でも `debug.Stack()` は引数を出し続けます。

`debug.Stack()` は内部で [runtime.Stack](https://pkg.go.dev/runtime#Stack) を呼び、runtime.Stack は `GOTRACEBACK` を見ずに表示の詳しさを自分で決めているためです。`sign` の行にある 2 つ目の `{0x846238?, …}` は文字列 `"x"` の欄で、末尾の `?` は値が正確とは限らないことを示します。文字列の中身は出ません。OTel の `RecordError` もこの `runtime.Stack` を使うので、`GOTRACEBACK=none` ではトレースに入るスタックは消えません。

<br>

#### 訂正されたクラッシュダンプの話

プロセスが落ちた時にメモリを丸ごと書き出すクラッシュダンプは、スタックトレースより多くのシークレットを含みます。Microsoft の署名鍵は、中国を拠点とする攻撃者 Storm-0558 に盗まれ、認証トークンの偽造とメールの閲覧に使われました。

2023 年 9 月、Microsoft はその鍵を手に入れた経路を[説明](https://www.microsoft.com/en-us/msrc/blog/2023/09/results-of-major-technical-investigations-for-storm-0558-key-acquisition)しました。2021 年 4 月に署名のシステムが落ちた時のクラッシュダンプに、競合状態（race condition）で鍵が混ざり、ダンプがデバッグ用の環境へ移され、乗っ取られた技術者のアカウントから取られたという内容です。

ところが 2024 年 3 月 12 日、同じ説明のページに追記が入りました。鍵を含むクラッシュダンプは見つかっていない、という訂正です。鍵が攻撃に使われたことは確かですが、クラッシュダンプの経路は確定していません。この件を根拠に引く時は、仮説のまま扱う必要があります。

<br>

#### この層の対策

スタックを出口へ付けるなら、引数を持たない形で自分で作ります。Go なら [runtime.CallersFrames](https://pkg.go.dev/runtime#CallersFrames) で、関数名・ファイル・行だけを取り出せます。`GOTRACEBACK=none` は未回復の panic にしか効かないので、それだけで済んだと考えないようにします。

クラッシュダンプは、ログとは別の問題です。プロセスのメモリを丸ごと書く以上、アプリのコードでは消せません。

シークレットそのものを扱うプロセスを分ける、[HSM](https://csrc.nist.gov/glossary/term/hardware_security_module_hsm)（Hardware Security Module、鍵を外へ出さずに署名する専用の機器）や、クラウドの [KMS](https://cloud.google.com/kms/docs/key-management-service)（Key Management Service）に鍵を置く、クラッシュダンプの保存と持ち出しを制限する、といった設計と運用の対策になります。

---

### 層 5: 集めて消すログ基盤

5 つ目の層は、ログを集めて保存するログ基盤です。ここにはシークレットを消す処理を置くことが多く、その処理の抜けや回帰がそのまま漏れになります。

Vault の [CVE-2024-8365](https://discuss.hashicorp.com/t/hcsec-2024-18-vault-leaks-client-token-and-token-accessor-in-audit-devices/69669) では、監査ログで機密のヘッダーを HMAC（鍵付きのハッシュ）に置き換える処理が、1.17.3 と 1.17.4（Enterprise は 1.16.7 と 1.16.8 も）で回帰して抜けました。クライアントのトークンと、トークンを参照するための ID（accessor）が、監査ログにそのまま残りました。

2022 年 5 月には [GitHub](https://github.blog/news-insights/company-news/npm-security-update-oauth-tokens/) が、npm のサービスが出したログの一部で、リクエストに含まれた認証情報を消す処理が適切に働いておらず、平文の認証情報が内部のログ基盤に残っていたと公表しました。GitHub はログを消し、消す処理を改善しています。

<br>

#### 後段の消去は形しか見ない

ログ基盤で消す処理は、シークレットかどうかを文字列の形で判断します。たとえば、アプリから受けたデータを加工して転送する OTel の Collector には、属性を許可リストと値のパターンで消す [redaction processor](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/processor/redactionprocessor) があります。値のパターンで消す時、次の図にある 2 つの値は区別できません。

{{< figure src="images/pattern.webp" alt="秘密鍵（説明用の偽の値）と取引のハッシュ（説明用の偽の値）は、どちらも 64 文字の 16 進。正規表現 [0-9a-f]{64} は形が同じなので、両方を消すか両方を残すかしかできない。どの値がシークレットかを知っているのは、値を作って受け取るアプリのコード。後段の消去は、アプリの手前で減らした後の最後の網として置く" caption="後段の消去が見るのは文字列の形だけで、何の値かは分からない" align="center" >}}

Ethereum や Bitcoin の秘密鍵と、取引を指す公開の ID である取引のハッシュは、どちらも 64 文字の 16 進です。パターンで秘密鍵を消すと、障害の調査に必要な取引のハッシュも消えます。残せば秘密鍵も残ります。どの値がシークレットかを知っているのは、その値を作って受け取ったアプリのコードだけです。

<br>

#### この層の対策

ログ基盤での消去は、アプリの手前で減らした後に残ったものを拾う、最後の網として置きます。ログ基盤に届く前にアプリが手元へ書いたファイルには、この消去は届きません。消す処理そのものもコードなので、Vault の件のように回帰します。テストの出力からシークレットを消す処理が、シークレットの途中に入った文字色の制御コードでシークレットを見つけられなかった例は、[Snapshot Testing](../../software-testing/snapshot-testing/) のノートで扱っています。消す処理には、シークレットの目印を流して消えることを確認するテストを付けます。

ログそのものも、シークレットを含み得るデータとして扱います。読める人を絞り、保存する期間を決め、ログを別のシステムに複製する時も同じ扱いにします。

---

### 層 6: 診断ファイルを渡す人の手

最後の層は、人がログや診断ファイルを外へ渡す所です。冒頭の Tangem は、アプリのログに書かれた秘密鍵が、この層で社外へ届きました。もう 1 つの例が、2023 年の [Okta](https://sec.okta.com/articles/2023/11/unauthorized-access-oktas-support-case-management-system-root-cause/) です。

Okta のサポートでは、顧客が障害の調査のために HAR ファイルを送ることがありました。HAR（HTTP Archive）は、ブラウザが記録した通信を丸ごと保存するファイルで、Cookie やセッショントークンも含みます。攻撃者は、サポートシステムのサービスアカウント（人ではなくシステムが使うアカウント）を使って、次の順に進みました。

```mermaid
sequenceDiagram
  participant C as 顧客
  participant S as Okta のサポートシステム
  participant A as 攻撃者
  C->>S: 調査のため HAR ファイルを添付
  Note over S: HAR に有効なセッショントークン
  A->>S: サービスアカウントでログイン
  A->>S: 134 顧客のファイルを取得
  A->>C: 5 顧客のセッションを乗っ取る
```

不正なアクセスは、2023 年 9 月 28 日から 10 月 17 日まで続きました。サービスアカウントのユーザー名とパスワードは、社員が業務用のノート PC で使った個人の Google アカウントに保存されていました。Okta は、その個人のアカウントか端末が侵害された可能性が最も高いと説明しています。

アカウントが乗っ取られたことと、HAR に有効なトークンが残っていたことは、別々の段階で起きた問題です。どちらか片方が無ければ、セッションの乗っ取りまでは進みませんでした。

<br>

#### この層の対策

この層で効くのは、渡す前に消すことと、渡したものの寿命を短くすることです。診断ファイルを集める側は、受け取る前か受け取った直後に Cookie やトークンを消し、保存期間を決めます。Tangem のログは 7 日で消える作りで、影響を受けたのは、復元フレーズで有効化してから 7 日以内に、アプリからサポートへ問い合わせた利用者だけでした。

漏れたと分かったら、ログを消すだけでは足りません。漏れたシークレットは、すでに誰かが写しているかもしれません。Okta はファイルに入っていたセッショントークンを無効にし、Vault の公告は該当するシークレットの交換を勧め、Tangem は新しいウォレットへの移し替えを案内しました。どれも、漏れたシークレットを使えなくする対応です。

---

### 層をまたいだ対策の順番

ここまでの対策は、効く順に並べると次の通りです。上の対策ほど、多くの層にまたがる漏れをまとめて減らします。

| 対策（効く順） | 効く層 |
|---|---|
| 1. 鍵をアプリに置かず、HSM・KMS で署名する | 全て（鍵のみ） |
| 2. 出す項目を選び、エラーは分類コードに写す | 1・2・3 |
| 3. シークレットを専用の型で包む | 1 |
| 4. 出口に目印が出ないことをテストする | 1〜5 |
| 5. ログ基盤で消し、読める人と期間を絞る | 5・6 |
| 6. 漏れたらシークレットを交換・無効にする | 漏れた後 |

1 は設計の段階でしか選べませんが、効く範囲が最も広い対策です。鍵を持たないプロセスは、どの層からも鍵を漏らしません。ただし、パスワードやセッショントークンのように、アプリが受け取るしかないシークレットもあります。それらには 2 番以降が必要です。2 と 3 はコードの書き方で、5 は運用です。

4 は、ほかの対策が効いているかを確認する手段です。型を入れても許可リストを書いても、依存するライブラリや SDK のバージョンを上げれば、エラー文や送る内容は変わります。最後に出口を見るテストが無いと、層 2 や層 4 の漏れは本番で初めて見つかります。

<br>

#### 出口に目印が出ないことのテスト

出口のテストでは、偽のシークレット（canary、目印）を入力に入れて処理を通し、ログ・エラー応答・SDK が送るデータのどこにも目印が出ないことを確認します。次のテストは、層 1 の書き方をした `handleImport` と、出す項目を選んだ `handleImportFixed` を同じ検査に掛けます。目印は、そのままの形に加えて、16 進・base64 にした形でも探します。

```go
// handleImport は不具合のある関数。失敗時に引数をまとめてログへ書く。
func handleImport(log *slog.Logger, p ImportParams) {
	log.Error("import failed", "params", fmt.Sprintf("%+v", p))
}

// handleImportFixed は、出して良い項目だけを選んで書く関数。
func handleImportFixed(log *slog.Logger, p ImportParams) {
	log.Error("import failed", "wallet", p.WalletName, "mnemonic_len", len(p.Mnemonic))
}

func forms(secret string) []string {
	return []string{
		secret,
		hex.EncodeToString([]byte(secret)),
		base64.StdEncoding.EncodeToString([]byte(secret)),
		base64.RawURLEncoding.EncodeToString([]byte(secret)),
	}
}

func checkExit(t *testing.T, handle func(*slog.Logger, ImportParams)) {
	t.Helper()
	var out bytes.Buffer
	handle(slog.New(slog.NewJSONHandler(&out, nil)), ImportParams{WalletName: "main", Mnemonic: canary})
	if out.Len() == 0 {
		t.Fatal("ログが 1 行も出ていない。出ないことを漏れないことと取り違えない")
	}
	for _, f := range forms(canary) {
		if strings.Contains(out.String(), f) {
			t.Errorf("出口に目印が出た: %q", f)
		}
	}
}

func TestImportLeaks(t *testing.T)   { checkExit(t, handleImport) }
func TestImportFixedOK(t *testing.T) { checkExit(t, handleImportFixed) }
```

```text
=== RUN   TestImportLeaks
    exit_test.go:49: 出口に目印が出た: "CANARY-abandon-ability-able"
--- FAIL: TestImportLeaks
=== RUN   TestImportFixedOK
--- PASS: TestImportFixedOK
```

不具合のある関数は落ち、項目を選んだ関数は通りました。`out.Len() == 0` の確認は、ログが 1 行も出なかった時に通ってしまうことを防ぐためです。何も出ていないことは、漏れていないことの証明になりません。

このテストで大事なのは、正常な入力だけでなく、層 2 で扱った形の崩れた入力・認証の失敗・タイムアウト・panic の経路にも目印を流すことです。漏れは、普段は通らないエラーの経路で起きてきました。OTel なら、層 3 の実験で使った `SpanRecorder` を出口にして、同じ検査ができます。

---

### 自分のサービスを点検する順

既存のサービスを点検するなら、層の番号順に見ていくのが早いです。まず、シークレットを受け取る入口を挙げ、その値がログ・エラー文・SDK に渡る所を探します。次に、依存するライブラリが入力をエラー文に入れないか、形の崩れた入力で試します。SDK の設定は、スタックトレースやリクエストの本文を送る設定になっていないかを見ます。

その上で、ログ基盤の消去と保存期間、サポートが受け取る診断ファイルの扱いを確認します。最後に、目印を流す出口のテストを CI に足せば、次の変更で同じ層から漏れた時に気づけます。シークレットをアプリに置かない設計を選べる段階なら、それが最も多くの層をまとめて閉じます。

<br>

シークレットの漏洩はログだけの話ではありません。リポジトリへの誤ったコミットについては、[GitHub Personal Access Token をコミットする人がいた話](/post/ja/2025-04-27-github-personal-access-tokenをコミットする人がいた話、類似例、漏洩/)に書きました。


