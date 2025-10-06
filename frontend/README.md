# RATP Live Tracker - Frontend

Modern Next.js 14 frontend for real-time Paris public transport monitoring.

## Features

- 📊 **Real-time Dashboard**: Live traffic status for all metro lines
- 📍 **Geolocation**: Find nearest stations based on your location
- 🗺️ **Interactive Map**: Visualize stations and lines (coming soon)
- 🔔 **Discord Webhooks**: Subscribe to alerts for specific lines
- 📱 **Responsive Design**: Mobile-first UI built with Tailwind CSS

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
npm run dev
```

The application will be available at `http://localhost:3000`

### Environment Variables

Create a `.env.local` file:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

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
│   │   └── NearestStations.tsx # Geolocation feature
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

### Header
Navigation bar with logo, menu links, and live status indicator.

### TrafficStatus
Grid of line cards showing current traffic status for all metro lines.

### LineCard
Individual card displaying line number, name, color, and current status.

### NearestStations
Geolocation-based feature to find and display nearby stations.

## API Integration

The frontend communicates with the FastAPI backend through the `apiClient` service:

```typescript
import { apiClient } from "@/services/api";

// Get all metro lines
const { lines } = await apiClient.getLines("metro");

// Get traffic status
const traffic = await apiClient.getTraffic();

// Find nearest stations
const { results } = await apiClient.getNearestStations(lat, lon);
```

## Styling

Built with Tailwind CSS utility classes:

- **Colors**: Custom primary, success, warning, error palettes
- **Responsive**: Mobile-first breakpoints (sm, md, lg, xl)
- **Dark Mode**: Ready for dark mode support

## Future Enhancements

- [ ] Interactive Leaflet map
- [ ] Real-time WebSocket updates
- [ ] Webhook management UI
- [ ] Schedule viewer for stations
- [ ] Traffic forecast predictions
- [ ] PWA support for offline access
- [ ] Dark mode toggle

## Contributing

Follow the project's commit conventions and ensure TypeScript checks pass before committing.

---

**Built with Next.js 14 and Tailwind CSS**
