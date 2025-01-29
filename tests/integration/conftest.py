"""
conftest.py: sharing fixtures across multiple files

The conftest.py file serves as a means of providing fixtures for an entire directory.
Fixtures defined in a conftest.py can be used by any test in that package without needing
to import them (pytest will automatically discover them).

You can have multiple nested directories/packages containing your tests, and each directory
can have its own conftest.py with its own fixtures, adding on to the ones provided by the
conftest.py files in parent directories.
"""

from unittest.mock import patch

import logging_http_client
import pytest
from starlette.testclient import TestClient
from wiremock.client import Mappings, Mapping, MappingRequest, MappingResponse
from wiremock.constants import Config
from wiremock.resources.near_misses import NearMissMatchPatternRequest
from wiremock.resources.requests.resource import Requests
from wiremock.testing.testcontainer import wiremock_container

from config.environment_loader import Environment

CONFIG_DISABLED_JSON = "path for kill_switch_config_disabled.json"


@pytest.fixture(scope="function", autouse=True)
def with_kill_switch_disabled():
    """
    Automatically sets the kill switch to DISABLED for every test in this file,
    so we don't get 503 or FileNotFoundError.
    """
    Environment.KILL_SWITCH_CONFIG_PATH.set(CONFIG_DISABLED_JSON)
    yield
    Environment.KILL_SWITCH_CONFIG_PATH.set(CONFIG_DISABLED_JSON)


@pytest.fixture(scope="session", autouse=True)
def mock_secret_manager():
    """
    We do not test the functionality of GCP managed services at the integration level
    """
    with patch("clients.gcp_client.secret_manager_client.SecretManager") as mock_secret_manager:
        yield mock_secret_manager


@pytest.fixture(scope="module")
def client(wiremock_server) -> TestClient:
    from main import app

    with TestClient(app) as client:
        logging_http_client.enable_request_body_logging()
        logging_http_client.enable_response_body_logging()
        yield client
        logging_http_client.enable_request_body_logging(enable=False)
        logging_http_client.enable_response_body_logging(enable=False)

@pytest.fixture(scope="session")
def wiremock_server() -> wiremock_container:
    with wiremock_container(secure=False) as server:
        # Configure the base URL for the WireMock server
        Config.base_url = server.get_url("__admin")

        def for_endpoint_with_multiple_responses(
            request_url,
            request_method,
            response_sequence,
            request_query_parameters=None,
            request_headers=None,
            request_body=None,
            response_status=200,
            response_headers=None,
            persistent=False,
        ):
            scenario_name = "Sequential Responses"
            for index, response in enumerate(response_sequence):
                mapping = Mapping(
                    request=MappingRequest(
                        url=request_url,
                        method=request_method,
                        query_parameters=request_query_parameters,
                        headers=request_headers,
                        body_patterns=request_body,
                    ),
                    response=MappingResponse(
                        status=response_status,
                        json_body=response,
                        headers=response_headers or {"content-type": "application/json"},
                    ),
                    scenario_name=scenario_name,
                    required_scenario_state=response.get(
                        "required_scenario_state", "Started" if index == 0 else f"State {index}"
                    ),
                    new_scenario_state=response.get("new_scenario_state", f"State {index + 1}"),
                )
                Mappings.create_mapping(mapping)

        def for_endpoint(
            request_url,
            request_method,
            request_query_parameters=None,
            request_headers=None,
            request_body=None,
            response_status=200,
            response_body=None,
            response_body_json=None,
            response_headers=None,
            persistent=False,
        ) -> None:
            """
            This is a syntactic sugar method to create a mapping for a given endpoint.

            :param request_method: The HTTP method to MATCH
            :param request_url: The URL to MATCH
            :param request_query_parameters: The query parameters to MATCH
            :param request_headers: The headers to MATCH
            :param request_body: The body to MATCH
            :param response_status: The status code to RETURN
            :param response_body: The body to RETURN
            :param response_body_json: The JSON body to RETURN (takes precedence over response_body)
            :param response_headers: The headers to RETURN
            :param persistent: Whether the mapping should be persisted or not

            :return: None (the mapping is created)
            """

            mapping_request = MappingRequest(
                url=request_url,
                method=request_method,
                query_parameters=request_query_parameters,
                headers=request_headers,
                body_patterns=request_body,
            )

            mapping_response = MappingResponse(
                status=response_status,
                body=response_body,
                headers=response_headers or {"content-type": "application/json"},
            )

            if response_body_json:
                mapping_response.json_body = response_body_json
            elif response_body:
                mapping_response.body = response_body
            Mappings.create_mapping(
                Mapping(
                    request=mapping_request,
                    response=mapping_response,
                    persistent=persistent,
                )
            )

        # Attach the method to the wm instance
        server.for_endpoint = for_endpoint
        server.for_endpoint_with_multiple_responses = for_endpoint_with_multiple_responses

        def verify_requests_were_matched(*urls: str):
            urls_not_matched = []
            for url in urls:
                did_not_match = (
                    Requests.get_matching_request_count(request=NearMissMatchPatternRequest(url=url)).count == 0
                )
                if did_not_match:
                    urls_not_matched.append(url)
            if urls_not_matched:
                pytest.fail(f"The following requests were not matched: {urls_not_matched}")
            assert len(Requests.get_unmatched_requests().requests) == 0, "We should not have any unmatched requests."

        server.verify_requests_were_matched = verify_requests_were_matched

        yield server


@pytest.fixture(scope="function", autouse=True)
def clear_wiremock_stubs_after_each_test(wiremock_server):
    yield
    Mappings.reset_mappings()
    Mappings.delete_all_mappings()


@pytest.fixture
def sample_resource():
    return {
        "id": str(uuid.uuid4()),
        "name": "Sample Resource",
        "description": "A brief description of the resource."
    }

@pytest.fixture
def create_request():
    return {
        "name": "New Resource",
        "description": "Description for the new resource."
    }

@pytest.fixture
def update_request():
    return {
        "name": "Updated Resource Name",
        "description": "Updated description."
    }

# Mock the in-memory mock_db from the router
@pytest.fixture(autouse=True)
def mock_db():
    with patch.dict("routers.resources_router.mock_db", {}, clear=True):
        yield
