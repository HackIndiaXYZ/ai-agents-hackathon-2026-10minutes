# 🌾 Sahayak AI — Financial Inclusion for Rural India

> *"Sahayak" means helper in Hindi. We built an AI that speaks your language, knows your schemes, and protects you from fraud — whether you're a farmer in UP or a shopkeeper in Tamil Nadu.*

---

## The Problem

India has made remarkable progress — **559.8 million Jan-Dhan accounts**, 80% banking penetration. But access is not the same as understanding.

- Only **27% of Indian adults are financially literate**
- Rural and low-income groups still rely on cash, missing out on subsidies, insurance, and safe digital payments
- Scams targeting rural users (fake loan apps, UPI fraud, lottery schemes) cost billions yearly
- Government schemes worth **₹3+ lakh crore** go unclaimed every year because people don't know they're eligible

**The gap isn't access. It's knowledge — and language.**

A farmer in Maharashtra asking about PM-KISAN in Marathi deserves the same quality of financial guidance as a city professional googling in English. Sahayak AI is that bridge.

---

## What We Built

A **production-grade, multilingual, multi-agent AI assistant** that:

- Understands queries in **11+ Indian languages** (Hindi, Marathi, Tamil, Telugu, Bengali, Gujarati, Kannada, Malayalam, Punjabi, Urdu, English) — including code-switching
- Runs a **11-node LangGraph reasoning pipeline** with live agent-by-agent streaming
- Retrieves answers from a **4,811-record knowledge base** of real financial fraud Q&A using hybrid BGE-M3 + Qdrant vector search
- Identifies **eligible government schemes**, **required documents**, **complaint pathways**, and **active fraud alerts** — all in parallel from a single chat message
- Continuously **grows its own dataset** via an adaptive data loop that logs, anonymises, and re-ingests every user interaction
- Builds a **personal knowledge graph** per user, tracking their financial literacy across 6 domains and adapting responses to their level

---

## Live Demo Flow

```
User types: "मुझे PM किसान योजना के लिए क्या दस्तावेज़ चाहिए?"
             (What documents do I need for PM Kisan scheme?)

                        ┌─────────────────────────────┐
                        │    Sahayak AI Pipeline        │
                        │                               │
  Query ──────────────► │ 1. Language: Hindi detected   │
                        │ 2. Context:  Farmer profile   │
                        │ 3. Supervisor: route query    │
                        │ 4. Decompose: 2 sub-queries   │
                        │ 5. Web Search: latest rules   │
                        │ 6. RAG: 5 similar expert Q&A  │
                        │ 7. Reasoning: synthesise      │
                        │ 8. Recommend: next steps      │
                        │ 9. Safety: fraud check        │
                        │ 10. Format: clean response    │
                        │ 11. Feedback: log & learn     │
                        └─────────────────────────────┘
                                      │
                          ┌───────────┴───────────┐
                          │                       │
                   Chat Answer              Explore Panel
                  (streamed live)        ┌─────────────────┐
                                         │ 🏛 Eligible      │
                                         │   Schemes (3) →  │
                                         │ 📄 Documents (7)→│
                                         │ 📋 File Complaint│
                                         │ 🚨 Fraud Alerts  │
                                         └─────────────────┘
```

---

## Architecture

### The 11-Agent LangGraph Pipeline

Every message flows through a directed graph of specialist agents. Each fires in sequence, streams its status to the frontend in real time, and hands enriched state to the next.

```
                         USER QUERY
                             │
                             ▼
                    ┌─────────────────┐
                    │  language_agent  │  Gemini Flash
                    │  • Detect lang   │  • 11 Indian languages
                    │  • Detect script │  • Code-switch aware
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  context_agent   │  Gemini Pro
                    │  • Load profile  │  • Redis session store
                    │  • Update KG     │  • Knowledge graph update
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ supervisor_agent │  Gemini Pro
                    │  • Classify      │  • Route decision
                    │  • Confidence    │  • Complexity score
                    └────────┬────────┘
                             │
                  ┌──────────┴──────────┐
                  │                     │
                  ▼                     ▼
         ┌──────────────┐     ┌──────────────────┐
         │clarification │     │decomposition_agent│  Gemini Flash
         │    _agent    │     │ • Split complex   │  • Up to 4 sub-queries
         │ • Ask user   │     │ • Type each query │  • Web search flags
         └──────┬───────┘     └────────┬─────────┘
                │                      │
                │             ┌────────┴────────┐
                │             ▼                 ▼
                │    ┌──────────────┐  ┌──────────────────┐
                │    │web_search_   │  │ reasoning_agent   │  Gemini Pro
                │    │   agent      │  │ • BGE-M3 RAG      │  • Hybrid Qdrant
                │    │ • Google API │  │ • 4,811 Q&A KB    │  • RRF fusion
                │    │ • Structured │  │ • Web synthesis   │  • Evidence graded
                │    └──────┬───────┘  └────────┬─────────┘
                │           └──────────┬─────────┘
                │                      │
                │                      ▼
                │           ┌──────────────────┐
                │           │recommendation_   │  Gemini Flash
                │           │     agent        │  • Next steps
                │           │ • Action plan    │  • Scheme links
                │           └────────┬─────────┘
                │                    │
                │                    ▼
                │           ┌──────────────────┐
                │           │fraud_safety_agent │  Gemini Flash
                │           │ • Regex layer     │  • Pattern match
                │           │ • LLM classify    │  • SAFE/WARN/BLOCK
                │           └────────┬─────────┘
                │                    │
                └──────────┬─────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ formatter_agent  │  Gemini Flash
                  │ • Final response │  • Lang-matched
                  │ • JSON struct    │  • Literacy-tuned
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  feedback_agent  │  Pure Python
                  │  • Redis log     │  • Adaptive loop
                  │  • Interaction   │  • Dataset growth
                  └─────────────────┘
```

### RAG System — BGE-M3 + Qdrant Hybrid Search

```
User Query (any language)
        │
        ▼
┌───────────────────────────────────────────────────┐
│              BGE-M3 Encoder (CUDA)                │
│                                                   │
│  ┌──────────────────┐  ┌──────────────────────┐  │
│  │  Dense Vector     │  │   Sparse Vector       │  │
│  │  (1024-dim)       │  │  (lexical weights)    │  │
│  │  Semantic meaning │  │  Exact keyword match  │  │
│  └────────┬─────────┘  └──────────┬────────────┘  │
└───────────┼────────────────────────┼───────────────┘
            │                        │
            ▼                        ▼
┌─────────────────────────────────────────────────────┐
│                   Qdrant (Docker)                    │
│                                                      │
│   Dense index  ──┐                                   │
│                  ├──► RRF Fusion ──► Top 5 Results   │
│   Sparse index ──┘   (Reciprocal                     │
│                       Rank Fusion)                   │
│                                                      │
│   4,811 records · sahayak_fraud_qa collection        │
│   Persisted at C:\Users\skmis\qdrant_storage         │
└─────────────────────────────────────────────────────┘
            │
            ▼
┌───────────────────────────────────────────────────┐
│           Reasoning Agent (Gemini Pro)            │
│                                                   │
│  Evidence priority:                               │
│    1. Dataset expert cases (RAG)                  │
│    2. Web search (current facts)                  │
│    3. General knowledge (fallback)                │
└───────────────────────────────────────────────────┘
```

**Why BGE-M3?** It's the only open embedding model that handles all Indian scripts natively — one model encodes Hindi, Tamil, Bengali, Marathi and English equally well, with no translation step.

### Adaptive Data Loop

```
User Interaction
      │
      ▼
┌─────────────────────────────────────────────────────┐
│              feedback_agent (every turn)             │
│                                                      │
│  Raw event logged to Redis list (capped at 5,000)    │
│  Fields: session_id, query, response, language,      │
│          domain, confidence, latency, user_profile   │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼ (on-demand or scheduled)
┌─────────────────────────────────────────────────────┐
│              DataLoop Harvester API                  │
│                                                      │
│  1. Pull raw events from Redis queue                 │
│  2. Anonymise (strip PII — names, IDs, numbers)      │
│  3. Gemini Pro formats into structured Q&A records   │
│  4. Validate schema + deduplicate                    │
│  5. Append to adaptive_dataset.jsonl                 │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│           Re-ingest into Qdrant                      │
│                                                      │
│  python rag/ingest_bge.py --path adaptive_dataset    │
│                                                      │
│  → BGE-M3 re-encodes new records                     │
│  → Upserted into sahayak_fraud_qa collection         │
│  → Every user interaction improves future answers    │
└─────────────────────────────────────────────────────┘
```

The knowledge base **grows automatically**. A question asked today that stumped the system becomes a training example that helps tomorrow's users.

---

## Features

### 💬 Multilingual Chat with Live Agent Pipeline
- Stream-based SSE responses — words appear as they're generated
- Right-hand panel shows each of the 11 agents lighting up in real time with latency
- Handles Hindi, Marathi, Tamil, Telugu, Bengali, Gujarati, Kannada, Malayalam, Punjabi, Urdu, English
- Code-switch aware — "mera UPI kyun band ho gaya" is understood perfectly
- Session-level conversation memory via Redis (24h TTL)

### ⚡ Integrated Parallel Pipeline (Explore Further)
When you send a chat message, Sahayak simultaneously:
1. Streams the main AI answer
2. After the response lands, fires parallel API calls based on **intent detection**
3. Attaches contextual deep-link buttons to every AI bubble:

| Button | What it does |
|--------|-------------|
| 🏛 Eligible Schemes (N) | Shows which government schemes you qualify for |
| 📄 Document Checklist (N) | Lists exactly what paperwork you need |
| 📋 File Complaint | Guides you to the right grievance authority |
| 🚨 Fraud Alerts | Shows active scam warnings relevant to your query |
| 🔍 Similar Questions | RAG results — what others asked in similar situations |

Click any button → navigate to that feature page with data **pre-loaded**. No re-fetching, no switching tabs manually.

### 🧠 Personal Knowledge Graph
Each user gets a persistent literacy profile across 6 domains:
- **Banking & Accounts** — UPI, savings, loans
- **Insurance** — PMSBY, PMJJBY, crop insurance
- **Government Schemes** — PMJDY, PM-KISAN, MGNREGA
- **Digital Payments** — UPI safety, mobile wallets
- **Fraud Awareness** — scam recognition, reporting
- **Investment Basics** — SIP, FD, mutual funds

The graph updates after every conversation. Beginner users get simpler explanations; advanced users get technical depth — automatically.

### 🏛 Benefits Hub
- **Scheme Eligibility** — enter your profile, get a list of schemes you qualify for with eligibility breakdown
- **Document Checklist** — describe what you need to apply for; get a precise list of required documents
- **Complaint Guide** — describe your issue; get routed to the right authority (RBI, SEBI, local consumer forum, cyber crime portal)
- **Fraud Alert Feed** — live feed of active scam warnings, filterable by type

### 🔍 RAG Pipeline Test
- Direct interface to the BGE-M3 + Qdrant retrieval system
- See similarity scores, domain categories, suggested actions
- 4,811 expert Q&A records covering financial fraud in 11 languages
- Hybrid RRF fusion outperforms pure dense or pure sparse search

### 📊 Data Loop Panel
- View raw interaction events queued in Redis
- Trigger the anonymisation + Gemini formatting pipeline
- Download the staged JSONL for review
- Re-ingest button to push new examples into Qdrant

### 👤 Onboarding & Profile System
- 3-step profile creation (name, location/occupation, language preference)
- Adaptive questionnaire (12–15 questions) to assess baseline literacy
- Knowledge graph generated from questionnaire answers
- Profiles stored in Redis (7-day TTL) with Set-indexed listing
- Profile switcher in the top bar — switch users without re-onboarding

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **LLM** | Google Gemini 2.5 Pro | Complex reasoning, context, supervision |
| **LLM** | Google Gemini 2.5 Flash | Fast agents: language, format, safety, clarification |
| **Orchestration** | LangGraph | Stateful 11-node directed agent graph |
| **Backend** | FastAPI | Async API, SSE streaming, REST endpoints |
| **Embeddings** | BGE-M3 (BAAI) | Multilingual dense + sparse encoding on CUDA |
| **Vector DB** | Qdrant (Docker) | Hybrid RRF search, persistent bind-mount storage |
| **Cache / State** | Redis 7 (Docker) | Session store, profile store, interaction queue |
| **Web Search** | Google Custom Search API | Real-time facts, prices, policy updates |
| **Frontend** | React 18 | SPA with SSE stream parsing |
| **Infra (GCP)** | Vertex AI | Gemini API hosting |
| **Dataset** | 4,811-record JSONL | Financial fraud Q&A, 11 languages |

---

## The Dataset

**4,811 expert-curated Q&A records** covering:

| Domain | Examples |
|--------|---------|
| UPI & Digital Fraud | "Someone asked for my OTP claiming to be from SBI" |
| Government Schemes | "PM-KISAN eligibility for tenant farmers" |
| Insurance Claims | "PMSBY claim process after accident" |
| Loan Scams | "Fake loan app took processing fee and disappeared" |
| Investment Fraud | "Chit fund promised 30% returns" |
| Banking | "Bank account frozen, what do I do?" |

Each record contains:
```jsonl
{
  "user_query": "...",          // original question (any Indian language)
  "domain_category": "...",     // Banking / Insurance / Digital Payments / etc.
  "subdomain": "...",
  "language_code": "te",        // ISO 639-1
  "language_name": "Telugu",
  "enhanced_completion": "...", // expert answer
  "actions_suggestions_next_step": "...",
  "learning_outcome": "...",
  "userprofile": "...",
  "source": "..."
}
```

Stored as both a flat JSONL file and as BGE-M3 vector embeddings in Qdrant, with dense (1024-dim) and sparse (lexical) vectors per record.

---

## Safety Architecture

Two-layer safety filter on every response:

```
Response Draft
      │
      ▼
┌─────────────────────────────────┐
│  Layer 1: Deterministic Regex   │
│                                 │
│  Block if response contains:    │
│  • "share your OTP"             │
│  • "guaranteed returns"         │
│  • "send money to claim prize"  │
│  • PIN / password requests      │
└───────────────┬─────────────────┘
                │ PASS
                ▼
┌─────────────────────────────────┐
│  Layer 2: Gemini Flash Classify │
│                                 │
│  SAFE       → send response     │
│  SOFT_WARN  → append disclaimer │
│  HARD_BLOCK → replace entirely  │
└─────────────────────────────────┘
```

RBI rule: "RBI never holds accounts for individuals, never offers lottery prizes, never asks for OTP." Any response that could be mistaken for these is hard-blocked.

---

## Project Structure

```
financial-inclusion/
├── fulli.jsonl                      # 4,811-record knowledge base
├── backend/
│   ├── main.py                      # FastAPI app, SSE /chat endpoint
│   ├── config.py                    # All settings (Pydantic BaseSettings)
│   ├── requirements.txt
│   ├── agents/
│   │   ├── language_agent.py        # Gemini Flash — detect lang/script
│   │   ├── context_agent.py         # Gemini Pro — profile + KG update
│   │   ├── supervisor_agent.py      # Gemini Pro — routing brain
│   │   ├── clarification_agent.py   # Gemini Flash — ask follow-ups
│   │   ├── decomposition_agent.py   # Gemini Flash — split complex queries
│   │   ├── web_search_agent.py      # Google Search — no LLM
│   │   ├── reasoning_agent.py       # Gemini Pro — RAG + web synthesis
│   │   ├── recommendation_agent.py  # Gemini Flash — action plan
│   │   ├── fraud_safety_agent.py    # Regex + Gemini Flash — safety filter
│   │   ├── formatter_agent.py       # Gemini Flash — final response
│   │   └── feedback_agent.py        # Pure Python — Redis logging
│   ├── graph/
│   │   ├── state.py                 # AgentState TypedDict
│   │   ├── graph_builder.py         # LangGraph assembly + conditional edges
│   │   └── router.py                # Routing logic
│   ├── memory/
│   │   └── session_store.py         # Redis helpers (session, profile, feedback)
│   ├── rag/
│   │   ├── bge_retriever.py         # BGE-M3 encode + Qdrant hybrid search
│   │   ├── ingest_bge.py            # Index JSONL into Qdrant
│   │   └── rag_router.py            # /rag/* FastAPI routes
│   ├── routers/
│   │   ├── profiles.py              # /profiles/* endpoints
│   │   ├── schemes.py               # /schemes/eligible
│   │   ├── documents.py             # /documents/checklist
│   │   ├── complaints.py            # /complaints/guide
│   │   └── fraud.py                 # /fraud/alerts
│   └── utils/
│       └── logger.py                # Structured JSON logger
└── frontend/
    └── src/
        ├── App.jsx                  # Root — always-mounted chat, tab routing
        ├── components/
        │   ├── ChatWindow.jsx        # SSE stream + intent detection + parallel calls
        │   ├── MessageBubble.jsx     # Explore Further panel with deep-link buttons
        │   ├── AgentPipeline.jsx     # Live 11-agent visualiser
        │   ├── BenefitsHub.jsx       # Schemes / Docs / Complaints / Fraud tabs
        │   ├── RAGTestPage.jsx       # Direct RAG search interface
        │   ├── KnowledgeTab.jsx      # Knowledge graph + literacy progress
        │   ├── DataLoopPanel.jsx     # Adaptive data loop UI
        │   ├── OnboardingQuestionnaire.jsx
        │   └── ProfileSetup.jsx
        └── api/
            └── client.js            # SSE parsing + all REST calls
```

---

## Setup

### Prerequisites
- Docker Desktop (for Qdrant + Redis)
- Python 3.11+
- Node.js 18+
- Google Cloud account with Vertex AI enabled
- NVIDIA GPU recommended (RTX series) — BGE-M3 runs on CUDA

### 1. Infrastructure

```bash
# Qdrant — vector database (data persists in qdrant_storage)
docker run -d -p 6333:6333 \
  -v ~/qdrant_storage:/qdrant/storage \
  qdrant/qdrant

# Redis — session + profile store
docker run -d -p 6379:6379 redis:7-alpine
```

### 2. GCP Authentication

```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable aiplatform.googleapis.com customsearch.googleapis.com
```

### 3. Backend

```bash
cd backend
cp .env.example .env    # fill in VERTEX_AI_PROJECT_ID, GOOGLE_SEARCH_API_KEY, etc.
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 4. Ingest Knowledge Base

```bash
cd backend
python rag/ingest_bge.py --path ../fulli.jsonl
# Takes ~5 minutes on first run (BGE-M3 encodes 4,811 records on GPU)
# Subsequent runs are skipped if collection already exists
```

### 5. Frontend

```bash
cd frontend
npm install
npm start
# Opens at http://localhost:3000
```

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/chat` | SSE streaming conversation |
| `POST` | `/profiles` | Create / update user profile |
| `GET`  | `/profiles` | List all profiles (Redis Set index) |
| `GET`  | `/profiles/{id}` | Load a profile |
| `POST` | `/rag/similar` | BGE-M3 hybrid search |
| `GET`  | `/rag/health` | Qdrant collection status |
| `POST` | `/schemes/eligible` | Scheme eligibility check |
| `POST` | `/documents/checklist` | Document requirements |
| `POST` | `/complaints/guide` | Complaint routing |
| `GET`  | `/fraud/alerts` | Active fraud warnings |
| `POST` | `/feedback` | Rate a response (thumbs up/down) |
| `GET`  | `/dataloop/queue-size` | Pending interaction events |
| `POST` | `/dataloop/harvest` | Anonymise + format queued events |
| `GET`  | `/health` | Redis + Qdrant health check |

### SSE Event Stream (`POST /chat`)

```
data: {"event": "stream_start", "session_id": "..."}
data: {"event": "agent_complete", "agent": "language", "latency_ms": 82}
data: {"event": "agent_complete", "agent": "context",  "latency_ms": 310}
data: {"event": "agent_complete", "agent": "supervisor","latency_ms": 420}
data: {"event": "agent_complete", "agent": "decomposition","latency_ms": 290}
data: {"event": "agent_complete", "agent": "web_search","latency_ms": 1100}
data: {"event": "agent_complete", "agent": "reasoning", "latency_ms": 2800}
data: {"event": "agent_complete", "agent": "recommendation","latency_ms": 350}
data: {"event": "agent_complete", "agent": "fraud_safety","latency_ms": 190}
data: {"event": "agent_complete", "agent": "formatter",  "latency_ms": 410}
data: {"event": "agent_complete", "agent": "feedback",   "latency_ms": 12}
data: {"event": "final_response", "response": "...", "confidence": 0.87,
       "detected_language": "Hindi", "next_steps": [...], "agents_fired": [...]}
```

---

## Sample Prompts

**English**
- "I got a call saying I won a lottery — is this a scam?"
- "What documents do I need to open a Jan Dhan account?"
- "How do I file a complaint against a fake loan app?"

**Hindi**
- "मेरे UPI से पैसे कट गए लेकिन transaction failed दिख रहा है"
- "PM किसान योजना के लिए कौन eligible है?"
- "क्या मुझे Aadhaar OTP किसी को देना चाहिए?"

**Marathi**
- "माझ्या शेतासाठी कर्ज कसे मिळवायचे?"
- "बँकेने माझा खाते freeze केला, काय करू?"

**Tamil**
- "UPI மோசடியிலிருந்து எப்படி பாதுகாப்பாக இருப்பது?"
- "PM Suraksha Bima Yojana என்றால் என்ன?"

---

## Research Grounding

This project is grounded in field research on India's financial inclusion landscape:

- **559.8 million** Jan-Dhan accounts (over half held by women)
- **80%** banking penetration vs 53% in 2014 — but only **27% financial literacy**
- RBI publishes fraud education in **13 Indian languages** — we encode all of it
- Common scams: fake loan apps, UPI reversal fraud, lottery calls, chit fund fraud, Aadhaar-linked SIM swap
- Target personas: crop farmers, daily wage labourers, women managing household budgets, microentrepreneurs, first-generation digital payment users

The adaptive data loop is inspired by the iterative feedback model described in Adaptive Data research — where each interaction round produces an average **82% improvement** in data quality through automated adaptation pipelines.

---

## What Makes This Different

| Feature | Generic Chatbot | Sahayak AI |
|---------|----------------|------------|
| Languages | English only | 11 Indian languages + code-switch |
| RAG | None | 4,811-record hybrid BGE-M3 + Qdrant |
| Agent pipeline | Single LLM call | 11 specialised agents, live-streamed |
| Safety | Basic filter | 2-layer (regex + LLM), RBI-rule aligned |
| Personalisation | None | Knowledge graph per user, adapts depth |
| Data loop | Static | Every conversation improves the KB |
| Feature integration | Siloed pages | Intent-detected parallel calls, deep links |
| Persistence | None | Redis profiles (7d), Qdrant (permanent) |

---

*Built for HackIndia · Sahayak AI · Financial Inclusion for Bharat*
