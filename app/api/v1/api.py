from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.v1.endpoints import medical_data
from .endpoints import query
from app.models import Facility, FacilityCreate, FacilityResponse, VectorDB, Collection
from app.models.sql_models import Facility as SQLFacility  # Import SQLAlchemy model
from app.db import get_db_session
from sqlalchemy.orm import Session
from fastapi import Depends

api_router = APIRouter()

api_router.include_router(query.router, tags=["query"])
api_router.include_router(medical_data.router, tags=["medical_data"])

@api_router.get("/test")
async def test_endpoint():
    return {"message": "API v1 is working"}

@api_router.post("/facility", response_model=FacilityResponse)
async def create_facility(facility_data: FacilityCreate, db: Session = Depends(get_db_session)):
    """
    Create a new facility with its associated VectorDB and shared collection.
    
    **Purpose:**
    - Creates a facility for organizing patients and medical data
    - Automatically sets up vector database infrastructure
    - Creates a shared collection for all facility documents
    
    **What gets created:**
    1. Facility record
    2. VectorDB for the facility
    3. Shared collection for all patient documents
    
    **Example Request:**
    ```json
    {
        "name": "General Hospital",
        "address": "123 Medical Center Dr, City, State 12345"
    }
    ```
    
    **Example Response:**
    ```json
    {
        "id": "c115e85c-b368-4e29-b945-2918fa679e57",
        "name": "General Hospital",
        "address": "123 Medical Center Dr, City, State 12345",
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-01-15T10:00:00Z"
    }
    ```
    """
    try:
        # Create the facility first
        facility = SQLFacility(
            name=facility_data.name,
            address=facility_data.address
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
            created_at=facility.created_at,
            updated_at=facility.updated_at
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error creating facility: {str(e)}")