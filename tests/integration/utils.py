from httpx import Response
from starlette.testclient import TestClient


def given_a_get_request(client: TestClient, endpoint: str) -> Response:
    return client.get(endpoint)


def given_a_post_request(client: TestClient, endpoint: str, data: dict) -> Response:
    return client.post(endpoint, json=data)
