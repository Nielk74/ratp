import { test, expect } from "@playwright/test";

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
    const { code } = await selectFirstLine(page);

    await expect(async () => {
      const response = await request.get(
        `http://127.0.0.1:8000/api/snapshots/metro/${code}?refresh=true`,
        { timeout: 180_000 }
      );
      const data = await response.json();
      const hasDepartures = Array.isArray(data?.stations) && data.stations.some((station: any) =>
        Array.isArray(station.departures) && station.departures.some((dep: any) => {
          const value = dep.waiting_time || dep.raw_text || "";
          return typeof value === "string" && value.trim().length > 0 && value.trim().toLowerCase() !== "no data";
        })
      );

      expect(hasDepartures).toBeTruthy();
    }).toPass({ timeout: 180_000, intervals: [3000, 5000] });

    await page.getByRole("button", { name: "Live map" }).click();

    const loadingState = page.getByText("Loading live train positions...");
    const liveMapPanel = page.locator("div").filter({ has: page.locator("text=Live trains") }).first();

    await expect(loadingState.or(liveMapPanel)).toBeVisible({ timeout: 45_000 });

    await expect(async () => {
      await page.getByRole("button", { name: "Refresh" }).click();
      await page.waitForTimeout(2000);

      const waits = await liveMapPanel
        .locator("li div.justify-between span:last-child")
        .allInnerTexts();

      expect(waits.some((text) => text.trim() !== "No data" && text.trim().length > 0)).toBeTruthy();
    }).toPass({ timeout: 120_000, intervals: [2000, 3000] });
  });
});
