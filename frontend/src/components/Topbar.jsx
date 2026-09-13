import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Search, Bell, ChevronDown, LogOut, Globe, Settings as SettingsIcon, ShieldCheck } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { apiRequest } from "../api/client";

export default function Topbar() {
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [recentNotifications, setRecentNotifications] = useState([]);
  const pollRef = useRef(null);

  useEffect(() => {
    refreshUnreadCount();
    pollRef.current = setInterval(refreshUnreadCount, 30000);
    return () => clearInterval(pollRef.current);
  }, []);

  function refreshUnreadCount() {
    apiRequest("/notifications/unread-count").then((d) => setUnreadCount(d.unread_count)).catch(() => {});
  }

  function toggleNotifications() {
    const next = !notifOpen;
    setNotifOpen(next);
    if (next) {
      apiRequest("/notifications?unread_only=true").then((d) => setRecentNotifications(d.slice(0, 5))).catch(() => {});
    }
  }

  return (
    <header className="h-16 border-b border-nexus-border flex items-center justify-between gap-4 px-4 md:px-6 sticky top-0 bg-nexus-bg/95 backdrop-blur z-30">
      <div className="flex-1 max-w-md">
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-nexus-text-muted" />
          <input
            type="text"
            placeholder="Rechercher dans Nexus..."
            className="nexus-input w-full pl-9 py-2 text-sm"
          />
        </div>
      </div>

      <div className="flex items-center gap-3 shrink-0">
        <button className="p-2 rounded-lg hover:bg-nexus-surface text-nexus-text-muted" aria-label="Langue">
          <Globe size={18} />
        </button>

        <div className="relative">
          <button
            onClick={toggleNotifications}
            className="relative p-2 rounded-lg hover:bg-nexus-surface text-nexus-text-muted"
            aria-label="Notifications"
          >
            <Bell size={18} />
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-nexus-purple" />
            )}
          </button>

          {notifOpen && (
            <div className="absolute right-0 mt-2 w-80 nexus-card p-2 shadow-xl">
              <div className="flex items-center justify-between px-2 py-1.5">
                <p className="text-sm font-medium">Notifications</p>
                <Link to="/notifications" onClick={() => setNotifOpen(false)} className="text-xs text-nexus-blue">
                  Tout voir
                </Link>
              </div>
              <div className="max-h-80 overflow-y-auto">
                {recentNotifications.map((n) => (
                  <div key={n.id} className="px-2 py-2 rounded-lg hover:bg-nexus-surface-hover">
                    <p className="text-sm font-medium truncate">{n.title}</p>
                    <p className="text-xs text-nexus-text-muted line-clamp-2">{n.message}</p>
                  </div>
                ))}
                {recentNotifications.length === 0 && (
                  <p className="text-xs text-nexus-text-muted px-2 py-4 text-center">Aucune notification non lue.</p>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="relative">
          <button
            onClick={() => setMenuOpen((v) => !v)}
            className="flex items-center gap-2 pl-2 pr-1 py-1 rounded-xl hover:bg-nexus-surface"
          >
            <div className="w-8 h-8 rounded-full bg-nexus-gradient flex items-center justify-center text-sm font-semibold text-white">
              {user?.full_name?.[0]?.toUpperCase() || "?"}
            </div>
            <span className="hidden sm:block text-sm font-medium max-w-[120px] truncate">
              {user?.full_name || "..."}
            </span>
            <ChevronDown size={16} className="text-nexus-text-muted" />
          </button>

          {menuOpen && (
            <div className="absolute right-0 mt-2 w-48 nexus-card p-1.5 shadow-xl">
              <Link
                to="/settings"
                onClick={() => setMenuOpen(false)}
                className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm hover:bg-nexus-surface-hover"
              >
                <SettingsIcon size={16} />
                Paramètres
              </Link>
              {user?.is_superuser && (
                <Link
                  to="/admin"
                  onClick={() => setMenuOpen(false)}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm hover:bg-nexus-surface-hover"
                >
                  <ShieldCheck size={16} />
                  Administration
                </Link>
              )}
              <button
                onClick={logout}
                className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-red-400 hover:bg-nexus-surface-hover"
              >
                <LogOut size={16} />
                Se déconnecter
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
