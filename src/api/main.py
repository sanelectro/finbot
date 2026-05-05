"""
FinBot FastAPI application
"""

from fastapi import FastAPI
from src.core.config import settings

# Create the FastAPI app
app = FastAPI(
    title="FinBot API",
    description="Advanced RAG application with RBAC for FinSolve Technologies",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "FinBot API - Advanced RAG with RBAC",
        "version": "0.1.0",
        "status": "running",
        "features": [
            "Semantic Query Routing",
            "Role-Based Access Control (RBAC)",
            "Hierarchical Document Processing",
            "Vector Similarity Search"
        ]
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}

# Include search router
from src.api.search import router as search_router
app.include_router(search_router, prefix="/api/v1", tags=["search"])

# Import and include other routers when they're created
# from src.api.chat import router as chat_router
# from src.api.admin import router as admin_router
# app.include_router(chat_router, prefix="/api/v1/chat", tags=["chat"])
# app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])