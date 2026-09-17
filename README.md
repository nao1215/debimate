# debimate とは

Nao1215(nchika)のブログです。  
https://debimate.jp

週報（Weeknotes）は `make weeknote 20260914` で作成します。日付を省略すると
今週の月曜を使います。`make weeknotes` と従来の `make weekly` も利用できます。

本文と画像は `content/weeknotes/<YYYY>/<MM-DD>/`、テンプレートは `layouts/weeknotes/` にあります。
公開 URL は `/weeknotes/YYYY-MM-DD/` を維持します。

`/weeknotes/` は、年ごとに「全週報」と各週のリンクを並べ、各週の下に
本文の `####` 見出しを箇条書きにした目次です。
「全週報」のリンク（例：`/weeknotes/2026/`）には、その年の週報全文をまとめています。
各話題の個別ページでは、目次の並び順に前後の話題へ移動でき、フッター中央から
その年のまとめに戻れます。週は新しい順、同じ週の話題は本文の順です。

ページは `content/weeknotes/_content.gotmpl` でビルド時に生成するため、
今までどおり週報の Markdown を更新するだけで反映されます。
個別 URL の末尾は見出しのハッシュです（見出しを変更すると URL も変わります）。

旧 `/weekly/` と各週の URL は `/weeknotes/` へ転送し、旧 RSS と画像 URL も維持しています。
GitHub Pages 用の HTML 転送で、JavaScript が有効ならクエリとフラグメントも引き継ぎます。

## 新規コンテンツと旧 URL の検証

新規記事・週報の `index.md` に `aliases` を書く必要はありません。
`aliases` は、公開済みページの URL を変更した場合に旧 URL を維持するための設定です。

移行用の対象は `data/legacy_urls.json` に固定しています。通常の新規投稿では
この一覧も変更しません。既存記事の WordPress・旧 Hugo URL と、週報の
`/weekly/` URL・画像・RSS の互換性を保つために利用します。
一覧には、移行後に既に公開された互換 URL も含めています。
新規週報には `/weekly/` の転送や画像コピーを作らず、旧 RSS の購読者にも
`/weeknotes/` の URL と GUID で配信します。

- `make redirects-check`：固定した移行対象の記事と静的リダイレクトを検証
- `python3 scripts/check_weeknotes.py`：ビルド後の移行対象の週報・画像と旧 RSS を検証
- `make lint-links`：サイトをビルドし、新規投稿を含むサイト内リンク・画像・参照先の見出しを検証
- `python3 -m unittest discover -s scripts -p 'test_*.py'`：新規投稿に移行用 URL を要求しないことなどの回帰テスト
