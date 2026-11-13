---
title: "モデル性能劣化の監視 - 正解率が 0.41 に落ちた週、平均確信度は 0.99 だった"
date: 2026-05-26
draft: false
series: ["機械学習ノート", "MLOps"]
tags: ["machine-learning", "mlops", "monitoring"]
weight: 5
topics: ["MLOps"]
---

モデル性能劣化の監視は、本番で動くモデルの予測が、学習した時より当たらなくなっていないかを見張り続けることです。分類のモデルなら、予測と後から分かる正解を突き合わせて正解率を出すのが基本で、正解が届くまでの間は、入力の分布やモデルの確信度を代わりに見ます。確信度は、モデルが予測したクラスに付けた確率で、2 値分類なら 0.5 から 1 の値を取ります。

監視を組む時は、次の前提を置きたくなります。

- 正解率が下がれば、モデルの確信度も下がる。
- 入力の分布が大きく変わった週は、正解率も下がる。
- 毎日の正解率が閾値を割れば、モデルが劣化している。
- 正解が後から届けば、劣化した週はその時に分かる。

どれも成り立ちそうですが、公開データ 1 つと乱数で試すと、4 つとも成り立たない例が出ました。使ったのは、オーストラリア・ニューサウスウェールズ州の電力市場で、30 分ごとの価格が直近 24 時間の平均より上がった（UP）か下がった（DOWN）かを記録した elec2 です。機械学習のデータセットを集めて公開している [OpenML](https://www.openml.org/d/151) から取得しました。1996 年 5 月からの 22 週で学習し、続く 4 週で当たり具合を見て（検証）、その後の 2 年余りを運用の期間として週ごとに評価しました。

{{< figure src="mpm_cover.webp" alt="横軸は第 22 週（1996-10）から第 134 週（1998-12）までの週、縦軸は週ごとの値。左端の緑の帯が検証の 4 週で、黒い平均確信度と赤い正解率はどちらも 0.78 付近で重なる。その後、黒い線は 0.9 から 1.0 へ上がり、赤い線は 0.5 から 0.7 の間に下がって、2 本が大きく離れる。第 101 週（1998-04）に印があり、正解率 0.411、確信度 0.994" caption="elec2 の週ごとの正解率と平均確信度" align="center" >}}

検証の 4 週では、正解率と平均確信度がどちらも 0.779 で揃っていました。その後の 109 週では正解率が 0.70 を割る週が 44 週あり、最も低い第 101 週は 0.411 でした。同じ週の平均確信度は 0.994 で、平均確信度が 0.70 を割った週は 1 週もありません。

ML のモデルを本番に出すと、ダッシュボードに何を並べ、どの値でアラートを鳴らすかを決めることになります。正解が届くまで数週間かかるモデルでは、正解率のグラフが空いた期間は、確信度や入力の分布で埋めたくなります。その選び方を誤ると、上の図のように、モデルが最も外れている週に 0.99 台という安心できる数字を見ることになります。

<br>

本記事では、本番で動くモデルに監視を組もうとしている人と、監視のグラフやアラートの意味に迷っている人に向けて、次の疑問に答えます。

- モデルは、どんな時に自信を持ったまま外れるのか。
- 正解が無い間に見るシグナルは、正解率の低下を拾えるか。
- 正解率のアラートは、何日分の件数で判断すればよいか。
- 正解が遅れて届く間、何が見えて何が見えないか。
- Prometheus で、これらをどう集計するか。

実験は scikit-learn 1.9.1、NumPy 2.5.4、SciPy 1.18.1 で行いました。図を描く処理も含めた完全なコードは [model-performance-monitoring_gen.py](https://github.com/nao1215/debimate/blob/main/projects/ml/scripts/notes/model-performance-monitoring_gen.py) にあります。

---

### 自信を持ったまま外れる区間

elec2 は 30 分ごとに 1 行で、1 日 48 行、1 週 336 行です。特徴量は曜日・時刻・ニューサウスウェールズ州の価格・需要の 4 列にし、勾配ブースティングの [`HistGradientBoostingClassifier`](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingClassifier.html) で UP か DOWN かを予測させました。仕組みは[勾配ブースティング](../../ml/gradient-boosting/)で説明しています。

```python
frame = fetch_openml(data_id=151, as_frame=True, parser="liac-arff").frame
frame["day"] = frame["day"].astype(int)
cols = ["day", "period", "nswprice", "nswdemand"]
X = frame[cols].to_numpy()
y = (frame["class"] == "UP").to_numpy().astype(int)  # 直近 24 時間の平均より上がったら UP
week = np.arange(len(frame)) // (48 * 7)              # 30 分ごとに 1 行、1 週は 336 行

train = week < 22                                     # 1996-05-07 からの 22 週で学習
valid = (week >= 22) & (week < 26)                    # 続く 4 週で検証
model = HistGradientBoostingClassifier(random_state=0).fit(X[train], y[train])

p_up = model.predict_proba(X)[:, 1]
pred_up = p_up > 0.5
conf = np.maximum(p_up, 1 - p_up)                     # 予測したクラスの確率 = 確信度
correct = pred_up == y
print(f"検証の 4 週: 正解率 {correct[valid].mean():.3f}  平均確信度 {conf[valid].mean():.3f}")

weeks = np.arange(26, week.max() + 1)
acc_w = np.array([correct[week == w].mean() for w in weeks])
conf_w = np.array([conf[week == w].mean() for w in weeks])
print(f"運用の {len(weeks)} 週: 正解率と確信度の相関 {np.corrcoef(acc_w, conf_w)[0, 1]:.2f}")
```

```text
検証の 4 週: 正解率 0.779  平均確信度 0.779
運用の 109 週: 正解率と確信度の相関 -0.55
```

確信度が上がる週ほど正解率が下がる、負の[相関](../../math/correlation/)です。

<br>

#### 安い価格は DOWN と覚えたモデル

原因は、elec2 が正解を決める方法にあります。UP は、価格が「直近 24 時間の平均より」上がったことを表します。[OpenML の説明](https://www.openml.org/d/151)によると、長い期間にわたる価格の動きを打ち消すために、この形にしています。モデルには平均を渡さず価格そのものを渡しているので、モデルが覚えられるのは「この価格なら UP が多い」という関係です。

学習した期間の価格で 10 個の区間に分け、区間ごとに UP の割合を並べました。

```python
test = week >= 26                                     # 運用の 109 週
edges = np.quantile(X[train, 2], np.linspace(0, 1, 11))  # 学習した期間の価格で 10 等分
bin_of = np.clip(np.searchsorted(edges, X[:, 2], side="right") - 1, 0, 9)
rows = []
for k in range(10):
    tr_k, te_k = train & (bin_of == k), test & (bin_of == k)
    rows.append((y[tr_k].mean(), y[te_k].mean(), pred_up[te_k].mean(), te_k.sum() / test.sum()))
    print(f"区間 {k + 1:>2}: 学習 UP {rows[-1][0]:.2f}  運用 UP {rows[-1][1]:.2f}"
          f"  予測 UP {rows[-1][2]:.2f}  運用の行の割合 {rows[-1][3]:.2f}")
bins = np.array(rows)
print(f"価格の中央値: 学習 {np.median(X[train, 2]):.4f}  運用 {np.median(X[test, 2]):.4f}")
hi = conf > 0.99
print(f"確信度 0.99 を超える行: 検証 {hi[valid].mean():.2f}  運用 {hi[test].mean():.2f}"
      f"  運用での正解率 {correct[test & hi].mean():.3f}")
band = np.digitize(conf, [0.6, 0.7, 0.8, 0.9, 0.95, 0.99])  # 確信度を 7 つの帯に分ける
gap = [abs(conf[valid & (band == b)].mean() - correct[valid & (band == b)].mean()) for b in range(7)]
print(f"検証の 4 週: 帯ごとの確信度と正解率の差 最大 {max(gap):.3f}")
```

```text
区間  1: 学習 UP 0.01  運用 UP 0.25  予測 UP 0.00  運用の行の割合 0.41
区間  2: 学習 UP 0.01  運用 UP 0.36  予測 UP 0.00  運用の行の割合 0.05
（区間 3〜10 は省略）
価格の中央値: 学習 0.0626  運用 0.0456
確信度 0.99 を超える行: 検証 0.03  運用 0.49  運用での正解率 0.765
検証の 4 週: 帯ごとの確信度と正解率の差 最大 0.047
```

{{< figure src="mpm_price_bins.webp" alt="左は価格の 10 分位ごとの 3 本の棒。最も安い区間 1 では、学習の 22 週で UP だった割合が 0.01、運用の 109 週で UP だった割合が 0.25、モデルが UP と予測した割合が 0.00。区間 2 と 3 も学習ではほぼ 0 だが、運用では 0.36 と 0.27。高い区間ほど 3 本とも 1 に近づく。右は運用の行がどの区間に入ったかの割合を黒い棒で示し、区間 1 だけが 41% と突出し、残りは学習時の 10% 以下" caption="価格の区間ごとの UP の割合（左）と、運用の行が入った区間（右）" align="center" >}}

学習した 22 週では、価格が最も安い 10% の区間で UP だったのは 1% でした。モデルはこの区間を DOWN と覚え、運用ではこの区間の行を全て DOWN と予測しています。

ところが運用の期間は価格全体が下がり、価格の[中央値](../../math/median/)は 0.0626 から 0.0456 になりました。運用の行のうち 41% がこの区間に入り、そこでは 25% が UP でした。価格の水準が下がれば、安い価格でも直近の平均より上がることは増えます。学習した期間の「安いから DOWN」は、水準が変わると成り立ちません。

入力の分布が動く[共変量シフト](../data-drift/)と、入力と正解の関係が動く概念ドリフトが、同時に起きたことになります。検証の 4 週では、平均確信度と正解率が揃っていただけでなく、確信度を 0.6・0.7・0.8・0.9・0.95・0.99 で 7 つの帯に分けても、帯ごとの差は最大 0.047 でした。この期間の確率は[校正](../../ml/probability-calibration/)されていたことになります。それでも、学習した期間に無かった状況が来ると、確信度は正解率の目安になりませんでした。

確信度が 0.99 を超える行は、検証では 3% でしたが運用では 49% に増え、その正解率は 0.765 でした。モデルが自信を持つのは学習した期間に例外が無かった区間で、そこへ行が流れ込んだ時に平均確信度は上がります。

---

### 正解が無い間に見るシグナル

正解を使わずに出せる値は、確信度の他にもあります。入力や確信度の分布がどれだけ動いたかと、予測したクラスの割合です。週ごとにアラートを鳴らして、どれが正解率の低い週を拾えるかを数えました。

分布の変化には PSI（Population Stability Index）を使いました。値を同じ区間に分け、基準の期間と今の期間で区間ごとの割合を比べる指標で、式と性質は[情報理論](../../math/information-theory/)で扱っています。閾値は、よく使われる目安のうち「変化が大きい」側の 0.25 にしました。

```python
def psi(base, now, bins=10, eps=1e-4):
    """PSI。区間は base の 10 分位。空の区間の割合 0 は eps に置き換える。"""
    q = np.quantile(base, np.linspace(0, 1, bins + 1))
    q[0], q[-1] = -np.inf, np.inf
    b = np.clip(np.histogram(base, q)[0] / len(base), eps, None)
    n = np.clip(np.histogram(now, q)[0] / len(now), eps, None)
    return float(np.sum((n - b) * np.log(n / b)))


psi_price_w = np.array([psi(X[valid, 2], X[week == w, 2]) for w in weeks])
psi_demand_w = np.array([psi(X[valid, 3], X[week == w, 3]) for w in weeks])
psi_conf_w = np.array([psi(conf[valid], conf[week == w]) for w in weeks])
predup_w = np.array([pred_up[week == w].mean() for w in weeks])
print(f"検証の 4 週: UP と予測した割合 {pred_up[valid].mean():.2f}")
signals = {                                           # 正解を使わずに鳴らすアラート
    "平均確信度 < 0.70": conf_w < 0.70,
    "価格の PSI > 0.25": psi_price_w > 0.25,
    "需要の PSI > 0.25": psi_demand_w > 0.25,
    "確信度の PSI > 0.25": psi_conf_w > 0.25,
    "UP と予測した割合 < 0.30": predup_w < 0.30,
}
bad = acc_w < 0.70                                    # 答え: 正解率が 0.70 未満の週
for name, alarm in signals.items():
    print(f"{name:<20} アラート {alarm.sum():>3} 週  当たり {np.sum(alarm & bad):>2}"
          f"  誤検知 {np.sum(alarm & ~bad):>2}  見逃し {np.sum(bad & ~alarm):>2}")
print(f"UP と予測した割合と正解率の相関 {np.corrcoef(acc_w, predup_w)[0, 1]:.2f}")
```

基準は検証の 4 週です。UP と予測した割合は検証で 0.58 だったので、その半分ほどの 0.30 を閾値にしました。

<br>

<details>
<summary>PSI の目安と、件数による揺れ</summary>

PSI は 0.1 未満なら変化は小さく、0.25 を超えたら大きいという目安で使われますが、[Yurdakul 氏の 2018 年の論文](https://scholarworks.wmich.edu/dissertations/3208/)が指摘するとおり、この目安は誤って鳴る確率とは結び付いていません。誤って鳴る確率で閾値を決めたいなら、KS 検定などの[仮説検定](../../math/hypothesis-test/)を使います。

件数が少ないと、分布が同じでも標本のばらつきだけで PSI は 0 から離れます。elec2 の 1 週 336 行でどこまで振れるかは、検証の 4 週から 336 行を選び直して出しました。

```python
rng_psi = np.random.default_rng(1)
base = X[valid, 2]
noise = np.array([psi(base, rng_psi.choice(base, 336, replace=False)) for _ in range(1000)])
print(f"検証の 4 週から 336 行を選んだ時の価格の PSI: 平均 {noise.mean():.3f}  0.1 を超えた割合 {np.mean(noise > 0.1):.3f}")
print("検証の各週の価格の PSI:", [round(psi(base, X[week == w, 2]), 2) for w in range(22, 26)])
```

```text
検証の 4 週から 336 行を選んだ時の価格の PSI: 平均 0.020  0.1 を超えた割合 0.000
検証の各週の価格の PSI: [1.11, 0.24, 0.15, 0.22]
```

336 行を選び直しただけなら PSI は平均 0.02 で、0.1 を超えた回はありません。一方、検証の 4 週を 1 週ずつ比べると、基準に含まれる週どうしでも 0.15 から 1.11 あります。elec2 で価格の PSI が鳴り続けたのは件数の揺れではなく、価格が週ごとに実際に動いているためです。

</details>

<br>

{{< figure src="mpm_signals.webp" alt="横軸は第 26 週から第 134 週までの週。6 段の帯があり、一番下の黒い段は正解率が 0.70 未満だった週で、第 55 週から第 104 週ごろに固まっている。上の 5 段は各シグナルのアラートで、赤は正解率も 0.70 未満だった週、青は正解率が 0.70 以上だった週。平均確信度の段は空。価格の PSI の段はほぼ全ての週が埋まり、青も多い。UP と予測した割合の段は黒い段とよく重なるが、青も混じる" caption="正解を使わない 5 つのアラートと、正解率が 0.70 未満だった週" align="center" >}}

| アラート | 鳴った週 | 当たり | 誤検知 | 見逃し |
|---|---:|---:|---:|---:|
| 平均確信度 < 0.70 | 0 | 0 | 0 | 44 |
| 価格の PSI > 0.25 | 102 | 44 | 58 | 0 |
| 需要の PSI > 0.25 | 83 | 34 | 49 | 10 |
| 確信度の PSI > 0.25 | 78 | 41 | 37 | 3 |
| UP と予測した割合 < 0.30 | 70 | 42 | 28 | 2 |

平均確信度は 109 週で一度も鳴りませんでした。価格の PSI は正解率の低い 44 週を全て拾いましたが、109 週のうち 102 週で鳴り続けています。検証の 4 週と比べると、価格はほとんどの週で 0.25 を超えるほど動いていて、鳴っていない週の方が珍しい状態です。

このデータで最も正解率に沿ったのは、UP と予測した割合でした。正解率との相関は 0.67 で、44 週のうち 42 週を拾い、誤検知は 28 週です。確信度も、PSI で分布の形を見ると 41 週を拾いましたが、誤検知は UP と予測した割合より多い 37 週です。平均確信度は上がる向きに動いたので「0.70 を下回る」という条件には掛かりませんが、PSI は向きを問わず、0.99 を超える所に寄った行の多さを変化として数えます。

<br>

どのシグナルが効くかは、データとモデルで変わります。elec2 で言えるのは、正解を使わないシグナルは「何かが変わった」を知らせるだけで、正解率が下がったかどうかは正解でしか分からない、ということです。鳴った時に、正解を急いで集める、区間ごとに予測を見直すといった次の作業を始める合図として使うのが向いていると考えられます。

---

### 日ごとの正解率の揺れ

正解が届いても、件数が少ないと正解率そのものが揺れます。elec2 は 1 日 48 行なので、1 日分の正解率は 48 回の当たり外れから出した値です。当たる確率が 0.78 で一定でも、48 回中の当たりの数は[二項分布](../../math/probability-distributions/)に従って散らばり、0.70 を割る日が 8.8% あります。1 年なら 32 日です。

本当の正解率が 365 日目まで 0.78、その後 0.65 に落ちる 485 日分の当たり外れを乱数で作り、直近の何日分で正解率を出すかを変えて、誤検知と気づくまでの日数を 2000 回ずつ数えました。

```python
rng = np.random.default_rng(0)
true_acc = np.r_[np.full(365, 0.78), np.full(120, 0.65)]   # 366 日目から 0.65 に落ちる
daily = rng.binomial(48, true_acc) / 48                     # 図に描く 1 本（1 日 48 件の正解率）
for win in [1, 7, 28]:
    false_alarm, delay = [], []
    for _ in range(2000):
        d = rng.binomial(48, true_acc)
        roll = np.convolve(d, np.ones(win), "valid") / (48 * win)  # 直近 win 日の正解率
        end = np.arange(win - 1, len(d))                          # 窓の最後の日
        alarm = roll < 0.70
        false_alarm.append(np.sum(alarm & (end < 365)) * 365 / np.sum(end < 365))
        after = np.flatnonzero(alarm & (end >= 365))
        delay.append(end[after[0]] - 365 + 1 if len(after) else np.nan)
    print(f"直近 {win:>2} 日: 誤検知 年 {np.mean(false_alarm):5.1f} 回  落ちてから鳴るまで 中央値 {np.nanmedian(delay):4.0f} 日")
```

```text
直近  1 日: 誤検知 年  32.3 回  落ちてから鳴るまで 中央値    1 日
直近  7 日: 誤検知 年   0.1 回  落ちてから鳴るまで 中央値    5 日
直近 28 日: 誤検知 年   0.0 回  落ちてから鳴るまで 中央値   18 日
```

{{< figure src="mpm_noise.webp" alt="横軸は 1 日目から 485 日目、縦軸は正解率。緑の破線の本当の正解率は 365 日目まで 0.78 で、その後 0.65 に下がる。点は 1 日 48 件の正解率で 0.48 から 0.96 に散らばり、0.70 以上の日は青、0.70 を割った日は赤で、赤い点が最初の 365 日にも数十個ある。黒い線の直近 7 日の正解率は、最初の 365 日は 0.72 から 0.83 の間を動き、0.65 に落ちた後は数日で 0.70 を下回る" caption="本当の正解率が一定でも、1 日 48 件の正解率は 0.70 を割る（乱数で作った 485 日）" align="center" >}}

1 日分で判断すると、劣化していないのに年 32 回鳴ります。直近 7 日分にすると誤検知は年 0.1 回に減り、0.65 に落ちてから鳴るまでの中央値は 5 日です。28 日分では誤検知はほぼ出ませんが、気づくまで 18 日かかります。

揺れの大きさは、正解率の[標準偏差](../../math/stddev/) `sqrt(p (1 - p) / n)` で見積もれます。`p = 0.78` で `n = 48` なら 0.060、7 日分の `n = 336` なら 0.023 です。件数を 7 倍にすると、揺れは 7 の平方根で割った大きさになります。この性質は[大数の法則と中心極限定理](../../math/lln-clt/)で説明しています。

<br>

誤り率と、その標準偏差の動きで変化を見つける考え方は、DDM（Drift Detection Method）にも使われています。DDM は [Gama 氏らが 2004 年に発表した手法](https://doi.org/10.1007/978-3-540-28645-5_29)で、OpenML の説明は、elec2 を分析した論文としてこれを挙げています。閾値を決める前に、1 日に正解が何件届き、その件数での揺れがどれくらいかを先に計算しておくと、窓の長さを選べます。

---

### 正解が遅れて届く間

elec2 の正解は 30 分後に分かります。レコメンドでもクリックの有無は数秒で分かりますが、購入したかは数日後、使い続けてくれたかは数週間後にしか分かりません。貸し倒れの予測なら、正解は数か月後です。仮に正解が 8 週遅れて届くとして、同じ週ごとの値がダッシュボードにどう出るかを動かしました。正解率は予測した週ごとに集計し、正解が届いた週から順に埋まります。

```python
LAG = 8
two_acc = bad[1:] & bad[:-1]                          # 2 週続けて 0.70 未満
two_up = (predup_w[1:] < 0.30) & (predup_w[:-1] < 0.30)
first_acc = weeks[1:][np.argmax(two_acc)]
first_up = weeks[1:][np.argmax(two_up)]
print(f"正解率が 2 週続けて 0.70 を割った最初の週: 第 {first_acc} 週。正解が {LAG} 週遅れるなら、分かるのは第 {first_acc + LAG} 週")
print(f"UP と予測した割合が 2 週続けて 0.30 を割った最初の週: 第 {first_up} 週")
```

```text
正解率が 2 週続けて 0.70 を割った最初の週: 第 47 週。正解が 8 週遅れるなら、分かるのは第 55 週
UP と予測した割合が 2 週続けて 0.30 を割った最初の週: 第 45 週
```

{{< figure src="mpm_label_lag.webp" alt="上下 2 段の動く図。上の段は正解率で、右端に灰色の「正解待ち」の帯が 8 週分あり、赤い線は今日から 8 週前までしか描かれない。下の段は UP と予測した割合で、青い線は今日まで描かれる。今日が第 26 週から第 80 週へ進むにつれ、下の段では第 45 週に印が付き、上の段では第 55 週になって初めて、0.70 を割った第 46 週（0.589）と第 47 週（0.696）に値付きの印が付く。最後のコマで 3 秒止まる" caption="正解が 8 週遅れて届く時のダッシュボード（1 週を 0.16 秒ずつ表示）" align="center" >}}

正解率のグラフは、右端がいつ見ても 8 週前です。2 週続けて 0.70 を割ったことは第 47 週の時点で起きていますが、ダッシュボードで分かるのは第 55 週になってからです。UP と予測した割合は、第 45 週の時点で 2 週続けて 0.30 を割り、その週のうちに見えています。

正解を後から突き合わせるには、予測した時に予測の ID・時刻・モデルのバージョン・入力・予測と確率を記録しておく必要があります。正解が届いた週で集計すると、違う週の予測が混ざり、劣化が始まった週が分からなくなります。ログを一部だけ抜き出して記録すると、正解が届いても突き合わせる相手の無い予測が出ます。予測が複数のサービスをまたぐなら、[分散トレーシング](/notes/distributed-systems/distributed-tracing/)の ID も記録しておくと、正解から予測の経路まで辿れます。予測を返す側の構成は[推論サービング](../inference-serving/)で扱っています。

---

### Prometheus で集める

正解を使わないシグナルは、予測を返すサーバーで数えられます。時系列の値を集めて保存する監視の OSS、[Prometheus](https://prometheus.io/) を使うなら、[公式の Python クライアント](https://prometheus.github.io/client_python/)で、予測したクラスの件数と確信度のヒストグラムを出します。集めた値のグラフは、[Grafana](https://grafana.com/) などのダッシュボードで見ます。

```python
from prometheus_client import Counter, Histogram

PREDICTIONS = Counter("model_predictions", "予測した件数", ["predicted"])
CONFIDENCE = Histogram("model_prediction_confidence", "予測したクラスの確率",
                       buckets=[0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 0.999, 1.0])
for c in ["UP", "DOWN"]:
    PREDICTIONS.labels(predicted=c)                   # 起動した時から 0 の系列を出しておく

def record(p_up: float) -> None:
    label = "UP" if p_up > 0.5 else "DOWN"
    PREDICTIONS.labels(predicted=label).inc()
    CONFIDENCE.observe(max(p_up, 1 - p_up))
```

ヒストグラムの区切り（buckets）は、1 に近い所を細かく刻みます。elec2 の変化は、確信度が 0.99 を超える行が 3% から 49% に増える形で出ました。区切りが 0.9 までしか無いと、この変化は最後の 1 つの区切りの中に埋もれます。

集計は、記録ルール（recording rules）として Prometheus に置きます。記録ルールは、式の結果を新しい時系列として定期的に保存する仕組みです。ヒストグラムの件数は区切りの上限ごとに `le` というラベルを付けて記録されるので、ルールに出てくる `le` はこの上限を指します。次のルールは、Prometheus 3.13.0 の `promtool check rules` で文法を通しています。

```yaml
groups:
  - name: model-monitoring
    rules:
      # UP と予測した割合（直近 7 日）
      - record: model:predicted_up_ratio:7d
        expr: |
          sum(increase(model_predictions_total{predicted="UP"}[7d]))
            / sum(increase(model_predictions_total[7d]))
      # 確信度が 0.99 を超えた予測の割合（直近 1 日）
      - record: model:confidence_over_099_ratio:1d
        expr: |
          1 - sum(increase(model_prediction_confidence_bucket{le="0.99"}[1d]))
                / sum(increase(model_prediction_confidence_count[1d]))
      # 確信度の 10% 点。全てのサーバーの件数を区切りの上限 le ごとに足してから求める
      - record: model:confidence_p10:1d
        expr: |
          histogram_quantile(0.1,
            sum by (le) (increase(model_prediction_confidence_bucket[1d])))
      - alert: PredictedUpRatioLow
        expr: model:predicted_up_ratio:7d < 0.30
      # サーバーかスクレイプが止まり、件数の系列そのものが消えた
      - alert: PredictionsAbsent
        expr: absent(model_predictions_total)
        for: 10m
      # サーバーは動いているが、予測が 1 時間に 1 件も無い
      - alert: PredictionsStopped
        expr: sum(increase(model_predictions_total[1h])) == 0
        for: 10m
```

最後の 2 つのアラートは、監視そのものが止まった時のためのものです。予測を返すサーバーや Prometheus のスクレイプが止まると、正解率もシグナルも値が来ないだけで、閾値を割るアラートは鳴りません。値が来ないこと自体を `absent` で拾うのは、[Heartbeat](/notes/distributed-systems/heartbeat/) と同じ考え方です。ただし `absent` は系列が消えた時にしか鳴らず、サーバーが動いたまま予測の要求だけが止まった時は、0 のまま残る系列を `increase(...) == 0` で拾います。Python のコードでラベルごとの系列を先に作っておいたのは、最初の予測が来る前に系列が無いと、起動直後に `absent` が鳴るためです。

[`histogram_quantile`](https://prometheus.io/docs/prometheus/latest/querying/functions/) に `sum by (le)` で足してから渡すのは、サーバーごとに求めた[分位数](../../math/quantile/)を平均しても、全体の分位数にはならないためです。Prometheus の[ヒストグラムとサマリーの文書](https://prometheus.io/docs/practices/histograms/)にも同じ注意があります。

<br>

ここまでは週ごとに見ましたが、ルールでは直近の何日分で割合を出すかを決める必要があります。1 日 48 件の予測を独立とみなすと、検証での割合 0.58 に対して 1 日分の標準偏差は 0.071 で、閾値の 0.30 はその 4 倍ほど下にあります。実際の予測で、検証の 28 日を数えました。

```python
day = np.arange(len(frame)) // 48                     # 1 日 48 行
for win in [1, 7]:
    r = np.array([pred_up[valid & (day >= d) & (day < d + win)].mean()
                  for d in range(day[valid].min(), day[valid].max() - win + 2)])
    print(f"検証の 28 日、直近 {win} 日: UP と予測した割合 標準偏差 {r.std():.3f}"
          f"  最小 {r.min():.3f}  0.30 を割った日 {np.sum(r < 0.30)}")
```

```text
検証の 28 日、直近 1 日: UP と予測した割合 標準偏差 0.154  最小 0.188  0.30 を割った日 3
検証の 28 日、直近 7 日: UP と予測した割合 標準偏差 0.049  最小 0.464  0.30 を割った日 0
```

1 日分の割合は、独立とみなした時の 2 倍ほどの 0.154 で揺れ、劣化していない検証の期間でも 28 日のうち 3 日は 0.30 を割りました。30 分ごとの予測は、同じ日の中で近い時刻どうしが似た値になりやすく、48 件を独立に足した時ほどには平均されません。直近 7 日分にすると最も低い日でも 0.464 だったので、ルールも 7 日分で出しています。

正解率は、ここには入れていません。正解は数週間後に別の経路で届くので、予測の記録と正解を ID で突き合わせるバッチで、予測した週ごとに計算します。PSI も、基準の期間で決めた区切りを持つ必要があるので、同じバッチで計算する方が素直です。

<br>

<details>
<summary>入力の値を Gauge で出さない理由</summary>

入力の値を Prometheus に出す時は、Gauge を使わないようにします。Gauge は最後に `set()` した値だけを持ち、Prometheus は[既定で 1 分ごと](https://prometheus.io/docs/prometheus/latest/configuration/configuration/)にしか読みに来ないので、その間の要求は最後の 1 件しか残りません。Gauge と [Summary](https://prometheus.io/docs/concepts/metric_types/#summary) の両方に、価格 0.04、0.05、0.06、0.09 の 4 件を入れて比べました。

```python
from prometheus_client import Gauge, Summary, generate_latest

g = Gauge("input_price_gauge", "価格")
s = Summary("input_price", "価格")
for v in [0.04, 0.05, 0.06, 0.09]:
    g.set(v)
    s.observe(v)
print(generate_latest().decode())
```

```text
（抜粋）
input_price_gauge 0.09
input_price_count 4.0
input_price_sum 0.24
```

Gauge は 0.09 だけを返し、Summary は件数 4 と合計 0.24 を返すので、平均 0.06 が求まります。平均は `rate(..._sum[1h]) / rate(..._count[1h])` で求め、分布の形まで見るなら Histogram にします。

</details>

<br>

ここまでの集計を自分で組まずに、ML 向けの監視サービスに任せる方法もあります。OSS の [Evidently](https://www.evidentlyai.com/)、Google Cloud の [Vertex AI Model Monitoring](https://cloud.google.com/vertex-ai/docs/model-monitoring/overview)、AWS の [SageMaker Model Monitor](https://docs.aws.amazon.com/sagemaker/latest/dg/model-monitor.html) などです。どれを使っても、正解の遅れと件数の少なさは変わらないので、前の 2 つの節の判断は残ります。

<br>

<details>
<summary>3 つのサービスが計算する内容</summary>

Evidently と SageMaker Model Monitor は、入力や予測の分布がどれだけ動いたかと、正解を突き合わせた性能を出します。Vertex AI Model Monitoring が出すのは、入力と予測の分布がどれだけ動いたかだけです。SageMaker Model Monitor は、2026 年 11 月 14 日に見た時点の文書で[新しい顧客の受け付けを止めている](https://docs.aws.amazon.com/sagemaker/latest/dg/model-monitor-availability-change.html)と書かれていて、代わりに Evidently などを組み合わせた構成を案内しています。

</details>

<br>

---

### 監視を組む前に決めること

最初に決めるのは、正解が何日後に、1 日に何件届くかです。遅れの分だけ、正解率のグラフは右端が過去になり、件数が少なければ正解率は揺れます。1 日 48 件なら、1 日分の正解率に閾値を引くと年 32 回の誤検知になるので、`sqrt(p (1 - p) / n)` から窓の長さを決めます。

正解が無い間のシグナルは、正解率の代わりではなく、正解を急いで集めるきっかけとして置きます。elec2 では平均確信度は一度も鳴らず、拾ったのは UP と予測した割合と、PSI で見た確信度の分布でした。予測したクラスの割合と、確信度が 1 に近い予測の割合は、正解率と並べておく価値があります。

そのため、アラートは重さで 2 段に分けて、通知先を変えます。当番を呼び出すのは、正解率が SLO を割った時だけです。SLO（Service Level Objective）は、サービスとして約束した品質の水準で、本記事の例では正解率 0.70 をこの水準と置きます。

| 段 | elec2 での条件 | 通知先 | 動く速さ |
|---|---|---|---|
| 調べる | 直近 7 日の UP と予測した割合 < 0.30 | [Slack](https://slack.com/) などのチャット | 営業日のうち |
| 呼び出す | 直近 7 日の正解率 < 0.70 | [PagerDuty](https://www.pagerduty.com/) などで当番の電話 | すぐ |

elec2 は正解が 30 分後に届くので、呼び出す段もすぐ動けます。正解が 8 週遅れるモデルなら、呼び出す段が鳴るのは前の節のとおり 8 週後で、それまでは調べる段だけが頼りです。

全てのアラートで当番を呼ぶと、elec2 で価格の PSI が鳴り続けたように、鳴り止まないアラートに慣れてしまい、本当に正解率が落ちた時の呼び出しも軽く扱われます。

<br>

アラートが鳴ったら、まず予測を返すサーバーの遅延やエラー、入力の欠損や型の崩れを見て、モデルの外に原因が無いかを切り分けます。影響の大きさは、売上やコンバージョンなどの事業の指標と並べて見ます。

その上で、入力の区間ごとに正解率と予測の割合を並べます。elec2 なら、価格が最も安い区間に運用の行のうち 41% が入り、そこで UP が 25% あるのに全て DOWN と予測していることが分かります。学習した範囲から外れた入力を 1 件ずつ拾いたい時は、[異常検知](/ml/ml/anomaly-detection/)の手法が使えます。学習した範囲の外にデータが移っているなら、手を入れるのは閾値ではなくモデルなので、[再学習パイプライン](../retraining-pipeline/)で新しい期間を学習させます。

アラートごとに、鳴った時に見るものと順番を手順書（runbook）に書いておくと、当番が迷いません。

冒頭の図で、検証の 4 週は黒と赤の線が重なっていました。平均確信度が上がった時は、モデルが良くなったと読む前に、学習した期間に例外が無かった区間へデータが寄っていないかを見るのが、elec2 から持ち帰れる見方です。
