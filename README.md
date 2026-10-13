# Aggiornamento v0.4.0 — 13 fonti dopo la verifica di ammissibilità

Questo ZIP è completo: comprende le fonti aggiunte e tutte le modifiche a sport, cultura e formazione al soccorso in acqua.

**EYF è stata rimossa** perché richiede organizzazioni giovanili registrate con requisiti specifici di partecipazione e gestione da parte dei giovani. È stato eliminato anche il riquadro di importazione da Chrome. Le call EYF già salvate non vengono più mostrate né esportate, anche se sono state riprese da un aggregatore e sono riconoscibili dal titolo, dal finanziatore, dal programma o dal link ufficiale. Lo storico SQLite resta conservato. Per le schede incomplete provenienti dagli aggregatori l'identificazione può richiedere il controllo del link ufficiale.

Le altre **13 fonti** rimangono: pubblicano almeno alcune opportunità per non profit/ETS e non impongono tutte la natura giovanile dell'organizzazione. Questo non certifica l'ammissibilità di Open Arms a ogni bando. In particolare AICS richiede di verificare l'Elenco OSC per il ruolo di proponente/capofila nei bandi per OSC; PN Inclusione pubblica sia avvisi per ETS sia avvisi per amministrazioni; fondazioni e portale UE hanno requisiti specifici di territorio, bilancio, registri o partenariato. Passando sullo stato della fonte compare anche una nota sui requisiti. La verifica con tutti i link ufficiali è in **AMMISSIBILITA_FONTI.md**.

Le schede salvate delle fonti controllate vengono rivalutate anche senza una nuova scansione: requisiti mancanti restano “Da verificare”. Sport e cultura mantengono il collegamento alla finalità sociale introdotto nella v0.3.

## Sport, cultura e formazione al soccorso

Sport, attività motorie, nuoto, musica, teatro, danza, cinema, arte, lettura e biblioteche ricevono un bonus positivo **quando il progetto li collega a una finalità sociale**: inclusione, integrazione, disabilità/accessibilità, povertà educativa, coesione sociale, partecipazione civica, contrasto all'isolamento, solidarietà o benessere sociale. Anche i laboratori educativi per bambini e giovani possono essere rilevanti. Le nuove categorie sono **Sport & Inclusione** e **Cultura & Inclusione**.

Il bonus è di 25 punti per ambito e non si moltiplica per sinonimi o ripetizioni. Si leggono titolo, obiettivi, attività, beneficiari e descrizione; una categoria, un tag generico o la sola ammissibilità degli ETS non attivano il bonus. Nelle descrizioni lunghe il collegamento si cerca vicino al tema oppure tra titolo e frasi descrittive. Si tratta di regole testuali trasparenti, non di una comprensione completa del bando: la scheda mostra la combinazione riconosciuta.

| Esempio | Comportamento |
|---|---|
| Sport per l'inclusione sociale; nuoto per persone con disabilità | Bonus positivo, categoria Sport & Inclusione |
| Musica e integrazione; teatro contro la povertà educativa | Bonus positivo, categoria Cultura & Inclusione |
| Campionato agonistico; festival musicale generico; formazione di musicisti professionisti | Nessun bonus sociale per queste parole da sole |
| Formazione al soccorso in acqua; salvataggio acquatico; prevenzione dell'annegamento | Termini prioritari; ulteriore bonus per formazione/addestramento, categoria Soccorso & Emergenze |

Sono riconosciuti anche equivalenti inglesi, tra cui social inclusion, music, water rescue, water safety e drowning prevention. Sport e cultura non vengono penalizzati quando la relativa regola sociale è soddisfatta. La rilevanza resta separata dall'ammissibilità e dai vincoli territoriali/economici.

**Al riavvio vengono rivalutati anche i bandi già nel database**, senza attendere una nuova scansione delle fonti e mantenendo fonti e scadenze; le schede delle fonti controllate vengono rivalutate anche per ammissibilità. I tag originali vengono conservati dalla v0.3; quelli non memorizzati nelle versioni precedenti tornano disponibili alla successiva lettura della fonte.

## Aggiornare su Windows (senza perdere i dati)

1. Ferma il server con **Ctrl+C** nella finestra PowerShell.
2. Estrai questo ZIP e copia il **contenuto** della cartella `openarms-bandi` nella tua cartella già esistente `C:\Users\irene\Desktop\openarms-bandi`. Accetta la sostituzione dei file di codice. Non eliminare la cartella esistente.
3. Conserva `.env`, `.venv`, `data` e `logs`. Il nuovo `.env.example` documenta le nuove opzioni, ma non serve ricopiarlo sopra `.env`.
4. Nella tua cartella, con `(.venv)` attivo, esegui:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --workers 1
```

Apri `http://127.0.0.1:8000` e ricarica con **Ctrl+F5**. Il database viene aggiornato automaticamente mantenendo i record esistenti. Il primo controllo può richiedere alcuni minuti: la dashboard resta disponibile e mostra l'avanzamento per fonte.

In alternativa `Avvia-Windows.ps1` prepara le dipendenze e avvia il server usando direttamente il Python dell'ambiente virtuale. Per nuova installazione crea anche `.venv` e `.env` solo se mancanti.

## Nuove fonti e metodi

| Fonte approvata | Metodo | Copertura / limite |
|---|---|---|
| 1. EU Funding & Tenders | API pubblica SEDIA, query multipart JSON, lingua inglese | Ricerche CERV, AMIF, ERASMUS, ESC, migration, human rights, social inclusion, rescue. Topic di sovvenzione, non gare/organizzazioni. Elenco mirato, non esportazione integrale del portale. |
| 2. Integrazione Migranti | HTML + form pubblico ASP.NET per paginazione | Prime pagine recenti; esclusi corsi/borse/selezioni individuali individuabili dal titolo. |
| 3. PN Inclusione | HTML archivio avvisi + home | Avvisi e preavvisi nelle schede pubbliche; diversi sono riservati ad amministrazioni pubbliche. |
| 4. Ministero Lavoro / Terzo Settore | Taxonomy Terzo Settore + pagina tematica, schede e PDF | Avvisi individuati nelle pagine recenti; distinzione tra data di candidatura e termine del progetto. |
| 5. AICS | Archivio HTML + schede | Selezione di annunci di bandi/call; esclusi risultati, FAQ, eventi e gare di acquisto riconoscibili dal titolo. Alcuni bandi territoriali possono essere pubblicati esclusivamente sui siti delle sedi estere. |
| 6. Fondazione CON IL SUD | Schede HTML con stato, scadenza e risorse | Archivio pubblico, dettagli delle opportunità attive; nessun accesso alla piattaforma candidature. |
| 7. Fondazione di Sardegna | Tre sezioni pubbliche, link alle aree annuali e PDF | Bandi ROL, Educazione e altri bandi; esclusi FAQ/elenchi risultati. PDF senza testo richiedono verifica manuale. |
| 8. Fondazione Unipolis | Endpoint JSON pubblico usato dall'elenco ufficiale + schede | Campi di apertura/chiusura e requisiti pubblici; nessun login. |
| 11. Compagnia di San Paolo | HTML paginato `sf_paged` + schede | Vincoli territoriali da verificare; bandi e linee guida possono essere già chiusi. |
| 13. Open Society Foundations | Pagina pubblica Grants | Solo call per organizzazioni; fellowship individuali escluse. Un elenco senza call per organizzazioni restituisce OK · 0. Nessuna ricerca tra grant su invito. |

Gli URL e i selettori sono in `scrapers/official_sources.py` e `scrapers/eu_portal.py`. Le API non richiedono una chiave personale: SEDIA usa il parametro pubblico `apiKey=SEDIA` documentato dalla Commissione.

## Cosa cambia nella dashboard

- Colonna e filtro **Programma**, anche nell'esportazione Google Sheets.
- Scoring anche in inglese per le call UE e internazionali.
- Stato **IN CORSO**, **OK**, **PARZIALE**, **ERRORE** per ogni fonte. Il tooltip spiega il limite o errore; i record già salvati restano disponibili.
- Il pulsante di aggiornamento avvia una procedura in background. La pagina si aggiorna ogni 5 secondi; le fonti vengono interrogate solo nel ciclo impostato (60 minuti di default) o su richiesta manuale.
- Controlli su edizioni annuali/identificativi di call per evitare fusioni sbagliate.
- Le call esplicitamente chiuse sono nascoste anche quando manca una data. Le scadenze non individuate con sufficiente evidenza sono “Da verificare”.

## Limiti e configurazione

Non è real time e non garantisce di trovare ogni opportunità disponibile. Di default si leggono fino a 3 pagine recenti e 35 dettagli per nuova fonte; le ricerche UE arrivano fino a 3 pagine da 50 topic **per termine**. Quando un limite viene raggiunto, la fonte è **PARZIALE**. Aumenta `ADDITIONAL_MAX_PAGES`, `ADDITIONAL_MAX_DETAILS`, `EU_MAX_PAGES_PER_QUERY` o `EU_PAGE_SIZE` in `.env` se vuoi ampliare la scansione, con tempi e richieste maggiori. Il parser può richiedere adattamenti se cambia un sito.

La parte europea non include automaticamente tutte le azioni Erasmus+/ESC gestite da agenzie nazionali: la copertura è quella delle call centrali trovate sul portale. L'ammissibilità richiede la verifica dell'identità giuridica di Open Arms Italia, dei registri, delle soglie economiche, dei paesi e del partenariato. I requisiti in PDF possono non essere riassunti integralmente nei campi tabellari: il link ufficiale resta essenziale.

Sono rispettati i `Disallow` espliciti in `robots.txt`. Quando il file è assente/non leggibile, resta il comportamento configurabile dell'MVP (`ROBOTS_STRICT=false` di default); questo non equivale a un'autorizzazione del sito. La lettura riguarda contenuti pubblici e non invia candidature o dati personali.

## Validazione

- Test offline: `python -m pip install pytest`, poi `python -m pytest -q`.
- Coperti: scadenze vs pubblicazione/fine progetto, date ISO UE, JSON Unipolis, multipart SEDIA, esclusione EYF anche dalla cache, OSF senza call, migrazione SQLite, fonti in errore, scoring inglese e limiti economici.
- Le fonti aggiunte sono state interrogate su Internet nell'ambiente di verifica il 09/10/2026. Risultati e limiti dell'ultima prova sono in `VERIFICA_FONTI.md`.

---

## Documentazione dell'MVP originale

# Open Arms – Monitor Bandi (MVP)

Dashboard web che aggrega bandi da **CSV Lazio**, **Infobandi CSVnet** e **ConfiniOnline**, li deduplica, calcola una rilevanza trasparente per Open Arms e separa la rilevanza tematica dall'ammissibilità.

## Verifica tecnica delle fonti (07/10/2026)

| Fonte | Metodo osservato | Strategia MVP | Affidabilità | Limiti |
|---|---|---|---|---|
| CSV Lazio | WordPress; feed RSS di categoria disponibile; archivio HTML paginato; schede pubbliche strutturate | RSS + HTML recente + ricontrollo delle schede attive già note | Medio-alta | Archivio storico molto profondo; alcune schede possono avere etichette diverse |
| Infobandi CSVnet | HTML server-side, paginazione `?sf_paged=N`; schede pubbliche molto strutturate | Scraping HTML con `httpx` + BeautifulSoup | Alta | Nessuna API pubblica verificata; dipendenza dalla struttura HTML/etichette |
| ConfiniOnline | HTML server-side, paginazione `?pagina=N` | Scraping della pagina elenco pubblica | Media | Il link “scarica” porta a un form di iscrizione; l'MVP non lo aggira e quindi molti requisiti restano “Da verificare” |

Non è necessario Playwright/Selenium: le pagine osservate sono leggibili con normali richieste HTTP e non richiedono JavaScript per ottenere l'elenco dei bandi.

### robots.txt

Durante la verifica esterna i tre `robots.txt` non erano leggibili dallo strumento di analisi usato per preparare l'MVP, quindi non viene fatta un'affermazione non verificata sul loro contenuto. Il codice **controlla `robots.txt` a runtime** prima di scaricare pagine HTML; un `Disallow` esplicito viene rispettato. Se `robots.txt` è temporaneamente irraggiungibile, il comportamento è configurabile con `ROBOTS_STRICT`.

## Architettura

- **FastAPI**: API + hosting della dashboard.
- **SQLite**: database locale con storico delle variazioni.
- **Thread scheduler interno**: aggiornamento automatico ogni 60 minuti (configurabile), senza dipendenze extra.
- **httpx + BeautifulSoup**: scraping server-side.
- **XML standard library**: parsing RSS CSV Lazio.
- **rapidfuzz**: deduplicazione fuzzy.
- **Vanilla HTML/CSS/JS**: tabella stile Google Sheets, senza build frontend.
- **Google Sheets**: sincronizzazione opzionale tramite service account.

Il progetto usa **un solo processo/worker** perché lo scheduler vive nello stesso processo dell'app. Se in produzione vuoi più worker, sposta il refresh in cron/systemd/Celery e disattiva `REFRESH_ON_STARTUP`.

## Struttura

```text
openarms-bandi/
├── app.py
├── config.py
├── models.py
├── requirements.txt
├── requirements-google-sheets.txt
├── .env.example
├── Dockerfile
├── scrapers/
│   ├── base.py
│   ├── csv_lazio.py
│   ├── infobandi.py
│   └── confinionline.py
├── services/
│   ├── relevance.py
│   ├── eligibility.py
│   ├── deduplication.py
│   ├── refresh.py
│   └── google_sheets.py
├── database/
│   └── repository.py
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── data/
├── logs/
└── tests/
    └── test_services.py
```

## Installazione locale

Richiede Python 3.11+ (consigliato 3.12).

```bash
cd openarms-bandi
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt
cp .env.example .env
```

Su Windows, invece di `cp`:

```powershell
Copy-Item .env.example .env
```

Modifica almeno `USER_AGENT` se vuoi inserire un contatto reale dell'organizzazione.

## Avvio

```bash
uvicorn app:app --host 127.0.0.1 --port 8000 --workers 1
```

Apri `http://127.0.0.1:8000`.

Al primo avvio, se `REFRESH_ON_STARTUP=true`, parte un aggiornamento automatico. Puoi anche usare **AGGIORNA ORA**.

## Aggiornamento automatico

Ogni `UPDATE_INTERVAL_MINUTES` (default 60):

1. controlla separatamente le 13 fonti configurate;
2. una fonte in errore non blocca le altre;
3. aggiorna/inserisce i bandi;
4. deduplica tra fonti;
5. registra variazioni importanti (es. scadenza, importo, URL ufficiale);
6. mantiene i record storici;
7. marca i bandi scaduti invece di cancellarli;
8. aggiorna lo stato fonte visibile nella dashboard.

Per CSV Lazio, oltre al feed/pagine recenti, le schede attive già presenti nel database vengono ricontrollate per intercettare proroghe senza dover ripercorrere tutto lo storico a ogni ciclo.

## Relevance scoring

La v1 **non richiede OpenAI, Claude o altre API a pagamento**. Il modulo `services/relevance.py` usa:

- keyword pesate;
- peso diverso per titolo, obiettivi, attività, beneficiari, descrizione, categorie/tag;
- bonus per combinazioni semantiche semplici (es. migrazione + scuola, mare + soccorso, diritti umani + advocacy);
- penalità leggere per ambiti chiaramente lontani quando non ci sono segnali forti Open Arms.

Soglie:

- `ALTA`: score >= 50
- `MEDIA`: 25–49
- `BASSA`: 12–24
- `IRRILEVANTE`: < 12 (salvato nel DB, non mostrato nella dashboard principale)

Il modulo è separato: in futuro può essere sostituito con embeddings o un LLM.

## Ammissibilità

`services/eligibility.py` produce separatamente:

- **Probabilmente ammissibile**
- **Da verificare**
- **Probabilmente non ammissibile**

Non assume che Open Arms Italia sia iscritta al RUNTS o ad altri registri. Imposta in `.env` solo dati verificati:

```env
OPEN_ARMS_RUNTS=yes
OPEN_ARMS_ASSOCIATION_REGISTER=unknown
```

Un bando molto pertinente non viene nascosto se l'ammissibilità è incerta.

## Deduplicazione

La deduplicazione considera, in ordine pratico:

1. URL ufficiale normalizzato;
2. similarità del titolo;
3. stessa scadenza;
4. similarità dell'ente finanziatore.

Le fonti restano collegate allo stesso record e nella dashboard vengono mostrate come `CSV Lazio + Infobandi`, con i singoli link.

## Google Sheets opzionale

1. Crea un progetto Google Cloud e abilita Google Sheets API.
2. Crea un service account e scarica il JSON delle credenziali.
3. Condividi il Google Sheet con l'email del service account.
4. Installa le dipendenze opzionali:

```bash
pip install -r requirements-google-sheets.txt
```

5. Configura `.env`:

```env
GOOGLE_SHEETS_ENABLED=true
GOOGLE_SHEETS_SPREADSHEET_ID=ID_DELLO_SHEET
GOOGLE_SHEETS_WORKSHEET=Bandi
GOOGLE_SERVICE_ACCOUNT_FILE=/percorso/service-account.json
```

Comparirà il pulsante **SYNC GOOGLE SHEET**. Il funzionamento principale non dipende da Google Sheets.

## Deployment semplice

### Opzione A — VPS (consigliata per SQLite)

```bash
git clone <repo>
cd openarms-bandi
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 1
```

Per produzione usa `systemd` e un reverse proxy (nginx/Caddy). Conserva la cartella `data/` su disco persistente.

Esempio `systemd`:

```ini
[Unit]
Description=Open Arms Monitor Bandi
After=network.target

[Service]
WorkingDirectory=/opt/openarms-bandi
ExecStart=/opt/openarms-bandi/.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000 --workers 1
Restart=always
EnvironmentFile=/opt/openarms-bandi/.env

[Install]
WantedBy=multi-user.target
```

### Opzione B — Docker

```bash
docker build -t openarms-bandi .
docker run --rm -p 8000:8000 --env-file .env -v $(pwd)/data:/app/data openarms-bandi
```

Serve un volume persistente per SQLite.

## Se un sito cambia struttura

Ogni fonte è isolata nel proprio scraper. Se una struttura cambia:

1. la dashboard continua a mostrare i dati già salvati;
2. le altre fonti continuano ad aggiornarsi;
3. lo stato della fonte diventa `ERRORE`;
4. controlla `logs/app.log`;
5. modifica solo il file in `scrapers/` relativo alla fonte;
6. aggiorna i selettori/etichette e testa di nuovo.

## Limiti noti

- **ConfiniOnline**: non vengono compilati o aggirati moduli di registrazione. I dati non presenti nell'elenco pubblico restano vuoti/“Da verificare”.
- **CSV Lazio**: un archivio molto profondo rende poco appropriato ripercorrere l'intero storico ogni ora. `CSV_LAZIO_MAX_PAGES` è configurabile; i record attivi già scoperti vengono comunque ricontrollati.
- **Robots/termini d'uso**: il codice rispetta `robots.txt` quando disponibile, applica rate limiting e usa solo pagine pubbliche. Prima di un uso organizzativo stabile è comunque opportuno verificare anche eventuali condizioni d'uso specifiche dei tre siti e, se possibile, chiedere autorizzazione per un monitoraggio continuativo.
- **Ammissibilità**: è un supporto al triage, non una valutazione legale. La fonte ufficiale del bando prevale sempre.
