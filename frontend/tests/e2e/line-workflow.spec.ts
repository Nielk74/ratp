import { test, expect } from "@playwright/test";

const BACKEND_BASE_URL = process.env.PLAYWRIGHT_BACKEND_URL || "http://127.0.0.1:8000";

async function selectFirstLine(page: import("@playwright/test").Page) {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "🚇 RATP Live Tracker" })).toBeVisible();

  const lineCards = page.locator('button:has(h3:has-text("Line"))');
  await expect(lineCards.first()).toBeVisible({ timeout: 30_000 });

  const lineNumber = (await lineCards
    .first()
    .locator("div.rounded-full")
    .first()
    .innerText())
    .trim();

  await lineCards.first().click();

  return { heading: `Line ${lineNumber}`, code: lineNumber };
}

test.describe("Live line workflow", () => {
  test("displays station list for selected line", async ({ page }) => {
    const { heading } = await selectFirstLine(page);

    await expect(page.getByRole("heading", { name: heading, level: 2 })).toBeVisible();

    const stationsPanel = page.locator("div").filter({ has: page.locator("h3:has-text(\"Stations\")") }).first();
    await expect(stationsPanel).toBeVisible({ timeout: 30_000 });

    const stationItems = stationsPanel.locator("ul li");
    await expect(async () => {
      const count = await stationItems.count();
      expect(count).toBeGreaterThan(0);
    }).toPass({ timeout: 180_000, intervals: [3000, 5000] });
  });

  test("shows live map tab populated with real departures", async ({ page, request }) => {
    const snapshotCache = new Map<string, unknown>();

    await page.route("**/api/snapshots/**", async (route) => {
      const url = new URL(route.request().url());
      const backendUrl = new URL(url.pathname, BACKEND_BASE_URL);
      url.searchParams.forEach((value, key) => {
        backendUrl.searchParams.set(key, value);
      });
      if (!backendUrl.searchParams.has("station_limit")) {
        backendUrl.searchParams.set("station_limit", "1");
      }
      const cacheKey = backendUrl.toString();
      if (!snapshotCache.has(cacheKey)) {
        const backendResponse = await request.get(cacheKey, { timeout: 180_000 });
        snapshotCache.set(cacheKey, await backendResponse.json());
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(snapshotCache.get(cacheKey)),
      });
    });

    const { code } = await selectFirstLine(page);

    await expect(async () => {
      const response = await request.get(
        `${BACKEND_BASE_URL}/api/snapshots/metro/${code}?refresh=true&station_limit=1`,
        { timeout: 240_000 }
      );
      const data = await response.json();
      const hasStations = Array.isArray(data?.stations) && data.stations.length > 0;
      expect(hasStations).toBeTruthy();
    }).toPass({ timeout: 180_000, intervals: [3000, 5000] });

    await page.getByRole("button", { name: "Live map" }).click();

    const loadingState = page.getByText("Loading live train positions...");
    const liveMapPanel = page.locator("div").filter({
      has: page.getByRole("heading", { name: "Live trains" }),
    }).first();

    await expect(loadingState.or(liveMapPanel)).toBeVisible({ timeout: 45_000 });

    await expect(async () => {
      await page.getByRole("button", { name: "Refresh" }).click();
      await page.waitForTimeout(2000);

      const stationCount = await liveMapPanel.locator("li").count();
      expect(stationCount).toBeGreaterThan(0);
    }).toPass({ timeout: 120_000, intervals: [2000, 3000] });
  });

  test("does not surface Playwright spawn race errors when forcing refresh with parallel jobs", async ({ page, request }) => {
    const { code } = await selectFirstLine(page);

    const response = await request.get(
      `${BACKEND_BASE_URL}/api/snapshots/metro/${code}?refresh=true&station_limit=1`,
      { timeout: 240_000 }
    );
    expect(response.ok()).toBeTruthy();

    const snapshot = await response.json();
    const errors: string[] = Array.isArray(snapshot?.errors) ? snapshot.errors : [];
    const combinedErrors = errors.join(" ").toLowerCase();

    expect(combinedErrors).not.toContain("racing with another loop to spawn a process");
  });

  test("shows retry flow when live snapshot fails and recovers after retry", async ({ page }) => {
    const fakeSnapshot = {
      scraped_at: new Date().toISOString(),
      network: "metro",
      line: "1",
      stations: [
        {
          name: "Bastille",
          slug: "bastille",
          order: 0,
          direction: "A",
          direction_index: 0,
          departures: [
            {
              raw_text: "2 mn → La Défense",
              destination: "La Défense",
              waiting_time: "2 mn",
            },
          ],
          metadata: { source: "cloudscraper" },
        },
        {
          name: "La Défense",
          slug: "la-defense",
          order: 0,
          direction: "B",
          direction_index: 0,
          departures: [
            {
              raw_text: "3 mn → Château de Vincennes",
              destination: "Château de Vincennes",
              waiting_time: "3 mn",
            },
          ],
          metadata: { source: "cloudscraper" },
        },
      ],
      trains: { A: [], B: [] },
      errors: ["Navitia init failed: missing API key"],
    };

    let callCount = 0;
    await page.route("**/api/snapshots/**", (route) => {
      callCount += 1;
      if (callCount === 1) {
        return route.fulfill({
          status: 500,
          contentType: "application/json",
          body: JSON.stringify({ detail: "forced failure" }),
        });
      }

      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(fakeSnapshot),
      });
    });

    await selectFirstLine(page);

    await page.getByRole("button", { name: "Live map" }).click();

    await expect(page.getByText("Unable to load live train data.")).toBeVisible({ timeout: 15_000 });
    const retryButton = page.getByRole("button", { name: "Retry" });
    await expect(retryButton).toBeVisible();

    await retryButton.click();

    const liveMapContainer = page.locator("div").filter({
      has: page.getByRole("heading", { name: "Live trains" }),
    }).first();

    await expect(liveMapContainer).toBeVisible({ timeout: 15_000 });
    await expect(liveMapContainer.getByText("Navitia init failed: missing API key")).toBeVisible();
    await expect(liveMapContainer.locator("li").filter({ hasText: "Bastille" })).toBeVisible();
    await expect(liveMapContainer.locator("li").filter({ hasText: "La Défense" })).toBeVisible();
  });
});
