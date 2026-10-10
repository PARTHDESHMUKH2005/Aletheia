import { Route, Routes } from "react-router-dom";
import Upload from "./pages/Upload.jsx";
import Result from "./pages/Result.jsx";
import MapPage from "./pages/Map.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Verify from "./pages/Verify.jsx";
import Review from "./pages/Review.jsx";
import Passport from "./pages/Passport.jsx";
import AppLayout from "./components/AppLayout.jsx";
import "./styles/passport.css";

export default function App() {
  return (
    <AppLayout>
        <Routes>
          <Route path="/" element={<Upload />} />
          <Route path="/streams/:streamId" element={<Result />} />
          <Route path="/map" element={<MapPage />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/review" element={<Review />} />
          <Route path="/passports" element={<Passport />} />
          <Route path="/passports/:passportId" element={<Passport />} />
          <Route path="/verify" element={<Verify />} />
          <Route path="/verify/:chainId" element={<Verify />} />
        </Routes>
    </AppLayout>
  );
}
