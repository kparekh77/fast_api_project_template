from fastapi import APIRouter

from endpoints.tags import Tags

READINESS_PATH = "/ready"

router = APIRouter()


@router.get(
    READINESS_PATH,
    summary="Check if the service is ready to receive requests. (Readiness Probe)",
    description="This does not return a response body, only HTTP 200 status codes indicating service is ready.",
    tags=[Tags.Observability.name],
)
async def ready():
    pass
