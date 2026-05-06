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

class InputGuardrails:
    """Input guardrails for detecting and blocking harmful queries"""
    
    def __init__(self):
        self.session_tracker: Dict[str, SessionInfo] = {}
        self._initialize_models()
        
        # Business domain keywords for off-topic detection
        self.business_domains = {
            'finance', 'financial', 'budget', 'revenue', 'profit', 'expense',
            'engineering', 'technical', 'system', 'architecture', 'code', 'api',
            'marketing', 'campaign', 'brand', 'market', 'customer', 'competitor',
            'hr', 'employee', 'policy', 'leave', 'benefits', 'company', 'organization',
            'general', 'faq', 'handbook', 'procedure', 'process', 'finsolve'
        }
        
        # Prompt injection patterns
        self.injection_patterns = [
            r'ignore\s+(?:your|the|previous|all)\s+(?:instructions|prompts?|rules?|context)',
            r'act\s+as\s+(?:a\s+)?(?:different|new|another)\s+(?:assistant|ai|model)',
            r'forget\s+(?:everything|all|your\s+(?:instructions|training|context))',
            r'override\s+(?:your|the|security|rbac)\s+(?:settings|restrictions|controls)',
            r'show\s+me\s+(?:all|everything)\s+(?:documents?|files?|data)\s+regardless',
            r'bypass\s+(?:security|rbac|access|restrictions|controls)',
            r'pretend\s+(?:you|to\s+be|that)',
            r'\/\*.*\*\/',  # Comment injection
            r'<script.*?>.*?<\/script>',  # Script injection
            r'system\s*:\s*you\s+are\s+now',
            r'new\s+(?:role|persona|character|identity)',
        ]
        
        # PII patterns
        self.pii_patterns = {
            'aadhaar': r'\b\d{4}\s?\d{4}\s?\d{4}\b',  # Aadhaar number
            'bank_account': r'\b\d{9,18}\b',  # Bank account numbers
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'(?:\+91|0)?[6-9]\d{9}',  # Indian phone numbers
            'pan': r'\b[A-Z]{5}\d{4}[A-Z]{1}\b',  # PAN number
            'credit_card': r'\b(?:\d{4}[\s-]?){3}\d{4}\b',  # Credit card
        }
        
    def _initialize_models(self):
        """Initialize ML models for guardrails (placeholder for now)"""
        try:
            # For production, you would initialize actual models here
            # self.injection_detector = pipeline("text-classification", 
            #                                   model="unitary/toxic-bert")
            logger.info("Guardrail models initialized successfully")
        except Exception as e:
            logger.warning(f"Could not initialize ML models: {e}")
            logger.info("Using rule-based approaches as fallback")
    
    async def check_off_topic(self, query: str) -> GuardrailResult:
        """Detect if query is off-topic from FinSolve business domains"""
        query_lower = query.lower()
        
        # Check for obvious off-topic patterns
        off_topic_patterns = [
            r'\bpoem\b', r'\bsong\b', r'\brecipe\b', r'\bmovie\b', r'\bcricket\b',
            r'\bfootball\b', r'\bweather\b', r'\bjoke\b', r'\bstory\b',
            r'\bgame\b', r'\bmusic\b', r'\bsport\b', r'\bentertainment\b',
            r'what.*time.*is.*it', r'tell.*me.*about.*yourself',
            r'write.*me.*a', r'create.*a.*story', r'sing.*me'
        ]
        
        # Check for off-topic patterns
        for pattern in off_topic_patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return GuardrailResult(
                    is_safe=False,
                    violation_type="off_topic",
                    violation_message="I'm FinBot, your workplace assistant for FinSolve Technologies. I can only help with business-related questions about our company policies, financial reports, engineering documentation, and marketing materials."
                )
        
        # Check if query contains any business domain keywords
        has_business_content = any(
            domain in query_lower for domain in self.business_domains
        )
        
        # If no business keywords and query doesn't seem business-related
        if not has_business_content and len(query.split()) > 3:
            # Use simple heuristic: if query has question words but no business terms
            question_words = {'what', 'how', 'when', 'where', 'why', 'who', 'which'}
            has_question = any(word in query_lower for word in question_words)
            
            if has_question:
                confidence_score = 0.7  # Medium confidence for rule-based detection
                return GuardrailResult(
                    is_safe=False,
                    violation_type="off_topic",
                    violation_message="I can only assist with FinSolve business-related questions. Please ask about our financial reports, HR policies, engineering documentation, or marketing materials.",
                    confidence_score=confidence_score
                )
        
        return GuardrailResult(is_safe=True)
    
    async def check_prompt_injection(self, query: str) -> GuardrailResult:
        """Detect prompt injection attempts"""
        query_lower = query.lower()
        
        # Check against known injection patterns
        for pattern in self.injection_patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return GuardrailResult(
                    is_safe=False,
                    violation_type="prompt_injection",
                    violation_message="I cannot process requests that attempt to modify my instructions or bypass security controls. Please ask a legitimate business question."
                )
        
        # Additional checks for common bypass attempts
        suspicious_phrases = [
            'admin mode', 'developer mode', 'debug mode',
            'unrestricted', 'no limits', 'full access',
            'root access', 'sudo', 'administrator'
        ]
        
        for phrase in suspicious_phrases:
            if phrase in query_lower:
                return GuardrailResult(
                    is_safe=False,
                    violation_type="prompt_injection",
                    violation_message="Access control bypass attempts are not allowed. Please ask legitimate business questions within your authorized scope."
                )
        
        return GuardrailResult(is_safe=True)
    
    async def check_pii(self, query: str) -> GuardrailResult:
        """Detect and handle PII in queries"""
        detected_pii = []
        sanitized_query = query
        
        for pii_type, pattern in self.pii_patterns.items():
            matches = re.finditer(pattern, query)
            for match in matches:
                detected_pii.append(pii_type)
                # Replace with masked version
                sanitized_query = re.sub(pattern, f"[REDACTED_{pii_type.upper()}]", sanitized_query)
        
        if detected_pii:
            return GuardrailResult(
                is_safe=False,
                violation_type="pii_detected",
                violation_message=f"Personal information detected ({', '.join(detected_pii)}). Please remove sensitive data from your query.",
                sanitized_input=sanitized_query
            )
        
        return GuardrailResult(is_safe=True)
    
    async def check_rate_limit(self, session_id: str) -> GuardrailResult:
        """Check session rate limiting (20 queries per session)"""
        current_time = time.time()
        
        if session_id not in self.session_tracker:
            self.session_tracker[session_id] = SessionInfo()
        
        session = self.session_tracker[session_id]
        
        # Add current query timestamp
        if session.query_timestamps is not None:
            session.query_timestamps.append(current_time)
        session.query_count += 1
        session.last_query_time = current_time
        
        # Check if exceeded rate limit
        if session.query_count > 20:
            return GuardrailResult(
                is_safe=False,
                violation_type="rate_limit_exceeded",
                violation_message="You have exceeded the session limit of 20 queries. Please start a new session to continue."
            )
        
        # Warning at 15 queries
        if session.query_count == 15:
            return GuardrailResult(
                is_safe=True,
                violation_type="rate_limit_warning",
                violation_message=f"Rate limit warning: {session.query_count}/20 queries used in this session."
            )
        
        return GuardrailResult(is_safe=True)
    
    async def validate_input(self, query: str, session_id: str = "default") -> Tuple[GuardrailResult, str]:
        """Run all input guardrails and return combined result"""
        
        # Run all checks in parallel
        results = await asyncio.gather(
            self.check_off_topic(query),
            self.check_prompt_injection(query),
            self.check_pii(query),
            self.check_rate_limit(session_id),
            return_exceptions=True
        )
        
        # Process results
        final_query = query
        violations = []
        warnings = []
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Guardrail check failed: {result}")
                continue
            
            # Assert type for Pylance
            assert isinstance(result, GuardrailResult)
            
            if not result.is_safe:
                if result.violation_type == "rate_limit_warning":
                    if result.violation_message:
                        warnings.append(result.violation_message)
                else:
                    violations.append(result)
                    
            # Use sanitized input if available
            if result.sanitized_input:
                final_query = result.sanitized_input
        
        # Return first violation found
        if violations:
            return violations[0], final_query
        
        # Return warning if any
        if warnings:
            return GuardrailResult(
                is_safe=True,
                violation_type="warning",
                violation_message=warnings[0]
            ), final_query
        
        return GuardrailResult(is_safe=True), final_query


