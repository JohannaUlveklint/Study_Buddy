from math import floor


def calculate_planned_duration_minutes(recent_sessions: list[dict]) -> int:
    if len(recent_sessions) < 2:
        return 10

    average_duration = sum(session["actual_duration_minutes"] for session in recent_sessions) / len(recent_sessions)
    rounded_duration = floor(average_duration + 0.5)

    return max(5, min(30, rounded_duration))


def select_next_task(task_candidates: list[dict]) -> dict | None:
    if not task_candidates:
        return None

    rank_group_zero = [
        candidate
        for candidate in task_candidates
        if candidate["latest_ended_at"] is not None and candidate["latest_ended_was_aborted"] is True
    ]
    rank_group_one = [
        candidate
        for candidate in task_candidates
        if candidate["has_session_history"] and candidate not in rank_group_zero
    ]
    rank_group_two = [candidate for candidate in task_candidates if not candidate["has_session_history"]]

    rank_group_zero.sort(
        key=lambda candidate: (
            _descending_datetime_value(candidate["latest_ended_at"]),
            -candidate["ended_abort_count"],
            candidate["created_at"],
        )
    )
    rank_group_one.sort(
        key=lambda candidate: (
            _descending_datetime_value(candidate["latest_started_at"]),
            candidate["created_at"],
        )
    )
    rank_group_two.sort(key=lambda candidate: candidate["created_at"])

    return (rank_group_zero + rank_group_one + rank_group_two)[0]


def _descending_datetime_value(value) -> float:
    if value is None:
        return float("inf")

    return -value.timestamp()