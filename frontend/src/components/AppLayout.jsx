import { useEffect, useRef, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import Icon from "./Icon.jsx";

const groups = [
  { label: "Workspace", items: [
    { label: "Overview", to: "/dashboard", icon: "dashboard" },
    { label: "Upload Waste", to: "/", icon: "upload" },
    { label: "Waste Passports", to: "/passports", icon: "passport" },
    { label: "Traceability Map", to: "/map", icon: "map" },
  ] },
  { label: "Verification", items: [
    { label: "Verify Records", to: "/verify", icon: "verify" },
    { label: "Review Queue", to: "/review", icon: "review" },
  ] },
];
const names = { dashboard: "Overview", passports: "Waste Passports", streams: "Processing Result", map: "Traceability Map", review: "Review Queue", verify: "Verify Records" };

export default function AppLayout({ children }) {
  const [collapsed, setCollapsed] = useState(false);
  const [open, setOpen] = useState(false);
  const menuRef = useRef(null);
  const { pathname } = useLocation();
  const parts = pathname.split("/").filter(Boolean);
  const closeMenu = () => { setOpen(false); menuRef.current?.focus(); };

  useEffect(() => {
    if (!open) return;
    const closeOnEscape = event => {
      if (event.key === "Escape") { setOpen(false); menuRef.current?.focus(); }
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [open]);

  return (
    <div className={`lb-shell ${collapsed ? "lb-collapsed" : ""}`}>
      {open && <button className="lb-scrim" aria-label="Close navigation" onClick={closeMenu} />}
      <aside id="loopback-navigation" className={`lb-sidebar ${open ? "lb-sidebar-open" : ""}`}>
        <Link to="/dashboard" className="lb-brand" aria-label="LoopBack overview" onClick={() => setOpen(false)}>
          <span className="lb-brand-mark"><Icon name="recycle" size={21} /></span>
          <div className="lb-expanded"><strong>LoopBack</strong><span>Waste Intelligence Platform</span></div>
        </Link>
        <nav className="lb-sidebar-nav" aria-label="Main navigation">
          {groups.map(group => <div className="lb-nav-group" key={group.label}>
            <p className="lb-expanded">{group.label}</p>
            {group.items.map(item => <NavLink key={item.to} to={item.to} end={item.to === "/"}
              title={item.label} onClick={() => setOpen(false)}
              className={({ isActive }) => `lb-nav-link ${isActive ? "lb-active" : ""}`}>
              <Icon name={item.icon} /><span className="lb-expanded">{item.label}</span>
            </NavLink>)}
          </div>)}
        </nav>
        <div className="lb-sidebar-bottom">
          <div className="lb-system-status lb-expanded"><span /><div><strong>Passport UI preview</strong><p>Sample data only</p></div></div>
          <div className="lb-account-row"><span className="lb-avatar">LB</span><div className="lb-expanded"><strong>Local workspace</strong><span>LoopBack demo</span></div></div>
          <button className="lb-collapse-button" aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-expanded={!collapsed} onClick={() => setCollapsed(value => !value)}>
            <Icon name="chevron" size={17} /><span className="lb-expanded">Collapse sidebar</span>
          </button>
        </div>
      </aside>
      <div className="lb-main">
        <header className="lb-topbar">
          <button ref={menuRef} className="lb-mobile-menu" aria-label="Open navigation" aria-expanded={open}
            aria-controls="loopback-navigation" onClick={() => setOpen(value => !value)}><Icon name="menu" size={20} /></button>
          <nav className="lb-breadcrumbs" aria-label="Breadcrumb">
            <Link to="/dashboard">LoopBack</Link>
            {parts.length ? parts.map((part, i) => <span key={i}><Icon name="chevron" size={13} />
              <span aria-current={i === parts.length - 1 ? "page" : undefined}>{names[part] || part}</span>
            </span>) : <span><Icon name="chevron" size={13} /><span aria-current="page">Upload Waste</span></span>}
          </nav>
          <div className="lb-topbar-actions">
            <label className="lb-global-search"><Icon name="search" size={15} />
              <span className="sr-only">Search records (not available in this preview)</span>
              <input disabled placeholder="Search records" title="Search is unavailable in this UI preview" />
            </label>
            <button className="lb-icon-button" disabled aria-label="Notifications unavailable in this preview" title="Notifications unavailable"><Icon name="bell" /></button>
            <span className="lb-avatar" aria-label="LoopBack workspace">LB</span>
          </div>
        </header>
        <main className="lb-content">{children}</main>
        <footer className="lb-footer">
          <p>Routing aid only. Confirm rules and processor authorization with the official CPCB or State Board source.</p>
          <p>Photos are sent to the model provider (Google for Gemini). Upload only waste photos, no faces or documents.</p>
        </footer>
      </div>
    </div>
  );
}
