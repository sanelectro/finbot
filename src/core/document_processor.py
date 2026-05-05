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
            # Get default access roles for collection
            access_roles_strings = self.settings.collection_access_roles.get(collection, [])
            # Cast strings to Role type for type safety
            from typing import cast
            access_roles = cast(List[Role], access_roles_strings)
        
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
                        embedding=None,  # Will be set when stored in vector DB
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
        Convert a Docling DocChunk into a plain dict optimized for vector search.
        
        Optimizations for cosine search:
        - Key information placed at the beginning
        - Semantic context enrichment
        - Consistent terminology and formatting
        """
        headings = doc_chunk.meta.headings or []
        content = doc_chunk.text.strip()
        
        # Create search-optimized chunk_text
        if headings:
            # Extract key terms from headings for prominence
            key_terms = self._extract_key_terms(headings)
            breadcrumb = " > ".join(headings)
            
            # Structure: Key terms + Breadcrumb + Content + Context
            chunk_text = f"Key Topics: {', '.join(key_terms)}\n\nDocument Section: {breadcrumb}\n\n{content}"
            
            # Add semantic context for better embeddings
            if key_terms:
                chunk_text += f"\n\nRelated Keywords: {', '.join(key_terms)}, document content, information"
        else:
            chunk_text = content

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
            headers_raw = reader.fieldnames
            
            # Ensure headers is not None and convert to List[str]
            if headers_raw is None:
                logger.error(f"No headers found in CSV file: {file_path}")
                return []
            headers = list(headers_raw)
            
            # Process each row as a separate chunk
            for row_num, row in enumerate(reader, 1):
                # Create content using semantic CSV chunk method
                content = self.create_semantic_csv_chunk(row, headers, file_path.name, row_num)
                
                # Create structured headings for better searchability
                headings = self.create_csv_headings(row, file_path.name)
                
                # OPTIMIZATION: Create search-optimized chunk_text with key terms first
                # This places the most important information at the beginning for better embedding weight
                employee_id = row.get('employee_id', 'N/A')
                full_name = row.get('full_name', 'Unknown')
                role = row.get('role', 'N/A')
                department = row.get('department', 'N/A')
                key_identifiers = [employee_id, full_name, role, department]
                key_identifiers = [item for item in key_identifiers if item and item != 'N/A' and item != 'Unknown']
                
                if key_identifiers:
                    identifier_text = " | ".join(key_identifiers)
                    # Natural language format: key identifiers + semantic content
                    chunk_text = f"{identifier_text}\n\n{content}"
                else:
                    chunk_text = content
                
                # Create chunk with enhanced structure
                chunk = DocumentChunk(
                    headings=headings,
                    content=content,
                    chunk_text=chunk_text,
                    embedding=None,  # Will be set when stored in vector DB
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
        Convert a CSV row into natural, human-readable semantic text for optimal LLM understanding.
        
        Following the High Accuracy Pattern:
        - Convert structured data → semantic text (MANDATORY)
        - Turn each row into human-understandable context
        - Natural language descriptions instead of field-value pairs
        """
        # Extract key employee information
        employee_id = row.get('employee_id', 'N/A')
        full_name = row.get('full_name', 'Unknown')
        role = row.get('role', 'N/A')
        department = row.get('department', 'N/A')
        employment_status = row.get('employment_status', 'N/A')
        location = row.get('location', 'N/A')
        attendance_pct = row.get('attendance_pct', '')
        performance_rating = row.get('performance_rating', '')
        designation_level = row.get('designation_level', '')
        employment_type = row.get('employment_type', 'N/A')
        salary = row.get('salary', '')
        manager_id = row.get('manager_id', '')
        email = row.get('email', '')
        phone = row.get('phone', '')
        date_of_joining = row.get('date_of_joining', '')
        
        # PRIMARY SEMANTIC TEXT: Natural language description
        semantic_text = f"Employee {full_name} (ID: {employee_id}) works as a {role} in the {department} department."
        
        # Add performance and attendance context
        if attendance_pct:
            attendance_desc = "high" if float(attendance_pct) >= 90 else "good" if float(attendance_pct) >= 80 else "average"
            semantic_text += f" They have {attendance_desc} attendance of {attendance_pct} percent"
            
        if performance_rating:
            rating_desc = "excellent" if float(performance_rating) >= 4 else "strong" if float(performance_rating) >= 3 else "satisfactory"
            semantic_text += f" and a {rating_desc} performance rating of {performance_rating}."
        else:
            semantic_text += "."
            
        # Add organizational context
        if designation_level and designation_level != 'N/A':
            semantic_text += f" They are a {designation_level}-level employee"
            
        if location and location != 'N/A':
            semantic_text += f" based in {location}."
        else:
            semantic_text += "."
            
        # Add employment details in natural language
        if employment_status == 'Active':
            semantic_text += f" This is an active {employment_type.lower()} employee"
        elif employment_status == 'Resigned':
            semantic_text += f" This employee has resigned from their {employment_type.lower()} position"
        else:
            semantic_text += f" Employment status: {employment_status}"
            
        if date_of_joining:
            semantic_text += f" who joined the company on {date_of_joining}."
        else:
            semantic_text += "."
            
        # Add contact and reporting information
        contact_info = []
        if email:
            contact_info.append(f"email: {email}")
        if phone:
            contact_info.append(f"phone: {phone}")
            
        if contact_info:
            semantic_text += f" Contact information includes {', '.join(contact_info)}."
            
        if manager_id:
            semantic_text += f" Reports to manager ID {manager_id}."
            
        # Add salary information for authorized roles (natural language)
        if salary:
            semantic_text += f" Annual compensation: {salary}."
            
        # Add searchable context paragraph
        semantic_text += f"\n\nThis employee record contains information about {full_name}, a {role} professional in the {department} team. "
        semantic_text += f"Key identifiers include employee ID {employee_id} and full name {full_name}. "
        semantic_text += f"This record is suitable for employee lookup, performance analysis, organizational reporting, and HR management purposes."
        
        # Add source context
        semantic_text += f"\n\nData source: {filename} | Employee database record | HR information system"
        
        return semantic_text.strip()
    
    def _extract_key_terms(self, headings: List[str]) -> List[str]:
        """
        Extract key terms from headings for search optimization.
        
        This method identifies important keywords that should be emphasized
        in the chunk text for better vector similarity matching.
        """
        if not headings:
            return []
            
        key_terms = set()
        
        # Common important terms to emphasize
        important_patterns = [
            'performance', 'metrics', 'sla', 'uptime', 'system', 'report', 
            'analysis', 'summary', 'overview', 'status', 'results',
            'incidents', 'security', 'compliance', 'budget', 'financial',
            'revenue', 'costs', 'engineering', 'infrastructure', 'api',
            'database', 'monitoring', 'alerts', 'maintenance', 'deployment'
        ]
        
        for heading in headings:
            # Split on common delimiters and get individual words
            words = heading.lower().replace('-', ' ').replace('_', ' ').split()
            
            for word in words:
                # Add words that are longer than 3 characters or match important patterns
                if len(word) > 3 or word.lower() in important_patterns:
                    key_terms.add(word.capitalize())
                    
                # Check if any important pattern is contained in the word
                for pattern in important_patterns:
                    if pattern in word.lower():
                        key_terms.add(word.capitalize())
                        break
        
        return sorted(list(key_terms))[:8]  # Limit to top 8 key terms
    
    def create_csv_headings(self, row: Dict[str, str], filename: str) -> List[str]:
        """
        Create structured headings for CSV rows using key employee fields.
        This creates a hierarchical structure for better searchability.
        """
        headings = []
        
        # Add employee identification
        employee_id = row.get('employee_id', 'N/A')
        full_name = row.get('full_name', 'Unknown')
        headings.append(f"Employee Id: {employee_id}")
        headings.append(f"Name: {full_name}")
        
        # Add role and department context
        role = row.get('role', 'N/A')
        department = row.get('department', 'N/A')
        if role != 'N/A' or department != 'N/A':
            headings.append(f"Role: {role} in {department}")
            
        # Add employment status
        employment_status = row.get('employment_status', 'N/A')
        if employment_status != 'N/A':
            headings.append(f"Status: {employment_status}")
            
        return headings
