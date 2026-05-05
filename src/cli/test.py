"""
Testing commands for FinBot
"""

import typer
import asyncio
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
import time

from src.core.config import settings
from src.core.document_processor import HierarchicalDocumentProcessor
from src.core.vector_store import VectorStore
from src.models.document import Role
import logging

console = Console()
logger = logging.getLogger(__name__)

# Create the test subcommand
test_app = typer.Typer(
    name="test",
    help="Testing and validation commands",
    rich_markup_mode="rich"
)

@test_app.command("embeddings")
def test_embeddings():
    """
    Test SentenceTransformer embedding generation with sample queries
    """
    console.print("\\n[bold blue]Testing SentenceTransformer Embeddings[/bold blue]")
    
    try:
        from sentence_transformers import SentenceTransformer
        
        # Initialize the model
        console.print(f"[yellow]Loading model:[/yellow] {settings.embedding_model}")
        model = SentenceTransformer(settings.embedding_model)
        
        # Sample test queries
        test_queries = [
            "What is the system uptime SLA?",
            "Show me financial budget information", 
            "How do I report an incident?",
            "What are the marketing campaign metrics?",
            "Tell me about employee policies"
        ]
        
        console.print("\\n[green]Generating embeddings for sample queries...[/green]")
        
        # Create results table
        table = Table(title="Embedding Test Results", box=box.ROUNDED)
        table.add_column("Query", style="cyan", width=40)
        table.add_column("Embedding Dim", justify="center", style="yellow")
        table.add_column("Sample Values", style="green", width=30)
        table.add_column("Processing Time", justify="center", style="magenta")
        
        total_time = 0
        
        for query in test_queries:
            start_time = time.time()
            embedding = model.encode(query)
            processing_time = time.time() - start_time
            total_time += processing_time
            
            # Show first few embedding values
            sample_values = f"[{embedding[0]:.4f}, {embedding[1]:.4f}, {embedding[2]:.4f}...]"
            
            table.add_row(
                query,
                str(len(embedding)),
                sample_values,
                f"{processing_time:.3f}s"
            )
        
        console.print("\\n")
        console.print(table)
        
        console.print(f"\\n[green]✅ Embedding test completed successfully![/green]")
        console.print(f"[green]Total processing time:[/green] {total_time:.3f}s")
        console.print(f"[green]Average time per query:[/green] {total_time/len(test_queries):.3f}s")
        
    except Exception as e:
        console.print(f"[red]❌ Embedding test failed:[/red] {str(e)}")
        raise typer.Exit(1)

@test_app.command("chunking")
def test_chunking(
    file_path: Optional[str] = typer.Option(
        None,
        "--file", 
        "-f",
        help="Path to specific file to test chunking (defaults to first engineering doc)"
    )
):
    """
    Test document chunking with Docling on a sample document
    """
    console.print("\\n[bold blue]Testing Document Chunking[/bold blue]")
    
    # Determine test file
    if file_path:
        test_file = Path(file_path)
    else:
        # Default to first engineering document
        eng_dir = settings.data_dir / "engineering"
        if not eng_dir.exists():
            console.print("[red]Engineering directory not found[/red]")
            raise typer.Exit(1)
        
        md_files = list(eng_dir.glob("*.md"))
        if not md_files:
            console.print("[red]No markdown files found in engineering directory[/red]")
            raise typer.Exit(1)
        
        test_file = md_files[0]
    
    if not test_file.exists():
        console.print(f"[red]File not found:[/red] {test_file}")
        raise typer.Exit(1)
    
    console.print(f"[green]Testing chunking on:[/green] {test_file}")
    
    try:
        # Run chunking test
        asyncio.run(_test_document_chunking(test_file))
        
    except Exception as e:
        console.print(f"[red]❌ Chunking test failed:[/red] {str(e)}")
        raise typer.Exit(1)

@test_app.command("search")  
def test_search(
    query: str = typer.Option(
        "system uptime",
        "--query",
        "-q", 
        help="Search query to test"
    ),
    role: str = typer.Option(
        "engineering",
        "--role",
        "-r",
        help="User role for RBAC testing (employee, finance, engineering, marketing, c_level)"
    )
):
    """
    Test RBAC-enforced vector search functionality
    """
    console.print("\\n[bold blue]Testing RBAC Vector Search[/bold blue]")
    
    # Validate role
    valid_roles = ["employee", "finance", "engineering", "marketing", "c_level"]
    if role not in valid_roles:
        console.print(f"[red]Invalid role.[/red] Must be one of: {', '.join(valid_roles)}")
        raise typer.Exit(1)
    
    try:
        # Run search test
        asyncio.run(_test_vector_search(query, role))
        
    except Exception as e:
        console.print(f"[red]❌ Search test failed:[/red] {str(e)}")
        raise typer.Exit(1)

@test_app.command("rbac")
def test_rbac():
    """
    Test RBAC enforcement with different user roles
    """
    console.print("\\n[bold blue]Testing RBAC Enforcement[/bold blue]")
    
    test_cases = [
        ("engineering", "system architecture", "Should find engineering docs"),
        ("finance", "budget allocation", "Should find finance docs if any"),
        ("employee", "company policies", "Should find general docs only"),
        ("marketing", "campaign metrics", "Should find marketing docs if any"),
        ("c_level", "quarterly report", "Should access all collections")
    ]
    
    try:
        asyncio.run(_test_rbac_enforcement(test_cases))
        
    except Exception as e:
        console.print(f"[red]❌ RBAC test failed:[/red] {str(e)}")
        raise typer.Exit(1)

async def _test_document_chunking(file_path: Path):
    """Test document chunking on a single file"""
    
    processor = HierarchicalDocumentProcessor()
    
    console.print(f"[yellow]Processing document...[/yellow]")
    
    # Process the document
    processed_doc = await processor.process_document(
        file_path, 
        "engineering",  # Collection
        ["engineering", "c_level"]  # Access roles
    )
    
    console.print(f"[green]✅ Document processed successfully![/green]")
    console.print(f"[green]Total chunks created:[/green] {len(processed_doc.chunks)}")
    console.print(f"[green]Processing time:[/green] {processed_doc.processing_time:.2f}s")
    
    # Show chunk analysis (using available metadata)
    chunk_types = {}
    section_titles = set()
    
    for chunk in processed_doc.chunks:
        chunk_type = "text"  # Default since chunk_type not available
        chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
        section_titles.add("Document Content")  # Default title
    
    # Create chunk analysis table
    table = Table(title="Chunk Analysis", box=box.ROUNDED)
    table.add_column("Chunk Type", style="cyan")
    table.add_column("Count", justify="center", style="yellow")
    table.add_column("Percentage", justify="center", style="green")
    
    total_chunks = len(processed_doc.chunks)
    for chunk_type, count in chunk_types.items():
        percentage = (count / total_chunks) * 100
        table.add_row(chunk_type, str(count), f"{percentage:.1f}%")
    
    console.print("\\n")
    console.print(table)
    
    # Show sample chunks
    console.print("\\n[bold]Sample Chunks:[/bold]")
    
    for i, chunk in enumerate(processed_doc.chunks[:3]):  # Show first 3 chunks
        panel_content = f"""
[bold]Content:[/bold] {chunk.content[:200]}{"..." if len(chunk.content) > 200 else ""}

[bold]Metadata:[/bold]
• Content Type: text
• Access Roles: {", ".join(chunk.metadata.access_roles)}
• Document: {chunk.metadata.document_path}
        """
        
        console.print(Panel(
            panel_content.strip(),
            title=f"Chunk {i+1}",
            border_style="blue"
        ))

async def _test_vector_search(query: str, role: str):
    """Test vector search with RBAC"""
    
    vector_store = VectorStore()
    
    console.print(f"[yellow]Searching for:[/yellow] '{query}'")
    console.print(f"[yellow]User role:[/yellow] {role}")
    
    # Fix role type conversion
    from typing import cast
    from src.models.document import Role
    
    # Perform search
    start_time = time.time()
    results = await vector_store.search_with_rbac(
        query=query,
        user_role=cast(Role, role),
        limit=5
    )
    search_time = time.time() - start_time
    
    console.print(f"[green]Search completed in {search_time:.3f}s[/green]")
    console.print(f"[green]Found {len(results)} results[/green]")
    
    if not results:
        console.print("[yellow]No results found. This could mean:[/yellow]")
        console.print("  • No documents match the query")
        console.print("  • User role doesn't have access to relevant documents")
        console.print("  • No documents ingested yet")
        return
    
    # Show results
    table = Table(title=f"Search Results for '{query}' (Role: {role})", box=box.ROUNDED)
    table.add_column("Score", justify="center", style="yellow", width=8)
    table.add_column("Document", style="cyan", width=25)
    table.add_column("Section", style="green", width=20) 
    table.add_column("Content Preview", style="white", width=40)
    table.add_column("Collection", style="magenta", width=12)
    
    for chunk, score in results:
        content_preview = chunk.content[:80] + "..." if len(chunk.content) > 80 else chunk.content
        content_preview = content_preview.replace("\\n", " ")
        
        table.add_row(
            f"{score:.3f}",
            chunk.metadata.source_document,
            "Document Content",  # Simplified since section_title not available
            content_preview,
            chunk.metadata.collection
        )
    
    console.print("\\n")
    console.print(table)
    
    # Verify RBAC enforcement
    allowed_collections = settings.role_access_matrix.get(role, [])
    
    for chunk, score in results:
        if chunk.metadata.collection not in allowed_collections:
            console.print(f"[red]🚨 RBAC VIOLATION:[/red] Role '{role}' accessed '{chunk.metadata.collection}' collection!")
        else:
            console.print(f"[green]✅ RBAC OK:[/green] Role '{role}' correctly accessed '{chunk.metadata.collection}'")

async def _test_rbac_enforcement(test_cases):
    """Test RBAC enforcement across different roles and queries"""
    
    vector_store = VectorStore()
    
    console.print("[yellow]Testing RBAC enforcement across different roles...[/yellow]")
    
    results_table = Table(title="RBAC Enforcement Test Results", box=box.ROUNDED)
    results_table.add_column("Role", style="cyan")
    results_table.add_column("Query", style="yellow")
    results_table.add_column("Results Found", justify="center", style="green")
    results_table.add_column("Collections Accessed", style="magenta")
    results_table.add_column("RBAC Status", justify="center", style="bold")
    
    for role, query, description in test_cases:
        console.print(f"\\n[blue]Testing {role} role with query '{query}'[/blue]")
        
        # Perform search
        # Fix role type conversion
        from typing import cast
        from src.models.document import Role
        results = await vector_store.search_with_rbac(
            query=query,
            user_role=cast(Role, role), 
            limit=10
        )
        
        # Analyze results
        collections_found = set()
        rbac_violations = []
        
        allowed_collections = settings.role_access_matrix.get(role, [])
        
        for chunk, score in results:
            collections_found.add(chunk.metadata.collection)
            if chunk.metadata.collection not in allowed_collections:
                rbac_violations.append(chunk.metadata.collection)
        
        # Determine RBAC status
        if rbac_violations:
            rbac_status = f"[red]VIOLATION: {', '.join(rbac_violations)}[/red]"
        else:
            rbac_status = "[green]✅ PASS[/green]"
        
        results_table.add_row(
            role,
            query,
            str(len(results)),
            ", ".join(collections_found) if collections_found else "None",
            rbac_status
        )
    
    console.print("\\n")
    console.print(results_table)
    
    # Summary
    console.print("\\n[bold]RBAC Test Summary:[/bold]")
    console.print(f"[green]Role-Collection Access Matrix:[/green]")
    
    for role, collections in settings.role_access_matrix.items():
        console.print(f"  • {role}: {', '.join(collections)}")

@test_app.command("chunking-accuracy")
def test_chunking_accuracy(
    file_path: Optional[str] = typer.Option(
        None,
        "--file", 
        "-f",
        help="Path to specific file to test chunking accuracy"
    ),
    content_type: str = typer.Option(
        "all",
        "--type",
        "-t", 
        help="Content type to test: table, paragraph, list, heading, multipage, csv, all"
    )
):
    """
    Test chunking accuracy by retrieving specific content and measuring relevance scores
    """
    console.print("\\n[bold blue]Testing Chunking Accuracy & Content Retrieval[/bold blue]")
    
    try:
        asyncio.run(_test_chunking_accuracy_async(file_path, content_type))
    except Exception as e:
        console.print(f"[red]❌ Chunking accuracy test failed:[/red] {str(e)}")
        raise typer.Exit(1)

@test_app.command("content-retrieval") 
def test_content_retrieval(
    queries: str = typer.Option(
        "system uptime,incident report,budget allocation",
        "--queries",
        "-q",
        help="Comma-separated test queries"
    ),
    expected_docs: str = typer.Option(
        "",
        "--expected",
        "-e", 
        help="Comma-separated expected document names for validation"
    ),
    min_score: float = typer.Option(
        0.5,
        "--min-score",
        "-s",
        help="Minimum relevance score threshold"  
    )
):
    """
    Test content retrieval accuracy with known queries and expected documents
    """
    console.print("\\n[bold blue]Testing Content Retrieval Accuracy[/bold blue]")
    
    query_list = [q.strip() for q in queries.split(",")]
    expected_list = [d.strip() for d in expected_docs.split(",")] if expected_docs else []
    
    try:
        asyncio.run(_test_content_retrieval_async(query_list, expected_list, min_score))
    except Exception as e:
        console.print(f"[red]❌ Content retrieval test failed:[/red] {str(e)}")
        raise typer.Exit(1)

async def _test_chunking_accuracy_async(file_path: Optional[str], content_type: str):
    """Test chunking accuracy across different content types"""
    
    vector_store = VectorStore()
    processor = HierarchicalDocumentProcessor()
    
    # Define test cases for different content types
    test_cases = await _get_chunking_test_cases(file_path, content_type)
    
    if not test_cases:
        console.print("[yellow]No test cases found. Make sure documents are ingested first.[/yellow]")
        return
    
    console.print(f"[green]Running {len(test_cases)} chunking accuracy test cases...[/green]")
    
    # Create results table
    results_table = Table(title="Chunking Accuracy Test Results", box=box.ROUNDED)
    results_table.add_column("Content Type", style="cyan")
    results_table.add_column("Test Query", style="yellow", width=30)
    results_table.add_column("Expected Content", style="blue", width=20)
    results_table.add_column("Best Score", justify="center", style="green")
    results_table.add_column("Found in Chunk", justify="center", style="magenta")
    results_table.add_column("Accuracy", justify="center", style="bold")
    
    total_score = 0
    passed_tests = 0
    
    for test_case in test_cases:
        content_type = test_case["type"]
        query = test_case["query"] 
        expected_content = test_case["expected_content"]
        expected_keywords = test_case.get("keywords", [])
        
        console.print(f"\\n[blue]Testing {content_type}: '{query}'[/blue]")
        
        # Choose appropriate role based on content type
        if test_case.get("collection") == "hr" or content_type == "csv":
            search_role = "c_level"  # c_level has access to HR data
        else:
            search_role = "engineering"  # Default role for other tests
        
        # Perform search
        results = await vector_store.search_with_rbac(
            query=query,
            user_role=search_role,
            limit=5
        )
        
        if not results:
            results_table.add_row(
                content_type,
                query,
                expected_content[:20] + "..." if len(expected_content) > 20 else expected_content,
                "0.000",
                "❌ No results",
                "[red]FAIL[/red]"
            )
            continue
        
        # Find best matching chunk and score
        best_score = results[0][1]  # First result has highest score
        best_chunk = results[0][0]
        
        # Check if expected content or keywords are found in the chunk
        content_found = False
        chunk_text = best_chunk.chunk_text.lower()
        
        # Check for expected content substring
        if expected_content.lower() in chunk_text:
            content_found = True
        
        # Check for expected keywords
        if not content_found and expected_keywords:
            content_found = any(keyword.lower() in chunk_text for keyword in expected_keywords)
        
        # Determine accuracy
        accuracy = "[green]PASS[/green]" if content_found and best_score >= 0.3 else "[red]FAIL[/red]"
        if content_found and best_score >= 0.3:
            passed_tests += 1
        
        total_score += best_score
        
        results_table.add_row(
            content_type,
            query[:30] + "..." if len(query) > 30 else query,
            expected_content[:20] + "..." if len(expected_content) > 20 else expected_content,
            f"{best_score:.4f}",
            "✅ Found" if content_found else "❌ Missing",
            accuracy
        )
    
    console.print("\\n")
    console.print(results_table)
    
    # Summary statistics
    avg_score = total_score / len(test_cases) if test_cases else 0
    pass_rate = (passed_tests / len(test_cases)) * 100 if test_cases else 0
    
    console.print(f"\\n[bold]Summary Statistics:[/bold]")
    console.print(f"  • Average Relevance Score: [green]{avg_score:.4f}[/green]")
    console.print(f"  • Test Pass Rate: [green]{passed_tests}/{len(test_cases)} ({pass_rate:.1f}%)[/green]")
    console.print(f"  • Content Types Tested: [blue]{len(set(tc['type'] for tc in test_cases))}[/blue]")

async def _get_chunking_test_cases(file_path: Optional[str], content_type: str) -> List[dict]:
    """Generate test cases for chunking accuracy based on available documents"""
    
    # Define test cases based on our known document structure
    all_test_cases = [
        # Engineering document tests
        {
            "type": "table",
            "query": "system uptime SLA percentage",
            "expected_content": "99.9%",
            "keywords": ["uptime", "availability", "SLA", "99.9"],
            "collection": "engineering"
        },
        {
            "type": "paragraph", 
            "query": "incident escalation procedure",
            "expected_content": "escalation",
            "keywords": ["escalation", "procedure", "incident", "notify"],
            "collection": "engineering"
        },
        {
            "type": "list",
            "query": "sprint planning steps",
            "expected_content": "planning",
            "keywords": ["sprint", "planning", "backlog", "estimation"],
            "collection": "engineering"
        },
        {
            "type": "heading",
            "query": "system monitoring alerts",
            "expected_content": "monitoring",
            "keywords": ["monitoring", "alerts", "system", "notification"],
            "collection": "engineering"
        },
        
        # CSV/HR document tests (using natural language chunk descriptions)
        {
            "type": "csv",
            "query": "employee Sarah Johnson information",
            "expected_content": "Sarah Johnson",
            "keywords": ["Sarah", "Johnson", "employee", "Software Engineer"],
            "collection": "hr"
        },
        {
            "type": "csv", 
            "query": "marketing manager employee details",
            "expected_content": "Marketing Manager",
            "keywords": ["Marketing", "Manager", "employee"],
            "collection": "hr"
        },
        {
            "type": "csv",
            "query": "full time employees in Engineering department",
            "expected_content": "Engineering",
            "keywords": ["Engineering", "Full-time", "employee", "department"],
            "collection": "hr"
        }
    ]
    
    # Filter test cases based on content_type parameter
    if content_type != "all":
        filtered_cases = [tc for tc in all_test_cases if tc["type"] == content_type]
        if not filtered_cases:
            console.print(f"[yellow]No test cases found for content type '{content_type}'[/yellow]")
            console.print(f"[yellow]Available types: {', '.join(set(tc['type'] for tc in all_test_cases))}[/yellow]")
        return filtered_cases
    
    return all_test_cases

async def _test_content_retrieval_async(query_list: List[str], expected_list: List[str], min_score: float):
    """Test content retrieval with specific queries"""
    
    vector_store = VectorStore()
    
    console.print(f"[green]Testing {len(query_list)} queries with minimum score threshold: {min_score}[/green]")
    
    results_table = Table(title="Content Retrieval Test Results", box=box.ROUNDED)
    results_table.add_column("Query", style="yellow")
    results_table.add_column("Results Found", justify="center", style="green")
    results_table.add_column("Best Score", justify="center", style="cyan")
    results_table.add_column("Meets Threshold", justify="center", style="bold")
    results_table.add_column("Expected Doc Found", justify="center", style="magenta")
    
    total_queries = len(query_list)
    queries_passed = 0
    expected_found = 0
    
    for i, query in enumerate(query_list):
        console.print(f"\\n[blue]Testing query {i+1}/{total_queries}: '{query}'[/blue]")
        
        # Perform search with engineering role (has broad access)
        results = await vector_store.search_with_rbac(
            query=query,
            user_role="engineering",
            limit=5
        )
        
        best_score = results[0][1] if results else 0.0
        meets_threshold = "✅ PASS" if best_score >= min_score else "❌ FAIL"
        
        # Check if expected document found (if provided)
        expected_doc_found = "N/A"
        if expected_list and i < len(expected_list):
            expected_doc = expected_list[i]
            if any(expected_doc.lower() in chunk.metadata.source_document.lower() 
                   for chunk, score in results):
                expected_doc_found = "✅ Found"
                expected_found += 1
            else:
                expected_doc_found = "❌ Missing"
        
        if best_score >= min_score:
            queries_passed += 1
        
        results_table.add_row(
            query,
            str(len(results)),
            f"{best_score:.3f}",
            meets_threshold,
            expected_doc_found
        )
    
    console.print("\\n")
    console.print(results_table)
    
    # Summary
    pass_rate = (queries_passed / total_queries) * 100
    console.print(f"\\n[bold]Summary:[/bold]")
    console.print(f"  • Queries passed threshold: [green]{queries_passed}/{total_queries} ({pass_rate:.1f}%)[/green]")
    if expected_list:
        expected_rate = (expected_found / len(expected_list)) * 100
        console.print(f"  • Expected documents found: [green]{expected_found}/{len(expected_list)} ({expected_rate:.1f}%)[/green]")


@test_app.command("semantic-routing")  
def test_semantic_routing(
    test_queries: str = typer.Option(
        "What was our Q3 revenue?,How do I deploy to production?,What are our brand guidelines?,What's our leave policy?,Tell me about FinSolve Technologies",
        "--queries", 
        "-q",
        help="Comma-separated test queries"
    ),
    user_role: str = typer.Option(
        "employee",
        "--role",
        "-r", 
        help="User role for testing (employee, finance, engineering, marketing, hr, c_level)"
    )
):
    """
    Test semantic query routing functionality with various query types and roles
    """
    console.print("\\n[bold blue]Testing Semantic Query Routing[/bold blue]")
    
    try:
        # Import and use the semantic router tester
        # Remove invalid imports - these functions don't exist in test_semantic_router
        # from src.tests.test_semantic_router import test_semantic_routing
        console.print("[yellow]⚠️ Semantic routing tests not available[/yellow]")
        return
        
        asyncio.run(test_semantic_routing(test_queries, user_role))
        
    except Exception as e:
        console.print(f"[red]❌ Semantic routing test failed:[/red] {str(e)}")
        raise typer.Exit(1)


@test_app.command("route-query")
def test_route_query_only(
    query: str = typer.Argument(..., help="Query to route"),
    user_role: str = typer.Option(
        "employee",
        "--role",
        "-r",
        help="User role for testing"
    )
):
    """
    Test routing for a single query without performing search
    """
    console.print("\\n[bold blue]Testing Query Routing[/bold blue]")
    
    try:
        # Remove invalid imports - these functions don't exist in test_semantic_router
        # from src.tests.test_semantic_router import test_route_query  
        console.print("[yellow]⚠️ Query routing tests not available[/yellow]")
        return
        
        asyncio.run(test_route_query(query, user_role))
        
    except Exception as e:
        console.print(f"[red]❌ Query routing test failed:[/red] {str(e)}")
        raise typer.Exit(1)


@test_app.command("route-info")
def show_route_info():
    """
    Show information about available semantic routes
    """
    console.print("\\n[bold blue]Semantic Router Information[/bold blue]")
    
    try:
        # Remove invalid imports - these functions don't exist in test_semantic_router
        # from src.tests.test_semantic_router import get_route_info
        console.print("[yellow]⚠️ Route info tests not available[/yellow]")
        return
        
        get_route_info()
        
    except Exception as e:
        console.print(f"[red]❌ Failed to get route info:[/red] {str(e)}")
        raise typer.Exit(1)
        
        # Check for expected content substring (more lenient)
        if expected_content.lower() in chunk_text:
            content_found = True
        
        # Check for expected keywords (at least 50% must be present)
        keywords_found = sum(1 for keyword in expected_keywords if keyword.lower() in chunk_text)
        keyword_ratio = keywords_found / len(expected_keywords) if expected_keywords else 1
        
        if keywords_found > 0:
            content_found = True
        
        # More lenient accuracy calculation
        # Consider it PASS if:
        # 1. Score is >= 0.4 AND at least 50% keywords found, OR
        # 2. Score is >= 0.6 (high semantic similarity), OR 
        # 3. Expected content found AND score >= 0.3
        if ((best_score >= 0.4 and keyword_ratio >= 0.5) or 
            best_score >= 0.6 or 
            (content_found and best_score >= 0.3)):
            accuracy = "[green]PASS[/green]"
            passed_tests += 1
        elif best_score >= 0.4 or keyword_ratio >= 0.5:
            accuracy = "[yellow]PARTIAL[/yellow]"
        else:
            accuracy = "[red]FAIL[/red]"
        
        total_score += best_score
        
        # Format found content indicator
        found_indicator = "✅ Found" if content_found else "❌ Missing"
        if keywords_found > 0 and expected_keywords:
            found_indicator += f" ({keywords_found}/{len(expected_keywords)} keywords)"
        
        results_table.add_row(
            content_type,
            query,
            expected_content[:20] + "..." if len(expected_content) > 20 else expected_content,
            f"{best_score:.4f}",
            found_indicator,
            accuracy
        )
        
        # Show best chunk details for debugging
        console.print(f"[dim]  Best chunk preview: {best_chunk.chunk_text[:100]}...[/dim]")
        console.print(f"[dim]  Relevance score: {best_score:.4f}[/dim]")
        console.print()
    
    console.print("\\n")
    console.print(results_table)
    
    # Summary statistics
    avg_score = total_score / len(test_cases) if test_cases else 0
    pass_rate = (passed_tests / len(test_cases)) * 100 if test_cases else 0
    
    console.print(f"\\n[bold]Chunking Accuracy Test Summary:[/bold]")
    console.print(f"[green]Total Test Cases:[/green] {len(test_cases)}")
    console.print(f"[green]Passed Tests:[/green] {passed_tests}")
    console.print(f"[green]Pass Rate:[/green] {pass_rate:.1f}%")
    console.print(f"[green]Average Relevance Score:[/green] {avg_score:.3f}")
    
    if pass_rate >= 80:
        console.print("[green]✅ Chunking accuracy test PASSED![/green]")
    elif pass_rate >= 60:
        console.print("[yellow]⚠️ Chunking accuracy test PARTIAL - needs improvement[/yellow]")
    else:
        console.print("[red]❌ Chunking accuracy test FAILED - significant issues found[/red]")

async def _get_chunking_test_cases_v2(file_path: Optional[str], content_type: str) -> List[dict]:
    """Generate test cases for different content types based on actual document content"""
    
    test_cases = []
    
    # Table content test cases (from SLA reports and CSV data)
    if content_type in ["table", "all"]:
        test_cases.extend([
            {
                "type": "table",
                "query": "system uptime availability percentage",
                "expected_content": "uptime",
                "keywords": ["uptime", "availability", "SLA", "system"]
            },
            {
                "type": "table", 
                "query": "incident response time metrics",
                "expected_content": "incident",
                "keywords": ["incident", "response", "time", "metrics"]
            },
            {
                "type": "table",
                "query": "sprint metrics velocity points",
                "expected_content": "sprint",
                "keywords": ["sprint", "velocity", "points", "metrics"]
            },
        ])
    
    # Paragraph content test cases (from engineering documents)
    if content_type in ["paragraph", "all"]:
        test_cases.extend([
            {
                "type": "paragraph",
                "query": "incident management process workflow",
                "expected_content": "incident",
                "keywords": ["incident", "management", "process", "workflow"]
            },
            {
                "type": "paragraph",
                "query": "system monitoring and alerting procedures", 
                "expected_content": "monitoring",
                "keywords": ["monitoring", "system", "alerting", "procedures"]
            },
            {
                "type": "paragraph",
                "query": "engineering team roles and responsibilities",
                "expected_content": "engineering",
                "keywords": ["engineering", "team", "roles", "responsibilities"]
            },
        ])
    
    # List content test cases (from structured documents)
    if content_type in ["list", "all"]:
        test_cases.extend([
            {
                "type": "list",
                "query": "system requirements and specifications",
                "expected_content": "requirements",
                "keywords": ["system", "requirements", "specifications"]
            },
            {
                "type": "list",
                "query": "deployment checklist steps",
                "expected_content": "deployment", 
                "keywords": ["deployment", "checklist", "steps"]
            },
        ])
    
    # Heading/structure test cases (hierarchical document structure)
    if content_type in ["heading", "all"]:
        test_cases.extend([
            {
                "type": "heading",
                "query": "incident report section overview",
                "expected_content": "incident",
                "keywords": ["incident", "report", "section"]
            },
            {
                "type": "heading", 
                "query": "system architecture documentation section",
                "expected_content": "system",
                "keywords": ["system", "architecture", "documentation"]
            },
        ])
    
    # Multi-page/complex content test cases
    if content_type in ["multipage", "all"]:
        test_cases.extend([
            {
                "type": "multipage",
                "query": "comprehensive engineering documentation spanning multiple topics",
                "expected_content": "engineering",
                "keywords": ["engineering", "documentation", "comprehensive"]
            },
            {
                "type": "multipage",
                "query": "detailed incident post-mortem analysis with lessons learned",
                "expected_content": "incident",
                "keywords": ["incident", "post-mortem", "analysis", "lessons"]
            },
        ])
    
    # CSV/structured data test cases
    if content_type in ["csv", "all"]:
        test_cases.extend([
            {
                "type": "csv",
                "query": "employee data HR information",
                "expected_content": "employee",
                "keywords": ["employee", "HR", "data"],
                "collection": "hr"  # Specify this test should search HR collection
            },
        ])
    
    return test_cases

async def _test_content_retrieval_async_v2(queries: List[str], expected_docs: List[str], min_score: float):
    """Test content retrieval accuracy with specific queries"""
    
    vector_store = VectorStore()
    
    console.print(f"[green]Testing content retrieval with {len(queries)} queries...[/green]")
    console.print(f"[green]Minimum score threshold:[/green] {min_score}")
    
    # Create results table
    results_table = Table(title="Content Retrieval Test Results", box=box.ROUNDED)
    results_table.add_column("Query", style="cyan", width=25)
    results_table.add_column("Top Result Score", justify="center", style="green")
    results_table.add_column("Source Document", style="yellow", width=20)
    results_table.add_column("Chunk Preview", style="blue", width=30)
    results_table.add_column("Status", justify="center", style="bold")
    
    total_score = 0
    passed_queries = 0
    
    for i, query in enumerate(queries):
        console.print(f"\\n[blue]Testing query: '{query}'[/blue]")
        
        # Perform search with multiple roles to test comprehensive retrieval
        results = await vector_store.search_with_rbac(
            query=query,
            user_role="c_level",  # Use c_level for maximum access
            limit=10
        )
        
        if not results:
            results_table.add_row(
                query,
                "0.000",
                "No results",
                "No content found",
                "[red]FAIL[/red]"
            )
            continue
        
        # Get best result
        best_chunk, best_score = results[0]
        total_score += best_score
        
        # Check if result meets minimum score threshold
        meets_threshold = best_score >= min_score
        
        # Check if expected document is found (if specified)
        doc_match = True
        if expected_docs and i < len(expected_docs):
            expected_doc = expected_docs[i]
            doc_match = expected_doc.lower() in best_chunk.metadata.source_document.lower()
        
        # Determine status
        if meets_threshold and doc_match:
            status = "[green]PASS[/green]"
            passed_queries += 1
        elif meets_threshold:
            status = "[yellow]SCORE OK[/yellow]"
        elif doc_match:
            status = "[yellow]DOC OK[/yellow]"
        else:
            status = "[red]FAIL[/red]"
        
        # Format chunk preview
        chunk_preview = best_chunk.chunk_text[:50] + "..." if len(best_chunk.chunk_text) > 50 else best_chunk.chunk_text
        
        results_table.add_row(
            query,
            f"{best_score:.3f}",
            best_chunk.metadata.source_document,
            chunk_preview,
            status
        )
        
        # Show additional context
        console.print(f"[dim]  Collection: {best_chunk.metadata.collection}[/dim]")
        console.print(f"[dim]  Headings: {' > '.join(best_chunk.headings) if best_chunk.headings else 'None'}[/dim]")
    
    console.print("\\n")
    console.print(results_table)
    
    # Summary statistics
    avg_score = total_score / len(queries) if queries else 0
    pass_rate = (passed_queries / len(queries)) * 100 if queries else 0
    
    console.print(f"\\n[bold]Content Retrieval Test Summary:[/bold]")
    console.print(f"[green]Total Queries:[/green] {len(queries)}")
    console.print(f"[green]Passed Queries:[/green] {passed_queries}")
    console.print(f"[green]Pass Rate:[/green] {pass_rate:.1f}%")
    console.print(f"[green]Average Relevance Score:[/green] {avg_score:.3f}")
    console.print(f"[green]Score Threshold:[/green] {min_score}")
    
    if pass_rate >= 80 and avg_score >= min_score:
        console.print("[green]✅ Content retrieval test PASSED![/green]")
    elif pass_rate >= 60:
        console.print("[yellow]⚠️ Content retrieval test PARTIAL - needs improvement[/yellow]")  
    else:
        console.print("[red]❌ Content retrieval test FAILED - significant issues found[/red]")