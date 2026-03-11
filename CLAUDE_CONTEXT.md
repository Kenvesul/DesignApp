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
from core.seepage import PhreaticSurface          # NOT: from seepage import ...
from exporters.report_pdf import generate_slope_report
from exporters.plot_wall import plot_retaining_wall

# ❌ WRONG — bare imports break when run as package
from soil import Soil
from seepage import PhreaticSurface
from report_pdf import generate_slope_report
```

---

## 4. Full File Inventory (v2.0, 100 files)

```
DesignApp/
├── api.py                            ← PUBLIC BRIDGE
├── README.md
├── LICENSE
├── CONTRIBUTING.md
├── CLAUDE_CONTEXT.md                 ← THIS FILE
├── requirements.txt
├── requirements-dev.txt
├── .gitignore
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── playwright.config.js
│
├── core/  (14 modules)
│   ├── bearing_capacity.py           Hansen/Meyerhof Nq,Nc,Nγ — EC7 §6.5.2
│   ├── boussinesq.py                 Stress distribution — Boussinesq (1885)
│   ├── factors_of_safety.py          EC7 DA1/DA2/DA3 partial factors
│   ├── foundation_check.py           SLS + ULS foundation checks
│   ├── limit_equilibrium.py          Bishop simplified + Spencer — Bishop(1955)
│   ├── materials.py                  Concrete/steel grades
│   ├── mechanics.py                  Basic stress/strain helpers
│   ├── pile_capacity.py              EC7 §7 α+β methods + R4 factors
│   ├── rankine_coulomb.py            Ka, Kp — Rankine/Coulomb
│   ├── search.py                     Grid search for critical slip circle
│   ├── seepage.py                    Laplace FD + Dupuit phreatic surface
│   ├── settlement.py                 Immediate + consolidation settlement
│   ├── sheet_pile_analysis.py        Free-earth support + bisection solver
│   ├── slicer.py                     Slice generator (Bishop/Spencer)
│   └── wall_analysis.py              Retaining wall DA1 checks
│
├── models/  (8 models)
│   ├── foundation.py                 Foundation dataclass
│   ├── geometry.py                   SlopeGeometry, SlipCircle
│   ├── pile.py                       Pile, PileSoilLayer dataclasses
│   ├── sheet_pile.py                 SheetPile dataclass
│   ├── soil.py                       Soil dataclass (γ, φ′, c′, cu)
│   ├── stratigraphy.py               Multi-layer soil profile
│   ├── surcharge.py                  Surcharge load types
│   └── wall_geometry.py              Retaining wall geometry
│
├── exporters/  (6 modules)
│   ├── report_pdf.py                 ReportLab stamped calculation sheets
│   ├── report_docx.py                python-docx calculation sheets
│   ├── plot_bishop.py                Bishop slip circle + FoS heatmap
│   ├── plot_foundation.py            Foundation + Boussinesq isobars
│   ├── plot_slope.py                 Slope cross-section
│   └── plot_wall.py                  Wall pressure diagram
│
├── data/
│   ├── ec7.json                      EC7 DA1/DA2/DA3 partial factor tables
│   └── soil_library.json             12 preset soil profiles
│
├── ui/
│   ├── app.py                        Flask routes (v2.0 — 30+ routes)
│   ├── api.py                        Shim re-exporting from root api.py
│   ├── templates/  (10 HTML)         Jinja2 legacy — kept during transition
│   └── static/                       CSS + React build output (dist/)
│
├── react-spa/
│   ├── package.json                  Vite 5 + React 18 + Tailwind CSS 3
│   ├── vite.config.js                Proxy /api/ → Flask :5000
│   ├── tailwind.config.js
│   └── src/
│       ├── App.jsx                   Router + NavBar (6 routes)
│       ├── main.jsx
│       ├── index.css                 Tailwind + component classes
│       ├── hooks/
│       │   └── useSoilLibrary.js     GET /api/soils with module-level cache
│       ├── components/
│       │   ├── ExportBar.jsx         PDF/DOCX/PNG download buttons
│       │   ├── FactorTable.jsx       DA1-C1 vs DA1-C2 comparison table
│       │   ├── InputField.jsx        Labelled input with unit + validation
│       │   ├── LoadingSpinner.jsx    Animated spinner with message
│       │   ├── ResultBadge.jsx       EC7 PASS/FAIL/WARN badge
│       │   └── SoilPicker.jsx        Soil library dropdown
│       └── pages/
│           ├── HomePage.jsx          Landing page + EC7 factor reference
│           ├── SlopePage.jsx         Slope form + Bishop results
│           ├── FoundationPage.jsx    Foundation form + bearing + settlement
│           ├── WallPage.jsx          Wall form + sliding/overturning/bearing
│           ├── PilePage.jsx          Pile form (dynamic layers) + capacity
│           ├── SheetPilePage.jsx     Sheet pile form + free-earth results
│           └── ProjectDashboard.jsx  Session summary + unified PDF export
│
├── tests/  (20 suites)
│   ├── test_bearing_capacity.py
│   ├── test_factors_of_safety.py
│   ├── test_foundation_check.py
│   ├── test_limit_equilibrium.py
│   ├── test_pile.py
│   ├── test_pile_api.py
│   ├── test_rankine_coulomb.py
│   ├── test_search.py                Craig Ex.9.1 — FoS=1.441
│   ├── test_seepage.py
│   ├── test_settlement.py
│   ├── test_sheet_pile.py            Craig Ex.12.1 — <0.002%
│   ├── test_slicer.py
│   ├── test_sprint3.py ... test_sprint9.py
│   ├── test_stratigraphy.py
│   ├── test_wall_analysis.py
│   ├── test_exporters.py
│   ├── test_data_layer.py
│   ├── test_report_docx.py
│   ├── test_api.py
│   ├── test_app.py                   15 Flask route tests
│   └── e2e/
│       └── test_app.spec.js          Playwright E2E (11 tests)
│
└── deploy/
    └── nginx.conf                    Production Nginx reverse proxy
```

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

These are the items to fix in the **Polish Phase** (after git upload):

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
| P-10 | `tests/e2e/` | Playwright tests require Flask + Vite running — no CI config yet | HIGH |

---

## 7. Git Preparation Checklist

Before the first `git push`:
- [ ] Run all 20 test suites: `for f in tests/test_*.py; do python $f; done`
- [ ] Remove any `.env` files (only `.env.example` should be committed)
- [ ] Verify `ui/static/dist/` is in `.gitignore` (or build and commit for deploy)
- [ ] Add `react-spa/node_modules/` to `.gitignore` ✅ already done
- [ ] Set `DESIGNAPP_SECRET` in production environment
- [ ] Review `LICENSE` — update copyright holder name
- [ ] Create GitHub repo → `git remote add origin https://github.com/your-org/DesignApp.git`

---

## 8. Next Session Suggested Starting Point

Start each session by running the test suite to confirm a clean baseline:

```bash
cd DesignApp/
python tests/test_app.py          # Flask route tests (quickest — 15 tests)
python tests/test_sheet_pile.py   # Craig Ex.12.1 calibration
python tests/test_search.py       # Craig Ex.9.1 slope calibration
```

All three should pass in under 60 seconds. If any fail, investigate before making changes.

---

## 9. Polishing Priorities (What to Work on Next)

1. **P-06** — Session size: store only key numbers in session, not full result dict
2. **P-03** — Slope canvas editor: interactive polyline on `<canvas>` in SlopePage.jsx
3. **P-04** — Wall SVG preview: live geometry as inputs change in WallPage.jsx
4. **P-10** — GitHub Actions CI: run all Python tests on push
5. **P-07** — Spencer convergence: add steep-slope test case
6. **P-08** — WCAG audit: run axe-core on each React page

---

## 10. EC7 DA1 Quick Reference

```
DA1-C1 (A1+M1+R1):  γ_φ=1.00  γ_c=1.00  γ_G=1.35  γ_Q=1.50
DA1-C2 (A2+M2+R1):  γ_φ=1.25  γ_c=1.25  γ_G=1.00  γ_Q=1.30
                     γ_cu=1.40 (undrained clay, C2 only)

Design angle:  φ′_d = arctan(tan(φ′_k) / γ_φ)
Design cohesion: c′_d = c′_k / γ_c
Governing combination = whichever gives lower resistance / higher demand
```

---

## 11. Flask API Route Map (v2.0)

```
GET  /                        Home page (also SPA entry)
GET  /api/health              {"status":"ok","version":"2.0","session":{...}}
GET  /api/soils               JSON soil library (12 presets)

POST /api/slope/analyse       → run_slope_analysis()
POST /api/foundation/analyse  → run_foundation_analysis()
POST /api/wall/analyse        → run_wall_analysis()
POST /api/pile/analyse        → run_pile_analysis()
POST /api/sheet-pile/analyse  → run_sheet_pile_analysis()

GET  /api/slope/export/pdf
GET  /api/slope/export/docx
GET  /api/slope/export/png
GET  /api/foundation/export/pdf
GET  /api/foundation/export/docx
GET  /api/foundation/export/png
GET  /api/wall/export/pdf
GET  /api/wall/export/docx
GET  /api/wall/export/png
GET/POST /api/project/export/pdf   Unified multi-analysis PDF

# Legacy Jinja2 routes (kept during React transition):
GET  /slope   GET /foundation   GET /wall   GET /sheet-pile
POST /slope/analyse   POST /foundation/analyse   POST /wall/analyse
GET  /*/export/pdf   GET  /*/export/docx   GET  /*/export/png
GET  /project/export/pdf
```
