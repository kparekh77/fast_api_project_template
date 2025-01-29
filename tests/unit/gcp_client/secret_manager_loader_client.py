import time
from unittest.mock import MagicMock

import pytest

from clients.gcp_client.secret_manager_client import SecretManager
from config.environment_loader import Environment


@pytest.fixture
def secret_manager():
    SecretManager._instance = None
    SecretManager._secret_cache = {}
    return SecretManager()


# secret manager tests
def test_get_secret_from_cache(secret_manager):
    secret_name = "test-secret"
    secret_value = "cached-value"
    current_time = time.time()

    # Add secret to cache
    secret_manager._secret_cache[secret_name] = (secret_value, current_time)

    # Fetch the secret
    fetched_secret = secret_manager.get_secret(secret_name)

    assert fetched_secret == secret_value


def test_get_secret_expired_cache(secret_manager, mocker):
    secret_name = "test-secret"
    expired_value = "expired-value"
    new_value = "new-value"
    past_time = time.time() - (int(Environment.GCP_SECRET_MANAGER_CACHE_TTL_SECS.get()) + 10)

    # Add expired secret to cache
    secret_manager._secret_cache[secret_name] = (expired_value, past_time)

    # Mock the SecretManagerServiceClient

    mock_secret_manager_client = mocker.patch(
        "clients.gcp_client.secret_manager_client.secretmanager.SecretManagerServiceClient"
    )
    mock_secret_manager_instance = mock_secret_manager_client.return_value
    mock_access_secret_version = mock_secret_manager_instance.access_secret_version
    mock_secret_payload = MagicMock()
    mock_secret_payload.payload.data.decode.return_value = new_value
    mock_access_secret_version.return_value = mock_secret_payload

    # Fetch the secret
    fetched_secret = secret_manager.get_secret(secret_name)

    assert fetched_secret == new_value
    assert secret_manager._secret_cache[secret_name][0] == new_value


def test_get_secret_new_fetch(secret_manager, mocker):
    secret_name = "test-secret"
    secret_value = "new-value"

    # Mock the SecretManagerServiceClient
    mock_secret_manager_client = mocker.patch(
        "clients.gcp_client.secret_manager_client.secretmanager.SecretManagerServiceClient"
    )
    mock_secret_manager_instance = mock_secret_manager_client.return_value
    mock_access_secret_version = mock_secret_manager_instance.access_secret_version
    mock_secret_payload = MagicMock()
    mock_secret_payload.payload.data.decode.return_value = secret_value
    mock_access_secret_version.return_value = mock_secret_payload

    # Fetch the secret
    fetched_secret = secret_manager.get_secret(secret_name)

    assert fetched_secret == secret_value
    assert secret_manager._secret_cache[secret_name][0] == secret_value


def test_singleton_behavior(secret_manager):
    another_instance = SecretManager()

    assert secret_manager is another_instance
    assert id(secret_manager) == id(another_instance)
