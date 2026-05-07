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

class OutputGuardrails:
    """Output guardrails for validating LLM responses"""
    
    def __init__(self):
        self.role_restricted_terms = {
            'finance': ['budget', 'revenue', 'profit', 'financial', 'earnings', 'investment'],
            'engineering': ['architecture', 'system', 'api', 'technical', 'infrastructure', 'database'],
            'marketing': ['campaign', 'brand', 'market', 'customer', 'advertising', 'promotion'],
            'hr': ['employee', 'salary', 'benefits', 'policy', 'organizational', 'personnel']
        }
    
    async def check_source_citation(self, response: str) -> GuardrailResult:
        """Check if response includes proper source citations"""
        
        # Look for source citation patterns
        citation_patterns = [
            r'\[.*\.(?:pdf|md|docx?)\]',  # [filename.pdf]
            r'source\s*:\s*.*\.(?:pdf|md|docx?)',  # Source: filename.pdf
            r'page\s+\d+',  # page 5
            r'(?:document|file|report):\s*\w+',  # Document: name
            r'according\s+to\s+.*\.(?:pdf|md|docx?)',  # According to file.pdf
        ]
        
        has_citation = any(
            re.search(pattern, response, re.IGNORECASE) 
            for pattern in citation_patterns
        )
        
        if not has_citation:
            return GuardrailResult(
                is_safe=False,
                violation_type="missing_citation",
                violation_message="⚠️ This response lacks proper source citations. Please verify information independently."
            )
        
        return GuardrailResult(is_safe=True)
    
    async def check_cross_role_leakage(self, response: str, user_role: str, accessible_collections: List[str]) -> GuardrailResult:
        """Check if response contains unauthorized information"""
        
        # Skip check for c_level (has access to everything)
        if user_role == 'c_level':
            return GuardrailResult(is_safe=True)
        
        response_lower = response.lower()
        violations = []
        
        # Check for content from restricted collections
        for collection, terms in self.role_restricted_terms.items():
            if collection not in accessible_collections:
                # Check if response contains terms from restricted collections
                for term in terms:
                    if term in response_lower:
                        violations.append(f"{collection} content: '{term}'")
        
        if violations:
            return GuardrailResult(
                is_safe=False,
                violation_type="cross_role_leakage",
                violation_message=f"⚠️ Response may contain unauthorized content: {', '.join(violations[:3])}. Please verify your access permissions."
            )
        
        return GuardrailResult(is_safe=True)
    
    async def check_grounding(self, response: str, retrieved_chunks: List[Dict[str, Any]]) -> GuardrailResult:
        """Check if response is grounded in retrieved context (optional)"""
        
        # Extract financial figures, dates, and specific claims from response
        financial_patterns = [
            r'\$[\d,]+(?:\.\d{2})?',  # Dollar amounts
            r'\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:million|billion|thousand)',  # Large numbers
            r'\d{1,2}%',  # Percentages
            r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4}',  # Dates
            r'\d{4}[-/]\d{1,2}[-/]\d{1,2}',  # Date formats
        ]
        
        response_claims = []
        for pattern in financial_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            response_claims.extend(matches)
        
        if not response_claims:
            return GuardrailResult(is_safe=True)
        
        # Check if claims appear in retrieved chunks
        chunk_content = ' '.join([
            chunk.get('content', '') + ' ' + str(chunk.get('metadata', {}))
            for chunk in retrieved_chunks
        ]).lower()
        
        ungrounded_claims = []
        for claim in response_claims:
            if claim.lower() not in chunk_content:
                ungrounded_claims.append(claim)
        
        if ungrounded_claims and len(ungrounded_claims) > len(response_claims) * 0.3:  # >30% ungrounded
            return GuardrailResult(
                is_safe=False,
                violation_type="potentially_ungrounded",
                violation_message="⚠️ This response may contain information not found in source documents. Please verify financial figures and claims independently."
            )
        
        return GuardrailResult(is_safe=True)
    
    async def validate_output(
        self, 
        response: str, 
        user_role: str, 
        accessible_collections: List[str],
        retrieved_chunks: Optional[List[Dict[str, Any]]] = None
    ) -> List[GuardrailResult]:
        """Run all output guardrails and return results"""
        
        checks = [
            self.check_source_citation(response),
            self.check_cross_role_leakage(response, user_role, accessible_collections)
        ]
        
        # Add grounding check if chunks provided
        if retrieved_chunks:
            checks.append(self.check_grounding(response, retrieved_chunks))
        
        results = await asyncio.gather(*checks, return_exceptions=True)
        
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Output guardrail check failed: {result}")
                continue
            valid_results.append(result)
        
        return valid_results


