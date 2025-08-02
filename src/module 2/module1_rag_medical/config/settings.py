import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Configuration settings for RAG Medical Module"""
    
    # Project paths
    PROJECT_ROOT: Path = Path(__file__).parent.parent
    DOCUMENTS_PATH: Path = PROJECT_ROOT / "documents"
    EMBEDDINGS_PATH: Path = PROJECT_ROOT / "embeddings"
    
    # Database configurations
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "hopital_douala_medical"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "password"
    
    @property
    def postgres_url(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # Chroma configuration
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    CHROMA_COLLECTION_NAME: str = "medical_knowledge"
    CHROMA_PERSIST_DIRECTORY: str = str(PROJECT_ROOT / "embeddings" / "chroma_db")
    
    # Embedding model configuration
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DEVICE: str = "cpu"  # or "cuda" if GPU available
    EMBEDDING_BATCH_SIZE: int = 32
    
    # LangChain configuration
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    TOP_K_RETRIEVAL: int = 5
    
    # API configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8080
    API_TITLE: str = "Hôpital Général Douala - RAG Medical API"
    API_VERSION: str = "1.0.0"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = str(PROJECT_ROOT / "logs" / "medical_rag.log")
    
    # Security
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Global settings instance
settings = Settings()

# Create necessary directories
settings.DOCUMENTS_PATH.mkdir(parents=True, exist_ok=True)
settings.EMBEDDINGS_PATH.mkdir(parents=True, exist_ok=True)
(settings.PROJECT_ROOT / "logs").mkdir(parents=True, exist_ok=True)