from __future__ import annotations

import logging
import threading
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config import (
    BASE_DIR,
    GOOGLE_SHEETS_ENABLED,
    LOG_DIR,
    REFRESH_ON_STARTUP,
    UPDATE_INTERVAL_MINUTES,
)
from database.repository import Repository
from services.google_sheets import sync_to_google_sheet
from services.source_policy import SOURCE_NOTES
from services.refresh import refresh_all, refresh_is_running, SCRAPERS


def configure_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(LOG_DIR / "app.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[handler, logging.StreamHandler()],
    )


configure_logging()
log = logging.getLogger(__name__)
repo = Repository()
_stop_event = threading.Event()
_scheduler_thread: threading.Thread | None = None

app = FastAPI(title="Open Arms – Monitor Bandi", version="0.4.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "frontend"), name="static")


def _scheduler_loop() -> None:
    if REFRESH_ON_STARTUP and not _stop_event.is_set():
        try:
            refresh_all(repo)
        except Exception:
            log.exception("Aggiornamento iniziale fallito")
    while not _stop_event.wait(UPDATE_INTERVAL_MINUTES * 60):
        try:
            refresh_all(repo)
        except Exception:
            log.exception("Aggiornamento pianificato fallito")


@app.on_event("startup")
def startup() -> None:
    global _scheduler_thread
    log.info("Rilevanza ricalcolata per %s bandi salvati", repo.recalculate_relevance())
    _stop_event.clear()
    if _scheduler_thread is None or not _scheduler_thread.is_alive():
        _scheduler_thread = threading.Thread(target=_scheduler_loop, name="grant-refresh", daemon=True)
        _scheduler_thread.start()


@app.on_event("shutdown")
def shutdown() -> None:
    _stop_event.set()


@app.get("/")
def index():
    return FileResponse(BASE_DIR / "frontend" / "index.html")


@app.get("/api/grants")
def grants(include_irrelevant: bool = Query(False)):
    return {"items": repo.list_grants(include_irrelevant=include_irrelevant)}


@app.get("/api/status")
def status():
    return {
        "latest_refresh": repo.latest_refresh(),
        "sources": [{**next((row for row in repo.source_statuses() if row["source_name"] == cls.source_name),
                    {"source_name": cls.source_name, "status": "DA CONTROLLARE", "message": "", "items_seen": 0}),
                    "eligibility_note": SOURCE_NOTES.get(cls.source_name, "")}
                    for cls in SCRAPERS],
        "refresh_running": refresh_is_running(),
        "update_interval_minutes": UPDATE_INTERVAL_MINUTES,
        "google_sheets_enabled": GOOGLE_SHEETS_ENABLED,
    }


@app.get("/api/grants/{grant_id}/history")
def history(grant_id: int):
    return {"items": repo.history(grant_id)}


@app.post("/api/refresh")
def manual_refresh():
    if refresh_is_running():
        return {"status": "busy", "message": "Un aggiornamento è già in corso."}
    threading.Thread(target=refresh_all, args=(repo,), name="manual-refresh", daemon=True).start()
    return {"status": "queued", "message": "Aggiornamento avviato. La dashboard mostra i risultati man mano che arrivano."}


@app.post("/api/google-sheets/sync")
def google_sheets_sync():
    if not GOOGLE_SHEETS_ENABLED:
        raise HTTPException(status_code=400, detail="Google Sheets non è abilitato in .env")
    count = sync_to_google_sheet(repo.list_grants(include_irrelevant=False))
    return {"status": "ok", "rows": count}

