// tests/playwright/frontend.spec.js
const { test, expect } = require('@playwright/test');

test.describe('Frontend Home Page', () => {
  test('loads the home page successfully', async ({ page }) => {
    const response = await page.goto('/');
    expect(response?.status()).toBe(200);
  });

  test('page has proper title', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/RATP/i);
  });

  test('page has the app container', async ({ page }) => {
    await page.goto('/');
    const appDiv = page.locator('.app');
    await expect(appDiv).toBeVisible();
  });

  test('departures tab is the default active tab', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('#tab-departures')).toBeVisible();
    await expect(page.locator('#dep-line')).toBeVisible();
  });

  test('navigation tabs switch correctly', async ({ page }) => {
    await page.goto('/');
    await page.locator('[data-tab="incidents"]').click();
    await expect(page.locator('#tab-incidents')).toBeVisible();
    await page.locator('[data-tab="itinerary"]').click();
    await expect(page.locator('#tab-itinerary')).toBeVisible();
  });

  test('search form has all expected fields', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('#dep-line')).toBeVisible();
    await expect(page.locator('#dep-stop')).toBeVisible();
    await expect(page.locator('#dep-direction')).toBeVisible();
  });
});

test.describe('Scalar API Documentation', () => {
  test('loads the Scalar UI page', async ({ page }) => {
    const response = await page.goto('/scalar');
    expect(response?.status()).toBe(200);
  });

  test('Scalar UI renders the API reference', async ({ page }) => {
    await page.goto('/scalar');
    await page.waitForTimeout(5000);

    expect(page.locator('#scalar').first()).toBeTruthy();
  });
});
