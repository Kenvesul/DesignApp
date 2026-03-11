# Contributing to DesignApp

Thank you for contributing. This document covers the architecture rules, coding standards, and workflow required to keep the codebase clean and the calculations trustworthy.

---

## Architecture Rules — Non-Negotiable

```
Input (models/) → Engine (core/) → Result dict → Exporters / UI
```

| Layer | Rule |
|---|---|
| `models/` | stdlib only. No imports from `core/`. |
| `core/` | stdlib + numpy. No UI imports. No reportlab/matplotlib. |
| `api.py` | Only file `ui/` may import. Accepts/returns plain dicts. |
| `exporters/` | matplotlib + reportlab + python-docx. No Flask. |
| `ui/app.py` | Imports ONLY from `ui/api.py`. No math. |
| `react-spa/` | Communicates ONLY with `/api/*` endpoints. No Python imports. |

**Violating the layer boundaries is a blocking review issue.**

---

## Adding a New Analysis Type

1. **Model** — add dataclass to `models/your_model.py`
2. **Engine** — add calculation module to `core/your_analysis.py` with EC7 formula citations
3. **Test** — add `tests/test_your_analysis.py` with a textbook calibration value
4. **API bridge** — add `run_your_analysis()` and `validate_your_params()` to `api.py`
5. **Exporter** — add PDF/DOCX section to `exporters/report_pdf.py` and `exporters/report_docx.py`
6. **UI** — add Flask route to `ui/app.py` + Jinja2 template + React page

Each step must pass before moving to the next (incremental rule).

---

## Code Standards

### Python

- **Type hints** on all public function signatures
- **Docstring** on every function citing the formula source:
  ```python
  def bearing_capacity_hansen(phi_d, c_d, q, B, ...):
      """
      Hansen (1970) ultimate bearing capacity — EC7 §6.5.2, Eq. D.2.
      q_ult = c·Nc·sc·ic + q·Nq·sq·iq + 0.5·γ·B′·Nγ·sγ·iγ
      """
  ```
- **No external deps in `core/` or `models/`** — stdlib + math only
- `from __future__ import annotations` at top of every module

### Import style (MANDATORY)

```python
# ✅ CORRECT — always use full package path
from models.soil import Soil
from core.bearing_capacity import bearing_capacity_hansen
from exporters.report_pdf import generate_slope_report

# ❌ WRONG — bare module name (breaks when run as package)
from soil import Soil
from bearing_capacity import bearing_capacity_hansen
```

### JavaScript / React

- Functional components only (no class components)
- Custom hooks in `react-spa/src/hooks/`
- Shared UI components in `react-spa/src/components/`
- API calls only from page components or hooks — never from shared components
- Tailwind utility classes only — no inline `style={}` props

---

## Testing Requirements

Every module **must** have a test that compares output to a published textbook value or EC7 example:

```python
def test_craig_example_12_1():
    """Craig (2004) Ex.12.1 — φ′=38°, γ=20 kN/m³, h=6m, propped top."""
    result = analyse_sheet_pile_da1(pile, factors_c2)
    assert abs(result.d_min - 2.1363) < 0.001   # <0.002% tolerance
    assert abs(result.T    - 54.780) < 0.01
    assert abs(result.M_max - 154.221) < 0.01
```

Run all tests before submitting a PR:
```bash
cd tests/
for f in test_*.py; do python $f || exit 1; done
```

---

## Calibration Values — Never Change Without Review

| Check | Value | Tolerance | Reference |
|---|---|---|---|
| Slope FoS_k | 1.441 | ±0.005 | Craig Ex.9.1, Bishop, φ=35°, ru=0 |
| Sheet pile d (DA1-C2) | 2.1363 m | <0.002% | Craig Ex.12.1 |
| Sheet pile T (DA1-C2) | 54.780 kN/m | <0.002% | Craig Ex.12.1 |
| Sheet pile M (DA1-C2) | 154.221 kN·m/m | <0.002% | Craig Ex.12.1 |
| Foundation q_ult_k | 1010–1050 kPa | ±5% | Hansen, φ=30°, B=2m, Df=1m |

If a code change causes any calibration value to shift outside tolerance, it must be reviewed and justified before merging.

---

## Pull Request Checklist

- [ ] All 20 test suites pass (`552+` checks green)
- [ ] No bare module imports (run `python scripts/check_imports.py`)
- [ ] New function has docstring with formula source citation
- [ ] New analysis type has textbook calibration test
- [ ] Layer boundaries respected (no cross-layer imports)
- [ ] `api.py` updated if new analysis type added
- [ ] React page added for new analysis type (if applicable)

---

## Development Setup

```bash
# Python backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# React frontend
cd react-spa
npm install
npm run dev
```

`requirements-dev.txt`:
```
pytest
pytest-cov
playwright
```
