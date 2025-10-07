# RATP Live Tracker - Project Plan & Architecture

**Version:** 1.0
**Last Updated:** 2025-10-07
**Status:** Phase 1 - Initial Setup

---

## 📋 Executive Summary

RATP Live Tracker is a modern, real-time monitoring system for Paris public transport. It provides live traffic updates, incident alerts, geolocation-based stop suggestions, and predictive forecasting using RATP and PRIM APIs.

---

## 🏗️ System Architecture

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Dashboard   │  │  Map View    │  │  Alerts      │      │
│  │  Component   │  │  Component   │  │  Manager     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                  │                  │              │
│         └──────────────────┴──────────────────┘              │
│                            │                                 │
└────────────────────────────┼─────────────────────────────────┘
                             │ REST API / WebSocket
┌────────────────────────────┼─────────────────────────────────┐
│                            ▼                                 │
│                   FastAPI Backend                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              API Routes Layer                         │   │
│  │  /api/lines  /api/traffic  /api/schedules /api/geo   │   │
│  └──────────────────────────────────────────────────────┘   │
│                            │                                 │
│  ┌────────────────┬────────┴────────┬───────────────────┐   │
│  │                │                 │                    │   │
│  ▼                ▼                 ▼                    ▼   │
│ ┌──────┐    ┌──────────┐    ┌──────────┐    ┌────────────┐ │
│ │ RATP │    │ Discord  │    │  Geo     │    │ Forecast   │ │
│ │Client│    │ Webhook  │    │ Service  │    │ Engine     │ │
│ └──────┘    └──────────┘    └──────────┘    └────────────┘ │
│     │             │                │                │        │
└─────┼─────────────┼────────────────┼────────────────┼────────┘
      │             │                │                │
      ▼             ▼                ▼                ▼
┌──────────┐  ┌──────────┐    ┌──────────┐    ┌──────────┐
│  PRIM    │  │ Discord  │    │OpenStreet│    │PostgreSQL│
│   API    │  │   API    │    │   Map    │    │ Database │
└──────────┘  └──────────┘    └──────────┘    └──────────┘
```

### Component Breakdown

#### 1. **Backend (FastAPI + Python)**
- **API Routes**: RESTful endpoints for frontend consumption
- **RATP Client Service**: Handles API calls to PRIM and community APIs
- **Cache Layer**: Redis for rate limit management and data caching
- **Database Models**: SQLAlchemy ORM for PostgreSQL
- **Background Tasks**: Celery for periodic data fetching and forecasting
- **WebSocket Server**: Real-time updates to connected clients

#### 2. **Frontend (Next.js + React)**
- **Dashboard**: Real-time network overview
- **Interactive Map**: Leaflet.js with station markers and live data
- **Alert Configuration**: Subscribe to specific lines via Discord webhooks
- **Geolocation Service**: Find nearest stops with live data
- **Responsive Design**: TailwindCSS for mobile-first UI

#### 3. **Data Layer (PostgreSQL)**
- **Historical Data**: Store traffic events, schedules, delays
- **User Subscriptions**: Discord webhook configurations
- **Forecasting Dataset**: Time-series data for ML predictions
- **Cache Tables**: Temporary storage for API responses

---

## 🎯 Project Milestones & Roadmap

### ✅ Phase 0: Research & Planning (COMPLETED)
- [x] Research RATP APIs (PRIM, community APIs)
- [x] Design system architecture
- [x] Create project structure
- [x] Document technology stack

### 🔄 Phase 1: Backend Foundation (IN PROGRESS)
- [ ] Set up Python virtual environment
- [ ] Install FastAPI, SQLAlchemy, Redis, Celery
- [ ] Create database schema and models
- [ ] Implement RATP API client with rate limiting
- [ ] Build caching layer (Redis)
- [ ] Create basic REST API endpoints
- [ ] Add error handling and logging
- [ ] Write unit tests for API client

**Duration:** 1-2 weeks
**Priority:** HIGH

### 📅 Phase 2: Core Features
- [ ] Implement traffic incident fetching
- [ ] Build real-time schedule endpoint
- [ ] Create geolocation service (nearest stops)
- [ ] Set up WebSocket for live updates
- [ ] Implement Discord webhook system
- [ ] Add subscription management endpoints
- [ ] Write integration tests

**Duration:** 2-3 weeks
**Priority:** HIGH

### 📅 Phase 3: Frontend Development
- [ ] Initialize Next.js project with TypeScript
- [ ] Set up TailwindCSS and component library
- [ ] Build dashboard layout and navigation
- [ ] Create line status cards with live data
- [ ] Implement interactive map (Leaflet.js)
- [ ] Build alert configuration UI
- [ ] Add geolocation-based stop finder
- [ ] Implement responsive mobile design
- [ ] Write frontend unit tests (Vitest/Jest)

**Duration:** 2-3 weeks
**Priority:** HIGH

### 📅 Phase 4: Forecasting & ML
- [ ] Collect historical traffic data
- [ ] Design time-series forecasting model
- [ ] Train ML model (Prophet/LSTM)
- [ ] Create prediction API endpoints
- [ ] Display forecasts on dashboard
- [ ] Implement confidence intervals
- [ ] Add model retraining pipeline

**Duration:** 3-4 weeks
**Priority:** MEDIUM

### 📅 Phase 5: Testing & Optimization
- [ ] Comprehensive unit test coverage (>80%)
- [ ] Integration tests for all endpoints
- [ ] Load testing (Locust/k6)
- [ ] Performance optimization
- [ ] Security audit
- [ ] API documentation (Swagger/OpenAPI)
- [ ] User acceptance testing

**Duration:** 1-2 weeks
**Priority:** HIGH

### 📅 Phase 6: Deployment & CI/CD
- [ ] Containerize with Docker
- [ ] Create Docker Compose setup
- [ ] Set up GitHub Actions CI/CD
- [ ] Configure production environment
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Implement logging aggregation
- [ ] Deploy to cloud (Railway/Fly.io/VPS)

**Duration:** 1 week
**Priority:** MEDIUM

---

## 🔧 Technology Stack

### Backend
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Framework | **FastAPI** | High-performance async API framework |
| Database | **PostgreSQL** | Relational database for structured data |
| Cache | **Redis** | Rate limiting, session storage, API caching |
| ORM | **SQLAlchemy** | Database models and migrations |
| Task Queue | **Celery** | Background jobs for data fetching |
| Validation | **Pydantic** | Request/response validation |
| HTTP Client | **httpx** | Async HTTP requests to RATP APIs |
| Testing | **pytest** | Unit and integration testing |

### Frontend
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Framework | **Next.js 14** | React framework with SSR/SSG |
| Language | **TypeScript** | Type-safe JavaScript |
| Styling | **TailwindCSS** | Utility-first CSS framework |
| UI Components | **shadcn/ui** | Pre-built accessible components |
| Maps | **Leaflet.js** | Interactive maps |
| State | **Zustand** | Lightweight state management |
| API Client | **Axios/Fetch** | HTTP requests |
| Testing | **Vitest + RTL** | Unit and component testing |

### Infrastructure
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Containerization | **Docker** | Application packaging |
| Orchestration | **Docker Compose** | Local multi-container setup |
| CI/CD | **GitHub Actions** | Automated testing and deployment |
| Monitoring | **Prometheus** | Metrics collection |
| Visualization | **Grafana** | Dashboards and alerts |
| Logging | **Loki/ELK** | Centralized logging |

---

## 📡 API Integration Details

### PRIM Île-de-France Mobilités API
**Base URL:** `https://prim.iledefrance-mobilites.fr/`
**Authentication:** API Key (register at PRIM portal)
**Rate Limits:**
- Traffic Info: 20,000 requests/day
- Next Departures: 1,000 requests/day
- Messages: 20,000 requests/day

**Key Endpoints:**
- `GET /traffic` - Real-time traffic incidents by line/mode
- `GET /next_departures` - Real-time schedules (updated every minute)
- `GET /messages` - Information messages displayed on screens

### Community RATP API (Fallback)
**Base URL:** `https://api-ratp.pierre-grimaud.fr/v4/`
**Authentication:** None
**Rate Limits:** Moderate (unofficial, use as fallback)

**Key Endpoints:**
- `GET /stations/{type}/{line}` - List stations for a line
- `GET /schedules/{type}/{line}/{station}/{direction}` - Real-time schedules
- `GET /traffic` - Network-wide traffic status

### Caching Strategy
- **Traffic Data:** Cache for 2 minutes
- **Schedule Data:** Cache for 30 seconds
- **Station Lists:** Cache for 24 hours
- **Line Information:** Cache for 7 days

---

## 🗄️ Database Schema

### Tables

#### `lines`
```sql
CREATE TABLE lines (
    id SERIAL PRIMARY KEY,
    line_code VARCHAR(10) UNIQUE NOT NULL,
    line_name VARCHAR(100) NOT NULL,
    transport_type VARCHAR(20) NOT NULL, -- metro, rer, tram, bus
    color VARCHAR(7), -- hex color
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### `stations`
```sql
CREATE TABLE stations (
    id SERIAL PRIMARY KEY,
    station_code VARCHAR(20) UNIQUE NOT NULL,
    station_name VARCHAR(200) NOT NULL,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    city VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### `line_stations`
```sql
CREATE TABLE line_stations (
    line_id INTEGER REFERENCES lines(id),
    station_id INTEGER REFERENCES stations(id),
    position INTEGER, -- order on the line
    PRIMARY KEY (line_id, station_id)
);
```

#### `traffic_events`
```sql
CREATE TABLE traffic_events (
    id SERIAL PRIMARY KEY,
    line_id INTEGER REFERENCES lines(id),
    event_type VARCHAR(50) NOT NULL, -- incident, maintenance, delay
    severity VARCHAR(20), -- low, medium, high, critical
    title VARCHAR(500),
    description TEXT,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### `schedules_history`
```sql
CREATE TABLE schedules_history (
    id SERIAL PRIMARY KEY,
    station_id INTEGER REFERENCES stations(id),
    line_id INTEGER REFERENCES lines(id),
    scheduled_time TIMESTAMP NOT NULL,
    actual_time TIMESTAMP,
    delay_seconds INTEGER,
    direction VARCHAR(200),
    recorded_at TIMESTAMP DEFAULT NOW()
);
```

#### `webhook_subscriptions`
```sql
CREATE TABLE webhook_subscriptions (
    id SERIAL PRIMARY KEY,
    discord_webhook_url TEXT NOT NULL,
    line_id INTEGER REFERENCES lines(id),
    severity_filter VARCHAR(20)[], -- array of severities
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    last_triggered TIMESTAMP
);
```

#### `forecast_predictions`
```sql
CREATE TABLE forecast_predictions (
    id SERIAL PRIMARY KEY,
    line_id INTEGER REFERENCES lines(id),
    station_id INTEGER REFERENCES stations(id),
    prediction_time TIMESTAMP NOT NULL,
    predicted_delay_seconds INTEGER,
    predicted_congestion DECIMAL(3, 2), -- 0.00 to 1.00
    confidence_score DECIMAL(3, 2),
    model_version VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 🧪 Testing Strategy

### Unit Tests (Target: 80% coverage)
- API client functions (RATP, Discord)
- Database models and queries
- Utility functions (geolocation calculations)
- Validation schemas
- Caching mechanisms

### Integration Tests
- API endpoint responses
- Database operations (CRUD)
- External API mocking
- WebSocket connections
- Background task execution

### End-to-End Tests
- User subscription workflow
- Alert delivery to Discord
- Map interaction and data display
- Geolocation-based search

### Performance Tests
- API response times (<200ms target)
- Concurrent user load (100+ users)
- Database query optimization
- Cache hit rates (>70% target)

---

## 🚀 Deployment Strategy

### Development Environment
```yaml
# docker-compose.dev.yml
services:
  backend:
    - FastAPI with hot reload
    - PostgreSQL local instance
    - Redis local instance
  frontend:
    - Next.js dev server
    - Hot module replacement
```

### Production Environment
- **Backend:** Railway/Fly.io (containerized FastAPI)
- **Database:** Managed PostgreSQL (Railway/Supabase)
- **Cache:** Managed Redis (Upstash/Railway)
- **Frontend:** Vercel (optimized Next.js deployment)
- **Monitoring:** Prometheus + Grafana on VPS

### CI/CD Pipeline
```yaml
# .github/workflows/ci.yml
1. Lint (ruff, eslint)
2. Type check (mypy, tsc)
3. Unit tests (pytest, vitest)
4. Integration tests
5. Build Docker images
6. Deploy to staging
7. Deploy to production (on main branch)
```

---

## 📊 Success Metrics

### Technical KPIs
- API uptime: >99.5%
- Average response time: <200ms
- Test coverage: >80%
- Cache hit rate: >70%
- Error rate: <0.5%

### User Experience
- Page load time: <2s
- Real-time update latency: <5s
- Mobile responsiveness: 100% Google Lighthouse
- Alert delivery time: <30s

---

## 🔐 Security Considerations

1. **API Key Protection:** Store PRIM API keys in environment variables
2. **Rate Limiting:** Implement per-IP rate limits (100 req/min)
3. **Input Validation:** Pydantic schemas for all inputs
4. **SQL Injection:** Use parameterized queries (SQLAlchemy ORM)
5. **CORS:** Restrict origins in production
6. **Webhook Validation:** Verify Discord webhook URLs before saving
7. **HTTPS:** Enforce TLS 1.3 in production
8. **Dependency Scanning:** Automated vulnerability checks (Snyk/Dependabot)

---

## 📝 Development Guidelines

### Git Commit Convention
```
<type>(<scope>): <subject>

Types: feat, fix, docs, style, refactor, test, chore
Scopes: api, frontend, db, deploy, tests

Examples:
- feat(api): add real-time traffic endpoint
- fix(frontend): correct geolocation permission handling
- docs(plan): update architecture diagram
```

### Code Style
- **Python:** Black formatter, Ruff linter, type hints
- **TypeScript:** Prettier, ESLint, strict mode
- **Imports:** Absolute imports preferred
- **Documentation:** Docstrings for all public functions

---

## 🎯 Next Actions (Current Sprint)

### Immediate Tasks
1. ✅ Research RATP APIs
2. ✅ Design system architecture
3. 🔄 Create project structure
4. 🔄 Document project plan
5. ⏳ Set up Python backend environment
6. ⏳ Initialize database schema
7. ⏳ Implement RATP API client

### 🚆 Real-Time Train Position Plan (Research 2025-10-08)
- **Live feeds status:** No public endpoints currently return train positions; community API remains offline. PRIM Navitia/SIRI/GTFS-RT URLs respond with `no Route matched` for the current key, confirming access is restricted.
- **Required action:** Contact Île-de-France Mobilités via the PRIM portal and request activation for real-time feeds (SIRI StopMonitoring, GTFS-RT vehicle_positions/trip_updates, or Navitia coverage stop_schedules). Specify the lines/modes needed (Metro, RER, Transilien, Tram).
- **Backend plan once enabled:**
  * Create a `VehiclePositionService` that polls the authorised feed, decodes vehicle locations, and stores snapshots (vehicle_id, line_code, lat/lon, next_stop, timestamp) for later analytics.
  * Expose REST endpoints such as `GET /api/lines/{type}/{code}/vehicles` providing live positions, inferred ETAs, and headways.
  * Persist historical snapshots in a dedicated table to power forecasting and reliability metrics.
- **Fallback approach:** If GTFS-RT is still unavailable after the request, use SIRI StopMonitoring arrivals to infer train progress between stations. This still requires SIRI access; without it we will not fabricate positions.
- **Next checkpoint:** Re-test feed URLs once IDFM confirms activation; resume backend ingestion and UI work immediately afterwards.

### This Week
- Complete backend foundation
- Create basic API endpoints
- Set up testing framework
- Initialize frontend project

### This Month
- Core features implementation
- Frontend development
- Integration testing
- Discord webhook system

---

## 📚 Resources & References

### APIs
- [PRIM Documentation](https://prim.iledefrance-mobilites.fr/en)
- [RATP Open Data Portal](https://data.ratp.fr/)
- [Community RATP API](https://github.com/pgrimaud/horaires-ratp-api)

### Technologies
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Next.js Docs](https://nextjs.org/docs)
- [TailwindCSS](https://tailwindcss.com/)
- [Leaflet.js](https://leafletjs.com/)

### Best Practices
- [12 Factor App](https://12factor.net/)
- [REST API Guidelines](https://restfulapi.net/)
- [Python Best Practices](https://docs.python-guide.org/)

---

**Document Version History:**
- v1.0 (2025-10-07): Initial architecture and roadmap
