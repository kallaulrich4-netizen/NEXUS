import { NavLink } from "react-router-dom";
import { Crown } from "lucide-react";
import { PRIMARY_NAV } from "../config/modules";

export default function Sidebar() {
  return (
    <aside className="hidden md:flex md:flex-col w-64 shrink-0 h-screen sticky top-0 border-r border-nexus-border bg-nexus-bg">
      <div className="flex items-center gap-2 px-6 h-16 shrink-0">
        <div className="w-8 h-8 rounded-lg bg-nexus-gradient flex items-center justify-center font-bold text-white">
          N
        </div>
        <span className="font-bold text-lg tracking-tight">NEXUS</span>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-2 space-y-1">
        {PRIMARY_NAV.map((item) => (
          <NavLink
            key={item.key}
            to={item.path}
            end={item.path === "/"}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                isActive
                  ? "bg-nexus-gradient text-white"
                  : "text-nexus-text-muted hover:bg-nexus-surface hover:text-nexus-text"
              }`
            }
          >
            <item.icon size={18} className="shrink-0" />
            <span className="truncate">{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="p-4">
        <div className="nexus-card p-4">
          <div className="flex items-center gap-2 text-amber-400 mb-1">
            <Crown size={18} />
            <span className="font-semibold text-sm">Nexus Premium</span>
          </div>
          <p className="text-xs text-nexus-text-muted mb-3">Débloquez toutes les fonctionnalités</p>
          <button className="w-full nexus-btn-primary text-sm py-2">Passer Premium</button>
        </div>
      </div>
    </aside>
  );
}
