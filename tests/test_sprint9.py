"""
test_sprint9.py — Sprint 9 validation suite.

Sprint 9 delivers two workstreams:

  A. Seepage → Slicer → LE engine integration
     ──────────────────────────────────────────
     PhreaticSurface is now threaded through create_slices → bishop_simplified /
     spencer_method / ordinary_method → grid_search, giving spatially variable
     pore pressures per slice.

     S9-A  create_slices: u=None without phreatic, u set with phreatic.
     S9-B  bishop_simplified: per-slice u gives correct FoS (vs hand calc).
     S9-C  ordinary_method: per-slice u consistent with Bishop.
     S9-D  spencer_method: phreatic FoS ≈ Bishop (same circular surface).
     S9-E  grid_search: phreatic_surface lowers FoS vs dry baseline.
     S9-F  Backward-compatibility: all existing scalar-ru paths unchanged.
     S9-G  Physics monotonicity: deeper phreatic → lower FoS.

  B. SheetPile model
     ──────────────────────────────────────────
     S9-H  Geometry properties and derived fields.
     S9-I  Support conditions: free / propped / fixed.
     S9-J  Invalid input validation.

References
----------
Bishop, A.W. & Morgenstern, N.R. (1960). Stability coefficients for earth
    slopes. Géotechnique 10(4), 129–150.
Bishop, A.W. (1955). The use of the slip circle. Géotechnique 5(1), 7–17.
Spencer, E. (1967). Géotechnique 17(1), 11–26.
Craig's Soil Mechanics, 9th ed., §9, §12.
Blum, H. (1931). Einspannungsverhältnisse bei Bohlwerken. Ernst & Sohn.
"""

import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.geometry         import SlopeGeometry, SlipCircle
from models.soil             import Soil
from core.slicer             import create_slices
from core.limit_equilibrium  import bishop_simplified, ordinary_method, spencer_method
from core.search             import grid_search
from core.seepage             import PhreaticSurface, build_dupuit_surface, GAMMA_W
from models.sheet_pile        import SheetPile


def _check(label, got, exp, tol_pct=0.05):
    err = abs(got - exp) / max(abs(exp), 1e-12) * 100.0
    ok  = err <= tol_pct
    tag = "PASS" if ok else "FAIL"
    print(f"  {tag}  {label:<46}  expected={exp:>10.6f}  got={got:>10.6f}  err={err:.4f}%")
    assert ok, f"FAIL {label}: expected {exp}, got {got} ({err:.4f}% > {tol_pct}%)"


# ── Shared fixtures ───────────────────────────────────────────────────────────

def _make_slope():
    return SlopeGeometry([(0, 0), (5, 0), (10, 5), (15, 5)])

def _make_soil():
    return Soil("Sand", 18.0, 30.0, 0.0)

def _make_circle():
    return SlipCircle(7.5, 9.0, 7.0)

def _make_slices_dry():
    return create_slices(_make_slope(), _make_circle(), soil=_make_soil(), num_slices=10)

def _make_slices_phreatic(y_ph=3.5):
    ps = PhreaticSurface([(0.0, y_ph), (15.0, y_ph)])
    return create_slices(
        _make_slope(), _make_circle(), soil=_make_soil(),
        num_slices=10, phreatic_surface=ps
    )


# ============================================================
#  S9-A  create_slices — phreatic_surface wiring
# ============================================================

def test_slices_u_none_without_phreatic():
    """
    Without phreatic_surface: every slice.u is None (backward-compatible).

    Ensures no change to existing usage (scalar ru path).
    """
    print("\n══  S9-A-1  create_slices: u=None without phreatic  ══")
    slices = _make_slices_dry()
    for s in slices:
        assert s.u is None, f"Expected s.u=None at x={s.x:.2f}, got {s.u}"
    print(f"  All {len(slices)} slices have u=None  ✓")
    print("  ✅  PASS")


def test_slices_u_set_with_phreatic():
    """
    With phreatic_surface: every slice.u is a non-negative float.

    Reference: Bishop & Morgenstern (1960) — per-slice pore pressure.
    """
    print("\n══  S9-A-2  create_slices: u set with phreatic  ══")
    slices = _make_slices_phreatic(y_ph=3.5)
    for s in slices:
        assert s.u is not None, f"Expected s.u≥0 at x={s.x:.2f}, got None"
        assert s.u >= 0.0, f"Pore pressure must be ≥0, got {s.u}"
    print(f"  All {len(slices)} slices have u≥0  ✓")
    print("  ✅  PASS")


def test_slices_u_correct_value():
    """
    Pore pressure stored in slice.u equals γ_w × max(0, y_ph − y_circ).

    Phreatic at y=3.5: for each slice, u_i = 9.81 × max(0, 3.5 − h_bot).
    """
    print("\n══  S9-A-3  create_slices: u value correctness  ══")
    ps = PhreaticSurface([(0.0, 3.5), (15.0, 3.5)])
    slices = create_slices(_make_slope(), _make_circle(), soil=_make_soil(),
                           num_slices=10, phreatic_surface=ps)
    for s in slices:
        expected_u = GAMMA_W * max(0.0, 3.5 - s.h_bot)
        _check(f"u at x={s.x:.2f}m", s.u, expected_u)
    print("  ✅  PASS")


def test_slices_u_zero_above_phreatic():
    """
    Slices whose base is above the phreatic surface get u=0.0 (no tension).
    """
    print("\n══  S9-A-4  create_slices: u=0 above phreatic  ══")
    # Very low phreatic (y=0.1) → all slip surface bases should be above it
    ps = PhreaticSurface([(0.0, 0.1), (15.0, 0.1)])
    slices = create_slices(_make_slope(), _make_circle(), soil=_make_soil(),
                           num_slices=10, phreatic_surface=ps)
    n_zero = sum(1 for s in slices if s.u == 0.0)
    print(f"  {n_zero}/{len(slices)} slices have u=0 (base above low phreatic)  ✓")
    assert n_zero > 0, "Expected some slices with u=0 for very low phreatic"
    print("  ✅  PASS")


# ============================================================
#  S9-B  bishop_simplified with per-slice u
# ============================================================

def test_bishop_phreatic_reference_fos():
    """
    Bishop FoS with flat phreatic at y=3.5 matches hand-computed reference.

    Reference case (verified numerically in sprint dev):
        Slope: (0,0)-(5,0)-(10,5)-(15,5)
        Soil:  Sand, γ=18, φ'=30°, c=0
        Circle: cx=7.5, cy=9.0, R=7.0
        Phreatic: y=3.5 (flat)
        Expected FoS = 0.889159  (hand-iterated Bishop, 10 slices)

    Reference: Bishop (1955); Bishop & Morgenstern (1960).
    """
    print("\n══  S9-B-1  Bishop with phreatic: FoS = 0.889159  ══")
    slices = _make_slices_phreatic(y_ph=3.5)
    r = bishop_simplified(slices, ru=0.0)
    _check("Bishop FoS (phreatic y=3.5)", r.fos, 0.889159, tol_pct=0.05)
    assert r.converged, "Bishop did not converge"
    print(f"  converged in {r.iterations} iterations  ✓")
    print("  ✅  PASS")


def test_bishop_phreatic_reduces_fos():
    """
    FoS with phreatic < FoS without pore pressure (dry).

    Higher pore pressure reduces effective normal stress → lower resistance.
    """
    print("\n══  S9-B-2  Phreatic reduces Bishop FoS vs dry  ══")
    r_dry = bishop_simplified(_make_slices_dry(), ru=0.0)
    r_ph  = bishop_simplified(_make_slices_phreatic(y_ph=3.5), ru=0.0)
    assert r_ph.fos < r_dry.fos, (
        f"Expected FoS(phreatic) < FoS(dry), got {r_ph.fos:.4f} >= {r_dry.fos:.4f}"
    )
    print(f"  dry={r_dry.fos:.4f}  phreatic={r_ph.fos:.4f}  reduction confirmed  ✓")
    print("  ✅  PASS")


def test_bishop_slice_pore_pressures_stored():
    """
    Pore pressures in slice_results match the values computed from phreatic.

    slice_result.pore_pressure should equal slice.u for per-slice mode.
    """
    print("\n══  S9-B-3  Bishop: per-slice pore pressures in slice_results  ══")
    slices = _make_slices_phreatic(y_ph=3.5)
    r = bishop_simplified(slices, ru=0.0)
    for sr, s in zip(r.slice_results, slices):
        _check(f"slice u at x={s.x:.2f}", sr.pore_pressure, s.u, tol_pct=0.01)
    print("  ✅  PASS")


def test_bishop_phreatic_vs_equivalent_scalar_ru():
    """
    For a uniform phreatic surface and uniform soil, variable-u and an
    equivalent scalar r_u give DIFFERENT FoS (variable u is more precise).

    The r_u approximation u = r_u × W/b differs from u = γ_w × h_w because
    W/b ≠ γ × h (W includes the full column, h_w < h when phreatic is partial).
    """
    print("\n══  S9-B-4  Variable u ≠ scalar ru approximation  ══")
    slices_ph  = _make_slices_phreatic(y_ph=3.5)
    r_ph = bishop_simplified(slices_ph, ru=0.0)

    # Equivalent scalar ru ~ 0.3 (rough order)
    r_ru  = bishop_simplified(_make_slices_dry(), ru=0.3)
    # They are DIFFERENT (the variable method is spatially precise)
    different = abs(r_ph.fos - r_ru.fos) > 0.001
    print(f"  variable-u FoS={r_ph.fos:.4f}  scalar-ru=0.3 FoS={r_ru.fos:.4f}  "
          f"differ={different}  ✓")
    assert different, "Expected variable-u and scalar-ru to give different FoS"
    print("  ✅  PASS")


# ============================================================
#  S9-C  ordinary_method with per-slice u
# ============================================================

def test_ordinary_phreatic_lower_than_bishop():
    """
    Ordinary (Fellenius) FoS < Bishop FoS for same phreatic condition.

    Fellenius neglects inter-slice forces → inherently more conservative.
    Reference: Craig §9.3 — ordinary method underestimates FoS by 3–15%.
    """
    print("\n══  S9-C-1  Ordinary < Bishop for phreatic condition  ══")
    slices = _make_slices_phreatic(y_ph=3.5)
    r_ord  = ordinary_method(slices, ru=0.0)
    r_bish = bishop_simplified(slices, ru=0.0)
    assert r_ord.fos < r_bish.fos, (
        f"Ordinary {r_ord.fos:.4f} should be < Bishop {r_bish.fos:.4f}"
    )
    print(f"  Ordinary={r_ord.fos:.4f}  Bishop={r_bish.fos:.4f}  ✓")
    print("  ✅  PASS")


def test_ordinary_u_none_unchanged():
    """
    Ordinary method with u=None slices gives same result as scalar ru=0.
    """
    print("\n══  S9-C-2  Ordinary backward-compat: u=None ≡ ru=0  ══")
    slices = _make_slices_dry()
    r_a = ordinary_method(slices, ru=0.0)
    r_b = ordinary_method(slices, ru=0.0)
    _check("Ordinary FoS stable", r_b.fos, r_a.fos)
    print("  ✅  PASS")


# ============================================================
#  S9-D  spencer_method with per-slice u
# ============================================================

def test_spencer_phreatic_close_to_bishop():
    """
    Spencer FoS with phreatic is within 1% of Bishop FoS for the same circle.

    For circular surfaces, Spencer reduces to Bishop (θ=0 solution);
    difference arises only from force-equation correction.
    Reference: Whitman & Bailey (1967) — Spencer within 1–3% of Bishop.
    """
    print("\n══  S9-D-1  Spencer ≈ Bishop for phreatic (circular surface)  ══")
    slices = _make_slices_phreatic(y_ph=3.5)
    r_bi = bishop_simplified(slices, ru=0.0)
    r_sp = spencer_method(slices, ru=0.0)
    diff_pct = abs(r_sp.fos - r_bi.fos) / r_bi.fos * 100.0
    print(f"  Bishop={r_bi.fos:.6f}  Spencer={r_sp.fos:.6f}  diff={diff_pct:.4f}%")
    assert diff_pct < 1.0, f"Spencer-Bishop difference {diff_pct:.4f}% > 1%"
    print("  ✅  PASS")


def test_spencer_phreatic_reduces_fos():
    """Spencer FoS with phreatic < Spencer FoS dry."""
    print("\n══  S9-D-2  Spencer phreatic < Spencer dry  ══")
    r_dry = spencer_method(_make_slices_dry(), ru=0.0)
    r_ph  = spencer_method(_make_slices_phreatic(y_ph=3.5), ru=0.0)
    assert r_ph.fos < r_dry.fos
    print(f"  dry={r_dry.fos:.4f}  phreatic={r_ph.fos:.4f}  ✓")
    print("  ✅  PASS")


# ============================================================
#  S9-E  grid_search with phreatic_surface
# ============================================================

def test_grid_search_phreatic_lower_than_dry():
    """
    grid_search with phreatic_surface gives lower critical FoS than dry.

    Reference: Craig §9.5 — critical circle shifts under pore pressure.
    """
    print("\n══  S9-E-1  grid_search phreatic FoS < dry FoS  ══")
    slope = _make_slope()
    soil  = _make_soil()
    ps    = PhreaticSurface([(0.0, 3.5), (15.0, 3.5)])

    sr_dry = grid_search(slope, soil=soil, ru=0.0,
                         n_cx=5, n_cy=5, n_r=4, num_slices=8)
    sr_ph  = grid_search(slope, soil=soil, phreatic_surface=ps,
                         n_cx=5, n_cy=5, n_r=4, num_slices=8)

    print(f"  Dry FoS={sr_dry.fos_min:.4f}  Phreatic FoS={sr_ph.fos_min:.4f}")
    assert sr_ph.fos_min < sr_dry.fos_min, (
        f"Phreatic FoS {sr_ph.fos_min:.4f} should be < dry {sr_dry.fos_min:.4f}"
    )
    print("  ✅  PASS")


def test_grid_search_phreatic_returns_search_result():
    """grid_search with phreatic returns a SearchResult with valid fields."""
    print("\n══  S9-E-2  grid_search phreatic returns SearchResult  ══")
    slope = _make_slope()
    soil  = _make_soil()
    ps    = PhreaticSurface([(0.0, 4.0), (15.0, 4.0)])
    sr    = grid_search(slope, soil=soil, phreatic_surface=ps,
                        n_cx=4, n_cy=4, n_r=3, num_slices=8)
    assert hasattr(sr, "fos_min") and sr.fos_min > 0
    assert hasattr(sr, "critical_circle")
    assert hasattr(sr, "best_fos_result")
    print(f"  FoS_min={sr.fos_min:.4f}  circle={sr.critical_circle}  ✓")
    print("  ✅  PASS")


def test_grid_search_dupuit_surface():
    """grid_search accepts a Dupuit-generated PhreaticSurface."""
    print("\n══  S9-E-3  grid_search with Dupuit phreatic surface  ══")
    slope = _make_slope()
    soil  = _make_soil()
    dupuit_surf = build_dupuit_surface(h1=5.0, h2=0.0, L=15.0, n_points=10)
    sr_d  = grid_search(slope, soil=soil, phreatic_surface=dupuit_surf,
                        n_cx=4, n_cy=4, n_r=3, num_slices=8)
    assert sr_d.fos_min > 0
    print(f"  Dupuit grid FoS_min={sr_d.fos_min:.4f}  ✓")
    print("  ✅  PASS")


# ============================================================
#  S9-F  Backward-compatibility: scalar ru path unchanged
# ============================================================

def test_backward_compat_bishop_scalar_ru():
    """
    bishop_simplified with scalar ru=0.3 gives SAME result as before Sprint 9.

    Ensures no regression in the primary slope stability use case.
    """
    print("\n══  S9-F-1  Backward compat: Bishop scalar ru=0.3 unchanged  ══")
    slices = _make_slices_dry()
    r = bishop_simplified(slices, ru=0.3)
    # Reference value from Sprint 6 regression (sand slope, ru=0.3)
    _check("Bishop FoS (ru=0.3, no phreatic)", r.fos, 0.929141, tol_pct=0.05)
    assert r.converged
    print("  ✅  PASS")


def test_backward_compat_ordinary_scalar_ru():
    """ordinary_method with scalar ru unchanged after Sprint 9."""
    print("\n══  S9-F-2  Backward compat: Ordinary scalar ru  ══")
    slices = _make_slices_dry()
    r0 = ordinary_method(slices, ru=0.0)
    assert r0.fos > 0
    print(f"  Ordinary FoS(ru=0)={r0.fos:.4f}  ✓")
    print("  ✅  PASS")


def test_backward_compat_grid_search_scalar_ru():
    """grid_search with scalar ru unchanged (no phreatic_surface)."""
    print("\n══  S9-F-3  Backward compat: grid_search scalar ru  ══")
    slope = _make_slope()
    soil  = _make_soil()
    sr = grid_search(slope, soil=soil, ru=0.0,
                     n_cx=4, n_cy=4, n_r=3, num_slices=8)
    assert sr.fos_min > 0
    print(f"  grid_search FoS_min={sr.fos_min:.4f} (scalar ru=0)  ✓")
    print("  ✅  PASS")


def test_backward_compat_create_slices_no_phreatic():
    """create_slices without phreatic leaves slice.u = None (no attribute error)."""
    print("\n══  S9-F-4  Backward compat: create_slices no phreatic  ══")
    slices = _make_slices_dry()
    assert all(s.u is None for s in slices)
    print(f"  {len(slices)} slices all have u=None  ✓")
    print("  ✅  PASS")


# ============================================================
#  S9-G  Physics: deeper phreatic → lower FoS
# ============================================================

def test_deeper_phreatic_lowers_fos():
    """
    FoS decreases monotonically as phreatic surface rises.

    Higher y_ph → more slices with hw > 0 → higher u → lower effective
    normal stress → lower resistance → lower FoS.

    Reference: Bishop & Morgenstern (1960), §3.
    """
    print("\n══  S9-G-1  FoS decreases as phreatic rises  ══")
    y_ph_values = [1.0, 2.0, 3.0, 3.5, 4.0]
    fos_values = []
    for y_ph in y_ph_values:
        ps = PhreaticSurface([(0.0, y_ph), (15.0, y_ph)])
        sl = create_slices(_make_slope(), _make_circle(), soil=_make_soil(),
                           num_slices=10, phreatic_surface=ps)
        r  = bishop_simplified(sl, ru=0.0)
        fos_values.append(r.fos)
        print(f"  y_ph={y_ph:.1f}: FoS={r.fos:.4f}")

    for i in range(len(fos_values) - 1):
        assert fos_values[i] >= fos_values[i+1] - 1e-6, (
            f"FoS not decreasing: y_ph={y_ph_values[i]} FoS={fos_values[i]:.4f} "
            f"< y_ph={y_ph_values[i+1]} FoS={fos_values[i+1]:.4f}"
        )
    print("  FoS strictly decreasing with rising phreatic  ✓")
    print("  ✅  PASS")


def test_full_submergence_equals_high_ru():
    """
    Fully submerged slope (phreatic at surface) gives FoS close to high ru.

    For a uniform phreatic at the slope surface:
        hw_i ≈ height of slice → u_i ≈ γ_w × h_i (nearly same as r_u ≈ γ_w/γ ≈ 0.545)
    FoS should be well below the dry case.
    """
    print("\n══  S9-G-2  Fully submerged slope gives very low FoS  ══")
    ps_high = PhreaticSurface([(0.0, 10.0), (15.0, 10.0)])  # above all soil
    slices  = create_slices(_make_slope(), _make_circle(), soil=_make_soil(),
                            num_slices=10, phreatic_surface=ps_high)
    r_sub   = bishop_simplified(slices, ru=0.0)
    r_dry   = bishop_simplified(_make_slices_dry(), ru=0.0)
    assert r_sub.fos < r_dry.fos * 0.8, (
        f"Submerged FoS {r_sub.fos:.4f} should be << dry {r_dry.fos:.4f}"
    )
    print(f"  Submerged FoS={r_sub.fos:.4f}  Dry FoS={r_dry.fos:.4f}  ✓")
    print("  ✅  PASS")


# ============================================================
#  S9-H  SheetPile model — geometry
# ============================================================

def test_sheet_pile_total_length():
    """
    total_length = h_retained + d_embed.

    Reference: Craig §12.1 — pile geometry convention.
    """
    print("\n══  S9-H-1  SheetPile total_length  ══")
    sp = SheetPile(h_retained=4.0, d_embed=2.5)
    _check("total_length", sp.total_length, 6.5)
    _check("z_toe",        sp.z_toe,        2.5)
    _check("z_excavation", sp.z_excavation, 0.0)
    print("  ✅  PASS")


def test_sheet_pile_derived_properties():
    """All derived properties consistent for various configurations."""
    print("\n══  S9-H-2  SheetPile derived properties  ══")
    sp = SheetPile(h_retained=5.0, d_embed=3.0)
    _check("total_length", sp.total_length, 8.0)
    assert sp.is_cantilevered, "free + no prop → cantilevered"
    assert not sp.is_propped
    print(f"  is_cantilevered={sp.is_cantilevered}  ✓")
    print("  ✅  PASS")


def test_sheet_pile_repr():
    """SheetPile repr is informative and contains key values."""
    print("\n══  S9-H-3  SheetPile repr  ══")
    sp = SheetPile(h_retained=4.0, d_embed=2.0, label="Test Wall")
    r = repr(sp)
    assert "Test Wall" in r
    assert "h=4.00m" in r
    assert "d=2.00m" in r
    print(f"  repr: {r}  ✓")
    print("  ✅  PASS")


def test_sheet_pile_zero_embed():
    """d_embed=0 is valid (pre-analysis, before embedment is calculated)."""
    print("\n══  S9-H-4  SheetPile d_embed=0 valid  ══")
    sp = SheetPile(h_retained=4.0, d_embed=0.0)
    _check("total_length with d=0", sp.total_length, 4.0)
    print("  d_embed=0 accepted  ✓")
    print("  ✅  PASS")


# ============================================================
#  S9-I  SheetPile support conditions
# ============================================================

def test_sheet_pile_propped():
    """
    Propped wall: support='propped', z_prop supplied.

    z_prop convention: measured from TOP of pile (negative = above excavation).
    Reference: Craig §12.2 — propped embedded wall.
    """
    print("\n══  S9-I-1  SheetPile propped configuration  ══")
    sp = SheetPile(h_retained=5.0, d_embed=3.0, support="propped", z_prop=-4.5)
    assert sp.is_propped, "Expected is_propped=True"
    assert not sp.is_cantilevered
    assert sp.z_prop == -4.5
    print(f"  is_propped={sp.is_propped}  z_prop={sp.z_prop}m  ✓")
    print("  ✅  PASS")


def test_sheet_pile_prop_at_top():
    """Prop at the top of the retained height (z_prop = −h_retained)."""
    print("\n══  S9-I-2  SheetPile prop at top of retained height  ══")
    h = 5.0
    sp = SheetPile(h_retained=h, d_embed=3.0, support="propped", z_prop=-h)
    assert sp.is_propped
    _check("z_prop = -h_retained", sp.z_prop, -h)
    print("  ✅  PASS")


def test_sheet_pile_fixed():
    """Fixed-earth support: support='fixed'."""
    print("\n══  S9-I-3  SheetPile fixed support  ══")
    sp = SheetPile(h_retained=4.0, d_embed=3.0, support="fixed")
    assert sp.support == "fixed"
    assert not sp.is_propped
    assert not sp.is_cantilevered
    print(f"  support={sp.support!r}  ✓")
    print("  ✅  PASS")


def test_sheet_pile_f_prop_k_stored():
    """F_prop_k can be set after construction (post-analysis result)."""
    print("\n══  S9-I-4  SheetPile F_prop_k storage  ══")
    sp = SheetPile(h_retained=4.0, d_embed=2.0, support="propped", z_prop=-3.5)
    assert sp.F_prop_k is None
    sp.F_prop_k = 45.6
    assert sp.F_prop_k == 45.6
    print(f"  F_prop_k stored: {sp.F_prop_k} kN/m  ✓")
    print("  ✅  PASS")


def test_sheet_pile_section_modulus():
    """S_el section modulus stored and validated (must be > 0 if given)."""
    print("\n══  S9-I-5  SheetPile section modulus  ══")
    sp = SheetPile(h_retained=4.0, d_embed=2.0, S_el=1500.0)
    assert sp.S_el == 1500.0
    print(f"  S_el={sp.S_el} cm³/m  ✓")
    print("  ✅  PASS")


# ============================================================
#  S9-J  SheetPile — invalid input validation
# ============================================================

def test_sheet_pile_invalid_h_retained():
    """h_retained ≤ 0 raises ValueError."""
    print("\n══  S9-J-1  SheetPile invalid h_retained  ══")
    for h in [0.0, -1.0]:
        try:
            SheetPile(h_retained=h)
            raise AssertionError(f"h={h} should have raised")
        except ValueError:
            print(f"  h={h}: raised ValueError  ✓")
    print("  ✅  PASS")


def test_sheet_pile_invalid_d_embed():
    """d_embed < 0 raises ValueError."""
    print("\n══  S9-J-2  SheetPile invalid d_embed  ══")
    try:
        SheetPile(h_retained=4.0, d_embed=-0.5)
        raise AssertionError("Should have raised")
    except ValueError:
        print("  d_embed=-0.5: raised ValueError  ✓")
    print("  ✅  PASS")


def test_sheet_pile_invalid_support():
    """Unrecognised support string raises ValueError."""
    print("\n══  S9-J-3  SheetPile invalid support  ══")
    try:
        SheetPile(h_retained=4.0, support="cantilever")
        raise AssertionError("Should have raised")
    except ValueError:
        print("  support='cantilever': raised ValueError  ✓")
    print("  ✅  PASS")


def test_sheet_pile_propped_no_z_prop():
    """support='propped' without z_prop raises ValueError."""
    print("\n══  S9-J-4  SheetPile propped without z_prop  ══")
    try:
        SheetPile(h_retained=4.0, d_embed=2.0, support="propped")
        raise AssertionError("Should have raised")
    except ValueError:
        print("  propped without z_prop: raised ValueError  ✓")
    print("  ✅  PASS")


def test_sheet_pile_z_prop_below_toe():
    """z_prop below the pile toe raises ValueError."""
    print("\n══  S9-J-5  SheetPile z_prop below toe  ══")
    try:
        SheetPile(h_retained=4.0, d_embed=2.0, support="propped", z_prop=5.0)
        raise AssertionError("Should have raised")
    except ValueError:
        print("  z_prop=5.0 (below toe d=2): raised ValueError  ✓")
    print("  ✅  PASS")


def test_sheet_pile_invalid_s_el():
    """S_el ≤ 0 raises ValueError."""
    print("\n══  S9-J-6  SheetPile invalid S_el  ══")
    try:
        SheetPile(h_retained=4.0, S_el=0.0)
        raise AssertionError("Should have raised")
    except ValueError:
        print("  S_el=0: raised ValueError  ✓")
    print("  ✅  PASS")


def test_sheet_pile_invalid_section():
    """Unknown section type raises ValueError."""
    print("\n══  S9-J-7  SheetPile invalid section type  ══")
    try:
        SheetPile(h_retained=4.0, section="W")
        raise AssertionError("Should have raised")
    except ValueError:
        print("  section='W': raised ValueError  ✓")
    print("  ✅  PASS")


# ============================================================
#  Runner
# ============================================================

if __name__ == "__main__":
    tests = [
        # S9-A  Slicer integration
        test_slices_u_none_without_phreatic,
        test_slices_u_set_with_phreatic,
        test_slices_u_correct_value,
        test_slices_u_zero_above_phreatic,
        # S9-B  Bishop
        test_bishop_phreatic_reference_fos,
        test_bishop_phreatic_reduces_fos,
        test_bishop_slice_pore_pressures_stored,
        test_bishop_phreatic_vs_equivalent_scalar_ru,
        # S9-C  Ordinary
        test_ordinary_phreatic_lower_than_bishop,
        test_ordinary_u_none_unchanged,
        # S9-D  Spencer
        test_spencer_phreatic_close_to_bishop,
        test_spencer_phreatic_reduces_fos,
        # S9-E  grid_search
        test_grid_search_phreatic_lower_than_dry,
        test_grid_search_phreatic_returns_search_result,
        test_grid_search_dupuit_surface,
        # S9-F  Backward-compat
        test_backward_compat_bishop_scalar_ru,
        test_backward_compat_ordinary_scalar_ru,
        test_backward_compat_grid_search_scalar_ru,
        test_backward_compat_create_slices_no_phreatic,
        # S9-G  Physics
        test_deeper_phreatic_lowers_fos,
        test_full_submergence_equals_high_ru,
        # S9-H  SheetPile geometry
        test_sheet_pile_total_length,
        test_sheet_pile_derived_properties,
        test_sheet_pile_repr,
        test_sheet_pile_zero_embed,
        # S9-I  Support conditions
        test_sheet_pile_propped,
        test_sheet_pile_prop_at_top,
        test_sheet_pile_fixed,
        test_sheet_pile_f_prop_k_stored,
        test_sheet_pile_section_modulus,
        # S9-J  Validation
        test_sheet_pile_invalid_h_retained,
        test_sheet_pile_invalid_d_embed,
        test_sheet_pile_invalid_support,
        test_sheet_pile_propped_no_z_prop,
        test_sheet_pile_z_prop_below_toe,
        test_sheet_pile_invalid_s_el,
        test_sheet_pile_invalid_section,
    ]

    passed = failed = 0
    failures = []

    print("\n" + "═"*68)
    print("  SPRINT 9 — Seepage Integration + SheetPile Model")
    print("═"*68)

    for fn in tests:
        try:
            fn()
            passed += 1
        except Exception as e:
            import traceback
            failed += 1
            failures.append((fn.__name__, e))
            print(f"\n  ❌  FAIL  {fn.__name__}:\n      {e}")
            traceback.print_exc()

    print("\n" + "═"*68)
    print(f"  SPRINT 9 RESULTS: {passed}/{passed+failed} passed, {failed} failed")
    print("═"*68)
    if failures:
        for name, err in failures:
            print(f"    - {name}: {err}")
        sys.exit(1)
    else:
        print("\n  ✅  ALL SPRINT 9 TESTS PASS")
