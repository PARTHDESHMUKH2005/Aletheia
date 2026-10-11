# LoopBack: demo data, scoring and assumptions

Carbon-aware waste routing: a photo is characterized, then matched to a buyer using a money/carbon slider.
**All processors, prices and recovery rates here are demo data. Nothing is a verified real business or a live quote.**

## Location (demo pincodes only)
- The pickup point comes from the request's `pincode`, looked up in `backend/app/data/pincodes_demo.json`.
- **The coordinates in that file are approximate area centres** typed in by hand for the demo (city-centre / main post-office area, roughly a few km of error). They are not surveyed points and were not checked against an India Post dataset.
- No external geocoder is ever called. A pincode that is not in the table is rejected with `Pincode not in demo data` and the list of available pincodes.
- Distances are straight-line (haversine), not road distance. Missing or invalid coordinates raise an error; they are never treated as 0 km.
- Buyers farther than `max_distance_km` (default 500, override with the `MAX_DISTANCE_KM` env var) are not ranked.

## Scoring
Per kg: `money = net ₹/kg ÷ best net ₹/kg`, `carbon = net CO2e/kg ÷ best net CO2e/kg`, where "best" is over all eligible buyers for the material (a fixed scale, not min-max over the shortlist). A measure whose spread across the shortlist is under 2% counts as equal. Ties go to the nearer buyer, then by name.

## Illustrative numbers (assumptions, not data)
- Every processor `recovery_rate` (0.85 to 0.95 for recyclers) is an illustrative assumption, not measured.
- Transport: ₹3 per tonne-km and 0.062 kg CO2e per tonne-km are unsourced assumptions.
- Processor prices with `price_basis: "illustrative_assumption"` (aluminium, e-waste, the Ludhiana steel mill, the reuse centre) are placeholders, not market quotes.
- CO2e factors are US EPA WARM values used as a proxy, not India-specific.
- Processors have no `authorization_ref`; every one is shown as "demo only, authorization not checked".

## Prices
Prices with `price_basis: "sourced"` (steel HMS Mumbai, Jalna, Mandi Gobindgarh; copper armature scrap Delhi, Mumbai) were checked on 2026-10-10 against `dataset-resized/Raw Material Prices December 2024.pdf` (BigMint, ₹/tonne ÷ 1000). All five matched. They are city wholesale benchmarks, not quotes from the fictional buyers. The PDF prints "13 Dec" without a year; 2024 comes from its title. Nothing had to be downgraded.

## Run the tests
`cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest` (an unrelated `web3` pytest plugin in some environments breaks collection otherwise).
