from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .endpoints import query
from app.models import Facility, FacilityCreate, FacilityResponse, VectorDB, Collection
from app.models.sql_models import Facility as SQLFacility  # Import SQLAlchemy model
from app.db import get_db_session
from sqlalchemy.orm import Session
from fastapi import Depends

api_router = APIRouter()

api_router.include_router(query.router, tags=["query"])

@api_router.get("/test")
async def test_endpoint():
    return {"message": "API v1 is working"}

@api_router.post("/facility", response_model=FacilityResponse)
async def create_facility(facility_data: FacilityCreate, db: Session = Depends(get_db_session)):
    vector_db = VectorDB(
        name=f"{facility_data.name}_VectorDB",
        collections=[Collection(name="Facility_Shared_Collection")]
    )
    
    facility = SQLFacility(
        name=facility_data.name,
        address=facility_data.address
    )
    
    db.add(facility)
    db.commit()
    db.refresh(facility)
    
    return FacilityResponse(
        id=facility.id,
        name=facility.name,
        address=facility.address,
        created_at=facility.created_at,
        updated_at=facility.updated_at
    )