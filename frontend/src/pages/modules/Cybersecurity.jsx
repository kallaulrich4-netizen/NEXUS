import { useEffect, useState } from "react";
import { Plus, X, ShieldCheck } from "lucide-react";
import { apiRequest } from "../../api/client";

const EMPTY_ASSET = { name: "", asset_type: "site_web", identifier: "" };

export default function Cybersecurity() {
  const [assets, setAssets] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_ASSET);
  const [error, setError] = useState("");

  useEffect(() => { loadAssets(); }, []);
  useEffect(() => { if (selectedId) loadDashboard(selectedId); }, [selectedId]);

  async function loadAssets() {
    try {
      const data = await apiRequest("/cybersecurity/assets");
      setAssets(data);
      if (data.length > 0 && !selectedId) setSelectedId(data[0].id);
    } catch (err) { setError(err.detail || "Impossible de charger les actifs."); }
  }

  async function loadDashboard(assetId) {
    try {
      const data = await apiRequest(`/cybersecurity/assets/${assetId}/risk-dashboard`);
      setDashboard(data);
    } catch (err) { setError(err.detail || "Impossible de charger le tableau de bord."); }
  }

  async function handleCreate(e) {
    e.preventDefault();
    try {
      await apiRequest("/cybersecurity/assets", { method: "POST", body: form });
      setForm(EMPTY_ASSET);
      setIsFormOpen(false);
      loadAssets();
    } catch (err) { setError(err.detail || "Impossible de créer l'actif."); }
  }

  async function requestAudit() {
    if (!selectedId) return;
    try {
      await apiRequest(`/cybersecurity/assets/${selectedId}/audits`, {
        method: "POST",
        body: { ownership_confirmed: true },
      });
      setError("");
      loadDashboard(selectedId);
    } catch (err) { setError(err.detail || "Impossible de créer la demande d'audit."); }
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold flex items-center gap-2"><ShieldCheck size={22} /> Cybersécurité</h1>
        <button onClick={() => setIsFormOpen(true)} className="nexus-btn-primary flex items-center gap-2 text-sm">
          <Plus size={16} /> Nouvel actif
        </button>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <div className="grid md:grid-cols-3 gap-6">
        <div className="nexus-card p-4 space-y-2">
          <h2 className="font-medium text-sm text-nexus-text-muted mb-2">Vos actifs</h2>
          {assets.map((a) => (
            <button
              key={a.id}
              onClick={() => setSelectedId(a.id)}
              className={`w-full text-left px-3 py-2.5 rounded-xl text-sm ${
                selectedId === a.id ? "bg-nexus-gradient text-white" : "hover:bg-nexus-surface-hover"
              }`}
            >
              <p className="font-medium truncate">{a.name}</p>
              <p className="text-xs opacity-70 capitalize">{a.asset_type.replace(/_/g, " ")}</p>
            </button>
          ))}
          {assets.length === 0 && <p className="text-sm text-nexus-text-muted">Aucun actif encore.</p>}
        </div>

        <div className="md:col-span-2 space-y-6">
          <button onClick={requestAudit} disabled={!selectedId} className="nexus-btn-secondary text-sm">
            Demander un audit (avec confirmation de propriété)
          </button>

          {dashboard && (
            <div className="grid grid-cols-2 gap-4">
              <div className="nexus-card p-4">
                <p className="text-xs text-nexus-text-muted">Constats totaux</p>
                <p className="text-2xl font-bold">{dashboard.total_findings}</p>
              </div>
              <div className="nexus-card p-4">
                <p className="text-xs text-nexus-text-muted">Critiques ouverts</p>
                <p className="text-2xl font-bold text-red-400">{dashboard.critical_open_count}</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {isFormOpen && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50">
          <div className="nexus-card w-full max-w-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-lg">Nouvel actif</h2>
              <button onClick={() => setIsFormOpen(false)}><X size={20} /></button>
            </div>
            <form onSubmit={handleCreate} className="space-y-3">
              <input required placeholder="Nom" value={form.name} onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))} className="nexus-input w-full" />
              <select value={form.asset_type} onChange={(e) => setForm((p) => ({ ...p, asset_type: e.target.value }))} className="nexus-input w-full">
                <option value="site_web">Site web</option>
                <option value="application_mobile">Application mobile</option>
                <option value="serveur">Serveur</option>
                <option value="base_de_donnees">Base de données</option>
                <option value="api">API</option>
              </select>
              <input required placeholder="Identifiant (URL, IP...)" value={form.identifier} onChange={(e) => setForm((p) => ({ ...p, identifier: e.target.value }))} className="nexus-input w-full" />
              {error && <p className="text-sm text-red-400">{error}</p>}
              <button type="submit" className="nexus-btn-primary w-full">Créer</button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
