# FinBot Architecture

**Visual diagrams of the FinBot system components, data flow, and RAG pipeline**

---

## 🏗️ System Components

```mermaid
graph TB
    subgraph Docker["🐳 Docker Services"]
        PG[(PostgreSQL<br/>Port 5435)]
        QD[(Qdrant Vector DB<br/>Port 6333)]
    end
    
    CLI[CLI Interface<br/>src/cli/] --> Core[Core Processing<br/>src/core/]
    API[REST API<br/>src/api/] --> Core
    Core --> Models[Data Models<br/>src/models/]
    Core --> QD
    Core --> Embedding[SentenceTransformers<br/>all-MiniLM-L6-v2]
    Core --> PG
    Tests[Test Suite<br/>src/tests/] --> Core
    Tests --> API
    Tests --> CLI
    Frontend[Frontend<br/>Next.js 14<br/>Port 3001] --> API
```

---

## 🔄 Request Data Flow

```mermaid
sequenceDiagram
    participant User as User / Admin
    participant Frontend as Frontend<br/>Next.js 14
    participant API as REST API
    participant Core as Core Processing
    participant PG[(PostgreSQL)]
    participant QD[(Qdrant)]

    User->>Frontend: Upload document / Chat query
    Frontend->>API: HTTP request
    API->>PG: RBAC lookup, user validation
    API->>Core: Process request
    Core->>QD: Vector search (role-filtered)
    QD-->>Core: Relevant chunks
    Core->>API: Generate response
    API-->>Frontend: JSON response
    Frontend-->>User: Display results
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
