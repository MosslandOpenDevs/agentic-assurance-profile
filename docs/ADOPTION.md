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
2. Perform the read-only archaeology (§4.1) and behavior
   classification (§4.2) without changing any functional code.
3. Copy the templates and draft the artifacts for the classified
   profile(s) and layout (§3).
4. Finish with a written proposal listing everything that requires
   human review under §4.3 — starting with the profile set and
   layout. Do not declare adoption complete; approval decisions
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

1. **A named human owner or governing body exists.** The profile requires a human authority over purpose, critical claims and invariants, public claim wording, control weakening, and residual acceptance ([PROFILE.md §3](../PROFILE.md)). Adoption cannot proceed without one.
2. **Profiles are chosen by classification, not by default.** Determine the profile set from what the repository is and promises, per §4.0 — the smallest set that *covers every trigger that fires*, which is not the same as starting at `core` and escalating later. An agent may propose the set, with `file:line` evidence for each fired trigger; the selection remains provisional until the human owner reviews it (§4.3).
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
- **The tag commit is the canonical release pin.** More than one commit can carry a release identifier in its `VERSION` file — the release pull request's branch commit and the merge commit the tag points to are distinct SHAs with identical content. Pin the commit the tag points to: `git rev-list -n1 vX.Y.Z`, or the commit shown on the [release page](https://github.com/MosslandOpenDevs/agentic-assurance-profile/releases). The CI workflow fails a release pin whose commit is not the tag commit (first-trial lesson).
- **The full commit SHA is the normative pin.** A floating branch such as `main` must not be the sole reference, and tags — although immutable once published — do not replace the 40-character SHA in the adoption file.
- **Upgrades are explicit.** Moving the pin is a material change with its own review. An agent must not silently update the pin ([PROFILE.md §15](../PROFILE.md)).

### 2.1 Before the first tagged release

Until the profile publishes its first tagged release, pin `version: unreleased` together with the full 40-character SHA of a commit whose `VERSION` file reads `unreleased`. When a release such as `v0.1.0` is published, upgrading to it is an ordinary explicit pin upgrade: update `upstream.version`, `upstream.commit`, and the CI workflow reference (§3.4) in one reviewed change.

## 3. Greenfield adoption

The step-by-step sequence for a repository adopting from the start — or for an existing repository after the archaeology of §4 has been reviewed.

### 3.0 Lite adoption — for a confirmed core-only repository

Use the lite layout only after the §4.0 classification confirms the repository is `core` (or `archived`) alone — no `service`, `trust-critical`, `data-curation`, or `agent-runtime` trigger fires. Lite is the residual layout for a genuinely core-only repository, not a default to start from and escalate away from later.

A repository adopting `core` only does not need the full split layout that the rest of this section describes. The lite layout collapses the assurance registers into a single file and brings first adoption down to four files: an `AGENTS.md` carrying the assurance reading-order section (§3.3), `AGENTIC_ASSURANCE.md` at the root, `.agentic-assurance/adoption.yaml` (§3.2) declaring `layout: lite`, and `.agentic-assurance/assurance.yaml` holding all assurance content. Copy from the same CC0-1.0 template set:

| Copy from | To (adopting repository) |
|---|---|
| [templates/AGENTIC_ASSURANCE.md](../templates/AGENTIC_ASSURANCE.md) | `AGENTIC_ASSURANCE.md` |
| [templates/AGENTS.md](../templates/AGENTS.md) | `AGENTS.md` (merge if one exists; see §3.3) |
| [templates/adoption.yaml](../templates/adoption.yaml) | `.agentic-assurance/adoption.yaml`, adding `layout: lite` |
| [templates/assurance.yaml](../templates/assurance.yaml) | `.agentic-assurance/assurance.yaml` |

`assurance.yaml` starts with `version: 1` and carries the `core` obligations of [PROFILE.md §6.1](../PROFILE.md) as sections:

- `purpose` (string, required) and `non_goals` (list of strings, required) — §6.1 requires human-approved purpose and non-goals;
- `system` (string, optional) — a short as-built description satisfying §6.1's "current system description or mapping to an existing equivalent". When omitted, keep a separate system description at the `paths.system` location instead (`assurance/SYSTEM.md` by default); one of the two must exist;
- `invariants` (optional; recommended at `core` — it anchors the regression protection), `residuals` (required), and `defeaters` (optional) — arrays whose entries have exactly the same shape as in the split register files. The item schemas are not forked: the validator checks each present section against the corresponding register schema and runs the same semantic checks over the combined result, so lite and split registers are interchangeable content.

**Lite is core-only.** Declaring `layout: lite` together with any profile beyond `core` or `archived` — `service`, `trust-critical`, `data-curation`, or `agent-runtime` — is a validation error. The graduation path preserves every ID: move the section arrays into `assurance/INVARIANTS.yaml`, `assurance/RESIDUALS.yaml`, and `assurance/DEFEATERS.yaml`, move the `system` text into `assurance/SYSTEM.md`, and drop `layout: lite`. The validator enforces the split layout from `service` upward.

At `core`, the [templates/github/](../templates/github/) issue-template bundle (§3.5) and `CODEOWNERS` are optional rather than part of the minimum: copy the bundle when the repository takes external contributions — recommended in that case, and copy it whole, since the shadowing warning of §3.5 applies — and `CODEOWNERS` remains recommended wherever a second maintainer exists to review.

§3.1–§3.5 describe the split layout, used from `service` upward or at `core` by preference. Local validation for both layouts is §3.6.

### 3.1 Copy the templates

This and the following subsections describe the split layout — one register per file — used from `service` upward, or at `core` by preference (§3.0 covers the lite alternative). Everything under [../templates/](../templates/) is published under CC0-1.0: copy it into your repository freely, with no attribution obligation.

| Copy from | To (adopting repository) |
|---|---|
| [templates/AGENTIC_ASSURANCE.md](../templates/AGENTIC_ASSURANCE.md) | `AGENTIC_ASSURANCE.md` |
| [templates/AGENTS.md](../templates/AGENTS.md) | `AGENTS.md` (merge if one exists; see §3.3) |
| [templates/adoption.yaml](../templates/adoption.yaml) | `.agentic-assurance/adoption.yaml` |
| [templates/SYSTEM.md](../templates/SYSTEM.md) | `assurance/SYSTEM.md` |
| [templates/INVARIANTS.yaml](../templates/INVARIANTS.yaml) | `assurance/INVARIANTS.yaml` (recommended at `core`; required from `service`) |
| [templates/RESIDUALS.yaml](../templates/RESIDUALS.yaml) | `assurance/RESIDUALS.yaml` |
| [templates/CLAIMS.yaml](../templates/CLAIMS.yaml) | `assurance/CLAIMS.yaml` (when applicable) |
| [templates/DEFEATERS.yaml](../templates/DEFEATERS.yaml) | `assurance/DEFEATERS.yaml` (when applicable) |
| [templates/THREAT_MODEL.md](../templates/THREAT_MODEL.md) | `assurance/THREAT_MODEL.md` (when applicable) |
| [templates/github/](../templates/github/) | `.github/` — copy the whole bundle; see §3.5 |

The split-layout minimum matches [templates/AGENTIC_ASSURANCE.md §4](../templates/AGENTIC_ASSURANCE.md) and PROFILE.md §6.1: `AGENTS.md`, `AGENTIC_ASSURANCE.md`, `.agentic-assurance/adoption.yaml`, `assurance/SYSTEM.md`, and `assurance/RESIDUALS.yaml`. `assurance/INVARIANTS.yaml` is recommended at `core` — it anchors the regression protection, and both pilots kept one — but becomes required only from the `service` profile. Optional additions: `assurance/CLAIMS.yaml`, `assurance/DEFEATERS.yaml`, `assurance/THREAT_MODEL.md`, `assurance/decisions/`, `assurance/reviews/`, and `assurance/evidence/`.

These files must live in the adopting repository itself, never only in an organization-level `.github` repository: `AGENTS.md`, `AGENTIC_ASSURANCE.md`, `.agentic-assurance/adoption.yaml`, and everything under `assurance/` (including `DEFEATERS.yaml` when used). Organization defaults may host issue templates and a fallback `SECURITY.md`, but the assurance artifacts are project truth and belong in the project.

### 3.2 Fill in `adoption.yaml`

Replace every `REPLACE_WITH_` token — the validator treats a leftover token in an adopter file as an error. Declare:

- the `upstream` pin per §2;
- `project` name, repository slug, and `human_owner`;
- the `profiles` list (from the §4.0 classification — the smallest set covering every fired trigger);
- `layout: lite` when using the single-file layout of §3.0 (the field is optional; absent means the split layout);
- the `specification_workflow` you identified in §1;
- `paths` mappings when reusing existing conventions ([MAPPINGS.md](MAPPINGS.md)); the defaults are fine for a fresh layout.

### 3.3 Integrate `AGENTS.md`

If the repository has no `AGENTS.md`, start from [templates/AGENTS.md](../templates/AGENTS.md). If one exists, add the "OpenDevs Agentic Assurance" reading-order section defined in [templates/AGENTIC_ASSURANCE.md §11](../templates/AGENTIC_ASSURANCE.md) near the beginning of the existing file. Nested `AGENTS.md` files may impose stricter local rules but must not weaken the adoption.

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

The explicit `pull_request` types matter: the drift check (§3.7) reads invariant mentions and no-impact statements from the pull-request description, and the default types do not include `edited` — without it, editing the description after the fact would leave a stale verdict standing.

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

**Bind the assurance layer to the owner.** The bundle includes a [CODEOWNERS](../templates/github/CODEOWNERS) template covering `AGENTS.md`, `AGENTIC_ASSURANCE.md`, `.agentic-assurance/`, `assurance/`, and the CI caller workflow. Copy it to `.github/CODEOWNERS` (merge into an existing file), replace the placeholder with the owner's `@handle` or `@org/team`, and enable branch protection with required reviews and "Require review from Code Owners" on the default branch. This is what stops an agent from silently weakening an invariant, closing a residual, or moving the upstream pin — the most common failure mode of assurance adoption is exactly documents landing while this binding lags, which leaves unverifiable claims in public. Honest caveat for single-maintainer repositories: GitHub does not allow self-approval, so the binding becomes fully effective only once a second maintainer exists; until then the review record is the effective control, and the CODEOWNERS file is a declared intention (the same stance this profile's own [GOVERNANCE.md](../GOVERNANCE.md) takes).

### 3.6 Validate locally

Check out the profile at the pinned commit and run the adopter validator from the project root:

```bash
git clone https://github.com/MosslandOpenDevs/agentic-assurance-profile .assurance-profile-pin
git -C .assurance-profile-pin checkout REPLACE_WITH_FULL_40_CHARACTER_COMMIT_SHA
pip install --require-hashes -r .assurance-profile-pin/requirements-ci.txt  # or: pip install pyyaml jsonschema
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

Presence is not enough where PROFILE.md mandates content: the `residuals` register must carry at least one entry for every non-archived profile, `invariants` at least one under `service`, and `claims` at least one under `trust-critical` — an empty array satisfies every per-entry check vacuously and passes no obligation. A project that believes it has zero residual risk should record that belief as its first residual. Since v0.3.0 the register schemas also reject empty or whitespace-only strings in semantic fields (`owner`, `statement`, `enforcement[]`, `evidence[]`, `accepted_by`, ...), matching the lite envelope's rules.

Under `layout: lite` (§3.0) the same command applies, with two differences. `.agentic-assurance/assurance.yaml` is validated — the envelope against the lite schema, each present section against the corresponding register schema, and the combined content through the same semantic checks. And the split per-profile file checks are replaced by the lite rules: the file itself must exist, `residuals` must be present, either a `system` section or a file at `paths.system` must exist, and any profile beyond `core`/`archived` is an error pointing to the graduation path of §3.0.

It also emits non-blocking warnings: `trust-critical` without a defeaters file; entries classified `RESTRICTED` or `EMBARGOED` (verify the file is not public); a local `.github/ISSUE_TEMPLATE/` without a `config.yml` (§3.5); and selection of the provisional `agent-runtime` profile.

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

Each component names the repository paths it covers — gitwildmatch-style globs, where `**` crosses directory boundaries and `*`/`?` stay within one path segment — and the invariant IDs those paths protect. `tests` is recorded but not checked in this release.

When the map is present, the reusable workflow (§3.4) runs a drift check on every pull request, against the pinned validator like everything else; push-event runs are unaffected. Changed files are computed rename-safely: a rename or copy counts both its source and its destination path, so moving code out of a mapped path cannot escape the component's globs. For each component whose `paths` match at least one changed file, the pull request satisfies that component if any of the following holds:

1. the **added lines** of the assurance-artifact diff (paths under `assurance/` or `.agentic-assurance/`) reference at least one of the component's invariant IDs, matched with token boundaries — merely touching some assurance file is not enough (an unrelated register edit does not satisfy an unrelated component), unchanged context lines around an edit do not count, deleting an entry does not count as an update, and a longer ID such as `INV-CORE-001-EXT-002` does not satisfy `INV-CORE-001`;
2. the pull-request description mentions every invariant ID listed for the component (a plain substring match; listing them under "Affected assurance IDs" in the pull-request template is sufficient);
3. the description carries an explicit no-impact statement — both lines at the start of a line, and the reason is mandatory (`Assurance impact: none` alone does not satisfy):

```text
Assurance impact: none
Reason: <why this change cannot affect the mapped invariants>
```

An unsatisfied component produces a warning — surfaced as a GitHub annotation in the checks UI, with a routing table in the job summary — naming the component, the number of matched files, and the invariant IDs to address; the job still passes. To escalate the warnings into a failing check, pass the `strict-drift` input to the reusable workflow:

```yaml
    with:
      strict-drift: true
```

Without a `components` map the component routing reports that impact routing is not configured and passes.

**Policy regression check.** On the same pull-request run, the assurance policy is compared against the base branch — at two levels.

The *adoption declaration*: an `adoption_stage` downgrade, a removed profile, a `layout` change, a removed component, removed path globs / invariant IDs inside a component, a changed `project.human_owner`, a changed `human_review.reviewer` or `human_review.record` (the provenance the declared stage rests on; `human_review.date` is deliberately not compared — advancing it is the normal re-review act), a changed artifact path under `paths:` (a moved path can point the validator at a freshly emptied file), or a changed `security.public_assurance_root`. A changed `upstream` pin is flagged with neutral wording: an upgrade is not a weakening, but [PROFILE.md §16](../PROFILE.md) requires every pin move to be an explicit, dedicated change, so it demands the same acknowledgment.

The *registers themselves*, compared by stable ID (the substance the declaration merely frames). The governing principle: a human-reviewed assurance item cannot quietly disappear, whatever form the change takes — a deleted entry, a deleted register file, or a status that closes it out. Detected:

- **Any register:** a deleted entry; a whole register that was present on the base branch and is gone on the head — or unreadable, or structurally unusable (including a path that exists but is not a readable regular file), or carrying duplicate IDs on the head (each fails closed: a register that cannot be compared reliably must never pass silently). An optional register such as `invariants` under the `core` profile could otherwise be deleted in full with no finding.
- **Every entry, all registers:** a changed `owner` (an accountability transfer); a recorded judgement value *unset* — removed, emptied, or replaced with a non-string value. That covers `status` everywhere plus `severity`, `proof_tier`, `impact`, and `uncertainty`: every weakening check below needs a meaningful value on both sides, so dropping one would otherwise be a free first hop (delete it in one pull request, record a weaker value in the next, both silent, while the one-step edit is a finding). The residual/defeater disposition gates additionally fire on *arriving* at a gated status whatever the base recorded. Also: items removed from the kind's relationship/basis lists — `evidence`/`invariants`/`limitations`/`defeaters`/`residuals` on claims, `assumptions`/`limitations`/`defeaters`/`residuals` on invariants (at *every* severity), `affected_claims`/`affected_invariants`/`evidence` on defeaters, `affected_claims`/`affected_invariants`/`mitigation` on residuals. Severing an assurance-graph edge (why a claim could be wrong, what a defeater affects, how a residual is mitigated) is a mechanism change, not a wording one.
- **Invariants:** severity downgraded; conclusion status weakened (`VERIFIED`/`INFERRED` toward `UNKNOWN`); an `INTENDED` intent reclassified (to `UNKNOWN`, `ACCIDENTAL`, `COMPATIBILITY`, or `DEPRECATED` — `INTENDED` is the recorded human commitment) or unset altogether, by the same first-hop reasoning as `status`; `enforcement`/`verification`/`evidence` items removed from a high/critical invariant.
- **Claims:** status weakened; `proof_tier` downgraded.
- **Invariants and claims:** a recorded `CONTRADICTED` status *cleared* (moving to `CONTRADICTED` is an honesty upgrade and is never flagged; moving away from it resolves a known problem and needs review).
- **Residuals:** impact or uncertainty downgraded (the two assessment axes of [PROFILE.md §12](../PROFILE.md)); the residual *closed* (status → `RESOLVED`); the residual *accepted* (status → `ACCEPTED` — accepting a risk is a human decision, and the acceptance fields are self-declared strings, so the transition itself routes through the gate); an existing acceptance record rewritten or removed (`accepted_by`/`accepted_at`/`acceptance_rationale`).
- **Defeaters:** the defeater *closed* (status → `MITIGATED`/`RESOLVED`/`WITHDRAWN`); a `MITIGATED` defeater moved to a terminal disposition (`RESOLVED`/`WITHDRAWN` assert the risk is gone or was never real — a materially stronger statement than "reduced").
- **Defeaters and residuals:** `review_after` removed, replaced with an unparsable value, or pushed out *after the recorded date had already passed* — an overdue re-review is done, not deferred, and postponing it is how a live overdue warning would otherwise be cleared. Rescheduling a date still in the future is the normal outcome of actually doing the review and is not a finding; nor is moving it earlier or adding one. An unparsable value on the base branch still counts as a recorded commitment (dropping it, or swapping it for different garbage, is a finding; repairing it into a real date is not).

Re-opening a closed residual or defeater, and recording a new contradiction, are never findings. Wording is deliberately not compared in the narrative fields — claim `text`, invariant `statement`/`title`, residual `summary` — which remain the §4.3 human review's terrain. The protected lists above are the exception, and by design: their items are commitments recorded one by one, compared as string sets, so rewording an assumption, limitation, or mitigation reads as removing it. Re-adding the corrected item in the same change leaves both the removal finding and the acknowledgment on the record, which is the intended outcome for edits to a reviewed caveat. Legitimate versions of the gated changes (a real acceptance, a real owner handover, a review-cycle `review_after` bump) surface as findings *by design*: they are exactly the human decisions the gate exists to put on the record.

Each finding fails the drift job (regardless of `strict-drift`) unless the pull-request description acknowledges it with an explicit line:

```text
Assurance policy change: <why this weakening is intended and who decided it>
```

**The acknowledgment is proportional to the declared stage.** It is a self-declaration by whoever writes the PR description — including an agent — so its force is capped by what the *base* declaration had asserted: at `DRAFT`, the acknowledgment downgrades findings to visible warnings; from `HUMAN_REVIEWED` on, findings stay errors even when acknowledged — the red check is the honest signal that reviewed policy is being weakened, and merging over it is the human owner's recorded decision. (The base branch's stage is the yardstick, not the head's — a downgrade PR would otherwise lower its own bar in the same change.)

This closes the self-downgrade loophole — a pull request that flips `adoption_stage: CONFORMANT` back to `DRAFT` would otherwise skip the `declared-stage` check silently, and a shrunken component map would evade routing with policy the base branch never agreed to drop. Additions (new components, added invariants, new registers, a stage raise) are never findings. When the adoption file does not exist on the base branch (a brand-new adoption, or a moved declaration), the comparison is skipped with a notice — treat a *moved* declaration as an assurance policy change in its own right.

The map itself is validated in the ordinary adopter run (§3.6): each component requires non-empty `paths` and `invariants`, and every listed invariant ID must exist in the invariant register — split or lite layout alike — so a dangling component reference is a validation error, not a silently dead route.

The drift check is a plain validator subcommand, runnable locally against the pinned checkout:

```bash
git diff --name-only BASE_SHA...HEAD_SHA > changed-files.txt
git diff BASE_SHA...HEAD_SHA -- assurance .agentic-assurance > assurance-diff.txt
git show BASE_SHA:.agentic-assurance/adoption.yaml > base-adoption.yaml
python .assurance-profile-pin/scripts/validate.py drift \
  --adoption .agentic-assurance/adoption.yaml \
  --changed-files changed-files.txt \
  --pr-body pr-body.txt \
  --assurance-diff assurance-diff.txt \
  --base-adoption base-adoption.yaml
```

`--changed-files` takes newline-separated repository-relative paths; `--pr-body` takes the pull-request description as a file, where a missing or empty file means an empty description. `--assurance-diff` and `--base-adoption` are optional: without the former, any assurance change satisfies every touched component (the coarse standalone fallback — CI always passes the diff); without the latter, the policy regression check is skipped. To reproduce the register-level diff, additionally materialize the base branch's tree — `git worktree add --detach /tmp/base-tree <base-sha>`, which is what CI does (a worktree, unlike per-file `git show`, keeps symlinked registers readable) — and pass `--base-registers-root /tmp/base-tree --project-root .`. Add `--strict` to reproduce the escalated mode and `--json` for machine-readable output. (`--name-only` is fine for a quick local run; the CI computation additionally lists rename sources, and scopes the assurance diff by the `paths:` both declarations actually name — custom artifact locations included.)

On noise: start with two to four components covering the paths of your critical invariants, and expand the map only as it proves quiet — a map that warns on every routine pull request teaches reviewers to ignore the warnings.

### 3.8 Adoption stages: DRAFT, HUMAN_REVIEWED, CONFORMANT

The optional `adoption_stage` field in `adoption.yaml` declares how far the adoption has progressed. Nobody awards a stage — the declaration is self-made and self-binding: the validator enforces exactly the stage you declare, turning its requirements into errors. Declare high, meet it, or the build is red. An absent field means `DRAFT`, and a `DRAFT` (or absent) declaration changes nothing: validation behaves exactly as in §3.6.

Each stage includes every requirement of the stages below it:

| Stage | Adds on top of the previous stage | Who advances it |
|---|---|---|
| `DRAFT` | Nothing — the ordinary validation of §3.6; unfilled placeholders and `UNKNOWN` are allowed in the local assurance registers. The adoption declaration itself (upstream pin, project identity, paths) must be complete at every stage: §3.6 always errors on an unfilled placeholder in `adoption.yaml`. | Nobody needs to; it is the default. |
| `HUMAN_REVIEWED` | No unfilled `REPLACE_WITH_` placeholder in any loaded register (split sections or the lite file alike); a `human_review` block with non-empty `date`, `reviewer`, and `record`. | The human owner, after completing the §4.3 review. |
| `CONFORMANT` | Passed `review_after` dates are errors (as with `--strict-review-dates`); every severity-`critical` invariant has a decided `intent.classification` — anything but `UNKNOWN`, so `ACCIDENTAL` or `DEPRECATED` counts as decided; at least one attributable entry in `human_review.approvals`. Additionally, the mechanically checkable subset of [PROFILE.md §17](../PROFILE.md): no `critical` residual left `OPEN` (accept it with rationale or resolve it), no `CONTRADICTED` claim, no `CONTRADICTED` critical invariant, every `VERIFIED` critical invariant carries non-empty `evidence`, and no register entry classified `RESTRICTED` or `EMBARGOED` in a public repository (the reusable workflow passes the repository's actual visibility; standalone runs declare it with `--repo-visibility`, and an undeclared visibility is treated as public, conservatively). In a private repository RESTRICTED entries stay the standing warning — §17 excludes restricted material from *public* artifacts, and §3.6's visibility binding already governs the private case. | The human owner, when standing behind the conformance statement of [PROFILE.md §17](../PROFILE.md). |

Honest boundary: even at `CONFORMANT`, the validator checks what strings can carry. Whether evidence is bound to the revision it claims to cover, and whether claim wording stays within evidence strength, remain the §4.3 human review's responsibility — a green `declared-stage` check at `CONFORMANT` asserts the mechanical subset, not the whole of §17.

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
      covers: [ INV-AUTH-001, RES-002 ]   # optional: what the approval covers
      rule: codeowners-default-branch     # optional: the local review rule it satisfies
```

`approver`, `review_url`, and `at` must all be non-empty; `covers` and `rule` are optional. One honest limitation, stated plainly: the workflow does not yet verify the `review_url` through the GitHub API — it does not check that the URL is a real approved review, or that the approver is not the author. Treat the entry as a claim reviewable by humans, exactly like the rest of the register; future tooling may verify the approved state and author ≠ approver mechanically.

**The CI check split.** The reusable workflow (§3.4) reports two checks so a stage cannot be misread:

- `assurance / structure` always runs: the ordinary adopter validation of §3.6 with stage requirements skipped (the validator's `--ignore-stage` flag) — a `DRAFT`-equivalent pass/fail.
- `assurance / declared-stage` runs the full stage-enforcing validation, and is skipped entirely while the declared stage is `DRAFT` or absent.

Check renames across releases (update branch protection when re-pinning): `assurance / validate` (pre-v0.2.0) became `assurance / structure`; `assurance / conformance` (v0.2.0) became `assurance / declared-stage` in v0.2.1. The second rename is deliberate: the check is green whenever the *declared* stage's requirements are met — at `HUMAN_REVIEWED` as well as `CONFORMANT` — so a check named "conformance" would show green on repositories that assert no conformance at all. The split and the name exist so a green check cannot be misread: green `structure` means structurally valid, green `declared-stage` means the declared stage is honestly met; only a `CONFORMANT` declaration behind a green `declared-stage` asserts conformance.

Locally, the §3.6 command enforces the declared stage by default and reports one summary line on success (`stage <X>: requirements satisfied`); add `--ignore-stage` to reproduce the `structure` check.

## 4. Brownfield adoption

Most adoption is brownfield. Initial adoption of an existing repository must begin as a read-only archaeology task before broad remediation ([PROFILE.md §7](../PROFILE.md)). Classify the profile first (§4.0) — a cheap pass that decides how deep everything after it must go — then work the four-stage sequence (§4.1–§4.4); do not compress the stages into one change, and do not mix archaeology with feature work, security audit, or broad refactoring.

### 4.0 Classify the profile first

The profile set is a *finding*, not a default. Before drafting any artifact, determine which of the [PROFILE.md §5](../PROFILE.md) profiles apply from what the repository **is and promises** — not from its size, and not by starting at `core` in the hope of escalating later. This classification sizes everything downstream: it decides the layout (§3.0 vs §3.1), which registers exist, and how deep the §4.1 reconstruction must go. Run it as a cheap first pass — surface signals are usually enough, and you do not need the full archaeology to classify.

For each escalation trigger, ask the disqualifying question and, when it fires, cite the `file:line` that fired it:

| Trigger | Fires when — surface signals | Adds |
|---|---|---|
| **service** | the repository is deployed or operated: a server framework, a `Dockerfile`, a deploy workflow, a live URL, a stateful backend | `service` |
| **trust-critical** | it makes a security, privacy, identity, authorization, financial, governance, or public-verifiability claim: auth/session/JWT, wallet or SSO login, admin/role gating, voting/proposals/tallies, payment or token transfer, PII handling | `trust-critical` |
| **data-curation** | it derives externally-sourced, editorial, scored, classified, or recommended data: embedding search or ranking, scoring, aggregated external feeds | `data-curation` |
| **agent-runtime** | a model or agent **runs in this repository's production path** — an LLM SDK invoked in a request or worker, not merely a call to a backend that does | `agent-runtime` |

`core` is the baseline every adopter carries; `archived` replaces the others for a repository that is no longer operated ([PROFILE.md §6.6](../PROFILE.md)). The result is the **smallest set that covers every trigger that fires** — that is what "smallest applicable set" means, not "the fewest profiles you can get away with."

**Bias toward escalation.** When a trigger's evidence is genuine but ambiguous in degree, fire it. Under-classification is the expensive mistake: a repository declared `core` gets only the `core` checks, so the claims, proof tiers, and defeaters a trust-critical repository needs are never required — and the run still passes green. Over-classification only costs some unused artifacts, which the owner can drop; under-classification silently turns off enforcement. The owner can de-escalate a conservatively-fired trigger in the §4.3 review with a recorded reason — there is no matching mechanism to catch a trigger that was never fired.

**Attack the classification before you commit it.** Re-open the cited evidence and challenge it from both sides: for each fired trigger, try to prove it should *not* fire — is the code load-bearing, or a stub, example, vendored copy, or test-only path? And hunt for triggers you missed — grep the actual code for the signals above, not just the directory names. (In a pilot classification the cited trust-critical evidence turned out to be a deprecated, frozen module; the adversarial pass found the live trust-critical behavior implemented on a different path — the verdict held, the evidence was corrected.)

**Layout follows the profile, never the size.** `layout: lite` (§3.0) is valid only when the classification is `core` (or `archived`) alone; any fired trigger means the split layout of §3.1. A large, sprawling repository with no external promises can be `core`; a two-hundred-line library that verifies auth tokens is `trust-critical`. Size is not a trigger.

Declare the proposed profile set and layout in `adoption.yaml` itself — the enforced `profiles:` field, not only the handoff prose — and list them in the §4.3 handoff, each fired trigger with its evidence, for the owner to confirm or de-escalate. Leaving `profiles: [core]` in the file while noting the escalation only in prose is the common miss: the handoff is read once, but the `profiles:` field is what selects the checks. The selection stays provisional until the owner's review (§1).

**Worked example.** A loan-underwriting backend that authenticates applicants, gates approval actions by reviewer role, scores each application against externally-sourced credit data, and drafts decision rationales with a production LLM is not `core`. It fires `service` (deployed API), `trust-critical` (identity + authorization + financial), `data-curation` (scored external data), and `agent-runtime` (a model runs in its request path): the honest set is `core + service + trust-critical + data-curation + agent-runtime`, split layout. Declaring it `core` (lite) would hide every claim, proof tier, and defeater it most needs — and pass green. Its separate frontend, which only *calls* that backend for the same LLM-drafted rationale, is `service + trust-critical + data-curation` but **not** `agent-runtime`: the model runs in the backend, not the client. The line is where the model actually executes, not which product it belongs to.

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
- Check the provenance of prose evidence. In an agent-built repository most comments, READMEs, and notes are themselves agent-authored: before citing one as intent authority, `git blame` the lines and inspect the introducing commit's authorship (for example `Co-Authored-By:` trailers, bot committer identities, agent-session branch names). Agent-authored prose may be cited as a *description* of behavior, never as *human intent* — that classification stays `UNKNOWN` until the owner confirms it in the §4.3 review. The check only sorts prose into two bins — *disqualified* (an agent marker is present) and *provenance-uncertain* (no marker, which proves nothing: many agents leave none, and humans commit agent-written text under their own names). It never yields "definitely human"; provenance-uncertain prose is presented to the owner as a candidate, and the owner's §4.3 answer is what settles it. The line that matters is the human act, not the typist: an agent-drafted record of an explicit owner decision, anchored by the owner's reviewed merge, is valid authority (second-pilot lesson — an agent cited an agent-written comment as intent and caught its own circular reasoning). Machine-verifiable evidence (schema constraints, live response headers, command output, code behavior) is unaffected.
- Keep the invariant register small: roughly 5–15 invariants per repository — the things that must never break, not the full specification. The real cost of an invariant is not writing it but re-examining it on every change that touches its scope; an exhaustive register stops being read and starts to rot. If the archaeology surfaces thirty candidates, that is a ranking exercise for the §4.3 review, not thirty register entries.

### 4.2 Behavior classification

This is distinct from the profile classification of §4.0: that decides *which profiles apply*; this classifies *observed behavior*. Classify observed behavior as `INTENDED`, `ACCIDENTAL`, `COMPATIBILITY`, `UNKNOWN`, or `DEPRECATED`, and each conclusion about the system as `VERIFIED`, `INFERRED`, `UNKNOWN`, or `CONTRADICTED` ([PROFILE.md §4](../PROFILE.md)). `UNKNOWN` is a first-class result: recording uncertainty is correct; inventing confidence is prohibited. Current production behavior is evidence of current behavior, not automatic proof of intended behavior.

### 4.3 Human intent review

Before broad remediation, the human owner reviews:

- purpose and non-goals;
- critical claims and invariants;
- the behavior classification from §4.2;
- critical residuals and public claim limitations.

An agent may draft all of this; it may approve none of it.

The adoption draft should arrive as an open pull request and stay unmerged until this review completes; merging the pull request is then the natural durable record that the owner reviewed and accepted the draft as the §4.3 baseline. If the draft was merged early, nothing is lost — corrections and the review record land as follow-up pull requests, as the first pilot did — but branch-until-reviewed is the intended flow. [REVIEW-GUIDE.md](REVIEW-GUIDE.md) is the owner-side companion for making these decisions, walking through each of them in plain language.

### 4.4 Staged remediation

After the intent review:

- record conformance gaps and residuals in the durable artifacts first;
- remediate through separate, scoped issues and pull requests — the `conformance-gap` and `evidence-gap` forms from the adopter bundle (§3.5) exist for exactly this;
- bind new evidence to a commit, artifact digest, release, or deployment identifier;
- map existing conventions instead of duplicating them ([MAPPINGS.md](MAPPINGS.md));
- for critical security, privacy, authorization, financial, governance, or data-integrity work, keep audit and remediation in separate contexts ([PROFILE.md §10](../PROFILE.md)).

## 5. Pilot guidance

For the initial pilot adoptions of this profile (Passport-class projects):

- classify the profile honestly up front (§4.0) — do not assume `core`; the smallest set is the one that covers every trigger the repository fires;
- run the full §4 brownfield sequence to gather the evidence behind that classification before drafting artifacts;
- `service` is warranted once the evidence confirms the repository operates a deployed service, and `trust-critical` once it establishes which security, identity, governance, or public-verifiability claims the project actually makes — claims drive obligations, not the other way around, and a fired trigger is not deferred to "later";
- treat `agent-runtime` as a provisional profile: its obligations may change in a minor release, and the validator warns on its selection. (`data-curation` was promoted from provisional in v0.2.0 after the second pilot exercised it.)

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
- [GLOSSARY.md](GLOSSARY.md) — plain-language definitions of the profile's terminology
- [REVIEW-GUIDE.md](REVIEW-GUIDE.md) — the human owner's guide to reviewing an adoption draft
- [templates/AGENTIC_ASSURANCE.md](../templates/AGENTIC_ASSURANCE.md) — the adopter-side entry document
- [templates/adoption.yaml](../templates/adoption.yaml) — the adoption file template
- [RELEASING.md](../RELEASING.md) — release ritual and the `VERSION` file lifecycle
- [SECURITY.md](../SECURITY.md) — vulnerability reporting for this repository
