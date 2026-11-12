#!/usr/bin/env bash
# nao1215 の文体ルールのうち、機械的に検出できる違反を洗い出す。
#
# 使い方:
#   bash style_check.sh <記事の .md パス> [...]
#
# 対象: content/notes/ (create-tech-notes)、projects/ml/notes/ (create-ml-notes)、
#       content/post/ja/ (write-tech-post) のいずれも です・ます体なので共通で使える。
#
# 終了ステータス: 違反が 1 件でもあれば 1、無ければ 0。
#
# 検出できないもの (目視で確認する): 見出し直下のリード文、比喩の種類、
# 段落の長さ、緩衝表現の回数、内容の正確さ。

set -u

here="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
status=0

report() {
  # $1: ラベル, $2: ファイル, $3: grep の結果
  if [ -n "$3" ]; then
    echo "  [NG] $1"
    echo "$3" | sed 's/^/       /'
    status=1
  fi
}

for f in "$@"; do
  if [ ! -f "$f" ]; then
    echo "not found: $f"
    status=1
    continue
  fi

  echo "== $f"

  # 本文だけを見る (front matter とコードフェンスを除去する)。
  # 行番号を原文と一致させるため、除去する行は空行に置き換える
  body=$(awk '
    NR==1 && $0=="---" { fm=1; print ""; next }
    fm==1 { if ($0=="---") fm=0; print ""; next }
    /^[ \t]*```/ { code = !code; print ""; next }
    { if (code) print ""; else print }
  ' "$f")

  # 1. 助詞「を」の直後の読点。語順を変えて回避する
  report "助詞「を」の直後に読点「、」がある" "$f" \
    "$(echo "$body" | grep -n 'を、' | head -20)"

  # 2. 太字。地の文の強調では使わない (概念名は「」で囲む)
  report "太字 ** が使われている" "$f" \
    "$(echo "$body" | grep -n '\*\*' | head -20)"

  # 3. である体の混入 (ノート・記事はいずれも です・ます体)。
  #    箇条書きと表のセルは常体のままが正しいので、地の文だけを見る。
  prose=$(echo "$body" | grep -nvE '^\s*([-*+]|[0-9]+\.|\|)')
  report "である体が混入している" "$f" \
    "$(echo "$prose" | grep -E '(である。|であった。|だった。|ではない。|と思う。)' | head -20)"

  # 4. LLM っぽい締め
  report "LLM っぽい締めがある" "$f" \
    "$(echo "$body" | grep -nE '(いかがでした|お役に立て|ぜひ参考|ぜひ試して|最後まで読んで|次のステップ)' | head -20)"

  # 5. 本人が使わないと明言した語
  report "本人が使わない語がある (ざっくり / 実務では / 現場では / 業務では)" "$f" \
    "$(echo "$body" | grep -nE '(ざっくり|大雑把に言え|実務では|現場では|業務では)' | head -20)"

  # 6. 感情形容詞
  report "感情形容詞がある" "$f" \
    "$(echo "$body" | grep -nE '(素晴らしい|強力な|革命的|驚くべき|凄い|すごい)' | head -20)"

  # 7. リスト記号のアスタリスク (ハイフンに統一する)
  report "リスト記号に * が使われている" "$f" \
    "$(echo "$body" | grep -nE '^\* ' | head -20)"

  # 8. 数式の LaTeX 形式 (KaTeX 未設定のため表示が崩れる)
  report "数式が LaTeX 形式になっている" "$f" \
    "$(echo "$body" | grep -nE '\$[^$]*\\\\[a-zA-Z]+[^$]*\$' | head -20)"

  # 9. 自己言及。2026-11-02 から「本記事」に揃えた (writing_style.md §0・§2-12。
  #    著者が調整した Wallet ノートと debimate-visual-notes に合わせる)。
  #    「本ノート」「このノート」「この記事」「本稿」を検出する。以下の旧経緯は参考:
  #    「ノート」の自己言及。「本稿」「本記事」も同じ理由で使わない
  #    (writing_style.md §2-12、2026-08-10 に B-Tree ノートで混入)
  #    例外は 1 つで、範囲を宣言する「本ノートでは、〜を扱い、〜は対象外とします」
  #    は許す。範囲の持ち主が文中に現れないと、読者が「何の範囲だ」で止まる
  #    (2026-08-11 ユーザー指摘、§14 型1)。2026-08-18 に 2 文の形
  #    「本ノートで、説明する範囲も決めておきます。」を廃し、1 文へ畳んだ (§26)
  #    引用の訳文に出る「本稿では」(原著者の自己言及) は誤検知なので、
  #    英語の引用と、その直後の全角括弧の訳を落としてから見る
  selfref=$(echo "$body" | python3 -c '
import re, sys
for i, line in enumerate(sys.stdin.read().split("\n"), 1):
    t = re.sub(r"「[^「」]*」", "", line)
    t = re.sub(r"（[^（）]*）", "", t)
    if re.search(r"(この|本)ノート|本稿|この記事", t):
        print(f"{i}:{line[:120]}")
')
  report "自己言及が「本記事」以外になっている (「本記事」へ)" "$f" "$(echo "$selfref" | head -20)"

  # 9.02. 範囲の宣言を 2 文に割っている (§14 型1・§26)。「これから範囲を決めます」
  #       と予告してから中身を書く形は、前半が実況文になる。1 文へ畳む
  report "範囲の宣言を予告文から始めている (「本記事では、〜を扱い、〜は対象外とします」の 1 文へ)" "$f" \
    "$(echo "$body" | grep -nE '(説明する|扱う)範囲(も|を)(決めて|示して|明確に)' | head -20)"

  # 9.03. 文章を実況している (§26、2026-08-18 ユーザー指摘)。「これから何を説明するか」
  #       を説明する文は内容を増やさず、書き手が文章構成を実況しているように読める。
  #       説明したい内容そのものから書き始める。
  #       主語が仕組みの側にある文 (「Router が値を確認します」) を巻き込まないよう、
  #       書き手の動作として現れる言い回しだけを拾う
  report "文章を実況する言い回しがある (説明したい内容そのものから書く)" "$f" \
    "$(echo "$body" | grep -nE '見ていきましょう|考えてみます|考えていきます|(整理|確認|説明)しておきます|(範囲|前提|方針)(も|を)決めておきます|押さえておきます|触れておきます|について(説明|解説)します|を説明していきます|順に(見て|追って)いきます' | head -20)"

  # 9.035. 節末の橋渡し「〜から見ていきます」(2026-11-02 Wallet で承認済み。1 本に 2 回まで)
  mite=$(echo "$body" | grep -nE '見ていきます' | head -10)
  nmite=$(echo "$mite" | grep -c ':')
  if [ "$nmite" -ge 3 ]; then
    echo "  [INFO] 「見ていきます」が ${nmite} 件 (節末の橋渡しは 1 本に 2 回まで)"
    echo "$mite" | sed 's/^/       /'
  fi

  # 9.036. 表記 (writing_style.md §0、2026-11-02 ユーザー決定「最近の記事に合わせる」)。
  #        2023 年以降の記事は ユーザー 69:0、サーバー 69:0、パーサー 16:0、
  #        すること 53:する事 2、るもの 13:る物 1。熟語 (記事・仕事・事故・荷物) は除く
  report "表記が旧形になっている (ユーザー・サーバー・パーサー、形式名詞のこと・もの・わけへ)" "$f" \
    "$(echo "$body" | python3 -c '
import re, sys
pat = re.compile(r"ユーザ(?!ー)|サーバ(?!ー)|パーサ(?!ー)|(?<=[ぁ-ん」])(?<![はがをにでとへもや])事(?![件務例前実情柄故業象態項典後者])|(?<=[ぁ-ん])(?<![はがをにでとへもや])物(?![理質体語流事])|訳では|訳がない|訳です")
for i, line in enumerate(sys.stdin.read().split("\n"), 1):
    if line.lstrip().startswith(("%%{", "classDef")): continue
    t = re.sub(r"`[^`]*`|\]\([^)]*\)|https?://\S+", "", line)
    t = re.sub(r"(入れ|持ち|詰め|買い|忘れ|生き|食べ|飲み|乗り|贈り|読み|書き|作り)物|(考え|悩み|頼み|決め|隠し|揉め|習い|願い|困り)事", "", t)
    m = pat.findall(t)
    if m: print(str(i) + ":[" + " ".join(sorted(set(m))) + "] " + line[:100])
' | head -20)"

  # 9.04. 「本記事では」の繰り返し (違反ではなく情報。§26)。範囲の宣言は
  #       ノート全体で 1 回に留める。節ごとに繰り返すと実況になる
  honnote=$(echo "$body" | grep -nE '本記事では' | head -10)
  nhonnote=$(echo "$honnote" | grep -c ':')
  if [ "$nhonnote" -ge 3 ]; then
    echo "  [INFO] 「本記事では」が ${nhonnote} 件 (導入で 1〜2 回に留め、節ごとに繰り返さない)"
    echo "$honnote" | sed 's/^/       /'
  fi

  # 9.05. 「まず」「次に」「最後に」で段落を始めている (違反ではなく情報。§26)。
  #       文章の構成の説明として使っているなら削る。処理の順序を説明する
  #       「まず prepare を送ります」は正しい用法なので、判断を残して INFO で出す
  jikkyou=$(echo "$body" | grep -nE '^(まず|次に|最後に|続いて|ここからは)[、,]' | head -20)
  njikkyou=$(echo "$jikkyou" | grep -c ':')
  if [ "$njikkyou" -ge 2 ]; then
    echo "  [INFO] 「まず／次に／最後に」で始まる段落が ${njikkyou} 件 (文章の構成の説明なら削る。処理の順序の説明なら残す)"
    echo "$jikkyou" | sed 's/^/       /'
  fi

  # 9.3. 人名の敬称 (§12、2026-08-11 ユーザー指摘)。ノートは他人の論文・資料・
  #      ブログを引いて成り立つので、本文の人名には「氏」を付ける。
  #      リンクの URL は人名と同じ綴りを含む事があるため先に落とす
  #      (ledsun.hatenablog.com など)。一覧に無い人名は検出できないので、
  #      新しい人名を本文へ出したら、ここへも足す
  names='和田卓人|Fowler|Evans|Dahan|Hayashibara|Joshi|Hieatt|Mee|Young|Burns|Vernon|Lamport|Gray|Oppenheimer|Karwin|Berenson|Bernstein|Melton|ledsun'
  #      姓だけを並べる。「Martin Fowler 氏」のような下の名前付きは姓が
  #      拾うので二重に書かない。Alice・Bob のような架空の登場人物は人名
  #      ではないので入れない
  report "人名に敬称「氏」が付いていない (書名・引用文・URL の中は除く)" "$f" \
    "$(echo "$body" | sed -E 's#https?://[^ )]*##g' \
        | grep -nP "($names)(?!\s*氏)" | head -20)"

  # 9.5. 断定を避ける言い回し・名詞化 (§11)
  report "事実を膨らませる言い回しがある (§11 で言い切りへ)" "$f" \
    "$(echo "$body" | grep -nE '(する形です|として知られて|と言われています|そもそも)' | head -20)"

  # 9.7. 「ここでは」「以下では」が段落の先頭に来ている (実測 0 件の形)。
  #      直前の文を受ける語なので、段落を改めると受ける対象が離れてしまう
  report "「ここでは」「以下では」が段落の先頭にある (直前の文へ続ける)" "$f" \
    "$(echo "$body" | grep -nE '^(ここでは|以下では)' | head -20)"

  # 9.71. 節を数えて参照している (writing_style.md §14 型4、2026-08-10)。
  #       読者は見出しを数え直す事になり、節を足すと記述が古くなる。
  #       節は見出しの文字列でそのまま呼ぶ
  report "節を数えて参照している (見出しの文字列で呼ぶ)" "$f" \
    "$(echo "$body" | grep -nE '(最後|最初)から *[0-9０-９一二三四五六七八九] *[つ番]目の節|[0-9０-９一二三四五六七八九] *[つ番]目の節' | head -20)"

  # 9.72. 図の中を左右で指している (writing_style.md §12、2026-08-10)。
  #       flowchart は LR と TB で枝の並ぶ向きが変わるため、位置は当てにならない。
  #       図中のラベルで呼ぶ。ただし、subgraph に名前が付いた 2 枚並びの比較図で
  #       「上図の右側」と書く形は既存ノートにもあり、木の中の兄弟を指す「右の
  #       ノード」のように対象そのものの性質を指す用法もあるため、判断を残して
  #       INFO で出す。「上図」と隣接する場合と、枝を左右で呼ぶ場合だけを拾う
  figside=$(echo "$body" | grep -nE '[上下]図の[左右](の|側)|[左右](の|側)の(経路|枝|矢印)' | head -20)
  if [ -n "$figside" ]; then
    echo "  [INFO] 図の中を左右で指している (図中のラベルで呼べないか検討する)"
    echo "$figside" | sed 's/^/       /'
  fi

  # 9.73. 出典リンクが述語 1 語だけに掛かっている (writing_style.md §14 型4)。
  #       リンクテキストが「書いています」では何の出典か分からない。
  #       出典の名前をリンクにして、述語は地の文へ出す
  report "出典リンクが述語 1 語だけに掛かっている (出典名をリンクにする)" "$f" \
    "$(echo "$body" | grep -nE '\[(書いて|説明して|述べて|定義して|示して|断って|挙げて|求めて|注意して)います\]\(' | head -20)"

  # 9.74. 出典リンクが主張の文を丸ごと囲んでいる (writing_style.md §14 型4、
  #       2026-08-14 ユーザー指摘)。リンクは下線で描画されるため、範囲を
  #       広げると本文が下線で埋まる。英語の引用そのものか、出典の名前だけに絞る。
  #       述語で終わるリンクテキストを拾う。英語引用は「」の内側なので当たらない
  report "出典リンクが主張の文を囲んでいる (英語の引用か出典名だけに絞る)" "$f" \
    "$(echo "$body" | grep -noE '\[[^][]{18,}(ます|です|ました|ません|ており)\]\(' | head -20)"

  # 9.75. 同じ段落の中で同じ URL を 2 回リンクしている (writing_style.md §14 型4)。
  #       2 文目は「同じドキュメント」「同じページ」で受けてリンクは 1 回にする。
  #       節をまたいだ再引用は対象外なので、段落 (1 行) の中だけを見る。
  #       英語引用 (「[...](URL)」) は引用ごとに出典へ結び付けるので除外する
  report "同じ段落で同じ URL を 2 回リンクしている (2 回目は「同じドキュメント」で受ける)" "$f" \
    "$(echo "$body" | awk '{
        delete seen
        s = $0
        while (match(s, /\]\(https?:\/\/[^)]+\)/)) {
          u = substr(s, RSTART + 2, RLENGTH - 3)
          rest = substr(s, RSTART + RLENGTH)
          if (substr(rest, 1, 3) != "」") {   # 英語引用のリンクは数えない
            if (u in seen) { print NR ": " u; break }
            seen[u] = 1
          }
          s = rest
        }
      }' | head -10)"

  # 9.8. 例示を文末で後付けしている形 (§7)。
  #      「例えば」「具体的には」で書き出し、読者が読み始める前に例だと分かるようにする
  report "例示が文末で後付けになっている (「例えば」「具体的には」で書き出す)" "$f" \
    "$(echo "$body" | grep -nE 'といった(設定|形|使い方|運用|構成|作り|やり方)|みたいな(形|感じ|設定)' | head -20)"



  # 9.11. 「〜の側」(§11)。名詞に「側」を付けても情報が増えず、主語がぼやける。
  #       「呼び出し側」「利用する側」「外側」「内側」は動作主体・方向を指すので当たらない
  report "「〜の側」が使われている (側を外して主語を名指しする)" "$f" \
    "$(echo "$body" | grep -n 'の側' | head -20)"

  # 9.12. 「こちら」「そちら」「あちら」(§11)。ノートは読者を登場人物の立場に
  #       置いていないため、指示語が指す先を読者が復元できない。名前で書く
  report "「こちら」「そちら」「あちら」で対象をぼかしている (名前で書く)" "$f" \
    "$(echo "$body" | grep -nE 'こちら|そちら|あちら' | head -20)"

  # 9.12b. 引用だけの段落・行 (§9・§23)。引用が地の文から切り離されると、読者は
  #        その引用を誰が何のために出したのかを自分で補う事になる。200 字を守る
  #        ために引用を独立させた形が典型で、直す先は引用の長さである
  report "引用だけの段落・行がある (地の文の文に埋める。長いなら引用を短く取り直す)" "$f" \
    "$(echo "$body" | grep -nE '^「(\[)?[^」]{20,}」（[^）]*）[ 　]*$' | head -10)"

  # 9.12c. 版番号・草案番号・記号の識別子を主語にしている (§25)。読者はその識別子が
  #        何だったかを覚えていないので、思い出す作業が文ごとに発生する。3 件以上で
  #        一覧にする。初出の紹介は主語でなくてよい
  idsubj=$(echo "$body" | grep -nE '(draft-[0-9]+|RFC [0-9]+|CVE-[0-9]{4}-[0-9]+|ADR-[0-9]+|v[0-9]+\.[0-9]+) は' | head -20)
  if [ "$(echo "$idsubj" | grep -c .)" -ge 3 ]; then
    report "識別子を文の主語にしている (概念か、その仕様が定めている物を主語にする)" "$f" "$idsubj"
  fi

  # 9.12d. 範囲宣言を固定の型で書いている (§14 型1)。本人の 54 万字に `〜を扱い、`
  #        は 0 件で、ノート 49 本のうち 22 本にだけ出る。扱う事だけを 1 文で書き、
  #        動詞は中身に合わせて変える (→ references/voice_markers.md 表 4)
  report "範囲宣言が固定の型になっている (扱う事だけを 1 文で。動詞は中身に合わせて変える)" "$f" \
    "$(echo "$body" | grep -nE 'を扱い、.*(対象外|扱いません|触れません)' | head -5)"

  # 9.12e. 数を文頭に置いている。本人も書くが密度が違う (1 万字あたり 本人 0.2 /
  #        ノート 2.9)。違反ではなく一覧で出し、列挙が続くなら表か箇条書きへ移す
  numhead=$(echo "$body" | grep -nE '(^|。)[ 　]*[0-9１-９]+ ?つ(は|目|あります|です)' | head -8)
  if [ "$(echo "$numhead" | grep -c .)" -ge 2 ]; then
    echo "  [INFO] 数を文頭に置いた箇所 (本人の 14 倍の密度。列挙が続くなら表か箇条書きへ)"
    echo "$numhead" | sed 's/^/       /'
  fi

  # 9.13. 先送りで文を埋めている (§18)。答えを 1 文で書かずに「後で扱う」とだけ
  #       書くと、読者は待たされるだけで何も受け取れない。拾い読みでは空白と同じ
  report "先送りで文を埋めている (答えを 1 文で書いてから、展開する場所を添える)" "$f" \
    "$(echo "$body" | grep -nE '後で(扱|述べ|説明|見)|だけを見てください|以下の主題|後述(します|する)|次(節|章)で(扱|説明)' | head -20)"

  # 9.14. 出典のページ番号 (§19)。読者が現物を持っていないと検証できない。
  #       節番号は本文が公開されていてリンクから辿れるので対象外
  report "出典にページ番号を書いている (書名と引用文だけで出典は成立する)" "$f" \
    "$(echo "$body" | grep -nE '[0-9]+ *ページ(から|の一文|で)|pp?\. *[0-9]+' | head -20)"

  # 9.14.1. 英語の引用に日本語訳が付いていない (§23)。ノートは日本語で読まれるので、
  #        原文だけを置くと読者が翻訳を担う事になる。「英語」の直後に全角括弧で訳を置く。
  #        除外するのは、題名 (論文・文書・白書・仕様) と、日本語の説明に原文を添えた形。
  #        識別子や短い語は訳さないので、3 語以上で英字比率の高い引用だけを見る
  report "英語の引用に日本語訳が付いていない (「英語」（日本語訳）の形にする)" "$f" \
    "$(echo "$body" | python3 -c '
import re, sys
title = re.compile(r"(論文|文書|白書|仕様|規格|記事|書名|題)$")
for i, line in enumerate(sys.stdin.read().split("\n"), 1):
    if "原文" in line:
        continue
    for m in re.finditer(r"「([^「」]*)」", line):
        q = m.group(1)
        latin = len(re.findall(r"[A-Za-z]", q))
        if len(q.split()) < 3 or latin <= len(q) * 0.4:
            continue
        if re.search(r"[ぁ-んァ-ヶ一-龥]", q) or q.startswith("["):
            continue
        if title.search(line[:m.start()]):
            continue
        if line[m.end():m.end() + 1] != "（":
            print(f"{i}:{q[:60]}")
' | head -20)"

  # 9.15. 「版」をバージョンの意味で使っている (§4)。notes の実測では
  #       バージョンが 126 件で、「版」は書名の「第 2 版」に偏る。
  #       書名・刊行形態の「版」は誤検知なので除く
  report "「版」をバージョンの意味で使っている (「バージョン」へ揃える)" "$f" \
    "$(echo "$body" | grep -n '版' \
       | grep -vE '(出版|初版|改訂版|新版|復刻版|限定版|英語版|日本語版|普及版|第 *[0-9]+ *版|版画)' | head -20)"

  # 9.16. 資源・時間を「予算」と呼ぶ比喩 (§11)。上限・残量・許容値のどれなのかが
  #       読者に伝わらない。「上限」「許容できる遅延」のように測れる語で書く
  report "資源や時間を「予算」と呼んでいる (上限・許容値など測れる語で書く)" "$f" \
    "$(echo "$body" | grep -nE '予算' | head -20)"

  # 9.17. 硬い漢語・直訳調の語 (§4)。リポジトリの実測で定着している語へ揃える
  report "硬い語が使われている (実際的→現実的 / 住所→アドレス)" "$f" \
    "$(echo "$body" | grep -nE '実際的|接続先の住所|宛先の住所' | head -20)"

  # 9.17.1. 「費用」をコストの意味で使っている (§4)。技術記事の実測は
  #         コスト 29 : 費用 14 でコスト優勢。成句の「費用対効果」は除く
  report "「費用」をコストの意味で使っている (「コスト」へ揃える)" "$f" \
    "$(echo "$body" | grep -n '費用' | grep -v '費用対効果' | head -20)"

  # 9.18.5. 機械を人格として描く劇的な比喩 (§11)。何が起きるのかを動作で書く。
  #        「運命が決まる瞬間」「誰にも裏切られずに」の類は、測れる言葉へ直す
  report "劇的な比喩・擬人化がある (何が起きるのかを動作で書く)" "$f" \
    "$(echo "$body" | grep -nE '運命|宿命|命運|裏切|生き残りを賭け|死活を分け' | head -20)"

  # 9.18.6. 1 文字の記号の定義を文末の括弧へ後置している (§14 型5)。
  #        読者は式を意味の分からないまま読み、括弧まで来て戻る事になる。
  #        違反ではなく情報に留めるのは、記号の再掲や単位の補足も同じ形を取るため
  symdef=$(echo "$body" | grep -nE '（[A-Z] は|（[A-Z] と [A-Z] は|（それぞれ [A-Z]' | head -20)
  if [ -n "$symdef" ]; then
    echo "  [INFO] 記号の定義を括弧で後置している (式より前へ出し、具体値を 1 つ添える)"
    echo "$symdef" | sed 's/^/       /'
  fi

  # 9.19. 確率的な事象を必然として書いている (precision_claims.md §3)。
  #       故障・競合・衝突は確率で起きる。件数が増えた時に何が変わるかを書けば、
  #       予言にしなくても危険は伝わる
  report "確率的な事象を必然として書いている (「積み上がるほど無視できなくなる」の形へ)" "$f" \
    "$(echo "$body" | grep -nE 'いずれ(起き|発生|訪れ|生じ|来ま)|遅かれ早かれ|時間の問題|必ず(起き|踏み|踏む|発生|生じ)' | head -20)"

  # 9.20. 既知の概念との同一視 (precision_claims.md §6)。「〜の発想そのもの」
  #       「〜にほかなりません」で結ぶと 2 つの定義の差が消える。共通する性質だけを
  #       名指しし、既知の側は使われ方で繋ぐ
  report "既知の概念と「そのもの」で同一視している (共通する性質だけを名指しする)" "$f" \
    "$(echo "$body" | grep -nE '(発想|考え方|理屈|仕組み|作り|やり方)そのもの|にほかなりません|に他なりません' | head -20)"

  # 9.18. Markdown の表の列数が揃っていない (§8)。
  #       表の直後に空行を入れ忘れると、次の段落が最終行の末尾へ吸い込まれて
  #       1 列だけ多い行になる。レンダリング後に気付きにくいので機械で拾う。
  #       表とみなすのは、区切り行 |---|---| を持つ塊だけ
  badtable=$(echo "$body" | awk '
    function cols(s,   n, t) {
      sub(/^ *\| */, "", s); sub(/ *\| *$/, "", s)
      n = split(s, t, /\|/)
      return n
    }
    /^ *\|/ {
      if (!intable) { intable = 1; hdr = NR; hdrline = $0; nsep = 0; next }
      if (nsep == 0) {
        if ($0 ~ /^ *\|[-: |]+\|? *$/) { nsep = 1; want = cols($0); if (cols(hdrline) != want) print hdr": (見出し) "substr(hdrline,1,70); next }
        intable = 0; next
      }
      if (cols($0) != want) printf "%d: %s\n", NR, substr($0, 1, 70)
      next
    }
    { intable = 0; nsep = 0 }
  ' | head -20)
  report "Markdown の表の列数が揃っていない (表の直後に空行があるか確認する)" "$f" "$badtable"

  # 10. コードフェンスの言語指定漏れ (開始フェンスだけを見る)
  report "言語指定の無いコードフェンスがある" "$f" \
    "$(awk '/^```/ { if (!code) { if ($0 == "```") print NR": "$0 } ; code = !code }' "$f" | head -20)"

  # 10.5. 「〜ため、」で繋いだ文の棚卸し (違反ではなく情報)。
  #       前後がそれぞれ独立した主張なら、切って「そのため、」で受けた方が読みやすい
  tame=$(echo "$body" | sed 's/そのため、/＿/g' | grep -nE 'ため、' | head -20)
  if [ -n "$tame" ]; then
    echo "  [INFO] 「〜ため、」で繋いだ文 (前後が独立した主張なら切れないか検討する)"
    echo "$tame" | sed 's/^/       /'
  fi

  # 10.6. 保証と故障を述べた文の棚卸し (違反ではなく情報)。
  #       precision_claims.md §1 §2 §5 §7 §42 を当てる場所を示すだけで、
  #       ここに出た事自体は問題ではない。1 文ずつ次を確認する。
  #         - 守る性質を書いたら、読者が読み取る隣の強い性質を切り離したか
  #         - 故障の影響で、結果が壊れるのか進まなくなるだけなのかを分けたか
  #         - 一次資料の役割名・成立条件を通称へ言い換えていないか
  #         - 抜け道 (zero value・nil・空入力・パッケージ内からの生成・serialization・
  #           別のコンストラクタ・実行時の設定・並行処理・失敗経路) を数えたか
  hoshou=$(echo "$body" | grep -nE '保証(し|され|する)|防ぎます|防げます|決して|あり得ませ|起きません|単一障害点|解決します|必ず|常に|作れませ|作れない|型から分か|だけになりま|すれば安全|なら壊れ|壊れませ' | head -20)
  if [ -n "$hoshou" ]; then
    echo "  [INFO] 保証・故障・断定を述べた文 (保証しない範囲を書いたか、safety と liveness を分けたか、§42 の抜け道を数えたか確認する)"
    echo "$hoshou" | sed 's/^/       /'
  fi

  # 10.7. 環境で桁が動く数値の棚卸し (precision_claims.md §4)。遅延・往復数は
  #       ネットワークと fsync の実装で変わる。手元で測っていない値を根拠に使わない。
  #       プロトコルが定める段階と、実装が足すやり取りも分ける
  numbers=$(echo "$body" | grep -nE 'ミリ秒|マイクロ秒|ナノ秒|秒未満|[0-9] ?(ms|μs|ns)|[0-9] *往復|往復|スループットは' | head -20)
  if [ -n "$numbers" ]; then
    echo "  [INFO] 環境で桁が動く数値 (測っていない値を根拠にしていないか、往復数が実装依存でないか確認する)"
    echo "$numbers" | sed 's/^/       /'
  fi

  # 11. 説明が見当たらない英字用語の棚卸し (違反ではなく情報。exit status には影響しない)
  #     全ての英字用語を並べると量が多くて読み飛ばすので、初出の近くに定義が
  #     見当たらないものだけへ絞る。「定義がある」と見なすのは次のいずれか。
  #       - どこかで `用語（...）` と括弧で展開・注釈している
  #       - 初出の段落かその次の段落に `用語 は` `用語 とは` `用語 と呼` がある
  #     誤検知を減らすため、以下は対象から外す。
  #       - 大文字始まりの語が 2 つ続き、直後が の/が/と で受けられている形 (人名)
  #       - front matter の title に含まれる語 (記事そのものの主題)
  #       - バッククォート内の識別子、URL、リンク先のパス
  #     大文字始まりの語が連続する場合はまとめて 1 つの用語として扱う
  #     (Election Safety、Leader Append-Only など)。
  title=$(sed -n 's/^title: *"\(.*\)"$/\1/p' "$f" | head -1)
  # mermaid 図に出てくる語は、図が登場人物の紹介になっているので対象外にする
  figlabels=$(awk '/^```mermaid/ { m=1; next } /^```/ { m=0 } m' "$f" | tr -c 'A-Za-z0-9' ' ')
  terms=$(echo "$body" | awk -v title="$title" -v figlabels="$figlabels" '
    # mawk のブラケット否定はバイト単位で判定するため、[^）] のような書き方は
    # 全角文字を含む行で誤動作する (「呼」の 2 バイト目が ） の 2 バイト目と同じ)。
    # 全角の括弧で囲まれた範囲は、正規表現ではなく index() で取り除く
    function stripspan(s, o, c,   p, q, r) {
      r = ""
      while ((p = index(s, o)) > 0) {
        r = r substr(s, 1, p - 1) " "
        s = substr(s, p + length(o))
        q = index(s, c)
        if (q == 0) return r
        s = substr(s, q + length(c))
      }
      return r s
    }
    # r の直後に marker が続く箇所を探す。r の直前が英字なら別の語の一部
    # (Multi-Paxos の中の Paxos など) なので数えない
    function definedas(g, r, m,   p, pos, before) {
      pos = 1
      while ((p = index(substr(g, pos), r m)) > 0) {
        p += pos - 1
        if (p == 1) return 1
        before = substr(g, p - 1, 1)
        if (before !~ /[A-Za-z0-9_.+-]/) return 1
        pos = p + 1
      }
      return 0
    }
    # 全角の括弧で囲まれた「中身だけ」を集める。理由は stripspan と同じ
    function insidespan(s, o, c,   p, q, r) {
      r = ""
      while ((p = index(s, o)) > 0) {
        s = substr(s, p + length(o))
        q = index(s, c)
        if (q == 0) return r
        r = r " " substr(s, 1, q - 1)
        s = substr(s, q + length(c))
      }
      return r
    }
    BEGIN {
      split("Client Server Node Figure NULL JSON YAML CSV SQL API URL HTTP HTTPS TCP UDP CPU OS DB ID Go Rust Python HTML CSS SELECT INSERT UPDATE DELETE WHERE FROM JOIN Java Kotlin Ruby Swift Scala TypeScript JavaScript Getter Setter", a, " ")
      for (k in a) common[a[k]] = 1
      n = split(figlabels, b, " ")
      for (k = 1; k <= n; k++) if (b[k] != "") fig[b[k]] = 1
    }
    {
      raw = $0
      gsub(/`[^`]*`/, " ", raw)
      # リンクを処理する。出典 (PDF) と既存ノートへのリンクは、
      # 定義がリンク先にあるのでリンクテキストごと対象から外す
      out = ""
      rest = raw
      while (match(rest, /\[[^]]*\]\([^)]*\)/)) {
        pre = substr(rest, 1, RSTART - 1)
        m = substr(rest, RSTART, RLENGTH)
        rest = substr(rest, RSTART + RLENGTH)
        p = index(m, "](")
        txt = substr(m, 2, p - 2)
        url = substr(m, p + 2, length(m) - p - 2)
        if (url ~ /\.pdf$/ || url ~ /^\.\.\// || url ~ /^\/notes\//) { excused[txt] = 1; txt = " " }
        out = out pre " " txt " "
      }
      line = out rest
      gsub(/https?:\/\/[^ )]+/, " ", line)
      all = all " " line
      # 括弧の中に出てくる語は、どこかで展開・注釈された語として控えておく
      inparen = inparen " " insidespan(line, "（", "）")
      # 用語の抽出からは、括弧の中 (展開そのもの) と書名・引用を除く
      line = stripspan(line, "（", "）")
      line = stripspan(line, "『", "』")
      line = stripspan(line, "「", "」")
      L[NR] = line
      last = NR
    }
    END {
      for (n = 1; n <= last; n++) {
        s = L[n]
        while (match(s, /[A-Z][A-Za-z0-9_.+\/-]*( (of|and|the) [A-Z][A-Za-z0-9_.+\/-]*| [A-Z][A-Za-z0-9_.+\/-]*)*/)) {
          run = substr(s, RSTART, RLENGTH)
          s = substr(s, RSTART + RLENGTH)
          if (length(run) < 3) continue
          if (run in first) continue
          first[run] = n
          tail = s
          sub(/^ +/, "", tail)
          after[run] = substr(tail, 1, 9)
          ord[++c] = run
        }
      }
      # 人名を先に確定させ、姓だけの再出現も外す
      for (i = 1; i <= c; i++) {
        run = ord[i]
        if (run ~ /^[A-Z][a-z]+ [A-Z][a-z]+$/ && after[run] ~ /^(の|が|と|、)/) {
          person[run] = 1
          split(run, nm, " ")
          person[nm[1]] = 1
          person[nm[2]] = 1
        }
        # 「Hayashibara ら」のように、姓だけ出して複数形で受ける形
        if (run ~ /^[A-Z][a-z]+$/ && after[run] ~ /^ら/) person[run] = 1
      }
      for (i = 1; i <= c; i++) {
        run = ord[i]
        if (run in person) continue
        if (run in common) continue
        if (run in fig) continue                                # mermaid 図の登場人物
        nf = split(run, w, /[ \/]/); allfig = 1                 # Node B のような複合ラベル
        for (k = 1; k <= nf; k++) if (!(w[k] in fig)) allfig = 0
        if (allfig) continue
        if (index(inparen, run) > 0) continue                   # 括弧の中で展開・注釈している
        if (run in excused) continue                            # 出典 PDF か既存ノートへのリンク
        if (run ~ /^[A-Z][0-9]/) continue                       # 2026-08-07T10 のような時刻の断片
        sing = run; sub(/s$/, "", sing)
        if (sing in excused) continue
        if (title != "" && index(title, run) > 0) continue      # 記事の主題そのもの
        if (title != "" && index(title, sing) > 0) continue
        if (index(all, run "（") > 0) continue                  # 括弧で展開・注釈している
        if (index(all, run " （") > 0) continue
        # 定義は初出の段落か、その次の段落にある事を求める。後ろの方に
        # 書いてあっても、初めて読む人はそこまで待たされる。
        # ただし初出が表の中なら、地の文での定義は表の後ろに来るので全体を見る
        if (L[first[run]] ~ /^ *\|/) {
          # 表の 1 列目に置いた見出しなら、その行の残りの列が説明になっている
          hd = L[first[run]]
          sub(/^ *\| */, "", hd)
          if (index(hd, run) == 1) continue
          ctx = all
        } else {
          ctx = L[first[run]]
          for (n = first[run] + 1; n <= last; n++) {
            if (L[n] ~ /[^ ]/) { ctx = ctx " " L[n]; break }
          }
        }
        g = ctx; gsub(/ /, "", g)
        r = run; gsub(/ /, "", r)
        if (definedas(g, r, "は")) continue
        if (definedas(g, r, "とは")) continue
        if (definedas(g, r, "と呼")) continue
        if (definedas(g, r, "という")) continue
        if (definedas(g, r, "である")) continue
        if (definedas(g, r, "になり")) continue
        if (definedas(g, r, "になる")) continue
        printf "%s (行 %d)\n", run, first[run]
      }
    }
  ')
  if [ -n "$terms" ]; then
    echo "  [INFO] 初出の近くに説明が見当たらない英字用語 (「何をするものか」を 1〜3 文で足すか、その語を消す)"
    echo "$terms" | sed 's/^/       /'
    echo "       ※ 論文・書籍のタイトルはここに出ても対応不要"
  fi

  # 11.2. 呼び名のブレ (scripts/name_drift.py)。括弧で和語と英語を併記した所を
  #       起点に、その後どちらの呼び名で本文を通しているかを数える。
  #       和語の呼び名を目で追う仕掛けはここだけである。11 は英字用語しか見ない。
  #         kanji1 = 1 文字の漢字へ略した呼び名を、定義した h3 の外で使っている
  #                  (2026-09-04 nonce の「列」、2026-09-06 hash-function の「語」)。
  #                  読者はその 1 文字が何を指すのか決められないので違反とする。
  #         mixed  = 和語と英語の両方を定義の後も使っている。記事で通す呼び名は
  #                  1 つに決める (writing_style.md §24)。判断が要るので情報に留める。
  drift=$(echo "$body" | python3 "$here/name_drift.py" 2>/dev/null)
  if [ -n "$drift" ]; then
    kanji1=$(echo "$drift" | awk -F'\t' '$1=="kanji1" {
      printf "「%s」(%s、%d 行目で定義) を %s 行目でも使っている\n", $2, $3, $4, $5 }')
    report "定義した呼び名を 1 文字の漢字へ略している (呼び名で書く → writing_style.md §22)" "$f" "$kanji1"
    mixed=$(echo "$drift" | awk -F'\t' '$1=="mixed" {
      printf "「%s」(%s 行目) と %s の両方を使っている: %s 行目 / %s 行目\n", $2, $4, $3, $5, $6 }')
    if [ -n "$mixed" ]; then
      echo "  [INFO] 和語と英語の呼び名が混在している (通す方を 1 つ決めて全文を揃える)"
      echo "$mixed" | sed 's/^/       /'
    fi
  fi

  # 11.5. mermaid の Note を否定形で書いている (違反ではなく情報)。
  #       「原因を作っていないのは Web サーバの方」のように、何でないかを書くと
  #       読者は残りを自分で組み立てる事になる。原因と結果をそれぞれ名指しする
  negnote=$(awk '
    /Note (over|left of|right of)/ {
      i = index($0, ":")
      if (i == 0) next
      s = substr($0, i + 1)
      if (s ~ /(ていない|でない|ではない|しない|無い|ない方|の方$)/) printf "%d: %s\n", NR, $0
    }
  ' "$f" | head -10)
  if [ -n "$negnote" ]; then
    echo "  [INFO] mermaid の Note が否定形 (原因と結果をそれぞれ名指しする)"
    echo "$negnote" | sed 's/^/       /'
  fi

  # 12. mermaid の Note が長すぎる (違反ではなく情報)。
  #     sequenceDiagram の Note の幅は参加者の間隔で決まるため、長いと文字がはみ出て
  #     読めなくなる。<br/> で折るか、Note over A,B で 2 参加者分の幅を稼ぐ。
  #     mawk の length() はバイト数を返すので、全角 1 文字 = 3 バイトで見積もる (40 ≒ 13 文字)
  longnote=$(awk '
    /Note (over|left of|right of)/ {
      i = index($0, ":")
      if (i == 0) next
      n = split(substr($0, i + 1), seg, "<br/>")
      for (j = 1; j <= n; j++) {
        s = seg[j]
        gsub(/^ +| +$/, "", s)
        if (length(s) > 40) { print NR": "$0; break }
      }
    }
  ' "$f" | head -20)
  if [ -n "$longnote" ]; then
    echo "  [INFO] mermaid の Note が長い (<br/> で折るか Note over A,B で幅を稼ぐ)"
    echo "$longnote" | sed 's/^/       /'
  fi

  # 12.5. 枝分かれの無い一直線の flowchart (違反ではなく情報。2026-08-14 ユーザー指摘)。
  #       直列に並べただけの flowchart は構造ではなく時間の前後を描いており、
  #       sequenceDiagram の方が相手と区間を出せる (→ references/mermaid_recipes.md §7)。
  #       矢印が 3 本以上あり、始点も終点も重複しない = 1 本の鎖、と判定する。
  #       分岐 ({} や |ラベル|) を含む図は構造なので対象外
  linearflow=$(awk '
    function nodeid(s,   a, n) {
      gsub(/^[ \t]+|[ \t]+$/, "", s)
      if (match(s, /[[({]/)) s = substr(s, 1, RSTART - 1)
      n = split(s, a, /[ \t]/)
      return a[n]
    }
    /^```mermaid/ { inblk = 1; start = NR; kind = ""; arrows = 0; branch = 0; peer = 0
                    delete src; delete dst; nsrc = 0; ndst = 0; next }
    inblk && /^```/ {
      if (kind == "flow" && arrows >= 3 && !branch && peer && nsrc == arrows && ndst == arrows)
        print start ": 一直線の flowchart (矢印 " arrows " 本、相手の居るやり取りを含む)"
      inblk = 0; next
    }
    inblk {
      if (kind == "" && $0 ~ /flowchart|graph /) { kind = "flow" }
      else if (kind == "") { kind = "other" }
      # 菱形・辺ラベルに加えて、点線や太線の矢印があれば鎖ではなく分岐である
      if ($0 ~ /[{}|]/ || $0 ~ /-\.|==>|--[ox]|<--/) branch = 1
      # 相手が居るやり取りが箱へ潰されている印。単独の主体が段を進むだけの
      # パイプライン図は flowchart のままでよいので、この語が無ければ流す。
      # 「登録の要求」のような名詞では鳴らさず、やり取りを表す動詞だけを見る
      if ($0 ~ /(呼ぶ|呼び出|応答を待|問い合わせる|送信する|API)/) peer = 1
      if (split($0, p, "-->") == 2) {
        a = nodeid(p[1]); b = nodeid(p[2])
        if (a != "" && b != "") {
          arrows++
          if (!(a in src)) { src[a] = 1; nsrc++ }
          if (!(b in dst)) { dst[b] = 1; ndst++ }
        }
      }
    }
  ' "$f" | head -10)
  if [ -n "$linearflow" ]; then
    echo "  [INFO] 一直線の flowchart がある (時間の前後なら sequenceDiagram へ移す)"
    echo "$linearflow" | sed 's/^/       /'
  fi

  # 12.6. mermaid で色や活性区間を直接指定している (writing_style/mermaid_recipes §7)。
  #       閲覧側のテーマで明暗が変わるため、色を固定すると片方で読めなくなる。
  #       区間は Note over を掛ける参加者の範囲で表す
  report "mermaid で色・活性区間を直接指定している (Note over の範囲で表す)" "$f" \
    "$(grep -nE '^\s*(rect (rgb|rgba)|activate |deactivate )' "$f" | head -10)"

  # 12.7. 冒頭のユースケースが読者の経歴を決め付けている (違反ではなく情報。
  #       2026-08-14 ユーザー指摘)。「最初に触れるのは〜する時ではないでしょうか」は、
  #       その場面が主題に出会う全員へ当てはまる時にしか使えない。特定の業務ドメイン・
  #       職種・製品を全員が通る道として書いていないかを 1 件ずつ当てる
  #       (→ references/writing_style.md §12)
  generalize=$(echo "$body" | grep -nE '(最初に(触れる|出会う|触れた|出会った)|初めて(触れる|出会う))' | head -10)
  if [ -n "$generalize" ]; then
    echo "  [INFO] 「最初に触れる／出会う」の書き出し (その場面を経験しない読者はこの主題に出会わないか、出会う場所が噛み合っているかを確かめる)"
    echo "$generalize" | sed 's/^/       /'
  fi

  # 12.8a. 出典を「原典」と呼んでいる (違反。writing_style.md §27)。
  #        2026-08-18 ユーザー指摘。Web 記事・ブログ・論文・書籍を一律に「原典」と
  #        まとめる呼び方は、大げさで権威的に読める上、情報源の種類も分からない。
  #        「King 氏の記事」「前述の記事」「論文」「書籍」のように種類で書くか、
  #        出典を明示する必要が無ければ主語ごと削る。「元記事」への一律置換も不可
  report "出典を「原典」と呼んでいる (「◯◯氏の記事」「前述の記事」「論文」「書籍」など情報源の種類で書く → writing_style.md §27)" "$f" \
    "$(grep -n '原典' "$f" | head -10)"

  # 12.8. 用語の歴史を断定している (違反ではなく情報。precision_claims.md §46)。
  #       広く参照されている整理記事を起源として書くと、それ以前から在った実践が
  #       消える。一次資料でそう確認できる場合だけ使い、そうでなければ
  #       「体系的に整理した」「広く参照されている」「この分類を示した」で書く。
  #       同じ資料を何度も指すなら、初出以降は資料の名前か著者名で受ける
  origin=$(echo "$body" | grep -nE '発明(した|者|され)|生みの親|最初に(提唱|考案|導入|定義|使わ)|初めて(提唱|考案|導入|定義)|の始まりです|起源です' | head -20)
  if [ -n "$origin" ]; then
    echo "  [INFO] 用語の歴史を断定している (一次資料で確認できないなら「体系的に整理した」「広く参照されている」へ)"
    echo "$origin" | sed 's/^/       /'
  fi

  # 12.9. 読者を主語にした冒頭の定型。2026-08-18 に 5 本を並べた時、全てが
  #       「読者がこの仕組みに既に触れているのは〜ではないでしょうか」で始まって
  #       おり、ユーザーから繰り返し指摘を受けた。入口を出す事自体は続けるが、
  #       書き方は題材ごとに変える (→ SKILL.md Step 4)
  report "冒頭の入口が読者を主語にした定型になっている (現象・壊れ方・コードの断片から書き出す)" "$f" \
    "$(grep -nE '読者が.*(既に触れ|最初に触れ|既に見て).*(でしょうか|です)|(開発者|読者)が.*へ最初に(触れる|出会う)のは' "$f")"

  # 12.9. 図・表を定型で導入している (違反ではなく情報。writing_style.md §25)。
  #       「〜を以下に示します」が並ぶと、本文が図の前置きだけで進む。
  #       本文の説明が図の内容へ着地する形にすると、この 1 文は要らなくなる
  intro=$(echo "$body" | grep -nE '以下に示し|下記に示し|次のように(なりま|示し|紹介|整理)|次の(表|図|通り)(に|で)?(示|なり)|対応を以下' | head -20)
  nintro=$(echo "$intro" | grep -c ':')
  if [ "$nintro" -ge 2 ]; then
    echo "  [INFO] 図・表を定型で導入している箇所が ${nintro} 件 (本文の説明が図へ着地する形にする)"
    echo "$intro" | sed 's/^/       /'
  fi

  # 12.10. 人名を文の主語にした回数 (違反ではなく情報。writing_style.md §25)。
  #        同じ資料を主要な参考文献にしていると、節ごとに「◯◯氏は〜」で書き出す
  #        形になりやすい。人名を主語にしてよいのは、その人の判断や評価そのものが
  #        主張の一部になっている時だけで、それ以外は概念を主語にする。
  #        敬称「氏」を付ける規則 (§12) は残るので、回数だけを見る
  shushi=$(echo "$body" | grep -nE '氏(は|が|も)' | head -20)
  nshushi=$(echo "$shushi" | grep -c ':')
  if [ "$nshushi" -ge 3 ]; then
    echo "  [INFO] 人名を文の主語にした箇所が ${nshushi} 件 (概念を主語にし直せないか見る)"
    echo "$shushi" | sed 's/^/       /'
  fi

  # 12.11. 図を受ける段落を「上図」で書き出した回数 (違反ではなく情報)。
  #        位置を指す必要がある所だけで使う。図に描いてある事を文章で
  #        言い直さず、図から読み取れない含意だけを書く (§25)
  jouzu=$(echo "$body" | grep -nE '^(上記の図|下記の図|上図|下図)' | head -20)
  njouzu=$(echo "$jouzu" | grep -c ':')
  if [ "$njouzu" -ge 3 ]; then
    echo "  [INFO] 段落を「上記の図／下記の図」で書き出した箇所が ${njouzu} 件 (図の言い直しになっていないか見る)"
    echo "$jouzu" | sed 's/^/       /'
  fi

  # 12.12. 英語の引用の本数 (違反ではなく情報。writing_style.md §25)。
  #        引用を置くのは、原文の表現そのものに意味がある時 (原則の紹介・
  #        用語の厳密な定義・原著者の強い表現) だけにする。裏付けだけが目的なら
  #        日本語で書いて出典名へリンクを張る。判定条件は 9.14.1 と揃える
  quotes=$(echo "$body" | python3 -c '
import re, sys
for i, line in enumerate(sys.stdin.read().split("\n"), 1):
    for m in re.finditer(r"「([^「」]*)」", line):
        q = m.group(1)
        latin = len(re.findall(r"[A-Za-z]", q))
        if len(q.split()) < 3 or latin <= len(q) * 0.4:
            continue
        if re.search(r"[ぁ-んァ-ヶ一-龥]", q):
            continue
        print(f"{i}:{q[:70]}")
')
  nquotes=$(echo "$quotes" | grep -c ':')
  if [ "$nquotes" -ge 3 ]; then
    echo "  [INFO] 英語の引用が ${nquotes} 個ある (原文の表現そのものに意味がある物だけ残し、残りは日本語とリンクへ)"
    echo "$quotes" | sed 's/^/       /'
  fi

  # 13. 1 行しかない段落の棚卸し (違反ではなく情報)。
  #     1 文で切って改行を挟むより、隣の段落へ寄せて 2〜4 行の塊にする。
  #     図・表・コードの直前に置く 1 行の橋渡し文は例外なので、次の非空行が
  #     コードフェンス・表・箇条書きの段落は対象から外す。
  #     行の折り返しは全角 45 文字前後なので、表示幅 48 未満を 1 行と見なす
  shortpara=$(awk '
    { line[NR] = $0 }
    END {
      fm = 0; code = 0
      for (i = 1; i <= NR; i++) {
        s = line[i]
        if (i == 1 && s == "---") { fm = 1; continue }
        if (fm) { if (s == "---") fm = 0; continue }
        if (s ~ /^```/) { code = !code; continue }
        if (code) continue
        if (s == "") continue
        if (s ~ /^(#|\||-|>|=)/) continue

        # 段落の本体を集める
        start = i; buf = ""
        while (i <= NR && line[i] != "" && line[i] !~ /^```/) { buf = buf line[i]; i++ }

        # 次の非空行が図・表・箇条書きなら橋渡し文とみなす
        nxt = ""
        for (j = i; j <= NR; j++) { if (line[j] != "") { nxt = line[j]; break } }
        if (nxt ~ /^(```|\||-)/) continue

        # 表示幅の見積もり。ASCII は半角、残りのバイトは全角 3 バイトで数える
        t = buf
        na = gsub(/[ -~]/, "", t)
        w = na / 2 + length(t) / 3
        if (w < 48) printf "%d: %s\n", start, substr(buf, 1, 90)
      }
    }
  ' "$f" | head -20)
  if [ -n "$shortpara" ]; then
    echo "  [INFO] 1 行しかない段落 (隣の段落へ寄せられないか検討する)"
    echo "$shortpara" | sed 's/^/       /'
  fi

  # コードブロック内で、ループの中から return / break している箇所。
  # 途中で抜けると、それまでの反復で書いた状態が残ったままコミットされる場合がある。
  # 該当が全部バグではないので INFO に留め、副作用が残らないかを目視で確認させる。
  loopexit=$(awk '
    /^```/ { infence = !infence; if (infence) lang = substr($0, 4); depth = 0; nloop = 0; next }
    !infence { next }
    lang ~ /^(mermaid|text|console|bash|sh|json|yaml|toml|markdown|md)$/ { next }
    {
      if (nloop > 0 && $0 ~ /(^|[ \t])(return|break)([ \t(;]|$)/) {
        printf "%d: %s\n", NR, substr($0, 1, 88)
      }
      isloop = ($0 ~ /(^|[ \t])(for|while)([ \t(]|$)/)
      a = $0; opens = gsub(/\{/, "&", a)
      b = $0; closes = gsub(/\}/, "&", b)
      depth += opens - closes
      if (isloop && opens > closes) { nloop++; start[nloop] = depth }
      while (nloop > 0 && depth < start[nloop]) nloop--
    }
  ' "$f" | head -12)
  if [ -n "$loopexit" ]; then
    echo "  [INFO] ループの中からの return / break (それまでの反復で書いた状態が残らないか確認する)"
    echo "$loopexit" | sed 's/^/       /'
  fi

  # ここから先は構成と分量の検査で、content/notes/ の技術ノートにだけ当てる。
  # ML ノート (projects/ml/notes) は 1 本で 1 分野を扱うため長く、ブログ記事
  # (content/post/ja) はコードを多く載せる。同じ目安を当てると誤検知になる
  case "$f" in
    */content/notes/*|content/notes/*) isnote=1 ;;
    *) isnote=0 ;;
  esac

  # 13.5. notes のページを「記事」と呼んでいる (writing_style.md §2-13、2026-08-10)。
  #       content/notes は「ノート」と呼ぶ。他ノートへの参照は「〜のノート」、
  #       自己言及は「このノート」も禁止 (検査 9) なので「ここでは」で書く。
  #       ブログ記事 (/post/) への言及と、外部の出典を指す「◯◯氏の記事」
  #       「前述の記事」の形 (→ writing_style.md §27) は対象外
  [ "$isnote" -eq 1 ] && report "他のノートを「記事」と呼んでいる (「〜のノート」かリンクへ。自己言及の「本記事」は対象外)" "$f" \
    "$(echo "$body" | grep -n '記事' | grep -vE '/post/|ブログ記事|氏の記事|前述の記事|参照した記事|この考え方を示した記事|整理記事' | sed -E 's/本記事//g' | grep '記事' | head -20)"

  # 14. 中身を表さない見出し。「仕組み」は catch-all として働くため、書き手は
  #     際限なく詰め、読者は目次から中身を推測できない。実測 14 本で、この見出しを
  #     持つノートの最大 h3 シェアは中央値 52% だった。中身を表す名前へ割る
  [ "$isnote" -eq 1 ] && report "見出しが中身を表していない (何をどうするのかで名づける)" "$f" \
    "$(grep -nE '^#{3,4} *(仕組み|概要|詳細|基本|その他|補足)$' "$f" | head -20)"

  # 15. 分量と h3 の配分。読者が読むのは地の文・箇条書き・表のセルなので、
  #     コードフェンスを除き、リンクは表示されるテキストだけを数える。
  #     全角 1 文字 = 3 バイトとして概算する
  layout=$(awk '
    function clen(s,   t, na) {
      gsub(/\]\([^)]*\)/, "", s)      # リンクは表示されるテキストだけ数える
      gsub(/\[/, "", s); gsub(/\]/, "", s); gsub(/`/, "", s)
      t = s; na = gsub(/[ -~]/, "", t)
      return na + length(t) / 3
    }
    NR == 1 && $0 == "---" { fm = 1; next }
    fm { if ($0 == "---") fm = 0; next }
    /^```/ {
      if (!infence) {
        infence = 1; has[sec] = 1
        # 図の定義 (mermaid・D2・DOT・SVG) は読者向け本文に数えない。通常のコード例は数える
        diagram = ($0 ~ /^```(mermaid|d2|dot|graphviz|svg)[ \t]*$/)
        if ($0 ~ /^```mermaid/) fig++; else if (!diagram) code++
      }
      else infence = 0
      next
    }
    infence { if (!diagram) reader += clen($0); next }
    /^[ \t]*\{\{[<%]/ { next }        # Hugo shortcode の呼び出しは数えない
    /^[ \t]*<!--/ { next }
    /^#+ / { h = $0; sub(/^#+ +/, "", h); reader += clen(h) }
    /^### / { sec++; name[sec] = substr($0, 5); next }
    /^#+ / { next }                 # 見出しは地の文の配分に数えない (読者向け本文には数える)
    /^-{3,} *$/ { next }
    /^\|/ { has[sec] = 1 }          # 表も、構造を見せている面として数える
    { n = clen($0); total += n; reader += n; part[sec] += n }
    END {
      printf "TOTAL %d %d %d %d %d\n", total, fig, code, sec, reader
      for (i = 1; i <= sec; i++) {
        printf "SEC %d %d %s\n", part[i], (total ? 100 * part[i] / total : 0), name[i]
        if (!has[i]) printf "NOVIS %d %s\n", part[i], name[i]
      }
    }
  ' "$f")

  set -- $(echo "$layout" | awk '/^TOTAL/ { print $2, $3, $4, $5, $6 }')
  total=$1; nfig=$2; ncode=$3; reader=$5

  # 図は mermaid だけではない。Page Bundle の images/ を参照した画像 (Python で
  # 生成した図) も 1 枚として数える (→ references/figure_recipes.md)
  nimg=$(grep -o '!\[[^]]*\](images/' "$f" | wc -l | tr -d ' ')
  nfig=$((nfig + nimg))

  echo "  読者向け本文 ${reader} 字 (見出し・表・通常のコード例を含み、図の定義・shortcode・URL を除く。1 万字以内が目標)"
  echo "  地の文 ${total} 字 / 図 ${nfig} 枚 (mermaid $((nfig - nimg)) + 画像 ${nimg}) / コード ${ncode} 個 / h3 見出し $(grep -c '^### ' "$f") 個"

  # 分量と配分の目安は content/notes/ の技術ノート向けなので、他は数値の表示で止める
  if [ "$isnote" -eq 0 ]; then
    continue
  fi

  # h3 が 1 つで本文の 35% を超えると、目次の 1 ブランチに記事の大半が入る。
  # 読者は目次を地図として使えず、書き手はその節に何でも足せてしまう
  bigsec=$(echo "$layout" | awk '$1 == "SEC" && $3 > 35 { $1=""; printf "%s%% (%s 字) %s\n", $3, $2, substr($0, index($0, $4)) }')
  report "1 つの h3 に本文の 35% 超が集まっている (内容を表す h3 へ割る)" "$f" "$bigsec"

  # 本文は 1 万字以内が目標 (2026-09-14 ユーザー指示)。どれほど正確でも、2 万字近い
  # 1 本は長すぎる。数えるのは読者が読む Markdown 本文で、図の定義は除く
  # (→ SKILL.md「本文は 1 万字以内を目標にする」)。超えたら、言い直し → 周辺の話 →
  # 重なる説明 → コード例の順に削り、それでも大きく超えるなら分割する
  # 2026-11-02: 違反から情報へ下げた。著者は 1.8 万字の Wallet ノートを承認しており、
  # debimate-visual-notes は「文字数の上限を機械的に設けず、理解に必要な内容だけを残す」
  if [ "$reader" -gt 10000 ]; then
    echo "  [INFO] 読者向け本文が ${reader} 字ある (上限ではなく目安。言い直し・周辺の話・重なる説明が残っていないかを見る)"
  elif [ "$reader" -gt 8000 ]; then
    echo "  [INFO] 読者向け本文が ${reader} 字ある (1 万字に近い。重複の削り残しと、主題から外れた話が無いかを見る)"
  fi

  # 図の枚数に下限は置かない。図は文章だけでは掴みにくい構造・順序・数量がある所に
  # だけ置く (→ references/diagram-guidelines.md)。同じ構成を描き直した図が並ぶと、
  # 長さを図で隠す事になるので、多い時だけ見直しを促す
  if [ "$reader" -gt 0 ] && [ "$nfig" -gt 0 ] && [ $((reader / nfig)) -lt 500 ]; then
    echo "  [INFO] 図が ${nfig} 枚ある (読者向け本文 500 字に 1 枚より多い。本文の言い換えになっている図や、同じ構成を描き直した図が無いか見る)"
  fi

  # コードが 4 個以上あるノートは、実測でいずれも 10,000 字を超えていた。
  # 概念の説明にコードが要るほど題材が広いという徴候
  if [ "$ncode" -ge 4 ]; then
    echo "  [INFO] コードブロックが ${ncode} 個ある (3 個までに収まらないか、題材が広すぎないか見る)"
  fi

  # Python で図を作ったのに本文へ貼り忘れる事がある。2026-09-03 にスキルを試した
  # 時、執筆エージェント 2 体とも figures.py で SVG を 3 枚ずつ生成しながら、本文は
  # mermaid だけで、数値の主張を表で処理していた。スクリプトを書いた時点で仕事が
  # 終わった気になるので、機械で塞ぐ (→ references/figure_recipes.md)
  imgdir="$(dirname "$f")/images"
  if [ -d "$imgdir" ]; then
    orphan=""
    for img in "$imgdir"/*; do
      [ -e "$img" ] || continue
      ibase=$(basename "$img")
      grep -qF "images/$ibase" "$f" || orphan="${orphan}${ibase}
"
    done
    report "images/ にあるのに本文から参照されていない画像がある (本文へ貼るか、使わないなら消す)" "$f" "$orphan"
  fi

  # 導入部 (最初の h3 より前) は全ての読者が最初に読む。ここで定義されていない語が
  # 出ると、読者はその先を抱えたまま読む事になる。2026-09-03 の finality で、冒頭の
  # 「ブロックタグ」を定義せずに使い、本人から「ブロックタグと、latest, safe,
  # finalized がわからん」という指摘を受けた。英字用語は下の一覧で拾えるが、
  # 和語・訳語 (ブロックタグ・合意層・確認数) の定義漏れは機械では判定できない。
  # 導入部の地の文をそのまま出して、語ごとに目で当てさせる
  intro=$(awk '
    BEGIN { fm = 0; incode = 0 }
    /^---$/ { if (fm < 2) fm++; next }
    fm == 2 && /^### / { exit }
    fm == 2 && /^```/ { incode = !incode; next }
    fm == 2 && !incode && NF { print "       " $0 }
  ' "$f")
  if [ -n "$intro" ]; then
    echo "  [INFO] 導入部 (最初の h3 より前)。ここに出る語が、この位置までに定義されているか 1 つずつ当てる"
    echo "$intro"
  fi

  # ノートは「適さないケース」(またはその言い換え) で終える。結論の後ろに比較・関連
  # パターン・まとめの節を足すと話が伸びる (2026-09-14 strangler-fig で本人から
  # 「結論を書いたら話を伸ばすな」→ SKILL.md Step 4)
  lasth3=$(grep '^### ' "$f" | tail -1 | sed 's/^### //')
  if [ -n "$lasth3" ] && echo "$lasth3" | grep -qE 'との(違い|比較|関係|使い分け|組み合わせ)|似た.*(比較|違い)|まとめ|関連'; then
    report "結論の後ろに比較・関連の節を足している (最後の h3 を消し、必要な区別は相手が初めて出る節で 1〜2 文にする)" "$f" "  ### $lasth3"
  fi

  # 見出しは、本文を直した時に直し忘れる面の 1 つ。本文へ但し書きを足しても
  # 見出しが前の版のまま残ると、目次だけが強く言い切った状態になる。
  # 強さの比較は機械ではできないので、一覧を出して目視させる
  # (2026-08-12、index-scan で見出しの「表を読まずに済ませる index-only scan」が
  #  本文の「必ず 0 にする形ではありません」と割れていた → precision_claims.md §19)
  # h4 も出す。同日の sql-null では `#### 集約関数は NULL を数えない` が、
  # 直下の表の「COUNT(*) は行を数える」と食い違ったまま残っていた (同 §24)
  heads=$(grep -n '^#\{3,4\} ' "$f")
  if [ -n "$heads" ]; then
    echo "  [INFO] 見出しの一覧 (本文より強く言い切っていないか、本文の場合分けを総称で潰していないか 1 つずつ当てる。mermaid のラベルと Note も同じ目で見る)"
    echo "$heads" | sed 's/^/       /'
  fi

  # 15.5. 図・表・コードの無い h3。
  #       図が特定の節へ偏る事がある。地の文だけで 500 字を超える節を出し、
  #       構造があるなら図の候補として当てる (2026-08-12 ユーザー指摘
  #       「この節は図がいらない？」)。前提・範囲の宣言のように構造を持たない節が
  #       残るのは正しい。逆に、1 項目 1 行の平坦な列挙を図にすると、同じ項目が
  #       並び直すだけになる (→ references/mermaid_recipes.md §6)
  novis=$(echo "$layout" | awk '$1 == "NOVIS" && $2 >= 300 { $1=""; printf "%s 字 %s\n", $2, substr($0, index($0, $3)) }')
  if [ -n "$novis" ]; then
    echo "  [INFO] 図・表・コードの無い h3 (振り分け・段の進行・2 方式の対比・時間の前後があるなら図の候補。平坦な列挙は図にしない)"
    echo "$novis" | sed 's/^/       /'
  fi

  # 16. 長すぎる段落。表示ベースで 200 字を超えると、画面では改行の無い塊が
  #     8 行以上続き、読者は目で追う位置を見失う。査読の指摘を既存の段落へ
  #     足していくと、ここが膨らむ
  longpara=$(awk '
    function clen(s,   t, na) {
      gsub(/\]\([^)]*\)/, "", s)
      gsub(/\[/, "", s); gsub(/\]/, "", s); gsub(/`/, "", s)
      t = s; na = gsub(/[ -~]/, "", t)
      return na + length(t) / 3
    }
    NR == 1 && $0 == "---" { fm = 1; next }
    fm { if ($0 == "---") fm = 0; next }
    /^[ \t]*```/ { infence = !infence; next }
    infence { next }
    /^(#|\||-{3,} *$|- |\{\{<|<br>)/ { next }
    /[^ ]/ { n = clen($0); if (n > 150) { q = ($0 ~ /」（/) ? "Q" : "P"; printf "%s\t%d: %d 字 %s\n", q, NR, n, substr($0, 1, 60) } }
  ' "$f")
  # 段落の長さは閾値では決まらない。引用は英語と訳の両方を書くので伸びるし、
  # コードを説明する段落は識別子で伸びる。本人のノート 48 本の実測では、200 字超が
  # 1 本あたり 0〜10 段落あり、最長の中央値は 242 字だった。つまり 200 字は違反の
  # 線ではなく、目を通す線である。違反にするのは、読者が目で追う位置を見失う
  # 300 字超だけにする (48 本で 1 本)。判断は「話題が 2 つ入っているか」で行う
  report "300 字を超える段落がある (話題の切れ目で割る)" "$f" \
    "$(echo "$longpara" | awk -F'\t' '$1 == "P" { print $2 }' | awk '$2 > 300')"
  plainlong=$(echo "$longpara" | awk -F'\t' '$1 == "P" { print $2 }' | awk '$2 > 200')
  if [ -n "$plainlong" ]; then
    echo "  [INFO] 200 字を超える段落 (文脈で判断する。話題が 2 つ入っていれば割り、1 つなら残してよい)"
    echo "$plainlong" | sed 's/^/       /'
  fi
  # 主語に文書・出典が来ている箇所 (→ references/voice_markers.md 表 6)。実測で、
  # ノートの「は」の直前の上位が 以下 / ドキュメント / 論文 / ここで / 本ノートで
  # になっており、本人 (本記事で / 具体的に / 今回 と説明対象そのもの) と別物だった。
  # 識別子を主語から外した先が文書へ移っただけの状態を出す
  docsubj=$(echo "$body" | grep -nE '(公式ドキュメント|ドキュメント|論文|白書|仕様書|パターンの説明|の記事)(は|が)[、 ]' | head -12)
  if [ "$(echo "$docsubj" | grep -c .)" -ge 3 ]; then
    echo "  [INFO] 文書・出典が主語になっている箇所 (説明している対象を主語に戻せないか見る)"
    echo "$docsubj" | sed 's/^/       /'
  fi

  # 長さが引用由来の段落は割れない。割ると引用だけの行ができ、読者はその引用を
  # 誰が何のために出したのかを補う事になる (→ writing_style.md §9)
  quotepara=$(echo "$longpara" | awk -F'\t' '$1 == "Q" { print $2 }' | awk '$2 > 200')
  if [ -n "$quotepara" ]; then
    echo "  [INFO] 引用を含む段落が 200 字を超えている (段落は割らない。長さが気になるなら引用を効いている部分だけへ狭める)"
    echo "$quotepara" | sed 's/^/       /'
  fi
  midpara=$(echo "$longpara" | awk -F'\t' '{ print $2 }' | awk '$2 > 150 && $2 <= 200')
  if [ -n "$midpara" ]; then
    echo "  [INFO] 150 字を超える段落 (切れ目があれば割る)"
    echo "$midpara" | sed 's/^/       /'
  fi

  # 17. 文体距離 (references/voice_markers.md)。ノート 47 本と、本人の文章
  #     (content/post/ja + content/weeknotes) を突き合わせて、
  #     ノート側だけで増えた言い回しを数える。規則を足す度にノート専用の方言が
  #     育ち、10 日で本人の 10 倍の密度になっていた (2026-08-18 ユーザー指摘
  #     「スキルを直す度に自分の文体から離れる。omokage では直せない」)。
  #     omokage は分布を見るため、この種のズレはスコアを保ったまま残る。
  #     閾値は本人の実測値を基準に置いている。
  voice=$(BODY="$body" python3 -c '
import os, re

body = os.environ["BODY"]
t = re.sub(r"\{\{<.*?>\}\}", "", body, flags=re.S)
t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
t = re.sub(r"https?://\S+", "", t)
t = re.sub(r"^\s*\|.*$", "", t, flags=re.M)
t = re.sub(r"^#+ .*$", "", t, flags=re.M)
t = re.sub(r"`[^`]*`", "", t)
t = re.sub(r"\s", "", t)
n = max(len(t), 1)
k = n / 1000.0

def c(*pats):
    return sum(t.count(p) for p in pats)

ng, info = [], []

def hard(label, cnt, ng_at, info_at, fix):
    if cnt >= ng_at:
        ng.append(f"{label} {cnt} 件 → {fix}")
    elif cnt >= info_at:
        info.append(f"{label} {cnt} 件 → {fix}")

def dens(label, cnt, ng_at, info_at, mine, fix):
    d = cnt / k
    if d >= ng_at:
        ng.append(f"{label} 千字あたり {d:.1f} 件 (本人 {mine}) → {fix}")
    elif d >= info_at:
        info.append(f"{label} 千字あたり {d:.1f} 件 (本人 {mine}) → {fix}")

# 本人の用例がほぼ無い言い回し。1 本に 1 個でも多い
hard("「上図」「下図」", c("上図", "下図"), 1, 1, "「上記の図」「下記の図」")
hard("「〜にあたります」", c("にあたりま", "にあたる"), 1, 1, "主語と動詞で書く")
hard("「要ります」「要る」", c("要りま", "要る", "要らな"), 2, 1, "「必要です」。述語の「注意が要る」だけ 1 本に 1 回まで")
hard("出典を主語にした形", c("と書いています", "と述べています", "と説明しています"), 2, 1,
     "概念を主語にし、根拠はリンクで示す (writing_style.md §25)")
hard("「そのもの」", c("そのもの"), 5, 3, "対象を名前で書く。「Xそのものではなく Y」の対比は残してよい")
hard("「よい」", c("てよい", "でよい", "がよい", "ばよい", "とよい", "よいです", "よい。"), 2, 1,
     "「良い」(本人は て良い 11:5、が良い 74:0、良いです 39:2)。副詞の「よく」は本人も使うので対象外")
hard("「〜ためです」", c("ためです"), 99, 3, "理由の「ため」なら「〜からです」。目的の「ため」（〜を守るためです）はそのまま残す。2026-11-02 の査読で、目的まで「から」に変えて意味が崩れた例が複数あった")
hard("「〜優先した結果として現れる制約です」", c("優先した結果として現れる"), 1, 1, "テンプレートの例文の写し。何を優先したかを、そのノートの主語と動詞で書く")
hard("「次の疑問を順に扱います」", c("次の疑問を順に扱います"), 99, 1, "Wallet の 1 文の写し。全ノートで同じ文にしない。前の文に合わせて言い回しを変える")
hard("「ここでは」", c("ここでは"), 5, 3, "範囲の宣言は「本記事では」で導入に 1 回。他は削るか対象を名指しする")
hard("「実際に」", c("実際に"), 99, 4, "削れないか見る。理論値と実測を分ける文では本人も使う")
hard("「〜を以下に示します」", c("以下に示し", "下記に示し"), 3, 2,
     "「以下の通りです」「以下が〜の一例です」。本人も使うが密度が 11 倍")

# 本人も使う言い回しの、使いすぎ。ここは NG にしない (ng_at=99)。
# ノートは定義と規則を書く分だけ、否定・受け身・「〜で決まります」が本人の
# ブログより増える。差の一部は文体ではなく題材なので、密度を下げるために
# 文を壊すと本末転倒になる (2026-08-18、47 本を補正した時に確認)。
# 直せる所だけ直す材料として出す
dens("否定の文末「〜ません。」", c("ません。"), 99, 2.5, "0.9", "何であるかを先に書き、否定は補足へ")
dens("「〜になります」", c("になりま"), 99, 1.2, "0.2", "「〜です」で言い切れる所は言い切る")
dens("「〜ではありません」", c("ではありません"), 99, 0.7, "0.1", "定義を否定から始めない")
dens("強調構文「〜のは、〜からです」", c("のは、"), 99, 6.0, "1.8",
     "主語を立てて普通の語順で書けないか見る。ノートは 5 倍使っていた")
dens("短い自動詞の文末 (決まる・残る・効く・済む・限る)",
     c("決まりま", "残りま", "効きま", "済みま", "限りま", "定まりま"),
     99, 0.8, "0.05", "主語と目的語を書けないか見る。「ここでは〜を扱いません」は範囲の宣言なので対象外")

# 助詞「へ」の比率。本人は に+へ の 3%、ノートは 19% だった
he, ni = t.count("へ"), t.count("に")
if he + ni > 0:
    r = he / (he + ni) * 100
    if r >= 12:
        ng.append(f"助詞「へ」が に+へ の {r:.0f}% (本人 3%) → 「に」に戻す")
    elif r >= 8:
        info.append(f"助詞「へ」が に+へ の {r:.0f}% (本人 3%) → 「に」に戻せる所を戻す")

# 本人が使うのに、ノートから消えていた語
mine = c("しかし", "例えば", "そのため", "ちなみに", "つまり", "なお、", "具体的に", "その結果")
d = mine / k
if d < 0.6:
    info.append(f"本人の接続詞 (しかし・例えば・そのため・ちなみに・つまり・なお・具体的に・その結果) が"
                f"千字あたり {d:.1f} 件 (本人 1.4) → 接続を削りすぎている")
tadashi = c("ただし")
if c("しかし") == 0 and tadashi >= 3:
    info.append(f"逆接が「ただし」{tadashi} 件だけで「しかし」が 0 件 → 前を正面から否定する所は「しかし」")

for x in ng:
    print("NG\t" + x)
for x in info:
    print("INFO\t" + x)
')
  vng=$(echo "$voice" | grep '^NG' | cut -f2-)
  vinfo=$(echo "$voice" | grep '^INFO' | cut -f2-)
  report "本人が使わない言い回しがある (references/voice_markers.md)" "$f" "$vng"
  if [ -n "$vinfo" ]; then
    echo "  [INFO] 文体距離 (本人の実測との差。本文を壊さずに直せる所だけ直す)"
    echo "$vinfo" | sed 's/^/       /'
  fi
done

if [ "$status" -eq 0 ]; then
  echo "OK: 機械チェックの違反なし"
fi
exit "$status"
