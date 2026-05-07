# FinBot Source Code Documentation

**Deep Component Documentation Structure**

This directory contains detailed technical documentation for FinBot's source code components. Each component has comprehensive documentation covering implementation details, architecture patterns, and development guidelines.

> **📖 For general project overview and getting started, see [../README.md](../README.md)**

---

## 📁 Component Overview

### 🔄 [Core Processing](core/docs/README.md)
- **Document Processor**: Docling-based hierarchical chunking
- **Vector Store**: Qdrant with RBAC enforcement  
- **Configuration**: Application settings and environment

**Key Features:**
- Native HierarchicalChunker implementation
- 384D vector embeddings with breadcrumb context
- Role-based access control at vector level

### 📊 [Data Models](models/docs/README.md)
- **DocumentChunk**: Simplified 3-field chunk structure
- **DocumentMetadata**: Essential 6-field RBAC metadata
- **Collection/Role**: Access control enums

**Design Principle:** Eliminated over-engineering (15+ → 6 fields)

### 🖥️ [Command Line Interface](cli/docs/README.md)
- **Ingestion**: Batch document processing
- **Testing**: System validation and search testing
- **Management**: Collection operations

**Usage:** `python -m src.cli <command>`

### 🌐 [API Endpoints](api/docs/README.md)
- **FastAPI**: RESTful API implementation
- **Search**: RBAC-enforced semantic search
- **Health**: System monitoring endpoints

**Status:** Ready for production deployment

### 🧪 [Testing Suite](tests/docs/README.md)
- **Integration Tests**: End-to-end workflow validation
- **Search Testing**: Natural language query validation
- **RBAC Testing**: Role-based access verification

**Coverage:** Complete system functionality

---

## 🚀 Quick Start

### 1. Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings
```

### 2. Initialize Vector Database
```bash
python -m src.cli ingest --recreate
```

### 3. Test System
```bash
python src/tests/test_ingestion_and_search.py
```

### 4. Start API Server
```bash
python main.py
```

---

## 📈 Architecture Achievements

✅ **Eliminated over-engineering**: 15+ metadata fields → 6 essential fields  
✅ **Native chunking**: Custom processing → Docling HierarchicalChunker  
✅ **Enhanced search**: Keyword matching → Breadcrumb-enhanced semantic search  
✅ **RBAC security**: Vector-level access control with zero data leakage  
✅ **Production ready**: Async processing, batch operations, comprehensive testing  

---

## 🔧 Development Workflow

1. **Code changes** → Update component-specific documentation
2. **New features** → Add tests in `tests/` directory  
3. **API changes** → Update `api/docs/` documentation
4. **Model changes** → Update `models/docs/` schemas

---

## 📚 Detailed Documentation

- [Core Processing Documentation](core/docs/README.md) - Document chunking and vector storage
- [Data Models Documentation](models/docs/README.md) - Schema definitions and validation
- [CLI Documentation](cli/docs/README.md) - Command-line interface usage
- [API Documentation](api/docs/README.md) - REST endpoint specifications  
- [Testing Documentation](tests/docs/README.md) - Test methodology and validation

---

## 📖 Related Documentation

- **[../README.md](../README.md)** - Main project documentation and overview
- **[../QUICKSTART.md](../QUICKSTART.md)** - 5-minute setup guide
- **[../ASSIGNMENT_COMPLETION_SUMMARY.md](../ASSIGNMENT_COMPLETION_SUMMARY.md)** - Component requirements verification
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture diagrams
- **[TECHNICAL_DOCUMENTATION.md](TECHNICAL_DOCUMENTATION.md)** - Complete technical reference
- **[PROJECT_HISTORY.md](PROJECT_HISTORY.md)** - Development journey and decisions

---

*For high-level project information and features, start with [../README.md](../README.md)*
