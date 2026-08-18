---
title: "Software Architecture"
date: 2026-08-04
draft: false
weight: 20
cardLabel: "設計"
cardNote: "DDD・アーキテクチャ・設計パターンのノート"

ShowToc: true
TocOpen: true
hidemeta: false
disableShare: true
ShowBreadCrumbs: true
description: ""
---

ソフトウェアアーキテクチャに関する技術ノートです。DDD・アーキテクチャスタイル・設計パターンを中心に整理しています。

---

### コンテンツ一覧

#### Domain-Driven Design

| No. | 項目 | カテゴリ |
| --- | --- | --- |
| 1 | [Value Object・Entity・Aggregate - DDD のモデル構成要素](/notes/software-architecture/value-object-entity-aggregate/) | DDD |
| 2 | [Bounded Context - モデルが通用する範囲を区切る](/notes/software-architecture/bounded-context/) | DDD |
| 3 | [Repository - Aggregate の永続化を隠す境界](/notes/software-architecture/repository/) | DDD |
| 4 | [Domain Event - ドメインで起きた事実を伝える](/notes/software-architecture/domain-event/) | DDD |
| 5 | [Anticorruption Layer - 上流のモデルを自分の語へ翻訳する](/notes/software-architecture/anti-corruption-layer/) | DDD |
| 6 | [Event Sourcing - 出来事の並びを一次記録にする](/notes/software-architecture/event-sourcing/) | 設計パターン |
| 7 | [CQRS - コマンドとクエリの分離](/notes/software-architecture/cqrs/) | 設計パターン |

#### Container Patterns

| No. | 項目 | カテゴリ |
| --- | --- | --- |
| 1 | [Sidecar - アプリケーションへ機能を足す補助コンテナ](/notes/software-architecture/sidecar/) | 設計パターン |
| 2 | [Ambassador - 外部との通信を仲介する補助コンテナ](/notes/software-architecture/ambassador/) | 設計パターン |
| 3 | [Adapter - アプリケーションの出力を外向きに揃える補助コンテナ](/notes/software-architecture/adapter/) | 設計パターン |

#### Release Patterns

| No. | 項目 | カテゴリ |
| --- | --- | --- |
| 1 | [Feature Flag - 機能の有効・無効を切り替える設計](/notes/software-architecture/feature-flag/) | 設計パターン |

#### Boundaries and Lifecycle

| No. | 項目 | カテゴリ |
| --- | --- | --- |
| 1 | [Plugin Architecture - コアを肥大化させずに機能を足す](/notes/software-architecture/plugin-architecture/) | 設計パターン |
| 2 | [Parse, Don't Validate - 不正な状態を後段へ持ち込まない](/notes/software-architecture/parse-dont-validate/) | 設計パターン |

---

### 参考文献（手元にある書籍）

- [アーキテクチャモダナイゼーション 組織とビジネスの未来を設計する](https://www.shoeisha.co.jp/book/detail/9784798195063)
- [ソフトウェアアーキテクトのための意思決定術　リーダーシップ／技術／プロダクトマネジメントの活用](https://book.impress.co.jp/books/1123101159)
- [マイクロサービスアーキテクチャ 第2版](https://www.oreilly.co.jp/books/9784814400010/)
- [ドメイン駆動設計をはじめよう―ソフトウェアの実装と事業戦略を結びつける実践技法](https://www.oreilly.co.jp//books/9784814400737/)
- [関数型ドメインモデリング](https://tatsu-zine.com/books/domain-modeling-made-functional)
- [セキュア・バイ・デザイン 安全なソフトウェア設計](https://book.mynavi.jp/ec/products/detail/id=124056)
- [ソフトウェアアーキテクチャの基礎 第2版―エンジニアリングに基づく体系的アプローチ](https://www.oreilly.co.jp/books/9784814401550/)
- [ドメイン駆動設計 モデリング/実装ガイド](https://booth.pm/ja/items/1835632)
- [ドメイン駆動設計 サンプルコード&FAQ](https://booth.pm/ja/items/3363104)
- [クリーンコードクックブック―コードの設計と品質を改善するためのレシピ集](https://www.oreilly.co.jp/books/9784814400973/)
- [分散システムのためのデザインパターン](https://www.maruzen-publishing.co.jp/book/b10134955.html)
- [分散システムデザインパターン―コンテナを使ったスケーラブルなサービスの設計](https://www.oreilly.co.jp/books/9784873118758/)
- [ソフトウェアアーキテクチャ・ハードパーツ―分散アーキテクチャのためのトレードオフ分析](https://www.oreilly.co.jp//books/9784814400065/)
- [マルチテナントSaaSアーキテクチャの構築―原則、ベストプラクティス、AWSアーキテクチャパターン](https://www.oreilly.co.jp/books/9784814401017/)
- [システム設計の面接試験](https://www.socym.co.jp/book/1406)
- [データモデリングでドメインを駆動する―⁠―分散／疎結合な基幹系システムに向けて](https://gihyo.jp/book/2024/978-4-297-14010-6)
