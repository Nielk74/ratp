import { defineConfig, devices } from "@playwright/test";

const backendHost = process.env.NEXT_PUBLIC_BACKEND_HOST || "127.0.0.1";
const backendPort = process.env.NEXT_PUBLIC_BACKEND_PORT || "8000";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  reporter: "list",
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:3000",
    trace: "on-first-retry",
    video: "retain-on-failure",
  },
  webServer: {
    command: "npm run dev -- --port 3000",
    url: "http://127.0.0.1:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    stdout: "pipe",
    stderr: "pipe",
    env: {
      NEXT_PUBLIC_BACKEND_HOST: backendHost,
      NEXT_PUBLIC_BACKEND_PORT: backendPort,
    },
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
