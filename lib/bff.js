'use strict';

const browser = require('./browser');

const BFF_URL = 'https://bff.bonjour-ratp.fr';
const WWW_URL = 'https://www.bonjour-ratp.fr';
const CLIENT_VERSION = '9.11.0';

const ACCEPT_MAP = {
  '/itineraries/stream': 'application/vnd.rss.bff.itinerary-stream.v9+json',
  '/next-stops/preview/batch': 'application/vnd.rss.bff.next-stop-preview-batch.v1+json',
  '/lines/situations': 'application/vnd.rss.bff.lines-situations.v5+json',
  '/itineraries/providers': 'application/vnd.rss.bff.itineraries-providers.v1+json',
  '/maps': 'application/vnd.rss.bff.maps.v3+json'
};

function bffHeaders(path) {
  const cfg = browser.getConfig();
  const acceptKey = Object.keys(ACCEPT_MAP).find(p => path.startsWith(p));
  return {
    'x-api-key': cfg.bffExternalApiKey,
    'x-client-platform': 'bonjour_web',
    'x-client-version': CLIENT_VERSION,
    'x-client-locale': 'fr_FR',
    'x-client-guid': 'bonjour-web-guid',
    'Accept-Language': 'fr',
    'Origin': WWW_URL,
    'Referer': WWW_URL + '/',
    ...(acceptKey ? { 'Accept': ACCEPT_MAP[acceptKey] } : {})
  };
}

function handleCloudflareBlock(status) {
  if (status === 403 || status === 429) {
    try {
      const proxy = require('./proxy');
      const browser = require('./browser');
      const deadUrl = browser.getCurrentProxyUrl();
      if (deadUrl) proxy.markDead(deadUrl);
    } catch (e) {
      console.warn('[bff] Failed to mark proxy dead:', e.message);
    }
    const err = new Error(`Cloudflare blocked (${status})`);
    err.code = 'CF_BLOCKED';
    err.status = status;
    throw err;
  }
}

function parseJSON(raw, endpoint) {
  try {
    return JSON.parse(raw);
  } catch {
    const err = new Error(`Invalid JSON from ${endpoint}: ${raw.substring(0, 100)}`);
    err.code = 'BFF_PARSE_ERROR';
    throw err;
  }
}

async function request(method, path, body = null, query = {}) {
  const params = new URLSearchParams(query).toString();
  const url = BFF_URL + path + (params ? '?' + params : '');
  const headers = bffHeaders(path);
  if (body) headers['Content-Type'] = 'application/json; charset=utf-8';

  const result = await browser.evaluate(async (args) => {
    const opts = { method: args.method, headers: args.headers, mode: 'cors', credentials: 'omit' };
    if (args.body) opts.body = args.body;
    const r = await fetch(args.url, opts);
    return { status: r.status, body: await r.text() };
  }, { url, method, headers, body: body ? JSON.stringify(body) : null });

  handleCloudflareBlock(result.status);

  if (result.status >= 400) {
    const err = new Error(`BFF error ${result.status}: ${result.body.substring(0, 200)}`);
    err.code = 'BFF_ERROR';
    err.status = result.status;
    err.body = result.body;
    throw err;
  }

  return result.body;
}

function parseSSE(text) {
  const events = [];
  for (const line of text.split('\n')) {
    if (!line.startsWith('data:')) continue;
    try { events.push(JSON.parse(line.slice(5).trim())); }
    catch (e) { console.warn('[bff] SSE parse skip:', line.slice(0, 80)); }
  }
  return events;
}

async function getLineSituations(lineId = '') {
  const raw = await request('GET', '/lines/situations', null, lineId ? { lineId } : {});
  return parseJSON(raw, '/lines/situations');
}

async function getProviders() {
  const raw = await request('GET', '/itineraries/providers');
  return parseJSON(raw, '/itineraries/providers');
}

async function getMaps(bbox = null) {
  const raw = await request('GET', '/maps', null, bbox ? { bbox } : {});
  return parseJSON(raw, '/maps');
}

async function streamItinerary(body) {
  const raw = await request('POST', '/itineraries/stream', body);
  return parseSSE(raw);
}

async function getNextStops(transitRequests) {
  const raw = await request('POST', '/next-stops/preview/batch', { requests: transitRequests });
  return parseJSON(raw, '/next-stops/preview/batch');
}

module.exports = {
  parseSSE,
  getLineSituations,
  getProviders,
  getMaps,
  streamItinerary,
  getNextStops
};
