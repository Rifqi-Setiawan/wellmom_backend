"""Upload endpoints for documents and photos"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.utils.file_handler import save_upload_file, get_file_url, delete_file

router = APIRouter()

@router.post("/puskesmas/sk-pendirian")
async def upload_sk_pendirian(file: UploadFile = File(...)):
    """Upload SK Pendirian Puskesmas (PDF)"""
    file_path = save_upload_file(file, "puskesmas_sk")
    file_url = get_file_url(file_path)
    return {
        "success": True,
        "file_path": file_path,
        "file_url": file_url,
        "message": "SK Pendirian uploaded successfully"
    }

@router.post("/puskesmas/npwp")
async def upload_npwp(file: UploadFile = File(...)):
    """Upload Scan NPWP Puskesmas (PDF/JPG)"""
    file_path = save_upload_file(file, "puskesmas_npwp")
    file_url = get_file_url(file_path)
    return {
        "success": True,
        "file_path": file_path,
        "file_url": file_url,
        "message": "NPWP uploaded successfully"
    }

@router.post("/puskesmas/photo")
async def upload_puskesmas_photo(file: UploadFile = File(...)):
    """Upload Foto Gedung Puskesmas (JPG/PNG)"""
    file_path = save_upload_file(file, "puskesmas_photo")
    file_url = get_file_url(file_path)
    return {
        "success": True,
        "file_path": file_path,
        "file_url": file_url,
        "message": "Puskesmas photo uploaded successfully"
    }

@router.post("/perawat/str")
async def upload_str(file: UploadFile = File(...)):
    """Upload STR Perawat (PDF/JPG)"""
    file_path = save_upload_file(file, "perawat_str")
    file_url = get_file_url(file_path)
    return {
        "success": True,
        "file_path": file_path,
        "file_url": file_url,
        "message": "STR uploaded successfully"
    }

@router.post("/perawat/profile-photo")
async def upload_perawat_profile(file: UploadFile = File(...)):
    """Upload Foto Profil Perawat (JPG/PNG)"""
    file_path = save_upload_file(file, "perawat_profile")
    file_url = get_file_url(file_path)
    return {
        "success": True,
        "file_path": file_path,
        "file_url": file_url,
        "message": "Profile photo uploaded successfully"
    }

@router.post("/ibu-hamil/profile-photo")
async def upload_ibu_hamil_profile(file: UploadFile = File(...)):
    """Upload Foto Profil Ibu Hamil (JPG/PNG)"""
    file_path = save_upload_file(file, "ibu_hamil_profile")
    file_url = get_file_url(file_path)
    return {
        "success": True,
        "file_path": file_path,
        "file_url": file_url,
        "message": "Profile photo uploaded successfully"
    }

@router.delete("/file")
async def delete_uploaded_file(file_path: str):
    """Delete uploaded file"""
    success = delete_file(file_path)
    if success:
        return {"success": True, "message": "File deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="File not found")