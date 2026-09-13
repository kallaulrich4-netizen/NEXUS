import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight, Layers, Zap, Sparkles, Bell, Activity, ShieldCheck, AlertTriangle,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { MODULES } from "../config/modules";
import { apiRequest } from "../api/client";

const ACTION_LABELS = {
  connexion: "Connexion",
  creation: "Création",
  modification: "Modification",
  suppression: "Suppression",
  autre: "Action",
};

export default function Dashboard() {
  const { user } = useAuth();

  const [unreadCount, setUnreadCount] = useState(null);
  const [recentNotifications, setRecentNotifications] = useState([]);
  const [recentActivity, setRecentActivity] = useState([]);
  const [systemHealth, setSystemHealth] = useState(null);

  useEffect(() => {
    apiRequest("/notifications/unread-count").then((d) => setUnreadCount(d.unread_count)).catch(() => {});
    apiRequest("/notifications?unread_only=true").then((d) => setRecentNotifications(d.slice(0, 3))).catch(() => {});
    apiRequest("/activity-log/mine").then((d) => setRecentActivity(d.slice(0, 5))).catch(() => {});
    apiRequest("/devops/system-health").then(setSystemHealth).catch(() => {});
  }, []);

  const STATS = [
    { icon: Bell, label: "Notifications non lues", value: unreadCount ?? "—", accent: "text-nexus-blue" },
    { icon: Layers, label: "Modules intégrés", value: String(MODULES.length), accent: "text-nexus-purple" },
    {
      icon: Zap,
      label: "État de la plateforme",
      value: systemHealth ? systemHealth.status.replace(/^./, (c) => c.toUpperCase()) : "—",
      accent: systemHealth?.status === "operationnel" ? "text-emerald-400" : systemHealth ? "text-amber-400" : "text-amber-400",
    },
    { icon: Activity, label: "Activités récentes", value: recentActivity.length || "—", accent: "text-emerald-400" },
  ];

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Hero */}
      <section className="relative overflow-hidden nexus-card p-8 md:p-10 bg-nexus-globe">
        <p className="text-nexus-text-muted mb-1">Bienvenue sur</p>
        <h1 className="text-4xl md:text-5xl font-extrabold bg-clip-text text-transparent bg-nexus-gradient mb-3">
          NEXUS
        </h1>
        <p className="text-nexus-text-muted max-w-md mb-6">
          La plateforme intelligente qui connecte, informe et transforme le monde.
        </p>
        <div className="flex flex-wrap gap-3">
          <Link to="/ai" className="nexus-btn-primary flex items-center gap-2">
            Explorer Nexus <ArrowRight size={16} />
          </Link>
          <button className="nexus-btn-secondary">Regarder la démo</button>
        </div>
      </section>

      {/* Stats */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {STATS.map((stat) => (
          <div key={stat.label} className="nexus-card p-5 flex items-center gap-3">
            <div className={`w-10 h-10 rounded-xl bg-nexus-bg flex items-center justify-center ${stat.accent}`}>
              <stat.icon size={20} />
            </div>
            <div className="min-w-0">
              <p className="text-lg font-bold leading-tight">{stat.value}</p>
              <p className="text-xs text-nexus-text-muted truncate">{stat.label}</p>
            </div>
          </div>
        ))}
      </section>

      {/* Centre de pilotage : notifications + activité récente */}
      <section className="grid md:grid-cols-2 gap-4">
        <div className="nexus-card p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-medium flex items-center gap-2"><Bell size={16} /> Notifications importantes</h2>
            <Link to="/notifications" className="text-xs text-nexus-blue">Tout voir</Link>
          </div>
          <div className="space-y-2">
            {recentNotifications.map((n) => (
              <div key={n.id} className="text-sm py-1.5 border-b border-nexus-border last:border-0">
                <p className="font-medium">{n.title}</p>
                <p className="text-xs text-nexus-text-muted line-clamp-1">{n.message}</p>
              </div>
            ))}
            {recentNotifications.length === 0 && (
              <p className="text-sm text-nexus-text-muted">Aucune notification non lue.</p>
            )}
          </div>
        </div>

        <div className="nexus-card p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-medium flex items-center gap-2"><Activity size={16} /> Activité récente</h2>
            <Link to="/activity-log" className="text-xs text-nexus-blue">Historique complet</Link>
          </div>
          <div className="space-y-2">
            {recentActivity.map((entry) => (
              <div key={entry.id} className="flex items-center justify-between text-sm py-1.5 border-b border-nexus-border last:border-0">
                <div className="min-w-0">
                  <p className="font-medium truncate">{entry.description}</p>
                  <p className="text-xs text-nexus-text-muted capitalize">{entry.module}</p>
                </div>
                <span className="text-xs px-2 py-0.5 rounded-full bg-nexus-surface-hover shrink-0 ml-2">
                  {ACTION_LABELS[entry.action] || entry.action}
                </span>
              </div>
            ))}
            {recentActivity.length === 0 && (
              <p className="text-sm text-nexus-text-muted">Aucune activité récente.</p>
            )}
          </div>
        </div>
      </section>

      {systemHealth?.status !== "operationnel" && systemHealth && (
        <section className="nexus-card p-4 border border-amber-500/40 flex items-center gap-3">
          <AlertTriangle size={18} className="text-amber-400 shrink-0" />
          <p className="text-sm">
            L'état de la plateforme est actuellement <span className="font-medium">{systemHealth.status}</span>.
            Consultez le module DevOps pour plus de détails.
          </p>
        </section>
      )}

      {/* Grille des modules */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Modules principaux</h2>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {MODULES.map((mod) => (
            <Link
              key={mod.key}
              to={mod.path}
              className={`group rounded-2xl p-5 flex flex-col justify-between min-h-[140px] ${mod.color} hover:opacity-90 transition-opacity`}
            >
              <mod.icon size={28} className={mod.iconColor} />
              <div>
                <p className="font-semibold mt-4">{mod.label}</p>
                <p className="text-xs text-white/70 mt-1 line-clamp-2">{mod.description}</p>
              </div>
              <ArrowRight
                size={16}
                className="mt-3 text-white/60 group-hover:translate-x-1 transition-transform"
              />
            </Link>
          ))}
        </div>
      </section>

      {/* Widget IA Nexus */}
      <section className="nexus-card p-5 flex items-center gap-4">
        <div className="w-11 h-11 rounded-full bg-nexus-gradient flex items-center justify-center shrink-0">
          <Sparkles size={20} className="text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-medium">IA Nexus</p>
          <p className="text-sm text-nexus-text-muted truncate">
            Bonjour {user?.full_name?.split(" ")[0] || ""}, comment puis-je vous aider aujourd'hui ?
          </p>
        </div>
        <Link to="/ai" className="nexus-btn-secondary text-sm shrink-0">
          Poser une question
        </Link>
      </section>

      {user?.is_superuser && (
        <section className="nexus-card p-4 flex items-center justify-between">
          <p className="text-sm flex items-center gap-2"><ShieldCheck size={16} className="text-nexus-blue" /> Accès administrateur disponible</p>
          <Link to="/admin" className="nexus-btn-secondary text-xs">Ouvrir le Centre d'administration</Link>
        </section>
      )}
    </div>
  );
}
