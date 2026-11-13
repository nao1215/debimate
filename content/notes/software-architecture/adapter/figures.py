"""Generate the figures of the Adapter note (WebP).

timeline_figure() reads lab/output_timeline.json (Prometheus query_range).
concept_figure() draws one Pod: PostgreSQL and postgres_exporter (the
adapter), Prometheus pulling /metrics, and the SQL the exporter runs.
matrix_figure() reads lab/output_matrix.txt.
unify_figure() draws three DBs whose exporters turn different outputs into one format.

Run: python3 content/notes/software-architecture/adapter/figures.py
Temporary PNG / SVG files go to $WORK (default: this directory's parent).
"""

import io
import json
import os
import re
import subprocess
import tempfile
from html import escape
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from PIL import Image  # noqa: E402

HERE = Path(__file__).resolve().parent
WORK = Path(os.environ.get("WORK", HERE.parent))
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE, RED_PALE = "#d4a24c", "#f8eed8", "#f9dcdc"
FONT = "'Noto Sans CJK JP','Hiragino Sans',sans-serif"


def _style():
    plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                         "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff"})


def _save(fig, name):
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, facecolor="#ffffff")
    plt.close(fig)
    Image.open(buf).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)


def timeline_figure():
    """DB と exporter を入れ替えた 240 秒の、系列とアラートの時刻を縦に並べる。"""
    d = json.loads((HERE / "lab" / "output_timeline.json").read_text())
    t0 = d["t0"]

    def series(key, **match):
        for r in d[key]["data"]["result"]:
            if all(r["metric"].get(k) == v for k, v in match.items()):
                return [(t - t0, float(v)) for t, v in r["values"]]
        return []

    def spans(points, step=5):
        """連続して値がある区間を (始め, 終わり) で返す。"""
        out = []
        for t, _ in points:
            if out and t - out[-1][1] <= step:
                out[-1][1] = t
            else:
                out.append([t, t])
        return out

    _style()
    fig, axes = plt.subplots(5, 1, figsize=(8.2, 5.4), sharex=True,
                             gridspec_kw={"height_ratios": [1, 1.3, 1.3, 0.55, 1.2]})
    events = [(60, "DB を 17 に"), (120, "exporter を\nv0.17.1 に"), (180, "stat_checkpointer\nを有効に")]

    ax = axes[0]
    up = series("pg_up")
    ax.step([t for t, _ in up], [v for _, v in up], where="post", color=ACCENT, lw=2)
    ax.set_ylim(-0.2, 2.8)
    ax.set_yticks([0, 1])
    ax.set_title("pg_up（DB に繋がったか）", loc="left", fontsize=9.5, color=INK)
    ax.annotate("入れ替えで 1 回だけ 0", xy=(67, 0), xytext=(75, 0.1), fontsize=8, color=SUB,
                arrowprops=dict(arrowstyle="->", color=SUB))

    ax = axes[1]
    old = series("checkpoints_req")
    ax.plot([t for t, _ in old], [v for _, v in old], color=ACCENT, lw=2, marker="o", ms=2.5)
    ax.set_title("pg_stat_bgwriter_checkpoints_req_total（ダッシュボードが見ている系列）",
                 loc="left", fontsize=9.5)
    ax.text(90, 5, "60 秒から先は\n値が 1 つも無い", ha="center", va="center", fontsize=9, color=RED,
            bbox=dict(fc="#ffffff", ec="none", pad=1.5), zorder=5)
    ax.set_ylim(0, 10)

    ax = axes[2]
    new = series("checkpointer_num_requested")
    ax.plot([t for t, _ in new], [v for _, v in new], color=OCHRE, lw=2, marker="o", ms=2.5)
    ax.set_title("pg_stat_checkpointer_num_requested_total（17 から数が移った先）", loc="left", fontsize=9.5)
    ax.text(90, 10, "既定では出ない", ha="center", va="center", fontsize=9, color=SUB,
            bbox=dict(fc="#ffffff", ec="none", pad=1.5), zorder=5)
    ax.set_ylim(0, 20)

    ax = axes[3]
    ok = series("bgwriter_success")
    for s, e in spans([(t, v) for t, v in ok if v == 0]):
        ax.add_patch(Rectangle((s, 0.2), e - s + 5, 0.6, color=RED))
    for s, e in spans([(t, v) for t, v in ok if v == 1]):
        ax.add_patch(Rectangle((s, 0.2), e - s + 5, 0.6, color=ACCENT))
    ax.set_ylim(0, 1)
    ax.set_yticks([])
    ax.set_title("stat_bgwriter の collector（青 = 成功、赤 = 失敗）", loc="left", fontsize=9.5)

    ax = axes[4]
    names = ["PostgresDown", "CollectorFailed", "CheckpointSeriesAbsent"]
    labels = ["pg_up == 0", "collector の失敗", "系列が無い"]
    for i, name in enumerate(names):
        y = 2 - i
        for state, color in (("pending", OCHRE_PALE), ("firing", RED)):
            for s, e in spans(series("alerts", alertname=name, alertstate=state)):
                ax.add_patch(Rectangle((s, y - 0.3), e - s + 5, 0.6, color=color, ec=OCHRE if state == "pending" else RED))
    ax.set_yticks([2, 1, 0], labels, fontsize=8.5)
    ax.set_ylim(-0.6, 2.6)
    ax.set_title("アラート（黄 = 待機中、赤 = 鳴っている）", loc="left", fontsize=9.5)

    for a in axes:
        a.set_xlim(0, 245)
        a.spines[["top", "right"]].set_visible(False)
        for x, _ in events:
            a.axvline(x, color=SUB, ls="--", lw=0.9)
    for x, s in events:
        axes[0].text(x + 2, 2.75, s, fontsize=8, color=INK, va="top")
    axes[-1].set_xlabel("実験の開始からの秒数（Prometheus は 5 秒ごとに集める）")
    _save(fig, "adapter_timeline.webp")


class Svg:
    def __init__(self, width, height, title):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="4" markerHeight="4" orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker></defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=20, color=INK, anchor="middle", mono=False):
        fam = ' font-family="DejaVu Sans Mono,monospace"' if mono else ""
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{fam} '
            f'style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke, sw=2.5, dash="", rx=10):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color=INK, sw=3, arrow=False, dash=""):
        m = ' marker-end="url(#arrow)"' if arrow else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{m}{d}/>')

    def save_webp(self, name, width, height):
        """SVG を Chrome で 2 倍の解像度に描き、WebP にする。"""
        with tempfile.TemporaryDirectory(dir=WORK) as tmp:
            svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
            svg.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")
            subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            "--force-device-scale-factor=2", f"--window-size={width},{height}",
                            f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
            Image.open(png).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)


def _shape(f, kind, cx, cy, fill, stroke, r=20):
    """出し方の違いを形で描く。ひし形は Prometheus が読む 1 つの形式。"""
    if kind == "circle":
        f.parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="3"/>')
    elif kind == "triangle":
        pts = f"{cx},{cy - r} {cx + r * 1.1},{cy + r * 0.8} {cx - r * 1.1},{cy + r * 0.8}"
        f.parts.append(f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="3" stroke-linejoin="round"/>')
    elif kind == "square":
        f.parts.append(f'<rect x="{cx - r * 0.85}" y="{cy - r * 0.85}" width="{r * 1.7}" height="{r * 1.7}" '
                       f'fill="{fill}" stroke="{stroke}" stroke-width="3"/>')
    else:
        pts = f"{cx},{cy - r} {cx + r},{cy} {cx},{cy + r} {cx - r},{cy}"
        f.parts.append(f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="3" stroke-linejoin="round"/>')


def unify_figure():
    """統計の出し方が違う 3 種類の DB が、隣の exporter を通ると同じ形式になって Prometheus に届く。"""
    w, h = 1010, 520
    f = Svg(w, h, "出し方の違う DB を exporter が 1 つの形式に揃える")
    f.text(505, 36, "統計の出し方は DB ごとに違うが、Prometheus に届く形式は 1 つ", 19, INK)
    rows = [("PostgreSQL", "統計のビューを SQL で", "circle", "postgres_exporter"),
            ("MySQL", "SHOW GLOBAL STATUS", "triangle", "mysqld_exporter"),
            ("Redis", "INFO コマンド", "square", "redis_exporter")]
    px, py, pw, ph = 800, 150, 190, 270
    for i, (name, how, kind, exp) in enumerate(rows):
        top = 62 + i * 150
        cy = top + 65
        f.box(20, top, 590, 130, "#ffffff", SUB, dash="10 7", rx=16)
        f.text(36, top + 24, "実行単位", 14, SUB, anchor="start")
        f.box(40, top + 34, 220, 84, FILL, INK)
        f.text(150, cy + 4, name, 21)
        f.text(150, cy + 32, how, 14, SUB, mono=(i == 1))
        f.line(262, cy + 10, 400, cy + 10, SUB)
        _shape(f, kind, 330, cy + 10, OCHRE_PALE, OCHRE)
        f.box(400, top + 34, 230, 84, PALE, ACCENT)
        f.text(515, cy + 4, exp, 17, mono=True)
        f.text(515, cy + 32, "（adapter）", 14, SUB)
        ty = py + 95 + i * 60
        f.line(632, cy + 10, px - 6, ty, ACCENT, sw=3, arrow=True)
        mx = 632 + (px - 6 - 632) * 0.42
        _shape(f, "diamond", mx, cy + 10 + (ty - cy - 10) * 0.42, ACCENT, ACCENT, r=15)
    f.box(px, py, pw, ph, FILL, INK)
    f.text(px + pw / 2, py + 44, "Prometheus", 22)
    for i in range(3):
        _shape(f, "diamond", px + pw / 2, py + 95 + i * 60, ACCENT, ACCENT, r=16)
    f.text(px + pw / 2, py + ph + 34, "テキスト形式 1 つ", 17, SUB)
    f.save_webp("adapter_unify.webp", w, h)


def concept_figure():
    """Pod の中の PostgreSQL と exporter、取りに来る Prometheus、exporter が投げる SQL。"""
    w, h = 1010, 470
    f = Svg(w, h, "PostgreSQL の隣に置いた exporter")
    f.box(30, 60, 620, 380, "#ffffff", SUB, dash="10 7", rx=16)
    f.text(60, 95, "Pod（同じ実行単位）", 20, SUB, anchor="start")
    # PostgreSQL
    f.box(60, 130, 230, 270, FILL, INK)
    f.text(175, 165, "PostgreSQL", 22)
    for i, (v, c) in enumerate([("pg_stat_database", INK), ("pg_stat_bgwriter", INK),
                                ("pg_stat_checkpointer", OCHRE), ("…", SUB)]):
        f.box(80, 190 + i * 50, 190, 38, "#ffffff", c, sw=2, rx=6)
        f.text(175, 216 + i * 50, v, 15, c, mono=True)
    # exporter
    f.box(370, 130, 240, 270, PALE, ACCENT)
    f.text(490, 165, "postgres_exporter", 20)
    f.text(490, 192, "（adapter）", 17, SUB)
    for i, (c, color) in enumerate([("database", INK), ("stat_bgwriter", INK), ("stat_checkpointer", OCHRE),
                                    ("…", SUB)]):
        f.box(392, 210 + i * 46, 196, 34, "#ffffff", color, sw=2, rx=6)
        f.text(490, 233 + i * 46, c, 15, color, mono=True)
    f.text(490, 425, "collector ごとに SQL を 1 本", 15, SUB)
    f.line(392, 273, 272, 255, ACCENT, sw=2.5, arrow=True)
    f.text(330, 252, "SQL", 15, SUB)
    f.line(392, 319, 272, 306, OCHRE, sw=2.5, arrow=True, dash="6 5")
    f.text(330, 352, "既定は無効", 14, OCHRE)
    # Prometheus
    f.box(780, 180, 210, 120, FILL, INK)
    f.text(885, 230, "Prometheus", 22)
    f.text(885, 262, "5 秒ごとに取りに来る", 15, SUB)
    f.line(778, 230, 614, 230, INK, arrow=True)
    f.text(712, 218, "GET /metrics", 14, INK, mono=True)
    f.line(614, 262, 778, 262, INK, arrow=True)
    f.text(712, 290, "テキスト", 14, INK)
    f.text(505, 38, "Prometheus が取りに来るたびに、exporter が DB の統計を読んで変換する", 18, INK)
    f.save_webp("adapter_concept.webp", w, h)


def matrix_figure():
    """PostgreSQL の版 × exporter の版で、stat_bgwriter の成否と checkpoint の数が出るかを並べる。"""
    out = (HERE / "lab" / "output_matrix.txt").read_text()
    pgs, exs = ["15", "16", "17", "18"], ["v0.15.0", "v0.16.0", "v0.17.1", "v0.20.1"]
    dates = {"v0.15.0": "2023-11", "v0.16.0": "2024-11", "v0.17.1": "2025-03", "v0.20.1": "2026-07"}
    cell = {}
    for blk in out.split("## postgres ")[1:]:
        m = re.match(r"(\d+) / exporter (\S+)", blk)
        ok = re.search(r'collector="stat_bgwriter"\} (\d)', blk).group(1) == "1"
        up = re.search(r"^pg_up (\d)", blk, re.M).group(1)
        cell[(m.group(1), m.group(2))] = (ok, up)
    _style()
    fig, ax = plt.subplots(figsize=(7.4, 3.5))
    for i, pg in enumerate(pgs):
        for j, ex in enumerate(exs):
            ok, up = cell[(pg, ex)]
            y = 3 - i
            if not ok:
                fc, ec, s = RED_PALE, RED, "collector が失敗\n（0）"
            elif int(pg) >= 17:
                fc, ec, s = OCHRE_PALE, OCHRE, "成功（1）だが\ncheckpoint の数は無い"
            else:
                fc, ec, s = "#ffffff", SUB, "成功（1）"
            ax.add_patch(Rectangle((j + 0.04, y + 0.06), 0.92, 0.88, fc=fc, ec=ec, lw=1.6))
            ax.text(j + 0.5, y + 0.58, s, ha="center", va="center", fontsize=8.6,
                    color=RED if not ok else INK)
            ax.text(j + 0.5, y + 0.2, f"pg_up = {up}", ha="center", va="center", fontsize=7.8, color=SUB)
    ax.set_xlim(0, 4)
    ax.set_ylim(0, 4)
    ax.set_xticks([j + 0.5 for j in range(4)], [f"{e}\n（{dates[e]}）" for e in exs])
    ax.set_yticks([3.5 - i for i in range(4)], [f"PostgreSQL {p}" for p in pgs])
    ax.xaxis.tick_top()
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("postgres_exporter のバージョン（リリースの年月）", fontsize=9.5, pad=34)
    _save(fig, "adapter_matrix.webp")


if __name__ == "__main__":
    (HERE / "images").mkdir(exist_ok=True)
    timeline_figure()
    unify_figure()
    concept_figure()
    matrix_figure()
