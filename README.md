# Hardened Copilot Agent Pack

This package contains a stricter multi-agent control system for VS Code and GitHub Copilot custom agents.

## Folder Structure

- `.github/AGENT-RUNTIME-RULES.md`
  Universal runtime law for all agents and subagents.

- `.github/agents/`
  Contains the hardened custom agent definitions:
  - `orchestrator.agent.md`
  - `planning.agent.md`
  - `intention.agent.md`
  - `coding.agent.md`
  - `verification.agent.md`
  - `governance-auditor.agent.md`
  - `testing.agent.md`

- `.github/skills/global-rules/SKILL.md`
  Shared global behaviour rules.

- `.github/skills/phase-artifacts/SKILL.md`
  Shared artifact contract rules.

- `implementation-docs/templates/`
  Templates for required repository artifacts.

## Intended Usage

1. Copy this package into the root of your repository.
2. Keep your master development document at `implementation-docs/devplan.md`.
3. Trigger the orchestrator with a phase command.
4. Let the orchestrator force the repository through planning, intention, coding, verification, governance audit, and testing.

## Notes

- The orchestrator does not implement.
- The governance auditor exists to police the other agents, not the product alone.
- The templates are there to reduce drift and make failures easier to detect.
