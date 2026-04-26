# RATP Semantic REST API — Design Spec

**Date:** 2026-04-25
**Status:** Approved

---

## Goal

Build a clean semantic REST API on top of the existing Playwright-based BFF proxy. Callers never touch raw BFF concepts (Cloudflare bypass, vendor Accept headers, SSE streams, Base64 transitIds, IDFM line IDs). They speak plain French transit vocabulary; the API handles everything else.

---

## Endpoints

All semantic routes are under `/v1/`. The existing `/api/proxy` and Scalar UI (`/`) remain unchanged.

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/v1/incidents` | All disruptions, or filtered by `?line=RER+A` |
| `POST` | `/v1/itinerary` | Journey planning — accepts addresses or coordinates |
| `GET` | `/v1/departures` | Next departures at a stop — accepts `?line=RER+A&stop=Gare+du+Nord&direction=Boissy` |
| `GET` | `/v1/providers` | Mobility providers (Vélib, Dott, Lime) |
| `GET` | `/v1/maps` | Transit maps, optional `?bbox=minLon,minLat,maxLon,maxLat` |

---

## Input Abstraction

### Line Resolver (`lib/lines.js`)
On startup, fetches all lines from `/lines/situations` (empty query returns every line) and builds an in-memory lookup:
- `"RER A"` → `LIG:IDFM:C01742`
- `"Metro 1"` → `LIG:IDFM:C01569`
- etc.

Matching is case-insensitive, ignores accents, accepts both `"RER A"` and `"A"` for RER lines or `"Metro 1"` and `"1"` for metro lines. Refreshed alongside config (every 5 min in background).

### Geocoder (`lib/geocoder.js`)
For `/v1/itinerary`, `from` and `to` accept either:
- `{ "lat": 48.88, "lng": 2.35 }` — used directly
- `"Gare du Nord, Paris"` — resolved via Nominatim (OpenStreetMap, free, no API key), biased to Île-de-France bounding box

### Stops Dataset (`lib/stops.js`)
A bundled static JSON of major IDFM stops (~500 entries) with `name`, `stopAreaId`, `stopPlaceId`, and associated `lineIds`. Used by `/v1/departures` to resolve `stop=Gare+du+Nord` into the correct `stopAreaId`/`stopPlaceId` for the given line and direction. Fuzzy name matching (lowercase, strip accents, partial match).

---

## Request & Response Shapes

### `GET /v1/incidents?line=RER+A`

`line` is optional. Omit to get all lines.

```json
[
  {
    "line": "RER A",
    "mode": "RER",
    "severity": "HIGH",
    "status": "STOPPED",
    "color": "#FF1400",
    "iconUrl": "https://assets-bff.bonjour-ratp.fr/pictograms/svg/LIG:IDFM:C01742.svg"
  }
]
```

### `POST /v1/itinerary`

Request:
```json
{
  "from": "Gare du Nord, Paris",
  "to": { "lat": 48.8584, "lng": 2.2945 },
  "modes": ["METRO", "BUS", "WALK"],
  "datetime": "2026-04-25T14:00:00Z",
  "accessibility": false
}
```
`modes` defaults to all. `datetime` defaults to now. `accessibility` defaults to false.

The BFF returns an SSE stream — this is consumed server-side and buffered into a single JSON response. The caller never sees the stream.

Response:
```json
{
  "sections": ["PUBLIC_TRANSIT", "ALTERNATIVE"],
  "itineraries": [
    {
      "durationMinutes": 32,
      "modes": ["METRO", "WALK"],
      "steps": [
        {
          "type": "BOARD",
          "line": "Metro 4",
          "from": "Gare du Nord",
          "to": "Châtelet",
          "departAt": "2026-04-25T14:08:00Z",
          "arriveAt": "2026-04-25T14:15:00Z"
        }
      ]
    }
  ]
}
```

### `GET /v1/departures?line=RER+A&stop=Gare+du+Nord&direction=Boissy`

`direction` is optional. Without it, returns departures for all directions.

```json
[
  {
    "destination": "Boissy-Saint-Léger",
    "waitMinutes": 5,
    "scheduledAt": "2026-04-25T14:36:44Z",
    "status": "ON_TIME"
  }
]
```

If stop cannot be resolved from the static dataset, returns `404 { "error": "Stop not found: Gare du Nord for line RER A" }`.

### `GET /v1/providers`

```json
[
  {
    "id": "DOTT",
    "name": "Dott",
    "color": "#00A8E9",
    "iconUrl": "https://assets-b2c.bonjour-ratp.fr/public/icon_dott.svg",
    "logoUrl": "https://assets-b2c.bonjour-ratp.fr/public/logo_dott.svg"
  }
]
```

### `GET /v1/maps?bbox=2.0,48.7,2.5,49.0`

`bbox` is optional.

```json
[
  {
    "name": "Plan du réseau régional des transports",
    "shortName": "Train et Métro",
    "type": "REGIONAL",
    "pdfUrl": "https://assets-web.bonjour-ratp.fr/PLAN_REGION_2025_12_06_12_2025_adee59ba82.pdf",
    "pngUrl": "https://assets-web.bonjour-ratp.fr/PLAN_REGION_2025_12_06_12_2025_a6811a08e0.png",
    "webpUrl": "https://assets-web.bonjour-ratp.fr/PLAN_REGION_2025_12_06_12_2025_615ba0f39c.webp"
  }
]
```

---

## Error Responses

All errors follow RFC 7807:
```json
{ "error": "human-readable message", "code": "MACHINE_CODE" }
```

| HTTP | Code | Meaning |
|------|------|---------|
| 400 | `INVALID_INPUT` | Missing/invalid parameter |
| 404 | `NOT_FOUND` | Line or stop not found |
| 502 | `BFF_ERROR` | BFF returned an error |
| 503 | `BROWSER_UNAVAILABLE` | Browser restarting, retry |

---

## File Structure

```
ratp/
├── server.js              ← thin HTTP router (add /v1/* delegation)
├── lib/
│   ├── browser.js         ← Playwright management (extracted from server.js)
│   ├── bff.js             ← raw BFF calls, header injection, SSE buffering
│   ├── lines.js           ← line name → IDFM ID resolver
│   ├── geocoder.js        ← address string → {lat, lng} via Nominatim
│   ├── stops.js           ← static stops dataset + fuzzy matching
│   └── proxy.js           ← proxy pool management
└── routes/
    ├── incidents.js
    ├── itinerary.js
    ├── departures.js
    ├── providers.js
    └── maps.js
```

---

## Backend Workflow

```
HTTP Request
     │
     ▼
┌─────────────────────────────────────────┐
│              server.js                  │
│           (HTTP router)                 │
└──────┬──────────────────────────────────┘
       │
       ├─ /v1/* ──► routes/*.js
       │               │
       │               ├─ Parse & validate input
       │               ├─ Resolve line names  ◄── lib/lines.js (cached)
       │               ├─ Geocode addresses   ◄── lib/geocoder.js (Nominatim)
       │               ├─ Resolve stops       ◄── lib/stops.js (static dataset)
       │               ├─ Call lib/bff.js
       │               └─ Normalize & return JSON
       │
       └─ /api/proxy, / ──► existing proxy + Scalar UI (unchanged)

lib/bff.js
  → always injects required BFF headers (x-api-key, x-client-*, etc.)
  → consumes SSE streams, buffers into plain JSON
  → delegates fetch to lib/browser.js

lib/browser.js
  → page.evaluate(() => fetch(...)) through headless Chromium
  → on failure: detect crash → restart browser (max 3 attempts, exponential backoff)
  → on Cloudflare 403/429: rotate to next proxy from lib/proxy.js
  → fallback chain: proxy → next proxy → direct (no proxy) → 503

lib/proxy.js  (startup + background refresh every 10 min)
  → fetch candidate list from 2-3 free proxy sources
  → test all concurrently (cap 50 parallel, 3s timeout each)
  → rank by latency, keep top N working
  → expose getProxy() / markDead(proxy)
```

---

## Startup Sequence

1. `proxy.js` — fetch + test proxy pool, pick best
2. `browser.js` — launch Chromium (with best proxy), create proxy page
3. `browser.js` — navigate temp page to `www.bonjour-ratp.fr`, extract `window.__CONFIG__`
4. `lines.js` — call `/lines/situations`, build name→ID map
5. `server.js` — start listening

If proxy pool finds no working proxies → start without proxy (direct mode, verified working).
If config extraction fails → use hardcoded fallback key.
If line map build fails → accept raw IDFM IDs as fallback.

---

## Out of Scope (v1)

- Authentication / rate limiting on the semantic API itself
- WebSocket / SSE passthrough to callers (itinerary is always buffered)
- Stop search beyond the bundled static dataset
- Paid proxy services
