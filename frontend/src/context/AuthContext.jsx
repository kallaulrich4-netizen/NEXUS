import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { apiRequest, getAccessToken, setTokens, clearTokens } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadCurrentUser = useCallback(async () => {
    if (!getAccessToken()) {
      setUser(null);
      setIsLoading(false);
      return;
    }
    try {
      const me = await apiRequest("/auth/me");
      setUser(me);
    } catch {
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCurrentUser();
  }, [loadCurrentUser]);

  async function login(email, password) {
    const tokens = await apiRequest("/auth/login", { method: "POST", body: { email, password } });
    setTokens(tokens);
    await loadCurrentUser();
  }

  async function register(payload) {
    await apiRequest("/auth/register", { method: "POST", body: payload });
    await login(payload.email, payload.password);
  }

  function logout() {
    clearTokens();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout, refreshUser: loadCurrentUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth doit être utilisé à l'intérieur de <AuthProvider>.");
  return context;
}
