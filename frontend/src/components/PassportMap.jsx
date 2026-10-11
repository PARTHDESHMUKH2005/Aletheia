import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { addBaseLayers, fetchRoadRoute, scoreColor, TIER_COLOR } from "../lib/mapKit.js";

const EMPTY = [];

// Pickup point, the chosen processor (highlighted) with a road route, and the other
// ranked options (colour-coded by carbon score). `candidates` are the routing candidates.
export default function PassportMap({ pickup, picked, others = EMPTY, candidates = EMPTY }) {
  const ref = useRef(null);

  useEffect(() => {
    if (!ref.current || !pickup) return;
    const map = L.map(ref.current, { scrollWheelZoom: false });
    addBaseLayers(map);
    const byId = Object.fromEntries(candidates.map((c) => [c.processor_id, c]));
    const abort = new AbortController();

    const start = [pickup.lat, pickup.lng];
    const points = [start];
    L.circleMarker(start, { radius: 9, color: "#1d4ed8", fillColor: "#3b82f6", fillOpacity: 0.9 })
      .addTo(map).bindPopup(`<strong>Pickup</strong><br/>${pickup.address} (${pickup.pincode})`);

    others.forEach((p) => {
      if (p.location?.lat == null) return;
      const c = byId[p.id];
      const color = scoreColor(c?.carbon_score);
      L.circleMarker([p.location.lat, p.location.lng], { radius: 7, color, fillColor: color, fillOpacity: 0.7 })
        .addTo(map)
        .bindPopup(`${p.name}<br/>${p.tier} · alternative${c ? `<br/>${c.distance_km} km · carbon score ${Math.round((c.carbon_score ?? 0) * 100)}%` : ""}`);
      points.push([p.location.lat, p.location.lng]);
    });

    if (picked?.location?.lat != null) {
      const dest = [picked.location.lat, picked.location.lng];
      const color = TIER_COLOR[picked.tier] || "#15803d";
      const c = byId[picked.id];
      const straightKm = c?.distance_km;

      const line = L.polyline([start, dest], { color, weight: 3, dashArray: "6 6" }).addTo(map);
      line.bindTooltip(`Straight line${straightKm != null ? ` · ${straightKm} km` : ""} (loading road route…)`, { sticky: true });

      L.circleMarker(dest, { radius: 10, color, fillColor: color, fillOpacity: 0.9 })
        .addTo(map).bindPopup(`<strong>${picked.name}</strong> (seeded)<br/>${picked.tier}`).openPopup();
      points.push(dest);

      fetchRoadRoute(start, dest, abort.signal).then((route) => {
        if (!route || abort.signal.aborted) {
          if (!abort.signal.aborted) line.setTooltipContent(`Straight line${straightKm != null ? ` · ${straightKm} km` : ""} (road route unavailable)`);
          return;
        }
        line.remove();
        const road = L.polyline(route.latlngs, { color, weight: 4 }).addTo(map);
        // Transport CO2e is computed by the backend on the straight-line distance; scale it to the road distance.
        const co2 = c?.transport_co2e_kg != null && straightKm
          ? ` · ~${(c.transport_co2e_kg * (route.km / straightKm)).toFixed(2)} kg CO₂e transport`
          : "";
        road.bindTooltip(`Road ${route.km.toFixed(1)} km${straightKm != null ? ` (straight ${straightKm} km)` : ""}${co2}`, { sticky: true });
        map.fitBounds(road.getBounds().extend(points), { padding: [40, 40], maxZoom: 11 });
      });
    }
    map.fitBounds(points, { padding: [40, 40], maxZoom: 11 });
    return () => { abort.abort(); map.remove(); };
  }, [pickup, picked, others, candidates]);

  if (!pickup) return <p className="lb-note">No pickup location is available for this record.</p>;
  return <div ref={ref} style={{ height: 300 }} className="lb-passport-map" role="img" aria-label="Map of pickup point and processor" />;
}
