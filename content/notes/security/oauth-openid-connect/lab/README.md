# ローカル実験

Python 3.9 以降の標準ライブラリだけで実行できます。

```sh
python3 run.py
```

`output.txt` は Python 3.14 で実行した結果です。

127.0.0.1 の空きポートで、説明用の authorization server（`/authorize`・`/token`・`/userinfo`）を起動します。外部のサービスには接続しません。登録した redirect URI（`https://photo.example/callback` など）にはアクセスせず、302 応答の `Location` から code と state を取り出します。

本番の実装ではありません。ID Token の署名は公開鍵暗号ではなく HMAC で代用し、ログイン画面と同意画面を省いて利用者名をクエリで渡し、code と token の有効期限、client 認証、`exp`・`iat` などの検証も省いています。
