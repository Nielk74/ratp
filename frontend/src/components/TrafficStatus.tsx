"use client";

import { Line, TrafficData } from "@/types";
import { LineCard } from "./LineCard";

interface TrafficStatusProps {
  traffic: TrafficData | null;
  lines: Line[];
}

export function TrafficStatus({ traffic, lines }: TrafficStatusProps) {
  if (!traffic || !lines.length) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-2xl font-bold mb-4">Traffic Status</h2>
        <p className="text-gray-500">No traffic data available</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="p-6 border-b border-gray-200">
        <h2 className="text-2xl font-bold text-gray-900">Metro Lines Status</h2>
        <p className="text-sm text-gray-500 mt-1">
          Last updated: {new Date().toLocaleTimeString()}
        </p>
      </div>

      <div className="p-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {lines.map((line) => (
            <LineCard key={line.code} line={line} traffic={traffic} />
          ))}
        </div>
      </div>
    </div>
  );
}
