import { useEffect, useState } from "react";
import { Palette, Video, Sparkles, Plus, X, Lock, Film } from "lucide-react";
import { apiRequest } from "../../api/client";
import DesignEditor from "./DesignEditor";
import VideoMontage from "./VideoMontage";

const CATEGORIES = [
  "post_reseau_social", "story", "flyer", "affiche", "logo",
  "presentation", "carte_visite", "carte_etudiant", "banniere", "miniature_video", "autre",
];

const SIZE_PRESETS = {
  post_reseau_social: { width: 1080, height: 1080 },
  story: { width: 1080, height: 1920 },
  flyer: { width: 1080, height: 1350 },
  affiche: { width: 1240, height: 1754 },
  logo: { width: 500, height: 500 },
  presentation: { width: 1920, height: 1080 },
  carte_visite: { width: 1050, height: 600 },
  carte_etudiant: { width: 1013, height: 638 },
  banniere: { width: 1584, height: 396 },
  miniature_video: { width: 1280, height: 720 },
  autre: { width: 1080, height: 1080 },
};

export default function Studio() {
  const [view, setView] = useState("list");
  const [designs, setDesigns] = useState([]);
  const [activeProject, setActiveProject] = useState(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [form, setForm] = useState({ title: "", category: "post_reseau_social" });
  const [categoryTemplates, setCategoryTemplates] = useState([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState(null);
  const [error, setError] = useState("");

  const [premiumStatus, setPremiumStatus] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [prompt, setPrompt] = useState("");
  const [style, setStyle] = useState("2d");
  const [isSubmittingVideo, setIsSubmittingVideo] = useState(false);

  useEffect(() => {
    loadDesigns();
    apiRequest("/studio/account/premium-status").then(setPremiumStatus).catch(() => {});
    loadJobs();
  }, []);

  useEffect(() => {
    if (isFormOpen) loadTemplatesForCategory(form.category);
  }, [isFormOpen, form.category]);

  async function loadTemplatesForCategory(category) {
    setSelectedTemplateId(null);
    try {
      const data = await apiRequest(`/studio/templates/search?category=${category}`);
      setCategoryTemplates(data);
    } catch {
      setCategoryTemplates([]);
    }
  }

  async function loadDesigns() {
    try {
      const data = await apiRequest("/studio/design-projects");
      setDesigns(data);
    } catch (err) {
      setError(err.detail || "Impossible de charger vos designs.");
    }
  }

  async function loadJobs() {
    try {
      const data = await apiRequest("/studio/ai-video-jobs");
      setJobs(data);
    } catch {
      // silencieux
    }
  }

  async function handleCreateDesign(e) {
    e.preventDefault();
    setError("");
    const preset = SIZE_PRESETS[form.category];
    try {
      const project = await apiRequest("/studio/design-projects", {
        method: "POST",
        body: {
          title: form.title,
          category: form.category,
          width: preset.width,
          height: preset.height,
          template_id: selectedTemplateId,
        },
      });
      setIsFormOpen(false);
      setForm({ title: "", category: "post_reseau_social" });
      setSelectedTemplateId(null);
      openEditor(project);
      loadDesigns();
    } catch (err) {
      setError(
        err.status === 402
          ? "Ce modèle est réservé aux comptes premium. Choisissez un modèle gratuit ou passez premium."
          : err.detail || "Impossible de créer le design."
      );
    }
  }

  function openEditor(project) {
    setActiveProject(project);
    setView("editor");
  }

  function backToList() {
    setView("list");
    setActiveProject(null);
    loadDesigns();
  }

  async function handleGenerateVideo(e) {
    e.preventDefault();
    setIsSubmittingVideo(true);
    setError("");
    try {
      await apiRequest("/studio/ai-video-jobs", { method: "POST", body: { prompt, style, duration_seconds: 5 } });
      setPrompt("");
      loadJobs();
    } catch (err) {
      setError(
        err.status === 402
          ? "La génération vidéo par IA est réservée aux comptes premium."
          : err.detail || "Génération impossible."
      );
    } finally {
      setIsSubmittingVideo(false);
    }
  }

  if (view === "editor" && activeProject) {
    return (
      <div className="max-w-6xl mx-auto">
        <DesignEditor project={activeProject} onBack={backToList} onSaved={setActiveProject} />
      </div>
    );
  }

  if (view === "video-montage") {
    return <VideoMontage onBack={() => setView("list")} />;
  }

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold flex items-center gap-2"><Palette size={22} /> Studio créatif</h1>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      {premiumStatus && !premiumStatus.has_premium_access && (
        <div className="nexus-card p-4 text-sm text-amber-400">
          Votre essai gratuit est terminé. Passez premium pour les modèles et filtres avancés.
        </div>
      )}

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-medium">Vos créations</h2>
          <button onClick={() => setIsFormOpen(true)} className="nexus-btn-primary flex items-center gap-2 text-sm">
            <Plus size={16} /> Nouveau design
          </button>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {designs.map((d) => (
            <button
              key={d.id}
              onClick={() => openEditor(d)}
              className="nexus-card p-4 text-left hover:bg-nexus-surface-hover transition-colors"
            >
              <div className="aspect-square rounded-lg bg-nexus-surface-hover mb-2" />
              <p className="text-sm font-medium truncate">{d.title}</p>
              <p className="text-xs text-nexus-text-muted capitalize">{d.category.replace(/_/g, " ")}</p>
            </button>
          ))}
          {designs.length === 0 && (
            <p className="col-span-full text-center text-nexus-text-muted py-8">
              Aucun design pour l'instant — créez le premier.
            </p>
          )}
        </div>
      </section>

      <section className="nexus-card p-5 flex items-center justify-between">
        <div>
          <h2 className="font-medium flex items-center gap-2"><Film size={18} /> Montage vidéo</h2>
          <p className="text-xs text-nexus-text-muted mt-1">
            Assemblez vos propres images/vidéos, appliquez des filtres, ajoutez du texte, puis téléchargez le résultat.
          </p>
        </div>
        <button onClick={() => setView("video-montage")} className="nexus-btn-primary flex items-center gap-2 text-sm">
          <Plus size={16} /> Ouvrir
        </button>
      </section>

      <section className="nexus-card p-5">
        <h2 className="font-medium mb-3 flex items-center gap-2"><Video size={18} /> Génération vidéo par IA (à partir d'un texte)</h2>
        <form onSubmit={handleGenerateVideo} className="space-y-3">
          <textarea
            required
            placeholder="Décrivez la vidéo à générer..."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={3}
            className="nexus-input w-full resize-none"
          />
          <div className="flex gap-3">
            <select value={style} onChange={(e) => setStyle(e.target.value)} className="nexus-input">
              <option value="2d">2D</option>
              <option value="3d">3D</option>
              <option value="ultra_realiste">Ultra-réaliste</option>
              <option value="animation">Animation</option>
              <option value="cinematique">Cinématique</option>
            </select>
            <button type="submit" disabled={isSubmittingVideo} className="nexus-btn-primary flex items-center gap-2">
              <Sparkles size={16} /> Générer
            </button>
          </div>
        </form>
        <div className="mt-4 space-y-2">
          {jobs.map((job) => (
            <div key={job.id} className="flex items-center justify-between text-sm py-1.5 border-t border-nexus-border first:border-0 first:pt-0">
              <p className="truncate max-w-xs">{job.prompt}</p>
              <span className="text-xs px-2 py-1 rounded-full bg-nexus-surface-hover capitalize shrink-0">
                {job.status.replace(/_/g, " ")}
              </span>
            </div>
          ))}
        </div>
      </section>

      {isFormOpen && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50">
          <div className="nexus-card w-full max-w-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-lg">Nouveau design</h2>
              <button onClick={() => setIsFormOpen(false)}><X size={20} /></button>
            </div>
            <form onSubmit={handleCreateDesign} className="space-y-3">
              <input
                required
                placeholder="Titre du design"
                value={form.title}
                onChange={(e) => setForm((p) => ({ ...p, title: e.target.value }))}
                className="nexus-input w-full"
              />
              <select
                value={form.category}
                onChange={(e) => setForm((p) => ({ ...p, category: e.target.value }))}
                className="nexus-input w-full"
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>{c.replace(/_/g, " ")}</option>
                ))}
              </select>
              <p className="text-xs text-nexus-text-muted">
                Format : {SIZE_PRESETS[form.category].width} × {SIZE_PRESETS[form.category].height}px
              </p>

              {categoryTemplates.length > 0 && (
                <div>
                  <p className="text-xs text-nexus-text-muted mb-2">Partir d'un modèle (optionnel)</p>
                  <div className="grid grid-cols-3 gap-2 max-h-48 overflow-y-auto">
                    <button
                      type="button"
                      onClick={() => setSelectedTemplateId(null)}
                      className={`p-2 rounded-lg border text-xs ${
                        selectedTemplateId === null ? "border-nexus-blue bg-nexus-surface-hover" : "border-nexus-border"
                      }`}
                    >
                      Page blanche
                    </button>
                    {categoryTemplates.map((tpl) => (
                      <button
                        key={tpl.id}
                        type="button"
                        onClick={() => setSelectedTemplateId(tpl.id)}
                        className={`p-2 rounded-lg border text-xs relative ${
                          selectedTemplateId === tpl.id ? "border-nexus-blue bg-nexus-surface-hover" : "border-nexus-border"
                        }`}
                      >
                        {tpl.is_premium && <Lock size={10} className="absolute top-1 right-1 text-amber-400" />}
                        <span className="line-clamp-2">{tpl.name}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <button type="submit" className="nexus-btn-primary w-full">Créer et ouvrir l'éditeur</button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
