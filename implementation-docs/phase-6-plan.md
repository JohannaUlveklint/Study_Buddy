## Phase
Phase 6: Stabilisation

## Phase Goal
Phase 6 stabilises the existing Study Buddy flow by making backend failure handling explicit and consistent, closing the current session-resolution and task-start race windows, expanding automated backend regression coverage across the uncovered engine, service, repository, and route layers, and replacing per-call PostgreSQL connections with pooled reuse, while leaving the existing route surface, database schema, frontend UI flow, and personalization behaviour unchanged.

## Scope
### Included
- Consistent backend HTTP error mapping for the existing `/tasks`, `/subjects`, `/next`, and `/sessions` routes.
- Explicit backend handling for database-unavailable failures and required-write failures during task start and session resolution.
- Transactional hardening of `POST /tasks/{task_id}/start` so task lookup, open-session rejection, recent-history reads, subtask persistence, and session persistence execute on one borrowed database connection.
- Transactional hardening of `POST /sessions/{session_id}/complete` and `POST /sessions/{session_id}/abort` so a session cannot be ended twice through a stale pre-check and an attempt row cannot fail silently.
- Application-scoped asyncpg connection pooling and pooled connection acquisition for repository access.
- New backend pytest coverage for route error mapping, service orchestration, difficulty reduction, subtask generation, and the tightened session repository contract.
- Retention of the existing frontend error banner without any UI or state-flow change.

### Excluded
- New routes, route renames, route removals, or route response-shape changes.
- New tables, new columns, new indexes, schema migrations, or seed changes.
- Changes to subject behavior, subtask generation rules, difficulty reduction thresholds, personalization formulas, next-task ranking rules, or task-completion semantics beyond rollback safety.
- Frontend component changes, frontend state changes, frontend API-client changes, frontend dependencies, and frontend test-runner setup.
- Caching layers, background jobs, retry queues, websocket updates, or any new infrastructure component.
- AI assist, prompt files, model calls, embeddings, generated wording, or any other AI surface.

## Preconditions
- Phase 5 code is present exactly as read in the repository, including `GET /next`, personalized `planned_duration_minutes`, and persisted `actual_duration_minutes`.
- The existing PostgreSQL schema from `implementation-docs/devplan.md` exists unchanged.
- `frontend/app/page.tsx` already renders backend error text through the existing page-level status banner, so no frontend error-display work is required in phase 6.
- The backend test surface currently consists of `backend/tests/test_personalization_engine.py` and `backend/tests/test_session_repository.py`, which cover only part of the engine and repository behavior.
- No phase 6 implementation step is allowed to introduce schema changes, new dependencies, or frontend feature work.

## Backend Design
### Routes
### Create Task
- Method: POST
- Path: /tasks
- Request Shape: Unchanged JSON body with `title` as a required string and `subject_id` as an optional UUID.
- Response Shape: Unchanged task object with `id`, `title`, `subject_id`, `created_at`, and `is_completed`.
- Error Conditions: `400` when `title` is blank after trimming; `400` when `subject_id` fails the existing foreign-key insert path; `422` when request validation fails before route logic; `503` when the database pool is unavailable or connection acquisition fails; `500` for unexpected internal failures. All handled errors return the existing FastAPI `detail` string shape.

### List Tasks
- Method: GET
- Path: /tasks
- Request Shape: No request body.
- Response Shape: Unchanged JSON array of task objects with `id`, `title`, `subject_id`, `created_at`, and `is_completed`.
- Error Conditions: `503` when the database pool is unavailable or connection acquisition fails; `500` for unexpected internal failures. All handled errors return the existing FastAPI `detail` string shape.

### Start Task
- Method: POST
- Path: /tasks/{task_id}/start
- Request Shape: Unchanged route parameter `task_id` as a UUID string and no request body.
- Response Shape: Unchanged `TaskStartResponse` object with `session` and `instruction`.
- Error Conditions: `404` when the task does not exist; `409` when the task is already completed; `409` when the task already has an open session; `503` when the database pool is unavailable or connection acquisition fails; `500` when subtask creation, session creation, or required-history reads fail unexpectedly. A missing subtask row or session row after the write step is treated as `500`, not as a silent success.

### List Subjects
- Method: GET
- Path: /subjects
- Request Shape: No request body.
- Response Shape: Unchanged JSON array of subject objects with `id`, `name`, `color`, and `icon`.
- Error Conditions: `503` when the database pool is unavailable or connection acquisition fails; `500` for unexpected internal failures. All handled errors return the existing FastAPI `detail` string shape.

### Get Next Task
- Method: GET
- Path: /next
- Request Shape: No request body.
- Response Shape: Unchanged task object with `id`, `title`, `subject_id`, `created_at`, and `is_completed`.
- Error Conditions: `404` when no incomplete task exists; `503` when the database pool is unavailable or connection acquisition fails; `500` for unexpected internal failures. The route keeps returning the existing `detail` string shape so the current frontend `getNextTask()` behavior remains valid.

### Complete Session
- Method: POST
- Path: /sessions/{session_id}/complete
- Request Shape: Unchanged route parameter `session_id` as a UUID string and no request body.
- Response Shape: Unchanged session object with `id`, `task_id`, `subtask_id`, `started_at`, `ended_at`, `planned_duration_minutes`, `actual_duration_minutes`, `was_completed`, and `was_aborted`.
- Error Conditions: `404` when the session does not exist; `409` when the session is already ended; `503` when the database pool is unavailable or connection acquisition fails; `500` when the session update or required attempt insert fails unexpectedly. An attempt insert that returns no row is treated as `500` and the transaction must roll back.

### Abort Session
- Method: POST
- Path: /sessions/{session_id}/abort
- Request Shape: Unchanged route parameter `session_id` as a UUID string and no request body.
- Response Shape: Unchanged session object with `id`, `task_id`, `subtask_id`, `started_at`, `ended_at`, `planned_duration_minutes`, `actual_duration_minutes`, `was_completed`, and `was_aborted`.
- Error Conditions: `404` when the session does not exist; `409` when the session is already ended; `503` when the database pool is unavailable or connection acquisition fails; `500` when the session update or required attempt insert fails unexpectedly. An attempt insert that returns no row is treated as `500` and the transaction must roll back.

### Domain Logic
- `backend/app/main.py`: own FastAPI lifespan startup and shutdown for the asyncpg pool and register shared HTTP mapping for database-unavailable failures so all existing routes expose consistent `detail` strings without widening the route surface.
- `backend/app/infrastructure/db/connection.py`: replace per-call `asyncpg.connect()` usage with application-scoped pool creation, pooled connection acquisition, and explicit database-unavailable exceptions when configuration or acquisition fails.
- `backend/app/domain/services/task_service.py`: run `start_task()` on one borrowed connection and one transaction, lock the target task row before the open-session check, read recent attempts and recent duration history on that same connection, apply the existing reducer and personalization engines unchanged, then persist the subtask row and session row inside the same transaction.
- `backend/app/domain/services/task_service.py` decision rules: keep the current `TaskNotFoundError`, `TaskAlreadyCompletedError`, and `OpenSessionExistsError` behavior unchanged; do not alter the difficulty reducer inputs or the planned-duration formula.
- `backend/app/domain/services/session_manager.py`: run `complete_session()` and `abort_session()` on one borrowed connection and one transaction, treat a no-row end-session update after the initial existence check as an already-ended conflict, require the attempt write to succeed, and mark the task completed only after the completed-session path has persisted both the session update and the attempt row.
- `backend/app/infrastructure/repositories/session_repository.py`: expose connection-bound read paths needed by `TaskService` and `SessionManager`, and make the end-session update target only rows where `ended_at` is still null.
- `backend/app/infrastructure/repositories/task_repository.py`: expose a connection-bound task read that locks the task row for the start flow and preserve all current task selection and task serialization fields.
- `backend/app/infrastructure/repositories/attempt_repository.py`: preserve the current attempt history read query and treat attempt creation as a required persistence step, not an optional best-effort write.
- Route modules remain thin. They do not compute difficulty, duration, ranking, or fallback values locally.

### Persistence
- `tasks` table: no schema change. `POST /tasks/{task_id}/start` reads the target task row under a database lock inside the start transaction. `POST /sessions/{session_id}/complete` continues to set `tasks.is_completed = TRUE` only for the completed-session path and only after the session update and attempt insert succeed.
- `sessions` table: no schema change. Session creation keeps the current columns and values. Session completion and abort keep writing `ended_at`, `actual_duration_minutes`, `was_completed`, and `was_aborted`, but the update query must target only rows where `ended_at IS NULL` so stale requests cannot overwrite an already-ended session.
- `attempts` table: no schema change. Attempt inserts remain derived from `sessions` and `subtasks`, but the insert result becomes mandatory; zero inserted rows must abort the surrounding transaction.
- `subtasks` table: no schema change. The start flow continues to insert exactly one generated subtask row before creating the session row.
- `subjects` table: no schema change and no new write path.
- Database pool behavior: no table change. All repositories acquire pooled connections instead of opening a new PostgreSQL connection per call.
- Database indexes, migrations, seed data, and table definitions remain untouched in phase 6.

## Frontend Design
### Views
- The root page at `/` remains the only frontend view involved in phase 6.
- The existing page-level error banner in `frontend/app/page.tsx` remains the only user-facing error display.
- No new page, modal, route, placeholder, or status surface is introduced.

### Components
- No frontend component file changes are part of phase 6.
- No API-client file changes are part of phase 6.
- No shared frontend type changes are part of phase 6.

### State Flow
- Frontend state ownership remains unchanged in `frontend/app/page.tsx`.
- The backend keeps returning `detail` strings on handled errors so the existing `frontend/services/api.ts` request helpers continue to raise `Error(message)` without modification.
- The frontend continues to surface those messages through the existing `error` state and status banner. No new client-side fallback, retry loop, or error normalization logic is added.

## File-Level Impact
### Files to Create
- backend/tests/test_connection.py
- backend/tests/test_difficulty_reducer.py
- backend/tests/test_subtask_engine.py
- backend/tests/test_task_service.py
- backend/tests/test_session_manager.py
- backend/tests/test_task_routes.py
- backend/tests/test_session_routes.py
- backend/tests/test_subject_routes.py

### Files to Modify
- backend/app/main.py
- backend/app/api/routes/tasks.py
- backend/app/api/routes/sessions.py
- backend/app/api/routes/subjects.py
- backend/app/domain/services/task_service.py
- backend/app/domain/services/session_manager.py
- backend/app/infrastructure/db/connection.py
- backend/app/infrastructure/repositories/task_repository.py
- backend/app/infrastructure/repositories/session_repository.py
- backend/app/infrastructure/repositories/attempt_repository.py
- backend/tests/test_session_repository.py

### Files Forbidden to Modify
- backend/app/api/schemas/**
- backend/app/domain/engines/personalization_engine.py
- backend/app/domain/engines/subtask_engine.py
- backend/app/domain/engines/difficulty_reducer.py
- backend/app/domain/services/subject_service.py
- backend/app/infrastructure/repositories/subject_repository.py
- backend/app/infrastructure/repositories/subtask_repository.py
- backend/requirements.txt
- frontend/**
- implementation-docs/devplan.md
- implementation-docs/current-phase.md
- implementation-docs/phase-1-plan.md
- implementation-docs/phase-2-plan.md
- implementation-docs/phase-3-plan.md
- implementation-docs/phase-4-plan.md
- implementation-docs/phase-5-plan.md

## Implementation Sequence
1. Modify `backend/app/infrastructure/db/connection.py` to create and close one asyncpg pool for the FastAPI app lifecycle and to expose pooled acquisition with explicit database-unavailable errors.
2. Modify `backend/app/main.py` to initialize and close that pool during app startup and shutdown and to register shared HTTP handling for database-unavailable failures.
3. Modify `backend/app/infrastructure/repositories/task_repository.py`, `backend/app/infrastructure/repositories/session_repository.py`, and `backend/app/infrastructure/repositories/attempt_repository.py` so repository methods use pooled acquisition by default and expose connection-bound methods for the start-task and session-resolution flows.
4. Tighten `backend/app/infrastructure/repositories/session_repository.py` so the end-session update matches only rows where `ended_at IS NULL` and returns `None` when a stale request tries to end an already-ended session.
5. Tighten `backend/app/infrastructure/repositories/attempt_repository.py` so attempt creation reports zero inserted rows as a failure condition instead of returning a silent `None` success path.
6. Modify `backend/app/domain/services/task_service.py` so `start_task()` borrows one connection, starts one transaction, locks the task row, checks completion and open-session state on that connection, reads recent attempts and duration history on that connection, and then writes the subtask row and session row before committing.
7. Modify `backend/app/domain/services/session_manager.py` so `complete_session()` and `abort_session()` borrow one connection, validate the session, end only open sessions, require the attempt write to succeed, and update `tasks.is_completed` only on the successful complete path.
8. Modify `backend/app/api/routes/tasks.py`, `backend/app/api/routes/sessions.py`, and `backend/app/api/routes/subjects.py` so each existing route keeps its current success payload and status codes while returning consistent `detail` messages for domain conflicts, database-unavailable failures, and unexpected internal failures.
9. Create `backend/tests/test_connection.py` to cover pool initialization failure, pooled acquisition failure mapping, and database URL normalization behavior.
10. Create `backend/tests/test_subtask_engine.py` and `backend/tests/test_difficulty_reducer.py` to cover every existing deterministic branch in those engines.
11. Create `backend/tests/test_task_service.py` and `backend/tests/test_session_manager.py` to cover not-found paths, conflict paths, required-write failure rollback paths, and the unchanged successful orchestration outputs.
12. Create `backend/tests/test_task_routes.py`, `backend/tests/test_session_routes.py`, and `backend/tests/test_subject_routes.py` to cover direct route-function HTTP mapping for the current routes without introducing a new frontend or browser test harness.
13. Extend `backend/tests/test_session_repository.py` to assert the tightened `ended_at IS NULL` guard and the unchanged actual-duration write expression.
14. Run the backend pytest suite covering the existing tests plus all new phase 6 tests, and confirm that no frontend file changed and no new dependency was introduced.

## Completion Criteria
1. The FastAPI application opens one asyncpg pool at startup, closes it at shutdown, and repository calls no longer create a brand-new PostgreSQL connection for every operation.
2. `POST /tasks/{task_id}/start` executes on one borrowed connection and one transaction, locks the target task row before the open-session check, and preserves the existing instruction and planned-duration formulas.
3. `POST /sessions/{session_id}/complete` and `POST /sessions/{session_id}/abort` update only sessions where `ended_at` is null, so a stale second request cannot overwrite an already-ended session.
4. A missing attempt insert result during complete or abort is treated as a backend failure and the surrounding transaction does not commit the session update or task-completion update.
5. All handled backend failures return the existing FastAPI `detail` string shape, with `404`, `409`, `400`, `422`, `503`, and `500` statuses limited to the conditions defined in this plan.
6. No route path, no success response shape, no database schema object, no personalization rule, and no difficulty-reduction rule changes in phase 6.
7. The backend test suite contains new coverage for subtask generation, difficulty reduction, task-service orchestration, session-manager orchestration, route error mapping, connection lifecycle, and the tightened session repository query contract.
8. `backend/tests/test_personalization_engine.py` and `backend/tests/test_session_repository.py` remain in the suite and pass alongside the new phase 6 tests.
9. No frontend file changes and no frontend dependency changes exist in the phase 6 implementation.
10. No AI code path, prompt file, model configuration, or external AI dependency exists in the completed phase 6 file set.

## Out-of-Scope Protection
- Do not add AI assist in any form. The current repository has no bounded AI contract, no AI dependency surface, and no existing AI error path to stabilize.
- Do not add or change frontend code. The current frontend already renders backend error messages through the page-level status banner, and phase 6 does not widen the UI surface.
- Do not add route tests that require a new browser runner, DOM runner, or frontend dependency. Keep phase 6 tests inside the existing backend pytest surface.
- Do not change any API schema file or widen any success response payload to include error metadata, timing metadata, or debug fields.
- Do not add caching, retries, background workers, or schema-level locking infrastructure. The bounded performance work in this phase is connection pooling and connection reuse only.
- Do not rewrite the personalization engine, next-task ranking, subtask generation, or difficulty reduction logic.
- Do not add database migrations, indexes, or seed updates to address concurrency. Phase 6 resolves the current race windows in application code only.
- Do not modify prior phase artifacts or `implementation-docs/devplan.md`.