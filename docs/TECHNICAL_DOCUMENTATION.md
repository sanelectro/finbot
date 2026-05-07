# FinBot Technical Documentation

**Enterprise RAG System with RBAC - Architecture Overview**

---

## 📋 System Overview

FinBot is a **production-ready document processing pipeline** that chunks hierarchical documents, stores them in a vector database with RBAC metadata, and enables semantic search with role-based access control.

### Architecture Philosophy
- **Simplification over complexity**: 6 essential metadata fields vs 15+ over-engineered fields
- **Native tooling**: Docling HierarchicalChunker vs custom processing
- **RBAC-first security**: Vector-level access control with zero data leakage
- **Modular design**: Component-specific documentation and clear separation of concerns

## 🏗️ System Architecture

**👉 [See ARCHITECTURE.md](ARCHITECTURE.md) for all diagrams (component graph, data flow, RAG pipeline, RBAC matrix)**

## 📚 Component Documentation

| Component | Purpose | Key Features | Documentation |
|-----------|---------|--------------|---------------|
| **Core Processing** | Document chunking & vector storage | Native Docling, RBAC enforcement, 54 chunks/sec | [📖 Core Docs](../src/core/docs/README.md) |
| **Data Models** | Pydantic schemas & RBAC structure | 6-field metadata, UUID tracking, validation | [📖 Models Docs](../src/models/docs/README.md) |
| **REST API** | FastAPI endpoints | `/search`, `/health`, `/stats`, <200ms response | [📖 API Docs](../src/api/docs/README.md) |
| **CLI Interface** | System management commands | `ingest`, `test`, Rich UI, progress tracking | [📖 CLI Docs](../src/cli/docs/README.md) |
| **Testing Suite** | Validation & performance testing | Integration tests, RBAC validation, benchmarking | [📖 Testing Docs](../src/tests/docs/README.md) |

## 🔄 Data Flow

See [ARCHITECTURE.md → Request Data Flow](ARCHITECTURE.md#-request-data-flow) for the sequence diagram.

## 🚀 Quick Start

```bash
# 1. Start PostgreSQL + Qdrant (Docker)
docker compose up -d

# 2. Install Python dependencies
pip install -e .

# 3. Load documents into vector database
python -m src.cli ingest documents

# 4. Start API server
PYTHONPATH=. python main.py

# 5. (Optional) Start frontend
cd frontend && npm run dev

# System endpoints:
# 📊 API Docs: http://localhost:8000/docs
# 🏥 Health Check: http://localhost:8000/health
# 💬 Chat Interface: http://localhost:3001
```

## 📊 System Metrics

```
🎯 Performance:           📏 Services:              🔒 Security:
• <200ms search response  • PostgreSQL 16 Alpine    • Role-based access control
• 54 chunks/second        • Qdrant vector DB        • 100% RBAC enforcement
• 0.655+ accuracy (CSV)   • SentenceTransformers    • Zero data leakage
• 100+ concurrent users   • FastAPI + Next.js 14    • Vector-level filtering
```

## 🎯 Architecture Benefits

| Aspect | Achievement | Impact |
|--------|-------------|--------|
| **Simplification** | 15+ → 6 metadata fields | 60% reduction in complexity |
| **Performance** | Native Docling chunker | 66% code reduction, higher reliability |
| **Security** | RBAC-first design | Zero security gaps, filter-first search |
| **Maintainability** | Modular documentation | Clear component separation |

---

## 📋 Navigation Guide

### 🔨 **For Developers**
- [Core Architecture](../src/core/docs/README.md) - Document processing & vector storage internals
- [Data Models](../src/models/docs/README.md) - Schema definitions & RBAC structure
- [Testing Guide](../src/tests/docs/README.md) - Integration testing & validation procedures
- [Guardrails System](GUARDRAILS_DOCUMENTATION.md) - Input/output safety measures & validation

### 🚀 **For Users**  
- [CLI Usage](../src/cli/docs/README.md) - Batch ingestion & system management
- [API Reference](../src/api/docs/README.md) - REST endpoints & integration examples
- [Project History](PROJECT_HISTORY.md) - Development timeline & achievements

### 📈 **For Operations**
- [API Health Monitoring](../src/api/docs/README.md#system-management) - System status & metrics
- [Performance Benchmarks](../src/tests/docs/README.md#performance-testing) - Load testing & optimization
- [Security Validation](../src/tests/docs/README.md#rbac-security-tests) - RBAC compliance testing

---

**📚 This document provides the high-level architecture overview. For detailed implementation, configuration, and usage instructions, refer to the component-specific documentation linked above.**

---

## 🔧 Environment Setup

### Services (Docker)
- **PostgreSQL 16 Alpine**: Runs on localhost:5435
  - User: `finbot`
  - Password: `finbot123`
  - Database: `finbot_db`
  - Schema: Auto-created by SQLAlchemy on startup

- **Qdrant Vector Database**: Runs on localhost:6333 (REST) + 6334 (gRPC)
  - Collections: `general`, `finance`, `engineering`, `marketing`, `hr`
  - Auto-initialized on backend startup

### Python Requirements
- See `pyproject.toml` for dependencies
- Install: `pip install -e .`

### Frontend
- Next.js 14 on localhost:3001
- Install: `cd frontend && npm install`
- Run: `npm run dev`