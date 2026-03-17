const { defineConfig, devices } = require("@playwright/test");
const path = require("path");

module.exports = defineConfig({
  testDir: "./tests/e2e",
  timeout: 60000,
  retries: 1,
  reporter: "list",

  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "on-first-retry",
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],

  webServer: [
    {
      // Flask backend — no reloader in CI to avoid forked child process
      command: "python -m ui.app --no-reload",
      url: "http://127.0.0.1:5000/api/health",
      timeout: 60000,
      reuseExistingServer: !process.env.CI,
      env: {
        PYTHONPATH: ".",
        DESIGNAPP_SECRET: process.env.DESIGNAPP_SECRET || "dev-secret",
        FLASK_ENV: "production",
      },
    },
    {
      // Vite dev server — use absolute path so cwd is always correct
      // regardless of where playwright is invoked from
      command: "npm run dev -- --host",
      cwd: path.join(__dirname, "react-spa"),
      url: "http://127.0.0.1:5173",
      timeout: 60000,
      reuseExistingServer: !process.env.CI,
    },
  ],
});
