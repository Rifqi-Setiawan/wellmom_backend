from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text  # ✅ ADD THIS
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db, engine
from app.api.v1.api import api_router

# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    debug=settings.DEBUG,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS (development: allow all)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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