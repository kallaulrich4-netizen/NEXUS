import { useEffect, useState } from "react";
import { Bell, Check, CheckCheck, Loader2 } from "lucide-react";
import { Link } from "react-router-dom";
import { apiRequest } from "../api/client";

const CATEGORY_STYLES = {
  info: "bg-nexus-surface-hover text-nexus-text-muted",
  alerte: "bg-red-500/20 text-red-400",
  rappel: "bg-amber-500/20 text-amber-400",
  recommandation_ia: "bg-nexus-purple/20 text-nexus-purple",
  echeance: "bg-amber-500/20 text-amber-400",
  confirmation: "bg-emerald-500/20 text-emerald-400",
};

const CATEGORY_LABELS = {
  info: "Info",
  alerte: "Alerte",
  rappel: "Rappel",
  recommandation_ia: "Recommandation IA",
  echeance: "Échéance",
  confirmation: "Confirmation",
};

export default function Notifications() {
  const [notifications, setNotifications] = useState([]);
  const [filter, setFilter] = useState("all");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => { load(); }, [filter]);

  async function load() {
    setIsLoading(true);
    try {
      const query = filter === "unread" ? "?unread_only=true" : "";
      setNotifications(await apiRequest(`/notifications${query}`));
    } catch (err) {
      setError(err.detail || "Impossible de charger les notifications.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleMarkRead(id) {
    try {
      await apiRequest(`/notifications/${id}/read`, { method: "POST" });
      setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
    } catch (err) { setError(err.detail || "Impossible de marquer comme lu."); }
  }

  async function handleMarkAllRead() {
    try {
      await apiRequest("/notifications/read-all", { method: "POST" });
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch (err) { setError(err.detail || "Impossible de tout marquer comme lu."); }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold flex items-center gap-2"><Bell size={20} /> Notifications</h1>
        <button onClick={handleMarkAllRead} className="nexus-btn-secondary text-xs flex items-center gap-1.5 py-1.5">
          <CheckCheck size={14} /> Tout marquer comme lu
        </button>
      </div>

      <div className="flex gap-2">
        {[{ key: "all", label: "Toutes" }, { key: "unread", label: "Non lues" }].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setFilter(tab.key)}
            className={`text-sm px-3 py-1.5 rounded-full ${
              filter === tab.key ? "bg-nexus-gradient text-white" : "bg-nexus-surface-hover text-nexus-text-muted"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      {isLoading ? (
        <div className="flex items-center justify-center py-16 text-nexus-text-muted">
          <Loader2 className="animate-spin mr-2" size={18} /> Chargement...
        </div>
      ) : (
        <div className="nexus-card divide-y divide-nexus-border">
          {notifications.map((n) => (
            <div key={n.id} className={`p-4 flex items-start gap-3 ${!n.is_read ? "bg-nexus-surface-hover" : ""}`}>
              <span className={`text-xs px-2 py-1 rounded-full shrink-0 ${CATEGORY_STYLES[n.category] || CATEGORY_STYLES.info}`}>
                {CATEGORY_LABELS[n.category] || n.category}
              </span>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-sm">{n.title}</p>
                <p className="text-xs text-nexus-text-muted mt-0.5">{n.message}</p>
                <div className="flex items-center gap-3 mt-1.5">
                  <p className="text-[11px] text-nexus-text-muted">
                    {new Date(n.created_at).toLocaleString("fr-FR")}
                  </p>
                  {n.link && (
                    <Link to={n.link} className="text-[11px] text-nexus-blue">Consulter</Link>
                  )}
                </div>
              </div>
              {!n.is_read && (
                <button onClick={() => handleMarkRead(n.id)} className="text-nexus-text-muted hover:text-emerald-400 shrink-0">
                  <Check size={16} />
                </button>
              )}
            </div>
          ))}
          {notifications.length === 0 && (
            <p className="text-center text-nexus-text-muted py-12 text-sm">Aucune notification.</p>
          )}
        </div>
      )}
    </div>
  );
}
