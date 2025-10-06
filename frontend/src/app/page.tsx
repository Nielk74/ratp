"use client";

import { useEffect, useState } from "react";
import { Header } from "@/components/Header";
import { TrafficStatus } from "@/components/TrafficStatus";
import { NearestStations } from "@/components/NearestStations";
import { apiClient } from "@/services/api";
import type { Line, TrafficData } from "@/types";

export default function Home() {
  const [lines, setLines] = useState<Line[]>([]);
  const [traffic, setTraffic] = useState<TrafficData | null>(null);
  const [loading, setLoading] = useState(true);

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

    // Refresh traffic data every 2 minutes
    const interval = setInterval(fetchData, 120000);
    return () => clearInterval(interval);
  }, []);

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

        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            <p className="mt-4 text-gray-600">Loading live data...</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2">
              <TrafficStatus traffic={traffic} lines={lines} />
            </div>

            <div>
              <NearestStations />
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
