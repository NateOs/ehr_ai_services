from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from app.core.config import settings
from app.core.llama_setup import setup_llama_index_with_ollama, create_query_engine, load_documents_to_index
import logging
import asyncio

logger = logging.getLogger(__name__)

class LlamaService:
    def __init__(self):
        self._index: VectorStoreIndex = None
        self._vector_store: PGVectorStore = None
        self._initialized = False

    async def initialize(self):
        """Initialize LlamaIndex with Ollama and PostgreSQL vector store"""
        if self._initialized:
            return
            
        try:
            logger.info("Initializing LlamaService with Ollama...")
            
            # Setup LlamaIndex with Ollama
            self._index, self._vector_store = await setup_llama_index_with_ollama()
            
            self._initialized = True
            logger.info("LlamaService initialized successfully with Ollama")
            
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
        response = await query_engine.aquery(query_text)
        return response

    async def cleanup(self):
        """Cleanup resources"""
        if self._vector_store:
            # Close any connections if needed
            pass
        
        self._initialized = False
        logger.info("LlamaService cleanup completed")
