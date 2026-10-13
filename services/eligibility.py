from __future__ import annotations

import re
from dataclasses import dataclass

from config import OPEN_ARMS_ASSOCIATION_REGISTER, OPEN_ARMS_RUNTS
from models import ScrapedGrant
from services.relevance import norm


@dataclass
class EligibilityResult:
    status: str
    reasons: list[str]


EXCLUSIVE_INCOMPATIBLE = [
    "esclusivamente comuni", "solo comuni", "istituzioni scolastiche in qualita di capofila",
    "diocesi", "istituti religiosi", "societa di vita apostolica", "imprese agricole",
    "micro piccole e medie imprese", "artisti", "ricercatori individuali",
]
NONPROFIT_SIGNALS = [
    "enti del terzo settore", "ets", "organizzazioni di volontariato", "odv",
    "associazioni di promozione sociale", "aps", "ong", "organizzazioni non profit",
    "associazioni", "fondazioni", "organismi senza fini di lucro", "imprese sociali",
    "enti senza fini di lucro", "non profit", "non-profit", "nonprofit",
    "civil society organisations", "civil society organizations", "ngos",
]


def nonprofit_signals(text: str) -> list[str]:
    return [s for s in NONPROFIT_SIGNALS if re.search(r"\b" + re.escape(norm(s)) + r"\b", text)]


def evaluate_eligibility(g: ScrapedGrant) -> EligibilityResult:
    text = norm(" ".join([
        g.eligible_entities, g.requirements, g.territory, g.partners_required,
        g.description, g.objectives,
    ]))
    reasons: list[str] = []

    aics = g.source_name == "AICS" or "agenzia italiana per la cooperazione allo sviluppo" in norm(g.funder)
    if aics:
        reasons.append("Per i bandi AICS destinati alle OSC, Elenco OSC richiesto come proponente/capofila: verificare iscrizione di Open Arms e ruolo nel bando")

    if not text.strip() or len(g.eligible_entities.strip()) < 3:
        return EligibilityResult("Da verificare", reasons + ["La fonte pubblica non espone abbastanza requisiti di ammissibilità"])

    # Se la scheda dice esplicitamente che gli ETS/ONG possono essere partner, non è una esclusione.
    partner_only = any(k in text for k in ["in qualita di partner", "ammessi come partner", "partner possono essere"])
    nonprofit = nonprofit_signals(text)

    # Public-only applicants stay distinct from the people/associations served by a project.
    applicants = norm(g.eligible_entities)
    if (re.search(r"\b(?:comuni|amministrazioni pubbliche|enti locali|ambiti territoriali sociali|universita)\b", applicants)
            and not nonprofit_signals(applicants) and not partner_only):
        return EligibilityResult("Probabilmente non ammissibile", ["La scheda indica soggetti pubblici come candidati; non risulta ammesso un ETS come proponente"])

    incompatible = [s for s in EXCLUSIVE_INCOMPATIBLE if norm(s) in text]
    if incompatible and not nonprofit and not partner_only:
        return EligibilityResult(
            "Probabilmente non ammissibile",
            ["I soggetti ammessi sembrano limitati a categorie diverse da un ente non profit/ETS"],
        )

    specific_conditions = []
    if aics:
        specific_conditions.extend(reasons)
        reasons.clear()
    elif "elenco aics" in text or "iscritt" in text and "aics" in text:
        specific_conditions.append("Iscrizione/accreditamento AICS da verificare")
    if re.search(r"entrate annue|bilancio|costituite da almeno|anzianita|annual (?:income|turnover)|legal entit|associated countr", text):
        specific_conditions.append("Vincoli economici, di anzianità o giuridici da verificare nel bando")
    if g.source_name == "EU Funding & Tenders":
        specific_conditions.append("Ammissibilità UE, paesi e consorzio da verificare nella documentazione ufficiale")
    reasons.extend(specific_conditions)
    if nonprofit:
        reasons.append("La scheda ammette soggetti del Terzo Settore/non profit")

    if "runts" in text:
        if OPEN_ARMS_RUNTS == "no":
            return EligibilityResult("Probabilmente non ammissibile", ["È richiesta iscrizione RUNTS e la configurazione indica OPEN_ARMS_RUNTS=no"])
        if OPEN_ARMS_RUNTS == "unknown":
            reasons.append("È richiesta/menzionata iscrizione RUNTS: verificare lo status di Open Arms Italia")

    if "registro delle associazioni e degli enti che svolgono attivita a favore degli immigrati" in text:
        if OPEN_ARMS_ASSOCIATION_REGISTER == "no":
            return EligibilityResult("Probabilmente non ammissibile", ["È richiesta iscrizione allo specifico registro immigrazione e la configurazione indica no"])
        if OPEN_ARMS_ASSOCIATION_REGISTER == "unknown":
            reasons.append("È richiesta iscrizione a uno specifico registro per enti attivi nell'immigrazione")

    territorial_cues = re.findall(r"\b(lazio|toscana|piemonte|lombardia|sicilia|sardegna|campania|puglia|calabria|molise|basilicata|veneto|liguria|umbria|marche|abruzzo|friuli|valle d.?aosta|trentino)\b", text)
    if territorial_cues:
        reasons.append("Sono presenti vincoli territoriali da verificare: " + ", ".join(sorted(set(territorial_cues))[:5]))

    if g.partners_required == "Sì":
        reasons.append("Partenariato/ATS obbligatorio")
    elif g.partners_required == "Da verificare":
        reasons.append("La scheda menziona partner/partenariato")

    if partner_only:
        reasons.append("Open Arms potrebbe essere ammissibile solo come partner, non necessariamente come capofila")
        return EligibilityResult("Da verificare", reasons)

    if specific_conditions:
        return EligibilityResult("Da verificare", reasons)

    if nonprofit:
        if "runts" in text and OPEN_ARMS_RUNTS == "unknown":
            return EligibilityResult("Da verificare", reasons)
        if territorial_cues:
            return EligibilityResult("Da verificare", reasons)
        return EligibilityResult("Probabilmente ammissibile", reasons or ["Categorie ammesse compatibili con un ente non profit"])

    return EligibilityResult("Da verificare", reasons or ["Requisiti non sufficienti per una conclusione affidabile"])
