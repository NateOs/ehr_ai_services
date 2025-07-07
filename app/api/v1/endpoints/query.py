from app.dependencies import get_llama_service
from app.services.llama_service import LlamaService
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
import logging

logger = logging.getLogger(__name__)

# Create the router that will be included
router = APIRouter()

# Request/Response models
class QueryRequest(BaseModel):
    query: str
    max_tokens: Optional[int] = 1000
    temperature: Optional[float] = 0.7
    include_sources: Optional[bool] = True

class SourceDocument(BaseModel):
    content: str
    metadata: dict
    score: Optional[float] = None

class QueryResponse(BaseModel):
    response: str
    sources: Optional[List[SourceDocument]] = None
    query: str
    processing_time: Optional[float] = None

@router.post("/query", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    llama_service: LlamaService = Depends(get_llama_service)
):
    """
    Query the indexed documents using natural language.
    
    This endpoint allows users to ask questions about the indexed medical documents
    and receive AI-generated responses based on the document content.
    """
    import time
    start_time = time.time()
    
    try:
        # Validate the service is ready
        if not await llama_service.is_ready():
            raise HTTPException(
                status_code=503,
                detail="LlamaIndex service is not ready. Please try again later."
            )
        
        # Get the index from the service
        index = llama_service.get_index()
        
        # Create query engine with custom parameters
        query_engine = index.as_query_engine(
            response_mode="tree_summarize",
            verbose=True,
            similarity_top_k=5 if request.include_sources else 3
        )
        
        # Execute the query
        logger.info(f"Processing query: {request.query[:100]}...")
        response = query_engine.query(request.query)
        
        # Prepare source documents if requested
        sources = []
        if request.include_sources and hasattr(response, 'source_nodes'):
            for node in response.source_nodes:
                source_doc = SourceDocument(
                    content=node.text[:500] + "..." if len(node.text) > 500 else node.text,
                    metadata=node.metadata or {},
                    score=getattr(node, 'score', None)
                )
                sources.append(source_doc)
        
        processing_time = time.time() - start_time
        
        return QueryResponse(
            response=str(response),
            sources=sources if request.include_sources else None,
            query=request.query,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process query: {str(e)}"
        )

@router.get("/query/health")
async def query_health(
    llama_service: LlamaService = Depends(get_llama_service)
):
    """
    Check if the query service is ready to handle requests.
    """
    try:
        is_ready = await llama_service.is_ready()
        return {
            "status": "ready" if is_ready else "not_ready",
            "service": "query_endpoint",
            "llama_index_ready": is_ready
        }
    except Exception as e:
        logger.error(f"Query health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Query service health check failed: {str(e)}"
        )