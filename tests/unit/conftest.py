import pytest

from config import environment_loader
from config.environment_loader import Environment
from tests.helpers import resource_path_for


@pytest.fixture(autouse=True, scope="module")
def mock_environment():
    environment_loader.init()
    Environment.KILL_SWITCH_CONFIG_PATH.set(resource_path_for("kill_switch_config_disabled.json"))
