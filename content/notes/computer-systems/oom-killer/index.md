---
title: "OOM killer - メモリが尽きた時に Linux が止めるプロセス"
date: 2026-11-10
draft: false
series: ["技術ノート", "Computer Systems"]
tags: ["computer-systems", "linux", "memory"]
weight: 1
wrapTables: true
topics: ["Linux Kernel"]
---

OOM killer（Out Of Memory killer）は、メモリが足りなくなった Linux カーネルがプロセスを選んで強制終了し、メモリを取り戻す仕組みです。

GUI が数分間固まると、OS やデスクトップ環境が不安定だと疑いたくなります。しかし、その原因がメモリ不足であることは珍しくありません。メモリが尽きかけると、カーネルは OOM killer を動かす前に、ファイルのキャッシュを捨てたり、メモリの中身をディスクのスワップ領域に退避したりしてメモリを空けようとします。その間はディスクの読み書きを待つ時間が増え、操作への応答が極端に遅くなります。

この状態を短くするために、カーネルより早い段階でプロセスを終了させる [earlyoom](https://github.com/rfjakob/earlyoom) というデーモンがあります。以下は、earlyoom を入れていない PC で空きメモリが減っていく時の経過を描いた模式図です。実測ではなく、生成コードは [figures.py](https://github.com/nao1215/debimate/blob/main/content/notes/computer-systems/oom-killer/figures.py) です。

{{< figure src="images/oom_timeline.svg" alt="横軸は時間。左の軸の空きメモリの線は下がり続け、右の軸の応答の遅さの破線は空きメモリが 20% を切った頃から上がり始める。空きメモリが 10% を切る所に、earlyoom を入れていればここで SIGTERM を送るという破線の縦線がある。応答が大きく悪化してから、右端でカーネルの OOM killer が動くまでの網掛けが、GUI が固まって見える区間" caption="earlyoom を入れていない PC で空きメモリが減っていく時の経過（模式図）" align="center" >}}

上記の図を見て分かる通り、カーネルの OOM killer が動くのは、メモリを空ける手段が尽きた最後の時点です。網掛けの区間では、プロセスは生きていますが、GUI は固まって見えます。earlyoom は空きメモリと空きスワップの割合を見て、それより前の時点で介入します。

<br>

本記事では、メモリ不足で GUI が固まる理由と、カーネルの OOM killer と earlyoom の違いを説明します。cgroup で上限を付けた実験で、OOM killer がプロセスを終了させる様子も確かめます。扱う疑問は以下の通りです。

- メモリが足りなくなると、なぜ OOM killer より先に GUI が固まるのか。
- OOM killer は、どのプロセスを終了させるのか。
- earlyoom は、カーネルの OOM killer と何が違うのか。
- メモリを使い切る処理は、どうすれば他のプロセスから切り離せるのか。

スワップの設定やメモリの断片化など、カーネルのメモリ管理の細部は説明しません。

---

### OOM killer が動くまで

Linux では、プロセスが確保したメモリにすぐ物理メモリが割り当てられるわけではありません。物理メモリのページは、プロセスが初めてそのメモリに触れた時点で割り当てられます（[カーネルの文書](https://docs.kernel.org/admin-guide/mm/concepts.html)）。

上記に加えて、Linux は物理メモリとスワップで裏付けられる量を超えるメモリの要求を受け付けることがあります。これをオーバーコミット（overcommit）と呼び、方針は [`vm.overcommit_memory`](https://docs.kernel.org/admin-guide/sysctl/vm.html#overcommit-memory) で変えられます。既定の 0 では、明らかに過大な要求だけを断ります（[Overcommit Accounting](https://docs.kernel.org/mm/overcommit-accounting.html)）。

そのため、`malloc` は成功したのに、後でメモリに書き込む段階になって物理メモリが足りなくなる状況が起きます。

物理メモリが足りなくなると、カーネルはメモリの回収（reclaim）を試みます。ファイルの内容を保持しているページキャッシュを捨てたり、しばらく使われていないページをスワップに退避したりします。どちらを優先するかは [`vm.swappiness`](https://docs.kernel.org/admin-guide/sysctl/vm.html#swappiness) などで変わり、順番は固定ではありません。

捨てたページや退避したページが繰り返し必要になると、読み直しと退避が延々と続きます。この状態をスラッシング（thrashing）と呼び、CPU はほとんどディスクを待つことになります。

カーネルから見ると、メモリはまだ回収できるので、OOM killer を動かす理由がありません。ユーザーから見ると、マウスカーソルすら動かない状態です。回収してもメモリを確保できなくなった時点で、ようやく OOM killer がプロセスを選んで `SIGKILL` で終了させます。

---

### 終了させるプロセスの選び方

OOM killer は、プロセスごとの点数（`oom_score`）が最も高いプロセスを終了させます。点数は主に使っているメモリの量で決まり、`oom_score_adj`（-1000〜1000）を足して調整できます。`oom_score_adj` を -1000 にしたプロセスは、カーネルの OOM killer の対象外です（[カーネルの文書](https://docs.kernel.org/filesystems/proc.html#chapter-3-per-process-parameters)）。

以下は、著者の環境で、シェル自身（`$$` はシェルのプロセス ID）の点数を読んだ結果です。

```console
$ cat /proc/$$/oom_score
800
$ cat /proc/$$/oom_score_adj
200
```

このシェルは Claude Code から起動されており、`oom_score_adj` が 200 に設定されていたので、点数が底上げされています。数値は環境で変わります。

メモリを多く使っているプロセスほど選ばれやすいですが、原因になったプロセスが選ばれるとは限りません。メモリを大量に使っているブラウザが、暴走した処理の巻き添えで終了されることもあります。

終了の記録はカーネルのログに残り、[journalctl](https://www.freedesktop.org/software/systemd/man/latest/journalctl.html) の `-k`（カーネルのメッセージだけを表示する）で確かめられます。`-k` が表示するのは今回の起動分だけなので、固まった後に再起動した場合は、`journalctl -k -b -1` で前回の起動分を見ます。

---

### 実例：Fuzzing でメモリを使い切った

著者の PC（RAM 128GB のうち 64GB をシステム、残りを GPU 用に割り当て）では、月に一回程度 GUI が固まっていました。最初は [Ubuntu](https://ubuntu.com/) 26.04 が不安定だと疑っていましたが、調べるとメモリ不足が原因でした（[weeknotes 2026/09/07 週](/weeknotes/2026-09-07/)）。

原因の一つは、自作のコマンドである [jsonize](https://github.com/nao1215/jsonize) の [Fuzzing](https://go.dev/doc/security/fuzz/)（自動で作った入力を大量に与えて、クラッシュする入力を探すテスト）でした。jsonize の aligned テーブルのパーサーは、列数に 256 の上限がある一方で行数には上限が無く、入力の約 13,000 倍のメモリを保持していました。

Fuzzing が作る 1MB 程度の入力でも、確保するメモリは十数 GB に達します。Go の Fuzzing は複数のワーカーで並列に動くので、合計はさらに増えます。64GB のメモリがあっても、入力の大きさに比例してメモリを使う処理が 1 つあれば足りなくなります。

---

### earlyoom：カーネルより早く終了させる

earlyoom は、ユーザー空間で空きメモリを監視し、カーネルの OOM killer より早い段階でプロセスを終了させるデーモンです。[マニュアル](https://github.com/rfjakob/earlyoom/blob/master/MANPAGE.md)によれば、既定では空きメモリ（`MemAvailable`、他のプロセスを止めずに使えるメモリの見積もり）と空きスワップがどちらも 10% 以下になると `SIGTERM` を送り、5% 以下になると `SIGKILL` を送ります。

```console
$ sudo apt install earlyoom
$ systemctl status earlyoom
```

利点は、カーネルの OOM killer より前に介入するので、GUI が長く固まる時間を短くできることです。冒頭の図で言えば、破線の縦線の時点で介入します。しかし、earlyoom が見ているのは空きの割合であり、GUI の応答そのものは見ていません。閾値に届く前に固まり始めることもあり、固まらないことを保証するものではありません。

欠点は、待てば終わったかもしれない処理も終了させることです。大きなビルドのように一時的にメモリを使う処理が終了される場合は、空きメモリの閾値を `-m`（空きスワップの閾値は `-s`）で下げます。`--avoid` を使うと、指定したプロセスの点数から 300 を引いて選ばれにくくできます。対象から完全に外すのは `--ignore` です。

似た仕組みに [systemd-oomd](https://www.freedesktop.org/software/systemd/man/latest/systemd-oomd.service.html) があります。systemd-oomd は、[PSI（Pressure Stall Information）](https://docs.kernel.org/accounting/psi.html)で見た「メモリ待ちで止まっていた時間の割合」や、スワップの使用率を設定に応じて監視し、cgroup 単位でプロセスを終了させます。

両方を同時に有効にすると、どちらがプロセスを終了させたのかを追いにくくなります。Ubuntu のように systemd-oomd が入っている環境で earlyoom を足す場合は、どちらを使うかを決めてから設定します。

---

### cgroup でメモリの上限を付ける

earlyoom は固まる時間を短くしますが、メモリを使い切る処理を直すわけではありません。jsonize の場合は、保持する行数に上限を付ける修正が根本対策です。

テストや Fuzzing のように、使うメモリの量を読みにくい処理は、動かす側で上限を付けます。Go には [`GOMEMLIMIT`](https://pkg.go.dev/runtime#hdr-Environment_Variables) がありますが、これは Go のランタイムが管理するメモリの目標値で、超えることもあります。保持し続けるデータが増える処理は、GOMEMLIMIT では止まりません。

確実に止めるには、Linux カーネルの [cgroup](https://docs.kernel.org/admin-guide/cgroup-v2.html) を使います。cgroup は、プロセスのまとまりごとに CPU やメモリの上限を付ける機能です。cgroup のメモリが上限に達し、回収しても収まらない場合、OOM killer はその cgroup の中だけからプロセスを選びます。コンテナのメモリの上限もこの仕組みで付けられています。そのため、[Sidecar](/notes/software-architecture/sidecar/) のように同じ Pod にログ転送などの補助コンテナを置いても、補助コンテナがメモリを使い切った時に止められるのは補助コンテナだけで、アプリケーションは巻き込まれません。

<br>

#### 実験：cgroup の上限で OOM killer を起こす

cgroup の中だけで OOM killer が動くことを確かめます。以下のコードは、100MB ずつメモリを確保し、確保した量を表示し続けます。

```python
"""100MB ずつメモリを確保し、確保した量を表示し続ける。

cgroup の上限を付けて実行し、OOM killer に終了されるまでを観察する。
    systemd-run --user --scope -p MemoryMax=200M -p MemorySwapMax=0 python3 lab/eat_memory.py
"""
import sys

chunks = []
for i in range(1, 51):  # 上限が効かなかった時のために 5GB で止める
    chunks.append(bytearray(100 * 1024 * 1024))  # 0 で埋めた 100MB を確保する
    print(f"{i * 100} MB allocated", flush=True)
print("finished without OOM", flush=True)
sys.exit(0)
```

[systemd-run](https://www.freedesktop.org/software/systemd/man/latest/systemd-run.html) は、コマンドを一時的な cgroup の中で動かしてくれます。`MemoryMax=200M` でメモリの上限を 200MB にし、`MemorySwapMax=0` でスワップへの退避を禁じています。実行環境は Linux 7.0.0、systemd 259、Python 3.14.4 です。

```console
$ systemd-run --user --scope -p MemoryMax=200M -p MemorySwapMax=0 python3 lab/eat_memory.py
Running as unit: run-p818544-i46937880.scope; invocation ID: 9127f4fce77c4f7592101997820cc9af
100 MB allocated
/bin/bash: 16 行: 818544 強制終了               systemd-run --user --scope -p MemoryMax=200M -p MemorySwapMax=0 python3 lab/eat_memory.py
$ echo $?
137
```

100MB を確保した後、200MB 目の確保で上限を超え、プロセスは強制終了されました。終了コードの 137 は 128 にシグナル番号を足した値で、9 番の `SIGKILL` で終了したことを示します。カーネルのログには、以下の記録が残っていました（抜粋）。

```text
python3 invoked oom-killer: gfp_mask=0xcc0(GFP_KERNEL), order=0, oom_score_adj=200
oom-kill:constraint=CONSTRAINT_MEMCG,...,task=python3,pid=818544,uid=1000
Memory cgroup out of memory: Killed process 818544 (python3) total-vm:221812kB, anon-rss:204308kB, ...
```

`constraint=CONSTRAINT_MEMCG` は、システム全体ではなく cgroup（memcg）の上限で OOM killer が動いたことを示します。終了させる候補も、その cgroup の中の python3 だけです。この間、PC の他のプロセスと GUI は普段通りに動いていました。ログの全体は [lab/output.txt](https://github.com/nao1215/debimate/blob/main/content/notes/computer-systems/oom-killer/lab/output.txt) にあります。

Fuzzing のようにメモリの使い方を読めない処理も、同じように `systemd-run` で上限を付けて動かせば、PC 全体を巻き込まずに済みます。
