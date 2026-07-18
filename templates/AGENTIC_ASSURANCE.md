# OpenDevs Agentic Assurance

> **Placement:** Copy this file to the root of an adopting repository as `AGENTIC_ASSURANCE.md`.
>
> **Upstream:** `MosslandOpenDevs/agentic-assurance-profile`
>
> **Purpose:** Connect this repository to the shared OpenDevs assurance profile without duplicating the upstream standard locally.

---

## 1. Adoption declaration

This repository adopts the **OpenDevs Agentic Assurance Profile** for software produced or maintained substantially by AI agents.

The profile complements—not replaces—the repository's existing mechanisms:

- `AGENTS.md` for persistent agent instructions;
- OpenSpec, Spec Kit, ADR/RFC, issues, or another established change workflow;
- tests, static analysis, CI, deployment controls, and runtime monitoring;
- project-specific security, privacy, data-governance, and operational policies.

The working chain is:

```text
Intent → Claims → Invariants → Enforcement → Evidence → Residuals
```

The pinned upstream profile defines the terms and generic obligations. This file defines how this repository adopts and applies them.

---

## 2. Pin the upstream profile

Create `.agentic-assurance/adoption.yaml`:

```yaml
upstream:
  repository: MosslandOpenDevs/agentic-assurance-profile
  version: REPLACE_WITH_PINNED_VERSION
  # Before the first tagged release, use: unreleased
  commit: REPLACE_WITH_FULL_40_CHARACTER_COMMIT_SHA

project:
  name: REPLACE_WITH_PROJECT_NAME
  repository: REPLACE_WITH_OWNER_AND_REPOSITORY
  human_owner: REPLACE_WITH_PERSON_OR_GOVERNING_BODY

profiles:
  - core
  # Add only after assessment:
  # - service
  # - trust-critical
  # - data-curation
  # - agent-runtime
  # - archived

# layout: lite
# (single-file core layout — put purpose/non-goals/invariants/residuals in
#  .agentic-assurance/assurance.yaml; see templates/assurance.yaml. Selecting
#  profiles beyond core requires the default split layout.)

# components:
#   authentication:
#     paths: [ "src/auth/**", "migrations/session_*" ]   # required, gitwildmatch-style globs
#     invariants: [ REPLACE_WITH_INVARIANT_IDS ]           # required, existing invariant IDs
#     tests: [ "tests/auth/**" ]                           # optional, informational in this release
# (optional impact-routing map — wires code paths to the invariant IDs they
#  protect. On pull requests, the drift check warns when a component's paths
#  change without its invariants being addressed; see docs/ADOPTION.md §3.7.)

specification_workflow:
  system: existing
  # Examples: openspec, spec-kit, adr-rfc, existing, minimal
  root: REPLACE_WITH_SPECIFICATION_PATH

paths:
  system: assurance/SYSTEM.md
  invariants: assurance/INVARIANTS.yaml
  claims: assurance/CLAIMS.yaml
  defeaters: assurance/DEFEATERS.yaml
  residuals: assurance/RESIDUALS.yaml
  threat_model: assurance/THREAT_MODEL.md
  evidence: assurance/evidence
```

The full commit SHA is the normative pin. A branch such as `main` MUST NOT be the sole reference.

Agents MUST NOT update the pin silently. An upstream upgrade requires a dedicated change with impact analysis.

---

## 3. Authority and precedence

When sources disagree, use this order:

1. human-approved project intent and non-goals;
2. the pinned upstream assurance profile;
3. human-approved local claims, invariants, decisions, and residual acceptances;
4. the active change specification;
5. implementation and tests as evidence of current behavior—not automatic proof of intended behavior.

Current production behavior is not a specification by itself.

An agent MUST report conflicts among intent, profile obligations, local artifacts, code, tests, and observed behavior. It MUST NOT silently rewrite one to match another.

Only a named human owner or governing body may approve:

- product intent and non-goals;
- critical invariants;
- public claim wording and limitations;
- weakening of a critical control or proof obligation;
- acceptance of critical residual risk.

---

## 4. Required local artifacts

Keep generic rules upstream and project truth local. Two layouts satisfy PROFILE.md §6.1.

**Lite layout** — the minimum for `core`. Declare it with `layout: lite` in `adoption.yaml`:

```text
AGENTS.md
AGENTIC_ASSURANCE.md
.agentic-assurance/
├── adoption.yaml     # with `layout: lite`
└── assurance.yaml    # purpose, non-goals, invariants, residuals in one file
```

`assurance.yaml` (start from `templates/assurance.yaml`) carries purpose, non-goals, residuals, and optionally invariants and defeaters. Its optional `system` section satisfies the system-description obligation; when absent, keep a separate `SYSTEM.md` at the path in `paths.system`. Section items use exactly the same shapes as the split registers, so graduating is a copy that preserves IDs. Selecting any profile beyond `core` requires the split layout.

**Split layout** — the default (no `layout` field), and required from `service` onward:

```text
AGENTS.md
AGENTIC_ASSURANCE.md
.agentic-assurance/
└── adoption.yaml
assurance/
├── SYSTEM.md
└── RESIDUALS.yaml
```

Add when applicable:

```text
assurance/
├── INVARIANTS.yaml   # recommended at core; required from `service`
├── CLAIMS.yaml
├── DEFEATERS.yaml
├── THREAT_MODEL.md
├── decisions/
├── reviews/
└── evidence/
```

An invariant register is what anchors the profile's regression protection, so most adopters will want one even at `core` — both pilot adoptions did — but it becomes an obligation only from the `service` profile (PROFILE.md §6.2). In the lite layout that register is the `invariants` section of `assurance.yaml`; in the split layout it is `assurance/INVARIANTS.yaml`.

Existing repository conventions MAY be reused instead of these exact paths. Record the mapping in `adoption.yaml`.

Do not copy the complete upstream profile into this repository. Local duplication creates an untracked fork and future semantic drift.

---

## 5. Profile selection

Use the smallest applicable set:

| Profile | Applies to |
|---|---|
| `core` | Any repository substantially produced or maintained by AI agents |
| `service` | Deployed applications, APIs, workers, websites, or stateful backends |
| `trust-critical` | Security, privacy, identity, authorization, financial, governance, or public-verifiability claims |
| `data-curation` | Externally sourced, editorial, scored, classified, or recommended data |
| `agent-runtime` | Model-driven agents or workflows executing in production |
| `archived` | Reference-only repositories with no active operation or development |

An agent may propose profiles, but the proposal remains provisional until reviewed by the human owner.

---

## 6. First adoption workflow

Initial adoption is a repository-archaeology task, not a feature task.

### 6.1 Discover before creating

Inspect and reuse existing:

- agent instruction files;
- specs, ADRs, RFCs, issue and PR templates;
- test, CI, schema, migration, scanner, and release commands;
- architecture, privacy, transparency, threat-model, and operations documents.

Do not introduce a second competing specification framework when an adequate one already exists.

### 6.2 Reconstruct the as-built system read-only

Before changing functional code, document:

1. purpose, users, scope, and non-goals;
2. domain entities, identifiers, and state transitions;
3. trust boundaries and external dependencies;
4. public claims and user-visible promises;
5. candidate invariants;
6. current enforcement mechanisms;
7. current verification and runtime evidence;
8. ambiguous or accidental behavior;
9. counterevidence, limitations, and residual risks.

Classify every material conclusion as:

- `VERIFIED` — reproducible evidence supports it;
- `INFERRED` — indirect evidence supports it;
- `UNKNOWN` — evidence is insufficient;
- `CONTRADICTED` — evidence conflicts with the claim or intended behavior.

Each non-`UNKNOWN` conclusion must cite concrete evidence: file and line, database constraint, test name, command output, endpoint response, artifact digest, deployment record, or runtime metric.

An AI-generated explanation is not evidence by itself. Committed prose inherits this rule when its authorship is agent-assisted (check the introducing commit's co-authorship trailers with `git blame`): cite such text as a description of behavior, never as human intent. The check is one-directional — an agent marker disqualifies; the absence of one proves nothing, since many agents leave no marker. Intent authority comes from a human act — a reviewed merge or a recorded review outcome — not from who typed the text.

### 6.3 Human intent review

Before broad remediation or refactoring, obtain human review of:

- purpose and non-goals;
- critical claims and invariants;
- behavior classified as `INTENDED`, `ACCIDENTAL`, `UNKNOWN`, or `DEPRECATED`;
- public claim limitations;
- critical residual acceptance.

### 6.4 Remediate in scoped changes

After intent review, address missing controls and evidence through separate, reviewable changes. Do not combine archaeology, feature work, security audit, broad refactoring, and remediation into one change unless explicitly scoped that way.

---

## 7. Material change workflow

A material change affects externally visible behavior, persistent data, authentication, authorization, privacy, security, billing, governance, recommendations, classification, migrations, deployment, public claims, or critical dependencies.

Before implementation, the active change artifact must state:

1. intent and non-goals;
2. affected claims and invariants;
3. before/after behavior;
4. failure and abuse cases;
5. migration and rollback;
6. observability;
7. required deterministic evidence;
8. independent verification requirements;
9. expected new or changed residuals.

Use the repository's existing specification workflow. Do not duplicate the same change in parallel document systems.

Preferred sequence:

```text
specify
  → review intent and critical obligations
  → implement enforcement
  → run deterministic verification
  → perform independent contradiction search
  → bind evidence to revision/deployment
  → update residuals
  → release decision
```

---

## 8. Evidence and residual rules

- **Tests verify; controls enforce.** A critical invariant should have both.
- “All checks passed” is not evidence unless the underlying results are linked and reproducible.
- Evidence should be bound to a commit SHA, artifact digest, or deployment identifier.
- Line coverage alone is not assurance coverage. Prefer claim coverage, critical-invariant coverage, unresolved defeaters, residual age, and runtime-evidence freshness.
- A **defeater** is a concrete reason a claim may be false or incomplete.
- A **residual** is a known limitation, unverified assumption, accepted inconsistency, unsupported condition, or remaining doubt.
- Residuals are expected. Hidden residuals are not.
- Do not close a residual merely because no recent failure was observed.
- Do not claim “bug-free,” “fully secure,” or “completely verified” without a precisely bounded and defensible proof basis.

For critical security, privacy, authorization, financial, governance, or data-integrity work:

1. audit in a read-only context;
2. record findings before remediation;
3. remediate in a separate context;
4. re-verify with a third context or deterministic suite.

The same agent context must not be the sole spec author, implementer, auditor, remediator, and final judge of a critical change.

---

## 9. Public disclosure and GitHub work tracking

For a public repository, assurance artifacts are a sanitized public view, not the complete private security record.

This repository MUST NOT publish secrets, personal data, private evidence, actionable details of an unpatched vulnerability, or privileged topology that materially lowers attack cost.

Use the following routing rule:

- generic profile changes belong in the upstream profile repository;
- project-specific non-sensitive adoption or conformance work belongs in this repository's Issues;
- suspected exploitable or sensitive findings belong in GitHub Private Vulnerability Reporting, a draft Security Advisory, or another approved restricted channel;
- sanitized documentation MAY be published after remediation and coordinated disclosure.

Durable assurance artifacts describe current project state. GitHub Issues track work required to change or clarify that state.

Claims, invariants, defeaters, and residuals MUST use stable semantic IDs independent of GitHub Issue numbers. Issues and pull requests SHOULD reference affected IDs.

Closing an Issue or merging code does not by itself resolve an assurance item. Required controls, evidence, and durable artifact updates must also be complete. Use a closing keyword such as `Closes #123` only when the pull request satisfies the Issue's full acceptance criteria.

When disclosure safety is uncertain, route privately first.

---

## 10. Prohibited agent behavior

An agent MUST NOT:

- redefine intent or non-goals without approval;
- label existing behavior `INTENDED` merely because it exists;
- weaken, delete, skip, or rewrite a failing test solely to obtain a green build;
- weaken an invariant, control, or evidence obligation without an explicit change record;
- fabricate test results, scanner output, runtime evidence, citations, or file references;
- hide contradictions, warnings, unknowns, or unresolved findings in a summary;
- claim an audit is independent when it reused the implementation context as its sole basis;
- silently upgrade the upstream profile pin;
- duplicate and modify the upstream profile as an untracked local fork;
- expose secrets, personal data, privileged topology, or actionable unresolved attack paths in public artifacts;
- accept a critical residual on behalf of the human owner.

When certainty is unavailable, record `UNKNOWN`, a defeater, or a residual. Do not invent confidence.

---

## 11. Root `AGENTS.md` integration

Add this section near the beginning of the root `AGENTS.md`:

```markdown
## OpenDevs Agentic Assurance

This repository adopts the OpenDevs Agentic Assurance Profile pinned in
`.agentic-assurance/adoption.yaml`.

Before any material change, read:

1. `AGENTIC_ASSURANCE.md`;
2. `.agentic-assurance/adoption.yaml`;
3. the project system specification and non-goals;
4. affected claims, invariants, defeaters, and residuals;
5. the active change specification.

Human-approved project intent governs project purpose. The pinned upstream
profile governs generic assurance obligations. Current implementation behavior
is not automatically intended behavior.

Do not silently weaken tests, controls, invariants, evidence obligations, or the
upstream pin. Report conflicts and unresolved uncertainty explicitly.
```

Nested `AGENTS.md` files may impose stricter local rules but must not weaken this adoption.

---

## 12. Expected initial adoption output

When first applying this file to an existing repository, produce a reviewable proposal containing:

1. proposed profiles and rationale;
2. existing workflows and files to reuse;
3. proposed local artifact mapping;
4. as-built system summary;
5. draft claims and invariants;
6. enforcement and evidence gaps;
7. `INTENDED`, `ACCIDENTAL`, `UNKNOWN`, and `DEPRECATED` behavior candidates;
8. initial defeaters and residuals;
9. staged remediation plan;
10. exact files created or changed;
11. a handoff summary for the human owner, in the owner's working language, that states nothing is decided, lists each pending decision in plain language, and instructs that the pull request must not be merged until those decisions are made.

Do not describe adoption as complete merely because the documents were created. In the handoff summary, the drafting agent must not describe its result as "settled" or "complete" — completion language is reserved for the human owner's acceptance.

Initial adoption is complete only when the upstream pin, human-approved intent, critical claims and invariants, evidence links, explicit unknowns, and residual ownership are all present in the repository's normal change process.

Completion means the system's promises, controls, evidence, and remaining doubt are inspectable. It does not mean the system is bug-free or universally secure.
