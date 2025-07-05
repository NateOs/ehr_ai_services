from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
import logging
import asyncio
from app.core.config import settings

logger = logging.getLogger(__name__)

class LlamaService:
    def __init__(self):
        self._index = None
        self._vector_store = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize LlamaIndex with PostgreSQL vector store"""
        if self._initialized:
            return
            
        try:
            # Configure embeddings and LLM
            Settings.embed_model = OpenAIEmbedding(
                model=settings.EMBEDDING_MODEL,
                api_key=settings.OPENAI_API_KEY
            )
            Settings.llm = OpenAI(
                model=settings.LLM_MODEL,
                api_key=settings.OPENAI_API_KEY
            )
            
            # Setup vector store
            self._vector_store = PGVectorStore.from_params(
                database=settings.POSTGRES_DB,
                host=settings.POSTGRES_SERVER,
                password=settings.POSTGRES_PASSWORD,
                port=settings.POSTGRES_PORT,
                user=settings.POSTGRES_USER,
                table_name="embeddings",
                embed_dim=settings.VECTOR_DIMENSION,
            )
            
            self._index = VectorStoreIndex.from_vector_store(self._vector_store)
            self._initialized = True
            logger.info("LlamaIndex initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize LlamaIndex: {e}")
            raise
    
    async def is_ready(self) -> bool:
        """Check if LlamaIndex is ready"""
        return self._initialized and self._index is not None
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            # Add any cleanup logic here
            self._initialized = False
            logger.info("LlamaService cleanup completed")
        except Exception as e:
            logger.error(f"Error during LlamaService cleanup: {e}")
    
    def get_index(self):
        """Get the vector store index"""
        if not self._initialized:
            raise RuntimeError("LlamaService not initialized")
        return self._index
    
    def get_vector_store(self):
        """Get the vector store"""
        if not self._initialized:
            raise RuntimeError("LlamaService not initialized")
        return self._vector_store