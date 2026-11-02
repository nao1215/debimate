# OSS directory

`/oss/` は `data/oss_catalog.json` と `layouts/oss/oss.html` から静的生成する。
掲載対象は [プロフィール README](https://github.com/nao1215/nao1215) にある保守中の OSS と、追加指定された `setup-*` GitHub Actions。
初回は 2026-11-03 に README と GitHub REST API を取得し、41 リポジトリを収録した。

## 更新

- 2026-11-03 に Pages 設定を確認した13件のうち12件の実ページを確認。omokage は Pages 設定があるが公開 URL が404のため `website` を付けていない。
- `website` は GitHub Pages API の公開 URL と実ページを照合して設定する。リポジトリの `homepage` が空でも Pages が公開されていることがあるので、`has_pages` も確認する。
- プロフィール README と照合して `projects` の追加・削除を行う。アーカイブ済みの旧作品は含めない。
- `stars` は GitHub GraphQL API の `stargazerCount`。`scripts/fetch_oss_stars.py` が全件を一括取得して `asOf` とともに更新する。取得・検証が全部成功したときだけファイルを置き換える。上位4件はビルド時に自動選択する。
- 既存の `deploy.yml` で Hugo ビルド前に取得する。毎週月曜 00:10 JST、手動実行、通常のデプロイ時に更新される。取得値は OSS 一覧とトップページの Featured OSS の両方に反映し、自動コミットはしない。ローカルのスナップショットを更新する場合は `python3 scripts/fetch_oss_stars.py`（gh の認証が必要）。
- `category` は用途、`language` は実装言語、`kind` は利用形態。説明文は各 README と照合する。
- `article` は Hugo のコンテンツパス（`content` と `index.md` を除く）。記事 URL はテンプレートで解決する。
- 紹介記事は執筆当時の情報。現在のインストール方法と仕様は README から参照できる。

## 配信と検証

一覧は JavaScript なしでも全件閲覧可能。小さなページ専用 JS で人気順・用途別の切り替えと検索を追加する。初期表示はスター数上位4件。キーワード入力・言語選択時は「すべて」へ切り替えて全件から検索する。その後に用途タブを選べば検索条件を保ったまま用途も絞り込める。
ページ専用 CSS は `/oss/` だけでロード。スターは文字、カードは About と共通の `.oss-grid` / `.oss-card` を利用し、名前・言語・スター数・説明・リンクを表示する。カード画像や外部バッジは読み込まない。
閲覧時の外部 API 通信は不要。通常のローカル Hugo ビルドは保存済みデータだけで動く。

`hugo --minify` 後に `make check-browser` で PC・モバイル・JS 無効時の表示と絞り込みを検証する。
単独なら HTTP サーバーで `public/` を配信し `node scripts/check_oss_browser.mjs http://127.0.0.1:PORT`。
`make check-performance` は OSS ページの HTML 容量も検証する。
