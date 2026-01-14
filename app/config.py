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
    
    # CORS - Allowed origins (comma-separated)
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001,http://103.191.92.29,https://103.191.92.29"
    
    # Gemini AI Chatbot
    GEMINI_API_KEY: str = ""
    CHATBOT_USER_DAILY_TOKEN_LIMIT: int = 10000      # Per user per day
    CHATBOT_GLOBAL_DAILY_TOKEN_LIMIT: int = 500000     # Total all users per day
    CHATBOT_RATE_LIMIT_PER_MINUTE: int = 10            # Max requests per user per minute
    CHATBOT_REQUEST_TIMEOUT: int = 30                  # Seconds
    CHATBOT_MAX_HISTORY_MESSAGES: int = 20             # Messages to include for context
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"

settings = Settings()