# 🚇 RATP Live Tracker

Real-time monitoring system for Paris public transport (RATP) with live traffic updates, incident alerts, geolocation-based stop suggestions, and predictive forecasting.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite)](https://sqlite.org)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000?logo=next.js)](https://nextjs.org)

---

## 🎯 Features

### ✅ Backend Highlights
- **Live Traffic Status** scraped from ratp.fr traffic endpoints via an emulated browser session with caching
- **Snapshot API**: Stations derived from IDFM open-data plus optional VMTR websocket vehicle feeds, with metadata to surface live vs inferred data
- **Multi-network Line Catalogue** (Metro, RER, Tram, Transilien) enriched with IDFM open-data stations
- **Discord Webhooks** with confirmation messages and CRUD endpoints
- **Geolocation & Utilities**: nearest-station search, in-memory cache, typed configuration
- **Automated Tests**: 48 passes covering services, models, and REST contracts
- **Background Orchestrator**: Kafka-backed scheduler + worker fleet keeping live data and traffic snapshots fresh (see [`docs/LIVE_DATA_ORCHESTRATION.md`](docs/LIVE_DATA_ORCHESTRATION.md))

> ℹ️ _True vehicle locations and mission ETAs need IDFM SIRI/GTFS-RT access. See the “Real-Time Train Position Plan” in `plan.md` for activation steps._

### ✅ Frontend Highlights
- **Network Toggles** to switch between Metro / RER / Tram / Transilien views
- **Line Details Panel** with ordered station list and VMTR-driven train markers (falls back to empty data when websocket disabled)
- **Discord Webhook Manager** page for creating, listing, and deleting alerts
- **Nearest Stations Widget** with client-side geolocation
- **Responsive Next.js 14 UI** refreshing data every two minutes

### 🚧 Coming Soon
- **Interactive Map** once official GTFS geometry & vehicle feeds are unlocked
- **Live Train Positions & Forecasts** using SIRI StopMonitoring or GTFS-RT vehicle data (pending IDFM approval)
- **Historical analytics** and reliability metrics based on stored vehicle snapshots
- **Mobile companion apps** once the API surface settles

---

## 🏗️ Architecture

```
RATP Live Tracker
├── backend/          FastAPI + SQLAlchemy + SQLite
│   ├── api/          REST endpoints
│   ├── models/       Database models
│   ├── services/     RATP client, Discord, geolocation
│   └── main.py       Application entry point
├── frontend/         Next.js + React + TailwindCSS
├── docs/            Documentation
└── plan.md          Project roadmap & architecture
```

### APIs & Data Sources
- **ratp.fr traffic endpoints** – official public site scraped with shared session cookies
- **VMTR Websocket** – live vehicle positions for lines with public feeds
- **IDFM Open Data** – station catalogue (`arrets-lignes`) and line references
- **Île-de-France Mobilités Open Data** – station catalogue (`arrets-lignes`) and line references
- **PRIM Navitia** – optional departures feed (requires API key, disabled by default)
- **Community RATP API** – legacy fallback (currently unreliable)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+ and pip
- Node.js 18+ and npm
- Git

### Full Stack Setup

#### 1. Clone the repository
```bash
git clone https://github.com/Nielk74/ratp.git
cd ratp
```

#### 2. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys (PRIM_API_KEY only required for optional Navitia features)

# Run the server
PYTHONPATH="$(pwd)/.." uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

API docs: `http://127.0.0.1:8000/docs` (health: `/health`)

**Backend Documentation:**
- **Interactive Docs (Swagger)**: http://localhost:8000/docs
- **Alternative Docs (ReDoc)**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

#### 3. Frontend Setup

In a **new terminal window**:

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.local.example .env.local
# By default the client derives the API origin from the browser host.
# Override with NEXT_PUBLIC_BACKEND_HOST / NEXT_PUBLIC_BACKEND_PORT if needed

# Start development server
npm run dev -- --hostname 127.0.0.1 --port 8001
```

The frontend will be available at `http://127.0.0.1:8001`

### Dev helpers

- `./serve.sh` – kills stale `uvicorn`/`next` processes, then starts backend (8000) and a Next.js dev server (first free port from 8001).
- `./scripts/run_tests.sh` – ensures the backend virtualenv exists, installs pytest if needed, and runs the backend unit test suite.
- `./scripts/check_m14_bibliotheque.sh` – calls the schedules endpoint for Metro 14 at Bibliothèque François-Mitterrand (direction configurable via `--direction`).
- `./scripts/run_e2e.sh` – launches the stack, runs Playwright e2e specs, streams progress, and tears everything down (log tails on failure).

### Running Tests

```bash
# Backend tests (from backend/ directory)
pytest
pytest --cov=backend --cov-report=html

# Frontend type checking
cd frontend
npm run type-check
npm run lint
```

---

## 📡 API Endpoints

### Lines
- `GET /api/lines` – List all networks (metro, rer, tram, transilien)
- `GET /api/lines?transport_type=metro` – Filter by transport type
- `GET /api/lines/{type}/{code}` – Detailed line payload (stations + VMTR-driven train markers when available)
- `GET /api/snapshots/{network}/{line}` – Aggregated station data (IDFM stations + VMTR vehicles)
- `GET /api/lines/{type}/{code}/stations` – Raw station feed for integrations

### Traffic
- `GET /api/traffic/status` – Normalised traffic overview with severity labels
- `GET /api/traffic` – Legacy pass-through payload (kept for compatibility)
- `GET /api/traffic?line_code=1` – Filter traffic response by specific line

### Schedules *(pending external feed reliability)*
- `GET /api/schedules/{type}/{line}/{station}/{direction}` – Routed to community API; currently unavailable until the feed returns

### Geolocation
- `GET /api/geo/nearest?lat=48.8566&lon=2.3522` – Find nearest stations to a coordinate

### Webhooks
- `POST /api/webhooks` – Create Discord alert subscription (sends confirmation message)
- `GET /api/webhooks` – List active subscriptions
- `DELETE /api/webhooks/{id}` – Remove a subscription
- `POST /api/webhooks/test` – Send test notification

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov-report=html

# Run specific test file
pytest backend/tests/test_ratp_client.py
```

For full-stack + Playwright validation run `./scripts/run_e2e.sh` from the repo root (it spins up the stack, runs tests, and tears everything down).

---

## 📦 Project Structure

```
ratp/
├── backend/
│   ├── api/             # FastAPI routers (lines, traffic, schedules, geo, webhooks)
│   ├── services/        # Integrations (ratp.fr traffic, IDFM open data, Discord, cache)
│   ├── models/          # SQLAlchemy models & mixins
│   ├── tests/           # pytest suite (48 tests)
│   └── main.py          # Application entry point
├── frontend/
│   ├── src/
│   │   ├── app/         # Dashboard & webhooks pages (Next.js App Router)
│   │   ├── components/  # Header, TrafficStatus, LineDetailsPanel, ...
│   │   ├── services/    # Axios client with dynamic host detection
│   │   └── types/       # Shared TypeScript definitions
├── plan.md              # Architecture & real-time roadmap
├── DEPLOYMENT.md        # Deployment & environment guide
└── README.md            # Project overview
```

---

## 🔧 Configuration

All configuration is managed via environment variables in `.env`:

```env
# Application
APP_NAME="RATP Live Tracker"
ENVIRONMENT="development"
DEBUG=True

# Server
HOST="0.0.0.0"
PORT=8000

# Database
DATABASE_URL="sqlite+aiosqlite:///./ratp.db"

# RATP / IDFM APIs
PRIM_API_KEY=""  # Optional: Navitia departures fallback (disable by default)
COMMUNITY_API_URL="https://api-ratp.pierre-grimaud.fr/v4"

# Caching
CACHE_TTL_TRAFFIC=120      # 2 minutes
CACHE_TTL_SCHEDULES=30     # 30 seconds
CACHE_TTL_STATIONS=86400   # 24 hours

# Discord
DISCORD_WEBHOOK_ENABLED=True
DISCORD_RATE_LIMIT_SECONDS=60

# Scrapers
NAVITIA_SCRAPER_MODE=mock   # Use 'live' to hit Navitia (requires PRIM_API_KEY), 'mock' for offline tests
VMTR_SOCKET_ENABLED=False   # Enable socket.io realtime fetch (requires internet)
VMTR_SOCKET_URL="wss://api.vmtr.ratp.fr/socket.io/"

# CORS
CORS_ALLOW_ORIGINS="http://localhost:3000,http://localhost:3100"
```

---

## 🗺️ Roadmap

See [plan.md](plan.md) for detailed roadmap.

### Phase 1: Backend Foundation ✅ (COMPLETED)
- [x] FastAPI setup
- [x] Database models (SQLite)
- [x] ratp.fr traffic scraper with caching
- [x] REST endpoints (lines, traffic, schedules*, geo, webhooks)
- [x] Discord webhooks service
- [x] Geolocation service
- [x] Comprehensive test suite (48 tests)

### Phase 2: Frontend Foundation ✅ (COMPLETED)
- [x] Next.js 14 application
- [x] Network filters and line detail panel
- [x] Webhook management UI
- [x] Tailwind CSS styling & responsive design
- [x] Geolocation nearest stations
- [x] API client service

> *Schedule endpoints remain dependent on the legacy community API; SIRI access is required for reliable live departures.*

### Phase 3: Advanced Features (Next)
- [ ] Interactive map with Leaflet
- [ ] Webhook management UI
- [ ] Real-time WebSocket updates
- [ ] Enhanced error handling
- [ ] Comprehensive logging

### Phase 4: Advanced Features
- [ ] Traffic forecasting with ML
- [ ] Historical data analysis
- [ ] Performance optimization

### Phase 5: Testing & Deployment
- [ ] Unit & integration tests
- [ ] CI/CD pipeline
- [ ] Docker deployment
- [ ] Production monitoring

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Commit changes: `git commit -m "feat: add my feature"`
4. Push to branch: `git push origin feat/my-feature`
5. Open a pull request

### Commit Convention
```
<type>(<scope>): <subject>

Types: feat, fix, docs, style, refactor, test, chore
Scopes: api, frontend, db, deploy, tests
```

---

## 📄 License

This project is open source and available under the MIT License.

---

## 🙏 Acknowledgments

- **RATP**: Public transport operator of Paris
- **Île-de-France Mobilités**: Regional transport authority
- **Community Contributors**: Pierre Grimaud for the community RATP API

---

## 📞 Support

- **Documentation**: See [plan.md](plan.md) for architecture details
- **Issues**: Open an issue on GitHub
- **API Docs**: http://localhost:8000/docs (when running)

---

**Built with ❤️ for Paris public transport users**
