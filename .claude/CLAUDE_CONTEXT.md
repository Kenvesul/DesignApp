# CLAUDE_CONTEXT.md — DesignApp AI Session Guide

**Read this file at the start of every new session.**
It tells you exactly where the project is, what rules apply, and what to do next.

---

## 1. Project Identity

| Item | Value |
|---|---|
| App | DesignApp v2.0 — Modular Geotechnical Analysis Suite |
| Standard | Eurocode 7 — EN 1997-1:2004 + UK/TR National Annex |
| Language | Python 3.12 (backend) + React 18 / Vite (frontend) |
| Test status | **20 suites · 552+ checks · 0 failures** |
| Roadmap doc | `DesignApp_Roadmap_v4_0.docx` (see project root) |
| Current phase | **Phase 5 COMPLETE** — React SPA + Polish Phase begins |

---

## 2. Mandatory Architecture Rules

```
models/ → core/ → api.py → ui/app.py
                        ↘ react-spa/ (via /api/* HTTP only)
                ↘ exporters/
```

| Layer | What it contains | Hard rule |
|---|---|---|
| `models/` | Dataclasses: Soil, Geometry, Foundation, Pile, SheetPile… | stdlib only; no imports from core/ |
| `core/` | Math engines: bearing_capacity, limit_equilibrium, pile_capacity… | stdlib + numpy; NO UI, NO reportlab/matplotlib |
| `api.py` | Public bridge — run_*(), export_*(), validate_*() | Accepts/returns plain dicts only |
| `exporters/` | report_pdf, report_docx, plot_* | matplotlib + reportlab; NO Flask |
| `ui/app.py` | Flask routes | Imports ONLY from `from . import api` (ui/api.py shim) |
| `react-spa/` | React components, hooks, pages | Calls ONLY `/api/*` endpoints; NEVER imports Python |

**Violating any of these is a blocking error.**

---

## 3. Import Style — ALWAYS Use Full Package Paths

```python
# ✅ CORRECT
from models.soil import Soil
from core.bearing_capacity import bearing_capacity_hansen
from core.seepage import PhreaticSurface
from exporters.report_pdf import generate_slope_report
from exporters.plot_wall import plot_retaining_wall

# ❌ WRONG — bare imports break when run as package
from soil import Soil
from seepage import PhreaticSurface
from report_pdf import generate_slope_report
```

---

## 4. Full File Inventory (v2.0, 100 files)

See project root `README.md` for the full tree.

---

## 5. Calibration Values — Never Break These

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

## 6. Known Issues / Polish Backlog

| ID | File | Issue | Priority |
|---|---|---|---|
| P-01 | `core/seepage.py` | Convergence uses fixed iteration count; no residual-based stopping | LOW |
| P-02 | `exporters/plot_foundation.py` | Aspect ratio distortion on non-square figures | LOW |
| P-03 | `react-spa/src/pages/SlopePage.jsx` | No canvas polyline editor for slope profile — textarea only | MEDIUM |
| P-04 | `react-spa/src/pages/WallPage.jsx` | No live SVG geometry preview | MEDIUM |
| P-05 | All React pages | No dark mode toggle wired (CSS vars ready, toggle button missing) | LOW |
| P-06 | `ui/app.py` | Session size can exceed Flask cookie limit for large slope results | MEDIUM |
| P-07 | `core/limit_equilibrium.py` | Spencer method convergence not tested for very steep slopes (>45°) | MEDIUM |
| P-08 | All | WCAG 2.1 AA accessibility audit not complete | MEDIUM |
| P-09 | `react-spa/` | Mobile layout not tested below 768px | LOW |
| P-10 | `tests/e2e/` | Playwright tests require Flask + Vite running — no CI config yet | ✅ FIXED — see .github/workflows/ci.yml |

---

## 7. Next Session Suggested Starting Point

```bash
cd DesignApp/
python tests/test_app.py          # Flask route tests (15 tests)
python tests/test_sheet_pile.py   # Craig Ex.12.1 calibration
python tests/test_search.py       # Craig Ex.9.1 slope calibration
```

---

## 8. Polishing Priorities (What to Work on Next)

1. **P-06** — Session size: store only key numbers in session, not full result dict
2. **P-03** — Slope canvas editor: interactive polyline on `<canvas>` in SlopePage.jsx
3. **P-04** — Wall SVG preview: live geometry as inputs change in WallPage.jsx
4. **P-07** — Spencer convergence: add steep-slope test case
5. **P-08** — WCAG audit: run axe-core on each React page

---

## 9. EC7 DA1 Quick Reference

```
DA1-C1 (A1+M1+R1):  γ_φ=1.00  γ_c=1.00  γ_G=1.35  γ_Q=1.50
DA1-C2 (A2+M2+R1):  γ_φ=1.25  γ_c=1.25  γ_G=1.00  γ_Q=1.30
                     γ_cu=1.40 (undrained clay, C2 only)

Design angle:    φ′_d = arctan(tan(φ′_k) / γ_φ)
Design cohesion: c′_d = c′_k / γ_c
Governing combination = whichever gives lower resistance / higher demand
```

---

## 10. Flask API Route Map (v2.0)

```
GET  /api/health
GET  /api/soils

POST /api/slope/analyse
POST /api/foundation/analyse
POST /api/wall/analyse
POST /api/pile/analyse
POST /api/sheet-pile/analyse

GET  /api/*/export/pdf
GET  /api/*/export/docx
GET  /api/*/export/png
GET/POST /api/project/export/pdf
```
