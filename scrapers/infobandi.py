from __future__ import annotations

import hashlib
import logging
import re
from urllib.parse import urljoin, urlparse

from config import INFOBANDI_MAX_PAGES
from models import ScrapedGrant
from scrapers.base import BaseScraper

log = logging.getLogger(__name__)


class InfobandiScraper(BaseScraper):
    source_name = "Infobandi"
    base_url = "https://infobandi.csvnet.it"
    listing_url = f"{base_url}/home/bandi-attivi/"

    LABELS = [
        "ENTE EROGATORE",
        "SCADENZA",
        "OBIETTIVO",
        "OBIETTIVI",
        "AZIONI FINANZIABILI",
        "DESTINATARI",
        "BENEFICIARI",
        "PAESI AMMISSIBILI",
        "AMBITO TERRITORIALE",
        "ENTI AMMISSIBILI",
        "SOGGETTI AMMISSIBILI",
        "DOTAZIONE FINANZIARIA DISPONIBILE",
        "ENTITÀ DEL CONTRIBUTO",
        "COFINANZIAMENTO",
        "MODALITÀ E PROCEDURE PER LA PRESENTAZIONE",
        "LINGUA SCRITTURA DEL FORMULARIO",
        "CONTATTI",
        "ULTERIORI INFORMAZIONI",
        "Tag",
    ]

    def scrape(self, known_urls: list[str] | None = None) -> list[ScrapedGrant]:
        detail_urls: dict[str, str] = {}
        total_pages = 1
        page = 1
        while page <= min(total_pages, INFOBANDI_MAX_PAGES):
            url = self.listing_url if page == 1 else f"{self.listing_url}?sf_paged={page}"
            html = self.fetch(url).text
            if page == 1:
                total_pages = min(self._page_count(html), INFOBANDI_MAX_PAGES)
            for href, title in self._listing_links(html):
                detail_urls[href] = title
            page += 1

        grants = []
        for url, title in detail_urls.items():
            try:
                grant = self._parse_detail(url, title)
                if grant.title:
                    grants.append(grant)
            except Exception as exc:
                log.exception("Infobandi: errore su %s: %s", url, exc)
        return grants

    def _page_count(self, html: str) -> int:
        text = self.clean_text(self.soup(html).get_text(" ", strip=True))
        m = re.search(r"Pagina\s+\d+\s+di\s+(\d+)", text, re.I)
        return int(m.group(1)) if m else 1

    def _listing_links(self, html: str) -> list[tuple[str, str]]:
        soup = self.soup(html)
        out, seen = [], set()
        for h in soup.find_all(["h2", "h3"]):
            a = h.find("a", href=True)
            if not a:
                continue
            href = urljoin(self.base_url, a["href"])
            title = self.clean_text(a.get_text(" ", strip=True))
            if not title or href in seen:
                continue
            p = urlparse(href)
            if p.netloc != urlparse(self.base_url).netloc:
                continue
            if any(x in href for x in ["/tag/", "/home/", "/category/"]):
                continue
            seen.add(href)
            out.append((href, title))
        return out

    def _parse_detail(self, url: str, fallback_title: str) -> ScrapedGrant:
        html = self.fetch(url).text
        soup = self.soup(html)
        lines = self.page_lines(html)
        h1 = soup.find("h1")
        title = self.clean_text(h1.get_text(" ", strip=True) if h1 else fallback_title)

        funder = self.extract_section(lines, ["ENTE EROGATORE"], self.LABELS)
        deadline_text = self.extract_section(lines, ["SCADENZA"], self.LABELS)
        objectives = self.extract_section(lines, ["OBIETTIVO", "OBIETTIVI"], self.LABELS)
        activities = self.extract_section(lines, ["AZIONI FINANZIABILI"], self.LABELS)
        beneficiaries = self.extract_section(lines, ["DESTINATARI", "BENEFICIARI"], self.LABELS)
        countries = self.extract_section(lines, ["PAESI AMMISSIBILI"], self.LABELS)
        scope = self.extract_section(lines, ["AMBITO TERRITORIALE"], self.LABELS)
        territory = self.clean_text(" ".join(x for x in [countries, scope] if x))
        eligible = self.extract_section(lines, ["ENTI AMMISSIBILI", "SOGGETTI AMMISSIBILI"], self.LABELS)
        total_amount = self.extract_section(lines, ["DOTAZIONE FINANZIARIA DISPONIBILE"], self.LABELS)
        contribution = self.extract_section(lines, ["ENTITÀ DEL CONTRIBUTO"], self.LABELS)
        amount = self.clean_text(" ".join(x for x in [total_amount, contribution] if x))
        cofinancing = self.extract_section(lines, ["COFINANZIAMENTO"], self.LABELS)

        tags = []
        tag_idx = next((i for i, x in enumerate(lines) if x.lower() == "tag"), None)
        if tag_idx is not None and tag_idx + 1 < len(lines):
            tag_text = lines[tag_idx + 1]
            tag_text = tag_text.strip("[]")
            tags = [self.clean_text(x) for x in tag_text.split(",") if self.clean_text(x)]

        official_url = ""
        for a in soup.find_all("a", href=True):
            label = self.clean_text(a.get_text(" ", strip=True)).lower()
            href = urljoin(url, a["href"])
            host = urlparse(href).netloc
            if any(k in label for k in ["link al bando", "documentazione completa", "sito web del"]):
                if host and host != urlparse(self.base_url).netloc:
                    official_url = href
                    break

        raw = self.clean_text(" ".join(lines))
        req = " ".join(x for x in [eligible, territory, cofinancing] if x)
        external_id = hashlib.sha1(url.encode("utf-8")).hexdigest()

        return ScrapedGrant(
            source_name=self.source_name,
            source_url=url,
            source_external_id=external_id,
            title=title,
            funder=funder,
            category=", ".join(tags[:4]),
            description=objectives or activities,
            objectives=objectives,
            activities=activities,
            beneficiaries=beneficiaries,
            eligible_entities=eligible,
            territory=territory,
            partners_required=self._partner_requirement(raw),
            amount_available=amount,
            cofinancing=cofinancing,
            open_date=None,
            deadline=self.parse_date(deadline_text),
            official_url=official_url,
            requirements=req,
            raw_text=raw,
            tags=tags,
        )

    @staticmethod
    def _partner_requirement(text: str) -> str:
        low = text.lower()
        if any(k in low for k in ["partner obbligatori", "partenariato obbligatorio", "in ats", "raggruppamento obbligatorio"]):
            return "Sì"
        if "in qualità di partner" in low or "partenari" in low:
            return "Da verificare"
        return "Non indicato"
