import { useEffect, useState } from "react";
import { Upload, Plus, Trash2, Play, Download, Film, ArrowLeft } from "lucide-react";
import { apiRequest, uploadFile } from "../../api/client";

const RESOLUTIONS = ["1080x1920", "1920x1080", "1080x1080", "720x1280"];
const CLIP_TYPES = [
  { value: "color", label: "Fond uni (texte / intro)" },
  { value: "image", label: "Image importée" },
  { value: "video", label: "Vidéo importée" },
];
const COLORS = ["black", "white", "blue", "red", "green", "gray"];

const STATUS_LABELS = {
  brouillon: "Brouillon",
  en_cours: "Rendu en cours…",
  pret: "Prête",
  echoue: "Échec",
};

function emptyClip() {
  return { type: "color", color: "black", media_id: "", duration_seconds: 3, filter_id: "", text_overlay: "" };
}

export default function VideoMontage({ onBack }) {
  const [media, setMedia] = useState([]);
  const [filters, setFilters] = useState([]);
  const [projects, setProjects] = useState([]);
  const [title, setTitle] = useState("");
  const [resolution, setResolution] = useState("1080x1920");
  const [clips, setClips] = useState([emptyClip()]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [busyProjectId, setBusyProjectId] = useState(null);

  useEffect(() => {
    loadMedia();
    loadFilters();
    loadProjects();
  }, []);

  async function loadMedia() {
    try { setMedia(await apiRequest("/studio/media")); } catch { /* silencieux */ }
  }
  async function loadFilters() {
    try { setFilters(await apiRequest("/studio/filters")); } catch { /* silencieux */ }
  }
  async function loadProjects() {
    try { setProjects(await apiRequest("/studio/video-projects")); } catch { /* silencieux */ }
  }

  async function handleUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError("");
    try {
      await uploadFile("/studio/media", file);
      await loadMedia();
    } catch (err) {
      setError(err.detail || "Import du fichier impossible (format non supporté ou fichier trop volumineux).");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  function updateClip(index, patch) {
    setClips((prev) => prev.map((c, i) => (i === index ? { ...c, ...patch } : c)));
  }
  function addClip() {
    setClips((prev) => [...prev, emptyClip()]);
  }
  function removeClip(index) {
    setClips((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleCreateProject(e) {
    e.preventDefault();
    setError("");
    const cleanedClips = clips.map((c) => {
      const clip = { type: c.type, duration_seconds: Number(c.duration_seconds) || 1 };
      if (c.type === "color") clip.color = c.color;
      if (c.type === "image" || c.type === "video") clip.media_id = c.media_id;
      if (c.filter_id) clip.filter_id = c.filter_id;
      if (c.text_overlay) clip.text_overlay = c.text_overlay;
      return clip;
    });
    try {
      await apiRequest("/studio/video-projects", {
        method: "POST",
        body: { title, resolution, timeline_data: JSON.stringify({ clips: cleanedClips }) },
      });
      setTitle("");
      setClips([emptyClip()]);
      await loadProjects();
    } catch (err) {
      setError(err.detail || "Impossible de créer le montage.");
    }
  }

  async function handleRender(projectId) {
    setBusyProjectId(projectId);
    setError("");
    try {
      await apiRequest(`/studio/video-projects/${projectId}/render`, { method: "POST" });
      await loadProjects();
    } catch (err) {
      setError(err.detail || "Le rendu a échoué.");
    } finally {
      setBusyProjectId(null);
    }
  }

  async function handleDownload(projectId, projectTitle) {
    try {
      const response = await apiRequest(`/studio/video-projects/${projectId}/download`, { rawResponse: true });
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${projectTitle || "video"}.mp4`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.detail || "Téléchargement impossible.");
    }
  }

  const mediaOptions = media; // { id, original_filename, media_type }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <button onClick={onBack} className="text-nexus-text-muted hover:text-nexus-text"><ArrowLeft size={20} /></button>
        <h1 className="text-xl font-semibold flex items-center gap-2"><Film size={22} /> Montage vidéo</h1>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <section className="nexus-card p-5 space-y-3">
        <h2 className="font-medium">1. Importer une image ou une vidéo</h2>
        <label className="nexus-btn-primary inline-flex items-center gap-2 text-sm cursor-pointer w-fit">
          <Upload size={16} /> {uploading ? "Envoi en cours…" : "Choisir un fichier"}
          <input type="file" accept="image/png,image/jpeg,image/webp,video/mp4,video/quicktime,video/webm" onChange={handleUpload} className="hidden" disabled={uploading} />
        </label>
        <div className="flex flex-wrap gap-2 mt-2">
          {mediaOptions.map((m) => (
            <span key={m.id} className="text-xs px-2 py-1 rounded-full bg-nexus-surface-hover">
              {m.media_type === "image" ? "🖼️" : "🎬"} {m.original_filename}
            </span>
          ))}
          {mediaOptions.length === 0 && <p className="text-xs text-nexus-text-muted">Aucun fichier importé pour l'instant.</p>}
        </div>
      </section>

      <section className="nexus-card p-5 space-y-4">
        <h2 className="font-medium">2. Construire le montage (clips, filtres, texte)</h2>
        <form onSubmit={handleCreateProject} className="space-y-4">
          <div className="flex gap-3">
            <input required placeholder="Titre de la vidéo" value={title} onChange={(e) => setTitle(e.target.value)} className="nexus-input flex-1" />
            <select value={resolution} onChange={(e) => setResolution(e.target.value)} className="nexus-input">
              {RESOLUTIONS.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>

          <div className="space-y-3">
            {clips.map((clip, index) => (
              <div key={index} className="border border-nexus-border rounded-lg p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-nexus-text-muted">Clip {index + 1}</span>
                  {clips.length > 1 && (
                    <button type="button" onClick={() => removeClip(index)} className="text-red-400"><Trash2 size={14} /></button>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <select value={clip.type} onChange={(e) => updateClip(index, { type: e.target.value })} className="nexus-input text-sm">
                    {CLIP_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </select>

                  {clip.type === "color" && (
                    <select value={clip.color} onChange={(e) => updateClip(index, { color: e.target.value })} className="nexus-input text-sm">
                      {COLORS.map((c) => <option key={c} value={c}>{c}</option>)}
                    </select>
                  )}
                  {(clip.type === "image" || clip.type === "video") && (
                    <select
                      value={clip.media_id}
                      onChange={(e) => updateClip(index, { media_id: e.target.value })}
                      className="nexus-input text-sm"
                    >
                      <option value="">Choisir un fichier importé…</option>
                      {mediaOptions
                        .filter((m) => m.media_type === clip.type)
                        .map((m) => <option key={m.id} value={m.id}>{m.original_filename}</option>)}
                    </select>
                  )}

                  <input
                    type="number" min="1" step="0.5" placeholder="Durée (secondes)"
                    value={clip.duration_seconds}
                    onChange={(e) => updateClip(index, { duration_seconds: e.target.value })}
                    className="nexus-input text-sm"
                  />
                  <select value={clip.filter_id} onChange={(e) => updateClip(index, { filter_id: e.target.value })} className="nexus-input text-sm">
                    <option value="">Aucun filtre</option>
                    {filters.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
                  </select>
                  <input
                    placeholder="Texte incrusté (optionnel)" value={clip.text_overlay}
                    onChange={(e) => updateClip(index, { text_overlay: e.target.value })}
                    className="nexus-input text-sm col-span-2"
                  />
                </div>
              </div>
            ))}
          </div>

          <button type="button" onClick={addClip} className="text-sm flex items-center gap-1 text-nexus-blue">
            <Plus size={14} /> Ajouter un clip
          </button>

          <button type="submit" className="nexus-btn-primary w-full">Créer le montage</button>
        </form>
      </section>

      <section className="space-y-3">
        <h2 className="font-medium">3. Vos montages</h2>
        {projects.map((p) => (
          <div key={p.id} className="nexus-card p-4 flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">{p.title}</p>
              <p className="text-xs text-nexus-text-muted">{STATUS_LABELS[p.render_status] || p.render_status}{p.render_error ? ` — ${p.render_error}` : ""}</p>
            </div>
            <div className="flex gap-2">
              {p.render_status !== "pret" && (
                <button
                  onClick={() => handleRender(p.id)}
                  disabled={busyProjectId === p.id}
                  className="nexus-btn-primary flex items-center gap-1 text-xs"
                >
                  <Play size={14} /> {busyProjectId === p.id ? "Rendu…" : "Lancer le rendu"}
                </button>
              )}
              {p.download_available && (
                <button onClick={() => handleDownload(p.id, p.title)} className="nexus-btn-primary flex items-center gap-1 text-xs">
                  <Download size={14} /> Télécharger
                </button>
              )}
            </div>
          </div>
        ))}
        {projects.length === 0 && <p className="text-sm text-nexus-text-muted">Aucun montage pour l'instant.</p>}
      </section>
    </div>
  );
}
