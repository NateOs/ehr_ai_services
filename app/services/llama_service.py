from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters, FilterOperator
from app.core.llama_setup import setup_llama_index_with_openai, create_query_engine, load_documents_to_index
from app.models.models import AbnormalFlag, DiagnosticInsight  # Add this import
from app.core.logging import logger
import logging
from typing import Dict, Any, List, Optional
from uuid import uuid4
from datetime import datetime
import json
import re

logger = logging.getLogger(__name__)

class LlamaService:
    def __init__(self):
        self._index: VectorStoreIndex = None
        self._vector_store: PGVectorStore = None
        self._initialized = False

    async def initialize(self):
        """Initialize LlamaIndex with OpenAI and PostgreSQL vector store"""
        if self._initialized:
            return
            
        try:
            logger.info("Initializing LlamaService with OpenAI...")
            
            # Setup LlamaIndex with OpenAI
            self._index, self._vector_store = await setup_llama_index_with_openai()
            
            self._initialized = True
            logger.info("LlamaService initialized successfully with OpenAI")
            
        except Exception as e:
            logger.error(f"Failed to initialize LlamaService: {e}")
            raise

    async def is_ready(self) -> bool:
        """Check if the service is ready to handle requests"""
        return self._initialized and self._index is not None

    def get_index(self) -> VectorStoreIndex:
        """Get the vector store index"""
        if not self._initialized:
            raise RuntimeError("LlamaService not initialized")
        return self._index

    def get_vector_store(self) -> PGVectorStore:
        """Get the vector store"""
        if not self._initialized:
            raise RuntimeError("LlamaService not initialized")
        return self._vector_store

    async def add_documents(self, documents_path: str):
        """Add documents from a directory to the index"""
        if not self._initialized:
            raise RuntimeError("LlamaService not initialized")
        
        await load_documents_to_index(documents_path, self._index)

    async def add_document_to_index(self, content: str, metadata: Dict[str, Any]):
        """Add a single document to the index with metadata"""
        if not self._initialized:
            raise RuntimeError("LlamaService not initialized")
        
        try:
            from llama_index.core import Document
            
            # Create a document with the content and metadata
            document = Document(text=content, metadata=metadata)
            
            # Add to the index
            self._index.insert(document)
            
            logger.info(f"Successfully added document to index with metadata: {metadata.get('document_id', 'unknown')}")
            
        except Exception as e:
            logger.error(f"Failed to add document to index: {e}")
            raise

    def create_query_engine(self, **kwargs):
        """Create a query engine with custom parameters"""
        if not self._initialized:
            raise RuntimeError("LlamaService not initialized")
        
        return create_query_engine(self._index, **kwargs)

    async def query(self, query_text: str, **engine_kwargs):
        """Execute a query against the index"""
        if not self._initialized:
            raise RuntimeError("LlamaService not initialized")
        
        query_engine = self.create_query_engine(**engine_kwargs)
        response = query_engine.query(query_text)
        return response

    async def cleanup(self):
        """Cleanup resources"""
        if self._vector_store:
            # Perform any necessary cleanup
            pass
        self._initialized = False
        logger.info("LlamaService cleanup completed")

    async def analyze_medical_data(self, prompt: str, patient_code: str, analysis_type: str) -> Dict[str, Any]:
        """
        Analyze medical data and return structured results
        """
        try:
            # Your existing LlamaIndex query logic here
            response = await self.query_engine.aquery(prompt)
            
            # Parse the response to extract structured data
            # This is a simplified example - you'll need to implement proper parsing
            analysis_result = {
                'id': uuid4(),
                'abnormal_flags': self._extract_abnormal_flags(str(response)),
                'diagnostic_insights': self._extract_diagnostic_insights(str(response)),
                'summary': self._extract_summary(str(response)),
                'confidence': 0.8,  # You can implement confidence scoring
                'recommendations': self._extract_recommendations(str(response)),
                'created_at': datetime.now()
            }
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error in medical data analysis: {str(e)}")
            raise

    def _extract_abnormal_flags(self, response_text: str) -> List[AbnormalFlag]:
        """Extract abnormal flags from AI response"""
        # Implement parsing logic to extract structured abnormal flags
        # This could use regex, NLP, or structured prompting
        return []  # Return empty list for now

    def _extract_diagnostic_insights(self, response_text: str) -> List[Dict[str, Any]]:
        """Extract diagnostic insights from AI response"""
        insights = []
        
        # Simple keyword-based extraction for now
        if "normal" in response_text.lower():
            insights.append({
                "category": "general",
                "insight": "Values appear to be within normal ranges",
                "confidence": 0.8,
                "type": "normal_finding"
            })
        
        if "abnormal" in response_text.lower() or "elevated" in response_text.lower():
            insights.append({
                "category": "abnormal_finding",
                "insight": "Some values may require attention",
                "confidence": 0.7,
                "type": "potential_concern"
            })
        
        # Enhanced medical terms for better coverage
        medical_terms = {
            # Lab values
            "cholesterol": "lipid_panel",
            "glucose": "metabolic_panel", 
            "hemoglobin": "hematology",
            "hematocrit": "hematology",
            "white blood cell": "hematology",
            "wbc": "hematology",
            "red blood cell": "hematology",
            "rbc": "hematology",
            "platelet": "hematology",
            "creatinine": "kidney_function",
            "bun": "kidney_function",
            "sodium": "electrolytes",
            "potassium": "electrolytes",
            "chloride": "electrolytes",
            "co2": "electrolytes",
            
            # Vital signs
            "blood pressure": "vital_signs",
            "heart rate": "vital_signs",
            "temperature": "vital_signs",
            "respiratory rate": "vital_signs",
            "oxygen saturation": "vital_signs",
            
            # Liver function
            "alt": "liver_function",
            "ast": "liver_function",
            "bilirubin": "liver_function",
            "alkaline phosphatase": "liver_function",
            
            # Cardiac markers
            "troponin": "cardiac_markers",
            "ck-mb": "cardiac_markers",
            "bnp": "cardiac_markers",
            "nt-probnp": "cardiac_markers",
            
            # Thyroid
            "tsh": "thyroid_function",
            "t3": "thyroid_function",
            "t4": "thyroid_function",
            
            # Inflammatory markers
            "esr": "inflammatory_markers",
            "crp": "inflammatory_markers",
            "c-reactive protein": "inflammatory_markers",
            
            # Coagulation
            "pt": "coagulation",
            "ptt": "coagulation",
            "inr": "coagulation",
            
            # Urinalysis
            "protein": "urinalysis",
            "ketones": "urinalysis",
            "specific gravity": "urinalysis",
            
            # Imaging
            "x-ray": "imaging",
            "ct scan": "imaging",
            "mri": "imaging",
            "ultrasound": "imaging",
            "echocardiogram": "imaging"
        }
        
        for term, category in medical_terms.items():
            if term in response_text.lower():
                insights.append({
                    "category": category,
                    "insight": f"Analysis includes {term} data",
                    "confidence": 0.9,
                    "type": "data_present",
                    "parameter": term
                })
        
        return insights

    def _extract_summary(self, response_text: str) -> str:
        """Extract summary from AI response"""
        # Implement parsing logic
        return "Analysis completed"  # Return default summary for now

    def _extract_recommendations(self, response_text: str) -> List[str]:
        """Extract recommendations from AI response"""
        # Implement parsing logic
        return []  # Return empty list for now

    async def query_patient_documents(self, patient_identifier_id: str, query: str) -> Dict[str, Any]:
        """Query documents for a specific patient"""
        try:
            if not self._initialized:
                raise Exception("LlamaService not initialized")
            
            logger.info(f"Querying patient documents for patient {patient_identifier_id}")
            
            # Create query engine
            query_engine = self.create_query_engine()
            
            # Query the index
            response = query_engine.query(query)
            
            # Filter source nodes to only include the specific patient
            patient_nodes = [
                node for node in response.source_nodes
                if node.metadata.get("patient_identifier_id") == str(patient_identifier_id)
            ]
            
            # Convert source nodes to serializable format
            source_documents = []
            for node in patient_nodes:
                source_documents.append({
                    "content": node.text,
                    "metadata": node.metadata,
                    "score": getattr(node, 'score', None)
                })
            
            # Extract diagnostic insights
            diagnostic_insights = self._extract_diagnostic_insights(str(response))
            
            return {
                "response": str(response),
                "source_nodes": source_documents,
                "diagnostic_insights": diagnostic_insights
            }
            
        except Exception as e:
            logger.error(f"Error querying patient documents: {str(e)}")
            raise Exception(f"Failed to query patient documents: {str(e)}")
# TODO calculate confidence score based on response quality
    async def suggest_medical_codes(
        self,
        prompt: str,
        clinical_notes: str,
        include_diagnoses: bool = True,
        include_procedures: bool = True,
        max_suggestions: int = 10
    ) -> Any:
        """
        Suggest ICD-10 and CPT codes based on clinical notes.
        
        Args:
            prompt: The analysis prompt
            clinical_notes: The clinical notes to analyze
            include_diagnoses: Whether to include ICD-10 diagnosis codes
            include_procedures: Whether to include CPT procedure codes
            max_suggestions: Maximum number of suggestions per code type
        
        Returns:
            Analysis result with suggested codes
        """
        try:
            # Enhanced prompt for medical coding
            enhanced_prompt = f"""
            {prompt}
            
            Additional Context:
            - Focus on the most relevant and specific codes
            - Prioritize primary diagnoses and main procedures
            - Consider comorbidities and complications
            - Ensure codes are current and valid
            - Provide rationale for high-confidence suggestions
            
            Clinical Notes Analysis:
            {clinical_notes}
            
            Please structure your response with clear sections for ICD-10 and CPT codes.
            Include specific code numbers and descriptions.
            
            Example format:
            ICD-10 Codes:
            - I21.19: ST elevation myocardial infarction involving other coronary artery of inferior wall
            - E11.9: Type 2 diabetes mellitus without complications
            
            CPT Codes:
            - 92928: Percutaneous transcatheter placement of intracoronary stent(s)
            - 93010: Electrocardiogram, routine ECG with at least 12 leads
            """
            
            # Use the existing query method instead of query_documents
            response = await self.query(enhanced_prompt)
            
            # Parse the response to extract structured code data
            parsed_result = self._parse_coding_response(
                str(response),
                include_diagnoses,
                include_procedures,
                max_suggestions
            )
            
            return parsed_result
            
        except Exception as e:
            logger.error(f"Error in suggest_medical_codes: {str(e)}")
            # Return a basic structure if parsing fails
            return type('obj', (object,), {
                'icd10_codes': [],
                'cpt_codes': [],
                'clinical_summary': f"Analysis completed with error: {str(e)}",
                'confidence_score': 0.3,
                'processing_notes': [f"Error occurred during analysis: {str(e)}"]
            })

    def _parse_coding_response(
        self,
        response_text: str,
        include_diagnoses: bool,
        include_procedures: bool,
        max_suggestions: int
    ) -> Any:
        """Parse AI response to extract structured coding data."""
        icd10_codes = []
        cpt_codes = []
        
        try:
            # Extract ICD-10 codes if requested
            if include_diagnoses:
                # Look for ICD-10 pattern: Letter followed by 2 digits, optional dot, more digits
                icd10_pattern = r'([A-Z]\d{2}\.?\d*)\s*[-:]?\s*([^\n\r]+?)(?=\n|$|[A-Z]\d{2}\.?\d*|\d{5})'
                icd10_matches = re.findall(icd10_pattern, response_text, re.IGNORECASE | re.MULTILINE)
                
                for i, (code, description) in enumerate(icd10_matches[:max_suggestions]):
                    confidence = max(0.9 - (i * 0.1), 0.5)  # Decreasing confidence
                    category = "primary" if i == 0 else "secondary"
                    
                    icd10_codes.append({
                        'code': code.upper().strip(),
                        'description': description.strip(),
                        'confidence': confidence,
                        'category': category
                    })
            
            # Extract CPT codes if requested
            if include_procedures:
                # Look for CPT pattern: 5 digits
                cpt_pattern = r'(\d{5})\s*[-:]?\s*([^\n\r]+?)(?=\n|$|[A-Z]\d{2}\.?\d*|\d{5})'
                cpt_matches = re.findall(cpt_pattern, response_text, re.MULTILINE)
                
                for i, (code, description) in enumerate(cpt_matches[:max_suggestions]):
                    confidence = max(0.85 - (i * 0.1), 0.5)  # Decreasing confidence
                    
                    cpt_codes.append({
                        'code': code.strip(),
                        'description': description.strip(),
                        'confidence': confidence,
                        'category': "procedure"
                    })
            
            # Extract clinical summary
            summary_lines = []
            lines = response_text.split('\n')
            
            for line in lines:
                line = line.strip()
                # Skip lines that look like codes or headers
                if (line and 
                    not re.match(r'^[A-Z]\d{2}\.?\d*', line) and 
                    not re.match(r'^\d{5}', line) and
                    not line.startswith(('ICD', 'CPT', 'Code:', 'Confidence:')) and
                    len(line) > 20 and 
                    '.' in line):
                    summary_lines.append(line)
            
            clinical_summary = ' '.join(summary_lines[:3]) if summary_lines else "Medical coding analysis completed based on clinical notes."
            
            # Calculate overall confidence
            all_suggestions = icd10_codes + cpt_codes
            if all_suggestions:
                avg_confidence = sum(code['confidence'] for code in all_suggestions) / len(all_suggestions)
                confidence_score = min(avg_confidence + 0.1, 1.0) if len(all_suggestions) >= 3 else avg_confidence
            else:
                confidence_score = 0.5
            
            # Generate processing notes
            processing_notes = []
            if icd10_codes:
                processing_notes.append(f"Found {len(icd10_codes)} ICD-10 diagnosis codes")
            if cpt_codes:
                processing_notes.append(f"Found {len(cpt_codes)} CPT procedure codes")
            if not icd10_codes and not cpt_codes:
                processing_notes.append("No specific medical codes identified in the clinical notes")
            
            return type('obj', (object,), {
                'icd10_codes': icd10_codes,
                'cpt_codes': cpt_codes,
                'clinical_summary': clinical_summary,
                'confidence_score': confidence_score,
                'processing_notes': processing_notes
            })
            
        except Exception as e:
            logger.error(f"Error parsing coding response: {str(e)}")
            return type('obj', (object,), {
                'icd10_codes': [],
                'cpt_codes': [],
                'clinical_summary': "Error parsing medical codes from analysis",
                'confidence_score': 0.3,
                'processing_notes': [f"Parsing error: {str(e)}"]
            })