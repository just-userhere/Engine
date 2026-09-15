"""Parse RSS 2.0 + Atom with stdlib only. Never executes fetched content."""
from __future__ import annotations

import html
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

log = logging.getLogger("techpulse.parser")
TAG_STRIP = re.compile(r"<[^>]+>")


def _clean(text: str | None) -> str:
    if not text:
        return ""
    text = TAG_STRIP.sub(" ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    s = s.strip()
    try:
        dt = parsedate_to_datetime(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            v = s.replace("Z", "+0000") if s.endswith("Z") else s
            dt = datetime.strptime(v, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            continue
    return None


@dataclass
class RawItem:
    title: str
    url: str
    published_at: datetime | None
    summary: str
    source: str = ""
    category_default: str = "Technology"
    reliability: float = 0.7
    extra: dict = field(default_factory=dict)


def parse_feed(xml_bytes: bytes, source_name: str, category_default: str = "Technology",
               reliability: float = 0.7) -> list[RawItem]:
    try:
        root = ET.fromstring(xml_bytes)
    except Exception as e:
        log.warning("malformed feed from %s: %s", source_name, e)
        return []
    items: list[RawItem] = []
    # RSS: channel/item ; Atom: entry (namespace aware fallback by localname)
    for el in root.iter():
        local = el.tag.rsplit("}", 1)[-1]
        if local not in ("item", "entry"):
            continue
        title = link = desc = datestr = ""
        for child in el:
            c = child.tag.rsplit("}", 1)[-1].lower()
            txt = (child.text or "").strip()
            if c == "title":
                title = txt
            elif c == "link":
                if txt:
                    link = txt
                else:  # Atom <link href="..."/>
                    href = child.attrib.get("href", "")
                    if href:
                        link = href
            elif c in ("description", "summary", "content", "encoded"):
                if not desc:
                    desc = txt
            elif c in ("pubdate", "published", "updated", "date"):
                if not datestr:
                    datestr = txt
        if not title or not link:
            continue
        items.append(RawItem(
            title=_clean(title), url=link.strip(),
            published_at=_parse_date(datestr),
            summary=_clean(desc)[:2000],
            source=source_name, category_default=category_default,
            reliability=reliability,
        ))
    return items
