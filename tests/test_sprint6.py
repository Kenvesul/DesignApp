"""
test_sprint6.py – Sprint 6 validation suite.

Covers:
    S6-A  wall_geometry.py — wall_type (cantilever / L-wall / counterfort),
          shear key geometry, counterfort weight formula.
    S6-B  wall_analysis.py — EQU overturning: EC7 Table A.2 factor values,
          EQU vs GEO distinction, EquOverturningResult fields.
    S6-C  wall_analysis.py — R1 resistance factors verified on sliding check.
    S6-D  wall_analysis.py — Overall passes logic (GEO sliding/bearing +
          EQU overturning), counterfort weight effect.
    S6-E  api.py — response schema: equ_overturn dict, wall_type, shear key.
    S6-F  Regression — existing wall test reference values unchanged.

Reference:
    EC7 EN 1997-1:2004, §2.4.7.2; Tables A.2, A.3, A.4, A.13; Annex D.
    Bond & Harris – Decoding Eurocode 7, §14.3.
    Craig's Soil Mechanics, 9th ed., §11.2–11.4.
"""

import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.wall_geometry import RetainingWall, GAMMA_CONCRETE
from models.soil           import Soil
from models.surcharge      import UniformSurcharge
from core.wall_analysis    import (
    analyse_wall_da1,
    EquOverturningResult,
    WallResult,
    C1_G_UNFAV, C1_G_FAV, C1_Q, C1_PHI, C1_C,
    C2_G_UNFAV, C2_G_FAV, C2_Q, C2_PHI, C2_C,
    EQU_G_UNFAV, EQU_G_FAV, EQU_Q,
    R1_SLIDING, R1_BEARING,
    ECCENTRICITY_LIMIT_RATIO,
)
from api import run_wall_analysis


# ── Shared reference wall (Craig §11 example) ────────────────────────────────
def _reference_wall():
    return RetainingWall(
        h_wall=4.5, b_base=3.0, b_toe=0.3,
        t_stem_base=0.35, t_stem_top=0.25, t_base=0.45,
    )

def _backfill():   return Soil("Dense sand", 19.0, 35.0, 0.0)
def _foundation(): return Soil("Foundation",  19.0, 30.0, 0.0)


# ============================================================
#  S6-A  wall_geometry.py – New geometry fields
# ============================================================

def test_cantilever_default_wall_type():
    """Default wall_type is 'cantilever'; shear key and counterfort zero."""
    print("\n══  S6-A-1  Default wall_type  ══")
    w = _reference_wall()
    assert w.wall_type == 'cantilever'
    assert w.shear_key_depth == 0.0
    assert w.shear_key_width == 0.0
    assert w.w_counterforts  == 0.0
    print(f"  wall_type={w.wall_type!r}  w_counterforts={w.w_counterforts}  ✓")
    print("  ✅  PASS")


def test_l_wall_geometry():
    """L-wall (b_toe=0) accepted; w_counterforts=0."""
    print("\n══  S6-A-2  L-wall geometry  ══")
    w = RetainingWall(
        h_wall=4.0, b_base=2.5, b_toe=0.0,
        t_stem_base=0.3, t_stem_top=0.3, t_base=0.4,
        wall_type='L-wall',
    )
    assert w.wall_type == 'L-wall'
    assert abs(w.b_heel - 2.2) < 1e-9
    assert w.w_counterforts == 0.0
    print(f"  wall_type={w.wall_type!r}  b_heel={w.b_heel:.3f}  ✓")
    print("  ✅  PASS")


def test_counterfort_weight_formula():
    """
    Counterfort weight per metre run (Craig §11.3):
        w_cf = γ_c × (b_heel × h_wall × t_cf) / s_cf
    """
    print("\n══  S6-A-3  Counterfort weight formula  ══")
    wc = RetainingWall(
        h_wall=6.0, b_base=4.0, b_toe=0.5,
        t_stem_base=0.35, t_stem_top=0.25, t_base=0.5,
        wall_type='counterfort',
        counterfort_spacing=3.0, counterfort_thickness=0.3,
    )
    expected = GAMMA_CONCRETE * (wc.b_heel * wc.h_wall * 0.3) / 3.0
    assert abs(wc.w_counterforts - expected) < 1e-6
    print(f"  w_counterforts={wc.w_counterforts:.3f}  expected={expected:.3f}  ✓")
    print("  ✅  PASS")


def test_shear_key_geometry():
    """Shear key fields accepted; bad combos rejected."""
    print("\n══  S6-A-4  Shear key geometry  ══")
    w = RetainingWall(
        h_wall=4.5, b_base=3.0, b_toe=0.3,
        t_stem_base=0.35, t_stem_top=0.25, t_base=0.45,
        shear_key_depth=0.4, shear_key_width=0.2,
    )
    assert w.shear_key_depth == 0.4
    assert w.shear_key_width == 0.2
    print(f"  Valid key: depth={w.shear_key_depth}  width={w.shear_key_width}  ✓")
    try:
        RetainingWall(h_wall=4.0, b_base=2.5, b_toe=0.3,
            t_stem_base=0.3, t_stem_top=0.3, t_base=0.4,
            shear_key_depth=0.3)
        raise AssertionError("Should have raised ValueError")
    except ValueError as e:
        print(f"  No width → ValueError  ✓")
    try:
        RetainingWall(h_wall=4.0, b_base=2.5, b_toe=0.3,
            t_stem_base=0.3, t_stem_top=0.3, t_base=0.4,
            wall_type='gravity')
        raise AssertionError("Should have raised ValueError")
    except ValueError:
        print(f"  Bad type → ValueError  ✓")
    try:
        RetainingWall(h_wall=4.0, b_base=2.5, b_toe=0.3,
            t_stem_base=0.3, t_stem_top=0.3, t_base=0.4,
            wall_type='counterfort')
        raise AssertionError("Should have raised ValueError")
    except ValueError:
        print(f"  Missing spacing → ValueError  ✓")
    print("  ✅  PASS")


# ============================================================
#  S6-B  EQU overturning
# ============================================================

def test_equ_factor_constants():
    """EC7 Table A.2: γ_G,unfav=1.10, γ_G,fav=0.90, γ_Q=1.50."""
    print("\n══  S6-B-1  EQU factor constants (Table A.2)  ══")
    assert EQU_G_UNFAV == 1.10
    assert EQU_G_FAV   == 0.90
    assert EQU_Q       == 1.50
    assert R1_SLIDING  == 1.00
    assert R1_BEARING  == 1.00
    print(f"  γ_G,unfav={EQU_G_UNFAV}  γ_G,fav={EQU_G_FAV}  γ_Q={EQU_Q}  ✓")
    print(f"  R1_sliding={R1_SLIDING}  R1_bearing={R1_BEARING}  ✓")
    print("  ✅  PASS")


def test_geo_da1_factor_constants():
    """EC7 Tables A.3/A.4 DA1 factor values."""
    print("\n══  S6-B-2  GEO DA1 factor constants  ══")
    assert C1_G_UNFAV == 1.35; assert C1_G_FAV == 1.00
    assert C1_Q == 1.50;       assert C1_PHI == 1.00; assert C1_C == 1.00
    assert C2_G_UNFAV == 1.00; assert C2_G_FAV == 1.00
    assert C2_Q == 1.30;       assert C2_PHI == 1.25; assert C2_C == 1.25
    print("  DA1-C1: gG_unfav=1.35 gG_fav=1.00 gQ=1.50 g_phi=1.00 g_c=1.00  ✓")
    print("  DA1-C2: gG_unfav=1.00 gG_fav=1.00 gQ=1.30 g_phi=1.25 g_c=1.25  ✓")
    print("  ✅  PASS")


def test_equ_result_type_and_fields():
    """EquOverturningResult present with all required fields."""
    print("\n══  S6-B-3  EquOverturningResult fields  ══")
    res = analyse_wall_da1(_reference_wall(), _backfill(), _foundation())
    eq  = res.equ_overturn
    assert isinstance(eq, EquOverturningResult)
    for attr in ('MR_perm_char', 'MO_perm_char', 'MO_var_char',
                 'MR_equ', 'MO_equ', 'N_equ', 'fos_d', 'e', 'e_limit', 'passes'):
        assert hasattr(eq, attr)
        print(f"  {attr} = {getattr(eq, attr)!r}")
    print("  ✅  PASS")


def test_equ_factoring_arithmetic():
    """
    MR_equ = 0.90 × MR_perm_char
    MO_equ = 1.10 × MO_perm_char + 1.50 × MO_var_char
    FoS_d  = MR_equ / MO_equ
    """
    print("\n══  S6-B-4  EQU factor arithmetic  ══")
    res = analyse_wall_da1(_reference_wall(), _backfill(), _foundation())
    eq  = res.equ_overturn
    MR_exp = EQU_G_FAV   * eq.MR_perm_char
    MO_exp = EQU_G_UNFAV * eq.MO_perm_char + EQU_Q * eq.MO_var_char
    assert abs(eq.MR_equ - MR_exp) < 1e-9
    assert abs(eq.MO_equ - MO_exp) < 1e-9
    assert abs(eq.fos_d  - MR_exp / MO_exp) < 1e-9
    print(f"  MR_equ = 0.90×{eq.MR_perm_char:.2f} = {eq.MR_equ:.2f}  ✓")
    print(f"  MO_equ = 1.10×{eq.MO_perm_char:.2f}+1.50×{eq.MO_var_char:.2f} = {eq.MO_equ:.2f}  ✓")
    print(f"  FoS_d = {eq.fos_d:.4f}  ✓")
    print("  ✅  PASS")


def test_equ_more_onerous_for_restoring():
    """EQU FoS ≤ equivalent ratio computed with GEO fav=1.00."""
    print("\n══  S6-B-5  EQU more onerous for restoring  ══")
    res = analyse_wall_da1(_reference_wall(), _backfill(), _foundation())
    eq  = res.equ_overturn
    MR_geo_ref  = 1.00 * eq.MR_perm_char
    fos_geo_ref = MR_geo_ref / (EQU_G_UNFAV * eq.MO_perm_char + EQU_Q * eq.MO_var_char)
    assert eq.fos_d <= fos_geo_ref + 1e-9
    print(f"  EQU FoS_d={eq.fos_d:.4f}  ≤  GEO-ref={fos_geo_ref:.4f}  ✓")
    print("  ✅  PASS")


def test_equ_uses_characteristic_ka():
    """EQU MO_perm_char matches Pa computed from characteristic phi_k (M1)."""
    print("\n══  S6-B-6  EQU uses characteristic Ka (M1)  ══")
    from core.rankine_coulomb import ka_rankine
    wall = _reference_wall()
    bf   = _backfill()
    res  = analyse_wall_da1(wall, bf, _foundation())
    ka_char = ka_rankine(bf.phi_k)
    Pa_char = 0.5 * ka_char * bf.gamma * wall.h_wall**2
    y_Pa    = wall.h_wall / 3.0 + wall.t_base
    MO_exp  = Pa_char * y_Pa
    eq      = res.equ_overturn
    assert abs(eq.MO_perm_char - MO_exp) < 0.01
    print(f"  Ka_char={ka_char:.4f}  MO_perm_char={eq.MO_perm_char:.3f}  expected={MO_exp:.3f}  ✓")
    print("  ✅  PASS")


def test_equ_surcharge_variable_overturning():
    """Surcharge increases MO_var_char; MR_perm_char unchanged (var. restoring excluded)."""
    print("\n══  S6-B-7  EQU surcharge variable component  ══")
    wall = _reference_wall(); bf = _backfill(); fnd = _foundation()
    r0   = analyse_wall_da1(wall, bf, fnd)
    r1   = analyse_wall_da1(wall, bf, fnd, UniformSurcharge(q=20.0))
    eq0  = r0.equ_overturn; eq1 = r1.equ_overturn
    assert abs(eq0.MO_var_char) < 1e-9
    assert eq1.MO_var_char > 0
    assert eq1.MO_equ > eq0.MO_equ
    assert abs(eq0.MR_perm_char - eq1.MR_perm_char) < 1e-9
    print(f"  No surcharge MO_var=0  ✓")
    print(f"  With surcharge MO_var={eq1.MO_var_char:.3f} > 0  ✓")
    print(f"  MR_perm_char unchanged ({eq1.MR_perm_char:.3f})  ✓")
    print("  ✅  PASS")


def test_equ_fos_adequate_wall():
    """Adequate wall passes EQU (FoS_d >= 1.0, e <= B/3)."""
    print("\n══  S6-B-8  EQU passes for adequate wall  ══")
    res = analyse_wall_da1(_reference_wall(), _backfill(), _foundation())
    eq  = res.equ_overturn
    assert eq.fos_d >= 1.0
    assert eq.e <= eq.e_limit
    assert eq.passes is True
    print(f"  FoS_d={eq.fos_d:.3f} >= 1.0  e={eq.e:.3f} <= {eq.e_limit:.3f}  ✓")
    print("  ✅  PASS")


def test_equ_arithmetic_narrow_wall():
    """EQU factor arithmetic consistent for a narrow (possibly failing) wall."""
    print("\n══  S6-B-9  EQU arithmetic narrow wall  ══")
    w   = RetainingWall(h_wall=5.0, b_base=2.0, b_toe=0.5,
                        t_stem_base=0.4, t_stem_top=0.3, t_base=0.5)
    bf  = Soil("Backfill", 18.0, 30.0, 0.0)
    fnd = Soil("Foundation", 19.0, 28.0, 0.0)
    res = analyse_wall_da1(w, bf, fnd)
    eq  = res.equ_overturn
    assert abs(eq.MR_equ - EQU_G_FAV * eq.MR_perm_char) < 1e-9
    assert abs(eq.MO_equ - (EQU_G_UNFAV * eq.MO_perm_char +
                             EQU_Q * eq.MO_var_char)) < 1e-9
    print(f"  EQU FoS_d={eq.fos_d:.3f}  passes={eq.passes}")
    print(f"  Factor arithmetic consistent  ✓")
    print("  ✅  PASS")


# ============================================================
#  S6-C  R1 resistance factors
# ============================================================

def test_r1_factors_documented():
    """R1_SLIDING = R1_BEARING = 1.00 (EC7 Table A.13, R1 set)."""
    print("\n══  S6-C-1  R1 resistance factors (Table A.13)  ══")
    assert R1_SLIDING == 1.00
    assert R1_BEARING == 1.00
    res = analyse_wall_da1(_reference_wall(), _backfill(), _foundation())
    sl  = res.comb1.sliding
    fos_manual = sl.R_slide / sl.H_drive
    assert abs(fos_manual - sl.fos_d) < 1e-9
    print(f"  R1_SLIDING={R1_SLIDING}  R1_BEARING={R1_BEARING}  ✓")
    print(f"  FoS_d=R_slide/H_drive={sl.R_slide:.3f}/{sl.H_drive:.3f}={sl.fos_d:.4f}  ✓")
    print("  ✅  PASS")


# ============================================================
#  S6-D  Overall passes logic
# ============================================================

def test_overall_passes_is_geo_and_equ():
    """WallResult.passes = comb1.passes AND comb2.passes AND equ.passes."""
    print("\n══  S6-D-1  Overall passes = GEO AND EQU  ══")
    res = analyse_wall_da1(_reference_wall(), _backfill(), _foundation())
    expected = res.comb1.passes and res.comb2.passes and res.equ_overturn.passes
    assert res.passes == expected
    print(f"  GEO C1={res.comb1.passes}  GEO C2={res.comb2.passes}  "
          f"EQU={res.equ_overturn.passes}  Overall={res.passes}  ✓")
    print("  ✅  PASS")


def test_counterfort_weight_increases_stability():
    """Counterfort wall has higher N_total and sliding resistance."""
    print("\n══  S6-D-2  Counterfort weight improves stability  ══")
    bf  = Soil("Backfill",   18.0, 30.0, 0.0)
    fnd = Soil("Foundation", 18.0, 28.0, 0.0)
    kw  = dict(h_wall=6.0, b_base=4.5, b_toe=0.5,
               t_stem_base=0.4, t_stem_top=0.3, t_base=0.5)
    rc  = analyse_wall_da1(RetainingWall(**kw), bf, fnd)
    rf  = analyse_wall_da1(RetainingWall(**kw, wall_type='counterfort',
                                         counterfort_spacing=3.0,
                                         counterfort_thickness=0.3), bf, fnd)
    assert rf.comb1.sliding.N_total > rc.comb1.sliding.N_total
    assert rf.comb1.sliding.R_slide > rc.comb1.sliding.R_slide
    assert rf.equ_overturn.MR_equ   > rc.equ_overturn.MR_equ
    print(f"  N_total: canti={rc.comb1.sliding.N_total:.1f}  cf={rf.comb1.sliding.N_total:.1f}  ✓")
    print(f"  MR_equ:  canti={rc.equ_overturn.MR_equ:.1f}  cf={rf.equ_overturn.MR_equ:.1f}  ✓")
    print("  ✅  PASS")


def test_shear_key_warning_issued():
    """Shear key triggers advisory warning (passive contribution deferred)."""
    print("\n══  S6-D-3  Shear key warning  ══")
    w = RetainingWall(
        h_wall=4.5, b_base=3.0, b_toe=0.3,
        t_stem_base=0.35, t_stem_top=0.25, t_base=0.45,
        shear_key_depth=0.4, shear_key_width=0.2,
    )
    res = analyse_wall_da1(w, _backfill(), _foundation())
    assert any("shear key" in wn.lower() for wn in res.warnings)
    print(f"  Shear key warning present  ✓")
    print("  ✅  PASS")


def test_equ_geo_discrepancy_checked():
    """EQU and GEO overturning arithmetic is internally consistent."""
    print("\n══  S6-D-4  EQU/GEO discrepancy logic  ══")
    w   = RetainingWall(h_wall=6.0, b_base=2.5, b_toe=0.8,
                        t_stem_base=0.4, t_stem_top=0.3, t_base=0.5)
    bf  = Soil("Dense sand", 20.0, 28.0, 0.0)
    fnd = Soil("Foundation", 19.0, 25.0, 0.0)
    res = analyse_wall_da1(w, bf, fnd)
    eq  = res.equ_overturn
    assert abs(eq.MR_equ - EQU_G_FAV * eq.MR_perm_char) < 1e-9
    print(f"  EQU FoS_d={eq.fos_d:.3f}  GEO C1={res.comb1.overturn.fos_d:.3f}")
    if not eq.passes and res.comb1.overturn.passes:
        assert any("EQU" in w and "GEO" in w for w in res.warnings)
        print(f"  EQU/GEO discrepancy warning issued  ✓")
    else:
        print(f"  No discrepancy (both consistent)  ✓")
    print("  ✅  PASS")


# ============================================================
#  S6-E  API schema
# ============================================================

def test_api_equ_key_in_response():
    """API response includes 'equ_overturn' with all required keys."""
    print("\n══  S6-E-1  API equ_overturn key  ══")
    r = run_wall_analysis({'H_wall': 4.5, 'B_base': 3.0, 'B_toe': 0.3,
                           'gamma': 19.0, 'phi_k': 35.0})
    assert r['ok']
    assert 'equ_overturn' in r
    eq = r['equ_overturn']
    for k in ('MR_perm_char','MO_perm_char','MO_var_char','MR_equ','MO_equ',
              'N_equ','fos_d','e','e_limit','passes'):
        assert k in eq, f"Missing key: {k}"
    print(f"  equ_overturn keys present  ✓  FoS_d={eq['fos_d']}  ✓")
    print("  ✅  PASS")


def test_api_wall_type_field():
    """API accepts and echoes wall_type."""
    print("\n══  S6-E-2  API wall_type field  ══")
    for wtype in ('cantilever', 'L-wall'):
        r = run_wall_analysis({'H_wall': 4.0, 'B_base': 2.8, 'B_toe': 0.3,
                               'gamma': 18.0, 'phi_k': 30.0, 'wall_type': wtype})
        assert r['ok'] and r['wall']['wall_type'] == wtype
        print(f"  wall_type={wtype!r}  ✓")
    rc = run_wall_analysis({'H_wall': 6.0, 'B_base': 4.5, 'B_toe': 0.5,
                            'gamma': 19.0, 'phi_k': 30.0,
                            'wall_type': 'counterfort',
                            'counterfort_spacing': 3.0, 'counterfort_thickness': 0.3})
    assert rc['ok'] and rc['wall']['wall_type'] == 'counterfort'
    print(f"  counterfort  ✓")
    print("  ✅  PASS")


def test_api_shear_key_in_response():
    """API echoes shear_key_depth and issues advisory warning."""
    print("\n══  S6-E-3  API shear key response  ══")
    r = run_wall_analysis({'H_wall': 4.5, 'B_base': 3.0, 'B_toe': 0.3,
                           'gamma': 19.0, 'phi_k': 35.0,
                           'shear_key_depth': 0.35, 'shear_key_width': 0.2})
    assert r['ok']
    assert r['wall']['shear_key_depth'] == 0.35
    assert any("shear key" in w.lower() for w in r['warnings'])
    print(f"  shear_key_depth={r['wall']['shear_key_depth']}  warning present  ✓")
    print("  ✅  PASS")


def test_api_overall_passes_consistent():
    """API 'passes' = GEO(C1 AND C2) AND EQU."""
    print("\n══  S6-E-4  API passes consistency  ══")
    r = run_wall_analysis({'H_wall': 4.5, 'B_base': 3.0, 'B_toe': 0.3,
                           'gamma': 19.0, 'phi_k': 35.0})
    geo = r['comb1']['passes'] and r['comb2']['passes']
    equ = r['equ_overturn']['passes']
    assert r['passes'] == (geo and equ)
    print(f"  GEO={geo}  EQU={equ}  overall={r['passes']}  ✓")
    print("  ✅  PASS")


# ============================================================
#  S6-F  Regression
# ============================================================

def test_regression_textbook_sliding_fos():
    """
    GEO sliding FoS unchanged from pre-Sprint-6 values.

    Reference wall is WALL from test_wall_analysis.py (Craig §11 example):
        h_wall=5.0  b_base=4.5  b_toe=0.8  t_stem_base=0.5
        t_stem_top=0.4  t_base=0.6  gamma=18  phi_k=30°
    Expected: C1 FoS_d≈1.462, C2≈1.307  (tol 0.5%)
    """
    print("\n══  S6-F-1  Regression: textbook sliding FoS  ══")
    res = analyse_wall_da1(
        RetainingWall(h_wall=5.0, b_base=4.5, b_toe=0.8,
                      t_stem_base=0.5, t_stem_top=0.4, t_base=0.6),
        Soil("Dense Sand", 18.0, 30.0, 0.0),
        Soil("Dense Sand", 18.0, 30.0, 0.0),
    )
    TOL = 0.005
    for lbl, comb, exp in [("C1", res.comb1, 1.462), ("C2", res.comb2, 1.307)]:
        err = abs(comb.sliding.fos_d - exp) / exp
        assert err < TOL, f"{lbl} FoS_d={comb.sliding.fos_d:.4f} vs {exp}"
        print(f"  {lbl}: FoS_d={comb.sliding.fos_d:.4f}  err={err:.3%}  ✓")
    print("  ✅  PASS")


def test_regression_equ_fos_vs_geo_ref():
    """
    EQU FoS < GEO-ref FoS (same destabilising, fav=1.00 instead of 0.90).

    Isolates the EQU restoring-action penalty (γ_G,fav=0.90):
        FoS_EQU  = 0.90 × MR_char / (1.10 × MO_perm + 1.50 × MO_var)
        FoS_ref  = 1.00 × MR_char / (1.10 × MO_perm + 1.50 × MO_var)
        Ratio    = FoS_EQU / FoS_ref = 0.90  (exactly equal to γ_G,fav)

    Note: EQU is NOT always ≤ GEO C1 overturn because GEO C1 uses
    γ_G,unfav=1.35 (more onerous on driving) while EQU only uses 1.10.
    The EQU check is specifically more onerous than GEO C2 overturn for
    permanent loading (where EQU adds the restoring penalty 0.90).
    Reference: Bond & Harris §14.3.
    """
    print("\n══  S6-F-2  Regression: EQU FoS < GEO-ref (fav=1.00)  ══")
    res = analyse_wall_da1(_reference_wall(), _backfill(), _foundation())
    eq  = res.equ_overturn
    # GEO-ref: same destabilising as EQU but no penalty on restoring
    fos_geo_ref = (1.00 * eq.MR_perm_char /
                   max(EQU_G_UNFAV * eq.MO_perm_char + EQU_Q * eq.MO_var_char, 1e-9))
    assert eq.fos_d < fos_geo_ref - 1e-9, (
        f"EQU FoS_d={eq.fos_d:.4f} should be < GEO-ref={fos_geo_ref:.4f}"
    )
    # Ratio must exactly equal EQU_G_FAV = 0.90
    ratio = eq.fos_d / fos_geo_ref
    assert abs(ratio - EQU_G_FAV) < 1e-9, (
        f"EQU/GEO-ref ratio={ratio:.6f} should equal γ_G,fav={EQU_G_FAV}"
    )
    print(f"  EQU FoS_d={eq.fos_d:.4f}  GEO-ref={fos_geo_ref:.4f}"
          f"  ratio={ratio:.4f} == γ_G,fav={EQU_G_FAV}  ✓")
    print("  ✅  PASS")


def test_regression_summary_contains_equ():
    """WallResult.summary() includes EQU section and Table A.2 reference."""
    print("\n══  S6-F-3  Regression: summary() includes EQU  ══")
    res  = analyse_wall_da1(_reference_wall(), _backfill(), _foundation())
    summ = res.summary()
    assert "EQU" in summ
    assert "Table A.2" in summ
    print("  'EQU' and 'Table A.2' in summary  ✓")
    print("  ✅  PASS")


# ============================================================
#  Runner (no pytest dependency)
# ============================================================

if __name__ == "__main__":
    tests = [
        test_cantilever_default_wall_type,
        test_l_wall_geometry,
        test_counterfort_weight_formula,
        test_shear_key_geometry,
        test_equ_factor_constants,
        test_geo_da1_factor_constants,
        test_equ_result_type_and_fields,
        test_equ_factoring_arithmetic,
        test_equ_more_onerous_for_restoring,
        test_equ_uses_characteristic_ka,
        test_equ_surcharge_variable_overturning,
        test_equ_fos_adequate_wall,
        test_equ_arithmetic_narrow_wall,
        test_r1_factors_documented,
        test_overall_passes_is_geo_and_equ,
        test_counterfort_weight_increases_stability,
        test_shear_key_warning_issued,
        test_equ_geo_discrepancy_checked,
        test_api_equ_key_in_response,
        test_api_wall_type_field,
        test_api_shear_key_in_response,
        test_api_overall_passes_consistent,
        test_regression_textbook_sliding_fos,
        test_regression_equ_fos_vs_geo_ref,
        test_regression_summary_contains_equ,
    ]

    passed = failed = 0
    failures = []

    print("\n" + "═"*62)
    print("  SPRINT 6 — EC7 EQU/GEO Wall Verification Suite")
    print("═"*62)

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

    print("\n" + "═"*62)
    print(f"  SPRINT 6 RESULTS: {passed}/{passed+failed} passed, {failed} failed")
    print("═"*62)
    if failures:
        print("\n  Failed tests:")
        for name, err in failures:
            print(f"    - {name}: {err}")
        sys.exit(1)
    else:
        print("\n  ✅  ALL SPRINT 6 TESTS PASS")
