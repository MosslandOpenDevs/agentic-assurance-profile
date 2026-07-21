# v0.4.0 characterization seed

> **SCAFFOLD — NOT ACCEPTED — NOT AN ORACLE — COVERAGE INCOMPLETE**

This directory is the first bounded seed for v0.5 Phase 0. It records seven
small, deterministic candidate input shapes and a *proposed* interpretation of
their outcomes. It does not complete Phase 0 or issue #49, authorize a parity
exception, define a public JSON contract, or establish stable finding/check
identifiers.

No validator, workflow, schema, template, CI job, or test assertion consumes
these files. The v0.4.0 executable is comparison evidence, not the authority
for the proposed expectations.

## The three separate artifacts

1. `cases/` contains immutable-input candidates. The manifest also names the
   exact v0.4.0 Git tree used by central self-check.
2. `manifest.json` describes how to hash and invoke those candidates. Its
   pre-acceptance shape is internal scaffolding and may change before acceptance.
3. `expected-outcomes.json` keeps proposed expectations, normative or accepted
   compatibility authority, and observed v0.4.0 results in separate fields.

A file cannot grant itself review authority. A later, separate owner decision
must bind an exact repository commit, raw `manifest.json` SHA-256, raw
`expected-outcomes.json` SHA-256, and actual governance review classes before
either document becomes an accepted parity oracle. A correction must create a
successor; it must not silently rewrite accepted bytes.

## Seed coverage

| Case | Covers | Deliberately does not prove |
|---|---|---|
| `core-split-draft-pass` | active core, split, default mappings, implicit DRAFT | specialized profiles or later stages |
| `core-lite-draft-pass` | active core, lite, implicit DRAFT | lite migration or specialized profiles |
| `archived-reviewed-pass` | archived, split, explicit system mapping, HUMAN_REVIEWED | truth of archived facts or forge review authenticity |
| `transition-stage-downgrade-block` | base/head declaration regression | full register-transition matrix |
| `trust-path-traversal-block` | lexical repository-boundary failure | symlink/retarget and every trust root |
| `drift-routing-strict-block` | component routing with strict escalation | workflow event applicability from #43 |
| `central-self-check-pass` | exact v0.4.0 tagged repository tree | real dogfood adoption or adopter usability |

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

Each `root_record` in the manifest covers one input tree. For a working-tree
root, recursively enumerate every regular file beneath the declared directory.
For the Git reference root, enumerate every tracked blob in the exact commit.
Reject symlinks, non-regular entries, absolute paths, `.`/`..` components,
duplicate paths, and paths outside the declared root.

For each tree, create records with `path` (POSIX relative path), byte `size`,
and lowercase raw-byte `sha256`; sort by `path`. Serialize the array as UTF-8
JSON with ASCII escaping, sorted object keys, and separators `,` and `:` with
no trailing newline. The SHA-256 of those bytes is `tree_sha256`.

For `corpus_sha256`, create records containing only `root_id` and the verified
`tree_sha256`, sort by `root_id`, and serialize/hash with the same rules. The
manifest, ledger, and this README are excluded, so the aggregate has no
self-reference. Acceptance later binds the raw manifest and ledger hashes
separately.

## Review checklist before any acceptance

- strict-parse both JSON documents with duplicate-key rejection;
- prove the seven manifest and ledger case IDs form a bijection;
- independently recalculate every tree and corpus digest, file count, and byte
  count, with no missing or extra input bytes;
- reproduce observations with the pinned executable in two fresh temp roots;
- verify each proposed expectation cites PROFILE or an already accepted
  compatibility/release decision rather than the executable's current output;
- run central self-check, the full regression suite, Markdown-link checks, and
  `git diff --check`;
- record the final head and actual governance review classes outside these files.
