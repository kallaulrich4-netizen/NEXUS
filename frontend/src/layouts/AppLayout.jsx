import { Outlet } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import Topbar from "../components/Topbar";
import MobileNav from "../components/MobileNav";

export default function AppLayout() {
  return (
    <div className="flex min-h-screen bg-nexus-bg">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar />
        <main className="flex-1 px-4 md:px-8 py-6 pb-24 md:pb-8">
          <Outlet />
        </main>
      </div>
      <MobileNav />
    </div>
  );
}
