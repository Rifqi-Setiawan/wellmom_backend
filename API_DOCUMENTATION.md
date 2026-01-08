# WellMom API Documentation

**Version:** 1.0.0  
**Base URL:** `http://localhost:8000` (Development) | `https://api.wellmom.com` (Production)  
**API Version:** `/api/v1`  

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Health Check Endpoints](#health-check-endpoints)
4. [Authentication Endpoints](#authentication-endpoints)
5. [User Management Endpoints](#user-management-endpoints)
6. [Puskesmas (Health Center) Endpoints](#puskesmas-endpoints)
7. [Ibu Hamil (Pregnant Women) Endpoints](#ibu-hamil-endpoints)
8. [Error Handling](#error-handling)
9. [Response Codes](#response-codes)
10. [Validation Rules](#validation-rules)

---

## Overview

WellMom API adalah backend service untuk aplikasi manajemen kesehatan ibu hamil (pregnant women). Platform ini menghubungkan ibu hamil dengan puskesmas (health centers) dan perawat untuk memberikan pelayanan kesehatan yang lebih baik.

### Fitur Utama:
- 👤 User authentication dengan JWT token
- 🏥 Manajemen puskesmas dan registrasi
- 🤰 Manajemen data ibu hamil
- 👨‍⚕️ Penugasan perawat otomatis atau manual
- 📍 Geo-location based assignment
- 📢 Notification system
- 🔐 Role-based access control (RBAC)

### User Roles:
- **super_admin**: Super administrator (dapat approve/reject/deactivate registrasi puskesmas, read-only untuk data lainnya)
- **puskesmas**: Puskesmas administrator (mengelola perawat dan assign ibu hamil di puskesmasnya)
- **perawat**: Nurse/Healthcare worker
- **ibu_hamil**: Pregnant woman
- **kerabat**: Family member/Guardian

---

## Authentication

WellMom API menggunakan **OAuth2 Bearer Token** (JWT) untuk autentikasi.

### Cara Menggunakan Token:

Setiap request yang memerlukan autentikasi harus menyertakan header berikut:

```
Authorization: Bearer <access_token>
```

### Token Details:
- **Format:** JWT (JSON Web Token)
- **Duration:** 30 hari
- **Stored In:** Request header `Authorization`

### Contoh Request dengan Authentication:

```bash
curl -X GET "http://localhost:8000/api/v1/users/me" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

## Health Check Endpoints

### 1. Root Endpoint

**Deskripsi:** Endpoint root untuk memverifikasi API sedang berjalan dan mendapatkan informasi dasar.

**Endpoint Details:**
- **HTTP Method:** GET
- **URL Path:** `/`
- **Authentication:** Not required
- **Status Code:** 200

**Response Example:**

```json
{
  "message": "Welcome to WellMom API",
  "version": "1.0.0",
  "status": "running"
}
```

---

### 2. Health Check

**Deskripsi:** Endpoint untuk verifikasi API health status. Berguna untuk monitoring dan load balancer checks.

**Endpoint Details:**
- **HTTP Method:** GET
- **URL Path:** `/health`
- **Authentication:** Not required
- **Status Code:** 200

**Response Example:**

```json
{
  "status": "healthy"
}
```

---

### 3. Database Connection Test

**Deskripsi:** Test koneksi database dan verifikasi database sudah tersedia.

**Endpoint Details:**
- **HTTP Method:** GET
- **URL Path:** `/db-test`
- **Authentication:** Not required
- **Status Code:** 200 | 500

**Success Response (Status 200):**

```json
{
  "status": "success",
  "message": "Database connection successful",
  "database": "wellmom"
}
```

**Error Response (Status 500):**

```json
{
  "status": "error",
  "message": "connection refused"
}
```

---

### 4. PostGIS Extension Test

**Deskripsi:** Test PostGIS extension untuk geographic/location queries.

**Endpoint Details:**
- **HTTP Method:** GET
- **URL Path:** `/postgis-test`
- **Authentication:** Not required
- **Status Code:** 200 | 500

**Success Response (Status 200):**

```json
{
  "status": "success",
  "message": "PostGIS is working",
  "version": "POSTGIS=\"3.3.0 3.3.0\""
}
```

---

## Authentication Endpoints

### 1. Register New User

**Deskripsi Endpoint:**
- Registrasi user baru dengan phone, password, full_name, dan role
- Otomatis membuat access token setelah registrasi sukses
- Validasi phone untuk mencegah duplikat

**Request Details:**

- **HTTP Method:** POST
- **URL Path:** `/api/v1/auth/register`
- **Authentication:** Not required
- **Status Codes:** 201 (Created), 400 (Bad Request)

**Headers:**

```
Content-Type: application/json
```

**Request Body:**

```json
{
  "phone": "+6281234567890",
  "password": "StrongPassword123!",
  "full_name": "Siti Aminah",
  "role": "ibu_hamil",
  "email": "siti@example.com"
}
```

**Request Body Schema:**

| Field | Type | Required | Validation |
|-------|------|----------|-----------|
| phone | string | Yes | 8-15 digits, optional leading '+' |
| password | string | Yes | Minimum 8 characters |
| full_name | string | Yes | Non-empty string |
| role | string | Yes | One of: admin, puskesmas, perawat, ibu_hamil, kerabat |
| email | string | Optional | Valid email format |

**Response Details:**

**Success Response (Status 201):**

```json
{
  "user": {
    "id": 1,
    "phone": "+6281234567890",
    "full_name": "Siti Aminah",
    "role": "ibu_hamil",
    "email": "siti@example.com",
    "profile_photo_url": null,
    "is_active": true,
    "is_verified": false
  },
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Error Response (Status 400):**

```json
{
  "detail": "Phone number already registered"
}
```

**Validation Notes:**
- Phone harus unik di database
- Password akan di-hash sebelum disimpan
- Role harus salah satu dari 5 role yang didefinisikan

---

### 2. Login User

**Deskripsi Endpoint:**
- Login dengan phone number dan password
- Kompatibel dengan OAuth2 standard
- Mengembalikan access token untuk authentikasi berikutnya

**Request Details:**

- **HTTP Method:** POST
- **URL Path:** `/api/v1/auth/login`
- **Authentication:** Not required
- **Status Codes:** 200 (OK), 401 (Unauthorized)

**Headers:**

```
Content-Type: application/x-www-form-urlencoded
```

**Request Body (Form Data):**

```
username=+6281234567890&password=StrongPassword123!
```

**Alternative: JSON Request**

Beberapa client dapat menggunakan format JSON:

```json
{
  "username": "+6281234567890",
  "password": "StrongPassword123!"
}
```

**Query Parameters:** None

**Response Details:**

**Success Response (Status 200):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIrNjI4MTIzNDU2Nzg5MCIsImV4cCI6MTcwMzAwMDAwMH0...",
  "token_type": "bearer"
}
```

**Error Response (Status 401):**

```json
{
  "detail": "Incorrect phone or password"
}
```

**Alternative Error Response:**

```json
{
  "detail": "User account is inactive"
}
```

**Validation Notes:**
- Phone dan password harus sesuai dengan yang terdaftar
- User harus dalam status active (`is_active = true`)
- Token berlaku selama 30 hari

---

### 3. Get Current User Info

**Deskripsi Endpoint:**
- Retrieve data user yang sedang login
- Tidak perlu memberikan user_id karena diambil dari JWT token

**Request Details:**

- **HTTP Method:** GET
- **URL Path:** `/api/v1/auth/me`
- **Authentication:** **Required** (Bearer Token)
- **Status Codes:** 200 (OK), 401 (Unauthorized)

**Headers:**

```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Query Parameters:** None

**Response Details:**

**Success Response (Status 200):**

```json
{
  "id": 1,
  "phone": "+6281234567890",
  "full_name": "Siti Aminah",
  "role": "ibu_hamil",
  "email": "siti@example.com",
  "profile_photo_url": null,
  "is_active": true,
  "is_verified": false,
  "created_at": "2024-12-15T10:30:00Z",
  "updated_at": "2024-12-15T10:30:00Z"
}
```

**Error Response (Status 401):**

```json
{
  "detail": "Could not validate credentials"
}
```

---

### 4. Register Super Admin

**Deskripsi Endpoint:**
- Registrasi akun super admin baru
- Super admin memiliki akses terbatas: dapat approve/reject registrasi puskesmas dan melihat data (read-only)
- Super admin TIDAK dapat mengelola perawat atau assign ibu hamil
- Endpoint ini sebaiknya hanya digunakan untuk setup awal sistem

**Request Details:**

- **HTTP Method:** POST
- **URL Path:** `/api/v1/auth/register/super-admin`
- **Authentication:** Not required
- **Status Codes:** 201 (Created), 400 (Bad Request)

**Headers:**

```
Content-Type: application/json
```

**Request Body:**

```json
{
  "email": "superadmin@wellmom.go.id",
  "phone": "+6281234567890",
  "password": "SuperSecurePass123!",
  "full_name": "Super Admin WellMom"
}
```

**Request Body Schema:**

| Field | Type | Required | Validation |
|-------|------|----------|-----------|
| email | string | Yes | Valid email format, unique |
| phone | string | Yes | 8-15 digits, optional leading '+', unique |
| password | string | Yes | Minimum 8 characters |
| full_name | string | Yes | Non-empty string |

**Response Details:**

**Success Response (Status 201):**

```json
{
  "user": {
    "id": 1,
    "email": "superadmin@wellmom.go.id",
    "phone": "+6281234567890",
    "full_name": "Super Admin WellMom",
    "role": "super_admin",
    "is_active": true,
    "is_verified": false
  },
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Error Response (Status 400):**

```json
{
  "detail": "Email already registered"
}
```

atau

```json
{
  "detail": "Phone number already registered"
}
```

**Catatan Penting:**
- Super admin hanya dapat approve/reject registrasi puskesmas
- Super admin dapat melihat data puskesmas, perawat, dan ibu hamil (read-only)
- Super admin TIDAK dapat mengelola perawat atau assign ibu hamil

---

### 5. Login Super Admin

**Deskripsi Endpoint:**
- Login endpoint khusus untuk super admin menggunakan email dan password
- Hanya user dengan role 'super_admin' yang dapat login melalui endpoint ini
- Mengembalikan JWT token beserta informasi user

**Request Details:**

- **HTTP Method:** POST
- **URL Path:** `/api/v1/auth/login/super-admin`
- **Authentication:** Not required
- **Status Codes:** 200 (OK), 401 (Unauthorized), 403 (Forbidden)

**Headers:**

```
Content-Type: application/json
```

**Request Body:**

```json
{
  "email": "superadmin@wellmom.go.id",
  "password": "SuperSecurePass123!"
}
```

**Request Body Schema:**

| Field | Type | Required | Validation |
|-------|------|----------|-----------|
| email | string | Yes | Valid email format |
| password | string | Yes | Password yang terdaftar |

**Response Details:**

**Success Response (Status 200):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "role": "super_admin",
  "user": {
    "id": 1,
    "email": "superadmin@wellmom.go.id",
    "full_name": "Super Admin WellMom"
  }
}
```

**Error Responses:**

**Status 401 (Unauthorized):**

```json
{
  "detail": "Email atau password salah"
}
```

atau

```json
{
  "detail": "Akun pengguna tidak aktif"
}
```

**Status 403 (Forbidden):**

```json
{
  "detail": "Akun ini bukan akun super admin"
}
```

**Akses Super Admin:**

- ✅ Dapat approve/reject registrasi puskesmas
- ✅ Dapat melihat data puskesmas, perawat, dan ibu hamil (read-only)
- ❌ TIDAK dapat mengelola perawat
- ❌ TIDAK dapat assign ibu hamil ke puskesmas atau perawat

---

## User Management Endpoints

### 1. List All Users

**Deskripsi Endpoint:**
- Admin dan super admin dapat melihat semua users
- Super admin memiliki akses read-only
- Support pagination dengan skip dan limit parameters

**Request Details:**

- **HTTP Method:** GET
- **URL Path:** `/api/v1/users`
- **Authentication:** **Required** (Bearer Token - Admin atau Super Admin)
- **Status Codes:** 200 (OK), 401 (Unauthorized), 403 (Forbidden)

**Headers:**

```
Authorization: Bearer <access_token>
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| skip | integer | 0 | Jumlah records yang skip (untuk pagination) |
| limit | integer | 100 | Maximum records yang akan dikembalikan |

**Example Request:**

```
GET /api/v1/users?skip=0&limit=10
```

**Response Details:**

**Success Response (Status 200):**

```json
[
  {
    "id": 1,
    "phone": "+6281234567890",
    "full_name": "Siti Aminah",
    "role": "ibu_hamil",
    "email": "siti@example.com",
    "profile_photo_url": null,
    "is_active": true,
    "is_verified": true
  },
  {
    "id": 2,
    "phone": "+6281111111111",
    "full_name": "Puskesmas Admin",
    "role": "puskesmas",
    "email": "admin@puskesmas.com",
    "profile_photo_url": null,
    "is_active": true,
    "is_verified": true
  }
]
```

**Error Response (Status 403):**

```json
{
  "detail": "Not authorized"
}
```

---

### 2. Get Current User Info (Duplicate Route)

**Deskripsi:** Same as `/api/v1/users/me` endpoint.

**Request Details:**

- **HTTP Method:** GET
- **URL Path:** `/api/v1/users/me`
- **Authentication:** **Required** (Bearer Token)
- **Status Codes:** 200 (OK), 401 (Unauthorized)

---

### 3. Get User by ID

**Deskripsi Endpoint:**
- Retrieve data user berdasarkan user ID
- Admin dapat melihat semua user
- Non-admin hanya bisa melihat data sendiri

**Request Details:**

- **HTTP Method:** GET
- **URL Path:** `/api/v1/users/{user_id}`
- **Authentication:** **Required** (Bearer Token)
- **Status Codes:** 200 (OK), 401 (Unauthorized), 403 (Forbidden), 404 (Not Found)

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_id | integer | Yes | User ID yang ingin diambil |

**Example Request:**

```
GET /api/v1/users/5
Authorization: Bearer <token>
```

**Response Details:**

**Success Response (Status 200):**

```json
{
  "id": 5,
  "phone": "+6281234567890",
  "full_name": "Siti Aminah",
  "role": "ibu_hamil",
  "email": "siti@example.com",
  "profile_photo_url": "https://cdn.example.com/photos/user5.jpg",
  "is_active": true,
  "is_verified": true
}
```

**Error Response (Status 404):**

```json
{
  "detail": "User not found"
}
```

**Error Response (Status 403):**

```json
{
  "detail": "Not authorized to view this user"
}
```

---

### 4. Update User

**Deskripsi Endpoint:**
- Update data user
- Admin dapat update semua user
- Non-admin hanya bisa update data sendiri

**Request Details:**

- **HTTP Method:** PATCH
- **URL Path:** `/api/v1/users/{user_id}`
- **Authentication:** **Required** (Bearer Token)
- **Status Codes:** 200 (OK), 400 (Bad Request), 401 (Unauthorized), 403 (Forbidden), 404 (Not Found)

**Headers:**

```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_id | integer | Yes | User ID yang ingin di-update |

**Request Body (All fields optional):**

```json
{
  "phone": "+628111222333",
  "full_name": "Siti Aminah Putri",
  "role": "ibu_hamil",
  "email": "siti.new@example.com",
  "profile_photo_url": "https://cdn.example.com/photos/user5_new.jpg",
  "is_active": true,
  "is_verified": true
}
```

**Request Body Schema:**

| Field | Type | Required | Validation |
|-------|------|----------|-----------|
| phone | string | No | 8-15 digits, optional leading '+', harus unik |
| full_name | string | No | Non-empty string |
| role | string | No | One of: admin, puskesmas, perawat, ibu_hamil, kerabat |
| email | string | No | Valid email format |
| profile_photo_url | string | No | Valid URL |
| is_active | boolean | No | True/False |
| is_verified | boolean | No | True/False |

**Response Details:**

**Success Response (Status 200):**

```json
{
  "id": 5,
  "phone": "+628111222333",
  "full_name": "Siti Aminah Putri",
  "role": "ibu_hamil",
  "email": "siti.new@example.com",
  "profile_photo_url": "https://cdn.example.com/photos/user5_new.jpg",
  "is_active": true,
  "is_verified": true
}
```

**Error Response (Status 400):**

```json
{
  "detail": "Phone number already in use"
}
```

---

### 5. Deactivate User (Soft Delete)

**Deskripsi Endpoint:**
- Deaktifkan/soft delete user
- Hanya super admin yang dapat melakukan ini
- User tidak dihapus, hanya di-set inactive

**Request Details:**

- **HTTP Method:** DELETE
- **URL Path:** `/api/v1/users/{user_id}`
- **Authentication:** **Required** (Bearer Token - Super Admin Only)
- **Status Codes:** 200 (OK), 401 (Unauthorized), 403 (Forbidden), 404 (Not Found)

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_id | integer | Yes | User ID yang ingin di-deactivate |

**Example Request:**

```
DELETE /api/v1/users/5
Authorization: Bearer <token>
```

**Response Details:**

**Success Response (Status 200):**

```json
{
  "message": "User deactivated successfully"
}
```

**Error Response (Status 404):**

```json
{
  "detail": "User not found"
}
```

---

## Puskesmas Endpoints

### 1. Register New Puskesmas

**Deskripsi Endpoint:**
- Registrasi puskesmas baru (kesehatan publik)
- Membuat satu akun admin puskesmas dengan role 'puskesmas'
- **Konsep Penting:** Setiap puskesmas hanya memiliki satu akun admin puskesmas
- Akun admin puskesmas digunakan untuk mengelola perawat dan assign ibu hamil ke perawat
- Initial status: "pending_approval" (menunggu approval super admin)
- Validasi phone untuk mencegah duplikat

**Request Details:**

- **HTTP Method:** POST
- **URL Path:** `/api/v1/puskesmas/register`
- **Authentication:** Not required
- **Status Codes:** 201 (Created), 400 (Bad Request)

**Headers:**

```
Content-Type: application/json
```

**Request Body:**

```json
{
  "name": "Puskesmas Sungai Penuh",
  "code": "PKM-ABC-123",
  "sk_number": "SK/2024/001",
  "sk_document_url": "https://cdn.example.com/docs/sk.pdf",
  "operational_license_number": "LIC-2024-001",
  "license_document_url": "https://cdn.example.com/docs/license.pdf",
  "npwp": "01234567890123456",
  "npwp_document_url": "https://cdn.example.com/docs/npwp.pdf",
  "accreditation_level": "Basic",
  "accreditation_cert_url": "https://cdn.example.com/docs/accred.pdf",
  "address": "Jl. Mawar No. 10, Sungai Penuh",
  "kelurahan": "Sungai Penuh",
  "kecamatan": "Sungai Penuh",
  "kabupaten": "Kerinci",
  "provinsi": "Jambi",
  "postal_code": "37114",
  "phone": "+6281234567890",
  "email": "admin@puskesmas.com",
  "location": [101.39, -2.06],
  "building_photo_url": "https://cdn.example.com/photos/building.jpg",
  "kepala_name": "Dr. Budi Santoso",
  "kepala_nip": "196512311987031001",
  "kepala_sk_number": "SK/KEPALA/2024/001",
  "kepala_sk_document_url": "https://cdn.example.com/docs/kepala_sk.pdf",
  "kepala_nik": "1965123119870310001",
  "kepala_ktp_url": "https://cdn.example.com/docs/ktp.pdf",
  "kepala_phone": "+6281234567890",
  "kepala_email": "budi@puskesmas.com",
  "verification_photo_url": "https://cdn.example.com/photos/verification.jpg",
  "total_perawat": 5,
  "operational_hours": "08:00-20:00",
  "facilities": "Imunisasi, KIA, Gizi, Kesehatan Lingkungan",
  "max_patients": 100,
  "current_patients": 25
}
```

**Request Body Schema:**

| Field | Type | Required | Validation |
|-------|------|----------|-----------|
| name | string | Yes | Nama puskesmas |
| code | string | Yes | Format: PKM-XXX-XXX |
| sk_number | string | Yes | Nomor SK |
| sk_document_url | string | Yes | Valid URL |
| operational_license_number | string | Yes | License number |
| license_document_url | string | Yes | Valid URL |
| phone | string | Yes | +62 atau 08, min 10 digit |
| email | string | Yes | Valid email |
| location | array | Yes | [longitude, latitude] |
| kepala_name | string | Yes | Nama kepala puskesmas |
| kepala_nik | string | Yes | Exactly 16 digits |
| kepala_phone | string | Yes | +62 atau 08, min 10 digit |
| kepala_email | string | Yes | Valid email |

**Response Details:**

**Success Response (Status 201):**

```json
{
  "puskesmas": {
    "id": 1,
    "name": "Puskesmas Sungai Penuh",
    "code": "PKM-ABC-123",
    "phone": "+6281234567890",
    "email": "admin@puskesmas.com",
    "address": "Jl. Mawar No. 10, Sungai Penuh",
    "kelurahan": "Sungai Penuh",
    "kecamatan": "Sungai Penuh",
    "kabupaten": "Kerinci",
    "provinsi": "Jambi",
    "registration_status": "pending",
    "is_active": true,
    "location": [101.39, -2.06],
    "total_perawat": 5,
    "max_patients": 100,
    "current_patients": 25
  },
  "message": "Registration submitted"
}
```

**Error Response (Status 400):**

```json
{
  "detail": "Phone already registered"
}
```

---

### 2. List Active Puskesmas

**Deskripsi Endpoint:**
- Public endpoint untuk melihat daftar puskesmas yang active dan sudah diapprove
- Pagination support

**Request Details:**

- **HTTP Method:** GET
- **URL Path:** `/api/v1/puskesmas`
- **Authentication:** Not required
- **Status Codes:** 200 (OK)

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| skip | integer | 0 | Jumlah records untuk di-skip |
| limit | integer | 100 | Maximum records yang dikembalikan |

**Example Request:**

```
GET /api/v1/puskesmas?skip=0&limit=10
```

**Response Details:**

**Success Response (Status 200):**

```json
[
  {
    "id": 1,
    "name": "Puskesmas Sungai Penuh",
    "code": "PKM-ABC-123",
    "phone": "+6281234567890",
    "email": "admin@puskesmas.com",
    "address": "Jl. Mawar No. 10, Sungai Penuh",
    "kelurahan": "Sungai Penuh",
    "kecamatan": "Sungai Penuh",
    "kabupaten": "Kerinci",
    "provinsi": "Jambi",
    "registration_status": "approved",
    "is_active": true,
    "location": [101.39, -2.06],
    "total_perawat": 5,
    "max_patients": 100,
    "current_patients": 25
  },
  {
    "id": 2,
    "name": "Puskesmas Kota Baru",
    "code": "PKM-KOT-001",
    "phone": "+6281111111111",
    "email": "admin@puskesmas2.com",
    "address": "Jl. Diponegoro No. 5",
    "kelurahan": "Kota Baru",
    "kecamatan": "Kota",
    "kabupaten": "Kerinci",
    "provinsi": "Jambi",
    "registration_status": "approved",
    "is_active": true,
    "location": [101.40, -2.07],
    "total_perawat": 8,
    "max_patients": 150,
    "current_patients": 45
  }
]
```

---

### 3. Get Puskesmas Detail

**Deskripsi Endpoint:**
- Get detail puskesmas berdasarkan ID
- Public endpoint

**Request Details:**

- **HTTP Method:** GET
- **URL Path:** `/api/v1/puskesmas/{puskesmas_id}`
- **Authentication:** Not required
- **Status Codes:** 200 (OK), 404 (Not Found)

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| puskesmas_id | integer | Yes | Puskesmas ID |

**Example Request:**

```
GET /api/v1/puskesmas/1
```

**Response Details:**

**Success Response (Status 200):**

```json
{
  "id": 1,
  "name": "Puskesmas Sungai Penuh",
  "code": "PKM-ABC-123",
  "sk_number": "SK/2024/001",
  "sk_document_url": "https://cdn.example.com/docs/sk.pdf",
  "operational_license_number": "LIC-2024-001",
  "license_document_url": "https://cdn.example.com/docs/license.pdf",
  "npwp": "01234567890123456",
  "accreditation_level": "Basic",
  "address": "Jl. Mawar No. 10, Sungai Penuh",
  "kelurahan": "Sungai Penuh",
  "kecamatan": "Sungai Penuh",
  "kabupaten": "Kerinci",
  "provinsi": "Jambi",
  "postal_code": "37114",
  "phone": "+6281234567890",
  "email": "admin@puskesmas.com",
  "location": [101.39, -2.06],
  "kepala_name": "Dr. Budi Santoso",
  "kepala_nip": "196512311987031001",
  "kepala_phone": "+6281234567890",
  "kepala_email": "budi@puskesmas.com",
  "registration_status": "approved",
  "is_active": true,
  "total_perawat": 5,
  "operational_hours": "08:00-20:00",
  "facilities": "Imunisasi, KIA, Gizi, Kesehatan Lingkungan",
  "max_patients": 100,
  "current_patients": 25
}
```

---

### 4. Find Nearest Puskesmas

**Deskripsi Endpoint:**
- Cari maksimal 5 puskesmas terdekat berdasarkan koordinat lokasi user
- Menggunakan PostGIS untuk geo-spatial query
- Hanya return puskesmas yang approved dan active
- Tidak ada batas radius, mengembalikan 5 puskesmas terdekat yang tersedia

**Request Details:**

- **HTTP Method:** GET
- **URL Path:** `/api/v1/puskesmas/nearest`
- **Authentication:** Not required
- **Status Codes:** 200 (OK), 400 (Bad Request)

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| latitude | float | Yes | Latitude koordinat user |
| longitude | float | Yes | Longitude koordinat user |

**Example Request:**

```
GET /api/v1/puskesmas/nearest?latitude=-2.06&longitude=101.39
```

**Response Details:**

**Success Response (Status 200):**

```json
[
  {
    "puskesmas": {
      "id": 1,
      "name": "Puskesmas Sungai Penuh",
      "code": "PKM-ABC-123",
      "phone": "+6281234567890",
      "email": "admin@puskesmas.com",
      "address": "Jl. Mawar No. 10, Sungai Penuh",
      "registration_status": "approved",
      "is_active": true
    },
    "distance_km": 0.5,
    "address": "Jl. Mawar No. 10, Sungai Penuh"
  },
  {
    "puskesmas": {
      "id": 2,
      "name": "Puskesmas Kota Baru",
      "code": "PKM-KOT-001",
      "phone": "+6281111111111",
      "email": "admin@puskesmas2.com",
      "address": "Jl. Diponegoro No. 5",
      "registration_status": "approved",
      "is_active": true
    },
    "distance_km": 2.3,
    "address": "Jl. Diponegoro No. 5"
  }
]
```

**Response Schema:**

| Field | Type | Description |
|-------|------|-------------|
| puskesmas | object | Detail lengkap puskesmas (PuskesmasResponse) |
| distance_km | float | Jarak dalam kilometer dari koordinat user |
| address | string | Alamat lengkap puskesmas (untuk akses cepat) |

**Notes:**
- Response mengembalikan maksimal 5 puskesmas terdekat
- Diurutkan berdasarkan jarak terdekat ke terjauh
- Hanya puskesmas dengan `registration_status: approved` yang ditampilkan

---

### 5. List Pending Registrations

**Deskripsi Endpoint:**
- Super admin-only endpoint untuk melihat daftar puskesmas yang pending approval
- Digunakan untuk approval workflow
- Response menyertakan seluruh dokumen yang diupload (SK, izin operasional, NPWP, akreditasi, foto gedung, foto verifikasi, KTP kepala) untuk keperluan review

**Request Details:**

- **HTTP Method:** GET
- **URL Path:** `/api/v1/puskesmas/pending`
- **Authentication:** **Required** (Bearer Token - Super Admin Only)
- **Status Codes:** 200 (OK), 401 (Unauthorized), 403 (Forbidden)

**Example Request:**

```
GET /api/v1/puskesmas/pending
Authorization: Bearer <token>
```

**Response Details:**

**Success Response (Status 200):**

```json
[
  {
    "id": 3,
    "name": "Puskesmas Baru",
    "code": "PKM-BAR-001",
    "sk_document_url": "https://cdn.example.com/docs/sk.pdf",
    "license_document_url": "https://cdn.example.com/docs/license.pdf",
    "npwp_document_url": "https://cdn.example.com/docs/npwp.pdf",
    "accreditation_cert_url": "https://cdn.example.com/docs/accred.pdf",
    "building_photo_url": "https://cdn.example.com/photos/building.jpg",
    "kepala_ktp_url": "https://cdn.example.com/docs/ktp.pdf",
    "verification_photo_url": "https://cdn.example.com/photos/verification.jpg",
    "phone": "+6282222222222",
    "email": "admin@puskesmas3.com",
    "address": "Jl. Baru No. 1",
    "registration_status": "pending",
    "is_active": true
  }
]
```

---

### 6. Approve Puskesmas Registration

**Deskripsi Endpoint:**
- Admin atau super admin approval untuk puskesmas registration
- Mengubah status dari "pending_approval" menjadi "approved"
- Mengirimkan notification ke admin user puskesmas
- **Akses:** Super admin

**Request Details:**

- **HTTP Method:** POST
- **URL Path:** `/api/v1/puskesmas/{puskesmas_id}/approve`
- **Authentication:** **Required** (Bearer Token - Admin atau Super Admin)
- **Status Codes:** 200 (OK), 401 (Unauthorized), 403 (Forbidden), 404 (Not Found)

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| puskesmas_id | integer | Yes | Puskesmas ID yang akan di-approve |

**Example Request:**

```
POST /api/v1/puskesmas/3/approve
Authorization: Bearer <token>
```

**Response Details:**

**Success Response (Status 200):**

```json
{
  "id": 3,
  "name": "Puskesmas Baru",
  "code": "PKM-BAR-001",
  "phone": "+6282222222222",
  "email": "admin@puskesmas3.com",
  "address": "Jl. Baru No. 1",
  "registration_status": "approved",
  "is_active": true,
  "location": [101.41, -2.08]
}
```

---

### 7. Reject Puskesmas Registration

**Deskripsi Endpoint:**
- Admin atau super admin rejection untuk puskesmas registration
- Mengubah status dari "pending_approval" menjadi "rejected"
- Harus menyertakan rejection reason
- Mengirimkan notification ke admin user puskesmas
- **Akses:** Super admin

**Request Details:**

- **HTTP Method:** POST
- **URL Path:** `/api/v1/puskesmas/{puskesmas_id}/reject`
- **Authentication:** **Required** (Bearer Token - Admin atau Super Admin)
- **Status Codes:** 200 (OK), 401 (Unauthorized), 403 (Forbidden), 404 (Not Found)

**Headers:**

```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| puskesmas_id | integer | Yes | Puskesmas ID yang akan di-reject |

**Request Body:**

```json
{
  "rejection_reason": "Dokumen SK tidak lengkap"
}
```

**Response Details:**

**Success Response (Status 200):**

```json
{
  "id": 3,
  "name": "Puskesmas Baru",
  "code": "PKM-BAR-001",
  "phone": "+6282222222222",
  "email": "admin@puskesmas3.com",
  "address": "Jl. Baru No. 1",
  "registration_status": "rejected",
  "is_active": true
}
```

---

### 8. Admin List Active Puskesmas (with stats)

**Deskripsi Endpoint:**
- Admin atau super admin dapat melihat list puskesmas yang sudah approved dan active
- Menyertakan agregasi jumlah ibu hamil aktif dan perawat aktif per puskesmas
- Super admin memiliki akses read-only

**Request Details:**

- **HTTP Method:** GET
- **URL Path:** `/api/v1/puskesmas/admin/active`
- **Authentication:** **Required** (Bearer Token - Admin atau Super Admin)
- **Status Codes:** 200 (OK), 401 (Unauthorized), 403 (Forbidden)

**Example Request:**

```
GET /api/v1/puskesmas/admin/active
Authorization: Bearer <token>
```

**Response Details:**

**Success Response (Status 200):**

```json
[
  {
    "id": 1,
    "name": "Puskesmas Sungai Penuh",
    "code": "PKM-ABC-123",
    "registration_status": "approved",
    "is_active": true,
    "active_ibu_hamil_count": 120,
    "active_perawat_count": 18,
    "total_perawat": 20,
    "phone": "+6281234567890",
    "email": "admin@puskesmas.com",
    "address": "Jl. Mawar No. 10, Sungai Penuh"
  }
]
```

---

### 9. Admin Get Puskesmas Detail (with stats)

**Deskripsi Endpoint:**
- Admin atau super admin dapat melihat detail puskesmas plus jumlah ibu hamil aktif dan perawat aktif
- Menyertakan seluruh dokumen legal dan data kepala puskesmas untuk audit
- Super admin memiliki akses read-only

**Request Details:**

- **HTTP Method:** GET
- **URL Path:** `/api/v1/puskesmas/admin/{puskesmas_id}`
- **Authentication:** **Required** (Bearer Token - Admin atau Super Admin)
- **Status Codes:** 200 (OK), 401 (Unauthorized), 403 (Forbidden), 404 (Not Found)

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| puskesmas_id | integer | Yes | ID puskesmas |

**Success Response (Status 200):**

```json
{
  "id": 1,
  "name": "Puskesmas Sungai Penuh",
  "code": "PKM-ABC-123",
  "registration_status": "approved",
  "is_active": true,
  "suspension_reason": null,
  "suspended_at": null,
  "sk_document_url": "https://cdn.example.com/docs/sk.pdf",
  "license_document_url": "https://cdn.example.com/docs/license.pdf",
  "npwp_document_url": "https://cdn.example.com/docs/npwp.pdf",
  "accreditation_cert_url": "https://cdn.example.com/docs/accred.pdf",
  "building_photo_url": "https://cdn.example.com/photos/building.jpg",
  "kepala_ktp_url": "https://cdn.example.com/docs/ktp.pdf",
  "verification_photo_url": "https://cdn.example.com/photos/verification.jpg",
  "active_ibu_hamil_count": 120,
  "active_perawat_count": 18,
  "admin_notes": "Perlu cek ulang alamat bisnis",
  "total_perawat": 20,
  "phone": "+6281234567890",
  "email": "admin@puskesmas.com",
  "address": "Jl. Mawar No. 10, Sungai Penuh"
}
```

---

### 10. Deactivate Puskesmas

**Deskripsi Endpoint:**
- Super admin-only untuk menonaktifkan puskesmas yang sedang aktif
- **Cascade Effects:**
  1. Semua ibu hamil yang ter-assign ke puskesmas ini akan kehilangan relasi (puskesmas_id = NULL, perawat_id = NULL)
  2. Semua perawat yang terdaftar di puskesmas ini akan otomatis terhapus (beserta akun usernya jika ada)
  3. Akun admin puskesmas akan dinonaktifkan (is_active = False)
  4. Puskesmas akan dinonaktifkan (is_active = False)
- Mengirim notifikasi ke admin user puskesmas

**Catatan Penting:**
- Ibu hamil yang kehilangan relasi harus memilih puskesmas aktif baru
- Perawat yang terhapus tidak dapat diakses lagi
- Admin puskesmas tidak dapat login setelah puskesmas dinonaktifkan

**Request Details:**

- **HTTP Method:** POST
- **URL Path:** `/api/v1/puskesmas/{puskesmas_id}/deactivate`
- **Authentication:** **Required** (Bearer Token - Super Admin Only)
- **Status Codes:** 200 (OK), 400 (Bad Request), 401 (Unauthorized), 403 (Forbidden), 404 (Not Found)

**Headers:**

```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| puskesmas_id | integer | Yes | ID puskesmas yang akan dinonaktifkan |

**Request Body:**

```json
{
  "reason": "Melanggar ketentuan operasional"
}
```

**Success Response (Status 200):**

```json
{
  "id": 1,
  "name": "Puskesmas Sungai Penuh",
  "registration_status": "approved",
  "is_active": false,
  "admin_notes": "[Deactivated] Melanggar ketentuan operasional"
}
```

**Error Response (Status 400):**

```json
{
  "detail": "Puskesmas sudah tidak aktif"
}
```

**Error Response (Status 403):**

```json
{
  "detail": "Not authorized. Hanya super admin yang dapat menonaktifkan puskesmas."
}
```

---

### 11. Reinstate Puskesmas

**Deskripsi Endpoint:**
- Super admin-only untuk mengembalikan puskesmas yang disuspend menjadi active/approved
- Membersihkan alasan suspend dan mencatat approval admin terakhir
- Mengirim notifikasi ke admin user puskesmas

**Request Details:**

- **HTTP Method:** POST
- **URL Path:** `/api/v1/puskesmas/{puskesmas_id}/reinstate`
- **Authentication:** **Required** (Bearer Token - Super Admin Only)
- **Status Codes:** 200 (OK), 401 (Unauthorized), 403 (Forbidden), 404 (Not Found)

**Example Request:**

```
POST /api/v1/puskesmas/1/reinstate
Authorization: Bearer <token>
```

**Success Response (Status 200):**

```json
{
  "id": 1,
  "name": "Puskesmas Sungai Penuh",
  "registration_status": "approved",
  "is_active": true,
  "suspension_reason": null,
  "suspended_at": null,
  "approved_at": "2025-01-10T10:00:00Z"
}
```

---

### 12. Assign Ibu Hamil ke Puskesmas

**Deskripsi Endpoint:**
- Menugaskan satu ibu hamil ke puskesmas tertentu secara manual
- **Konsep:** Setiap puskesmas memiliki satu akun admin puskesmas (role: 'puskesmas')
- Admin puskesmas dapat mengelola perawat dan assign ibu hamil ke perawat di puskesmasnya
- Dapat diakses oleh:
  - Admin puskesmas (hanya dapat assign ke puskesmas yang dikelolanya sendiri)
- **Catatan:** Super admin TIDAK dapat assign (hanya dapat approve/reject registrasi puskesmas)
- Puskesmas harus dalam status 'approved' dan aktif
- Setelah assign ke puskesmas, ibu hamil belum memiliki perawat yang menangani
- Mengirim notifikasi ke user ibu hamil

**Request Details:**

- **HTTP Method:** POST
- **URL Path:** `/api/v1/puskesmas/{puskesmas_id}/ibu-hamil/{ibu_id}/assign`
- **Authentication:** **Required** (Bearer Token - Puskesmas Admin Only)
- **Status Codes:** 200 (OK), 400 (Bad Request), 401 (Unauthorized), 403 (Forbidden), 404 (Not Found)

**Headers:**

```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| puskesmas_id | integer | Yes | ID puskesmas tujuan |
| ibu_id | integer | Yes | ID ibu hamil yang akan di-assign |

**Example Request:**

```
POST /api/v1/puskesmas/2/ibu-hamil/1/assign
Authorization: Bearer <token>
```

**Response Details:**

**Success Response (Status 200):**

```json
{
  "id": 1,
  "puskesmas_id": 2,
  "perawat_id": null,
  "user_id": 5,
  "nama_lengkap": "Siti Aminah",
  "nik": "3175091201850001",
  "date_of_birth": "1985-12-12",
  "address": "Jl. Mawar No. 10, RT 02 RW 05",
  "provinsi": "Jambi",
  "kota_kabupaten": "Kerinci",
  "kelurahan": "Sungai Penuh",
  "kecamatan": "Pesisir Bukit",
  "location": [101.3912, -2.0645],
  "emergency_contact_name": "Budi (Suami)",
  "emergency_contact_phone": "+6281298765432",
  "is_active": true,
  "assignment_date": "2025-01-10T10:30:00Z",
  "assignment_method": "manual"
}
```

**Error Responses:**

**Status 403 (Forbidden):**

```json
{
  "detail": "Not authorized"
}
```

**Status 404 (Not Found):**

```json
{
  "detail": "Puskesmas tidak ditemukan atau belum aktif"
}
```

atau

```json
{
  "detail": "Ibu Hamil not found"
}
```

---

### 13. Assign Ibu Hamil ke Perawat

**Deskripsi Endpoint:**
- Menugaskan satu ibu hamil ke perawat yang terdaftar di puskesmas tersebut
- **Konsep:** Setiap puskesmas memiliki satu akun admin puskesmas (role: 'puskesmas')
- Admin puskesmas dapat mengelola perawat dan assign ibu hamil ke perawat di puskesmasnya
- Dapat diakses oleh:
  - Super admin (TIDAK dapat assign, hanya dapat approve/reject registrasi puskesmas)
  - Admin puskesmas (hanya dapat assign untuk puskesmas yang dikelolanya sendiri)
- **Prasyarat:**
  - Ibu hamil HARUS sudah ter-assign ke puskesmas terlebih dahulu
  - Perawat HARUS terdaftar di puskesmas yang sama dengan ibu hamil
  - Perawat harus aktif dan memiliki kapasitas
- Otomatis menambah workload perawat
- Mengirim notifikasi ke user ibu hamil

**Request Details:**

- **HTTP Method:** POST
- **URL Path:** `/api/v1/puskesmas/{puskesmas_id}/ibu-hamil/{ibu_id}/assign-perawat/{perawat_id}`
- **Authentication:** **Required** (Bearer Token - Puskesmas Admin Only)
- **Status Codes:** 200 (OK), 400 (Bad Request), 401 (Unauthorized), 403 (Forbidden), 404 (Not Found)

**Headers:**

```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| puskesmas_id | integer | Yes | ID puskesmas |
| ibu_id | integer | Yes | ID ibu hamil yang akan di-assign |
| perawat_id | integer | Yes | ID perawat tujuan |

**Example Request:**

```
POST /api/v1/puskesmas/2/ibu-hamil/1/assign-perawat/3
Authorization: Bearer <token>
```

**Response Details:**

**Success Response (Status 200):**

```json
{
  "id": 1,
  "puskesmas_id": 2,
  "perawat_id": 3,
  "user_id": 5,
  "nama_lengkap": "Siti Aminah",
  "nik": "3175091201850001",
  "date_of_birth": "1985-12-12",
  "address": "Jl. Mawar No. 10, RT 02 RW 05",
  "provinsi": "Jambi",
  "kota_kabupaten": "Kerinci",
  "kelurahan": "Sungai Penuh",
  "kecamatan": "Pesisir Bukit",
  "location": [101.3912, -2.0645],
  "emergency_contact_name": "Budi (Suami)",
  "emergency_contact_phone": "+6281298765432",
  "is_active": true,
  "assignment_date": "2025-01-10T10:30:00Z",
  "assignment_method": "manual"
}
```

**Error Responses:**

**Status 400 (Bad Request):**

```json
{
  "detail": "Ibu hamil belum ter-assign ke puskesmas. Silakan assign ke puskesmas terlebih dahulu."
}
```

atau

```json
{
  "detail": "Ibu hamil tidak ter-assign ke puskesmas ini"
}
```

atau

```json
{
  "detail": "Perawat tidak aktif"
}
```

**Status 403 (Forbidden):**

```json
{
  "detail": "Not authorized"
}
```

atau

```json
{
  "detail": "Not authorized to assign for this puskesmas"
}
```

**Status 404 (Not Found):**

```json
{
  "detail": "Ibu Hamil not found"
}
```

atau

```json
{
  "detail": "Perawat tidak ditemukan atau tidak terdaftar di puskesmas ini"
}
```

atau

```json
{
  "detail": "Puskesmas tidak ditemukan atau belum aktif"
}
```

**Catatan Penting:**

1. **Alur yang Direkomendasikan:**
   - Pertama, assign ibu hamil ke puskesmas menggunakan endpoint `/puskesmas/{puskesmas_id}/ibu-hamil/{ibu_id}/assign`
   - Kemudian, assign ibu hamil ke perawat menggunakan endpoint ini

2. **Validasi:**
   - Admin puskesmas hanya dapat assign ibu hamil ke puskesmas yang dikelolanya
   - Ibu hamil harus sudah ter-assign ke puskesmas sebelum dapat di-assign ke perawat
   - Perawat harus terdaftar di puskesmas yang sama dengan ibu hamil

3. **Notifikasi:**
   - Setelah assign berhasil, sistem akan mengirim notifikasi ke user ibu hamil
   - Notifikasi berisi informasi puskesmas atau perawat yang ditugaskan

---

## Ibu Hamil Endpoints

### 1. Register Ibu Hamil with User

**Deskripsi Endpoint:**
- Registrasi ibu hamil baru lengkap dengan user account
- Mengumpulkan data lengkap ibu hamil termasuk identitas, data kehamilan, riwayat kesehatan, dan lokasi
- Jika user sudah ada, akan menggunakan existing user
- Auto-assign ke puskesmas terdekat jika location diberikan
- Otomatis membuat access token

**Request Details:**

- **HTTP Method:** POST
- **URL Path:** `/api/v1/ibu-hamil/register`
- **Authentication:** Not required
- **Status Codes:** 201 (Created), 400 (Bad Request)

**Headers:**

```
Content-Type: application/json
```

**Request Body:**

```json
{
  "user": {
    "phone": "+6281234567890",
    "password": "StrongPassword123!",
    "full_name": "Siti Aminah",
    "email": "siti@example.com"
  },
  "ibu_hamil": {
    "nama_lengkap": "Siti Aminah",
    "nik": "3175091201850001",
    "date_of_birth": "1985-12-12",
    "address": "Jl. Mawar No. 10",
    "provinsi": "Jambi",
    "kota_kabupaten": "Kerinci",
    "kelurahan": "Sungai Penuh",
    "kecamatan": "Pesisir Bukit",
    "rt_rw": "02/05",
    "location": [101.3912, -2.0645],
    "last_menstrual_period": "2024-12-01",
    "estimated_due_date": "2025-09-08",
    "usia_kehamilan": 8,
    "kehamilan_ke": 2,
    "jumlah_anak": 1,
    "jarak_kehamilan_terakhir": "2 tahun",
    "miscarriage_number": 0,
    "previous_pregnancy_complications": "Tidak ada",
    "pernah_caesar": false,
    "pernah_perdarahan_saat_hamil": false,
    "riwayat_kesehatan_ibu": {
      "darah_tinggi": false,
      "diabetes": false,
      "anemia": false,
      "penyakit_jantung": false,
      "asma": false,
      "penyakit_ginjal": false,
      "tbc_malaria": false
    },
    "emergency_contact_name": "Budi (Suami)",
    "emergency_contact_phone": "+6281234567890",
    "emergency_contact_relation": "Suami",
    "blood_type": "O+",
    "height_cm": 158.0,
    "pre_pregnancy_weight_kg": 55.0,
    "house_photo_url": "/files/rumah_ibu.jpg"
  }
}
```

**Request Body Schema:**

**User Object:**

| Field | Type | Required | Validation |
|-------|------|----------|-----------|
| phone | string | Yes | 8-15 digits, optional leading '+' |
| password | string | Yes | Minimum 8 characters |
| full_name | string | Yes | Non-empty string |
| email | string | No | Valid email format |

**IbuHamil Object:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| nama_lengkap | string | Yes | Nama lengkap ibu hamil |
| nik | string | Yes | Nomor Induk Kependudukan (16 digit) |
| date_of_birth | date | Yes | Tanggal lahir (YYYY-MM-DD) |
| address | string | Yes | Alamat lengkap |
| provinsi | string | No | Provinsi tempat tinggal |
| kota_kabupaten | string | No | Kota/Kabupaten tempat tinggal |
| kelurahan | string | No | Kelurahan/Desa |
| kecamatan | string | No | Kecamatan |
| rt_rw | string | No | RT/RW |
| location | array | Yes | [longitude, latitude] - Koordinat lokasi |
| last_menstrual_period | date | No | HPHT - Hari Pertama Haid Terakhir |
| estimated_due_date | date | No | HPL - Hari Perkiraan Lahir |
| usia_kehamilan | integer | No | Usia kehamilan dalam minggu |
| kehamilan_ke | integer | No | Kehamilan ke berapa (default: 1) |
| jumlah_anak | integer | No | Jumlah anak yang sudah dilahirkan (default: 0) |
| jarak_kehamilan_terakhir | string | No | Jarak kehamilan terakhir |
| miscarriage_number | integer | No | Jumlah keguguran (default: 0) |
| previous_pregnancy_complications | string | No | Komplikasi kehamilan sebelumnya |
| pernah_caesar | boolean | No | Apakah pernah Caesar (default: false) |
| pernah_perdarahan_saat_hamil | boolean | No | Apakah pernah perdarahan saat hamil (default: false) |
| riwayat_kesehatan_ibu | object | No | Riwayat kesehatan ibu (lihat schema di bawah) |
| emergency_contact_name | string | Yes | Nama kontak darurat |
| emergency_contact_phone | string | Yes | Nomor telepon kontak darurat |
| emergency_contact_relation | string | No | Hubungan dengan kontak darurat |
| blood_type | string | No | Golongan darah |
| height_cm | number | No | Tinggi badan dalam cm |
| pre_pregnancy_weight_kg | number | No | Berat badan sebelum hamil dalam kg |
| house_photo_url | string | No | URL foto rumah |

**Riwayat Kesehatan Ibu Object:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| darah_tinggi | boolean | false | Riwayat darah tinggi |
| diabetes | boolean | false | Riwayat diabetes |
| anemia | boolean | false | Riwayat anemia |
| penyakit_jantung | boolean | false | Riwayat penyakit jantung |
| asma | boolean | false | Riwayat asma |
| penyakit_ginjal | boolean | false | Riwayat penyakit ginjal |
| tbc_malaria | boolean | false | Riwayat TBC/Malaria |

**Response Details:**

**Success Response (Status 201):**

```json
{
  "ibu_hamil": {
    "id": 1,
    "user_id": 1,
    "nama_lengkap": "Siti Aminah",
    "nik": "3175091201850001",
    "date_of_birth": "1985-12-12",
    "age": 39,
    "puskesmas_id": 2,
    "perawat_id": null,
    "location": [101.3912, -2.0645],
    "address": "Jl. Mawar No. 10",
    "provinsi": "Jambi",
    "kota_kabupaten": "Kerinci",
    "kelurahan": "Sungai Penuh",
    "kecamatan": "Pesisir Bukit",
    "rt_rw": "02/05",
    "last_menstrual_period": "2024-12-01",
    "estimated_due_date": "2025-09-08",
    "usia_kehamilan": 8,
    "kehamilan_ke": 2,
    "jumlah_anak": 1,
    "jarak_kehamilan_terakhir": "2 tahun",
    "miscarriage_number": 0,
    "previous_pregnancy_complications": "Tidak ada",
    "pernah_caesar": false,
    "pernah_perdarahan_saat_hamil": false,
    "riwayat_kesehatan_ibu": {
      "darah_tinggi": false,
      "diabetes": false,
      "anemia": false,
      "penyakit_jantung": false,
      "asma": false,
      "penyakit_ginjal": false,
      "tbc_malaria": false
    },
    "emergency_contact_name": "Budi (Suami)",
    "emergency_contact_phone": "+6281234567890",
    "emergency_contact_relation": "Suami",
    "blood_type": "O+",
    "height_cm": 158.0,
    "pre_pregnancy_weight_kg": 55.0,
    "house_photo_url": "/files/rumah_ibu.jpg",
    "is_active": true,
    "created_at": "2025-01-01T10:00:00Z",
    "updated_at": "2025-01-01T10:00:00Z"
  },
  "user": {
    "id": 1,
    "phone": "+6281234567890",
    "full_name": "Siti Aminah",
    "role": "ibu_hamil",
    "email": "siti@example.com",
    "is_active": true,
    "is_verified": false
  },
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "assignment": {
    "puskesmas": {
      "id": 2,
      "name": "Puskesmas Sungai Penuh",
      "code": "PKM-ABC-123",
      "registration_status": "approved",
      "is_active": true
    },
    "distance_km": 0.5
  }
}
```

**Error Response Examples:**

Status 400 - NIK Already Exists:
```json
{
  "detail": "NIK already registered"
}
```

Status 400 - Invalid Location:
```json
{
  "detail": "Location must be a (longitude, latitude) tuple"
}
```

---

### 2. Get My Profile (Current Ibu Hamil)

**Deskripsi Endpoint:**
- Get profile ibu hamil yang sedang login
- Juga bisa diakses oleh kerabat yang linked

**Request Details:**

- **HTTP Method:** GET
- **URL Path:** `/api/v1/ibu-hamil/me`
- **Authentication:** **Required** (Bearer Token)
- **Status Codes:** 200 (OK), 401 (Unauthorized), 404 (Not Found)

**Example Request:**

```
GET /api/v1/ibu-hamil/me
Authorization: Bearer <token>
```

**Response Details:**

**Success Response (Status 200):**

```json
{
  "id": 1,
  "user_id": 1,
  "nama_lengkap": "Siti Aminah",
  "nik": "3175091201850001",
  "date_of_birth": "1985-12-12",
  "puskesmas_id": 2,
  "perawat_id": null,
  "location": [101.3912, -2.0645],
  "address": "Jl. Mawar No. 10",
  "provinsi": "Jambi",
  "kota_kabupaten": "Kerinci",
  "emergency_contact_name": "Budi (Suami)",
  "emergency_contact_phone": "+6281234567890",
  "is_active": true
}
```

---

### 3. Get Ibu Hamil Detail

**Deskripsi Endpoint:**
- Get detail ibu hamil berdasarkan ID
- Authorized untuk: Admin, Perawat assigned, Puskesmas admin, Kerabat linked, atau pemilik akun

**Request Details:**

- **HTTP Method:** GET
- **URL Path:** `/api/v1/ibu-hamil/{ibu_id}`
- **Authentication:** **Required** (Bearer Token)
- **Status Codes:** 200 (OK), 401 (Unauthorized), 403 (Forbidden), 404 (Not Found)

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| ibu_id | integer | Yes | Ibu Hamil ID |

**Example Request:**

```
GET /api/v1/ibu-hamil/1
Authorization: Bearer <token>
```

**Response Details:**

**Success Response (Status 200):**

```json
{
  "id": 1,
  "user_id": 1,
  "nama_lengkap": "Siti Aminah",
  "nik": "3175091201850001",
  "date_of_birth": "1985-12-12",
  "puskesmas_id": 2,
  "perawat_id": 3,
  "location": [101.3912, -2.0645],
  "address": "Jl. Mawar No. 10",
  "provinsi": "Jambi",
  "kota_kabupaten": "Kerinci",
  "kelurahan": "Sungai Penuh",
  "emergency_contact_name": "Budi (Suami)",
  "emergency_contact_phone": "+6281234567890",
  "is_active": true
}
```

---

### 4. Update Ibu Hamil Profile

**Deskripsi Endpoint:**
- Update profile ibu hamil
- Authorized untuk: Admin, pemilik akun, perawat assigned, atau admin puskesmas
- Jika location diubah dan tidak ada explicit puskesmas_id, akan auto-assign ulang

**Request Details:**

- **HTTP Method:** PATCH
- **URL Path:** `/api/v1/ibu-hamil/{ibu_id}`
- **Authentication:** **Required** (Bearer Token)
- **Status Codes:** 200 (OK), 400 (Bad Request), 401 (Unauthorized), 403 (Forbidden), 404 (Not Found)

**Headers:**

```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| ibu_id | integer | Yes | Ibu Hamil ID |

**Request Body (All fields optional):**

```json
{
  "usia_kehamilan": 12,
  "estimated_due_date": "2025-09-15",
  "location": [101.40, -2.07],
  "address": "Jl. Mawar No. 15",
  "puskesmas_id": 3,
  "riwayat_kesehatan_ibu": {
    "darah_tinggi": true,
    "diabetes": false,
    "anemia": true,
    "penyakit_jantung": false,
    "asma": false,
    "penyakit_ginjal": false,
    "tbc_malaria": false
  }
}
```

**Response Details:**

**Success Response (Status 200):**

```json
{
  "id": 1,
  "user_id": 1,
  "nama_lengkap": "Siti Aminah",
  "nik": "3175091201850001",
  "puskesmas_id": 3,
  "perawat_id": 3,
  "usia_kehamilan": 12,
  "estimated_due_date": "2025-09-15",
  "location": [101.40, -2.07],
  "address": "Jl. Mawar No. 15",
  "riwayat_kesehatan_ibu": {
    "darah_tinggi": true,
    "diabetes": false,
    "anemia": true,
    "penyakit_jantung": false,
    "asma": false,
    "penyakit_ginjal": false,
    "tbc_malaria": false
  },
  "is_active": true
}
```

---

### 5. List Unassigned Ibu Hamil

**Deskripsi Endpoint:**
- List ibu hamil yang belum ter-assign ke puskesmas
- Hanya admin atau puskesmas admin yang dapat access
- Berguna untuk admin puskesmas mencari ibu hamil untuk di-assign

**Request Details:**

- **HTTP Method:** GET
- **URL Path:** `/api/v1/ibu-hamil/unassigned`
- **Authentication:** **Required** (Bearer Token - Admin/Puskesmas Only)
- **Status Codes:** 200 (OK), 401 (Unauthorized), 403 (Forbidden)

**Example Request:**

```
GET /api/v1/ibu-hamil/unassigned
Authorization: Bearer <token>
```

**Response Details:**

**Success Response (Status 200):**

```json
[
  {
    "id": 2,
    "user_id": 2,
    "nama_lengkap": "Nur Azizah",
    "nik": "3175091201850002",
    "puskesmas_id": null,
    "perawat_id": null,
    "location": [101.50, -2.10],
    "address": "Jl. Kenanga No. 5",
    "emergency_contact_name": "Ahmad",
    "emergency_contact_phone": "+6281777777777",
    "is_active": true
  }
]
```

---

### 6. Manual Assign to Puskesmas

**Deskripsi Endpoint:**
- Manual assignment ibu hamil ke puskesmas
- Admin atau puskesmas admin dapat melakukan ini
- Optional memilih perawat
- Cek kapasitas puskesmas dan perawat
- Kirim notification ke ibu hamil

**Request Details:**

- **HTTP Method:** POST
- **URL Path:** `/api/v1/ibu-hamil/{ibu_id}/assign`
- **Authentication:** **Required** (Bearer Token - Admin/Puskesmas)
- **Status Codes:** 200 (OK), 400 (Bad Request), 401 (Unauthorized), 403 (Forbidden), 404 (Not Found)

**Headers:**

```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| ibu_id | integer | Yes | Ibu Hamil ID |

**Request Body:**

```json
{
  "puskesmas_id": 2,
  "perawat_id": 3
}
```

**Request Body Schema:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| puskesmas_id | integer | Yes | Target puskesmas |
| perawat_id | integer | No | Target perawat (optional) |

**Response Details:**

**Success Response (Status 200):**

```json
{
  "id": 1,
  "user_id": 1,
  "puskesmas_id": 2,
  "perawat_id": 3,
  "nik": "3175091201850001",
  "location": [101.39, -2.06],
  "address": "Jl. Mawar No. 10",
  "emergency_contact_name": "Budi",
  "emergency_contact_phone": "+6281999999999",
  "is_active": true
}
```

**Error Response (Status 400):**

```json
{
  "detail": "Puskesmas capacity is full"
}
```

**Alternative Error Response:**

```json
{
  "detail": "Perawat sudah penuh"
}
```

---

### 7. Auto-Assign to Nearest Puskesmas

**Deskripsi Endpoint:**
- Auto-assignment ke puskesmas terdekat
- Admin atau ibu bersangkutan dapat melakukan ini
- Cek kapasitas dan status puskesmas
- Return puskesmas yang di-assign beserta jarak

**Request Details:**

- **HTTP Method:** POST
- **URL Path:** `/api/v1/ibu-hamil/{ibu_id}/auto-assign`
- **Authentication:** **Required** (Bearer Token)
- **Status Codes:** 200 (OK), 401 (Unauthorized), 403 (Forbidden), 404 (Not Found)

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| ibu_id | integer | Yes | Ibu Hamil ID |

**Example Request:**

```
POST /api/v1/ibu-hamil/1/auto-assign
Authorization: Bearer <token>
```

**Response Details:**

**Success Response (Status 200):**

```json
{
  "ibu_hamil": {
    "id": 1,
    "user_id": 1,
    "puskesmas_id": 2,
    "perawat_id": 3,
    "nik": "3175091201850001",
    "location": [101.39, -2.06],
    "address": "Jl. Mawar No. 10",
    "emergency_contact_name": "Budi",
    "emergency_contact_phone": "+6281999999999",
    "is_active": true
  },
  "puskesmas": {
    "id": 2,
    "name": "Puskesmas Sungai Penuh",
    "code": "PKM-ABC-123",
    "registration_status": "approved",
    "is_active": true
  },
  "distance_km": 0.5
}
```

---

### 8. List Ibu Hamil by Puskesmas

**Deskripsi Endpoint:**
- Daftar ibu hamil per puskesmas
- Authorized untuk: Admin, admin puskesmas, atau perawat di puskesmas
- Support pagination

**Request Details:**

- **HTTP Method:** GET
- **URL Path:** `/api/v1/ibu-hamil/by-puskesmas/{puskesmas_id}`
- **Authentication:** **Required** (Bearer Token)
- **Status Codes:** 200 (OK), 401 (Unauthorized), 403 (Forbidden), 404 (Not Found)

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| puskesmas_id | integer | Yes | Puskesmas ID |

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| skip | integer | 0 | Jumlah records untuk di-skip |
| limit | integer | 100 | Maximum records yang dikembalikan |

**Example Request:**

```
GET /api/v1/ibu-hamil/by-puskesmas/2?skip=0&limit=10
Authorization: Bearer <token>
```

**Response Details:**

**Success Response (Status 200):**

```json
[
  {
    "id": 1,
    "user_id": 1,
    "puskesmas_id": 2,
    "perawat_id": 3,
    "nik": "3175091201850001",
    "location": [101.39, -2.06],
    "address": "Jl. Mawar No. 10",
    "emergency_contact_name": "Budi",
    "emergency_contact_phone": "+6281999999999",
    "is_active": true
  },
  {
    "id": 4,
    "user_id": 4,
    "puskesmas_id": 2,
    "perawat_id": 4,
    "nik": "3175091201850004",
    "location": [101.35, -2.08],
    "address": "Jl. Dahlia No. 7",
    "emergency_contact_name": "Udin",
    "emergency_contact_phone": "+6281666666666",
    "is_active": true
  }
]
```

---

### 9. List Ibu Hamil by Perawat

**Deskripsi Endpoint:**
- Daftar ibu hamil per perawat
- Authorized untuk: Admin, super admin (read-only), perawat terkait, atau admin puskesmas yang menaungi perawat

**Request Details:**

- **HTTP Method:** GET
- **URL Path:** `/api/v1/ibu-hamil/by-perawat/{perawat_id}`
- **Authentication:** **Required** (Bearer Token)
- **Status Codes:** 200 (OK), 401 (Unauthorized), 403 (Forbidden), 404 (Not Found)

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| perawat_id | integer | Yes | Perawat ID |

**Example Request:**

```
GET /api/v1/ibu-hamil/by-perawat/3
Authorization: Bearer <token>
```

**Response Details:**

**Success Response (Status 200):**

```json
[
  {
    "id": 1,
    "user_id": 1,
    "puskesmas_id": 2,
    "perawat_id": 3,
    "nik": "3175091201850001",
    "location": [101.39, -2.06],
    "address": "Jl. Mawar No. 10",
    "emergency_contact_name": "Budi",
    "emergency_contact_phone": "+6281999999999",
    "is_active": true
  },
  {
    "id": 5,
    "user_id": 5,
    "puskesmas_id": 2,
    "perawat_id": 3,
    "nik": "3175091201850005",
    "location": [101.38, -2.05],
    "address": "Jl. Melati No. 3",
    "emergency_contact_name": "Sardi",
    "emergency_contact_phone": "+6281555555555",
    "is_active": true
  }
]
```

---

## Perawat (Nurse) Endpoints

### 1. Generate Akun Perawat oleh Puskesmas

**Deskripsi Endpoint:**
- Puskesmas admin membuat akun perawat baru (membuat user + profil perawat)
- Sistem otomatis membuat token aktivasi dan mengirim email aktivasi ke perawat
- User dan profil perawat diset inactive sampai perawat menyelesaikan aktivasi

**Request Details:**

- **HTTP Method:** POST
- **URL Path:** `/api/v1/perawat/generate`
- **Authentication:** **Required** (Bearer Token - Role `puskesmas`)
- **Status Codes:** 201 (Created), 400 (Bad Request), 401/403/404

**Headers:**

```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**

```json
{
  "full_name": "Siti Nurhaliza",
  "phone": "+6281234567890",
  "email": "siti.nurhaliza@example.com",
  "nik": "1234567890123456",
  "nip": "198501012015011001",
  "job_title": "Bidan",
  "license_number": "STR-1234567890",
  "max_patients": 15
}
```

**Response Details (Status 201):**

```json
{
  "perawat": {
    "id": 12,
    "user_id": 30,
    "puskesmas_id": 5,
    "created_by_user_id": 8,
    "nik": "1234567890123456",
    "nip": "198501012015011001",
    "job_title": "Bidan",
    "license_number": "STR-1234567890",
    "max_patients": 15,
    "current_patients": 0,
    "status": "active",
    "is_available": false,
    "is_active": false,
    "is_verified": false,
    "full_name": "Siti Nurhaliza",
    "phone": "+6281234567890",
    "email": "siti.nurhaliza@example.com"
  },
  "activation_link": "https://app.wellmom.com/perawat/activate?token=abc123"
}
```

**Catatan:**
- Sistem mengirim email aktivasi ke alamat email perawat yang diberikan.
- Kode sementara (password sementara) tidak dikirim; perawat diwajibkan set password baru melalui tautan aktivasi.
- Akun tetap inactive sampai perawat menyelesaikan aktivasi.

---

### 2. Resend Email Aktivasi Perawat

**Deskripsi Endpoint:**
- Mengirim ulang email aktivasi untuk user perawat tertentu (misalnya jika email pertama tidak diterima)

**Request Details:**

- **HTTP Method:** POST
- **URL Path:** `/api/v1/perawat/activation/request`
- **Authentication:** **Recommended** (Admin/Puskesmas); membutuhkan `user_id` perawat
- **Status Codes:** 200 (OK), 400, 404, 500

**Request Body:**

```json
{
  "user_id": 30
}
```

**Response Details (Status 200):**

```json
{
  "message": "Verification email sent",
  "activation_link": "https://app.wellmom.com/perawat/activate?token=abc123"
}
```

---

### 3. Aktivasi Akun Perawat (Langkah Frontend)

Flow aktivasi setelah email diterima:
1) **Verify token:** `POST /api/v1/perawat/activation/verify` dengan payload `{ "token": "..." }`
2) **Set password:** `POST /api/v1/perawat/activation/set-password` dengan payload `{ "token": "...", "new_password": "StrongPass!234" }`
3) **Upload foto profil (opsional kini):** `POST /api/v1/perawat/activation/complete-profile` dengan payload `{ "token": "...", "profile_photo_url": "https://..." }`
4) **Terima syarat & aktifkan:** `POST /api/v1/perawat/activation/accept-terms` dengan payload `{ "token": "..." }`

Setelah langkah 4 berhasil, user dan profil perawat menjadi aktif (`is_active=true`, `is_verified=true`).

---

## Error Handling

### HTTP Status Codes

| Code | Name | Description |
|------|------|-------------|
| 200 | OK | Request berhasil |
| 201 | Created | Resource berhasil dibuat |
| 400 | Bad Request | Request invalid (validation error) |
| 401 | Unauthorized | Authentication required atau invalid |
| 403 | Forbidden | Tidak punya authorization/permission |
| 404 | Not Found | Resource tidak ditemukan |
| 500 | Internal Server Error | Server error |

### Error Response Format

Semua error responses menggunakan format berikut:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Error Scenarios

#### 1. Invalid Token

```json
{
  "detail": "Could not validate credentials"
}
```

**Action:** Login kembali untuk mendapatkan token baru

#### 2. Expired Token

```json
{
  "detail": "Could not validate credentials"
}
```

**Action:** Refresh token atau login kembali

#### 3. Permission Denied

```json
{
  "detail": "Not authorized"
}
```

**Action:** Gunakan account dengan role yang tepat

#### 4. Resource Not Found

```json
{
  "detail": "User not found"
}
```

**Action:** Verifikasi ID yang digunakan

#### 5. Validation Error

```json
{
  "detail": "Phone number already registered"
}
```

**Action:** Gunakan data yang valid sesuai validasi rules

---

## Response Codes

### Standard Success Codes

| Endpoint | Method | Success Code |
|----------|--------|--------------|
| / | GET | 200 |
| /health | GET | 200 |
| /db-test | GET | 200 |
| /postgis-test | GET | 200 |
| /api/v1/auth/register | POST | 201 |
| /api/v1/auth/login | POST | 200 |
| /api/v1/auth/me | GET | 200 |
| /api/v1/users | GET | 200 |
| /api/v1/users/{id} | GET | 200 |
| /api/v1/users/{id} | PATCH | 200 |
| /api/v1/users/{id} | DELETE | 200 |
| /api/v1/puskesmas/register | POST | 201 |
| /api/v1/puskesmas | GET | 200 |
| /api/v1/puskesmas/{id} | GET | 200 |
| /api/v1/puskesmas/nearest | GET | 200 |
| /api/v1/ibu-hamil/register | POST | 201 |
| /api/v1/ibu-hamil/me | GET | 200 |
| /api/v1/ibu-hamil/{id} | GET | 200 |
| /api/v1/ibu-hamil/{id} | PATCH | 200 |

---

## Validation Rules

### Phone Number Format

- **Pattern:** Optional leading `+`, followed by 8-15 digits
- **Examples:** `+6281234567890`, `081234567890`
- **Indonesian Specific:** Can start with `+62` or `08` followed by 10-13 digits

### Email Format

- **Pattern:** Standard email format (RFC 5322)
- **Example:** `user@example.com`

### Password Requirements

- **Minimum Length:** 8 characters
- **Recommended:** Mix of uppercase, lowercase, numbers, and special characters
- **Example:** `StrongPass!234`

### NIK (Indonesian ID) Format

- **Pattern:** Exactly 16 digits
- **Example:** `3175091201850001`

### Puskesmas Code Format

- **Pattern:** `PKM-XXX-XXX` (PKM prefix, 2 groups of 3 alphanumeric characters)
- **Example:** `PKM-ABC-123`

### Location Format

- **Format:** Array dengan 2 elemen float: `[longitude, latitude]`
- **Longitude Range:** -180 to 180
- **Latitude Range:** -90 to 90
- **Example:** `[101.39, -2.06]` (Kerinci, Jambi)

### Role Validation

- **Allowed Roles:** `admin`, `puskesmas`, `perawat`, `ibu_hamil`, `kerabat`
- **Default for Ibu Hamil Registration:** `ibu_hamil`

### Registration Status

- **For Puskesmas:**
  - `pending`: Menunggu approval admin
  - `approved`: Sudah disetujui
  - `rejected`: Ditolak dengan alasan
  - `suspended`: Di-suspend

---

## Rate Limiting & Pagination

### Pagination

Endpoints yang support pagination menggunakan query parameters:

```
GET /api/v1/users?skip=0&limit=10
```

- **skip:** Jumlah records untuk di-skip (default: 0)
- **limit:** Maximum records yang dikembalikan (default: 100)

### Response Structure untuk List

```json
[
  { "id": 1, "name": "Item 1" },
  { "id": 2, "name": "Item 2" }
]
```

---

## Best Practices

### 1. Token Management

- **Store Token Securely:** Simpan token di secure storage (bukan localStorage untuk sensitive apps)
- **Refresh Strategy:** Request token baru 1-2 hari sebelum expiry
- **Logout:** Clear token dari storage saat user logout

### 2. Error Handling

- **Always Check Status Code:** Verify HTTP status code sebelum parse response
- **Handle Timeouts:** Implement retry logic untuk network issues
- **User Feedback:** Tampilkan meaningful error messages ke user

### 3. Location Data

- **Always Validate:** Verifikasi koordinat sebelum submit
- **GPS Accuracy:** Untuk production, gunakan GPS yang accurate
- **Mock Data Testing:** Gunakan koordinat Kerinci/Jambi untuk testing: `[101.39, -2.06]`

### 4. Request/Response

- **Always Include Headers:** Content-Type dan Authorization (jika required)
- **Validate Input:** Validate di frontend sebelum mengirim ke backend
- **Handle Edge Cases:** Plan untuk cases seperti missing optional fields

---

## API SDK Recommendations

Untuk integrasi yang lebih mudah, pertimbangkan menggunakan:

- **JavaScript/TypeScript:** axios, fetch API
- **Python:** requests, httpx
- **Mobile:** Retrofit (Android), Alamofire (iOS), dio (Flutter)

### Example using cURL

```bash
# Register
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+6281234567890",
    "password": "StrongPassword123!",
    "full_name": "Siti Aminah",
    "role": "ibu_hamil"
  }'

# Login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -d "username=+6281234567890&password=StrongPassword123!"

# Get Profile with Token
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer <access_token>"
```

---

## 📑 API Endpoints Summary

Berikut adalah rangkuman lengkap semua API endpoints yang tersedia di WellMom Backend:

### Health Check Endpoints

1. **Get Root Endpoint** : Endpoint root untuk verifikasi API sedang berjalan dan mendapatkan informasi dasar
2. **Health Check** : Verifikasi API health status untuk monitoring dan load balancer checks
3. **Database Connection Test** : Test koneksi database dan verifikasi database sudah tersedia
4. **PostGIS Extension Test** : Test PostGIS extension untuk geographic dan location queries

### Authentication Endpoints

5. **Register New User** : Registrasi user baru dengan phone, password, full_name, dan role
6. **Login User** : Login dengan phone number dan password, mengembalikan JWT access token
7. **Get Current User Info** : Retrieve data user yang sedang login dari JWT token

### User Management Endpoints

8. **List All Users** : Melihat daftar semua users (super admin only) dengan pagination support
9. **Get Current User Info** : Endpoint duplikat untuk mengambil profile user yang sedang login
10. **Get User by ID** : Retrieve data user berdasarkan user ID (admin atau self access)
11. **Update User** : Update data user seperti phone, full_name, email, dan profile photo
12. **Deactivate User (Soft Delete)** : Deaktifkan user tanpa menghapus data dari database

### Puskesmas (Health Center) Endpoints

13. **Register New Puskesmas** : Registrasi puskesmas baru dengan membuat user linked role 'puskesmas'
14. **List Active Puskesmas** : Public endpoint untuk melihat daftar puskesmas yang active dan approved
15. **Get Puskesmas Detail** : Get detail puskesmas berdasarkan ID dengan informasi lengkap
16. **Find Nearest Puskesmas** : Cari maksimal 5 puskesmas terdekat berdasarkan koordinat latitude/longitude
17. **List Pending Registrations** : Admin atau super admin dapat melihat daftar puskesmas yang pending approval
18. **Approve Puskesmas Registration** : Admin atau super admin approval untuk puskesmas registration dengan mengirim notification
19. **Reject Puskesmas Registration** : Admin atau super admin rejection untuk puskesmas registration dengan alasan penolakan
20. **Admin List Active Puskesmas (with stats)** : Admin atau super admin dapat melihat list puskesmas yang sudah approved dan active dengan agregasi jumlah ibu hamil dan perawat
21. **Admin Get Puskesmas Detail (with stats)** : Admin atau super admin dapat melihat detail puskesmas plus jumlah ibu hamil aktif dan perawat aktif
22. **Deactivate Puskesmas** : Super admin-only untuk menonaktifkan puskesmas yang sedang aktif dengan cascade effects
23. **Reinstate Puskesmas** : Super admin-only untuk mengembalikan puskesmas yang disuspend menjadi active/approved
24. **Assign Ibu Hamil ke Puskesmas** : Menugaskan satu ibu hamil ke puskesmas tertentu (admin atau puskesmas admin, super admin tidak dapat assign)
25. **Assign Ibu Hamil ke Perawat** : Menugaskan satu ibu hamil ke perawat yang terdaftar di puskesmas tersebut (admin atau puskesmas admin, super admin tidak dapat assign)

### Ibu Hamil (Pregnant Women) Endpoints

26. **Register Ibu Hamil with User** : Registrasi ibu hamil baru lengkap dengan user account dan auto-assign
27. **Get My Profile (Current Ibu Hamil)** : Get profile ibu hamil yang sedang login atau kerabat yang linked
28. **Get Ibu Hamil Detail** : Get detail ibu hamil berdasarkan ID dengan authorization check
29. **Update Ibu Hamil Profile** : Update profile ibu hamil dengan auto-assign ulang jika location berubah
30. **List Unassigned Ibu Hamil** : List ibu hamil yang belum ter-assign ke puskesmas (super admin/puskesmas only)
31. **Manual Assign to Puskesmas** : Manual assignment ibu hamil ke puskesmas dengan optional perawat selection
32. **Auto-Assign to Nearest Puskesmas** : Auto-assignment ibu hamil ke puskesmas terdekat dengan cek kapasitas
33. **List Ibu Hamil by Puskesmas** : Daftar ibu hamil per puskesmas dengan pagination support
34. **List Ibu Hamil by Perawat** : Daftar ibu hamil per perawat/nurse dengan authorization check

---

### Statistik API

- **Total Endpoints:** 35 API endpoints
- **Health Check:** 4 endpoints
- **Authentication:** 3 endpoints
- **User Management:** 5 endpoints
- **Puskesmas Management:** 7 endpoints
- **Ibu Hamil Management:** 9 endpoints

### Authentication Requirements

- **Public Endpoints:** 7 (Health checks, Register, Login, List Puskesmas, Get Puskesmas Detail, Find Nearest)
- **Authenticated Endpoints:** 21 (Memerlukan JWT Bearer Token)
- **Super Admin Only:** 5 (List Users, List Pending, Approve, Reject, Deactivate)
- **Role-based Access:** 13 (Puskesmas admin, Perawat, Ibu Hamil, Kerabat)

---

## Support & Contact

Untuk pertanyaan atau issues, silakan hubungi tim development WellMom.

**Last Updated:** December 15, 2024  
**API Version:** 1.0.0
