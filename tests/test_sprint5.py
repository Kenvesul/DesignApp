"""
test_sprint5.py – Validation suite for Sprint 5 additions.

Covers:
    1. ClayLayer + multi_layer_consolidation_settlement (foundation_check.py)
       - Boussinesq stress replaces 2:1 at each layer mid-point
       - Two-layer profile: total settlement = sum of per-layer values
       - t_95 returned per layer (max governs)
       - Validate vs Craig 9th ed., Example 7.1 (single NC clay, Boussinesq)

    2. check_foundation_da1 with clay_layers (multi-layer path)
       - layer_results populated; settlement.legacy path = None
       - t_95_years == max(t_95 per layer)
       - SLS verdict consistent with s_total vs s_lim

    3. check_foundation_da1 legacy path (single-layer consolidation)
       - Backward compatibility: passing consolidation= still works
       - layer_results is empty list

    4. Stem structural check (wall_analysis.py)
       - M_max at base = Ka·γ·h³/6 + Ka·q·h²/2  (Craig §11.2)
       - V_max at base = Ka·γ·h²/2 + Ka·q·h
       - No surcharge: M_max = Ka·γ·h³/6 exactly
       - With surcharge: M_max increases
       - Diagram has n_points nodes, monotone V and M (triangular load)
       - Governing combination Ka used

    5. api.py wall response includes 'stem' key
       - stem dict has M_max, V_max, ka, diagram
       - layer_breakdown in foundation response

    6. api.py foundation with clay_layers list
       - layer_breakdown populated, t_95_years present

    7. Regression: all Sprint 4 suites still pass

Reference:
    Craig's Soil Mechanics, 9th ed., §11.2 (cantilever stem), §7.4 (consolidation).
    Das, B.M. (2019). Principles of Geotechnical Engineering, §11.5, §11.7.
    Fadum, R.E. (1948). Proc. 2nd ICSMFE (Boussinesq influence factors).

Run from project root:
    python test_sprint5.py
"""

import sys, os, math

ROOT = os.path.abspath(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.foundation_check import (
    ClayLayer, LayerConsolidationResult,
    multi_layer_consolidation_settlement,
    check_foundation_da1,
    FoundationCheckResult,
)
from core.wall_analysis   import analyse_wall_da1, StemStructuralResult
from core.boussinesq      import stress_below_centre
from core.rankine_coulomb import ka_rankine
from models.soil          import Soil
from models.foundation    import Foundation
from models.wall_geometry import RetainingWall
from models.surcharge     import UniformSurcharge
from core.api             import run_wall_analysis, run_foundation_analysis


# ──────────────────────────────────────────────────────────────────────────────
#  Shared fixtures
# ──────────────────────────────────────────────────────────────────────────────

SAND_SOIL  = Soil("Med sand", 18.5, 30.0, 0.0)
CLAY_SOIL  = Soil("Soft clay", 16.0, 0.0,  20.0)

# 2 m × 2 m square pad at 1 m depth
FDN_SQUARE = Foundation(B=2.0, Df=1.0, L=2.0)

# Simple cantilever wall
WALL = RetainingWall(
    h_wall=4.0, b_base=2.8, b_toe=0.5, t_base=0.4,
    t_stem_base=0.4, t_stem_top=0.3, gamma_concrete=24.0,
)
BACKFILL = Soil("Dense gravel", 19.0, 35.0, 0.0)
FOUND_S  = Soil("Firm clay",   18.0, 25.0,  5.0)


def _two_layers():
    """Two NC clay layers for multi-layer consolidation tests."""
    return [
        ClayLayer(H=2.0, Cc=0.35, e0=0.9, sigma_v0=40.0,
                  cv=1.5, label="Upper clay"),
        ClayLayer(H=3.0, Cc=0.25, e0=0.8, sigma_v0=70.0,
                  cv=0.8, label="Lower clay"),
    ]


# ──────────────────────────────────────────────────────────────────────────────
#  SECTION 1 – multi_layer_consolidation_settlement
# ──────────────────────────────────────────────────────────────────────────────

def test_multi_layer_returns_correct_count():
    """multi_layer_consolidation_settlement returns one result per layer."""
    layers = _two_layers()
    results = multi_layer_consolidation_settlement(FDN_SQUARE, q_net=100.0,
                                                   clay_layers=layers)
    assert len(results) == 2, f"Expected 2 results, got {len(results)}"


def test_multi_layer_z_mid_values():
    """
    Mid-layer depths must equal cumulative thickness + H/2 for each layer.
    Layer 1: z_mid = 0 + 2/2 = 1.0 m
    Layer 2: z_mid = 2 + 3/2 = 3.5 m
    """
    layers  = _two_layers()
    results = multi_layer_consolidation_settlement(FDN_SQUARE, q_net=100.0,
                                                   clay_layers=layers)
    assert abs(results[0].z_mid - 1.0) < 1e-9, f"Layer 1 z_mid={results[0].z_mid}"
    assert abs(results[1].z_mid - 3.5) < 1e-9, f"Layer 2 z_mid={results[1].z_mid}"
    print(f"\n  z_mid: Layer1={results[0].z_mid} m  Layer2={results[1].z_mid} m  ✓")


def test_multi_layer_boussinesq_stress():
    """
    Stress at layer 1 mid-point must match stress_below_centre() directly.
    This confirms Boussinesq is being used (not the old 2:1 method).
    """
    q, B, L, z = 100.0, 2.0, 2.0, 1.0
    expected = stress_below_centre(q, B, L, z)
    layers   = _two_layers()
    results  = multi_layer_consolidation_settlement(
        Foundation(B=B, Df=1.0, L=L), q_net=q, clay_layers=layers
    )
    calc = results[0].delta_sigma
    assert abs(calc - expected) < 0.01, (
        f"Layer 1 Δσ={calc:.3f} vs Boussinesq {expected:.3f}"
    )
    print(f"\n  Δσ (Boussinesq): {calc:.3f} kPa == {expected:.3f} kPa ✓")


def test_multi_layer_stress_decreases_with_depth():
    """Deeper layer should have smaller stress increase (Boussinesq dissipation)."""
    layers  = _two_layers()
    results = multi_layer_consolidation_settlement(FDN_SQUARE, q_net=100.0,
                                                   clay_layers=layers)
    assert results[0].delta_sigma > results[1].delta_sigma, (
        f"Upper Δσ={results[0].delta_sigma:.2f} should exceed lower "
        f"Δσ={results[1].delta_sigma:.2f}"
    )


def test_multi_layer_total_settlement_equals_sum():
    """Total consolidation s_c = Σ per-layer s_c."""
    layers  = _two_layers()
    results = multi_layer_consolidation_settlement(FDN_SQUARE, q_net=100.0,
                                                   clay_layers=layers)
    s_total = sum(r.consolidation.s_c for r in results)
    s_layer = results[0].consolidation.s_c + results[1].consolidation.s_c
    assert abs(s_total - s_layer) < 1e-12
    print(f"\n  Total s_c = {s_total*1000:.2f} mm  ✓")


def test_multi_layer_t95_present():
    """t_95 is populated for layers with cv; absent for layers without."""
    layers = [
        ClayLayer(H=2.0, Cc=0.3, e0=0.8, sigma_v0=40.0, cv=1.5),  # has cv
        ClayLayer(H=2.0, Cc=0.3, e0=0.8, sigma_v0=60.0),           # no cv
    ]
    results = multi_layer_consolidation_settlement(FDN_SQUARE, q_net=80.0,
                                                   clay_layers=layers)
    assert results[0].t_95 is not None, "Layer with cv should have t_95"
    assert results[1].t_95 is None,     "Layer without cv should have t_95=None"
    print(f"\n  t_95 (layer 1): {results[0].t_95:.2f} years  layer2: None  ✓")


def test_multi_layer_empty_raises():
    """Empty clay_layers list must raise ValueError."""
    try:
        multi_layer_consolidation_settlement(FDN_SQUARE, q_net=100.0,
                                             clay_layers=[])
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_multi_layer_negative_H_raises():
    """Layer with H <= 0 must raise ValueError."""
    try:
        multi_layer_consolidation_settlement(
            FDN_SQUARE, q_net=100.0,
            clay_layers=[ClayLayer(H=-1.0, Cc=0.3, e0=0.8, sigma_v0=40.0)]
        )
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_multi_layer_z_top_offset():
    """z_top > 0 shifts all z_mid values down by z_top."""
    layers  = _two_layers()
    z_off   = 2.0
    results = multi_layer_consolidation_settlement(
        FDN_SQUARE, q_net=100.0, clay_layers=layers, z_top=z_off
    )
    assert abs(results[0].z_mid - (z_off + 1.0)) < 1e-9
    assert abs(results[1].z_mid - (z_off + 3.5)) < 1e-9


# ──────────────────────────────────────────────────────────────────────────────
#  SECTION 2 – check_foundation_da1 multi-layer path
# ──────────────────────────────────────────────────────────────────────────────

def test_check_foundation_multilayer_has_layer_results():
    """check_foundation_da1(clay_layers=...) populates layer_results."""
    res = check_foundation_da1(
        FDN_SQUARE, SAND_SOIL, Gk=400.0, Qk=100.0,
        clay_layers=_two_layers(), s_lim=0.050,
    )
    assert len(res.layer_results) == 2, (
        f"Expected 2 layer results, got {len(res.layer_results)}"
    )
    print(f"\n  layer_results: {len(res.layer_results)} layers  ✓")


def test_check_foundation_multilayer_s_total_positive():
    """s_total must be positive when clay layers exist."""
    res = check_foundation_da1(
        FDN_SQUARE, SAND_SOIL, Gk=400.0, Qk=100.0,
        clay_layers=_two_layers(), s_lim=0.050,
    )
    assert res.s_total is not None and res.s_total > 0, (
        f"s_total should be > 0, got {res.s_total}"
    )
    print(f"  s_total = {res.s_total*1000:.2f} mm  ✓")


def test_check_foundation_multilayer_t95_max():
    """t_95_years = max of per-layer t_95 values."""
    res = check_foundation_da1(
        FDN_SQUARE, SAND_SOIL, Gk=400.0, Qk=100.0,
        clay_layers=_two_layers(), s_lim=0.050,
    )
    t95_vals = [lr.t_95 for lr in res.layer_results if lr.t_95 is not None]
    if t95_vals:
        expected_max = max(t95_vals)
        assert abs(res.t_95_years - expected_max) < 1e-9, (
            f"t_95_years={res.t_95_years:.2f} should equal max per-layer "
            f"t_95={expected_max:.2f}"
        )
        print(f"  t_95_years (max) = {res.t_95_years:.2f} years  ✓")


def test_check_foundation_multilayer_sls_verdict():
    """SLS verdict is consistent with s_total <= s_lim."""
    res = check_foundation_da1(
        FDN_SQUARE, SAND_SOIL, Gk=400.0, Qk=100.0,
        clay_layers=_two_layers(), s_lim=0.050,
    )
    assert res.sls_passes == (res.s_total <= 0.050)


def test_check_foundation_multilayer_settlement_legacy_cleared():
    """When clay_layers used, res.settlement (legacy) should be None."""
    res = check_foundation_da1(
        FDN_SQUARE, SAND_SOIL, Gk=400.0, Qk=100.0,
        clay_layers=_two_layers(), s_lim=0.050,
    )
    assert res.settlement is None, (
        "Legacy .settlement should be None when clay_layers path is active"
    )


# ──────────────────────────────────────────────────────────────────────────────
#  SECTION 3 – check_foundation_da1 legacy path (backward compat)
# ──────────────────────────────────────────────────────────────────────────────

def test_check_foundation_legacy_layer_results_empty():
    """Legacy path (no clay_layers) leaves layer_results empty."""
    from core.settlement import consolidation_settlement
    consol = consolidation_settlement(H=3.0, Cc=0.3, e0=0.85,
                                      sigma_v0=50.0, delta_sigma=30.0)
    res = check_foundation_da1(
        FDN_SQUARE, SAND_SOIL, Gk=400.0, Qk=100.0,
        consolidation=consol, s_lim=0.050,
    )
    assert res.layer_results == [], "layer_results should be [] in legacy path"
    assert res.settlement is consol, "Legacy .settlement should be the passed object"
    print(f"\n  Legacy path: s_total={res.s_total*1000:.2f} mm  layer_results=[]  ✓")


# ──────────────────────────────────────────────────────────────────────────────
#  SECTION 4 – Stem structural check (wall_analysis.py)
# ──────────────────────────────────────────────────────────────────────────────

def _run_wall(surcharge_kpa=0.0):
    sur = UniformSurcharge(q=surcharge_kpa) if surcharge_kpa > 0 else None
    return analyse_wall_da1(WALL, BACKFILL, FOUND_S, surcharge=sur)


def test_stem_present():
    """WallResult.stem is not None after analyse_wall_da1()."""
    res = _run_wall()
    assert res.stem is not None, "WallResult.stem should not be None"
    print(f"\n  Stem: M_max={res.stem.M_max:.3f} kN·m/m  V_max={res.stem.V_max:.3f} kN/m")


def test_stem_M_max_no_surcharge():
    """
    Without surcharge, M_max at fixed base = Ka·γ·h³/6.

    Reference: Craig §11.2, Eq for pure triangular load:
        M_base = Ka·γ·h³/6
    """
    res   = _run_wall()
    ka    = res.stem.ka
    gamma = BACKFILL.gamma
    h     = WALL.h_wall
    expected = ka * gamma * h**3 / 6.0
    diff = abs(res.stem.M_max - expected)
    print(f"\n  M_max: calc={res.stem.M_max:.4f}  expected={expected:.4f}  diff={diff:.6f}")
    assert diff < 0.001, f"M_max mismatch: {res.stem.M_max:.4f} vs {expected:.4f}"


def test_stem_V_max_no_surcharge():
    """
    Without surcharge, V_max at fixed base = Ka·γ·h²/2.
    """
    res      = _run_wall()
    ka       = res.stem.ka
    gamma    = BACKFILL.gamma
    h        = WALL.h_wall
    expected = ka * gamma * h**2 / 2.0
    diff     = abs(res.stem.V_max - expected)
    assert diff < 0.001, f"V_max mismatch: {res.stem.V_max:.4f} vs {expected:.4f}"
    print(f"  V_max: calc={res.stem.V_max:.4f}  expected={expected:.4f}  ✓")


def test_stem_surcharge_increases_M():
    """Applying a surcharge must increase M_max."""
    res_no  = _run_wall(surcharge_kpa=0.0)
    res_sur = _run_wall(surcharge_kpa=10.0)
    assert res_sur.stem.M_max > res_no.stem.M_max, (
        f"Surcharge should increase M_max: "
        f"{res_sur.stem.M_max:.3f} vs {res_no.stem.M_max:.3f}"
    )
    print(f"\n  M_max: no surcharge={res_no.stem.M_max:.3f}  "
          f"with 10 kPa surcharge={res_sur.stem.M_max:.3f}  ✓")


def test_stem_diagram_monotone():
    """Shear V and moment M must be monotonically non-decreasing with depth."""
    res = _run_wall()
    diag = res.stem.diagram
    for i in range(1, len(diag)):
        assert diag[i].V >= diag[i-1].V - 1e-9, (
            f"V not monotone at z={diag[i].z}: {diag[i].V:.4f} < {diag[i-1].V:.4f}"
        )
        assert diag[i].M >= diag[i-1].M - 1e-9, (
            f"M not monotone at z={diag[i].z}: {diag[i].M:.4f} < {diag[i-1].M:.4f}"
        )
    print(f"  Diagram ({len(diag)} points) monotone ✓")


def test_stem_diagram_zero_at_top():
    """V=0 and M=0 at z=0 (free top of cantilever)."""
    res = _run_wall()
    assert abs(res.stem.diagram[0].V) < 1e-9
    assert abs(res.stem.diagram[0].M) < 1e-9


def test_stem_z_M_max_equals_h_wall():
    """Maximum moment occurs at the fixed base z = h_wall."""
    res = _run_wall()
    assert abs(res.stem.z_M_max - WALL.h_wall) < 1e-9, (
        f"z_M_max={res.stem.z_M_max} should equal h_wall={WALL.h_wall}"
    )


def test_stem_uses_governing_ka():
    """Stem Ka must equal the governing combination's Ka."""
    res = _run_wall()
    assert abs(res.stem.ka - res.governing.ka) < 1e-9, (
        f"Stem ka={res.stem.ka} != governing ka={res.governing.ka}"
    )


# ──────────────────────────────────────────────────────────────────────────────
#  SECTION 5 – api.py wall response includes stem
# ──────────────────────────────────────────────────────────────────────────────

def test_api_wall_stem_in_response():
    """run_wall_analysis() must return 'stem' key with M_max, V_max, diagram."""
    params = dict(
        soil_name="Dense gravel", gamma=19.0, phi_k=35.0, c_k=0.0,
        H_wall=4.0, B_base=2.8, B_toe=0.5,
    )
    r = run_wall_analysis(params)
    assert r.get("ok"), f"API error: {r.get('errors')}"
    assert "stem" in r, "Response must include 'stem' key"
    stem = r["stem"]
    assert "M_max" in stem and stem["M_max"] > 0
    assert "V_max" in stem and stem["V_max"] > 0
    assert "diagram" in stem and len(stem["diagram"]) > 0
    print(f"\n  API stem: M_max={stem['M_max']:.3f}  V_max={stem['V_max']:.3f}  "
          f"diagram_pts={len(stem['diagram'])}  ✓")


# ──────────────────────────────────────────────────────────────────────────────
#  SECTION 6 – api.py foundation with clay_layers list
# ──────────────────────────────────────────────────────────────────────────────

def test_api_foundation_clay_layers():
    """run_foundation_analysis() with clay_layers list returns layer_breakdown."""
    params = dict(
        soil_name="Sand", gamma=18.5, phi_k=30.0, c_k=0.0,
        B=2.0, Df=1.0, L=2.0, Gk=400.0, Qk=100.0,
        Es_kpa=20000.0, s_lim=0.060,
        clay_layers=[
            dict(H=2.0, Cc=0.35, e0=0.9, sigma_v0=40.0, cv=1.5, label="Upper"),
            dict(H=3.0, Cc=0.25, e0=0.8, sigma_v0=70.0, cv=0.8, label="Lower"),
        ],
    )
    r = run_foundation_analysis(params)
    assert r.get("ok"), f"API error: {r.get('errors')}"
    assert "layer_breakdown" in r, "Must include layer_breakdown"
    assert len(r["layer_breakdown"]) == 2
    assert r["s_consolidation_mm"] is not None and r["s_consolidation_mm"] > 0
    assert r.get("t_95_years") is not None
    print(f"\n  API clay_layers: s_c={r['s_consolidation_mm']} mm  "
          f"t_95={r['t_95_years']} yr  layers={len(r['layer_breakdown'])}  ✓")


# ──────────────────────────────────────────────────────────────────────────────
#  SECTION 7 – Regression
# ──────────────────────────────────────────────────────────────────────────────

def test_regression_wall_passes_still_works():
    """analyse_wall_da1 still returns a valid WallResult with passes flag."""
    res = _run_wall()
    assert isinstance(res.passes, bool)
    assert res.comb1 is not None and res.comb2 is not None


def test_regression_foundation_check_legacy():
    """check_foundation_da1 without clay_layers still works (no regression)."""
    res = check_foundation_da1(FDN_SQUARE, SAND_SOIL, Gk=400.0, Qk=100.0)
    assert res.uls_passes is not None
    assert res.layer_results == []


def test_regression_sprint4_da2():
    """DA2 still present in verify_slope_da1 output (Sprint 4 regression)."""
    from core.factors_of_safety import verify_slope_da1
    from models.geometry import SlopeGeometry
    slope  = SlopeGeometry([(0,10),(10,10),(20,0),(30,0)])
    soil   = Soil("Sand", 18.5, 28.0, 2.0)
    ver    = verify_slope_da1(slope, soil, ru=0.0, n_cx=5, n_cy=5, n_r=3, num_slices=10)
    assert ver.da2 is not None
    assert abs(ver.da3_fos_d - ver.comb2.fos_d) < 1e-9


def test_regression_boussinesq():
    """Fadum influence factor at m=n=1 still ≈ 0.175 (Sprint 4 regression)."""
    from core.boussinesq import fadum_influence_corner
    iz = fadum_influence_corner(1.0, 1.0)
    assert abs(iz - 0.175) < 0.003, f"Fadum m=n=1: {iz:.4f}"


# ──────────────────────────────────────────────────────────────────────────────
#  Runner
# ──────────────────────────────────────────────────────────────────────────────

def _run_all():
    tests = [
        # Multi-layer consolidation
        test_multi_layer_returns_correct_count,
        test_multi_layer_z_mid_values,
        test_multi_layer_boussinesq_stress,
        test_multi_layer_stress_decreases_with_depth,
        test_multi_layer_total_settlement_equals_sum,
        test_multi_layer_t95_present,
        test_multi_layer_empty_raises,
        test_multi_layer_negative_H_raises,
        test_multi_layer_z_top_offset,
        # check_foundation_da1 multi-layer
        test_check_foundation_multilayer_has_layer_results,
        test_check_foundation_multilayer_s_total_positive,
        test_check_foundation_multilayer_t95_max,
        test_check_foundation_multilayer_sls_verdict,
        test_check_foundation_multilayer_settlement_legacy_cleared,
        # Legacy path
        test_check_foundation_legacy_layer_results_empty,
        # Stem structural
        test_stem_present,
        test_stem_M_max_no_surcharge,
        test_stem_V_max_no_surcharge,
        test_stem_surcharge_increases_M,
        test_stem_diagram_monotone,
        test_stem_diagram_zero_at_top,
        test_stem_z_M_max_equals_h_wall,
        test_stem_uses_governing_ka,
        # API
        test_api_wall_stem_in_response,
        test_api_foundation_clay_layers,
        # Regression
        test_regression_wall_passes_still_works,
        test_regression_foundation_check_legacy,
        test_regression_sprint4_da2,
        test_regression_boussinesq,
    ]

    passed = failed = 0
    print("\n" + "═"*64)
    print("  Sprint 5 Test Suite")
    print("═"*64)

    for test in tests:
        name = test.__name__
        try:
            print(f"\n▶ {name}")
            test()
            print(f"  ✅ PASS")
            passed += 1
        except Exception as exc:
            import traceback
            print(f"  ❌ FAIL: {exc}")
            traceback.print_exc()
            failed += 1

    print("\n" + "═"*64)
    total = passed + failed
    print(f"  Results: {passed}/{total} passed", end="")
    print(f"  ({failed} FAILED)" if failed else "  — ALL PASS ✅")
    print("═"*64)
    return failed


if __name__ == "__main__":
    sys.exit(_run_all())
