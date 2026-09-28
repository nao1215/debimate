---
title: "2026/09/28週"
date: 2026-09-28T00:00:00+09:00
---

#### OpenSSF Scorecard を導入

「OSS ライブラリのメンテナンス具合を調べるツールが欲しいな（作ろうかな）」と考え、類似 OSS を調査したら OpenSSF Scorecard に辿り着いた。OpenSSF Scorecard は、OSS の開発・配布過程にあるセキュリティ上の弱点を自動点検し、保守体制の一部を可視化する。雑に説明すれば、OSS の状態をスコア化する。

成熟したライブラリや単独開発ではスコアが低くなりがちだが、GitHub Actions に余計な権限を与えていないかをチェックできる利点がある。GitHub Actions の Runner 上で任意コマンドを実行する類の脆弱性を見かける機会が増えたので、対策をしておきたかった（参考：[相次ぐGitHub Actions 侵害から学ぶ、初期アクセス手法と開発者が知っておきたい対策](https://blog.flatt.tech/entry/2026-github-actions-security-part1)）。一先ず、Go 製の主要 OSS に OpenSSF Scorecard を導入した。導入済み OSS は、README 上部のバッジにスコアが表示されている。

ついでに、OpenSSF criticality score を計測した。gup が 0.4 を超えているので、[Claude for Open Source Program](https://claude.com/contact-sales/claude-for-oss) の申込条件を満たしていることに気づいた。計測方法によっては 0.4 を下回る説があるが......調べてから再挑戦する。

| Repository | Criticality score | Stars | Contributors | Orgs | Mentions | Releases (1y) |
|---|---|---|---|---|---|---|
| [gup](https://github.com/nao1215/gup) | 0.51532 | 606 | 25 | 6 | 1509 | 29 |
| [sqly](https://github.com/nao1215/sqly) | 0.40981 | 190 | 9 | 1 | 118 | 49 |
| [markdown](https://github.com/nao1215/markdown) | 0.37067 | 142 | 9 | 2 | 77 | 5 |
| [filesql](https://github.com/nao1215/filesql) | 0.33102 | 386 | 2 | 0 | 81 | 74 |
| [atago](https://github.com/nao1215/atago) | 0.32255 | 18 | 3 | 1 | 46 | 33 |

Measured with [criticality_score](https://github.com/ossf/criticality_score) v2.0.4 (default scorer, deps.dev disabled) on 2026-09-28.
