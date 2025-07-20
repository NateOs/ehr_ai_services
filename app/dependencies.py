from app.services.llama_service import LlamaService
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings, StorageContext
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from app.core.config import settings
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Global variable to store LlamaService instance
llama_service = None

def get_llama_service() -> LlamaService:
    """Get the global LlamaService instance"""
    global llama_service
    if llama_service is None:
        raise RuntimeError("LlamaService not initialized")
    return llama_service

def set_llama_service(service: LlamaService):
    """Set the global LlamaService instance"""
    global llama_service
    llama_service = service

async def setup_llama_index_with_openai():
    """
    Setup LlamaIndex with OpenAI LLM and embeddings, PostgreSQL vector store, and document loading
    """
    try:
        logger.info("Setting up LlamaIndex with OpenAI...")
        
        # Configure OpenAI LLM and embeddings
        Settings.llm = OpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.1,
            max_tokens=1000
        )
        
        Settings.embed_model = OpenAIEmbedding(
            model=settings.EMBEDDING_MODEL,
            api_key=settings.OPENAI_API_KEY
        )
        
        # Setup PostgreSQL vector store
        vector_store = PGVectorStore.from_params(
            database=settings.POSTGRES_DB,
            host=settings.POSTGRES_SERVER,
            password=settings.POSTGRES_PASSWORD,
            port=settings.POSTGRES_PORT,
            user=settings.POSTGRES_USER,
            table_name=settings.EMBEDDINGS_TABLE_NAME,
            embed_dim=settings.VECTOR_DIMENSION,
        )
        
        # Create storage context
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        # Load documents from the documents directory
        documents_path = Path(settings.DOCUMENTS_PATH)
        if documents_path.exists() and any(documents_path.iterdir()):
            logger.info(f"Loading documents from {documents_path}")
            documents = SimpleDirectoryReader(
                input_dir=str(documents_path),
                recursive=True,
                required_exts=[".pdf", ".txt", ".docx", ".md", ".csv", ".html"]
            ).load_data()
            
            logger.info(f"Loaded {len(documents)} documents")
            
            # Create or load index
            index = VectorStoreIndex.from_documents(
                documents,
                storage_context=storage_context,
                show_progress=True
            )
        else:
            logger.info("No documents found, creating empty index")
            # Create empty index
            index = VectorStoreIndex.from_documents(
                [],
                storage_context=storage_context
            )
        
        logger.info("LlamaIndex setup completed successfully")
        return index, vector_store
        
    except Exception as e:
        logger.error(f"Failed to setup LlamaIndex: {e}")
        raise

async def load_documents_to_index(documents_path: str, index: VectorStoreIndex):
    """Load documents from a directory into the existing index"""
    try:
        logger.info(f"Loading documents from {documents_path}")
        documents = SimpleDirectoryReader(
            input_dir=documents_path,
            recursive=True,
            required_exts=[".pdf", ".txt", ".docx", ".md", ".csv", ".html"]
        ).load_data()
        
        if documents:
            for doc in documents:
                index.insert(doc)
            logger.info(f"Successfully loaded {len(documents)} documents to index")
        else:
            logger.warning("No documents found to load")
            
    except Exception as e:
        logger.error(f"Failed to load documents to index: {e}")
        raise

def create_query_engine(index: VectorStoreIndex, **kwargs):
    """Create a query engine with default parameters"""
    default_params = {
        "response_mode": "tree_summarize",
        "verbose": True,
        "similarity_top_k": 5
    }
    default_params.update(kwargs)
    return index.as_query_engine(**default_params)