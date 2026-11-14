---
title: "PKI - 公開鍵と証明書を信頼の連鎖につなぐ"
date: 2026-11-08
draft: false
series: ["技術ノート", "Security"]
tags: ["security", "pki", "x.509", "tls"]
weight: 10
wrapTables: true
topics: ["Authentication / Identity"]
---

PKI（Public Key Infrastructure、公開鍵基盤）は、公開鍵と名前や組織の結び付きを証明書と信頼の連鎖で検証する仕組みです。公開鍵だけでは、接続先が本当にその鍵の持ち主か分かりません。

Web ブラウザで `https://example.test` を開く時は、接続先が示した公開鍵と `example.test` の関係を確認する必要があります。これは、利用者を確認する [Authentication](../authentication/) とは別に、接続先のサーバーを認証する処理です。

この関係を記録するデータが X.509 証明書です。証明書と失効リストのプロファイル、および証明書パス検証の手順は、[RFC 5280](https://www.rfc-editor.org/rfc/rfc5280) で定められています。

証明書を発行する CA（Certification Authority、認証局）は、証明書ポリシーに従って申請者と識別子を確認し、証明書に署名します。検証する側は、あらかじめ信頼する CA の証明書を trust store に持ち、その署名をたどります。

以下は、trust store から署名をたどる検証と、検証で拒否される箇所を示した図です。

{{< figure src="images/pki_concept.svg" alt="端末の trust store の枠の中には Root CA だけがあり、サーバーが送る Intermediate とサーバー証明書は署名の矢印で外側につながる。サーバー証明書の名前・期限・用途は黄土色の枠で確認し、合わなければ拒否される。サーバー証明書を CA として使った場合は、赤い × の所で拒否される。" caption="trust store の Root CA から署名をたどる検証と、拒否される箇所" align="center" >}}

上記の図で信頼の起点になる Root CA は、接続先から受け取るものではありません。OS、ブラウザ、組織の端末管理などがあらかじめ trust store に入れた証明書です。Intermediate CA は Root CA の秘密鍵を日常的な発行に使わずに済むよう、発行権限を分けます。

<br>

本記事では、TLS（Transport Layer Security）でサーバー証明書を検証する流れを取り上げ、次の疑問に答えます。

- CA の署名だけで、なぜ接続先を信頼できるのか。
- hostname、期限、証明書チェーンは、それぞれ何を防ぐのか。
- CA が発行できる範囲は、どの拡張で制限されるのか。
- 失効、Certificate Transparency、ACME は、どの問題を受け持つのか。
- Public CA と Private CA は、どの名前と利用者に使い分けるのか。

クライアント証明書による利用者認証、TLS の暗号スイート、証明書の署名アルゴリズムの計算は扱いません。署名が秘密鍵の保持をどう証明するかは [Digital Signature](../../blockchain-systems/digital-signature/) のノートを参照してください。

---

### 証明書と trust store

X.509 証明書は、subject（識別される主体）、公開鍵、有効期間、発行者、拡張、発行者による署名を持つデータです。サーバー証明書の場合、接続先の DNS 名は通常 `subjectAltName` 拡張に入ります。subject の distinguished name を使う場面もありますが、TLS で DNS 名を照合する時は [RFC 9525](https://www.rfc-editor.org/rfc/rfc9525) の規則に従います。

CA の仕事は、公開鍵をただ登録することではありません。どの識別子について、どの種類の確認を済ませ、どの用途・期限で証明書を発行するかを決めます。

公開 Web PKI の CA は、[CA/Browser Forum Baseline Requirements](https://cabforum.org/working-groups/server/baseline-requirements/)（以下、BR）に従い、申請者がその DNS 名を管理していることを必ず検証します。運営する組織の実在まで検証するのは OV や EV の証明書だけで、最も多い DV の証明書はサイトの運営者が誰かを保証しません。どの種類も、通信内容の安全性は保証しません。

trust store に Root CA を入れる行為は、その CA が定めた検証と発行の方針を受け入れることです。CA は [RFC 3647](https://www.rfc-editor.org/rfc/rfc3647) の枠組みに沿って、Certificate Policy と Certification Practice Statement に方針と実務を記述します。したがって、署名の検証に成功しても、利用者が信頼したのは任意の CA ではなく、手元の trust store にある CA です。

Public CA は不特定のインターネット利用者が検証する公開 DNS 名に向きます。一方で、Private CA は社内の端末、[サービスメッシュ](/notes/software-architecture/sidecar/)、閉じた環境のホスト名に使えます。Private CA の Root 証明書は利用する端末すべてに配布し、更新・削除を管理する必要があります。

公開 DNS で一意に確認できない社内名（例えば `.local` で終わる名前）には、Public CA の証明書を使えません。BR の 4.2.2 は、このような Internal Name を含む証明書の発行を禁じています。そのため、社内名には Private CA を使うか、社内のホストにも自社の公開ドメインの名前を割り当てて、その名前で証明書を取ります。

---

### 証明書パスの検証

サーバーは通常、サーバー証明書と Intermediate CA 証明書をクライアントに送ります。クライアントはこれらをつなぎ、trust store にある Root CA までの証明書パスを構築します。Root CA 自身は trust store から得られるため、サーバーが送らないこともあります。

パスを構築できた後も、署名をたどるだけでは十分ではありません。TLS クライアントは、少なくとも次の条件を個別に確認します。

| 確認する条件 | 失敗した時に防ぎたいこと |
| --- | --- |
| 署名と発行者の連鎖 | 攻撃者が作った証明書を CA 発行と見なすこと |
| 有効期間 | 期限切れ、または開始前の証明書を使うこと |
| hostname と `subjectAltName` | 別の DNS 名向けの証明書を接続先に使うこと |
| `basicConstraints` | 終端の証明書を CA として使い、さらに証明書を発行すること |
| `nameConstraints` | CA が委任された範囲の外の名前に証明書を発行すること |
| `keyUsage` と `extendedKeyUsage` | 鍵を許可されていない用途で使うこと |
| trust anchor | 端末が信頼していない CA だけで連鎖を作ること |

`basicConstraints` の `CA:TRUE` は、その証明書が CA として扱われ得ることを示します。`pathLenConstraint` があれば、その下に置ける CA の数も制限します。CA 証明書の `keyUsage` には通常 `keyCertSign` が必要です。

公開 Web PKI のサーバー証明書は、BR により `extendedKeyUsage` に `serverAuth` を必ず持ちます。クライアントはこれを見て、TLS サーバー認証に使ってよいかを判断します。

`basicConstraints` が CA になれるかと深さを決めるのに対し、CA が発行できる名前の範囲は `nameConstraints` で制限します。これらは RFC 5280 の証明書パス検証で確認する制約です。

例えば、Intermediate CA に `permitted;DNS:example.test` を入れると、その CA が発行した `www.other.test` の証明書は検証で拒否されます（OpenSSL 3.5.5 では error 47 permitted subtree violation）。

{{< figure src="images/pki_name_constraints.svg" alt="Root CA の下に、permitted;DNS:example.test を持つ Intermediate CA。そこから署名の矢印が 2 本出る。灰色の点線で囲んだ example.test の下の範囲にある www.example.test は通り、範囲の外の www.other.test には赤い×と「error 47 で拒否」" caption="nameConstraints が Intermediate CA の発行範囲を絞る" align="center" >}}

hostname の照合には、接続しようとした名前そのものを使います。例えば `api.example.test` に接続する時、`www.example.test` だけを含む証明書は通りません。ワイルドカードを使う場合も、RFC 9525 が許す位置と 1 つのラベルに限られます。IP アドレスに接続する場合は、DNS 名ではなく IP address 型の `subjectAltName` と照合します。

---

### OpenSSL で見る検証の失敗

以下は、ローカルで作った Root CA とサーバー証明書を OpenSSL で検証する最小例です。`example.test` は説明用の予約済み名前であり、実在の公開サービスには接続しません。OpenSSL の [verify](https://docs.openssl.org/3.5/man1/openssl-verify/) は証明書パスを検証し、`-verify_hostname` は hostname も照合します。以下の出力は OpenSSL 3.5.5 で確認しました。

```sh
mkdir pki-lab && cd pki-lab

openssl req -x509 -newkey rsa:2048 -nodes -days 7 \
  -keyout root.key -out root.pem -subj '/CN=Local Root' \
  -addext 'basicConstraints=critical,CA:TRUE' \
  -addext 'keyUsage=critical,keyCertSign,cRLSign'

openssl req -newkey rsa:2048 -nodes -keyout server.key -out server.csr \
  -subj '/CN=ignored.example.test'

openssl x509 -req -in server.csr -CA root.pem -CAkey root.key -CAcreateserial \
  -out server.pem -days 7 \
  -extfile <(printf 'basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature\nextendedKeyUsage=serverAuth\nsubjectAltName=DNS:example.test')

openssl verify -CAfile root.pem -purpose sslserver \
  -verify_hostname example.test server.pem
openssl verify -CAfile root.pem -purpose sslserver \
  -verify_hostname other.example.test server.pem
```

出力の前者は成功し、後者は hostname が一致しないため失敗します。

```text
server.pem: OK
CN=ignored.example.test
error 62 at 0 depth lookup: hostname mismatch
error server.pem: verification failed
```

上記に加えて、表の `basicConstraints` の行を確認します。終端の証明書である `server.pem` とその秘密鍵で、別の名前の証明書を署名します。署名の計算自体は成功するので、`evil.pem` は作れます。

```sh
openssl req -newkey rsa:2048 -nodes -keyout evil.key -out evil.csr \
  -subj '/CN=evil.example.test'

openssl x509 -req -in evil.csr -CA server.pem -CAkey server.key -CAcreateserial \
  -out evil.pem -days 7 \
  -extfile <(printf 'basicConstraints=critical,CA:FALSE\nextendedKeyUsage=serverAuth\nsubjectAltName=DNS:evil.example.test')

openssl verify -CAfile root.pem -untrusted server.pem -purpose sslserver \
  -verify_hostname evil.example.test evil.pem
```

`evil.pem` の署名は `server.pem` の鍵で正しく検証できますが、パスの 1 段目（depth 1）にある `server.pem` が 3 つの理由で拒否されます。

```text
CN=ignored.example.test
error 79 at 1 depth lookup: invalid CA certificate
CN=ignored.example.test
error 26 at 1 depth lookup: unsuitable certificate purpose
CN=ignored.example.test
error 32 at 1 depth lookup: key usage does not include certificate signing
error evil.pem: verification failed
```

error 79 は `CA:FALSE`、error 26 は TLS サーバー用の CA として使える条件を満たさないこと、error 32 は `keyUsage` に `keyCertSign` が無いことに対応します。正規のサーバー証明書を持つ攻撃者でも、署名を連ねるだけでは別の名前の証明書を作れません。

この実験で `root.pem` を `-CAfile` に渡すことは、ローカルの検証器がその Root CA を trust store として受け入れることに相当します。実際のブラウザは、OS やブラウザが管理する複数の trust anchor と、より多くのポリシーを使います。

---

### 失効と可視化

証明書の期限が残っていても、対応する秘密鍵の漏洩や誤発行を後から知ることがあります。失効（revocation）はこのような証明書を有効期限より前に無効にする仕組みです。

CRL（Certificate Revocation List）は RFC 5280 で定義され、OCSP（Online Certificate Status Protocol）は [RFC 6960](https://www.rfc-editor.org/rfc/rfc6960) で定義された、特定の証明書の状態を問い合わせる方式です。

2026 年 11 月時点の BR では CRL の公開が必須で、OCSP は任意です。例えば、Let's Encrypt は 2025 年 8 月に [OCSP の応答を停止](https://letsencrypt.org/2024/12/05/ending-ocsp/)しました。

しかし、クライアントが失効情報を取得できなかった時に接続を止めるかは、可用性とのトレードオフになります。OCSP 応答を TLS ハンドシェイクでサーバーが添える OCSP stapling も、失効の確認を常に成功させるものではありません。そのため、証明書を短期間で更新し、秘密鍵の保護と監視を併用します。

Certificate Transparency（CT）は、公開 Web PKI の証明書を追記専用ログに記録し、誤発行を監視可能にする仕組みです。証明書がログに登録されたことを示す SCT（Signed Certificate Timestamp）を利用して、発行を第三者が観測できるようにします。CT は DNS 名の所有を確認する仕組みでも、失効情報でもありません。ログは記録を [Merkle Tree](/notes/blockchain-systems/merkle-tree/) にまとめているので、少数のハッシュで、ある証明書が入っていることや過去の記録が書き換わっていないことを検証できます。

ブラウザが受け付ける CT ログと SCT は [RFC 6962](https://www.rfc-editor.org/rfc/rfc6962)（CT v1）の形式です。v2.0 を定めた [RFC 9162](https://www.rfc-editor.org/rfc/rfc9162) は、公開 Web PKI ではまだ広く運用されていません。

以下は、1 枚の証明書の発行から有効期限までの間に、失効・CT・後述の ACME が受け持つ位置を並べた図です。

{{< figure src="images/pki_lifecycle.svg" alt="横長の帯が 1 枚の証明書の発行から有効期限まで。左端の発行に「ACME で自動化」と「発行時に CT ログへ記録（SCT）、誤発行を第三者が観測できる」。途中で鍵の漏洩や誤発行が分かり、その後の失効（CRL / OCSP）から有効期限までの帯は黄土色の「期限は残るが失効済み」。失効の下に「取れない時に止めるかはクライアント次第」" caption="証明書の一生と、ACME・CT・失効の受け持ち" align="center" >}}

ACME（Automatic Certificate Management Environment）は、CA と証明書利用者の間で証明書の発行・更新・失効を自動化するプロトコルです。[RFC 8555](https://www.rfc-editor.org/rfc/rfc8555) では、HTTP-01 や DNS-01 の challenge で識別子の制御を検証します。ただし、更新済みの証明書をサーバーが読み込み直す設定は、ACME とは別に用意します。

---

### 境界と運用

PKI が検証するのは、指定した名前に対する公開鍵の結び付きと、その結び付きを発行した CA までの連鎖です。証明書が有効でも、接続先のアプリケーションが安全であること、取得したデータが正しいこと、サイト運営者が利用者の期待する組織であることまでは導けません。

Public CA を使う場合は、公開 DNS 名、CA の発行要件、利用者の trust store をそろえて考えます。Private CA を使う場合は、Root 証明書の配布対象を最小にし、不要になった trust anchor を端末から除去できる状態を保ちます。どちらも、秘密鍵の保管、証明書の更新、失効・CT の監視を分けずに扱うことが必要です。
