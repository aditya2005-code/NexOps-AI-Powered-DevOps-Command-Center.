from fastapi import APIRouter
from app.integrations.switch.listener import get_switch_listener
from app.integrations.switch.schemas import SwitchStatusResponse
from app.schemas.common import BaseResponse

router = APIRouter()


@router.get(
    "/integrations/switch/status",
    response_model=BaseResponse[SwitchStatusResponse],
    summary="Switch Integration Status",
    description="Returns current connection lifecycle state and health of the Switch Agent Bridge integration.",
)
async def get_switch_status() -> BaseResponse[SwitchStatusResponse]:
    """Retrieve verified connection and health status of Switch integration."""
    listener = get_switch_listener()
    status_data = listener.get_status()
    return BaseResponse(
        success=True,
        message="Switch integration status retrieved successfully",
        data=status_data,
    )

