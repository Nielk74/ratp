'use strict';

const geocoder = require('./geocoder');
const bff = require('./bff');

// Cache: "LIG:IDFM:C01742|gare du nord" → [{ transitId, directionId, directionName }]
const transitIdCache = new Map();

// Inflight cache: prevents concurrent calls for the same key from firing duplicate requests
const inflightCache = new Map();

// A fixed destination near the center of Paris used for dummy itinerary planning
const DUMMY_DEST = { lat: 48.8584, lng: 2.2945 }; // Tour Eiffel

function cacheKey(lineId, stopName) {
  return `${lineId}|${stopName.toLowerCase().trim()}`;
}

// Extract all transit segments matching a lineId from itinerary events
function extractTransitSegments(events, lineId) {
  const segments = [];
  const segmentTypes = ['RAIL_SEGMENT', 'METRO_SEGMENT', 'BUS_SEGMENT', 'TRAM_SEGMENT', 'CABLE_SEGMENT'];

  for (const event of events) {
    for (const itinerary of (event.itineraries || [])) {
      for (const step of (itinerary.steps || [])) {
        if (!segmentTypes.includes(step.stepType)) continue;
        if (!step.transit) continue;
        if (step.transit.lineId !== lineId) continue;

        segments.push({
          transitId: step.transit.id,
          directionId: step.transit.directionId,
          directionName: step.transit.directionNameLabels?.displayName || ''
        });
      }
    }
  }

  return segments;
}

async function resolveTransitIds(lineId, stopName) {
  const key = cacheKey(lineId, stopName);
  if (transitIdCache.has(key)) return transitIdCache.get(key);

  // Coalesce concurrent callers for the same key onto a single in-flight promise
  if (inflightCache.has(key)) return inflightCache.get(key);

  const promise = (async () => {
    // Geocode the stop name to coordinates
    const stopCoord = await geocoder.toCoord(stopName);

    // Plan a dummy itinerary FROM the stop TO the fixed destination
    // This forces the BFF to route through that stop on matching lines
    const events = await bff.streamItinerary({
      origin: { latitude: stopCoord.lat, longitude: stopCoord.lng },
      destination: { latitude: DUMMY_DEST.lat, longitude: DUMMY_DEST.lng },
      withReducedMobility: false,
      excludedLinesIds: [],
      excludedStationsIds: [],
      transportModes: ['RER', 'TRANSILIEN', 'METRO', 'BUS', 'TRAM', 'WALK']
    });

    const segments = extractTransitSegments(events, lineId);

    // Deduplicate by directionId
    const seen = new Set();
    const unique = segments.filter(s => {
      if (seen.has(s.directionId)) return false;
      seen.add(s.directionId);
      return true;
    });

    // Always cache the result, even when empty, to avoid repeated BFF calls
    transitIdCache.set(key, unique);

    return unique;
  })();

  inflightCache.set(key, promise);
  try {
    return await promise;
  } finally {
    inflightCache.delete(key);
  }
}

// Find the best matching transitId given an optional direction hint
function pickDirection(segments, directionHint) {
  if (!directionHint || segments.length === 0) return segments[0] || null;

  const hint = directionHint.toLowerCase().trim();
  const match = segments.find(s =>
    s.directionName.toLowerCase().includes(hint)
  );
  return match || segments[0];
}

async function getTransitId(lineId, stopName, directionHint = null) {
  const segments = await resolveTransitIds(lineId, stopName);
  if (segments.length === 0) return null;
  return pickDirection(segments, directionHint);
}

function clearCache() {
  transitIdCache.clear();
  inflightCache.clear();
}

module.exports = { getTransitId, clearCache, extractTransitSegments };
