/**
 * pages/WallPage.jsx
 *
 * Retaining wall analysis — Sprint 15.
 * POST /api/wall/analyse → EC7 §9 sliding/overturning/bearing DA1.
 *
 * Refs: EC7 §9, Rankine/Coulomb, Craig Ch.11
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
  soil_name: "Granular Fill", gamma: "18.0", phi_k: "30.0", c_k: "0",
  H_wall: "4.0", B_base: "3.0", B_toe: "0.8",
  t_stem_base: "0.4", t_stem_top: "0.3", t_base: "0.5",
  surcharge_kpa: "0",
  project: "", job_ref: "", calc_by: "", checked_by: "",
};

export default function WallPage() {
  const { soils, loading: soilLoading } = useSoilLibrary();
  const [form, setForm]     = useState(DEFAULT);
  const [result, setResult] = useState(null);
  const [running, setRunning] = useState(false);
  const [apiErr, setApiErr]  = useState(null);

  function set(n, v) { setForm(f => ({ ...f, [n]: v })); }

  function onSoilSelect(soil) {
    setForm(f => ({ ...f, soil_name: soil.name, gamma: String(soil.gamma),
                          phi_k: String(soil.phi_k), c_k: String(soil.c_k ?? 0) }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setRunning(true); setResult(null); setApiErr(null);
    const payload = {
      ...form,
      gamma: +form.gamma, phi_k: +form.phi_k, c_k: +(form.c_k||0),
      H_wall: +form.H_wall, B_base: +form.B_base, B_toe: +form.B_toe,
      t_stem_base: +form.t_stem_base, t_stem_top: +form.t_stem_top, t_base: +form.t_base,
      surcharge_kpa: +(form.surcharge_kpa||0),
    };
    try {
      const resp = await fetch("/api/wall/analyse", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await resp.json();
      if (data.ok) setResult(data);
      else setApiErr(data.errors?.join("; ") || data.error || "Analysis failed");
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
          🧱 Retaining Wall Analysis
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          EC7 §9 · Rankine/Coulomb · Sliding, overturning, bearing · DA1 dual-combination
        </p>
      </div>

      <form onSubmit={handleSubmit} noValidate className="card space-y-5">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <h2 className="font-semibold">Backfill Soil</h2>
          <SoilPicker soils={soils} loading={soilLoading} onSelect={onSoilSelect} />
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <InputField label="γ" name="gamma" value={form.gamma} onChange={e => set("gamma",e.target.value)} type="number" unit="kN/m³" required />
          <InputField label="φ′_k" name="phi_k" value={form.phi_k} onChange={e => set("phi_k",e.target.value)} type="number" unit="°" required />
          <InputField label="c′_k" name="c_k" value={form.c_k} onChange={e => set("c_k",e.target.value)} type="number" unit="kPa" min={0} />
          <InputField label="Surcharge q" name="surcharge_kpa" value={form.surcharge_kpa} onChange={e => set("surcharge_kpa",e.target.value)} type="number" unit="kPa" min={0} />
        </div>

        <div>
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Wall Geometry</h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            <InputField label="H_wall (retained height)" name="H_wall" value={form.H_wall} onChange={e => set("H_wall",e.target.value)} type="number" unit="m" required min={0.5} step={0.1} />
            <InputField label="B_base (total base width)" name="B_base" value={form.B_base} onChange={e => set("B_base",e.target.value)} type="number" unit="m" required min={0.5} step={0.1} />
            <InputField label="B_toe (toe projection)" name="B_toe" value={form.B_toe} onChange={e => set("B_toe",e.target.value)} type="number" unit="m" min={0} step={0.1} />
            <InputField label="t_stem (base)" name="t_stem_base" value={form.t_stem_base} onChange={e => set("t_stem_base",e.target.value)} type="number" unit="m" min={0.1} step={0.05} />
            <InputField label="t_stem (top)" name="t_stem_top" value={form.t_stem_top} onChange={e => set("t_stem_top",e.target.value)} type="number" unit="m" min={0.1} step={0.05} />
            <InputField label="t_base (slab thickness)" name="t_base" value={form.t_base} onChange={e => set("t_base",e.target.value)} type="number" unit="m" min={0.1} step={0.05} />
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <InputField label="Project" name="project" value={form.project} onChange={e => set("project",e.target.value)} />
          <InputField label="Job ref" name="job_ref" value={form.job_ref} onChange={e => set("job_ref",e.target.value)} />
          <InputField label="Calc by" name="calc_by" value={form.calc_by} onChange={e => set("calc_by",e.target.value)} />
          <InputField label="Checked by" name="checked_by" value={form.checked_by} onChange={e => set("checked_by",e.target.value)} />
        </div>

        <div className="flex gap-3 pt-2">
          <button type="submit" disabled={running} className="btn-primary">{running ? "Running…" : "Run Analysis"}</button>
          <button type="button" onClick={() => { setForm(DEFAULT); setResult(null); }} className="btn-secondary">Reset</button>
        </div>
      </form>

      {running && <LoadingSpinner message="Computing wall stability…" />}
      {apiErr && <div className="card border-red-300 bg-red-50 dark:bg-red-950"><p className="text-sm text-red-700 dark:text-red-300">⚠ {apiErr}</p></div>}
      {result && <WallResults result={result} />}
    </div>
  );
}

function WallResults({ result }) {
  const c1 = result.comb1 || {};
  const c2 = result.comb2 || {};
  const rows = [
    { label: "Ka (active)",         c1: c1.Ka,                c2: c2.Ka },
    { label: "Kp (passive)",        c1: c1.Kp,                c2: c2.Kp },
    { label: "Sliding FoS",         c1: c1.fos_sliding,       c2: c2.fos_sliding,       passes_c1: c1.passes_sliding,       passes_c2: c2.passes_sliding },
    { label: "Overturning FoS",     c1: c1.fos_overturning,   c2: c2.fos_overturning,   passes_c1: c1.passes_overturning,   passes_c2: c2.passes_overturning },
    { label: "Bearing utilisation", c1: c1.bearing_util,      c2: c2.bearing_util,      passes_c1: c1.passes_bearing,       passes_c2: c2.passes_bearing },
  ];
  return (
    <div className="space-y-5">
      <div className="card flex flex-wrap items-center gap-4">
        <div><p className="text-xs text-gray-400">Overall EC7</p><ResultBadge passes={result.passes} size="lg" /></div>
        <div><p className="text-xs text-gray-400">Ka (C2)</p><p className="text-2xl font-bold font-mono">{c2.Ka?.toFixed(3) ?? "—"}</p></div>
        <div><p className="text-xs text-gray-400">Sliding FoS (C2)</p><p className="text-2xl font-bold font-mono">{c2.fos_sliding?.toFixed(3) ?? "—"}</p></div>
        <div className="ml-auto"><ExportBar type="wall" /></div>
      </div>
      <div className="card"><FactorTable rows={rows} title="DA1 Combinations — EC7 §9" /></div>
    </div>
  );
}
