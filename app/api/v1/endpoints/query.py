from app.db import get_db_session
from app.dependencies import get_llama_service
from app.services.llama_service import LlamaService
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.config import settings
import logging
from app.models.models import ClinicalQueryRequest, ClinicalQueryResponse, ClinicalInsight
from app.models.sql_models import PatientIdentifier, Facility, MedicalDocument
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import time

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
        response = query_engine.query(f"{settings.AI_SYSTEM_PROMPT}\n\nUser Query: {request.query}")
        
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
# TODO check confidence level
@router.post("/clinical", response_model=ClinicalQueryResponse)
async def query_clinical_data(
    request: ClinicalQueryRequest,
    db: Session = Depends(get_db_session),
    llama_service: LlamaService = Depends(get_llama_service)
):
    """
    Perform advanced clinical queries on patient data with AI-powered insights.
    
    **Purpose:**
    - Advanced natural language querying of clinical data
    - Generate clinical insights and recommendations
    - Support different query types (diagnostic, treatment, medication, etc.)
    - Provide evidence-based responses with source attribution
    - Clinical decision support for healthcare professionals
    
    **Request Body:**
    ```json
    {
        "query": "What are the trends in this patient's blood pressure over the last 3 months?",
        "patient_code": "PAT001_HOSP_A",
        "facility_id": "c115e85c-b368-4e29-b945-2918fa679e57",
        "query_type": "diagnostic",
        "include_context": true,
        "include_sources": true,
        "date_range_days": 90,
        "max_results": 10
    }
    ```
    
    **Example Response:**
    ```json
    {
        "query": "What are the trends in this patient's blood pressure over the last 3 months?",
        "patient_code": "PAT001_HOSP_A",
        "facility_id": "c115e85c-b368-4e29-b945-2918fa679e57",
        "response": "Analysis of blood pressure trends shows gradual improvement with current antihypertensive therapy...",
        "clinical_insights": [
            {
                "category": "treatment",
                "insight": "Blood pressure control has improved by 15% over the monitoring period",
                "confidence": 0.88,
                "supporting_evidence": ["Systolic BP decreased from 160 to 135 mmHg", "Diastolic BP stable at 85 mmHg"],
                "clinical_significance": "high"
            }
        ],
        "source_documents": [
            {
                "document_id": "doc123",
                "document_type": "vital_signs",
                "date": "2024-01-10",
                "relevance_score": 0.95
            }
        ],
        "related_conditions": ["Hypertension", "Cardiovascular disease"],
        "recommendations": ["Continue current medication", "Monitor weekly"],
        "confidence_score": 0.87,
        "query_type": "diagnostic",
        "processing_time": 2.34,
        "created_at": "2024-01-15T10:30:00Z"
    }
    ```
    
    **Query Types:**
    - `general`: General clinical questions
    - `diagnostic`: Diagnostic-related queries
    - `treatment`: Treatment and therapy questions
    - `medication`: Medication-related queries
    - `lab_results`: Laboratory test analysis
    - `imaging`: Imaging study interpretation
    - `history`: Patient history and timeline queries
    
    **Use Cases:**
    - Clinical decision support during patient consultations
    - Medical research and case analysis
    - Quality improvement initiatives
    - Medical education and training
    - Longitudinal patient care planning
    """
    start_time = time.time()
    
    try:
        # Validate patient and facility if provided
        patient = None
        facility = None
        
        if request.patient_code:
            # Find patient
            query_filter = [PatientIdentifier.patient_code == request.patient_code]
            if request.facility_id:
                query_filter.append(PatientIdentifier.facility_id == request.facility_id)
            
            patient = db.query(PatientIdentifier).filter(*query_filter).first()
            
            if not patient:
                raise HTTPException(
                    status_code=404,
                    detail="Patient not found" + (f" in facility {request.facility_id}" if request.facility_id else "")
                )
            
            # Validate facility if specified
            if request.facility_id:
                facility = db.query(Facility).filter(Facility.id == request.facility_id).first()
                if not facility:
                    raise HTTPException(status_code=404, detail="Facility not found")
        
        # Validate service readiness
        if not await llama_service.is_ready():
            raise HTTPException(
                status_code=503,
                detail="Clinical query service is not ready. Please try again later."
            )
        
        # Gather contextual data if patient is specified
        context_data = ""
        source_documents = []
        
        if patient and request.include_context:
            # Get relevant documents within date range
            document_query = db.query(MedicalDocument).filter(
                MedicalDocument.patient_identifier_id == patient.id
            )
            
            if request.date_range_days:
                cutoff_date = datetime.now() - timedelta(days=request.date_range_days)
                document_query = document_query.filter(
                    MedicalDocument.created_at >= cutoff_date
                )
            
            documents = document_query.order_by(
                MedicalDocument.created_at.desc()
            ).limit(request.max_results).all()
            
            if documents:
                context_data = "\n\nPatient Context:\n"
                for doc in documents:
                    context_data += f"- {doc.document_type} ({doc.created_at.strftime('%Y-%m-%d')}): {doc.content[:300]}...\n"
                    
                    if request.include_sources:
                        source_documents.append({
                            "document_id": str(doc.id),
                            "document_type": doc.document_type,
                            "date": doc.created_at.strftime('%Y-%m-%d'),
                            "relevance_score": 0.8  # This could be calculated based on query similarity
                        })
        
        # Prepare enhanced clinical query prompt
        clinical_prompt = f"""
        You are an advanced clinical AI assistant. Analyze the following clinical query and provide comprehensive insights.
        
        Query Type: {request.query_type}
        Patient Code: {request.patient_code or "General Query"}
        Facility: {facility.name if facility else "Not specified"}
        
        Clinical Query: {request.query}
        
        {context_data}
        
        Please provide:
        1. A comprehensive clinical response
        2. Specific clinical insights with confidence levels
        3. Evidence-based recommendations
        4. Related conditions or considerations
        5. Clinical significance assessment
        
        Focus on:
        - Clinical accuracy and evidence-based insights
        - Actionable recommendations for healthcare providers
        - Risk assessment and safety considerations
        - Differential diagnoses where applicable
        - Treatment optimization opportunities
        
        Structure your response to be clinically relevant and actionable.
        """
        
        # Execute clinical query
        logger.info(f"Processing clinical query: {request.query[:100]}... for patient: {request.patient_code}")
        
        # Use the existing query method
        ai_response = await llama_service.query(clinical_prompt)
        response_text = str(ai_response)
        
        # Extract clinical insights from response
        clinical_insights = _extract_clinical_insights(response_text, request.query_type)
        
        # Extract recommendations
        recommendations = _extract_recommendations(response_text)
        
        # Extract related conditions
        related_conditions = _extract_related_conditions(response_text)
        
        # Calculate confidence score
        confidence_score = _calculate_clinical_confidence(
            response_text, 
            clinical_insights, 
            len(source_documents)
        )
        
        processing_time = time.time() - start_time
        
        # Create response
        response = ClinicalQueryResponse(
            query=request.query,
            patient_code=request.patient_code,
            facility_id=request.facility_id,
            response=response_text,
            clinical_insights=clinical_insights,
            source_documents=source_documents if request.include_sources else [],
            related_conditions=related_conditions,
            recommendations=recommendations,
            confidence_score=confidence_score,
            query_type=request.query_type,
            processing_time=processing_time
        )
        
        logger.info(f"Clinical query completed for patient {request.patient_code}, "
                   f"insights: {len(clinical_insights)}, processing time: {processing_time:.2f}s")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing clinical query: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing clinical query: {str(e)}"
        )

def _extract_clinical_insights(response_text: str, query_type: str) -> List[ClinicalInsight]:
    """Extract structured clinical insights from AI response."""
    insights = []
    lines = response_text.split('\n')
    
    # Look for insight patterns in the response
    current_insight = None
    current_evidence = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check for insight indicators
        if any(keyword in line.lower() for keyword in ['insight:', 'finding:', 'observation:', 'conclusion:']):
            if current_insight:
                # Save previous insight
                insights.append(ClinicalInsight(
                    category=_determine_category(current_insight, query_type),
                    insight=current_insight,
                    confidence=_extract_confidence(current_insight),
                    supporting_evidence=current_evidence.copy(),
                    clinical_significance=_determine_significance(current_insight)
                ))
            
            current_insight = line.split(':', 1)[1].strip() if ':' in line else line
            current_evidence = []
            
        elif current_insight and line.startswith(('-', '•', '*')):
            # This is supporting evidence
            current_evidence.append(line[1:].strip())
    
    # Add the last insight if exists
    if current_insight:
        insights.append(ClinicalInsight(
            category=_determine_category(current_insight, query_type),
            insight=current_insight,
            confidence=_extract_confidence(current_insight),
            supporting_evidence=current_evidence,
            clinical_significance=_determine_significance(current_insight)
        ))
    
    return insights[:5]  # Limit to top 5 insights

def _determine_category(insight_text: str, query_type: str) -> str:
    """Determine the category of a clinical insight."""
    insight_lower = insight_text.lower()
    
    if any(word in insight_lower for word in ['diagnos', 'condition', 'disease', 'disorder']):
        return "diagnosis"
    elif any(word in insight_lower for word in ['treatment', 'therapy', 'intervention']):
        return "treatment"
    elif any(word in insight_lower for word in ['medication', 'drug', 'prescription']):
        return "medication"
    elif any(word in insight_lower for word in ['lab', 'test', 'result', 'level']):
        return "lab"
    elif any(word in insight_lower for word in ['imaging', 'scan', 'x-ray']):
        return "imaging"
    elif any(word in insight_lower for word in ['risk', 'factor', 'complication']):
        return "risk_factor"
    else:
        return query_type

def _extract_confidence(text: str) -> float:
    """Extract confidence level from text or assign based on content."""
    text_lower = text.lower()
    
    if any(word in text_lower for word in ['certain', 'definitive', 'confirmed']):
        return 0.9
    elif any(word in text_lower for word in ['likely', 'probable', 'suggests']):
        return 0.8
    elif any(word in text_lower for word in ['possible', 'may', 'could']):
        return 0.6
    elif any(word in text_lower for word in ['uncertain', 'unclear', 'inconclusive']):
        return 0.4
    else:
        return 0.7  # Default confidence

def _determine_significance(insight_text: str) -> str:
    """Determine clinical significance of an insight."""
    insight_lower = insight_text.lower()
    
    if any(word in insight_lower for word in ['critical', 'urgent', 'severe', 'emergency']):
        return "high"
    elif any(word in insight_lower for word in ['moderate', 'significant', 'important']):
        return "medium"
    else:
        return "low"

def _extract_recommendations(response_text: str) -> List[str]:
    """Extract recommendations from AI response."""
    recommendations = []
    lines = response_text.split('\n')
    
    in_recommendations_section = False
    for line in lines:
        line = line.strip()
        if 'recommendation' in line.lower() or 'suggest' in line.lower():
            in_recommendations_section = True
            if ':' in line:
                rec = line.split(':', 1)[1].strip()
                if rec:
                    recommendations.append(rec)
            continue
        elif in_recommendations_section and line.startswith(('-', '•', '*')):
            recommendations.append(line[1:].strip())
        elif in_recommendations_section and line.startswith(('1.', '2.', '3.', '4.', '5.')):
            recommendations.append(line[2:].strip())
        elif in_recommendations_section and line and not line.startswith(('-', '•', '*')):
            in_recommendations_section = False
    
    return recommendations[:5]  # Limit to top 5 recommendations

def _extract_related_conditions(response_text: str) -> List[str]:
    """Extract related conditions from AI response."""
    conditions = []
    lines = response_text.split('\n')
    
    # Look for sections mentioning related conditions
    for line in lines:
        line = line.strip()
        if any(phrase in line.lower() for phrase in ['related condition', 'differential', 'consider', 'rule out']):
            # Extract conditions from this line
            if ':' in line:
                condition_text = line.split(':', 1)[1].strip()
                # Split by common separators
                for separator in [',', ';', 'and', 'or']:
                    if separator in condition_text:
                        conditions.extend([c.strip() for c in condition_text.split(separator)])
                        break
                else:
                    conditions.append(condition_text)
    
    # Clean and deduplicate
    conditions = [c for c in conditions if c and len(c) > 2]
    return list(set(conditions))[:5]  # Limit to top 5 unique conditions

def _calculate_clinical_confidence(response_text: str, clinical_insights: List[ClinicalInsight], num_sources: int) -> float:
    """Calculate confidence score based on response quality and number of sources."""
    base_confidence = 0.5
    
    # Boost confidence based on number of insights
    insight_boost = min(len(clinical_insights) * 0.1, 0.3)
    
    # Boost confidence based on number of sources
    source_boost = min(num_sources * 0.05, 0.2)
    
    # Boost confidence based on response length and detail
    response_length_boost = min(len(response_text) / 1000 * 0.1, 0.2)
    
    # Average confidence from individual insights
    if clinical_insights:
        avg_insight_confidence = sum(insight.confidence for insight in clinical_insights) / len(clinical_insights)
        insight_confidence_boost = (avg_insight_confidence - 0.5) * 0.3
    else:
        insight_confidence_boost = 0
    
    total_confidence = base_confidence + insight_boost + source_boost + response_length_boost + insight_confidence_boost
    
    # Ensure confidence is between 0 and 1
    return max(0.0, min(1.0, total_confidence))