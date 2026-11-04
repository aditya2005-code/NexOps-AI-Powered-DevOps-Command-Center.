# NexOps — AI-Powered DevOps Command Center

NexOps is an AI-native DevOps command center that unifies real-time incident intake, infrastructure observability, automated triage, and bidirectional collaboration between humans and AI agents.

---

## Architecture

```mermaid
flowchart TD
    subgraph HumanChat["Human Operators (Chat / Switch Rooms)"]
        ChatUser["DevOps Engineer / Operator"]
    end

    subgraph SwitchPlatform["Switch Platform"]
        SwitchBridge["Switch Agent Bridge (WebSocket)"]
        SwitchCore["Switch Core (/ops Gateway)"]
    end

    subgraph NexOpsBackend["NexOps FastAPI Backend"]
        Listener["SwitchListener (WebSocket)"]
        Intake["SwitchIntakeService (Deduplication & Intake)"]
        Client["SwitchClient (HTTP Outbound)"]
        API["FastAPI REST API (/api/v1)"]
    end

    subgraph Storage["Persistence Layer"]
        Postgres[("Neon PostgreSQL Database")]
        Alembic["Alembic Migrations"]
    end

    subgraph NexOpsFrontend["NexOps React Command Center"]
        Dashboard["Dashboard & Command Center"]
        Incidents["Incident Queue & Details"]
        SwitchUI["Switch Bridge Integration Console"]
    end

    ChatUser -->|Reports incident| SwitchBridge
    SwitchBridge -->|WebSocket event frame| Listener
    Listener -->|Dispatch| Intake
    Intake -->|Atomic commit| Postgres
    Intake -->|Post-commit acknowledgement| Client
    Client -->|POST /ops send_message| SwitchCore
    SwitchCore -->|Thread confirmation| ChatUser

    Postgres -->|Queries| API
    API -->|GET /incidents| Incidents
    API -->|GET /integrations/switch/status| SwitchUI
    API -->|Real-time status & metrics| Dashboard
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19, TypeScript 5.8, Vite 6, Tailwind CSS v4, shadcn/ui, TanStack Query v5, Recharts, Lucide React, Sonner |
| **Backend** | FastAPI, Python 3.11, Pydantic v2, Pydantic Settings, SQLAlchemy 2.0, Alembic, HTTPX, WebSockets |
| **Integrations** | Switch Agent Bridge (WebSocket stream & HTTP `/ops` outbound dispatcher) |
| **Database** | Neon Serverless PostgreSQL / Local PostgreSQL 16 via psycopg3 |
| **Testing** | pytest, pytest-asyncio, anyio, Vitest, React Testing Library, jsdom |

---

## Project Structure

```text
NexOps/
├── backend/
│   ├── app/
│   │   ├── api/v1/                  # Versioned API routes
│   │   │   ├── endpoints/
│   │   │   │   ├── health.py        # System health & echo validation
│   │   │   │   ├── database.py      # Database connectivity health probe
│   │   │   │   └── incidents.py     # Incident query, detail, stats & events API
│   │   │   └── router.py            # API v1 aggregator
│   │   ├── core/                    # Config, logging, centralized exceptions
│   │   ├── db/                      # Sessionmaker, base, dependencies
│   │   ├── integrations/
│   │   │   └── switch/              # Official Switch Agent Bridge integration
│   │   │       ├── client.py        # HTTP async client targeting /ops
│   │   │       ├── listener.py      # WebSocket connection & event loop
│   │   │       ├── service.py       # SwitchIntakeService & composite deduplication
│   │   │       ├── schemas.py       # Protocol & status models
│   │   │       └── router.py        # GET /api/v1/integrations/switch/status
│   │   ├── models/                  # SQLAlchemy ORM models (Project, Incident, AuditLog, etc.)
│   │   ├── repositories/            # Data access layer
│   │   └── schemas/                 # Pydantic request/response envelopes
│   ├── alembic/                     # Database migrations
│   │   └── versions/                # Migration scripts (e.g. add_incident_source_id)
│   ├── tests/                       # Comprehensive pytest suite (66 tests)
│   ├── .env.example                 # Backend environment variable template
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/              # UI badges, cards, layouts, dialogs
│   │   ├── hooks/                   # useSwitchStatus, useIncidents, useHealth
│   │   ├── layouts/                 # AppLayout, Sidebar, TopNavbar
│   │   ├── pages/
│   │   │   ├── dashboard/           # Command Center with live metrics & Switch status
│   │   │   ├── incidents/           # Live PostgreSQL incidents & simulation toggle
│   │   │   ├── integrations/        # Dedicated Switch Collaboration Bridge Console
│   │   │   ├── settings/            # Settings with embedded Switch diagnostics
│   │   │   └── projects/            # Monitored projects
│   │   ├── services/                # Axios API services (api, switchService, incidentService)
│   │   ├── test/                    # Vitest test suites (16 tests)
│   │   └── types/                   # TypeScript interfaces (switch, incident, etc.)
│   ├── .env.example                 # Frontend environment template
│   └── package.json
└── README.md
```

---

## Prerequisites

- **Python 3.11+** (Windows 64-bit or Linux/macOS)
- **Node.js 20+** and npm
- **PostgreSQL 16** (Neon serverless cloud or local PostgreSQL)

---

## Backend Installation & Setup

### 1. Activate Dedicated Virtual Environment

The project uses the pre-configured virtual environment located at `backend/.venv`.

**Windows PowerShell:**
```powershell
Set-Location D:\Projects\NexOps\backend
.\.venv\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
cd backend
source .venv/bin/activate
```

### 2. Install Dependencies

```powershell
python -m pip install -r requirements.txt
```

### 3. Environment Configuration

Copy the template environment file:

```powershell
Copy-Item .env.example .env
```

Configure backend keys in `backend/.env`:

```env
APP_NAME="NexOps Backend"
APP_ENV="development"
DEBUG=true
API_V1_PREFIX="/api/v1"
BACKEND_CORS_ORIGINS=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]
DATABASE_URL="postgresql+psycopg://user:password@localhost:5432/nexops"

# Switch Integration Settings
SWITCH_ENABLED=false
SWITCH_CORE_URL="http://localhost:8080"
SWITCH_API_KEY="sk_live_replace_with_actual_switch_token"
SWITCH_AGENT_ID="nexops-agent"
SWITCH_ROOM_PROJECT_MAPPING='{"ops-payments": "Payments API", "devops-war-room": "Core Gateway"}'
```

### 4. Database Migrations (Alembic)

Run pending schema migrations against PostgreSQL:

```powershell
# Upgrade schema to head
alembic upgrade head

# Revert previous migration
alembic downgrade -1
```

> **Note on Neon Cloud Database:** To run against remote Neon PostgreSQL, set `DATABASE_URL` in `backend/.env` to your pooled Neon connection string (`postgresql+psycopg://user:password@ep-xyz.us-east-2.aws.neon.tech/nexops?sslmode=require`) and execute `alembic upgrade head`.

### 5. Start Backend Development Server

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at [http://localhost:8000](http://localhost:8000).

---

## Frontend Installation & Setup

### 1. Install Dependencies

```powershell
Set-Location D:\Projects\NexOps\frontend
npm install
```

### 2. Environment Configuration

```powershell
Copy-Item .env.example .env
```

`frontend/.env` contains:
```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

### 3. Start Development Server

```powershell
npm run dev
```

The NexOps Command Center will open at [http://localhost:5173](http://localhost:5173).

---

## Switch Integration Guide

NexOps implements bidirectional integration with the official [Switch Platform](https://github.com/sandbox-quantum/switch):

### Inbound Intake
1. Human operators post incident alerts in a mapped Switch room (e.g. `ops-payments`).
2. Switch Agent Bridge forwards WebSocket event frames (`room_message`) to NexOps.
3. `SwitchIntakeService`:
   - Validates event payload integrity.
   - Enforces room authorization against `SWITCH_ROOM_PROJECT_MAPPING`.
   - Derives a collision-resistant composite idempotency key (`switch:{room_id}:{message_id}`).
   - Creates an `Incident` (status `OPEN`, source `switch`), an `IncidentEvent`, and an `AuditLog` entry in a single atomic transaction.

### Outbound Acknowledgement
1. Immediately post-commit, `SwitchClient` dispatches a confirmation message to Switch Core `/ops` using `send_message`.
2. The Switch room thread receives confirmation with the created Incident ID and project status.
3. Outbound delivery failures are safely audited without rolling back or deleting the created incident.

---

## API Documentation

Interactive OpenAPI documentation is available when the backend server is running:

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **System Health:** `GET http://localhost:8000/health`
- **Database Connectivity:** `GET http://localhost:8000/api/v1/health/database`
- **Switch Status:** `GET http://localhost:8000/api/v1/integrations/switch/status`
- **List Incidents:** `GET http://localhost:8000/api/v1/incidents?skip=0&limit=50&status=OPEN`
- **Incident Detail:** `GET http://localhost:8000/api/v1/incidents/{incident_id}`
- **Incident Events:** `GET http://localhost:8000/api/v1/incidents/{incident_id}/events`
- **Incident Summary Stats:** `GET http://localhost:8000/api/v1/incidents/stats/summary`

---

## Running Automated Tests

### Backend Test Suite (pytest)

```powershell
Set-Location D:\Projects\NexOps\backend
$env:PYTHONPATH="backend"
.\.venv\Scripts\pytest.exe tests/ -v
```

**Results:** 66 passed (Database architecture, core health, Switch protocol client, listener, status, intake & deduplication, and incident REST API).

### Frontend Test Suite (Vitest)

```powershell
Set-Location D:\Projects\NexOps\frontend
npm test
```

**Results:** 16 passed (Switch connection states, loading, empty states, polling, incident rendering, API failure handling, and application routing).

### Frontend Production Build Verification

```powershell
Set-Location D:\Projects\NexOps\frontend
npm run build
```

---

## Known Limitations & Security Boundaries

1. **Transactional Outbox:** NexOps Phase 4 dispatches outbound Switch acknowledgements directly via HTTP post-commit. In the event of a network partition between NexOps and Switch Core, the incident is safely retained in PostgreSQL, but no asynchronous persistent outbox queue is currently present to retry the notification.
2. **Untrusted Input Sanitation:** Incoming Switch room messages are treated strictly as passive text data (`Incident.description`). No dynamic SQL, code execution, shell commands, or LLM agent prompts are invoked on incoming content.
3. **Secret Redaction:** `SWITCH_API_KEY` is strictly managed server-side. It is never exposed to the browser, logs, or status endpoints.
