from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.vector_stores.postgres import PGVectorStore
from app.core.llama_setup import setup_llama_index_with_openai, create_query_engine, load_documents_to_index
from app.models.models import AbnormalFlag, DiagnosticInsight  # Add this import
import logging
from typing import Dict, Any, List
from uuid import uuid4
from datetime import datetime

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

    def _extract_diagnostic_insights(self, response_text: str) -> List[DiagnosticInsight]:
        """Extract diagnostic insights from AI response"""
        # Implement parsing logic
        return []  # Return empty list for now

    def _extract_summary(self, response_text: str) -> str:
        """Extract summary from AI response"""
        # Implement parsing logic
        return "Analysis completed"  # Return default summary for now

    def _extract_recommendations(self, response_text: str) -> List[str]:
        """Extract recommendations from AI response"""
        # Implement parsing logic
        return []  # Return empty list for now