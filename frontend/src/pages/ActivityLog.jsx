import { useEffect, useState } from "react";
import { History, Loader2 } from "lucide-react";
import { apiRequest } from "../api/client";
import { useAuth } from "../context/AuthContext";

const ACTION_STYLES = {
  connexion: "bg-nexus-blue/20 text-nexus-blue",
  creation: "bg-emerald-500/20 text-emerald-400",
  modification: "bg-amber-500/20 text-amber-400",
  suppression: "bg-red-500/20 text-red-400",
  autre: "bg-nexus-surface-hover text-nexus-text-muted",
};

const ACTION_LABELS = {
  connexion: "Connexion",
  creation: "Création",
  modification: "Modification",
  suppression: "Suppression",
  autre: "Autre",
};

export default function ActivityLog() {
  const { user } = useAuth();
  const [entries, setEntries] = useState([]);
  const [scope, setScope] = useState("mine");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => { load(); }, [scope]);

  async function load() {
    setIsLoading(true);
    setError("");
    try {
      const path = scope === "all" ? "/activity-log/all" : "/activity-log/mine";
      setEntries(await apiRequest(path));
    } catch (err) {
      setError(err.detail || "Impossible de charger le journal d'activité.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold flex items-center gap-2"><History size={20} /> Journal d'activité</h1>
        {user?.is_superuser && (
          <div className="flex gap-2">
            {[{ key: "mine", label: "Mon activité" }, { key: "all", label: "Toute la plateforme" }].map((tab) => (
              <button
                key={tab.key}
                onClick={() => setScope(tab.key)}
                className={`text-sm px-3 py-1.5 rounded-full ${
                  scope === tab.key ? "bg-nexus-gradient text-white" : "bg-nexus-surface-hover text-nexus-text-muted"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      {isLoading ? (
        <div className="flex items-center justify-center py-16 text-nexus-text-muted">
          <Loader2 className="animate-spin mr-2" size={18} /> Chargement...
        </div>
      ) : (
        <div className="nexus-card divide-y divide-nexus-border">
          {entries.map((entry) => (
            <div key={entry.id} className="p-4 flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="text-sm font-medium truncate">{entry.description}</p>
                <p className="text-xs text-nexus-text-muted capitalize mt-0.5">
                  {entry.module} — {new Date(entry.created_at).toLocaleString("fr-FR")}
                </p>
              </div>
              <span className={`text-xs px-2 py-1 rounded-full shrink-0 ${ACTION_STYLES[entry.action] || ACTION_STYLES.autre}`}>
                {ACTION_LABELS[entry.action] || entry.action}
              </span>
            </div>
          ))}
          {entries.length === 0 && (
            <p className="text-center text-nexus-text-muted py-12 text-sm">Aucune activité enregistrée.</p>
          )}
        </div>
      )}
    </div>
  );
}
