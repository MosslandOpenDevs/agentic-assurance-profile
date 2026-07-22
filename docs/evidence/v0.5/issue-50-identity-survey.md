# Issue #50 diagnostic-identity survey

> **DECISION SUPPORT — NOT A PUBLIC CATALOG — NOT RUNTIME BEHAVIOR**

This note supports
[ADR 0002](../../adr/v0.5/0002-diagnostic-identities.md). It records why the
v0.4 message surface cannot safely become the v0.5 identity contract and keeps
measured facts separate from allocation policy.

## Bounded slice

- working base: `main@fced1feeb6daa48da16faa88f220cf4f68517f73`;
- parent aggregate record:
  [Issue #48 comment](https://github.com/MosslandOpenDevs/agentic-assurance-profile/issues/48#issuecomment-5040643089);
- child and active-slice record:
  [Issue #50 comment](https://github.com/MosslandOpenDevs/agentic-assurance-profile/issues/50#issuecomment-5040646569);
- active hard cap: four elapsed working hours, not increasable while active;
- scope: ADR 0002, the ADR index, this evidence note, and a
  documentation-only Unreleased changelog entry; and
- non-scope: catalog allocation, legacy mapping bytes, executable contracts,
  JSON/output, CI status or forge trust, authority verification, package/CLI
  naming, ledger mutation, Snapshot work, and #43 runtime behavior.

The slice stops rather than expanding if an honest identity rule requires a
non-scope decision. Its output is a separately reviewed Draft PR.

## Current repository observation

At the working base:

- `scripts/validate.py` is 7,263 lines;
- `Report` stores only `(level, message)` tuples;
- the validator contains 243 direct result emissions: 195 `error`, 16 `warn`,
  and 32 `ok` calls;
- eight sites inspect `report.results` directly to make intermediate control
  decisions;
- 30 paths return through `report.emit` before the end of their entry-point
  flow;
- the public entry points `self-check`, `adopter`, and `drift` mix planning,
  execution, gate decisions, and rendering; and
- `.github/workflows/adopter-validate.yml` exposes the job names `structure`,
  `declared-stage`, and `drift`, which are provider projections rather than a
  reviewed semantic capability graph.

These are code-surface counts, not proposed catalog cardinalities. Multiple
emitters may establish one semantic condition, while one dynamic family may
need deterministic predicates. Conversely, a message count cannot reveal
checks that disappeared after an early prerequisite failure.

The existing `Report.emit` JSON contains `subcommand`, message-level results,
counts, and exit code. It has no finding code, SourceRef, owning check,
applicability, completion, outcome, reason, dependency edge, coverage, plan
identity, or overall indeterminate state. Wrapping that final JSON would
therefore preserve the ambiguity the Foundation is intended to remove.

## Phase 0 constraint

The accepted Phase 0 decision
[`AAP-V05-P0-ORACLE-001`](oracle-decisions/phase-0-v0.4.0-seven-seed-r1.json)
sets:

```text
implementation_parity_authorized = false
parity_projection = null
```

The bound candidate ledger also states that its
`phase0.internal.*` condition keys are provisional, not finding codes, check
IDs, or reason codes. Before implementation parity it requires an accepted
public mapping with evaluated severity, owning check, and check state, plus the
accepted ADR 0004 gate-plan projection that fixes `completion_required`,
dependencies, coverage, and plan identity.

Therefore neither ADR 0002 nor a later implementation may relabel the seven
internal keys in place. A catalog/mapping candidate is accepted separately,
then a successor decision may authorize its exact bytes for implementation
parity.

## Why message-derived identity is rejected

### Presentation and condition are different

Messages contain paths, IDs, parser wording, visibility, stage, PR prose, and
suggested remediation. Those values are facts or display context. Treating the
whole string as identity would assign a new code whenever wording improves or
a dependency changes its exception text.

### Severity is contextual

Several drift and stage conditions warn in one accepted context and block in
another. Prefixes such as `E`, `W`, `ERROR`, or a stage name would either lie
or split one condition into multiple identities. Gate effect belongs to the
evaluation, not the code.

### Failure and non-completion are different

A safely parsed declaration that violates a required-field rule is a completed
policy failure. A read deadline, missing Git revision, unavailable dependency,
or unsupported applicable event means the check could not establish a policy
result. Both can currently print `ERROR:`, but only the first is a finding.

### Positive messages do not prove a closed plan

An `OK:` message proves only that code reached one renderer call. It does not
prove that every trusted plan entry existed, was applicable, or completed.
The future compatibility adapter must instantiate the plan first and record
completion independently of success prose.

## Candidate inventory method for the next slice

The catalog/mapping slice should build a reproducible inventory from:

1. Python AST extraction of direct `Report.error`, `warn`, and `ok` sites,
   upstream YAML/schema/regression diagnostic producer branches, and
   policy-regression result builders;
2. workflow extraction of bootstrap exits, emitted commands, job conclusions,
   and public output propagation;
3. execution of the existing 452-test suite and the accepted seven-case corpus
   to collect exercised variants;
4. human grouping by semantic condition and authority reference; and
5. a closed mapping verifier that rejects an unregistered public emitter or
   overlapping predicate.

AST and test extraction are discovery aids, not allocation authority. Human
review must decide whether two sources establish the same condition, whether a
source is a finding or reason, and which public check owns it.

An initial survey estimates roughly 20–35 semantic checks, 85–120 finding
conditions, 35–55 non-completion reasons, and 150–220 mapping rows after
semantic grouping. The estimate combines the 243 final emitters with roughly
50 policy-regression condition templates and workflow/bootstrap terminal
sources; those sets overlap and are not added mechanically. These ranges are
`INFERRED`, not a target and not permission to omit a source. If a closed
inventory cannot fit the child cap, the correct result is `RESCOPE`, not a
partial catalog described as complete.

## Reserved inputs and ownership boundaries

The v0.5 design already reserves
`adoption.profile-classification-review` and `PREREQUISITE_FAILED`. Accepted
ADR 0009 reserves eight additional event reasons. ADR 0002 imports those exact
strings but does not claim that v0.4 emits them.

Adjacent decisions remain separate:

- ADR 0003 owns JSON spelling, redaction, and deterministic serialization;
- the next #50 decision owns the public check catalog and the v0.4 semantic
  ownership, dependency, possible gate-effect, and mapping inputs;
- ADR 0004 owns canonical plan manifest identity, version and digest, trusted
  `completion_required` derivation, CI status identity, binding the accepted
  plan to a trusted provider projection, and producer/caller trust;
- ADR 0005 owns the boundary between structurally recorded review provenance
  and externally verified human authority;
- ADR 0001 owns package, executable, and display naming; and
- the #50 catalog/mapping decision owns actual `F####` allocation and the
  complete v0.4 projection.

This separation is why product initials do not appear in finding codes. A
later display-name decision cannot rename a machine identity or force an alias
layer into the first public protocol.

## Remaining unknowns

- exact public check count and dependency graph;
- exact first-catalog finding and reason allocations;
- which dynamic legacy families need disjoint mapping predicates;
- canonical catalog bytes and digest rules, pending ADR 0003;
- installed package layout, pending ADR 0001 and the distribution checkpoint;
  and
- provider status spelling and authentication, pending ADR 0004.

None of these unknowns prevents the identity-class decision. They do prevent
this slice from claiming that a usable catalog, JSON contract, or runtime
adapter has shipped.
