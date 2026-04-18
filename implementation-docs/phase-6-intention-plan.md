# Phase
Phase 6

# Summary
Phase 6 hardens the existing backend-only Study Buddy flow without widening the product surface. The implementation is limited to replacing per-call PostgreSQL connections with application-scoped pooled acquisition, tightening the existing start-task and session-resolution orchestration so their dependent reads and writes execute on one borrowed connection and one transaction, standardizing route-level HTTP mapping for the current task, subject, next-task, and session endpoints, and adding backend pytest coverage for the newly constrained connection, engine, service, repository, and route behavior. No schema, frontend, API success shape, personalization rule, subtask rule, or difficulty rule change is allowed.

# Repository Reality Check
- Existing backend surface: backend/app/main.py currently creates a plain FastAPI app, registers CORS, and includes the existing tasks, subjects, and sessions routers, but it does not own application lifespan pool startup or shutdown and it has no shared exception mapping. backend/app/infrastructure/db/connection.py currently loads DATABASE_URL at import time, normalizes postgres:// to postgresql:// once, and opens a brand-new asyncpg connection inside get_connection() for every repository call. backend/app/api/routes/tasks.py, backend/app/api/routes/sessions.py, and backend/app/api/routes/subjects.py already expose the current route surface and already map some domain exceptions to HTTP responses, but they do not distinguish database-unavailable failures from generic 500s. backend/app/domain/services/task_service.py already owns get_next_task() and start_task(), but start_task() performs task lookup, open-session lookup, recent-attempt reads, and duration-history reads before opening the write transaction, so the current flow is split across separate connections and race windows remain. backend/app/domain/services/session_manager.py already owns complete_session() and abort_session(), but it performs the existence and ended-state checks before borrowing the write connection, treats a no-row end_session_tx(...) result as not found, and does not enforce attempt creation as a required persistence step. backend/app/infrastructure/repositories/task_repository.py, backend/app/infrastructure/repositories/session_repository.py, and backend/app/infrastructure/repositories/attempt_repository.py all currently rely on get_connection() for default reads and writes, and only session_repository.py and subtask_repository.py currently expose any connection-bound write path.
- Existing frontend surface: frontend/app/page.tsx already stores backend error text in error state and renders it through the existing page-level status banner. frontend/services/api.ts already raises Error(detail) when backend responses include the existing FastAPI detail string. frontend/types/study-buddy.ts already matches the unchanged task, session, and instruction payloads. Phase 6 does not require any frontend edit.
- Existing tests: the only backend pytest files currently present are backend/tests/test_personalization_engine.py and backend/tests/test_session_repository.py. The existing tests cover personalization-engine ranking and duration logic plus part of the session-repository query and duration-write expression, but there is no current test coverage for connection lifecycle, route-level error mapping, task-service orchestration, session-manager orchestration, difficulty reduction, or subtask generation.
- Missing required surfaces: implementation-docs/phase-6-intention-plan.md does not exist yet. The backend currently has no phase-6 test files for connection lifecycle, task routes, session routes, subject routes, task service, session manager, difficulty reducer, or subtask engine. The backend also has no explicit database-unavailable exception type or shared pool lifecycle surface yet.

# Files to Create
## backend/tests/test_connection.py
- Why it must exist: Phase 6 requires direct regression coverage for connection-pool initialization, pooled acquisition failure behavior, and database URL normalization, and no existing test file covers backend/app/infrastructure/db/connection.py.
- Responsibility: Verify the connection module's bounded runtime contract only: URL normalization, explicit database-unavailable failure signaling when pool creation or acquisition fails, and the expected pool lifecycle entry points used by the FastAPI app.
- Forbidden contents: No live database dependency, no route tests, no service orchestration tests, no frontend assertions, and no assertions about schema changes or new dependencies.

## backend/tests/test_difficulty_reducer.py
- Why it must exist: Phase 6 explicitly adds deterministic engine coverage for the existing difficulty reducer, and no current file tests backend/app/domain/engines/difficulty_reducer.py.
- Responsibility: Cover every current branch in reduce_instruction(...), including no-context pass-through, abort-driven reduction, completion-driven increment, and the existing upper-bound cap.
- Forbidden contents: No reducer rule changes, no service-level orchestration, no repository mocking beyond what is necessary to call the pure engine, and no frontend or route concerns.

## backend/tests/test_subtask_engine.py
- Why it must exist: Phase 6 explicitly adds deterministic engine coverage for the existing subtask generation rules, and no current file tests backend/app/domain/engines/subtask_engine.py.
- Responsibility: Cover every current generate_subtask(...) branch for write, read, math, and fallback titles using the existing response keys and values.
- Forbidden contents: No changes to the generation rules, no difficulty-reducer assertions, no database concerns, and no service or route behavior.

## backend/tests/test_task_service.py
- Why it must exist: The start-task hardening in Phase 6 moves more coordination into one borrowed connection and one transaction, and there is no current test file that constrains task-service orchestration or failure paths.
- Responsibility: Verify TaskService.get_next_task() and TaskService.start_task() behavior only, including not-found and conflict paths, same-connection orchestration across task/session/attempt/subtask dependencies, required-write failure handling, and unchanged success payload shape.
- Forbidden contents: No direct FastAPI route assertions, no live database dependency, no frontend assertions, and no rewriting of personalization, subtask, or difficulty rules.

## backend/tests/test_session_manager.py
- Why it must exist: Phase 6 tightens complete_session() and abort_session() around one connection, one transaction, already-ended conflict handling, mandatory attempt persistence, and rollback-sensitive task completion, and no current test file covers that orchestration.
- Responsibility: Verify SessionManager.complete_session() and SessionManager.abort_session() behavior for not-found, already-ended, stale-end conflict, attempt-write failure, rollback-sensitive complete path, and unchanged success response shape.
- Forbidden contents: No route-level HTTP assertions, no live database dependency, no task-start logic, and no schema assertions.

## backend/tests/test_task_routes.py
- Why it must exist: Phase 6 requires direct route-function coverage for the current task routes so the new HTTP error mapping remains stable without changing payload shapes.
- Responsibility: Cover create_task(), list_tasks(), start_task(), and get_next_task() in backend/app/api/routes/tasks.py for the planned 400, 404, 409, 422, 503, and 500 mappings while preserving the existing success response contract.
- Forbidden contents: No browser or frontend runner setup, no UI assertions, no schema-file edits, and no route-path or success-payload changes.

## backend/tests/test_session_routes.py
- Why it must exist: Phase 6 requires direct route-function coverage for the current complete and abort endpoints so their not-found, conflict, database-unavailable, and generic failure mappings stay bounded.
- Responsibility: Cover complete_session() and abort_session() in backend/app/api/routes/sessions.py for the planned 404, 409, 503, and 500 mappings while preserving the current success response contract.
- Forbidden contents: No live database dependency, no frontend assertions, no new route surface, and no schema changes.

## backend/tests/test_subject_routes.py
- Why it must exist: Phase 6 requires direct route-function coverage for /subjects so the list endpoint maps pooled-connection failures to 503 and preserves the current success response.
- Responsibility: Cover list_subjects() in backend/app/api/routes/subjects.py for the planned 503 and 500 mappings while preserving the existing subject response shape.
- Forbidden contents: No subject-service logic changes, no database integration harness, no frontend assertions, and no route or schema changes.

# Files to Modify
## backend/app/main.py
- Why it must change: The current file only constructs the FastAPI app, CORS middleware, and router registration. Phase 6 requires this file to own application-scoped pool startup and shutdown and shared HTTP mapping for database-unavailable failures.
- Exact scope of change: Add FastAPI lifespan ownership for initializing and closing the asyncpg pool through backend/app/infrastructure/db/connection.py, and register one shared exception handler for the explicit database-unavailable exception so existing routes can return consistent detail strings without duplicating pool-failure handling logic. Keep the current app instance, existing CORS origin list, and existing router registration.
- Must remain untouched: Route inclusion order, route paths, middleware configuration values, and the public FastAPI title must remain unchanged. Do not add new routers, new middleware, new dependencies, or any frontend behavior.

## backend/app/api/routes/tasks.py
- Why it must change: The current task routes already map validation and domain conflicts, but they collapse database-unavailable failures into generic 500 responses and the /next handler uses inconsistent literal status handling and generic error text.
- Exact scope of change: Limit edits to create_task(), list_tasks(), start_task(), and get_next_task(). Preserve the current success response models and payload shapes while adding explicit 503 mapping for the shared database-unavailable exception, preserving the existing 400 title validation and subject foreign-key mapping for create_task(), preserving 404 and 409 mappings for start_task(), preserving 404 for no next task, and making unexpected failures consistently return the planned 500 detail strings. Keep the route module thin by delegating all business logic to TaskService.
- Must remain untouched: Router paths, response_model declarations, request payload shapes, module-level service wiring, and the existing schema classes in backend/app/api/schemas/tasks.py must remain unchanged. Do not compute difficulty, duration, ranking, or fallback data in this module.

## backend/app/api/routes/sessions.py
- Why it must change: The current session routes only distinguish not-found and already-ended domain errors from generic 500 failures and do not map database-unavailable failures separately.
- Exact scope of change: Limit edits to complete_session() and abort_session() so they preserve the current response model and domain error mapping while adding explicit 503 handling for the shared database-unavailable exception and keeping unexpected failures at 500 with the planned detail strings.
- Must remain untouched: Router paths, response_model declarations, module-level SessionManager construction, and the existing session schema contract in backend/app/api/schemas/sessions.py must remain unchanged. No session-resolution logic may move into the route layer.

## backend/app/api/routes/subjects.py
- Why it must change: The current subjects route maps all failures to 500, but Phase 6 requires pooled-connection failures to return 503 and all handled errors to keep the existing detail-string shape.
- Exact scope of change: Limit edits to list_subjects() so it preserves the current success response contract while mapping the shared database-unavailable exception to 503 and leaving unexpected failures as 500.
- Must remain untouched: The /subjects path, response_model declaration, module-level SubjectService construction, and the existing backend/app/api/schemas/subjects.py contract must remain unchanged. No subject sorting or fallback behavior may move into the route.

## backend/app/domain/services/task_service.py
- Why it must change: start_task() currently validates task existence, completion state, open-session state, recent attempts, and recent duration history across separate repository calls before opening the write transaction, so the start flow is not fully connection-bound and still has a race window. The service also depends on repositories that only partly expose connection-bound reads.
- Exact scope of change: Keep create_task() and list_tasks() as pass-throughs. Keep get_next_task() on the current repository-candidate plus personalization-engine selection path, changing only what is required to use the pooled repository surface if signatures change. Rework start_task() so one borrowed connection and one transaction cover the task lookup with row lock, completed-task rejection, open-session rejection, recent-attempt history read, recent duration-history read, subtask generation, difficulty reduction, subtask persistence, and session persistence. Preserve the existing TaskNotFoundError, TaskAlreadyCompletedError, and OpenSessionExistsError behavior, preserve the current recent_completions and recent_aborts counting, preserve calculate_planned_duration_minutes(...) and reduce_instruction(generate_subtask(...), ...) usage, and preserve the returned {"session": ..., "instruction": ...} shape. Treat a missing persisted subtask or session row as a backend failure instead of a silent success path.
- Must remain untouched: No HTTPException handling, no schema shaping, no SQL strings, no personalization-formula change, no difficulty-rule change, and no create_task/list_tasks behavior change.

## backend/app/domain/services/session_manager.py
- Why it must change: complete_session() and abort_session() currently perform the pre-checks outside the write transaction, treat a no-row end_session_tx(...) result as not found instead of stale already-ended conflict, and do not enforce attempt creation as a required persistence step.
- Exact scope of change: Limit edits to complete_session() and abort_session(). Rework both methods so one borrowed connection and one transaction cover the session read, already-ended validation, end-session update, required attempt insert, and task-completion write on the successful complete path. After the initial existence check on that borrowed connection, treat a no-row end_session_tx(...) result as an already-ended conflict. Require the attempt insert to succeed before the transaction can commit. Preserve task completion only for the successful complete path and keep abort_session() from marking the task complete.
- Must remain untouched: SessionNotFoundError and SessionAlreadyEndedError class identities, public method names, and the absence of any frontend or route logic in this service. Do not change create_session() because this service does not currently define one.

## backend/app/infrastructure/db/connection.py
- Why it must change: The current module opens a new asyncpg connection for every get_connection() call and raises a generic RuntimeError only when DATABASE_URL is missing at import time. Phase 6 requires pooled reuse, explicit database-unavailable failure signaling, and lifecycle hooks compatible with FastAPI startup and shutdown.
- Exact scope of change: Replace the per-call asyncpg.connect(...) pattern with one application-scoped asyncpg pool lifecycle surface, a bounded URL-normalization helper for postgres:// to postgresql:// conversion, and pooled acquisition helpers used by repositories and FastAPI lifespan. Introduce an explicit database-unavailable exception for missing configuration, pool initialization failure, or connection acquisition failure so the route layer can map those cases to 503 through the shared app handler.
- Must remain untouched: The module must remain the only backend location that knows about DATABASE_URL loading and normalization details. Do not add retries, caching, schema changes, or route logic here.

## backend/app/infrastructure/repositories/task_repository.py
- Why it must change: The current repository still uses a per-call connection context for every method and does not expose a connection-bound task read that locks the task row for the start flow.
- Exact scope of change: Preserve _serialize_task(...), _serialize_task_candidate(...), create_task(), list_tasks(), get_task(), and get_next_task_candidates() as the current repository responsibilities, but switch their default database access to pooled acquisition from backend/app/infrastructure/db/connection.py. Add a connection-bound task read for the start flow that selects the current task fields and locks the row before TaskService performs the open-session check. If needed, add only the minimum connection-bound helper surface for methods already owned by this repository.
- Must remain untouched: The existing task field set returned by _serialize_task(...), the existing candidate summary field set returned by _serialize_task_candidate(...), task ordering for list_tasks(), and the absence of business ranking logic in this repository. Do not add writes beyond the existing create path.

## backend/app/infrastructure/repositories/session_repository.py
- Why it must change: The current repository still uses per-call acquisition for default reads and writes, and end_session_tx(...) updates any matching session id without guarding ended_at IS NULL, so a stale second request can overwrite an already-ended session.
- Exact scope of change: Preserve _serialize_session(...), _insert_session_record(...), create_session(), create_session_in_connection(...), get_open_session_for_task(), get_session(), mark_task_completed_tx(...), end_session(), and get_recent_task_duration_history() as the current repository responsibilities, but move default database access to pooled acquisition and add the minimum connection-bound read helpers needed by TaskService.start_task() and SessionManager.complete_session()/abort_session(). Tighten end_session_tx(...) so its update matches only rows where ended_at IS NULL while preserving the current actual_duration_minutes expression and returned session shape.
- Must remain untouched: Session serialization fields, session create fields, planned-duration persistence, actual-duration calculation formula, and task-completion write responsibility must remain unchanged. This repository must not take on difficulty logic, personalization logic, or HTTP mapping.

## backend/app/infrastructure/repositories/attempt_repository.py
- Why it must change: The current repository still uses per-call acquisition for get_recent_attempts(...) and create_attempt(...) may return None, which leaves attempt persistence as an optional best-effort write from the service perspective.
- Exact scope of change: Preserve the current attempt-history read query semantics and result shape, but move default acquisition to the pooled connection surface and add the minimum connection-bound recent-attempt read helper needed by TaskService.start_task(). Tighten create_attempt(...) so the session-resolution flow can treat a zero-row insert as a required-write failure rather than a silent success path.
- Must remain untouched: The existing join from attempts to sessions and subtasks, the current history ordering, the current serialized field set, and the absence of route or business logic in this repository.

## backend/tests/test_session_repository.py
- Why it must change: The existing file already constrains the duration-history query and actual-duration expression, but Phase 6 also requires a regression assertion that end_session_tx(...) only targets still-open sessions.
- Exact scope of change: Keep the existing tests intact and extend the end_session_tx(...) coverage so it also asserts the update query includes the ended_at IS NULL guard while preserving the current whole-minute actual_duration_minutes expression check and serialized response expectation.
- Must remain untouched: The existing duration-history test intent, the existing actual-duration expression assertion, and the file's repository-only focus. Do not widen this file into route, service, or frontend testing.

# Files Forbidden to Modify
- backend/app/api/schemas/**
- backend/app/domain/engines/personalization_engine.py
- backend/app/domain/engines/subtask_engine.py
- backend/app/domain/engines/difficulty_reducer.py
- backend/app/domain/services/subject_service.py
- backend/app/infrastructure/repositories/subject_repository.py
- backend/app/infrastructure/repositories/subtask_repository.py
- backend/tests/test_personalization_engine.py
- backend/requirements.txt
- frontend/**
- implementation-docs/devplan.md
- implementation-docs/current-phase.md
- implementation-docs/phase-1-plan.md
- implementation-docs/phase-2-plan.md
- implementation-docs/phase-3-plan.md
- implementation-docs/phase-4-plan.md
- implementation-docs/phase-5-plan.md
- Any file outside the exact create and modify lists in this intention plan

# Required Contracts Between Files
- backend/app/main.py must call the connection-pool startup and shutdown functions from backend/app/infrastructure/db/connection.py during FastAPI lifespan, and it must translate the connection module's explicit database-unavailable exception into the common 503 detail-string response shape used by the route layer.
- backend/app/api/routes/tasks.py must remain a thin adapter over backend/app/domain/services/task_service.py. create_task(), list_tasks(), start_task(), and get_next_task() keep their current success payloads and status codes while mapping TaskService domain exceptions and the shared database-unavailable exception to HTTP responses.
- backend/app/api/routes/sessions.py must remain a thin adapter over backend/app/domain/services/session_manager.py. complete_session() and abort_session() must not implement session state logic locally; they only translate SessionManager outcomes into the existing HTTP surface.
- backend/app/api/routes/subjects.py must remain a thin adapter over backend/app/domain/services/subject_service.py and must rely on the shared database-unavailable mapping for pooled-connection failures.
- backend/app/domain/services/task_service.py must own the full start-task orchestration. It must borrow one connection, begin one transaction, call a task-repository locked read, call session-repository and attempt-repository connection-bound reads on that same connection, compute the instruction through the unchanged subtask and difficulty engines, then persist the subtask through backend/app/infrastructure/repositories/subtask_repository.py and persist the session through backend/app/infrastructure/repositories/session_repository.py before commit.
- backend/app/domain/services/session_manager.py must own the full session-resolution orchestration. It must borrow one connection, begin one transaction, validate the session through backend/app/infrastructure/repositories/session_repository.py, end only still-open sessions through end_session_tx(...), require backend/app/infrastructure/repositories/attempt_repository.py to persist the attempt row, and only on the successful complete path call mark_task_completed_tx(...).
- backend/app/infrastructure/repositories/task_repository.py, backend/app/infrastructure/repositories/session_repository.py, and backend/app/infrastructure/repositories/attempt_repository.py must expose pooled default acquisition for ordinary calls and only the minimum connection-bound helpers needed for the connection-scoped service flows. They must not absorb business logic from the services.
- frontend/services/api.ts and frontend/app/page.tsx remain unchanged downstream consumers. They continue to depend on backend responses returning the existing detail string for handled errors and the existing success payload shapes for tasks, sessions, and instructions.

# Migration / Schema Impact
- No migration or schema change is allowed.
- No table, column, index, seed, or type-generation artifact changes are required.
- The only persistence change in Phase 6 is runtime connection management and tighter transaction/query behavior against the existing schema.

# Test Surface Impact
- Add backend/tests/test_connection.py.
- Add backend/tests/test_difficulty_reducer.py.
- Add backend/tests/test_subtask_engine.py.
- Add backend/tests/test_task_service.py.
- Add backend/tests/test_session_manager.py.
- Add backend/tests/test_task_routes.py.
- Add backend/tests/test_session_routes.py.
- Add backend/tests/test_subject_routes.py.
- Modify backend/tests/test_session_repository.py.
- Keep backend/tests/test_personalization_engine.py in the suite unchanged.

# Risk Points
- The main implementation drift risk is leaving any start-task validation reads outside the single borrowed connection and transaction in backend/app/domain/services/task_service.py, which would preserve the race window Phase 6 is explicitly closing.
- A second drift risk is treating a no-row end_session_tx(...) result as not found instead of already ended after the initial existence check in backend/app/domain/services/session_manager.py.
- Another concrete risk is allowing backend/app/infrastructure/repositories/attempt_repository.py to keep returning a silent None success path for create_attempt(...), which would let session updates commit without the required attempt row.
- A repository-boundary risk is moving ranking, difficulty, duration, or fallback decision logic into the route or repository layers while tightening transaction and pooling behavior.
- A scope risk is widening edits into backend/app/api/schemas/**, frontend/**, backend/app/domain/engines/*.py, or implementation-docs files outside the new phase-6 intention artifact.
- A contract risk is changing any success payload shape or handled-error detail-string format, which would break the unchanged frontend request helpers and page-level error banner flow.