from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlsplit, urlunsplit

from rapidfuzz.fuzz import ratio


def normalize_title(title: str) -> str:
    s = unicodedata.normalize("NFKD", title or "").encode("ascii", "ignore").decode("ascii").lower()
    s = re.sub(r"\b(bando|avviso|call|202[0-9]|scadenza|prorogat[oa])\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def normalize_url(url: str) -> str:
    if not url:
        return ""
    try:
        p = urlsplit(url)
        path = p.path.rstrip("/")
        return urlunsplit((p.scheme.lower(), p.netloc.lower().replace("www.", ""), path, "", ""))
    except Exception:
        return url.strip().lower()


def duplicate_score(existing: dict, candidate: dict) -> int:
    e_off = normalize_url(existing.get("official_url", ""))
    c_off = normalize_url(candidate.get("official_url", ""))
    if e_off and c_off and e_off == c_off:
        return 100

    # Separate annual editions and distinct official EU topics/EYF call identifiers.
    raw_e, raw_c = existing.get("title", ""), candidate.get("title", "")
    years_e = set(re.findall(r"\b20\d{2}\b", raw_e))
    years_c = set(re.findall(r"\b20\d{2}\b", raw_c))
    if years_e and years_c and years_e.isdisjoint(years_c):
        return 0
    code_e = re.search(r"\b\d{4}\.C\d+\.[A-Z]\b", raw_e)
    code_c = re.search(r"\b\d{4}\.C\d+\.[A-Z]\b", raw_c)
    if code_e and code_c and code_e.group(0) != code_c.group(0):
        return 0
    if '/topic-details/' in e_off and '/topic-details/' in c_off and e_off != c_off:
        return 0

    et = normalize_title(existing.get("title", ""))
    ct = normalize_title(candidate.get("title", ""))
    if not et or not ct:
        return 0
    title_score = ratio(et, ct)

    ed = existing.get("deadline") or ""
    cd = candidate.get("deadline") or ""
    deadline_bonus = 10 if ed and cd and str(ed) == str(cd) else 0

    ef = normalize_title(existing.get("funder", ""))
    cf = normalize_title(candidate.get("funder", ""))
    funder_bonus = 8 if ef and cf and ratio(ef, cf) >= 80 else 0

    score = min(100, round(title_score * 0.82 + deadline_bonus + funder_bonus))
    return score


def find_duplicate(existing_grants: list[dict], candidate: dict, threshold: int = 88) -> dict | None:
    best = None
    best_score = 0
    for item in existing_grants:
        s = duplicate_score(item, candidate)
        if s > best_score:
            best, best_score = item, s
    return best if best is not None and best_score >= threshold else None
