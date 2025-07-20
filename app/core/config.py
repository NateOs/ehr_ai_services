from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "EHR AI Services"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Database
    POSTGRES_SERVER: str = "postgres"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "ehr_ai_db"
    POSTGRES_PORT: int = 5432
    
    # CORS
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # LlamaIndex - Updated to use OpenAI
    OPENAI_API_KEY: Optional[str] = None
    EMBEDDINGS_TABLE_NAME: str = "data_embeddings"  # Make sure this matches your SQL
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    LLM_MODEL: str = "gpt-4o-mini"
    
    AI_SYSTEM_PROMPT: str = """You are an AI medical expert. You will be given a question about a medical document.
    Respond with the necessary information from the document, and if possible, provide a summary."""
    
    # Vector Store - Updated for OpenAI embeddings
    VECTOR_DIMENSION: int = int(os.getenv("VECTOR_DIMENSION", "1536"))  # text-embedding-3-small dimension
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # File Upload
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_DIR: str = "data/uploads"
    PROCESSED_DIR: str = "data/processed"
    TEMP_DIR: str = "data/temp"
    
    # Document Processing
    DOCUMENTS_PATH: str = "./documents"
    
    @property
    def database_url(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    class Config:
        env_file = ".env"

settings = Settings()