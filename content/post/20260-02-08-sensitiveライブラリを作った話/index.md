---
title: "【Golang】クレカ番号などを検出・マスクするsensitiveライブラリを作った話"
type: post
date: 2026-02-08
categories:
  - "linux"
cover:
  image: "images/2026-sensitive-logo.png"
  alt: "sensitive-logo"
  hidden: false
---

### 前書き

sensitive テキストを見つけ、必要であればマスクする [nao1215/sensitive](https://github.com/nao1215/sensitive) ライブラリ（Golang）を作ったので、軽く紹介します。Fintech に所属していれば、誰でも一度は作ろうと考えるタイプのライブラリですね。なお、暇つぶしで作っただけなので、現職の業務で利用予定はありません。

「センシティブ」の文字を見ると、「下ネタかな？」と思われる方がいらっしゃるかもしれません。残念ながら、本ライブラリでのセンシティブとは、クレジットカード番号（PAN）や電話番号などのロギングできない文字列（機密情報）を指します。カード業界の国際セキュリティ基準である PCI DSS（Payment Card Industry Data Security Standard）では、PANを出力する際はマスキングすることが求められます。この辺りの話題は、「[クレジットカード番号の混入を防ぐ技術 - inSmartBank](https://blog.smartbank.co.jp/entry/2026/01/08/100000)」に詳しく書かれています。[^1]

下ネタ（下品な単語）を検出することは当然可能ですが、対応しませんでした。対応し始めると、ライブラリのコード内に単語を埋め込む必要があり、かつ日本国内の性的な単語は進化（?）が早くてキャッチアップが大変です。自分で利用する機会のないコードをメンテするのは不毛なので、対応しない方針としました。

[^1]: 私の所属は、株式会社スマートバンクではありません。

---

### sensitive ライブラリの仕組み

sensitive ライブラリは、大別して以下の3つの仕組みを提供しています。

- Scanner：テキストや io.Reader を読み込む
- Detector：特定の機密情報を検出する
- Masker：指定のパターンで機密情報をマスクする

ユーザーは、「Scanner に Detector を指定して初期化」、「テキストをスキャン」、「指定の方法でテキストをマスク」という流れを実装します。

コード例：

```go
package main

import (
    "fmt"

    "github.com/nao1215/sensitive"
    "github.com/nao1215/sensitive/detector"
    "github.com/nao1215/sensitive/mask"
)

func main() {
    scanner := sensitive.NewScanner(sensitive.WithAll())
    text := "user tanaka@example.com paid with 4532015112830366" // 架空のPANです。
    findings := scanner.ScanString(text)

    for _, f := range findings {
        fmt.Printf("type=%s raw=%s confidence=%.2f\n",
            f.DetectorName, f.RawValue, f.Confidence)
    }

    masked := mask.Mask(text, findings, map[sensitive.DetectorName]mask.Strategy{
        detector.NamePAN:   mask.Last4,
        detector.NameEmail: mask.Partial,
    })
    fmt.Println(masked)
}
```

出力例（順不同）:

```
type=pan raw=4532015112830366 confidence=1.00
type=email raw=tanaka@example.com confidence=1.00
user t*****@example.com paid with ************0366
```

---

### sensitive ライブラリが対応している機密情報

Scanner の初期化時に Detector（検出器）を指定でき、Detector は以下の機密情報を検出します。検出精度は、`confidence`として0.0〜1.0で表現しています。しかし、この数値の裏付け説明が弱い状態です。言い換えると、sensitive ライブラリは野良OSSなので、本番環境で使うときは運用に耐えられるかを判断してからご利用ください。

| Option | Detects | Validation |
|--------|---------|------------|
| `WithPAN()` | クレジットカード番号（Visa, Mastercard, Amex, JCB, Discover, Diners, UnionPay） | BIN プレフィックス + Luhn アルゴリズム |
| `WithEmail()` | メールアドレス | 構造 + 既知 TLD チェック |
| `WithJPPhone()` | 日本の電話番号（携帯・固定・IP・フリーダイヤル・M2M/IoT・サービス） | プレフィックス分類 + 桁数 |
| `WithMyNumber()` | マイナンバー（12 桁） | MOD 11 チェックディジット |
| `WithJWT()` | JWT（JSON Web Token） | ヘッダデコード + `alg` キーチェック |
| `WithAWSKey()` | AWS アクセスキー ID（`AKIA...` / `ASIA...`） | プレフィックス + 20 文字の英数字 |
| `WithIBAN()` | IBAN（国際銀行口座番号） | 国コード + MOD 97 チェックディジット |
| `WithIPAddr()` | IP アドレス（IPv4/IPv6） | `net.ParseIP` + オクテット範囲 |
| `WithSWIFTBIC()` | SWIFT/BIC コード | 形式 + 国コード検証 |
| `WithABARouting()` | 米国 ABA ルーティング番号 | プレフィックス範囲 + チェックサム |
| `WithUKSortCode()` | 英国ソートコード（XX-XX-XX） | パターン + 境界チェック |
| `WithCVV()` | カード確認番号（CVV/CVC/CID） | 文脈キーワード + 桁数（文脈依存・弱） |
| `WithCardExpiry()` | カード有効期限 | 文脈キーワード + MM/YY 検証（文脈依存・弱） |
| `WithPaymentToken()` | 決済事業者のトークン（Stripe/PayPal/Square） | プレフィックス + 最低ボディ長 |
| `WithBankAccount()` | 銀行口座番号（文脈依存） | 文脈キーワード + 桁数範囲（文脈依存・弱） |
| `WithACHTrace()` | ACH トレース番号 | 文脈キーワード + プレフィックス範囲（文脈依存・弱） |
| `WithMerchantID()` | マーチャント/端末 ID | 文脈キーワード + 形式（文脈依存・弱） |
| `WithBTC()` | Bitcoin アドレス（P2PKH, P2SH, Bech32, Bech32m/Taproot） | Base58Check（二重 SHA-256）/ Bech32 多項式チェックサム |
| `WithETH()` | Ethereum アドレス（0x + 40 hex） | EIP-55 混在大小チェックサム（Keccak-256） |
| `WithAll()` | 上記すべて | |

---

### マスキングパターン

下表のマスキング方法を選択できます。特に強い理由はないですが、カスタムマスキングを導入しませんでした。

| Strategy | Example |
|----------|---------|
| `Redact` | `4532015112830366` -> `****************` |
| `Last4` | `4532015112830366` -> `************0366` |
| `First1Last4` | `4532015112830366` -> `4***********0366` |
| `Partial` | `tanaka@example.com` -> `t*****@example.com` |
| `Hash` | `4532015112830366` -> `a8f5f167`（SHA-256 先頭） |

---

### 検出した機密情報の詳細確認

PAN等の情報を検出したら、どのような検出結果だったのかを以下のメソッドからチェックできます。例えば、`PANDetail()`を使えば、クレカブランド（例：Visa）を把握できます。ほぼデバッグ用途の機能です。

| Method | Fields |
|--------|--------|
| `PANDetail()` | Brand, BIN, Last4, Luhn, Length |
| `EmailDetail()` | Local, Domain |
| `JPPhoneDetail()` | PhoneType (`JPPhoneTypeMobile`, `JPPhoneTypeLandline`, `JPPhoneTypeIPPhone`, `JPPhoneTypeTollFree`, `JPPhoneTypeM2M`, `JPPhoneTypeService`) |
| `JWTDetail()` | Algorithm（例: `HS256`, `RS256`） |
| `AWSKeyDetail()` | KeyType (`AWSKeyTypeLongTerm` または `AWSKeyTypeTemporary`) |
| `IBANDetail()` | CountryCode（ISO 3166-1 alpha-2） |
| `IPAddrDetail()` | Version（4 または 6） |
| `MyNumberDetail()` | CheckDigitValid |
| `BTCDetail()` | AddressType (`BTCAddressP2PKH`, `BTCAddressP2SH`, `BTCAddressBech32`, `BTCAddressBech32m`) |
| `ETHDetail()` | EIP55（EIP-55 の検証が通ったかどうか） |

---

### どこでマスキングするかは、ユーザーに委ねる仕様

当初、ロガーのアダプターライブラリを作り、例えば slog でロギングする際にセンシティブ情報をマスクする予定でした。

しかし、ロガーのアダプタを作るだけで十分でしょうか？センシティブ情報は、`fmt.Println()`で書き込まれるかもしれないし、DB に INSERT されるかもしれません。構造体の struct tag を利用して、構造体フィールドのデータをマスク出力したいユーザーもいるかもしれません。

検出やマスキングタイミングをユーザーに委ねられた方が使い勝手が良いと考え、現在の仕様に落ち着いています。具体的なユースケース例としては、ダークウェブ監視時にダークウェブに存在した文字列が PAN だったかどうかを sensitive ライブラリで判定することができます。

---

### 信頼性の確保の仕方が不明

sensitive ライブラリのユースケースを考えると、下表の"4. 偽陰性"が許容できません。例えば、Scanner に PAN を渡したら、検出されず、そのままロギングしてしまう事例が起きたら、一発でインシデントです。


| ケース | 実際のデータ | 検出結果 | 分類 | 問題点 | ライブラリ側で出来る対策 |
|------|--------------|----------|------|--------|--------------------------|
| 1 | 機密情報ではない | 検出されない | 真陰性 (TN) | 問題なし | 何もしなくてよい |
| 2 | 機密情報 | 正しく検出 | 真陽性 (TP) | 問題なし | 現状維持 |
| 3 | 機密情報ではない | 検出される | 偽陽性 (FP) | ログ破壊・可読性低下 | strict / context-aware 検出、キーワード条件追加 |
| 4 | 機密情報 | 検出されない | 偽陰性 (FN) | 情報漏洩リスク | loose モード、検出ルール追加 |

偽陰性がないことを証明する手段がないため、sensitive ライブラリを Production Ready に引き上げられません。使い込んでくれる酔狂な会社がいれば別ですけど、いないでしょう（そして、現職で使い込む気がない）。

---

### 最後に

sensitive ライブラリを作る前に、1週間ほどMarkdownエディタを作っていました。[wailsapp/wails](https://github.com/wailsapp/wails)を使って、基本機能が揃う段階まで作り込んでいました。しかし、「GUI部分のメンテが続かなそう」「他のアプリを使った方が良い」と判断して、ポシャりました。ポシャって、「なんか別なの作るか」と思い立ち、sensitive ライブラリが生まれました。

