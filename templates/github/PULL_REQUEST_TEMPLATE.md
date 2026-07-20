<!-- Placement: Copy this file to `.github/PULL_REQUEST_TEMPLATE.md` in the
     adopting repository. This placement note is an HTML comment so the impact
     directive below remains the first visible nonblank line. -->

Assurance impact: REPLACE_WITH_COMMA_SEPARATED_INVARIANT_IDS_OR_NONE

<!-- Keep exactly one Assurance impact directive: the line above. It must be
     the first visible nonblank line of the pull-request body; HTML comments
     may precede it. For a mapped component impact,
     replace the placeholder with every affected mapped INV- ID, comma-
     separated on that one line. Arbitrary ID mentions, a bulleted list,
     blockquotes, links, or code examples do not satisfy component routing.
     If the mapped invariants are unaffected, replace the directive with
       Assurance impact: none
     and add this visible top-level line immediately below it:
       Reason: <why the mapped invariants are unaffected>
     `Assurance impact: none` without that reason does not satisfy routing.
     The reason (and any policy-change explanation) must contain visible plain
     text; zero-width-only text, invisible-only entities, and empty inline HTML
     do not count.
     A duplicate, conflicting, or malformed Assurance impact line invalidates
     the declaration rather than supplementing it.
     If this pull request has a gated policy change, also add
       Assurance policy change: <why this change is intended and who decided it>
     below the impact/reason lines and before `## Summary`. These recognized
     lines form the leading directive block; after ordinary visible content
     begins, later directives are ignored. -->

## Summary

<!-- Intent, non-goals, and the implementation or control changes made. For data-semantics changes, state migration and rollback impact. -->

## Related issue or advisory

<!-- Use `Closes #N` only when this pull request fully satisfies the issue's acceptance criteria, including evidence and durable artifact updates. Otherwise use `Related to #N`. Reference published advisories rather than reproducing confidential detail. -->

## Affected assurance IDs

<!-- List any other affected CLAIM-, DEF-, and RES- identifiers here. The
     first-line directive, not this list, carries mapped invariant impact. -->

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
