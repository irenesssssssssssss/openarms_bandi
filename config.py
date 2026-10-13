from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = Path(os.getenv("DB_PATH", DATA_DIR / "openarms_bandi.sqlite3"))
LOG_DIR = Path(os.getenv("LOG_DIR", BASE_DIR / "logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)

APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
UPDATE_INTERVAL_MINUTES = int(os.getenv("UPDATE_INTERVAL_MINUTES", "60"))
REFRESH_ON_STARTUP = os.getenv("REFRESH_ON_STARTUP", "true").lower() == "true"

REQUEST_TIMEOUT_SECONDS = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "20"))
REQUEST_RETRIES = int(os.getenv("REQUEST_RETRIES", "2"))
REQUEST_DELAY_SECONDS = float(os.getenv("REQUEST_DELAY_SECONDS", "0.8"))
USER_AGENT = os.getenv(
    "USER_AGENT",
    "OpenArmsGrantMonitor/0.1 (non-commercial grant monitoring)",
)
ROBOTS_STRICT = os.getenv("ROBOTS_STRICT", "false").lower() == "true"

CSV_LAZIO_MAX_PAGES = int(os.getenv("CSV_LAZIO_MAX_PAGES", "15"))
INFOBANDI_MAX_PAGES = int(os.getenv("INFOBANDI_MAX_PAGES", "10"))
CONFINIONLINE_MAX_PAGES = int(os.getenv("CONFINIONLINE_MAX_PAGES", "12"))

RELEVANCE_MIN_VISIBLE_SCORE = int(os.getenv("RELEVANCE_MIN_VISIBLE_SCORE", "12"))

OPEN_ARMS_RUNTS = os.getenv("OPEN_ARMS_RUNTS", "unknown").lower()  # yes/no/unknown
OPEN_ARMS_ASSOCIATION_REGISTER = os.getenv("OPEN_ARMS_ASSOCIATION_REGISTER", "unknown").lower()
OPEN_ARMS_REGIONS = [x.strip() for x in os.getenv("OPEN_ARMS_REGIONS", "Italia").split(",") if x.strip()]

GOOGLE_SHEETS_ENABLED = os.getenv("GOOGLE_SHEETS_ENABLED", "false").lower() == "true"
GOOGLE_SHEETS_SPREADSHEET_ID = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "")
GOOGLE_SHEETS_WORKSHEET = os.getenv("GOOGLE_SHEETS_WORKSHEET", "Bandi")
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "")

# Limiti di copertura: gli archivi non vengono scansionati senza limiti.
ADDITIONAL_MAX_PAGES = max(1, int(os.getenv("ADDITIONAL_MAX_PAGES", "3")))
ADDITIONAL_MAX_DETAILS = max(1, int(os.getenv("ADDITIONAL_MAX_DETAILS", "35")))
EU_MAX_PAGES_PER_QUERY = max(1, int(os.getenv("EU_MAX_PAGES_PER_QUERY", "3")))
EU_PAGE_SIZE = max(1, min(100, int(os.getenv("EU_PAGE_SIZE", "50"))))
REFRESH_MAX_WORKERS = max(1, min(4, int(os.getenv("REFRESH_MAX_WORKERS", "3"))))
PDF_MAX_BYTES = 10 * 1024 * 1024
