"use client";

import type { Line, LineStatusInfo } from "@/types";
import { sourceLabel } from "@/utils/traffic";

interface LineCardProps {
  line: Line;
  status: LineStatusInfo;
  isActive?: boolean;
  onSelect?: (line: Line) => void;
}

const STATUS_DOT_COLORS: Record<LineStatusInfo["level"], string> = {
  normal: "bg-success",
  warning: "bg-warning",
  disrupted: "bg-error",
  closed: "bg-error",
  unknown: "bg-gray-300",
};

const STATUS_TEXT_COLORS: Record<LineStatusInfo["level"], string> = {
  normal: "text-success",
  warning: "text-warning",
  disrupted: "text-error",
  closed: "text-error",
  unknown: "text-gray-500",
};

export function LineCard({ line, status, isActive = false, onSelect }: LineCardProps) {
  const dotColor = STATUS_DOT_COLORS[status.level] ?? "bg-gray-300";
  const textColor = STATUS_TEXT_COLORS[status.level] ?? "text-gray-500";
  const showSource = status.source !== "fallback";
  const handleClick = () => {
    if (onSelect) {
      onSelect(line);
    }
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      className={`w-full text-left border rounded-lg p-4 bg-white transition ${
        isActive ? "border-primary shadow-lg ring-2 ring-primary/20" : "border-gray-200 hover:shadow-md"
      }`}
    >
      <div className="flex items-center justify-between mb-3">
        <div
          className="w-12 h-12 rounded-full flex items-center justify-center text-white font-bold text-lg"
          style={{ backgroundColor: line.color || "#666" }}
        >
          {line.code}
        </div>
        <div className={`${dotColor} w-3 h-3 rounded-full`} title={status.label}></div>
      </div>

      <h3 className="font-semibold text-gray-900 text-sm mb-1">
        Line {line.code}
      </h3>
      <p className="text-xs text-gray-600 line-clamp-2">{line.name}</p>

      <div className="mt-3 pt-3 border-t border-gray-100 space-y-2">
        <span className={`text-xs font-medium ${textColor}`}>{status.label}</span>

        {status.message && (
          <p className="text-xs text-gray-600 line-clamp-3">{status.message}</p>
        )}

        {showSource && (
          <p className="text-[10px] uppercase tracking-wide text-gray-400">
            {sourceLabel(status.source)}
          </p>
        )}
      </div>
    </button>
  );
}
