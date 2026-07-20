# As-built system description

> **Placement:** Copy this file to `assurance/SYSTEM.md` in the adopting repository, or to the path recorded under `paths.system` in the configured adoption declaration (default: `.agentic-assurance/adoption.yaml`). Replace every all-caps placeholder prompt in the sections that apply, and delete inapplicable prompt sections.
>
> **Evidence rule:** Every material conclusion in this document that is not classified `UNKNOWN` must cite concrete evidence: file and line, database constraint, test name, command output, endpoint response, artifact digest, deployment record, or runtime metric. An AI-generated narrative is not evidence by itself. When evidence is insufficient, record `UNKNOWN` rather than invent confidence.
>
> **Paths note:** Sibling artifact references below use the default `assurance/` paths; if your repository remaps artifacts, substitute the paths recorded under `paths:` in the configured adoption declaration.
>
> **Profile-specific use:** `archived` applies only when the repository is retained solely for historical reference, is not supported or intended for current use, and has no active operation, functional maintenance, or feature development. Such adopters MUST complete §0 below. For non-`archived` adopters, delete §0 and complete §§1–10. An `archived` adopter MAY retain any of §§1–10 that provide useful historical context, but those sections do not replace any §0 statement. Initial adoption and factual corrections or upkeep to the pin, stage, review record, and agent instructions are archival-assurance metadata work, not functional maintenance.

---

## 0. Archived declaration (`archived` profile only)

Delete this section for every non-`archived` adoption. For an `archived` adoption, replace all four prompts; do not infer any answer merely from inactivity or repository age.

- **Historical-reference-only status; no active operation, functional maintenance, or feature development:** REPLACE_WITH_ARCHIVED_OPERATION_MAINTENANCE_AND_FEATURE_DEVELOPMENT_STATUS
- **Historical purpose:** REPLACE_WITH_ARCHIVED_HISTORICAL_PURPOSE
- **Known material limitations:** REPLACE_WITH_ARCHIVED_MATERIAL_LIMITATIONS
- **Last supported revision or release:** REPLACE_WITH_ARCHIVED_LAST_SUPPORTED_REVISION_OR_RELEASE_OR_EXPLICIT_NONE

The human owner must confirm all four statements and the `paths.system` mapping during adoption review. The interim validator requires this artifact to be non-empty at every adoption stage. At `HUMAN_REVIEWED` and `CONFORMANT`, it additionally rejects any unchanged archived prompt above. It does not establish the truth of a replacement or semantically parse the four statements. That stronger structured enforcement is deferred to [#40](https://github.com/MosslandOpenDevs/agentic-assurance-profile/issues/40), so explicit owner review remains the content backstop.

## 1. Purpose and users

REPLACE_WITH_PURPOSE_USERS_AND_SCOPE

State what the system is for, who uses it, and the boundary of what it covers.

## 2. Non-goals

REPLACE_WITH_EXPLICIT_NON_GOALS

List what the system deliberately does not do. Non-goals are human-approved intent; an agent must not redefine them.

## 3. Domain entities and identifiers

REPLACE_WITH_DOMAIN_ENTITIES_AND_IDENTIFIERS

Name the core entities, their stable identifiers, and where each identifier is authoritative.

## 4. State transitions

REPLACE_WITH_STATE_TRANSITIONS

Describe the material lifecycle states and permitted transitions for each core entity, including who or what may trigger each transition.

## 5. Trust boundaries and external dependencies

REPLACE_WITH_TRUST_BOUNDARIES_AND_EXTERNAL_DEPENDENCIES

Identify where control changes hands: external services, third-party data, user input surfaces, deployment infrastructure, and privileged access paths. Cross-reference `assurance/THREAT_MODEL.md` when present.

## 6. Public claims and user-visible promises

REPLACE_WITH_PUBLIC_CLAIMS_AND_PROMISES

List what the project asserts to users, operators, integrators, or the public. Material claims belong in `assurance/CLAIMS.yaml` with stable `CLAIM-` IDs; summarize and reference them here.

## 7. Enforcement inventory

REPLACE_WITH_ENFORCEMENT_INVENTORY

List the mechanisms that prevent or block invariant violations: database constraints, authorization guards, cryptographic checks, schemas, state-machine guards, transaction boundaries, policy enforcement points. Reference the affected `INV-` IDs.

## 8. Verification and evidence inventory

REPLACE_WITH_VERIFICATION_AND_EVIDENCE_INVENTORY

List the mechanisms that check declared properties: test suites, static analysis, migration verification, runtime assertions, monitoring, independent reproduction. State where evidence is stored and how it is bound to a revision, artifact digest, or deployment. Tests verify; controls enforce.

## 9. Behavior classification

Classify each material observed behavior. Classification is one of `INTENDED`, `ACCIDENTAL`, `COMPATIBILITY`, `UNKNOWN`, `DEPRECATED`. Conclusion is one of `VERIFIED`, `INFERRED`, `UNKNOWN`, `CONTRADICTED`.

| Behavior | Classification | Evidence | Conclusion |
|---|---|---|---|
| REPLACE_WITH_OBSERVED_BEHAVIOR | UNKNOWN | REPLACE_WITH_EVIDENCE_REFERENCE | UNKNOWN |

Do not classify behavior as `INTENDED` merely because it exists. Current production behavior is evidence of current behavior, not automatic proof of intended behavior.

## 10. Known unknowns

REPLACE_WITH_KNOWN_UNKNOWNS

List the questions this reconstruction could not answer and the evidence that would resolve each one. Material remaining doubt also belongs in `assurance/RESIDUALS.yaml` with stable `RES-` IDs.
