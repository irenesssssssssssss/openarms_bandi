const columns = [
  ['relevance_level', 'Rilevanza'], ['title', 'Titolo'], ['funder', 'Ente finanziatore'], ['program', 'Programma'], ['category', 'Categoria'],
  ['relevance_reasons', 'Perché interessante per Open Arms'], ['activities', 'Attività finanziabili'],
  ['beneficiaries', 'Destinatari'], ['eligible_entities', 'Enti ammessi'], ['eligibility_status', 'Ammissibilità Open Arms'],
  ['amount_available', 'Importo disponibile'], ['cofinancing', 'Cofinanziamento'], ['territory', 'Territorio'],
  ['partners_required', 'Necessità partner'], ['open_date', 'Data apertura'], ['deadline', 'Scadenza'],
  ['days_left', 'Giorni mancanti'], ['sources', 'Fonte'], ['source_links', 'Link alla scheda'],
  ['official_url', 'Link al bando ufficiale'], ['updated_at', 'Data ultimo aggiornamento']
];
let allGrants = [];
let sortKey = null;
let sortDir = 1;
let grantsSnapshot = null;
const publicMode = document.body.dataset.public === 'true';

const $ = (id) => document.getElementById(id);

function esc(v) {
  return String(v ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
}
function fmtDate(v) {
  if (!v) return 'Da verificare';
  const d = new Date(v.length === 10 ? `${v}T12:00:00` : v);
  return Number.isNaN(d.getTime()) ? esc(v) : d.toLocaleDateString('it-IT');
}
function badgeRelevance(v, score) {
  const cls = v === 'ALTA' ? 'rel-alta' : v === 'MEDIA' ? 'rel-media' : 'rel-bassa';
  return `<span class="badge ${cls}">${esc(v)} · ${esc(score)}</span>`;
}
function badgeEligibility(v, reasons=[]) {
  const cls = v === 'Probabilmente ammissibile' ? 'elig-ok' : v === 'Probabilmente non ammissibile' ? 'elig-no' : 'elig-check';
  return `<span class="badge ${cls}" title="${esc((reasons||[]).join('; '))}">${esc(v)}</span>`;
}
function linksForSources(sources, namesOnly=false) {
  if (!sources?.length) return '';
  if (namesOnly) return sources.map(s => esc(s.source_name)).join(' + ');
  return `<div class="source-links">${sources.map(s => `<a href="${esc(s.source_url)}" target="_blank" rel="noopener">${esc(s.source_name)}</a>`).join('')}</div>`;
}
function cell(g, key) {
  if (key === 'relevance_level') return badgeRelevance(g.relevance_level, g.relevance_score);
  if (key === 'eligibility_status') return badgeEligibility(g.eligibility_status, g.eligibility_reasons);
  if (key === 'relevance_reasons') return `<div class="cell-clamp" tabindex="0" aria-label="Motivi della rilevanza" title="${esc((g.relevance_reasons||[]).join('; '))}">${esc((g.relevance_reasons||[]).join('; '))}</div>`;
  if (key === 'sources') return linksForSources(g.sources, true);
  if (key === 'source_links') return linksForSources(g.sources, false);
  if (key === 'official_url') return g.official_url ? `<a href="${esc(g.official_url)}" target="_blank" rel="noopener">Apri</a>` : '';
  if (key === 'deadline' || key === 'open_date' || key === 'updated_at') return fmtDate(g[key]);
  const value = g[key] ?? '';
  const long = ['activities','beneficiaries','eligible_entities','territory','amount_available','cofinancing'].includes(key);
  return long ? `<div class="cell-clamp" tabindex="0" aria-label="${esc(columns.find(([k]) => k === key)[1])}" title="${esc(value)}">${esc(value)}</div>` : esc(value);
}

function filtered() {
  const q = $('search').value.trim().toLowerCase();
  const source = $('sourceFilter').value;
  const category = $('categoryFilter').value;
  const program = $('programFilter').value;
  const rel = $('relevanceFilter').value;
  const elig = $('eligibilityFilter').value;
  const territory = $('territoryFilter').value.trim().toLowerCase();
  const days = Number($('daysFilter').value || 0);
  const deadlineFrom = $('deadlineFrom').value;
  const deadlineTo = $('deadlineTo').value;
  const showExpired = $('showExpired').checked;

  let rows = allGrants.filter(g => {
    const blob = [g.title,g.funder,g.program,g.category,g.description,g.objectives,g.activities,g.beneficiaries,g.territory,(g.relevance_reasons||[]).join(' ')].join(' ').toLowerCase();
    if (q && !blob.includes(q)) return false;
    if (source && !(g.sources||[]).some(s => s.source_name === source)) return false;
    if (category && g.category !== category) return false;
    if (program && g.program !== program) return false;
    if (rel && g.relevance_level !== rel) return false;
    if (elig && g.eligibility_status !== elig) return false;
    if (territory && !(g.territory||'').toLowerCase().includes(territory)) return false;
    if (!showExpired && g.expired) return false;
    if (days && (g.days_left == null || g.days_left < 0 || g.days_left > days)) return false;
    if (deadlineFrom && (!g.deadline || g.deadline < deadlineFrom)) return false;
    if (deadlineTo && (!g.deadline || g.deadline > deadlineTo)) return false;
    return true;
  });

  const defaultRank = {ALTA:1, MEDIA:2, BASSA:3, IRRILEVANTE:4};
  rows.sort((a,b) => {
    if (sortKey) {
      if (sortKey === 'relevance_level') {
        const rank = (defaultRank[a.relevance_level] || 9) - (defaultRank[b.relevance_level] || 9);
        return (rank || (b.relevance_score || 0) - (a.relevance_score || 0)) * sortDir;
      }
      let av = sortKey === 'sources' ? linksForSources(a.sources, true) : a[sortKey];
      let bv = sortKey === 'sources' ? linksForSources(b.sources, true) : b[sortKey];
      if (av == null) av = ''; if (bv == null) bv = '';
      if (typeof av === 'number' && typeof bv === 'number') return (av-bv)*sortDir;
      return String(av).localeCompare(String(bv), 'it', {numeric:true}) * sortDir;
    }
    const r = (defaultRank[a.relevance_level]||9) - (defaultRank[b.relevance_level]||9);
    if (r) return r;
    const score = (b.relevance_score || 0) - (a.relevance_score || 0);
    if (score) return score;
    if (!a.deadline && b.deadline) return 1;
    if (a.deadline && !b.deadline) return -1;
    if (a.deadline && b.deadline) return a.deadline.localeCompare(b.deadline);
    return 0;
  });
  return rows;
}

function render() {
  const rows = filtered();
  $('tableBody').innerHTML = rows.map(g => `<tr class="${g.expired ? 'expired' : ''}">${columns.map(([k]) => `<td>${cell(g,k)}</td>`).join('')}</tr>`).join('');
  $('emptyState').hidden = rows.length > 0;
}

function buildHeader() {
  $('headerRow').innerHTML = columns.map(([key,label]) => `<th data-key="${key}">${esc(label)}</th>`).join('');
  document.querySelectorAll('th').forEach(th => th.addEventListener('click', () => {
    const key = th.dataset.key;
    if (['source_links'].includes(key)) return;
    if (sortKey === key) sortDir *= -1; else { sortKey = key; sortDir = 1; }
    render();
  }));
}

function populateFilters() {
  const selected = Object.fromEntries(['sourceFilter','programFilter','categoryFilter','eligibilityFilter'].map(id => [id,$(id).value]));
  const sources = [...new Set(allGrants.flatMap(g => (g.sources||[]).map(s => s.source_name)))].sort();
  const programs = [...new Set(allGrants.map(g => g.program).filter(Boolean))].sort();
  $('programFilter').innerHTML = '<option value="">Tutti i programmi</option>' + programs.map(x => `<option>${esc(x)}</option>`).join('');
  const categories = [...new Set(allGrants.map(g => g.category).filter(Boolean))].sort();
  const eligs = [...new Set(allGrants.map(g => g.eligibility_status).filter(Boolean))].sort();
  $('sourceFilter').innerHTML = '<option value="">Tutte le fonti</option>' + sources.map(x => `<option>${esc(x)}</option>`).join('');
  $('categoryFilter').innerHTML = '<option value="">Tutte le categorie</option>' + categories.map(x => `<option>${esc(x)}</option>`).join('');
  $('eligibilityFilter').innerHTML = '<option value="">Tutte le ammissibilità</option>' + eligs.map(x => `<option>${esc(x)}</option>`).join('');
  Object.entries(selected).forEach(([id,value]) => { $(id).value = value; });
}

async function loadData() {
  let gData, sData;
  if (publicMode) {
    const res = await fetch('./data.json', {cache: 'no-store'});
    if (!res.ok) throw new Error('Dati pubblici non disponibili');
    const payload = await res.json();
    gData = payload;
    sData = payload.status;
  } else {
    const [gRes,sRes] = await Promise.all([fetch('/api/grants'), fetch('/api/status')]);
    if (!gRes.ok || !sRes.ok) throw new Error('Dati non disponibili');
    gData = await gRes.json(); sData = await sRes.json();
  }
  const items = gData.items || [];
  const snapshot = JSON.stringify(items);
  if (snapshot !== grantsSnapshot) {
    const viewport = document.querySelector('.table-wrap');
    const {scrollTop, scrollLeft} = viewport;
    allGrants = items;
    populateFilters(); render();
    viewport.scrollTop = scrollTop;
    viewport.scrollLeft = scrollLeft;
    grantsSnapshot = snapshot;
  }
  renderStatus(sData);
  const button = $('refreshBtn');
  button.disabled = sData.refresh_running;
  button.textContent = sData.refresh_running ? 'AGGIORNAMENTO…' : 'AGGIORNA ORA';
  if (publicMode) button.textContent = 'RICARICA DATI';
}

function renderStatus(data) {
  const last = data.latest_refresh?.finished_at || data.latest_refresh?.started_at;
  $('lastRefresh').textContent = last ? new Date(last).toLocaleString('it-IT') : 'mai';
  $('sourceStatus').innerHTML = (data.sources||[]).map(s => `<span class="source-pill ${s.status==='OK'?'ok':s.status==='PARZIALE'?'partial':s.status==='IN CORSO'?'running':'error'}" title="${esc([s.message, s.eligibility_note].filter(Boolean).join(' · '))}">${esc(s.source_name)}: ${esc(s.status)}${['OK','PARZIALE'].includes(s.status) ? ` · ${s.items_seen}` : ''}</span>`).join('');
  $('sheetBtn').hidden = publicMode || !data.google_sheets_enabled;
  $('sourceCount').textContent = (data.sources||[]).length;
}

function toast(msg) { $('toast').textContent = msg; $('toast').hidden = false; setTimeout(() => $('toast').hidden = true, 4500); }

$('refreshBtn').addEventListener('click', async () => {
  const btn = $('refreshBtn'); btn.disabled = true; btn.textContent = 'AGGIORNAMENTO…';
  try {
    if (publicMode) {
      await loadData();
      toast('Dati aggiornati all’ultima versione pubblicata.');
      return;
    }
    const res = await fetch('/api/refresh', {method:'POST'}); const data = await res.json();
    toast(data.message || `Aggiornamento: ${data.status}.`);
    await loadData();
  } catch (e) { toast(`Errore: ${e.message}`); }
  finally { btn.disabled = false; btn.textContent = publicMode ? 'RICARICA DATI' : 'AGGIORNA ORA'; }
});

$('sheetBtn').addEventListener('click', async () => {
  const btn = $('sheetBtn'); btn.disabled = true;
  try {
    const res = await fetch('/api/google-sheets/sync', {method:'POST'}); const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Sync fallita');
    toast(`Google Sheet aggiornato: ${data.rows} righe.`);
  } catch (e) { toast(e.message); }
  finally { btn.disabled = false; }
});

['search','sourceFilter','programFilter','categoryFilter','relevanceFilter','eligibilityFilter','territoryFilter','daysFilter','deadlineFrom','deadlineTo','showExpired']
  .forEach(id => $(id).addEventListener(id === 'search' || id === 'territoryFilter' ? 'input' : 'change', render));

buildHeader();
loadData().catch(e => toast(`Impossibile caricare la dashboard: ${e.message}`));

setInterval(() => loadData().catch(() => {}), publicMode ? 60000 : 5000);
