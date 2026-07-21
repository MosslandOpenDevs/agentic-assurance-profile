# v0.5 Phase 0 evidence log

> **SCAFFOLD — NOT ACCEPTED — NOT AN ORACLE — COVERAGE INCOMPLETE**

This log records the bounded Phase 0 slices of issue #49. It does not mark Phase
0 complete, supply a G1 decision, or count static engine fixtures as adoption
trials.

## Slice decisions

### Slice 1 — deterministic seed

The owner recorded the `START` decision in
[#49's bounded-slice kickoff](https://github.com/MosslandOpenDevs/agentic-assurance-profile/issues/49#issuecomment-5028818203):

- working base: `main@4ecf81cbe161281652fd543abc15d270f8656e18`;
- reference: `v0.4.0@00e2fe46d4eb01a4147f149851a48a3017cbb796`;
- effort cap: four elapsed working hours, not increasable while active;
- stop if fixture determinism requires behavior changes, the ledger becomes a
  new normative source/public contract, or the slice cannot fit the cap;
- output: a Draft PR, with any expansion requiring a new reviewed decision.

No stop condition authorized a scope expansion. Slice 1 changed only
documentation and inert characterization data and merged in PR #60.

### Slice 2 — oracle contract hardening

After PR #60, the owner recorded a second `START` decision in
[#49's contract-hardening kickoff](https://github.com/MosslandOpenDevs/agentic-assurance-profile/issues/49#issuecomment-5030095573):

- working base: `main@e328535113f621e12351ee9d7eb97f629f5d007a`;
- effort cap: four elapsed working hours, not increasable while active;
- scope: semantic/legacy separation, closed semantic finding sets, pinned
  authority references, and the external acceptance-record boundary;
- non-scope: actual oracle acceptance, executable or CI changes, public codes,
  new fixtures, trials, runtime replay, and #43; and
- output: a Draft PR, with each later expansion requiring a new reviewed
  decision.

Slice 2 changes the proposed interpretation contract, not the frozen inputs or
the v0.4.0 observations. `oracle: false`, `implementation_consumable: false`,
and `acceptance_binding: null` remain.

## Reference identity

| Item | Identity |
|---|---|
| annotated tag object | `1373d963a098e13d2f44891e58ee8a47e285c5c3` |
| peeled release commit | `00e2fe46d4eb01a4147f149851a48a3017cbb796` |
| validator Git blob | `af5f7c39373f6dc6ced93d437cec4b972851e3a3` |
| requirements Git blob | `1fbebbbb08277b81307439866de067ebd224515b` |

The executable was run from a clean detached worktree at the peeled commit.
Current `main` was not substituted for the reference. The locked environment
used CPython 3.14.6, PyYAML 6.0.3, and jsonschema 4.26.0 installed with
`pip --require-hashes` from the release's `requirements-ci.txt`.
This is one reference observation environment, not evidence of parity across
the repository's Python CI matrix, operating systems, or architectures.

Candidate identities at the observed head are:

| Candidate | SHA-256 |
|---|---|
| corpus aggregate | `cb9710c7b27350e11b69450d8d4cc6bb95f0d8adb3e37ae474d3512d64d6a293` |
| raw `manifest.json` | `4cd135234698b47c9b4444ca0cb00121b1da872ff8abf4ac9ccf32015009387b` |
| raw proposed `expected-outcomes.json` | `8161327deb5b605eede377414bc6b1646922ea454f5050f5d6d12c5d7858270c` |

These are candidate byte identities, not an acceptance binding. The ledger
contains the manifest hash, while neither candidate contains its own hash.

## Seed observations

Reference execution recorded only observed exit status, level counts, empty
stderr, and selected bounded predicates. They now live in evidence-only legacy
matcher and observation fields, separate from the authority-backed semantic
proposals in `expected-outcomes.json`.

| Case | Reference observation | Interpretation status |
|---|---|---|
| `core-split-draft-pass` | exit 0; 12 ok, 0 warn, 0 error | proposed, not accepted |
| `core-lite-draft-pass` | exit 0; 12 ok, 0 warn, 0 error | proposed, not accepted |
| `archived-reviewed-pass` | exit 0; 9 ok, 1 warn, 0 error | proposed, not accepted |
| `transition-stage-downgrade-block` | exit 1; 0 ok, 0 warn, 1 error | proposed, not accepted |
| `trust-path-traversal-block` | exit 1; 11 ok, 0 warn, 2 errors | proposed, not accepted |
| `drift-routing-strict-block` | exit 1; 0 ok, 0 warn, 1 error | proposed, not accepted |
| `central-self-check-pass` | exit 0; 25 ok, 0 warn, 0 error | proposed, not accepted |

The seven invocations were repeated from two independently copied fresh corpus
roots. Exit status, level counts, stderr-empty state, and the selected bounded
predicates described above were identical in both runs. No separate
reference-observation projection serialization or digest is claimed. This
comparison establishes reproducibility of those selected fields only; it does
not make the v0.4.0 behavior correct.

The proposed semantic contract binds `EvaluationKind`, overall outcome, and an
exact unordered finding set with unique condition keys, without copying raw
diagnostic cardinality. In particular, the trust-path case's two legacy errors
map to one repository-containment condition. Internal `phase0.internal.*` keys
are corpus identifiers, not public finding/check/reason codes.

The candidate does not close unlisted check state or bind public codes,
evaluated severity, complete check state, `GateCoverage`, plan identity, or
dependency edges. It is therefore a semantic seed, not an
implementation-consumable parity projection. Those missing fields require
separately merged candidate material and a separate acceptance decision before
implementation work may consume them.

## Remaining evidence before #49 can close

The seven seeds do not yet supply a complete fixture matrix, an accepted
manifest/ledger binding, a real dogfood adopter, either required end-to-end
trial, independent operator evidence, usability metrics, or the #43 event
contract. External usability evidence remains `UNKNOWN`; this scaffold makes
no claim that v0.4.0 is easy or difficult to adopt.

A later acceptance record must live outside the candidate files and bind the
exact commit plus raw manifest and ledger SHA-256 values and the actual review
classes. Semantic-ledger acceptance alone cannot authorize implementation
parity. The public mapping and complete parity projection must first merge as
non-executable candidate material, then a separate decision must bind both.
The format and byte-selection rules are documented in
[the oracle-decision README](oracle-decisions/README.md). Until that complete
decision is already present on an implementation PR's base branch, the PR may
not use this seed as an oracle or rewrite its mapping or expectations to approve
its own difference.
