import { contaminationLevel } from "../lib/contamination.js";

const COLORS = { low: "#16a34a", moderate: "#d97706", high: "#dc2626", unknown: "#9ca3af" };

export default function ContaminationMeter({ item }) {
  const c = contaminationLevel(item);
  const color = COLORS[c.tone];
  return (
    <div role="group" aria-label={`Contamination: ${c.label}`}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{ display: "flex", gap: 4, flex: "0 0 120px" }} aria-hidden="true">
          {[1, 2, 3].map((n) => (
            <span key={n} style={{ flex: 1, height: 8, borderRadius: 4, background: n <= c.level ? color : "#e5e7eb" }} />
          ))}
        </div>
        <strong style={{ color }}>{c.label}</strong>
      </div>
      <p className="lb-note" style={{ margin: "4px 0 0" }}>{c.note}</p>
      {c.contaminants.length > 0 && <p className="lb-note" style={{ margin: "2px 0 0" }}>Seen: {c.contaminants.join("; ")}</p>}
    </div>
  );
}
