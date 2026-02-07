"""
Configuration management for the Campaign Calls microservice.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/campaign_calls"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Application
    default_max_concurrent_calls: int = 10
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Mock Telephony
    mock_call_duration_min: int = 5
    mock_call_duration_max: int = 30
    mock_call_failure_rate: float = 0.2
    
    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
