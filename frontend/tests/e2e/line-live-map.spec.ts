import { test, expect } from "@playwright/test";

const mockLines = {
  lines: [
    {
      code: "1",
      name: "Ligne 1",
      type: "metro",
      color: "#FFD700",
    },
  ],
  count: 1,
};

const mockTraffic = {
  generated_at: new Date().toISOString(),
  lines: [],
  default: {
    level: "unknown",
    message: "Data unavailable",
  },
};

const mockLineDetails = {
  line: {
    code: "1",
    name: "Ligne 1",
    type: "metro",
    color: "#FFD700",
  },
  stations: [
    { name: "La Défense", slug: "la-defense" },
    { name: "Champs-Élysées", slug: "champs-elysees" },
    { name: "Bastille", slug: "bastille" },
  ],
  stations_count: 3,
  source: "mock",
};

const nowIso = new Date().toISOString();

const mockSnapshot = {
  scraped_at: nowIso,
  network: "metro",
  line: "1",
  stations: [
    {
      name: "La Défense",
      slug: "la-defense",
      order: 0,
      direction: "A",
      direction_index: 0,
      departures: [
        {
          raw_text: "0 → Château de Vincennes",
          destination: "Château de Vincennes",
          waiting_time: "0 mn",
          extra: {},
        },
      ],
      metadata: {
        cloudflare_blocked: false,
      },
    },
    {
      name: "Champs-Élysées",
      slug: "champs-elysees",
      order: 1,
      direction: "A",
      direction_index: 1,
      departures: [
        {
          raw_text: "4 → Château de Vincennes",
          destination: "Château de Vincennes",
          waiting_time: "4 mn",
          extra: {},
        },
      ],
      metadata: {
        cloudflare_blocked: false,
      },
    },
    {
      name: "Bastille",
      slug: "bastille",
      order: 2,
      direction: "B",
      direction_index: 0,
      departures: [
        {
          raw_text: "5 → La Défense",
          destination: "La Défense",
          waiting_time: "5 mn",
          extra: {},
        },
      ],
      metadata: {
        cloudflare_blocked: false,
      },
    },
  ],
  trains: {
    A: [
      {
        direction: "A",
        from_station: "La Défense",
        to_station: "Champs-Élysées",
        eta_from: 0,
        eta_to: 4,
        progress: 0.2,
        absolute_progress: 0.2,
        confidence: "high",
      },
    ],
    B: [],
  },
  errors: [],
};

test.describe("Line live map", () => {
  test("renders live map with inferred trains even when traffic is unavailable", async ({ page }) => {
    await page.route("**/api/lines", (route) => {
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(mockLines) });
    });

    await page.route("**/api/traffic/status", (route) => {
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(mockTraffic) });
    });

    await page.route("**/api/lines/metro/1", (route) => {
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(mockLineDetails) });
    });

    await page.route("**/api/snapshots/metro/1", (route) => {
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(mockSnapshot) });
    });

    await page.goto("/");

    await expect(page.getByRole("heading", { name: "🚇 RATP Live Tracker" })).toBeVisible();

    await expect(page.getByRole("heading", { name: "Line 1", level: 2 })).toBeVisible();

    await page.getByRole("button", { name: "Live map" }).click();

    await expect(page.getByText("Live trains")).toBeVisible();
    await expect(page.getByText(/Direction Château de Vincennes/)).toBeVisible();
    await expect(page.getByText(/No trains inferred for this direction/)).toBeVisible();
  });
});
