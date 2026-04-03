def generate_subtask(title: str) -> dict[str, int | str]:
    lowered_title = title.lower()

    if "write" in lowered_title:
        return {"title": "Write 3 sentences", "difficulty_level": 1}
    if "read" in lowered_title:
        return {"title": "Read 1 page", "difficulty_level": 1}
    if "math" in lowered_title:
        return {"title": "Solve 2 problems", "difficulty_level": 1}

    return {"title": "Work for 5 minutes", "difficulty_level": 1}