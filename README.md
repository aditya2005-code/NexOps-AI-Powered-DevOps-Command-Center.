# NexOps — AI-Powered DevOps Command Center

NexOps is an AI-native DevOps platform that unifies incident management, infrastructure observability, and intelligent automation through LangChain/LangGraph-powered agents.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, TypeScript 5.8, Vite 6, Tailwind CSS v4, shadcn/ui, TanStack Query, Recharts, Lucide React, Sonner |
| Backend | FastAPI, Python 3.11, Pydantic v2, Pydantic Settings, SQLAlchemy 2.0 (async), Alembic |
| AI / Agents | LangChain, LangGraph, Gemini 1.5 Flash / Groq Llama (Multi-Agent Swarm) |
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
│   │   ├── components/      # Common & dashboard components (MetricCard, IncidentOverview, etc.)
│   │   ├── constants/       # Realistic telemetry, incident & agent demo data
│   │   ├── hooks/           # Custom React hooks (useHealth, etc.)
│   │   ├── layouts/         # AppLayout, collapsible Sidebar & TopNavbar
│   │   ├── pages/           # Command Center, Projects, Incidents, Agents, Audit Logs, Settings
│   │   ├── services/        # Centralized Axios API client
│   │   ├── test/            # Vitest & Testing Library test suites
│   │   └── types/           # Strict TypeScript models
│   ├── .env.example
│   ├── package.json
│   ├── eslint.config.js
│   └── vite.config.ts
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

---

## Backend Setup (Phase 1)

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

```powershell
copy .env.example .env
```

Review and adjust variables in `backend/.env` (`APP_NAME`, `APP_ENV`, `DEBUG`, `API_V1_PREFIX`, `BACKEND_CORS_ORIGINS`, `LOG_LEVEL`).

### 4. Running the Backend

Start the development server using Uvicorn:

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Running Backend Tests

<<<<<<< HEAD
Run the full test suite using pytest:

=======
>>>>>>> 86de97ca2539389ada6d917d29795fa30f43498c
```powershell
pytest -v
```

Or run the isolated database test suite:

```powershell
pytest tests/db/ -v
```

### 6. Database Migrations (Alembic)

Manage database schema revisions using Alembic:

```powershell
# Apply all pending migrations to head
alembic upgrade head

# Rollback one migration revision
alembic downgrade -1

# Generate a new autodetected migration
alembic revision --autogenerate -m "migration_description"
```

### 7. Interactive API Documentation & Health Checks

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI Schema:** [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)
- **System Health:** [http://localhost:8000/health](http://localhost:8000/health)
- **Database Health:** [http://localhost:8000/api/v1/health/database](http://localhost:8000/api/v1/health/database)

---

## Frontend Setup (Phase 2)

### 1. Installation

```powershell
cd frontend
npm install
```

### 2. Environment Configuration

```powershell
copy .env.example .env.local
```

Default configuration points to `VITE_API_BASE_URL=http://localhost:8000/api/v1`.

### 3. Running Development Server

```powershell
npm run dev
```

The Command Center will be accessible at [http://localhost:5173](http://localhost:5173).

### 4. Running Frontend Tests

```powershell
npm test
```

Runs the 7 Vitest + React Testing Library test suites covering routing, navigation, KPI cards, incident tables, and responsive sidebar.

### 5. Type Checking and Linting

```powershell
npx tsc --noEmit
npm run lint
```

### 6. Production Build

```powershell
npm run build
```

---

## Available Application Routes

| Route | Purpose | Key Features |
|-------|---------|--------------|
| `/dashboard` (or `/`) | Command Center | KPI metrics, incident velocity chart, active incident table, agent swarm status, activity feed |
| `/projects` | Monitored Projects | Multi-environment repo cards, health indicators, service counts, search filter |
| `/incidents` | Incident Queue | Severity & status filters, incident inspection drawer, root-cause hypothesis preview |
| `/agents` | AI Agent Swarm | 5 specialized agent cards (Incident Manager, Log Analyst, Code Investigator, Fix Agent, Testing Agent) |
| `/audit-logs` | Audit Trail | Structured immutable event ledger with actor filters and JSON export simulation |
| `/settings` | System Settings | General preferences, appearance density, notification channels, integration statuses |
| `*` | 404 Error View | Graceful error boundary with return navigation |
