"""
Semantic Router for Query Intent Classification and RBAC Enforcement

This module implements intelligent query routing that determines which document collections
should be searched based on query intent, while enforcing role-based access control.
"""

import logging
from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

# Clean imports now that we renamed the file to avoid conflicts
from semantic_router import Route, SemanticRouter
from semantic_router.encoders import CohereEncoder, OpenAIEncoder, HuggingFaceEncoder

from src.core.config import settings

logger = logging.getLogger(__name__)


class RouteType(str, Enum):
    """Supported route types for query classification"""
    FINANCE = "finance_route"
    ENGINEERING = "engineering_route"
    MARKETING = "marketing_route"
    HR_GENERAL = "hr_general_route"
    CROSS_DEPARTMENT = "cross_department_route"


@dataclass
class RoutingResult:
    """Result of semantic routing with access control validation"""
    route: Optional[RouteType]
    target_collections: List[str]
    accessible_collections: List[str]
    access_denied_collections: List[str]
    user_role: str
    access_granted: bool
    message: Optional[str] = None


from src.core.routing.router_utterances import (
    FINANCE_UTTERANCES,
    ENGINEERING_UTTERANCES,
    MARKETING_UTTERANCES,
    HR_GENERAL_UTTERANCES,
    CROSS_DEPARTMENT_UTTERANCES
)

class SemanticQueryRouter:
    """
    Intelligent query router that classifies queries by intent and enforces RBAC.
    
    Routes queries to appropriate document collections while ensuring users can only
    access collections permitted by their role.
    """
    
    def __init__(self, encoder_type: str = "huggingface"):
        """
        Initialize the semantic router with route definitions and encoder.
        
        Args:
            encoder_type: Type of encoder to use ('huggingface', 'openai', 'cohere')
        """
        self.settings = settings
        self.encoder = self._setup_encoder(encoder_type)
        self.routes = self._create_routes()
        
        # Initialize the router with auto_sync to automatically build the index
        self.router = SemanticRouter(
            encoder=self.encoder, 
            routes=self.routes,
            auto_sync="local"  # This automatically builds the index on creation
        )
        
        # Verify the index was built successfully
        try:
            if hasattr(self.router.index, 'is_ready'):
                is_ready = self.router.index.is_ready()
                logger.info(f"Semantic router index ready: {is_ready}")
                
                if not is_ready:
                    logger.warning("Index not ready after auto_sync, will use fallback routing")
            else:
                logger.info("Index readiness check not available")
                
        except Exception as check_error:
            logger.warning(f"Could not verify index readiness: {check_error}")
        
        # Route to collection mapping
        self.route_collections = {
            RouteType.FINANCE: ["finance", "general"],
            RouteType.ENGINEERING: ["engineering", "general"],
            RouteType.MARKETING: ["marketing", "general"],
            RouteType.HR_GENERAL: ["hr", "general"],
            RouteType.CROSS_DEPARTMENT: ["general", "finance", "engineering", "marketing", "hr"]
        }
        
        logger.info(f"Semantic router initialized with {len(self.routes)} routes")
    
    def _setup_encoder(self, encoder_type: str):
        """Setup the appropriate encoder for semantic routing"""
        if encoder_type.lower() == "huggingface":
            # Use configured semantic router model
            return HuggingFaceEncoder(name=self.settings.semantic_router_model)
        elif encoder_type.lower() == "openai":
            return OpenAIEncoder()
        elif encoder_type.lower() == "cohere":
            return CohereEncoder()
        else:
            logger.warning(f"Unknown encoder type {encoder_type}, defaulting to HuggingFace")
            return HuggingFaceEncoder(name=self.settings.semantic_router_model)
    
    def _create_routes(self) -> List[Route]:
        """Create route definitions with representative utterances"""
        
        # Create Route objects
        routes = [
            Route(
                name=RouteType.FINANCE.value,
                utterances=FINANCE_UTTERANCES
            ),
            Route(
                name=RouteType.ENGINEERING.value,
                utterances=ENGINEERING_UTTERANCES
            ),
            Route(
                name=RouteType.MARKETING.value,
                utterances=MARKETING_UTTERANCES
            ),
            Route(
                name=RouteType.HR_GENERAL.value,
                utterances=HR_GENERAL_UTTERANCES
            ),
            Route(
                name=RouteType.CROSS_DEPARTMENT.value,
                utterances=CROSS_DEPARTMENT_UTTERANCES
            )
        ]
        
        return routes
    
    async def route_query(self, query: str, user_role: str) -> RoutingResult:
        """
        Route a query to appropriate collections with RBAC enforcement.
        
        Args:
            query: User's natural language query
            user_role: User's role (employee, finance, engineering, marketing, hr, c_level)
            
        Returns:
            RoutingResult containing routing decision and access control information
        """
        # Log the routing attempt
        self._log_routing_attempt(query, user_role)
        
        # Get user's accessible collections
        user_accessible_collections = self.settings.role_access_matrix.get(user_role, [])
        
        # Perform semantic routing with auto_sync handling
        routing_decision = None
        route_name = None
        
        try:
            # With auto_sync="local", the index should be ready automatically
            routing_decision = self.router(query)
            
            # Handle both single RouteChoice and List[RouteChoice] return types
            if isinstance(routing_decision, list) and len(routing_decision) > 0:
                route_name = routing_decision[0].name
            elif routing_decision and not isinstance(routing_decision, list) and hasattr(routing_decision, 'name'):
                route_name = routing_decision.name
            else:
                route_name = None
            
        except Exception as e:
            logger.error(f"Semantic routing failed: {e}")
            # If semantic routing fails, default to cross-department
            route_name = RouteType.CROSS_DEPARTMENT.value
        
        # Convert route name to RouteType enum
        selected_route = None
        if route_name:
            try:
                selected_route = RouteType(route_name)
            except ValueError:
                logger.warning(f"Unknown route returned: {route_name}")
        
        # Determine target collections based on route
        if selected_route:
            target_collections = self.route_collections[selected_route]
        else:
            # Default to cross-department if no clear route found
            logger.info(f"No clear route found for query, defaulting to cross-department")
            selected_route = RouteType.CROSS_DEPARTMENT
            target_collections = self.route_collections[RouteType.CROSS_DEPARTMENT]
        
        # Intersect target collections with user's accessible collections
        accessible_collections = list(set(target_collections) & set(user_accessible_collections))
        access_denied_collections = list(set(target_collections) - set(user_accessible_collections))
        
        # Determine if access is granted
        access_granted = len(accessible_collections) > 0
        
        # Generate appropriate message
        message = self._generate_access_message(
            selected_route, user_role, accessible_collections, access_denied_collections, access_granted
        )
        
        # Log the routing result
        self._log_routing_result(selected_route, user_role, accessible_collections, access_denied_collections, access_granted)
        
        return RoutingResult(
            route=selected_route,
            target_collections=target_collections,
            accessible_collections=accessible_collections,
            access_denied_collections=access_denied_collections,
            user_role=user_role,
            access_granted=access_granted,
            message=message
        )
    
    def _generate_access_message(
        self, 
        route: RouteType, 
        user_role: str, 
        accessible: List[str], 
        denied: List[str], 
        granted: bool
    ) -> Optional[str]:
        """Generate appropriate access control message"""
        
        if not granted:
            if route == RouteType.FINANCE and user_role not in ["finance", "c_level"]:
                return "I apologize, but you don't have access to financial documents. Please contact your manager or the Finance team if you need this information."
            elif route == RouteType.ENGINEERING and user_role not in ["engineering", "c_level"]:
                return "I apologize, but you don't have access to engineering documents. Please contact the Engineering team for technical assistance."
            elif route == RouteType.MARKETING and user_role not in ["marketing", "c_level"]:
                return "I apologize, but you don't have access to marketing documents. Please contact the Marketing team for this information."
            elif route == RouteType.HR_GENERAL and user_role not in ["hr", "c_level", "employee"]:
                return "I apologize, but you don't have access to HR documents. Please contact the HR team for policy and benefit information."
            else:
                return "I apologize, but you don't have access to the requested information. Please contact your manager for assistance."
        
        elif denied:
            # Partial access - inform user about limitations
            denied_types = []
            if "finance" in denied:
                denied_types.append("financial")
            if "engineering" in denied:
                denied_types.append("engineering")
            if "marketing" in denied:
                denied_types.append("marketing")
            if "hr" in denied:
                denied_types.append("HR")
            
            if denied_types:
                return f"Note: Your search is limited to collections you have access to. {', '.join(denied_types)} documents are not included in the results."
        
        return None
    
    def _log_routing_attempt(self, query: str, user_role: str):
        """Log the routing attempt for audit purposes"""
        logger.info(f"Semantic routing attempt - User: {user_role}, Query: '{query[:100]}{'...' if len(query) > 100 else ''}'")
    
    def _log_routing_result(
        self, 
        route: Optional[RouteType], 
        user_role: str, 
        accessible: List[str], 
        denied: List[str], 
        granted: bool
    ):
        """Log the routing result for audit and monitoring purposes"""
        logger.info(
            f"Routing result - Route: {route.value if route else 'None'}, "
            f"User: {user_role}, "
            f"Access granted: {granted}, "
            f"Accessible collections: {accessible}, "
            f"Denied collections: {denied}"
        )
    
    def get_route_info(self) -> Dict[str, Dict]:
        """Get information about all available routes"""
        route_info = {}
        for route_type, collections in self.route_collections.items():
            route_info[route_type.value] = {
                "target_collections": collections,
                "description": self._get_route_description(route_type)
            }
        return route_info
    
    def _get_route_description(self, route_type: RouteType) -> str:
        """Get description for a route type"""
        descriptions = {
            RouteType.FINANCE: "Queries about revenue, budgets, financial metrics, and investor information",
            RouteType.ENGINEERING: "Queries about systems, architecture, APIs, incidents, and code",
            RouteType.MARKETING: "Queries about campaigns, brand guidelines, market share, and competitors",
            RouteType.HR_GENERAL: "Queries about policies, leave, benefits, and company culture",
            RouteType.CROSS_DEPARTMENT: "Broad queries that search across all accessible collections"
        }
        return descriptions.get(route_type, "Unknown route")


# Global router instance - initialized when needed
_router_instance: Optional[SemanticQueryRouter] = None


def get_semantic_router(encoder_type: str = "huggingface") -> SemanticQueryRouter:
    """Get or create the global semantic router instance"""
    global _router_instance
    if _router_instance is None:
        _router_instance = SemanticQueryRouter(encoder_type=encoder_type)
    return _router_instance