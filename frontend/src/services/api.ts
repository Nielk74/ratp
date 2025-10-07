import axios from "axios";
import type {
  Line,
  NormalizedTrafficStatus,
  NearestStationResult,
  Schedule,
  WebhookSubscription,
} from "@/types";

const DEFAULT_BACKEND_PORT = process.env.NEXT_PUBLIC_BACKEND_PORT || "8000";
const FALLBACK_HOST = process.env.NEXT_PUBLIC_BACKEND_HOST;

function resolveBaseUrl(): string {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }

  if (typeof window !== "undefined") {
    try {
      const url = new URL(window.location.href);
      const host = FALLBACK_HOST || url.hostname;
      return `${url.protocol}//${host}:${DEFAULT_BACKEND_PORT}`;
    } catch (error) {
      console.error("Failed to resolve backend host from window.location", error);
    }
  }

  const envHost = FALLBACK_HOST || "127.0.0.1";
  return `http://${envHost}:${DEFAULT_BACKEND_PORT}`;
}

const api = axios.create({
  baseURL: resolveBaseUrl(),
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
  },
});
api.interceptors.request.use((config) => {
  config.baseURL = resolveBaseUrl();
  return config;
});

export const apiClient = {
  // Lines
  async getLines(transportType?: string): Promise<{ lines: Line[]; count: number }> {
    const params = transportType ? { transport_type: transportType } : {};
    const { data } = await api.get("/api/lines", { params });
    return data;
  },

  async getLineStations(
    transportType: string,
    lineCode: string
  ): Promise<any> {
    const { data } = await api.get(
      `/api/lines/${transportType}/${lineCode}/stations`
    );
    return data;
  },

  // Traffic
  async getTraffic(lineCode?: string): Promise<NormalizedTrafficStatus> {
    const params = lineCode ? { line_code: lineCode } : {};
    const { data } = await api.get("/api/traffic/status", { params });
    return data;
  },

  // Schedules
  async getSchedules(
    transportType: string,
    lineCode: string,
    station: string,
    direction: string
  ): Promise<{ result: { schedules: Schedule[] } }> {
    const { data } = await api.get(
      `/api/schedules/${transportType}/${lineCode}/${station}/${direction}`
    );
    return data;
  },

  // Geolocation
  async getNearestStations(
    lat: number,
    lon: number,
    maxResults?: number,
    maxDistance?: number
  ): Promise<{ results: NearestStationResult[]; count: number }> {
    const params: any = { lat, lon };
    if (maxResults) params.max_results = maxResults;
    if (maxDistance) params.max_distance = maxDistance;

    const { data } = await api.get("/api/geo/nearest", { params });
    return data;
  },

  // Webhooks
  async createWebhook(
    webhookUrl: string,
    lineCode: string,
    severityFilter?: string[]
  ): Promise<any> {
    const { data } = await api.post("/api/webhooks", {
      webhook_url: webhookUrl,
      line_code: lineCode,
      severity_filter: severityFilter,
    });
    return data;
  },

  async listWebhooks(): Promise<{
    subscriptions: WebhookSubscription[];
    count: number;
  }> {
    const { data } = await api.get("/api/webhooks");
    return data;
  },

  async deleteWebhook(id: number): Promise<any> {
    const { data } = await api.delete(`/api/webhooks/${id}`);
    return data;
  },

  async testWebhook(webhookUrl: string): Promise<any> {
    const { data } = await api.post("/api/webhooks/test", null, {
      params: { webhook_url: webhookUrl },
    });
    return data;
  },
};
