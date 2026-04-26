// tests/lines.test.js
const { test } = require('node:test');
const assert = require('node:assert/strict');
const lines = require('../lib/lines');

test('normalizeName produces consistent keys', () => {
  assert.equal(lines.normalizeName('RER A'), 'rer-a');
  assert.equal(lines.normalizeName('rer a'), 'rer-a');
  assert.equal(lines.normalizeName('Metro 1'), 'metro-1');
  assert.equal(lines.normalizeName('METRO 1'), 'metro-1');
  assert.equal(lines.normalizeName('Tram T3b'), 'tram-t3b');
  assert.equal(lines.normalizeName('Bus 38'), 'bus-38');
  assert.equal(lines.normalizeName('Transilien N'), 'transilien-n');
});

test('resolve returns null for unknown line before init', () => {
  const result = lines.resolve('RER ZZZ');
  assert.equal(result, null);
});

test('buildMap populates resolver from BFF situations data', () => {
  const fakeSituations = [
    { line: { id: 'LIG:IDFM:C01742', displayCode: 'A', businessMode: 'RER' } },
    { line: { id: 'LIG:IDFM:C01569', displayCode: '1', businessMode: 'METRO' } }
  ];
  lines.buildMap(fakeSituations);
  assert.equal(lines.resolve('RER A'), 'LIG:IDFM:C01742');
  assert.equal(lines.resolve('rer a'), 'LIG:IDFM:C01742');
  assert.equal(lines.resolve('Metro 1'), 'LIG:IDFM:C01569');
  assert.equal(lines.resolve('metro 1'), 'LIG:IDFM:C01569');
  assert.equal(lines.resolve('1'), 'LIG:IDFM:C01569'); // short form
  assert.equal(lines.resolve('A'), 'LIG:IDFM:C01742'); // short form
  assert.equal(lines.resolve('RER Z'), null);
});
