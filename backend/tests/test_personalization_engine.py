from datetime import datetime, timedelta, timezone

from app.domain.engines.personalization_engine import (
    calculate_planned_duration_minutes,
    select_next_task,
)


def _utc_datetime(days_ago: int = 0, hours_ago: int = 0, minutes_ago: int = 0) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)


def test_calculate_planned_duration_minutes_defaults_to_ten_for_fewer_than_two_sessions() -> None:
    assert calculate_planned_duration_minutes([]) == 10
    assert calculate_planned_duration_minutes([
        {"actual_duration_minutes": 17, "ended_at": _utc_datetime(minutes_ago=30)}
    ]) == 10


def test_calculate_planned_duration_minutes_uses_half_up_rounding() -> None:
    recent_sessions = [
        {"actual_duration_minutes": 11, "ended_at": _utc_datetime(minutes_ago=20)},
        {"actual_duration_minutes": 12, "ended_at": _utc_datetime(minutes_ago=10)},
    ]

    assert calculate_planned_duration_minutes(recent_sessions) == 12


def test_calculate_planned_duration_minutes_clamps_low_and_high_bounds() -> None:
    low_history = [
        {"actual_duration_minutes": 1, "ended_at": _utc_datetime(days_ago=1)},
        {"actual_duration_minutes": 2, "ended_at": _utc_datetime(days_ago=2)},
    ]
    high_history = [
        {"actual_duration_minutes": 31, "ended_at": _utc_datetime(days_ago=1)},
        {"actual_duration_minutes": 35, "ended_at": _utc_datetime(days_ago=2)},
        {"actual_duration_minutes": 40, "ended_at": _utc_datetime(days_ago=3)},
    ]

    assert calculate_planned_duration_minutes(low_history) == 5
    assert calculate_planned_duration_minutes(high_history) == 30


def test_select_next_task_returns_none_for_empty_candidates() -> None:
    assert select_next_task([]) is None


def test_select_next_task_prioritizes_latest_aborted_group_before_others() -> None:
    candidates = [
        {
            "id": "group-1",
            "title": "History task",
            "subject_id": None,
            "created_at": _utc_datetime(days_ago=5),
            "is_completed": False,
            "latest_ended_at": _utc_datetime(days_ago=3),
            "latest_ended_was_aborted": False,
            "latest_started_at": _utc_datetime(days_ago=3),
            "ended_abort_count": 0,
            "has_session_history": True,
        },
        {
            "id": "group-0",
            "title": "Recently aborted task",
            "subject_id": None,
            "created_at": _utc_datetime(days_ago=2),
            "is_completed": False,
            "latest_ended_at": _utc_datetime(minutes_ago=5),
            "latest_ended_was_aborted": True,
            "latest_started_at": _utc_datetime(minutes_ago=15),
            "ended_abort_count": 1,
            "has_session_history": True,
        },
        {
            "id": "group-2",
            "title": "Never started task",
            "subject_id": None,
            "created_at": _utc_datetime(days_ago=10),
            "is_completed": False,
            "latest_ended_at": None,
            "latest_ended_was_aborted": None,
            "latest_started_at": None,
            "ended_abort_count": 0,
            "has_session_history": False,
        },
    ]

    selected = select_next_task(candidates)

    assert selected is not None
    assert selected["id"] == "group-0"


def test_select_next_task_breaks_group_zero_ties_by_abort_count_after_latest_end() -> None:
    same_end_time = _utc_datetime(minutes_ago=10)
    candidates = [
        {
            "id": "lower-aborts",
            "title": "Lower abort count",
            "subject_id": None,
            "created_at": _utc_datetime(days_ago=4),
            "is_completed": False,
            "latest_ended_at": same_end_time,
            "latest_ended_was_aborted": True,
            "latest_started_at": _utc_datetime(minutes_ago=30),
            "ended_abort_count": 1,
            "has_session_history": True,
        },
        {
            "id": "higher-aborts",
            "title": "Higher abort count",
            "subject_id": None,
            "created_at": _utc_datetime(days_ago=3),
            "is_completed": False,
            "latest_ended_at": same_end_time,
            "latest_ended_was_aborted": True,
            "latest_started_at": _utc_datetime(minutes_ago=25),
            "ended_abort_count": 4,
            "has_session_history": True,
        },
    ]

    assert select_next_task(candidates)["id"] == "higher-aborts"


def test_select_next_task_uses_latest_started_for_group_one_ordering() -> None:
    candidates = [
        {
            "id": "older-start",
            "title": "Older start",
            "subject_id": None,
            "created_at": _utc_datetime(days_ago=4),
            "is_completed": False,
            "latest_ended_at": _utc_datetime(days_ago=1),
            "latest_ended_was_aborted": False,
            "latest_started_at": _utc_datetime(hours_ago=4),
            "ended_abort_count": 0,
            "has_session_history": True,
        },
        {
            "id": "newer-start",
            "title": "Newer start",
            "subject_id": None,
            "created_at": _utc_datetime(days_ago=2),
            "is_completed": False,
            "latest_ended_at": _utc_datetime(days_ago=2),
            "latest_ended_was_aborted": False,
            "latest_started_at": _utc_datetime(hours_ago=1),
            "ended_abort_count": 0,
            "has_session_history": True,
        },
    ]

    assert select_next_task(candidates)["id"] == "newer-start"


def test_select_next_task_prefers_oldest_created_task_when_no_history_exists() -> None:
    candidates = [
        {
            "id": "newer-task",
            "title": "Newer",
            "subject_id": None,
            "created_at": _utc_datetime(days_ago=1),
            "is_completed": False,
            "latest_ended_at": None,
            "latest_ended_was_aborted": None,
            "latest_started_at": None,
            "ended_abort_count": 0,
            "has_session_history": False,
        },
        {
            "id": "older-task",
            "title": "Older",
            "subject_id": None,
            "created_at": _utc_datetime(days_ago=10),
            "is_completed": False,
            "latest_ended_at": None,
            "latest_ended_was_aborted": None,
            "latest_started_at": None,
            "ended_abort_count": 0,
            "has_session_history": False,
        },
    ]

    assert select_next_task(candidates)["id"] == "older-task"