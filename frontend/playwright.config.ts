import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 240_000,
  expect: {
    timeout: 10_000,
  },
  reporter: "list",
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:8001",
    trace: "on-first-retry",
    video: "retain-on-failure",
  },
  webServer: [
    {
      command: "../serve.sh",
      url: "http://127.0.0.1:8001",
      reuseExistingServer: !process.env.CI,
      timeout: 180_000,
      stdout: "pipe",
      stderr: "pipe",
    },
  ],
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
