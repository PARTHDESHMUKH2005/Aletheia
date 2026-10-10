import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { api } from "../api.js";

const TIER_COLOR = {
  reuse: "#15803d",
  refurbish: "#0369a1",
  recycle: "#374151",
  recovery: "#a16207",
  disposal: "#991b1b",
};

export default function MapPage() {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.listProcessors().then((processors) => {
      if (!containerRef.current || mapRef.current) return;
      const map = L.map(containerRef.current).setView([30.6, 76.3], 7);
      mapRef.current = map;
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "&copy; OpenStreetMap contributors",
      }).addTo(map);

      processors.forEach((p) => {
        if (p.location?.lat == null || p.location?.lng == null) return;
        const color = TIER_COLOR[p.tier] || "#374151";
        L.circleMarker([p.location.lat, p.location.lng], {
          radius: 8, color, fillColor: color, fillOpacity: 0.7,
        })
          .addTo(map)
          .bindPopup(
            `<strong>${p.name}</strong> (seeded)<br/>${p.tier}<br/>accepts: ${p.accepted_materials.join(", ")}<br/>` +
            `<span style="font-size:11px">${p.authorization_label || "demo only, authorization not checked"}</span>`,
          );
      });
    }).catch((err) => setError(err.message));

    return () => {
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, []);

  return (
    <div>
      <h1 className="text-lg font-semibold mb-1">Seeded processors</h1>
      <p className="text-sm text-gray-500 mb-3">
        All markers are seeded example data, not verified real entities.
      </p>
      {error && <div className="text-sm text-red-600 mb-2">{error}</div>}
      <div ref={containerRef} style={{ height: "500px" }} className="rounded-lg border" />
    </div>
  );
}
