# RULES.md: Indian waste rules reference for LoopBack

Working reference for the rules table (`backend/app/data/rules.json`). It covers the E-Waste, Hazardous Waste, Battery, Plastic and Solid Waste rules, plus a few neighbours, and maps each LoopBack material to the rule that governs it.

This is a build aid, not legal advice. LoopBack routes and records. It does not certify compliance.

## 0. How to read this file

Every statement carries a label:

- **[V]** Verified against an official gazette notification or CPCB/MoEFCC publication. A source is linked below where it was checked during this update; older entries may still refer to source documents previously reviewed.
- **[M]** From my general knowledge. Likely right in outline, but verify against the official text before you cite it in the pitch or fill `section_ref` in `rules.json`.
- **[P]** LoopBack policy. A design choice of ours, not something the law says.

Rule numbers are given only where the official text has been checked. Where the exact provision or applicability is uncertain, leave `section_ref` empty and keep the row in human review.

Official sources checked on 11 October 2026: [CPCB SWM Rules, 2026](https://swm.cpcb.gov.in/images/solid-waste-management-rules-2026.pdf), [MoEFCC HOTWM Amendment Rules, 2025 (G.S.R. 438(E))](https://moef.gov.in/storage/tender/1751520898.pdf), [MoEFCC/CPCB rule texts and amendments linked below](https://moef.gov.in/rules-regulations-3), [CPCB E-Waste FAQ](https://cpcb.nic.in/uploads/Projects/E-Waste/FAQ_ewaste_23012024.pdf), and [Haryana SPCB's copy of the HOTWM Rules, 2016](https://www.hspcb.gov.in/uploads/laws/hsm1.pdf). Check the official indexes for later amendments before relying on a row.

## 1. Quick map: waste to governing rule

| Waste | Governing rule | Regulated? |
|---|---|---|
| Clean aluminium, steel, copper scrap | Solid Waste Management Rules, 2026 for dry waste; the 2025 hazardous-waste amendment adds conditional EPR rules for scheduled non-ferrous products [V, M] | Yes. Segregation and local-body handoff duties apply. Additional non-ferrous EPR duties depend on the product and actor; review aluminium and copper streams. |
| Mixed metal scrap | Solid Waste Management Rules, 2026; hazardous-waste rules if contaminated; conditional non-ferrous EPR [V, M, P] | Yes. Review before handoff if contamination or product scope is unclear |
| Paper, cardboard | Solid Waste Management Rules, 2026 [V] | Yes. Segregate as dry waste and follow local-body collection directions; additional duties apply to specified institutions and bulk waste generators [V] |
| Computers, IT equipment, appliances | E-Waste (Management) Rules, 2022 | Yes. Bulk consumers must hand over only to a registered producer, refurbisher or recycler. |
| Storage drives | E-Waste Rules for the device, plus data wipe [P] | Yes |
| Lead-acid (UPS) and lithium batteries | Battery Waste Management Rules, 2022, as amended [V] | Separate from mixed waste and hand over through an eligible collection, refurbishment or recycling route. LoopBack's hazard flag is a safety precaution, not a legal classification under the Hazardous and Other Wastes Rules [V, P] |
| Used oil, solvents, chemical waste | Hazardous and Other Wastes Rules, 2016 | Yes. Authorization and manifest. |
| Plastic packaging and plastic waste | Plastic Waste Management Rules, 2016 and amendments | Yes. EPR and registration. |
| Household special-care waste (paint cans, household batteries, bulbs) | Solid Waste Management Rules, 2026; separate hazardous-waste rules may also apply | Segregate and hand over under local-body directions; confirm the current collection route [V, M] |
| Hospital or lab biological waste | Bio-Medical Waste Management Rules, 2016 [M] | Out of LoopBack scope. Flag and refuse. |

## 2. E-Waste (Management) Rules, 2022

Principal rules: [G.S.R. 801(E), 2 November 2022](https://moef.gov.in/uploads/2022/11/E-Waste-Management-Rules-2022.pdf). The official text and [MoEFCC rules index](https://moef.gov.in/rules-regulations-3) list G.S.R. 61(E), 30 January 2023; G.S.R. 534(E), 24 July 2023; G.S.R. 164(E), 8 March 2024; and G.S.R. 699(E), 12 November 2024. The rules came into force on 1 April 2023 and superseded the 2016 rules [V]. The March 2024 amendment changed the dismantler definition, added a possible nine-month reporting extension, and added EPR-certificate platform provisions. The November 2024 amendment replaced rule 23's contravention provision with a penalty under section 15 of the Act [V].

**Verified**
- Rule 3(f): "dismantler" means any person or entity engaged in dismantling used electrical and electronic equipment and components, in accordance with CPCB guidelines [V].
- Rule 9A: the Central Government may relax any deadline for filing returns or reports by a manufacturer, producer, refurbisher or recycler, for a further period not exceeding nine months [V].
- Rule 15, sub-rules (7) to (10): the Centre may set up one or more platforms to exchange or transfer EPR certificates. CPCB fixes a floor and ceiling price equal to 30 percent and 100 percent of the environmental compensation for not meeting EPR obligations under rule 22. Trades between registered entities on the portal must fall between those prices [V].
- Rule 22: environmental compensation for non-fulfilment of EPR [V].

**Verified from the principal rules and CPCB guidance**
- Rule 2 covers entities involved with equipment in Schedule I. Rule 4 requires portal registration for manufacturers, producers, refurbishers and recyclers; dismantlers are not listed as a separate registration category [V].
- Producers fulfil EPR targets through the portal. The rules provide distinct recycling and refurbishing certificates; refurbishing defers the producer's EPR liability for the corresponding quantity and period [V].
- Rule 3(b) defines a bulk consumer as an entity that has used at least 1,000 Schedule I units at any point in the financial year, including an e-retailer. Rule 8 requires such consumers to hand over e-waste only to a registered producer, refurbisher or recycler. The 2022 rules do not assign a bulk-consumer registration or annual-return duty [V]. Organizations need their equipment counts to determine whether this definition applies.
- Rule 16 restricts lead, mercury, cadmium, hexavalent chromium, PBB and PBDE in covered new equipment and parts to 0.1% by weight in homogeneous materials, except cadmium at 0.01%, subject to listed exemptions [V].
- Registered manufacturers, producers, refurbishers and recyclers have the specific portal return duties set out in their respective rules. Do not generalize those duties to every generator [V].
- CPCB's current FAQ says dismantlers are not a Rule 4 portal-registration category. Check the recipient's applicable registration and other permissions before relying on a dismantler route [V].

**LoopBack mapping**
- Working equipment can be routed to a registered refurbisher; other e-waste goes to a registered recycler. The demo does not establish a dismantler's eligibility [P].
- Storage drives: no move until a wipe or destruction record exists [P]. I am not aware of a specific rule that mandates this, so do not present it as law.

## 3. Hazardous and Other Wastes (Management and Transboundary Movement) Rules, 2016

Principal rules: G.S.R. 395(E), 4 April 2016. Amendments on the CPCB page run from the First (6 July 2016) to the Tenth (12 November 2024) [V]. The Seventh (21 July 2022) added EPR for waste tyres and the Eighth (18 September 2023) added EPR for used oil [V]. The Ninth (12 March 2024) is G.S.R. 177(E) [V]. The Hazardous and Other Wastes (Management and Transboundary Movement) Amendment Rules, 2025 (G.S.R. 438(E), 1 July 2025) inserted Chapter VIII for EPR of scrap from specified non-ferrous products, effective 1 April 2026 [V].

**Verified from G.S.R. 177(E)**
- New definition 22A: "deposition centres" are the centres specified in the Solid Waste Management Rules, 2016 for collecting domestic hazardous waste [V]. The 2016 rules were superseded by the 2026 rules; verify how this cross-reference is applied before using it for a live route.
- Rule 6(1B) and (1C): deposition centres need authorization from the State Pollution Control Board or Committee, hand domestic hazardous waste to the actual user or disposal facility operator, keep records in Form 3, and file an annual return in Form 4 [V].
- Rule 8(1) proviso: small generators producing 5 to 10 tonnes a year may store up to 180 days of annual capacity. Those under 5 tonnes a year may store up to 365 days [V].
- Rule 12(6B): import of post-industrial or pre-consumer polyethylene waste is allowed with a requirement to export at least 35 percent of total annual turnover [V].
- Rule 29, sub-rules (7) to (9): EPR certificate exchange platform and price band, tied to environmental compensation under rule 39 [V].
- Rule 30(5): the Centre may relax return deadlines by up to nine months for producers, collection agents, recyclers and used oil importers [V].
- Schedule III Part B and Schedule VI: entries on polysiloxanes changed [V].
- Schedule IX (waste tyre EPR): platform and price band, retreader duties (monthly portal submissions, quarterly and annual returns), and relaxation of return deadlines [V].
- Form 2 (authorization), general condition 15: hazardous waste produced sporadically, for example by fire, natural calamity or a chemical spill, must be sent to a disposal facility operator or actual user. Hazardous waste produced routinely in the consented process must be added to the authorization within one month of being identified [V].

**Verified from the rules**
- Rule 6 requires an occupier handling listed hazardous waste to obtain State Board authorization; apply in Form 1 and receive authorization in Form 2 [V]. Applicability depends on the waste and activity.
- Rule 8 sets a general 90-day storage limit, subject to specified exceptions. Rule 8(1)(b) permits up to 180 days for eligible small generators producing 5–10 tonnes/year and up to 365 days for those producing under 5 tonnes/year [V].
- Rules 18–19 require safe transport and the Form 10 manifest for domestic movement. The sender or receiver arranging transport must have the necessary State Board transport authorization [V].
- Rule 4 restricts handling and disposal to the authorized actual users and facilities named by the rules and authorization [V].
- Rule 17 requires safe packaging and Form 8 labels; Rule 18(2) also requires the Form 9 transport-emergency information [V].
- Used oil is covered by the rules' waste entries. The 2023 amendment inserted the used-oil EPR chapter, effective 1 April 2024; the EPR registration and targets depend on the role of the entity [V]. Do not describe every used-oil generator as an EPR-obligated producer.
- Rule 22 requires immediate reporting to the State Board or Committee when an accident occurs during handling of hazardous or other waste, using Form 11 [V].

**LoopBack mapping**
- Used oil, solvents, chemical residues, contaminated metal scrap and similar items are hazardous. The agent only routes them to processors whose authorization covers that waste type, and flags them for human review. It never advises on handling [P].
- Clean metal scrap that picks up oil or chemical contamination should be treated as potentially hazardous and sent to review [P].

## 4. Battery Waste Management Rules, 2022

The [Battery Waste Management Rules, 2022 (S.O. 3984(E), 22 August 2022)](https://moef.gov.in/uploads/pdf-uploads/pdf_676567459cdfe9.16099796.pdf) apply to all battery types regardless of chemistry, size, volume, weight, material composition or use (rule 2). The MoEFCC rules index lists amendments dated 25 October 2023, 14 March 2024, 20 June 2024, 3 December 2024 and 24 February 2025. The 2025 amendment permits specified EPR registration-number QR/barcode labeling, subject to notice to CPCB, and creates a quarterly published producer list [V].

- Covers battery types regardless of chemistry, shape, volume, weight, composition or use, subject to stated exclusions [V].
- Producers carry EPR obligations; amendments set collection, recycling and refurbishment targets, registration, and certificate rules [V].
- Schedule I sets battery labelling rules. Waste battery collected by a producer must be sent for recycling or refurbishment, not landfilling or incineration [V].
- Consumers must keep waste batteries separate from other waste streams and give them to an entity engaged in collection, refurbishment or recycling (rule 5). Recyclers and refurbishers must be registered under the rules (rules 8-9) [V].
- Waste batteries may be hazardous or non-hazardous under the rules' definition. LoopBack marks battery streams for safety review and restricts them to a recipient with checked eligibility as a precaution; this flag does not assert that every battery is hazardous waste under the HOTWM Rules [V, P].

**LoopBack mapping:** `battery_lead_acid` and `battery_lithium` get an internal hazard/safety flag and human review. Routes require a checked recipient reference in the demo. This is a conservative product rule, not a finding that every battery is legally hazardous waste. Lithium batteries also carry a fire risk, so the agent surfaces a warning [P].

## 5. Plastic Waste Management Rules, 2016 and amendments

Principal rules: G.S.R. 320(E), 18 March 2016. Amended by G.S.R. 285(E) (27 March 2018), 571(E) (12 August 2021), 647(E) (17 August 2021), 133(E) (16 February 2022), 522(E) (6 July 2022), 318(E) (27 April 2023), 807(E) (30 October 2023) and G.S.R. 201(E) (14 March 2024) [V]. The official [MoEFCC 2024 amended text](https://moef.gov.in/uploads/pdf-uploads/pdf_684015cdcfe270.47591512.pdf) and [rules index](https://moef.gov.in/rules-regulations-3) provide the source record.

**Verified from G.S.R. 522(E)**
- New definitions: biodegradable plastics, end of life disposal, importer, plastic packaging, plastic waste processors, post-consumer and pre-consumer plastic packaging waste, recyclers, reuse, use of recycled plastic, and waste to energy [V].
- Rule 9: producers, importers and brand owners fulfil EPR for plastic packaging under the guidelines in Schedule II [V].
- Rule 10: compostable plastics must conform to IS/ISO 17088:2021. Biodegradable plastics must meet Bureau of Indian Standards standards and be certified by CPCB, with provisional certificate arrangements [V].
- Rule 11: labelling must show the producer or brand owner name, registration number and thickness, with listed exemptions [V].
- Rule 13: registration with the State Pollution Control Board or Committee (operating in one or two states) or CPCB (more than two states) for manufacturers of carry bags, recyclers and processors [V].
- Rule 18: environmental compensation on the polluter pays principle [V].
- Schedule II, paragraph 7.8: packaging made from biodegradable plastics is outside the EPR target [V].
- Form IV: annual data by 30 April to the State Pollution Control Board. Form VI note: annual information to CPCB by 30 April [V].
- CPCB e-governance document: an in-house portal for registration of producers, importers and brand owners and for plastic waste processing facilities, with CPCB issuing online e-registration certificates. A separate portal handles compostable plastic certificates [V].

**Verified from the official amendments**
- Schedule II defines five packaging categories: rigid (I), flexible (II), multilayered with a non-plastic layer (III), compostable (IV), and biodegradable (V) [V].
- The 2021 amendment phased the minimum carry-bag thickness to 75 microns from 30 September 2021 and 120 microns from 31 December 2022. The ban on the notified single-use plastic items took effect on 1 July 2022 [V].
- Schedule II sets recycled-content and reuse obligations by packaging category and year. Check the current schedule before applying a target to an entity [V].

**LoopBack mapping:** plastic is not in the current material list. If you add it, route to plastic recyclers or processors registered under rule 13 and prefer reuse and recycling over waste-to-energy, following the hierarchy [P].

The December 2024 [EPR rules proposal for paper, glass and metal packaging and sanitary products](https://moef.gov.in/storage/tender/1734524379.pdf) is explicitly a draft notification. Do not treat it as an operative obligation unless a final notification is confirmed. The draft excludes non-ferrous metal-based packaging.

## 6. Solid Waste Management Rules, 2026

The Ministry of Environment, Forest and Climate Change notified the Solid Waste Management Rules, 2026 as S.O. 388(E) on 27 January 2026. They came into force on 1 April 2026 and superseded the 2016 rules [V]. The official [CPCB copy of the 2026 rules](https://swm.cpcb.gov.in/images/solid-waste-management-rules-2026.pdf) is the source for the references below.

- Rule 3(s) defines dry waste as waste other than wet, sanitary and special-care waste, including recyclable and non-recyclable waste [V].
- Rule 5(1)(b) requires waste generators to segregate and store four streams at source (wet, dry, sanitary and special care) and hand them to authorized waste pickers or waste collectors as directed by the local body [V].
- Rule 5(2) requires institutions with more than 5,000 sq. m. and specified other entities, within one year of notification and in partnership with the local body, to arrange source segregation, separate collection, and hand recyclable material to authorized waste pickers or recyclers [V].
- Rule 3(i) defines a bulk waste generator using one or more thresholds: building area of at least 20,000 sq. m., water consumption of at least 40,000 litres per day, or solid-waste generation of at least 100 kg per day, for listed entity types including educational institutions [V]. Rule 6 sets additional registration, handling, and reporting duties for those entities [V].
- Applicability depends on the waste stream, institution and local-body directions. Do not assume a sample organization meets a threshold without its data [P].

**LoopBack mapping:** paper, cardboard and clean metal scrap are represented as dry waste. The app should route them according to local-body directions; direct recycler handoff is supported by rule 5(2) for covered institutions after its transition period. The current organization records do not include the area, water use or waste generation needed to determine those obligations [V, P].
## 7. Neighbouring rules and the base law

- **Environment (Protection) Act, 1986** is the enabling law for all three gazettes you uploaded, which cite sections 3, 6, 8 and 25 [V].
- **Bio-Medical Waste Management Rules, 2016** cover hospital and clinical waste [M]. Out of scope. The agent flags and refuses.
- **Environment (Construction and Demolition) Waste Management Rules, 2025 (G.S.R. 219(E))** superseded the 2016 rules and came into force on 1 April 2026 [V]. Out of LoopBack scope for now.
- Radioactive waste, explosives and import or export under the Basel Convention are out of scope.

## 8. LoopBack material mapping (feeds rules.json)

| material | hazardous default | governing rule | who may handle | paperwork | basis |
|---|---|---|---|---|---|
| `aluminium_scrap` | no | SWM Rules, 2026; conditional non-ferrous EPR under HOTWM Rules, Chapter VIII | authorized waste picker or collector per local-body directions; registered recycler where applicable | segregation and local-body handoff details | V, M, P |
| `steel_scrap` | no | SWM Rules, 2026 (dry waste) | authorized waste picker or collector per local-body directions | segregation and local-body handoff details | V, M, P |
| `copper_scrap` | no | SWM Rules, 2026; conditional non-ferrous EPR under HOTWM Rules, Chapter VIII | authorized waste picker or collector per local-body directions; registered recycler where applicable | segregation and local-body handoff details | V, M, P |
| `mixed_metal` | no, review if unsure | SWM Rules, 2026; HW Rules if contaminated; conditional non-ferrous EPR | authorized waste picker or collector after sorting; human review if uncertain | segregation and local-body handoff details | V, M, P |
| `paper` | no | SWM Rules, 2026 (dry waste) | authorized waste picker or collector per local-body directions; authorized recycler where rule 5(2) applies | segregation and local-body handoff details | V, M, P |
| `cardboard` | no | SWM Rules, 2026 (dry waste) | authorized waste picker or collector per local-body directions; authorized recycler where rule 5(2) applies | segregation and local-body handoff details | V, M, P |
| `e_waste_computer` | regulated | E-Waste (Management) Rules, 2022 | registered refurbisher or recycler; do not assume dismantler registration | transfer record | V, P |
| `e_waste_storage_drive` | regulated | E-Waste Rules, 2022, plus data wipe policy | registered refurbisher or recycler after wipe | transfer record, wipe certificate | V, P |
| `e_waste_other` | regulated | E-Waste (Management) Rules, 2022 | registered refurbisher or recycler; do not assume dismantler registration | transfer record | V, P |
| `battery_lead_acid` | safety flag | Battery Waste Management Rules, 2022 | eligible collection, refurbishment or recycling route; recipient eligibility checked | transfer record | V, P |
| `battery_lithium` | safety flag | Battery Waste Management Rules, 2022 | eligible collection, refurbishment or recycling route; recipient eligibility checked | transfer record, fire risk flag | V, P |
| `used_oil` | yes | Hazardous and Other Wastes Rules, 2016 | authorized used oil recycler or re-refiner | generator authorization, manifest | V, M |
| `other` | unknown | review | human review | none | P |

## 9. Things LoopBack must never claim

- That a processor is authorized, unless you checked it against the current CPCB or State Board list on the day. Store `authorization_ref` and a check date.
- That using LoopBack makes an organization compliant. It routes and records.
- That a clean-scrap row has no legal duties in every state or for every buyer. Local licensing, tax and state rules can apply.
- Any rule number or section reference that is not on the official text. Leave `section_ref` null instead.

## 10. Verification checklist

1. Recheck the official rule indexes for amendments before each release; these references were checked on 11 October 2026.
2. Recheck every `rules.json` row that retains an `M` basis label before using it for a real waste stream or legal decision.
3. Check how the old SWM 2016 cross-reference in the 2024 hazardous-waste amendment applies after the SWM Rules, 2026 superseded the 2016 rules.
4. Seed each processor with its `authorization_ref` and a check date before enabling real routing.

## Machine-readable rules

`backend/app/data/rules.json` is the rule table used by the application. Its section references and verification basis should be maintained alongside this document; do not copy an old seed table into a second source of truth.
