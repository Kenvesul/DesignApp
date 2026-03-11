/**
 * App.jsx — DesignApp root component
 *
 * Routes (React Router v6):
 *   /              → Home / analysis selector
 *   /slope         → Slope stability analysis (S14)
 *   /foundation    → Foundation bearing capacity (S15)
 *   /wall          → Retaining wall analysis (S15)
 *   /pile          → Pile capacity analysis (S15)
 *   /sheet-pile    → Sheet pile free-earth (S15)
 *   /project       → Project dashboard — combined results (S16)
 */

import { Routes, Route, NavLink, useLocation } from "react-router-dom";
import { useState } from "react";

import HomePage          from "./pages/HomePage";
import SlopePage         from "./pages/SlopePage";
import FoundationPage    from "./pages/FoundationPage";
import WallPage          from "./pages/WallPage";
import PilePage          from "./pages/PilePage";
import SheetPilePage     from "./pages/SheetPilePage";
import ProjectDashboard  from "./pages/ProjectDashboard";

const NAV_ITEMS = [
  { to: "/slope",      label: "⛰ Slope" },
  { to: "/foundation", label: "🏛 Foundation" },
  { to: "/wall",       label: "🧱 Wall" },
  { to: "/pile",       label: "📌 Pile" },
  { to: "/sheet-pile", label: "🗂 Sheet Pile" },
  { to: "/project",    label: "📋 Project" },
];

function NavBar() {
  const [menuOpen, setMenuOpen] = useState(false);
  return (
    <nav className="bg-brand-700 dark:bg-gray-900 shadow-lg sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">

          {/* Logo */}
          <NavLink to="/" className="flex items-center gap-2 text-white font-bold text-lg">
            <span className="text-2xl">🏗</span>
            <span className="hidden sm:inline">DesignApp</span>
            <span className="text-xs font-normal text-blue-200 hidden md:inline ml-1">
              EC7 v2.0
            </span>
          </NavLink>

          {/* Desktop nav */}
          <div className="hidden md:flex gap-1">
            {NAV_ITEMS.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-white/20 text-white"
                      : "text-blue-100 hover:bg-white/10 hover:text-white"
                  }`
                }
              >
                {label}
              </NavLink>
            ))}
          </div>

          {/* Mobile hamburger */}
          <button
            className="md:hidden text-white p-2 rounded hover:bg-white/10"
            onClick={() => setMenuOpen(o => !o)}
            aria-label="Open navigation menu"
          >
            {menuOpen ? "✕" : "☰"}
          </button>
        </div>

        {/* Mobile menu */}
        {menuOpen && (
          <div className="md:hidden pb-3 flex flex-col gap-1">
            {NAV_ITEMS.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                onClick={() => setMenuOpen(false)}
                className={({ isActive }) =>
                  `px-3 py-2 rounded text-sm font-medium ${
                    isActive ? "bg-white/20 text-white" : "text-blue-100 hover:bg-white/10"
                  }`
                }
              >
                {label}
              </NavLink>
            ))}
          </div>
        )}
      </div>
    </nav>
  );
}

function Footer() {
  return (
    <footer className="mt-auto border-t border-gray-200 dark:border-gray-700
                       bg-white dark:bg-gray-900 py-4 text-center
                       text-xs text-gray-400 dark:text-gray-500">
      DesignApp v2.0 — Eurocode 7 EN 1997-1:2004 |
      Bishop (1955) · Hansen (1970) · Craig (2004) · Blum (1931)
    </footer>
  );
}

export default function App() {
  return (
    <div className="min-h-screen flex flex-col bg-gray-50 dark:bg-gray-950">
      <NavBar />
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Routes>
          <Route path="/"           element={<HomePage />} />
          <Route path="/slope"      element={<SlopePage />} />
          <Route path="/foundation" element={<FoundationPage />} />
          <Route path="/wall"       element={<WallPage />} />
          <Route path="/pile"       element={<PilePage />} />
          <Route path="/sheet-pile" element={<SheetPilePage />} />
          <Route path="/project"    element={<ProjectDashboard />} />
          <Route path="*"           element={
            <div className="text-center py-24">
              <p className="text-6xl mb-4">404</p>
              <p className="text-gray-500">Page not found.</p>
            </div>
          } />
        </Routes>
      </main>
      <Footer />
    </div>
  );
}
