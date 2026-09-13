import { useEffect, useState } from "react";
import { Plus, Search, X, Star } from "lucide-react";
import { apiRequest } from "../../api/client";

const CATEGORIES = [
  "ferme", "exploitation_agricole", "veterinaire", "avocat", "medecin", "ecole",
  "hopital", "hotel", "restaurant", "commerce", "entreprise", "artisan",
  "administration", "garage", "prestataire_service", "autre",
];

const EMPTY_FORM = {
  name: "", category: "restaurant", description: "", latitude: "", longitude: "",
  address: "", city: "", country: "",
};

export default function Maps() {
  const [listings, setListings] = useState([]);
  const [query, setQuery] = useState("");
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState("");

  useEffect(() => {
    loadListings();
  }, []);

  async function loadListings() {
    try {
      const data = await apiRequest("/maps/listings/search");
      setListings(data);
    } catch (err) {
      setError(err.detail || "Impossible de charger les fiches.");
    }
  }

  async function handleCreate(e) {
    e.preventDefault();
    try {
      await apiRequest("/maps/listings", {
        method: "POST",
        body: { ...form, latitude: Number(form.latitude), longitude: Number(form.longitude) },
      });
      setForm(EMPTY_FORM);
      setIsFormOpen(false);
      loadListings();
    } catch (err) {
      setError(err.detail || "Impossible de créer la fiche.");
    }
  }

  const filtered = listings.filter((l) => l.name.toLowerCase().includes(query.toLowerCase()));

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-xl font-semibold">Cartographie intelligente</h1>
        <button onClick={() => setIsFormOpen(true)} className="nexus-btn-primary flex items-center gap-2 text-sm">
          <Plus size={16} /> Ajouter une fiche
        </button>
      </div>

      <div className="relative max-w-md">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-nexus-text-muted" />
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Rechercher un lieu..." className="nexus-input w-full pl-9" />
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((listing) => (
          <article key={listing.id} className="nexus-card p-4">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs uppercase tracking-wide text-nexus-blue">{listing.category.replace(/_/g, " ")}</span>
              {listing.is_verified && <Star size={14} className="text-amber-400" fill="currentColor" />}
            </div>
            <h3 className="font-medium">{listing.name}</h3>
            <p className="text-xs text-nexus-text-muted mt-1 line-clamp-2">{listing.description}</p>
            <p className="text-xs text-nexus-text-muted mt-2">{listing.city}, {listing.country}</p>
          </article>
        ))}
        {filtered.length === 0 && <p className="col-span-full text-center text-nexus-text-muted py-12">Aucune fiche trouvée.</p>}
      </div>

      {isFormOpen && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50">
          <div className="nexus-card w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-lg">Ajouter une fiche professionnelle</h2>
              <button onClick={() => setIsFormOpen(false)}><X size={20} /></button>
            </div>
            <form onSubmit={handleCreate} className="space-y-3">
              <input required placeholder="Nom" value={form.name} onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))} className="nexus-input w-full" />
              <select value={form.category} onChange={(e) => setForm((p) => ({ ...p, category: e.target.value }))} className="nexus-input w-full">
                {CATEGORIES.map((c) => <option key={c} value={c}>{c.replace(/_/g, " ")}</option>)}
              </select>
              <textarea required placeholder="Description" value={form.description} onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))} rows={2} className="nexus-input w-full resize-none" />
              <div className="grid grid-cols-2 gap-3">
                <input required type="number" step="any" placeholder="Latitude" value={form.latitude} onChange={(e) => setForm((p) => ({ ...p, latitude: e.target.value }))} className="nexus-input w-full" />
                <input required type="number" step="any" placeholder="Longitude" value={form.longitude} onChange={(e) => setForm((p) => ({ ...p, longitude: e.target.value }))} className="nexus-input w-full" />
              </div>
              <input required placeholder="Adresse" value={form.address} onChange={(e) => setForm((p) => ({ ...p, address: e.target.value }))} className="nexus-input w-full" />
              <div className="grid grid-cols-2 gap-3">
                <input required placeholder="Ville" value={form.city} onChange={(e) => setForm((p) => ({ ...p, city: e.target.value }))} className="nexus-input w-full" />
                <input required placeholder="Pays" value={form.country} onChange={(e) => setForm((p) => ({ ...p, country: e.target.value }))} className="nexus-input w-full" />
              </div>
              {error && <p className="text-sm text-red-400">{error}</p>}
              <button type="submit" className="nexus-btn-primary w-full">Créer la fiche</button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
