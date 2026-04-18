# Study Buddy — Full Development & Design Execution Directive

---

# 0. Absolute Execution Rules

These rules override everything else.

Copilot must follow these strictly.

No business logic in frontend
No direct Supabase usage in frontend
No SQLite
No AI usage in any phase unless explicitly introduced in Phase 6
No feature expansion outside defined scope
No speculative abstractions
No merging to main branch
Each phase must be implemented in its own branch
Commit only when phase is fully working end-to-end

If unsure → choose the simplest implementation that satisfies the spec.

---

# 1. Product Definition

Study Buddy is a low-friction activation system.

It is not:

* a planner
* a productivity dashboard
* a task management system
* a gamified study tool

It is:

A system that helps the user begin.

Core question:

What is the smallest realistic thing the user can do right now?

All implementation decisions must support this.

---

# 2. UX & Design System

## 2.1 Design Direction

Discord-inspired, but restrained.

Must include:

* dark theme
* layered surfaces
* soft contrast
* clear hierarchy
* minimal noise

Must avoid:

* gamer aesthetics
* neon colors
* dashboards
* data overload
* urgency signals

---

## 2.2 Design Tokens

```ts
export const colors = {
  bg: "#1e1f22",
  panel: "#2b2d31",
  text: "#ffffff",
  muted: "#b5bac1",
  accent: "#5865F2"
};
```

---

## 2.3 Core UX Rules

* Show ONE action at a time
* Avoid forcing decisions
* No guilt messaging
* Abort is neutral, not failure

---

# 3. System Architecture

Frontend: Next.js (App Router, TypeScript)
Backend: FastAPI
Database: Supabase PostgreSQL
Development: MCP access to Supabase

---

# 4. Database (Supabase)

## 4.1 Schema

```sql
-- subjects
create table subjects (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  color text not null,
  icon text not null
);

-- tasks
create table tasks (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  subject_id uuid references subjects(id),
  created_at timestamptz default now(),
  is_completed boolean default false
);

-- subtasks
create table subtasks (
  id uuid primary key default gen_random_uuid(),
  task_id uuid references tasks(id) on delete cascade,
  title text not null,
  difficulty_level int not null,
  is_completed boolean default false
);

-- sessions
create table sessions (
  id uuid primary key default gen_random_uuid(),
  started_at timestamptz default now(),
  ended_at timestamptz,
  task_id uuid references tasks(id),
  subtask_id uuid references subtasks(id),
  planned_duration_minutes int,
  actual_duration_minutes int,
  was_completed boolean default false,
  was_aborted boolean default false
);

-- attempts
create table attempts (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references sessions(id),
  difficulty_level int,
  outcome text
);
```

---

## 4.2 Seed

```sql
insert into subjects (name, color, icon) values
('Math', '#5865F2', 'calculator'),
('English', '#57F287', 'book'),
('Swedish', '#FEE75C', 'language'),
('Science', '#EB459E', 'flask');
```

---

# 5. Backend — Core Structure

```text
backend/app/
  main.py
  api/routes/
  api/schemas/
  domain/engines/
  domain/services/
  infrastructure/db/
  infrastructure/repositories/
```

---

# 6. Domain Logic (Phase Foundation)

## 6.1 SubTaskEngine

```python
def generate_subtask(title: str):
    t = title.lower()

    if "write" in t:
        return {"title": "Write 3 sentences", "difficulty": 1}
    if "read" in t:
        return {"title": "Read 1 page", "difficulty": 1}
    if "math" in t:
        return {"title": "Solve 2 problems", "difficulty": 1}

    return {"title": "Work for 5 minutes", "difficulty": 1}
```

---

## 6.2 DifficultyReducer (Phase-aware)

```python
def reduce(subtask, context=None):
    return subtask
```

---

## 6.3 SessionManager

```python
async def create_session(conn, task_id, subtask_id):
    return await conn.fetchrow("""
        insert into sessions (task_id, subtask_id, planned_duration_minutes)
        values ($1, $2, 10)
        returning *
    """, task_id, subtask_id)
```

---

# 7. API (Complete Contract)

Must exist in Phase 1:

POST /tasks
GET /tasks
POST /tasks/{id}/start
POST /sessions/{id}/complete
POST /sessions/{id}/abort

Add later:

GET /next

---

# 8. Frontend — Structure

```text
frontend/
  app/
  components/
  services/
  hooks/
  types/
```

---

# 9. PHASE EXECUTION

---

# PHASE 1 — Core Start Flow

## Build

Backend:

* DB connection
* Task CRUD
* SubTaskEngine (static)
* DifficultyReducer (static)
* SessionManager
* API endpoints

Frontend:

* dark layout
* task form
* task list
* session view

## Forbidden

* subjects UI
* adaptive logic
* analytics
* AI
* dashboards

## Done When

* user can start task and see ONE instruction
* session can complete/abort
* Supabase persists data

---

# PHASE 2 — Structure

## Build

Backend:

* Subject support
* Subtask persistence

Frontend:

* subject colors/icons
* improved list UI

## Forbidden

* filters
* planning tools

## Done

* subjects work end-to-end

---

# PHASE 3 — Adaptive Logic

## Build

Backend:

* Attempt tracking
* adaptive DifficultyReducer:

```python
if recent_aborts > 2:
    difficulty = 1
elif recent_completions > 3:
    difficulty = min(difficulty + 1, 5)
```

* GET /next

## Forbidden

* AI
* black box logic

## Done

* behaviour affects next steps

---

# PHASE 4 — UX Refinement

## Build

Frontend:

* better start flow
* smoother transitions
* improved wording
* mobile polish

## Forbidden

* new features

## Done

* friction reduced

---

# PHASE 5 — Personalisation

## Build

Backend:

* duration adjustment
* task prioritisation

## Forbidden

* social features
* complex settings

## Done

* feels personalised

---

# PHASE 6 — Stabilisation

## Build

* error handling
* tests
* performance improvements

Optional (ONLY IF SAFE):

* minimal AI assist (strictly bounded)

## Forbidden

* feature creep

## Done

* existing behaviour is more reliable under failure and concurrency

---

# PHASE 7 — System Contracts and Enforcement

## Goal

Define the real system boundaries and enforce their contracts.

## Build

* boundary DTO validation at the backend API edge
* machine-readable API contract surface
* `/health` endpoint for process liveness
* `/ready` endpoint for database and dependency readiness
* consistent backend error contract
* explicit definition of done tied to a runnable user flow

## Rules

* contracts must be enforced, not only documented
* boundary validation belongs at the boundary layer, not inside business logic
* invalid input and invalid contract output must fail predictably

## Done

* no critical contract exists only as prose
* health and readiness endpoints exist and are tested
* at least one deliberate contract violation fails immediately and clearly

---

# PHASE 8 — Validated Runtime Contract

## Goal

Eliminate ambiguous runtime configuration and fail early on invalid setup.

## Build

* typed backend config validation before application boot
* typed frontend config validation at the build/runtime boundary
* one canonical runtime contract for dev, test, and production
* mechanical compatibility checks between frontend and backend runtime assumptions
* removal of silent fallback configuration for required values

## Rules

* no required setting may rely on a hidden default that masks failure
* frontend and backend may not drift silently on ports, origins, or required env vars
* config validation must live at startup/build boundaries

## Done

* invalid config prevents startup
* no conflicting config definitions remain across layers
* config errors fail before user interaction or API calls

---

# PHASE 9 — Database Ownership and Lifecycle

## Goal

Make schema, migrations, seeds, and test database state repository-owned and reproducible.

## Build

* one committed migration strategy
* explicit schema source of truth
* deterministic migrations for the current system
* idempotent seed strategy for required subjects
* isolated and reproducible test database lifecycle
* integration of migrations and seeds into local bootstrap and test setup
* explicit migration lifecycle discipline

## Rules

* schema ownership must be explicit
* missing schema or seed state must fail explicitly
* frontend may not compensate for missing required seed data

## Done

* a fresh database can be created from repository-owned assets only
* seed state is deterministic and repeatable
* tests run against isolated database instances
* missing schema or seed prerequisites fail immediately and specifically

---

# PHASE 10 — CI Reproducibility Gate

## Goal

Make reproducibility a system property enforced in CI.

## Build

* CI bootstrap for database creation, migrations, and seeds
* CI startup of backend services
* readiness gating before verification runs
* CI execution of backend integration tests
* CI execution of minimal end-to-end smoke tests

## Rules

* CI must use the same essential assumptions as local development
* tests may not start before readiness passes
* broken bootstrap must fail the pipeline immediately

## Done

* CI bootstrap requires no manual intervention
* local and CI drift causes explicit failure
* reproducibility is proven beyond local development only

---

# PHASE 11 — Backend Integration Proof

## Goal

Prove backend correctness at the API and persistence boundary with no mocks.

## Build

* integration tests against the real API and real database lifecycle
* coverage for subjects load, tasks list, task create, task start, and session resolution
* validation of health, readiness, and seed expectations
* clear failure attribution to backend or database only

## Rules

* no mocks for the core API plus database proof path
* failures must isolate backend or database faults clearly
* boundary contract violations must be caught explicitly

## Done

* the core backend flow is proven against a real database
* at least one deliberate regression produces a clear isolated failure

---

# PHASE 12 — Minimal End-to-End Smoke

## Goal

Prove the full browser-to-backend-to-database wiring through one minimal user flow.

## Build

* browser-driven smoke path for:
  * app load
  * subject load
  * task creation
  * task start
  * session completion
* reuse of the same bootstrap and readiness assumptions validated earlier

## Rules

* keep the smoke suite intentionally small
* failures must indicate wiring problems, not broad ambiguity
* do not expand beyond the core user flow

## Done

* the full primary flow works end to end
* the smoke suite remains deterministic and diagnostically useful

---

# PHASE 13 — Frontend State Model Aligned to Contracts

## Goal

Make the frontend resilient through explicit, contract-driven resource state.

## Build

* independent state slices for `subjects`, `tasks`, and `nextTask`
* explicit `loading`, `data`, and `error` states per resource
* progressive rendering instead of all-or-nothing page boot
* alignment of frontend states with real backend contract states only

## Rules

* frontend may not invent client-only business states to hide backend ambiguity
* one failing resource may not collapse the full page
* state modelling belongs in application state, not scattered component hacks

## Done

* the UI reflects actual system state rather than guesses
* broken backend assumptions fail visibly and are debuggable
* partial failure does not break the entire user experience

---

# PHASE 14 — Observability for Runtime and Verification

## Goal

Make runtime and test failures attributable and diagnosable.

## Build

* structured backend logging
* request logging
* startup and database failure logging
* visible frontend failure states
* bounded error boundary behaviour where needed
* diagnostics that support failed integration and end-to-end runs

## Rules

* no silent failures in the critical path
* observability must remain pragmatic and architecture-safe
* failures must be attributable to a layer

## Done

* runtime failures are visible and attributable
* failed verification runs provide enough signal to debug without guesswork

---

# 10. Frontend Components (Phase 1 Exact)

## TaskForm

* input
* submit → POST /tasks

## TaskList

* render tasks
* start button → POST /start

## SessionView

* show subtask
* complete/abort buttons

---

# 11. API Client

```ts
const BASE = "http://localhost:8000";
```

Must include:

* getTasks
* createTask
* startTask
* completeSession
* abortSession

---

# 12. Testing (Required from Phase 3)

Must include:

* subtask generation tests
* difficulty reduction tests
* session logic tests

---

# 13. Final Instruction

Do not build more.

Do not optimise prematurely.

Do not expand scope.

Do not move logic into frontend.

Do not introduce AI.

Build exactly this system.

