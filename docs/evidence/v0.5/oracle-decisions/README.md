# Phase 0 oracle decision records

> **FORMAT CANDIDATE — NO ORACLE ACCEPTANCE IS RECORDED HERE**

This directory is the reserved location for separately reviewed Phase 0 oracle
decision records. This README defines an internal decision-record shape and
sequence; it is not a public JSON contract or an acceptance of the current
characterization seed. The bounded offline verifier described below checks only
repository-object and byte-binding predicates; it cannot grant acceptance.

## Required separation sequence

1. A **semantic-candidate PR** establishes the corpus, manifest, and proposed
   ledger bytes, then merges them to canonical `main`.
2. Before implementation parity, a later **parity-projection candidate PR**
   maps every internal condition to public finding or reason identity and adds
   the complete check/gate comparison projection. It contains no executable or
   allowlist change and merges before the decision that accepts it.
3. A later **acceptance-only PR** adds one decision record that binds the
   earlier candidate commits and exact raw hashes. It does not modify candidate
   material, a parity implementation, or an allowlist.
4. A later **implementation PR** may consume only material whose byte-identical
   decision record is already present on its base branch.

For this internal format, each candidate and acceptance PR must land as an
ordinary Git merge commit with exactly two parents: the final canonical-main
base first and the reviewed PR head second. Squash and rebase merges are
unsupported because they erase that boundary. Repository settings that still
permit those strategies are an external process risk, not a condition this
offline verifier can repair.

A narrower decision may accept the semantic ledger revision after step 1 while
recording `implementation_parity_authorized: false`. That decision preserves a
reviewed semantic baseline but does not permit an implementation comparison.
Implementation parity requires steps 2 and 3 and a decision that binds both
the semantic ledger and the complete projection.

An implementation or parity PR cannot establish, update, or supersede the
decision that it consumes. A decision record introduced on the PR head is
ignored as authority even if its fields and hashes are otherwise valid.

The candidate ledger's `status`, `oracle`, `coverage`, `candidate_use`, and
`acceptance_binding` fields never grant authority. In particular,
`oracle: false`, `implementation_consumable: false`, and
`acceptance_binding: null` remain honest self-non-authorization markers;
effective acceptance comes only from the separate merged decision.

## Effective acceptance predicate

A decision record has effect only when all of the following are true:

- the record arrived through a merged acceptance-only PR on protected canonical
  `main`, under the factual review class recorded in that PR and record;
- `candidate.repository_commit_sha1` is the canonical `main` merge commit of an
  earlier candidate PR, not a branch-only commit or the acceptance PR itself;
- the manifest and ledger at that candidate commit match their recorded raw
  SHA-256 values, and the manifest yields the recorded corpus digest;
- `ledger_revision` exactly equals the bound candidate ledger's
  `proposed_ledger_revision`; neither identifier grants authority by itself;
- `decision_authority_revision` binds the `GOVERNANCE.md` revision effective on
  the acceptance-only PR's final base by repository, commit, path, locator, and
  raw SHA-256, and the recorded governing body and factual review classes
  satisfy that revision;
- the consumer names one exact `decision_id` and either materializes the bound
  files from their recorded candidate commits or fails unless the bytes at the
  consumed paths match every selected raw hash;
- the decision's case scope and three coverage axes are used literally, without
  promoting selected-case semantic completeness to complete Phase 0 or to a
  complete implementation-parity projection;
- a decision that authorizes implementation parity binds a separately merged
  complete parity projection; semantic-ledger acceptance alone is insufficient;
- the consuming implementation base already contains this exact record; and
- no accepted record has been edited in place, deleted, or made to look new by
  reintroducing its path after deletion. The selected path must have no earlier
  use on the acceptance base's first-parent history.

For a current parity claim, the named record must be terminal for every
selected case: no accepted record already on the base branch may supersede it
for that case. A superseded record may be selected only for explicitly labeled
historical reproduction and cannot satisfy the current required CI gate. There
is no implicit `latest` lookup.

The repository's internal offline verifier mechanizes only the bounded subset
described below. The external authority predicates remain a review contract,
and no operational acceptance or parity CI consumer is added. Regression CI
does check that the committed candidate artifacts remain component-compatible
with the internal verifier; that check grants no authority.

## Slice 3 offline binding verifier

Slice 3 adds a Python-standard-library-only internal verifier for one explicitly
named semantic decision. A representative invocation is:

```bash
python -I scripts/verify_phase0_acceptance.py \
  --repo-root /path/to/repository \
  --expected-repository MosslandOpenDevs/agentic-assurance-profile \
  --consumer-base <40-lowercase-sha> \
  --decision-commit <40-lowercase-sha> \
  --decision-id AAP-V05-P0-ORACLE-001 \
  --decision-path docs/evidence/v0.5/oracle-decisions/<record>.json \
  --format json
```

The verifier uses the local Git object database only. Its Git subprocesses run
with a sanitized repository environment and `GIT_NO_LAZY_FETCH=1`; inherited
Git-directory, worktree, object-directory, alternate-object, and configuration
overrides cannot redirect the inspection. It does not fetch, read candidate or
decision bytes from the worktree or index, or select an implicit latest
decision. Missing objects, shallow history, unsafe or ambiguous paths, parse
failures, and binding mismatches are controlled failures rather than permission
to fall back to current files.

The `local_observations` fields `verifier_executable_path`,
`git_executable_path`, `git_version`, and `repository_root` are diagnostics,
not provenance. The
verifier and Git executable provenance, local repository origin, and authority
of the caller's expected-repository argument remain unverified preconditions. A
successful run must not promote those observations into a trust claim. JSON
names them under `unverified_preconditions` as
`verifier-executable-provenance`, `git-executable-provenance`,
`local-repository-origin`, and `expected-repository-argument-authority`.

The selected decision path must be introduced for the first time by the named
acceptance merge. A path that appeared earlier on the acceptance base's
first-parent history remains used even if an intervening commit deleted it;
deletion and reintroduction cannot reset record identity. The stable
`decision_id` likewise must not occur in any earlier decision-directory tree,
even under another path. After acceptance, no first-parent commit through the
consumer base may touch the selected path; restoring the same endpoint bytes
does not erase an intermediate edit or deletion.

The canonical decision-record set is append-only: any first-parent modification,
deletion, rename, or Git object-type change of a direct decision-directory JSON
record fails closed.
That invariant plus the current-tree duplicate-ID check prevents historical ID
reuse without selecting an implicit latest record. History walks ignore both
replacement refs and repository-local grafts and reject shallow repositories.

Git subprocesses have a timeout and parsed object/tree results receive
post-output count and size checks. Slice 3 does not yet implement a streaming
byte cap on Git stdout, however. A repository with an adversarially huge object
database is outside this internal slice's supported boundary: the verifier MUST
NOT be used as an authoritative CI gate or public verifier until a separately
reviewed hardening change adds that bound.

Exit status `0` means only that the implemented offline object and binding
predicates were verified. JSON success therefore reports
`"offline_binding":"VERIFIED"` together with
`"effective_acceptance":"NOT_ESTABLISHED"` and
`"implementation_parity_authorized":false`. Text success begins with
`OFFLINE BINDING VERIFIED; EFFECTIVE ACCEPTANCE NOT ESTABLISHED`. Exit `1`
means a controlled missing, mismatch, or unsupported condition; command-line
usage errors retain `argparse` exit `2`.

In particular, the verifier does not establish that the decision arrived on
protected canonical `main`, that the named GitHub pull request was the actual
acceptance-only change, that the recorded decision maker is a human, or that
the factual review classes are authentic. JSON lists these as
`unverified_external_predicates`, using the stable internal names
`protected-canonical-main`, `github-acceptance-pr-state`,
`factual-human-decision-maker`, and `factual-review-classes`. Green automation
or exit `0` cannot upgrade any of them.

It also does not establish the semantic validity of the ledger's authority
references or the factual published-release, GitHub release-PR, and release
workflow state they describe. JSON records these under
`unverified_authority_predicates` as
`semantic-authority-reference-validity`, `published-release-tag-state`,
`github-release-pr-state`, and `github-release-workflow-run-state`. Completing
the authority graph, adding an
aggregate resource budget, and separating binding failure from verifier
indeterminacy in a stable exit taxonomy are deferred requirements before any
authoritative consumer or CI gate.

The Slice 3 implementation accepts only the semantic-only, non-successor shape:
`decision = ACCEPT_SEMANTIC_LEDGER_REVISION`,
`supersedes_decision_id = null`, `successor_change = null`,
`parity_projection = null`, and `implementation_parity_authorized = false`.
An `accepted: true` field or self-reported `status: ACCEPTED` switch is invalid
and cannot affect the result.
Successor selection, public mapping, implementation parity, effective authority
verification, and CI-gate consumption remain outside this slice.

## Candidate JSON shape

One acceptance-only PR adds a new file named for its stable decision ID, for
example `phase-0-v0.4.0-seven-seed-r1.json`:

```json
{
  "document_kind": "phase0_oracle_decision",
  "format_version": 1,
  "decision_id": "AAP-V05-P0-ORACLE-001",
  "decision": "ACCEPT_SEMANTIC_LEDGER_REVISION",
  "ledger_revision": "v0.4.0-seven-seed-contract-r3-2026-07-21",
  "ledger_shape_revision": "phase0-candidate-3",
  "scope": {
    "coverage": {
      "phase0_matrix_complete": false,
      "semantic_projection_complete_for_selected_cases": true,
      "implementation_projection_complete_for_selected_cases": false
    },
    "case_ids": [
      "archived-reviewed-pass",
      "central-self-check-pass",
      "core-lite-draft-pass",
      "core-split-draft-pass",
      "drift-routing-strict-block",
      "transition-stage-downgrade-block",
      "trust-path-traversal-block"
    ]
  },
  "candidate": {
    "repository": "MosslandOpenDevs/agentic-assurance-profile",
    "repository_commit_sha1": "<prior-canonical-main-merge-sha1>",
    "manifest": {
      "path": "tests/characterization/v0.4.0/manifest.json",
      "raw_sha256": "<raw-manifest-sha256>"
    },
    "ledger": {
      "path": "tests/characterization/v0.4.0/expected-outcomes.json",
      "raw_sha256": "<raw-ledger-sha256>"
    },
    "corpus_sha256": "<verified-corpus-sha256>"
  },
  "reference_release_decision": {
    "repository": "MosslandOpenDevs/agentic-assurance-profile",
    "release": "v0.4.0",
    "annotated_tag_object_sha1": "1373d963a098e13d2f44891e58ee8a47e285c5c3",
    "commit_sha1": "00e2fe46d4eb01a4147f149851a48a3017cbb796",
    "release_pr_url": "https://github.com/MosslandOpenDevs/agentic-assurance-profile/pull/44",
    "release_pr_head_sha1": "6e9d7af921f1539dfbad6ad53812e313158c6289",
    "pull_request_workflow_run_id": 29720585318,
    "recorded_review_classes": {
      "human": "SOLE_OWNER_ATTESTED",
      "automation": "AUTOMATION_VERIFIED"
    }
  },
  "decision_authority_revision": {
    "repository": "MosslandOpenDevs/agentic-assurance-profile",
    "commit_sha1": "<acceptance-pr-final-base-sha1>",
    "path": "GOVERNANCE.md",
    "locator": "§§1–2",
    "raw_sha256": "<raw-governance-sha256>"
  },
  "parity_projection": null,
  "implementation_parity_authorized": false,
  "decision_record": {
    "pr_url": "<acceptance-only-pr-url>",
    "governing_body": "MosslandOpenDevs maintainers",
    "decision_maker": "<factual-human-decision-maker>",
    "human_review_class": "SOLE_OWNER_ATTESTED",
    "automation_review_class": "AUTOMATION_VERIFIED"
  },
  "supersedes_decision_id": null,
  "successor_change": null,
  "compatibility_impact": "none"
}
```

The record deliberately has no `accepted: true` or self-reported
`status: ACCEPTED` switch. The decision text is effective only through the
predicate above: exact bytes plus the durable merge of the separate decision
PR.

## Parity-projection gate

The current seven-seed candidate intentionally stops before public code
allocation. Its catalog gives every provisional key a bounded semantic meaning
and authority, and its closed semantic set binds `EvaluationKind`, gate effect,
and a selected-case `SATISFIED|BLOCKED` result. That result is not
`OverallOutcome`: the candidate does not close the public check plan or bind
`GateCoverage` or `GatePlanIdentity`. It therefore cannot support
`implementation_parity_authorized: true`.

The `condition_catalog` key set must equal the union of every
`required_satisfied_condition_key` and every finding `condition_key`. Each key
has one kind, one bounded statement, and structured authority references. A
required-satisfied statement is limited to the selected listed requirements and
never means that an unlisted check completed or that the public gate passed.

A later `AUTHORIZE_IMPLEMENTATION_PARITY` decision must replace
`parity_projection: null` with a binding to an earlier canonical commit, path,
raw SHA-256, and mapping revision. The separately reviewed projection must
cover every selected case and bind:

- each internal condition to a stable finding code or check reason code;
- owning public `check_id`, `completion_required`, evaluated severity, gate
  effect, and relevant source;
- applicability, completion, outcome, `reason_code`, and `blocked_by`;
- `EvaluationKind`, `GateCoverage`, `GatePlanIdentity`, public dependency
  edges, overall outcome, and exit class; and
- uniqueness or multiplicity for every compared semantic instance.

That mapping/projection candidate cannot contain the implementation that will
be tested against it. Its acceptance decision must already be on the
implementation base and must bind the semantic decision ID plus the projection
commit, path, and raw hash. This slice allocates no public code and records no
such binding.

## Consumer byte selection

Loading the current files merely because a historical decision named the same
paths is invalid. A consumer must name the decision ID and then either:

1. materialize the manifest, ledger, corpus, and projection from the exact
   commits bound by that decision; or
2. read them from its base tree only after recomputing and matching every bound
   raw hash and corpus digest.

If a later unaccepted edit occupies one of those paths, option 2 fails closed;
it does not inherit the older decision. A consumer also cannot combine a
ledger from one decision with a projection or allowlist from another unless a
later accepted decision explicitly binds that exact combination.

## Review classes and authority

`human_review_class` is exactly one factual class from `GOVERNANCE.md`:
`INDEPENDENTLY_REVIEWED` or `SOLE_OWNER_ATTESTED`. `automation_review_class`
is recorded separately because automation and external technical review do not
become human approval.

The acceptance record must bind the exact governance revision that governed
its decision. The `reference_release_decision` for a v0.4.0 expectation is
separate: for the central self-check seed, the accepted operational source is
the annotated v0.4.0 release decision, release PR #44, and its successful
pull-request workflow run 29720585318. The workflow definition is only the
mechanism and supporting context; it cannot authorize its own passing result.

With the current sole-maintainer project, an owner decision remains
`SOLE_OWNER_ATTESTED` unless a different human maintainer actually submits an
approving review. An agent-authored change, AI review, second account, or green
CI must not be recorded as `INDEPENDENTLY_REVIEWED`.

This internal Phase 0 binding does not resolve the general public
human-authority provenance ADR described in `docs/V0.5-DESIGN.md` §14.5. It
records repository decision provenance only and makes no claim about external
identity, credential custody, or human presence.

## Immutability and successors

An effective decision record is immutable. A correction, expanded scope,
changed expectation, `KNOWN_BUG` or `INTENDED_CHANGE` classification, or
allowlist change requires:

1. a new candidate change when candidate bytes must change;
2. a new acceptance-only PR and filename;
3. a new stable `decision_id` and `ledger_revision`; and
4. `supersedes_decision_id` pointing to the prior decision, with the affected
   fixtures, old and new outcomes, authority, review class, rationale, and
   compatibility impact recorded in that successor change.

When `supersedes_decision_id` is non-null, `successor_change` is also non-null
and has at least this shape:

```json
{
  "affected_case_ids": ["<case-id>"],
  "old_expected_outcomes": {"<case-id>": "<old-semantic-projection>"},
  "new_expected_outcomes": {"<case-id>": "<new-semantic-projection>"},
  "authority_refs": ["<pinned-authority-ref>"],
  "rationale": "<why-the-successor-is-authorized>",
  "compatibility_impact": "<none-or-described-impact>"
}
```

Those placeholder strings show required information, not a public schema; the
accepted record must contain the actual bounded projections and structured
authority references.

The earlier record and candidate bytes remain in history and are never edited
to make an implementation pass.
