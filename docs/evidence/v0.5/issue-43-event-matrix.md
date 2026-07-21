# Issue #43 event-matrix evidence

> **DECISION SUPPORT — NOT RUNTIME BEHAVIOR — NOT A SHIPPED FIX**

This note supports [ADR 0009](../../adr/v0.5/0009-event-matrix.md). It separates
observed repository/provider facts from the AAP policy decision so that a
provider behavior does not silently become an assurance rule.

## Bounded slice

- working base: `main@a300bd1806804e6b660423a905d6a353131c5642`;
- effort cap: four elapsed working hours, not increasable while active;
- checkpoint: at two elapsed working hours, continue only if the
  decision-only contract still fits the remaining cap;
- scope: ADR, ADR index, this evidence note, and a documentation-only
  changelog entry; and
- non-scope: executable changes, privileged PR-head evaluation, new push
  before/after or aggregate merge-group transition semantics, public
  output/catalog contracts, status-rule migration, engine work, and closing
  #43.

The slice stops rather than expanding if an honest decision requires new
permissions, network recovery, executable changes, or new base/head semantics.
Its output is a separately reviewed Draft PR.

## Current repository observation

At the working base,
`.github/workflows/adopter-validate.yml` declares only `workflow_call` and:

- runs `structure` and `declared-stage` for every underlying caller event;
- gates `drift` on `github.event_name == 'pull_request'`;
- checks out `github.event.pull_request.head.sha` for drift;
- compares `github.event.pull_request.base.sha` and head; and
- reads the PR body for impact and policy-change declarations.

Therefore the existing job has real pull-request transition semantics, not a
generic two-revision interface. On any other caller event GitHub skips it and
the workflow emits no AAP applicability/completion record. `docs/ADOPTION.md`
and `CHANGELOG.md` already warn that a green v0.4.x non-PR run has no drift
verdict.

## GitHub provider facts

The following were verified against GitHub's official documentation on
2026-07-21:

- [`pull_request`](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request)
  uses a synthetic merge ref/SHA by default; the explicit head revision is
  `github.event.pull_request.head.sha`. `edited` is a distinct activity type,
  and the same page says the payload may be empty for a fork-origin PR. That
  fork statement requires an actual provider pilot before support is claimed.
- [`pull_request_target`](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request_target)
  runs in the base repository's default-branch context, not the PR merge
  context. GitHub warns that executing untrusted PR code in this privileged
  trigger can expose secrets or write authority.
- [`merge_group`](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#merge_group)
  is separate from PR and push and supplies a merge-group SHA/ref. Repositories
  using required checks with merge queues need the event to obtain group
  checks.
- [`push`](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#push)
  supplies the pushed tip for ordinary updates, but on branch deletion the run
  SHA and ref revert to the default branch.
- [`schedule`](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
  runs on the latest default-branch commit, while
  [`workflow_dispatch`](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_dispatch)
  identifies the selected branch or tag and its last commit. Neither supplies
  a PR review transition.
- In a [reusable workflow](https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations#github-context),
  the `github` context remains associated with the caller workflow; token
  permissions can be maintained or reduced, not elevated through nesting.
- GitHub's [secure-use guidance](https://docs.github.com/en/actions/reference/security/secure-use#mitigating-the-risks-of-untrusted-code-checkout)
  says privileged triggers must not explicitly check out untrusted PR code.

These facts constrain the adapter but do not decide which AAP capability an
event satisfies. That normative mapping lives only in ADR 0009.

## Threat and compatibility analysis

### Safe boundary retained

The current PR evaluator already uses a pinned reusable workflow, read-only
repository permission, explicit base/head payload SHAs, no persisted checkout
credentials, bounded validator inputs, and environment variables for PR
prose. The event contract preserves those properties.

For `pull_request_target`, the contract deliberately refuses to add a PR-head
checkout or execute adopter-controlled code. A base-tree structure result may
be informative, but it cannot be promoted into a completed transition result.

### Rejected compatibility shortcut

Leaving the evaluator PR-only and placing a green N/A projection at the same
public `drift` identity looks mechanically small but is semantically unsafe. On
`merge_group` or another snapshot event, that check could satisfy branch
protection while performing no single-PR transition comparison. The provider
status would then erase the distinction this ADR exists to preserve.

The current evidence therefore does not justify a v0.4.1 behavior patch.
Implementation defaults to the v0.5 CI adapter unless a later reviewed slice
proves that separate, non-substitutable status identities and caller
provenance can be introduced compatibly. Running drift on a new event remains
out of scope.

Before shipping, local table tests and a GitHub pilot must verify event rows,
evaluator failure and cancellation, reusable outputs, caller-trigger
provenance, status identity, and same-repository, fork, Dependabot,
`pull_request_target`, and `merge_group` runs. The legacy drift process also
conflates policy failure with some execution failures in exit `1`; no adapter
may claim the full v0.5 `OverallOutcome` taxonomy until the typed Foundation
boundary exists.

## Remaining unknowns

- wider public reason/check catalog metadata and JSON spelling (the exact
  semantic event-reason identifiers in ADR 0009 are reserved);
- separate required-status identities for snapshot and transition gates;
- a safe bounded-data design, if any, for `pull_request_target`;
- aggregate multi-PR drift semantics for a merge group;
- whether push `before`/`after` should ever define a separately named
  transition capability; and
- provider-level behavior for cancellation and reusable outputs until a real
  GitHub pilot runs.

None of these unknowns changes the ADR's central distinction: known
non-applicability may pass a snapshot gate, while an applicable comparison that
did not complete is indeterminate.
