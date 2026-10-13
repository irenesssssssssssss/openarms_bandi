from __future__ import annotations

import hashlib
import logging
import re
from urllib.parse import urljoin, urlparse
from datetime import date

import xml.etree.ElementTree as ET

from config import CSV_LAZIO_MAX_PAGES
from models import ScrapedGrant
from scrapers.base import BaseScraper

log = logging.getLogger(__name__)


class CsvLazioScraper(BaseScraper):
    source_name = "CSV Lazio"
    base_url = "https://volontariatolazio.it"
    category_url = f"{base_url}/category/bandi-e-finanziamenti/"
    feed_url = f"{base_url}/category/bandi-e-finanziamenti/feed/"

    LABELS = [
        "ENTE FINANZIATORE",
        "PROGETTI FINANZIABILI",
        "OBIETTIVI",
        "AZIONI FINANZIABILI",
        "ENTI FINANZIABILI",
        "SOGGETTI AMMISSIBILI",
        "BENEFICIARI",
        "DESTINATARI",
        "AMBITO TERRITORIALE",
        "TERRITORIO",
        "RISORSE COMPLESSIVE",
        "RISORSE PER SINGOLO PROGETTO",
        "COFINANZIAMENTO",
        "SCADENZA",
        "DOCUMENTAZIONE COMPLETA",
        "MODALITÀ E PROCEDURE PER LA PRESENTAZIONE",
    ]

    def scrape(self, known_urls: list[str] | None = None) -> list[ScrapedGrant]:
        urls: dict[str, dict] = {}
        for known in known_urls or []:
            if known:
                urls[known] = {"title": "", "published": None}

        # Preferenza 1 per aggiornamenti: feed RSS di categoria.
        try:
            feed_response = self.fetch(self.feed_url)
            root = ET.fromstring(feed_response.text)
            items = root.findall(".//item")
            if not items:
                raise RuntimeError("Feed RSS senza item")
            for entry in items:
                link = self.clean_text(entry.findtext("link"))
                if link:
                    urls[link] = {
                        "title": self.clean_text(entry.findtext("title")),
                        "published": self.parse_feed_date(entry.findtext("pubDate")),
                    }
        except Exception as exc:
            log.warning("CSV Lazio feed non disponibile: %s", exc)

        # Backfill/fallback: pagine HTML recenti e paginazione WordPress.
        for page in range(1, CSV_LAZIO_MAX_PAGES + 1):
            page_url = self.category_url if page == 1 else f"{self.category_url}page/{page}/"
            try:
                html = self.fetch(page_url).text
            except Exception as exc:
                if page == 1 and not urls:
                    raise
                log.warning("CSV Lazio pagina %s non disponibile: %s", page, exc)
                break
            found = self._listing_links(html)
            if not found and page > 1:
                break
            for link, title in found:
                urls.setdefault(link, {"title": title, "published": None})

        grants: list[ScrapedGrant] = []
        for url, meta in urls.items():
            try:
                listed_deadline = self.extract_deadline_from_text(meta.get("title", ""))
                if listed_deadline and listed_deadline < date.today() and url not in (known_urls or []):
                    continue
                grant = self._parse_detail(url, fallback_title=meta.get("title", ""), published=meta.get("published"))
                if grant.title:
                    grants.append(grant)
            except Exception as exc:
                log.exception("CSV Lazio: errore su %s: %s", url, exc)
        return grants

    def _listing_links(self, html: str) -> list[tuple[str, str]]:
        soup = self.soup(html)
        selectors = [
            "h2.entry-title a[href]",
            "h2.blog-shortcode-post-title a[href]",
            "h3.entry-title a[href]",
            "article h2 a[href]",
            "article h3 a[href]",
            ".fusion-post-content a[href]",
        ]
        anchors = []
        for selector in selectors:
            anchors.extend(soup.select(selector))
        if not anchors:
            anchors = soup.find_all("a", href=True)

        seen = set()
        out = []
        for a in anchors:
            href = urljoin(self.base_url, a.get("href", ""))
            text = self.clean_text(a.get_text(" ", strip=True))
            p = urlparse(href)
            if p.netloc not in {"volontariatolazio.it", "www.volontariatolazio.it"}:
                continue
            if not text or href in seen:
                continue
            if any(x in href for x in ["/category/", "/tag/", "/author/", "/page/", "#"]):
                continue
            # Le schede sono post WordPress; il filtro evita menu e pagine istituzionali.
            cue = (text + " " + href).lower()
            if not any(k in cue for k in ["bando", "avviso", "fondo", "finanzi", "contribut", "scaden", "progett"]):
                continue
            seen.add(href)
            out.append((href, text))
        return out

    def _parse_detail(self, url: str, fallback_title: str = "", published=None) -> ScrapedGrant:
        html = self.fetch(url).text
        soup = self.soup(html)
        lines = self.page_lines(html)

        h1 = soup.find("h1")
        title = self.clean_text(h1.get_text(" ", strip=True) if h1 else fallback_title)
        title = re.sub(r"\s*(?:Scadenza|Scade)\s*[:\-]?.*$", "", title, flags=re.I).strip() or fallback_title

        funder = self.extract_section(lines, ["ENTE FINANZIATORE"], self.LABELS)
        objectives = self.extract_section(lines, ["OBIETTIVI", "OBIETTIVO"], self.LABELS)
        activities = self.extract_section(lines, ["AZIONI FINANZIABILI"], self.LABELS) or self.extract_section(lines, ["PROGETTI FINANZIABILI"], self.LABELS)
        eligible = self.extract_section(lines, ["ENTI FINANZIABILI", "SOGGETTI AMMISSIBILI"], self.LABELS)
        beneficiaries = self.extract_section(lines, ["BENEFICIARI", "DESTINATARI"], self.LABELS)
        territory = self.extract_section(lines, ["AMBITO TERRITORIALE", "TERRITORIO"], self.LABELS)
        amount = self.extract_section(lines, ["RISORSE PER SINGOLO PROGETTO", "RISORSE COMPLESSIVE"], self.LABELS)
        cofinancing = self.extract_section(lines, ["COFINANZIAMENTO"], self.LABELS)
        deadline_text = self.extract_section(lines, ["SCADENZA"], self.LABELS)
        deadline = self.parse_date(deadline_text) or self.extract_deadline_from_text("\n".join(lines[:80]))

        official_url = ""
        for a in soup.find_all("a", href=True):
            label = self.clean_text(a.get_text(" ", strip=True)).lower()
            href = urljoin(url, a["href"])
            host = urlparse(href).netloc.lower()
            if any(k in label for k in ["link al bando", "visita il sito", "documentazione completa", "sito del bando"]):
                if "volontariatolazio.it" not in host:
                    official_url = href
                    break

        raw_main = self.clean_text(" ".join(lines))
        desc = objectives or activities
        req = " ".join(x for x in [eligible, territory, cofinancing] if x)
        external_id = hashlib.sha1(url.encode("utf-8")).hexdigest()

        return ScrapedGrant(
            source_name=self.source_name,
            source_url=url,
            source_external_id=external_id,
            title=title,
            funder=funder,
            category="",
            description=desc,
            objectives=objectives,
            activities=activities,
            beneficiaries=beneficiaries,
            eligible_entities=eligible,
            territory=territory,
            partners_required=self._partner_requirement(raw_main),
            amount_available=amount,
            cofinancing=cofinancing,
            open_date=published,
            deadline=deadline,
            official_url=official_url,
            requirements=req,
            raw_text=raw_main,
            tags=[],
        )

    @staticmethod
    def _partner_requirement(text: str) -> str:
        low = text.lower()
        if any(k in low for k in ["partenariato obbligatorio", "partner obbligatori", "deve costituire un partenariato", "in ats"]):
            return "Sì"
        if "partenari" in low or "partner" in low or "ats" in low:
            return "Da verificare"
        return "Non indicato"
