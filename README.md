# WellMom Backend

Backend API untuk sistem WellMom - Aplikasi monitoring kesehatan ibu hamil.

## Tech Stack

- **Framework:** FastAPI
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **Authentication:** JWT
- **Real-time:** WebSocket

## Features

### User Management
- Multi-role authentication (Ibu Hamil, Perawat, Puskesmas, Kerabat)
- JWT-based authentication
- Profile management

### Health Monitoring
- Health record management
- Risk level assessment (rendah/sedang/tinggi)
- IoT sensor integration

### Communication
- Real-time chat between Ibu Hamil and Perawat
- WebSocket for instant messaging
- AI-powered chatbot for health questions

### Notification System
- In-app notifications
- Multiple notification types (health alerts, reminders, assignments)
- Priority levels (low, normal, high, urgent)
- WhatsApp integration (future)
- See [NOTIFICATION_API.md](./NOTIFICATION_API.md) for detailed API documentation

### Forum
- Community forum for pregnant women
- Post categories and replies
- Like functionality

### Administration
- Puskesmas management
- Perawat assignment
- Patient transfer between perawat

## Project Structure

```
app/
├── api/
│   └── v1/
│       ├── endpoints/      # API endpoints
│       └── api.py          # Router aggregator
├── core/                   # Core configurations
├── crud/                   # Database operations
├── models/                 # SQLAlchemy models
├── schemas/                # Pydantic schemas
├── services/               # Business logic services
└── main.py                 # Application entry point
```

## Getting Started

### Prerequisites

- Python 3.10+
- PostgreSQL 14+
- Docker (optional)

### Installation

1. Clone the repository
```bash
git clone <repository-url>
cd wellmom-backend
```

2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Configure environment
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Create database tables
```bash
python create_tables.py
```

6. Run the server
```bash
uvicorn app.main:app --reload
```

### Using Docker

```bash
docker-compose up -d
```

## API Documentation

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Feature-specific Documentation

- [Notification API](./NOTIFICATION_API.md) - Notification system documentation

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | - |
| `SECRET_KEY` | JWT secret key | - |
| `FRONTEND_BASE_URL` | Frontend application URL | - |
| `OPENAI_API_KEY` | OpenAI API key for chatbot | - |

## Database Migrations

Migration files are located in the `migrations/` directory. Run them manually or use the provided scripts.

## Testing

```bash
pytest
```

## License

Proprietary - All rights reserved.
