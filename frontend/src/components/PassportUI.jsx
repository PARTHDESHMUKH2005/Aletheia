import Icon from "./Icon.jsx";

export function PageHeader({ title, description, eyebrow, action }) {
  return (
    <header className="lb-page-header">
      <div>
        {eyebrow && <p className="lb-eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action && <div className="lb-page-actions">{action}</div>}
    </header>
  );
}

export function SectionCard({ title, action, children, className = "" }) {
  return (
    <section className={`lb-section-card ${className}`}>
      <div className="lb-section-header"><h2>{title}</h2>{action}</div>
      {children}
    </section>
  );
}

export function StatusBadge({ children, tone = "neutral" }) {
  return <span className={`lb-badge lb-badge-${tone}`}>{children}</span>;
}

export function DetailList({ rows }) {
  return (
    <dl className="lb-detail-list">
      {rows.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
    </dl>
  );
}

export function Timeline({ events }) {
  return (
    <ol className="lb-timeline" aria-label="Illustrative waste journey">
      {events.map(event => (
        <li className={`lb-timeline-item lb-timeline-${event.state}`} key={event.label}>
          <span className="lb-timeline-marker"><Icon name={event.state === "example" ? "check" : "clock"} size={13} /></span>
          <div className="lb-timeline-heading"><strong>{event.label}</strong>
            <StatusBadge tone={event.state === "example" ? "demo" : "pending"}>
              {event.state === "example" ? "Illustrative" : "Pending"}
            </StatusBadge>
          </div>
          <p>{event.description}</p>
          {event.timestamp && <time dateTime={event.dateTime}>{event.timestamp}</time>}
        </li>
      ))}
    </ol>
  );
}
