from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional
from app.db import get_db_session
from app.dependencies import get_llama_service
from app.services.llama_service import LlamaService
from app.models.sql_models import PatientIdentifier, MedicalDocument, Collection, VectorDB
from app.models.models import (
    MedicalDocumentCreate, 
    MedicalDocumentResponse,
    PatientIdentifierCreate,
    PatientIdentifierResponse
)
from app.core.logging import logger
from pydantic import BaseModel

# Add this model at the top of the file
class QueryPatientDataRequest(BaseModel):
    patient_code: str
    query: str

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
    
    **Gender Options (Medical/Biological):**
    - M: Male
    - F: Female  
    - Unknown: For cases where biological gender is not determined or recorded
    
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
    db: Session = Depends(get_db_session),
    llama_service: LlamaService = Depends(get_llama_service)
):
    """
    Ingest medical document into patient's dedicated collection with AI embedding.
    
    **Enhanced Features:**
    - Stores document in database
    - Creates vector embeddings for AI querying
    - Adds document to LlamaIndex for semantic search
    - Maintains patient data isolation
    
    **Auto-Collection Assignment:**
    - Automatically uses patient's dedicated collection
    - Collection format: "Patient_{patient_code}_Collection"
    - Ensures proper data isolation per patient
    
    **AI Integration:**
    - Creates vector embeddings using OpenAI
    - Adds to searchable index for patient-specific queries
    - Enables semantic search and medical insights
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
        
        # Create medical document in patient's collection
        medical_document = MedicalDocument(
            content=document_data.content,
            metadata_json=document_data.metadata,
            patient_identifier_id=document_data.patient_identifier_id,
            document_type=document_data.document_type,
            document_category=document_data.document_category,
            sensitivity_level=document_data.sensitivity_level,
            collection_id=patient_collection.id,
            facility_id=patient_identifier.facility_id
        )
        
        db.add(medical_document)
        db.commit()
        db.refresh(medical_document)
        
        # NEW: Add document to AI index for querying
        try:
            logger.info(f"Adding document {medical_document.id} to AI index for patient {patient_identifier.patient_code}")
            
            # Prepare metadata for the AI index
            ai_metadata = {
                "document_id": str(medical_document.id),
                "patient_code": patient_identifier.patient_code,
                "patient_identifier_id": str(patient_identifier.id),
                "facility_id": str(patient_identifier.facility_id),
                "document_type": medical_document.document_type,
                "document_category": medical_document.document_category,
                "sensitivity_level": medical_document.sensitivity_level,
                "collection_id": str(patient_collection.id),
                **document_data.metadata
            }
            
            # Add to LlamaIndex for AI querying
            await llama_service.add_document_to_index(
                content=document_data.content,
                metadata=ai_metadata
            )
            
            logger.info(f"Successfully added document {medical_document.id} to AI index")
            
        except Exception as e:
            # Log error but don't fail the request - document is still saved
            logger.error(f"Failed to add document {medical_document.id} to AI index: {e}")
            # You might want to set a flag in the database to retry later
        
        return MedicalDocumentResponse(
            id=medical_document.id,
            patient_identifier_id=medical_document.patient_identifier_id,
            document_type=medical_document.document_type,
            document_category=medical_document.document_category,
            sensitivity_level=medical_document.sensitivity_level,
            metadata=medical_document.metadata_json or {},
            created_at=medical_document.created_at,
            updated_at=medical_document.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating medical document: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error creating medical document: {str(e)}")

@router.get("/medical-documents", response_model=List[MedicalDocumentResponse])
async def get_medical_documents(
    patient_identifier_id: UUID = None,
    facility_id: UUID = None,
    document_type: str = None,
    document_category: str = None,
    sensitivity_level: str = None,
    db: Session = Depends(get_db_session)
):
    """
    Get medical documents with optional filtering.
    
    **Query Parameters:**
    - `patient_identifier_id`: Filter by specific patient
    - `facility_id`: Filter by facility
    - `document_type`: Filter by document type
    - `document_category`: Filter by category
    - `sensitivity_level`: Filter by sensitivity level
    
    **Example Request:**
    ```
    GET /api/v1/medical-documents?patient_identifier_id=a1b2c3d4-e5f6-7890-abcd-ef1234567890&document_type=clinical_note
    ```
    """
    query = db.query(MedicalDocument)
    
    if patient_identifier_id:
        query = query.filter(MedicalDocument.patient_identifier_id == patient_identifier_id)
    if facility_id:
        query = query.filter(MedicalDocument.facility_id == facility_id)
    if document_type:
        query = query.filter(MedicalDocument.document_type == document_type)
    if document_category:
        query = query.filter(MedicalDocument.document_category == document_category)
    if sensitivity_level:
        query = query.filter(MedicalDocument.sensitivity_level == sensitivity_level)
    
    medical_documents = query.all()
    
    return [
        MedicalDocumentResponse(
            id=doc.id,
            patient_identifier_id=doc.patient_identifier_id,
            document_type=doc.document_type,
            document_category=doc.document_category,
            sensitivity_level=doc.sensitivity_level,
            metadata=doc.metadata_json or {},
            created_at=doc.created_at,
            updated_at=doc.updated_at
        )
        for doc in medical_documents
    ]

@router.get("/medical-documents/{document_id}", response_model=MedicalDocumentResponse)
async def get_medical_document(
    document_id: UUID,
    db: Session = Depends(get_db_session)
):
    """
    Get a specific medical document by ID.
    """
    medical_document = db.query(MedicalDocument).filter(
        MedicalDocument.id == document_id
    ).first()
    
    if not medical_document:
        raise HTTPException(status_code=404, detail="Medical document not found")
    
    return MedicalDocumentResponse(
        id=medical_document.id,
        patient_identifier_id=medical_document.patient_identifier_id,
        document_type=medical_document.document_type,
        document_category=medical_document.document_category,
        sensitivity_level=medical_document.sensitivity_level,
        metadata=medical_document.metadata_json or {},
        created_at=medical_document.created_at,
        updated_at=medical_document.updated_at
    )

@router.post("/query-patient-data")
async def query_patient_medical_data(
    request: QueryPatientDataRequest,
    db: Session = Depends(get_db_session),
    llama_service: LlamaService = Depends(get_llama_service)
):
    """
    Query medical data for a specific patient using AI-powered semantic search.
    
    **Enhanced Features:**
    - Uses vector embeddings for semantic search
    - Searches only the specified patient's documents
    - Provides AI-generated insights and summaries
    - Returns source documents with relevance scores
    
    **Example Request:**
    ```json
    {
        "patient_code": "PAT001_HOSP_A",
        "query": "What are the latest lab results?"
    }
    """
    
    # Find patient identifier
    patient_identifier = db.query(PatientIdentifier).filter(
        PatientIdentifier.patient_code == request.patient_code
    ).first()
    
    if not patient_identifier:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    try:
        # Query patient's documents using LlamaService
        result = await llama_service.query_patient_documents(
            patient_identifier_id=str(patient_identifier.id),
            query=request.query
        )
        
        return {
            "patient_code": request.patient_code,
            "query": request.query,
            "response": result["response"],
            "source_documents": result["source_nodes"],
            "diagnostic_insights": result["diagnostic_insights"]
        }
        
    except Exception as e:
        logger.error(f"Error querying patient data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query patient data: {str(e)}"
        )