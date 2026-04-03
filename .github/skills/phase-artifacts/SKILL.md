---
name: phase-artifacts
description: Exact artifact contracts for every document written into implementation-docs during phase execution.
---
# PHASE ARTIFACT CONTRACTS

All agents that write files into `implementation-docs/` must obey the matching template.

Required artifact set:
- `devplan.md`
- `current-phase.md`
- `phase-X-plan.md`
- `phase-X-intention-plan.md` when applicable
- `phase-X-verification-report.md`
- `phase-X-governance-audit.md`
- `phase-X-test-report.md`

## current-phase.md
Must match the template in `implementation-docs/templates/current-phase.template.md`

## phase-X-plan.md
Must match the template in `implementation-docs/templates/phase-plan.template.md`

## phase-X-intention-plan.md
Must match the template in `implementation-docs/templates/phase-intention.template.md`

## phase-X-verification-report.md
Must match the template in `implementation-docs/templates/phase-verification.template.md`

## phase-X-governance-audit.md
Must match the template in `implementation-docs/templates/phase-governance-audit.template.md`

## phase-X-test-report.md
Must match the template in `implementation-docs/templates/phase-test-report.template.md`

If a required section is missing, the artifact is malformed and the step is incomplete.
