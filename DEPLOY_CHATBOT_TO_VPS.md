# Panduan Deploy Chatbot Feature ke VPS

## 📋 Checklist Pre-Deployment

Sebelum deploy, pastikan:
- [ ] Semua perubahan sudah di-commit dan push ke GitHub
- [ ] Database migration file sudah ada (`migrations/create_chatbot_tables.sql`)
- [ ] Environment variables sudah disiapkan (`.env` di VPS)

## 🚀 Langkah-langkah Deployment

### 1. SSH ke VPS

```bash
ssh wellmom@your-vps-ip
# atau
ssh wellmom@103.191.92.29
```

### 2. Navigate ke Project Directory

```bash
cd /opt/wellmom/wellmom-backend
# atau sesuai path project Anda
```

### 3. Pull Latest Changes dari GitHub

```bash
# Backup dulu (optional, tapi recommended)
cp .env .env.backup

# Pull latest code
git pull origin main
# atau
git pull origin master
```

### 4. Install Dependencies Baru

```bash
# Masuk ke Docker container backend
docker exec -it wellmom_backend bash

# Install google-generativeai package
pip install google-generativeai>=0.8.0

# Exit dari container
exit
```

**Atau jika menggunakan requirements.txt:**
```bash
# Di dalam container
pip install -r requirements.txt
```

### 5. Update Environment Variables

Edit file `.env` di VPS (jika belum ada):

```bash
# Edit .env file
nano .env
# atau
vim .env
```

Tambahkan/update variabel berikut:

```env
# Gemini AI Chatbot
GEMINI_API_KEY=AIzaSyBRvLdsbCYkRjEqKQdCiF3If8SUMFanpfg
CHATBOT_USER_DAILY_TOKEN_LIMIT=10000
CHATBOT_GLOBAL_DAILY_TOKEN_LIMIT=500000
CHATBOT_RATE_LIMIT_PER_MINUTE=10
CHATBOT_REQUEST_TIMEOUT=30
CHATBOT_MAX_HISTORY_MESSAGES=20
```

**Catatan:** Ganti `GEMINI_API_KEY` dengan API key yang valid untuk production.

### 6. Run Database Migration

**PENTING:** Jalankan migration untuk membuat tabel chatbot:

```bash
# Masuk ke PostgreSQL container
docker exec -i wellmom_postgres psql -U wellmom -d wellmom_db < migrations/create_chatbot_tables.sql
```

**Atau jika file migration ada di host:**
```bash
# Dari host VPS
cat migrations/create_chatbot_tables.sql | docker exec -i wellmom_postgres psql -U wellmom -d wellmom_db
```

**Verifikasi migration berhasil:**
```bash
docker exec -it wellmom_postgres psql -U wellmom -d wellmom_db -c "\d chatbot_conversations"
docker exec -it wellmom_postgres psql -U wellmom -d wellmom_db -c "\d chatbot_messages"
docker exec -it wellmom_postgres psql -U wellmom -d wellmom_db -c "\d chatbot_user_usage"
docker exec -it wellmom_postgres psql -U wellmom -d wellmom_db -c "\d chatbot_global_usage"
```

### 7. Restart Backend Service

```bash
# Restart container backend
docker-compose restart wellmom_backend

# Atau jika menggunakan docker run
docker restart wellmom_backend
```

### 8. Verify Deployment

#### A. Cek Logs Backend

```bash
# Monitor logs
docker logs wellmom_backend -f

# Cek apakah ada error
docker logs wellmom_backend | grep -i error

# Cek apakah chatbot service initialized
docker logs wellmom_backend | grep -i "gemini\|chatbot"
```

**Expected output:**
```
INFO: Successfully initialized Gemini model: gemini-1.5-flash-latest
```

#### B. Test API Endpoint

```bash
# Test quota endpoint (tanpa auth dulu untuk cek apakah endpoint ada)
curl http://localhost:8000/api/v1/chatbot/quota

# Atau test dengan Postman/curl dengan token
curl -X GET "http://your-vps-ip:8000/api/v1/chatbot/quota" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### C. Cek Swagger Documentation

Buka browser:
```
http://your-vps-ip:8000/docs
```

Cari endpoint `/api/v1/chatbot/*` - seharusnya sudah muncul.

## 🔍 Troubleshooting

### Error: "ModuleNotFoundError: No module named 'google.generativeai'"

**Solusi:**
```bash
docker exec -it wellmom_backend pip install google-generativeai>=0.8.0
docker-compose restart wellmom_backend
```

### Error: "GEMINI_API_KEY tidak ditemukan"

**Solusi:**
1. Pastikan `.env` file ada di root project
2. Pastikan `GEMINI_API_KEY` sudah di-set
3. Restart container:
   ```bash
   docker-compose restart wellmom_backend
   ```

### Error: "relation 'chatbot_conversations' does not exist"

**Solusi:**
Migration belum dijalankan. Jalankan:
```bash
docker exec -i wellmom_postgres psql -U wellmom -d wellmom_db < migrations/create_chatbot_tables.sql
```

### Error: "404 models/gemini-1.5-flash-latest is not found"

**Solusi:**
Service akan otomatis mencoba model berikutnya. Cek logs:
```bash
docker logs wellmom_backend | grep -i "gemini\|model"
```

Jika semua model gagal, cek API key di Google AI Studio.

## 📝 Quick Deployment Script

Buat file `deploy_chatbot.sh` di VPS:

```bash
#!/bin/bash

echo "=========================================="
echo "Deploying Chatbot Feature to VPS"
echo "=========================================="

# 1. Pull latest code
echo "1. Pulling latest code..."
cd /opt/wellmom/wellmom-backend
git pull origin main

# 2. Install dependencies
echo "2. Installing dependencies..."
docker exec -it wellmom_backend pip install google-generativeai>=0.8.0

# 3. Run migration
echo "3. Running database migration..."
docker exec -i wellmom_postgres psql -U wellmom -d wellmom_db < migrations/create_chatbot_tables.sql

# 4. Restart service
echo "4. Restarting backend service..."
docker-compose restart wellmom_backend

# 5. Wait for service to start
echo "5. Waiting for service to start..."
sleep 5

# 6. Check logs
echo "6. Checking logs..."
docker logs wellmom_backend --tail 50 | grep -i "gemini\|chatbot\|error"

echo "=========================================="
echo "Deployment complete!"
echo "=========================================="
```

**Jalankan:**
```bash
chmod +x deploy_chatbot.sh
./deploy_chatbot.sh
```

## ✅ Post-Deployment Checklist

- [ ] Database migration berhasil (tabel chatbot ada)
- [ ] Dependencies terinstall (`google-generativeai`)
- [ ] Environment variables sudah di-set
- [ ] Backend service restart tanpa error
- [ ] Logs menunjukkan "Successfully initialized Gemini model"
- [ ] API endpoint `/api/v1/chatbot/*` accessible
- [ ] Swagger documentation menampilkan chatbot endpoints
- [ ] Test dari Flutter app berhasil

## 🎯 Summary Commands

**Quick deploy (copy-paste semua):**

```bash
# 1. Pull code
cd /opt/wellmom/wellmom-backend && git pull origin main

# 2. Install dependencies
docker exec -it wellmom_backend pip install google-generativeai>=0.8.0

# 3. Run migration
docker exec -i wellmom_postgres psql -U wellmom -d wellmom_db < migrations/create_chatbot_tables.sql

# 4. Restart service
docker-compose restart wellmom_backend

# 5. Check logs
docker logs wellmom_backend --tail 50 | grep -i "gemini\|chatbot"
```

## 📞 Jika Ada Masalah

1. **Cek logs:**
   ```bash
   docker logs wellmom_backend -f
   ```

2. **Cek database:**
   ```bash
   docker exec -it wellmom_postgres psql -U wellmom -d wellmom_db -c "\dt chatbot*"
   ```

3. **Cek environment:**
   ```bash
   docker exec wellmom_backend env | grep GEMINI
   ```

4. **Restart ulang:**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

## 🔐 Security Notes

- **Jangan commit `.env` file ke Git**
- **Gunakan API key yang berbeda untuk production**
- **Monitor token usage untuk cost control**
- **Set up alerts untuk quota limits**
