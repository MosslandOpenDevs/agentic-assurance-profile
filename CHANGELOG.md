# Changelog

All notable changes to the OpenDevs Agentic Assurance Profile will be documented here.

## Unreleased

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

### Changed

- Unified version strings: the informal draft version identifier is abolished in favor of `unreleased` and `vMAJOR.MINOR.PATCH` release identifiers; `PROFILE.md` §16 adds pre-release naming, tag immutability, version/commit mismatch, and pre-first-release pinning rules.
- Marked the `data-curation` and `agent-runtime` profiles as provisional; while provisional, changes to their obligations are classified as minor.
- Clarified normativity: `PROFILE.md` is the normative text; README files and translations are informative.
- `SECURITY.md` scope now names templates alongside example configurations.
