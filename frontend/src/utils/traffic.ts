import {
  CommunityTrafficLine,
  Line,
  LineStatusInfo,
  LineStatusLevel,
  LineStatusSource,
  PrimTrafficLineReport,
  TrafficData,
} from "@/types";

const LEVEL_PRIORITY: Record<LineStatusLevel, number> = {
  normal: 0,
  warning: 1,
  disrupted: 2,
  closed: 3,
  unknown: 0,
};

const LEVEL_LABELS: Record<LineStatusLevel, string> = {
  normal: "Normal service",
  warning: "Minor disruption",
  disrupted: "Major disruption",
  closed: "Line closed",
  unknown: "Status unknown",
};

const COMMUNITY_SLUG_LEVEL: Record<string, LineStatusLevel> = {
  normal: "normal",
  ok: "normal",
  info: "warning",
  travaux: "warning",
  slowdown: "warning",
  ralentissement: "warning",
  perturbation: "warning",
  alerte: "disrupted",
  alerte_fermeture: "closed",
  alertefermeture: "closed",
  alertefermee: "closed",
  alerte_fermee: "closed",
  critical: "closed",
  unknow: "unknown",
};

const PRIM_SEVERITY_LEVEL: Record<string, LineStatusLevel> = {
  information: "warning",
  warning: "warning",
  caution: "warning",
  attention: "warning",
  disruption: "disrupted",
  disturbed: "disrupted",
  disturbance: "disrupted",
  significant: "disrupted",
  major: "disrupted",
  critical: "closed",
  blocking: "closed",
  very_important: "closed",
  no_service: "closed",
};

const PRIM_EFFECT_LEVEL: Record<string, LineStatusLevel> = {
  SIGNIFICANT_DELAYS: "disrupted",
  DELAYED: "warning",
  REDUCED_SERVICE: "disrupted",
  SHUTTLE_SERVICE: "disrupted",
  NO_SERVICE: "closed",
  OTHER_EFFECT: "warning",
};

const SOURCE_LABEL: Record<LineStatusSource, string> = {
  prim: "Île-de-France Mobilités",
  community: "Community API",
  fallback: "No live data",
};

function pickHigherLevel(
  current: LineStatusLevel,
  candidate: LineStatusLevel,
): LineStatusLevel {
  const currentPriority = LEVEL_PRIORITY[current] ?? 0;
  const candidatePriority = LEVEL_PRIORITY[candidate] ?? 0;
  return candidatePriority > currentPriority ? candidate : current;
}

function normaliseLineCode(code?: string | null): string | null {
  if (!code) return null;
  return code.trim().toUpperCase();
}

function resolvePrimSeverity(report: PrimTrafficLineReport): {
  level: LineStatusLevel;
  message?: string;
} {
  let level: LineStatusLevel = "normal";
  const messages: string[] = [];

  if (report.status?.message) {
    messages.push(report.status.message);
  } else if (report.status?.short_message) {
    messages.push(report.status.short_message);
  }

  if (report.disruption?.description) {
    messages.push(report.disruption.description);
  }

  if (report.impacts) {
    for (const impact of report.impacts) {
      if (impact.description) {
        messages.push(impact.description);
      }
      if (impact.severity) {
        level = pickHigherLevel(
          level,
          PRIM_SEVERITY_LEVEL[impact.severity.toLowerCase()] ?? "disrupted",
        );
      }
    }
  }

  if (report.status?.severity) {
    level = pickHigherLevel(
      level,
      PRIM_SEVERITY_LEVEL[report.status.severity.toLowerCase()] ?? "warning",
    );
  }

  if (report.disruption?.severity) {
    level = pickHigherLevel(
      level,
      PRIM_SEVERITY_LEVEL[report.disruption.severity.toLowerCase()] ??
        "disrupted",
    );
  }

  if (report.status?.effect) {
    level = pickHigherLevel(
      level,
      PRIM_EFFECT_LEVEL[report.status.effect] ?? "warning",
    );
  }

  return { level, message: messages.join(" ") || undefined };
}

function resolveCommunitySeverity(
  entry: CommunityTrafficLine,
): { level: LineStatusLevel; message?: string } {
  const slug = entry.slug?.toLowerCase() ?? "";
  let level = COMMUNITY_SLUG_LEVEL[slug];

  if (!level) {
    if (slug.includes("normal")) {
      level = "normal";
    } else if (slug.includes("ferme")) {
      level = "closed";
    } else if (slug.includes("ralent")) {
      level = "warning";
    } else if (slug.includes("perturb")) {
      level = "disrupted";
    } else {
      level = "unknown";
    }
  }

  const message = entry.message || entry.title;

  return { level, message };
}

export function buildLineStatusKey(line: Line): string {
  return normaliseLineCode(line.code) ?? line.code;
}

export function lineStatusLabel(level: LineStatusLevel): string {
  return LEVEL_LABELS[level] ?? LEVEL_LABELS.unknown;
}

export function sourceLabel(source: LineStatusSource): string {
  return SOURCE_LABEL[source] ?? SOURCE_LABEL.fallback;
}

export function buildLineStatusMap(
  traffic: TrafficData | null,
): Record<string, LineStatusInfo> {
  const statusByLine: Record<string, LineStatusInfo> = {};

  if (traffic?.data?.line_reports?.length) {
    for (const report of traffic.data.line_reports) {
      const code = normaliseLineCode(report.line?.code);
      if (!code) continue;

      const { level, message } = resolvePrimSeverity(report);
      const info: LineStatusInfo = {
        level,
        label: lineStatusLabel(level),
        message,
        source: "prim",
      };

      const existing = statusByLine[code];
      if (!existing || LEVEL_PRIORITY[level] >= LEVEL_PRIORITY[existing.level]) {
        statusByLine[code] = info;
      }
    }
  }

  if (traffic?.result) {
    const groups = [
      traffic.result.metros,
      traffic.result.rers,
      traffic.result.tramways,
      traffic.result.buses,
    ];

    for (const group of groups) {
      if (!group) continue;

      for (const entry of group) {
        const code = normaliseLineCode(entry.line);
        if (!code) continue;

        const { level, message } = resolveCommunitySeverity(entry);
        const info: LineStatusInfo = {
          level,
          label: lineStatusLabel(level),
          message,
          source: "community",
        };

        const existing = statusByLine[code];
        if (
          !existing ||
          (existing.source !== "prim" &&
            LEVEL_PRIORITY[level] >= LEVEL_PRIORITY[existing.level])
        ) {
          statusByLine[code] = info;
        }
      }
    }
  }

  return statusByLine;
}

export function getLineStatus(
  line: Line,
  statusMap: Record<string, LineStatusInfo>,
  traffic: TrafficData | null,
): LineStatusInfo {
  const code = buildLineStatusKey(line);
  return (
    statusMap[code] ?? {
      level: "unknown",
      label: lineStatusLabel("unknown"),
      message:
        traffic?.status === "unavailable"
          ? traffic.message
          : "Live status unavailable",
      source: "fallback",
    }
  );
}
