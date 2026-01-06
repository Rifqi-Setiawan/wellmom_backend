"""File upload handler for WellMom VPS storage"""
import os
import uuid
from pathlib import Path
from fastapi import UploadFile, HTTPException
from app.config import settings

# Allowed file types
ALLOWED_IMAGES = {".jpg", ".jpeg", ".png"}
ALLOWED_DOCUMENTS = {".pdf", ".jpg", ".jpeg", ".png"}

# Upload paths mapping
UPLOAD_PATHS = {
    # Documents
    "puskesmas_sk": "documents/puskesmas/sk_pendirian",
    "puskesmas_npwp": "documents/puskesmas/npwp",
    "perawat_str": "documents/perawat/str",
    
    # Photos
    "puskesmas_photo": "photos/puskesmas",
    "perawat_profile": "photos/profiles/perawat",
    "ibu_hamil_profile": "photos/profiles/ibu_hamil",
}

def validate_file(upload_file: UploadFile, file_type: str) -> None:
    """Validate file type and size"""
    upload_file.file.seek(0, 2)
    file_size = upload_file.file.tell()
    upload_file.file.seek(0)
    
    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413, 
            detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE / 1024 / 1024}MB"
        )
    
    file_ext = Path(upload_file.filename).suffix.lower()
    
    if file_type == "document":
        if file_ext not in ALLOWED_DOCUMENTS:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid document type. Allowed: {', '.join(ALLOWED_DOCUMENTS)}"
            )
    elif file_type == "image":
        if file_ext not in ALLOWED_IMAGES:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid image type. Allowed: {', '.join(ALLOWED_IMAGES)}"
            )

def save_upload_file(upload_file: UploadFile, upload_type: str) -> str:
    """Save uploaded file to VPS local storage"""
    if upload_type not in UPLOAD_PATHS:
        raise HTTPException(status_code=400, detail=f"Invalid upload type: {upload_type}")
    
    file_type = "document" if "documents" in UPLOAD_PATHS[upload_type] else "image"
    validate_file(upload_file, file_type)
    
    file_ext = Path(upload_file.filename).suffix.lower()
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    
    subfolder = UPLOAD_PATHS[upload_type]
    upload_path = Path(settings.UPLOAD_DIR) / subfolder
    upload_path.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_path / unique_filename
    
    with open(file_path, "wb") as f:
        content = upload_file.file.read()
        f.write(content)
    
    return f"/uploads/{subfolder}/{unique_filename}"

def delete_file(file_path: str) -> bool:
    """Delete file from VPS storage"""
    try:
        if not file_path:
            return False
            
        full_path = Path(settings.UPLOAD_DIR).parent / file_path.lstrip("/")
        
        if full_path.exists():
            full_path.unlink()
            return True
        return False
    except Exception as e:
        print(f"Error deleting file {file_path}: {e}")
        return False

def get_file_url(file_path: str) -> str:
    """Get public URL for file"""
    if not file_path:
        return None
    
    if not file_path.startswith("/"):
        file_path = f"/{file_path}"
    
    return f"{settings.FRONTEND_BASE_URL}{file_path}"