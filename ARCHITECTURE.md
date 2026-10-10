# LoopBack: how the code works (in plain words)

This file explains the whole project so you do not need to ask anyone. Read it top to bottom once, then use the file list in section 4 as a map.

Facts here were checked against the code on 2026-10-10. Where something is only a placeholder, it says so.

---

## 1. What the app does

A person has some waste (a steel can, old paper, a laptop). They:

1. Upload a photo, and type their **pincode** (and optionally the weight).
2. The app asks an AI model (Gemini) **what the waste is**.
3. The app finds the **best buyer** nearby, using a slider: "more money" ... "less carbon".
4. It shows a **receipt**: how much money and CO2 saved, compared with just throwing it away.
5. It writes the choice into a **tamper-proof log** (the ledger).

**Important:** the buyers, most prices, and the recovery numbers are **made-up demo data**. Nothing here is a real business or a real quote. Nobody is ever contacted. See section 9.

---

## 2. The journey of one request (follow one photo from start to end)

```
Browser  --1-->  POST /uploads        get a key + upload address
Browser  --2-->  PUT  /local-uploads  send the photo bytes
Browser  --3-->  POST /streams        send org, pincode, weight, note, photo key
                      |  (checks the org exists and the pincode is in our table)
                      |  (saves a "stream" with status SUBMITTED)
                      |  (starts the pipeline in the background)
                      v
              run_pipeline()   <-- backend/app/pipeline.py
                1. look up the pincode  -> latitude/longitude
                2. status = CHARACTERIZING
                3. ask Gemini what the waste is  (tools/characterize.py)
                4. for each item found:
                     - refuse it if it is out of scope (medical, explosive...)
                     - flag it for human review if unsure or hazardous
                     - find the best buyer          (tools/matching.py)
                     - build the receipt            (tools/report.py)
                     - write a ledger entry         (tools/ledger.py)
                5. status = ROUTED  (or NEEDS_REVIEW, or FAILED)
Browser  --4-->  GET /streams/{id}    asked every 2 seconds ("polling") until
                                      the status changes
Browser  --5-->  GET /streams/{id}/route?w=0.7   move the slider -> new pick
```

**Statuses a stream can have**

| Status | Meaning |
|---|---|
| SUBMITTED | saved, waiting for the background job |
| CHARACTERIZING | the AI is looking at the photo (can take ~30-40 seconds the first time) |
| ROUTED | a buyer was picked, receipt ready |
| NEEDS_REVIEW | done, but a human should check (low confidence, hazardous, or refused) |
| FAILED | something went wrong; the reason is in the stream's `error` field |

**Why "polling"?** The AI call is slow, so the server answers "accepted" straight away and works in the background. The page just keeps asking "done yet?".

---

## 3. How the important parts work

### 3.1 Pincode -> location
- File `backend/app/data/pincodes_demo.json` is a small table: pincode -> city + latitude/longitude.
- The coordinates are **approximate area centres typed in by hand** (a few km of error). They were not taken from India Post.
- There is **no online geocoder**. If a pincode is not in the table, the app says `Pincode not in demo data` and lists the ones that work.
- Valid demo pincodes: 147001, 147004 (Patiala), 141001 (Ludhiana), 160017 (Chandigarh), 133001 (Ambala), 143001 (Amritsar), 144001 (Jalandhar), 110001 (Delhi), 122001 (Gurugram), 147301 (Mandi Gobindgarh), plus 400001 (Mumbai) and 132103 (Panipat), which are only there because demo buyers sit in those cities.
- Code: `backend/app/tools/geo.py`.

### 3.2 Asking the AI (characterize)
- `tools/characterize.py` sends the photo(s) to Gemini through a library called Strands.
- The AI must answer in a fixed shape (the `Item` model in `models.py`): material, weight, how pure, hazardous or not, confidence, and so on.
- It tries a cheap model first. If confidence is under 0.7, it tries the stronger model once. It never loops.
- **Cache:** the answer is saved, keyed by a fingerprint of the photo, so the same photo is instant the second time. **Known bug:** the key ignores the weight and note you typed (see section 8).
- This is the **only** place an AI model is used. It is one call, not an "agent" that makes decisions.

### 3.3 Finding the best buyer (matching)
File: `tools/matching.py`. For one item and one pickup point:

1. **Candidates:** all demo buyers that accept this material.
2. **Distance:** straight-line distance (haversine) from pickup to buyer. If a location is missing or invalid, it **raises an error** (it never quietly uses 0 km).
3. **Distance cap:** buyers farther than 500 km are not ranked (change with the `MAX_DISTANCE_KM` setting).
4. **Money per kg** = buyer's price - transport cost.
   **Carbon per kg** = (CO2 saved by recycling x the buyer's recovery rate) - transport CO2.
5. **Scores (0 to 1):** each buyer's money and carbon are divided by the best available for that material. So 0.9 means "90% as good as the best".
6. **"Close enough" rule:** if buyers are within 2% of each other on money (or on carbon), that measure is treated as equal.
7. **The slider `w`:** `score = (1 - w) x money score + w x carbon score`. `w = 0` means only money, `w = 1` means only carbon.
8. **Ties:** nearer buyer wins, then alphabetical name. The explanation says so.
9. **Not scored:** buyers with no price, no CO2 number, failing the hazardous-waste check, or beyond the cap are listed separately with the reason.
10. **Reuse first:** a working laptop is recommended for reuse/donation before recycling, whatever the slider says.

**Worked example** (steel, 100 kg, pickup Patiala):

| Buyer | Money score | Carbon score | Score at w=0.5 | Score at w=1 |
|---|---|---|---|---|
| Mandi Gobindgarh foundry (37 km) | 1.00 | 0.94 | 0.969 | 0.937 |
| Ludhiana steel mill (80 km) | 0.91 | 1.00 | 0.957 | 1.000 |

At w=0.5 the foundry wins (cheaper). Around w=0.6 it flips and the Ludhiana mill wins (more CO2 saved).

### 3.4 The receipt
`tools/report.py` compares "throw it away" (₹0, 0 kg CO2e) with the chosen buyer: money earned, CO2 saved, the difference. It also shows the CO2 number's source and whether it is **verified**. If a number is only an estimate, it is labelled "unverified estimate".

### 3.5 Safety rules (guardrails)
`tools/guardrails.py` and `tools/rules.py`. In plain words:
- Hazardous items (batteries, used oil, mixed metal, e-waste) always go to **human review**.
- A hazardous item can only go to a buyer with a recorded authorization reference **and** check date. Right now **no demo buyer has one**, so such items never get a route. This is intentional.
- Medical waste, explosives, radioactive and biological waste are **refused**, not routed.
- A storage device (hard drive) cannot move past "requested" until a data wipe is confirmed. This is our own policy, not a law.
- The app must never say "compliant", "approved" or "certified", and never calls a demo buyer "authorized". Buyers without a reference show: **"demo only, authorization not checked"**.
- `rules.py` looks up the written waste rule for a material from `rules.json` (which comes from `RULES.md`).

### 3.6 The ledger (the tamper-proof log)
`tools/ledger.py`. Every important step adds a row. Each row stores a fingerprint (hash) made from **the previous row's fingerprint + its own content + time**. If anyone edits an old row, its fingerprint no longer matches and everything after it breaks.
- `GET /verify/{stream_id}` re-checks the whole chain: `ok: true` or the first broken link.
- `POST /dev/tamper/{id}` deliberately corrupts a row so you can demo "it turns red". It is switched off when `ENV=production`.
- This is a learning/demo tool, not a legal record.

---

## 4. Every file, one by one

### Top level
| File / folder | What it is |
|---|---|
| `README.md` | Short intro: demo-data warnings, pincode note, scoring summary, how to run tests. |
| `ARCHITECTURE.md` | This file. |
| `BUILD.md` | The original build plan: phases, API design, prompts. Treat it as the "what we meant to build" document. |
| `RULES.md` | Reference notes on Indian waste rules; the source for `rules.json`. Must not be quoted as legal advice. |
| `.env` | Secrets and settings (for example `GEMINI_API_KEY`). **Never commit it or paste it anywhere.** |
| `dataset-resized/` | Sample photos by category (cardboard, glass, metal, paper, plastic, trash) plus `Raw Material Prices December 2024.pdf` (BigMint prices used for the real steel/copper prices). |
| `.local_data/`, `backend/.local_data/` | Local SQLite databases and uploaded photos created while running. Delete them to reset. They hold old test data, so dashboard totals can look large. |
| `.venv/` | The Python environment with the project's dependencies. |

### `backend/` (the server)
| File | What it does |
|---|---|
| `requirements.txt` | Python libraries needed. |
| `pytest.ini` | Test settings. |
| `app/main.py` | The web API (FastAPI). All the URLs. Also serves the demo page at `/demo/`. |
| `app/pipeline.py` | `run_pipeline()`: the step-by-step job in section 2. |
| `app/models.py` | The data shapes: `Item` (what the AI returns), request/response shapes, the candidate and receipt shapes. |
| `app/config.py` | Reads settings (which AI provider, local vs AWS storage, dev tools on/off). Creates the AI model and storage objects. |
| `app/agent.py` | **Empty placeholder.** The planned "orchestrator agent" is not built. |
| `app/lambda_api.py`, `app/lambda_pipeline.py` | **Empty placeholders** for running on AWS Lambda later. |
| `app/tools/characterize.py` | Photo -> structured description via Gemini, with caching. |
| `app/tools/geo.py` | Pincode lookup and coordinate checks. Defines the location errors. |
| `app/tools/matching.py` | Finds and ranks buyers (section 3.3). Also holds `haversine_km`. |
| `app/tools/report.py` | Receipt, CO2 factor lookup, price range, dashboard totals. |
| `app/tools/guardrails.py` | Safety rules and the authorization label (section 3.5). |
| `app/tools/rules.py` | Looks up the written rule for a material. |
| `app/tools/ledger.py` | The hash-chained log (section 3.6) and `record_handoff`. |
| `app/storage/base.py` | The list of things any storage must do (so local and AWS are interchangeable). |
| `app/storage/local.py` | Storage using a SQLite file and the disk. **This is what runs today.** |
| `app/storage/aws.py` | **Placeholder.** Raises "not implemented". |
| `app/data/processors.json` | The 18 **made-up** buyers: location, pincode, materials, price, recovery rate. |
| `app/data/pincodes_demo.json` | Pincode -> approximate coordinates. |
| `app/data/orgs.json` | 3 demo organizations (campus workshop, campus lab, data center). Used for identity and the dashboard, not for location. |
| `app/data/prices.json` | 5 real BigMint price quotes (steel, copper), each checked against the PDF. |
| `app/data/emission_factors.json` | CO2 saved per kg by material (US EPA numbers used as a stand-in). Paper and cardboard are **unverified guesses**. |
| `app/data/rules.json` | One rule row per material (handler, paperwork, needs review or not). |
| `tests/` | Automatic tests, one file per area. `test_location_and_scoring.py` covers pincodes, distance, scoring, cap, labels. |

### `scripts/`, `eval/`, `frontend/`, `infra/`
| File | What it does |
|---|---|
| `scripts/run_demo.py` | One-command demo: runs a photo through the pipeline, moves the slider, verifies the ledger, tampers a row, verifies again. Uses a real Gemini call. |
| `scripts/hello_agent.py` | Early smoke test that the AI connection works. |
| `scripts/seed.py` | Placeholder for creating sample data. |
| `eval/run_eval.py`, `eval/labels.csv`, `eval/test_photos/` | Measures how often the AI labels photos correctly. |
| `frontend/demo/index.html` | A simple single-page demo (form, result, slider, ledger check). Served at `/demo/`. It does not yet show API errors (see section 8). |
| `frontend/src/pages/*.jsx` | Five **empty placeholder** pages for the planned real interface. |
| `infra/template.yaml`, `samconfig.toml`, `events/pipeline.json` | AWS deployment files. Each is a single stub line today. |

---

## 5. The API (URLs)

| Method and URL | Purpose |
|---|---|
| `POST /uploads` | Get an upload key/address. |
| `PUT /local-uploads/{key}` | Upload the photo bytes (local stand-in for S3). |
| `POST /streams` | Start a job. Needs `org_id`, `photo_keys`, and a valid `pincode`. Optional `quantity_kg`, `note`. Returns `stream_id`. Errors: 404 unknown org, 422 bad pincode. |
| `GET /streams/{id}` | Status, characterization, routing, receipts, ledger, and `error` if failed. |
| `GET /streams/{id}/route?w=0.5&item_index=0` | Re-rank buyers at slider value `w` (0-1). |
| `POST /streams/{id}/draft-message?processor_id=...` | Writes a draft pickup message and logs it. **Never sends anything.** |
| `POST /streams/{id}/wipe` | Marks a data wipe as done (simulated certificate). |
| `GET /streams/{id}/report` | Receipt data as JSON (PDF export not built). |
| `GET /orgs/{org_id}/dashboard` | Totals for an org: kg per route type, CO2 avoided. |
| `GET /processors` | The demo buyers, with their authorization label. |
| `GET /verify/{id}` | Checks the ledger chain. |
| `POST /dev/tamper/{id}` | Demo only: corrupts a ledger row. |

---

## 6. How to run it

Run these from the project folder. The Python environment is `.venv`.

```bash
# start the server (loads GEMINI_API_KEY from .env)
cd backend
set -a && . ../.env && set +a
../.venv/bin/python -m uvicorn app.main:app --port 8000
# open http://localhost:8000/demo/

# run the tests (the env var avoids a broken unrelated plugin)
cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ../.venv/bin/python -m pytest

# command-line demo
cd backend && set -a && . ../.env && set +a && ../.venv/bin/python ../scripts/run_demo.py
```

Restart the server after changing any `data/*.json` file. They are read once at startup.

Settings (environment variables): `GEMINI_API_KEY`, `LLM_PROVIDER` (gemini, bedrock or qwen), `STORAGE` (local or aws), `ENV` (production turns dev tools off), `MAX_DISTANCE_KM` (default 500), `FRONTEND_ORIGIN` (allowed web origins).

---

## 7. Where to change things

| I want to... | Edit |
|---|---|
| Add a demo pincode | `data/pincodes_demo.json` |
| Add or change a buyer | `data/processors.json` (include a `pincode` that exists in the table) |
| Change how much transport matters | the two constants at the top of `tools/matching.py` |
| Change the 2% rule or the default cap | `EQUAL_SPREAD_THRESHOLD` / `DEFAULT_MAX_DISTANCE_KM` in `tools/matching.py` |
| Add a CO2 number | `data/emission_factors.json` (set `verified: true` only with a real citation) |
| Change what the AI is asked | `_build_prompt` in `tools/characterize.py` |
| Add a safety rule | `tools/guardrails.py` (and add a test) |
| Add an API URL | `app/main.py` |

---

## 8. Known bugs and gaps (to fix)

Confirmed by running the code:

1. **Missing weight gives silent zeros.** If nobody types a weight and the AI returns none, the item counts as 0 kg, so the receipt shows ₹0 and 0 kg CO2e with no warning.
2. **The photo cache ignores weight and note.** Same photo again returns the old answer (typing 100 kg returned 0.3 kg).
3. **The demo page hides errors.** A rejected pincode (HTTP 422) or a FAILED stream is not shown; it can sit on "polling...". It also does not show "characterizing" while the slow AI call runs.
4. **One test fails:** `test_main.py::test_draft_message_is_never_sent_and_is_recorded`. The test blocks the same HTTP client the test uses, so it breaks itself.

Suspected, needs checking:

5. Photos with several items: routing and the page mostly handle only the first item.
6. A job that crashes mid-way can leave a stream stuck in CHARACTERIZING with no retry.
7. Dashboard totals count old test data and NEEDS_REVIEW streams.
8. There is no check that the AI's material guess makes sense beyond its own confidence.

Not built yet:

9. The orchestrator agent (`agent.py`), the real frontend pages, PDF export, AWS storage and Lambda handlers, and the infra files.

---

## 9. What is real and what is made up

| Thing | Status |
|---|---|
| Buyers (all 18) | **Made up.** Names, places, everything. |
| Steel and copper prices (5 numbers) | **Real** BigMint city quotes, Dec 2024, checked against the PDF. They are wholesale benchmarks, not quotes from the demo buyers. |
| Other prices (aluminium, paper, cardboard, e-waste, the Ludhiana steel mill, reuse centre) | **Illustrative guesses**, marked `illustrative_assumption`. |
| Recovery rates (0.85-0.95 for recyclers) | **Illustrative guesses**, not measured. |
| Transport cost (₹3 per tonne-km) and transport CO2 (0.062 kg per tonne-km) | **Unsourced assumptions.** |
| CO2 saved: metals and e-waste | US EPA WARM values used as a stand-in (not India-specific). |
| CO2 saved: paper and cardboard | **Unverified estimates.** Need a real citation. |
| CO2 saved: batteries, used oil, mixed metal, storage drives, "other" | **None.** Not invented. |
| Pincode coordinates | **Approximate** area centres, typed by hand. |
| Authorization of buyers | **Not checked for any buyer.** |
| Pickup message | A template only. **Nothing is sent to anyone.** |
| Distances | Straight-line, not road distance. |

If you present any number from this app, say it is a demo.

---

## 10. Rules for working on this project

- Do not invent numbers. If a value is a guess, mark it `illustrative_assumption` and list it in `README.md`.
- Every bug fix needs a test.
- Never print the word "authorized" for a buyer that has no authorization reference.
- Never call an external geocoder. Unknown pincode = clear error.
- Never treat missing coordinates as 0 km.
- Never commit `.env` or any API key.
