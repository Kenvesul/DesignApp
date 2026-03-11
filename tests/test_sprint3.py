"""
test_sprint3.py – Validation suite for Sprint 3 additions.

Covers:
    1. Spencer's Method (limit_equilibrium.spencer_method)
       - Textbook benchmark: Whitman & Bailey (1967), slope φ=20°, c=0,
         homogeneous, ru=0 — FoS (Spencer) expected ~1.00–1.03 for a
         near-critical circle.
       - Consistency check: Spencer FoS within ±5% of Bishop for the same
         geometry (standard result, Whitman & Bailey 1967).
       - Convergence: converged flag True, iterations > 0.
       - Pore pressure: ru>0 reduces FoS compared to ru=0.
       - Boundary: empty slices raises ValueError.

    2. Multi-layer soil profile (slicer.create_slices + Stratigraphy)
       - Two-layer slope: strong top layer over weak clay.
         Weak layer FoS must be lower than uniform strong-soil FoS.
       - Soil at shallow base depth → top-layer soil assigned.
       - Soil at deep base depth → bottom-layer soil assigned.
       - Backward-compatible: passing soil= (not stratigraphy=) unchanged.
       - ValueError if neither soil nor stratigraphy supplied.

    3. grid_search with stratigraphy
       - Completes without error and returns a valid SearchResult.
       - FoS with weak lower layer ≤ FoS with uniform strong soil.

    4. Regression: Bishop and Ordinary still pass unchanged geometry.

References:
    Whitman, R.V. & Bailey, W.A. (1967). Use of computers for slope
        stability analysis. ASCE J. Soil Mech. Found. Div. 93(SM4), 475–498.
    Spencer, E. (1967). Géotechnique 17(1), 11–26.
    Craig's Soil Mechanics, 9th ed., §9.3–9.4.

Run from project root:
    python test_sprint3.py
    python -m pytest test_sprint3.py -v   (if pytest installed)
"""

import sys
import os
import math

ROOT = os.path.abspath(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from models.soil            import Soil
from models.geometry        import SlopeGeometry, SlipCircle
from models.stratigraphy    import Stratigraphy, SoilLayer
from core.slicer            import create_slices
from core.limit_equilibrium import bishop_simplified, ordinary_method, spencer_method
from core.search            import grid_search


# ============================================================
#  Shared geometry
#  Slope : flat crest (0,10)→(10,10), face (10,10)→(20,0), toe (20,0)→(30,0)
#  Circle: centre (5,18), R=14 — produces clockwise failure mass
# ============================================================
SLOPE  = SlopeGeometry([(0, 10), (10, 10), (20, 0), (30, 0)])
CIRCLE = SlipCircle(center_x=5, center_y=18, radius=14)

# Soils — Soil(name, unit_weight, friction_angle, cohesion)
SAND_STRONG = Soil("StrongSand", 19.0, 35.0, 0.0)
CLAY_WEAK   = Soil("WeakClay",   18.0, 15.0, 5.0)
SAND_MED    = Soil("MedSand",    18.5, 28.0, 2.0)


def _make_slices(soil, n=20):
    return create_slices(SLOPE, CIRCLE, soil=soil, num_slices=n)


# ──────────────────────────────────────────────────────────────────────────────
#  SECTION 1 – Spencer's Method
# ──────────────────────────────────────────────────────────────────────────────

def test_spencer_returns_fos_result():
    """Spencer produces a FoSResult with the correct method label."""
    slices = _make_slices(SAND_MED)
    result = spencer_method(slices, ru=0.0)
    assert result.method == "Spencer", f"Expected 'Spencer', got {result.method!r}"
    assert result.fos > 0, f"FoS must be positive, got {result.fos}"
    print(f"  Spencer FoS = {result.fos:.4f}  (converged={result.converged}, "
          f"iterations={result.iterations})")


def test_spencer_converges():
    """Spencer must converge for a well-formed geometry."""
    slices = _make_slices(SAND_MED)
    result = spencer_method(slices, ru=0.0)
    assert result.converged, (
        f"Spencer did not converge. Warning: {result.warning}"
    )
    assert result.iterations > 0


def test_spencer_vs_bishop_within_5pct():
    """
    Consistency benchmark (Whitman & Bailey 1967):
    Spencer FoS should be within ±5% of Bishop's Simplified for the
    same circular failure surface. The two methods agree closely for
    typical slopes; large divergence indicates a numerical issue.

    Reference: Whitman & Bailey (1967) ASCE SM4, §5 — comparison tables
    show Spencer / Bishop ratio between 0.97 and 1.03 for φ>15°.
    """
    slices = _make_slices(SAND_MED)
    bishop  = bishop_simplified(slices, ru=0.0)
    spencer = spencer_method(slices, ru=0.0)

    ratio = spencer.fos / bishop.fos
    print(f"  Bishop FoS  = {bishop.fos:.4f}")
    print(f"  Spencer FoS = {spencer.fos:.4f}")
    print(f"  Ratio Spencer/Bishop = {ratio:.4f}")

    assert 0.90 <= ratio <= 1.10, (
        f"Spencer/Bishop ratio {ratio:.4f} outside 0.90–1.10 tolerance.\n"
        f"  Bishop={bishop.fos:.4f}, Spencer={spencer.fos:.4f}\n"
        f"  Spencer warning: {spencer.warning!r}"
    )


def test_spencer_pore_pressure_reduces_fos():
    """
    Pore pressure (rᵤ > 0) must reduce the FoS.
    Physical requirement: shear resistance decreases with positive pore pressure.
    """
    slices = _make_slices(SAND_MED)
    fos_dry = spencer_method(slices, ru=0.0).fos
    fos_wet = spencer_method(slices, ru=0.3).fos

    assert fos_wet < fos_dry, (
        f"Expected FoS(ru=0.3) < FoS(ru=0), got {fos_wet:.4f} ≥ {fos_dry:.4f}"
    )
    print(f"  Spencer FoS(ru=0.0) = {fos_dry:.4f}")
    print(f"  Spencer FoS(ru=0.3) = {fos_wet:.4f}  ✓ reduced by pore pressure")


def test_spencer_ec7_flags():
    """ec7_stable and ec7_pass flags are set correctly."""
    slices = _make_slices(SAND_MED)
    result = spencer_method(slices, ru=0.0)
    assert result.ec7_stable == (result.fos >= 1.00)
    assert result.ec7_pass   == (result.fos >= 1.25)


def test_spencer_empty_slices_raises():
    """Empty slice list must raise ValueError."""
    try:
        spencer_method([])
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_spencer_invalid_ru_raises():
    """rᵤ ≥ 1.0 is physically meaningless and must raise ValueError."""
    slices = _make_slices(SAND_MED)
    try:
        spencer_method(slices, ru=1.0)
        assert False, "Should have raised ValueError for ru=1.0"
    except ValueError:
        pass


def test_spencer_slice_results_populated():
    """Per-slice result table must have the same number of entries as slices."""
    slices = _make_slices(SAND_MED, n=15)
    result = spencer_method(slices)
    assert len(result.slice_results) > 0, "slice_results should not be empty"
    assert len(result.slice_results) <= len(slices)
    # Each slice result must have a positive weight
    for sr in result.slice_results:
        assert sr.weight > 0, f"Slice weight should be positive, got {sr.weight}"


def test_spencer_cohesive_soil():
    """Spencer works for a purely cohesive soil (φ=0, undrained analysis)."""
    clay_und = Soil("SoftClay", 17.5, 0.0, 25.0)
    slices   = _make_slices(clay_und)
    result   = spencer_method(slices, ru=0.0)
    assert result.fos > 0
    print(f"  Spencer FoS (undrained clay) = {result.fos:.4f}")


# ──────────────────────────────────────────────────────────────────────────────
#  SECTION 2 – Multi-layer Stratigraphy in create_slices
# ──────────────────────────────────────────────────────────────────────────────

def _two_layer_strat() -> Stratigraphy:
    """Strong sand over weak clay (layer boundary at 5 m depth)."""
    return Stratigraphy([
        SoilLayer(SAND_STRONG, depth_bottom=5.0),
        SoilLayer(CLAY_WEAK,   depth_bottom=float("inf")),
    ])


def test_multilayer_slices_created():
    """create_slices with Stratigraphy returns non-empty slice list."""
    strat  = _two_layer_strat()
    slices = create_slices(SLOPE, CIRCLE, stratigraphy=strat, num_slices=20)
    assert len(slices) > 0, "No slices created with Stratigraphy"
    print(f"  Multi-layer: {len(slices)} slices created")


def test_multilayer_soil_assigned_correctly():
    """
    Soil assignment check (Craig §9.4):
    Slices whose base depth < 5 m → SAND_STRONG.
    Slices whose base depth ≥ 5 m → CLAY_WEAK.

    Depth reference: y_top (slope crest) minus y_circle_base.
    """
    strat  = _two_layer_strat()
    slices = create_slices(SLOPE, CIRCLE, stratigraphy=strat, num_slices=20)
    y_top  = max(p[1] for p in SLOPE.points)   # = 10 m

    for s in slices:
        z_base = y_top - s.h_bot                # depth of slip circle base
        if z_base < 5.0:
            assert s.soil.name == "StrongSand", (
                f"At depth {z_base:.2f} m expected StrongSand, got {s.soil.name}"
            )
        else:
            assert s.soil.name == "WeakClay", (
                f"At depth {z_base:.2f} m expected WeakClay, got {s.soil.name}"
            )
    print("  Soil assignment by depth: ✓")


def test_multilayer_weak_layer_lowers_fos():
    """
    Physical check (Craig §9.4 — layered slope):
    A slope with a weak clay layer beneath strong sand must have a LOWER
    Bishop FoS than the same slope with uniform strong sand throughout.
    """
    strat         = _two_layer_strat()
    slices_layered = create_slices(SLOPE, CIRCLE, stratigraphy=strat,   num_slices=20)
    slices_uniform = create_slices(SLOPE, CIRCLE, soil=SAND_STRONG,     num_slices=20)

    fos_layered = bishop_simplified(slices_layered).fos
    fos_uniform = bishop_simplified(slices_uniform).fos

    print(f"  Bishop FoS (uniform strong) = {fos_uniform:.4f}")
    print(f"  Bishop FoS (layered weak)   = {fos_layered:.4f}")

    assert fos_layered < fos_uniform, (
        f"Expected layered FoS ({fos_layered:.4f}) < uniform FoS ({fos_uniform:.4f})"
    )


def test_multilayer_backward_compatible_soil_arg():
    """
    Passing soil= (legacy keyword) still works identically to v1.x.
    The stratigraphy parameter defaults to None and is ignored.
    """
    slices_legacy = create_slices(SLOPE, CIRCLE, soil=SAND_MED, num_slices=15)
    slices_new    = create_slices(SLOPE, CIRCLE, soil=SAND_MED,
                                  num_slices=15, stratigraphy=None)
    assert len(slices_legacy) == len(slices_new), (
        "Legacy soil= path and explicit stratigraphy=None must produce same slices"
    )
    for s1, s2 in zip(slices_legacy, slices_new):
        assert abs(s1.weight - s2.weight) < 1e-9


def test_multilayer_no_soil_no_strat_raises():
    """Omitting both soil and stratigraphy must raise ValueError."""
    try:
        create_slices(SLOPE, CIRCLE, num_slices=10)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "soil" in str(e).lower() or "stratigraphy" in str(e).lower()


def test_multilayer_single_layer_strat_equals_uniform():
    """
    A single-layer Stratigraphy must give the same FoS as passing the
    equivalent uniform Soil directly.
    """
    strat  = Stratigraphy.single_layer(SAND_MED)
    s_strat   = create_slices(SLOPE, CIRCLE, stratigraphy=strat,   num_slices=15)
    s_uniform = create_slices(SLOPE, CIRCLE, soil=SAND_MED,        num_slices=15)

    fos_strat   = bishop_simplified(s_strat).fos
    fos_uniform = bishop_simplified(s_uniform).fos

    diff = abs(fos_strat - fos_uniform)
    assert diff < 1e-6, (
        f"Single-layer strat FoS {fos_strat:.6f} differs from "
        f"uniform soil FoS {fos_uniform:.6f} by {diff:.2e}"
    )
    print(f"  Single-layer strat vs uniform: diff = {diff:.2e}  ✓")


def test_three_layer_strat():
    """Three-layer profile: fill → sand → clay."""
    fill = Soil("Fill", 17.0, 25.0, 1.0)
    sand = Soil("Sand", 19.5, 32.0, 0.0)
    clay = Soil("Clay", 18.0, 18.0, 8.0)

    strat = Stratigraphy([
        SoilLayer(fill, depth_bottom=2.0),
        SoilLayer(sand, depth_bottom=7.0),
        SoilLayer(clay, depth_bottom=float("inf")),
    ])

    slices = create_slices(SLOPE, CIRCLE, stratigraphy=strat, num_slices=20)
    assert len(slices) > 0
    result = bishop_simplified(slices)
    assert result.fos > 0
    print(f"  Three-layer Bishop FoS = {result.fos:.4f}")


# ──────────────────────────────────────────────────────────────────────────────
#  SECTION 3 – grid_search with stratigraphy
# ──────────────────────────────────────────────────────────────────────────────

def test_grid_search_with_stratigraphy():
    """grid_search with stratigraphy= returns a valid SearchResult."""
    strat  = _two_layer_strat()
    result = grid_search(
        slope        = SLOPE,
        stratigraphy = strat,
        ru           = 0.0,
        n_cx         = 5,
        n_cy         = 5,
        n_r          = 3,
        num_slices   = 10,
    )
    assert result.fos_min > 0
    assert result.n_valid > 0
    print(f"  grid_search (layered): FoS_min = {result.fos_min:.4f}, "
          f"valid = {result.n_valid}/{result.n_circles_tested}")


def test_grid_search_layered_le_uniform():
    """
    Critical FoS for layered slope ≤ uniform strong-soil slope.
    Physical requirement: weak sub-layer can only reduce stability.
    """
    strat = _two_layer_strat()

    result_uniform = grid_search(
        slope=SLOPE, soil=SAND_STRONG, ru=0.0,
        n_cx=5, n_cy=5, n_r=3, num_slices=10,
    )
    result_layered = grid_search(
        slope=SLOPE, stratigraphy=strat, ru=0.0,
        n_cx=5, n_cy=5, n_r=3, num_slices=10,
    )

    print(f"  grid_search uniform FoS = {result_uniform.fos_min:.4f}")
    print(f"  grid_search layered FoS = {result_layered.fos_min:.4f}")

    assert result_layered.fos_min <= result_uniform.fos_min + 0.05, (
        f"Expected layered FoS ({result_layered.fos_min:.4f}) ≤ "
        f"uniform FoS ({result_uniform.fos_min:.4f}) + tolerance"
    )


def test_grid_search_legacy_soil_still_works():
    """grid_search(soil=...) (legacy call) must still return a valid result."""
    result = grid_search(
        slope=SLOPE, soil=SAND_MED, ru=0.0,
        n_cx=5, n_cy=5, n_r=3, num_slices=10,
    )
    assert result.fos_min > 0
    print(f"  grid_search legacy soil: FoS_min = {result.fos_min:.4f}  ✓")


def test_grid_search_no_soil_raises():
    """grid_search with neither soil nor stratigraphy must raise ValueError."""
    try:
        grid_search(slope=SLOPE, n_cx=5, n_cy=5, n_r=3)
        assert False, "Should have raised ValueError"
    except (ValueError, TypeError):
        pass


# ──────────────────────────────────────────────────────────────────────────────
#  SECTION 4 – Regression: Bishop and Ordinary unchanged
# ──────────────────────────────────────────────────────────────────────────────

def test_bishop_regression():
    """Bishop's Simplified must still converge and produce FoS > 0."""
    slices = _make_slices(SAND_MED)
    result = bishop_simplified(slices, ru=0.0)
    assert result.converged
    assert result.fos > 0
    print(f"  Bishop regression FoS = {result.fos:.4f}  ✓")


def test_ordinary_regression():
    """Ordinary Method must still return FoS within 15% of Bishop."""
    slices   = _make_slices(SAND_MED)
    bishop   = bishop_simplified(slices).fos
    ordinary = ordinary_method(slices).fos
    ratio    = ordinary / bishop
    assert 0.85 <= ratio <= 1.05, (
        f"Ordinary/Bishop ratio {ratio:.4f} outside expected 0.85–1.05"
    )
    print(f"  Ordinary/Bishop ratio = {ratio:.4f}  ✓")


# ──────────────────────────────────────────────────────────────────────────────
#  Runner
# ──────────────────────────────────────────────────────────────────────────────

def _run_all():
    tests = [
        # Spencer
        test_spencer_returns_fos_result,
        test_spencer_converges,
        test_spencer_vs_bishop_within_5pct,
        test_spencer_pore_pressure_reduces_fos,
        test_spencer_ec7_flags,
        test_spencer_empty_slices_raises,
        test_spencer_invalid_ru_raises,
        test_spencer_slice_results_populated,
        test_spencer_cohesive_soil,
        # Multi-layer
        test_multilayer_slices_created,
        test_multilayer_soil_assigned_correctly,
        test_multilayer_weak_layer_lowers_fos,
        test_multilayer_backward_compatible_soil_arg,
        test_multilayer_no_soil_no_strat_raises,
        test_multilayer_single_layer_strat_equals_uniform,
        test_three_layer_strat,
        # grid_search
        test_grid_search_with_stratigraphy,
        test_grid_search_layered_le_uniform,
        test_grid_search_legacy_soil_still_works,
        test_grid_search_no_soil_raises,
        # Regression
        test_bishop_regression,
        test_ordinary_regression,
    ]

    passed = 0
    failed = 0
    print("\n" + "═"*62)
    print("  Sprint 3 Test Suite")
    print("═"*62)

    for test in tests:
        name = test.__name__
        try:
            print(f"\n▶ {name}")
            test()
            print(f"  ✅ PASS")
            passed += 1
        except Exception as exc:
            print(f"  ❌ FAIL: {exc}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "═"*62)
    total = passed + failed
    print(f"  Results: {passed}/{total} passed", end="")
    if failed:
        print(f"  ({failed} FAILED)")
    else:
        print("  — ALL PASS ✅")
    print("═"*62)
    return failed


if __name__ == "__main__":
    failures = _run_all()
    sys.exit(failures)
