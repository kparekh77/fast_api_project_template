import uuid
from fastapi import status
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

# Test POST /resources
def test_create_resource_success(create_request):
    response = client.post("/api/v1/resources", json=create_request)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == create_request["name"]
    assert data["description"] == create_request["description"]
    assert "id" in data

def test_create_resource_conflict(create_request, mock_db):
    # First creation
    response1 = client.post("/api/v1/resources", json=create_request)
    assert response1.status_code == status.HTTP_201_CREATED

    # Second creation with the same name should conflict
    response2 = client.post("/api/v1/resources", json=create_request)
    assert response2.status_code == status.HTTP_409_CONFLICT
    assert response2.json()["detail"] == "Resource already exists."

def test_create_resource_bad_request():
    # Missing required field 'name'
    bad_request = {
        "description": "Missing name field."
    }
    response = client.post("/api/v1/resources", json=bad_request)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

# Test GET /resources
def test_get_resources_success(sample_resource, mock_db):
    resource_id = uuid.uuid4()
    mock_db[resource_id] = sample_resource

    response = client.get("/api/v1/resources")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["name"] == sample_resource["name"]

def test_get_resources_empty():
    response = client.get("/api/v1/resources")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0

# Test GET /resources/{resource_id}
def test_get_resource_success(sample_resource, mock_db):
    resource_id = uuid.uuid4()
    mock_db[resource_id] = sample_resource

    response = client.get(f"/api/v1/resources/{resource_id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(resource_id)
    assert data["name"] == sample_resource["name"]

def test_get_resource_not_found():
    non_existent_id = uuid.uuid4()
    response = client.get(f"/api/v1/resources/{non_existent_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Resource not found."

# Test PUT /resources/{resource_id}
def test_update_resource_success(sample_resource, update_request, mock_db):
    resource_id = uuid.uuid4()
    mock_db[resource_id] = sample_resource

    response = client.put(f"/api/v1/resources/{resource_id}", json=update_request)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(resource_id)
    assert data["name"] == update_request["name"]
    assert data["description"] == update_request["description"]

def test_update_resource_not_found(update_request):
    non_existent_id = uuid.uuid4()
    response = client.put(f"/api/v1/resources/{non_existent_id}", json=update_request)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Resource not found."

def test_update_resource_bad_request():
    # Invalid UUID format
    invalid_id = "invalid-uuid"
    update_request = {
        "name": "Invalid Update",
        "description": "Invalid UUID format."
    }
    response = client.put(f"/api/v1/resources/{invalid_id}", json=update_request)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

# Test PATCH /resources/{resource_id}
def test_partially_update_resource_success(sample_resource, mock_db):
    resource_id = uuid.uuid4()
    mock_db[resource_id] = sample_resource

    partial_update = {
        "description": "Partially updated description."
    }

    response = client.patch(f"/api/v1/resources/{resource_id}", json=partial_update)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(resource_id)
    assert data["name"] == sample_resource["name"]  # Unchanged
    assert data["description"] == partial_update["description"]

def test_partially_update_resource_not_found():
    non_existent_id = uuid.uuid4()
    partial_update = {
        "description": "Attempting to update non-existent resource."
    }
    response = client.patch(f"/api/v1/resources/{non_existent_id}", json=partial_update)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Resource not found."

def test_partially_update_resource_bad_request():
    # Invalid request body
    invalid_update = {
        "unknown_field": "This field does not exist."
    }
    resource_id = uuid.uuid4()
    response = client.patch(f"/api/v1/resources/{resource_id}", json=invalid_update)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

# Test DELETE /resources/{resource_id}
def test_delete_resource_success(sample_resource, mock_db):
    resource_id = uuid.uuid4()
    mock_db[resource_id] = sample_resource

    response = client.delete(f"/api/v1/resources/{resource_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert resource_id not in mock_db

def test_delete_resource_not_found():
    non_existent_id = uuid.uuid4()
    response = client.delete(f"/api/v1/resources/{non_existent_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Resource not found."

def test_delete_resource_bad_request():
    # Invalid UUID format
    invalid_id = "invalid-uuid"
    response = client.delete(f"/api/v1/resources/{invalid_id}")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
