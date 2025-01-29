from fastapi import APIRouter

from endpoints.tags import Tags
from model.status.response import Status, State

LIVENESS_PATH = "/health"

router = APIRouter()


@router.get(
    LIVENESS_PATH,
    summary="Check the health of the service. (Liveness Probe)",
    description="This endpoint will execute necessary checks to determine if the service is healthy.",
    response_model=Status,
    tags=[Tags.Observability.name],
)
async def health():
    return Status(status=State.OK, message="Service is healthy.")
