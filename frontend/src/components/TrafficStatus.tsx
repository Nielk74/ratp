"use client";

import { Line, TrafficData } from "@/types";
import { useMemo } from "react";

import { LineCard } from "./LineCard";
import {
  buildLineStatusKey,
  buildLineStatusMap,
  getLineStatus,
  sourceLabel,
} from "@/utils/traffic";

interface TrafficStatusProps {
  traffic: TrafficData | null;
  lines: Line[];
}

export function TrafficStatus({ traffic, lines }: TrafficStatusProps) {
  const statusMap = useMemo(() => buildLineStatusMap(traffic), [traffic]);
  const hasLines = lines.length > 0;

  const hasLiveData = useMemo(() => {
    return Object.values(statusMap).some(
      (status) => status.source !== "fallback",
    );
  }, [statusMap]);

  if (!traffic || !hasLines) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-2xl font-bold mb-4">Traffic Status</h2>
        <p className="text-gray-500">No traffic data available</p>
      </div>
    );
  }

  const advisoryMessage = !hasLiveData
    ? traffic.message ?? "Live data unavailable. Please configure PRIM API access."
    : undefined;

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="p-6 border-b border-gray-200">
        <h2 className="text-2xl font-bold text-gray-900">Metro Lines Status</h2>
        <p className="text-sm text-gray-500 mt-1">
          Last updated: {new Date().toLocaleTimeString()}
        </p>
      </div>

      <div className="p-6">
        {advisoryMessage && (
          <div className="mb-6 rounded-lg border border-warning/40 bg-warning/10 px-4 py-3 text-sm text-warning">
            {advisoryMessage}
          </div>
        )}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {lines.map((line) => {
            const status = getLineStatus(line, statusMap, traffic);
            return (
              <LineCard
                key={buildLineStatusKey(line)}
                line={line}
                status={status}
              />
            );
          })}
        </div>
        {hasLiveData && (
          <p className="mt-6 text-xs text-gray-500">
            Data source: {sourceLabel("prim")} (fallback to community API when available)
          </p>
        )}
      </div>
    </div>
  );
}
