"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiClient } from "@/services/api";
import type { DatabaseSummary, SnapshotRecord, ScrapedDepartureInfo } from "@/types";

const REFRESH_INTERVAL_MS = 15000;
const SNAPSHOT_LIMIT_OPTIONS = [10, 20, 25, 50, 100];

type SnapshotStatus = "success" | "error" | string;

interface DepartureSummary {
  id: string;
  snapshotId: number;
  network: string;
  line: string;
  station: string;
  direction?: string;
  destination?: string;
  waitingTime?: string;
  status?: string;
  scrapedAt?: string | null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function coerceDisplayString(value: unknown): string | undefined {
  if (typeof value === "string" && value.trim()) {
    return value.trim();
  }
  return undefined;
}

function collectDepartures(snapshot: SnapshotRecord, stationsPerSnapshot = 4, departuresPerStation = 3): DepartureSummary[] {
  if (!isRecord(snapshot.payload)) {
    return [];
  }
  const payload = snapshot.payload as Record<string, unknown>;
  const stationsRaw = payload["stations"];
  if (!Array.isArray(stationsRaw)) {
    return [];
  }
  const scrapedAt = coerceDisplayString(payload["scraped_at"]);
  const result: DepartureSummary[] = [];
  stationsRaw.slice(0, stationsPerSnapshot).forEach((stationRaw, stationIndex) => {
    if (!isRecord(stationRaw)) {
      return;
    }
    const stationName = coerceDisplayString(stationRaw["name"]) ?? `Station ${stationIndex + 1}`;
    const direction = coerceDisplayString(stationRaw["direction"]);
    const departures = Array.isArray(stationRaw["departures"]) ? stationRaw["departures"] : [];
    (departures as ScrapedDepartureInfo[]).slice(0, departuresPerStation).forEach((departure, departureIndex) => {
      if (!departure) {
        return;
      }
      let destination = coerceDisplayString(departure.destination);
      if (!destination && departure.extra && typeof departure.extra === "object") {
        destination = coerceDisplayString((departure.extra as Record<string, unknown>)["destination"]);
      }
      const waitingTime = coerceDisplayString(departure.waiting_time) ?? departure.raw_text;
      result.push({
        id: `${snapshot.id}-${stationIndex}-${departureIndex}`,
        snapshotId: snapshot.id,
        network: snapshot.network,
        line: snapshot.line,
        station: stationName,
        direction,
        destination,
        waitingTime,
        status: coerceDisplayString(departure.status),
        scrapedAt: scrapedAt ?? snapshot.fetched_at ?? null,
      });
    });
  });
  return result;
}

function formatPayloadPreview(payload: unknown, maxLength = 400): string {
  if (payload === null || payload === undefined) {
    return "No payload";
  }
  try {
    const json = JSON.stringify(payload, null, 2);
    if (json.length <= maxLength) {
      return json;
    }
    return `${json.slice(0, maxLength)}...`;
  } catch (error) {
    console.error("Unable to format payload preview", error);
    return "Unable to display payload";
  }
}

function formatJson(value: unknown): string {
  if (value === null || value === undefined) {
    return "{}";
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch (error) {
    console.error("Unable to format JSON", error);
    return "{}";
  }
}

function formatTimestamp(value?: string | null): string {
  if (!value) {
    return "-";
  }
  try {
    const date = new Date(value);
    return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
  } catch (error) {
    return value;
  }
}

export default function DatabaseDashboard(): JSX.Element {
  const [summary, setSummary] = useState<DatabaseSummary | null>(null);
  const [snapshots, setSnapshots] = useState<SnapshotRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [networkFilter, setNetworkFilter] = useState("");
  const [lineFilter, setLineFilter] = useState("");
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [includePayload, setIncludePayload] = useState(false);
  const [limit, setLimit] = useState(25);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [summaryData, snapshotData] = await Promise.all([
        apiClient.getDatabaseSummary(),
        apiClient.getDatabaseSnapshots({
          limit,
          includePayload,
          network: networkFilter || undefined,
          line: lineFilter || undefined,
        }),
      ]);
      setSummary(summaryData);
      setSnapshots(snapshotData);
      setLastUpdated(new Date().toISOString());
    } catch (err) {
      console.error("Failed to fetch database dashboard data", err);
      setError("Unable to load database metrics. Please try again.");
    } finally {
      setLoading(false);
    }
  }, [networkFilter, lineFilter, limit, includePayload]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (!autoRefresh) {
      return undefined;
    }
    const timer = setInterval(() => {
      fetchData();
    }, REFRESH_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [autoRefresh, fetchData]);

  useEffect(() => {
    setLineFilter("");
  }, [networkFilter]);

  const totalTaskCount = useMemo(() => {
    if (!summary) {
      return 0;
    }
    return Object.values(summary.task_counts).reduce((total, count) => total + count, 0);
  }, [summary]);

  const taskStatusEntries = useMemo(() => {
    if (!summary) {
      return [] as Array<[string, number]>;
    }
    return Object.entries(summary.task_counts).sort((a, b) => b[1] - a[1]);
  }, [summary]);

  const workerStatusEntries = useMemo(() => {
    if (!summary) {
      return [] as Array<[string, number]>;
    }
    return Object.entries(summary.worker_counts).sort((a, b) => b[1] - a[1]);
  }, [summary]);

  const latestSnapshot = snapshots[0];

  const departureHighlights = useMemo(() => {
    const rows: DepartureSummary[] = [];
    for (const snapshot of snapshots) {
      rows.push(...collectDepartures(snapshot));
    }
    return rows.slice(0, 30);
  }, [snapshots]);

  const departuresByLine = useMemo(() => {
    const aggregator = new Map<string, number>();
    for (const departure of departureHighlights) {
      const label = `${departure.network?.toUpperCase() ?? ""} ${departure.line ?? ""}`.trim() || "Unknown";
      aggregator.set(label, (aggregator.get(label) ?? 0) + 1);
    }
    return Array.from(aggregator.entries()).sort((a, b) => b[1] - a[1]);
  }, [departureHighlights]);

  const snapshotStatusCounts = useMemo(() => {
    const counts: Record<SnapshotStatus, number> = {};
    for (const snapshot of snapshots) {
      const status = snapshot.status as SnapshotStatus;
      counts[status] = (counts[status] ?? 0) + 1;
    }
    return counts;
  }, [snapshots]);

  const networkOptions = useMemo(() => {
    const unique = new Set<string>();
    for (const snapshot of snapshots) {
      if (snapshot.network) {
        unique.add(snapshot.network);
      }
    }
    const options = Array.from(unique);
    options.sort();
    return options;
  }, [snapshots]);

  const lineOptions = useMemo(() => {
    const unique = new Set<string>();
    for (const snapshot of snapshots) {
      if (networkFilter && snapshot.network !== networkFilter) {
        continue;
      }
      if (snapshot.line) {
        unique.add(snapshot.line);
      }
    }
    const options = Array.from(unique);
    options.sort();
    return options;
  }, [snapshots, networkFilter]);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-200">
        <div className="container mx-auto px-4 py-6">
          <h1 className="text-2xl font-semibold text-gray-900">Database Dashboard</h1>
          <p className="text-sm text-gray-600 mt-2">
            Observe live database activity for orchestrator artifacts. Filter by network and line to drill into recent snapshots.
          </p>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              onClick={fetchData}
              className="px-3 py-2 rounded-md bg-primary text-white text-sm shadow hover:bg-primary/90 disabled:opacity-60"
              disabled={loading}
            >
              {loading ? "Refreshing..." : "Refresh now"}
            </button>
            <label className="flex items-center gap-2 text-sm text-gray-600">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-gray-300"
                checked={autoRefresh}
                onChange={(event) => setAutoRefresh(event.target.checked)}
              />
              Auto refresh ({Math.round(REFRESH_INTERVAL_MS / 1000)}s)
            </label>
            <label className="flex items-center gap-2 text-sm text-gray-600">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-gray-300"
                checked={includePayload}
                onChange={(event) => setIncludePayload(event.target.checked)}
              />
              Include payload data
            </label>
            {lastUpdated && (
              <span className="text-sm text-gray-500">
                Last updated {formatTimestamp(lastUpdated)}
              </span>
            )}
            {error && <span className="text-sm text-red-600">{error}</span>}
          </div>
        </div>
      </div>

      <main className="container mx-auto px-4 py-8 space-y-8">
        <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <div className="bg-white rounded-lg shadow p-4 border border-gray-100">
            <p className="text-xs uppercase tracking-wide text-gray-500">Active workers</p>
            <p className="text-3xl font-semibold text-gray-900 mt-2">{summary?.active_workers ?? 0}</p>
            <p className="text-xs text-gray-500">Total workers: {summary?.total_workers ?? 0}</p>
          </div>
          <div className="bg-white rounded-lg shadow p-4 border border-gray-100">
            <p className="text-xs uppercase tracking-wide text-gray-500">Task records</p>
            <p className="text-3xl font-semibold text-gray-900 mt-2">{totalTaskCount}</p>
            <p className="text-xs text-gray-500">Statuses tracked in TaskRun table</p>
          </div>
          <div className="bg-white rounded-lg shadow p-4 border border-gray-100">
            <p className="text-xs uppercase tracking-wide text-gray-500">Snapshot samples</p>
            <p className="text-3xl font-semibold text-gray-900 mt-2">{snapshots.length}</p>
            <p className="text-xs text-gray-500">Fetched with limit {limit}</p>
          </div>
          <div className="bg-white rounded-lg shadow p-4 border border-gray-100">
            <p className="text-xs uppercase tracking-wide text-gray-500">Latest snapshot</p>
            <p className="text-sm font-semibold text-gray-900 mt-2">
              {latestSnapshot ? `${latestSnapshot.network?.toUpperCase() ?? ""} ${latestSnapshot.line ?? ""}`.trim() || "Unnamed" : "No data"}
            </p>
            <p className="text-xs text-gray-500">{latestSnapshot ? formatTimestamp(latestSnapshot.fetched_at) : "Waiting for data"}</p>
          </div>
          <div className="bg-white rounded-lg shadow p-4 border border-gray-100">
            <p className="text-xs uppercase tracking-wide text-gray-500">Departure samples</p>
            <p className="text-3xl font-semibold text-gray-900 mt-2">{departureHighlights.length}</p>
            <p className="text-xs text-gray-500">Based on latest snapshot payloads</p>
          </div>
        </section>

        <section className="bg-white rounded-lg shadow p-6">
          <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Snapshot stream</h2>
              <p className="text-sm text-gray-600">Filter by network and line. Data refreshes automatically.</p>
            </div>
            <div className="flex flex-wrap items-end gap-4">
              <label className="text-sm text-gray-700">
                <span className="block text-xs uppercase tracking-wide text-gray-500">Network</span>
                <select
                  value={networkFilter}
                  onChange={(event) => setNetworkFilter(event.target.value)}
                  className="mt-1 block rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none"
                >
                  <option value="">All networks</option>
                  {networkOptions.map((network) => (
                    <option key={network} value={network}>
                      {network.toUpperCase()}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-sm text-gray-700">
                <span className="block text-xs uppercase tracking-wide text-gray-500">Line</span>
                <select
                  value={lineFilter}
                  onChange={(event) => setLineFilter(event.target.value)}
                  className="mt-1 block rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none"
                  disabled={!networkFilter && lineOptions.length === 0}
                >
                  <option value="">All lines</option>
                  {lineOptions.map((line) => (
                    <option key={line} value={line}>
                      {line}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-sm text-gray-700">
                <span className="block text-xs uppercase tracking-wide text-gray-500">Limit</span>
                <select
                  value={limit}
                  onChange={(event) => setLimit(Number(event.target.value))}
                  className="mt-1 block rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none"
                >
                  {SNAPSHOT_LIMIT_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Network</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Line</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Status</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Fetched</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Stations</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Scheduler run</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Error</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Inspect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {snapshots.map((snapshot) => (
                  <tr key={snapshot.id} className="align-top">
                    <td className="px-4 py-2 font-medium text-gray-900 uppercase">{snapshot.network}</td>
                    <td className="px-4 py-2 text-gray-700">{snapshot.line}</td>
                    <td className="px-4 py-2 capitalize text-gray-700">{snapshot.status}</td>
                    <td className="px-4 py-2 text-gray-600">{formatTimestamp(snapshot.fetched_at)}</td>
                    <td className="px-4 py-2 text-gray-600">{typeof snapshot.station_count === "number" ? snapshot.station_count : "-"}</td>
                    <td className="px-4 py-2 text-gray-600 text-xs">{snapshot.scheduler_run_id ?? "-"}</td>
                    <td className="px-4 py-2 text-xs text-red-600 whitespace-pre-line">{snapshot.error_message ?? ""}</td>
                    <td className="px-4 py-2 text-xs text-gray-700 max-w-xs">
                      <details>
                        <summary className="cursor-pointer text-primary hover:underline">View data</summary>
                        <div className="mt-2 space-y-3">
                          <div>
                            <p className="font-medium text-gray-700">Context</p>
                            <pre className="mt-1 whitespace-pre-wrap rounded bg-gray-100 p-2 text-[11px] text-gray-700">
                              {formatJson(snapshot.context)}
                            </pre>
                          </div>
                          {includePayload && (
                            <div>
                              <p className="font-medium text-gray-700">Payload</p>
                              <pre className="mt-1 whitespace-pre-wrap rounded bg-gray-100 p-2 text-[11px] text-gray-700">
                                {formatPayloadPreview(snapshot.payload)}
                              </pre>
                            </div>
                          )}
                        </div>
                      </details>
                    </td>
                  </tr>
                ))}
                {snapshots.length === 0 && (
                  <tr>
                    <td colSpan={8} className="px-4 py-6 text-center text-gray-500 text-sm">
                      No snapshots recorded for the selected filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="bg-white rounded-lg shadow p-6">
          <div className="flex flex-wrap items-start justify-between gap-4 mb-4">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Recent departure highlights</h2>
              <p className="text-sm text-gray-600">Quick view of the next departures extracted from the latest snapshot payloads.</p>
            </div>
            {!includePayload && (
              <span className="text-sm text-amber-600">Enable "Include payload data" above to populate departures.</span>
            )}
          </div>

          {includePayload ? (
            departureHighlights.length > 0 ? (
              <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-6">
                <div className="overflow-x-auto border border-gray-100 rounded-lg">
                  <table className="min-w-full divide-y divide-gray-200 text-sm">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left font-semibold text-gray-700">Line</th>
                        <th className="px-4 py-3 text-left font-semibold text-gray-700">Station</th>
                        <th className="px-4 py-3 text-left font-semibold text-gray-700">Destination</th>
                        <th className="px-4 py-3 text-left font-semibold text-gray-700">Waiting time</th>
                        <th className="px-4 py-3 text-left font-semibold text-gray-700">Status</th>
                        <th className="px-4 py-3 text-left font-semibold text-gray-700">Captured</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {departureHighlights.map((item) => (
                        <tr key={item.id}>
                          <td className="px-4 py-3 whitespace-nowrap text-gray-900">{`${item.network?.toUpperCase() ?? ""} ${item.line ?? ""}`.trim() || "Unknown"}</td>
                          <td className="px-4 py-3 text-gray-700">
                            <div className="font-medium text-gray-900">{item.station}</div>
                            {item.direction && <div className="text-xs text-gray-500">Direction {item.direction}</div>}
                          </td>
                          <td className="px-4 py-3 text-gray-700">{item.destination ?? "-"}</td>
                          <td className="px-4 py-3 text-gray-700">{item.waitingTime ?? "-"}</td>
                          <td className="px-4 py-3 text-gray-700">{item.status ?? "-"}</td>
                          <td className="px-4 py-3 text-gray-500 whitespace-nowrap">{formatTimestamp(item.scrapedAt)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="border border-gray-100 rounded-lg p-4 bg-gray-50">
                  <h3 className="text-sm font-semibold text-gray-800 uppercase tracking-wide">Samples by line</h3>
                  <ul className="mt-3 space-y-2 text-sm text-gray-700">
                    {departuresByLine.map(([label, count]) => (
                      <li key={label} className="flex items-center justify-between">
                        <span>{label}</span>
                        <span className="font-medium">{count}</span>
                      </li>
                    ))}
                    {departuresByLine.length === 0 && <li className="text-gray-500">No departures available.</li>}
                  </ul>
                </div>
              </div>
            ) : (
              <p className="text-sm text-gray-500">No departures found in the latest payloads.</p>
            )
          ) : (
            <p className="text-sm text-gray-500">Departure preview requires payload data. Toggle the checkbox above to include payloads in the snapshot fetch.</p>
          )}
        </section>

        <section className="bg-white rounded-lg shadow p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-3">Task status distribution</h2>
              <ul className="space-y-2 text-sm text-gray-700">
                {taskStatusEntries.map(([status, count]) => (
                  <li key={status} className="flex items-center justify-between">
                    <span className="capitalize">{status}</span>
                    <span className="font-medium">{count}</span>
                  </li>
                ))}
                {taskStatusEntries.length === 0 && <li className="text-gray-500">No task history found.</li>}
              </ul>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-3">Worker status distribution</h2>
              <ul className="space-y-2 text-sm text-gray-700">
                {workerStatusEntries.map(([status, count]) => (
                  <li key={status} className="flex items-center justify-between">
                    <span className="capitalize">{status}</span>
                    <span className="font-medium">{count}</span>
                  </li>
                ))}
                {workerStatusEntries.length === 0 && <li className="text-gray-500">No worker status entries.</li>}
              </ul>
            </div>
          </div>
        </section>

        <section className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Snapshot status summary</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {Object.entries(snapshotStatusCounts).map(([status, count]) => (
              <div key={status} className="border rounded-lg p-4">
                <p className="text-xs uppercase tracking-wide text-gray-500">{status}</p>
                <p className="text-2xl font-semibold text-gray-900 mt-2">{count}</p>
              </div>
            ))}
            {Object.keys(snapshotStatusCounts).length === 0 && (
              <p className="text-sm text-gray-500">No snapshots available to summarise.</p>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
