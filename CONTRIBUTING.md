# Contributing

This document describes how to propose changes to the OpenDevs Agentic Assurance Profile repository. Decision authority is defined in [GOVERNANCE.md](GOVERNANCE.md); the release process is defined in [RELEASING.md](RELEASING.md).

## 1. Where to raise what

The complete routing rules are in [docs/DISCLOSURE-AND-ISSUES.md](docs/DISCLOSURE-AND-ISSUES.md) §3. In summary:

- **This repository** — generic profile wording and terminology, schema and validator behavior, compatibility with existing specification workflows, proposed requirement additions or clarifications, and errors in profile documentation.
- **The adopting project's repository** — project-specific adoption work, conformance gaps, domain invariants, and evidence work.
- **Private security reporting** — suspected or confirmed vulnerabilities, and any finding whose sensitivity is uncertain.

Blank issues are disabled in this repository. Use the issue forms:

| Form | Use for |
|---|---|
| Profile change | Modifying a normative obligation, schema, or template |
| Clarification | Resolving ambiguous wording without changing intent |
| Adoption question | Questions about applying the profile to a repository (consult [docs/ADOPTION.md](docs/ADOPTION.md) first) |
| Tooling defect | Defects in schemas, the validator, workflows, or templates |

**Do not describe a suspected vulnerability in a public issue.** Follow [SECURITY.md](SECURITY.md) and use GitHub's private vulnerability reporting. When uncertain whether a finding is sensitive, route it privately first.

## 2. Pull request requirements

Every pull request follows the repository pull-request template. A pull request states:

- a summary and the related issue or advisory;
- the affected profile sections and stable IDs (for example `AAP-CORE-004`);
- its change classification: normative obligation change, schema change, template change, documentation only, or tooling only;
- its semver impact — major, minor, or patch per [PROFILE.md](PROFILE.md) §16 — with a one-line justification;
- a completed synchronization checklist (§3);
- a disclosure check confirming it contains no secrets, personal data, or actionable vulnerability detail.

Changes to `PROFILE.md`, `schemas/`, or `templates/` require approval by at least one human maintainer who did not author the change. Agents may draft changes; they never approve them ([GOVERNANCE.md](GOVERNANCE.md) §3).

## 3. Synchronization checklist

The normative text, schemas, templates, and documentation of this repository describe one profile and must not drift apart. Every pull request confirms, for each of the following, that it was either updated or is explicitly not affected:

- `PROFILE.md`;
- `schemas/`;
- `templates/`;
- `docs/`;
- `README.md`;
- `README.ko.md` (see §4);
- a `CHANGELOG.md` entry added under `## Unreleased`;
- `python scripts/validate.py self-check` passes locally (the `self-check` workflow also runs it on every push and pull request).

## 4. Language and translation rule

The English [PROFILE.md](PROFILE.md) is the normative text of the profile. All README files and translations are informative.

[README.ko.md](README.ko.md) is an informative Korean translation of [README.md](README.md). A pull request that changes README.md updates README.ko.md in the same pull request, or explicitly marks the affected Korean sections as stale so that a follow-up translation pass can find them. A silently diverged translation is treated as a documentation defect.

## 5. Licensing of contributions

Contributions are accepted under the license governing the paths they touch:

| Paths | License | License file |
|---|---|---|
| `schemas/`, `scripts/`, `.github/` workflows, and other tooling code | Apache-2.0 | [LICENSE](LICENSE) |
| `PROFILE.md`, `README.md`, `README.ko.md`, `docs/`, `SECURITY.md`, and all other prose | CC-BY-4.0 | [LICENSE-docs](LICENSE-docs) |
| Everything under `templates/` | CC0-1.0 | [templates/LICENSE](templates/LICENSE) |

The split is deliberate: code carries a standard software license with a patent grant (Apache-2.0); prose carries an attribution license suited to documents (CC-BY-4.0); templates are dedicated to the public domain (CC0-1.0) so that adopters can copy them into their repositories with no attribution obligation. By submitting a contribution, you agree that it is provided under the license governing each touched path.
