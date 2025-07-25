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
    address = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    users = relationship("User", back_populates="facility")
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
    content = Column(String, nullable=False)
    metadata_json = Column(JSON)
    embedding = Column(ARRAY(Float))
    collection_id = Column(UUID(as_uuid=True), ForeignKey('collections.id'))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    collection = relationship("Collection", back_populates="documents")