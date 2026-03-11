import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir:  "./tests/e2e",
  timeout:  60_000,          // 60 s per test (analysis can take 10–20 s)
  retries:  1,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL:     process.env.APP_URL || "http://localhost:5173",
    screenshot:  "only-on-failure",
    video:       "off",
    headless:    true,
  },
  projects: [
    { name: "chromium", use: { browserName: "chromium" } },
  ],
  // Start Flask + Vite before tests (adjust paths as needed)
  webServer: [
    {
      command: "python -m ui.app",
      url:     "http://localhost:5000/api/health",
      reuseExistingServer: true,
      timeout: 15_000,
    },
    {
      command: "npm run dev",
      url:     "http://localhost:5173",
      reuseExistingServer: true,
      timeout: 30_000,
    },
  ],
});
