---
title: "IP-Adapter Color Cast - 参照の背景で、描いた絵の色が転ぶ"
date: 2026-11-12
draft: false
series: ["技術ノート", "Generative AI"]
tags: ["generative-ai", "image-generation", "ip-adapter", "controlnet", "diffusion", "comfyui"]
weight: 16
wrapTables: true
topics: ["Image Generation"]
---

画像生成でゲームのコマを作っていた時、4 枚で衣装の色を揃えたくて、キャラクターの立ち絵を参照画像として渡しました。参照画像を渡すと、描く絵がその見た目に寄ります。ところが、描いた 4 枚は衣装の色が揃った代わりに、絵全体の色が青に寄り、塗りも平たくなりました。本記事では、このように参照に無い色へ絵全体が寄ることを「色が転ぶ」と呼びます。原因として疑ったのは、渡した立ち絵の背景です。確認用に、濃い緑の背景を敷いた絵をそのまま渡していました。

以下は、同じことを公開モデルだけで再現した絵です。左の参照は銀の鎧を着た騎士で、背景だけを緑にしています。

{{< figure src="images/ipa_cover.webp" alt="3 枚の騎士の絵。左は緑の背景に立つ銀の鎧の参照。中央は参照なしで描いた、薄い灰色の背景に銀の鎧と黒いズボンの騎士。右は参照画像を使って描いた絵で、背景が蛍光の黄色、鎧とズボンと剣が鮮やかな青、髪が赤に変わっている" caption="背景を緑にした参照画像を使うと、背景も鎧も髪も別の色になった（1 段目・linear、seed 20261113）" align="center" >}}

参照には青も黄色も赤もありません。それでも、参照画像を使った右の絵は、背景が蛍光の黄色に、鎧が鮮やかな青に、茶色の髪が赤になりました。参照の見た目に寄せたかったのに、参照に無い色が出ています。

<br>

本記事では、参照画像で見た目を揃えようとしているエンジニアに向けて、色が転ぶ条件を手元の実験で切り分けます。変えたのは、参照の背景・使う段・効かせ方・強さの 4 つです。扱う疑問は次の通りです。

- 参照の背景色は、描いた絵のどこに出るのか。
- 背景を透明にすれば、背景の色は効かないのか。
- ノイズから描く段と描き直す段の、どちらで使うと転ぶのか。
- 2 つの効かせ方（linear と style transfer precise）で、何が違うのか。
- 色を転ばせずに、参照の色だけを写せるのか。

参照画像で顔や服を揃える手段の全体は [Character Consistency のノート](/notes/generative-ai/character-consistency/)で比べました。そのノートでは、参照画像を使うと色と塗りが崩れ、原因は推測に留めていました。本記事はその続きです。

---

### 前提: 参照の読み方と、使う段・効かせ方

[IP-Adapter](https://arxiv.org/abs/2308.06721) は、画像と文の対応を学習した [CLIP](https://arxiv.org/abs/2103.00020) と同じ仕組みの画像エンコーダーで参照画像を特徴に変え、生成の途中へ混ぜる仕組みです。特徴は、画像の中身を表す数値の列です。

画像生成のモデル（[拡散モデル](/notes/generative-ai/diffusion-model/)）は、ノイズだけの画像から始めて、数十回に分けて少しずつノイズを除き、絵にします。各回で、プロンプトを特徴に変えたものを cross-attention という層で読み、どちらへノイズを除くかを決めます。IP-Adapter は、この cross-attention に参照画像の特徴を読む口を足します。生成モデル本体の重みは変えないので、学習済みのモデルにそのまま使えます。

今回使った IP-Adapter Plus は、参照画像を 224 x 224 に縮め、14 画素四方の区画に分けます。区画は縦横 16 個ずつ、256 個です。プロンプトは、単語ほどの単位（トークン）ごとの特徴の列としてモデルに渡ります。IP-Adapter Plus は、256 区画の特徴を学習済みの変換で 16 トークン分の特徴にまとめます。それをプロンプトとは別の口で読ませ、その結果をプロンプトの結果に足します。

<br>

#### 背景も区画の 1 つとして読まれる

画像エンコーダーにとって、人物と背景の区別はありません。IP-Adapter を使うための拡張は、参照が正方形でなければ中央を正方形に切り抜きます（[拡張の説明](https://github.com/cubiq/ComfyUI_IPAdapter_plus/blob/a0f451a/NODES.md)）。全身の立ち絵で頭や足が切れないように左右へ背景を足して正方形にすると、多くの区画は背景だけを写します。以下は、本記事で使う参照を 224 x 224 に縮め、区画を重ねた図です。

{{< figure src="images/ipa_read.webp" alt="3 枚の図。左は市松模様の上に立つ騎士で、背景が透明な参照。中央は ComfyUI がその参照を読み込んだ絵で、透明だった所が黒になっている。右はそれを 224 x 224 に縮めて 16 x 16 の区画を重ねた図で、人物を含まない区画が青く塗られ、全体の 75% を占める" caption="透明な参照は、下に残った黒で読まれる。区画の 75% は背景だけ" align="center" >}}

右の図で青く塗った区画は、人物を 1 画素も含みません。全体の 75% です。画素で数えると、人物は参照全体の約 15% しかありません。

今回は、ノードをつないで生成の流れを組むツールの [ComfyUI](https://github.com/Comfy-Org/ComfyUI) を使いました。画像を読み込むノードの LoadImage は、透明度をマスクとして別に出し、画像としては RGB だけを渡します。IP-Adapter に渡るのはこの RGB です。透明な画素の下にも RGB の値は残っていて、それがそのまま読まれます。左の参照は、背景を抜いた時に透明な画素の下に黒が残っていたので、中央のように黒い背景の絵として読まれました。下に白を残した参照なら、白い背景として読まれます。読み込んで保存し直すだけの流れで、どちらも確認しました。

透明な背景は「背景が無い」ことにはなりません。下に何色が残っているかは、背景を抜いた道具で変わります。ComfyUI の背景抜きノードで作った透過 PNG にも、描いた時の背景色が残ることを [Background Removal のノート](/notes/generative-ai/background-removal/)で確認しました。

<br>

#### 使う段

参照画像を使う段は 2 つ比べます。本記事では、ノイズだけの状態から描く段（txt2img）を 1 段目と呼びます。1 段目では、3D モデルから書き出した深度マップを [ControlNet](/notes/generative-ai/controlnet/) で渡し、姿勢を縛ります。深度マップは、カメラからの距離を明るさで表した白黒の画像です。

参照なしの 1 段目で描いた絵を [img2img](/notes/generative-ai/img2img-denoise/) で描き直す段は、2 段目と呼びます。denoise は 0.45 で、ノイズを除く道のりの後半 45% だけを描き直します。2 段目でも同じ深度マップを渡します。構図と大まかな色は、元の絵で決まっています。

<br>

#### 効かせ方: linear と style transfer precise

ComfyUI で IP-Adapter を使うための拡張の [ComfyUI_IPAdapter_plus](https://github.com/cubiq/ComfyUI_IPAdapter_plus) には、参照画像を効かせる場所を選ぶ weight type という設定があります。本記事では効かせ方と呼びます。

今回のモデルは、SDXL という画像生成モデルを元にしています。SDXL の本体は U-Net という形で、画像を縮めながら読む下りの部分と、元の大きさへ戻しながら描く上りの部分があります。cross-attention を含むブロックは、下りに 4 か所、中央に 1 か所、上りに 6 か所の計 11 か所あり、効かせ方によって使う場所が変わります。

{{< figure src="images/ipa_layers.webp" alt="SDXL の U-Net で参照を読むブロック 11 か所が、下り 4 か所、中央 1 か所、上り 6 か所の U 字に並ぶ図。上段の linear は 11 か所すべてが青い。下段の style transfer precise は、上り 2（6 番）だけが青く色・質感と書かれ、下り 4（3 番）が橙で配置（遠ざける）と書かれ、ほかは灰色" caption="linear と style transfer precise が参照を読ませる場所" align="center" >}}

linear は 11 か所すべてに同じ重みで参照を足します。style transfer precise は、6 番の 1 か所にだけ足します。この場所は、[InstantStyle](https://github.com/InstantStyle/InstantStyle) が「色・材質・雰囲気」を受け持つと報告した層です。3 番は、同じく配置を受け持つと報告された層です。style transfer precise はここで参照を打ち消す側に回し、参照の構図から遠ざけます。この割り当ては拡張のコードで確認しました。

つまり style transfer precise は、構図を写さずに、色と質感だけを写すための効かせ方です。色だけを渡すので、背景の色も渡りやすいのではないか、という疑問が出ます。

---

### 実験の作り方

参照は、公開モデルの [WAI-illustrious-SDXL v17.0](https://civitai.com/models/827184?modelVersionId=2883731) で描いた、銀の鎧を着た騎士です。白い背景で描いた絵から人物を切り抜き、背景を白・黒・緑に差し替えて、左右に背景を足した正方形にしました。透明の参照は、前の図で見た通り黒い背景と同じに読まれるので、黒で代表させています。

生成する絵も同じモデルで描きます。姿勢は [Animation Flicker のノート](/notes/generative-ai/animation-flicker/)で作った 3D モデルの深度マップで縛り、プロンプトは「銀の鎧、暗い色のズボン、白い背景の騎士」です。参照の強さ（weight）は 0.6 です。seed は最初のノイズを決める数で、同じなら同じ絵になります。これを 3 通りに変えました。

参照の背景 3 通り × 効かせ方 2 通り × 段 2 通り × seed 3 通りで 36 枚です。これに、参照なしの 1 段目と、それを参照なしのまま描き直した 2 段目を 3 枚ずつ加えた 42 枚が、銀の参照で比べた絵です。

ComfyUI の API には、ノードを ID で結んだ辞書を送ります。参照画像を使う所は IPAdapterAdvanced のノード 1 つで、条件ごとに変えたのは、参照画像と weight（強さ）と weight_type（効かせ方）です。

```python
wf["33"] = {"class_type": "IPAdapterAdvanced", "inputs": {
    "model": ["1", 0], "ipadapter": ["30", 0], "image": ["32", 0], "clip_vision": ["31", 0],
    "weight": weight, "weight_type": TYPES[wtype], "combine_embeds": "concat",
    "start_at": 0.0, "end_at": 1.0, "embeds_scaling": "V only"}}
wf["6"]["inputs"]["model"] = ["33", 0]   # KSampler は参照を足したモデルで描く
```

全体の台本は [lab/run.py](https://github.com/nao1215/debimate/blob/main/content/notes/generative-ai/ip-adapter-color-cast/lab/run.py) にあります。

<br>

#### 色の数え方

色の転びは、[CIELAB](https://en.wikipedia.org/wiki/CIELAB_color_space)（L\*a\*b\*）で 2 つの数値に分けて数えます。L\* は明るさ、a\* と b\* は色みです。a\* と b\* が 0 なら灰色で、0 から離れるほど鮮やかになります。

1 つ目は人物の彩度 C\* です。深度マップで 3D モデルが写っている画素について、a\* と b\* の長さを平均します。参照の騎士は銀と焦げ茶の服なので 3.9 しかなく、参照なしの絵も 4〜6 です。赤いマントと青い陣羽織を着た騎士でも、人物全体の平均は 20 でした。参照に無い色が出ると、この値が上がります。

2 つ目は背景と白の差 ΔE です。3D モデルから 48 画素より離れた所の平均色と、真っ白との L\*a\*b\* の距離です。プロンプトで白い背景を頼んでいるので、0 に近いほど頼んだ通りです。ΔE がおよそ 2.3 で、並べて見た色の違いが人に分かるとされています（[Color difference](https://en.wikipedia.org/wiki/Color_difference)）。参照なしでも、seed によっては薄い灰色の背景になるので、1〜6 の幅があります。

```python
def lab(path):
    rgb = np.asarray(Image.open(path).convert("RGB"), np.float32) / 255
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2Lab)   # L* 0〜100、a* と b* は 0 が灰色

img = lab(path)
chroma = np.hypot(img[body][:, 1], img[body][:, 2]).mean()      # 人物の彩度 C*
back_dE = np.linalg.norm(img[back].mean(axis=0) - (100, 0, 0))  # 背景と白の差 ΔE
```

---

### 1 段目は、背景が白でも色が転ぶ

以下は、seed を 1 つに固定し、段（行）と、参照の背景・効かせ方（列）を変えた絵です。

{{< figure src="images/ipa_grid.webp" alt="2 行 7 列の騎士の絵。列は参照なし、白・precise、白・linear、黒・precise、黒・linear、緑・precise、緑・linear。1 段目の行では、参照画像を使った 6 枚とも鎧が青みを帯び、linear の 3 枚は髪が赤や橙になり、黒・linear は全体が鮮やかな青、緑・linear は背景が蛍光の黄色。2 段目の行では、precise の 3 枚は参照なしとほぼ同じで、linear の 3 枚は全体が青黒く、緑・linear は背景が黄土色" caption="段と、参照の背景・型を変えた絵（銀の参照、seed 20261113）" align="center" >}}

1 段目の行では、参照画像を使った 6 枚がすべて青みを帯びました。参照は銀と焦げ茶の騎士で、背景が白でも同じです。linear では、茶色の髪が赤や橙になり、背景が黒なら全身が鮮やかな青に、背景が緑なら背景が蛍光の黄色になりました。

2 段目の行は様子が違います。style transfer precise の 3 枚は、背景が黒でも緑でも、参照なしの絵とほとんど見分けが付きません。linear の 3 枚は、全体が青黒くなり、緑の背景では背景が黄土色に寄りました。

<br>

#### 数値で見ると

3 seed の値を並べると、以下のようになります。1 つの点が 1 枚です。

{{< figure src="images/ipa_metrics.webp" alt="2 つの点のグラフ。縦は参照なし、白・precise、白・linear、黒・precise、黒・linear、緑・precise、緑・linear。左の人物の彩度 C* は、参照なしが 4〜6、1 段目は precise が 12〜18、linear が 16〜67、2 段目は precise が 6〜11、linear が 9〜28。右の背景と白の差 ΔE は、参照なしが 1〜6、1 段目の緑・linear が 7〜79、1 段目の緑・precise が 3〜18、2 段目の緑・linear が 3〜14、それ以外は概ね 1〜12" caption="人物の彩度と、背景と白の差（銀の参照、各 3 seed。右の横軸は 10 より先を縮めた）" align="center" >}}

人物の彩度は、1 段目で使うと背景が何色でも 12 以上に上がりました。style transfer precise で参照なしの 3 倍前後、linear ではそれ以上です。背景と白の差を最も大きくしたのは、背景が緑の参照を linear で使った組です。黒の背景は、背景よりも人物の彩度に強く出ました。段と効かせ方ごとにまとめると、次の通りです。

| 段 | 効かせ方 | 人物の彩度 C\* | 背景と白の差 ΔE |
|---|---|---|---|
| 参照なし | | 4〜6 | 1〜6 |
| 1 段目 | style transfer precise | 12〜18 | 2〜18 |
| 1 段目 | linear | 16〜67 | 3〜79 |
| 2 段目 | style transfer precise | 6〜11 | 1〜7 |
| 2 段目 | linear | 9〜28 | 1〜14 |

1 段目は、構図も色もノイズから決める段です。参照の特徴が加わると、全体の色調がそれに引っ張られます。2 段目では、構図と大まかな色が元の絵で決まっていて、参照が動かせる幅が小さくなります。2 段目の style transfer precise がほとんど効かなかったのは、参照を足すのが 11 か所のうち 1 か所だからと見ています。linear は 11 か所すべてに足すので、2 段目でも色を動かします。

---

### 人物のいない 1 枚を参照にする

1 段目の青みが、参照の騎士から来るのか、参照画像を使うこと自体から来るのかを分けるために、人物のいない真っ白と真っ緑の 1 枚を参照にして、1 段目を描きました。

{{< figure src="images/ipa_blank.webp" alt="2 行 3 列の図。上の行は真っ白の参照と、それを 1 段目に precise と linear で使った絵で、どちらも背景がクリーム色になり、鎧と服が茶色のセピア調になる。下の行は真っ緑の参照と、それを使った絵で、precise は背景がくすんだ緑、linear は背景が明るい黄緑になり、ズボンが緑になる" caption="人物のいない参照を 1 段目で使った絵（seed 20261113）" align="center" >}}

真っ緑の参照では、背景が緑になりました。style transfer precise ではくすんだ緑、linear では明るい黄緑です。style transfer precise でも、背景と白の差は 3 seed 中 2 枚で 53〜58 です。残る 1 枚は背景が白いままでしたが、ズボンが緑になりました。参照の色は、場所を問わずに絵のどこかへ移ります。

真っ白の参照も、無色ではありませんでした。背景はクリーム色に、鎧と服はセピア調になり、背景と白の差は 8〜14 です。画像エンコーダーは、白一色の画像を「白」ではなく「古い紙の絵」のような特徴として読んだと見ています。一方、銀の騎士を載せた参照では、1 段目の絵は青みを帯びました。モデルは、銀の鎧が持つ光沢を青い金属として読んだと見ています。どちらも推測で、検証していません。

確かなのは、参照の背景色が絵に移ること、そして背景の無い画像でも、参照は何かの色調を運ぶことです。1 段目の転びは、参照の背景だけでは決まりません。

---

### 重みで加減する

参照の強さを 0.3・0.6・0.9 に変えました。上の行は 1 段目に白の参照を style transfer precise で、下の行は 2 段目に緑の参照を linear で使った絵です。

{{< figure src="images/ipa_weight.webp" alt="2 行 3 列の騎士の絵。上の行は 1 段目に白の参照を precise で使ったもので、重み 0.3 は鎧がわずかに青く、0.6 で青みが増え、0.9 では背景まで青白く、剣が青い。下の行は 2 段目に緑の参照を linear で使ったもので、重み 0.3 は参照なしとほぼ同じ、0.6 で全体が青黒く背景が黄土色、0.9 で顔が桃色になり輪郭が光る" caption="参照の強さ 0.3・0.6・0.9（銀の参照、seed 20261113）" align="center" >}}

1 段目の style transfer precise では、人物の彩度が 0.3 で 9〜10、0.6 で 12〜17、0.9 で 20〜24 と、重みにほぼ比例して上がりました。0.3 でも、参照なしの 4〜6 には戻りません。

2 段目の linear は、0.3 なら背景と白の差が 1〜6 で、参照なしと同じ範囲に収まりました。人物の彩度も 6〜8 で、参照なし（4〜6）に近い値です。0.6 から先で崩れます。緑の背景でも、2 段目で弱く使う限りは転ばない、ということです。

---

### 写したい色も届かない

ここまでは、参照に無い色が出る話でした。最後に、参照の色を写したい場合を見ます。参照は赤いマントと青い陣羽織の騎士に替え、白い背景・style transfer precise で描きました。プロンプトには、マントも陣羽織も書いていません。

{{< figure src="images/ipa_want.webp" alt="4 枚の騎士の絵。左の参照は赤いマントと青い陣羽織を着ている。参照なしの絵は銀の鎧だけ。1 段目に precise で使った絵は胸が青く、腕に赤い帯が出て、鎧全体も青みを帯びる。2 段目に precise で使った絵は、襟元が少し青く膝に赤が少しあるだけで、参照なしとほぼ同じ" caption="赤いマントと青い陣羽織の参照で、1 段目と 2 段目で使った絵（seed 20261113）" align="center" >}}

1 段目で使うと、胸に青い陣羽織が出て、腕に赤い帯が出ました。参照の色が写っています。ただし、銀の鎧まで青みを帯びました。2 段目で使うと、襟元が少し青くなり、膝に赤が少し出ただけで、陣羽織は出ません。人物の彩度は、1 段目で 16〜20、2 段目で 6〜12 でした。赤いマントは、どちらの段でも出ませんでした。

2 段目で style transfer precise を使うと、色は転ばない代わりに、参照の色もほとんど届きません。1 段目で使うと、参照の色は届く代わりに、参照に無い色調も一緒に付いてきます。今回の範囲では、写したい色だけを取り出す効かせ方は見つかりませんでした。

冒頭で触れたゲームのコマでは、参照の背景を白に替えると青みが消えました。その時は[画風 LoRA](/notes/generative-ai/lora/) を当てた別の構成で、今回の公開モデルだけの構成では、白の背景でも 1 段目の青みは残りました。背景を白にすれば転ばない、とは言い切れません。

---

### 参照を渡す前に見ること

参照画像で見た目を揃えたい時は、次の順に確認すると、色が転ぶ原因を切り分けられます。

<br>

#### 参照の背景

最初に、参照の背景を見ます。背景の色は、描いた絵の色調を変えます。真っ緑の参照では背景やズボンが緑になり、背景を緑にした騎士の参照では黄色や青が出ました。合成用の緑や確認用の色を敷いた絵は、そのまま渡しません。透明な背景は、下に残った色で読まれるので、白で塗りつぶしてから渡します。全身の立ち絵は、正方形にすると区画の多くが背景になります。

<br>

#### 使う段と効かせ方

次に、使う段を決めます。参照の色を写したいなら 1 段目ですが、参照に無い色調も付いてくるので、style transfer precise を 0.3 程度の弱さから試します。転びを避けたいなら 2 段目ですが、参照の色もほとんど届きません。linear は、どちらの段でも強く使うと髪の色や塗りまで変えるので、2 段目に 0.3 程度で使うのが、今回試した中での上限でした。

<br>

#### プロンプトに色を書く

参照で色が揃わない時は、プロンプトに色の語を書く方が確実な場合もあります。本記事で使った青い陣羽織の参照は、参照画像を使わず、プロンプトに「red cape, blue tabard」（赤いマント、青い陣羽織）と足して描いたものです。seed を 3 通り変えて、3 枚とも赤いマントと青い陣羽織になりました。

<br>

<details>
<summary>実験の条件とファイル</summary>

- 生成: ComfyUI 0.35.0、[WAI-illustrious-SDXL v17.0](https://civitai.com/models/827184?modelVersionId=2883731)、[ControlNet Union（ProMax）](https://huggingface.co/xinsir/controlnet-union-sdxl-1.0/tree/801a4a3) の depth、[SDXL 向けの IP-Adapter Plus](https://huggingface.co/h94/IP-Adapter/tree/018e402)（`ip-adapter-plus_sdxl_vit-h`、画像エンコーダーは OpenCLIP の ViT-H-14）。steps 28、CFG 5.5、euler_ancestral
- 参照・計測・図: [lab/make_refs.py](https://github.com/nao1215/debimate/blob/main/content/notes/generative-ai/ip-adapter-color-cast/lab/make_refs.py)、[lab/measure.py](https://github.com/nao1215/debimate/blob/main/content/notes/generative-ai/ip-adapter-color-cast/lab/measure.py)、[figures.py](https://github.com/nao1215/debimate/blob/main/content/notes/generative-ai/ip-adapter-color-cast/figures.py)
- 絵ごとの数値: [lab/metrics_plain.json](https://github.com/nao1215/debimate/blob/main/content/notes/generative-ai/ip-adapter-color-cast/lab/metrics_plain.json)（銀の参照）、[lab/metrics_color.json](https://github.com/nao1215/debimate/blob/main/content/notes/generative-ai/ip-adapter-color-cast/lab/metrics_color.json)（青い陣羽織の参照）、[lab/metrics_blank.json](https://github.com/nao1215/debimate/blob/main/content/notes/generative-ai/ip-adapter-color-cast/lab/metrics_blank.json)（人物のいない参照）
- 手順・バージョン・ライセンス: [lab/README.txt](https://github.com/nao1215/debimate/blob/main/content/notes/generative-ai/ip-adapter-color-cast/lab/README.txt)

</details>

<br>
