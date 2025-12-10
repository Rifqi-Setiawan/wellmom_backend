from fastapi import FastAPI, Depends
from sqlalchemy import text  # ✅ ADD THIS
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db, engine

# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    debug=settings.DEBUG
)

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