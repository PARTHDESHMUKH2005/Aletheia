# LoopBack: Build Guide, Scratch to Deployment

WeMakeDevs x AWS hackathon, Waste and Energy track. Keep this file at the repo root as `BUILD.md`. It is the single source of truth for the build.

## 0. How to use this file

- Sections 1 to 8 are the spec: what we build, the architecture, the agent, the ledger, the data, the repo layout.
- Section 9 is the runbook, phase by phase, from an empty folder to a live deployment.
- Section 10 has the prompts to give a coding agent (Claude Code or similar), one phase at a time.
- The order is fixed: build and test the whole agent pipeline locally (Phases 0 to 2), then move the same code to AWS Lambda (Phase 3), then the interface (Phase 4), then submit (Phase 5).
- Anything marked **VERIFY** could not be confirmed from official docs while writing this. Check it before relying on it.

## 1. What is being built

LoopBack is an agent that takes a waste stream from an organization (photos, a short note, an approximate quantity) and does five things:

1. Characterizes it: material, purity, quantity, hazardous or not, confidence.
2. Looks up the Indian rule that applies and who may legally handle it.
3. Routes it by the waste hierarchy: reuse, then repair or refurbish, then recycle, then recovery, disposal last. Hazardous items go only to authorized processors.
4. Records every handoff in a hash-chained ledger that anyone can re-verify.
5. Produces a report: kg diverted, CO2e avoided, compliance status.

Build scope (anything outside this is roadmap):

- Waste types: metal scrap, e-waste (computers, storage drives, batteries), paper, and one hazardous liquid (used oil) to show the compliance logic.
- Processors: 6 to 8, seeded from the CPCB authorized list, local foundries, refurbishers and paper recyclers. All labelled `seeded: true`.
- Organizations: three sample ones (campus workshop, campus lab, a data center).
- Handoffs are simulated. Nothing is presented as a real pilot unless it happened.

## 2. Architecture and API contract

```
LOCAL (Phases 0 to 2)                    AWS (Phase 3)
React app (Vite dev server)              React app on Amplify Hosting
   |                                        |
FastAPI (uvicorn)                        API Gateway HTTP API
   |                                        |
   |                                     api Lambda (same FastAPI app via Mangum)
   | BackgroundTasks                        | async invoke (InvocationType=Event)
run_pipeline(stream_id)  <== same code ==>  pipeline Lambda -> run_pipeline(stream_id)
   |                                        |
Strands orchestrator Agent               Strands orchestrator Agent -> Qwen API
   | tools = plain Python                   | tools = the same Python files
SQLite + local disk                      DynamoDB + S3
```

### Portability rules (so the same code runs locally and on Lambda)

1. **One place reads the environment:** `config.py`. Nothing else touches `os.environ`.
2. **Adapters behind interfaces.** `Storage` (local, aws), `VisionClient` (qwen now, bedrock later if wanted) and the orchestrator model builder. The pipeline and the tools import interfaces only.
3. **Stateless.** Stream status, results and the ledger live in the store, never in process memory or local disk. On Lambda the only writable path is `/tmp` (512 MB by default), so reports are built in `/tmp` and then saved through `Storage`.
4. **Thin entry points.** FastAPI routes and Lambda handlers only parse input and call `run_pipeline` or a service function.
5. **Time-boxed.** `run_pipeline(stream_id, time_budget_ms)` stops cleanly before the limit and marks the stream `FAILED` with a retryable flag. Locally the budget comes from config. On Lambda it comes from `context.get_remaining_time_in_millis()`.
6. **Small, portable dependencies.** Pure Python or prebuilt wheels, versions pinned, no pandas, numpy or Pillow in the backend. Check the `sam build` size early.
7. **Import once, reuse.** Clients, data files and the Agent factory are created at module level and reused across warm invocations.
8. **Same code path everywhere.** Local runs `uvicorn app.main:app`, Lambda runs `Mangum(app)`, and both call the same `run_pipeline`.
9. **Config over code.** Local to AWS means `STORAGE=aws` plus the Lambda handlers. Changing the model provider means `LLM_PROVIDER`, `LLM_BASE_URL` and model names.

### Request flow

1. The browser resizes each photo to at most 1280 px on the long edge (JPEG) before upload. This keeps image tokens and latency down and avoids needing an image library in Lambda.
2. `POST /uploads` returns upload targets (presigned S3 PUT URLs on AWS, local PUT URLs in dev). The browser uploads the photos.
3. `POST /streams` creates the stream with status `SUBMITTED` and returns `202` with `stream_id`.
4. The pipeline runs (background task locally, async Lambda invoke on AWS).
5. The browser polls `GET /streams/{id}` until status is `ROUTED`, `NEEDS_REVIEW` or `FAILED`.
6. The result page shows characterization, rule, routing with reasoning, ledger entries and the report.

### Endpoints

| Method and path | Purpose |
|---|---|
| `POST /uploads` | body `{count}`, returns `[{key, url}]` |
| `POST /streams` | body `{org_id, note, quantity_kg?, photo_keys[]}`, returns `202 {stream_id}` |
| `GET /streams/{id}` | status, characterization, rule, routing, ledger, timings |
| `POST /streams/{id}/wipe` | records a `data_wipe_confirmed` event (simulated certificate) |
| `GET /streams/{id}/report` | PDF (presigned URL on AWS) |
| `GET /orgs/{id}/dashboard` | kg diverted by tier, CO2e avoided, compliance status |
| `GET /processors` | seeded processors for the map |
| `GET /verify/{chain_id}` | public, recomputes the chain, returns `{ok, links, first_broken}` |

Status values for a stream: `SUBMITTED`, `CHARACTERIZING`, `ROUTED`, `NEEDS_REVIEW`, `FAILED`. Handoff status values: `requested`, `matched`, `collected`, `weighed`, `verified`.

## 3. Stack and model choice

| Layer | Local | AWS |
|---|---|---|
| Agent | Strands Agents SDK | Strands Agents SDK |
| Model | Qwen API (Alibaba Cloud Model Studio, OpenAI-compatible endpoint) | the same Qwen API by default; Bedrock only if you add that adapter later |
| Backend | FastAPI, Pydantic | same app via Mangum in the `api` Lambda |
| Worker | FastAPI BackgroundTasks | `pipeline` Lambda (async invoke) |
| Database | SQLite | DynamoDB (on-demand) |
| Files | local disk | S3 (private bucket, presigned URLs) |
| Frontend | React (Vite), Tailwind, Leaflet | Amplify Hosting |
| Reports | ReportLab | ReportLab, stored in S3 |
| Infra as code | none | AWS SAM (`infra/template.yaml`) |
| Logs and cost | console | CloudWatch Logs, AWS Budget alert |

Strands Agents SDK is on the hackathon "Build It" list, and SAM CLI is too. Deploying on Lambda also meets the "Ship It" route. Either one makes the project prize eligible.

### Model choice

- All model calls go to the Qwen API (Alibaba Cloud Model Studio) through its OpenAI-compatible endpoint. No OpenAI or Anthropic APIs are used.
- **Orchestrator:** Strands `OpenAIModel` pointed at the Qwen endpoint with a text model. It never sees images.
- **Characterizer:** the `openai` client pointed at the same endpoint with a vision model, using `image_url` content blocks (base64 data URLs). This avoids depending on how Strands passes images to a given provider.
- **Two vision tiers:** a cheaper one first, a stronger one only on low confidence. Alibaba's docs use `qwen3-vl-plus` in their examples. **VERIFY** current model names, prices and image limits in the Model Studio console, and pick the tiers from there.
- **Base URL:** Alibaba's docs give a workspace-specific Singapore address, `https://{WorkspaceId}.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1`, and say the older `https://dashscope-intl.aliyuncs.com` domain still works. **VERIFY** which one your account uses. Keys are tied to a region, so the key and the base URL must come from the same region.
- **Key:** `DASHSCOPE_API_KEY`. Keep it in `.env` locally and out of git.
- Strands tool calling and `structured_output` work through the OpenAI provider (`pip install 'strands-agents[openai]'`). **VERIFY** that your chosen Qwen text model handles tool calls reliably, and test this early.
- Photos are sent to Alibaba Cloud servers. Use only waste photos with no faces or personal documents, and say so in the README.
- Moving to AWS does not force a model change. Lambda calls the Qwen API over the internet. A Bedrock adapter can be added later behind the same `VisionClient` interface.

Environment variables (all read in `config.py`):

| Variable | Meaning |
|---|---|
| `STORAGE` | `local` or `aws` |
| `LLM_PROVIDER` | `qwen` (default) |
| `LLM_BASE_URL` | OpenAI-compatible base URL for your region |
| `DASHSCOPE_API_KEY` | secret, never committed |
| `MODEL_VISION_FAST`, `MODEL_VISION_STRONG` | vision model names (cheap tier, strong tier) |
| `MODEL_ORCH` | text model for the Strands orchestrator |
| `TIME_BUDGET_MS` | local only; Lambda uses the remaining invocation time |

## 4. Data model

Logical tables (SQLite locally, DynamoDB on AWS):

| Table | Key fields |
|---|---|
| `organizations` | id, name, type (university, company, data center), location |
| `waste_streams` | id, org_id, photos, note, material items, quantity_kg, hazardous, status, timings |
| `processors` | id, name, location, accepted_materials, authorization_ref, price_per_kg, tier, seeded |
| `handoffs` | id, stream_id, processor_id, status |
| `ledger` | chain_id, link_no, event, payload_json, prev_hash, entry_hash, ts, signature |
| `rules` | material, hazardous, rule_name, section_ref, handler_requirement, paperwork |

Storage choices:

- `rules`, `processors`, `organizations`, prices and CO2e factors are small and static. Ship them as JSON in `backend/app/data/` and load them once at startup. Do not put them in DynamoDB.
- DynamoDB holds `streams` (partition key `stream_id`), `ledger` (partition key `chain_id`, sort key `link_no` as a number), handoffs inside the stream item, and a small `cache` table (partition key `image_sha`, with TTL).
- The ledger uses one chain per stream (`chain_id = stream_id`). Attribute names `link_no` and `entry_hash` avoid DynamoDB reserved words.

## 5. The agent

### Two layers

- **Orchestrator:** a Strands `Agent` with five tools and a short system prompt. It decides the order of tool calls and handles streams with several items.
- **Characterizer:** a plain `VisionClient` call (OpenAI-compatible chat completions to Qwen) used inside `characterize_waste`. It is not a Strands agent, and it is the only place images enter a model.

### Tools

| Tool | Input | Output |
|---|---|---|
| `characterize_waste` | stream_id | list of items: material, composition note, quantity_kg, quantity_basis (stated or estimated), purity, hazardous, is_storage_device, confidence, reasoning |
| `lookup_rules` | material, hazardous | rule name, section_ref, who may handle, paperwork |
| `find_processors` | item, location | top 3 authorized processors that accept it, ranked by hierarchy tier, then distance, then price |
| `record_handoff` | stream_id, processor_id, event | new ledger entry (hash, link_no) |
| `generate_report` | org_id or stream_id | kg diverted by tier, CO2e avoided, compliance status, PDF path |

Characterization schema (Pydantic):

```python
class Item(BaseModel):
    material: Literal[
        "aluminium_scrap", "steel_scrap", "copper_scrap", "mixed_metal",
        "paper", "cardboard", "e_waste_computer", "e_waste_storage_drive",
        "e_waste_other", "battery_lead_acid", "battery_lithium",
        "used_oil", "other",
    ]
    composition_note: str
    quantity_kg: float | None
    quantity_basis: Literal["stated", "estimated"]
    purity: Literal["high", "mixed", "unknown"]
    hazardous: bool
    is_storage_device: bool
    confidence: float          # 0 to 1
    reasoning: str

class Characterization(BaseModel):
    items: list[Item]
    overall_confidence: float
```

The characterizer asks the vision model for JSON matching this schema, parses it with Pydantic, retries once if the JSON is invalid (strip code fences first), and sends the item to `NEEDS_REVIEW` if it still fails. **VERIFY** whether the Qwen endpoint supports `response_format={"type": "json_object"}` for the model you pick. The retry logic covers it either way.

Adapter sketches:

```python
# backend/app/llm/base.py
from typing import Protocol

class VisionClient(Protocol):
    def characterize(self, images: list[bytes], prompt: str, model: str) -> tuple[dict, dict]:
        """Return (parsed_json, usage)."""
```

```python
# backend/app/llm/qwen.py
import base64, json
from openai import OpenAI

class QwenVision:
    def __init__(self, api_key: str, base_url: str):
        # created once at import time and reused across warm Lambda invocations
        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=60, max_retries=2)

    def characterize(self, images, prompt, model):
        content = [{"type": "text", "text": prompt}]
        for img in images:
            b64 = base64.b64encode(img).decode()
            content.append({"type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
        r = self.client.chat.completions.create(
            model=model, temperature=0.1, max_tokens=800,
            messages=[{"role": "user", "content": content}],
        )
        return json.loads(r.choices[0].message.content), r.usage.model_dump()
```

```python
# in config.py: the orchestrator model for Strands
from strands.models.openai import OpenAIModel

def build_orchestrator_model(s):
    return OpenAIModel(
        client_args={"api_key": s.api_key, "base_url": s.base_url},
        model_id=s.model_orch,
        params={"max_tokens": 1200, "temperature": 0.1},
    )
```

**VERIFY** that Qwen accepts base64 data URLs for images and what the size limits are. If it does not, upload the resized image to a temporary public URL (a short-lived presigned S3 URL on AWS) and pass that instead.

### Guardrails (enforced in code, never only in the prompt)

1. `find_processors` calls the rules lookup internally. The agent cannot route without the rules being applied.
2. Hazardous items can only go to processors whose `authorization_ref` covers that waste type. Otherwise the result is `NEEDS_REVIEW`.
3. Confidence below 0.7 after escalation sends the item to `NEEDS_REVIEW`. Hazardous items with confidence below 0.85 do the same.
4. `record_handoff` refuses to move a storage device past `requested` until the ledger holds a `data_wipe_confirmed` event for it.
5. The agent routes and flags hazardous waste only. It never gives handling advice.
6. Tool-call cap: a counter in the tool wrapper raises after 12 calls in one run.

### Efficiency rules (apply in every phase)

1. **Images enter once.** All photos of a stream go into a single characterization call, resized to 1280 px client-side, maximum 4 photos. The orchestrator receives compact JSON only.
2. **Deterministic work stays in code.** Rules, matching, guardrails, CO2e, ledger and report are plain Python. Models are used only for characterization, orchestration and one short plain-language rationale.
3. **Confidence-gated escalation.** Run the cheap model first. If `overall_confidence` is below 0.7, run the strong model once. If still low, mark `NEEDS_REVIEW`. Never loop.
4. **Hard limits.** Set `max_tokens` on every model, temperature 0 to 0.2, the tool-call cap above, and the Lambda timeout.
5. **Compact tool outputs.** Return ids and short fields, top 3 processors only, no full rule texts.
6. **Cache by image hash.** `sha256` of the resized image bytes maps to the characterization. Repeat demos cost nothing.
7. **Cheap cold starts.** Load JSON data, create boto3 clients and build the Agent factory at module import, outside the handler. Use arm64. Keep dependencies small (no pandas, numpy or Pillow in Lambda). Measure memory settings.
8. **Idempotent pipeline.** At start, read the stream status and exit if it is already past `SUBMITTED`. Ledger writes are conditional (section 6). Set async invoke retries to 0 so a failure does not silently re-run.
9. **Cost guard.** An AWS Budget alert, API Gateway throttling, and if your account allows it, reserved concurrency on the pipeline Lambda.
10. **Observability.** One JSON log line per step: stream_id, step, milliseconds, model id, token counts. Take orchestrator token counts from the Strands agent result metrics (**VERIFY** attribute names in your installed version) and vision token counts from the `usage` field of the Qwen response.
11. **Reuse the HTTP client.** One client per process with an explicit timeout (60 seconds) and at most 2 retries with backoff on rate-limit and 5xx errors. Never create a client per request.

Targets to measure and report, not promises:

| Metric | Target |
|---|---|
| Model calls per single-item stream | 1 vision call plus at most 4 orchestrator turns |
| Warm end-to-end time | 30 seconds or less |
| Average characterization time | 10 seconds or less |
| Init (cold start) overhead | under 5 seconds |
| Cost per stream | record the actual figure from the bill |

## 6. The ledger

Each entry stores `entry_hash = SHA256(prev_hash + payload_json + ts)`. The first entry in a chain uses `prev_hash = "0" * 64`. The payload is stored as a canonical JSON string (`payload_json`) so the hash input is byte-identical when read back. DynamoDB returns numbers as `Decimal`, which is why the payload is stored as a string and never re-serialized.

```python
import hashlib, json
from datetime import datetime, timezone

GENESIS = "0" * 64

def canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def compute_hash(prev_hash: str, payload_json: str, ts: str) -> str:
    return hashlib.sha256((prev_hash + payload_json + ts).encode("utf-8")).hexdigest()
```

Append on DynamoDB, with a conditional write so two writers can never create the same link:

```python
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

def append(table, chain_id: str, event: str, payload: dict, retries: int = 3) -> dict:
    for _ in range(retries):
        head = table.query(
            KeyConditionExpression=Key("chain_id").eq(chain_id),
            ScanIndexForward=False, Limit=1, ConsistentRead=True,
        )["Items"]
        link_no = int(head[0]["link_no"]) + 1 if head else 1
        prev = head[0]["entry_hash"] if head else GENESIS
        ts = datetime.now(timezone.utc).isoformat()
        payload_json = canonical(payload)
        item = {
            "chain_id": chain_id, "link_no": link_no, "event": event,
            "payload_json": payload_json, "prev_hash": prev, "ts": ts,
            "entry_hash": compute_hash(prev, payload_json, ts),
        }
        try:
            table.put_item(Item=item, ConditionExpression="attribute_not_exists(link_no)")
            return item
        except ClientError as e:
            if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
                raise
    raise RuntimeError("ledger append kept colliding")
```

The SQLite version uses the same `canonical` and `compute_hash`, with a unique constraint on `(chain_id, link_no)` in place of the condition.

Verification walks the chain from link 1, recomputes every hash, checks each `prev_hash` against the previous entry, and returns `{ok, links, first_broken}`. The public verify page shows green, or red at the first broken link.

Demo moment: edit one `payload_json` directly in the database (DynamoDB console on AWS), reload the verify page, and show it turn red.

Stated limit: the chain proves records were not edited afterwards. It does not prove the physical event happened. Weighing photos and signed processor confirmations are the next step. Optional Ed25519 signatures (PyNaCl) are a stretch.

## 7. Data sources

| Data | Source | File |
|---|---|---|
| Waste photos | Own 80 to 150 labeled campus photos; TACO, TrashNet, Kaggle waste and e-waste sets, Roboflow Universe (check each license) | `eval/test_photos/`, `eval/labels.csv` |
| Rules | E-Waste (Management) Rules 2022, Hazardous and Other Wastes Rules 2016, Battery Waste Management Rules 2022, Plastic Waste Management Rules, Solid Waste Management Rules 2016, from CPCB, MoEFCC, eGazette. **VERIFY** exact titles and amendments | `data/rules.json` (30 to 50 rows with section refs) |
| Processors | CPCB authorized recycler list, foundries near Patiala and Mandi Gobindgarh, local paper recyclers and refurbishers | `data/processors.json` |
| Prices | Rates from 2 or 3 local dealers | `data/prices.json` |
| CO2e factors | EPA WARM, IPCC or DEFRA tables, one factor per material, source cited | `data/co2.json` |
| Organizations | Three sample orgs | `data/orgs.json` |

Models are not trained. The photo sets are a test set used to measure accuracy.

## 8. Repo layout

```
loopback/
  BUILD.md
  README.md
  backend/
    app/
      main.py              # FastAPI app (local and Lambda)
      lambda_api.py        # Mangum handler for the api Lambda
      lambda_pipeline.py   # handler for the pipeline Lambda
      pipeline.py          # run_pipeline(stream_id)
      agent.py             # build_orchestrator(): Strands Agent
      models.py            # Pydantic schemas
      config.py            # env-driven settings, storage and model factories
      storage/             # base.py, local.py (SQLite + disk), aws.py (DynamoDB + S3)
      llm/                 # base.py (VisionClient interface), qwen.py, bedrock.py (optional, later)
      tools/               # characterize.py rules.py matching.py ledger.py report.py guardrails.py
      data/                # rules.json processors.json prices.json co2.json orgs.json
    tests/
    requirements.txt
  eval/
    test_photos/  labels.csv  run_eval.py
  frontend/
    src/pages/             # Upload, Result, Map, Dashboard, Verify
  infra/
    template.yaml          # AWS SAM
    samconfig.toml
    events/pipeline.json
  scripts/
    hello_agent.py  seed.py
```

## 9. Phases

### Schedule (IST)

Today is Friday 9 October. The submission is due before 11 October, so there are about 36 hours. **VERIFY** the exact deadline time on the hackathon page.

| Phase | When |
|---|---|
| 0. Setup | Fri 9 Oct, afternoon (AWS account steps start now, in parallel) |
| 1. Core | Fri 9 Oct, evening |
| 2. Routing and proof | Fri night to Sat 10 Oct, early morning |
| 3. AWS deployment | Sat 10 Oct, morning to midday |
| 4. Interface | Sat 10 Oct, afternoon (a teammate can start Fri night against mock data using the section 2 contract) |
| 5. Submit | Sat 10 Oct, evening to night |
| Buffer | Sun 11 Oct, morning: fixes and re-testing only |

Suggested split for three people: (A) agent, tools, guardrails, ledger, Lambda; (B) data, photos, rules table, processors, eval; (C) frontend, Amplify, report, demo video.

Biggest schedule risk: the AWS account. Phases 0 to 2 and 4 do not need it, because the models come from the Qwen API. If it is not usable by Saturday midday, keep the local build, deploy the API on a free host, and keep Strands as the eligibility anchor.

### Phase 0: Setup

1. Create the repo with the layout from section 8. Python 3.12 virtualenv. Install `'strands-agents[openai]' fastapi uvicorn pydantic mangum boto3 openai pytest reportlab` (the `[openai]` extra provides the OpenAI-compatible provider used for Qwen; **VERIFY** package names). Install Node, AWS CLI v2 and SAM CLI. Docker is needed only for `sam local` and `sam build --use-container`.
2. Qwen API: create an Alibaba Cloud Model Studio account, create an API key, note its region and the matching base URL, and test one text call and one image call with curl or the `openai` client. Put the key in `.env` as `DASHSCOPE_API_KEY`.
3. AWS account (do this in parallel, it can stall; Phases 1 and 2 do not depend on it):
   - Sign in as root in a private window. If you get "bad request" or a forced logout, clear cookies for `aws.amazon.com` and `signin.aws.amazon.com`, or switch browser, with VPN and extensions off.
   - In Billing, check the account plan. A new account on the Free plan can block services such as IAM until you upgrade to the Paid plan. Credits should carry over (**VERIFY** on the page before confirming).
   - Create an AWS Budget with a 5 dollar alert and email notification.
   - Turn on MFA for root.
   - Create `loopback-dev`: an IAM user with admin permissions and an access key, or IAM Identity Center. Stop using root after this. Delete the access key when the hackathon is over.
   - `aws configure` (or `aws sso login`), then `aws sts get-caller-identity` must succeed.
   - If it still fails, open a free Account and Billing support case.
4. Choose the models from the Model Studio console: a cheap and a strong vision model, and one text model for the orchestrator (**VERIFY** names).
5. Write `scripts/hello_agent.py`: a Strands agent (`OpenAIModel` on Qwen) with one tool, plus one `VisionClient` call on a single photo returning JSON.
6. Start collecting photos. Download the rule PDFs.

Done when: the Qwen text and image calls work, the hello-world agent returns, and the skeleton is committed. A working `aws sts get-caller-identity` is needed only before Phase 3.

### Phase 1: Core

1. `models.py`: `Item`, `Characterization`, request and response schemas.
2. `config.py`: the only file that reads environment variables (section 3 table), plus factories that return the storage backend, the `VisionClient` and the orchestrator model.
3. `storage/base.py` and `storage/local.py` (SQLite and disk).
4. Data files: first 30 rows of `rules.json` with section refs, `co2.json`, `prices.json`, `orgs.json`.
5. `llm/base.py`, `llm/qwen.py` and `tools/characterize.py`: the `VisionClient` adapter, JSON validated against the schema with one retry, cheap-then-strong escalation, image-hash cache, and compact output.
6. `tools/rules.py`: `lookup_rules` as a dictionary lookup.
7. Tests: schema validation, rules lookup (hit and miss), escalation logic with a stubbed model.
8. First eval pass on 20 labeled photos.

Done when: a photo becomes a `Characterization` with confidence, the matching rule row comes back with its section ref, and tests pass.

### Phase 2: Routing and proof (the agent is finished here, locally)

1. `data/processors.json`: 6 to 8 seeded processors with accepted materials, authorization_ref, tier (reuse, refurbish, recycle, recovery, disposal), coordinates and price.
2. `tools/matching.py`: `find_processors` with filters (accepts material, authorized for hazardous), ranking by tier, then haversine distance, then price, top 3. It calls the rules lookup internally.
3. `tools/guardrails.py`: all six guardrails from section 5.
4. `tools/ledger.py`: `canonical`, `compute_hash`, `append`, `verify`, with the SQLite implementation.
5. `record_handoff` with the handoff state machine and the wipe requirement for storage devices.
6. `tools/report.py`: kg by tier, CO2e = kg times factor, compliance status, PDF.
7. `agent.py`: `build_orchestrator()` with the five tools, a short system prompt that states the hierarchy and the rules above, and the tool-call cap.
8. `pipeline.py`: `run_pipeline(stream_id)` with idempotent status handling, per-step timing logs and failure handling.
9. `main.py`: all endpoints from section 2, with BackgroundTasks as the local worker.
10. `eval/run_eval.py`: accuracy, confusion matrix, average seconds per classification, and the share of low-confidence items correctly sent to review.
11. Tests: guardrails (hazardous to unauthorized processor refused, drive moved without wipe refused), ledger (append, verify ok, tamper detected), pipeline idempotency.

Done when: three sample streams (workshop, lab, data center) run end to end through the local API, the tamper test turns verify red, and eval numbers are recorded.

### Phase 3: AWS deployment (the pipeline goes to Lambda)

This follows the Strands-on-Lambda pattern from the Strands docs: a `handler(event, context)` that builds the Agent and runs it, and dependencies kept separate from app code (the docs also grant Bedrock invoke permissions, which we skip because models come from the Qwen API). We use SAM instead of the CDK shown in the docs, since SAM CLI is on the hackathon list and is simpler for Python.

Region: deploy to `ap-south-1` (Mumbai) or `ap-southeast-1` (Singapore), close to you and to the Qwen international endpoint. Bedrock is not used, so Bedrock regional availability does not matter. Lambda is not placed in a VPC, so it reaches the Qwen endpoint over the internet with no NAT gateway.

1. **Write `infra/template.yaml`** (skeleton below).
2. **Add `storage/aws.py`**: the DynamoDB and S3 implementation of the `base.py` interface, including the conditional ledger append from section 6 and presigned upload and download URLs.
3. **Write the handlers**:

```python
# backend/app/lambda_pipeline.py
from app.pipeline import run_pipeline

def handler(event, context):
    # leave a 5 second margin to save state and exit cleanly
    budget = context.get_remaining_time_in_millis() - 5000
    return run_pipeline(event["stream_id"], time_budget_ms=budget)
```

```python
# backend/app/lambda_api.py
from mangum import Mangum
from app.main import app

handler = Mangum(app, lifespan="off")
```

The API starts the worker with an async invoke:

```python
boto3.client("lambda").invoke(
    FunctionName=os.environ["PIPELINE_FN"],
    InvocationType="Event",
    Payload=json.dumps({"stream_id": stream_id}).encode(),
)
```

4. **Package.** `sam build` with `backend/requirements.txt`, Python 3.12, arm64. Check the built size: the Lambda limit is 250 MB unzipped including layers. If `strands-agents` pushes you over, remove it from `requirements.txt` and attach the official Strands Lambda layer instead. Copy the exact ARN for your region, Python version, architecture and layer version from the Strands Lambda deployment page (the pattern is `arn:aws:lambda:{region}:856699698935:layer:strands-agents-py{python_version}-{architecture}:{layer_version}`). **VERIFY** the current version number.
5. **Deploy.** `sam build` then `sam deploy --guided` the first time (it prompts for `QwenApiKey` with hidden input). Note the outputs: `ApiUrl`, `BucketName`.
6. **Smoke test.** First `sam local invoke PipelineFunction -e infra/events/pipeline.json` (needs Docker, real AWS credentials), then curl the deployed API: `POST /uploads`, upload a photo, `POST /streams`, poll `GET /streams/{id}`.
7. **Seed.** `scripts/seed.py` creates the sample organizations and uploads the demo photos.
8. **Measure.** From CloudWatch logs: cold start, warm end-to-end time, tokens per stream, cost per stream. Try 1024, 1536 and 2048 MB and keep the cheapest setting that meets the targets.
9. **Tighten.** Keep the Qwen key out of the repo (a NoEcho parameter now, Secrets Manager or SSM Parameter Store later). If you add the Bedrock adapter later, add its invoke permission then, scoped to the model ARNs.

SAM template skeleton:

```yaml
AWSTemplateFormatVersion: "2010-09-09"
Transform: AWS::Serverless-2016-10-31

Parameters:
  LlmBaseUrl:  { Type: String, Default: "https://dashscope-intl.aliyuncs.com/compatible-mode/v1" }   # VERIFY your region's URL
  QwenApiKey:  { Type: String, NoEcho: true }
  ModelVisionFast:   { Type: String, Default: "qwen3-vl-plus" }      # VERIFY names, pick tiers in the console
  ModelVisionStrong: { Type: String, Default: "qwen3-vl-plus" }
  ModelOrch:         { Type: String, Default: "qwen-plus" }
  FrontendOrigin: { Type: String, Default: "*" }   # set to the Amplify URL later

Globals:
  Function:
    Runtime: python3.12
    Architectures: [arm64]
    CodeUri: ../backend/
    Environment:
      Variables:
        STORAGE: aws
        LLM_PROVIDER: qwen
        LLM_BASE_URL: !Ref LlmBaseUrl
        DASHSCOPE_API_KEY: !Ref QwenApiKey
        MODEL_VISION_FAST: !Ref ModelVisionFast
        MODEL_VISION_STRONG: !Ref ModelVisionStrong
        MODEL_ORCH: !Ref ModelOrch
        BUCKET: !Ref UploadBucket
        STREAMS_TABLE: !Ref StreamsTable
        LEDGER_TABLE: !Ref LedgerTable
        CACHE_TABLE: !Ref CacheTable
  Api:
    Cors: { AllowOrigin: !Sub "'${FrontendOrigin}'" }

Resources:
  UploadBucket:
    Type: AWS::S3::Bucket
    Properties:
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true
      CorsConfiguration:
        CorsRules:
          - AllowedMethods: [PUT, GET]
            AllowedOrigins: ["*"]        # tighten to the frontend origin
            AllowedHeaders: ["*"]
      LifecycleConfiguration:
        Rules:
          - { Id: expire-uploads, Status: Enabled, ExpirationInDays: 14 }

  StreamsTable:
    Type: AWS::DynamoDB::Table
    Properties:
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions: [{ AttributeName: stream_id, AttributeType: S }]
      KeySchema: [{ AttributeName: stream_id, KeyType: HASH }]

  LedgerTable:
    Type: AWS::DynamoDB::Table
    Properties:
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - { AttributeName: chain_id, AttributeType: S }
        - { AttributeName: link_no, AttributeType: N }
      KeySchema:
        - { AttributeName: chain_id, KeyType: HASH }
        - { AttributeName: link_no, KeyType: RANGE }

  CacheTable:
    Type: AWS::DynamoDB::Table
    Properties:
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions: [{ AttributeName: image_sha, AttributeType: S }]
      KeySchema: [{ AttributeName: image_sha, KeyType: HASH }]
      TimeToLiveSpecification: { AttributeName: ttl, Enabled: true }

  PipelineFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: app.lambda_pipeline.handler
      Timeout: 180
      MemorySize: 1536
      EventInvokeConfig: { MaximumRetryAttempts: 0 }
      Policies:
        - DynamoDBCrudPolicy: { TableName: !Ref StreamsTable }
        - DynamoDBCrudPolicy: { TableName: !Ref LedgerTable }
        - DynamoDBCrudPolicy: { TableName: !Ref CacheTable }
        - S3CrudPolicy: { BucketName: !Ref UploadBucket }
        # add a Bedrock invoke statement here only if the optional Bedrock adapter is added later

  ApiFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: app.lambda_api.handler
      Timeout: 29
      MemorySize: 512
      Environment:
        Variables:
          PIPELINE_FN: !Ref PipelineFunction
      Policies:
        - DynamoDBCrudPolicy: { TableName: !Ref StreamsTable }
        - DynamoDBReadPolicy: { TableName: !Ref LedgerTable }
        - S3CrudPolicy: { BucketName: !Ref UploadBucket }
        - LambdaInvokePolicy: { FunctionName: !Ref PipelineFunction }
      Events:
        Any:
          Type: Api
          Properties: { Path: "/{proxy+}", Method: ANY }
        Root:
          Type: Api
          Properties: { Path: /, Method: ANY }

Outputs:
  ApiUrl:
    Value: !Sub "https://${ServerlessRestApi}.execute-api.${AWS::Region}.amazonaws.com/Prod"
  BucketName:
    Value: !Ref UploadBucket
```

Notes on the template:

- The API Gateway event type here is the implicit REST API (`Type: Api`), which is the simplest to get working with Mangum. The pipeline runs asynchronously, so the 29 second API Gateway limit never applies to the agent run.
- On new AWS accounts the Lambda concurrency limit can be as low as 10, in which case reserved concurrency is rejected. Use API Gateway throttling instead (add `MethodSettings` with throttling to the API, or set a usage plan).
- Log retention: set 7 days on both function log groups to avoid cost.
- No keys in the repo. The Qwen key is a NoEcho parameter passed at deploy time and lives in the function environment, which is acceptable for a hackathon. Move it to Secrets Manager or SSM Parameter Store afterwards.

Done when: a stream submitted to the deployed API reaches `ROUTED` with ledger entries, the verify endpoint is green, and editing one ledger item in the DynamoDB console turns it red.

### Phase 4: Interface

1. React (Vite) pages: Upload, Result, Map, Dashboard, Verify. The API base URL comes from an environment variable.
2. Upload page: client-side resize to 1280 px JPEG, request upload targets, PUT to S3, create the stream, poll for status.
3. Result page: characterization with confidence, the rule and section ref, the routing with reasoning, the ledger entries, a "Record wipe certificate" button for storage devices, and the report download.
4. Map page: Leaflet with seeded processors, clearly labelled as seeded.
5. Dashboard: kg diverted by tier, CO2e avoided (with the factor source shown), compliance status.
6. Verify page: public, green or red, first broken link highlighted.
7. Deploy to Amplify Hosting (connect the repo, or use a manual zip deploy). Set the API URL environment variable, then restrict the S3 and API CORS origins to the Amplify domain.

Done when: someone who has never seen it can run one stream start to finish on the live URL.

### Phase 5: Submit

1. Record the 3 minute demo: open with one real campus waste number, upload workshop and lab photos, show the reasoning, rule and routing, show the ledger then tamper one row and show verify turn red, show the dashboard and report, close with the roadmap.
2. README: architecture diagram, how to run locally, how to deploy with SAM, and a plain disclosure that processors are seeded and handoffs are simulated.
3. Fill every bracketed number in the pitch from the real eval and CloudWatch figures. Remove any you cannot back.
4. Submit with the live URL, repo and video.
5. Buffer morning: re-test the live URL end to end, fix only what is broken.
6. After judging: `sam delete`, delete the IAM access key, and keep the Budget alert on.

### Cut line

If time runs short, drop in this order: voice input, Cedar access rules, route optimization, payments, Telegram bot, Step Functions, Cognito. Put them on the roadmap slide. Never cut the guardrails, the ledger or the verify page.

## 10. Prompts for the coding agent

Put this file at the repo root as `BUILD.md`. Paste the master prompt once at the start of the session, then paste one phase prompt at a time. Do not move on until the previous phase reports passing acceptance checks.

### Master prompt

```
You are building LoopBack in this repo. BUILD.md at the repo root is the single
source of truth. Read it fully before doing anything.

Rules:
1. Work one phase at a time, in order. I will tell you which phase to run. Do not
   start the next phase on your own.
2. Follow BUILD.md exactly for architecture, file layout, schemas, tool contracts,
   guardrails and efficiency rules. If something in it is wrong or impossible,
   stop and tell me before deviating.
3. Anything marked VERIFY: check the official docs or the installed package source
   first, and tell me what you found.
4. run_pipeline() and every tool stay free of AWS-specific and local-specific code.
   Differences live only behind the storage and model factories in config.py, which
   is the only file allowed to read environment variables. All model calls go to the
   Qwen API through the llm/ adapters. Do not call OpenAI or Anthropic APIs.
5. Safety rules are enforced in code (guardrails.py), never only in prompts.
6. Never invent data. Seeded data carries seeded: true. Never commit secrets,
   keys, or .env files.
7. Write the tests listed for the phase. A phase is not done if any test fails.
8. At the end of each phase: run the acceptance commands, paste the real output,
   list anything unfinished, then stop and wait for me.
9. Write plainly. Keep comments, docs and commit messages short.
```

### Phase 0 prompt

```
Run Phase 0 from BUILD.md, repo and local parts only.

1. Create the repo layout from section 8 with empty modules and short docstrings.
2. Add requirements.txt, .gitignore (include .env, *.pem, __pycache__, .aws-sam,
   node_modules), and config.py as the only file that reads environment
   variables (section 3 table). Add factories for storage, VisionClient and the
   orchestrator model. Do not implement AWS storage yet.
3. Write scripts/hello_agent.py: a Strands agent with one tool, plus one vision call
   on a single photo from eval/test_photos returning the Item schema from section 5.
   Use the Qwen API through its OpenAI-compatible endpoint (LLM_BASE_URL and
   DASHSCOPE_API_KEY from .env). The Strands orchestrator uses OpenAIModel. The vision
   call uses the openai client directly with an image_url data URL.
4. Check the VERIFY items for this phase: package names, the correct Qwen base URL
   and model names for my account, whether base64 data URLs work for images, and
   whether the chosen text model handles Strands tool calls.

Acceptance: `python scripts/hello_agent.py eval/test_photos/<any>.jpg` prints valid
JSON that parses into Characterization. Paste the output. Then stop.
```

### Phase 1 prompt

```
Run Phase 1 from BUILD.md.

Order: models.py, config.py, llm/base.py and llm/qwen.py, storage/base.py and
storage/local.py, the data files
(rules.json with 30 rows from the official texts I will attach, co2.json,
prices.json, orgs.json), tools/characterize.py, tools/rules.py, tests.

Requirements for characterize:
- VisionClient adapter in llm/qwen.py (OpenAI-compatible, image_url data URLs). JSON
  validated against Characterization, one retry on invalid JSON, then NEEDS_REVIEW.
- All photos of a stream go into ONE call. One reused client, 60 second timeout.
- Cheap vision model first. If overall_confidence < 0.7, run the strong model once. No loops.
- Cache by sha256 of the image bytes. Set max_tokens and temperature 0 to 0.2.
- Return compact JSON only. Log one JSON line with step, milliseconds, model id,
  token counts.

Do not invent rules. If a row's section reference is not in the attached text,
leave section_ref null and list it for me.

Acceptance: `pytest backend/tests -q` passes; running characterize on 5 sample
photos prints items with confidence; lookup_rules returns the row with section_ref
for a known material and a clear miss for an unknown one. Paste the output. Stop.
```

### Phase 2 prompt

```
Run Phase 2 from BUILD.md. The agent must be complete and working locally at the end.

Order: processors.json (use only the processors I provide, seeded: true),
tools/matching.py, tools/guardrails.py (all six guardrails), tools/ledger.py with the
SQLite implementation, record_handoff with the state machine and wipe requirement,
tools/report.py, agent.py, pipeline.py, main.py, eval/run_eval.py, tests.

Requirements:
- find_processors calls the rules lookup internally and applies guardrails.
- The orchestrator never receives images. Its tool outputs are compact JSON,
  top 3 processors only.
- Tool-call cap of 12 per run. Idempotent run_pipeline: exit if status is past SUBMITTED.
- Per-step timing logs. Hierarchy order: reuse, refurbish, recycle, recovery, disposal.

Acceptance:
1. `pytest backend/tests -q` passes, including: hazardous to an unauthorized
   processor is refused, a drive cannot move without a wipe event, tamper
   detection, and pipeline idempotency.
2. Run the three sample streams (workshop, lab, data center) through the local
   API with curl. Paste the final JSON of each.
3. Edit one payload_json in the SQLite file; GET /verify/{chain_id} must return
   ok: false with first_broken set.
4. `python eval/run_eval.py` prints accuracy, confusion matrix, average seconds
   per classification, and the share of low-confidence items sent to review.
Paste all output. Stop.
```

### Phase 3 prompt

```
Run Phase 3 from BUILD.md. This moves the finished pipeline to AWS Lambda.
Region ap-south-1 (confirm with me). Do not change pipeline or tool logic; only add
AWS code behind the existing interfaces. Models stay on the Qwen API.

Order:
1. storage/aws.py (DynamoDB and S3) implementing storage/base.py, including the
   conditional ledger append from section 6 and presigned URLs.
2. lambda_pipeline.py and lambda_api.py exactly as in section 9. The API starts the
   worker with an async invoke.
3. infra/template.yaml from the skeleton in section 9. Fix anything in it that fails
   validation. Run `sam validate`.
4. `sam build`. Report the built package size. If it exceeds 250 MB unzipped, switch
   to the official Strands Lambda layer as described in section 9 and tell me which
   layer ARN and version you used.
5. Ask me before running `sam deploy`. After I confirm, deploy, then run the smoke
   test: POST /uploads, upload a photo, POST /streams, poll until ROUTED.
6. Write scripts/seed.py.
7. Confirm the Lambda reaches the Qwen endpoint, the key is passed as a NoEcho
   parameter and never committed, and report latency of one Qwen call from Lambda.

Acceptance: a stream on the deployed API reaches ROUTED with ledger entries;
/verify is ok; after I edit one ledger item in the DynamoDB console, /verify is red.
Paste the commands and outputs. Stop.
```

### Efficiency audit prompt (run after Phase 3)

```
Audit the deployed pipeline against section 5 (efficiency rules and targets) in
BUILD.md. Do not change behavior unless a rule is violated.

1. Run 10 streams (5 cold, 5 warm if possible) and read CloudWatch logs.
2. Report a table: model calls per stream, tokens per stream, cold start overhead,
   warm end-to-end time, average characterization time, cost per stream.
3. List any efficiency rule that is violated, with the file and line.
4. Try memory sizes 1024, 1536 and 2048 MB. Recommend the cheapest that meets the
   targets.
5. Check: images enter exactly one model call; the orchestrator sees no image bytes;
   escalation happens at most once; async retries are 0; data files load once at init.
Fix violations, redeploy, and re-measure. Paste the before and after table. Stop.
```

### Phase 4 prompt

```
Run Phase 4 from BUILD.md. Frontend in frontend/ using React (Vite) and Tailwind.
Keep the design minimal and clean. The API base URL comes from VITE_API_URL.

Pages: Upload, Result, Map, Dashboard, Verify, as specified in section 9.
- Upload resizes each photo to at most 1280 px JPEG in the browser before upload.
- Result polls every 2 seconds, stops on ROUTED, NEEDS_REVIEW or FAILED, shows
  confidence, the rule with section ref, routing reasoning, ledger entries, a
  wipe-certificate button for storage devices, and the report download.
- Map labels processors as seeded. Dashboard shows the CO2e factor source.
- Verify is public and highlights the first broken link in red.

Then give me exact steps to deploy to Amplify Hosting, set VITE_API_URL, and tighten
CORS on the API and the bucket to the Amplify domain.

Acceptance: `npm run build` succeeds; running one full stream against the deployed
API from the browser works. Paste results. Stop.
```

### Phase 5 prompt

```
Run Phase 5 from BUILD.md.

1. Write README.md: architecture diagram (from section 2), run locally, deploy with
   SAM, the eval and efficiency numbers from the real runs, and a plain disclosure
   that processors are seeded and handoffs are simulated.
2. Produce a 3 minute demo script with exact click order and what to say, using the
   real numbers from the eval and CloudWatch.
3. List every bracketed placeholder still left in README.md or the pitch, with the
   real value if we have it, or "remove" if we cannot back it.
4. Write a teardown checklist: sam delete, delete the IAM access key, keep the Budget alert.
5. Final end-to-end test on the live URL. Report anything broken.

Do not change pipeline logic in this phase. Stop after the report.
```

## 11. Open items to verify

- Exact rule titles, amendments and requirements, against the official CPCB and MoEFCC texts.
- License of every public dataset used.
- Qwen model names (cheap vision, strong vision, text orchestrator), the base URL for your account's region, and that your API key region matches it.
- That the Qwen endpoint accepts base64 data URL images, its image size limits, and whether JSON mode is supported.
- That Strands `OpenAIModel` tool calling works reliably with your chosen Qwen text model.
- The Strands result metrics attribute names in the installed version.
- The official Strands Lambda layer version number and ARN for your region.
- That an upgraded Paid plan keeps your remaining credits.
- Whether your Lambda concurrency limit allows reserved concurrency.
- The authorized status of each seeded processor.
- The exact submission deadline time.
