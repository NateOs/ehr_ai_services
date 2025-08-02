from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.v1.endpoints import documents, facilities, medical_data
from .endpoints import query
from app.models import Facility, FacilityCreate, FacilityResponse, VectorDB, Collection
from app.models.sql_models import Facility as SQLFacility  # Import SQLAlchemy model
from app.db import get_db_session
from sqlalchemy.orm import Session
from fastapi import Depends

api_router = APIRouter()

api_router.include_router(query.router, tags=["query"])
api_router.include_router(medical_data.router, tags=["medical_data"])
api_router.include_router(facilities.router, tags=["facilities"])
api_router.include_router(documents.router, tags=["documents"])

@api_router.get("/test")
async def test_endpoint():
    return {"message": "API v1 is working"}
