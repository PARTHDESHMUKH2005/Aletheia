// Compliance details for a routed item: governing rule, who may handle it, required paperwork,
// and whether the rule text is verified. Reads routing.compliance (falls back to rule_name for older records).
export default function ComplianceCard({ routing, processor }) {
  if (!routing || routing.refused) return null;
  const c = routing.compliance || (routing.rule_name ? { rule_name: routing.rule_name, paperwork: [] } : null);
  if (!c) return null;
  const rows = [
    ["Governing rule", c.rule_name],
    ["Notification / section", c.section_ref || "Not recorded: check the official text"],
    c.handler_requirement && ["Who may handle it", c.handler_requirement],
    ["Hazardous", c.hazardous ? "Yes: authorized handlers only" : "No"],
    c.regulated != null && ["Specifically regulated", c.regulated ? "Yes" : "No specific rule for this material"],
    c.paperwork?.length > 0 && ["Paperwork required", c.paperwork.join(" · ")],
    processor && ["Processor authorization", processor.authorization_label || "demo only, authorization not checked"],
    ["Human review", routing.review_required ? "Required before handoff" : "Not required"],
  ].filter(Boolean);
  return (
    <div className="border rounded-lg p-4 bg-white text-sm" data-testid="compliance-card">
      <div className="flex items-center gap-2 mb-2">
        <span className="font-medium">Compliance</span>
        {c.verified === false && (
          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-800">
            {c.unverified_label || "Unverified, check the official text"}
          </span>
        )}
        {c.verified === true && <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-green-100 text-green-800">Verified against official text</span>}
      </div>
      <div className="text-xs rounded-md bg-amber-50 text-amber-800 px-2 py-1 mb-2">
        Demo data: rule summaries are drawn from our RULES.md reference, not legal advice. Confirm with the official gazette.
      </div>
      <dl className="space-y-1">
        {rows.map(([k, v]) => (
          <div key={k} className="flex gap-2"><dt className="text-gray-500 w-44 shrink-0">{k}</dt><dd>{v}</dd></div>
        ))}
      </dl>
      {c.key_requirements?.length > 0 && (
        <div className="mt-3">
          <div className="text-gray-500 mb-1">Key requirements for this material</div>
          <ul className="list-disc pl-5 space-y-0.5">{c.key_requirements.map((r) => <li key={r}>{r}</li>)}</ul>
        </div>
      )}
      <p className="text-xs text-gray-500 mt-2">Routing aid only. LoopBack records handoffs; it does not certify compliance. Confirm with the official CPCB or State Board source.</p>
    </div>
  );
}
