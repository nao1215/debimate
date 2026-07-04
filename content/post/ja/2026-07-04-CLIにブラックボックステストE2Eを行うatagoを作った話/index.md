---
title: "CLI向けブラックボックス E2E テストランナー nao1215/atago を作った"
type: post
date: 2026-07-04
draft: true
categories:
  - "linux"
cover:
  image: "images/atago-logo.jpg"
  alt: "atago-logo"
  hidden: false
---

###  前書き：LLM の登場で自作 OSS の E2E テストを書く機会が増えた

LLM が登場してから、E2E（End to End） テストを書くのが楽になりました。維持は相変わらず大変ですが。

具体例としては、業務では [k1LoW/runn](https://github.com/k1LoW/runn) を利用して API をシナリオベースで E2E したり、プライベートでは [shellspec/shellspec](https://github.com/shellspec/shellspec) を使って CLI のブラックボックステストしています。LLM に自然言語でテスト観点やユースケースを書けば、テストを実行するための spec ファイルを生成してくれます。いい時代になりました。

大前提として、runn は API サーバー寄りのテスト、ShellSpec はシェルスクリプト寄りのテストに最適化されたテスティングフレームワークと言えるでしょう。どちらも素晴らしいツールであり、CLI のテストにも利用できます。私は、ShellSpec を気に入りすぎて、[Software Design 誌で ShellSpec に関する記事を寄稿](https://gihyo.jp/magazine/SD/archive/2024/202412)しました。

しかし、これらのツールでは私のユースケースに合わない部分がありました。私が重要視したのは、以下のポイントです。
- ターゲットは、サーバーやシェルスクリプトではなく、ターミナルで普段使いするコマンド
- 対話型 CLI がテストできること
- PR 作成時に CI しても気にならないほど、実行が高速であること
- 画像、PDF、金融特有フォーマットなどの入出力を取り扱えること
- クロスプラットフォームで実行しやすいこと
- 特定の言語限定のツールでないこと

私は幅広い領域の CLI を作りがちであり、Linux/macOS/Windows 環境で動作することを重要視しています。また、私は CI 待ちが嫌いな性格です。私のユースケースに合うテスティングツールを探すより、自作した方が話が早いと結論づけました。私が OSS 開発を続ける限り、テスティングツールを使い続けるので余裕でペイできると判断しました。

このような流れで開発したのが [nao1215/atago](https://github.com/nao1215/atago) です。本記事では、v0.3.0時点の機能を一部紹介します。

![demo](./images/atago-demo.gif)


---

### atago の特徴

atago は、コマンドを実際に実行し、YAML で定義したテストケースにもとづいて stdout / stderr / exit code / 生成ファイル / snapshot / 対話操作まで検証します。CLI 向けブラックボックス E2E テストランナーです。

意図的に runn と ShellSpec と競合しないようにしました。つまり、シナリオベースの API サーバーをテストしたい場合は runn を採用し、シェルやシェルスクリプトのテストをしたい場合は ShellSpec を採用してください。atago は、ターミナルで普段使いするコマンドをターゲットにしています。

以下、atago の特徴（抜粋）です。
- クロスプラットフォーム対応
- YAML による宣言的なテストケース記述（複雑度を下げるため、意図的に式を不採用）
- デフォルト並列実行による高速な E2E
- 実バイナリをそのまま対象にしたブラックボックステスト
- `atago record`：実行結果からテストケースの雛形生成
- `atago snapshot`：Golden Test ファイル（期待値データ）の生成
- 対話型 CLI の操作フロー検証
- 標準出力・終了コード・生成ファイル・ディレクトリ差分・画像・PDFなどをチェック
- Mock Server / DB / SSH など、CLI が依存する外部環境をテスト実行時に用意できる
- CI ログやスナップショットへのクレデンシャル流出を抑えるマスキング機構
- YAML ファイルを Markdown ドキュメントに変換
- GitHub Actions でビルド済み atago を取得する[nao1215/setup-atago](https://github.com/nao1215/setup-atago) を提供

機能追加だけでなく、現在は atago 自身を atago で E2E し、ドッグフーディングしながら品質を上げるフェーズに入っています。

---


### 実行例

atago は、実行時に指定したディレクトリ以下を再帰的に探索し、YAML をテストケース定義ファイルとみなしてテストします。以下が実行例です。ドットがｽｺｽｺするのが好きなので、ｽｺｽｺさせました。
```shell
$ atago run ./specs
...............................................

PASSED  47 scenarios: 47 passed, 0 failed, 0 errored, 0 skipped (1.2s)
```

テスト失敗時は、以下の出力になります。 unified diff 形式で差分を表示するため、出力と期待値のズレが分かりやすくなっています。
```shell
FAILED: demo / greeting matches its golden

Step:
  assert stdout snapshot

Diff (-expected +actual):
  --- snapshot (golden)
  +++ actual
  @@ -1,3 +1,3 @@
   hello
  -WORLD
  +world
   bye

Hint:
  stdout did not match snapshot "snaps/greeting.txt" (update with --update-snapshots if intended)
```

---

### YAML（テストケース）サンプル

[Example](https://github.com/nao1215/atago#examples)から、atago の守備範囲が伝わりやすいものを 3 つだけ抜粋します。atago は、基本的に機能を追加するたびに Example コードを用意し、その Example コードが実装と乖離しないように CI で確認しています。

#### 終了コード・標準出力・標準エラー出力の検証

```yaml
version: "1"

suite:
  name: run and assert

scenarios:
  - name: one assert can check several targets at once
    steps:
      - run:
          shell: true
          command: echo hello atago
      - assert:
          exit_code: 0
          stdout:
            contains: hello
          stderr:
            empty: true
```

#### 対話型 CLI の expect / send 検証

```yaml
version: "1"

suite:
  name: pty

scenarios:
  - name: drive an interactive session with expect and send
    skip:
      os: windows
    steps:
      - pty:
          command: cat
          timeout: 10s
          session:
            - send: "hello interactive world\n"
            - expect: "hello interactive world"
            - send: ""
      - assert:
          exit_code: 0
          stdout:
            contains: hello interactive world
```

#### Mock Server を用いた API クライアント CLI 検証

```yaml
version: "1"

suite:
  name: mock http server

scenarios:
  - name: the CLI posts a report and the mock records exactly what was sent
    skip:
      os: windows
    mock_servers:
      - name: api
        routes:
          - method: POST
            path: /v1/reports
            status: 201
            json: { id: "r-1", ok: true }
    steps:
      - run:
          shell: true
          command: >-
            curl -sf -X POST -H 'Authorization: Bearer tok-123'
            -d '{"title":"report"}' ${api.url}/v1/reports
      - assert:
          exit_code: 0
          stdout:
            json: { path: "$.id", equals: "r-1" }
      - assert:
          mock:
            name: api
            path: /v1/reports
            method: POST
            count: 1
            header: { name: Authorization, matches: "^Bearer " }
            body:
              json: { path: "$.title", equals: "report" }
```

---

### record 機能

`atago record` は、CLI を一度だけ実行し、その結果からテストケースの雛形を生成する機能です。多くの人が YAML を手で書くのが苦痛だと思われたので、用意しました。

例えば `atago record --out mytool.atago.yaml -- mytool convert input.txt` のように実行すると、終了コード、標準出力、標準エラー出力、生成されたファイルを観測し、それらをもとに YAML を出力します。

対話型 CLI 向けには `atago record --pty` も用意しています。pseudo terminal 上で実際にコマンドを操作するため、対話形式の CLI や TTY 前提で挙動が変わるコマンドでも、最初の YAML を手で全部書かなくて済みます。

なお、`atago init`で YAML テンプレートファイルを出力する方法もあります。

---

### snapshot 機能（Golden Test）

`atago snapshot` は、CLI の出力を Golden File（期待値データ）として保存し、以後の実行結果と比較する機能です。`contains` や `equals` で細かく assert を積み上げる代わりに、「この出力全体が期待値である」と丸ごと固定できます。

特に、help メッセージ、整形済みテキスト、レポート出力、Markdown 生成結果のように、部分一致より全体一致で見たいケースと相性が良いです。差分が出た場合は unified diff 形式で確認できます。また、snapshot は単純な文字列比較ではありません。ANSI カラーコード、一時ディレクトリ、UUID、タイムスタンプ、ポート番号、CRLF などを正規化して比較するため、環境差分で壊れにくいようにしています。

更新時は、以下のコマンドで Golden File を再生成します。

```shell
atago snapshot update spec.atago.yaml
```

`atago snapshot` は、YAML（テストケース）に書かれているテストをそのまま実行し、`snapshot:` を使っている assert に到達したら、比較の代わりにその時点の出力を Golden File へ書き込みます。

snapshot を利用した YAML の例を以下に示します。

```yaml
version: "1"

suite:
  name: snapshot

scenarios:
  - name: stdout matches the committed golden file
    steps:
      - run:
          shell: true
          command: echo stable greeting
      - assert:
          stdout:
            snapshot: snapshots/greeting.txt
```

![snapshot](./images/snapshot.gif)

### GitHub Actions 対応

[nao1215/setup-atago](https://github.com/nao1215/setup-atago) を利用すると、事前にビルドされたリリースバイナリをダウンロードしてセットアップします。Linux、macOS、Windows (amd64 / arm64)向けのバイナリを自動で準備します 。バージョンをピン留めする機能もあります。

以下が参考例です。

```yaml
name: behavior-specs
on: [push, pull_request]
jobs:
  atago:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: nao1215/setup-atago@v0
      - run: atago run --ci --report gha ./specs
```

- `--ci`：色に依存しない出力（CI ログの可読性を落とさないためのオプション）
- `--report`：レポート形式。json, junit, gha, tap をサポート

---

### atago で E2E テストした OSS

atago の信頼性を高めるために、atago 自身 / nao1215 の OSS（8個） / 有名な OSS（29個） を atago で E2E しました。テスト対象 OSS を網羅的にテストしているわけではなく、基本機能だけピックアップでテストしています。

下表にテスト対象の OSS を示します。Specs はテストケース集へのリンク、Docs はテストケースから変換した Markdown ドキュメントへのリンクです。

私が開発した OSS 向けのテスト：

| ツール名 | 機能 | Specs | Docs |
|------|---------|-------|------|
| [atago](https://github.com/nao1215/atago) | 本記事のツール | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/atago) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/atago.md) |
| [gup](https://github.com/nao1215/gup) | `$GOBIN` 内の Go 製コマンドラインツールの更新・管理 | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/tools/gup) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/gup.md) |
| [sqly](https://github.com/nao1215/sqly) | CSV/TSV/LTSV/JSON/Parquet/Excel/ACH/Fedwire に対する SQL 実行 | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/tools/sqly) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/sqly.md) |
| [truss](https://github.com/nao1215/truss) | 画像変換（形式変換、リサイズ、再エンコード） | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/tools/truss) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/truss.md) |
| [iso8583tool](https://github.com/nao1215/iso8583tool) | ISO 8583 決済メッセージのデバッグ・解析 | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/tools/iso8583tool) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/iso8583tool.md) |
| [jose](https://github.com/nao1215/jose) | JOSE による署名・暗号化 | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/tools/jose) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/jose.md) |
| [career](https://github.com/nao1215/career) | 単一 YAML から履歴書・経歴書 PDF を生成 | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/tools/career) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/career.md) |
| [mimixbox](https://github.com/nao1215/mimixbox) | 多数の Unix コマンドを 1 つの BusyBox 風バイナリに同梱 | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/tools/mimixbox) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/mimixbox.md) |
| [mobilepkg](https://github.com/nao1215/mobilepkg) | iOS / Android パッケージのメタデータ・セキュリティの解析 | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/tools/mobilepkg) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/mobilepkg.md) |


有名な OSS 向けのテスト：

| ツール名 | 機能 | License | Specs | Docs |
|---------|---------|---------|-------|------|
| [git](https://git-scm.com/) | バージョン管理 | GPL-2.0 | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/thirdparty/git) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/git.md) |
| [jq](https://jqlang.org/) | JSON 処理 | MIT | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/thirdparty/jq) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/jq.md) |
| [fzf](https://github.com/junegunn/fzf) | 対話型ファジーファインダ | MIT | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/thirdparty/fzf) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/fzf.md) |
| [redis](https://redis.io/) | インメモリデータストア | RSALv2/SSPLv1 | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/thirdparty/redis) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/redis.md) |
| [hugo](https://gohugo.io/) | 静的サイトジェネレータ | Apache-2.0 | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/thirdparty/hugo) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/hugo.md) |
| [openssl](https://www.openssl.org/) | 暗号ツールキット | Apache-2.0 | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/thirdparty/openssl) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/openssl.md) |
| [sqlite3](https://sqlite.org/cli.html) | 埋め込みデータベース | Public Domain | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/thirdparty/sqlite3) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/sqlite3.md) |
| [caddy](https://caddyserver.com/) | Web サーバー | Apache-2.0 | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/thirdparty/caddy) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/caddy.md) |
| [coredns](https://coredns.io/) | DNS サーバー | Apache-2.0 | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/thirdparty/coredns) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/coredns.md) |
| [gitea](https://about.gitea.com/) | Git ホスティングサービス | MIT | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/thirdparty/gitea) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/gitea.md) |
| [gotify](https://gotify.net/) | 通知サーバー | MIT | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/thirdparty/gotify) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/gotify.md) |
| [grafana](https://grafana.com/oss/grafana/) | 可観測性プラットフォーム | AGPL-3.0 | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/thirdparty/grafana) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/grafana.md) |
| [mailpit](https://mailpit.axllent.org/) | メールテストサーバー | MIT | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/thirdparty/mailpit) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/mailpit.md) |
| [minio](https://min.io/) | S3 互換オブジェクトストレージ | AGPL-3.0 | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/thirdparty/minio) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/minio.md) |
| [aws-cli](https://aws.amazon.com/cli/) | AWS 向け CLI | Apache-2.0 | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/thirdparty/awscli) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/awscli.md) |
| [python3](https://www.python.org/) | プログラミング言語処理系 | PSF-2.0 | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/thirdparty/python) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/python.md) |
| [ssh-keygen](https://www.openssh.com/) | SSH 鍵生成ツール | BSD | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/thirdparty/ssh-keygen) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/ssh-keygen.md) |
| [ffmpeg](https://ffmpeg.org/) | 動画・音声変換ツール | LGPL/GPL | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/thirdparty/ffmpeg) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/ffmpeg.md) |
| [pandoc](https://pandoc.org/) | ドキュメント変換ツール | GPL-2.0+ | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/thirdparty/pandoc) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/pandoc.md) |
| [terraform](https://www.terraform.io/) | IaC ツール | BUSL-1.1 | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/thirdparty/terraform) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/terraform.md) |
| [age](https://age-encryption.org/) | ファイル暗号化ツール | BSD-3-Clause | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/thirdparty/age) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/age.md) |
| [nats](https://nats.io/) | メッセージングシステム | Apache-2.0 | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/thirdparty/nats) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/nats.md) |
| [ntfy](https://ntfy.sh/) | Push 通知サービス | Apache-2.0 | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/thirdparty/ntfy) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/ntfy.md) |
| [prometheus](https://prometheus.io/) | 監視システム | Apache-2.0 | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/thirdparty/prometheus) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/prometheus.md) |
| [pushgateway](https://github.com/prometheus/pushgateway) | メトリクス受け渡しゲートウェイ | Apache-2.0 | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/thirdparty/pushgateway) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/pushgateway.md) |
| [rclone](https://rclone.org/) | ファイル同期ツール | MIT | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/thirdparty/rclone) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/rclone.md) |
| [restic](https://restic.net/) | バックアップツール | BSD-2-Clause | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/thirdparty/restic) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/restic.md) |
| [transfer.sh](https://github.com/dutchcoders/transfer.sh) | ファイル共有サービス | MIT | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/thirdparty/transfersh) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/transfersh.md) |
| [webhook](https://github.com/adnanh/webhook) | Webhook 受信サーバー | MIT | [specs](https://github.com/nao1215/atago/tree/main/test/e2e/thirdparty/webhook) | [docs](https://github.com/nao1215/atago/blob/main/doc/e2e/webhook.md) |

---

### atago の由来

atago は、愛宕（あたご）から名付けました。愛宕は、防火の神様です。IT 業界では炎上プロジェクトと呼ばれる人災があり、「atago が炎上を食い止める存在まで成長すると嬉しい」という思いを込めました。atago は Go 製ツールなので、末尾に"go"が付いているのもポイント高かったです。

パブリック公開直前まで名前が決まらず、"b3spec（Black Box Behavior Spec）"として開発していました。「長年使うツールなのに、b3spec はなんか味気ないな」と思い、ChatGPT と壁打ちしながら決めました。他の候補は、hegi（新潟のへぎそばに使う箱）、nagisa（落ち着いたテストツール感）、amon（隠されたものという意味。[SHADOW HEARTS](https://ja.wikipedia.org/wiki/%E3%82%B7%E3%83%A3%E3%83%89%E3%82%A6%E3%83%8F%E3%83%BC%E3%83%84) から借用）でした。

---

### 最後に：テスティングツール再び

atago は、約3年前のリベンジでもあります。

私は2023年頃に Go 向けの [nao1215/spectest](https://github.com/nao1215/spectest) と [nao1215/hottest](https://github.com/nao1215/hottest) を作り、API E2E テスト、テスト結果の Markdown ドキュメント化、テスト実行中のドットｽｺｽｺを実現していました。

spectest は [steinfletcher/apitest](https://github.com/steinfletcher/apitest) をフォークして改良していたこともあり、実装の困難さを感じていました。他人の書いたコードを修正するのは難しいものです。さらに、「Go でしか使えない」「E2E ライブラリは製品コードに埋め込みづらいし、[onsi/ginkgo](https://github.com/onsi/ginkgo) が似たポジションで知名度があった」「[k1LoW/runn](https://github.com/k1LoW/runn) の方向性が自分好みで、runn の設計センスに勝てる気がしない（k1LoW 氏が開発するツールはどれも設計センスが良いですよね）」と、複数の課題を感じて開発を中断していました。バックエンドエンジニア歴1年の段階では、背伸びした開発だったとも言えます。

そこから2年強ほどの期間が経過し、「runn（+ ShellSpec）と競う必要はない」「自分の課題を解決するツールであればよい」と割り切れるぐらいには大人になりました。atago は完全に自分向けです。正直、CLI を E2E したい開発者は少数派だと考えています。それでも、自分向けにツールを作ると、自分の需要を確実に満たすので「良いツール作ったな！」と自己肯定感を高められてオススメです。

---

### 余談

atago をパブリック公開する前に、[知り合い（spectest 作った頃の同僚）が存在を速攻で検知](https://x.com/shogo82148/status/2072313182333567261?s=20)してて、「GitHub を SNS みたいに使っている人だ」と思わずにいられませんでした。
