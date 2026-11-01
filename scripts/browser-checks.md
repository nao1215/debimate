# ブラウザ操作の公開前検証

CI は Ubuntu 24.04 / Node.js 24 で、ビルド済みの `public/` を検査する。
検査失敗時は Pages artifact のアップロードとデプロイへ進まない。
Playwright は `package-lock.json` で固定し、対応する Chromium をインストールする。

ローカル実行:

```sh
npm ci --ignore-scripts --no-audit --no-fund
npx playwright install --with-deps chromium
make build
make check-browser
```

既存の Chrome を使う場合は `CHROME_PATH=/usr/bin/google-chrome make check-browser`。
`BROWSER_TEST_PORT`（既定値 8138）で HTTP サーバーのポートを変更できる。
サーバーは検査終了時に停止する。ポート使用中なら既存サーバーを流用せず失敗する。

検査対象:

- トップ: 追加読み込み、更新・戻る操作、通信失敗時の再試行、全記事の重複なし。
- Posts・weeknotes・2026年年間ページ: スクロール読み込み、更新直前の位置復元、戻る操作、古いアンカー、JavaScript 無効時のリンク。
- 検索: 未入力時の索引取得なし、日本語変換イベント、再試行、索引再利用、Escape。
- Games: 表示中の自動再生、範囲外の停止、遅延取得、動きを減らす設定。
- トップの週報動画: 過去の追加読み込み分も探し、実フレームの再生と範囲外の停止。

トップ・一覧・検索・トップ動画は幅 390px と 1440px、Games は幅 390px で検査する。
本番向け生成物をそのまま使い、テスト内の記事遷移先だけローカルURLへ置き換える。
外部通信は遮断する。年間ページ中の Mermaid はスタブで読み込み、外部CDNの可用性には依存しない。
各スクリプトに3分の上限を設け、失敗時のログとスクリーンショットは `reports/browser/` に保存する。
CI は失敗時のみ診断ファイルを7日間保存する。

依存は検証専用で、公開サイトには同梱しない。
[Playwright / playwright-core は Apache-2.0](https://github.com/microsoft/playwright/blob/v1.58.2/LICENSE)、
macOS用の任意依存 fsevents は MIT（lockfile参照）。
Chromium の配布物にはブラウザ自身と同梱コンポーネントのライセンスが含まれる。
