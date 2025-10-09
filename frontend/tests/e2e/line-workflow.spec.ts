import { test, expect } from "@playwright/test";

async function selectFirstLine(page) {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "🚇 RATP Live Tracker" })).toBeVisible();

  const lineCards = page.locator('button:has(h3:has-text("Line"))');
  await expect(lineCards.first()).toBeVisible({ timeout: 30_000 });

  const lineCode = (await lineCards.first().locator("h3").innerText()).trim();
  await lineCards.first().click();

  return lineCode;
}

test.describe("Live line workflow", () => {
  test("displays station list for selected line", async ({ page }) => {
    const lineHeading = await selectFirstLine(page);

    await expect(page.getByRole("heading", { name: lineHeading, level: 2 })).toBeVisible();

    const stationsPanel = page.locator("div").filter({ has: page.locator("h3:has-text(\"Stations\")") }).first();
    await expect(stationsPanel).toBeVisible({ timeout: 30_000 });

    const stationItems = stationsPanel.locator("ul li");
    await expect(stationItems.first()).toBeVisible({ timeout: 30_000 });

    const count = await stationItems.count();
    expect(count).toBeGreaterThan(0);
  });

  test("shows live map tab with data or loading state", async ({ page }) => {
    await selectFirstLine(page);

    await page.getByRole("button", { name: "Live map" }).click();

    const loadingState = page.getByText("Loading live train positions...");
    const liveMapPanel = page.locator("div").filter({ has: page.locator("text=Live trains") }).first();

    await expect(loadingState.or(liveMapPanel)).toBeVisible({ timeout: 45_000 });

    if (await liveMapPanel.isVisible()) {
      const trainsIcon = liveMapPanel.locator("text=🚆");
      const noTrainsMessage = liveMapPanel.locator("text=No trains inferred for this direction");
      const errorMessage = liveMapPanel.locator("text=Unable to load live train data.");

      await expect(trainsIcon.or(noTrainsMessage).or(errorMessage)).toBeVisible({ timeout: 30_000 });
    }
  });
});
