import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import App from "./App.jsx";
import "./index.css";
const Landing = React.lazy(() => import("./marketing/index.js").then(m => ({ default: m.Landing }))); // marketing (src/marketing/REVERT.md)
const About = React.lazy(() => import("./marketing/index.js").then(m => ({ default: m.About }))); // marketing (src/marketing/REVERT.md)

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <React.Suspense fallback={null}><Routes><Route path="/" element={<Landing />} /><Route path="/about" element={<About />} /><Route path="*" element={<App />} /></Routes></React.Suspense>
    </BrowserRouter>
  </React.StrictMode>,
);
