# FinBot Architecture

**Visual diagrams of the FinBot system components, data flow, and RAG pipeline**

---

## 🏗️ System Components

```mermaid
graph TB

    subgraph Client["🖥️ Client Layer"]
        Frontend[Frontend<br/>Next.js 14<br/>Port 3001]
        CLI[CLI Interface<br/>src/cli/]
        Tests[Test Suite<br/>src/tests/]
    end

    subgraph Backend["⚡ Backend Services"]
        API[REST API<br/>src/api/]
        Core[Core Processing<br/>src/core/]
        Models[Data Models<br/>src/models/]
    end

    subgraph AI["🧠 AI / RAG Pipeline"]
        Docling[Docling Parser<br/>Hierarchical Parsing]
        Chunking[Hierarchical Chunking]
        Embedding[SentenceTransformers<br/>all-MiniLM-L6-v2]
        Router[Semantic Router]
        Guardrails[Guardrails]
        LLM[LLM Response Generation]
    end

    subgraph Docker["🐳 Docker Services"]
        PG[(PostgreSQL<br/>Users / Roles / Audit Logs<br/>Port 5435)]

        QD[(Qdrant Vector DB<br/>Embeddings + Metadata<br/>Port 6333)]
    end

    Frontend --> API
    CLI --> Core
    Tests --> API
    Tests --> CLI

    API --> Core
    Core --> Models

    Core --> Guardrails
    Guardrails --> Router

    Core --> Docling
    Docling --> Chunking
    Chunking --> Embedding

    Embedding --> QD

    Core --> QD
    Core --> LLM
    Core --> PG
```

---

## 🔄 Request Data Flow

```mermaid
sequenceDiagram

    participant User as User / Admin
    participant FE as Frontend<br/>Next.js 14
    participant API as FastAPI Backend
    participant Auth as Auth + RBAC
    participant Guard as Guardrails
    participant Router as Semantic Router
    participant Embed as Embedding Model
    participant QD as Qdrant Vector DB
    participant LLM as LLM Provider
    participant PG as PostgreSQL

    User->>FE: Ask question / Upload document

    FE->>API: HTTP Request

    API->>Auth: Validate JWT + User Role
    Auth->>PG: Fetch user + permissions
    PG-->>Auth: Role + access collections

    API->>Guard: Input guardrails
    Guard-->>API: Query approved

    API->>Router: Detect query intent
    Router-->>API: Route selection

    API->>Embed: Generate query embedding
    Embed-->>API: Vector embedding

    API->>QD: Role-filtered vector search
    Note over API,QD: RBAC metadata filter applied BEFORE retrieval

    QD-->>API: Relevant chunks + metadata

    API->>LLM: Prompt + retrieved context
    LLM-->>API: Generated grounded answer

    API->>Guard: Output guardrails
    Guard-->>API: Citation + leakage validation

    API->>PG: Store audit logs / chat history

    API-->>FE: Final response + citations
    FE-->>User: Display answer
```

---

## 🧠 RAG Pipeline

```
📝 Query Input
     ↓
🛡️  Input Guardrails (Component 3)
     ├── Off-topic Detection
     ├── Prompt Injection Prevention
     ├── PII Detection & Scrubbing
     └── Rate Limiting (20/session)
     ↓
🧠 Semantic Router (Component 2)
     ├── Intent Classification (5 routes)
     ├── RBAC-Enforced Routing
     └── Collection Targeting
     ↓
🔍 Vector Search & RAG Processing
     ├── Role-Based Document Filtering
     ├── Hierarchical Chunk Retrieval
     └── Groq LLM Response Generation
     ↓
🛡️  Output Guardrails (Component 3)
     ├── Citation Enforcement
     ├── Cross-Role Leakage Prevention
     └── Response Grounding Validation
     ↓
📤 Final Response + Guardrail Metadata
```

---

## 🔐 RBAC Access Matrix

```
Collection     │ employee │ finance │ engineering │ marketing │ hr │ c_level
───────────────┼──────────┼─────────┼─────────────┼───────────┼────┼────────
general        │    ✅    │   ✅    │     ✅      │    ✅     │ ✅ │   ✅
finance        │    ❌    │   ✅    │     ❌      │    ❌     │ ❌ │   ✅
engineering    │    ❌    │   ❌    │     ✅      │    ❌     │ ❌ │   ✅
marketing      │    ❌    │   ❌    │     ❌      │    ✅     │ ❌ │   ✅
hr             │    ❌    │   ❌    │     ❌      │    ❌     │ ✅ │   ✅
```

---

## 🐳 Docker Services

```
docker compose up -d
│
├── finbot-postgres (postgres:16-alpine)
│   ├── Port: 5435
│   ├── DB: finbot_db
│   ├── User: finbot / finbot123
│   └── Volume: postgres_data
│
└── finbot-qdrant (qdrant/qdrant:latest)
    ├── Port: 6333 (REST)
    ├── Port: 6334 (gRPC)
    └── Volume: qdrant_data
```
