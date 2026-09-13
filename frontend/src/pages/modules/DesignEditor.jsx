import { useEffect, useRef, useState } from "react";
import { Type, Square, Circle as CircleIcon, Trash2, Save, ArrowLeft } from "lucide-react";
import { apiRequest } from "../../api/client";

/**
 * Éditeur de calques du Studio créatif, façon Canva.
 *
 * Modèle de données d'un calque (élément) :
 *   { id, type: "text"|"rectangle"|"circle", x, y, width, height,
 *     content, color, backgroundColor, fontSize }
 *
 * Le tout est sérialisé en JSON dans `canvas_data` et envoyé au backend
 * tel quel — même format déjà validé côté serveur (voir
 * app/modules/studio/schemas.py, `_validate_json_field`).
 */

const MAX_DISPLAY_SIZE = 640;

function createElement(type) {
  const base = { id: crypto.randomUUID(), type, x: 40, y: 40, rotation: 0 };
  if (type === "text") {
    return { ...base, width: 220, height: 60, content: "Votre texte ici", color: "#e8ecf7", fontSize: 24 };
  }
  if (type === "rectangle") {
    return { ...base, width: 160, height: 100, backgroundColor: "#3b82f6" };
  }
  return { ...base, width: 120, height: 120, backgroundColor: "#8b5cf6" };
}

export default function DesignEditor({ project, onBack, onSaved }) {
  const [elements, setElements] = useState(() => {
    try {
      const parsed = JSON.parse(project.canvas_data || "{}");
      return parsed.elements || [];
    } catch {
      return [];
    }
  });
  const [selectedId, setSelectedId] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");
  const canvasRef = useRef(null);
  const dragState = useRef(null);

  const scale = Math.min(1, MAX_DISPLAY_SIZE / Math.max(project.width, project.height));
  const displayWidth = project.width * scale;
  const displayHeight = project.height * scale;

  const selectedElement = elements.find((el) => el.id === selectedId) || null;

  function addElement(type) {
    const el = createElement(type);
    setElements((prev) => [...prev, el]);
    setSelectedId(el.id);
  }

  function updateElement(id, patch) {
    setElements((prev) => prev.map((el) => (el.id === id ? { ...el, ...patch } : el)));
  }

  function deleteSelected() {
    if (!selectedId) return;
    setElements((prev) => prev.filter((el) => el.id !== selectedId));
    setSelectedId(null);
  }

  function handleMouseDown(e, el) {
    e.stopPropagation();
    setSelectedId(el.id);
    const canvasRect = canvasRef.current.getBoundingClientRect();
    dragState.current = {
      id: el.id,
      offsetX: (e.clientX - canvasRect.left) / scale - el.x,
      offsetY: (e.clientY - canvasRect.top) / scale - el.y,
    };
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
  }

  function handleMouseMove(e) {
    if (!dragState.current) return;
    const canvasRect = canvasRef.current.getBoundingClientRect();
    const rawX = (e.clientX - canvasRect.left) / scale - dragState.current.offsetX;
    const rawY = (e.clientY - canvasRect.top) / scale - dragState.current.offsetY;
    const clampedX = Math.max(0, Math.min(project.width - 20, rawX));
    const clampedY = Math.max(0, Math.min(project.height - 20, rawY));
    updateElement(dragState.current.id, { x: Math.round(clampedX), y: Math.round(clampedY) });
  }

  function handleMouseUp() {
    dragState.current = null;
    window.removeEventListener("mousemove", handleMouseMove);
    window.removeEventListener("mouseup", handleMouseUp);
  }

  useEffect(() => {
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, []);

  async function handleSave() {
    setIsSaving(true);
    setError("");
    try {
      const canvas_data = JSON.stringify({ elements });
      const updated = await apiRequest(`/studio/design-projects/${project.id}`, {
        method: "PATCH",
        body: { canvas_data },
      });
      onSaved?.(updated);
    } catch (err) {
      setError(err.detail || "Impossible d'enregistrer le design.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <button onClick={onBack} className="nexus-btn-secondary flex items-center gap-2 text-sm">
          <ArrowLeft size={16} /> Retour
        </button>
        <h2 className="font-medium truncate max-w-xs">{project.title}</h2>
        <button onClick={handleSave} disabled={isSaving} className="nexus-btn-primary flex items-center gap-2 text-sm">
          <Save size={16} /> {isSaving ? "Enregistrement..." : "Enregistrer"}
        </button>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <div className="flex flex-col md:flex-row gap-4">
        <div className="nexus-card p-3 flex flex-row md:flex-col gap-2 h-fit overflow-x-auto md:overflow-visible">
          <button onClick={() => addElement("text")} className="p-2.5 rounded-lg hover:bg-nexus-surface-hover shrink-0" title="Ajouter du texte">
            <Type size={18} />
          </button>
          <button onClick={() => addElement("rectangle")} className="p-2.5 rounded-lg hover:bg-nexus-surface-hover shrink-0" title="Ajouter un rectangle">
            <Square size={18} />
          </button>
          <button onClick={() => addElement("circle")} className="p-2.5 rounded-lg hover:bg-nexus-surface-hover shrink-0" title="Ajouter un cercle">
            <CircleIcon size={18} />
          </button>
          <div className="hidden md:block h-px bg-nexus-border my-1" />
          <button
            onClick={deleteSelected}
            disabled={!selectedId}
            className="p-2.5 rounded-lg hover:bg-red-500/10 text-red-400 disabled:opacity-30 shrink-0"
            title="Supprimer le calque sélectionné"
          >
            <Trash2 size={18} />
          </button>
        </div>

        <div className="flex-1 overflow-auto flex justify-center py-4 bg-nexus-bg/50 rounded-2xl">
          <div
            ref={canvasRef}
            onMouseDown={() => setSelectedId(null)}
            className="relative bg-white shrink-0 shadow-2xl"
            style={{ width: displayWidth, height: displayHeight }}
          >
            {elements.map((el) => (
              <div
                key={el.id}
                onMouseDown={(e) => handleMouseDown(e, el)}
                className={`absolute cursor-move select-none ${
                  selectedId === el.id ? "outline outline-2 outline-nexus-blue" : ""
                }`}
                style={{
                  left: el.x * scale,
                  top: el.y * scale,
                  width: el.width * scale,
                  height: el.height * scale,
                  transform: `rotate(${el.rotation || 0}deg)`,
                  backgroundColor: el.type !== "text" ? el.backgroundColor : "transparent",
                  borderRadius: el.type === "circle" ? "50%" : el.type === "rectangle" ? 8 : 0,
                  color: el.color,
                  fontSize: el.fontSize ? el.fontSize * scale : undefined,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontWeight: 600,
                  wordBreak: "break-word",
                  padding: el.type === "text" ? 4 : 0,
                }}
              >
                {el.type === "text" ? el.content : null}
              </div>
            ))}
          </div>
        </div>

        <div className="nexus-card p-4 w-full md:w-64 shrink-0 space-y-3">
          <h3 className="text-sm font-medium text-nexus-text-muted">Propriétés</h3>
          {!selectedElement && <p className="text-sm text-nexus-text-muted">Sélectionnez un calque pour le modifier.</p>}

          {selectedElement && (
            <div className="space-y-3">
              {selectedElement.type === "text" && (
                <>
                  <textarea
                    value={selectedElement.content}
                    onChange={(e) => updateElement(selectedElement.id, { content: e.target.value })}
                    rows={2}
                    className="nexus-input w-full text-sm resize-none"
                  />
                  <div>
                    <label className="text-xs text-nexus-text-muted block mb-1">Taille de police</label>
                    <input
                      type="number"
                      value={selectedElement.fontSize}
                      onChange={(e) => updateElement(selectedElement.id, { fontSize: Number(e.target.value) })}
                      className="nexus-input w-full text-sm"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-nexus-text-muted block mb-1">Couleur du texte</label>
                    <input
                      type="color"
                      value={selectedElement.color}
                      onChange={(e) => updateElement(selectedElement.id, { color: e.target.value })}
                      className="w-full h-9 rounded-lg bg-transparent"
                    />
                  </div>
                </>
              )}

              {selectedElement.type !== "text" && (
                <div>
                  <label className="text-xs text-nexus-text-muted block mb-1">Couleur de fond</label>
                  <input
                    type="color"
                    value={selectedElement.backgroundColor}
                    onChange={(e) => updateElement(selectedElement.id, { backgroundColor: e.target.value })}
                    className="w-full h-9 rounded-lg bg-transparent"
                  />
                </div>
              )}

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-xs text-nexus-text-muted block mb-1">Largeur</label>
                  <input
                    type="number"
                    value={selectedElement.width}
                    onChange={(e) => updateElement(selectedElement.id, { width: Number(e.target.value) })}
                    className="nexus-input w-full text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs text-nexus-text-muted block mb-1">Hauteur</label>
                  <input
                    type="number"
                    value={selectedElement.height}
                    onChange={(e) => updateElement(selectedElement.id, { height: Number(e.target.value) })}
                    className="nexus-input w-full text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs text-nexus-text-muted block mb-1">Rotation ({selectedElement.rotation || 0}°)</label>
                <input
                  type="range"
                  min="0"
                  max="360"
                  value={selectedElement.rotation || 0}
                  onChange={(e) => updateElement(selectedElement.id, { rotation: Number(e.target.value) })}
                  className="w-full"
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
