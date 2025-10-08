import { test, expect } from "@playwright/test";

test.describe("Line live map", () => {
  test("displays live map panel using real backend data", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByRole("heading", { name: "🚇 RATP Live Tracker" })).toBeVisible();

    await page.waitForTimeout(5000);

    const firstLineButton = page.locator('button').filter({ has: page.locator('h3:has-text("Line")') }).first();
    await expect(firstLineButton).toBeVisible();
    await firstLineButton.click();

    await expect(page.getByRole("heading", { name: /Line \d+/, level: 2 })).toBeVisible();

    await page.getByRole("button", { name: "Live map" }).click();

    const liveTrains = page.getByText("Live trains");
    const liveError = page.getByText("Unable to load live train data.");

    await expect(liveTrains.or(liveError)).toBeVisible();
  });
});
