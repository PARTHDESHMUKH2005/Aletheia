import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import Icon from "../components/Icon.jsx";
import { DetailList, PageHeader, SectionCard, StatusBadge, Timeline } from "../components/PassportUI.jsx";
import { passportSample } from "../data/passportSample.js";

export default function PassportSample() {
  const { passportId } = useParams();
  const [copyMessage, setCopyMessage] = useState("");
  const sample = passportSample;

  async function copyId() {
    try {
      await navigator.clipboard.writeText(sample.id);
      setCopyMessage("Sample passport ID copied.");
    } catch {
      setCopyMessage("Could not copy. Select and copy the sample ID above.");
    }
  }

  if (passportId && passportId !== sample.id) {
    return <div className="lb-passport-page">
      <PageHeader title="Waste Passport" description="A waste stream's identity and traceability record." />
      <SectionCard title="Passport unavailable">
        <p className="lb-note">Part 1 contains one sample record only. This identifier has not been loaded from the backend.</p>
        <Link className="lb-button lb-button-primary" to="/passports">View sample passport</Link>
      </SectionCard>
    </div>;
  }

  return (
    <div className="lb-passport-page">
      <PageHeader title="Waste Passport"
        description="A structured identity and traceability record for a waste stream."
        eyebrow={`Sample record · ${sample.id}`}
        action={<div className="lb-inline-actions">
          <button className="lb-button lb-button-secondary" onClick={() => window.print()}><Icon name="print" size={15} />Print sample</button>
          <StatusBadge tone="demo">Sample / demo data</StatusBadge>
        </div>} />

      <div className="lb-demo-notice"><Icon name="passport" size={17} />
        <p>This is an illustrative passport. No live waste record, AI result, processor assignment, or verification is represented.</p>
      </div>

      <div className="lb-metric-grid" aria-label="Sample waste overview">
        {[
          ["Waste category", sample.category, sample.categoryBasis, "recycle"],
          ["Quantity", `${sample.quantity} ${sample.unit}`, "Sample declared quantity", "weight"],
          ["Waste origin", sample.origin, sample.originDetail, "pin"],
          ["Date created", sample.createdDateLabel, `Sample date · ${sample.createdTimeLabel}`, "calendar"],
        ].map(([label, value, note, icon]) => <article className="lb-metric-card" key={label}>
          <div className="lb-metric-top"><span>{label}</span><Icon name={icon} /></div>
          <strong>{value}</strong><p>{note}</p>
        </article>)}
      </div>

      <article className="lb-passport-card" aria-label="Sample passport identity">
        <header className="lb-passport-banner">
          <div><span className="lb-passport-kicker"><Icon name="passport" size={15} />Digital Waste Passport · Sample</span>
            <h2>{sample.category}</h2><p>{sample.id} · {sample.categoryBasis}</p></div>
          <Icon name="recycle" size={42} strokeWidth={1.2} />
        </header>
        <div className="lb-passport-body">
          <div className="lb-passport-photo"><div><Icon name="passport" size={32} /><strong>Sample image placeholder</strong><span>No waste photo is attached to this preview</span></div></div>
          <div className="lb-passport-facts">
            <DetailList rows={[
              ["Record status", <StatusBadge key="demo" tone="demo">Sample / preliminary</StatusBadge>],
              ["Characterization", <StatusBadge key="pending" tone="pending">Pending</StatusBadge>],
              ["Verification", <StatusBadge key="unchecked">Not performed</StatusBadge>],
              ["Created (sample)", sample.createdLabel],
              ["Material origin (sample)", sample.origin],
            ]} />
            <button className="lb-button lb-button-secondary" onClick={copyId}><Icon name="copy" size={15} />Copy sample ID</button>
            <p className="lb-copy-message" role="status">{copyMessage}</p>
          </div>
        </div>
      </article>

      <div className="lb-passport-grid">
        <SectionCard title="Waste characterization" action={<StatusBadge tone="pending">Pending</StatusBadge>}>
          <div className="lb-empty-state"><span className="lb-empty-icon"><Icon name="recycle" size={22} /></span>
            <h3>Characterization unavailable</h3><p>No AI response is attached to this sample. The passport remains preliminary.</p></div>
          <DetailList rows={[["Characterized waste type", sample.characterizedType], ["Material / category details", sample.materialDetails], ["Characterization status", sample.characterizationStatus]]} />
        </SectionCard>
        <SectionCard title="Verification & ledger" className="lb-verification-card" action={<Icon name="lock" size={18} />}>
          <p className="lb-note">Ledger integrity has not been checked. Sample IDs are not real chain identifiers.</p>
          <DetailList rows={[["Verification status", sample.verification.status], ["Sample record identifier", sample.id], ["Chain identifier", sample.verification.chainId ?? "Not available"], ["Hash / ledger reference", sample.verification.hash ?? "Not available"]]} />
          <button className="lb-button lb-button-primary" disabled><Icon name="verify" size={15} />Verify Record — Part 3</button>
          <p className="lb-note lb-action-note">Verification will be connected in Part 3.</p>
        </SectionCard>
      </div>
      <div className="lb-passport-grid">
        <SectionCard title="Journey & processing timeline" action={<StatusBadge tone="demo">Illustrative</StatusBadge>}>
          <p className="lb-note">Example stages only, not actual recorded ledger events.</p><Timeline events={sample.journey} />
        </SectionCard>
        <SectionCard title="Processor & destination" action={<StatusBadge tone="pending">Unassigned</StatusBadge>}>
          <div className="lb-destination-icon"><Icon name="map" size={24} /></div>
          <h3 className="lb-destination-title">Awaiting a destination</h3>
          <p className="lb-note">No processor has been matched, accepted this waste, or completed processing.</p>
          <DetailList rows={[["Processor name", sample.processor.name], ["Location", sample.processor.location], ["Accepted waste / matching", sample.processor.matching], ["Assignment status", sample.processor.status]]} />
        </SectionCard>
      </div>
    </div>
  );
}
