"""
Simplified RAG System using Groq for intelligent response generation
"""

import asyncio
import logging
import os
import re
from typing import List, Dict, Any, Optional, Tuple

from src.core.store.vector_store import VectorStore
from src.core.config import settings
from src.core.guardrails import GuardrailsOrchestrator
from src.models.document import Role

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

logger = logging.getLogger(__name__)

class FinBotRAGSystem:
    """
    RAG system with integrated guardrails using Groq for intelligent response generation
    """
    
    def __init__(self):
        self.vector_store = VectorStore()
        self.guardrails = GuardrailsOrchestrator()
        self.system_prompt = self._create_system_prompt()
        
        # Initialize Groq client with proper error handling
        self.groq_client = None
        self.groq_model = settings.groq_model
        
        if GROQ_AVAILABLE:
            api_key = settings.groq_api_key or os.getenv('GROQ_API_KEY')
            if api_key:
                try:
                    self.groq_client = Groq(api_key=api_key)
                    logger.info("Groq client initialized successfully")
                except Exception as e:
                    logger.warning(f"Failed to initialize Groq client: {e}")
            else:
                logger.warning("GROQ_API_KEY not found in environment variables or config")
        else:
            logger.warning("Groq package not available")
        
    def _create_system_prompt(self) -> str:
        """Create comprehensive system prompt for FinBot"""
        return """You are FinBot, an intelligent assistant for FinSolve Technologies. You help employees access company information based on their role and the available documents.

## CORE RESPONSIBILITIES:
- Answer questions accurately using only the provided context
- Respect role-based access control (users can only see information they're authorized for)
- Provide clear, professional, and helpful responses
- Handle employee queries, salary information, policies, and company data

## RESPONSE GUIDELINES:
1. **Use only the provided context** - Don't make up information
2. **Be specific and direct** - Answer the exact question asked
3. **Include relevant details** - Employee IDs, salary figures, department info when available
4. **Professional tone** - You represent FinSolve Technologies
5. **Handle missing info gracefully** - If information isn't in the context, say so
6. **Employee ID queries** - When asked about a specific employee ID, look for exact matches in the context

## SPECIAL HANDLING:
- **Employee ID Lookups**: For queries like "employee with ID FINEMP1352", find the exact employee record with that ID
- **Salary Questions**: Provide specific salary figures when available and authorized
- **Department Info**: Include department, role, and reporting details when relevant

## ACCESS CONTROL:
- HR role: Employee data, salary info, HR policies
- Finance role: Financial data, budgets, accounting info  
- Engineering role: Technical docs, system info, engineering processes
- Marketing role: Marketing materials, campaigns, customer data
- Employee role: General policies, basic company info
- C-level role: All information across departments

When you receive context documents and a question, provide a clear, accurate answer based solely on that context. Pay special attention to exact matches for employee IDs, numbers, and specific identifiers."""

    async def process_query(
        self, 
        query: str, 
        user_role: Role,
        session_id: str = "default",
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        RAG pipeline with guardrails:
        1. Validate input query through guardrails
        2. Retrieve relevant documents with RBAC
        3. Build context from retrieved chunks  
        4. Send to Groq with system prompt
        5. Validate output through guardrails
        6. Return final response with warnings
        
        Args:
            query: User's question
            user_role: User's role for RBAC
            session_id: Session ID for rate limiting
            limit: Maximum documents to retrieve
            
        Returns:
            Response with query, user_role, answer, confidence, warnings, and guardrail_info
        """
        
        logger.info(f"Processing RAG query: '{query}' for role: {user_role}")
        
        # Step 1: Input Guardrails Validation
        is_safe, processed_query, input_warning = await self.guardrails.validate_query(query, session_id)
        
        if not is_safe:
            return {
                "query": query,
                "user_role": user_role,
                "answer": input_warning,
                "confidence": 0.0,
                "warnings": [input_warning] if input_warning else [],
                "guardrail_info": {
                    "input_blocked": True,
                    "session_info": self.guardrails.get_session_info(session_id)
                }
            }
        
        # Prepare warnings list
        warnings = [input_warning] if input_warning else []
        
        try:
            # Step 2: Enhanced query processing for employee IDs
            enhanced_query = self._enhance_query_for_exact_matches(processed_query)
            
            # Step 3: Retrieve relevant documents with RBAC
            results = await self.vector_store.search_with_rbac(
                query=enhanced_query,
                user_role=user_role,
                limit=limit
            )
            
            if not results:
                return {
                    "query": query,
                    "user_role": user_role,
                    "answer": f"I couldn't find any relevant information for your query in the documents you have access to as a {user_role} user.",
                    "confidence": 0.0,
                    "warnings": warnings,
                    "guardrail_info": {
                        "input_blocked": False,
                        "output_warnings": [],
                        "session_info": self.guardrails.get_session_info(session_id)
                    }
                }
            
            # Step 4: Build context from retrieved chunks
            context = self._build_context(results)
            
            # Step 5: Generate response using Groq (if available)
            if self.groq_client:
                try:
                    user_message = f"Context:\\n{context}\\n\\nQuestion: {processed_query}"
                    
                    response = self.groq_client.chat.completions.create(
                        model=self.groq_model,
                        messages=[
                            {"role": "system", "content": self.system_prompt},
                            {"role": "user", "content": user_message},
                        ],
                        temperature=0.2,  # Low temperature for factual responses
                    )
                    
                    answer = response.choices[0].message.content
                    if answer is None:
                        answer = self._create_fallback_response(processed_query, results)
                except Exception as e:
                    logger.error(f"Groq API error: {e}")
                    answer = self._create_fallback_response(processed_query, results)
            else:
                # Fallback response without LLM
                answer = self._create_fallback_response(processed_query, results)
            
            # Step 6: Output Guardrails Validation
            accessible_collections = self._get_accessible_collections(user_role)
            retrieved_chunks = [{
                "content": chunk.content,
                "metadata": chunk.metadata.model_dump() if hasattr(chunk.metadata, 'model_dump') else chunk.metadata
            } for chunk, _ in results]
            
            final_answer, output_warnings = await self.guardrails.validate_response(
                answer, user_role, accessible_collections, retrieved_chunks
            )
            
            warnings.extend(output_warnings)
            
            # Get confidence from top result
            confidence = results[0][1] if results else 0.0
            
            return {
                "query": query,
                "user_role": user_role,
                "answer": final_answer,
                "confidence": confidence,
                "warnings": warnings,
                "guardrail_info": {
                    "input_blocked": False,
                    "output_warnings": output_warnings,
                    "session_info": self.guardrails.get_session_info(session_id)
                }
            }
            
        except Exception as e:
            logger.error(f"RAG processing failed: {str(e)}")
            return {
                "query": query,
                "user_role": user_role,
                "answer": "I encountered an error while processing your request. Please try again or contact support.",
                "confidence": 0.0,
                "warnings": warnings,
                "guardrail_info": {
                    "input_blocked": False,
                    "output_warnings": [],
                    "session_info": self.guardrails.get_session_info(session_id),
                    "error": str(e)
                }
            }
    
    def _build_context(self, results: List[Tuple]) -> str:
        """Build context string from retrieved document chunks"""
        if not results:
            return "No relevant documents found."
        
        context_parts = []
        for i, (chunk, score) in enumerate(results, 1):
            context_parts.append(
                f"Document {i} (Relevance: {score:.3f}):\\n"
                f"Source: {chunk.metadata.source_document} | Collection: {chunk.metadata.collection}\\n"
                f"Content: {chunk.content}\\n"
            )
        
        return "\\n---\\n".join(context_parts)
    
    def _enhance_query_for_exact_matches(self, query: str) -> str:
        """Enhance queries to better match employee IDs and other exact terms"""
        # Detect employee ID patterns (FINEMP followed by numbers)
        employee_id_pattern = r'\b(FINEMP\d+)\b'
        employee_ids = re.findall(employee_id_pattern, query, re.IGNORECASE)
        
        if employee_ids:
            # For employee ID queries, create a more targeted search
            # Add the exact ID multiple times and specify it's an employee_id search
            employee_id = employee_ids[0]  # Take the first found ID
            enhanced_query = f"employee_id {employee_id} Employee: {employee_id} {query} {employee_id}"
            logger.info(f"Enhanced query for employee ID search: '{enhanced_query}'")
            return enhanced_query
        
        return query
    
    def _get_accessible_collections(self, user_role: Role) -> List[str]:
        """Get list of collections accessible to the user role"""
        role_access_matrix = {
            "employee": ["general"],
            "finance": ["general", "finance"],
            "engineering": ["general", "engineering"],
            "marketing": ["general", "marketing"],
            "hr": ["general", "hr"],
            "c_level": ["general", "finance", "engineering", "marketing", "hr"]
        }
        return role_access_matrix.get(user_role, ["general"])
    
    def reset_session(self, session_id: str):
        """Reset guardrail session tracking"""
        self.guardrails.reset_session(session_id)
    
    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get session information for rate limiting"""
        return self.guardrails.get_session_info(session_id)
    
    def _create_fallback_response(self, query: str, results: List[Tuple]) -> str:
        """Create a fallback response when Groq is not available"""
        if not results:
            return "I found no relevant information for your query."
        
        # Simple fallback: return content from top result
        top_result = results[0]
        chunk, score = top_result
        
        return f"Based on the available information (relevance: {score:.3f}): {chunk.content[:500]}{'...' if len(chunk.content) > 500 else ''}"
        
