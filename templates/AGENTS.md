# Agent instructions

> **Placement:** Copy this file to the root of an adopting repository as `AGENTS.md`, or merge its sections into an existing `AGENTS.md`. Replace every `REPLACE_WITH_` placeholder in applicable project-specific sections. Under `archived`, delete or explicitly mark inapplicable project-specific lines; do not alter the verbatim OpenDevs block.
>
> **Normative source:** The "OpenDevs Agentic Assurance" section below is copied verbatim from `AGENTIC_ASSURANCE.md` §11 ("Root `AGENTS.md` integration"), which remains the normative source. If the two copies ever differ, §11 governs.

---

## OpenDevs Agentic Assurance

This repository adopts the OpenDevs Agentic Assurance Profile pinned in
`.agentic-assurance/adoption.yaml`.

Before any material change, read:

1. `AGENTIC_ASSURANCE.md`;
2. `.agentic-assurance/adoption.yaml`;
3. the project system artifact and applicable non-goals;
4. affected claims, invariants, defeaters, and residuals, where applicable;
5. the active change specification.

Human-approved project intent governs project purpose. The pinned upstream
profile governs generic assurance obligations. Current implementation behavior
is not automatically intended behavior.

Do not silently weaken tests, controls, invariants, evidence obligations, or the
upstream pin. Report conflicts and unresolved uncertainty explicitly.

---

## Project overview

REPLACE_WITH_ONE_PARAGRAPH_DESCRIPTION_OF_PURPOSE_USERS_AND_SCOPE

For an active split adoption, non-goals and the as-built system description live in `assurance/SYSTEM.md` or at the path recorded under `paths.system` in `.agentic-assurance/adoption.yaml`. Under `layout: lite`, `non_goals` lives in `.agentic-assurance/assurance.yaml`; the system description may be its optional `system` field or the separately mapped system artifact. Under the exclusive `archived` profile, the mapped system artifact instead records the four historical facts required by PROFILE.md §6.6.

## Build and test commands

```text
REPLACE_WITH_BUILD_COMMAND
REPLACE_WITH_TEST_COMMAND
REPLACE_WITH_LINT_OR_STATIC_ANALYSIS_COMMAND
```

Run the full test suite before describing a change as complete. Do not weaken, remove, skip, or rewrite a failing test solely to obtain a green build.

## Conventions

- Code style: REPLACE_WITH_CODE_STYLE_RULES_OR_FORMATTER_COMMAND
- Branches and commits: REPLACE_WITH_BRANCH_AND_COMMIT_CONVENTIONS
- Change workflow: REPLACE_WITH_SPECIFICATION_WORKFLOW — for an active adoption, must match `specification_workflow` in `.agentic-assurance/adoption.yaml`; under `archived`, delete this line if that optional block is absent, or describe the archival-record correction and active-reclassification rule
- Review: REPLACE_WITH_REVIEW_REQUIREMENTS

Nested `AGENTS.md` files may impose stricter local rules but must not weaken the assurance adoption above.
