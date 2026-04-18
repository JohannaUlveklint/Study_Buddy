from app.domain.engines.subtask_engine import generate_subtask


def test_generate_subtask_returns_write_instruction_for_write_titles() -> None:
    assert generate_subtask("Write my essay") == {"title": "Write 3 sentences", "difficulty_level": 1}


def test_generate_subtask_returns_read_instruction_for_read_titles() -> None:
    assert generate_subtask("Read chapter 1") == {"title": "Read 1 page", "difficulty_level": 1}


def test_generate_subtask_returns_math_instruction_for_math_titles() -> None:
    assert generate_subtask("Math homework") == {"title": "Solve 2 problems", "difficulty_level": 1}


def test_generate_subtask_returns_fallback_instruction_for_other_titles() -> None:
    assert generate_subtask("Organize desk") == {"title": "Work for 5 minutes", "difficulty_level": 1}