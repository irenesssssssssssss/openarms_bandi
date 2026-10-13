from datetime import date

from models import ScrapedGrant
from services.deduplication import duplicate_score
from services.eligibility import evaluate_eligibility
from services.relevance import score_grant


def grant(**kwargs):
    base = dict(
        source_name="test", source_url="https://example.test/x", source_external_id="x",
        title="Bando per integrazione di migranti nelle scuole",
        objectives="Integrazione scolastica di studenti di Paesi terzi e sensibilizzazione",
        activities="Formazione e attività educative con associazioni del Terzo Settore",
        beneficiaries="Studenti migranti e famiglie",
        eligible_entities="Enti del Terzo Settore e associazioni",
        territory="Italia",
        deadline=date(2027, 1, 1),
    )
    base.update(kwargs)
    return ScrapedGrant(**base)


def test_relevance_is_high_for_migration_education():
    r = score_grant(grant())
    assert r.level in {"ALTA", "MEDIA"}
    assert r.score >= 25


def test_eligibility_nonprofit_signal():
    e = evaluate_eligibility(grant())
    assert e.status in {"Probabilmente ammissibile", "Da verificare"}


def test_dedup_same_title_deadline():
    a = {"title": "Bando integrazione migranti 2026", "funder": "Ministero", "deadline": "2026-12-01", "official_url": ""}
    b = {"title": "Bando per integrazione migranti", "funder": "Ministero", "deadline": "2026-12-01", "official_url": ""}
    assert duplicate_score(a, b) >= 80
