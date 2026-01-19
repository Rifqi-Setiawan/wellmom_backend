"""File upload handler for WellMom VPS storage with security best practices"""
import os
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Set
from fastapi import UploadFile, HTTPException, status
from app.config import settings

# Setup logging
logger = logging.getLogger(__name__)

# ============================================
# FILE TYPE DEFINITIONS WITH MIME VALIDATION
# ============================================

# Magic bytes signatures for file type validation
MAGIC_BYTES = {
    # PDF: %PDF
    "pdf": [b"%PDF"],
    # JPEG: FFD8FF
    "jpeg": [b"\xff\xd8\xff"],
    # PNG: 89504E47
    "png": [b"\x89PNG\r\n\x1a\n"],
    # GIF: GIF87a or GIF89a
    "gif": [b"GIF87a", b"GIF89a"],
}

# Extension to magic type mapping
EXTENSION_TO_TYPE = {
    ".pdf": "pdf",
    ".jpg": "jpeg",
    ".jpeg": "jpeg",
    ".png": "png",
    ".gif": "gif",
}

# Allowed file types per category
ALLOWED_IMAGES: Set[str] = {".jpg", ".jpeg", ".png"}
ALLOWED_DOCUMENTS: Set[str] = {".pdf", ".jpg", ".jpeg", ".png"}
ALLOWED_PHOTO_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".gif"}

# Size limits
MAX_DOCUMENT_SIZE_MB = 2
MAX_PHOTO_SIZE_MB = 5
MAX_UPLOAD_SIZE = settings.MAX_UPLOAD_SIZE  # From config (2MB default)

# Upload paths mapping (relative to UPLOAD_DIR)
UPLOAD_PATHS = {
    # Documents
    "puskesmas_sk": "documents/puskesmas/sk_pendirian",
    "puskesmas_npwp": "documents/puskesmas/npwp",
    "perawat_str": "documents/perawat/str",

    # Photos
    "puskesmas_photo": "photos/puskesmas",
    "perawat_profile": "photos/profiles/perawat",
    "ibu_hamil_profile": "photos/profiles/ibu_hamil",

    # Profile photos (consistent path)
    "profile_photos": "photos/profiles",
}

# Upload type to allowed extensions mapping
UPLOAD_TYPE_ALLOWED_EXTENSIONS = {
    "puskesmas_sk": {".pdf"},
    "puskesmas_npwp": {".pdf", ".jpg", ".jpeg"},
    "perawat_str": {".pdf", ".jpg", ".jpeg"},
    "puskesmas_photo": {".jpg", ".jpeg", ".png"},
    "perawat_profile": {".jpg", ".jpeg", ".png"},
    "ibu_hamil_profile": {".jpg", ".jpeg", ".png"},
    "profile_photos": {".jpg", ".jpeg", ".png", ".gif"},
}


# ============================================
# SECURITY VALIDATION FUNCTIONS
# ============================================

def validate_magic_bytes(file_content: bytes, expected_type: str) -> bool:
    """
    Validate file content by checking magic bytes (file signature).
    This prevents attackers from uploading malicious files with fake extensions.

    Args:
        file_content: First few bytes of the file
        expected_type: Expected file type (pdf, jpeg, png, gif)

    Returns:
        True if magic bytes match expected type
    """
    if expected_type not in MAGIC_BYTES:
        return False

    signatures = MAGIC_BYTES[expected_type]
    for signature in signatures:
        if file_content.startswith(signature):
            return True

    return False


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal and other attacks.

    Args:
        filename: Original filename from upload

    Returns:
        Sanitized filename (only alphanumeric, dash, underscore, and dot)
    """
    if not filename:
        return "unnamed"

    # Get only the basename (remove any path components)
    basename = Path(filename).name

    # Remove or replace potentially dangerous characters
    safe_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")
    sanitized = "".join(c if c in safe_chars else "_" for c in basename)

    # Ensure it doesn't start with a dot (hidden file)
    while sanitized.startswith("."):
        sanitized = sanitized[1:]

    return sanitized if sanitized else "unnamed"


def validate_path_safety(file_path: str) -> bool:
    """
    Validate that file path doesn't contain path traversal attempts.

    Args:
        file_path: File path to validate

    Returns:
        True if path is safe
    """
    if not file_path:
        return False

    # Check for path traversal patterns
    dangerous_patterns = ["..", "~", "//", "\\"]
    for pattern in dangerous_patterns:
        if pattern in file_path:
            logger.warning(f"Path traversal attempt detected: {file_path}")
            return False

    # Ensure path doesn't start with absolute path markers
    if file_path.startswith("/") and not file_path.startswith("/uploads"):
        return False

    return True


def get_file_extension(filename: str) -> str:
    """Safely get file extension in lowercase."""
    if not filename:
        return ""
    return Path(filename).suffix.lower()


# ============================================
# MAIN VALIDATION FUNCTION
# ============================================

def validate_upload_file(
    upload_file: UploadFile,
    upload_type: str,
    max_size_bytes: Optional[int] = None
) -> Tuple[bytes, str]:
    """
    Comprehensive file validation with security checks.

    Args:
        upload_file: FastAPI UploadFile object
        upload_type: Type of upload (e.g., 'puskesmas_sk', 'perawat_profile')
        max_size_bytes: Optional custom max size, defaults to MAX_UPLOAD_SIZE

    Returns:
        Tuple of (file_content, file_extension)

    Raises:
        HTTPException: If validation fails
    """
    if not upload_file or not upload_file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File tidak valid atau tidak ada"
        )

    # Get allowed extensions for this upload type
    allowed_extensions = UPLOAD_TYPE_ALLOWED_EXTENSIONS.get(upload_type)
    if not allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipe upload tidak valid: {upload_type}"
        )

    # Sanitize and validate filename
    original_filename = sanitize_filename(upload_file.filename)
    file_ext = get_file_extension(original_filename)

    # Check extension
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipe file tidak diizinkan. Format yang diterima: {', '.join(allowed_extensions)}"
        )

    # Read file content
    upload_file.file.seek(0)
    file_content = upload_file.file.read()
    upload_file.file.seek(0)  # Reset for potential re-read

    # Validate file size
    max_size = max_size_bytes or MAX_UPLOAD_SIZE
    if len(file_content) > max_size:
        size_mb = max_size / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File terlalu besar. Maksimal: {size_mb:.1f}MB"
        )

    # Validate file is not empty
    if len(file_content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File kosong tidak diizinkan"
        )

    # Validate magic bytes (content type verification)
    expected_type = EXTENSION_TO_TYPE.get(file_ext)
    if expected_type and not validate_magic_bytes(file_content, expected_type):
        logger.warning(
            f"Magic bytes mismatch - filename: {original_filename}, "
            f"expected_type: {expected_type}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Konten file tidak sesuai dengan ekstensi. File mungkin rusak atau tidak valid."
        )

    logger.info(f"File validated successfully: type={upload_type}, size={len(file_content)} bytes")

    return file_content, file_ext


# ============================================
# FILE STORAGE FUNCTIONS
# ============================================

def save_upload_file(upload_file: UploadFile, upload_type: str) -> str:
    """
    Save uploaded file to VPS local storage with security validation.

    Args:
        upload_file: FastAPI UploadFile object
        upload_type: Type of upload (determines storage path and allowed types)

    Returns:
        str: Relative URL path (e.g., /uploads/documents/puskesmas/sk_pendirian/uuid.pdf)

    Raises:
        HTTPException: If validation or save fails
    """
    if upload_type not in UPLOAD_PATHS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipe upload tidak valid: {upload_type}"
        )

    # Validate file (includes magic bytes check)
    file_content, file_ext = validate_upload_file(upload_file, upload_type)

    # Generate unique filename with UUID
    unique_filename = f"{uuid.uuid4()}{file_ext}"

    # Get subfolder path
    subfolder = UPLOAD_PATHS[upload_type]
    upload_path = Path(settings.UPLOAD_DIR) / subfolder

    # Create directory if not exists
    upload_path.mkdir(parents=True, exist_ok=True)

    file_path = upload_path / unique_filename

    # Save file
    try:
        with open(file_path, "wb") as f:
            f.write(file_content)

        logger.info(f"File saved: {file_path}")

        # Return relative URL path
        return f"/uploads/{subfolder}/{unique_filename}"

    except IOError as e:
        logger.error(f"Failed to save file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal menyimpan file. Silakan coba lagi."
        )


def delete_file(file_path: str) -> bool:
    """
    Safely delete file from VPS storage with path traversal protection.

    Args:
        file_path: Relative path to file (e.g., /uploads/documents/...)

    Returns:
        True if file was deleted, False otherwise
    """
    try:
        if not file_path:
            return False

        # Validate path safety
        if not validate_path_safety(file_path):
            logger.warning(f"Unsafe file path rejected: {file_path}")
            return False

        # Normalize path - handle both /uploads/... and uploads/... formats
        clean_path = file_path.lstrip("/")
        if clean_path.startswith("uploads/"):
            clean_path = clean_path[8:]  # Remove "uploads/"

        # Construct full path
        full_path = Path(settings.UPLOAD_DIR) / clean_path

        # Resolve to absolute path and verify it's within UPLOAD_DIR
        resolved_path = full_path.resolve()
        upload_dir_resolved = Path(settings.UPLOAD_DIR).resolve()

        # Security check: ensure file is within upload directory
        if not str(resolved_path).startswith(str(upload_dir_resolved)):
            logger.warning(f"Path traversal blocked: {file_path} -> {resolved_path}")
            return False

        # Delete file if exists
        if resolved_path.exists() and resolved_path.is_file():
            resolved_path.unlink()
            logger.info(f"File deleted: {resolved_path}")
            return True

        return False

    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {e}")
        return False


def get_file_url(file_path: str) -> Optional[str]:
    """
    Get public URL for file.

    Args:
        file_path: Relative path like /uploads/documents/... or just the stored path

    Returns:
        Full URL like http://103.191.92.29/uploads/documents/...
    """
    if not file_path:
        return None

    # Ensure path starts with /uploads
    if not file_path.startswith("/uploads"):
        if file_path.startswith("uploads/"):
            file_path = f"/{file_path}"
        elif file_path.startswith("/"):
            file_path = f"/uploads{file_path}"
        else:
            file_path = f"/uploads/{file_path}"

    return f"{settings.FRONTEND_BASE_URL.rstrip('/')}{file_path}"


# ============================================
# PROFILE PHOTO FUNCTIONS
# ============================================

def ensure_upload_dir(subdir: str = "") -> Path:
    """Ensure upload directory exists and return the path."""
    if subdir:
        dir_path = Path(settings.UPLOAD_DIR) / subdir
    else:
        dir_path = Path(settings.UPLOAD_DIR)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def validate_photo_file(file: UploadFile) -> Tuple[bool, Optional[str]]:
    """
    Validate uploaded photo file.

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not file or not file.filename:
        return False, "File tidak valid"

    file_ext = get_file_extension(file.filename)
    if file_ext not in ALLOWED_PHOTO_EXTENSIONS:
        return False, f"Tipe file tidak diizinkan. Format yang diterima: {', '.join(ALLOWED_PHOTO_EXTENSIONS)}"

    return True, None


async def save_profile_photo(
    file: UploadFile,
    entity_type: str,
    entity_id: int
) -> Optional[str]:
    """
    Save profile photo with validation and return file path.

    Args:
        file: UploadFile object
        entity_type: "perawat" or "ibu_hamil"
        entity_id: ID of the perawat or ibu_hamil

    Returns:
        Relative URL path (e.g., /uploads/photos/profiles/perawat/perawat_1_20250118_123456.jpg)

    Raises:
        ValueError: If validation fails
    """
    # Validate entity type
    if entity_type not in ["perawat", "ibu_hamil"]:
        raise ValueError(f"Tipe entity tidak valid: {entity_type}")

    # Basic validation
    is_valid, error = validate_photo_file(file)
    if not is_valid:
        raise ValueError(error)

    # Read and validate content
    file_content = await file.read()

    # Check file size
    size_mb = len(file_content) / (1024 * 1024)
    if size_mb > MAX_PHOTO_SIZE_MB:
        raise ValueError(f"File terlalu besar. Maksimal: {MAX_PHOTO_SIZE_MB}MB")

    # Validate magic bytes
    file_ext = get_file_extension(file.filename)
    expected_type = EXTENSION_TO_TYPE.get(file_ext)
    if expected_type and not validate_magic_bytes(file_content, expected_type):
        raise ValueError("Konten file tidak sesuai dengan ekstensi")

    # Create directory
    subdir = f"photos/profiles/{entity_type}"
    ensure_upload_dir(subdir)

    # Generate filename: type_id_timestamp.ext
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{entity_type}_{entity_id}_{timestamp}{file_ext}"

    filepath = Path(settings.UPLOAD_DIR) / subdir / filename

    # Save file
    try:
        with open(filepath, "wb") as f:
            f.write(file_content)

        logger.info(f"Profile photo saved: {filepath}")

        # Return relative URL path
        return f"/uploads/{subdir}/{filename}"

    except IOError as e:
        logger.error(f"Failed to save profile photo: {e}")
        raise ValueError(f"Gagal menyimpan file: {str(e)}")


# ============================================
# LEGACY COMPATIBILITY FUNCTION
# ============================================

def validate_file(upload_file: UploadFile, file_type: str) -> None:
    """
    Legacy validation function - kept for backward compatibility.
    Use validate_upload_file() for new code.
    """
    upload_file.file.seek(0, 2)
    file_size = upload_file.file.tell()
    upload_file.file.seek(0)

    if file_size > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File terlalu besar. Maksimal: {MAX_UPLOAD_SIZE / 1024 / 1024}MB"
        )

    file_ext = get_file_extension(upload_file.filename)

    if file_type == "document":
        if file_ext not in ALLOWED_DOCUMENTS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipe dokumen tidak valid. Format yang diterima: {', '.join(ALLOWED_DOCUMENTS)}"
            )
    elif file_type == "image":
        if file_ext not in ALLOWED_IMAGES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipe gambar tidak valid. Format yang diterima: {', '.join(ALLOWED_IMAGES)}"
            )
