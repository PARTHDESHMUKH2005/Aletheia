import { useEffect, useState } from "react";
import { api } from "../api.js";
import { ORGS } from "../orgs.js";

export default function Dashboard() {
  const [orgId, setOrgId] = useState(ORGS[0].id);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setError(null);
    setData(null);
    api.getDashboard(orgId).then(setData).catch((err) => setError(err.message));
  }, [orgId]);

  return (
    <div className="max-w-xl">
      <h1 className="text-lg font-semibold mb-1">Dashboard</h1>
      <select
        className="border rounded-md px-3 py-2 text-sm mb-4"
        value={orgId}
        onChange={(e) => setOrgId(e.target.value)}
      >
        {ORGS.map((o) => (
          <option key={o.id} value={o.id}>{o.name}</option>
        ))}
      </select>

      {error && <div className="text-sm text-red-600">{error}</div>}

      {data && (
        <div className="space-y-4">
          <div className="border rounded-lg p-4 bg-white">
            <div className="text-sm font-medium mb-2">kg diverted by tier</div>
            <div className="grid grid-cols-5 gap-2 text-center text-sm">
              {Object.entries(data.kg_by_tier).map(([tier, kg]) => (
                <div key={tier} className="border rounded p-2">
                  <div className="text-gray-500 text-xs">{tier}</div>
                  <div className="font-semibold">{kg}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="border rounded-lg p-4 bg-white">
            <div className="text-sm font-medium">CO2e avoided</div>
            <div className="text-2xl font-semibold">{data.co2e_avoided_kg} kg</div>
            <div className="text-xs text-gray-500 mt-1">
              Factors come from data/emission_factors.json (EPA WARM, labelled "US proxy, not India-specific"
              where verified; otherwise an explicitly unverified estimate). See each item's receipt for the
              exact source.
            </div>
          </div>

          <div className="border rounded-lg p-4 bg-white">
            <div className="text-sm font-medium">Compliance status</div>
            <div>{data.compliance_status}</div>
          </div>

          <div className="text-xs text-gray-500">{data.disclaimer}</div>
        </div>
      )}
    </div>
  );
}
