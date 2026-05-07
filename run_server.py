#!/usr/bin/env python3
"""
Simple FastAPI server launcher - no debugging required
Run this directly from terminal or VS Code
"""

import subprocess
import sys
import os
import webbrowser
import time
import threading
import asyncio
from typing import Optional


def check_database_connection() -> bool:
    """Check if Qdrant database is running"""
    try:
        from qdrant_client import QdrantClient
        from src.core.config import settings
        
        client = QdrantClient(url=settings.qdrant_url)
        # Try to get collection list to test connection
        collections = client.get_collections()
        print(f"✅ Qdrant database is running at {settings.qdrant_url}")
        print(f"📊 Found {len(collections.collections)} existing collections")
        return True
    except Exception as e:
        print(f"❌ Qdrant database connection failed: {e}")
        print("💡 Make sure Qdrant is running:")
        print("   docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant")
        return False

async def ensure_collections() -> bool:
    """Ensure required collections exist in the database"""
    try:
        from src.core.store.vector_store import VectorStore
        
        print("🔧 Checking vector store collections...")
        vector_store = VectorStore()
        
        # Initialize collection (creates if doesn't exist)
        success = await vector_store.initialize_collection(recreate=False)
        
        if success:
            print("✅ Vector store collections are ready")
            # Now check if collections have documents
            return await check_document_counts(vector_store)
        else:
            print("❌ Failed to initialize vector store collections")
            return False
            
    except Exception as e:
        print(f"❌ Collection setup failed: {e}")
        return False

async def check_document_counts(vector_store) -> bool:
    """Check if collections have documents and provide statistics"""
    try:
        from qdrant_client.http.models import Filter, FieldCondition, MatchValue
        
        print("📊 Checking document counts in collections...")
        
        # Get collection info
        collection_info = await asyncio.get_event_loop().run_in_executor(
            None, vector_store.client.get_collection, vector_store.collection_name
        )
        
        total_points = collection_info.points_count
        print(f"📈 Total documents in database: {total_points}")
        
        if total_points == 0:
            print("⚠️  No documents found in collections!")
            print("💡 Run document ingestion first:")
            print("   python -m src.cli ingest documents --collection all")
            return False
            
        # Check document counts by collection type
        collection_stats = {}
        collection_types = ['hr', 'finance', 'engineering', 'marketing', 'general']
        
        for collection_type in collection_types:
            try:
                # Count documents for each collection type
                filter_condition = Filter(
                    must=[
                        FieldCondition(
                            key="collection", 
                            match=MatchValue(value=collection_type)
                        )
                    ]
                )
                
                scroll_result = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: vector_store.client.scroll(
                        collection_name=vector_store.collection_name,
                        scroll_filter=filter_condition,
                        limit=1,  # Just count, don't fetch data
                        with_payload=False,
                        with_vectors=False
                    )
                )
                
                # Get actual count using count API
                count_result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: vector_store.client.count(
                        collection_name=vector_store.collection_name,
                        count_filter=filter_condition,
                        exact=True
                    )
                )
                
                collection_stats[collection_type] = count_result.count
                
            except Exception as e:
                print(f"⚠️  Could not get count for {collection_type}: {e}")
                collection_stats[collection_type] = 0
        
        # Display statistics
        print("\n📋 Collection Statistics:")
        total_found = 0
        for collection_type, count in collection_stats.items():
            status = "✅" if count > 0 else "❌"
            print(f"   {status} {collection_type}: {count} documents")
            total_found += count
            
        if total_found == 0:
            print("\n⚠️  No documents found in any collection!")
            print("💡 Run document ingestion:")
            print("   python -m src.cli ingest documents --collection all")
            return False
        elif total_found < total_points:
            print(f"\n⚠️  Some documents ({total_points - total_found}) may not be properly categorized")
            
        print(f"\n✅ Found {total_found} documents across collections")
        return True
        
    except Exception as e:
        print(f"❌ Document count check failed: {e}")
        # Don't fail completely, just warn
        print("⚠️  Proceeding without document count verification")
        return True

def setup_database() -> bool:
    """Setup database connection and collections"""
    print("\\n🔍 Checking database setup...")
    
    # Check if database is running
    if not check_database_connection():
        return False
    
    # Ensure collections exist
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        collections_ready = loop.run_until_complete(ensure_collections())
        loop.close()
        
        if not collections_ready:
            print("❌ Database collections are not ready")
            return False
            
        print("✅ Database setup complete")
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False

def check_dependencies() -> bool:
    """Check if required packages are installed"""
    try:
        import uvicorn
        import fastapi
        print("✅ FastAPI and Uvicorn are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("💡 Install with: pip install fastapi uvicorn")
        return False

def open_browser_delayed():
    """Open browser after server starts"""
    time.sleep(3)  # Wait for server startup
    try:
        webbrowser.open("http://localhost:8000/docs")
        print("🌐 Opened Swagger UI in browser")
    except Exception as e:
        print(f"⚠️  Could not open browser: {e}")
        print("   Manually visit: http://localhost:8000/docs")

def main():
    """Main launcher function"""
    print("🚀 FinBot API Server Launcher")
    print("=" * 40)
    
    # Set working directory and Python path first (needed for imports)
    project_root = "/Users/santhosh_simha/Personal/Learnings/codebasics-live/Assignment-1-FinBot/finbot"
    os.chdir(project_root)
    os.environ["PYTHONPATH"] = project_root
    
    print(f"📁 Working directory: {os.getcwd()}")
    print(f"🐍 Python path: {project_root}")
    
    # Check dependencies
    if not check_dependencies():
        return
        
    # Check database setup
    if not setup_database():
        return
    
    # Start browser opener in background
    threading.Thread(target=open_browser_delayed, daemon=True).start()
    
    # Launch server
    print("\\n🌐 Starting server...")
    print("   - API: http://localhost:8000")
    print("   - Swagger UI: http://localhost:8000/docs")
    print("   - Press Ctrl+C to stop")
    print("-" * 40)
    
    try:
        # Run uvicorn directly
        cmd = [
            sys.executable, 
            "-m", "uvicorn",
            "src.api.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload",
            "--reload-dir", "src"
        ]
        
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\\n\\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server failed to start: {e}")

if __name__ == "__main__":
    main()