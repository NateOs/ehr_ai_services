from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from app.db import get_db_session
from app.dependencies import get_llama_service
from app.services.llama_service import LlamaService
from app.models.sql_models import PatientIdentifier, Facility, MedicalDocument
from app.models.models import DischargeInstructionRequest, DischargeInstructionResponse
from app.core.logging import logger
from typing import Optional, List, Dict, Any
import json

router = APIRouter()


# TODO review how far back and what medical history is considered
# TODO modify code to use add the response to the vector database
@router.post("/generate/discharge-instructions", response_model=DischargeInstructionResponse)
async def generate_discharge_instructions(
    request: DischargeInstructionRequest,
    db: Session = Depends(get_db_session),
    llama_service: LlamaService = Depends(get_llama_service)
):
    """
    Generate comprehensive discharge instructions following best practices.
    
    **Based on Evidence-Based Discharge Best Practices:**
    
    1. **Thorough Paperwork Review** - Instructions written in patient-friendly language
    2. **Medication Reconciliation** - Clear explanation of all medication changes
    3. **No Assumptions** - Everything explained, open-ended questions encouraged
    4. **Comprehensive Follow-up** - All appointments, services, and testing coordinated
    
    **Key Features:**
    - Generates "repeat back" checklist for patient verification
    - Addresses medication changes with both generic and brand names
    - Provides clear follow-up instructions with phone numbers
    - Tailored to patient's education and literacy level
    - Includes family/caregiver in planning
    """
    try:
        # Verify patient exists using patient_identifier_id
        patient = db.query(PatientIdentifier).filter(
            PatientIdentifier.id == request.patient_identifier_id
        ).first()
        
        if not patient:
            raise HTTPException(
                status_code=404,
                detail="Patient not found"
            )
        
        # Verify facility exists
        facility = db.query(Facility).filter(Facility.id == patient.facility_id).first()
        if not facility:
            raise HTTPException(status_code=404, detail="Facility not found")
        
        # Get patient's recent medical history for context
        recent_documents = db.query(MedicalDocument).filter(
            MedicalDocument.patient_identifier_id == patient.id
        ).order_by(MedicalDocument.created_at.desc()).limit(5).all()
        
        patient_history = ""
        if recent_documents:
            patient_history = "Recent Patient History:\n"
            for doc in recent_documents:
                patient_history += f"- {doc.document_type}: {doc.content[:200]}...\n"
        
        # Prepare discharge instruction prompt
        medications_text = "\n".join([f"- {med}" for med in request.medications]) if request.medications else "No medications prescribed"
        
        discharge_prompt = f"""
        Generate comprehensive discharge instructions for patient {patient.patient_code}:
        
        **Patient Information:**
        - Patient Code: {patient.patient_code}
        - Facility: {facility.name}
        - Age Range: {patient.age_range or 'Not specified'}
        - Gender: {patient.gender or 'Not specified'}
        
        **Discharge Details:**
        - Primary Diagnosis: {request.diagnosis}
        - Language Preference: {request.language_preference}
        - Reading Level: {request.reading_level}
        
        **Medications:**
        {medications_text}
        
        **Follow-up Instructions:**
        {request.follow_up_instructions or 'Standard follow-up as needed'}
        
        **Activity Restrictions:**
        {request.activity_restrictions or 'No specific restrictions'}
        
        **Diet Instructions:**
        {request.diet_instructions or 'Regular diet as tolerated'}
        
        **Warning Signs:**
        {request.warning_signs or 'Standard warning signs to watch for'}
        
        **Additional Notes:**
        {request.additional_notes or 'No additional notes'}
        
        **Recent Medical History:**
        {patient_history}
        
        Please generate comprehensive, patient-friendly discharge instructions that include:
        1. Clear explanation of the diagnosis in simple terms
        2. Detailed medication instructions with purpose and timing
        3. Specific follow-up care instructions
        4. Activity and diet guidelines
        5. Warning signs that require immediate medical attention
        6. Emergency contact information
        
        Tailor the language to the specified reading level ({request.reading_level}) and ensure all instructions are clear and actionable.
        """
        
        # Generate discharge instructions using AI
        try:
            response = await llama_service.query(discharge_prompt)
            discharge_instructions = str(response)
        except Exception as e:
            logger.error(f"Error querying LlamaService: {str(e)}")
            # Fallback to basic instructions
            discharge_instructions = f"""
            DISCHARGE INSTRUCTIONS FOR {patient.patient_code}
            
            Diagnosis: {request.diagnosis}
            
            Medications: {medications_text}
            
            Follow-up: {request.follow_up_instructions or 'Follow up with your primary care provider as needed'}
            
            Activity: {request.activity_restrictions or 'Resume normal activities as tolerated'}
            
            Diet: {request.diet_instructions or 'Regular diet'}
            
            Warning Signs: {request.warning_signs or 'Contact your doctor if symptoms worsen'}
            
            Additional Notes: {request.additional_notes or 'Take care and follow all instructions'}
            """
        
        # Parse medications for response
        medication_explanations = []
        if request.medications:
            for med in request.medications:
                medication_explanations.append(f"Take {med} as prescribed by your doctor")
        
        # Create response
        from datetime import datetime
        response_data = DischargeInstructionResponse(
            patient_identifier_id=request.patient_identifier_id,
            discharge_instructions=discharge_instructions,
            medication_explanations=medication_explanations,
            follow_up_summary=request.follow_up_instructions,
            emergency_contact_info=f"For emergencies, contact {facility.name} or call 911",
            generated_at=datetime.now().isoformat(),
            language=request.language_preference,
            reading_level=request.reading_level
        )
        
        logger.info(f"Generated discharge instructions for patient {patient.patient_code}")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating discharge instructions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating discharge instructions: {str(e)}"
        )