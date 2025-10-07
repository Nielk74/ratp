import type {
  Line,
  LineStatusInfo,
  LineStatusLevel,
  LineStatusSource,
  NormalizedTrafficStatus,
} from "@/types";

const LEVEL_LABELS: Record<LineStatusLevel, string> = {
  normal: "Normal service",
  warning: "Minor disruption",
  disrupted: "Major disruption",
  closed: "Line closed",
  unknown: "Status unknown",
};

const SOURCE_LABEL: Record<LineStatusSource, string> = {
  prim: "Île-de-France Mobilités",
  community: "Community API",
  fallback: "No live data",
};

export function lineStatusLabel(level: LineStatusLevel): string {
  return LEVEL_LABELS[level] ?? LEVEL_LABELS.unknown;
}

export function sourceLabel(source: LineStatusSource): string {
  return SOURCE_LABEL[source] ?? SOURCE_LABEL.fallback;
}

export function buildLineStatusKey(line: Line): string {
  return line.code.trim().toUpperCase();
}

export function buildLineStatusMap(
  traffic: NormalizedTrafficStatus | null,
): Record<string, LineStatusInfo> {
  if (!traffic) {
    return {};
  }

  return traffic.lines.reduce<Record<string, LineStatusInfo>>((acc, line) => {
    acc[line.line_code] = {
      line_code: line.line_code,
      level: line.level,
      label: lineStatusLabel(line.level),
      message: line.message,
      source: line.source,
      details: line.details,
    };
    return acc;
  }, {});
}

export function getLineStatus(
  line: Line,
  statusMap: Record<string, LineStatusInfo>,
  traffic: NormalizedTrafficStatus | null,
): LineStatusInfo {
  const code = buildLineStatusKey(line);
  const existing = statusMap[code];
  if (existing) {
    return existing;
  }

  if (traffic) {
    return {
      line_code: code,
      level: traffic.default.level,
      label: lineStatusLabel(traffic.default.level),
      message: traffic.default.message,
      source: traffic.default.level === "normal" ? "prim" : "fallback",
    };
  }

  return {
    line_code: code,
    level: "unknown",
    label: lineStatusLabel("unknown"),
    message: "Live status unavailable",
    source: "fallback",
  };
}
