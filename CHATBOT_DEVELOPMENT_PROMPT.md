# Task: Implement AI Chatbot Feature for WellMom Healthcare Application

## Project Context

WellMom adalah sistem monitoring kesehatan ibu hamil berbasis AI dan IoT untuk daerah terpencil di Indonesia. Backend menggunakan FastAPI dengan PostgreSQL. Kita perlu menambahkan fitur chatbot AI menggunakan Google Gemini API untuk membantu ibu hamil dengan pertanyaan seputar kesehatan kehamilan.

## Existing Project Structure

```
app/
├── api/
│   ├── deps.py                    # Dependency injection (get_db, get_current_user, require_role)
│   └── v1/
│       ├── api.py                 # Router aggregation
│       └── endpoints/
│           ├── auth.py
│           ├── chat.py            # Existing human-to-human chat
│           ├── forum.py
│           └── ...
├── config.py                      # Settings using pydantic_settings
├── core/
│   ├── exceptions.py
│   └── security.py                # JWT token handling
├── crud/
│   ├── base.py                    # CRUDBase generic class
│   └── ...
├── database.py                    # SQLAlchemy setup
├── main.py                        # FastAPI app
├── models/                        # SQLAlchemy models
├── schemas/                       # Pydantic schemas
├── services/                      # Business logic services
└── utils/
```

## Existing Patterns to Follow

### 1. Dependency Injection Pattern (from deps.py)
```python
from app.api.deps import get_db, get_current_active_user, require_role
from sqlalchemy.orm import Session
from app.models.user import User

@router.post("/endpoint")
async def endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    pass
```

### 2. Model Pattern (SQLAlchemy)
```python
from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base

class ModelName(Base):
    __tablename__ = "table_name"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
```

### 3. Schema Pattern (Pydantic v2)
```python
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class SchemaBase(BaseModel):
    field: str
    
    model_config = ConfigDict(json_schema_extra={"example": {...}})

class SchemaCreate(SchemaBase):
    pass

class SchemaResponse(SchemaBase):
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
```

### 4. CRUD Pattern
```python
from app.crud.base import CRUDBase
from app.models.model import Model
from app.schemas.model import ModelCreate, ModelUpdate

class CRUDModel(CRUDBase[Model, ModelCreate, ModelUpdate]):
    def custom_method(self, db: Session, ...) -> Model:
        pass

crud_model = CRUDModel(Model)
```

### 5. Endpoint Pattern
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/resource",
    tags=["Resource"],
)

@router.post(
    "/action",
    response_model=ResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Short summary",
    description="Detailed description",
)
async def action(
    request: RequestSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ResponseSchema:
    """Docstring."""
    pass
```

### 6. Config Pattern
```python
# In app/config.py - add new settings
class Settings(BaseSettings):
    # ... existing settings ...
    
    # New Chatbot Settings
    GEMINI_API_KEY: str
    CHATBOT_USER_DAILY_TOKEN_LIMIT: int = 10000
    CHATBOT_GLOBAL_DAILY_TOKEN_LIMIT: int = 500000
    CHATBOT_RATE_LIMIT_PER_MINUTE: int = 10
    CHATBOT_REQUEST_TIMEOUT: int = 30
    CHATBOT_MAX_HISTORY_MESSAGES: int = 20
```

---

## Implementation Requirements

### 1. Database Models (app/models/chatbot.py)

Create the following tables:

```sql
-- Chatbot conversations (sessions)
CREATE TABLE chatbot_conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),  -- Auto-generated from first message
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Individual messages in conversations
CREATE TABLE chatbot_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES chatbot_conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Daily usage tracking per user
CREATE TABLE chatbot_user_usage (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    tokens_used INTEGER DEFAULT 0,
    request_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, date)
);

-- Global daily usage (for billing protection)
CREATE TABLE chatbot_global_usage (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE DEFAULT CURRENT_DATE,
    tokens_used INTEGER DEFAULT 0,
    request_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 2. Pydantic Schemas (app/schemas/chatbot.py)

```python
# Request/Response schemas needed:
- ChatbotSendRequest: message (str)
- ChatbotSendResponse: response (str), conversation_id (int), quota (QuotaInfo)
- ChatbotConversationResponse: id, title, created_at, updated_at, message_count
- ChatbotMessageResponse: id, role, content, created_at
- ChatbotHistoryResponse: conversation (ChatbotConversationResponse), messages (List[ChatbotMessageResponse])
- QuotaInfoResponse: used_today, limit, remaining, resets_at
- ChatbotNewConversationRequest: title (Optional[str])
```

### 3. CRUD Operations (app/crud/chatbot.py)

```python
# Required CRUD methods:
- create_conversation(db, user_id, title=None)
- get_conversation(db, conversation_id, user_id)  # Must verify ownership
- get_user_conversations(db, user_id, skip, limit)
- delete_conversation(db, conversation_id, user_id)
- add_message(db, conversation_id, role, content, input_tokens, output_tokens)
- get_conversation_messages(db, conversation_id, limit)
- get_or_create_user_usage(db, user_id, date)
- increment_user_usage(db, user_id, tokens)
- get_or_create_global_usage(db, date)
- increment_global_usage(db, tokens)
- check_user_quota(db, user_id) -> (can_use: bool, remaining: int)
- check_global_quota(db) -> (can_use: bool, remaining: int)
```

### 4. Chatbot Service (app/services/chatbot_service.py)

```python
import google.generativeai as genai
from app.config import settings

class ChatbotService:
    """Service for interacting with Gemini API with token management."""
    
    SYSTEM_PROMPT = """
    Kamu adalah WellMom Assistant, asisten kesehatan maternal yang ramah dan informatif.
    
    ## Identitas
    - Nama: WellMom Assistant
    - Peran: Asisten kesehatan untuk ibu hamil
    - Bahasa: Bahasa Indonesia yang sopan dan mudah dipahami
    
    ## Tugas Utama
    - Menjawab pertanyaan seputar kehamilan: gejala, nutrisi, olahraga, tanda bahaya
    - Memberikan informasi kesehatan yang akurat dan mudah dipahami
    - Memberikan dukungan emosional dengan empati
    - Mengingatkan untuk selalu berkonsultasi dengan bidan/dokter untuk masalah serius
    
    ## Batasan Penting
    - JANGAN memberikan diagnosis medis
    - JANGAN merekomendasikan obat-obatan tanpa saran dokter
    - JANGAN menjawab pertanyaan di luar topik kesehatan kehamilan
    - Untuk pertanyaan di luar topik, tolak dengan sopan dan arahkan kembali ke topik kehamilan
    
    ## Gaya Komunikasi
    - Gunakan bahasa yang hangat dan mendukung
    - Panggil pengguna dengan "Ibu" atau "Bunda"
    - Berikan jawaban yang ringkas namun informatif
    - Sertakan emoji yang relevan untuk membuat percakapan lebih ramah 🤰💕
    
    ## Format Respons
    - Untuk pertanyaan kesehatan: berikan informasi + saran + reminder konsultasi dokter
    - Untuk keluhan: tunjukkan empati + informasi + kapan harus ke dokter
    - Untuk pertanyaan umum kehamilan: jawab informatif + tips praktis
    """
    
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            'gemini-1.5-flash',
            system_instruction=self.SYSTEM_PROMPT
        )
    
    async def chat(
        self, 
        message: str, 
        history: list = None,
        timeout: int = 30
    ) -> tuple[str, int, int]:
        """
        Send message to Gemini and get response.
        
        Returns:
            tuple: (response_text, input_tokens, output_tokens)
        """
        # Implementation with timeout and error handling
        pass
    
    def count_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        pass
```

### 5. Rate Limiter (app/core/rate_limiter.py)

```python
from datetime import datetime, timedelta
from typing import Dict
import asyncio

class InMemoryRateLimiter:
    """Simple in-memory rate limiter for MVP."""
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[int, list] = {}  # user_id -> list of timestamps
        self._lock = asyncio.Lock()
    
    async def is_allowed(self, user_id: int) -> tuple[bool, int]:
        """
        Check if user is allowed to make request.
        
        Returns:
            tuple: (is_allowed, seconds_until_reset)
        """
        pass
    
    async def record_request(self, user_id: int):
        """Record a request for the user."""
        pass
```

### 6. API Endpoints (app/api/v1/endpoints/chatbot.py)

```python
router = APIRouter(
    prefix="/chatbot",
    tags=["AI Chatbot"],
)

# Required endpoints:

@router.post("/send", response_model=ChatbotSendResponse)
async def send_message(
    request: ChatbotSendRequest,
    conversation_id: Optional[int] = None,  # Query param, None = new conversation
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ibu_hamil", "kerabat")),
) -> ChatbotSendResponse:
    """
    Kirim pesan ke AI chatbot dan dapatkan respons.
    
    - Jika conversation_id tidak diberikan, akan membuat conversation baru
    - Cek quota sebelum mengirim
    - Track token usage
    """
    pass

@router.get("/conversations", response_model=List[ChatbotConversationResponse])
async def get_conversations(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ibu_hamil", "kerabat")),
) -> List[ChatbotConversationResponse]:
    """Dapatkan daftar conversation milik user."""
    pass

@router.get("/conversations/{conversation_id}", response_model=ChatbotHistoryResponse)
async def get_conversation_history(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ibu_hamil", "kerabat")),
) -> ChatbotHistoryResponse:
    """Dapatkan history pesan dalam satu conversation."""
    pass

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ibu_hamil", "kerabat")),
) -> dict:
    """Hapus conversation."""
    pass

@router.get("/quota", response_model=QuotaInfoResponse)
async def get_quota(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ibu_hamil", "kerabat")),
) -> QuotaInfoResponse:
    """Cek sisa quota penggunaan chatbot hari ini."""
    pass

@router.post("/conversations/new", response_model=ChatbotConversationResponse)
async def create_new_conversation(
    request: ChatbotNewConversationRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ibu_hamil", "kerabat")),
) -> ChatbotConversationResponse:
    """Buat conversation baru (opsional, /send juga bisa buat otomatis)."""
    pass
```

### 7. Register Router (app/api/v1/api.py)

```python
# Add to existing api.py
from app.api.v1.endpoints import chatbot

api_router.include_router(chatbot.router, prefix="/api/v1")
```

### 8. Update Config (app/config.py)

Add these settings:
```python
# Gemini AI Chatbot
GEMINI_API_KEY: str = ""
CHATBOT_USER_DAILY_TOKEN_LIMIT: int = 10000      # Per user per day
CHATBOT_GLOBAL_DAILY_TOKEN_LIMIT: int = 500000   # Total all users per day
CHATBOT_RATE_LIMIT_PER_MINUTE: int = 10          # Max requests per user per minute
CHATBOT_REQUEST_TIMEOUT: int = 30                 # Seconds
CHATBOT_MAX_HISTORY_MESSAGES: int = 20           # Messages to include for context
```

### 9. Update requirements.txt

Add:
```
google-generativeai>=0.8.0
```

---

## Error Handling Requirements

### HTTP Status Codes
- 200: Success
- 201: Created (new conversation)
- 400: Bad request (invalid input)
- 401: Unauthorized (not logged in)
- 403: Forbidden (wrong role or quota exceeded)
- 404: Not found (conversation doesn't exist)
- 429: Too many requests (rate limited)
- 500: Internal server error
- 503: Service unavailable (Gemini API down)

### Error Response Format
```python
{
    "detail": "Pesan error dalam Bahasa Indonesia"
}
```

### Specific Error Messages
```python
ERRORS = {
    "QUOTA_EXCEEDED_USER": "Batas penggunaan chatbot harian Anda telah habis. Silakan coba lagi besok.",
    "QUOTA_EXCEEDED_GLOBAL": "Layanan chatbot sedang tidak tersedia. Silakan coba lagi besok.",
    "RATE_LIMITED": "Terlalu banyak permintaan. Silakan tunggu {seconds} detik.",
    "CONVERSATION_NOT_FOUND": "Percakapan tidak ditemukan.",
    "GEMINI_ERROR": "Layanan AI sedang mengalami gangguan. Silakan coba lagi.",
    "GEMINI_TIMEOUT": "Waktu respons habis. Silakan coba lagi.",
}
```

---

## Token Management (CRITICAL - Cost Control)

### Token Counting Strategy
```python
# Gemini 1.5 Flash pricing (as of 2024):
# - Input: $0.075 / 1M tokens
# - Output: $0.30 / 1M tokens
# Free tier: 15 RPM, 1M TPM, 1500 RPD

# Conservative estimation for safety:
def estimate_tokens(text: str) -> int:
    """Rough estimate: 1 token ≈ 4 characters for Indonesian text."""
    return len(text) // 4 + 1
```

### Quota Check Flow
```
1. User sends message
2. Check rate limit (10 req/min) → 429 if exceeded
3. Check user daily quota → 403 if exceeded
4. Check global daily quota → 403 if exceeded
5. Send to Gemini
6. Record actual token usage
7. Return response with quota info
```

### Daily Reset
- Reset time: 00:00 WIB (Asia/Jakarta)
- Implementation: Check date in usage table, create new record if different date

---

## Security Requirements

1. **API Key Protection**
   - Store in environment variable only
   - Never log or expose in responses

2. **User Authorization**
   - Only `ibu_hamil` and `kerabat` roles can access chatbot
   - Users can only access their own conversations

3. **Input Sanitization**
   - Limit message length (max 2000 characters)
   - Strip HTML/script tags

4. **Content Safety**
   - Rely on Gemini's built-in safety filters
   - Log suspicious queries for review

---

## Migration File (migrations/create_chatbot_tables.sql)

```sql
-- Create chatbot tables for WellMom AI Assistant

-- Chatbot conversations
CREATE TABLE IF NOT EXISTS chatbot_conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_chatbot_conversations_user_id ON chatbot_conversations(user_id);
CREATE INDEX idx_chatbot_conversations_created_at ON chatbot_conversations(created_at DESC);

-- Chatbot messages
CREATE TABLE IF NOT EXISTS chatbot_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES chatbot_conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_chatbot_messages_conversation_id ON chatbot_messages(conversation_id);
CREATE INDEX idx_chatbot_messages_created_at ON chatbot_messages(created_at);

-- User daily usage
CREATE TABLE IF NOT EXISTS chatbot_user_usage (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    tokens_used INTEGER DEFAULT 0,
    request_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, date)
);

CREATE INDEX idx_chatbot_user_usage_user_date ON chatbot_user_usage(user_id, date);

-- Global daily usage
CREATE TABLE IF NOT EXISTS chatbot_global_usage (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE DEFAULT CURRENT_DATE,
    tokens_used INTEGER DEFAULT 0,
    request_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_chatbot_global_usage_date ON chatbot_global_usage(date);
```

---

## File Deliverables

Create the following files:
1. `app/models/chatbot.py` - SQLAlchemy models
2. `app/schemas/chatbot.py` - Pydantic schemas
3. `app/crud/chatbot.py` - CRUD operations
4. `app/services/chatbot_service.py` - Gemini integration
5. `app/core/rate_limiter.py` - Rate limiting
6. `app/api/v1/endpoints/chatbot.py` - API endpoints
7. `migrations/create_chatbot_tables.sql` - Database migration

Update existing files:
1. `app/config.py` - Add chatbot settings
2. `app/api/v1/api.py` - Register chatbot router
3. `requirements.txt` - Add google-generativeai
4. `app/models/__init__.py` - Export chatbot models
5. `app/schemas/__init__.py` - Export chatbot schemas
6. `app/crud/__init__.py` - Export chatbot crud

---

## Testing Checklist

After implementation, verify:
- [ ] Can create new conversation
- [ ] Can send message and get response
- [ ] Token usage is tracked correctly
- [ ] Rate limiting works (>10 req/min blocked)
- [ ] User quota limit works
- [ ] Global quota limit works
- [ ] Only ibu_hamil and kerabat can access
- [ ] Users can only see their own conversations
- [ ] Quota resets at midnight WIB
- [ ] Error messages in Indonesian
- [ ] Graceful handling when Gemini API is down

---

## Important Notes

1. **Deadline**: Innovillage 2025 - January 12th
2. **Priority**: Working MVP over perfect code
3. **Free Tier**: Stay within Gemini free tier limits
4. **Language**: All user-facing messages in Bahasa Indonesia
5. **Timezone**: Asia/Jakarta for daily reset

## Environment Variables to Add (.env)

```env
# Gemini AI Chatbot
GEMINI_API_KEY=your_api_key_here
CHATBOT_USER_DAILY_TOKEN_LIMIT=10000
CHATBOT_GLOBAL_DAILY_TOKEN_LIMIT=500000
CHATBOT_RATE_LIMIT_PER_MINUTE=10
CHATBOT_REQUEST_TIMEOUT=30
CHATBOT_MAX_HISTORY_MESSAGES=20
```
