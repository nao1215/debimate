---
title: "Linux Kernel: prink(print kernel)によるメッセージ出力"
type: post
date: 2019-02-02
categories:
  - "linux"
tags:
  - "c言語"
  - "linux"
  - "linuxkernel"
cover:
  image: "images/bash-161382_640.png"
  alt: "Linux Kernel: prink(print kernel)によるメッセージ出力"
  hidden: false
---

### printk()とは

printk(print kernel)は、ユーザ空間のprintf( print formatted )に相当します。注意すべき点として、printf()と以下の点が異なります。本記事では、この差異を説明します。

printf()との差異

- フォーマット
- ログレベルの存在
- printk()のラッパーマクロの存在
- ログの出力先がメッセージ用リングバッファ
- メッセージ表示に使用するコマンド(dmesg等)の存在

---


### printk()フォーマット

pritnk()フォーマットは、printfとほぼ同様です。差異は、ログレベル(0〜7, d, c)が指定できる点、実数型(double/float)をサポートしない点です。ログレベルは後ほど解説します。

```
printk( ログレベル 書式文字列, 可変個引数 );
```

文字列の書式は、「printf(3)を参考にする事("$ man 3 printf")」とソースコード中に記載されている。下表に、代表的な指定文字を示す。型に応じて、どの変換指定文字を使用すべきか迷った場合は、[公式ドキュメントに逆引きが存在](https://www.kernel.org/doc/html/latest/core-api/printk-formats.html?highlight=printk)します。

| 変換指定文字 | 意味 |
| --- | --- |
| %c | 1文字として出力 |
| %d | 10進数で出力 |
| %x | 16進数で出力 |
| %o | 8進数で出力 |
| %f | 使用不可。浮動小数点(実数)をKernelはサポートしない |
| %d | 使用不可。浮動小数点(実数)をKernelはサポートしない |
| %s | 文字列として出力 |
| %p | ポインタ情報を出力（[ポインタ関連は変換指定文字が多数存在](https://qiita.com/todok-r/items/d754fb29930431c9efa0)） |

なお、ログレベルと書式文字列の間には、","がありません。

```
printk(KERN_WARNING "Test message.\n");

```

KERN\_WARNINGは、defineマクロで定義された"4"を意味します。C言語では自動的にログレベルと書式文字列("Test〜"の部分)は、 文字列として結合されます。ログレベルを指定しなかった場合は、自動的にデフォルト値(KERN\_WARNING)となります。

---


### ログレベル一覧

| **文字列** |   **defineマクロ**   | **意味・用途** |
| --- | --- | --- |
| 0 | KERN\_EMERG |  システム停止前の緊急メッセージ |
| 1 | KERN\_ALERT |  早急な対応が必要なエラー |
| 2 | KERN\_CRIT |  HWもしくはSWの致命的なエラー |
| 3 | KERN\_ERR |  ドライバ共通のエラー |
| 4 | KERN\_WARNING |  警告(エラーとなる可能性がある) |
| 5 | KERN\_NOTICE |  注意(エラーではない) |
| 6 | KERN\_INFO |  情報通知 |
| 7 | KERN\_DEBUG |  デバッグメッセージ専用 |
| d | KERN\_DEFAULT | デフォルトのログレベル |
| c | KERN\_CONT | ログの継続(タイムスタンプの更新を回避。ブート中専用) |

---


### printk()のラッパーマクロ

Kernel開発者は、printk()を高頻度で使用します。利便性を高めるために、printkに関するラッパーマクロが存在します。マクロは、"[<Linux>/include/linux/printk.h](https://github.com/torvalds/linux/blob/master/include/linux/printk.h)"に定義されています。

良く使用するマクロは、ログレベルを省略できるマクロです。マクロは、以下のように定義されています。全てのログレベルに対して、マクロが用意されています(下表)。

```
#define pr_warning(fmt, ...) \
	printk(KERN_WARNING pr_fmt(fmt), ##__VA_ARGS__)
```

```
/* 以下の二つの書き方では、同じ結果が得られます。*/
printk(KERN_WARNING "Test message.\n");
pr_warn("Test message.\n");

```

| **文字列** |   **ログレベル**   | **ラッパーマクロ** |
| --- | --- | --- |
| 0 | KERN\_EMERG | pr\_emerg |
| 1 | KERN\_ALERT | pr\_alert |
| 2 | KERN\_CRIT | pr\_crit |
| 3 | KERN\_ERR | pr\_err |
| 4 | KERN\_WARNING | pr\_warningもしくはpr\_warn |
| 5 | KERN\_NOTICE | pr\_notice |
| 6 | KERN\_INFO | pr\_info |
| 7 | KERN\_DEBUG | pr\_devel(#ifdefによって、"DEBUG"が0の場合はprintk()しない仕様) |
| c | KERN\_CONT | pr\_cont |

上記の他にも、一度しかprintkを表示しないマクロや遅延表示するマクロが存在します。

\[the\_ad id="598"\]

---


### printk()出力先のメッセージリングバッファ

printk()は、ログレベルに関わらず、Kernel内部ログバッファにメッセージを保存しています。このログバッファは循環式であり、バッファ上限値を超えた場合は古いメッセージをに上書きする形で新しいメッセージを保存します。なお、ログバッファにメッセージを書き込む前に、タイムスタンプが付与されます。

ログバッファのサイズ変更は、Linux Kernelビルド前設定("make menuconfig")で行います。変更対象は"**CONFIG\_LOG\_BUF\_SHIFT"**で、Bitシフトでしか設定できません(下図)。

![](images/バッファサイズ.png)

---


### メッセージ表示に利用するdmesgコマンド

printk()で用いるログバッファは、[dmesgコマンド](http://www.atmarkit.co.jp/ait/articles/1612/20/news023.html) で内容を表示できます。dmesgは、klogctl(システムコール)を使用して、ログバッファを読み取り、標準出力 に表示します(以下の例を参考)。出力行数が多いため、head/tail/less/grepなどのコマンドで、メッセージを取捨選択したほうが良いです。

```
$ sudo dmesg | head -n 10
[    0.000000] Linux version 4.9.0-8-amd64 (debian-kernel@lists.debian.org) (gcc version 6.3.0 20170516 (Debian 6.3.0-18+deb9u1) ) #1 SMP Debian 4.9.130-2 (2018-10-27)
[    0.000000] Command line: BOOT_IMAGE=/boot/vmlinuz-4.9.0-8-amd64 root=UUID=0c52f0f1-f354-4cff-9ed7-e8d7a8bc9814 ro quiet
[    0.000000] x86/fpu: Supporting XSAVE feature 0x001: 'x87 floating point registers'
[    0.000000] x86/fpu: Supporting XSAVE feature 0x002: 'SSE registers'
[    0.000000] x86/fpu: Supporting XSAVE feature 0x004: 'AVX registers'
[    0.000000] x86/fpu: Supporting XSAVE feature 0x008: 'MPX bounds registers'
[    0.000000] x86/fpu: Supporting XSAVE feature 0x010: 'MPX CSR'
[    0.000000] x86/fpu: xstate_offset[2]:  576, xstate_sizes[2]:  256
[    0.000000] x86/fpu: xstate_offset[3]:  832, xstate_sizes[3]:   64
[    0.000000] x86/fpu: xstate_offset[4]:  896, xstate_sizes[4]:   64

```

ログ出力の程度を抑えるために、ユーザ設定のログレベルのメッセージだけを表示する仕組みがあります。その設定値は、"/proc/sys/kernel/printk"に記載されています。以下にprintkファイルに記載された設定値を示し、その設定値の意味を下表に示します。

```
$ cat /proc/sys/kernel/printk
4	4	1	7

(注釈)数値は左から順に、
console_loglevel、default_message_level、minimum_console_loglevel、　default_console_loglevel

```

|   **設定**   | **意味** |
| --- | --- |
| console\_loglevel | ログレベルが設定値より小さい場合のみ、コンソール出力可能。 |
| default\_message\_level | 明示的にログレベルが設定されていないpritnk()メッセージのログレベル |
| minimum\_console\_loglevel | console\_loglevelに設定できる最小値 |
| default\_console\_loglevel | console\_loglevelのデフォルト値 |

"/proc/sys/kernel/printk"は書き込み可能なファイルであるため、以下のように設定値を変更できます。ただし、管理者権限が必要です。

```
# cat /proc/sys/kernel/printk
4	4	1	7
# echo "7 2 1 7" > /proc/sys/kernel/printk
# cat /proc/sys/kernel/printk
7	2	1	7

```

最後に余談ですが、Linuxは、dmesgとは別の仕組みでログが管理されています。システム内部では、klogd が周期的にログ内容を収集し、 /var/log/syslog に書き出しています。こちらに関しては、インフラ系の勉強時に記事を作成します。

---


### 参考

[Linux Kernel公式ドキュメント](https://www.kernel.org/doc/html/latest/driver-api/basics.html?highlight=printk#c.printk)

[カーネル・ロギング: API と実装(IBM)](https://www.ibm.com/developerworks/jp/linux/library/l-kernel-logging-apis/index.html)

[<Linux>kernel/printk/printk.c](https://github.com/torvalds/linux/blob/master/kernel/printk/printk.c)
