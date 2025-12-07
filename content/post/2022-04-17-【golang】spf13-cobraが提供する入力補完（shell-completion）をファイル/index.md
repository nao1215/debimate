---
title: "【Golang】spf13/cobraが提供する入力補完（shell completion）をファイル形式でインストールする方法【bash, zsh, fish】"
type: post
date: 2022-04-17
categories:
  - "linux"
tags:
  - "cli"
  - "golang"
  - "linux"
cover:
  image: "images/snake-gc4e761055_640.jpg"
  alt: "【Golang】spf13/cobraが提供する入力補完（shell completion）をファイル形式でインストールする方法【bash, zsh, fish】"
  hidden: false
---

### 前書き：spf13/cobraのシェル補完は便利

本記事は、[spf13/cobra](https://github.com/spf13/cobra)が提供する「シェル補完（文字列）」をファイルとしてシステムにインストールする例を紹介します。今回の例を実践すると、cobraを用いたCLIコマンドでシェル補完が有効になります。ここでのシェル補完とは、ターミナルでコマンド入力中に\[TAB\]キーを押すと、自動で単語を補完する機能です。

対象シェルは、bash、zsh、fishです。PowerShellは、私が詳しくないので除外します。

cobraは、Golang用のCLIコマンド作成補助ライブラリです。代表的な機能は、CLIコマンド実行時にオプション／サブコマンドが指定されたかどうかを判定する機能です。cobraを使用した場合、自動的にcompletionサブコマンドが追加され（例：以下に示すposixerコマンドのhelp参照）、このサブコマンドはシェル補完用の文字列を出力します。

```
$ posixer help
posixer command provides information about the Posix-Shell

Usage:
  posixer [command]

Available Commands:
  completion  Generate the autocompletion script for the specified shell　// ☆自動で追加されるサブコマンド
```

```
$ posixer completion bash　※ bashのshell completionの出力
# bash completion V2 for posixer                              -*- shell-script -*-

__posixer_debug()
{
    if [[ -n ${BASH_COMP_DEBUG_FILE:-} ]]; then
        echo "$*" >> "${BASH_COMP_DEBUG_FILE}"
    fi
}

# Macs have bash3 for which the bash-completion package doesn't include
# _init_completion. This is a minimal version of that function.
__posixer_init_completion()
{
    COMPREPLY=()
    _get_comp_words_by_ref "$@" cur prev words cword
}

// 省略

```

自動追加されるcompletionサブコマンドのイケてない部分は、出力された文字列をどのように扱えば良いのかがサッパリ分からないことです。恐らく、「ユーザーがシェル補完（文字列）をファイル化して、システムにインストールしてください」が期待値だと考えています。

しかし、ユーザーにコマンドを使ってもらう観点からは、ユーザーに手作業を強いるよりも、「CLIコマンドが自動でシェル補完ファイルをシステムにインストール」した方が利便性が高いです。

そこで、本記事では「シェル補完ファイルのインストール先」を示し、シェル補完ファイルインストールの実装例を示します。

---


### 検証環境

Ubuntu21.10、golang version 1.18、spf13/cobra v1.4.0で検証しました。

```
$ neofetch 
           ./oydmMMMMMMmdyo/.
        :smMMMMMMMMMMMhs+:++yhs:           nao@nao 
     `omMMMMMMMMMMMN+`        `odo`        ------- 
    /NMMMMMMMMMMMMN- `sN/       OS: Ubuntu Budgie 21.10 x86_64 
  `hMMMMmhhmMMMMMMh               sMh`     Host: B450 I AORUS PRO WIFI 
 .mMmo- /yMMMMm`              `MMm.    Kernel: 5.13.0-39-generic 
 mN/       yMMMMMMMd- MMMm    Uptime: 3 hours, 34 mins 
oN- oMMMMMMMMMms+//+o+:    :MMMMo   Packages: 3667 (dpkg), 18 (snap) 
m/          +NMMMMMMMMMMMMMMMMm. :NMMMMm   Shell: bash 5.1.8 
M`           .NMMMMMMMMMMMMMMMNodMMMMMMM   Resolution: 2560x1080, 1920x1080 
M- sMMMMMMMMMMMMMMMMMMMMMMMMM   DE: Budgie 10.5.3 
mm`           mMMMMMMMMMNdhhdNMMMMMMMMMm   WM: Mutter(Budgie) 
oMm/        .dMMMMMMMMh:      :dMMMMMMMo   Theme: Yaru-dark [GTK2/3] 
 mMMNyo/:/sdMMMMMMMMM+          sMMMMMm    Icons: ubuntu-mono-dark [GTK2/3] 
 .mMMMMMMMMMMMMMMMMMs           `NMMMm.    Terminal: vscode 
  `hMMMMMMMMMMM.oo+.            `MMMh`     CPU: AMD Ryzen 5 3400G (8) @ 3.700GHz 
    /NMMMMMMMMMo                sMN/       GPU: AMD ATI 09:00.0 Picasso 
     `omMMMMMMMMy.            :dmo`        Memory: 6883MiB / 30032MiB 
        :smMMMMMMMh+-`   `.:ohs:
           ./oydmMMMMMMdhyo/.                                      
                                                                   

```

---


### シェル補完ファイルの出力先

シェル補完ファイルは、シェル毎に格納先が異なります。格納先は大別して、「OS内の全ユーザーが参照できる場所（例：/etc以下 や /usr/local/share以下）」と「特定のユーザーのみが参照できる場所（例：$HOME以下）」の2種類があります。

今回の例では、一般ユーザーがCLIコマンドを実行した場合を想定しているため、シェル補完ファイルをユーザーホームディレクトリ以下にインストールします。全ユーザー向けにインストールしたい場合は、以下に示す参考情報（リンク）を調べてください。以下、特定ユーザー向けのインストール先です。

- **bashの場合：**$HOME/.bash\_completion
    - 複数のコマンドの入力補完情報が格納されるファイルのため、編集時に注意が必要
    - [参考情報](https://github.com/scop/bash-completion/blob/6009de8534cd24b71d0bfda479823abcc640e4b1/doc/bash_completion.txt#L13)
- **fishの場合  ：**$HOME/.config/fish/completions/${cmd\_name}.fish
    - [参考情報](https://fishshell.com/docs/current/completions.html)
- **zshの場合   ：**$HOME/.zsh/completion/\_${cmd\_name}
    - [参考情報](https://github.com/zsh-users/zsh-completions/blob/master/zsh-completions-howto.org)

デフォルトのzshでは、シェル補完ファイル格納先がユーザーホームディレクトリ以下に存在しません。そこで、zshがシェル補完ファイルの格納先を$fpathで管理している事を利用します。具体的には、.zshrcを編集して、$fpathに"$HOME/.zsh/completion"を追加します。

---


### シェル補完ファイル作成の流れ

シェル補完ファイルの作成は、CLIコマンドの起動直後（cmd/root.go Execute()内）で実行します。詳細な処理は後述しますが、大まかな流れは以下のとおりです。

- completionサブコマンドをdisable（使用不可）に変更
    - ユーザーが明示的にcompletionサブコマンドを使用しなくなるため

- シェル補完ファイルを必要であれば生成する関数を実行（詳細を後述）
    - シェル補完ファイルが既に存在するか
    - 「cobraが生成するシェル補完の内容」と「システムに存在するシェル補完ファイル内容」が一致するか
    - 上記2点を満たさない場合は、シェル補完ファイルを生成

- cobraのrootコマンドを実行

```
// root.go内
func Execute() {
	// completion サブコマンドを使用不可に変更
	rootCmd.CompletionOptions.DisableDefaultCmd = true
	
	// シェル補完ファイルを必要であれば生成する関数（後述）
	deployShellCompletionFileIfNeeded(rootCmd)

	if err := rootCmd.Execute(); err != nil {
		exitError(err)
	}
}                                                    

```

---


### シェル補完ファイル作成の実例

シェル補完ファイルの作成は、最も面倒なzsh用シェル補完ファイル作成の例だけ示します。bash、fish用の作成例を知りたい方は、[GitHub上に実例をアップしているのでそちら](https://github.com/nao1215/gup/blob/main/cmd/root.go)をご確認ください。

まずは、シェル補完ファイル作成の実処理を説明する前に、ヘルパー関数（下請け的な関数）を示します。ここでの重要な処理は、"isSameZshCompletionContent()"内で「cobraが生成するシェル補完」と「システムに存在するシェル補完ファイルの内容」を比較する部分です。ここでの比較が一致しなければ、シェル補完ファイルの作成が必要と判断します。

```
// root.go内

// deployShellCompletionFileIfNeeded 必要であれば、シェル補完を生成
func deployShellCompletionFileIfNeeded(cmd *cobra.Command) {
	// 本来であれば、bash, fish用の処理をココに書きます。
	makeZshCompletionFileIfNeeded(cmd)
}

// zshCompletionFilePath zsh-completionファイルのパスを返します
func zshCompletionFilePath() string {
	return filepath.Join(os.Getenv("HOME"), ".zsh", "completion", "_sample_command")
}

// zshrcPath .zshrcのパスを返します
func zshrcPath() string {
	return filepath.Join(os.Getenv("HOME"), ".zshrc")
}

// isFile pathがファイルかどうかを返します
func isFile(path string) bool {
	stat, err := os.Stat(path)
	return (err == nil) && (!stat.IsDir())
}

// isSameZshCompletionContent zsh用のシェル補完ファイルの内容が同一かを返します
func isSameZshCompletionContent(cmd *cobra.Command) bool {
	// シェル補完ファイルが存在するかどうかのチェック
	path := zshCompletionFilePath()
	if !isFile(path) {
		return false
	}

	// cobraからシェル補完（バイト）を取得
	currentZshCompletion := new(bytes.Buffer)
	if err := cmd.GenZshCompletion(currentZshCompletion); err != nil {
		return false
	}

	// システムに存在するシェル補完ファイルを読み込み
	zshCompletionInLocal, err := os.ReadFile(path)
	if err != nil {
		return false
	}

	// 「最新のシェル補完（cobra提供）」と「システムに存在するシェル補完ファイルの内容」を
	// 比較する。
	if bytes.Compare(currentZshCompletion.Bytes(), zshCompletionInLocal) != 0 {
		return false
	}
	return true
}
                                      

```

次に、シェル補完ファイルの作成関数を示します。処理を以下の順で実施します。

- シェル補完ファイルが既に最新の場合は、シェル補完ファイルの作成処理をスキップ（①）
- シェル補完ファイルを作成する前に、格納先ディレクトリを作成（②）
- cobraが提供する関数を用いて、シェル補完ファイルを作成（③）
- 必要であれば、.zshrcにシェル補完ファイルの格納先情報を追記（④）

```
// root.go内
// makeZshCompletionFileIfNeeded 必要であれば、zsh用のシェル補完ファイルを作成する
func makeZshCompletionFileIfNeeded(cmd *cobra.Command) {
	// ①既にシステムにシェル補完ファイルが最新の状態で存在する場合、
	// 　シェル補完ファイルを作成しない
	if isSameZshCompletionContent(cmd) {
		return
	}

	// ②シェル補完ファイル格納先ディレクトリを作成する
	path := zshCompletionFilePath()
	if err := os.MkdirAll(filepath.Dir(path), 0775); err != nil {
		fmt.Println(fmt.Errorf("can not create zsh-completion file: %w", err))
		return
	}

	// ③cobraが提供する関数でシェル補完ファイルを作成する。
	if err := cmd.GenZshCompletionFile(path); err != nil {
		fmt.Println(fmt.Errorf("can not create zsh-completion file: %w", err))
		return
	}
	fmt.Println("create zsh-completion file: " + path)

	// ④ .zshrcにシェル補完ファイルの格納先情報を追記
	appendFpathIfNeeded()
}

// appendFpathIfNeeded デフォルトのzshはユーザーホームディレクトリ以下に、
// シェル補完ファイルの格納先ディレクトリを持ちません。
// そのため、シェル補完ファイル格納先を$fpathに登録します。
func appendFpathIfNeeded() {
	// fpathに新しいパスを登録した後、compinitで再読込しなければ、
	// シェル補完が有効化されません。
	const zshFpath = `
# setting for gup command (auto generate)
fpath=(~/.zsh/completion $fpath)
autoload -Uz compinit && compinit -i
`

	// .zshrcが存在しない場合は、.zshrcを新規作成する
	zshrcPath := zshrcPath()
	if !file.IsFile(zshrcPath) {
		fp, err := os.OpenFile(zshrcPath, os.O_RDWR|os.O_CREATE, 0664)
		if err != nil {
			fmt.Println(fmt.Errorf("can not open .zshrc: %w", err))
			return
		}
		defer fp.Close()

		if _, err := fp.WriteString(zshFpath); err != nil {
			fmt.Println(fmt.Errorf("can not add zsh $fpath in .zshrc: %w", err))
		}
		return
	}

	// .zshrc内に、既に"fpath=(~/.zsh/completion $fpath)"が含まれている場合は、
	// .zshrcに対して追記処理を行わない
	zshrc, err := os.ReadFile(zshrcPath)
	if err != nil {
		fmt.Println(fmt.Errorf("can not read .zshrc: %w", err))
		return
	}

	if strings.Contains(string(zshrc), zshFpath) {
		return
	}

	// fpathの追記処理
	fp, err := os.OpenFile(zshrcPath, os.O_RDWR|os.O_APPEND, 0664)
	if err != nil {
		fmt.Println(fmt.Errorf("can not add zsh $fpath in .zshrc: %w", err))
		return
	}
	defer fp.Close()

	if _, err := fp.WriteString(zshFpath); err != nil {
		fmt.Println(fmt.Errorf("can not add zsh $fpath in .zshrc: %w", err))
		return
	}
}

```

---


### 最後に

cobraがシェル補完ファイル作成関数を提供している事から、cobra開発者は「completionサブコマンドを開発者が作り込む事」を期待している気がします。個人的な意見としては、作り込む必要のあるサブコマンドをデフォルトで有効にしない方が好ましいのでは、と思ってしまいます。

今回の例では、ユーザーの負担を減らすために自動でシェル補完ファイル作成や.zshrc追記を実施しています。しかし、ユーザーによっては「勝手にファイルを追加・編集しないで欲しい」という方も居る筈です。そのため、本記事の例は参考実装程度に留めてください。
