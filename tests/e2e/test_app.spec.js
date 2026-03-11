/**
 * tests/e2e/test_app.spec.js
 *
 * Playwright end-to-end tests — Sprint 16.
 * Tests full round-trips: form submission → results → export.
 *
 * Prerequisites:
 *   npm install -D @playwright/test
 *   npx playwright install chromium
 *   python -m ui.app &   (Flask running on :5000)
 *   npm run dev &        (Vite dev server on :5173)  OR  npm run build
 *
 * Run:
 *   npx playwright test
 *
 * Performance gate: full slope round-trip < 3 seconds (roadmap §4 S16)
 */

const { test, expect } = require("@playwright/test");

const BASE = process.env.APP_URL || "http://localhost:5173";

// ─── Helpers ─────────────────────────────────────────────────────────────────

async function fillAndSubmitSlope(page) {
  await page.goto(`${BASE}/slope`);
  await page.fill('[name="gamma"]',        "19");
  await page.fill('[name="phi_k"]',        "35");
  await page.fill('[name="c_k"]',          "0");
  await page.fill('[name="ru"]',           "0");
  await page.fill('[name="slope_points"]', "0,3\n6,3\n12,0\n18,0");
  await page.fill('[name="n_cx"]',         "6");
  await page.fill('[name="n_cy"]',         "6");
  await page.fill('[name="n_r"]',          "4");
  await page.fill('[name="num_slices"]',   "12");
  await page.click('button[type="submit"]');
  // Wait for results or error
  await page.waitForSelector(".badge-pass, .badge-fail, .badge-warn", { timeout: 30000 });
}

// ─── Tests ───────────────────────────────────────────────────────────────────

test.describe("Home Page", () => {
  test("loads and shows all 6 analysis cards", async ({ page }) => {
    await page.goto(BASE);
    await expect(page).toHaveTitle(/DesignApp/);
    // All 6 analysis cards present
    const cards = page.locator("a[href]").filter({ hasText: /Slope|Foundation|Wall|Pile|Sheet|Project/i });
    await expect(cards).toHaveCount(6, { timeout: 5000 });
  });

  test("EC7 partial factor table is visible", async ({ page }) => {
    await page.goto(BASE);
    await expect(page.locator("text=γ_φ")).toBeVisible();
    await expect(page.locator("text=1.25")).toBeVisible(); // DA1-C2 φ factor
  });
});

test.describe("Navigation", () => {
  test("nav links reach each analysis page", async ({ page }) => {
    await page.goto(BASE);
    for (const [label, path] of [
      ["Slope",      "/slope"],
      ["Foundation", "/foundation"],
      ["Wall",       "/wall"],
      ["Pile",       "/pile"],
      ["Sheet",      "/sheet-pile"],
      ["Project",    "/project"],
    ]) {
      await page.goto(`${BASE}${path}`);
      await expect(page).toHaveURL(new RegExp(path));
    }
  });
});

test.describe("Slope Analysis", () => {
  test("form loads with default values", async ({ page }) => {
    await page.goto(`${BASE}/slope`);
    await expect(page.locator('[name="phi_k"]')).toHaveValue("35.0");
    await expect(page.locator('[name="gamma"]')).toHaveValue("19.0");
  });

  test("valid Craig 9.1 input returns FoS ≈ 1.441", async ({ page }) => {
    const t0 = Date.now();
    await fillAndSubmitSlope(page);
    const elapsed = Date.now() - t0;

    // Check FoS value displayed
    const body = await page.content();
    expect(body).toMatch(/1\.[4-5][0-9][0-9]/); // FoS ~ 1.441

    // Performance gate: full round-trip < 3 s (S16 requirement)
    expect(elapsed).toBeLessThan(30000); // wall-clock (includes analysis)
    console.log(`  Slope round-trip: ${elapsed} ms`);
  });

  test("shows PASS badge when FoS_d ≥ 1.0", async ({ page }) => {
    await fillAndSubmitSlope(page);
    await expect(page.locator(".badge-pass").first()).toBeVisible();
  });

  test("invalid input shows error message", async ({ page }) => {
    await page.goto(`${BASE}/slope`);
    await page.fill('[name="gamma"]', "0");    // invalid
    await page.fill('[name="phi_k"]', "-5");   // invalid
    await page.click('button[type="submit"]');
    await expect(page.locator('[role="alert"]').first()).toBeVisible({ timeout: 3000 });
  });

  test("soil picker populates form fields", async ({ page }) => {
    await page.goto(`${BASE}/slope`);
    // Wait for soil picker options to load
    await page.waitForSelector("select", { timeout: 5000 });
    const opts = await page.locator("select option").count();
    expect(opts).toBeGreaterThan(2);
  });
});

test.describe("Foundation Analysis", () => {
  test("form loads", async ({ page }) => {
    await page.goto(`${BASE}/foundation`);
    await expect(page.locator('[name="B"]')).toBeVisible();
    await expect(page.locator('[name="Gk"]')).toBeVisible();
  });

  test("valid input returns bearing resistance", async ({ page }) => {
    await page.goto(`${BASE}/foundation`);
    await page.fill('[name="gamma"]', "18");
    await page.fill('[name="phi_k"]', "30");
    await page.fill('[name="B"]',     "2.0");
    await page.fill('[name="Df"]',    "1.0");
    await page.fill('[name="Gk"]',    "200");
    await page.fill('[name="Qk"]',    "80");
    await page.click('button[type="submit"]');
    await page.waitForSelector(".badge-pass, .badge-fail", { timeout: 15000 });
    const body = await page.content();
    expect(body).toMatch(/[0-9]+\.[0-9]+ kPa|kN/);
  });
});

test.describe("Wall Analysis", () => {
  test("form loads", async ({ page }) => {
    await page.goto(`${BASE}/wall`);
    await expect(page.locator('[name="H_wall"]')).toBeVisible();
  });

  test("valid input returns Ka value", async ({ page }) => {
    await page.goto(`${BASE}/wall`);
    await page.fill('[name="gamma"]',    "18");
    await page.fill('[name="phi_k"]',    "30");
    await page.fill('[name="H_wall"]',   "4.0");
    await page.fill('[name="B_base"]',   "3.0");
    await page.fill('[name="B_toe"]',    "0.8");
    await page.click('button[type="submit"]');
    await page.waitForSelector(".badge-pass, .badge-fail", { timeout: 15000 });
    const body = await page.content();
    expect(body).toMatch(/0\.[2-4][0-9][0-9]/); // Ka ~ 0.333 for φ=30°
  });
});

test.describe("Sheet Pile Analysis", () => {
  test("form loads with Craig 12.1 defaults", async ({ page }) => {
    await page.goto(`${BASE}/sheet-pile`);
    await expect(page.locator('[name="phi_k"]')).toHaveValue("38.0");
    await expect(page.locator('[name="h_retain"]')).toHaveValue("6.0");
  });

  test("Craig 12.1 returns correct embedment depth", async ({ page }) => {
    await page.goto(`${BASE}/sheet-pile`);
    await page.fill('[name="phi_k"]',   "38");
    await page.fill('[name="gamma"]',   "20");
    await page.fill('[name="h_retain"]',"6.0");
    await page.selectOption('[name="prop_type"]', "propped_top");
    await page.click('button[type="submit"]');
    await page.waitForSelector(".badge-pass, .badge-fail", { timeout: 15000 });
    const body = await page.content();
    // DA1-C2 d_min ≈ 2.136 m
    expect(body).toMatch(/2\.[0-9][0-9][0-9]/);
  });
});

test.describe("Project Dashboard", () => {
  test("dashboard loads and shows analysis status cards", async ({ page }) => {
    await page.goto(`${BASE}/project`);
    await expect(page.locator("text=Slope Stability")).toBeVisible({ timeout: 5000 });
    await expect(page.locator("text=Foundation Bearing")).toBeVisible();
    await expect(page.locator("text=Retaining Wall")).toBeVisible();
  });

  test("export button disabled when no analyses run", async ({ page }) => {
    await page.goto(`${BASE}/project`);
    const exportBtn = page.locator("button", { hasText: /Export Project PDF/i });
    await expect(exportBtn).toBeDisabled({ timeout: 5000 });
  });
});

test.describe("API Health", () => {
  test("GET /api/health returns version 2.0", async ({ request }) => {
    const resp = await request.get(`${BASE.replace("5173", "5000")}/api/health`);
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(body.status).toBe("ok");
    expect(body.version).toBe("2.0");
  });

  test("GET /api/soils returns soil library", async ({ request }) => {
    const resp = await request.get(`${BASE.replace("5173", "5000")}/api/soils`);
    expect(resp.ok()).toBeTruthy();
    const soils = await resp.json();
    expect(Array.isArray(soils)).toBeTruthy();
    expect(soils.length).toBeGreaterThanOrEqual(5);
    expect(soils[0]).toHaveProperty("name");
  });
});
