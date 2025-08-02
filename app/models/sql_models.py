from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from app.db import Base
import uuid
from datetime import datetime

class Facility(Base):
    __tablename__ = 'facilities'  # Explicitly set the table name

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    external_id = Column(String, nullable=True, unique=True)  # Add this field
    address = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    users = relationship("User", back_populates="facility")
    patient_identifiers = relationship("PatientIdentifier", back_populates="facility")
    vector_db = relationship("VectorDB", back_populates="facility", uselist=False)

class User(Base):
    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False, unique=True)
    facility_id = Column(UUID(as_uuid=True), ForeignKey('facilities.id'))
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    facility = relationship("Facility", back_populates="users")

class VectorDB(Base):
    __tablename__ = 'vector_dbs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    facility_id = Column(UUID(as_uuid=True), ForeignKey('facilities.id'))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    facility = relationship("Facility", back_populates="vector_db")
    collections = relationship("Collection", back_populates="vector_db")

class Collection(Base):
    __tablename__ = 'collections'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(String)
    vector_db_id = Column(UUID(as_uuid=True), ForeignKey('vector_dbs.id'))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    vector_db = relationship("VectorDB", back_populates="collections")
    documents = relationship("Document", back_populates="collection")

class Document(Base):
    __tablename__ = 'documents'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content = Column(String, nullable=False)  # Original text for reference
    metadata_json = Column(JSON)  # Store document metadata
    embedding = Column(ARRAY(Float))  # Vector representation
    
    # Relationships
    collection_id = Column(UUID(as_uuid=True), ForeignKey('collections.id'))
    patient_identifier_id = Column(UUID(as_uuid=True), ForeignKey('patient_identifiers.id'), nullable=True)
    
    # Document classification
    document_type = Column(String)  # diagnosis, lab_result, prescription, note, etc.
    document_category = Column(String)  # clinical, administrative, etc.
    
    # Privacy and access control
    sensitivity_level = Column(String, default='standard')  # standard, sensitive, restricted
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    collection = relationship("Collection", back_populates="documents")
    patient_identifier = relationship("PatientIdentifier", back_populates="medical_documents")

class PatientIdentifier(Base):
    __tablename__ = 'patient_identifiers'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Minimal identifiable data
    patient_code = Column(String, nullable=False, unique=True)  # Internal anonymized ID
    external_id = Column(String, nullable=True)  # Optional external system ID
    facility_id = Column(UUID(as_uuid=True), ForeignKey('facilities.id'))
    
    # Optional minimal demographics for filtering/grouping
    age_range = Column(String)  # e.g., "25-30", "60-65" instead of exact age
    gender = Column(String, nullable=True)  # Optional
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    facility = relationship("Facility", back_populates="patient_identifiers")
    medical_documents = relationship("Document", back_populates="patient_identifier")