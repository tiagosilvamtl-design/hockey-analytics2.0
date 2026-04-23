"""Minimal whitelist RSS scraper. Off by default; user opts in per source.

Pulls title + lede + URL only — no full text. Stance is NEVER inferred automatically;
user must tag each pulled entry before it enters the cross-check view.
"""
from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import requests

from config import NST_USER_AGENT

DEFAULT_SOURCES: list[dict] = [
    # Friendly, obvious public RSS feeds. User can edit in the UI.
    # Deliberately empty by default — opt-in per source.
]


@dataclass
class FeedItem:
    source: str
    url: str
    title: str
    lede: str
    date: str | None


def fetch_rss(url: str, source_label: str, limit: int = 10) -> list[FeedItem]:
    headers = {"User-Agent": NST_USER_AGENT, "Accept": "application/rss+xml, application/xml, text/xml"}
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    items: list[FeedItem] = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = (item.findtext("description") or "").strip()
        date = (item.findtext("pubDate") or "").strip() or None
        lede = _strip_html(desc)
        if len(lede) > 400:
            lede = lede[:397] + "..."
        items.append(FeedItem(source=source_label, url=link, title=html.unescape(title), lede=lede, date=date))
        if len(items) >= limit:
            break
    return items


def _strip_html(text: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", text))
