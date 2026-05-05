"""
Qdrant vector store integration with RBAC metadata support
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from sentence_transformers import SentenceTransformer
import numpy as np

from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from qdrant_client.http.models import (
    VectorParams,
    Distance,
    CollectionInfo,
    PointStruct,
    Filter,
    FieldCondition,
    MatchAny,
    MatchValue,
    Range
)

from src.models.document import (
    DocumentChunk, 
    ProcessedDocument,
    Collection,
    Role
)
from src.core.config import settings

logger = logging.getLogger(__name__)

class VectorStore:
    """
    Qdrant vector store with RBAC metadata enforcement
    
    This class handles:
    - Storing document chunks with proper RBAC metadata
    - Enforcing role-based access control at the query level
    - Managing collection lifecycle
    """
    
    def __init__(self):
        self.client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key
        )
        self.embedding_model = SentenceTransformer(settings.embedding_model)
        self.collection_name = settings.collection_name
        
    async def initialize_collection(self, recreate: bool = False) -> bool:
        """
        Initialize the Qdrant collection with proper configuration
        
        Args:
            recreate: Whether to recreate collection if it exists
            
        Returns:
            True if collection was created/exists, False otherwise
        """
        try:
            # Check if collection exists
            collections = await asyncio.get_event_loop().run_in_executor(
                None, self.client.get_collections
            )
            
            collection_exists = any(
                col.name == self.collection_name 
                for col in collections.collections
            )
            
            if collection_exists and recreate:
                logger.info(f"Deleting existing collection: {self.collection_name}")
                await asyncio.get_event_loop().run_in_executor(
                    None, 
                    self.client.delete_collection,
                    self.collection_name
                )
                collection_exists = False
            
            if not collection_exists:
                logger.info(f"Creating collection: {self.collection_name}")
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.client.create_collection,
                    self.collection_name,
                    VectorParams(
                        size=settings.embedding_dimension,
                        distance=Distance.COSINE
                    )
                )
                
                # Create payload indexes for efficient RBAC filtering
                await self._create_payload_indexes()
                
            logger.info(f"Collection {self.collection_name} is ready")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize collection: {str(e)}")
            return False
    
    async def _create_payload_indexes(self):
        """Create indexes on RBAC metadata fields for efficient filtering"""
        
        indexes = [
            ("collection", rest.PayloadSchemaType.KEYWORD),
            ("access_roles", rest.PayloadSchemaType.KEYWORD), 
            ("source_document", rest.PayloadSchemaType.KEYWORD),
            ("section_title", rest.PayloadSchemaType.TEXT),
            ("chunk_type", rest.PayloadSchemaType.KEYWORD),
            ("page_number", rest.PayloadSchemaType.INTEGER)
        ]
        
        for field_name, field_type in indexes:
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.client.create_payload_index,
                    self.collection_name,
                    field_name,
                    field_type
                )
                logger.debug(f"Created index for field: {field_name}")
            except Exception as e:
                logger.warning(f"Failed to create index for {field_name}: {str(e)}")
    
    async def store_documents(self, documents: List[ProcessedDocument]) -> bool:
        """
        Store processed documents in Qdrant with RBAC metadata
        
        Args:
            documents: List of processed documents to store
            
        Returns:
            True if all documents stored successfully
        """
        try:
            all_chunks = []
            
            # Collect all chunks from all documents
            for doc in documents:
                all_chunks.extend(doc.chunks)
            
            if not all_chunks:
                logger.warning("No chunks to store")
                return True
            
            logger.info(f"Storing {len(all_chunks)} chunks from {len(documents)} documents")
            
            # Generate embeddings for all chunks
            await self._generate_embeddings(all_chunks)
            
            # Create Qdrant points
            points = []
            for i, chunk in enumerate(all_chunks):
                point = PointStruct(
                    id=i,
                    vector=chunk.embedding,
                    payload=self._chunk_to_payload(chunk)
                )
                points.append(point)
            
            # Store in batches to avoid memory issues
            batch_size = 100
            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.client.upsert,
                    self.collection_name,
                    batch
                )
                logger.debug(f"Stored batch {i//batch_size + 1}/{(len(points) + batch_size - 1)//batch_size}")
            
            logger.info(f"Successfully stored {len(all_chunks)} chunks")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store documents: {str(e)}")
            return False
    
    async def search_with_rbac(
        self, 
        query: str, 
        user_role: Role,
        limit: int = 10,
        collection_filter: Optional[Collection] = None,
        score_threshold: float = 0.0
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Search documents with RBAC enforcement
        
        This is the core RBAC enforcement method - it ensures users can only
        retrieve documents they have access to based on their role.
        
        Args:
            query: Search query
            user_role: User's role for RBAC filtering
            limit: Maximum number of results
            collection_filter: Optional filter by collection
            score_threshold: Minimum similarity score
            
        Returns:
            List of (chunk, score) tuples
        """
        try:
            # Generate query embedding
            query_embedding = await asyncio.get_event_loop().run_in_executor(
                None,
                self.embedding_model.encode,
                query
            )
            
            # Build RBAC filter - this is the critical security enforcement
            rbac_filter = Filter(
                must=[
                    FieldCondition(
                        key="access_roles",
                        match=MatchAny(any=[user_role])
                    )
                ]
            )
            
            # Add collection filter if specified
            if collection_filter:
                rbac_filter.must.append(
                    FieldCondition(
                        key="collection", 
                        match=MatchValue(value=collection_filter)
                    )
                )
            
            # Perform search with RBAC filter
            search_results = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_embedding.tolist(),
                    query_filter=rbac_filter,
                    limit=limit,
                    with_payload=True,
                    with_vectors=False
                ).points
            )
            
            # Convert results to DocumentChunk objects
            results = []
            for result in search_results:
                if result.score >= score_threshold:
                    chunk = self._payload_to_chunk(result.payload)
                    results.append((chunk, result.score))
            
            logger.info(f"RBAC search for role '{user_role}': {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            return []
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector collection"""
        try:
            info = await asyncio.get_event_loop().run_in_executor(
                None,
                self.client.get_collection,
                self.collection_name
            )
            
            # Handle different versions of Qdrant API
            optimizer_status = "unknown"
            if hasattr(info.optimizer_status, 'ok'):
                optimizer_status = info.optimizer_status.ok
            elif hasattr(info.optimizer_status, 'status'):
                optimizer_status = str(info.optimizer_status.status)
            else:
                optimizer_status = str(info.optimizer_status)
            
            return {
                "total_points": info.points_count,
                "vector_size": info.config.params.vectors.size,
                "distance_metric": info.config.params.vectors.distance.value,
                "status": info.status.value,
                "optimizer_status": optimizer_status
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {str(e)}")
            return {}
    
    async def _generate_embeddings(self, chunks: List[DocumentChunk]):
        """Generate embeddings for document chunks using chunk_text (breadcrumb + content)"""
        
        # Extract chunk_text (breadcrumb + content) from chunks for embedding
        contents = [chunk.chunk_text for chunk in chunks]
        
        # Generate embeddings in executor to avoid blocking
        def encode_with_progress():
            return self.embedding_model.encode(contents, show_progress_bar=True)
        
        embeddings = await asyncio.get_event_loop().run_in_executor(
            None,
            encode_with_progress
        )
        
        # Assign embeddings back to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding.tolist()
    
    def _chunk_to_payload(self, chunk: DocumentChunk) -> Dict[str, Any]:
        """Convert simplified DocumentChunk to Qdrant payload"""
        
        return {
            # Content fields
            "content": chunk.content,
            "chunk_text": chunk.chunk_text,  # This is what gets embedded
            "headings": chunk.headings,
            
            # RBAC metadata (critical for security)
            "collection": chunk.metadata.collection,
            "access_roles": chunk.metadata.access_roles,
            
            # Essential document metadata
            "source_document": chunk.metadata.source_document,
            "document_path": chunk.metadata.document_path,
            "chunk_id": chunk.metadata.chunk_id,
            "created_at": chunk.metadata.created_at.isoformat(),
        }
    
    def _payload_to_chunk(self, payload: Dict[str, Any]) -> DocumentChunk:
        """Convert Qdrant payload back to simplified DocumentChunk"""
        
        from src.models.document import DocumentMetadata
        from datetime import datetime
        
        metadata = DocumentMetadata(
            collection=payload["collection"],
            access_roles=payload["access_roles"],
            source_document=payload["source_document"],
            document_path=payload["document_path"],
            chunk_id=payload["chunk_id"],
            created_at=datetime.fromisoformat(payload["created_at"])
        )
        
        return DocumentChunk(
            headings=payload["headings"],
            content=payload["content"],
            chunk_text=payload["chunk_text"],
            metadata=metadata
        )

    async def remove_document_chunks(self, document_path: str) -> bool:
        """
        Remove all chunks for a specific document by its path
        
        Args:
            document_path: Relative path of the document to remove chunks for
            
        Returns:
            True if chunks were removed successfully
        """
        try:
            # Create filter to match chunks from the specific document
            document_filter = Filter(
                must=[
                    FieldCondition(
                        key="document_path",
                        match=MatchValue(value=document_path)
                    )
                ]
            )
            
            # Delete points matching the filter
            delete_result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=rest.FilterSelector(
                        filter=document_filter
                    )
                )
            )
            
            logger.info(f"Removed chunks for document: {document_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove chunks for {document_path}: {str(e)}")
            return False