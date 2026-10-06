#!/usr/bin/env python3
"""Convert the prepared portrait to ASCII with a single staggered row reveal."""

import argparse
import os
from pathlib import Path
import tempfile
from xml.sax.saxutils import escape

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
GLYPHS = " .`:-=+*cs#%@"


def convert(source: Path, destination: Path, columns: int) -> None:
    if not 1 <= columns <= 500:
        raise ValueError("COLS must be an integer between 1 and 500")
    rows = max(1, round(columns * 0.53))
    try:
        with Image.open(source) as image:
            sample = image.convert("L").resize((columns, rows), Image.Resampling.LANCZOS)
    except (OSError, ValueError) as error:
        raise ValueError(f"Cannot read input image {source}: {error}") from error

    width = 370
    content_width = 330
    character_width = content_width / columns
    font_size = character_width / 0.6
    line_height = character_width / 0.53
    height = round(48 + rows * line_height)
    pixels = sample.tobytes()
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="portrait-title portrait-description">',
        '<title id="portrait-title">Felipe Natanael — ASCII portrait</title>',
        '<desc id="portrait-description">Felipe Natanael’s portrait used on inovadigitalid.com, rendered in monochrome ASCII. Rows reveal once from top to bottom, then remain visible.</desc>',
        f'<rect x="0.5" y="0.5" width="369" height="{height - 1}" rx="10" fill="#0d1117" stroke="#30363d"/>',
        '<path d="M1 30H369" stroke="#30363d"/>',
        '<g fill="#8b949e"><circle cx="15" cy="15" r="3"/><circle cx="27" cy="15" r="3"/><circle cx="39" cy="15" r="3"/></g>',
        '<text x="185" y="19" text-anchor="middle" font-family="monospace" font-size="10" fill="#8b949e">felipe@github:~</text>',
        '<defs>',
    ]
    for row in range(rows):
        top = 38 + row * line_height
        delay = row * 0.045
        duration = delay + 0.22
        timing = ('from="0" to="330"' if row == 0 else
                  f'values="0;0;330" keyTimes="0;{delay / duration:.6f};1"')
        parts.append(
            f'<clipPath id="row-clip-{row}" clipPathUnits="userSpaceOnUse">'
            f'<rect x="20" y="{top:.3f}" width="330" height="{line_height:.3f}">'
            f'<animate attributeName="width" {timing} dur="{duration:.3f}s" begin="0s" fill="freeze"/>'
            '</rect></clipPath>'
        )
    parts.append('</defs>')
    for row in range(rows):
        glyphs = ''.join(GLYPHS[round((255 - value) * (len(GLYPHS) - 1) / 255)] for value in pixels[row * columns:(row + 1) * columns])
        baseline = 38 + row * line_height + font_size * 0.85
        parts.append(
            f'<g id="portrait-row-{row}" clip-path="url(#row-clip-{row})">'
            f'<text x="20" y="{baseline:.3f}" xml:space="preserve" font-family="monospace" '
            f'font-size="{font_size:.3f}" fill="#c9d1d9" textLength="330" lengthAdjust="spacingAndGlyphs">'
            f'{escape(glyphs)}</text></g>'
        )
    parts.append('</svg>')
    svg = '\n'.join(parts) + '\n'
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=destination.parent, suffix=".svg", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(svg)
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print(f"Generated {destination.name}: {columns}x{rows} characters, {width}x{height}px")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path, default=ROOT / "source-prepped.png")
    parser.add_argument("output", nargs="?", type=Path, default=ROOT / "felipe-ascii.svg")
    args = parser.parse_args()
    try:
        convert(args.input, args.output, int(os.environ.get("COLS", "100")))
    except Exception as error:
        parser.exit(1, f"ASCII conversion failed: {error}\n")


if __name__ == "__main__":
    main()
