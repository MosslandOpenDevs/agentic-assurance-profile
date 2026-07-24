# OpenDevs Agentic Assurance Profile

> A lightweight, evidence-oriented adoption profile for software substantially built or maintained by AI coding agents.

**Status:** Released — current release on the [releases page](https://github.com/MosslandOpenDevs/agentic-assurance-profile/releases)  
**Repository:** `MosslandOpenDevs/agentic-assurance-profile`  
**Current maturity:** reference profile, not a certification scheme

> **Normative status:** [PROFILE.md](PROFILE.md) is the normative text. This README and all translations are informative summaries; where they disagree, PROFILE.md governs.

Code generation is cheap; the reasoning around it is not. This profile keeps that reasoning as durable, inspectable repository artifacts:

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

**Told to "apply this profile" to a repository (human or AI agent)?** Go to [Adopting the profile](#adopting-the-profile-for-an-ai-agent-or-a-human).

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

This profile descends from a question Donald Knuth answered for an earlier era. *TeX: The Program* treated a program as something to be explained to people, not merely executed: the reasoning, the invariants, and the argument for correctness were part of the work itself. AI coding agents invert the economics that once made that discipline optional. Implementation is now cheap. Design rationale, invariants, evidence, and known limitations are not — and they are what a project loses when code outpaces the record of intent.

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

Neighboring tool categories answer different questions. A specification workflow records what a change is meant to do. An analysis or code-review tool finds risk in the code as written. A provenance tool records what an agent actually did. This profile asks the question left over: **do the promises a human approved, and the risk that human accepted, still hold after the change?** Answering it needs artifacts that outlive any single change. That is why the unit is the repository, not the pull request — and why the profile consumes other tools' output as evidence rather than reproducing it.

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
| OpenSpec, Spec Kit, Kiro, ADR, RFC, or equivalent | Change specification and decision workflow |
| Tests, schemas, constraints, scanners, code-review tools, CI | Enforcement and verification mechanisms |
| Agent change records and session logs | Provenance of what an agent read, ran, and changed |
| SLSA, in-toto, or equivalent attestations | Build and artifact provenance for a release |
| `SECURITY.md` and GitHub private vulnerability reporting | Confidential vulnerability intake and coordinated disclosure |
| OpenSSF Security Insights | Machine-readable public description of security practices and posture |
| This profile | Traceability among intent, claims, invariants, evidence, defeaters, and residuals |

An adopting project should reuse what it already has. The profile should not create a parallel document system merely to rename existing artifacts.

Where a mechanism above produces output, the profile references that output rather than regenerating it: a specification workflow supplies intent and change scope, verification tooling and attestations supply evidence, review findings supply defeater candidates. [docs/MAPPINGS.md §5](docs/MAPPINGS.md) shows how to reference that output from the registers without overstating what it proves. Some parts no tool supplies: intent, claim wording, defeater disposition, and residual acceptance stay human decisions ([PROFILE.md §3](PROFILE.md)).

---

## Public repository safety

> **Public assurance is a sanitized projection of project knowledge, not the project's complete private security record.**

Applying this profile to a public repository does not require publishing actionable weaknesses: public transparency and responsible vulnerability handling are separate obligations. Keep a **two-ledger** split — a public assurance view (safe for the repo and its users) and a restricted security record (private advisory or another access-controlled system) for anything still actionable or sensitive. Safe-to-publish material includes product purpose and non-goals, high-level trust boundaries, stable claims and invariants, and sanitized evidence status; secrets, privileged topology, unpatched reproduction steps, and reporter identity stay restricted. When uncertain, route privately first — content committed publicly cannot be made meaningfully private by deleting the latest version.

Assurance material carries a disclosure class — `PUBLIC`, `SUMMARY_ONLY`, `RESTRICTED`, or `EMBARGOED` (defined in [PROFILE.md §13](PROFILE.md) and [docs/GLOSSARY.md](docs/GLOSSARY.md)). A control may be published as "under restricted review" only when that status does not itself reveal the attack path; omit even the status when disclosure would create material risk.

**Security reporting** — every public adopting repository must ship a `SECURITY.md`, enable GitHub **Private Vulnerability Reporting**, route suspected exploitable vulnerabilities away from public Issues into a draft Security Advisory for triage and coordinated disclosure, and publish only a sanitized profile update after a fix or disclosure is approved.

See [SECURITY.md](SECURITY.md) and [Disclosure and issue model](docs/DISCLOSURE-AND-ISSUES.md) for the security-reporting lifecycle and how disclosure classes route through issues and advisories.

---

## Profile documents and GitHub Issues

The division of responsibility is simple:

> **Profile artifacts describe durable project state. Issues track work required to change or clarify that state.**

`PROFILE.md` plus the local claims, invariants, and residuals are the durable truth; Issues, pull requests, CI evidence, Security Advisories, and release tags are the work and evidence that move that state. Closing an Issue or merging a pull request does **not** by itself resolve an assurance item — a change lands only when the durable artifacts (claims, invariants, residuals) and their evidence are updated too.

Profile requirements and local assurance items carry stable IDs (`AAP-CORE-004`, `CLAIM-IDENTITY-002`, `INV-AUTH-007`, `RES-DATA-003`). Issues and pull requests reference those IDs; the IDs are never derived from GitHub issue numbers, which may be moved, closed, duplicated, or split while the assurance item persists. Each relevant Issue and PR states its affected IDs:

```markdown
## Affected assurance IDs

- AAP-CORE-004
- INV-AUTH-007
- RES-DATA-003
```

The full state/work model, the stable-ID namespaces, the Issue/PR routing (central profile vs. adopting project vs. private security report), `Closes #` vs. `Related to #` rules, and the closure-vs-resolution lifecycle are in [docs/DISCLOSURE-AND-ISSUES.md](docs/DISCLOSURE-AND-ISSUES.md).

---

## Adopting the profile (for an AI agent or a human)

Adoption begins by **classifying the profile, not by copying files** — the applicable profile set is a *finding* about what the repository is and promises, determined from evidence before any file is written, and it sizes everything downstream. Layout follows from that classification, never from repository size: a confirmed `core`-only repository may use the `layout: lite` single-`assurance.yaml` form, while any specialized active profile — or the exclusive `archived` profile — uses the split layout with one file per register. The upstream profile is pinned by version and full commit SHA — never a floating `main`, never a copy-modified untracked local fork. Creating the files alone is not adoption; it ends with a human decision, not a merge.

**If you were told to "apply this profile" to a repository — even from a bare prompt with nothing but this link — do not begin by copying templates.** First confirm a **named human owner or governing body exists** ([docs/ADOPTION.md §1](docs/ADOPTION.md)); adoption cannot proceed without one. Then:

1. **Pin** this profile by both version *and* full 40-character commit SHA. A floating `main` is not a valid pin ([Versioning](#versioning), [docs/ADOPTION.md §2](docs/ADOPTION.md)).
2. **Classify** the target from what it *is and promises*, never from its size ([docs/ADOPTION.md §4.0](docs/ADOPTION.md); the triggers and suggested profile set are in [PROFILE.md §5](PROFILE.md)). Bias toward escalation. Declare `[core]` only for an active repository where no specialized trigger fires; select `archived` only as an exclusive alternative when evidence establishes full reference-only eligibility. Write the set into `adoption.yaml`'s enforced `profiles:` field — not only the handoff prose.
3. **Follow** the applicable path in [docs/ADOPTION.md §4](docs/ADOPTION.md): the active path is read-only reconstruction (§4.1) and behavior classification (§4.2) **without changing functional code**, then the §4.3 review items and §4.4 staged remediation; the `archived` path is the narrower §4.1/§4.3 branch that records the four §6.6 historical facts.
4. *(optional)* Before handoff, run the [§3.6.1 `aap check` pre-flight](docs/ADOPTION.md) (or full §3.6 validation) from your pinned checkout to catch structural gaps early — `python3 scripts/aap.py check --project-root /path/to/your/repo` (exit `0` pass / `1` findings / `2` setup / `3` internal). It is a convenience self-check, **not the gate of record and not owner approval**; the reusable workflow remains the enforced gate.
5. **Hand off** on a branch as a draft pull request — **do not merge.** Merging is the human owner's act after the §4.3 review. Close with a summary in the owner's working language stating that nothing is decided yet and listing each decision the owner must make ([docs/REVIEW-GUIDE.md](docs/REVIEW-GUIDE.md)); never describe the draft as settled, complete, or done.

The [§0 kick-off prompt](docs/ADOPTION.md) is the fuller form of this instruction — give an agent that prompt rather than a bare "apply the profile"; the steps above hold even when all you were given is this link. Map existing repository conventions onto profile artifacts via [docs/MAPPINGS.md](docs/MAPPINGS.md) instead of creating parallel files. Owners reviewing a draft start at [docs/REVIEW-GUIDE.md](docs/REVIEW-GUIDE.md); unfamiliar terms are in [docs/GLOSSARY.md](docs/GLOSSARY.md).

---

## Repository layout

Top-level layout of this central repository:

```text
.
├── PROFILE.md        # sole normative text — the obligations this profile governs
├── README.md         # this overview (README.ko.md is the Korean translation)
├── schemas/          # JSON Schemas for the adopter YAML artifacts (claims, defeaters, invariants, residuals, adoption)
├── scripts/          # validate.py — the `aap` validator (see docs/ADOPTION.md §3.6)
├── templates/        # files an adopter copies into their repo (assurance YAML, AGENTS.md, github/ scaffolding, …)
├── docs/             # informative guides: ADOPTION.md, DISCLOSURE-AND-ISSUES.md, GLOSSARY.md, REVIEW-GUIDE.md, MAPPINGS.md
└── .github/          # this repo's own CODEOWNERS, issue/PR templates, and CI workflows
```

Root also holds the usual governance files (CHANGELOG, CONTRIBUTING, GOVERNANCE, RELEASING, SECURITY, VERSION). For the full contents of `templates/` and what to copy where, see [docs/ADOPTION.md](docs/ADOPTION.md).

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

The proposed development direction is recorded in the non-normative [v0.5 working design and delivery plan](docs/V0.5-DESIGN.md).

Use public Issues for profile clarification, non-sensitive schema or validator defects, workflow-compatibility questions, documentation improvements, and proposals that expose no active vulnerability. **Do not** use public Issues for suspected exploitable vulnerabilities — follow [SECURITY.md](SECURITY.md).

A pull request should identify: affected profile IDs; behavioral and compatibility impact; evidence added or changed; new, resolved, or modified residuals; disclosure classification; and the Issue or advisory it addresses.

Decision authority and approval rules for the normative text, schemas, and templates are defined in [GOVERNANCE.md](GOVERNANCE.md).

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

Code uses Apache-2.0 so the schemas, validator, and workflow automation are reusable under a standard, patent-aware license. Prose uses CC-BY-4.0 so it can be shared and adapted with attribution. Templates use CC0-1.0 so copying them into adopting repositories carries no attribution obligation.
