import axios from "axios";
import type {
  Line,
  TrafficData,
  NearestStationResult,
  Schedule,
  WebhookSubscription,
} from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_URL,
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
  },
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
  async getTraffic(lineCode?: string): Promise<TrafficData> {
    const params = lineCode ? { line_code: lineCode } : {};
    const { data } = await api.get("/api/traffic", { params });
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
