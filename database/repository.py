from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from config import DB_PATH
from models import ScrapedGrant
from services.deduplication import find_duplicate, normalize_title
from services.source_policy import is_excluded_grant, is_excluded_source, SOURCE_NOTES


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Repository:
    def __init__(self, path: Path | str = DB_PATH):
        self.path = str(path)
        self.init_db()

    @contextmanager
    def conn(self):
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def init_db(self) -> None:
        with self.conn() as c:
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS grants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    canonical_key TEXT NOT NULL,
                    title TEXT NOT NULL,
                    funder TEXT DEFAULT '',
                    category TEXT DEFAULT '',
                    description TEXT DEFAULT '',
                    objectives TEXT DEFAULT '',
                    activities TEXT DEFAULT '',
                    beneficiaries TEXT DEFAULT '',
                    eligible_entities TEXT DEFAULT '',
                    territory TEXT DEFAULT '',
                    partners_required TEXT DEFAULT '',
                    amount_available TEXT DEFAULT '',
                    cofinancing TEXT DEFAULT '',
                    open_date TEXT,
                    deadline TEXT,
                    official_url TEXT DEFAULT '',
                    requirements TEXT DEFAULT '',
                    relevance_score INTEGER DEFAULT 0,
                    relevance_level TEXT DEFAULT 'IRRILEVANTE',
                    relevance_reasons TEXT DEFAULT '[]',
                    eligibility_status TEXT DEFAULT 'Da verificare',
                    eligibility_reasons TEXT DEFAULT '[]',
                    expired INTEGER DEFAULT 0,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_grants_deadline ON grants(deadline);
                CREATE INDEX IF NOT EXISTS idx_grants_relevance ON grants(relevance_level, relevance_score);
                CREATE INDEX IF NOT EXISTS idx_grants_canonical ON grants(canonical_key);

                CREATE TABLE IF NOT EXISTS grant_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    grant_id INTEGER NOT NULL REFERENCES grants(id) ON DELETE CASCADE,
                    source_name TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    source_external_id TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    UNIQUE(source_name, source_external_id)
                );
                CREATE INDEX IF NOT EXISTS idx_sources_grant ON grant_sources(grant_id);

                CREATE TABLE IF NOT EXISTS grant_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    grant_id INTEGER NOT NULL REFERENCES grants(id) ON DELETE CASCADE,
                    changed_at TEXT NOT NULL,
                    field_name TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT
                );

                CREATE TABLE IF NOT EXISTS source_status (
                    source_name TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    message TEXT DEFAULT '',
                    last_checked_at TEXT NOT NULL,
                    items_seen INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS refresh_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    status TEXT NOT NULL,
                    message TEXT DEFAULT ''
                );
                """
            )

            # Backward-compatible schema migration; preserve the existing SQLite database.
            columns = {row[1] for row in c.execute("PRAGMA table_info(grants)")}
            if "program" not in columns:
                c.execute("ALTER TABLE grants ADD COLUMN program TEXT DEFAULT ''")
            if "source_closed" not in columns:
                c.execute("ALTER TABLE grants ADD COLUMN source_closed INTEGER DEFAULT 0")
            if "tags" not in columns:
                c.execute("ALTER TABLE grants ADD COLUMN tags TEXT DEFAULT '[]'")

    def recalculate_relevance(self) -> int:
        """Apply current rules to the cache without fetching sources or changing eligibility."""
        from services.relevance import score_grant

        changed = 0
        with self.conn() as c:
            for row in c.execute("SELECT * FROM grants").fetchall():
                evidence = {key: row[key] or "" for key in (
                    "title", "category", "description", "objectives", "activities",
                    "beneficiaries", "eligible_entities", "territory",
                )}
                grant = ScrapedGrant(source_name="cache", source_url="",
                    source_external_id=str(row["id"]), tags=json.loads(row["tags"] or "[]"), **evidence)
                result = score_grant(grant)
                reasons = json.dumps(result.reasons, ensure_ascii=False)
                values = (result.score, result.level, reasons, result.category)
                previous = tuple(row[key] for key in (
                    "relevance_score", "relevance_level", "relevance_reasons", "category"))
                if values != previous:
                    c.execute("UPDATE grants SET relevance_score=?,relevance_level=?,relevance_reasons=?,category=? WHERE id=?",
                              (*values, row["id"]))
                    changed += 1
        return changed

    def start_refresh(self) -> int:
        with self.conn() as c:
            cur = c.execute(
                "INSERT INTO refresh_runs(started_at,status,message) VALUES(?,?,?)",
                (utcnow(), "running", ""),
            )
            return int(cur.lastrowid)

    def finish_refresh(self, run_id: int, status: str, message: str = "") -> None:
        with self.conn() as c:
            c.execute(
                "UPDATE refresh_runs SET finished_at=?,status=?,message=? WHERE id=?",
                (utcnow(), status, message[:2000], run_id),
            )

    def update_source_status(self, source_name: str, status: str, message: str, items_seen: int) -> None:
        with self.conn() as c:
            c.execute(
                """
                INSERT INTO source_status(source_name,status,message,last_checked_at,items_seen)
                VALUES(?,?,?,?,?)
                ON CONFLICT(source_name) DO UPDATE SET
                    status=excluded.status,
                    message=excluded.message,
                    last_checked_at=excluded.last_checked_at,
                    items_seen=excluded.items_seen
                """,
                (source_name, status, message[:1000], utcnow(), items_seen),
            )


    def active_source_urls(self, source_name: str) -> list[str]:
        with self.conn() as c:
            rows = c.execute(
                """
                SELECT DISTINCT gs.source_url
                FROM grant_sources gs
                JOIN grants g ON g.id = gs.grant_id
                WHERE gs.source_name=? AND g.expired=0
                """,
                (source_name,),
            ).fetchall()
            return [r[0] for r in rows if r[0]]

    def source_statuses(self) -> list[dict[str, Any]]:
        with self.conn() as c:
            rows = c.execute("SELECT * FROM source_status ORDER BY source_name").fetchall()
            return [dict(r) for r in rows]

    def latest_refresh(self) -> dict | None:
        with self.conn() as c:
            r = c.execute("SELECT * FROM refresh_runs ORDER BY id DESC LIMIT 1").fetchone()
            return dict(r) if r else None

    def _grant_rows_for_dedup(self, c: sqlite3.Connection) -> list[dict]:
        rows = c.execute("SELECT id,title,funder,deadline,official_url FROM grants").fetchall()
        return [dict(r) for r in rows]

    def _find_by_source(self, c: sqlite3.Connection, source_name: str, external_id: str) -> int | None:
        row = c.execute(
            "SELECT grant_id FROM grant_sources WHERE source_name=? AND source_external_id=?",
            (source_name, external_id),
        ).fetchone()
        return int(row[0]) if row else None


    @staticmethod
    def _merge_deadline(old: str | None, new: str | None) -> str | None:
        if not old:
            return new
        if not new:
            return old
        try:
            return max(date.fromisoformat(old), date.fromisoformat(new)).isoformat()
        except ValueError:
            return new or old

    @staticmethod
    def _prefer(old: str | None, new: str | None) -> str:
        old = old or ""
        new = new or ""
        return new if len(new.strip()) > len(old.strip()) else old

    def upsert_grant(
        self,
        g: ScrapedGrant,
        relevance_score: int,
        relevance_level: str,
        relevance_reasons: list[str],
        category: str,
        eligibility_status: str,
        eligibility_reasons: list[str],
    ) -> int:
        now = utcnow()
        candidate = g.to_dict()
        with self.conn() as c:
            grant_id = self._find_by_source(c, g.source_name, g.source_external_id)
            if grant_id is None:
                dup = find_duplicate(self._grant_rows_for_dedup(c), candidate)
                grant_id = int(dup["id"]) if dup else None

            if grant_id is None:
                cur = c.execute(
                    """
                    INSERT INTO grants(
                        canonical_key,title,funder,category,description,objectives,activities,
                        beneficiaries,eligible_entities,territory,partners_required,amount_available,
                        cofinancing,open_date,deadline,official_url,requirements,relevance_score,
                        relevance_level,relevance_reasons,eligibility_status,eligibility_reasons,
                        expired,first_seen_at,last_seen_at,updated_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        normalize_title(g.title), g.title, g.funder, category, g.description, g.objectives,
                        g.activities, g.beneficiaries, g.eligible_entities, g.territory, g.partners_required,
                        g.amount_available, g.cofinancing, g.open_date.isoformat() if g.open_date else None,
                        g.deadline.isoformat() if g.deadline else None, g.official_url, g.requirements,
                        relevance_score, relevance_level, json.dumps(relevance_reasons, ensure_ascii=False),
                        eligibility_status, json.dumps(eligibility_reasons, ensure_ascii=False),
                        int(bool(g.deadline and g.deadline < date.today())), now, now, now,
                    ),
                )
                grant_id = int(cur.lastrowid)
            else:
                current = dict(c.execute("SELECT * FROM grants WHERE id=?", (grant_id,)).fetchone())
                merged = {
                    "title": self._prefer(current["title"], g.title),
                    "funder": self._prefer(current["funder"], g.funder),
                    "category": self._prefer(current["category"], category),
                    "description": self._prefer(current["description"], g.description),
                    "objectives": self._prefer(current["objectives"], g.objectives),
                    "activities": self._prefer(current["activities"], g.activities),
                    "beneficiaries": self._prefer(current["beneficiaries"], g.beneficiaries),
                    "eligible_entities": self._prefer(current["eligible_entities"], g.eligible_entities),
                    "territory": self._prefer(current["territory"], g.territory),
                    "partners_required": self._prefer(current["partners_required"], g.partners_required),
                    "amount_available": self._prefer(current["amount_available"], g.amount_available),
                    "cofinancing": self._prefer(current["cofinancing"], g.cofinancing),
                    "open_date": current["open_date"] or (g.open_date.isoformat() if g.open_date else None),
                    "deadline": self._merge_deadline(current["deadline"], g.deadline.isoformat() if g.deadline else None),
                    "official_url": current["official_url"] or g.official_url,
                    "requirements": self._prefer(current["requirements"], g.requirements),
                    "tags": list(dict.fromkeys(json.loads(current["tags"] or "[]") + g.tags)),
                }

                # Score the merged evidence, so a sparse duplicate can't hide a rich record.
                from services.relevance import score_grant
                from services.eligibility import evaluate_eligibility
                evidence = dict(merged)
                for date_key in ("deadline", "open_date"):
                    evidence[date_key] = date.fromisoformat(evidence[date_key]) if evidence[date_key] else None
                merged_grant = ScrapedGrant(source_name=g.source_name, source_url=g.source_url,
                    source_external_id=g.source_external_id, **evidence)
                rel = score_grant(merged_grant)
                merged["category"] = rel.category
                elig = evaluate_eligibility(merged_grant)
                relevance_score, relevance_level, relevance_reasons = rel.score, rel.level, rel.reasons
                eligibility_status, eligibility_reasons = elig.status, elig.reasons

                for field in ["deadline", "official_url", "amount_available", "cofinancing"]:
                    old = current.get(field)
                    new = merged.get(field)
                    if old != new and new:
                        c.execute(
                            "INSERT INTO grant_history(grant_id,changed_at,field_name,old_value,new_value) VALUES(?,?,?,?,?)",
                            (grant_id, now, field, old, new),
                        )

                c.execute(
                    """
                    UPDATE grants SET
                        canonical_key=?,title=?,funder=?,category=?,description=?,objectives=?,activities=?,
                        beneficiaries=?,eligible_entities=?,territory=?,partners_required=?,amount_available=?,
                        cofinancing=?,open_date=?,deadline=?,official_url=?,requirements=?,relevance_score=?,
                        relevance_level=?,relevance_reasons=?,eligibility_status=?,eligibility_reasons=?,
                        expired=?,last_seen_at=?,updated_at=?
                    WHERE id=?
                    """,
                    (
                        normalize_title(merged["title"]), merged["title"], merged["funder"], merged["category"],
                        merged["description"], merged["objectives"], merged["activities"], merged["beneficiaries"],
                        merged["eligible_entities"], merged["territory"], merged["partners_required"],
                        merged["amount_available"], merged["cofinancing"], merged["open_date"], merged["deadline"],
                        merged["official_url"], merged["requirements"], relevance_score, relevance_level,
                        json.dumps(relevance_reasons, ensure_ascii=False), eligibility_status,
                        json.dumps(eligibility_reasons, ensure_ascii=False),
                        int(bool(merged["deadline"] and date.fromisoformat(merged["deadline"]) < date.today())),
                        now, now, grant_id,
                    ),
                )

            c.execute(
                """
                INSERT INTO grant_sources(grant_id,source_name,source_url,source_external_id,last_seen_at)
                VALUES(?,?,?,?,?)
                ON CONFLICT(source_name,source_external_id) DO UPDATE SET
                    grant_id=excluded.grant_id,
                    source_url=excluded.source_url,
                    last_seen_at=excluded.last_seen_at
                """,
                (grant_id, g.source_name, g.source_url, g.source_external_id, now),
            )
            state = dict(c.execute("SELECT program,source_closed,tags FROM grants WHERE id=?", (grant_id,)).fetchone())
            tags = list(dict.fromkeys(json.loads(state["tags"] or "[]") + g.tags))
            c.execute("UPDATE grants SET tags=? WHERE id=?", (json.dumps(tags, ensure_ascii=False), grant_id))
            if g.program:
                c.execute("UPDATE grants SET program=? WHERE id=?", (g.program, grant_id))
            if g.source_closed is not None:
                if int(g.source_closed) != int(state["source_closed"] or 0):
                    c.execute("INSERT INTO grant_history(grant_id,changed_at,field_name,old_value,new_value) VALUES(?,?,?,?,?)",
                              (grant_id, now, "source_closed", str(state["source_closed"]), str(int(g.source_closed))))
                c.execute("UPDATE grants SET source_closed=? WHERE id=?", (int(g.source_closed), grant_id))
            c.execute("UPDATE grants SET expired=CASE WHEN source_closed=1 OR (deadline IS NOT NULL AND deadline < ?) THEN 1 ELSE 0 END WHERE id=?",
                      (date.today().isoformat(), grant_id))
            return grant_id

    def mark_expired(self) -> None:
        today = date.today().isoformat()
        with self.conn() as c:
            c.execute("UPDATE grants SET expired=CASE WHEN source_closed=1 OR (deadline IS NOT NULL AND deadline < ?) THEN 1 ELSE 0 END", (today,))

    def list_grants(self, include_irrelevant: bool = False) -> list[dict[str, Any]]:
        with self.conn() as c:
            where = "" if include_irrelevant else "WHERE g.relevance_level <> 'IRRILEVANTE'"
            rows = c.execute(
                f"""
                SELECT g.* FROM grants g
                {where}
                ORDER BY
                    CASE g.relevance_level WHEN 'ALTA' THEN 1 WHEN 'MEDIA' THEN 2 WHEN 'BASSA' THEN 3 ELSE 4 END,
                    CASE WHEN g.deadline IS NULL THEN 1 ELSE 0 END,
                    g.deadline ASC,
                    g.relevance_score DESC
                """
            ).fetchall()
            result = []
            for r in rows:
                item = dict(r)
                sources = c.execute(
                    "SELECT source_name,source_url,last_seen_at FROM grant_sources WHERE grant_id=? ORDER BY source_name",
                    (item["id"],),
                ).fetchall()
                item["sources"] = [dict(x) for x in sources if not is_excluded_source(x["source_name"])]
                if is_excluded_grant(item) or (sources and not item["sources"]):
                    continue
                item["relevance_reasons"] = json.loads(item["relevance_reasons"] or "[]")
                item["eligibility_reasons"] = json.loads(item["eligibility_reasons"] or "[]")
                # Reassess audited sources on read, including old caches and sheet exports.
                audited_sources = [x["source_name"] for x in item["sources"] if x["source_name"] in SOURCE_NOTES]
                if audited_sources:
                    from services.eligibility import evaluate_eligibility
                    evidence = {key: item[key] or "" for key in (
                        "title", "funder", "eligible_entities", "requirements", "territory",
                        "partners_required", "description", "objectives",
                    )}
                    assessments = [evaluate_eligibility(ScrapedGrant(source_name=name,
                        source_url="", source_external_id=str(item["id"]), **evidence)) for name in audited_sources]
                    rank = {"Probabilmente ammissibile": 0, "Da verificare": 1, "Probabilmente non ammissibile": 2}
                    item["eligibility_status"] = max(assessments, key=lambda a: rank[a.status]).status
                    item["eligibility_reasons"] = list(dict.fromkeys(reason for a in assessments for reason in a.reasons))
                if item["deadline"]:
                    try:
                        item["days_left"] = (date.fromisoformat(item["deadline"]) - date.today()).days
                    except ValueError:
                        item["days_left"] = None
                else:
                    item["days_left"] = None
                result.append(item)
            return result

    def history(self, grant_id: int) -> list[dict]:
        with self.conn() as c:
            rows = c.execute(
                "SELECT changed_at,field_name,old_value,new_value FROM grant_history WHERE grant_id=? ORDER BY id DESC",
                (grant_id,),
            ).fetchall()
            return [dict(r) for r in rows]
