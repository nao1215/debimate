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
スイートは既定で最大 4 本を同時に流す。`BROWSER_CHECK_JOBS=1` で 1 本ずつに戻せる（失敗の切り分け用）。キー入力の間隔で合否が決まる archive_scroll と home_scroll は、CPU の取り合いで誤って落ちるため、並列の分が終わった後に 1 本ずつ流す。
サーバーは検査終了時に停止する。ポート使用中なら既存サーバーを流用せず失敗する。

検査対象:

- トップのスクロール: 一覧データの応答に200msの遅延を加え、スペースキーを12回操作。1440×900・1440×1200・390×844で、各回の移動量が画面高の75%以上あること、初期カード数が72枚以内であること、カードの重複がないことを確認する。実測値は `reports/browser/home-scroll.json` に保存する。FPSの閾値はCIマシンに左右されるため設けない。
- トップ: 追加読み込み、更新・戻る操作、通信失敗時の再試行、全記事の重複なし。
- 一覧のスクロール: `/post/`・`/post/ja/`・`/weeknotes/`・`/weeknotes/2026/` の追加読み込み境界の近くから最大3組の操作を行い、少なくとも3ページの追加取得を確認する。応答に200msの遅延を加え、1440×900・1440×1200・390×844でスペースキーの移動量が画面高の75%以上あることを確認する。年別ページも本文の長さにかかわらず境界付近まで移動して検査し、全件読了後の正常な停止は除外し、実測値を `reports/browser/archive-scroll.json` に保存する。
- Posts・weeknotes・2026年年間ページ: スクロール読み込み、更新直前の位置復元、戻る操作、古いアンカー、JavaScript 無効時のリンク。
- 検索: 未入力時の索引取得なし、日本語変換イベント、再試行、索引再利用、Escape。
- Games: 3本のアニメーションWebPの読み込み、レスポンシブ表示、video要素がないこと。
- トップのアニメーション: 追加読み込みを最後まで行い、全デモ画像で実際に表示フレームが変化することを確認する。
- MP4再導入の防止: `check_asset_delivery.py` が、公開用ファイル・HTMLのMP4参照・video要素を検出したら失敗する。GIFとアニメーションWebPは共通の画像検証で扱う。

トップ・一覧・検索・トップ画像は幅 390px と 1440px、Games は幅 390px で検査する。
本番向け生成物をそのまま使い、テスト内の記事遷移先だけローカルURLへ置き換える。
外部通信は遮断する。年間ページ中の Mermaid はスタブで読み込み、外部CDNの可用性には依存しない。
各スクリプトに3分の上限を設け、失敗時のログとスクリーンショットは `reports/browser/` に保存する。
CI は失敗時のみ診断ファイルを7日間保存する。

依存は検証専用で、公開サイトには同梱しない。
[Playwright / playwright-core は Apache-2.0](https://github.com/microsoft/playwright/blob/v1.58.2/LICENSE)、
macOS用の任意依存 fsevents は MIT（lockfile参照）。
Chromium の配布物にはブラウザ自身と同梱コンポーネントのライセンスが含まれる。
