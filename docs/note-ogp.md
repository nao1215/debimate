# 技術ノートのOGP画像

`notes` と `ml` の記事では、トップページと共通の `note_cover.html` を
960 × 540 のPNGにして、OGPとXのカードに指定する。
文字組みは `note_title_image.html`、背景は `home_note_banner.html` が担当する。

本番用の生成は `make build`（または `make lint-links`）で実行する。
初回は `npm ci`、`npx playwright install --with-deps chromium` と
日本語フォント `fonts-noto-cjk` のインストールが必要。
既存のChromeを使う場合は `CHROME_PATH=/usr/bin/google-chrome make build`。
GitHub Actionsでも同じ手順で画像を生成する。

`hugo` 単独や `hugo server` はPNGを生成しない。
ローカルでOGPも確認するときは `make build` を使う。
Hugoが `public/assets/note-ogp/` に描画用HTMLを出力し、
`scripts/generate_note_ogp.mjs` がローカルの成果物だけを読み込んでPNGを作る。
描画用HTMLはnoindex指定。タイトルや背景が変わると画像URLも変わる。
