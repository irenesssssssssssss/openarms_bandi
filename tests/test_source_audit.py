import pytest

from database.repository import Repository
from models import ScrapedGrant
from services.eligibility import evaluate_eligibility
from services.relevance import score_grant
from services import refresh
from services.source_policy import is_excluded_grant
from scrapers.base import BaseScraper


def grant(**kwargs):
    values = dict(source_name="Infobandi", source_url="https://example.test/call",
                  source_external_id="1", title="Formazione al soccorso in acqua",
                  eligible_entities="Enti del Terzo Settore", territory="Italia")
    values.update(kwargs)
    return ScrapedGrant(**values)


def save(repo, g):
    r, e = score_grant(g), evaluate_eligibility(g)
    return repo.upsert_grant(g, r.score, r.level, r.reasons, r.category, e.status, e.reasons)


@pytest.mark.parametrize("identity", [
    {"funder": "Consiglio d’Europa – European Youth Foundation"},
    {"title": "Call EYF 2027.C1"},
    {"program": "Fondazione europea per la gioventù"},
    {"official_url": "https://www.coe.int/en/web/european-youth-foundation/calls"},
])
def test_eyf_excluded_across_aggregators(identity):
    assert is_excluded_grant(grant(**identity))


def test_incidental_eyf_mention_does_not_exclude_other_funders():
    assert not is_excluded_grant(grant(description="In passato abbiamo partecipato a EYF",
                                       funder="Fondazione di Sardegna"))


def test_existing_cache_hides_eyf_without_deleting_history(tmp_path):
    repo = Repository(tmp_path / "data.sqlite3")
    a = save(repo, grant(source_name="European Youth Foundation"))
    b = save(repo, grant(title="Educazione ai diritti umani", source_external_id="2",
                         funder="European Youth Foundation"))
    save(repo, grant(title="Nuoto per inclusione sociale", source_external_id="3"))
    with repo.conn() as c:
        c.execute("INSERT INTO grant_history(grant_id,changed_at,field_name,old_value,new_value) VALUES(?,?,?,?,?)",
                  (a, "2026-10-09", "amount_available", "", "1000"))
    for include_irrelevant in (False, True):
        assert {g["id"] for g in repo.list_grants(include_irrelevant)}.isdisjoint({a, b})
        assert len(repo.list_grants(include_irrelevant)) == 1
    with repo.conn() as c:
        assert c.execute("SELECT COUNT(*) FROM grants").fetchone()[0] == 3
    assert len(repo.history(a)) == 1


def test_mixed_references_keep_non_eyf_grant(tmp_path):
    repo = Repository(tmp_path / "data.sqlite3")
    g = grant(funder="Fondazione di Sardegna")
    identifier = save(repo, g)
    # Simulate an erroneous historical EYF source attachment to a different grant.
    with repo.conn() as c:
        c.execute("INSERT INTO grant_sources(grant_id,source_name,source_url,source_external_id,last_seen_at) VALUES(?,?,?,?,?)",
                  (identifier, "European Youth Foundation", "https://example.test/old", "old", "2026-10-09"))
    items = repo.list_grants(True)
    assert len(items) == 1 and [s["source_name"] for s in items[0]["sources"]] == ["Infobandi"]


def test_refresh_does_not_save_eyf_from_aggregator(tmp_path, monkeypatch):
    class Aggregator(BaseScraper):
        source_name = "Infobandi"
        def scrape(self, known_urls=None):
            return [grant(funder="EYF"), grant(title="Inclusione sociale", source_external_id="2")]
    monkeypatch.setattr(refresh, "SCRAPERS", [Aggregator])
    repo = Repository(tmp_path / "data.sqlite3")
    result = refresh.refresh_all(repo)
    assert result.total_items == 1 and len(repo.list_grants(True)) == 1


def test_aics_registration_check_survives_sparse_cache(tmp_path):
    repo = Repository(tmp_path / "data.sqlite3")
    identifier = save(repo, grant(source_name="AICS"))
    with repo.conn() as c:
        c.execute("UPDATE grants SET eligibility_status='Probabilmente ammissibile',eligibility_reasons='[]' WHERE id=?", (identifier,))
    item = repo.list_grants(True)[0]
    assert item["eligibility_status"] == "Da verificare"
    assert any("Elenco OSC" in reason and "capofila" in reason for reason in item["eligibility_reasons"])
    sparse = evaluate_eligibility(grant(source_name="AICS", eligible_entities=""))
    assert any("Elenco OSC" in reason for reason in sparse.reasons)


def test_pn_public_applicants_distinct_from_nonprofit_beneficiaries():
    result = evaluate_eligibility(grant(source_name="PN Inclusione",
        eligible_entities="Ambiti territoriali sociali e Comuni",
        description="Inclusione sociale con associazioni e volontariato"))
    assert result.status == "Probabilmente non ammissibile"
    assert evaluate_eligibility(grant(source_name="PN Inclusione")).status == "Probabilmente ammissibile"
    assert evaluate_eligibility(grant(source_name="PN Inclusione",
        eligible_entities="Comuni capofila, ETS ammessi come partner")).status == "Da verificare"


def test_unipolis_age_of_organisation_is_not_youth_governance():
    result = evaluate_eligibility(grant(source_name="Fondazione Unipolis",
        eligible_entities="Organizzazioni non profit giovani",
        requirements="Entrate annue fino a 500.000 euro; costituite da almeno 2 e non più di 10 anni"))
    assert result.status == "Da verificare"
    assert any("anzianità" in reason for reason in result.reasons)
    assert all("giovanile" not in reason for reason in result.reasons)


def test_api_and_dashboard_have_thirteen_sources_no_manual_import(tmp_path, monkeypatch):
    import app
    from fastapi.testclient import TestClient
    repo = Repository(tmp_path / "data.sqlite3")
    repo.update_source_status("European Youth Foundation", "ERRORE", "old 403", 0)
    save(repo, grant(source_name="European Youth Foundation"))
    monkeypatch.setattr(app, "repo", repo)
    monkeypatch.setattr(app, "REFRESH_ON_STARTUP", False)
    with TestClient(app.app) as client:
        status = client.get("/api/status").json()
        assert len(status["sources"]) == 13
        assert all(s["source_name"] != "European Youth Foundation" and s["eligibility_note"] for s in status["sources"])
        assert client.get("/api/grants").json()["items"] == []
        assert "eyfImportPanel" not in client.get("/").text
        assert client.post("/api/sources/eyf/import-html", content="unused").status_code == 404
        captured = []
        monkeypatch.setattr(app, "GOOGLE_SHEETS_ENABLED", True)
        monkeypatch.setattr(app, "sync_to_google_sheet", lambda items: captured.extend(items) or len(items))
        assert client.post("/api/google-sheets/sync").json()["rows"] == 0
        assert captured == []
