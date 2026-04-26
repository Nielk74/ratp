// tests/bff.test.js
const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');

const browser = require('../lib/browser');
const bff = require('../lib/bff');

before(async () => {
  await browser.start();
});

after(async () => {
  await browser.stop();
});

test('bff.getProviders returns array with id field', async () => {
  const providers = await bff.getProviders();
  assert.ok(Array.isArray(providers), 'should be array');
  assert.ok(providers.length > 0, 'should have entries');
  assert.ok(providers[0].id, 'each entry should have id');
});

test('bff.getLineSituations returns array', async () => {
  const situations = await bff.getLineSituations();
  assert.ok(Array.isArray(situations), 'should be array');
});

test('bff.parseSSE extracts data events', () => {
  const raw = [
    'id:abc',
    'event:data',
    'data:{"hello":"world"}',
    '',
    'id:def',
    'event:data',
    'data:{"foo":"bar"}'
  ].join('\n');
  const events = bff.parseSSE(raw);
  assert.deepEqual(events, [{ hello: 'world' }, { foo: 'bar' }]);
});

test('bff.parseSSE skips malformed lines', () => {
  const raw = 'data:{"ok":true}\ndata:not-json\ndata:{"also":"ok"}';
  const events = bff.parseSSE(raw);
  assert.equal(events.length, 2);
  assert.deepEqual(events[0], { ok: true });
  assert.deepEqual(events[1], { also: 'ok' });
});
