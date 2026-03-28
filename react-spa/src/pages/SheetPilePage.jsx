/**
 * pages/SheetPilePage.jsx
 *
 * Sheet pile free-earth support — Sprint 15.
 * POST /api/sheet-pile/analyse → EC7 §9 / Craig Ex.12.1.
 *
 * Refs: EC7 §9, Blum (1931), Craig Ex.12.1
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
  phi_k: "38.0", c_k: "0", gamma: "20.0",
  h_retain: "6.0", prop_type: "propped_top", delta_deg: "0", surcharge_kpa: "0",
  project: "", job_ref: "", calc_by: "", checked_by: "",
};

export default function SheetPilePage() {
  const { soils, loading: soilLoading } = useSoilLibrary();
  const [form, setForm]     = useState(DEFAULT);
  const [result, setResult] = useState(null);
  const [running, setRunning] = useState(false);
  const [apiErr, setApiErr]  = useState(null);

  function set(n, v) { setForm(f => ({ ...f, [n]: v })); }

  function onSoilSelect(soil) {
    setForm(f => ({ ...f, phi_k: String(soil.phi_k), c_k: String(soil.c_k ?? 0), gamma: String(soil.gamma) }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setRunning(true); setResult(null); setApiErr(null);
    const payload = {
      ...form,
      phi_k: +form.phi_k, c_k: +(form.c_k||0), gamma: +form.gamma,
      h_retained: +form.h_retain, delta_deg: +(form.delta_deg||0),
      q: +(form.surcharge_kpa||0),
    };
    try {
      const resp = await fetch("/api/sheet-pile/analyse", {
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
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">🗂 Sheet Pile Analysis</h1>
        <p className="text-sm text-gray-500 mt-1">
          Free-earth support · EC7 §9 · DA1 dual-combination · Validated: Craig Ex.12.1 &lt;0.002%
        </p>
      </div>

      <div className="card bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800 text-xs text-blue-700 dark:text-blue-300">
        <strong>Craig Ex.12.1 calibration:</strong> φ′=38°, γ=20 kN/m³, h=6 m, propped at top →
        DA1-C1: d=1.510 m, T=38.30 kN/m, M=102.4 kN·m/m |
        DA1-C2: d=2.136 m, T=54.78 kN/m, M=154.2 kN·m/m
      </div>

      <form onSubmit={handleSubmit} noValidate className="card space-y-5">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <h2 className="font-semibold">Soil Parameters</h2>
          <SoilPicker soils={soils} loading={soilLoading} onSelect={onSoilSelect} />
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <InputField label="φ′_k" name="phi_k" value={form.phi_k} onChange={e => set("phi_k",e.target.value)} type="number" unit="°" required min={0} max={55} />
          <InputField label="c′_k" name="c_k" value={form.c_k} onChange={e => set("c_k",e.target.value)} type="number" unit="kPa" min={0} />
          <InputField label="γ" name="gamma" value={form.gamma} onChange={e => set("gamma",e.target.value)} type="number" unit="kN/m³" required min={5} max={25} />
          <InputField label="Surcharge q" name="surcharge_kpa" value={form.surcharge_kpa} onChange={e => set("surcharge_kpa",e.target.value)} type="number" unit="kPa" min={0} />
        </div>

        <div>
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Sheet Pile Geometry</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <InputField label="h_retain (retained height)" name="h_retain" value={form.h_retain} onChange={e => set("h_retain",e.target.value)} type="number" unit="m" required min={0.5} step={0.1} />
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Support type</label>
              <select name="prop_type" value={form.prop_type} onChange={e => set("prop_type",e.target.value)} className="input text-sm">
                <option value="propped_top">Propped at top</option>
                <option value="cantilever">Cantilever (free)</option>
                <option value="propped_mid">Propped at mid-height</option>
              </select>
            </div>
            <InputField label="Wall friction δ" name="delta_deg" value={form.delta_deg} onChange={e => set("delta_deg",e.target.value)} type="number" unit="°" min={0} max={30} step={1} help="Typically 0–φ/2" />
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

      {running && <LoadingSpinner message="Solving embedment depth…" />}
      {apiErr && <div className="card border-red-300 bg-red-50 dark:bg-red-950"><p className="text-sm text-red-700 dark:text-red-300">⚠ {apiErr}</p></div>}
      {result && <SheetPileResults result={result} />}
    </div>
  );
}

function SheetPileResults({ result }) {
  const c1 = result.comb1 || {};
  const c2 = result.comb2 || {};
  const rows = [
    { label: "Ka",                      c1: c1.Ka,    c2: c2.Ka },
    { label: "Kp",                      c1: c1.Kp,    c2: c2.Kp },
    { label: "d_min (embedment) [m]",   c1: c1.d_min, c2: c2.d_min },
    { label: "Prop/anchor force T [kN/m]", c1: c1.T, c2: c2.T },
    { label: "Max bending moment [kN·m/m]", c1: c1.M_max, c2: c2.M_max },
  ];
  const gov = result.governing || result.governing_combination || "—";
  return (
    <div className="space-y-5">
      <div className="card flex flex-wrap items-center gap-4">
        <div><p className="text-xs text-gray-400">Overall EC7</p><ResultBadge passes={result.passes} size="lg" /></div>
        <div><p className="text-xs text-gray-400">Embedment d (governing)</p>
          <p className="text-2xl font-bold font-mono">{result.d_design?.toFixed(3) ?? "—"} m</p></div>
        <div><p className="text-xs text-gray-400">Governing combination</p>
          <p className="text-sm font-semibold">{gov}</p></div>
        <div className="ml-auto"><ExportBar type="sheet-pile" showPng={false} /></div>
      </div>
      <div className="card"><FactorTable rows={rows} title="DA1 Combinations — EC7 §9 / Craig Ex.12.1" /></div>
    </div>
  );
}
