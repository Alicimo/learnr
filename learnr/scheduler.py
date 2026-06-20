from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from learnr.models import CardState
from learnr.settings import SchedulerSettings, get_scheduler_settings


@dataclass(frozen=True)
class ScheduledState:
    due_at: datetime
    interval_days: float
    ease_factor: float
    review_count: int
    lapse_count: int
    stability: float | None
    difficulty: float | None


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def schedule_binary(
    state: CardState,
    correct: bool,
    answered_at: datetime,
    settings: SchedulerSettings | None = None,
) -> ScheduledState:
    settings = settings or get_scheduler_settings()
    review_count = state.review_count + 1
    lapse_count = state.lapse_count
    ease_factor = state.ease_factor

    if correct:
        if state.review_count == 0:
            interval_days = settings.first_correct_interval_days
        elif state.interval_days < settings.minimum_correct_interval_days:
            interval_days = settings.minimum_correct_interval_days
        else:
            interval_days = max(
                settings.minimum_correct_interval_days,
                round(state.interval_days * ease_factor, 2),
            )
        ease_factor = min(settings.maximum_ease_factor, ease_factor + settings.correct_ease_bonus)
    else:
        lapse_count += 1
        interval_days = settings.failed_interval_days
        ease_factor = max(settings.minimum_ease_factor, ease_factor - settings.incorrect_ease_penalty)

    if correct:
        due_at = answered_at + timedelta(days=interval_days)
    else:
        due_at = answered_at + timedelta(minutes=settings.again_interval_minutes)

    return ScheduledState(
        due_at=due_at,
        interval_days=interval_days,
        ease_factor=ease_factor,
        review_count=review_count,
        lapse_count=lapse_count,
        stability=state.stability,
        difficulty=state.difficulty,
    )
