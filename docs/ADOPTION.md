# Adoption Guide

This document is the practical walk-through for adopting the OpenDevs Agentic Assurance Profile in a repository. The normative obligations live in [PROFILE.md](../PROFILE.md); this guide operationalizes them with mechanical detail: which files to copy, what to pin, how to wire continuous validation, and how to sequence adoption in an existing codebase. Where this guide and PROFILE.md appear to disagree, PROFILE.md governs.

To reuse existing repository conventions instead of the default artifact paths, see [MAPPINGS.md](MAPPINGS.md).

## 0. Quick start for AI agents

To start adoption in an existing repository, give the coding agent a pointer to this guide and the pinned commit — not a bare "apply the profile". A minimal kick-off prompt:

```text
Read docs/ADOPTION.md of MosslandOpenDevs/agentic-assurance-profile
at commit <FULL_40_CHARACTER_SHA>, then begin adoption of this repository.
This is an existing repository, so follow the brownfield sequence in §4:
1. Classify the profile from evidence (§4.0) — determine which §5
   profiles apply from what this repository is and promises; do not
   assume `core`, and cite file:line for each trigger that fires.
2. If the classification is active, perform the read-only archaeology
   (§4.1) and behavior classification (§4.2) without changing any
   functional code. If it is `archived`, follow §4.1's narrower path:
   establish with evidence that the repository is retained solely for
   historical reference, is not supported or intended for current use,
   and has no active operation, functional maintenance, or feature
   development; reconstruct only the four §6.6 historical facts;
   do not fabricate active registers.
3. Copy the templates and draft the artifacts for the classified
   profile(s) and layout (§3).
4. Finish with a written proposal listing everything that requires
   human review under §4.3 — the active-system decisions for an
   active profile, or the exclusive classification and four facts for
   `archived`. Do not declare adoption complete; approval decisions
   belong to the human owner.
5. Keep all changes on a branch and open a draft pull request;
   do not merge to the default branch — merging is the human
   owner's act after the §4.3 review.
6. End with a handoff summary addressed to the human owner,
   written in the owner's working language: state first that
   nothing is decided yet and the pull request must not be merged
   until the owner has answered; then list each decision the
   owner must make, in plain language (see docs/REVIEW-GUIDE.md).
   Never describe the draft as 'settled', 'complete', or 'done'.
```

The agent drafts; the human owner approves (§4.3, §6). The expected shape of the proposal is defined in [templates/AGENTIC_ASSURANCE.md](../templates/AGENTIC_ASSURANCE.md) §12. If you are the human owner receiving the result, start with the review guide, [REVIEW-GUIDE.md](REVIEW-GUIDE.md); unfamiliar terminology is defined in [GLOSSARY.md](GLOSSARY.md).

## 1. Prerequisites

Before creating any file, confirm:

1. **A named human owner or governing body exists.** For an active adoption, the profile requires human authority over purpose, critical claims and invariants, public claim wording, control weakening, and residual acceptance; for `archived`, the owner confirms the exclusive reference-only classification and four historical facts ([PROFILE.md §3](../PROFILE.md), [§7](../PROFILE.md)). Adoption cannot proceed without one.
2. **Profiles are chosen by classification, not by default.** Determine the profile set from what the repository is and promises, per §4.0 — the smallest set that *covers every trigger that fires*, which is not the same as starting at `core` and escalating later. Active specialized profiles inherit `core` obligations without needing `core` in the declaration: for an active classification, declare `[core]` only when no specialized trigger fires; otherwise list the fired specialized profiles. `archived` is the exclusive alternative. An agent may propose the set, with `file:line` evidence for each fired trigger; the selection remains provisional until the human owner reviews it (§4.3).
3. **For an active adoption, the existing change workflow is identified.** OpenSpec, Spec Kit, ADR/RFC, an issue-driven process, or a minimal one — the profile reuses it rather than replacing it. This becomes the `specification_workflow` entry in the adoption file. An `archived` adopter MAY omit that optional block when no archival-record workflow exists; it must not invent an active workflow merely to fill the template.
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

- **Allowed version strings.** `version` is either `unreleased` or a release identifier of the form `vMAJOR.MINOR.PATCH`, optionally with a pre-release suffix `-rc.N`. Numeric identifiers use ASCII decimal digits with no leading zero unless the identifier is exactly zero, and `N` starts at 1. A `-dev` string is never a valid adopter pin; it appears only in the central repository's `VERSION` file between releases (see [../RELEASING.md](../RELEASING.md)).
- **Version and commit must agree.** Pin only a commit whose `VERSION` file content equals your declared `upstream.version`. In practice that means a release-tag commit — or, during the pre-first-release pilot phase, a commit whose `VERSION` file reads `unreleased`. Conformance checking fails when the pinned version does not match the `VERSION` file at the pinned commit.
- **The tag commit is the canonical release pin.** More than one commit can carry a release identifier in its `VERSION` file — the release pull request's branch commit and the merge commit the tag points to are distinct SHAs with identical content. Pin the commit the tag points to: `git rev-list -n1 vX.Y.Z`, or the commit shown on the [release page](https://github.com/MosslandOpenDevs/agentic-assurance-profile/releases). The CI workflow fails a release pin whose commit is not the tag commit (first-trial lesson).
- **The full commit SHA is the normative pin.** A floating branch such as `main` must not be the sole reference, and tags — although immutable once published — do not replace the 40-character SHA in the adoption file.
- **Upgrades are explicit.** Moving the pin is a material change with its own review. An agent must not silently update the pin ([PROFILE.md §15](../PROFILE.md)).

### 2.1 Before the first tagged release

Until the profile publishes its first tagged release, pin `version: unreleased` together with the full 40-character SHA of a commit whose `VERSION` file reads `unreleased`. When a release such as `v0.1.0` is published, upgrading to it is an ordinary explicit pin upgrade: update `upstream.version`, `upstream.commit`, and the CI workflow reference (§3.4) in one reviewed change.

## 3. Greenfield adoption

The step-by-step sequence for a repository adopting from the start — or for an existing repository after the archaeology of §4 has been reviewed.

### 3.0 Lite adoption — for a confirmed core-only repository

Use the lite layout only after the §4.0 classification confirms the repository is `core` alone — no `service`, `trust-critical`, `data-curation`, or `agent-runtime` trigger fires, and it is not `archived`. Lite is the residual layout for a genuinely core-only repository, not a default to start from and escalate away from later.

A repository adopting `core` only does not need the full split layout that the rest of this section describes. The lite layout collapses the project-specific assurance register content into a single file and brings first adoption down to four required profile files: an `AGENTS.md` carrying the assurance reading-order section (§3.3), `AGENTIC_ASSURANCE.md` at the root, `.agentic-assurance/adoption.yaml` (§3.2) declaring `layout: lite`, and `.agentic-assurance/assurance.yaml` holding the purpose, non-goals, invariants, residuals, and normally an inline system description. A recorded mapping to an existing system artifact may supply that description instead. Those four are the profile's own files; alongside them `specification_workflow.root` must resolve to the material-change workflow entry document — PROFILE.md §6.1 requires a non-empty repository-local entry document or directory, and §3.6 errors when the mapped path does not exist. Reuse an existing CONTRIBUTING/ADR/spec file where one exists; in a genuinely greenfield repository where none does, that is a fifth file to create. Copy from the same CC0-1.0 template set:

| Copy from | To (adopting repository) |
|---|---|
| [templates/AGENTIC_ASSURANCE.md](../templates/AGENTIC_ASSURANCE.md) | `AGENTIC_ASSURANCE.md` |
| [templates/AGENTS.md](../templates/AGENTS.md) | `AGENTS.md` (merge if one exists; see §3.3) |
| [templates/adoption.yaml](../templates/adoption.yaml) | `.agentic-assurance/adoption.yaml`, adding `layout: lite` and setting `security.public_assurance_root: .agentic-assurance` |
| [templates/assurance.minimal.yaml](../templates/assurance.minimal.yaml) | `.agentic-assurance/assurance.yaml` — the required-minimum starting point (purpose, non-goals, system, one invariant, one residual) |

For an expanded reference showing the standard optional fields, the optional `defeaters` section, and the local `extensions` namespace, copy [templates/assurance.yaml](../templates/assurance.yaml) instead. Both shipped templates include an inline `system` value, so either is a complete four-file starting path and both face the same adopter schema and semantic checks after copying. If you delete that optional field, add a separate system artifact at `paths.system`. The minimal template exists so a fresh `core` adoption sees only what it must fill in. Register schemas permit some project-local entry fields, so the expanded reference is intentionally not a catalogue of every possible extension.

`assurance.yaml` starts with `version: 1` and carries the `core` obligations of [PROFILE.md §6.1](../PROFILE.md) as sections:

- `purpose` (string, required) and `non_goals` (list of strings, required) — §6.1 requires human-approved purpose and non-goals;
- `system` (string, optional) — the inline form of §6.1's current system description. It must identify the system being assured, its principal responsibilities and material boundaries, and known material limitations or unknowns; lite changes the layout, not this content minimum. When omitted, keep an equivalent description at the `paths.system` location instead (`assurance/SYSTEM.md` by default); one of the two must exist;
- `invariants` (required at `core` — at least one; it anchors the regression protection), `residuals` (required), and `defeaters` (optional) — arrays whose entries have exactly the same shape as in the split register files. The item schemas are not forked: the validator checks each present section against the corresponding register schema and runs the same semantic checks over the combined result, so lite and split registers are interchangeable content.

**Lite is core-only.** Declaring `layout: lite` together with any profile beyond `core` — `service`, `trust-critical`, `data-curation`, `agent-runtime`, or `archived` — is a validation error. The validator enforces the split layout for every specialized or `archived` profile, but those two transitions have different content obligations.

To graduate to an **active specialized profile**, preserve every register ID by moving each present `invariants`, `residuals`, and `defeaters` array unchanged into `assurance/INVARIANTS.yaml`, `assurance/RESIDUALS.yaml`, and `assurance/DEFEATERS.yaml`. Move the inline `system` prose into the artifact mapped by `paths.system`. Preserve lite `purpose` and `non_goals` in that mapped artifact or another owner-approved local intent artifact, and preserve or deliberately relocate every entry under `extensions`. Only after all of that content is represented in the split layout may you remove `layout: lite`.

To reclassify as **`archived`**, do not treat that active-layout migration as the archived contract. Write all four §6.6 facts in the artifact mapped by `paths.system` and have the human owner confirm them: historical-reference-only/non-operational status, historical purpose, known material limitations, and the last supported revision or release (or an explicit statement that none exists). Prior active registers may be retained as optional historical material, but they do not supply or substitute for any of those four facts. Remove `layout: lite` only after the archived record is complete.

At `core`, the [templates/github/](../templates/github/) issue-template bundle (§3.5) and a `CODEOWNERS` file are optional rather than part of the minimum: copy the bundle when the repository takes external contributions — recommended in that case, and copy it whole, since the shadowing warning of §3.5 applies — and use `CODEOWNERS` wherever a second maintainer exists to review. PROFILE.md §6 still requires effective human-owner review of the policy locations; a repository without enforceable code-owner approval uses its equivalent repository control or attributable review record rather than pretending a self-approval occurred.

§3.1–§3.5 describe the split layout, used for every specialized or `archived` profile, or at `core` by preference. Local validation for both layouts is §3.6.

### 3.1 Copy the templates

This and the following subsections describe the split layout — one file per applicable artifact, including one file per active register — used for every specialized or `archived` profile, or at `core` by preference (§3.0 covers the lite alternative). Everything under [../templates/](../templates/) is published under CC0-1.0: copy it into your repository freely, with no attribution obligation.

| Copy from | To (adopting repository) |
|---|---|
| [templates/AGENTIC_ASSURANCE.md](../templates/AGENTIC_ASSURANCE.md) | `AGENTIC_ASSURANCE.md` |
| [templates/AGENTS.md](../templates/AGENTS.md) | `AGENTS.md` (merge if one exists; see §3.3) |
| [templates/adoption.yaml](../templates/adoption.yaml) | `.agentic-assurance/adoption.yaml` |
| [templates/SYSTEM.md](../templates/SYSTEM.md) | `assurance/SYSTEM.md` |
| [templates/INVARIANTS.yaml](../templates/INVARIANTS.yaml) | `assurance/INVARIANTS.yaml` (required for every active profile; at least one entry; not required for `archived`) |
| [templates/RESIDUALS.yaml](../templates/RESIDUALS.yaml) | `assurance/RESIDUALS.yaml` (required for every active profile; not required for `archived`) |
| [templates/CLAIMS.yaml](../templates/CLAIMS.yaml) | `assurance/CLAIMS.yaml` (required under active `trust-critical`; optional elsewhere) |
| [templates/DEFEATERS.yaml](../templates/DEFEATERS.yaml) | `assurance/DEFEATERS.yaml` (active profiles, when applicable) |
| [templates/THREAT_MODEL.md](../templates/THREAT_MODEL.md) | `assurance/THREAT_MODEL.md` (required under active `service`; optional elsewhere) |
| [templates/github/](../templates/github/) | `.github/` — copy the whole bundle; see §3.5 |

For an active adopter, the split-layout minimum matches [templates/AGENTIC_ASSURANCE.md §4](../templates/AGENTIC_ASSURANCE.md) and PROFILE.md §6.1: `AGENTS.md`, `AGENTIC_ASSURANCE.md`, `.agentic-assurance/adoption.yaml`, `assurance/SYSTEM.md`, `assurance/INVARIANTS.yaml`, and `assurance/RESIDUALS.yaml`. `assurance/INVARIANTS.yaml` carries at least one invariant — the properties that must remain true; it anchors the regression protection, and is required by the inherited `core` obligations (a repository with nothing that must stay true has not found its invariants yet). The exclusive `archived` profile does not inherit those active obligations: its split-layout assurance minimum is the system artifact containing §6.6's four facts; the root adoption and agent-instruction files remain required. Optional additions for active profiles: `assurance/CLAIMS.yaml`, `assurance/DEFEATERS.yaml`, `assurance/THREAT_MODEL.md`, `assurance/decisions/`, `assurance/reviews/`, and `assurance/evidence/`.

These files must live in the adopting repository itself, never only in an organization-level `.github` repository: `AGENTS.md`, `AGENTIC_ASSURANCE.md`, `.agentic-assurance/adoption.yaml`, and everything under `assurance/` (including `DEFEATERS.yaml` when used). Organization defaults may host issue templates and a fallback `SECURITY.md`, but the assurance artifacts are project truth and belong in the project.

### 3.2 Fill in `adoption.yaml`

Replace every `REPLACE_WITH_` token in the adoption declaration — the validator treats a leftover token there as an error at every stage. Register placeholders remain permitted only while the declared stage is `DRAFT`, as described in §3.8. Declare:

- the `upstream` pin per §2;
- `project` name, repository slug, and `human_owner`;
- the `profiles` list (from the §4.0 classification — for an active adopter, `[core]` when no specialized trigger fires, otherwise the fired specialized profiles, which inherit `core`; or `[archived]` alone);
- `layout: lite` when using the single-file layout of §3.0 (the field is optional; absent means the split layout);
- for an active adoption, the `specification_workflow` identified in §1; for `archived`, keep it only when a real archival-record workflow applies, otherwise delete the optional template block;
- `paths` mappings when reusing existing conventions ([MAPPINGS.md](MAPPINGS.md)); the defaults are fine for a fresh layout.

If the declaration itself will live anywhere other than `.agentic-assurance/adoption.yaml`, treat that location as one coordinated mapping: pass the same repository-relative path as the workflow's `adoption-file`, and replace `.agentic-assurance/adoption.yaml` with that path in the reading-order block in **both** root `AGENTIC_ASSURANCE.md` and root `AGENTS.md`. The standalone block is otherwise copied verbatim; this synchronized path substitution is the one permitted adaptation.

### 3.3 Integrate `AGENTS.md`

If the repository has no `AGENTS.md`, start from [templates/AGENTS.md](../templates/AGENTS.md). If one exists, add the "OpenDevs Agentic Assurance" reading-order section defined in [templates/AGENTIC_ASSURANCE.md §11](../templates/AGENTIC_ASSURANCE.md) near the beginning of the existing file. Keep that block verbatim unless the workflow uses a custom `adoption-file`; in that case, substitute the same custom declaration path in the reading order in both root files and change nothing else in the block. Nested `AGENTS.md` files may impose stricter local rules but must not weaken the adoption.

### 3.4 Wire continuous validation

Add a caller workflow at `.github/workflows/assurance.yml` in the adopting repository:

```yaml
# .github/workflows/assurance.yml
name: assurance
on:
  push:
  pull_request:
    types: [opened, synchronize, reopened, edited, ready_for_review]
jobs:
  assurance:
    uses: MosslandOpenDevs/agentic-assurance-profile/.github/workflows/adopter-validate.yml@REPLACE_WITH_FULL_40_CHARACTER_COMMIT_SHA
```

The explicit `pull_request` types matter: the drift check (§3.7) reads impact directives and no-impact statements from the pull-request description, and the default types do not include `edited` — without it, editing the description after the fact would leave a stale verdict standing.

The `@` reference must be the same full commit SHA you declared as `upstream.commit`. The reusable workflow is pinned exactly like the profile itself; a floating reference such as `@main` reintroduces the un-pinned dependency that the profile prohibits. When upgrading the pin, update `upstream.version`, `upstream.commit`, and this `@` reference in the same change.

For safety the reusable workflow executes the validator only from its own identity: the repository and commit of the workflow file itself (`job.workflow_repository` / `job.workflow_sha`), verified to be the canonical upstream `MosslandOpenDevs/agentic-assurance-profile` before use. Your `upstream.repository` is validated as data, `upstream.commit` must equal the workflow's own commit (the documented same-change rule, enforced), and a caller that references the workflow by tag or branch instead of a full 40-character SHA is rejected. The workflow runs with `contents: read`, does not persist checkout credentials, pins its actions to full commit SHAs (and its lint image by digest), and installs only hash-locked dependencies. If you adopt from a fork of the profile, run your own copy of `adopter-validate.yml` with its `CANONICAL` constants changed to your fork. The `job.workflow_*` contexts it relies on do not exist on GitHub Enterprise Server; the workflow targets GitHub.com.

**The honest boundary of the caller workflow.** The caller file above lives in *your* repository, and `pull_request` events run the pull request's version of it — a pull request can change the `@` reference, or replace the caller entirely, and thereby run an older or different workflow; GitHub required status checks are matched by check name, which another workflow can reproduce. No content of the reusable workflow can defend that boundary. What does:

- **CODEOWNERS on `.github/workflows/`** with required code-owner review — the adopter bundle's CODEOWNERS template (§3.5) already covers the caller workflow; this is the primary control, and a caller swap is always visible in the PR diff.
- **Organization Actions policies** (free plan): restrict allowed actions and reusable workflows so only the canonical profile's workflow can be called.
- **Organization rulesets with required workflows** (GitHub Team/Enterprise): a centrally-required workflow that a repository pull request cannot modify — the right anchor once assurance checks become mandatory across many repositories. Until then, treat a green check as an input to human review, not as a tamper-proof verdict.

The called workflow validates your tree against the pinned schemas — never against the latest ones. If your adoption file is not at the default location, pass it explicitly:

```yaml
    with:
      adoption-file: path/to/adoption.yaml
```

That input changes where validation reads the declaration; it does not rewrite project instructions or ownership rules for you. Make the same `path/to/adoption.yaml` substitution in the assurance reading order in both root `AGENTIC_ASSURANCE.md` and root `AGENTS.md`, and extend the effective owner-review boundary to that exact declaration path. When `CODEOWNERS` supplies that boundary, add the path there as described in §3.5.

The workflow also emits a non-blocking notice when the pinned version trails the latest published release. Staleness never fails the build; upgrading remains an explicit decision.

### 3.5 Copy the GitHub issue-template bundle whole

[templates/github/](../templates/github/) contains issue forms (`bug.yml`, `feature.yml`, `conformance-gap.yml`, `evidence-gap.yml`, `residual-review.yml`), a `config.yml`, and a pull-request template.

**Shadowing warning.** GitHub treats any file in a repository's `.github/ISSUE_TEMPLATE/` directory as a complete replacement for the organization's default template set — including `config.yml`. An incomplete copy (for example, only `conformance-gap.yml`) silently discards the organization's `config.yml`, re-enables blank issues, and drops the contact link that routes vulnerability reports to private security reporting. Copy the whole bundle, `config.yml` included, and replace the `REPLACE_WITH_OWNER_AND_REPOSITORY` placeholder in `config.yml` with your repository slug.

**Labels must exist before the forms can apply them.** The issue forms reference labels — `assurance/gap`, `assurance/evidence`, `assurance/residual`, `needs-human-approval`, and the common `bug`, `enhancement`, `question`, and `documentation` — and GitHub silently drops any label a form references that does not already exist in the repository: the issue is still created, just unlabeled. Create the missing ones once, for example:

```bash
for L in "assurance/gap" "assurance/evidence" "assurance/residual" "needs-human-approval"; do gh label create "$L" --repo OWNER/REPO --color 5319e7 2>/dev/null || true; done
```

Adjust the list and colors to your conventions; the common labels (`bug`, `enhancement`, `question`, `documentation`) exist by default in most repositories but are worth verifying.

Which form to use for which purpose is defined in [DISCLOSURE-AND-ISSUES.md §4](DISCLOSURE-AND-ISSUES.md).

**Bind the assurance layer to the owner.** PROFILE.md §6 requires an effective owner-review boundary; a file named `CODEOWNERS` without enforced review is not that boundary. On GitHub where independent code-owner approval is available, the bundle's [CODEOWNERS](../templates/github/CODEOWNERS) template covers the default `AGENTS.md`, `AGENTIC_ASSURANCE.md`, `.agentic-assurance/`, `assurance/`, `SECURITY.md`, and CI-caller locations. Copy it to `.github/CODEOWNERS` (merge into an existing file), replace the placeholder with the owner's `@handle` or `@org/team`, and enable branch protection with required reviews and "Require review from Code Owners" on the default branch. For both standard defaults and custom locations, ensure that whichever effective review mechanism the repository uses covers the effective adoption declaration, **every** effective artifact location selected under `paths:`, `specification_workflow.root`, `human_review.record`, `security.policy`, and `security.public_assurance_root`; the shipped template supplies rules for its standard locations, while every custom declaration or mapping needs an explicit added rule. A custom mapping must not move policy outside owner review. If any such location is a tracked in-project symlink, keep the lexical symlink path itself (so retargeting requires review), its resolved target, and the resolved target's parent or containing tree inside that boundary. GitHub CODEOWNERS must list all three because it matches changed Git paths and does not transfer ownership from the link to its target. This is what stops an agent from silently weakening an invariant, closing a residual, or moving the upstream pin — the most common failure mode of assurance adoption is exactly documents landing while this binding lags, which leaves unverifiable claims in public. Honest caveat for single-maintainer repositories: GitHub does not allow self-approval, so the binding becomes fully effective only once a second maintainer exists; until then the attributable review record is the effective control, and a CODEOWNERS file is only a declared intention (the same stance this profile's own [GOVERNANCE.md](../GOVERNANCE.md) takes).

### 3.6 Validate locally

Check out the profile at the pinned commit and run the adopter validator from the project root:

```bash
git clone https://github.com/MosslandOpenDevs/agentic-assurance-profile .assurance-profile-pin
git -C .assurance-profile-pin checkout REPLACE_WITH_FULL_40_CHARACTER_COMMIT_SHA
pip install --require-hashes -r .assurance-profile-pin/requirements-ci.txt  # or: pip install pyyaml jsonschema
python -I .assurance-profile-pin/scripts/validate.py adopter \
  --adoption .agentic-assurance/adoption.yaml \
  --project-root . \
  --schemas .assurance-profile-pin/schemas \
  --profile-checkout .assurance-profile-pin
```

The validator strict-checks the adoption file against the pinned adoption schema and verifies that `upstream.version` matches the exact token in the pinned checkout's `VERSION` file. When the checkout has Git metadata, it also requires its `HEAD` commit to equal `upstream.commit`, verifies that the process is executing that checkout's `scripts/validate.py`, rejects symlink substitutes for the consumed validator/schema resources, and requires `VERSION`, `requirements-ci.txt`, `scripts/`, and `schemas/` to be clean relative to that `HEAD` (including no untracked files under the two resource directories). This prevents a nominally correct commit from validating with locally replaced code or schemas. A source/archive copy without Git metadata emits a warning because neither commit identity nor worktree cleanliness can be established locally; use the documented Git checkout for a mechanically verified pin. It then validates every existing YAML artifact at its resolved path and enforces per-profile presence checks:

Adopter-owned artifact, workflow, and review-record paths are resolved through symlinks before they are trusted. Their final targets must remain inside the adopting project and outside Git metadata (`.git`), the pinned profile checkout, and the schema tree. A portable relative symlink whose every hop stays in the repository remains valid; an absolute symlink is rejected even when it currently points back inside, as is a relative link that escapes and later re-enters, because detached BASE worktrees would resolve either spelling differently. A broken link, an escape from the project, or a link back into trusted upstream/template data also fails closed. This trust-boundary check is separate from owner binding: for every accepted path that traverses an in-project symlink, the validator emits a warning naming the lexical path and resolved target and reminding the adopter to protect the lexical path (including retargeting), resolved target, and target parent in CODEOWNERS. The warning cannot inspect branch-protection settings or prove that those rules are effective.

Every policy YAML input is limited to 5,242,880 bytes and 100,000 logical
nodes after aliases are expanded. The logical-node bound prevents a compact
alias graph from representing an exponentially large policy tree; split an
oversized declaration or register instead of relying on aliases to compress it.
Separately, each adopter-owned UTF-8 prose or review file that the validator
reads directly is limited to 5,242,880 bytes: root `AGENTIC_ASSURANCE.md` and
`AGENTS.md`, the mapped system artifact, the required `service` threat model,
and a declared `human_review.record`. Keep larger background material outside
those control entry files and link to it from a bounded artifact.

| Selected profiles | Files that must exist |
|---|---|
| all adopters | non-empty `AGENTIC_ASSURANCE.md` and `AGENTS.md` at the project root, with the assurance reading-order references required by PROFILE.md §6 |
| non-`archived` profiles | additionally a §6.1 system description (inline under lite or at `paths.system` under split) and non-empty `invariants` and `residuals` artifacts |
| `archived` | the non-empty system artifact resolved from `paths.system` (default `assurance/SYSTEM.md`), where §6.6's four facts are recorded |
| `service` | additionally the `threat_model` artifact |
| `trust-critical` | additionally the `claims` artifact |

Presence is not enough where PROFILE.md mandates content: root `AGENTIC_ASSURANCE.md` and `AGENTS.md` must establish the assurance reading order, every active adoption must identify a real project-local material-change workflow, the `residuals` and `invariants` registers must each carry at least one entry for every non-archived profile, and `claims` at least one under `trust-critical` — an empty array satisfies every per-entry check vacuously and passes no obligation. A `specification_workflow.root` file must be readable, non-empty UTF-8 text and no larger than 1 MiB. A mapped directory must contain such a regular entry document within the validator's bounded recursive scan (16 directory levels, 4,096 entries, 1 MiB per candidate file, and 8 MiB aggregate inspected content); child symlinks are not followed, and Git metadata plus the actual pinned profile/schema checkout are excluded wherever they live (including the conventional `.git` and `.assurance-profile-pin` locations). Map a narrower directory or its entry document when those bounds are exceeded. Two `issue_integration` values are fixed rather than declared: `public_security_issues_allowed` must be `false` and `closing_requires_artifact_update` must be `true` (PROFILE.md §14), for a private repository as much as a public one — `--repo-visibility private` does not relax either. A project that believes it has zero residual risk should record that belief as its first residual. Since v0.3.0 the register schemas also reject empty or whitespace-only strings in semantic fields (`owner`, `statement`, `enforcement[]`, `evidence[]`, `accepted_by`, ...), matching the lite envelope's rules.

For active prose, the mechanical boundary is narrower than the normative content rule. The validator requires a non-empty inline or mapped system description and, from `HUMAN_REVIEWED`, rejects generic `REPLACE_WITH_` markers. A service's mapped threat model must likewise be a non-empty file at every stage and marker-free from `HUMAN_REVIEWED`. It does not decide whether arbitrary prose actually identifies all §6.1 responsibilities, boundaries, limitations, or unknowns, or whether a threat model is substantively adequate. The applicable §4.3 human review remains responsible for that semantic judgment; a non-empty string by itself is not evidence that the content minimum is met.

Under `layout: lite` (§3.0) the same command applies, with two differences. `.agentic-assurance/assurance.yaml` is validated — the envelope against the lite schema, each present section against the corresponding register schema, and the combined content through the same semantic checks. And the split per-profile file checks are replaced by the lite rules: the file itself must exist, `invariants` and `residuals` must each be present and non-empty, either a `system` section or a file at `paths.system` must exist, and any profile beyond `core` is an error pointing to the graduation path of §3.0.

It also emits non-blocking warnings: `trust-critical` without a defeaters file; entries classified `RESTRICTED` or `EMBARGOED` (verify the file is not public); a local `.github/ISSUE_TEMPLATE/` without a `config.yml` (§3.5); selection of the provisional `agent-runtime` profile; selection of the `archived` profile; and, under `layout: lite`, a `security.public_assurance_root` still pointing at the split-layout `assurance` directory. For `archived`, validation enforces exclusive declaration and a non-empty mapped system artifact; from `HUMAN_REVIEWED` it also rejects the four exact archived markers shipped in `templates/SYSTEM.md`. It does not parse arbitrary replacement prose for the four facts or determine their truth: until structured enforcement in [#40](https://github.com/MosslandOpenDevs/agentic-assurance-profile/issues/40), human review must confirm all four §6.6 facts in that artifact.

Entries classified `RESTRICTED` may be committed to a private repository, but they bind its visibility: the repository must not be made public while `RESTRICTED` material is present. Before any publication, sanitize `RESTRICTED` entries to `SUMMARY_ONLY` or `PUBLIC`, or move them to the restricted record ([DISCLOSURE-AND-ISSUES.md](DISCLOSURE-AND-ISSUES.md)). The validator's `RESTRICTED` warnings exist to keep this constraint visible on every run.

### 3.7 Impact routing (optional): wire code changes to invariants

An invariant register protects against regressions only when the changes that enter an invariant's territory are confronted with it. The optional `components` map in `adoption.yaml` makes that confrontation mechanical — it is what turns the register from documentation into a regression gate:

```yaml
components:
  authentication:
    paths: [ "src/auth/**", "migrations/session_*" ]   # required, gitwildmatch-style globs
    invariants: [ INV-AUTH-001, INV-AUTH-004 ]          # required, existing invariant IDs
    tests: [ "tests/auth/**" ]                          # optional, informational in this release
```

Each component names the repository paths it covers — gitwildmatch-style globs, where `**` crosses directory boundaries and `*`/`?` stay within one path segment — and the invariant IDs those paths protect. Each glob must itself be a canonical repository-relative pattern: absolute spellings, C0 controls or DEL, and empty, `.` or `..` slash-delimited components fail because they cannot soundly share the declared routing syntax; `*` or `?` can still match such a character in a legal Git filename. `tests` is recorded but not checked in this release. Routing is explicitly resource-bounded: at most 256 components, 256 path globs and 256 invariant IDs per component, and 20,000 changed paths; component names and invariant IDs are at most 256 characters, each path glob at most 1,024 characters, and each changed path at most 4,096 characters. Duplicate path globs and invariant IDs remain accepted for v0.3 compatibility, have no additional routing meaning, and still count toward those limits; deduplicate them when editing. Before matching, the validator also caps aggregate glob work at 20,000,000 dynamic-programming cells and impact-directive scanning (including ID compilation cost) at 20,000,000 bounded work units. Input files are capped at 33,554,432 bytes for changed paths, 1,048,576 bytes for the PR body, and 20,971,520 bytes for the assurance diff. A standalone changed-file list must contain canonical repository-relative Git paths: absolute paths, escapes, and `.`/`..` or empty path components fail closed; one legacy leading `./` is normalized for compatibility. NUL-separated input preserves path boundaries for supported UTF-8 Git names containing newlines or edge spaces; non-UTF-8 input fails closed because component globs are Unicode strings. Split a large change or reduce and narrow an oversized component map when a total would exceed either bound.

**Known event limitation in v0.4.x:** the reusable workflow implements `drift` only when the caller's `github.event_name` is `pull_request`. A green push or other non-`pull_request` workflow run reports only the checks that actually ran; it is not a drift verdict. Push is outside the documented drift scope, while applicability for other caller events — including `pull_request_target`, `merge_group`, `workflow_dispatch`, and `schedule` — remains unresolved in [#43](https://github.com/MosslandOpenDevs/agentic-assurance-profile/issues/43). Do not interpret the skipped drift job as a completed policy comparison.

When the map is present, the reusable workflow (§3.4) runs a drift check on every pull request, against the pinned validator like everything else; push-event runs are unaffected. Changed files are computed rename-safely: a rename or copy counts both its source and its destination path, so moving code out of a mapped path cannot escape the component's globs. For each component whose `paths` match at least one changed file, the pull request satisfies that component if any of the following holds. In the pull-request description, only visible prose outside HTML comments and fenced code blocks is eligible: hidden example IDs, no-impact directives, reasons, and policy acknowledgments are ignored, and an unclosed comment or fence conservatively hides the remainder. PR declarations live in one **leading top-level directive block**: after those exclusions, it starts at the first visible nonblank line and ends at the first ordinary visible nonblank line. Its recognized lines are `Assurance impact:`, the mandatory `Reason:` for `none`, and the optional `Assurance policy change:` acknowledgment below. Every directive starts at column one; blank lines and HTML comments may separate or precede them. A heading, prose line, blockquote, or link-definition line ends or prevents the block, so a later directive is ignored. When impact is declared, the block must contain **exactly one** `Assurance impact:` line — either a comma-separated exact-ID list or `none`; duplicate, conflicting, or malformed impact lines satisfy neither form. When combined, put that single impact line first, then its `Reason:` when applicable, then `Assurance policy change:`. This fixed boundary prevents IDs embedded in presentation or metadata from becoming declarations.

1. the **net-new lines** of the assurance-artifact evidence diff reference at least one of the component's invariant IDs, matched with token boundaries. CI constructs that small diff from exact invariant-bearing lines in regular, strict UTF-8 text blobs reached by **HEAD-active** impact bindings: the two root guides and current configured declaration; the exact current active-layout artifacts (split defaults/mappings, or the lite file plus its active fallback system and local extension mappings); applicable current workflow, review, and security locations; and contained tracked regular-file targets of those bindings. A directory-root binding that resolves to the repository root — whether written `.` or reached through a permitted in-project symlink — remains containment-, trust-, and retarget-checked but contributes no positive evidence: otherwise an invariant ID added to ordinary source code could satisfy its own routing gate. Use a narrower policy location or an explicit PR-body directive. Control-heavy or invalid-UTF-8 blobs, PDF containers, gitlinks, and HEAD symlink target-name blobs are not prose evidence. Before emitting a line, CI cancels every exact invariant-bearing line that existed anywhere in the pull request's **merge-base tree**; that cancellation side is deliberately broader and includes non-text and symlink blobs. Consequently an unchanged line cannot become evidence merely because it was renamed, copied while retaining its source, remapped, changed from symlink to regular file, cleaned from binary/PDF to text eligibility, or left on the PR branch after the current base tip deleted it. This repository-wide cancellation is conservative: adding an exact line that already existed elsewhere requires the explicit PR-body impact directive instead. The generated diff contains only canonical invariant IDs, not adopter paths or surrounding prose. Base bindings are still trust-checked and compared for policy regression, but an old-layout or otherwise base-only artifact that this pull request deactivates cannot contribute positive routing evidence. Every explicitly declared filesystem path remains containment- and retarget-checked, while a known split-role mapping inactive under inline lite likewise cannot contribute evidence. Merely touching an assurance file is not enough, deleting an entry does not count, and a longer ID such as `INV-CORE-001-EXT-002` does not satisfy `INV-CORE-001`;
2. the first visible nonblank line of the pull-request description is the block's **only** top-level impact directive, whose comma-separated values include every invariant ID listed for the component. It contains exact IDs rather than prose or substrings and uses this form (so a second or conflicting impact line, an arbitrary mention elsewhere, a bulleted list, or `INV-CORE-001-EXT-002` does not satisfy `INV-CORE-001`):

```text
Assurance impact: INV-CORE-001, INV-CORE-002
```

3. the leading directive block carries exactly one impact directive, that directive is the explicit no-impact form, and it has a reason — both lines start at column one, and the reason is mandatory (`Assurance impact: none` alone does not satisfy; any second impact line also invalidates the declaration):

```text
Assurance impact: none
Reason: <visible plain-text explanation of why the mapped invariants are unaffected>
```

The `Reason:` payload and any `Assurance policy change:` explanation must contain visible plain text. Zero-width-only text, an entity that decodes only to invisible characters, or empty inline HTML is not an explanation and does not satisfy the gate.

An unsatisfied component produces a warning — surfaced as a GitHub annotation in the checks UI, with a routing table in the job summary — naming the component, the number of matched files, and the invariant IDs to address; the job still passes. To escalate the warnings into a failing check, pass the `strict-drift` input to the reusable workflow:

```yaml
    with:
      strict-drift: true
```

Without a `components` map the component routing reports that impact routing is not configured and passes.

**Policy regression check.** On the same pull-request run, the assurance policy is compared against the base branch — at two levels.

The *adoption declaration*: moving the declaration itself; an `adoption_stage` downgrade; removal of an effective active profile (including the implicit `core` inherited by every active specialized profile); a `layout` change; a removed component or removed path glob / invariant ID inside one; a change to an already committed `project.name`, `project.repository`, or `project.human_owner`; a changed `human_review.reviewer` or `human_review.record`; removal, invalidation, or backdating of a completed `human_review.date`; removal or rewriting of attributable approval provenance (`approver`, `review_url`, `at`, and normalized `covers` scope — omission is equivalent to `[CONFORMANCE]`); a changed `specification_workflow.system` or normalized `specification_workflow.root`; a changed `security.policy`, `security.restricted_record`, or `security.public_assurance_root`; or weakening one of the three protected `issue_integration` controls. Artifact mappings are compared after applying standard defaults and normalizing path spelling: absent and explicitly default standard paths are equivalent, but changing an effective standard path or a previously declared custom mapping is a finding. Under lite, moving the effective system description between the inline `system` field and a mapped/default system artifact is also a gated policy relocation even when `layout` and the dormant mapping spelling stay unchanged. Advancing `human_review.date` is the normal ungated re-review act. Changing from exclusive `archived` to an active profile set is a separate, neutrally worded **profile-mode reclassification gate**: it is required before active work, not itself a weakening, but it still needs the same stage-proportional explicit acknowledgment. A changed `upstream` pin is likewise flagged with neutral wording: an upgrade is not a weakening, but [PROFILE.md §16](../PROFILE.md) requires every pin move to be an explicit, dedicated change, so it demands that acknowledgment too.

The *registers themselves*, compared by stable ID (the substance the declaration merely frames). The governing principle: a human-reviewed assurance item cannot quietly disappear, whatever form the change takes — a deleted entry, a deleted register file, or a status that closes it out. Detected:

- **Any register:** a deleted entry; a whole register that was present on the base branch and is gone on the head — or unreadable, or structurally unusable (including a path that exists but is not a readable regular file), or carrying duplicate IDs on the head (each fails closed: a register that cannot be compared reliably must never pass silently). An optional register such as `defeaters` under the `core` profile could otherwise be deleted in full with no finding.
- **Every entry, all registers:** a changed `owner` (an accountability transfer); a recorded judgement value *unset* — removed, emptied, or replaced with a non-string value. That covers `status` everywhere plus `severity`, `proof_tier`, `impact`, and `uncertainty`: every weakening check below needs a meaningful value on both sides, so dropping one would otherwise be a free first hop (delete it in one pull request, record a weaker value in the next, both silent, while the one-step edit is a finding). The residual/defeater disposition gates additionally fire on *arriving* at a gated status whatever the base recorded. Also: items removed from the kind's relationship/basis lists — `evidence`/`invariants`/`limitations`/`defeaters`/`residuals` on claims, `assumptions`/`limitations`/`defeaters`/`residuals` on invariants (at *every* severity), `affected_claims`/`affected_invariants`/`evidence` on defeaters, `affected_claims`/`affected_invariants`/`mitigation` on residuals. Severing an assurance-graph edge (why a claim could be wrong, what a defeater affects, how a residual is mitigated) is a mechanism change, not a wording one.
- **Invariants:** severity downgraded; conclusion status weakened (`VERIFIED`/`INFERRED` toward `UNKNOWN`); any affirmative intent decision (`INTENDED`, `COMPATIBILITY`, or `DEPRECATED`) reclassified or unset, or its recorded authority rewritten; `enforcement`/`verification`/`evidence` items removed from a high/critical invariant.
- **Claims:** status weakened; `proof_tier` downgraded.
- **Invariants and claims:** a recorded `CONTRADICTED` status *cleared* (moving to `CONTRADICTED` is an honesty upgrade and is never flagged; moving away from it resolves a known problem and needs review).
- **Residuals:** impact or uncertainty downgraded (the two assessment axes of [PROFILE.md §12](../PROFILE.md)); the residual *closed* (status → `RESOLVED`); the residual *accepted* (status → `ACCEPTED` — accepting a risk is a human decision, and the acceptance fields are self-declared strings, so the transition itself routes through the gate); an existing acceptance record rewritten or removed (`accepted_by`/`accepted_at`/`acceptance_rationale`); or `resolution_note` rewritten while the residual remains `RESOLVED`.
- **Defeaters:** the defeater *closed* (status → `MITIGATED`/`RESOLVED`/`WITHDRAWN`); a `MITIGATED` defeater moved to a terminal disposition (`RESOLVED`/`WITHDRAWN` assert the risk is gone or was never real — a materially stronger statement than "reduced"); or `resolution` rewritten while the defeater remains in a closed disposition.
- **Defeaters and residuals:** `review_after` removed, replaced with an unparsable value, or pushed out *after the recorded date had already passed* — an overdue re-review is done, not deferred, and postponing it is how a live overdue warning would otherwise be cleared. Rescheduling a date still in the future is the normal outcome of actually doing the review and is not a finding; nor is moving it earlier or adding one. An unparsable value on the base branch still counts as a recorded commitment (dropping it, or swapping it for different garbage, is a finding; repairing it into a real date is not).

Re-opening a closed residual or defeater, and recording a new contradiction, are never findings. Wording is deliberately not compared in the narrative fields — claim `text`, invariant `statement`/`title`, residual `summary` — which remain the §4.3 human review's terrain. The protected lists above are the exception, and by design: their items are commitments recorded one by one, compared as string sets, so rewording an assumption, limitation, or mitigation reads as removing it. Re-adding the corrected item in the same change leaves both the removal finding and the acknowledgment on the record, which is the intended outcome for edits to a reviewed caveat. Legitimate versions of the gated changes (a real acceptance, a real owner handover, a review-cycle `review_after` bump) surface as findings *by design*: they are exactly the human decisions the gate exists to put on the record.

Each finding requires a visible, explicit line in the leading top-level directive block defined above (outside HTML comments and fenced code):

```text
Assurance policy change: <why this gated policy change is intended and who decided it>
```

When impact routing is also declared, place this line after `Assurance impact:` and its required `Reason:` when the impact is `none`, but before any heading or ordinary prose. Without an impact declaration, the policy-change line itself may begin the leading block. A matching line after ordinary visible content is ignored.

**The explicit acknowledgment is stage-proportional.** It is a self-declaration by whoever writes the PR description — including an agent — so its force is capped by what the *base* declaration had asserted: at `DRAFT`, it downgrades gated findings to visible warnings; from `HUMAN_REVIEWED` on, the same findings remain errors even when acknowledged. The acknowledgment therefore records intent but does not unblock a reviewed policy change; merging over the red check is the human owner's recorded decision. (The base branch's stage is the yardstick, not the head's — a downgrade PR would otherwise lower its own bar in the same change.)

This closes the self-downgrade loophole — a pull request that flips `adoption_stage: CONFORMANT` back to `DRAFT` would otherwise skip the `declared-stage` check silently, and a shrunken component map would evade routing with policy the base branch never agreed to drop. Apart from the explicit `archived` → active reclassification gate, additions (new components, added invariants, new registers, a stage raise) are never findings. The drift job explicitly checks out `github.event.pull_request.head.sha`; GitHub's default synthetic merge checkout is not used for HEAD-side policy reads, so the working tree, the explicit diff SHA, and the validator's `--project-root` describe one snapshot. Changed-file production uses three-dot merge-base semantics plus explicit rename and retained-source copy detection, reporting both source and destination. The reusable workflow reconstructs the prior declaration path from the base version of the actual caller named by `github.workflow_ref`, reading that caller's literal `with.adoption-file` value (or the default when omitted). It therefore does not mistake a pre-existing file at the new HEAD destination for the base policy, and a pin-only caller edit can keep using a tracked symlink alias without an ambiguous whole-tree scan. When exact recovery is impossible — for example, a newly added or renamed caller, an expression-valued input, or differing inputs across multiple reusable-workflow jobs — the workflow scans tracked regular files regardless of extension or YAML surface syntax and identifies a prior declaration by its canonical AAP pin/project/profile shape. That fallback streams Git's NUL-delimited listing and is fail-closed at 100,000 tracked records, 64 MiB of raw listing data, 64 MiB of lexical file surface, and 16 declaration candidates. Every tracked record counts before file-type, containment, or trusted-path filters; exceeding a budget or finding multiple matches is an error, and only a completed bounded scan with no match is treated as a new adoption. Moving a found declaration is itself a policy finding, not merely a notice, because the new location may sit outside existing review controls. Retargeting a symlink behind the same lexical declaration or policy-artifact path is likewise a finding. Base bindings remain containment-, trust-, and target-identity checked for policy comparison. Positive CI evidence is limited to the HEAD-active strict-text set described above; its merge-base-wide cancellation set can only remove candidates, never authorize base-only content. All evidence Git operations, including `cat-file` blob reads, share one 60-second deadline. Merge-base and HEAD enumeration together share a 64 MiB aggregate listing budget, a 1 MiB diagnostic budget, and a 100,000 tracked-tree-record bound; pathspecs are deduplicated, ancestor-collapsed, and batched. Explicit inactive-lite mappings remain containment- and retarget-checked but cannot supply routing evidence. Coordinate the workflow input, both root reading-order copies, resolved targets, and CODEOWNERS as described in §3.2–§3.5.

The map itself is validated in the ordinary adopter run (§3.6): each component requires non-empty `paths` and `invariants`, and every listed invariant ID must exist in the invariant register — split or lite layout alike — so a dangling component reference is a validation error, not a silently dead route.

The drift check is a plain validator subcommand, runnable locally against the pinned checkout:

```bash
git diff --name-only BASE_SHA...HEAD_SHA > changed-files.txt
git diff BASE_SHA...HEAD_SHA -- assurance .agentic-assurance > assurance-diff.txt
git show BASE_SHA:.agentic-assurance/adoption.yaml > base-adoption.yaml
python -I .assurance-profile-pin/scripts/validate.py drift \
  --adoption .agentic-assurance/adoption.yaml \
  --changed-files changed-files.txt \
  --pr-body pr-body.txt \
  --assurance-diff assurance-diff.txt \
  --base-adoption base-adoption.yaml
```

`--changed-files` accepts newline-separated repository-relative paths for ordinary standalone use, or auto-detects a NUL-separated file for lossless path boundaries; CI uses NUL end to end so embedded newlines and leading/trailing spaces cannot evade a component glob. `--pr-body` takes the pull-request description as a file, where a missing or empty file means an empty description; as in CI, directives and ID mentions inside HTML comments or fenced code do not count. `--assurance-diff` and `--base-adoption` are optional: without the former, any assurance change satisfies every touched component (the coarse standalone fallback — CI always passes the diff); without the latter, the policy regression check is skipped. For a supplied ordinary unified diff, the standalone parser excludes added symlink/gitlink payloads and conservatively cancels exact deleted lines against identical additions; it still cannot reconstruct CI's contained targets and repository-wide merge-base cancellation. The simple `assurance/` diff command above therefore remains only a quick local approximation. The reusable workflow's BASE materializer can normalize the bounded historical pre-v0.4 SafeLoader surface (including merge and scalar non-string keys) before invoking the strict validator; a direct standalone `--base-adoption` accepts only the narrower duplicate-key last-wins migration case and otherwise fails closed. For an exact local check of such an older base, first materialize an equivalent strict JSON copy without changing its historical data. To reproduce declaration-path gating, also pass `--adoption-path-transition` with strict JSON containing both lexical and resolved paths, such as `{"base":".agentic-assurance/adoption.yaml","head":"config/adoption.yaml","base_resolved":"policy/adoption-v1.yaml","head_resolved":"config/adoption.yaml"}`. To reproduce resolved-target binding and the register-level diff, additionally materialize the base branch's policy tree — `git worktree add --detach /tmp/base-tree <base-sha>`, which is what CI does (a worktree, unlike per-file `git show`, keeps symlinked artifacts readable) — and pass `--base-registers-root /tmp/base-tree --project-root .`. Those two root flags are an inseparable pair, require `--base-adoption`, and must resolve to existing distinct directory trees with no ancestor/descendant overlap; missing, aliased, or overlapping snapshots fail closed. Add `--strict` to reproduce the escalated mode and `--json` for machine-readable output. (`--name-only` remains acceptable for a quick local run; CI additionally performs explicit rename/retained-copy detection and generates the stricter synthetic evidence diff described above.)

On noise: start with two to four components covering the paths of your critical invariants, and expand the map only as it proves quiet — a map that warns on every routine pull request teaches reviewers to ignore the warnings.

### 3.8 Adoption stages: DRAFT, HUMAN_REVIEWED, CONFORMANT

The optional `adoption_stage` field in `adoption.yaml` declares how far the adoption has progressed. Nobody awards a stage — the declaration is self-made and self-binding: the validator enforces exactly the stage you declare, turning its requirements into errors. Declare high, meet it, or the build is red. An absent field means `DRAFT`, and a `DRAFT` (or absent) declaration changes nothing: validation behaves exactly as in §3.6.

Each stage includes every requirement of the stages below it:

| Stage | Adds on top of the previous stage | Who advances it |
|---|---|---|
| `DRAFT` | The ordinary validation of §3.6: baseline schema, required artifacts, and all applicable stage-independent semantic checks. Unfilled placeholders and `UNKNOWN` are allowed in the local assurance registers where their schemas permit them. The adoption declaration itself (upstream pin, project identity, paths) must be complete at every stage, and an exclusive `archived` adoption's mapped system artifact must already exist and be non-empty. Semantic rules still apply while drafting: for example, an active severity-`critical` invariant recorded `VERIFIED` needs at least one enforcement and one verification reference, while the stricter `service` rule requires both references on every critical invariant regardless of conclusion; `INTENDED`, `COMPATIBILITY`, and `DEPRECATED` intent dispositions need a non-blank human authority; every `ACCEPTED` residual needs its human acceptor, non-future date, and rationale; resolved residuals and closed defeaters need their resolution grounds; and critical acceptance belongs to the human owner. A machine-detectable placeholder supplies none of those disposition grounds, including in a historical register retained under `archived`; archived skips the active-register completion rules, not the truth conditions of any completed act it keeps. | Nobody needs to; it is the default. |
| `HUMAN_REVIEWED` | No unfilled `REPLACE_WITH_` placeholder in the adoption declaration. For an active adoption, none may remain in any loaded register (split sections or the lite file alike), nor may any path-scoped pre-v0.4 compatibility placeholder remain: the legacy `YYYY-MM-DD` sentinel at a residual/defeater `review_after` path or any of the seven exact `Replace with ...` starter prompts in their original claim, invariant, defeater, and residual fields. An active system description may contain no generic `REPLACE_WITH_` marker. A required service threat model must be non-empty and contain no generic marker. For exclusive `archived`, retained historical active registers do not reintroduce that active completion rule; instead, the all-stage non-empty rule remains in force and none of the four exact `REPLACE_WITH_ARCHIVED_...` markers shipped in `templates/SYSTEM.md` may remain. A `human_review` block must have non-empty `date`, `reviewer`, and `record` pointing to an existing non-empty project review artifact; `date` must be a non-future ISO date. Every active severity-`critical` invariant must record an intent classification, with `UNKNOWN` allowed as an honest reviewed result. | The human owner, after completing the applicable active or archived branch of §4.3. |
| `CONFORMANT` | At least one attributable entry in `human_review.approvals` must attest the full claim (`covers` omitted, or containing `CONFORMANCE`) and have a non-future approval date whose civil date is the same as or later than `human_review.date`. For an active adoption, passed `review_after` dates are errors (as with `--strict-review-dates`); every severity-`critical` invariant has an intent classification other than `UNKNOWN` or `ACCIDENTAL` (`DEPRECATED` is a decided intent, not permission to delete it without change control); and the mechanically checkable active subset of [PROFILE.md §17](../PROFILE.md) applies: no residual with `impact: critical` left `OPEN` (carry it only as `ACCEPTED` with explicit human acceptance, or record a grounded `RESOLVED` disposition; the separate `uncertainty` axis does not trigger this gate), no `CONTRADICTED` claim, no `CONTRADICTED` critical invariant, and every `VERIFIED` critical invariant carries non-empty `evidence`. Accepting a residual that records a critical-invariant violation does not make the false invariant conforming. Under exclusive `archived`, retained historical active registers do not reintroduce those replaced active-system checks. For every profile, no register entry may be classified `RESTRICTED` or `EMBARGOED` in a public repository (the reusable workflow passes the repository's actual visibility; standalone runs declare it with `--repo-visibility`, and an undeclared visibility is treated as public, conservatively). In a private repository RESTRICTED entries stay the standing warning — §17 excludes restricted material from *public* artifacts, and §3.6's visibility binding already governs the private case. | The human owner, when standing behind the conformance statement of [PROFILE.md §17](../PROFILE.md). |

Honest boundary: a `CONFORMANT` declaration is the adopter's full claim that **all** applicable selected-profile obligations in PROFILE.md §6 and all §17 conditions are met. The human approval attests that full claim. The validator enforces only the listed structural and mechanically decidable subset; green `declared-stage` is a prerequisite, not machine proof of conformance. Human review must still establish, among other things, the truth and completeness of system prose; revision/deployment binding and claim-to-evidence sufficiency; the substance of service enforcement, verification, and release evidence; trust-critical limitations, audit/remediation separation, secret handling, and private-reporting practice; and the profile-specific semantics of data-curation and agent-runtime controls. For `archived`, the non-empty and marker guards do not establish reference-only eligibility or the truth of the four historical facts. A green check behind a human-approved `CONFORMANT` declaration therefore supports the adopter's normative claim; it does not replace the human attestation.

Advancing the stage is an owner act, recorded like a §4.3 outcome: the change that raises `adoption_stage` should carry, or point at, the review record that justifies it. An agent may propose the raise; it may not perform it on its own authority.

**Attributable approval.** From `CONFORMANT`, the `human_review` block must carry an `approvals` list with at least one entry naming who approved, where the approval can be inspected, and when:

```yaml
human_review:
  date: 2026-07-01
  reviewer: alice
  record: assurance/reviews/2026-07-01-adoption.md
  approvals:
    - approver: alice
      review_url: https://github.com/OWNER/REPO/pull/42#pullrequestreview-123456789
      at: 2026-07-01
      covers: [ CONFORMANCE, INV-AUTH-001, RES-002 ]   # optional; CONFORMANCE makes an explicit list attest the full claim
      rule: codeowners-default-branch     # optional: the local review rule it satisfies
```

`approver`, `review_url`, and `at` must all be non-empty; `review_url` uses a deliberately narrow ASCII HTTP(S) URL grammar: a DNS/IPv4-style hostname or bracketed hexadecimal IPv6 literal, no user information, an optional numeric port in range, and valid RFC 3986 path/query/fragment characters and percent escapes. Percent-encoded path/query/fragment octets must decode as UTF-8; write an internationalized hostname as an ASCII IDNA A-label (punycode) accepted by the narrow hostname grammar. This is narrower than the complete RFC 3986 `reg-name`/IP-literal surface. `at` must be an ISO date or RFC 3339 timestamp; second `60` is accepted only at an actual historical positive leap second, including an offset-equivalent spelling of that instant. Review and approval dates record acts that have already occurred, so `human_review.date` and every approval `at` must not be future-dated; at least one attributable approval's written civil date must be the same as or later than `human_review.date`. A date-only value has no time-zone offset, so validation permits the current civil date anywhere on Earth (up to UTC+14); a timestamp is compared at its stated offset. Residual `accepted_at` is governed by the same completed-act rule. Review schedules use the same host-independent boundary: `review_after` is compared with the latest civil date currently possible in UTC+14, so its result does not depend on the runner's local time zone. `covers` and `rule` are optional. Omitting `covers` means the approval attests the full conformance claim. If `covers` is present, include the reserved `CONFORMANCE` token for that approval to count toward the `CONFORMANT` gate; a list of only invariant or residual IDs is intentionally scoped too narrowly. One honest limitation, stated plainly: the workflow does not verify the URL through the GitHub API — it does not check that the URL is a real approved review, or that the approver is not the author. Treat the entry as a claim reviewable by humans, exactly like the rest of the register; future tooling may verify the approved state and author ≠ approver mechanically.

**The CI check split.** The reusable workflow (§3.4) reports two checks so a stage cannot be misread:

- `assurance / structure` always runs: the ordinary adopter validation of §3.6 with stage requirements skipped (the validator's `--ignore-stage` flag) — a `DRAFT`-equivalent pass/fail.
- `assurance / declared-stage` runs the full stage-enforcing validation, and is skipped entirely while the declared stage is `DRAFT` or absent.

Check renames across releases (update branch protection when re-pinning): `assurance / validate` (pre-v0.2.0) became `assurance / structure`; `assurance / conformance` (v0.2.0) became `assurance / declared-stage` in v0.2.1. The second rename is deliberate: the check is green whenever the *declared* stage's requirements are met — at `HUMAN_REVIEWED` as well as `CONFORMANT` — so a check named "conformance" would show green on repositories that assert no conformance at all. The split and the name exist so a green check cannot be misread: green `structure` means the DRAFT-equivalent schema, artifact, and semantic baseline is valid; green `declared-stage` means the declared stage's mechanical gates are met; only a human-approved `CONFORMANT` declaration asserts the full normative claim.

Locally, the §3.6 command enforces the declared stage by default. A successful `HUMAN_REVIEWED` or `CONFORMANT` run reports `stage <X>: requirements satisfied`; `DRAFT` intentionally emits no stage-specific summary line, while its ordinary validation results still run. Add `--ignore-stage` to reproduce the `structure` check.

## 4. Brownfield adoption

Most adoption is brownfield. Initial adoption of an existing repository must begin as a read-only archaeology task before broad remediation ([PROFILE.md §7](../PROFILE.md)). Classify the profile first (§4.0) — a cheap pass that decides how deep everything after it must go. An active adoption then follows §4.1–§4.4 without compressing archaeology, review, and remediation into one change. An `archived` adoption follows the narrower branches in §4.1 and §4.3: it establishes reference-only eligibility and the four §6.6 facts, skips the active-system §4.2 and §4.4 work, and must be reclassified before any functional remediation or renewed operation, functional maintenance, or feature development.

### 4.0 Classify the profile first

The profile set is a *finding*, not a default. Before drafting any artifact, determine which of the [PROFILE.md §5](../PROFILE.md) profiles apply from what the repository **is and promises** — not from its size, and not by starting at `core` in the hope of escalating later. This classification sizes everything downstream: it decides the layout (§3.0 vs §3.1), which registers exist, and how deep the §4.1 reconstruction must go. Run it as a cheap first pass — surface signals are usually enough, and you do not need the full archaeology to classify.

For each escalation trigger, ask the disqualifying question and, when it fires, cite the `file:line` that fired it:

| Trigger | Fires when — surface signals | Adds |
|---|---|---|
| **service** | the repository is deployed or operated: a server framework, a `Dockerfile`, a deploy workflow, a live URL, a stateful backend | `service` |
| **trust-critical** | it makes a security, privacy, identity, authorization, financial, governance, or public-verifiability claim: auth/session/JWT, wallet or SSO login, admin/role gating, voting/proposals/tallies, payment or token transfer, PII handling | `trust-critical` |
| **data-curation** | it derives externally-sourced, editorial, scored, classified, or recommended data: embedding search or ranking, scoring, aggregated external feeds | `data-curation` |
| **agent-runtime** | a model or agent **runs in this repository's production path** — an LLM SDK invoked in a request or worker, not merely a call to a backend that does | `agent-runtime` |

`core` is the obligation baseline for every active adopter, but specialized profiles inherit it implicitly: for an active adopter, when no specialized trigger fires, declare `[core]`; when any fire, the canonical smallest declaration lists all fired specialized profiles and omits `core`. Writing `core` alongside them is allowed but changes no obligation. `archived` is different: it is declared alone and replaces every active profile only when the repository is retained solely for historical reference, is not supported or intended for current use, and has no active operation, functional maintenance, or feature development ([PROFILE.md §5](../PROFILE.md), [§6.6](../PROFILE.md)). The result is the **smallest set that covers every trigger that fires** — that is what "smallest applicable set" means, not "the fewest profiles you can get away with."

**Bias toward escalation.** When a trigger's evidence is genuine but ambiguous in degree, fire it. Under-classification is the expensive mistake: a repository declared `core` gets only the `core` checks, so the claims, proof tiers, and defeaters a trust-critical repository needs are never required — and the run still passes green. Over-classification only costs some unused artifacts, which the owner can drop; under-classification silently turns off enforcement. The owner can de-escalate a conservatively-fired trigger in the §4.3 review with a recorded reason — there is not yet a matching mechanical mechanism to catch a trigger that was never fired; that backstop is tracked in [#41](https://github.com/MosslandOpenDevs/agentic-assurance-profile/issues/41).

**Attack the classification before you commit it.** Re-open the cited evidence and challenge it from both sides: for each fired trigger, try to prove it should *not* fire — is the code load-bearing, or a stub, example, vendored copy, or test-only path? And hunt for triggers you missed — grep the actual code for the signals above, not just the directory names. (In a pilot classification the cited trust-critical evidence turned out to be a deprecated, frozen module; the adversarial pass found the live trust-critical behavior implemented on a different path — the verdict held, the evidence was corrected.)

**Layout follows the profile, never the size.** `layout: lite` (§3.0) is valid only when the classification is `core` alone; any fired trigger means the split layout of §3.1. A large, sprawling repository with no external promises can be `core`; a two-hundred-line library that verifies auth tokens is `trust-critical`. Size is not a trigger.

Declare the proposed profile set and layout in `adoption.yaml` itself — the enforced `profiles:` field, not only the handoff prose — and list them in the §4.3 handoff, each fired trigger with its evidence, for the owner to confirm or de-escalate. Leaving `profiles: [core]` in the file while noting specialized triggers only in prose is the common miss: the handoff is read once, but the `profiles:` field is what selects the checks. The selection stays provisional until the owner's review (§1).

**Worked example.** A loan-underwriting backend that authenticates applicants, gates approval actions by reviewer role, scores each application against externally-sourced credit data, and drafts decision rationales with a production LLM is not `core`-only. It fires `service` (deployed API), `trust-critical` (identity + authorization + financial), `data-curation` (scored external data), and `agent-runtime` (a model runs in its request path): the canonical declaration is `[service, trust-critical, data-curation, agent-runtime]`, split layout; §6.1 `core` obligations are inherited without listing `core`. Declaring it `[core]` (lite) would hide every claim, proof tier, and defeater it most needs — and pass green. Its separately classified frontend repository, which deploys the client and only calls the backend for the resulting score and LLM-drafted rationale, canonically declares `[service, trust-critical]`, not `data-curation` or `agent-runtime`: neither the external-data derivation nor the model execution occurs in the frontend repository. Classification follows each repository's own operational, claim, data-processing, and execution boundary, not the product boundary as a whole.

### 4.1 Read-only reconstruction

For an `archived` classification, replace the active-system reconstruction below with a narrower read-only assessment: cite evidence that the repository is retained solely for historical reference, is not supported or intended for current use, and has no active operation, functional maintenance, or feature development; reconstruct the historical purpose, known material limitations, and last supported revision or release (or explicitly that none exists); and record all four facts in the system artifact resolved from `paths.system`. Extra historical context is allowed, but do not invent empty active claims, invariants, defeaters, or residuals. After drafting those artifacts, skip §4.2 and use the archived owner-review branch in §4.3; §4.4 applies only if the repository is reclassified for renewed active work.

For a non-`archived` classification, before changing any functional code, reconstruct the as-built system:

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
- For an active adoption, record the reconstruction in the system description; [templates/SYSTEM.md](../templates/SYSTEM.md) mirrors this list section by section. For `archived`, complete its §0 prompts instead.
- Evidence discipline applies from the first line: each non-`UNKNOWN` material conclusion cites concrete evidence — file and line, database constraint, test name, command output, endpoint response, artifact digest, deployment record, or runtime metric. An AI-generated explanation is not evidence by itself.
- Check the provenance of prose evidence. In an agent-built repository most comments, READMEs, and notes are themselves agent-authored: before citing one as intent authority, `git blame` the lines and inspect the introducing commit's authorship (for example `Co-Authored-By:` trailers, bot committer identities, agent-session branch names). Agent-authored prose may be cited as a *description* of behavior, never as *human intent* — that classification stays `UNKNOWN` until the owner confirms it in the §4.3 review. The check only sorts prose into two bins — *disqualified* (an agent marker is present) and *provenance-uncertain* (no marker, which proves nothing: many agents leave none, and humans commit agent-written text under their own names). It never yields "definitely human"; provenance-uncertain prose is presented to the owner as a candidate, and the owner's §4.3 answer is what settles it. The line that matters is the human act, not the typist: an agent-drafted record of an explicit owner decision, anchored by the owner's reviewed merge, is valid authority (second-pilot lesson — an agent cited an agent-written comment as intent and caught its own circular reasoning). Machine-verifiable evidence (schema constraints, live response headers, command output, code behavior) is unaffected.
- For an active adoption, keep the invariant register small: roughly 5–15 invariants per repository — the things that must never break, not the full specification. The real cost of an invariant is not writing it but re-examining it on every change that touches its scope; an exhaustive register stops being read and starts to rot. If the archaeology surfaces thirty candidates, that is a ranking exercise for the §4.3 review, not thirty register entries.

### 4.2 Behavior classification

For a non-`archived` adoption, this is distinct from the profile classification of §4.0: that decides *which profiles apply*; this classifies *observed behavior*. Classify observed behavior as `INTENDED`, `ACCIDENTAL`, `COMPATIBILITY`, `UNKNOWN`, or `DEPRECATED`, and each conclusion about the system as `VERIFIED`, `INFERRED`, `UNKNOWN`, or `CONTRADICTED` ([PROFILE.md §4](../PROFILE.md)). `UNKNOWN` is a first-class result: recording uncertainty is correct; inventing confidence is prohibited. Current production behavior is evidence of current behavior, not automatic proof of intended behavior. An `archived` adoption does not perform this separate active-system step solely to create registers; its §4.1 conclusions still use honest evidence classifications where recorded.

### 4.3 Human intent review

For a non-`archived` adoption, before broad remediation the human owner reviews:

- purpose and non-goals;
- critical claims and invariants;
- the behavior classification from §4.2;
- critical residuals and public claim limitations.

The profile set is part of that decision, not a menu the owner may only trim. The owner confirms supported triggers, removes unsupported ones, **and adds any applicable trigger the proposal missed**; the recorded set must still cover every trigger that fires.

For an `archived` adoption, the owner instead confirms that the repository is retained solely for historical reference, is not supported or intended for current use, and has no active operation, functional maintenance, or feature development; that `archived` is declared alone; that the mapped system artifact is the intended record; and that each of its four §6.6 facts is accurate. These confirmations replace the active-system decisions above; [REVIEW-GUIDE.md](REVIEW-GUIDE.md) provides the checklist.

An agent may draft all of this; it may approve none of it.

The adoption draft should arrive as an open pull request and stay unmerged until this review completes; merging the pull request is then the natural durable record that the owner reviewed and accepted the draft as the §4.3 baseline. If the draft was merged early, nothing is lost — corrections and the review record land as follow-up pull requests, as the first pilot did — but branch-until-reviewed is the intended flow. [REVIEW-GUIDE.md](REVIEW-GUIDE.md) is the owner-side companion for making these decisions, walking through each of them in plain language.

### 4.4 Staged remediation

For a non-`archived` adoption, after the intent review:

- record conformance gaps and residuals in the durable artifacts first;
- remediate through separate, scoped issues and pull requests — the `conformance-gap` and `evidence-gap` forms from the adopter bundle (§3.5) exist for exactly this;
- bind new evidence to a commit, artifact digest, release, or deployment identifier;
- map existing conventions instead of duplicating them ([MAPPINGS.md](MAPPINGS.md));
- for critical security, privacy, authorization, financial, governance, or data-integrity work, keep audit and remediation in separate contexts ([PROFILE.md §10](../PROFILE.md)).

An `archived` adoption has no active remediation stage. Correct gaps in the reference-only classification or four historical facts before acceptance. Initial adoption, factual corrections, and upkeep of the pin, stage, review record, or agent-instruction metadata are archival-assurance metadata work, not functional maintenance. If functional remediation, operation, functional maintenance, or feature development resumes, reclassify the repository under the applicable active profiles first.

## 5. Pilot guidance

For the initial pilot adoptions of this profile (Passport-class projects):

- classify the profile honestly up front (§4.0) — do not assume `core`; the smallest set is the one that covers every trigger the repository fires;
- run the full §4 brownfield sequence to gather the evidence behind that classification before drafting artifacts;
- `service` is warranted once the evidence confirms the repository operates a deployed service, and `trust-critical` once it establishes which security, identity, governance, or public-verifiability claims the project actually makes — claims drive obligations, not the other way around, and a fired trigger is not deferred to "later";
- treat `agent-runtime` as a provisional profile: before `v1.0.0`, its obligations may change in a minor release, and the validator warns on its selection; the provisional label does not override stable-version SemVer rules at or after `v1.0.0`. (`data-curation` was promoted from provisional in v0.2.0 after the second pilot exercised it.)

## 6. What adoption is not

Creating the files is not adopting the profile. A repository containing `AGENTIC_ASSURANCE.md`, an adoption file, and freshly copied templates has declared an intention — nothing more. Per [templates/AGENTIC_ASSURANCE.md §12](../templates/AGENTIC_ASSURANCE.md), an active adoption is complete only when:

- the upstream pin resolves to a real version and commit per §2;
- human-approved purpose and non-goals are recorded;
- critical claims and invariants are stated, with enforcement and evidence references or an explicit `UNKNOWN`;
- the residual register is active and owned;
- the material-change workflow references the assurance artifacts in normal review.

The exclusive `archived` path substitutes its narrower §6.6 contract for those active-system bullets: adoption is complete only when the owner confirms the full reference-only eligibility and all four facts in the system artifact resolved from `paths.system`. The validator requires that artifact to exist and be non-empty, and at `HUMAN_REVIEWED` or `CONFORMANT` rejects any of the four exact `REPLACE_WITH_ARCHIVED_...` markers shipped in `templates/SYSTEM.md`. Those guards detect an empty or untouched template, but they do not determine whether replacement prose contains all four facts or is truthful; until structured content enforcement lands in [#40](https://github.com/MosslandOpenDevs/agentic-assurance-profile/issues/40), use the checklist in [REVIEW-GUIDE.md](REVIEW-GUIDE.md).

A green validator run checks structure, presence, and pin consistency — not the truth of the claims. Conformance is bounded: for an active project, it means the project's promises, controls, evidence, and remaining doubt are represented according to the pinned profile; for `archived`, it means the bounded reference-only classification and required historical facts are owner-confirmed, not that current operational assurance exists. Neither means the project is secure or bug-free ([PROFILE.md §17](../PROFILE.md)).

## Related documents

- [PROFILE.md](../PROFILE.md) — the normative profile text
- [MAPPINGS.md](MAPPINGS.md) — reusing existing conventions via `paths:`
- [DISCLOSURE-AND-ISSUES.md](DISCLOSURE-AND-ISSUES.md) — issue routing and disclosure rules
- [GLOSSARY.md](GLOSSARY.md) — plain-language definitions of the profile's terminology
- [REVIEW-GUIDE.md](REVIEW-GUIDE.md) — the human owner's guide to reviewing an adoption draft
- [templates/AGENTIC_ASSURANCE.md](../templates/AGENTIC_ASSURANCE.md) — the adopter-side entry document
- [templates/adoption.yaml](../templates/adoption.yaml) — the adoption file template
- [RELEASING.md](../RELEASING.md) — release ritual and the `VERSION` file lifecycle
- [SECURITY.md](../SECURITY.md) — vulnerability reporting for this repository
