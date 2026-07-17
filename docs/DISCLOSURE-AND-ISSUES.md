# Disclosure and GitHub Issue Model

This document defines how durable assurance artifacts, public GitHub Issues, pull requests, evidence, and private security reports relate to each other.

## 1. The state/work distinction

The profile separates **state** from **work**.

- Assurance artifacts describe durable project state: intended behavior, claims, invariants, controls, evidence status, defeaters, and residuals.
- Issues describe work: a proposed change, clarification, gap, investigation, or remediation task.
- Pull requests propose reviewable modifications to state and implementation.
- CI and release artifacts provide evidence.
- Security Advisories contain confidential vulnerability details.

An Issue is not the normative source of truth. Closing an Issue does not, by itself, alter a claim, satisfy an invariant, or resolve a residual.

## 2. Stable identifiers

Use stable semantic IDs for profile and project artifacts.

Recommended namespaces:

| Prefix | Meaning | Example |
|---|---|---|
| `AAP-` | Upstream Agentic Assurance Profile requirement | `AAP-CORE-004` |
| `CLAIM-` | Project claim | `CLAIM-IDENTITY-002` |
| `INV-` | Project invariant | `INV-AUTH-007` |
| `DEF-` | Defeater or counterevidence item | `DEF-AUTH-003` |
| `RES-` | Residual uncertainty or accepted risk | `RES-DATA-005` |
| `ADR-` | Architecture or policy decision | `ADR-0017` |

GitHub Issue numbers are workflow identifiers, not assurance identifiers.

Each relevant Issue and pull request should state its affected IDs explicitly.

```markdown
## Affected assurance IDs

- AAP-SERVICE-003
- INV-AUTH-007
- RES-AUTH-004
```

## 3. Routing matrix

### 3.1 Public central-profile Issue

Use the central profile repository for:

- generic wording or terminology;
- schema and validator behavior;
- profile-level compatibility with OpenSpec, Spec Kit, ADR/RFC, CI, or release workflows;
- non-sensitive examples;
- proposed requirement additions or clarifications;
- errors in profile documentation.

Do not place project-specific exploit details in the central repository.

### 3.2 Public adopting-project Issue

Use the adopting project repository for:

- initial adoption tasks;
- as-built documentation work;
- non-sensitive conformance gaps;
- missing tests or evidence where the gap is not itself exploitable;
- documentation drift;
- accepted public residuals;
- project-specific claim or invariant changes;
- general hardening whose details are safe to disclose.

### 3.3 Private security report or advisory

Use GitHub Private Vulnerability Reporting, a draft Security Advisory, or another restricted channel for:

- suspected or confirmed exploitable vulnerabilities;
- authentication, authorization, privacy, financial, or data-integrity bypasses;
- secrets or credentials;
- proof-of-concept exploit code;
- affected-version details before a fix is available;
- sensitive production topology, logs, or user data;
- residual details that materially lower the cost of attack;
- a finding whose sensitivity is uncertain.

When uncertain, route privately. Maintainers can later decide that a sanitized public Issue is safe.

## 4. Issue types

Recommended public Issue types and labels:

| Issue type | Suggested labels | Purpose |
|---|---|---|
| Profile change | `profile/change`, `needs-decision` | Modify a generic obligation or schema |
| Clarification | `profile/clarification`, `documentation` | Resolve ambiguous wording without changing intent |
| Adoption | `assurance/adoption`, `project` | Introduce the profile into an existing repository |
| Conformance gap | `assurance/gap`, severity label | Track a non-sensitive mismatch with adopted obligations |
| Evidence gap | `assurance/evidence` | Add or refresh reproducible evidence |
| Residual review | `assurance/residual`, `needs-human-approval` | Review a known limitation or acceptance decision |
| Tooling defect | `bug`, `tooling` | Fix schema, validator, generator, or workflow behavior |

Do not create a public `security-vulnerability` Issue type. The issue chooser should direct vulnerability reporters to `SECURITY.md` and private reporting.

### 4.1 Issue form placement

The taxonomy above maps onto concrete GitHub issue forms in two tiers:

- **Central profile repository** (`.github/ISSUE_TEMPLATE/` in this repository): `profile-change.yml`, `clarification.yml`, `adoption-question.yml`, and `tooling-defect.yml`. Schema work splits across two of these: a change to what a schema requires is an obligation change and routes to `profile-change.yml`; a schema that fails to encode the documented obligation is a defect and routes to `tooling-defect.yml`. Adoption questions directed at the profile maintainers use `adoption-question.yml`; a project's own adoption work items belong in that project's repository (§3.2).
- **Adopter bundle** ([templates/github/ISSUE_TEMPLATE/](../templates/github/ISSUE_TEMPLATE/), copied whole into the adopting repository): `bug.yml`, `feature.yml`, `conformance-gap.yml`, `evidence-gap.yml`, and `residual-review.yml`.

Both tiers must ship a `config.yml` with `blank_issues_enabled: false` and a contact link routing suspected vulnerabilities to private security reporting. This is load-bearing, not decorative: GitHub treats any file in a repository's `.github/ISSUE_TEMPLATE/` directory as a complete replacement of the organization default set, including `config.yml` — a partial copy silently re-enables blank issues and drops the private-reporting link.

## 5. Lifecycle

### 5.1 Ordinary public change

```text
Issue
  → human scope and affected IDs
  → pull request
  → implementation and/or profile update
  → deterministic verification
  → independent review when required
  → evidence bound to revision or deployment
  → claims/invariants/residuals updated
  → merge
  → Issue close
```

Use a closing keyword only when the pull request completes the declared acceptance criteria. Otherwise use a plain reference.

Examples:

```markdown
Closes #123
```

Use only when the PR completes the work, including evidence and durable artifact updates.

```markdown
Related to #123
```

Use when the PR is one step in a larger change.

### 5.2 Security change

```text
Private report
  → private triage
  → draft Security Advisory
  → private reproduction and affected-version analysis
  → private remediation
  → independent re-verification
  → release
  → coordinated disclosure decision
  → advisory publication
  → sanitized public profile/evidence update
```

A public Issue may be created after disclosure to track long-term hardening, documentation, or follow-up work, but it should reference the published advisory rather than reproduce confidential discussion.

## 6. Relationship between profile status and Issue status

| Situation | Issue may close? | Assurance item status |
|---|---:|---|
| Code changed but no evidence produced | No | Unverified or partially verified |
| Test added but no enforcement exists | Usually no | Evidence exists; invariant remains weakly enforced |
| Control and test added, evidence bound to release | Yes, if acceptance criteria met | Verified for the bounded revision |
| Finding cannot be fixed but human accepts residual | Yes, after approval | Residual remains active and accepted |
| Issue closed as “not planned” | Yes | Claim/invariant/residual must still reflect the unresolved state |
| Duplicate Issue closed | Yes | Canonical Issue and assurance ID remain active |
| Security advisory fixed but not yet disclosed | Private advisory may remain open | Public profile remains sanitized until disclosure decision |

## 7. Required Issue fields

A non-trivial assurance Issue should contain:

1. problem statement;
2. affected profile and project IDs;
3. current evidence or reason evidence is absent;
4. expected durable artifact changes;
5. acceptance criteria;
6. disclosure classification;
7. explicit statement that no active vulnerability detail is included, when public;
8. human decisions required;
9. expected residual impact.

## 8. Required pull-request fields

A material pull request should contain:

1. related Issue or advisory;
2. affected profile and project IDs;
3. intent and non-goals;
4. implementation/control changes;
5. verification commands and evidence location;
6. independent review status when required;
7. claim, invariant, defeater, and residual changes;
8. migration and rollback impact;
9. disclosure classification;
10. exact reason the linked Issue may close.

## 9. Public profile redaction rules

Redaction should preserve meaning without preserving exploitability.

Good public summary:

```yaml
- id: RES-AUTH-004
  summary: Authentication replay resistance is under restricted review.
  disclosure: SUMMARY_ONLY
  status: mitigated_pending_release
  review_after: 2026-08-15
```

Unsafe public entry:

```yaml
- id: RES-AUTH-004
  description: Exact endpoint, race window, request sequence, and bypass payload...
```

A public summary is optional. If even the existence or timing of the review creates material risk, omit the entry from the public projection and retain it only in the restricted record.

## 10. Automation boundaries

Automation may:

- verify required IDs and fields;
- detect stale evidence;
- detect a closed Issue whose referenced residual remains unresolved;
- ensure a pull request names affected artifacts;
- validate schemas;
- generate sanitized public summaries from explicitly public source data.

Automation must not:

- decide that sensitive material is safe to publish;
- downgrade `RESTRICTED` or `EMBARGOED` content automatically;
- accept a critical residual for the human owner;
- copy private advisory content into public Issues, PRs, logs, or artifacts;
- treat Issue closure as proof of verification.

## 11. Organization-level defaults

An organization may place default community health files in a public `.github` repository, including `SECURITY.md`, contribution guidance, and Issue/PR templates. Project repositories can override those defaults when their threat model or adoption profile requires stricter handling.

The central assurance profile remains the normative reference; the organization `.github` repository is the distribution point for default GitHub workflow files.
