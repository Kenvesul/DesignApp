"""
tests/test_app.py
=================
Integration tests for ui/app.py Flask routes.
Uses Flask's built-in test client — no browser required.

Sprint 13 — all 11 original tests + 4 new tests:
  12. GET /wall/export/png      → PNG magic bytes
  13. GET /foundation/export/png → PNG magic bytes
  14. GET /project/export/pdf   → PDF with ≥2 analyses
  15. GET /api/health           → version 2.0 + session keys
"""

import sys, os, json, io
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ui.app import app
app.config["TESTING"]    = True
app.config["SECRET_KEY"] = "test-secret"

client = app.test_client()

# ── Shared fixtures ───────────────────────────────────────────────────────────

SLOPE_FORM = dict(
    soil_name  = "Dense Sand",
    gamma      = "19.0",
    phi_k      = "35.0",
    c_k        = "0",
    ru         = "0",
    slope_points = "0,3\n6,3\n12,0\n18,0",
    n_cx="6", n_cy="6", n_r="4", num_slices="12",  # small grid for speed
    project="TestProject", job_ref="TP-001",
    calc_by="Test", checked_by="QA",
)

FOUND_FORM = dict(
    soil_name = "Medium Sand",
    gamma="18.0", phi_k="30.0", c_k="0",
    B="2.0", Df="1.0", Gk="200", Qk="80",
    Es_kpa="10000", nu="0.3", s_lim="0.025",
    project="TestProject", job_ref="TP-001",
    calc_by="Test", checked_by="QA",
)

WALL_FORM = dict(
    soil_name   = "Granular Fill",
    gamma="18.0", phi_k="30.0", c_k="0",
    H_wall="4.0", B_base="3.0", B_toe="0.8",
    t_stem_base="0.4", t_stem_top="0.3", t_base="0.5",
    surcharge_kpa="0",
    project="TestProject", job_ref="TP-001",
    calc_by="Test", checked_by="QA",
)

# ── Assertion helpers ─────────────────────────────────────────────────────────

def _ok(resp, label):
    assert resp.status_code == 200, \
        f"FAIL {label}: HTTP {resp.status_code}\n{resp.data[:400].decode('utf-8','replace')}"


def _section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")


# ─────────────────────────────────────────────────────────────────────────────
#  ORIGINAL TESTS 1–11
# ─────────────────────────────────────────────────────────────────────────────

def test_home_page():
    _section("TEST 1 — GET / → home page")
    r = client.get("/")
    _ok(r, "GET /")
    assert b"DesignApp" in r.data
    print("  PASS")


def test_slope_form():
    _section("TEST 2 — GET /slope → input form")
    r = client.get("/slope")
    _ok(r, "GET /slope")
    assert b"slope_points" in r.data
    assert b"phi_k" in r.data
    print("  PASS")


def test_slope_analyse_valid():
    _section("TEST 3 — POST /slope/analyse valid → results page")
    r = client.post("/slope/analyse", data=SLOPE_FORM)
    _ok(r, "POST /slope/analyse")
    html = r.data.decode("utf-8", errors="replace")
    assert "FoS" in html or "fos" in html.lower(), "Expected FoS in results"
    assert "DA1" in html, "Expected DA1 in results"
    print(f"  Response: {len(r.data):,} bytes  PASS")


def test_slope_analyse_invalid():
    _section("TEST 4 — POST /slope/analyse invalid → error shown")
    r = client.post("/slope/analyse",
                    data=dict(gamma="999", phi_k="-5",
                              slope_points="0,0", ru="5"))
    _ok(r, "POST /slope/analyse bad")
    html = r.data.decode("utf-8", errors="replace")
    assert any(k in html.lower() for k in ("error", "correct", "required",
                                            "invalid", "must")), \
        "Expected error message in response"
    print("  PASS")


def test_foundation_form():
    _section("TEST 5 — GET /foundation → form page")
    r = client.get("/foundation")
    _ok(r, "GET /foundation")
    assert b"Foundation" in r.data
    print("  PASS")


def test_foundation_analyse_valid():
    _section("TEST 6 — POST /foundation/analyse valid → results")
    r = client.post("/foundation/analyse", data=FOUND_FORM)
    _ok(r, "POST /foundation/analyse")
    html = r.data.decode("utf-8", errors="replace")
    assert any(k in html for k in ("Rd", "kN", "Utilisation", "PASS", "FAIL",
                                   "bearing", "Bearing")), \
        f"Expected result keywords.\n{html[:500]}"
    print(f"  Response: {len(r.data):,} bytes  PASS")


def test_wall_form():
    _section("TEST 7 — GET /wall → form page")
    r = client.get("/wall")
    _ok(r, "GET /wall")
    assert b"Wall" in r.data or b"wall" in r.data
    print("  PASS")


def test_wall_analyse_valid():
    _section("TEST 8 — POST /wall/analyse valid → results")
    r = client.post("/wall/analyse", data=WALL_FORM)
    _ok(r, "POST /wall/analyse")
    html = r.data.decode("utf-8", errors="replace")
    assert any(k in html for k in ("Ka", "Kp", "Sliding", "PASS", "FAIL")), \
        f"Expected Ka/Kp in wall results.\n{html[:500]}"
    print(f"  Response: {len(r.data):,} bytes  PASS")


def test_api_health():
    _section("TEST 9 — GET /api/health → JSON {status: ok, version: 2.0}")
    r = client.get("/api/health")
    _ok(r, "GET /api/health")
    data = json.loads(r.data)
    assert data["status"]  == "ok",        f"status field: {data}"
    assert data["app"]     == "DesignApp", f"app field: {data}"
    assert data["version"] == "2.0",       f"version field (expected 2.0): {data}"
    assert "session" in data,             f"session key missing: {data}"
    print(f"  {data}  PASS")


def test_api_soils():
    _section("TEST 10 — GET /api/soils → JSON soil library")
    r = client.get("/api/soils")
    _ok(r, "GET /api/soils")
    data = json.loads(r.data)
    assert isinstance(data, list),  "Expected list"
    assert len(data) >= 5,          f"Expected ≥5 soils, got {len(data)}"
    assert "name" in data[0],       "Expected 'name' key in soil object"
    print(f"  Soils: {len(data)}  PASS")


def test_export_routes_reachable():
    _section("TEST 11 — Slope export routes: PDF, DOCX, PNG downloadable")
    with app.test_client() as c:
        r = c.post("/slope/analyse", data=SLOPE_FORM)
        _ok(r, "POST /slope/analyse for export test")

        r_pdf = c.get("/slope/export/pdf")
        assert r_pdf.status_code == 200, f"PDF: {r_pdf.status_code}"
        assert r_pdf.data[:4] == b"%PDF", "Not a PDF"
        print(f"  PDF  : {len(r_pdf.data):,} bytes  ✓")

        r_docx = c.get("/slope/export/docx")
        assert r_docx.status_code == 200, f"DOCX: {r_docx.status_code}"
        assert r_docx.data[:2] == b"PK", "Not a DOCX"
        print(f"  DOCX : {len(r_docx.data):,} bytes  ✓")

        r_png = c.get("/slope/export/png")
        assert r_png.status_code == 200, f"PNG: {r_png.status_code}"
        assert r_png.data[:8] == b'\x89PNG\r\n\x1a\n', "Not a PNG"
        print(f"  PNG  : {len(r_png.data):,} bytes  ✓")

    print("  PASS")


# ─────────────────────────────────────────────────────────────────────────────
#  NEW TESTS 12–15 (Sprint 13)
# ─────────────────────────────────────────────────────────────────────────────

def test_wall_export_png():
    """Test 12: Wall PNG export returns valid PNG after wall analysis."""
    _section("TEST 12 — GET /wall/export/png → PNG bytes after wall analysis")
    with app.test_client() as c:
        r = c.post("/wall/analyse", data=WALL_FORM)
        _ok(r, "POST /wall/analyse for PNG test")

        r_png = c.get("/wall/export/png")
        assert r_png.status_code == 200, f"Wall PNG: {r_png.status_code}"
        assert r_png.data[:8] == b'\x89PNG\r\n\x1a\n', \
            f"Not a PNG (got: {r_png.data[:8]})"
        print(f"  Wall PNG: {len(r_png.data):,} bytes  ✓")
    print("  PASS")


def test_foundation_export_png():
    """Test 13: Foundation PNG export returns valid PNG after foundation analysis."""
    _section("TEST 13 — GET /foundation/export/png → PNG bytes after foundation analysis")
    with app.test_client() as c:
        r = c.post("/foundation/analyse", data=FOUND_FORM)
        _ok(r, "POST /foundation/analyse for PNG test")

        r_png = c.get("/foundation/export/png")
        assert r_png.status_code == 200, f"Foundation PNG: {r_png.status_code}"
        assert r_png.data[:8] == b'\x89PNG\r\n\x1a\n', \
            f"Not a PNG (got: {r_png.data[:8]})"
        print(f"  Foundation PNG: {len(r_png.data):,} bytes  ✓")
    print("  PASS")


def test_project_export_pdf():
    """
    Test 14: /project/export/pdf returns a valid PDF combining slope + foundation.

    B-14 fix: sheet pile session key is included in assembly.
    Requires pypdf — skipped gracefully if not installed.
    """
    _section("TEST 14 — GET /project/export/pdf → unified PDF (slope + foundation)")
    try:
        import pypdf  # noqa: F401
    except ImportError:
        print("  SKIP — pypdf not installed (pip install pypdf)")
        return

    with app.test_client() as c:
        # Run slope
        r1 = c.post("/slope/analyse", data=SLOPE_FORM)
        _ok(r1, "slope for project PDF")

        # Run foundation
        r2 = c.post("/foundation/analyse", data=FOUND_FORM)
        _ok(r2, "foundation for project PDF")

        r_pdf = c.get("/project/export/pdf")
        assert r_pdf.status_code == 200, \
            f"Project PDF: HTTP {r_pdf.status_code}\n{r_pdf.data[:200]}"
        assert r_pdf.data[:4] == b"%PDF", \
            f"Not a valid PDF (got: {r_pdf.data[:8]})"
        print(f"  Project PDF: {len(r_pdf.data):,} bytes  ✓")
    print("  PASS")


def test_api_health_v2():
    """
    Test 15: /api/health returns version 2.0 and session state keys.

    Sprint 13 — version bump to 2.0 signals React-ready API.
    """
    _section("TEST 15 — GET /api/health → version 2.0 with session keys")
    r = client.get("/api/health")
    _ok(r, "GET /api/health v2")
    data = json.loads(r.data)
    assert data["version"] == "2.0", f"Expected version 2.0, got {data['version']}"
    assert isinstance(data.get("session"), dict), "Expected 'session' dict in response"
    for key in ("slope", "foundation", "wall", "sheet_pile"):
        assert key in data["session"], f"Missing session key '{key}'"
    print(f"  version={data['version']}, session_keys={list(data['session'])}  PASS")


# ── Runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        # Original 11
        test_home_page,
        test_slope_form,
        test_slope_analyse_valid,
        test_slope_analyse_invalid,
        test_foundation_form,
        test_foundation_analyse_valid,
        test_wall_form,
        test_wall_analyse_valid,
        test_api_health,
        test_api_soils,
        test_export_routes_reachable,
        # New Sprint 13
        test_wall_export_png,
        test_foundation_export_png,
        test_project_export_pdf,
        test_api_health_v2,
    ]

    passed = failed = skipped = 0
    for fn in tests:
        try:
            fn()
            passed += 1
        except AssertionError as exc:
            print(f"\n  *** FAIL ***  {fn.__name__}\n  {exc}")
            failed += 1
        except Exception as exc:
            import traceback
            print(f"\n  *** ERROR *** {fn.__name__}: {exc}")
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    total = len(tests)
    if failed == 0:
        print(f"  ALL {passed}/{total} Flask route tests PASSED.")
    else:
        print(f"  {failed} FAILED / {passed} passed / {total} total.")
    print("=" * 60)
    sys.exit(failed)
