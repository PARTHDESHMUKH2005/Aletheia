# LoopBack: Build and Development Guide

This guide describes the implementation in this repository. For the project overview, quick start, and AWS deployment notes, see [README.md](README.md). For a request-by-request architecture walkthrough, see [ARCHITECTURE.md](ARCHITECTURE.md).

## What the app does

LoopBack accepts an organization's waste photos, note, approximate quantity, and pickup pincode. The backend characterizes items, looks up the applicable rule record, finds eligible processors, calculates a route, and records stream events in a verifiable hash-chained ledger. Low-confidence or unsupported cases can be sent for human review. It also creates a PDF report and a Waste Passport.

The product is a demo. Processor identities, prices, recovery rates, and some emissions factors are illustrative. Some rule records still need official-source verification; see the basis and source references in `RULES.md`. The app does not certify compliance or confirm that a physical handoff occurred. See [RULES.md](RULES.md) and [docs/DEMO_DATA.md](docs/DEMO_DATA.md).

## Current architecture

- **Frontend:** React and Vite in `frontend/`.
- **API:** FastAPI in `backend/app/main.py`; local development uses Uvicorn.
- **Pipeline:** `backend/app/pipeline.py` runs characterization, deterministic rule and processor lookups, routing, and ledger updates. The Strands agent can coordinate tools, with deterministic guardrails enforced in Python.
- **Models:** `backend/app/config.py` selects Gemini by default, with other configured providers available. Model calls require credentials and model IDs that work for your account.
- **Local storage:** SQLite and local upload files through `backend/app/storage/local.py`.
- **AWS adapters:** DynamoDB and S3 implementations are in `backend/app/storage/aws.py`; Lambda entry points and a SAM template are present. They have not been validated in a live AWS account.
- **Reports:** ReportLab creates PDF reports, which the API serves to authenticated users.

## Local development

Follow the PowerShell quick start in [README.md](README.md). It creates a local virtual environment, installs backend development dependencies, prepares a private backend environment file, generates a local credential, and starts the API and frontend.

The local app expects an authenticated session. Keep `backend/.env` private and set `GEMINI_API_KEY` and model IDs that are available to your account before making live model calls.

## Repository map

- `backend/app/`: API, authentication, schemas, pipeline, model configuration, storage adapters, and deterministic tools.
- `backend/app/data/`: JSON demo rules, organizations, processors, prices, emissions factors, and postcodes.
- `backend/tests/`: backend unit and integration tests, including local API and mocked AWS adapter coverage.
- `frontend/src/`: app pages, components, session handling, and API client.
- `frontend/tests/`: frontend API and handoff tests.
- `eval/`: labeled photos, labels, and the model evaluation harness.
- `infra/`: SAM template, deployment configuration, and a sample pipeline event.
- `scripts/`: local demo and credential/model helper scripts.

## Current constraints and data readiness

- The API accepts up to four photos per stream; the upload page supports up to four.
- Demo processors are fictional and have no checked authorization references. Hazardous and e-waste routing is therefore restricted by the guardrails.
- Rule rows are marked with their verification basis; none is fully source-verified yet.
- The evaluation set currently covers cardboard, paper, and a broad metal-scrap family. It does not validate hazardous or storage-device classification, and no evaluation output is checked in.
- Some emission factors are illustrative. Dataset licensing and attribution should be confirmed before broader distribution.
- The frontend uses public map tiles and routing services; review their availability and usage terms before production use.

## Local validation

From the repository root:

```powershell
Set-Location backend
..\.venv\Scripts\python -m pytest -q
Set-Location ..\frontend
npm test
npm run build
```

The vision evaluation makes live model calls and requires a working provider configuration:

```powershell
# Run from the repository root.
.\.venv\Scripts\python eval/run_eval.py
```

Record the evaluation output before using it to support accuracy or confidence claims. Expand the labeled set to include e-waste, batteries, used oil, and hazard/storage-device flags before treating it as a broad waste-classification evaluation.

## Work to complete before AWS deployment

1. Run the backend tests, frontend tests, and frontend production build locally.
2. Run the vision evaluation with an available model account, save the result, and expand its labels and checks.
3. Verify rule text and amendments against official sources; record citations and review dates.
4. Replace or clearly retain demo-only processor data; verify authorization references and dates for any real routing.
5. Confirm dataset licenses and attribution, and keep demo assumptions visible in the UI and reports.
6. Review the local authenticated upload-to-result, routing, review, handoff, and PDF flows.

AWS deployment is a separate phase. The SAM template and AWS adapters are implementation artifacts, not evidence of a successful live deployment.
