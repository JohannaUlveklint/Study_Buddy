---
name: global-rules
description: Universal operating rules that all agents and subagents must obey before touching the repository.
---
# GLOBAL RULES

You operate in a deterministic multi-agent system.
You must follow instructions exactly.
You must not expand scope.
You must not improvise architecture.
You must not perform tasks assigned to other agents.
You must only use allowed tools.
You must read `.github/AGENT-RUNTIME-RULES.md` before relying on your own judgment.

# FILE CONTRACT

All durable outputs for planning, verification, governance, and testing must be written to:

`implementation-docs/`

No exceptions.

# FAILURE RULE

If input is missing, unclear, or invalid:
- stop
- report precisely
- do not guess
- do not invent fallback assumptions

# ARCHITECTURE RULES

- no business logic in frontend
- no direct Supabase usage in frontend
- no silent cross-layer drift
- no unauthorised dependency additions

# COMPLETION RULE

A task is not complete because work happened.
A task is complete only when the required artifact exists, required behaviour exists, and the state file has been updated.
