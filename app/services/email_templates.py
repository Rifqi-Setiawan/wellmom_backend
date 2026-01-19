"""Professional email templates for WellMom application."""

from datetime import datetime
from typing import Optional


def _get_base_styles() -> str:
    """Base CSS styles for email templates."""
    return """
    <style>
        body { margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .email-container { max-width: 600px; margin: 0 auto; background-color: #ffffff; }
        .email-header { background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); padding: 32px 24px; text-align: center; }
        .email-header img { height: 40px; margin-bottom: 8px; }
        .email-header h1 { color: #ffffff; font-size: 24px; margin: 0; font-weight: 600; }
        .email-body { padding: 32px 24px; color: #1f2937; line-height: 1.6; }
        .email-body h2 { color: #1f2937; font-size: 20px; margin: 0 0 16px 0; }
        .email-body p { margin: 0 0 16px 0; font-size: 15px; }
        .highlight-box { background-color: #f0f9ff; border-left: 4px solid #2563eb; padding: 16px; margin: 24px 0; border-radius: 0 8px 8px 0; }
        .highlight-box p { margin: 0; color: #1e40af; }
        .credentials-box { background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; margin: 24px 0; }
        .credentials-box .label { font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
        .credentials-box .value { font-size: 16px; color: #1e293b; font-weight: 600; font-family: monospace; background: #e2e8f0; padding: 8px 12px; border-radius: 4px; margin-bottom: 12px; }
        .btn-primary { display: inline-block; background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); color: #ffffff !important; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 16px; margin: 8px 0; }
        .btn-primary:hover { background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%); }
        .link-fallback { font-size: 13px; color: #64748b; word-break: break-all; margin-top: 16px; }
        .link-fallback a { color: #2563eb; }
        .divider { border: 0; border-top: 1px solid #e2e8f0; margin: 24px 0; }
        .email-footer { background-color: #f8fafc; padding: 24px; text-align: center; border-top: 1px solid #e2e8f0; }
        .email-footer p { margin: 0 0 8px 0; font-size: 13px; color: #64748b; }
        .email-footer .social-links { margin: 16px 0; }
        .email-footer .social-links a { display: inline-block; margin: 0 8px; color: #64748b; text-decoration: none; }
        .warning-box { background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 16px; margin: 24px 0; border-radius: 0 8px 8px 0; }
        .warning-box p { margin: 0; color: #92400e; font-size: 14px; }
        .success-box { background-color: #d1fae5; border-left: 4px solid #10b981; padding: 16px; margin: 24px 0; border-radius: 0 8px 8px 0; }
        .success-box p { margin: 0; color: #065f46; }
        .info-list { list-style: none; padding: 0; margin: 16px 0; }
        .info-list li { padding: 8px 0 8px 24px; position: relative; font-size: 14px; }
        .info-list li:before { content: "✓"; position: absolute; left: 0; color: #10b981; font-weight: bold; }
    </style>
    """


def _get_header(title: str = "WellMom") -> str:
    """Email header with logo."""
    return f"""
    <div class="email-header">
        <h1>{title}</h1>
        <p style="color: rgba(255,255,255,0.9); margin: 8px 0 0 0; font-size: 14px;">
            Sistem Pemantauan Kesehatan Ibu Hamil
        </p>
    </div>
    """


def _get_footer(year: Optional[int] = None) -> str:
    """Email footer with copyright."""
    if year is None:
        year = datetime.now().year
    return f"""
    <div class="email-footer">
        <p><strong>WellMom</strong></p>
        <p>Sistem Pemantauan Kesehatan Ibu Hamil</p>
        <hr class="divider" style="margin: 16px auto; width: 50%;">
        <p style="font-size: 12px;">
            Email ini dikirim secara otomatis oleh sistem WellMom.<br>
            Mohon tidak membalas email ini.
        </p>
        <p style="font-size: 11px; color: #94a3b8;">
            &copy; {year} WellMom. All rights reserved.
        </p>
    </div>
    """


def build_perawat_activation_email(
    *,
    nurse_name: str,
    puskesmas_name: str,
    activation_link: str,
    email: str,
    nip: str,
    expires_in_hours: int = 72,
) -> tuple[str, str, str]:
    """Build professional activation email for perawat.

    Returns:
        Tuple of (subject, html_body, text_body)
    """
    subject = "Aktivasi Akun Perawat - WellMom"

    html_body = f"""
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        {_get_base_styles()}
    </head>
    <body style="background-color: #f1f5f9; padding: 24px 0;">
        <div class="email-container" style="border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            {_get_header("WellMom")}

            <div class="email-body">
                <h2>Selamat Datang di WellMom!</h2>

                <p>Halo <strong>{nurse_name}</strong>,</p>

                <p>
                    Akun perawat Anda telah berhasil dibuat oleh <strong>{puskesmas_name}</strong>.
                    Anda sekarang dapat mengakses sistem WellMom untuk memantau dan mengelola
                    data kesehatan ibu hamil di wilayah kerja Anda.
                </p>

                <div class="highlight-box">
                    <p><strong>Langkah selanjutnya:</strong> Aktivasi akun Anda untuk mulai menggunakan WellMom.</p>
                </div>

                <div class="credentials-box">
                    <div class="label">Email Login</div>
                    <div class="value">{email}</div>

                    <div class="label">Password Awal (NIP Anda)</div>
                    <div class="value">{nip}</div>

                    <p style="font-size: 13px; color: #64748b; margin: 8px 0 0 0;">
                        * Anda dapat mengubah password setelah aktivasi
                    </p>
                </div>

                <div style="text-align: center; margin: 32px 0;">
                    <a href="{activation_link}" class="btn-primary">
                        Aktivasi Akun Sekarang
                    </a>
                </div>

                <div class="link-fallback">
                    Jika tombol tidak berfungsi, salin dan tempel tautan berikut di browser Anda:<br>
                    <a href="{activation_link}">{activation_link}</a>
                </div>

                <div class="warning-box">
                    <p>
                        <strong>Penting:</strong> Tautan aktivasi ini akan kedaluwarsa dalam
                        <strong>{expires_in_hours} jam</strong>. Segera aktivasi akun Anda.
                    </p>
                </div>

                <hr class="divider">

                <p style="font-size: 14px; color: #64748b;">
                    Jika Anda tidak merasa mendaftar atau tidak mengenali email ini,
                    abaikan saja dan akun tidak akan diaktifkan.
                </p>
            </div>

            {_get_footer()}
        </div>
    </body>
    </html>
    """

    text_body = f"""
WELLMOM - Aktivasi Akun Perawat
================================

Halo {nurse_name},

Akun perawat Anda telah berhasil dibuat oleh {puskesmas_name}.

INFORMASI LOGIN:
- Email: {email}
- Password Awal: {nip} (NIP Anda)

Silakan aktivasi akun Anda melalui tautan berikut:
{activation_link}

PENTING: Tautan ini akan kedaluwarsa dalam {expires_in_hours} jam.

Jika Anda tidak merasa mendaftar, abaikan email ini.

---
WellMom - Sistem Pemantauan Kesehatan Ibu Hamil
Email ini dikirim secara otomatis. Mohon tidak membalas.
    """

    return subject, html_body, text_body


def build_perawat_activation_success_email(
    *,
    nurse_name: str,
    puskesmas_name: str,
    login_url: str,
) -> tuple[str, str, str]:
    """Build email notification when perawat successfully activates account.

    Returns:
        Tuple of (subject, html_body, text_body)
    """
    subject = "Akun Berhasil Diaktivasi - WellMom"

    html_body = f"""
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        {_get_base_styles()}
    </head>
    <body style="background-color: #f1f5f9; padding: 24px 0;">
        <div class="email-container" style="border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            {_get_header("WellMom")}

            <div class="email-body">
                <div class="success-box">
                    <p><strong>Selamat!</strong> Akun Anda telah berhasil diaktivasi.</p>
                </div>

                <h2>Akun Aktif!</h2>

                <p>Halo <strong>{nurse_name}</strong>,</p>

                <p>
                    Akun perawat Anda di <strong>{puskesmas_name}</strong> telah berhasil
                    diaktivasi dan siap digunakan.
                </p>

                <p>Dengan akun WellMom, Anda dapat:</p>

                <ul class="info-list">
                    <li>Memantau kesehatan ibu hamil di wilayah kerja Anda</li>
                    <li>Menerima notifikasi pemeriksaan rutin</li>
                    <li>Mencatat hasil pemeriksaan dan konsultasi</li>
                    <li>Berkoordinasi dengan tim kesehatan puskesmas</li>
                </ul>

                <div style="text-align: center; margin: 32px 0;">
                    <a href="{login_url}" class="btn-primary">
                        Masuk ke WellMom
                    </a>
                </div>

                <hr class="divider">

                <p style="font-size: 14px; color: #64748b;">
                    Jika Anda memiliki pertanyaan, silakan hubungi admin puskesmas Anda.
                </p>
            </div>

            {_get_footer()}
        </div>
    </body>
    </html>
    """

    text_body = f"""
WELLMOM - Akun Berhasil Diaktivasi
===================================

Halo {nurse_name},

Selamat! Akun perawat Anda di {puskesmas_name} telah berhasil diaktivasi.

Anda sekarang dapat login ke WellMom di:
{login_url}

Dengan akun WellMom, Anda dapat:
- Memantau kesehatan ibu hamil di wilayah kerja Anda
- Menerima notifikasi pemeriksaan rutin
- Mencatat hasil pemeriksaan dan konsultasi
- Berkoordinasi dengan tim kesehatan puskesmas

Jika memiliki pertanyaan, hubungi admin puskesmas Anda.

---
WellMom - Sistem Pemantauan Kesehatan Ibu Hamil
    """

    return subject, html_body, text_body


def build_puskesmas_perawat_activated_notification(
    *,
    admin_name: str,
    nurse_name: str,
    nurse_email: str,
    nurse_nip: str,
    puskesmas_name: str,
    dashboard_url: str,
) -> tuple[str, str, str]:
    """Build notification email for puskesmas admin when perawat activates account.

    Returns:
        Tuple of (subject, html_body, text_body)
    """
    subject = f"Perawat Baru Aktif: {nurse_name} - WellMom"

    html_body = f"""
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        {_get_base_styles()}
    </head>
    <body style="background-color: #f1f5f9; padding: 24px 0;">
        <div class="email-container" style="border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            {_get_header("WellMom")}

            <div class="email-body">
                <div class="success-box">
                    <p><strong>Kabar Baik!</strong> Seorang perawat baru telah mengaktifkan akunnya.</p>
                </div>

                <h2>Perawat Baru Aktif</h2>

                <p>Halo <strong>{admin_name}</strong>,</p>

                <p>
                    Kami ingin memberitahukan bahwa perawat berikut telah berhasil
                    mengaktifkan akun WellMom mereka di <strong>{puskesmas_name}</strong>:
                </p>

                <div class="credentials-box">
                    <div class="label">Nama Perawat</div>
                    <div class="value" style="background: #d1fae5; color: #065f46;">{nurse_name}</div>

                    <div class="label">Email</div>
                    <div class="value">{nurse_email}</div>

                    <div class="label">NIP</div>
                    <div class="value">{nurse_nip}</div>
                </div>

                <p>
                    Perawat ini sekarang dapat mengakses sistem WellMom dan siap
                    untuk ditugaskan menangani ibu hamil.
                </p>

                <div style="text-align: center; margin: 32px 0;">
                    <a href="{dashboard_url}" class="btn-primary">
                        Kelola Perawat
                    </a>
                </div>
            </div>

            {_get_footer()}
        </div>
    </body>
    </html>
    """

    text_body = f"""
WELLMOM - Perawat Baru Aktif
=============================

Halo {admin_name},

Perawat berikut telah berhasil mengaktifkan akun WellMom di {puskesmas_name}:

INFORMASI PERAWAT:
- Nama: {nurse_name}
- Email: {nurse_email}
- NIP: {nurse_nip}

Perawat ini sekarang dapat mengakses sistem dan siap ditugaskan menangani ibu hamil.

Kelola perawat di: {dashboard_url}

---
WellMom - Sistem Pemantauan Kesehatan Ibu Hamil
    """

    return subject, html_body, text_body


def build_resend_activation_email(
    *,
    nurse_name: str,
    puskesmas_name: str,
    activation_link: str,
    email: str,
    expires_in_hours: int = 72,
) -> tuple[str, str, str]:
    """Build resend activation email for perawat.

    Returns:
        Tuple of (subject, html_body, text_body)
    """
    subject = "Tautan Aktivasi Baru - WellMom"

    html_body = f"""
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        {_get_base_styles()}
    </head>
    <body style="background-color: #f1f5f9; padding: 24px 0;">
        <div class="email-container" style="border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            {_get_header("WellMom")}

            <div class="email-body">
                <h2>Tautan Aktivasi Baru</h2>

                <p>Halo <strong>{nurse_name}</strong>,</p>

                <p>
                    Anda telah meminta tautan aktivasi baru untuk akun perawat Anda
                    di <strong>{puskesmas_name}</strong>.
                </p>

                <div class="highlight-box">
                    <p>Tautan aktivasi sebelumnya telah dinonaktifkan. Gunakan tautan baru di bawah ini.</p>
                </div>

                <div style="text-align: center; margin: 32px 0;">
                    <a href="{activation_link}" class="btn-primary">
                        Aktivasi Akun Sekarang
                    </a>
                </div>

                <div class="link-fallback">
                    Jika tombol tidak berfungsi, salin dan tempel tautan berikut di browser Anda:<br>
                    <a href="{activation_link}">{activation_link}</a>
                </div>

                <div class="warning-box">
                    <p>
                        <strong>Penting:</strong> Tautan ini akan kedaluwarsa dalam
                        <strong>{expires_in_hours} jam</strong>.
                    </p>
                </div>

                <hr class="divider">

                <p style="font-size: 14px; color: #64748b;">
                    Jika Anda tidak meminta tautan aktivasi baru, abaikan email ini.
                    Keamanan akun Anda tetap terjaga.
                </p>
            </div>

            {_get_footer()}
        </div>
    </body>
    </html>
    """

    text_body = f"""
WELLMOM - Tautan Aktivasi Baru
===============================

Halo {nurse_name},

Anda telah meminta tautan aktivasi baru untuk akun perawat Anda di {puskesmas_name}.

Tautan aktivasi sebelumnya telah dinonaktifkan.

Silakan aktivasi akun Anda melalui tautan berikut:
{activation_link}

PENTING: Tautan ini akan kedaluwarsa dalam {expires_in_hours} jam.

Jika Anda tidak meminta tautan ini, abaikan email ini.

---
WellMom - Sistem Pemantauan Kesehatan Ibu Hamil
    """

    return subject, html_body, text_body
