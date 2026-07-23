# Diagnostic catalog acceptance decisions

> **INTERNAL REPOSITORY DECISION DATA — NOT A PUBLIC OR RUNTIME CONTRACT**

This directory is reserved for append-only decisions about the diagnostic
catalog candidate under
[`../`](../). Its record shape is local review infrastructure. It does not
define the public catalog/report JSON owned by ADR 0003, a canonical digest,
an adopter-facing schema, or a runtime acceptance switch.

The candidate preserved by PR
[#66](https://github.com/MosslandOpenDevs/agentic-assurance-profile/pull/66)
cannot accept itself. Its `acceptance_binding: null`,
`implementation_parity_authorized: false`, and `runtime_ready: false` values
remain unchanged. An effective decision is a separate repository act over the
exact candidate bytes; changing those candidate fields would not create that
act.

## Required sequence

The sequence is deliberately verifier-first:

1. A contract/verifier change defines and tests this closed internal format. It
   adds no decision record and grants no acceptance.
2. That change merges to canonical `main`.
3. A later acceptance-only pull request, based on that merge, adds exactly one
   direct child JSON file to this directory. It changes no verifier, candidate
   artifact, allowlist, workflow, validator, schema, template, profile, or
   runtime code.
4. A human owner reviews one exact acceptance-PR head and records the actual
   process facts outside the candidate JSON. The pull request must merge as an
   ordinary merge commit with exactly two parents: its final canonical-main
   base first and the reviewed head second.
5. A later consumer names the exact record ID, path, and decision merge already
   present on its base. A record introduced or changed by the consuming head
   has no authority.

There is no implicit `latest` record and no acceptance inferred from directory
contents, file names, current worktree bytes, green CI, or verifier exit zero.

## Closed record shape

Version 1 is one strict JSON object with exactly these top-level members:

```json
{
  "document_kind": "diagnostic_catalog_acceptance_decision",
  "internal_format_version": 1,
  "record_id": "AAP-V05-DIAGNOSTICS-ACCEPTANCE-001",
  "subject_decision_id": "AAP-V05-DIAGNOSTICS-001",
  "decision": "ACCEPT_FOUNDATION_DIAGNOSTIC_BASELINE",
  "verifier_contract": {},
  "subject": {},
  "scope": {},
  "authority_basis": {},
  "repository_process": {},
  "predecessor": null,
  "successor_change": null
}
```

Unknown or duplicate members are rejected. SHA-1 values are exactly 40
lowercase hexadecimal characters and raw SHA-256 values are exactly 64.
Paths are normalized repository-relative paths with no empty, `.` or `..`
segment, backslash, control character, or symlink substitution. Identifiers,
enums, array order, and cardinality are closed by the verifier. Raw SHA-256 is
only byte identity for these internal artifacts; it is not ADR 0003 canonical
serialization.

### Prior verifier contract

The record binds the already-merged verifier contract that makes the later
decision mechanically checkable:

```json
{
  "contract_id": "AAP-V05-DIAGNOSTIC-CATALOG-ACCEPTANCE-OFFLINE-V1",
  "repository": "MosslandOpenDevs/agentic-assurance-profile",
  "canonical_merge_commit_sha1": "<prior-verifier-contract-merge-sha1>",
  "artifacts": [
    {
      "role": "CONTRACT",
      "path": "docs/evidence/v0.5/diagnostic-catalog/decisions/README.md",
      "raw_sha256": "<format-v1-contract-readme-sha256>"
    },
    {
      "role": "ACCEPTANCE_VERIFIER",
      "path": "scripts/verify_diagnostic_catalog_acceptance.py",
      "raw_sha256": "<exact-prior-merge-blob-sha256>"
    },
    {
      "role": "CANDIDATE_SEMANTIC_VERIFIER",
      "path": "scripts/verify_diagnostic_catalog_candidate.py",
      "raw_sha256": "<exact-prior-merge-blob-sha256>"
    },
    {
      "role": "ACCEPTANCE_VERIFIER_TESTS",
      "path": "tests/test_verify_diagnostic_catalog_acceptance.py",
      "raw_sha256": "<exact-prior-merge-blob-sha256>"
    }
  ]
}
```

The merge is an ordinary two-parent canonical-main merge whose tree equals its
reviewed second-parent head. It must be the contract README's first
introduction on the acceptance base's canonical first-parent history, the PR
#66 candidate merge must precede it on that history, and it must not contain
the later acceptance record. The verifier materializes all four artifacts from
that exact merge. The contract README hash is fixed by format v1; the
executable and test hashes bind the exact reviewed implementation without
claiming that the local executable running today has authenticated provenance.

This ordering prevents a decision record from defining or importing its own
checker. A pre-verifier base, a record that points to its own merge, or an
unmerged verifier head fails closed.

### Exact subject

The first record's `subject` is:

```json
{
  "repository": "MosslandOpenDevs/agentic-assurance-profile",
  "candidate_canonical_merge_sha1": "c51b8c1cc7cb5fd343a4acf65e0cccc38356a4fe",
  "candidate_head_sha1": "f4c8f82e7d0bdfe7edd9a364d2e75a4d7af7ec67",
  "catalog": {
    "path": "docs/evidence/v0.5/diagnostic-catalog/catalog-r1.json",
    "raw_sha256": "da541828f462784eeb504af1436e6c689dc7f429814a18c729e2dc48362a0cec",
    "catalog_id": "urn:uuid:6d6187ea-521e-4f3e-98d9-cb716877a84b",
    "catalog_revision": 1
  },
  "legacy_mapping": {
    "path": "docs/evidence/v0.5/diagnostic-catalog/legacy-v0.4.0-mapping-r1.json",
    "raw_sha256": "281803836ca4034a3cf441c46b6e608434dea9245e5fa18c90e2954deac79100",
    "mapping_revision": 1
  },
  "compatibility_changes": {
    "path": "docs/evidence/v0.5/diagnostic-catalog/compatibility-changes-r1.json",
    "raw_sha256": "499a7a571502d0d70289d00f2bf655673da36c73c82bfb9df4c25913b9be0f7b"
  },
  "normalized_inventory": {
    "path": "docs/evidence/v0.5/diagnostic-catalog/normalized-inventory-r1.json",
    "raw_sha256": "aa3b9a5d30e41b2e78cb9e45c736ec697ccb04393ab6c300b82ce0e796cbc305",
    "role": "BOUND_REVIEW_EVIDENCE"
  }
}
```

The canonical merge must be the prior, ordinary two-parent PR #66 merge. Its
second parent is `candidate_head_sha1`, and its tree is byte-identical to that
head. The verifier materializes subject files from that merge, never from an
implicit current tree.

The artifact roles are intentionally different:

- `catalog` accepts revision 1 identity allocation, entry semantics, fact
  contracts, and lifecycle metadata as Foundation semantic input.
- `legacy_mapping` accepts revision 1's closed v0.4.0 semantic and terminal
  mapping as Foundation compatibility input.
- `compatibility_changes` accepts the closed pending distinctions and their
  rationales as compatibility-design input. It does not authorize a runtime
  difference or change a Phase 0 expectation.
- `normalized_inventory` is hash-bound reproducibility evidence only. It is
  not semantic authority or a public contract.

All embedded IDs, revisions, source/tag/commit bindings, cross-artifact hashes,
closed inventories, and candidate lifecycle boundaries must agree. A hash
match alone is insufficient when those semantic cross-checks fail.

### Acceptance scope

The exact version-1 `scope` is:

```json
{
  "accepted_baseline_components": [
    "DIAGNOSTIC_IDENTITY_ALLOCATION",
    "V0_4_SEMANTIC_MAPPING",
    "COMPATIBILITY_CHANGE_INTENT"
  ],
  "bound_review_evidence": [
    "NORMALIZED_SOURCE_INVENTORY"
  ],
  "implementation_parity_authorized": false,
  "runtime_consumption_authorized": false,
  "runtime_ready": false,
  "public_contract": false
}
```

When the external repository decision is effective, this scope removes only
the unaccepted-baseline precondition for later Foundation contract and
compatibility-adapter implementation work. It does not approve any such
implementation change.

It specifically does **not** authorize implementation parity, runtime emission
or activation, a public report/catalog wire format, ADR 0003 serialization or
redaction, the ADR 0004 plan/gate/status contract, a Phase 0 ledger or
projection change, an allowlist, Issue #43 behavior, or a validator, workflow,
schema, template, profile, or normative-obligation change. A later parity
decision must separately bind the accepted catalog decision and a complete,
separately merged ADR 0004 projection.

### Authority basis

`authority_basis` is closed to the governance revision on the acceptance
change's final base and the two already accepted ADRs:

```json
{
  "governance": {
    "repository": "MosslandOpenDevs/agentic-assurance-profile",
    "commit_sha1": "<acceptance-pr-final-base-sha1>",
    "path": "GOVERNANCE.md",
    "locator": "§§1–3",
    "raw_sha256": "5bc92e111440f117d4b7c1a801688889d6767217fcafdd4bdf9d0e333d9798a6"
  },
  "accepted_adrs": [
    {
      "adr_id": "0002",
      "repository": "MosslandOpenDevs/agentic-assurance-profile",
      "acceptance_merge_commit_sha1": "a34f074ab57214d5fe924ba90c00df313cc2acb6",
      "path": "docs/adr/v0.5/0002-diagnostic-identities.md",
      "locator": "Decision",
      "raw_sha256": "1ef92f7affec0e3031abcc7336fe68625db97e6931698e471b523ff44e8ff858"
    },
    {
      "adr_id": "0005",
      "repository": "MosslandOpenDevs/agentic-assurance-profile",
      "acceptance_merge_commit_sha1": "2a08ed7d0edbd0c9463513150d78017f2207f97f",
      "path": "docs/adr/v0.5/0005-human-review-authority.md",
      "locator": "Decision",
      "raw_sha256": "688ad75c79ac0253f4b26685d2c96316e4f1c82be2647157f80f749bfec89564"
    }
  ]
}
```

The governance commit must equal the acceptance PR's final base and the first
parent of the eventual decision merge. The verifier reads all three authority
artifacts from their named commits, not from the worktree.

### Repository-process binding

The record binds the repository process without fabricating its future result:

```json
{
  "pr_url": "<exact-acceptance-only-pr-url>",
  "acceptance_base_commit_sha1": "<acceptance-pr-final-base-sha1>",
  "governing_body": "MosslandOpenDevs maintainers",
  "review_fact_source": "DURABLE_ACCEPTANCE_PR_RECORD"
}
```

`acceptance_base_commit_sha1` equals `authority_basis.governance.commit_sha1`.
The PR URL must be final before designating the review-candidate head; a
placeholder is invalid.

The JSON does not contain its own acceptance merge/head, `accepted: true`,
`status: ACCEPTED`, decision maker, or human/automation review class. Those
facts do not exist when the immutable candidate bytes are prepared and cannot
be self-certified. The exact-head owner decision and actual merge record them
externally. A mismatch or unavailable external record leaves effective
acceptance not established.

## Effective predicate and verifier result

The internal verifier may establish only the local object-and-byte predicate:

- explicit record ID, path, decision merge, and consumer base; never a branch,
  tag, `HEAD`, directory scan, or implicit latest;
- one new direct JSON record introduced by an acceptance-only, ordinary
  two-parent merge whose first parent is the recorded final base;
- one exact, ordinary verifier-contract merge already on that base, with the
  fixed contract and recorded verifier/test artifact bytes;
- the candidate merge predates that base and has the recorded parent/tree
  relationship;
- exact candidate artifacts, identities, revisions, cross-references, roles,
  scope, governance, and ADR bytes;
- record-ID/path uniqueness in the selected canonical tree, first introduction
  on the acceptance base's first-parent history, append-only canonical
  first-parent history, and absence of head-only authority; and
- the decision merge already present on the consuming implementation base.

A successful local result means:

```text
offline_binding = VERIFIED
effective_acceptance = NOT_ESTABLISHED
implementation_parity_authorized = false
runtime_consumption_authorized = false
runtime_ready = false
```

Git subprocesses have a timeout and their captured output and parsed
object/tree data receive post-read bounds. This verifier does not implement a
streaming subprocess-output cap, however. An adversarially large local object
database is outside this internal review tool's supported boundary; the tool
must not be promoted to an authoritative CI gate or public verifier without
separately reviewed resource hardening.

It does not establish protected-canonical-main state, GitHub candidate or
acceptance PR state, the factual human decision maker or review classes,
maintainer eligibility or substantive authorship, credential/session custody,
branch/ruleset/CODEOWNERS/bypass controls at the event, GitHub CI conclusions,
semantic authority-reference validity, or published release/PR/workflow state.
Local repository origin, caller-supplied repository authority, and verifier/Git
executable provenance are likewise unverified preconditions. Missing or
ambiguous external facts never fall back to an in-repository assertion.

Exit zero therefore cannot grant acceptance. The repository's separately
governed owner decision supplies the organizational authority; the offline
result only makes its exact byte subject reproducible.

## Immutability and successors

An effective record is never edited, deleted, renamed, restored after deletion,
or reused under another path in a canonical first-parent tree state. The
offline verifier enforces that canonical-history scope; it does not claim that
the same bytes never appeared in discarded or non-canonical side-branch
objects. The initial record has both `predecessor` and `successor_change` set
to `null`.

A correction or expanded catalog/mapping scope requires a new candidate when
subject bytes change, then a new acceptance-only PR, record ID, and path. A
successor sets both fields non-null:

- `predecessor` binds the prior record ID, path, decision merge commit, and raw
  record SHA-256.
- `successor_change` closes the affected catalog identities and mapping groups,
  old/new revisions and artifact hashes, pinned authority references,
  rationale, and compatibility impact.

One non-null field without the other is invalid. The earlier record and subject
bytes remain historical facts. A structured successor whose
`predecessor.record_id` names the selected record invalidates that record for
current consumption even when the successor has a new subject decision ID. A
consumer must select one exact terminal record; a successor does not silently
reinterpret old reports, authorize parity, or make the newest filename
authoritative.
