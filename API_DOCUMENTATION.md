# bonjour-ratp.fr API Documentation

> Reverse-engineered on 2026-04-19 using Playwright browser automation and JS bundle analysis.

---

## 1. INFRASTRUCTURE

### Architecture

```
User Agent → Cloudflare CDN → Varnish Cache → Kong 3.9.0 API Gateway → Next.js Backend
```

| Component | Detail |
|-----------|--------|
| **CDN** | Cloudflare (`server: cloudflare`, `cf-ray` headers) |
| **API Gateway** | Kong 3.9.0 (`via: 1.1 kong/3.9.0`) |
| **Cache** | Varnish (`x-varnish-cache: HIT/MISS`) |
| **Backend** | Next.js App Router (RSC) |
| **SSL/TLS** | HSTS preloaded (`max-age=63072000`) |
| **HTTP/3** | Enabled (`alt-svc: h3=":443"; ma=86400`) |

### Hosts

| Host | Purpose |
|------|---------|
| `www.bonjour-ratp.fr` | Frontend app + CMS endpoints |
| `bff.bonjour-ratp.fr` | Backend-for-Frontend (core transit API) |
| `assets-bff.bonjour-ratp.fr` | Line pictograms (SVG/PNG) |
| `assets-b2c.bonjour-ratp.fr` | Provider logos (Dott, Lime, Vélib') |
| `assets-web.bonjour-ratp.fr` | Static assets (PDF maps, PNGs) |
| `omelette.bonjour-ratp.fr` | Analytics/tracking (GTM) |
| `privacy.bonjour-ratp.fr` | Cookie consent |

---

## 2. AUTHENTICATION

### API Key

```
x-api-key: rHaqHU7laBW3WANbmWUwvrAOoLrdU8pC5aLLkS6e
```

Hardcoded in the website's JavaScript bundles (module `68114`). 40-character alphanumeric string.

### Required Headers (BFF API)

| Header | Value | Purpose |
|--------|-------|---------|
| `x-api-key` | `rHaqHU7laBW3WANbmWUwvrAOoLrdU8pC5aLLkS6e` | API key |
| `x-client-platform` | `bonjour_web` | Client type |
| `x-client-version` | `9.11.0` | App version |
| `x-client-locale` | `fr_FR` | Locale |
| `x-client-guid` | `bonjour-web-guid` | Client GUID |
| `Accept-Language` | `fr` | Language |

### Content Negotiation

All BFF endpoints use vendor-specific media types for versioning:

```
Accept: application/vnd.rss.bff.{endpoint}.v{N}+json
```

Response header: `x-api-version: {N}`

### CORS

| Setting | Value |
|---------|-------|
| `access-control-allow-origin` | `https://www.bonjour-ratp.fr` |
| `access-control-allow-credentials` | `true` |
| `access-control-allow-methods` | `GET, HEAD, PUT, PATCH, POST, DELETE, OPTIONS` |
| `access-control-allow-headers` | `Content-Type, apikey, x-api-key, x-client-guid, x-client-locale, x-client-platform, x-client-version` |

### Error Format (RFC 7807 ProblemDetails)

```json
{
  "statusCode": 404,
  "error": "Not Found",
  "message": "Not Found"
}
```
Content-Type: `application/vnd.rss.bff.problem.v1+json`

---

## 3. WWW API (`www.bonjour-ratp.fr`)

### GET `/api/banner/`

Returns CMS-managed banner/alert content.

**Response (JSON):**
```json
{
  "id": 176,
  "documentId": "nr7r8uq4djkc37yrlits53jr",
  "slug": "alert-empty",
  "content": null,
  "url": null,
  "fontColor": null,
  "backgroundColor": null,
  "scheduleDateTime": "2026-04-09T18:45:00.000Z",
  "hoursUntilNextDisplay": null,
  "createdAt": "2025-03-10T09:45:00.148Z",
  "updatedAt": "2026-04-09T18:50:30.363Z",
  "publishedAt": "2026-04-01T17:20:45.674Z",
  "locale": "fr",
  "isCloseable": null
}
```

### GET `/api/detect-browser/`

Returns a JavaScript snippet for browser fingerprinting.

**Response (JavaScript):**
```javascript
// Chrome 120 => false
```

---

## 4. BFF API (`bff.bonjour-ratp.fr`)

### 4.1 POST `/itineraries/stream` (SSE) ⭐ PRIMARY ENDPOINT

Returns step-by-step journey itineraries as **Server-Sent Events (SSE)**.

**Status:** 200
**Content-Type:** `text/event-stream; charset=utf-8`
**API Version:** v9 (`x-api-version: 9`)
**Encoding:** `identity` (no compression)

**Accept:** `application/vnd.rss.bff.itinerary-stream.v9+json`

**Request Body:**
```json
{
  "origin": { "latitude": 48.88327, "longitude": 2.23349 },
  "destination": { "latitude": 48.80604, longitude": 2.15266 },
  "withReducedMobility": false,
  "excludedLinesIds": [],
  "excludedStationsIds": [],
  "transportModes": [
    "RER", "TRANSILIEN", "METRO", "BUS", "TRAM",
    "CABLE", "BICYCLE", "SELF_SERVICE_VEHICLE", "WALK"
  ]
}
```

**Response Format (SSE):**
```
id:<uuid>
event:data
data:<JSON_PAYLOAD>
```

**JSON Payload Structure:**
```json
{
  "metadata": {
    "uuid": "9eed4d1ab81cd114-CDG",
    "sections": [
      {
        "id": "PUBLIC_TRANSIT",
        "itinerariesIds": ["1"]
      },
      {
        "id": "ALTERNATIVE",
        "title": { "displayName": "Voyager autrement" },
        "itinerariesIds": ["2", "0"]
      }
    ],
    "trackingId": "J|I|E7",
    "editorialConfiguration": {
      "id": "ba4n2amhm0j8uc33uz1ekwk5-337",
      "body": "Récap hebdo : perturbations à venir...",
      "redirectUrl": "https://www.bonjour-ratp.fr/...",
      "isCloseable": true,
      "fontColor": "#000000",
      "backgroundColor": "#FFE866"
    },
    "tags": [
      { "id": "lessWalk", "itineraryId": "1" }
    ],
    "feedbackUrl": "https://form.typeform.com/to/UzwClBCV#..."
  },
  "itineraries": [
    {
      "modes": "walk",
      "steps": [
        {
          "stepType": "ADDRESS_POINT",
          "coordinates": { "latitude": 48.88342, "longitude": 2.2334445 },
          "accessibilityLevel": "UNKNOWN",
          "pictoType": "pin",
          "dateTime": "2026-04-19T16:31:44.000Z",
          "departureDateTime": "2026-04-19T17:09:00.000Z",
          "arrivalDateTime": "2026-04-19T19:50:58.000Z",
          "durationInSeconds": 9720,
          "lengthInKilometers": 12.7,
          "polyline": { "value": "kpjiH_fsLAFCHELz@j@@DUr@..." }
        }
      ]
    }
  ]
}
```

**Itinerary Sections:**
- `PUBLIC_TRANSIT` — Public transit routes
- `ALTERNATIVE` — Alternative modes (walking, cycling)

**Step Types:** `ADDRESS_POINT`, `BOARD`, `GET_OFF`, `WALK`, `BIKE`, etc.

**Polyline:** Google Polyline Algorithm (encoded path). Characters: `ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-`

### 4.2 POST `/next-stops/preview/batch`

Returns real-time next departures for multiple transit queries.

**Status:** 200
**Content-Type:** `application/vnd.rss.bff.next-stop-preview-batch.v1+json`
**API Version:** v1 (`x-api-version: 1`)

**Accept:** `application/vnd.rss.bff.next-stop-preview-batch.v1+json`

**Request Body:**
```json
{
  "requests": [
    {
      "transitId": "eyJsaW5lSWQiOiJMSUc6SURGTTpDMDE3NDAi...",
      "startDate": "2026-04-19T16:34:43.000Z"
    }
  ]
}
```

**Response:**
```json
{
  "transitsNextStops": [
    {
      "transitId": "eyJsaW5lSWQiOiJMSUc6SURGTTpDMDE3NDAi...",
      "realTimeNextStops": [
        {
          "destinationName": {
            "displayName": "Gare de Versailles - Rive Droite",
            "accessibilityName": "Gare de Versailles - Rive Droite"
          },
          "status": "AVAILABLE_WAITING_TIME",
          "servicePatternName": "VOLA",
          "waitingTimeInMinutes": 5,
          "dateTime": "2026-04-19T16:36:44.401Z"
        }
      ],
      "theoreticalNextStops": []
    }
  ]
}
```

**Transit Status Values:**
- `AVAILABLE_WAITING_TIME` — Real-time data available

### 4.3 GET `/lines/situations`

Returns current disruption/crisis situations for all lines (or filtered by `lineId`).

**Accept:** `application/vnd.rss.bff.lines-situations.v5+json`

**Query Parameters:**
| Param | Description |
|-------|-------------|
| `lineId` | Optional — filter by line. Empty = all lines. |

**Response (array of line situations):**
```json
[{
  "line": {
    "id": "LIG:IDFM:C01742",
    "labels": {
      "displayName": "Boissy-Saint-Léger • Marne-la-Vallée Chessy / Cergy le Haut...",
      "accessibilityName": "RER A"
    },
    "displayNamesByWay": ["Boissy-Saint-Léger • Marne-la-Vallée Chessy", "Cergy le Haut..."],
    "displayCode": "A",
    "color": { "background": "#FF1400", "font": "#FFFFFF" },
    "businessMode": "RER",
    "assets": {
      "icon": {
        "svg": "https://assets-bff.bonjour-ratp.fr/pictograms/svg/LIG:IDFM:C01742.svg",
        "png": "https://assets-bff.bonjour-ratp.fr/pictograms/png/LIG:IDFM:C01742@3x.png",
        "name": "LIG:IDFM:C01742"
      }
    },
    "operatorName": "SNCF"
  },
  "pictoType": "critical",
  "outlineColor": "#E32826",
  "outlineWidth": 4,
  "criticity": "HIGH",
  "trackingSituation": "STOPPED"
}]
```

**Situation Fields:**
| Field | Description |
|-------|-------------|
| `pictoType` | `critical` or other |
| `outlineColor` | Crisis outline color |
| `outlineWidth` | Outline width |
| `criticity` | `HIGH`, `MEDIUM`, `LOW` |
| `trackingSituation` | `STOPPED`, `PARTIALLY_STOPPED`, etc. |

### 4.4 GET `/itineraries/providers`

Returns available mobility providers (bike share, e-scooter).

**Accept:** `application/vnd.rss.bff.itineraries-providers.v1+json`

**Response (array):**
```json
[{
  "id": "DOTT",
  "name": "DOTT",
  "color": "#00A8E9",
  "assets": {
    "icon": {
      "name": "icon-provider-DOTT",
      "svg": "https://assets-b2c.bonjour-ratp.fr/public/icon_dott.svg",
      "png": "https://assets-b2c.bonjour-ratp.fr/public/icon_dott.png"
    },
    "logo": {
      "name": "logo-provider-DOTT",
      "svg": "https://assets-b2c.bonjour-ratp.fr/public/logo_dott.svg",
      "png": "https://assets-b2c.bonjour-ratp.fr/public/logo_dott.png"
    },
    "pictoSausage": {
      "name": "pictoSausage-provider-DOTT",
      "svg": "https://assets-b2c.bonjour-ratp.fr/public/logo_full_name_dott.svg",
      "png": "https://assets-b2c.bonjour-ratp.fr/public/logo_full_name_dott.png"
    }
  }
}]
```

**Providers:** `DOTT` (e-scooter), `LIME` (e-scooter), `VELIB_METROPOLE` (bike)

### 4.5 GET `/maps`

Returns regional transit maps (PDF, PNG, WebP).

**Accept:** `application/vnd.rss.bff.maps.v3+json`

**Query Parameters:**
| Param | Description |
|-------|-------------|
| `bbox` | Bounding box: `minLon,minLat,maxLon,maxLat` |

**Response (array):**
```json
[{
  "id": "pmx27jr4ajcy8x8uokep9jtd",
  "displayName": "Plan du réseau régional des transports",
  "accessibilityName": "Plan du réseau régional des transports",
  "shortName": "Train et Métro",
  "type": "REGIONAL",
  "url": {
    "id": "PLAN_REGION_2025-12_06-12-2025.pdf",
    "pdfLink": "https://assets-web.bonjour-ratp.fr/PLAN_REGION_2025_12_06_12_2025_adee59ba82.pdf",
    "pngLink": "https://assets-web.bonjour-ratp.fr/PLAN_REGION_2025_12_06_12_2025_a6811a08e0.png",
    "webpLink": "https://assets-web.bonjour-ratp.fr/PLAN_REGION_2025_12_06_12_2025_615ba0f39c.webp"
  }
}]
```

**Map Types:** `REGIONAL`, `EVENT`

---

## 5. DATA FORMATS

### 5.1 Google Polyline Encoding

`polyline.value` uses Google Polyline Algorithm (encoded path):
- Delta-encoded coordinate differences
- Multiplied by 1e5, base64-varint encoded
- Odd positions = longitude, even positions = latitude
- Character set: `ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-`

**Decoding:** Use `google-polyline` npm package, Python `polyline` library, or similar.

### 5.2 Base64 TransitId

The `transitId` is a Base64-encoded JSON object:

```
eyJsaW5lSWQiOiJMSUc6SURGTTpDMDE3NDAiLCJkaXJlY3Rpb25JZCI6IkRJUjpJREZNOkMwMTc0MDpBIiwic3RvcEFyZWFJZCI6IkxEQTpJREZNOjcxNDIyIiwic3RvcFBsYWNlSWQiOiJBUlQ6SURGTTo0MzE4NCJ9
```

Decodes to:
```json
{
  "lineId": "LIG:IDFM:C01740",
  "directionId": "DIR:IDFM:C01740:A",
  "stopAreaId": "LDA:IDFM:71422",
  "stopPlaceId": "ART:IDFM:43184"
}
```

### 5.3 ID Prefixes

| Prefix | Meaning | Example |
|--------|---------|---------|
| `LIG:IDFM:` | Line (Ligne) | `LIG:IDFM:C01742` (RER A) |
| `DIR:IDFM:` | Direction | `DIR:IDFM:C01740:A` |
| `LDA:IDFM:` | Stop Area | `LDA:IDFM:71422` |
| `ART:IDFM:` | Stop Place | `ART:IDFM:43184` |
| `RI:` | Reference/Itinerary | `ba4n2amhm0j8uc33uz1ekwk5` |

### 5.4 UUIDs

| Context | Format | Example |
|---------|--------|---------|
| Session/Correlation ID | `hex-timestamp-region` | `9eed4d1ab81cd114-CDG` |
| Kong Request ID | UUID v4 | `e3594c4fbd31744a61d9286d6bbf646f` |

---

## 6. TRANSPORT MODES

| Mode ID | Description |
|---------|-------------|
| `RER` | RER (regional express network) |
| `TRANSILIEN` | Transilien (SNCF suburban rails) |
| `METRO` | Metro |
| `BUS` | Bus |
| `TRAM` | Tramway |
| `CABLE` | Cable car (Montmartre Funicular) |
| `BICYCLE` | Bicycle |
| `SELF_SERVICE_VEHICLE` | Vélib', Dott, Lime scooters |
| `WALK` | Walking |

---

## 7. ENDPOINTS SUMMARY

### Working Endpoints

| # | Method | Path | Accept | Status | Description |
|---|--------|------|--------|--------|-------------|
| 1 | POST | `/itineraries/stream` | `...itinerary-stream.v9+json` | **200** | Journey planning (SSE) |
| 2 | POST | `/next-stops/preview/batch` | `...next-stop-preview-batch.v1+json` | **200** | Real-time departures |
| 3 | GET | `/lines/situations?lineId=` | `...lines-situations.v5+json` | **200** | Disruptions |
| 4 | GET | `/itineraries/providers` | `...itineraries-providers.v1+json` | **200** | Mobility providers |
| 5 | GET | `/maps?bbox=...` | `...maps.v3+json` | **200** | Regional maps |
| 6 | GET | `/api/banner/` (www) | `application/json` | **200** | CMS banners |

### Not Implemented / 404

`/lines/search`, `/lines/{lineId}`, `/lines/situations/{lineId}`, `/lines/timetables`, `/stop-places`, `/pois/search`, `/line-maps`, `/next-stops/view`, `/locations`, `/geocode`, `/health`, `/status`

---

## 8. EXAMPLE REQUESTS

### Itinerary Search

```bash
curl -X POST 'https://bff.bonjour-ratp.fr/itineraries/stream' \
  -H 'Accept: application/vnd.rss.bff.itinerary-stream.v9+json' \
  -H 'Content-Type: application/json; charset=utf-8' \
  -H 'x-api-key: rHaqHU7laBW3WANbmWUwvrAOoLrdU8pC5aLLkS6e' \
  -H 'x-client-platform: bonjour_web' \
  -H 'x-client-version: 9.11.0' \
  -H 'x-client-locale: fr_FR' \
  -H 'x-client-guid: bonjour-web-guid' \
  -H 'Origin: https://www.bonjour-ratp.fr' \
  -d '{
    "origin": { "latitude": 48.88327, "longitude": 2.23349 },
    "destination": { "latitude": 48.80604, "longitude": 2.15266 },
    "withReducedMobility": false,
    "excludedLinesIds": [],
    "excludedStationsIds": [],
    "transportModes": ["RER","TRANSILIEN","METRO","BUS","TRAM","CABLE","BICYCLE","SELF_SERVICE_VEHICLE","WALK"]
  }'
```

### Next Stops (Real-Time)

```bash
curl -X POST 'https://bff.bonjour-ratp.fr/next-stops/preview/batch' \
  -H 'Accept: application/vnd.rss.bff.next-stop-preview-batch.v1+json' \
  -H 'Content-Type: application/json' \
  -H 'x-api-key: rHaqHU7laBW3WANbmWUwvrAOoLrdU8pC5aLLkS6e' \
  -H 'x-client-platform: bonjour_web' \
  -H 'x-client-version: 9.11.0' \
  -H 'x-client-locale: fr_FR' \
  -d '{
    "requests": [{
      "transitId": "eyJsaW5lSWQiOiJMSUc6SURGTTpDMDE3NDAiLCJkaXJlY3Rpb25JZCI6IkRJUjpJREZNOkMwMTc0MDpBIiwic3RvcEFyZWFJZCI6IkxEQTpJREZNOjcxNDIyIiwic3RvcFBsYWNlSWQiOiJBUlQ6SURGTTo0MzE4NCJ9",
      "startDate": "2026-04-19T16:34:43.000Z"
    }]
  }'
```

### Lines Disruptions

```bash
curl 'https://bff.bonjour-ratp.fr/lines/situations?lineId=' \
  -H 'Accept: application/vnd.rss.bff.lines-situations.v5+json' \
  -H 'x-api-key: rHaqHU7laBW3WANbmWUwvrAOoLrdU8pC5aLLkS6e' \
  -H 'x-client-platform: bonjour_web' \
  -H 'x-client-version: 9.11.0' \
  -H 'x-client-locale: fr_FR'
```

### Mobility Providers

```bash
curl 'https://bff.bonjour-ratp.fr/itineraries/providers' \
  -H 'Accept: application/vnd.rss.bff.itineraries-providers.v1+json' \
  -H 'x-api-key: rHaqHU7laBW3WANbmWUwvrAOoLrdU8pC5aLLkS6e' \
  -H 'x-client-platform: bonjour_web' \
  -H 'x-client-version: 9.11.0' \
  -H 'x-client-locale: fr_FR'
```

### Regional Maps

```bash
curl 'https://bff.bonjour-ratp.fr/maps?bbox=2.0,48.7,2.5,49.0' \
  -H 'Accept: application/vnd.rss.bff.maps.v3+json' \
  -H 'x-api-key: rHaqHU7laBW3WANbmWUwvrAOoLrdU8pC5aLLkS6e' \
  -H 'x-client-platform: bonjour_web' \
  -H 'x-client-version: 9.11.0' \
  -H 'x-client-locale: fr_FR'
```

---

## 9. KEY FINDINGS

1. **API key is public** — hardcoded in frontend JS, no secret key required
2. **SSE for itineraries** — `/itineraries/stream` returns Server-Sent Events, not compressed
3. **Base64 transitId** — contains `lineId`, `directionId`, `stopAreaId`, `stopPlaceId` in JSON
4. **Content-type versioning** — API versions in Accept headers, not URLs
5. **ID format** — follows Île-de-France Mobilités (IDFM) convention: `PREFIX:IDFM:CODE`
6. **No search API** — geocoding/stop search endpoints are 404; may use external APIs client-side
7. **No rate limiting observed** — no rate limit or Retry-After headers
8. **Tracking ID** — `trackingId` field uses single-letter codes (e.g., `J|I|E7`)
