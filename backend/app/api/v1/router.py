from fastapi import APIRouter
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.database import router as database_router
from app.api.v1.endpoints.incidents import router as incidents_router
from app.api.v1.endpoints.agent_executions import router as agent_executions_router
from app.api.v1.endpoints.patches import router as patches_router
from app.integrations.switch.router import router as switch_router

router = APIRouter()
router.include_router(health_router, tags=["Health"])
router.include_router(database_router, tags=["Database"])
router.include_router(incidents_router, tags=["Incidents"])
router.include_router(agent_executions_router, tags=["Agent Executions"])
router.include_router(patches_router, tags=["Code Patches"])
router.include_router(switch_router, tags=["Integrations"])
