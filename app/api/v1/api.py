from fastapi import APIRouter
from .endpoints import query

api_router = APIRouter()

api_router.include_router(query.router,  tags=["query"])

@api_router.get("/test")
async def test_endpoint():
    return {"message": "API v1 is working"}
