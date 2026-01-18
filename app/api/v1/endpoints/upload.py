"""Upload endpoints for documents and photos"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import Optional

from app.api.deps import get_current_active_user, get_db, require_role
from app.utils.file_handler import save_upload_file, get_file_url, delete_file
from app.crud import crud_puskesmas, crud_perawat, crud_ibu_hamil
from app.models.user import User

router = APIRouter(
    prefix="/upload",
    tags=["Upload"]
)

# ===========================================
# PUSKESMAS DOCUMENT UPLOADS (Public - untuk registrasi)
# ===========================================

@router.post("/puskesmas/sk-pendirian")
async def upload_sk_pendirian(file: UploadFile = File(...)):
    """
    Upload SK Pendirian Puskesmas (PDF only).
    
    Digunakan saat registrasi puskesmas baru.
    Returns file_path yang akan disimpan ke database saat registrasi.
    
    - **file**: File PDF SK Pendirian (max 2MB)
    """
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SK Pendirian harus berformat PDF"
        )
    
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
    """
    Upload Scan NPWP Puskesmas (PDF atau JPG/JPEG).
    
    Digunakan saat registrasi puskesmas baru.
    Returns file_path yang akan disimpan ke database saat registrasi.
    
    - **file**: File PDF atau JPG/JPEG NPWP (max 2MB)
    """
    allowed_extensions = ['.pdf', '.jpg', '.jpeg']
    file_ext = file.filename.lower().split('.')[-1]
    
    if f'.{file_ext}' not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"NPWP harus berformat PDF atau JPG. Format yang diterima: {', '.join(allowed_extensions)}"
        )
    
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
    """
    Upload Foto Gedung Puskesmas (JPG/PNG).
    
    Digunakan saat registrasi puskesmas baru.
    Returns file_path yang akan disimpan ke database saat registrasi.
    
    - **file**: File JPG/JPEG/PNG foto gedung (max 2MB)
    """
    allowed_extensions = ['.jpg', '.jpeg', '.png']
    file_ext = file.filename.lower().split('.')[-1]
    
    if f'.{file_ext}' not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Foto harus berformat JPG atau PNG. Format yang diterima: {', '.join(allowed_extensions)}"
        )
    
    file_path = save_upload_file(file, "puskesmas_photo")
    file_url = get_file_url(file_path)
    
    return {
        "success": True,
        "file_path": file_path,
        "file_url": file_url,
        "message": "Foto gedung uploaded successfully"
    }


# ===========================================
# PUSKESMAS DOCUMENT UPDATES (Authenticated - untuk update)
# ===========================================

@router.put("/puskesmas/{puskesmas_id}/sk-pendirian")
async def update_sk_pendirian(
    puskesmas_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update SK Pendirian Puskesmas.
    
    Hanya admin puskesmas yang bersangkutan atau super_admin yang dapat update.
    File lama akan dihapus dan diganti dengan file baru.
    
    - **puskesmas_id**: ID puskesmas
    - **file**: File PDF SK Pendirian baru (max 2MB)
    """
    # Get puskesmas
    puskesmas = crud_puskesmas.get(db, id=puskesmas_id)
    if not puskesmas:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Puskesmas tidak ditemukan"
        )
    
    # Authorization: hanya admin puskesmas atau super_admin
    if current_user.role == "puskesmas" and puskesmas.admin_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tidak memiliki akses untuk update dokumen puskesmas ini"
        )
    elif current_user.role not in ["puskesmas", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya admin puskesmas atau super admin yang dapat update dokumen"
        )
    
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SK Pendirian harus berformat PDF"
        )
    
    # Delete old file if exists
    if puskesmas.sk_document_url:
        delete_file(puskesmas.sk_document_url)
    
    # Upload new file
    file_path = save_upload_file(file, "puskesmas_sk")
    file_url = get_file_url(file_path)
    
    # Update database
    puskesmas.sk_document_url = file_path
    db.add(puskesmas)
    db.commit()
    db.refresh(puskesmas)
    
    return {
        "success": True,
        "puskesmas_id": puskesmas_id,
        "file_path": file_path,
        "file_url": file_url,
        "message": "SK Pendirian updated successfully"
    }


@router.put("/puskesmas/{puskesmas_id}/npwp")
async def update_npwp(
    puskesmas_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update Scan NPWP Puskesmas.
    
    Hanya admin puskesmas yang bersangkutan atau super_admin yang dapat update.
    File lama akan dihapus dan diganti dengan file baru.
    
    - **puskesmas_id**: ID puskesmas
    - **file**: File PDF atau JPG NPWP baru (max 2MB)
    """
    # Get puskesmas
    puskesmas = crud_puskesmas.get(db, id=puskesmas_id)
    if not puskesmas:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Puskesmas tidak ditemukan"
        )
    
    # Authorization
    if current_user.role == "puskesmas" and puskesmas.admin_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tidak memiliki akses untuk update dokumen puskesmas ini"
        )
    elif current_user.role not in ["puskesmas", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya admin puskesmas atau super admin yang dapat update dokumen"
        )
    
    # Validate file type
    allowed_extensions = ['.pdf', '.jpg', '.jpeg']
    file_ext = file.filename.lower().split('.')[-1]
    
    if f'.{file_ext}' not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"NPWP harus berformat PDF atau JPG"
        )
    
    # Delete old file if exists
    if puskesmas.npwp_document_url:
        delete_file(puskesmas.npwp_document_url)
    
    # Upload new file
    file_path = save_upload_file(file, "puskesmas_npwp")
    file_url = get_file_url(file_path)
    
    # Update database
    puskesmas.npwp_document_url = file_path
    db.add(puskesmas)
    db.commit()
    db.refresh(puskesmas)
    
    return {
        "success": True,
        "puskesmas_id": puskesmas_id,
        "file_path": file_path,
        "file_url": file_url,
        "message": "NPWP updated successfully"
    }


@router.put("/puskesmas/{puskesmas_id}/photo")
async def update_puskesmas_photo(
    puskesmas_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update Foto Gedung Puskesmas.
    
    Hanya admin puskesmas yang bersangkutan atau super_admin yang dapat update.
    File lama akan dihapus dan diganti dengan file baru.
    
    - **puskesmas_id**: ID puskesmas
    - **file**: File JPG/PNG foto gedung baru (max 2MB)
    """
    # Get puskesmas
    puskesmas = crud_puskesmas.get(db, id=puskesmas_id)
    if not puskesmas:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Puskesmas tidak ditemukan"
        )
    
    # Authorization
    if current_user.role == "puskesmas" and puskesmas.admin_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tidak memiliki akses untuk update foto puskesmas ini"
        )
    elif current_user.role not in ["puskesmas", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya admin puskesmas atau super admin yang dapat update foto"
        )
    
    # Validate file type
    allowed_extensions = ['.jpg', '.jpeg', '.png']
    file_ext = file.filename.lower().split('.')[-1]
    
    if f'.{file_ext}' not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Foto harus berformat JPG atau PNG"
        )
    
    # Delete old file if exists
    if puskesmas.building_photo_url:
        delete_file(puskesmas.building_photo_url)
    
    # Upload new file
    file_path = save_upload_file(file, "puskesmas_photo")
    file_url = get_file_url(file_path)
    
    # Update database
    puskesmas.building_photo_url = file_path
    db.add(puskesmas)
    db.commit()
    db.refresh(puskesmas)
    
    return {
        "success": True,
        "puskesmas_id": puskesmas_id,
        "file_path": file_path,
        "file_url": file_url,
        "message": "Foto gedung updated successfully"
    }


# ===========================================
# DELETE ENDPOINTS
# ===========================================

@router.delete("/puskesmas/{puskesmas_id}/sk-pendirian")
async def delete_sk_pendirian(
    puskesmas_id: int,
    current_user: User = Depends(require_role("super_admin")),
    db: Session = Depends(get_db)
):
    """
    Hapus SK Pendirian Puskesmas (Super Admin only).
    """
    puskesmas = crud_puskesmas.get(db, id=puskesmas_id)
    if not puskesmas:
        raise HTTPException(status_code=404, detail="Puskesmas tidak ditemukan")
    
    if puskesmas.sk_document_url:
        delete_file(puskesmas.sk_document_url)
        puskesmas.sk_document_url = None
        db.commit()
    
    return {"success": True, "message": "SK Pendirian deleted"}


@router.delete("/puskesmas/{puskesmas_id}/npwp")
async def delete_npwp(
    puskesmas_id: int,
    current_user: User = Depends(require_role("super_admin")),
    db: Session = Depends(get_db)
):
    """
    Hapus NPWP Puskesmas (Super Admin only).
    """
    puskesmas = crud_puskesmas.get(db, id=puskesmas_id)
    if not puskesmas:
        raise HTTPException(status_code=404, detail="Puskesmas tidak ditemukan")
    
    if puskesmas.npwp_document_url:
        delete_file(puskesmas.npwp_document_url)
        puskesmas.npwp_document_url = None
        db.commit()
    
    return {"success": True, "message": "NPWP deleted"}


@router.delete("/puskesmas/{puskesmas_id}/photo")
async def delete_puskesmas_photo(
    puskesmas_id: int,
    current_user: User = Depends(require_role("super_admin")),
    db: Session = Depends(get_db)
):
    """
    Hapus Foto Gedung Puskesmas (Super Admin only).
    """
    puskesmas = crud_puskesmas.get(db, id=puskesmas_id)
    if not puskesmas:
        raise HTTPException(status_code=404, detail="Puskesmas tidak ditemukan")
    
    if puskesmas.building_photo_url:
        delete_file(puskesmas.building_photo_url)
        puskesmas.building_photo_url = None
        db.commit()
    
    return {"success": True, "message": "Foto gedung deleted"}


# ===========================================
# PERAWAT DOCUMENT UPLOADS
# ===========================================

@router.post("/perawat/str")
async def upload_str(file: UploadFile = File(...)):
    """Upload STR Perawat (PDF/JPG)"""
    allowed_extensions = ['.pdf', '.jpg', '.jpeg']
    file_ext = file.filename.lower().split('.')[-1]
    
    if f'.{file_ext}' not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="STR harus berformat PDF atau JPG"
        )
    
    file_path = save_upload_file(file, "perawat_str")
    file_url = get_file_url(file_path)
    
    return {
        "success": True,
        "file_path": file_path,
        "file_url": file_url,
        "message": "STR uploaded successfully"
    }


# ===========================================
# PERAWAT PROFILE PHOTOS
# ===========================================

@router.post("/perawat/profile-photo")
async def upload_perawat_profile(file: UploadFile = File(...)):
    """Upload Foto Profil Perawat (JPG/PNG)"""
    allowed_extensions = ['.jpg', '.jpeg', '.png']
    file_ext = file.filename.lower().split('.')[-1]
    
    if f'.{file_ext}' not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Foto harus berformat JPG atau PNG"
        )
    
    file_path = save_upload_file(file, "perawat_profile")
    file_url = get_file_url(file_path)
    
    return {
        "success": True,
        "file_path": file_path,
        "file_url": file_url,
        "message": "Profile photo uploaded successfully"
    }


@router.put("/perawat/{perawat_id}/profile-photo")
async def update_perawat_photo(
    perawat_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update Foto Profil Perawat.
    
    Hanya perawat sendiri atau super_admin yang dapat update.
    File lama akan dihapus dan diganti dengan file baru.
    
    - **perawat_id**: ID perawat
    - **file**: File JPG/PNG foto baru (max 2MB)
    """
    # Get perawat
    perawat = crud_perawat.get(db, id=perawat_id)
    if not perawat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perawat tidak ditemukan"
        )
    
    # Authorization: hanya perawat sendiri atau super_admin
    if current_user.role == "perawat" and perawat.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tidak memiliki akses untuk update foto perawat ini"
        )
    elif current_user.role not in ["perawat", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya perawat atau super admin yang dapat update foto"
        )
    
    # Validate file type
    allowed_extensions = ['.jpg', '.jpeg', '.png']
    file_ext = file.filename.lower().split('.')[-1]
    
    if f'.{file_ext}' not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Foto harus berformat JPG atau PNG"
        )
    
    # Delete old file if exists
    if perawat.profile_photo_url:
        delete_file(perawat.profile_photo_url)
    
    # Upload new file
    file_path = save_upload_file(file, "perawat_profile")
    file_url = get_file_url(file_path)
    
    # Update database
    perawat.profile_photo_url = file_path
    db.add(perawat)
    db.commit()
    db.refresh(perawat)
    
    return {
        "success": True,
        "perawat_id": perawat_id,
        "file_path": file_path,
        "file_url": file_url,
        "message": "Profile photo updated successfully"
    }


@router.delete("/perawat/{perawat_id}/profile-photo")
async def delete_perawat_photo(
    perawat_id: int,
    current_user: User = Depends(require_role("super_admin")),
    db: Session = Depends(get_db)
):
    """
    Hapus Foto Profil Perawat (Super Admin only).
    """
    perawat = crud_perawat.get(db, id=perawat_id)
    if not perawat:
        raise HTTPException(status_code=404, detail="Perawat tidak ditemukan")
    
    if perawat.profile_photo_url:
        delete_file(perawat.profile_photo_url)
        perawat.profile_photo_url = None
        db.commit()
    
    return {"success": True, "message": "Profile photo deleted"}


# ===========================================
# IBU HAMIL UPLOADS
# ===========================================

@router.post("/ibu-hamil/profile-photo")
async def upload_ibu_hamil_profile(file: UploadFile = File(...)):
    """Upload Foto Profil Ibu Hamil (JPG/PNG)"""
    allowed_extensions = ['.jpg', '.jpeg', '.png']
    file_ext = file.filename.lower().split('.')[-1]
    
    if f'.{file_ext}' not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Foto harus berformat JPG atau PNG"
        )
    
    file_path = save_upload_file(file, "ibu_hamil_profile")
    file_url = get_file_url(file_path)
    
    return {
        "success": True,
        "file_path": file_path,
        "file_url": file_url,
        "message": "Profile photo uploaded successfully"
    }


@router.put("/ibu-hamil/{ibu_hamil_id}/profile-photo")
async def update_ibu_hamil_photo(
    ibu_hamil_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update Foto Profil Ibu Hamil.
    
    Hanya ibu hamil sendiri atau super_admin yang dapat update.
    File lama akan dihapus dan diganti dengan file baru.
    
    - **ibu_hamil_id**: ID ibu hamil
    - **file**: File JPG/PNG foto baru (max 2MB)
    """
    # Get ibu hamil
    ibu_hamil = crud_ibu_hamil.get(db, id=ibu_hamil_id)
    if not ibu_hamil:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ibu hamil tidak ditemukan"
        )
    
    # Authorization: hanya ibu hamil sendiri atau super_admin
    if current_user.role == "ibu_hamil" and ibu_hamil.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tidak memiliki akses untuk update foto ibu hamil ini"
        )
    elif current_user.role not in ["ibu_hamil", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya ibu hamil atau super admin yang dapat update foto"
        )
    
    # Validate file type
    allowed_extensions = ['.jpg', '.jpeg', '.png']
    file_ext = file.filename.lower().split('.')[-1]
    
    if f'.{file_ext}' not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Foto harus berformat JPG atau PNG"
        )
    
    # Delete old file if exists
    if ibu_hamil.profile_photo_url:
        delete_file(ibu_hamil.profile_photo_url)
    
    # Upload new file
    file_path = save_upload_file(file, "ibu_hamil_profile")
    file_url = get_file_url(file_path)
    
    # Update database
    ibu_hamil.profile_photo_url = file_path
    db.add(ibu_hamil)
    db.commit()
    db.refresh(ibu_hamil)
    
    return {
        "success": True,
        "ibu_hamil_id": ibu_hamil_id,
        "file_path": file_path,
        "file_url": file_url,
        "message": "Profile photo updated successfully"
    }


@router.delete("/ibu-hamil/{ibu_hamil_id}/profile-photo")
async def delete_ibu_hamil_photo(
    ibu_hamil_id: int,
    current_user: User = Depends(require_role("super_admin")),
    db: Session = Depends(get_db)
):
    """
    Hapus Foto Profil Ibu Hamil (Super Admin only).
    """
    ibu_hamil = crud_ibu_hamil.get(db, id=ibu_hamil_id)
    if not ibu_hamil:
        raise HTTPException(status_code=404, detail="Ibu hamil tidak ditemukan")
    
    if ibu_hamil.profile_photo_url:
        delete_file(ibu_hamil.profile_photo_url)
        ibu_hamil.profile_photo_url = None
        db.commit()
    
    return {"success": True, "message": "Profile photo deleted"}