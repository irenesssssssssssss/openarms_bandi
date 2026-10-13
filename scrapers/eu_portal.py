"""Documented EU SEDIA search API, multipart JSON query, English topics only."""
from __future__ import annotations

import json
from datetime import date
from urllib.parse import urlparse

from config import EU_MAX_PAGES_PER_QUERY, EU_PAGE_SIZE
from models import ScrapedGrant
from scrapers.base import BaseScraper
from scrapers.catalogue import content_text


class EuPortalScraper(BaseScraper):
    source_name = 'EU Funding & Tenders'
    api_url = 'https://api.tech.ec.europa.eu/search-api/prod/rest/search'
    # Programme acronyms plus thematic searches. No claim of full portal coverage.
    search_terms = ['CERV', 'AMIF', 'ERASMUS', 'ESC', 'migration', 'human rights', 'social inclusion', 'rescue']

    @staticmethod
    def query(identifier=None):
        must = [{'terms': {'type': ['1']}}, {'term': {'language': 'en'}}]
        if identifier:
            must.append({'terms': {'identifier': [identifier]}})
        else:
            must.append({'terms': {'status': ['31094501', '31094502']}})
        return {'bool': {'must': must}}

    def search(self, term, page=1, identifier=None):
        r = self.fetch(self.api_url, method='POST',
            params={'apiKey': 'SEDIA', 'text': term, 'pageSize': EU_PAGE_SIZE, 'pageNumber': page},
            files={'query': ('query.json', json.dumps(self.query(identifier)), 'application/json')})
        result = json.loads(r.text)
        if not isinstance(result, dict) or not isinstance(result.get('results'), list) or 'totalResults' not in result:
            raise ValueError('Risposta API SEDIA non riconosciuta')
        return result

    @staticmethod
    def values(metadata, key):
        v = metadata.get(key, [])
        return v if isinstance(v, list) else [v]

    @classmethod
    def first(cls, metadata, key):
        values = cls.values(metadata, key)
        return str(values[0]) if values else ''

    def parse_result(self, row):
        m = row.get('metadata') or {}
        if self.first(m, 'type') != '1' or self.first(m, 'language') not in ('en', ''):
            return None
        identifier = self.first(m, 'identifier')
        if not identifier:
            return None
        title = content_text(self.first(m, 'title') or row.get('summary', ''))
        description = content_text(self.first(m, 'descriptionByte'))
        requirements = content_text(self.first(m, 'topicConditions'))
        dates = [self.parse_date(str(v)) for v in self.values(m, 'deadlineDate')]
        dates = [d for d in dates if d]
        future = [d for d in dates if d >= date.today()]
        deadline = min(future) if future else max(dates) if dates else None
        programme = identifier.split('-', 1)[0]
        labels = {'ERASMUS': 'Erasmus+', 'ESC': 'Corpo Europeo di Solidarietà', 'HORIZON': 'Horizon Europe'}
        return ScrapedGrant(
            source_name=self.source_name,
            source_url='https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/' + identifier,
            source_external_id=identifier, title=title or identifier,
            funder='Commissione europea', program=labels.get(programme, programme),
            description=description, requirements=requirements or 'Requisiti nella scheda ufficiale UE; non verificati automaticamente.',
            # Conditions are evidence, not a generic assumption that all NGOs qualify.
            eligible_entities=requirements[:12000],
            open_date=self.parse_date(self.first(m, 'startDate')),
            deadline=deadline, source_closed=self.first(m, 'status') == '31094503',
            official_url='https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/' + identifier,
            tags=[str(x) for x in self.values(m, 'tags') + self.values(m, 'keywords')],
            raw_text=description + '\n' + requirements,
        )

    def scrape(self, known_urls=None):
        rows = {}
        successes = 0
        for term in self.search_terms:
            try:
                for page in range(1, EU_MAX_PAGES_PER_QUERY + 1):
                    data = self.search(term, page)
                    successes += 1
                    for row in data['results']:
                        grant = self.parse_result(row)
                        if grant:
                            rows[grant.source_external_id] = grant
                    total = int(data['totalResults'])
                    if page * EU_PAGE_SIZE >= total:
                        break
                    if page == EU_MAX_PAGES_PER_QUERY:
                        self.warnings.append(f'Ricerca UE {term}: {total} risultati, letti fino a {page * EU_PAGE_SIZE}.')
            except Exception as exc:
                self.warnings.append(f'Ricerca UE {term} fallita: {exc}')
        if not successes:
            raise RuntimeError('Nessuna ricerca UE completata. ' + '; '.join(self.warnings))
        # Specific rechecks also retrieve closed topics and update previously stored calls.
        for url in known_urls or []:
            identifier = urlparse(url).path.rsplit('/', 1)[-1]
            if identifier in rows or '/topic-details/' not in url:
                continue
            try:
                data = self.search('', identifier=identifier)
                for row in data['results']:
                    grant = self.parse_result(row)
                    if grant:
                        rows[grant.source_external_id] = grant
            except Exception as exc:
                self.warnings.append(f'Ricontrollo UE {identifier} fallito: {exc}')
        return list(rows.values())
