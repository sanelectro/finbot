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
        "status": "running"
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}

# Import and include routers when they're created
# from src.api.chat import router as chat_router
# from src.api.admin import router as admin_router
# app.include_router(chat_router, prefix="/chat", tags=["chat"])
# app.include_router(admin_router, prefix="/admin", tags=["admin"])