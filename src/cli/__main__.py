#!/usr/bin/env python3
"""
FinBot CLI - Document ingestion and management commands
"""

import typer
from rich.console import Console
from rich.progress import Progress, TaskID
from pathlib import Path
from typing import Optional, List
import asyncio

from src.cli.ingest import ingest_app
from src.cli.test import test_app
from src.core.config import Settings

# Create the main CLI app
app = typer.Typer(
    name="finbot",
    help="FinBot CLI - Advanced RAG system with RBAC for FinSolve Technologies",
    rich_markup_mode="rich"
)

# Add subcommands
app.add_typer(ingest_app, name="ingest")
app.add_typer(test_app, name="test")

console = Console()

@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind the server to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind the server to"),
    reload: bool = typer.Option(True, "--reload/--no-reload", help="Enable auto-reload on code changes"),
):
    """Start the FinBot API server"""
    import uvicorn
    from src.api.main import app as api_app
    
    console.print(f"[green]🚀 Starting FinBot API Server[/green]")
    console.print(f"[blue]📍 Server will be available at: http://{host}:{port}[/blue]")
    console.print(f"[blue]📖 API Documentation: http://{host}:{port}/docs[/blue]")
    console.print(f"[blue]🔄 Auto-reload: {'enabled' if reload else 'disabled'}[/blue]")
    
    try:
        uvicorn.run(
            "src.api.main:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped by user[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Failed to start server: {str(e)}[/red]")
        raise typer.Exit(1)

@app.command()
def info():
    """Show FinBot system information"""
    settings = Settings()
    console.print(f"""
[bold blue]FinBot System Information[/bold blue]
[green]Version:[/green] 0.1.0
[green]Data Directory:[/green] {settings.data_dir}
[green]Vector Store:[/green] Qdrant ({settings.qdrant_url})
[green]Embedding Model:[/green] {settings.embedding_model}
    """)

@app.command()
def validate():
    """Validate system configuration and dependencies"""
    console.print("[yellow]Validating FinBot configuration...[/yellow]")
    
    # Check if required directories exist
    data_dir = Path("data")
    if not data_dir.exists():
        console.print("[red]❌ Data directory not found[/red]")
        return
    
    collections = ["general", "finance", "engineering", "marketing"]
    missing_collections = []
    
    for collection in collections:
        collection_dir = data_dir / collection
        if not collection_dir.exists():
            missing_collections.append(collection)
    
    if missing_collections:
        console.print(f"[red]❌ Missing collections: {', '.join(missing_collections)}[/red]")
    else:
        console.print("[green]✅ All document collections found[/green]")
    
    console.print("[green]✅ Configuration validation complete[/green]")

if __name__ == "__main__":
    app()