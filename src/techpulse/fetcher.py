"""HTTP fetching with timeouts, retries, exponential backoff. One bad source never kills a run."""
from __future__ import annotations

import logging
import time
import urllib.request

log = logging.getLogger("techpulse.fetcher")
USER_AGENT = "TechPulse/1.0 (+https://github.com/just-userhere/Engine)"


def fetch_url(url: str, timeout: int = 20, retries: int = 2) -> bytes | None:
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
                if not data:
                    raise ValueError("empty response")
                return data
        except Exception as e:  # noqa: BLE001 — log and degrade gracefully
            last_err = e
            log.warning("fetch failed (%s) attempt %d/%d: %s", url, attempt + 1, retries + 1, e)
            if attempt < retries:
                time.sleep(2 ** attempt)
    log.error("fetch gave up (%s): %s", url, last_err)
    return None
