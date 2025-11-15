import { defineConfig, devices } from "@playwright/test";

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
    baseURL: "http://127.0.0.1:3000"
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] }
    }
  ],
  webServer: {
    command: "bash scripts/dev-with-backend.sh",
    url: "http://127.0.0.1:3000",
    reuseExistingServer: false
  }
});
