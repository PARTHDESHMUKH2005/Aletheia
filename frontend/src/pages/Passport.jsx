import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, API_URL } from "../api.js";
import Icon from "../components/Icon.jsx";
import PassportMap from "../components/PassportMap.jsx";
import { DetailList, PageHeader, SectionCard, StatusBadge, Timeline } from "../components/PassportUI.jsx";
import { recentStreams } from "../lib/recent.js";
import PassportSample from "./PassportSample.jsx";

const POLL_MS = 2000;
const PENDING = ["SUBMITTED", "CHARACTERIZING"];
const STATUS_TONE = { ROUTED: "success", NEEDS_REVIEW: "pending", FAILED: "danger" };
const STATUS_LABEL = { SUBMITTED: "Submitted", CHARACTERIZING: "Characterizing…", ROUTED: "Routed", NEEDS_REVIEW: "Needs review", FAILED: "Failed", REJECTED: "Rejected" };

const label = (m) => (m ? m.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase()) : "Unknown");
const fmtTime = (iso) => (iso ? new Date(iso).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }) : null);
const short = (h) => (h ? `${h.slice(0, 10)}…${h.slice(-6)}` : "Not available");

function buildTimeline(stream) {
  const done = (d) => ({ state: "example", ...d });
  const pending = (d) => ({ state: "pending", ...d });
  const events = [done({ label: "Waste uploaded", description: `${stream.photo_keys?.length || 0} photo(s) submitted for ${stream.org_name || stream.org_id}.`, timestamp: fmtTime(stream.created_at), dateTime: stream.created_at })];
  const items = stream.characterization?.items;
  if (stream.status === "FAILED") {
    events.push({ label: "Processing failed", state: "pending", description: stream.error || "The pipeline failed." });
    return events;
  }
  events.push(items
    ? done({ label: "Waste characterization", description: `${items.length} item(s) identified${stream.timings?.characterize_ms ? ` in ${(stream.timings.characterize_ms / 1000).toFixed(1)}s` : ""}.` })
    : pending({ label: "Waste characterization", description: "The AI is looking at the photo(s)…" }));
  if (stream.agent?.summary) events.push(done({ label: "Orchestrator agent", description: `${stream.agent.tool_calls} tool calls in ${((stream.timings?.agent_ms || 0) / 1000).toFixed(1)}s.` }));
  events.push(stream.routing
    ? done({ label: "Processor matching / routing", description: stream.status === "NEEDS_REVIEW" ? "Matched, but flagged for human review." : "Best-ranked processor selected." })
    : pending({ label: "Processor matching / routing", description: "Waiting for characterization." }));
  (stream.ledger || []).forEach((e) => events.push(done({
    label: label(e.event.replace("handoff_", "Handoff ")), description: `Ledger link #${e.link_no} · ${short(e.entry_hash)}`, timestamp: fmtTime(e.ts), dateTime: e.ts,
  })));
  if (!(stream.ledger || []).length) events.push(pending({ label: "Collection & processing", description: "No handoff has been recorded yet." }));
  return events;
}

export default function Passport() {
  const { passportId } = useParams();
  const streamId = passportId || recentStreams()[0];
  const [stream, setStream] = useState(null);
  const [error, setError] = useState(null);
  const [processors, setProcessors] = useState([]);
  const [verify, setVerify] = useState(null);
  const [copyMessage, setCopyMessage] = useState("");

  useEffect(() => { api.listProcessors().then(setProcessors).catch(() => {}); }, []);

  // Live updates: poll while the pipeline is still working, so the passport fills in on its own.
  useEffect(() => {
    if (!streamId) return undefined;
    let cancelled = false;
    let timer;
    setStream(null); setError(null); setVerify(null);
    const load = async () => {
      try {
        const s = await api.getStream(streamId);
        if (cancelled) return;
        setStream(s);
        if (PENDING.includes(s.status)) timer = setTimeout(load, POLL_MS);
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    };
    load();
    return () => { cancelled = true; clearTimeout(timer); };
  }, [streamId]);

  const items = stream?.characterization?.items || [];
  const routing = stream?.routing?.[0];
  const pickedId = routing && !routing.refused ? (routing.picked_processor_id || routing.reuse_recommended_processor_id) : null;
  const picked = processors.find((p) => p.id === pickedId);
  const candidate = routing?.candidates?.find((c) => c.processor_id === pickedId);
  const others = useMemo(() => {
    const ids = new Set((routing?.candidates || []).slice(0, 4).map((c) => c.processor_id));
    return processors.filter((p) => ids.has(p.id) && p.id !== pickedId);
  }, [processors, routing, pickedId]);
  const timeline = useMemo(() => (stream ? buildTimeline(stream) : []), [stream]);

  if (!streamId) {
    return <div>
      <div className="lb-demo-notice"><Icon name="passport" size={17} />
        <p>No waste has been uploaded from this browser yet. <Link to="/">Upload a photo</Link> and its passport will appear here, filled in live. Below is a sample record.</p>
      </div>
      <PassportSample />
    </div>;
  }
  if (error) {
    return <div className="lb-passport-page"><PageHeader title="Waste Passport" description="A waste stream's identity and traceability record." />
      <SectionCard title="Passport unavailable"><p className="lb-note">{error}</p>
        <Link className="lb-button lb-button-primary" to="/">Upload waste</Link></SectionCard></div>;
  }
  if (!stream) return <div className="lb-passport-page"><PageHeader title="Waste Passport" description="Loading…" /></div>;

  const working = PENDING.includes(stream.status);
  const totalKg = items.reduce((sum, i) => sum + (i.quantity_kg || 0), 0);
  const basis = items.some((i) => i.quantity_basis === "estimated") ? "AI-estimated" : "Declared";
  const title = items.length ? items.map((i) => label(i.material)).join(" + ") : "Characterizing…";
  const anyHazard = items.some((i) => i.hazardous);
  const lastLink = (stream.ledger || []).slice(-1)[0];

  async function copyId() {
    try { await navigator.clipboard.writeText(streamId); setCopyMessage("Passport ID copied."); }
    catch { setCopyMessage("Could not copy. Select the ID and copy it."); }
  }
  async function runVerify() {
    try { setVerify(await api.verifyChain(streamId)); } catch (err) { setVerify({ error: err.message }); }
  }

  return (
    <div className="lb-passport-page">
      <PageHeader title="Waste Passport" description="A structured identity and traceability record for this waste stream."
        eyebrow={`Live record · ${streamId.slice(0, 12)}`}
        action={<div className="lb-inline-actions">
          <button className="lb-button lb-button-secondary" onClick={() => window.print()}><Icon name="print" size={15} />Print</button>
          <StatusBadge tone={STATUS_TONE[stream.status] || "pending"}>{STATUS_LABEL[stream.status] || stream.status}</StatusBadge>
        </div>} />

      {working && <div className="lb-demo-notice" role="status"><Icon name="clock" size={17} /><p>Processing… this passport updates automatically when results arrive.</p></div>}
      {stream.status === "FAILED" && <div className="lb-demo-notice" role="alert"><Icon name="passport" size={17} /><p>Processing failed: {stream.error}</p></div>}

      <div className="lb-metric-grid" aria-label="Waste overview">
        {[
          ["Waste category", items.length ? title : "Pending", items.length ? `${items.length} item(s) · confidence ${Math.round((stream.characterization.overall_confidence || 0) * 100)}%` : "Awaiting characterization", "recycle"],
          ["Quantity", items.length ? `${totalKg.toFixed(totalKg < 10 ? 2 : 0)} kg` : (stream.quantity_kg ? `${stream.quantity_kg} kg` : "Pending"), items.length ? `${basis} quantity` : "Awaiting characterization", "weight"],
          ["Waste origin", stream.org_name || stream.org_id, stream.pickup_location ? `${stream.pickup_location.address} · ${stream.pickup_location.pincode}` : "Location unavailable", "pin"],
          ["Date created", fmtTime(stream.created_at)?.split(",").slice(0, 2).join(",") || "Not recorded", fmtTime(stream.created_at)?.split(",").slice(-1)[0]?.trim() || "Created before timestamps were stored", "calendar"],
        ].map(([lbl, value, note, icon]) => <article className="lb-metric-card" key={lbl}>
          <div className="lb-metric-top"><span>{lbl}</span><Icon name={icon} /></div>
          <strong>{value}</strong><p>{note}</p>
        </article>)}
      </div>

      <article className="lb-passport-card" aria-label="Passport identity">
        <header className="lb-passport-banner">
          <div><span className="lb-passport-kicker"><Icon name="passport" size={15} />Digital Waste Passport{anyHazard ? " · Hazardous" : ""}</span>
            <h2>{title}</h2><p>{streamId}</p></div>
          <Icon name="recycle" size={42} strokeWidth={1.2} />
        </header>
        <div className="lb-passport-body">
          <div className="lb-passport-photo">
            {stream.photo_keys?.[0]
              ? <img src={`${API_URL}/local-uploads/${stream.photo_keys[0]}`} alt="Submitted waste" style={{ width: "100%", height: "100%", objectFit: "cover", minHeight: 265 }} />
              : <div><Icon name="passport" size={32} /><strong>No photo</strong></div>}
          </div>
          <div className="lb-passport-facts">
            <DetailList rows={[
              ["Record status", <StatusBadge key="s" tone={STATUS_TONE[stream.status] || "pending"}>{STATUS_LABEL[stream.status] || stream.status}</StatusBadge>],
              ["Characterization", <StatusBadge key="c" tone={items.length ? "success" : "pending"}>{items.length ? "Complete" : "Pending"}</StatusBadge>],
              ["Ledger", <StatusBadge key="l" tone={stream.ledger?.length ? "success" : "pending"}>{stream.ledger?.length ? `${stream.ledger.length} link(s)` : "No entries"}</StatusBadge>],
              ["Created", fmtTime(stream.created_at) || "Not recorded"],
              ["Submitter note", stream.note || "None"],
            ]} />
            <button className="lb-button lb-button-secondary" onClick={copyId}><Icon name="copy" size={15} />Copy passport ID</button>
            <p className="lb-copy-message" role="status">{copyMessage}</p>
          </div>
        </div>
      </article>

      <div className="lb-passport-grid">
        <SectionCard title="Waste characterization" action={<StatusBadge tone={items.length ? "success" : "pending"}>{items.length ? "AI result" : "Pending"}</StatusBadge>}>
          {!items.length && <div className="lb-empty-state"><span className="lb-empty-icon"><Icon name="recycle" size={22} /></span>
            <h3>{stream.status === "FAILED" ? "Characterization failed" : "Characterizing…"}</h3><p>Results appear here automatically.</p></div>}
          {items.map((it, i) => <div key={i} style={{ marginBottom: 14 }}>
            <DetailList rows={[
              [items.length > 1 ? `Item ${i + 1}` : "Material", label(it.material)],
              ["Quantity", `${it.quantity_kg ?? "?"} kg (${it.quantity_basis})`],
              ["Purity", label(it.purity)],
              ["Hazardous", it.hazardous ? "Yes — routed to authorized handlers only" : "No"],
              ["Confidence", `${Math.round(it.confidence * 100)}%`],
              ["Composition", it.composition_note],
              ["Contaminants", it.contaminants?.length ? it.contaminants.join(", ") : "None visible"],
            ]} />
            <p className="lb-note">{it.reasoning}</p>
          </div>)}
        </SectionCard>

        <SectionCard title="Verification & ledger" className="lb-verification-card" action={<Icon name="lock" size={18} />}>
          <DetailList rows={[
            ["Chain identifier", streamId],
            ["Ledger links", String(stream.ledger?.length || 0)],
            ["Latest hash", short(lastLink?.entry_hash)],
            ["Integrity", verify == null ? "Not checked" : verify.error ? verify.error : verify.ok ? `Intact — ${verify.links} link(s)` : `BROKEN at link ${verify.first_broken}`],
          ]} />
          <button className="lb-button lb-button-primary" onClick={runVerify} disabled={!stream.ledger?.length}><Icon name="verify" size={15} />Verify record</button>
          {!stream.ledger?.length && <p className="lb-note lb-action-note">Available once a handoff is recorded.</p>}
          {stream.ledger?.length > 0 && <p className="lb-action-note"><Link to={`/verify/${streamId}`}>Open full verification</Link></p>}
        </SectionCard>
      </div>

      <div className="lb-passport-grid">
        <SectionCard title="Journey & processing timeline" action={<StatusBadge tone={working ? "pending" : "success"}>{working ? "Live" : "Recorded"}</StatusBadge>}>
          <Timeline events={timeline} />
        </SectionCard>

        <SectionCard title="Processor & destination" action={<StatusBadge tone={picked ? "success" : "pending"}>{picked ? "Matched" : routing?.refused ? "Refused" : "Unassigned"}</StatusBadge>}>
          {picked ? <DetailList rows={[
            ["Processor", `${picked.name} (seeded demo entity)`],
            ["Location", picked.location?.address],
            ["Tier", label(picked.tier)],
            ["Distance", candidate ? `${candidate.distance_km} km` : "—"],
            ["Accepts", picked.accepted_materials.map(label).join(", ")],
            ["Governing rule", routing.rule_name],
            ["Why this one", routing.explanation],
            ["Authorization", picked.authorization_label],
          ]} /> : <>
            <div className="lb-destination-icon"><Icon name="map" size={24} /></div>
            <h3 className="lb-destination-title">{routing?.refused ? "Outside LoopBack's scope" : "Awaiting a destination"}</h3>
            <p className="lb-note">{routing?.refused ? `Category: ${routing.out_of_scope_category}. Needs human review.` : "No processor has been matched yet."}</p>
          </>}
          {stream.status === "NEEDS_REVIEW" && <p className="lb-note">Flagged for human review — see the <Link to="/review">review queue</Link>.</p>}
          <PassportMap pickup={stream.pickup_location} picked={picked} others={others} />
        </SectionCard>
      </div>

      {stream.agent?.summary && <SectionCard title="Orchestrator summary" action={<StatusBadge tone="demo">AI agent</StatusBadge>}>
        <p className="lb-note">{stream.agent.summary}</p>
        <p className="lb-note">{stream.agent.tool_calls} tool calls · {stream.agent.usage?.totalTokens ?? "?"} tokens</p>
      </SectionCard>}
      {stream.agent?.error && <p className="lb-note">Agent unavailable ({stream.agent.error.slice(0, 80)}); routing completed by the rules engine.</p>}
    </div>
  );
}
