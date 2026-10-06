#!/usr/bin/env python3
"""Render the public contribution calendar as a standalone animated SVG."""

from __future__ import annotations

import json
import os
from datetime import date, timedelta
from html import escape
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
PALETTE = ("#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def parse_date(value: object) -> date:
    if not isinstance(value, str):
        raise ValueError("dates must be ISO YYYY-MM-DD strings")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"invalid calendar date: {value!r}") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"date must use YYYY-MM-DD format: {value!r}")
    return parsed


def build_grid(days: list[dict[str, object]]) -> list[list[dict[str, object] | None]]:
    """Return 53 Sunday-first week columns, padding absent dates with None."""
    if not isinstance(days, list) or not days:
        raise ValueError("days must be a non-empty list")
    grid: list[list[dict[str, object] | None]] = [[None] * 7 for _ in range(53)]
    first: date | None = None
    previous: date | None = None
    for day in days:
        if not isinstance(day, dict) or set(day) != {"date", "count", "level"}:
            raise ValueError("each day must contain exactly date, count, and level")
        current = parse_date(day["date"])
        count, level = day["count"], day["level"]
        if type(count) is not int or count < 0:
            raise ValueError(f"invalid contribution count on {current}")
        if type(level) is not int or not 0 <= level <= 4:
            raise ValueError(f"invalid GitHub contribution level on {current}")
        if (count == 0) != (level == 0):
            raise ValueError(f"count and level disagree on {current}")
        if previous is not None and current != previous + timedelta(days=1):
            raise ValueError("days must be sorted, unique, and calendar-contiguous")
        if first is None:
            first = current - timedelta(days=(current.weekday() + 1) % 7)
        column, row = divmod((current - first).days, 7)
        if column >= 53:
            raise ValueError("calendar exceeds the supported 53-week grid")
        grid[column][row] = day
        previous = current
    return grid


def render_heatmap(payload: dict[str, object]) -> str:
    """Validate contribution data and return the entire SVG before any write."""
    if not isinstance(payload, dict):
        raise ValueError("contribution payload must be an object")
    days = payload.get("days")
    grid = build_grid(days)
    range_value = payload.get("range")
    if not isinstance(range_value, dict) or set(range_value) != {"start", "end"}:
        raise ValueError("range must contain exactly start and end")
    start, end = parse_date(range_value["start"]), parse_date(range_value["end"])
    if start.isoformat() != days[0]["date"] or end.isoformat() != days[-1]["date"]:
        raise ValueError("range must match the first and last calendar dates")
    total = payload.get("total_contributions")
    if type(total) is not int or total < 0 or total != sum(day["count"] for day in days):
        raise ValueError("total_contributions must equal the sum of daily counts")
    description = f"{total:,} contributions from {start.isoformat()} to {end.isoformat()}"
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="860" height="224" viewBox="0 0 860 224" role="img" aria-labelledby="calendar-title calendar-desc">',
        '<title id="calendar-title">Contribution calendar</title>',
        f'<desc id="calendar-desc">{escape(description)}. Sunday-first calendar; brighter green means more daily contributions.</desc>',
        '<style>text{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}.cell{animation:reveal .45s ease-out both;transform-box:fill-box;transform-origin:center}@keyframes reveal{from{opacity:0;transform:scale(.65)}to{opacity:1;transform:scale(1)}}@media(prefers-reduced-motion:reduce){.cell{animation:none}}</style>',
        '<rect x=".5" y=".5" width="859" height="223" rx="12" fill="#0d1117" stroke="#30363d"/>',
        '<text x="20" y="25" fill="#c9d1d9" font-size="12">CONTRIBUTIONS</text>',
    ]
    # Fixed daily count buckets preserve intensity meaning across refreshes.
    # The scraped GitHub level is validated separately from this six-color scale.
    labeled_months: set[tuple[int, int]] = set()
    for column, week in enumerate(grid):
        for row, day in enumerate(week):
            if day is None:
                continue
            current = parse_date(day["date"])
            month_key = (current.year, current.month)
            if month_key not in labeled_months and (current.day == 1 or day is days[0]):
                # Avoid labels colliding when the first partial month is short.
                if column == 0 and (end - start).days > 30 and start.day > 20:
                    pass
                else:
                    svg.append(f'<text x="{44 + column * 15}" y="45" fill="#8b949e" font-size="10">{MONTHS[current.month - 1]}</text>')
                labeled_months.add(month_key)
            count = day["count"]
            intensity = sum(count > threshold for threshold in (0, 5, 15, 30, 50))
            color = PALETTE[intensity]
            delay = column * .018 + row * .028
            tooltip = f'{count:,} contribution{"" if count == 1 else "s"} on {current.isoformat()}'
            svg.append(f'<rect class="cell" x="{44 + column * 15}" y="{54 + row * 15}" width="12" height="12" rx="3" fill="{color}" style="animation-delay:{delay:.3f}s"><title>{escape(tooltip)}</title></rect>')
    for label, row in (("Mon", 1), ("Wed", 3), ("Fri", 5)):
        svg.append(f'<text x="12" y="{63 + row * 15}" fill="#8b949e" font-size="9">{label}</text>')
    svg.append('<text x="663" y="178" fill="#8b949e" font-size="10">Less</text>')
    for index, color in enumerate(PALETTE):
        svg.append(f'<rect x="{696 + index * 15}" y="168" width="12" height="12" rx="3" fill="{color}"/>')
    svg.extend([
        '<text x="793" y="178" fill="#8b949e" font-size="10">More</text>',
        f'<text x="20" y="179" fill="#c9d1d9" font-size="12">{total:,} contributions</text>',
        f'<text x="20" y="205" fill="#8b949e" font-size="10">{start.isoformat()} → {end.isoformat()}</text>',
        '</svg>',
    ])
    return "\n".join(svg) + "\n"


def main() -> int:
    temporary: str | None = None
    try:
        payload = json.loads((ROOT / "data/contributions.json").read_text(encoding="utf-8"))
        svg = render_heatmap(payload)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=ROOT, suffix=".svg.tmp", delete=False) as output:
            temporary = output.name
            output.write(svg)
        os.replace(temporary, ROOT / "contrib-heatmap.svg")
        temporary = None
        print(f"Generated contrib-heatmap.svg: {len(payload['days'])} days, {payload['total_contributions']:,} contributions")
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(f"Heatmap generation failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
