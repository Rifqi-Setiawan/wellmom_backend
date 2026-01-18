from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text  
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db, engine
from app.api.v1.api import api_router
from pathlib import Path

# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    debug=settings.DEBUG,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Configuration
# When allow_credentials=True, cannot use allow_origins=["*"]
# Must specify explicit origins
cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
    expose_headers=["Content-Length", "Content-Type"],
)

upload_dir = Path(settings.UPLOAD_DIR)
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")

# Include versioned API router
app.include_router(api_router)

# Root endpoint
@app.get("/")
def read_root():
    """Hello World endpoint"""
    return {
        "message": "Welcome to WellMom API",
        "version": settings.API_VERSION,
        "status": "running"
    }

# Health check endpoint
@app.get("/health")
def health_check():
    """API health check"""
    return {"status": "healthy"}

# Database test endpoint
@app.get("/db-test")
def test_database(db: Session = Depends(get_db)):
    """Test database connection"""
    try:
        # Execute simple query
        db.execute(text("SELECT 1"))  # ✅ WRAPPED WITH text()
        return {
            "status": "success",
            "message": "Database connection successful",
            "database": "wellmom"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# PostGIS test endpoint
@app.get("/postgis-test")
def test_postgis(db: Session = Depends(get_db)):
    """Test PostGIS extension"""
    try:
        result = db.execute(text("SELECT PostGIS_Version()")).fetchone()  # ✅ WRAPPED WITH text()
        return {
            "status": "success",
            "message": "PostGIS is working",
            "version": result[0]
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }