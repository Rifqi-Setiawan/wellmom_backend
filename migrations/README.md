# Database Migrations

## Create Forum Tables

Migration ini membuat tables untuk fitur forum diskusi:
- `posts`: Tabel untuk postingan forum
- `post_likes`: Tabel untuk like pada postingan
- `post_replies`: Tabel untuk reply/comment pada postingan

### Cara Menjalankan Migration di VPS

#### Opsi 1: Via Docker (RECOMMENDED)

```bash
# Pastikan container PostgreSQL berjalan
docker ps | grep wellmom_postgres

# Jalankan migration
docker exec -i wellmom_postgres psql -U wellmom -d wellmom_db < migrations/create_forum_tables.sql
```

Atau menggunakan script:
```bash
bash migrations/create_forum_tables_docker.sh
```

#### Opsi 2: Copy-paste SQL langsung

1. **Connect ke database:**
```bash
docker exec -it wellmom_postgres psql -U wellmom -d wellmom_db
```

2. **Copy-paste isi file `migrations/create_forum_tables.sql`** ke console

3. **Verifikasi:**
```sql
\dt posts post_likes post_replies
```

### Verifikasi Migration

Setelah migration berhasil, verifikasi dengan:

```bash
docker exec -i wellmom_postgres psql -U wellmom -d wellmom_db -c "\d posts"
docker exec -i wellmom_postgres psql -U wellmom -d wellmom_db -c "\d post_likes"
docker exec -i wellmom_postgres psql -U wellmom -d wellmom_db -c "\d post_replies"
```

---

## Update User Role Constraint

Migration ini mengupdate constraint `check_user_role` di tabel `users` untuk:
- Menambahkan role `super_admin`
- Menghapus role `admin`

### Cara Menjalankan Migration di VPS

#### Opsi 1: Via SSH ke VPS (Recommended untuk Production)

**Untuk Windows (CMD/PowerShell):**

1. **SSH ke VPS menggunakan CMD atau PowerShell:**
```cmd
ssh user@your_vps_ip
```

2. **Setelah masuk ke VPS (Linux), masuk ke direktori project:**
```bash
cd /path/to/wellmom_backend
```

3. **Pull update terbaru dari GitHub:**
```bash
git pull origin main
# atau
git pull origin master
```

4. **Jalankan script migration:**
```bash
# Jika menggunakan environment variables (.env)
bash migrations/update_constraint_vps.sh

# Atau jika database di Docker (untuk setup wellmom_postgres)
bash migrations/update_constraint_docker.sh wellmom_postgres wellmom wellmom_db

# Atau lebih mudah, langsung via docker exec:
docker exec -i wellmom_postgres psql -U wellmom -d wellmom_db < migrations/update_user_role_constraint.sql
```

**Atau jalankan SQL langsung (lebih cepat):**
```bash
# Connect ke database
psql -U your_username -d your_database -h localhost

# Kemudian jalankan SQL:
ALTER TABLE users DROP CONSTRAINT IF EXISTS check_user_role;
ALTER TABLE users ADD CONSTRAINT check_user_role 
    CHECK (role IN ('super_admin', 'puskesmas', 'perawat', 'ibu_hamil', 'kerabat'));
```

**Workflow lengkap dari lokal ke VPS:**
```cmd
# 1. Di VSCode lokal (Windows), commit dan push ke GitHub
git add .
git commit -m "Update user role constraint untuk super_admin"
git push origin main

# 2. SSH ke VPS
ssh user@your_vps_ip

# 3. Di VPS, pull update
cd /path/to/wellmom_backend
git pull origin main

# 4. Jalankan migration (pilih salah satu):
# Opsi A: Via script (berikan permission dulu jika perlu)
chmod +x migrations/update_constraint_vps.sh
bash migrations/update_constraint_vps.sh

# Opsi B: Via psql langsung (LEBIH MUDAH - Recommended)
psql -U your_username -d your_database -h localhost -f migrations/update_user_role_constraint.sql

# Opsi C: Copy-paste SQL langsung
psql -U your_username -d your_database -h localhost
# Kemudian jalankan:
# ALTER TABLE users DROP CONSTRAINT IF EXISTS check_user_role;
# ALTER TABLE users ADD CONSTRAINT check_user_role 
#     CHECK (role IN ('super_admin', 'puskesmas', 'perawat', 'ibu_hamil', 'kerabat'));
```

#### Opsi 2: Menjalankan SQL Langsung via psql di VPS

1. **SSH ke VPS dan connect ke database:**
```bash
ssh user@your_vps_ip
psql -U your_username -d your_database -h localhost
```

2. **Jalankan SQL:**
```sql
-- Drop constraint lama
ALTER TABLE users DROP CONSTRAINT IF EXISTS check_user_role;

-- Tambahkan constraint baru
ALTER TABLE users ADD CONSTRAINT check_user_role 
    CHECK (role IN ('super_admin', 'puskesmas', 'perawat', 'ibu_hamil', 'kerabat'));
```

3. **Verifikasi:**
```sql
SELECT conname, pg_get_constraintdef(oid) 
FROM pg_constraint 
WHERE conname = 'check_user_role';
```

#### Opsi 3: Via Docker (jika database di Docker) - **RECOMMENDED untuk setup Anda**

**Cara 1: Menggunakan script (untuk setup wellmom_postgres):**
```bash
# Berikan permission dulu
chmod +x migrations/update_constraint_docker.sh

# Jalankan dengan default (wellmom_postgres, wellmom, wellmom_db)
bash migrations/update_constraint_docker.sh

# Atau dengan parameter custom
bash migrations/update_constraint_docker.sh [container_name] [db_user] [db_name]
```

**Cara 2: Langsung via docker exec (LEBIH MUDAH - Recommended):**
```bash
# Jalankan SQL file langsung
docker exec -i wellmom_postgres psql -U wellmom -d wellmom_db < migrations/update_user_role_constraint.sql

# Atau copy-paste SQL langsung
docker exec -i wellmom_postgres psql -U wellmom -d wellmom_db -c "ALTER TABLE users DROP CONSTRAINT IF EXISTS check_user_role; ALTER TABLE users ADD CONSTRAINT check_user_role CHECK (role IN ('super_admin', 'puskesmas', 'perawat', 'ibu_hamil', 'kerabat'));"
```

**Cara 3: Masuk ke container dan jalankan SQL:**
```bash
# Masuk ke psql di container
docker exec -it wellmom_postgres psql -U wellmom -d wellmom_db

# Kemudian copy-paste SQL berikut:
ALTER TABLE users DROP CONSTRAINT IF EXISTS check_user_role;
ALTER TABLE users ADD CONSTRAINT check_user_role 
    CHECK (role IN ('super_admin', 'puskesmas', 'perawat', 'ibu_hamil', 'kerabat'));
```

#### Opsi 4: Via Database Management Tool

Jika Anda menggunakan pgAdmin, DBeaver, atau tool database management lainnya:

1. Connect ke database VPS
2. Buka SQL Editor
3. Copy-paste isi file `migrations/update_user_role_constraint.sql`
4. Execute

### Verifikasi

Setelah migration berhasil, verifikasi dengan menjalankan:

```sql
SELECT conname, pg_get_constraintdef(oid) 
FROM pg_constraint 
WHERE conname = 'check_user_role';
```

Hasilnya harus menunjukkan constraint dengan role: `super_admin, puskesmas, perawat, ibu_hamil, kerabat`.

### Troubleshooting

**Error: "check constraint 'check_user_role' of relation 'users' is violated by some row"**

Error ini terjadi karena ada data di tabel `users` yang masih menggunakan role `'admin'`. 

**Solusi:**

**Opsi 1: Gunakan script migration yang sudah include data fix (RECOMMENDED):**
```bash
# Script ini akan otomatis update data 'admin' ke 'super_admin' sebelum update constraint
docker exec -i wellmom_postgres psql -U wellmom -d wellmom_db < migrations/update_user_role_constraint_with_data_fix.sql
```

**Opsi 2: Update data manual terlebih dahulu:**
```bash
# 1. Cek data dengan role 'admin'
docker exec -i wellmom_postgres psql -U wellmom -d wellmom_db -c "SELECT id, email, role FROM users WHERE role = 'admin';"

# 2. Update ke 'super_admin'
docker exec -i wellmom_postgres psql -U wellmom -d wellmom_db -c "UPDATE users SET role = 'super_admin' WHERE role = 'admin';"

# 3. Baru update constraint
docker exec -i wellmom_postgres psql -U wellmom -d wellmom_db < migrations/update_user_role_constraint.sql
```

**Opsi 3: Copy-paste SQL lengkap:**
```bash
docker exec -it wellmom_postgres psql -U wellmom -d wellmom_db
```

Kemudian jalankan:
```sql
-- 1. Cek data dengan role 'admin'
SELECT id, email, role FROM users WHERE role = 'admin';

-- 2. Update ke 'super_admin'
UPDATE users SET role = 'super_admin' WHERE role = 'admin';

-- 3. Drop constraint lama
ALTER TABLE users DROP CONSTRAINT IF EXISTS check_user_role;

-- 4. Tambahkan constraint baru
ALTER TABLE users ADD CONSTRAINT check_user_role 
    CHECK (role IN ('super_admin', 'puskesmas', 'perawat', 'ibu_hamil', 'kerabat'));
```

**Error lainnya:**
1. Pastikan Anda sudah connect ke database yang benar
2. Pastikan user memiliki permission untuk ALTER TABLE dan UPDATE

---

## Add Kerabat Invitation Code Fields

Migration ini menambahkan field untuk fitur invitation code kerabat:
- `invite_code_created_at`: Waktu invitation code dibuat
- `invite_code_expires_at`: Waktu expiration invitation code (24 jam)
- `kerabat_user_id`: Diubah menjadi nullable (untuk support invitation code flow)
- `relation_type`: Diubah menjadi nullable (akan diisi setelah kerabat complete profile)

### Cara Menjalankan Migration di VPS

#### Opsi 1: Via Docker (RECOMMENDED)

```bash
# Pastikan container PostgreSQL berjalan
docker ps | grep wellmom_postgres

# Jalankan migration
docker exec -i wellmom_postgres psql -U wellmom -d wellmom_db < migrations/add_kerabat_invitation_code_fields.sql
```

#### Opsi 2: Copy-paste SQL langsung

1. **Connect ke database:**
```bash
docker exec -it wellmom_postgres psql -U wellmom -d wellmom_db
```

2. **Copy-paste isi file `migrations/add_kerabat_invitation_code_fields.sql`** ke console

3. **Verifikasi:**
```sql
\d kerabat_ibu_hamil
```

### Verifikasi Migration

Setelah migration berhasil, verifikasi dengan:

```bash
docker exec -i wellmom_postgres psql -U wellmom -d wellmom_db -c "\d kerabat_ibu_hamil"
```

Pastikan kolom berikut ada:
- `invite_code_created_at` (TIMESTAMP)
- `invite_code_expires_at` (TIMESTAMP)
- `kerabat_user_id` (nullable)
- `relation_type` (nullable)
