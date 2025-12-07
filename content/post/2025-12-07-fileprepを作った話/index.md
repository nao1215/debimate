---
title: "【Golang】CSV、TSV、LTSV、Parquet、Excel に前処理とバリデーションを行う nao1215/fileprep を作った話"
type: post
date: 2025-12-07
categories:
  - "linux"
cover:
  image: "images/20251207-fileprep-logo.jpg"
  alt: "fileprep"
  hidden: false
---

### [nao1215/fileprep](https://github.com/nao1215/fileprep)（前処理ライブラリ） を開発した理由

理由は、データが汚れているからです。

私は、過去に [nao1215/csv](https://github.com/nao1215/csv) ライブラリ（パブリックアーカイブ済み） を開発していました。nao1215/csv は、struct tag でバリデーションルールを指定すると、CSV ファイルの読込み後に「どの行のどのカラムが不正値なのか」を教えてくれます。

nao1215/csv を開発した理由は、「非エンジニアが渡してくる CSV データに誤りが多すぎるので、読み込み時にバリデーションする必要がある」と思い立ったのが、キッカケです。nao1215/csv を作成してから1年以上が経ち、当時と状況が変わってきました。

- 複数の表形式ファイルを扱う [nao1215/filesql](https://github.com/nao1215/filesql) を開発
- 機械学習を学び、前処理（データ整形）の重要性に気づく

さらに、nao1215/filesql のバリデーション機能の弱さのせいで、会社で別プロジェクトメンバが戸惑っている姿を見て、「nao1215/filesql と統合でき、かつ前処理とバリデーションができるライブラリを作ろう」と思い立ちました。

nao1215/filesql に機能追加しなかった理由は、「データ整形とバリデーションだけしたい需要もあると考えたから」および「nao1215/filesql が巨大なライブラリになることを避けたから」です。

----

### file + preprocess = fileprep とは

[nao1215/fileprep](https://github.com/nao1215/fileprep) は、struct tag を指定した構造体を用いて、ファイル読み込みを行うライブラリです。ファイル読み込み時に、前処理とバリデーションを行います。

主に、以下の特徴を持ちます。

- データ整形用の `prep` タグ
- データバリデーション用の `validate` タグ
- カラム名を指定する `name` タグ（通常、カラム名は自動推定）
- CSV、TSV、LTSV、Parquet、Excel および  gzip, bzip2, xz, zstd をサポート
- 前処理／バリデーション時の入力は io.Reader、出力は前処理後の io.Reader、構造体スライス、前処理エラー／バリデーションエラー

io.Reader として出力することで、nao1215/filesql にそのまま受け渡せるメリットがあります。過去に作成した nao1215/csv は、読み込み結果を構造体スライスとして返していたので、nao1215/filesql にそのまま渡せませんでした。とは言え、nao1215/filesql を使わないユーザーもいる筈なので、構造体スライスを返す仕様も踏襲しました。

----

### fileprep サンプルコード

実際にコードを見た方が理解しやすいと思われるので、以下に示します。
  
このサンプルコードは、前処理として、Name は前後にある空白を除去し、Email は空白除去と小文字化をしています。構造体フィールド名をスネークケースに変換したものが、カラム名となります。カラム名を明示したい場合は`name` タグを利用しますが、今回のサンプルでは登場しません。

```go
package main

import (
    "fmt"
    "os"
    "strings"

    "github.com/nao1215/fileprep"
)

type User struct {
    Name  string `prep:"trim" validate:"required"`
    Email string `prep:"trim,lowercase"`
    Age   string
}

func main() {
    csvData := `name,email,age
  John Doe  ,JOHN@EXAMPLE.COM,30
Jane Smith,jane@example.com,25
`

    processor := fileprep.NewProcessor(fileprep.FileTypeCSV)
    var users []User

    // reader（返り値）: 前処理後の io.Reader
    // result（返り値）: 前処理とバリデーションの結果
    // users（引数）: processor.Process() 後は、前処理後のデータが追加されている。
    reader, result, err := processor.Process(strings.NewReader(csvData), &users)
    if err != nil {
        fmt.Printf("Error: %v\n", err)
        return
    }

    fmt.Printf("Processed %d rows, %d valid\n", result.RowCount, result.ValidRowCount)

    for _, user := range users {
        fmt.Printf("Name: %q, Email: %q\n", user.Name, user.Email)
    }
}
```

Output:
```
Processed 2 rows, 2 valid
Name: "John Doe", Email: "john@example.com"
Name: "Jane Smith", Email: "jane@example.com"
```

---

### タグ一覧

[go-playground/validator](https://github.com/go-playground/validator)を参考に、`validate` タグを設計しています。なお、バリデーションロジックは一致していません。

タグのカスタマイズ性は、意図的に持たせていません。つまり、ユーザー指定のタグ名に、ユーザー指定の関数を定義するような機能はありません。そこまで複雑な前処理とバリデーションが必要な場合、nao1215/fileprep が適していない気がします。

### 前処理タグ (`prep`)
#### 基本的な前処理

| タグ | 説明 | 例 |
|-----|------|-----|
| `trim` | 前後の空白を削除 | `prep:"trim"` |
| `ltrim` | 先頭の空白を削除 | `prep:"ltrim"` |
| `rtrim` | 末尾の空白を削除 | `prep:"rtrim"` |
| `lowercase` | 小文字に変換 | `prep:"lowercase"` |
| `uppercase` | 大文字に変換 | `prep:"uppercase"` |
| `default=value` | 空の場合にデフォルト値を設定 | `prep:"default=N/A"` |

#### 文字列変換

| タグ | 説明 | 例 |
|-----|------|-----|
| `replace=old:new` | すべての出現を置換 | `prep:"replace=;:,"` |
| `prefix=value` | 文字列を先頭に追加 | `prep:"prefix=ID_"` |
| `suffix=value` | 文字列を末尾に追加 | `prep:"suffix=_END"` |
| `truncate=N` | N文字に制限 | `prep:"truncate=100"` |
| `strip_html` | HTMLタグを削除 | `prep:"strip_html"` |
| `strip_newline` | 改行を削除 (LF, CRLF, CR) | `prep:"strip_newline"` |
| `collapse_space` | 複数のスペースを1つに | `prep:"collapse_space"` |

#### 文字フィルタリング

| タグ | 説明 | 例 |
|-----|------|-----|
| `remove_digits` | すべての数字を削除 | `prep:"remove_digits"` |
| `remove_alpha` | すべてのアルファベットを削除 | `prep:"remove_alpha"` |
| `keep_digits` | 数字のみを保持 | `prep:"keep_digits"` |
| `keep_alpha` | アルファベットのみを保持 | `prep:"keep_alpha"` |
| `trim_set=chars` | 指定文字を両端から削除 | `prep:"trim_set=@#$"` |

#### パディング

| タグ | 説明 | 例 |
|-----|------|-----|
| `pad_left=N:char` | N文字まで左にパディング | `prep:"pad_left=5:0"` |
| `pad_right=N:char` | N文字まで右にパディング | `prep:"pad_right=10: "` |

#### 高度な前処理

| タグ | 説明 | 例 |
|-----|------|-----|
| `normalize_unicode` | UnicodeをNFC形式に正規化 | `prep:"normalize_unicode"` |
| `nullify=value` | 特定の文字列を空として扱う | `prep:"nullify=NULL"` |
| `coerce=type` | 型変換 (int, float, bool) | `prep:"coerce=int"` |
| `fix_scheme=scheme` | URLスキームを追加/修正 | `prep:"fix_scheme=https"` |
| `regex_replace=pattern:replacement` | 正規表現による置換 | `prep:"regex_replace=\\d+:X"` |

### バリデーションタグ (`validate`)

#### 基本的なバリデータ

| タグ | 説明 | 例 |
|-----|------|-----|
| `required` | フィールドは空であってはならない | `validate:"required"` |
| `boolean` | true, false, 0, または 1 である必要がある | `validate:"boolean"` |

#### 文字種バリデータ

| タグ | 説明 | 例 |
|-----|------|-----|
| `alpha` | ASCIIアルファベットのみ | `validate:"alpha"` |
| `alphaunicode` | Unicode文字のみ | `validate:"alphaunicode"` |
| `alphaspace` | アルファベットまたはスペース | `validate:"alphaspace"` |
| `alphanumeric` | ASCII英数字のみ | `validate:"alphanumeric"` |
| `alphanumunicode` | Unicode文字または数字 | `validate:"alphanumunicode"` |
| `numeric` | 有効な整数 | `validate:"numeric"` |
| `number` | 有効な数値（整数または小数） | `validate:"number"` |
| `ascii` | ASCII文字のみ | `validate:"ascii"` |
| `printascii` | 印刷可能なASCII文字（0x20-0x7E） | `validate:"printascii"` |
| `multibyte` | マルチバイト文字を含む | `validate:"multibyte"` |

#### 数値比較バリデータ

| タグ | 説明 | 例 |
|-----|------|-----|
| `eq=N` | 値がNと等しい | `validate:"eq=100"` |
| `ne=N` | 値がNと等しくない | `validate:"ne=0"` |
| `gt=N` | 値がNより大きい | `validate:"gt=0"` |
| `gte=N` | 値がN以上 | `validate:"gte=1"` |
| `lt=N` | 値がNより小さい | `validate:"lt=100"` |
| `lte=N` | 値がN以下 | `validate:"lte=99"` |
| `min=N` | 値が最小N | `validate:"min=0"` |
| `max=N` | 値が最大N | `validate:"max=100"` |
| `len=N` | 正確にN文字 | `validate:"len=10"` |

#### 文字列バリデータ

| タグ | 説明 | 例 |
|-----|------|-----|
| `oneof=a b c` | 許可された値のいずれか | `validate:"oneof=active inactive"` |
| `lowercase` | すべて小文字である | `validate:"lowercase"` |
| `uppercase` | すべて大文字である | `validate:"uppercase"` |
| `eq_ignore_case=value` | 大文字小文字を無視して等しい | `validate:"eq_ignore_case=yes"` |
| `ne_ignore_case=value` | 大文字小文字を無視して等しくない | `validate:"ne_ignore_case=no"` |

#### 文字列内容バリデータ

| タグ | 説明 | 例 |
|-----|------|-----|
| `startswith=prefix` | 指定プレフィックスで始まる | `validate:"startswith=http"` |
| `startsnotwith=prefix` | 指定プレフィックスで始まらない | `validate:"startsnotwith=_"` |
| `endswith=suffix` | 指定サフィックスで終わる | `validate:"endswith=.com"` |
| `endsnotwith=suffix` | 指定サフィックスで終わらない | `validate:"endsnotwith=.tmp"` |
| `contains=substr` | 部分文字列を含む | `validate:"contains=@"` |
| `containsany=chars` | いずれかの文字を含む | `validate:"containsany=abc"` |
| `containsrune=r` | 指定ルーンを含む | `validate:"containsrune=@"` |
| `excludes=substr` | 部分文字列を含まない | `validate:"excludes=admin"` |
| `excludesall=chars` | いずれの文字も含まない | `validate:"excludesall=<>"` |
| `excludesrune=r` | 指定ルーンを含まない | `validate:"excludesrune=$"` |

#### フォーマットバリデータ

| タグ | 説明 | 例 |
|-----|------|-----|
| `email` | 有効なメールアドレス | `validate:"email"` |
| `uri` | 有効なURI | `validate:"uri"` |
| `url` | 有効なURL | `validate:"url"` |
| `http_url` | 有効なHTTPまたはHTTPS URL | `validate:"http_url"` |
| `https_url` | 有効なHTTPS URL | `validate:"https_url"` |
| `url_encoded` | URLエンコード文字列 | `validate:"url_encoded"` |
| `datauri` | 有効なデータURI | `validate:"datauri"` |
| `uuid` | 有効なUUID | `validate:"uuid"` |

#### ネットワークバリデータ

| タグ | 説明 | 例 |
|-----|------|-----|
| `ip_addr` | 有効なIPアドレス（v4またはv6） | `validate:"ip_addr"` |
| `ip4_addr` | 有効なIPv4アドレス | `validate:"ip4_addr"` |
| `ip6_addr` | 有効なIPv6アドレス | `validate:"ip6_addr"` |
| `cidr` | 有効なCIDR表記 | `validate:"cidr"` |
| `cidrv4` | 有効なIPv4 CIDR | `validate:"cidrv4"` |
| `cidrv6` | 有効なIPv6 CIDR | `validate:"cidrv6"` |
| `fqdn` | 有効な完全修飾ドメイン名 | `validate:"fqdn"` |
| `hostname` | 有効なホスト名（RFC 952） | `validate:"hostname"` |
| `hostname_rfc1123` | 有効なホスト名（RFC 1123） | `validate:"hostname_rfc1123"` |
| `hostname_port` | 有効なホスト名:ポート | `validate:"hostname_port"` |

#### クロスフィールドバリデータ

| タグ | 説明 | 例 |
|-----|------|-----|
| `eqfield=Field` | 値が別のフィールドと等しい | `validate:"eqfield=Password"` |
| `nefield=Field` | 値が別のフィールドと等しくない | `validate:"nefield=OldPassword"` |
| `gtfield=Field` | 値が別のフィールドより大きい | `validate:"gtfield=MinPrice"` |
| `gtefield=Field` | 値が別のフィールド以上 | `validate:"gtefield=StartDate"` |
| `ltfield=Field` | 値が別のフィールドより小さい | `validate:"ltfield=MaxPrice"` |
| `ltefield=Field` | 値が別のフィールド以下 | `validate:"ltefield=EndDate"` |
| `fieldcontains=Field` | 別のフィールドの値を含む | `validate:"fieldcontains=Keyword"` |
| `fieldexcludes=Field` | 別のフィールドの値を含まない | `validate:"fieldexcludes=Forbidden"` |

---

### 最後に：鉄は熱いうちに打つ

nao1215/fileprep の発想に辿り着いたのは、23時でした。
  
ワンオペが続くので、開発タイミングに迷いました。しかし、平日にゆるゆる開発すると、次第にモチベーションが失せていくので、休日での開発を決意しました。朝方までカタカタ作業していました。昼間、吐き気と疲労感に悩まされました。

でも、リリースまでこじつけられて良かったです。
