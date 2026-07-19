# Changelog

All notable changes to the OpenDevs Agentic Assurance Profile will be documented here.

## Unreleased

Nothing yet.

## v0.3.1 — 2026-07-19

Completes the register policy diff so a base-branch, human-reviewed
assurance item cannot silently disappear regardless of the form the change
takes — deletion, whole-register removal, or a status that closes it out.
From a fourth external review of v0.3.0. No schema changes; existing
adopters see only stricter drift-job findings, and only on pull requests
that actually remove reviewed assurance.

#### Fixed — register policy diff completeness

- **Whole-register removal is now caught (was fail-open).** The diff
  skipped a register entirely when the head branch lacked it, so deleting
  an optional register file (e.g. `INVARIANTS.yaml` under the `core`
  profile, where it is not a required file) erased every reviewed entry
  with no finding. A base register missing on the head is now a
  "register removed" finding listing the former IDs; an unreadable head
  register fails closed.
- **Closing dispositions are now caught.** A residual moved to `RESOLVED`,
  a defeater moved to `MITIGATED`/`RESOLVED`/`WITHDRAWN`, and a recorded
  `CONTRADICTED` status cleared (moving *away* from `CONTRADICTED`) each
  remove a tracked concern without deleting its ID; they are now findings,
  subject to the same stage-proportional acknowledgment. Re-opening and
  recording a new contradiction remain non-findings.
- **Claim basis removal is now caught.** Removing a claim's `evidence`,
  supporting `invariants`, or `limitations` items is flagged (parallel to
  the invariant evidence-removal check) — stripping a claim's basis is a
  mechanism change, not a wording change.

#### Security

- The drift job's assurance-diff step now runs `git` with
  `--literal-pathspecs` and screens pull-request-controlled `paths:` values
  through an in-tree containment check before using them as pathspecs or
  base-tree write targets (belt-and-suspenders with the validator's
  existing containment), and fails closed if `git diff` errors instead of
  proceeding with an empty diff.

## v0.3.0 — 2026-07-19

Trust-boundary honesty and register-level policy protection, from an
external review of v0.2.1. Minor release: the register schemas now reject
empty/whitespace-only semantic strings and profile-mandated registers must
be non-empty — theoretically breaking for adopters relying on vacuous
passes (none known).

#### Adopter impact / upgrade actions

- **Caller must pin a full SHA.** The workflow now rejects callers that
  reference it by tag or branch (`job.workflow_ref` must end in the
  workflow's own 40-hex SHA). Existing SHA-pinned callers are unaffected.
- The reusable workflow targets GitHub.com only (it relies on the
  `job.workflow_*` contexts, absent on GitHub Enterprise Server).
- `--repo-visibility` (CI passes it automatically): at `CONFORMANT`,
  `RESTRICTED`/`EMBARGOED` entries are errors only in public repositories;
  private repositories keep the standing warning (fixes the v0.2.1
  conflict with ADOPTION.md's private-repository allowance).
- Registers mandated by a profile must carry at least one entry
  (`residuals` for non-archived, `invariants` for `service`, `claims` for
  `trust-critical`); register schemas reject empty/whitespace-only
  semantic strings, matching the lite envelope.

#### Security / trust boundary

- **Trusted-checkout-first:** every job first verifies the workflow's own
  identity (`job.workflow_repository` == canonical, caller pinned by full
  SHA) and checks out that exact source; the hash-locked dependencies come
  from it, and the v0.2.1 version-pinned pyyaml bootstrap is gone — no
  install precedes the trusted checkout. `upstream.commit` must equal the
  workflow's own SHA, so the trusted checkout IS the pinned profile.
- **The caller-workflow boundary is now documented honestly** (workflow
  header + ADOPTION.md §3.4): a pull request can swap the caller's `@`
  reference or the caller itself — no reusable-workflow content can defend
  that; CODEOWNERS on `.github/workflows/` (already in the adopter
  bundle), organization Actions allow-lists, and organization rulesets
  with required workflows (Team/Enterprise) are the controls, and a green
  check is an input to human review, not a tamper-proof verdict.
- `actionlint` (digest-pinned image) added to self-check.

#### Changed

- **Register-level policy regression (stable-ID base/head diff)** in the
  drift job: deleted entries; invariant severity downgrades,
  status weakening (`VERIFIED`/`INFERRED` toward `UNKNOWN` —
  `CONTRADICTED` is an honesty upgrade, never flagged), `INTENDED` intent
  reclassified, enforcement/verification/evidence removed from
  high/critical invariants; claim status weakening and proof-tier
  downgrades; residual impact downgrades. Adoption-level findings gain
  `project.human_owner`, `paths.*`, and `security.public_assurance_root`
  changes.
- **Stage-proportional acknowledgment:** `Assurance policy change:` still
  downgrades findings to warnings at base-stage `DRAFT`, but from
  `HUMAN_REVIEWED` on findings stay errors even when acknowledged — the
  acknowledgment is a self-declaration (an agent can write it), so its
  force is capped by the stage the base declaration had asserted.
- The assurance diff is scoped by the `paths:` both declarations actually
  name — custom artifact locations now count toward per-component
  satisfaction; a missing base declaration emits a notice instead of
  silently skipping.
- `human_review.approvals` remains unverified against the forge API
  (deferred); GOVERNANCE.md now defines honest review classes
  (INDEPENDENTLY_REVIEWED / SOLE_OWNER_ATTESTED / AUTOMATION_VERIFIED) and
  records that releases currently ship as SOLE_OWNER_ATTESTED +
  AUTOMATION_VERIFIED.

#### Added

- `requirements.in` (lock regeneration input) committed.
- New tests covering the register diff, stage-proportional acknowledgment,
  visibility-aware disclosure, empty-register obligations, and the schema
  hardening.

## v0.2.1 — 2026-07-18

Security hardening of the reusable adopter CI plus honest-signal fixes,
from an external review of v0.2.0. No adoption-schema changes; both pilot
registers validate identically. All behavior changes land in surface area
no current adopter occupies (no adopter declares HUMAN_REVIEWED/CONFORMANT
or ships a component map yet), which is why this is a patch release.

### Adopter impact / upgrade actions

- **Recommended upgrade.** Re-pin to `v0.2.1` (`upstream.version`,
  `upstream.commit`, and the workflow `@` reference) to pick up the CI
  trust-boundary fix.
- **Check rename:** `assurance / conformance` is now
  `assurance / declared-stage` — update branch protection if you made it a
  required check. Rationale: the check is green whenever the *declared*
  stage is met (HUMAN_REVIEWED included), so the old name could be misread
  as a conformance statement.
- **Caller `on:` update recommended** (docs/ADOPTION.md §3.4): add
  `pull_request` types `[opened, synchronize, reopened, edited,
  ready_for_review]` — the drift check reads the PR description, and
  without `edited` a later description edit leaves a stale verdict.
- The reusable workflow now requires the caller's `@` reference to equal
  `upstream.commit` (this was already the documented rule; it is now
  enforced) and validates only against the canonical upstream
  `MosslandOpenDevs/agentic-assurance-profile` — fork adopters run their
  own copy with the `CANONICAL` constant changed.

### Security

- `adopter-validate.yml` no longer checks out the validator from a
  repository named in the pull-request-mutable adoption file. The validator
  is always checked out from the canonical upstream; the declared
  repository is validated as data (must equal the canonical upstream, else
  error), the commit must be a full 40-hex SHA (checked before any
  checkout), and the caller's pinned workflow SHA must match it. This
  closes a code-execution vector where a pull request could point CI at
  attacker-controlled validator code.
- Both workflows now set `permissions: contents: read`, use
  `persist-credentials: false` on every checkout, pin every action to a
  full commit SHA, and install dependencies from a universal hash-pinned
  lock (`requirements-ci.txt`, `pip install --require-hashes`). One
  deliberate exception: each adopter-validate job first bootstraps the
  pin reader with a version-pinned (not hash-pinned)
  `pip install "pyyaml==6.0.3" --no-deps` — the lock only exists after
  the pinned checkout that the pin reader itself enables.

### Changed

- **Stage self-downgrade protection.** The pull-request drift job now
  compares the adoption declaration against the base branch: a stage
  downgrade, profile removal, layout change, upstream pin change, component
  removal, or removal of a component's path globs / invariant IDs fails the
  job unless the PR description carries an explicit
  `Assurance policy change: <why>` line (which downgrades the findings to
  warnings). A PR flipping `CONFORMANT` back to `DRAFT` no longer slips
  through as a skipped check.
- **CONFORMANT now enforces the mechanically checkable subset of PROFILE
  §17:** no `critical` residual left `OPEN`, no `CONTRADICTED` claim, no
  `CONTRADICTED` critical invariant, every `VERIFIED` critical invariant
  carries non-empty `evidence`, and `RESTRICTED`/`EMBARGOED` entries are
  errors (still warnings at lower stages). ADOPTION.md §3.8 states the
  honest boundary: revision-bound evidence and claim-vs-evidence wording
  remain the human review's responsibility.
- **Per-component drift satisfaction.** Touching some assurance file no
  longer satisfies every touched component: in CI, the assurance diff must
  reference at least one of the component's invariant IDs (PR-body mention
  and the no-impact statement are unchanged). Standalone runs without
  `--assurance-diff` keep the coarse fallback.
- **Rename-safe change detection.** Changed files are computed with
  `--name-status -z`; a rename or copy counts both source and destination,
  so code cannot move out of a mapped path unseen.
- Validator findings are now emitted as GitHub annotations
  (`::error::`/`::warning::`) inside Actions, and the drift job writes an
  impact-routing table to the job summary — warn-first findings were
  previously easy to miss in raw logs.
- Lite envelope schema tightened: unknown top-level keys are rejected (a
  typo like `invarients` fails loudly; adopter-specific keys go under the
  new `extensions` namespace), and `purpose`/`non_goals`/`system` reject
  empty or whitespace-only strings.
- New warning under `layout: lite` when `security.public_assurance_root`
  still points at the split layout's `assurance` directory.

### Added

- `tests/test_validate.py`: a fixture-based regression suite for the
  validator (stage ladder, §17 conformance checks, drift routing and
  policy regression, lite tightening), run by `self-check` on a Python
  3.10/3.12/3.13 matrix.
- `requirements-ci.txt`: universal hash-pinned dependency lock.

### Fixed

- `GOVERNANCE.md` referenced `@MosslandOpenDevs/assurance-maintainers`
  while `.github/CODEOWNERS` uses `@MosslandOpenDevs/maintainers`; both now
  name the real team.
- `templates/AGENTIC_ASSURANCE.md` §2 now instructs adopters to keep the
  concrete pin values only in `adoption.yaml` (a pin duplicated into prose
  is not validator-checked and silently goes stale — observed in a v0.2.0
  pilot).
- ADOPTION.md §3.8 no longer overstates DRAFT ("placeholders allowed
  everywhere"): the adoption declaration itself must be complete at every
  stage; the allowance covers the local registers.
- `templates/AGENTS.md` reading order is now lite-aware (non-goals and the
  system description live in `.agentic-assurance/assurance.yaml` under
  `layout: lite`, not `assurance/SYSTEM.md`).
- `templates/adoption.yaml` lite comment now notes that
  `security.public_assurance_root` should point at `.agentic-assurance`.

## v0.2.0 — 2026-07-18

The register becomes a regression gate, the safest usage becomes the
easiest usage, and a green check can no longer be misread. All three
features come from the two pilot adoptions and two external reviews of
the v0.1 line.

### Adopter impact / upgrade actions

- Re-pin is optional; existing v0.1.x pins remain valid. Upgrading
  adopters update `upstream.version`, `upstream.commit` (the v0.2.0 tag
  commit), and the workflow `@` reference in one reviewed change.
- **Required-check rename:** the reusable workflow's `validate` job is
  now `structure`, and a `conformance` check appears (skipped while the
  declared stage is DRAFT). Update branch-protection required checks
  when re-pinning.
- All new fields are optional; adoptions without `layout`, `components`,
  or `adoption_stage` behave byte-identically.
- `data-curation` is no longer provisional; `agent-runtime` remains so.

### Added

- Lite adoption layout for `core`: all assurance content in a single
  `.agentic-assurance/assurance.yaml` (purpose, non-goals, optional
  system description, and the invariant/residual/defeater registers),
  declared with the new optional `layout` field in the adoption
  declaration (`schemas/adoption.schema.json`; `split` or `lite`,
  absent means `split`). The file is described by a thin envelope
  schema (`schemas/assurance-lite.schema.json`) whose section items
  follow the existing register schemas — no duplicated item shapes;
  the validator extracts each present section, validates it against
  the pinned register schemas, and runs the existing semantic checks
  over the combined result. Lite is core-only: combining `layout: lite`
  with any profile beyond `core`/`archived` is an error, and the
  graduation to the split layout preserves every ID. Starter template
  at `templates/assurance.yaml`. The 25-file/1,867-line first-adoption
  cost observed in the pilots drops to four files for `core`.
- Impact routing: optional `components` map in the adoption declaration
  (`schemas/adoption.schema.json`), wiring repository paths
  (gitwildmatch-style globs) to the invariant IDs they protect, with an
  informational `tests` list. Documented in adoption guide §3.7 and the
  commented example block in both adopter templates; the adopter
  pull-request template documents the two-line no-impact statement
  convention (`Assurance impact: none` plus a mandatory `Reason:`).
- `drift` subcommand in `scripts/validate.py`: given a changed-file list
  and the pull-request description, checks every mapped component the
  change touches — satisfied when the change also touches assurance
  artifacts, when the description mentions every listed invariant ID, or
  when it carries the explicit no-impact statement — and reports
  unsatisfied components as WARN (exit 0) or, with `--strict`, as ERROR
  (exit 1); `--json` emits machine-readable output.
- Drift job in the reusable `adopter-validate` workflow, running the
  pinned `validate.py drift` on pull-request events only, gated by a
  new `strict-drift` input (boolean, default false). Push-event callers
  and the existing validate job are unaffected.
- Adopter-mode cross-check: every `components[].invariants` ID must
  exist in the loaded invariant register (split and lite layouts alike);
  a dangling component reference is an ERROR.
- Adoption stages: optional `adoption_stage` field in the adoption
  declaration (`schemas/adoption.schema.json`; `DRAFT`,
  `HUMAN_REVIEWED`, or `CONFORMANT`, absent means `DRAFT`). Stages are
  self-declared and self-binding: the validator enforces the declared
  stage's requirements as ERRORs, so declaring a stage the repository
  does not meet fails the build, while an absent or `DRAFT` declaration
  keeps validator output byte-identical to before. `HUMAN_REVIEWED`
  requires no unfilled `REPLACE_WITH_` placeholder in the adoption file
  or any loaded register (split or lite) and a `human_review` block
  with non-empty `date`, `reviewer`, and `record`; `CONFORMANT`
  additionally treats passed `review_after` dates as errors (as with
  `--strict-review-dates`), requires a decided (non-`UNKNOWN`)
  `intent.classification` on every severity-critical invariant, and
  requires at least one attributable approval. Documented in adoption
  guide §3.8, the review guide, the glossary, and the commented
  `adoption_stage` block in both adopter templates. New `--ignore-stage`
  flag on the `validate.py adopter` subcommand skips stage enforcement
  (structure-only validation).
- Attributable approvals: optional `human_review.approvals` array in the
  adoption declaration (`schemas/adoption.schema.json`) — entries carry
  `approver`, `review_url`, and `at`, plus optional `covers` and `rule`;
  at least one entry with all three non-empty is required at
  `CONFORMANT`. Deliberately deferred: the workflow does not yet verify
  the `review_url` via the GitHub API (approved state, author ≠
  approver); the entry is a human-reviewable claim, and the deferral is
  documented in adoption guide §3.8.
- `conformance` job in the reusable `adopter-validate` workflow: runs
  the full stage-enforcing validator (no `--ignore-stage`), and is
  skipped while the declared `adoption_stage` is `DRAFT` or absent (the
  pin-reading step now also outputs the declared stage, defaulting to
  `DRAFT`). The drift job is untouched.

### Changed

- Adoption guide restructured around lite-first `core` adoption: new
  §3.0 documents the four-file lite layout, the core-only rule, and
  the ID-preserving graduation path; §3.1–§3.5 now explicitly describe
  the split layout used from `service` upward; §3.6 documents the lite
  validation differences. The `templates/github/` issue-template bundle
  and `CODEOWNERS` are now optional at `core` — recommended when the
  repository takes external contributions, and `CODEOWNERS` wherever a
  second maintainer exists. Both READMEs and the review guide present
  the lite layout as the `core` minimum.
- CI check-name split in the reusable `adopter-validate` workflow: the
  `validate` job is renamed to `structure` (the check appears as
  "assurance / structure") and now runs the validator with
  `--ignore-stage` — a `DRAFT`-equivalent, structure-only pass/fail —
  while the new `conformance` job carries stage enforcement. Adopter
  impact: re-pinning adopters who made the old check a required status
  check must update their branch-protection settings from `validate` to
  `structure`; the split exists so a green structure check cannot be
  misread as conformance (adoption guide §3.8).

### Changed (release)

- `PROFILE.md` §5: `data-curation` promoted from provisional (exercised
  end-to-end by the second pilot; both §6.4 gaps dispositioned).
  `agent-runtime` remains provisional.
- `PROFILE.md` §17: a declared adoption stage binds — conformance
  checking MUST fail when the declared stage's requirements are not met.

## v0.1.2 — 2026-07-18

Semantic validation: an evidence-free `VERIFIED` no longer passes.
Closes the external-review finding that the schemas alone accept
formally-green, semantically-empty registers.

### Adopter impact / upgrade actions

- Optional upgrade; existing pins remain valid. Re-pinning adopters get
  seven new semantic checks — six ERROR-level (duplicate IDs; dangling
  cross-references; `VERIFIED` critical invariants without enforcement
  and verification; `INTENDED` without `intent.authority`; high-impact
  `ACCEPTED` residuals without `acceptance_rationale`; `RESOLVED`
  entries without recorded grounds) and one WARN-level (passed
  `review_after` dates; `--strict-review-dates` escalates). Both current
  pilot registers pass all seven unchanged.
- Conclusion status and intent classification remain independent axes:
  a `VERIFIED` invariant with intent `UNKNOWN` is legitimate; the new
  checks require mechanism evidence for `VERIFIED` and human authority
  for `INTENDED`, never one for the other.

### Added

- Semantic checks in `scripts/validate.py` (both subcommands; templates
  are checked in self-check too): duplicate-ID detection, cross-reference
  integrity across all nine reference fields (WARN when the referenced
  register file does not exist at all), grounded-status requirements for
  `VERIFIED`-critical, `INTENDED`, `ACCEPTED`, and `RESOLVED` entries,
  and passed-`review_after` warnings with `--strict-review-dates`.

### Changed

- Informative minimum layouts aligned with normative `PROFILE.md` §6.1
  (owner decision, 2026-07-18): `assurance/INVARIANTS.yaml` is
  recommended at `core` — it anchors the regression protection, and both
  pilots keep one — and required from the `service` profile
  (template §4, adoption guide §3.1, both READMEs).

## v0.1.1 — 2026-07-18

Post-release hardening from external review: close the gap between
creating assurance documents and binding them.

### Adopter impact / upgrade actions

- Optional upgrade — no obligations changed and no re-pin is required.
  Adopters who want the new CODEOWNERS binding copy
  `templates/github/CODEOWNERS` and follow adoption guide §3.5; existing
  pins remain valid.

### Added

- Adopter `CODEOWNERS` template (`templates/github/CODEOWNERS`) covering
  the assurance layer (`AGENTS.md`, `AGENTIC_ASSURANCE.md`,
  `.agentic-assurance/`, `assurance/`, the CI caller workflow), with the
  honest single-maintainer caveat; adoption guide §3.5 documents the
  binding steps (branch protection + code-owner review) and names the
  documents-without-binding failure mode.

### Changed

- Adoption guide §4.1 and the review guide now recommend keeping the
  invariant register at roughly 5–15 entries per repository — the things
  that must never break, not the full specification.

## v0.1.0 — 2026-07-18

First stable release of the v0.1 line. Two completed pilot adoptions
validated the full cycle end to end: a private brownfield service
(archaeology → human intent review → recorded outcomes → scoped
remediations → pin upgrade) and a public repository adopted from a bare
kick-off prompt, whose review surfaced the tag-pin and prose-provenance
rules below.

### Adopter impact / upgrade actions

- Upgrade from a `v0.1.0-rc.1` or `unreleased` pin in one reviewed change
  (ADOPTION.md §2.1): set `upstream.version` to `v0.1.0`, `upstream.commit`
  to the commit the `v0.1.0` tag points to (`git rev-list -n1 v0.1.0`),
  and the CI caller workflow `@` reference to that same SHA.
- From this release the `adopter-validate` workflow rejects a release pin
  whose commit is not the tag commit.
- The prose-provenance rule is a SHOULD-level normative addition to
  archaeology practice; existing artifacts need no changes.
- Schemas are unchanged since `v0.1.0-rc.1`.

### Added

- `adopter-validate` workflow: a release-version pin is now verified against the
  published tag — the job fails when `upstream.commit` is not the commit the tag
  points to (second-trial lesson: the release PR's branch commit carries the same
  `VERSION` content and previously validated interchangeably).

### Changed

- Adoption guide §2 and `RELEASING.md` now state that the tag commit is the
  canonical release pin, with `git rev-list -n1 vX.Y.Z` as the lookup.
- Prose-provenance rule (second-pilot lesson — an adopting agent cited an
  agent-written comment as intent authority and caught its own circular
  reasoning): `PROFILE.md` §7 now states that committed prose with
  agent-assisted authorship remains an agent narrative, that provenance
  SHOULD be checked against commit authorship, and that intent authority
  comes from a human act (a reviewed merge or recorded review outcome),
  not from who typed the text; the marker check is one-directional (an
  agent trailer disqualifies, its absence proves nothing); operationalized in the adoption guide §4.1
  (`git blame` / `Co-Authored-By` check), the `AGENTIC_ASSURANCE.md`
  template §6.2, the review guide, and a new glossary entry.

## v0.1.0-rc.1 — 2026-07-18

First tagged release candidate of the v0.1 line, after one complete
brownfield pilot adoption (archaeology → §4.3 human review → recorded
outcomes → scoped remediations).

### Adopter impact / upgrade actions

- Adopters pinned to `unreleased` commits from the pilot phase upgrade in
  one reviewed change (ADOPTION.md §2.1): set `upstream.version` to
  `v0.1.0-rc.1`, `upstream.commit` to the release commit SHA, and the CI
  caller workflow `@` reference to that same SHA.
- All schema changes are backward-compatible additions; artifacts that
  validated under earlier draft commits remain valid.
- Templates copied earlier keep working as copied; re-copying is optional.
  The branch-until-reviewed and handoff-format rules apply to future
  adoption runs.
- Pinning `version: unreleased` remains valid only for commits whose
  `VERSION` file reads `unreleased` (PROFILE.md §16).

### Added

- Initial draft profile (`PROFILE.md`).
- Public/restricted disclosure model.
- GitHub Issue and Security Advisory routing model.
- Adoption and assurance artifact templates.
- JSON Schemas for adoption declarations, claims, invariants, defeaters, and residuals (`schemas/`).
- Validator with `self-check` and `adopter` subcommands (`scripts/validate.py`).
- CI workflows: `self-check` for this repository and the reusable `adopter-validate` workflow for adopting repositories (`.github/workflows/`).
- Governance, release, and contribution documents: `GOVERNANCE.md`, `RELEASING.md`, `CONTRIBUTING.md`.
- License files for the per-path license split: `LICENSE` (Apache-2.0, code and tooling), `LICENSE-docs` (CC-BY-4.0, prose), `templates/LICENSE` (CC0-1.0, templates).
- Central repository issue forms, `config.yml`, pull request template, and `CODEOWNERS` (`.github/`).
- Adopter template bundle: `templates/github/` issue forms and pull request template, `templates/AGENTS.md`, `templates/SYSTEM.md`, `templates/THREAT_MODEL.md`.
- Adoption guide (`docs/ADOPTION.md`) and convention-mapping guide (`docs/MAPPINGS.md`).
- Root `VERSION` file recording the repository's release state.
- Optional `acceptance_rationale` and `resolution_note` fields on residual entries (`schemas/residuals.schema.json`), standardized from first-pilot usage.
- Optional `resolution` field on defeater entries (`schemas/defeaters.schema.json`), standardized from first-pilot usage.
- Optional `human_review` block in the adoption declaration (`schemas/adoption.schema.json`) recording the §4.3 intent review, standardized from first-pilot usage.
- Adoption guide §3.5: note that GitHub silently drops issue-form labels that do not exist in the repository, with an example `gh label create` loop.
- Glossary (`docs/GLOSSARY.md`): plain-language definitions of the profile's terminology, as an owner-side entry point (first-pilot lesson).
- Owner review guide (`docs/REVIEW-GUIDE.md`): the human owner's entry point for reviewing an adoption draft and making the §4.3 decisions (first-pilot lesson).

### Changed

- Unified version strings: the informal draft version identifier is abolished in favor of `unreleased` and `vMAJOR.MINOR.PATCH` release identifiers; `PROFILE.md` §16 adds pre-release naming, tag immutability, version/commit mismatch, and pre-first-release pinning rules.
- Marked the `data-curation` and `agent-runtime` profiles as provisional; while provisional, changes to their obligations are classified as minor.
- Clarified normativity: `PROFILE.md` is the normative text; README files and translations are informative.
- `SECURITY.md` scope now names templates alongside example configurations.
- Adoption guide §0 kick-off prompt and §4.3 now direct agents to keep the adoption draft on a branch as an open pull request; merging to the default branch is the human owner's act after the §4.3 review (first-pilot lesson).
- Adoption guide §3.6 now states that `RESTRICTED` entries bind repository visibility: the repository must not be made public until they are sanitized to `SUMMARY_ONLY`/`PUBLIC` or moved to the restricted record.
- Prescribed the agent→owner handoff format (adoption guide §0 kick-off prompt item 5; template `AGENTIC_ASSURANCE.md` §12): the drafting agent ends with a handoff summary in the owner's working language that states nothing is decided, lists each pending decision in plain language, and instructs that the pull request must not be merged until those decisions are made; the agent must not describe its result as "settled" or "complete" — completion language is reserved for the owner's acceptance (first-pilot lesson).
