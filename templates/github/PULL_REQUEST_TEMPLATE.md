> **Placement:** Copy this file to `.github/PULL_REQUEST_TEMPLATE.md` in the adopting repository. Delete this header block when copying; everything below it becomes the default pull-request body.

## Summary

<!-- Intent, non-goals, and the implementation or control changes made. For data-semantics changes, state migration and rollback impact. -->

## Related issue or advisory

<!-- Use `Closes #N` only when this pull request fully satisfies the issue's acceptance criteria, including evidence and durable artifact updates. Otherwise use `Related to #N`. Reference published advisories rather than reproducing confidential detail. -->

## Affected assurance IDs

<!-- List affected CLAIM-, INV-, DEF-, and RES- identifiers, or state "none".
     If this repository maps components in `.agentic-assurance/adoption.yaml`
     and this pull request touches mapped component paths without changing
     assurance artifacts, either list that component's invariant IDs above or
     add this two-line no-impact statement to the description — both lines at
     the start of a line, and the reason is mandatory:
       Assurance impact: none
       Reason: <why the mapped invariants are unaffected>
     If this pull request deliberately weakens the adoption declaration
     (stage downgrade, pin change, component removal or narrowing), the
     drift check requires an explicit acknowledgment line:
       Assurance policy change: <why this weakening is intended and who decided it> -->

- 

## Change classification

- [ ] Implementation-only — no externally visible behavior change
- [ ] Behavioral — externally visible behavior changes
- [ ] Public-claim — public claims or their limitations change
- [ ] Security-sensitive — authentication, authorization, privacy, secrets, or trust boundaries
- [ ] Data-semantics — persistent data meaning, identifiers, or migrations

## Verification evidence

<!-- Commands run, test names, output locations. Bind evidence to a commit SHA, artifact digest, or deployment identifier. "All checks passed" is not evidence unless the underlying results are linked and reproducible. -->

- Tests:
- Static analysis:
- Runtime evidence:
- Independent review:

## Residual impact

- [ ] None
- [ ] Residuals added or updated — RES- IDs listed above
- [ ] Residuals resolved — RES- IDs listed above

## Completion checklist

- [ ] Change specification updated, or not required for this change
- [ ] Enforcement implemented for affected invariants
- [ ] Evidence bound to a revision, artifact digest, or deployment
- [ ] Durable assurance artifacts updated — claims, invariants, defeaters, residuals
- [ ] Public disclosure reviewed — no secrets, personal data, or actionable vulnerability detail
