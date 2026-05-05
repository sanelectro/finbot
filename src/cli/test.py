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
    
    # Show chunk analysis
    chunk_types = {}
    section_titles = set()
    
    for chunk in processed_doc.chunks:
        chunk_type = chunk.metadata.chunk_type
        chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
        section_titles.add(chunk.metadata.section_title)
    
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
• Section: {chunk.metadata.section_title}
• Type: {chunk.metadata.chunk_type}
• Hierarchy Level: {chunk.metadata.hierarchy_level}
• Access Roles: {", ".join(chunk.metadata.access_roles)}
• Page: {chunk.metadata.page_number or "N/A"}
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
    
    # Perform search
    start_time = time.time()
    results = await vector_store.search_with_rbac(
        query=query,
        user_role=role,
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
            chunk.metadata.section_title,
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
        results = await vector_store.search_with_rbac(
            query=query,
            user_role=role, 
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