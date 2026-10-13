# Pubblicazione gratuita con GitHub Pages

Il workflow `.github/workflows/pages.yml` pubblica il sito a ogni push su
`main`, ogni 6 ore circa e su richiesta dal pulsante Run workflow nella
scheda Actions. In Settings > Pages selezionare GitHub Actions come Source.
Il primo aggiornamento cloud legge le fonti da zero: il database locale
non viene caricato su GitHub.

Solo `public-site` viene pubblicata: HTML, CSS, JavaScript, `.nojekyll`
e dati JSON dei bandi. Nessun database, log, .env o credenziale viene
copiato nell'artefatto del sito. Prima del primo commit verificare comunque
i file selezionati: .gitignore non rimuove file già tracciati da Git.

La pagina pubblica mantiene ricerca, filtri e ordinamento. RICARICA DATI
legge l'ultima versione pubblicata, senza avviare gli scraper. La
sincronizzazione Google Sheets rimane disponibile solo nell'app locale.

## Verifica locale

Con l'ambiente virtuale attivo:

```powershell
python build_public.py
python -m http.server 8080 --directory public-site
```

Aprire http://localhost:8080. Il primo comando esporta il database locale
senza interrogare le fonti. Per aggiornare anche le fonti usare
`python build_public.py --refresh`.

L'app locale continua a usare FastAPI, senza modifiche al suo avvio.

## Limiti dell'automazione gratuita

GitHub può ritardare o saltare le esecuzioni programmate; nei repository
pubblici le disabilita dopo 60 giorni senza attività. Si possono riattivare
dalla scheda Actions. La cache conserva SQLite tra le esecuzioni, ma può
essere eliminata da GitHub: in quel caso le fonti vengono rilette da zero
e lo storico precedente non è garantito. Non è un archivio permanente.

Se alcune fonti falliscono, vengono pubblicati i dati disponibili con
gli stati di errore o parziali. Se tutte falliscono o la build fallisce,
la pubblicazione viene interrotta e il sito precedente resta disponibile.

Fonti: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
e https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching
