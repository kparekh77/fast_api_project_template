# Load some pre-defined environment variables from .env file
# See: https://github.com/theskumar/python-dotenv
import os
from enum import Enum

from dotenv import load_dotenv, dotenv_values, find_dotenv


class Environment(Enum):
    """
    Compulsory environment variables that the application depends on to run successfully
    If any of these variables are not set, the application will raise an assertion error.
    """

    NAME = "ENVIRONMENT"
    LOG_LEVEL = "LOG_LEVEL"
    LOG_JSON_FORMAT = "LOG_JSON_FORMAT"
    APP_NAME = "APP_NAME"
    APP_VERSION = "APP_VERSION"
    APP_SUMMARY = "APP_SUMMARY"
    APP_DESCRIPTION = "APP_DESCRIPTION"
    APP_CONTACT_NAME = "APP_CONTACT_NAME"
    APP_CONTACT_URL = "APP_CONTACT_URL"
    APP_CONTACT_EMAIL = "APP_CONTACT_EMAIL"
    APP_LICENCE_NAME = "APP_LICENCE_NAME"
    APP_LICENCE_URL = "APP_LICENCE_URL"
    APP_WEB_HOST = "APP_WEB_HOST"
    APP_WEB_PORT = "APP_WEB_PORT"
    APP_WEB_CORS_ALLOW_ORIGINS = "APP_WEB_CORS_ALLOW_ORIGINS"
    APP_WEB_CORS_ALLOW_CREDENTIALS = "APP_WEB_CORS_ALLOW_CREDENTIALS"
    APP_WEB_CORS_ALLOW_METHODS = "APP_WEB_CORS_ALLOW_METHODS"
    APP_WEB_CORS_ALLOW_HEADERS = "APP_WEB_CORS_ALLOW_HEADERS"
    GCP_PROJECT_ID = "GCP_PROJECT_ID"
    GCP_SECRET_MANAGER_CACHE_TTL_SECS = "GCP_SECRET_MANAGER_CACHE_TTL_SECS"
    OPENAPI_VERSION = "OPENAPI_VERSION"
    KILL_SWITCH_CONFIG_PATH = "KILL_SWITCH_CONFIG_PATH"
    DB_NAME = "DB_NAME"
    DB_USERNAME = "DB_USERNAME"
    DB_CONNECTION = "DB_CONNECTION"

    def get(self):
        if self.value not in os.environ:
            raise KeyError(f"Missing compulsory environment variable: {self.value}")
        return os.getenv(self.value)

    def set(self, value):
        os.environ[self.value] = value

    @staticmethod
    def as_list():
        return [env.value for env in Environment]


"""
This is a special value that can be used to indicate that the value of an environment
variable MUST be inherited from the environment in which the application is running.

Once deployed, if an environment key value still has this `INHERIT_FROM_ENVIRONMENT` value,
it means that the environment variable was not set in the deployment environment and the
application will raise an assertion error.
"""
INHERIT_FROM_ENVIRONMENT_KEY_VALUE = "INHERIT_FROM_ENVIRONMENT"

"""
This is a special value that can be used to indicate that the value of an environment
is a temporary placeholder value that SHOULD be changed before deployment.

This is useful as a reminder to developers to that we have a missing environment key
value that needs to be set for a successful deployment to said environment.
"""
CHANGE_ME_KEY_VALUE = "CHANGE_ME"


def init(compulsory_variables=None):
    """
    The environment loader function is responsible for loading the environment variables
    from the `.env` file and the `.env.{ENVIRONMENT}` file. It also checks for:

     - Missing compulsory environment variables (e.g. anything explicitly defined in Environment Enum)
     - Environment variables dot env definitions that are still set to the `CHANGE_ME` value despite
       being loaded/used as part of the application runtime environment.
     - Environment variables that are still set to the `INHERIT_FROM_ENVIRONMENT` value after
       loading all environment variables into the application runtime environment.

    Any errors found will be raised as an assertion error.

    Args:
        compulsory_variables: A list of all Environment Variables that the application depends on
        to run successfully. If any of these variables are not set, the application will raise an assertion error.
    """
    if compulsory_variables is None:
        compulsory_variables = Environment.as_list()

    if Environment.NAME.value not in os.environ:
        Environment.NAME.set("local")

    shared_environment_config = find_dotenv("environment/.env")
    deployed_environment_config = find_dotenv(f"environment/.env.{Environment.NAME.get().lower()}")

    load_dotenv(dotenv_path=shared_environment_config, verbose=True, override=False)
    load_dotenv(dotenv_path=deployed_environment_config, verbose=True, override=False)

    # Check for environment variables that are STILL set to the `CHANGE_ME_KEY_VALUE` value
    # WITHOUT interference from the deployment environment.
    memory_loaded_dotenv = {**dotenv_values(shared_environment_config), **dotenv_values(deployed_environment_config)}
    change_me_variables = [var for var in compulsory_variables if memory_loaded_dotenv.get(var) == CHANGE_ME_KEY_VALUE]
    # If there are any change me variables, raise an assertion error
    assert not change_me_variables, (
        f"The following variables were set as '{CHANGE_ME_KEY_VALUE}' "
        f"but no value were found for them in the deployment environment: "
        f"{', '.join(change_me_variables)}"
    )

    # Check for environment variables that are STILL set to the `INHERIT_FROM_ENVIRONMENT_KEY_VALUE` value
    # AFTER loading the environment variables from the deployment environment.
    inherent_variables = [var for var in compulsory_variables if os.getenv(var) == INHERIT_FROM_ENVIRONMENT_KEY_VALUE]
    # If there are any inherent variables, raise an assertion error
    assert not inherent_variables, (
        f"The following variables were set as '{INHERIT_FROM_ENVIRONMENT_KEY_VALUE}' "
        f"but no value were found for them in the deployed environment: "
        f"{', '.join(inherent_variables)}"
    )

    # Check for missing compulsory environment variables
    missing_variables = [var for var in compulsory_variables if var not in os.environ]
    # If there are any missing variables, raise an assertion error
    assert not missing_variables, f"Missing compulsory environment variables: {', '.join(missing_variables)}"
