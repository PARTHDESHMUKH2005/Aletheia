import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { ORGS } from "../orgs.js";

const inr = (v) => `₹${Number(v).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;

function Card({ title, children }) {
  return (
    <div className="border rounded-lg p-4 bg-white">
      <div className="text-sm font-medium mb-2">{title}</div>
      {children}
    </div>
  );
}

function Stat({ label, value, sub }) {
  return (
    <div className="border rounded p-2 text-center">
      <div className="text-gray-500 text-xs">{label}</div>
      <div className="font-semibold">{value}</div>
      {sub && <div className="text-[10px] text-gray-400">{sub}</div>}
    </div>
  );
}

export default function Dashboard() {
  const [orgId, setOrgId] = useState(ORGS[0].id);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setError(null);
    setData(null);
    api.getDashboard(orgId).then(setData).catch((err) => setError(err.message));
  }, [orgId]);

  const p = data?.revenue_inr.projected;
  const r = data?.revenue_inr.realised;

  return (
    <div className="max-w-2xl">
      <h1 className="text-lg font-semibold mb-1">Waste value and impact</h1>
      <select className="border rounded-md px-3 py-2 text-sm mb-4" value={orgId} onChange={(e) => setOrgId(e.target.value)}>
        {ORGS.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
      </select>

      {error && <div className="text-sm text-red-600">{error}</div>}

      {data && (
        <div className="space-y-4">
          <Card title="Kilograms">
            <div className="grid grid-cols-3 gap-2 text-sm">
              <Stat label="submitted" value={data.kg.submitted} />
              <Stat label="collected" value={data.kg.collected} />
              <Stat label="verified" value={data.kg.verified} sub="handoff marked verified" />
            </div>
            <div className="text-xs text-gray-500 mt-3 mb-1">By route (routed items only)</div>
            <div className="grid grid-cols-5 gap-2 text-sm">
              {Object.entries(data.kg_by_tier).map(([tier, kg]) => <Stat key={tier} label={tier} value={kg} />)}
            </div>
          </Card>

          <Card title="Revenue recovered (costs shown separately)">
            <table className="w-full text-sm">
              <thead><tr className="text-left text-xs text-gray-500"><th></th><th>Projected</th><th>Realised (verified)</th></tr></thead>
              <tbody>
                <tr><td>Gross</td><td>{inr(p.gross_inr)}</td><td>{inr(r.gross_inr)}</td></tr>
                <tr><td>Transport cost</td><td>- {inr(p.transport_cost_inr)}</td><td>- {inr(r.transport_cost_inr)}</td></tr>
                <tr className="font-semibold border-t"><td>Net</td><td>{inr(p.net_inr)}</td><td>{inr(r.net_inr)}</td></tr>
              </tbody>
            </table>
            <div className="text-xs text-gray-500 mt-2">{data.methodology.revenue}</div>
            <div className="text-xs text-gray-500 mt-1">{data.methodology.projected_vs_realised}</div>
          </Card>

          <Card title="CO2e avoided">
            <div className="text-2xl font-semibold">{data.co2e.projected_kg} kg <span className="text-sm font-normal text-gray-500">projected</span></div>
            <div className="text-sm text-gray-600">{data.co2e.realised_kg} kg from verified handoffs</div>
            <div className="text-xs text-gray-500 mt-2">{data.co2e.methodology}</div>
            <ul className="text-xs text-gray-500 mt-2 space-y-0.5">
              {Object.entries(data.co2e.factors_used).map(([m, f]) => (
                <li key={m}>{m}: {f.kg_co2e_per_kg} kg CO2e/kg &middot; {f.source} &middot; {f.label}</li>
              ))}
            </ul>
            {data.co2e.materials_without_factor.length > 0 && (
              <div className="text-xs text-amber-700 mt-1">No factor, so not counted: {data.co2e.materials_without_factor.join(", ")}</div>
            )}
          </Card>

          <Card title="Waiting on someone">
            <div className="grid grid-cols-3 gap-2 text-sm">
              <Stat label="review" value={data.pending.awaiting_review} />
              <Stat label="pickup" value={data.pending.awaiting_pickup} />
              <Stat label="verification" value={data.pending.awaiting_verification} />
            </div>
          </Card>

          <Card title={`Outstanding actions (${data.outstanding_actions.length})`}>
            {data.outstanding_actions.length === 0 && <div className="text-sm text-gray-500">None.</div>}
            <ul className="text-sm space-y-1">
              {data.outstanding_actions.map((a, i) => (
                <li key={i}>
                  <Link className="underline text-blue-700" to={`/streams/${a.stream_id}`}>{a.stream_id.slice(0, 8)}</Link>{" "}
                  <span className="font-medium">{a.action}</span>: <span className="text-gray-600">{a.detail}</span>
                </li>
              ))}
            </ul>
            {data.missing_documents.length > 0 && (
              <div className="mt-3 text-sm">
                <div className="font-medium">Missing documents</div>
                <ul className="text-gray-600">
                  {data.missing_documents.map((m, i) => <li key={i}>{m.document} for {m.material} ({m.stream_id.slice(0, 8)})</li>)}
                </ul>
              </div>
            )}
            {data.paperwork_not_tracked_by_loopback.length > 0 && (
              <div className="mt-2 text-xs text-gray-500">
                LoopBack cannot check these yet: {data.paperwork_not_tracked_by_loopback.join(", ")}.
              </div>
            )}
          </Card>

          <div className="text-xs text-gray-500">{data.disclaimer}</div>
        </div>
      )}
    </div>
  );
}
