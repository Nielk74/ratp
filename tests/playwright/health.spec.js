// tests/playwright/health.spec.js
const { test, expect } = require('@playwright/test');

test.describe('Health Check', () => {
  test('GET /api/test returns healthy status', async ({ request }) => {
    const res = await request.get('/api/test');
    expect(res.ok()).toBeTruthy();

    const body = await res.json();
    expect(body.status).toBe('ok');
    expect(body.keyPrefix).toMatch(/^[a-zA-Z0-9]{8}\.\.\./);
  });

  test('server responds within reasonable time', async ({ request }) => {
    const startTime = Date.now();
    await request.get('/api/test');
    const elapsed = Date.now() - startTime;
    expect(elapsed).toBeLessThan(5000);
  });
});
