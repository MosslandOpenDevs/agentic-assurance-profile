# Threat model

> **Placement:** Copy this file to `assurance/THREAT_MODEL.md` in the adopting repository, or to the path recorded under `paths.threat_model` in `.agentic-assurance/adoption.yaml`. Replace every `REPLACE_WITH_` placeholder.
>
> **Disclosure rule:** This file is public. Keep actionable attack detail — exploit steps, unpatched bypasses, sensitive production topology, privileged access paths — in the restricted record, not here. See `PROFILE.md` §13 ("Public and restricted disclosure") of the pinned upstream profile, `MosslandOpenDevs/agentic-assurance-profile`.
>
> **Paths note:** Sibling artifact references below use the default `assurance/` paths; if your repository remaps artifacts, substitute the paths recorded under `paths:` in `.agentic-assurance/adoption.yaml`.

---

## 1. Scope and assets

REPLACE_WITH_SCOPE_AND_ASSETS

State what this threat model covers and the assets worth protecting: data, credentials, funds, identities, availability, reputation, and integrity of public claims.

## 2. Actors and trust levels

| Actor | Trust level | Notes |
|---|---|---|
| REPLACE_WITH_ACTOR | REPLACE_WITH_TRUST_LEVEL | REPLACE_WITH_NOTES |

Include benign and adversarial actors: anonymous users, authenticated users, operators, agents, third-party services, and infrastructure providers.

## 3. Trust boundaries

A diagram is optional; the table is not.

| Boundary | Inside | Outside | Crossing mechanism |
|---|---|---|---|
| REPLACE_WITH_BOUNDARY | REPLACE_WITH_TRUSTED_SIDE | REPLACE_WITH_UNTRUSTED_SIDE | REPLACE_WITH_CROSSING_MECHANISM |

## 4. Entry points and attack surface

REPLACE_WITH_ENTRY_POINTS_AND_ATTACK_SURFACE

List every surface an actor can reach: endpoints, message queues, file uploads, webhooks, CLI inputs, dependency and supply-chain channels, and operational access paths. Describe surfaces at a level safe for public disclosure.

## 5. Abuse cases

REPLACE_WITH_ABUSE_CASES

Describe how each actor could misuse the system against its intent: bypass, escalation, replay, injection, exhaustion, data exfiltration, and manipulation of trusted outputs. State the abuse and its impact without publishing a working recipe.

## 6. Controls mapped to invariants

| Threat | Control | Invariant ID | Verification |
|---|---|---|---|
| REPLACE_WITH_THREAT | REPLACE_WITH_CONTROL | INV-EXAMPLE-001 | REPLACE_WITH_VERIFICATION_REFERENCE |

Each row connects a threat to the enforcement mechanism that blocks it, the invariant in `assurance/INVARIANTS.yaml` that names the obligation, and the test or check that verifies the control. Tests verify; controls enforce.

## 7. Residual links

Threats that are not fully controlled are residuals, not omissions. List the affected `RES-` IDs from `assurance/RESIDUALS.yaml`:

- RES-EXAMPLE-001

## 8. Review triggers

Re-review this threat model when any of the following occurs:

- a new entry point, actor, or trust boundary is introduced;
- authentication, authorization, or session handling changes;
- a critical dependency or infrastructure provider changes;
- a security incident or near-miss occurs;
- a linked residual reaches its `review_after` date;
- REPLACE_WITH_PROJECT_SPECIFIC_TRIGGERS
