---
title: "Linux Kernel: エラー番号の一覧"
type: post
date: 2019-02-24
categories:
  - "linux"
tags:
  - "c言語"
  - "linux"
  - "linuxkernel"
cover:
  image: "images/mistake-3085712_640.jpg"
  alt: "Linux Kernel: エラー番号の一覧"
  hidden: false
---

### 前書き

本記事では、Linux Kernelが用いるエラー番号を説明します。

---


### Linux Kernelがエラー番号（errno）を正しく返す意義

Linux Kernelでは、エラーの種類に応じて、返すべきエラー番号が定められています。例えば、ファイルが存在しない場合は、"ENOENT(No such file or directory、 エラー番号2)"を返します。Linux Kernel内のエラー内容は、変数errnoを通してUser空間にも伝わります。

Linux Kernel内で誤ったエラー番号を使用した場合、その影響は広範囲に渡ります。Kernel空間は勿論ですが、User空間アプリケーションに本来であれば不要であった判断や対応を強いる事になります。さらに、エラー番号の誤りに気づき、Kernelコードを修正した後もまた、Kernel空間/User空間の両方に影響が出ます。

すなわち、他の人に迷惑をかけないために、Linux Kernelコード内で定義されたエラー番号を正しく使う事が重要になります。ちなみに、Linux Kernelのエラー番号は、以下の特徴があります。

特徴

- FreeBSD Kernelよりもエラー番号が多い事
- Linux Kernel内専用のエラー番号がある事

\[the\_ad id="598"\]

---


### エラー番号の定義ファイル

エラー番号の定義ファイルは、下表の３種類存在します。それぞれのファイルに定義されたエラー番号の意味も後述します（表の中だけ、である調にします）。

| **PATH** | **内容** |
| --- | --- |
| <KERNEL\_TOP>/include/uapi/asm-generic/errno-base.h | ファイル・リソースの基本的なエラー状態を説明するためのエラー番号（1〜34） |
| <KERNEL\_TOP>/include/uapi/asm-generic/errno.h | errno-base.hで表しきれなかったエラー状態を説明するためのエラー番号（35〜133） |
| <KERNEL\_TOP>/include/linux/errno.h | Kernel空間のみで使用するエラー番号（512〜518、521〜530） |

| <KERNEL\_TOP>/include/uapi/asm-generic/errno-base.h |  |  |  |
| --- | --- | --- | --- |
| 名称 | 値 | 原文 | 和訳 |
| EPERM | 1 | Operation not permitted | 許可されていない操作である |
| ENOENT | 2 | No such file or directory | ファイルまたはディレクトリが存在しない |
| ESRCH | 3 | No such process | 指定されたプロセスが存在しない |
| EINTR | 4 | Interrupted system call | シグナル割り込みが発生した |
| EIO | 5 | I/O error | 入出力エラーである |
| ENXIO | 6 | No such device or address | デバイスまたはアドレスが存在しない |
| E2BIG | 7 | Argument list too long | 引数リストが長すぎる |
| ENOEXEC | 8 | Exec format error | 実行形式が異常である |
| EBADF | 9 | Bad file number | 無効（異常）なファイル番号 |
| ECHILD | 10 | No child processes | 子プロセスが存在しない |
| EAGAIN | 11 | Try again |   再実行する事（EWOULDBLOCKも同じ番号）   |
| ENOMEM | 12 | Out of memory | メモリー不足である |
| EACCES | 13 | Permission denied | 権限が無い |
| EFAULT | 14 | Bad address | 無効なアドレス |
| ENOTBLK | 15 | Block device required | ブロックデバイスが必要である |
| EBUSY | 16 | Device or resource busy | デバイスまたはリソースは使用中である |
| EEXIST | 17 | File exists | ファイルは既に存在する |
| EXDEV | 18 | Cross-device link | デバイスをまたぐリンクである |
| ENODEV | 19 | No such device | デバイスが存在しない |
| ENOTDIR | 20 | Not a directory | ディレクトリではない |
| EISDIR | 21 | Is a directory | ディレクトリである |
| EINVAL | 22 | Invalid argument | 無効な引数である |
| ENFILE | 23 | File table overflow | オープン済ファイル（ファイルディスクリプタ）がシステム上限に達している |
| EMFILE | 24 | Too many open files | 開いているファイルが多すぎる |
| ENOTTY | 25 | Not a typewriter | TTYではない |
| ETXTBSY | 26 | Text file busy | テキストファイルが使用中である |
| EFBIG | 27 | File too large | ファイルが大きすぎる |
| ENOSPC | 28 | No space left on device | デバイスの空き領域が不足している |
| ESPIPE | 29 | Illegal seek | 無効なシークである |
| EROFS | 30 | Read-only file system | リードオンリーファイルシステムである |
| EMLINK | 31 | Too many links | リンクの数が多すぎる |
| EPIPE | 32 | Broken pipe | パイプが壊れている（既にクライアントでcloseされている状態など） |
| EDOM | 33 | Math argument out of domain of func | 数値引数が領域外である |
| ERANGE | 34 | Math result not representable | 結果が大き過ぎる |

| <KERNEL\_TOP>/include/uapi/asm-generic/errno.h |  |  |  |
| --- | --- | --- | --- |
| 名称 | 値 | 原文 | 和訳（補足説明） |
| EDEADLK | 35 | Resource deadlock would occur |   リソースデッドロックが発生する見込みである。（EDEADLOCKでも定義されている）Kernel内部のデッドロック検知システム[lockdep](http://www.intellilink.co.jp/article/column/oss16.html)などで、デッドロック検知時に使われる。   |
| ENAMETOOLONG | 36 | File name too long | ファイル名が長過ぎる |
| ENOLCK | 37 | No record locks available | 利用できるレコードロックが無い |
| ENOSYS | 38 | Function not implemented | 関数（system call）は実装されていない。本当に関数が存在しないかどうかを判断するために、system callの実装内で、このエラー番号は使うべきでない。 |
| ENOTEMPTY | 39 | Directory not empty | ディレクトリーが空ではない |
| ELOOP | 40 | Too many symbolic links encountered | シンボリックリンクの回数が多すぎる |
| ENOMSG | 42 | No message of desired type | 要求された型のメッセージが無い |
| EIDRM | 43 | Identifier removed | 識別子は削除された |
| ECHRNG | 44 | Channel number out of range | チャンネル番号が範囲外である |
| EL2NSYNC | 45 | Level 2 not synchronized | 同期できていない (レベル2) |
| EL3HLT | 46 | Level 3 halted | 停止 (レベル3) |
| EL3RST | 47 | Level 3 reset | リセット (レベル3) |
| ELNRNG | 48 | Link number out of range | リンク番号が範囲外である |
| EUNATCH | 49 | Protocol driver not attached | プロトコルドライバが[アタッチ](https://www.wdic.org/w/TECH/%E3%82%A2%E3%82%BF%E3%83%83%E3%83%81 "アタッチ")されていない |
| ENOCSI | 50 | No CSI structure available | CSI構造が利用できない |
| EL2HLT | 51 | Level 2 halted | 停止 (レベル2) |
| EBADE | 52 | Invalid exchange | 不正な交換である |
| EBADR | 53 | Invalid request descriptor | 無効な要求ディスクリプターである |
| EXFULL | 54 | Exchange full | 変換テーブルが一杯である |
| ENOANO | 55 | No anode | inodeが無い（[諸説があるエラー番号](https://unix.stackexchange.com/questions/167368/what-is-enoano-no-anode-intended-to-be-used-for)） |
| EBADRQC | 56 | Invalid request code | 不正なリクエストコードである |
| EBADSLT | 57 | Invalid slot | 不正なスロットである |
| EBFONT | 59 | Bad font file format | 不正なフォントファイルフォーマットである |
| ENOSTR | 60 | Device not a stream | ストリームではない |
| ENODATA | 61 | No data available | データが無い |
| ETIME | 62 | Timer expired | 時間が経過した（時間による失効） |
| ENOSR | 63 | Out of streams resources | ストリームリソースが存在しない |
| ENONET | 64 | Machine is not on the network | 装置がネットワーク上に無い |
| ENOPKG | 65 | Package not installed | パッケージがインストールされていない |
| EREMOTE | 66 | Object is remote | オブジェクトがリモートにある |
| ENOLINK | 67 | Link has been severed | リンクが切れている |
| EADV | 68 | Advertise error | Advertiseエラー |
| ESRMNT | 69 | Srmount error | Srmountエラー |
| ECOMM | 70 | Communication error on send | 送信時に通信エラーが発生した |
| EPROTO | 71 | Protocol error | プロトコルエラーである |
| EMULTIHOP | 72 | Multihop attempted | マルチホップが試みられた |
| EDOTDOT | 73 | RFS specific error | RFS特有のエラーである |
| EBADMSG | 74 | Not a data message | データメッセージではない |
| EOVERFLOW | 75 | Value too large for defined data type | データ型に格納するには値が大きすぎる |
| ENOTUNIQ | 76 | Name not unique on network | 名前がネットワークで一意ではない |
| EBADFD | 77 | File descriptor in bad state | ファイルディスクリプターが不正な状態である |
| EREMCHG | 78 | Remote address changed | リモートアドレスが変わった |
| ELIBACC | 79 | Can not access a needed shared library | 必要な共有ライブラリにアクセスできない |
| ELIBBAD | 80 | Accessing a corrupted shared library | 壊れた共有ライブラリにアクセスをした |
| ELIBSCN | 81 | .lib section in a.out corrupted | .libセクションが壊れている |
| ELIBMAX | 82 | Attempting to link in too many shared libraries | リンクしようとした共有ライブラリが多過ぎる |
| ELIBEXEC | 83 | Cannot exec a shared library directly | 共有ライブラリを直接実行できなかった |
| EILSEQ | 84 | Illegal byte sequence | 不正なバイト列である |
| ERESTART | 85 | Interrupted system call should be restarted | 中断[システムコール](https://www.wdic.org/w/TECH/%E3%82%B7%E3%82%B9%E3%83%86%E3%83%A0%E3%82%B3%E3%83%BC%E3%83%AB "システムコール")は再起動が必要である |
| ESTRPIPE | 86 | Streams pipe error | ストリームパイプエラー |
| EUSERS | 87 | Too many users | ユーザー数が多過ぎる |
| ENOTSOCK | 88 | Socket operation on non-socket | ソケットではない |
| EDESTADDRREQ | 89 | Destination address required | 宛先のアドレスが必要 |
| EMSGSIZE | 90 | Message too long | メッセージが長過ぎる |
| EPROTOTYPE | 91 | Protocol wrong type for socket | ソケットに指定できないプロトコルタイプである |
| ENOPROTOOPT | 92 | Protocol not available | 利用できないプロトコルである |
| EPROTONOSUPPORT | 93 | Protocol not supported | 未対応のプロトコルである |
| ESOCKTNOSUPPORT | 94 | Socket type not supported | 未対応のソケットタイプである |
| EOPNOTSUPP | 95 | Operation not supported on transport endpoint | トランスポートエンドポイントで未対応の操作 |
| EPFNOSUPPORT | 96 | Protocol family not supported | 対応していないプロトコルファミリーである |
| EAFNOSUPPORT | 97 | Address family not supported by protocol | 対応していないアドレスファミリーである |
| EADDRINUSE | 98 | Address already in use | アドレスは既に使用されている |
| EADDRNOTAVAIL | 99 | Cannot assign requested address | アドレスが使用できない |
| ENETDOWN | 100 | Network is down | ネットワークは不通である |
| ENETUNREACH | 101 | Network is unreachable | ネットワークは到達不能である |
| ENETRESET | 102 | Network dropped connection because of reset | リセットでネットワーク接続が失われた |
| ECONNABORTED | 103 | Software caused connection abort | ソフトウェア要求により接続は中止された |
| ECONNRESET | 104 | Connection reset by peer | 接続は相手からリセットされた |
| ENOBUFS | 105 | No buffer space available | バッファーは容量不足である |
| EISCONN | 106 | Transport endpoint is already connected | トランスポートエンドポイントは既に接続されている |
| ENOTCONN | 107 | Transport endpoint is not connected | トランスポートエンドポイントは接続されていない |
| ESHUTDOWN | 108 | Cannot send after transport endpoint shutdown | トランスポートエンドポイントはシャットダウン中であり送信できない |
| ETOOMANYREFS | 109 | Too many references: cannot splice | 処理限界を超える多重参照である |
| ETIMEDOUT | 110 | Connection timed out | 操作はタイムアウトした |
| ECONNREFUSED | 111 | Connection refused | 接続は拒否された |
| EHOSTDOWN | 112 | Host is down | ホストはダウンしている |
| EHOSTUNREACH | 113 | No route to host | ホストに到達不能である |
| EALREADY | 114 | Operation already in progress | 操作は既に実行中である |
| EINPROGRESS | 115 | Operation now in progress | 操作は現在実行中である |
| ESTALE | 116 | Stale NFS file handle | NFSファイルハンドルが古い |
| EUCLEAN | 117 | Structure needs cleaning | 構造のクリーニングが必要である |
| ENOTNAM | 118 | Not a XENIX named type file | XENIX名前付きファイルではない |
| ENAVAIL | 119 | No XENIX semaphores available | XENIXセマフォは利用できない |
| EISNAM | 120 | Is a named type file | 名前付きファイルである |
| EREMOTEIO | 121 | Remote I/O error | リモートI/Oエラーである |
| EDQUOT | 122 | Quota exceeded | クォータ超過である |
| ENOMEDIUM | 123 | No medium found | メディアが見つからない |
| EMEDIUMTYPE | 124 | Wrong medium type | 間違ったメディアタイプである |
| ECANCELED | 125 | Operation Canceled | 処理はキャンセルされた |
| ENOKEY | 126 | Required key not available | 要求された鍵が利用できない |
| EKEYEXPIRED | 127 | Key has expired | 鍵の期限が切れた |
| EKEYREVOKED | 128 | Key has been revoked | 鍵が無効となった |
| EKEYREJECTED | 129 | Key was rejected by service | 鍵がサーバーにより拒否された |
| EOWNERDEAD | 130 | Owner died | 所有者が死亡した |
| ENOTRECOVERABLE | 131 | State not recoverable | 状態は回復不能である |
| ERFKILL | 132 | Operation not possible due to RF-kill | RF-killのため操作できない |
| EHWPOISON | 133 | Memory page has hardware error | メモリページはHWエラーがあります。 |

\[the\_ad id="598"\]

| <KERNEL\_TOP>/include/linux/errno.h |  |  |  |
| --- | --- | --- | --- |
| 名称 | 値 | 原文 | 和訳（補足説明） |
| ERESTARTSYS | 512 |   (無し)   | [system callが再起動可能である事を示す](https://stackoverflow.com/questions/9576604/what-does-erestartsys-used-while-writing-linux-driver) |
| ERESTARTNOINTR | 513 | (無し) | systemcallを必ず再実行する |
| ERESTARTNOHAND | 514 |  restart if no handler. | ハンドラが無ければ再実行する  |
| ENOIOCTLCMD | 515 |  No ioctl command | ioctl() が存在しない |
| ERESTART\_RESTARTBLOCK | 516 | restart by calling sys\_restart\_syscall | sys\_restart\_syscall()によって、再実行する |
| EPROBE\_DEFER | 517 | Driver requests probe retry | ドライバはprobe（探査、初期化）の再実行を要求している |
| EOPENSTALE | 518  | open found a stale dentry |   古いdentryを発見した（Openした）   |
| EBADHANDLE | 521  |  Illegal NFS file handle |  不正なNFSファイルハンドラである |
| ENOTSYNC | 522  | Update synchronization mismatch |  更新同期の不一致である |
| EBADCOOKIE | 523  | Cookie is stale | Cookieが古い  |
| ENOTSUPP | 524 | Operation is not supported | その操作はサポートしていない  |
| ETOOSMALL  | 525  | Buffer or request is too small | バッファかリクエストが小さすぎる  |
| ESERVERFAULT | 526 | An untranslatable error occurred  | 翻訳（変換）できないエラーが発生した  |
| EBADTYPE  | 527  | Type not supported by server | サーバによって、その型がサポートされていない  |
| EJUKEBOX | 528  | Request initiated, but will not complete before timeout | リクエストは開始されたが、タイムアウトまでに完了しなかった |
| EIOCBQUEUED | 529 | iocb queued, will get completion event |  iocbがキューに入れられ、完了イベントが取得される |
| ERECALLCONFLICT | 530  | conflict with recalled state |  再呼び出し状態での衝突である |

---


### 補足：User空間でKernel空間のエラー番号を見る方法

User空間には、Kernel空間のエラー番号を示すerrnoが存在します。以下に[errnoに関するMANページ情報](https://linuxjm.osdn.jp/html/LDP_man-pages/man3/errno.3.html)を引用します。

> ヘッダーファイル _<[errno.h](file:///usr/include/errno.h)\>_ で整数型の変数 _errno_ が定義されており、 システムコールやいくつかのライブラリ関数は、エラーが発生した際に この変数にその原因を示す値を設定する。 この値は呼び出しの返り値がエラー (ほとんどのシステムコールでは -1 で、ほとんどのライブラリ関数では -1 か NULL) を示したときに のみ意味を持つが、ライブラリ関数は成功した場合も _errno_ を変更することが許されている。
> 
> 有効なエラー番号はいずれも 0 以外の値を持つ。 どのシステムコールもライブラリ関数も _errno_ を 0 に設定することはない。

この変数errnoの取り扱いで、注意すべきポイントが2つあります。

ポイント

- 関数コール前にerrnoを初期化（エラー番号をセット後、その番号を保持し続けるため）
- 関数コール後にerrno値を別変数にコピー（errnoは一つしかなく、書き換わる可能性があるため）

以下に、存在しないファイルをOpenしようとし、エラーが発生するサンプルプログラム（および実行結果）を示します。プログラム中で使用している関数perror()は、変数errnoに格納されたエラー番号とメッセージを対応付け、メッセージを標準エラー出力に書き出します。

```
#include <stdio.h>
#include <errno.h>

int main(void){
    FILE *fp      = NULL;
    char  fname[] = "no_exist_file.txt"; /* 存在しないファイル */
    int   err     = 0;

    /* お作法：関数呼び出し前、既にerrnoが設定されている可能性があります。
     * 　　　　errnoを確認する場合は、事前初期化をします。
     * 　　　　（今回の例では、fopen()前に関数がないので、本当は不要）*/
    errno = 0;
    fp = fopen(fname, "r");
    if(NULL == fp) {
        /* お作法：errnoは書き換えられる可能性があるため、
         * 　　　　ローカル変数にコピー。（今回の例では、本当は不要な処理）*/
        err = errno;
        perror(NULL); /* エラーを説明する文章を出力 */
        printf("Error No. = %d\n", err);
        return -1;
    }
    fclose(fp);
    return 0;
}
```

```
$ gcc -o test test.c 
$ ./test 
No such file or directory
Error No. = 2

```
