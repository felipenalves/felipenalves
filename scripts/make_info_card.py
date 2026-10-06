#!/usr/bin/env python3
"""Generate the static, terminal-style identity card embedded in the profile README."""

from __future__ import annotations

import html
import os
from pathlib import Path


WIDTH = 490
HEIGHT = 370
PAD = 24
TITLEBAR_HEIGHT = 34
BACKGROUND = "#0d1117"
BACKGROUND_TOP = "#111722"
FRAME = "#30363d"
TEXT = "#e6edf3"
MUTED = "#7d8590"
CYAN = "#22d3ee"
GREEN = "#39d353"
GOLD = "#f2cc60"

HERE = Path(__file__).resolve().parent
OUTPUT = HERE.parent / "info-card.svg"

ROWS = (
    ("Now", "construo produtos e operações com IA", CYAN),
    ("Prev", "Dokke nasceu de um Galaxy J5 parado", GREEN),
    ("Stack", "JavaScript · Swift · Kotlin · Shell", GOLD),
    ("Highlights", "Mac · Android · PWA", CYAN),
)


def build_info_card(static: bool = False) -> str:
    """Return a complete SVG; static previews show the final visible state."""
    style = ""
    if not static:
        style = """<style>
@keyframes printLine {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}
.line { animation: printLine 420ms cubic-bezier(.2,.8,.2,1) both; }
</style>"""

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="card-title card-desc" '
        'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">',
        '<title id="card-title">Felipe Natanael — cartão do perfil</title>',
        '<desc id="card-desc">Cartão em estilo de terminal com trabalho atual, origem de um projeto, ferramentas e destaques.</desc>',
        style,
        '<defs><linearGradient id="card-bg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{BACKGROUND_TOP}"/><stop offset="1" stop-color="{BACKGROUND}"/>'
        '</linearGradient></defs>',
        f'<rect width="{WIDTH}" height="{HEIGHT}" rx="12" fill="url(#card-bg)"/>',
        f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{HEIGHT - 1}" rx="12" '
        f'fill="none" stroke="{FRAME}"/>',
        f'<line x1="0" y1="{TITLEBAR_HEIGHT}" x2="{WIDTH}" y2="{TITLEBAR_HEIGHT}" stroke="{FRAME}"/>',
    ]

    for index, color in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        parts.append(f'<circle cx="{PAD + index * 16}" cy="17" r="5" fill="{color}"/>')

    parts.extend(
        (
            f'<text x="{WIDTH / 2}" y="22" text-anchor="middle" fill="{MUTED}" font-size="12">'
            'felipe@github:~$ neofetch</text>',
            f'<text x="{PAD}" y="76" fill="{TEXT}" font-size="21" font-weight="700">'
            'Felipe Natanael</text>',
            f'<line x1="{PAD}" y1="107" x2="{WIDTH - PAD}" y2="107" stroke="{FRAME}"/>',
        )
    )

    row_start = 145
    row_gap = 43
    label_x = PAD
    value_x = 144
    for index, (label, value, color) in enumerate(ROWS):
        y = row_start + index * row_gap
        group_attrs = "" if static else f' class="line" style="animation-delay:{index * 150}ms"'
        parts.append(
            f'<g{group_attrs}>'
            f'<text x="{label_x}" y="{y}" fill="{color}" font-size="12" font-weight="700">'
            f'{html.escape(label)}</text>'
            f'<text x="{value_x}" y="{y}" fill="{TEXT}" font-size="12">'
            f'{html.escape(value)}</text>'
            '</g>'
        )

    parts.append(
        f'<line x1="{PAD}" y1="337" x2="{WIDTH - PAD}" y2="337" stroke="{FRAME}"/>'
    )
    parts.append(
        f'<text x="{PAD}" y="356" fill="{MUTED}" font-size="11">'
        f'<tspan fill="{GREEN}">●</tspan> build · test · document</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


def main() -> None:
    OUTPUT.write_text(build_info_card(static=os.environ.get("STATIC") == "1"), encoding="utf-8")
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
