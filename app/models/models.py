from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum

class GenderEnum(str, Enum):
    MALE = "M"
    FEMALE = "F"
    OTHER = "Other"
    NON_BINARY = "Non-binary"
    PREFER_NOT_TO_SAY = "Prefer not to say"

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
    content: str
    metadata: Dict[str, str] = {}

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
        description="Age range in format 'XX-YY' where XX and YY are ages (e.g., '25-30', '60-65')",
        example="25-30",
        pattern=r'^\d{1,3}-\d{1,3}'
    )
    gender: Optional[GenderEnum] = Field(
        None, 
        description="Patient gender"
    )

class PatientIdentifierResponse(BaseModel):
    id: UUID
    patient_code: str
    external_id: Optional[str]
    facility_id: UUID
    age_range: Optional[str]
    gender: Optional[str]
    created_at: datetime
    updated_at: datetime

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