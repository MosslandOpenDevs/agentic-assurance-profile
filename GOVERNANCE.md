# Governance

This document defines who holds decision authority over the OpenDevs Agentic Assurance Profile repository and how that authority is exercised.

[PROFILE.md](PROFILE.md) §3 requires a named human owner or governing body to retain authority over purpose, critical claims, the wording of public trust claims, the weakening of controls, the acceptance of critical residuals, and restricted disclosure. This document satisfies that requirement for this repository itself: the profile is governed under the same authority model it asks adopting projects to follow.

## 1. Governing body

The governing body of this repository is the **MosslandOpenDevs maintainers**, represented on GitHub by the `@MosslandOpenDevs/maintainers` team named in [.github/CODEOWNERS](.github/CODEOWNERS). Until that team is populated with real maintainer handles, the CODEOWNERS entry is a placeholder, and the pre-first-release checklist in [RELEASING.md](RELEASING.md) blocks the first release.

For this repository, the governing body retains authority over:

- the purpose and non-goals of the profile;
- every normative obligation in PROFILE.md, including its wording and limitations;
- the schemas and templates that encode those obligations;
- weakening or removal of any control, evidence obligation, or release safeguard;
- acceptance of critical residuals in the profile's own assurance record;
- disclosure decisions for restricted or embargoed security material handled under [SECURITY.md](SECURITY.md).

## 2. Decision rules

- Changes to normative text (`PROFILE.md`), to `schemas/`, or to `templates/` require review and approval by at least one human maintainer who did not author the change.
- A change classified as **major** under PROFILE.md §16 requires explicit governing-body approval, recorded in the release pull request that ships it.
- Documentation-only and tooling-only changes follow the ordinary pull-request process; branch protection still requires at least one approving human review.
- Every change states its semver classification per PROFILE.md §16 in the pull request (see [CONTRIBUTING.md](CONTRIBUTING.md)).

### Review classes — what a shipped change actually received

Every release states, honestly, which of these classes its changes received; the class is a fact about the record, not an aspiration:

- **INDEPENDENTLY_REVIEWED** — an approving review by a human maintainer who did not author the change, durably recorded on the pull request.
- **SOLE_OWNER_ATTESTED** — reviewed and merged on the sole maintainer's own authority, with no independent human review on record. This is the honest current default: the maintainers team has one active member, GitHub does not allow self-approval, and a merge performed by a second account is not an approving review.
- **AUTOMATION_VERIFIED** — the mechanical evidence that accompanied the change: self-check, the validator regression suite, workflow lint, and any external review text folded into the change.

The decision rules above state the intended bar (independent review for normative text, schemas, and templates). Until a second active maintainer exists, releases ship as SOLE_OWNER_ATTESTED + AUTOMATION_VERIFIED, and any external technical reviews are cited in the release pull request rather than counted as approvals. Assuming an independent review that did not happen would violate the profile's own prose-provenance principle; recording the true class is the conformant behavior. The reusable workflow's trust assumption should be read accordingly: "maintainer-reviewed canonical commit" means reviewed under whichever class the release records.

## 3. Role of agents

AI agents may draft any change in this repository: profile text, schemas, templates, documentation, and tooling. Agents never approve. An approving review must come from a human maintainer, and the agent prohibitions of PROFILE.md §15 apply to work on this repository exactly as they apply to adopting projects.

## 4. Required repository settings

The decision rules above are only as strong as the settings that enforce them. The following must be enabled, and they are verified by the pre-first-release checklist in [RELEASING.md](RELEASING.md):

- branch protection on `main` requiring at least one approving human review before merge;
- CODEOWNERS entries with real maintainer handles, so that changes to `PROFILE.md`, `schemas/`, `templates/`, `docs/`, `GOVERNANCE.md`, `RELEASING.md`, and `SECURITY.md` request review from the governing body;
- a tag ruleset protecting `v*` tags from being moved, deleted, or reused, backing the tag-immutability rule in RELEASING.md.

## 5. Amending this document

Changes to GOVERNANCE.md follow the same rule as normative text: review and approval by at least one human maintainer who did not author the change. A change that transfers, reduces, or redistributes the governing body's authority additionally requires explicit governing-body approval recorded in the pull request. Agents may draft amendments; they may not approve them.
