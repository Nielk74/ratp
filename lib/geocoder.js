'use strict';

const https = require('https');

// Île-de-France bounding box for Nominatim viewbox bias
const IDF_VIEWBOX = '1.4,49.3,3.6,48.0'; // minLon,maxLat,maxLon,minLat

function isCoord(input) {
  return (
    input !== null &&
    typeof input === 'object' &&
    typeof input.lat === 'number' &&
    typeof input.lng === 'number' &&
    isFinite(input.lat) &&
    isFinite(input.lng)
  );
}

function nominatimFetch(address) {
  return new Promise((resolve, reject) => {
    const params = new URLSearchParams({
      q: address,
      format: 'json',
      limit: '1',
      viewbox: IDF_VIEWBOX,
      bounded: '0' // viewbox is a preference, not a hard filter
    });
    const options = {
      hostname: 'nominatim.openstreetmap.org',
      path: '/search?' + params.toString(),
      method: 'GET',
      headers: {
        'User-Agent': 'ratp-api/1.0 (transit info tool)',
        'Accept-Language': 'fr'
      },
      timeout: 8000
    };
    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        if (res.statusCode !== 200) {
          reject(new Error(`Nominatim HTTP ${res.statusCode}`));
          return;
        }
        try { resolve(JSON.parse(data)); }
        catch { reject(new Error('Nominatim response parse error')); }
      });
    });
    req.on('error', reject);
    req.on('timeout', () => { req.destroy(); reject(new Error('Nominatim timeout')); });
    req.end();
  });
}

async function toCoord(input) {
  if (isCoord(input)) return input;

  if (typeof input !== 'string' || !input.trim()) {
    throw new Error(`Invalid location: expected {lat, lng} or address string, got ${JSON.stringify(input)}`);
  }

  const results = await nominatimFetch(input.trim());
  if (!results || results.length === 0) {
    throw new Error(`Location not found: "${input}"`);
  }

  const lat = parseFloat(results[0].lat);
  const lng = parseFloat(results[0].lon);
  if (isNaN(lat) || isNaN(lng)) {
    throw new Error(`Nominatim returned invalid coordinates for "${input}"`);
  }
  return { lat, lng };
}

module.exports = { isCoord, toCoord };
