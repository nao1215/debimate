---
title: "Linux Kernel: mutex APIによるロック(排他)方法"
type: post
date: 2019-07-07
categories:
  - "linux"
tags:
  - "c言語"
  - "debian"
  - "linux"
  - "linuxkernel"
cover:
  image: "images/mutex2.jpg"
  alt: "Linux Kernel: mutex APIによるロック(排他)方法"
  hidden: false
---

## 前書き：mutexとは

Linux Kernelに限らず、様々なプログラミング言語やライブラリはロック機構を提供しています。ロック機構は、複数のプロセスが同時に共有データを書き換え、意図しないデータ状態となる事を防ぎます。代表的なロック機構には、

- spinlock
- semaphore
- mutex

があります。

今回説明するmutex(Mutal Exclusion)は、一つのプロセス(スレッド)だけが共有リソースにアクセスする事を許可するロック機構です。Device Driverで用いるロック機構ではデファクトスタンダード扱いです。その理由は、他のロック機構がデメリット(以下)があるからです。

- spinlockはロック解放待ち(ビジーウェイト)でCPUリソースを消費
    - ただし、割り込みコンテキストではspinlockを使用(mutexはデッドロックが発生する可能性あり)
- semaphoreは共有データに複数プロセスが同時アクセス可能(ロック獲得条件が緩い)

本記事では、mutexを使用する上での注意点を述べた後に、Linux Kernelのmutex APIについて説明していきます。

## mutexを使用する上での注意点

Linux Kernelソースコードのinclude/linux/mutex.hには、mutexを使用する上での注意点(以下の箇条書き)が記載されています。User空間でも同じようなノウハウ(注意点)があると思いますが、赤字部分はHardwareを考慮した注意事点(Kernel空間ならではの注意点)です。

> - 一度に、一つのタスクだけがmutexを保持可能
> - mutex所有者のみがロックを解除可能
> - 複数のロック解除は許可されていない
> - 再帰的なロックは許可されていない
> - mutexオブジェクト(mutex用の構造体)は、API経由で初期化する事
> - mutexオブジェクトは、memset()やコピーによる初期化をしてはいけない
> - タスク(プロセス)は、mutex(ロック)を保持した状態で終了してはいけない
> - ロック獲得したままのメモリ領域は、解放(free)してはいけない
> - 獲得されたmutex(使用中のmutex)は、再初期化してはいけない
> - mutexは、taskletsやtimerのようなHW/SWのIRQ(割り込み)コンテキストで使用不可
>     - 理由：割り込みハンドラがロック中のmutexを獲得しようとするとデッドロック発生するため

## Linux Kernel mutex構造体

mutex構造体は、include/linux/mutex.hに定義が存在します。mutex APIを使う上でmutex内部の仕組みを知る必要はありませんが、簡単に説明します。

```
struct mutex {
	/* 1: unlocked, 0: locked, negative: locked, possible waiters */
	atomic_t		count;
	spinlock_t		wait_lock;
	struct list_head	wait_list;
#if defined(CONFIG_DEBUG_MUTEXES) || defined(CONFIG_MUTEX_SPIN_ON_OWNER)
	struct task_struct	*owner;
#endif
#ifdef CONFIG_MUTEX_SPIN_ON_OWNER
	struct optimistic_spin_queue osq; /* Spinner MCS lock */
#endif
#ifdef CONFIG_DEBUG_MUTEXES
	void			*magic;
#endif
#ifdef CONFIG_DEBUG_LOCK_ALLOC
	struct lockdep_map	dep_map;
#endif
};

```

| mutex構造体のメンバ変数 | 役割 |
| --- | --- |
| atomic\_t count | atomic\_t構造体(中身はint型のcounter)としてmutexの状態を管理します。1=アンロック状態、0=ロック状態。 |
| spinlock\_t wait\_lock | mutex内部で、mutex獲得待ちのタスクを起床(wake up)させる場合などに、spinlockを使用します。 |
| struct list\_head wait\_list | mutex獲得待ちのタスクをList形式で管理します。Linux Kernel内のListの仕組みに関しては、[本サイトに説明記事](https://debimate.jp/post/2019-04-07-linux-kernel-list%E6%A7%8B%E9%80%A0%E3%82%92%E6%93%8D%E4%BD%9C%E3%81%99%E3%82%8B%E3%81%9F%E3%82%81%E3%81%AEapilist%E3%81%AE%E4%BD%BF%E3%81%84%E6%96%B9/)があります。 |
| struct task\_struct \*owner; | mutex構造体を管理(使用)するタスクを意味します。 |
| struct optimistic\_spin\_queue osq | Mutex獲得時のMCSロック(スピン)機能が有効の場合、使用します。MCSロック機能では、1）他のCPUがmutexの所有者、2）タスクの再スケジューリングが不要、の条件を共に満たした場合、ロック獲得(※)のためにスピンして待ち続けます 。※他のCPUが処理実行中のため、直ぐにロックが解放される可能性があります。 |
| void \*magic | mutexのセマンティックス違反やデッドロックを検知する場合に使用します。 |
| struct lockdep\_map dep\_map | lockdep機能(ロック獲得順番などの正当性チェッカ)で用いるロック依存関係マップです。 |

## Linux Kernel mutexの初期化(動的)

Linux Kernel内で、動的にmutexを初期化する場合、mutex\_initマクロを使用します。初期化例は、以下の通りです。

```
struct mutex __mutex;
mutex_init(&__mutex);

```

mutex\_initマクロは、以下の実装の通り、各APIの初期化関数をコールしているだけです。途中で登場するlock\_class\_key構造体は、lockdep機能におけるロッククラス(ロック規則に関して論理的に同じロックのグループ)に対して、一意(ユニーク)のアドレスを割り当てるために存在します。

```
# define mutex_init(mutex) \ 
do {                            \
    static struct lock_class_key __key;     \ 
                            \ 
    __mutex_init((mutex), #mutex, &__key);      \
} while (0)

```

```
void
__mutex_init(struct mutex *lock, const char *name, struct lock_class_key *key) 
{  
      atomic_set(&lock->count, 1); 
      spin_lock_init(&lock->wait_lock); 
      INIT_LIST_HEAD(&lock->wait_list); 
      mutex_clear_owner(lock); 
  #ifdef CONFIG_MUTEX_SPIN_ON_OWNER 
      osq_lock_init(&lock->osq); 
  #endif                                                                                 
                                                                                         
      debug_mutex_init(lock, name, key); 
  } 

```

## Linux Kernel mutexの初期化(静的)

Linux Kernel内で、静的にmutexを初期化する場合、DEFINE\_MUTEXマクロを使用します。ここでの静的とは、mutexの変数宣言時という意味です。DEFINE\_MUTEXマクロをコールすると、新しいmutex構造体(\_\_mutex)が作成され、初期化済みになります。初期化例は、以下の通りです。

```
DEFINE_MUTEX(__mutex);

```

DEFINE\_MUTEXマクロの定義は、include/linux/mutex.hにあり、以下の通りです。mutexの初期化処理としては、sponlockやlistなどの各APIにおける静的初期化処理をコールしているだけです。

```
#define __MUTEX_INITIALIZER(lockname) \                                                
        { .count = ATOMIC_INIT(1) \                                                    
        , .wait_lock = __SPIN_LOCK_UNLOCKED(lockname.wait_lock) \                      
        , .wait_list = LIST_HEAD_INIT(lockname.wait_list) \                            
        __DEBUG_MUTEX_INITIALIZER(lockname) \                                          
        __DEP_MAP_MUTEX_INITIALIZER(lockname) }  

#define DEFINE_MUTEX(mutexname) \                                                      
    struct mutex mutexname = __MUTEX_INITIALIZER(mutexname)  

```

## mutex(ロック)獲得およびmutex(ロック)解放

mutex獲得にはmutex\_lock()、mutex解放にはmutex\_unlock()を用います。mutex\_lock()はmutexを獲得できれば処理を継続しますが、mutexを獲得できなければ獲得できる状態になるまでスリープします。どちらのケースも、mutex\_lock()の処理が終了した後では、mutexを獲得した状態になっています。

以下に実行例を示します。

```
struct mutex __mutex;
mutex_init(&__mutex);

mutex_lock(&__mutex);
/* ここに共有リソースへのアクセス処理を記載 */
mutex_unlock(&__mutex);

```

\[the\_ad id="598"\]

## mutex(ロック)の状態をチェック

mutexの獲得はせず、mutex(ロック)の状態を調べたい場合、mutex\_is\_locked()を使用します。返り値が1の場合は他のタスクがmutexを獲得中(ロック状態)、0の場合はどのタスクもmutexを獲得していません(アンロック状態)。

以下に実行例を示します。

```
struct mutex __mutex;
mutex_init(&__mutex);

if(mutex_is_locked(&__mutex)) {
    /* ロック中 */
} else {
    /* アンロック中 */
}

```

## mutex獲得を試み、獲得失敗時はスリープしない

mutexの獲得失敗時、mutex\_lock()のようにスリープ状態に移行せず、そのまま処理を継続するには、mutex\_trylock()を使用します。mutex\_trylock()は、mutexの獲得成功時には1を返し、獲得失敗時は0を返します。

以下に実行例を示します。

```
struct mutex __mutex;
mutex_init(&__mutex);

if(mutex_trylock(&__mutex)) {
    /* ロック中 */
} else {
    /* ロック獲得に失敗したため、別の処理を実行 */
}

```

## 割り込み可能なスリープでmutex獲得を待機

mutex(ロック)獲得中に割り込みが発生し、mutex(ロック)獲得処理の呼び出し元がスリープ状態になる場合、mutex\_lock\_interruptible()を使用します。mutex\_lock\_interruptible()は、mutexの獲得成功時には1を返し、ロック獲得を試みている最中にシグナルによって中断された場合は-EINTRを返します。

ユーザコンテキストで処理が制御される場合、ユーザが急に処理を中断("Ctrl+C"="SIGINT")する可能性があるため、mutex\_lock()ではなくmutex\_lock\_interruptible()を使用します。mutex\_lock()は、Ctrl+Cなどのシグナルが発生した場合も、スリープし続けます。

以下に実行例を示します。

```
struct mutex __mutex;
mutex_init(&__mutex);

if(!mutex_lock_interruptible(&__mutex)) {
    /* ロック中 */
} else {
    /* シグナルにより、mutex獲得が中断 */
}

```

## mutex獲得待機タスクのKILLを検出

mutex獲得待機タスクがKILLされた事を検出するには、mutex\_lock\_killable()を使用します。前述のmutex\_lock\_interruptible()は複数のシグナルを検出しますが、その一方でmutex\_lock\_killable()はタスク(プロセス)を終了させるSIGKILL(および他の重要なシグナル)を検出します(Ctrl+Cは、SIGKILLではなくSIGINT)。

mutex\_lock\_interruptible()は、mutex 獲得待ちの間に重要なシグナルを受信した場合、シグナル処理を優先するため、現在実行中のmutex 獲得待ちタスクをmutex獲得待ちリストから削除します。返り値は、mutexが獲得成功時に0、それ以外のケースは状況に応じたERROR番号(-EALREADY、-EINTR、-EDEADLK)です。

以下に実行例を示します。

```
struct mutex __mutex;
mutex_init(&__mutex);

if(!mutex_lock_killable(&__mutex)) {
    /* ロック中 */
} else {
    /* シグナルにより、mutex獲得が中断 */
}

```
