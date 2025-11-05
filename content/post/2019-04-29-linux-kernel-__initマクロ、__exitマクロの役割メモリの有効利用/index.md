---
title: "Linux Kernel: __initマクロ、__exitマクロの役割(メモリの有効利用)"
type: post
date: 2019-04-29
categories:
  - "linux"
tags:
  - "c言語"
  - "debian"
  - "linux"
  - "linuxkernel"
  - "マクロ"
cover:
  image: images/tux.png
  alt: "Linux Kernel: __initマクロ、__exitマクロの役割(メモリの有効利用)"
  hidden: false
images: ["images/tux.png"]
---

## \_\_initマクロ、\_\_exitマクロが使われるケース

一般的に、\_\_initマクロはKernelモジュールの初期化時、\_\_exitマクロはKernelモジュールの終了時に付与します。以下の例では、初期化関数がdebimate\_init()、終了関数がdebimate\_exit()で、それぞれにマクロを付与しています。

```
static int __init debimate_init(void)
{
	int result                  = 0;
	struct device *debimate_dev = NULL;

	pr_info(KERN_INFO "START: %s\n", __func__);

	/* メジャー番号の動的確保 */
	result = alloc_chrdev_region(&dev, MINOR_NR_BASE, MAX_MINOR_NR, DEV_NAME);
	if (0 != result) {
		pr_err("%s: alloc_chrdev_region = %d\n", __func__, result);
		goto REGION_ERR;
	}

	/* デバイスをクラス登録 */
	debimate_class = class_create(THIS_MODULE, DEV_CLASS);
	if(IS_ERR(debimate_class)){
		result = PTR_ERR(debimate_class);
		pr_err("%s: class_create = %d\n", __func__, result);
		goto CREATE_CLASS_ERR;
	}

	/* キャラクターデバイス構造体(cdev構造体)初期化および
	 * システムコールの関数ポインタ登録 */
	cdev_init(&debimate_cdev, &debimate_drv_fops);

	/* キャラクターデバイスをKernelに登録 */
	result = cdev_add(&debimate_cdev, dev, MAX_MINOR_NR);
	if (0 != result) {
		pr_err("%s: cdev_add = %d\n", __func__, result);
		goto CDEV_ADD_ERR;
	}

	/* デバイスノードを作成。作成したノードは/dev以下からアクセス可能 */
	debimate_dev = device_create(debimate_class, NULL, dev, NULL, DEV_NAME,
					MINOR_NR_BASE);
	if (IS_ERR(debimate_dev)) {
		result = PTR_ERR(debimate_dev);
		pr_err("%s: device_create = %d\n", __func__, result);
		goto DEV_CREATE_ERR;
	}
	pr_info(KERN_INFO "Hello, World!\n");
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

static void __exit debimate_exit(void)
{
	pr_info(KERN_INFO "START: %s\n", __func__);

	/* メジャー番号、マイナー番号からdevを得る */
	/* release_dev  = MKDEV(MAJOR(dev), MINOR(dev)); */

	/* デバイスノードの削除 */
	device_destroy(debimate_class, dev);

	/* キャラクターデバイスをKernelから削除 */
	cdev_del(&debimate_cdev);

	/* デバイスのクラス登録を削除 */
	class_destroy(debimate_class);

	/* デバイスドライバが使用していたメジャー番号の登録を解除 */
	unregister_chrdev_region(dev, MAX_MINOR_NR);

	pr_info(KERN_INFO "Goodbye.\n");
	pr_info(KERN_INFO "END  : %s\n", __func__);
}
```

## \_\_initマクロの役割・定義

\_\_initマクロは、メモリ上の初期化関数用の領域に、関数を配置します。そして、\_\_initマクロで指定した関数による初期化が終了後、その初期化関数はメモリ上から破棄(解放)されます。

Kernelモジュールの初期化処理は、通常一度しか呼ばれません。そのため、実行後にメモリから初期化関数を解放した方が、メモリの節約になるという考え方です。

この仕組みを提供している\_\_initマクロの定義は、以下の通りです。

```
#define __init      __section(.init.text) __cold  __latent_entropy __noinitretpoline 

```

\_\_section(.init.text)マクロは、メモリ上の初期化関数用の領域(.init.text)に、関数を配置するための宣言です。通常、コンパイラは、生成したコードを.textセクションに配置します。しかし、\_\_sectionマクロを使う事により、任意のセクションに関数を配置できます。詳細は、[GCCの仕様](https://gcc.gnu.org/onlinedocs/gcc/Common-Function-Attributes.html)に記載されています。

[\_\_coldマクロ](https://gcc.gnu.org/onlinedocs/gcc/Common-Function-Attributes.html#index-cold-function-attribute)は、関数にcold属性を付与します。cold属性は、この属性を付与した関数が実行される可能性が低い事をコンパイラに通知します。cold属性が付与された関数は、速度よりサイズに対して最適化されます。

[\_\_latent\_entropyマクロ](https://lwn.net/Articles/688492/)は、Kernel内部のエントロピーが少ない問題を解決します( エントロピーを増やしてくれます)。エントロピーは、Kernelが質の良い乱数を生成するために、プールされています。初期化時以外にも、キーボード入力やストレージ書き込みなどで発生するHW割込をもとに、予測しづらい情報としてプールされます。このプールが情報量が多く、かつ不確実な内容であれば、 偏りのない乱数が生成できます。

\_\_noinitretpolineマクロは、CPUの脆弱性”[Spectre](https://ja.wikipedia.org/wiki/Spectre)”対策である"[Retpoline](https://pc.watch.impress.co.jp/docs/topic/feature/1176718.html)**"**を利用しない宣言です。初期化コードはSpectreの影響を受けないため、パフォーマンスが低下するRetpolineを避けています。

## \_\_exitマクロの役割・定義

\_\_exitマクロは、\_\_initマクロと同等で、メモリの有効活用を目的としています。メモリ上の終了関数用の領域(.exit.text)に、関数を配置します。その終了関数は、実行後にメモリ上から破棄(解放)されます。

\_\_exitマクロの定義は、以下の通りです。

```
#define __exit          __section(.exit.text) __exitused __cold notrace 

```

\_\_section(.exit.text)マクロは、メモリ上の終了関数用の領域(.exit.text)に、関数のデータを配置するための宣言です。

[\_\_exitusedマクロ](https://www.ibm.com/developerworks/jp/linux/library/l-gcc-hacks/index.html)は、関数が参照されていないように見えても、その関数をオブジェクトファイル内で保持させます。リンク時に、未使用のセクションが削除される場合があるため、その防止です。また、「関数が未使用」という警告を抑えるために用いています。

\_\_coldマクロは、説明済みのため、省略します。

notraceマクロは、解析プログラム(コードカバレッジなど)向けのプロファイル情報を生成しないよう、 \_\_attribute\_\_(([no\_instrument\_function](https://gcc.gnu.org/onlinedocs/gcc-3.1/gcc/Function-Attributes.html)))属性を付与します。
