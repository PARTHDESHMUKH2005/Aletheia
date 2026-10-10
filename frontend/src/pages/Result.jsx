import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api.js";

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
  const [route, setRoute] = useState(null);
  const [routeError, setRouteError] = useState(null);
  const [draft, setDraft] = useState(null);
  const pollRef = useRef(null);

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
      .getRoute(streamId, w)
      .then((r) => !cancelled && (setRoute(r), setRouteError(null)))
      .catch((err) => !cancelled && setRouteError(err.message));
    return () => {
      cancelled = true;
    };
  }, [stream?.characterization, streamId, w]);

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
                  className="underline text-blue-700"
                  onClick={() => api.confirmWipe(streamId).then(() => api.getStream(streamId).then(setStream))}
                >
                  record wipe certificate
                </button>
              )}
            </div>
          )}
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
                    {c.processor_id === route.routing.picked_processor_id && (
                      <button
                        className="mt-2 text-xs underline text-blue-700"
                        onClick={() =>
                          api.draftPickupMessage(streamId, c.processor_id).then(setDraft)
                        }
                      >
                        Request pickup (draft only, never sent)
                      </button>
                    )}
                  </div>
                ))}
              </div>

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
