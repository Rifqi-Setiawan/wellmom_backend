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

    # SMTP / Email (optional, required for email notifications)
    SMTP_HOST: str | None = None
    SMTP_PORT: int | None = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str | None = None
    SMTP_FROM_NAME: str = "WellMom"
    SMTP_USE_TLS: bool = True

    # Frontend base URL for activation links
    FRONTEND_BASE_URL: str = "https://app.wellmom.com"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()