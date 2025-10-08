"use client";

import { useMemo } from "react";
import type { Line, LineSnapshot, LineSnapshotStation, TrainEstimate } from "@/types";

interface LineLiveMapProps {
  line: Line;
  snapshot: LineSnapshot | null;
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
}

function stationSorter(direction: string) {
  return (a: LineSnapshotStation, b: LineSnapshotStation) => {
    const aIndex = a.direction_index ?? a.order;
    const bIndex = b.direction_index ?? b.order;
    return direction === "A" ? bIndex - aIndex : aIndex - bIndex;
  };
}

function formatWait(departures: LineSnapshotStation["departures"]): string {
  if (!departures || departures.length === 0) {
    return "No data";
  }
  const primary = departures[0];
  if (!primary) {
    return "No data";
  }
  return primary.waiting_time || primary.status || primary.raw_text || "No data";
}

function directionLabel(direction: string, stations: LineSnapshotStation[]): string {
  const withDeparture = stations.find((station) => station.departures.length > 0);
  if (withDeparture) {
    const first = withDeparture.departures[0];
    if (first?.destination) {
      return `Direction ${first.destination}`;
    }
  }
  return `Direction ${direction}`;
}

function clamp(value: number, min = 0, max = 1): number {
  return Math.min(Math.max(value, min), max);
}

function resolveAbsolutePosition(train: TrainEstimate, stationCount: number): number {
  if (stationCount <= 1) {
    return 0;
  }
  return clamp(train.absolute_progress);
}

export function LineLiveMap({ line, snapshot, loading, error, onRefresh }: LineLiveMapProps) {
  const directions = useMemo(() => {
    if (!snapshot) {
      return [];
    }
    const dirKeys = Object.keys(snapshot.trains ?? {});
    return dirKeys.length ? dirKeys : ["A", "B"];
  }, [snapshot]);

  if (loading) {
    return <div className="p-4 text-sm text-gray-500">Loading live train positions...</div>;
  }

  if (error) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-error">{error}</p>
        <button
          type="button"
          className="px-3 py-2 text-sm rounded bg-primary text-white hover:bg-primary/90"
          onClick={onRefresh}
        >
          Retry
        </button>
      </div>
    );
  }

  if (!snapshot) {
    return (
      <p className="text-sm text-gray-500">
        No live snapshot is available yet for line {line.code}.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-gray-900">Live trains</h3>
          <p className="text-xs text-gray-500">
            Last refresh {new Date(snapshot.scraped_at).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}
          </p>
        </div>
        <button
          type="button"
          className="px-3 py-2 text-sm rounded bg-primary text-white hover:bg-primary/90"
          onClick={onRefresh}
        >
          Refresh
        </button>
      </div>

      {snapshot.errors.length > 0 && (
        <div className="rounded border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-700">
          {snapshot.errors.map((err) => (
            <p key={err}>{err}</p>
          ))}
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        {directions.map((direction) => {
          const directionStations = [...(snapshot.stations ?? [])]
            .filter((station) => station.direction === direction)
            .sort(stationSorter(direction));
          const trains = snapshot.trains?.[direction] ?? [];

          if (!directionStations.length) {
            return (
              <div key={direction} className="rounded-lg border border-gray-200 p-4">
                <h4 className="text-sm font-semibold text-gray-700 mb-2">
                  {`Direction ${direction}`}
                </h4>
                <p className="text-xs text-gray-500">No station data available.</p>
              </div>
            );
          }

          return (
            <div key={direction} className="rounded-lg border border-gray-200 p-4">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h4 className="text-sm font-semibold text-gray-700">
                    {directionLabel(direction, directionStations)}
                  </h4>
                  <p className="text-xs text-gray-500">{directionStations.length} stops</p>
                </div>
              </div>

              <div className="relative pt-2 pb-6">
                <div className="absolute left-4 top-3 bottom-6 w-px bg-primary/60" aria-hidden="true" />
                <ul className="space-y-4">
                  {directionStations.map((station, index) => (
                    <li key={`${direction}-${station.slug}-${index}`} className="relative pl-10">
                      <div className="absolute left-[14px] top-2 h-3 w-3 rounded-full bg-primary" />
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-900">{station.name}</span>
                        <span className="text-xs text-gray-500">{formatWait(station.departures)}</span>
                      </div>
                    </li>
                  ))}
                </ul>

                {trains.map((train, idx) => {
                  const absolute = resolveAbsolutePosition(train, directionStations.length);
                  const top = `${absolute * 100}%`;
                  return (
                    <div
                      key={`${direction}-train-${idx}`}
                      className="absolute left-[10px] -translate-y-1/2 text-lg"
                      style={{ top }}
                      title={`${train.from_station} → ${train.to_station} (${train.confidence})`}
                    >
                      🚆
                    </div>
                  );
                })}
              </div>

              {trains.length === 0 && (
                <p className="text-xs text-gray-500">No trains inferred for this direction.</p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
