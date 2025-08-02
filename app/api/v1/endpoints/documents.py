import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
import os
import shutil
from pathlib import Path
import mimetypes

from app.db import get_db_session
from app.models.models import DocumentCreate, DocumentResponse, DocumentUploadResponse, DocumentTypeEnum
from app.models.sql_models import Document as SQLDocument, Facility as SQLFacility
from app.core.config import settings
from app.services.llama_service import LlamaService
from app.dependencies import get_llama_service
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Allowed file types
ALLOWED_EXTENSIONS = {'.pdf', '.txt', '.docx', '.md', '.doc'}
ALLOWED_MIME_TYPES = {
    'application/pdf',
    'text/plain',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/msword',
    'text/markdown'
}

def validate_file(file: UploadFile) -> bool:
    """Validate uploaded file type and size"""
    # Check file size
    if file.size and file.size > settings.MAX_FILE_SIZE:
        return False
    
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return False
    
    # Check MIME type
    if file.content_type not in ALLOWED_MIME_TYPES:
        return False
    
    return True

def ensure_upload_directories():
    """Ensure upload directories exist"""
    for directory in [settings.UPLOAD_DIR, settings.PROCESSED_DIR, settings.TEMP_DIR]:
        Path(directory).mkdir(parents=True, exist_ok=True)

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    document_type: DocumentTypeEnum = Form(...),
    facility_id: UUID = Form(...),
    patient_code: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None),  # JSON string
    db: Session = Depends(get_db_session),
    llama_service: LlamaService = Depends(get_llama_service)
):
    """
    Upload a medical document for processing
    """
    try:
        # Validate file
        if not validate_file(file):
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}. Max size: {settings.MAX_FILE_SIZE/1024/1024:.1f}MB"
            )
        
        # Verify facility exists
        facility = db.query(SQLFacility).filter(SQLFacility.id == facility_id).first()
        if not facility:
            raise HTTPException(status_code=404, detail="Facility not found")
        
        # Ensure directories exist
        ensure_upload_directories()
        
        # Generate unique filename
        file_ext = Path(file.filename).suffix.lower()
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = Path(settings.UPLOAD_DIR) / unique_filename
        
        # Save file to disk
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Get file size
        file_size = file_path.stat().st_size
        
        # Parse metadata if provided
        parsed_metadata = {}
        if metadata:
            try:
                import json
                parsed_metadata = json.loads(metadata)
            except json.JSONDecodeError:
                logger.warning(f"Invalid metadata JSON provided: {metadata}")
        
        # Create document record
        document_data = SQLDocument(
            filename=file.filename,
            content_type=file.content_type,
            document_type=document_type.value,
            patient_code=patient_code,
            facility_id=facility_id,
            file_path=str(file_path),
            file_size=file_size,
            document_metadata=parsed_metadata  # Changed from 'metadata' to 'document_metadata'
        )
        
        db.add(document_data)
        db.commit()
        db.refresh(document_data)
        
        # Convert to response model
        document_response = DocumentResponse(
            id=document_data.id,
            filename=document_data.filename,
            content_type=document_data.content_type,
            document_type=DocumentTypeEnum(document_data.document_type),
            patient_code=document_data.patient_code,
            facility_id=document_data.facility_id,
            file_path=document_data.file_path,
            file_size=document_data.file_size,
            processed=document_data.processed,
            metadata=document_data.document_metadata,  # Map back to 'metadata' for API response
            created_at=document_data.created_at,
            updated_at=document_data.updated_at
        )
        
        # Queue for processing (we'll implement this next)
        processing_status = "uploaded"
        
        logger.info(f"Document uploaded successfully: {document_data.id}")
        
        return DocumentUploadResponse(
            document=document_response,
            message="Document uploaded successfully",
            processing_status=processing_status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        # Clean up file if it was created
        if 'file_path' in locals() and file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"Error uploading document: {str(e)}")

@router.get("/documents", response_model=list[DocumentResponse])
async def get_documents(
    facility_id: Optional[UUID] = None,
    patient_code: Optional[str] = None,
    document_type: Optional[DocumentTypeEnum] = None,
    processed: Optional[bool] = None,
    db: Session = Depends(get_db_session)
):
    """
    Get documents with optional filtering
    """
    query = db.query(SQLDocument)
    
    if facility_id:
        query = query.filter(SQLDocument.facility_id == facility_id)
    if patient_code:
        query = query.filter(SQLDocument.patient_code == patient_code)
    if document_type:
        query = query.filter(SQLDocument.document_type == document_type.value)
    if processed is not None:
        query = query.filter(SQLDocument.processed == processed)
    
    documents = query.order_by(SQLDocument.created_at.desc()).all()
    
    return [
        DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            content_type=doc.content_type,
            document_type=DocumentTypeEnum(doc.document_type),
            patient_code=doc.patient_code,
            facility_id=doc.facility_id,
            file_path=doc.file_path,
            file_size=doc.file_size,
            processed=doc.processed,
            metadata=doc.document_metadata,  # Map back to 'metadata' for API response
            created_at=doc.created_at,
            updated_at=doc.updated_at
        )
        for doc in documents
    ]

@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    db: Session = Depends(get_db_session)
):
    """
    Get a specific document by ID
    """
    document = db.query(SQLDocument).filter(SQLDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        content_type=document.content_type,
        document_type=DocumentTypeEnum(document.document_type),
        patient_code=document.patient_code,
        facility_id=document.facility_id,
        file_path=document.file_path,
        file_size=document.file_size,
        processed=document.processed,
        metadata=document.document_metadata,  # Map back to 'metadata' for API response
        created_at=document.created_at,
        updated_at=document.updated_at
    )

@router.post("/documents/{document_id}/process")
async def process_document(
    document_id: UUID,
    db: Session = Depends(get_db_session),
    llama_service: LlamaService = Depends(get_llama_service)
):
    """
    Process a specific document by ID
    """
    document = db.query(SQLDocument).filter(SQLDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        # Process document using llama_service
        processing_result = await llama_service.process_document(document.file_path)
        
        # Update document processed status
        document.processed = True
        document.document_metadata.update(processing_result)  # Updated to use 'document_metadata'
        db.commit()
        db.refresh(document)
        
        logger.info(f"Document processed successfully: {document.id}")
        
        return DocumentResponse(
            id=document.id,
            filename=document.filename,
            content_type=document.content_type,
            document_type=DocumentTypeEnum(document.document_type),
            patient_code=document.patient_code,
            facility_id=document.facility_id,
            file_path=document.file_path,
            file_size=document.file_size,
            processed=document.processed,
            metadata=document.document_metadata,  # Map back to 'metadata' for API response
            created_at=document.created_at,
            updated_at=document.updated_at
        )
        
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")
