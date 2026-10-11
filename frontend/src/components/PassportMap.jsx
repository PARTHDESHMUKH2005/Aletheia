import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const TIER_COLOR = { reuse: "#15803d", refurbish: "#0369a1", recycle: "#374151", recovery: "#a16207", disposal: "#991b1b" };

// Pickup point, the chosen processor (highlighted), and the other ranked options (faint).
export default function PassportMap({ pickup, picked, others = [] }) {
  const ref = useRef(null);

  useEffect(() => {
    if (!ref.current || !pickup) return;
    const map = L.map(ref.current, { scrollWheelZoom: false });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);

    const points = [[pickup.lat, pickup.lng]];
    L.circleMarker(points[0], { radius: 9, color: "#1d4ed8", fillColor: "#3b82f6", fillOpacity: 0.9 })
      .addTo(map).bindPopup(`<strong>Pickup</strong><br/>${pickup.address} (${pickup.pincode})`);

    others.forEach((p) => {
      if (p.location?.lat == null) return;
      L.circleMarker([p.location.lat, p.location.lng], { radius: 6, color: "#9ca3af", fillColor: "#9ca3af", fillOpacity: 0.5 })
        .addTo(map).bindPopup(`${p.name}<br/>${p.tier} · alternative`);
      points.push([p.location.lat, p.location.lng]);
    });

    if (picked?.location?.lat != null) {
      const dest = [picked.location.lat, picked.location.lng];
      const color = TIER_COLOR[picked.tier] || "#15803d";
      L.polyline([points[0], dest], { color, weight: 3, dashArray: "6 6" }).addTo(map);
      L.circleMarker(dest, { radius: 10, color, fillColor: color, fillOpacity: 0.9 })
        .addTo(map).bindPopup(`<strong>${picked.name}</strong> (seeded)<br/>${picked.tier}`).openPopup();
      points.push(dest);
    }
    map.fitBounds(points, { padding: [40, 40], maxZoom: 11 });
    return () => map.remove();
  }, [pickup, picked, others]);

  if (!pickup) return <p className="lb-note">No pickup location is available for this record.</p>;
  return <div ref={ref} style={{ height: 300 }} className="lb-passport-map" role="img" aria-label="Map of pickup point and processor" />;
}
