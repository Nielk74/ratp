'use strict';
const http = require('http');
const fs = require('fs');
const path = require('path');

const browser = require('./lib/browser');
const proxy = require('./lib/proxy');
const lines = require('./lib/lines');
const { createRouter } = require('./routes/index');

const PORT = process.env.PORT || 3210;
const BFF_URL = 'https://bff.bonjour-ratp.fr';
const ALLOWED_HOSTS = new Set([
  'bff.bonjour-ratp.fr',
  'www.bonjour-ratp.fr',
  'assets-bff.bonjour-ratp.fr',
  'assets-b2c.bonjour-ratp.fr',
  'assets-web.bonjour-ratp.fr'
]);

const ACCEPT_MAP = {
  '/itineraries/stream': 'application/vnd.rss.bff.itinerary-stream.v9+json',
  '/next-stops/preview/batch': 'application/vnd.rss.bff.next-stop-preview-batch.v1+json',
  '/lines/situations': 'application/vnd.rss.bff.lines-situations.v5+json',
  '/itineraries/providers': 'application/vnd.rss.bff.itineraries-providers.v1+json',
  '/maps': 'application/vnd.rss.bff.maps.v3+json'
};

let specYaml = null;
let specJson = null;

function loadSpec() {
  if (!specYaml) specYaml = fs.readFileSync(path.join(__dirname, 'bff-api.yaml'), 'utf8');
  return specYaml;
}

function loadSpecJson() {
  if (!specJson) {
    specJson = JSON.stringify(require('js-yaml').load(loadSpec()));
  }
  return specJson;
}

function corsHeaders(contentType) {
  const h = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Credentials': 'true',
    'Access-Control-Allow-Headers': '*',
    'Access-Control-Expose-Headers': '*'
  };
  if (contentType) h['Content-Type'] = contentType;
  return h;
}

async function handleProxy(req, res) {
  const reqUrl = new URL(req.url, `http://localhost:${PORT}`);
  const rawTarget = reqUrl.searchParams.get('url');
  const targetUrl = rawTarget || (BFF_URL + reqUrl.pathname.replace(/^\/api\/proxy/, '') + reqUrl.search);

  let targetHost;
  try { targetHost = new URL(targetUrl).hostname; }
  catch {
    res.writeHead(400, corsHeaders('application/json'));
    res.end(JSON.stringify({ error: 'Invalid target URL' }));
    return;
  }

  if (!ALLOWED_HOSTS.has(targetHost)) {
    res.writeHead(403, corsHeaders('application/json'));
    res.end(JSON.stringify({ error: `Host not allowed: ${targetHost}` }));
    return;
  }

  const HOP_BY_HOP = new Set(['host', 'connection', 'keep-alive', 'upgrade', 'proxy-authorization', 'te', 'trailers', 'transfer-encoding']);
  const headers = {};
  for (const [k, v] of Object.entries(req.headers)) {
    if (!HOP_BY_HOP.has(k.toLowerCase())) headers[k] = v;
  }

  const cfg = browser.getConfig();
  headers['x-api-key'] = cfg.bffExternalApiKey;
  headers['x-client-platform'] = 'bonjour_web';
  headers['x-client-version'] = '9.11.0';
  headers['x-client-locale'] = 'fr_FR';
  headers['x-client-guid'] = 'bonjour-web-guid';
  headers['Accept-Language'] = 'fr';
  headers['Origin'] = 'https://www.bonjour-ratp.fr';
  headers['Referer'] = 'https://www.bonjour-ratp.fr/';

  const targetPath = new URL(targetUrl).pathname;
  const acceptKey = Object.keys(ACCEPT_MAP).find(p => targetPath.startsWith(p));
  if (acceptKey && !headers['accept']) headers['accept'] = ACCEPT_MAP[acceptKey];

  let body = null;
  if (req.method === 'POST' || req.method === 'PUT' || req.method === 'PATCH') {
    const chunks = [];
    for await (const chunk of req) chunks.push(chunk);
    body = Buffer.concat(chunks).toString('utf-8');
  }

  const result = await browser.evaluate(async (args) => {
    const opts = { method: args.method, headers: args.headers, mode: 'cors', credentials: 'omit' };
    if (args.body) opts.body = args.body;
    const r = await fetch(args.url, opts);
    return { status: r.status, headers: Object.fromEntries(r.headers.entries()), body: await r.text() };
  }, { url: targetUrl, method: req.method, headers, body });

  const ct = result.headers['content-type'] || 'application/json';
  res.writeHead(result.status, { 'Content-Type': ct.split(';')[0].trim(), ...corsHeaders() });
  res.end(result.body);
}

function buildHtml() {
  const cfg = browser.getConfig();
  const apiKey = cfg.bffExternalApiKey;
  const proxyUrl = `http://localhost:${PORT}/api/proxy`;
  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Bonjour RATP BFF API</title>
</head>
<body>
<div id="app"></div>
<script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference@1.52.3"></script>
<script>
  Scalar.createApiReference("#app", {
    spec: { content: ${loadSpecJson()} },
    proxyUrl: "${proxyUrl}",
    theme: "purple",
    badge: null,
    credentials: "${apiKey}",
    metaData: { title: "Bonjour RATP BFF API", description: "API Documentation" },
  });
</script>
</body>
</html>`;
}

const v1Router = createRouter();

const server = http.createServer(async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Headers', '*');
  res.setHeader('Access-Control-Allow-Credentials', 'true');

  if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return; }

  const { pathname } = new URL(req.url, `http://localhost:${PORT}`);

  if (pathname.startsWith('/v1/')) {
    return v1Router(req, res);
  }

  if (pathname === '/api/proxy' || pathname.startsWith('/api/proxy/')) {
    return handleProxy(req, res).catch(err => {
      console.error('[proxy] Error:', err.message);
      res.writeHead(502, corsHeaders('application/json'));
      res.end(JSON.stringify({ error: err.message }));
    });
  }

  if (pathname === '/api/spec') {
    try {
      res.writeHead(200, { 'Content-Type': 'application/yaml', 'Access-Control-Allow-Origin': '*' });
      return res.end(loadSpec());
    } catch (e) {
      res.writeHead(404); return res.end('Spec file not found');
    }
  }

  if (pathname === '/api/config') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    return res.end(JSON.stringify(browser.getConfig()));
  }

  if (pathname === '/api/keys') {
    const cfg = browser.getConfig();
    const keys = {};
    for (const k of ['bffExternalApiKey', 'mapApiKey', 'ddRumClientToken', 'ddRumAppId']) {
      if (cfg[k]) keys[k] = cfg[k];
    }
    res.writeHead(200, { 'Content-Type': 'application/json' });
    return res.end(JSON.stringify(keys));
  }

  if (pathname === '/api/test') {
    const cfg = browser.getConfig();
    res.writeHead(200, { 'Content-Type': 'application/json' });
    return res.end(JSON.stringify({ status: 'ok', keyPrefix: cfg.bffExternalApiKey.substring(0, 8) + '...' }));
  }

  if (pathname === '/' || pathname === '/index.html') {
    try {
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      return res.end(buildHtml());
    } catch (e) {
      console.error('[server] UI build error:', e.message);
      res.writeHead(500); return res.end('Server error');
    }
  }

  res.writeHead(404); res.end('Not found');
});

async function gracefulShutdown(signal) {
  console.log(`\n[server] ${signal} — shutting down...`);
  server.close();
  proxy.stop();
  await browser.stop();
  process.exit(0);
}

process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));

async function startup() {
  // Wait for proxy pool — mandatory before starting the browser
  await proxy.start();

  // Try each proxy until one successfully completes a live BFF call (lines.init)
  const MAX_PROXY_ATTEMPTS = 5;
  for (let attempt = 1; attempt <= MAX_PROXY_ATTEMPTS; attempt++) {
    const proxyEntry = proxy.getProxy();
    if (!proxyEntry) throw new Error('No working proxies found — cannot start browser safely');

    console.log(`[startup] Trying proxy ${attempt}/${MAX_PROXY_ATTEMPTS}: ${proxyEntry.url}`);
    try {
      await browser.start(proxyEntry.url);
      await lines.init();
      break; // success
    } catch (e) {
      console.error(`[startup] Proxy failed BFF check: ${e.message}`);
      proxy.markDead(proxyEntry.url);
      await browser.stop();
      if (attempt === MAX_PROXY_ATTEMPTS) throw new Error('All proxy attempts failed');
    }
  }

  server.listen(PORT, () => {
    console.log('\n  Bonjour RATP — Semantic API + BFF Proxy\n');
    console.log(`  Semantic API: http://localhost:${PORT}/v1/`);
    console.log(`    GET  /v1/incidents[?line=RER+A]`);
    console.log(`    POST /v1/itinerary`);
    console.log(`    GET  /v1/departures?line=RER+A&stop=Gare+du+Nord`);
    console.log(`    GET  /v1/providers`);
    console.log(`    GET  /v1/maps`);
    console.log(`\n  Scalar UI:   http://localhost:${PORT}/`);
    console.log(`  Raw proxy:   http://localhost:${PORT}/api/proxy?url=...\n`);
  });
}

startup().catch(e => {
  console.error('[server] Startup failed:', e.message);
  process.exit(1);
});
