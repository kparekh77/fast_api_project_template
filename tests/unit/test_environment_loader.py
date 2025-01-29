import os

import pytest
from _pytest.outcomes import fail
from dotenv import find_dotenv

from config import environment_loader

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))


@pytest.fixture
def mocked_load_dotenv(mocker):
    mocked_load_dotenv = mocker.Mock()
    mocker.patch.object(environment_loader, "load_dotenv", mocked_load_dotenv)
    return mocked_load_dotenv


@pytest.fixture
def env_vars_manager():
    env_vars = {}

    def _set_env_vars(vars_dict):
        env_vars.update(vars_dict)
        for key, value in vars_dict.items():
            os.environ[key] = value

    yield _set_env_vars

    # Cleanup code after test execution
    for var in env_vars.keys():
        del os.environ[var]


def test_init_all_variables_set(mocked_load_dotenv, env_vars_manager):
    compulsory_variables = ["VAR1", "VAR2", "VAR3"]
    env_vars_manager({var: "test_value" for var in compulsory_variables})

    environment_loader.init(compulsory_variables)


def test_init_missing_variables(mocked_load_dotenv, env_vars_manager):
    compulsory_variables = ["VAR1", "VAR2", "VAR3"]
    env_vars_manager({"VAR1": "test_value"})

    try:
        environment_loader.init(compulsory_variables)
    except AssertionError as e:
        assert str(e) == "Missing compulsory environment variables: VAR2, VAR3"


def test_init_empty_compulsory_variables(mocked_load_dotenv, env_vars_manager):
    compulsory_variables = []
    try:
        environment_loader.init(compulsory_variables)
    except AssertionError:
        fail("init() raised AssertionError unexpectedly!")


def test_init_variable_set_to_empty_string(mocked_load_dotenv, env_vars_manager):
    compulsory_variables = ["VAR1", "VAR2"]
    env_vars_manager({"VAR1": "test_value", "VAR2": ""})

    try:
        environment_loader.init(compulsory_variables)
    except AssertionError as e:
        assert str(e) == "Missing compulsory environment variables: VAR2"


def test_load_dotenv_files_with_default_environment(mocked_load_dotenv):
    environment_loader.init([])

    mocked_load_dotenv.assert_any_call(
        dotenv_path=find_dotenv(os.path.join(ROOT_DIR, "environment/.env")), verbose=True, override=False
    )
    mocked_load_dotenv.assert_any_call(
        dotenv_path=find_dotenv(os.path.join(ROOT_DIR, "environment/.env.local")), verbose=True, override=False
    )


def test_load_dotenv_files_with_custom_environment(mocked_load_dotenv, env_vars_manager):
    env_vars_manager({"ENVIRONMENT": "prod"})

    environment_loader.init([])

    mocked_load_dotenv.assert_any_call(
        dotenv_path=find_dotenv(os.path.join(ROOT_DIR, "environment/.env")), verbose=True, override=False
    )
    mocked_load_dotenv.assert_any_call(
        dotenv_path=find_dotenv(os.path.join(ROOT_DIR, "environment/.env.prod")), verbose=True, override=False
    )


def test_init_change_me_key_value(mocked_load_dotenv, env_vars_manager):
    compulsory_variables = ["VAR1", "VAR2"]
    env_vars_manager({"VAR1": "test_value", "VAR2": environment_loader.CHANGE_ME_KEY_VALUE})

    try:
        environment_loader.init(compulsory_variables)
    except AssertionError as e:
        assert str(e) == (
            "The following variables were set as 'CHANGE_ME' "
            "but no value were found for them in the deployment environment: VAR2"
        )


def test_init_inherent_from_environment_key_value(mocked_load_dotenv, env_vars_manager):
    compulsory_variables = ["VAR1", "VAR2"]
    env_vars_manager({"VAR1": "test_value", "VAR2": environment_loader.INHERIT_FROM_ENVIRONMENT_KEY_VALUE})

    try:
        environment_loader.init(compulsory_variables)
    except AssertionError as e:
        assert str(e) == (
            "The following variables were set as 'INHERIT_FROM_ENVIRONMENT' "
            "but no value were found for them in the deployed environment: VAR2"
        )
