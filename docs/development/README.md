# NexOps Development Guide

## Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 16 (or use `docker-compose up db`)

## Common Tasks

### Run backend tests

```bash
cd backend
.venv/Scripts/pytest tests/ -v
```

### Create a new migration

```bash
cd backend
.venv/Scripts/python -m alembic revision --autogenerate -m "description"
.venv/Scripts/python -m alembic upgrade head
```

### Add a new API endpoint

1. Create `app/api/v1/endpoints/<name>.py` with an `APIRouter`
2. Include router in `app/api/v1/router.py`
3. Add service logic in `app/services/`
4. Add repository in `app/repositories/`

### Environment variables

Copy `.env.example` to `.env` in `backend/` and fill in values before running.
