"""
ui/api.py — UI-side shim
========================
Re-exports every public symbol from the root api.py so that ui/app.py can do:

    from . import api
    api.run_slope_analysis(...)

ARCHITECTURE RULE:
    This file may ONLY import from the project-root api.py.
    It must NEVER import from core/ or models/ directly.
"""

from api import (                           # root api.py  ← sole bridge
    # Analysis runners
    run_slope_analysis,
    run_foundation_analysis,
    run_wall_analysis,
    run_pile_analysis,
    run_sheet_pile_analysis,

    # Exporters
    export_pdf,
    export_docx,
    export_slope_plot_png,
    export_heatmap_png,
    export_foundation_pdf,
    export_foundation_docx,
    export_foundation_plot_png,
    export_wall_pdf,
    export_wall_docx,
    export_wall_plot_png,
    export_sheet_pile_pdf,
    export_sheet_pile_docx,
    export_project_pdf,

    # Utilities
    get_soil_library,
    validate_slope_params,
    validate_foundation_params,
    validate_wall_params,
    validate_sheet_pile_params,
)

__all__ = [
    "run_slope_analysis",
    "run_foundation_analysis",
    "run_wall_analysis",
    "run_pile_analysis",
    "run_sheet_pile_analysis",
    "export_pdf",
    "export_docx",
    "export_slope_plot_png",
    "export_heatmap_png",
    "export_foundation_pdf",
    "export_foundation_docx",
    "export_foundation_plot_png",
    "export_wall_pdf",
    "export_wall_docx",
    "export_wall_plot_png",
    "export_sheet_pile_pdf",
    "export_sheet_pile_docx",
    "export_project_pdf",
    "get_soil_library",
    "validate_slope_params",
    "validate_foundation_params",
    "validate_wall_params",
    "validate_sheet_pile_params",
]

# Additional utility functions present in root api.py
from api import (
    get_ec7_factors,
    get_material_grades,
    validate_pile_params,
)
