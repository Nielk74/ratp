"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiClient } from "@/services/api";
import type { QueueMetrics, TaskRunInfo, WorkerStatusInfo } from "@/types";

const COMMANDS = ["PAUSE", "RESUME", "DRAIN", "RELOAD_CONFIG"];

interface CommandState {
  loading: boolean;
  message: string | null;
  error: string | null;
}

export default function OrchestratorDashboard() {
  const [workers, setWorkers] = useState<WorkerStatusInfo[]>([]);
  const [tasks, setTasks] = useState<TaskRunInfo[]>([]);
  const [queue, setQueue] = useState<QueueMetrics | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [commandState, setCommandState] = useState<CommandState>({ loading: false, message: null, error: null });

  const fetchData = useCallback(async () => {
    try {
      setRefreshing(true);
      const [workerData, taskData, queueData] = await Promise.all([
        apiClient.getSystemWorkers(),
        apiClient.getRecentTaskRuns(25),
        apiClient.getQueueMetrics(),
      ]);
      setWorkers(workerData);
      setTasks(taskData);
      setQueue(queueData);
    } catch (error) {
      console.error("Failed to fetch orchestrator data", error);
    } finally {
      setRefreshing(false);
    }
  }, []);

  const handleCommand = useCallback(
    async (workerId: string, command: string) => {
      try {
        setCommandState({ loading: true, message: null, error: null });
        await apiClient.sendWorkerCommand(workerId, command);
        setCommandState({ loading: false, message: `Command ${command} queued`, error: null });
        await fetchData();
      } catch (error) {
        console.error(error);
        setCommandState({ loading: false, message: null, error: `Unable to send ${command}` });
      }
    },
    [fetchData],
  );

  const handleSchedulerTrigger = useCallback(
    async () => {
      try {
        setCommandState({ loading: true, message: null, error: null });
        await apiClient.triggerSchedulerRun();
        setCommandState({ loading: false, message: "Scheduler triggered", error: null });
        await fetchData();
      } catch (error) {
        console.error(error);
        setCommandState({ loading: false, message: null, error: "Failed to trigger scheduler" });
      }
    },
    [fetchData],
  );

  const handleScale = useCallback(
    async (delta: number) => {
      const target = Math.max(0, workers.length + delta);
      if (target === workers.length) {
        return;
      }
      try {
        setCommandState({ loading: true, message: null, error: null });
        await apiClient.scaleWorkers(target);
        setCommandState({ loading: false, message: `Scaled worker pool to ${target}`, error: null });
        await fetchData();
      } catch (error) {
        console.error(error);
        setCommandState({ loading: false, message: null, error: "Unable to scale workers" });
      }
    },
    [fetchData, workers.length],
  );

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const pendingTasks = useMemo(
    () => tasks.filter((task) => ["queued", "pending", "running"].includes(task.status)).length,
    [tasks],
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-200">
        <div className="container mx-auto px-4 py-6">
          <h1 className="text-2xl font-semibold text-gray-900">Orchestrator Dashboard</h1>
          <p className="text-sm text-gray-600 mt-2">
            Monitor scheduler, Kafka queue, and worker fleet. Use the controls below to manage the system.
          </p>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              onClick={fetchData}
              className="px-3 py-2 rounded-md bg-primary text-white text-sm shadow hover:bg-primary/90 disabled:opacity-60"
              disabled={refreshing}
            >
              {refreshing ? "Refreshing..." : "Refresh data"}
            </button>
            <button
              onClick={handleSchedulerTrigger}
              className="px-3 py-2 rounded-md bg-emerald-600 text-white text-sm shadow hover:bg-emerald-500 disabled:opacity-60"
              disabled={commandState.loading}
            >
              Trigger scheduler run
            </button>
            <button
              onClick={() => handleScale(1)}
              className="px-3 py-2 rounded-md bg-blue-600 text-white text-sm shadow hover:bg-blue-500 disabled:opacity-60"
              disabled={commandState.loading}
            >
              Add worker
            </button>
            <button
              onClick={() => handleScale(-1)}
              className="px-3 py-2 rounded-md bg-rose-600 text-white text-sm shadow hover:bg-rose-500 disabled:opacity-60"
              disabled={commandState.loading || workers.length === 0}
            >
              Remove worker
            </button>
            <span className="text-sm text-gray-600">Active workers: {workers.length}</span>
            {commandState.message && <span className="text-sm text-green-600">{commandState.message}</span>}
            {commandState.error && <span className="text-sm text-red-600">{commandState.error}</span>}
          </div>
        </div>
      </div>

      <main className="container mx-auto px-4 py-8 space-y-8">
        <section className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Queue Overview</h2>
          <p className="text-sm text-gray-600 mb-4">Real-time status of scheduler output and worker backlog.</p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="p-4 border rounded-lg">
              <p className="text-sm text-gray-500">Pending tasks</p>
              <p className="text-2xl font-semibold text-gray-900">{queue?.pending ?? pendingTasks}</p>
            </div>
            <div className="p-4 border rounded-lg">
              <p className="text-sm text-gray-500">Total scheduled</p>
              <p className="text-2xl font-semibold text-gray-900">{queue?.total ?? tasks.length}</p>
            </div>
            <div className="p-4 border rounded-lg">
              <p className="text-sm text-gray-500">Last scheduled run</p>
              <p className="text-base text-gray-900">
                {queue?.last_scheduled_at ? new Date(queue.last_scheduled_at).toLocaleTimeString() : "Not available"}
              </p>
            </div>
          </div>
        </section>

        <section className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Worker Fleet</h2>
              <p className="text-sm text-gray-600">Manage worker nodes and review their latest heartbeat.</p>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Worker</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Status</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Host</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Last heartbeat</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Metrics</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {workers.map((worker) => (
                  <tr key={worker.worker_id}>
                    <td className="px-4 py-2 font-medium text-gray-900">{worker.worker_id}</td>
                    <td className="px-4 py-2 capitalize text-gray-700">{worker.status}</td>
                    <td className="px-4 py-2 text-gray-600">{worker.host ?? "-"}</td>
                    <td className="px-4 py-2 text-gray-600">
                      {worker.last_heartbeat ? new Date(worker.last_heartbeat).toLocaleTimeString() : "-"}
                    </td>
                    <td className="px-4 py-2 text-gray-600 whitespace-pre-line text-xs">
                      {worker.metrics && Object.keys(worker.metrics).length > 0
                        ? JSON.stringify(worker.metrics, null, 2)
                        : "No metrics"}
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex flex-wrap gap-2">
                        {COMMANDS.map((command) => (
                          <button
                            key={`${worker.worker_id}-${command}`}
                            className="px-3 py-1 rounded border text-xs hover:bg-gray-100 disabled:opacity-50"
                            disabled={commandState.loading}
                            onClick={() => handleCommand(worker.worker_id, command)}
                          >
                            {command}
                          </button>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
                {workers.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-6 text-center text-gray-500 text-sm">
                      No workers have reported yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Recent Task Runs</h2>
          <p className="text-sm text-gray-600 mb-4">Inspect the latest fetch executions.</p>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-gray-600">Job</th>
                  <th className="px-4 py-2 text-left text-gray-600">Line</th>
                  <th className="px-4 py-2 text-left text-gray-600">Status</th>
                  <th className="px-4 py-2 text-left text-gray-600">Worker</th>
                  <th className="px-4 py-2 text-left text-gray-600">Started</th>
                  <th className="px-4 py-2 text-left text-gray-600">Finished</th>
                  <th className="px-4 py-2 text-left text-gray-600">Error</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {tasks.map((task) => (
                  <tr key={task.job_id}>
                    <td className="px-4 py-2 text-gray-700 font-mono text-xs">{task.job_id}</td>
                    <td className="px-4 py-2 text-gray-700">
                      {task.network} {task.line}
                    </td>
                    <td className="px-4 py-2 text-gray-700 capitalize">{task.status}</td>
                    <td className="px-4 py-2 text-gray-600">{task.worker_id ?? "-"}</td>
                    <td className="px-4 py-2 text-gray-600">
                      {task.started_at ? new Date(task.started_at).toLocaleTimeString() : "-"}
                    </td>
                    <td className="px-4 py-2 text-gray-600">
                      {task.finished_at ? new Date(task.finished_at).toLocaleTimeString() : "-"}
                    </td>
                    <td className="px-4 py-2 text-xs text-red-600 whitespace-pre-line">
                      {task.error_message ?? ""}
                    </td>
                  </tr>
                ))}
                {tasks.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-6 text-center text-gray-500 text-sm">
                      No tasks recorded yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
}
