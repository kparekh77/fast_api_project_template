import pytest
from httpx import Response

from integration.utils import given_a_get_request


@pytest.fixture(autouse=True)
def response(client) -> Response:
    return given_a_get_request(client, "/ready")


def test_should_return_200(response):
    assert response.is_success, "Should return a 200 success status"


def test_should_return_empty_body(response):
    assert response.text == "null", "Should return an empty body"
