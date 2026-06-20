from datetime import datetime, timezone

from learnr.models import CardState
from learnr.scheduler import schedule_binary


def test_correct_new_card_moves_due_to_tomorrow():
    state = CardState(interval_days=0, ease_factor=2.5, review_count=0, lapse_count=0)
    answered_at = datetime(2026, 6, 13, 10, 0, tzinfo=timezone.utc)

    scheduled = schedule_binary(state, True, answered_at)

    assert scheduled.interval_days == 1.0
    assert scheduled.review_count == 1
    assert scheduled.lapse_count == 0
    assert scheduled.due_at > answered_at


def test_wrong_card_is_due_again_soon_and_counts_lapse():
    state = CardState(interval_days=5, ease_factor=2.5, review_count=3, lapse_count=1)
    answered_at = datetime(2026, 6, 13, 10, 0, tzinfo=timezone.utc)

    scheduled = schedule_binary(state, False, answered_at)

    assert scheduled.interval_days == 0.0
    assert scheduled.review_count == 4
    assert scheduled.lapse_count == 2
    assert scheduled.ease_factor == 2.3
