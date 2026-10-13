import json
import sqlite3

import pytest

from database.repository import Repository
from models import ScrapedGrant
from services.relevance import score_grant


def grant(title="Bando progetti", **kwargs):
    return ScrapedGrant("test", "https://example.test/social", "social", title, **kwargs)


@pytest.mark.parametrize("g,category", [
    (grant("Sport per l'inclusione sociale"), "Sport & Inclusione"),
    (grant("Attività sportive", objectives="Contrastare l'isolamento sociale"), "Sport & Inclusione"),
    (grant(activities="Nuoto adattato", beneficiaries="Persone con disabilità"), "Sport & Inclusione"),
    (grant("Sport e coesione sociale"), "Sport & Inclusione"),
    (grant("Attività fisiche per la coesione sociale"), "Sport & Inclusione"),
    (grant("Musica e integrazione"), "Cultura & Inclusione"),
    (grant("Attività culturali per la coesione sociale"), "Cultura & Inclusione"),
    (grant(activities="Teatro e lettura", objectives="Contrasto alla povertà educativa"), "Cultura & Inclusione"),
    (grant("Danza accessibile", objectives="Promuovere l'accessibilità"), "Cultura & Inclusione"),
    (grant("Music for social inclusion"), "Cultura & Inclusione"),
    (grant("Biblioteche per il benessere della comunità"), "Cultura & Inclusione"),
    (grant("Musica solidale"), "Cultura & Inclusione"),
    (grant(activities="Laboratori educativi di musica", beneficiaries="Bambini e famiglie"), "Cultura & Inclusione"),
    (grant(description="Attività sportive per la partecipazione civica."), "Sport & Inclusione"),
])
def test_social_activities_receive_contextual_bonus(g, category):
    result = score_grant(g)
    assert result.score >= 25
    assert result.category == category
    assert any(reason.startswith("Regola: ") for reason in result.reasons)


@pytest.mark.parametrize("g", [
    grant("Campionato sportivo agonistico"),
    grant("Festival di musica e spettacolo dal vivo"),
    grant("Restauro del patrimonio culturale"),
    grant("Corso di formazione musicale per giovani professionisti"),
    grant("Ristrutturazione impianti sportivi", eligible_entities="ETS, associazioni per l'inclusione sociale"),
    grant("Festival musicale", category="Inclusione sociale", tags=["social inclusion"]),
    grant(description="Finanziamenti per lo sport agonistico. " + "Regole di rendicontazione. " * 50 + "Inclusione sociale."),
    grant("Ricerca sulla gestione delle acque"),
])
def test_unrelated_activities_do_not_receive_contextual_bonus(g):
    result = score_grant(g)
    assert result.score < 25
    assert not any(reason.startswith("Regola: ") for reason in result.reasons)


@pytest.mark.parametrize("title", [
    "Corso di soccorso in acqua",
    "Formazione al salvataggio acquatico",
    "Formazione per la prevenzione dell'annegamento",
    "Formazione per la prevenzione dell’annegamento",
    "Water rescue training",
    "Drowning prevention training",
])
def test_water_rescue_training_is_high_without_migration_terms(title):
    result = score_grant(grant(title))
    assert result.level == "ALTA"
    assert result.category == "Soccorso & Emergenze"
    assert any("formazione / addestramento" in reason for reason in result.reasons)


def test_context_bonus_is_not_multiplied_by_synonyms_or_repeated_fields():
    short = score_grant(grant("Arte e coesione sociale"))
    repeated = score_grant(grant("Arte, musica, teatro, danza e coesione sociale",
                                activities="Arte, musica, teatro, danza e coesione sociale"))
    assert short.score == repeated.score == 25


def test_cached_grants_are_rescored_without_changing_eligibility_or_source_data(tmp_path):
    path = tmp_path / "existing.sqlite3"
    repo = Repository(path)
    g = grant("Attività culturali per la coesione sociale")
    record_id = repo.upsert_grant(g, 0, "IRRILEVANTE", [], "Altro",
                                 "Da verificare", ["Verificare territorio e requisiti"])
    with repo.conn() as c:
        before = dict(c.execute("SELECT * FROM grants WHERE id=?", (record_id,)).fetchone())
        sources = [tuple(row) for row in c.execute("SELECT * FROM grant_sources")]
    # Simula il database di una versione senza la colonna dei tag.
    with sqlite3.connect(path) as c:
        c.execute("ALTER TABLE grants DROP COLUMN tags")
    repo = Repository(path)
    assert repo.recalculate_relevance() == 1
    assert repo.recalculate_relevance() == 0
    with repo.conn() as c:
        after = dict(c.execute("SELECT * FROM grants WHERE id=?", (record_id,)).fetchone())
        assert sources == [tuple(row) for row in c.execute("SELECT * FROM grant_sources")]
    assert after["relevance_score"] == 25
    assert after["category"] == "Cultura & Inclusione"
    for key in before.keys() - {"category", "relevance_score", "relevance_level", "relevance_reasons", "tags"}:
        assert after[key] == before[key]


def test_rescore_preserves_tags_and_does_not_feed_categories_back_into_score(tmp_path):
    repo = Repository(tmp_path / "tags.sqlite3")
    g = grant("Attività culturali per la coesione sociale", tags=["volontariato"])
    result = score_grant(g)
    record_id = repo.upsert_grant(g, result.score, result.level, result.reasons, result.category,
                                 "Da verificare", [])
    assert repo.recalculate_relevance() == 0
    sparse = grant("Attività culturali per la coesione sociale")
    repo.upsert_grant(sparse, 25, "MEDIA", [], "Cultura & Inclusione", "Da verificare", [])
    assert repo.recalculate_relevance() == 0
    with repo.conn() as c:
        row = c.execute("SELECT * FROM grants WHERE id=?", (record_id,)).fetchone()
        assert json.loads(row["tags"]) == ["volontariato"]
        assert row["relevance_score"] == result.score
