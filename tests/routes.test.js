// tests/routes.test.js
const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');
const http = require('http');
const browser = require('../lib/browser');
const lines = require('../lib/lines');

// Start the server on a test port
let server;
const TEST_PORT = 3299;

before(async () => {
  await browser.start();
  await lines.init();
  // Start a minimal test server with only the v1 routes
  const { createRouter } = require('../routes/index');
  server = http.createServer(createRouter());
  await new Promise(r => server.listen(TEST_PORT, r));
});

after(async () => {
  server.close();
  await browser.stop();
});

function get(path) {
  return new Promise((resolve, reject) => {
    http.get(`http://localhost:${TEST_PORT}${path}`, (res) => {
      let body = '';
      res.on('data', c => body += c);
      res.on('end', () => resolve({ status: res.statusCode, body: JSON.parse(body) }));
    }).on('error', reject);
  });
}

function post(path, body) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const req = http.request({
      hostname: 'localhost', port: TEST_PORT, path, method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) }
    }, (res) => {
      let b = ''; res.on('data', c => b += c);
      res.on('end', () => resolve({ status: res.statusCode, body: JSON.parse(b) }));
    });
    req.on('error', reject);
    req.write(data); req.end();
  });
}

test('GET /v1/incidents returns array', async () => {
  const { status, body } = await get('/v1/incidents');
  assert.equal(status, 200);
  assert.ok(Array.isArray(body), 'body should be array');
});

test('GET /v1/incidents?line=RER+A returns filtered results', async () => {
  const { status, body } = await get('/v1/incidents?line=RER+A');
  assert.equal(status, 200);
  assert.ok(Array.isArray(body));
  if (body.length > 0) {
    assert.equal(body[0].mode, 'RER');
  }
});

test('GET /v1/incidents?line=INVALID returns 404', async () => {
  const { status } = await get('/v1/incidents?line=INVALID+ZZZ');
  assert.equal(status, 404);
});

test('GET /v1/providers returns array with id and iconUrl', async () => {
  const { status, body } = await get('/v1/providers');
  assert.equal(status, 200);
  assert.ok(Array.isArray(body));
  assert.ok(body.length > 0);
  assert.ok(body[0].id, 'should have id');
  assert.ok(body[0].iconUrl, 'should have iconUrl');
});

test('GET /v1/maps returns array with pdfUrl', async () => {
  const { status, body } = await get('/v1/maps');
  assert.equal(status, 200);
  assert.ok(Array.isArray(body));
  assert.ok(body.length > 0);
  assert.ok(body[0].name, 'should have name');
  assert.ok(body[0].pdfUrl || body[0].pngUrl, 'should have at least one URL');
});

test('POST /v1/itinerary with addresses returns itineraries array', async () => {
  const { status, body } = await post('/v1/itinerary', {
    from: 'Gare du Nord, Paris',
    to: 'Tour Eiffel, Paris'
  });
  assert.equal(status, 200);
  assert.ok(Array.isArray(body.itineraries), 'should have itineraries array');
  assert.ok(body.itineraries.length > 0, 'should have at least one itinerary');
  assert.ok(typeof body.itineraries[0].durationMinutes === 'number');
});

test('POST /v1/itinerary with coordinates returns itineraries', async () => {
  const { status, body } = await post('/v1/itinerary', {
    from: { lat: 48.8800, lng: 2.3551 },
    to: { lat: 48.8584, lng: 2.2945 }
  });
  assert.equal(status, 200);
  assert.ok(Array.isArray(body.itineraries));
});

test('POST /v1/itinerary without from returns 400', async () => {
  const { status } = await post('/v1/itinerary', { to: 'Tour Eiffel, Paris' });
  assert.equal(status, 400);
});

test('GET /v1/departures without required params returns 400', async () => {
  const { status } = await get('/v1/departures');
  assert.equal(status, 400);
});

test('GET /v1/departures?line=RER+B&stop=Gare+du+Nord returns array', async () => {
  const { status, body } = await get('/v1/departures?line=RER+B&stop=Gare+du+Nord');
  assert.equal(status, 200);
  assert.ok(Array.isArray(body), 'should be array');
  if (body.length > 0) {
    assert.ok(typeof body[0].destination === 'string');
    assert.ok(typeof body[0].waitMinutes === 'number');
  }
});
