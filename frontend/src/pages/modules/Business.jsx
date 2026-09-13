import { useEffect, useState } from "react";
import { Plus, X, Briefcase } from "lucide-react";
import { apiRequest } from "../../api/client";

const EMPTY_FORM = { name: "", sector: "", country: "", city: "" };

export default function Business() {
  const [companies, setCompanies] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState("");

  useEffect(() => { loadCompanies(); }, []);
  useEffect(() => { if (selectedId) loadDashboard(selectedId); }, [selectedId]);

  async function loadCompanies() {
    try {
      const data = await apiRequest("/business/companies");
      setCompanies(data);
      if (data.length > 0 && !selectedId) setSelectedId(data[0].id);
    } catch (err) { setError(err.detail || "Impossible de charger les entreprises."); }
  }

  async function loadDashboard(companyId) {
    try {
      const data = await apiRequest(`/business/companies/${companyId}/dashboard`);
      setDashboard(data);
    } catch (err) { setError(err.detail || "Impossible de charger le tableau de bord."); }
  }

  async function handleCreate(e) {
    e.preventDefault();
    try {
      await apiRequest("/business/companies", { method: "POST", body: form });
      setForm(EMPTY_FORM);
      setIsFormOpen(false);
      loadCompanies();
    } catch (err) { setError(err.detail || "Impossible de créer l'entreprise."); }
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold flex items-center gap-2"><Briefcase size={22} /> Gestion d'entreprise</h1>
        <button onClick={() => setIsFormOpen(true)} className="nexus-btn-primary flex items-center gap-2 text-sm">
          <Plus size={16} /> Nouvelle entreprise
        </button>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <div className="grid md:grid-cols-3 gap-6">
        <div className="nexus-card p-4 space-y-2">
          <h2 className="font-medium text-sm text-nexus-text-muted mb-2">Vos entreprises</h2>
          {companies.map((c) => (
            <button
              key={c.id}
              onClick={() => setSelectedId(c.id)}
              className={`w-full text-left px-3 py-2.5 rounded-xl text-sm ${
                selectedId === c.id ? "bg-nexus-gradient text-white" : "hover:bg-nexus-surface-hover"
              }`}
            >
              <p className="font-medium truncate">{c.name}</p>
              <p className="text-xs opacity-70 capitalize">{c.sector}</p>
            </button>
          ))}
          {companies.length === 0 && <p className="text-sm text-nexus-text-muted">Aucune entreprise encore.</p>}
        </div>

        <div className="md:col-span-2">
          {dashboard && (
            <div className="grid grid-cols-2 gap-4">
              <div className="nexus-card p-4">
                <p className="text-xs text-nexus-text-muted">Employés</p>
                <p className="text-2xl font-bold">{dashboard.total_employees}</p>
                <p className="text-xs text-nexus-text-muted">{dashboard.active_employees} actifs</p>
              </div>
              <div className="nexus-card p-4">
                <p className="text-xs text-nexus-text-muted">Clients</p>
                <p className="text-2xl font-bold">{dashboard.total_clients}</p>
              </div>
              <div className="nexus-card p-4">
                <p className="text-xs text-nexus-text-muted">Total facturé</p>
                <p className="text-2xl font-bold">{dashboard.total_invoiced.toLocaleString("fr-FR")}</p>
              </div>
              <div className="nexus-card p-4">
                <p className="text-xs text-nexus-text-muted">En attente de paiement</p>
                <p className="text-2xl font-bold">{dashboard.total_outstanding.toLocaleString("fr-FR")}</p>
              </div>
            </div>
          )}
          {!dashboard && <p className="text-sm text-nexus-text-muted">Sélectionnez une entreprise pour voir son tableau de bord.</p>}
        </div>
      </div>

      {isFormOpen && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50">
          <div className="nexus-card w-full max-w-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-lg">Nouvelle entreprise</h2>
              <button onClick={() => setIsFormOpen(false)}><X size={20} /></button>
            </div>
            <form onSubmit={handleCreate} className="space-y-3">
              <input required placeholder="Nom" value={form.name} onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))} className="nexus-input w-full" />
              <input required placeholder="Secteur (ex: commerce, BTP...)" value={form.sector} onChange={(e) => setForm((p) => ({ ...p, sector: e.target.value }))} className="nexus-input w-full" />
              <input required placeholder="Pays" value={form.country} onChange={(e) => setForm((p) => ({ ...p, country: e.target.value }))} className="nexus-input w-full" />
              <input placeholder="Ville (optionnel)" value={form.city} onChange={(e) => setForm((p) => ({ ...p, city: e.target.value }))} className="nexus-input w-full" />
              {error && <p className="text-sm text-red-400">{error}</p>}
              <button type="submit" className="nexus-btn-primary w-full">Créer</button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
