const paths = {
  recycle: ["M7 19H4.815a2 2 0 0 1-1.749-2.97l4.343-7.815", "m3 11 4-1 1 4", "M12 19h5.186a2 2 0 0 0 1.749-2.97l-1.343-2.415", "m20 15-1 4-4-1", "m8 5 1.186-2.135a2 2 0 0 1 3.498 0l4.343 7.815", "m14 8 3 3 3-3"],
  dashboard: ["M3 3h7v7H3z", "M14 3h7v7h-7z", "M3 14h7v7H3z", "M14 14h7v7h-7z"],
  upload: ["M12 16V4", "m7 9 5-5 5 5", "M4 16v4h16v-4"],
  passport: ["M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z", "M14 2v6h6", "M8 12h8", "M8 16h5"],
  map: ["m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3z", "M9 3v15", "M15 6v15"],
  verify: ["M20 11a8 8 0 1 0-9 9", "m15 18 2 2 4-5", "m7 10 3 3 4-5"],
  review: ["M9 5H5v16h14V5h-4", "M9 3h6v4H9z", "M8 12h8", "M8 16h5"],
  chevron: ["m9 18 6-6-6-6"],
  menu: ["M4 6h16", "M4 12h16", "M4 18h16"],
  search: ["M21 21l-5-5"],
  bell: ["M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9", "M10 21h4"],
  copy: ["M9 9h12v12H9z", "M5 15H3V3h12v2"],
  print: ["M6 9V3h12v6", "M6 18H3V9h18v9h-3", "M6 14h12v8H6z"],
  check: ["m5 12 4 4L19 6"],
  clock: ["M12 7v5l3 2"],
  pin: ["M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0z"],
  weight: ["M6 7h12l3 14H3z"],
  calendar: ["M4 5h16v16H4z", "M16 3v4", "M8 3v4", "M4 11h16"],
  lock: ["M5 11h14v10H5z", "M8 11V7a4 4 0 0 1 8 0v4"],
};

export default function Icon({ name, size = 18, ...props }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"
      aria-hidden="true" focusable="false" {...props}>
      {(paths[name] || paths.passport).map((d, i) => <path key={i} d={d} />)}
      {name === "search" && <circle cx="10" cy="10" r="7" />}
      {name === "clock" && <circle cx="12" cy="12" r="9" />}
      {name === "pin" && <circle cx="12" cy="10" r="2.5" />}
      {name === "weight" && <circle cx="12" cy="5" r="2" />}
    </svg>
  );
}
