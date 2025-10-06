"use client";

import { Line, TrafficData } from "@/types";

interface LineCardProps {
  line: Line;
  traffic: TrafficData;
}

export function LineCard({ line, traffic }: LineCardProps) {
  // Determine status from traffic data
  // This is simplified - real implementation would parse traffic.result
  const status = "normal"; // normal, disrupted, closed
  const statusColors = {
    normal: "bg-success",
    disrupted: "bg-warning",
    closed: "bg-error",
  };

  const statusText = {
    normal: "Normal",
    disrupted: "Disrupted",
    closed: "Closed",
  };

  return (
    <div className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition">
      <div className="flex items-center justify-between mb-3">
        <div
          className="w-12 h-12 rounded-full flex items-center justify-center text-white font-bold text-lg"
          style={{ backgroundColor: line.color || "#666" }}
        >
          {line.code}
        </div>
        <div
          className={`${statusColors[status]} w-3 h-3 rounded-full`}
          title={statusText[status]}
        ></div>
      </div>

      <h3 className="font-semibold text-gray-900 text-sm mb-1">
        Line {line.code}
      </h3>
      <p className="text-xs text-gray-600 line-clamp-2">{line.name}</p>

      <div className="mt-3 pt-3 border-t border-gray-100">
        <span
          className={`text-xs font-medium ${
            status === "normal"
              ? "text-success"
              : status === "disrupted"
              ? "text-warning"
              : "text-error"
          }`}
        >
          {statusText[status]}
        </span>
      </div>
    </div>
  );
}
