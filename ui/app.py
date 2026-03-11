"""
ui/app.py
=========
Flask web application for DesignApp v2.0.

ARCHITECTURE RULE:
    This module ONLY imports from . (ui/api.py) — never from core/ or models/.
    All math is delegated to api.py which acts as the sole bridge.

Routes (Jinja2 — legacy, kept active during React transition)
------
GET  /                          → Home page / React SPA entry
GET  /slope                     → Slope stability input form
POST /slope/analyse             → Run analysis, return results page
GET  /slope/export/pdf          → Download PDF calculation sheet
GET  /slope/export/docx         → Download Word calculation sheet
GET  /slope/export/png          → Download cross-section PNG
GET  /foundation                → Foundation analysis input form
POST /foundation/analyse        → Run foundation analysis
GET  /foundation/export/pdf     → Download PDF foundation report
GET  /foundation/export/docx    → Download Word foundation report
GET  /foundation/export/png     → Download foundation PNG
GET  /wall                      → Retaining wall input form
POST /wall/analyse              → Run wall analysis
GET  /wall/export/pdf           → Download PDF wall report
GET  /wall/export/docx          → Download Word wall report
GET  /wall/export/png           → Download wall PNG
GET  /sheet-pile                → Sheet pile input form
POST /sheet-pile/analyse        → Run sheet pile analysis        [B-14]
GET  /sheet-pile/export/pdf     → Download PDF sheet pile report
GET  /sheet-pile/export/docx    → Download Word sheet pile report
GET  /project/export/pdf        → Unified project PDF (all types) [B-14]

JSON API Routes (Sprint 14-16 — React SPA communication)
---------
GET  /api/health                → {"status":"ok","app":"DesignApp","version":"2.0"}
GET  /api/soils                 → JSON soil library list
POST /api/slope/analyse         → JSON slope analysis result      [S14]
POST /api/foundation/analyse    → JSON foundation analysis result [S15]
POST /api/wall/analyse          → JSON wall analysis result       [S15]
POST /api/pile/analyse          → JSON pile analysis result       [S15]
POST /api/sheet-pile/analyse    → JSON sheet pile analysis result [S15]
GET  /api/project/export/pdf    → Unified PDF (from JSON body)    [S16]
"""

from __future__ import annotations

import base64
import io
import json
import os
import tempfile

from flask import (Flask, render_template, request, redirect,
                   url_for, session, jsonify, send_file, make_response)

# ── THE ONLY import from the math side ───────────────────────────────────────
from . import api

# ── App factory ───────────────────────────────────────────────────────────────
app = Flask(__name__,
            template_folder="templates",
            static_folder="static")

app.secret_key = os.environ.get("DESIGNAPP_SECRET", "dev-secret-change-in-production")
# Session cookies must be large enough to hold full analysis results
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# ── CORS (dev server support for React @ localhost:5173) ─────────────────────
_CORS_ORIGIN = os.environ.get("CORS_ORIGIN", "http://localhost:5173")

@app.after_request
def _add_cors(response):
    """
    Add CORS headers so the Vite dev server (port 5173) can call /api/* routes.
    In production the React bundle is served from Flask itself, so CORS is not
    needed — the header is harmless in that case.
    """
    response.headers["Access-Control-Allow-Origin"]  = _CORS_ORIGIN
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response


@app.route("/api/<path:_>", methods=["OPTIONS"])
def _options_handler(_):
    """Handle CORS preflight requests for all /api/* routes."""
    return make_response("", 204)


# ── Custom Jinja2 filters ────────────────────────────────────────────────────
import math as _math

@app.template_filter("sin_deg")
def _sin_deg(x):
    """sin of angle given in degrees — used in slice summary table."""
    try:
        return round(_math.sin(_math.radians(float(x))), 4)
    except (ValueError, TypeError):
        return "—"

@app.template_filter("cos_deg")
def _cos_deg(x):
    """cos of angle given in degrees — used in slice summary table."""
    try:
        return round(_math.cos(_math.radians(float(x))), 4)
    except (ValueError, TypeError):
        return "—"


# ── Form parsers ─────────────────────────────────────────────────────────────

def _parse_slope_points(raw: str) -> list:
    """
    Parse slope points from textarea input.
    Accepts lines like:  0,3   or   0 3   or   (0, 3)
    Returns list of [x, y] pairs.
    """
    points = []
    for line in raw.strip().splitlines():
        line = line.replace("(", "").replace(")", "").replace(";", ",")
        parts = line.replace(",", " ").split()
        if len(parts) >= 2:
            try:
                points.append([float(parts[0]), float(parts[1])])
            except ValueError:
                pass
    return points


def _form_to_slope_params(form) -> dict:
    """Extract and coerce slope analysis parameters from a Flask form."""
    return dict(
        soil_name  = form.get("soil_name", "Soil"),
        gamma      = form.get("gamma"),
        phi_k      = form.get("phi_k"),
        c_k        = form.get("c_k", "0"),
        ru         = form.get("ru", "0"),
        slope_points = _parse_slope_points(form.get("slope_points", "")),
        n_cx       = form.get("n_cx", "12"),
        n_cy       = form.get("n_cy", "12"),
        n_r        = form.get("n_r",  "8"),
        num_slices = form.get("num_slices", "20"),
        project    = form.get("project", "DesignApp"),
        job_ref    = form.get("job_ref", ""),
        calc_by    = form.get("calc_by", ""),
        checked_by = form.get("checked_by", ""),
    )


def _form_to_foundation_params(form) -> dict:
    """Extract and coerce foundation analysis parameters from a Flask form."""
    return dict(
        soil_name  = form.get("soil_name", "Soil"),
        gamma      = form.get("gamma"),
        phi_k      = form.get("phi_k"),
        c_k        = form.get("c_k", "0"),
        B          = form.get("B"),
        Df         = form.get("Df"),
        L          = form.get("L") or None,
        e_B        = form.get("e_B", "0"),
        e_L        = form.get("e_L", "0"),
        Gk         = form.get("Gk"),
        Qk         = form.get("Qk", "0"),
        Hk         = form.get("Hk", "0"),
        Es_kpa     = form.get("Es_kpa", "10000"),
        nu         = form.get("nu", "0.3"),
        s_lim      = form.get("s_lim", "0.025"),
        # Clay consolidation fields (all optional)
        Cc         = form.get("Cc") or None,
        Cs         = form.get("Cs") or None,
        e0         = form.get("e0") or None,
        sigma_v0   = form.get("sigma_v0") or None,
        H_layer    = form.get("H_layer") or None,
        sigma_pc   = form.get("sigma_pc") or None,
        cv         = form.get("cv") or None,
        project    = form.get("project", "DesignApp"),
        job_ref    = form.get("job_ref", ""),
        calc_by    = form.get("calc_by", ""),
        checked_by = form.get("checked_by", ""),
    )


def _form_to_wall_params(form) -> dict:
    """Extract and coerce retaining wall parameters from a Flask form."""
    return dict(
        soil_name     = form.get("soil_name", "Backfill"),
        gamma         = form.get("gamma"),
        phi_k         = form.get("phi_k"),
        c_k           = form.get("c_k", "0"),
        H_wall        = form.get("H_wall"),
        B_base        = form.get("B_base"),
        B_toe         = form.get("B_toe"),
        t_stem_base   = form.get("t_stem_base", "0.3"),
        t_stem_top    = form.get("t_stem_top",  "0.3"),
        t_base        = form.get("t_base",      "0.4"),
        surcharge_kpa = form.get("surcharge_kpa", "0"),
        gamma_found   = form.get("gamma_found") or None,
        phi_k_found   = form.get("phi_k_found") or None,
        c_k_found     = form.get("c_k_found")   or None,
        project       = form.get("project", "DesignApp"),
        job_ref       = form.get("job_ref", ""),
        calc_by       = form.get("calc_by", ""),
        checked_by    = form.get("checked_by", ""),
    )


def _form_to_sheet_pile_params(form) -> dict:
    """
    Extract sheet pile analysis parameters from a Flask form.

    Supports single-layer homogeneous input (the form approach).
    Multi-layer input is available via the JSON API only.
    """
    return dict(
        phi_k      = form.get("phi_k"),
        c_k        = form.get("c_k", "0"),
        gamma      = form.get("gamma"),
        h_retain   = form.get("h_retain"),
        prop_type  = form.get("prop_type", "propped_top"),
        delta_deg  = form.get("delta_deg", "0"),
        surcharge_kpa = form.get("surcharge_kpa", "0"),
        project    = form.get("project", "DesignApp"),
        job_ref    = form.get("job_ref", ""),
        calc_by    = form.get("calc_by", ""),
        checked_by = form.get("checked_by", ""),
    )


# ── Meta helpers ─────────────────────────────────────────────────────────────

def _meta_from_session(prefix: str) -> dict:
    """Read project metadata from session using a key prefix (e.g. 'wall_')."""
    return dict(
        project    = session.get(f"{prefix}project",    session.get("last_project",    "DesignApp")),
        job_ref    = session.get(f"{prefix}job_ref",    session.get("last_job_ref",    "")),
        calc_by    = session.get(f"{prefix}calc_by",    session.get("last_calc_by",    "")),
        checked_by = session.get(f"{prefix}checked_by", session.get("last_checked_by", "")),
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  JINJA2 ROUTES (legacy — kept active during React SPA transition)
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    """Home page — analysis type selector (also serves React SPA entry)."""
    return render_template("index.html")


# ── Slope stability ───────────────────────────────────────────────────────────

@app.route("/slope")
def slope_form():
    return render_template("slope_form.html", soils=api.get_soil_library())


@app.route("/slope/analyse", methods=["POST"])
def slope_analyse():
    params = _form_to_slope_params(request.form)
    errors = api.validate_slope_params(params)
    if errors:
        return render_template("slope_form.html",
                               soils=api.get_soil_library(),
                               errors=errors, prev=request.form)
    result = api.run_slope_analysis(params)
    if not result.get("ok"):
        return render_template("slope_form.html",
                               soils=api.get_soil_library(),
                               errors=[result.get("error", "Unknown error")],
                               prev=request.form)
    try:
        png_bytes = api.export_slope_plot_png(result, dpi=100)
        plot_b64  = base64.b64encode(png_bytes).decode("ascii")
    except Exception:
        plot_b64 = None

    session["last_slope"]      = result
    session["last_project"]    = params.get("project", "DesignApp")
    session["last_job_ref"]    = params.get("job_ref", "")
    session["last_calc_by"]    = params.get("calc_by", "")
    session["last_checked_by"] = params.get("checked_by", "")
    return render_template("slope_results.html", result=result, plot_b64=plot_b64)


@app.route("/slope/export/pdf")
def slope_export_pdf():
    result = session.get("last_slope")
    if not result:
        return redirect(url_for("slope_form"))
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        path = f.name
    api.export_pdf(result, path, **_meta_from_session("last_"))
    return send_file(path, as_attachment=True,
                     download_name="slope_stability.pdf",
                     mimetype="application/pdf")


@app.route("/slope/export/docx")
def slope_export_docx():
    result = session.get("last_slope")
    if not result:
        return redirect(url_for("slope_form"))
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        path = f.name
    api.export_docx(result, path, **_meta_from_session("last_"))
    return send_file(path, as_attachment=True,
                     download_name="slope_stability.docx",
                     mimetype="application/vnd.openxmlformats-officedocument"
                               ".wordprocessingml.document")


@app.route("/slope/export/png")
def slope_export_png():
    result = session.get("last_slope")
    if not result:
        return redirect(url_for("slope_form"))
    png = api.export_slope_plot_png(result, dpi=150)
    return send_file(io.BytesIO(png), as_attachment=True,
                     download_name="slope_section.png",
                     mimetype="image/png")


# ── Foundation ────────────────────────────────────────────────────────────────

@app.route("/foundation")
def foundation_form():
    return render_template("foundation_form.html", soils=api.get_soil_library())


@app.route("/foundation/analyse", methods=["POST"])
def foundation_analyse():
    params = _form_to_foundation_params(request.form)
    errors = api.validate_foundation_params(params)
    if errors:
        return render_template("foundation_form.html",
                               soils=api.get_soil_library(),
                               errors=errors, prev=request.form)
    result = api.run_foundation_analysis(params)
    if not result.get("ok"):
        return render_template("foundation_form.html",
                               soils=api.get_soil_library(),
                               errors=[result.get("error", "Unknown error")],
                               prev=request.form)
    session["last_foundation"]   = result
    session["fdn_project"]       = params.get("project", "DesignApp")
    session["fdn_job_ref"]       = params.get("job_ref", "")
    session["fdn_calc_by"]       = params.get("calc_by", "")
    session["fdn_checked_by"]    = params.get("checked_by", "")
    return render_template("foundation_results.html", result=result)


@app.route("/foundation/export/pdf")
def foundation_export_pdf():
    result = session.get("last_foundation")
    if not result:
        return redirect(url_for("foundation_form"))
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        path = f.name
    api.export_foundation_pdf(result, path, **_meta_from_session("fdn_"))
    return send_file(path, as_attachment=True,
                     download_name="foundation_bearing.pdf",
                     mimetype="application/pdf")


@app.route("/foundation/export/docx")
def foundation_export_docx():
    result = session.get("last_foundation")
    if not result:
        return redirect(url_for("foundation_form"))
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        path = f.name
    api.export_foundation_docx(result, path, **_meta_from_session("fdn_"))
    return send_file(path, as_attachment=True,
                     download_name="foundation_bearing.docx",
                     mimetype="application/vnd.openxmlformats-officedocument"
                               ".wordprocessingml.document")


@app.route("/foundation/export/png")
def foundation_export_png():
    result = session.get("last_foundation")
    if not result:
        return redirect(url_for("foundation_form"))
    png = api.export_foundation_plot_png(result, dpi=150)
    return send_file(io.BytesIO(png), as_attachment=True,
                     download_name="foundation_section.png",
                     mimetype="image/png")


# ── Retaining wall ────────────────────────────────────────────────────────────

@app.route("/wall")
def wall_form():
    return render_template("wall_form.html", soils=api.get_soil_library())


@app.route("/wall/analyse", methods=["POST"])
def wall_analyse():
    params = _form_to_wall_params(request.form)
    errors = api.validate_wall_params(params)
    if errors:
        return render_template("wall_form.html",
                               soils=api.get_soil_library(),
                               errors=errors, prev=request.form)
    result = api.run_wall_analysis(params)
    if not result.get("ok"):
        return render_template("wall_form.html",
                               soils=api.get_soil_library(),
                               errors=[result.get("error", "Unknown error")],
                               prev=request.form)
    session["last_wall"]       = result
    session["wall_project"]    = params.get("project", "DesignApp")
    session["wall_job_ref"]    = params.get("job_ref", "")
    session["wall_calc_by"]    = params.get("calc_by", "")
    session["wall_checked_by"] = params.get("checked_by", "")
    return render_template("wall_results.html", result=result)


@app.route("/wall/export/pdf")
def wall_export_pdf():
    result = session.get("last_wall")
    if not result:
        return redirect(url_for("wall_form"))
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        path = f.name
    api.export_wall_pdf(result, path, **_meta_from_session("wall_"))
    return send_file(path, as_attachment=True,
                     download_name="retaining_wall.pdf",
                     mimetype="application/pdf")


@app.route("/wall/export/docx")
def wall_export_docx():
    result = session.get("last_wall")
    if not result:
        return redirect(url_for("wall_form"))
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        path = f.name
    api.export_wall_docx(result, path, **_meta_from_session("wall_"))
    return send_file(path, as_attachment=True,
                     download_name="retaining_wall.docx",
                     mimetype="application/vnd.openxmlformats-officedocument"
                               ".wordprocessingml.document")


@app.route("/wall/export/png")
def wall_export_png():
    result = session.get("last_wall")
    if not result:
        return redirect(url_for("wall_form"))
    png = api.export_wall_plot_png(result, dpi=150)
    return send_file(io.BytesIO(png), as_attachment=True,
                     download_name="retaining_wall_section.png",
                     mimetype="image/png")


# ── Sheet pile ────────────────────────────────────────────────────────────────
# B-14: Sheet pile session storage + routes (Sprint 13)

@app.route("/sheet-pile")
def sheet_pile_form():
    return render_template("sheet_pile_form.html", soils=api.get_soil_library())


@app.route("/sheet-pile/analyse", methods=["POST"])
def sheet_pile_analyse():
    params = _form_to_sheet_pile_params(request.form)
    errors = api.validate_sheet_pile_params(params)
    if errors:
        return render_template("sheet_pile_form.html",
                               soils=api.get_soil_library(),
                               errors=errors, prev=request.form)
    result = api.run_sheet_pile_analysis(params)
    if not result.get("ok"):
        return render_template("sheet_pile_form.html",
                               soils=api.get_soil_library(),
                               errors=[result.get("error", "Unknown error")],
                               prev=request.form)
    # B-14 FIX: store in session so project PDF can include it
    session["last_sheet_pile"]   = result          # ← B-14 key fix
    session["sp_project"]        = params.get("project", "DesignApp")
    session["sp_job_ref"]        = params.get("job_ref", "")
    session["sp_calc_by"]        = params.get("calc_by", "")
    session["sp_checked_by"]     = params.get("checked_by", "")
    return render_template("sheet_pile_results.html", result=result)


@app.route("/sheet-pile/export/pdf")
def sheet_pile_export_pdf():
    result = session.get("last_sheet_pile")
    if not result:
        return redirect(url_for("sheet_pile_form"))
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        path = f.name
    api.export_wall_pdf(result, path, **_meta_from_session("sp_"))
    return send_file(path, as_attachment=True,
                     download_name="sheet_pile.pdf",
                     mimetype="application/pdf")


@app.route("/sheet-pile/export/docx")
def sheet_pile_export_docx():
    result = session.get("last_sheet_pile")
    if not result:
        return redirect(url_for("sheet_pile_form"))
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        path = f.name
    api.export_wall_docx(result, path, **_meta_from_session("sp_"))
    return send_file(path, as_attachment=True,
                     download_name="sheet_pile.docx",
                     mimetype="application/vnd.openxmlformats-officedocument"
                               ".wordprocessingml.document")


# ── Project export (unified) ──────────────────────────────────────────────────

@app.route("/project/export/pdf")
def project_export_pdf():
    """
    Download unified project PDF combining ALL analyses in the current session.

    B-14 FIX: now includes 'last_sheet_pile' in the session key scan.
    EC7 §2.1 — the calculation sheet must cover all analysis types submitted.
    """
    analyses = []
    for key in ("last_slope", "last_foundation", "last_wall", "last_sheet_pile"):
        a = session.get(key)
        if a and a.get("ok"):
            analyses.append(a)
    if not analyses:
        return redirect(url_for("index"))

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        path = f.name

    # Use first available metadata set
    meta = (_meta_from_session("last_") if session.get("last_slope") else
            _meta_from_session("fdn_")  if session.get("last_foundation") else
            _meta_from_session("wall_") if session.get("last_wall") else
            _meta_from_session("sp_"))

    api.export_project_pdf(analyses, path, **meta)
    return send_file(path, as_attachment=True,
                     download_name="project_calculations.pdf",
                     mimetype="application/pdf")


# ═══════════════════════════════════════════════════════════════════════════════
#  JSON API ROUTES (Sprint 14-16 — React SPA)
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/api/health")
def api_health():
    """Health check — also reports which session analyses are available."""
    return jsonify({
        "status":  "ok",
        "app":     "DesignApp",
        "version": "2.0",
        "session": {
            "slope":       bool(session.get("last_slope")),
            "foundation":  bool(session.get("last_foundation")),
            "wall":        bool(session.get("last_wall")),
            "sheet_pile":  bool(session.get("last_sheet_pile")),
        },
    })


@app.route("/api/soils")
def api_soils():
    """Return soil library as JSON."""
    return jsonify(api.get_soil_library())


@app.route("/api/slope/analyse", methods=["POST"])
def api_slope_analyse():
    """
    JSON endpoint for slope stability analysis (Sprint 14 — React SPA).

    Accepts: application/json with slope analysis parameters.
    Returns: full analysis result dict (same schema as run_slope_analysis).

    EC7 DA1 dual-combination, Bishop simplified (Bishop 1955).
    """
    params = request.get_json(force=True) or {}
    # Convert slope_points from JSON list if given as string in form encoding
    if isinstance(params.get("slope_points"), str):
        params["slope_points"] = _parse_slope_points(params["slope_points"])
    errors = api.validate_slope_params(params)
    if errors:
        return jsonify({"ok": False, "errors": errors}), 400
    result = api.run_slope_analysis(params)
    if result.get("ok"):
        # Stash in session so export routes work from the React client too
        session["last_slope"]      = result
        session["last_project"]    = params.get("project", "DesignApp")
        session["last_job_ref"]    = params.get("job_ref", "")
        session["last_calc_by"]    = params.get("calc_by", "")
        session["last_checked_by"] = params.get("checked_by", "")
    return jsonify(result)


@app.route("/api/foundation/analyse", methods=["POST"])
def api_foundation_analyse():
    """
    JSON endpoint for foundation bearing capacity analysis (Sprint 15).

    EC7 §6.5.2 — Meyerhof/Hansen bearing factors, DA1 dual-combination.
    """
    params = request.get_json(force=True) or {}
    errors = api.validate_foundation_params(params)
    if errors:
        return jsonify({"ok": False, "errors": errors}), 400
    result = api.run_foundation_analysis(params)
    if result.get("ok"):
        session["last_foundation"]  = result
        session["fdn_project"]      = params.get("project", "DesignApp")
        session["fdn_job_ref"]      = params.get("job_ref", "")
        session["fdn_calc_by"]      = params.get("calc_by", "")
        session["fdn_checked_by"]   = params.get("checked_by", "")
    return jsonify(result)


@app.route("/api/wall/analyse", methods=["POST"])
def api_wall_analyse():
    """
    JSON endpoint for retaining wall analysis (Sprint 15).

    EC7 §9 — sliding, overturning, bearing capacity DA1.
    """
    params = request.get_json(force=True) or {}
    errors = api.validate_wall_params(params)
    if errors:
        return jsonify({"ok": False, "errors": errors}), 400
    result = api.run_wall_analysis(params)
    if result.get("ok"):
        session["last_wall"]       = result
        session["wall_project"]    = params.get("project", "DesignApp")
        session["wall_job_ref"]    = params.get("job_ref", "")
        session["wall_calc_by"]    = params.get("calc_by", "")
        session["wall_checked_by"] = params.get("checked_by", "")
    return jsonify(result)


@app.route("/api/pile/analyse", methods=["POST"])
def api_pile_analyse():
    """
    JSON endpoint for pile capacity analysis (Sprint 15).

    EC7 §7 — α-method (clay) and β-method (sand), R4 resistance factors.
    """
    params = request.get_json(force=True) or {}
    errors = api.validate_pile_params(params)
    if errors:
        return jsonify({"ok": False, "errors": errors}), 400
    result = api.run_pile_analysis(params)
    return jsonify(result)


@app.route("/api/sheet-pile/analyse", methods=["POST"])
def api_sheet_pile_analyse():
    """
    JSON endpoint for sheet pile analysis (Sprint 15).

    EC7 §9 / Craig Ex.12.1 — free-earth support, DA1 dual-combination.
    """
    params = request.get_json(force=True) or {}
    errors = api.validate_sheet_pile_params(params)
    if errors:
        return jsonify({"ok": False, "errors": errors}), 400
    result = api.run_sheet_pile_analysis(params)
    if result.get("ok"):
        session["last_sheet_pile"]  = result
        session["sp_project"]       = params.get("project", "DesignApp")
        session["sp_job_ref"]       = params.get("job_ref", "")
        session["sp_calc_by"]       = params.get("calc_by", "")
        session["sp_checked_by"]    = params.get("checked_by", "")
    return jsonify(result)


@app.route("/api/project/export/pdf", methods=["GET", "POST"])
def api_project_export_pdf():
    """
    Return unified project PDF as binary (Sprint 16).

    GET  — uses analyses already stored in session.
    POST — accepts JSON body: {"analyses": [...result dicts...], "meta": {...}}
           Allows React client to submit analyses directly without session state.
    """
    if request.method == "POST":
        body     = request.get_json(force=True) or {}
        analyses = body.get("analyses", [])
        meta     = body.get("meta", {})
    else:
        analyses = [session[k] for k in
                    ("last_slope", "last_foundation", "last_wall", "last_sheet_pile")
                    if session.get(k) and session[k].get("ok")]
        meta = _meta_from_session("last_")

    if not analyses:
        return jsonify({"ok": False, "error": "No completed analyses in session"}), 400

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        path = f.name
    api.export_project_pdf(analyses, path, **meta)
    return send_file(path, as_attachment=True,
                     download_name="project_calculations.pdf",
                     mimetype="application/pdf")


# ── Export routes accessible from React client (use session) ─────────────────

@app.route("/api/slope/export/pdf")
def api_slope_export_pdf():
    result = session.get("last_slope")
    if not result:
        return jsonify({"ok": False, "error": "No slope analysis in session"}), 404
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        path = f.name
    api.export_pdf(result, path, **_meta_from_session("last_"))
    return send_file(path, as_attachment=True,
                     download_name="slope_stability.pdf", mimetype="application/pdf")


@app.route("/api/slope/export/docx")
def api_slope_export_docx():
    result = session.get("last_slope")
    if not result:
        return jsonify({"ok": False, "error": "No slope analysis in session"}), 404
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        path = f.name
    api.export_docx(result, path, **_meta_from_session("last_"))
    return send_file(path, as_attachment=True,
                     download_name="slope_stability.docx",
                     mimetype="application/vnd.openxmlformats-officedocument"
                               ".wordprocessingml.document")


@app.route("/api/slope/export/png")
def api_slope_export_png():
    result = session.get("last_slope")
    if not result:
        return jsonify({"ok": False, "error": "No slope analysis in session"}), 404
    png = api.export_slope_plot_png(result, dpi=150)
    return send_file(io.BytesIO(png), as_attachment=True,
                     download_name="slope_section.png", mimetype="image/png")


@app.route("/api/foundation/export/pdf")
def api_foundation_export_pdf():
    result = session.get("last_foundation")
    if not result:
        return jsonify({"ok": False, "error": "No foundation analysis in session"}), 404
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        path = f.name
    api.export_foundation_pdf(result, path, **_meta_from_session("fdn_"))
    return send_file(path, as_attachment=True,
                     download_name="foundation_bearing.pdf", mimetype="application/pdf")


@app.route("/api/foundation/export/docx")
def api_foundation_export_docx():
    result = session.get("last_foundation")
    if not result:
        return jsonify({"ok": False, "error": "No foundation analysis in session"}), 404
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        path = f.name
    api.export_foundation_docx(result, path, **_meta_from_session("fdn_"))
    return send_file(path, as_attachment=True,
                     download_name="foundation_bearing.docx",
                     mimetype="application/vnd.openxmlformats-officedocument"
                               ".wordprocessingml.document")


@app.route("/api/foundation/export/png")
def api_foundation_export_png():
    result = session.get("last_foundation")
    if not result:
        return jsonify({"ok": False, "error": "No foundation analysis in session"}), 404
    png = api.export_foundation_plot_png(result, dpi=150)
    return send_file(io.BytesIO(png), as_attachment=True,
                     download_name="foundation_section.png", mimetype="image/png")


@app.route("/api/wall/export/pdf")
def api_wall_export_pdf():
    result = session.get("last_wall")
    if not result:
        return jsonify({"ok": False, "error": "No wall analysis in session"}), 404
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        path = f.name
    api.export_wall_pdf(result, path, **_meta_from_session("wall_"))
    return send_file(path, as_attachment=True,
                     download_name="retaining_wall.pdf", mimetype="application/pdf")


@app.route("/api/wall/export/docx")
def api_wall_export_docx():
    result = session.get("last_wall")
    if not result:
        return jsonify({"ok": False, "error": "No wall analysis in session"}), 404
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        path = f.name
    api.export_wall_docx(result, path, **_meta_from_session("wall_"))
    return send_file(path, as_attachment=True,
                     download_name="retaining_wall.docx",
                     mimetype="application/vnd.openxmlformats-officedocument"
                               ".wordprocessingml.document")


@app.route("/api/wall/export/png")
def api_wall_export_png():
    result = session.get("last_wall")
    if not result:
        return jsonify({"ok": False, "error": "No wall analysis in session"}), 404
    png = api.export_wall_plot_png(result, dpi=150)
    return send_file(io.BytesIO(png), as_attachment=True,
                     download_name="retaining_wall_section.png", mimetype="image/png")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port  = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    print(f"\n  DesignApp running on http://127.0.0.1:{port}")
    print(f"  Debug mode : {debug}\n")
    app.run(host="127.0.0.1", port=port, debug=debug)
