import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ full_name: "", email: "", password: "", country: "" });
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      await register(form);
      navigate("/");
    } catch (err) {
      setError(err.detail || "Impossible de créer le compte.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-nexus-bg px-4 py-10">
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-2 justify-center mb-8">
          <div className="w-9 h-9 rounded-lg bg-nexus-gradient flex items-center justify-center font-bold text-white">
            N
          </div>
          <span className="font-bold text-xl tracking-tight">NEXUS</span>
        </div>

        <div className="nexus-card p-6">
          <h1 className="text-xl font-semibold mb-1">Créer votre compte</h1>
          <p className="text-sm text-nexus-text-muted mb-6">
            24h d'accès complet à toutes les fonctionnalités premium, sans engagement.
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-sm font-medium block mb-1.5" htmlFor="full_name">Nom complet</label>
              <input
                id="full_name"
                required
                value={form.full_name}
                onChange={(e) => update("full_name", e.target.value)}
                className="nexus-input w-full"
                placeholder="Votre nom"
              />
            </div>
            <div>
              <label className="text-sm font-medium block mb-1.5" htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
                required
                value={form.email}
                onChange={(e) => update("email", e.target.value)}
                className="nexus-input w-full"
                placeholder="vous@exemple.com"
              />
            </div>
            <div>
              <label className="text-sm font-medium block mb-1.5" htmlFor="country">Pays</label>
              <input
                id="country"
                value={form.country}
                onChange={(e) => update("country", e.target.value)}
                className="nexus-input w-full"
                placeholder="Cameroun"
              />
            </div>
            <div>
              <label className="text-sm font-medium block mb-1.5" htmlFor="password">Mot de passe</label>
              <input
                id="password"
                type="password"
                required
                minLength={10}
                value={form.password}
                onChange={(e) => update("password", e.target.value)}
                className="nexus-input w-full"
                placeholder="Au moins 10 caractères, 1 majuscule, 1 chiffre"
              />
            </div>

            {error && <p className="text-sm text-red-400">{error}</p>}

            <button type="submit" disabled={isSubmitting} className="nexus-btn-primary w-full">
              {isSubmitting ? "Création..." : "Créer mon compte"}
            </button>
          </form>
        </div>

        <p className="text-center text-sm text-nexus-text-muted mt-6">
          Déjà un compte ?{" "}
          <Link to="/login" className="text-nexus-blue hover:underline">
            Se connecter
          </Link>
        </p>
      </div>
    </div>
  );
}
