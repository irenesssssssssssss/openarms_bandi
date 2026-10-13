from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from config import REFRESH_MAX_WORKERS
from database.repository import Repository
from scrapers.confinionline import ConfiniOnlineScraper
from scrapers.csv_lazio import CsvLazioScraper
from scrapers.infobandi import InfobandiScraper
from scrapers.eu_portal import EuPortalScraper
from scrapers.official_sources import (IntegrazioneMigrantiScraper, PnInclusioneScraper,
    MinisteroLavoroScraper, AicsScraper, ConIlSudScraper, SardegnaScraper,
    UnipolisScraper, SanPaoloScraper, OpenSocietyScraper)
from services.eligibility import evaluate_eligibility
from services.relevance import score_grant
from services.source_policy import is_excluded_grant

log = logging.getLogger(__name__)
_refresh_lock = threading.Lock()


@dataclass
class RefreshSummary:
    status: str
    sources: dict[str, dict]
    total_items: int


# Three original sources + ten approved sources after the eligibility audit.
SCRAPERS = [CsvLazioScraper, InfobandiScraper, ConfiniOnlineScraper, EuPortalScraper,
    IntegrazioneMigrantiScraper, PnInclusioneScraper, MinisteroLavoroScraper,
    AicsScraper, ConIlSudScraper, SardegnaScraper, UnipolisScraper,
    SanPaoloScraper, OpenSocietyScraper]


def refresh_is_running():
    return _refresh_lock.locked()


def _read_source(scraper_cls, known_urls):
    scraper = scraper_cls()
    try:
        grants = scraper.scrape(known_urls=known_urls)
        return grants, list(dict.fromkeys(scraper.warnings))
    finally:
        scraper.close()


def refresh_all(repo=None):
    repo = repo or Repository()
    if not _refresh_lock.acquire(blocking=False):
        return RefreshSummary('busy', {}, 0)
    run_id = None
    source_results = {}
    total = 0
    try:
        run_id = repo.start_refresh()
        with ThreadPoolExecutor(max_workers=REFRESH_MAX_WORKERS) as executor:
            futures = {}
            for cls in SCRAPERS:
                name = cls.source_name
                repo.update_source_status(name, 'IN CORSO', '', 0)
                futures[executor.submit(_read_source, cls, repo.active_source_urls(name))] = name
            for future in as_completed(futures):
                name = futures[future]
                count = 0
                try:
                    grants, warnings = future.result()
                    for grant in grants:
                        if is_excluded_grant(grant):
                            continue
                        rel = score_grant(grant)
                        elig = evaluate_eligibility(grant)
                        repo.upsert_grant(grant, relevance_score=rel.score, relevance_level=rel.level,
                            relevance_reasons=rel.reasons, category=rel.category,
                            eligibility_status=elig.status, eligibility_reasons=elig.reasons)
                        count += 1
                    status = 'PARZIALE' if warnings else 'OK'
                    message = '; '.join(warnings) or ('Nessun bando per organizzazioni nell’elenco pubblico.' if not count else '')
                    total += count
                except Exception as exc:
                    log.exception('Fonte %s fallita', name)
                    status, message = 'ERRORE', f'{type(exc).__name__}: {exc}'
                repo.update_source_status(name, status, message, count)
                source_results[name] = {'status': status, 'items': count, 'message': message}
        repo.mark_expired()
        statuses = [r['status'] for r in source_results.values()]
        overall = 'ok' if all(s == 'OK' for s in statuses) else 'error' if all(s == 'ERRORE' for s in statuses) else 'partial'
        repo.finish_refresh(run_id, overall, f'Totale record osservati: {total}')
        return RefreshSummary(overall, source_results, total)
    except Exception as exc:
        if run_id:
            repo.finish_refresh(run_id, 'error', str(exc))
        raise
    finally:
        _refresh_lock.release()
