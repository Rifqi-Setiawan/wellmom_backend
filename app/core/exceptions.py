"""Custom exceptions untuk aplikasi WellMom."""

from fastapi import HTTPException, status


class IbuHamilLoginException(HTTPException):
    """Base exception untuk login ibu hamil."""
    pass


class InvalidCredentialsException(IbuHamilLoginException):
    """Exception ketika email atau password salah."""

    def __init__(self, detail: str = "Email atau password salah"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class EmailNotFoundException(IbuHamilLoginException):
    """Exception ketika email tidak ditemukan di sistem."""

    def __init__(self, detail: str = "Email tidak terdaftar di sistem"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


class AccountInactiveException(IbuHamilLoginException):
    """Exception ketika akun tidak aktif."""

    def __init__(self, detail: str = "Akun tidak aktif. Silakan hubungi administrator."):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class NotIbuHamilException(IbuHamilLoginException):
    """Exception ketika user bukan ibu hamil."""

    def __init__(self, detail: str = "Akun ini bukan akun ibu hamil. Silakan gunakan login yang sesuai."):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class IbuHamilProfileNotFoundException(IbuHamilLoginException):
    """Exception ketika profil ibu hamil tidak ditemukan."""

    def __init__(self, detail: str = "Profil ibu hamil tidak ditemukan. Silakan lengkapi registrasi terlebih dahulu."):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


class HealthRecordNotFoundException(HTTPException):
    """
    Exception ketika health record tidak ditemukan untuk ibu hamil.

    Digunakan ketika ibu hamil belum memiliki data health record sama sekali.
    Berbeda dengan kasus ketika health record dengan ID tertentu tidak ditemukan.

    Status Code: 404 Not Found

    Penggunaan:
        >>> from app.core.exceptions import HealthRecordNotFoundException
        >>> raise HealthRecordNotFoundException()
        >>> # atau dengan pesan custom
        >>> raise HealthRecordNotFoundException(detail="Pesan custom")

    Response Body:
        {
            "detail": "Belum ada data health record. Silakan lakukan pemeriksaan kesehatan terlebih dahulu."
        }
    """

    def __init__(self, detail: str = "Belum ada data health record. Silakan lakukan pemeriksaan kesehatan terlebih dahulu."):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


__all__ = [
    "IbuHamilLoginException",
    "InvalidCredentialsException",
    "EmailNotFoundException",
    "AccountInactiveException",
    "NotIbuHamilException",
    "IbuHamilProfileNotFoundException",
    "HealthRecordNotFoundException",
]
