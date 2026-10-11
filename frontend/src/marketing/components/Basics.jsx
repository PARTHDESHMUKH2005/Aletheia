import { useEffect, useState } from "react";
import { Link, NavLink } from "react-router-dom";
import { useInView, useReducedMotion } from "../hooks.js";
import { CONTACT_EMAIL } from "../data.js";

// Original Aletheia mark: an open loop (the route) closing on a dot (the record).
export function Mark({ size = 32, title }) {
  return (
    <svg className="al-mark" width={size} height={size} viewBox="0 0 40 40" role={title ? "img" : undefined}
      aria-hidden={title ? undefined : true} aria-label={title}>
      <circle cx="20" cy="20" r="20" fill="var(--al-forest)" />
      <path d="M28.5 14.2A10 10 0 1 0 30 20" fill="none" stroke="var(--al-ivory)" strokeWidth="2.6" strokeLinecap="round" />
      <path d="m24.6 13.4 4.4.6.4-4.4" fill="none" stroke="var(--al-ivory)" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="20" cy="20" r="3.2" fill="var(--al-beige)" />
    </svg>
  );
}

export function Wordmark({ size = 30 }) {
  return (
    <span className="al-wordmark"><Mark size={size} /><span>aletheia</span></span>
  );
}

export function DemoTag({ children = "Illustrative demo data" }) {
  return <span className="al-demo-tag">{children}</span>;
}

export function Reveal({ as: Tag = "div", delay = 0, className = "", children, ...rest }) {
  const [ref, inView] = useInView();
  return (
    <Tag ref={ref} className={`al-reveal ${inView ? "al-in" : ""} ${className}`} style={{ transitionDelay: `${delay}ms` }} {...rest}>
      {children}
    </Tag>
  );
}

const easeOut = t => 1 - Math.pow(1 - t, 3);

export function CountUp({ value, decimals = 0, prefix = "", suffix = "", duration = 1600, locale = "en-IN" }) {
  const [ref, inView] = useInView({ threshold: 0.5 });
  const reduced = useReducedMotion();
  const [shown, setShown] = useState(reduced ? value : 0);
  useEffect(() => {
    if (reduced) { setShown(value); return; }
    if (!inView) return;
    let raf; const start = performance.now();
    const tick = now => {
      const t = Math.min(1, (now - start) / duration);
      setShown(value * easeOut(t));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [inView, reduced, value, duration]);
  const fmt = n => n.toLocaleString(locale, { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  return (
    <span ref={ref} className="al-count">
      {/* Final value reserves the width so nothing shifts while counting. */}
      <span className="al-count-ghost" aria-hidden="true">{prefix}{fmt(value)}{suffix}</span>
      <span className="al-count-live" aria-hidden="true">{prefix}{fmt(shown)}{suffix}</span>
      <span className="al-sr">{prefix}{fmt(value)}{suffix}</span>
    </span>
  );
}

export function Nav() {
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);
  return (
    <header className="al-nav">
      <div className="al-container al-nav-inner">
        <Link to="/" className="al-nav-brand" aria-label="Aletheia home" onClick={close}><Wordmark size={30} /></Link>
        <button className="al-nav-toggle" aria-expanded={open} aria-controls="al-nav-menu" onClick={() => setOpen(v => !v)}>
          <span className="al-sr">{open ? "Close menu" : "Open menu"}</span>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
            {open ? <path d="M6 6l12 12M18 6 6 18" /> : <path d="M4 7h16M4 12h16M4 17h16" />}
          </svg>
        </button>
        <nav id="al-nav-menu" className={`al-nav-menu ${open ? "al-open" : ""}`} aria-label="Site">
          <NavLink to="/about" onClick={close} className={({ isActive }) => isActive ? "al-active" : ""}>About</NavLink>
          <a href="/#product" onClick={close}>Product</a>
          <Link to="/dashboard" onClick={close}>Launch app</Link>
          <Link to="/dashboard" className="al-btn al-btn-primary" onClick={close}>Open the app</Link>
        </nav>
      </div>
    </header>
  );
}

export function Footer() {
  return (
    <footer className="al-footer">
      <div className="al-container">
        <div className="al-footer-grid">
          <div className="al-footer-brand">
            <Wordmark size={32} />
            <p>Routes institutional waste to the right place and keeps a record of every handoff.</p>
          </div>
          <div>
            <h2>Product</h2>
            <ul>
              <li><a href="/#product">How it works</a></li>
              <li><Link to="/dashboard">Open the app</Link></li>
              <li><Link to="/verify">Verify a record</Link></li>
              <li><Link to="/passports">Waste passports</Link></li>
            </ul>
          </div>
          <div>
            <h2>Company</h2>
            <ul>
              <li><Link to="/about">About</Link></li>
              <li><a href="/about#team">Team</a></li>
              <li><a href={`mailto:${CONTACT_EMAIL}`}>Contact</a></li>
            </ul>
          </div>
          <div>
            <h2>Legal</h2>
            <ul>
              {/* Placeholder links until real pages exist. */}
              <li><a href="#privacy">Privacy</a></li>
              <li><a href="#terms">Terms of use</a></li>
              <li><a href="/about#trust">Disclaimer</a></li>
            </ul>
          </div>
        </div>
        <div className="al-footer-base">
          <p>Routing aid only. Confirm rules and processor authorization with the official CPCB or State Board source.</p>
          <p>© {new Date().getFullYear()} Aletheia. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
}

export function SectionHead({ eyebrow, title, children, center = false }) {
  return (
    <Reveal className={`al-section-head ${center ? "al-center" : ""}`}>
      {eyebrow && <p className="al-eyebrow">{eyebrow}</p>}
      <h2>{title}</h2>
      {children && <p className="al-lede">{children}</p>}
    </Reveal>
  );
}
