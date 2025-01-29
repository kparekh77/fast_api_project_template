import pytest

from config.environment_loader import Environment
from endpoints.liveness_endpoint import LIVENESS_PATH
from endpoints.readiness_endpoint import READINESS_PATH
from integration.utils import given_a_get_request
from tests.helpers import resource_path_for

CONFIG_ENABLED_JSON = resource_path_for("kill_switch_config_enabled.json")


@pytest.fixture(scope="function")
def with_kill_switch_enabled():
    Environment.KILL_SWITCH_CONFIG_PATH.set(CONFIG_ENABLED_JSON)
    yield
    Environment.KILL_SWITCH_CONFIG_PATH.set(CONFIG_ENABLED_JSON)


@pytest.mark.parametrize(
    "endpoint",
    [
        LIVENESS_PATH,
        READINESS_PATH,
    ],
)
def test_should_not_return_503_when_kill_switch_is_disabled(client, endpoint):
    assert given_a_get_request(client, endpoint).is_success


@pytest.mark.parametrize(
    "endpoint",
    [
        LIVENESS_PATH,
        READINESS_PATH,
    ],
)
def test_should_return_503_when_kill_switch_is_enabled(client, with_kill_switch_enabled, endpoint):
    response = given_a_get_request(client, endpoint)
    assert response.is_server_error
    assert (
        "Kill-Switch is enabled. " "Please contact the service owner for more information"
    ) in response.json()["detail"]


@pytest.mark.parametrize(
    "endpoint",
    [
        "/docs",
        "/redoc",
        "/openapi.json",
    ],
)
def test_should_still_allow_user_to_access_docs_when_kill_switch_is_enabled(client, with_kill_switch_enabled, endpoint):
    assert given_a_get_request(client, endpoint).is_success
