/**
 * pages/FoundationPage.jsx
 *
 * Foundation bearing capacity + settlement — Sprint 15.
 * POST /api/foundation/analyse → EC7 §6.5.2 DA1 results.
 *
 * Refs: EC7 §6.5.2, Hansen (1970), Meyerhof (1963), Bowles (1996)
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
  soil_name: "Medium Sand", gamma: "18.0", phi_k: "30.0", c_k: "0",
  B: "2.0", Df: "1.0", L: "", e_B: "0", e_L: "0",
  Gk: "200", Qk: "80", Hk: "0",
  Es_kpa: "10000", nu: "0.3", s_lim: "0.025",
  project: "", job_ref: "", calc_by: "", checked_by: "",
};

export default function FoundationPage() {
  const { soils, loading: soilLoading } = useSoilLibrary();
  const [form, setForm]     = useState(DEFAULT);
  const [errors, setErrors] = useState({});
  const [result, setResult] = useState(null);
  const [running, setRunning] = useState(false);
  const [apiErr, setApiErr]  = useState(null);

  function set(name, value) {
    setForm(f => ({ ...f, [name]: value }));
    setErrors(e => ({ ...e, [name]: undefined }));
  }

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
      B: +form.B, Df: +form.Df, L: form.L ? +form.L : null,
      e_B: +(form.e_B||0), e_L: +(form.e_L||0),
      Gk: +form.Gk, Qk: +(form.Qk||0), Hk: +(form.Hk||0),
      Es_kpa: +form.Es_kpa, nu: +form.nu, s_lim: +form.s_lim,
    };
    try {
      const resp = await fetch("/api/foundation/analyse", {
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
          🏛 Foundation Bearing Capacity
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Hansen factors · EC7 §6.5.2 · DA1 dual-combination · Immediate + consolidation settlement
        </p>
      </div>

      <form onSubmit={handleSubmit} noValidate className="card space-y-5">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <h2 className="font-semibold">Soil & Geometry</h2>
          <SoilPicker soils={soils} loading={soilLoading} onSelect={onSoilSelect} />
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <InputField label="γ" name="gamma" value={form.gamma} onChange={e => set("gamma",e.target.value)} type="number" unit="kN/m³" required min={5} max={25} step={0.1} error={errors.gamma} />
          <InputField label="φ′_k" name="phi_k" value={form.phi_k} onChange={e => set("phi_k",e.target.value)} type="number" unit="°" required min={0} max={55} error={errors.phi_k} />
          <InputField label="c′_k" name="c_k" value={form.c_k} onChange={e => set("c_k",e.target.value)} type="number" unit="kPa" min={0} />
          <InputField label="B (width)" name="B" value={form.B} onChange={e => set("B",e.target.value)} type="number" unit="m" required min={0.1} step={0.1} error={errors.B} />
          <InputField label="L (length)" name="L" value={form.L} onChange={e => set("L",e.target.value)} type="number" unit="m" min={0} help="Blank = strip footing" />
          <InputField label="Df (depth)" name="Df" value={form.Df} onChange={e => set("Df",e.target.value)} type="number" unit="m" required min={0} step={0.1} error={errors.Df} />
          <InputField label="e_B (eccentricity)" name="e_B" value={form.e_B} onChange={e => set("e_B",e.target.value)} type="number" unit="m" min={0} step={0.01} />
          <InputField label="e_L (eccentricity)" name="e_L" value={form.e_L} onChange={e => set("e_L",e.target.value)} type="number" unit="m" min={0} step={0.01} />
        </div>

        <div>
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Loads</h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            <InputField label="Gk (permanent)" name="Gk" value={form.Gk} onChange={e => set("Gk",e.target.value)} type="number" unit="kN/m" required error={errors.Gk} />
            <InputField label="Qk (variable)" name="Qk" value={form.Qk} onChange={e => set("Qk",e.target.value)} type="number" unit="kN/m" min={0} />
            <InputField label="Hk (horizontal)" name="Hk" value={form.Hk} onChange={e => set("Hk",e.target.value)} type="number" unit="kN/m" min={0} />
          </div>
        </div>

        <div>
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Settlement (SLS)</h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            <InputField label="E_s (stiffness)" name="Es_kpa" value={form.Es_kpa} onChange={e => set("Es_kpa",e.target.value)} type="number" unit="kPa" min={100} />
            <InputField label="ν (Poisson ratio)" name="nu" value={form.nu} onChange={e => set("nu",e.target.value)} type="number" min={0.1} max={0.49} step={0.05} />
            <InputField label="s_lim (allowable)" name="s_lim" value={form.s_lim} onChange={e => set("s_lim",e.target.value)} type="number" unit="m" min={0.001} step={0.005} help="EC7 §2.4.8: typically 25mm" />
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <InputField label="Project" name="project" value={form.project} onChange={e => set("project",e.target.value)} />
          <InputField label="Job ref" name="job_ref" value={form.job_ref} onChange={e => set("job_ref",e.target.value)} />
          <InputField label="Calc by" name="calc_by" value={form.calc_by} onChange={e => set("calc_by",e.target.value)} />
          <InputField label="Checked by" name="checked_by" value={form.checked_by} onChange={e => set("checked_by",e.target.value)} />
        </div>

        <div className="flex gap-3 pt-2">
          <button type="submit" disabled={running} className="btn-primary">
            {running ? "Running…" : "Run Analysis"}
          </button>
          <button type="button" onClick={() => { setForm(DEFAULT); setResult(null); setErrors({}); }} className="btn-secondary">Reset</button>
        </div>
      </form>

      {running && <LoadingSpinner message="Computing bearing capacity…" />}
      {apiErr && <div className="card border-red-300 bg-red-50 dark:bg-red-950"><p className="text-sm text-red-700 dark:text-red-300">⚠ {apiErr}</p></div>}
      {result && <FoundationResults result={result} />}
    </div>
  );
}

function FoundationResults({ result }) {
  const c1 = result.comb1 || {};
  const c2 = result.comb2 || {};
  const rows = [
    { label: "q_Ed (design action)", c1: c1.q_ed, c2: c2.q_ed, unit: "kPa" },
    { label: "q_Rd (design resistance)", c1: c1.q_rd, c2: c2.q_rd, unit: "kPa", passes_c1: c1.passes_bearing, passes_c2: c2.passes_bearing },
    { label: "Utilisation q_Ed/q_Rd", c1: c1.utilisation, c2: c2.utilisation, unit: "" },
    { label: "Settlement s_imm", c1: result.s_immediate, c2: result.s_immediate, unit: "m", passes_c1: result.passes_settlement, passes_c2: result.passes_settlement },
    { label: "Settlement s_total", c1: result.s_total, c2: result.s_total, unit: "m" },
  ];
  return (
    <div className="space-y-5">
      <div className="card flex flex-wrap items-center gap-4">
        <div><p className="text-xs text-gray-400">Overall EC7</p><ResultBadge passes={result.passes} size="lg" /></div>
        <div><p className="text-xs text-gray-400">Design resistance (C2)</p>
          <p className="text-2xl font-bold font-mono">{c2.q_rd?.toFixed(1) ?? "—"} kPa</p></div>
        <div><p className="text-xs text-gray-400">Total settlement</p>
          <p className="text-2xl font-bold font-mono">{result.s_total != null ? (result.s_total*1000).toFixed(1) : "—"} mm</p></div>
        <div className="ml-auto"><ExportBar type="foundation" /></div>
      </div>
      <div className="card"><FactorTable rows={rows} title="DA1 Combinations — EC7 §6.5.2" /></div>
    </div>
  );
}
