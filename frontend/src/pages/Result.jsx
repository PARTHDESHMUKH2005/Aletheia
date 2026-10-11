import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api.js";
import { rememberStream } from "../lib/recent.js";
import ContaminationMeter from "../components/ContaminationMeter.jsx";

const STATUS_STYLE = {
  ROUTED: "bg-green-100 text-green-800",
  NEEDS_REVIEW: "bg-yellow-100 text-yellow-800",
  FAILED: "bg-red-100 text-red-800",
  SUBMITTED: "bg-blue-100 text-blue-800",
  CHARACTERIZING: "bg-blue-100 text-blue-800",
};

function StatusBadge({ status }) {
  return (
    <span className={`text-xs font-semibold px-2 py-1 rounded-full ${STATUS_STYLE[status] || "bg-gray-100"}`}>
      {status}
    </span>
  );
}

export default function Result() {
  const { streamId } = useParams();
  const [stream, setStream] = useState(null);
  const [error, setError] = useState(null);
  const [w, setW] = useState(0.5);
  const [ev, setEv] = useState(0);
  const [ewaste, setEwaste] = useState(null);
  const [ewasteError, setEwasteError] = useState(null);
  const [handoffMsg, setHandoffMsg] = useState(null);
  const [route, setRoute] = useState(null);
  const [processors, setProcessors] = useState([]);
  const [routeError, setRouteError] = useState(null);
  const [draft, setDraft] = useState(null);
  const [wipeBusy, setWipeBusy] = useState(false);
  const [wipeError, setWipeError] = useState(null);
  const [draftBusy, setDraftBusy] = useState(false);
  const [draftError, setDraftError] = useState(null);
  const wipePendingRef = useRef(false);
  const draftPendingRef = useRef(false);
  const pollRef = useRef(null);

  useEffect(() => { if (streamId) rememberStream(streamId); }, [streamId]);
  useEffect(() => { api.listProcessors().then(setProcessors).catch(() => {}); }, []);

  async function handleWipe() {
    if (wipePendingRef.current) return;
    wipePendingRef.current = true;
    setWipeBusy(true);
    setWipeError(null);
    try {
      await api.confirmWipe(streamId);
      try {
        setStream(await api.getStream(streamId));
      } catch (err) {
        setWipeError(`Wipe recorded, but ledger refresh failed: ${err.message}`);
      }
    } catch (err) {
      setWipeError(err.message);
    } finally {
      wipePendingRef.current = false;
      setWipeBusy(false);
    }
  }

  async function handleDraft(processorId) {
    if (draftPendingRef.current) return;
    draftPendingRef.current = true;
    setDraftBusy(true);
    setDraftError(null);
    setDraft(null);
    try {
      setDraft(await api.draftPickupMessage(streamId, processorId));
      try {
        setStream(await api.getStream(streamId));
      } catch (err) {
        setDraftError(`Draft created, but ledger refresh failed: ${err.message}`);
      }
    } catch (err) {
      setDraftError(err.message);
    } finally {
      draftPendingRef.current = false;
      setDraftBusy(false);
    }
  }

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const s = await api.getStream(streamId);
        if (cancelled) return;
        setStream(s);
        if (s.status === "SUBMITTED" || s.status === "CHARACTERIZING") {
          pollRef.current = setTimeout(poll, 2000);
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }
    poll();
    return () => {
      cancelled = true;
      clearTimeout(pollRef.current);
    };
  }, [streamId]);

  useEffect(() => {
    if (!stream?.characterization) return;
    let cancelled = false;
    api
      .getRoute(streamId, w, 0, ev)
      .then((r) => !cancelled && (setRoute(r), setRouteError(null)))
      .catch((err) => !cancelled && setRouteError(err.message));
    return () => {
      cancelled = true;
    };
  }, [stream?.characterization, streamId, w, ev]);

  useEffect(() => {
    if (!stream?.characterization) return;
    api.getEwaste(streamId).then(setEwaste).catch(() => {});
  }, [stream?.characterization, streamId]);

  async function addDevices(e) {
    e.preventDefault();
    const f = new FormData(e.target);
    setEwasteError(null);
    try {
      setEwaste(await api.registerEwaste(streamId, [{
        asset_tag: f.get("tag"), kind: f.get("kind"), condition: f.get("condition"),
        storage_drives: parseInt(f.get("drives") || "0", 10),
      }]));
      e.target.reset();
    } catch (err) {
      setEwasteError(err.message);
    }
  }

  async function wipe(e, driveId) {
    e.preventDefault();
    const f = new FormData(e.target);
    setEwasteError(null);
    try {
      setEwaste(await api.wipeDrive(streamId, driveId, {
        method: f.get("method"), certificate_ref: f.get("ref"), operator: f.get("operator"),
      }));
    } catch (err) {
      setEwasteError(err.message);
    }
  }

  async function handoff(status) {
    setHandoffMsg(null);
    try {
      await api.advanceHandoff(streamId, { status });
      setStream(await api.getStream(streamId));
    } catch (err) {
      setHandoffMsg(err.message);
    }
  }

  if (error) return <div className="text-sm text-red-600">{error}</div>;
  if (!stream) return <div className="text-sm text-gray-500">Loading...</div>;

  const item = stream.characterization?.items?.[0];
  const isStorageDevice = item?.is_storage_device;
  const wiped = stream.ledger?.some((e) => e.event === "data_wipe_confirmed");

  return (
    <div className="space-y-5 max-w-xl">
      <div>
        <h1 className="text-lg font-semibold">Decision</h1>
        <div className="mt-1"><StatusBadge status={stream.status} /></div>
        {stream.error && <div className="text-sm text-red-600 mt-2">{stream.error}</div>}
      </div>

      {item && (
        <div className="border rounded-lg p-4 bg-white">
          <div className="font-medium">{item.material}</div>
          <div className="text-sm text-gray-500">{item.composition_note}</div>
          <div className="text-sm text-gray-500">
            {item.quantity_kg ?? "?"} kg ({item.quantity_basis}) &middot; confidence {item.confidence}
          </div>
          {isStorageDevice && (
            <div className="mt-2 text-sm">
              Storage device: {wiped ? (
                <span className="text-green-700">wipe confirmed</span>
              ) : (
                <button
                  className="underline text-blue-700 disabled:opacity-40"
                  disabled={wipeBusy}
                  aria-busy={wipeBusy}
                  onClick={handleWipe}
                >
                  {wipeBusy ? "Recording wipe..." : "record wipe certificate"}
                </button>
              )}
            </div>
          )}
          {wipeError && <div role="alert" className="mt-2 text-sm text-red-600">{wipeError}</div>}
        </div>
      )}

      {item && route?.routing && !route.routing.refused && (() => {
        const pid = route.routing.picked_processor_id || route.routing.reuse_recommended_processor_id;
        const proc = processors.find((p) => p.id === pid);
        const cand = route.routing.candidates?.find((c) => c.processor_id === pid);
        if (!proc) return null;
        const accepts = proc.accepted_materials?.includes(item.material);
        return (
          <div className="border-2 border-green-500 rounded-lg p-4 bg-green-50 text-sm space-y-1" data-testid="destination-card">
            <div className="text-xs uppercase tracking-wide text-green-800 font-semibold">Where this waste goes</div>
            <div className="text-base font-semibold">
              {item.material} <span aria-hidden="true">&rarr;</span> {proc.name}
              <span className="text-[10px] bg-white text-gray-500 px-1.5 py-0.5 rounded-full ml-2 align-middle">seeded demo entity</span>
            </div>
            <div>{proc.location?.address || "Address not recorded"}{proc.pincode ? ` (${proc.pincode})` : ""}</div>
            {cand && <div>Distance from pickup: <strong>{cand.distance_km} km</strong> (straight line)</div>}
            <div>
              Why it is allowed: this processor {accepts ? <strong className="text-green-800">accepts {item.material}</strong> : <strong className="text-red-700">does not list {item.material} as accepted</strong>}
              {" "}(accepts: {proc.accepted_materials?.join(", ")}) &middot; tier: {proc.tier}
            </div>
            {route.routing.rule_name && <div>Governing rule: {route.routing.rule_name}</div>}
            <div className="text-xs text-gray-600">{proc.authorization_label || "demo only, authorization not checked"}</div>
          </div>
        );
      })()}

      {route?.assessment && (
        <div className="border rounded-lg p-4 bg-white text-sm space-y-1">
          <div className="font-medium">Quality check</div>
          <div className="text-gray-600">
            Confidence {route.assessment.confidence} ({route.assessment.confidence_band}) &middot; purity: {route.assessment.purity}
          </div>
          <div className="text-xs text-gray-500">{route.assessment.confidence_basis}. {route.assessment.purity_note}</div>
          {item && <div className="pt-1"><div className="text-xs text-gray-600 mb-1">Contamination</div><ContaminationMeter item={item} /></div>}
          {route.assessment.price_is_provisional && (
            <div className="text-xs text-amber-700">Price is provisional: {route.assessment.inspection_reasons.join("; ")}.</div>
          )}
          {route.assessment.review_reasons.map((r) => <div key={r} className="text-xs text-yellow-800">Review: {r}</div>)}
          <div className="font-medium pt-1">Next: {route.assessment.recommended_action}</div>
        </div>
      )}

      {item && (
        <div className="space-y-3">
          <div>
            <label className="block text-xs text-gray-600 mb-1">
              Routing slider: {w.toFixed(2)} (0 = max money, 1 = max carbon)
            </label>
            <input
              type="range" min="0" max="1" step="0.05" value={w}
              onChange={(e) => setW(parseFloat(e.target.value))}
              className="w-full"
            />
          </div>

          <div>
            <label className="block text-xs text-gray-600 mb-1">
              Weight on authorization evidence: {ev.toFixed(2)} (0 = ignore, 1 = only evidence on file)
            </label>
            <input type="range" min="0" max="1" step="0.05" value={ev} onChange={(e) => setEv(parseFloat(e.target.value))} className="w-full" />
          </div>

          {routeError && <div className="text-sm text-red-600">{routeError}</div>}

          {route && (
            <>
              <p className="text-sm text-gray-600">{route.routing.explanation}</p>
              {route.routing.review_required && (
                <div className="text-xs font-semibold inline-block px-2 py-1 rounded-full bg-yellow-100 text-yellow-800">
                  needs human review
                </div>
              )}
              <div className="space-y-2">
                {route.routing.candidates.map((c) => (
                  <div
                    key={c.processor_id}
                    className={`border rounded-md p-3 text-sm ${
                      c.processor_id === route.routing.picked_processor_id ? "border-green-500 bg-green-50" : "bg-white"
                    }`}
                  >
                    <div className="font-medium">
                      {c.name} <span className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded-full ml-1">seeded</span>
                      {c.price_basis === "illustrative_assumption" && (
                        <span className="text-[10px] text-amber-700 ml-1">(illustrative price)</span>
                      )}
                    </div>
                    <div className="text-gray-500">
                      {c.distance_km} km &middot; recovery_rate {c.recovery_rate} (assumption)
                    </div>
                    <div className="text-gray-500">
                      net &#8377;{c.net_rupees?.toFixed(2)} &middot; net {c.net_co2e_kg?.toFixed(2)} kg CO2e avoided
                    </div>
                    <div className="text-gray-500">
                      gross &#8377;{c.gross_rupees?.toFixed(2)} &minus; transport &#8377;{c.transport_cost_rupees?.toFixed(2)} &middot; evidence level {c.evidence_level}/2
                    </div>
                    {c.why_not_picked && <div className="text-xs text-gray-600 mt-1">{c.why_not_picked}</div>}
                    {c.processor_id === route.routing.picked_processor_id && (
                      <button
                        className="mt-2 text-xs underline text-blue-700 disabled:opacity-40"
                        disabled={draftBusy}
                        aria-busy={draftBusy}
                        onClick={() => handleDraft(c.processor_id)}
                      >
                        {draftBusy ? "Creating draft..." : "Request pickup (draft only, never sent)"}
                      </button>
                    )}
                  </div>
                ))}
              </div>

              {draftError && <div role="alert" className="text-sm text-red-600">{draftError}</div>}

              {draft && (
                <div className="border rounded-md p-3 bg-gray-50 text-sm">
                  <pre className="whitespace-pre-wrap text-xs">{draft.draft_message}</pre>
                  <div className="text-xs font-semibold mt-1">{draft.label}</div>
                </div>
              )}

              <div className="border rounded-md p-3 bg-white text-sm">
                <div className="font-medium mb-1">Counterfactual receipt</div>
                <div className="text-gray-500">
                  {route.receipt.default_case.label}: &#8377;{route.receipt.default_case.value_inr} / {route.receipt.default_case.co2e_kg} kg CO2e
                </div>
                <div className="text-gray-500">
                  {route.receipt.chosen_case.label}: &#8377;{route.receipt.chosen_case.value_inr?.toFixed?.(2)} / {route.receipt.chosen_case.co2e_kg?.toFixed?.(2)} kg CO2e
                </div>
                <div className="font-medium mt-1">
                  Diff: &#8377;{route.receipt.diff_rupees?.toFixed?.(2) ?? "n/a"} &middot; {route.receipt.diff_co2e_kg?.toFixed?.(2) ?? "n/a"} kg CO2e
                </div>
                {route.receipt.price_range ? (
                  <div className="text-gray-500 mt-1">
                    Price range: &#8377;{route.receipt.price_range.low_inr_per_kg}-{route.receipt.price_range.high_inr_per_kg}/kg,
                    source: {route.receipt.price_range.source} ({route.receipt.price_range.as_of})
                  </div>
                ) : (
                  <div className="text-gray-500 mt-1">No sourced price range for this material.</div>
                )}
                <div className="text-gray-500">
                  CO2e factor: {route.receipt.emission_factor_available
                    ? `${route.receipt.emission_factor_source} -- ${route.receipt.emission_factor_label}`
                    : "not available for this material"}
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {stream.status === "ROUTED" && (
        <div className="border rounded-md p-3 bg-white text-sm space-y-1">
          <div className="font-medium">Handoff</div>
          <div className="flex gap-3 text-xs">
            {["matched", "collected", "weighed", "verified"].map((st) => (
              <button key={st} className="underline text-blue-700" onClick={() => handoff(st)}>mark {st}</button>
            ))}
          </div>
          {handoffMsg && <div className="text-xs text-red-600">{handoffMsg}</div>}
        </div>
      )}

      {stream.characterization && (
        <div className="border rounded-md p-3 bg-white text-sm space-y-2">
          <div className="font-medium">E-waste batch (optional)</div>
          {ewaste?.device_count > 0 && (
            <>
              <div className="text-xs text-gray-500">{ewaste.policy_note}</div>
              {ewaste.devices.map((d) => (
                <div key={d.asset_tag} className="text-xs border rounded px-2 py-1">
                  <b>{d.asset_tag}</b> {d.kind}, {d.condition}: {d.pathway_note}
                </div>
              ))}
              {ewaste.drives.map((dr) => (
                <div key={dr.drive_id} className="text-xs border rounded px-2 py-1">
                  Drive {dr.drive_id}:{" "}
                  {dr.wipe ? (
                    <span className="text-green-700">{dr.wipe.method}, ref {dr.wipe.certificate_ref}, by {dr.wipe.operator}. {dr.wipe.note}</span>
                  ) : (
                    <form className="inline-flex gap-1 flex-wrap" onSubmit={(e) => wipe(e, dr.drive_id)}>
                      <select name="method" className="border rounded px-1">
                        <option value="overwrite">overwrite</option>
                        <option value="crypto_erase">crypto erase</option>
                        <option value="degauss">degauss</option>
                        <option value="physical_destruction">physical destruction</option>
                      </select>
                      <input name="ref" placeholder="certificate ref" className="border rounded px-1" required />
                      <input name="operator" placeholder="operator" className="border rounded px-1" required />
                      <button className="underline text-blue-700">record</button>
                    </form>
                  )}
                </div>
              ))}
              {ewaste.transfer_blocked && <div className="text-xs text-red-600">Transfer blocked: {ewaste.blocking_reasons.length} drive(s) without a wipe or destruction record.</div>}
            </>
          )}
          <form className="flex gap-1 flex-wrap text-xs" onSubmit={addDevices}>
            <input name="tag" placeholder="asset tag" className="border rounded px-1" required />
            <select name="kind" className="border rounded px-1">
              {["laptop", "desktop", "server", "monitor", "phone", "network", "printer", "other"].map((k) => <option key={k}>{k}</option>)}
            </select>
            <select name="condition" className="border rounded px-1">
              {["working", "repairable", "broken", "unknown"].map((k) => <option key={k}>{k}</option>)}
            </select>
            <input name="drives" type="number" min="0" defaultValue="0" className="border rounded px-1 w-16" title="installed storage drives" />
            <button className="underline text-blue-700">add device</button>
          </form>
          {ewasteError && <div className="text-xs text-red-600">{ewasteError}</div>}
        </div>
      )}

      <div>
        <h2 className="text-sm font-semibold mb-2">Ledger</h2>
        <div className="space-y-1">
          {stream.ledger?.map((e) => (
            <div key={e.link_no} className="text-xs text-gray-600 border rounded px-2 py-1 bg-white">
              #{e.link_no} {e.event} &middot; {e.ts}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
