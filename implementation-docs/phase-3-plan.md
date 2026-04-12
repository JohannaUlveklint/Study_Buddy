# Phase
Phase 3: Adaptive Logic

# Phase Goal
Phase 3 adds deterministic history-driven behavior to the existing single-page study flow: completing or aborting a session writes one attempt row, starting a task reads the last five attempts for that same task and applies the exact difficulty rules from the master spec, and the frontend surfaces one backend-selected next task through GET /next without adding pages or moving business logic into React.

# Scope
## Included
- Attempt tracking on POST /sessions/{session_id}/complete and POST /sessions/{session_id}/abort, with one attempts row written for each successful session end.
- Retrieval of the last five attempts for the same task during POST /tasks/{task_id}/start.
- DifficultyReducer logic that counts recent aborts and completions from those five attempts and mutates only instruction.difficulty_level.
- GET /next as a backend-selected recommendation endpoint that returns one incomplete task.
- Root-page frontend changes limited to fetching GET /next and rendering the recommended task inside the existing session-panel area when no session is active.
- Refresh of the recommendation after task creation, task start, session completion, and session abort.

## Excluded
- AI, probabilistic ranking, hidden heuristics, and any reducer behavior outside the two explicit rules in implementation-docs/devplan.md.
- New frontend pages, new frontend routes, dashboards, analytics views, and attempt-history UI.
- Changes to subject write APIs, subject UI write paths, subtask write APIs, and subtask editing flows.
- Changes to task completion semantics, task list sorting, subject retrieval behavior, or planned session duration.
- Direct frontend Supabase usage, direct frontend database access, and frontend-owned difficulty or recommendation logic.
- Schema migrations, seed changes, and any change to table definitions for subjects, tasks, subtasks, sessions, or attempts.

# Preconditions
- Phase 2 task start flow already inserts one subtask row and one session row in one transaction, and sessions created through that flow have a non-null subtask_id.
- The PostgreSQL schema from implementation-docs/devplan.md already exists, including the attempts table with session_id, difficulty_level, and outcome.
- backend/app/api/routes/tasks.py already exposes POST /tasks, GET /tasks, and POST /tasks/{task_id}/start through TaskService.
- backend/app/api/routes/sessions.py already exposes POST /sessions/{session_id}/complete and POST /sessions/{session_id}/abort through SessionManager.
- frontend/app/page.tsx already owns the root-page state, loads subjects and tasks through frontend/services/api.ts, and renders the existing session panel without extra pages.

# Backend Design
## Routes
### Start Task
- Method: POST
- Path: /tasks/{task_id}/start
- Request Shape: Route parameter task_id as a UUID string. No request body.
- Response Shape: Existing TaskStartResponse contract. session contains id, task_id, subtask_id, started_at, ended_at, planned_duration_minutes, actual_duration_minutes, was_completed, and was_aborted. instruction contains title and difficulty_level. The response shape does not change in phase 3. The returned instruction.difficulty_level is the reducer result after reading the last five attempts for that task.
- Error Conditions: 404 when the task does not exist. 409 when the task already has an open session. 500 when recent-attempt lookup fails, reducer input preparation fails, subtask insertion fails, or session insertion fails.

### Complete Session
- Method: POST
- Path: /sessions/{session_id}/complete
- Request Shape: Route parameter session_id as a UUID string. No request body.
- Response Shape: Existing SessionResponse contract with id, task_id, subtask_id, started_at, ended_at, planned_duration_minutes, actual_duration_minutes, was_completed, and was_aborted. No attempt payload is returned.
- Error Conditions: 404 when the session does not exist. 409 when ended_at is already non-null. 500 when the session update fails or the attempt insert fails. The session update and attempt insert execute in one transaction, so a failed attempt insert leaves the session unchanged.

### Abort Session
- Method: POST
- Path: /sessions/{session_id}/abort
- Request Shape: Route parameter session_id as a UUID string. No request body.
- Response Shape: Existing SessionResponse contract with id, task_id, subtask_id, started_at, ended_at, planned_duration_minutes, actual_duration_minutes, was_completed, and was_aborted. No attempt payload is returned.
- Error Conditions: 404 when the session does not exist. 409 when ended_at is already non-null. 500 when the session update fails or the attempt insert fails. The session update and attempt insert execute in one transaction, so a failed attempt insert leaves the session unchanged.

### Get Next Task
- Method: GET
- Path: /next
- Request Shape: No request body.
- Response Shape: Existing TaskResponse contract with id, title, subject_id, created_at, and is_completed for one recommended incomplete task. No subject object and no attempt summary are embedded.
- Error Conditions: 404 when no task row exists with is_completed = false. 500 when the recommendation query fails.

## Domain Logic
- DifficultyReducer: accept the generated instruction plus a context containing recent_aborts and recent_completions derived from the last five attempts for the same task. Preserve instruction.title. Read the current difficulty from instruction.difficulty_level. If recent_aborts > 2, set difficulty_level to 1. Else if recent_completions > 3, set difficulty_level to the smaller of current difficulty_level + 1 and 5. Else leave difficulty_level unchanged. The abort rule executes first and blocks the completion rule when both conditions are true.
- AttemptRepository: own phase 3 attempt reads and writes only. list_recent_attempts_for_task reads the last five attempt rows for one task in newest-ended-session order. create_attempt_from_session writes one attempt row using the ended session id, the linked subtask difficulty_level, and the explicit outcome string completed or aborted.
- TaskService.start_task: keep the existing task lookup and open-session rejection. Before opening the transaction that writes the new subtask and session, load the last five attempts for the same task through AttemptRepository, count completed and aborted outcomes in Python, pass those counts into DifficultyReducer, then persist the reduced instruction through the existing subtask and session write flow.
- TaskService.get_next_task: delegate the recommendation selection to TaskRepository, raise a not-found domain error when no incomplete task exists, and return the selected task row unchanged.
- SessionManager.complete_session: keep the existing not-found and already-ended validation. After validation, end the session and insert an attempt row with outcome completed in one database transaction, then return the updated session row.
- SessionManager.abort_session: keep the existing not-found and already-ended validation. After validation, end the session and insert an attempt row with outcome aborted in one database transaction, then return the updated session row.
- Route handlers remain thin. No SQL moves into routes, and no attempt counting or recommendation ordering moves into frontend code.

## Persistence
- No schema migration work occurs in phase 3. The attempts table from implementation-docs/devplan.md is used as-is.
- Recent attempt history for task start is read with this SQL in backend/app/infrastructure/repositories/attempt_repository.py: SELECT a.session_id, a.difficulty_level, a.outcome FROM attempts a JOIN sessions s ON s.id = a.session_id WHERE s.task_id = $1 ORDER BY s.ended_at DESC, a.id DESC LIMIT 5.
- Session completion continues to update the existing sessions row, but phase 3 adds a connection-bound repository path so the update can share a transaction with the attempt insert. The SQL remains: UPDATE sessions SET ended_at = NOW(), was_completed = $2, was_aborted = $3 WHERE id = $1 RETURNING id, task_id, subtask_id, started_at, ended_at, planned_duration_minutes, actual_duration_minutes, was_completed, was_aborted.
- Attempt insert for session completion and abort uses this SQL in backend/app/infrastructure/repositories/attempt_repository.py: INSERT INTO attempts (session_id, difficulty_level, outcome) SELECT s.id, st.difficulty_level, $2 FROM sessions s JOIN subtasks st ON st.id = s.subtask_id WHERE s.id = $1 RETURNING id, session_id, difficulty_level, outcome.
- Task recommendation for GET /next uses one PostgreSQL query in backend/app/infrastructure/repositories/task_repository.py with latest session selection per task: WITH latest_sessions AS ( SELECT DISTINCT ON (s.task_id) s.task_id, s.ended_at, s.was_aborted FROM sessions s WHERE s.ended_at IS NOT NULL ORDER BY s.task_id, s.ended_at DESC ) SELECT t.id, t.title, t.subject_id, t.created_at, t.is_completed FROM tasks t LEFT JOIN latest_sessions ls ON ls.task_id = t.id WHERE t.is_completed = FALSE ORDER BY CASE WHEN ls.was_aborted THEN 0 ELSE 1 END, CASE WHEN ls.was_aborted THEN ls.ended_at END DESC NULLS LAST, CASE WHEN ls.was_aborted THEN NULL ELSE t.created_at END ASC LIMIT 1.
- GET /next does not write any table. It reads tasks plus the latest ended session per task and returns one row only.
- Starting a task continues to insert one subtask row and one session row exactly as phase 2 defined. Phase 3 changes only the difficulty_level value supplied to the existing subtasks insert.
- subjects, subtasks, and tasks tables receive no new write paths in this phase beyond the pre-existing task creation and task start flows.

# Frontend Design
## Views
- The root page at / remains the only frontend view.
- The right-hand session panel area renders one of three states only: active session, recommended next task, or the existing empty placeholder when GET /next returns no task.
- No new page, modal route, dashboard, or history screen is introduced.

## Components
- frontend/app/page.tsx: own the recommendation state, fetch GET /next alongside subjects and tasks, refresh that recommendation after every mutation that changes task or session state, and pass presentational props into the existing child components.
- frontend/components/session-view.tsx: render the existing active-session state unchanged when activeSession and activeInstruction exist, and add a no-session recommendation state that displays the recommended task title, matched subject metadata, and a start action wired to the existing POST /tasks/{task_id}/start flow.
- frontend/services/api.ts: add one GET /next client method. The method returns the backend TaskResponse on 200 and returns null on 404 so the page can render the existing empty placeholder without treating no recommendation as an error.
- Existing task form, task list, and subject icon components remain phase 2 components. They do not fetch GET /next and do not own recommendation logic.

## State Flow
- frontend/app/page.tsx holds tasks, subjects, title, selectedSubjectId, activeSession, activeInstruction, nextTask, isPending, and error.
- Initial page load calls listSubjects, listTasks, and getNextTask in parallel through frontend/services/api.ts, then stores all three results in page state.
- The page derives the subject display data for nextTask by matching nextTask.subject_id against the already-fetched subjects list. No frontend component queries subjects separately.
- Creating a task keeps the current POST /tasks flow and then refreshes tasks plus nextTask.
- Starting a task from either the task list or the recommendation panel calls the same startTask client method, stores the returned session and instruction, clears nextTask from local state, and leaves reducer logic entirely on the backend.
- Completing or aborting a session keeps the existing session endpoint flow, clears activeSession and activeInstruction after success, and then refreshes tasks plus nextTask.
- When getNextTask returns null because the backend returned 404, the page renders the existing no-active-session placeholder and does not synthesize a client-side fallback recommendation.

# File-Level Impact
## Files to Create
- backend/app/infrastructure/repositories/attempt_repository.py

## Files to Modify
- backend/app/api/routes/sessions.py
- backend/app/api/routes/tasks.py
- backend/app/domain/engines/difficulty_reducer.py
- backend/app/domain/services/session_manager.py
- backend/app/domain/services/task_service.py
- backend/app/infrastructure/repositories/session_repository.py
- backend/app/infrastructure/repositories/task_repository.py
- frontend/app/page.tsx
- frontend/components/session-view.tsx
- frontend/services/api.ts

## Files Forbidden to Modify
- backend/app/main.py
- backend/app/api/routes/subjects.py
- backend/app/api/schemas/sessions.py
- backend/app/api/schemas/subjects.py
- backend/app/api/schemas/tasks.py
- backend/app/domain/engines/subtask_engine.py
- backend/app/domain/services/subject_service.py
- backend/app/infrastructure/db/connection.py
- backend/app/infrastructure/repositories/subject_repository.py
- backend/app/infrastructure/repositories/subtask_repository.py
- frontend/app/layout.tsx
- frontend/app/globals.css
- frontend/components/subject-icon.tsx
- frontend/components/task-form.tsx
- frontend/components/task-list.tsx
- frontend/types/study-buddy.ts
- Any new file under frontend/app/ other than the existing root page
- Any file that introduces direct frontend Supabase access, analytics UI, or subject or subtask write surfaces

# Implementation Sequence
1. Create backend/app/infrastructure/repositories/attempt_repository.py with one read method for the last five attempts for a task and one write method that inserts an attempt row from an ended session plus explicit outcome.
2. Extend backend/app/infrastructure/repositories/session_repository.py with a connection-bound end-session method so the session update can run inside the same transaction as the new attempt insert.
3. Extend backend/app/infrastructure/repositories/task_repository.py with one recommendation query that returns the incomplete task whose latest ended session is an aborted session with the newest ended_at value, or the oldest incomplete task when no latest session is aborted.
4. Replace the identity reducer in backend/app/domain/engines/difficulty_reducer.py with the exact recent_aborts and recent_completions logic from the devplan, preserving instruction.title and capping difficulty_level at 5.
5. Update backend/app/domain/services/task_service.py so start_task reads recent attempts through AttemptRepository, counts completed and aborted outcomes from those five rows, passes the counts into DifficultyReducer, and then preserves the existing subtask-plus-session transaction with the reduced difficulty_level.
6. Update backend/app/domain/services/task_service.py with a get_next_task method that delegates to TaskRepository and raises the existing not-found style error when no incomplete task exists.
7. Update backend/app/domain/services/session_manager.py so complete_session and abort_session each open one transaction, end the session inside that transaction, write one attempt row with the correct outcome string, and return the updated session row only after both writes succeed.
8. Update backend/app/api/routes/sessions.py to construct SessionManager with the new AttemptRepository dependency while keeping the existing route paths, response models, and HTTP status mapping.
9. Update backend/app/api/routes/tasks.py to construct TaskService with AttemptRepository and add GET /next using the existing TaskResponse contract and a 404 mapping when no incomplete task exists.
10. Update frontend/services/api.ts to add getNextTask and convert a backend 404 for /next into null instead of an error.
11. Update frontend/app/page.tsx to load the recommendation on first render, refresh it after create or resolve actions, clear it while a session is active, and pass a recommended-task state into the session-panel area.
12. Update frontend/components/session-view.tsx so the existing panel can render the recommended next task and start it through the already-existing start callback without creating a second page or a second recommendation source.

# Completion Criteria
1. POST /sessions/{session_id}/complete writes exactly one attempts row with the session id, the linked subtask difficulty_level, and outcome = completed when the session ends successfully.
2. POST /sessions/{session_id}/abort writes exactly one attempts row with the session id, the linked subtask difficulty_level, and outcome = aborted when the session ends successfully.
3. If the attempt insert fails during complete or abort, the session row remains unended because both writes share one transaction.
4. POST /tasks/{task_id}/start reads no more and no fewer than the last five attempts for that same task when preparing reducer input.
5. The reducer sets difficulty_level to 1 when recent_aborts > 2, raises difficulty_level by exactly 1 and never above 5 when recent_completions > 3 and the abort rule is false, and leaves difficulty_level unchanged in all other cases.
6. GET /next returns one TaskResponse row for an incomplete task and uses the latest aborted-session-first rule before the oldest-incomplete fallback rule.
7. GET /next returns 404 when no task exists with is_completed = false.
8. The frontend root page shows the backend-provided recommendation in the existing session-panel area when no active session exists and GET /next returns a task.
9. The frontend root page keeps the existing placeholder when GET /next returns 404 and does not generate a client-side recommendation.
10. No new frontend page, no analytics UI, no subject write surface, no subtask write surface, and no AI logic are added.

# Out-of-Scope Protection
- Do not add attempt history endpoints, attempt history panels, or analytics summaries. Phase 3 writes and reads attempts only for reducer input and GET /next selection.
- Do not add any recommendation formula beyond the exact latest-aborted-session rule and oldest-incomplete fallback defined in this plan.
- Do not change tasks.is_completed, subtasks.is_completed, or subject behavior as part of session completion or abort. Phase 3 does not redefine completion semantics.
- Do not widen TaskResponse or SessionResponse to include attempt objects, subject objects, or history counts.
- Do not add a new frontend page, new frontend route, or second recommendation component outside the existing root page and session-panel area.
- Do not move attempt counting, reducer execution, or next-task ranking into frontend code.
- Do not modify backend/app/domain/engines/subtask_engine.py or introduce any new black-box difficulty logic.