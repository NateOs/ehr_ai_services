from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from uuid import UUID
import json
import tempfile
import os
from pathlib import Path

from app.db import get_db_session
from app.dependencies import get_llama_service
from app.services.llama_service import LlamaService
from app.models.models import (
    AnalysisResultCreate,
    AnalysisResultResponse,
    DiagnosticInsight,
    AbnormalFlag
)
from app.models.sql_models import PatientIdentifier, Facility, MedicalDocument
from app.utils.document_utils import extract_text_from_file, validate_medical_file
from app.core.logging import logger

router = APIRouter()

@router.post("/analyze/results", response_model=AnalysisResultResponse)
async def analyze_patient_results(
    patient_code: str = Form(...),
    facility_id: UUID = Form(...),
    text_data: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    analysis_type: str = Form("comprehensive"),  # comprehensive, lab_results, imaging, etc.
    include_history: bool = Form(True),
    db: Session = Depends(get_db_session),
    llama_service: LlamaService = Depends(get_llama_service)
):
    """
    Analyze patient results from text data and/or uploaded files.
    
    **Purpose:**
    - Flag abnormal results in lab reports, imaging studies, or clinical notes
    - Provide diagnostic insights based on patient data
    - Support both text input and file uploads (PDF, images, etc.)
    - Optionally include patient history for context
    
    **Form Parameters:**
    - `patient_code`: The anonymized patient identifier
    - `facility_id`: The facility UUID
    - `text_data`: Optional text data to analyze (lab results, notes, etc.)
    - `file`: Optional file upload (PDF, image, etc.)
    - `analysis_type`: Type of analysis (comprehensive, lab_results, imaging, clinical_notes)
    - `include_history`: Whether to include patient history for context
    
    **Example Request:**
    ```
    POST /api/v1/analyze/results
    Content-Type: multipart/form-data
    
    patient_code: PAT001_HOSP_A
    facility_id: c115e85c-b368-4e29-b945-2918fa679e57
    text_data: "Hemoglobin: 8.2 g/dL, WBC: 15,000/μL, Glucose: 180 mg/dL"
    analysis_type: lab_results
    include_history: true
    ```
    
    **Example Response:**
    ```json
    {
        "analysis_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "patient_code": "PAT001_HOSP_A",
        "abnormal_flags": [
            {
                "parameter": "Hemoglobin",
                "value": "8.2 g/dL",
                "normal_range": "12.0-15.5 g/dL (female)",
                "severity": "moderate",
                "flag_type": "low"
            }
        ],
        "diagnostic_insights": [
            {
                "category": "hematology",
                "insight": "Low hemoglobin suggests possible anemia",
                "confidence": 0.85,
                "recommendations": ["Further iron studies", "Reticulocyte count"]
            }
        ],
        "summary": "Analysis reveals potential anemia and elevated glucose levels requiring follow-up",
        "created_at": "2024-01-15T10:30:00Z"
    }
    ```
    """
    try:
        # Validate inputs
        if not text_data and not file:
            raise HTTPException(
                status_code=400, 
                detail="Either text_data or file must be provided"
            )
        
        # Verify patient exists
        patient = db.query(PatientIdentifier).filter(
            PatientIdentifier.patient_code == patient_code,
            PatientIdentifier.facility_id == facility_id
        ).first()
        
        if not patient:
            raise HTTPException(
                status_code=404, 
                detail="Patient not found in specified facility"
            )
        
        # Verify facility exists
        facility = db.query(Facility).filter(Facility.id == facility_id).first()
        if not facility:
            raise HTTPException(status_code=404, detail="Facility not found")
        
        # Process file if provided
        file_content = ""
        if file:
            if not validate_medical_file(file):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid file type. Supported: PDF, DOCX, TXT, JPG, PNG"
                )
            
            # Extract text from file
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
                content = await file.read()
                tmp_file.write(content)
                tmp_file.flush()
                
                file_content = extract_text_from_file(tmp_file.name, file.content_type)
                os.unlink(tmp_file.name)  # Clean up temp file
        
        # Combine text data and file content
        combined_content = ""
        if text_data:
            combined_content += f"Text Data:\n{text_data}\n\n"
        if file_content:
            combined_content += f"File Content:\n{file_content}\n\n"
        
        # Get patient history if requested
        patient_history = ""
        if include_history:
            recent_documents = db.query(MedicalDocument).filter(
                MedicalDocument.patient_identifier_id == patient.id
            ).order_by(MedicalDocument.created_at.desc()).limit(5).all()
            
            if recent_documents:
                patient_history = "Recent Patient History:\n"
                for doc in recent_documents:
                    patient_history += f"- {doc.document_type}: {doc.content[:200]}...\n"
        
        # Prepare analysis prompt
        analysis_prompt = f"""
        Analyze the following medical data for patient {patient_code}:
        
        Analysis Type: {analysis_type}
        
        {combined_content}
        
        {patient_history}
        
        Please provide:
        1. Abnormal flags with specific values, normal ranges, and severity
        2. Diagnostic insights with confidence levels
        3. Clinical recommendations
        4. Overall summary
        
        Focus on identifying abnormal results and providing actionable insights.
        """
        
        # Perform AI analysis
        analysis_result = await llama_service.analyze_medical_data(
            prompt=analysis_prompt,
            patient_code=patient_code,
            analysis_type=analysis_type
        )
        
        # Parse and structure the response
        abnormal_flags = []
        diagnostic_insights = []
        
        # Extract structured data from AI response
        # This would depend on your LlamaService implementation
        if hasattr(analysis_result, 'abnormal_flags'):
            abnormal_flags = analysis_result.abnormal_flags
        
        if hasattr(analysis_result, 'diagnostic_insights'):
            diagnostic_insights = analysis_result.diagnostic_insights
        
        # Create response
        response = AnalysisResultResponse(
            analysis_id=analysis_result.id if hasattr(analysis_result, 'id') else None,
            patient_code=patient_code,
            facility_id=facility_id,
            analysis_type=analysis_type,
            abnormal_flags=abnormal_flags,
            diagnostic_insights=diagnostic_insights,
            summary=analysis_result.summary if hasattr(analysis_result, 'summary') else str(analysis_result),
            confidence_score=analysis_result.confidence if hasattr(analysis_result, 'confidence') else 0.8,
            recommendations=analysis_result.recommendations if hasattr(analysis_result, 'recommendations') else [],
            created_at=analysis_result.created_at if hasattr(analysis_result, 'created_at') else None
        )
        
        logger.info(f"Analysis completed for patient {patient_code}, type: {analysis_type}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing patient results: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error analyzing patient results: {str(e)}"
        )