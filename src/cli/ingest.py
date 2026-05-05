"""
CLI commands for document ingestion
"""

import typer
import asyncio
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.progress import Progress, TaskID, track
from rich.table import Table
from rich import box
import time

from src.core.config import settings
from src.core.document_processor import HierarchicalDocumentProcessor
from src.core.vector_store import VectorStore
from src.models.document import IngestionStatus, Collection
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the ingest subcommand
ingest_app = typer.Typer(
    name="ingest",
    help="Document ingestion commands",
    rich_markup_mode="rich"
)

console = Console()

@ingest_app.command("documents")
def ingest_documents(
    collection: str = typer.Option(
        "all", 
        "--collection", 
        "-c",
        help="Collection to ingest: all, general, finance, engineering, marketing"
    ),
    data_dir: Optional[str] = typer.Option(
        None,
        "--data-dir",
        "-d", 
        help="Path to data directory (defaults to ./data)"
    ),
    files_str: Optional[str] = typer.Option(
        None,
        "--files",
        "-f",
        help="Specific files to ingest (comma-separated, relative to data directory)"
    ),
    recreate_collection: bool = typer.Option(
        False,
        "--recreate",
        "-r",
        help="Recreate the vector collection (deletes existing data)"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be processed without actually ingesting"
    )
):
    """
    Ingest documents into the vector store with hierarchical chunking and RBAC metadata
    
    This command processes documents from the data directory, creates hierarchical
    chunks using Docling, and stores them in Qdrant with proper RBAC metadata.
    
    Examples:
        # Ingest all documents in engineering collection
        python -m src.cli ingest documents --collection engineering
        
        # Ingest specific files only
        python -m src.cli ingest documents --files engineering/system_sla_report_2024.md
        
        # Ingest multiple specific files (comma-separated)
        python -m src.cli ingest documents --files "engineering/report1.md,finance/budget.pdf"
        
        # Re-ingest a single modified file (removes old chunks first)
        python -m src.cli ingest documents --files engineering/updated_report.md
    """
    
    # Validate collection parameter
    valid_collections = ["all", "general", "finance", "engineering", "marketing"]
    if collection not in valid_collections:
        console.print(f"[red]Error:[/red] Invalid collection '{collection}'. Must be one of: {', '.join(valid_collections)}")
        raise typer.Exit(1)
    
    # Set data directory
    if data_dir:
        data_path = Path(data_dir)
    else:
        data_path = settings.data_dir
    
    if not data_path.exists():
        console.print(f"[red]Error:[/red] Data directory not found: {data_path}")
        raise typer.Exit(1)
    
    # Run the async ingestion process
    try:
        asyncio.run(_run_ingestion(
            collection=collection,
            data_path=data_path,
            files_str=files_str,
            recreate_collection=recreate_collection,
            dry_run=dry_run
        ))
    except KeyboardInterrupt:
        console.print("\\n[yellow]Ingestion cancelled by user[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"\\n[red]Ingestion failed:[/red] {str(e)}")
        raise typer.Exit(1)

@ingest_app.command("status")
def show_status():
    """Show status of the vector store and document collections"""
    
    try:
        asyncio.run(_show_vector_store_status())
    except Exception as e:
        console.print(f"[red]Error getting status:[/red] {str(e)}")
        raise typer.Exit(1)

async def _run_ingestion(
    collection: str,
    data_path: Path,
    files_str: Optional[str],
    recreate_collection: bool,
    dry_run: bool
):
    """Main async ingestion process"""
        # Parse files from string
    files = []
    if files_str:
        files = [f.strip() for f in files_str.split(',') if f.strip()]
        console.print(f"\\n[bold blue]FinBot Document Ingestion[/bold blue]")
    console.print(f"[green]Data Directory:[/green] {data_path}")
    console.print(f"[green]Collection:[/green] {collection}")
    if files:
        console.print(f"[green]Specific Files:[/green] {', '.join(files)}")
    console.print(f"[green]Recreate Collection:[/green] {recreate_collection}")
    console.print(f"[green]Dry Run:[/green] {dry_run}")
    
    # Initialize components
    processor = HierarchicalDocumentProcessor()
    vector_store = VectorStore()
    
    # Determine which collections to process
    if collection == "all":
        collections_to_process = ["general", "finance", "engineering", "marketing"]
    else:
        collections_to_process = [collection]
    
    # Discover documents
    if files:
        # Process specific files
        document_files = _discover_specific_files(data_path, files)
        if not document_files:
            console.print(f"[red]Error:[/red] No valid files found from the specified list")
            return
    else:
        # Process by collection
        document_files = _discover_documents(data_path, collections_to_process)
    
    if not document_files:
        console.print("[yellow]No documents found to process[/yellow]")
        return
    
    # Show summary
    _show_ingestion_summary(document_files, dry_run)
    
    if dry_run:
        console.print("\\n[yellow]Dry run complete - no documents were actually processed[/yellow]")
        return
    
    # Confirm before proceeding
    if not typer.confirm("\\nProceed with ingestion?"):
        console.print("[yellow]Ingestion cancelled[/yellow]")
        return
    
    # Initialize vector store
    console.print("\\n[blue]Initializing vector store...[/blue]")
    if not await vector_store.initialize_collection(recreate=recreate_collection):
        console.print("[red]Failed to initialize vector store[/red]")
        return    
    # If processing specific files, remove existing chunks first
    if files and not recreate_collection:
        console.print("\n[blue]Removing existing chunks for specified files...[/blue]")
        for collection_name, file_path in document_files:
            relative_path = str(file_path.relative_to(data_path))
            await vector_store.remove_document_chunks(relative_path)
            console.print(f"[yellow]Removed chunks for:[/yellow] {relative_path}")    
    # Track ingestion status
    status = IngestionStatus(total_documents=len(document_files))
    processed_documents = []
    
    # Process documents with progress bar
    with Progress(console=console) as progress:
        task = progress.add_task(
            f"[green]Processing documents...", 
            total=len(document_files)
        )
        
        for collection_name, file_path in document_files:
            try:
                # Get access roles for this collection
                access_roles = settings.collection_access_roles.get(collection_name, [])
                
                progress.update(
                    task, 
                    description=f"[green]Processing {file_path.name}..."
                )
                
                # Process document
                processed_doc = await processor.process_document(
                    file_path, 
                    collection_name, 
                    access_roles
                )
                processed_documents.append(processed_doc)
                
                status.processed_documents += 1
                status.total_chunks += len(processed_doc.chunks)
                
                if collection_name not in status.collections_processed:
                    status.collections_processed.append(collection_name)
                
                progress.advance(task)
                
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {str(e)}")
                status.failed_documents += 1
                status.errors.append(f"{file_path.name}: {str(e)}")
                progress.advance(task)
    
    # Store documents in vector store
    if processed_documents:
        console.print("\\n[blue]Storing documents in vector store...[/blue]")
        
        if await vector_store.store_documents(processed_documents):
            console.print("[green]✅ All documents stored successfully[/green]")
        else:
            console.print("[red]❌ Failed to store some documents[/red]")
    
    # Show final status
    status.end_time = status.start_time.__class__.utcnow()
    _show_ingestion_results(status)

def _discover_documents(
    data_path: Path, 
    collections: List[str]
) -> List[tuple]:
    """Discover documents in the specified collections"""
    
    document_files = []
    
    for collection_name in collections:
        collection_dir = data_path / collection_name
        
        if not collection_dir.exists():
            console.print(f"[yellow]Warning:[/yellow] Collection directory not found: {collection_dir}")
            continue
        
        # Get supported file extensions for this collection
        supported_extensions = settings.collection_file_types.get(collection_name, [])
        
        # Find all files with supported extensions
        for ext in supported_extensions:
            pattern = f"*{ext}"
            files = list(collection_dir.glob(pattern))
            for file_path in files:
                if file_path.is_file():
                    document_files.append((collection_name, file_path))
    
    # Sort by collection and filename for consistent processing order
    document_files.sort(key=lambda x: (x[0], x[1].name))
    
    return document_files

def _discover_specific_files(
    data_path: Path,
    files: List[str]
) -> List[tuple]:
    """Discover specific files and determine their collections"""
    
    document_files = []
    
    for file_spec in files:
        # Handle both absolute paths and relative paths
        if file_spec.startswith('/'):
            file_path = Path(file_spec)
        else:
            file_path = data_path / file_spec
        
        if not file_path.exists():
            console.print(f"[red]Warning:[/red] File not found: {file_spec}")
            continue
        
        if not file_path.is_file():
            console.print(f"[red]Warning:[/red] Not a file: {file_spec}")
            continue
        
        # Determine collection from file path
        try:
            relative_to_data = file_path.relative_to(data_path)
            collection_name = relative_to_data.parts[0]  # First directory is collection
            
            # Validate collection name
            valid_collections = ["general", "finance", "engineering", "marketing"]
            if collection_name not in valid_collections:
                console.print(f"[yellow]Warning:[/yellow] Unknown collection '{collection_name}' for file: {file_spec}")
                console.print(f"[yellow]Valid collections:[/yellow] {', '.join(valid_collections)}")
                continue
            
            # Check if file extension is supported for this collection
            file_extension = file_path.suffix.lower()
            supported_extensions = settings.collection_file_types.get(collection_name, [])
            
            if file_extension not in supported_extensions:
                console.print(f"[yellow]Warning:[/yellow] Unsupported file type '{file_extension}' for collection '{collection_name}': {file_spec}")
                console.print(f"[yellow]Supported types:[/yellow] {', '.join(supported_extensions)}")
                continue
            
            document_files.append((collection_name, file_path))
            
        except ValueError:
            # File is not under data_path
            console.print(f"[red]Error:[/red] File must be under data directory: {file_spec}")
            continue
    
    # Sort by collection and filename for consistent processing order
    document_files.sort(key=lambda x: (x[0], x[1].name))
    
    return document_files

def _show_ingestion_summary(document_files: List[tuple], dry_run: bool):
    """Show a summary of documents to be processed"""
    
    # Create summary table
    table = Table(
        title="Documents to Process" + (" (DRY RUN)" if dry_run else ""),
        box=box.ROUNDED
    )
    table.add_column("Collection", style="cyan")
    table.add_column("Document", style="green")
    table.add_column("Size", justify="right", style="yellow")
    table.add_column("Access Roles", style="magenta")
    
    # Group by collection for better display
    collection_counts = {}
    total_size = 0
    
    for collection_name, file_path in document_files:
        # Get file size
        file_size = file_path.stat().st_size
        size_str = _format_file_size(file_size)
        total_size += file_size
        
        # Get access roles
        access_roles = settings.collection_access_roles.get(collection_name, [])
        roles_str = ", ".join(access_roles)
        
        table.add_row(collection_name, file_path.name, size_str, roles_str)
        
        # Track counts
        collection_counts[collection_name] = collection_counts.get(collection_name, 0) + 1
    
    console.print("\\n")
    console.print(table)
    
    # Show summary statistics
    console.print(f"\\n[bold]Summary:[/bold]")
    console.print(f"  Total documents: {len(document_files)}")
    console.print(f"  Total size: {_format_file_size(total_size)}")
    console.print(f"  Collections: {', '.join(collection_counts.keys())}")
    
    for collection_name, count in collection_counts.items():
        console.print(f"    - {collection_name}: {count} documents")

def _show_ingestion_results(status: IngestionStatus):
    """Show final ingestion results"""
    
    console.print("\\n[bold blue]Ingestion Complete![/bold blue]")
    
    # Create results table
    table = Table(title="Ingestion Results", box=box.ROUNDED)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total Documents", str(status.total_documents))
    table.add_row("Successfully Processed", str(status.processed_documents))
    table.add_row("Failed", str(status.failed_documents))
    table.add_row("Total Chunks Created", str(status.total_chunks))
    table.add_row("Collections Processed", ", ".join(status.collections_processed))
    
    if status.processing_time:
        table.add_row("Processing Time", f"{status.processing_time:.2f} seconds")
    
    console.print("\\n")
    console.print(table)
    
    # Show errors if any
    if status.errors:
        console.print("\\n[bold red]Errors:[/bold red]")
        for error in status.errors:
            console.print(f"  [red]•[/red] {error}")

def _format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024**2:
        return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024**3:
        return f"{size_bytes/(1024**2):.1f} MB"
    else:
        return f"{size_bytes/(1024**3):.1f} GB"

async def _show_vector_store_status():
    """Show vector store status and statistics"""
    
    vector_store = VectorStore()
    
    try:
        stats = await vector_store.get_collection_stats()
        
        console.print(f"\\n[bold blue]Vector Store Status[/bold blue]")
        
        if stats:
            table = Table(title="Qdrant Collection Stats", box=box.ROUNDED)
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Collection Name", settings.collection_name)
            table.add_row("Total Points", str(stats.get("total_points", "Unknown")))
            table.add_row("Vector Dimension", str(stats.get("vector_size", "Unknown")))
            table.add_row("Distance Metric", str(stats.get("distance_metric", "Unknown")))
            table.add_row("Status", str(stats.get("status", "Unknown")))
            table.add_row("Optimizer OK", str(stats.get("optimizer_status", "Unknown")))
            
            console.print("\\n")
            console.print(table)
        else:
            console.print("[yellow]Could not retrieve collection statistics[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error connecting to vector store:[/red] {str(e)}")
        console.print(f"[yellow]Make sure Qdrant is running at:[/yellow] {settings.qdrant_url}")