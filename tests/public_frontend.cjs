// Smoke-test both data sources without requiring a browser or network.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');

async function check(publicMode) {
  const nodes = new Map();
  const get = id => {
    if (!nodes.has(id)) nodes.set(id, {
      value: '', checked: false, scrollTop: 37, scrollLeft: 52,
      addEventListener(type, fn) { this[type] = fn; }, innerHTML: ''
    });
    return nodes.get(id);
  };
  const calls = [];
  const payload = {items: [{title: 'Bando', relevance_level: 'ALTA', relevance_score: 95}],
    status: {sources: [], refresh_running: false, google_sheets_enabled: true}};
  const context = {
    document: {body: {dataset: {public: String(publicMode)}},
      getElementById: get, querySelector: () => get('viewport'), querySelectorAll: () => []},
    fetch: async url => {
      calls.push(url);
      return {ok: true, json: async () => url === './data.json' ? payload :
        url === '/api/grants' ? {items: payload.items} : payload.status};
    },
    setInterval() {}, setTimeout() {}
  };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync('frontend/app.js', 'utf8'), context);
  await new Promise(resolve => setImmediate(resolve));
  assert.deepEqual(calls, publicMode ? ['./data.json'] : ['/api/grants', '/api/status']);
  assert(get('tableBody').innerHTML.includes('Bando'));
  assert.equal(get('viewport').scrollTop, 37);
  assert.equal(get('viewport').scrollLeft, 52);
  if (publicMode) {
    assert.equal(get('refreshBtn').textContent, 'RICARICA DATI');
    assert.equal(get('sheetBtn').hidden, true);
    calls.length = 0;
    await get('refreshBtn').click();
    assert.deepEqual(calls, ['./data.json']);
  }
}
(async () => {
  await check(true);
  await check(false);
  console.log('Public and local frontend checks passed');
})().catch(error => { console.error(error); process.exit(1); });
