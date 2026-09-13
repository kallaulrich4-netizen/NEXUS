import { NavLink } from "react-router-dom";
import { Home, MessageCircle, Sparkles, Bell, User } from "lucide-react";

const ITEMS = [
  { key: "home", label: "Accueil", icon: Home, path: "/" },
  { key: "social", label: "Messages", icon: MessageCircle, path: "/social" },
  { key: "ai", label: "Nexus", icon: Sparkles, path: "/ai", isCenter: true },
  { key: "alerts", label: "Notifications", icon: Bell, path: "/notifications" },
  { key: "profile", label: "Profil", icon: User, path: "/settings" },
];

export default function MobileNav() {
  return (
    <nav className="md:hidden fixed bottom-0 inset-x-0 h-16 bg-nexus-bg/95 backdrop-blur border-t border-nexus-border flex items-center justify-around z-40">
      {ITEMS.map((item) =>
        item.isCenter ? (
          <NavLink
            key={item.key}
            to={item.path}
            className="w-12 h-12 -mt-6 rounded-full bg-nexus-gradient flex items-center justify-center shadow-lg shadow-nexus-blue/30"
          >
            <item.icon size={22} className="text-white" />
          </NavLink>
        ) : (
          <NavLink
            key={item.key}
            to={item.path}
            end={item.path === "/"}
            className={({ isActive }) =>
              `flex flex-col items-center gap-0.5 text-[10px] ${
                isActive ? "text-nexus-blue" : "text-nexus-text-muted"
              }`
            }
          >
            <item.icon size={20} />
            {item.label}
          </NavLink>
        )
      )}
    </nav>
  );
}
