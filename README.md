# RATP BFF Proxy

A local reverse-proxy server that exposes the RATP **BFF** (Backend for Frontend) API (`bff.bonjour-ratp.fr`) with CORS headers, API key injection, and a self-documented OpenAPI spec.

## Features

- **Proxy** all RATP BFF endpoints with automatic `Accept` header negotiation per route
- **CORS** – open wildcard headers so any browser / local tool can call the API
- **API key injection** via `api-keys.json` (git-ignored)
- **OpenAPI spec** served at `/openapi.yaml` and `/openapi.json`
- **Interactive HTML explorer** (`bff-api.html` / `bff-api-keyed.html`)
- **Named routes** for the most-used endpoints:
  - `GET /departures` – next departures for a stop
  - `GET /incidents` – line disruptions / situations
  - `GET /itinerary` – journey planner (stream)
  - `GET /maps` – line maps
  - `GET /providers` – itinerary providers
- **Geocoder** helper to resolve stop names → coordinates
- **Lines** metadata cache
- **Tests** via Node built-in test runner (`node --test`)

## Requirements

- Node.js ≥ 18
- [Playwright](https://playwright.dev/) (used to capture authenticated sessions)

```
npm install
npx playwright install chromium
```

## Usage

```bash
node server.js
# or
PORT=3210 node server.js
```

Server starts on **http://localhost:3210**.

### Key endpoints

| Path | Description |
|------|-------------|
| `GET /openapi.yaml` | Raw OpenAPI spec |
| `GET /openapi.json` | OpenAPI spec as JSON |
| `GET /` | HTML API explorer |
| `GET /departures?stop=…` | Next departures |
| `GET /incidents?line=…` | Line incidents |
| `GET /itinerary?from=…&to=…` | Journey planner |
| `GET /maps?line=…` | Line map |
| `POST /*` | Proxy any BFF endpoint |

## API Keys

Place your RATP API keys in `api-keys.json` (this file is **not** committed):

```json
{
  "apiKey": "YOUR_KEY_HERE"
}
```

## Tests

```bash
npm test
```

## Project Structure

```
server.js          – HTTP server & routing
lib/
  bff.js           – BFF HTTP client
  browser.js       – Playwright session capture
  geocoder.js      – Stop geocoding
  lines.js         – Lines metadata
  proxy.js         – Generic proxy logic
  stops.js         – Stop helpers
routes/
  departures.js
  incidents.js
  itinerary.js
  maps.js
  providers.js
  index.js         – Route registry
tests/             – Node built-in test suites
bff-api.yaml       – OpenAPI spec (reverse-engineered)
```

## License

ISC
