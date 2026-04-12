# Phase
Phase 3

# Summary
Phase 3 adds adaptive session outcomes and backend-selected next-task recommendation to the existing Study Buddy flow without widening the UI surface. In the current repository, that means adding one new attempts repository, extending the existing task-start and session-end domain flows so attempts are read and written around already-existing session and subtask persistence, exposing one new `GET /next` route inside the existing tasks router, and teaching the root frontend page plus the existing session panel to render a backend-provided recommendation when no session is active. This artifact intentionally constrains the write surface to the files allowed by the approved phase 3 plan; it does not widen scope to files the user listed when the approved plan forbids those edits.

# Repository Reality Check
- Existing backend surface: [backend/app/api/routes/tasks.py](backend/app/api/routes/tasks.py) already exposes `POST /tasks`, `GET /tasks`, and `POST /tasks/{task_id}/start` through `TaskService`. [backend/app/api/routes/sessions.py](backend/app/api/routes/sessions.py) already exposes `POST /sessions/{session_id}/complete` and `POST /sessions/{session_id}/abort` through `SessionManager`. [backend/app/domain/services/task_service.py](backend/app/domain/services/task_service.py) already loads the task, rejects an open session, generates one instruction through the existing engines, writes one subtask through [backend/app/infrastructure/repositories/subtask_repository.py](backend/app/infrastructure/repositories/subtask_repository.py), and writes one session through [backend/app/infrastructure/repositories/session_repository.py](backend/app/infrastructure/repositories/session_repository.py) inside one transaction. [backend/app/domain/services/session_manager.py](backend/app/domain/services/session_manager.py) currently validates existence and ended state, then ends the session through [backend/app/infrastructure/repositories/session_repository.py](backend/app/infrastructure/repositories/session_repository.py) with no attempt write path. [backend/app/domain/engines/difficulty_reducer.py](backend/app/domain/engines/difficulty_reducer.py) is still an identity reducer. [backend/app/infrastructure/repositories/task_repository.py](backend/app/infrastructure/repositories/task_repository.py) has task create, list, and get methods only. No attempts repository exists.
- Existing frontend surface: [frontend/app/page.tsx](frontend/app/page.tsx) is still the single page that owns `tasks`, `subjects`, `title`, `selectedSubjectId`, `activeSession`, `activeInstruction`, `isPending`, and `error`. It loads subjects and tasks on mount, starts tasks through [frontend/services/api.ts](frontend/services/api.ts), and renders either the active-session view or a static empty placeholder. [frontend/components/session-view.tsx](frontend/components/session-view.tsx) renders only the active-session state. [frontend/services/api.ts](frontend/services/api.ts) has methods for task create/list/start and session complete/abort, but no `GET /next` client. [frontend/types/study-buddy.ts](frontend/types/study-buddy.ts) already contains the `Task`, `Session`, `Instruction`, and `TaskStartResponse` contracts needed by the approved phase 3 plan.
- Existing tests: No backend or frontend product test files are present anywhere in the current repository tree. There is no existing `backend/tests`, `frontend/__tests__`, or equivalent test harness surface that can be named as an exact modification target.
- Missing required surfaces: [backend/app/infrastructure/repositories/attempt_repository.py](backend/app/infrastructure/repositories/attempt_repository.py) does not exist. No repository method currently reads recent attempts for one task. No repository method currently inserts one attempt from an ended session. No task recommendation query exists. No task service method exposes `GET /next`. No session-manager transaction currently binds session end and attempt insert together. No frontend API method fetches `GET /next`. No root-page state currently stores a backend recommendation. No session-panel component currently renders a recommended next task.

# Files to Create
## backend/app/infrastructure/repositories/attempt_repository.py
- Why it must exist: Phase 3 requires one repository dedicated to reading the last five attempts for one task and inserting one attempt row derived from an ended session, and no attempt repository exists in the current backend tree.
- Responsibility: Own phase 3 attempt persistence only. It must provide one read path that joins `attempts` to `sessions` to return the newest five attempts for a task, and one write path that inserts an `attempts` row by reading the ended session and linked subtask difficulty inside an existing transaction-capable flow.
- Forbidden contents: No route wiring, no domain counting logic, no difficulty-reduction rules, no task recommendation query, no session-state validation, and no writes to `sessions`, `tasks`, `subjects`, or `subtasks` outside the one attempt insert required by phase 3.

# Files to Modify
## backend/app/api/routes/sessions.py
- Why it must change: The session routes currently construct `SessionManager` with only `SessionRepository`, but phase 3 requires session completion and abort to write one attempt row in the same transactional flow as the session end.
- Exact scope of change: Update only the dependency construction so `SessionManager` receives the new `AttemptRepository` alongside the existing `SessionRepository`. Keep the existing `POST /sessions/{session_id}/complete` and `POST /sessions/{session_id}/abort` handlers, their route paths, their response model, and their current 404, 409, and 500 mappings. No new route is added here.
- Must remain untouched: The public route paths, the `SessionResponse` contract imported from [backend/app/api/schemas/sessions.py](backend/app/api/schemas/sessions.py), the existing exception-to-HTTP mapping shape, and the absence of SQL or business logic in the route module.

## backend/app/domain/engines/difficulty_reducer.py
- Why it must change: The reducer is still a pass-through, but phase 3 requires deterministic mutation of `instruction.difficulty_level` based on counts derived from the last five attempts.
- Exact scope of change: Replace the identity implementation with the approved recent-history rule set only. The function must read `recent_aborts` and `recent_completions` from the provided context, preserve `instruction.title`, preserve other instruction keys if present, set `difficulty_level` to `1` when `recent_aborts > 2`, otherwise increase `difficulty_level` by exactly `1` and cap at `5` when `recent_completions > 3`, and otherwise leave `difficulty_level` unchanged. The abort rule must take precedence over the completion rule.
- Must remain untouched: The module remains a pure domain-engine surface with no database calls, no task lookup, no frontend concerns, and no heuristics beyond the two explicit rules approved in [implementation-docs/phase-3-plan.md](implementation-docs/phase-3-plan.md).

## backend/app/domain/services/session_manager.py
- Why it must change: The current session manager ends sessions through `SessionRepository` only, which cannot satisfy the phase 3 requirement that session end and attempt insert succeed or fail together.
- Exact scope of change: Extend the constructor to accept `AttemptRepository`. Keep the existing `SessionNotFoundError` and `SessionAlreadyEndedError` classes and the existing validation order. Change `complete_session` and `abort_session` so, after validation, each opens one database transaction, updates the session through a connection-bound repository method, inserts exactly one attempt through `AttemptRepository` with the explicit outcome string for that route, and returns the updated session row only after both writes succeed.
- Must remain untouched: `create_session`, the current existence and already-ended validation behavior, the current exception types, and the current returned session shape.

## backend/app/domain/services/task_service.py
- Why it must change: The current task-start flow generates and reduces one instruction without any history input, and there is no domain method for backend-selected next-task recommendation.
- Exact scope of change: Extend the constructor to accept `AttemptRepository`. Keep `create_task` and `list_tasks` behavior intact. In `start_task`, keep the current task lookup and open-session rejection, then read the newest five attempts for the same task through `AttemptRepository`, count completed and aborted outcomes in the service layer, pass those counts into `reduce_instruction`, and preserve the existing one-transaction subtask-plus-session write flow using the reduced `difficulty_level`. Add one `get_next_task` method that delegates recommendation selection to `TaskRepository` and raises the existing task-not-found style domain error when no incomplete task exists.
- Must remain untouched: The existing `TaskNotFoundError` and `OpenSessionExistsError` classes, use of [backend/app/domain/engines/subtask_engine.py](backend/app/domain/engines/subtask_engine.py) for instruction generation, the one-transaction creation of subtask plus session, and the current `{"session": ..., "instruction": ...}` return shape for task start.

## backend/app/infrastructure/repositories/session_repository.py
- Why it must change: Phase 3 needs a session-end path that can run inside the same transaction as the attempt insert, but the current repository ends sessions only by opening its own connection.
- Exact scope of change: Add a bounded connection-aware method for ending a session using an already-open connection or transaction while preserving the current serialized session shape. The existing standalone `end_session` method may delegate to the new helper, but no other repository behavior should expand. The session-end update fields remain `ended_at`, `was_completed`, and `was_aborted`, and the returned columns remain the current session response fields only.
- Must remain untouched: `_serialize_session`, the current open-session lookup contract, the current session insert contract, and the field set returned for session reads and writes.

## backend/app/infrastructure/repositories/task_repository.py
- Why it must change: The repository has no read path for the backend-selected next task required by `GET /next`.
- Exact scope of change: Add one recommendation method that returns exactly one incomplete task using the approved latest-aborted-session-first rule and oldest-incomplete fallback rule. The method must remain a read-only query surface and must return the existing serialized task shape already used by the task routes and frontend. No existing create, list, or get behavior should change.
- Must remain untouched: The existing task serializer, the current task creation query, the current task listing order for `GET /tasks`, and the current single-task lookup by id.

## backend/app/api/routes/tasks.py
- Why it must change: The tasks router must construct `TaskService` with the new `AttemptRepository` dependency and expose the new `GET /next` endpoint without creating a new router file.
- Exact scope of change: Update service construction to pass `AttemptRepository`, keep the existing `POST /tasks`, `GET /tasks`, and `POST /tasks/{task_id}/start` handlers intact, and add one `GET /next` handler that returns the existing `TaskResponse` model through `TaskService.get_next_task`. Map missing recommendation to the same 404 not-found style already used for missing tasks and map unexpected failures to 500.
- Must remain untouched: Existing task route paths, blank-title validation, current response models for create/list/start, and the absence of SQL or business logic in the route layer.

## frontend/services/api.ts
- Why it must change: The frontend API client has no method for `GET /next`, so the root page cannot fetch a backend recommendation.
- Exact scope of change: Add one `getNextTask` client method that calls `GET /next` through the existing request helper. The method must convert a backend `404` for `/next` into `null` so the page can render the existing placeholder state, while leaving all other request failures as errors. Existing task and session client methods stay intact.
- Must remain untouched: `API_BASE_URL`, the shared request helper’s general fetch behavior, and the existing endpoint paths for task create/list/start and session complete/abort.

## frontend/app/page.tsx
- Why it must change: The root page currently fetches only subjects and tasks and renders a static no-session placeholder when there is no active session, but phase 3 requires backend recommendation state to live here.
- Exact scope of change: Add root-page state for `nextTask`. On initial load, fetch subjects, tasks, and `getNextTask` in parallel and store all three results. After task creation, refresh tasks plus `nextTask`. After starting a task, keep the existing session and instruction state updates, clear `nextTask` locally, and do not compute difficulty or recommendation in React. After session completion or abort, clear active session state and refresh tasks plus `nextTask`. Continue deriving subject display data for tasks and recommended task by matching `subject_id` against the already-loaded subject list.
- Must remain untouched: The page remains the single frontend view, owns page-level loading and error state, keeps task creation and session resolution on the same page, performs all network access through [frontend/services/api.ts](frontend/services/api.ts), and does not add direct database access or frontend-owned recommendation logic.

## frontend/components/session-view.tsx
- Why it must change: The component currently renders only an active session, but phase 3 requires the same panel area to also render a recommended next task when there is no active session.
- Exact scope of change: Extend the component so it can render either the existing active-session state or a recommendation state driven entirely by props from [frontend/app/page.tsx](frontend/app/page.tsx). The recommendation state must display the recommended task title, matched subject metadata supplied by the page, and one start action wired to the existing start callback. The existing active-session display and complete or abort actions must remain intact.
- Must remain untouched: The component remains presentational, does not fetch data, does not calculate recommendation ranking or difficulty, and does not create a second session panel outside the existing page structure.

# Files Forbidden to Modify
- [backend/app/main.py](backend/app/main.py)
- [backend/app/api/schemas/sessions.py](backend/app/api/schemas/sessions.py)
- [frontend/types/study-buddy.ts](frontend/types/study-buddy.ts)
- [backend/app/api/routes/subjects.py](backend/app/api/routes/subjects.py)
- [backend/app/api/schemas/subjects.py](backend/app/api/schemas/subjects.py)
- [backend/app/api/schemas/tasks.py](backend/app/api/schemas/tasks.py)
- [backend/app/domain/engines/subtask_engine.py](backend/app/domain/engines/subtask_engine.py)
- [backend/app/domain/services/subject_service.py](backend/app/domain/services/subject_service.py)
- [backend/app/infrastructure/db/connection.py](backend/app/infrastructure/db/connection.py)
- [backend/app/infrastructure/repositories/subject_repository.py](backend/app/infrastructure/repositories/subject_repository.py)
- [backend/app/infrastructure/repositories/subtask_repository.py](backend/app/infrastructure/repositories/subtask_repository.py)
- [frontend/app/layout.tsx](frontend/app/layout.tsx)
- [frontend/app/globals.css](frontend/app/globals.css)
- [frontend/components/subject-icon.tsx](frontend/components/subject-icon.tsx)
- [frontend/components/task-form.tsx](frontend/components/task-form.tsx)
- [frontend/components/task-list.tsx](frontend/components/task-list.tsx)
- Any new file under [frontend/app](frontend/app) other than the already-existing root page
- Any new backend route module other than the approved new repository file
- Any file not named in this intention plan as a create or modify target

# Required Contracts Between Files
- [backend/app/api/routes/tasks.py](backend/app/api/routes/tasks.py) must remain the only route surface for `GET /next` and `POST /tasks/{task_id}/start`; it must call [backend/app/domain/services/task_service.py](backend/app/domain/services/task_service.py) and must not read the database directly.
- [backend/app/domain/services/task_service.py](backend/app/domain/services/task_service.py) must call [backend/app/infrastructure/repositories/task_repository.py](backend/app/infrastructure/repositories/task_repository.py) for task reads and recommendation selection, [backend/app/infrastructure/repositories/session_repository.py](backend/app/infrastructure/repositories/session_repository.py) for open-session rejection and session insertion, [backend/app/infrastructure/repositories/subtask_repository.py](backend/app/infrastructure/repositories/subtask_repository.py) for subtask insertion, and [backend/app/infrastructure/repositories/attempt_repository.py](backend/app/infrastructure/repositories/attempt_repository.py) for recent-attempt reads.
- [backend/app/domain/services/task_service.py](backend/app/domain/services/task_service.py) must remain the layer that counts recent completed versus aborted outcomes before calling [backend/app/domain/engines/difficulty_reducer.py](backend/app/domain/engines/difficulty_reducer.py); the repository layer must not own those counts and the frontend must not recompute them.
- [backend/app/domain/services/session_manager.py](backend/app/domain/services/session_manager.py) must call [backend/app/infrastructure/repositories/session_repository.py](backend/app/infrastructure/repositories/session_repository.py) for session lookup and connection-bound session end, and [backend/app/infrastructure/repositories/attempt_repository.py](backend/app/infrastructure/repositories/attempt_repository.py) for attempt insert, inside one transaction boundary per complete or abort call.
- [backend/app/infrastructure/repositories/attempt_repository.py](backend/app/infrastructure/repositories/attempt_repository.py) depends on the existing `sessions` and `subtasks` tables only through repository queries; it must not introduce new schema ownership or new table writes beyond `attempts`.
- [frontend/app/page.tsx](frontend/app/page.tsx) must remain the owner of `tasks`, `subjects`, `activeSession`, `activeInstruction`, `nextTask`, `isPending`, and `error`; [frontend/components/session-view.tsx](frontend/components/session-view.tsx) receives derived recommendation and session props only.
- [frontend/services/api.ts](frontend/services/api.ts) must remain the only frontend network surface used by [frontend/app/page.tsx](frontend/app/page.tsx); recommendation selection remains backend-owned and no direct backend access may move into [frontend/components/session-view.tsx](frontend/components/session-view.tsx).
- [frontend/components/session-view.tsx](frontend/components/session-view.tsx) must use subject metadata already derived in [frontend/app/page.tsx](frontend/app/page.tsx) rather than fetching subjects or matching ids itself.

# Migration / Schema Impact
- No schema migration, seed change, or DDL update is allowed in phase 3. The existing `attempts` table defined in [implementation-docs/devplan.md](implementation-docs/devplan.md) is used as-is.
- No API schema file changes are allowed because the approved phase 3 plan keeps the existing `TaskResponse`, `TaskStartResponse`, and `SessionResponse` contracts unchanged.
- No frontend type-file change is allowed because [frontend/types/study-buddy.ts](frontend/types/study-buddy.ts) already contains the `Task` shape needed for `GET /next` and the session and instruction shapes needed for the unchanged start and session-end responses.
- The only new persistence surface is the new repository file [backend/app/infrastructure/repositories/attempt_repository.py](backend/app/infrastructure/repositories/attempt_repository.py), and its queries must target existing `attempts`, `sessions`, and `subtasks` data without altering schema ownership.

# Test Surface Impact
- No existing backend test file can be modified because no backend test files exist in the current repository.
- No existing frontend test file can be modified because no frontend test files exist in the current repository.
- Later work will need new backend coverage for the task-start history read path, the transactional complete or abort attempt-write path, and `GET /next`, but this intention plan does not authorize any test-file path because the current repository has no approved test harness surface.
- Later work will need new frontend coverage for initial recommendation load, recommendation refresh after create and session resolution, recommendation clearing during an active session, and placeholder behavior on backend `404` from `/next`, but no exact frontend test file path can be contracted from the current tree.

# Risk Points
- Scope drift is the highest risk: the user request names [backend/app/main.py](backend/app/main.py), [backend/app/api/schemas/sessions.py](backend/app/api/schemas/sessions.py), and [frontend/types/study-buddy.ts](frontend/types/study-buddy.ts), but the approved phase 3 plan explicitly forbids editing those files. A coding agent must not widen the write surface to satisfy the request wording.
- Transaction drift is a core implementation risk: phase 3 fails if [backend/app/domain/services/session_manager.py](backend/app/domain/services/session_manager.py) ends the session through a separate committed connection before inserting the attempt.
- Boundary drift is a core backend risk: counting recent attempts must stay in [backend/app/domain/services/task_service.py](backend/app/domain/services/task_service.py), not in [backend/app/infrastructure/repositories/attempt_repository.py](backend/app/infrastructure/repositories/attempt_repository.py) and not in any route module.
- Query drift is a recommendation risk: [backend/app/infrastructure/repositories/task_repository.py](backend/app/infrastructure/repositories/task_repository.py) must implement exactly one latest-aborted-session-first query plus oldest-incomplete fallback and must not add hidden ranking heuristics.
- Frontend logic drift is a UI risk: [frontend/app/page.tsx](frontend/app/page.tsx) may derive subject display data for the recommendation, but it must not generate its own recommendation or difficulty rule when `GET /next` returns `404`.
- Component drift is a presentation risk: [frontend/components/session-view.tsx](frontend/components/session-view.tsx) must remain a presentational panel and must not become a second data-loading surface.