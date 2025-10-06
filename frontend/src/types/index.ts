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

export interface TrafficData {
  result?: {
    [key: string]: any;
  };
  timestamp?: string;
  error?: string;
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
