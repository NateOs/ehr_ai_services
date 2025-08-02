from pydantic import BaseModel

from app.api.v1.endpoints import medical_data
from ..endpoints import query
from app.models import Facility, FacilityCreate, FacilityResponse, VectorDB, Collection
from app.models.sql_models import Facility as SQLFacility  # Import SQLAlchemy model
from app.db import get_db_session
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException

api_router = APIRouter()


async def get_facility_by_external_id(
    external_id: str,
    db: Session = Depends(get_db_session)
):	
    """
    Get facility by external ID for integration with external systems.
    
    **Purpose:**
    - Allow external systems to lookup facilities using their own identifiers
    - Support integration with EMRs, billing systems, etc.
    - Maintain referential integrity across multiple systems
    
    **Path Parameters:**
    - `external_id`: The external system's identifier for this facility
    
    **Example Request:**
    ```
    GET /api/v1/facilities/external/HOSP_SYS_12345
    ```
    """
    facility = db.query(Facility).filter(
        Facility.external_id == external_id
    ).first()
    
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")
    
    return facility

@api_router.post("/facilities", response_model=FacilityResponse)
async def create_facility(facility_data: FacilityCreate, db: Session = Depends(get_db_session)):
    """
    Create a new facility with its associated VectorDB and shared collection.
    
    **Purpose:**
    - Creates a facility for organizing patients and medical data
    - Automatically sets up vector database infrastructure
    - Creates a shared collection for all facility documents
    - Supports external system integration via external_id
    
    **What gets created:**
    1. Facility record (with optional external_id)
    2. VectorDB for the facility
    3. Shared collection for all patient documents
    
    **Example Request:**
    ```json
    {
        "name": "General Hospital",
        "address": "123 Medical Center Dr, City, State 12345",
        "external_id": "HOSP_SYS_12345"
    }
    ```
    
    **Example Response:**
    ```json
    {
        "id": "c115e85c-b368-4e29-b945-2918fa679e57",
        "name": "General Hospital",
        "address": "123 Medical Center Dr, City, State 12345",
        "external_id": "HOSP_SYS_12345",
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-01-15T10:00:00Z"
    }
    ```
    """
    try:
        # Check if external_id already exists (if provided)
        if facility_data.external_id:
            existing_facility = db.query(SQLFacility).filter(
                SQLFacility.external_id == facility_data.external_id
            ).first()
            if existing_facility:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Facility with external_id '{facility_data.external_id}' already exists"
                )
        
        # Create the facility first
        facility = SQLFacility(
            name=facility_data.name,
            address=facility_data.address,
            external_id=facility_data.external_id
        )
        
        db.add(facility)
        db.commit()
        db.refresh(facility)
        
        # Create VectorDB for this facility
        from app.models.sql_models import VectorDB as SQLVectorDB, Collection as SQLCollection
        
        vector_db = SQLVectorDB(
            name=f"{facility_data.name}_VectorDB",
            facility_id=facility.id
        )
        
        db.add(vector_db)
        db.commit()
        db.refresh(vector_db)
        
        # Create shared collection for this facility
        shared_collection = SQLCollection(
            name="Facility_Shared_Collection",
            description=f"Shared collection for all patient documents at {facility_data.name}",
            vector_db_id=vector_db.id
        )
        
        db.add(shared_collection)
        db.commit()
        db.refresh(shared_collection)
        
        # TODO: Create a folder for facility uploads
        # facility_folder = f"uploads/{facility.name.replace(' ', '_')}"
        # os.makedirs(facility_folder, exist_ok=True)
        
        return FacilityResponse(
            id=facility.id,
            name=facility.name,
            address=facility.address,
            external_id=facility.external_id,
            created_at=facility.created_at,
            updated_at=facility.updated_at
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error creating facility: {str(e)}")

@api_router.get("/facilities", response_model=list[FacilityResponse])
async def list_facilities(db: Session = Depends(get_db_session)):
    """
    List all facilities.
    
    **Purpose:**
    - Get a list of all facilities in the system
    - Useful for admin interfaces and facility selection
    - Includes external_id for integration purposes
    
    **Example Response:**
    ```json
    [
        {
            "id": "c115e85c-b368-4e29-b945-2918fa679e57",
            "name": "General Hospital",
            "address": "123 Medical Center Dr, City, State 12345",
            "external_id": "HOSP_SYS_12345",
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-15T10:00:00Z"
        }
    ]
    ```
    """
    facilities = db.query(SQLFacility).all()
    return [
        FacilityResponse(
            id=facility.id,
            name=facility.name,
            address=facility.address,
            external_id=facility.external_id,
            created_at=facility.created_at,
            updated_at=facility.updated_at
        )
        for facility in facilities
    ]

@api_router.get("/facilities/{facility_id}", response_model=FacilityResponse)
async def get_facility(facility_id: str, db: Session = Depends(get_db_session)):
    """
    Get facility by ID.
    
    **Purpose:**
    - Get a specific facility by its UUID
    - Includes external_id for integration purposes
    
    **Path Parameters:**
    - `facility_id`: The UUID of the facility
    
    **Example Request:**
    ```
    GET /api/v1/facilities/c115e85c-b368-4e29-b945-2918fa679e57
    ```
    """
    facility = db.query(SQLFacility).filter(SQLFacility.id == facility_id).first()
    
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")
    
    return FacilityResponse(
        id=facility.id,
        name=facility.name,
        address=facility.address,
        external_id=facility.external_id,
        created_at=facility.created_at,
        updated_at=facility.updated_at
    )