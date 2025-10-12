"use client";

import { Line, NormalizedTrafficStatus } from "@/types";
import { useMemo } from "react";

import { LineCard } from "./LineCard";
import {
  buildLineStatusKey,
  buildLineStatusMap,
  getLineStatus,
  sourceLabel,
} from "@/utils/traffic";

interface TrafficStatusProps {
  traffic: NormalizedTrafficStatus | null;
  lines: Line[];
  onSelectLine?: (line: Line) => void;
  selectedLineCode?: string | null;
}

export function TrafficStatus({ traffic, lines, onSelectLine, selectedLineCode }: TrafficStatusProps) {
  const statusMap = useMemo(() => buildLineStatusMap(traffic), [traffic]);
  const hasLines = lines.length > 0;

  const hasLiveData = !!(traffic && traffic.lines.length > 0);

  const lastUpdated = useMemo(() => {
    if (traffic?.timestamp) {
      const parsed = new Date(traffic.timestamp);
      return Number.isNaN(parsed.getTime()) ? null : parsed;
    }
    return null;
  }, [traffic?.timestamp]);

  const dataSourceLabel = useMemo(() => {
    if (!traffic?.source) return undefined;
    if (traffic.source === "prim_api") return sourceLabel("prim");
    if (traffic.source === "community_api") return sourceLabel("community");
    return undefined;
  }, [traffic?.source]);

  if (!hasLines) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-2xl font-bold mb-4">Traffic Status</h2>
        <p className="text-gray-500">No traffic data available</p>
      </div>
    );
  }

  const advisoryMessage = !hasLiveData
    ? traffic?.default.message ?? "Live data unavailable."
    : undefined;

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="p-6 border-b border-gray-200">
        <h2 className="text-2xl font-bold text-gray-900">Metro Lines Status</h2>
        <p className="text-sm text-gray-500 mt-1">
          Last updated: {lastUpdated ? lastUpdated.toLocaleTimeString() : "Not available"}
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
                isActive={selectedLineCode === line.code}
                onSelect={onSelectLine}
              />
            );
          })}
        </div>
        {dataSourceLabel && (
          <p className="mt-6 text-xs text-gray-500">
            Data source: {dataSourceLabel}
          </p>
        )}
      </div>
    </div>
  );
}
