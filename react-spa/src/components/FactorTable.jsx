/**
 * components/FactorTable.jsx
 *
 * Renders a DA1 Combination 1 vs Combination 2 comparison table.
 *
 * Props:
 *   rows — array of { label, c1, c2, unit?, passes_c1?, passes_c2? }
 *   title — optional string header
 */

import ResultBadge from "./ResultBadge";

export default function FactorTable({ rows = [], title }) {
  return (
    <div className="overflow-x-auto">
      {title && (
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
          {title}
        </h3>
      )}
      <table className="result-table">
        <thead>
          <tr>
            <th className="text-left">Check</th>
            <th className="text-right">DA1-C1 (A1+M1+R1)</th>
            <th className="text-right">DA1-C2 (A2+M2+R1)</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              <td className="font-medium">{row.label}</td>
              <td className="text-right font-mono">
                {row.passes_c1 !== undefined ? (
                  <span className="flex items-center justify-end gap-2">
                    <ResultBadge passes={row.passes_c1} size="sm" />
                    <span>{fmt(row.c1)}{row.unit ? ` ${row.unit}` : ""}</span>
                  </span>
                ) : (
                  `${fmt(row.c1)}${row.unit ? ` ${row.unit}` : ""}`
                )}
              </td>
              <td className="text-right font-mono">
                {row.passes_c2 !== undefined ? (
                  <span className="flex items-center justify-end gap-2">
                    <ResultBadge passes={row.passes_c2} size="sm" />
                    <span>{fmt(row.c2)}{row.unit ? ` ${row.unit}` : ""}</span>
                  </span>
                ) : (
                  `${fmt(row.c2)}${row.unit ? ` ${row.unit}` : ""}`
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function fmt(v) {
  if (v === null || v === undefined) return "—";
  if (typeof v === "boolean")       return v ? "✓" : "✗";
  if (typeof v === "number")        return v.toFixed(3);
  return String(v);
}
