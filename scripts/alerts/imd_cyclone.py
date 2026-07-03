"""Collect current official cyclone bulletin links from IMD RSMC New Delhi."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

import requests

from scripts.sources.common.config import PROJECT_ROOT

SOURCE_URL = "https://rsmcnewdelhi.imd.gov.in/"
OUTPUT = PROJECT_ROOT / "data/silver/alerts/imd_cyclone.json"


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attributes: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            self._href = dict(attributes).get("href")
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            self.links.append({"href": self._href, "text": " ".join(self._text).strip()})
            self._href = None
            self._text = []


def parse_bulletins(html: str) -> dict:
    parser = LinkParser()
    parser.feed(html)
    bulletins = []
    for link in parser.links:
        text = " ".join(link["text"].split())
        combined = f"{text} {link['href']}".lower()
        if not any(
            phrase in combined
            for phrase in (
                "tropical weather outlook",
                "national bulletin",
                "rsmc bulletin",
                "no_cyclone",
            )
        ):
            continue
        bulletins.append(
            {
                "title": text or Path(link["href"]).name,
                "url": urljoin(SOURCE_URL, link["href"]),
            }
        )
    unique = {item["url"]: item for item in bulletins}
    bulletins = list(unique.values())
    no_cyclone = any("no_cyclone" in item["url"].lower() for item in bulletins)
    active_national = any(
        "national bulletin" in item["title"].lower()
        and "no_cyclone" not in item["url"].lower()
        for item in bulletins
    )
    status = (
        "ACTIVE_CYCLONE_BULLETIN"
        if active_national
        else "NO_ACTIVE_CYCLONE_BULLETIN"
        if no_cyclone
        else "OUTLOOK_AVAILABLE"
        if bulletins
        else "UNAVAILABLE"
    )
    return {"status": status, "bulletins": bulletins}


def collect(session: requests.Session | None = None) -> dict:
    session = session or requests.Session()
    response = session.get(
        SOURCE_URL,
        timeout=60,
        headers={"User-Agent": "SusBiome weather outlook/1.0"},
    )
    response.raise_for_status()
    parsed = parse_bulletins(response.text)
    result = {
        "collected_at": datetime.now(UTC).isoformat(),
        "source": "India Meteorological Department RSMC New Delhi",
        "source_url": SOURCE_URL,
        "official_confirmation": True,
        **parsed,
        "disclaimer": "IMD bulletins remain authoritative; SusBiome does not reproduce warning instructions.",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(result, indent=2), encoding="utf-8")
    temporary.replace(OUTPUT)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("collect", "status"), nargs="?", default="collect")
    arguments = parser.parse_args()
    if arguments.command == "collect":
        result = collect()
    else:
        if not OUTPUT.exists():
            raise SystemExit("IMD cyclone confirmation has not been collected.")
        result = json.loads(OUTPUT.read_text(encoding="utf-8"))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
