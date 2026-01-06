"""Perawat activation and profile endpoints (FR-TK-001).

Flow:
- Puskesmas generates account (existing in project via Perawat schemas/CRUD)
- Nurse receives verification link (token)
- Verify email -> set password -> complete profile (photo)
- Accept T&C -> account active

Notes:
- We store verification token in users.verification_token.
- Bio and terms timestamp are not in current models; proposing add later.
"""

import secrets
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db, require_role
from app.config import settings
from app.crud import crud_user, crud_perawat, crud_puskesmas
from app.models.user import User
from app.models.perawat import Perawat as PerawatModel
from app.schemas.perawat import PerawatRegisterWithUser, PerawatResponse
from app.schemas.perawat import PerawatCreate
from app.schemas.user import UserCreate
from app.services.email import EmailNotConfigured, send_email
from app.utils.file_handler import save_profile_photo

router = APIRouter(
    prefix="/perawat",
    tags=["Perawat (Nurses)"]
)


class VerificationRequest(BaseModel):
    user_id: int

    model_config = ConfigDict(json_schema_extra={
        "example": {"user_id": 123}
    })


class VerificationConfirm(BaseModel):
    token: str

    model_config = ConfigDict(json_schema_extra={
        "example": {"token": "VERIF_TOKEN_ABC..."}
    })


class SetPasswordPayload(BaseModel):
    token: str
    new_password: str

    model_config = ConfigDict(json_schema_extra={
        "example": {"token": "VERIF_TOKEN_ABC...", "new_password": "StrongPass!234"}
    })


class CompleteProfilePayload(BaseModel):
    token: str
    profile_photo_url: str

    model_config = ConfigDict(json_schema_extra={
        "example": {"token": "VERIF_TOKEN_ABC...", "profile_photo_url": "https://cdn.example.com/photos/perawat.jpg"}
    })


class AcceptTermsPayload(BaseModel):
    token: str

    model_config = ConfigDict(json_schema_extra={
        "example": {"token": "VERIF_TOKEN_ABC..."}
    })


def _get_perawat_by_user(db: Session, user_id: int) -> PerawatModel | None:
    return db.query(PerawatModel).filter(PerawatModel.user_id == user_id).first()


def _build_activation_email(*, token: str, nurse_name: str, puskesmas_name: str) -> tuple[str, str, str]:
    activation_link = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/perawat/activate?token={token}"
    subject = "Aktivasi Akun Perawat WellMom"
    text_body = (
        "Halo {name},\n\n"
        "Akun perawat Anda di WellMom telah dibuat oleh {puskesmas}. "
        "Silakan aktivasi akun dan atur password Anda melalui tautan berikut: {link}\n\n"
        "Jika Anda tidak merasa mendaftar, abaikan email ini.\n"
    ).format(name=nurse_name, puskesmas=puskesmas_name, link=activation_link)

    html_body = f"""
    <div style='font-family:Arial,sans-serif;color:#1f2937;'>
        <p>Halo <strong>{nurse_name}</strong>,</p>
        <p>Akun perawat Anda di WellMom telah dibuat oleh <strong>{puskesmas_name}</strong>.</p>
        <p>Silakan aktivasi akun dan atur password Anda dengan menekan tombol di bawah ini.</p>
        <p style='margin:24px 0;'>
            <a href='{activation_link}'
                 style='background:#2563eb;color:#ffffff;padding:12px 18px;border-radius:8px;text-decoration:none;font-weight:600;'>
                Aktivasi Akun
            </a>
        </p>
        <p>Jika tombol tidak berfungsi, gunakan tautan ini: <br><a href='{activation_link}'>{activation_link}</a></p>
        <p style='color:#6b7280;font-size:12px;'>Jika Anda tidak merasa mendaftar, abaikan email ini.</p>
    </div>
    """
    return subject, html_body, text_body


@router.post(
    "/generate",
    status_code=status.HTTP_201_CREATED,
    summary="Puskesmas generate akun perawat dan kirim email aktivasi",
)
def generate_perawat_account(
    payload: PerawatRegisterWithUser,
    current_user: User = Depends(require_role("puskesmas")),
    db: Session = Depends(get_db),
) -> dict:
    """Puskesmas creates a nurse account, stores verification token, and emails activation link."""
    puskesmas = crud_puskesmas.get_by_admin_user_id(db, admin_user_id=current_user.id)
    if not puskesmas:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Puskesmas profile not found for this user")

    # Uniqueness checks
    if crud_user.get_by_phone(db, phone=payload.phone):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone already registered")
    if crud_user.get_by_email(db, email=payload.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    if crud_perawat.get_by_nip(db, nip=payload.nip):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="NIP already registered")

    # Create user with temporary password; mark inactive until activation
    temp_password = secrets.token_urlsafe(8)
    user = crud_user.create_user(
        db,
        user_in=UserCreate(
            phone=payload.phone,
            password=temp_password,
            full_name=payload.full_name,
            role="perawat",
            email=payload.email,
        ),
    )
    user.is_active = False
    user.is_verified = False
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create perawat profile
    perawat = crud_perawat.create(
        db,
        obj_in=PerawatCreate(
            user_id=user.id,
            puskesmas_id=puskesmas.id,
            created_by_user_id=current_user.id,
            nik=payload.nik,
            nip=payload.nip,
            job_title=payload.job_title,
            license_number=payload.license_number,
            max_patients=payload.max_patients,
        ),
    )
    perawat.is_active = False
    perawat.is_available = False
    db.add(perawat)
    db.commit()
    db.refresh(perawat)

    token = crud_user.create_verification_token(db, user_id=user.id)
    if not token:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create verification token")

    subject, html_body, text_body = _build_activation_email(
        token=token, nurse_name=user.full_name, puskesmas_name=puskesmas.name
    )
    try:
        send_email(to_email=user.email, subject=subject, html_content=html_body, text_content=text_body)
    except EmailNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    activation_link = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/perawat/activate?token={token}"

    # Enrich perawat object for response schema (joined fields)
    perawat.full_name = user.full_name  # type: ignore[attr-defined]
    perawat.phone = user.phone  # type: ignore[attr-defined]
    perawat.email = user.email  # type: ignore[attr-defined]
    perawat.is_verified = False  # type: ignore[attr-defined]

    return {
        "perawat": PerawatResponse.from_orm(perawat),
        "activation_link": activation_link,
    }


@router.post(
    "/activation/request",
    status_code=status.HTTP_200_OK,
    summary="Request email verification",
)
def request_verification(payload: VerificationRequest, db: Session = Depends(get_db)) -> dict:
    """Generate verification token and send activation email to perawat."""
    user = crud_user.get(db, payload.user_id)
    if not user or user.role != "perawat":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perawat user not found")
    if not user.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Perawat email is required to send verification")

    token = crud_user.create_verification_token(db, user_id=user.id)
    if not token:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create token")

    perawat = _get_perawat_by_user(db, user_id=user.id)
    puskesmas_name = perawat.puskesmas.name if perawat and perawat.puskesmas else "Puskesmas"
    subject, html_body, text_body = _build_activation_email(token=token, nurse_name=user.full_name, puskesmas_name=puskesmas_name)

    try:
        send_email(to_email=user.email, subject=subject, html_content=html_body, text_content=text_body)
    except EmailNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    activation_link = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/perawat/activate?token={token}"
    return {"message": "Verification email sent", "activation_link": activation_link}


@router.post(
    "/activation/verify",
    status_code=status.HTTP_200_OK,
    summary="Verify email via token",
)
def verify_email(payload: VerificationConfirm, db: Session = Depends(get_db)) -> dict:
    user = crud_user.verify_by_token(db, token=payload.token)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
    return {"message": "Email verified", "user_id": user.id, "is_verified": user.is_verified}


@router.post(
    "/activation/set-password",
    status_code=status.HTTP_200_OK,
    summary="Set password after verification",
)
def set_password(payload: SetPasswordPayload, db: Session = Depends(get_db)) -> dict:
    # Only allow with valid token (pre-activation)
    stmt_user = db.query(User).filter(User.verification_token == payload.token).first()
    if not stmt_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token for password set")

    updated = crud_user.update_password(db, user_id=stmt_user.id, new_password=payload.new_password)
    if not updated:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to set password")
    return {"message": "Password updated", "user_id": updated.id}


@router.post(
    "/activation/complete-profile",
    response_model=PerawatResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete profile (photo)",
)
def complete_profile(payload: CompleteProfilePayload, db: Session = Depends(get_db)) -> PerawatModel:
    # Use token to locate user in activation flow
    user = db.query(User).filter(User.verification_token == payload.token).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")

    user.profile_photo_url = payload.profile_photo_url
    db.add(user)
    db.commit()
    db.refresh(user)

    perawat = _get_perawat_by_user(db, user_id=user.id)
    if not perawat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perawat profile not found")
    return perawat


@router.post(
    "/activation/accept-terms",
    status_code=status.HTTP_200_OK,
    summary="Accept T&C and activate",
)
def accept_terms(payload: AcceptTermsPayload, db: Session = Depends(get_db)) -> dict:
    user = db.query(User).filter(User.verification_token == payload.token).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")

    # Mark user verified/active and clear token
    user.is_verified = True
    user.is_active = True
    user.verification_token = None
    db.add(user)
    db.commit()
    db.refresh(user)

    perawat = _get_perawat_by_user(db, user_id=user.id)
    if perawat:
        perawat.is_active = True
        db.add(perawat)
        db.commit()
        db.refresh(perawat)

    return {"message": "Account activated", "user_id": user.id, "perawat_id": getattr(perawat, "id", None)}


@router.post(
    "/{perawat_id}/profile-photo",
    response_model=PerawatResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload perawat profile photo",
)
async def upload_profile_photo(
    perawat_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> PerawatModel:
    """Upload profile photo for a perawat.
    
    Only the perawat themselves or admin can upload their photo.
    Supported formats: JPG, PNG, GIF (max 5MB).
    """
    perawat = crud_perawat.get(db, perawat_id)
    if not perawat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perawat not found",
        )
    
    # Authorization: only the perawat or admin can upload their photo
    if current_user.role == "perawat" and perawat.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot upload photo for another perawat",
        )
    
    try:
        # Save file and get path
        photo_path = await save_profile_photo(file, "perawat", perawat_id)
        
        # Update perawat record
        perawat_update_data = {"profile_photo_url": photo_path}
        perawat = crud_perawat.update(db, db_obj=perawat, obj_in=perawat_update_data)
        
        return perawat
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload photo: {str(e)}",
        )


@router.get(
    "/{perawat_id}/profile-photo",
    status_code=status.HTTP_200_OK,
    summary="Get perawat profile photo URL",
)
def get_profile_photo_url(
    perawat_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Get profile photo URL for a perawat."""
    perawat = crud_perawat.get(db, perawat_id)
    if not perawat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perawat not found",
        )
    
    if not perawat.profile_photo_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile photo not found",
        )
    
    return {
        "perawat_id": perawat_id,
        "profile_photo_url": perawat.profile_photo_url,
    }


@router.delete(
    "/{perawat_id}/profile-photo",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete perawat profile photo",
)
def delete_profile_photo(
    perawat_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete profile photo for a perawat."""
    perawat = crud_perawat.get(db, perawat_id)
    if not perawat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perawat not found",
        )
    
    # Authorization: only the perawat themselves or admin can delete their photo
    if current_user.role == "perawat" and perawat.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete photo for another perawat",
        )
    
    # Clear photo URL
    perawat_update = {"profile_photo_url": None}
    crud_perawat.update(db, db_obj=perawat, obj_in=perawat_update)


@router.get(
    "",
    response_model=List[PerawatResponse],
    status_code=status.HTTP_200_OK,
    summary="List all perawat",
)
def list_perawat(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> List[PerawatModel]:
    """Public list of all active perawat."""
    return crud_perawat.get_multi(db, skip=skip, limit=limit)


