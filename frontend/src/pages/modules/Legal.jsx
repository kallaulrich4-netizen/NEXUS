import { useEffect, useState } from "react";
import { Search, Scale } from "lucide-react";
import { apiRequest } from "../../api/client";

const CATEGORIES = [
  "droit_civil", "droit_penal", "droit_commercial", "droit_des_societes",
  "droit_du_travail", "droit_de_la_famille", "divorce", "succession",
  "immobilier", "fiscalite", "contrats", "propriete_intellectuelle",
  "procedures_administratives", "droit_international", "autre",
];

export default function Legal() {
  const [resources, setResources] = useState([]);
  const [country, setCountry] = useState("");
  const [category, setCategory] = useState("");
  const [error, setError] = useState("");

  useEffect(() => { search(); }, []);

  async function search() {
    try {
      const params = new URLSearchParams();
      if (country) params.set("country", country);
      if (category) params.set("category", category);
      const data = await apiRequest(`/legal/resources/search?${params.toString()}`);
      setResources(data);
    } catch (err) {
      setError(err.detail || "Impossible de charger les ressources.");
    }
  }

  function handleSubmit(e) {
    e.preventDefault();
    search();
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h1 className="text-xl font-semibold flex items-center gap-2"><Scale size={22} /> Droit</h1>

      <form onSubmit={handleSubmit} className="nexus-card p-4 grid md:grid-cols-3 gap-3">
        <input
          placeholder="Pays (ex: Sénégal)"
          value={country}
          onChange={(e) => setCountry(e.target.value)}
          className="nexus-input"
        />
        <select value={category} onChange={(e) => setCategory(e.target.value)} className="nexus-input">
          <option value="">Toutes les catégories</option>
          {CATEGORIES.map((c) => <option key={c} value={c}>{c.replace(/_/g, " ")}</option>)}
        </select>
        <button type="submit" className="nexus-btn-primary flex items-center justify-center gap-2">
          <Search size={16} /> Rechercher
        </button>
      </form>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <div className="space-y-3">
        {resources.map((resource) => (
          <article key={resource.id} className="nexus-card p-4">
            <div className="flex items-center justify-between mb-1">
              <h3 className="font-medium">{resource.title}</h3>
              <span className="text-xs text-nexus-text-muted capitalize">{resource.category.replace(/_/g, " ")}</span>
            </div>
            <p className="text-sm text-nexus-text-muted">{resource.summary}</p>
            <p className="text-xs text-nexus-text-muted mt-2">{resource.jurisdiction_country}</p>
          </article>
        ))}
        {resources.length === 0 && (
          <p className="text-center text-nexus-text-muted py-12">
            Aucune ressource publiée pour ces critères pour l'instant. Pour un conseil personnalisé, mettez-vous en relation avec un avocat via le module Cartographie.
          </p>
        )}
      </div>
    </div>
  );
}
