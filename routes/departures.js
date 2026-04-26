'use strict';
const bff = require('../lib/bff');
const lines = require('../lib/lines');
const stops = require('../lib/stops');

function normalizeStatus(s) {
  if (!s) return 'UNKNOWN';
  if (s === 'AVAILABLE_WAITING_TIME') return 'ON_TIME';
  return s;
}

async function handleDepartures(req, res, parsedUrl) {
  const lineParam = parsedUrl.searchParams.get('line');
  const stopParam = parsedUrl.searchParams.get('stop');
  const directionParam = parsedUrl.searchParams.get('direction') || null;

  if (!lineParam || !stopParam) {
    res.writeHead(400, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      error: 'Both "line" and "stop" query parameters are required',
      code: 'INVALID_INPUT'
    }));
    return;
  }

  const lineId = lines.resolve(lineParam);
  if (!lineId) {
    res.writeHead(404, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: `Line not found: "${lineParam}"`, code: 'NOT_FOUND' }));
    return;
  }

  const segment = await stops.getTransitId(lineId, stopParam, directionParam);
  if (!segment) {
    res.writeHead(404, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      error: `Stop not found: "${stopParam}" for line ${lineParam}`,
      code: 'NOT_FOUND'
    }));
    return;
  }

  const now = new Date().toISOString();
  const response = await bff.getNextStops([{ transitId: segment.transitId, startDate: now }]);

  const nextStops = response.transitsNextStops?.[0];
  const realTime = nextStops?.realTimeNextStops || [];
  const theoretical = nextStops?.theoreticalNextStops || [];
  const all = [...realTime, ...theoretical];

  const result = all.map(s => ({
    destination: s.destinationName?.displayName || '',
    waitMinutes: typeof s.waitingTimeInMinutes === 'number' ? s.waitingTimeInMinutes : null,
    scheduledAt: s.dateTime || null,
    status: normalizeStatus(s.status),
    servicePattern: s.servicePatternName || null
  }));

  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(result));
}

module.exports = { handleDepartures };
