---
title: "Code Reading：Redox(Rust)版coreutilsのcatコマンド その2(全2回)"
type: post
date: 2019-05-11
categories:
  - "linux"
tags:
  - "codereading"
  - "coreutils"
  - "linux"
  - "rust"
cover:
  image: images/s_cat2.jpg
  alt: "Code Reading：Redox(Rust)版coreutilsのcatコマンド その2(全2回)"
  hidden: false
---

## 前書き

Rustを学習するための一環として、Redox(OS)版coreutilsのcatコマンドをCode Readingします。本記事(その2)は、catコマンドの主要な処理(ファイル内容の表示)を説明します。catコマンドのオプションパース処理に関する内容は、以下に示す前回記事(その1)を確認して下さい。

https://debimate.jp/2019/05/06/code-reading%EF%BC%9Aredoxrust%E7%89%88coreutils%E3%81%AEcat%E3%82%B3%E3%83%9E%E3%83%B3%E3%83%89-%E3%81%9D%E3%81%AE1%E5%85%A82%E5%9B%9E/

## Reading対象のコード

本記事では、catコマンドの関数and\_execute(以下のコード)を読んだ結果を説明します。関連するコードは、解説のタイミングで適宜示します。全文を確認する場合、[Redox版coreutilsの公式リポジトリ](https://github.com/redox-os/coreutils/blob/master/src/bin/cat.rs)を参照して下さい。

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

impl Program {
    // 省略

    /// Execute the parameters given to the program.
    fn and_execute(&self, stdout: &mut StdoutLock, stderr: &mut Stderr) -> i32 {
        let stdin = io::stdin();
        let line_count = &mut 0usize;
        let flags_enabled = self.number || self.number_nonblank || self.show_ends || self.show_tabs ||
                            self.squeeze_blank || self.show_nonprinting;

        if self.paths.is_empty() && flags_enabled {
            self.cat(&mut stdin.lock(), line_count, stdout, stderr);
        } else if self.paths.is_empty() {
            self.simple_cat(&mut stdin.lock(), stdout, stderr);
        } else {
            for path in &self.paths {
                if flags_enabled && path == "-" {
                    self.cat(&mut stdin.lock(), line_count, stdout, stderr);
                } else if path == "-" {
                    // Copy the standard input directly to the standard output.
                    self.simple_cat(&mut stdin.lock(), stdout, stderr);
                } else if fs::metadata(&path).map(|m| m.is_dir()).unwrap_or(false) {
                    stderr.write(path.as_bytes()).try(stderr);
                    stderr.write(b": Is a directory\n").try(stderr);
                    stderr.flush().try(stderr);
                    self.exit_status.set(1i32);
                } else if flags_enabled {
                    fs::File::open(&path)
                        // Open the file and copy the file's contents to standard output based input arguments.
                        .map(|file| self.cat(&mut BufReader::new(file), line_count, stdout, stderr))
                        // If an error occurred, print the error and set the exit status.
                        .unwrap_or_else(|message| {
                            stderr.write(path.as_bytes()).try(stderr);
                            stderr.write(b": ").try(stderr);
                            stderr.write(message.description().as_bytes()).try(stderr);
                            stderr.write(b"\n").try(stderr);
                            stderr.flush().try(stderr);
                            self.exit_status.set(1i32);
                        });
                } else {
                    // Open a file and copy the contents directly to standard output.
                    fs::File::open(&path).map(|ref mut file| { self.simple_cat(file, stdout, stderr); })
                        // If an error occurs, print the error and set the exit status.
                        .unwrap_or_else(|message| {
                            stderr.write(path.as_bytes()).try(stderr);
                            stderr.write(b": ").try(stderr);
                            stderr.write(message.description().as_bytes()).try(stderr);
                            stderr.write(b"\n").try(stderr);
                            stderr.flush().try(stderr);
                            self.exit_status.set(1i32);
                        });
                }
            }
        }
        self.exit_status.get()
    }

    /// A simple cat that runs a lot faster than self.cat() due to no iterators over single bytes.
    fn simple_cat(&self, file: &mut F, stdout: &mut StdoutLock, stderr: &mut Stderr) {
        let mut buf: [u8; 8*8192] = [0; 8*8192]; // 64K seems to be the sweet spot for a buffer on my machine.
        loop {
            let n_read = file.read(&mut buf).try(stderr);
            if n_read == 0 { // We've reached the end of the input
                break;
            }
            stdout.write_all(&buf[..n_read]).try(stderr);
        }
    }

    /// Cats either a file or stdin based on the flag arguments given to the program.
    fn cat(&self, file: &mut F, line_count: &mut usize, stdout: &mut StdoutLock, stderr: &mut Stderr) {
        let mut character_count = 0;
        let mut last_line_was_blank = false;
        let mut buf: [u8; 8*8192] = [0; 8*8192]; // 64K seems to be the sweet spot for a buffer on my machine.
        let mut out_buf: Vec = Vec::with_capacity(24*8192); // Worst case 2 chars out per char
        loop {
            let n_read = file.read(&mut buf).try(stderr);
            if n_read == 0 { // We've reached the end of the input
                break;
            }

            for &byte in buf[0..n_read].iter() {
                if character_count == 0 && (self.number || (self.number_nonblank && byte != b'\n')) {
                    out_buf.write(b"     ").try(stderr);
                    out_buf.write(line_count.to_string().as_bytes()).try(stderr);
                    out_buf.write(b"  ").try(stderr);
                    *line_count += 1;
                }
                match byte {
                    0...8 | 11...31 => if self.show_nonprinting {
                        push_caret(&mut out_buf, stderr, byte+64);
                        count_character(&mut character_count, &self.number, &self.number_nonblank);
                    },
                    9 => {
                        if self.show_tabs {
                            push_caret(&mut out_buf, stderr, b'I');
                        } else {
                            out_buf.write(&[byte]).try(stderr);
                        }
                        count_character(&mut character_count, &self.number, &self.number_nonblank);
                    }
                    10 => {
                        if character_count == 0 {
                            if self.squeeze_blank && last_line_was_blank {
                                continue
                            } else if !last_line_was_blank {
                                last_line_was_blank = true;
                            }
                        } else {
                            last_line_was_blank = false;
                            character_count = 0;
                        }
                        if self.show_ends {
                            out_buf.write(b"$\n").try(stderr);
                        } else {
                            out_buf.write(b"\n").try(stderr);
                        }
                    },
                    32...126 => {
                        out_buf.write(&[byte]).try(stderr);
                        count_character(&mut character_count, &self.number, &self.number_nonblank);
                    },
                    127 => if self.show_nonprinting {
                        push_caret(&mut out_buf, stderr, b'?');
                        count_character(&mut character_count, &self.number, &self.number_nonblank);
                    },
                    128...159 => if self.show_nonprinting {
                        out_buf.write(b"M-^").try(stderr);
                        out_buf.write(&[byte-64]).try(stderr);
                        count_character(&mut character_count, &self.number, &self.number_nonblank);
                    } else {
                        out_buf.write(&[byte]).try(stderr);
                        count_character(&mut character_count, &self.number, &self.number_nonblank);
                    },
                    _ => if self.show_nonprinting {
                        out_buf.write(b"M-").try(stderr);
                        out_buf.write(&[byte-128]).try(stderr);
                        count_character(&mut character_count, &self.number, &self.number_nonblank);
                    } else {
                        out_buf.write(&[byte]).try(stderr);
                        count_character(&mut character_count, &self.number, &self.number_nonblank);
                    },
                }
            }
            stdout.write_all(&out_buf).try(stderr);
            out_buf.clear();
        }
    }

　// 省略
}

```

上記のコードで、構造体Programが持つメンバの意味合い(用途)は、下表の通りです。

| **メンバ名** | **用途** |
| --- | --- |
| exit\_status | catコマンドの終了ステータス |
| number | 表示対象ファイルの行番号を表示するためのフラグ |
| number\_nonblank | 表示対象ファイルの行番号(空白行を除く)を表示するためのフラグ |
| show\_ends | 行末を表示するためのフラグ |
| show\_tabs | Tabを表示するためのフラグ |
| show\_nonprinting | 非表示文字(行末、Tab、CR)を表示するためのフラグ |
| squeeze\_blank | 連続した空行を一行に変更するためのフラグ |
| paths | 表示もしくは連結対象のファイルPATH |

catコマンドの関数and\_execute()は、大別して以下の3つの処理に分岐します。本記事では、これらの分岐処理に関して説明します。

and\_execute()処理：3種類の分岐

- 「引数でファイルPATHを指定しない」かつ「オプションを指定した」場合
- 引数でファイルPATHおよびオプションを指定しない場合
- 引数でファイルPATHを指定した場合

## 「引数でファイルPATHを指定しない」かつ「オプションを指定した」場合

本ケースは、ファイルPATHが指定されていないため、ユーザからの標準入力を標準出力に返します。さらに、オプションを解釈します。以下に、catコマンドをnオプション(行番号表示)のみで実行した例を示します。

```
$ ./target/debug/cat -n
この文章はテストです。
     0  この文章はテストです。
標準入力の内容を標準出力に表示します。
     1  標準入力の内容を標準出力に表示します。
今回は、行番号を表示するオプション="n"を付与しています。
     2  今回は、行番号を表示するオプション="n"を付与しています。
そのため、標準出力に行番号も付いています。
     3  そのため、標準出力に行番号も付いています。

```

本ケースに該当するコードおよび各変数の意味合いを以下に示します。

- 変数stdinは、標準入力へのハンドラ
- 変数line\_countは、行番号の格納用
- 変数flags\_enabledは、ユーザがオプションを付与して実行したかを管理するフラグ

```
     fn and_execute(&self, stdout: &mut StdoutLock, stderr: &mut Stderr) -> i32 {
        let stdin = io::stdin();
        let line_count = &mut 0usize;
        let flags_enabled = self.number || self.number_nonblank || self.show_ends || self.show_tabs ||
                            self.squeeze_blank || self.show_nonprinting;

        if self.paths.is_empty() && flags_enabled {
            self.cat(&mut stdin.lock(), line_count, stdout, stderr);
        } 
        // 以下、省略
    }
```

最初のif文を抜けると、関数self.cat()を呼び出します。この関数cat()では、以下の3点を実施します。

1. 標準入力(もしくはファイル)から文字を読込
2. 1Byteずつオプション処理しつつ、1.で読み込んだデータを全て一時バッファに書込
3. 一時バッファを標準出力に書き込み

一時バッファ経由で標準出力に書き込む理由は、I/O速度を向上させるためです。Rust は、アクセス競合を起こさないように、非バッファI/Oを採用しています。非バッファI/Oは、処理が遅いです。遅い理由は、Read/Writeの度にLock/Unlock処理を繰り返す事、およびシステムコール使用回数がバッファを利用している時用も増えてしまう事が挙げられます([参考](https://stackoverflow.com/questions/43028653/rust-file-i-o-is-very-slow-compared-with-c-is-something-wrong))。

\[the\_ad id="598"\]

では、上述の1.〜3.の処理を順に説明します。

**標準入力から文字を読み込む処理**

以下に、該当部分のコードおよび変数の意味合いを示します。

- 変数character\_countは、文字数
- 変数last\_line\_was\_blankは、最終行が空行だったかを示すフラグ
- 変数bufは、標準入力から読み込んだデータを保持するバッファ(「実装者の環境では64KBが最適だった」とコメントがあります)
- 変数out\_bufは、標準出力へ書き込むデータの一時バッファ(192KB。オプションによっては、入力1文字に対して2文字追記するケース、つまり出力が3文字になるケースがあるため、このサイズにしています)

```
    /// Cats either a file or stdin based on the flag arguments given to the program.
    fn cat(&self, file: &mut F, line_count: &mut usize, stdout: &mut StdoutLock, stderr: &mut Stderr) {
        let mut character_count = 0;
        let mut last_line_was_blank = false;
        let mut buf: [u8; 8*8192] = [0; 8*8192]; // 64K seems to be the sweet spot for a buffer on my machine.
        let mut out_buf: Vec = Vec::with_capacity(24*8192); // Worst case 2 chars out per char
        loop {
            let n_read = file.read(&mut buf).try(stderr);
            if n_read == 0 { // We've reached the end of the input
                break;
            }
        /* 省略 */

```

ループの頭では、関数file.read()によって、標準入力(もしくはファイル)の内容を変数bufに代入しています。戻り値n\_readは、読み込んだ文字数を表します。そのため、読み込んだ文字数が0の場合は、ファイルの終端に達したと判断し、ループを抜けます。

今回は、標準入力の例なので、このif文内の処理(break)を実行する事はありません。

**1Byteずつオプション処理しつつ、読み込んだデータを全て一時バッファに書込**

前提として、Rustの文字コードはUTF-8です。UTF-8は、半角英数字(一部記号含む)のみ、ASCIIと同じ体系になっています。具体的には、下表に示す「数字(0〜160)」と「文字(記号)」との組み合わせがASCIIと同じです。

表中の赤字部分は、catコマンドのオプションによって、別文字に置換される文字です。

| **数字** | **文字** | **数字** | **文字** | **数字** | **文字** | **数字** | **文字** | **数字** | **文字** |
| :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| 0 | NULL | 33 | ! | 66 | B | 99 | c | 132 | IND |
| 1 | SOH | 34 | " | 67 | C | 100 | d | 133 | NEL |
| 2 | STX | 35 | # | 68 | D | 101 | e | 134 | SSA |
| 3 | ETX | 36 | $ | 69 | E | 102 | f | 135 | ESA |
| 4 | EOT | 37 | % | 70 | F | 103 | g | 136 | HTS |
| 5 | ENQ | 38 | & | 71 | G | 104 | h | 137 | HTJ |
| 6 | ACK | 39 | ' | 72 | H | 105 | i | 138 | VTS |
| 7 | BEL | 40 | ( | 73 | I | 106 | j | 139 | PLD |
| 8 | BS | 41 | ) | 74 | J | 107 | k | 140 | PLU |
| 9 | TAB | 42 | \* | 75 | K | 108 | l | 141 | RI |
| 10 | LF | 43 | + | 76 | L | 109 | m | 142 | SS2 |
| 11 | VT | 44 | , | 77 | M | 110 | n | 143 | SS3 |
| 12 | FF | 45 | \- | 78 | N | 111 | o | 144 | DCS |
| 13 | CR | 46 | 0 | 79 | O | 112 | p | 145 | PU1 |
| 14 | SO | 47 | / | 80 | P | 113 | q | 146 | PU2 |
| 15 | SI | 48 | 0 | 81 | Q | 114 | r | 147 | STS |
| 16 | DLE | 49 | 1 | 82 | R | 115 | s | 148 | CCH |
| 17 | DC1 | 50 | 2 | 83 | S | 116 | t | 149 | MW |
| 18 | DC2 | 51 | 3 | 84 | T | 117 | u | 150 | SPA |
| 19 | DC3 | 52 | 4 | 85 | U | 118 | v | 151 | EPA |
| 20 | DC4 | 53 | 5 | 86 | V | 119 | w | 152 | SOS |
| 21 | NAK | 54 | 6 | 87 | W | 120 | x | 153 | SGCI |
| 22 | SYN | 55 | 7 | 88 | X | 121 | y | 154 | SCI |
| 23 | ETB | 56 | 8 | 89 | Y | 122 | z | 155 | CSI |
| 24 | CAN | 57 | 9 | 90 | Z | 123 | { | 156 | ST |
| 25 | EM | 58 | : | 91 | \[ | 124 | \| | 157 | OSC |
| 26 | SUB | 59 | ; | 92 | \\ | 125 | } | 158 | PM |
| 27 | ESC | 60 | < | 93 | \] | 126 | ~ | 159 | APC |
| 28 | FS | 61 | \= | 94 | ^ | 127 | DEL | 160 | NBSP |
| 29 | GS | 62 | \> | 95 | \_ | 128 | PAD |   |  |
| 30 | RS | 63 | ? | 96 | \` | 129 | HOP |
| 31 | US | 64 | @ | 97 | a | 130 | BPH |
| 32 | Space | 65 | A | 98 | b | 131 | NBH |

以上の文字コード(UTF-8)の情報を踏まえて、catコマンドのByte処理を説明します。まず、読み込んだデータに対して、行番号を付与します。具体的には、一文字も読み込んでなく、「number(n)オプションが有効の場合」か「"nunber-noblank(b)オプション(空白行を除いて行番号を付与)"かつ"入力文字が改行ではない場合"」に、行番号を付与します。

```
        // 省略
        loop {
            for &byte in buf[0..n_read].iter() {
                if character_count == 0 && (self.number || (self.number_nonblank && byte != b'\n')) {
                    out_buf.write(b"     ").try(stderr);
                    out_buf.write(line_count.to_string().as_bytes()).try(stderr);
                    out_buf.write(b"  ").try(stderr);
                    *line_count += 1;
                }
               // 省略

```

```
(注釈)：number-nonblankオプションを有効にした実行例
$ cat -b
test
     0  test
                               (注釈)：この行は何も入力しないで、Enter

空行は行番号がつかない
     1  空行は行番号がつかない

```

次に、1Byteで表現された文字の処理です。実装順に説明します。

以下のコードは、非表示文字(0〜31)に対する処理です。show-nonprintingオプションが有効の場合、キャレット記法(表示できない文字を特定の文字列で表示する方法)で表します。[キャレット記法では、"^"と"非表示文字(0〜31)に64を加算した数値に対応する英字・記号"によって、非表示文字を表します](https://ja.wikipedia.org/wiki/%E5%88%B6%E5%BE%A1%E6%96%87%E5%AD%97)。

例えば、非表示文字であるNUL(0)の場合、"^"と"@(64)"を合わせた"^@"で表します。以上を踏まえてコードを確認すると、以下の処理はキャレット記法で文字を一時バッファに書き込み、その後に文字数をカウント(保持)しているだけと分かります。

```
           match byte {
                 0...8 | 11...31 => if self.show_nonprinting {
                        push_caret(&mut out_buf, stderr, byte+64);
                        count_character(&mut character_count, &self.number, &self.number_nonblank);
                    },

```

```
/// Print a caret notation to stdout.
fn push_caret(stdout: &mut T, stderr: &mut Stderr, notation: u8) {
    stdout.write(&[b'^']).try(stderr);
    stdout.write(&[notation]).try(stderr);
}

```

次の処理(以下のコード)は、show-tabsオプションが有効の場合、TAB(9)をキャレット記法で一時バッファに書き込みます。TABの場合は、直接”I(9+64=73)”を渡しています。show-tabsオプションが無効の場合、Byteをそのまま一時バッファに書き込みます。その後、文字数をカウント(保持)します。

```
                    9 => {
                        if self.show_tabs {
                            push_caret(&mut out_buf, stderr, b'I');
                        } else {
                            out_buf.write(&[byte]).try(stderr);
                        }
                        count_character(&mut character_count, &self.number, &self.number_nonblank);
                    }

```

次の処理(以下のコード)は、改行LF(10)の処理で、主に2つのオプションを処理しています。

- 文字数が0の場合、squeeze-blankオプション(連続した空行を1行に変更)を実施
- show-endsオプション(行の最後に”$”を表示)の実施

1つ目の処理は、文字数が0でこの処理を初めて通った場合、最終行が空行だった事を変数last\_line\_was\_blankフラグに保持(=trueに変更)します。文字数が0でlast\_line\_was\_blankフラグ有効(この処理を通るのが2回目以降)の場合、ループの先頭に戻る事で空行を増やしません。文字数が1以上の場合、後ほど改行処理が入るため、「最終行が空行フラグ」および「文字数」をリセットし、次のループ処理に備えます。

2つ目の処理は、一時バッファに書き込む内容を分けています。

- show-endsオプションが有効の場合、"$"と改行("\\n")を書込
- show-endsオプションが無効の場合、改行("\\n")のみを書込

```
                  10 => {
                        if character_count == 0 {
                            if self.squeeze_blank && last_line_was_blank {
                                continue
                            } else if !last_line_was_blank {
                                last_line_was_blank = true;
                            }
                        } else {
                            last_line_was_blank = false;
                            character_count = 0;
                        }
                        if self.show_ends {
                            out_buf.write(b"$\n").try(stderr);
                        } else {
                            out_buf.write(b"\n").try(stderr);
                        }
                    },

```

次の処理(以下のコード)は、英数字・一部の記号を表示する処理です。オプション処理が不要なため、そのまま一時バッファに書き込み、文字数をカウントします。

```
                 32...126 => {
                        out_buf.write(&[byte]).try(stderr);
                        count_character(&mut character_count, &self.number, &self.number_nonblank);
                    },

```

次の処理(以下のコード)は、「非表示文字(0〜31)をキャレット記法で表示した処理」と同等の内容を非表示文字(127〜159)に対して実施します。show-nonprintingオプションが有効の場合、非表示文字を可視化します。無効の場合、そのまま一時バッファに書き込みます。どちらの場合も、文字数をカウントします。

DEL(127)のみキャレット記法で表示し、他の非表示文字(128〜159)は"M-^"および"非表示文字から64を減算した数値に対応する英字・記号"で表示します。例えば、PAD(128)の場合、"M-^"と"@(64)"を合わせた"M-^@"で表します。

```
                   127 => if self.show_nonprinting {
                        push_caret(&mut out_buf, stderr, b'?');
                        count_character(&mut character_count, &self.number, &self.number_nonblank);
                    },
                   128...159 => if self.show_nonprinting {
                        out_buf.write(b"M-^").try(stderr);
                        out_buf.write(&[byte-64]).try(stderr);
                        count_character(&mut character_count, &self.number, &self.number_nonblank);
                    } else {
                        out_buf.write(&[byte]).try(stderr);
                        count_character(&mut character_count, &self.number, &self.number_nonblank);
                    },

```

次の処理(以下のコード)は、0〜159以外の数値に変換される文字を処理します。この処理も他の非表示文字に対する処理に似た対応をします。具体的には、該当の文字(!=0〜159)は、"M-"および"非表示文字から128を減算した数値に対応する英字・記号"で表示します。変換した文字を一時バッファに書き込み、文字数をカウントします。

```
                    _ => if self.show_nonprinting {
                        out_buf.write(b"M-").try(stderr);
                        out_buf.write(&[byte-128]).try(stderr);
                        count_character(&mut character_count, &self.number, &self.number_nonblank);
                    } else {
                        out_buf.write(&[byte]).try(stderr);
                        count_character(&mut character_count, &self.number, &self.number_nonblank);
                    },

```

**一時バッファを標準出力に書込**

この処理(以下のコード)は、単純です。この処理に達している場合、標準出力から読み込んだデータ全てが一時バッファに書き込まれた状態です。その一時バッファ内容を標準出力に書き込みます。その後、もう一度標準入力の内容を読み込むループの先頭に戻るため、一時バッファをクリアします。

```
            stdout.write_all(&out_buf).try(stderr);
            out_buf.clear();

```

## 引数でファイルPATHおよびオプションを指定しない場合

本ケースは、ファイルPATHおよびオプションが指定されていないため、単純にユーザからの標準入力を標準出力に返します。以下に、本ケースでcatコマンドを実行した例を示します。

```
$ cat
この文章はテストです
この文章はテストです
オプションがないため、入力内容をそのまま表示します
オプションがないため、入力内容をそのまま表示します
```

本ケースでは、関数simple\_cat()が呼ばれます。関数simple\_catは、関数cat()からオプション対応を無くしただけです。以下の処理を実施しています。

- 標準入力(もしくはファイル内容)を読み込むためのバッファ確保(64KB)
- バッファに標準入力(もしくはファイル内容)の内容を読込
- バッファの内容を標準出力に書込

```
    /// Execute the parameters given to the program.
    fn and_execute(&self, stdout: &mut StdoutLock, stderr: &mut Stderr) -> i32 {
         /* 省略 */
        } else if self.paths.is_empty() {
            self.simple_cat(&mut stdin.lock(), stdout, stderr);
        } 
        /* 省略 */
    }

    /// A simple cat that runs a lot faster than self.cat() due to no iterators over single bytes.
    fn simple_cat(&self, file: &mut F, stdout: &mut StdoutLock, stderr: &mut Stderr) {
        let mut buf: [u8; 8*8192] = [0; 8*8192]; // 64K seems to be the sweet spot for a buffer on my machine.
        loop {
            let n_read = file.read(&mut buf).try(stderr);
            if n_read == 0 { // We've reached the end of the input
                break;
            }
            stdout.write_all(&buf[..n_read]).try(stderr);
        }
    }

```

## 引数でファイルPATHを指定した場合

本ケース(以下のコード)では、渡されたPATHの数だけループを繰り返し、以下の5通りで分岐処理します。分岐1.と分岐2.は、説明済みの内容のため、省略します。

1. 「オプション有効」かつ「PATH="-"(標準入力と同等)」の場合、関数cat()を実行
2. 「オプション無効」かつ「PATH="-"(標準入力と同等)」の場合、関数simple\_cat()を実行
3. PATHがDirectoryの場合、エラーメッセージを表示し、終了(後述)
4. 「オプション有効」かつ「PATH=File」の場合、関数cat()を実行(後述)
5. 「オプション無効」かつ「PATH=File」の場合、関数simple\_cat()を実行(後述)

```
    /// Execute the parameters given to the program.
    fn and_execute(&self, stdout: &mut StdoutLock, stderr: &mut Stderr) -> i32 {
       // 省略

        } else {
            for path in &self.paths {
                if flags_enabled && path == "-" {
                    self.cat(&mut stdin.lock(), line_count, stdout, stderr);
                } else if path == "-" {
                    // Copy the standard input directly to the standard output.
                    self.simple_cat(&mut stdin.lock(), stdout, stderr);
                } else if fs::metadata(&path).map(|m| m.is_dir()).unwrap_or(false) {
                    stderr.write(path.as_bytes()).try(stderr);
                    stderr.write(b": Is a directory\n").try(stderr);
                    stderr.flush().try(stderr);
                    self.exit_status.set(1i32);
                } else if flags_enabled {
                    fs::File::open(&path)
                        // Open the file and copy the file's contents to standard output based input arguments.
                        .map(|file| self.cat(&mut BufReader::new(file), line_count, stdout, stderr))
                        // If an error occurred, print the error and set the exit status.
                        .unwrap_or_else(|message| {
                            stderr.write(path.as_bytes()).try(stderr);
                            stderr.write(b": ").try(stderr);
                            stderr.write(message.description().as_bytes()).try(stderr);
                            stderr.write(b"\n").try(stderr);
                            stderr.flush().try(stderr);
                            self.exit_status.set(1i32);
                        });
                } else {
                    // Open a file and copy the contents directly to standard output.
                    fs::File::open(&path).map(|ref mut file| { self.simple_cat(file, stdout, stderr); })
                        // If an error occurs, print the error and set the exit status.
                        .unwrap_or_else(|message| {
                            stderr.write(path.as_bytes()).try(stderr);
                            stderr.write(b": ").try(stderr);
                            stderr.write(message.description().as_bytes()).try(stderr);
                            stderr.write(b"\n").try(stderr);
                            stderr.flush().try(stderr);
                            self.exit_status.set(1i32);
                        });
                }
            }
        }
        self.exit_status.get()
    }

```

まず、分岐3.「 PATHがディレクトリの場合」を説明します。PATHがディレクトリかどうかを判断するために、fs::metadata(&path)を用います。fs::metadata()は、引数にPATHを渡して、filesystemに問い合わせて、PATHがFileかDirctoryかなどに関するメタ情報を取得します。具体的には、std::fs::Metadata構造体を返します。

fs::metadata()は、シンボリックリンクの場合はリンク元まで辿ります。エラーとなるケースは、主に2つです。

- PATHにFileやDirectoryが存在しない場合
- アクセス権限がない場合

fs::metadata(&path)に続くmap(|m| m.is\_dir())は、[クロージャ](https://keens.github.io/blog/2016/10/10/rustnokuro_ja3tanewotsukutterikaisuru/)であり、Metadata構造体の関数であるis\_dir()を用いて、Directoryかどうかの判定をしています。以上の処理でエラーが発生した場合、以下のエラーを出します。

```
$ cat $(pwd)          (注釈)：引数はカレントワーキングディレクトリ
/home/nao/RUST2/coreutils: Is a directory
```

次に、分岐4.「オプション有効かつPATH=Fileの場合」を説明します。関数cat()に渡せる形式にPATHを変換するために、fs::File::open(&path)を実行します。エラーハンドリングに用いられているunwrap\_or\_else()は、関数cat()が成功した場合は成功値を返し、失敗した場合はクロージャ(message)を呼び出します。また、std::error::Errorに用いられるdescription()は、非推奨になりつつある関数で、Errorトレイトに定義済みのエラーメッセージを表示します。エラーメッセージのサンプルを示します。

```
PATH: "この部分に、エラーに応じたメッセージが出力されます"
```

最後に、分岐5. 「オプション無効かつPATH=Fileの場合」を説明します。オプション有効時と同様に、関数simple\_cat()に渡せる形式にPATHを変換するために、fs::File::open(&path)を実行します。オプション有効時と無効時の差異は、有効時は速度向上を目的としてBufReaderの参照を関数cat()に渡しますが、無効時は文字列加工をしないのでfileへのミュータブル参照をそのまま関数simple\_cat()に渡します。エラーハンドリングは、オプション有効時と同じです。

## 最後に

Redox版coreutils(Rust版coreutils)のCode Readingは、catコマンドだけでなく、他のコマンドに対しても実施しています。興味があれば、以下の記事から参照できます。

https://debimate.jp/2019/05/03/%E7%92%B0%E5%A2%83%E6%A7%8B%E7%AF%89%EF%BC%9Aredox%E5%90%91%E3%81%91coreutilsrust%E3%81%AEcode-reading%E6%BA%96%E5%82%99%E3%81%8A%E3%82%88%E3%81%B3reading%E5%AF%BE%E8%B1%A1%E3%82%B3%E3%83%9E/
