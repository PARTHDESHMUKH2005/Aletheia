import { NavLink, Route, Routes } from "react-router-dom";
import Upload from "./pages/Upload.jsx";
import Result from "./pages/Result.jsx";
import MapPage from "./pages/Map.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Verify from "./pages/Verify.jsx";

const navLink = ({ isActive }) =>
  `px-3 py-2 text-sm rounded-md ${isActive ? "bg-gray-900 text-white" : "text-gray-600 hover:bg-gray-100"}`;

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b bg-white">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <span className="font-semibold">LoopBack</span>
          <nav className="flex gap-1">
            <NavLink to="/" end className={navLink}>Upload</NavLink>
            <NavLink to="/map" className={navLink}>Map</NavLink>
            <NavLink to="/dashboard" className={navLink}>Dashboard</NavLink>
            <NavLink to="/verify" className={navLink}>Verify</NavLink>
          </nav>
        </div>
      </header>

      <main className="flex-1 max-w-5xl w-full mx-auto px-4 py-6">
        <Routes>
          <Route path="/" element={<Upload />} />
          <Route path="/streams/:streamId" element={<Result />} />
          <Route path="/map" element={<MapPage />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/verify" element={<Verify />} />
          <Route path="/verify/:chainId" element={<Verify />} />
        </Routes>
      </main>

      <footer className="border-t bg-gray-900 text-white text-xs text-center py-3 px-4">
        Routing aid only. Confirm rules and processor authorization with the official CPCB or State Board source.
        Photos are sent to the model provider (Google for Gemini). Upload only waste photos, no faces or documents.
      </footer>
    </div>
  );
}
