# API Endpoints

**FastAPI-based REST API for document management, user management, and semantic search with RBAC**

The API provides RESTful endpoints for:
- Document upload, processing, and management
- User authentication and role-based access
- Semantic search with RBAC enforcement
- System health monitoring

## 🚀 Quick Start

```bash
# Prerequisites: Docker services running
docker compose up -d

# Start backend
PYTHONPATH=. python main.py

# API will be available at:
# - HTTP: http://localhost:8000
# - Swagger UI: http://localhost:8000/docs
# - ReDoc: http://localhost:8000/redoc
# - Health: http://localhost:8000/health
```

## 📋 Core Endpoints

### 📄 **Document Management** (`src/api/documents.py`)

#### Upload Document
```http
POST /api/documents/upload
Content-Type: multipart/form-data

Parameters:
  - file: (required) File to upload
  - collection: (required) Collection (general, finance, engineering, marketing, hr)
  - original_filename: (optional) Display name for document
  - role_access: (optional) JSON array of roles or single role
    Example: ["finance", "c_level"] or "finance"
```

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "original_filename": "Q3_Report.pdf",
  "collection": "finance",
  "role_access": ["finance", "c_level"],
  "upload_status": "processing",
  "embedding_status": "pending",
  "created_at": "2026-05-07T10:30:00.000000"
}
```

#### Get Documents
```http
GET /api/documents?page=1&page_size=10&upload_status=completed
```

**Response:**
```json
{
  "items": [
    {
      "id": "doc-id",
      "original_filename": "Q3_Report.pdf",
      "collection": "finance",
      "role_access": ["finance", "c_level"],
      "upload_status": "completed",
      "embedding_status": "completed",
      "created_at": "2026-05-07T10:30:00.000000"
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 10
}
```

#### Update Document
```http
PUT /api/documents/{document_id}
Content-Type: application/json

{
  "original_filename": "Updated_Name.pdf",
  "collection": "finance",
  "role_access": ["finance", "c_level"]
}
```

#### Delete Document
```http
DELETE /api/documents/{document_id}
```

---

### 👥 **User Management** (`src/api/users.py`)

#### List Users
```http
GET /api/users?page=1&page_size=10
```

#### Create User
```http
POST /api/users
Content-Type: application/json

{
  "email": "user@finbot.com",
  "role": "finance"
}
```

All users created with default password `demo123`

#### Update User
```http
PUT /api/users/{user_id}
Content-Type: application/json

{
  "email": "newemail@finbot.com",
  "role": "engineering"
}
```

#### Reset User Password
```http
POST /api/users/{user_id}/reset-password
```

Returns user with password reset to `demo123`

---

### 🔍 **Search** (`src/api/search.py`)

#### Semantic Search with RBAC
```http
POST /api/v1/search
Content-Type: application/json

{
  "query": "What are our Q3 revenue targets?",
  "user_role": "finance"
}
```

**Response:**
```json
{
  "query": "What are our Q3 revenue targets?",
  "user_role": "finance",
  "answer": "Based on FinSolve's Q3 targets...",
  "score": 0.92,
  "response_time_ms": 234,
  "guardrail_triggered": false
}
```

---

### 📊 **System Management**

#### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-05-07T10:35:00.000000",
  "services": {
    "postgresql": "connected",
    "qdrant": "connected",
    "guardrails": "active"
  }
}
```

#### Root Endpoint
```http
GET /
```

Returns: `{"message": "FinBot API v1.0.0"}`

---

## 🏗️ **Service Architecture**

```
FastAPI Main (main.py)
├── PostgreSQL (localhost:5435)
│   ├── users table
│   └── documents table
├── Qdrant (localhost:6333)
│   ├── general collection
│   ├── finance collection
│   ├── engineering collection
│   ├── marketing collection
│   └── hr collection
└── Endpoints:
    ├── /api/documents/* (document.py)
    ├── /api/users/* (users.py)
    ├── /api/v1/search (search.py)
    ├── /health
    └── /
```

---

## 🔐 **RBAC (Role-Based Access Control)**

### Supported Roles
```python
UserRole = {
    "employee": ["general"],
    "finance": ["general", "finance"],
    "engineering": ["general", "engineering"],
    "marketing": ["general", "marketing"],
    "hr": ["general", "hr"],
    "c_level": ["general", "finance", "engineering", "marketing", "hr"]
}
```

### Access Control
- **Employee**: Only access General documents
- **Department Roles**: Access own collection + General
- **C-Level**: Full access to all collections
- Vector search automatically filters by user role

---

## 🛡️ **Error Handling**

### Common Responses
```
200 OK - Success
201 Created - Resource created
400 Bad Request - Invalid input
401 Unauthorized - Missing/invalid credentials
403 Forbidden - RBAC denied
404 Not Found - Resource not found
422 Unprocessable Entity - Validation error
500 Internal Server Error - Server error
```

---

## 📁 **File Structure**

```
src/api/
├── main.py           # FastAPI app initialization
├── documents.py      # Document CRUD endpoints
├── users.py          # User management endpoints
├── search.py         # Search endpoint
└── README.md         # This file
```
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