# ADR 0009: caller-event applicability and drift completion

- **Lifecycle path:** PROPOSED while the linked pull request is open ->
  ACCEPTED only when its exact named review-candidate head is durably merged
- **Decision owner:** MosslandOpenDevs maintainers
- **Tracking issue:** [#43](https://github.com/MosslandOpenDevs/agentic-assurance-profile/issues/43)
- **Acceptance:** maintainer review and merge of the exact review-candidate
  head in the linked pull request
- **Acceptance record:** [Draft PR #64](https://github.com/MosslandOpenDevs/agentic-assurance-profile/pull/64)
- **Acceptance review class:** derived from the durable PR #64 acceptance
  record under [`GOVERNANCE.md`](../../../GOVERNANCE.md); the immutable
  candidate does not predeclare its eventual class
- **Recorded:** 2026-07-21
- **Working base:** `main@a300bd1806804e6b660423a905d6a353131c5642`
- **Runtime effect:** none; this ADR does not change the v0.4.x workflow

## Context

The v0.4.x reusable adopter workflow runs its `drift` job only when the
underlying caller event is `pull_request`. Other events can produce green
`structure` and `declared-stage` jobs while GitHub marks `drift` skipped. A
GitHub job conclusion is not enough to distinguish a policy comparison that
does not apply from one that should have run but did not.

The accepted v0.5 design already defines three independent check-state axes:

```text
Applicability = APPLICABLE | NOT_APPLICABLE | UNDETERMINED
Completion    = COMPLETED | NOT_RUN | FAILED_TO_COMPLETE
Outcome       = PASS | FAIL | NONE
```

This ADR decides how the single-pull-request review-transition drift
capability uses those axes. It reserves the exact semantic reason identifiers
shown below, but does not allocate finding codes, a wider catalog namespace,
JSON field spelling, or CI status names.

## Decision

### Invariants

1. The transition-drift capability remains present in every applicable trusted
   plan. A skipped GitHub job is not semantic completion.
2. `NOT_APPLICABLE` means that the invocation is a snapshot evaluation with no
   single pull-request review transition. It never means that event facts were
   missing or that an applicable comparison failed to run.
3. `ADOPTER_SNAPSHOT` cannot satisfy an `ADOPTER_TRANSITION` gate or status
   identity. A green snapshot report is not proof that a pull request's drift
   comparison ran.
4. An applicable, completion-required comparison that cannot complete makes
   the run `INDETERMINATE` under the precedence in the v0.5 design §7.1.
5. `workflow_call` is transport, not an event or an authority source. The
   called workflow classifies the caller-associated `github` context and does
   not accept caller inputs that override event, base, or head identity.
6. A transition status is authoritative only inside an accepted caller trust
   boundary that proves the required event subscriptions, invocation
   reachability, producer pin, and non-substitutable status identity. For every
   required activity, the reusable-workflow call job must not disappear behind
   a job-level condition or a skipped or failed dependency: GitHub reports a
   skipped job as successful even when it is a required check. A called
   workflow cannot infer the caller YAML's full trigger set or job graph from
   one runtime payload.
7. A provider-required workflow that ignores event filters cannot by itself
   prove PR-prose freshness. In particular, GitHub ruleset workflows run
   `pull_request` only for the provider's default activity types and ignore a
   caller's `types` filter, so they do not observe `edited` solely because the
   YAML lists it.

### Event matrix

The state shown is the nominal single-PR transition-drift state after event
facts and required revisions have been acquired. Any later acquisition or
execution failure changes an applicable check to
`APPLICABLE / FAILED_TO_COMPLETE / NONE` with an appropriate stable
non-completion reason.

For this contract a `merge_group` invocation evaluates an adopter snapshot;
the table says only that single-PR/body-based drift does not apply. It does not
claim that an aggregate multi-PR transition gate passed. Defining such a gate
requires a successor decision and a non-substitutable status identity.

| Underlying caller event | `EvaluationKind` | Transition-drift state | Trusted revision/context source | Stable reason when not evaluated | Gate meaning |
|---|---|---|---|---|---|
| `pull_request` | `ADOPTER_TRANSITION` | `APPLICABLE / COMPLETED / PASS` or `APPLICABLE / COMPLETED / FAIL` | `pull_request.base.sha`, `pull_request.head.sha`, and the PR body | none when completed; missing or unusable revisions use `PULL_REQUEST_REVISIONS_UNAVAILABLE` | Complete transition result; non-completion is `INDETERMINATE`. |
| `pull_request_target` | `ADOPTER_TRANSITION` | `APPLICABLE / NOT_RUN / NONE` | The payload identifies a PR, but the event executes in the trusted base/default-branch context. | `PRIVILEGED_PULL_REQUEST_TARGET_UNSUPPORTED` | `INDETERMINATE`; a base snapshot is at most partial/advisory and cannot satisfy the transition gate. |
| non-deletion branch or tag `push` | `ADOPTER_SNAPSHOT` | `NOT_APPLICABLE / NOT_RUN / NONE` | The pushed tip identified by `GITHUB_SHA`; webhook `before`/`after` are not silently promoted into PR-review inputs. | `PUSH_HAS_NO_REVIEW_TRANSITION` | Snapshot result only; explicitly no drift verdict. |
| `merge_group` | `ADOPTER_SNAPSHOT` | `NOT_APPLICABLE / NOT_RUN / NONE` | The merge-group synthetic SHA/ref; there is no selected single-PR body or review transition. | `MERGE_GROUP_HAS_NO_SINGLE_PR_TRANSITION` | Single-PR drift is N/A; the snapshot cannot prove that each member PR ran drift or that an aggregate transition gate passed. |
| `workflow_dispatch` | `ADOPTER_SNAPSHOT` | `NOT_APPLICABLE / NOT_RUN / NONE` | The selected ref and its `GITHUB_SHA`; no authoritative base/body pair. | `MANUAL_RUN_HAS_NO_REVIEW_TRANSITION` | Snapshot result only. |
| `schedule` | `ADOPTER_SNAPSHOT` | `NOT_APPLICABLE / NOT_RUN / NONE` | The latest default-branch commit; no authoritative base/body pair. | `SCHEDULE_HAS_NO_REVIEW_TRANSITION` | Snapshot result only. |
| unrecognized or unavailable caller event | conservative fallback `ADOPTER_TRANSITION` | `UNDETERMINED / NOT_RUN / NONE` | No caller input may repair or reclassify the missing trusted event fact. | `CALLER_EVENT_UNSUPPORTED` | `INDETERMINATE`; no snapshot result may substitute. |

For a reusable workflow, each recognized caller inherits the corresponding row
unchanged. The presence of `workflow_call` does not replace the underlying
event name or produce another `EvaluationKind`.

A deletion `push` is deliberately not covered by the nominal push row: GitHub
documents that `GITHUB_SHA` reverts to the default branch when a branch is
deleted. Unless a caller excludes deletion triggers before invocation, the
snapshot-acquisition capability reports
`UNDETERMINED / NOT_RUN / NONE` with
`PUSH_TARGET_SNAPSHOT_UNAVAILABLE`, making the run `INDETERMINATE`; the
transition-drift capability remains not applicable with
`PUSH_HAS_NO_REVIEW_TRANSITION`. The adapter must not describe a
default-branch checkout as the deleted ref's snapshot.

### Pull-request acquisition

For `pull_request`, the adapter must:

- require canonical full commit IDs for both explicit payload revisions;
- materialize and compare exactly those base and head objects without mixing a
  merge ref, worktree, index, or another snapshot;
- treat an absent, malformed, shallow, unavailable, or unmaterializable
  required revision as `PULL_REQUEST_REVISIONS_UNAVAILABLE`, not as
  `NOT_APPLICABLE` or `PASS`; and
- receive PR prose as data rather than interpolate it into executable code.

Because the PR body carries the assurance-impact and policy-change
declarations, callers that claim transition coverage must trigger at least
`opened`, `synchronize`, `reopened`, and `edited`. `ready_for_review` is
required only if a later trusted plan makes draft state an evaluation input.
They must also make the reusable-workflow call reachable on every required
activity despite job conditions and dependency outcomes, and prevent another
producer from satisfying the same complete-transition identity. The current
called workflow cannot verify this static caller configuration or job graph;
until an accepted producer/caller provenance mechanism does so, its status is
not eligible as proof of complete transition coverage.

GitHub ruleset workflows are not sufficient proof of that coverage when PR
prose is an input: GitHub ignores event filters for these workflows and runs
`pull_request` only for `opened`, `synchronize`, and `reopened`. A separately
accepted mechanism must run or invalidate the transition result on `edited`;
otherwise complete transition coverage remains unproved.

GitHub's event documentation says that a `pull_request` payload may be empty
for a fork-origin PR. The same-repository, fork, and Dependabot cases therefore
require provider pilots. Whenever either explicit revision is absent, this
contract remains fail-closed with `PULL_REQUEST_REVISIONS_UNAVAILABLE`.

ADR 0008 will decide concrete Git materialization, shallow-clone, merge-base,
rename, symlink, and submodule mechanics. This ADR fixes only the required
event identities and the fail-closed result when those identities cannot be
acquired safely.

### Privilege boundary

This ADR does not authorize transition evaluation on `pull_request_target`.
No implementation may check out or execute the untrusted PR head in that
privileged context, pass it through a shared writable cache, or consume an
untrusted artifact as executable input. A future trusted-engine/bounded-data
design requires its own threat-model review. Until then the honest state is
applicable but not run, and therefore indeterminate.

No event class uses a GitHub API lookup or caller-supplied override to repair
missing trusted event facts in this contract.

## Compatibility and delivery

The simplest v0.4.1 patch is not safe: an always-running green N/A projection
at the existing public `drift` identity could satisfy a required check on a
snapshot event such as `merge_group`, contradicting the non-substitution
invariant above. This ADR therefore authorizes no v0.4.1 behavior patch.

A later patch is eligible only if it can add non-substitutable snapshot and
transition identities plus accepted caller provenance without breaking
supported structural-only callers. Those are ADR 0004 concerns; absent that
proof, implementation belongs in the v0.5 CI adapter.

The executable slice must separately test event classification, evaluator
failure/cancellation, output propagation, producer/caller trust, and real
GitHub behavior for same-repository, fork, Dependabot,
`pull_request_target`, and `merge_group` cases. Fully typed reports, wider
catalog metadata, JSON encoding, and distinct CI status identities remain v0.5
Foundation work. The reason identifiers reserved here must not be renamed or
reused by that catalog.

## Consequences

- Manual, scheduled, merge-queue, and ordinary push snapshot validation can
  remain useful without being mislabeled as a drift verdict.
- `pull_request_target` can no longer be treated as harmlessly skipped: it is
  an applicable comparison that the current trust boundary cannot complete.
- Reusable callers cannot game applicability by supplying event or revision
  inputs.
- The current v0.4.x workflow still lacks this runtime projection until a
  separately reviewed implementation lands.

## Evidence

Provider facts, current-workflow observations, threat analysis, compatibility
limits, and implementation unknowns are recorded in
[`issue-43-event-matrix.md`](../../evidence/v0.5/issue-43-event-matrix.md).
