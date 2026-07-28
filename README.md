# OpenDevs Agentic Assurance Profile

> A lightweight, evidence-oriented adoption profile for software substantially built or maintained by AI coding agents.

**Status:** Released — current release on the [releases page](https://github.com/MosslandOpenDevs/agentic-assurance-profile/releases)<br>
**Repository:** `MosslandOpenDevs/agentic-assurance-profile`<br>
**Current maturity:** reference profile, not a certification scheme

> **Normative status:** [PROFILE.md](PROFILE.md) is the normative text. This README and all translations are informative summaries; where they disagree, PROFILE.md governs.

Code generation is cheap; the reasoning around it is not. The OpenDevs
Agentic Assurance Profile (AAP) keeps intent, claims, invariants, enforcement,
evidence, defeaters, residual risk, and human decisions as durable,
inspectable repository artifacts.

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

**Start here:** [adopt AAP](#adopting-the-profile-for-an-ai-agent-or-a-human)
· [review an adoption draft](docs/REVIEW-GUIDE.md)
· [use the three-layer baseline without AAP](docs/CODING-AGENT-BASELINE.md)
· [report a vulnerability](SECURITY.md)

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

The objective is not to eliminate all uncertainty. It is to make the boundary
between demonstrated properties and remaining doubt inspectable. That boundary
is the assurance artifact.

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

## Origins

AAP draws on the literate-programming idea exemplified by Donald Knuth's
*TeX: The Program*: reasoning, invariants, and the argument for correctness
are part of the work, not merely commentary on executable code. AI coding
agents change the economics—implementation is cheap; durable rationale,
evidence, and known limitations are not.

The practical catalyst was [Passport](https://passport.moss.land), a Mossland
project built almost entirely by AI coding agents without a conventional code
editor. It made the owner's changing role concrete: from writing code to
governing claims, invariants, evidence, and residual risk. AAP gives that
governance a durable, inspectable form.

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

Reuse existing artifacts instead of creating a parallel document system. AAP
references their output rather than regenerating it: specifications supply
intent and scope; verification and attestations supply evidence; review
findings supply defeater candidates. Intent, claim wording, defeater
disposition, and residual acceptance remain human decisions
([PROFILE.md §3](PROFILE.md#3-authority)). [docs/MAPPINGS.md §5](docs/MAPPINGS.md#5-mapping-external-tool-output-into-the-evidence-position) shows
how to map existing output without overstating what it proves.

---

## A three-layer starting pattern—even without AAP

> **Informative scope:** This model- and tool-neutral pattern can be used
> without AAP. It neither establishes AAP adoption or conformance nor proves
> security or correctness, and it does not replace a complete engineering or
> security program.

| Layer | Role |
|---|---|
| Persistent agent instructions | Point agents to canonical contracts, commands, authority boundaries, and stop conditions. |
| Durable contract records | State the authorized, scoped, falsifiable contract and its known gaps. |
| Controls, verification, and gates | Controls prevent violations; verification checks them; gates block unacceptable changes; evidence names the bounded subject it supports. |

The [detailed guide](docs/CODING-AGENT-BASELINE.md) provides concrete
procedures and examples. Reuse equivalent existing artifacts; an AAP adopter
maps them into its applicable AAP records instead of duplicating them.

---

## Public repository safety

> **Public assurance is a sanitized projection of project knowledge, not the project's complete private security record.**

Public transparency and responsible vulnerability handling are separate
obligations. Keep a **two-ledger** split: a public assurance view for sanitized
project state, and an access-controlled security record for actionable or
sensitive material. Purpose, non-goals, high-level trust boundaries, stable
claims and invariants, and sanitized evidence status may be public. Secrets,
privileged topology, unpatched reproduction steps, private evidence, and
reporter identity stay restricted. When uncertain, route privately first;
deleting a later revision cannot make committed information private.

Assurance material should carry a disclosure class: `PUBLIC`, `SUMMARY_ONLY`,
`RESTRICTED`, or `EMBARGOED` ([PROFILE.md §13](PROFILE.md#13-public-and-restricted-disclosure),
[docs/GLOSSARY.md](docs/GLOSSARY.md)). A control may be described as "under
restricted review" only when even that status does not reveal the attack path.

**Security reporting:** suspected exploitable findings must go through the
repository's private security process, never a public Issue. Before assurance
artifacts are published, a public adopter should provide a `SECURITY.md` and
GitHub **Private Vulnerability Reporting** or an equivalent restricted channel.
Public `trust-critical` adopters are required to maintain private
vulnerability-reporting and disclosure procedures. After remediation and
coordinated disclosure, the public profile may be updated with a sanitized
summary.

See [SECURITY.md](SECURITY.md) and [Disclosure and issue model](docs/DISCLOSURE-AND-ISSUES.md) for the security-reporting lifecycle and how disclosure classes route through issues and advisories.

---

## Profile documents and GitHub Issues

The division of responsibility is simple:

> **Profile artifacts describe durable project state. Issues track work required to change or clarify that state.**

`PROFILE.md` defines the profile; an adopter's system, claims, invariants,
defeaters, and residuals record durable project state. Issues, pull requests,
CI evidence, Security Advisories, and release tags are the work and evidence
that move that state. Closing an Issue or merging a pull request does **not**
by itself resolve an assurance item: all affected durable artifacts and their
evidence must be updated too.

Profile requirements and local assurance items use stable semantic IDs such
as `AAP-CORE-004`, `CLAIM-IDENTITY-002`, `INV-AUTH-007`, and `RES-DATA-003`.
Material Issues and pull requests should reference their affected IDs. The IDs
are never derived from GitHub issue numbers, which may be moved, closed,
duplicated, or split while the assurance item persists.

The full state/work model, the stable-ID namespaces, the Issue/PR routing (central profile vs. adopting project vs. private security report), `Closes #` vs. `Related to #` rules, and the closure-vs-resolution lifecycle are in [docs/DISCLOSURE-AND-ISSUES.md](docs/DISCLOSURE-AND-ISSUES.md).

---

## Adopting the profile (for an AI agent or a human)

Adoption begins by **classifying the profile, not by copying files**. The
applicable set is an evidence-based finding about what the repository is and
promises. Layout follows that classification, not repository size: confirmed
`core`-only projects may use the `layout: lite` single-`assurance.yaml` form;
specialized active profiles and the exclusive `archived` profile use the split
layout. Files alone do not constitute adoption; a human owner decides.

The recommended low-friction path is
[Minimum Effective Adoption](docs/ADOPTION.md#11-minimum-effective-adoption-agent-led-with-two-human-decision-touchpoints).
The agent prepares the reconstruction, evidence, artifacts, and validation;
the human normally confirms scope and reviews one consolidated decision
packet. `DRAFT` is a scaffold, `HUMAN_REVIEWED` is the normal first
destination, and `CONFORMANT` is pursued only when the project needs that
claim. “Effective,” the initial target size, and the interaction budget remain
pilot hypotheses, not measured outcome claims.
MEA is informative, not a new stage or lighter profile: it narrows the initial
slice, never the applicable obligations, and `HUMAN_REVIEWED` is not a
conformance claim.

**If you were told to "apply this profile" to a repository — even from a bare prompt with nothing but this link — do not begin by copying templates.** First confirm a **named human owner or governing body exists** ([docs/ADOPTION.md §1](docs/ADOPTION.md#1-prerequisites)); adoption cannot proceed without one. Then:

1. **Resolve the pin without writing adopter files:** identify both the version and full 40-character commit SHA. For a release, use its tagged commit and confirm that `VERSION` matches. Record both when the adoption artifacts are created; a floating `main` is not valid ([Versioning](#versioning), [docs/ADOPTION.md §2](docs/ADOPTION.md#2-pinning-version-and-commit)).
2. **Classify** the target from what it *is and promises*, never from its size ([docs/ADOPTION.md §4.0](docs/ADOPTION.md#40-classify-the-profile-first); the triggers and suggested profile set are in [PROFILE.md §5](PROFILE.md#5-adoption-profiles)). When trigger evidence is genuine but ambiguous in degree, bias toward escalation. Declare `[core]` only for an active repository where no specialized trigger fires; select `archived` only as an exclusive alternative when evidence establishes full reference-only eligibility. Write the set into `adoption.yaml`'s enforced `profiles:` field — not only the handoff prose.
3. **Follow** the applicable path in [docs/ADOPTION.md §4](docs/ADOPTION.md#4-brownfield-adoption): the active path is read-only reconstruction (§4.1) and behavior classification (§4.2) **without changing functional code**, then the §4.3 review items and §4.4 staged remediation; the `archived` path is the narrower §4.1/§4.3 branch that records the four §6.6 historical facts.
4. *(optional)* Before handoff, run the [§3.6.1 `aap check` pre-flight](docs/ADOPTION.md#361-convenience-pre-flight-aap-check-alpha) from the pinned checkout to catch structural gaps early: `python3 scripts/aap.py check --project-root /path/to/your/repo`. It is a convenience self-check, **not the gate of record and not owner approval**; the reusable workflow remains the enforced gate.
5. **Hand off** on a branch as a draft pull request — **do not merge.** Merging is the human owner's act after the §4.3 review. Close with a summary in the owner's working language stating that nothing is decided yet and listing each decision the owner must make ([docs/REVIEW-GUIDE.md](docs/REVIEW-GUIDE.md)); never describe the draft as settled, complete, or done.

The [§0 kick-off prompt](docs/ADOPTION.md#0-quick-start-for-ai-agents) is the fuller form of this instruction — give an agent that prompt rather than a bare "apply the profile"; the steps above hold even when all you were given is this link. Map existing repository conventions onto profile artifacts via [docs/MAPPINGS.md](docs/MAPPINGS.md) instead of creating parallel files. Owners reviewing a draft start at [docs/REVIEW-GUIDE.md](docs/REVIEW-GUIDE.md); unfamiliar terms are in [docs/GLOSSARY.md](docs/GLOSSARY.md).

---

## Repository layout

Top-level layout of this central repository:

```text
.
├── PROFILE.md        # sole normative text — the obligations this profile governs
├── README.md         # this overview (README.ko.md is the Korean translation)
├── schemas/          # JSON Schemas for adopter artifacts
├── scripts/          # aap.py entry point and validate.py validation engine
├── templates/        # adopter files and GitHub scaffolding
├── docs/             # adoption, review, mapping, and baseline guides
└── .github/          # this repo's own CODEOWNERS, issue/PR templates, and CI workflows
```

Root also holds the usual governance files (CHANGELOG, CONTRIBUTING, GOVERNANCE, RELEASING, SECURITY, VERSION). For the full contents of `templates/` and what to copy where, see [docs/ADOPTION.md](docs/ADOPTION.md).

---

## Versioning

The profile uses semantic versioning and publishes tagged releases.

- **Major:** removes, weakens, or materially changes an obligation.
- **Minor:** adds backward-compatible requirements, profiles, or fields.
- **Patch:** clarifies wording or fixes schemas without changing intended obligations.

Before `v1.0.0`, adding or tightening an obligation is minor and is called out
in the changelog with its adopter impact. This is the project's stated `0.x`
policy, not a universal SemVer rule. From `v1.0.0`, materially changing an
obligation is major.

Adopting repositories pin both the human-readable version and the exact commit SHA. Upgrades are explicit project changes with impact review.

The release process is defined in [RELEASING.md](RELEASING.md). The root `VERSION` file records the repository's release state: `unreleased` before the first release, the exact tag string on a release commit, and a `-dev` suffix between releases. Adopters pin only commits whose `VERSION` matches their declared version.

---

## Contributing

The [v0.5 working design](docs/V0.5-DESIGN.md) is a frozen historical record.
The accepted, non-normative [v0.5.1 closeout](docs/V0.5.1-CLOSEOUT.md)
scope-freezes the v0.5 architecture and diagnostic-expansion track, centers
current work on low-friction adoption and bounded adopter evidence, and
defines the evidence required to reopen that track.

Use public Issues for profile clarification, non-sensitive schema or validator defects, workflow-compatibility questions, documentation improvements, and proposals that expose no active vulnerability. **Do not** use public Issues for suspected exploitable vulnerabilities — follow [SECURITY.md](SECURITY.md).

A pull request should identify: affected profile IDs; behavioral and compatibility impact; evidence added or changed; new, resolved, or modified residuals; disclosure classification; and the Issue or advisory it addresses.

Contribution mechanics are in [CONTRIBUTING.md](CONTRIBUTING.md); decision
authority for the normative text, schemas, and templates is in
[GOVERNANCE.md](GOVERNANCE.md).

---

## Design principle

AAP does not ask a project to claim zero uncertainty. For a specific revision
or release, it records intent and claims, what prevents their violation, the
supporting evidence and possible defeaters, and the boundary of what remains
unknown. That boundary is the assurance artifact.

---

## License

This repository uses three licenses, split by path:

| File | License | Covers |
|---|---|---|
| [LICENSE](LICENSE) | Apache-2.0 | `schemas/`, `scripts/`, `.github/` workflows, and any future validator or tooling code |
| [LICENSE-docs](LICENSE-docs) | CC-BY-4.0 | `PROFILE.md`, `README.md`, `README.ko.md`, `docs/`, `SECURITY.md`, and all other prose |
| [templates/LICENSE](templates/LICENSE) | CC0-1.0 | Everything under `templates/` |

Code is Apache-2.0, prose is CC-BY-4.0, and copy-ready adopter templates are
CC0-1.0.
