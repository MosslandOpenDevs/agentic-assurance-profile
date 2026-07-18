# Changelog

All notable changes to the OpenDevs Agentic Assurance Profile will be documented here.

## Unreleased

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
