"use client";

import { useEffect, useMemo, useState } from "react";
import { Header } from "@/components/Header";
import { TrafficStatus } from "@/components/TrafficStatus";
import { NearestStations } from "@/components/NearestStations";
import { LineDetailsPanel } from "@/components/LineDetailsPanel";
import { buildLineStatusMap, getLineStatus } from "@/utils/traffic";
import { apiClient } from "@/services/api";
import type {
  Line,
  LineDetails,
  LineStatusInfo,
  NormalizedTrafficStatus,
} from "@/types";

const TRANSPORT_FILTERS: Array<{ value: Line["type"]; label: string; icon: string }> = [
  { value: "metro", label: "Metro", icon: "🚇" },
  { value: "rer", label: "RER", icon: "🚆" },
  { value: "tram", label: "Tram", icon: "🚊" },
  { value: "transilien", label: "Transilien", icon: "🚉" },
];

export default function Home() {
  const [lines, setLines] = useState<Line[]>([]);
  const [traffic, setTraffic] = useState<NormalizedTrafficStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [transportFilter, setTransportFilter] = useState<Line["type"]>("metro");
  const [selectedLine, setSelectedLine] = useState<Line | null>(null);
  const [lineDetails, setLineDetails] = useState<LineDetails | null>(null);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [detailsError, setDetailsError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [linesData, trafficData] = await Promise.all([
          apiClient.getLines(),
          apiClient.getTraffic(),
        ]);
        setLines(linesData.lines);
        setTraffic(trafficData);
      } catch (error) {
        console.error("Failed to fetch data:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();

    const interval = setInterval(fetchData, 120000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!lines.length) {
      setSelectedLine(null);
      return;
    }

    setSelectedLine((current) => {
      const currentExists =
        current &&
        lines.find(
          (line) =>
            line.type === current.type && line.code === current.code,
        );

      if (currentExists && currentExists.type === transportFilter) {
        return currentExists;
      }

      const firstOfFilter =
        lines.find((line) => line.type === transportFilter) ?? null;
      return firstOfFilter ?? currentExists ?? null;
    });
  }, [lines, transportFilter]);

  useEffect(() => {
    if (!selectedLine) {
      setLineDetails(null);
      return;
    }

    let ignore = false;
    const fetchDetails = async () => {
      try {
        setDetailsLoading(true);
        setDetailsError(null);
        const details = await apiClient.getLineDetails(selectedLine.type, selectedLine.code);
        if (!ignore) {
          setLineDetails(details);
        }
      } catch (error) {
        console.error(error);
        if (!ignore) {
          setDetailsError("Unable to load line details at the moment.");
          setLineDetails(null);
        }
      } finally {
        if (!ignore) {
          setDetailsLoading(false);
        }
      }
    };

    fetchDetails();

    return () => {
      ignore = true;
    };
  }, [selectedLine]);

  const filteredLines = useMemo(
    () => lines.filter((line) => line.type === transportFilter),
    [lines, transportFilter],
  );

  const statusMap = useMemo(() => buildLineStatusMap(traffic), [traffic]);
  const lineStatus = useMemo(() => {
    if (!selectedLine) return null;
    return getLineStatus(selectedLine, statusMap, traffic);
  }, [selectedLine, statusMap, traffic]);

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />

      <main className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            🚇 RATP Live Tracker
          </h1>
          <p className="text-gray-600">
            Real-time monitoring for Paris public transport
          </p>
        </div>

        <div className="mb-6 flex flex-wrap gap-2">
          {TRANSPORT_FILTERS.map((option) => {
            const active = option.value === transportFilter;
            return (
              <button
                key={option.value}
                onClick={() => {
                  setTransportFilter(option.value);
                  const first = lines.find((line) => line.type === option.value) ?? null;
                  setSelectedLine(first);
                }}
                className={`px-4 py-2 rounded-full border text-sm transition ${
                  active
                    ? "border-primary bg-primary text-white"
                    : "border-gray-300 bg-white text-gray-700 hover:border-primary hover:text-primary"
                }`}
              >
                <span className="mr-2">{option.icon}</span>
                {option.label}
              </button>
            );
          })}
        </div>

        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            <p className="mt-4 text-gray-600">Loading live data...</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 xl:grid-cols-4 gap-8">
            <div className="xl:col-span-3 space-y-6">
              <TrafficStatus
                traffic={traffic}
                lines={filteredLines}
                onSelectLine={setSelectedLine}
                selectedLineCode={selectedLine?.code ?? null}
              />
              <NearestStations />
            </div>

            <div className="xl:col-span-1">
              <LineDetailsPanel
                line={selectedLine}
                status={lineStatus}
                details={lineDetails}
                loading={detailsLoading}
              />
              {detailsError && (
                <p className="text-sm text-error mt-3">{detailsError}</p>
              )}
            </div>
          </div>
        )}
      </main>

      <footer className="bg-white border-t border-gray-200 mt-16">
        <div className="container mx-auto px-4 py-6 text-center text-gray-600">
          <p>Built with ❤️ for Paris public transport users</p>
          <p className="text-sm mt-2">
            Data from RATP & Île-de-France Mobilités
          </p>
        </div>
      </footer>
    </div>
  );
}
