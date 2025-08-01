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
from app.models.sql_models import PatientIdentifier, Document, Collection, VectorDB, Facility
from uuid import UUID

router = APIRouter()

@router.post("/patient-identifiers", response_model=PatientIdentifierResponse)
async def create_patient_identifier(
    patient_data: PatientIdentifierCreate,
    db: Session = Depends(get_db_session)
):
    """
    Create an anonymized patient identifier with dedicated collection for their medical data.
    
    **Important:** The facility must exist prior to creating a patient identifier.
    
    **Auto-Collection Creation:**
    - Automatically creates a dedicated collection for this patient's medical documents
    - Collection name format: "Patient_{patient_code}_Collection"
    - Ensures proper data isolation and organization per patient
    
    **Purpose:**
    - Creates anonymized patient ID (`patient_code`) for HIPAA compliance
    - Links to external system identifier (`external_id`) for integration
    - Maintains minimal demographics for filtering without exposing PII
    - Sets up vector storage infrastructure for patient's medical documents
    
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
    
    **What Gets Created:**
    1. Patient identifier record
    2. Dedicated collection: "Patient_PAT001_HOSP_A_Collection"
    3. Ready-to-use storage for patient's medical documents
    
    **Use Cases:**
    - Hospital EMR system creates anonymized patient records
    - Clinic management system integrates patient data
    - Research systems need de-identified patient references
    - AI-powered medical document analysis per patient
    """
    try:
        # Validate that facility exists and has a VectorDB
        facility = db.query(Facility).filter(Facility.id == patient_data.facility_id).first()
        if not facility:
            raise HTTPException(status_code=400, detail="Facility not found")
        
        # Get facility's VectorDB
        facility_vector_db = db.query(VectorDB).filter(
            VectorDB.facility_id == patient_data.facility_id
        ).first()
        if not facility_vector_db:
            raise HTTPException(
                status_code=400, 
                detail="Facility's vector database not found. Please contact administrator."
            )
        
        # Create patient identifier
        patient_identifier = PatientIdentifier(**patient_data.dict())
        db.add(patient_identifier)
        db.commit()
        db.refresh(patient_identifier)
        
        # Create dedicated collection for this patient
        patient_collection = Collection(
            name=f"Patient_{patient_data.patient_code}_Collection",
            description=f"Medical documents collection for patient {patient_data.patient_code}",
            vector_db_id=facility_vector_db.id
        )
        
        db.add(patient_collection)
        db.commit()
        db.refresh(patient_collection)
        
        return patient_identifier
        
    except HTTPException:
        raise
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
    """
    Ingest medical document into patient's dedicated collection.
    
    **Auto-Collection Assignment:**
    - Automatically uses patient's dedicated collection
    - Collection format: "Patient_{patient_code}_Collection"
    - Ensures proper data isolation per patient
    - No need to specify collection_id in request
    
    **Document Processing:**
    - Stores original document content
    - Creates vector embeddings for AI querying
    - Maintains document metadata and classification
    - Links to patient's anonymized identifier
    
    **Document Types:**
    - clinical_note, diagnosis, lab_result, prescription, discharge_summary, 
    - radiology_report, pathology_report, consultation_note, progress_note
    
    **Document Categories:**
    - clinical, administrative, billing, research, imaging
    
    **Sensitivity Levels:**
    - standard, sensitive, restricted
    
    **Example Request:**
    ```json
    {
        "content": "Patient presents with acute chest pain. Onset 2 hours ago, described as crushing, radiating to left arm. Vital signs: BP 140/90, HR 95, RR 18, O2 sat 98%. ECG shows normal sinus rhythm with no acute ST changes. Troponin I pending. Started on aspirin 325mg, nitroglycerin SL PRN. Plan: serial ECGs, troponin levels q6h, cardiology consult.",
        "patient_identifier_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "document_type": "clinical_note",
        "document_category": "clinical",
        "sensitivity_level": "standard",
        "metadata": {
            "provider": "Dr. Sarah Johnson",
            "department": "Emergency Department",
            "visit_date": "2024-01-15",
            "visit_type": "emergency",
            "chief_complaint": "chest pain"
        }
    }
    ```
    
    **Example Response:**
    ```json
    {
        "id": "doc123e4-5678-9abc-def0-123456789abc",
        "patient_identifier_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "document_type": "clinical_note",
        "document_category": "clinical",
        "sensitivity_level": "standard",
        "metadata": {
            "provider": "Dr. Sarah Johnson",
            "department": "Emergency Department",
            "visit_date": "2024-01-15",
            "visit_type": "emergency",
            "chief_complaint": "chest pain"
        },
        "created_at": "2024-01-15T14:30:00Z",
        "updated_at": "2024-01-15T14:30:00Z"
    }
    ```
    
    **Use Cases:**
    - EMR systems uploading patient records
    - Clinical documentation workflows
    - AI-powered medical analysis and insights
    - Research data collection (anonymized)
    - Quality improvement initiatives
    """
    try:
        # Validate that patient identifier exists
        patient_identifier = db.query(PatientIdentifier).filter(
            PatientIdentifier.id == document_data.patient_identifier_id
        ).first()
        if not patient_identifier:
            raise HTTPException(
                status_code=400, 
                detail="Patient identifier not found"
            )
        
        # Find patient's dedicated collection
        patient_collection = db.query(Collection).join(VectorDB).filter(
            VectorDB.facility_id == patient_identifier.facility_id,
            Collection.name == f"Patient_{patient_identifier.patient_code}_Collection"
        ).first()
        
        if not patient_collection:
            raise HTTPException(
                status_code=400,
                detail=f"Patient collection not found for {patient_identifier.patient_code}. Please contact administrator."
            )
        
        # Create document in patient's collection
        document = Document(
            content=document_data.content,
            metadata_json=document_data.metadata,
            patient_identifier_id=document_data.patient_identifier_id,
            document_type=document_data.document_type,
            document_category=document_data.document_category,
            sensitivity_level=document_data.sensitivity_level,
            collection_id=patient_collection.id
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
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
        
    except HTTPException:
        raise
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