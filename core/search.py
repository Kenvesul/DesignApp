"""
search.py – Critical slip circle search for minimum Factor of Safety.

Sweeps a 3-D grid of trial circles (cx, cy, R) and returns the circle
that produces the lowest Bishop FoS — the "critical circle."

Algorithm: Grid Search (Phase 0.6 of the DesignApp roadmap).
    For each combination (cx_i, cy_j, R_k) in the search grid:
        1. Attempt to create slices (skip if no valid mass exists).
        2. Run bishop_simplified — skip if driving sum ≤ 0.
        3. Record FoS; track the global minimum.

    The 2-D output grid fos_grid[j][i] stores the minimum FoS found
    at (cx_i, cy_j) over all R values.  This is the standard heatmap
    representation used in slope stability software.

Soil assignment modes (Sprint 3):
    Homogeneous: pass ``soil`` (single Soil) — original behaviour.
    Multi-layer:  pass ``stratigraphy`` (Stratigraphy) — each slice queries
                  the layer at its base depth.  ``soil`` is ignored when
                  ``stratigraphy`` is provided.

Reference:
    Craig's Soil Mechanics, 9th ed., §9.5 – Location of Critical Circle.
    Craig §9.4 – Layered slope stability (multi-layer soil assignment).
    Eurocode 7 – EN 1997-1:2004, §11.5.1 (search for critical surface).

Sign conventions:
    x positive right, y positive up (consistent with geometry.py / slicer.py).
    A valid circle must have its centre above the slope so that the lower
    arc intersects the slope and creates a clockwise-rotating mass.

Units:
    All lengths in metres (m).  FoS is dimensionless.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from models.geometry        import SlopeGeometry, SlipCircle
from models.soil            import Soil
from core.slicer            import create_slices
from core.limit_equilibrium import bishop_simplified, FoSResult

if TYPE_CHECKING:
    from models.stratigraphy import Stratigraphy
    from core.seepage import PhreaticSurface


# ============================================================
#  Constants
# ============================================================

_INF = float("inf")   # sentinel for invalid / untested circles


# ============================================================
#  Result container
# ============================================================

@dataclass
class SearchResult:
    """
    Complete output from a critical circle search.

    Attributes
    ----------
    critical_circle   : SlipCircle with the lowest FoS found.
    fos_min           : Minimum Factor of Safety (–).
    best_fos_result   : Full FoSResult for the critical circle (slice table,
                        convergence info, EC7 flags, etc.)
    fos_grid          : 2-D grid [i_cy][i_cx] of minimum FoS over all R
                        values at each (cx, cy) node.  inf = no valid circle
                        at that node.  Shape: (n_cy, n_cx).
    cx_values         : List of cx search nodes (m).
    cy_values         : List of cy search nodes (m).
    cx_range          : (cx_min, cx_max) bounds used.
    cy_range          : (cy_min, cy_max) bounds used.
    r_range           : (r_min,  r_max)  bounds used.
    n_circles_tested  : Total (cx, cy, R) combinations attempted.
    n_valid           : Circles that produced a valid, convergent FoS.
    method            : Search algorithm identifier string.
    ru                : Pore pressure ratio used.
    warnings          : List of non-fatal warnings collected during search.
    """
    critical_circle  : SlipCircle
    fos_min          : float
    best_fos_result  : FoSResult
    fos_grid         : list[list[float]]
    cx_values        : list[float]
    cy_values        : list[float]
    cx_range         : tuple[float, float]
    cy_range         : tuple[float, float]
    r_range          : tuple[float, float]
    n_circles_tested : int
    n_valid          : int
    method           : str
    ru               : float
    warnings         : list[str] = field(default_factory=list)

    def summary(self) -> str:
        """Human-readable search summary."""
        valid_pct = 100.0 * self.n_valid / max(self.n_circles_tested, 1)
        lines = [
            f"{'═'*58}",
            f"  Critical Circle Search  [{self.method}]",
            f"{'─'*58}",
            f"  FoS (min)       : {self.fos_min:.4f}",
            f"  Critical centre : ({self.critical_circle.cx:.2f}, "
                                  f"{self.critical_circle.cy:.2f}) m",
            f"  Critical radius : {self.critical_circle.r:.2f} m",
            f"  Grid size       : {len(self.cx_values)} cx × "
                                  f"{len(self.cy_values)} cy × "
                                  f"{self.n_circles_tested // max(len(self.cx_values)*len(self.cy_values),1)} R",
            f"  Circles tested  : {self.n_circles_tested}  "
                                  f"({valid_pct:.1f}% valid)",
            f"  rᵤ              : {self.ru:.3f}",
            f"{'─'*58}",
            f"  EC7 Stable : "
                f"{'✅ YES  (FoS ≥ 1.00)' if self.fos_min >= 1.00 else '❌ NO   (COLLAPSE)'}",
            f"  EC7 Pass   : "
                f"{'✅ YES  (FoS ≥ 1.25)' if self.fos_min >= 1.25 else '⚠️  NO   (BELOW EC7 THRESHOLD)'}",
        ]
        if self.warnings:
            lines.append(f"  ⚠️  {len(self.warnings)} warning(s) — see .warnings list")
        lines.append(f"{'═'*58}")
        return "\n".join(lines)


# ============================================================
#  Internal helpers
# ============================================================

def _auto_bounds(
    slope: SlopeGeometry,
) -> tuple[
    tuple[float, float],
    tuple[float, float],
    tuple[float, float],
]:
    """
    Derives conservative default search bounds from slope geometry.

    Strategy (Craig §9.5 / standard practice):
        cx : from slightly left of crest to right of slope toe — centres
             placed too far right produce counter-clockwise rotation and
             negative driving sums, so the right bound is capped at x_max.
        cy : from the crest elevation up to 2× the slope height above
             it — circle centres must be above the slip mass.
        R  : from 0.5× to 2.5× the slope height — small R produces
             shallow failures; large R produces deep-seated failures.

    :param slope: SlopeGeometry instance.
    :return:      Tuple of ((cx_min, cx_max), (cy_min, cy_max), (r_min, r_max)).
    """
    xs = [p[0] for p in slope.points]
    ys = [p[1] for p in slope.points]

    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)

    H = y_max - y_min          # slope height
    L = x_max - x_min          # horizontal extent
    H_eff = max(H, L * 0.1)    # guard against near-flat slopes

    # cx: sweep from just left of crest to the midpoint of the slope plan.
    # Keeping cx left of centre ensures the failure mass (to the right of cx)
    # is large enough to produce a positive driving sum.
    cx_min = x_min - 0.10 * L
    cx_max = x_min + 0.50 * L

    # cy: circle centres must be meaningfully ABOVE the slope crest so that
    # the lower arc creates a proper deep-seated failure surface.
    # Starting at y_max + 0.5*H avoids degenerate near-surface circles.
    cy_min = y_max + 0.50 * H_eff
    cy_max = y_max + 3.00 * H_eff

    # R: half-height to generous deep-seated radius
    r_min = 0.5 * H_eff
    r_max = 3.0 * H_eff

    return (cx_min, cx_max), (cy_min, cy_max), (r_min, r_max)


def _evaluate_circle(
    slope:             SlopeGeometry,
    circle:            SlipCircle,
    soil:              "Soil | None",
    ru:                float,
    num_slices:        int,
    stratigraphy:      "Stratigraphy | None" = None,
    phreatic_surface:  "PhreaticSurface | None" = None,
) -> float | None:
    """
    Attempts a Bishop analysis for one trial circle.

    Returns the FoS (float) on success, or None if the circle is
    geometrically invalid for this slope (no sliding mass, negative
    driving sum, non-convergent).  Silently swallows expected failures
    so the grid search can keep running.

    :param slope:             SlopeGeometry instance.
    :param circle:            Trial SlipCircle.
    :param soil:              Soil properties (uniform; ignored if stratigraphy given).
    :param ru:                Scalar pore pressure ratio (fallback if phreatic_surface=None).
    :param num_slices:        Number of slices to use.
    :param stratigraphy:      Optional multi-layer Stratigraphy (Sprint 3).
    :param phreatic_surface:  Optional PhreaticSurface for variable u (Sprint 9).
    :return:                  FoS (float) or None.

    Reference:
        Bishop & Morgenstern (1960) — variable pore pressure in slope analysis.
    """
    try:
        slices = create_slices(
            slope, circle,
            soil=soil,
            num_slices=num_slices,
            stratigraphy=stratigraphy,
            phreatic_surface=phreatic_surface,
        )
        if len(slices) < 3:
            return None
        # When phreatic_surface is set, slices carry .u values → pass ru=0.0
        _ru = 0.0 if phreatic_surface is not None else ru
        result = bishop_simplified(slices, ru=_ru)
        if not result.converged:
            return None
        if result.fos <= 0:
            return None
        return result.fos
    except (ValueError, ZeroDivisionError):
        return None


# ============================================================
#  Public API
# ============================================================

def grid_search(
    slope:        SlopeGeometry,
    soil:         "Soil | None"         = None,
    ru:               float                  = 0.0,
    cx_range:         tuple[float, float] | None = None,
    cy_range:         tuple[float, float] | None = None,
    r_range:          tuple[float, float] | None = None,
    n_cx:             int   = 10,
    n_cy:             int   = 10,
    n_r:              int   = 5,
    num_slices:       int   = 20,
    verbose:          bool  = False,
    stratigraphy:     "Stratigraphy | None"     = None,
    phreatic_surface: "PhreaticSurface | None"  = None,
) -> SearchResult:
    """
    Grid search for the critical slip circle (minimum FoS).

    Sweeps an (n_cx × n_cy × n_r) grid of trial circles.  For each
    (cx, cy) node the minimum FoS over all R values is stored in
    fos_grid[j][i] (i=cx index, j=cy index).

    Default search bounds are auto-derived from the slope geometry if
    not supplied.  Override any or all of cx_range / cy_range / r_range
    to narrow the search around a known region of interest.

    Soil assignment (Sprint 3 — Craig §9.4):
        Pass ``soil`` for homogeneous slopes (original behaviour).
        Pass ``stratigraphy`` for layered slopes; ``soil`` is then ignored
        and each slice queries the Stratigraphy at its base depth.
        If only ``soil`` is supplied (legacy call), behaviour is unchanged.

    Pore pressure (Sprint 9 — Bishop & Morgenstern 1960):
        Pass ``phreatic_surface`` (PhreaticSurface) for spatially variable pore
        pressures.  Each slice receives u_i = γ_w × max(0, y_ph(x_i) − y_circ).
        If ``phreatic_surface`` is None, the scalar ``ru`` is used (default).
        The two modes are mutually exclusive; ``phreatic_surface`` takes priority.

    Recommended grid sizes:
        Coarse (quick feasibility check): n_cx=8,  n_cy=8,  n_r=4
        Standard (design):                n_cx=15, n_cy=15, n_r=6
        Fine (critical circle reporting): n_cx=25, n_cy=25, n_r=8

    :param slope:             Ground surface geometry (SlopeGeometry).
    :param soil:              Uniform soil (Soil). Ignored if stratigraphy given.
    :param ru:                Scalar pore pressure ratio rᵤ (default 0.0).
                              Used only when phreatic_surface is None.
    :param cx_range:          (cx_min, cx_max) search bounds in metres.
    :param cy_range:          (cy_min, cy_max) search bounds in metres.
    :param r_range:           (r_min, r_max) search bounds in metres.
    :param n_cx:              Grid points along cx axis (default 10).
    :param n_cy:              Grid points along cy axis (default 10).
    :param n_r:               Grid points along R  axis (default 5).
    :param num_slices:        Slices per circle evaluation (default 20).
    :param verbose:           Print progress every 10% if True.
    :param stratigraphy:      Multi-layer Stratigraphy (optional; Sprint 3).
    :param phreatic_surface:  Spatially variable pore pressure surface
                              (optional; Sprint 9). Overrides scalar ru.
    :return:                  SearchResult with critical circle and full FoS grid.
    :raises ValueError:       If grid parameters are invalid, or if no valid
                              circle is found in the entire search domain.

    Reference:
        Bishop & Morgenstern (1960) — variable pore pressure in slope analysis.
        Craig §9.5 — critical circle search procedure.
    """
    # ── Validate soil / stratigraphy ──────────────────────────────────────
    if stratigraphy is None and soil is None:
        raise ValueError(
            "Provide either 'soil' (uniform) or 'stratigraphy' (multi-layer)."
        )

    # ── Validate parameters ───────────────────────────────────────────────
    if n_cx < 2 or n_cy < 2 or n_r < 1:
        raise ValueError(
            f"Grid dimensions must be n_cx≥2, n_cy≥2, n_r≥1.  "
            f"Got n_cx={n_cx}, n_cy={n_cy}, n_r={n_r}."
        )
    # Only validate ru when phreatic_surface is not provided
    if phreatic_surface is None and not (0.0 <= ru < 1.0):
        raise ValueError(f"rᵤ must be in [0, 1), got {ru}")
    if num_slices < 5:
        raise ValueError(f"num_slices must be ≥ 5 for a reliable search, got {num_slices}")

    # ── Resolve bounds (auto or user-supplied) ────────────────────────────
    auto_cx, auto_cy, auto_r = _auto_bounds(slope)
    cx_lo, cx_hi = cx_range if cx_range is not None else auto_cx
    cy_lo, cy_hi = cy_range if cy_range is not None else auto_cy
    r_lo,  r_hi  = r_range  if r_range  is not None else auto_r

    if cx_lo >= cx_hi:
        raise ValueError(f"cx_range: min ({cx_lo}) must be < max ({cx_hi})")
    if cy_lo >= cy_hi:
        raise ValueError(f"cy_range: min ({cy_lo}) must be < max ({cy_hi})")
    if r_lo <= 0 or r_lo >= r_hi:
        raise ValueError(f"r_range: must have 0 < r_min ({r_lo}) < r_max ({r_hi})")

    # ── Build coordinate arrays ────────────────────────────────────────────
    def _linspace(lo: float, hi: float, n: int) -> list[float]:
        if n == 1:
            return [(lo + hi) / 2.0]
        step = (hi - lo) / (n - 1)
        return [lo + i * step for i in range(n)]

    cx_vals = _linspace(cx_lo, cx_hi, n_cx)
    cy_vals = _linspace(cy_lo, cy_hi, n_cy)
    r_vals  = _linspace(r_lo,  r_hi,  n_r)

    # ── Initialise output grid: fos_grid[j][i] = min FoS over R ──────────
    fos_grid: list[list[float]] = [
        [_INF] * n_cx for _ in range(n_cy)
    ]

    best_fos      : float            = _INF
    best_circle   : SlipCircle | None = None
    best_fos_result: FoSResult | None = None

    n_tested = 0
    n_valid  = 0
    warnings : list[str] = []

    total = n_cx * n_cy * n_r

    # ── Grid sweep ────────────────────────────────────────────────────────
    for j, cy in enumerate(cy_vals):
        for i, cx in enumerate(cx_vals):
            for k, r in enumerate(r_vals):
                n_tested += 1

                if verbose and n_tested % max(1, total // 10) == 0:
                    pct = 100.0 * n_tested / total
                    print(f"  [search] {pct:5.1f}%  tested={n_tested}  "
                          f"valid={n_valid}  best FoS={best_fos:.4f}")

                if r <= 0:
                    continue

                try:
                    circle = SlipCircle(cx, cy, r)
                except ValueError:
                    continue

                fos = _evaluate_circle(
                    slope, circle, soil, ru, num_slices,
                    stratigraphy=stratigraphy,
                    phreatic_surface=phreatic_surface,
                )

                if fos is None:
                    continue

                n_valid += 1

                if fos < fos_grid[j][i]:
                    fos_grid[j][i] = fos

                if fos < best_fos:
                    best_fos    = fos
                    best_circle = circle

    # ── Require at least one valid result ─────────────────────────────────
    if best_circle is None or math.isinf(best_fos):
        raise ValueError(
            f"No valid slip circle was found in the search domain.\n"
            f"  cx ∈ [{cx_lo:.2f}, {cx_hi:.2f}]  n={n_cx}\n"
            f"  cy ∈ [{cy_lo:.2f}, {cy_hi:.2f}]  n={n_cy}\n"
            f"  R  ∈ [{r_lo:.2f},  {r_hi:.2f}]  n={n_r}\n"
            f"Suggestions: widen the search bounds, increase n_cx/n_cy/n_r, "
            f"or check that the slope geometry is correct."
        )

    # ── Re-run Bishop on critical circle to capture full FoSResult ────────
    try:
        critical_slices = create_slices(
            slope, best_circle,
            soil=soil, num_slices=num_slices,
            stratigraphy=stratigraphy,
            phreatic_surface=phreatic_surface,
        )
        _ru_final = 0.0 if phreatic_surface is not None else ru
        best_fos_result = bishop_simplified(critical_slices, ru=_ru_final)
    except ValueError as exc:
        warnings.append(
            f"Re-evaluation of critical circle failed: {exc}.  "
            "FoSResult will be empty."
        )
        best_fos_result = None  # type: ignore[assignment]

    if verbose:
        print(f"\n  [search] Complete — {n_tested} circles, "
              f"{n_valid} valid, best FoS = {best_fos:.4f}")

    return SearchResult(
        critical_circle   = best_circle,
        fos_min           = best_fos,
        best_fos_result   = best_fos_result,
        fos_grid          = fos_grid,
        cx_values         = cx_vals,
        cy_values         = cy_vals,
        cx_range          = (cx_lo, cx_hi),
        cy_range          = (cy_lo, cy_hi),
        r_range           = (r_lo,  r_hi),
        n_circles_tested  = n_tested,
        n_valid           = n_valid,
        method            = f"Grid ({n_cx}×{n_cy}×{n_r})",
        ru                = ru,
        warnings          = warnings,
    )


# ============================================================
#  Convenience re-search helper
# ============================================================

def refine_search(
    result:       SearchResult,
    slope:        SlopeGeometry,
    soil:         "Soil | None"         = None,
    zoom:         float                  = 0.3,
    n_cx:         int   = 12,
    n_cy:         int   = 12,
    n_r:          int   = 6,
    num_slices:   int   = 20,
    verbose:      bool  = False,
    stratigraphy: "Stratigraphy | None" = None,
) -> SearchResult:
    """
    Refines a coarse grid result by zooming in around the critical circle.

    Constructs a tighter search box centred on the best (cx, cy, R) found
    in *result*, then calls grid_search() within that box.  Useful for
    two-pass workflows:
        1. Coarse sweep (n=8) to locate the region of minimum FoS.
        2. Fine refine  (n=12) to pin-point the critical circle precisely.

    :param result:       SearchResult from a previous grid_search call.
    :param slope:        Same SlopeGeometry used in the original search.
    :param soil:         Same Soil used in the original search (or None if
                         stratigraphy was used).
    :param zoom:         Half-width of refined box as a fraction of the
                         original range (default 0.3 = ±30% of original span).
    :param n_cx:         Grid points in refined cx sweep.
    :param n_cy:         Grid points in refined cy sweep.
    :param n_r:          Grid points in refined R  sweep.
    :param num_slices:   Slices per evaluation.
    :param verbose:      Print progress if True.
    :param stratigraphy: Multi-layer Stratigraphy (pass same as original search).
    :return:             New SearchResult for the refined domain.
    """
    if not (0.0 < zoom <= 1.0):
        raise ValueError(f"zoom must be in (0, 1], got {zoom}")

    cx_best = result.critical_circle.cx
    cy_best = result.critical_circle.cy
    r_best  = result.critical_circle.r

    cx_span = (result.cx_range[1] - result.cx_range[0]) * zoom
    cy_span = (result.cy_range[1] - result.cy_range[0]) * zoom
    r_span  = (result.r_range[1]  - result.r_range[0])  * zoom

    cx_range = (cx_best - cx_span, cx_best + cx_span)
    cy_range = (cy_best - cy_span, cy_best + cy_span)
    r_range  = (max(0.1, r_best - r_span), r_best + r_span)

    return grid_search(
        slope        = slope,
        soil         = soil,
        ru           = result.ru,
        cx_range     = cx_range,
        cy_range     = cy_range,
        r_range      = r_range,
        n_cx         = n_cx,
        n_cy         = n_cy,
        n_r          = n_r,
        num_slices   = num_slices,
        verbose      = verbose,
        stratigraphy = stratigraphy,
    )
