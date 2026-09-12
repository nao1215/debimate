# debimate とは

Nao1215(nchika)のブログです。  
https://debimate.jp

週報（Weeknotes）は `make weeknote 20260914` で作成します。日付を省略すると
今週の月曜を使います。`make weeknotes` と従来の `make weekly` も利用できます。

本文と画像は `content/weeknotes/<YYYY>/<MM-DD>/`、テンプレートは `layouts/weeknotes/` にあります。
公開 URL は `/weeknotes/YYYY-MM-DD/` を維持します。
旧 `/weekly/` と各週の URL は `/weeknotes/` へ転送し、旧 RSS と画像 URL も維持しています。
GitHub Pages 用の HTML 転送で、JavaScript が有効ならクエリとフラグメントも引き継ぎます。
