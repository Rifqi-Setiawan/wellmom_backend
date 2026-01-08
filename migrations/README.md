# Database Migrations

## Update User Role Constraint

Migration ini mengupdate constraint `check_user_role` di tabel `users` untuk:
- Menambahkan role `super_admin`
- Menghapus role `admin`

### Cara Menjalankan Migration di VPS

#### Opsi 1: Via SSH ke VPS (Recommended untuk Production)

1. **SSH ke VPS:**
```bash
ssh user@your_vps_ip
```

2. **Masuk ke direktori project:**
```bash
cd /path/to/wellmom_backend
```

3. **Jalankan script migration:**
```bash
# Jika menggunakan environment variables (.env)
bash migrations/update_constraint_vps.sh

# Atau jika database di Docker
bash migrations/update_constraint_docker.sh [container_name]
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

#### Opsi 3: Via Docker (jika database di Docker)

```bash
# Copy file SQL ke container dan jalankan
docker exec -i your_postgres_container psql -U your_username -d your_database < migrations/update_user_role_constraint.sql

# Atau masuk ke container dan jalankan
docker exec -it your_postgres_container psql -U your_username -d your_database
# Kemudian copy-paste SQL dari update_user_role_constraint.sql
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

**Jika constraint masih error:**
1. Pastikan Anda sudah connect ke database yang benar
2. Pastikan user memiliki permission untuk ALTER TABLE
3. Cek apakah ada data yang masih menggunakan role 'admin' (harus diupdate dulu)

**Update data yang masih menggunakan role 'admin':**
```sql
-- Cek data dengan role 'admin'
SELECT id, email, role FROM users WHERE role = 'admin';

-- Update ke 'super_admin' (jika perlu)
UPDATE users SET role = 'super_admin' WHERE role = 'admin';
```
