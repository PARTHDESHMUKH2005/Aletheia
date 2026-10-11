import { useState } from "react";
import { steelDecision, handoffs } from "../data.js";
import { DemoTag } from "./Basics.jsx";

const inr = n => `₹${n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

function WindowBar({ title }) {
  return (
    <div className="al-win-bar" aria-hidden="true">
      <span /><span /><span /><em>{title}</em>
    </div>
  );
}

// Mirrors the working app's decision screen (Processing result): item, slider,
// ranked candidates and the counterfactual receipt. Numbers are the app's own demo
// output for 120 kg of steel scrap from the seeded campus workshop.
export function DecisionMock() {
  const [mode, setMode] = useState("money");
  const d = steelDecision[mode];
  const picked = d.candidates[0];
  return (
    <div className="al-window al-decision">
      <WindowBar title="Processing result" />
      <div className="al-decision-body">
        <div className="al-decision-head">
          <div>
            <p className="al-mini-label">Item 1 of 1</p>
            <h3>Steel scrap · 120 kg <small>stated</small></h3>
          </div>
          <span className="al-pill al-pill-ok">Routed</span>
        </div>

        <div className="al-seg" role="group" aria-label="Routing preference">
          <button aria-pressed={mode === "money"} onClick={() => setMode("money")}>Most money</button>
          <button aria-pressed={mode === "carbon"} onClick={() => setMode("carbon")}>Most carbon saved</button>
          <span className="al-seg-thumb" data-mode={mode} aria-hidden="true" />
        </div>
        <p className="al-decision-note" aria-live="polite">{d.note}</p>

        <ul className="al-cands">
          {d.candidates.map(c => (
            <li key={c.name} className={c.name === d.pick ? "al-cand al-cand-pick" : "al-cand"}>
              <div className="al-cand-top">
                <strong>{c.name}</strong>
                {c.name === d.pick && <span className="al-pill al-pill-ok">Pick</span>}
              </div>
              <p>{c.km} km away · {c.price} · demo buyer</p>
              <p className="al-cand-nums"><span>net {inr(c.inr)}</span><span>{c.co2e.toFixed(2)} kg CO2e avoided</span></p>
              {c.why && <p className="al-cand-why">{c.why}</p>}
            </li>
          ))}
        </ul>

        <div className="al-receipt-mini">
          <p className="al-mini-label">Receipt</p>
          <div><span>Landfill or informal buyer (default)</span><span>₹0 · 0 kg</span></div>
          <div><span>Routed via {picked.name.replace(/ \(.*\)/, "")}</span><span>{inr(picked.inr)} · {picked.co2e.toFixed(2)} kg</span></div>
          <div className="al-receipt-diff"><span>Difference</span><span>+{inr(picked.inr)} · {picked.co2e.toFixed(2)} kg CO2e</span></div>
        </div>
        <DemoTag>Illustrative demo data · synthetic buyers and prices</DemoTag>
      </div>
    </div>
  );
}

// Receipt + verify view for the signature section.
export function SignatureMock() {
  return (
    <div className="al-signature">
      <div className="al-window al-sig-receipt">
        <WindowBar title="Waste passport" />
        <div className="al-sig-banner">
          <p>Waste passport · sample record</p>
          <h3>Steel scrap, 120 kg</h3>
          <code>Record AL-DEMO-0001</code>
        </div>
        <div className="al-sig-body">
          <dl className="al-sig-facts">
            <div><dt>From</dt><dd>Campus workshop, Patiala</dd></div>
            <div><dt>To</dt><dd>Demo Foundry, Mandi Gobindgarh</dd></div>
            <div><dt>Recovered</dt><dd>₹4,042.50</dd></div>
            <div><dt>CO2e avoided</dt><dd>215.04 kg</dd></div>
          </dl>
          <ol className="al-sig-timeline">
            {handoffs.map((h, i) => (
              <li key={h}><span className="al-sig-dot">{i + 1}</span><div><strong>{h}</strong><p>{["Buyer chosen and pickup drafted", "Load left the campus", "Weight written on the record", "Final weight checked against pickup"][i]}</p></div></li>
            ))}
          </ol>
        </div>
      </div>
      <div className="al-window al-sig-verify">
        <WindowBar title="Verify a record" />
        <div className="al-sig-verify-body">
          <p className="al-mini-label">Public page · no sign-in</p>
          <div className="al-fake-input"><span>AL-DEMO-0001</span><span className="al-btn al-btn-primary al-btn-sm">Verify</span></div>
          <div className="al-verify-ok">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m5 12 4 4L19 6" /></svg>
            <div><strong>Intact</strong><p>4 of 4 handoffs check out. Nothing was changed after it was written.</p></div>
          </div>
          <div className="al-verify-bad">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><path d="M12 8v5M12 16.5v.5" /><circle cx="12" cy="12" r="9" /></svg>
            <div><strong>If someone edits a step</strong><p>The page names the exact handoff that no longer matches.</p></div>
          </div>
        </div>
      </div>
      <DemoTag>Illustrative demo data</DemoTag>
    </div>
  );
}
