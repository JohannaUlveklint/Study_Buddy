# Phase
Phase 2

# Summary
Phase 2 adds subject retrieval and subtask-backed session creation to the existing single-page task flow. The implementation surface is narrow: add one backend subjects read path, persist one generated subtask during task start before creating the session, and extend the current frontend page so task creation and task rendering are subject-aware without moving business logic into React.

# Repository Reality Check
- Existing backend surface: The backend already exposes task creation, task listing, task start, session complete, and session abort through `backend/app/main.py`, `backend/app/api/routes/tasks.py`, and the existing services and repositories. `backend/app/api/routes/tasks.py` already delegates task start to `TaskService.start_task`, `backend/app/domain/services/task_service.py` already generates an instruction through the existing engines, `backend/app/infrastructure/repositories/task_repository.py` already persists `title` and `subject_id`, and `backend/app/infrastructure/repositories/session_repository.py` already accepts `subtask_id` when inserting a session. No subject route, subject schema, subject service, subject repository, or subtask repository exists yet.
- Existing frontend surface: The frontend is a single root page in `frontend/app/page.tsx` that owns all page state, calls the API client in `frontend/services/api.ts`, renders `frontend/components/task-form.tsx`, `frontend/components/task-list.tsx`, and `frontend/components/session-view.tsx`, and uses the shared types in `frontend/types/study-buddy.ts`. The API client already posts tasks and sessions through the backend, and task types already include `subject_id`, but there is no subject fetch, no subject selector, and no subject icon component.
- Existing tests: No backend or frontend product test files exist in the repository today. The repository contains implementation artifacts only, so phase 2 implementation will change production code without a pre-existing automated test harness in the current tree.
- Missing required surfaces: Phase 2 still needs a backend subjects read surface, a backend subtask persistence surface, transaction-capable task-start orchestration that writes the first subtask before the session row, frontend subject types and API methods, frontend subject selection on the existing page, and subject-aware task-card presentation on the existing task list.

# Files to Create
## backend/app/api/routes/subjects.py
- Why it must exist: Phase 2 requires a dedicated backend route for `GET /subjects`, and no subject route file exists in the current repository.
- Responsibility: Define the FastAPI subjects router and expose a read-only `GET /subjects` handler that returns the seeded subject rows through the service layer.
- Forbidden contents: No SQL, no subject write endpoints, no task logic, no session logic, no direct frontend formatting concerns, and no extra route surface beyond the single read endpoint required for phase 2.

## backend/app/api/schemas/subjects.py
- Why it must exist: The new subjects route needs an explicit response contract for the subject payload returned to the frontend.
- Responsibility: Own the API schema for a subject object containing the read fields required by phase 2: `id`, `name`, `color`, and `icon`.
- Forbidden contents: No task schemas, no session schemas, no request models for subject creation or editing, and no fields outside the four read-only subject properties used by this phase.

## backend/app/domain/services/subject_service.py
- Why it must exist: The subjects route needs a domain-layer entrypoint rather than reading from repositories directly in the route handler.
- Responsibility: Read subjects through the repository and return the stable subject list contract required by the frontend.
- Forbidden contents: No route wiring, no SQL, no seed logic, no subject writes, no task creation logic, and no session-start orchestration.

## backend/app/infrastructure/repositories/subject_repository.py
- Why it must exist: The backend has no current repository for reading the seeded subjects table.
- Responsibility: Read `id`, `name`, `color`, and `icon` from `subjects` in the required stable order for the API response.
- Forbidden contents: No inserts, updates, deletes, no task queries, no session queries, no subtask writes, and no response shaping beyond record serialization.

## backend/app/infrastructure/repositories/subtask_repository.py
- Why it must exist: The current backend has no persistence surface for writing the generated subtask before session creation.
- Responsibility: Insert exactly one subtask row for a started task using the generated instruction title and difficulty level, then return the inserted subtask record shape needed by the task-start flow.
- Forbidden contents: No session writes, no task reads, no transaction orchestration, no subtask completion updates, and no adaptive or history-driven logic.

## frontend/components/subject-icon.tsx
- Why it must exist: The frontend needs a single reusable display surface for the seeded subject icon names, and no subject icon component exists yet.
- Responsibility: Render the local icon treatment for the backend-provided subject icon strings used in this phase, including a neutral fallback for unknown icon values.
- Forbidden contents: No API calls, no page state, no task creation logic, no task-start logic, and no subject lookup against backend data sources.

# Files to Modify
## backend/app/main.py
- Why it must change: The new subjects router must be registered on the FastAPI app so `GET /subjects` becomes reachable.
- Exact scope of change: Add the subjects router import and include it alongside the existing task and session routers.
- Must remain untouched: Existing application title, existing CORS configuration, and existing registration of the task and session routes.

## backend/app/api/routes/tasks.py
- Why it must change: The task route wiring must construct `TaskService` with the new subtask persistence dependency while preserving the current task endpoints.
- Exact scope of change: Update dependency construction for `TaskService` so the existing `POST /tasks`, `GET /tasks`, and `POST /tasks/{task_id}/start` handlers can use the new task-start persistence path without changing their public route paths.
- Must remain untouched: Current route paths, current request validation behavior for blank titles, current error mapping for not found and duplicate open sessions, and the existing response-model contracts for task creation, task listing, and task start.

## backend/app/domain/services/task_service.py
- Why it must change: The current task-start flow generates an instruction and creates a session with `subtask_id=None`, which does not satisfy the phase 2 persistence contract.
- Exact scope of change: Extend the service constructor to accept the new subtask repository, keep `create_task` and `list_tasks` behavior intact, and change `start_task` so it loads the task, rejects duplicate open sessions, generates the instruction, persists one subtask, creates one session with the inserted subtask id, and returns the existing `session` plus `instruction` response shape.
- Must remain untouched: The existing task-not-found and open-session exception classes, the existing use of the subtask engine and difficulty reducer for instruction generation, and the public return shapes used by the route layer.

## backend/app/infrastructure/repositories/session_repository.py
- Why it must change: Phase 2 requires the session insert to participate in the same database transaction as the new subtask insert.
- Exact scope of change: Add a bounded repository path that can create a session row using an already-open database transaction or connection while preserving the current serialized session shape and existing read and end-session behavior.
- Must remain untouched: The current session serialization fields, the existing open-session lookup query intent, and the existing complete or abort update behavior.

## frontend/app/page.tsx
- Why it must change: The root page currently owns all state but only loads tasks; phase 2 requires it to also own subjects, selected subject state, and subject-aware task creation and rendering.
- Exact scope of change: Extend the page state and initial load flow to fetch subjects and tasks through the API client, store `selectedSubjectId`, submit `subject_id` during task creation, derive subject display data for the task list, and preserve the current active-session lifecycle on the same page.
- Must remain untouched: The single-page structure, the existing session complete or abort flow, the current error and pending state ownership at the page level, and the absence of direct database access from the frontend.

## frontend/app/globals.css
- Why it must change: The existing task card and form styling do not cover a subject selector, subject icon presentation, or subject-colored task-card treatment.
- Exact scope of change: Add only the styles needed for the new subject selector, subject icon component, subject metadata treatment, and the richer existing task-card layout on desktop and mobile.
- Must remain untouched: The established theme tokens, the overall single-page layout structure, and the current styling for areas unrelated to subject-aware form and task-list presentation.

## frontend/components/task-form.tsx
- Why it must change: The current form only captures a title and cannot emit the selected subject required by phase 2 task creation.
- Exact scope of change: Extend props so the form receives the fetched subject options and current selection from the page, renders a subject-selection control alongside the title input, and emits title and selected subject changes through callbacks without performing its own fetches.
- Must remain untouched: The component’s role as a presentational form, the page-owned submission flow, and the prohibition on backend or database logic inside the component.

## frontend/components/task-list.tsx
- Why it must change: The current task list renders only title and timestamp, while phase 2 requires subject name, icon, and color treatment on each task card.
- Exact scope of change: Extend props so the list receives subject display data from the page, render a subject-aware task card for each task, preserve the existing start action, and provide a neutral fallback presentation when the task has no matching subject.
- Must remain untouched: The component’s role as a presentational list, the existing start callback contract, and the prohibition on network requests or business logic inside the component.

## frontend/services/api.ts
- Why it must change: The frontend API client currently has no subject fetch method and task creation does not send `subject_id`.
- Exact scope of change: Add a `GET /subjects` client method and extend `createTask` so it sends `subject_id` in the existing backend request body while leaving the shared request helper and session methods intact.
- Must remain untouched: The backend-facing base URL behavior, the shared request error handling pattern, and the existing complete-session, abort-session, list-tasks, and start-task endpoint paths.

## frontend/types/study-buddy.ts
- Why it must change: The shared frontend types cover tasks, sessions, instructions, and task-start responses but do not yet define a subject payload.
- Exact scope of change: Add the subject type needed by `GET /subjects` and extend any existing frontend request or display types only as far as required for subject-aware page state and task rendering.
- Must remain untouched: The existing `Task`, `Session`, `Instruction`, and `TaskStartResponse` contracts except for narrowly compatible additions required by the new subject flow.

# Files Forbidden to Modify
- Every repository file not explicitly listed in the `Files to Create` or `Files to Modify` sections is forbidden to modify for phase 2.
- Within the approved phase 2 surface, no additional file creation or path expansion is allowed beyond the exact sixteen files listed above.

# Required Contracts Between Files
- `backend/app/api/routes/subjects.py` must call `backend/app/domain/services/subject_service.py`, and `backend/app/domain/services/subject_service.py` must call `backend/app/infrastructure/repositories/subject_repository.py`; the route must not read the database directly.
- `backend/app/api/schemas/subjects.py` defines the response shape returned by `backend/app/api/routes/subjects.py`; the repository may read database rows, but only the schema file owns the API contract fields exposed to the frontend.
- `backend/app/api/routes/tasks.py` must keep the existing task endpoints while wiring `backend/app/domain/services/task_service.py` with `backend/app/infrastructure/repositories/subtask_repository.py` and `backend/app/infrastructure/repositories/session_repository.py` for the start flow.
- `backend/app/domain/services/task_service.py` must keep instruction generation in the domain layer by calling the existing engines, persist the resulting instruction through `backend/app/infrastructure/repositories/subtask_repository.py`, and only then create the session through `backend/app/infrastructure/repositories/session_repository.py` with the inserted subtask id.
- The subtask insert and session insert must share one transaction boundary from the task-start flow so a failed session write cannot leave an orphaned subtask row behind.
- `frontend/services/api.ts` must remain the only frontend network surface used by `frontend/app/page.tsx`; `frontend/components/task-form.tsx`, `frontend/components/task-list.tsx`, and `frontend/components/subject-icon.tsx` must stay presentational.
- `frontend/app/page.tsx` must remain the owner of `tasks`, `subjects`, `selectedSubjectId`, `activeSession`, `activeInstruction`, `isPending`, and `error`; child components receive derived data and callbacks only.
- `frontend/types/study-buddy.ts` must remain the shared type source for `frontend/services/api.ts`, `frontend/app/page.tsx`, and the subject-aware UI components so the frontend uses one consistent subject payload contract.
- `frontend/app/page.tsx` must derive subject display state by matching each task’s `subject_id` against the fetched subject list; `frontend/components/task-list.tsx` must not perform backend subject lookup or own cross-record matching logic.

# Migration / Schema Impact
- No schema migration, seed update, or DDL change is part of phase 2; the required tables already exist.
- The new write path for `subtasks` must be `backend/app/domain/services/task_service.py` -> `backend/app/infrastructure/repositories/subtask_repository.py`, with one insert per successful `POST /tasks/{task_id}/start` execution.
- The new session linkage path must be `backend/app/domain/services/task_service.py` -> `backend/app/infrastructure/repositories/session_repository.py`, using the inserted subtask id as `sessions.subtask_id` during the same start-task transaction.
- `tasks.subject_id` continues to be written only through the existing task-creation path; phase 2 must not widen subject data storage onto task rows beyond the existing foreign key.
- `subjects` remains read-only in this phase, and `attempts` remains untouched.

# Test Surface Impact
- There are no existing product test files to modify, so phase 2 has only future test-addition impact.
- Later verification must add backend coverage for `GET /subjects`, `POST /tasks`, and `POST /tasks/{task_id}/start`, with explicit checks that a successful start writes one subtask row and one session row linked by `subtask_id`, and that a failed start does not leave an orphaned subtask row.
- Later verification must add frontend coverage for root-page subject loading, default subject selection, subject-aware task creation, neutral fallback rendering for tasks without a matching subject, and the unchanged active-session flow on the existing page.

# Risk Points
- Transaction drift is the highest-risk area: phase 2 fails its core contract if `backend/app/domain/services/task_service.py` creates the subtask and session through separate committed connections instead of one rollback-safe transaction.
- Surface drift in `backend/app/api/routes/tasks.py` is a risk if route changes alter the existing endpoint paths or response models instead of limiting the change to service wiring.
- Boundary drift in the frontend is a risk if subject matching, icon resolution, or request logic migrates out of `frontend/app/page.tsx` and `frontend/services/api.ts` into presentational components.
- Contract drift in `frontend/types/study-buddy.ts` and `frontend/services/api.ts` is a risk if the frontend starts expecting embedded subject objects on task rows instead of continuing to fetch subjects separately.
- Styling drift in `frontend/app/globals.css` is a risk if the phase adds broad visual rewrites rather than only the styles needed for subject selection and subject-aware task cards.