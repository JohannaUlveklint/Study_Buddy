# Phase
Phase 1

# Summary
Phase 1 adds the minimum real implementation surface required to deliver the core start flow described in the approved plan: a FastAPI backend that can create and list tasks, start one task into a session, and complete or abort that session; plus a new Next.js frontend that consumes only those backend routes. In the current repository, this phase is grounded on one existing backend persistence file, an otherwise empty backend package shell, and no existing frontend or test implementation surface.

# Repository Reality Check
- Existing backend surface: `backend/app/__init__.py` exists and is empty. `backend/app/infrastructure/db/connection.py` exists and currently exposes a direct `asyncpg.connect(DATABASE_URL)` helper after loading `.env`. No FastAPI entrypoint, route modules, schema modules, domain modules, repository modules, dependency manifest, or tests currently exist under `backend/`.
- Existing frontend surface: No `frontend/` directory exists. There is no Next.js application, no component files, no frontend service layer, and no frontend types.
- Existing tests: No backend or frontend test directories or test files exist in the repository.
- Missing required surfaces: The repository is missing every phase 1 backend application file described in the approved plan except the DB connection helper, and it is missing the entire phase 1 frontend surface.

# Files to Create
## `backend/requirements.txt`
- Why it must exist: The backend currently has no dependency manifest, and phase 1 requires a runnable FastAPI application with PostgreSQL connectivity.
- Responsibility: Declare the backend runtime packages required for the phase 1 API only.
- Forbidden contents: No frontend dependencies, no test-only tooling, no future-phase packages, and no AI-related packages.

## `backend/app/main.py`
- Why it must exist: The backend needs a single FastAPI application entrypoint for the phase 1 route surface.
- Responsibility: Construct the application instance and register only the phase 1 task and session route modules.
- Forbidden contents: No embedded business logic, no direct SQL, no future-phase routes, and no background-job orchestration.

## `backend/app/api/__init__.py`
- Why it must exist: The repository currently has no API package surface.
- Responsibility: Mark the API package so the route and schema modules live under a concrete import path.
- Forbidden contents: No route logic, no schema definitions, and no runtime side effects.

## `backend/app/api/routes/__init__.py`
- Why it must exist: The route modules need a concrete package boundary.
- Responsibility: Mark the routes package only.
- Forbidden contents: No route handlers, no imports with side effects, and no business rules.

## `backend/app/api/routes/tasks.py`
- Why it must exist: Phase 1 requires `POST /tasks`, `GET /tasks`, and `POST /tasks/{id}/start`.
- Responsibility: Define only the task-related HTTP handlers and translate service outcomes into the approved HTTP responses.
- Forbidden contents: No direct database access, no instruction-generation logic inside handlers, and no routes outside the three approved task endpoints.

## `backend/app/api/routes/sessions.py`
- Why it must exist: Phase 1 requires `POST /sessions/{id}/complete` and `POST /sessions/{id}/abort`.
- Responsibility: Define only the session state-transition HTTP handlers and map service errors to the approved HTTP responses.
- Forbidden contents: No direct SQL, no task-start logic, and no additional session routes.

## `backend/app/api/schemas/__init__.py`
- Why it must exist: The backend needs a concrete schema package for request and response contracts.
- Responsibility: Mark the schemas package only.
- Forbidden contents: No validation logic outside schema definitions and no route wiring.

## `backend/app/api/schemas/tasks.py`
- Why it must exist: The task endpoints need explicit phase 1 request and response models.
- Responsibility: Define the task create, task list item, and task start response shapes used by the task route module.
- Forbidden contents: No database code, no service orchestration, and no schemas for future-phase routes.

## `backend/app/api/schemas/sessions.py`
- Why it must exist: The session endpoints need explicit phase 1 response models.
- Responsibility: Define the complete and abort session response shapes used by the session route module.
- Forbidden contents: No route handlers, no SQL, and no attempt-tracking schemas.

## `backend/app/domain/__init__.py`
- Why it must exist: The backend currently has no domain package surface.
- Responsibility: Mark the domain package only.
- Forbidden contents: No business logic implementation and no import side effects.

## `backend/app/domain/engines/__init__.py`
- Why it must exist: The deterministic instruction logic needs a concrete package boundary.
- Responsibility: Mark the engines package only.
- Forbidden contents: No engine logic and no service orchestration.

## `backend/app/domain/engines/subtask_engine.py`
- Why it must exist: Phase 1 requires deterministic instruction generation from the task title.
- Responsibility: Own the exact title-to-instruction mapping defined in the approved phase plan.
- Forbidden contents: No database access, no adaptive history reads, and no persistence to the `subtasks` table.

## `backend/app/domain/engines/difficulty_reducer.py`
- Why it must exist: The phase plan requires a phase-aware reducer even though phase 1 returns the instruction unchanged.
- Responsibility: Receive the generated instruction and return it unchanged in phase 1.
- Forbidden contents: No adaptive logic, no attempt analysis, and no database reads.

## `backend/app/domain/services/__init__.py`
- Why it must exist: The backend currently has no service package surface.
- Responsibility: Mark the services package only.
- Forbidden contents: No service logic and no route registration.

## `backend/app/domain/services/task_service.py`
- Why it must exist: The start flow needs a bounded service layer between routes, engines, and repositories.
- Responsibility: Validate task existence for the start flow, generate one instruction, apply the reducer, and coordinate session creation.
- Forbidden contents: No HTTP concerns, no direct SQL, and no future-phase recommendation logic.

## `backend/app/domain/services/session_manager.py`
- Why it must exist: Session creation, completion, and abortion need a dedicated domain boundary.
- Responsibility: Create a session with the fixed planned duration and enforce the allowed end-state transitions.
- Forbidden contents: No route logic, no instruction-generation logic, and no writes to tables other than `sessions`.

## `backend/app/infrastructure/repositories/__init__.py`
- Why it must exist: The backend currently has no repository package surface.
- Responsibility: Mark the repositories package only.
- Forbidden contents: No SQL execution outside repository modules and no business-rule branching.

## `backend/app/infrastructure/repositories/task_repository.py`
- Why it must exist: Phase 1 task creation, retrieval, and start-flow task lookup require a dedicated persistence module.
- Responsibility: Own task-table reads and writes needed for `POST /tasks`, `GET /tasks`, and task existence lookup for start.
- Forbidden contents: No session writes, no joins to subjects, and no broader task-management features.

## `backend/app/infrastructure/repositories/session_repository.py`
- Why it must exist: Phase 1 session creation and terminal state updates require a dedicated persistence module.
- Responsibility: Own session-table insert, open-session lookup, and complete/abort updates for the approved phase 1 fields only.
- Forbidden contents: No writes to `attempts`, no writes to `subtasks`, and no analytics queries.

## `frontend/package.json`
- Why it must exist: The repository currently has no frontend project definition.
- Responsibility: Declare the frontend runtime and build scripts required for a Next.js App Router TypeScript application for phase 1.
- Forbidden contents: No database drivers, no Supabase client, and no unrelated UI or analytics packages.

## `frontend/tsconfig.json`
- Why it must exist: The new TypeScript frontend requires an explicit compiler configuration.
- Responsibility: Configure TypeScript for the phase 1 Next.js application only.
- Forbidden contents: No path aliases that imply broader architecture and no settings tied to future phases.

## `frontend/next-env.d.ts`
- Why it must exist: A TypeScript Next.js app requires the environment type declaration file.
- Responsibility: Provide the standard Next.js type environment surface.
- Forbidden contents: No app logic and no custom business types.

## `frontend/next.config.ts`
- Why it must exist: The new frontend application needs a concrete Next.js configuration file.
- Responsibility: Hold only the minimal framework configuration required to run the phase 1 app.
- Forbidden contents: No backend proxy business logic and no future deployment-specific complexity.

## `frontend/app/layout.tsx`
- Why it must exist: The App Router requires a root layout file.
- Responsibility: Provide the outer document shell and apply the global styling entrypoint.
- Forbidden contents: No page-specific business logic and no data-fetching workflows.

## `frontend/app/page.tsx`
- Why it must exist: Phase 1 needs a single root page for task creation, task listing, and the active session view.
- Responsibility: Own the page-level state and coordinate calls into the frontend API service for the approved phase 1 flow.
- Forbidden contents: No direct database access, no instruction-generation logic, and no multi-page routing concerns.

## `frontend/app/globals.css`
- Why it must exist: The frontend requires global styling for the dark phase 1 interface.
- Responsibility: Define the global visual system and page-level layout styling for the single-page flow.
- Forbidden contents: No component business logic and no styles for future-phase dashboards or analytics views.

## `frontend/components/task-form.tsx`
- Why it must exist: The root page needs a dedicated task input surface.
- Responsibility: Render the title input and emit create requests upward to the page state.
- Forbidden contents: No direct API calls if the page is the chosen coordinator, no backend logic, and no subject-selection UI.

## `frontend/components/task-list.tsx`
- Why it must exist: The root page needs a reusable task list view.
- Responsibility: Render persisted tasks and expose one start action per task while no session is active.
- Forbidden contents: No direct data fetching, no session-completion logic, and no analytics summaries.

## `frontend/components/session-view.tsx`
- Why it must exist: The root page needs a dedicated active-session interaction surface.
- Responsibility: Render the single current instruction and expose complete and abort actions upward to the page state.
- Forbidden contents: No timer engine, no adaptive difficulty logic, and no persistence code.

## `frontend/services/api.ts`
- Why it must exist: The frontend needs a single backend API boundary.
- Responsibility: Own the five phase 1 HTTP calls to the FastAPI backend and define no other network contract.
- Forbidden contents: No direct Supabase usage, no database drivers, and no frontend business-rule branching.

## `frontend/types/study-buddy.ts`
- Why it must exist: The new frontend needs a shared local type surface for task, session, and instruction payloads.
- Responsibility: Define the TypeScript shapes that mirror the approved backend API responses used in phase 1.
- Forbidden contents: No runtime logic, no database schema declarations, and no future-phase types.

# Files to Modify
## `backend/app/infrastructure/db/connection.py`
- Why it must change: It is the only existing persistence module and must become the shared database connection boundary that the new repository layer uses safely.
- Exact scope of change: Keep this file limited to environment loading and the database connection helper needed by the new repositories; tighten it only as required for phase 1 runtime correctness, including explicit failure on missing `DATABASE_URL` if the coding agent implements that behaviour.
- Must remain untouched: No repository query logic, no FastAPI app wiring, no route definitions, and no domain rules.

# Files Forbidden to Modify
- `README.md`
- `.github/AGENT-RUNTIME-RULES.md`
- `.github/agents/*.md`
- `.github/skills/**/*.md`
- `implementation-docs/devplan.md`
- `implementation-docs/current-phase.md`
- `implementation-docs/phase-1-plan.md`
- `implementation-docs/templates/*.md`
- `backend/.env`
- `backend/.gitignore`
- `backend/app/__init__.py`
- Any file under `implementation-docs/` other than `implementation-docs/phase-1-intention-plan.md` during this intention step
- Any file under a `frontend/` path other than the exact phase 1 files listed in this document once implementation begins
- Any file under a `backend/app/` path other than the exact phase 1 files listed in this document once implementation begins

# Required Contracts Between Files
- `backend/app/api/schemas/tasks.py` defines the request and response contracts consumed only by `backend/app/api/routes/tasks.py`.
- `backend/app/api/schemas/sessions.py` defines the response contracts consumed only by `backend/app/api/routes/sessions.py`.
- `backend/app/api/routes/tasks.py` calls `backend/app/domain/services/task_service.py` for task creation, task listing coordination if a service boundary is used there, and task start orchestration; it does not call repository modules directly if the service layer owns the flow.
- `backend/app/api/routes/sessions.py` calls `backend/app/domain/services/session_manager.py` for complete and abort transitions; it does not execute SQL.
- `backend/app/domain/services/task_service.py` may call `backend/app/infrastructure/repositories/task_repository.py`, `backend/app/infrastructure/repositories/session_repository.py`, `backend/app/domain/engines/subtask_engine.py`, and `backend/app/domain/engines/difficulty_reducer.py` to implement the start flow.
- `backend/app/domain/services/session_manager.py` calls `backend/app/infrastructure/repositories/session_repository.py` to create and close sessions and does not call frontend code.
- `backend/app/infrastructure/repositories/task_repository.py` and `backend/app/infrastructure/repositories/session_repository.py` both use `backend/app/infrastructure/db/connection.py` as the only database connection entrypoint.
- `backend/app/main.py` mounts only `backend/app/api/routes/tasks.py` and `backend/app/api/routes/sessions.py` for phase 1.
- `frontend/services/api.ts` is the only frontend file allowed to issue HTTP requests to the backend.
- `frontend/app/page.tsx` owns the page state for the task collection, active session, active instruction, loading status, and error status.
- `frontend/components/task-form.tsx`, `frontend/components/task-list.tsx`, and `frontend/components/session-view.tsx` receive state and callbacks from `frontend/app/page.tsx`; they do not own backend orchestration.
- `frontend/types/study-buddy.ts` provides the local TypeScript payload contracts used by `frontend/services/api.ts`, `frontend/app/page.tsx`, and the three phase 1 components.

# Migration / Schema Impact
- No repository migration file should be created in phase 1.
- No schema change should be made to the existing Supabase PostgreSQL tables described in `implementation-docs/devplan.md`.
- Phase 1 code may read from and write to `tasks` and `sessions` only, using the existing schema shape already defined in the plan.
- No type-generation pipeline exists in the repository today, so no generated schema or client files should be introduced in this phase.

# Test Surface Impact
- No existing tests need modification because no test surface currently exists.
- Later implementation and testing steps should add backend API coverage under exact new paths `backend/tests/api/test_tasks.py` and `backend/tests/api/test_sessions.py`.
- Later implementation and testing steps should add frontend interaction coverage under exact new paths `frontend/__tests__/page.test.tsx` or an equivalent single-page test file if the chosen frontend test runner requires a different naming convention.
- Test additions must remain limited to the phase 1 route set and the single root page flow.

# Risk Points
- The current repository has no backend application skeleton beyond the DB connection helper, so there is a high risk of widening the backend write surface beyond the exact files listed here.
- The current repository has no frontend at all, so there is a high risk of introducing extra pages, extra routes, or subject-oriented UI that belongs to later phases.
- `backend/app/infrastructure/db/connection.py` currently exposes a raw connection helper with no visible guard for a missing `DATABASE_URL`, so phase 1 implementation may drift into ad hoc connection handling unless that file stays the sole DB entrypoint.
- The approved phase plan requires deterministic instruction generation without `subtasks` persistence; implementation may drift into writing generated instructions to the database unless the repository and service boundaries stay strict.
- The frontend is at risk of absorbing business logic because `frontend/app/page.tsx` must coordinate the full user flow; component files must remain presentational and callback-driven.
- The phase plan allows only five backend routes; implementation may drift into adding convenience routes such as `GET /next` or task update endpoints unless route creation is kept to the exact files and handlers listed above.