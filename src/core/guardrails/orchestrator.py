import re
import time
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from collections import defaultdict, deque
import asyncio
import logging
from datetime import datetime, timedelta

from langchain_community.llms import HuggingFacePipeline
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification

logger = logging.getLogger(__name__)

from .models import GuardrailResult, SessionInfo
from .input_guardrails import InputGuardrails
from .output_guardrails import OutputGuardrails

class GuardrailsOrchestrator:
    """Main guardrails orchestrator for the FinBot system"""
    
    def __init__(self):
        self.input_guardrails = InputGuardrails()
        self.output_guardrails = OutputGuardrails()
        logger.info("Guardrails system initialized successfully")
    
    async def validate_query(self, query: str, session_id: str = "default") -> Tuple[bool, str, Optional[str]]:
        """
        Validate input query through all guardrails
        
        Returns:
            Tuple[is_safe, processed_query, warning_message]
        """
        result, processed_query = await self.input_guardrails.validate_input(query, session_id)
        
        if not result.is_safe:
            return False, processed_query, result.violation_message
        
        warning_message = result.violation_message if result.violation_type == "warning" else None
        return True, processed_query, warning_message
    
    async def validate_response(
        self,
        response: str,
        user_role: str,
        accessible_collections: List[str],
        retrieved_chunks: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[str, List[str]]:
        """
        Validate output response through all guardrails
        
        Returns:
            Tuple[final_response, warnings]
        """
        results = await self.output_guardrails.validate_output(
            response, user_role, accessible_collections, retrieved_chunks
        )
        
        warnings = []
        final_response = response
        
        for result in results:
            if not result.is_safe and result.violation_message:
                warnings.append(result.violation_message)
        
        # Append warnings to response if any violations found
        if warnings:
            final_response = response + "\n\n" + "\n".join(warnings)
        
        return final_response, warnings
    
    def reset_session(self, session_id: str):
        """Reset session tracking for rate limiting"""
        if session_id in self.input_guardrails.session_tracker:
            del self.input_guardrails.session_tracker[session_id]
            logger.info(f"Session {session_id} reset")
    
    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get current session information"""
        if session_id in self.input_guardrails.session_tracker:
            session = self.input_guardrails.session_tracker[session_id]
            return {
                "query_count": session.query_count,
                "last_query_time": session.last_query_time,
                "queries_remaining": 20 - session.query_count
            }
        return {"query_count": 0, "last_query_time": 0, "queries_remaining": 20}