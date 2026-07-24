# OpenDevs Agentic Assurance

> **Placement:** Copy this file to the root of an adopting repository as `AGENTIC_ASSURANCE.md`.
>
> **Upstream:** `MosslandOpenDevs/agentic-assurance-profile`
>
> **Purpose:** Connect this repository to the shared OpenDevs assurance profile without duplicating the upstream standard locally.

Before any material change, read:

1. `AGENTIC_ASSURANCE.md`;
2. `.agentic-assurance/adoption.yaml`;
3. the project system artifact and applicable non-goals;
4. affected claims, invariants, defeaters, and residuals, where applicable;
5. the active change specification, when applicable.

---

## 1. Adoption declaration

This repository adopts the **OpenDevs Agentic Assurance Profile** for software produced or maintained substantially by AI agents.

For an active adoption, the profile complements—not replaces—the repository's existing mechanisms, where applicable:

- `AGENTS.md` for persistent agent instructions;
- OpenSpec, Spec Kit, ADR/RFC, issues, or another established change workflow;
- tests, static analysis, CI, deployment controls, and runtime monitoring;
- project-specific security, privacy, data-governance, and operational policies.

The active working chain is:

```text
Intent → Claims → Invariants → Enforcement → Evidence → Defeaters → Residuals → Human acceptance
```

The exclusive `archived` path does not fabricate that active chain. It applies only when the repository is retained solely for historical reference, is not supported or intended for current use, and has no active operation, functional maintenance, or feature development. It retains the pin and root agent instructions, then records the four PROFILE.md §6.6 historical facts in the mapped system artifact for owner confirmation. Initial adoption and factual corrections or upkeep to the pin, stage, review record, and agent instructions are archival-assurance metadata work, not functional maintenance.

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
  - REPLACE_WITH_CLASSIFIED_PROFILE
  # Classify from what the repository IS and promises (docs/ADOPTION.md §4.0);
  # replace the placeholder above with the classified set — validation fails
  # until it is filled. For an active adopter, use `core` only when no
  # specialized trigger fires. If any fire, list all fired specialized profiles
  # and normally omit `core`; they inherit all core obligations whether or not
  # `core` is written:
  # - service
  # - trust-critical
  # - data-curation
  # - agent-runtime
  # - archived  # exclusive alternative — declare alone

# layout: lite
# (single-file core layout — put purpose/non-goals, a system description,
#  invariants, and residuals in
#  .agentic-assurance/assurance.yaml; start from templates/assurance.minimal.yaml
#  (expanded standard-field reference: templates/assurance.yaml). Any profile
#  other than core requires the default split layout.)

# components:
#   authentication:
#     paths: [ "src/auth/**", "migrations/session_*" ]   # required, gitwildmatch-style globs
#     invariants: [ REPLACE_WITH_INVARIANT_IDS ]           # required, existing invariant IDs
#     tests: [ "tests/auth/**" ]                           # optional, informational in this release
# (optional impact-routing map — wires code paths to the invariant IDs they
#  protect. On pull requests, the drift check warns when a component's paths
#  change without its invariants being addressed; see docs/ADOPTION.md §3.7.)

# adoption_stage: DRAFT
# (optional self-declared stage, enforced as declared: DRAFT (schema, required
#  artifacts, and applicable semantic checks pass; register placeholders are
#  allowed — the adoption declaration itself must be complete, an archived
#  SYSTEM artifact must be non-empty, a VERIFIED critical invariant must name
#  enforcement and verification references, and under `service` every critical
#  invariant must name both regardless of conclusion, at every stage)
#  → HUMAN_REVIEWED (active registers completed; archived SYSTEM markers
#  replaced; non-future review recorded; active critical intent recorded,
#  with UNKNOWN allowed)
#  → CONFORMANT
#  (active review dates fresh; critical intent neither UNKNOWN nor ACCIDENTAL;
#  at least one non-future attributable approval on/after the review date).
#  Absent means DRAFT; declaring a stage you do not meet fails validation;
#  see docs/ADOPTION.md §3.8.)

# Required by every active profile. Under `archived`, keep this optional block
# only when a real archival-record workflow applies; otherwise delete it rather
# than inventing an active change workflow.
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

The full commit SHA is the normative pin. A branch such as `main` MUST NOT be the sole reference. If this declaration is placed at a custom path, pass that exact path as the validator workflow's `adoption-file`, substitute it in the assurance reading order in both root files, and keep it under the repository's effective human-owner review mechanism (including `CODEOWNERS` when used); see §11.

Record the concrete pin values (version and commit) **only** in the adoption declaration, at `.agentic-assurance/adoption.yaml` or the workflow's configured custom `adoption-file` path. Do not copy them into the prose of this file or elsewhere: a duplicated pin is not checked by the structure validator and silently goes stale on the next upgrade (a v0.2.0 pilot left a superseded version and commit in its `AGENTIC_ASSURANCE.md` this way). Refer to the configured adoption declaration, not to a duplicated set of pin values.

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

Keep generic rules upstream and project truth local. Active adopters use the two layouts below to satisfy PROFILE.md §6.1; the exclusive `archived` profile uses the split layout for §6.6.

**Lite layout** — the minimum for `core`. Declare it with `layout: lite` in `adoption.yaml`:

```text
AGENTS.md
AGENTIC_ASSURANCE.md
.agentic-assurance/
├── adoption.yaml     # with `layout: lite`
└── assurance.yaml    # purpose, non-goals, system, invariants, residuals
```

`assurance.yaml` (start from `templates/assurance.minimal.yaml` — the required minimum; `templates/assurance.yaml` is an expanded reference showing the standard optional fields, optional `defeaters`, and local `extensions` namespace) carries purpose, non-goals, a system description (inline or separately mapped), invariants, and residuals — at least one invariant and one residual — and optionally defeaters. Its optional `system` section satisfies the system-description obligation; when absent, keep a separate `SYSTEM.md` at the path in `paths.system`. Register schemas permit project-local entry fields, so the expanded reference does not claim to enumerate every extension. Any profile other than `core` requires the split layout.

When graduating to an **active specialized profile**, move each present register array unchanged into its split register so every ID survives. Move inline `system` prose into the artifact mapped by `paths.system`; preserve lite `purpose` and `non_goals` there or in another owner-approved local intent artifact, and preserve or deliberately relocate `extensions`. Remove `layout: lite` only after all of that content is represented. When reclassifying as **`archived`**, do not treat that active migration as the archived contract: write all four PROFILE.md §6.6 facts in the mapped system artifact and obtain owner confirmation. Prior active registers may remain as optional historical material, but they do not supply or substitute for those facts. Remove `layout: lite` only after the applicable target contract is complete.

**Split layout** — the default (no `layout` field), and required for every specialized or `archived` profile:

```text
AGENTS.md
AGENTIC_ASSURANCE.md
.agentic-assurance/
└── adoption.yaml
assurance/
├── SYSTEM.md
├── INVARIANTS.yaml
└── RESIDUALS.yaml
```

Add when applicable:

```text
assurance/
├── CLAIMS.yaml
├── DEFEATERS.yaml
├── THREAT_MODEL.md
├── decisions/
├── reviews/
└── evidence/
```

The exclusive `archived` profile also uses the split convention but does not inherit the active §6.1 invariant and residual obligations: keep the root files, adoption declaration, and the system artifact mapped by `paths.system`; complete the archived-only §0 prompts in `templates/SYSTEM.md`. The interim validator requires that artifact to be non-empty at every stage and, at `HUMAN_REVIEWED` and `CONFORMANT`, additionally rejects unchanged archived prompt markers; it does not establish truth or semantically parse the four facts. Do not add empty active registers merely to imitate the tree above.

An invariant register is what anchors the profile's regression protection, and is required from `core` — at least one invariant, the properties that must remain true (PROFILE.md §6.1). In the lite layout that register is the `invariants` section of `assurance.yaml`; in the split layout it is `assurance/INVARIANTS.yaml`.

Existing repository conventions MAY be reused instead of these exact paths. Record the mapping in the configured adoption declaration, and keep that declaration, every custom mapped artifact, `specification_workflow.root`, `human_review.record`, `security.policy`, and `security.public_assurance_root` under the repository's effective human-owner review mechanism; add them to `CODEOWNERS` when it supplies that boundary. For a tracked symlink at any such location, protect the lexical link itself (including retargeting), its resolved target, and the target's parent or containing tree; list all three in CODEOWNERS when used because it does not follow the validator's path resolution for you.

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
| `archived` | Repositories retained solely for historical reference, not supported or intended for current use, with no active operation, functional maintenance, or feature development |

An agent may propose profiles, but the proposal remains provisional until reviewed by the human owner.

Every active specialized profile inherits the `core` obligations in PROFILE.md §6.1. For an active classification, canonically declare `[core]` only when none applies; otherwise declare every fired specialized profile and omit `core` (listing it explicitly is allowed but changes no obligation). Declare `archived` alone: it replaces all active profiles, and its four §6.6 facts belong in the artifact mapped by `paths.system` (default `assurance/SYSTEM.md`).

---

## 6. First adoption workflow

Initial adoption is a repository-archaeology task, not a feature task. Active profiles follow the full workflow below; the exclusive `archived` profile follows the explicit narrower branches.

### 6.1 Discover before creating

Inspect and reuse existing:

- agent instruction files;
- specs, ADRs, RFCs, issue and PR templates;
- test, CI, schema, migration, scanner, and release commands;
- architecture, privacy, transparency, threat-model, and operations documents.

Do not introduce a second competing specification framework when an adequate one already exists.

### 6.2 Reconstruct the applicable record read-only

For an active profile, before changing functional code, document:

1. purpose, users, scope, and non-goals;
2. domain entities, identifiers, and state transitions;
3. trust boundaries and external dependencies;
4. public claims and user-visible promises;
5. candidate invariants;
6. current enforcement mechanisms;
7. current verification and runtime evidence;
8. intended, accidental, compatibility-preserving, unknown, or deprecated behavior;
9. counterevidence, limitations, and residual risks.

For `archived`, replace that active-system list with evidence that the repository is retained solely for historical reference, is not supported or intended for current use, and has no active operation, functional maintenance, or feature development, plus the remaining PROFILE.md §6.6 facts: historical purpose, known material limitations, and the last supported revision or release (or explicitly that none exists). Record all four facts in the system artifact mapped by `paths.system`; do not fabricate active registers merely to fill the active template tree.

Classify every material conclusion as:

- `VERIFIED` — reproducible evidence supports it;
- `INFERRED` — indirect evidence supports it;
- `UNKNOWN` — evidence is insufficient;
- `CONTRADICTED` — evidence conflicts with the claim or intended behavior.

Each non-`UNKNOWN` conclusion must cite concrete evidence: file and line, database constraint, test name, command output, endpoint response, artifact digest, deployment record, or runtime metric.

An AI-generated explanation is not evidence by itself. Committed prose inherits this rule when its authorship is agent-assisted (check the introducing commit's co-authorship trailers with `git blame`): cite such text as a description of behavior, never as human intent. The check is one-directional — an agent marker disqualifies; the absence of one proves nothing, since many agents leave no marker. Intent authority comes from a human act — a reviewed merge or a recorded review outcome — not from who typed the text.

### 6.3 Human owner review

For an active profile, before broad remediation or refactoring, obtain human review of:

- purpose and non-goals;
- critical claims and invariants;
- behavior classified as `INTENDED`, `ACCIDENTAL`, `COMPATIBILITY`, `UNKNOWN`, or `DEPRECATED`;
- public claim limitations;
- critical residual dispositions, including any acceptance or claimed resolution grounds.

For `archived`, the owner instead confirms the exclusive classification, the mapped system artifact, and each of the four §6.6 facts. Those confirmations replace the active-system decisions above.

### 6.4 Remediate in scoped changes

For an active profile, after intent review, address missing controls and evidence through separate, reviewable changes. Do not combine archaeology, feature work, security audit, broad refactoring, and remediation into one change unless explicitly scoped that way.

An `archived` adoption has no active remediation stage. Correct its reference-only eligibility/classification or historical facts before acceptance. Initial adoption and factual corrections or upkeep to assurance metadata do not themselves count as functional maintenance. Before renewed operation, functional maintenance, feature development, or functional remediation, reclassify the repository under every applicable active profile.

---

## 7. Material change workflow

A material change affects externally visible behavior, persistent data, authentication, authorization, privacy, security, billing, governance, recommendations, classification, migrations, deployment, public claims, or critical dependencies.

An `archived` repository MUST be reclassified under every applicable active profile before any such functional change or renewed operation, functional maintenance, or feature development. A correction limited to the archived classification or four §6.6 facts—or upkeep to its pin, stage, review record, or agent instructions—stays on the archived review path and requires owner confirmation where applicable.

Before implementation, the active change artifact must state:

1. intent and non-goals;
2. affected claims and invariants;
3. before/after behavior;
4. failure and abuse cases;
5. migration and rollback;
6. observability;
7. required deterministic evidence;
8. independent verification requirements;
9. expected new or changed residuals;
10. disclosure classification and public-versus-restricted routing.

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

- **Tests verify; controls enforce.** Every active severity-`critical` invariant recorded `VERIFIED` must name at least one enforcement and one verification reference. Under `service`, every critical invariant must name both regardless of conclusion; where no stricter profile rule applies, other critical invariants should have both.
- “All checks passed” is not evidence unless the underlying results are linked and reproducible.
- Evidence should be bound to a commit SHA, artifact digest, or deployment identifier.
- Line coverage alone is not assurance coverage. Prefer claim coverage, critical-invariant coverage, unresolved defeaters, residual age, and runtime-evidence freshness.
- A **defeater** is a concrete reason a claim may be false or incomplete.
- A **residual** is a known limitation, unverified assumption, accepted inconsistency, unsupported condition, or remaining doubt.
- Residuals are expected. Hidden residuals are not.
- An `ACCEPTED` residual names the human acceptor, a non-future acceptance date, and the rationale; a critical acceptance belongs to the human owner. A `RESOLVED` residual instead records its resolution grounds and remediation reference.
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
3. the project system artifact and applicable non-goals;
4. affected claims, invariants, defeaters, and residuals, where applicable;
5. the active change specification, when applicable.

Human-approved project intent governs project purpose. The pinned upstream
profile governs generic assurance obligations. Current implementation behavior
is not automatically intended behavior.

Do not silently weaken tests, controls, invariants, evidence obligations, or the
upstream pin. Report conflicts and unresolved uncertainty explicitly.
```

Copy this block verbatim into root `AGENTS.md`. If—and only if—the adoption declaration uses the workflow's custom `adoption-file`, replace `.agentic-assurance/adoption.yaml` with that same repository-relative path in this block in root `AGENTIC_ASSURANCE.md` and in its copy in root `AGENTS.md`; no other divergence is permitted.

Nested `AGENTS.md` files may impose stricter local rules but must not weaken this adoption.

---

## 12. Expected initial adoption output

When first applying this file to an existing active repository, produce a reviewable proposal containing:

1. proposed profiles and rationale;
2. existing workflows and files to reuse;
3. proposed local artifact mapping;
4. as-built system summary;
5. draft claims and invariants;
6. enforcement and evidence gaps;
7. `INTENDED`, `ACCIDENTAL`, `COMPATIBILITY`, `UNKNOWN`, and `DEPRECATED` behavior candidates;
8. initial defeaters and residuals;
9. staged remediation plan;
10. exact files created or changed;
11. a handoff summary for the human owner, in the owner's working language, that states nothing is decided, lists each pending decision in plain language, and instructs that the pull request must not be merged until those decisions are made.

Before handoff, the drafting agent SHOULD run any available local structure pre-flight over the files it created (see the upstream adoption instructions) and resolve or record any findings; a local pre-flight is a convenience, never the acceptance gate.

For the exclusive `archived` profile, produce the narrower reviewable proposal instead: evidence that the repository is retained solely for historical reference, is not supported or intended for current use, and has no active operation, functional maintenance, or feature development; the exclusive profile declaration and artifact mapping; all four §6.6 facts in the mapped system artifact; the exact files changed; and a handoff asking the owner to confirm both the reference-only eligibility/classification and each fact using `docs/REVIEW-GUIDE.md`. Do not fabricate empty active claims, invariants, defeaters, or residuals for an archived repository.

Do not describe adoption as complete merely because the documents were created. In the handoff summary, the drafting agent must not describe its result as "settled" or "complete" — completion language is reserved for the human owner's acceptance.

An active initial adoption is complete only when the upstream pin, human-approved intent, critical claims and invariants, evidence links, explicit unknowns, and residual ownership are all present in the repository's normal change process. An `archived` initial adoption is complete only when the owner confirms the exclusive classification and all four §6.6 facts in the mapped system artifact. The interim validator requires a non-empty artifact at every stage and additionally rejects unchanged archived template markers at `HUMAN_REVIEWED` and `CONFORMANT`, but those syntactic checks do not establish truth or structured completeness; stronger semantic enforcement remains deferred to [upstream issue #40](https://github.com/MosslandOpenDevs/agentic-assurance-profile/issues/40).

Completion means the system's promises, controls, evidence, and remaining doubt are inspectable. It does not mean the system is bug-free or universally secure.
