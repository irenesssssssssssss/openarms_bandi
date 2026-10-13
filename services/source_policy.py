"""Source decisions from the 2026-10-09 applicant eligibility audit."""
from __future__ import annotations

import re
from collections.abc import Mapping

from services.relevance import norm


SOURCE_NOTES = {
    "CSV Lazio": "Portale misto: verificare i soggetti ammessi nel singolo bando.",
    "Infobandi": "Portale per volontariato e Terzo Settore: requisiti specifici per bando.",
    "ConfiniOnline": "Portale non profit: verificare ruolo di capofila/partner e requisiti nel bando.",
    "EU Funding & Tenders": "Sono presenti opportunità per società civile/non profit; paesi, programma e consorzio da verificare.",
    "Integrazione Migranti": "Portale misto: destinatari del progetto e soggetti che possono candidarsi sono distinti.",
    "PN Inclusione": "Include avvisi per ETS e avvisi per amministrazioni/ambiti territoriali: verificare il singolo avviso.",
    "Ministero Lavoro – Terzo Settore": "Include avvisi per ODV, APS e fondazioni ETS; forma giuridica e registri da verificare.",
    "AICS": "Elenco OSC richiesto come proponente/capofila dei bandi per OSC; requisiti dei partner da verificare separatamente.",
    "Fondazione CON IL SUD": "Opportunità per ETS nel Sud, inclusa la Sardegna; territorio, capofila e partenariato dipendono dal bando.",
    "Fondazione di Sardegna": "Ammessi anche non profit con sede fuori regione per progetti prevalentemente in Sardegna o a beneficio delle comunità sarde, secondo il bando.",
    "Fondazione Unipolis": "ACT include ETS; POP 2026 richiede enti costituiti da 2–10 anni ed entrate fino a 500.000 euro. Giovane riguarda l'ente, non i membri.",
    "Compagnia di San Paolo": "Opportunità per non profit; territorio del progetto, sede del capofila e cofinanziamento dipendono dal bando.",
    "Open Society Foundations": "Finanzia anche organizzazioni; molti contributi sono su invito. Qui si controllano soltanto call pubbliche per enti.",
}


def is_excluded_source(name: str) -> bool:
    return norm(name) in {"european youth foundation", "eyf"}


def is_excluded_grant(grant) -> bool:
    """Exclude EYF across sources, avoiding matches to incidental mentions in descriptions."""
    def field(key):
        return (grant.get(key, "") if isinstance(grant, Mapping) else getattr(grant, key, "")) or ""

    identity = norm(" ".join(field(key) for key in ("funder", "program", "title")))
    official = field("official_url").lower()
    return (is_excluded_source(field("source_name"))
            or bool(re.search(r"\beyf\b|european youth foundation|fondazione europea (?:per |della |dei |per la )?(?:gioventu|giovani)", identity))
            or "/european-youth-foundation/" in official)
