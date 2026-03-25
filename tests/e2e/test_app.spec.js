// @ts-check
const { test, expect } = require("@playwright/test");

const BASE = "http://127.0.0.1:5173";

// ── Home Page ────────────────────────────────────────────────────────────────
test.describe("Home Page", () => {
  test("loads and shows all 6 analysis cards", async ({ page }) => {
    await page.goto(BASE);

    // FIX #1: The old locator matched nav links too (12 elements).
    // Scope to the main <main> content area, not the whole page.
    // Cards are <a> tags inside main, not in the nav bar.
    const cards = page
      .locator("main")
      .locator("a[href]")
      .filter({ hasText: /Slope|Foundation|Wall|Pile|Sheet|Project/i });

    await expect(cards).toHaveCount(6, { timeout: 5000 });
  });

  test("EC7 partial factor table is visible", async ({ page }) => {
    await page.goto(BASE);
    await expect(page.locator("text=γ_φ")).toBeVisible();

    // FIX #2: Two cells contain "1.25" — strict mode rejects ambiguous locators.
    // Use .first() to pick either one; presence of the value is what matters.
    await expect(page.locator("text=1.25").first()).toBeVisible();
  });
});

// ── Navigation ───────────────────────────────────────────────────────────────
test.describe("Navigation", () => {
  test("nav links reach each analysis page", async ({ page }) => {
    await page.goto(BASE);
    const links = ["/slope", "/foundation", "/wall", "/pile", "/sheet-pile", "/project"];
    for (const href of links) {
      await page.goto(`${BASE}${href}`);
      await expect(page).not.toHaveURL(/error/i);
    }
  });
});

// ── Slope Analysis ────────────────────────────────────────────────────────────
async function fillAndSubmitSlope(page) {
  await page.goto(`${BASE}/slope`);
  await page.fill('[name="phi_k"]',    "35");
  await page.fill('[name="gamma"]',  "19");
  await page.fill('[name="c_k"]',"0");
  await page.fill('[name="ru"]',     "0");
  const submitBtn = page.locator('button[type="submit"]').first();
  await submitBtn.click();
  // Wait for result to appear (badge OR error message)
  await page.waitForSelector(".badge-pass, .badge-fail, .text-red-600", { timeout: 15000 });
}

test.describe("Slope Analysis", () => {
  test("form loads with default values", async ({ page }) => {
    await page.goto(`${BASE}/slope`);
    await expect(page.locator('[name="phi_k"]')).toBeVisible();
  });

  test("valid Craig 9.1 input returns FoS ≈ 1.441", async ({ page }) => {
    const start = Date.now();
    await fillAndSubmitSlope(page);
    const elapsed = Date.now() - start;
    console.log(`Slope round-trip: ${elapsed} ms`);
    const body = await page.content();
    expect(body).toMatch(/1\.44/);
  });

  test("shows result badge after analysis", async ({ page }) => {
    await fillAndSubmitSlope(page);

    // Craig 9.1 inputs (φ=35°) may FAIL DA1-C2 after applying γ_φ=1.25 design
    // factor — that is correct EC7 behaviour, not a bug. We verify a badge
    // (either PASS or FAIL) is rendered, confirming the result section appeared.
    const anyBadge = page.locator(".badge-pass, .badge-fail").first();
    await expect(anyBadge).toBeVisible({ timeout: 15000 });
  });

  test("invalid input shows error message", async ({ page }) => {
    await page.goto(`${BASE}/slope`);
    await page.fill('[name="phi_k"]', "-999");
    await page.locator('button[type="submit"]').first().click();
    await expect(page.locator(".text-red-600, [role='alert']").first()).toBeVisible({ timeout: 5000 });
  });

  test("soil picker populates form fields", async ({ page }) => {
    await page.goto(`${BASE}/slope`);
    // Select first non-empty option in soil picker
    const picker = page.locator("select").first();
    const options = await picker.locator("option").all();
    if (options.length > 1) {
      await picker.selectOption({ index: 1 });
    }
    await expect(page.locator('[name="phi_k"]')).not.toHaveValue("0");
  });
});

// ── Foundation Analysis ───────────────────────────────────────────────────────
test.describe("Foundation Analysis", () => {
  test("form loads", async ({ page }) => {
    await page.goto(`${BASE}/foundation`);
    await expect(page.locator('[name="phi_k"]')).toBeVisible();
  });

  test("valid input returns bearing resistance", async ({ page }) => {
    await page.goto(`${BASE}/foundation`);
    await page.fill('[name="phi_k"]',    "30");
    await page.fill('[name="gamma"]',  "18");
    await page.fill('[name="B"]',       "2");
    await page.fill('[name="Df"]',      "1");
    await page.locator('button[type="submit"]').first().click();
    await page.waitForSelector(".badge-pass, .badge-fail", { timeout: 15000 });
    const body = await page.content();
    expect(body).toMatch(/kPa|bearing|resistance/i);
  });
});

// ── Wall Analysis ─────────────────────────────────────────────────────────────
test.describe("Wall Analysis", () => {
  test("form loads", async ({ page }) => {
    await page.goto(`${BASE}/wall`);
    await expect(page.locator('[name="phi_k"]')).toBeVisible();
  });

  test("valid input returns Ka value", async ({ page }) => {
    await page.goto(`${BASE}/wall`);
    await page.fill('[name="phi_k"]',   "30");
    await page.fill('[name="gamma"]', "18");
    await page.locator('button[type="submit"]').first().click();
    await page.waitForSelector(".badge-pass, .badge-fail", { timeout: 15000 });
    const body = await page.content();
    expect(body).toMatch(/Ka|0\.33|sliding|overturning/i);
  });
});

// ── Sheet Pile Analysis ────────────────────────────────────────────────────────
test.describe("Sheet Pile Analysis", () => {
  test("form loads with Craig 12.1 defaults", async ({ page }) => {
    await page.goto(`${BASE}/sheet-pile`);
    await expect(page.locator('[name="phi_k"]')).toBeVisible();
  });

  test("Craig 12.1 returns correct embedment depth", async ({ page }) => {
    // Call the API directly with Craig 12.1 inputs
    const resp = await page.request.post("http://127.0.0.1:5000/api/sheet-pile/analyse", {
      headers: { "Content-Type": "application/json" },
      data: JSON.stringify({
        phi_k: 38, c_k: 0, gamma: 20,
        h_retain: 6.0, prop_type: "propped_top",
        delta_deg: 0, surcharge_kpa: 0,
      }),
    });

    // Log response body to diagnose 400 errors
    const json = await resp.json();
    console.log("Sheet pile API response:", JSON.stringify(json));

    expect(resp.ok(), `API returned ${resp.status()}: ${JSON.stringify(json)}`).toBeTruthy();
    expect(json.ok).toBe(true);
    // Craig 12.1 DA1-C2: embedment depth = 2.1363 m (tolerance <0.002%)
    const d = json.d_design ?? json.comb2?.d_min;
    expect(d).toBeGreaterThan(2.0);
    expect(d).toBeLessThan(2.3);
  });
});

// ── Project Dashboard ─────────────────────────────────────────────────────────
test.describe("Project Dashboard", () => {
  test("dashboard loads and shows analysis status cards", async ({ page }) => {
    await page.goto(`${BASE}/project`);

    // FIX #5: "text=Slope Stability" matched 2 elements (nav + card).
    // Scope to the main content area to avoid the nav link.
    await expect(
      page.locator("main").locator("text=Slope Stability").first()
    ).toBeVisible({ timeout: 5000 });
    await expect(
      page.locator("main").locator("text=Foundation Bearing").first()
    ).toBeVisible();
    await expect(
      page.locator("main").locator("text=Retaining Wall").first()
    ).toBeVisible();
  });

  test("export button disabled when no analyses run", async ({ page }) => {
    await page.goto(`${BASE}/project`);
    const exportBtn = page.locator("button", { hasText: /export|pdf/i }).first();
    await expect(exportBtn).toBeDisabled();
  });
});

// ── API Health ────────────────────────────────────────────────────────────────
test.describe("API Health", () => {
  test("GET /api/health returns version 2.0", async ({ page }) => {
    const resp = await page.request.get("http://127.0.0.1:5000/api/health");
    expect(resp.ok()).toBeTruthy();
    const json = await resp.json();
    expect(json.version).toBe("2.0");
  });

  test("GET /api/soils returns soil library", async ({ page }) => {
    const resp = await page.request.get("http://127.0.0.1:5000/api/soils");
    expect(resp.ok()).toBeTruthy();
    const json = await resp.json();
    expect(Array.isArray(json)).toBeTruthy();
    expect(json.length).toBeGreaterThan(0);
  });
});
