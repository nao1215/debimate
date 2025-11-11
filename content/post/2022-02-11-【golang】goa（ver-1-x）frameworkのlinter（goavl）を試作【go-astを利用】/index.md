---
title: "【Golang】goa（ver 1.x）frameworkのlinter（goavl）を試作【go/astを利用】"
type: post
date: 2022-02-11
categories:
  - "linux"
tags:
  - "cli"
  - "golang"
  - "linux"
  - "ツール"
  - "体験談"
cover:
  image: "images/owl-g4a1fd006f_640.jpg"
  alt: "【Golang】goa（ver 1.x）frameworkのlinter（goavl）を試作【go/astを利用】"
  hidden: false
---

### 前書き：DSLに半日悩み、カッとなって作った

[goa](https://github.com/shogo82148/goa-v1)は、[DSL](https://ja.wikipedia.org/wiki/%E3%83%89%E3%83%A1%E3%82%A4%E3%83%B3%E5%9B%BA%E6%9C%89%E8%A8%80%E8%AA%9E)で記述されたデザインをもとに、Web APIホスティングに必要なベース処理（ルーティング、コントローラ、Swaggerなど）を生成するFrameworkです。[goaを採用している会社の例は、DMM](https://logmi.jp/tech/articles/323091)。goaを使うとコード記述量が減り、APIドキュメントが自動生成される利点があります。

私は、2022年1月からgoaを開発で使用するようになりました。goaは、DSLを覚えるコストが小さくはありません。DSLを書き間違えると、当然goa-designから各種ファイルの生成処理でエラーとなります。

ここでのエラー文章は簡潔（例：「パニックが起きた」）であり、プログラマに優しくありません。例えば、近年のコンパイラはユーザフレンドリーで、実装ミスをしている箇所を表示し、間違いの原因（推測）も出力します。goaはそのような情報を一切出力しません。この仕様は、goa初心者には辛いものです。ドキュメントやgoa-designコードを読み漁る時間が増えます。

この課題を解決するため、[goa version1（フォーク版）](https://github.com/shogo82148/goa-v1)のlinterとして、[goavl](https://github.com/nao1215/goavl)の開発を始めました。開発目的は、goaを用いたWeb APIデザイン設計速度を早め、チーム内でのgoa-designの差異を極力小さくする事です。

goavlは、**goa version 1 のみをサポート**し、現行のversion 3 はサポートしない予定です。その理由は、フォークしたgoa version 1 を私が利用しているからです。何故、フォーク版を使用しているかの背景は、[他のサイト](https://furusax0621.hatenablog.com/entry/2021/12/13/000000)で説明しています（記事の作者とgoavl開発者は別人のため注意）

本記事では、「goavlをどのように機能を用いて実装したかの説明（ザックリ説明）」と「goavlの基本機能」について説明します。

### GolangはASTを作る標準パッケージが存在

linter（静的解析ツール）を作る場合は、ソースコードの中身を解析する必要があります。

コンパイラを自作した経験がある方は、「字句解析器（lexer、tokenizer）や構文解析器（parser）を作るの大変だな」と考えるかもしれません（私は新卒で入社した会社で、構文解析器を上手く作れなかった苦い経験があります。雑な設計では動きません）。

Golangでは、標準パッケージ[go/ast](https://pkg.go.dev/go/ast)がAST（構文解析木）を作成してくれます。そのため、lexerやparserを自作せずにすみます。さらに、ASTを可視化する関数ast.Print() が用意されており、ASTを目視確認しながら実装を進められます。これが本当に便利。

どれぐらい便利かというと、目的の機能をlinterに導入するのに要した時間が10〜12時間ぐらいでした。go/astやast.Print() がなければ、10倍以上の時間が必要だったと思います。

### ASTの出力例

以下のコードで、ASTを出力できます。

```
package main

import (
	"go/ast"
	"go/parser"
	"go/token"
	"os"
)

func main() {
	filepath := os.Args[1] // 今回は、引数でこのファイル自身を指定する
	fset := token.NewFileSet()
	f, _ := parser.ParseFile(fset, filepath, nil, 0)
	ast.Print(fset, f)
}
```

上記ファイル自体をast.Print()した結果は、以下の通りです（約250行）。

0行目に書かれているast.Fileノードは、goファイル（1個）のASTを表す構造体です。ast.File構造体には、パッケージ名やインポートPATH、変数や関数の宣言／実装が全て代入されています。ここからお目当ての変数や関数を探し出す作業は、以下のast.Print()結果を見ながら行います。

ast.Print()結果には、Package、Name、Specsなどの変数名が書かれており、変数の内容も合わせて出力されています。この情報を見ながら、ノードを辿る作業を行います。

```
     0  *ast.File {
     1  .  Package: cmd/ast/main.go:1:1
     2  .  Name: *ast.Ident {
     3  .  .  NamePos: cmd/ast/main.go:1:9
     4  .  .  Name: "main"
     5  .  }
     6  .  Decls: []ast.Decl (len = 2) {
     7  .  .  0: *ast.GenDecl {
     8  .  .  .  TokPos: cmd/ast/main.go:3:1
     9  .  .  .  Tok: import
    10  .  .  .  Lparen: cmd/ast/main.go:3:8
    11  .  .  .  Specs: []ast.Spec (len = 4) {
    12  .  .  .  .  0: *ast.ImportSpec {
    13  .  .  .  .  .  Path: *ast.BasicLit {
    14  .  .  .  .  .  .  ValuePos: cmd/ast/main.go:4:2
    15  .  .  .  .  .  .  Kind: STRING
    16  .  .  .  .  .  .  Value: "\"go/ast\""
    17  .  .  .  .  .  }
    18  .  .  .  .  .  EndPos: -
    19  .  .  .  .  }
    20  .  .  .  .  1: *ast.ImportSpec {
    21  .  .  .  .  .  Path: *ast.BasicLit {
    22  .  .  .  .  .  .  ValuePos: cmd/ast/main.go:5:2
    23  .  .  .  .  .  .  Kind: STRING
    24  .  .  .  .  .  .  Value: "\"go/parser\""
    25  .  .  .  .  .  }
    26  .  .  .  .  .  EndPos: -
    27  .  .  .  .  }
    28  .  .  .  .  2: *ast.ImportSpec {
    29  .  .  .  .  .  Path: *ast.BasicLit {
    30  .  .  .  .  .  .  ValuePos: cmd/ast/main.go:6:2
    31  .  .  .  .  .  .  Kind: STRING
    32  .  .  .  .  .  .  Value: "\"go/token\""
    33  .  .  .  .  .  }
    34  .  .  .  .  .  EndPos: -
    35  .  .  .  .  }
    36  .  .  .  .  3: *ast.ImportSpec {
    37  .  .  .  .  .  Path: *ast.BasicLit {
    38  .  .  .  .  .  .  ValuePos: cmd/ast/main.go:7:2
    39  .  .  .  .  .  .  Kind: STRING
    40  .  .  .  .  .  .  Value: "\"os\""
    41  .  .  .  .  .  }
    42  .  .  .  .  .  EndPos: -
    43  .  .  .  .  }
    44  .  .  .  }
    45  .  .  .  Rparen: cmd/ast/main.go:8:1
    46  .  .  }
    47  .  .  1: *ast.FuncDecl {
    48  .  .  .  Name: *ast.Ident {
    49  .  .  .  .  NamePos: cmd/ast/main.go:10:6
    50  .  .  .  .  Name: "main"
    51  .  .  .  .  Obj: *ast.Object {
    52  .  .  .  .  .  Kind: func
    53  .  .  .  .  .  Name: "main"
    54  .  .  .  .  .  Decl: *(obj @ 47)
    55  .  .  .  .  }
    56  .  .  .  }
    57  .  .  .  Type: *ast.FuncType {
    58  .  .  .  .  Func: cmd/ast/main.go:10:1
    59  .  .  .  .  Params: *ast.FieldList {
    60  .  .  .  .  .  Opening: cmd/ast/main.go:10:10
    61  .  .  .  .  .  Closing: cmd/ast/main.go:10:11
    62  .  .  .  .  }
    63  .  .  .  }
    64  .  .  .  Body: *ast.BlockStmt {
    65  .  .  .  .  Lbrace: cmd/ast/main.go:10:13
    66  .  .  .  .  List: []ast.Stmt (len = 4) {
    67  .  .  .  .  .  0: *ast.AssignStmt {
    68  .  .  .  .  .  .  Lhs: []ast.Expr (len = 1) {
    69  .  .  .  .  .  .  .  0: *ast.Ident {
    70  .  .  .  .  .  .  .  .  NamePos: cmd/ast/main.go:11:2
    71  .  .  .  .  .  .  .  .  Name: "filepath"
    72  .  .  .  .  .  .  .  .  Obj: *ast.Object {
    73  .  .  .  .  .  .  .  .  .  Kind: var
    74  .  .  .  .  .  .  .  .  .  Name: "filepath"
    75  .  .  .  .  .  .  .  .  .  Decl: *(obj @ 67)
    76  .  .  .  .  .  .  .  .  }
    77  .  .  .  .  .  .  .  }
    78  .  .  .  .  .  .  }
    79  .  .  .  .  .  .  TokPos: cmd/ast/main.go:11:11
    80  .  .  .  .  .  .  Tok: :=
    81  .  .  .  .  .  .  Rhs: []ast.Expr (len = 1) {
    82  .  .  .  .  .  .  .  0: *ast.IndexExpr {
    83  .  .  .  .  .  .  .  .  X: *ast.SelectorExpr {
    84  .  .  .  .  .  .  .  .  .  X: *ast.Ident {
    85  .  .  .  .  .  .  .  .  .  .  NamePos: cmd/ast/main.go:11:14
    86  .  .  .  .  .  .  .  .  .  .  Name: "os"
    87  .  .  .  .  .  .  .  .  .  }
    88  .  .  .  .  .  .  .  .  .  Sel: *ast.Ident {
    89  .  .  .  .  .  .  .  .  .  .  NamePos: cmd/ast/main.go:11:17
    90  .  .  .  .  .  .  .  .  .  .  Name: "Args"
    91  .  .  .  .  .  .  .  .  .  }
    92  .  .  .  .  .  .  .  .  }
    93  .  .  .  .  .  .  .  .  Lbrack: cmd/ast/main.go:11:21
    94  .  .  .  .  .  .  .  .  Index: *ast.BasicLit {
    95  .  .  .  .  .  .  .  .  .  ValuePos: cmd/ast/main.go:11:22
    96  .  .  .  .  .  .  .  .  .  Kind: INT
    97  .  .  .  .  .  .  .  .  .  Value: "1"
    98  .  .  .  .  .  .  .  .  }
    99  .  .  .  .  .  .  .  .  Rbrack: cmd/ast/main.go:11:23
   100  .  .  .  .  .  .  .  }
   101  .  .  .  .  .  .  }
   102  .  .  .  .  .  }
   103  .  .  .  .  .  1: *ast.AssignStmt {
   104  .  .  .  .  .  .  Lhs: []ast.Expr (len = 1) {
   105  .  .  .  .  .  .  .  0: *ast.Ident {
   106  .  .  .  .  .  .  .  .  NamePos: cmd/ast/main.go:12:2
   107  .  .  .  .  .  .  .  .  Name: "fset"
   108  .  .  .  .  .  .  .  .  Obj: *ast.Object {
   109  .  .  .  .  .  .  .  .  .  Kind: var
   110  .  .  .  .  .  .  .  .  .  Name: "fset"
   111  .  .  .  .  .  .  .  .  .  Decl: *(obj @ 103)
   112  .  .  .  .  .  .  .  .  }
   113  .  .  .  .  .  .  .  }
   114  .  .  .  .  .  .  }
   115  .  .  .  .  .  .  TokPos: cmd/ast/main.go:12:7
   116  .  .  .  .  .  .  Tok: :=
   117  .  .  .  .  .  .  Rhs: []ast.Expr (len = 1) {
   118  .  .  .  .  .  .  .  0: *ast.CallExpr {
   119  .  .  .  .  .  .  .  .  Fun: *ast.SelectorExpr {
   120  .  .  .  .  .  .  .  .  .  X: *ast.Ident {
   121  .  .  .  .  .  .  .  .  .  .  NamePos: cmd/ast/main.go:12:10
   122  .  .  .  .  .  .  .  .  .  .  Name: "token"
   123  .  .  .  .  .  .  .  .  .  }
   124  .  .  .  .  .  .  .  .  .  Sel: *ast.Ident {
   125  .  .  .  .  .  .  .  .  .  .  NamePos: cmd/ast/main.go:12:16
   126  .  .  .  .  .  .  .  .  .  .  Name: "NewFileSet"
   127  .  .  .  .  .  .  .  .  .  }
   128  .  .  .  .  .  .  .  .  }
   129  .  .  .  .  .  .  .  .  Lparen: cmd/ast/main.go:12:26
   130  .  .  .  .  .  .  .  .  Ellipsis: -
   131  .  .  .  .  .  .  .  .  Rparen: cmd/ast/main.go:12:27
   132  .  .  .  .  .  .  .  }
   133  .  .  .  .  .  .  }
   134  .  .  .  .  .  }
   135  .  .  .  .  .  2: *ast.AssignStmt {
   136  .  .  .  .  .  .  Lhs: []ast.Expr (len = 2) {
   137  .  .  .  .  .  .  .  0: *ast.Ident {
   138  .  .  .  .  .  .  .  .  NamePos: cmd/ast/main.go:13:2
   139  .  .  .  .  .  .  .  .  Name: "f"
   140  .  .  .  .  .  .  .  .  Obj: *ast.Object {
   141  .  .  .  .  .  .  .  .  .  Kind: var
   142  .  .  .  .  .  .  .  .  .  Name: "f"
   143  .  .  .  .  .  .  .  .  .  Decl: *(obj @ 135)
   144  .  .  .  .  .  .  .  .  }
   145  .  .  .  .  .  .  .  }
   146  .  .  .  .  .  .  .  1: *ast.Ident {
   147  .  .  .  .  .  .  .  .  NamePos: cmd/ast/main.go:13:5
   148  .  .  .  .  .  .  .  .  Name: "_"
   149  .  .  .  .  .  .  .  .  Obj: *ast.Object {
   150  .  .  .  .  .  .  .  .  .  Kind: var
   151  .  .  .  .  .  .  .  .  .  Name: "_"
   152  .  .  .  .  .  .  .  .  .  Decl: *(obj @ 135)
   153  .  .  .  .  .  .  .  .  }
   154  .  .  .  .  .  .  .  }
   155  .  .  .  .  .  .  }
   156  .  .  .  .  .  .  TokPos: cmd/ast/main.go:13:7
   157  .  .  .  .  .  .  Tok: :=
   158  .  .  .  .  .  .  Rhs: []ast.Expr (len = 1) {
   159  .  .  .  .  .  .  .  0: *ast.CallExpr {
   160  .  .  .  .  .  .  .  .  Fun: *ast.SelectorExpr {
   161  .  .  .  .  .  .  .  .  .  X: *ast.Ident {
   162  .  .  .  .  .  .  .  .  .  .  NamePos: cmd/ast/main.go:13:10
   163  .  .  .  .  .  .  .  .  .  .  Name: "parser"
   164  .  .  .  .  .  .  .  .  .  }
   165  .  .  .  .  .  .  .  .  .  Sel: *ast.Ident {
   166  .  .  .  .  .  .  .  .  .  .  NamePos: cmd/ast/main.go:13:17
   167  .  .  .  .  .  .  .  .  .  .  Name: "ParseFile"
   168  .  .  .  .  .  .  .  .  .  }
   169  .  .  .  .  .  .  .  .  }
   170  .  .  .  .  .  .  .  .  Lparen: cmd/ast/main.go:13:26
   171  .  .  .  .  .  .  .  .  Args: []ast.Expr (len = 4) {
   172  .  .  .  .  .  .  .  .  .  0: *ast.Ident {
   173  .  .  .  .  .  .  .  .  .  .  NamePos: cmd/ast/main.go:13:27
   174  .  .  .  .  .  .  .  .  .  .  Name: "fset"
   175  .  .  .  .  .  .  .  .  .  .  Obj: *(obj @ 108)
   176  .  .  .  .  .  .  .  .  .  }
   177  .  .  .  .  .  .  .  .  .  1: *ast.Ident {
   178  .  .  .  .  .  .  .  .  .  .  NamePos: cmd/ast/main.go:13:33
   179  .  .  .  .  .  .  .  .  .  .  Name: "filepath"
   180  .  .  .  .  .  .  .  .  .  .  Obj: *(obj @ 72)
   181  .  .  .  .  .  .  .  .  .  }
   182  .  .  .  .  .  .  .  .  .  2: *ast.Ident {
   183  .  .  .  .  .  .  .  .  .  .  NamePos: cmd/ast/main.go:13:43
   184  .  .  .  .  .  .  .  .  .  .  Name: "nil"
   185  .  .  .  .  .  .  .  .  .  }
   186  .  .  .  .  .  .  .  .  .  3: *ast.BasicLit {
   187  .  .  .  .  .  .  .  .  .  .  ValuePos: cmd/ast/main.go:13:48
   188  .  .  .  .  .  .  .  .  .  .  Kind: INT
   189  .  .  .  .  .  .  .  .  .  .  Value: "0"
   190  .  .  .  .  .  .  .  .  .  }
   191  .  .  .  .  .  .  .  .  }
   192  .  .  .  .  .  .  .  .  Ellipsis: -
   193  .  .  .  .  .  .  .  .  Rparen: cmd/ast/main.go:13:49
   194  .  .  .  .  .  .  .  }
   195  .  .  .  .  .  .  }
   196  .  .  .  .  .  }
   197  .  .  .  .  .  3: *ast.ExprStmt {
   198  .  .  .  .  .  .  X: *ast.CallExpr {
   199  .  .  .  .  .  .  .  Fun: *ast.SelectorExpr {
   200  .  .  .  .  .  .  .  .  X: *ast.Ident {
   201  .  .  .  .  .  .  .  .  .  NamePos: cmd/ast/main.go:14:2
   202  .  .  .  .  .  .  .  .  .  Name: "ast"
   203  .  .  .  .  .  .  .  .  }
   204  .  .  .  .  .  .  .  .  Sel: *ast.Ident {
   205  .  .  .  .  .  .  .  .  .  NamePos: cmd/ast/main.go:14:6
   206  .  .  .  .  .  .  .  .  .  Name: "Print"
   207  .  .  .  .  .  .  .  .  }
   208  .  .  .  .  .  .  .  }
   209  .  .  .  .  .  .  .  Lparen: cmd/ast/main.go:14:11
   210  .  .  .  .  .  .  .  Args: []ast.Expr (len = 2) {
   211  .  .  .  .  .  .  .  .  0: *ast.Ident {
   212  .  .  .  .  .  .  .  .  .  NamePos: cmd/ast/main.go:14:12
   213  .  .  .  .  .  .  .  .  .  Name: "fset"
   214  .  .  .  .  .  .  .  .  .  Obj: *(obj @ 108)
   215  .  .  .  .  .  .  .  .  }
   216  .  .  .  .  .  .  .  .  1: *ast.Ident {
   217  .  .  .  .  .  .  .  .  .  NamePos: cmd/ast/main.go:14:18
   218  .  .  .  .  .  .  .  .  .  Name: "f"
   219  .  .  .  .  .  .  .  .  .  Obj: *(obj @ 140)
   220  .  .  .  .  .  .  .  .  }
   221  .  .  .  .  .  .  .  }
   222  .  .  .  .  .  .  .  Ellipsis: -
   223  .  .  .  .  .  .  .  Rparen: cmd/ast/main.go:14:19
   224  .  .  .  .  .  .  }
   225  .  .  .  .  .  }
   226  .  .  .  .  }
   227  .  .  .  .  Rbrace: cmd/ast/main.go:15:1
   228  .  .  .  }
   229  .  .  }
   230  .  }
   231  .  Scope: *ast.Scope {
   232  .  .  Objects: map[string]*ast.Object (len = 1) {
   233  .  .  .  "main": *(obj @ 51)
   234  .  .  }
   235  .  }
   236  .  Imports: []*ast.ImportSpec (len = 4) {
   237  .  .  0: *(obj @ 12)
   238  .  .  1: *(obj @ 20)
   239  .  .  2: *(obj @ 28)
   240  .  .  3: *(obj @ 36)
   241  .  }
   242  .  Unresolved: []*ast.Ident (len = 5) {
   243  .  .  0: *(obj @ 84)
   244  .  .  1: *(obj @ 120)
   245  .  .  2: *(obj @ 161)
   246  .  .  3: *(obj @ 182)
   247  .  .  4: *(obj @ 200)
   248  .  }
   249  }

```

### ast.Fileノードを愚直に辿るとどうなるか

ast.Print()の結果を見ながら、愚直にast.File構造体を辿っていくと、あなたのエンジニア人生で見た事がない深さのネストコードが拝めます。そして、この実装方法は間違えています。

<blockquote class="twitter-tweet"><p dir="ltr" lang="ja">エンジニア人生で最も深いネストを書いてしまった。<br><br>golangのgo/ast、どうやればネスト浅く書けるんだ？明日見たら理解できないと思う。 <a href="https://t.co/TqhzxVPLAo">pic.twitter.com/TqhzxVPLAo</a></p>— Nao31 (@ARC_AED) <a href="https://twitter.com/ARC_AED/status/1491759943997095937?ref_src=twsrc%5Etfw">February 10, 2022</a></blockquote>

愚直にast.File構造体を辿っても、パースしたファイルによってast.Fileの内容は変わります。そのため、愚直に書いたコードは汎用性がありません。

通常は、ast.Inspect()を使用してast.Fileの内容を探索します。ast.Inspect()は、探しているノード位置（型）をswitch-caseに記載しておくと、その位置で探索が止まります（case文に入ります）。ここでの型はプリミティブ型ではなく、go/ast内で定義されている型（ASTを表現するための型）です。

```
func main() {
	// 解析対象ソースコード
	src := `
package p
const c = 1.0
var X = f(3.14)*2 + c
`
	// srcのASTを作成
	fset := token.NewFileSet() // positions are relative to fset
	f, err := parser.ParseFile(fset, "src.go", src, 0)
	if err != nil {
		panic(err)
	}

	// ASTを再帰的に探索する。case部には、停止したいノード位置の型を書く
	ast.Inspect(f, func(n ast.Node) bool {
		var s string
		switch x := n.(type) {
		case *ast.BasicLit:
			s = x.Value
		case *ast.Ident:
			s = x.Name
		}
		if s != "" {
			fmt.Printf("%s:\t%s\n", fset.Position(n.Pos()), s)
		}
		return true
	})

}
```

以下、「愚直にコードを書いた場合」と「ast.Inspect()を使った場合」の例です。後者はもっとネストを浅く書けますが、この時の実力では以下が限界でした。

<blockquote class="twitter-tweet"><p dir="ltr" lang="ja">ASTを再帰的に探索する処理を試したら、ネストがかなり浅くなった。 <a href="https://t.co/PWYdH9lnFk">pic.twitter.com/PWYdH9lnFk</a></p>— Nao31 (@ARC_AED) <a href="https://twitter.com/ARC_AED/status/1491769878151577602?ref_src=twsrc%5Etfw">February 10, 2022</a></blockquote>

### より詳細なAST情報が欲しい方への参考文献（日本語）

- [GoのAST全部見る](https://monpoke1.hatenablog.com/entry/2018/12/16/110943#Spec)
- [GoのためのGo](https://motemen.github.io/go-for-go-book/)
- [ASTを取得する方法を調べる](https://tenntenn.dev/ja/posts/qiita-13340f2845316532b55a/)

### goavlの設計

[goavl](https://github.com/nao1215/goavl)は限定的な用途のツールと言っても差し支えないので、簡単な作りにしました。より正確に言うと、既存のLinterのプラグインとして開発してもマージされない可能性が高かったので、自分で管理できる範囲のLinterとして設計しました。

goavlは、以下の2つを機能として持ちます。

- Task（チェック項目）のランナー
- ASTを用いたTask（チェック項目）

Taskのランナーは、非常にシンプルな作りです。まず、Task構造体の中に関数ポインタ（Check）を持ち、このポインタに文法チェック関数を登録します。ランナーは関数ポインタを順番にコールするだけです。優先度も何もありません。

```
type check func(filepath string)

type Task struct {
	Name string
	Check check // 関数ポインタ：一つの観点で文法チェックを行う
}

func Run(files []string) {
	// ここで複数のタスクがセットされる
	tasks := task.Setup()

	// goa-designファイルのみを抽出し、Task.Checkを順次実行する
	for _, f := range fileutils.ExtractDesignPackageFile(files) {
		for _, v := range tasks {
			v.Check(f)
		}
	}
}

```

ASTを用いたTaskは、例えば「命名規則が正しいか」といった観点（1個単位）で作ります。多くのLinterがこの方針を採用していると思われます。今回実装したTaskは、goa-designに関する知識がある方でないと理解できないので、説明を省略します。

### goavlの使い方

インストール方法は、[README（日本語）](https://github.com/nao1215/goavl)を参照してください。goavlは、引数指定が無い場合はカレントディレクトリ以下のgoa-designファイルをチェックし、--fileオプションをつけた場合は任意のgoa-designファイルをチェックします。

以下、実行例です。

```
$ goavl
[WARN] test/sample/action.go:7    Resource("operandsNG") is not snake case ('operands_ng')
[WARN] test/sample/action.go:9    Action("add-ng") is not snake case ('add_ng')
[WARN] test/sample/action.go:11   Not exist Description() in Action().
[WARN] test/sample/attribute.go:17   Not exist Example() in Attribute().
[WARN] test/sample/attribute.go:27   NoExample() is not user(client) friendly
[WARN] test/sample/attribute.go:9    Resource() has Attribute(). Attribute() can be used in View(), Type(), Attribute(), Attributes(), MediaType()
[WARN] test/sample/description.go:11   Not exist Example() in Attribute().
[WARN] test/sample/goa.go:40   Attributes() has View(). View() can be used in MediaType() or Response()
[WARN] test/sample/goa.go:46   Type() has View(). View() can be used in MediaType() or Response()
[WARN] test/sample/resource.go:11   Resource("operands-Ng_case") is not snake case ('operands_ng_case')
[WARN] test/sample/routing.go:12   Routing(DELETE("delete_ng/:left-ng/:right")) is not chain case ('delete-ng/:left-ng/:right')
[WARN] test/sample/routing.go:15   Routing(POST("/postNg/abc.php")) is not chain case ('/post-ng/abc.php')
[WARN] test/sample/view.go:12   Attributes() has View(). View() can be used in MediaType() or Response()
[WARN] test/sample/view.go:18   Type() has View(). View() can be used in MediaType() or Response()

```

現状は、「命名規則チェック」や「関数の使用条件チェック」、「APIや属性の説明が書かれているかのチェック」を行います。指摘箇所（ファイル、行数）と直し方を併記しているため、goavlを使えばgoa-designファイルの修正が容易にできる筈です。

### 最後に：goavlの由来

初期名称は"goalinter-v1"でした。

末尾の"v1"がlinterのVersion 1に見えるため、"goav1linter"に改名。その後、"1"と"l"が似ていたため、それらを統合する事を思いつきました。

その結果、 "goavl"が誕生しました。goavlは「ゴアブル」と呼んでいます。
