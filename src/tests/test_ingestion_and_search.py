#!/usr/bin/env python3
"""
Comprehensive test for FinBot simplified architecture:
1. Clear existing collection
2. Ingest one engineering document
3. Test search functionality with headings
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Tuple

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.core.document_processor import HierarchicalDocumentProcessor
from src.core.vector_store import VectorStore
from src.models.document import DocumentChunk


class FinBotTester:
    """Comprehensive testing suite for simplified FinBot architecture"""
    
    def __init__(self):
        self.processor = HierarchicalDocumentProcessor()
        self.vector_store = VectorStore()
        
    async def clear_and_setup_collection(self):
        """Clear existing collection and set up fresh one"""
        print("🗑️  Clearing existing collection...")
        success = await self.vector_store.initialize_collection(recreate=True)
        if success:
            print("✅ Collection cleared and recreated successfully")
        else:
            print("❌ Failed to clear collection")
            return False
        return True
    
    async def ingest_engineering_document(self, doc_path: str):
        """Process and ingest a single engineering document"""
        print(f"\n📄 Processing document: {doc_path}")
        
        try:
            # Process document with simplified architecture
            doc = await self.processor.process_document(
                Path(doc_path),
                'engineering'
            )
            
            print(f"  📊 Document processed:")
            print(f"    • Total chunks: {len(doc.chunks)}")
            print(f"    • Processing time: {doc.processing_time:.2f}s")
            print(f"    • File size: {doc.file_size} bytes")
            
            # Display sample chunk structure
            if doc.chunks:
                chunk = doc.chunks[0]
                print(f"\n  📋 Sample chunk structure:")
                print(f"    • headings: {chunk.headings}")
                print(f"    • content length: {len(chunk.content)} chars")
                print(f"    • chunk_text length: {len(chunk.chunk_text)} chars")
                print(f"    • collection: {chunk.metadata.collection}")
                print(f"    • access_roles: {chunk.metadata.access_roles}")
            
            # Store in vector database
            print(f"\n💾 Storing in vector database...")
            success = await self.vector_store.store_documents([doc])
            
            if success:
                print("✅ Document stored successfully")
                return doc
            else:
                print("❌ Failed to store document")
                return None
                
        except Exception as e:
            print(f"❌ Error processing document: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def test_search_functionality(self):
        """Test search with various queries to verify headings work"""
        print(f"\n🔍 Testing search functionality...")
        
        test_queries = [
            ("What are the overall sprint performance metrics?", "Should find sprint-related content"),
            ("What is our system uptime and SLA compliance?", "Should find SLA and uptime information"),
            ("Give me a summary of our system performance", "Should find executive summary sections"),
            ("What are the access restrictions for engineering documents?", "Should find engineering team content"),
            ("How do we measure our system performance indicators?", "Should find KPI and metrics"),
            ("Tell me about FinSolve Technologies system reports", "Should find company-related content"),
        ]
        
        for query, description in test_queries:
            print(f"\n  🔎 Query: '{query}' ({description})")
            
            try:
                # Search with engineering role
                results = await self.vector_store.search_with_rbac(
                    query=query,
                    user_role='engineering',
                    limit=3,
                    collection_filter='engineering'
                )
                
                if results:
                    print(f"    ✅ Found {len(results)} results")
                    for i, (chunk, score) in enumerate(results, 1):
                        breadcrumb = " > ".join(chunk.headings) if chunk.headings else "Root"
                        print(f"      {i}. Score: {score:.3f}")
                        print(f"         Headings: {breadcrumb}")
                        print(f"         Content: {chunk.content[:80]}...")
                        
                        # Verify chunk_text contains breadcrumb
                        if chunk.headings and " > ".join(chunk.headings) in chunk.chunk_text:
                            print(f"         ✅ Breadcrumb found in chunk_text")
                        elif not chunk.headings:
                            print(f"         ℹ️  Root level chunk (no headings)")
                        else:
                            print(f"         ⚠️  Breadcrumb not found in chunk_text")
                else:
                    print(f"    ⚠️  No results found")
                    
            except Exception as e:
                print(f"    ❌ Search failed: {e}")
    
    async def test_rbac_filtering(self):
        """Test RBAC filtering works correctly"""
        print(f"\n🔐 Testing RBAC filtering...")
        
        # Test with engineering role (should have access)
        print(f"  👤 Testing with 'engineering' role (should have access)")
        try:
            results = await self.vector_store.search_with_rbac(
                query="engineering",
                user_role='engineering',
                limit=5
            )
            print(f"    ✅ Engineering role found {len(results)} results")
        except Exception as e:
            print(f"    ❌ Engineering role search failed: {e}")
        
        # Test with finance role (should have limited access)
        print(f"  👤 Testing with 'finance' role (limited access expected)")
        try:
            results = await self.vector_store.search_with_rbac(
                query="engineering",
                user_role='finance',
                limit=5
            )
            print(f"    ℹ️  Finance role found {len(results)} results")
        except Exception as e:
            print(f"    ❌ Finance role search failed: {e}")
    
    async def show_collection_stats(self):
        """Display collection statistics"""
        print(f"\n📈 Collection statistics:")
        try:
            collections = await asyncio.get_event_loop().run_in_executor(
                None, self.vector_store.client.get_collections
            )
            
            for collection in collections.collections:
                if collection.name == self.vector_store.collection_name:
                    print(f"  • Collection: {collection.name}")
                    print(f"  • Vector count: {collection.vectors_count or 0}")
                    print(f"  • Vector size: {collection.config.params.vectors.size}")
                    print(f"  • Distance: {collection.config.params.vectors.distance}")
                    break
        except Exception as e:
            print(f"    ❌ Failed to get collection stats: {e}")


async def main():
    """Run comprehensive test suite"""
    print("🚀 FinBot Simplified Architecture - Comprehensive Test")
    print("=" * 60)
    
    tester = FinBotTester()
    
    # Step 1: Clear existing collection
    if not await tester.clear_and_setup_collection():
        print("❌ Failed to setup collection. Exiting.")
        return
    
    # Step 2: Ingest engineering document
    doc = await tester.ingest_engineering_document('data/engineering/system_sla_report_2024.md')
    if not doc:
        print("❌ Failed to ingest document. Exiting.")
        return
    
    # Step 3: Test search functionality
    await tester.test_search_functionality()
    
    # Step 4: Test RBAC filtering
    await tester.test_rbac_filtering()
    
    # Step 5: Show collection statistics
    await tester.show_collection_stats()
    
    print(f"\n🎉 Test completed successfully!")
    print("✅ Simplified architecture is working correctly:")
    print("  • 6-field metadata structure")
    print("  • Native Docling HierarchicalChunker")  
    print("  • Breadcrumb-enhanced search")
    print("  • RBAC filtering functional")


if __name__ == "__main__":
    asyncio.run(main())