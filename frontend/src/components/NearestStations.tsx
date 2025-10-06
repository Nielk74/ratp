"use client";

import { useState } from "react";
import { apiClient } from "@/services/api";
import type { NearestStationResult } from "@/types";

export function NearestStations() {
  const [stations, setStations] = useState<NearestStationResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const findNearestStations = async () => {
    setLoading(true);
    setError(null);

    try {
      // Get user's location
      if (!navigator.geolocation) {
        throw new Error("Geolocation is not supported by your browser");
      }

      navigator.geolocation.getCurrentPosition(
        async (position) => {
          try {
            const { latitude, longitude } = position.coords;
            const data = await apiClient.getNearestStations(
              latitude,
              longitude,
              5,
              2.0
            );
            setStations(data.results);
          } catch (err) {
            setError("Failed to fetch nearest stations");
            console.error(err);
          } finally {
            setLoading(false);
          }
        },
        () => {
          setError("Unable to retrieve your location");
          setLoading(false);
        }
      );
    } catch (err) {
      setError((err as Error).message);
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-bold text-gray-900 mb-4">
        📍 Nearest Stations
      </h2>

      <button
        onClick={findNearestStations}
        disabled={loading}
        className="w-full bg-primary text-white py-2 px-4 rounded-lg hover:bg-primary-dark transition disabled:opacity-50 disabled:cursor-not-allowed mb-4"
      >
        {loading ? "Locating..." : "Find Nearest Stations"}
      </button>

      {error && (
        <div className="bg-error/10 border border-error text-error px-4 py-3 rounded-lg mb-4">
          {error}
        </div>
      )}

      {stations.length > 0 && (
        <div className="space-y-3">
          {stations.map((result, index) => (
            <div
              key={index}
              className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="font-semibold text-gray-900">
                    {result.station.name}
                  </h3>
                  {result.station.lines && result.station.lines.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {result.station.lines.map((line) => (
                        <span
                          key={line}
                          className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-primary/10 text-primary"
                        >
                          {line}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <div className="text-right ml-4">
                  <div className="text-sm font-semibold text-gray-900">
                    {result.distance_km.toFixed(2)} km
                  </div>
                  <div className="text-xs text-gray-500">
                    {result.distance_m.toFixed(0)} m
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && !error && stations.length === 0 && (
        <p className="text-gray-500 text-sm text-center py-8">
          Click the button above to find stations near you
        </p>
      )}
    </div>
  );
}
