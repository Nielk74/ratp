'use strict';
const bff = require('../lib/bff');
const geocoder = require('../lib/geocoder');

const ALL_MODES = ['RER', 'TRANSILIEN', 'METRO', 'BUS', 'TRAM', 'CABLE', 'BICYCLE', 'SELF_SERVICE_VEHICLE', 'WALK'];
const SEGMENT_TYPES = new Set(['RAIL_SEGMENT', 'METRO_SEGMENT', 'BUS_SEGMENT', 'TRAM_SEGMENT', 'CABLE_SEGMENT', 'BICYCLE_SEGMENT', 'WALK_SEGMENT', 'SELF_SERVICE_VEHICLE_SEGMENT']);

function modeFromSegmentType(type) {
  const map = {
    RAIL_SEGMENT: 'RER/TRANSILIEN',
    METRO_SEGMENT: 'METRO',
    BUS_SEGMENT: 'BUS',
    TRAM_SEGMENT: 'TRAM',
    CABLE_SEGMENT: 'CABLE',
    BICYCLE_SEGMENT: 'BICYCLE',
    WALK_SEGMENT: 'WALK',
    SELF_SERVICE_VEHICLE_SEGMENT: 'SELF_SERVICE_VEHICLE'
  };
  return map[type] || type;
}

function normalizeStep(step) {
  const base = { type: step.stepType };

  if (step.name?.displayName) base.name = step.name.displayName;
  if (step.transit?.lineId) {
    base.lineId = step.transit.lineId;
    base.direction = step.transit.directionNameLabels?.displayName || null;
  }
  if (step.stations?.length) {
    base.from = step.stations[0];
    base.to = step.stations[step.stations.length - 1];
  }
  if (step.departureDateTime) base.departAt = step.departureDateTime;
  if (step.arrivalDateTime) base.arriveAt = step.arrivalDateTime;
  if (step.durationInSeconds) base.durationMinutes = Math.round(step.durationInSeconds / 60);
  if (step.destinationName?.displayName) base.destination = step.destinationName.displayName;
  if (step.cost?.amount) base.cost = { amount: step.cost.amount, currency: step.cost.currency };

  return base;
}

function normalizeItinerary(it) {
  const steps = (it.steps || []).filter(s => SEGMENT_TYPES.has(s.stepType));
  const modes = [...new Set(steps.map(s => modeFromSegmentType(s.stepType)))];

  // Find total duration from the itinerary's own duration field, or sum steps
  const durationInSeconds = it.durationInSeconds
    || (it.steps || []).reduce((sum, s) => sum + (s.durationInSeconds || 0), 0);

  const allSteps = it.steps || [];
  const firstStep = allSteps[0];
  const lastStep = allSteps[allSteps.length - 1];

  return {
    durationMinutes: Math.round(durationInSeconds / 60),
    modes,
    departAt: firstStep?.departureDateTime || firstStep?.dateTime || null,
    arriveAt: lastStep?.arrivalDateTime || lastStep?.dateTime || null,
    steps: steps.map(normalizeStep)
  };
}

async function readBody(req) {
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  return JSON.parse(Buffer.concat(chunks).toString('utf-8'));
}

async function handleItinerary(req, res) {
  let body;
  try {
    body = await readBody(req);
  } catch {
    res.writeHead(400, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Invalid JSON body', code: 'INVALID_INPUT' }));
    return;
  }

  if (!body.from || !body.to) {
    res.writeHead(400, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Both "from" and "to" are required', code: 'INVALID_INPUT' }));
    return;
  }

  const [origin, destination] = await Promise.all([
    geocoder.toCoord(body.from),
    geocoder.toCoord(body.to)
  ]);

  const bffBody = {
    origin: { latitude: origin.lat, longitude: origin.lng },
    destination: { latitude: destination.lat, longitude: destination.lng },
    withReducedMobility: body.accessibility === true,
    excludedLinesIds: [],
    excludedStationsIds: [],
    transportModes: body.modes || ALL_MODES
  };

  if (body.datetime) bffBody.datetime = body.datetime;

  const events = await bff.streamItinerary(bffBody);

  const itineraries = [];
  const sections = new Set();
  for (const event of events) {
    if (event.metadata?.sections) {
      event.metadata.sections.forEach(s => sections.add(s.id));
    }
    if (event.itineraries) {
      itineraries.push(...event.itineraries.map(normalizeItinerary));
    }
  }

  // Deduplicate by durationMinutes+modes signature
  const seen = new Set();
  const unique = itineraries.filter(it => {
    const key = `${it.durationMinutes}-${it.modes.join(',')}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ sections: [...sections], itineraries: unique }));
}

module.exports = { handleItinerary };
