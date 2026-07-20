# OpenDevs Agentic Assurance Profile

**Status:** Released — adopters pin a [tagged release](https://github.com/MosslandOpenDevs/agentic-assurance-profile/releases); `main` carries in-progress changes between releases (see `VERSION`)  
**Normative language:** `MUST`, `MUST NOT`, `SHOULD`, `SHOULD NOT`, and `MAY` express profile obligations.

## 1. Purpose and scope

This profile defines repository-level assurance practices for software substantially produced or maintained by AI coding agents.

Its purpose is to:

- preserve human-approved intent and non-goals;
- distinguish intended behavior from implementation accident;
- express critical claims and invariants explicitly;
- connect those properties to enforcement and reproducible evidence;
- record counterevidence, limitations, and residual uncertainty;
- separate implementation, audit, remediation, and final acceptance where risk warrants it;
- make public assurance inspectable without requiring unsafe disclosure.

The profile is model-neutral, editor-neutral, language-neutral, and platform-neutral.

Conformance to this profile is not a security certification, formal proof, penetration test, or claim that a system is bug-free.

This document is the normative text of the profile. README files and translations are informative.

## 2. Core model

```text
Intent
  → Claims
  → Invariants
  → Enforcement
  → Evidence
  → Defeaters
  → Residuals
  → Human acceptance
```

### 2.1 Intent

The human-owned description of purpose, users, scope, non-goals, authority, and acceptable trade-offs.

### 2.2 Claim

A proposition asserted to a user, operator, integrator, auditor, or the public.

### 2.3 Invariant

A proposition that MUST remain true across every valid state and permitted change.

Example:

- Feature: “Users may authenticate with a wallet.”
- Invariant: “An expired or consumed challenge cannot create a valid authenticated session.”

### 2.4 Enforcement

A mechanism that prevents or blocks violation, such as a database constraint, authorization guard, cryptographic check, schema, state-machine guard, transaction boundary, or policy enforcement point.

### 2.5 Verification

A mechanism that checks whether declared properties and controls behave as claimed, such as tests, static analysis, reproducible inspection, migration verification, runtime assertions, monitoring, or independent reproduction.

**Tests verify; controls enforce.** For every active profile, an invariant
recorded with severity `critical` and conclusion `VERIFIED` MUST name at least
one enforcement reference and at least one verification reference. Where no
stricter profile-specific obligation applies, other critical invariants SHOULD
have both. A stricter obligation still governs; in particular, the `service`
profile's §6.2 enforcement-and-verification requirement remains a MUST.

### 2.6 Evidence

A reproducible artifact linked to a bounded revision, build, release, artifact digest, or deployment. An AI agent's narrative that a check passed is not evidence by itself.

### 2.7 Defeater

A concrete reason a claim or assurance argument may be false, incomplete, stale, or inapplicable.

### 2.8 Residual

A known limitation, unverified assumption, accepted inconsistency, unsupported condition, or remaining doubt after a release or operational decision.

In this profile, a **critical residual** means a residual whose `impact` is
`critical`. The separate `uncertainty` field records confidence in the
assessment; `uncertainty: critical` does not by itself make a non-critical
impact a critical residual or trigger the critical-residual disposition gate.

Residuals are expected. Hidden residuals are not.

## 3. Authority

A named human owner or governing body MUST retain authority over:

- purpose and non-goals;
- critical claims and invariants;
- wording and limitation of public trust claims;
- weakening of critical controls or evidence obligations;
- acceptance of critical residuals;
- disclosure of restricted or embargoed security material.

An implementation agent MAY choose implementation details within approved contracts. It MUST NOT silently redefine the contract, weaken a failed test to obtain a green result, or accept a critical residual for the human owner.

## 4. Behavior and evidence classification

Observed behavior SHOULD be classified as:

- `INTENDED` — supported by a current human-approved specification, invariant, or decision;
- `ACCIDENTAL` — known to exist but not desired;
- `COMPATIBILITY` — retained to preserve an explicit compatibility obligation;
- `UNKNOWN` — evidence is insufficient to determine intent;
- `DEPRECATED` — temporarily supported with an approved removal path.

A conclusion about the system SHOULD be classified as:

- `VERIFIED` — reproducible evidence directly supports it;
- `INFERRED` — indirect evidence supports it;
- `UNKNOWN` — evidence is insufficient;
- `CONTRADICTED` — available evidence conflicts with it.

Current production behavior is evidence of current behavior. It is not automatic proof of intended behavior.

## 5. Adoption profiles

Use the smallest applicable set. The smallest applicable set is the smallest that covers every characteristic the system actually has — not the fewest profiles selected in the hope of escalating later. Declaring a lighter profile than the system's nature does not reduce its obligations; it only leaves them unstated, and unstates the checks the system needs.

| Profile | Applies to |
|---|---|
| `core` | Any repository substantially produced or maintained by AI agents |
| `service` | Deployed websites, APIs, workers, stateful backends, or operational services |
| `trust-critical` | Security, privacy, identity, authorization, financial, governance, or public-verifiability claims |
| `data-curation` | Externally sourced, editorial, scored, classified, or recommended data |
| `agent-runtime` | Model-driven agents or workflows operating in production |
| `archived` | Repositories retained solely for historical reference, not supported or intended for current use, with no active operation, functional maintenance, or feature development |

Every applicable non-`archived` specialized profile (`service`, `trust-critical`, `data-curation`, or `agent-runtime`) inherits all `core` obligations in §6.1, whether or not `core` is written in the adoption declaration. When one or more specialized profiles apply, the canonical smallest declaration lists every applicable specialized profile and omits `core`; an adopter MAY also list `core` explicitly, but doing so neither adds nor removes an obligation. For an active adopter to which no specialized profile applies, the declaration is `[core]`.

The `archived` profile is exclusive: it MUST be declared alone and replaces, rather than inherits or combines with, all active profiles including `core` and their §6.1–§6.5 obligations.

Creating an initial archived adoption, correcting its historical facts, or maintaining its profile pin, adoption stage, review record, or agent-instruction metadata is archival-assurance metadata work, not functional maintenance. Work that supports current use or changes code, dependencies, or behavior for continued operation is functional maintenance and makes `archived` inapplicable.

The `agent-runtime` profile is provisional until exercised by a real adopter. Before `v1.0.0`, while it remains provisional, changes to its obligations are classified as minor under §16's initial-development rule; the provisional label does not override §16's stable-version rules at or after `v1.0.0`. The `data-curation` profile was promoted from provisional in v0.2.0 after a public adopter exercised every §6.4 obligation and dispositioned the resulting gaps.

A project MAY define local extensions. Local extensions MUST NOT silently weaken the pinned upstream profile.

## 6. Required local artifacts

Except for the exclusive `archived` profile, the obligations in this section are cumulative: every specialized profile includes §6.1 and adds its own subsection, regardless of whether `core` is explicit in the declaration.

The single-file `lite` layout is valid only when `core` is the sole declared
profile. Every specialized active profile and the exclusive `archived` profile
MUST use the split/mapped layout. When graduating from lite to an active
specialized profile, the adopter MUST move each present register section
unchanged, preserving its IDs, and move any inline system description into the artifact mapped
by `paths.system`, preserve purpose and non-goals there or in another
human-approved local intent artifact, and preserve or deliberately relocate
local extensions before removing `layout: lite`. Reclassification to
`archived` instead follows §6.6 and MUST record its four historical facts in
the mapped system artifact before the lite declaration is removed.

Every adoption MUST keep each applicable or declared location—its declaration,
root instructions, mapped policy artifacts, material-change workflow root,
human-review record, and security/public-assurance paths—under effective
human-owner change review when that location is present.
Relocation MUST NOT move policy outside that review boundary. If one of these
locations is a tracked symlink, both the lexical link (including retargeting)
and its resolved in-project target and containing tree MUST remain in the
effective review boundary. `CODEOWNERS` plus enforced code-owner review is the
GitHub mechanism described in the adoption guide; an equivalent repository
control or, where independent approval is unavailable, the attributable review
record may supply the platform-neutral obligation. The validator's path and
warning checks do not prove that repository review settings are effective.

Every filesystem artifact/root path field carried by the adoption declaration,
and the reusable workflow's configured `adoption-file`, MUST use a
repository-relative lexical spelling and, after normalization and symlink
resolution, remain inside the adopting project. Artifact/file paths
MUST NOT name the repository root; directory-root fields may use `.` where
their schema permits it. No adopter-owned obligation may be satisfied from Git
metadata, the pinned profile/schema checkout, or another trusted non-adopter
tree. A symlink is valid only when its final target remains in permitted
adopter-owned content; the review-boundary rule above still applies to both
the link and target.

### 6.1 Core

A `core` adopter MUST have:

- an upstream adoption declaration pinned by version and full commit SHA;
- a root `AGENTIC_ASSURANCE.md` adoption guide with a reading order that directs agents to that guide and the adoption declaration;
- a root `AGENTS.md` carrying that same guide-then-declaration reading order, from which the applicable assurance-artifact paths are resolved;
- human-approved purpose and non-goals;
- a current system description, either inline in the lite assurance file or at the artifact mapped by `paths.system`, that identifies the system being assured, its principal responsibilities and material boundaries, and known material limitations or unknowns;
- at least one project invariant — a property that must remain true (section 8);
- an active residual register;
- a material-change workflow identified in the adoption declaration, with a non-empty repository-local entry document or directory from which agents and reviewers can find the operative process.

The system-description content minimum above is the same in lite and split layouts. Mapping an existing equivalent changes its location, not the obligation it satisfies; §7 gives the fuller reconstruction that an active brownfield assessment SHOULD normally record.

### 6.2 Service

A `service` adopter MUST additionally have:

- trust-boundary or threat-model documentation;
- enforcement and verification references for critical invariants;
- release or deployment evidence linked to a bounded revision.

### 6.3 Trust-critical

A `trust-critical` adopter MUST additionally have:

- public or user-facing claims and explicit limitations;
- proof tiers or equivalent evidence-strength classification;
- separation of audit and remediation for critical work;
- secret and privileged-access boundaries;
- private vulnerability reporting and disclosure procedures for public repositories.

### 6.4 Data-curation

A `data-curation` adopter MUST additionally have:

- stable domain identifiers;
- source provenance and version metadata;
- separation between external facts and local editorial or model judgment;
- model or rubric version history;
- audit trails for override and bulk migration.

### 6.5 Agent-runtime

An `agent-runtime` adopter MUST additionally have:

- explicit delegated authority and execution boundaries;
- tool permissions and high-impact action controls;
- retry, idempotency, deadline, and duplicate-action semantics where applicable;
- runtime incident evidence and human override or safe-stop behavior.

### 6.6 Archived

An adopter selecting `archived` MUST declare it exclusively; `archived` replaces all active profiles and their §6.1–§6.5 obligations. It MUST still have:

- an upstream adoption declaration pinned by version and full commit SHA;
- a root `AGENTIC_ASSURANCE.md` adoption guide and a root `AGENTS.md`, each carrying the same reading order that directs agents first to that guide and then to the adoption declaration;
- a non-empty system artifact, at every adoption stage, resolved from the adoption declaration's `paths.system` mapping (default: `assurance/SYSTEM.md`).

That system artifact MUST state:

- that the repository is retained solely for historical reference, is not supported or intended for current use, and has no active operation, functional maintenance, or feature development;
- its historical purpose;
- known material limitations;
- the last supported revision or release, or explicitly that none exists.

## 7. Brownfield adoption

Initial adoption of an existing repository MUST begin as a read-only archaeology task before broad remediation.

For a non-`archived` adopter, the adoption assessment SHOULD reconstruct:

1. purpose, users, scope, and non-goals;
2. domain entities, identifiers, and state transitions;
3. trust boundaries and external dependencies;
4. public claims and user-visible promises;
5. candidate invariants;
6. existing enforcement;
7. existing verification and runtime evidence;
8. ambiguous, accidental, or compatibility behavior;
9. defeaters, limitations, and residuals;
10. conformance gaps.

For an `archived` adopter, that active-system reconstruction is replaced by a narrower read-only assessment. It MUST establish evidence that the repository is retained solely for historical reference, is not supported or intended for current use, and has no active operation, functional maintenance, or feature development; reconstruct the four §6.6 historical facts; and record them in the mapped system artifact. It MAY preserve additional historical context, but it MUST NOT fabricate active claims, invariants, defeaters, or residuals merely to imitate an active adoption.

Each non-`UNKNOWN` material conclusion SHOULD cite concrete evidence such as file and line, database constraint, test name, command output, endpoint response, artifact digest, deployment record, or runtime metric.

An AI-generated explanation is not evidence by itself.

This rule extends to committed prose. A comment, document, or note is not evidence of human intent merely because it is committed; when its authorship is agent-assisted — for example, an agent co-authorship trailer on the introducing commit — it remains an agent narrative under this section. The provenance of prose cited as intent authority SHOULD be checked against commit authorship. The check is one-directional: an agent marker disqualifies prose as intent authority, but the absence of one establishes nothing — many agents leave no marker, and a human may commit agent-written text under their own name. Prose whose human authorship cannot be positively established is provenance-uncertain and MUST NOT be promoted to human authority by that absence alone. Authority comes from a human act, not from who typed the text: an agent-drafted record of an explicit human decision, anchored by the human's own approval act such as a reviewed merge or a recorded review outcome, is human authority; committed prose without such an act is not, and the affected intent classification remains `UNKNOWN` until the human review settles it.

Before broad remediation, a human owner of a non-`archived` adoption MUST review:

- purpose and non-goals;
- critical claims and invariants;
- behavior classified as intended, accidental, compatibility, unknown, or deprecated;
- critical residuals and public claim limitations.

For an `archived` adoption, that active-system review is replaced by the owner's confirmation that the repository satisfies the exclusive archived classification and that each of the four §6.6 facts in the mapped system artifact is accurate. This confirmation MUST occur before the archived adoption is accepted.

## 8. Claims and invariants

Each claim or invariant SHOULD have:

- stable ID;
- precise statement;
- scope and assumptions;
- rationale;
- limitations;
- owner;
- current status;
- affected system versions;
- enforcement references, when applicable;
- verification and evidence references;
- related defeaters and residuals;
- disclosure classification.

Critical invariants MUST NOT be considered verified solely because an agent states that tests pass.

Recommended claim proof tiers:

1. `INDEPENDENTLY_VERIFIABLE` — a third party can reproduce the result without privileged access;
2. `OPERATIONALLY_AUDITABLE` — evidence exists but requires controlled access;
3. `OPERATOR_ATTESTED` — the claim currently depends on operator process or statement;
4. `NOT_CLAIMED` — the project explicitly declines to assert the property.

Claim wording MUST NOT exceed the support of its evidence tier.

## 9. Material changes

A material change affects externally visible behavior, persistent data, authentication, authorization, privacy, security, billing, governance, recommendations, classification, migration, deployment, public claims, or critical dependencies.

An `archived` project MUST be reclassified under every applicable active profile before any material change above or any renewed operation, functional maintenance, or feature development. The archival-assurance metadata work defined in §5 is not by itself an active material change; a correction to the archived classification or four §6.6 facts still requires the owner confirmation in §7.

For a non-`archived` project, before implementation, the project's change workflow MUST state:

- intent and non-goals;
- affected claims and invariants;
- before and after behavior;
- failure and abuse cases;
- migration and rollback;
- observability;
- required deterministic evidence;
- independent verification requirements;
- expected residual impact;
- disclosure classification.

Every active adopter MUST identify that workflow under
`specification_workflow` in its adoption declaration and map `root` to a
non-empty repository-local entry document or directory. The entry may point
onward to a forge Issue process or another durable system; a forge-only custom
known only to maintainers is not enough because agents and reviewers need a
versioned local starting point. An archived adopter MAY retain such a mapping
for archival-record corrections, but §6.6 does not require an active workflow.

The project SHOULD reuse its existing OpenSpec, Spec Kit, ADR/RFC, Issue, or equivalent workflow rather than duplicate it.

## 10. Audit and remediation separation

For critical security, privacy, authorization, financial, governance, or data-integrity work:

1. audit SHOULD occur in a read-only context;
2. findings SHOULD be recorded before remediation;
3. remediation SHOULD occur in a separate context;
4. a third context or deterministic suite SHOULD re-verify the original finding and regressions.

The same agent context MUST NOT be the sole specification author, implementer, auditor, remediator, and final judge of a critical change.

## 11. Evidence

Evidence SHOULD be:

- reproducible;
- attributable to a revision, release, artifact, or deployment;
- produced by deterministic tooling or independent review where practical;
- stored or summarized without leaking restricted information;
- refreshed when affected claims, controls, dependencies, or environments change.

A release evidence manifest SHOULD include:

- commit SHA;
- artifact or build digest;
- profile version and profile commit;
- schema and migration version;
- critical invariant results;
- public claim coverage;
- unresolved defeater and residual IDs;
- generation time;
- relevant tool versions.

Line coverage alone is not assurance coverage.

## 12. Defeaters and residuals

Each residual SHOULD contain:

- stable ID;
- description or safe public summary;
- impact and uncertainty;
- affected claims and invariants;
- mitigation;
- owner;
- disposition authority and grounds;
- review date or trigger;
- disclosure classification.

Every residual recorded as `ACCEPTED` MUST name the human who accepted it, the non-future acceptance date, and the acceptance rationale. As defined in §2.8, a critical residual is one whose `impact` is `critical`; its separate `uncertainty` value does not change this classification. Acceptance of a critical residual MUST come from the human owner or governing body. A residual recorded as `RESOLVED`, including critical history, MUST instead state the resolution grounds and remediation reference; resolution is not acceptance.

Every defeater recorded as `MITIGATED`, `RESOLVED`, or `WITHDRAWN` MUST state
non-blank resolution or disposition grounds. `MITIGATED` means that the
defeater's force is reduced but not eliminated. `RESOLVED` means that it no
longer applies because it was answered by evidence or a fix. `WITHDRAWN` means
that it was recorded in error or is outside the applicable scope.

A residual MUST NOT be closed solely because no recent incident was observed.

## 13. Public and restricted disclosure

Public assurance is a sanitized projection, not the complete private security record.

Material SHOULD be classified as:

- `PUBLIC`;
- `SUMMARY_ONLY`;
- `RESTRICTED`;
- `EMBARGOED`.

A public repository MUST NOT contain:

- secrets or personal data;
- actionable details of an unpatched vulnerability;
- sensitive production topology or access paths that materially reduce attack cost;
- private reporter identity or confidential correspondence;
- restricted evidence copied into Issues, pull requests, logs, or public artifacts.

Suspected exploitable findings MUST be routed through the repository's private security process, not a public Issue.

The public profile MAY be updated with a sanitized summary after remediation and coordinated disclosure.

## 14. GitHub Issues and durable artifacts

Durable profile artifacts describe current state. Issues track proposed or incomplete work.

Profile items MUST use stable semantic IDs independent of GitHub Issue numbers.

A material Issue or pull request SHOULD reference affected profile IDs.

An Issue MUST NOT be considered resolved solely because code was merged. Required artifact, evidence, defeater, and residual updates MUST also be complete.

A closing keyword such as `Closes #123` SHOULD be used only when the pull request satisfies the Issue's full acceptance criteria.

Potentially exploitable vulnerabilities MUST be handled through a private report or Security Advisory.

## 15. Agent prohibitions

An agent MUST NOT:

- redefine intent or non-goals without approval;
- classify behavior as intended merely because it exists;
- weaken, remove, skip, or rewrite a failed test solely to obtain a green build;
- fabricate test results, scanner output, runtime evidence, citations, or file references;
- hide contradictions, warnings, unknowns, or unresolved findings;
- claim independence when audit and implementation relied on the same sole context;
- silently update the upstream profile pin;
- copy and modify the profile as an untracked local fork;
- publish restricted or embargoed material;
- accept a critical residual for the human owner.

When certainty is unavailable, the agent MUST record `UNKNOWN`, a defeater, or a residual rather than invent confidence.

## 16. Versioning and pinning

The profile uses semantic versioning.

- **Major:** removes, weakens, or materially changes an obligation;
- **Minor:** adds backward-compatible requirements, profiles, or fields;
- **Patch:** clarifies wording or repairs validation without changing intended obligations.

Before the first stable release (`v1.0.0`), the profile is under active development: under this project's governing interpretation of semantic versioning's initial-development latitude, adding a new obligation, or tightening an existing one, is a **minor** change, and MAY cause a previously conforming adoption to require new content. Such changes are called out in the changelog with their adopter impact. This rule is the profile's stated `0.x` operating policy, not a claim that semantic versioning universally requires that classification. It was introduced in v0.4.0 and applied to that same release by a recorded governing owner decision; releases before v0.4.0 were classified under the preceding rule, and that release's changelog entry states the decision and its rationale. From `v1.0.0`, materially changing an obligation is major.

Release identifiers MUST use the form `vMAJOR.MINOR.PATCH`. Pre-releases MUST use the form `vMAJOR.MINOR.PATCH-rc.N`. Numeric identifiers use ASCII decimal digits, have no leading zero unless the identifier is exactly zero, and `N` starts at 1.

A published tag MUST NOT be moved, deleted, or reused. A correction MUST be published as a new tag.

An adopting repository MUST pin:

- the human-readable profile version; and
- the exact full commit SHA.

Before the first tagged release, an adopting repository MUST pin the version string `unreleased` together with the exact full commit SHA.

Conformance checking MUST fail when the pinned version does not match the `VERSION` file at the pinned commit.

For a release or pre-release pin, the exact full commit SHA MUST be the commit
to which the matching published tag resolves. A release-preparation commit that
carries the same bare `VERSION` string but is not that tag commit is not a valid
adopter pin.

When conformance checking consumes a Git-backed profile checkout, it MUST also
bind the validation run to that commit: the checkout `HEAD` MUST equal the
pinned SHA, the executing validator MUST be the checkout's validator, and the
consumed version, dependency-lock, validator, and schema resources MUST be real
files from a worktree clean at that `HEAD`. A source archive without Git object
identity cannot establish that commit binding mechanically and MUST disclose
that limitation rather than imply that `VERSION` alone proves it.

A floating branch MUST NOT be the sole normative reference.

Profile upgrades MUST occur through explicit project change review.

## 17. Conformance statement

A project MAY declare an adoption stage in its adoption declaration. The declaration is self-made and self-binding, each stage includes every stage below it, and advancing it is a human-owner act. An omitted stage means `DRAFT`:

- `DRAFT` means the adoption satisfies the baseline schema, required-artifact checks, and every applicable semantic check independent of review stage. Work-in-progress placeholders and `UNKNOWN` register values MAY remain where the schema permits them, but the adoption declaration itself MUST be complete. A machine-detectable placeholder never constitutes a committed mechanism reference, human authority, residual acceptance or resolution ground, or closed-defeater resolution. The exclusive `archived` profile's mapped system artifact MUST already be non-empty at this and every later stage. For every active profile, a `VERIFIED` critical invariant MUST name at least one enforcement and one verification reference; under `service`, every critical invariant MUST name both regardless of conclusion status. Any invariant classified `INTENDED`, `COMPATIBILITY`, or `DEPRECATED`, at any severity, MUST name a non-blank human authority for that affirmative disposition.
- `HUMAN_REVIEWED` means `DRAFT` plus no unfilled shipped placeholder in the adoption declaration and, for an active adoption, no unfilled shipped placeholder in loaded active registers. An active system description and every other required active prose artifact (currently the service threat model) MUST be non-empty and contain no generic `REPLACE_WITH_` marker. Under the exclusive `archived` profile, retained historical active registers do not reintroduce that active-register completion rule; instead, the archived system artifact MUST contain none of the four exact archived markers shipped in `templates/SYSTEM.md`. A dated `human_review` record MUST name the reviewer and point to an existing, non-empty durable review artifact in the adopting project. The human owner MUST have completed the applicable active or archived review in §7. For every active critical invariant, that review MUST record an intent classification; `UNKNOWN` is an honest reviewed result when the owner cannot decide.
- `CONFORMANT` means `HUMAN_REVIEWED` plus at least one attributable approval naming who approved, where the approval is recorded as an absolute HTTP(S) URL, and when as an ISO date or timestamp, and satisfaction of the applicable conformance conditions below. For an active adopter, no `review_after` date may be overdue and every critical invariant's intent MUST be decided and MUST NOT be `UNKNOWN` or `ACCIDENTAL`; an accidental behavior is not an invariant that the project commits to preserve. An archived adopter's retained historical active registers do not reintroduce these active review-date or invariant-intent conditions.

`human_review.date`, every approval `at`, and every residual `accepted_at` record completed human acts and MUST NOT be future-dated. Because a date-only value carries no time-zone offset, it MUST NOT be later than the latest civil date currently possible (UTC+14); a timestamp is compared at its stated offset. At `CONFORMANT`, at least one attributable approval's civil date MUST be the same as or later than `human_review.date`.

An approval with no `covers` list attests the full conformance claim. If `covers` is present, the approval counts toward the `CONFORMANT` gate only when it includes the reserved `CONFORMANCE` token; other listed IDs describe additional scope, but a narrowly scoped approval without `CONFORMANCE` does not attest the full claim.

Conformance checking MUST fail when a declared stage's requirements are not met. A project MUST explicitly declare `adoption_stage: CONFORMANT` before it describes a bounded revision or release as conforming; meeting the conditions without that declaration does not make a `DRAFT` or `HUMAN_REVIEWED` adoption a conformance claim.

A `CONFORMANT` declaration is the adopter's claim that the bounded revision satisfies **all** applicable obligations of its selected §6 profiles and the conditions below, including conditions that cannot be inferred from file shape. The attributable human approval attests that full claim; it is not limited to the validator's mechanically decidable subset.

A non-`archived` project MAY describe a bounded revision or release as conforming only when:

- required profile artifacts or approved mappings exist;
- the profile version and commit are pinned;
- human-approved purpose and non-goals exist;
- no claim or critical invariant is `CONTRADICTED`, and no critical invariant has another known violation; recording or accepting that violation as a residual does not make the false invariant conforming;
- evidence is bound to the bounded revision or deployment;
- every critical invariant recorded as `VERIFIED` has at least one evidence reference bound to the bounded revision or deployment claimed by the conformance statement;
- claim language does not exceed evidence strength;
- no critical residual is `OPEN`; each critical residual carried as `ACCEPTED` has explicit human acceptance, while each critical residual recorded as `RESOLVED` states the grounds and remediation reference for its resolution;
- public artifacts exclude restricted and embargoed material.

An `archived` project MAY describe a bounded revision as conforming only when:

- the §6.6 adoption, root instruction, and mapped system artifacts exist;
- the profile version and commit are pinned;
- the human owner has confirmed that the repository is retained solely for historical reference, is not supported or intended for current use, and has no active operation, functional maintenance, or feature development;
- the human owner has confirmed all four §6.6 facts in the mapped system artifact, with that review bound to the bounded revision;
- public artifacts exclude restricted and embargoed material.

These archived conditions replace the active-system purpose, claim, invariant, deployment-evidence, and residual conditions above; they do not waive the common stage, pinning, or disclosure rules.

The validator enforces the structural and mechanically decidable subset of this contract; a green result is not proof of full conformance. Among the conditions that remain human-reviewed are the truth and completeness of system prose; whether evidence is genuinely bound to the claimed revision and claim wording stays within its strength; the substance of service enforcement, verification, and release/deployment evidence; trust-critical limitations, audit/remediation separation, secret handling, and private-reporting practice; and the profile-specific semantics of data-curation and agent-runtime controls. For `archived`, the validator's non-empty and untouched-template guards likewise do not establish reference-only eligibility or the truth of the four §6.6 facts. A green check means the declaration has passed the implemented mechanical gates; the human-approved `CONFORMANT` declaration remains the full normative claim.

For a non-`archived` project, conformance means that its contracts, controls, evidence, counterarguments, and remaining uncertainty are represented according to this profile. For an `archived` project, it means that the bounded reference-only classification and required historical facts are represented and owner-confirmed; it does not assert current operational assurance. Neither statement means the project is universally secure or bug-free.
