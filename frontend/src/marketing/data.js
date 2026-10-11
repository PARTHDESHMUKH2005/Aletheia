// Marketing content for the Aletheia landing and About pages.
// Every number here is either illustrative demo data (computed from the app's own
// seeded receipt logic, synthetic buyers and prices) or a sourced figure shown with its link and year.

// Placeholder contact address. Replace with the real inbox before launch.
export const CONTACT_EMAIL = "hello@aletheia.example";

// Illustrative demo batch: one campus workshop (Patiala, seeded) routing five materials.
// Values = the app's counterfactual receipt (diff vs. landfill/informal default) at
// slider 0 (most money) and slider 1 (most carbon). Synthetic buyers, demo prices.
export const demoBatch = [
  { material: "Steel scrap", kg: 120, money: { inr: 4042, co2e: 215 }, carbon: { inr: 3691, co2e: 229 } },
  { material: "Aluminium", kg: 25, money: { inr: 4244, co2e: 214 }, carbon: { inr: 3750, co2e: 240 } },
  { material: "Copper", kg: 8, money: { inr: 5915, co2e: 39 }, carbon: { inr: 5915, co2e: 39 } },
  { material: "Cardboard", kg: 60, money: { inr: 706, co2e: 186 }, carbon: { inr: 600, co2e: 209 } },
  { material: "Paper", kg: 40, money: { inr: 470, co2e: 135 }, carbon: { inr: 400, co2e: 152 } },
];

export const demoTotals = {
  kg: 253, // 120 + 25 + 8 + 60 + 40
  materials: 5,
  inrMostMoney: 15377, // sum of money.inr (unrounded 15,377.36)
  co2eMostCarbon: 868, // sum of carbon.co2e (unrounded 868.06)
  co2eMostMoney: 790,
  inrMostCarbon: 14356,
};

// The steel line of the demo batch, as the decision screen shows it.
export const steelDecision = {
  money: {
    pick: "Demo Foundry (Mandi Gobindgarh)",
    note: "Picked for money. Sliding toward carbon would favour the carbon leader instead.",
    candidates: [
      { name: "Demo Foundry (Mandi Gobindgarh)", km: 37.5, inr: 4042.5, co2e: 215.04, price: "sourced price", why: null },
      { name: "Demo Steel Re-rolling Mill (Ludhiana)", km: 80.4, inr: 3691.06, co2e: 229.4, price: "illustrative price",
        why: "₹351.44 less, 14.36 kg CO2e more avoided, 42.9 km farther." },
    ],
  },
  carbon: {
    pick: "Demo Steel Re-rolling Mill (Ludhiana)",
    note: "Picked for carbon avoided, trading off against the better-paying option.",
    candidates: [
      { name: "Demo Steel Re-rolling Mill (Ludhiana)", km: 80.4, inr: 3691.06, co2e: 229.4, price: "illustrative price", why: null },
      { name: "Demo Foundry (Mandi Gobindgarh)", km: 37.5, inr: 4042.5, co2e: 215.04, price: "sourced price",
        why: "₹351.44 more, 14.36 kg CO2e less avoided, 42.9 km closer." },
    ],
  },
};

// Market figures, each shown with its source link and year. Taken from secondary citations; check the primary documents.
export const marketFigures = [
  {
    value: 170339, suffix: " t", label: "of solid waste generated per day in India's cities",
    source: "CPCB Annual Report on Solid Waste Management 2021-22, as cited by CAG", year: "2021-22",
    url: "https://cpcb.nic.in/uploads/MSW/MSW_AnnualReport_2021-22.pdf",
  },
  {
    value: 58, suffix: "%", label: "of collected solid waste is treated; the rest is not",
    source: "CPCB Annual Report 2021-22, as cited by CAG audit", year: "2021-22",
    url: "https://cag.gov.in/uploads/download_audit_report/2022/05-PA-on-Solid-Waste-Management-(SWM)-069b7f1c6092804.42011626.pdf",
  },
  {
    value: 4.1, decimals: 1, suffix: " Mt", label: "of e-waste generated in India in a single year",
    source: "Global E-waste Monitor 2024 (UNITAR, ITU)", year: "2022",
    url: "https://ewastemonitor.info/",
  },
  {
    value: 30, suffix: " Mt", label: "steel scrap market, mostly handled informally",
    source: "Ministry of Steel, reply in Parliament", year: "2023",
    url: "https://steel.gov.in/sites/default/files/2025-04/lu4667.pdf",
  },
  {
    value: 11.4, decimals: 1, prefix: "$", suffix: " bn", label: "India metal recycling market size",
    source: "IMARC Group market estimate", year: "2024",
    url: "https://www.imarcgroup.com/india-metal-recycling-market",
  },
];

export const wasteKinds = ["Steel scrap", "Aluminium", "Copper", "Mixed metal", "Paper", "Cardboard", "Laptops and desktops",
  "Storage drives", "Other electronics", "Lead-acid batteries", "Lithium batteries", "Used oil"];

export const orgKinds = ["Universities", "Colleges", "Manufacturers", "Data centers", "Corporate offices", "Research labs",
  "Campus workshops", "Warehouses"];

export const handoffs = ["Matched", "Collected", "Weighed", "Verified"];
