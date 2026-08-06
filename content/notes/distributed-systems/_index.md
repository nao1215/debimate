---
title: "Distributed Systems"
date: 2026-08-04
draft: false

ShowToc: true
TocOpen: true
hidemeta: false
disableShare: true
ShowBreadCrumbs: true
description: ""
---

分散システムに関する技術ノートです。障害検知・合意・複製・整合性を中心に整理しています。

---

### コンテンツ一覧

#### Failure Detection

| No. | 項目 | カテゴリ |
| --- | --- | --- |
| 1 | [Heartbeat - ノードの死活監視](/notes/distributed-systems/heartbeat/) | 障害検知 |

#### Coordination

| No. | 項目 | カテゴリ |
| --- | --- | --- |
| 1 | [Lease - 期限付きで権利を貸す仕組み](/notes/distributed-systems/lease/) | 協調 |
| 2 | [Quorum - 過半数で決定を成立させる仕組み](/notes/distributed-systems/quorum/) | 協調 |

#### Durability

| No. | 項目 | カテゴリ |
| --- | --- | --- |
| 1 | [WAL - 書き込み先行ログと 2 つのウォーターマーク](/notes/distributed-systems/write-ahead-log/) | 耐久性 |

---

### 参考文献（手元にある書籍）

- [分散システムのためのデザインパターン](https://www.maruzen-publishing.co.jp/book/b10134955.html)
- [分散システムデザインパターン―コンテナを使ったスケーラブルなサービスの設計](https://www.oreilly.co.jp/books/9784873118758/)
- [ソフトウェアアーキテクチャ・ハードパーツ―分散アーキテクチャのためのトレードオフ分析](https://www.oreilly.co.jp//books/9784814400065/)
- [プログラミング・ビットコイン―ゼロからビットコインをプログラムする方法](https://www.oreilly.co.jp/books/9784873119021/)
- [詳解 ビットコイン―ゼロから設計する過程で学ぶデジタル通貨システム](https://www.oreilly.co.jp/books/9784873119083/)
- [データ指向アプリケーションデザイン―信頼性、拡張性、保守性の高い分散システム設計の原理](https://www.oreilly.co.jp/books/9784873118703/)
