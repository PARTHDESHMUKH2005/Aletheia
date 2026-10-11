<div align="center">

# ♻️ LoopBack

### Snap a photo of waste. Get the best buyer, the money earned and the CO₂ saved, with a tamper-proof record.

*An AI agent that turns waste into a routed, auditable, carbon-aware transaction.*

**WeMakeDevs × AWS Hackathon · Waste & Energy track**

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![Gemini](https://img.shields.io/badge/Gemini-vision-4285F4?logo=googlegemini&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-Lambda%20ready-FF9900?logo=amazonaws&logoColor=white)

</div>

> **Transparency note.** Buyers, most prices and recovery rates in this repo are **illustrative demo data**. Nothing is a verified real business or a live quote, and nobody is contacted. See [`docs/DEMO_DATA.md`](docs/DEMO_DATA.md) for exactly what is sourced and what is assumed.

---

## 🔥 The problem

India generates tens of millions of tonnes of waste a year, and a large share of the recyclable part never reaches a recycler.

- **Nobody knows what they hold.** A workshop, lab or data center sees "junk". Is it steel, aluminium, e-waste or hazardous oil? The answer decides who can legally take it.
- **Nobody knows who to call.** Scrap goes to whichever dealer is nearest, at whatever price they offer.
- **Nobody can prove where it went.** Rules such as the E-Waste, Hazardous Waste and Battery Rules require paperwork. Records are scattered, editable and rarely trusted.

## 😣 The pain

| Who | What hurts |
|---|---|
| **Organizations** (campuses, labs, data centers) | Manual sorting, no price discovery, compliance risk if hazardous items go to the wrong handler |
| **Recyclers and processors** | Mixed, unlabelled, unquantified material and no trusted trail |
| **The planet** | Recoverable material gets landfilled or burned, and its CO₂ benefit is lost |

Money and carbon are also treated as separate questions. The highest bidder may be 400 km away, and the trucking cancels the climate gain.

## 💡 The solution

**LoopBack** is an agent that handles the whole journey from a photo to a proof of handoff:

1. 📸 **Characterize.** Gemini vision identifies the material, purity, hazard flag and a confidence score from a photo.
2. 📜 **Apply the rules.** It looks up the Indian waste rule that governs the material and who may legally handle it.
3. 🎚️ **Route with a slider.** One control runs from *more money* to *less carbon*. Buyers are ranked by net ₹/kg and net CO₂e/kg, with transport cost and emissions included.
4. 🧾 **Show the receipt.** It reports money earned and CO₂e avoided against the throw-it-away baseline.
5. 🔗 **Record it.** Every handoff goes into a SHA-256 hash-chained ledger that anyone can re-verify. The result is a shareable **Waste Passport**.
6. 🧑‍⚖️ **Keep a human in the loop.** Low-confidence, hazardous or out-of-scope items go to a review queue instead of being auto-routed.

```
 Photo + pincode ──► Gemini characterizes ──► Rules + guardrails ──► Carbon-aware matching
                                                                          │
        Waste Passport ◄── Hash-chained ledger ◄── Receipt (₹ + CO₂e) ◄───┘
```

## 🏆 Why we stand out

- **Carbon and money in one decision.** The slider, with real transport cost and emissions, makes the trade-off visible instead of hidden.
- **Tamper-evident by design.** Each ledger entry hashes the previous one, so editing history breaks the chain and `/verify` shows it.
- **Compliance-aware, not just clever.** Hazardous and unsure cases are refused or sent to human review. The agent knows what it should not do.
- **Honest about its numbers.** Every figure is labelled *sourced* or *illustrative assumption*. We never present demo data as real.
- **Tested.** Backend tests cover scoring, location, the agent and the API, and an `eval/` harness measures characterization against labelled photos.
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
| **Cloud** | AWS Lambda via Mangum, boto3 (the SAM template in `infra/` is still a stub) |
| **Frontend** | React 18, Vite, Tailwind CSS, React Router, Leaflet maps |
| **Integrity** | SHA-256 hash-chained ledger |
| **Reports** | ReportLab (PDF) |
| **Testing** | pytest, plus a photo-based eval harness |

## 🚀 Quick start

```bash
# Backend
cd backend
pip install -r requirements.txt
export GEMINI_API_KEY=your_key        # Gemini is the default provider
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open the Vite URL, upload a photo and use a demo pincode such as `147001` (Patiala) or `110001` (Delhi).

```bash
# Tests
cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest
```

## 📚 Documentation

| Doc | What's inside |
|---|---|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Plain-words tour of the code and the life of one request |
| [`BUILD.md`](BUILD.md) | Full spec and build runbook |
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
