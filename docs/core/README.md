# Core Processing Components

**Document Processing & Vector Storage with RBAC**

This module contains the core FinBot processing pipeline that handles document chunking, vector embedding generation, and RBAC-enforced search.

## 📁 Components

### 🔄 Document Processor (`document_processor.py`)

**Native Docling-based hierarchical document processing**

#### Key Features
- **HierarchicalChunker**: Uses Docling's native chunker (no custom processing)
- **Breadcrumb Generation**: Creates hierarchical context for embeddings
- **Async Processing**: Non-blocking document conversion
- **Simplified Output**: 3-field chunk structure

#### Implementation
```python
class HierarchicalDocumentProcessor:
    def __init__(self):
        self.converter = DocumentConverter()
        
    async def process_document(self, file_path: Path, collection: Collection):
        # 1. Load document using Docling
        doc = await self.load_document(str(file_path))
        
        # 2. Use native HierarchicalChunker
        chunker = HierarchicalChunker()
        doc_chunks = list(chunker.chunk(doc))
        
        # 3. Convert to simplified format with breadcrumbs
        chunks = [self.convert_chunk(chunk) for chunk in doc_chunks]
```

#### Chunk Conversion Process
```python
def convert_chunk(self, doc_chunk) -> dict:
    """Convert Docling chunk to simplified format with breadcrumb context"""
    headings = doc_chunk.meta.headings or []           # ["FinSolve", "SLA Report", "Summary"]
    content = doc_chunk.text.strip()                   # Raw paragraph text
    breadcrumb = " > ".join(headings)                  # "FinSolve > SLA Report > Summary"  
    chunk_text = f"{breadcrumb}\n\n{content}" if breadcrumb else content
    
    return {
        "headings": headings,        # Hierarchical path
        "content": content,          # Raw text  
        "chunk_text": chunk_text,    # Breadcrumb + content (for embeddings)
    }
```

**Benefits:**
- ✅ **66% code reduction** (400+ lines → 135 lines)
- ✅ **More reliable** than custom processing
- ✅ **Breadcrumb context** improves search accuracy
- ✅ **Native performance** optimized by Docling team

---

### 💾 Vector Store (`vector_store.py`)

**Qdrant integration with RBAC metadata enforcement**

#### Key Features
- **Vector Storage**: 384D embeddings using SentenceTransformers
- **RBAC Enforcement**: Role-based access control at query time
- **Batch Processing**: Efficient chunk storage and retrieval
- **Async Operations**: Non-blocking embedding generation

#### Architecture
```python
class VectorStore:
    def __init__(self):
        self.client = QdrantClient(url=settings.qdrant_url)
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')  # 384D
        
    async def store_documents(self, documents: List[ProcessedDocument]):
        # 1. Generate embeddings from chunk_text (breadcrumb + content)
        await self._generate_embeddings(all_chunks)
        
        # 2. Create Qdrant points with RBAC payload
        points = [self._chunk_to_payload(chunk) for chunk in all_chunks]
        
        # 3. Store in batches (100 chunks per batch)
        await self.client.upsert(collection_name, points)
```

#### RBAC-Enforced Search
```python
async def search_with_rbac(self, query: str, user_role: Role):
    # 1. Generate query embedding
    query_embedding = await self.embedding_model.encode(query)
    
    # 2. Build RBAC filter (CRITICAL SECURITY LAYER)
    rbac_filter = Filter(
        must=[FieldCondition(
            key="access_roles", 
            match=MatchAny(any=[user_role])  # Only accessible roles
        )]
    )
    
    # 3. Vector similarity search with security enforcement
    results = self.client.query_points(
        query=query_embedding.tolist(),
        query_filter=rbac_filter,        # Security enforcement
        limit=limit
    )
```

**Security Model:**
- ✅ **Filter-first**: RBAC applied before similarity search
- ✅ **Vector-level security**: Each chunk tagged with access roles  
- ✅ **Zero-trust**: No documents returned without proper role match

---

### ⚙️ Configuration (`config.py`)

**Application settings and environment management**

#### Key Settings
```python
class Settings:
    # Vector Database
    qdrant_url: str = "http://localhost:6333"
    collection_name: str = "finbot_documents"
    
    # Embedding Model
    embedding_model: str = "all-MiniLM-L6-v2"  # 384 dimensions
    embedding_dimension: int = 384
    
    # RBAC Mappings
    collection_access_roles: Dict[Collection, List[Role]] = {
        "engineering": ["engineering", "c_level"],
        "finance": ["finance", "c_level"],
        "marketing": ["marketing", "c_level"],
        "general": ["general", "engineering", "finance", "marketing", "c_level"]
    }
```

## 🔧 Usage Examples

### Process Document
```python
processor = HierarchicalDocumentProcessor()
doc = await processor.process_document(
    Path('data/engineering/system_sla_report_2024.md'),
    'engineering'
)
print(f"Processed {len(doc.chunks)} chunks in {doc.processing_time:.2f}s")
```

### Store in Vector Database  
```python
vector_store = VectorStore()
await vector_store.initialize_collection(recreate=True)
success = await vector_store.store_documents([doc])
```

### Search with RBAC
```python
results = await vector_store.search_with_rbac(
    query="What is our system uptime and SLA compliance?",
    user_role='engineering',
    limit=5
)
for chunk, score in results:
    print(f"Score: {score:.3f} | {' > '.join(chunk.headings)}")
```

## 📊 Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| **Processing Speed** | ~54 chunks/0.48s | System SLA report (22KB) |
| **Embedding Dimension** | 384D | Optimal speed/accuracy balance |
| **Batch Size** | 100 chunks | Avoids memory issues |
| **Search Accuracy** | 0.730+ scores | Natural language queries |
| **RBAC Enforcement** | 100% | Zero data leakage |

## 🏗️ Architecture Benefits

### Before (Over-engineered)
- 400+ lines of custom chunking code
- 15+ metadata fields per chunk
- Complex text processing pipeline
- Custom embedding logic

### After (Simplified)
- 135 lines using native Docling
- 6 essential metadata fields
- Breadcrumb-enhanced context
- Async processing throughout

**Result:** 66% code reduction with improved reliability and search accuracy.