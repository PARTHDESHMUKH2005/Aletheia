import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.markercluster";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";
import "leaflet.heat";
import { api } from "../api.js";
import { addBaseLayers, TIER_COLOR } from "../lib/mapKit.js";

export default function MapPage() {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.listProcessors().then((processors) => {
      if (!containerRef.current || mapRef.current) return;
      const map = L.map(containerRef.current).setView([30.6, 76.3], 7);
      mapRef.current = map;
      const control = addBaseLayers(map);

      const cluster = L.markerClusterGroup({ showCoverageOnHover: false });
      const heatPoints = [];
      processors.forEach((p) => {
        if (p.location?.lat == null || p.location?.lng == null) return;
        const color = TIER_COLOR[p.tier] || "#374151";
        cluster.addLayer(
          L.circleMarker([p.location.lat, p.location.lng], {
            radius: 8, color, fillColor: color, fillOpacity: 0.7,
          }).bindPopup(
            `<strong>${p.name}</strong> (seeded)<br/>${p.tier}<br/>accepts: ${p.accepted_materials.join(", ")}<br/>` +
            `<span style="font-size:11px">${p.authorization_label || "demo only, authorization not checked"}</span>`,
          ),
        );
        // Weight by how many materials the processor accepts: a proxy for handling capacity, not waste volume.
        heatPoints.push([p.location.lat, p.location.lng, Math.min(1, p.accepted_materials.length / 6)]);
      });
      map.addLayer(cluster);
      const heat = L.heatLayer(heatPoints, { radius: 35, blur: 25, maxZoom: 9 });
      control.addOverlay(cluster, "Processors (clustered)");
      control.addOverlay(heat, "Density heatmap");

      const legend = L.control({ position: "bottomleft" });
      legend.onAdd = () => {
        const div = L.DomUtil.create("div", "leaflet-bar");
        div.style.cssText = "background:#fff;padding:6px 8px;font-size:12px;line-height:1.5;color:#111";
        div.innerHTML = Object.entries(TIER_COLOR)
          .map(([tier, c]) => `<div><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${c};margin-right:6px"></span>${tier}</div>`)
          .join("");
        return div;
      };
      legend.addTo(map);
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
        All markers are seeded example data, not verified real entities. The heatmap shows processor
        density (weighted by materials accepted), not waste volume. Use the layer control (top right) to switch basemaps and overlays.
      </p>
      {error && <div className="text-sm text-red-600 mb-2">{error}</div>}
      <div ref={containerRef} style={{ height: "500px" }} className="rounded-lg border" />
    </div>
  );
}
