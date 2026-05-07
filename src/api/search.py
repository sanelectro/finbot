"""
FinBot RAG API endpoint with intelligent response generation
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
import logging
import time

from src.core.rag.rag_system import FinBotRAGSystem
from src.models.document import Role

logger = logging.getLogger(__name__)

# Create the search router
router = APIRouter()

# Response models
class SourceCitation(BaseModel):
    """Source citation with document and page info"""
    document_name: str
    page_number: Optional[int] = None
    section: Optional[str] = None
    relevance_score: Optional[float] = None

class RAGResponse(BaseModel):
    """Complete RAG response model with all assignment requirements"""
    query: str
    user_role: str
    answer: str
    score: float
    response_time_ms: float
    
    # Assignment-required fields
    semantic_route: Optional[str] = Field(None, description="The semantic route selected for the query")
    accessible_collections: List[str] = Field(default_factory=list, description="Collections user has access to")
    source_citations: List[SourceCitation] = Field(default_factory=list, description="Sources with document and page numbers")
    
    # Guardrail and RBAC information
    warnings: Optional[List[str]] = Field(default_factory=list, description="Guardrail warning banners")
    rbac_message: Optional[str] = Field(None, description="RBAC denial or informative message")
    guardrail_triggered: bool = Field(False, description="Whether any guardrail was triggered")
    guardrail_info: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Detailed guardrail info")
    
class SessionInfo(BaseModel):
    """Session information for rate limiting"""
    query_count: int
    queries_remaining: int
    session_id: str

# Dependency for RAG system
async def get_rag_system() -> FinBotRAGSystem:
    """Get RAG system instance"""
    return FinBotRAGSystem()

@router.get("/search", response_model=RAGResponse)
async def search_documents(
    q: str = Query(..., description="Search query", min_length=1, max_length=500),
    role: Role = Query(..., description="User role for RBAC enforcement"),
    session_id: str = Query("default", description="Session ID for rate limiting"),
    limit: int = Query(5, description="Maximum documents for context", ge=1, le=10),
    rag_system: FinBotRAGSystem = Depends(get_rag_system)
):
    """
    FinBot intelligent search with RAG response generation and guardrails.
    
    This endpoint uses the complete RAG pipeline with integrated guardrails
    to provide safe, intelligent, context-aware responses.
    
    Features:
    - Input guardrails: Off-topic detection, prompt injection, PII scrubbing
    - Semantic query routing to appropriate collections
    - RBAC enforcement at the vector level  
    - System prompt-driven response generation
    - Output guardrails: Citation enforcement, cross-role leakage detection
    - Session-based rate limiting (20 queries per session)
    - Professional answers with source attribution
    - Structured data extraction for specific query types
    """
    try:
        start_time = time.time()
        
        logger.info(f"Processing FinBot query: '{q}' for role: {role} (session: {session_id})")
        
        # Use the RAG system's complete processing pipeline with guardrails
        rag_result = await rag_system.process_query(
            query=q,
            user_role=role,
            session_id=session_id,
            limit=limit
        )
        
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Create enhanced API response with all assignment requirements
        response = RAGResponse(
            query=rag_result["query"],
            user_role=rag_result["user_role"],
            answer=rag_result["answer"],
            score=rag_result["confidence"],
            response_time_ms=response_time,
            
            # Assignment-required fields
            semantic_route=rag_result.get("semantic_route"),
            accessible_collections=rag_result.get("accessible_collections", []),
            source_citations=[
                SourceCitation(
                    document_name=citation["document_name"],
                    page_number=citation.get("page_number"),
                    section=citation.get("section"),
                    relevance_score=citation.get("relevance_score")
                ) for citation in rag_result.get("source_citations", [])
            ],
            
            # Guardrail and RBAC information
            warnings=rag_result.get("warnings", []),
            rbac_message=rag_result.get("rbac_message"),
            guardrail_triggered=bool(rag_result.get("warnings", []) or rag_result.get("guardrail_info", {}).get("input_blocked", False)),
            guardrail_info=rag_result.get("guardrail_info", {})
        )
        
        logger.info(f"FinBot response generated in {response_time:.1f}ms with score {response.score:.3f}")
        
        # Log guardrail information for monitoring
        guardrail_info = rag_result.get("guardrail_info", {})
        if guardrail_info.get("input_blocked"):
            logger.warning(f"Query blocked by input guardrails: {q}")
        if rag_result.get("warnings"):
            logger.info(f"Guardrail warnings: {', '.join(rag_result['warnings'])}")
        
        return response
        
    except Exception as e:
        logger.error(f"FinBot API error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"FinBot processing failed: {str(e)}"
        )


@router.get("/session/{session_id}/info", response_model=SessionInfo)
async def get_session_info(
    session_id: str,
    rag_system: FinBotRAGSystem = Depends(get_rag_system)
):
    """Get session information for rate limiting monitoring"""
    try:
        info = rag_system.get_session_info(session_id)
        return SessionInfo(
            session_id=session_id,
            query_count=info.get("query_count", 0),
            queries_remaining=info.get("queries_remaining", 20)
        )
    except Exception as e:
        logger.error(f"Session info error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get session info")


@router.post("/session/{session_id}/reset")
async def reset_session(
    session_id: str,
    rag_system: FinBotRAGSystem = Depends(get_rag_system)
):
    """Reset session for rate limiting (useful for testing)"""
    try:
        rag_system.reset_session(session_id)
        return {"message": f"Session {session_id} reset successfully"}
    except Exception as e:
        logger.error(f"Session reset error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to reset session")