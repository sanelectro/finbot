# Command Line Interface

**Typer-based CLI for document ingestion, testing, and system management**

The CLI provides a user-friendly interface for managing FinBot's document processing pipeline, vector database operations, and system testing.

## 🚀 Quick Start

```bash
# Run CLI from project root
python -m src.cli --help

# Check available commands
python -m src.cli ingest --help
python -m src.cli test --help

# Run specific subcommands
python -m src.cli ingest documents --help
python -m src.cli test search --help
```

## 📁 Components

### 📥 Ingestion (`ingest.py`)

**Batch document processing and vector storage**

#### Features
- **Recursive directory scanning** for document discovery
- **Collection-based organization** with automatic role assignment
- **File-specific ingestion** for incremental updates
- **Intelligent chunk replacement** - removes old chunks before adding new ones
- **Parallel processing** for large document sets
- **Progress tracking** with Rich console output
- **Error handling** with detailed reporting

#### Commands

##### Ingest Documents
```bash
# Ingest all documents (all collections)
python -m src.cli ingest documents

# Ingest specific collection
python -m src.cli ingest documents --collection engineering

# Ingest specific files only (incremental updates)
python -m src.cli ingest documents --files engineering/system_sla_report_2024.md

# Ingest multiple specific files (comma-separated)
python -m src.cli ingest documents --files "engineering/report1.md,finance/budget.pdf"

# Re-ingest modified file (removes old chunks, adds new ones)
python -m src.cli ingest documents --files marketing/campaign_update.md

# Recreate vector database (clears existing data)
python -m src.cli ingest documents --recreate

# Specify custom data directory
python -m src.cli ingest documents --data-dir /path/to/documents

# Check ingestion status
python -m src.cli ingest status

# Dry run (preview what would be processed)
python -m src.cli ingest documents --dry-run --collection engineering
```

#### Implementation Details
```python
class IngestionManager:
    async def ingest_documents(
        self, 
        data_dir: Path,
        collection_filter: Optional[Collection] = None,
        recreate_collection: bool = False
    ):
        # 1. Initialize vector store
        if recreate_collection:
            await self.vector_store.initialize_collection(recreate=True)
        
        # 2. Scan directories for documents
        documents = self.discover_documents(data_dir, collection_filter)
        
        # 3. Process documents in parallel
        processed_docs = await self.process_documents_parallel(documents)
        
        # 4. Store in vector database
        await self.vector_store.store_documents(processed_docs)
```

#### Collection Auto-Detection
```python
# Directory structure determines collection
data/
  ├── engineering/     → Collection: "engineering", Roles: ["engineering", "c_level"]
  ├── finance/         → Collection: "finance", Roles: ["finance", "c_level"]  
  ├── marketing/       → Collection: "marketing", Roles: ["marketing", "c_level"]
  └── general/         → Collection: "general", Roles: ["general", ..., "c_level"]
```

---

### 🧪 Testing (`test.py`)

**System validation and search accuracy testing**

#### Features
- **End-to-end testing** of document processing pipeline
- **Natural language query validation** with accuracy scoring
- **RBAC enforcement testing** across different user roles  
- **Performance benchmarking** for processing and search
- **Rich output formatting** with tables and progress bars

#### Commands

##### Available Test Commands
```bash
# Test document chunking
python -m src.cli test chunking

# Test embedding generation  
python -m src.cli test embeddings

# Test RBAC enforcement
python -m src.cli test rbac

# Test search functionality
python -m src.cli test search
```

##### Test Command Details
```bash
# Test RBAC enforcement across different roles
python -m src.cli test rbac

# Test search functionality with RBAC filtering
python -m src.cli test search

# Test document chunking process
python -m src.cli test chunking

# Test embedding generation
python -m src.cli test embeddings
```

#### Test Categories

##### 1. Document Processing Tests
```python
async def test_document_processing():
    """Test document chunking and metadata generation"""
    processor = HierarchicalDocumentProcessor()
    doc = await processor.process_document(test_file, "engineering")
    
    assert len(doc.chunks) > 0
    assert all(chunk.headings for chunk in doc.chunks)
    assert all(chunk.chunk_text for chunk in doc.chunks)
```

##### 2. Search Accuracy Tests  
```python
SEARCH_TEST_QUERIES = [
    ("What are our SLA compliance targets?", "engineering", 0.5),
    ("Q4 financial performance metrics", "finance", 0.6),
    ("Marketing campaign effectiveness", "marketing", 0.5),
]

async def test_search_accuracy():
    for query, role, min_score in SEARCH_TEST_QUERIES:
        results = await vector_store.search_with_rbac(query, role, limit=5)
        assert len(results) > 0
        assert results[0][1] >= min_score  # Score threshold
```

##### 3. RBAC Enforcement Tests
```python
async def test_rbac_enforcement():
    """Verify role-based access control"""
    # Engineering role should access engineering documents
    eng_results = await search_with_rbac("SLA metrics", "engineering")
    assert len(eng_results) > 0
    
    # Finance role should NOT access engineering documents
    fin_results = await search_with_rbac("SLA metrics", "finance") 
    assert len(fin_results) == 0
```

---

### 🎛️ Main CLI (`__main__.py`)

**Central command dispatcher and help system**

#### Command Structure
```python
app = typer.Typer(
    name="finbot-cli",
    help="FinBot CLI - Document processing and testing tools"
)

app.add_typer(ingest_app, name="ingest", help="Document ingestion commands")
app.add_typer(test_app, name="test", help="System testing commands")
```

#### Global Options
```bash
# Global CLI options
--config-file    # Custom configuration file
--log-level     # Logging verbosity (DEBUG, INFO, WARNING, ERROR)
--no-color      # Disable colored output  
--quiet         # Minimal output mode
--verbose       # Detailed output mode
```

## 📊 Rich Console Output

### Progress Tracking
```python
# Document processing with progress bar
with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
) as progress:
    task = progress.add_task("Processing documents...", total=len(documents))
    for doc in documents:
        await process_document(doc)
        progress.advance(task)
```

### Results Tables
```python
# Search results in formatted table
table = Table(title="Search Results")
table.add_column("Score", style="cyan", width=8)
table.add_column("Collection", style="green", width=12)  
table.add_column("Headings", style="yellow")
table.add_column("Content Preview", width=50)

for chunk, score in results:
    table.add_row(
        f"{score:.3f}",
        chunk.metadata.collection,
        " > ".join(chunk.headings[:2]),  # First 2 levels
        chunk.content[:50] + "..."
    )
```

### Status Panels
```python
# System status panel
panel = Panel(
    f"""[green]✅ Collection Status[/green]
    
📊 Vector Database: {collection_name}
📄 Total Documents: {doc_count}  
🔍 Total Chunks: {chunk_count}
⚡ Last Updated: {last_updated}
🔐 RBAC Status: Active""",
    title="FinBot System Status",
    border_style="green"
)
```

## 🔧 Usage Examples

### Complete Workflow
```bash
# 1. Fresh setup - recreate database and ingest all documents
python -m src.cli ingest documents --recreate

# 2. Check ingestion status
python -m src.cli ingest status

# 3. Test system functionality
python -m src.cli test search
python -m src.cli test rbac

# 4. Update a single modified file (incremental)
python -m src.cli ingest documents --files engineering/updated_report.md
# Update multiple files (comma-separated)
python -m src.cli ingest documents --files "engineering/doc1.md,finance/doc2.pdf"
# 5. Add new documents to existing collection
python -m src.cli ingest documents --collection finance --data-dir /new/finance/docs
```

### Development Workflow
```bash
# Test specific components after code changes
python -m src.cli test chunking
python -m src.cli test embeddings

# Update a single file during development
python -m src.cli ingest documents --files engineering/test_document.md

# Update multiple files during development
python -m src.cli ingest documents --files "engineering/test1.md,finance/test2.pdf"

# Validate search and RBAC functionality
python -m src.cli test search
python -m src.cli test rbac

# Preview ingestion without processing
python -m src.cli ingest documents --dry-run --collection engineering

# Preview specific file ingestion
python -m src.cli ingest documents --dry-run --files "finance/quarterly_report.pdf,engineering/system_report.md"
```

### Production Deployment
```bash
# Initial data load
python -m src.cli ingest documents --recreate

# Validate system components
python -m src.cli test search
python -m src.cli test rbac

# Check collection status
python -m src.cli ingest status
```

## 📈 Performance Metrics

### Ingestion Performance
```
📊 Document Processing Metrics:
• Processing Speed: ~54 chunks/second
• Memory Usage: < 500MB for 1000 documents
• Vector Storage: 100 chunks/batch (optimized)
• Error Rate: < 0.1% for clean documents
```

### Search Performance  
```
🔍 Search Performance Metrics:
• Query Response: < 100ms for 1000 chunks
• Embedding Generation: ~50ms per query
• RBAC Filter Time: < 5ms per query  
• Accuracy Score: 0.730+ for relevant queries
```

## 🚨 Error Handling

### Common Issues & Solutions

#### Document Processing Errors
```bash
# Issue: Unsupported file format
❌ Error: Cannot process file 'document.xyz'
✅ Solution: Ensure files are PDF, DOCX, or Markdown

# Issue: Access permissions
❌ Error: Permission denied accessing 'secure_doc.pdf'  
✅ Solution: Check file permissions and user access
```

#### Vector Database Errors
```bash
# Issue: Connection failed
❌ Error: Cannot connect to Qdrant at localhost:6333
✅ Solution: Start Qdrant server or update connection settings

# Issue: Collection not found
❌ Error: Collection 'finbot_documents' does not exist
✅ Solution: Run with --recreate flag to initialize database
```

#### RBAC Validation Errors
```bash
# Issue: No results for valid query
❌ Warning: No results found for role 'finance' 
✅ Check: Verify role has access to queried collection
✅ Solution: Use appropriate role or add role to collection access
```

## 🏗️ Architecture Benefits

### User Experience
- **Rich terminal UI** with colors, progress bars, and tables
- **Clear error messages** with actionable solutions
- **Flexible command structure** supporting various workflows
- **Comprehensive help system** with examples

### Developer Experience  
- **Modular command structure** - easy to add new commands
- **Async processing** - non-blocking operations throughout
- **Type safety** - full Pydantic validation on all inputs
- **Extensible architecture** - plugin system for custom commands

### Production Ready
- **Robust error handling** with graceful degradation
- **Performance monitoring** built into test commands
- **Configuration management** supporting multiple environments
- **Logging integration** with configurable verbosity levels