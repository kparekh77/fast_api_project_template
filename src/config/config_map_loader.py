import json

from pydantic import BaseModel, Field

from config.environment_loader import Environment


class KillSwitchConfig(BaseModel):
    enabled: bool = Field(
        ...,
        description="Indicates whether the service is enabled or disabled",
        examples=[True, False],
    )

    @staticmethod
    def load() -> "KillSwitchConfig":
        with open(Environment.KILL_SWITCH_CONFIG_PATH.get(), "r") as f:
            return KillSwitchConfig.model_validate(json.load(f))
