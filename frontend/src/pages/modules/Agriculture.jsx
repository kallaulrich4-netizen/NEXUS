import { useEffect, useState } from "react";
import {
  Plus, X, Sprout, LayoutDashboard, CalendarDays, Stethoscope, Sparkles,
  Wallet, Check, AlertTriangle, Loader2, DollarSign,
} from "lucide-react";
import { apiRequest } from "../../api/client";

const EMPTY_FIELD = { name: "", area_hectares: "", country: "", soil_type: "" };
const EMPTY_CYCLE = { crop_name: "", planting_date: new Date().toISOString().slice(0, 10), expected_harvest_date: "" };
const EMPTY_ACTIVITY = { activity_type: "irrigation", activity_date: new Date().toISOString().slice(0, 10), cost_amount: "" };

const ACTIVITY_TYPES = [
  "semis", "irrigation", "fertilisation", "traitement_phytosanitaire",
  "desherbage", "recolte", "labour", "autre",
];

export default function Agriculture() {
  const [fields, setFields] = useState([]);
  const [selectedFieldId, setSelectedFieldId] = useState(null);
  const [cycles, setCycles] = useState([]);
  const [selectedCycleId, setSelectedCycleId] = useState(null);

  const [isFieldFormOpen, setIsFieldFormOpen] = useState(false);
  const [fieldForm, setFieldForm] = useState(EMPTY_FIELD);
  const [cycleForm, setCycleForm] = useState(EMPTY_CYCLE);
  const [activityForm, setActivityForm] = useState(EMPTY_ACTIVITY);

  const [dashboard, setDashboard] = useState(null);

  const [recommendations, setRecommendations] = useState([]);
  const [recoForm, setRecoForm] = useState({ season: "pluies", budget_amount: "" });
  const [recoLoading, setRecoLoading] = useState(false);

  const [projection, setProjection] = useState(null);
  const [marketPrice, setMarketPrice] = useState("");
  const [projectionLoading, setProjectionLoading] = useState(false);

  const [calendarTasks, setCalendarTasks] = useState([]);
  const [calendarLoading, setCalendarLoading] = useState(false);

  const [diagnoses, setDiagnoses] = useState([]);
  const [symptoms, setSymptoms] = useState("");
  const [diagnosisLoading, setDiagnosisLoading] = useState(false);

  const [error, setError] = useState("");

  useEffect(() => { loadFields(); loadDashboard(); }, []);
  useEffect(() => {
    if (selectedFieldId) {
      loadCycles(selectedFieldId);
      loadRecommendations(selectedFieldId);
      loadProjection(selectedFieldId);
      setSelectedCycleId(null);
    }
  }, [selectedFieldId]);
  useEffect(() => {
    if (selectedCycleId) {
      loadCalendar(selectedCycleId);
      loadDiagnoses(selectedCycleId);
    }
  }, [selectedCycleId]);

  async function loadFields() {
    try {
      const data = await apiRequest("/agriculture/fields");
      setFields(data);
      if (data.length > 0 && !selectedFieldId) setSelectedFieldId(data[0].id);
    } catch (err) { setError(err.detail || "Impossible de charger les parcelles."); }
  }

  async function loadDashboard() {
    try {
      const data = await apiRequest("/agriculture/dashboard");
      setDashboard(data);
    } catch (err) { setError(err.detail || "Impossible de charger le tableau de bord."); }
  }

  async function loadCycles(fieldId) {
    try {
      const data = await apiRequest(`/agriculture/fields/${fieldId}/crop-cycles`);
      setCycles(data);
      if (data.length > 0) setSelectedCycleId(data[0].id);
    } catch (err) { setError(err.detail || "Impossible de charger les cycles."); }
  }

  async function loadRecommendations(fieldId) {
    try {
      const data = await apiRequest(`/agriculture/fields/${fieldId}/recommendations`);
      setRecommendations(data);
    } catch { setRecommendations([]); }
  }

  async function loadProjection(fieldId) {
    try {
      const data = await apiRequest(`/agriculture/fields/${fieldId}/financial-projection`);
      setProjection(data);
    } catch { setProjection(null); }
  }

  async function loadCalendar(cycleId) {
    try {
      const data = await apiRequest(`/agriculture/crop-cycles/${cycleId}/calendar`);
      setCalendarTasks(data);
    } catch { setCalendarTasks([]); }
  }

  async function loadDiagnoses(cycleId) {
    try {
      const data = await apiRequest(`/agriculture/crop-cycles/${cycleId}/diagnoses`);
      setDiagnoses(data);
    } catch { setDiagnoses([]); }
  }

  async function handleCreateField(e) {
    e.preventDefault();
    try {
      await apiRequest("/agriculture/fields", {
        method: "POST",
        body: { ...fieldForm, area_hectares: Number(fieldForm.area_hectares) },
      });
      setFieldForm(EMPTY_FIELD);
      setIsFieldFormOpen(false);
      loadFields();
      loadDashboard();
    } catch (err) { setError(err.detail || "Impossible de créer la parcelle."); }
  }

  async function handleCreateCycle(e) {
    e.preventDefault();
    if (!selectedFieldId) return;
    try {
      await apiRequest(`/agriculture/fields/${selectedFieldId}/crop-cycles`, {
        method: "POST",
        body: { ...cycleForm, expected_harvest_date: cycleForm.expected_harvest_date || null },
      });
      setCycleForm(EMPTY_CYCLE);
      loadCycles(selectedFieldId);
      loadDashboard();
    } catch (err) { setError(err.detail || "Impossible de créer le cycle."); }
  }

  async function handleAddActivity(e) {
    e.preventDefault();
    if (!selectedCycleId) return;
    try {
      await apiRequest(`/agriculture/crop-cycles/${selectedCycleId}/activities`, {
        method: "POST",
        body: {
          ...activityForm,
          cost_amount: activityForm.cost_amount ? Number(activityForm.cost_amount) : null,
        },
      });
      setActivityForm(EMPTY_ACTIVITY);
      loadDashboard();
    } catch (err) { setError(err.detail || "Impossible d'enregistrer l'activité."); }
  }

  async function handleGenerateRecommendations() {
    if (!selectedFieldId) return;
    setRecoLoading(true);
    setError("");
    try {
      const data = await apiRequest(`/agriculture/fields/${selectedFieldId}/recommendations`, {
        method: "POST",
        body: {
          season: recoForm.season,
          budget_amount: recoForm.budget_amount ? Number(recoForm.budget_amount) : null,
          budget_currency: "XOF",
        },
      });
      setRecommendations(data);
    } catch (err) { setError(err.detail || "Impossible de générer des recommandations."); }
    finally { setRecoLoading(false); }
  }

  async function handleGenerateProjection() {
    if (!selectedFieldId) return;
    setProjectionLoading(true);
    setError("");
    try {
      const data = await apiRequest(`/agriculture/fields/${selectedFieldId}/financial-projection`, {
        method: "POST",
        body: {
          crop_cycle_id: selectedCycleId || null,
          market_price_per_unit: marketPrice ? Number(marketPrice) : 0,
          currency: "XOF",
        },
      });
      setProjection(data);
    } catch (err) { setError(err.detail || "Impossible de calculer la projection."); }
    finally { setProjectionLoading(false); }
  }

  async function handleGenerateCalendar() {
    if (!selectedCycleId) return;
    setCalendarLoading(true);
    setError("");
    try {
      const data = await apiRequest(`/agriculture/crop-cycles/${selectedCycleId}/calendar`, { method: "POST" });
      setCalendarTasks(data);
    } catch (err) { setError(err.detail || "Impossible de générer le calendrier."); }
    finally { setCalendarLoading(false); }
  }

  async function handleMarkTaskDone(taskId) {
    try {
      await apiRequest(`/agriculture/calendar-tasks/${taskId}`, { method: "PATCH", body: { status: "faite" } });
      loadCalendar(selectedCycleId);
    } catch (err) { setError(err.detail || "Impossible de mettre à jour la tâche."); }
  }

  async function handleDiagnose(e) {
    e.preventDefault();
    if (!selectedCycleId || !symptoms.trim()) return;
    setDiagnosisLoading(true);
    setError("");
    try {
      await apiRequest(`/agriculture/crop-cycles/${selectedCycleId}/diagnose`, {
        method: "POST",
        body: { symptoms_description: symptoms },
      });
      setSymptoms("");
      loadDiagnoses(selectedCycleId);
    } catch (err) { setError(err.detail || "Impossible d'obtenir un diagnostic."); }
    finally { setDiagnosisLoading(false); }
  }

  async function handleDownloadReport(format) {
    if (!selectedFieldId) return;
    try {
      const response = await apiRequest(`/agriculture/fields/${selectedFieldId}/report?file_format=${format}`, { rawResponse: true });
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `rapport-culture.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) { setError(err.detail || "Impossible de télécharger le rapport."); }
  }

  const selectedCycle = cycles.find((c) => c.id === selectedCycleId);
  const today = new Date().toISOString().slice(0, 10);

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Agriculture</h1>
        <button onClick={() => setIsFieldFormOpen(true)} className="nexus-btn-primary flex items-center gap-2 text-sm">
          <Plus size={16} /> Nouvelle parcelle
        </button>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      {/* Tableau de bord consolidé */}
      {dashboard && (
        <div className="nexus-card p-5">
          <h2 className="font-medium mb-3 flex items-center gap-2"><LayoutDashboard size={18} /> Tableau de bord</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Stat label="Parcelles" value={dashboard.total_fields} />
            <Stat label="Cycles actifs" value={dashboard.total_active_cycles} />
            <Stat label="Tâches à venir" value={dashboard.total_upcoming_tasks} accent="text-nexus-blue" />
            <Stat label="Tâches en retard" value={dashboard.total_overdue_tasks} accent={dashboard.total_overdue_tasks > 0 ? "text-red-400" : ""} />
          </div>
        </div>
      )}

      <div className="grid md:grid-cols-3 gap-6">
        <div className="nexus-card p-4 space-y-2 h-fit">
          <h2 className="font-medium text-sm text-nexus-text-muted mb-2">Vos parcelles</h2>
          {fields.map((field) => (
            <button
              key={field.id}
              onClick={() => setSelectedFieldId(field.id)}
              className={`w-full text-left px-3 py-2.5 rounded-xl text-sm ${
                selectedFieldId === field.id ? "bg-nexus-gradient text-white" : "hover:bg-nexus-surface-hover"
              }`}
            >
              <p className="font-medium truncate">{field.name}</p>
              <p className="text-xs opacity-70">{field.area_hectares} ha — {field.country}</p>
            </button>
          ))}
          {fields.length === 0 && <p className="text-sm text-nexus-text-muted">Aucune parcelle encore.</p>}

          {selectedFieldId && (
            <div className="pt-2 border-t border-nexus-border">
              <p className="text-xs text-nexus-text-muted mb-1.5">Télécharger le rapport</p>
              <div className="flex flex-wrap gap-1.5">
                {["pdf", "docx", "xlsx", "csv"].map((format) => (
                  <button
                    key={format}
                    onClick={() => handleDownloadReport(format)}
                    className="text-xs px-2 py-1 rounded-lg bg-nexus-surface-hover uppercase"
                  >
                    {format}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="md:col-span-2 space-y-6">
          <div className="nexus-card p-5">
            <h2 className="font-medium mb-3 flex items-center gap-2"><Sprout size={18} /> Nouveau cycle de culture</h2>
            <form onSubmit={handleCreateCycle} className="grid grid-cols-2 gap-3">
              <input required placeholder="Culture (ex: maïs)" value={cycleForm.crop_name} onChange={(e) => setCycleForm((p) => ({ ...p, crop_name: e.target.value }))} className="nexus-input" />
              <input required type="date" value={cycleForm.planting_date} onChange={(e) => setCycleForm((p) => ({ ...p, planting_date: e.target.value }))} className="nexus-input" />
              <input type="date" placeholder="Récolte prévue (optionnel)" value={cycleForm.expected_harvest_date} onChange={(e) => setCycleForm((p) => ({ ...p, expected_harvest_date: e.target.value }))} className="nexus-input col-span-2" />
              <button type="submit" disabled={!selectedFieldId} className="nexus-btn-primary col-span-2">Planifier</button>
            </form>
          </div>

          <div className="nexus-card p-5">
            <h2 className="font-medium mb-3">Cycles de culture</h2>
            <div className="space-y-2">
              {cycles.map((cycle) => (
                <button
                  key={cycle.id}
                  onClick={() => setSelectedCycleId(cycle.id)}
                  className={`w-full flex items-center justify-between text-sm py-2 px-3 rounded-xl ${
                    selectedCycleId === cycle.id ? "bg-nexus-surface-hover ring-1 ring-nexus-blue" : "hover:bg-nexus-surface-hover"
                  }`}
                >
                  <div className="text-left">
                    <p className="font-medium">{cycle.crop_name}</p>
                    <p className="text-xs text-nexus-text-muted">Semé le {cycle.planting_date}</p>
                  </div>
                  <span className="text-xs px-2 py-1 rounded-full bg-nexus-surface-hover capitalize">
                    {cycle.status.replace(/_/g, " ")}
                  </span>
                </button>
              ))}
              {cycles.length === 0 && <p className="text-sm text-nexus-text-muted">Aucun cycle pour cette parcelle.</p>}
            </div>
          </div>

          {/* Recommandations de culture (IA) */}
          <div className="nexus-card p-5">
            <h2 className="font-medium mb-3 flex items-center gap-2"><Sparkles size={18} className="text-nexus-purple" /> Recommandations de culture (IA)</h2>
            <div className="flex flex-wrap gap-2 mb-3">
              <select value={recoForm.season} onChange={(e) => setRecoForm((p) => ({ ...p, season: e.target.value }))} className="nexus-input">
                <option value="pluies">Saison des pluies</option>
                <option value="saison sèche">Saison sèche</option>
                <option value="contre-saison">Contre-saison</option>
              </select>
              <input
                type="number" placeholder="Budget (XOF, optionnel)"
                value={recoForm.budget_amount}
                onChange={(e) => setRecoForm((p) => ({ ...p, budget_amount: e.target.value }))}
                className="nexus-input flex-1 min-w-[160px]"
              />
              <button onClick={handleGenerateRecommendations} disabled={!selectedFieldId || recoLoading} className="nexus-btn-primary text-sm flex items-center gap-2">
                {recoLoading && <Loader2 size={14} className="animate-spin" />} Générer
              </button>
            </div>
            <div className="space-y-2">
              {recommendations.map((reco) => (
                <div key={reco.id} className="p-3 rounded-xl bg-nexus-surface-hover">
                  <div className="flex items-center justify-between mb-1">
                    <p className="font-medium capitalize">{reco.crop_name}</p>
                    <span className="text-xs text-emerald-400">{Math.round(reco.score)}% de pertinence</span>
                  </div>
                  <p className="text-xs text-nexus-text-muted">{reco.rationale}</p>
                </div>
              ))}
              {recommendations.length === 0 && <p className="text-sm text-nexus-text-muted">Aucune recommandation générée pour l'instant.</p>}
            </div>
          </div>

          {/* Projection économique */}
          <div className="nexus-card p-5">
            <h2 className="font-medium mb-3 flex items-center gap-2"><DollarSign size={18} className="text-emerald-400" /> Projection économique</h2>
            <div className="flex flex-wrap gap-2 mb-3">
              <input
                type="number" placeholder="Prix de marché estimé (par unité de rendement)"
                value={marketPrice}
                onChange={(e) => setMarketPrice(e.target.value)}
                className="nexus-input flex-1 min-w-[220px]"
              />
              <button onClick={handleGenerateProjection} disabled={!selectedFieldId || projectionLoading} className="nexus-btn-primary text-sm flex items-center gap-2">
                {projectionLoading && <Loader2 size={14} className="animate-spin" />} Calculer
              </button>
            </div>
            {projection ? (
              <div className="grid grid-cols-3 gap-3">
                <Stat label="Coûts estimés" value={`${Number(projection.estimated_cost_total).toLocaleString("fr-FR")} ${projection.currency}`} small />
                <Stat label="Revenus estimés" value={`${Number(projection.estimated_revenue_total).toLocaleString("fr-FR")} ${projection.currency}`} small />
                <Stat
                  label="Bénéfice estimé"
                  value={`${Number(projection.estimated_profit).toLocaleString("fr-FR")} ${projection.currency}`}
                  accent={projection.estimated_profit >= 0 ? "text-emerald-400" : "text-red-400"}
                  small
                />
              </div>
            ) : (
              <p className="text-sm text-nexus-text-muted">Aucune projection calculée pour cette parcelle.</p>
            )}
          </div>

          {selectedCycle && (
            <>
              {/* Ajouter une activité / dépense */}
              <div className="nexus-card p-5">
                <h2 className="font-medium mb-3">Enregistrer une activité — {selectedCycle.crop_name}</h2>
                <form onSubmit={handleAddActivity} className="grid grid-cols-3 gap-3">
                  <select value={activityForm.activity_type} onChange={(e) => setActivityForm((p) => ({ ...p, activity_type: e.target.value }))} className="nexus-input capitalize">
                    {ACTIVITY_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
                  </select>
                  <input type="date" value={activityForm.activity_date} onChange={(e) => setActivityForm((p) => ({ ...p, activity_date: e.target.value }))} className="nexus-input" />
                  <input type="number" placeholder="Coût (optionnel)" value={activityForm.cost_amount} onChange={(e) => setActivityForm((p) => ({ ...p, cost_amount: e.target.value }))} className="nexus-input" />
                  <button type="submit" className="nexus-btn-primary col-span-3 text-sm">Enregistrer l'activité</button>
                </form>
              </div>

              {/* Calendrier automatique */}
              <div className="nexus-card p-5">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="font-medium flex items-center gap-2"><CalendarDays size={18} className="text-nexus-blue" /> Calendrier — {selectedCycle.crop_name}</h2>
                  <button onClick={handleGenerateCalendar} disabled={calendarLoading} className="nexus-btn-secondary text-xs flex items-center gap-1.5 py-1.5">
                    {calendarLoading && <Loader2 size={13} className="animate-spin" />} Générer / régénérer
                  </button>
                </div>
                <div className="space-y-1.5">
                  {calendarTasks.map((task) => {
                    const isOverdue = task.status === "prevue" && task.due_date < today;
                    return (
                      <div key={task.id} className="flex items-center justify-between text-sm py-2 px-3 rounded-xl bg-nexus-surface-hover">
                        <div className="flex items-center gap-2">
                          {isOverdue && <AlertTriangle size={14} className="text-red-400 shrink-0" />}
                          <div>
                            <p className="font-medium">{task.title}</p>
                            <p className="text-xs text-nexus-text-muted">Prévue le {task.due_date}</p>
                          </div>
                        </div>
                        {task.status === "prevue" ? (
                          <button onClick={() => handleMarkTaskDone(task.id)} className="text-xs px-2.5 py-1 rounded-full bg-nexus-bg hover:bg-emerald-500/20 flex items-center gap-1">
                            <Check size={12} /> Marquer fait
                          </button>
                        ) : (
                          <span className="text-xs px-2 py-1 rounded-full bg-emerald-500/20 text-emerald-400 capitalize">{task.status}</span>
                        )}
                      </div>
                    );
                  })}
                  {calendarTasks.length === 0 && <p className="text-sm text-nexus-text-muted">Aucune tâche générée pour ce cycle.</p>}
                </div>
              </div>

              {/* Diagnostic des maladies */}
              <div className="nexus-card p-5">
                <h2 className="font-medium mb-3 flex items-center gap-2"><Stethoscope size={18} className="text-red-400" /> Diagnostic des maladies — {selectedCycle.crop_name}</h2>
                <form onSubmit={handleDiagnose} className="space-y-2 mb-4">
                  <textarea
                    required
                    placeholder="Décrivez les symptômes observés (taches, flétrissement, décoloration...)"
                    value={symptoms}
                    onChange={(e) => setSymptoms(e.target.value)}
                    className="nexus-input w-full min-h-[80px]"
                  />
                  <button type="submit" disabled={diagnosisLoading} className="nexus-btn-primary text-sm flex items-center gap-2">
                    {diagnosisLoading && <Loader2 size={14} className="animate-spin" />} Obtenir un diagnostic
                  </button>
                </form>
                <div className="space-y-3">
                  {diagnoses.map((d) => (
                    <div key={d.id} className="p-3 rounded-xl bg-nexus-surface-hover text-sm">
                      <p className="text-xs text-nexus-text-muted mb-1">« {d.symptoms_description} »</p>
                      <p className="font-medium">{d.diagnosis_text}</p>
                      <p className="text-xs text-emerald-400 mt-1">{d.recommended_actions}</p>
                    </div>
                  ))}
                  {diagnoses.length === 0 && <p className="text-sm text-nexus-text-muted">Aucun diagnostic pour ce cycle.</p>}
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {isFieldFormOpen && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50">
          <div className="nexus-card w-full max-w-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-lg">Nouvelle parcelle</h2>
              <button onClick={() => setIsFieldFormOpen(false)}><X size={20} /></button>
            </div>
            <form onSubmit={handleCreateField} className="space-y-3">
              <input required placeholder="Nom de la parcelle" value={fieldForm.name} onChange={(e) => setFieldForm((p) => ({ ...p, name: e.target.value }))} className="nexus-input w-full" />
              <input required type="number" step="0.01" placeholder="Superficie (hectares)" value={fieldForm.area_hectares} onChange={(e) => setFieldForm((p) => ({ ...p, area_hectares: e.target.value }))} className="nexus-input w-full" />
              <input required placeholder="Pays" value={fieldForm.country} onChange={(e) => setFieldForm((p) => ({ ...p, country: e.target.value }))} className="nexus-input w-full" />
              <input placeholder="Type de sol (optionnel)" value={fieldForm.soil_type} onChange={(e) => setFieldForm((p) => ({ ...p, soil_type: e.target.value }))} className="nexus-input w-full" />
              {error && <p className="text-sm text-red-400">{error}</p>}
              <button type="submit" className="nexus-btn-primary w-full">Créer</button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, accent = "", small = false }) {
  return (
    <div className="nexus-card p-3 bg-nexus-bg">
      <p className={`${small ? "text-sm" : "text-lg"} font-bold ${accent}`}>{value}</p>
      <p className="text-xs text-nexus-text-muted mt-0.5">{label}</p>
    </div>
  );
}
