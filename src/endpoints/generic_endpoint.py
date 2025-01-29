import uuid
from typing import Annotated, List, Optional

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field


class CreateRequest(BaseModel):
    name: str = Field(..., example="Sample Resource")
    description: Optional[str] = Field(None, example="A brief description of the resource.")

class UpdateRequest(BaseModel):
    name: Optional[str] = Field(None, example="Updated Resource Name")
    description: Optional[str] = Field(None, example="An updated description of the resource.")

class Resource(BaseModel):
    id: uuid.UUID = Field(..., example="123e4567-e89b-12d3-a456-426614174000")
    name: str = Field(..., example="Sample Resource")
    description: Optional[str] = Field(None, example="A brief description of the resource.")

class Problem(BaseModel):
    detail: str

# Initialize the APIRouter
router = APIRouter()

RESOURCE_PATH = "/resources"

x_correlation_id = Annotated[
    str,
    Header(
        description="A unique identifier for the request to track it across services.",
        example=str(uuid.uuid4()),
    ),
]

x_source = Annotated[
    Optional[str],
    Header(
        default=None,
        description="The system name that is sending this request.",
        example="ExternalSystem",
    ),
]

@router.post(
    RESOURCE_PATH,
    summary="Create a new resource.",
    description="Endpoint to create a new resource with the provided details.",
    response_model=Resource,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {"description": "Resource created successfully."},
        status.HTTP_400_BAD_REQUEST: {
            "model": Problem,
            "description": "Invalid input data.",
        },
        status.HTTP_409_CONFLICT: {
            "model": Problem,
            "description": "Resource already exists.",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": Problem,
            "description": "Internal server error.",
        },
    },
    tags=["Resources"],
)
async def create_resource(
    request: CreateRequest,
    x_correlation_id: str = x_correlation_id,
    x_source: Optional[str] = x_source,
):
    """
    Create a new resource.

    - **name**: Name of the resource.
    - **description**: (Optional) Description of the resource.
    """
    try:
        # TODO: Implement the logic to create a resource
        resource = Resource(
            id=uuid.uuid4(),
            name=request.name,
            description=request.description,
        )
        return resource
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

@router.get(
    RESOURCE_PATH,
    summary="Retrieve all resources.",
    description="Endpoint to retrieve a list of all resources.",
    response_model=List[Resource],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"description": "List of resources retrieved successfully."},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": Problem,
            "description": "Internal server error.",
        },
    },
    tags=["Resources"],
)
async def get_resources(
    x_correlation_id: str = x_correlation_id,
    x_source: Optional[str] = x_source,
):
    """
    Retrieve all resources.
    """
    try:
        # TODO: Implement the logic to retrieve resources
        resources = [
            Resource(
                id=uuid.uuid4(),
                name="Resource 1",
                description="Description for Resource 1",
            ),
            Resource(
                id=uuid.uuid4(),
                name="Resource 2",
                description="Description for Resource 2",
            ),
        ]
        return resources
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

@router.get(
    f"{RESOURCE_PATH}/{{resource_id}}",
    summary="Retrieve a single resource.",
    description="Endpoint to retrieve a single resource by its unique ID.",
    response_model=Resource,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"description": "Resource retrieved successfully."},
        status.HTTP_404_NOT_FOUND: {
            "model": Problem,
            "description": "Resource not found.",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": Problem,
            "description": "Internal server error.",
        },
    },
    tags=["Resources"],
)
async def get_resource(
    resource_id: uuid.UUID,
    x_correlation_id: str = x_correlation_id,
    x_source: Optional[str] = x_source,
):
    """
    Retrieve a single resource by its ID.

    - **resource_id**: UUID of the resource to retrieve.
    """
    try:
        # TODO: Implement the logic to retrieve a single resource
        resource = Resource(
            id=resource_id,
            name="Sample Resource",
            description="A sample resource description.",
        )
        return resource
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

@router.put(
    f"{RESOURCE_PATH}/{{resource_id}}",
    summary="Update a resource.",
    description="Endpoint to update an existing resource by its unique ID.",
    response_model=Resource,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"description": "Resource updated successfully."},
        status.HTTP_400_BAD_REQUEST: {
            "model": Problem,
            "description": "Invalid input data.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": Problem,
            "description": "Resource not found.",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": Problem,
            "description": "Internal server error.",
        },
    },
    tags=["Resources"],
)
async def update_resource(
    resource_id: uuid.UUID,
    request: UpdateRequest,
    x_correlation_id: str = x_correlation_id,
    x_source: Optional[str] = x_source,
):
    """
    Update an existing resource by its ID.

    - **resource_id**: UUID of the resource to update.
    - **name**: (Optional) New name of the resource.
    - **description**: (Optional) New description of the resource.
    """
    try:
        # TODO: Implement the logic to update a resource
        updated_resource = Resource(
            id=resource_id,
            name=request.name or "Updated Resource Name",
            description=request.description or "Updated description.",
        )
        return updated_resource
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

@router.patch(
    f"{RESOURCE_PATH}/{{resource_id}}",
    summary="Partially update a resource.",
    description="Endpoint to partially update an existing resource by its unique ID.",
    response_model=Resource,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"description": "Resource partially updated successfully."},
        status.HTTP_400_BAD_REQUEST: {
            "model": Problem,
            "description": "Invalid input data.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": Problem,
            "description": "Resource not found.",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": Problem,
            "description": "Internal server error.",
        },
    },
    tags=["Resources"],
)
async def partially_update_resource(
    resource_id: uuid.UUID,
    request: UpdateRequest,
    x_correlation_id: str = x_correlation_id,
    x_source: Optional[str] = x_source,
):
    """
    Partially update an existing resource by its ID.

    - **resource_id**: UUID of the resource to update.
    - **name**: (Optional) New name of the resource.
    - **description**: (Optional) New description of the resource.
    """
    try:
        # TODO: Implement the logic to partially update a resource
        partially_updated_resource = Resource(
            id=resource_id,
            name=request.name or "Partially Updated Resource Name",
            description=request.description or "Partially updated description.",
        )
        return partially_updated_resource
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

@router.delete(
    f"{RESOURCE_PATH}/{{resource_id}}",
    summary="Delete a resource.",
    description="Endpoint to delete a resource by its unique ID.",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_204_NO_CONTENT: {"description": "Resource deleted successfully."},
        status.HTTP_400_BAD_REQUEST: {
            "model": Problem,
            "description": "Invalid input data.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": Problem,
            "description": "Resource not found.",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": Problem,
            "description": "Internal server error.",
        },
    },
    tags=["Resources"],
)
async def delete_resource(
    resource_id: uuid.UUID,
    x_correlation_id: str = x_correlation_id,
    x_source: Optional[str] = x_source,
):
    """
    Delete a resource by its ID.

    - **resource_id**: UUID of the resource to delete.
    """
    try:
        # TODO: Implement the logic to delete a resource
        return
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
