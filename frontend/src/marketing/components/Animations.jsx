import { useState } from "react";
import { useInView } from "../hooks.js";
import { demoBatch, demoTotals, handoffs } from "../data.js";
import { DemoTag, Mark } from "./Basics.jsx";

const series = [
  { key: "default", label: "Landfill or informal buyer", cls: "al-bar-default" },
  { key: "money", label: "Routed for most money", cls: "al-bar-money" },
  { key: "carbon", label: "Routed for most carbon saved", cls: "al-bar-carbon" },
];
const valueOf = (row, s, metric) => (s === "default" ? 0 : row[s][metric]);
const fmt = (n, metric) => (metric === "inr" ? `₹${n.toLocaleString("en-IN")}` : `${n} kg`);

export function BarChart() {
  const [metric, setMetric] = useState("inr");
  const [ref, inView] = useInView({ threshold: 0.3 });
  const max = Math.max(...demoBatch.flatMap(r => [r.money[metric], r.carbon[metric]]));
  return (
    <figure className="al-chart" ref={ref}>
      <div className="al-chart-top">
        <div className="al-seg al-seg-small" role="group" aria-label="Chart measure">
          <button aria-pressed={metric === "inr"} onClick={() => setMetric("inr")}>Money recovered</button>
          <button aria-pressed={metric === "co2e"} onClick={() => setMetric("co2e")}>CO2e avoided</button>
          <span className="al-seg-thumb" data-mode={metric === "inr" ? "money" : "carbon"} aria-hidden="true" />
        </div>
        <ul className="al-legend">
          {series.map(s => <li key={s.key}><span className={s.cls} />{s.label}</li>)}
        </ul>
      </div>
      <div className="al-chart-plot" aria-hidden="true">
        {demoBatch.map((row, gi) => (
          <div className="al-chart-group" key={row.material}>
            <div className="al-chart-bars">
              {series.map((s, si) => {
                const v = valueOf(row, s.key, metric);
                return (
                  <div className="al-bar-slot" key={s.key}>
                    <span className="al-bar-val" style={{ opacity: inView ? 1 : 0, transitionDelay: `${gi * 90 + si * 60 + 500}ms` }}>
                      {metric === "inr" ? (v ? `₹${(v / 1000).toFixed(1)}k` : "₹0") : v}
                    </span>
                    <span className={`al-bar ${s.cls}`}
                      style={{ height: inView ? `${Math.max(1.5, (v / max) * 100)}%` : "0%", transitionDelay: `${gi * 90 + si * 60}ms` }} />
                  </div>
                );
              })}
            </div>
            <span className="al-chart-label">{row.material}<small>{row.kg} kg</small></span>
          </div>
        ))}
      </div>
      <table className="al-sr">
        <caption>{metric === "inr" ? "Money recovered in rupees" : "Kilograms of CO2e avoided"} by routing choice, illustrative demo data</caption>
        <thead><tr><th>Material</th>{series.map(s => <th key={s.key}>{s.label}</th>)}</tr></thead>
        <tbody>{demoBatch.map(row => (
          <tr key={row.material}><th>{row.material} ({row.kg} kg)</th>{series.map(s => <td key={s.key}>{fmt(valueOf(row, s.key, metric), metric)}</td>)}</tr>
        ))}</tbody>
      </table>
      <figcaption>
        <div className="al-chart-totals">
          <p><span>Most money</span><strong>₹{demoTotals.inrMostMoney.toLocaleString("en-IN")}</strong> and {demoTotals.co2eMostMoney} kg CO2e</p>
          <p><span>Most carbon saved</span><strong>{demoTotals.co2eMostCarbon} kg CO2e</strong> and ₹{demoTotals.inrMostCarbon.toLocaleString("en-IN")}</p>
          <p><span>Default</span><strong>₹0</strong> and no credit</p>
        </div>
        <DemoTag>Illustrative demo data · one {demoTotals.kg} kg campus batch · synthetic buyers and prices</DemoTag>
      </figcaption>
    </figure>
  );
}

const rings = [
  { inset: 27, dur: 30, items: [{ label: "Metals", a: 20 }, { label: "Paper", a: 200 }] },
  { inset: 14, dur: 44, items: [{ label: "E-waste", a: 80 }, { label: "Cardboard", a: 170 }, { label: "Batteries", a: 290 }] },
  { inset: 2, dur: 60, items: [{ label: "Copper", a: 0 }, { label: "Storage drives", a: 110 }, { label: "Used oil", a: 220 }, { label: "Aluminium", a: 300 }] },
];

export function Orbit() {
  return (
    <div className="al-orbit" role="img" aria-label="The Aletheia mark at the centre with material types orbiting it: metals, paper, e-waste, cardboard, batteries, copper, storage drives, used oil and aluminium.">
      {rings.map((r, ri) => (
        <div key={ri} className="al-orbit-ring" style={{ inset: `${r.inset}%`, "--dur": `${r.dur}s` }}>
          {r.items.map(it => (
            <div key={it.label} className="al-orbit-arm" style={{ transform: `rotate(${it.a}deg)` }}>
              <div className="al-orbit-node">
                <div className="al-orbit-pt" style={{ transform: `rotate(${-it.a}deg)` }}>
                  <div className="al-orbit-pt al-orbit-spin">
                    <div className="al-orbit-label"><span className="al-orbit-dot" />{it.label}</div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ))}
      <div className="al-orbit-core"><Mark size={64} /></div>
    </div>
  );
}

export function Marquee({ rows }) {
  return (
    <div className="al-marquee">
      {rows.map((row, i) => (
        <div key={i} className={`al-marquee-row ${i % 2 ? "al-rev" : ""}`} aria-label={row.label} role="list">
          <div className="al-marquee-track">
            {[0, 1].map(copy => row.items.map(item => (
              <span key={`${copy}-${item}`} className="al-marquee-item" role={copy ? undefined : "listitem"} aria-hidden={copy ? true : undefined}>
                <span className="al-marquee-dot" />{item}
              </span>
            )))}
          </div>
        </div>
      ))}
    </div>
  );
}

// Sheets land one by one and each gets stamped: one sheet per recorded handoff.
export function StampStack() {
  return (
    <div className="al-stamps" role="img" aria-label="Animation: four sheets of paper, one per handoff (matched, collected, weighed, verified), stack up and each receives an Aletheia stamp.">
      {handoffs.map((h, i) => (
        <div key={h} className="al-sheet-pos" style={{ transform: `translate(${i * 14}px, ${-i * 16}px) rotate(${[-4, 2, -1.5, 3][i]}deg)` }}>
          <div className="al-sheet" style={{ animationDelay: `${i * 1.25}s` }}>
            <p className="al-sheet-k">Handoff {i + 1} of 4</p>
            <p className="al-sheet-h">{h}</p>
            <span className="al-sheet-line" /><span className="al-sheet-line al-short" /><span className="al-sheet-line" />
            <div className="al-stamp" style={{ animationDelay: `${i * 1.25}s` }}>
              <svg viewBox="0 0 100 100" aria-hidden="true">
                <circle cx="50" cy="50" r="44" fill="none" stroke="currentColor" strokeWidth="3" />
                <circle cx="50" cy="50" r="37" fill="none" stroke="currentColor" strokeWidth="1.2" strokeDasharray="2 3" />
                <path d="M63 39A14 14 0 1 0 65 50" fill="none" stroke="currentColor" strokeWidth="4" strokeLinecap="round" />
                <path d="m57.5 38 6.2.8.6-6.2" fill="none" stroke="currentColor" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
                <circle cx="50" cy="50" r="4.5" fill="currentColor" />
                <text x="50" y="86" textAnchor="middle" fontSize="9" fontWeight="600" fill="currentColor" letterSpacing="1.5">RECORDED</text>
              </svg>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
