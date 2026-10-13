"""Build the public site without importing the web server or its scheduler."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from config import BASE_DIR, DB_PATH
from database.repository import Repository, utcnow
from services.refresh import SCRAPERS, refresh_all
from services.source_policy import SOURCE_NOTES


def build_public(output: Path, repo: Repository) -> int:
    output.mkdir(parents=True, exist_ok=True)
    repo.recalculate_relevance()
    repo.mark_expired()
    # Explicit allowlist: never copy the repository, database or credentials.
    html = (BASE_DIR / 'frontend/index.html').read_text(encoding='utf-8')
    html = html.replace('href="/static/styles.css"', 'href="./styles.css"')
    html = html.replace('src="/static/app.js"', 'src="./app.js"')
    html = html.replace('<body>', '<body data-public="true">')
    html = html.replace('AGGIORNA ORA', 'RICARICA DATI')
    html = html.replace('Aggiornamento periodico.',
        'I bandi vengono aggiornati automaticamente ogni 6 ore circa. Ricarica dati mostra l’ultima versione pubblicata.')
    (output / 'index.html').write_text(html, encoding='utf-8')
    for asset in ('styles.css', 'app.js'):
        shutil.copyfile(BASE_DIR / 'frontend' / asset, output / asset)
    rows = repo.list_grants()
    statuses = {row['source_name']: row for row in repo.source_statuses()}
    payload = {
        'items': rows,
        'status': {
            'latest_refresh': repo.latest_refresh(),
            'sources': [{**statuses.get(cls.source_name, {
                'source_name': cls.source_name, 'status': 'DA CONTROLLARE',
                'message': '', 'items_seen': 0,
            }), 'eligibility_note': SOURCE_NOTES.get(cls.source_name, '')} for cls in SCRAPERS],
            'refresh_running': False,
            'google_sheets_enabled': False,
            'published_at': utcnow(),
        },
    }
    (output / 'data.json').write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
    (output / '.nojekyll').write_text('', encoding='utf-8')
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true', help='Fetch sources before exporting')
    parser.add_argument('--db', type=Path, default=DB_PATH)
    parser.add_argument('--output', type=Path, default=BASE_DIR / 'public-site')
    args = parser.parse_args()
    args.db.parent.mkdir(parents=True, exist_ok=True)
    repo = Repository(args.db)
    if args.refresh:
        summary = refresh_all(repo)
        if summary.status != 'ok':
            print(f'::warning::Aggiornamento fonti: {summary.status}')
        if summary.status == 'error':
            raise RuntimeError('Tutte le fonti sono fallite: mantengo il sito già pubblicato.')
    count = build_public(args.output, repo)
    print(f'Sito generato in {args.output}: {count} bandi.')


if __name__ == '__main__':
    main()
