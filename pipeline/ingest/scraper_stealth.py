"""
HTTP scraper stealth utilities — user-agent rotation, jitter delays,
retry logic, and header randomisation for Indian news portals.

Usage:
    from ingestion.scraper_stealth import StealthSession, jitter_sleep

    sess = StealthSession()
    html = sess.get("https://www.jagran.com/uttar-pradesh/gorakhpur")

    jitter_sleep(base=1.5, jitter=0.8)   # sleeps 1.5 ± 0.8 s
"""

from __future__ import annotations

import logging
import os
import random
import time
import urllib.error
import urllib.request
from typing import Optional

logger = logging.getLogger(__name__)

# ── User-agent pool ───────────────────────────────────────────────────────────
# Rotated pool of real browser UAs — mix of Chrome, Firefox, Edge on
# Windows/Mac/Android to avoid fingerprinting by a single static UA.

_USER_AGENTS: list[str] = [
    # Chrome Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    # Chrome macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    # Firefox Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    # Firefox macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:125.0) Gecko/20100101 Firefox/125.0",
    # Edge Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    # Chrome Android (mobile UA for sites with mobile-first pages)
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.82 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.40 Mobile Safari/537.36",
]

# Accept-Language variants to rotate
_ACCEPT_LANGUAGES: list[str] = [
    "hi-IN,hi;q=0.9,en-IN;q=0.8,en;q=0.7",
    "en-IN,en;q=0.9,hi;q=0.8",
    "hi;q=0.9,en-US;q=0.7,en;q=0.6",
    "en-US,en;q=0.9,hi;q=0.8",
    "hi-IN,hi;q=0.8,en-GB;q=0.6,en;q=0.5",
]

# Referer pool for common Indian news navigation paths
_REFERERS: list[str] = [
    "https://www.google.co.in/",
    "https://www.google.com/",
    "https://news.google.com/",
    "",  # no referer (direct navigation)
    "",  # weighted blank — direct is common
]


def _random_ua() -> str:
    return random.choice(_USER_AGENTS)


def _random_lang() -> str:
    return random.choice(_ACCEPT_LANGUAGES)


def _random_referer() -> str:
    return random.choice(_REFERERS)


def _build_headers(extra: Optional[dict] = None) -> dict:
    """Build a randomised, realistic browser header set."""
    ua = _random_ua()
    is_firefox = "Firefox" in ua
    is_mobile = "Mobile" in ua

    headers: dict[str, str] = {
        "User-Agent": ua,
        "Accept-Language": _random_lang(),
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
    }

    if is_firefox:
        headers["Accept"] = (
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        )
        headers["Connection"] = "keep-alive"
    else:
        headers["Accept"] = (
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
        )
        headers["sec-ch-ua"] = '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"'
        headers["sec-ch-ua-mobile"] = "?1" if is_mobile else "?0"
        headers["sec-ch-ua-platform"] = '"Android"' if is_mobile else '"Windows"'
        headers["sec-fetch-dest"] = "document"
        headers["sec-fetch-mode"] = "navigate"
        headers["sec-fetch-site"] = "none" if not _random_referer() else "cross-site"
        headers["sec-fetch-user"] = "?1"

    ref = _random_referer()
    if ref:
        headers["Referer"] = ref

    if extra:
        headers.update(extra)

    return headers


# ── Jitter sleep ──────────────────────────────────────────────────────────────


def jitter_sleep(base: float = 1.5, jitter: float = 0.8) -> None:
    """Sleep for base ± jitter seconds (uniform distribution)."""
    sleep_time = max(0.1, base + random.uniform(-jitter, jitter))
    time.sleep(sleep_time)


# ── StealthSession ────────────────────────────────────────────────────────────


class StealthSession:
    """
    urllib-based HTTP session with:
      - Rotating user-agents and Accept-Language headers
      - Randomised jitter delays between requests
      - Gzip decompression
      - Retry with exponential backoff on 429 / 5xx

    Drop-in replacement for the existing `_fetch_text` helper.
    """

    def __init__(
        self,
        base_delay: float = 1.5,
        jitter: float = 0.8,
        max_retries: int = 3,
        backoff_base: float = 2.0,
    ):
        self.base_delay = base_delay
        self.jitter = jitter
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self._last_fetch: float = 0.0

    def _polite_wait(self) -> None:
        """Enforce minimum delay since last request."""
        elapsed = time.time() - self._last_fetch
        target = self.base_delay + random.uniform(-self.jitter, self.jitter)
        wait = max(0, target - elapsed)
        if wait > 0:
            time.sleep(wait)

    def _get_proxy_handler(self) -> urllib.request.ProxyHandler:
        """Fetch and rotate proxies from SCRAPER_PROXIES environment variable."""
        proxies_str = os.environ.get("SCRAPER_PROXIES")
        if proxies_str:
            proxies = [p.strip() for p in proxies_str.split(",") if p.strip()]
            if proxies:
                proxy = random.choice(proxies)
                logger.debug("[stealth] Using proxy: %s", proxy)
                return urllib.request.ProxyHandler({"http": proxy, "https": proxy})
        return urllib.request.ProxyHandler({})

    def get(
        self,
        url: str,
        timeout: int = 20,
        extra_headers: Optional[dict] = None,
    ) -> Optional[str]:
        """
        Fetch URL with stealth headers.  Returns decoded HTML or None on failure.
        Retries on 429 / 5xx with exponential backoff.
        """
        self._polite_wait()
        headers = _build_headers(extra_headers)

        for attempt in range(self.max_retries):
            try:
                req = urllib.request.Request(url, headers=headers)
                proxy_handler = self._get_proxy_handler()
                opener = urllib.request.build_opener(
                    proxy_handler, urllib.request.HTTPRedirectHandler()
                )
                with opener.open(req, timeout=timeout) as resp:
                    raw = resp.read()

                # Decompress gzip
                if raw[:2] == b"\x1f\x8b":
                    import gzip as _gzip

                    raw = _gzip.decompress(raw)

                self._last_fetch = time.time()

                for enc in ("utf-8", "utf-8-sig", "latin-1"):
                    try:
                        return raw.decode(enc)
                    except UnicodeDecodeError:
                        continue
                return raw.decode("utf-8", errors="replace")

            except urllib.error.HTTPError as exc:
                if exc.code in (429, 503, 502, 504):
                    wait = self.backoff_base ** (attempt + 1) + random.uniform(0, 2)
                    logger.warning(
                        "[stealth] HTTP %d for %s — retrying in %.1fs (attempt %d/%d)",
                        exc.code,
                        url,
                        wait,
                        attempt + 1,
                        self.max_retries,
                    )
                    time.sleep(wait)
                    # Rotate UA on retry
                    headers = _build_headers(extra_headers)
                    continue
                logger.warning("[stealth] HTTP %d for %s", exc.code, url)
                return None
            except Exception as exc:
                logger.warning("[stealth] Fetch failed %s (attempt %d): %s", url, attempt + 1, exc)
                if attempt < self.max_retries - 1:
                    time.sleep(self.backoff_base ** (attempt + 1))

        self._last_fetch = time.time()
        return None


# ── Module-level default session ──────────────────────────────────────────────

_default_session: Optional[StealthSession] = None


def get_default_session() -> StealthSession:
    """Get the module-level default StealthSession (singleton)."""
    global _default_session
    if _default_session is None:
        _default_session = StealthSession()
    return _default_session


def fetch(url: str, timeout: int = 20) -> Optional[str]:
    """Convenience wrapper using the default StealthSession."""
    return get_default_session().get(url, timeout=timeout)
