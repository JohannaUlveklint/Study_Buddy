## Phase
Phase 5: Personalisation

## Phase Goal
Phase 5 personalises the existing start flow by replacing the fixed 10-minute session duration with a task-specific planned duration derived from recent session history and by making GET /next choose the next incomplete task with a deterministic priority order based on prior starts and aborts, while keeping all personalisation logic in the backend and leaving the existing frontend route structure, API client surface, and single-page UI intact.

## Scope
### Included
- Backend calculation of planned session duration from recent ended sessions for the same task.
- Backend persistence of actual session duration when a session is completed or aborted.
- Backend prioritisation of incomplete tasks for GET /next using task session history.
- Reuse of the existing POST /tasks/{task_id}/start, POST /sessions/{session_id}/complete, POST /sessions/{session_id}/abort, and GET /next routes with unchanged request and response shapes.
- Verification that the existing frontend already consumes planned_duration_minutes from the start-task response and already consumes GET /next without any client-side ranking logic.

### Excluded
- Social features, sharing, presence, collaboration, and any multi-user data.
- Settings pages, personalization controls, sliders, toggles, or per-user preferences.
- AI logic, heuristic text generation, embeddings, or any external recommendation service.
- New frontend pages, new frontend routes, new backend routes, and any direct database access from the frontend.
- Changes to subject behavior, subtask generation rules, difficulty reduction rules, or any feature from Phase 6.

## Preconditions
- Phase 4 artifacts already exist and Phase 5 is the active phase in implementation-docs/current-phase.md.
- The sessions table already contains planned_duration_minutes and actual_duration_minutes.
- The existing backend route surface already includes POST /tasks, GET /tasks, POST /tasks/{task_id}/start, GET /next, POST /sessions/{session_id}/complete, and POST /sessions/{session_id}/abort.
- backend/app/domain/services/task_service.py currently creates sessions with planned_duration_minutes set to 10 and already owns start-task orchestration.
- backend/app/domain/services/session_manager.py already ends sessions and records attempts for completed and aborted sessions.
- backend/app/api/schemas/tasks.py, backend/app/api/schemas/sessions.py, frontend/types/study-buddy.ts, and frontend/components/session-view.tsx already expose and consume planned_duration_minutes and actual_duration_minutes fields.
- frontend/app/page.tsx already hydrates nextTask from GET /next and activeSession from POST /tasks/{task_id}/start, so no frontend state model change is required for this phase.

## Backend Design
### Routes
#### Start Task
- Method: POST
- Path: /tasks/{task_id}/start
- Request Shape: Route parameter task_id as a task UUID string. No request body.
- Response Shape: Unchanged TaskStartResponse object with session and instruction. session contains id, task_id, subtask_id, started_at, ended_at, planned_duration_minutes, actual_duration_minutes, was_completed, and was_aborted. instruction contains title and difficulty_level.
- Error Conditions: 404 when the task does not exist. 409 when the task is already completed. 409 when the task already has an open session. 500 for any unhandled backend failure.
- Phase 5 Contract Change: session.planned_duration_minutes is no longer hardcoded to 10. It is the output of the duration-adjustment algorithm defined in this plan.

#### Get Next Task
- Method: GET
- Path: /next
- Request Shape: No request body.
- Response Shape: Unchanged TaskResponse object with id, title, subject_id, created_at, and is_completed.
- Error Conditions: 404 when no incomplete task exists. 500 for any unhandled backend failure.
- Phase 5 Contract Change: The returned task is selected by the task-prioritisation algorithm defined in this plan instead of the current repository ordering.

#### Complete Session
- Method: POST
- Path: /sessions/{session_id}/complete
- Request Shape: Route parameter session_id as a session UUID string. No request body.
- Response Shape: Unchanged SessionResponse object with id, task_id, subtask_id, started_at, ended_at, planned_duration_minutes, actual_duration_minutes, was_completed, and was_aborted.
- Error Conditions: 404 when the session does not exist. 409 when the session is already ended. 500 for any unhandled backend failure.
- Phase 5 Contract Change: actual_duration_minutes is populated on success with the stored integer duration for the ended session.

#### Abort Session
- Method: POST
- Path: /sessions/{session_id}/abort
- Request Shape: Route parameter session_id as a session UUID string. No request body.
- Response Shape: Unchanged SessionResponse object with id, task_id, subtask_id, started_at, ended_at, planned_duration_minutes, actual_duration_minutes, was_completed, and was_aborted.
- Error Conditions: 404 when the session does not exist. 409 when the session is already ended. 500 for any unhandled backend failure.
- Phase 5 Contract Change: actual_duration_minutes is populated on success with the stored integer duration for the ended session.

### Domain Logic
- backend/app/domain/engines/personalization_engine.py: add one backend-only engine file that contains the exact duration-adjustment and task-priority rules for this phase. No frontend file contains these rules.
- Duration adjustment input set: the engine receives the last five ended sessions for the same task where actual_duration_minutes is not null, ordered by ended_at descending.
- Duration adjustment default: when fewer than two qualifying historical sessions exist for the task, planned_duration_minutes is 10.
- Duration adjustment formula: when at least two qualifying historical sessions exist, compute the arithmetic mean of actual_duration_minutes across those sessions, convert it to an integer with half-up rounding using floor(average + 0.5), then clamp the result to a minimum of 5 and a maximum of 30.
- Duration adjustment source rows: include both completed and aborted ended sessions. Aborted sessions remain in the sample because they represent the actual amount of time the user sustained that task.
- TaskService responsibility: start_task fetches the task, validates task state, fetches recent attempts for difficulty reduction exactly as Phase 3 already does, fetches recent session-duration history for the same task, calls the duration-adjustment engine, creates the subtask, and creates the session with the personalised planned_duration_minutes.
- Actual duration write rule: SessionManager complete_session and abort_session both end the session inside the existing transaction and store actual_duration_minutes as the session length in whole minutes using GREATEST(1, CEILING(elapsed_seconds / 60.0)), where elapsed_seconds is the difference between the database end timestamp and started_at.
- Task prioritisation candidate set: GET /next evaluates every task where is_completed is false.
- Task prioritisation summary data per candidate: latest ended session timestamp, latest ended session aborted flag, latest session started_at timestamp, count of ended aborted sessions, and a boolean that marks whether the task has any session history.
- Task prioritisation rank group 0: tasks whose latest ended session exists and was_aborted is true.
- Task prioritisation rank group 1: tasks with session history but not in rank group 0.
- Task prioritisation rank group 2: tasks with no session history.
- Task prioritisation ordering inside rank group 0: latest ended session timestamp descending, then abort count descending, then task created_at ascending.
- Task prioritisation ordering inside rank group 1: latest session started_at descending, then task created_at ascending.
- Task prioritisation ordering inside rank group 2: task created_at ascending.
- Task prioritisation output: TaskService returns the single highest-ranked incomplete task. No tie-breaking logic exists outside the declared ordering keys.
- Difficulty reduction remains unchanged. Subtask generation remains unchanged. Phase 5 adds personalisation only through planned duration and next-task selection.

### Persistence
- sessions.planned_duration_minutes: keep the existing column and start writing the personalised planned duration selected by the duration-adjustment algorithm instead of the constant 10.
- sessions.actual_duration_minutes: keep the existing column and write a non-null integer when a session is completed or aborted.
- sessions read requirements for duration adjustment: fetch up to five rows for the same task where ended_at is not null and actual_duration_minutes is not null, ordered by ended_at descending.
- sessions read requirements for prioritisation: fetch per-task session summary fields required for the rank-group and ordering rules defined in this plan.
- tasks read requirements for prioritisation: fetch id, title, subject_id, created_at, and is_completed for incomplete tasks only.
- attempts table: no schema change and no write-path change beyond the existing completed and aborted attempt inserts.
- subtasks table: no schema change and no write-path change.
- Database schema changes: none.
- Database migrations: none.
- New tables, new columns, new indexes, and seed changes are forbidden in this phase.

## Frontend Design
### Views
- The existing root page at frontend/app/page.tsx remains the only view involved in this phase.
- The active session panel in frontend/components/session-view.tsx already renders session.planned_duration_minutes, so the adjusted duration becomes visible through the existing UI with no copy change, layout change, or new control.
- The recommended task panel and task list already consume the task returned by GET /next, so prioritised task selection becomes visible through the existing UI with no new frontend behavior.

### Components
- frontend/app/page.tsx: no code change. It continues to call getNextTask on load and after session resolution, and it continues to store the start-task response session in activeSession.
- frontend/components/session-view.tsx: no code change. It continues to display planned_duration_minutes from the session payload.
- frontend/services/api.ts: no code change. Existing route methods and request shapes remain valid.
- frontend/types/study-buddy.ts: no code change. The existing Session type already contains planned_duration_minutes and actual_duration_minutes.

### State Flow
- Frontend state ownership remains unchanged in frontend/app/page.tsx.
- POST /tasks/{task_id}/start returns a session whose planned_duration_minutes already contains the backend-selected personalised value. The page stores that session without any client-side calculation.
- GET /next returns the backend-selected prioritised task. The page stores that task in nextTask without any client-side sorting or fallback ranking.
- POST /sessions/{session_id}/complete and POST /sessions/{session_id}/abort continue to return Session objects. The frontend does not add any personalisation logic after those calls; it only refreshes tasks and nextTask through the existing flow.
- No state, cache, local storage, cookie, or query parameter is added for Phase 5.

## File-Level Impact
### Files to Create
- backend/app/domain/engines/personalization_engine.py

### Files to Modify
- backend/app/domain/services/task_service.py
- backend/app/domain/services/session_manager.py
- backend/app/infrastructure/repositories/task_repository.py
- backend/app/infrastructure/repositories/session_repository.py

### Files Forbidden to Modify
- backend/app/main.py
- backend/app/api/routes/**
- backend/app/api/schemas/**
- backend/app/domain/engines/difficulty_reducer.py
- backend/app/domain/engines/subtask_engine.py
- backend/app/infrastructure/repositories/attempt_repository.py
- backend/app/infrastructure/repositories/subtask_repository.py
- frontend/**
- implementation-docs/devplan.md
- implementation-docs/current-phase.md

## Implementation Sequence
1. Create backend/app/domain/engines/personalization_engine.py with one duration function and one priority function that encode the exact formulas and ordering rules from this plan.
2. Modify backend/app/infrastructure/repositories/session_repository.py to expose one query for recent ended session durations by task and to update end_session_tx so it writes actual_duration_minutes at the same time it writes ended_at, was_completed, and was_aborted.
3. Modify backend/app/infrastructure/repositories/task_repository.py to expose candidate data for all incomplete tasks, including the per-task session summary fields required by the priority engine.
4. Modify backend/app/domain/services/task_service.py so get_next_task pulls candidate rows from the repository and selects the first task by calling the priority engine instead of relying on repository-only ordering.
5. Modify backend/app/domain/services/task_service.py so start_task fetches recent session-duration history, computes planned_duration_minutes through the personalization engine, and passes that value into session creation.
6. Modify backend/app/domain/services/session_manager.py so complete_session and abort_session persist actual_duration_minutes through the repository transaction while keeping the existing attempt write behavior and task-completion behavior intact.
7. Run backend validation for the modified files and confirm that the frontend file set remains unchanged because the existing UI already consumes the unchanged route contracts.
8. Verify that no new route, schema, page, component, migration, or dependency was added and that the only new file is backend/app/domain/engines/personalization_engine.py.

## Completion Criteria
1. POST /tasks/{task_id}/start returns TaskStartResponse with session.planned_duration_minutes equal to 10 when the task has fewer than two ended sessions with non-null actual_duration_minutes.
2. POST /tasks/{task_id}/start returns TaskStartResponse with session.planned_duration_minutes equal to the half-up rounded average of the last five qualifying actual_duration_minutes values, clamped to the range 5 through 30, when at least two qualifying ended sessions exist for that task.
3. POST /sessions/{session_id}/complete writes ended_at, writes was_completed as true, writes was_aborted as false, writes actual_duration_minutes as an integer greater than or equal to 1, and still records a completed attempt and marks the task completed.
4. POST /sessions/{session_id}/abort writes ended_at, writes was_completed as false, writes was_aborted as true, writes actual_duration_minutes as an integer greater than or equal to 1, and still records an aborted attempt.
5. GET /next returns the highest-ranked incomplete task according to these exact groups and ordering rules: latest-ended-aborted first, other started tasks second, never-started tasks last; group-internal order follows the exact timestamp and count rules from this plan.
6. GET /next response shape remains unchanged and frontend/services/api.ts requires no modification.
7. frontend/app/page.tsx, frontend/components/session-view.tsx, frontend/services/api.ts, and frontend/types/study-buddy.ts remain byte-for-byte unchanged for Phase 5.
8. No database migration file, schema change, seed change, new route, new page, new component, or new dependency exists in the Phase 5 implementation.

## Out-of-Scope Protection
- Do not add settings for preferred session length, manual task ranking, or any user-editable personalization control.
- Do not add analytics, streaks, dashboards, progress charts, or history views to explain the personalised values.
- Do not add new API endpoints such as /preferences, /recommendations, /sessions/history, or /tasks/priorities. Phase 5 uses the existing route surface only.
- Do not move priority selection or duration calculation into frontend/app/page.tsx, frontend/services/api.ts, or any other frontend file.
- Do not change difficulty reduction thresholds, subtask templates, subject behavior, or task completion rules.
- Do not add schema objects, migrations, or indexes. Phase 5 uses the existing tables and columns only.
- Do not widen the file surface beyond the four modified backend files and the one new backend engine file listed in this plan.