import { defineConfig, devices } from "@playwright/test";

const WEB_HOST = process.env.POLYWATCH_FRONTEND_HOST ?? "127.0.0.1";
const WEB_PORT = process.env.POLYWATCH_FRONTEND_PORT ?? "3100";
const WEB_URL = `http://${WEB_HOST}:${WEB_PORT}`;

export default defineConfig({
  testDir: "./tests",
  timeout: 30_000,
  expect: {
    timeout: 5_000
  },
  fullyParallel: true,
  reporter: [["list"]],
  use: {
    trace: "on-first-retry",
    baseURL: WEB_URL
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] }
    }
  ],
  webServer: {
    command: `POLYWATCH_USE_TEMP_REPORTS=1 POLYWATCH_FRONTEND_HOST=${WEB_HOST} POLYWATCH_FRONTEND_PORT=${WEB_PORT} bash scripts/dev-with-backend.sh`,
    url: WEB_URL,
    reuseExistingServer: false
  }
});
