import { useEffect, useState } from "react";
import { Plus, X, Code2 } from "lucide-react";
import { apiRequest } from "../../api/client";

const EMPTY_PROJECT = { name: "", description: "", project_type: "" };
const EMPTY_TASK = { title: "", priority: "moyenne" };

export default function DevTools() {
  const [projects, setProjects] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [projectForm, setProjectForm] = useState(EMPTY_PROJECT);
  const [taskForm, setTaskForm] = useState(EMPTY_TASK);
  const [error, setError] = useState("");

  useEffect(() => { loadProjects(); }, []);
  useEffect(() => { if (selectedId) loadTasks(selectedId); }, [selectedId]);

  async function loadProjects() {
    try {
      const data = await apiRequest("/devtools/projects");
      setProjects(data);
      if (data.length > 0 && !selectedId) setSelectedId(data[0].id);
    } catch (err) { setError(err.detail || "Impossible de charger les projets."); }
  }

  async function loadTasks(projectId) {
    try {
      const data = await apiRequest(`/devtools/projects/${projectId}/tasks`);
      setTasks(data);
    } catch (err) { setError(err.detail || "Impossible de charger les tâches."); }
  }

  async function handleCreateProject(e) {
    e.preventDefault();
    try {
      await apiRequest("/devtools/projects", { method: "POST", body: projectForm });
      setProjectForm(EMPTY_PROJECT);
      setIsFormOpen(false);
      loadProjects();
    } catch (err) { setError(err.detail || "Impossible de créer le projet."); }
  }

  async function handleAddTask(e) {
    e.preventDefault();
    if (!selectedId) return;
    try {
      await apiRequest(`/devtools/projects/${selectedId}/tasks`, { method: "POST", body: taskForm });
      setTaskForm(EMPTY_TASK);
      loadTasks(selectedId);
    } catch (err) { setError(err.detail || "Impossible d'ajouter la tâche."); }
  }

  async function updateTaskStatus(taskId, status) {
    try {
      await apiRequest(`/devtools/tasks/${taskId}/status`, { method: "PATCH", body: { status } });
      loadTasks(selectedId);
    } catch (err) { setError(err.detail || "Impossible de mettre à jour la tâche."); }
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold flex items-center gap-2"><Code2 size={22} /> Développement logiciel</h1>
        <button onClick={() => setIsFormOpen(true)} className="nexus-btn-primary flex items-center gap-2 text-sm">
          <Plus size={16} /> Nouveau projet
        </button>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <div className="grid md:grid-cols-3 gap-6">
        <div className="nexus-card p-4 space-y-2">
          <h2 className="font-medium text-sm text-nexus-text-muted mb-2">Vos projets</h2>
          {projects.map((p) => (
            <button
              key={p.id}
              onClick={() => setSelectedId(p.id)}
              className={`w-full text-left px-3 py-2.5 rounded-xl text-sm ${
                selectedId === p.id ? "bg-nexus-gradient text-white" : "hover:bg-nexus-surface-hover"
              }`}
            >
              <p className="font-medium truncate">{p.name}</p>
              <p className="text-xs opacity-70 capitalize">{p.status.replace(/_/g, " ")}</p>
            </button>
          ))}
          {projects.length === 0 && <p className="text-sm text-nexus-text-muted">Aucun projet encore.</p>}
        </div>

        <div className="md:col-span-2 space-y-6">
          <div className="nexus-card p-5">
            <h2 className="font-medium mb-3">Ajouter une tâche</h2>
            <form onSubmit={handleAddTask} className="grid grid-cols-3 gap-3">
              <input required placeholder="Titre" value={taskForm.title} onChange={(e) => setTaskForm((p) => ({ ...p, title: e.target.value }))} className="nexus-input col-span-2" />
              <select value={taskForm.priority} onChange={(e) => setTaskForm((p) => ({ ...p, priority: e.target.value }))} className="nexus-input">
                <option value="basse">Basse</option>
                <option value="moyenne">Moyenne</option>
                <option value="haute">Haute</option>
                <option value="critique">Critique</option>
              </select>
              <button type="submit" disabled={!selectedId} className="nexus-btn-primary col-span-3">Ajouter</button>
            </form>
          </div>

          <div className="nexus-card p-5">
            <h2 className="font-medium mb-3">Tâches</h2>
            <div className="space-y-2">
              {tasks.map((task) => (
                <div key={task.id} className="flex items-center justify-between text-sm py-1.5">
                  <p className="font-medium">{task.title}</p>
                  <select
                    value={task.status}
                    onChange={(e) => updateTaskStatus(task.id, e.target.value)}
                    className="nexus-input text-xs py-1"
                  >
                    <option value="a_faire">À faire</option>
                    <option value="en_cours">En cours</option>
                    <option value="en_revue">En revue</option>
                    <option value="termine">Terminé</option>
                    <option value="bloque">Bloqué</option>
                  </select>
                </div>
              ))}
              {tasks.length === 0 && <p className="text-sm text-nexus-text-muted">Aucune tâche pour ce projet.</p>}
            </div>
          </div>
        </div>
      </div>

      {isFormOpen && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50">
          <div className="nexus-card w-full max-w-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-lg">Nouveau projet</h2>
              <button onClick={() => setIsFormOpen(false)}><X size={20} /></button>
            </div>
            <form onSubmit={handleCreateProject} className="space-y-3">
              <input required placeholder="Nom du projet" value={projectForm.name} onChange={(e) => setProjectForm((p) => ({ ...p, name: e.target.value }))} className="nexus-input w-full" />
              <textarea required placeholder="Description" value={projectForm.description} onChange={(e) => setProjectForm((p) => ({ ...p, description: e.target.value }))} rows={2} className="nexus-input w-full resize-none" />
              <input required placeholder="Type (web, mobile, API...)" value={projectForm.project_type} onChange={(e) => setProjectForm((p) => ({ ...p, project_type: e.target.value }))} className="nexus-input w-full" />
              {error && <p className="text-sm text-red-400">{error}</p>}
              <button type="submit" className="nexus-btn-primary w-full">Créer</button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
