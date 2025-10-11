export interface Line {
  code: string;
  name: string;
  type: "metro" | "rer" | "tram" | "transilien";
  color?: string;
}

export interface Station {
  name: string;
  latitude: number;
  longitude: number;
  lines?: string[];
}

export interface CommunityTrafficLine {
  line: string;
  slug: string;
  title: string;
  message?: string;
}

export interface PrimTrafficLineReport {
  line?: {
    code?: string;
    name?: string;
    id?: string;
  };
  status?: {
    severity?: string;
    message?: string;
    short_message?: string;
    description?: string;
    effect?: string;
    status?: string;
  };
  disruption?: {
    severity?: string;
    description?: string;
  };
  impacts?: Array<{
    severity?: string;
    description?: string;
  }>;
}

export type LineStatusLevel = "normal" | "warning" | "disrupted" | "closed" | "unknown";

export type LineStatusSource = "prim" | "community" | "fallback";

export interface LineStatusInfo {
  level: LineStatusLevel;
  label: string;
  message?: string;
  source: LineStatusSource;
  line_code?: string;
  details?: unknown;
}

export interface NormalizedTrafficStatus {
  generated_at: string;
  status?: string;
  source?: string;
  timestamp?: string;
  lines: Array<{
    line_code: string;
    level: LineStatusLevel;
    message?: string;
    source: LineStatusSource;
    details?: unknown;
  }>;
  default: {
    level: LineStatusLevel;
    message: string;
  };
}

export interface LineStation {
  name?: string;
  slug?: string;
  latitude?: number;
  longitude?: number;
  city?: string;
  [key: string]: unknown;
}

export interface LineDetails {
  line: Line;
  stations: LineStation[];
  stations_count: number;
  source?: string;
}

export interface Schedule {
  message: string;
  destination: string;
}

export interface NearestStationResult {
  station: Station;
  distance_km: number;
  distance_m: number;
}

export interface WebhookSubscription {
  id: number;
  webhook_url: string;
  line_code: string;
  line_name?: string;
  severity_filter?: string[];
  is_active: boolean;
}


export interface ScrapedDepartureInfo {
  raw_text: string;
  destination?: string | null;
  waiting_time?: string | null;
  status?: string | null;
  platform?: string | null;
  extra?: Record<string, unknown>;
}

export interface LineSnapshotStation {
  name: string;
  slug: string;
  order: number;
  direction: string;
  direction_index?: number | null;
  departures: ScrapedDepartureInfo[];
  metadata: Record<string, unknown>;
  error?: string | null;
}

export interface TrainEstimate {
  direction: string;
  from_station: string;
  to_station: string;
  eta_from: number | null;
  eta_to: number | null;
  progress: number;
  absolute_progress: number;
  confidence: "high" | "medium" | "low";
  status?: string | null;
}

export interface LineSnapshot {
  scraped_at: string;
  network: string;
  line: string;
  stations: LineSnapshotStation[];
  trains: Record<string, TrainEstimate[]>;
  errors: string[];
}
