/**
 * pages/HomePage.jsx
 *
 * Landing page — analysis type selector cards.
 * Mirrors the Jinja2 index.html but as a React component.
 */

import { Link } from "react-router-dom";

const CARDS = [
  {
    to:      "/slope",
    icon:    "⛰",
    title:   "Slope Stability",
    desc:    "Bishop simplified slip-circle search. EC7 DA1 dual-combination.",
    ref:     "EC7 §11 · Bishop (1955) · Craig Ex.9.1",
    color:   "from-green-500 to-emerald-600",
  },
  {
    to:      "/foundation",
    icon:    "🏛",
    title:   "Foundation Bearing",
    desc:    "Hansen bearing factors, eccentricity, immediate + consolidation settlement.",
    ref:     "EC7 §6.5.2 · Hansen (1970) · Meyerhof (1963)",
    color:   "from-blue-500 to-blue-700",
  },
  {
    to:      "/wall",
    icon:    "🧱",
    title:   "Retaining Wall",
    desc:    "L-shaped gravity wall: sliding, overturning and bearing EC7 checks.",
    ref:     "EC7 §9 · Rankine/Coulomb · Craig Ch.11",
    color:   "from-orange-500 to-red-600",
  },
  {
    to:      "/pile",
    icon:    "📌",
    title:   "Pile Capacity",
    desc:    "α-method (clay) and β-method (sand), multi-layer profile, R4 factors.",
    ref:     "EC7 §7 · Tomlinson (1970) · Craig Ch.7",
    color:   "from-purple-500 to-violet-700",
  },
  {
    to:      "/sheet-pile",
    icon:    "🗂",
    title:   "Sheet Pile",
    desc:    "Free-earth support method, bisection embedment solver, prop force & moment.",
    ref:     "EC7 §9 · Blum (1931) · Craig Ex.12.1",
    color:   "from-teal-500 to-cyan-700",
  },
  {
    to:      "/project",
    icon:    "📋",
    title:   "Project Dashboard",
    desc:    "Combine all analyses into one stamped PDF calculation set.",
    ref:     "Unified project report — all EC7 checks",
    color:   "from-gray-600 to-gray-800",
  },
];

export default function HomePage() {
  return (
    <div className="space-y-8">
      {/* Hero */}
      <div className="text-center space-y-3">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
          DesignApp <span className="text-brand-600">v2.0</span>
        </h1>
        <p className="text-gray-500 dark:text-gray-400 max-w-xl mx-auto text-sm">
          Modular Python geotechnical analysis suite · Eurocode 7 EN 1997-1:2004 ·
          552+ validated checks · 19 test suites
        </p>
      </div>

      {/* Analysis cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {CARDS.map(({ to, icon, title, desc, ref, color }) => (
          <Link
            key={to}
            to={to}
            className="group card hover:shadow-md transition-shadow cursor-pointer
                       hover:border-brand-300 dark:hover:border-brand-600"
          >
            <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${color}
                             flex items-center justify-center text-xl mb-3
                             group-hover:scale-105 transition-transform`}>
              {icon}
            </div>
            <h2 className="font-semibold text-gray-900 dark:text-gray-100 mb-1">
              {title}
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
              {desc}
            </p>
            <p className="text-xs text-gray-400 dark:text-gray-500 font-mono">
              {ref}
            </p>
          </Link>
        ))}
      </div>

      {/* EC7 DA1 quick reference */}
      <div className="card">
        <h3 className="font-semibold text-gray-800 dark:text-gray-200 mb-3">
          EC7 DA1 Partial Factor Reference
        </h3>
        <div className="overflow-x-auto">
          <table className="result-table text-xs">
            <thead>
              <tr>
                <th>Factor</th>
                <th>Applied to</th>
                <th className="text-center">DA1-C1</th>
                <th className="text-center">DA1-C2</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["γ_φ",  "tan φ′_k",        "1.00", "1.25"],
                ["γ_c′", "c′_k (effective)", "1.00", "1.25"],
                ["γ_cu", "cu_k (undrained)", "1.00", "1.40"],
                ["γ_G",  "Gk permanent",     "1.35", "1.00"],
                ["γ_Q",  "Qk variable",      "1.50", "1.30"],
                ["γ_Rv", "Bearing (R1)",     "1.00", "1.00"],
              ].map(([f, a, c1, c2]) => (
                <tr key={f}>
                  <td className="font-mono font-semibold">{f}</td>
                  <td className="text-gray-500">{a}</td>
                  <td className="text-center">{c1}</td>
                  <td className={`text-center font-semibold ${
                    c2 !== "1.00" ? "text-amber-600 dark:text-amber-400" : ""
                  }`}>{c2}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
