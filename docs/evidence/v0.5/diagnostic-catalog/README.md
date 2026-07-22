# v0.5 diagnostic catalog and v0.4.0 mapping candidate

> **PROPOSED REVIEW DATA — NOT ACCEPTED — NOT A RUNTIME CONTRACT**

This directory is the review candidate for Issue
[#50](https://github.com/MosslandOpenDevs/agentic-assurance-profile/issues/50),
Slice 50B. It allocates the first proposed diagnostic catalog and maps the
exact v0.4.0 semantic and terminal surface into that catalog. It changes no
validator, workflow, profile, schema, template, Phase 0 ledger, report format,
or CI status.

The candidate cannot accept itself. The files deliberately contain
`acceptance_binding: null` and
`implementation_parity_authorized: false`. Review and merge preserve one named
candidate head; they do not make these bytes accepted. A later acceptance-only
record with a qualifying durable review binding may accept that exact candidate.
Implementation parity still requires the separate Phase 0 projection and
acceptance sequence in
[`../oracle-decisions/README.md`](../oracle-decisions/README.md).

## Candidate artifacts

- [`catalog-r1.json`](catalog-r1.json) allocates one opaque, brand-independent
  `catalog_id`, revision 1, the closed check/finding/reason entry sets, and the
  semantic graph inputs that ADR 0004 may later consume.
- [`legacy-v0.4.0-mapping-r1.json`](legacy-v0.4.0-mapping-r1.json) binds the
  exact release source and closes semantic producers separately from terminal
  paths. It also projects the seven accepted Phase 0 conditions without
  changing their ledger bytes.

| Review artifact | Raw SHA-256 |
|---|---|
| `catalog-r1.json` | `4293658b4fea19180f8593a5d4d287cd33ff56ca3982fca4ad8134630f3ee42b` |
| `legacy-v0.4.0-mapping-r1.json` | `29d41201faa0322aab0f067698af7590787fa5cc8b46cc8efe5969ebb382b8d1` |

The mapping binds the catalog hash. These values are ordinary review evidence,
not ADR 0003 canonical serialization or an acceptance digest.

These JSON files are decision data, not the public v0.5 report or catalog wire
format. ADR 0003 still owns field spelling, canonical serialization, digest,
redaction, and negotiation. Their ordinary raw SHA-256 values are review
evidence only and do not pre-empt that decision.

## Exact source boundary

The mapped release is the annotated tag object
`1373d963a098e13d2f44891e58ee8a47e285c5c3` (`v0.4.0`), peeled to commit
`00e2fe46d4eb01a4147f149851a48a3017cbb796`. The three runtime sources are
byte-identical on the Slice 50B working base
`main@a34f074ab57214d5fe924ba90c00df313cc2acb6`:

| Source | Raw SHA-256 |
|---|---|
| `scripts/validate.py` | `c603735db7218c9d4a7da7cafb31501294b1e00ac84290ae4d5256feb27f6298` |
| `.github/workflows/adopter-validate.yml` | `d6c183e676cf72d9332fec2f417faff110a8d97e452bcb1697117221c1c25ea8` |
| `.github/workflows/self-check.yml` | `6f279cd99dac64e03aa7db01db36c5e328d7b34e1eb6be79ecdc10dbbf8f5497` |

Line locators in the mapping always mean those exact bytes, never an implicit
latest file.

## What “closed” means here

The mapping has independent closed sets for:

1. every direct `Report.error`, `Report.warn`, and `Report.ok` call;
2. every pre-render loader, schema, and regression producer branch whose
   meaning is otherwise collapsed into a string;
3. every direct `Report.emit` return and every `report.results` control read;
4. parser help/usage, import/bootstrap, top-level exception and signal paths;
5. each workflow `run`, `uses`, job `if`/`needs`, required output,
   `continue-on-error`, and provider conclusion family; and
6. cancellation, timeout, skipped job, lost output, and status-publication
   outcomes that only a provider adapter can observe.

Closed inventory does **not** claim that v0.4 already emits typed identity.
Where v0.4 collapses two states into the same English text, exit code, or
provider conclusion, the row records the required future discriminant and is
`INTENDED_CHANGE_PENDING`. An implementation may not recover identity by
parsing rendered English. Unknown source or provider families fail closure;
they do not inherit a catch-all success.

The catalog contains 113 proposed finding identities. Exactly 112 bind one or
more v0.4 producer groups. Only `F0072` is a prospective allocation with an
explicit closed negative v0.4 inventory; the mapping does not pretend that
v0.4 emitted it. `F0015`, `F0071`, and `F0097` are instead bound to closed
v0.4 source predicates that require a future typed discriminant. All four
remain `INTENDED_CHANGE_PENDING`, and the whole candidate remains non-runtime.

The compatibility dispositions are:

- `PRESERVE`: the semantic condition and selected behavior remain compatible;
- `INTENDED_CHANGE_PENDING`: v0.5 must distinguish a finding, non-completion,
  or terminal state that v0.4 currently collapses; and
- `KNOWN_BUG_PENDING`: an accepted compatibility authority would be required
  before preserving or changing a known defect. Revision 1 allocates no row
  with this disposition.

## Positive completion is not inferred from prose

The 32 legacy `OK:` emitters are evidence that a renderer call was reached;
they are not proof of a closed plan. Mapping rows may identify the public
capability whose successful branch was reached, but a future adapter must
instantiate the trusted plan and record check completion explicitly. Likewise,
the eight `report.results` reads and 30 early `Report.emit` returns are control
flow observations, not public check state.

## Phase 0 selected projection

The projection below is intentionally narrower than an ADR 0004 plan. It maps
only the accepted seven-seed condition set and does not bind
`completion_required`, `GateCoverage`, `GatePlanIdentity`, complete dependency
edges, `OverallOutcome`, or public exit projection.

| Phase 0 case | Selected public result |
|---|---|
| split/core DRAFT | `adoption.bundle-conformance` completed with no selected finding |
| lite/core DRAFT | `adoption.bundle-conformance` completed with no selected finding |
| archived reviewed | `adoption.archived-history-boundary` completed with warning `F0001` |
| stage downgrade | `transition.policy-regression` completed with blocking `F0002` |
| security path escape | `adoption.repository-containment` completed with blocking `F0003` |
| strict unrouted component | `transition.component-routing` completed with blocking `F0004` |
| pinned release self-check | `profile.release-tree-conformance` completed with no selected finding |

The trust-path seed produces two legacy `ERROR:` lines but one semantic
`F0003` instance. The mapping fixes that collapse explicitly; line count is not
finding multiplicity.

## Required implementation discriminants

The v0.4 renderer stores only `(level, message)`. Before a compatibility
adapter can emit this catalog, the producer must attach stable discriminants
at the source branch for at least:

- bounded YAML/JSON loading: inaccessible input versus malformed bounded
  policy;
- schema evaluation: policy violation versus unavailable offline reference;
- every adoption, path-target, and register regression template;
- silently swallowed PR-body and lite-system inspection failures;
- completed policy failure versus validator bootstrap, internal, or output
  failure; and
- workflow N/A, failed prerequisite, action/process failure, skipped,
  cancelled, timed out, lost output, and status-publication failure.

The future orchestrator must also create positive check state independently of
legacy success messages. Until these discriminants and ADR 0004 are present,
the candidate is interpretation and implementation input only, not an
executable parity oracle.

Every mapped finding that has required facts carries a closed binding for the
exact required key set. Source-fixed values are literal; context-dependent
values name a registered trusted semantic input or a closed source-predicate
dispatch. Missing, extra, null, unknown, or out-of-domain facts are rejected.
These bindings cover all 78 finding leaves that require facts; they are mapping
evidence only and do not define ADR 0003 wire spelling.

GitHub step `outcome` and effective step `conclusion` are separate axes. The
mapping records both—especially for `continue-on-error`—then carries job
result, check conclusion, and provider observation as distinct downstream
states. All observation-ready flags remain false.

## Decision boundaries

This slice supplies semantic owners, proposed prerequisite inputs, and possible
gate-effect contexts recovered from v0.4. It does not decide:

- canonical plan membership, dependency edges, `completion_required`, plan
  digest, coverage, overall outcome, exit mapping, or CI status identity (ADR
  0004);
- report/catalog JSON spelling, canonical bytes, or redaction (ADR 0003);
- verified human authority (ADR 0005);
- package, executable, or display naming (ADR 0001); or
- any Issue #43 runtime repair.

The accepted Phase 0 ledger remains byte-for-byte unchanged. A later
parity-projection candidate must bind this catalog decision plus the full ADR
0004 projection, and a later acceptance-only record must bind both before an
implementation may consume them.

## Reconciliation evidence

The candidate was reconciled against independently generated inventories from
the exact source:

- 36 proposed public checks, 113 finding identities, and 41 non-completion
  reasons;
- 243 direct result emitters in 43 functions: 195 error, 16 warning, 32
  success;
- 84 upstream producer branches, including all 50 regression branches;
- 309 closed semantic groups: 198 direct findings, 27 typed non-completions,
  25 legacy success-evidence groups, 24 renderer endpoints, 14 callsite
  dispatches, five callsite-reason dispatches, four variant-and-callsite
  dispatches, five source-predicate dispatches, one context-state promotion,
  and six pre-plan invocation errors;
- all 78 finding leaves with required facts bound by literal, closed source
  predicate, or registered trusted-context contracts;
- 30 direct `Report.emit` returns and eight `report.results` control reads;
- all 41 parser, process, workflow, and provider terminal families; and
- every job, step, guard, dependency, output, and provider-conclusion family
  across five jobs and 36 steps in the two runtime workflows.

Review validation rejects duplicate identifiers, dangling owners or reasons,
uncovered or multiply covered source locators, overlapping mapping predicates,
unregistered targets, and any Phase 0 projection mismatch. Test and workflow
results belong to the named review-candidate checkpoint; they are not encoded
as self-acceptance in these files.
