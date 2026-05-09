"""
FinBot FastAPI application
"""

import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.core.store.vector_store import VectorStore

logger = logging.getLogger(__name__)

# Create the FastAPI app
app = FastAPI(
    title="FinBot API",
    description="Advanced RAG application with RBAC for FinSolve Technologies",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

async def initialize_postgres() -> None:
    """Connect to PostgreSQL and create missing tables."""
    logger.info("[Startup] Step 1/4: Connect PostgreSQL and create missing tables")
    from src.core.database import db_manager

    db_success = await db_manager.initialize_database()
    if not db_success:
        raise RuntimeError("PostgreSQL initialization failed")

    logger.info("[Startup] PostgreSQL is ready")
    
async def preseed_demo_users() -> None:
    """Pre-seed demo users into the database."""
    logger.info("[Startup] Pre-seeding demo users")
    from src.core.database import db_manager

    db_success = await db_manager.seed_demo_users()
    if not db_success:
        logger.warning("Demo user seeding encountered issues. Please check logs.")
    else:
        logger.info("✅ Demo users seeded successfully")


async def initialize_qdrant() -> None:
    """Connect to Qdrant and ensure collections are available."""
    logger.info("[Startup] Step 2/4: Initialize Qdrant")
    vector_store = VectorStore()
    success = await vector_store.initialize_collection(recreate=False)
    if not success:
        raise RuntimeError("Qdrant initialization failed")

    logger.info("[Startup] Qdrant is ready")


async def preload_router() -> None:
    """Preload routing-related components."""
    logger.info("[Startup] Step 3/4: Preload router")
    # Placeholder for route/cache warm-up if needed.
    logger.info("[Startup] Router preload completed")


async def initialize_guardrails() -> None:
    """Initialize guardrails components."""
    logger.info("[Startup] Step 4/4: Initialize guardrails")
    # Placeholder for safety/validation guardrails initialization.
    logger.info("[Startup] Guardrails initialization completed")


async def preseed_demo_docs() -> None:
    """Seed demo documents via CRUD APIs after server startup completes."""
    try:
        # Wait for app startup completion so localhost API endpoints are reachable.
        await asyncio.sleep(2)
        from scripts.seed_demo_docs import seed_demo_docs

        logger.info("[Startup] Running post-start demo document seeding")
        result = await asyncio.to_thread(seed_demo_docs)
        if result != 0:
            logger.warning("Demo document seeding completed with non-zero exit code: %s", result)
        else:
            logger.info("✅ Demo documents seeded successfully")
    except Exception as exc:
        logger.warning("Demo document seeding failed: %s", exc)


@app.on_event("startup")
async def startup() -> None:
    """Run startup sequence in strict order before serving requests."""
    logger.info("Starting up FastAPI application...")
    await initialize_postgres()
    await preseed_demo_users()
    await initialize_qdrant()
    await preload_router()
    await initialize_guardrails()
    #asyncio.create_task(preseed_demo_docs())
    logger.info("✅ Application ready")


@app.on_event("shutdown")
async def shutdown() -> None:
    """Cleanly close resources on shutdown."""
    logger.info("Shutting down FastAPI application...")
    from src.core.database import db_manager
    await db_manager.close()
    logger.info("✅ Database connections closed")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js frontend
        "http://localhost:3001",  # Next.js frontend
        "http://127.0.0.1:3000",
        "http://localhost:3002",  # Alternative port
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
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

# Include users router
from src.api.users import router as users_router
app.include_router(users_router, prefix="/api/v1", tags=["users"])

# Include documents router
from src.api.documents import router as documents_router
app.include_router(documents_router, prefix="/api/v1", tags=["documents"])

# Import and include other routers when they're created
# from src.api.chat import router as chat_router
# from src.api.admin import router as admin_router
# app.include_router(chat_router, prefix="/api/v1/chat", tags=["chat"])
# app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])
