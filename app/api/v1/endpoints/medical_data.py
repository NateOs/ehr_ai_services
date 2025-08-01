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
    Create an anonymized patient identifier that links to external system ID.
    
    **Important:** The facility must exist prior to creating a patient identifier.
    
    **Purpose:**
    - Creates anonymized patient ID (`patient_code`) for HIPAA compliance
    - Links to external system identifier (`external_id`) for integration
    - Maintains minimal demographics for filtering without exposing PII
    
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
        "patient_code": "PAT001_HOSP_A",
        "external_id": "HOSP_PATIENT_12345",
        "facility_id": "c115e85c-b368-4e29-b945-2918fa679e57",
        "age_range": "45-50",
        "gender": "F"
    }
    ```
    
    **Example Response:**
    ```json
    {
        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "patient_code": "PAT001_HOSP_A",
        "external_id": "HOSP_PATIENT_12345",
        "facility_id": "c115e85c-b368-4e29-b945-2918fa679e57",
        "age_range": "45-50",
        "gender": "F",
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z"
    }
    ```
    
    **Use Cases:**
    - Hospital EMR system creates anonymized patient records
    - Clinic management system integrates patient data
    - Research systems need de-identified patient references
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
    """
    Get all anonymized patient identifiers, optionally filtered by facility.
    
    **Purpose:**
    - Retrieve all patient identifiers for administrative purposes
    - Filter by facility to get facility-specific patients
    - Useful for bulk operations and reporting
    
    **Query Parameters:**
    - `facility_id` (optional): UUID of facility to filter patients
    
    **Example Request (All Patients):**
    ```
    GET /api/v1/patient-identifiers
    ```
    
    **Example Request (Facility-Specific):**
    ```
    GET /api/v1/patient-identifiers?facility_id=c115e85c-b368-4e29-b945-2918fa679e57
    ```
    
    **Example Response:**
    ```json
    [
        {
            "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "patient_code": "PAT001_HOSP_A",
            "external_id": "HOSP_PATIENT_12345",
            "facility_id": "c115e85c-b368-4e29-b945-2918fa679e57",
            "age_range": "45-50",
            "gender": "F",
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:30:00Z"
        },
        {
            "id": "b2c3d4e5-f6g7-8901-bcde-f23456789012",
            "patient_code": "PAT002_HOSP_A",
            "external_id": "HOSP_PATIENT_67890",
            "facility_id": "c115e85c-b368-4e29-b945-2918fa679e57",
            "age_range": "30-35",
            "gender": "M",
            "created_at": "2024-01-15T11:15:00Z",
            "updated_at": "2024-01-15T11:15:00Z"
        }
    ]
    ```
    
    **Use Cases:**
    - Facility administrators viewing all their patients
    - System administrators monitoring patient registrations
    - Bulk data operations and migrations
    - Reporting and analytics dashboards
    """
    query = db.query(PatientIdentifier)
    if facility_id:
        query = query.filter(PatientIdentifier.facility_id == facility_id)
    return query.all()

@router.get("/patient-identifiers/{patient_code}", response_model=PatientIdentifierResponse)
async def get_patient_identifier(
    patient_code: str,
    db: Session = Depends(get_db_session)
):
    """
    Get a specific patient identifier by patient code (the real anonymized identifier).
    
    **Purpose:**
    - Retrieve patient details using the anonymized patient_code
    - This is the primary way to reference patients in the system
    - Used by all other endpoints that need patient context
    
    **Path Parameters:**
    - `patient_code`: The anonymized patient identifier (e.g., "PAT001_HOSP_A")
    
    **Example Request:**
    ```
    GET /api/v1/patient-identifiers/PAT001_HOSP_A
    ```
    
    **Example Response (Success):**
    ```json
    {
        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "patient_code": "PAT001_HOSP_A",
        "external_id": "HOSP_PATIENT_12345",
        "facility_id": "c115e85c-b368-4e29-b945-2918fa679e57",
        "age_range": "45-50",
        "gender": "F",
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z"
    }
    ```
    
    **Example Response (Not Found):**
    ```json
    {
        "detail": "Patient identifier not found"
    }
    ```
    
    **Use Cases:**
    - Medical document ingestion (linking documents to patients)
    - AI query operations (querying specific patient data)
    - Clinical workflow systems (patient lookup)
    - Audit trail operations (tracking patient-specific actions)
    - Integration with external systems using patient_code
    
    **Security Note:**
    - Only returns anonymized data, no PII exposed
    - Patient_code serves as the safe identifier for all operations
    """
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