import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { User, Lock, Crown, AlertTriangle, Loader2, Check, History, ShieldCheck } from "lucide-react";
import { apiRequest } from "../../api/client";
import { useAuth } from "../../context/AuthContext";

const LANGUAGES = [
  { value: "fr", label: "Français" },
  { value: "en", label: "English" },
];

export default function Settings() {
  const { user, refreshUser, logout } = useAuth();
  const navigate = useNavigate();

  const [profileForm, setProfileForm] = useState({ full_name: "", preferred_language: "fr", country: "" });
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileMessage, setProfileMessage] = useState("");
  const [profileError, setProfileError] = useState("");

  const [passwordForm, setPasswordForm] = useState({ current_password: "", new_password: "", confirm_password: "" });
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [passwordMessage, setPasswordMessage] = useState("");
  const [passwordError, setPasswordError] = useState("");

  const [activeSubscription, setActiveSubscription] = useState(null);

  const [showDeactivateConfirm, setShowDeactivateConfirm] = useState(false);
  const [deactivating, setDeactivating] = useState(false);
  const [deactivateError, setDeactivateError] = useState("");

  useEffect(() => {
    if (user) {
      setProfileForm({
        full_name: user.full_name || "",
        preferred_language: user.preferred_language || "fr",
        country: user.country || "",
      });
    }
  }, [user]);

  useEffect(() => {
    apiRequest("/payments/subscriptions/mine/active")
      .then(setActiveSubscription)
      .catch(() => setActiveSubscription(null));
  }, []);

  async function handleProfileSubmit(e) {
    e.preventDefault();
    setProfileSaving(true);
    setProfileMessage("");
    setProfileError("");
    try {
      await apiRequest("/auth/me", { method: "PATCH", body: profileForm });
      await refreshUser();
      setProfileMessage("Profil mis à jour avec succès.");
    } catch (err) {
      setProfileError(err.detail || "Impossible de mettre à jour le profil.");
    } finally {
      setProfileSaving(false);
    }
  }

  async function handlePasswordSubmit(e) {
    e.preventDefault();
    setPasswordMessage("");
    setPasswordError("");

    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setPasswordError("Les deux mots de passe ne correspondent pas.");
      return;
    }

    setPasswordSaving(true);
    try {
      await apiRequest("/auth/me/change-password", {
        method: "POST",
        body: {
          current_password: passwordForm.current_password,
          new_password: passwordForm.new_password,
        },
      });
      setPasswordMessage("Mot de passe modifié avec succès.");
      setPasswordForm({ current_password: "", new_password: "", confirm_password: "" });
    } catch (err) {
      setPasswordError(err.detail || "Impossible de modifier le mot de passe.");
    } finally {
      setPasswordSaving(false);
    }
  }

  async function handleDeactivate() {
    setDeactivating(true);
    setDeactivateError("");
    try {
      await apiRequest("/auth/me", { method: "DELETE" });
      logout();
      navigate("/login");
    } catch (err) {
      setDeactivateError(err.detail || "Impossible de désactiver le compte.");
      setDeactivating(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-xl font-semibold">Paramètres</h1>

      {/* Profil */}
      <section className="nexus-card p-5">
        <div className="flex items-center gap-2 mb-4">
          <User size={18} className="text-nexus-blue" />
          <h2 className="font-medium">Profil</h2>
        </div>
        <form onSubmit={handleProfileSubmit} className="space-y-3">
          <div>
            <label className="text-xs text-nexus-text-muted block mb-1">Nom complet</label>
            <input
              required
              value={profileForm.full_name}
              onChange={(e) => setProfileForm((p) => ({ ...p, full_name: e.target.value }))}
              className="nexus-input w-full"
            />
          </div>
          <div>
            <label className="text-xs text-nexus-text-muted block mb-1">Email</label>
            <input value={user?.email || ""} disabled className="nexus-input w-full opacity-60 cursor-not-allowed" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-nexus-text-muted block mb-1">Langue préférée</label>
              <select
                value={profileForm.preferred_language}
                onChange={(e) => setProfileForm((p) => ({ ...p, preferred_language: e.target.value }))}
                className="nexus-input w-full"
              >
                {LANGUAGES.map((lang) => (
                  <option key={lang.value} value={lang.value}>
                    {lang.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-nexus-text-muted block mb-1">Pays</label>
              <input
                value={profileForm.country}
                onChange={(e) => setProfileForm((p) => ({ ...p, country: e.target.value }))}
                className="nexus-input w-full"
              />
            </div>
          </div>

          {profileMessage && (
            <p className="text-sm text-emerald-400 flex items-center gap-1.5">
              <Check size={14} /> {profileMessage}
            </p>
          )}
          {profileError && <p className="text-sm text-red-400">{profileError}</p>}

          <button type="submit" disabled={profileSaving} className="nexus-btn-primary text-sm flex items-center gap-2">
            {profileSaving && <Loader2 size={14} className="animate-spin" />}
            Enregistrer
          </button>
        </form>
      </section>

      {/* Sécurité */}
      <section className="nexus-card p-5">
        <div className="flex items-center gap-2 mb-4">
          <Lock size={18} className="text-nexus-blue" />
          <h2 className="font-medium">Sécurité</h2>
        </div>
        <form onSubmit={handlePasswordSubmit} className="space-y-3">
          <div>
            <label className="text-xs text-nexus-text-muted block mb-1">Mot de passe actuel</label>
            <input
              required
              type="password"
              value={passwordForm.current_password}
              onChange={(e) => setPasswordForm((p) => ({ ...p, current_password: e.target.value }))}
              className="nexus-input w-full"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-nexus-text-muted block mb-1">Nouveau mot de passe</label>
              <input
                required
                type="password"
                minLength={10}
                value={passwordForm.new_password}
                onChange={(e) => setPasswordForm((p) => ({ ...p, new_password: e.target.value }))}
                className="nexus-input w-full"
              />
            </div>
            <div>
              <label className="text-xs text-nexus-text-muted block mb-1">Confirmer</label>
              <input
                required
                type="password"
                value={passwordForm.confirm_password}
                onChange={(e) => setPasswordForm((p) => ({ ...p, confirm_password: e.target.value }))}
                className="nexus-input w-full"
              />
            </div>
          </div>
          <p className="text-xs text-nexus-text-muted">
            Au moins 10 caractères, avec une majuscule et un chiffre.
          </p>

          {passwordMessage && (
            <p className="text-sm text-emerald-400 flex items-center gap-1.5">
              <Check size={14} /> {passwordMessage}
            </p>
          )}
          {passwordError && <p className="text-sm text-red-400">{passwordError}</p>}

          <button
            type="submit"
            disabled={passwordSaving}
            className="nexus-btn-primary text-sm flex items-center gap-2"
          >
            {passwordSaving && <Loader2 size={14} className="animate-spin" />}
            Modifier le mot de passe
          </button>
        </form>
      </section>

      {/* Abonnement */}
      <section className="nexus-card p-5">
        <div className="flex items-center gap-2 mb-2">
          <Crown size={18} className="text-amber-400" />
          <h2 className="font-medium">Abonnement</h2>
        </div>
        {activeSubscription ? (
          <p className="text-sm text-nexus-text-muted">
            Abonnement <span className="text-emerald-400 font-medium">actif</span> jusqu'au{" "}
            {activeSubscription.ends_at ? new Date(activeSubscription.ends_at).toLocaleDateString("fr-FR") : "—"}.
          </p>
        ) : (
          <p className="text-sm text-nexus-text-muted">Aucun abonnement actif.</p>
        )}
        <Link to="/payments" className="nexus-btn-secondary text-sm inline-flex items-center gap-2 mt-3">
          <Crown size={14} /> Gérer mon abonnement
        </Link>
      </section>

      {/* Plateforme */}
      <section className="nexus-card p-5">
        <h2 className="font-medium mb-3">Plateforme</h2>
        <div className="flex flex-wrap gap-2">
          <Link to="/activity-log" className="nexus-btn-secondary text-sm inline-flex items-center gap-2">
            <History size={14} /> Journal d'activité
          </Link>
          {user?.is_superuser && (
            <Link to="/admin" className="nexus-btn-secondary text-sm inline-flex items-center gap-2">
              <ShieldCheck size={14} /> Centre d'administration
            </Link>
          )}
        </div>
      </section>

      {/* Zone dangereuse */}
      <section className="nexus-card p-5 border border-red-500/30">
        <div className="flex items-center gap-2 mb-2 text-red-400">
          <AlertTriangle size={18} />
          <h2 className="font-medium">Zone dangereuse</h2>
        </div>
        <p className="text-sm text-nexus-text-muted mb-3">
          La désactivation de votre compte vous déconnectera immédiatement et empêchera toute nouvelle connexion.
          Votre historique dans les autres modules (agriculture, élevage, finance...) est conservé conformément aux
          obligations légales de conservation des données.
        </p>

        {deactivateError && <p className="text-sm text-red-400 mb-2">{deactivateError}</p>}

        {!showDeactivateConfirm ? (
          <button
            onClick={() => setShowDeactivateConfirm(true)}
            className="text-sm px-4 py-2 rounded-xl border border-red-500/50 text-red-400 hover:bg-red-500/10 transition-colors"
          >
            Désactiver mon compte
          </button>
        ) : (
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm">Confirmez-vous la désactivation de votre compte ?</p>
            <button
              onClick={handleDeactivate}
              disabled={deactivating}
              className="text-sm px-3 py-1.5 rounded-xl bg-red-500 text-white flex items-center gap-2"
            >
              {deactivating && <Loader2 size={14} className="animate-spin" />}
              Oui, désactiver
            </button>
            <button
              onClick={() => setShowDeactivateConfirm(false)}
              className="text-sm px-3 py-1.5 rounded-xl nexus-btn-secondary"
            >
              Annuler
            </button>
          </div>
        )}
      </section>
    </div>
  );
}
