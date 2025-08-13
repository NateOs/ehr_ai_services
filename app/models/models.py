from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum

class GenderEnum(str, Enum):
    MALE = "M"
    FEMALE = "F"
    UNKNOWN = "Unknown"  # For cases where gender is not determined/recorded

class DocumentTypeEnum(str, Enum):
    MEDICAL_RECORD = "medical_record"
    LAB_RESULT = "lab_result"
    IMAGING_REPORT = "imaging_report"
    DISCHARGE_SUMMARY = "discharge_summary"
    CLINICAL_NOTE = "clinical_note"
    PRESCRIPTION = "prescription"
    OTHER = "other"

class Document(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    content: str
    metadata: Dict[str, str] = {}
    embedding: Optional[List[float]] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class Collection(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: Optional[str] = None
    documents: List[Document] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class VectorDB(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    collections: List[Collection] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class User(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    username: str
    email: str
    facility_id: UUID
    is_admin: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class Facility(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    address: str
    vector_db: VectorDB
    users: List[User] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

# Additional models for API requests and responses

class FacilityCreate(BaseModel):
    name: str = Field(..., description="Name of the facility")
    address: Optional[str] = Field(None, description="Address of the facility")
    external_id: Optional[str] = Field(None, description="External system identifier for this facility")

class UserCreate(BaseModel):
    username: str
    email: str
    facility_id: UUID
    is_admin: bool = False

class DocumentCreate(BaseModel):
    filename: str = Field(..., description="Original filename of the document")
    content_type: str = Field(..., description="MIME type of the document")
    document_type: DocumentTypeEnum = Field(..., description="Type of medical document")
    patient_code: Optional[str] = Field(None, description="Patient identifier code")
    facility_id: UUID = Field(..., description="Facility this document belongs to")
    metadata: Optional[Dict] = Field(default_factory=dict, description="Additional document metadata")

class CollectionCreate(BaseModel):
    name: str
    description: Optional[str] = None

class FacilityResponse(BaseModel):
    id: UUID
    name: str
    address: Optional[str] = None
    external_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class UserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    facility_id: UUID
    is_admin: bool
    created_at: datetime
    updated_at: datetime

class PatientIdentifierCreate(BaseModel):
    patient_code: str = Field(..., description="Unique patient identifier code")
    external_id: Optional[str] = Field(None, description="Optional external system identifier")
    facility_id: UUID = Field(..., description="UUID of the facility this patient belongs to")
    age_range: Optional[str] = Field(
        None, 
        description="Age range in format 'XX-YY' (e.g., '25-30')",
        pattern=r"^\d{1,3}-\d{1,3}$"
    )
    gender: Optional[GenderEnum] = Field(
        None, 
        description="Biological gender: M (Male), F (Female), or Unknown"
    )

class PatientIdentifierResponse(BaseModel):
    id: UUID
    patient_code: str
    external_id: Optional[str]
    facility_id: UUID
    age_range: Optional[str]
    gender: Optional[GenderEnum]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class MedicalDocumentCreate(BaseModel):
    content: str
    metadata: Dict[str, str] = {}
    patient_identifier_id: Optional[UUID] = None
    document_type: str
    document_category: str = "clinical"
    sensitivity_level: str = "standard"
    collection_id: Optional[UUID] = None

class MedicalDocumentResponse(BaseModel):
    id: UUID
    patient_identifier_id: Optional[UUID]
    document_type: str
    document_category: str
    sensitivity_level: str
    metadata: Dict[str, str]
    created_at: datetime
    updated_at: datetime
    # Note: content and embedding are excluded from response for privacy

class DocumentResponse(BaseModel):
    id: UUID
    filename: str
    content_type: str
    document_type: DocumentTypeEnum
    patient_code: Optional[str]
    facility_id: UUID
    file_path: str
    file_size: int
    processed: bool = False
    metadata: Optional[Dict] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class DocumentUploadResponse(BaseModel):
    document: DocumentResponse
    message: str
    processing_status: str = "queued"

class AbnormalFlag(BaseModel):
    parameter: str
    value: str
    normal_range: str
    severity: str  # "low", "moderate", "high", "critical"
    flag_type: str  # "low", "high", "abnormal"
    unit: Optional[str] = None
    
    class Config:
        from_attributes = True

class DiagnosticInsight(BaseModel):
    category: str  # e.g., "hematology", "cardiology", "endocrinology"
    insight: str
    confidence: float = Field(ge=0.0, le=1.0)
    recommendations: List[str] = []
    severity: Optional[str] = None  # "low", "moderate", "high", "critical"
    
    class Config:
        from_attributes = True

class AnalysisResultCreate(BaseModel):
    patient_code: str
    facility_id: UUID
    analysis_type: str
    content: str
    include_history: bool = True
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True

class AnalysisResultResponse(BaseModel):
    analysis_id: Optional[UUID] = None
    patient_code: str
    facility_id: UUID
    analysis_type: str
    abnormal_flags: List[AbnormalFlag] = []
    diagnostic_insights: List[DiagnosticInsight] = []
    summary: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    recommendations: List[str] = []
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class DischargeInstructionRequest(BaseModel):
    patient_identifier_id: UUID
    diagnosis: str
    medications: List[str] = []
    follow_up_instructions: Optional[str] = None
    activity_restrictions: Optional[str] = None
    diet_instructions: Optional[str] = None
    warning_signs: Optional[str] = None
    additional_notes: Optional[str] = None
    language_preference: str = "english"
    reading_level: str = "standard"  # "simple", "standard", "detailed"

class DischargeInstructionResponse(BaseModel):
    patient_identifier_id: UUID
    discharge_instructions: str
    medication_explanations: List[str] = []
    follow_up_summary: Optional[str] = None
    emergency_contact_info: Optional[str] = None
    generated_at: str
    language: str
    reading_level: str

class PatientSummaryResponse(BaseModel):
    patient_code: str
    facility_name: str
    summary_period: str
    total_documents: int
    document_types: List[str]
    ai_generated_summary: str
    key_findings: List[str]
    recent_activities: List[Dict[str, Any]]
    health_trends: Optional[Dict[str, List[str]]]
    recommendations: List[str]
    last_updated: datetime
    confidence_score: float
    
    class Config:
        from_attributes = True