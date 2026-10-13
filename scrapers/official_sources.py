from __future__ import annotations

import json
import re
from urllib.parse import urljoin

from config import ADDITIONAL_MAX_PAGES
from scrapers.catalogue import CatalogueScraper, ListingItem, deadline_from_text, strict_date


def text(node, selector=''):
    tag = node.select_one(selector) if selector else node
    return tag.get_text(' ', strip=True) if tag else ''


class ConIlSudScraper(CatalogueScraper):
    source_name = 'Fondazione CON IL SUD'
    funder = source_name
    listing_urls = ['https://www.fondazioneconilsud.it/bandi/']

    def parse_listing(self, html, url):
        soup = self.soup(html)
        cards = soup.select('article.bando-card')
        if not cards:
            raise ValueError('Struttura elenco CON IL SUD non riconosciuta')
        items = []
        for card in cards:
            link = card.select_one('.bando-card__title a[href]')
            if not link:
                continue
            meta = {text(row, '.bando-metaLabel').rstrip(':'): text(row, '.bando-metaValue') for row in card.select('.bando-metaRow')}
            state = text(card, '.bando-badge--status').lower()
            items.append(ListingItem(text(link), urljoin(url, link['href']), text(card, '.bando-card__excerpt'),
                text(card, '.bando-card__badges'), strict_date(meta.get('Scadenza', '')),
                state == 'scaduto' if state else None, meta.get('Risorse', '')))
        return items


class SanPaoloScraper(CatalogueScraper):
    source_name = 'Compagnia di San Paolo'
    funder = source_name
    listing_urls = ['https://www.compagniadisanpaolo.it/it/cosa-facciamo/contributi/']

    def parse_listing(self, html, url):
        cards = self.soup(html).select('.vco-bando-card')
        if not cards:
            raise ValueError('Struttura elenco San Paolo non riconosciuta')
        return [ListingItem(text(c, '.vco-bando-titolo'), urljoin(url, c.select_one('.vco-bando-titolo a')['href']),
            category=text(c, '.vco-bando-aree'), deadline=strict_date(text(c, '.vco-bando-scadenza')),
            closed=text(c, '.vco-bando-stato').upper() == 'CHIUSO') for c in cards if c.select_one('.vco-bando-titolo a')]

    def next_page(self, html, url):
        from urllib.parse import urlparse, parse_qs
        current = int(parse_qs(urlparse(url).query).get('sf_paged', ['1'])[0])
        for a in self.soup(html).select('a[href]'):
            if a.get_text(strip=True) == str(current + 1) and 'sf_paged=' in a['href']:
                return urljoin(url, a['href'])
        return None


class UnipolisScraper(CatalogueScraper):
    source_name = 'Fondazione Unipolis'
    funder = source_name
    listing_urls = ['https://www.fondazioneunipolis.org/site/bandi/']
    api_url = 'https://www.fondazioneunipolis.org/site/wp-json/unipolis/v1/filtra-bandi'

    def read_listings(self):
        # The public endpoint and payload are used by the official listing page itself.
        r = self.fetch(self.api_url, method='POST', json={'chips': [], 'year': '', 'toggle': False})
        html = json.loads(r.text)
        if not isinstance(html, str):
            raise ValueError('Risposta Unipolis non riconosciuta (attesa stringa HTML JSON)')
        return self.parse_listing(html, self.listing_urls[0])

    def parse_listing(self, html, url):
        soup = self.soup(html)
        cards = soup.select('.card-bando')
        if not cards and soup.get_text(strip=True) and re.search('nessun|non ci sono', soup.get_text(), re.I):
            return []
        if not cards:
            raise ValueError('Elenco Unipolis vuoto/non riconosciuto')
        items = []
        for c in cards:
            a = c.select_one('a[href*="/bando/"]')
            if a:
                items.append(ListingItem(text(c, '.card-title-bando'), urljoin(url, a['href']), text(c, '.card-description'), text(c, '.tags-container')))
        return items


class PnInclusioneScraper(CatalogueScraper):
    source_name = 'PN Inclusione'
    funder = 'Ministero del Lavoro e delle Politiche Sociali'
    program = 'PN Inclusione 2021–2027'
    listing_urls = ['https://pninclusione21-27.lavoro.gov.it/avvisi/archivio-avvisi',
                    'https://pninclusione21-27.lavoro.gov.it/']

    def parse_listing(self, html, url):
        soup = self.soup(html)
        cards = soup.select('.container-card')
        items = []
        for c in cards:
            a = c.select_one('a[href^="/avvisi/"],a[href^="/preavvisi/"]')
            if a and not a['href'].endswith('archivio-avvisi'):
                items.append(ListingItem(text(c, '.card-title') or a.get('aria-label', ''), urljoin(url, a['href']), text(c, '.font-size-text')))
        if not items:
            raise ValueError('Struttura elenco PN Inclusione non riconosciuta')
        return items

    def detail_text(self, item):
        from scrapers.catalogue import content_text
        soup = self.soup(self.fetch(item.url).text)
        section = soup.select_one('.text-area-section')
        return content_text(str(section)) if section else content_text(str(soup))


class AicsScraper(CatalogueScraper):
    source_name = 'AICS'
    funder = 'Agenzia Italiana per la Cooperazione allo Sviluppo'
    listing_urls = ['https://www.aics.gov.it/category/bandi/']

    def parse_listing(self, html, url):
        soup = self.soup(html)
        links = soup.select('a[data-element="news-category-link"]')
        if not links:
            raise ValueError('Struttura elenco AICS non riconosciuta')
        items = []
        for a in links:
            title = text(a)
            # Results, FAQ releases, appointments and purchasing tenders aren't new grants.
            if re.search(r'FAQ|graduatoria|esiti|elenco.*(?:proposte|iniziative)|iniziative ammissibili|verbale esito|commissioni|verbale|incontro|info day|consultazione|acquisto|procedura di gara|appalto|accreditamento stampa', title, re.I):
                continue
            if not re.search(r'bando|avviso|call for proposals|candidature|procedura comparativa', title, re.I):
                continue
            if re.search('new leaders lab|ricercator|selezione.*personale', title, re.I):
                continue
            card = a.find_parent(class_='card-body') or a.parent
            description = text(card, '.card-text')
            items.append(ListingItem(title, urljoin(url, a['href']), description, deadline=deadline_from_text(description)))
        return items


class MinisteroLavoroScraper(CatalogueScraper):
    source_name = 'Ministero Lavoro – Terzo Settore'
    funder = 'Ministero del Lavoro e delle Politiche Sociali'
    listing_urls = ['https://www.lavoro.gov.it/taxonomy/term/66',
                    'https://www.lavoro.gov.it/temi-e-priorita/Terzo-settore-e-responsabilita-sociale-imprese/Pagine/default']

    def parse_listing(self, html, url):
        soup = self.soup(html)
        soup = soup.select_one("main") or soup
        if 'terzo settore' not in soup.get_text(' ', strip=True).lower():
            raise ValueError('Pagina Ministero non riconosciuta')
        items = {}
        for a in soup.select('a[href]'):
            href = urljoin(url, a['href'])
            if re.search(r'/pagine/avviso-\d+-\d{4}/?$', href, re.I):
                title = 'Avviso ' + href.rsplit('/', 1)[-1].replace('avviso-', '').replace('-', '/')
                items[href] = ListingItem(title, href, category='Terzo Settore')
        # Follow the canonical call link inside official announcement pages.
        for a in soup.select('a[href*="/notizie/pagine/"]'):
            title = text(a)
            if re.search(r'avviso.*finanziamento|bando.*terzo settore', title, re.I) and a.get('href'):
                href = urljoin(url, a['href'])
                if href not in items:
                    r = self.fetch(href)
                    for call in self.soup(r.text).select('a[href]'):
                        target = urljoin(href, call['href'])
                        if re.search(r'/pagine/avviso-\d+-\d{4}/?$', target, re.I):
                            items[target] = ListingItem('Avviso ' + target.rsplit('/', 1)[-1].replace('avviso-', '').replace('-', '/'), target, category='Terzo Settore')
        return list(items.values())

    def detail_text(self, item):
        from scrapers.catalogue import content_text
        r = self.fetch(item.url)
        soup = self.soup(r.text)
        soup = soup.select_one('article.node') or soup.select_one('main') or soup
        pieces = [content_text(str(soup))]
        for a in soup.select('a[href]'):
            title = text(a)
            href = urljoin(item.url, a['href'])
            if '/documenti/' in href and re.fullmatch(r'Avviso\s+(?:n\.?\s*)?\d+[/–-]\d{4}', title, re.I):
                try:
                    doc = self.fetch(href)
                    if doc.content.startswith(b'%PDF'):
                        pdf = self.pdf_text(href)
                        pieces.append(pdf)
                        sections = list(re.finditer(r'§\s*6[.\s].{0,100}MODALIT', pdf, re.I))
                        if sections:
                            portion = re.split(r'§\s*7[.\s]', pdf[sections[-1].start():], maxsplit=1)[0]
                            item.deadline = deadline_from_text(portion)
                    else:
                        link = self.soup(doc.text).select_one('a[href$=".pdf"]')
                        if not link:
                            raise ValueError('Link al PDF di avviso non individuato')
                        pdf = self.pdf_text(urljoin(href, link['href']))
                        # Read submission terms, not the project completion/reporting section.
                        sections = list(re.finditer(r'§\s*6[.\s].{0,100}MODALIT', pdf, re.I))
                        if sections:
                            portion = pdf[sections[-1].start():]
                            portion = re.split(r'§\s*7[.\s]', portion, maxsplit=1)[0]
                            item.deadline = deadline_from_text(portion)
                        pieces.append(pdf)
                except Exception as exc:
                    self.warnings.append(f'Avviso PDF non letto: {href}: {exc}')
                break
        return '\n'.join(pieces)


class IntegrazioneMigrantiScraper(CatalogueScraper):
    source_name = 'Integrazione Migranti'
    listing_urls = ['https://www.integrazionemigranti.gov.it/it-it/Ricerca-bandi']

    def parse_listing(self, html, url):
        soup = self.soup(html)
        links = soup.select('a[href*="/Dettaglio-bando/"]')
        if not links:
            if re.search(r'0 Risultati', soup.get_text()):
                return []
            raise ValueError('Struttura elenco Integrazione Migranti non riconosciuta')
        items = []
        for a in links:
            title = text(a, '.listaTitle')
            # Individual scholarships/courses/job applications are not organisation grants.
            if re.search(r'borse di studio|corso gratuito|laboratori gratuiti|formazione gratuita|corso lingua|ricercatric|ricercator|diventare agente|iscriversi', title, re.I):
                continue
            if title:
                items.append(ListingItem(title, urljoin(url, a['href']), text(a, '.dettaglio-abstract')))
        return items

    def read_listings(self):
        url = self.listing_urls[0]
        result = self.fetch(url)
        items = {}
        for page in range(ADDITIONAL_MAX_PAGES):
            soup = self.soup(result.text)
            for item in self.parse_listing(result.text, result.url):
                items[item.url] = item
            pager_indices = [int(x) for x in re.findall(r"setPagina\('(\d+)'\)", result.text)]
            if not pager_indices or page >= max(pager_indices):
                break
            if page == ADDITIONAL_MAX_PAGES - 1:
                self.warnings.append(f'Archivio limitato alle prime {ADDITIONAL_MAX_PAGES} pagine recenti.')
                break
            # Public ASP.NET form pagination, including the server-issued hidden fields.
            fields = {x['name']: x.get('value', '') for x in soup.select('input[name]')
                      if x.get('type', '').lower() in ('hidden', 'text')}
            pagination = next((k for k in fields if k.endswith('$txtPaginaCorrente')), None)
            if not pagination:
                raise ValueError('Paginazione ASP.NET non riconosciuta')
            fields[pagination] = str(page + 1)
            fields['__EVENTTARGET'] = 'vaiAllaPagina'
            fields['__EVENTARGUMENT'] = ''
            following = self.fetch(url, method='POST', data=fields)
            if [x.url for x in self.parse_listing(following.text, url)] == [x.url for x in self.parse_listing(result.text, url)]:
                self.warnings.append('Paginazione ignorata dal server: letta solo la pagina corrente.')
                break
            result = following
        return list(items.values())


    def detail_text(self, item):
        from scrapers.catalogue import content_text
        soup = self.soup(self.fetch(item.url).text)
        section = soup.select_one('.dettaglioBando') or soup
        return content_text(str(section))


class SardegnaScraper(CatalogueScraper):
    source_name = 'Fondazione di Sardegna'
    funder = source_name
    territory = 'Sardegna (vincoli specifici da verificare)'
    listing_urls = ['https://www.fondazionedisardegna.it/contributi/bandi-rol',
                    'https://www.fondazionedisardegna.it/contributi/Bandi-Settore-Educazione',
                    'https://www.fondazionedisardegna.it/contributi/bandi-partecipazione-fondazione']

    def parse_listing(self, html, url):
        soup = self.soup(html)
        for t in soup.select('header,footer,nav'):
            t.decompose()
        pdfs = []
        for a in soup.select('a[href]'):
            name = text(a)
            if '.pdf' not in a['href'].lower() or not re.search('bando|progetto', name, re.I) or re.search('faq|guida|regolamento generale|elenco|ammessi|graduatoria|esiti', name, re.I):
                continue
            title = re.sub(r'^Scarica\s*|\.pdf.*$', '', name, flags=re.I).strip()
            pdfs.append(ListingItem(title, urljoin(url, a['href'])))
        return pdfs

    def read_listings(self):
        items = {}
        for start in self.listing_urls:
            try:
                r = self.fetch(start)
                for item in self.parse_listing(r.text, r.url):
                    items[item.url] = item
                soup = self.soup(r.text)
                categories = soup.select('h2 a.my-arrows-link[href]')
                # Follow current links, despite legacy years in their URL slugs.
                links = list(dict.fromkeys(urljoin(r.url, a['href'].strip()) for a in categories))
                for link in links:
                    detail = self.fetch(link)
                    for item in self.parse_listing(detail.text, detail.url):
                        items[item.url] = item
                if not items and not categories and 'band' not in soup.get_text().lower():
                    raise ValueError('Struttura Sardegna non riconosciuta')
            except Exception as exc:
                self.warnings.append(f'Sezione Sardegna non letta: {start}: {exc}')
        if not items:
            raise ValueError('Nessun documento di bando letto su Fondazione di Sardegna')
        return list(items.values())


    def make_grant(self, item, text=''):
        grant = super().make_grant(item, text)
        compact = self.clean_text(text)
        # Annual Sardegna calls express the closing date as "alle ore ... del ...".
        window = re.search(r'\balle\s+ore\s+\d{1,2}(?:[:.]\d{2})?\s+del\s+([^.;]{3,65})', compact, re.I)
        if window:
            closing = strict_date(window.group(1))
            if closing:
                grant.deadline = closing
        return grant


class OpenSocietyScraper(CatalogueScraper):
    source_name = 'Open Society Foundations'
    funder = source_name
    listing_urls = ['https://www.opensocietyfoundations.org/grants']

    def parse_listing(self, html, url):
        soup = self.soup(html)
        if not soup.select_one('h1.pageTitle') or 'Grants' not in text(soup, 'h1.pageTitle'):
            raise ValueError('Pagina grants OSF non riconosciuta')
        items = []
        for c in soup.select('a.a-grantsCard[href]'):
            subtitle = text(c, '.a-grantsCard__subtitle')
            # Fellowships for individual people do not fund Open Arms as an organisation.
            if 'fellowship' in subtitle.lower():
                continue
            info = text(c, '.a-grantsCard__footer')
            items.append(ListingItem(text(c, '.a-grantsCard__title'), urljoin(url, c['href']), text(c, 'p'),
                         deadline=deadline_from_text(info), closed=bool(re.search('passed|closed', info, re.I))))
        return items
