"""Fetch GitHub's public contribution calendar without an API token."""

import json
import os
import re
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup


OUTPUT = Path(__file__).resolve().parent.parent / "data" / "contributions.json"


def fetch_days(username: str) -> list[dict[str, object]]:
    """Return dated contribution cells, failing on incomplete calendar markup."""
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", username):
        raise ValueError("Invalid GitHub username")
    response = requests.get(
        f"https://github.com/users/{username}/contributions",
        headers={"User-Agent": "GitHubProfileContributionFetcher/1.0 (public profile artwork)"},
        timeout=30,
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    cells = soup.select("td.ContributionCalendar-day")
    if not cells:
        raise ValueError("GitHub response contains no contribution calendar cells")
    tooltips = {
        tooltip.get("for"): tooltip.get_text(" ", strip=True)
        for tooltip in soup.find_all("tool-tip")
        if tooltip.get("for")
    }
    days = []
    seen = set()
    for cell in cells:
        raw_date = cell.get("data-date")
        try:
            if not isinstance(raw_date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_date):
                raise ValueError("missing or malformed date")
            date.fromisoformat(raw_date)
        except ValueError as exc:
            raise ValueError(f"Malformed contribution date: {raw_date!r}") from exc
        if raw_date in seen:
            raise ValueError(f"Duplicate contribution date: {raw_date}")
        raw_level = cell.get("data-level")
        if raw_level not in {"0", "1", "2", "3", "4"}:
            raise ValueError(f"Invalid contribution level for {raw_date}: {raw_level!r}")
        tooltip = tooltips.get(cell.get("id"), "")
        if re.match(r"^No contributions\b", tooltip, re.IGNORECASE):
            count = 0
        else:
            match = re.match(r"^(\d+(?:,\d{3})*)\s+contributions?\b", tooltip, re.IGNORECASE)
            if not match:
                raise ValueError(f"Missing or unrecognized contribution tooltip for {raw_date}")
            count = int(match.group(1).replace(",", ""))
        seen.add(raw_date)
        days.append({"date": raw_date, "count": count, "level": int(raw_level)})
    if not days:
        raise ValueError("GitHub calendar contains no usable contribution days")
    return sorted(days, key=lambda day: day["date"])


def build_payload(username: str, days: list[dict[str, object]]) -> dict[str, object]:
    """Package the parsed calendar with totals and UTC generation metadata."""
    if not days:
        raise ValueError("Cannot build an empty contribution calendar")
    ordered = sorted(days, key=lambda day: day["date"])
    return {
        "username": username,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "range": {"start": ordered[0]["date"], "end": ordered[-1]["date"]},
        "total_contributions": sum(day["count"] for day in ordered),
        "days": ordered,
    }


def main() -> int:
    username = os.environ.get("GH_PROFILE_USER", "felipenalves")
    temporary_path = None
    try:
        payload = build_payload(username, fetch_days(username))
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=OUTPUT.parent, suffix=".tmp", delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
            json.dump(payload, temporary, indent=2, ensure_ascii=False)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, OUTPUT)
        temporary_path = None
    except (requests.RequestException, ValueError, OSError) as exc:
        print(f"Contribution fetch failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    print(f"Saved {len(payload['days'])} days for {username}; total {payload['total_contributions']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
