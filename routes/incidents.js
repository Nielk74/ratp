'use strict';
const bff = require('../lib/bff');
const lines = require('../lib/lines');

async function handleIncidents(req, res, parsedUrl) {
  const lineParam = parsedUrl.searchParams.get('line');
  let lineId = null;

  if (lineParam) {
    lineId = lines.resolve(lineParam);
    if (!lineId) {
      res.writeHead(404, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: `Line not found: "${lineParam}"`, code: 'NOT_FOUND' }));
      return;
    }
  }

  const situations = await bff.getLineSituations(lineId || '');
  const filtered = lineId ? situations.filter(s => s.line?.id === lineId) : situations;

  const result = filtered.map(s => ({
    line: s.line?.displayCode || '',
    mode: s.line?.businessMode || '',
    severity: s.criticity || null,
    status: s.trackingSituation || null,
    color: s.line?.color?.background || null,
    iconUrl: s.line?.assets?.icon?.svg || null
  }));

  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(result));
}

module.exports = { handleIncidents };
