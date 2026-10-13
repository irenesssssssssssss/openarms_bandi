from __future__ import annotations

import hashlib
import logging
import re
from urllib.parse import urljoin

from bs4 import NavigableString, Tag

from config import CONFINIONLINE_MAX_PAGES
from models import ScrapedGrant
from scrapers.base import BaseScraper

log = logging.getLogger(__name__)


class ConfiniOnlineScraper(BaseScraper):
    source_name = "ConfiniOnline"
    base_url = "https://www.confinionline.it"
    listing_url = f"{base_url}/it/Principale/bandi.aspx"

    def scrape(self, known_urls: list[str] | None = None) -> list[ScrapedGrant]:
        grants: list[ScrapedGrant] = []
        total_pages = 1
        page = 1
        while page <= min(total_pages, CONFINIONLINE_MAX_PAGES):
            url = self.listing_url if page == 1 else f"{self.listing_url}?pagina={page}"
            html = self.fetch(url).text
            if page == 1:
                total_pages = min(self._page_count(html), CONFINIONLINE_MAX_PAGES)
            entries = self._parse_listing(html, url)
            grants.extend(entries)
            if not entries and page > 1:
                break
            page += 1
        return grants

    def _page_count(self, html: str) -> int:
        text = self.clean_text(self.soup(html).get_text(" ", strip=True))
        m = re.search(r"Pagina\s+\d+\s+di\s+(\d+)", text, re.I)
        return int(m.group(1)) if m else 1

    def _parse_listing(self, html: str, page_url: str) -> list[ScrapedGrant]:
        soup = self.soup(html)
        grants: list[ScrapedGrant] = []
        headings = soup.find_all("h3")
        for h3 in headings:
            title = self.clean_text(h3.get_text(" ", strip=True))
            if not title:
                continue

            deadline_text = ""
            prev = h3.find_previous(string=re.compile(r"In scadenza il", re.I))
            if prev:
                deadline_text = self.clean_text(str(prev))

            texts: list[str] = []
            download_url = ""
            for element in h3.next_elements:
                if isinstance(element, Tag) and element.name == "h3" and element is not h3:
                    break
                if isinstance(element, Tag) and element.name == "a" and element.get("href"):
                    label = self.clean_text(element.get_text(" ", strip=True)).lower()
                    if "scarica" in label:
                        download_url = urljoin(page_url, element["href"])
                if isinstance(element, NavigableString):
                    txt = self.clean_text(str(element))
                    if not txt or txt == title or txt.lower() == "scarica":
                        continue
                    if txt not in texts:
                        texts.append(txt)

            # Rimuove elementi di navigazione/rumore comuni e usa il primo frammento breve come categoria.
            clean_parts = [
                t for t in texts
                if not re.match(r"^(pagina\s+\d+|successiva|precedente|\d+)$", t, re.I)
                and not t.lower().startswith("in scadenza il")
            ]
            category = ""
            desc_parts = clean_parts[:]
            if clean_parts and len(clean_parts[0]) <= 80:
                category = clean_parts[0]
                desc_parts = clean_parts[1:]
            description = self.clean_text(" ".join(desc_parts))

            deadline = self.extract_deadline_from_text(deadline_text) if deadline_text else None
            source_url = download_url or page_url
            external_seed = download_url or f"{page_url}|{title}"
            external_id = hashlib.sha1(external_seed.encode("utf-8")).hexdigest()

            grants.append(
                ScrapedGrant(
                    source_name=self.source_name,
                    source_url=source_url,
                    source_external_id=external_id,
                    title=title,
                    funder="",
                    category=category,
                    description=description,
                    objectives=description,
                    activities="",
                    beneficiaries="",
                    eligible_entities="",
                    territory="",
                    partners_required="Non indicato",
                    amount_available="",
                    cofinancing="",
                    open_date=None,
                    deadline=deadline,
                    official_url="",  # Il testo completo richiede iscrizione; non aggiriamo il form.
                    requirements="",
                    raw_text=self.clean_text(f"{title} {category} {description} {deadline_text}"),
                    tags=[x.strip() for x in category.split(",") if x.strip()],
                )
            )
        return grants
