'use strict';

const net = require('net');
const https = require('https');
const tls = require('tls');

// SOCKS5 proxies: transparent TCP tunneling, no HTTP inspection, no MITM
const SOURCES = [
  'https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=10000&country=all&ssl=all&anonymity=all',
  'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt'
];
const CONNECT_TIMEOUT = 5000;
const MAX_CONCURRENT = 150;
const REFRESH_INTERVAL = 10 * 60 * 1000;
const POOL_SIZE = 20;
const EARLY_STOP = POOL_SIZE * 2;

const TARGET_HOST = 'bff.bonjour-ratp.fr';
const TARGET_PORT = 443;

let pool = []; // [{ url, latency }]
let poolIndex = 0;
let refreshTimer = null;

function fetchText(url) {
  return new Promise((resolve, reject) => {
    const req = https.get(url, { timeout: 10000 }, (res) => {
      let data = '';
      res.on('data', c => {
        data += c;
        if (data.length > 2 * 1024 * 1024) { req.destroy(); resolve(data); }
      });
      res.on('end', () => resolve(data));
    });
    req.on('error', reject);
    req.on('timeout', () => { req.destroy(); reject(new Error('timeout')); });
  });
}

async function fetchCandidates() {
  const results = await Promise.allSettled(SOURCES.map(fetchText));
  const seen = new Set();
  for (const r of results) {
    if (r.status !== 'fulfilled') continue;
    for (const line of r.value.split('\n')) {
      const l = line.trim();
      if (/^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{2,5}$/.test(l)) seen.add(l);
    }
  }
  return [...seen].map(l => `socks5://${l}`);
}

// SOCKS5 handshake + TLS tunnel test:
// Verifies the proxy can transparently forward HTTPS to bff.bonjour-ratp.fr.
function testProxy(proxyUrl) {
  return new Promise((resolve) => {
    const start = Date.now();
    try {
      const { hostname, port } = new URL(proxyUrl);
      const socket = net.connect(parseInt(port), hostname);
      socket.setTimeout(CONNECT_TIMEOUT);

      let buf = Buffer.alloc(0);
      let step = 0;

      socket.on('connect', () => {
        // Step 0: SOCKS5 greeting — no auth
        socket.write(Buffer.from([0x05, 0x01, 0x00]));
      });

      socket.on('data', (chunk) => {
        buf = Buffer.concat([buf, chunk]);

        if (step === 0 && buf.length >= 2) {
          // Expect: VER=5, METHOD=0 (no auth accepted)
          if (buf[0] !== 0x05 || buf[1] !== 0x00) { socket.destroy(); return resolve(null); }
          step = 1;
          buf = Buffer.alloc(0);
          // Step 1: CONNECT request to target
          const hostBuf = Buffer.from(TARGET_HOST);
          const req = Buffer.alloc(7 + hostBuf.length);
          req[0] = 0x05; req[1] = 0x01; req[2] = 0x00; req[3] = 0x03;
          req[4] = hostBuf.length;
          hostBuf.copy(req, 5);
          req.writeUInt16BE(TARGET_PORT, 5 + hostBuf.length);
          socket.write(req);

        } else if (step === 1 && buf.length >= 4) {
          // Expect: VER=5, REP=0 (success)
          if (buf[0] !== 0x05 || buf[1] !== 0x00) { socket.destroy(); return resolve(null); }
          step = 2;
          // Step 2: TLS handshake through the SOCKS5 tunnel
          const tlsSocket = tls.connect({
            host: TARGET_HOST,
            socket,
            servername: TARGET_HOST,
            rejectUnauthorized: true,
            timeout: CONNECT_TIMEOUT
          });
          tlsSocket.setTimeout(CONNECT_TIMEOUT);
          tlsSocket.on('secureConnect', () => {
            tlsSocket.write(`HEAD / HTTP/1.0\r\nHost: ${TARGET_HOST}\r\nConnection: close\r\n\r\n`);
          });
          tlsSocket.on('data', () => {
            tlsSocket.destroy();
            resolve({ url: proxyUrl, latency: Date.now() - start });
          });
          tlsSocket.on('timeout', () => { tlsSocket.destroy(); resolve(null); });
          tlsSocket.on('error', () => resolve(null));
        }
      });

      socket.on('timeout', () => { socket.destroy(); resolve(null); });
      socket.on('error', () => resolve(null));
    } catch {
      resolve(null);
    }
  });
}

async function testAll(candidates) {
  const working = [];
  for (let i = 0; i < candidates.length; i += MAX_CONCURRENT) {
    if (working.length >= EARLY_STOP) break;
    const batch = candidates.slice(i, i + MAX_CONCURRENT);
    const results = await Promise.all(batch.map(testProxy));
    working.push(...results.filter(Boolean));
  }
  return working.sort((a, b) => a.latency - b.latency);
}

async function refresh() {
  console.log('[proxy] Refreshing pool...');
  try {
    const candidates = await fetchCandidates();
    console.log(`[proxy] Testing ${candidates.length} candidates (max ${MAX_CONCURRENT} parallel, ${CONNECT_TIMEOUT}ms timeout)...`);
    const working = await testAll(candidates);
    pool = working.slice(0, POOL_SIZE);
    console.log(`[proxy] Pool ready: ${pool.length} working proxies`);
    if (pool.length > 0) {
      console.log('[proxy] Fastest:', pool[0].url, `(${pool[0].latency}ms)`);
    }
  } catch (e) {
    console.error('[proxy] Refresh failed:', e.message);
  }
}

async function start() {
  await refresh();
  refreshTimer = setInterval(refresh, REFRESH_INTERVAL);
}

function stop() {
  if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null; }
}

function getProxy() {
  if (pool.length === 0) return null;
  poolIndex = poolIndex % pool.length;
  return pool[poolIndex++];
}

function markDead(proxyUrl) {
  const before = pool.length;
  pool = pool.filter(p => p.url !== proxyUrl);
  console.log(`[proxy] Marked dead: ${proxyUrl} (pool: ${before} → ${pool.length})`);
  if (pool.length === 0) {
    console.warn('[proxy] Pool empty — triggering emergency refresh');
    refresh().catch(e => console.error('[proxy] Emergency refresh failed:', e.message));
  }
}

module.exports = { start, stop, getProxy, markDead, refresh };
