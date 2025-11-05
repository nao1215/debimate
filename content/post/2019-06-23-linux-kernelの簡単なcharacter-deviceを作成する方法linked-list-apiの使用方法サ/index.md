---
title: "Linux Kernelの簡単なCharacter Deviceを作成する方法(Linked List APIの使用方法サンプル)"
type: post
date: 2019-06-23
categories:
  - "linux"
tags:
  - "c言語"
  - "debian"
  - "devicedriver"
  - "linux"
  - "linuxkernel"
cover:
  image: images/businesswoman-571153_640.jpg
  alt: "Linux Kernelの簡単なCharacter Deviceを作成する方法(Linked List APIの使用方法サンプル)"
  hidden: false
images: ["images/businesswoman-571153_640.jpg"]
---

## 前書き

本記事では、Linux KernelにおけるCharacter Device向けのDevice Driverを作成する方法を示します。専用のHardware(例：シリアルデバイスのUARTなど)を用いず、メモリ上のデータ読み書きのみを行います。そのため、擬似デバイス(/dev/nullや/dev/zeroなど)を操作するDriverと同等です。

Character Deviceは、少量のデータを管理する低速のデバイスを指し、該当するデバイスはキーボード、マウス、シリアルポート等です。これらのデバイスを読み書き(Read/Write)操作する際、バイト単位で順次操作します。

本記事で作成するDevice Driverでは、Open/Close、Read/Writeのシステムコールのみを実装します(仕様概要は下表)。

| **システムコール** | **仕様説明** |
| --- | --- |
| Write |   ユーザが文字列を書き込む度に(Writeシステムコールを発行する度に)、Listに要素を追加します。増やした要素に、ユーザが書き込んだ文字列を保持します。   |
| Read | ユーザが書き込んだ文字列を管理するListを操作し、ユーザが指定したByte数だけ文字列をユーザに返します。 |
| Open | ユーザが書き込む文字列を管理するためのListを初期化します。 |
| Close | Read/Writeシステムコールで使用したListや文字列保持用のメモリを解放します。 |

## 検証環境

検証は、Debian10(buster)環境で実施しました。他のディストリビューションでもDevice Driverが作成可能ですが、Debian系(Ubuntu、Kaliなど)を使用した方が作業手順に差異が少ないと思われます。

```
$ neofetch                                                    2019年06月23日 12時26分29秒
       _,met$$$$$gg.          nao@debian 
    ,g$$$$$$$$$$$$$$$P.       ---------- 
  ,g$$P"     """Y$$.".        OS: Debian GNU/Linux 10 (buster) x86_64 
 ,$$P'              `$$$.     Kernel: 4.19.0-5-amd64 
',$$P       ,ggs.     `$$b:   Uptime: 3 hours, 39 minutes 
`d$$'     ,$P"'   .    $$$    Packages: 2606 (dpkg) 
 $$P      d$'     ,    $$P    Shell: fish 3.0.2 
 $$:      $$.   - ,d$$'    Resolution: 2560x1080 
 $$;      Y$b._   _,d$P'      DE: Cinnamon 3.2.7 
 Y$$.    `.`"Y$$$$P"'         WM: Mutter (Muffin) 
 `$$b      "-.__              WM Theme: cinnamon (Albatross) 
  `Y$$                        Theme: BlackMATE [GTK2/3] 
   `Y$$.                      Icons: gnome [GTK2/3] 
     `$$b.                    Terminal: gnome-terminal 
       `Y$$b.                 CPU: Intel i3-6100U (4) @ 2.300GHz 
          `"Y$b._             GPU: Intel HD Graphics 520 
              `"""            Memory: 5669MiB / 32060MiB 
```

## 前準備

Linux Kernel用のDevice Driverを作成するには、環境構築が必要になります。環境構築およびKernelモジュールの雛形を作成するまでの手順は、以下の記事に記載してあります。本記事の手順を実施する前に、確認して下さい。

また、本記事で使用するコードは、[GitHub](https://github.com/nao1215/LinuxKernelArticle/tree/master/01_char_device)に格納してあります。

https://debimate.jp/2019/01/27/%E7%92%B0%E5%A2%83%E6%A7%8B%E7%AF%89-linux-kernel%E3%83%A2%E3%82%B8%E3%83%A5%E3%83%BC%E3%83%AB%E3%81%AE%E4%BD%9C%E6%88%90%E6%BA%96%E5%82%99/

## Device DriverのLoad処理の作成

Device DriverのLoad時(手動の場合はinsmodコマンド実行時)は、以下の内容を実施します。詳細な説明は、コードの後に記載しています。

- デバイスのメジャー番号(デバイスの種類を表す番号)を動的取得
- /sys/class/以下にデバイスクラスを登録
- Character Deviceを操作するためのシステムコールを登録
- Character DeviceをKernelに登録
- /dev以下にデバイスノード(今回は/dev/debimate)を追加

```
#include <linux/module.h>
#include <linux/fs.h>
#include <linux/cdev.h>
#include <linux/device.h>
#include <linux/slab.h>
#include <linux/uaccess.h>

MODULE_LICENSE("Dual BSD/GPL");
MODULE_AUTHOR("Nao <n.chika156@gmail.com>");
MODULE_INFO(free_form_info, "You can write the string here freely");
MODULE_DESCRIPTION("This moduel is for testing");

#define DEV_NAME  "debimate"
#define DEV_CLASS "debimate_class"
#define MINOR_NR_BASE 0
#define MAX_MINOR_NR  1

static struct class *debimate_class;
static struct cdev   debimate_cdev;
static dev_t dev;

/* 省略 */

 static int __init debimate_init(void)
{
	int result                  = 0;
	struct device *debimate_dev = NULL;

	pr_info(KERN_INFO "START: %s\n", __func__);

	/* メジャー番号の動的確保 */
	result = alloc_chrdev_region(&dev, MINOR_NR_BASE,
                                 MAX_MINOR_NR, DEV_NAME);
	if (result) {
		pr_err("%s: alloc_chrdev_region = %d\n", __func__, result);
		goto REGION_ERR;
	}

	/* デバイスをクラス登録 */
	debimate_class = class_create(THIS_MODULE, DEV_CLASS);
	if(IS_ERR(debimate_class)) {
		result = PTR_ERR(debimate_class);
		pr_err("%s: class_create = %d\n", __func__, result);
		goto CREATE_CLASS_ERR;
	}

	/* キャラクターデバイス構造体(cdev構造体)初期化および
	 * システムコールの関数ポインタ登録 */
	cdev_init(&debimate_cdev, &debimate_drv_fops);

	/* キャラクターデバイスをKernelに登録 */
	result = cdev_add(&debimate_cdev, dev, MAX_MINOR_NR);
	if (result) {
		pr_err("%s: cdev_add = %d\n", __func__, result);
		goto CDEV_ADD_ERR;
	}

	/* デバイスノードを作成。作成したノードは/dev以下からアクセス可能 */
	debimate_dev = device_create(debimate_class, NULL, dev, NULL,
                                 DEV_NAME, MINOR_NR_BASE);
	if (IS_ERR(debimate_dev)) {
		result = PTR_ERR(debimate_dev);
		pr_err("%s: device_create = %d\n", __func__, result);
		goto DEV_CREATE_ERR;
	}
	pr_info(KERN_INFO "END  : %s\n", __func__);
	return result;

DEV_CREATE_ERR:
	cdev_del(&debimate_cdev);
CDEV_ADD_ERR:
	class_destroy(debimate_class);
CREATE_CLASS_ERR:
	unregister_chrdev_region(dev, MAX_MINOR_NR);
REGION_ERR:
	return result;
}

```

Load用の関数(debimate\_init())全体で注意すべき点は、各登録処理(class\_create())の途中で失敗した場合、それまでに成功していた登録処理を解除する事です。そのため、各処理の異常系では、登録解除処理を行う位置までgoto文を用いてジャンプします。

異常系処理で用いられるIS\_ERR()やPTR\_ERR()は、NULLポインタのエラー原因を特定するためのKernel APIです。このKernel特有のエラーハンドリングに関しては、以下の記事にまとめてあります。

https://debimate.jp/2019/03/02/linux-kernel-null%E3%83%9D%E3%82%A4%E3%83%B3%E3%82%BF%E3%82%A8%E3%83%A9%E3%83%BC%E3%83%8F%E3%83%B3%E3%83%89%E3%83%AA%E3%83%B3%E3%82%B0err\_ptr-is\_err-ptr\_err/

debimate\_init()の最初で実行しているalloc\_chrdev\_region()では、メジャー番号を動的に取得しています。引数のMINOR\_NR\_BASE、MAX\_MINOR\_NRは、マイナー番号用の設定です。メジャー番号はデバイスの種類を表し、マイナー番号は同じ種類のデバイス(複数個)を識別するため値です。

今回の例では、debimate(デバイス)用のメジャー番号を動的に取得し、マイナー番号は0〜1まで割り当てるという設定をしています。メジャー番号とデバイスの対応は、以下のように/proc/devicesで確認できます。

```
$ cat /proc/devices                                           2019年06月23日 14時18分26秒
Character devices:
  1 mem
  4 /dev/vc/0
  4 tty
  4 ttyS
  5 /dev/tty
  5 /dev/console
  5 /dev/ptmx
  7 vcs
 10 misc
 13 input
 21 sg
 29 fb
116 alsa
128 ptm
136 pts
153 spi
180 usb
189 usb_device
216 rfcomm
226 drm
242 debimate               ★ 今回登録するメジャー番号(番号は環境によって変わります)
243 mei
244 BaseRemoteCtl
245 hidraw
246 aux
247 bsg
248 watchdog
249 ptp
250 pps
251 cec
252 rtc
253 dax
254 gpiochip

Block devices:
  8 sd
  （省略）
```

次のclass\_create()は、/sys/class/以下にデバイスを登録します。/sys/class以下には、クラスで分類されたデバイスの親子関係をディレクトリ階層(サブディレクトリ)で表します。今回の例では、/sys以下に関する設定をしないため、「登録しただけ」という形になります。生成されるディレクトリは、以下の通りです。

```
$ pwd                                                         2019年06月23日 14時41分30秒
/sys/class/debimate_class/debimate
$ tree                                                        2019年06月23日 14時41分31秒
.
├── dev
├── power
│   ├── async
│   ├── autosuspend_delay_ms
│   ├── control
│   ├── runtime_active_kids
│   ├── runtime_active_time
│   ├── runtime_enabled
│   ├── runtime_status
│   ├── runtime_suspended_time
│   └── runtime_usage
├── subsystem -> ../../../../class/debimate_class
└── uevent

```

cdev\_init()では、Charcter Deviceを操作するために、file\_operations構造体に各システムコール(ReadやWriteなど)用の関数ポインタを登録します。関数ポインタを登録していないシステムコールは、NULL扱いなため、Kernel内部で使用されません。今回の例では、以下の関数をセットします。メンバ変数owner(module構造体)は、どのようなDevice DriverであってもTHIS\_MODULEを指定します。コンパイル時に、メンバ変数ownerに値が自動的にセットされます。

```
static struct file_operations debimate_drv_fops ={
	.owner    = THIS_MODULE,
	.open     = debimate_open,
	.release  = debimate_close,
	.read     = debimate_read,
	.write    = debimate_write,
};

```

cdev\_add()ではKernelにCharacter Deviceを登録し、device\_create()では/dev以下にデバイスファイル(デバイスノード)を生成します。ここまでが、Load処理となります。

## Device DriverのUnload処理の作成

Unload処理は、Load時に実行した登録処理と逆の順番で、各登録の解除処理を実施します。ここでの各登録の解除処理は、Load時の異常系(goto文を用いた解除処理)に似た流れで実施します。

- /dev以下からデバイスノード(今回は/dev/debimate)を削除
- Character DeviceをKernelから削除
- /sys/class/以下からデバイスクラスを削除
- Character Deviceが使用していたメジャー番号の登録を解除

```
static void __exit debimate_exit(void)
{
	pr_info(KERN_INFO "START: %s\n", __func__);

	/* デバイスノードの削除 */
	device_destroy(debimate_class, dev);

	/* キャラクターデバイスをKernelから削除 */
	cdev_del(&debimate_cdev);

	/* デバイスのクラス登録を削除 */
	class_destroy(debimate_class);

	/* デバイスが使用していたメジャー番号の登録を解除 */
	unregister_chrdev_region(dev, MAX_MINOR_NR);

	pr_info(KERN_INFO "END  : %s\n", __func__);
}

```

## Device DriverのOpen処理の作成

Open処理では、同じデバイスファイルを複数プロセスから同時に開かれた場合に備えて、関数内でメモリを確保します。つまり、グローバル変数を用いて、複数プロセス用に使い回す事はしません。グローバル変数を共有する場合は、データの競合が発生しないように注意が必要です。

関数内で確保したメモリを他関数(ReadやWrite)で使用するために、Open関数の引数として渡されるfile構造体を用います。file構造体のメンバ変数private\_data(void型ポインタ)に、Device Driver内で使用するメモリを渡しておけば、ReadやWriteでもprivate\_dataを使用できます。

今回のOpen処理では、独自に定義したstr\_list構造体のメモリ確保、初期化、private\_dataへの登録を行います。エラーが発生するのは、メモリ確保に失敗した場合のみです。

```
struct str_list {
  char  *s;
  struct list_head list;
};

static int debimate_open(struct inode *inode, struct file *file)
{
    struct str_list *s_list = NULL;

    pr_info("START: %s\n", __func__);

    /* リスト用のメモリを確保 */
    s_list = kmalloc(sizeof(struct str_list), GFP_KERNEL);
    if(!s_list) {
        pr_err("ERR  : Can't alloc memory(%s)\n", __func__);
        pr_err("ERR  : Can't open debimate(%s)\n", __func__);
        goto MEM_ALLOC_ERR;
    }

    /* Listを初期化し、file(device)毎の個別データにListを渡す。
     * 他のsystemcall(write, readなど)は、private_data経由で、
     * Listを操作する。*/
    INIT_LIST_HEAD(&s_list->list);
    file->private_data = (void *)s_list;

    pr_info("END  : %s\n", __func__);
    return 0;

MEM_ALLOC_ERR:
    return -ENOMEM;
}

```

(Linked) List操作の方法(API)に関しては、別記事でまとめています。これから説明するWrite、Read、Closeでは、List操作を知らないと理解できない内容のため、自身がない方は確認して下さい。

https://debimate.jp/2019/04/07/linux-kernel-list%E6%A7%8B%E9%80%A0%E3%82%92%E6%93%8D%E4%BD%9C%E3%81%99%E3%82%8B%E3%81%9F%E3%82%81%E3%81%AEapilist%E3%81%AE%E4%BD%BF%E3%81%84%E6%96%B9/

\[the\_ad id="598"\]

## Device DriverのWrite処理の作成

Write処理では、以下の処理を行います。

- ユーザが書き込んだ文字列を管理するList用メモリを確保
- ユーザが書き込んだ文字列をコピーするためのメモリを確保
- ユーザが書き込んだ文字列(User空間メモリ)をKernel空間メモリにコピー
- Open関数で作成したリストの末尾に、本関数内で作成したListを挿入

Write関数の引数は順番に、Open関数で作成したListにアクセスするためのfile構造体、User空間からデータを受け取るための変数buf、ユーザが書き込んだデータサイズを表すcount、書き込み位置オフセットの変数f\_posです。

Write処理で用いている関数の中で、Kernel特有の関数はstrncpy\_from\_user()です。User空間とKernel空間では、使用するメモリ領域が違います。strncpy\_from\_user()は、その事を意識して、文字列をコピーしてくれます。

```
static ssize_t debimate_write(struct file *filp, const char __user *buf,
	size_t count, loff_t *f_pos)
{
    int    result           = 0;
    char  *str              = NULL;
    struct str_list *s_list = NULL;
    struct str_list *head   = (struct str_list*)filp->private_data;

	pr_info("START: %s\n", __func__);

    /* リスト用のメモリを確保 */
    s_list = kmalloc(sizeof(struct str_list), GFP_KERNEL);
    if(!s_list) {
        pr_err("ERR  : Can't alloc memory for list(%s)\n", __func__);
        goto LIST_MEM_ALLOC_ERR;
    }

    /* 文字列コピー用のメモリを確保 */
    str = kmalloc(count+1, GFP_KERNEL);
    if(!str) {
        pr_err("ERR  : Can't alloc memory for string(%s)\n", __func__);
        goto STR_MEM_ALLOC_ERR;
    }
    memset(str, '\0', count+1);

    /* ユーザ空間メモリ領域からカーネル空間メモリ領域にデータをコピー */
    result = strncpy_from_user(str, buf, count);
    if(result != count) {
        pr_err("ERR  : Can't copy data from user space to kernel space(%s)\n",
               __func__);
        goto WRITE_DATA_ERR;
    }
    s_list->s = str;
    list_add_tail(&s_list->list ,&head->list); /* リストへ挿入 */

    pr_info("END  : %s\n", __func__);
    return result;

WRITE_DATA_ERR:
    kfree(str);
STR_MEM_ALLOC_ERR:
    kfree(s_list);
LIST_MEM_ALLOC_ERR:
    return -ENOMEM;
}

```

## Device DriverのRead処理の作成

Read処理では、ユーザが読み込みたいByte数をListから取り出し、User空間に文字列をコピーします。

Read関数の引数は、Write関数とほぼ同じです。Open関数で作成したListにアクセスするためのfile構造体、User空間にデータを渡すための変数buf、ユーザが読み込みたいデータサイズを表すcount、読み込み位置オフセットの変数f\_posです。

今回の仕様では、Listの各要素が何Byteの文字列を保持しているか分かりません。そのため、Listの先頭から順番に文字列のサイズを確認します。その後、ユーザが読み込みたいByte数の分だけ、Listを探索し、Listの要素(文字列)を変数strにコピーします。最後に、Kernel空間からUser空間にメモリをコピーするためのcopy\_to\_user()を使用します。なお、copy\_to\_user()の返り値は、読み込んだByte数ではなく、読み込めなかったByte数のため、注意が必要です。

```
static ssize_t debimate_read(struct file *filp, char __user *buf, size_t count,
	loff_t *f_pos)
{
    int     loop_cnt       = 0;
    ssize_t size           = 0;
    ssize_t total_size     = 0;
    char   *str            = NULL;
    char   *str_head       = NULL;
    struct  str_list *itr  = NULL;
    struct  str_list *head = (struct str_list*)filp->private_data;
    unsigned long result   = 0;

    pr_info("START: %s\n", __func__);

    /* 文字列コピー用のメモリを確保 */
    str = kmalloc(count+1, GFP_KERNEL);
    if(!str) {
        pr_err("ERR  : Can't alloc memory for string(%s)\n", __func__);
        goto STR_MEM_ALLOC_ERR;
    }
    memset(str, '\0', count+1);

    /* Listを先頭から順に探索し、リストの要素(文字列)を連結する。
     * 文字列の連結は、ユーザが読み込みたいByte数と一致するまで続く。 */
    str_head = str;
    list_for_each_entry(itr, &head->list, list) {
        size = strlen(itr->s);
        pr_info("loop count=%d: %s is %ld byte\n", loop_cnt, itr->s, size);
        if((total_size += size) > count) {
            strncpy(str, itr->s, (total_size - count));
            total_size = count;
            break;
        }
        strncpy(str, itr->s, size);
        str = str + size;
        loop_cnt++;
    }

    /* ユーザ空間に文字列をコピー */
    result = copy_to_user(buf, str_head, total_size);
    if (result) {
        pr_err("ERR  : Can't copy data to user space(result=%ld)\n",
                result);
        goto COPY_DATA_ERR;
    }
    pr_info("Copy %s from kernel space to user space(result=%ld))\n",
            str_head, result);

    kfree(str_head);
    pr_info("END  : %s\n", __func__);

    return total_size;

COPY_DATA_ERR:
    kfree(str);
STR_MEM_ALLOC_ERR:
    return result;
}

```

## Device DriverのClose処理の作成

Close処理では、「文字列格納用メモリ(Listの要素)の解放」、「Open関数で作成したListから順番に全てのListを削除」、「List用メモリの解放」を行います。

list\_for\_each\_entry\_safe(Listの先頭から順にListを辿るためのAPI)を使用すれば、iterator自身のメモリを開放する事ができるため、以下のように

1. 文字列用バッファの解放
2. Listから要素を削除
3. List用メモリを解放

を順番に行う事ができます。なお、list\_for\_each\_entry(別API)では、iteratorのメモリが開放できません。

```
static int debimate_close(struct inode *inode, struct file *file)
{
    int    loop_cnt       = 0;
    struct str_list *itr  = NULL;
    struct str_list *tmp  = NULL;
    struct str_list *head = (struct str_list*)file->private_data;

    pr_info("START: %s\n", __func__);

    list_for_each_entry_safe(itr ,tmp, &head->list, list){
        pr_info("loop number: %d", loop_cnt);
        kfree(itr->s);
        list_del(&itr->list);
        kfree(itr);
        loop_cnt++;
    }

    pr_info("END  : %s\n", __func__);
    return 0;
}

```

## Device Driverのテストプログラム

今回作成したDevice Driverのテストプログラムとして、ユーザ空間から"/dev/debimate" にアクセスし、"abcde"および"fghij"を書き込みます。その後、10Byteのデータを"/dev/debimate" から読み出し、表示します。

テストプログラム(test.cおよびMakefile)は、以下の通りです。

```
#include <stdio.h>
#include <string.h>

int main() {
    int  result     = 0;
    FILE *fp        = NULL;
    char filename[] = "/dev/debimate";
    char str1[]     = "abcde";
    char str2[]     = "fghij";
    char buf[11]    = {'\0'};

    fp = fopen(filename, "w+");
    if(fp == NULL) {
        perror("fopen");
        return -1;
    }

    result = fwrite(str1, sizeof(char), 5, fp);
    result = fwrite(str2, sizeof(char), 5, fp);
    if(result != 5) {
        perror("fwrite"); /* サンプルのため最後の書き込みのみチェックする */
        fclose(fp);
        return -1;
    }
    printf("Write down \"%s\" and \"%s\" to %s\n",
            str1, str2, filename);

	result = fread(buf, sizeof(char), 10, fp);
    if(result != 10) {
        perror("fread");
        fclose(fp);
        return -1;
    }
    printf("Read \"%s(10byte)\" from %s\n", buf, filename);

    fclose(fp);
    return 0;
}

```

```
CC     = gcc
CFLAGS = -Wall -O2

all:test

test:test.c
	$(CC) $(CFLAGS) -o test test.c

.PHONY: clean
clean:
	rm -f test *.o

```

以下に、実行例を示します。

```
$ pwd                                             
/home/nao/KERNEL/01_char_device

$ tree                                              
.
├── kernel_moduel
│   ├── Makefile
│   └── debimate_module.c
└── test
    ├── Makefile
    └── test.c

$ cd kernel_moduel/
$ make                             (注釈) 今回作成したDevice Driverのビルド
$ sudo insmod debimate_module.ko   (注釈) Device DriverをLoad
$ sudo dmesg | tail -n 2           (注釈) Loadメッセージの確認
[29569.185199] START: debimate_init
[29569.185262] END  : debimate_init

$ cd ../test/ 
$ make                             (注釈) 今回作成したテストプログラムのビルド

$  sudo ./test                     (注釈) テストプログラムの実行
Write down "abcde" and "fghij" to /dev/debimate
Read "abcdefghij(10byte)" from /dev/debimate

$ sudo dmesg | tail -n 11           (注釈) open〜closeまでのシステムコールログ                       
[29628.007046] START: debimate_open
[29628.007047] END  : debimate_open
[29628.007071] START: debimate_write
[29628.007073] END  : debimate_write
[29628.007075] START: debimate_read
[29628.007077] loop count=0: abcdefghij is 10 byte
[29628.007078] Copy abcdefghij from kernel space to user space(result=0))
[29628.007079] END  : debimate_read
[29628.007086] START: debimate_close
[29628.007087] loop number: 0
[29628.007088] END  : debimate_close

$ sudo rmmod debimate_module        (注釈) Device DriverをUnload
$  sudo dmesg | tail -n 2           (注釈) Unloadメッセージを確認
[29976.814936] START: debimate_exit
[29976.815019] END  : debimate_exit

```
