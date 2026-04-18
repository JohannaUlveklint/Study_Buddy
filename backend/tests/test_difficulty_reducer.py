from app.domain.engines.difficulty_reducer import reduce_instruction


def test_reduce_instruction_returns_same_instruction_without_context() -> None:
    instruction = {"title": "Read 1 page", "difficulty_level": 2}

    assert reduce_instruction(instruction) is instruction


def test_reduce_instruction_resets_difficulty_to_one_after_many_aborts() -> None:
    instruction = {"title": "Read 1 page", "difficulty_level": 4}

    reduced = reduce_instruction(instruction, {"recent_aborts": 3, "recent_completions": 5})

    assert reduced == {"title": "Read 1 page", "difficulty_level": 1}


def test_reduce_instruction_increments_difficulty_after_many_completions() -> None:
    instruction = {"title": "Write 3 sentences", "difficulty_level": 1}

    reduced = reduce_instruction(instruction, {"recent_aborts": 0, "recent_completions": 4})

    assert reduced == {"title": "Write 3 sentences", "difficulty_level": 2}


def test_reduce_instruction_caps_completion_increase_at_five() -> None:
    instruction = {"title": "Solve 2 problems", "difficulty_level": 5}

    reduced = reduce_instruction(instruction, {"recent_aborts": 0, "recent_completions": 7})

    assert reduced == {"title": "Solve 2 problems", "difficulty_level": 5}