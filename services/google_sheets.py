from __future__ import annotations

from config import (
    GOOGLE_SERVICE_ACCOUNT_FILE,
    GOOGLE_SHEETS_SPREADSHEET_ID,
    GOOGLE_SHEETS_WORKSHEET,
)

HEADERS = [
    "Rilevanza", "Titolo", "Ente finanziatore", "Programma", "Categoria", "Perché interessante per Open Arms",
    "Attività finanziabili", "Destinatari", "Enti ammessi", "Ammissibilità Open Arms", "Importo disponibile",
    "Cofinanziamento", "Territorio", "Necessità partner", "Data apertura", "Scadenza", "Giorni mancanti",
    "Fonte", "Link alla scheda", "Link al bando ufficiale", "Data ultimo aggiornamento",
]


def sync_to_google_sheet(grants: list[dict]) -> int:
    if not GOOGLE_SERVICE_ACCOUNT_FILE or not GOOGLE_SHEETS_SPREADSHEET_ID:
        raise RuntimeError("Configura GOOGLE_SERVICE_ACCOUNT_FILE e GOOGLE_SHEETS_SPREADSHEET_ID")
    try:
        import gspread
    except ImportError as exc:
        raise RuntimeError("Installa requirements-google-sheets.txt per abilitare Google Sheets") from exc

    gc = gspread.service_account(filename=GOOGLE_SERVICE_ACCOUNT_FILE)
    sh = gc.open_by_key(GOOGLE_SHEETS_SPREADSHEET_ID)
    try:
        ws = sh.worksheet(GOOGLE_SHEETS_WORKSHEET)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=GOOGLE_SHEETS_WORKSHEET, rows=1000, cols=len(HEADERS))

    values = [HEADERS]
    for g in grants:
        sources = g.get("sources", [])
        values.append([
            g.get("relevance_level", ""),
            g.get("title", ""),
            g.get("funder", ""),
            g.get("program", ""),
            g.get("category", ""),
            "; ".join(g.get("relevance_reasons", [])),
            g.get("activities", ""),
            g.get("beneficiaries", ""),
            g.get("eligible_entities", ""),
            g.get("eligibility_status", ""),
            g.get("amount_available", ""),
            g.get("cofinancing", ""),
            g.get("territory", ""),
            g.get("partners_required", ""),
            g.get("open_date", ""),
            g.get("deadline", ""),
            g.get("days_left", ""),
            " + ".join(x.get("source_name", "") for x in sources),
            " | ".join(x.get("source_url", "") for x in sources),
            g.get("official_url", ""),
            g.get("updated_at", ""),
        ])
    ws.clear()
    ws.update(values, value_input_option="RAW")
    ws.freeze(rows=1)
    return len(grants)
