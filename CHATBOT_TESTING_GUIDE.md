# Panduan Testing & Troubleshooting Chatbot WellMom

## 🔍 Analisis Error yang Ditemukan

Error yang muncul:
```
404 models/gemini-1.5-flash is not found for API version v1beta
```

**Penyebab:**
- Model name `gemini-1.5-flash` mungkin tidak tersedia untuk API key tertentu
- Beberapa API key hanya memiliki akses ke model tertentu
- Perlu mencoba model name alternatif

## ✅ Perbaikan yang Sudah Dilakukan

1. **Auto-fallback ke model alternatif:**
   - `gemini-1.5-flash-latest` (prioritas 1)
   - `gemini-1.5-flash` (prioritas 2)
   - `gemini-1.5-pro-latest` (prioritas 3)
   - `gemini-pro` (fallback terakhir)

2. **Error handling yang lebih baik:**
   - Deteksi error 404 secara spesifik
   - Pesan error yang lebih informatif
   - Logging untuk debugging

## 🧪 Testing Steps

### 1. Test Service Langsung

Jalankan test script:
```bash
python test_chatbot_service.py
```

Script ini akan:
- ✅ Cek apakah GEMINI_API_KEY ada
- ✅ Test inisialisasi service
- ✅ Test basic chat (tanpa history)
- ✅ Test chat dengan history
- ✅ Test token counting

### 2. Test via API Endpoint

#### A. Cek Quota (tanpa mengirim pesan)
```bash
curl -X GET "http://localhost:8000/api/v1/chatbot/quota" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### B. Buat Conversation Baru
```bash
curl -X POST "http://localhost:8000/api/v1/chatbot/conversations/new" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Conversation"}'
```

#### C. Kirim Pesan (Test Utama)
```bash
curl -X POST "http://localhost:8000/api/v1/chatbot/send?conversation_id=1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Halo, apa kabar?"}'
```

#### D. Get Conversation History
```bash
curl -X GET "http://localhost:8000/api/v1/chatbot/conversations/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. Test dari Flutter

Pastikan:
1. ✅ Base URL backend benar
2. ✅ Token authentication sudah di-set
3. ✅ Request body sesuai schema
4. ✅ Error handling di Flutter sudah ada

**Contoh request body:**
```json
{
  "message": "Apa saja makanan yang baik untuk ibu hamil?"
}
```

**Query parameter (optional):**
- `conversation_id`: ID conversation yang sedang berlangsung (jika ada)

## 🔧 Troubleshooting

### Error: "404 models/gemini-1.5-flash is not found"

**Solusi:**
1. Service sudah otomatis mencoba model alternatif
2. Jika masih error, cek API key di Google AI Studio:
   - Buka: https://makersuite.google.com/app/apikey
   - Pastikan API key aktif
   - Cek model yang tersedia untuk API key ini

3. **Manual fix:** Edit `app/services/chatbot_service.py`, ubah urutan model:
```python
model_names = [
    'gemini-pro',  # Coba legacy model dulu
    'gemini-1.5-flash-latest',
    # ...
]
```

### Error: "GEMINI_API_KEY tidak ditemukan"

**Solusi:**
1. Pastikan file `.env` ada di root project
2. Tambahkan:
```env
GEMINI_API_KEY=your_actual_api_key_here
```
3. Restart backend service

### Error: "Konfigurasi layanan AI tidak valid"

**Kemungkinan:**
- API key tidak valid
- API key expired
- API key tidak memiliki permission

**Solusi:**
1. Generate API key baru di Google AI Studio
2. Update `.env` dengan API key baru
3. Restart backend

### Error: "Layanan AI sedang sibuk"

**Kemungkinan:**
- Rate limit tercapai
- Quota harian habis
- API sedang maintenance

**Solusi:**
1. Tunggu beberapa saat
2. Cek quota di Google Cloud Console
3. Upgrade API key jika perlu

### Error: "Batas penggunaan chatbot harian Anda telah habis"

**Solusi:**
- Ini adalah user quota limit (bukan error)
- User perlu menunggu reset (midnight WIB)
- Atau admin bisa reset manual di database

## 📊 Monitoring & Logs

### Cek Logs Backend

```bash
# Docker
docker logs wellmom_backend -f

# Atau cari error chatbot
docker logs wellmom_backend | grep -i chatbot
```

### Cek Database

```sql
-- Cek conversations
SELECT * FROM chatbot_conversations ORDER BY created_at DESC LIMIT 10;

-- Cek messages
SELECT * FROM chatbot_messages ORDER BY created_at DESC LIMIT 10;

-- Cek user usage
SELECT * FROM chatbot_user_usage ORDER BY date DESC LIMIT 10;

-- Cek global usage
SELECT * FROM chatbot_global_usage ORDER BY date DESC LIMIT 10;
```

## 🎯 Checklist Testing

- [ ] Service initialization berhasil
- [ ] Basic chat tanpa history works
- [ ] Chat dengan history works
- [ ] Token counting accurate
- [ ] Rate limiting works (coba >10 req/min)
- [ ] User quota limit works
- [ ] Global quota limit works
- [ ] Error handling proper (404, timeout, etc.)
- [ ] Flutter integration works
- [ ] Database records created correctly

## 🚀 Next Steps

1. **Jika masih error setelah perbaikan:**
   - Jalankan `test_chatbot_service.py` dan share output
   - Cek logs backend untuk error details
   - Verifikasi API key di Google AI Studio

2. **Untuk production:**
   - Set environment variables di VPS
   - Monitor token usage
   - Set up alerts untuk quota limits

3. **Optimization:**
   - Adjust `CHATBOT_MAX_HISTORY_MESSAGES` jika response terlalu lambat
   - Adjust `CHATBOT_REQUEST_TIMEOUT` jika timeout sering terjadi
   - Monitor token usage untuk cost control

## 📝 Notes

- Model name bisa berbeda tergantung API key
- Free tier Gemini memiliki rate limits
- Token counting adalah estimasi (tidak 100% accurate)
- Quota reset setiap midnight WIB (Asia/Jakarta)
