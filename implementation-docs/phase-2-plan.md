## Phase
Phase 2: Structure

## Phase Goal
Phase 2 adds the structural data needed to make tasks subject-aware and sessions subtask-backed without expanding the product flow: the backend exposes the seeded subjects through a dedicated route, the task-start flow persists the generated instruction into the subtasks table before creating the session, and the existing frontend page fetches subjects so task creation and task-card rendering show the correct subject color and icon.

## Scope
### Included
- Backend GET /subjects endpoint that returns the seeded subject rows for frontend consumption.
- Backend read access to the subjects table limited to id, name, color, and icon.
- Backend task-start persistence that inserts the generated instruction into the subtasks table.
- Backend session creation that stores the inserted subtask id on sessions.subtask_id.
- Transactional task-start flow so the subtask row and session row are created or rolled back together.
- Frontend subject fetch on the existing root page.
- Frontend task creation flow that sends a selected subject_id through POST /tasks.
- Frontend task-card rendering that shows the matched subject color and icon on the existing task list.
- Frontend task-list layout changes limited to a richer card presentation on the existing page.

### Excluded
- Filters, search, planning tools, and any secondary task-browsing controls.
- Any feature from phase 3 or later, including adaptive logic, GET /next, attempt tracking, and outcome history.
- New frontend pages, new frontend routes, or a separate subjects screen.
- Subject creation, subject editing, subject deletion, or any subject write API.
- Changes to the SubTaskEngine decision rules or DifficultyReducer behaviour.
- Direct frontend Supabase access, direct frontend PostgreSQL access, or frontend-owned business logic.
- Any change to the GET /tasks response shape that embeds full subject objects.
- Schema migrations, seed changes, or any write to the attempts table.

## Preconditions
- Phase 1 backend routes are present and verified: POST /tasks, GET /tasks, POST /tasks/{id}/start, POST /sessions/{id}/complete, and POST /sessions/{id}/abort.
- The Supabase PostgreSQL schema already contains the subjects, tasks, subtasks, sessions, and attempts tables defined in implementation-docs/devplan.md.
- The subjects table is already seeded with Math, English, Swedish, and Science, each with a color and icon value.
- backend/app/api/schemas/tasks.py already accepts subject_id on CreateTaskRequest.
- backend/app/domain/services/task_service.py currently starts a task by generating an instruction and creating a session with subtask_id set to null.
- frontend/app/page.tsx, frontend/components/task-form.tsx, and frontend/components/task-list.tsx already provide the single-page create/list/start flow from phase 1.
- frontend/services/api.ts currently provides the phase 1 task and session calls and requires extension for subject fetch and subject-aware task creation.

## Backend Design
### Routes
### List Subjects
- Method: GET
- Path: /subjects
- Request Shape: No request body.
- Response Shape: JSON array of subject objects containing id, name, color, and icon, ordered by name ascending.
- Error Conditions: 500 when the subject read fails.

### Create Task
- Method: POST
- Path: /tasks
- Request Shape: JSON body with title as a required non-empty string and subject_id as an optional UUID at the API contract level; the phase 2 frontend sends one selected seeded subject id.
- Response Shape: JSON object containing id, title, subject_id, created_at, and is_completed for the inserted task row.
- Error Conditions: 400 when title is missing or blank; 422 when subject_id is not a valid UUID; 500 when the database insert fails, including foreign-key rejection for a non-existent subject id.

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
- Response Shape: JSON object with session and instruction. Session contains id, task_id, subtask_id, started_at, ended_at, planned_duration_minutes, actual_duration_minutes, was_completed, and was_aborted. Instruction contains title and difficulty_level. On successful phase 2 execution, session.subtask_id is non-null and references the persisted subtask row created for this start action.
- Error Conditions: 404 when the task does not exist; 409 when the task already has an open session with ended_at unset; 500 when subtask persistence or session creation fails.

## Domain Logic
- SubjectService: retrieve the seeded subjects for GET /subjects and return only the fields required by the frontend.
- SubjectRepository: read subjects rows from the subjects table and impose the stable response order defined for phase 2.
- TaskService.create_task: continue delegating task insertion to TaskRepository and persist subject_id unchanged when present.
- TaskService.start_task: load the task, reject a duplicate open session, generate the instruction through SubTaskEngine, pass the instruction through DifficultyReducer, insert one subtask row, create one session row with the inserted subtask id, and return the persisted session together with the instruction.
- TaskService.start_task transaction rule: the subtask insert and the session insert execute inside one database transaction; if either write fails, neither row remains committed.
- SubtaskRepository: persist one subtask row using task_id from the started task, title from the generated instruction title, and difficulty_level from the generated instruction difficulty_level.
- SessionManager: keep the fixed planned duration of 10 minutes and create the session with the provided non-null subtask_id during the start flow.
- Task start decision rules remain phase 1 rules for instruction generation and phase 1 rules for duplicate open-session rejection.
- No subject matching logic, instruction generation logic, or fallback database logic moves into the frontend.

## Persistence
- subjects table: read id, name, color, and icon only; no inserts, updates, deletes, or seed changes.
- tasks table: continue inserting title and subject_id through POST /tasks; subject_id remains the only subject field stored on the task row.
- tasks table: continue listing id, title, subject_id, created_at, and is_completed through GET /tasks without joining subject objects into the response.
- subtasks table: insert one row when POST /tasks/{id}/start succeeds, with task_id set to the started task id, title set to the generated instruction title, difficulty_level set to the generated instruction difficulty_level, and is_completed left at the database default.
- sessions table: insert one row when POST /tasks/{id}/start succeeds, with task_id set to the started task id, subtask_id set to the inserted subtask id, planned_duration_minutes set to 10, and all remaining phase 1 session defaults preserved.
- sessions table: session.subtask_id must be non-null for sessions created in phase 2.
- attempts table: no reads and no writes.
- Database schema: no schema migration work is part of phase 2.

## Frontend Design
### Views
- Root page at / remains the only frontend view for this phase.
- The existing task creation panel gains a subject selector populated from GET /subjects.
- The existing task list remains on the root page and renders richer task cards that display subject identity through color and icon.
- The existing active-session panel remains on the root page with no new route and no new phase 2 workflow branch.

### Components
- Home page container in frontend/app/page.tsx: fetch the subject list and task list, hold the selected subject id, hold the existing session state, and derive the display data needed by TaskForm and TaskList.
- TaskForm: render the title input plus subject selection control, block submission when the title is blank or no subject options are available, and emit title plus selected subject id back to the page container.
- TaskList: render each task card with the matched subject name, subject color treatment, subject icon, creation timestamp, title, and start action without fetching data itself.
- SubjectIcon: render the local icon element for the seeded backend icon values calculator, book, language, and flask, plus a neutral fallback for any unmatched icon string.
- SessionView: remain phase 1 session UI and consume the updated session payload without adding new controls.

### State Flow
- frontend/app/page.tsx owns tasks, subjects, selectedSubjectId, activeSession, activeInstruction, pending state, and error state.
- On initial load, the page requests GET /subjects and GET /tasks through frontend/services/api.ts and stores both result sets locally.
- After subjects load, the page sets selectedSubjectId to the first returned subject id when no selection already exists.
- TaskForm receives the subject options and current selection from the page, then emits title and selected subject id through callbacks instead of issuing network requests itself.
- On task creation, the page calls POST /tasks with title and selectedSubjectId, clears the title after success, and refreshes the task list from the backend.
- TaskList receives task rows plus subject display data derived by the page from the fetched subject list; it does not perform subject lookup against the backend.
- For a task whose subject_id is null or has no matching subject row, the task card renders a neutral fallback presentation instead of failing to render.
- On task start, the page calls POST /tasks/{id}/start through the API client and stores the returned session and instruction exactly as returned by the backend.
- On session complete or abort, the page keeps the phase 1 flow: call the session endpoint, clear the active session state, and refresh the task list.
- No frontend file connects to Supabase, imports backend repositories, or performs instruction persistence.

## File-Level Impact
### Files to Create
- backend/app/api/routes/subjects.py
- backend/app/api/schemas/subjects.py
- backend/app/domain/services/subject_service.py
- backend/app/infrastructure/repositories/subject_repository.py
- backend/app/infrastructure/repositories/subtask_repository.py
- frontend/components/subject-icon.tsx

### Files to Modify
- backend/app/main.py
- backend/app/api/routes/tasks.py
- backend/app/domain/services/task_service.py
- backend/app/infrastructure/repositories/session_repository.py
- frontend/app/page.tsx
- frontend/app/globals.css
- frontend/components/task-form.tsx
- frontend/components/task-list.tsx
- frontend/services/api.ts
- frontend/types/study-buddy.ts

### Files Forbidden to Modify
- implementation-docs/devplan.md
- implementation-docs/current-phase.md
- implementation-docs/phase-1-plan.md
- implementation-docs/phase-1-intention-plan.md
- implementation-docs/phase-1-governance-audit.md
- implementation-docs/phase-1-test-report.md
- implementation-docs/phase-1-verification-report.md
- implementation-docs/templates/
- .github/
- backend/app/api/routes/sessions.py
- backend/app/api/schemas/sessions.py
- backend/app/domain/engines/subtask_engine.py
- backend/app/domain/engines/difficulty_reducer.py
- backend/app/domain/services/session_manager.py
- backend/app/infrastructure/db/connection.py
- backend/app/infrastructure/repositories/task_repository.py
- frontend/app/layout.tsx
- frontend/components/session-view.tsx
- Any file that introduces filters, search, planning tools, GET /next, adaptive logic, attempt tracking, or direct frontend database access

## Implementation Sequence
1. Create backend subject schema, repository, service, and route files that expose GET /subjects with the exact response contract defined in this plan.
2. Register the new subjects router in backend/app/main.py without changing the existing phase 1 route paths.
3. Create backend/app/infrastructure/repositories/subtask_repository.py with the single persistence operation required to insert one generated subtask row.
4. Extend backend/app/infrastructure/repositories/session_repository.py so the task-start flow can create the session row within the same database transaction used for subtask insertion.
5. Update backend/app/domain/services/task_service.py so POST /tasks/{id}/start performs task lookup, duplicate-open-session rejection, instruction generation, subtask persistence, and session creation in one transaction, then returns the persisted session plus instruction.
6. Update backend/app/api/routes/tasks.py so the task service wiring includes the new repository dependency while preserving the existing route paths and response models.
7. Extend frontend/types/study-buddy.ts with the subject payload type required by GET /subjects.
8. Extend frontend/services/api.ts with GET /subjects and update createTask so it sends subject_id in the POST /tasks request body.
9. Create frontend/components/subject-icon.tsx to render the seeded backend icon values without adding a new dependency.
10. Update frontend/app/page.tsx to load subjects and tasks on the existing page, store selectedSubjectId, submit subject-aware task creation, and pass subject display data into the form and list components.
11. Update frontend/components/task-form.tsx so the create flow includes subject selection from the fetched subject list.
12. Update frontend/components/task-list.tsx and frontend/app/globals.css so each task card renders the matched subject icon, color treatment, and richer layout on the existing page.
13. Verify the end-to-end flow by confirming that created tasks persist subject_id, GET /subjects feeds the frontend subject selector, and starting a task creates both a subtasks row and a session row whose subtask_id references that inserted subtask.

## Completion Criteria
1. GET /subjects exists and returns the seeded subjects as objects containing id, name, color, and icon through the FastAPI backend.
2. The frontend root page fetches subjects through the backend API client and does not use direct Supabase access.
3. Creating a task from the frontend sends a subject_id in POST /tasks and the persisted task row contains that same subject_id.
4. GET /tasks remains the task-list source and returns subject_id without embedding full subject objects.
5. Each rendered task card on the existing list UI displays the matching subject color and icon when a subject match exists.
6. A task with null subject_id or a missing subject match renders a neutral fallback card state instead of a broken UI.
7. Starting a task inserts exactly one subtask row whose title and difficulty_level match the returned instruction.
8. Starting a task inserts exactly one session row whose subtask_id references the inserted subtask row and is non-null.
9. If subtask insertion or session insertion fails during POST /tasks/{id}/start, the transaction leaves no orphaned subtask row.
10. No filters, search controls, planning tools, subject-creation UI, GET /next route, adaptive logic, or attempt tracking are added.

## Out-of-Scope Protection
- Do not add subject objects to the GET /tasks response; the frontend must continue to fetch subjects separately through GET /subjects.
- Do not add POST, PATCH, PUT, or DELETE routes for subjects.
- Do not add filters, search inputs, planning widgets, tabs, or extra task-browsing controls to the task list.
- Do not add GET /next, attempts writes, adaptive difficulty reads, or any history-based decision rule.
- Do not change the phase 1 instruction-generation rules in backend/app/domain/engines/subtask_engine.py.
- Do not move task-start orchestration, subject lookup against the database, or instruction persistence into React components.
- Do not create a new frontend page, new frontend route, modal flow, or dedicated subject management screen.
- Do not alter the database schema, alter the seeded subject rows, or widen writes into the attempts table.