# API Endpoints

**FastAPI-based REST API for document search and system management**

The API provides RESTful endpoints for semantic document search with RBAC enforcement, system health monitoring, and administrative operations.

## 🚀 Quick Start

```bash
# Start API server
python main.py

# API will be available at:
# - HTTP: http://localhost:8000
# - Docs: http://localhost:8000/docs
# - OpenAPI: http://localhost:8000/openapi.json
```

## 🌐 API Structure

### Base Configuration
```python
app = FastAPI(
    title="FinBot API",
    description="Advanced RAG application with RBAC for FinSolve Technologies",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)
```

### CORS & Middleware
```python
# CORS configuration for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 📋 Core Endpoints

### 🔍 Search Endpoints

#### Semantic Search with RBAC
```http
POST /search
Content-Type: application/json

{
  "query": "What are our SLA compliance targets?",
  "user_role": "engineering", 
  "limit": 5,
  "collection_filter": "engineering",
  "score_threshold": 0.3
}
```

**Response:**
```json
{
  "query": "What are our SLA compliance targets?",
  "results": [
    {
      "chunk": {
        "headings": ["FinSolve Technologies", "SLA Report", "Target Definitions"],
        "content": "**SLA Compliance Definition:** Monthly uptime ≥ target...",
        "chunk_text": "FinSolve Technologies > SLA Report > Target Definitions\n\n**SLA Compliance...",
        "metadata": {
          "collection": "engineering",
          "access_roles": ["engineering", "c_level"],
          "source_document": "system_sla_report_2024.md",
          "document_path": "data/engineering/system_sla_report_2024.md",
          "chunk_id": "550e8400-e29b-41d4-a716-446655440000",
          "created_at": "2026-05-05T01:40:44.162340"
        }
      },
      "score": 0.785
    }
  ],
  "total_results": 3,
  "processing_time_ms": 89,
  "rbac_applied": true
}
```

#### Request Models
```python
class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000, description="Natural language search query")
    user_role: Role = Field(description="User role for RBAC enforcement") 
    limit: int = Field(default=10, ge=1, le=100, description="Maximum results to return")
    collection_filter: Optional[Collection] = Field(default=None, description="Filter by collection")
    score_threshold: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum similarity score")

class SearchResponse(BaseModel):
    query: str
    results: List[ChunkResult]
    total_results: int
    processing_time_ms: int
    rbac_applied: bool
```

#### Advanced Search
```http
POST /search/advanced
Content-Type: application/json

{
  "queries": [
    "SLA compliance targets",
    "system performance metrics", 
    "error rate analysis"
  ],
  "user_role": "engineering",
  "combine_results": true,
  "deduplicate": true
}
```

---

### 📊 System Management

#### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-05-05T07:35:12.123456",
  "version": "1.0.0",
  "components": {
    "vector_database": {
      "status": "healthy", 
      "collection": "finbot_documents",
      "total_points": 1247,
      "last_updated": "2026-05-05T07:30:00.000000"
    },
    "embedding_model": {
      "status": "healthy",
      "model": "all-MiniLM-L6-v2", 
      "dimensions": 384,
      "load_time_ms": 1200
    },
    "rbac_system": {
      "status": "active",
      "collections": ["general", "finance", "engineering", "marketing"],
      "roles": ["general", "finance", "engineering", "marketing", "c_level"]
    }
  }
}
```

#### System Statistics
```http
GET /stats
```

**Response:**
```json
{
  "database": {
    "total_documents": 156,
    "total_chunks": 1247,
    "collections": {
      "engineering": 542,
      "finance": 398, 
      "marketing": 207,
      "general": 100
    }
  },
  "performance": {
    "avg_search_time_ms": 87,
    "avg_embedding_time_ms": 45,
    "cache_hit_rate": 0.78
  },
  "rbac": {
    "total_access_checks": 15420,
    "denied_requests": 89,
    "success_rate": 0.994
  }
}
```

---

### 🔐 RBAC & Collections

#### List Collections
```http
GET /collections
```

**Response:**
```json
{
  "collections": [
    {
      "name": "engineering",
      "access_roles": ["engineering", "c_level"],
      "document_count": 42,
      "chunk_count": 542,
      "last_updated": "2026-05-05T07:30:00.000000"
    },
    {
      "name": "finance", 
      "access_roles": ["finance", "c_level"],
      "document_count": 28,
      "chunk_count": 398,
      "last_updated": "2026-05-05T07:25:00.000000"
    }
  ]
}
```

#### Check User Access
```http
POST /rbac/check-access
Content-Type: application/json

{
  "user_role": "engineering",
  "collection": "finance"
}
```

**Response:**
```json
{
  "user_role": "engineering",
  "collection": "finance", 
  "has_access": false,
  "reason": "Role 'engineering' not in collection access list ['finance', 'c_level']"
}
```

## 🔒 Authentication & Security

### API Key Authentication (Future)
```python
# Planned implementation
async def verify_api_key(api_key: str = Header()):
    if api_key not in valid_api_keys:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key
```

### RBAC Enforcement
```python
@app.post("/search", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    api_key: str = Depends(verify_api_key)  # Future auth
):
    # RBAC is enforced at the vector store level
    results = await vector_store.search_with_rbac(
        query=request.query,
        user_role=request.user_role,  # Critical security parameter
        limit=request.limit,
        collection_filter=request.collection_filter,
        score_threshold=request.score_threshold
    )
```

### Rate Limiting (Future)
```python
# Planned implementation using slowapi
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=lambda request: request.client.host)

@app.post("/search")
@limiter.limit("100/minute")  # 100 requests per minute per IP
async def search_documents(request: Request, search_request: SearchRequest):
    pass
```

## 📋 Response Models

### Success Response Structure
```python
class BaseResponse(BaseModel):
    success: bool = True
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    processing_time_ms: int

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    error_code: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Optional[Dict[str, Any]] = None
```

### Chunk Result Model
```python
class ChunkResult(BaseModel):
    chunk: DocumentChunk
    score: float = Field(ge=0.0, le=1.0)
    
class SearchResponse(BaseResponse):
    query: str
    results: List[ChunkResult]
    total_results: int
    rbac_applied: bool
```

## 🚨 Error Handling

### HTTP Status Codes
```python
# Success responses
200: "OK - Request successful"
201: "Created - Resource created successfully"

# Client error responses  
400: "Bad Request - Invalid request parameters"
401: "Unauthorized - Authentication required"  
403: "Forbidden - Insufficient permissions"
404: "Not Found - Resource not found"
422: "Unprocessable Entity - Validation error"
429: "Too Many Requests - Rate limit exceeded"

# Server error responses
500: "Internal Server Error - Unexpected server error"
503: "Service Unavailable - System temporarily unavailable"
```

### Error Response Examples
```json
// Validation Error
{
  "success": false,
  "error": "Query must be between 1 and 1000 characters",
  "error_code": "VALIDATION_ERROR",
  "timestamp": "2026-05-05T07:35:12.123456",
  "details": {
    "field": "query",
    "provided_length": 1500,
    "max_length": 1000
  }
}

// RBAC Error
{
  "success": false,
  "error": "Access denied for role 'finance' to collection 'engineering'",
  "error_code": "RBAC_ACCESS_DENIED", 
  "timestamp": "2026-05-05T07:35:12.123456",
  "details": {
    "user_role": "finance",
    "requested_collection": "engineering",
    "allowed_roles": ["engineering", "c_level"]
  }
}
```

## 🔧 Usage Examples

### Python Client
```python
import httpx
import asyncio

async def search_documents():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/search",
            json={
                "query": "What are our Q4 performance metrics?",
                "user_role": "engineering",
                "limit": 5,
                "score_threshold": 0.3
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"Found {data['total_results']} results")
            for result in data['results']:
                print(f"Score: {result['score']:.3f}")
                print(f"Headings: {' > '.join(result['chunk']['headings'])}")
                print(f"Content: {result['chunk']['content'][:100]}...")
                print("-" * 50)
```

### cURL Examples
```bash
# Basic search
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SLA compliance targets",
    "user_role": "engineering",
    "limit": 3
  }'

# Health check
curl -X GET "http://localhost:8000/health"

# System statistics
curl -X GET "http://localhost:8000/stats"
```

### JavaScript/Fetch
```javascript
async function searchDocuments(query, userRole) {
  try {
    const response = await fetch('http://localhost:8000/search', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: query,
        user_role: userRole,
        limit: 5,
        score_threshold: 0.3
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return data.results;
  } catch (error) {
    console.error('Search failed:', error);
    return [];
  }
}
```

## 📈 Performance Monitoring

### Built-in Metrics
```python
# Automatic timing middleware
@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

### Performance Targets
```
🎯 API Performance Targets:
• Search Endpoint: < 200ms response time
• Health Check: < 50ms response time  
• Embedding Generation: < 100ms per query
• RBAC Validation: < 10ms per request
• Throughput: > 100 requests/second
```

## 🚀 Deployment

### Production Configuration
```python
# production settings
app = FastAPI(
    title="FinBot API",
    docs_url=None if settings.environment == "production" else "/docs",
    redoc_url=None if settings.environment == "production" else "/redoc"
)

# Security headers
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff" 
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response
```

### Docker Deployment
```dockerfile
FROM python:3.11-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src/ /app/src/
WORKDIR /app
EXPOSE 8000
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Load Balancer Configuration
```nginx
upstream finbot_api {
    server localhost:8001;
    server localhost:8002; 
    server localhost:8003;
}

server {
    listen 80;
    location / {
        proxy_pass http://finbot_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🏗️ Architecture Benefits

### API Design
- **RESTful standards** with clear resource endpoints
- **Comprehensive validation** using Pydantic models
- **Consistent response format** for all endpoints
- **Rich error information** with actionable details

### Security Features
- **RBAC enforcement** at the API level
- **Input validation** preventing injection attacks
- **Structured error responses** avoiding information leakage
- **Future-ready authentication** with API key support

### Performance Optimized
- **Async throughout** - non-blocking operations
- **Response caching** for frequently accessed data
- **Connection pooling** for database operations
- **Efficient serialization** with optimized JSON responses