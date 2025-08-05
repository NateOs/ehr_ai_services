from fastapi import APIRouter

from app.api.v1.endpoints import documents, facilities, medical_data, query, analysis

api_router = APIRouter()

api_router.include_router(query.router, tags=["query"])
api_router.include_router(medical_data.router, tags=["medical-data"])
api_router.include_router(facilities.router, tags=["facilities"])
api_router.include_router(documents.router, tags=["documents"])
api_router.include_router(analysis.router, tags=["analysis"])  # Add this line

@api_router.get("/test")
async def test_endpoint():
    return {"message": "API v1 is working"}
