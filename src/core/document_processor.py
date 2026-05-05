"""
Document processor using Docling with HierarchicalChunker (simplified)
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging
from docling.document_converter import DocumentConverter, ConversionResult
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import DoclingDocument
from docling.chunking import HierarchicalChunker
import hashlib
import time

from src.models.document import (
    DocumentChunk, 
    DocumentMetadata, 
    ProcessedDocument, 
    Collection,
    Role
)
from src.core.config import settings

logger = logging.getLogger(__name__)

class HierarchicalDocumentProcessor:
    """
    Simplified document processor using native Docling HierarchicalChunker
    """
    
    def __init__(self):
        self.converter = DocumentConverter()
        self.settings = settings
        
    def load_document(self, source: str) -> DoclingDocument:
        """
        Parse a document using Docling.
        Returns a DoclingDocument object.
        """
        result = self.converter.convert(source)
        return result.document
        
    async def process_document(
        self, 
        file_path: Path, 
        collection: Collection,
        access_roles: Optional[List[Role]] = None
    ) -> ProcessedDocument:
        """
        Process a single document using native Docling HierarchicalChunker
        
        Args:
            file_path: Path to the document file
            collection: Document collection (general, finance, engineering, marketing)
            access_roles: Optional list of roles, defaults to collection-based roles
            
        Returns:
            ProcessedDocument with simplified chunks
        """
        start_time = time.time()
        
        if access_roles is None:
            access_roles = self.settings.collection_access_roles.get(collection, [])
        
        logger.info(f"Processing document: {file_path} for collection: {collection}")
        
        try:
            # Load document using Docling
            doc = await asyncio.get_event_loop().run_in_executor(
                None, 
                self.load_document,
                str(file_path)
            )
            
            # Use native HierarchicalChunker
            chunker = HierarchicalChunker()
            doc_chunks = list(chunker.chunk(doc))
            
            # Convert to our simplified format
            chunks = []
            for doc_chunk in doc_chunks:
                chunk_dict = self.convert_chunk(doc_chunk)
                
                # Create simplified chunk
                chunk = DocumentChunk(
                    headings=chunk_dict["headings"],
                    content=chunk_dict["content"],
                    chunk_text=chunk_dict["chunk_text"],
                    metadata=DocumentMetadata(
                        collection=collection,
                        access_roles=access_roles,
                        source_document=file_path.name,
                        document_path=str(file_path)
                    )
                )
                chunks.append(chunk)
            
            processing_time = time.time() - start_time
            
            processed_doc = ProcessedDocument(
                source_path=file_path,
                collection=collection,
                access_roles=access_roles,
                chunks=chunks,
                file_size=file_path.stat().st_size,
                processing_time=processing_time,
                total_pages=None  # Could extract from doc if needed
            )
            
            logger.info(f"Successfully processed {file_path}: {len(chunks)} chunks in {processing_time:.2f}s")
            return processed_doc
            
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {str(e)}")
            raise
    
    def convert_chunk(self, doc_chunk) -> dict:
        """
        Convert a Docling DocChunk into a plain dict.

        headings   → list preserved as-is
        content    → paragraph text
        chunk_text → breadcrumb + content  (what gets embedded)
        """
        headings = doc_chunk.meta.headings or []
        content = doc_chunk.text.strip()
        breadcrumb = " > ".join(headings)
        chunk_text = f"{breadcrumb}\n\n{content}" if breadcrumb else content

        return {
            "headings": headings,
            "content": content,
            "chunk_text": chunk_text,
        }
