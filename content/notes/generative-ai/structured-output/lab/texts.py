"""抽出課題の入力文と正解を作る。文は全て本記事のために作った架空のもので、人物も実在しない。

テンプレートに名前・日付・金額を差し込むので、正解は作る時点で決まる。
日付と金額は、書き方（西暦・スラッシュ・和暦、カンマ・万・円記号）を変えて混ぜる。
"""
import random

NAMES = ["佐藤花子", "鈴木一郎", "高橋健太", "田中美咲", "伊藤翔", "渡辺由美",
         "山本大輔", "中村さくら", "小林拓也", "加藤陽子", "吉田誠", "松本彩"]

TEMPLATES = [
    "{date}、{name}さんは書店で技術書を3冊、合計{amt}で購入した。",
    "{name}様より、{date}付けで{amt}のご入金を確認いたしました。請求書番号は INV-{num} です。",
    "経費精算 申請者: {name} / 利用日: {date} / 金額: {amt}（タクシー代、乗車人数2名）",
    "{date}に開かれた勉強会で、幹事の{name}さんが参加者12名分の会場費{amt}を立て替えた。",
    "山田さんの代わりに、{name}さんが{date}に家賃{amt}を振り込んだ。部屋番号は204号室。",
    "{name}さんから{date}の午後3時に連絡があり、修理代として{amt}を支払うとのことだった。",
    "Receipt: {date} 支払者 {name} 合計 {amt}",
    "{date}締めの請求として、{name}さんに{amt}（税込、送料500円を含む）を請求した。",
]


def date_text(rng, y, m, d):
    kind = rng.choice(["kanji", "slash", "wareki", "kanji"])
    if kind == "kanji":
        return f"{y}年{m}月{d}日"
    if kind == "slash":
        return f"{y}/{m}/{d}"
    return f"令和{y - 2018}年{m}月{d}日"  # 2019 年が令和元年


def amount_text(rng, a):
    kinds = ["comma", "yen_sign", "plain"]
    if a >= 10000 and a % 1000 == 0:
        kinds += ["man", "man"]
    if a >= 10000 and a % 10000 == 5000:
        kinds.append("man_decimal")
    kind = rng.choice(kinds)
    if kind == "comma":
        return f"{a:,}円"
    if kind == "yen_sign":
        return f"¥{a:,}"
    if kind == "plain":
        return f"{a}円"
    if kind == "man_decimal":
        return f"{a / 10000:g}万円"
    man, rest = divmod(a, 10000)
    sen = rest // 1000
    return f"{man}万" + (f"{sen}千" if sen else "") + "円"


def make_items(n=40, seed=20261110):
    rng = random.Random(seed)
    items = []
    for i in range(n):
        name = rng.choice(NAMES)
        y, m, d = rng.choice([2024, 2025, 2026]), rng.randint(1, 12), rng.randint(1, 28)
        a = rng.choice([980, 1500, 3200, 4500, 12800, 15000, 25000, 32000, 48000,
                        65000, 120000, 135000])
        tpl = TEMPLATES[i % len(TEMPLATES)]
        text = tpl.format(name=name, date=date_text(rng, y, m, d),
                          amt=amount_text(rng, a), num=rng.randint(1000, 9999))
        items.append({"id": i, "text": text, "answer": {
            "person": name, "date": f"{y:04d}-{m:02d}-{d:02d}", "amount_yen": a}})
    return items


if __name__ == "__main__":
    for it in make_items():
        print(it["id"], it["text"], it["answer"])
