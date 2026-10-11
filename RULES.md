# RULES.md: Indian waste rules reference for LoopBack

Working reference for the rules table (`backend/app/data/rules.json`). It covers the E-Waste, Hazardous Waste, Battery, Plastic and Solid Waste rules, plus a few neighbours, and maps each LoopBack material to the rule that governs it.

This is a build aid, not legal advice. LoopBack routes and records. It does not certify compliance.

## 0. How to read this file

Every statement carries a label:

- **[V]** Verified against an official gazette notification or CPCB/MoEFCC publication. A source is linked below where it was checked during this update; older entries may still refer to source documents previously reviewed.
- **[M]** From my general knowledge. Likely right in outline, but verify against the official text before you cite it in the pitch or fill `section_ref` in `rules.json`.
- **[P]** LoopBack policy. A design choice of ours, not something the law says.

Rule numbers are given only where the official text has been checked. Where the exact provision or applicability is uncertain, leave `section_ref` empty and keep the row in human review.

Official sources: [CPCB SWM Rules, 2026](https://swm.cpcb.gov.in/images/solid-waste-management-rules-2026.pdf), [MoEFCC HOTWM Amendment Rules, 2025 (G.S.R. 438(E))](https://moef.gov.in/storage/tender/1751520898.pdf), CPCB (Waste Management section), MoEFCC, and the eGazette of India. Check official sources for the latest amendment before relying on a row.

## 1. Quick map: waste to governing rule

| Waste | Governing rule | Regulated? |
|---|---|---|
| Clean aluminium, steel, copper scrap | Solid Waste Management Rules, 2026 for dry waste; the 2025 hazardous-waste amendment adds conditional EPR rules for scheduled non-ferrous products [V, M] | Yes. Segregation and local-body handoff duties apply. Additional non-ferrous EPR duties depend on the product and actor; review aluminium and copper streams. |
| Mixed metal scrap | Solid Waste Management Rules, 2026; hazardous-waste rules if contaminated; conditional non-ferrous EPR [V, M, P] | Yes. Review before handoff if contamination or product scope is unclear |
| Paper, cardboard | Solid Waste Management Rules, 2026 [V] | Yes. Segregate as dry waste and follow local-body collection directions; additional duties apply to specified institutions and bulk waste generators [V] |
| Computers, IT equipment, appliances | E-Waste (Management) Rules, 2022 | Yes. Registered entities only. |
| Storage drives | E-Waste Rules for the device, plus data wipe [P] | Yes |
| Lead-acid (UPS) and lithium batteries | Battery Waste Management Rules, 2022 [M] | Yes. Hazardous handling. |
| Used oil, solvents, chemical waste | Hazardous and Other Wastes Rules, 2016 | Yes. Authorization and manifest. |
| Plastic packaging and plastic waste | Plastic Waste Management Rules, 2016 and amendments | Yes. EPR and registration. |
| Household special-care waste (paint cans, household batteries, bulbs) | Solid Waste Management Rules, 2026; separate hazardous-waste rules may also apply | Segregate and hand over under local-body directions; confirm the current collection route [V, M] |
| Hospital or lab biological waste | Bio-Medical Waste Management Rules, 2016 [M] | Out of LoopBack scope. Flag and refuse. |

## 2. E-Waste (Management) Rules, 2022

Principal rules: G.S.R. 801(E), 2 November 2022. Amended by G.S.R. 534(E), 24 July 2023, and G.S.R. 164(E), 8 March 2024 [V]. In force from 1 April 2023 [M]. These replaced the E-Waste Rules, 2016 [M].

**Verified**
- Rule 3(f): "dismantler" means any person or entity engaged in dismantling used electrical and electronic equipment and components, in accordance with CPCB guidelines [V].
- Rule 9A: the Central Government may relax any deadline for filing returns or reports by a manufacturer, producer, refurbisher or recycler, for a further period not exceeding nine months [V].
- Rule 15, sub-rules (7) to (10): the Centre may set up one or more platforms to exchange or transfer EPR certificates. CPCB fixes a floor and ceiling price equal to 30 percent and 100 percent of the environmental compensation for not meeting EPR obligations under rule 22. Trades between registered entities on the portal must fall between those prices [V].
- Rule 22: environmental compensation for non-fulfilment of EPR [V].

**From memory**
- Applies to manufacturers, producers, refurbishers, dismantlers and recyclers of electrical and electronic equipment listed in a schedule (over 100 items, covering IT and telecom equipment, consumer electronics and large and small appliances) [M].
- Producers, refurbishers, dismantlers and recyclers must register on the CPCB portal [M].
- Producers meet annual EPR targets, a percentage of past sales, by buying EPR certificates from registered recyclers and refurbishers. Separate certificates exist for recycling and refurbishing [M].
- E-waste must go to registered dismantlers, recyclers or refurbishers. It must not be landfilled, burned or sold to unregistered dealers [M].
- Restriction on hazardous substances in equipment (lead, mercury, cadmium, hexavalent chromium, PBB, PBDE), with a 0.1 percent limit by weight and 0.01 percent for cadmium [M].
- Annual returns are filed on the CPCB portal [M].
- Check whether the term "bulk consumer" (used in the 2016 rules for large institutions) still exists in the 2022 text, and what duties it carries. This matters for universities and data centers [M].

**LoopBack mapping**
- Working equipment goes to a registered refurbisher first. Non-working equipment goes to a registered dismantler or recycler [P, following the waste hierarchy].
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

**From memory**
- Occupiers who generate hazardous waste need authorization from the State Pollution Control Board (application Form 1, authorization Form 2) [M].
- General storage limit of 90 days, with the amendments above relaxing it for small generators [M].
- Movement needs a manifest and an authorized transporter [M].
- Hazardous waste may go only to authorized actual users, recyclers or treatment, storage and disposal facilities [M].
- Containers must be labelled and packaged to prescribed standards [M].
- Used or spent oil is listed as hazardous waste. It goes only to registered recyclers or re-refiners, with used oil EPR applying since 2023 [M].
- Accident reporting duties exist [M].

**LoopBack mapping**
- Used oil, solvents, chemical residues, contaminated metal scrap and similar items are hazardous. The agent only routes them to processors whose authorization covers that waste type, and flags them for human review. It never advises on handling [P].
- Clean metal scrap that picks up oil or chemical contamination should be treated as potentially hazardous and sent to review [P].

## 4. Battery Waste Management Rules, 2022

Nothing in your uploads covers these, so everything here is [M]. Notified in August 2022 and in force from 1 April 2023, replacing the Batteries (Management and Handling) Rules, 2001. Later amendments exist.

- Covers all battery types: electric vehicle, portable, automotive and industrial [M].
- Producers, including importers, carry EPR, register on a central portal, and meet recycling and recovered-material targets through EPR certificates [M].
- Batteries must be labelled. Landfilling and incineration are prohibited [M].
- Entities that hold used batteries (including large institutions with UPS banks) must hand them to the producer, a collection point or an authorized recycler or refurbisher [M].
- Lead-acid batteries (UPS and backup) move only to authorized battery recyclers or back to the seller, never to general scrap dealers [M].

**LoopBack mapping:** `battery_lead_acid` and `battery_lithium` are hazardous, routed only to authorized battery recyclers, and flagged for human review. Lithium batteries also carry a fire risk, so the agent surfaces a warning [P].

## 5. Plastic Waste Management Rules, 2016 and amendments

Principal rules: G.S.R. 320(E), 18 March 2016. Amended by G.S.R. 285(E) (27 March 2018), 571(E) (12 August 2021), 647(E) (17 August 2021), 133(E) (16 February 2022) and the Second Amendment, G.S.R. 522(E) (6 July 2022) [V].

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

**From memory**
- EPR categories for plastic packaging: rigid (I), flexible single or multilayer (II), multilayered with a non-plastic layer (III), and compostable sheets and carry bags (IV) [M].
- Ban on identified single-use plastic items from 1 July 2022, and minimum thickness requirements for carry bags [M].
- Recycled content requirements for rigid packaging under the EPR guidelines [M].

**LoopBack mapping:** plastic is not in the current material list. If you add it, route to plastic recyclers or processors registered under rule 13 and prefer reuse and recycling over waste-to-energy, following the hierarchy [P].

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
- **Construction and Demolition Waste Management Rules, 2016** [M]. Out of scope for now.
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
| `e_waste_computer` | regulated | E-Waste (Management) Rules, 2022 | registered refurbisher, dismantler or recycler | transfer record | V, M |
| `e_waste_storage_drive` | regulated | E-Waste Rules, 2022, plus data wipe policy | registered refurbisher or recycler after wipe | transfer record, wipe certificate | V, M, P |
| `e_waste_other` | regulated | E-Waste (Management) Rules, 2022 | registered refurbisher, dismantler or recycler | transfer record | V, M |
| `battery_lead_acid` | yes | Battery Waste Management Rules, 2022 | authorized battery recycler or producer take-back | transfer record | M |
| `battery_lithium` | yes | Battery Waste Management Rules, 2022 | authorized battery recycler | transfer record, fire risk flag | M |
| `used_oil` | yes | Hazardous and Other Wastes Rules, 2016 | authorized used oil recycler or re-refiner | generator authorization, manifest | V, M |
| `other` | unknown | review | human review | none | P |

## 9. Things LoopBack must never claim

- That a processor is authorized, unless you checked it against the current CPCB or State Board list on the day. Store `authorization_ref` and a check date.
- That using LoopBack makes an organization compliant. It routes and records.
- That a clean-scrap row has no legal duties in every state or for every buyer. Local licensing, tax and state rules can apply.
- Any rule number or section reference that is not on the official text. Leave `section_ref` null instead.

## 10. Verification checklist

1. Check the current principal texts and amendments: E-Waste Rules 2022, HW Rules 2016 including the 2025 amendment, Battery Waste Management Rules 2022, Plastic Waste Management Rules 2016, and SWM Rules 2026.
2. Replace every [M] statement you plan to cite with the official wording and section number.
3. Check whether the E-Waste 2022 text still has a "bulk consumer" duty.
4. Confirm the hazardous waste storage period and the authorization form numbers.
5. Check later amendments to the Battery Waste Management Rules and confirm how references to the superseded SWM 2016 rules are applied. HOTWM 2025 adds conditional non-ferrous EPR duties.
6. Seed each processor with its `authorization_ref` and a check date.

## Machine-readable rules

`backend/app/data/rules.json` is the rule table used by the application. Its section references and verification basis should be maintained alongside this document; do not copy an old seed table into a second source of truth.
