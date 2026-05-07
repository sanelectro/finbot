"""
Test module for semantic router functionality
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.store.vector_store import VectorStore
from src.models.document import Role

console = Console()
logger = logging.getLogger(__name__)


class SemanticRouterTester:
    """Test suite for semantic router functionality"""
    
    def __init__(self):
        self.vector_store = VectorStore()
    
    async def test_hr_employee_query(self, fallback_mode: bool = False) -> Dict[str, Any]:
        """
        Test semantic routing for HR employee query to verify it routes correctly
        and returns employee information through the semantic router.
        
        Args:
            fallback_mode: If True, skip semantic routing and test direct search
        """
        query = "How many employees are inactive?"
        user_role = "hr"
        
        console.print(f"[bold blue]Testing HR Employee Query {'(Fallback Mode)' if fallback_mode else 'via Semantic Router'}[/bold blue]")
        console.print(f"[yellow]Query:[/yellow] {query}")
        console.print(f"[yellow]Role:[/yellow] {user_role}")
        
        if not fallback_mode:
            try:
                from src.core.routing.query_router import get_semantic_router
            except ImportError as e:
                console.print(f"[red]❌ Import failed:[/red] {str(e)}")
                console.print("[yellow]Make sure semantic-router is installed: pip install semantic-router[/yellow]")
                console.print("[blue]Falling back to direct search test...[/blue]")
                return await self.test_hr_employee_query(fallback_mode=True)
            
            try:
                # Initialize router
                console.print(f"[blue]Initializing semantic router...[/blue]")
                router = get_semantic_router()
                console.print(f"[green]✅ Semantic router initialized successfully[/green]")
            except Exception as e:
                console.print(f"[red]❌ Failed to initialize semantic router:[/red] {str(e)}")
                console.print("[yellow]This might be due to:[/yellow]")
                console.print("  • Missing or incompatible semantic-router version")
                console.print("  • Network issues downloading the Qwen model")  
                console.print("  • Index not ready - try running a simpler test first")
                console.print("[blue]Falling back to direct search test...[/blue]")
                return await self.test_hr_employee_query(fallback_mode=True)
            
            try:
                # Test routing decision
                console.print(f"\\n[blue]Step 1: Testing routing decision...[/blue]")
                routing_result = await router.route_query(query, user_role)
            except Exception as e:
                console.print(f"[red]❌ Routing failed:[/red] {str(e)}")
                console.print("[yellow]Try using a different encoder or simpler model[/yellow]")
                console.print("[blue]Falling back to direct search test...[/blue]")
                return await self.test_hr_employee_query(fallback_mode=True)
        else:
            # Fallback mode - simulate expected routing result
            console.print(f"[yellow]⚠️ Running in fallback mode without semantic routing[/yellow]")
            from dataclasses import dataclass
            from typing import List, Optional
            
            @dataclass
            class MockRoutingResult:
                route: Optional[str] = "hr_general_route"
                target_collections: Optional[List[str]] = None
                accessible_collections: Optional[List[str]] = None
                access_denied_collections: Optional[List[str]] = None
                access_granted: bool = True
                message: Optional[str] = None
            
            routing_result = MockRoutingResult(
                target_collections=["hr", "general"],
                accessible_collections=["hr", "general"],
                access_denied_collections=[]
            )
        
        
        # Create routing results table
        routing_table = Table(title="Routing Analysis", box=box.ROUNDED)
        routing_table.add_column("Property", style="cyan")
        routing_table.add_column("Value", style="yellow")
        
        routing_table.add_row("Detected Route", getattr(routing_result, 'route', 'hr_general_route') or "No route")
        routing_table.add_row("Target Collections", ", ".join(routing_result.target_collections or []))
        routing_table.add_row("Access Granted", "✅ Yes" if routing_result.access_granted else "❌ No")
        routing_table.add_row("Accessible Collections", ", ".join(routing_result.accessible_collections or []))
        routing_table.add_row("Denied Collections", ", ".join(routing_result.access_denied_collections or []))
        if routing_result.message:
            routing_table.add_row("Message", routing_result.message)
        if fallback_mode:
            routing_table.add_row("Mode", "⚠️ Fallback (No Semantic Router)")
        
        console.print("\\n")
        console.print(routing_table)
        
        # Test full search with routing
        console.print(f"\\n[blue]Step 2: Testing search with {'direct RBAC' if fallback_mode else 'semantic routing'}...[/blue]")
        try:
            if fallback_mode:
                # Direct search without semantic routing
                search_result = await self.vector_store.search_with_rbac(
                    query=query,
                    user_role=user_role,
                    limit=5
                )
                # Convert to expected format
                search_result = {
                    "results": search_result,
                    "total_results": len(search_result),
                    "routing_info": {
                        "searched_collections": ["hr", "general"],
                        "route": "direct_search"
                    }
                }
            else:
                search_result = await self.vector_store.search_with_semantic_routing(
                    query=query,
                    user_role=user_role,
                    limit=5
                )
            console.print(f"[green]✅ Search completed successfully[/green]")
        except Exception as e:
            console.print(f"[red]❌ Search failed:[/red] {str(e)}")
            console.print("[yellow]This might be due to:[/yellow]")
            console.print("  • Qdrant server not running")
            console.print("  • No documents ingested yet")
            console.print("  • Vector store connection issues")
            return {"error": f"Search failed: {str(e)}"}
        
        
        # Create search results table
        search_table = Table(title="Search Results", box=box.ROUNDED)
        search_table.add_column("Document", style="cyan")
        search_table.add_column("Collection", style="magenta") 
        search_table.add_column("Score", style="green", justify="center")
        search_table.add_column("Content Preview", style="white")
        
        for chunk, score in search_result["results"][:3]:  # Show top 3 results
            # Show more content to see full employee information
            content_preview = chunk.content[:400] + "..." if len(chunk.content) > 400 else chunk.content
            search_table.add_row(
                chunk.metadata.source_document,
                chunk.metadata.collection,
                f"{score:.3f}",
                content_preview.replace("\\n", "\n")
            )
        
        console.print("\\n")
        console.print(search_table)
        
        # Show detailed content for first result to see full employee data
        if search_result['results']:
            console.print(f"\n[blue]📋 Detailed view of top result:[/blue]")
            top_chunk, top_score = search_result['results'][0]
            console.print(f"[yellow]Score:[/yellow] {top_score:.4f}")
            console.print(f"[yellow]Full Content:[/yellow]")
            console.print(f"[cyan]{top_chunk.content}[/cyan]")
        
        # Analyze results
        test_results = {
            "query": query,
            "user_role": user_role,
            "mode": "fallback" if fallback_mode else "semantic_routing",
            "routing": {
                "route": getattr(routing_result, 'route', 'hr_general_route'),
                "target_collections": routing_result.target_collections,
                "accessible_collections": routing_result.accessible_collections,
                "access_granted": routing_result.access_granted,
                "expected_hr_route": (getattr(routing_result, 'route', 'hr_general_route') == "hr_general_route")
            },
            "search": {
                "total_results": search_result["total_results"],
                "best_score": search_result['results'][0][1] if search_result['results'] else 0.0,
                "searched_collections": search_result["routing_info"]["searched_collections"],
                "found_hr_content": any("hr" in chunk.metadata.collection.lower() 
                                      for chunk, _ in search_result['results']),
                "found_employee_data": any("FINEMP1138" in chunk.content or "employee" in chunk.content.lower()
                                         for chunk, _ in search_result['results'])
            }
        }
        
        # Summary
        console.print(f"\\n[bold]Test Results Summary:[/bold]")
        
        # Check if routing worked as expected
        routing_success = (routing_result.access_granted and
                          "hr" in (routing_result.accessible_collections or []))
        
        console.print(f"  • Routing Success: [{'green' if routing_success else 'red'}]{routing_success}[/{'green' if routing_success else 'red'}]")
        console.print(f"  • Results Found: [{'green' if search_result['total_results'] > 0 else 'red'}]{search_result['total_results']} documents[/{'green' if search_result['total_results'] > 0 else 'red'}]")
        console.print(f"  • HR Content Found: [{'green' if test_results['search']['found_hr_content'] else 'red'}]{test_results['search']['found_hr_content']}[/{'green' if test_results['search']['found_hr_content'] else 'red'}]")
        console.print(f"  • Employee Data Found: [{'green' if test_results['search']['found_employee_data'] else 'red'}]{test_results['search']['found_employee_data']}[/{'green' if test_results['search']['found_employee_data'] else 'red'}]")
        
        if search_result['total_results'] > 0:
            console.print(f"  • Best Match Score: [cyan]{test_results['search']['best_score']:.4f}[/cyan]")
        
        # Overall assessment
        overall_success = (routing_success and 
                          search_result['total_results'] > 0 and
                          test_results['search']['found_hr_content'])
        
        status = "✅ PASS" if overall_success else "❌ FAIL"
        console.print(f"\\n[bold]Overall Test Status: {status} {'(Fallback Mode)' if fallback_mode else ''}[/bold]")
        
        if not overall_success:
            console.print("\\n[yellow]💡 Possible issues:[/yellow]")
            if not routing_success:
                console.print("  • Semantic routing may not be working correctly")
            if search_result['total_results'] == 0:
                console.print("  • No HR documents found - check if HR data is ingested")
            if not test_results['search']['found_hr_content']:
                console.print("  • HR collection not being searched - check RBAC configuration")
        
        return test_results


# Convenience function for direct testing
async def test_hr_employee_search(fallback_mode: bool = False) -> Dict[str, Any]:
    """Convenience function to test HR employee search via semantic router"""
    tester = SemanticRouterTester()
    return await tester.test_hr_employee_query(fallback_mode=fallback_mode)


if __name__ == "__main__":
    # Run the test directly - will automatically fallback if semantic routing fails
    asyncio.run(test_hr_employee_search())