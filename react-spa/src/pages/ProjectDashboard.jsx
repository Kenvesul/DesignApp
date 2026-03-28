import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import ResultBadge from "../components/ResultBadge";
import LoadingSpinner from "../components/LoadingSpinner";

const ANALYSIS_ROUTES = [
  { key: "foundation", label: "Foundation Bearing", to: "/foundation" },
  { key: "wall", label: "Retaining Wall", to: "/wall" },
  { key: "pile", label: "Pile Capacity", to: "/pile" },
  { key: "sheet_pile", label: "Sheet Pile", to: "/sheet-pile" },
];

export default function ProjectDashboard() {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [exportErr, setExportErr] = useState(null);

  useEffect(() => {
    fetch("/api/health")
      .then(r => r.json())
      .then(d => {
        setSession(d.session || {});
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  async function exportProjectPDF() {
    setExporting(true);
    setExportErr(null);
    try {
      const resp = await fetch("/api/project/export/pdf");
      if (!resp.ok) {
        const j = await resp.json().catch(() => ({}));
        throw new Error(j.error || `HTTP ${resp.status}`);
      }
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "project_calculations.pdf";
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setExportErr(err.message);
    } finally {
      setExporting(false);
    }
  }

  const completedCount = session ? Object.values(session).filter(Boolean).length : 0;

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Project Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">Combine completed analyses into one stamped EC7 calculation set</p>
      </div>

      {loading && <LoadingSpinner message="Loading session state..." size="sm" />}

      {!loading && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {ANALYSIS_ROUTES.map(({ key, label, to }) => {
              const done = session?.[key];
              return (
                <div
                  key={key}
                  className={`card flex items-center justify-between gap-3 ${
                    done ? "border-green-300 dark:border-green-700" : "border-gray-200 dark:border-gray-700 opacity-70"
                  }`}
                >
                  <div>
                    <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">{label}</p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {done ? "Analysis complete - included in PDF" : "Not yet run"}
                    </p>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <ResultBadge passes={done || null} size="sm" />
                    {!done && (
                      <Link to={to} className="text-xs text-brand-600 dark:text-brand-400 hover:underline">
                        Run -&gt;
                      </Link>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="card space-y-3">
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div>
                <h2 className="font-semibold text-gray-800 dark:text-gray-200">Unified Project PDF</h2>
                <p className="text-xs text-gray-500 mt-0.5">
                  {completedCount > 0
                    ? `${completedCount} analysis type${completedCount > 1 ? "s" : ""} will be included`
                    : "No completed analyses yet - run at least one above"}
                </p>
              </div>
              <button onClick={exportProjectPDF} disabled={exporting || completedCount === 0} className="btn-primary">
                {exporting ? "Generating PDF..." : "Export Project PDF"}
              </button>
            </div>

            {exportErr && <p className="text-xs text-red-600 dark:text-red-400">Export failed: {exportErr}</p>}

            <div className="text-xs text-gray-400 dark:text-gray-500 space-y-1 border-t dark:border-gray-700 pt-3">
              <p>The project PDF includes:</p>
              <ul className="list-disc list-inside space-y-0.5 ml-2">
                <li>Cover page with project metadata, date, and EC7 standard reference</li>
                <li>One calculation section per completed analysis type</li>
                <li>DA1 combination tables with PASS or FAIL indicators</li>
                <li>Plots and diagrams for the completed non-desktop analysis surfaces that remain enabled</li>
              </ul>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
