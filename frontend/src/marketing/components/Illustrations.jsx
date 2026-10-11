// Original line illustrations for the feature blocks. Decorative: the copy beside each says the same thing.
const base = { viewBox: "0 0 320 220", className: "al-illus", "aria-hidden": true, fill: "none", strokeLinecap: "round", strokeLinejoin: "round" };

export function PhotoIllus() {
  return (
    <svg {...base}>
      <rect x="40" y="22" width="104" height="176" rx="18" fill="var(--al-ivory)" stroke="var(--al-border-strong)" strokeWidth="1.5" />
      <rect x="52" y="44" width="80" height="96" rx="8" fill="var(--al-pale-sage)" />
      <path d="M60 128l14-22 10 12 8-9 16 19z" fill="var(--al-sage)" opacity=".7" />
      <rect x="64" y="96" width="22" height="12" rx="2" fill="var(--al-clay)" opacity=".8" transform="rotate(-12 75 102)" />
      <rect x="92" y="104" width="26" height="10" rx="2" fill="var(--al-green)" opacity=".8" transform="rotate(8 105 109)" />
      <path d="M60 52h12M52 52v10M124 52h-12M132 52v10M60 132h12M124 132h-12" stroke="var(--al-forest)" strokeWidth="2" />
      <circle cx="92" cy="170" r="11" stroke="var(--al-forest)" strokeWidth="2" />
      <path d="M156 110h30" stroke="var(--al-sage)" strokeWidth="2" strokeDasharray="3 5" />
      <path d="m182 104 8 6-8 6" stroke="var(--al-sage)" strokeWidth="2" />
      <rect x="198" y="62" width="104" height="96" rx="12" fill="var(--al-ivory)" stroke="var(--al-border)" />
      <text x="212" y="86" className="al-illus-k">MATERIAL</text>
      <text x="212" y="102" className="al-illus-t">Steel scrap</text>
      <text x="212" y="124" className="al-illus-k">AMOUNT</text>
      <text x="212" y="140" className="al-illus-t">about 120 kg</text>
    </svg>
  );
}

export function SliderIllus() {
  return (
    <svg {...base}>
      <rect x="34" y="40" width="252" height="140" rx="16" fill="var(--al-ivory)" stroke="var(--al-border)" />
      <text x="56" y="76" className="al-illus-t">₹</text>
      <path d="M262 64c-14 0-22 8-22 20 0 0 18 2 22-20zM240 84l10-10" stroke="var(--al-green)" strokeWidth="2" />
      <rect x="56" y="102" width="208" height="6" rx="3" fill="var(--al-pale-sage)" />
      <rect x="56" y="102" width="132" height="6" rx="3" fill="var(--al-green)" />
      <circle cx="188" cy="105" r="12" fill="var(--al-ivory)" stroke="var(--al-forest)" strokeWidth="2.5" className="al-illus-knob" />
      <rect x="56" y="134" width="90" height="26" rx="8" fill="var(--al-cream)" />
      <rect x="174" y="134" width="90" height="26" rx="8" fill="var(--al-pale-sage)" />
      <text x="68" y="151" className="al-illus-k">₹3,691</text>
      <text x="186" y="151" className="al-illus-k">229 kg CO2e</text>
    </svg>
  );
}

export function ReceiptIllus() {
  return (
    <svg {...base}>
      <path d="M96 20h128v172l-10.7-8-10.6 8-10.7-8-10.7 8-10.6-8-10.7 8-10.7-8-10.6 8-10.7-8-10.7 8-10.6-8L96 192z" fill="var(--al-ivory)" stroke="var(--al-border-strong)" strokeWidth="1.5" />
      <text x="112" y="46" className="al-illus-k">RECEIPT</text>
      <path d="M112 64h96M112 80h70" stroke="var(--al-border-strong)" strokeWidth="2" />
      <text x="112" y="106" className="al-illus-k">Default</text><text x="208" y="106" className="al-illus-k" textAnchor="end">₹0</text>
      <text x="112" y="126" className="al-illus-k">Chosen</text><text x="208" y="126" className="al-illus-k" textAnchor="end">₹4,042</text>
      <path d="M112 138h96" stroke="var(--al-forest)" strokeWidth="1.5" />
      <text x="112" y="158" className="al-illus-t">Difference</text>
      <circle cx="250" cy="64" r="22" fill="var(--al-pale-sage)" />
      <path d="m240 64 7 7 13-14" stroke="var(--al-forest)" strokeWidth="2.5" />
    </svg>
  );
}

export function RecordIllus() {
  const xs = [52, 124, 196, 268];
  return (
    <svg {...base}>
      <path d="M52 110H268" stroke="var(--al-border-strong)" strokeWidth="2" />
      {xs.map((x, i) => (
        <g key={x}>
          <circle cx={x} cy="110" r="24" fill={i === 3 ? "var(--al-forest)" : "var(--al-ivory)"} stroke="var(--al-forest)" strokeWidth="2" />
          <path d={`m${x - 8} 110 6 6 11-12`} stroke={i === 3 ? "var(--al-ivory)" : "var(--al-forest)"} strokeWidth="2.5" />
          <text x={x} y="158" textAnchor="middle" className="al-illus-k">{["Matched", "Collected", "Weighed", "Verified"][i]}</text>
        </g>
      ))}
      <rect x="110" y="34" width="100" height="30" rx="15" fill="var(--al-pale-sage)" />
      <text x="160" y="54" textAnchor="middle" className="al-illus-k">Nothing changed</text>
    </svg>
  );
}

export function ReuseIllus() {
  return (
    <svg {...base}>
      <rect x="56" y="58" width="120" height="78" rx="8" fill="var(--al-ivory)" stroke="var(--al-forest)" strokeWidth="2" />
      <rect x="66" y="68" width="100" height="58" rx="3" fill="var(--al-pale-sage)" />
      <path d="M40 148h152l-10 12H50z" fill="var(--al-cream)" stroke="var(--al-forest)" strokeWidth="2" />
      <path d="M106 86a14 14 0 1 1-4 16" stroke="var(--al-green)" strokeWidth="2.5" />
      <path d="m98 92 4 10 10-4" stroke="var(--al-green)" strokeWidth="2.5" />
      <rect x="214" y="64" width="78" height="30" rx="15" fill="var(--al-forest)" />
      <text x="253" y="84" textAnchor="middle" className="al-illus-k al-illus-inv">1. Reuse</text>
      <rect x="214" y="108" width="78" height="30" rx="15" fill="var(--al-pale-sage)" />
      <text x="253" y="128" textAnchor="middle" className="al-illus-k">2. Recycle</text>
      <path d="M190 97h16" stroke="var(--al-sage)" strokeWidth="2" strokeDasharray="3 4" />
    </svg>
  );
}

export function UnsureIllus() {
  return (
    <svg {...base}>
      <path d="M38 40h184a16 16 0 0 1 16 16v56a16 16 0 0 1-16 16H96l-24 20v-20H38a16 16 0 0 1-16-16V56a16 16 0 0 1 16-16z" fill="var(--al-ivory)" stroke="var(--al-border-strong)" strokeWidth="1.5" />
      <text x="40" y="76" className="al-illus-t">Not sure about this one.</text>
      <text x="40" y="100" className="al-illus-k">Sending it to a person to check.</text>
      <circle cx="272" cy="166" r="30" fill="var(--al-gold-soft)" />
      <circle cx="272" cy="156" r="9" stroke="var(--al-gold)" strokeWidth="2.2" />
      <path d="M256 182c3-9 10-13 16-13s13 4 16 13" stroke="var(--al-gold)" strokeWidth="2.2" />
    </svg>
  );
}
