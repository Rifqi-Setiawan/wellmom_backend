from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    DATABASE_URL: str
    DB_PASSWORD: str
    
    # API
    API_TITLE: str = "WellMom API"
    API_VERSION: str = "1.0.0"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = False
    
    # Security
    SECRET_KEY: str
    
    # MQTT
    MQTT_BROKER: str
    
    # File Upload (VPS local storage)
    UPLOAD_DIR: str = "/app/uploads"
    MAX_UPLOAD_SIZE: int = 2097152  # 2MB in bytes
    
    # SMTP / Email (optional)
    SMTP_HOST: str | None = None
    SMTP_PORT: int | None = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str | None = None
    SMTP_FROM_NAME: str = "WellMom"
    SMTP_USE_TLS: bool = True
    
    # Frontend base URL
    FRONTEND_BASE_URL: str = "http://103.191.92.29"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"

settings = Settings()