---
title: "【C言語】完全なオブジェクト指向ではなく、Interfaceのみを利用する選択【Golangを参考に】"
type: post
date: 2021-11-17
categories:
  - "linux"
tags:
  - "c言語"
  - "interface"
  - "オブジェクト指向"
cover:
  image: "images/Valac.jpg"
  alt: "【C言語】完全なオブジェクト指向ではなく、Interfaceのみを利用する選択【Golangを参考に】"
  hidden: false
---

### C言語とオブジェクト指向は相性悪い

オブジェクト指向は、C言語でも実現できます。

C言語は、言語によるオブジェクト指向プログラミングのサポートがありません。しかし、開発者が注意深く実装する事によって、オブジェクト指向プログラミングが可能です。

詳しくない方は、「[C言語によるオブジェクト指向プログラミング入門](https://www.amazon.co.jp/C%E8%A8%80%E8%AA%9E%E3%81%AB%E3%82%88%E3%82%8B%E3%82%AA%E3%83%96%E3%82%B8%E3%82%A7%E3%82%AF%E3%83%88%E6%8C%87%E5%90%91%E3%83%97%E3%83%AD%E3%82%B0%E3%83%A9%E3%83%9F%E3%83%B3%E3%82%B0%E5%85%A5%E9%96%80-%E5%9D%82%E4%BA%95-%E5%BC%98%E4%BA%AE/dp/4798121134?__mk_ja_JP=%E3%82%AB%E3%82%BF%E3%82%AB%E3%83%8A&keywords=C%E8%A8%80%E8%AA%9E+%E3%82%AA%E3%83%96%E3%82%B8%E3%82%A7%E3%82%AF%E3%83%88%E6%8C%87%E5%90%91&qid=1637120966&sr=8-1&linkCode=ll1&tag=debimate07-22&linkId=f66ecd8a94933cd541c88d3f95a23fb6&language=ja_JP&ref_=as_li_ss_tl)」や「[モダンC言語プログラミング](https://www.amazon.co.jp/%E3%83%A2%E3%83%80%E3%83%B3C%E8%A8%80%E8%AA%9E%E3%83%97%E3%83%AD%E3%82%B0%E3%83%A9%E3%83%9F%E3%83%B3%E3%82%B0-%E3%82%A2%E3%82%B9%E3%82%AD%E3%83%BC%E6%9B%B8%E7%B1%8D-%E8%8A%B1%E4%BA%95-%E5%BF%97%E7%94%9F-ebook/dp/B00HWLJEKW?__mk_ja_JP=%E3%82%AB%E3%82%BF%E3%82%AB%E3%83%8A&keywords=C%E8%A8%80%E8%AA%9E+%E3%82%AA%E3%83%96%E3%82%B8%E3%82%A7%E3%82%AF%E3%83%88%E6%8C%87%E5%90%91&qid=1637120966&sr=8-5&linkCode=ll1&tag=debimate07-22&linkId=fd8da8d7bfb9f70685da31697daa9dd0&language=ja_JP&ref_=as_li_ss_tl)」を手に取るか、[GLib（GNOME ToolKitのベースライブラリ）](https://gitlab.gnome.org/GNOME/glib)のようにオブジェクト指向プログラミングで実装されたコードを確認してみてください。

C言語にオブジェクト指向を適用する場合、実装規模が爆発的に増えます。さらに、プロジェクトに旗振り役のリーダーが居ないと、容易にオブジェクト指向が崩れます（言語がオブジェクト指向を強制しないため）。

そもそも、C言語プログラマも他言語プログラマも、C言語とオブジェクト指向の組み合わせには拒否反応を示す可能性が高いです。C言語プログラマ視点では「労力の割にリターンが少ない」と感じ、他言語プログラマ視点は「クラスを作るためだけに、どれだけコードを書かせるのか」と感じます。

オブジェクト指向のメリットを得るために、C++や[Vala言語](https://ja.wikipedia.org/wiki/Vala)を選択する方法もあります。しかし、プロジェクトによってはC言語を選択しなければならない場合があるでしょう（補足：Vala言語はC#のような文法を持ち、valaファイル → C言語ファイル（中間ファイル） → バイナリの順でコンパイルするマイナー言語）

\[caption id="attachment\_6924" align="aligncenter" width="628"\]![Introducing Vala Programming（Michael Lauer著、35頁）より引用](images/Valac.jpg) Introducing Vala Programming（Michael Lauer著、35頁）より引用\[/caption\] 

上記のような課題を踏まえて、C言語ではどこまでオブジェクト指向ライクに実装すべきでしょうか。その現実解は、「Golangのようにクラス構造や継承を捨て、Interfaceだけ利用する」ではないかと感じ始めました。

---


### C言語とInterfaceの組み合わせは簡単

C言語とオブジェクト指向との組み合わせで面倒な部分は、「クラス構造（new, deleteサポート）」、「継承の実現」、「public、protected、private等のアクセス範囲コントロール」です。

面倒な割に、メリットがほぼ無いです。現代のプログラミングでは、「継承を使わない方が良い」という見解が強まっています。継承がなければ、クラス構造とprotectedの利点が薄れます。つまり、苦労して実装したオブジェクト指向の使いどころが殆どありません。

その一方でInterfaceはどうでしょうか。

C言語では、Interfaceは関数ポインタをメンバ変数に持つ構造体です。新しい構造体（Interface）を一つ作り、Interfaceを別の構造体（データを持つメンバ変数）に含める方法は、とても簡単に実現できます。

Interfaceの利便性は、様々なコードで証明されています。例えば、Linux Kernelではファイル操作のInterfaceがfile\_operations構造体として定義されています。

```
struct file_operations {
	struct module *owner;
	loff_t (*llseek) (struct file *, loff_t, int);
	ssize_t (*read) (struct file *, char __user *, size_t, loff_t *);
	ssize_t (*write) (struct file *, const char __user *, size_t, loff_t *);
	ssize_t (*read_iter) (struct kiocb *, struct iov_iter *);
	ssize_t (*write_iter) (struct kiocb *, struct iov_iter *);
	int (*iopoll)(struct kiocb *kiocb, bool spin);
	int (*iterate) (struct file *, struct dir_context *);
	int (*iterate_shared) (struct file *, struct dir_context *);
	__poll_t (*poll) (struct file *, struct poll_table_struct *);
	long (*unlocked_ioctl) (struct file *, unsigned int, unsigned long);
	long (*compat_ioctl) (struct file *, unsigned int, unsigned long);
	int (*mmap) (struct file *, struct vm_area_struct *);
	unsigned long mmap_supported_flags;
	int (*open) (struct inode *, struct file *);
	int (*flush) (struct file *, fl_owner_t id);
	int (*release) (struct inode *, struct file *);
	int (*fsync) (struct file *, loff_t, loff_t, int datasync);
	int (*fasync) (int, struct file *, int);
	int (*lock) (struct file *, int, struct file_lock *);
	ssize_t (*sendpage) (struct file *, struct page *, int, size_t, loff_t *, int);
	unsigned long (*get_unmapped_area)(struct file *, unsigned long, unsigned long, unsigned long, unsigned long);
	int (*check_flags)(int);
	int (*flock) (struct file *, int, struct file_lock *);
	ssize_t (*splice_write)(struct pipe_inode_info *, struct file *, loff_t *, size_t, unsigned int);
	ssize_t (*splice_read)(struct file *, loff_t *, struct pipe_inode_info *, size_t, unsigned int);
	int (*setlease)(struct file *, long, struct file_lock **, void **);
	long (*fallocate)(struct file *file, int mode, loff_t offset,
			  loff_t len);
	void (*show_fdinfo)(struct seq_file *m, struct file *f);
#ifndef CONFIG_MMU
	unsigned (*mmap_capabilities)(struct file *);
#endif
	ssize_t (*copy_file_range)(struct file *, loff_t, struct file *,
			loff_t, size_t, unsigned int);
	loff_t (*remap_file_range)(struct file *file_in, loff_t pos_in,
				   struct file *file_out, loff_t pos_out,
				   loff_t len, unsigned int remap_flags);
	int (*fadvise)(struct file *, loff_t, loff_t, int);
} __randomize_layout;
```

file\_operations構造体（Interface）に対して、操作するファイル種類ごとに異なる関数ポインタをセットすれば、処理を柔軟に切り替えられます。

```
static const struct file_operations cpuid_fops = {
	.owner = THIS_MODULE,
	.llseek = no_seek_end_llseek,
	.read = cpuid_read,
	.open = cpuid_open,
};
```

```
const struct file_operations binder_fops = {
	.owner = THIS_MODULE,
	.poll = binder_poll,
	.unlocked_ioctl = binder_ioctl,
	.compat_ioctl = compat_ptr_ioctl,
	.mmap = binder_mmap,
	.open = binder_open,
	.flush = binder_flush,
	.release = binder_release,
};
```

下手にガチガチのオブジェクト指向をC言語に適用するよりは、Interfaceの適用ぐらいが費用対効果的に好ましいのではないかな、と考えています。

---


### 後書き：C言語から離れるので最後にポエム記事

[転職した関係](https://debimate.jp/post/2021-11-13-%E9%80%80%E8%81%B7%E3%82%A8%E3%83%B3%E3%83%88%E3%83%AA%E6%96%B0%E6%BD%9F%E5%9C%A8%E4%BD%8F%E3%81%AE%E7%B5%84%E3%81%BF%E8%BE%BC%E3%81%BF%E3%82%A8%E3%83%B3%E3%82%B8%E3%83%8B%E3%82%A2/)で、大学時代から10年近く触り続けていたC言語とお別れします。そのため、最後にポエム記事を書きました。

C言語はプログラマのスキルが如実に反映される言語であり、OSSのコード（Linux Kernelやsystemd等）を見ると、そのレベルの高さ（作者の頭の良さ）を痛感する事が多かったです。システムプログラミングや組み込みには、C言語は良い言語です。ただし、趣味のコーディングではもう選択しないと思います（GolangやRustを選択するかな）。

今振り返れば、私が大学生／大学院の頃（2009〜2014年）は、世間様も私自身もオブジェクト指向信仰が強かった気がします。私は、オブジェクト指向こそが設計の全てのように錯覚していました。しかし、最近（2021年）は関数型言語の良さがJava等の言語に取り込まれたり、クラス構造をそこまで大事にしないGolangが流行っています。[staticおじさん](https://monobook.org/wiki/Static%E3%81%8A%E3%81%98%E3%81%95%E3%82%93)の時代とは変わったな、と思わずにはいられません。

私の中でもオブジェクト指向への憧れや固定観念は、薄れてきました。以前よりフラットな視点で「C言語とオブジェクト指向の関わり方」を再考した結果、「Interfaceがあれば良いのでは？」と考えた次第です。
