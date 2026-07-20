# Mapping Existing Conventions to Profile Artifacts

An adopting repository frequently already has an architecture document, a threat model, an ADR directory, or an established specification workflow. The profile does not ask for parallel copies of any of these. [PROFILE.md §6](../PROFILE.md) requires "a current system description or mapping to an existing equivalent", and [templates/AGENTIC_ASSURANCE.md §4](../templates/AGENTIC_ASSURANCE.md) states that existing repository conventions may be reused when the mapping is recorded in the adoption file. This document explains how.

For the full adoption sequence, see [ADOPTION.md](ADOPTION.md).

## 1. The `paths:` mechanism

The `paths:` object in `.agentic-assurance/adoption.yaml` maps the profile's artifact roles onto concrete files in the adopting repository. Seven keys are known to the schema and the validator, each with a default:

| Key | Default | Artifact role |
|---|---|---|
| `system` | `assurance/SYSTEM.md` | as-built system description |
| `invariants` | `assurance/INVARIANTS.yaml` | invariant register |
| `claims` | `assurance/CLAIMS.yaml` | claim register |
| `defeaters` | `assurance/DEFEATERS.yaml` | defeater register |
| `residuals` | `assurance/RESIDUALS.yaml` | residual register |
| `threat_model` | `assurance/THREAT_MODEL.md` | trust-boundary and threat documentation |
| `evidence` | `assurance/evidence` | evidence root |

When the `paths:` block or an individual key is omitted, the default applies. Additional string-valued keys are permitted as local extension mappings (for example `decisions` or `reviews`); the [adoption schema](../schemas/adoption.schema.json) accepts them, and tools that do not know a local key ignore it.

The validator resolves these mappings before doing anything else: schema validation of existing YAML artifacts and the per-profile presence checks both operate on the mapped locations, not on the defaults.

## 2. Rules

Three rules govern every mapping. All are consequences of [PROFILE.md](../PROFILE.md) §6 and §15.

1. **Record the mapping in `adoption.yaml`.** A reuse that lives only in a maintainer's head is not a mapping. If `docs/architecture.md` serves as the system description, `paths.system` must say so — otherwise agents, reviewers, and the validator look at the default location, report the artifact missing, and sooner or later a second competing copy appears there.
2. **A mapped artifact must satisfy the same obligations.** Mapping changes where an artifact lives, not what it must contain. A `paths.system` entry pointing at an existing architecture document is adequate only if that document — possibly after extension — covers what a system description must cover: purpose and non-goals, entities and state transitions, trust boundaries, public claims, enforcement and verification inventory, behavior classification, and known unknowns ([PROFILE.md §7](../PROFILE.md); [templates/SYSTEM.md](../templates/SYSTEM.md) shows the expected shape). If the existing document cannot reasonably absorb that content, keep the default artifact and cross-link the two instead.
3. **YAML artifacts must remain schema-valid wherever they live.** The claim, invariant, defeater, and residual registers must validate against the pinned upstream schemas ([../schemas/](../schemas/)) regardless of location. Relocation via `paths:` changes the file path only. Renaming fields, restructuring entries, or embedding the register in a different format is not a mapping — it is a local fork of the artifact format (see §4).

## 3. Worked examples

### 3.1 Existing architecture document as the system description

The repository has maintained `docs/architecture.md` for years. Map it instead of duplicating it:

```yaml
paths:
  system: docs/architecture.md
```

All omitted keys resolve to their defaults, so the registers still live under `assurance/`. Rule 2 applies: `docs/architecture.md` must cover the system-description content — in practice this usually means adding a behavior-classification table and a known-unknowns section to the existing document rather than rewriting it.

### 3.2 Existing threat model and ADR directory

A security-reviewed threat model exists at `docs/security/threat-model.md`, and decisions are recorded as ADRs under `docs/adr`:

```yaml
specification_workflow:
  system: adr-rfc
  root: docs/adr

paths:
  threat_model: docs/security/threat-model.md
  decisions: docs/adr
```

`decisions` is not one of the seven known keys; it is a local extension mapping, which the schema permits. The `specification_workflow` block declares ADR/RFC as the material-change workflow, so the change obligations of [PROFILE.md §9](../PROFILE.md) are met by ADRs rather than by a new parallel document system.

### 3.3 OpenSpec workflow with a relocated assurance tree

The project runs OpenSpec and keeps all assurance material under `docs/assurance/` to match its documentation layout:

```yaml
specification_workflow:
  system: openspec
  root: openspec

paths:
  system: docs/assurance/SYSTEM.md
  invariants: docs/assurance/INVARIANTS.yaml
  claims: docs/assurance/CLAIMS.yaml
  defeaters: docs/assurance/DEFEATERS.yaml
  residuals: docs/assurance/RESIDUALS.yaml
  threat_model: docs/assurance/THREAT_MODEL.md
  evidence: docs/assurance/evidence
```

Rule 3 applies: the four YAML registers keep the upstream schema format at the new location. When relocating the whole tree, also update `security.public_assurance_root` in the adoption file to match.

## 4. Anti-pattern: the local fork

The one reuse strategy the profile prohibits is copying the upstream profile text or schemas into the adopting repository and maintaining them there. [PROFILE.md §15](../PROFILE.md) forbids an agent to "copy and modify the profile as an untracked local fork". Why it fails:

- the local copy drifts: wording gets "clarified", obligations get softened, and no change record distinguishes deliberate local policy from accidental weakening;
- the pin becomes decorative: the repository declares a version and commit while actually following its own divergent text;
- reviewers and agents can no longer tell which obligations are upstream and which are local, so precedence ([templates/AGENTIC_ASSURANCE.md §3](../templates/AGENTIC_ASSURANCE.md)) is unresolvable.

The correct alternatives:

- pin the upstream by version and full commit SHA and reference it ([ADOPTION.md §2](ADOPTION.md));
- map existing files with `paths:` as shown above;
- record genuine local additions as local extensions in the adopting repository's own artifacts — local extensions must not silently weaken the pinned upstream profile ([PROFILE.md §5](../PROFILE.md)).

Copying the templates is not a fork. Everything under [../templates/](../templates/) is published under CC0-1.0 precisely so adopters can copy the skeletons and fill them with project truth. The fork prohibition covers the normative profile text and the schemas, not the templates.

## 5. Mapping external tool output into the evidence position

The `paths:` mechanism maps documents. An adopting repository also runs tools, and their output belongs in the model too — referenced from the registers rather than restated inside them. This is the reuse that keeps the profile a coordination layer: it consumes what the existing toolchain already produces instead of asking for a second, hand-written account of the same result.

### 5.1 Where each tool class lands

| Tool class | Typical output | Position in the core model | What it does not establish |
|---|---|---|---|
| Specification and planning workflow (Spec Kit, OpenSpec, ADR/RFC, issues) | change specification, approved plan | intent and claim input, declared via `specification_workflow` (§3.2, §3.3) | that the implementation matches the specification |
| Tests, schema checks, constraint checks | pass or fail bound to a revision | `verification` on the invariant; the run is `evidence` | that an unchecked property holds |
| Static analysis, scanners, structural or semantic code review | findings on a revision or a diff | `evidence` where the run is reproducible; individual findings are defeater candidates ([PROFILE.md §2.7](../PROFILE.md)) | that the absence of a finding proves the property |
| Agent change records, session logs, prompt and tool-call traces | what an agent read, ran, and changed | provenance evidence: attribution for a change, and an input to brownfield reconstruction ([PROFILE.md §7](../PROFILE.md)) | that the change was correct, or that a human approved it |
| Build and release attestation (SLSA, in-toto, signed digests) | where and how an artifact was built | the release evidence manifest ([PROFILE.md §11](../PROFILE.md)) | anything about the behavior of the source |

The rightmost column is the one that gets lost. Each of these tools answers its own question well; an assurance argument fails when a strong answer to one question is filed as the answer to another.

### 5.2 An evidence reference binds to a revision

The `evidence` field in the claim, invariant, and defeater registers is a free-form array of strings by design — a reference is whatever lets a reader reproduce the result. [PROFILE.md §11](../PROFILE.md) supplies the constraint: evidence is attributable to a revision, release, artifact, or deployment. A tool's name is not a reference, and neither is a URL that shows something different next week.

Not evidence references:

```yaml
evidence:
  - "CI is green"
  - "static analysis passes"
  - "https://ci.example.com/latest"
```

Evidence references:

```yaml
evidence:
  - "tests/test_session.py::test_expired_challenge_rejected, commit 4f2a9c1"
  - "assurance/evidence/2026-07-01-codeql.sarif (workflow run 118392, commit 4f2a9c1)"
  - "SLSA provenance attestation for sha256:9b1e0c7..., release v1.4.0"
```

Where the tool's output is durable and safe to publish, store it under the mapped `evidence` root and reference the file. Where it is not — a hosted scan behind authentication, a report carrying restricted detail — reference the run identity, keep the artifact private, and let the affected claim's `proof_tier` be `OPERATIONALLY_AUDITABLE` rather than `INDEPENDENTLY_VERIFIABLE` ([PROFILE.md §8](../PROFILE.md), [§13](../PROFILE.md)).

### 5.3 The output does not set the status by itself

[PROFILE.md §4](../PROFILE.md) classifies conclusions, and the classification follows the reproducibility of the reference rather than the confidence of the tool:

- a deterministic check a reader can re-run against a named revision supports `VERIFIED`;
- a result the reader cannot re-run — an expired hosted run, a summary pasted out of a tool — supports `INFERRED` at best;
- an agent's narrative that it ran a check is not evidence by itself ([PROFILE.md §2.6](../PROFILE.md)). An agent change record is evidence *of the action*: it can support "this file changed under approved task T" and leaves the invariant's own status where it was;
- a review tool reporting no findings is coverage, not proof. Record it under `verification`, and record what that tool cannot see as a defeater or a residual.

### 5.4 Worked example: existing test suite and scanner referenced from an invariant

```yaml
# assurance/INVARIANTS.yaml (excerpt)
- id: INV-AUTH-001
  title: Consumed authentication challenges cannot be replayed
  statement: An expired or consumed challenge cannot create a valid authenticated session.
  severity: critical
  intent:
    classification: INTENDED
    authority: docs/adr/0031-wallet-authentication.md
  scope: The session-issuing path of the authentication service.
  enforcement:
    - "Unique partial index on auth_challenge(nonce) where consumed_at is null"
    - "src/auth/session.py: single-use guard in issue_session()"
  verification:
    - "tests/test_session.py::test_expired_challenge_rejected"
    - "tests/test_session.py::test_consumed_challenge_rejected"
    - "CodeQL workflow .github/workflows/codeql.yml"
  evidence:
    - "tests/test_session.py, commit 4f2a9c1 (workflow run 118392)"
    - "assurance/evidence/2026-07-01-codeql.sarif (run 118392, commit 4f2a9c1)"
  status: VERIFIED
  disclosure: PUBLIC
  owner: REPLACE_WITH_OWNER
```

Nothing here is a new artifact: the tests, the workflow, and the ADR already existed. `enforcement` names what blocks a violation and `verification` names what checks it — the distinction in [PROFILE.md §2.4](../PROFILE.md) and [§2.5](../PROFILE.md) — while `evidence` carries the bound references that let a reader confirm the `VERIFIED` status. The decision record is reachable through `intent.authority` because §3.2 already mapped `decisions` onto `docs/adr`.

### 5.5 What no external tool supplies

No tool produces the entries that carry human authority ([PROFILE.md §3](../PROFILE.md)):

- purpose and non-goals;
- the wording and the limitation of a public claim;
- the disposition of a defeater;
- the acceptance of a critical residual.

A tool may propose any of these and an agent may draft them, but only the named owner can decide them — an agent-drafted record carries human authority only when the owner's own approval act, such as a reviewed merge or a recorded review outcome, anchors it ([PROFILE.md §7](../PROFILE.md)). That boundary is also why the profile does not need an analyzer, a scanner, or a session recorder of its own: the mechanical work belongs to tools that already do it well, and what remains is the part that has to be decided by a person and survive the next change.

## Related documents

- [ADOPTION.md](ADOPTION.md) — the full adoption walk-through
- [PROFILE.md](../PROFILE.md) — the normative profile text
- [templates/adoption.yaml](../templates/adoption.yaml) — the adoption file template
- [schemas/adoption.schema.json](../schemas/adoption.schema.json) — the schema enforcing the `paths:` shape
