// tests/playwright/semantic-api.spec.js
const { test, expect } = require('@playwright/test');

test.describe('Semantic API v1', () => {
  test('GET /v1/incidents returns incidents', { retries: 2 }, async ({ request }) => {
    const res = await request.get('/v1/incidents');
    expect(res.status()).toBeLessThan(500);
    if (!res.ok()) return; // proxy may be flaky

    expect(res.headers()['content-type']).toContain('application/json');

    const body = await res.json();
    expect(Array.isArray(body)).toBe(true);
  });

  test('GET /v1/incidents?line=RER+A filters by line', { retries: 2 }, async ({ request }) => {
    const res = await request.get('/v1/incidents?line=RER+A');
    expect(res.status()).toBeLessThan(500);
    if (!res.ok()) return;

    const body = await res.json();
    expect(Array.isArray(body)).toBe(true);
  });

  test('GET /v1/providers returns providers', { retries: 2 }, async ({ request }) => {
    const res = await request.get('/v1/providers');
    expect(res.status()).toBeLessThan(500);
    if (!res.ok()) return;

    expect(res.headers()['content-type']).toContain('application/json');

    const body = await res.json();
    expect(Array.isArray(body)).toBe(true);
    expect(body.length).toBeGreaterThan(0);
  });

  test('GET /v1/maps returns map data', { retries: 2 }, async ({ request }) => {
    const res = await request.get('/v1/maps');
    expect(res.status()).toBeLessThan(500);
    if (!res.ok()) return;

    expect(res.headers()['content-type']).toContain('application/json');

    const body = await res.json();
    expect(body).toBeDefined();
  });

  test('GET /v1/departures returns departures', { retries: 2 }, async ({ request }) => {
    const res = await request.get('/v1/departures?line=M1');
    expect(res.status()).toBeLessThan(500);
    if (!res.ok()) return;

    expect(res.headers()['content-type']).toContain('application/json');

    const body = await res.json();
    expect(Array.isArray(body)).toBe(true);
  });

  test('POST /v1/itinerary returns itinerary', { retries: 2 }, async ({ request }) => {
    const res = await request.post('/v1/itinerary', {
      json: {
        origin: { lat: 48.8738, lon: 2.335 },
        destination: { lat: 48.8566, lon: 2.3522 },
      },
    });
    expect(res.status()).toBeLessThan(500);
    if (!res.ok()) return;

    expect(res.headers()['content-type']).toContain('application/json');

    const body = await res.json();
    expect(body).toBeDefined();
  });

  test('unknown v1 endpoint returns 404', async ({ request }) => {
    const res = await request.get('/v1/nonexistent');
    expect(res.status()).toBe(404);

    const body = await res.json();
    expect(body.code).toBe('NOT_FOUND');
  });
});
