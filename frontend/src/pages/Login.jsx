import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setError(err.detail || "Email ou mot de passe incorrect.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-nexus-bg px-4">
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-2 justify-center mb-8">
          <div className="w-9 h-9 rounded-lg bg-nexus-gradient flex items-center justify-center font-bold text-white">
            N
          </div>
          <span className="font-bold text-xl tracking-tight">NEXUS</span>
        </div>

        <div className="nexus-card p-6">
          <h1 className="text-xl font-semibold mb-1">Content de vous revoir</h1>
          <p className="text-sm text-nexus-text-muted mb-6">Connectez-vous pour accéder à vos modules.</p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-sm font-medium block mb-1.5" htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="nexus-input w-full"
                placeholder="vous@exemple.com"
              />
            </div>
            <div>
              <label className="text-sm font-medium block mb-1.5" htmlFor="password">Mot de passe</label>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="nexus-input w-full"
                placeholder="••••••••••"
              />
            </div>

            {error && <p className="text-sm text-red-400">{error}</p>}

            <button type="submit" disabled={isSubmitting} className="nexus-btn-primary w-full">
              {isSubmitting ? "Connexion..." : "Se connecter"}
            </button>
          </form>
        </div>

        <p className="text-center text-sm text-nexus-text-muted mt-6">
          Pas encore de compte ?{" "}
          <Link to="/register" className="text-nexus-blue hover:underline">
            Créer un compte
          </Link>
        </p>
      </div>
    </div>
  );
}
