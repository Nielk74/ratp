'use strict';

const bff = require('./bff');

// name → lineId map, populated on startup
let nameMap = new Map(); // "rer-a" → "LIG:IDFM:C01742"
let codeMap = new Map(); // "a" → "LIG:IDFM:C01742" (short codes, mode-agnostic)

const MODE_ALIASES = {
  'métro': 'metro',
  'metro': 'metro',
  'rer': 'rer',
  'transilien': 'transilien',
  'tram': 'tram',
  'tramway': 'tram',
  'bus': 'bus',
  'cable': 'cable'
};

const BFF_MODE_MAP = {
  'METRO': 'metro',
  'RER': 'rer',
  'TRANSILIEN': 'transilien',
  'TRAM': 'tram',
  'BUS': 'bus',
  'CABLE': 'cable'
};

function normalizeName(input) {
  const lower = input.toLowerCase().trim()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/\s+/g, ' ');

  // Try "MODE CODE" pattern
  const match = lower.match(/^(métro|metro|rer|transilien|tram(?:way)?|bus|cable)\s+(.+)$/);
  if (match) {
    const mode = MODE_ALIASES[match[1]] || match[1];
    const code = match[2].trim();
    return `${mode}-${code}`;
  }

  return lower.replace(/\s+/g, '-');
}

function buildMap(situations) {
  if (!Array.isArray(situations)) {
    throw new Error(`buildMap expected array, got ${typeof situations}`);
  }

  nameMap.clear();
  codeMap.clear();

  for (const s of situations) {
    const line = s.line;
    if (!line || !line.id) continue;

    const mode = BFF_MODE_MAP[line.businessMode] || line.businessMode?.toLowerCase();
    const code = line.displayCode?.toLowerCase();
    if (!mode || !code) continue;

    const key = `${mode}-${code}`;
    nameMap.set(key, line.id);

    // Also register short code (mode-agnostic) — last write wins for ambiguous codes
    codeMap.set(code, line.id);
  }
}

function resolve(input) {
  if (!input) return null;

  const key = normalizeName(input);
  if (nameMap.has(key)) return nameMap.get(key);

  // Fallback: try pure code (e.g. "A" → RER A, "1" → Metro 1)
  const code = input.toLowerCase().trim();
  if (codeMap.has(code)) return codeMap.get(code);

  return null;
}

async function init() {
  const situations = await bff.getLineSituations();
  buildMap(situations);
  console.log(`[lines] Built map for ${nameMap.size} lines`);
}

module.exports = { normalizeName, buildMap, resolve, init };
