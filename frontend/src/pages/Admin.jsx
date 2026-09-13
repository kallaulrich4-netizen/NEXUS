import { useEffect, useState } from "react";
import { ShieldCheck, Users, UserCheck, UserX, Crown, Loader2 } from "lucide-react";
import { apiRequest } from "../api/client";

export default function Admin() {
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => { load(); }, []);

  async function load() {
    setIsLoading(true);
    setError("");
    try {
      const [statsData, usersData] = await Promise.all([
        apiRequest("/auth/admin/stats"),
        apiRequest("/auth/admin/users"),
      ]);
      setStats(statsData);
      setUsers(usersData);
    } catch (err) {
      setError(err.detail || "Accès refusé ou impossible de charger les données d'administration.");
    } finally {
      setIsLoading(false);
    }
  }

  async function toggleActive(user) {
    try {
      await apiRequest(`/auth/admin/users/${user.id}`, { method: "PATCH", body: { is_active: !user.is_active } });
      setUsers((prev) => prev.map((u) => (u.id === user.id ? { ...u, is_active: !u.is_active } : u)));
    } catch (err) { setError(err.detail || "Impossible de mettre à jour l'utilisateur."); }
  }

  async function toggleSuperuser(user) {
    try {
      await apiRequest(`/auth/admin/users/${user.id}`, { method: "PATCH", body: { is_superuser: !user.is_superuser } });
      setUsers((prev) => prev.map((u) => (u.id === user.id ? { ...u, is_superuser: !u.is_superuser } : u)));
    } catch (err) { setError(err.detail || "Impossible de mettre à jour le rôle."); }
  }

  if (isLoading) {
    return (
      <div className="max-w-5xl mx-auto flex items-center justify-center py-24 text-nexus-text-muted">
        <Loader2 className="animate-spin mr-2" size={18} /> Chargement...
      </div>
    );
  }

  if (error && !stats) {
    return (
      <div className="max-w-5xl mx-auto">
        <p className="text-sm text-red-400">{error}</p>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <h1 className="text-xl font-semibold flex items-center gap-2"><ShieldCheck size={20} /> Centre d'administration</h1>

      {error && <p className="text-sm text-red-400">{error}</p>}

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Stat icon={Users} label="Utilisateurs" value={stats.total_users} />
          <Stat icon={UserCheck} label="Comptes actifs" value={stats.active_users} accent="text-emerald-400" />
          <Stat icon={Crown} label="Administrateurs" value={stats.superusers} accent="text-amber-400" />
          <Stat icon={Users} label="Nouveaux (30j)" value={stats.new_users_last_30_days} accent="text-nexus-blue" />
        </div>
      )}

      <div className="nexus-card overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-nexus-text-muted border-b border-nexus-border">
              <th className="p-3 font-medium">Utilisateur</th>
              <th className="p-3 font-medium">Email</th>
              <th className="p-3 font-medium">Statut</th>
              <th className="p-3 font-medium">Rôle</th>
              <th className="p-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-b border-nexus-border last:border-0">
                <td className="p-3 font-medium">{u.full_name}</td>
                <td className="p-3 text-nexus-text-muted">{u.email}</td>
                <td className="p-3">
                  <span className={`text-xs px-2 py-1 rounded-full ${u.is_active ? "bg-emerald-500/20 text-emerald-400" : "bg-red-500/20 text-red-400"}`}>
                    {u.is_active ? "Actif" : "Désactivé"}
                  </span>
                </td>
                <td className="p-3">
                  <span className={`text-xs px-2 py-1 rounded-full ${u.is_superuser ? "bg-amber-500/20 text-amber-400" : "bg-nexus-surface-hover text-nexus-text-muted"}`}>
                    {u.is_superuser ? "Administrateur" : "Utilisateur"}
                  </span>
                </td>
                <td className="p-3 flex gap-2">
                  <button onClick={() => toggleActive(u)} className="nexus-btn-secondary text-xs py-1 px-2 flex items-center gap-1">
                    {u.is_active ? <UserX size={12} /> : <UserCheck size={12} />}
                    {u.is_active ? "Désactiver" : "Réactiver"}
                  </button>
                  <button onClick={() => toggleSuperuser(u)} className="nexus-btn-secondary text-xs py-1 px-2 flex items-center gap-1">
                    <Crown size={12} /> {u.is_superuser ? "Retirer admin" : "Rendre admin"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Stat({ icon: Icon, label, value, accent = "text-nexus-text" }) {
  return (
    <div className="nexus-card p-4 flex items-center gap-3">
      <div className={`w-9 h-9 rounded-xl bg-nexus-bg flex items-center justify-center ${accent}`}>
        <Icon size={18} />
      </div>
      <div>
        <p className="text-lg font-bold leading-tight">{value}</p>
        <p className="text-xs text-nexus-text-muted">{label}</p>
      </div>
    </div>
  );
}
