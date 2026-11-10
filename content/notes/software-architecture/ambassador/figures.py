"""Generate the cover diagram of the Ambassador note as a hand-written SVG.

concept_figure() uses the same execution-unit frame as the Sidecar note.
main sees one door on localhost; the ambassador sits on the edge of the unit
and splits the traffic outside: writes to one master, reads to the replicas.
The region that holds the Redis nodes is drawn as what main does not see.

Run: python3 content/notes/software-architecture/ambassador/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


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

    def text(self, x, y, s, size=24, color=INK, weight="normal", anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke, sw=2.5, dash="", rx=10):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color=INK, sw=4, arrow=False):
        m = ' marker-end="url(#arrow)"' if arrow else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{m}/>')

    def db(self, cx, top, w, h, fill, stroke):
        rx, ry = w / 2, 10
        x = cx - rx
        self.parts.append(
            f'<path d="M{x},{top} v{h} a{rx},{ry} 0 0 0 {w},0 v{-h}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="2.5"/>')
        self.parts.append(
            f'<ellipse cx="{cx}" cy="{top}" rx="{rx}" ry="{ry}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="2.5"/>')

    def save(self, path):
        path.parent.mkdir(exist_ok=True)
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


def concept_figure():
    f = Svg(960, 540, "main からは localhost の 1 つの宛先だけが見え、外で書き込みと読み取りに分かれる")

    # The execution unit (same frame as the Sidecar note).
    f.box(30, 40, 550, 460, FILL, SUB, sw=2.5, dash="10 7", rx=24)
    f.text(54, 82, "実行単位", 26, SUB, "normal", "start")

    # main and the ambassador on the edge of the unit.
    f.box(60, 160, 230, 220, "#ffffff", INK, sw=3, rx=18)
    f.text(175, 255, "main", 28, weight="normal")
    f.text(175, 292, "アプリケーション", 24, SUB)
    f.box(450, 160, 230, 220, PALE, ACCENT, sw=3, rx=18)
    f.text(580, 280, "ambassador", 26, weight="normal")

    # One door: localhost.
    f.line(292, 270, 424, 270, INK, 5, arrow=True)
    f.box(436, 238, 36, 64, "#ffffff", INK, sw=3, rx=4)
    f.text(360, 250, "localhost", 24)
    f.text(360, 320, "宛先は 1 つ", 24, SUB)

    # Outside: what main does not see.
    f.box(712, 40, 236, 460, "#ffffff", SUB, sw=2, dash="6 6", rx=18)
    f.text(830, 80, "main から見えない", 24, SUB)
    f.text(830, 130, "書き込み", 24, INK, "normal")
    f.db(830, 160, 150, 56, OCHRE_PALE, OCHRE)
    f.text(830, 206, "master", 24)
    f.text(830, 278, "読み取り", 24, INK, "normal")
    for top, name in ((308, "replica 1"), (408, "replica 2")):
        f.db(830, top, 150, 56, PALE, ACCENT)
        f.text(830, top + 46, name, 24)

    # The ambassador splits the traffic.
    f.line(682, 230, 752, 186, OCHRE, 5)
    f.line(682, 300, 752, 336, ACCENT, 5)
    f.line(682, 330, 752, 436, ACCENT, 5)

    f.save(HERE / "images" / "ambassador_concept.svg")


def network_figure():
    """localhost only works when the containers share one network namespace."""
    f = Svg(960, 540, "ネットワークを共有すれば localhost で届き、共有しなければ相手のアドレスが要る")

    def panel(x0, head, sub):
        f.text(x0 + 217, 58, head, 26)
        f.text(x0 + 217, 94, sub, 24, SUB)
        f.box(x0, 120, 435, 320, FILL, SUB, sw=2, dash="10 7", rx=20)

    def container(x, label, fill, stroke):
        f.box(x, 250, 160, 96, fill, stroke, sw=3, rx=14)
        f.text(x + 80, 307, label, 24)

    panel(25, "ネットワークを共有する", "Kubernetes の Pod")
    f.box(45, 150, 395, 266, PALE, ACCENT, rx=14)
    f.text(242, 196, "IP アドレス 1 つ", 24, SUB)
    container(58, "main", "#ffffff", INK)
    container(268, "ambassador", "#ffffff", ACCENT)
    f.line(220, 298, 264, 298, INK, 4, arrow=True)
    f.text(242, 486, "localhost で届く", 24)

    panel(500, "共有しない", "ECS の bridge モード")
    for x, ip in ((515, "172.17.0.2"), (727, "172.17.0.3")):
        f.box(x, 150, 198, 266, OCHRE_PALE, OCHRE, rx=14)
        f.text(x + 99, 196, ip, 24, SUB)
    container(534, "main", "#ffffff", INK)
    container(746, "ambassador", "#ffffff", ACCENT)
    f.line(696, 298, 742, 298, INK, 4, arrow=True)
    f.text(717, 486, "相手のアドレスを探して持つ", 24)
    f.save(HERE / "images" / "ambassador_network.svg")


def startup_figure():
    """If the application starts before the proxy, its first requests fail."""
    f = Svg(960, 540, "アプリケーションがプロキシより先に動くと最初の通信が失敗する")
    x0, x1 = 240, 930
    f.text(930, 44, "時間 →", 24, SUB, anchor="end")

    def lane(y, label):
        f.text(30, y + 29, label, 24, anchor="start")

    def scenario(top, head, ready, app_start, requests, wait=False):
        f.text(30, top, head, 26, anchor="start")
        py, ay = top + 24, top + 130
        lane(py, "プロキシ")
        lane(ay, "アプリケーション")
        f.box(x0, py, ready - x0, 42, "#ffffff", SUB, sw=2, dash="7 6", rx=6)
        f.text((x0 + ready) / 2, py + 29, "起動中", 24, SUB)
        f.box(ready, py, x1 - ready, 42, PALE, ACCENT, rx=6)
        f.text((ready + x1) / 2, py + 29, "準備完了", 24)
        if wait:
            f.text((x0 + app_start) / 2, ay + 29, "待つ", 24, SUB)
        f.box(app_start, ay, x1 - app_start, 42, "#ffffff", INK, sw=2.5, rx=6)
        for x, ok in requests:
            f.line(x, ay - 2, x, py + 50, INK if ok else RED, 3, arrow=ok)
            f.text(x + 14, ay - 22, "届く" if ok else "失敗", 24,
                   INK if ok else RED, anchor="start")

    scenario(80, "起動の順序を決めない", 600, 270, [(330, False), (720, True)])
    scenario(316, "プロキシの準備を待つ", 480, 500, [(560, True)], wait=True)
    f.text(480, 528, "holdApplicationUntilProxyStarts・Sidecar Containers", 24, SUB)
    f.save(HERE / "images" / "ambassador_startup.svg")


if __name__ == "__main__":
    concept_figure()
    network_figure()
    startup_figure()
