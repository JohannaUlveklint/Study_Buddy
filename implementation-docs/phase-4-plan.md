# Phase
Phase 4: UX Refinement

# Phase Goal
Phase 4 reduces start friction on the existing single-page frontend by tightening the entry copy, prioritizing the backend-provided next step in the interaction order, adding bounded motion for panel and status changes, and applying explicit responsive spacing and typography rules for tablets and phones without changing backend contracts, adding pages, or introducing any new feature.

# Scope
## Included
- Copy changes on the existing root page, task form, task list, session panel, status banners, and metadata text.
- Start-flow changes on the existing root page that make the recommended next task the first visible action when a recommendation exists and make task creation the first visible action when no task exists.
- Action-specific loading language for page load, task creation, task start, session completion, and session abort.
- CSS transitions and animations limited to the existing root-page layout, panels, banners, task cards, buttons, and session-state swaps.
- Mobile and tablet layout rules limited to the existing page and existing components.

## Excluded
- New features, new decision branches, new pages, new frontend routes, modal flows, and any new component file.
- New backend routes, new backend files, backend logic changes, schema changes, and any backend modification whatsoever.
- Changes to API request or response shapes, recommendation logic, task ordering logic, subject data, or type contracts.
- New analytics, timers, dashboards, onboarding tours, notifications, settings, or personalization controls.

# Preconditions
- Phase 3 is already implemented and the existing root page consumes GET /subjects, GET /tasks, GET /next, POST /tasks, POST /tasks/{task_id}/start, POST /sessions/{session_id}/complete, and POST /sessions/{session_id}/abort.
- The current frontend file surface exists exactly as read in the repository: frontend/app/page.tsx, frontend/app/globals.css, frontend/app/layout.tsx, frontend/components/task-form.tsx, frontend/components/task-list.tsx, frontend/components/session-view.tsx, and frontend/components/subject-icon.tsx.
- frontend/services/api.ts and frontend/types/study-buddy.ts already expose the data required for phase 4, so this phase does not require any new client method or type addition.
- The recommendation state already exists in frontend/app/page.tsx as nextTask and remains backend-owned in phase 4.

# Backend Design
## Routes
### List Subjects
- Method: GET
- Path: /subjects
- Request Shape: No request body.
- Response Shape: Unchanged JSON array of subject objects with id, name, color, and icon.
- Error Conditions: Unchanged backend behavior. The frontend phase 4 work only consumes the existing response.

### List Tasks
- Method: GET
- Path: /tasks
- Request Shape: No request body.
- Response Shape: Unchanged JSON array of task objects with id, title, subject_id, created_at, and is_completed.
- Error Conditions: Unchanged backend behavior. The frontend phase 4 work only consumes the existing response.

### Get Next Task
- Method: GET
- Path: /next
- Request Shape: No request body.
- Response Shape: Unchanged task object or 404 when no incomplete task exists.
- Error Conditions: Unchanged backend behavior. The frontend phase 4 work only consumes the existing response and existing 404 handling.

### Create Task
- Method: POST
- Path: /tasks
- Request Shape: Unchanged JSON body with title and subject_id.
- Response Shape: Unchanged task object with id, title, subject_id, created_at, and is_completed.
- Error Conditions: Unchanged backend behavior. The frontend phase 4 work only changes copy and interaction wording around the existing request.

### Start Task
- Method: POST
- Path: /tasks/{task_id}/start
- Request Shape: Unchanged route parameter task_id and no request body.
- Response Shape: Unchanged TaskStartResponse with session and instruction.
- Error Conditions: Unchanged backend behavior. The frontend phase 4 work only changes the wording and layout used before and after the request.

### Complete Session
- Method: POST
- Path: /sessions/{session_id}/complete
- Request Shape: Unchanged route parameter session_id and no request body.
- Response Shape: Unchanged session object.
- Error Conditions: Unchanged backend behavior. The frontend phase 4 work only changes the button wording and pending copy.

### Abort Session
- Method: POST
- Path: /sessions/{session_id}/abort
- Request Shape: Unchanged route parameter session_id and no request body.
- Response Shape: Unchanged session object.
- Error Conditions: Unchanged backend behavior. The frontend phase 4 work only changes the button wording and pending copy.

# Domain Logic
- No backend engine, service, or repository changes occur in phase 4.
- Recommendation selection remains owned by the existing backend GET /next implementation. React components do not rank tasks, synthesize a fallback recommendation, or alter difficulty language based on business rules.
- The only new frontend interaction rule is presentation order: active session first, recommended next task second, task creation first only when there is no active session and no recommended task.

# Persistence
- No table, field, migration, seed, repository query, or write-path change occurs in phase 4.
- The only data writes in phase 4 remain the existing POST /tasks, POST /tasks/{task_id}/start, POST /sessions/{session_id}/complete, and POST /sessions/{session_id}/abort requests.
- No frontend file adds local persistence, browser storage, or direct database access.

# Frontend Design
## Views
- The root page at / remains the only frontend view.
- The session panel becomes the first rendered interactive block in the page layout when either activeSession or nextTask exists. The task form and task list remain on the same page and remain visible below or beside that panel depending on breakpoint.
- When no task exists, the task form becomes the first rendered interactive block after the hero and uses shorter onboarding copy that directs the user to enter one concrete task.
- The hero remains on the page but shifts from feature-summary wording to activation wording.
- No new page, modal, drawer, tab set, or route state is introduced.

## Components
- frontend/app/layout.tsx: replace the metadata description text from "Phase 1 start flow for Study Buddy" to "Low-friction study activation for the next small step." so browser and share text stop referring to an obsolete phase.
- frontend/app/page.tsx: replace the hero eyebrow text from "Study Buddy" to "Low-friction study start"; replace the hero heading from "Turn one task into one study action." to "Start smaller. Begin faster."; replace the hero copy from "Create a task, start it, get a single instruction, and finish the session without leaving the page." to "Pick one task or start the suggested one. Study Buddy keeps the next action narrow.".
- frontend/app/page.tsx: replace the single generic pending label "Working..." with action-specific text mapped to the current request: "Loading your next step...", "Saving task...", "Preparing the first step...", "Wrapping up this step...", and "Stopping this step...".
- frontend/app/page.tsx: replace the fallback error text from "Unexpected error." to "Something went wrong. Try again." and replace the validation errors from "Enter a task title before creating a task." and "Select a subject before creating a task." to "Enter one task before saving it." and "Choose a subject before saving the task.".
- frontend/app/page.tsx: add one page-level pendingAction state so wording and status banners match the user action that is actually running. Keep all network access in the page and keep services/api.ts unchanged.
- frontend/app/page.tsx: move the session panel block above the task form and task list in the DOM order so the first tab stop after the hero is the active session or suggested start panel whenever one exists.
- frontend/components/task-form.tsx: change the eyebrow from "Create" to "Add one task"; change the heading from "Start with one small task." to "Name the thing you can start now."; add one short helper line under the heading with the text "Keep it concrete. You only need enough detail to begin.".
- frontend/components/task-form.tsx: change the field label from "Task title" to "Task"; change the placeholder from "Read chapter 2" to "Read two pages of chapter 2"; change the submit button from "Add task" to "Save task".
- frontend/components/task-form.tsx: wrap the existing controls in a semantic form element so pressing Enter in the title field triggers the existing create action when the submit button is enabled.
- frontend/components/task-list.tsx: when nextTask exists, change the eyebrow from "Tasks" to "Other ways in" and change the heading from "Queue the next study action." to "Pick a different task if this one feels easier to start.".
- frontend/components/task-list.tsx: when nextTask does not exist, keep the section as the primary chooser and change the heading text to "Choose a task and get one step.".
- frontend/components/task-list.tsx: change the empty-state copy from "No tasks yet. Add one title to create the first study step." to "No tasks yet. Save one task to unlock the first step.".
- frontend/components/task-list.tsx: change each start button label from "Start" to "Start this task" when there is no recommendation and to "Start this instead" when nextTask exists.
- frontend/components/session-view.tsx: active-session state keeps the instruction title as the main heading but changes the eyebrow from "Active session" to "Do this now"; change the primary button from "Complete session" to "I finished this step"; change the secondary button from "Abort session" to "Stop for now".
- frontend/components/session-view.tsx: recommended-task state changes the eyebrow from "Suggested next" to "Start here"; add one short supporting line with the text "This is the narrowest way back in right now." above the subject row; change the button text from "Start" to "Start this step".
- frontend/components/session-view.tsx: no-session placeholder changes the heading from "No active session." to "No step yet." and changes the body text from "Start a task to reveal the single instruction for this phase." to "Save a task or pick one from the list to get the next action.".
- frontend/app/globals.css: add shared focus-visible styles for buttons, inputs, and selects using the existing accent color so keyboard and touch-assist navigation expose the current control without adding new UI elements.
- frontend/app/globals.css: add entry and state-swap motion with exact timing rules: page sections fade and lift in over 220ms, status banners fade in over 180ms, session-panel state swaps animate opacity and translateY over 180ms, and buttons, task cards, panels, inputs, and selects transition transform, border-color, background-color, box-shadow, and opacity over 160ms to 180ms.
- frontend/app/globals.css: add mobile and tablet breakpoints at 1024px, 900px, 640px, and 480px with explicit spacing, font-size, and stack changes defined in this plan.
- frontend/components/subject-icon.tsx: no change in phase 4.

## State Flow
- frontend/app/page.tsx owns tasks, subjects, title, selectedSubjectId, activeSession, activeInstruction, nextTask, isPending, pendingAction, and error.
- On initial load, the page requests subjects, tasks, and nextTask through the existing API client, sets pendingAction to the load state, and renders "Loading your next step..." while the request is active.
- After the initial load, the page determines the primary interaction zone in this exact order: active session when activeSession and activeInstruction exist, recommended next task when nextTask exists, task form when neither state exists.
- Task creation keeps the existing POST /tasks request. During that request, the page sets pendingAction to create, disables all start and session-resolution controls, and leaves the user on the same page.
- Task start keeps the existing POST /tasks/{task_id}/start request. During that request, the page sets pendingAction to start, clears nextTask only after the backend responds successfully, and moves the new active session panel into the first interactive position.
- Session completion keeps the existing POST /sessions/{session_id}/complete request. During that request, the page sets pendingAction to complete, keeps the active instruction visible until the backend response returns, and refreshes tasks and nextTask after success.
- Session abort keeps the existing POST /sessions/{session_id}/abort request. During that request, the page sets pendingAction to abort, keeps the active instruction visible until the backend response returns, and refreshes tasks and nextTask after success.
- TaskForm receives only input state and callbacks from the page. TaskList receives only rendered task items, recommendation-aware wording props, and the start callback. SessionView receives only the already-resolved active session or recommended task props and never fetches data itself.

# File-Level Impact
## Files to Create
- None

## Files to Modify
- frontend/app/layout.tsx
- frontend/app/page.tsx
- frontend/app/globals.css
- frontend/components/task-form.tsx
- frontend/components/task-list.tsx
- frontend/components/session-view.tsx

## Files Forbidden to Modify
- backend/**
- frontend/services/api.ts
- frontend/types/study-buddy.ts
- frontend/components/subject-icon.tsx
- Any new file under frontend/app/
- Any new file under frontend/components/
- Any new frontend page, route, modal, or drawer file

# Implementation Sequence
1. Update frontend/app/layout.tsx metadata text so phase-specific wording is removed from the browser description.
2. Update frontend/app/page.tsx to add pendingAction state, action-specific loading copy, revised validation and fallback error copy, and the new DOM order that places the session panel before the task form and task list whenever a session or recommendation exists.
3. Update frontend/components/task-form.tsx to apply the exact new heading, helper copy, field label, placeholder, and submit label, and convert the existing controls into a semantic form that submits on Enter.
4. Update frontend/components/task-list.tsx so its heading, empty-state text, and start-button labels change based on whether nextTask exists, with no change to task data or start behavior.
5. Update frontend/components/session-view.tsx so the three existing panel states use the exact new copy, keep the same callbacks, and present the recommended task as the primary no-session entry point.
6. Update frontend/app/globals.css to add the exact focus styles, panel and banner entry animations, session-state swap motion, and control hover or press transitions defined in this plan.
7. Update frontend/app/globals.css responsive rules so the page uses these exact breakpoint changes: at 1024px reduce shell padding to 56px 20px 72px and tighten the two-column ratio; at 900px stack the layout into one column with the session panel first; at 640px reduce shell padding to 32px 14px 48px, reduce panel padding to 18px, reduce hero text size and line-height, stack task-card actions vertically, and make all buttons full width; at 480px reduce input, select, and button minimum height to 48px, collapse session stats to one column, reduce metadata font size, and tighten badge spacing.
8. Verify that only the six named frontend files changed, no service or type file changed, no backend file changed, and the page still consumes the existing backend routes with unchanged request and response contracts.

# Completion Criteria
1. Only frontend/app/layout.tsx, frontend/app/page.tsx, frontend/app/globals.css, frontend/components/task-form.tsx, frontend/components/task-list.tsx, and frontend/components/session-view.tsx change for phase 4.
2. No backend file, backend route, backend service, backend repository, API client file, type file, or new page file changes in phase 4.
3. The root-page hero and metadata text match the exact replacement copy defined in this plan and no remaining visible text refers to "Phase 1".
4. The page shows action-specific pending copy instead of the single generic "Working..." label for load, create, start, complete, and abort requests.
5. The session panel is the first interactive block in DOM order whenever an active session or recommended next task exists.
6. Pressing Enter in the task title field triggers the existing create action when the form is enabled and does nothing when the existing disabled conditions are true.
7. The task list changes its heading and start-button wording when nextTask exists, and the empty-state text matches the exact copy defined in this plan.
8. The session panel active, recommendation, and placeholder states match the exact copy and button labels defined in this plan without changing their callbacks or adding new controls.
9. The stylesheet applies focus-visible styling plus the exact bounded motion rules from this plan: 220ms section entry, 180ms banner fade, 180ms session-state swap, and 160ms to 180ms control transitions.
10. The stylesheet applies the exact responsive breakpoint rules from this plan at 1024px, 900px, 640px, and 480px, including stacked layout on tablet and phone, tighter spacing, smaller type, and full-width action controls on small screens.

# Out-of-Scope Protection
- Do not add any new feature disguised as UX work, including timers, onboarding steps, empty-state recommendations beyond GET /next, filters, sorting controls, or task editing.
- Do not modify backend code, backend routes, backend persistence, API client methods, or shared type contracts.
- Do not create a new page, modal, drawer, or overlay to present the start flow. Phase 4 remains on the existing root page.
- Do not move recommendation logic, task ranking, or session business rules into React. The frontend only changes copy, layout order, and motion.
- Do not change the underlying create, start, complete, or abort request sequence. Phase 4 changes presentation and interaction polish only.
- Do not widen the file surface beyond the six named frontend files.