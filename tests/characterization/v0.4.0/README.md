# v0.4.0 characterization seed

> **SCAFFOLD — NOT ACCEPTED — NOT AN ORACLE — PHASE-0 MATRIX INCOMPLETE**

This directory is the first bounded seed for v0.5 Phase 0. It records seven
small, deterministic candidate input shapes and a *proposed* interpretation of
their outcomes. It does not complete Phase 0 or issue #49, authorize a parity
exception, define a public JSON contract, or establish stable finding/check
identifiers.

No validator, workflow, schema, template, acceptance gate, or parity test
consumes these files. Slice 3 regression CI checks only that the committed
manifest, ledger, and local corpus roots remain component-compatible with the
internal verifier. The verifier itself may read bound Git-object bytes only to
check repository and hash bindings; neither path evaluates the expectations,
grants acceptance, or authorizes implementation parity. The v0.4.0 executable
is comparison evidence, not the authority for the proposed expectations.

## The three separate artifacts

1. `cases/` contains immutable-input candidates. The manifest also names the
   exact v0.4.0 Git tree used by central self-check.
2. `manifest.json` describes how to hash and invoke those candidates. Its
   pre-acceptance shape is internal scaffolding and may change before acceptance.
3. `expected-outcomes.json` keeps proposed semantic expectations, pinned
   authority, evidence-only legacy matchers, and observed v0.4.0 results in
   separate fields.

A file cannot grant itself review authority. A later, separate owner decision
must bind an exact repository commit, raw `manifest.json` SHA-256, raw
`expected-outcomes.json` SHA-256, and actual governance review classes before
the semantic ledger revision can be accepted. Its `ledger_revision` must
exactly equal the candidate's `proposed_ledger_revision`, and it must bind the
`GOVERNANCE.md` revision effective on the acceptance-only PR's final base. That
decision alone does not authorize implementation parity: the public mapping
and complete parity projection described below must also be proposed and
accepted separately. A correction must create a successor; it must not silently
rewrite accepted bytes. The candidate decision-record format and
anti-self-approval sequence are defined in
[the oracle-decision README](../../../docs/evidence/v0.5/oracle-decisions/README.md).

## Candidate ledger boundary

Each `semantic_expectation` records the proposed `EvaluationKind`, a bounded
selected-case `SATISFIED|BLOCKED` result, any required satisfied internal
conditions, and an exact closed set of semantic findings. The bounded result is
not the run-level `OverallOutcome`: no complete gate plan, `GateCoverage`, or
`GatePlanIdentity` is bound. `closed: true` means an unordered comparison with
unique `condition_key` values: every listed finding occurs exactly once and any
unlisted or duplicate semantic finding rejects the comparison. It does not make
the v0.4.0 diagnostic count or prose part of the contract. For example, the two
legacy errors observed for the trust-path seed collapse to one proposed
repository-containment condition.

Every listed satisfied-condition key must likewise occur exactly once. That
positive list is not a closed check plan and cannot prove that an unlisted
check completed. This candidate deliberately does not yet bind evaluated
severity, public `check_id`, `completion_required`, the three check-state axes,
`reason_code`, `blocked_by`, `GateCoverage`, public dependency edges, or
`GatePlanIdentity`. Consequently it is a semantic seed, not an
implementation-consumable parity projection.

The neighboring `legacy_reference_matcher` is explicitly `evidence_only`. Its
numeric process exit, level, bounded message substring, and traceback checks
describe how the pinned v0.4.0 executable was recognized. They cannot define
the successor engine's finding set or renderer wording.

Keys under `phase0.internal.*` are provisional corpus identifiers. The ledger's
top-level `condition_catalog` fixes each key's bounded meaning, kind, and
authority so a later mapping cannot redefine it. Its key set is exactly the
union of every required-satisfied key and every finding key used by the entries;
positive statements cover only selected requirements and cannot imply complete
gate execution. The keys are not public
`finding_code`, `check_id`, or `reason_code` values. A later public-code mapping
and the missing check/gate projection are required before implementation
parity. They must be merged as non-executable candidate material and accepted
by a separate decision already present on an implementation change's base
branch; an implementation PR cannot create its own mapping. They also must not
silently rewrite an accepted ledger revision.

Every `authority_ref` resolves through a named `authority_source` pinned to an
exact commit. `NORMATIVE`, `ACCEPTED_COMPATIBILITY`, and
`ACCEPTED_OPERATIONAL` references can ground an expectation in their declared
scope. `SUPPORTING_CONTEXT` explains mechanics but cannot authorize an
expectation by itself. The authority commit is not an oracle acceptance
binding; those are deliberately separate controls.

The central self-check condition uses the annotated v0.4.0 release decision and
release PR #44 as `ACCEPTED_OPERATIONAL` authority. They record the canonical
release commit, a passing self-check, and the factual
`SOLE_OWNER_ATTESTED + AUTOMATION_VERIFIED` classes. The workflow itself is
`SUPPORTING_CONTEXT`: it is the mechanism and cannot authorize its own result.

The ledger reports coverage on three independent axes. The Phase 0 fixture
matrix is incomplete; the semantic projection is complete for the seven
selected cases; and the implementation projection for those cases is
incomplete. The manifest's older `coverage_complete: false` field denotes only
the incomplete Phase 0 input matrix; it does not summarize the semantic or
implementation-projection axes. None of those fields self-authorizes the
candidate.

## Seed coverage

| Case | Covers | Deliberately does not prove |
|---|---|---|
| `core-split-draft-pass` | active core, split, default mappings, implicit DRAFT | specialized profiles or later stages |
| `core-lite-draft-pass` | active core, lite, implicit DRAFT | lite migration or specialized profiles |
| `archived-reviewed-pass` | archived, split, explicit system mapping, HUMAN_REVIEWED | truth of archived facts or forge review authenticity |
| `transition-stage-downgrade-block` | base/head declaration regression | full register-transition matrix |
| `trust-path-traversal-block` | lexical repository-boundary failure | symlink/retarget and every trust root |
| `drift-routing-strict-block` | component routing with strict escalation | workflow event applicability from #43 |
| `central-self-check-pass` | release-decision-backed central self-check on the exact v0.4.0 tagged tree | real dogfood adoption or adopter usability |

Still missing from #49 are, at minimum: the current/legacy matrix, specialized
split profiles, full stage ladder, default/explicit mapping cross-product,
symlink and retarget cases, malformed and resource-bound failures, a real
dogfood adopter distinct from central self-check, two end-to-end adoption
trials, usability measures, and the #43 applicability/completion contract.
These fixtures are engine test data, not adoption trials.

## Reproduction boundary

The reference is the peeled release commit
`00e2fe46d4eb01a4147f149851a48a3017cbb796`, not the annotated tag object and
not current `main`. Materialize that commit as a clean detached worktree and
use its `scripts/validate.py`, `requirements-ci.txt`, schemas, and templates.
This execution identity is separate from release authority provenance, which
also binds the annotated tag object and release PR #44.
Install only the hash-locked dependencies from that worktree. Run with an
environment that removes `GITHUB_ACTIONS` and `GITHUB_STEP_SUMMARY` so GitHub
annotations do not change the selected observation.

Invocation arrays in `manifest.json` use only these symbolic roots:

- `@profile`: the clean detached v0.4.0 worktree;
- `@corpus`: this directory;
- `@python`: the selected CPython executable with the locked dependencies.

They are documentation, not an executable fixture DSL. Substitute each token
as one argv element; do not evaluate the arrays through a shell. The selected
observation is exit status plus bounded level/message predicates. Absolute
temporary paths and whole stdout hashes are intentionally not parity claims.

## Digest algorithm

Each `root_record` in the manifest covers one input tree. Digest format v1
enumerates it exclusively from Git objects already present in the repository:
a `corpus_directory` beneath its path in the bound candidate commit, or the
exact commit and tree named by a `git_commit` source. It does not enumerate a
worktree or index. Reject symlinks, covered file entries that are not blobs,
absolute paths, `.`/`..` components, duplicate paths, and paths outside the
declared root.

For each tree, create records with `path` (POSIX relative path), byte `size`,
and lowercase raw-byte `sha256`. Digest format v1 accepts ASCII `path` values
only and sorts their encoded ASCII bytes lexicographically. It performs no
locale collation, case folding, or Unicode normalization. Serialize the array
as UTF-8 JSON with ASCII escaping, sorted object keys, and separators `,` and
`:` with no trailing newline. The SHA-256 of those bytes is `tree_sha256`.

For `corpus_sha256`, create records containing only `root_id` and the verified
`tree_sha256`. Digest format v1 likewise accepts ASCII `root_id` values only and
sorts their encoded ASCII bytes lexicographically before serializing and
hashing with the same rules. The manifest, ledger, and this README are excluded,
so the aggregate has no self-reference. Acceptance later binds the raw manifest
and ledger hashes separately.

For the Slice 3 verifier, every covered file must be a Git blob with mode
`100644`. Any executable, symlink, submodule, or other mode is unsupported and
fails closed. A `corpus_directory` is enumerated beneath its path in the bound
candidate commit; a `git_commit` root is enumerated from the exact commit and
tree named by the manifest. All bytes come from objects already present in the
repository's Git object database. The verifier performs no fetch or checkout
and does not read the worktree, index, untracked files, or filesystem modes.
It sanitizes inherited Git repository/object/configuration overrides and sets
`GIT_NO_LAZY_FETCH=1`. Missing objects and tree/object identity mismatches are
controlled failures. A decision path must have no earlier use on the
acceptance base's first-parent history, so deletion and reintroduction cannot
make an old record appear newly accepted. Historical reuse of the same stable
decision ID under another path is also rejected. No first-parent commit after
acceptance may touch the selected record, even if the consumer endpoint restores
the original bytes or round-trips through another Git object type. Replacement
refs and local grafts are ignored; shallow or non-append-only decision history
fails closed.

## Offline binding verification boundary

The internal command and its exact exit semantics are documented in
[the oracle-decision README](../../../docs/evidence/v0.5/oracle-decisions/README.md#slice-3-offline-binding-verifier).
Its success state is only `offline_binding = VERIFIED`; effective acceptance
remains `NOT_ESTABLISHED`. It supports semantic-only decisions with no
successor and no parity projection, authenticates no external human or GitHub
authority predicate, and is not a CI consumer. Self-reported `accepted: true`
or `status: ACCEPTED` fields are invalid and cannot upgrade that result.

Candidate and acceptance boundaries require ordinary exactly-two-parent merge
commits; squash and rebase merges are unsupported even if repository settings
permit them. Reported Git executable/version and repository-root identities are
diagnostic observations; verifier/Git provenance, repository origin, and the
authority of the expected-repository argument are not established.
Authority-reference semantics and the factual published-release, GitHub
release-PR, and workflow state remain unverified. Full authority-graph
verification, aggregate resource budgeting, and a stable
failure-versus-indeterminate exit taxonomy are required before an authoritative
consumer.

The current internal implementation applies Git subprocess timeouts and checks
tree counts and sizes after output is returned, but it has no streaming Git
stdout byte cap. Adversarially huge object databases therefore remain
unsupported; authoritative CI or public use requires a separately reviewed
resource-bound hardening change first.

## Review checklist before any acceptance

- strict-parse both JSON documents with duplicate-key rejection;
- prove the seven manifest and ledger case IDs form a bijection;
- independently recalculate every tree and corpus digest, file count, and byte
  count, with no missing or extra input bytes;
- reproduce observations with the pinned executable in two fresh temp roots;
- verify each proposed expectation cites PROFILE or an already accepted
  compatibility/release decision rather than the executable's current output;
- confirm every entry keeps authority-backed semantic expectations separate
  from evidence-only legacy matchers and closes the semantic finding set
  with unique condition keys, without freezing complete v0.4.0 prose or raw
  diagnostic counts;
- confirm the condition catalog exactly closes over every used key, gives each
  key one bounded authority-backed meaning, and limits positive statements to
  selected requirements;
- review the three coverage axes independently and do not promote selected-case
  semantic completeness to complete Phase 0 or implementation parity;
- confirm every authority reference resolves at its pinned revision and review
  the separately versioned acceptance decision that binds the candidate commit
  and raw manifest/ledger hashes, matches `proposed_ledger_revision`, and binds
  the governance revision effective on its final base;
- before implementation parity, separately merge and accept the public mapping
  plus complete check/gate projection, then verify that both decisions and the
  exact bound bytes are already present on the implementation base;
- confirm v1 ASCII byte collation, `100644`-only Git-object coverage, and the
  no-fetch/no-worktree boundary; separately define supported-runtime replay
  requirements before any verifier treats the data as an accepted parity
  oracle;
- run central self-check, the full regression suite, Markdown-link checks, and
  `git diff --check`;
- record the final head and actual governance review classes outside these files.
