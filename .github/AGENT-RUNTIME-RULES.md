# AGENT RUNTIME RULES

These rules apply to all custom agents and subagents in this repository.

## 1. Truthfulness
Never claim a file exists unless you have read it or listed it.
Never claim a step is complete unless the required artifact exists and is non-empty.
Never claim a test passed unless you ran it or read its output.
Never convert uncertainty into confidence.

## 2. Scope
Only work on the requested phase.
Do not pull future-phase behaviour into the current phase.
Do not widen scope because it feels efficient.
Do not silently improve unrelated code.

## 3. Architecture
No business logic in frontend.
No direct Supabase usage in frontend.
No shortcuts around domain boundaries.
No route handlers acting as hidden domain engines.
No database logic pretending to be business logic.

## 4. Write Discipline
Only write files that are explicitly allowed by the active plan and intention plan.
Do not widen the write surface without explicit plan support.
Do not rename, move, or delete files unless the active plan explicitly requires it.
Do not edit broad directories when only narrow files are required.

## 5. Failure Discipline
When blocked, fail with precision.
Do not continue on assumptions.
Do not downgrade uncertainty into a warning.
Do not replace missing input with guessed input.
Do not patch around missing artifacts.

## 6. Artifact Discipline
Every meaningful step must leave a durable artifact in `implementation-docs/`.
Artifacts are part of the contract, not optional documentation.
Missing required artifacts mean the step is incomplete.

## 7. Language Discipline
Use precise, operational language.
Avoid vague verbs such as improve, refine, enhance, support, handle, manage unless followed by exact, bounded meaning.
Avoid advisory fluff.
Avoid motivational tone.

## 8. Completion
A step is complete only when:
- required files exist
- required structure is present
- required behaviour is implemented or verified
- required artifact has been written
- the state file has been updated

## 9. Agent Boundaries
Each agent performs its own role only.
Planning agents do not code.
Coding agents do not verify.
Verification agents do not fix.
Testing agents do not rewrite product code.
The orchestrator never implements.

## 10. Repository Hygiene
Do not merge to `main` unless explicitly instructed by the user.
Do not introduce dependencies unless explicitly required by the active phase plan.
Do not leave placeholder TODOs in place of implementation.
