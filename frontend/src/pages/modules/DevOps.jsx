import { useEffect, useState } from "react";
import { Plus, X, Cloud, Activity, DatabaseBackup, Play, Loader2 } from "lucide-react";
import { apiRequest } from "../../api/client";

const EMPTY_FORM = { name: "", resource_type: "", provider: "" };

export default function DevOps() {
  const [resources, setResources] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState("");

  const [systemHealth, setSystemHealth] = useState(null);
  const [backups, setBackups] = useState([]);
  const [backupLoading, setBackupLoading] = useState(false);

  useEffect(() => {
    loadResources();
    loadDashboard();
    loadSystemHealth();
    loadBackups();
  }, []);

  async function loadSystemHealth() {
    try { setSystemHealth(await apiRequest("/devops/system-health")); }
    catch { setSystemHealth(null); }
  }

  async function loadBackups() {
    try { setBackups(await apiRequest("/devops/backups")); }
    catch { setBackups([]); }
  }

  async function handleScheduleBackup() {
    setBackupLoading(true);
    try {
      await apiRequest("/devops/backups", { method: "POST", body: { backup_type: "complete" } });
      loadBackups();
    } catch (err) { setError(err.detail || "Impossible de planifier la sauvegarde."); }
    finally { setBackupLoading(false); }
  }

  async function handleRunBackup(backupId) {
    try {
      await apiRequest(`/devops/backups/${backupId}/run`, { method: "POST" });
      loadBackups();
    } catch (err) { setError(err.detail || "Impossible d'exécuter la sauvegarde."); }
  }

  async function loadResources() {
    try {
      const data = await apiRequest("/devops/resources");
      setResources(data);
    } catch (err) { setError(err.detail || "Impossible de charger les ressources."); }
  }

  async function loadDashboard() {
    try {
      const data = await apiRequest("/devops/dashboard");
      setDashboard(data);
    } catch {
      // Tableau de bord vide si aucune ressource n'existe encore.
    }
  }

  async function handleCreate(e) {
    e.preventDefault();
    try {
      await apiRequest("/devops/resources", { method: "POST", body: form });
      setForm(EMPTY_FORM);
      setIsFormOpen(false);
      loadResources();
      loadDashboard();
    } catch (err) { setError(err.detail || "Impossible de créer la ressource."); }
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold flex items-center gap-2"><Cloud size={22} /> DevOps / Cloud</h1>
        <button onClick={() => setIsFormOpen(true)} className="nexus-btn-primary flex items-center gap-2 text-sm">
          <Plus size={16} /> Nouvelle ressource
        </button>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      {/* Monitoring système */}
      <div className="nexus-card p-5">
        <h2 className="font-medium mb-3 flex items-center gap-2"><Activity size={18} className="text-emerald-400" /> Supervision système</h2>
        {systemHealth ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="nexus-card p-3 bg-nexus-bg">
              <p className={`text-sm font-bold capitalize ${
                systemHealth.status === "operationnel" ? "text-emerald-400" : systemHealth.status === "degrade" ? "text-amber-400" : "text-red-400"
              }`}>{systemHealth.status}</p>
              <p className="text-xs text-nexus-text-muted mt-0.5">Statut</p>
            </div>
            <div className="nexus-card p-3 bg-nexus-bg">
              <p className="text-sm font-bold">{systemHealth.cpu_percent != null ? `${systemHealth.cpu_percent.toFixed(0)}%` : "—"}</p>
              <p className="text-xs text-nexus-text-muted mt-0.5">Processeur</p>
            </div>
            <div className="nexus-card p-3 bg-nexus-bg">
              <p className="text-sm font-bold">{systemHealth.memory_percent != null ? `${systemHealth.memory_percent.toFixed(0)}%` : "—"}</p>
              <p className="text-xs text-nexus-text-muted mt-0.5">Mémoire</p>
            </div>
            <div className="nexus-card p-3 bg-nexus-bg">
              <p className="text-sm font-bold">{systemHealth.disk_percent != null ? `${systemHealth.disk_percent.toFixed(0)}%` : "—"}</p>
              <p className="text-xs text-nexus-text-muted mt-0.5">Stockage</p>
            </div>
          </div>
        ) : (
          <p className="text-sm text-nexus-text-muted">Impossible de récupérer les métriques système.</p>
        )}
        {systemHealth?.metrics_source === "estimation" && (
          <p className="text-xs text-nexus-text-muted mt-2">
            Métriques indicatives (installez `psutil` côté serveur pour des chiffres précis).
          </p>
        )}
      </div>

      {/* Sauvegardes */}
      <div className="nexus-card p-5">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-medium flex items-center gap-2"><DatabaseBackup size={18} className="text-nexus-blue" /> Sauvegardes</h2>
          <button onClick={handleScheduleBackup} disabled={backupLoading} className="nexus-btn-secondary text-xs flex items-center gap-1.5 py-1.5">
            {backupLoading && <Loader2 size={13} className="animate-spin" />} Planifier une sauvegarde
          </button>
        </div>
        <div className="space-y-1.5">
          {backups.map((b) => (
            <div key={b.id} className="flex items-center justify-between text-sm py-2 px-3 rounded-xl bg-nexus-surface-hover">
              <div>
                <p className="font-medium capitalize">{b.backup_type}</p>
                <p className="text-xs text-nexus-text-muted">
                  Planifiée le {new Date(b.scheduled_at).toLocaleString("fr-FR")}
                  {b.executed_at && ` — exécutée le ${new Date(b.executed_at).toLocaleString("fr-FR")}`}
                </p>
              </div>
              {b.status === "planifiee" ? (
                <button onClick={() => handleRunBackup(b.id)} className="text-xs px-2.5 py-1 rounded-full bg-nexus-bg hover:bg-emerald-500/20 flex items-center gap-1">
                  <Play size={12} /> Exécuter
                </button>
              ) : (
                <span className={`text-xs px-2 py-1 rounded-full capitalize ${
                  b.status === "reussie" ? "bg-emerald-500/20 text-emerald-400" : "bg-red-500/20 text-red-400"
                }`}>{b.status}</span>
              )}
            </div>
          ))}
          {backups.length === 0 && <p className="text-sm text-nexus-text-muted">Aucune sauvegarde planifiée.</p>}
        </div>
      </div>

      {dashboard && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="nexus-card p-4">
            <p className="text-xs text-nexus-text-muted">Ressources totales</p>
            <p className="text-2xl font-bold">{dashboard.total_resources}</p>
          </div>
          {Object.entries(dashboard.open_alerts_by_severity).map(([severity, count]) => (
            <div key={severity} className="nexus-card p-4">
              <p className="text-xs text-nexus-text-muted capitalize">Alertes {severity}</p>
              <p className="text-2xl font-bold text-red-400">{count}</p>
            </div>
          ))}
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-4">
        {resources.map((r) => (
          <article key={r.id} className="nexus-card p-4">
            <div className="flex items-center justify-between">
              <h3 className="font-medium">{r.name}</h3>
              <span className="text-xs px-2 py-1 rounded-full bg-nexus-surface-hover capitalize">{r.status}</span>
            </div>
            <p className="text-xs text-nexus-text-muted mt-1 capitalize">
              {r.resource_type.replace(/_/g, " ")} — {r.provider.toUpperCase()} {r.region ? `(${r.region})` : ""}
            </p>
          </article>
        ))}
        {resources.length === 0 && (
          <p className="col-span-full text-center text-nexus-text-muted py-12">Aucune ressource pour l'instant.</p>
        )}
      </div>

      {isFormOpen && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50">
          <div className="nexus-card w-full max-w-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-lg">Nouvelle ressource</h2>
              <button onClick={() => setIsFormOpen(false)}><X size={20} /></button>
            </div>
            <form onSubmit={handleCreate} className="space-y-3">
              <input required placeholder="Nom" value={form.name} onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))} className="nexus-input w-full" />
              <input required placeholder="Type (serveur, conteneur, cluster...)" value={form.resource_type} onChange={(e) => setForm((p) => ({ ...p, resource_type: e.target.value }))} className="nexus-input w-full" />
              <input required placeholder="Fournisseur (aws, gcp, azure...)" value={form.provider} onChange={(e) => setForm((p) => ({ ...p, provider: e.target.value }))} className="nexus-input w-full" />
              {error && <p className="text-sm text-red-400">{error}</p>}
              <button type="submit" className="nexus-btn-primary w-full">Créer</button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
