# Phase
Phase 5

# Summary
Phase 5 adds backend-only personalisation to the existing start flow by introducing a dedicated personalisation engine, moving next-task ranking out of repository-only ordering and into a bounded backend engine/service contract, computing session planned duration from recent ended sessions for the same task, and persisting actual session duration when sessions are completed or aborted. The route surface, schema surface, frontend files, and database schema remain unchanged.

# Repository Reality Check
- Existing backend surface: `backend/app/domain/services/task_service.py` already owns start-task orchestration, including task lookup, completed-task rejection, open-session rejection, recent attempt lookup, subtask generation, difficulty reduction, and transactional creation of the subtask plus session. It currently hardcodes `planned_duration_minutes=10` and currently delegates `get_next_task` directly to `TaskRepository.get_next_task()`. `backend/app/domain/services/session_manager.py` already owns session completion and abort orchestration, including ended-session validation, attempt creation, and task completion on successful completion. `backend/app/infrastructure/repositories/session_repository.py` already serializes `planned_duration_minutes` and `actual_duration_minutes`, already creates sessions with a supplied planned duration, and already ends sessions, but its end-session update does not write `actual_duration_minutes` and it exposes no history query for recent task durations. `backend/app/infrastructure/repositories/task_repository.py` already creates, lists, and fetches tasks and currently implements `/next` selection in SQL with a simpler latest-abort-first ordering that does not expose the full candidate summary required by Phase 5. `backend/app/api/routes/tasks.py` and `backend/app/api/schemas/tasks.py` already expose the unchanged `/tasks`, `/tasks/{task_id}/start`, and `/next` contracts needed for this phase.
- Existing frontend surface: `frontend/app/page.tsx` already loads `getNextTask()` on page load and after session resolution, and already stores the `session` and `instruction` returned by `startTask()`. `frontend/services/api.ts` already exposes `getNextTask`, `startTask`, `completeSession`, and `abortSession` with the required unchanged request/response shapes. `frontend/types/study-buddy.ts` already includes `planned_duration_minutes` and `actual_duration_minutes` on the `Session` type. `frontend/components/session-view.tsx` already renders `session.planned_duration_minutes` from the backend response. Phase 5 does not require any frontend code change.
- Existing tests: No automated product test surface exists in the repository tree. There is no `backend/tests`, `frontend/tests`, `frontend/__tests__`, or equivalent application test directory currently present. Only implementation-doc artifacts exist under `implementation-docs/`.
- Missing required surfaces: `backend/app/domain/engines/personalization_engine.py` does not exist yet. `backend/app/infrastructure/repositories/session_repository.py` is missing a query for the last five ended sessions with non-null `actual_duration_minutes` for one task. `backend/app/infrastructure/repositories/task_repository.py` is missing a repository method that returns every incomplete task together with the Phase 5 candidate summary fields. `backend/app/domain/services/task_service.py` is missing the service-level duration calculation call and service-level task ranking call. `backend/app/domain/services/session_manager.py` is missing persistence of `actual_duration_minutes` through the existing end-session transaction.

# Files to Create
## backend/app/domain/engines/personalization_engine.py
- Why it must exist: Phase 5 requires one backend-only location for the new duration-adjustment rules and task-priority ordering rules, and no existing engine file owns that behaviour.
- Responsibility: Own exactly two behaviours: computing the planned session duration from recent ended-session history and selecting the highest-ranked task from a list of incomplete-task candidates using the deterministic Phase 5 ordering rules.
- Forbidden contents: No database access, no FastAPI route concerns, no schema objects, no subject logic, no subtask-generation logic, no difficulty-reduction logic, no frontend logic, and no persistence writes.

# Files to Modify
## backend/app/domain/services/task_service.py
- Why it must change: The current `get_next_task()` method calls `self._task_repository.get_next_task()` and returns that result directly, which keeps priority selection inside repository SQL. The current `start_task()` method always passes `planned_duration_minutes=10` into `create_session_in_connection(...)`, so it does not apply Phase 5 personalisation.
- Exact scope of change: Add the new personalisation-engine import and use it in two places only. In `get_next_task()`, replace the current direct repository selection path with a repository call that returns all incomplete-task candidates plus their session-summary fields, then select one task through the engine and return only the unchanged task payload. In `start_task()`, keep the existing sequence of task lookup, completed-task validation, open-session validation, recent-attempt lookup, `generate_subtask(...)`, `reduce_instruction(...)`, and transactional subtask/session creation, but insert one read of recent ended-session duration history for the same task, call the personalisation engine to compute the planned duration, and pass that computed value into `create_session_in_connection(...)` instead of the hardcoded `10`.
- Must remain untouched: `create_task()` and `list_tasks()` stay as repository pass-throughs. The existing error classes stay unchanged. The Phase 3 difficulty-reduction flow and the current `recent_completions` / `recent_aborts` counting stay unchanged. The response shape from `start_task()` remains `{"session": session, "instruction": instruction}`. No HTTP exceptions, schema shaping, or SQL should move into this file.

## backend/app/domain/services/session_manager.py
- Why it must change: The current `complete_session()` and `abort_session()` methods already orchestrate end-session writes and attempt writes, but they rely on `end_session_tx(...)` to update only `ended_at`, `was_completed`, and `was_aborted`, so `actual_duration_minutes` is never persisted.
- Exact scope of change: Limit edits to `complete_session()` and `abort_session()` so they continue to perform the existing `get_session(...)` existence check, already-ended check, transaction wrapper, attempt creation, and task-completion write on completion, while relying on the updated repository transaction to return a session record that now includes a stored `actual_duration_minutes` value. Keep the existing sequence in which attempt rows are still written after the session end update within the same transaction. Do not add new service methods.
- Must remain untouched: `create_session()` must remain untouched in this phase. The existing error classes remain unchanged. Completion must still mark the task completed when `task_id` is present. Abort must still avoid task completion. No personalisation formula should be implemented in this service.

## backend/app/infrastructure/repositories/task_repository.py
- Why it must change: The current `get_next_task()` query embeds a partial ranking directly in SQL by looking only at the latest ended session and then returning a single task. That current implementation cannot express the full Phase 5 candidate summary contract or leave final ranking ownership in the backend domain layer.
- Exact scope of change: Replace or retire the current single-task `get_next_task()` read path with a repository method that returns every incomplete task together with these exact per-task summary fields derived from session history: latest ended session timestamp, latest ended session aborted flag, latest session started timestamp, count of ended aborted sessions, and a boolean indicating whether any session history exists. Preserve the existing base task fields `id`, `title`, `subject_id`, `created_at`, and `is_completed` in each returned candidate row so the service can return an unchanged `TaskResponse` shape after engine selection.
- Must remain untouched: `create_task()`, `list_tasks()`, `get_task()`, and `_serialize_task(...)` must continue to return the existing task shape. This repository must not own the final Phase 5 ordering logic once the candidate summary data has been fetched. It must not add writes, schema changes, or unrelated task filtering.

## backend/app/infrastructure/repositories/session_repository.py
- Why it must change: The file already stores sessions and serializes `actual_duration_minutes`, but it has no method to fetch recent ended-session duration history for one task, and `end_session_tx(...)` does not currently write `actual_duration_minutes` when ending a session.
- Exact scope of change: Add one read method that returns up to the last five sessions for a given task where `ended_at IS NOT NULL` and `actual_duration_minutes IS NOT NULL`, ordered by `ended_at DESC`, so `TaskService.start_task()` can compute the personalised planned duration. Update `end_session_tx(...)` so the same `UPDATE sessions ... RETURNING ...` statement that writes `ended_at`, `was_completed`, and `was_aborted` also writes `actual_duration_minutes` as the whole-minute duration between the database end timestamp and `started_at`, using the Phase 5 whole-minute rule. Keep returning the same serialized session shape.
- Must remain untouched: `_serialize_session(...)`, `_insert_session_record(...)`, `create_session(...)`, `create_session_in_connection(...)`, `get_open_session_for_task(...)`, `get_session(...)`, and `mark_task_completed_tx(...)` must keep their current responsibilities and response fields. This file must not implement task-priority ordering or difficulty logic.

# Files Forbidden to Modify
- backend/app/main.py
- backend/app/api/routes/**
- backend/app/api/schemas/**
- backend/app/domain/engines/difficulty_reducer.py
- backend/app/domain/engines/subtask_engine.py
- backend/app/domain/services/subject_service.py
- backend/app/infrastructure/repositories/attempt_repository.py
- backend/app/infrastructure/repositories/subject_repository.py
- backend/app/infrastructure/repositories/subtask_repository.py
- frontend/**
- implementation-docs/devplan.md
- implementation-docs/current-phase.md
- Any file outside the explicit create and modify list in this intention plan

# Required Contracts Between Files
- `backend/app/domain/services/task_service.py` owns orchestration. It remains the only Phase 5 file that combines task state validation, attempt-history reads, duration-history reads, subtask generation, difficulty reduction, personalisation-engine calls, and session creation into the existing `start_task()` response.
- `backend/app/domain/engines/personalization_engine.py` owns only pure decision logic. It consumes recent ended-session duration rows from `backend/app/infrastructure/repositories/session_repository.py` and candidate task rows from `backend/app/infrastructure/repositories/task_repository.py`, then returns a planned duration value or the selected highest-ranked task. It does not fetch data itself.
- `backend/app/infrastructure/repositories/session_repository.py` owns persistence for session history reads and end-session writes. `backend/app/domain/services/task_service.py` uses it to fetch recent duration rows before starting a task. `backend/app/domain/services/session_manager.py` uses it to end a session and persist `actual_duration_minutes` in the same database update that sets `ended_at`, `was_completed`, and `was_aborted`.
- `backend/app/infrastructure/repositories/task_repository.py` owns read access to incomplete-task candidates and their per-task session summary fields, but it must not own the final ranking rule. `backend/app/domain/services/task_service.py` receives those candidate rows and delegates the final selection to `backend/app/domain/engines/personalization_engine.py`.
- `backend/app/infrastructure/repositories/attempt_repository.py` remains unchanged and continues to supply recent attempts for difficulty reduction in `backend/app/domain/services/task_service.py` and to write completion/abort attempts in `backend/app/domain/services/session_manager.py` after the session-end update.
- `backend/app/api/routes/tasks.py` and `backend/app/api/schemas/tasks.py` remain unchanged consumers of the service output. The selected next task must still fit the current `TaskResponse` shape, and the started session must still fit the current `TaskStartResponse` shape.
- `frontend/services/api.ts`, `frontend/app/page.tsx`, `frontend/types/study-buddy.ts`, and `frontend/components/session-view.tsx` remain unchanged downstream consumers. They continue to receive personalised `planned_duration_minutes` and the prioritised next task through the existing backend contracts only.

# Migration / Schema Impact
- None. Phase 5 uses the existing `sessions.planned_duration_minutes` and `sessions.actual_duration_minutes` columns.
- No schema migration, no seed change, no new table, no new column, no index addition, and no schema-model change is allowed.
- No frontend type-file change is allowed because the current shared frontend types already expose the session duration fields consumed by the UI.

# Test Surface Impact
- No existing automated test files can be modified because no product test directory currently exists in the repository.
- Later verification must cover the default planned-duration path where fewer than two qualifying ended sessions exist for a task and the start response still returns `planned_duration_minutes = 10`.
- Later verification must cover the personalised planned-duration path where at least two qualifying ended sessions exist, the mean is computed from at most the last five qualifying rows, half-up rounding is applied, and the result is clamped to the Phase 5 minimum and maximum bounds.
- Later verification must cover both `complete_session` and `abort_session` writing a non-null integer `actual_duration_minutes` greater than or equal to 1 while preserving the existing attempt-write behaviour and task-completion-on-complete behaviour.
- Later verification must cover `/next` selection across all three rank groups and their exact tie-break order using incomplete tasks only.
- Later verification must confirm that `frontend/app/page.tsx`, `frontend/services/api.ts`, `frontend/types/study-buddy.ts`, and `frontend/components/session-view.tsx` remain unchanged for Phase 5.

# Risk Points
- The main drift risk is leaving task-priority logic inside `backend/app/infrastructure/repositories/task_repository.py`. Phase 5 requires the repository to expose candidate data and the new engine/service layer to own final ranking.
- Another drift risk is broadening edits into `backend/app/api/routes/**`, `backend/app/api/schemas/**`, or any frontend file even though the approved plan and the current frontend surface already support the unchanged contracts.
- A concrete persistence risk is updating `ended_at` without computing `actual_duration_minutes` from the same database end timestamp, which would break the Phase 5 end-session contract.
- A concrete history-sampling risk is using open sessions, rows with null `actual_duration_minutes`, or more than five rows when computing the personalised planned duration.
- A concrete ordering risk is implementing the wrong tie-break direction for never-started tasks or started tasks, or failing to distinguish `latest ended aborted` from other session-history cases exactly as defined in the approved plan.
- A scope risk is editing `backend/app/domain/engines/difficulty_reducer.py`, `backend/app/domain/engines/subtask_engine.py`, or `backend/app/infrastructure/repositories/attempt_repository.py` even though Phase 5 explicitly leaves those behaviours unchanged.