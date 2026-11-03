# NexOps Architecture

## Overview

NexOps follows a clean layered architecture:

```
frontend (React/Vite)  ←→  backend (FastAPI)  ←→  PostgreSQL
                                   ↓
                          LangChain / LangGraph agents
                                   ↓
                          LLM providers (Gemini / Groq)
```

## Layers

- **API layer** (`app/api/v1/`): HTTP endpoints, request/response models
- **Service layer** (`app/services/`): Business logic, orchestration
- **Repository layer** (`app/repositories/`): Database access, no business logic
- **Model layer** (`app/models/`): SQLAlchemy ORM models
- **Agent layer** (`app/agents/`): LangChain/LangGraph workflows and tools
- **Integration layer** (`app/integrations/`): Third-party service adapters
