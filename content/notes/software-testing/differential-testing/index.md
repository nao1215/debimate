---
title: "Differential Testing - 同じ入力を別の実装に渡して出力を比べる"
date: 2026-11-12
draft: false
series: ["技術ノート", "Software Testing"]
tags: ["software-testing", "differential-testing", "coreutils", "uutils", "sqlite", "postgresql"]
weight: 2
wrapTables: true
topics: ["Test Oracles"]
---

Differential Testing（差分テスト）は、同じ仕事をする 2 つ以上の実装に同じ入力を渡し、出力が一致するかを比べるテスト手法です。正解を人が書く代わりに、もう 1 つの実装の出力を比較の基準にします。名前は、[McKeeman 氏の 1998 年の論文](https://web.archive.org/web/20061031200115/http://www.hpl.hp.com/hpjournal/dtj/vol10num1/vol10num1art9.pdf)から広まりました。

同じ仕事をする実装が 2 つある場面は、思ったより身近にあります。Ubuntu 25.10 では、`ls` や `sort` などの基本コマンドを集めた coreutils の既定が、C で書かれた [GNU coreutils](https://www.gnu.org/software/coreutils/) から Rust で書き直した [uutils coreutils](https://github.com/uutils/coreutils) に切り替わりました。経緯は [Ubuntu の告知](https://discourse.ubuntu.com/t/an-update-on-rust-coreutils/80773)にあります。

著者の Ubuntu 26.04 には両方が入っていて、`ls` は uutils、`gnuls` は GNU です。シェルスクリプトから見ると、ある日を境に同じ名前のコマンドの中身が入れ替わったことになります。

著者はこの 2 つに、同じ 32 ケースの呼び出しを渡して比べました。26 ケースは出力も終了コードも一致し、5 ケースで違いました。違った 5 ケースのうち 4 ケースは、書き込み先のディスクが一杯の時の振る舞いです。`/dev/full` は、書き込むと必ず「空き容量が無い」エラーを返す特殊なファイルで、ディスクが一杯の状況を再現できます。

{{< figure src="images/full_disk.webp" alt="ディスクが一杯の時の ls > list.txt。GNU 9.7 は書き込みが失敗すると stderr に ls: write error: No space left を出し、終了コード 2 で終わるので、スクリプトは失敗に気付いて止まる。uutils 0.8.0 は書き込みが失敗しても stderr に何も出さず、終了コード 0 で終わるので、スクリプトは成功とみなして欠けた list.txt を使う" caption="ディスクが一杯の時、uutils 0.8.0 の ls は失敗を報告しない" align="center" >}}

uutils の `ls` は、書き込みに失敗しても何も表示せずに 0 で終わりました。`ls > list.txt` を実行したスクリプトは、ディスクが一杯でも成功したと判断して、中身の欠けたファイルを次の処理に渡します。残りの差は後の節で扱います。

どちらの実装にも「ディスクが一杯の時の正解」は書いてありません。2 つを並べて比べたことで、片方だけが失敗を報告していないと分かります。

<br>

本記事では、手元の 3 つの実験で、2 つの実装を比べるテストの考え方を説明します。扱う疑問は以下の通りです。

- 正解が分からない処理で、比較の相手はどこにあるのか。
- 出力の何を比べ、何を比べないのか。
- 差が出た時、どちらが正しいと決めるのか。
- 比べても見つからないものは何か。

---

### 正解の代わりに別の実装を使う

[Metamorphic Testing のノート](/notes/software-testing/metamorphic-testing/)では、入力ごとの正解（期待値）を書けない処理を扱いました。正解を書けない問題は、テストオラクル問題と呼ばれます。

Metamorphic Testing は、1 つの実装に入力を変えて 2 回渡し、2 つの出力が満たすはずの関係を検証する方法でした。例えば「2 つのファイルを 1 回で `wc` に渡した結果は、1 ファイルずつ渡してつないだ結果と等しい」という関係です。Differential Testing は、入力を 1 つに固定し、実装の方を 2 つにします。

{{< figure src="images/concept.webp" alt="左は Metamorphic Testing。入力 x と変えた入力 x′ を 1 つの実装 P に渡し、P(x) と P(x′) が関係を満たすかを見る。右は Differential Testing。1 つの入力 x を実装 A と実装 B に渡し、A(x) と B(x) が一致するかを見る" caption="Metamorphic Testing は入力を 2 つにし、Differential Testing は実装を 2 つにする" align="center" >}}

Differential Testing で確認する関係は常に「一致する」なので、処理ごとに関係を考える必要がありません。その代わり、同じ仕事をする別の実装が必要です。

この手法で有名な成果に、C コンパイラのテストがあります。[Csmith](https://github.com/csmith-project/csmith) は、ランダムな C のプログラムを生成し、複数のコンパイラでビルドして実行し、出力が一致するかを比べるツールです。[開発者の論文](https://www-old.cs.utah.edu/~regehr/papers/pldi11-preprint.pdf)によると、3 年間で GCC や LLVM などに 325 件を超える未知のバグを報告しました。

Csmith は、C の仕様で動作が未定義になるプログラムを生成しないように作られています。未定義の動作では、コンパイラごとに出力が違っても誤りではないので、差がバグを意味しなくなるためです。

<br>

#### 比較の相手の見つけ方

Csmith のように別の製品を用意できる場面は限られます。しかし、比較の相手は別の製品でなくても構いません。

| 比較の相手 | 例 |
|---|---|
| 同じ仕様の別の実装 | GNU coreutils と uutils、GCC と Clang |
| 同じプログラムの古いバージョン | 書き直し前のコード、リリース済みのバイナリ |
| 同じプログラムの別の経路 | パイプで渡す場合と、ファイル名で渡す場合 |
| 対象が自分で出す別の形式 | コマンドの表と JSON 出力（実験 2） |
| 対象が準拠すると約束した製品 | PostgreSQL 互換のライブラリと PostgreSQL（実験 3） |

書き直しや移行の作業では、古い実装がそのまま比較の相手になります。古い実装を消す前に、両方へ同じ入力を渡して比べておくと、書き直しで変わった振る舞いを一覧にできます。

---

### 実験 1: GNU coreutils と uutils

冒頭の結果は、以下のスクリプトで取りました。`/usr/bin/gnu<コマンド名>` が GNU、`/usr/lib/cargo/bin/coreutils/<コマンド名>` が uutils の実体です。全体は [lab の exp1_gnu_uutils.py](https://github.com/nao1215/debimate/blob/main/content/notes/software-testing/differential-testing/lab/exp1_gnu_uutils.py) にあります。以下は抜粋で、`make_fixture` は作業ディレクトリに入力のファイル（`data.txt` など）を作る関数です。

```python
GNU = "/usr/bin/gnu{}"
UUTILS = "/usr/lib/cargo/bin/coreutils/{}"


def run(impl, argv, redirect):
    exe = (GNU if impl == "gnu" else UUTILS).format(argv[0])
    env = {"LC_ALL": "C", "PATH": "/usr/bin:/bin", "TZ": "UTC"}
    with tempfile.TemporaryDirectory() as d:
        make_fixture(d)
        stdin = subprocess.DEVNULL
        out = subprocess.PIPE
        if redirect == "full":
            out = open("/dev/full", "w")
        elif redirect:
            stdin = open(os.path.join(d, redirect))
        p = subprocess.run(argv, executable=exe, cwd=d, env=env,
                           stdin=stdin, stdout=out, stderr=subprocess.PIPE)
        return {"stdout": ..., "stderr": ..., "exit": p.returncode}


for name, argv, redirect in CASES:
    g = run("gnu", argv, redirect)
    u = run("uutils", argv, redirect)
    raw = g != u
    normalized = (g["stdout"], g["exit"], bool(g["stderr"])) != \
                 (u["stdout"], u["exit"], bool(u["stderr"]))
```

比べる前に、2 つの実装の条件を揃えています。

- 呼び出し名: `executable` で実体を指定し、`argv[0]` はコマンド名（`ls`）のままにします。`gnuls` という名前で起動すると、エラーメッセージが `gnuls: ...` で始まり、それだけで差になります。
- ロケールと時刻: `LC_ALL=C` と `TZ=UTC` で揃えます。日本語のロケールでは、日付の表記などが実装ごとに違います。
- 入力: ケースごとに作業ディレクトリを作り直し、同じファイルを同じ更新時刻で置きます。

<br>

#### 何を比べるか

全てを比べる `raw` では、32 ケース中 6 ケースに差が出ました。stdout と終了コードを比べ、stderr は「何か表示したか」だけを比べる `normalized` では 5 ケースです。

{{< figure src="images/compare_scope.webp" alt="ls --bogus の結果を項目ごとに比べる図。stdout はどちらも空でそのまま比べて一致。終了コードはどちらも 2 でそのまま比べて一致。stderr は GNU が ls: unrecognized option、uutils が error: unexpected argument で文面が違うが、何か出したかだけを比べるので、どちらも出したとして一致。raw では stderr の文面で差になり、normalized では差にならない" caption="normalized は、stdout と終了コードをそのまま比べ、stderr は何か出したかだけを比べる" align="center" >}}

```text
32 ケース、raw で差 6、normalized で差 5
[ノイズ] ls --bogus
  GNU    exit=2 stdout='' stderr="ls: unrecognized option '--bogus'\nTry 'ls --help' for more information"
  uutils exit=2 stdout='' stderr="error: unexpected argument '--bogus' found\n\n  tip: to pass '--bogus' a"
```

外れた 1 ケースは、知らないオプションを渡した時のエラーメッセージの文面です。uutils は引数の解析に [clap](https://github.com/clap-rs/clap) というライブラリを使っていて、エラーの書式が GNU と違います。文面を読んで処理するスクリプトは稀なので、ここではこの差をノイズとして扱いました。

uutils の開発者も同じ判断をしています。uutils のリポジトリの [fuzz ディレクトリ](https://github.com/uutils/coreutils/tree/main/fuzz)には、ランダムな引数と入力を GNU と uutils の両方に渡して比べるテスト（uufuzz）があります。失敗にするのは stdout と終了コードの差で、stderr の差はほとんどの対象で表示するだけです。

stderr を比べる前に、両方の stderr から `sort:` のような最初の `:` までを落とし、コマンド名の違いが差として出ないようにしています。また、GNU は `LC_ALL=C` で起動します。

何を比べないかを決めないと、差の一覧の大半がノイズになり、本当の差を見落とします。一方で、比べない範囲を広げ過ぎると、本当の差も消えます。stderr を全く比べなければ、`ls` が書き込み失敗を報告しない差は終了コードでしか見えません。

---

### 差が出た時の判断

2 つの実装の出力が違っても、どちらが正しいかは比べただけでは分かりません。実装が 3 つ以上あれば多数決を考えられますが、2 つでは決められません。そこで、両方が従うはずの文書を確認します。coreutils の場合は、UNIX 系 OS のコマンドの振る舞いを定めた標準規格である POSIX と、GNU のマニュアルです。

| 差 | 確認した文書の定め | 判断 |
|---|---|---|
| `ls -l` の `+` | [GNU のマニュアル](https://www.gnu.org/software/coreutils/manual/html_node/What-information-is-listed.html): ACL などがある時に付ける | uutils の誤り |
| `ls`、`printf` の 0 | [POSIX の printf](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/printf.html) と ls: エラーは 0 より大きい値 | uutils の誤り |
| `sort` の 1 | [POSIX の sort](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sort.html): エラーは 1 より大きい値 | uutils の誤り |
| `md5sum` の異常終了 | 書き込みの失敗での異常終了を認める文書は無い | uutils の誤り |
| エラーの文面 | 文面を定めた文書は無い | ノイズ |

ACL（Access Control List）は、ファイルに利用者ごとの権限を付ける仕組みです。実験では、ファイルに名前と値の組を付ける拡張属性（xattr）で、`user.note` という属性を付けました。これはアクセス制御ではないので、GNU の `ls` は `+` を付けません。

uutils 0.8.0 の [has_acl 関数](https://github.com/uutils/coreutils/blob/0.8.0/src/uucore/src/lib/features/fsxattr.rs)は、拡張属性が 1 つでもあれば ACL があるとみなすので、`+` を付けました。

{{< figure src="images/acl.webp" alt="拡張属性 user.note = 1 だけを付けた attr.txt の ls -l。GNU 9.7 は ACL などのアクセス制御があるかを見て、無いので -rw-rw-r-- を出す。uutils 0.8.0 の has_acl は拡張属性が 1 つでもあるかを見て、あるので -rw-rw-r--+ を出す" caption="uutils 0.8.0 は、拡張属性があるだけで + を付ける" align="center" >}}

`ls -l` の 1 列目を正規表現で読んでいるスクリプトは、末尾の `+` で一致しなくなることがあります。

`sort` の終了コード 1 は、POSIX では `-c`（入力が並んでいるかを確認するオプション）で並んでいなかった時の値です。GNU の 2 は「1 より大きい値」に収まり、uutils の 1 は収まりません。`sort -c` で「並んでいるか」を確認するスクリプトは、終了コード 1 を「並んでいない」と読むので、書き込みの失敗を並びの問題と取り違えます。

<br>

`md5sum` の異常終了は、Rust の panic（回復できないエラーで処理を止める仕組み）です。uutils は panic した時にすぐ止まる設定（`panic = "abort"`）で[ビルドされている](https://github.com/uutils/coreutils/blob/0.8.0/Cargo.toml)ので、プロセスは SIGABRT（シグナル 6）で終わり、シェルからは終了コード 134 に見えます。

書き込みの失敗の扱いは、同じ uutils の中でもコマンドごとに違います。[stdio Buffering のノート](/notes/computer-systems/stdout-buffering/)で試した uutils の `cat` は、`/dev/full` への書き込みでエラーを表示して 1 を返しました。

<br>

#### バージョンを上げた時の比較

本記事を書いている途中の 2026-11-12 の朝に、著者の Ubuntu 26.04 では unattended-upgrades（更新を自動で入れる仕組み）が uutils を 0.8.0 から 0.10.0 に上げました。同じスクリプトを実行し直すと、normalized の差は 5 から 4 に減りました。0.8.0 の結果は、docker の `ubuntu:26.04` のイメージで同じスクリプトを実行して残しています。

| ケース | GNU 9.7 | uutils 0.8.0 | uutils 0.10.0 |
|---|---|---|---|
| `ls -l`（xattr 付き） | `-rw-rw-r--` | `-rw-rw-r--+` | `-rw-rw-r--+` |
| `ls`（`/dev/full` へ） | 2、エラーを表示 | 0、何も表示しない | 1、エラーを表示 |
| `printf`（`/dev/full` へ） | 1、エラーを表示 | 0、何も表示しない | 0、何も表示しない |
| `sort`（`/dev/full` へ） | 2、エラーを表示 | 1、エラーを表示 | 1、エラーを表示 |
| `md5sum`（`/dev/full` へ） | 1、エラーを表示 | panic（134） | 1、エラーを表示 |

`md5sum` は panic せずにエラーを表示して 1 を返すようになり、残った差は stderr の文面だけです。`ls` もエラーを表示するようになりましたが、終了コードは GNU の 2 に対して 1 です。

POSIX の ls は「0 より大きい値」としか定めていないので、この差は仕様の範囲内です。比較の規則に「終了コードは 0 かそれ以外かだけを比べる」を足すかは、次に決めることになります。`printf` の 0、`sort` の 1、`ls -l` の `+` は 0.8.0 と同じでした。

更新は利用者の知らない間にも入ります。比べるスクリプトを残しておけば、変わった振る舞いを 1 回の実行で一覧にできます。

---

### 実験 2: 対象が自分で出す JSON と比べる

[jsonize](https://github.com/nao1215/jsonize) は、コマンドの出力を JSON に変換する著者の CLI で、コマンド名は `jz` です。コマンドごとに、出力の各行を正規表現で読む「定義」を持っています。

Linux のネットワークの設定を表示する `ip` コマンドは、`-br`（brief）を付けるとインターフェースを 1 行 1 つの短い表で出し、`-j` を付けると同じ内容を JSON で出します。以下は、docker が作った veth の行です。veth は、コンテナとホストをつなぐ仮想のネットワークインターフェースです。

```text
$ ip -br link
veth3a8eedd@if2  UP             xx:xx:xx:xx:xx:xx <BROADCAST,MULTICAST,UP,LOWER_UP>
```

左から、インターフェース名、状態、MAC アドレス（ここでは伏せています）、フラグです。この表を jz で JSON にした結果と、`ip -j -br link` の JSON は、同じ情報のはずです。後者を比較の相手にすると、jz の定義が値を正しく読んでいるかを確認できます。

ただし、キーの名前は一致しません。jz はインターフェース名を `interface` に置き、`ip -j` は `ifname` に置きます。そこで、キーは比べずに、1 行に含まれる値の集まりを比べます。

```python
for o, n in zip(ours, native):          # 行の位置で対にする
    a, b = Counter(leaves(o, [])), Counter(leaves(n, []))
    extra = a - b                         # jz にだけある値
```

`leaves` は、1 行分の JSON から値だけを取り出して 1 つの一覧にする関数です。`ip` の表と JSON は同じ順でインターフェースを並べるので、行の位置で対にできます。jz にだけある値は、jz が作った値か、誤って読んだ値の候補です。以下は、jz の修正前のバージョンと v0.9.1 で、veth の 1 行を比べた結果です。

{{< figure src="images/native_json.webp" alt="上は修正前の jz。interface の値 veth3a8eedd@if2 が赤く、jz にだけある値。ip -j の ifname の veth3a8eedd と link_index の 2 も赤い枠で、ip -j にだけある値。state の UP、lladdr の MAC、flags の 4 個は ip -j の値と実線でつながる。下は修正後の v0.9.1。interface の veth3a8eedd は ifname と実線で、peer の if2 は link_index の 2 と点線でつながり、if2 と 2 は表現の違いと書かれている" caption="docker の veth の 1 行。修正前の jz は名前に相手の番号を含めていた" align="center" >}}

修正前の jz は、`veth3a8eedd@if2` 全体をインターフェース名にしていました。`@` の後ろは veth の相手の番号で、`ip -j` では `link_index` という別の値です。この値をインターフェース名として次のコマンドに渡すと、`ip link show dev veth3a8eedd@if2` は `Device "veth3a8eedd@if2" does not exist.` で失敗します。

スクリプトは、jz にだけある値のうち、表現が違うだけと分かっている 2 種類を先に分けて数えます。1 つは「アドレスと長さ」で、jz の `127.0.0.1/8` に対して `ip -j` は `127.0.0.1` と `8` に分けています。もう 1 つは「ifN と N」で、jz の `if2` に対して `ip -j` は `2` です。

どちらにも当たらない値を「その他」として表示します。手元には docker の veth が 3 本あり、修正前の「その他 3」はその 3 本の名前です。

```text
== 修正前の jz
ip -br link: 11 行、76 値、jz にだけある値 3（アドレスと長さ 0、ifN と N 0、その他 3）
  その他: jz 'veth3a8eedd@if2'、ip の JSON にだけある値 ['2', 'veth3a8eedd']
ip -br addr: 11 行、40 値、jz にだけある値 21（アドレスと長さ 18、ifN と N 0、その他 3）
== jz v0.9.1
ip -br link: 11 行、79 値、jz にだけある値 3（アドレスと長さ 0、ifN と N 3、その他 0）
ip -br addr: 11 行、43 値、jz にだけある値 21（アドレスと長さ 18、ifN と N 3、その他 0）
```

修正後の jz は、veth の相手を `peer` という値に分けるので、値が 3 個増えて 79 個になりました。jz にだけある値は 0 になりませんが、全て表現の違いに分類され、その他は 0 です。

<br>

#### 表現の違いとバグの区別

`veth3a8eedd@if2` も、`ip -j` の 2 つの値（`veth3a8eedd` と `2`）をつないだ形です。字面だけで見ると、`127.0.0.1/8` と同じく表現の違いに見えます。

区別したのは、値がその名前の役割を果たすかです。`127.0.0.1/8` はアドレスの書き方として正しいですが、`veth3a8eedd@if2` はインターフェース名として使えません。そのため、`@if2` の方だけをバグとして直しました。

比べる前に表現の違いを吸収する変換（正規化）は、ノイズを減らす一方で、同じ形のバグも隠します。正規化の規則は、何の値に対して、なぜ同じとみなすかを 1 つずつ書いておく必要があります。

著者は jsonize で、表を出すコマンドとその JSON 出力の組 66 組を同じ方法で比べました。値の誤りとして直したのは、この `@if2` の 1 件です。

別の機会に、ディスクの一覧を出す `lsblk` の `-f`・`-m`・`-t` の 3 つの表で、`lsblk -J` とキーの名前で値を対応させて比べました。空白区切りの `-r` の形式でも桁を揃えた表でも、3 つ合わせて 1281 個の値で差が 0 でした。差が 0 という結果も、定義が値を正しく読んでいる根拠になります。

---

### 実験 3: 比較の相手同士の結果が違う時

[filesql](https://github.com/nao1215/filesql) は、CSV などのファイルを SQLite に読み込んで SQL で問い合わせる著者の Go のライブラリです。PostgreSQL や MySQL の書き方の SQL を受け取り、SQLite の SQL に変換して実行する機能も持っています。

この機能を検証する時、比較の相手の候補は 2 つあります。filesql が内部で使う SQLite と、filesql が書き方を受け付けると約束した PostgreSQL です。2 つの結果が同じなら迷いませんが、違う時はどちらかに合わせる必要があります。

以下は、同じ SQL を SQLite と PostgreSQL に渡す [exp3_group_by.sh](https://github.com/nao1215/debimate/blob/main/content/notes/software-testing/differential-testing/lab/exp3_group_by.sh) の結果です。テーブル `g` には `(1,10)`、`(2,10)`、`(3,20)` の 3 行があり、どちらの SQL も、GROUP BY に無く集約もしていない列 `a` を SELECT しています。

```text
== SQLite 3.46.1
> SELECT a, b FROM g GROUP BY b ORDER BY b;
(1, 10)
(3, 20)
> SELECT a, max(b) FROM g;
(3, 20)
== postgres (PostgreSQL) 17.11
> SELECT a, b FROM g GROUP BY b ORDER BY b;
ERROR:  column "g.a" must appear in the GROUP BY clause or be used in an aggregate function
> SELECT a, max(b) FROM g;
ERROR:  column "g.a" must appear in the GROUP BY clause or be used in an aggregate function
```

{{< figure src="images/sql.webp" alt="SELECT a, b FROM g GROUP BY b を 2 つの相手に渡す図。上は filesql が内部で使う SQLite で、(1, 10) と (3, 20) を返し、a はグループのどれか 1 行の値。下は filesql が約束した相手の PostgreSQL で、a は GROUP BY に無く集約もしていないので拒否する。下に、修正前の filesql は SQLite の答えを返していたが、約束した PostgreSQL に合わせて拒否するように直したと書かれている" caption="filesql にとって比較の相手の候補は 2 つあり、結果が違った" align="center" >}}

SQLite は答え、PostgreSQL は拒否しました。SQLite の答えは誤りではありません。[SQLite の文書](https://www.sqlite.org/lang_select.html#bare_columns_in_an_aggregate_query)は、このような列を bare column と呼び、グループのどれか 1 行の値を返すと定めています。`b = 10` のグループでは、`a` が 1 になるか 2 になるかは決まっていません。

修正前の filesql は、PostgreSQL の書き方の SQL を SQLite に渡し、SQLite の答えをそのまま返していました。

しかし、filesql は PostgreSQL の書き方を受け付けると約束しているので、比べる相手は PostgreSQL です。PostgreSQL の書き方で書かれた SQL に、決まっていない行を返すのは約束に反します。そこで、[filesql の Issue #1095](https://github.com/nao1215/filesql/issues/1095) で、変換の時点でこの SQL を拒否するように直しました。

比較の相手が 2 つあって結果が違う時は、どちらに合わせると約束したかで正しさが決まります。約束していない相手との差は、記録はしても直す理由にはなりません。

---

### 比べても見つからないもの

Differential Testing は、2 つの実装が同じ誤りを持っていると、差が出ないので見つけられません。

{{< figure src="images/blind_spot.webp" alt="仕様書の曖昧な記述について、実装 A と実装 B が同じ解釈をし、どちらも誤った出力 X を出す。比べると一致するので、テストは通る。比べて分かるのは 2 つが違うことだけで、2 つが正しいことは分からない" caption="2 つの実装が同じ誤りを持つと、比べても差が出ない" align="center" >}}
jsonize の定義と `ip -j` は別の人が書いたので、同じ誤りを持つ可能性は低いです。しかし、2 人の開発者が、仕様書の同じ曖昧な記述で、同じ誤った解釈をすることはあります。

また、渡していない入力の差は見つかりません。実験 1 で `/dev/full` の 4 ケースを足したのは、書き込みの失敗が書き直しで壊れやすいと知っていたからです。思い付かなかった入力は、比べようがありません。uutils の uufuzz がランダムな引数と入力を生成しているのは、人が思い付かない入力も比べるためです。入力を機械に作らせる方法は、次の [Fuzzing のノート](/notes/software-testing/fuzzing/)で扱います。

<br>

実装を書き直す時や、ライブラリ・DB を移行する時は、古い実装を消す前に比較のスクリプトを用意すると、変わった振る舞いを一覧にできます。最初に決めることは 3 つです。何を比べないか（文面、時刻、並び順など）、表現の違いをどの規則で同じとみなすか、差が出た時にどの文書で判断するかです。この 3 つを決めずに比べ始めると、差の一覧を読み切れなくなります。

実験のスクリプトと出力は [lab](https://github.com/nao1215/debimate/tree/main/content/notes/software-testing/differential-testing/lab) に、図の生成元は [figures.py](https://github.com/nao1215/debimate/blob/main/content/notes/software-testing/differential-testing/figures.py) にあります。
