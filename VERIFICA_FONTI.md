# Verifica tecnica — 9 ottobre 2026

È stato aggiornato il progetto MVP originale, senza richiedere nuovi servizi a pagamento.

La verifica ha usato richieste HTTP alle pagine e alle API pubbliche effettive, non soltanto risultati di ricerca o HTML inventato. Gli scraper controllano robots.txt e mantengono un intervallo tra richieste. Nessun modulo di candidatura è stato compilato.

| Fonte aggiunta | Evidenza tecnica e risultato |
|---|---|
| EU Funding & Tenders | API SEDIA: POST multipart con file `query.json`. Importati 252 topic distinti nella prova a 3 pagine da 50 per ricerca. Le ricerche “human rights” e “social inclusion” superano il limite; la fonte segnala PARZIALE. I risultati possono includere record con stato remoto obsoleto: le date passate li escludono dalla vista predefinita. |
| Integrazione Migranti | Letti HTML e paginazione del form ASP.NET (hidden fields e `vaiAllaPagina`). 22 annunci per organizzazioni dalle prime 3 pagine, con copertura dichiarata parziale dell'archivio. Un articolo SAI contenente anche proroghe di altri progetti è usato per controllare che 10 novembre 2026 non diventi 31 dicembre 2026. |
| PN Inclusione | 25 schede pubbliche tra archivio e homepage. Alcuni inviti sono destinati ad amministrazioni: l'ammissibilità rimane da verificare. Rebuilding 2.0: riconosciuta la data 30 ottobre 2026. |
| Ministero Lavoro / Terzo Settore | Pagine Drupal e download dell'Avviso 2/2026 in PDF. Riconosciuta la data 22 ottobre 2026 nella sezione di presentazione delle domande; le date di conclusione/rendicontazione non diventano la scadenza. Archivio limitato alle pagine configurate. |
| AICS | Verificati archivio e schede HTML. Una prova ha registrato un timeout; la fonte è indipendente dalle altre ed è stata ricontrollata con successo (11 annunci). Esclusi gli annunci riconoscibili come FAQ, graduatorie e risultati. |
| Fondazione CON IL SUD | 50 schede con stato pubblico, risorse e scadenza. Nella prova solo un bando risulta attivo; gli altri sono conservati come archivio e nascosti dalla vista normale. |
| Fondazione di Sardegna | Verificati i link correnti alle aree, alle sezioni Educazione/Altri bandi e ai PDF (13 documenti di bando nella prova finale). Gli URL delle aree possono contenere anni storici mentre il contenuto è aggiornato. Per i bandi annuali 2026 la candidatura può essere terminata il 5 dicembre 2025: il titolo non determina l'anno di scadenza. |
| Unipolis | Verificata la chiamata JSON pubblica `/site/wp-json/unipolis/v1/filtra-bandi`, con payload chips/year/toggle. Letti 4 bandi e i dettagli; separati chiusura/apertura, condizioni economiche e stato chiuso. |
| European Youth Foundation — rimossa nella v0.4.0 | La precedente prova leggeva 6 call chiuse. La fonte è ora esclusa per requisiti organizzativi incompatibili con la selezione richiesta dall’utente. |
| Compagnia di San Paolo | Letti 36 bandi/linee guida nelle prime 3 pagine (`sf_paged`), con limite segnalato come PARZIALE. Stati e date vengono dalle singole card. |
| Open Society Foundations | La pagina Grants era leggibile ma non esponeva call per organizzazioni; la fellowship individuale presente è stata esclusa. Risultato valido: OK, 0. |

I conteggi riguardano record osservati nelle fonti prima del filtro di rilevanza, dello stato di scadenza e della deduplicazione. Non sono il numero di bandi attivi e ammissibili per Open Arms. Pagine e contenuti possono cambiare.

## Controlli del codice

52 test automatici superati nella v0.3.1, inclusi isolamento delle fonti in errore, mantenimento del database esistente, chiusura senza data, scadenze, API, scoring inglese e identità distinte. Le nuove prove coprono sport e cultura con finalità sociali, esclusione del bonus per attività generiche/professionali e per soli metadati/enti ammessi, formazione al soccorso in acqua anche in inglese, sinonimi senza bonus duplicati e rivalutazione del database con conservazione di tag e ammissibilità.

Controllata la sintassi JavaScript nella v0.2. FastAPI risponde con HTTP 200 a `/`, `/api/grants`, `/api/status`; `/api/refresh` avvia il lavoro in background e restituisce immediatamente `queued`. Nella verifica aggiuntiva v0.3, con scansione di rete iniziale disattivata, il riavvio ha rivalutato tre record salvati: sport per inclusione e formazione al soccorso sono diventati visibili, mentre il festival musicale generico è rimasto irrilevante. Le 14 fonti e i giudizi di ammissibilità sono rimasti disponibili.

## Aggiornamento v0.4.0 — audit dei soggetti ammessi

EYF è esclusa: non viene più interrogata, non compare tra le fonti e il vecchio endpoint di importazione HTML non esiste più. Il filtro si applica ai record salvati e ai bandi riconoscibili come EYF nei portali aggregatori, sia nella dashboard sia nel dataset passato a Google Sheets. Non vengono cancellati dati o storico. Le altre 13 fonti sono mantenute dopo il controllo dei requisiti sui siti ufficiali; evidenze e limiti sono documentati in AMMISSIBILITA_FONTI.md. I risultati delle prove di rete sopra si riferiscono alla verifica precedente, non a una nuova scansione completa.

Sono stati aggiornati i controlli di ammissibilità: il requisito Elenco OSC per AICS come proponente/capofila non dipende più dalla sua presenza nel riassunto; soggetti pubblici ammessi vengono distinti dai beneficiari sociali del progetto; sigle ETS/APS/ODV sono cercate come parole intere. Le schede salvate delle fonti controllate vengono rivalutate durante la lettura, prima della visualizzazione o dell'esportazione. I requisiti economici e di anzianità già riconosciuti restano da verificare.

58 test automatici superati nella v0.4.0. Verificati cache esistente senza cancellazione dello storico, esclusione EYF tramite aggregatori e refresh, esportazione priva di EYF, 13 fonti API, rimozione del pannello e dell’endpoint, requisiti AICS anche senza testo completo, candidati pubblici rispetto ai beneficiari sociali e anzianità Unipolis. Sintassi JavaScript valida. Il test usa FastAPI TestClient e non dichiara una nuova verifica visuale in Chrome su Windows.

## Copertura e limiti

La scansione è periodica e mirata. Limiti configurabili per pagine, dettagli e risultati UE. Eventuali errori di rete, PDF non estraibili o selettori non riconosciuti sono visibili nello stato fonte; i record già salvati non vengono cancellati. “Da verificare” indica che non è stata raggiunta una conclusione affidabile: non equivale a essere ammissibili.

Gli esiti delle verifiche sono documentati per trasparenza; lo ZIP non contiene copie integrali dei siti o dei bandi terzi né un database prepopolato con risultati che diventerebbero obsoleti.
