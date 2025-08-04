from pydantic import BaseModel

from app.api.v1.endpoints import medical_data
from ..endpoints import query
from app.models.models import FacilityCreate, FacilityResponse
from app.models.sql_models import Facility as SQLFacility, VectorDB as SQLVectorDB, Collection as SQLCollection
from app.db import get_db_session
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from uuid import UUID
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/facilities/external/{external_id}", response_model=FacilityResponse)
async def get_facility_by_external_id(
    external_id: str,
    db: Session = Depends(get_db_session)
):
    """
    Get facility by external ID for integration with external systems.
    
    **Purpose:**
    - Allows external systems to lookup facilities using their own identifiers
    - Useful for EMR integrations and third-party system connections
    
    **Parameters:**
    - `external_id`: The external system's identifier for the facility
    
    **Example Request:**
    ```
    GET /api/v1/facilities/external/HOSP_001
    ```
    
    **Example Response:**
    ```json
    {
        "id": "c115e85c-b368-4e29-b945-2918fa679e57",
        "name": "General Hospital",
        "address": "123 Medical Center Dr, City, State 12345",
        "external_id": "HOSP_001",
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z"
    }
    """
    facility = db.query(SQLFacility).filter(
        SQLFacility.external_id == external_id
    ).first()
    
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

@router.post("/facilities", response_model=FacilityResponse)
async def create_facility(
    facility_data: FacilityCreate, 
    db: Session = Depends(get_db_session)
):
    """
    Create a new healthcare facility with its associated infrastructure.
    
    **Auto-Infrastructure Setup:**
    - Creates a dedicated VectorDB for the facility
    - Sets up a shared collection for facility-wide documents
    - Establishes the foundation for patient-specific collections
    
    **Request Body:**
    ```json
    {
        "name": "General Hospital",
        "address": "123 Medical Center Dr, City, State 12345",
        "external_id": "HOSP_001"
    }
    ```
    
    **What Gets Created:**
    1. **Facility Record**: Main facility information
    2. **VectorDB**: `{facility_name}_VectorDB` for AI embeddings
    3. **Shared Collection**: `Facility_Shared_Collection` for general documents
    
    **Example Response:**
    ```json
    {
        "id": "c115e85c-b368-4e29-b945-2918fa679e57",
        "name": "General Hospital",
        "address": "123 Medical Center Dr, City, State 12345",
        "external_id": "HOSP_001",
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z"
    }
    ```
    
    **Use Cases:**
    - Hospital system onboarding
    - Clinic network expansion
    - EMR system integration
    - Multi-facility healthcare organizations
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
        
        logger.info(f"Facility created successfully: {facility.id}")
        
        return FacilityResponse(
            id=facility.id,
            name=facility.name,
            address=facility.address,
            external_id=facility.external_id,
            created_at=facility.created_at,
            updated_at=facility.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating facility: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error creating facility: {str(e)}")

@router.get("/facilities", response_model=List[FacilityResponse])
async def list_facilities(db: Session = Depends(get_db_session)):
    """
    List all registered healthcare facilities.
    
    **Purpose:**
    - Get overview of all facilities in the system
    - Useful for administrative dashboards
    - Facility selection in user interfaces
    
    **Example Response:**
    ```json
    [
        {
            "id": "c115e85c-b368-4e29-b945-2918fa679e57",
            "name": "General Hospital",
            "address": "123 Medical Center Dr, City, State 12345",
            "external_id": "HOSP_001",
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:30:00Z"
        },
        {
            "id": "d226f96d-c479-5f3a-c056-3029gb780e68",
            "name": "City Clinic",
            "address": "456 Health Ave, City, State 12345",
            "external_id": "CLINIC_002",
            "created_at": "2024-01-16T14:20:00Z",
            "updated_at": "2024-01-16T14:20:00Z"
        }
    ]
    ```
    
    **Use Cases:**
    - Administrative facility management
    - System monitoring and reporting
    - User interface facility selection
    - Integration with external systems
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

@router.get("/facilities/{facility_id}", response_model=FacilityResponse)
async def get_facility(
    facility_id: UUID, 
    db: Session = Depends(get_db_session)
):
    """
    Get detailed information about a specific facility.
    
    **Purpose:**
    - Retrieve complete facility details by UUID
    - Verify facility existence before operations
    - Display facility information in applications
    
    **Parameters:**
    - `facility_id`: UUID of the facility
    
    **Example Request:**
    ```
    GET /api/v1/facilities/c115e85c-b368-4e29-b945-2918fa679e57
    ```
    
    **Example Response:**
    ```json
    {
        "id": "c115e85c-b368-4e29-b945-2918fa679e57",
        "name": "General Hospital",
        "address": "123 Medical Center Dr, City, State 12345",
        "external_id": "HOSP_001",
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z"
    }
    ```
    
    **Error Responses:**
    - `404`: Facility not found
    - `422`: Invalid UUID format
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