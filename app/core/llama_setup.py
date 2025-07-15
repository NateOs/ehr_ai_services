from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings, StorageContext
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from app.core.config import settings
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

async def setup_llama_index_with_ollama():
    """
    Setup LlamaIndex with Ollama LLM and embeddings, PostgreSQL vector store, and document loading
    """
    try:
        logger.info("Setting up LlamaIndex with Ollama...")
        
        # Configure Ollama LLM and embeddings
        Settings.llm = Ollama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            request_timeout=120.0
        )
        
        Settings.embed_model = OllamaEmbedding(
            model_name=settings.OLLAMA_EMBEDDING_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            ollama_additional_kwargs={"mirostat": 0}
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
    """
    Load new documents into an existing index
    """
    try:
        documents_path = Path(documents_path)
        if not documents_path.exists():
            raise FileNotFoundError(f"Documents path {documents_path} does not exist")
        
        logger.info(f"Loading documents from {documents_path}")
        documents = SimpleDirectoryReader(
            input_dir=str(documents_path),
            recursive=True,
            required_exts=[".pdf", ".txt", ".docx", ".md", ".csv", ".html"]
        ).load_data()
        
        if documents:
            # Insert documents into existing index
            for doc in documents:
                index.insert(doc)
            logger.info(f"Successfully loaded {len(documents)} documents into index")
        else:
            logger.warning("No documents found to load")
            
    except Exception as e:
        logger.error(f"Failed to load documents: {e}")
        raise

def create_query_engine(index: VectorStoreIndex, **kwargs):
    """
    Create a query engine with customizable parameters
    """
    default_params = {
        "response_mode": "tree_summarize",
        "verbose": True,
        "similarity_top_k": 5,
        "streaming": False
    }
    
    # Update with any provided kwargs
    default_params.update(kwargs)
    
    return index.as_query_engine(**default_params)