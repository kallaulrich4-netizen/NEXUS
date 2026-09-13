/**
 * Client API central de Nexus.
 *
 * Un seul endroit gère le stockage du jeton JWT et la construction des
 * requêtes — tous les modules (auth, IA, social, marketplace...)
 * passent par `apiRequest`, ce qui évite de dupliquer la logique
 * d'authentification dans chaque page.
 */
const TOKEN_KEY = "nexus_access_token";
const REFRESH_KEY = "nexus_refresh_token";

// En développement, Vite proxifie /api vers le backend FastAPI (voir vite.config.js).
// En production, remplacez par l'URL réelle de votre API déployée.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

export function getAccessToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens({ access_token, refresh_token }) {
  localStorage.setItem(TOKEN_KEY, access_token);
  if (refresh_token) localStorage.setItem(REFRESH_KEY, refresh_token);
}

export function clearTokens() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

class ApiError extends Error {
  constructor(message, status, detail) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

async function tryRefreshToken() {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!response.ok) return false;
    const data = await response.json();
    setTokens(data);
    return true;
  } catch {
    return false;
  }
}

/**
 * Effectue une requête vers l'API Nexus.
 * Rafraîchit automatiquement le jeton une fois en cas de 401, avant d'abandonner.
 */
export async function apiRequest(path, { method = "GET", body, isRetry = false, rawResponse = false } = {}) {
  const token = getAccessToken();
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (response.status === 401 && !isRetry) {
    const refreshed = await tryRefreshToken();
    if (refreshed) {
      return apiRequest(path, { method, body, isRetry: true, rawResponse });
    }
    clearTokens();
    window.location.href = "/login";
    throw new ApiError("Session expirée", 401, "Veuillez vous reconnecter.");
  }

  if (rawResponse) {
    if (!response.ok) throw new ApiError("Erreur de requête", response.status, "Échec du téléchargement.");
    return response;
  }

  if (response.status === 204) return null;

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const detail = data?.detail || "Une erreur est survenue.";
    throw new ApiError(detail, response.status, detail);
  }

  return data;
}

export { ApiError, API_BASE_URL };

/**
 * Importe un fichier (image/vidéo) vers l'API — utilisé par le Studio
 * créatif pour les fichiers sources du montage. Distinct de `apiRequest`
 * car un envoi de fichier utilise `multipart/form-data`, pas du JSON :
 * on laisse volontairement le navigateur poser lui-même l'en-tête
 * Content-Type (avec sa "boundary"), donc pas de "Content-Type": "application/json" ici.
 */
export async function uploadFile(path, file) {
  const token = getAccessToken();
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;

  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (response.status === 401) {
    const refreshed = await tryRefreshToken();
    if (refreshed) return uploadFile(path, file);
    clearTokens();
    window.location.href = "/login";
    throw new ApiError("Session expirée", 401, "Veuillez vous reconnecter.");
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = data?.detail || "Échec de l'envoi du fichier.";
    throw new ApiError(detail, response.status, detail);
  }
  return data;
}
