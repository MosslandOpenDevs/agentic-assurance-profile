# Mapping Existing Conventions to Profile Artifacts

An adopting repository frequently already has an architecture document, a threat model, an ADR directory, or an established specification workflow. The profile does not ask for parallel copies of any of these. For active adopters, [PROFILE.md §6.1](../PROFILE.md) permits the current system description inline under lite or at the artifact mapped by `paths.system`; for the exclusive `archived` profile, §6.6 uses that mapped system artifact for its four required historical facts. [templates/AGENTIC_ASSURANCE.md §4](../templates/AGENTIC_ASSURANCE.md) states that existing repository conventions may be reused when the mapping is recorded in the adoption file. This document explains how.

For the full adoption sequence, see [ADOPTION.md](ADOPTION.md).

## 1. The `paths:` mechanism

The `paths:` object in `.agentic-assurance/adoption.yaml` maps the profile's artifact roles onto concrete files in the adopting repository. Seven keys are known to the schema and the validator, each with a split-layout default:

| Key | Default | Artifact role |
|---|---|---|
| `system` | `assurance/SYSTEM.md` | active as-built system description, or the four §6.6 historical facts under `archived` |
| `invariants` | `assurance/INVARIANTS.yaml` | invariant register |
| `claims` | `assurance/CLAIMS.yaml` | claim register |
| `defeaters` | `assurance/DEFEATERS.yaml` | defeater register |
| `residuals` | `assurance/RESIDUALS.yaml` | residual register |
| `threat_model` | `assurance/THREAT_MODEL.md` | trust-boundary and threat documentation |
| `evidence` | `assurance/evidence` | evidence root |

Under the split layout, the default applies when the `paths:` block or an individual key is omitted. Lite replaces the known split artifacts with `.agentic-assurance/assurance.yaml`: its implicit split defaults are inactive, except that omitted `paths.system` falls back to `assurance/SYSTEM.md` when the lite document has no nonblank inline `system`. Every path explicitly carried by either layout is still containment- and symlink-retarget checked. Additional string-valued keys are permitted as local extension mappings (for example `decisions` or `reviews`); the [adoption schema](../schemas/adoption.schema.json) accepts them, and tools that do not know a local key ignore it. The complete `paths:` object is limited to 256 mappings and each mapped path to 4,096 characters so containment, target-binding, and pull-request evidence checks remain bounded; consolidate closely related local roles under a directory mapping rather than enumerating beyond that limit.

The validator resolves the mappings applicable to the selected layout before artifact schema and presence checks. In split, those checks operate on mapped locations or their defaults. In lite, register checks operate on the consolidated file and only the active system fallback is loaded separately; dormant known split-role mappings do not become lite register sources.

## 2. Rules

Four rules govern every mapping. All are consequences of [PROFILE.md](../PROFILE.md) §6 and §15.

1. **Record the mapping in `adoption.yaml`.** A reuse that lives only in a maintainer's head is not a mapping. If `docs/architecture.md` serves as the system description, `paths.system` must say so — otherwise split, archived, or lite without inline system makes agents, reviewers, and the validator look at the default location, report the artifact missing, and sooner or later a second competing copy appears there.
2. **A mapped artifact must satisfy the same obligations.** Mapping changes where an artifact lives, not what it must contain. For an active adoption, a `paths.system` entry pointing at an existing architecture document MUST satisfy the §6.1 minimum: identify the system being assured, its principal responsibilities and material boundaries, and known material limitations or unknowns. A brownfield description SHOULD normally also cover the fuller §7 reconstruction — purpose and non-goals, entities and state transitions, trust boundaries, public claims, enforcement and verification inventory, behavior classification, and known unknowns; [templates/SYSTEM.md](../templates/SYSTEM.md) shows that expected shape. This fuller list is recommended reconstruction depth, not a separate hard equivalence test imposed only on mapped or split descriptions. For an `archived` adoption, the mapped system artifact instead MUST state all four §6.6 facts: that the repository is retained solely for historical reference, is not supported or intended for current use, and has no active operation, functional maintenance, or feature development; historical purpose; known material limitations; and the last supported revision or release (or explicitly that none exists). If the existing document cannot reasonably absorb the applicable content, keep the default artifact and cross-link the two instead.
3. **YAML artifacts must remain schema-valid wherever they live.** The claim, invariant, defeater, and residual registers must validate against the pinned upstream schemas ([../schemas/](../schemas/)) regardless of location. Relocation via `paths:` changes the file path only. Renaming fields, restructuring entries, or embedding the register in a different format is not a mapping — it is a local fork of the artifact format (see §4).
4. **Mapping must not move policy outside owner review.** Extend the repository's effective human-owner review mechanism to the exact custom adoption declaration, every custom location named under `paths:`, `specification_workflow.root`, `human_review.record`, `security.policy`, and `security.public_assurance_root`; directory mappings should cover their descendants. When GitHub CODEOWNERS with enforced code-owner review is that mechanism, add those locations to `CODEOWNERS`. If the declaration itself moves from `.agentic-assurance/adoption.yaml`, also pass that exact path as the reusable workflow's `adoption-file` and substitute it in the assurance reading order in both root `AGENTIC_ASSURANCE.md` and root `AGENTS.md`. If any such location is a tracked symlink, the effective boundary must cover three locations: the lexical link path (including a retargeting change), the resolved target, and the target's parent or containing tree; list all three in CODEOWNERS when it is used. The validator follows in-project symlinks for content and containment and warns with these locations when it encounters one, but GitHub ownership is matched against changed Git paths and does not automatically follow a link; the warning does not verify CODEOWNERS, branch-protection, or an equivalent repository control.

## 3. Worked examples

### 3.1 Existing architecture document as the system description

The repository has maintained `docs/architecture.md` for years. Map it instead of duplicating it:

```yaml
paths:
  system: docs/architecture.md
```

This example uses the default split layout, so all omitted keys resolve to their defaults and the registers still live under `assurance/`. Rule 2 applies: `docs/architecture.md` must cover the system-description content — in practice this usually means adding a behavior-classification table and a known-unknowns section to the existing document rather than rewriting it.

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

`decisions` is not one of the seven known keys; it is a local extension mapping, which the schema permits. The `specification_workflow` block declares ADR/RFC as the material-change workflow, so ADRs are the vehicle through which the change obligations of [PROFILE.md §9](../PROFILE.md) must be met rather than a new parallel document system. Each material-change ADR must still state the applicable §9 content; the validator checks that the declared workflow root is real and project-local, not whether the prose is substantively complete.

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

Rules 3 and 4 apply: the four YAML registers keep the upstream schema format at the new location, and the `docs/assurance/` tree plus `openspec` root belong in `CODEOWNERS`. When relocating the whole tree, also update `security.public_assurance_root` in the adoption file to match. If any mapped path is implemented as a symlink, add the lexical link, resolved target, and target parent/tree rather than assuming the directory rule for one side covers the other.

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

## Related documents

- [ADOPTION.md](ADOPTION.md) — the full adoption walk-through
- [PROFILE.md](../PROFILE.md) — the normative profile text
- [templates/adoption.yaml](../templates/adoption.yaml) — the adoption file template
- [schemas/adoption.schema.json](../schemas/adoption.schema.json) — the schema enforcing the `paths:` shape
