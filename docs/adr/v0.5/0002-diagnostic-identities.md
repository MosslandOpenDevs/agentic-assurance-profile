# ADR 0002: diagnostic identity and allocation policy

- **Lifecycle path:** PROPOSED while the linked pull request is open ->
  ACCEPTED only when its exact named review-candidate head is durably merged
- **Decision owner:** MosslandOpenDevs maintainers
- **Tracking issue:** [#50](https://github.com/MosslandOpenDevs/agentic-assurance-profile/issues/50)
- **Acceptance:** maintainer review and merge of the exact review-candidate
  head in the linked pull request
- **Acceptance record:** [Draft PR #65](https://github.com/MosslandOpenDevs/agentic-assurance-profile/pull/65)
- **Acceptance review class:** derived from the durable linked-PR acceptance
  record under [`GOVERNANCE.md`](../../../GOVERNANCE.md); the immutable
  candidate does not predeclare its eventual class
- **Recorded:** 2026-07-22
- **Working base:** `main@fced1feeb6daa48da16faa88f220cf4f68517f73`
- **Runtime effect:** none; this ADR allocates no finding instance and changes
  no validator, workflow, schema, template, profile obligation, or output

## Context

The v0.4.x validator exposes human messages and three workflow job names, but
it has no stable semantic identity for a policy condition, an uncompleted
check, or a public capability. Message wording currently carries all three
roles. Freezing those strings would turn presentation details and library
errors into an accidental machine API.

The accepted v0.5 design instead requires:

- a finding code for a semantic condition established by a completed check;
- a reason code when a check is not evaluated or cannot complete;
- a public `check_id` for a semantic capability rather than an implementation
  task or GitHub job; and
- a separately accepted, versioned catalog and legacy mapping before an
  implementation can use either as its parity oracle.

This ADR fixes the identity classes and their evolution rules. It deliberately
does not allocate the full catalog or map v0.4 emitters; that is the next
separately reviewed #50 slice.

## Decision

### Identity classes

The three public identities have different jobs and therefore different
grammars:

| Identity | Grammar | Meaning |
|---|---|---|
| finding `code` | exact ASCII `F` plus four digits; `F0000` is permanently invalid | One immutable semantic condition established by one completed public check. |
| `check_id` | lower-case dot-separated semantic segments; a segment may contain internal hyphens | One public assurance capability in a trusted plan. |
| `reason_code` | `^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*$` | Why a check, required input identity, run bootstrap, or provider projection has no semantic result. |

Finding codes are intentionally opaque and have no product acronym. A human
projection may render `[F0042]`, but the `F` means only “finding”; it does not
mean error, fatal, or a severity. Allocation begins at `F0001`, gaps are
allowed, and exhaustion is a hard stop requiring a separately accepted new
non-colliding grammar. A new catalog ID alone cannot recycle the spelling.

`check_id` uses readable capability names because plans and dependency edges
must be reviewable. It is 3–96 ASCII bytes with 2–8 dot-separated segments;
each segment is 1–32 bytes. Its normalized grammar is:

```text
^[a-z][a-z0-9]*(?:-[a-z0-9]+)*(?:\.[a-z][a-z0-9]*(?:-[a-z0-9]+)*)+$
```

Examples of the shape are `adoption.document-parse` and
`transition.policy-regression`. The already specified
`adoption.profile-classification-review` remains reserved. A check ID never
names a Python function, parser phase, scheduler task, workflow job, or
renderer.

Reason codes are 1–64 ASCII bytes. They are readable state-machine vocabulary
because they are a much smaller operational set and frequently explain a
non-result. Their text is still immutable after acceptance; clarity is not
permission to rename one.

All grammars use exact byte-for-byte ASCII full-match semantics: case folding,
Unicode normalization, leading or trailing whitespace, and a final newline are
rejected. Matching a grammar is necessary but not sufficient; an identifier is
valid only when registered in the exact selected catalog revision.

The diagnostic catalog has its own immutable `catalog_id` and monotonically
increasing positive `catalog_revision`. The first catalog slice allocates the
exact `catalog_id`. It must be an opaque protocol identifier independent of
the display product, executable, package, and provisional `aap` command name.
The stable semantic identity is `(catalog_id, code)`; the same rule applies to
check and reason identifiers. `catalog_revision` selects the exact closed
metadata and fact schema used to interpret a report, but does not create a new
semantic identity for every compatible revision.

Every `CheckPlan`, `CheckEvaluation`, `Finding`, gate decision, and `RunReport`
is bound to one exact `catalog_id + catalog_revision`, and every referenced
identifier must be registered there. ADR 0003 must serialize that binding;
ADR 0004 must bind each canonical plan identity and provider status projection
to the same catalog revision. A bare `F0001`, reason, or check ID may appear as
human display shorthand, but is not a complete machine identity. Exact digest
and JSON spelling belong to ADR 0003.

### Finding versus reason

The boundary is determined by evaluation state, not by whether the text sounds
like an error:

1. A **finding** exists only when an `APPLICABLE` public check completed and
   established a policy, accepted-compatibility, or versioned-operational
   condition. It is attached to that check. A blocking finding makes the
   owning completed check fail; a warning remains a finding on a completed
   passing check.
2. A **reason** exists when a check is `NOT_APPLICABLE`, `UNDETERMINED`,
   `NOT_RUN`, or `FAILED_TO_COMPLETE`. Such a check has `Outcome = NONE` and
   has no finding. The reason explains the check state; it does not pretend
   that the policy condition was evaluated.
3. Safely acquired malformed policy that the bounded parser deterministically
   rejects is a completed parse-check finding. A missing Git object,
   inaccessible input, timeout, dependency failure, unsupported applicable
   event, or internal failure that prevents classification is a reason.
4. A deterministically absent required artifact is a finding when the check
   can safely establish absence. Failure to determine whether it exists is a
   reason.
5. `PREREQUISITE_FAILED` is a reason, requires a non-empty valid `blocked_by`
   chain, and never hides the completed blocking finding at the end of that
   chain.

Reason codes also describe a required `InputReport` identity, run bootstrap,
or provider-adapter boundary that has no public check owner.
Each such use is registered with its exact owner kind and valid state; a
check-state reason cannot be moved to a run boundary merely because its prose
sounds similar. CLI usage errors and conventional signals remain distinct
terminal classes rather than reasons.

Messages, stack traces, exception classes, exit codes, GitHub conclusions, and
believed remediation actors do not choose between the two classes.

### Finding entry contract

Before a finding code can become `ACTIVE`, its catalog entry fixes:

- one semantic condition statement;
- exactly one owning public `check_id`;
- a normative `rule_id`, accepted compatibility-decision ID, or versioned
  operational-catalog reference;
- a closed set of fact keys, their primitive or bounded-list types, required
  versus optional status, and length or cardinality limits;
- default display metadata, which is not machine identity;
- the contexts in which severity and gate effect are derived; and
- lifecycle state and any replacement reference.

Source locations are `SourceRef` values, not arbitrary facts. Raw sensitive
values, unrestricted objects, exception text, and renderer-ready prose are not
fact fields. A library validation message may be projected into bounded facts
such as document kind, schema keyword, and safe pointer; it is never itself a
finding code.

The semantic condition, owning check, required fact keys, fact types, and every
fact constraint are immutable. Constraints include enum membership and member
meaning, numeric bounds, string normalization/pattern/length, list element
schema, ordering or set semantics, and list cardinality. The initial catalog
does not permit `null` facts: an unknown optional fact is absent, and absence
must not be interpreted as a null value.

A later catalog revision may add an optional bounded fact or improve display
metadata only when absence of that fact cannot change condition identity,
severity, gate effect, outcome, resolution authority, or any existing fact's
interpretation. It may not remove a fact, make an optional fact required,
retype or constrain an existing fact differently, add an enum member, or
change meaning. Such a change requires a new finding code and an explicit
replacement link. Reason display-detail keys follow the same compatibility,
bounding, absence, and null rules.

Severity, stage, profile, gate effect, renderer, and fix authority are not
encoded in the finding code. They are evaluated from trusted rule context and
reported separately. The same condition may therefore be `WARN` in one
context and `BLOCK` in another without changing identity.

### Check and reason entry contract

A public check entry fixes its semantic capability and allowed evaluation
kinds. A finding code has exactly one owning check. Public plan dependency
edges and `completion_required` are versioned gate-plan data rather than part
of the check name; an internal refactor does not allocate another check ID.
The later #50 catalog/mapping decision owns the public check catalog and the
semantic ownership, dependency, and possible gate-effect inputs recovered from
v0.4. ADR 0004 owns the canonical plan manifest identity, version and digest,
the trusted derivation of `completion_required`, and complete/partial CI status
and producer/caller-trust binding. It consumes those semantic inputs without
redefining their condition or check meanings.

A reason entry fixes:

- its state-machine meaning;
- its allowed owner kinds (`CHECK | INPUT | RUN | PROVIDER`) and the valid
  state combinations for each;
- whether `blocked_by` is forbidden, optional, or required;
- either a closed set of allowed owners or an explicitly reviewed shared
  scope; and
- bounded display-detail keys, if any.

One reason code may be shared only when all of those semantics are identical.
It may not be reused as a convenient generic message.

### Allocation, deprecation, and tombstones

The catalog is append-only within its identity lineage:

- allocation occurs only in a separately reviewed decision change;
- an implementation change consumes an accepted catalog revision from its
  base and cannot allocate its own passing identity or mapping;
- numeric order and gaps carry no meaning;
- accepted finding codes, check IDs, and reason codes are never recycled;
- lifecycle transitions are monotone: `ACTIVE -> DEPRECATED -> RETIRED` only;
- an `ACTIVE` identity may be emitted by current producers;
- a `DEPRECATED` identity may be emitted only by the catalog-listed legacy or
  compatibility producers through its recorded `last_emitted_revision`; new
  rule implementations use its replacement when one exists;
- a `RETIRED` identity is interpretation-only and must not be emitted by a
  current producer;
- no lifecycle state may be reversed or reactivated;
- a deprecated or retired entry remains as a tombstone with its original
  meaning, first revision, last active and last emitted revisions, rationale,
  and optional replacement;
- replacement does not create an alias and historical reports retain the old
  identity; and
- changing a spelling, including correcting a typo, allocates a new identity.

A replacement must be an existing accepted identity of the same class, must
not refer to itself, and replacement edges must be acyclic. `catalog_id` never
changes within this identity lineage; ordinary evolution increments only the
catalog revision. If governance ever creates a distinct successor lineage, it
must import every prior spelling, allocation watermark, and tombstone as
reserved and cannot claim that the new `catalog_id` preserves the old semantic
identity. Cross-lineage replacement uses the complete old and new identities.
An unrelated external catalog may have the same short spelling, which is why
`catalog_id` is part of semantic identity.

Every catalog revision records its parent revision and immutable candidate
provenance. The candidate bytes do not predeclare their future acceptance or
review class. A separately durable acceptance record binds the exact revision
and canonical digest after review; consumers require that binding rather than
trusting a self-asserted lifecycle field inside the catalog. Consumers select
an exact accepted revision; “latest” is not an implicit input. Serialization,
canonical digest, compatibility negotiation, and redaction are owned by ADR
0003 and #51.

### Legacy mapping completeness

The separately accepted v0.4 mapping closes two related inventories without
conflating a semantic result with the terminal path that carries it.

First, each reachable semantic producer branch or emitter family maps to
exactly one of:

- a finding code and owning check;
- a reason code with its registered `CHECK`, `INPUT`, `RUN`, or `PROVIDER`
  owner and valid state;
- successful completion of a public check with no finding;
- a justified display-only diagnostic that cannot affect outcome, exit status,
  gate state, or check completion.

Independently, each reachable terminal path maps to exactly one terminal
projection:

- a normal report whose explicit planned-check states, `OverallOutcome`, and
  exit `0`, `1`, or `3` agree;
- a pre-plan informational success, which is outside `CheckPlan` and exit `0`;
- a pre-plan invocation error, which is outside `CheckPlan` and exit `2`;
- conventional signal termination; or
- a bootstrap, process, or provider non-completion projection with a stable
  registered reason at the applicable boundary.

One terminal path may carry zero, one, or many semantic results already
classified by the first inventory. Terminal closure is not a claim that a
report contains exactly one finding or reason.

Many legacy messages may map to one identity only when they establish the same
condition and differ solely in bounded facts. One legacy family may map to
multiple identities only through closed, deterministic, non-overlapping
predicates recorded in the mapping. No adapter parses rendered English to
recover identity.

The mapping records an exact source revision and closed producer, emitter, and
terminal-outcome inventory. A producer branch must attach a stable internal
discriminant before YAML/schema libraries, regression builders, or exception
formatters collapse state into prose. Identity must never be reconstructed by
parsing the final English message.

Completeness verification must reject an unregistered producer discriminant,
error or warning emitter, or semantic mapping predicate that does not cover or
overlaps its family. Its independent terminal inventory must reject a silent
early return, option-combination or argparse exit, uncaught bootstrap
exception, unmapped process failure, and unknown external Action failure,
cancellation, timeout, skipped job, lost output, or status-publication result.
Legacy `OK:` wording is not positive evidence by itself; the orchestrator
records check completion explicitly.

The seven Phase 0 internal condition keys remain provisional and non-public.
Their public projection is accepted in the catalog/mapping slice before any
implementation parity decision. That decision cannot modify the accepted
Phase 0 ledger bytes in the same change.

### Existing reservations

This ADR imports, without renaming, the reason vocabulary already fixed by the
accepted design and ADR 0009:

- `PREREQUISITE_FAILED`;
- `PULL_REQUEST_REVISIONS_UNAVAILABLE`;
- `PRIVILEGED_PULL_REQUEST_TARGET_UNSUPPORTED`;
- `PUSH_HAS_NO_REVIEW_TRANSITION`;
- `MERGE_GROUP_HAS_NO_SINGLE_PR_TRANSITION`;
- `MANUAL_RUN_HAS_NO_REVIEW_TRANSITION`;
- `SCHEDULE_HAS_NO_REVIEW_TRANSITION`;
- `CALLER_EVENT_UNSUPPORTED`; and
- `PUSH_TARGET_SNAPSHOT_UNAVAILABLE`.

They are reserved inputs to the first catalog, not proof that a runtime
producer currently emits them. ADR 0009 continues to own their event meaning.
This ADR also preserves the reserved check ID
`adoption.profile-classification-review`. It allocates no `F####` value; the
closed catalog/mapping decision does that separately.

## Boundaries

This decision does not define:

- JSON field spelling, canonicalization, redaction, or text layout (ADR 0003);
- canonical plan manifest identity, version, digest, `completion_required`
  derivation, coverage, CI status, producer/caller trust, or forge rules (ADR
  0004);
- human-review authority verification (ADR 0005);
- product, package, executable, or plugin names (ADR 0001);
- the complete public check catalog, v0.4 semantic-input projection, or legacy
  mapping (the separate #50 catalog/mapping decision candidate);
- package layout, CLI behavior, or implementation types; or
- a new normative profile obligation, Snapshot, rule, or #43 runtime fix.

The identifier strings remain stable even if ADR 0001 later changes product
branding. Human text may display a product label around them; machine identity
does not acquire that label as a prefix.

## Consequences

- Consumers can branch on stable condition, capability, and non-completion
  identities without matching prose.
- Severity changes driven by stage or policy context do not churn finding
  codes.
- Opaque finding codes require a catalog or `explain` surface, but avoid
  freezing a misleading category or product name into identity.
- The current validator cannot gain trustworthy structured output merely by
  wrapping `Report.emit`; identity must be attached at semantic emitters or an
  explicit compatibility adapter.
- No implementation parity work is authorized until the separately reviewed
  catalog and mapping, ADR 0004 plan/check-state projection, and accepted
  authority-provenance decision exist on its base.

## Evidence

Repository counts, current output behavior, Phase 0 constraints, mapping risks,
and excluded decisions are recorded in
[`issue-50-identity-survey.md`](../../evidence/v0.5/issue-50-identity-survey.md).
The separately reviewable catalog and exact v0.4 mapping candidate are in
[`diagnostic-catalog/`](../../evidence/v0.5/diagnostic-catalog/README.md).
