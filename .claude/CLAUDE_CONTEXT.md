# CLAUDE_CONTEXT.md — DesignApp AI Session Guide
**Version:** 3.0 | **Updated:** 2026-03-25
**Read this file at the start of every new session.**

---

## 1. Project Identity

| Item | Value |
|---|---|
| App | DesignApp v2.0 → v3.0 (in progress) |
| Standard | Eurocode 7 — EN 1997-1:2004 + UK/TR National Annex |
| Backend | Python 3.12 — math engine + Flask API |
| Web UI | React 18 / Vite (existing, maintained) |
| Desktop UI | **PySide6** (NEW — Phase 6 target) |
| Test status | **20 suites · 552+ checks · 0 failures · 18/18 E2E ✅** |
| CI | GitHub Actions — `.github/workflows/ci.yml` ✅ |
| Current phase | **Phase 6 begins** — Bug fixes + PySide6 Desktop UI |

---

## 2. Architecture — THREE valid entry points

```
models/ → core/ → api.py ──→ ui/app.py (Flask)  ──→ react-spa/ (browser)
                        ╰──→ desktop/app.py (PySide6)  ← NEW Phase 6
                        ╰──→ exporters/ (PDF/DOCX/PNG)
```

### Hard rules per layer

| Layer | Rule |
|---|---|
| `models/` | stdlib only; NO imports from core/ |
| `core/` | stdlib + numpy only; NO UI, NO reportlab, NO Qt |
| `api.py` | Accepts/returns plain dicts only; NO Flask, NO Qt |
| `exporters/` | matplotlib + reportlab; NO Flask, NO Qt |
| `ui/app.py` | Flask only; imports ONLY `from . import api` |
| `react-spa/` | Calls ONLY `/api/*` endpoints |
| `desktop/` | PySide6 only; imports ONLY `from api import *` — never imports core/ directly |

**The desktop UI must go through api.py exactly like the web UI does.**
This ensures both frontends are always in sync.

---

## 3. Import Style — ALWAYS full package paths

```python
# ✅ CORRECT
from models.soil import Soil
from core.bearing_capacity import bearing_capacity_hansen
from core.seepage import PhreaticSurface
from exporters.report_pdf import generate_slope_report

# ❌ WRONG
from soil import Soil
from seepage import PhreaticSurface
```

---

## 4. Calibration Values — NEVER break these

| Analysis | Value | Tolerance | Source |
|---|---|---|---|
| Slope FoS_k | 1.441 | ±0.005 | Craig Ex.9.1, Bishop, φ=35°, γ=19, ru=0 |
| Sheet pile d (DA1-C2) | 2.1363 m | <0.002% | Craig Ex.12.1, φ=38°, γ=20, h=6m |
| Sheet pile T (DA1-C2) | 54.780 kN/m | <0.002% | Craig Ex.12.1 |
| Sheet pile M (DA1-C2) | 154.221 kN·m/m | <0.002% | Craig Ex.12.1 |
| Sheet pile d (DA1-C1) | 1.5102 m | <0.002% | Craig Ex.12.1 |
| Sheet pile T (DA1-C1) | 38.298 kN/m | <0.002% | Craig Ex.12.1 |
| Sheet pile M (DA1-C1) | 102.445 kN·m/m | <0.002% | Craig Ex.12.1 |
| Foundation q_ult_k | 1010–1050 kPa | ±5% | Hansen, φ=30°, γ=18, B=2m, Df=1m |

---

## 5. Known Bugs — Fix before new features

| ID | Severity | File | Issue | Status |
|---|---|---|---|---|
| BUG-1 | 🔴 HIGH | `ui/app.py` | Session overflow >4KB — export routes return 404 | **OPEN** |
| BUG-2 | 🔴 HIGH | `ui/app.py` | Temp file leak — `/tmp` fills indefinitely on exports | **OPEN** |
| BUG-3 | 🟡 MED | `react-spa/src/pages/SheetPilePage.jsx` | Sends `h_retain` but API expects `h_retained` | **OPEN** |

---

## 6. Polish Backlog

| ID | Priority | File | Issue |
|---|---|---|---|
| P-01 | LOW | `core/seepage.py` | Fixed iteration count; no residual-based stop |
| P-02 | LOW | `exporters/plot_foundation.py` | Aspect ratio distortion on non-square figures |
| P-03 | MED | `react-spa/.../SlopePage.jsx` | No canvas polyline editor — textarea only |
| P-04 | MED | `react-spa/.../WallPage.jsx` | No live SVG geometry preview |
| P-05 | LOW | All React pages | Dark mode toggle wired (CSS vars ready) |
| P-07 | MED | `core/limit_equilibrium.py` | Spencer ValueError not caught in grid search |
| P-08 | MED | `react-spa/src/` | WCAG 2.1 AA audit incomplete |
| P-09 | LOW | `react-spa/` | Mobile layout below 768px untested |

---

## 7. Phase 6 — PySide6 Desktop UI

### Why PySide6?
- HTML graphs have layout/overlap issues reported by user
- Desktop tool → no browser dependency, no Flask server needed
- Matplotlib plots embed natively via `FigureCanvasQTAgg` — same plots as exporters
- `api.py` is called directly (no HTTP) — faster, simpler

### Target file structure
```
desktop/
├── __init__.py
├── app.py                  ← QApplication entry point
├── main_window.py          ← QMainWindow + QTabWidget (6 analysis tabs)
├── widgets/
│   ├── soil_picker.py      ← QComboBox wrapping /api/soils equiv
│   ├── result_badge.py     ← QLabel with green/red stylesheet
│   ├── input_panel.py      ← QFormLayout helper
│   ├── plot_canvas.py      ← FigureCanvasQTAgg wrapper
│   └── export_bar.py       ← PDF/DOCX/PNG QPushButton row
└── pages/
    ├── slope_page.py       ← QWidget for slope analysis
    ├── foundation_page.py
    ├── wall_page.py
    ├── pile_page.py
    ├── sheet_pile_page.py
    └── project_dashboard.py
```

### PySide6 architecture rules
- Each page is a `QWidget` subclass
- Analysis runs in a `QThread` worker — NEVER block the main thread
- Results displayed via `FigureCanvasQTAgg` (matplotlib) embedded in layout
- All data flow goes: `QWidget → api.run_*() → dict → update UI`
- Export buttons call `api.export_*()` directly then `QFileDialog.getSaveFileName()`
- Dark/light mode via Qt palette — no CSS variables needed

### Dependencies to add to requirements.txt
```
PySide6 >= 6.6
matplotlib >= 3.8   # already present
```

---

## 8. Session Start Checklist

```bash
cd DesignApp/
python tests/test_app.py          # Flask route tests (15 tests)
python tests/test_sheet_pile.py   # Craig Ex.12.1 calibration
python tests/test_search.py       # Craig Ex.9.1 slope calibration
```

All three must pass before making changes.

---

## 9. EC7 DA1 Quick Reference

```
DA1-C1 (A1+M1+R1):  γ_φ=1.00  γ_c=1.00  γ_G=1.35  γ_Q=1.50
DA1-C2 (A2+M2+R1):  γ_φ=1.25  γ_c=1.25  γ_G=1.00  γ_Q=1.30
                     γ_cu=1.40 (undrained clay, C2 only)

Design angle:    φ′_d = arctan(tan(φ′_k) / γ_φ)
Design cohesion: c′_d = c′_k / γ_c
Governing = whichever gives lower resistance / higher demand
```

---

## 10. Flask API Route Map (v2.0) — unchanged

```
GET  /api/health
GET  /api/soils
POST /api/slope/analyse        → run_slope_analysis()
POST /api/foundation/analyse   → run_foundation_analysis()
POST /api/wall/analyse         → run_wall_analysis()
POST /api/pile/analyse         → run_pile_analysis()
POST /api/sheet-pile/analyse   → run_sheet_pile_analysis()
GET  /api/*/export/pdf|docx|png
GET/POST /api/project/export/pdf
```

---

## 11. CI Status

| Job | Status |
|---|---|
| Python Tests (20 suites, 552+ checks) | ✅ |
| React Build & Lint | ✅ |
| Docker Build | ✅ |
| Playwright E2E (18/18) | ✅ |

CI workflow: `.github/workflows/ci.yml`
Trigger: push to `main` or `develop`, PR to `main`
