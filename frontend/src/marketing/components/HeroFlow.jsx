import { useReducedMotion } from "../hooks.js";

// Original illustration: materials enter on the left, pass through the Aletheia loop,
// and leave toward the right destination. Pure SVG.
const sources = [
  { label: "Steel", y: 70, glyph: "M-6 4h12l2-8h-16z" },
  { label: "Paper", y: 160, glyph: "M-5-7h7l3 3v11h-10z" },
  { label: "Laptop", y: 250, glyph: "M-7-5h14v9h-14zM-9 6h18" },
  { label: "Battery", y: 340, glyph: "M-7-4h12v8h-12zM5-1.5h2v3h-2" },
];
const dests = [
  { label: "Recycler", y: 110 },
  { label: "Reuse", y: 205 },
  { label: "Person reviews", y: 300 },
];
const flows = [
  { from: 0, to: 0, dur: 5.2, begin: 0 },
  { from: 1, to: 0, dur: 5.6, begin: 1.4 },
  { from: 2, to: 1, dur: 5.0, begin: 2.6 },
  { from: 3, to: 2, dur: 5.4, begin: 3.6 },
  { from: 0, to: 0, dur: 5.2, begin: 2.6 },
  { from: 2, to: 1, dur: 5.0, begin: 0.2 },
];
const pathFor = (sy, dy) => `M118 ${sy} C 180 ${sy}, 185 205, 236 205 L 284 205 C 335 205, 340 ${dy}, 398 ${dy}`;

export default function HeroFlow() {
  const reduced = useReducedMotion();
  return (
    <svg className="al-heroflow" viewBox="0 0 520 410" role="img"
      aria-label="Illustration: steel, paper, a laptop and a battery flow into the Aletheia loop and come out routed to a recycler, to reuse, or to a person for review.">
      <defs>
        <radialGradient id="al-hf-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="var(--al-pale-sage)" stopOpacity="1" />
          <stop offset="100%" stopColor="var(--al-pale-sage)" stopOpacity="0" />
        </radialGradient>
      </defs>
      <circle cx="260" cy="205" r="120" fill="url(#al-hf-glow)" />
      {flows.map((f, i) => (
        <path key={i} id={`al-flow-${i}`} d={pathFor(sources[f.from].y, dests[f.to].y)} fill="none"
          stroke="var(--al-border-strong)" strokeWidth="1.4" strokeDasharray="3 5" />
      ))}
      {!reduced && flows.map((f, i) => (
        <circle key={i} r="5" fill={f.to === 2 ? "var(--al-gold)" : "var(--al-green)"} opacity="0">
          <animateMotion dur={`${f.dur}s`} begin={`${f.begin}s`} repeatCount="indefinite" rotate="auto" calcMode="spline"
            keyTimes="0;1" keySplines="0.45 0 0.35 1">
            <mpath href={`#al-flow-${i}`} />
          </animateMotion>
          <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.08;0.9;1" dur={`${f.dur}s`} begin={`${f.begin}s`} repeatCount="indefinite" />
        </circle>
      ))}

      {sources.map((s, i) => (
        <g key={s.label} className="al-hf-chip" style={{ animationDelay: `${120 + i * 110}ms` }} transform={`translate(18 ${s.y - 20})`}>
          <rect width="100" height="40" rx="11" fill="var(--al-ivory)" stroke="var(--al-border)" />
          <g transform="translate(22 20)" fill="none" stroke="var(--al-forest)" strokeWidth="1.5" strokeLinejoin="round">
            <circle r="13" fill="var(--al-pale-sage)" stroke="none" /><path d={s.glyph} />
          </g>
          <text x="42" y="25" className="al-hf-text">{s.label}</text>
        </g>
      ))}

      <g className="al-hf-center" transform="translate(260 205)">
        <circle r="46" fill="none" stroke="var(--al-sage)" strokeWidth="1.2" strokeDasharray="2 6" className={reduced ? "" : "al-hf-spin"} />
        <circle r="30" fill="var(--al-forest)" />
        <g transform="scale(1.3)" fill="none" stroke="var(--al-ivory)" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
          <path d="M8.5-5.8A10 10 0 1 0 10 0" /><path d="m4.6-6.6 4.4.6.4-4.4" />
          <circle r="3.2" fill="var(--al-beige)" stroke="none" />
        </g>
      </g>

      {dests.map((d, i) => (
        <g key={d.label} className="al-hf-chip" style={{ animationDelay: `${640 + i * 120}ms` }} transform={`translate(398 ${d.y - 19})`}>
          <rect width="112" height="38" rx="19" fill={i === 2 ? "var(--al-gold-soft)" : "var(--al-pale-sage)"} />
          <circle cx="18" cy="19" r="4" fill={i === 2 ? "var(--al-gold)" : "var(--al-green)"} />
          <text x="30" y="24" className="al-hf-text al-hf-small">{d.label}</text>
        </g>
      ))}
    </svg>
  );
}
