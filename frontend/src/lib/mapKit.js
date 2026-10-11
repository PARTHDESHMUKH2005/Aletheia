import L from "leaflet";

export const TIER_COLOR = {
  reuse: "#15803d", refurbish: "#0369a1", recycle: "#374151", recovery: "#a16207", disposal: "#991b1b",
};

// Street / dark / satellite basemaps with a switcher control.
export function addBaseLayers(map) {
  const street = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors", maxZoom: 19,
  });
  const dark = L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    attribution: "&copy; OpenStreetMap contributors &copy; CARTO", maxZoom: 19,
  });
  const satellite = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    { attribution: "Tiles &copy; Esri", maxZoom: 18 },
  );
  street.addTo(map);
  const control = L.control.layers({ Street: street, Dark: dark, Satellite: satellite }, {}, { collapsed: true }).addTo(map);
  return control;
}

// Green = strong score, amber = middling, red = weak. Used to colour-code buyers.
export function scoreColor(score) {
  if (score == null) return "#9ca3af";
  if (score >= 0.8) return "#16a34a";
  if (score >= 0.5) return "#d97706";
  return "#dc2626";
}

// Driving route from the public OSRM demo server. Resolves to null on any failure
// (offline, rate limit, no route) so callers can fall back to a straight line.
const routeCache = new Map();
export async function fetchRoadRoute(from, to, signal) {
  const key = `${from}|${to}`;
  if (routeCache.has(key)) return routeCache.get(key);
  const url = `https://router.project-osrm.org/route/v1/driving/${from[1]},${from[0]};${to[1]},${to[0]}?overview=full&geometries=geojson`;
  try {
    const res = await fetch(url, { signal });
    if (!res.ok) return null;
    const data = await res.json();
    const route = data.routes?.[0];
    if (!route) return null;
    const result = {
      latlngs: route.geometry.coordinates.map(([lng, lat]) => [lat, lng]),
      km: route.distance / 1000,
    };
    routeCache.set(key, result);
    return result;
  } catch {
    return null;
  }
}
