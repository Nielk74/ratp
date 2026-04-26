// tests/geocoder.test.js
const { test } = require('node:test');
const assert = require('node:assert/strict');
const geocoder = require('../lib/geocoder');

test('isCoord returns true for {lat, lng} objects', () => {
  assert.equal(geocoder.isCoord({ lat: 48.8, lng: 2.3 }), true);
  assert.equal(geocoder.isCoord({ lat: 0, lng: 0 }), true);
  assert.equal(geocoder.isCoord('Gare du Nord'), false);
  assert.equal(geocoder.isCoord(null), false);
  assert.equal(geocoder.isCoord({ lat: 48.8 }), false); // missing lng
});

test('toCoord passes through {lat,lng} objects unchanged', async () => {
  const coord = { lat: 48.8800, lng: 2.3551 };
  const result = await geocoder.toCoord(coord);
  assert.deepEqual(result, coord);
});

test('toCoord geocodes "Gare du Nord Paris" to Paris coordinates', async () => {
  const result = await geocoder.toCoord('Gare du Nord Paris');
  assert.ok(result.lat > 48.8 && result.lat < 48.9, 'lat should be near Paris');
  assert.ok(result.lng > 2.3 && result.lng < 2.4, 'lng should be near Paris');
});
