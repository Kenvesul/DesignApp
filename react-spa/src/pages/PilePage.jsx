/**
 * pages/PilePage.jsx
 *
 * Pile capacity analysis — Sprint 15.
 * POST /api/pile/analyse → EC7 §7 DA1 α/β-method results.
 *
 * Refs: EC7 §7, Tomlinson (1970), Craig Ch.7
 */

import { useState } from "react";
import InputField     from "../components/InputField";
import ResultBadge    from "../components/ResultBadge";
import ExportBar      from "../components/ExportBar";
import LoadingSpinner from "../components/LoadingSpinner";

const DEFAULT_LAYER = { thickness: "5.0", soil_type: "sand", phi_k: "30.0", c_k: "0", gamma: "18.0" };

const DEFAULT = {
  pile_type: "driven_steel", material: "steel",
  diameter: "0.5", length: "10.0",
  Gk: "500", Qk: "200",
  project: "", job_ref: "", calc_by: "", checked_by: "",
};

export default function PilePage() {
  const [form, setForm]     = useState(DEFAULT);
  const [layers, setLayers] = useState([{ ...DEFAULT_LAYER }]);
  const [result, setResult] = useState(null);
  const [running, setRunning] = useState(false);
  const [apiErr, setApiErr]  = useState(null);

  function set(n, v) { setForm(f => ({ ...f, [n]: v })); }

  function setLayer(i, n, v) {
    setLayers(ls => ls.map((l, idx) => idx === i ? { ...l, [n]: v } : l));
  }

  function addLayer() { setLayers(ls => [...ls, { ...DEFAULT_LAYER }]); }
  function removeLayer(i) { setLayers(ls => ls.filter((_, idx) => idx !== i)); }

  async function handleSubmit(e) {
    e.preventDefault();
    setRunning(true); setResult(null); setApiErr(null);
    const payload = {
      pile_type: form.pile_type, material: form.material,
      diameter: +form.diameter, length: +form.length,
      Gk: +form.Gk, Qk: +(form.Qk||0),
      layers: layers.map(l => ({
        thickness: +l.thickness, soil_type: l.soil_type,
        phi_k: +l.phi_k, c_k: +(l.c_k||0), gamma: +l.gamma,
      })),
      project: form.project, job_ref: form.job_ref,
      calc_by: form.calc_by, checked_by: form.checked_by,
    };
    try {
      const resp = await fetch("/api/pile/analyse", {
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
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">📌 Pile Capacity</h1>
        <p className="text-sm text-gray-500 mt-1">EC7 §7 · α-method (clay) · β-method (sand) · R4 resistance factors · DA1</p>
      </div>

      <form onSubmit={handleSubmit} noValidate className="card space-y-5">
        <h2 className="font-semibold">Pile Geometry & Loads</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Pile type</label>
            <select value={form.pile_type} onChange={e => set("pile_type",e.target.value)} className="input text-sm">
              <option value="driven_steel">Driven steel</option>
              <option value="driven_concrete">Driven concrete</option>
              <option value="bored">Bored</option>
              <option value="cfa">CFA</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Material</label>
            <select value={form.material} onChange={e => set("material",e.target.value)} className="input text-sm">
              <option value="steel">Steel</option>
              <option value="concrete">Concrete</option>
              <option value="timber">Timber</option>
            </select>
          </div>
          <InputField label="Diameter" name="diameter" value={form.diameter} onChange={e => set("diameter",e.target.value)} type="number" unit="m" min={0.1} step={0.05} required />
          <InputField label="Length" name="length" value={form.length} onChange={e => set("length",e.target.value)} type="number" unit="m" min={1} step={0.5} required />
          <InputField label="Gk (permanent)" name="Gk" value={form.Gk} onChange={e => set("Gk",e.target.value)} type="number" unit="kN" required />
          <InputField label="Qk (variable)" name="Qk" value={form.Qk} onChange={e => set("Qk",e.target.value)} type="number" unit="kN" min={0} />
        </div>

        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Soil Layers (top to bottom)</h3>
            <button type="button" onClick={addLayer} className="btn-secondary text-xs py-1 px-3">+ Add Layer</button>
          </div>
          <div className="space-y-3">
            {layers.map((l, i) => (
              <div key={i} className="grid grid-cols-5 gap-2 items-end bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
                <InputField label={`Layer ${i+1} thickness`} name={`t_${i}`} value={l.thickness} onChange={e => setLayer(i,"thickness",e.target.value)} type="number" unit="m" min={0.1} step={0.1} />
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Type</label>
                  <select value={l.soil_type} onChange={e => setLayer(i,"soil_type",e.target.value)} className="input text-xs py-1.5">
                    <option value="sand">Sand</option>
                    <option value="clay">Clay</option>
                    <option value="gravel">Gravel</option>
                    <option value="silt">Silt</option>
                  </select>
                </div>
                <InputField label="φ′_k" name={`phi_${i}`} value={l.phi_k} onChange={e => setLayer(i,"phi_k",e.target.value)} type="number" unit="°" min={0} max={55} />
                <InputField label="c_k / cu" name={`c_${i}`} value={l.c_k} onChange={e => setLayer(i,"c_k",e.target.value)} type="number" unit="kPa" min={0} />
                <div className="flex items-end gap-2">
                  <InputField label="γ" name={`g_${i}`} value={l.gamma} onChange={e => setLayer(i,"gamma",e.target.value)} type="number" unit="kN/m³" min={5} max={25} />
                  {layers.length > 1 && (
                    <button type="button" onClick={() => removeLayer(i)} className="btn-danger text-xs py-1 px-2 mb-0.5">✕</button>
                  )}
                </div>
              </div>
            ))}
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
          <button type="button" onClick={() => { setForm(DEFAULT); setLayers([{...DEFAULT_LAYER}]); setResult(null); }} className="btn-secondary">Reset</button>
        </div>
      </form>

      {running && <LoadingSpinner message="Computing pile capacity…" />}
      {apiErr && <div className="card border-red-300 bg-red-50 dark:bg-red-950"><p className="text-sm text-red-700 dark:text-red-300">⚠ {apiErr}</p></div>}
      {result && <PileResults result={result} />}
    </div>
  );
}

function PileResults({ result }) {
  const c1 = result.comb1 || {};
  const c2 = result.comb2 || {};
  return (
    <div className="space-y-5">
      <div className="card flex flex-wrap items-center gap-4">
        <div><p className="text-xs text-gray-400">Overall EC7</p><ResultBadge passes={result.passes} size="lg" /></div>
        <div><p className="text-xs text-gray-400">Char. capacity R_k</p><p className="text-2xl font-bold font-mono">{result.R_k?.toFixed(1) ?? "—"} kN</p></div>
        <div><p className="text-xs text-gray-400">Design action (C2)</p><p className="text-2xl font-bold font-mono">{c2.F_cd?.toFixed(1) ?? "—"} kN</p></div>
        <div className="ml-auto"><ExportBar type="pile" showPng={false} /></div>
      </div>
      <div className="card">
        <table className="result-table text-sm">
          <thead><tr><th>Parameter</th><th className="text-right">DA1-C1</th><th className="text-right">DA1-C2</th></tr></thead>
          <tbody>
            {[
              ["Design action F_cd (kN)", c1.F_cd, c2.F_cd],
              ["Design resistance R_cd (kN)", c1.R_cd, c2.R_cd],
              ["Shaft resistance R_s (kN)", c1.R_s, c2.R_s],
              ["Base resistance R_b (kN)", c1.R_b, c2.R_b],
              ["Utilisation", c1.utilisation, c2.utilisation],
            ].map(([lbl, v1, v2]) => (
              <tr key={lbl}>
                <td>{lbl}</td>
                <td className="text-right font-mono">{v1 != null ? Number(v1).toFixed(3) : "—"}</td>
                <td className="text-right font-mono">{v2 != null ? Number(v2).toFixed(3) : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
