"""File upload utilities for profile photos."""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from fastapi import UploadFile


ALLOWED_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}
MAX_PHOTO_SIZE_MB = 5
PROFILE_PHOTOS_DIR = "uploads/profile_photos"


def ensure_upload_dir() -> None:
    """Ensure upload directory exists."""
    Path(PROFILE_PHOTOS_DIR).mkdir(parents=True, exist_ok=True)


def validate_photo_file(file: UploadFile) -> Tuple[bool, Optional[str]]:
    """Validate uploaded photo file.
    
    Returns: (is_valid, error_message)
    """
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_PHOTO_EXTENSIONS:
        return False, f"File type not allowed. Allowed: {', '.join(ALLOWED_PHOTO_EXTENSIONS)}"
    
    # Check file size (approximate check via filename)
    # Note: More precise check should happen during actual file save
    return True, None


async def save_profile_photo(file: UploadFile, entity_type: str, entity_id: int) -> Optional[str]:
    """Save profile photo and return file path.
    
    Args:
        file: UploadFile object
        entity_type: "perawat" or "ibu_hamil"
        entity_id: ID of the perawat or ibu_hamil
    
    Returns:
        Relative file path or None if save failed
    """
    # Validate file
    is_valid, error = validate_photo_file(file)
    if not is_valid:
        raise ValueError(error)
    
    # Create directory if not exists
    ensure_upload_dir()
    
    # Generate filename: type_id_timestamp.ext
    file_ext = Path(file.filename).suffix.lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{entity_type}_{entity_id}_{timestamp}{file_ext}"
    filepath = os.path.join(PROFILE_PHOTOS_DIR, entity_type, filename)
    
    # Ensure subdirectory exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    # Save file
    try:
        contents = await file.read()
        
        # Check file size
        size_mb = len(contents) / (1024 * 1024)
        if size_mb > MAX_PHOTO_SIZE_MB:
            raise ValueError(f"File too large. Max size: {MAX_PHOTO_SIZE_MB}MB")
        
        with open(filepath, "wb") as f:
            f.write(contents)
        
        # Return relative path for storage
        return filepath.replace("\\", "/")
    except Exception as e:
        raise ValueError(f"Failed to save file: {str(e)}")
