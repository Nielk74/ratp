'use strict';
const { handleIncidents } = require('./incidents');
const { handleProviders } = require('./providers');
const { handleMaps } = require('./maps');
const { handleItinerary } = require('./itinerary');
const { handleDepartures } = require('./departures');

function createRouter() {
  return async function router(req, res) {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Headers', '*');
    res.setHeader('Content-Type', 'application/json');

    if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return; }

    const parsedUrl = new URL(req.url, `http://localhost`);
    const path = parsedUrl.pathname;

    try {
      if (path === '/v1/incidents' && req.method === 'GET') {
        return await handleIncidents(req, res, parsedUrl);
      }
      if (path === '/v1/providers' && req.method === 'GET') {
        return await handleProviders(req, res, parsedUrl);
      }
      if (path === '/v1/maps' && req.method === 'GET') {
        return await handleMaps(req, res, parsedUrl);
      }
      if (path === '/v1/itinerary' && req.method === 'POST') {
        return await handleItinerary(req, res, parsedUrl);
      }
      if (path === '/v1/departures' && req.method === 'GET') {
        return await handleDepartures(req, res, parsedUrl);
      }

      res.writeHead(404, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Not found', code: 'NOT_FOUND' }));
    } catch (err) {
      console.error('[router] Error:', err.message);
      const status = err.status || 500;
      const code = err.code || 'SERVER_ERROR';
      res.writeHead(status, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: err.message, code }));
    }
  };
}

module.exports = { createRouter };
