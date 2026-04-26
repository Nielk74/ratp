'use strict';
const bff = require('../lib/bff');

async function handleMaps(req, res, parsedUrl) {
  const bbox = parsedUrl.searchParams.get('bbox') || null;

  if (bbox && !/^-?\d+\.?\d*,-?\d+\.?\d*,-?\d+\.?\d*,-?\d+\.?\d*$/.test(bbox)) {
    res.writeHead(400, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Invalid bbox format: expected minLon,minLat,maxLon,maxLat', code: 'INVALID_INPUT' }));
    return;
  }

  const raw = await bff.getMaps(bbox);

  const result = raw.map(m => ({
    id: m.id || null,
    name: m.displayName || m.accessibilityName || '',
    shortName: m.shortName || null,
    type: m.type || null,
    pdfUrl: m.url?.pdfLink || null,
    pngUrl: m.url?.pngLink || null,
    webpUrl: m.url?.webpLink || null
  }));

  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(result));
}

module.exports = { handleMaps };
