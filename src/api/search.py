"""
FinBot RAG API endpoint with intelligent response generation
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
import logging
import time

from src.core.rag_system import FinBotRAGSystem
from src.models.document import Role

logger = logging.getLogger(__name__)

# Create the search router
router = APIRouter()

# Response models
class RAGResponse(BaseModel):
    """Simplified RAG response model with search score"""
    query: str
    user_role: str
    answer: str
    score: float
    response_time_ms: float

# Dependency for RAG system
async def get_rag_system() -> FinBotRAGSystem:
    """Get RAG system instance"""
    return FinBotRAGSystem()

@router.get("/search", response_model=RAGResponse)
async def search_documents(
    q: str = Query(..., description="Search query", min_length=1, max_length=500),
    role: Role = Query(..., description="User role for RBAC enforcement"),
    limit: int = Query(5, description="Maximum documents for context", ge=1, le=10),
    rag_system: FinBotRAGSystem = Depends(get_rag_system)
):
    """
    FinBot intelligent search with RAG response generation.
    
    This endpoint uses the complete RAG pipeline to provide intelligent, 
    context-aware responses instead of raw document chunks.
    
    Features:
    - Semantic query routing to appropriate collections
    - RBAC enforcement at the vector level  
    - System prompt-driven response generation
    - Professional answers with source attribution
    - Structured data extraction for specific query types
    """
    try:
        start_time = time.time()
        
        logger.info(f"Processing FinBot query: '{q}' for role: {role}")
        
        # Use the RAG system's complete processing pipeline
        rag_result = await rag_system.process_query(
            query=q,
            user_role=role,
            limit=limit
        )
        
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Create simplified API response
        response = RAGResponse(
            query=rag_result["query"],
            user_role=rag_result["user_role"],
            answer=rag_result["answer"],
            score=rag_result["confidence"],
            response_time_ms=response_time
        )
        
        logger.info(f"FinBot response generated in {response_time:.1f}ms with score {response.score:.3f}")
        
        return response
        
    except Exception as e:
        logger.error(f"FinBot API error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"FinBot processing failed: {str(e)}"
        )