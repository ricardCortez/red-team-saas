# Red Team SaaS Professional

Red Team Security Audit Platform with AI Integration.

## Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Git

### Setup

1. **Clone and setup**
```bash
cd red-team-saas
cp backend/.env.example backend/.env
```

2. **Start services**
```bash
docker-compose up -d
```

3. **Access API**
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Test Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "user123",
    "password": "SecurePass123!",
    "full_name": "Full Name"
  }'

# Login
curl -X POST "http://localhost:8000/api/v1/auth/login?email=user@example.com&password=SecurePass123!"

# Get user info (use token from login)
curl "http://localhost:8000/api/v1/auth/me?token=YOUR_TOKEN"
```

## Architecture

- **Backend**: FastAPI
- **Database**: PostgreSQL
- **Cache**: Redis
- **Queue**: Celery

## Development

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Run tests
pytest

# Format code
black .

# Lint
flake8 .
```

## License

MIT
