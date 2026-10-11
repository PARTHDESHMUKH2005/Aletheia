<div align="center">

# ♻️ LoopBack

### Snap a photo of waste. Compare buyers, projected money and CO₂ savings, with a verifiable record.

*An AI agent that turns waste into a routed, auditable, carbon-aware transaction.*

**WeMakeDevs × AWS Hackathon · Waste & Energy track**

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![Gemini](https://img.shields.io/badge/Gemini-vision-4285F4?logo=googlegemini&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-SAM%20template-FF9900?logo=amazonaws&logoColor=white)

</div>

> **Transparency note.** Buyers, most prices and recovery rates in this repo are **illustrative demo data**. Nothing is a verified real business or a live quote, and nobody is contacted. See [`docs/DEMO_DATA.md`](docs/DEMO_DATA.md) for exactly what is sourced and what is assumed.

---

## 🔥 The problem

Waste generators often lack a clear material inventory, current handler information and a traceable record of where each stream went.

- **Nobody knows what they hold.** A workshop, lab or data center sees "junk". Is it steel, aluminium, e-waste or used oil? The material and contamination affect which handling rules and destinations may apply.
- **Nobody knows who to call.** Scrap goes to whichever dealer is nearest, at whatever price they offer.
- **Nobody can prove where it went.** Applicable waste rules can impose registration, handling and record-keeping duties. Exact obligations depend on the material and generator; see [`RULES.md`](RULES.md). Records are often scattered and difficult to verify.

## The pain

| Who | What hurts |
|---|---|
| **Organizations** (campuses, labs, data centers) | Manual sorting, no price discovery, compliance risk if hazardous items go to the wrong handler |
| **Recyclers and processors** | Mixed, unlabelled, unquantified material and no trusted trail |
| **The planet** | Recoverable material gets landfilled or burned, and its CO₂ benefit is lost |

Money and carbon are also treated as separate questions. The highest bidder may be 400 km away, and the trucking cancels the climate gain.

## 💡 The solution

**LoopBack** is an agent that handles the whole journey from a photo to a proof of handoff:

1.  **Characterize.** Gemini vision identifies the material, purity, hazard flag and a confidence score from a photo.
2.  **Apply the rules.** It looks up the app's rule record for the material and the handler requirements to check.
3.  **Route with a slider.** One control runs from *more money* to *less carbon*. Buyers are ranked by net ₹/kg and net CO₂e/kg, with transport cost and emissions included.
4.  **Show the receipt.** It reports money earned and CO₂e avoided against the throw-it-away baseline.
5.  **Record it.** Every handoff goes into a SHA-256 hash-chained ledger that anyone can re-verify. The result is a shareable **Waste Passport**.
6.  **Keep a human in the loop.** Low-confidence, hazardous or out-of-scope items go to a review queue instead of being auto-routed.

```
 Photo + pincode ──► Gemini characterizes ──► Rules + guardrails ──► Carbon-aware matching
                                                                          │
        Waste Passport ◄── Hash-chained ledger ◄── Receipt (₹ + CO₂e) ◄───┘
```

## 🏆 Why we stand out

- **Carbon and money in one decision.** The slider includes transport cost and emissions assumptions, making the trade-off visible. Demo factors are illustrative; see [`docs/DEMO_DATA.md`](docs/DEMO_DATA.md).
- **Tamper-evident by design.** Each ledger entry hashes the previous one, so editing history breaks the chain and `/verify` shows it.
- **Compliance-aware, not just clever.** Hazardous and unsure cases are refused or sent to human review. The agent knows what it should not do.
- **Honest about its numbers.** Every figure is labelled *sourced* or *illustrative assumption*. We never present demo data as real.
- **Test coverage.** Backend tests cover scoring, location, the agent and the API. An `eval/` harness can measure characterization against labelled photos; evaluation results have not yet been recorded.
- **End to end.** It has a working API, an agent pipeline, a review queue, an e-waste workflow, an impact dashboard, a map and a public ledger verifier.

## 🌍 Impact

Every routed item produces a receipt showing:

- **kg diverted** from disposal
- **₹ earned** at the best matched buyer, net of transport
- **CO₂e avoided** versus landfill, net of transport emissions
- **Compliance status** and a verifiable passport

The **Impact Dashboard** aggregates this across an organization's streams. The long-term goal is to make recovery the easiest option for anyone holding waste.

## 🛠️ Tech stack

| Layer | Technology |
|---|---|
| **AI / Agent** | Gemini (vision characterization), Strands Agents |
| **Backend** | Python, FastAPI, Pydantic, Uvicorn |
| **Cloud** | AWS Lambda via Mangum, asynchronous worker, DynamoDB, private S3 and SAM |
| **Frontend** | React 18, Vite, Tailwind CSS, React Router, Leaflet maps |
| **Integrity** | SHA-256 hash-chained ledger |
| **Reports** | ReportLab (PDF) |
| **Testing** | pytest, plus a photo-based eval harness |

## 🚀 Quick start

PowerShell, from the repository root (Python 3.11+ and Node 20+):

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install -r backend/requirements-dev.txt
Copy-Item backend/.env.example backend/.env
# Generates a random local administrator credential. Keep this file private.
.\.venv\Scripts\python scripts/create_credentials.py --env-assignment | Add-Content backend/.env
# Set GEMINI_API_KEY and your account's model IDs in backend/.env.
Set-Location backend
..\.venv\Scripts\python -m uvicorn app.main:app --reload
```

In a second PowerShell window:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Open the Vite URL and sign in using the `token` value from `API_TOKENS_JSON` in `backend/.env`. Upload one to four photos with a demo pincode such as `147001` (Patiala) or `110001` (Delhi). The same-origin demo at `http://localhost:8000/demo/` also accepts this credential. Sliding previews a route; **Save routing choice** persists it for pickup, passports and dashboards.

`API_TOKENS_JSON` is a JSON array of `{token, subject, role, org_ids}` entries. `operator` can submit and record handoffs; `reviewer` can also review and record wipe certificates; `admin` can also use the local tamper demo. Each role is restricted to its listed organizations. The generator supports `--role`, `--subject` and repeated `--org` options. A missing or malformed credential configuration denies private access. Only processor/scoring data and ledger verification are public. Browser credentials stay in the current tab's session; never embed them in a frontend build.

```powershell
Set-Location backend
..\.venv\Scripts\python -m pytest -q
Set-Location ..\frontend
npm test
npm run build
```

Tests isolate SQLite data and mock AI/AWS calls. AWS storage tests use Moto; the SAM template is transformed offline. A deployed AWS account and live AI model have not been exercised by those tests.

### AWS setup

`infra/template.yaml` defines an HTTP API, two Lambda functions, DynamoDB tables and a private S3 upload bucket. From `infra/`, run `sam build --use-container` and then `sam deploy --guided`; supply `GeminiApiKey`, `ApiTokensJson`, `FrontendOrigin` and model IDs. The custom build copies only application code and runtime dependencies, excluding `.env`, test data and local uploads. Deploying creates billable resources. Set `VITE_API_URL` to the stack's `ApiUrl` before building the frontend, and configure `FrontendOrigin` to its exact web origin. The worker receives a stream ID asynchronously and preserves time to record a timeout failure. Uploaded cloud photos expire after 14 days.

### Existing local records

New ledger entries use hash format 2, which covers event type, chain identity, link number, time, payload and previous hash. Existing format-1 chains remain unchanged and readable, but show as unverified and cannot accept mutations. Export them for reference and resubmit photos to create a new record; no automatic rehash asserts their integrity. Old unscoped photo keys are private and must be uploaded again under an organization. Hash verification detects edits to retained records; it does not independently verify a handoff or protect against replacement or deletion of an entire chain by a database owner.

Photos are uploaded once per key: a second local PUT returns 409, and cloud PUTs require the signed `If-None-Match: *` header. Request a new upload target for a different photo. Handoff statuses advance strictly forward per item; duplicates and backward steps return 409, and verification finalizes the measured weight. Review reclassification resets obsolete hazard/storage flags, enforces flags required by the corrected material, and accepts explicit `hazardous` and `is_storage_device` flags for contamination or installed storage. It still requires a separate routing confirmation.

## 📚 Documentation

| Doc | What's inside |
|---|---|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Plain-words tour of the code and the life of one request |
| [`BUILD.md`](BUILD.md) | Current implementation, local development and pre-AWS checklist |
| [`RULES.md`](RULES.md) | Indian waste-rules reference behind the compliance logic |
| [`docs/DEMO_DATA.md`](docs/DEMO_DATA.md) | Demo data, scoring formula, sourced versus assumed numbers |

## 👥 Team

| | |
|---|---|
| **Parth Deshmukh** | |
| **Keha Chopra** | |
| **Tarush Mohindru** | |
| **Abhinandan Kumar** | |

---

<div align="center">

*Built for the WeMakeDevs × AWS Hackathon. LoopBack routes and records, and it does not certify compliance.*

</div>
