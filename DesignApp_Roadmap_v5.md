# DesignApp â€” Roadmap v5.0
**Date:** 2026-03-25
**Status:** Phase 5 complete (React SPA + CI) â†’ Phase 6 begins

---

## Phases completed

| Phase | Description | Status |
|---|---|---|
| 1 | Core math engine (bearing, slope, wall, pile, sheet pile) | âœ… |
| 2 | Exporters (PDF, DOCX, PNG) | âœ… |
| 3 | Flask web UI (Jinja2 legacy) | âœ… |
| 4 | React SPA (6 pages, API bridge) | âœ… |
| 5 | CI/CD, E2E tests, polish | âœ… |

---

## Phase 6 â€” Bug Fixes + PySide6 Desktop UI

### Why PySide6 now?
The web UI has known layout issues (overlapping info boxes, HTML graph quality).
A native desktop UI solves these permanently:
- Matplotlib plots embedded at full resolution via `FigureCanvasQTAgg`
- No browser rendering quirks
- No Flask server required for local use
- Native file dialogs for PDF/DOCX export
- Proper form layouts that don't overlap

The web UI (React + Flask) is **kept and maintained** for remote/multi-user access.
PySide6 is an additional entry point â€” both call the same `api.py`.

---

## Sprint A â€” Critical Bug Fixes
**Target: 1â€“2 days | Files: `ui/app.py`, `react-spa/src/pages/SheetPilePage.jsx`, `tests/test_app.py`**

### A-1: Fix temp file leak (BUG-2) ðŸ”´
Add `_send_temp_file()` helper to `ui/app.py`. Replace all 16 `return send_file(path, ...)` calls.
```python
def _send_temp_file(path, download_name, mimetype):
    @flask.after_this_request
    def _cleanup(response):
        try: os.unlink(path)
        except OSError: pass
        return response
    return send_file(path, as_attachment=True,
                     download_name=download_name, mimetype=mimetype)
```

### A-2: Fix session overflow (BUG-1) ðŸ”´
Add `_slim_for_session()` helper. Strip `slices`, `search_cache`, `stem.diagram` before
storing in Flask session. Verify combined session size < 3500 bytes.

### A-3: Fix SheetPilePage field name (BUG-3) ðŸŸ¡
In `SheetPilePage.jsx` `handleSubmit`, change `h_retain: +form.h_retain` â†’
`h_retained: +form.h_retain`. Also add `name="h_retain"` to the `<select>` element
so E2E tests can interact with it properly.

### A-4: Regression tests
Add to `tests/test_app.py`:
- `test_export_tempfile_deleted` â€” verify `/tmp` file is removed after export response
- `test_session_size_within_limit` â€” verify slim session < 3500 bytes for all 4 analyses

---

## Sprint B â€” Spencer & Seepage Polish
**Target: 1 day | Files: `core/limit_equilibrium.py`, `core/search.py`, `core/seepage.py`, `tests/test_sprint3.py`**

### B-1: Spencer steep-slope fix (P-07)
In `core/search.py` grid search, catch `ValueError` per-circle (retrograde geometry)
and skip rather than propagate. Improve error message to be actionable.

### B-2: Add steep-slope test
Add `test_spencer_steep_slope_skips_invalid` to `tests/test_sprint3.py`.
Use 1.2H:1V slope, Ï†=40Â°, c=5 kPa â€” should return a valid FoS without raising.

### B-3: Seepage residual stop (P-01)
Replace fixed iteration count in `core/seepage.py` with `while residual > tol` loop.
Expose `max_iter=500` and `tol=1e-6` as parameters.

---

## Sprint C â€” PySide6 Desktop UI (Phase 6 main deliverable)
**Target: 5â€“7 days | New folder: `desktop/`**

### C-1: Project scaffold
```
desktop/
â”œâ”€â”€ __init__.py
â”œâ”€â”€ app.py                  â† QApplication, sets theme, launches MainWindow
â”œâ”€â”€ main_window.py          â† QMainWindow with QTabWidget (6 tabs + dashboard)
â””â”€â”€ widgets/
    â”œâ”€â”€ plot_canvas.py      â† FigureCanvasQTAgg + NavigationToolbar2QT
    â”œâ”€â”€ result_badge.py     â† QLabel styled green/red/amber
    â”œâ”€â”€ input_panel.py      â† QFormLayout helper (label + unit + QLineEdit)
    â”œâ”€â”€ soil_picker.py      â† QComboBox loading from api.get_soil_library()
    â””â”€â”€ export_bar.py       â† Row of QPushButtons (PDF, DOCX, PNG)
```

### C-2: Analysis pages (one per tab)
Each page is a `QWidget` with:
- Left panel: `QFormLayout` inputs + `SoilPicker` + Run button
- Right panel: `FigureCanvasQTAgg` (embedded matplotlib plot)
- Bottom: `ResultBadge` + DA1 C1/C2 results table (`QTableWidget`)
- Export bar: PDF / DOCX / PNG buttons

Pages to implement:
1. `SlopePage` â€” slope geometry inputs + Bishop slip circle plot
2. `FoundationPage` â€” foundation inputs + Boussinesq isobar plot
3. `WallPage` â€” wall geometry inputs + live SVG-like QPainter preview + pressure diagram
4. `PilePage` â€” pile inputs + layer table (`QTableWidget` dynamic rows)
5. `SheetPilePage` â€” sheet pile inputs + free-earth pressure diagram
6. `ProjectDashboard` â€” session summary + unified PDF export

### C-3: Threading model
```python
class AnalysisWorker(QRunnable):
    def __init__(self, fn, payload, on_result, on_error):
        self.fn = fn
        self.payload = payload
    def run(self):
        try:
            result = self.fn(self.payload)  # calls api.run_*()
            self.on_result.emit(result)
        except Exception as e:
            self.on_error.emit(str(e))
```
All `api.run_*()` calls run in `QThreadPool`. Main thread only updates UI.

### C-4: Dark/light mode
Use `QPalette` to set dark mode system-wide.
Provide toggle in `View` menu. Persist preference to `~/.designapp/prefs.json`.

### C-5: Requirements update
Add to `requirements.txt`:
```
PySide6 >= 6.6
```
Add to `requirements-dev.txt`:
```
pytest-qt >= 4.4   # for desktop UI tests
```

### C-6: Desktop tests
Add `tests/test_desktop_ui.py` using `pytest-qt`:
- `test_slope_page_run_analysis` â€” fill form, click Run, verify result badge appears
- `test_foundation_page_export_pdf` â€” verify PDF file created and non-empty
- `test_calibration_slope_fos` â€” verify FoS = 1.441 Â± 0.005 displayed in UI

---

## Sprint D â€” React UX Polish (web UI catch-up)
**Target: 2â€“3 days | Files: `react-spa/src/pages/`**

### D-1: SlopePage canvas editor (P-03)
Replace textarea with interactive `<canvas>` polyline editor.
Click to add points, drag to move, keyboard Delete to remove.
Keep textarea as hidden fallback for paste input.

### D-2: WallPage SVG preview (P-04)
Add live `<svg>` geometry preview that updates on every `onChange`.
Colour zones: concrete (grey), soil (tan), foundation (brown).

### D-3: Dark mode toggle (P-05)
Wire the toggle button (CSS vars already in `index.css`).
Write `"dark"` class to `<html>` element and persist to `localStorage`.

---

## Sprint E â€” Accessibility & Mobile
**Target: 1 day | Files: `react-spa/src/`**

### E-1: WCAG 2.1 AA audit (P-08)
Run axe-core on all 6 pages. Fix known gaps:
- `ResultBadge`: add `aria-label="Pass"` / `aria-label="Fail"`
- `InputField`: verify every input has explicit `<label htmlFor>`
- Tab order audit on all forms

### E-2: Mobile layout (P-09)
Audit all form grids below 768px. Add `sm:` Tailwind breakpoints where missing.
Test on Chrome DevTools mobile emulation.

---

## Sprint F â€” Low Polish
**Target: 0.5 days**

| Item | File | Change |
|---|---|---|
| P-02 | `exporters/plot_foundation.py` | Add `ax.set_aspect('equal', adjustable='box')` |
| P-01 | `core/seepage.py` | Done in Sprint B |

---

## Sprint G Ã¢â‚¬â€ Slope Search Reliability + Verification
**Target: 2Ã¢â‚¬â€œ4 days | Files: `core/search.py`, `core/limit_equilibrium.py`, `api.py`, `exporters/plot_bishop.py`, `desktop/pages/slope_page.py`, `react-spa/src/pages/SlopePage.jsx`**

### G-1: User-defined search zone
Add explicit search-zone input support for slip-circle search:
- `xc_min`, `xc_max`
- `yc_min`, `yc_max`
- `r_min`, `r_max`
- `n_cx`, `n_cy`, `n_r`

Default values should still be auto-derived from slope geometry, but the engineer must be able to override them.

### G-2: Boundary proximity warning
After the critical circle is found, check whether the circle centre lies within a tolerance band near any search-zone edge.

If yes, return a warning such as:
- `Critical circle center is near the search boundary - expand the zone to confirm the global minimum.`

### G-3: Full result-surface / heatmap support
Return all circle results, or a heatmap-ready representation of them, so the engineer can inspect the FoS landscape and detect edge minima visually.

### G-4: Improve invalid-circle handling
Tighten filtering for:
- boundary-truncated circles
- geometrically invalid circles
- near-zero-driving circles that produce unrealistically large FoS

### G-5: API exposure
Expose through `api.py`:
- `search_zone`
- `boundary_warning`
- search metadata / heatmap-ready data

### G-6: UI follow-up after core validation
Desktop first:
- add search-zone controls and heatmap support to `desktop/pages/slope_page.py`

Web later:
- add the same controls and a static heatmap to `react-spa/src/pages/SlopePage.jsx`

### G-7: Verification tests
Add regression coverage for:
- near-flat safe slope no longer failing
- ordinary stable slope returning physically meaningful FoS
- steep slope skipping invalid circles cleanly
- boundary-adjacent minima raising a warning
- plotted/exported circle matching the accepted critical circle

---

## File change summary

| Sprint | Files |
|---|---|
| A | `ui/app.py` Â· `react-spa/.../SheetPilePage.jsx` Â· `tests/test_app.py` |
| B | `core/limit_equilibrium.py` Â· `core/search.py` Â· `core/seepage.py` Â· `tests/test_sprint3.py` |
| C | `desktop/` (all new) Â· `requirements.txt` Â· `requirements-dev.txt` |
| D | `react-spa/src/pages/SlopePage.jsx` Â· `WallPage.jsx` Â· `App.jsx` Â· `index.css` |
| E | `react-spa/src/components/ResultBadge.jsx` Â· `InputField.jsx` Â· all pages |
| F | `exporters/plot_foundation.py` |
| G | `core/search.py` · `core/limit_equilibrium.py` · `api.py` · `exporters/plot_bishop.py` · `desktop/pages/slope_page.py` · `react-spa/src/pages/SlopePage.jsx` |

---

## Definition of Done for Phase 6

- [ ] BUG-1, BUG-2, BUG-3 fixed and regression tests green
- [ ] PySide6 desktop app launches with `python -m desktop.app`
- [ ] All 6 analysis pages functional with embedded matplotlib plots
- [ ] Export (PDF/DOCX/PNG) works from desktop via native file dialog
- [ ] Dark/light mode toggle working
- [ ] `pytest-qt` tests pass for slope, foundation, calibration
- [ ] All existing 552+ Python tests still green
- [ ] All 18 E2E Playwright tests still green
- [ ] CI pipeline green on push

---

## Calibration values â€” must remain valid throughout all phases

| Check | Value | Tolerance |
|---|---|---|
| Craig Ex.9.1 FoS | 1.441 | Â±0.005 |
| Craig Ex.12.1 d DA1-C2 | 2.1363 m | <0.002% |
| Craig Ex.12.1 T DA1-C2 | 54.780 kN/m | <0.002% |
| Craig Ex.12.1 M DA1-C2 | 154.221 kNÂ·m/m | <0.002% |
| Foundation q_ult_k | 1010â€“1050 kPa | Â±5% |

