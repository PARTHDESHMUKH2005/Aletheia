# RULES.md: Indian waste rules reference for LoopBack

Working reference for the rules table (`backend/app/data/rules.json`). It covers the E-Waste, Hazardous Waste, Battery, Plastic and Solid Waste rules, plus a few neighbours, and maps each LoopBack material to the rule that governs it.

This is a build aid, not legal advice. LoopBack routes and records. It does not certify compliance.

## 0. How to read this file

Every statement carries a label:

- **[V]** Verified. The text appears in the documents you uploaded (gazette notifications G.S.R. 164(E) of 2024, G.S.R. 177(E) of 2024, G.S.R. 522(E) of 2022), the CPCB e-governance PDF, or the CPCB hazardous waste rules page in your screenshot.
- **[M]** From my general knowledge. Likely right in outline, but verify against the official text before you cite it in the pitch or fill `section_ref` in `rules.json`.
- **[P]** LoopBack policy. A design choice of ours, not something the law says.

Rule numbers are given only where the uploaded text confirms them. Where I am not sure of a number, I say "rule on X" and leave `section_ref` empty.

Official sources: CPCB (cpcb.nic.in, Waste Management section), MoEFCC (moef.gov.in), eGazette of India. These rules are amended often, so always check for the latest amendment.

## 1. Quick map: waste to governing rule

| Waste | Governing rule | Regulated? |
|---|---|---|
| Clean aluminium, steel, copper scrap | No dedicated rule found for domestic trade of clean, non-hazardous scrap [M] | Generally trade as scrap. Contamination changes this (see section 3). |
| Mixed metal scrap | Same as above, but may hide batteries, electronics or mercury items | Review if unsure |
| Paper, cardboard | Solid Waste Management Rules, 2016 (dry waste) [M] | Segregation duties, no authorization for recycling paper [M] |
| Computers, IT equipment, appliances | E-Waste (Management) Rules, 2022 | Yes. Registered entities only. |
| Storage drives | E-Waste Rules for the device, plus data wipe [P] | Yes |
| Lead-acid (UPS) and lithium batteries | Battery Waste Management Rules, 2022 [M] | Yes. Hazardous handling. |
| Used oil, solvents, chemical waste | Hazardous and Other Wastes Rules, 2016 | Yes. Authorization and manifest. |
| Plastic packaging and plastic waste | Plastic Waste Management Rules, 2016 and amendments | Yes. EPR and registration. |
| Household hazardous waste (paint, batteries, bulbs) | Solid Waste Management Rules, 2016, with deposition centres under the HW Rules | Yes |
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

Principal rules: G.S.R. 395(E), 4 April 2016. Amendments on the CPCB page run from the First (6 July 2016) to the Tenth (12 November 2024) [V]. The Seventh (21 July 2022) added EPR for waste tyres and the Eighth (18 September 2023) added EPR for used oil [V]. The Ninth (12 March 2024) is G.S.R. 177(E) [V].

**Verified from G.S.R. 177(E)**
- New definition 22A: "deposition centres" are the centres specified in the Solid Waste Management Rules, 2016 for collecting domestic hazardous waste [V].
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

## 6. Solid Waste Management Rules, 2016

Mostly [M]. Notified in April 2016.

- Waste generators must segregate at source into wet, dry and domestic hazardous waste [M].
- Bulk waste generators, which include institutions and large campuses (the thresholds are set by the local body and by floor area, water use or daily waste quantity), must segregate, process wet waste on site where possible, hand dry waste to authorized waste pickers or recyclers, and pay user fees [M].
- Domestic hazardous waste goes to deposition centres, which the 2024 HW amendment ties to authorization and record keeping [V].
- Local bodies are responsible for collection, processing and integrating waste pickers [M].
- Check whether these rules have since been replaced or revised, because replacement drafts were under discussion. Use the current version on the CPCB site [M].

**LoopBack mapping:** paper and cardboard fall under dry waste and go to authorized waste pickers or paper recyclers. A campus like yours is likely a bulk generator, which supports the pitch. Confirm the threshold with your local body [M].

## 7. Neighbouring rules and the base law

- **Environment (Protection) Act, 1986** is the enabling law for all three gazettes you uploaded, which cite sections 3, 6, 8 and 25 [V].
- **Bio-Medical Waste Management Rules, 2016** cover hospital and clinical waste [M]. Out of scope. The agent flags and refuses.
- **Construction and Demolition Waste Management Rules, 2016** [M]. Out of scope for now.
- Radioactive waste, explosives and import or export under the Basel Convention are out of scope.

## 8. LoopBack material mapping (feeds rules.json)

| material | hazardous default | governing rule | who may handle | paperwork | basis |
|---|---|---|---|---|---|
| `aluminium_scrap` | no | none specific for clean scrap | scrap dealer or foundry | weighment slip, LoopBack record | M, P |
| `steel_scrap` | no | none specific for clean scrap | scrap dealer or foundry | weighment slip, LoopBack record | M, P |
| `copper_scrap` | no | none specific for clean scrap | scrap dealer or foundry | weighment slip, LoopBack record | M, P |
| `mixed_metal` | no, review if unsure | none specific, HW Rules if contaminated | scrap dealer, sorted first | weighment slip | M, P |
| `paper` | no | SWM Rules, 2016 (dry waste) | authorized waste picker or paper recycler | weighment slip | M |
| `cardboard` | no | SWM Rules, 2016 (dry waste) | authorized waste picker or paper recycler | weighment slip | M |
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

1. Download the principal texts: E-Waste Rules 2022 (G.S.R. 801(E)), HW Rules 2016 (G.S.R. 395(E)) plus the Tenth Amendment of 12 November 2024, Battery Waste Management Rules 2022, Plastic Waste Management Rules 2016, Solid Waste Management Rules (current version).
2. Replace every [M] statement you plan to cite with the official wording and section number.
3. Check whether the E-Waste 2022 text still has a "bulk consumer" duty.
4. Confirm the hazardous waste storage period and the authorization form numbers.
5. Check the later amendments to the Battery and SWM rules.
6. Seed each processor with its `authorization_ref` and a check date.

## Appendix: rules.json seed

Starting point for `backend/app/data/rules.json`. `section_ref` is null everywhere until you verify it against the official text. `basis` follows the labels in section 0.

```json
[
  {"material": "aluminium_scrap", "hazardous": false, "regulated": false, "rule_name": "No specific rule for clean scrap", "section_ref": null, "handler_requirement": "scrap dealer or foundry", "paperwork": ["weighment slip", "ledger record"], "review_required": false, "basis": ["M", "P"]},
  {"material": "steel_scrap", "hazardous": false, "regulated": false, "rule_name": "No specific rule for clean scrap", "section_ref": null, "handler_requirement": "scrap dealer or foundry", "paperwork": ["weighment slip", "ledger record"], "review_required": false, "basis": ["M", "P"]},
  {"material": "copper_scrap", "hazardous": false, "regulated": false, "rule_name": "No specific rule for clean scrap", "section_ref": null, "handler_requirement": "scrap dealer or foundry", "paperwork": ["weighment slip", "ledger record"], "review_required": false, "basis": ["M", "P"]},
  {"material": "mixed_metal", "hazardous": false, "regulated": false, "rule_name": "No specific rule, Hazardous and Other Wastes Rules, 2016 if contaminated", "section_ref": null, "handler_requirement": "scrap dealer after sorting", "paperwork": ["weighment slip", "ledger record"], "review_required": true, "basis": ["M", "P"]},
  {"material": "paper", "hazardous": false, "regulated": false, "rule_name": "Solid Waste Management Rules, 2016 (dry waste)", "section_ref": null, "handler_requirement": "authorized waste picker or paper recycler", "paperwork": ["weighment slip", "ledger record"], "review_required": false, "basis": ["M"]},
  {"material": "cardboard", "hazardous": false, "regulated": false, "rule_name": "Solid Waste Management Rules, 2016 (dry waste)", "section_ref": null, "handler_requirement": "authorized waste picker or paper recycler", "paperwork": ["weighment slip", "ledger record"], "review_required": false, "basis": ["M"]},
  {"material": "e_waste_computer", "hazardous": false, "regulated": true, "rule_name": "E-Waste (Management) Rules, 2022", "section_ref": null, "handler_requirement": "registered refurbisher, dismantler or recycler", "paperwork": ["transfer record", "ledger record"], "review_required": false, "basis": ["V", "M"]},
  {"material": "e_waste_storage_drive", "hazardous": false, "regulated": true, "rule_name": "E-Waste (Management) Rules, 2022, data wipe policy", "section_ref": null, "handler_requirement": "registered refurbisher or recycler after wipe or destruction", "paperwork": ["transfer record", "data wipe certificate", "ledger record"], "review_required": false, "basis": ["V", "M", "P"]},
  {"material": "e_waste_other", "hazardous": false, "regulated": true, "rule_name": "E-Waste (Management) Rules, 2022", "section_ref": null, "handler_requirement": "registered refurbisher, dismantler or recycler", "paperwork": ["transfer record", "ledger record"], "review_required": false, "basis": ["V", "M"]},
  {"material": "battery_lead_acid", "hazardous": true, "regulated": true, "rule_name": "Battery Waste Management Rules, 2022", "section_ref": null, "handler_requirement": "authorized battery recycler or producer take-back", "paperwork": ["transfer record", "ledger record"], "review_required": true, "basis": ["M"]},
  {"material": "battery_lithium", "hazardous": true, "regulated": true, "rule_name": "Battery Waste Management Rules, 2022", "section_ref": null, "handler_requirement": "authorized battery recycler", "paperwork": ["transfer record", "fire risk flag", "ledger record"], "review_required": true, "basis": ["M"]},
  {"material": "used_oil", "hazardous": true, "regulated": true, "rule_name": "Hazardous and Other Wastes (Management and Transboundary Movement) Rules, 2016", "section_ref": null, "handler_requirement": "authorized used oil recycler or re-refiner", "paperwork": ["generator authorization", "manifest", "ledger record"], "review_required": true, "basis": ["V", "M"]},
  {"material": "other", "hazardous": null, "regulated": null, "rule_name": "Unclassified", "section_ref": null, "handler_requirement": "human review", "paperwork": [], "review_required": true, "basis": ["P"]}
]
```
