# Data Models & Schemas

**Simplified Pydantic models for document processing and RBAC**

This module defines the core data structures used throughout FinBot, emphasizing simplicity and RBAC enforcement.

## 🎯 Design Philosophy

**Eliminated Over-engineering:**
- **Before**: 15+ metadata fields with complex nested structures
- **After**: 6 essential fields focused on RBAC and document tracking
- **Result**: 60% reduction in complexity while maintaining all necessary functionality

## 📊 Core Models

### 📄 DocumentChunk

**Simplified 3-field structure for processed document chunks**

```python
class DocumentChunk(BaseModel):
    headings: List[str]           # Hierarchical breadcrumb path
    content: str                  # Raw paragraph text
    chunk_text: str              # Breadcrumb + content (for embeddings)
    metadata: DocumentMetadata    # RBAC and tracking info
    embedding: Optional[List[float]] = None  # 384D vector (populated during storage)
```

**Field Descriptions:**
- **`headings`**: Hierarchical document structure from Docling
  - Example: `["FinSolve Technologies", "SLA Report", "Executive Summary"]`
  - Used to generate breadcrumb navigation context
  
- **`content`**: Raw text content of the chunk
  - Example: `"**2024 Performance Highlights:** All services met SLA targets..."`
  - Clean paragraph text without formatting
  
- **`chunk_text`**: Formatted text for embedding generation
  - Example: `"FinSolve Technologies > SLA Report > Executive Summary\n\n**2024 Performance Highlights:**..."`
  - Combines breadcrumb context with content for better semantic search

### 🔐 DocumentMetadata

**Essential 6-field RBAC metadata (simplified from 15+ fields)**

```python
class DocumentMetadata(BaseModel):
    collection: Collection               # Document categorization
    access_roles: List[Role]            # RBAC enforcement
    source_document: str                # Filename for tracking
    document_path: str                  # Full file path
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

**RBAC Fields:**
- **`collection`**: Categorizes documents for access control
- **`access_roles`**: List of roles that can access this chunk

**Tracking Fields:**
- **`source_document`**: Original filename (e.g., `"system_sla_report_2024.md"`)
- **`document_path`**: Full path for audit trail
- **`chunk_id`**: Unique identifier for chunk tracking
- **`created_at`**: Processing timestamp for versioning

### 🗂️ ProcessedDocument

**Container for document processing results**

```python
class ProcessedDocument(BaseModel):
    source_path: Path                    # Original file location
    collection: Collection               # Document categorization
    access_roles: List[Role]            # Default access roles
    chunks: List[DocumentChunk]         # All processed chunks
    file_size: int                      # Original file size in bytes
    processing_time: float              # Processing duration in seconds
    total_pages: Optional[int] = None   # Page count (if applicable)
```

**Processing Metrics:**
- Tracks performance characteristics
- Enables processing optimization
- Provides audit information

## 🏷️ Enums & Types

### Collection Categories
```python
class Collection(str, Enum):
    GENERAL = "general"         # Public access documents
    FINANCE = "finance"         # Financial reports and data
    ENGINEERING = "engineering" # Technical documentation
    MARKETING = "marketing"     # Marketing materials
```

### RBAC Roles
```python
class Role(str, Enum):
    GENERAL = "general"         # Basic access level
    FINANCE = "finance"         # Financial team access
    ENGINEERING = "engineering" # Technical team access  
    MARKETING = "marketing"     # Marketing team access
    C_LEVEL = "c_level"        # Executive access (all collections)
```

### Access Control Matrix
```python
COLLECTION_ACCESS_ROLES = {
    "general": ["general", "finance", "engineering", "marketing", "c_level"],
    "finance": ["finance", "c_level"], 
    "engineering": ["engineering", "c_level"],
    "marketing": ["marketing", "c_level"]
}
```

## 🔄 Model Lifecycle

### 1. Document Processing
```python
# Create chunk from Docling output
chunk = DocumentChunk(
    headings=["FinSolve", "SLA Report", "Executive Summary"],
    content="**2024 Performance Highlights:** All services met SLA targets...",
    chunk_text="FinSolve > SLA Report > Executive Summary\n\n**2024 Performance Highlights:**...",
    metadata=DocumentMetadata(
        collection="engineering",
        access_roles=["engineering", "c_level"],
        source_document="system_sla_report_2024.md",
        document_path="data/engineering/system_sla_report_2024.md"
    )
)
```

### 2. Vector Storage
```python
# Generate embedding and store
chunk.embedding = await generate_embedding(chunk.chunk_text)
payload = {
    "content": chunk.content,
    "chunk_text": chunk.chunk_text,
    "headings": chunk.headings,
    "collection": chunk.metadata.collection,
    "access_roles": chunk.metadata.access_roles,
    # ... other metadata fields
}
```

### 3. RBAC-Filtered Retrieval
```python
# Search with role enforcement
results = await search_with_rbac(
    query="system performance metrics",
    user_role="engineering"  # Can access engineering + c_level documents
)
```

## 📈 Validation & Constraints

### Field Validation
```python
class DocumentMetadata(BaseModel):
    collection: Collection  # Must be valid enum value
    access_roles: List[Role] = Field(min_items=1)  # At least one role required
    source_document: str = Field(min_length=1)     # Non-empty filename
    document_path: str = Field(min_length=1)       # Valid path required
    chunk_id: str = Field(regex=r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')
```

### RBAC Validation
- Access roles must be valid enum values
- At least one access role must be specified
- Collection must match valid categories
- C-level role provides access to all collections

## 🚀 Usage Examples

### Create Document Chunk
```python
chunk = DocumentChunk(
    headings=["Financial Report", "Q4 Results"],
    content="Revenue increased by 15% in Q4 2024...", 
    chunk_text="Financial Report > Q4 Results\n\nRevenue increased by 15%...",
    metadata=DocumentMetadata(
        collection="finance",
        access_roles=["finance", "c_level"],
        source_document="q4_financial_report.pdf"
    )
)
```

### Validate Access Rights
```python
def can_access_chunk(chunk: DocumentChunk, user_role: Role) -> bool:
    return user_role in chunk.metadata.access_roles
```

### Filter by Collection
```python
engineering_chunks = [
    chunk for chunk in all_chunks 
    if chunk.metadata.collection == "engineering"
]
```

## 🏗️ Architecture Benefits

### Simplified Structure
- **3 core fields** instead of complex nested objects
- **Clear separation** between content and metadata
- **Type safety** through Pydantic validation
- **Enum constraints** prevent invalid values

### RBAC Integration
- **Built-in access control** at the data model level
- **Zero-trust security** - every chunk has explicit permissions
- **Scalable role system** - easy to add new roles/collections
- **Audit-friendly** - complete tracking of access patterns

### Performance Optimized
- **Minimal memory footprint** - eliminated unnecessary fields
- **Fast serialization** - simple structure for JSON/DB operations  
- **Efficient indexing** - RBAC fields optimized for database queries
- **Vector-ready** - embedding field designed for similarity search