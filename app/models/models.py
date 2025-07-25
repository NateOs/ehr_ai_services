from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from uuid import UUID, uuid4

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
    name: str
    address: str

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
    address: str
    created_at: datetime
    updated_at: datetime

class UserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    facility_id: UUID
    is_admin: bool
    created_at: datetime
    updated_at: datetime