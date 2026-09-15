"""Normalization: titles, URLs, stable IDs."""
from __future__ import annotations

import hashlib
import re
import urllib.parse

TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
                   "fbclid", "gclid", "mc_cid", "mc_eid", "ref", "source"}
PUNCT = re.compile(r"[^a-z0-9\s]")
WS = re.compile(r"\s+")


def normalize_title(title: str) -> str:
    t = title.lower().strip()
    t = PUNCT.sub(" ", t)
    return WS.sub(" ", t).strip()


def normalize_url(url: str) -> str:
    try:
        p = urllib.parse.urlsplit(url.strip())
        host = p.hostname.lower() if p.hostname else ""
        # drop default ports
        port = ""
        if p.port and not ((p.scheme == "https" and p.port == 443) or (p.scheme == "http" and p.port == 80)):
            port = f":{p.port}"
        netloc = host + port
        # strip tracking query params
        q = urllib.parse.parse_qsl(p.query, keep_blank_values=False)
        q = [(k, v) for k, v in q if k.lower() not in TRACKING_PARAMS]
        q.sort()
        query = urllib.parse.urlencode(q)
        path = p.path.rstrip("/") or ""
        out = urllib.parse.urlunsplit((p.scheme.lower() or "https", netloc, path, query, ""))
        return out
    except Exception:
        return url.strip()


def stable_id(canonical_url: str, normalized_title: str) -> str:
    h = hashlib.sha1(f"{canonical_url}|{normalized_title}".encode("utf-8")).hexdigest()
    return h[:16]
