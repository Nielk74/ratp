# RATP Live Tracker - Frontend

Modern Next.js 14 frontend for real-time Paris public transport monitoring.

## Features

- 📊 **Network Dashboard**: Filterable views for Metro, RER, Tram, and Transilien lines
- 🧭 **Line Details Panel**: Station roster plus (for now) inferred train positions (Navitia primary, HTTP fallback)
- 🔔 **Webhook Manager**: Create, list, and delete Discord subscriptions with severity filters
- 📍 **Nearest Stations**: Client-side geolocation to find the closest stops
- 📱 **Responsive Design**: Tailored for desktop and mobile with Tailwind CSS
- ⏱️ **Auto Refresh**: Data refreshes every two minutes

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State Management**: Zustand
- **HTTP Client**: Axios
- **Maps**: Leaflet.js + React-Leaflet

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Backend API running on `http://localhost:8000`

### Installation

```bash
# Install dependencies
npm install

# Create environment file
cp .env.local.example .env.local

# Start development server
npm run dev -- --hostname 127.0.0.1 --port 8001
```

The application will be available at `http://127.0.0.1:8001` (auto-discovers backend host)

### Environment Variables

Create a `.env.local` file if you need to override defaults:

```env
# Optional – only required when the backend host differs from the browser host
NEXT_PUBLIC_BACKEND_HOST=xps
NEXT_PUBLIC_BACKEND_PORT=8000
```
By default the client infers the backend origin from the current browser hostname.

### Dev helpers

- `../serve.sh` – spins up backend + frontend dev servers, killing stale ones first.
- `../scripts/run_e2e.sh` – spins up the stack, runs Playwright e2e tests, tears everything down.

## Project Structure

```
frontend/
├── src/
│   ├── app/                 # Next.js App Router pages
│   │   ├── layout.tsx       # Root layout
│   │   ├── page.tsx         # Home page
│   │   └── globals.css      # Global styles
│   ├── components/          # React components
│   │   ├── Header.tsx       # Navigation header
│   │   ├── TrafficStatus.tsx# Traffic status dashboard
│   │   ├── LineCard.tsx     # Individual line card
│   │   ├── NearestStations.tsx # Geolocation feature
│   │   └── LineDetailsPanel.tsx # Station list & train summary
│   ├── services/            # API client
│   │   └── api.ts           # Backend API wrapper
│   ├── types/               # TypeScript definitions
│   │   └── index.ts         # Shared types
│   └── lib/                 # Utilities
├── public/                  # Static assets
├── tailwind.config.ts       # Tailwind configuration
├── tsconfig.json           # TypeScript configuration
└── next.config.js          # Next.js configuration
```

## Available Scripts

```bash
# Development
npm run dev              # Start dev server

# Production
npm run build            # Build for production
npm start                # Start production server

# Code Quality
npm run lint             # Run ESLint
npm run type-check       # TypeScript type checking
```

## Components

- `Header` – navigation bar with live indicator and API docs shortcut
- `TrafficStatus` – responsive grid of line cards with selection handling
- `LineCard` – status chip, colour bubble, and active-state styles
- `LineDetailsPanel` – station roster & (current) inferred vehicles from Navitia snapshot
- `NearestStations` – geolocation-based finder

## API Integration

The frontend communicates with the FastAPI backend through the `apiClient` service:

```typescript
import { apiClient } from "@/services/api";

// Get all Transilien lines
const { lines } = await apiClient.getLines("transilien");

// Get normalised traffic status
const traffic = await apiClient.getTraffic();

// Find nearest stations
const { results } = await apiClient.getNearestStations(lat, lon);

// Fetch detailed line information (stations + inferred trains (Navitia snapshot))
const details = await apiClient.getLineDetails("metro", "1");
const snapshot = await apiClient.getLineSnapshot("metro", "1");
```

## Styling

Built with Tailwind CSS utility classes:

- **Colors**: Custom primary, success, warning, error palettes
- **Responsive**: Mobile-first breakpoints (sm, md, lg, xl)
- **Dark Mode**: Ready for dark mode support

## Future Enhancements

- [ ] Upgrade live map to Leaflet/Mapbox with animated markers
- [ ] Real-time WebSocket/SSE updates for snapshots
- [ ] Surface Navitia vs fallback state directly in the UI
- [ ] Schedule viewer for stations (once SIRI/GTFS feeds unlock)
- [ ] Traffic forecast visualisations
- [ ] PWA support for offline access
- [ ] Dark mode toggle

## Contributing

Follow the project's commit conventions and ensure TypeScript checks pass before committing.

---

**Built with Next.js 14 and Tailwind CSS**
