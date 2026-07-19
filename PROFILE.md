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

**Tests verify; controls enforce.** A critical invariant SHOULD have both.

### 2.6 Evidence

A reproducible artifact linked to a bounded revision, build, release, artifact digest, or deployment. An AI agent's narrative that a check passed is not evidence by itself.

### 2.7 Defeater

A concrete reason a claim or assurance argument may be false, incomplete, stale, or inapplicable.

### 2.8 Residual

A known limitation, unverified assumption, accepted inconsistency, unsupported condition, or remaining doubt after a release or operational decision.

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
| `archived` | Reference-only repositories without active operation or feature development |

The `agent-runtime` profile is provisional until exercised by a real adopter; while marked provisional, changes to its obligations are classified as minor. The `data-curation` profile was promoted from provisional in v0.2.0 after a public adopter exercised every §6.4 obligation and dispositioned the resulting gaps.

A project MAY define local extensions. Local extensions MUST NOT silently weaken the pinned upstream profile.

## 6. Required local artifacts

### 6.1 Core

A `core` adopter MUST have:

- an upstream adoption declaration pinned by version and full commit SHA;
- an agent-visible reading order, normally through `AGENTS.md`;
- human-approved purpose and non-goals;
- a current system description or mapping to an existing equivalent;
- at least one project invariant — a property that must remain true (section 8);
- an active residual register;
- a material-change workflow.

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

An `archived` adopter MUST state:

- that the repository is not actively operated or maintained;
- its historical purpose;
- known material limitations;
- the last supported revision or release, if any.

## 7. Brownfield adoption

Initial adoption of an existing repository MUST begin as a read-only archaeology task before broad remediation.

The adoption assessment SHOULD reconstruct:

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

Each non-`UNKNOWN` material conclusion SHOULD cite concrete evidence such as file and line, database constraint, test name, command output, endpoint response, artifact digest, deployment record, or runtime metric.

An AI-generated explanation is not evidence by itself.

This rule extends to committed prose. A comment, document, or note is not evidence of human intent merely because it is committed; when its authorship is agent-assisted — for example, an agent co-authorship trailer on the introducing commit — it remains an agent narrative under this section. The provenance of prose cited as intent authority SHOULD be checked against commit authorship. The check is one-directional: an agent marker disqualifies prose as intent authority, but the absence of one establishes nothing — many agents leave no marker, and a human may commit agent-written text under their own name. Prose whose human authorship cannot be positively established is provenance-uncertain and MUST NOT be promoted to human authority by that absence alone. Authority comes from a human act, not from who typed the text: an agent-drafted record of an explicit human decision, anchored by the human's own approval act such as a reviewed merge or a recorded review outcome, is human authority; committed prose without such an act is not, and the affected intent classification remains `UNKNOWN` until the human review settles it.

Before broad remediation, a human owner MUST review:

- purpose and non-goals;
- critical claims and invariants;
- behavior classified as intended, accidental, compatibility, unknown, or deprecated;
- critical residuals and public claim limitations.

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

Before implementation, the project's change workflow MUST state:

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
- acceptance authority;
- review date or trigger;
- disclosure classification.

Critical residuals MUST have explicit human acceptance.

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

Release identifiers MUST use the form `vMAJOR.MINOR.PATCH`. Pre-releases MUST use the form `vMAJOR.MINOR.PATCH-rc.N`.

A published tag MUST NOT be moved or reused. A correction MUST be published as a new tag.

An adopting repository MUST pin:

- the human-readable profile version; and
- the exact full commit SHA.

Before the first tagged release, an adopting repository MUST pin the version string `unreleased` together with the exact full commit SHA.

Conformance checking MUST fail when the pinned version does not match the `VERSION` file at the pinned commit.

A floating branch MUST NOT be the sole normative reference.

Profile upgrades MUST occur through explicit project change review.

## 17. Conformance statement

A project MAY describe a bounded revision or release as conforming only when:

- required profile artifacts or approved mappings exist;
- the profile version and commit are pinned;
- human-approved purpose and non-goals exist;
- critical claims and invariants have no unaccepted known violation;
- evidence is bound to the bounded revision or deployment;
- claim language does not exceed evidence strength;
- critical residuals are explicitly accepted;
- public artifacts exclude restricted and embargoed material.

A project MAY declare an adoption stage (`DRAFT`, `HUMAN_REVIEWED`, `CONFORMANT`) in its adoption declaration. A declared stage binds: conformance checking MUST fail when the declared stage's requirements are not met, and advancing the stage is a human-owner act.

Conformance means that the project's contracts, controls, evidence, counterarguments, and remaining uncertainty are represented according to this profile. It does not mean the project is universally secure or bug-free.
