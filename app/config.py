from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    DATABASE_URL: str
    
    # API
    API_TITLE: str = "WellMom API"
    API_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Security
    SECRET_KEY: str
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()