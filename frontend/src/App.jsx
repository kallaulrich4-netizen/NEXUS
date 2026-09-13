import { Routes, Route } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import RequireAuth from "./components/RequireAuth";
import AppLayout from "./layouts/AppLayout";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import AiAssistant from "./pages/modules/AiAssistant";
import Social from "./pages/modules/Social";
import Marketplace from "./pages/modules/Marketplace";
import Finance from "./pages/modules/Finance";
import Maps from "./pages/modules/Maps";
import Agriculture from "./pages/modules/Agriculture";
import Livestock from "./pages/modules/Livestock";
import Legal from "./pages/modules/Legal";
import Business from "./pages/modules/Business";
import Education from "./pages/modules/Education";
import Studio from "./pages/modules/Studio";
import DevTools from "./pages/modules/DevTools";
import Cybersecurity from "./pages/modules/Cybersecurity";
import DevOps from "./pages/modules/DevOps";
import Payments from "./pages/modules/Payments";
import Settings from "./pages/modules/Settings";
import Notifications from "./pages/Notifications";
import ActivityLog from "./pages/ActivityLog";
import Admin from "./pages/Admin";
import ModuleScaffold from "./pages/modules/ModuleScaffold";
import { MODULES } from "./config/modules";

// Tous les modules ont désormais leur propre page dédiée, entièrement connectée au backend.
const CUSTOM_PAGES = {
  ai: AiAssistant,
  social: Social,
  marketplace: Marketplace,
  finance: Finance,
  payments: Payments,
  maps: Maps,
  agriculture: Agriculture,
  livestock: Livestock,
  legal: Legal,
  business: Business,
  education: Education,
  studio: Studio,
  devtools: DevTools,
  cybersecurity: Cybersecurity,
  devops: DevOps,
};

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        <Route
          element={
            <RequireAuth>
              <AppLayout />
            </RequireAuth>
          }
        >
          <Route path="/" element={<Dashboard />} />
          {MODULES.map((mod) => {
            const CustomPage = CUSTOM_PAGES[mod.key];
            return (
              <Route
                key={mod.key}
                path={mod.path}
                element={CustomPage ? <CustomPage /> : <ModuleScaffold moduleKey={mod.key} />}
              />
            );
          })}
          <Route path="/settings" element={<Settings />} />
          <Route path="/notifications" element={<Notifications />} />
          <Route path="/activity-log" element={<ActivityLog />} />
          <Route path="/admin" element={<Admin />} />
        </Route>
      </Routes>
    </AuthProvider>
  );
}
