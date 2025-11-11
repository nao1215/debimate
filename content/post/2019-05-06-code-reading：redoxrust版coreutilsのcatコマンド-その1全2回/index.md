---
title: "Code Reading：Redox(Rust)版coreutilsのcatコマンド その1(全2回)"
type: post
date: 2019-05-06
categories:
  - "linux"
tags:
  - "codereading"
  - "coreutils"
  - "linux"
  - "rust"
cover:
  image: "images/cat.jpg"
  alt: "Code Reading：Redox(Rust)版coreutilsのcatコマンド その1(全2回)"
  hidden: false
---

### 前書き

Rustを学習するための一環として、Redox(OS)版coreutilsのcatコマンドをCode Readingします。Redoxプロジェクトや環境構築方法に関しては、以下の記事にまとめてあります。

- [環境構築：Redox向けcoreutils(Rust)のCode Reading準備およびReading対象コマンド一覧](https://debimate.jp/post/2019-05-03-%E7%92%B0%E5%A2%83%E6%A7%8B%E7%AF%89redox%E5%90%91%E3%81%91coreutilsrust%E3%81%AEcode-reading%E6%BA%96%E5%82%99%E3%81%8A%E3%82%88%E3%81%B3reading%E5%AF%BE%E8%B1%A1%E3%82%B3%E3%83%9E/)

catコマンドは、記事を2つに分けて説明します。今回(その1)は、catコマンドのオプションパース処理までを説明し、その2でcatコマンドの主要な処理(ファイル内容の表示)を説明します。

### catコマンド 挙動のおさらい

ソースコードの確認に入る前に、catコマンドの挙動を確認します。catコマンドは、由来である"con**cat**enate(〜を連結する)"の通り、ファイルの中身を連結します。連結操作よりも、ファイルの中身を表示するために用いる事が多いと思います。

以下に、実行例を示します。Redox版coreutils(Rust版coreutils)を用いていますが、GNU版/BSD版と挙動は同じです。

```
(注釈)：Redox版coreutils(Rust版のcoreutils)のcatコマンド、
　　　  テスト用ファイルをワーキングディレクトリ以下に用意してあります。
$ ls
cat  fileA.txt  fileB.txt  fileC.txt

(注釈)：file[A-C].txtの中身をcatコマンドで表示。内容は、大文字のアルファベット3文字。
$ cat fileA.txt 
AAA
$ cat fileB.txt 
BBB
$ cat fileC.txt 
CCC

(注釈)：file[A-C].txtの中身をcatコマンドで連結して表示。
$ cat fileA.txt fileB.txt fileC.txt 
AAA
BBB
CCC
```

### catコマンドのコード全文(Reading対象)

catコマンドは約270Stepと短いですが、本記事では全文を示しません。全文を確認する場合、[Redox版coreutilsの公式リポジトリ](https://github.com/redox-os/coreutils/blob/master/src/bin/cat.rs)を参照して下さい。ただし、Reading結果を示す際は、部分的なコードを示します。

### 一行目：#!\[deny(warnings)\]について

以下に示すcat.rsを示します。最初の部分は、"#!\[deny(warnings)\]"、crateの読込(extern部分)、モジュールの読込(use部分)で開始しています。crate・モジュールの読み込みは一般的な文法のため、一行目のみ説明します。

```
#![deny(warnings)]

extern crate arg_parser;
extern crate extra;

use std::cell::Cell; // Provide mutable fields in immutable structs
use std::env;
use std::error::Error;
use std::fs;
use std::io::{self, BufReader, Read, Stderr, StdoutLock, Write};
use std::process::exit;
use extra::option::OptionalExt;
use arg_parser::ArgParser;

```

"#!\[deny(warnings)\]"によって、コンパイラがWarningを出した場合、強制的にエラー(ビルド失敗)扱いにします。安定したバイナリを提供するために有効な設定に思えますが、現段階では推奨されていません。その理由は、2019年現在のRustが安定した仕様ではなく(仕様変更が多く)、下方互換性に関するWarningが出やすいためです(参考情報：[その1](https://github.com/rust-unofficial/patterns/blob/master/anti_patterns/deny-warnings.md)、[その2](https://users.rust-lang.org/t/how-to-fail-a-build-with-warnings/2687/7))。

2019年現在のRustは、構文と標準ライブラリAPIのみが安定しており、バージョンが上がると非推奨API(obsolete API)が増えます。非推奨APIは、ビルド時にWarningとして指摘されます。つまり、#!\[deny(warnings)\]を記述している場合、バージョンアップ後にビルドが壊れる可能性があります。

なお、#!\[deny(warnings)\]を使用せずに、Warning発生時にビルドエラーを発生させる方法は、

1. CI時(正確にはテスト時のみ)に有効化する方法
2. ビルド時オプションによる方法

の2通りがあります(正確には、他の方法もあります)。順に、方法を説明します。

**1\. CI時(正確にはテスト時のみ)に有効化する方法**

Cargo.tomlに\[features\]以下の内容を記載し、crate(lib.rsやmain.rs)のトップにcfg\_attr(条件付き属性)を記載します。

```
[features]
strict = []
```

```
#![cfg_attr(feature = "strict", deny(warnings))]

```

[cfg\_attr(条件付き属性)](https://doc.rust-jp.rs/the-rust-programming-language-ja/1.6/book/conditional-compilation.html)は、第一引数(今回はfeature="strict")が有効になっている場合、"#\[deny(warnings)\]"と同じ扱いになります。第一引数が無効の場合、この処理は何もしません。

第一引数を有効化するために、テスト時のコンパイルは、以下のようにcargoを実行します。この記載は、strict機能を有効化しています。

```
$ cargo build --features "strict"

```

**2.ビルド時オプションによる方法**

変数RUSTFLAGS経由で、cargoが呼び出すコンパイラに-D(deny)オプションを付与する事によって、Warning時にビルドエラーを発生させます。具体的には、以下の形式でビルドします。

```
$ RUSTFLAGS="-D warnings" cargo build

```

### main関数における標準出力・標準エラーの設定

以下に示すmain関数内で、標準出力へのハンドラ(変数stdout)、標準エラーのハンドラ(変数stderr)を取得します。それぞれ、バッファに関する仕様が異なります。

- 標準出力ハンドラは、[mutex(排他制御)](https://doc.rust-jp.rs/the-rust-programming-language-ja/1.6/book/concurrency.html)によってアクセス同期される共有グローバルバッファへの参照
- 標準エラーハンドラは、バッファリングされない

```
fn main() {
    let stdout = io::stdout();
    let mut stdout = stdout.lock();
    let mut stderr = io::stderr();
    exit(Program::initialize(&mut stdout, &mut stderr).and_execute(&mut stdout, &mut stderr));
}
```

"[stdout.lock()](https://doc.rust-lang.org/std/io/struct.Stdout.html#method.lock)"は、明示的にアクセスを同期させます。ハンドラを標準ストリームにmutexでロックし、書き込み可能な状態にします。一度だけロックを取得した方が、複数回ロックを取得するよりも高速で動作します。このロックは、ハンドラがスコープ範囲外となった場合(今回であればmain関数を抜けた場合)、解除されます。

同様に、"stderr.lock()"も存在しますが、使われていません。エラーメッセージは量が少ないため、明示的な同期が不要という判断でしょうか？

\[the\_ad id="598"\]

### main関数における構造体Programの初期化

main関数の残りの部分は、構造体Programの初期化(initialize())を実行後、メインとなる処理(and\_execute())を実行するだけです。and\_execute()の実行結果(終了ステータス)を引数として、現在のプロセスをexit()で終了させます。

```
struct Program {
    exit_status:      Cell,
    number:           bool,
    number_nonblank:  bool,
    show_ends:        bool,
    show_tabs:        bool,
    show_nonprinting: bool,
    squeeze_blank:    bool,
    paths:            Vec,
}

fn main() {
    /* 説明済みのため、省略 */
    exit(Program::initialize(&mut stdout, &mut stderr).and_execute(&mut stdout, &mut stderr));
}
```

構造体Programが持つメンバの意味合い(用途)は、下表の通りです。

| **メンバ名** | **用途** |
| --- | --- |
| exit\_status | catコマンドの終了ステータス |
| number | 表示対象ファイルの行番号を表示するためのフラグ |
| number\_nonblank | 表示対象ファイルの行番号(空白行を除く)を表示するためのフラグ |
| show\_ends | 行末を表示するためのフラグ |
| show\_tabs | Tabを表示するためのフラグ |
| show\_nonprinting | 非表示文字を表示するためのフラグ |
| squeeze\_blank | 連続した空行を一行に変更するためのフラグ |
| paths | 表示もしくは連結対象のファイルPATH |

初期化処理(initialize())の実装は、以下の通りです。initialize()は、実装の上に書かれているコメント通り、引数・フラグの初期化をしています。上から順番に説明します。

```
    /// Initialize the program's arguments and flags.
    fn initialize(stdout: &mut StdoutLock, stderr: &mut Stderr) -> Program {
        let mut parser = ArgParser::new(10).
            add_flag(&["A", "show-all"]). //vET
            add_flag(&["b", "number-nonblank"]).
            add_flag(&["e"]). //vE
            add_flag(&["E", "show-ends"]).
            add_flag(&["n", "number"]).
            add_flag(&["s", "squeeze-blank"]).
            add_flag(&["t"]). //vT
            add_flag(&["T", "show-tabs"]).
            add_flag(&["v", "show-nonprinting"]).
            add_flag(&["h", "help"]);
        parser.parse(env::args());

        let mut cat = Program {
            exit_status:      Cell::new(0i32),
            number:           false,
            number_nonblank:  false,
            show_ends:        false,
            show_tabs:        false,
            show_nonprinting: false,
            squeeze_blank:    false,
            paths:            Vec::with_capacity(parser.args.len()),
        };

        if parser.found("help") {
            stdout.write(MAN_PAGE.as_bytes()).try(stderr);
            stdout.flush().try(stderr);
            exit(0);
        }

        if parser.found("show-all") {
            cat.show_nonprinting = true;
            cat.show_ends = true;
            cat.show_tabs = true;
        }

        if parser.found("number") {
            cat.number = true;
            cat.number_nonblank = false;
        }

        if parser.found("number-nonblank") {
            cat.number_nonblank = true;
            cat.number = false;
        }

        if parser.found("show-ends") || parser.found(&'e') {
            cat.show_ends = true;
        }

        if parser.found("squeeze-blank") {
            cat.squeeze_blank = true;
        }

        if parser.found("show-tabs") || parser.found(&'t') {
            cat.show_tabs = true;
        }

        if parser.found("show-nonprinting") || parser.found(&'e') || parser.found(&'t') {
            cat.show_nonprinting = true;
        }

        if !parser.args.is_empty() {
            cat.paths = parser.args;
        }
        cat
    }
```

まず、引数の初期化部分(以下に示したコード)です。引数をパースするcrateは、Redoxプロジェクトが独自に作成したものです。この処理では、以下の内容を順番に実行しています。

1. オプションが10個として、ArgParserのコンストラクタ(new())を実行
2. add\_flag()でオプションを追加(第一引数=shotオプション、第二引数=longオプション)
3. 標準API経由(env::args())で、catコマンドの実行時オプションをパース

```
    /// Initialize the program's arguments and flags.
    fn initialize(stdout: &mut StdoutLock, stderr: &mut Stderr) -> Program {
        let mut parser = ArgParser::new(10).
            add_flag(&["A", "show-all"]). //vET
            add_flag(&["b", "number-nonblank"]).
            add_flag(&["e"]). //vE
            add_flag(&["E", "show-ends"]).
            add_flag(&["n", "number"]).
            add_flag(&["s", "squeeze-blank"]).
            add_flag(&["t"]). //vT
            add_flag(&["T", "show-tabs"]).
            add_flag(&["v", "show-nonprinting"]).
            add_flag(&["h", "help"]);
        parser.parse(env::args());

        /* 省略 */
    }

```

| **Shortオプション** | **Longオプション** | **機能** |
| --- | --- | --- |
| A | show-all | 全ての非表示文字(行末、Tab、CR)を表示 |
| b | number-nonblank | 空白行を除いて、行番号を付与 |
| e | なし | Tabを除いて、全ての非表示文字(行末、CR)を表示 |
| E | show-ends | 行の最後に"$"を表示 |
| n | number | 行番号を付与 |
| s | squeeze-blank | 連続した空行を一行に変更 |
| t | なし | TABを"^I"で表示 |
| T | show-tabs | TABを"^I"で表示 |
| v | show-nonprinting | 非表示文字を[キャレット記法](https://ja.wikipedia.org/wiki/%E3%82%AD%E3%83%A3%E3%83%AC%E3%83%83%E3%83%88%E8%A8%98%E6%B3%95)などで表示 |
| h | help | ヘルプを表示 |

初期化処理の残り部分は、catコマンドのオプションパース結果をもとに、各フラグを有効化し、表示・連結対象のファイルパスを保持するだけです。helpの表示のみ(以下の実装のみ)、説明します。

```
    fn initialize(stdout: &mut StdoutLock, stderr: &mut Stderr) -> Program {
        /* 省略 */
        if parser.found("help") {
            stdout.write(MAN_PAGE.as_bytes()).try(stderr);
            stdout.flush().try(stderr);
            exit(0);
        }
        /* 省略 */
    }

```

オプションパーサで"help"(もしくは"h")を見つけた場合、helpの表示処理に移ります。正常系の処理は、以下のように、コードを読んだ通りです。

- 標準出力に変数MAN\_PAGE(後述)をバイト列として出力
- ストリームバッファのフラッシュ(標準出力への書き出し)
- 正常終了

異常系の処理では、try()によるエラーハンドリングをしています。このtry()は、昔のバージョンで?演算子を用いてResult型(エラーかどうかを示す列挙型)を返していた処理と同等です。エラーハンドリングに用いる型を柔軟にするための処理のようですが、公式ドキュメントに詳細な説明がなかったため、割愛します。

変数MAN\_PAGEは、以下のように、help文をそのままハードコーディングされています。

```
const MAN_PAGE: &'static str = /* @MANSTART{cat} */ r#"NAME
    cat - concatenate files and print on the standard output

SYNOPSIS
    cat [-h | --help] [-A | --show-all] [-b | --number-nonblank] [-e] [-E | --show-ends]
        [-n | --number] [-s | --squeeze-blank] [-t] [-T] FILES...

  /* 長いため、省略 */

"#; /* @MANEND */

```

変数MAN\_PAGEは、&'static str型なので、文字リテラル(バイト列)としてバイナリ中に埋め込まれます。また、文字リテラルは、r#"文字列"#という形式で表記されています。この形式は、Raw(生)の文字リテラルを定義するために使います。この形式を用いる事によって、エスケープ文字("\\")なしで、文字リテラル内の特殊文字(エスケープシーケンス)を通常の文字として扱えます([参考](https://rahul-thakoor.github.io/rust-raw-string-literals/))。

### Reading結果 その2へのリンク

- [Code Reading：Redox(Rust)版coreutilsのcatコマンド その2(全2回)](https://debimate.jp/post/2019-05-11-code-readingredoxrust%E7%89%88coreutils%E3%81%AEcat%E3%82%B3%E3%83%9E%E3%83%B3%E3%83%89-%E3%81%9D%E3%81%AE2%E5%85%A82%E5%9B%9E/)
