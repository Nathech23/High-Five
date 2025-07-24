from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # LLM Configuration
    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "mistral:7b"
    llm_temperature: float = 0.3
    llm_max_tokens: int = 2048
    llm_context_window: int = 4096
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl: int = 3600
    
    # API Configuration
    api_v1_str: str = "/api/v1"
    project_name: str = "Service LLM Medical"
    debug: bool = True
    log_level: str = "INFO"
    
    # Security
    secret_key: str = "your-secret-key-here"
    access_token_expire_minutes: int = 30
    
    # Rate Limiting
    rate_limit_per_minute: int = 60
    max_concurrent_requests: int = 10
    
    # Medical Safety
    max_response_length: int = 1500
    require_medical_disclaimer: bool = True
    enable_safety_filters: bool = True
    
    class Config:
        env_file = ".env"

settings = Settings()
