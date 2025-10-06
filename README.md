# 🚇 RATP Live Tracker

Real-time monitoring system for Paris public transport (RATP) with live traffic updates, incident alerts, geolocation-based stop suggestions, and predictive forecasting.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite)](https://sqlite.org)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000?logo=next.js)](https://nextjs.org)

---

## 🎯 Features

### ✅ Backend (Fully Implemented)
- **Real-time Traffic Data**: Fetch live traffic status and incidents from RATP APIs
- **Schedule Information**: Get real-time departure times for any station
- **Line Information**: Browse all metro, RER, tram, and bus lines
- **Geolocation Service**: Find nearest stations based on coordinates
- **Discord Webhooks**: Subscribe to alerts for specific lines
- **Rate Limiting & Caching**: Intelligent API usage with in-memory cache
- **REST API**: FastAPI backend with automatic documentation
- **Test Suite**: 42 comprehensive tests covering all services and endpoints

### ✅ Frontend (Fully Implemented)
- **Live Dashboard**: Real-time traffic status for all metro lines
- **Responsive Design**: Mobile-first UI built with Next.js 14 and Tailwind CSS
- **Geolocation Feature**: Find nearest stations using your device location
- **Auto-refresh**: Live data updates every 2 minutes
- **Modern UI**: Clean, intuitive interface with line cards and status indicators

### 🚧 Coming Soon
- **Interactive Map**: Leaflet.js map with stations and real-time data
- **Traffic Forecasting**: ML-based predictions for delays and congestion
- **Historical Data**: Track patterns and analyze past incidents
- **Webhook Management UI**: Manage Discord subscriptions from the dashboard
- **Mobile App**: Native iOS/Android applications

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

### APIs Used
- **PRIM Île-de-France Mobilités**: Official API (20k requests/day)
- **Community RATP API**: Fallback for simpler access

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
# Edit .env with your API keys (PRIM_API_KEY is optional)

# Run the server
python main.py
```

The API will be available at `http://localhost:8000`

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
# Default API URL is http://localhost:8000

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:3000`

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
- `GET /api/lines` - List all transport lines
- `GET /api/lines/{type}/{code}/stations` - Get stations for a line

### Traffic
- `GET /api/traffic` - Get network-wide traffic status
- `GET /api/traffic?line_code=1` - Filter by specific line

### Schedules
- `GET /api/schedules/{type}/{line}/{station}/{direction}` - Real-time departures

### Geolocation
- `GET /api/geo/nearest?lat=48.8566&lon=2.3522` - Find nearest stations

### Webhooks
- `POST /api/webhooks` - Create Discord alert subscription
- `GET /api/webhooks` - List active subscriptions
- `POST /api/webhooks/test` - Send test notification

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

---

## 📦 Project Structure

```
ratp/
├── backend/
│   ├── api/
│   │   ├── lines.py         # Line endpoints
│   │   ├── traffic.py       # Traffic endpoints
│   │   ├── schedules.py     # Schedule endpoints
│   │   ├── geo.py           # Geolocation endpoints
│   │   └── webhooks.py      # Webhook management
│   ├── models/
│   │   ├── line.py          # Line model
│   │   ├── station.py       # Station model
│   │   ├── traffic.py       # Traffic event model
│   │   ├── schedule.py      # Schedule history model
│   │   ├── webhook.py       # Webhook subscription model
│   │   └── forecast.py      # Forecast prediction model
│   ├── services/
│   │   ├── ratp_client.py   # RATP API client
│   │   ├── cache_service.py # Caching layer
│   │   ├── discord_service.py # Discord notifications
│   │   └── geo_service.py   # Geolocation calculations
│   ├── config.py            # Configuration management
│   ├── database.py          # Database connection
│   ├── main.py              # FastAPI app
│   └── requirements.txt     # Python dependencies
├── frontend/                # (Coming soon)
├── docs/
├── plan.md                  # Architecture & roadmap
├── README.md                # This file
└── .gitignore
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

# RATP APIs
PRIM_API_KEY=""  # Optional, register at prim.iledefrance-mobilites.fr
COMMUNITY_API_URL="https://api-ratp.pierre-grimaud.fr/v4"

# Caching
CACHE_TTL_TRAFFIC=120      # 2 minutes
CACHE_TTL_SCHEDULES=30     # 30 seconds
CACHE_TTL_STATIONS=86400   # 24 hours

# Discord
DISCORD_WEBHOOK_ENABLED=True
DISCORD_RATE_LIMIT_SECONDS=60
```

---

## 🗺️ Roadmap

See [plan.md](plan.md) for detailed roadmap.

### Phase 1: Backend Foundation ✅ (COMPLETED)
- [x] FastAPI setup
- [x] Database models (SQLite)
- [x] RATP API client with rate limiting
- [x] REST endpoints (lines, traffic, schedules, geo, webhooks)
- [x] Discord webhooks service
- [x] Geolocation service
- [x] Comprehensive test suite (42 tests)

### Phase 2: Frontend Foundation ✅ (COMPLETED)
- [x] Next.js 14 application
- [x] Real-time dashboard
- [x] Tailwind CSS styling
- [x] Live traffic status component
- [x] Geolocation nearest stations
- [x] API client service
- [x] Responsive mobile design

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
