---
title: "Blockchain Systems"
date: 2026-08-08
draft: false
weight: 60
cardLabel: "ブロックチェーン"
cardNote: "ブロックチェーンを構成・接続する技術のノート"

ShowToc: true
TocOpen: true
hidemeta: false
disableShare: true
ShowBreadCrumbs: true
description: ""
---

---

### コンテンツ一覧

#### Introduction

| No. | 項目 | カテゴリ |
| --- | --- | --- |
| 1 | [Blockchain Basics - 中央管理者なしで同じ履歴を共有する](/notes/blockchain-systems/blockchain-basics/) | 導入 / 全体像 |
| 2 | [Bitcoin Transaction Lifecycle - 送金がブロックへ入るまで](/notes/blockchain-systems/bitcoin-transaction-lifecycle/) | 導入 / 取引の流れ |

#### Cryptography

| No. | 項目 | カテゴリ |
| --- | --- | --- |
| 1 | [Hash Function - 改竄の検出を支える 3 つの耐性](/notes/blockchain-systems/hash-function/) | ハッシュ関数 |
| 2 | [Digital Signature - 秘密鍵で作り公開鍵で検証する証明](/notes/blockchain-systems/digital-signature/) | デジタル署名 |

#### Transaction

| No. | 項目 | カテゴリ |
| --- | --- | --- |
| 1 | [UTXO - 未使用の取引出力でコインを表すモデル](/notes/blockchain-systems/utxo/) | 取引 / UTXO |
| 2 | [Bitcoin Script - 出力の使う条件を書くスタック言語](/notes/blockchain-systems/bitcoin-script/) | 取引 / スクリプト |
| 3 | [Ethereum Account Model - 残高と通し番号を状態として持つモデル](/notes/blockchain-systems/ethereum-account-model/) | 取引 / アカウントモデル |
| 4 | [Ethereum Transaction - 署名された実行の依頼と手数料の上限](/notes/blockchain-systems/ethereum-transaction/) | 取引 / gas と署名 |

#### Data Structure

| No. | 項目 | カテゴリ |
| --- | --- | --- |
| 1 | [Bitcoin Block - 取引をまとめてチェーンにする単位](/notes/blockchain-systems/bitcoin-block/) | ブロック / チェーン構造 |
| 2 | [Merkle Tree - ハッシュ木で包含を証明する](/notes/blockchain-systems/merkle-tree/) | ハッシュ木 / 包含証明 |
| 3 | [Bitcoin Merkle Tree - txid の木と SPV による検証](/notes/blockchain-systems/bitcoin-merkle-tree/) | 包含証明 / SPV |
| 4 | [Merkle Tree Design - 構築規則が決める安全性と証明能力](/notes/blockchain-systems/merkle-tree-design/) | ハッシュ木 / 設計 |

#### Consensus

| No. | 項目 | カテゴリ |
| --- | --- | --- |
| 1 | [Proof of Work - 計算作業をブロック追加の条件にする](/notes/blockchain-systems/proof-of-work/) | 作業証明 |
| 2 | [Finality - ブロックチェーンの取引はいつ確定したと言えるのか](/notes/blockchain-systems/finality/) | 確定性 / reorg |

#### Node Policy

| No. | 項目 | カテゴリ |
| --- | --- | --- |
| 1 | [Mempool - 未確認取引の置き場とノードごとの受け入れ方針](/notes/blockchain-systems/mempool/) | 未確認取引 / policy |

---

### 参考文献

#### 手元にある書籍

- [プログラミング・ビットコイン―ゼロからビットコインをプログラムする方法](https://www.oreilly.co.jp/books/9784873119021/)
- [詳解 ビットコイン―ゼロから設計する過程で学ぶデジタル通貨システム](https://www.oreilly.co.jp/books/9784873119083/)
- [ブロックチェーン技術概論　理論と実践](https://www.kodansha.co.jp/book/products/0000353684)
- [デジタルアイデンティティのすべて―安全かつユーザー中心のアイデンティティシステムを実現するための知識](https://www.oreilly.co.jp/books/9784814400980/)
- [ゼロ知識証明入門](https://www.shoeisha.co.jp/book/detail/9784798170992)
- [暗号技術入門 第3版 秘密の国のアリス](https://www.sbcr.jp/product/4797382228/)
- [実務論点 ブロックチェーンの法務: 暗号資産と電子決済手段](https://www.kodansha.co.jp/book/products/0000353684)
- [ビットコイン・スタンダード お金が変わると世界が変わる](https://www.minervashobo.co.jp/book/b577558.html)

#### GitHub で公開されている書籍

- [Mastering Bitcoin: Programming the Open Blockchain（第3版）](https://github.com/bitcoinbook/bitcoinbook)
- [Mastering Ethereum（第2版）](https://github.com/ethereumbook/ethereumbook)
- [Mastering the Lightning Network（第1版）](https://github.com/lnbook/lnbook)

#### 主要な公式仕様・標準

- [Bitcoin Improvement Proposals（BIPs）](https://github.com/bitcoin/bips)
- [Ethereum Improvement Proposals（EIPs）](https://github.com/ethereum/EIPs) / [Ethereum Request for Comments（ERCs）](https://github.com/ethereum/ERCs)
- [Ethereum Execution Layer Specifications](https://github.com/ethereum/execution-specs) / [Ethereum Consensus Specifications](https://github.com/ethereum/consensus-specs) 
- [Lightning Network Specifications（BOLTs）](https://github.com/lightning/bolts)
