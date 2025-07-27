from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db import get_db_session
from app.models.models import (
    PatientIdentifierCreate, 
    PatientIdentifierResponse,
    MedicalDocumentCreate,
    MedicalDocumentResponse
)
from app.services.llama_service import LlamaService
from app.models.sql_models import PatientIdentifier, Document
from uuid import UUID

router = APIRouter()

@router.post("/patient-identifiers", response_model=PatientIdentifierResponse)
async def create_patient_identifier(
    patient_data: PatientIdentifierCreate,
    db: Session = Depends(get_db_session)
):
    """
    Create a minimal patient identifier
    
    **Age Range Format:**
    - Use format "XX-YY" where XX is start age and YY is end age
    - Examples: "25-30", "60-65", "0-5", "80-85"
    - Both ages must be between 0 and 150
    - Start age must be less than end age
    
    **Gender Options:**
    - M, F, Male, Female, Other, Non-binary, Prefer not to say
    
    **Example Request:**
    ```json
    {
        "patient_code": "PAT001",
        "external_id": "EXT123",
        "facility_id": "c115e85c-b368-4e29-b945-2918fa679e57",
        "age_range": "25-30",
        "gender": "M"
    }
    """
    try:
        patient_identifier = PatientIdentifier(**patient_data.dict())
        db.add(patient_identifier)
        db.commit()
        db.refresh(patient_identifier)
        return patient_identifier
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error creating patient identifier: {str(e)}")

@router.get("/patient-identifiers", response_model=List[PatientIdentifierResponse])
async def get_patient_identifiers(
    facility_id: UUID = None,
    db: Session = Depends(get_db_session)
):
    """Get all patient identifiers, optionally filtered by facility"""
    query = db.query(PatientIdentifier)
    if facility_id:
        query = query.filter(PatientIdentifier.facility_id == facility_id)
    return query.all()

@router.get("/patient-identifiers/{patient_code}", response_model=PatientIdentifierResponse)
async def get_patient_identifier(
    patient_code: str,
    db: Session = Depends(get_db_session)
):
    """Get a specific patient identifier by patient code"""
    patient_identifier = db.query(PatientIdentifier).filter(
        PatientIdentifier.patient_code == patient_code
    ).first()
    
    if not patient_identifier:
        raise HTTPException(status_code=404, detail="Patient identifier not found")
    
    return patient_identifier

@router.post("/medical-documents", response_model=MedicalDocumentResponse)
async def ingest_medical_document(
    document_data: MedicalDocumentCreate,
    db: Session = Depends(get_db_session)
):
    """Ingest medical document and create vector embedding"""
    try:
        # For now, we'll create the document without embedding
        # You can add the LlamaService integration later
        document = Document(
            content=document_data.content,
            metadata_json=document_data.metadata,
            patient_identifier_id=document_data.patient_identifier_id,
            document_type=document_data.document_type,
            document_category=document_data.document_category,
            sensitivity_level=document_data.sensitivity_level,
            collection_id=document_data.collection_id if hasattr(document_data, 'collection_id') else None
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        # Return response without sensitive content
        return MedicalDocumentResponse(
            id=document.id,
            patient_identifier_id=document.patient_identifier_id,
            document_type=document.document_type,
            document_category=document.document_category,
            sensitivity_level=document.sensitivity_level,
            metadata=document.metadata_json or {},
            created_at=document.created_at,
            updated_at=document.updated_at
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error creating medical document: {str(e)}")

@router.post("/query-patient-data")
async def query_patient_medical_data(
    patient_code: str,
    query: str,
    db: Session = Depends(get_db_session),
    llama_service: LlamaService = Depends()
):
    """Query medical data for a specific patient using vector similarity"""
    
    # Find patient identifier
    patient_identifier = db.query(PatientIdentifier).filter(
        PatientIdentifier.patient_code == patient_code
    ).first()
    
    if not patient_identifier:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Query using vector similarity on patient's documents
    results = await llama_service.query_patient_documents(
        patient_identifier_id=patient_identifier.id,
        query=query
    )
    
    return {
        "patient_code": patient_code,
        "query": query,
        "results": results,
        "patient_metadata": {
            "age_range": patient_identifier.age_range,
            "gender": patient_identifier.gender
        }
    }