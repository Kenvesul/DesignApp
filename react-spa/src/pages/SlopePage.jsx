/**
 * pages/SlopePage.jsx
 *
 * Slope stability analysis — Sprint 14.
 * POST /api/slope/analyse → EC7 DA1 Bishop results.
 *
 * Refs: EC7 §11, Bishop (1955), Craig Ex.9.1
 */

import { useState } from "react";
import InputField     from "../components/InputField";
import SoilPicker     from "../components/SoilPicker";
import ResultBadge    from "../components/ResultBadge";
import FactorTable    from "../components/FactorTable";
import ExportBar      from "../components/ExportBar";
import LoadingSpinner from "../components/LoadingSpinner";
import { useSoilLibrary } from "../hooks/useSoilLibrary";

const DEFAULT = {
  soil_name:    "Dense Sand",
  gamma:        "19.0",
  phi_k:        "35.0",
  c_k:          "0",
  ru:           "0",
  slope_points: "0,3\n6,3\n12,0\n18,0",
  n_cx:         "12",
  n_cy:         "12",
  n_r:          "8",
  num_slices:   "20",
  project:      "",
  job_ref:      "",
  calc_by:      "",
  checked_by:   "",
};

export default function SlopePage() {
  const { soils, loading: soilLoading } = useSoilLibrary();
  const [form,    setForm]    = useState(DEFAULT);
  const [errors,  setErrors]  = useState({});
  const [result,  setResult]  = useState(null);
  const [running, setRunning] = useState(false);
  const [apiErr,  setApiErr]  = useState(null);

  function set(name, value) {
    setForm(f => ({ ...f, [name]: value }));
    setErrors(e => ({ ...e, [name]: undefined }));
  }

  function onSoilSelect(soil) {
    setForm(f => ({
      ...f,
      soil_name: soil.name,
      gamma:     String(soil.gamma),
      phi_k:     String(soil.phi_k),
      c_k:       String(soil.c_k ?? 0),
    }));
  }

  function validate() {
    const e = {};
    if (!form.gamma || isNaN(+form.gamma) || +form.gamma <= 0)
      e.gamma = "Required — positive number (kN/m³)";
    if (!form.phi_k || isNaN(+form.phi_k) || +form.phi_k < 0 || +form.phi_k > 60)
      e.phi_k = "Required — 0°–60°";
    if (isNaN(+form.ru) || +form.ru < 0 || +form.ru > 1)
      e.ru = "Pore pressure ratio — 0–1";
    const pts = form.slope_points.trim().split("\n").filter(Boolean);
    if (pts.length < 3)
      e.slope_points = "Minimum 3 coordinate pairs required";
    return e;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length) { setErrors(errs); return; }

    setRunning(true);
    setResult(null);
    setApiErr(null);

    // Convert textarea points to [[x,y], ...] array
    const points = form.slope_points.trim().split("\n")
      .map(l => l.replace(/[()]/g, "").split(/[\s,]+/).map(Number))
      .filter(p => p.length >= 2 && !isNaN(p[0]) && !isNaN(p[1]));

    const payload = {
      ...form,
      slope_points: points,
      gamma:        +form.gamma,
      phi_k:        +form.phi_k,
      c_k:          +(form.c_k || 0),
      ru:           +(form.ru || 0),
      n_cx:         +form.n_cx,
      n_cy:         +form.n_cy,
      n_r:          +form.n_r,
      num_slices:   +form.num_slices,
    };

    try {
      const resp = await fetch("/api/slope/analyse", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(payload),
      });
      const data = await resp.json();
      if (data.ok) {
        setResult(data);
      } else {
        setApiErr(data.errors?.join("; ") || data.error || "Analysis failed");
      }
    } catch (err) {
      setApiErr(`Network error: ${err.message}`);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          ⛰ Slope Stability Analysis
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Bishop simplified · EC7 §11 · DA1 dual-combination · Craig Ex.9.1 FoS=1.441
        </p>
      </div>

      {/* Input form */}
      <form onSubmit={handleSubmit} noValidate className="card space-y-5">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <h2 className="font-semibold text-gray-800 dark:text-gray-200">Soil Parameters</h2>
          <SoilPicker soils={soils} loading={soilLoading} onSelect={onSoilSelect} />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <InputField label="γ (unit weight)" name="gamma" value={form.gamma}
            onChange={e => set("gamma", e.target.value)}
            type="number" unit="kN/m³" min={5} max={25} step={0.1}
            required error={errors.gamma} />
          <InputField label="φ′_k (friction angle)" name="phi_k" value={form.phi_k}
            onChange={e => set("phi_k", e.target.value)}
            type="number" unit="°" min={0} max={60} step={0.5}
            required error={errors.phi_k} />
          <InputField label="c′_k (cohesion)" name="c_k" value={form.c_k}
            onChange={e => set("c_k", e.target.value)}
            type="number" unit="kPa" min={0} step={1} error={errors.c_k} />
          <InputField label="r_u (pore pressure ratio)" name="ru" value={form.ru}
            onChange={e => set("ru", e.target.value)}
            type="number" min={0} max={0.8} step={0.05} error={errors.ru}
            help="0 = dry · 0.5 = typical phreatic" />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Slope profile points <span className="text-red-500">*</span>
          </label>
          <textarea
            name="slope_points"
            value={form.slope_points}
            onChange={e => set("slope_points", e.target.value)}
            rows={5}
            className={`input font-mono text-xs ${errors.slope_points ? "input-error" : ""}`}
            placeholder="x1,y1&#10;x2,y2&#10;x3,y3&#10;..."
            aria-label="Slope profile coordinates, one pair per line"
          />
          {errors.slope_points && (
            <p className="text-xs text-red-600 mt-1">{errors.slope_points}</p>
          )}
          <p className="text-xs text-gray-400 mt-1">
            Example (Craig 9.1): 0,3 / 6,3 / 12,0 / 18,0
          </p>
        </div>

        <div>
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
            Search Grid
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <InputField label="Grid cols (n_cx)" name="n_cx" value={form.n_cx}
              onChange={e => set("n_cx", e.target.value)}
              type="number" min={4} max={30} step={1} />
            <InputField label="Grid rows (n_cy)" name="n_cy" value={form.n_cy}
              onChange={e => set("n_cy", e.target.value)}
              type="number" min={4} max={30} step={1} />
            <InputField label="Radii per cell (n_r)" name="n_r" value={form.n_r}
              onChange={e => set("n_r", e.target.value)}
              type="number" min={2} max={20} step={1} />
            <InputField label="Slices per circle" name="num_slices" value={form.num_slices}
              onChange={e => set("num_slices", e.target.value)}
              type="number" min={10} max={50} step={5} />
          </div>
        </div>

        <div>
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
            Project Metadata (for reports)
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <InputField label="Project" name="project" value={form.project}
              onChange={e => set("project", e.target.value)} />
            <InputField label="Job ref" name="job_ref" value={form.job_ref}
              onChange={e => set("job_ref", e.target.value)} />
            <InputField label="Calc by" name="calc_by" value={form.calc_by}
              onChange={e => set("calc_by", e.target.value)} />
            <InputField label="Checked by" name="checked_by" value={form.checked_by}
              onChange={e => set("checked_by", e.target.value)} />
          </div>
        </div>

        <div className="flex items-center gap-3 pt-2">
          <button type="submit" disabled={running} className="btn-primary">
            {running ? "Running…" : "Run Analysis"}
          </button>
          <button type="button" onClick={() => { setForm(DEFAULT); setResult(null); setErrors({}); }}
                  className="btn-secondary">
            Reset
          </button>
        </div>
      </form>

      {/* Loading */}
      {running && <LoadingSpinner message="Running Bishop grid search…" />}

      {/* API error */}
      {apiErr && (
        <div className="card border-red-300 bg-red-50 dark:bg-red-950">
          <p className="text-sm text-red-700 dark:text-red-300">⚠ {apiErr}</p>
        </div>
      )}

      {/* Results */}
      {result && <SlopeResults result={result} />}
    </div>
  );
}

function SlopeResults({ result }) {
  const c1 = result.comb1 || {};
  const c2 = result.comb2 || {};
  const gov = result.governing_combination || "—";
  const warns = result.warnings || [];

  const rows = [
    {
      label:     "FoS_d (Bishop)",
      c1:        c1.fos_d,
      c2:        c2.fos_d,
      unit:      "",
      passes_c1: c1.fos_d >= 1.0,
      passes_c2: c2.fos_d >= 1.0,
    },
    { label: "FoS_k (characteristic)", c1: result.fos_k, c2: result.fos_k, unit: "" },
    { label: "Critical circle cx",     c1: result.critical_circle?.cx, c2: result.critical_circle?.cx, unit: "m" },
    { label: "Critical circle cy",     c1: result.critical_circle?.cy, c2: result.critical_circle?.cy, unit: "m" },
    { label: "Critical radius r",      c1: result.critical_circle?.r,  c2: result.critical_circle?.r,  unit: "m" },
  ];

  return (
    <div className="space-y-5">
      {/* Summary bar */}
      <div className="card flex flex-wrap items-center gap-4">
        <div>
          <p className="text-xs text-gray-400 dark:text-gray-500">Overall EC7 result</p>
          <ResultBadge passes={result.passes} size="lg" />
        </div>
        <div>
          <p className="text-xs text-gray-400 dark:text-gray-500">Characteristic FoS</p>
          <p className="text-2xl font-bold font-mono text-gray-900 dark:text-gray-100">
            {result.fos_k?.toFixed(3) ?? "—"}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-400 dark:text-gray-500">Governing combination</p>
          <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">{gov}</p>
        </div>
        <div className="ml-auto">
          <ExportBar type="slope" disabled={false} />
        </div>
      </div>

      {/* Warnings */}
      {warns.length > 0 && (
        <div className="card border-amber-300 bg-amber-50 dark:bg-amber-950 space-y-1">
          {warns.map((w, i) => (
            <p key={i} className="text-xs text-amber-700 dark:text-amber-300">⚠ {w}</p>
          ))}
        </div>
      )}

      {/* DA1 factor table */}
      <div className="card">
        <FactorTable rows={rows} title="DA1 Combinations — EC7 §2.4.7.3" />
      </div>

      {/* Slice table */}
      {result.slices && (
        <div className="card">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
            Slice Summary ({result.slices.length} slices — critical circle)
          </h3>
          <div className="overflow-x-auto max-h-64">
            <table className="result-table text-xs">
              <thead>
                <tr>
                  <th>#</th><th>Width (m)</th><th>Height (m)</th>
                  <th>α (°)</th><th>Weight (kN/m)</th>
                </tr>
              </thead>
              <tbody>
                {result.slices.map((s, i) => (
                  <tr key={i}>
                    <td className="text-center font-mono">{i + 1}</td>
                    <td className="text-right font-mono">{s.width?.toFixed(3)}</td>
                    <td className="text-right font-mono">{s.height?.toFixed(3)}</td>
                    <td className="text-right font-mono">{s.alpha_deg?.toFixed(2)}</td>
                    <td className="text-right font-mono">{s.weight?.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
