# Adoption Guide

This document is the practical walk-through for adopting the OpenDevs Agentic Assurance Profile in a repository. The normative obligations live in [PROFILE.md](../PROFILE.md); this guide operationalizes them with mechanical detail: which files to copy, what to pin, how to wire continuous validation, and how to sequence adoption in an existing codebase. Where this guide and PROFILE.md appear to disagree, PROFILE.md governs.

To reuse existing repository conventions instead of the default artifact paths, see [MAPPINGS.md](MAPPINGS.md).

## 0. Quick start for AI agents

To start adoption in an existing repository, give the coding agent a pointer to this guide and the pinned commit — not a bare "apply the profile". A minimal kick-off prompt:

```text
Read docs/ADOPTION.md of MosslandOpenDevs/agentic-assurance-profile
at commit <FULL_40_CHARACTER_SHA>, then begin adoption of this repository.
This is an existing repository, so follow the brownfield sequence in §4:
1. Perform the read-only archaeology (§4.1) and classification (§4.2)
   without changing any functional code.
2. Copy the templates and draft the core-profile artifacts (§3).
3. Finish with a written proposal listing everything that requires
   human review under §4.3. Do not declare adoption complete;
   approval decisions belong to the human owner.
```

The agent drafts; the human owner approves (§4.3, §6). The expected shape of the proposal is defined in [templates/AGENTIC_ASSURANCE.md](../templates/AGENTIC_ASSURANCE.md) §12.

## 1. Prerequisites

Before creating any file, confirm:

1. **A named human owner or governing body exists.** The profile requires a human authority over purpose, critical claims and invariants, public claim wording, control weakening, and residual acceptance ([PROFILE.md §3](../PROFILE.md)). Adoption cannot proceed without one.
2. **Profiles are chosen provisionally.** Use the smallest applicable set from [PROFILE.md §5](../PROFILE.md). Start with `core`; add others only after assessment (see §4 and §5 below). An agent may propose profiles; the selection remains provisional until the human owner reviews it.
3. **The existing change workflow is identified.** OpenSpec, Spec Kit, ADR/RFC, an issue-driven process, or a minimal one — the profile reuses it rather than replacing it. This becomes the `specification_workflow` entry in the adoption file.
4. **Public repositories have private security intake.** A `SECURITY.md` and GitHub Private Vulnerability Reporting (or an equivalent restricted channel) should exist before assurance artifacts are published; see [../SECURITY.md](../SECURITY.md) and [DISCLOSURE-AND-ISSUES.md](DISCLOSURE-AND-ISSUES.md).

## 2. Pinning: version and commit

Every adopter pins the upstream profile twice in `.agentic-assurance/adoption.yaml`:

```yaml
upstream:
  repository: MosslandOpenDevs/agentic-assurance-profile
  version: REPLACE_WITH_PINNED_VERSION
  # Before the first tagged release, use: unreleased
  commit: REPLACE_WITH_FULL_40_CHARACTER_COMMIT_SHA
```

The pinning rules (normative in [PROFILE.md §16](../PROFILE.md)):

- **Allowed version strings.** `version` is either `unreleased` or a release identifier of the form `vMAJOR.MINOR.PATCH`, optionally with a pre-release suffix `-rc.N`. A `-dev` string is never a valid adopter pin; it appears only in the central repository's `VERSION` file between releases (see [../RELEASING.md](../RELEASING.md)).
- **Version and commit must agree.** Pin only a commit whose `VERSION` file content equals your declared `upstream.version`. In practice that means a release-tag commit — or, during the pre-first-release pilot phase, a commit whose `VERSION` file reads `unreleased`. Conformance checking fails when the pinned version does not match the `VERSION` file at the pinned commit.
- **The full commit SHA is the normative pin.** A floating branch such as `main` must not be the sole reference, and tags — although immutable once published — do not replace the 40-character SHA in the adoption file.
- **Upgrades are explicit.** Moving the pin is a material change with its own review. An agent must not silently update the pin ([PROFILE.md §15](../PROFILE.md)).

### 2.1 Before the first tagged release

Until the profile publishes its first tagged release, pin `version: unreleased` together with the full 40-character SHA of a commit whose `VERSION` file reads `unreleased`. When a release such as `v0.1.0` is published, upgrading to it is an ordinary explicit pin upgrade: update `upstream.version`, `upstream.commit`, and the CI workflow reference (§3.4) in one reviewed change.

## 3. Greenfield adoption

The step-by-step sequence for a repository adopting from the start — or for an existing repository after the archaeology of §4 has been reviewed.

### 3.1 Copy the templates

Everything under [../templates/](../templates/) is published under CC0-1.0: copy it into your repository freely, with no attribution obligation.

| Copy from | To (adopting repository) |
|---|---|
| [templates/AGENTIC_ASSURANCE.md](../templates/AGENTIC_ASSURANCE.md) | `AGENTIC_ASSURANCE.md` |
| [templates/AGENTS.md](../templates/AGENTS.md) | `AGENTS.md` (merge if one exists; see §3.3) |
| [templates/adoption.yaml](../templates/adoption.yaml) | `.agentic-assurance/adoption.yaml` |
| [templates/SYSTEM.md](../templates/SYSTEM.md) | `assurance/SYSTEM.md` |
| [templates/INVARIANTS.yaml](../templates/INVARIANTS.yaml) | `assurance/INVARIANTS.yaml` |
| [templates/RESIDUALS.yaml](../templates/RESIDUALS.yaml) | `assurance/RESIDUALS.yaml` |
| [templates/CLAIMS.yaml](../templates/CLAIMS.yaml) | `assurance/CLAIMS.yaml` (when applicable) |
| [templates/DEFEATERS.yaml](../templates/DEFEATERS.yaml) | `assurance/DEFEATERS.yaml` (when applicable) |
| [templates/THREAT_MODEL.md](../templates/THREAT_MODEL.md) | `assurance/THREAT_MODEL.md` (when applicable) |
| [templates/github/](../templates/github/) | `.github/` — copy the whole bundle; see §3.5 |

The minimum layout matches [templates/AGENTIC_ASSURANCE.md §4](../templates/AGENTIC_ASSURANCE.md): `AGENTS.md`, `AGENTIC_ASSURANCE.md`, `.agentic-assurance/adoption.yaml`, `assurance/SYSTEM.md`, `assurance/INVARIANTS.yaml`, and `assurance/RESIDUALS.yaml`. Optional additions: `assurance/CLAIMS.yaml`, `assurance/DEFEATERS.yaml`, `assurance/THREAT_MODEL.md`, `assurance/decisions/`, `assurance/reviews/`, and `assurance/evidence/`.

These files must live in the adopting repository itself, never only in an organization-level `.github` repository: `AGENTS.md`, `AGENTIC_ASSURANCE.md`, `.agentic-assurance/adoption.yaml`, and everything under `assurance/` (including `DEFEATERS.yaml` when used). Organization defaults may host issue templates and a fallback `SECURITY.md`, but the assurance artifacts are project truth and belong in the project.

### 3.2 Fill in `adoption.yaml`

Replace every `REPLACE_WITH_` token — the validator treats a leftover token in an adopter file as an error. Declare:

- the `upstream` pin per §2;
- `project` name, repository slug, and `human_owner`;
- the `profiles` list (smallest applicable set);
- the `specification_workflow` you identified in §1;
- `paths` mappings when reusing existing conventions ([MAPPINGS.md](MAPPINGS.md)); the defaults are fine for a fresh layout.

### 3.3 Integrate `AGENTS.md`

If the repository has no `AGENTS.md`, start from [templates/AGENTS.md](../templates/AGENTS.md). If one exists, add the "OpenDevs Agentic Assurance" reading-order section defined in [templates/AGENTIC_ASSURANCE.md §11](../templates/AGENTIC_ASSURANCE.md) near the beginning of the existing file. Nested `AGENTS.md` files may impose stricter local rules but must not weaken the adoption.

### 3.4 Wire continuous validation

Add a caller workflow at `.github/workflows/assurance.yml` in the adopting repository:

```yaml
# .github/workflows/assurance.yml
name: assurance
on: [push, pull_request]
jobs:
  assurance:
    uses: MosslandOpenDevs/agentic-assurance-profile/.github/workflows/adopter-validate.yml@REPLACE_WITH_FULL_40_CHARACTER_COMMIT_SHA
```

The `@` reference must be the same full commit SHA you declared as `upstream.commit`. The reusable workflow is pinned exactly like the profile itself; a floating reference such as `@main` reintroduces the un-pinned dependency that the profile prohibits. When upgrading the pin, update `upstream.version`, `upstream.commit`, and this `@` reference in the same change.

The called workflow reads `upstream.repository` and `upstream.commit` from your adoption file, checks out the profile at that pinned commit, and runs the validator against the pinned schemas — never against the latest ones. If your adoption file is not at the default location, pass it explicitly:

```yaml
    with:
      adoption-file: path/to/adoption.yaml
```

The workflow also emits a non-blocking notice when the pinned version trails the latest published release. Staleness never fails the build; upgrading remains an explicit decision.

### 3.5 Copy the GitHub issue-template bundle whole

[templates/github/](../templates/github/) contains issue forms (`bug.yml`, `feature.yml`, `conformance-gap.yml`, `evidence-gap.yml`, `residual-review.yml`), a `config.yml`, and a pull-request template.

**Shadowing warning.** GitHub treats any file in a repository's `.github/ISSUE_TEMPLATE/` directory as a complete replacement for the organization's default template set — including `config.yml`. An incomplete copy (for example, only `conformance-gap.yml`) silently discards the organization's `config.yml`, re-enables blank issues, and drops the contact link that routes vulnerability reports to private security reporting. Copy the whole bundle, `config.yml` included, and replace the `REPLACE_WITH_OWNER_AND_REPOSITORY` placeholder in `config.yml` with your repository slug.

Which form to use for which purpose is defined in [DISCLOSURE-AND-ISSUES.md §4](DISCLOSURE-AND-ISSUES.md).

### 3.6 Validate locally

Check out the profile at the pinned commit and run the adopter validator from the project root:

```bash
git clone https://github.com/MosslandOpenDevs/agentic-assurance-profile .assurance-profile-pin
git -C .assurance-profile-pin checkout REPLACE_WITH_FULL_40_CHARACTER_COMMIT_SHA
pip install pyyaml jsonschema
python .assurance-profile-pin/scripts/validate.py adopter \
  --adoption .agentic-assurance/adoption.yaml \
  --project-root . \
  --schemas .assurance-profile-pin/schemas \
  --profile-checkout .assurance-profile-pin
```

The validator strict-checks the adoption file against the pinned adoption schema, verifies that `upstream.version` matches the `VERSION` file of the pinned checkout, validates every existing YAML artifact at its resolved path, and enforces per-profile presence checks:

| Selected profiles | Files that must exist |
|---|---|
| all adopters | `AGENTIC_ASSURANCE.md` and `AGENTS.md` at the project root |
| `core`, and any other non-`archived` profile | the `system` and `residuals` artifacts |
| `service` | additionally the `invariants` and `threat_model` artifacts |
| `trust-critical` | additionally the `claims` artifact |

It also emits non-blocking warnings: `trust-critical` without a defeaters file; entries classified `RESTRICTED` or `EMBARGOED` (verify the file is not public); a local `.github/ISSUE_TEMPLATE/` without a `config.yml` (§3.5); and selection of the provisional `data-curation` or `agent-runtime` profiles.

## 4. Brownfield adoption

Most adoption is brownfield. Initial adoption of an existing repository must begin as a read-only archaeology task before broad remediation ([PROFILE.md §7](../PROFILE.md)). The practical sequence has four stages; do not compress them into one change, and do not mix archaeology with feature work, security audit, or broad refactoring.

### 4.1 Read-only reconstruction

Before changing any functional code, reconstruct the as-built system:

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

Practical notes:

- Start from what already exists: specifications, ADRs, tests, CI configuration, schemas and migrations, deployment records, and issue and pull-request history. Do not introduce a second specification framework when an adequate one exists.
- Record the reconstruction in the system description; [templates/SYSTEM.md](../templates/SYSTEM.md) mirrors this list section by section.
- Evidence discipline applies from the first line: each non-`UNKNOWN` material conclusion cites concrete evidence — file and line, database constraint, test name, command output, endpoint response, artifact digest, deployment record, or runtime metric. An AI-generated explanation is not evidence by itself.

### 4.2 Classification

Classify observed behavior as `INTENDED`, `ACCIDENTAL`, `COMPATIBILITY`, `UNKNOWN`, or `DEPRECATED`, and each conclusion about the system as `VERIFIED`, `INFERRED`, `UNKNOWN`, or `CONTRADICTED` ([PROFILE.md §4](../PROFILE.md)). `UNKNOWN` is a first-class result: recording uncertainty is correct; inventing confidence is prohibited. Current production behavior is evidence of current behavior, not automatic proof of intended behavior.

### 4.3 Human intent review

Before broad remediation, the human owner reviews:

- purpose and non-goals;
- critical claims and invariants;
- the behavior classification from §4.2;
- critical residuals and public claim limitations.

An agent may draft all of this; it may approve none of it.

### 4.4 Staged remediation

After the intent review:

- record conformance gaps and residuals in the durable artifacts first;
- remediate through separate, scoped issues and pull requests — the `conformance-gap` and `evidence-gap` forms from the adopter bundle (§3.5) exist for exactly this;
- bind new evidence to a commit, artifact digest, release, or deployment identifier;
- map existing conventions instead of duplicating them ([MAPPINGS.md](MAPPINGS.md));
- for critical security, privacy, authorization, financial, governance, or data-integrity work, keep audit and remediation in separate contexts ([PROFILE.md §10](../PROFILE.md)).

## 5. Pilot guidance

For the initial pilot adoptions of this profile (Passport-class projects):

- select `core` only at first;
- run the full §4 brownfield sequence before extending the profile set;
- add `service` once the assessment confirms the repository operates a deployed service, and `trust-critical` only after the assessment establishes which security, identity, or public-verifiability claims the project actually makes — claims drive obligations, not the other way around;
- treat `data-curation` and `agent-runtime` as provisional profiles: their obligations may change in a minor release, and the validator warns on their selection.

## 6. What adoption is not

Creating the files is not adopting the profile. A repository containing `AGENTIC_ASSURANCE.md`, an adoption file, and freshly copied templates has declared an intention — nothing more. Per [templates/AGENTIC_ASSURANCE.md §12](../templates/AGENTIC_ASSURANCE.md), adoption is complete only when:

- the upstream pin resolves to a real version and commit per §2;
- human-approved purpose and non-goals are recorded;
- critical claims and invariants are stated, with enforcement and evidence references or an explicit `UNKNOWN`;
- the residual register is active and owned;
- the material-change workflow references the assurance artifacts in normal review.

A green validator run checks structure, presence, and pin consistency — not the truth of the claims. And conformance itself is bounded: it means the project's promises, controls, evidence, and remaining doubt are represented according to the pinned profile, not that the project is secure or bug-free ([PROFILE.md §17](../PROFILE.md)).

## Related documents

- [PROFILE.md](../PROFILE.md) — the normative profile text
- [MAPPINGS.md](MAPPINGS.md) — reusing existing conventions via `paths:`
- [DISCLOSURE-AND-ISSUES.md](DISCLOSURE-AND-ISSUES.md) — issue routing and disclosure rules
- [templates/AGENTIC_ASSURANCE.md](../templates/AGENTIC_ASSURANCE.md) — the adopter-side entry document
- [templates/adoption.yaml](../templates/adoption.yaml) — the adoption file template
- [RELEASING.md](../RELEASING.md) — release ritual and the `VERSION` file lifecycle
- [SECURITY.md](../SECURITY.md) — vulnerability reporting for this repository
