import { useEffect, useState } from "react";
import {
  Plus, X, Heart, Users, Wheat, Wallet, TrendingUp, Baby, Syringe,
  Loader2, ChevronRight, ArrowLeft,
} from "lucide-react";
import { apiRequest } from "../../api/client";

const EMPTY_HERD = { name: "", species: "", current_count: "0", country: "" };
const EMPTY_EVENT = { event_type: "vaccination", event_date: new Date().toISOString().slice(0, 10), count_change: "0" };
const EMPTY_ANIMAL = { tag: "", sex: "inconnu", breed: "", birth_date: "" };
const EMPTY_HEALTH_RECORD = { record_type: "vaccination", record_date: new Date().toISOString().slice(0, 10), cost_amount: "" };
const EMPTY_WEIGHT = { weight_kg: "", measured_at: new Date().toISOString().slice(0, 10) };
const EMPTY_REPRODUCTION = { event_type: "chaleurs", event_date: new Date().toISOString().slice(0, 10) };
const EMPTY_BIRTH = { event_date: new Date().toISOString().slice(0, 10), offspring_count: "1", offspring_sex: "inconnu" };

export default function Livestock() {
  const [herds, setHerds] = useState([]);
  const [selectedHerdId, setSelectedHerdId] = useState(null);
  const [events, setEvents] = useState([]);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [herdForm, setHerdForm] = useState(EMPTY_HERD);
  const [eventForm, setEventForm] = useState(EMPTY_EVENT);
  const [error, setError] = useState("");

  const [animals, setAnimals] = useState([]);
  const [selectedAnimalId, setSelectedAnimalId] = useState(null);
  const [animalForm, setAnimalForm] = useState(EMPTY_ANIMAL);
  const [isAnimalFormOpen, setIsAnimalFormOpen] = useState(false);

  const [healthRecords, setHealthRecords] = useState([]);
  const [healthForm, setHealthForm] = useState(EMPTY_HEALTH_RECORD);

  const [growth, setGrowth] = useState(null);
  const [weightForm, setWeightForm] = useState(EMPTY_WEIGHT);

  const [reproductionRecords, setReproductionRecords] = useState([]);
  const [reproForm, setReproForm] = useState(EMPTY_REPRODUCTION);
  const [birthForm, setBirthForm] = useState(EMPTY_BIRTH);
  const [showBirthForm, setShowBirthForm] = useState(false);

  const [feedPlan, setFeedPlan] = useState(null);
  const [feedLoading, setFeedLoading] = useState(false);
  const [economics, setEconomics] = useState(null);

  useEffect(() => { loadHerds(); }, []);
  useEffect(() => {
    if (selectedHerdId) {
      loadEvents(selectedHerdId);
      loadAnimals(selectedHerdId);
      loadFeedPlan(selectedHerdId);
      loadEconomics(selectedHerdId);
      setSelectedAnimalId(null);
    }
  }, [selectedHerdId]);
  useEffect(() => {
    if (selectedAnimalId) {
      loadHealthRecords(selectedAnimalId);
      loadGrowth(selectedAnimalId);
      loadReproduction(selectedAnimalId);
    }
  }, [selectedAnimalId]);

  async function loadHerds() {
    try {
      const data = await apiRequest("/livestock/herds");
      setHerds(data);
      if (data.length > 0 && !selectedHerdId) setSelectedHerdId(data[0].id);
    } catch (err) { setError(err.detail || "Impossible de charger les troupeaux."); }
  }

  async function loadEvents(herdId) {
    try {
      setEvents(await apiRequest(`/livestock/herds/${herdId}/health-events`));
    } catch (err) { setError(err.detail || "Impossible de charger les événements."); }
  }

  async function loadAnimals(herdId) {
    try {
      setAnimals(await apiRequest(`/livestock/herds/${herdId}/animals`));
    } catch (err) { setError(err.detail || "Impossible de charger les animaux."); }
  }

  async function loadFeedPlan(herdId) {
    try { setFeedPlan(await apiRequest(`/livestock/herds/${herdId}/feed-plan`)); }
    catch { setFeedPlan(null); }
  }

  async function loadEconomics(herdId) {
    try { setEconomics(await apiRequest(`/livestock/herds/${herdId}/economics`)); }
    catch { setEconomics(null); }
  }

  async function loadHealthRecords(animalId) {
    try { setHealthRecords(await apiRequest(`/livestock/animals/${animalId}/health-records`)); }
    catch { setHealthRecords([]); }
  }

  async function loadGrowth(animalId) {
    try { setGrowth(await apiRequest(`/livestock/animals/${animalId}/growth-summary`)); }
    catch { setGrowth(null); }
  }

  async function loadReproduction(animalId) {
    try { setReproductionRecords(await apiRequest(`/livestock/animals/${animalId}/reproduction-records`)); }
    catch { setReproductionRecords([]); }
  }

  async function handleCreateHerd(e) {
    e.preventDefault();
    try {
      await apiRequest("/livestock/herds", {
        method: "POST",
        body: { ...herdForm, current_count: Number(herdForm.current_count) },
      });
      setHerdForm(EMPTY_HERD);
      setIsFormOpen(false);
      loadHerds();
    } catch (err) { setError(err.detail || "Impossible de créer le troupeau."); }
  }

  async function handleAddEvent(e) {
    e.preventDefault();
    if (!selectedHerdId) return;
    try {
      await apiRequest(`/livestock/herds/${selectedHerdId}/health-events`, {
        method: "POST",
        body: { ...eventForm, count_change: Number(eventForm.count_change) },
      });
      setEventForm(EMPTY_EVENT);
      loadEvents(selectedHerdId);
      loadHerds();
      loadEconomics(selectedHerdId);
    } catch (err) { setError(err.detail || "Impossible d'ajouter l'événement."); }
  }

  async function handleCreateAnimal(e) {
    e.preventDefault();
    if (!selectedHerdId) return;
    try {
      await apiRequest(`/livestock/herds/${selectedHerdId}/animals`, {
        method: "POST",
        body: { ...animalForm, birth_date: animalForm.birth_date || null, breed: animalForm.breed || null },
      });
      setAnimalForm(EMPTY_ANIMAL);
      setIsAnimalFormOpen(false);
      loadAnimals(selectedHerdId);
    } catch (err) { setError(err.detail || "Impossible de créer la fiche animal."); }
  }

  async function handleUpdateAnimalStatus(status) {
    if (!selectedAnimalId) return;
    try {
      await apiRequest(`/livestock/animals/${selectedAnimalId}`, { method: "PATCH", body: { status } });
      loadAnimals(selectedHerdId);
      loadEconomics(selectedHerdId);
    } catch (err) { setError(err.detail || "Impossible de mettre à jour l'animal."); }
  }

  async function handleAddHealthRecord(e) {
    e.preventDefault();
    if (!selectedAnimalId) return;
    try {
      await apiRequest(`/livestock/animals/${selectedAnimalId}/health-records`, {
        method: "POST",
        body: { ...healthForm, cost_amount: healthForm.cost_amount ? Number(healthForm.cost_amount) : null },
      });
      setHealthForm(EMPTY_HEALTH_RECORD);
      loadHealthRecords(selectedAnimalId);
      loadEconomics(selectedHerdId);
    } catch (err) { setError(err.detail || "Impossible d'ajouter le suivi sanitaire."); }
  }

  async function handleAddWeight(e) {
    e.preventDefault();
    if (!selectedAnimalId) return;
    try {
      await apiRequest(`/livestock/animals/${selectedAnimalId}/weight-records`, {
        method: "POST",
        body: { ...weightForm, weight_kg: Number(weightForm.weight_kg) },
      });
      setWeightForm(EMPTY_WEIGHT);
      loadGrowth(selectedAnimalId);
    } catch (err) { setError(err.detail || "Impossible d'ajouter le relevé de poids."); }
  }

  async function handleAddReproduction(e) {
    e.preventDefault();
    if (!selectedAnimalId) return;
    try {
      await apiRequest(`/livestock/animals/${selectedAnimalId}/reproduction-records`, {
        method: "POST",
        body: reproForm,
      });
      setReproForm(EMPTY_REPRODUCTION);
      loadReproduction(selectedAnimalId);
    } catch (err) { setError(err.detail || "Impossible d'ajouter l'événement de reproduction."); }
  }

  async function handleDeclareBirth(e) {
    e.preventDefault();
    if (!selectedAnimalId) return;
    try {
      await apiRequest(`/livestock/animals/${selectedAnimalId}/declare-birth`, {
        method: "POST",
        body: { ...birthForm, offspring_count: Number(birthForm.offspring_count) },
      });
      setBirthForm(EMPTY_BIRTH);
      setShowBirthForm(false);
      loadReproduction(selectedAnimalId);
      loadAnimals(selectedHerdId);
      loadHerds();
    } catch (err) { setError(err.detail || "Impossible de déclarer la mise bas."); }
  }

  async function handleGenerateFeedPlan() {
    if (!selectedHerdId) return;
    setFeedLoading(true);
    try {
      setFeedPlan(await apiRequest(`/livestock/herds/${selectedHerdId}/feed-plan`, { method: "POST", body: {} }));
    } catch (err) { setError(err.detail || "Impossible de générer le plan alimentaire."); }
    finally { setFeedLoading(false); }
  }

  async function handleDownloadAnimalReport(format) {
    if (!selectedAnimalId) return;
    try {
      const response = await apiRequest(`/livestock/animals/${selectedAnimalId}/report?file_format=${format}`, { rawResponse: true });
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `fiche-animal.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) { setError(err.detail || "Impossible de télécharger la fiche."); }
  }

  const selectedHerd = herds.find((h) => h.id === selectedHerdId);
  const selectedAnimal = animals.find((a) => a.id === selectedAnimalId);

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Élevage</h1>
        <button onClick={() => setIsFormOpen(true)} className="nexus-btn-primary flex items-center gap-2 text-sm">
          <Plus size={16} /> Nouveau troupeau
        </button>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <div className="grid md:grid-cols-3 gap-6">
        <div className="nexus-card p-4 space-y-2 h-fit">
          <h2 className="font-medium text-sm text-nexus-text-muted mb-2">Vos troupeaux</h2>
          {herds.map((herd) => (
            <button
              key={herd.id}
              onClick={() => setSelectedHerdId(herd.id)}
              className={`w-full text-left px-3 py-2.5 rounded-xl text-sm ${
                selectedHerdId === herd.id ? "bg-nexus-gradient text-white" : "hover:bg-nexus-surface-hover"
              }`}
            >
              <p className="font-medium truncate capitalize">{herd.name}</p>
              <p className="text-xs opacity-70">{herd.current_count} têtes — {herd.species}</p>
            </button>
          ))}
          {herds.length === 0 && <p className="text-sm text-nexus-text-muted">Aucun troupeau encore.</p>}
        </div>

        <div className="md:col-span-2 space-y-6">
          {selectedHerd && !selectedAnimal && (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <Stat label="Effectif" value={`${selectedHerd.current_count} têtes`} />
                {economics && (
                  <>
                    <Stat label="Coûts cumulés" value={`${Number(economics.total_cost).toLocaleString("fr-FR")} ${economics.currency}`} />
                    <Stat label="Valeur estimée" value={`${Number(economics.estimated_herd_value).toLocaleString("fr-FR")} ${economics.currency}`} />
                    <Stat
                      label="Bénéfice net"
                      value={`${Number(economics.net_profit).toLocaleString("fr-FR")} ${economics.currency}`}
                      accent={economics.net_profit >= 0 ? "text-emerald-400" : "text-red-400"}
                    />
                  </>
                )}
              </div>

              {/* Plan alimentaire */}
              <div className="nexus-card p-5">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="font-medium flex items-center gap-2"><Wheat size={18} className="text-amber-400" /> Plan alimentaire</h2>
                  <button onClick={handleGenerateFeedPlan} disabled={feedLoading} className="nexus-btn-secondary text-xs flex items-center gap-1.5 py-1.5">
                    {feedLoading && <Loader2 size={13} className="animate-spin" />} Générer / mettre à jour
                  </button>
                </div>
                {feedPlan ? (
                  <div className="grid grid-cols-3 gap-3 text-sm">
                    <Stat label="Aliment" value={feedPlan.feed_type} small />
                    <Stat label="Quantité / jour" value={`${feedPlan.daily_quantity_kg.toFixed(1)} kg`} small />
                    <Stat label="Coût / jour" value={`${Number(feedPlan.estimated_daily_cost).toLocaleString("fr-FR")} ${feedPlan.currency}`} small />
                  </div>
                ) : (
                  <p className="text-sm text-nexus-text-muted">Aucun plan alimentaire généré pour ce troupeau.</p>
                )}
              </div>

              {/* Événements sanitaires du troupeau */}
              <div className="nexus-card p-5">
                <h2 className="font-medium mb-3 flex items-center gap-2"><Heart size={18} /> Ajouter un événement sanitaire (troupeau)</h2>
                <form onSubmit={handleAddEvent} className="grid grid-cols-3 gap-3">
                  <select value={eventForm.event_type} onChange={(e) => setEventForm((p) => ({ ...p, event_type: e.target.value }))} className="nexus-input">
                    <option value="vaccination">Vaccination</option>
                    <option value="traitement">Traitement</option>
                    <option value="naissance">Naissance</option>
                    <option value="deces">Décès</option>
                    <option value="sevrage">Sevrage</option>
                  </select>
                  <input required type="date" value={eventForm.event_date} onChange={(e) => setEventForm((p) => ({ ...p, event_date: e.target.value }))} className="nexus-input" />
                  <input type="number" placeholder="Variation effectif" value={eventForm.count_change} onChange={(e) => setEventForm((p) => ({ ...p, count_change: e.target.value }))} className="nexus-input" />
                  <button type="submit" disabled={!selectedHerdId} className="nexus-btn-primary col-span-3">Enregistrer</button>
                </form>
              </div>

              <div className="nexus-card p-5">
                <h2 className="font-medium mb-3">Historique sanitaire du troupeau</h2>
                <div className="space-y-2">
                  {events.map((event) => (
                    <div key={event.id} className="flex items-center justify-between text-sm py-1.5">
                      <div>
                        <p className="font-medium capitalize">{event.event_type}</p>
                        <p className="text-xs text-nexus-text-muted">{event.event_date}</p>
                      </div>
                      {event.count_change !== 0 && (
                        <span className={event.count_change > 0 ? "text-emerald-400" : "text-red-400"}>
                          {event.count_change > 0 ? "+" : ""}{event.count_change}
                        </span>
                      )}
                    </div>
                  ))}
                  {events.length === 0 && <p className="text-sm text-nexus-text-muted">Aucun événement enregistré.</p>}
                </div>
              </div>

              {/* Fiches individuelles */}
              <div className="nexus-card p-5">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="font-medium flex items-center gap-2"><Users size={18} /> Fiches individuelles des animaux</h2>
                  <button onClick={() => setIsAnimalFormOpen(true)} className="nexus-btn-secondary text-xs flex items-center gap-1.5 py-1.5">
                    <Plus size={14} /> Ajouter un animal
                  </button>
                </div>
                <div className="space-y-1.5">
                  {animals.map((animal) => (
                    <button
                      key={animal.id}
                      onClick={() => setSelectedAnimalId(animal.id)}
                      className="w-full flex items-center justify-between text-sm py-2.5 px-3 rounded-xl hover:bg-nexus-surface-hover"
                    >
                      <div className="text-left">
                        <p className="font-medium">{animal.tag} {animal.breed ? `— ${animal.breed}` : ""}</p>
                        <p className="text-xs text-nexus-text-muted">
                          {animal.sex} {animal.current_weight_kg ? `— ${animal.current_weight_kg} kg` : ""}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`text-xs px-2 py-1 rounded-full capitalize ${
                          animal.status === "vivant" ? "bg-emerald-500/20 text-emerald-400" : "bg-nexus-surface-hover text-nexus-text-muted"
                        }`}>
                          {animal.status}
                        </span>
                        <ChevronRight size={16} className="text-nexus-text-muted" />
                      </div>
                    </button>
                  ))}
                  {animals.length === 0 && <p className="text-sm text-nexus-text-muted">Aucune fiche animal pour ce troupeau (le suivi global reste disponible ci-dessus).</p>}
                </div>
              </div>
            </>
          )}

          {/* Détail d'un animal */}
          {selectedAnimal && (
            <>
              <button onClick={() => setSelectedAnimalId(null)} className="flex items-center gap-1.5 text-sm text-nexus-text-muted hover:text-nexus-text">
                <ArrowLeft size={14} /> Retour au troupeau
              </button>

              <div className="nexus-card p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="font-semibold text-lg">{selectedAnimal.tag}</h2>
                    <p className="text-sm text-nexus-text-muted">
                      {selectedAnimal.breed || "Race non précisée"} — {selectedAnimal.sex}
                      {selectedAnimal.birth_date ? ` — né(e) le ${selectedAnimal.birth_date}` : ""}
                    </p>
                  </div>
                  <select
                    value={selectedAnimal.status}
                    onChange={(e) => handleUpdateAnimalStatus(e.target.value)}
                    className="nexus-input text-sm"
                  >
                    <option value="vivant">Vivant</option>
                    <option value="vendu">Vendu</option>
                    <option value="decede">Décédé</option>
                    <option value="reforme">Réformé</option>
                  </select>
                </div>
                <div className="pt-3 mt-3 border-t border-nexus-border">
                  <p className="text-xs text-nexus-text-muted mb-1.5">Télécharger la fiche / carnet</p>
                  <div className="flex flex-wrap gap-1.5">
                    {["pdf", "docx", "xlsx", "csv"].map((format) => (
                      <button
                        key={format}
                        onClick={() => handleDownloadAnimalReport(format)}
                        className="text-xs px-2 py-1 rounded-lg bg-nexus-surface-hover uppercase"
                      >
                        {format}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Croissance */}
              <div className="nexus-card p-5">
                <h2 className="font-medium mb-3 flex items-center gap-2"><TrendingUp size={18} className="text-emerald-400" /> Suivi de croissance</h2>
                <form onSubmit={handleAddWeight} className="grid grid-cols-3 gap-3 mb-4">
                  <input required type="number" step="0.1" placeholder="Poids (kg)" value={weightForm.weight_kg} onChange={(e) => setWeightForm((p) => ({ ...p, weight_kg: e.target.value }))} className="nexus-input" />
                  <input required type="date" value={weightForm.measured_at} onChange={(e) => setWeightForm((p) => ({ ...p, measured_at: e.target.value }))} className="nexus-input" />
                  <button type="submit" className="nexus-btn-primary text-sm">Enregistrer</button>
                </form>
                {growth && growth.records.length > 0 ? (
                  <div className="grid grid-cols-3 gap-3 mb-3">
                    <Stat label="Premier poids" value={`${growth.first_weight_kg} kg`} small />
                    <Stat label="Dernier poids" value={`${growth.latest_weight_kg} kg`} small />
                    <Stat
                      label="Gain moyen / jour"
                      value={growth.average_daily_gain_kg != null ? `${growth.average_daily_gain_kg.toFixed(2)} kg` : "—"}
                      small accent="text-emerald-400"
                    />
                  </div>
                ) : (
                  <p className="text-sm text-nexus-text-muted">Aucun relevé de poids encore.</p>
                )}
              </div>

              {/* Suivi sanitaire individuel */}
              <div className="nexus-card p-5">
                <h2 className="font-medium mb-3 flex items-center gap-2"><Syringe size={18} className="text-nexus-blue" /> Suivi sanitaire individuel</h2>
                <form onSubmit={handleAddHealthRecord} className="grid grid-cols-3 gap-3 mb-4">
                  <select value={healthForm.record_type} onChange={(e) => setHealthForm((p) => ({ ...p, record_type: e.target.value }))} className="nexus-input">
                    <option value="vaccination">Vaccination</option>
                    <option value="traitement">Traitement</option>
                    <option value="controle_veterinaire">Contrôle vétérinaire</option>
                    <option value="autre">Autre</option>
                  </select>
                  <input required type="date" value={healthForm.record_date} onChange={(e) => setHealthForm((p) => ({ ...p, record_date: e.target.value }))} className="nexus-input" />
                  <input type="number" placeholder="Coût (optionnel)" value={healthForm.cost_amount} onChange={(e) => setHealthForm((p) => ({ ...p, cost_amount: e.target.value }))} className="nexus-input" />
                  <button type="submit" className="nexus-btn-primary col-span-3 text-sm">Enregistrer</button>
                </form>
                <div className="space-y-1.5">
                  {healthRecords.map((r) => (
                    <div key={r.id} className="flex items-center justify-between text-sm py-1.5">
                      <p className="font-medium capitalize">{r.record_type}</p>
                      <p className="text-xs text-nexus-text-muted">{r.record_date}</p>
                    </div>
                  ))}
                  {healthRecords.length === 0 && <p className="text-sm text-nexus-text-muted">Aucun suivi sanitaire encore.</p>}
                </div>
              </div>

              {/* Reproduction */}
              {selectedAnimal.sex === "femelle" && (
                <div className="nexus-card p-5">
                  <div className="flex items-center justify-between mb-3">
                    <h2 className="font-medium flex items-center gap-2"><Baby size={18} className="text-pink-400" /> Reproduction</h2>
                    <button onClick={() => setShowBirthForm((v) => !v)} className="nexus-btn-secondary text-xs py-1.5">
                      Déclarer une mise bas
                    </button>
                  </div>

                  {showBirthForm && (
                    <form onSubmit={handleDeclareBirth} className="grid grid-cols-3 gap-3 mb-4 p-3 rounded-xl bg-nexus-surface-hover">
                      <input required type="date" value={birthForm.event_date} onChange={(e) => setBirthForm((p) => ({ ...p, event_date: e.target.value }))} className="nexus-input" />
                      <input required type="number" min="1" placeholder="Nombre de petits" value={birthForm.offspring_count} onChange={(e) => setBirthForm((p) => ({ ...p, offspring_count: e.target.value }))} className="nexus-input" />
                      <button type="submit" className="nexus-btn-primary text-sm">Confirmer</button>
                    </form>
                  )}

                  <form onSubmit={handleAddReproduction} className="grid grid-cols-3 gap-3 mb-4">
                    <select value={reproForm.event_type} onChange={(e) => setReproForm((p) => ({ ...p, event_type: e.target.value }))} className="nexus-input">
                      <option value="chaleurs">Chaleurs</option>
                      <option value="insemination">Insémination</option>
                      <option value="saillie">Saillie</option>
                      <option value="gestation_confirmee">Gestation confirmée</option>
                      <option value="avortement">Avortement</option>
                    </select>
                    <input required type="date" value={reproForm.event_date} onChange={(e) => setReproForm((p) => ({ ...p, event_date: e.target.value }))} className="nexus-input" />
                    <button type="submit" className="nexus-btn-primary text-sm">Enregistrer</button>
                  </form>

                  <div className="space-y-1.5">
                    {reproductionRecords.map((r) => (
                      <div key={r.id} className="flex items-center justify-between text-sm py-1.5">
                        <p className="font-medium capitalize">{r.event_type.replace(/_/g, " ")}</p>
                        <p className="text-xs text-nexus-text-muted">{r.event_date}</p>
                      </div>
                    ))}
                    {reproductionRecords.length === 0 && <p className="text-sm text-nexus-text-muted">Aucun événement de reproduction encore.</p>}
                  </div>
                </div>
              )}
            </>
          )}

          {!selectedHerd && <p className="text-sm text-nexus-text-muted">Sélectionnez ou créez un troupeau pour commencer.</p>}
        </div>
      </div>

      {isFormOpen && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50">
          <div className="nexus-card w-full max-w-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-lg">Nouveau troupeau</h2>
              <button onClick={() => setIsFormOpen(false)}><X size={20} /></button>
            </div>
            <form onSubmit={handleCreateHerd} className="space-y-3">
              <input required placeholder="Nom du troupeau" value={herdForm.name} onChange={(e) => setHerdForm((p) => ({ ...p, name: e.target.value }))} className="nexus-input w-full" />
              <input required placeholder="Espèce (bovins, poissons, abeilles...)" value={herdForm.species} onChange={(e) => setHerdForm((p) => ({ ...p, species: e.target.value }))} className="nexus-input w-full" />
              <input required type="number" placeholder="Effectif initial" value={herdForm.current_count} onChange={(e) => setHerdForm((p) => ({ ...p, current_count: e.target.value }))} className="nexus-input w-full" />
              <input required placeholder="Pays" value={herdForm.country} onChange={(e) => setHerdForm((p) => ({ ...p, country: e.target.value }))} className="nexus-input w-full" />
              {error && <p className="text-sm text-red-400">{error}</p>}
              <button type="submit" className="nexus-btn-primary w-full">Créer</button>
            </form>
          </div>
        </div>
      )}

      {isAnimalFormOpen && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50">
          <div className="nexus-card w-full max-w-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-lg">Nouvelle fiche animal</h2>
              <button onClick={() => setIsAnimalFormOpen(false)}><X size={20} /></button>
            </div>
            <form onSubmit={handleCreateAnimal} className="space-y-3">
              <input required placeholder="Identifiant / nom (ex: A-001)" value={animalForm.tag} onChange={(e) => setAnimalForm((p) => ({ ...p, tag: e.target.value }))} className="nexus-input w-full" />
              <select value={animalForm.sex} onChange={(e) => setAnimalForm((p) => ({ ...p, sex: e.target.value }))} className="nexus-input w-full">
                <option value="inconnu">Sexe inconnu</option>
                <option value="femelle">Femelle</option>
                <option value="male">Mâle</option>
              </select>
              <input placeholder="Race (optionnel)" value={animalForm.breed} onChange={(e) => setAnimalForm((p) => ({ ...p, breed: e.target.value }))} className="nexus-input w-full" />
              <input type="date" placeholder="Date de naissance (optionnel)" value={animalForm.birth_date} onChange={(e) => setAnimalForm((p) => ({ ...p, birth_date: e.target.value }))} className="nexus-input w-full" />
              {error && <p className="text-sm text-red-400">{error}</p>}
              <button type="submit" className="nexus-btn-primary w-full">Créer la fiche</button>
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
