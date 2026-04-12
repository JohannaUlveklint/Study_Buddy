def reduce_instruction(instruction: dict, context: dict | None = None) -> dict:
    if context is None:
        return instruction

    result = dict(instruction)
    recent_aborts = context.get("recent_aborts", 0)
    recent_completions = context.get("recent_completions", 0)

    if recent_aborts > 2:
        result["difficulty_level"] = 1
    elif recent_completions > 3:
        result["difficulty_level"] = min(result.get("difficulty_level", 1) + 1, 5)

    return result