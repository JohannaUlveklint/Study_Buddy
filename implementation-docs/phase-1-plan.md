## Phase
Phase 1: Core Start Flow

## Phase Goal
Phase 1 delivers the smallest end-to-end path that lets a user create a task, start that task, receive exactly one generated instruction, and then complete or abort the resulting session while all task and session records persist through the FastAPI backend into the existing Supabase PostgreSQL schema.

## Scope
### Included
- FastAPI application entrypoint for phase 1 backend routes.
- Reusable PostgreSQL connection helper built from the existing backend connection module.
- Task creation through POST /tasks with title-only input.
- Task retrieval through GET /tasks for rendering the phase 1 task list.
- Static subtask generation based on task title.
- Static difficulty reduction that returns the generated instruction unchanged.
- Session creation through POST /tasks/{id}/start with a fixed planned duration of 10 minutes.
- Session completion through POST /sessions/{id}/complete.
- Session abortion through POST /sessions/{id}/abort.
- Next.js App Router frontend with one dark-themed page for task creation, task listing, and the active session view.
- Frontend API client that talks only to the FastAPI backend at http://localhost:8000.

### Excluded
- Subject creation, subject selection, subject colors, and subject icons in the UI.
- Direct frontend access to Supabase or PostgreSQL.
- Adaptive difficulty logic, attempt tracking, and any behaviour that reads prior outcomes.
- GET /next and any other route not listed in phase 1 API scope.
- Task update routes, task delete routes, task completion rules, and any broader task management workflow.
- Subtask table persistence and any write to the subtasks table.
- Analytics, dashboards, timers, streaks, progress charts, and notifications.
- AI features, recommendation features, and personalisation features.
- Mobile polish and UX refinement work assigned to later phases.

## Preconditions
- implementation-docs/devplan.md remains the governing specification for phase 1 scope and route set.
- backend/app/infrastructure/db/connection.py remains the shared database entrypoint and is the only existing backend persistence file.
- A Supabase PostgreSQL database exists with the subjects, tasks, subtasks, sessions, and attempts tables defined in implementation-docs/devplan.md.
- The database connection string is available to the backend through DATABASE_URL.
- No prior phase artifacts exist, so phase 1 implementation does not depend on any earlier phase plan or intention artifact.

## Backend Design
### Routes
### Create Task
- Method: POST
- Path: /tasks
- Request Shape: JSON body with one required field, title, as a non-empty string.
- Response Shape: JSON object containing id, title, subject_id, created_at, and is_completed for the inserted task row.
- Error Conditions: 400 when title is missing or blank; 500 when database insertion fails.

### List Tasks
- Method: GET
- Path: /tasks
- Request Shape: No request body.
- Response Shape: JSON array of task objects containing id, title, subject_id, created_at, and is_completed, ordered by newest created_at first.
- Error Conditions: 500 when task retrieval fails.

### Start Task
- Method: POST
- Path: /tasks/{id}/start
- Request Shape: Route parameter id as a task UUID; no request body.
- Response Shape: JSON object with two top-level fields: session and instruction. Session contains id, task_id, subtask_id, started_at, ended_at, planned_duration_minutes, actual_duration_minutes, was_completed, and was_aborted. Instruction contains title and difficulty_level for the generated phase 1 instruction.
- Error Conditions: 404 when the task does not exist; 409 when the task already has an open session with ended_at unset; 500 when instruction generation or session creation fails.

### Complete Session
- Method: POST
- Path: /sessions/{id}/complete
- Request Shape: Route parameter id as a session UUID; no request body.
- Response Shape: JSON object containing the updated session row with ended_at set, was_completed set to true, and was_aborted set to false.
- Error Conditions: 404 when the session does not exist; 409 when the session is already ended; 500 when the update fails.

### Abort Session
- Method: POST
- Path: /sessions/{id}/abort
- Request Shape: Route parameter id as a session UUID; no request body.
- Response Shape: JSON object containing the updated session row with ended_at set, was_completed set to false, and was_aborted set to true.
- Error Conditions: 404 when the session does not exist; 409 when the session is already ended; 500 when the update fails.

### Domain Logic
- SubTaskEngine: Accept the task title, convert it to the deterministic phase 1 instruction, and emit only one instruction object with a title and difficulty level.
- SubTaskEngine decision rules: titles containing write map to Write 3 sentences at difficulty level 1; titles containing read map to Read 1 page at difficulty level 1; titles containing math map to Solve 2 problems at difficulty level 1; all other titles map to Work for 5 minutes at difficulty level 1.
- DifficultyReducer: Receive the generated instruction and return it unchanged in phase 1.
- TaskService: Validate task existence for the start flow, call SubTaskEngine, pass the result through DifficultyReducer, and delegate session creation to SessionManager.
- SessionManager: Create a session with fixed planned_duration_minutes equal to 10, close a session on complete or abort, and reject state transitions when the session is already ended.
- Route handlers: perform request validation, call services, and translate domain and persistence failures into the defined HTTP errors only.

### Persistence
- tasks table: insert one row per created task with title populated from the request, subject_id left null in phase 1, created_at using the database default, and is_completed left false.
- tasks table: read rows for GET /tasks without introducing subject joins or task filtering logic beyond descending creation order.
- sessions table: insert one row when a task starts with task_id set, subtask_id set to null, planned_duration_minutes set to 10, started_at using the database default, ended_at null, actual_duration_minutes null, was_completed false, and was_aborted false.
- sessions table: update one existing row on complete by setting ended_at to the current timestamp, was_completed to true, and was_aborted to false.
- sessions table: update one existing row on abort by setting ended_at to the current timestamp, was_completed to false, and was_aborted to true.
- subtasks table: no reads and no writes in phase 1.
- subjects table: no reads and no writes in phase 1.
- attempts table: no reads and no writes in phase 1.
- Database schema: no schema migration work is part of phase 1 implementation in this repository; phase 1 consumes the schema defined in implementation-docs/devplan.md.

## Frontend Design
### Views
- Root start-flow view at / that contains the task form, the task list, and the active session panel within one dark-themed page.
- No secondary routes, modal flows, subject views, analytics views, or dashboard views.

### Components
- TaskForm: capture a task title, submit it to the backend, clear the input after a successful create, and surface create failures to the page state.
- TaskList: render the fetched tasks and expose one start action per task when no session is active.
- SessionView: render the single active instruction and expose complete and abort actions for the active session.
- Page container in frontend/app/page.tsx: own the application state, coordinate API calls, and switch the primary action area from task-start actions to the active session action set.
- Layout and styling files: apply the dark visual system and page structure required for the phase 1 core start flow.

### State Flow
- frontend/app/page.tsx owns the task collection, the active session object, the active instruction object, loading state, and error state.
- On initial page load, the page requests GET /tasks through frontend/services/api.ts and stores the returned tasks locally.
- TaskForm emits a create action to the page; the page calls POST /tasks; after success, the page refreshes the task list from the backend and clears any stale session error.
- TaskList emits a start action to the page; the page calls POST /tasks/{id}/start; after success, the page stores the returned session and instruction as the only active action context.
- While an active session exists, the page keeps the session view as the primary interaction and withholds additional start actions until the session resolves.
- SessionView emits complete or abort actions to the page; the page calls the matching session endpoint; after success, the page clears the active session state and refreshes the task list.
- No component generates instructions locally, computes difficulty locally, or talks to the database directly.

## File-Level Impact
### Files to Create
- backend/requirements.txt
- backend/app/main.py
- backend/app/api/__init__.py
- backend/app/api/routes/__init__.py
- backend/app/api/routes/tasks.py
- backend/app/api/routes/sessions.py
- backend/app/api/schemas/__init__.py
- backend/app/api/schemas/tasks.py
- backend/app/api/schemas/sessions.py
- backend/app/domain/__init__.py
- backend/app/domain/engines/__init__.py
- backend/app/domain/engines/subtask_engine.py
- backend/app/domain/engines/difficulty_reducer.py
- backend/app/domain/services/__init__.py
- backend/app/domain/services/task_service.py
- backend/app/domain/services/session_manager.py
- backend/app/infrastructure/repositories/__init__.py
- backend/app/infrastructure/repositories/task_repository.py
- backend/app/infrastructure/repositories/session_repository.py
- frontend/package.json
- frontend/tsconfig.json
- frontend/next-env.d.ts
- frontend/next.config.ts
- frontend/app/layout.tsx
- frontend/app/page.tsx
- frontend/app/globals.css
- frontend/components/task-form.tsx
- frontend/components/task-list.tsx
- frontend/components/session-view.tsx
- frontend/services/api.ts
- frontend/types/study-buddy.ts

### Files to Modify
- backend/app/infrastructure/db/connection.py

### Files Forbidden to Modify
- implementation-docs/devplan.md
- implementation-docs/templates/
- .github/
- Any file whose purpose is analytics, AI, dashboards, subjects UI, adaptive logic, or future-phase personalisation
- Any frontend file that introduces direct Supabase access, direct PostgreSQL access, or business logic outside the page state and backend API boundary

## Implementation Sequence
1. Create the backend dependency manifest and the missing backend package directories and files defined for phase 1.
2. Complete backend/app/infrastructure/db/connection.py so it provides the shared asynchronous database connection path used by repositories and fails fast on missing DATABASE_URL.
3. Create backend API schema modules that define the request and response contracts for task creation, task listing, task start, session completion, and session abortion.
4. Create repository modules for task reads and writes and for session reads and writes against the existing tasks and sessions tables only.
5. Create SubTaskEngine and DifficultyReducer with the exact phase 1 decision rules and no adaptive behaviour.
6. Create SessionManager and TaskService so the task-start flow validates the task, rejects duplicate open sessions for the same task, generates one instruction, and creates the session row with subtask_id set to null.
7. Create the FastAPI route modules and backend/app/main.py, wire the five phase 1 routes, and keep route handlers free of hidden business logic.
8. Create the frontend Next.js scaffold files required to run an App Router TypeScript application inside frontend/.
9. Create frontend/services/api.ts with the five phase 1 backend calls and no direct database integration.
10. Create the page, layout, styles, and phase 1 components so the root page renders the dark layout, task form, task list, and active session view.
11. Wire the frontend state flow so task creation refreshes the list, task start activates exactly one instruction view, and session completion or abortion clears the active session and refreshes tasks.
12. Run the application end to end against the configured database and verify that task rows and session rows persist with the phase 1 field behaviour defined in this plan.

## Completion Criteria
1. A user can load the frontend root page, create a task with a non-empty title, and see that task appear in the rendered task list after the backend write succeeds.
2. GET /tasks returns persisted task rows with the fields defined in this plan and without subject expansion logic.
3. Starting a task creates exactly one new session row, returns exactly one instruction object, and the frontend presents that instruction as the only active session action.
4. Completing a session updates the matching session row so ended_at is set, was_completed is true, and was_aborted is false.
5. Aborting a session updates the matching session row so ended_at is set, was_completed is false, and was_aborted is true.
6. No phase 1 route writes to subtasks, subjects, or attempts.
7. No frontend code imports Supabase clients, database drivers, or backend-only domain logic.
8. The implemented route surface is limited to POST /tasks, GET /tasks, POST /tasks/{id}/start, POST /sessions/{id}/complete, and POST /sessions/{id}/abort.
9. The UI contains the dark layout, task form, task list, and session view, and it does not contain subjects UI, analytics, dashboard panels, or AI features.

## Out-of-Scope Protection
- Do not add subject selectors, subject badges, or subject color rendering anywhere in phase 1.
- Do not persist generated instructions into the subtasks table in phase 1.
- Do not add GET /next, attempt logging, adaptive difficulty, or any read of prior completions or aborts.
- Do not add task delete, task edit, or task completion routes to fill the gap implied by the word CRUD in the devplan.
- Do not add timers, duration tracking UI, analytics summaries, dashboards, or notification features.
- Do not add AI calls, recommendation logic, or personalisation logic.
- Do not move business rules into React components or API route handlers.
- Do not connect the frontend directly to Supabase, PostgreSQL, or any backend repository module.