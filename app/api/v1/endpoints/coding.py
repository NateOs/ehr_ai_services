from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional
from app.db import get_db_session
from app.dependencies import get_llama_service
from app.services.llama_service import LlamaService
from app.models.models import CodeSuggestionRequest, CodeSuggestionResponse, CodeSuggestion
from app.models.sql_models import PatientIdentifier, Facility
from app.core.logging import logger
import json
import re

router = APIRouter()

@router.post("/suggest/codes", response_model=CodeSuggestionResponse)
async def suggest_medical_codes(
    request: CodeSuggestionRequest,
    db: Session = Depends(get_db_session),
    llama_service: LlamaService = Depends(get_llama_service)
):
    """
    Suggest ICD-10 and CPT codes based on clinical notes.
    
    **Purpose:**
    - Analyze clinical notes and suggest appropriate medical codes
    - Support both ICD-10 (diagnosis) and CPT (procedure) codes
    - Provide confidence scores for each suggestion
    - Help healthcare professionals with accurate coding
    
    **Request Body:**
    ```json
    {
        "clinical_notes": "Patient presents with acute chest pain, shortness of breath. ECG shows ST elevation in leads II, III, aVF. Troponin elevated. Diagnosed with inferior STEMI. Underwent primary PCI with stent placement to RCA.",
        "patient_code": "PAT001_HOSP_A",
        "facility_id": "c115e85c-b368-4e29-b945-2918fa679e57",
        "include_procedures": true,
        "include_diagnoses": true,
        "max_suggestions": 10
    }
    ```
    
    **Example Response:**
    ```json
    {
        "patient_code": "PAT001_HOSP_A",
        "facility_id": "c115e85c-b368-4e29-b945-2918fa679e57",
        "icd10_suggestions": [
            {
                "code": "I21.19",
                "description": "ST elevation (STEMI) myocardial infarction involving other coronary artery of inferior wall",
                "confidence": 0.95,
                "category": "primary",
                "code_type": "ICD-10"
            }
        ],
        "cpt_suggestions": [
            {
                "code": "92928",
                "description": "Percutaneous transcatheter placement of intracoronary stent(s), with coronary angioplasty when performed; single major coronary artery or branch",
                "confidence": 0.90,
                "category": "procedure",
                "code_type": "CPT"
            }
        ],
        "clinical_summary": "Patient diagnosed with inferior STEMI and treated with primary PCI",
        "confidence_score": 0.92,
        "processing_notes": ["High confidence diagnosis based on clear clinical indicators"],
        "created_at": "2024-01-15T10:30:00Z"
    }
    ```
    
    **Use Cases:**
    - Medical coding assistance for billing departments
    - Quality assurance for coding accuracy
    - Training tool for medical coders
    - Integration with EHR systems for automated coding suggestions
    - Audit trail for coding decisions
    """
    try:
        # Validate patient and facility if provided
        patient = None
        facility = None
        
        if request.patient_code and request.facility_id:
            patient = db.query(PatientIdentifier).filter(
                PatientIdentifier.patient_code == request.patient_code,
                PatientIdentifier.facility_id == request.facility_id
            ).first()
            
            if not patient:
                raise HTTPException(
                    status_code=404, 
                    detail="Patient not found in specified facility"
                )
            
            facility = db.query(Facility).filter(
                Facility.id == request.facility_id
            ).first()
            
            if not facility:
                raise HTTPException(status_code=404, detail="Facility not found")
        
        # Validate clinical notes
        if not request.clinical_notes.strip():
            raise HTTPException(
                status_code=400,
                detail="Clinical notes cannot be empty"
            )
        
        if len(request.clinical_notes) < 10:
            raise HTTPException(
                status_code=400,
                detail="Clinical notes too short for meaningful analysis"
            )
        
        # Prepare coding analysis prompt
        coding_prompt = f"""
        Analyze the following clinical notes and suggest appropriate medical codes:
        
        Clinical Notes:
        {request.clinical_notes}
        
        Requirements:
        - Include ICD-10 codes: {request.include_diagnoses}
        - Include CPT codes: {request.include_procedures}
        - Maximum suggestions: {request.max_suggestions}
        
        Please provide:
        1. ICD-10 diagnosis codes with descriptions and confidence scores
        2. CPT procedure codes with descriptions and confidence scores
        3. Categorize codes as primary, secondary, or procedure
        4. Provide a clinical summary
        5. Include processing notes for any assumptions made
        
        Format the response as structured data that can be parsed.
        Focus on accuracy and provide confidence scores between 0.0 and 1.0.
        """
        
        # Get AI analysis
        analysis_result = await llama_service.suggest_medical_codes(
            prompt=coding_prompt,
            clinical_notes=request.clinical_notes,
            include_diagnoses=request.include_diagnoses,
            include_procedures=request.include_procedures,
            max_suggestions=request.max_suggestions
        )
        
        # Parse AI response and extract structured data
        icd10_suggestions = []
        cpt_suggestions = []
        clinical_summary = ""
        confidence_score = 0.8
        processing_notes = []
        
        # Extract structured data from AI response
        if hasattr(analysis_result, 'icd10_codes'):
            icd10_suggestions = [
                CodeSuggestion(
                    code=code.get('code', ''),
                    description=code.get('description', ''),
                    confidence=code.get('confidence', 0.5),
                    category=code.get('category', 'secondary'),
                    code_type="ICD-10"
                )
                for code in analysis_result.icd10_codes
            ]
        
        if hasattr(analysis_result, 'cpt_codes'):
            cpt_suggestions = [
                CodeSuggestion(
                    code=code.get('code', ''),
                    description=code.get('description', ''),
                    confidence=code.get('confidence', 0.5),
                    category=code.get('category', 'procedure'),
                    code_type="CPT"
                )
                for code in analysis_result.cpt_codes
            ]
        
        if hasattr(analysis_result, 'clinical_summary'):
            clinical_summary = analysis_result.clinical_summary
        else:
            clinical_summary = _extract_clinical_summary(str(analysis_result))
        
        if hasattr(analysis_result, 'confidence_score'):
            confidence_score = analysis_result.confidence_score
        else:
            confidence_score = _calculate_overall_confidence(icd10_suggestions + cpt_suggestions)
        
        if hasattr(analysis_result, 'processing_notes'):
            processing_notes = analysis_result.processing_notes
        
        # Create response
        response = CodeSuggestionResponse(
            patient_code=request.patient_code,
            facility_id=request.facility_id,
            icd10_suggestions=icd10_suggestions,
            cpt_suggestions=cpt_suggestions,
            clinical_summary=clinical_summary,
            confidence_score=confidence_score,
            processing_notes=processing_notes
        )
        
        logger.info(f"Code suggestions generated for patient {request.patient_code}, "
                   f"ICD-10: {len(icd10_suggestions)}, CPT: {len(cpt_suggestions)}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating code suggestions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating code suggestions: {str(e)}"
        )

def _extract_clinical_summary(ai_response: str) -> str:
    """Extract clinical summary from AI response text."""
    lines = ai_response.split('\n')
    summary_lines = []
    
    for line in lines:
        line = line.strip()
        if line and not line.startswith(('ICD', 'CPT', 'Code:', 'Confidence:')):
            if len(line) > 20 and '.' in line:
                summary_lines.append(line)
    
    return ' '.join(summary_lines[:3]) if summary_lines else "Clinical analysis completed"

def _calculate_overall_confidence(suggestions: List[CodeSuggestion]) -> float:
    """Calculate overall confidence score from individual suggestions."""
    if not suggestions:
        return 0.5
    
    total_confidence = sum(suggestion.confidence for suggestion in suggestions)
    avg_confidence = total_confidence / len(suggestions)
    
    # Adjust based on number of suggestions
    if len(suggestions) >= 3:
        return min(avg_confidence + 0.1, 1.0)
    elif len(suggestions) >= 2:
        return avg_confidence
    else:
        return max(avg_confidence - 0.1, 0.0)