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

| No. | 項目 | カテゴリ |
| --- | --- | --- |
| 1 | [平均（算術平均）](math/mean/) | 代表値 |
| 2 | [中央値（メジアン）](math/median/) | 代表値 |
| 3 | [四分位点（quantile）](math/quantile/) | 代表値・散らばり |
| 4 | [分散（バリアンス）](math/variance/) | 散らばり |
| 5 | [標準偏差](math/stddev/) | 散らばり |
| 6 | [歪度（skewness）と log1p 変換](math/skewness/) | 分布の形 |
| 7 | [カーネル密度推定（KDE）](math/kde/) | 分布の可視化 |
| 8 | [相関係数](math/correlation/) | 2 変数の関係 |
| 9 | [期待値](math/expectation/) | 確率分布の基礎 |
| 10 | [同時分布・周辺分布・条件付き分布](math/joint-marginal-conditional/) | 確率分布の基礎 |
| 11 | [代表的な確率分布](math/probability-distributions/) | 確率分布 |
| 12 | [ベイズの定理](math/bayes-theorem/) | 確率推論 |
| 13 | [対数・指数関数の性質と log-odds](math/log-exp-logodds/) | 関数 |
| 14 | [情報理論（エントロピー / KL / 相互情報量）](math/information-theory/) | 情報理論 |
| 15 | [ベクトルと行列の演算（内積・行列積）](math/vector-matrix-ops/) | 線形代数 |
| 16 | [固有値・固有ベクトルと固有値分解](math/eigen-decomposition/) | 線形代数 |
| 17 | [偏微分と勾配](math/partial-derivative-gradient/) | 微分 |
| 18 | [最急降下法・確率的勾配降下法（SGD）](math/gradient-descent-sgd/) | 最適化 |
| 19 | [凸関数と凸最適化](math/convex-functions/) | 最適化 |
| 20 | [大数の法則と中心極限定理（LLN / CLT）](math/lln-clt/) | 統計的推論 |
| 21 | [仮説検定・p 値・信頼区間](math/hypothesis-test/) | 統計的推論 |

#### Machine Learning（評価・概念・アルゴリズム）

| No. | 項目 | カテゴリ |
| --- | --- | --- |
| 1 | [混同行列・偽陽性/偽陰性・閾値調整](ml/confusion-matrix/) | 評価指標 |
| 2 | [ROC-AUC / PR-AUC](ml/roc-pr-auc/) | 評価指標 |
| 3 | [回帰の評価指標（RMSE / MAE / R²）](ml/regression-metrics/) | 評価指標 |
| 4 | [確率の校正（Platt scaling / Isotonic）](ml/probability-calibration/) | 評価指標 |
| 5 | [損失関数（MSE / 交差エントロピー）](ml/loss-functions/) | 学習概念 |
| 6 | [過学習（overfitting）](ml/overfitting/) | 学習概念 |
| 7 | [バイアス-バリアンス分解（bias-variance tradeoff）](ml/bias-variance-tradeoff/) | 学習概念 |
| 8 | [正則化（regularization）](ml/regularization/) | 学習概念 |
| 9 | [交差検証（cross validation）](ml/cross-validation/) | 学習概念 |
| 10 | [ハイパーパラメータ（hyperparameter）](ml/hyperparameter/) | 学習概念 |
| 11 | [データリーク（data leakage）](ml/data-leakage/) | 学習概念 |
| 12 | [クラス不均衡への対処（class imbalance）](ml/class-imbalance/) | 学習概念 |
| 13 | [次元の呪い（curse of dimensionality）](ml/curse-of-dimensionality/) | 学習概念 |
| 14 | [標準化と特徴量スケーリング（standardization）](ml/standardization/) | 前処理 |
| 15 | [カテゴリ変数のエンコーディング（categorical encoding）](ml/categorical-encoding/) | 前処理 |
| 16 | [欠損値処理（MCAR / MAR / MNAR）](ml/missing-values/) | 前処理 |
| 17 | [特徴量選択（feature selection）](ml/feature-selection/) | 前処理 |
| 18 | [線形回帰（linear regression）](ml/linear-regression/) | 教師あり |
| 19 | [LogisticRegression - ロジスティック回帰](ml/logistic-regression/) | 教師あり |
| 20 | [kNN - k近傍法](ml/knn/) | 教師あり |
| 21 | [決定木（decision tree）](ml/decision-tree/) | 教師あり |
| 22 | [サポートベクターマシン（SVM）](ml/svm/) | 教師あり |
| 23 | [RandomForest - ランダムフォレスト](ml/random-forest/) | 教師あり |
| 24 | [GradientBoosting - 勾配ブースティング](ml/gradient-boosting/) | 教師あり |
| 25 | [アンサンブル学習（bagging / boosting / stacking）](ml/ensemble-learning/) | 学習概念 |
| 26 | [時系列予測（time series forecasting）](ml/time-series-forecasting/) | 時系列 |
| 27 | [k-means - K-means／k平均法](ml/k-means/) | 教師なし |
| 28 | [PCA - Principal Component Analysis](ml/pca/) | 教師なし |
| 29 | [DBSCAN（density-based clustering）](ml/dbscan/) | 教師なし |
| 30 | [階層的クラスタリング（hierarchical clustering）](ml/hierarchical-clustering/) | 教師なし |
| 31 | [t-SNE と UMAP（非線形次元削減）](ml/tsne-umap/) | 教師なし |
| 32 | [異常検知（Isolation Forest / LOF / One-Class SVM）](ml/anomaly-detection/) | 教師なし |
| 33 | [特徴量重要度（permutation importance）](ml/feature-importance/) | 解釈性 |
| 34 | [パーセプトロン（perceptron）](ml/perceptron/) | 深層学習 |
| 35 | [活性化関数（sigmoid / ReLU / GELU）](ml/activation-functions/) | 深層学習 |
| 36 | [誤差逆伝播法（backpropagation）](ml/backpropagation/) | 深層学習 |

#### MLOps

| No. | 項目 | カテゴリ |
| --- | --- | --- |
| 1 | [実験管理（experiment tracking）](mlops/experiment-tracking/) | 開発 |
| 2 | [モデルレジストリとバージョニング](mlops/model-registry/) | 開発 |
| 3 | [推論サービング（バッチ / オンライン）](mlops/inference-serving/) | 配信 |
| 4 | [データドリフト（data drift / concept drift）](mlops/data-drift/) | 監視 |
| 5 | [モデル性能劣化の監視](mlops/model-performance-monitoring/) | 監視 |
| 6 | [再学習パイプライン](mlops/retraining-pipeline/) | 運用 |

#### 理解度チェック

学習で扱った判断軸を自分でも試せる形式にまとめたクイズ集。問題と折りたたみ解答で構成されており、判断軸の定着を確認したいときに使う（Claude製）。

| No. | 項目 |
| --- | --- |
| 1 | [機械学習の判断軸クイズ集](quiz/) |

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
