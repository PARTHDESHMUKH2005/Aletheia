import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useSession } from "../components/Session.jsx";

const MATERIALS = ["aluminium_scrap", "steel_scrap", "copper_scrap", "mixed_metal", "paper", "cardboard",
  "e_waste_computer", "e_waste_storage_drive", "e_waste_other", "battery_lead_acid", "battery_lithium", "used_oil", "other"];
const HAZARDOUS_MATERIALS = ["battery_lead_acid", "battery_lithium", "used_oil"];

export default function Review() {
  const [queue, setQueue] = useState(null);
  const [error, setError] = useState(null);
  const { principal } = useSession();
  const [reviewer, setReviewer] = useState(principal?.subject || "");
  const [note, setNote] = useState("");
  const [selections, setSelections] = useState({});
  const [busy, setBusy] = useState(false);

  const load = () => api.getReviewQueue().then(setQueue).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  async function decide(streamId, decision, extra = {}) {
    setError(null);
    setBusy(true);
    try {
      await api.submitReview(streamId, { decision, reviewer, note, ...extra });
      setSelections((current) => Object.fromEntries(Object.entries(current).filter(([key]) => !key.startsWith(`${streamId}:`))));
      await load();
    } catch (e) {
      setError(e.message);
    } finally { setBusy(false); }
  }

  return (
    <div className="max-w-2xl space-y-4">
      <div>
        <h1 className="text-lg font-semibold">Review queue</h1>
        <p className="text-sm text-gray-500">
          Items the system was not sure about, or that need a person by rule. Nothing moves until someone decides.
        </p>
      </div>
      <div className="flex gap-2">
        <input className="border rounded-md px-3 py-2 text-sm flex-1" placeholder="Your name (required)" value={reviewer} onChange={(e) => setReviewer(e.target.value)} />
        <input className="border rounded-md px-3 py-2 text-sm flex-1" placeholder="Note (optional)" value={note} onChange={(e) => setNote(e.target.value)} />
      </div>
      {error && <div className="text-sm text-red-600">{error}</div>}
      {queue && queue.length === 0 && <div className="text-sm text-gray-500">Nothing waiting.</div>}
      {queue?.map((q) => (
        <div key={q.stream_id} className="border rounded-lg p-4 bg-white space-y-2">
          <div className="flex justify-between text-sm">
            <Link className="underline text-blue-700" to={`/streams/${q.stream_id}`}>{q.stream_id.slice(0, 8)}</Link>
            <span className="text-gray-500">{q.org_id}</span>
          </div>
          {q.assessments.map((a, i) => {
            const key = `${q.stream_id}:${i}`;
            const classification = selections[key] || q.classifications?.[i] || {
              material: a.material, hazardous: HAZARDOUS_MATERIALS.includes(a.material), is_storage_device: a.material === "e_waste_storage_drive",
            };
            const update = (next) => setSelections((current) => ({ ...current, [key]: { ...classification, ...next } }));
            return (
            <div key={i} className="text-sm">
              <div className="font-medium">{a.material} <span className="text-xs text-gray-500">confidence {a.confidence} ({a.confidence_band})</span></div>
              <ul className="list-disc ml-5 text-gray-600">
                {a.review_reasons.map((r) => <li key={r}>{r}</li>)}
              </ul>
              {a.contaminants.length > 0 && <div className="text-xs text-amber-700">Contamination: {a.contaminants.join("; ")}</div>}
              <div className="flex gap-2 mt-2">
                <select aria-label={`Material for item ${i + 1}`} className="border rounded p-1"
                  value={classification.material}
                  onChange={(e) => update({ material: e.target.value, hazardous: HAZARDOUS_MATERIALS.includes(e.target.value),
                    is_storage_device: e.target.value === "e_waste_storage_drive" })}>
                  {MATERIALS.map((material) => <option key={material}>{material}</option>)}
                </select>
                <button disabled={!reviewer.trim() || busy} className="underline text-blue-700 disabled:text-gray-400"
                  onClick={() => decide(q.stream_id, "reclassify", { item_index: i, ...classification })}>
                  Reclassify item
                </button>
              </div>
              <div className="flex flex-wrap gap-3 mt-2 text-xs">
                <label><input type="checkbox" checked={classification.hazardous}
                  disabled={HAZARDOUS_MATERIALS.includes(classification.material)} onChange={(e) => update({ hazardous: e.target.checked })} /> Hazardous (including contamination)</label>
                <label><input type="checkbox" checked={classification.is_storage_device}
                  disabled={classification.material === "e_waste_storage_drive"} onChange={(e) => update({ is_storage_device: e.target.checked })} /> Contains data storage</label>
              </div>
            </div>
          ); })}
          <div className="flex gap-3 text-sm pt-1">
            <button disabled={!reviewer.trim() || busy} className="underline text-blue-700 disabled:text-gray-400" onClick={() => decide(q.stream_id, "confirm_routing")}>Confirm routing</button>
            <button disabled={!reviewer.trim() || busy} className="underline text-red-700 disabled:text-gray-400" onClick={() => decide(q.stream_id, "reject")}>Reject</button>
          </div>
        </div>
      ))}
    </div>
  );
}
