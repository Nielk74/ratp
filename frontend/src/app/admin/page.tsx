"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { apiClient } from "@/services/api";
import type { DatabaseSummary, QueueMetrics, SnapshotRecord, WorkerStatusInfo } from "@/types";

const REFRESH_INTERVAL_MS = 30000;

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

export default function AdminIndex(): JSX.Element {
  const [workers, setWorkers] = useState<WorkerStatusInfo[]>([]);
  const [queueMetrics, setQueueMetrics] = useState<QueueMetrics | null>(null);
  const [dbSummary, setDbSummary] = useState<DatabaseSummary | null>(null);
  const [latestSnapshot, setLatestSnapshot] = useState<SnapshotRecord | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [workerData, queueData, summaryData, snapshotData] = await Promise.all([
        apiClient.getSystemWorkers(),
        apiClient.getQueueMetrics(),
        apiClient.getDatabaseSummary(),
        apiClient.getDatabaseSnapshots({ limit: 1 }),
      ]);
      setWorkers(workerData);
      setQueueMetrics(queueData);
      setDbSummary(summaryData);
      setLatestSnapshot(snapshotData[0] ?? null);
      setLastUpdated(new Date().toISOString());
    } catch (err) {
      console.error("Failed to load admin previews", err);
      setError("Unable to load admin previews. Please try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    const timer = setInterval(() => {
      refresh();
    }, REFRESH_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [refresh]);

  const totalWorkers = workers.length;
  const activeWorkers = useMemo(() => workers.filter((worker) => worker.status !== "lost" && worker.status !== "stopped").length, [workers]);
  const totalTasks = useMemo(() => {
    if (!dbSummary) {
      return 0;
    }
    return Object.values(dbSummary.task_counts).reduce((sum, count) => sum + count, 0);
  }, [dbSummary]);

  const latestSnapshotLabel = useMemo(() => {
    if (!latestSnapshot) {
      return "No data";
    }
    const network = latestSnapshot.network?.toUpperCase() ?? "";
    const line = latestSnapshot.line ?? "";
    const label = `${network} ${line}`.trim();
    return label || "Unnamed";
  }, [latestSnapshot]);

  const latestSnapshotStatus = latestSnapshot?.status ?? null;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-200">
        <div className="container mx-auto px-4 py-6">
          <h1 className="text-2xl font-semibold text-gray-900">Admin Control Center</h1>
          <p className="text-sm text-gray-600 mt-2">
            Quick overview of orchestration health and data snapshots. Navigate to detailed dashboards for deeper insight.
          </p>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              onClick={refresh}
              className="px-3 py-2 rounded-md bg-primary text-white text-sm shadow hover:bg-primary/90 disabled:opacity-60"
              disabled={loading}
            >
              {loading ? "Refreshing..." : "Refresh now"}
            </button>
            {lastUpdated && <span className="text-sm text-gray-500">Last updated {formatTimestamp(lastUpdated)}</span>}
            {error && <span className="text-sm text-red-600">{error}</span>}
          </div>
        </div>
      </div>

      <main className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <Link
            href="/admin/orchestrator"
            className="group block rounded-xl bg-white border border-gray-200 shadow-sm hover:shadow-md transition-shadow duration-150"
          >
            <div className="p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900">Orchestrator dashboard</h2>
                  <p className="text-sm text-gray-600">Manage worker fleet and queue lifecycle.</p>
                </div>
                <span className="text-primary text-sm font-medium group-hover:underline">Open</span>
              </div>
              <dl className="grid grid-cols-2 gap-4 text-sm text-gray-700">
                <div className="rounded-lg border border-gray-100 bg-gray-50 p-3">
                  <dt className="text-xs uppercase tracking-wide text-gray-500">Active workers</dt>
                  <dd className="text-lg font-semibold text-gray-900">{activeWorkers}</dd>
                </div>
                <div className="rounded-lg border border-gray-100 bg-gray-50 p-3">
                  <dt className="text-xs uppercase tracking-wide text-gray-500">Total workers</dt>
                  <dd className="text-lg font-semibold text-gray-900">{totalWorkers}</dd>
                </div>
                <div className="rounded-lg border border-gray-100 bg-gray-50 p-3">
                  <dt className="text-xs uppercase tracking-wide text-gray-500">Pending tasks</dt>
                  <dd className="text-lg font-semibold text-gray-900">{queueMetrics?.pending ?? 0}</dd>
                </div>
                <div className="rounded-lg border border-gray-100 bg-gray-50 p-3">
                  <dt className="text-xs uppercase tracking-wide text-gray-500">Last scheduled run</dt>
                  <dd className="text-sm text-gray-700">{formatTimestamp(queueMetrics?.last_scheduled_at)}</dd>
                </div>
              </dl>
            </div>
          </Link>

          <Link
            href="/admin/logs"
            className="group block rounded-xl bg-white border border-gray-200 shadow-sm hover:shadow-md transition-shadow duration-150"
          >
            <div className="p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900">Log observatory</h2>
                  <p className="text-sm text-gray-600">Inspect centralized logs with filters and search.</p>
                </div>
                <span className="text-primary text-sm font-medium group-hover:underline">Open</span>
              </div>
              <dl className="grid grid-cols-2 gap-4 text-sm text-gray-700">
                <div className="rounded-lg border border-gray-100 bg-gray-50 p-3">
                  <dt className="text-xs uppercase tracking-wide text-gray-500">Latest status</dt>
                  <dd className="text-sm text-gray-900">{latestSnapshotStatus ?? "-"}</dd>
                </div>
                <div className="rounded-lg border border-gray-100 bg-gray-50 p-3">
                  <dt className="text-xs uppercase tracking-wide text-gray-500">Workers reporting</dt>
                  <dd className="text-lg font-semibold text-gray-900">{workers.length}</dd>
                </div>
              </dl>
            </div>
          </Link>

          <Link
            href="/admin/db"
            className="group block rounded-xl bg-white border border-gray-200 shadow-sm hover:shadow-md transition-shadow duration-150"
          >
            <div className="p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900">Database dashboard</h2>
                  <p className="text-sm text-gray-600">Inspect live snapshots and task history.</p>
                </div>
                <span className="text-primary text-sm font-medium group-hover:underline">Open</span>
              </div>
              <dl className="grid grid-cols-2 gap-4 text-sm text-gray-700">
                <div className="rounded-lg border border-gray-100 bg-gray-50 p-3">
                  <dt className="text-xs uppercase tracking-wide text-gray-500">Task records</dt>
                  <dd className="text-lg font-semibold text-gray-900">{totalTasks}</dd>
                </div>
                <div className="rounded-lg border border-gray-100 bg-gray-50 p-3">
                  <dt className="text-xs uppercase tracking-wide text-gray-500">Active workers</dt>
                  <dd className="text-lg font-semibold text-gray-900">{dbSummary?.active_workers ?? 0}</dd>
                </div>
                <div className="rounded-lg border border-gray-100 bg-gray-50 p-3">
                  <dt className="text-xs uppercase tracking-wide text-gray-500">Latest snapshot</dt>
                  <dd className="text-sm text-gray-700">
                    <span className="block text-base font-semibold text-gray-900">{latestSnapshotLabel}</span>
                    <span className="text-xs text-gray-500 capitalize">Status: {latestSnapshotStatus ?? "unknown"}</span>
                  </dd>
                </div>
                <div className="rounded-lg border border-gray-100 bg-gray-50 p-3">
                  <dt className="text-xs uppercase tracking-wide text-gray-500">Snapshot updated</dt>
                  <dd className="text-sm text-gray-700">{formatTimestamp(latestSnapshot?.fetched_at)}</dd>
                </div>
              </dl>
            </div>
          </Link>
        </div>
      </main>
    </div>
  );
}
