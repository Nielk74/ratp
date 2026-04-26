'use strict';
const bff = require('../lib/bff');

async function handleProviders(req, res) {
  const raw = await bff.getProviders();

  const result = raw.map(p => ({
    id: p.id,
    name: p.name,
    color: p.color || null,
    iconUrl: p.assets?.icon?.svg || p.assets?.icon?.png || null,
    logoUrl: p.assets?.logo?.svg || p.assets?.logo?.png || null
  }));

  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(result));
}

module.exports = { handleProviders };
