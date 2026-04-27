// tests/playwright/api.spec.js
const { test, expect } = require('@playwright/test');

test.describe('API Endpoints', () => {
  test('GET /api/spec returns OpenAPI YAML', async ({ request }) => {
    const res = await request.get('/api/spec');
    expect(res.ok()).toBeTruthy();
    expect(res.headers()['content-type']).toContain('application/yaml');

    const text = await res.text();
    expect(text).toContain('openapi:');
  });

  test('GET /api/config returns configuration', async ({ request }) => {
    const res = await request.get('/api/config');
    expect(res.ok()).toBeTruthy();
    expect(res.headers()['content-type']).toContain('application/json');

    const body = await res.json();
    expect(body).toBeDefined();
  });

  test('GET /api/keys returns API keys', async ({ request }) => {
    const res = await request.get('/api/keys');
    expect(res.ok()).toBeTruthy();
    expect(res.headers()['content-type']).toContain('application/json');

    const body = await res.json();
    expect(body.bffExternalApiKey).toBeDefined();
    expect(body.bffExternalApiKey.length).toBeGreaterThan(0);
  });

  test('CORS headers are present on all API responses', async ({ request }) => {
    const endpoints = ['/api/test', '/api/config', '/api/keys'];
    for (const endpoint of endpoints) {
      const res = await request.get(endpoint);
      expect(res.headers()['access-control-allow-origin']).toBe('*');
    }
  });

  test('OPTIONS preflight returns 204', async ({ request }) => {
    const res = await request.fetch('/api/test', { method: 'OPTIONS' });
    expect(res.status()).toBe(204);
  });
});
