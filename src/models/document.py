"""
Document models and schemas for FinBot
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from pathlib import Path
import uuid

ChunkType = Literal["text", "table", "heading", "code", "list"]
Collection = Literal["general", "finance", "engineering", "marketing"]
Role = Literal["employee", "finance", "engineering", "marketing", "c_level"]

class DocumentMetadata(BaseModel):
    """Essential metadata for a document chunk stored in vector database"""
    
    # Essential fields only
    collection: Collection = Field(..., description="Document collection (general, finance, engineering, marketing)")
    access_roles: List[Role] = Field(..., description="List of roles that can access this document")
    source_document: str = Field(..., description="Filename of the source document")
    document_path: str = Field(..., description="Full path to the source document")
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique chunk identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class DocumentChunk(BaseModel):
    """A document chunk with hierarchical content and minimal metadata"""
    
    headings: List[str] = Field(..., description="Hierarchical path of headings")
    content: str = Field(..., description="Raw paragraph text")
    chunk_text: str = Field(..., description="Breadcrumb + content (what gets embedded)")
    metadata: DocumentMetadata = Field(..., description="Essential chunk metadata")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding for the chunk")
    
    class Config:
        arbitrary_types_allowed = True

class ProcessedDocument(BaseModel):
    """A fully processed document with all its chunks"""
    
    source_path: Path
    collection: Collection
    access_roles: List[Role]
    chunks: List[DocumentChunk]
    
    # Document-level metadata
    total_pages: Optional[int] = None
    file_size: int = 0
    processing_time: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        arbitrary_types_allowed = True

class DocumentSummary(BaseModel):
    """Summary information about a processed document"""
    
    source_document: str
    collection: Collection
    access_roles: List[Role] 
    total_chunks: int
    chunk_types: Dict[ChunkType, int]  # Count of each chunk type
    sections: List[str]  # List of main sections
    file_size: int
    processed_at: datetime

class IngestionStatus(BaseModel):
    """Status of document ingestion process"""
    
    total_documents: int = 0
    processed_documents: int = 0
    failed_documents: int = 0
    total_chunks: int = 0
    collections_processed: List[Collection] = Field(default_factory=list)
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    errors: List[str] = Field(default_factory=list)
    
    @property
    def processing_time(self) -> Optional[float]:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def is_complete(self) -> bool:
        return self.processed_documents + self.failed_documents == self.total_documents