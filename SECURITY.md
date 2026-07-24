# Security Policy

## Scope

This policy covers security issues in the OpenDevs Agentic Assurance Profile repository itself, including:

- normative profile text whose ambiguity could cause unsafe adoption;
- JSON/YAML schemas and validators;
- setup, synchronization, or migration scripts;
- GitHub Actions and release automation;
- templates and example configurations that could create an unsafe default;
- documentation that directs users to disclose sensitive information publicly.

A weakness in an adopting project should normally be reported to that project's maintainers, not to this profile repository, unless the weakness is caused by the profile or shared tooling.

## Reporting a vulnerability

**Do not open a public GitHub Issue for a suspected vulnerability.**

Use GitHub's **Report a vulnerability** function under the repository's Security tab. The repository maintainers should enable Private Vulnerability Reporting before the first public release.

If private vulnerability reporting is unavailable, open a public Issue containing no technical details and ask maintainers to establish a private contact channel. Do not include reproduction steps, affected secrets, logs, user data, exploit code, or an actionable attack path in that Issue.

A useful private report includes:

- affected profile version, commit, schema, validator, or script;
- impact and plausible abuse scenario;
- reproduction steps or proof-of-concept;
- affected and unaffected configurations, when known;
- suggested mitigation, when available;
- disclosure constraints and credit preference.

## Handling process

Maintainers should:

1. acknowledge and triage the report privately;
2. create or accept a draft GitHub Security Advisory;
3. reproduce and bound the issue;
4. prepare and verify a fix in a private working area when necessary;
5. determine affected versions and migration requirements;
6. release the fix;
7. publish an advisory and sanitized profile update when coordinated disclosure is appropriate.

An unresolved vulnerability must not be converted into a public conformance Issue merely to fit the profile workflow.

## Public assurance versus private security detail

Public profile artifacts may include:

- a sanitized statement of the affected requirement;
- the fact that evidence was refreshed;
- a published advisory identifier after disclosure;
- a non-actionable residual summary;
- affected and fixed versions after coordinated disclosure.

They must not include, before authorized disclosure:

- proof-of-concept exploit code;
- exact control-bypass conditions;
- secrets, personal data, or private reporter information;
- production topology or logs that materially lower attack cost;
- links to private evidence that leak through permissions or artifact settings.

## Supported versions

Releases are listed here as they are published. Between releases, the draft on the default branch is also maintained.

| Version | Supported |
|---|---|
| `v0.5.0` | Yes — current release |
| `v0.4.0` | Yes — previous release; upgrade at convenience (v0.5.0 adds the optional `aap check` local CLI and the v0.5 governance/design records; it changes no adopter obligation, so a v0.4.0 adoption remains conforming) |
| `v0.3.2` | Yes — previous release; upgrade at convenience (v0.4.0 requires an invariant for every active adoption, restricts `layout: lite` to `core` alone, gives the two root guides a reading-order and an unfilled-placeholder obligation, and fixes a false accept that let an adoption reach `CONFORMANT` with both root guides left as untouched upstream templates) |
| `v0.3.1` | Yes — previous release; upgrade at convenience (v0.3.2 closes a fail-open on symlinked base registers and change-controls recorded decisions — residual acceptance, terminal dispositions, unset judgement values, assurance-graph edges) |
| `v0.3.0` | Yes — previous release; upgrade at convenience (v0.3.1 completes the register policy diff — whole-register removal, closing dispositions, claim-basis removal — and hardens the drift diff step) |
| `v0.2.1` | Yes — previous release; upgrade at convenience (v0.3.0 adds the register policy diff and closes a drift-job file-read; no CI trust-boundary regression) |
| `v0.2.0`, `v0.1.2`, `v0.1.1`, `v0.1.0` | Superseded by `v0.2.1`: their reusable `adopter-validate.yml` carries the CI trust-boundary issue fixed in v0.2.1 (the validator checkout source was read from the pull-request-mutable adoption file). Documents and schemas remain usable, but re-pin before running the reusable workflow on a repository that accepts external pull requests. |
| `v0.1.0-rc.1` | Superseded — upgrade to the current release |
| Draft on default branch | Yes |
| Earlier unreleased draft commits | No — upgrade to the current release |
| Unreleased local forks | No |

## Disclosure principle

The profile exists to make residual uncertainty explicit, not to publish active attack instructions. When transparency and immediate safety conflict, preserve the evidence privately and publish a sanitized summary until coordinated disclosure is complete.
