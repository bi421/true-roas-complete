#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.

from pydantic_settings import BaseSettings, SettingsConfigDict


class LearningSettings(BaseSettings):
    """Typed configuration for the Self-Learning System."""

    learning_enabled: bool = False
    learning_min_samples: int = 20

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


learning_settings = LearningSettings()
