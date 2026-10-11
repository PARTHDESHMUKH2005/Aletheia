# LoopBack architecture

Checked against the code on 2026-10-11. LoopBack is a waste-routing demo with React, FastAPI, model-based photo characterization, deterministic buyer matching, per-item handoff records and PDF passports. Buyers, most prices and recovery rates are illustrative; see [demo data](docs/DEMO_DATA.md).

## Request flow

1. A bearer credential identifies an operator, reviewer or administrator and its allowed organizations. `GET /session` supplies that identity and the organization selector. Private endpoints enforce scope independently of the browser.
2. `POST /uploads` receives `org_id`, a count of 1–4 and resized image sizes. Keys are organization-prefixed and accept one upload. Local storage publishes complete files atomically; S3 URLs sign an `If-None-Match: *` condition that the browser sends. A replacement photo requires a new target. The browser resizes images to JPEG and uploads to an authenticated local URL or a short-lived S3 PUT URL, without sending its API credential to S3.
3. `POST /streams` validates the organization, supported pincode, positive finite weight if supplied, and actual image contents. Photos are limited to 5 MiB and 16 million pixels each. It stores `SUBMITTED`, dispatches processing and returns 202.
4. `run_pipeline()` records `CHARACTERIZING`, characterizes all photos together and computes routes, receipts and assessments for every item. Out-of-scope material is refused. Low confidence, hazardous items, missing buyers and empty results become `NEEDS_REVIEW`; usable results become `ROUTED`. Exceptions record `FAILED`.
5. The frontend polls until processing finishes. Moving a slider previews a route. `PUT /streams/{id}/route` saves that item's choice, receipt and ledger event. Pickup drafts and handoffs validate against the saved buyer. Routing locks after physical handoff begins.
6. A reviewer can reclassify one item while retaining its model confidence. Correction replaces the old hazard/storage flags with those required by the new material and any flags the reviewer explicitly supplies (for contamination or installed storage). The review form resets flags when the material changes and exposes both for correction; batteries/oil and storage drives retain mandatory flags. This keeps the stream in review. Confirmation is separate and requires eligible buyers for all items; it cannot bypass a refusal or missing hazardous-handler authorization.
7. Handoff events include `item_index` and optional measured weight. Dashboard totals derive each item's progress independently. Storage devices need recorded wipe details; an e-waste batch needs records for every installed drive. Reviewer-entered records are not independently certified by LoopBack.

## Main modules

| File | Responsibility |
|---|---|
| `backend/app/main.py` | API validation, review, saved routes, handoff, dashboards, PDFs and public verification |
| `backend/app/auth.py` | Credentials, organization scope and reviewer/admin permissions |
| `backend/app/uploads.py` | Shared file-key, image and size validation |
| `backend/app/models.py` | Typed schemas, bounded confidence, finite positive quantities and material flags |
| `backend/app/pipeline.py` | Deterministic processing and persisted results; optional agent summary afterward |
| `backend/app/agent.py` | Strands tools and optional orchestrator; tools reuse deterministic results |
| `backend/app/worker.py` | Local background tasks or asynchronous Lambda dispatch |
| `backend/app/lambda_api.py` | Mangum adapter for FastAPI |
| `backend/app/lambda_pipeline.py` | Worker handler with time reserved to persist failures |
| `backend/app/config.py` | Environment settings, model factories and storage selection |
| `backend/app/tools/characterize.py` | Vision call, one stronger-model escalation, versioned prompt-input cache |
| `backend/app/tools/matching.py` | Material/authorization filters, distance cap, scoring and reuse preference |
| `backend/app/tools/assessment.py` | Confidence band, contaminants, review reasons and next action |
| `backend/app/tools/guardrails.py`, `rules.py` | Scope refusals, review/wipe policies and material-specific rule lookup |
| `backend/app/tools/ewaste.py` | Device registry, installed drives and entered wipe records |
| `backend/app/tools/ledger.py` | Canonical format-2 hashes, append collision handling and verification |
| `backend/app/tools/report.py` | Receipts, per-item impact aggregation, provenance and PDF rendering |
| `backend/app/storage/local.py` | SQLite records/cache/ledger and constrained local upload paths |
| `backend/app/storage/aws.py` | DynamoDB records/cache/ledger, organization index and private S3 uploads |
| `frontend/src/components/Session.jsx` | Credential entry, scoped session and sign-out; public verification |
| `frontend/src/pages/` | Upload, result, review, passport, dashboard, maps and verification |
| `frontend/demo/index.html` | Minimal authenticated same-origin demo |
| `infra/template.yaml`, `backend/Makefile` | SAM resources and application-only Lambda packaging |
| `backend/tests/`, `frontend/tests/` | Isolated regressions, emulated AWS and browser API-contract checks |
| `eval/` | Separate labelled-photo evaluation harness, outside offline unit tests |

## Characterization and matching

The characterizer requests structured output from the configured provider. A fast-tier token-limit failure or low overall confidence can trigger the strong tier once. Cache keys include photo formats, boundaries and bytes, submitter note and quantity, provider, model IDs and cache version. Old image-only cache records cannot match. Model confidence remains self-reported and uncalibrated.

Locations come from `data/pincodes_demo.json`, without online geocoding. Missing coordinates raise an error. Buyers beyond the distance cap (500 km by default) are excluded. Distances are straight-line estimates.

Scoring combines normalized net money and net CO₂e using the slider, with optional authorization-evidence weighting. Transport factors come from `data/scoring_config.json`. A spread under 2% is treated as equal; ties use distance then name. Missing prices/factors are unscored. Working equipment prefers eligible nearby reuse destinations; receipts and handoffs use the same choice.

Batteries and used oil are always hazardous even if the model says otherwise. Hazardous material and e-waste recycling need a handler authorization reference and check date. Demo buyers lack checked authorization, so a reviewer cannot approve those routes. Medical, biological, radioactive and explosive material remains refused. The software provides a routing aid, not a compliance certification.

The rule table uses the Solid Waste Management Rules, 2026 for dry waste. Aluminium and copper streams require review because the Hazardous and Other Wastes Rules amendment of 2025 adds conditional EPR duties for specified non-ferrous products, and the app does not capture enough information to establish that scope. Other rule rows still carry unverified basis labels; see [RULES.md](RULES.md).

Receipts identify factor sources and historical price benchmarks. Missing weight produces an explicit notice and unavailable money/carbon totals. Dashboards separate projected totals from verified handoffs, use each item's measured weight where present, and list missing documents. Handoffs advance strictly forward per item through requested, matched, collected, weighed and verified; forward jumps remain possible, with missing documents reported. Duplicate/backward steps return a conflict, and verification finalizes the weight. Transition guards run against the chain being extended and recheck after concurrent insert collisions. For older histories containing duplicate verification, the dashboard retains the first verified weight. Rejected and unreviewed streams receive no projected credit. Legacy handoff entries without item identity apply only to single-item streams.

## Ledger and old data

Each format-2 hash covers chain ID, link number, event, timestamp, canonical payload, previous hash and format version. Verification checks sequence, identity and every digest. Empty or unknown records never verify successfully. Mutations on damaged or legacy chains are refused.

SQLite migration labels old entries as format 1 without rewriting hashes. They remain readable and exportable, but unverified. Re-submit photos for a new record rather than asserting old history was intact. Old unscoped uploads are not served through private organization routes.

There is no independently published ledger head or trusted external anchor. A database owner can replace a whole chain or remove its tail. A passing check verifies retained contents; it does not prove a real pickup, weight or certificate. The tamper demo requires a scoped administrator and is disabled in production.

## API map

Routes require an organization-scoped credential unless marked public. Review and wipe writes require reviewer/admin; the tamper tool requires admin.

| API | Purpose |
|---|---|
| `GET /session` | Identity and accessible organizations |
| `POST /uploads`, `PUT/GET /local-uploads/{org}/{key}` | Upload targets and private photo bytes |
| `POST /streams`, `GET /streams/{id}` | Submit and retrieve processing/results/ledger |
| `GET/PUT /streams/{id}/route` | Preview/save one item's route and receipt |
| `POST /streams/{id}/draft-message` | Saved-buyer pickup draft; never sends messages |
| `GET /review-queue`, `POST /streams/{id}/review` | Scoped queue and confirm/reclassify/reject decisions |
| `POST /streams/{id}/handoff` | Per-item matched/collected/weighed/verified records |
| `POST /streams/{id}/wipe` | Per-item wipe method, certificate reference and operator |
| `POST/GET /streams/{id}/ewaste` | Device batch registration/status |
| `POST /streams/{id}/ewaste/drives/{drive_id}/wipe` | Per-drive wipe record |
| `GET /streams/{id}/report` | PDF attachment; `?format=json` retains a JSON summary |
| `GET /orgs/{org_id}/dashboard` | Scoped impact and outstanding actions |
| `GET /processors`, `GET /scoring-config` | Public demo/reference data |
| `GET /verify/{id}` | Public integrity result without private contents |
| `POST /dev/tamper/{id}` | Scoped local demo corruption |

## Running and deploying

Use the [README quick start](README.md#-quick-start). Settings load from `backend/.env`, then the root `.env`, without replacing process environment values. Variables include `API_TOKENS_JSON`, `STORAGE`, `ENV`, provider credentials/model IDs, `USE_AGENT`, `MAX_DISTANCE_KM` and `FRONTEND_ORIGIN`. Restart after changing settings or static data.

Local records live under ignored `backend/.local_data/`. Tests use temporary databases. Cloud storage uses SAM table/bucket names, a seven-day cache TTL, conditional stream revisions and unique ledger inserts. The HTTP API invokes the worker asynchronously. The worker has a 180-second limit and reserves five seconds for timeout handling. Production disables the tamper endpoint, S3 objects are private, and photos expire after 14 days. Build targets copy only application code and dependencies, excluding secrets and local records.

Offline tests use Moto/Stubber and validate SAM transformation. Live model accuracy, provider model availability and a real AWS deployment require separate validation. Qwen defaults are explicitly unverified. `BUILD.md` is the local development guide; this file describes the implementation.
