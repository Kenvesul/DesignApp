# DesignApp v2.0

**Modular Python Geotechnical Analysis Suite — Eurocode 7 (EN 1997-1:2004)**

[![CI](https://github.com/Kenvesul/DesignApp/actions/workflows/ci.yml/badge.svg)](https://github.com/Kenvesul/DesignApp/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/tests-552%2B%20passing-brightgreen)](https://github.com/Kenvesul/DesignApp/blob/main/tests)
[![EC7](https://img.shields.io/badge/standard-EC7%20EN%201997--1-blue)](https://eurocodes.jrc.ec.europa.eu/)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](https://github.com/Kenvesul/DesignApp/blob/main/LICENSE)

DesignApp performs five core geotechnical analyses following Eurocode 7 Design Approach 1 (DA1), generates stamped PDF/DOCX calculation sheets, and serves results through both a legacy Jinja2 web interface and a modern React SPA.

---

## Analysis Types

| Analysis | Method | EC7 Reference | Calibration |
|---|---|---|---|
| Slope Stability | Bishop Simplified + Spencer | §11, Annex B | Craig Ex.9.1 — FoS=1.441 |
| Foundation Bearing | Hansen + Meyerhof factors | §6.5.2 | q_ult ≈ 1010–1050 kPa |
| Retaining Wall | Rankine/Coulomb, sliding/overturning | §9 | Craig Ch.11 |
| Pile Capacity | α-method (clay), β-method (sand) | §7, R4 | Tomlinson (1970) |
| Sheet Pile | Free-earth support, bisection solver | §9 | Craig Ex.12.1 — <0.002% |

All analyses run **DA1 dual-combination** (C1: A1+M1+R1, C2: A2+M2+R1) as required by EC7 §2.4.7.3.

---

## Quick Start

### Backend (Python)

```bash
# 1. Clone
git clone https://github.com/Kenvesul/DesignApp.git
cd DesignApp

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run Flask app
python -m ui.app
# → http://127.0.0.1:5000
```

### Frontend (React SPA)

```bash
cd react-spa
npm install
npm run dev      # Dev server on :5173 — proxies /api/ to Flask :5000

# Production build:
npm run build    # Outputs to ui/static/dist/
```

### Run All Tests

```bash
cd tests/
python test_bearing_capacity.py
python test_sheet_pile.py
# or run all:
for f in test_*.py; do python $f && echo "PASS: $f" || echo "FAIL: $f"; done
```

---

## Project Structure

```
DesignApp/
├── api.py                    ← Public bridge — ONLY file ui/ imports from
├── core/                     ← Math engines — NO UI imports
│   ├── bearing_capacity.py   ← Hansen/Meyerhof Nq, Nc, Nγ
│   ├── limit_equilibrium.py  ← Bishop simplified + Spencer
│   ├── pile_capacity.py      ← EC7 §7 α+β methods
│   ├── search.py             ← Grid search for critical slip circle
│   ├── seepage.py            ← Laplace FD + Dupuit phreatic surface
│   ├── sheet_pile_analysis.py← Free-earth support + bisection solver
│   ├── slicer.py             ← Slice generator with phreatic surface
│   ├── wall_analysis.py      ← Sliding/overturning/bearing DA1
│   └── ...                   ← (14 modules total)
├── models/                   ← Dataclasses — stdlib only
│   ├── soil.py               ← Soil (γ, φ′, c′, cu)
│   ├── geometry.py           ← SlopeGeometry, SlipCircle
│   └── ...                   ← (8 models total)
├── exporters/                ← PDF/DOCX/PNG — reportlab, python-docx, matplotlib
│   ├── report_pdf.py         ← Stamped calculation sheets
│   ├── report_docx.py        ← Word calculation sheets
│   └── plot_*.py             ← Cross-section + pressure diagram plots
├── ui/
│   ├── app.py                ← Flask routes — imports ONLY from ui/api.py
│   ├── api.py                ← Thin shim re-exporting from root api.py
│   └── templates/            ← Jinja2 HTML (legacy, kept during React transition)
├── react-spa/                ← Vite + React 18 + Tailwind CSS
│   └── src/
│       ├── App.jsx           ← React Router, NavBar
│       ├── pages/            ← SlopePage, FoundationPage, WallPage, PilePage, SheetPilePage, ProjectDashboard
│       ├── components/       ← InputField, SoilPicker, ResultBadge, FactorTable, ExportBar
│       └── hooks/            ← useSoilLibrary
├── data/
│   ├── ec7.json              ← EC7 partial factor tables
│   └── soil_library.json     ← 12 preset soil profiles
├── tests/                    ← 20 test suites, 552+ checks
└── deploy/
    └── nginx.conf            ← Production Nginx config
```

---

## API Endpoints

| Method | Route | Description |
|---|---|---|
| GET | `/api/health` | Health check — version 2.0, session state |
| GET | `/api/soils` | JSON soil library (12 presets) |
| POST | `/api/slope/analyse` | EC7 DA1 slope stability |
| POST | `/api/foundation/analyse` | EC7 DA1 bearing + settlement |
| POST | `/api/wall/analyse` | EC7 DA1 retaining wall |
| POST | `/api/pile/analyse` | EC7 DA1 pile capacity |
| POST | `/api/sheet-pile/analyse` | EC7 DA1 sheet pile free-earth |
| GET | `/api/*/export/pdf` | Download PDF calculation sheet |
| GET | `/api/*/export/docx` | Download Word calculation sheet |
| GET | `/api/*/export/png` | Download cross-section PNG |
| GET/POST | `/api/project/export/pdf` | Unified multi-analysis PDF |

All analysis endpoints return:
```json
{
  "ok": true,
  "version": "2.0",
  "analysis_type": "slope",
  "passes": true,
  "comb1": { ... },
  "comb2": { ... },
  "warnings": [],
  "errors": []
}
```

---

## Requirements

```
Python 3.12+
flask >= 3.0
reportlab >= 4.0
python-docx >= 1.1
matplotlib >= 3.8
numpy >= 1.26
pypdf >= 4.0          # for unified project PDF
```

**React SPA:**
```
Node.js 20+
React 18
Vite 5
Tailwind CSS 3
React Router 6
```

---

## EC7 DA1 Partial Factors

| Factor | DA1-C1 | DA1-C2 | Applied to |
|---|---|---|---|
| γ_φ | 1.00 | **1.25** | tan φ′_k |
| γ_c′ | 1.00 | **1.25** | c′_k |
| γ_cu | 1.00 | **1.40** | cu_k (undrained) |
| γ_G | 1.35 | 1.00 | Permanent loads |
| γ_Q | 1.50 | 1.30 | Variable loads |
| γ_Rv | 1.00 | 1.00 | Bearing resistance (R1) |

Design value: `φ′_d = arctan(tan(φ′_k) / γ_φ)`

---

## Test Suite

| Suite | Checks | Reference |
|---|---|---|
| test_bearing_capacity | ✅ | Meyerhof (1963), Hansen (1970) |
| test_settlement | ✅ | Bowles (1996), Terzaghi (1943) |
| test_limit_equilibrium | ✅ | Bishop (1955) |
| test_search | ✅ | Craig Ex.9.1 — FoS=1.441 |
| test_sheet_pile (57) | ✅ | Craig Ex.12.1 — <0.002% |
| test_pile (36) | ✅ | EC7 §7, Tomlinson (1970) |
| test_seepage (29) | ✅ | Laplace FD, Dupuit |
| test_exporters (40) | ✅ | PDF/DOCX/PNG content |
| test_app (15) | ✅ | Flask routes + exports |
| **TOTAL 20 suites** | **552+** | **All green** |

---

## Production Deployment

```bash
# Build React
cd react-spa && npm run build

# Start with Docker Compose
DESIGNAPP_SECRET=your-secret-key docker compose up -d
# → https://your-domain/
```

See `deploy/nginx.conf` and `docker-compose.yml` for configuration details.

---

## Bibliography

1. EC7: EN 1997-1:2004 — Eurocode 7: Geotechnical Design, Part 1. CEN, Brussels.
2. Bishop, A.W. (1955) — The use of the slip circle in stability analysis. Géotechnique 5(1):7–17.
3. Hansen, J.B. (1970) — A revised formula for bearing capacity. Danish Geotech. Inst. Bull. 28.
4. Meyerhof, G.G. (1963) — Recent research on bearing capacity. Canadian Geotech. J. 1(1).
5. Craig, R.F. (2004) — Craig's Soil Mechanics, 7th ed. Spon Press.
6. Spencer, E. (1967) — Stability of embankments assuming parallel inter-slice forces. Géotechnique 17(1).
7. Blum, H. (1931) — Einspannungsverhältnisse bei Bohlwerken. W. Ernst & Sohn.
8. Terzaghi, K. (1943) — Theoretical Soil Mechanics. Wiley.
9. Tomlinson, M.J. (1970) — Adhesion of piles driven in clay. Proc. 4th ICSMFE 2:66–71.
10. Bowles, J.E. (1996) — Foundation Analysis and Design, 5th ed. McGraw-Hill.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.
> AI-assisted development context is stored in `.claude/CLAUDE_CONTEXT.md`.

## License

MIT — see [LICENSE](LICENSE).
