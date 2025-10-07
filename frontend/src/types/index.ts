export interface Line {
  code: string;
  name: string;
  type: "metro" | "rer" | "tram" | "bus";
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

export interface TrafficData {
  result?: {
    metros?: CommunityTrafficLine[];
    rers?: CommunityTrafficLine[];
    tramways?: CommunityTrafficLine[];
    buses?: CommunityTrafficLine[];
    [key: string]: CommunityTrafficLine[] | undefined;
  };
  data?: {
    line_reports?: PrimTrafficLineReport[];
    [key: string]: unknown;
  };
  status?: string;
  source?: string;
  message?: string;
  timestamp?: string;
  error?: string;
}

export type LineStatusLevel = "normal" | "warning" | "disrupted" | "closed" | "unknown";

export type LineStatusSource = "prim" | "community" | "fallback";

export interface LineStatusInfo {
  level: LineStatusLevel;
  label: string;
  message?: string;
  source: LineStatusSource;
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
  severity_filter?: string[];
  is_active: boolean;
}
