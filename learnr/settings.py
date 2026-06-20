from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SchedulerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LEARNR_SCHEDULER_")

    first_correct_interval_days: float = Field(default=1.0, gt=0)
    minimum_correct_interval_days: float = Field(default=1.0, gt=0)
    again_interval_minutes: int = Field(default=10, ge=1)
    correct_ease_bonus: float = Field(default=0.05, ge=0)
    incorrect_ease_penalty: float = Field(default=0.2, ge=0)
    maximum_ease_factor: float = Field(default=3.0, gt=0)
    minimum_ease_factor: float = Field(default=1.3, gt=0)
    failed_interval_days: float = Field(default=0.0, ge=0)


@lru_cache
def get_scheduler_settings() -> SchedulerSettings:
    return SchedulerSettings()
