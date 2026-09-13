import { ExternalLink } from "lucide-react";
import { MODULES } from "../../config/modules";

/**
 * Page d'attente honnête pour les modules dont le backend est complet
 * mais dont l'interface dédiée n'a pas encore été construite (voir
 * AiAssistant.jsx et Social.jsx pour des exemples d'interfaces
 * pleinement connectées, à reproduire module par module).
 */
export default function ModuleScaffold({ moduleKey }) {
  const mod = MODULES.find((m) => m.key === moduleKey);

  if (!mod) {
    return (
      <div className="max-w-2xl mx-auto nexus-card p-6">
        <h1 className="text-xl font-semibold mb-2">Paramètres</h1>
        <p className="text-sm text-nexus-text-muted">
          Page de gestion du compte à construire (profil, langue, statut d'abonnement).
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className={`rounded-2xl p-8 ${mod.color} mb-6`}>
        <mod.icon size={36} className={mod.iconColor} />
        <h1 className="text-2xl font-bold mt-4">{mod.label}</h1>
        <p className="text-white/70 mt-1">{mod.description}</p>
      </div>

      <div className="nexus-card p-6">
        <h2 className="font-semibold mb-2">Backend entièrement fonctionnel, interface à construire</h2>
        <p className="text-sm text-nexus-text-muted mb-4">
          Toutes les routes de ce module ({mod.apiBase}/...) sont opérationnelles côté serveur — création,
          consultation, mise à jour, permissions, tout est déjà testé. Cette page suit le même patron que
          les pages Réseau Social et IA Nexus, déjà entièrement connectées : à construire module par module
          en réutilisant les mêmes composants (nexus-card, nexus-btn-primary, nexus-input) et le même
          client API (`src/api/client.js`).
        </p>
        <a
          href={`${import.meta.env.VITE_API_BASE_URL || "/api"}/docs`}
          target="_blank"
          rel="noreferrer"
          className="nexus-btn-secondary inline-flex items-center gap-2 text-sm"
        >
          Explorer les endpoints de ce module <ExternalLink size={14} />
        </a>
      </div>
    </div>
  );
}
