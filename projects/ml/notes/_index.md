---
title: "Machine Learning"
date: 2026-05-24
draft: false

ShowToc: true
TocOpen: true
hidemeta: false
disableShare: true
ShowBreadCrumbs: true
---

機械学習初心者（私）が、機械学習の初歩を学ぶ際に残した記録です。

ソースコード・Jupyter Notebook・実行環境は、GitHub 上の [debimate/projects/ml/](https://github.com/nao1215/debimate/tree/main/projects/ml) を参照してください。記載内容の誤り（認識違い）の指摘は大歓迎です。

---

### コンテンツ一覧

#### Mathematics（数学の基礎）

| No. | 項目 |
| --- | --- |
| 1 | [平均（算術平均）](math/mean/) |
| 2 | [中央値（メジアン）](math/median/) |
| 3 | [四分位点（quantile）](math/quantile/) |
| 4 | [分散（バリアンス）](math/variance/) |
| 5 | [標準偏差](math/stddev/) |
| 6 | [歪度（skewness）と log1p 変換](math/skewness/) |
| 7 | [カーネル密度推定（KDE）](math/kde/) |
| 8 | [相関係数](math/correlation/) |

#### Machine Learning（古典的アルゴリズム・評価指標）

| No. | 項目 |
| --- | --- |
| 1 | [ROC-AUC / PR-AUC](ml/roc-pr-auc/) |
| 2 | [混同行列・偽陽性/偽陰性・閾値調整](ml/confusion-matrix/) |
| 3 | [PCA - Principal Component Analysis](ml/pca/) |
| 4 | [k-means - K-means／k平均法](ml/k-means/) |
| 5 | [RandomForest - ランダムフォレスト](ml/random-forest/) |
| 6 | [GradientBoosting - 勾配ブースティング](ml/gradient-boosting/) |
| 7 | [LogisticRegression - ロジスティック回帰](ml/logistic-regression/) |
| 8 | [kNN - k近傍法](ml/knn/) |

#### MLOps

作成中。

---

### Notebooks

| No. | 内容 |
| --- | --- |
| 1 | [クレカ不正検出](https://github.com/nao1215/debimate/blob/main/projects/ml/notebooks/credit-card-fraud/credit-card-fraud.ipynb) |

---

### プロジェクト構成

```text
projects/ml/
├── notes/        ← このページ配下のMarkdown本体
│   ├── math/
│   ├── ml/
│   └── mlops/
├── notebooks/    ← Jupyter Notebooks
├── datasets/     ← 分析対象データ（再取得可能なので Git 非追跡）
├── scripts/      ← データセット取得スクリプト
└── pyproject.toml
```

#### 前提

- Python 3.12 以上
- [uv](https://github.com/astral-sh/uv)（Python パッケージ・環境管理）
- Visual Studio Code ＋ [Jupyter 拡張](https://marketplace.visualstudio.com/items?itemName=ms-toolsai.jupyter)
- Kaggle アカウント（API トークンを `~/.kaggle/kaggle.json` に配置）

#### インストール

```bash
cd projects/ml
uv sync
```

#### データセットのダウンロード

```bash
uv run python scripts/download_datasets.py
```

---

### 参考文献（手元にある書籍）

- [事例で学ぶ特徴量エンジニアリング](https://www.oreilly.co.jp/books/9784814400546/)
- [The Kaggle Book](https://tatsu-zine.com/books/the-kaggle-book)
- [見て試してわかる機械学習アルゴリズムの仕組み 機械学習図鑑](https://www.shoeisha.co.jp/book/detail/9784798155654)
- [MLOps実装ガイド 本番運用を見据えた開発戦略](https://www.oreilly.co.jp/books/9784814401208/)
- [仕事ではじめる機械学習 第2版](https://www.oreilly.co.jp//books/9784873119472/)
- [機械学習システムデザイン](https://www.oreilly.co.jp/books/9784814400409/)
- [楽しみながら学ぶベイズ統計](https://www.sbcr.jp/product/4815604745/)
- [データサイエンスのための数学入門](https://www.oreilly.co.jp/books/9784814401260/)
- [「原因と結果」の経済学](https://www.diamond.co.jp/book/9784478039472.html)
- [Pythonで学ぶあたらしい統計学の教科書](https://www.shoeisha.co.jp/book/detail/9784798155067)
- [前処理大全](https://gihyo.jp/book/2018/978-4-7741-9647-3)
- [戦略的データサイエンス入門](https://www.oreilly.co.jp/books/9784873116853/)
- [ゼロから作るDeep Learning](https://www.oreilly.co.jp/books/9784873117584/)
