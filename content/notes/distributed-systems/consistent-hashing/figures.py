"""Generate the illustrative rings with Python 3 standard library.
Run: python3 figures.py. Positions are explanatory, not experiment results.
"""
from math import cos, sin, pi
from pathlib import Path

ROOT = Path(__file__).parent


def point(value, radius=104):
    angle = value / 100 * 2 * pi - pi / 2
    return 170 + radius * cos(angle), 165 + radius * sin(angle)


def ring(added):
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="340" height="340" viewBox="0 0 340 340">',
             '<rect width="340" height="340" fill="#fafbf9"/>',
             '<g font-family="sans-serif" font-size="14" fill="#28343b" text-anchor="middle">',
             f'<text x="170" y="25">{"After: A, B, C + D" if added else "Before: A, B, C"}</text>',
             '<circle cx="170" cy="165" r="104" fill="none" stroke="#7f8f99" stroke-width="2"/>']
    x1, y1 = point(20)
    x2, y2 = point(40)
    parts.append(f'<path d="M{x1},{y1} A104,104 0 0,1 {x2},{y2}" fill="none" stroke="#338573" stroke-width="9"/>')
    for label, value in [('A', 20), ('B', 60), ('C', 90)] + ([('D', 40)] if added else []):
        x, y = point(value)
        tx, ty = point(value, 135)
        parts.extend([f'<circle cx="{x}" cy="{y}" r="5" fill="#28343b"/>',
                      f'<text x="{tx}" y="{ty+5}">{label}: {value}</text>'])
    x, y = point(30)
    parts.append(f'<circle cx="{x}" cy="{y}" r="5" fill="#b47721"/>')
    parts.extend(['<text x="170" y="51">0 / 100</text>',
                  '<text x="170" y="151">Clockwise</text>',
                  f'<text x="170" y="176">key: 30 → {"D" if added else "B"}</text>',
                  f'<text x="170" y="310">(20, 40] → {"D" if added else "B"}</text>', '</g></svg>'])
    (ROOT / ('ring-after.svg' if added else 'ring-before.svg')).write_text('\n'.join(parts))


if __name__ == '__main__':
    ring(False)
    ring(True)
