from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./receipt_processing.db")

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-jwt-secret-key-here")
    ALGORITHM: str = 'HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Google OAuth2
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI: str = None  # Will be constructed from FRONTEND_URL
    
    @property
    def google_redirect_uri(self) -> str:
        """Construct Google redirect URI from frontend URL"""
        if self.GOOGLE_REDIRECT_URI:
            return self.GOOGLE_REDIRECT_URI
        return f"{self.FRONTEND_URL}/auth/callback"

    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Email polling settings (for development only)
    EMAIL_POLL_INTERVAL: int = 30
    MAX_EMAILS_PER_POLL: int = 10

    # File upload settings
    MAX_FILE_SIZE: int = 10485760
    UPLOAD_DIR: str = './uploads'
     
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Receipt Processing API"
    
    # Backend URL Configuration
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8005")
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8005
    
    # Frontend URL
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    # Debug mode
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

settings = Settings()
