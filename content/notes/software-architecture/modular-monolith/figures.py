"""Modular Monolith のノートの図を生成する（Python 標準ライブラリだけを使う）。

実行: python3 figures.py
出力: images/modular_monolith_map.svg
"""

from pathlib import Path

FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
INK, SUB, LIGHT, ACCENT, RED = "#1f1f1f", "#666666", "#f2f2f2", "#7aa6c2", "#e15759"


def text(x, y, s, size=15, color=INK, anchor="middle", weight="normal"):
    return (f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" '
            f'fill="{color}" text-anchor="{anchor}" font-weight="{weight}">{s}</text>')


def cell(x, y, w, h, title, lines, stroke=INK, dash="", fill="#ffffff", modules=None):
    """1 つの象限。外枠はデプロイ単位、中の小箱はモジュールを表す。"""
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" fill="{fill}" '
           f'stroke="{LIGHT}" />']
    out.append(text(x + w / 2, y + 28, title, size=17, color=stroke, weight="bold"))
    # デプロイ単位とモジュールの絵
    total = sum(u["w"] for u in modules) + 12 * (len(modules) - 1)
    bx, by = x + (w - total) / 2, y + 46
    for unit in modules:
        uw = unit["w"]
        out.append(f'<rect x="{bx}" y="{by}" width="{uw}" height="58" rx="3" fill="#ffffff" '
                   f'stroke="{stroke}" stroke-width="2" {dash} />')
        mx = bx + 8
        for m in unit["mods"]:
            mdash = 'stroke-dasharray="4 3"' if unit.get("weak") else ""
            out.append(f'<rect x="{mx}" y="{by + 12}" width="34" height="34" rx="2" '
                       f'fill="{LIGHT}" stroke="{SUB}" {mdash} />')
            out.append(text(mx + 17, by + 34, m, size=14, color=INK))
            mx += 42
        bx += uw + 12
    for i, line in enumerate(lines):
        out.append(text(x + w / 2, y + 134 + i * 22, line, size=14, color=SUB))
    return out


def map_figure():
    W, H = 720, 500
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
             f'role="img" aria-label="デプロイ単位の数と境界の強さで 4 つの構成を並べた図">',
             f'<rect width="{W}" height="{H}" fill="#ffffff" />']
    x0, y0, cw, ch = 70, 20, 310, 190
    one = [{"w": 146, "mods": ["注", "請", "在"]}]
    one_weak = [{"w": 146, "mods": ["注", "請", "在"], "weak": True}]
    many = [{"w": 50, "mods": ["注"]}, {"w": 50, "mods": ["請"]}, {"w": 50, "mods": ["在"]}]
    many_weak = [dict(u, weak=True) for u in many]
    parts += cell(x0, y0, cw, ch, "Modular Monolith", ["デプロイは 1 回", "モジュール間は公開 API だけ"],
                  stroke=ACCENT, modules=one)
    parts += cell(x0 + cw + 20, y0, cw, ch, "Microservices", ["サービスごとにデプロイ", "呼び出しはネットワーク越し"],
                  modules=many)
    parts += cell(x0, y0 + ch + 20, cw, ch, "モノリス（境界なし）", ["デプロイは 1 回", "どこからでも内部を呼べる"],
                  stroke=SUB, modules=one_weak)
    parts += cell(x0 + cw + 20, y0 + ch + 20, cw, ch, "Distributed Monolith",
                  ["デプロイ単位は複数", "変更は同時に出す必要がある"], stroke=RED,
                  dash='stroke-dasharray="7 4"', modules=many_weak)
    # 軸
    ax_y = y0 + 2 * ch + 20 + 14
    parts.append(f'<line x1="{x0}" y1="{ax_y}" x2="{x0 + 2 * cw + 20}" y2="{ax_y}" stroke="{SUB}" />')
    parts.append(text(x0 + cw / 2, ax_y + 22, "デプロイ単位 1 つ", size=14, color=SUB))
    parts.append(text(x0 + cw * 1.5 + 20, ax_y + 22, "デプロイ単位 複数", size=14, color=SUB))
    parts.append(f'<line x1="{x0 - 14}" y1="{y0}" x2="{x0 - 14}" y2="{y0 + 2 * ch + 20}" stroke="{SUB}" />')
    parts.append(f'<text x="{x0 - 26}" y="{y0 + ch / 2}" font-family="{FONT}" font-size="14" fill="{SUB}" '
                 f'text-anchor="middle" transform="rotate(-90 {x0 - 26} {y0 + ch / 2})">境界を機械が検査</text>')
    parts.append(f'<text x="{x0 - 26}" y="{y0 + ch * 1.5 + 20}" font-family="{FONT}" font-size="14" fill="{SUB}" '
                 f'text-anchor="middle" transform="rotate(-90 {x0 - 26} {y0 + ch * 1.5 + 20})">境界は約束だけ</text>')
    parts.append(text(x0 + cw + 10, H - 10, "注=注文 請=請求 在=在庫、破線の小箱=内部のコードや表に外から触れられるモジュール",
                      size=13, color=SUB))
    parts.append("</svg>")
    return "\n".join(parts)


def main():
    out = Path(__file__).parent / "images"
    out.mkdir(exist_ok=True)
    (out / "modular_monolith_map.svg").write_text(map_figure() + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
