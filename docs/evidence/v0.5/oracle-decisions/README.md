# Phase 0 oracle decision records

> **FORMAT CANDIDATE — NO ORACLE ACCEPTANCE IS RECORDED HERE**

This directory is the reserved location for separately reviewed Phase 0 oracle
decision records. This README defines an internal decision-record shape and
sequence; it is not a public JSON contract, a verifier, or an acceptance of the
current characterization seed.

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

A narrower decision may accept the semantic ledger revision after step 1 while
recording `implementation_parity_authorized: false`. That decision preserves a
reviewed semantic baseline but does not permit an implementation comparison.
Implementation parity requires steps 2 and 3 and a decision that binds both
the semantic ledger and the complete projection.

An implementation or parity PR cannot establish, update, or supersede the
decision that it consumes. A decision record introduced on the PR head is
ignored as authority even if its fields and hashes are otherwise valid.

The candidate ledger's `status`, `oracle`, `candidate_use`, and
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
- the consumer names one exact `decision_id` and either materializes the bound
  files from their recorded candidate commits or fails unless the bytes at the
  consumed paths match every selected raw hash;
- the decision's case scope and coverage flag are used literally, without
  promoting partial coverage to a complete-Phase-0 or full-parity claim;
- a decision that authorizes implementation parity binds a separately merged
  complete parity projection; semantic-ledger acceptance alone is insufficient;
- the consuming implementation base already contains this exact record; and
- no accepted record has been edited in place.

For a current parity claim, the named record must be terminal for every
selected case: no accepted record already on the base branch may supersede it
for that case. A superseded record may be selected only for explicitly labeled
historical reproduction and cannot satisfy the current required CI gate. There
is no implicit `latest` lookup.

These checks are a review contract until a separately authorized verifier is
implemented. This bounded slice adds no CI consumer.

## Candidate JSON shape

One acceptance-only PR adds a new file named for its stable decision ID, for
example `phase-0-v0.4.0-seven-seed-r1.json`:

```json
{
  "document_kind": "phase0_oracle_decision",
  "format_version": 1,
  "decision_id": "AAP-V05-P0-ORACLE-001",
  "decision": "ACCEPT_SEMANTIC_LEDGER_REVISION",
  "ledger_revision": "v0.4.0-seven-seed-contract-r2-2026-07-21",
  "ledger_shape_revision": "phase0-candidate-2",
  "scope": {
    "coverage_complete": false,
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
  "authority_revision": {
    "repository": "MosslandOpenDevs/agentic-assurance-profile",
    "release": "v0.4.0",
    "commit_sha1": "00e2fe46d4eb01a4147f149851a48a3017cbb796"
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
allocation. Its closed semantic set binds unique internal condition keys,
`EvaluationKind`, gate effect, and overall outcome, but it does not close the
public check plan or bind `GateCoverage`. It therefore cannot support
`implementation_parity_authorized: true`.

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
