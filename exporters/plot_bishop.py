"""
plot_bishop.py -- FoS grid heatmap from a Bishop/Ordinary circle search.

Renders a 2-D colour contour map of FoS values over the (cx, cy) search grid,
with the critical circle marked.  Intended for QA/audit purposes so engineers
can verify the search converged and did not miss a lower FoS.

Reference:
    Bishop, A.W. (1955) -- critical circle location methodology.
    Craig's Soil Mechanics, 9th ed., Chapter 9 (FoS contour plots).

Axes:
    x -- circle centre x-coordinate (m)
    y -- circle centre y-coordinate (m)
    colour -- FoS value at each (cx, cy) point

Units:
    All spatial inputs in metres (m).  FoS dimensionless.
"""

import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from models.geometry        import SlopeGeometry, SlipCircle
from models.soil            import Soil
from core.search            import SearchResult, grid_search


def plot_fos_heatmap(
    slope       : SlopeGeometry,
    soil        : Soil,
    result      : SearchResult,
    ru          : float = 0.0,
    n_cx        : int   = 30,
    n_cy        : int   = 25,
    title       : str   = "FoS Heatmap — Bishop Simplified",
    figsize     : tuple = (10, 7),
    fos_clip    : float = 3.0,
) -> plt.Figure:
    """
    Renders a FoS heatmap over the cx-cy search grid used by grid_search().

    Recomputes FoS over a uniform (cx, cy) grid centred on the critical circle
    from ``result``.  The grid spans ±radius around the critical centre so that
    the minimum is always visible.

    :param slope:     SlopeGeometry defining the ground surface.
    :param soil:      Soil used for the stability analysis.
    :param result:    SearchResult containing the critical circle.
    :param ru:        Pore pressure ratio (dimensionless).
    :param n_cx:      Number of grid points in the cx direction.
    :param n_cy:      Number of grid points in the cy direction.
    :param title:     Figure title.
    :param figsize:   Figure size (width, height) in inches.
    :param fos_clip:  Maximum FoS value shown (higher values clipped for contrast).
    :return:          matplotlib Figure.
    """
    from core.limit_equilibrium import bishop_simplified
    from core.slicer            import create_slices

    crit   = result.critical_circle
    r_span = crit.r

    cx_min = crit.cx - r_span * 0.8
    cx_max = crit.cx + r_span * 0.8
    cy_min = crit.cy - r_span * 0.6
    cy_max = crit.cy + r_span * 0.6

    cx_vals = np.linspace(cx_min, cx_max, n_cx)
    cy_vals = np.linspace(cy_min, cy_max, n_cy)

    fos_grid = np.full((n_cy, n_cx), np.nan)

    for i, cy in enumerate(cy_vals):
        for j, cx in enumerate(cx_vals):
            r = math.hypot(crit.cx - cx, crit.cy - cy)
            r = max(r, crit.r * 0.5)   # keep radius reasonable
            # Use critical radius offset from each point
            r_try = crit.r
            circ = SlipCircle(cx, cy, r_try)
            try:
                slices = create_slices(slope, circ, n_slices=20)
                if len(slices) < 3:
                    continue
                res = bishop_simplified(slices, soil.phi_d(), soil.c_d(), ru=ru)
                fos_grid[i, j] = min(res.fos, fos_clip)
            except Exception:
                pass

    fig, ax = plt.subplots(figsize=figsize)

    CX, CY = np.meshgrid(cx_vals, cy_vals)
    masked = np.ma.masked_invalid(fos_grid)

    levels = np.linspace(max(0.5, float(np.nanmin(fos_grid)) * 0.9 if not np.all(np.isnan(fos_grid)) else 0.5),
                         fos_clip, 20)
    cf = ax.contourf(CX, CY, masked, levels=levels, cmap="RdYlGn", extend="both")
    cs = ax.contour( CX, CY, masked, levels=levels, colors="black", linewidths=0.3, alpha=0.4)
    ax.clabel(cs, levels[::4], inline=True, fontsize=7, fmt="%.2f")

    cbar = fig.colorbar(cf, ax=ax, label="Factor of Safety (FoS)")
    cbar.ax.tick_params(labelsize=8)

    # Mark critical circle centre
    ax.plot(crit.cx, crit.cy, "r*", markersize=14, zorder=5,
            label=f"Critical: FoS={result.best_fos_result.fos:.4f}")
    ax.plot(crit.cx, crit.cy, "k+", markersize=8, markeredgewidth=1.5, zorder=6)

    # FoS=1.0 contour highlighted
    try:
        cs1 = ax.contour(CX, CY, masked, levels=[1.0],
                         colors="red", linewidths=1.5, linestyles="--")
        ax.clabel(cs1, fmt="FoS=1.0", fontsize=8)
    except Exception:
        pass

    ax.set_xlabel("Circle centre x (m)", fontsize=9)
    ax.set_ylabel("Circle centre y (m)", fontsize=9)
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.legend(loc="upper right", fontsize=8)
    ax.tick_params(labelsize=8)
    ax.set_aspect("equal")
    fig.tight_layout()
    return fig


def save_fos_heatmap(
    slope       : SlopeGeometry,
    soil        : Soil,
    result      : SearchResult,
    filepath    : str,
    title       : str = "FoS Heatmap — Bishop Simplified",
    dpi         : int = 150,
    **kwargs,
) -> None:
    """
    Convenience wrapper: renders FoS heatmap and saves to a file.

    :param slope:    SlopeGeometry.
    :param soil:     Soil object.
    :param result:   SearchResult (critical circle).
    :param filepath: Output path (PNG, PDF, SVG etc.).
    :param title:    Figure title.
    :param dpi:      Resolution.
    :param kwargs:   Passed to plot_fos_heatmap().
    """
    fig = plot_fos_heatmap(slope, soil, result, title=title, **kwargs)
    fig.savefig(filepath, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
