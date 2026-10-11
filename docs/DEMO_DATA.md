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
- Every processor `recovery_rate` (0.85 to 0.95 for recyclers) is an illustrative assumption, not measured. WARM's material-level recycling factors already include modeled material losses; the additional processor recovery rate is a separate demo multiplier, not a measured local yield.
- Transport: ₹3 per tonne-km and 0.062 kg CO2e per tonne-km are unsourced assumptions. They must be replaced with route- and vehicle-specific evidence before operational use.
- Processor prices with `price_basis: "illustrative_assumption"` (aluminium, e-waste, the Ludhiana steel mill, the reuse centre) are placeholders, not market quotes.
- There are 16 emission-factor rows: ten have cited US EPA WARM source rows and six are unverified or missing. Source-matched values are US proxies, not India-specific factors. Paper uses WARM's mixed-paper (general) row; cardboard uses corrugated containers. Missing factors leave a candidate unscored.
- The paper and corrugated values come from [US EPA WARM v16 Paper Products, Exhibit 3-7](https://www.epa.gov/system/files/documents/2023-12/warm_containers_packaging_and_non-durable_goods_materials_v16_dec.pdf), converted from MTCO2e per short ton to kg CO2e per kg. EPA reports the mixed-paper recycling factor as -3.55 and landfill factor as 0.07; corrugated as -3.14 and 0.18. Their differences are used as avoided emissions. The source models US waste and energy systems.
- The WARM material factors include modeled recycling losses, while the routing formula also applies the demo processor `recovery_rate`. Treat resulting carbon scores as comparative illustration only until local factors and measured yields are supplied.
- All 18 processor records are fictional seeded demo entities. Every `authorization_ref` and `authorization_checked_on` is null; none is eligible to represent a verified real-world handler. Replace the records and confirm registration/authorization against the relevant official CPCB or State Board source before any live routing.

## Vision evaluation dataset
- `dataset-resized/` is the 2,527-image TrashNet collection. The source and MIT license attribution are recorded in [`dataset-resized/README.md`](../dataset-resized/README.md) and [`dataset-resized/LICENSE`](../dataset-resized/LICENSE).
- `eval/labels.csv` contains 31 reviewed rows: 10 cardboard, 10 paper, and 11 broad metal-scrap examples. All 31 referenced photos exist and have distinct file hashes. The labels cover only three material groups; every row has `hazardous=false` and `is_storage_device=false`. There are no labeled glass, plastic, trash, e-waste, batteries, hazard-positive, or storage-device examples.
- The metal label is deliberately broad: any clean metal-scrap family prediction counts as correct because TrashNet's metal class does not identify alloy. It cannot validate aluminium, steel, copper, or mixed-metal precision separately.
- The live evaluation was not run because this workspace has no `.env` model configuration. Do not cite accuracy, latency, calibration, or confidence-gate results until the live evaluation is run with an available model account and the output is recorded. The 31-row sample is a smoke-check set, not a representative performance benchmark.

## Prices
Prices with `price_basis: "sourced"` (steel HMS Mumbai, Jalna, Mandi Gobindgarh; copper armature scrap Delhi, Mumbai) were reconciled on 2026-10-10 against `dataset-resized/Raw Material Prices December 2024.pdf` (BigMint, ₹/tonne ÷ 1000). All five matched that source. The observations themselves are dated December 2024, so this check verifies transcription, not current market validity. They are city wholesale benchmarks, not quotes from the fictional buyers. The PDF prints "13 Dec" without a year; 2024 comes from its title.

## Review disposition before live deployment
- Source transcription and demo boundaries have been reviewed. The values remain suitable for a clearly labeled demo only.
- Production data is still unavailable: real processor identities and current authorizations, live buyer quotes by material/grade/quantity, measured recovery yields, current road distances, and sourced transport cost/emissions are needed.
- No India-specific lifecycle factors have been established. Do not present the US WARM proxies as India impact measurements or carbon claims.
- Rule mappings remain routing guidance with human-review flags. Material names alone do not establish legal scope; confirm the waste generator, contamination, product category, recipient status, State Board requirements, and current law for each real handoff.
- Evaluation remains blocked on a model API credential and representative, independently reviewed labels spanning the supported material and safety classes.

## Validation
Use the platform-specific test commands in [README.md](../README.md#-quick-start) and the [build guide](../BUILD.md#local-validation). If an unrelated globally installed pytest plugin prevents collection, retry with plugin autoload disabled for that command.
