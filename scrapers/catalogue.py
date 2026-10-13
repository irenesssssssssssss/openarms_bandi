"""Shared conservative extraction for the approved official sources."""
from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass
from datetime import date
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from pypdf import PdfReader

from config import ADDITIONAL_MAX_DETAILS, ADDITIONAL_MAX_PAGES, PDF_MAX_BYTES
from models import ScrapedGrant
from scrapers.base import BaseScraper

# A complete year is mandatory. Publication dates and yearless dates are never deadlines.
DATE_RE = r"(?:\d{4}-\d{2}-\d{2}|\d{1,2}[/.\-]\d{1,2}[/.\-]\d{4}|\d{1,2}\s+(?:gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre|January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})"
DEADLINE_CUE = r"(?:scadenza|scade(?:\s+il)?|chiusura|deadline(?:\s+for submission)?|closing date|entro(?:\s+il)?|fino\s+(?:al|alle))"


def strict_date(text: str):
    m = re.search(DATE_RE, text or "", re.I)
    return BaseScraper.parse_date(m.group(0).replace('.', '/')) if m else None


def deadline_from_text(text: str):
    text = re.sub(r"[ \t]+", " ", text or "")
    # Prefer explicit closing labels, then submission-window language.
    patterns = [r"(?:scadenza|chiusura|deadline(?: for submission)?|closing date)\s*[:–-]", 
                r"(?:scadenza|scade(?:\s+il)?|deadline(?:\s+for submission)?|chiusura)",
                r"(?:entro(?:\s+il)?|fino\s+(?:al|alle)|non oltre(?:\s+il)?)"]
    for pattern in patterns:
        for match in re.finditer(pattern, text or "", re.I):
            before = text[max(0, match.start()-100):match.start()].lower()
            if re.search(r"in\s*$|progetti.{0,25}$|rendicontazione.{0,30}$|conclusione.{0,30}$", before):
                continue
            fragment = text[match.end():match.end()+110]
            # An unrelated later paragraph cannot supply a missing date/year.
            fragment = re.split(r"\n\s*\n|\[\s*(?:…|\.{3})\s*\]|\bData\s*:|\b(?:apertura|opening date|pubblicazione)\b", fragment, maxsplit=1, flags=re.I)[0]
            m = re.search(DATE_RE, fragment, re.I)
            if m:
                return strict_date(m.group(0))
    return None


def content_soup(html: str):
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup.select('script,style,noscript,nav,header,footer,.bandi-correlati,.related-posts'):
        tag.decompose()
    return soup.select_one('main') or soup.select_one('article') or soup


def content_text(html: str) -> str:
    soup = content_soup(html)
    for tag in reversed(soup.select('p,li,h1,h2,h3,h4,h5')):
        value = tag.get_text(' ', strip=True)
        tag.clear()
        tag.append(value)
    return '\n'.join(BaseScraper.clean_text(line) for line in soup.get_text('\n').splitlines() if BaseScraper.clean_text(line))


@dataclass
class ListingItem:
    title: str
    url: str
    description: str = ''
    category: str = ''
    deadline: date | None = None
    closed: bool | None = None
    amount: str = ''
    external_id: str = ''


class CatalogueScraper(BaseScraper):
    listing_urls: list[str] = []
    funder = ''
    territory = ''
    program = ''

    def parse_listing(self, html: str, url: str) -> list[ListingItem]:
        raise NotImplementedError

    def next_page(self, html: str, url: str) -> str | None:
        soup = self.soup(html)
        a = soup.select_one('a.next.page-numbers, a[rel="next"], .pager__item--next a')
        return urljoin(url, a['href']) if a and a.get('href') else None

    def read_listings(self) -> list[ListingItem]:
        items = {}
        for start in self.listing_urls:
            url = start
            seen_pages = set()
            for page in range(ADDITIONAL_MAX_PAGES):
                if not url or url in seen_pages:
                    break
                seen_pages.add(url)
                result = self.fetch(url)
                for item in self.parse_listing(result.text, result.url):
                    items[item.external_id or item.url] = item
                url = self.next_page(result.text, result.url)
                if page == ADDITIONAL_MAX_PAGES - 1 and url:
                    self.warnings.append(f'Archivio limitato a {ADDITIONAL_MAX_PAGES} pagine: {start}')
        return list(items.values())

    def pdf_text(self, url: str) -> str:
        r = self.fetch(url)
        if len(r.content) > PDF_MAX_BYTES:
            raise ValueError('PDF oltre il limite di 10 MB')
        if not r.content.startswith(b'%PDF'):
            raise ValueError('Il documento non è un PDF pubblico')
        reader = PdfReader(io.BytesIO(r.content))
        text = '\n'.join(page.extract_text() or '' for page in reader.pages[:40])
        if not text.strip():
            raise ValueError('PDF senza testo estraibile: richiede OCR/verifica manuale')
        return text

    def detail_text(self, item: ListingItem) -> str:
        if urlparse(item.url).path.lower().endswith('.pdf'):
            return self.pdf_text(item.url)
        return content_text(self.fetch(item.url).text)

    def make_grant(self, item: ListingItem, text: str = '') -> ScrapedGrant:
        # Extract eligibility evidence from explicit headings or applicant sentences.
        paragraphs = [self.clean_text(x) for x in re.split(r'\n', text) if x.strip()]
        eligible = []
        for i, paragraph in enumerate(paragraphs):
            if re.search(r'^(?:organizzazioni|soggetti|enti) ammissibili$|^beneficiari$|^eligible applicants$|^who can apply', paragraph, re.I):
                eligible.extend(paragraphs[i + 1:i + 9])
            elif re.search(r'possono (?:partecipare|candidarsi|aderire)|si rivolge (?:a|alle)|rivolt[oa] (?:a|agli)|ammess[ei] (?:a|alla)|applicants must|eligible (?:organisations|organizations|entities)', paragraph, re.I):
                eligible.extend(paragraphs[max(0, i):i + 5])
        text = text or item.description
        closed = item.closed
        if closed is None and re.search(r'Bando chiuso|call (?:is )?closed|applications (?:are )?closed', text, re.I):
            closed = True
        return ScrapedGrant(
            source_name=self.source_name, source_url=item.url,
            source_external_id=item.external_id or hashlib.sha256(item.url.encode()).hexdigest()[:24],
            title=item.title, funder=self.funder, program=self.program,
            category=item.category, description=self.clean_text(text)[:22000],
            eligible_entities=self.clean_text(' '.join(dict.fromkeys(eligible)))[:8000],
            territory=self.territory,
            deadline=item.deadline or deadline_from_text(text),
            source_closed=closed, amount_available=item.amount,
            official_url=item.url, raw_text=text[:40000],
            requirements='Requisiti completi da verificare nel bando ufficiale.',
        )

    def scrape(self, known_urls=None) -> list[ScrapedGrant]:
        items = self.read_listings()
        # Revisit active stored grants even if they have moved out of the recent archive.
        have = {item.url for item in items}
        for url in known_urls or []:
            if url in have or urlparse(url).hostname != urlparse(self.listing_urls[0]).hostname:
                continue
            try:
                text = self.detail_text(ListingItem('', url))
                soup = content_soup(self.fetch(url).text) if not urlparse(url).path.endswith('.pdf') else None
                h = soup.select_one('h1') if soup else None
                title = self.clean_text(h.get_text(' ')) if h else urlparse(url).path.rsplit('/', 1)[-1]
                items.append(ListingItem(title, url, text, deadline=deadline_from_text(text)))
            except Exception as exc:
                self.warnings.append(f'Ricontrollo scheda fallito: {url}: {exc}')
        grants = []
        details = 0
        for item in items:
            text = ''
            active = item.closed is not True and not (item.deadline and item.deadline < date.today())
            if active:
                if details < ADDITIONAL_MAX_DETAILS:
                    details += 1
                    try:
                        text = self.detail_text(item)
                    except Exception as exc:
                        self.warnings.append(f'Scheda non letta: {item.url}: {exc}')
                else:
                    self.warnings.append('Limite schede raggiunto: aumentare ADDITIONAL_MAX_DETAILS per una lettura più ampia.')
            grants.append(self.make_grant(item, text))
        return grants
