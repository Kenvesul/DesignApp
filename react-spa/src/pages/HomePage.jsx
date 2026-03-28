import { Link } from "react-router-dom";

const CARDS = [
  {
    to: "/foundation",
    icon: "F",
    title: "Foundation Bearing",
    desc: "Hansen bearing factors, eccentricity, immediate and consolidation settlement.",
    ref: "EC7 6.5.2 - Hansen (1970) - Meyerhof (1963)",
    color: "from-blue-500 to-blue-700",
  },
  {
    to: "/wall",
    icon: "W",
    title: "Retaining Wall",
    desc: "L-shaped gravity wall: sliding, overturning and bearing EC7 checks.",
    ref: "EC7 9 - Rankine/Coulomb - Craig Ch.11",
    color: "from-orange-500 to-red-600",
  },
  {
    to: "/pile",
    icon: "P",
    title: "Pile Capacity",
    desc: "Alpha-method (clay) and beta-method (sand), multi-layer profile, R4 factors.",
    ref: "EC7 7 - Tomlinson (1970) - Craig Ch.7",
    color: "from-purple-500 to-violet-700",
  },
  {
    to: "/sheet-pile",
    icon: "SP",
    title: "Sheet Pile",
    desc: "Free-earth support method, embedment solver, prop force and moment.",
    ref: "EC7 9 - Blum (1931) - Craig Ex.12.1",
    color: "from-teal-500 to-cyan-700",
  },
  {
    to: "/project",
    icon: "PR",
    title: "Project Dashboard",
    desc: "Combine completed analyses into one stamped PDF calculation set.",
    ref: "Unified project report - all EC7 checks",
    color: "from-gray-600 to-gray-800",
  },
];

export default function HomePage() {
  return (
    <div className="space-y-8">
      <div className="text-center space-y-3">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
          DesignApp <span className="text-brand-600">v2.0</span>
        </h1>
        <p className="text-gray-500 dark:text-gray-400 max-w-xl mx-auto text-sm">
          Modular Python geotechnical analysis suite - Eurocode 7 EN 1997-1:2004
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {CARDS.map(({ to, icon, title, desc, ref, color }) => (
          <Link
            key={to}
            to={to}
            className="group card hover:shadow-md transition-shadow cursor-pointer hover:border-brand-300 dark:hover:border-brand-600"
          >
            <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${color} flex items-center justify-center text-xl mb-3 group-hover:scale-105 transition-transform`}>
              {icon}
            </div>
            <h2 className="font-semibold text-gray-900 dark:text-gray-100 mb-1">{title}</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">{desc}</p>
            <p className="text-xs text-gray-400 dark:text-gray-500 font-mono">{ref}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
