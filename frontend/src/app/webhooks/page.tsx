"use client";

import { useEffect, useMemo, useState } from "react";

import { apiClient } from "@/services/api";
import type { Line, WebhookSubscription } from "@/types";

const severityOptions = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "critical", label: "Critical" },
];

export default function WebhooksPage() {
  const [lines, setLines] = useState<Line[]>([]);
  const [subscriptions, setSubscriptions] = useState<WebhookSubscription[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [webhookUrl, setWebhookUrl] = useState("");
  const [selectedLine, setSelectedLine] = useState("");
  const [selectedSeverities, setSelectedSeverities] = useState<string[]>([
    "high",
    "critical",
  ]);
  const [submitting, setSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const sortedLines = useMemo(
    () =>
      [...lines].sort((a, b) => a.code.localeCompare(b.code, undefined, { numeric: true })),
    [lines],
  );

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [linesResponse, webhooksResponse] = await Promise.all([
          apiClient.getLines("metro"),
          apiClient.listWebhooks(),
        ]);

        setLines(linesResponse.lines);
        setSubscriptions(webhooksResponse.subscriptions);
        setSelectedLine(linesResponse.lines[0]?.code ?? "");
      } catch (err) {
        console.error(err);
        setError("Failed to load webhook data.");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const toggleSeverity = (value: string) => {
    setSelectedSeverities((prev) => {
      if (prev.includes(value)) {
        return prev.filter((item) => item !== value);
      }
      return [...prev, value];
    });
  };

  const handleCreateWebhook = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const payload = await apiClient.createWebhook(
        webhookUrl.trim(),
        selectedLine,
        selectedSeverities.length > 0 ? selectedSeverities : undefined,
      );

      setSubscriptions((prev) => [payload, ...prev]);
      setWebhookUrl("");
      setSuccessMessage("Subscription created and confirmation sent to Discord.");
    } catch (err) {
      console.error(err);
      setError("Failed to create webhook subscription.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await apiClient.deleteWebhook(id);
      setSubscriptions((prev) => prev.filter((item) => item.id !== id));
    } catch (err) {
      console.error(err);
      setError("Failed to delete subscription.");
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-12">
        <p className="text-gray-600">Loading webhook management...</p>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-12 space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Discord Webhook Alerts</h1>
        <p className="text-gray-600 mt-2 max-w-2xl">
          Register your Discord webhook to receive instant notifications when traffic
          disruptions occur on your favourite lines.
        </p>
      </div>

      <div className="bg-white rounded-xl shadow p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Create Subscription</h2>

        <form className="space-y-6" onSubmit={handleCreateWebhook}>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Discord Webhook URL
            </label>
            <input
              type="url"
              required
              value={webhookUrl}
              onChange={(event) => setWebhookUrl(event.target.value)}
              className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-primary focus:outline-none"
              placeholder="https://discord.com/api/webhooks/..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Line
            </label>
            <select
              required
              value={selectedLine}
              onChange={(event) => setSelectedLine(event.target.value)}
              className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-primary focus:outline-none"
            >
              {sortedLines.map((line) => (
                <option key={line.code} value={line.code}>
                  Line {line.code} — {line.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <p className="block text-sm font-medium text-gray-700 mb-2">
              Severity Filter
            </p>
            <div className="flex flex-wrap gap-3">
              {severityOptions.map((option) => {
                const active = selectedSeverities.includes(option.value);
                return (
                  <button
                    type="button"
                    key={option.value}
                    onClick={() => toggleSeverity(option.value)}
                    className={`px-3 py-1.5 rounded-full text-sm border transition ${
                      active
                        ? "border-primary bg-primary/10 text-primary"
                        : "border-gray-300 text-gray-600 hover:border-primary hover:text-primary"
                    }`}
                  >
                    {option.label}
                  </button>
                );
              })}
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Leave all unselected to receive every alert regardless of severity.
            </p>
          </div>

          <div className="flex items-center gap-4">
            <button
              type="submit"
              disabled={submitting}
              className="bg-primary text-white px-5 py-2.5 rounded-lg hover:bg-primary-dark transition disabled:opacity-50"
            >
              {submitting ? "Registering..." : "Register Webhook"}
            </button>

            {successMessage && (
              <span className="text-sm text-success">{successMessage}</span>
            )}
            {error && <span className="text-sm text-error">{error}</span>}
          </div>
        </form>
      </div>

      <div className="bg-white rounded-xl shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Active Subscriptions</h2>
          <span className="text-sm text-gray-500">{subscriptions.length} active</span>
        </div>

        {subscriptions.length === 0 ? (
          <p className="text-gray-500 text-sm">
            You don&apos;t have any subscriptions yet. Create one above to get started.
          </p>
        ) : (
          <div className="space-y-4">
            {subscriptions.map((subscription) => (
              <div
                key={subscription.id}
                className="flex flex-col md:flex-row md:items-center justify-between border border-gray-200 rounded-lg px-4 py-3 gap-3"
              >
                <div className="space-y-1">
                  <p className="text-sm font-semibold text-gray-900">
                    Line {subscription.line_code}
                    {subscription.line_name ? ` — ${subscription.line_name}` : ""}
                  </p>
                  <p className="text-xs text-gray-500 break-all">{subscription.webhook_url}</p>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {(subscription.severity_filter ?? ["all"]).map((severity) => (
                      <span
                        key={`${subscription.id}-${severity}`}
                        className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-primary/10 text-primary"
                      >
                        {severity.toUpperCase()}
                      </span>
                    ))}
                  </div>
                </div>

                <button
                  onClick={() => handleDelete(subscription.id)}
                  className="self-start md:self-center text-sm text-error hover:text-error/80"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
