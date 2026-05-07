"""
Document upload and management API endpoints for FinBot
"""

import os
import uuid
import json
import aiofiles
from typing import List, Optional, Union
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, Field
import logging
from datetime import datetime
from pathlib import Path

from src.core.database import get_db_session
from src.models.database import Document, UserRole
from src.core.config import settings
from src.core.processing.document_processor import HierarchicalDocumentProcessor
from src.core.store.vector_store import VectorStore
from src.models.document import Collection, Role

logger = logging.getLogger(__name__)

# Create the documents router
router = APIRouter()

# Response models
class DocumentResponse(BaseModel):
    """Document response model"""
    id: int
    filename: str
    original_filename: str
    collection: str
    role_access: UserRole
    file_size: int
    content_type: str
    upload_status: str
    embedding_status: str
    error_message: Optional[str] = None
    uploaded_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Documents list response"""
    documents: List[DocumentResponse]
    total: int
    page: int
    page_size: int


class UploadResponse(BaseModel):
    """File upload response"""
    document_id: int
    filename: str
    collection: str
    role_access: UserRole
    status: str
    message: str


class DocumentUpdate(BaseModel):
    """Document metadata update model"""
    original_filename: Optional[str] = Field(None, min_length=1, max_length=255)
    collection: Optional[str] = Field(None, description="Document collection")
    role_access: Optional[Union[UserRole, List[UserRole]]] = Field(None, description="Role(s) that can access the document")


# Allowed file types
ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.txt', '.md', ".csv", ".xlsx", ".json"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


def get_upload_directory() -> Path:
    """Get upload directory path"""
    upload_dir = Path(settings.data_dir) / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def get_role_access_list(role_access: UserRole) -> List[Role]:
    """Convert database user role enum to document access role list."""
    return [role_access.value]  # type: ignore[list-item]


async def process_document_background(document_id: int, file_path: str, collection: str, role_access: Union[UserRole, List[str]]):
    """Background task to process uploaded document and create embeddings"""
    from src.core.database import db_manager
    
    async with db_manager.async_session() as db:
        try:
            # Update status to processing
            document = await db.get(Document, document_id)
            if document:
                document.upload_status = "processing"  # type: ignore
                document.embedding_status = "processing"  # type: ignore
                await db.commit()

            logger.info(f"Starting background processing for document {document_id}")
            
            # Process document using existing document processor
            processor = HierarchicalDocumentProcessor()
            
            # Convert role_access to list of Role objects
            if isinstance(role_access, list):
                access_roles: List[str] = [role for role in role_access]  # Already a list of role strings
            else:
                access_roles = [role_access.value]  # type: ignore[list-item]
            
            # Extract text and metadata from the document
            processed_doc = await processor.process_document(
                file_path=Path(file_path),
                collection=collection,  # type: ignore[arg-type]
                access_roles=access_roles,  # type: ignore[arg-type]
            )
            processed_docs = [processed_doc] if processed_doc else []
            
            if not processed_docs:
                raise Exception("No content extracted from document")
            
            # Store embeddings in vector database  
            vector_store = VectorStore()
            
            # Initialize collection if needed
            await vector_store.initialize_collection(recreate=False)

            # Remove previous chunks before re-indexing to keep Qdrant in sync.
            await vector_store.remove_document_chunks(file_path)
            
            success = await vector_store.store_documents(
                documents=processed_docs
            )
            
            if success:
                # Update document status to completed
                if document:
                    document.upload_status = "completed"  # type: ignore
                    document.embedding_status = "completed"  # type: ignore
                    document.error_message = None  # type: ignore
                    await db.commit()
                
                logger.info(f"✅ Successfully processed document {document_id}")
            else:
                raise Exception("Failed to store document embeddings")
                
        except Exception as e:
            logger.error(f"❌ Error processing document {document_id}: {e}")
            
            # Update document status to failed
            if document:
                document.upload_status = "failed"  # type: ignore
                document.embedding_status = "failed"  # type: ignore
                document.error_message = str(e)  # type: ignore
                await db.commit()


@router.post("/documents/upload", response_model=UploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    collection: str = Form(..., description="Document collection (hr, finance, engineering, marketing, general)"),
    role_access: str = Form(..., description="Role or list of roles that can access this document"),
    uploaded_by: Optional[int] = Form(None, description="User ID who uploaded the file"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Upload a document file and process it for embeddings.
    
    - **file**: Document file (PDF, DOCX, TXT, MD)
    - **collection**: Collection to store document in
    - **role_access**: Which role(s) can access this document (single role or JSON array of roles)
    - **uploaded_by**: Optional user ID who uploaded the file
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file_ext} not allowed. Supported types: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # Check file size
        file_size = 0
        content = await file.read()
        file_size = len(content)
        
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File size {file_size} bytes exceeds maximum {MAX_FILE_SIZE} bytes"
            )
        
        # Parse role_access - can be single role or JSON array of roles
        try:
            if role_access.startswith('['):
                # It's a JSON array of roles
                roles_list = json.loads(role_access)
                primary_role_str = roles_list[0] if roles_list else 'employee'
            else:
                # It's a single role
                primary_role_str = role_access
                roles_list = [role_access]
        except (json.JSONDecodeError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid role_access format")
        
        # Convert to UserRole enum
        try:
            primary_role = UserRole[primary_role_str.upper()]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid role: {primary_role_str}")
        
        # Generate unique filename
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        upload_dir = get_upload_directory()
        file_path = upload_dir / unique_filename
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        logger.info(f"Saved uploaded file: {file_path}")
        
        # Create document record (store primary role for database)
        document = Document(
            filename=unique_filename,
            original_filename=file.filename,
            file_path=str(file_path),
            collection=collection,
            role_access=primary_role,
            file_size=file_size,
            content_type=file.content_type or 'application/octet-stream',
            upload_status="processing",
            embedding_status="pending",
            uploaded_by=uploaded_by
        )
        
        db.add(document)
        await db.commit()
        await db.refresh(document)
        
        # Start background processing with full roles list
        background_tasks.add_task(
            process_document_background,
            document.id,  # type: ignore
            str(file_path),
            collection,
            roles_list  # Pass full roles list for Qdrant metadata
        )
        
        logger.info(f"Created document record {document.id} and started background processing")
        
        return UploadResponse(
            document_id=document.id,  # type: ignore
            filename=file.filename,
            collection=collection,
            role_access=primary_role,
            status="processing",
            message="Document uploaded successfully and processing started"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        
        # Clean up file if it was created
        if 'file_path' in locals() and file_path.exists():
            file_path.unlink()
        
        raise HTTPException(status_code=500, detail="Failed to upload document")


@router.get("/documents", response_model=DocumentListResponse)
async def get_documents(
    page: int = 1,
    page_size: int = 20,
    collection: Optional[str] = None,
    role_access: Optional[UserRole] = None,
    upload_status: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get documents with optional filtering and pagination.
    
    - **page**: Page number (1-based)
    - **page_size**: Number of documents per page (max 100)
    - **collection**: Filter by collection
    - **role_access**: Filter by role access
    - **upload_status**: Filter by upload status (processing, completed, failed)
    """
    try:
        # Validate pagination
        if page < 1:
            raise HTTPException(status_code=400, detail="Page must be >= 1")
        if page_size < 1 or page_size > 100:
            raise HTTPException(status_code=400, detail="Page size must be between 1 and 100")
        
        # Build query
        query = select(Document)
        
        # Apply filters
        if collection:
            query = query.where(Document.collection == collection)
        if role_access:
            query = query.where(Document.role_access == role_access)
        if upload_status:
            query = query.where(Document.upload_status == upload_status)
        
        # Get total count
        count_query = select(func.count()).select_from(Document)
        if collection:
            count_query = count_query.where(Document.collection == collection)
        if role_access:
            count_query = count_query.where(Document.role_access == role_access)
        if upload_status:
            count_query = count_query.where(Document.upload_status == upload_status)
        
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Apply pagination and ordering
        query = query.order_by(Document.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        
        # Execute query
        result = await db.execute(query)
        documents = result.scalars().all()
        
        return DocumentListResponse(
            documents=[DocumentResponse.model_validate(doc) for doc in documents],
            total=total,
            page=page,
            page_size=page_size
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch documents")


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: int, db: AsyncSession = Depends(get_db_session)):
    """Get document by ID"""
    try:
        document = await db.get(Document, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return DocumentResponse.model_validate(document)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch document")


@router.delete("/documents/{document_id}")
async def delete_document(document_id: int, db: AsyncSession = Depends(get_db_session)):
    """Delete document by ID"""
    try:
        document = await db.get(Document, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        vector_store = VectorStore()
        await vector_store.initialize_collection(recreate=False)
        await vector_store.remove_document_chunks(str(document.file_path))  # type: ignore[arg-type]
        
        # Delete physical file
        file_path = Path(str(document.file_path))  # type: ignore
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted file: {file_path}")
        
        # Delete database record
        await db.delete(document)
        await db.commit()
        
        logger.info(f"Deleted document: {document.filename} (ID: {document_id})")
        
        return {"message": "Document deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete document")


@router.put("/documents/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: int,
    document_data: DocumentUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session)
):
    """Update document metadata and resync embeddings when relevant fields change."""
    try:
        document = await db.get(Document, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        update_data = document_data.dict(exclude_unset=True)
        should_reprocess = False
        roles_list_for_reprocess = None

        for field, value in update_data.items():
            if field == "role_access":
                # Handle role_access that can be single role or list of roles
                if isinstance(value, list):
                    primary_role = value[0] if value else 'employee'
                    roles_list_for_reprocess = value
                else:
                    primary_role = value
                    roles_list_for_reprocess = [value] if value else ['employee']
                
                if getattr(document, field) != primary_role:
                    setattr(document, field, primary_role)
                    should_reprocess = True
            else:
                current_value = getattr(document, field)
                if current_value != value:
                    setattr(document, field, value)
                    if field == "collection":
                        should_reprocess = True

        if should_reprocess:
            document.upload_status = "processing"  # type: ignore
            document.embedding_status = "processing"  # type: ignore
            document.error_message = None  # type: ignore

        await db.commit()
        await db.refresh(document)

        if should_reprocess:
            background_tasks.add_task(
                process_document_background,
                document.id,  # type: ignore[arg-type]
                str(document.file_path),
                str(document.collection),  # type: ignore[arg-type]
                roles_list_for_reprocess or [str(document.role_access)],  # type: ignore[arg-type]
            )

        return DocumentResponse.model_validate(document)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update document")


@router.post("/documents/{document_id}/reprocess")
async def reprocess_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session)
):
    """Reprocess document embeddings"""
    try:
        document = await db.get(Document, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Check if file still exists
        file_path = Path(str(document.file_path))  # type: ignore
        if not file_path.exists():
            raise HTTPException(status_code=400, detail="Document file not found")
        
        # Reset status and start reprocessing
        document.upload_status = "processing"  # type: ignore
        document.embedding_status = "processing"  # type: ignore
        document.error_message = None  # type: ignore
        await db.commit()
        
        # Start background processing
        background_tasks.add_task(
            process_document_background,
            document.id,  # type: ignore
            str(file_path),
            str(document.collection),  # type: ignore
            document.role_access  # type: ignore
        )
        
        return {"message": "Document reprocessing started"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reprocessing document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to start reprocessing")