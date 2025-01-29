import time

from google.cloud import secretmanager

from config.environment_loader import Environment


class SecretManager:
    _instance = None
    _secret_cache = {}

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(SecretManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    @staticmethod
    def get_secret(secret_name: str) -> str:
        current_time = time.time()

        # Check if the secret is in the cache and if it is still valid
        if secret_name in SecretManager._secret_cache:
            secret_value, cache_timestamp = SecretManager._secret_cache[secret_name]
            if current_time - cache_timestamp < int(Environment.GCP_SECRET_MANAGER_CACHE_TTL_SECS.get()):
                return secret_value

        # If not in cache or cache is expired, fetch the secret and update the cache
        client = secretmanager.SecretManagerServiceClient()
        secret_value = client.access_secret_version(name=secret_name).payload.data.decode("UTF-8")
        SecretManager._secret_cache[secret_name] = (secret_value, current_time)

        return secret_value
