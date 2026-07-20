# OpenDevs Agentic Assurance Profile

> A lightweight, evidence-oriented adoption profile for software substantially built or maintained by AI coding agents.

**Status:** Released — current release on the [releases page](https://github.com/MosslandOpenDevs/agentic-assurance-profile/releases)  
**Repository:** `MosslandOpenDevs/agentic-assurance-profile`  
**Current maturity:** reference profile, not a certification scheme

> **Normative status:** [PROFILE.md](PROFILE.md) is the normative text. This README and all translations are informative summaries; where they disagree, PROFILE.md governs.

The profile helps a project preserve the parts of software development that code generation does not make cheap:

- why the system is designed this way;
- which properties must remain true;
- which controls actually enforce those properties;
- which evidence supports the project's claims;
- which counterarguments, limitations, and residual risks remain;
- which decisions still require explicit human authority.

Its working chain is:

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

A project can adopt the profile without changing editor, programming language, agent vendor, deployment platform, or existing specification workflow.

---

## Why this exists

AI coding agents can produce and modify implementation faster than teams can reconstruct intent, validate assumptions, or understand the consequences of change.

The resulting risk is not only defective code. A system can be internally consistent while still implementing the wrong requirement, preserving an accidental behavior, weakening an unstated invariant, or presenting a public claim that its evidence does not support.

This profile treats the following as first-class project artifacts:

| Artifact | Question it answers |
|---|---|
| Intent and non-goals | What is this system for, and what is it explicitly not for? |
| Claim | What does the project assert to users, operators, or integrators? |
| Invariant | What must remain true across every permitted state and change? |
| Enforcement | What prevents an invariant violation? |
| Evidence | What reproducibly supports the claim or invariant? |
| Defeater | What concrete reason might make the claim false or incomplete? |
| Residual | What known uncertainty, limitation, or accepted risk remains? |

The objective is not to eliminate all uncertainty. It is to make the boundary between demonstrated properties and remaining doubt inspectable.

---

## Origins

This profile descends from a question Donald Knuth answered for an earlier era. *TeX: The Program* treated a program as something to be explained to people, not merely executed: the reasoning, the invariants, and the argument for correctness were part of the work itself. AI coding agents invert the economics that once made that discipline optional. Implementation is now cheap, but design rationale, invariants, evidence, and known limitations do not write themselves — and they are exactly what a project loses when code is produced faster than intent can be recorded.

The immediate origin is practical. [Passport](https://passport.moss.land), a Mossland project, was built almost entirely by AI coding agents, without a conventional code editor. Working that way makes the gap concrete: the owner's role shifts from writing code to governing claims, invariants, evidence, and residual risk — and that governance needs a durable, inspectable form. This profile is that form.

---

## What this project is

The OpenDevs Agentic Assurance Profile is:

- a **repository-level adoption profile** for AI-agent-assisted software engineering;
- **brownfield-first**: designed to reconstruct and govern systems that already exist;
- **evidence-oriented**: an agent's narrative is not accepted as proof by itself;
- **model-neutral and tool-neutral**;
- compatible with existing specification, issue, pull-request, test, CI, and release workflows;
- a way to connect human intent, implementation controls, verification evidence, and residual uncertainty.

## What this project is not

It is not:

- a new coding-agent instruction format;
- a replacement for `AGENTS.md`, Agent Skills, OpenSpec, Spec Kit, ADRs, RFCs, or a project's established workflow;
- a security audit, penetration test, formal proof, or certification;
- a claim that an adopting project is secure, bug-free, complete, or fit for every environment;
- a public vulnerability ledger;
- a reason to publish secrets, exploitable attack paths, sensitive topology, personal data, or unpatched findings.

**For an active adoption, conformance means that promises, controls, evidence, and remaining doubt are represented according to the adopted profile. For exclusive `archived`, it means that reference-only eligibility and the four required historical facts are represented and owner-confirmed—not that current operational assurance exists. Neither means “no vulnerabilities exist.”**

---

## Relationship to existing practices

This profile is intentionally a thin coordination layer rather than a replacement ecosystem.

| Existing mechanism | Role |
|---|---|
| `AGENTS.md` | Persistent instructions and reading order for coding agents |
| Agent Skills / `SKILL.md` | Reusable task-specific procedures |
| OpenSpec, Spec Kit, ADR, RFC, or equivalent | Change specification and decision workflow |
| Tests, schemas, constraints, scanners, CI | Enforcement and verification mechanisms |
| `SECURITY.md` and GitHub private vulnerability reporting | Confidential vulnerability intake and coordinated disclosure |
| OpenSSF Security Insights | Machine-readable public description of security practices and posture |
| This profile | Traceability among intent, claims, invariants, evidence, defeaters, and residuals |

An adopting project should reuse what it already has. The profile should not create a parallel document system merely to rename existing artifacts.

---

## Public repository safety

### The central rule

> **Public assurance is a sanitized projection of project knowledge, not the project's complete private security record.**

Applying this profile to a public repository does not require publishing actionable weaknesses. Public transparency and responsible vulnerability handling are separate obligations.

### Two-ledger model

Use two logically separate records:

1. **Public assurance view** — safe for the repository and its users.
2. **Restricted security record** — maintained through private security advisories, a private tracker, or another access-controlled system.

| Generally safe to publish | Keep restricted while actionable or sensitive |
|---|---|
| Product purpose and explicit non-goals | Secrets, tokens, keys, credentials, or personal data |
| High-level trust boundaries | Internal hostnames, privileged topology, or access paths that materially reduce attack cost |
| Stable claim and invariant statements | Reproduction steps or proof-of-concept for an unpatched vulnerability |
| Non-sensitive control categories | Exact bypass conditions for an active control gap |
| Test names and reproducible public checks | Sensitive logs, production snapshots, private evidence, or user records |
| Sanitized evidence status | Embargoed findings and affected-version analysis before coordinated disclosure |
| Publicly acceptable limitations | Residuals whose details reveal an immediately exploitable weakness |
| Published advisories after coordination | Private reporter identity or confidential correspondence |

When uncertain, route the report privately first. It can be sanitized and published later; information committed publicly cannot be made meaningfully private by deleting the latest version.

### Disclosure classes

Projects may classify assurance material as:

- `PUBLIC` — full detail may be committed publicly;
- `SUMMARY_ONLY` — publish only a non-actionable statement and status;
- `RESTRICTED` — do not commit the material to a public repository;
- `EMBARGOED` — hold privately until a fix and coordinated disclosure decision.

The public profile may state that a control or evidence obligation is under restricted review, but it should not reveal the attack path. Even that status should be omitted when disclosure would itself create material risk.

### Security reporting

Every public adopting repository should:

1. include a `SECURITY.md`;
2. enable GitHub **Private Vulnerability Reporting** where available;
3. direct suspected exploitable vulnerabilities away from public Issues;
4. use a draft GitHub Security Advisory or another private channel for triage, reproduction, remediation, and coordinated disclosure;
5. publish only a sanitized profile update after the issue is fixed or disclosure is otherwise approved.

See [SECURITY.md](SECURITY.md) and [Disclosure and issue model](docs/DISCLOSURE-AND-ISSUES.md).

---

## Profile documents and GitHub Issues

The division of responsibility is simple:

> **Profile artifacts describe durable project state. Issues track work required to change or clarify that state.**

| GitHub object or repository artifact | Function |
|---|---|
| `PROFILE.md` | Generic normative obligations of this profile |
| Local claims, invariants, and residuals | Current project truth and accepted uncertainty |
| GitHub Issue | Proposal, question, non-sensitive gap, or work item |
| Pull Request | Reviewable change to implementation and/or profile artifacts |
| CI and evidence artifact | Reproducible support for a claim or invariant |
| GitHub Security Advisory | Confidential handling of an exploitable or sensitive vulnerability |
| Release/tag | Versioned snapshot of code, profile pin, evidence, and residual state |

### Stable IDs, not issue numbers, define meaning

Profile requirements and local assurance items should have stable IDs, for example:

```text
AAP-CORE-004
CLAIM-IDENTITY-002
INV-AUTH-007
RES-DATA-003
```

Issues and pull requests reference those IDs. The IDs must not be derived from GitHub issue numbers, because issues may be moved, closed, duplicated, or split while the assurance item remains part of the system's history.

Example issue field:

```markdown
## Affected assurance IDs

- AAP-CORE-004
- INV-AUTH-007
- RES-DATA-003
```

### Issue closure is not assurance resolution

Merging code or closing an Issue is insufficient by itself. A change is complete only when the applicable durable artifacts are updated:

```text
Issue or change proposal
  → Pull Request
  → implementation / control update
  → deterministic verification
  → independent contradiction search when required
  → evidence bound to revision or deployment
  → claims / invariants / residuals updated
  → Issue closed
```

A pull request may use `Closes #123` only when merging it actually completes the issue's declared acceptance criteria, including required profile and evidence updates. Otherwise use a non-closing reference such as `Related to #123`.

### Where an Issue belongs

| Topic | Correct location |
|---|---|
| Generic profile wording, schema, terminology, or compatibility | This central profile repository |
| Project-specific adoption, conformance gap, domain invariant, or evidence work | The adopting project's repository |
| Exploitable or potentially exploitable security finding | Private vulnerability report / draft Security Advisory |
| General security hardening with no sensitive exploit detail | Public project Issue, if disclosure is safe |
| Published vulnerability after remediation | Public advisory and sanitized documentation/Issue references |

See [Disclosure and issue model](docs/DISCLOSURE-AND-ISSUES.md) for the complete routing rules.

---

## Adoption model

**Adoption begins by classifying the profile, not by copying files.** Which active profiles apply — or whether the exclusive `archived` profile applies instead — is a finding about what the repository *is and promises*, determined from evidence before any file is written ([docs/ADOPTION.md §4.0](docs/ADOPTION.md)). Every specialized active profile inherits the `core` obligations: for an active adopter, declare `[core]` when none applies; otherwise canonically list the fired specialized profiles without `core`. The layout follows from that classification — never from the repository's size.

At `core` alone, adoption has four required profile files, and `specification_workflow.root` must point at a material-change workflow entry document that actually exists — normally an existing `CONTRIBUTING`, ADR, or spec file, so only a repository that has none writes a fifth. The lite layout, declared with `layout: lite` in `adoption.yaml`, concentrates purpose, non-goals, at least one invariant, at least one residual, and normally the system description in a single `assurance.yaml`; the system description may instead be supplied by a recorded mapping to an existing artifact:

```text
AGENTS.md
AGENTIC_ASSURANCE.md
.agentic-assurance/
├── adoption.yaml
└── assurance.yaml
```

For any specialized active profile (or at `core` by preference), the split layout gives each active register its own file:

```text
AGENTS.md
AGENTIC_ASSURANCE.md
.agentic-assurance/
└── adoption.yaml
assurance/
├── SYSTEM.md
├── INVARIANTS.yaml
└── RESIDUALS.yaml
```

`archived` also uses split-path conventions, but it does not inherit active-register obligations: its assurance minimum is the system artifact containing the four §6.6 historical facts, alongside the root adoption and agent-instruction files.

Additional artifacts are introduced only when applicable:

```text
assurance/
├── CLAIMS.yaml
├── DEFEATERS.yaml
├── THREAT_MODEL.md
├── decisions/
├── reviews/
└── evidence/
```

The upstream profile must be pinned by version and full commit SHA. An adopting agent must not silently follow a floating `main` branch or copy and modify the profile as an untracked local fork.

### Suggested profiles

| Profile | Intended use |
|---|---|
| `core` | Any repository substantially produced or maintained by AI agents |
| `service` | Deployed website, API, worker, stateful backend, or operational service |
| `trust-critical` | Identity, authorization, privacy, security, financial, governance, or public-verifiability claims |
| `data-curation` | Externally sourced, editorial, scored, classified, or recommended data |
| `agent-runtime` | Model-driven agents or workflows operating in production |
| `archived` | Repositories retained solely for historical reference, not supported or intended for current use, with no active operation, functional maintenance, or feature development |

`service`, `trust-critical`, `data-curation`, and `agent-runtime` inherit all `core` obligations even when `core` is omitted from `profiles:`. `archived` is declared alone and records its four required historical facts in the system artifact mapped by `paths.system` (default `assurance/SYSTEM.md`). That artifact must be non-empty at every stage; from `HUMAN_REVIEWED`, none of the four exact shipped archived prompt markers may remain.

### Brownfield adoption sequence

For an existing repository, start here and continue through step 8 only if classification confirms an active profile:

1. classify the profile from what the repository is and promises — collect any `service` / `trust-critical` / `data-curation` / `agent-runtime` trigger with `file:line` evidence and declare `[core]` only when none fires and the `archived` criteria do not apply; if the evidence instead supports `archived`, stop and use the short path below ([§4.0](docs/ADOPTION.md));
2. inspect existing specifications, tests, workflows, policies, and release controls;
3. reconstruct the as-built system without changing functional code;
4. classify conclusions as `VERIFIED`, `INFERRED`, `UNKNOWN`, or `CONTRADICTED`;
5. obtain human review of purpose and non-goals; critical claims and invariants; behavior classified as `INTENDED`, `ACCIDENTAL`, `COMPATIBILITY`, `UNKNOWN`, or `DEPRECATED`; critical residuals; and public-claim limitations;
6. record conformance gaps and residuals;
7. remediate through separate, scoped Issues and pull requests;
8. bind evidence to a commit, artifact digest, release, or deployment identifier.

For a candidate `archived` repository, use this narrower path instead:

1. collect evidence that the repository is retained solely for historical reference, is not supported or intended for current use, and has no active operation, functional maintenance, or feature development;
2. declare `[archived]` alone and record all four §6.6 facts in the system artifact mapped by `paths.system`: that reference-only and inactive status; historical purpose; known material limitations; and the last supported revision or release (or explicitly that none exists);
3. obtain the human owner's confirmation of the archived eligibility, the artifact mapping, and each of the four facts using [docs/REVIEW-GUIDE.md](docs/REVIEW-GUIDE.md).

The active path's as-built reconstruction, behavior classification, active claim/invariant/residual registers, and remediation plan do not apply to an `archived` adoption. Do not create empty active artifacts as stand-ins.

Initial adoption, factual corrections, and upkeep of the pin, stage, review record, or agent-instruction metadata do not by themselves count as functional maintenance. Changing code, dependencies, or behavior to support current use does; reclassify under the applicable active profiles before that work.

Creating the files alone is not adoption.

**If you are an AI agent told to "apply this profile" to a repository** — even from a bare prompt with nothing but this link — do not begin by copying templates. First: (1) **pin** this profile at its latest release commit (a floating `main` is not a valid pin — see [Versioning](#versioning)); (2) **classify** the target repository's profile from what it is and promises ([§4.0](docs/ADOPTION.md)), declaring `[core]` only for an active classification with no specialized trigger and selecting `archived` only as an exclusive alternative when evidence establishes the full reference-only eligibility above; (3) then follow the applicable active or archived brownfield path in [docs/ADOPTION.md §4](docs/ADOPTION.md), declare the classified set in `adoption.yaml`'s `profiles:` field, and hand the result to the human owner on a branch — without merging. The [§0 kick-off prompt](docs/ADOPTION.md) is the fuller form of this instruction; use it when you can, but the steps above hold even when all you were given is this link.

See [docs/ADOPTION.md](docs/ADOPTION.md) for the practical adoption guide, and [docs/MAPPINGS.md](docs/MAPPINGS.md) for mapping existing repository conventions onto profile artifacts instead of creating parallel files. Tasking an AI agent with adoption? Give it the kick-off prompt in [docs/ADOPTION.md §0](docs/ADOPTION.md) instead of a bare "apply the profile". Owners reviewing an adoption start at [docs/REVIEW-GUIDE.md](docs/REVIEW-GUIDE.md); unfamiliar terms are defined in [docs/GLOSSARY.md](docs/GLOSSARY.md).

---

## Repository layout

Layout of this central repository:

```text
.
├── .github/
│   ├── CODEOWNERS
│   ├── ISSUE_TEMPLATE/
│   │   ├── adoption-question.yml
│   │   ├── clarification.yml
│   │   ├── config.yml
│   │   ├── profile-change.yml
│   │   └── tooling-defect.yml
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── workflows/
│       ├── adopter-validate.yml
│       └── self-check.yml
├── .gitignore
├── CHANGELOG.md
├── CONTRIBUTING.md
├── GOVERNANCE.md
├── LICENSE                  (Apache-2.0)
├── LICENSE-docs             (CC-BY-4.0)
├── PROFILE.md
├── README.ko.md
├── README.md
├── RELEASING.md
├── SECURITY.md
├── VERSION
├── docs/
│   ├── ADOPTION.md
│   ├── DISCLOSURE-AND-ISSUES.md
│   ├── GLOSSARY.md
│   ├── MAPPINGS.md
│   └── REVIEW-GUIDE.md
├── schemas/
│   ├── adoption.schema.json
│   ├── assurance-lite.schema.json
│   ├── claims.schema.json
│   ├── defeaters.schema.json
│   ├── invariants.schema.json
│   └── residuals.schema.json
├── scripts/
│   └── validate.py
└── templates/
    ├── AGENTIC_ASSURANCE.md
    ├── AGENTS.md
    ├── CLAIMS.yaml
    ├── DEFEATERS.yaml
    ├── INVARIANTS.yaml
    ├── LICENSE              (CC0-1.0)
    ├── RESIDUALS.yaml
    ├── SYSTEM.md
    ├── THREAT_MODEL.md
    ├── adoption.yaml
    ├── assurance.minimal.yaml
    ├── assurance.yaml
    └── github/
        ├── CODEOWNERS
        ├── ISSUE_TEMPLATE/
        │   ├── bug.yml
        │   ├── config.yml
        │   ├── conformance-gap.yml
        │   ├── evidence-gap.yml
        │   ├── feature.yml
        │   └── residual-review.yml
        └── PULL_REQUEST_TEMPLATE.md
```

---

## Versioning

The profile should use semantic versioning and publish tagged releases.

- **Major:** removes, weakens, or materially changes an obligation.
- **Minor:** adds backward-compatible requirements, profiles, or fields.
- **Patch:** clarifies wording or fixes schemas without changing intended obligations.

Before `v1.0.0` the profile is under active development. Under this project's governing interpretation of semantic versioning's initial-development latitude, adding or tightening an obligation is a minor change (and may require new content from a previously conforming adoption), called out in the changelog with its adopter impact. This is the profile's stated `0.x` operating policy, not a universal SemVer rule. From `v1.0.0`, materially changing an obligation is major.

Adopting repositories pin both the human-readable version and the exact commit SHA. Upgrades are explicit project changes with impact review.

The release process is defined in [RELEASING.md](RELEASING.md). The root `VERSION` file records the repository's release state: `unreleased` before the first release, the exact tag string on a release commit, and a `-dev` suffix between releases. Adopters pin only commits whose `VERSION` matches their declared version.

---

## Contributing

Use public Issues for:

- profile clarification;
- non-sensitive schema or validator defects;
- compatibility with an existing workflow;
- proposals that do not expose an active vulnerability;
- documentation improvements.

Do not use public Issues for suspected exploitable vulnerabilities. Follow [SECURITY.md](SECURITY.md).

Pull requests should identify:

- affected profile IDs;
- behavioral and compatibility impact;
- evidence added or changed;
- new, resolved, or modified residuals;
- disclosure classification;
- the Issue or advisory they address.

Decision authority and approval rules for changes to the normative text, schemas, and templates are defined in [GOVERNANCE.md](GOVERNANCE.md).

---

## Design principle

The profile does not ask a project to claim that its uncertainty is zero.

It asks the project to state, for a specific revision or release:

- what it intends;
- what it claims;
- what prevents violation;
- what evidence exists;
- what could still defeat the claim;
- where the remaining uncertainty stops.

That boundary is the assurance artifact.

---

## License

This repository uses three licenses, split by path:

| File | License | Covers |
|---|---|---|
| [LICENSE](LICENSE) | Apache-2.0 | `schemas/`, `scripts/`, `.github/` workflows, and any future validator or tooling code |
| [LICENSE-docs](LICENSE-docs) | CC-BY-4.0 | `PROFILE.md`, `README.md`, `README.ko.md`, `docs/`, `SECURITY.md`, and all other prose |
| [templates/LICENSE](templates/LICENSE) | CC0-1.0 | Everything under `templates/` |

Code is licensed under Apache-2.0 so that the schemas, validator, and workflow automation can be reused under a standard, patent-aware code license. Prose is licensed under CC-BY-4.0 so that the profile text and documentation can be shared and adapted with attribution. Templates are dedicated to the public domain under CC0-1.0 so that copying them into adopting repositories carries no attribution obligation.
