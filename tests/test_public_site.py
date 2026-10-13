import json

import pytest

from build_public import build_public
from database.repository import Repository
from models import ScrapedGrant


@pytest.mark.parametrize('populated', [False, True])
def test_public_export_is_self_contained_and_excludes_database(tmp_path, populated):
    repo = Repository(tmp_path / 'private.sqlite3')
    if populated:
        grant = ScrapedGrant(source_name='test', source_url='https://example.org',
            source_external_id='1', title='Soccorso in mare e assistenza umanitaria')
        repo.upsert_grant(grant, 90, 'ALTA', ['Soccorso'], 'Soccorso & Emergenze',
            'Da verificare', [])
    output = tmp_path / 'site'
    count = build_public(output, repo)
    assert count == int(populated)
    assert {p.name for p in output.iterdir()} == {
        'index.html', 'styles.css', 'app.js', 'data.json', '.nojekyll'}
    html = (output / 'index.html').read_text(encoding='utf-8')
    assert 'data-public="true"' in html
    assert 'href="./styles.css"' in html and 'src="./app.js"' in html
    assert '/static/' not in html
    payload = json.loads((output / 'data.json').read_text(encoding='utf-8'))
    assert len(payload['items']) == count
    assert payload['status']['google_sheets_enabled'] is False
    assert payload['status']['refresh_running'] is False
