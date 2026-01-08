# Chat Feature Documentation

## Overview

Fitur chat memungkinkan komunikasi real-time antara **Ibu Hamil** dan **Perawat** yang ter-assign. Sistem ini menggunakan kombinasi REST API untuk mengirim pesan dan WebSocket untuk real-time updates.

## Architecture

### Database Models

1. **Conversation** (`conversations` table)
   - Menyimpan metadata percakapan antara satu ibu hamil dan satu perawat
   - Unique constraint: satu conversation per pasangan (ibu_hamil_id, perawat_id)
   - `last_message_at`: untuk sorting conversations

2. **Message** (`messages` table)
   - Menyimpan pesan-pesan dalam conversation
   - `is_read`: status read/unread
   - `read_at`: timestamp ketika pesan dibaca

### API Endpoints

#### REST API (HTTP)

1. **GET `/api/v1/chat/conversations`**
   - List semua conversations untuk user yang login
   - **Ibu Hamil**: conversations dengan perawat yang ter-assign
   - **Perawat**: conversations dengan semua ibu hamil yang ter-assign ke mereka
   - Response termasuk last message dan unread count

2. **GET `/api/v1/chat/conversations/{conversation_id}`**
   - Get detail conversation

3. **GET `/api/v1/chat/conversations/{conversation_id}/messages`**
   - Get messages dalam conversation (dengan pagination)
   - Messages diurutkan dari oldest ke newest (untuk chat UI)

4. **POST `/api/v1/chat/messages`**
   - Send new message
   - **Ibu Hamil**: otomatis kirim ke perawat yang ter-assign (ibu_hamil_id diabaikan)
   - **Perawat**: harus specify `ibu_hamil_id` dalam request body
   - Conversation akan dibuat otomatis jika belum ada

5. **POST `/api/v1/chat/conversations/{conversation_id}/mark-read`**
   - Mark messages as read
   - Jika `message_ids` diisi, hanya message tersebut yang di-mark
   - Jika `message_ids` kosong/null, semua unread messages akan di-mark

6. **GET `/api/v1/chat/conversations/{conversation_id}/unread-count`**
   - Get jumlah unread messages

#### WebSocket API

**WS `/api/v1/ws/chat/{conversation_id}?token={jwt_token}`**

- Connect ke WebSocket untuk real-time updates
- Query parameter `token`: JWT token untuk authentication
- Events:
  - `connection`: Konfirmasi koneksi berhasil
  - `new_message`: Broadcast ketika ada message baru
  - `read_receipt`: Broadcast ketika messages di-mark as read
  - `ping`/`pong`: Heartbeat untuk keep-alive

## Best Practices

### 1. Authorization

- Hanya **ibu_hamil** dan **perawat** yang bisa mengakses chat
- Ibu hamil hanya bisa chat dengan perawat yang ter-assign ke mereka
- Perawat hanya bisa chat dengan ibu hamil yang ter-assign ke mereka
- Super admin tidak bisa mengakses chat (read-only untuk data lain)

### 2. Real-time Updates

**Recommended Flow:**

1. **Flutter App (Ibu Hamil):**
   - Connect ke WebSocket saat membuka chat screen
   - Listen untuk `new_message` events
   - Update UI secara real-time
   - Disconnect saat keluar dari chat screen

2. **Next.js Web (Perawat):**
   - Connect ke WebSocket saat membuka chat screen
   - Listen untuk `new_message` events
   - Update UI secara real-time
   - Implement reconnection logic jika connection terputus

### 3. Message Pagination

- Gunakan pagination untuk load messages (default: 50 messages per request)
- Load oldest messages first untuk chat UI
- Implement "load more" untuk load older messages
- Cache messages di client untuk performa lebih baik

### 4. Read Receipts

- Mark messages as read saat user membuka conversation
- Mark messages as read saat user scroll ke message tersebut
- Broadcast read receipt via WebSocket untuk update real-time

### 5. Error Handling

- Handle WebSocket disconnection gracefully
- Implement reconnection logic dengan exponential backoff
- Fallback ke REST API polling jika WebSocket tidak available
- Show appropriate error messages ke user

## Usage Examples

### Flutter (Ibu Hamil)

```dart
// 1. Connect WebSocket
final ws = WebSocket.connect(
  'ws://your-api.com/api/v1/ws/chat/$conversationId?token=$token'
);

// 2. Listen for messages
ws.listen((message) {
  final data = jsonDecode(message);
  if (data['type'] == 'new_message') {
    // Update UI with new message
    updateChatUI(data['message']);
  }
});

// 3. Send message via REST API
final response = await http.post(
  Uri.parse('https://your-api.com/api/v1/chat/messages'),
  headers: {'Authorization': 'Bearer $token'},
  body: jsonEncode({
    'message_text': 'Hello, perawat!',
  }),
);
```

### Next.js (Perawat)

```typescript
// 1. Connect WebSocket
const ws = new WebSocket(
  `ws://your-api.com/api/v1/ws/chat/${conversationId}?token=${token}`
);

// 2. Listen for messages
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'new_message') {
    // Update UI with new message
    setMessages(prev => [...prev, data.message]);
  }
};

// 3. Send message via REST API
const response = await fetch('https://your-api.com/api/v1/chat/messages', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    message_text: 'Hello, ibu hamil!',
    ibu_hamil_id: ibuHamilId, // Required for perawat
  }),
});
```

## Database Migration

Setelah menambahkan models baru, jalankan migration:

```bash
# Generate migration (jika menggunakan Alembic)
alembic revision --autogenerate -m "Add chat tables"

# Apply migration
alembic upgrade head
```

Atau create tables manually:

```sql
-- Create conversations table
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    ibu_hamil_id INTEGER NOT NULL REFERENCES ibu_hamil(id) ON DELETE CASCADE,
    perawat_id INTEGER NOT NULL REFERENCES perawat(id) ON DELETE CASCADE,
    last_message_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(ibu_hamil_id, perawat_id)
);

CREATE INDEX idx_conversation_ibu_hamil ON conversations(ibu_hamil_id, last_message_at);
CREATE INDEX idx_conversation_perawat ON conversations(perawat_id, last_message_at);

-- Create messages table
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE SET NULL,
    message_text TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_message_conversation_created ON messages(conversation_id, created_at);
CREATE INDEX idx_message_unread ON messages(conversation_id, is_read, created_at);
```

## Security Considerations

1. **Authentication**: Semua endpoints memerlukan JWT token
2. **Authorization**: User hanya bisa mengakses conversations mereka sendiri
3. **Input Validation**: Message text dibatasi max 5000 karakter
4. **Rate Limiting**: Consider implement rate limiting untuk prevent spam
5. **WebSocket Security**: Validate token di WebSocket connection

## Performance Optimization

1. **Database Indexes**: Sudah dioptimalkan dengan indexes untuk query performance
2. **Pagination**: Gunakan pagination untuk messages (default 50)
3. **WebSocket Connection Pooling**: Manage connections efficiently
4. **Message Caching**: Cache messages di client untuk reduce API calls

## Future Enhancements

- [ ] Typing indicators
- [ ] File attachments (images, documents)
- [ ] Message reactions
- [ ] Message search
- [ ] Message deletion (soft delete)
- [ ] Push notifications untuk new messages
- [ ] Message delivery status (sent, delivered, read)
