from __future__ import annotations

import logging
import re
import time
import urllib.robotparser
from dataclasses import dataclass
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from typing import Iterable, Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from config import (
    REQUEST_DELAY_SECONDS,
    REQUEST_RETRIES,
    REQUEST_TIMEOUT_SECONDS,
    ROBOTS_STRICT,
    USER_AGENT,
)

log = logging.getLogger(__name__)

ITALIAN_MONTHS = {
    "gennaio": "january",
    "febbraio": "february",
    "marzo": "march",
    "aprile": "april",
    "maggio": "may",
    "giugno": "june",
    "luglio": "july",
    "agosto": "august",
    "settembre": "september",
    "ottobre": "october",
    "novembre": "november",
    "dicembre": "december",
}


@dataclass
class FetchResult:
    url: str
    text: str
    status_code: int
    content_type: str
    content: bytes = b""


class BaseScraper:
    source_name = "base"

    def __init__(self) -> None:
        self.client = httpx.Client(
            headers={"User-Agent": USER_AGENT, "Accept-Language": "it-IT,it;q=0.9,en;q=0.7"},
            follow_redirects=True,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        self.warnings: list[str] = []
        self._last_request_at = 0.0
        self._robots_cache: dict[str, tuple[urllib.robotparser.RobotFileParser | None, str]] = {}

    def close(self) -> None:
        self.client.close()

    def _sleep_if_needed(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        wait = REQUEST_DELAY_SECONDS - elapsed
        if wait > 0:
            time.sleep(wait)

    def _robots_allowed(self, url: str) -> tuple[bool, str]:
        parsed = urlparse(url)
        root = f"{parsed.scheme}://{parsed.netloc}"
        if root not in self._robots_cache:
            robots_url = f"{root}/robots.txt"
            try:
                self._sleep_if_needed()
                r = self.client.get(robots_url)
                self._last_request_at = time.monotonic()
                if r.status_code >= 400:
                    self._robots_cache[root] = (None, f"robots.txt HTTP {r.status_code}")
                else:
                    rp = urllib.robotparser.RobotFileParser()
                    rp.set_url(robots_url)
                    rp.parse(r.text.splitlines())
                    self._robots_cache[root] = (rp, "robots.txt checked")
            except Exception as exc:
                self._robots_cache[root] = (None, f"robots.txt non verificabile: {exc}")
        rp, reason = self._robots_cache[root]
        if rp is None:
            return (not ROBOTS_STRICT, reason)
        return (rp.can_fetch(USER_AGENT, url), reason)

    def fetch(self, url: str, *, check_robots: bool = True, method: str = "GET", **kwargs) -> FetchResult:
        if check_robots:
            allowed, reason = self._robots_allowed(url)
            if not allowed:
                raise PermissionError(f"robots.txt non consente il fetch di {url}: {reason}")
            if "non verificabile" in reason or "HTTP" in reason:
                log.warning("%s: %s", self.source_name, reason)

        last_exc: Exception | None = None
        for attempt in range(REQUEST_RETRIES + 1):
            try:
                self._sleep_if_needed()
                r = self.client.request(method, url, **kwargs)
                self._last_request_at = time.monotonic()
                r.raise_for_status()
                return FetchResult(
                    url=str(r.url),
                    text=r.text,
                    status_code=r.status_code,
                    content_type=r.headers.get("content-type", ""),
                    content=r.content,
                )
            except Exception as exc:
                last_exc = exc
                if attempt < REQUEST_RETRIES:
                    time.sleep(min(2 ** attempt, 3))
        raise RuntimeError(f"Fetch fallito per {url}: {last_exc}")

    @staticmethod
    def soup(html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "html.parser")

    @staticmethod
    def clean_text(value: str | None) -> str:
        if not value:
            return ""
        return re.sub(r"\s+", " ", value).strip()

    @classmethod
    def page_lines(cls, html: str) -> list[str]:
        soup = cls.soup(html)
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()
        raw = soup.get_text("\n")
        return [cls.clean_text(x) for x in raw.splitlines() if cls.clean_text(x)]

    @staticmethod
    def parse_date(value: str | None) -> Optional[date]:
        if not value:
            return None
        s = value.strip().lower()
        iso = re.match(r"^\d{4}-\d{2}-\d{2}", s)
        if iso:
            try:
                return date.fromisoformat(iso.group(0))
            except ValueError:
                return None
        s = re.sub(r"\b(ore|entro le ore)\s+\d{1,2}[:.]\d{2}\b.*$", "", s).strip()
        for it, en in ITALIAN_MONTHS.items():
            s = re.sub(rf"\b{it}\b", en, s)
        s = s.replace("scadenza", " ").replace("scade", " ")
        s = re.sub(r"[^0-9a-zA-Z/\-. ]+", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        candidates = [
            r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b",
            r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b",
            r"\b\d{1,2}\s+[a-zA-Z]+\s+\d{4}\b",
        ]
        for pattern in candidates:
            m = re.search(pattern, s)
            if not m:
                continue
            try:
                return date_parser.parse(m.group(0), dayfirst=True, fuzzy=True).date()
            except Exception:
                pass
        try:
            return date_parser.parse(s, dayfirst=True, fuzzy=True).date()
        except Exception:
            return None

    @staticmethod
    def parse_feed_date(value: str | None) -> Optional[date]:
        if not value:
            return None
        try:
            return parsedate_to_datetime(value).date()
        except Exception:
            try:
                return date_parser.parse(value).date()
            except Exception:
                return None

    @classmethod
    def extract_section(cls, lines: list[str], labels: Iterable[str], stop_labels: Iterable[str]) -> str:
        norm_labels = {cls._norm_label(x) for x in labels}
        norm_stops = {cls._norm_label(x) for x in stop_labels}
        start = None
        for i, line in enumerate(lines):
            if cls._norm_label(line) in norm_labels:
                start = i + 1
                break
        if start is None:
            return ""
        out: list[str] = []
        for line in lines[start:]:
            if cls._norm_label(line) in norm_stops:
                break
            out.append(line)
        return cls.clean_text(" ".join(out))

    @staticmethod
    def _norm_label(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()

    @classmethod
    def extract_deadline_from_text(cls, text: str) -> Optional[date]:
        patterns = [
            r"(?:scadenza|scade|in scadenza il)\s*[:\-]?\s*([^\n|]{4,50})",
            r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b",
            r"\b\d{1,2}\s+(?:gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+\d{4}\b",
        ]
        for pattern in patterns:
            m = re.search(pattern, text, re.I)
            if m:
                d = cls.parse_date(m.group(1) if m.lastindex else m.group(0))
                if d:
                    return d
        return None
