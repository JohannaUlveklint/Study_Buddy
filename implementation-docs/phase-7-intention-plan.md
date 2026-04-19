# Phase
Phase 7

# Summary
Phase 7 hardens the existing backend contract surface without changing Study Buddy product behavior. The implementation is limited to moving request-body and path-parameter enforcement fully to the FastAPI and Pydantic boundary, introducing one shared backend error schema and one shared exception-normalization path, exposing machine-readable API metadata plus bounded system liveness and readiness endpoints, and extending backend-only tests to prove both the success flow and immediate contract failure paths. No frontend logic, domain-service rules, repository query behavior, dependency set, or database schema may change in this phase.

# Repository Reality Check
- Existing backend surface: backend/app/main.py already owns FastAPI app construction, CORS, pooled connection lifecycle, and a DatabaseUnavailableError handler, but it does not register shared handlers for request validation, response validation, HTTPException, or uncaught exceptions, and it does not include a system router. backend/app/api/routes/tasks.py, backend/app/api/routes/sessions.py, and backend/app/api/routes/subjects.py already expose the current business routes and map domain failures to HTTPException detail strings, but task-title validation is still manual in the tasks route and task_id and session_id are still accepted as raw strings instead of FastAPI UUID parameters. backend/app/api/schemas/tasks.py, backend/app/api/schemas/sessions.py, and backend/app/api/schemas/subjects.py already define the current success DTOs, but there is no shared error DTO and no DTOs for health or readiness responses. backend/app/infrastructure/db/connection.py already owns database URL normalization, pool startup and shutdown, and pooled acquisition, but it does not expose a dedicated readiness probe for a connection-acquire plus lightweight query path.
- Existing frontend surface: frontend/services/api.ts already treats backend failures as a JSON payload with a detail field and frontend/app/page.tsx already executes the user flow that Phase 7 must preserve: load subjects, load tasks, load next task, create task, start task, complete session, abort session, and reload tasks and next task. There is no frontend health UI, readiness UI, or OpenAPI consumer, and no frontend file needs to become a write target in this phase.
- Existing tests: backend/tests/test_task_routes.py, backend/tests/test_session_routes.py, backend/tests/test_subject_routes.py, and backend/tests/test_connection.py already constrain current route-level status mapping and connection-pool behavior. backend/tests/test_task_service.py, backend/tests/test_session_manager.py, backend/tests/test_subtask_engine.py, backend/tests/test_difficulty_reducer.py, backend/tests/test_personalization_engine.py, and backend/tests/test_session_repository.py already cover current orchestration, engine, and repository behavior that Phase 7 must not rewrite.
- Missing required surfaces: there is no backend/app/api/routes/system.py, backend/app/api/schemas/errors.py, or backend/app/api/schemas/system.py. There is no explicit readiness probe entry point in backend/app/infrastructure/db/connection.py. There is no backend test file dedicated to /health and /ready and no backend test file dedicated to the OpenAPI and boundary-contract surface.

# Files to Create
## backend/app/api/routes/system.py
- Why it must exist: Phase 7 introduces GET /health and GET /ready, and no existing route module owns those endpoints.
- Responsibility: Define the system-only route surface for liveness and readiness, declare the success DTOs and shared error responses for those endpoints, and delegate readiness probing to backend/app/infrastructure/db/connection.py.
- Forbidden contents: No direct business-route logic, no task, session, or subject orchestration, no inline database query code beyond calling the connection-layer readiness function, and no frontend-facing behavior.

## backend/app/api/schemas/errors.py
- Why it must exist: the repository has no shared backend error DTO today, but Phase 7 requires one documented JSON error shape for handled failures.
- Responsibility: Own the single error response schema used by documented request-validation, domain, readiness, and unexpected-failure responses while preserving detail as the client-visible field.
- Forbidden contents: No success DTOs, no route logic, no exception handling, and no business validation rules.

## backend/app/api/schemas/system.py
- Why it must exist: Phase 7 adds contract-bound success payloads for GET /health and GET /ready, and no existing schema file owns those payloads.
- Responsibility: Define the liveness and readiness success DTOs only.
- Forbidden contents: No business DTOs, no error DTOs, no validation side effects, and no database access logic.

## backend/tests/test_system_routes.py
- Why it must exist: the backend currently has no direct test file for the new system endpoints, and Phase 7 requires proof that liveness and readiness behave differently under dependency failure.
- Responsibility: Prove GET /health stays process-only, prove GET /ready uses the readiness probe contract, and prove documented success and failure payload shapes for the system endpoints.
- Forbidden contents: No live database dependency, no frontend assertions, no business-route orchestration tests, and no schema-migration assertions.

## backend/tests/test_api_contract_surface.py
- Why it must exist: the backend currently has no dedicated contract-surface test file for OpenAPI exposure, boundary validation, or deliberate response-contract failure.
- Responsibility: Prove /openapi.json exposes the documented route contract, prove malformed request bodies and malformed UUID path parameters fail at the FastAPI boundary, and prove at least one invalid response payload is surfaced as a contract failure instead of a malformed success.
- Forbidden contents: No browser harness, no frontend behavior assertions, no repository-logic rewrites, and no dependence on undocumented routes.

# Files to Modify
## backend/app/main.py
- Why it must change: the app entry point currently only normalizes DatabaseUnavailableError to a JSON response and does not own the full shared error-handling and system-route registration contract required by Phase 7.
- Exact scope of change: Register the new system router, keep the existing pooled lifespan and CORS configuration, and add the shared exception handling needed to normalize RequestValidationError, ResponseValidationError, HTTPException, DatabaseUnavailableError, and uncaught exceptions into the documented error shape.
- Must remain untouched: The FastAPI app identity, existing CORS origins and middleware configuration, pooled startup and shutdown ownership, and existing business router inclusion must remain in place. Do not add unrelated middleware, dependencies, authentication, or frontend behavior.

## backend/app/api/routes/tasks.py
- Why it must change: the current tasks route layer still trims and rejects blank titles manually and still accepts task_id as a raw string instead of enforcing the contract at the FastAPI boundary.
- Exact scope of change: Remove route-local blank-title enforcement in favor of backend/app/api/schemas/tasks.py, switch task_id to a typed UUID boundary input, and declare the shared error response metadata for POST /tasks, GET /tasks, POST /tasks/{task_id}/start, and GET /next while preserving the existing success response models and service delegation.
- Must remain untouched: Route paths, business-service wiring, success payload shapes, and all task-start orchestration logic in backend/app/domain/services/task_service.py must remain unchanged. Do not add business rules or database probing to this route module.

## backend/app/api/routes/sessions.py
- Why it must change: the current session routes expose the right business endpoints but do not yet express the Phase 7 UUID boundary and shared error-contract metadata.
- Exact scope of change: Switch session_id to a typed UUID boundary input and declare the shared error response metadata for the complete and abort endpoints while preserving the current response model, status codes, and delegation to backend/app/domain/services/session_manager.py.
- Must remain untouched: Session state rules, service construction, route paths, and the current success payload shape must remain unchanged. Do not move session-resolution logic into this module.

## backend/app/api/routes/subjects.py
- Why it must change: the current subjects route lacks the shared error response metadata required for the Phase 7 documented contract surface.
- Exact scope of change: Add the shared error response metadata for GET /subjects while preserving the current route path, response model, status code, and delegation to backend/app/domain/services/subject_service.py.
- Must remain untouched: Subject listing logic, response payload shape, service construction, and route path must remain unchanged. Do not add sorting, filtering, readiness logic, or frontend concerns here.

## backend/app/api/schemas/tasks.py
- Why it must change: the current CreateTaskRequest only type-checks fields and does not own the trimmed non-blank title rule required at the request boundary.
- Exact scope of change: Add bounded request DTO validation so title is trimmed and rejected when blank after trimming, while preserving the existing success DTO field sets for task, session, instruction, and task-start responses.
- Must remain untouched: The current success response field names, field types, and DTO responsibilities must remain unchanged. Do not add system DTOs or error DTOs to this file.

## backend/app/infrastructure/db/connection.py
- Why it must change: the connection layer currently exposes pool lifecycle and pooled acquisition but has no dedicated readiness probe contract for GET /ready.
- Exact scope of change: Add one readiness probe function that reuses the existing pool, verifies the pool exists, acquires one connection, executes one lightweight database query, and raises DatabaseUnavailableError when readiness fails.
- Must remain untouched: DATABASE_URL loading, URL normalization, pool initialization, pool shutdown, pooled acquisition, and the existing DatabaseUnavailableError type must remain the only connection responsibilities. Do not add retries, business queries, migrations, or route logic here.

## backend/tests/test_connection.py
- Why it must change: the current connection tests cover URL normalization, pool-init failure, pooled acquisition failure, and pool shutdown, but they do not constrain the new readiness probe behavior.
- Exact scope of change: Extend the file so it verifies readiness success, missing-pool failure, acquire failure, and probe-query failure for the new connection-layer readiness function.
- Must remain untouched: Existing pool lifecycle and URL-normalization assertions should remain in scope and should not be rewritten into integration tests.

## backend/tests/test_task_routes.py
- Why it must change: the current task route tests reflect pre-Phase-7 manual blank-title handling and do not yet constrain the OpenAPI-documented boundary-validation contract for task creation and task start.
- Exact scope of change: Update task-route tests so they align with DTO-owned title validation, shared handled-error shape expectations where the route layer still raises handled HTTP errors, and typed UUID path enforcement where route-level behavior is still directly tested.
- Must remain untouched: Existing task-route business status mapping for not found, conflict, database unavailable, and generic failure should remain covered. Do not widen this file into service, repository, or frontend testing.

## backend/tests/test_session_routes.py
- Why it must change: the session route module will move to typed UUID boundary inputs and shared error-contract metadata, and the route test surface must stay aligned with that narrow contract.
- Exact scope of change: Adjust only what is necessary for complete and abort route tests to remain valid after the boundary-input typing and shared handled-error contract changes.
- Must remain untouched: Existing not-found, conflict, database-unavailable, and generic-failure route assertions should remain the focus. Do not turn this file into end-to-end user-flow coverage.

## backend/tests/test_subject_routes.py
- Why it must change: the subjects route will gain documented shared error metadata and must continue to preserve its handled error and success contract.
- Exact scope of change: Adjust only what is necessary so the file remains aligned with the shared handled-error contract and the unchanged subject success payload.
- Must remain untouched: The file must stay limited to subject-route behavior. Do not add system-route assertions, frontend assertions, or service orchestration coverage.

# Files Forbidden to Modify
- backend/app/domain/engines/**
- backend/app/domain/services/**
- backend/app/infrastructure/repositories/**
- backend/app/api/schemas/sessions.py
- backend/app/api/schemas/subjects.py
- backend/tests/test_task_service.py
- backend/tests/test_session_manager.py
- backend/tests/test_subtask_engine.py
- backend/tests/test_difficulty_reducer.py
- backend/tests/test_personalization_engine.py
- backend/tests/test_session_repository.py
- backend/requirements.txt
- frontend/**
- implementation-docs/devplan.md
- implementation-docs/current-phase.md
- implementation-docs/phase-1-*.md
- implementation-docs/phase-2-*.md
- implementation-docs/phase-3-*.md
- implementation-docs/phase-4-*.md
- implementation-docs/phase-5-*.md
- implementation-docs/phase-6-*.md
- implementation-docs/phase-7-plan.md
- Any file outside the exact create and modify lists in this intention plan

# Required Contracts Between Files
- backend/app/main.py must remain the single FastAPI composition root. It must include backend/app/api/routes/system.py alongside the existing business routers and must normalize handled failures into the shared schema from backend/app/api/schemas/errors.py.
- backend/app/api/routes/tasks.py must remain a thin adapter over backend/app/domain/services/task_service.py. Request-body trimming and blank-title rejection must come from backend/app/api/schemas/tasks.py, not from route-local logic, and task_id must be rejected by the FastAPI boundary before service execution when malformed.
- backend/app/api/routes/sessions.py must remain a thin adapter over backend/app/domain/services/session_manager.py. session_id must be rejected by the FastAPI boundary before service execution when malformed, and the module must not implement session business rules locally.
- backend/app/api/routes/subjects.py must remain a thin adapter over backend/app/domain/services/subject_service.py and must only add documented error-contract metadata, not business logic.
- backend/app/api/routes/system.py must use backend/app/api/schemas/system.py for success responses and backend/app/api/schemas/errors.py for documented failure responses. GET /health must not depend on the database. GET /ready must depend only on the readiness probe exposed by backend/app/infrastructure/db/connection.py.
- backend/app/infrastructure/db/connection.py must remain the single owner of database readiness probing. The system route must call that probe instead of issuing SQL directly, and no business route may adopt readiness logic.
- frontend/services/api.ts must remain able to read handled backend failures from detail without any frontend change. Phase 7 error normalization must preserve that field.
- frontend/app/page.tsx must remain the owner of frontend page state and the existing user flow sequence. No validation, readiness, or OpenAPI logic may move into the frontend during this phase.

# Migration / Schema Impact
- No migration or schema change is allowed.
- No table, column, constraint, index, seed, or data backfill change is allowed.
- No frontend type-generation, SDK generation, or OpenAPI code-generation step is introduced.
- The only contract expansion is runtime API metadata and the addition of system endpoint DTOs and the shared backend error DTO.

# Test Surface Impact
- Add backend/tests/test_system_routes.py.
- Add backend/tests/test_api_contract_surface.py.
- Modify backend/tests/test_connection.py.
- Modify backend/tests/test_task_routes.py.
- Modify backend/tests/test_session_routes.py.
- Modify backend/tests/test_subject_routes.py.
- Keep backend/tests/test_task_service.py, backend/tests/test_session_manager.py, backend/tests/test_session_repository.py, backend/tests/test_subtask_engine.py, backend/tests/test_difficulty_reducer.py, and backend/tests/test_personalization_engine.py unchanged.

# Risk Points
- The main drift risk is leaving blank-title enforcement in backend/app/api/routes/tasks.py, which would keep Phase 7 request validation split between the route layer and the DTO boundary and would preserve a 400 path where the phase requires a boundary 422.
- Another concrete risk is implementing GET /health through the database path, which would collapse liveness and readiness into the same dependency behavior and violate the Phase 7 contract.
- A second backend drift risk is adding readiness probing directly inside backend/app/api/routes/system.py instead of backend/app/infrastructure/db/connection.py, which would smear infrastructure behavior into the route layer.
- A contract risk is changing the handled error payload away from detail, which would break the unchanged frontend/services/api.ts error reader.
- Another contract risk is changing any existing business success payload shape while adding response validation and OpenAPI metadata.
- A scope risk is widening edits into backend/app/domain/services/**, backend/app/infrastructure/repositories/**, frontend/**, or dependency files under the label of contract cleanup.