import axios from "axios";
import type {
  Line,
  LineDetails,
  NormalizedTrafficStatus,
  NearestStationResult,
  Schedule,
  WebhookSubscription,
  LineSnapshot,
  WorkerStatusInfo,
  TaskRunInfo,
  QueueMetrics,
  SnapshotRecord,
  DatabaseSummary,
  SystemLogEntry,
} from "@/types";

const DEFAULT_BACKEND_PORT = process.env.NEXT_PUBLIC_BACKEND_PORT || "8000";
const SYSTEM_API_TOKEN = process.env.NEXT_PUBLIC_SYSTEM_API_KEY || "";

function resolveBaseUrl(): string {
  if (typeof window !== "undefined") {
    try {
      const url = new URL(window.location.href);
      return `${url.protocol}//${url.hostname}:${DEFAULT_BACKEND_PORT}`;
    } catch (error) {
      console.error("Failed to resolve backend host from window.location", error);
    }
  }

  const envHost = process.env.NEXT_PUBLIC_BACKEND_HOST || "127.0.0.1";
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
  if (SYSTEM_API_TOKEN) {
    config.headers = config.headers ?? {};
    config.headers["X-API-Key"] = SYSTEM_API_TOKEN;
  }
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

  async getLineDetails(
    transportType: string,
    lineCode: string
  ): Promise<LineDetails> {
    const { data } = await api.get(`/api/lines/${transportType}/${lineCode}`);
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
  ): Promise<WebhookSubscription> {
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

  async getLineSnapshot(
    network: string,
    lineCode: string,
    refresh = false
  ): Promise<LineSnapshot> {
    const params = refresh ? { refresh: true } : {};
    const { data } = await api.get(`/api/snapshots/${network}/${lineCode}`, { params });
    return data;
  },

  async getSystemWorkers(): Promise<WorkerStatusInfo[]> {
    const { data } = await api.get("/api/system/workers");
    return data.workers ?? [];
  },

  async getRecentTaskRuns(limit = 25): Promise<TaskRunInfo[]> {
    const { data } = await api.get("/api/system/tasks/recent", { params: { limit } });
    return data.items ?? [];
  },

  async getQueueMetrics(): Promise<QueueMetrics> {
    const { data } = await api.get("/api/system/queue");
    return data;
  },

  async getDatabaseSummary(): Promise<DatabaseSummary> {
    const { data } = await api.get("/api/system/db/summary");
    return data;
  },

  async getDatabaseSnapshots(options?: {
    limit?: number;
    network?: string;
    line?: string;
    includePayload?: boolean;
  }): Promise<SnapshotRecord[]> {
    const params: Record<string, unknown> = {};
    if (options?.limit) params.limit = options.limit;
    if (options?.network) params.network = options.network;
    if (options?.line) params.line = options.line;
    if (options?.includePayload) params.include_payload = options.includePayload;
    const { data } = await api.get("/api/system/db/snapshots", { params });
    return data.items ?? [];
  },

  async getSystemLogs(options?: {
    limit?: number;
    service?: string;
    level?: string;
    search?: string;
    since?: string;
  }): Promise<SystemLogEntry[]> {
    const params: Record<string, unknown> = {};
    if (options?.limit) params.limit = options.limit;
    if (options?.service) params.service = options.service;
    if (options?.level) params.level = options.level;
    if (options?.search) params.search = options.search;
    if (options?.since) params.since = options.since;
    const { data } = await api.get("/api/system/logs", { params });
    return data.items ?? [];
  },

  async sendWorkerCommand(workerId: string, command: string): Promise<void> {
    await api.post(`/api/system/workers/${workerId}/command`, null, {
      params: { command },
    });
  },

  async triggerSchedulerRun(): Promise<void> {
    await api.post("/api/system/scheduler/run", null);
  },

  async scaleWorkers(payload: { count?: number; delta?: number }): Promise<{ count: number }> {
    const { data } = await api.post("/api/system/workers/scale", payload);
    return { count: data.count };
  },
};
