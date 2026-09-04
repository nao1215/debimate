---
title: "Security"
date: 2026-08-04
draft: false
weight: 40
cardLabel: "セキュリティ"
cardNote: "認証・暗号・安全な実装を扱うノート"

ShowToc: true
TocOpen: true
hidemeta: false
disableShare: true
ShowBreadCrumbs: true
description: ""
---

セキュリティに関する技術ノートです。認証・鍵・認可・プライバシーを中心に整理しています。関連する既存のブログ記事も、同じ分類の中へ並べています。

---

### コンテンツ一覧

#### Authentication / Identity

| No. | 項目 | カテゴリ |
| --- | --- | --- |
| 1 | [Authentication - ログインした相手を本人として扱う根拠](/notes/security/authentication/) | 技術ノート / 認証 |
| 2 | [Passkey - 秘密鍵をサーバへ渡さない認証](/notes/security/passkey/) | 技術ノート / 認証 |
| 3 | [Raspberry Pi3向けのセキュアSSH接続設定(公開鍵認証、rootアクセス禁止、ログインユーザ設定など)](/post/ja/2019-03-26-%E7%92%B0%E5%A2%83%E6%A7%8B%E7%AF%89raspberry-pi3%E5%90%91%E3%81%91%E3%81%AE%E3%82%BB%E3%82%AD%E3%83%A5%E3%82%A2ssh%E6%8E%A5%E7%B6%9A%E8%A8%AD%E5%AE%9A%E5%85%AC%E9%96%8B%E9%8D%B5%E8%AA%8D/) | 既存記事 / SSH・公開鍵認証 |

---

#### Cryptography

| No. | 項目 | カテゴリ |
| --- | --- | --- |
| 1 | [Random Number - 暗号で乱数がなぜ重要なのか](/notes/security/random-number/) | 技術ノート / 乱数 |
| 2 | [Nonce - 用途によって異なる「一度」の意味](/notes/security/nonce/) | 技術ノート / 乱数 |

---

#### Privacy

| No. | 項目 | カテゴリ |
| --- | --- | --- |
| 1 | [Tor - 複数のリレーで接続元と接続先を切り離す](/notes/security/tor/) | 技術ノート / 匿名性 |

---

#### Secret Management

| No. | 項目 | カテゴリ |
| --- | --- | --- |
| 1 | [Shamir's Secret Sharing - 閾値以上の Share が揃った時だけ Secret を復元する](/notes/security/shamir-secret-sharing/) | 技術ノート / 秘密分散 |
| 2 | [Timelock Encryption - 将来の条件が成立するまで復号できなくする](/notes/security/timelock-encryption/) | 技術ノート / 時限暗号 |
| 3 | [GitHub Personal Access Tokenをコミットする人がいた話、類似例、漏洩対策ツール【GitHub Secret scanning、gitleaks、git-secrets、gitguardian】](/post/ja/2025-04-27-github-personal-access-token%E3%82%92%E3%82%B3%E3%83%9F%E3%83%83%E3%83%88%E3%81%99%E3%82%8B%E4%BA%BA%E3%81%8C%E3%81%84%E3%81%9F%E8%A9%B1%E9%A1%9E%E4%BC%BC%E4%BE%8B%E6%BC%8F%E6%B4%A9/) | 既存記事 / シークレット漏洩対策 |
| 4 | [【TypeScript】ファイルを分割し、任意の分割ファイル数で復元できる nao1215/horcrux を作った話【分霊箱】](/post/ja/2025-10-05-typescript%E3%83%95%E3%82%A1%E3%82%A4%E3%83%AB%E3%82%92%E5%88%86%E5%89%B2%E3%81%97%E4%BB%BB%E6%84%8F%E3%81%AE%E5%88%86%E5%89%B2%E3%83%95%E3%82%A1%E3%82%A4%E3%83%AB%E6%95%B0/) | 既存記事 / 秘密分散 |

---

#### Software Supply Chain

| No. | 項目 | カテゴリ |
| --- | --- | --- |
| 1 | [DependabotでGitHub ActionsのActionを最新に保つ方法](/post/ja/2023-09-30-dependabot%E3%81%A7github-actions%E3%81%AEaction%E3%82%92%E6%9C%80%E6%96%B0%E3%81%AB%E4%BF%9D%E3%81%A4%E6%96%B9%E6%B3%95/) | 既存記事 / 依存関係管理 |

---

### 参考文献（手元にある書籍）

- [実践 bashによるサイバーセキュリティ対策―セキュリティ技術者のためのシェルスクリプト活用術](https://www.oreilly.co.jp//books/9784873119052/)
- [サイバーセキュリティプログラミング 第2版―Pythonで学ぶハッカーの思考](https://www.oreilly.co.jp/books/9784873119731/)
- [リアルワールドバグハンティング―ハッキング事例から学ぶウェブの脆弱性](https://www.oreilly.co.jp/books/9784873119212/)
- [ハッキング・ラボのつくりかた 完全版 仮想環境におけるハッカー体験学習](https://www.shoeisha.co.jp/book/detail/9784798185996)
- [ペネトレーションテストの教科書 (ハッカーの技術書)](https://www.valuebooks.jp/%E3%83%9A%E3%83%8D%E3%83%88%E3%83%AC%E3%83%BC%E3%82%B7%E3%83%A7%E3%83%B3%E3%83%86%E3%82%B9%E3%83%88%E3%81%AE%E6%95%99%E7%A7%91%E6%9B%B8--%E3%83%8F%E3%83%83%E3%82%AB%E3%83%BC%E3%81%AE%E6%8A%80%E8%A1%93%E6%9B%B8-/bp/VS0081091302?srsltid=AfmBOoq46Xkri7xlN_OcPnwrj_dZD2-zBGxAH5XATCerXY9Sm9dQWfCg)
- [ホワイトハッカー入門 第2版](https://book.impress.co.jp/books/1123101143)
- [マスタリングGhidra―基礎から学ぶリバースエンジニアリング完全マニュアル](https://www.oreilly.co.jp/books/9784873119922/)
- [ハッキングAPI―Web APIを攻撃から守るためのテスト技法](https://www.oreilly.co.jp/books/9784814400249/)
- [7日間でハッキングをはじめる本 TryHackMeを使って身体で覚える攻撃手法と脆弱性](https://www.shoeisha.co.jp/book/detail/9784798181578)
- [ステップアップ脆弱性診断　ツールを比較しながら初級者から中級者に！](https://nextpublishing.jp/book/16525.html)
- [雰囲気で使わずきちんと理解する！整理してOAuth2.0を使うためのチュートリアルガイド・最新改訂版](https://nextpublishing.jp/book/10979.html)
- [暗号技術入門 第3版 秘密の国のアリス](https://www.sbcr.jp/product/4797382228/)
