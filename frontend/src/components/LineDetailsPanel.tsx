"use client";

import type { Line, LineDetails, LineStatusInfo, LineStation } from "@/types";
import { sourceLabel } from "@/utils/traffic";

interface LineDetailsPanelProps {
  line: Line | null;
  status: LineStatusInfo | null;
  details: LineDetails | null;
  loading: boolean;
}

function formatStationName(station: LineStation, index: number): string {
  if (station.name) {
    return station.name;
  }
  if (station.slug) {
    return station.slug.replace("-", " ");
  }
  return `Stop ${index + 1}`;
}

export function LineDetailsPanel({
  line,
  status,
  details,
  loading,
}: LineDetailsPanelProps) {
  if (!line) {
    return (
      <div className="bg-white rounded-xl shadow p-6">
        <p className="text-gray-500 text-sm">
          Select a line to view live details and station information.
        </p>
      </div>
    );
  }

  const activeStatus = status ?? {
    level: "unknown",
    label: "Status unavailable",
    message: "No live information available.",
    source: "fallback",
  };

  return (
    <div className="bg-white rounded-xl shadow p-6 h-full flex flex-col">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">
            Line {line.code}
          </h2>
          <p className="text-sm text-gray-500">{line.name}</p>
        </div>
        <div
          className="w-12 h-12 rounded-full flex items-center justify-center text-white font-semibold"
          style={{ backgroundColor: line.color || "#111" }}
        >
          {line.code}
        </div>
      </div>

      <div className="mt-6 space-y-3">
        <div>
          <p className="text-sm font-medium text-gray-700">Live status</p>
          <p className="text-base font-semibold text-gray-900">
            {activeStatus.label}
          </p>
          {activeStatus.message && (
            <p className="text-sm text-gray-600">{activeStatus.message}</p>
          )}
          <p className="text-xs text-gray-400 mt-1">
            Source: {sourceLabel(activeStatus.source ?? "fallback")}
          </p>
        </div>

        <div>
          <p className="text-sm font-medium text-gray-700">Transport type</p>
          <p className="text-sm text-gray-600 uppercase tracking-wide">
            {line.type}
          </p>
        </div>
      </div>

      <div className="mt-6 flex-1 overflow-hidden flex flex-col">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
            Stations
          </h3>
          <span className="text-xs text-gray-500">
            {details?.stations_count ?? 0} stops
          </span>
        </div>

        <div className="mt-3 flex-1 overflow-y-auto rounded-lg border border-gray-200">
          {loading ? (
            <div className="p-4 text-sm text-gray-500">Loading stations...</div>
          ) : details && details.stations.length > 0 ? (
            <ul className="divide-y divide-gray-100">
              {details.stations.map((station, index) => (
                <li key={`${station.slug ?? index}`} className="px-4 py-2 text-sm text-gray-700">
                  {formatStationName(station, index)}
                </li>
              ))}
            </ul>
          ) : (
            <div className="p-4 text-sm text-gray-500">
              Station data is not available yet for this line.
            </div>
          )}
        </div>
      </div>

      <div className="mt-6 text-sm text-gray-500">
        Manage Discord alerts for this line on the{" "}
        <a href="/webhooks" className="text-primary hover:underline">
          Webhooks page
        </a>
        .
      </div>
    </div>
  );
}
