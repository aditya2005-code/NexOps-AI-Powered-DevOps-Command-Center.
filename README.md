# NexOps — AI-Powered DevOps Command Center

NexOps is an AI-native DevOps platform that unifies incident management, infrastructure observability, and intelligent automation through LangChain/LangGraph-powered agents.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, TypeScript, Vite 6, Tailwind CSS v4, shadcn/ui |
| Backend | FastAPI, Python 3.11, Pydantic v2, Pydantic Settings, SQLAlchemy 2.0 (async), Alembic |
| AI / Agents | LangChain, LangGraph, Gemini 1.5 Flash / Groq Llama (Phase 2+) |
| Database | PostgreSQL 16 (Neon cloud or local Docker) |
| Auth | JWT (python-jose), bcrypt (passlib) |

## Project Structure

```
NexOps/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Versioned API routes & endpoints
│   │   │   ├── router.py
│   │   │   └── endpoints/health.py
│   │   ├── agents/          # LangChain/LangGraph agent workflows
│   │   ├── core/            # Config, logging, security, centralized exceptions
│   │   ├── db/              # SQLAlchemy session and base
│   │   ├── integrations/    # Third-party adapters (Switch, etc.)
│   │   ├── models/          # ORM models
│   │   ├── repositories/    # Data access layer
│   │   ├── schemas/         # Pydantic request/response & common envelopes
│   │   └── services/        # Business logic
│   ├── alembic/             # Database migrations
│   ├── tests/               # pytest test suite
│   ├── .env.example
│   ├── requirements.txt
│   └── pytest.ini
├── frontend/
│   ├── src/
│   │   ├── components/      # React components (layout/, ui/, common/)
│   │   ├── hooks/           # Custom React hooks
│   │   ├── pages/           # Page-level components
│   │   ├── services/        # API client (axios)
│   │   └── types/           # TypeScript interfaces
│   ├── .env.example
│   └── package.json
├── docs/
│   ├── architecture/
│   ├── api/
│   └── development/
├── docker-compose.yml       # Local PostgreSQL
├── DEVELOPMENT_PROGRESS.md  # Project progress tracker
└── README.md
```

## Prerequisites

- **Python 3.11+** (Windows 64-bit or Unix)
- **Node.js 20+** and npm
- **PostgreSQL 16** (Neon or local Docker)

## Backend Setup

### 1. Virtual Environment Activation

The project uses the existing dedicated virtual environment located at `backend/.venv`.

**Windows PowerShell:**
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
cd backend
source .venv/bin/activate
```

### 2. Dependency Installation

Install dependencies using the virtual environment's pip:

```powershell
python -m pip install -r requirements.txt
```

### 3. Environment Configuration

Copy the example configuration file:

```powershell
copy .env.example .env
```

Review and adjust variables in `backend/.env`:

| Variable | Default | Purpose |
|----------|---------|---------|
| `APP_NAME` | `NexOps` | Application display name |
| `APP_ENV` | `development` | Runtime environment name |
| `DEBUG` | `true` | Enable verbose debugging and logging |
| `API_V1_PREFIX` | `/api/v1` | Prefix for version 1 API endpoints |
| `BACKEND_CORS_ORIGINS` | `http://localhost:5173` | Allowed CORS origins (comma-separated or list) |
| `LOG_LEVEL` | `INFO` | Application log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `DATABASE_URL` | `postgresql+psycopg://...` | PostgreSQL connection string (future phases) |
| `SECRET_KEY` | `change-me-in-production` | JWT signing secret key |
| `GOOGLE_API_KEY` | `""` | Google Gemini API key (future phases) |
| `GROQ_API_KEY` | `""` | Groq API key (future phases) |

### 4. Running the Backend

Start the development server using Uvicorn:

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Running Backend Tests

Run the test suite using pytest:

```powershell
pytest -v
```

### 6. Interactive API Documentation

Once the server is running, explore the API at:
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI Schema:** [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

## Frontend Setup

```bash
cd frontend
npm install

# Configure environment
copy .env.example .env.local

# Run development server
npm run dev
```

The frontend will be available at [http://localhost:5173](http://localhost:5173).

## Testing Commands Summary

- **Backend tests:** `pytest -v` (inside `backend/` directory)
- **Frontend build test:** `npm run build` (inside `frontend/` directory)
- **Frontend type check:** `npx tsc --noEmit` (inside `frontend/` directory)
