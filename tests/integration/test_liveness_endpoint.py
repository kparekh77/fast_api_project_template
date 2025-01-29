import pytest
from httpx import Response

from model.status.response import Status, State
from integration.utils import given_a_get_request


@pytest.fixture(autouse=True)
def response(client) -> Response:
    return given_a_get_request(client, "/health")


def test_should_return_200(response):
    assert response.is_success, "Should return a 200 success status"


def test_should_return_status_model(response):
    expected_status = Status(status=State.OK, message="Service is healthy.")
    actual_status = Status(**response.json())
    assert expected_status == actual_status
