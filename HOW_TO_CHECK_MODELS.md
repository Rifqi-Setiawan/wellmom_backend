# Cara Mengecek Model Gemini yang Tersedia

## 🎯 Metode 1: Menggunakan Script Python (Recommended)

Saya sudah membuat script `check_gemini_models.py` untuk mengecek model yang tersedia.

### Langkah-langkah:

1. **Jalankan script:**
   ```bash
   python check_gemini_models.py
   ```

2. **Script akan:**
   - ✅ Menampilkan semua model yang tersedia
   - ✅ Mengelompokkan berdasarkan family (gemini-1.5-flash, gemini-1.5-pro, dll)
   - ✅ Test setiap model untuk memastikan bisa digunakan
   - ✅ Memberikan rekomendasi model terbaik

3. **Output akan menunjukkan:**
   - Model mana yang tersedia
   - Model mana yang berhasil di-test
   - Rekomendasi model untuk digunakan

## 🎯 Metode 2: Melalui Google AI Studio Web Interface

### Langkah-langkah:

1. **Buka Google AI Studio:**
   - Kunjungi: https://makersuite.google.com/app/apikey
   - Login dengan akun Google Anda

2. **Cek di Dashboard:**
   - Klik "Dashboard" di sidebar kiri
   - Scroll ke bawah untuk melihat "Available Models"
   - Atau cek di "Get API key" section

3. **Cek di Documentation:**
   - Klik "API quickstart" button
   - Atau buka: https://ai.google.dev/models/gemini

## 🎯 Metode 3: Melalui API Call Langsung

### Menggunakan Python:

```python
import google.generativeai as genai

# Configure dengan API key Anda
genai.configure(api_key="YOUR_API_KEY")

# List semua model
models = genai.list_models()

# Filter model yang support generateContent
for model in models:
    if 'generateContent' in model.supported_generation_methods:
        print(f"✅ {model.name}")
```

### Menggunakan cURL:

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models?key=YOUR_API_KEY"
```

## 🎯 Metode 4: Test Langsung di Code

Tambahkan kode ini di `app/services/chatbot_service.py` untuk debug:

```python
def __init__(self):
    # ... existing code ...
    
    # Debug: List available models
    try:
        models = genai.list_models()
        print("Available models:")
        for model in models:
            if 'generateContent' in model.supported_generation_methods:
                print(f"  - {model.name}")
    except Exception as e:
        print(f"Error listing models: {e}")
```

## 📋 Model yang Umum Tersedia

Berdasarkan Google AI Studio, model yang biasanya tersedia:

### Free Tier:
- ✅ `gemini-1.5-flash-latest` (Recommended - Fast & Free)
- ✅ `gemini-1.5-flash`
- ✅ `gemini-pro` (Legacy, lebih stabil)

### Paid Tier:
- 💎 `gemini-1.5-pro-latest` (More capable)
- 💎 `gemini-1.5-pro`

## 🔧 Jika Model Tidak Ditemukan

### Solusi 1: Update Model List di Code

Edit `app/services/chatbot_service.py`, ubah urutan `model_names`:

```python
model_names = [
    'gemini-pro',  # Coba legacy model dulu
    'gemini-1.5-flash',
    'gemini-1.5-flash-latest',
]
```

### Solusi 2: Cek Quota Tier

Dari gambar yang Anda kirim, quota tier adalah "Free tier". 
- Free tier biasanya hanya memiliki akses ke `gemini-pro` dan `gemini-1.5-flash`
- Untuk akses ke model Pro, perlu "Set up billing"

### Solusi 3: Generate API Key Baru

1. Di Google AI Studio, klik "Create API key"
2. Pilih project yang berbeda
3. Coba dengan API key baru

## ✅ Langkah Selanjutnya

1. **Jalankan `check_gemini_models.py`** untuk melihat model yang tersedia
2. **Update `app/services/chatbot_service.py`** dengan model yang berhasil
3. **Test lagi** dengan Flutter app

## 📝 Catatan Penting

- Model name bisa berbeda tergantung:
  - Quota tier (Free vs Paid)
  - Region
  - API key permissions
  - Project settings

- Untuk production, gunakan model yang stabil:
  - `gemini-pro` (paling stabil, legacy)
  - `gemini-1.5-flash-latest` (latest, tapi mungkin tidak selalu tersedia)

- Untuk development/testing:
  - Bisa gunakan model apapun yang tersedia
  - Test dengan `check_gemini_models.py` dulu
