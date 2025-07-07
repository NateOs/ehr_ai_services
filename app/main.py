import sys
import os

# Add the parent directory to the Python path for direct execution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.services.llama_service import LlamaService
from app.dependencies import set_llama_service, get_llama_service

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    logger.info("Starting up EHR AI Services...")
    
    try:
        # Initialize LlamaIndex service
        llama_service = LlamaService()
        await llama_service.initialize()
        
        # Set the global service instance
        set_llama_service(llama_service)
        
        logger.info("LlamaIndex service initialized successfully")
        
        # Add any other startup tasks here
        logger.info("Application startup completed")
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down EHR AI Services...")
    
    try:
        # Cleanup resources
        service = get_llama_service()
        if service:
            await service.cleanup()
        logger.info("Application shutdown completed")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="EHR AI Services - LlamaIndex Web Interface for medical document processing and querying",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Add trusted host middleware for security
if settings.ALLOWED_HOSTS != ["*"]:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )

# Add request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception handler caught: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.DEBUG else "An unexpected error occurred"
        }
    )

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Root endpoints
@app.get("/")
async def root():
    """
    Root endpoint - provides basic API information
    """
    return {
        "message": "EHR AI Services API",
        "version": settings.VERSION,
        "description": "LlamaIndex-powered medical document processing and querying service",
        "docs_url": "/docs",
        "health_check": "/health",
        "api_v1": settings.API_V1_STR
    }

@app.get("/health")
async def health_check():
    """
    Basic health check endpoint
    """
    try:
        # Check if LlamaService is ready
        is_llama_ready = get_llama_service() and await get_llama_service().is_ready()
        
        return {
            "status": "healthy" if is_llama_ready else "degraded",
            "timestamp": time.time(),
            "version": settings.VERSION,
            "services": {
                "llama_index": "ready" if is_llama_ready else "not_ready",
                "database": "connected",  # You can add actual DB health check here
                "api": "ready"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": time.time(),
                "error": str(e)
            }
        )

@app.get("/info")
async def app_info():
    """
    Application information endpoint
    """
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "api_version": settings.API_V1_STR,
        "features": [
            "Document upload and processing",
            "Vector-based document search",
            "Natural language querying",
            "Chat-style interactions",
            "Embedding generation"
        ],
        "supported_formats": [
            "PDF", "TXT", "DOCX", "MD"
        ]
    }

# Development helper endpoints (only in debug mode)
if settings.DEBUG:
    @app.get("/debug/config")
    async def debug_config():
        """
        Debug endpoint to view configuration (only in debug mode)
        """
        return {
            "project_name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "log_level": settings.LOG_LEVEL,
            "database_host": settings.POSTGRES_SERVER,
            "database_name": settings.POSTGRES_DB,
            "vector_dimension": settings.VECTOR_DIMENSION,
            "embedding_model": settings.EMBEDDING_MODEL,
            "llm_model": settings.LLM_MODEL
        }

# Dependency to get LlamaService instance
def get_llama_service() -> LlamaService:
    """
    Dependency to get the global LlamaService instance
    """
    service = get_llama_service()
    if not service:
        raise RuntimeError("LlamaService not initialized")
    return service

# Make the dependency available for import
app.dependency_overrides = {}

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )