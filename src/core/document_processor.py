"""
Document processor using Docling with HierarchicalChunker (simplified)
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging
import csv
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
            # Check if this is a CSV file and use specialized processing
            if file_path.suffix.lower() == '.csv':
                chunks = await self.process_csv_document(file_path, collection, access_roles)
            else:
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
    
    async def process_csv_document(
        self, 
        file_path: Path, 
        collection: Collection,
        access_roles: List[Role]
    ) -> List[DocumentChunk]:
        """
        Process CSV files with specialized row-based chunking for better semantic search.
        Each row becomes a separate, semantically rich chunk.
        """
        logger.info(f"Processing CSV document with specialized chunking: {file_path}")
        
        chunks = []
        
        # Read CSV file
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            # Try to detect delimiter, fallback to comma
            try:
                sample = csvfile.read(1024)
                csvfile.seek(0)
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
            except csv.Error:
                # Fallback to comma if detection fails
                delimiter = ','
                logger.info(f"Delimiter detection failed, using comma as default for {file_path}")
            
            reader = csv.DictReader(csvfile, delimiter=delimiter)
            headers = reader.fieldnames
            
            # Process each row as a separate chunk
            for row_num, row in enumerate(reader, 1):
                chunk_text = self.create_semantic_csv_chunk(row, headers, file_path.name, row_num)
                
                # Create descriptive heading with actual field values
                field_values = [str(row.get(header, '')) for header in headers]
                heading = ', '.join(field_values)
                
                # Create chunk with semantic enhancement
                chunk = DocumentChunk(
                    headings=[heading],
                    content=chunk_text,
                    chunk_text=chunk_text,
                    metadata=DocumentMetadata(
                        collection=collection,
                        access_roles=access_roles,
                        source_document=file_path.name,
                        document_path=str(file_path)
                    )
                )
                chunks.append(chunk)
        
        logger.info(f"Created {len(chunks)} semantic chunks from CSV: {file_path}")
        return chunks
    
    def create_semantic_csv_chunk(self, row: Dict[str, str], headers: List[str], filename: str, row_num: int) -> str:
        """
        Convert a CSV row into semantically rich, natural language text.
        This dramatically improves embedding quality for structured data.
        """
        # Extract key employee information with semantic context
        employee_id = row.get('employee_id', 'N/A')
        full_name = row.get('full_name', 'Unknown')
        role = row.get('role', 'N/A')
        department = row.get('department', 'N/A')
        employment_type = row.get('employment_type', 'N/A')
        employment_status = row.get('employment_status', 'N/A')
        location = row.get('location', 'N/A')
        
        # Create natural language description
        semantic_text = f"""
Employee Data Record from {filename}

Employee Information:
- Employee ID: {employee_id}
- Full Name: {full_name}
- Role: {role} in {department} department
- Employment Type: {employment_type}
- Employment Status: {employment_status}
- Location: {location}

HR Data Summary: This record contains comprehensive employee information including personal details, role information, department assignment, and employment status. This data is suitable for HR analysis, employee management, workforce reporting, and organizational planning.

Key Fields Available: {', '.join(headers)}

Record Details:
"""
        
        # Add all field data in a structured way
        for header in headers:
            value = row.get(header, '')
            if value:  # Only include non-empty values
                semantic_text += f"- {header.replace('_', ' ').title()}: {value}\n"
        
        # Add searchable context
        semantic_text += f"""
\nSearch Context: employee data, HR information, {full_name}, {role}, {department}, employee record, staff information, workforce data, {employment_type} employee, {employment_status} status
"""
        
        return semantic_text.strip()
