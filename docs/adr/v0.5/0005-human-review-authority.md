# ADR 0005: human-review provenance and authority boundary

- **Lifecycle path:** PROPOSED while the linked pull request is open ->
  ACCEPTED only when its exact named review-candidate head is durably merged
- **Decision owner:** MosslandOpenDevs maintainers
- **Tracking issue:** [#50](https://github.com/MosslandOpenDevs/agentic-assurance-profile/issues/50)
- **Acceptance:** maintainer review and merge of the exact review-candidate
  head in the linked pull request
- **Acceptance record:** [Draft PR #67](https://github.com/MosslandOpenDevs/agentic-assurance-profile/pull/67)
- **Acceptance review class:** derived from the durable linked-PR acceptance
  record under [`GOVERNANCE.md`](../../../GOVERNANCE.md); the immutable
  candidate does not predeclare its eventual class
- **Recorded:** 2026-07-22
- **Working base:** `main@c51b8c1cc7cb5fd343a4acf65e0cccc38356a4fe`
- **Runtime effect:** none; this ADR changes no validator, workflow, schema,
  template, profile obligation, public report, gate, or repository setting

## Context

The v0.5 design uses
`ProfileClassificationReview = UNCONFIRMED | REVIEW_RECORDED |
UNDETERMINED(reason_code)`. It already limits `REVIEW_RECORDED` to the
mechanically decidable structure of a pinned declaration's durable review
record and stage relationships. It does not authenticate a forge actor,
effective repository controls, signer custody, or human identity.

That distinction is necessary because the primary threat model includes an AI
agent with repository-write access. Such an agent can create or rewrite every
in-repository file, prose assertion, commit author field, and self-attestation.
If the same agent can also use a maintainer's forge token, browser session, or
signing key, a provider event or valid signature attributed to that account
still cannot establish that a human was present or made the decision.

At the same time, exact Git objects, artifact bytes, review-event identifiers,
and governance revisions are valuable provenance. Discarding them because
they are not proof of human presence would make repository decisions
unnecessarily ambiguous. This ADR therefore separates four properties that
must not collapse into one another.

## Decision

> v0.5 Foundation verifies and reports structural review provenance. A
> repository process may additionally record exact decision provenance and
> its factual governance class. Neither property is external verification of
> human identity, presence, intent, or credential custody. The Foundation
> provides no stronger authority-verification capability or public state.

### Four non-equivalent properties

| Property | What it can establish | What it cannot establish |
|---|---|---|
| **Structural review provenance** | The selected declaration safely loaded, names the required review fields, points to the required in-project record, and mechanically satisfies its stage relationships. | That the named reviewer exists, opened the record, understood it, or performed the claimed act. |
| **Repository-decision provenance** | An append-only decision record binds a stable decision identity and scope to exact candidate bytes, Git revisions, governance revision, and durable repository/forge locators. | That a forge account corresponds to a distinct live human, or that its credentials were outside agent control. |
| **Recorded governance class** | The repository honestly reports the process fact `INDEPENDENTLY_REVIEWED` or `SOLE_OWNER_ATTESTED`, with `AUTOMATION_VERIFIED` recorded separately. | An assurance score, proof of review quality, or a machine-authenticated human identity. |
| **External authority verification** | Under a separately accepted capability, a named external trust anchor could verify a bounded provider, credential, event, revision, scope, and control-plane claim. | Universal human presence, comprehension, or consent beyond the accepted anchor's stated limits. |

The first property is the only authority-adjacent property in the Foundation's
public `ProfileClassificationReview` state. The other properties remain
orthogonal. A successful check on one axis never promotes another axis.

### Foundation semantics

`REVIEW_RECORDED` retains exactly the meaning fixed in the v0.5 design:

1. the primary current/head declaration is safely loaded;
2. its self-declared stage is `HUMAN_REVIEWED` or `CONFORMANT`;
3. the bounded parser and stage checks establish the required review-record
   fields, referenced artifact, and mechanical relationships; and
4. no acquisition or evaluation failure prevents that classification.

It means **recorded structural provenance**, not “human verified.” A renderer
may report the declaration's stage and the fact that its structural review
requirements passed, but it must not infer or state that:

- the reviewer, approver, committer, signer, or forge actor is a human;
- the named person was present, retained exclusive credential custody, read
  the change, understood its effect, or approved it intentionally;
- a URL resolved to an approving review by an eligible non-author;
- branch protection, CODEOWNERS, required-review, or no-bypass controls were
  effective for the relevant event;
- the declaration is factually correct or fully conformant;
- a risk, residual, defeater, policy weakening, or public claim was accepted;
  or
- an agent may change policy, advance a stage, or manufacture approval.

The normative profile may require that a human act actually occurred. Passing
the mechanical subset does not prove the truth of that claim. A missing or
unqualified external-authority claim remains **not established**; this phrase
is a review conclusion, not a new public enum value or JSON field.

No local command, TTY prompt, username, commit metadata, mere existence of a
commit, in-repository flag, agent message, green check, or `aap review`
invocation creates authority by itself. A governed owner act such as a
reviewed merge may anchor an agent-drafted record, but the authority comes
from that act under the repository's owner process, not from the record's
bytes or authorship metadata. The Progressive UX track may prepare a
non-authoritative review packet; it cannot make the decision it records.

### Repository-decision provenance

A durable repository decision is useful only when a later reader can identify
the exact subject, rule, scope, and process record without selecting a mutable
“latest” value. A decision record that is intended to authorize later
consumption must semantically bind all of the following, although ADR 0003
owns its eventual field spelling, serialization, digest, and redaction rules:

- a stable decision identity and decision kind;
- the subject repository and exact candidate commit;
- the canonical-main merge commit that first preserved the candidate, when a
  prior candidate merge is part of the lifecycle;
- the selected artifact paths, content identities or digests defined by the
  applicable accepted serialization contract, semantic revision identities,
  and the exact accepted or rejected scope;
- the governing policy or governance revision that was effective on the
  decision change's base;
- the separate decision or acceptance change, its base and candidate/head
  revisions, and its durable repository/forge locator;
- the actor/account and event facts the provider recorded, without relabeling
  those facts as verified human identity;
- the factual review class and a separate automation-evidence class;
- explicit limitations, including unavailable provider/control/credential
  facts and anything deliberately not authorized; and
- an append-only successor or supersession edge for any later correction.

An independently reviewed record additionally identifies the qualifying
approval event, the exact reviewed commit/diff state, the provider-recorded
reviewer account, the approval state and time observed at acceptance, and the
accepted governance roster or role against which eligibility was decided.
Any later verifier records its new observation separately and applies an
accepted dismissal, revocation, and staleness policy; it does not rewrite the
historical observation as if mutable provider state were immutable. A
sole-owner record instead identifies the owner's explicit decision record and
merge and states that no independent approving human review is on record. It
must not fabricate an approval event that the provider does not permit.

The candidate or implementation change cannot create its own effective
acceptance, allowlist, or parity authority. When a lifecycle requires a
separate acceptance-only change:

1. the canonical candidate must already exist on the acceptance change's base;
2. the acceptance change binds that earlier candidate and only the scope
   actually decided;
3. the acceptance record becomes effective only through its separately
   governed repository process, not through `accepted: true` prose inside the
   record; and
4. a consumer must already contain the effective record in its base and select
   its exact identity; it may not use an acceptance introduced by its own head.

Missing, mismatched, ambiguous, rewritten, or unavailable required binding
facts leave the decision not established for consumption. A consumer must not
fall back to current worktree bytes, a floating branch, the most recent file,
an unverified URL, or a weaker structural state.

This ADR fixes those semantic bindings, not a universal acceptance-record
schema. In particular it neither accepts the PR #66 diagnostic candidate nor
authorizes catalog parity or runtime consumption.

### Factual review classes

The review classes in [`GOVERNANCE.md`](../../../GOVERNANCE.md) are factual
descriptions of what actually occurred:

- `INDEPENDENTLY_REVIEWED` requires an approving review by an actual human
  maintainer who did not author the change, durably recorded for the bound
  change;
- `SOLE_OWNER_ATTESTED` means the sole maintainer reviewed and merged on their
  own authority with no independent human approval on record; and
- `AUTOMATION_VERIFIED` records mechanical evidence and is independent of both
  human-review classes.

An AI review, a second account controlled by the same person, an external
technical opinion that is not a qualifying maintainer approval, a bot review,
or green CI is not `INDEPENDENTLY_REVIEWED`. GitHub's inability to accept
self-approval must not be hidden by inventing one. The current one-maintainer
repository therefore reports `SOLE_OWNER_ATTESTED + AUTOMATION_VERIFIED` when
that is the record it actually has.

“Did not author” is a fact about actual human substantive authorship under the
governing process, not merely `reviewer account != pull-request author`.
Repository provenance should preserve the provider-recorded pull-request
author, commit author and committer, latest pusher where available, and known
agent or substantive authorship as distinct facts. Account inequality can
support a provider-policy check, but cannot by itself turn an owner-opened,
agent-drafted change or two accounts controlled by one person into independent
human review.

A machine may reproduce the repository's recorded class and validate its
bound fields. Until a stronger capability and its trust anchors are accepted,
it must describe the value as a **recorded review class**, not as a verified
real-world identity or presence claim.

### External authority verification is unsupported in Foundation

v0.5 Foundation ships no provider adapter, signature verifier, liveness
mechanism, credential-isolation proof, or public authority-verification state.
It does not silently turn any of the following into human authority:

- a forge login, account ID, review URL, comment, approval, merge, or current
  repository setting;
- CODEOWNERS membership or a requested code-owner review;
- commit, tag, GPG, SSH, S/MIME, or provider-generated signature status;
- an OIDC token, workflow actor claim, artifact attestation, transparency-log
  entry, or green required check; or
- an in-repository statement that a trust boundary or human act existed.

These mechanisms may establish narrower and useful facts. For example, a
provider may show that a named account submitted an approval for a particular
commit, a signature verifier may show that a key signed bytes, and OIDC may
bind a workflow to a repository and revision. None of those narrow facts
establishes that a human exclusively controlled the credential, was present,
or made an informed decision.

A future provider-specific authority-provenance capability is eligible only
through a separate accepted decision and versioned catalog/plan. It must name:

1. the exact claim it verifies and every stronger claim it declines;
2. the provider and trusted API or transparency source;
3. canonical provider, repository, pull-request, review, and account
   identities and bindings to revision, diff, scope, time, and governance
   roster;
4. an allowlisted authenticated HTTPS origin from which API requests are
   derived using those canonical identities; an adopter-recorded
   `review_url` remains a display locator and is never fetched or sent
   credentials merely because it was recorded;
5. the relevant review, stale-approval, latest-push, code-owner, push,
   administrator, ruleset, and bypass controls;
6. how those controls are bound at the time of the event rather than inferred
   from only current settings;
7. credential and control-plane isolation assumptions for agents,
   automations, maintainers, administrators, and signing services;
8. revocation, dismissal, account/role change, key compromise, history
   rewrite, and successor behavior;
9. acquisition, authentication, rate-limit, timeout, provider-outage, and
   unsupported-host failure states; and
10. why the capability remains optional and does not become a new baseline
   obligation for adopters.

Even such a capability may establish only a bounded provider fact such as
“the provider recorded an eligible account approving the bound candidate
under the controls checked by this adapter.” It must not call that fact human
liveness, exclusive credential custody, informed semantic consent, or
real-world identity unless a still stronger accepted trust anchor actually
establishes the named property.

Identity allocation, public check/reason codes, JSON state spelling, canonical
digests, and redaction remain ADR 0002/0003 concerns. Trusted plan derivation,
completion requirements, provider status identities, caller/producer trust,
and gate behavior remain ADR 0004 concerns. This ADR creates none of them.

### Offline and unavailable-provider behavior

An offline verifier may safely establish exact local Git topology, raw bytes,
digests, revision relationships, and internal record consistency when its
required objects are present. A scoped result such as the existing Phase 0
`offline_binding: VERIFIED` is therefore meaningful: it verifies the exact
offline binding it names, not effective external acceptance. An offline
verifier may also report `REVIEW_RECORDED` after the Foundation's structural
checks complete. It cannot establish from a clone alone:

- that a URL denotes the claimed review or remains approved rather than
  dismissed;
- who controlled the provider account or signing key;
- which branch/ruleset, bypass, role, or membership controls were effective at
  the relevant time;
- that observed Git topology was produced through the protected,
  provider-governed acceptance-only process or satisfied its external
  acceptance predicates; or
- the factual human decision maker or real-world review class.

Provider unavailability, unauthenticated or incomplete acquisition, missing
historical controls, rate limiting, and ambiguous identity never fall back to
an in-repository assertion. The Foundation continues to report only its
structural state. A future completion-required external check would report a
typed non-completion and make the owning run indeterminate under the v0.5
precedence; this ADR allocates no such check or reason.

## Compatibility and delivery

This decision narrows claims rather than changing current v0.4.x behavior.
The current validator already checks only the structural and mechanically
decidable subset of review and conformance declarations. It does not
dereference approval URLs or authenticate their actors.

Any implementation of this decision **must** preserve:

- current v0.4.x adoption-field and stage meanings, the accepted semantic
  conditions and gate effects represented by v0.4.x validation results, the
  preregistered legacy renderer subset, and existing workflow-job compatibility
  except where a separately accepted and ledgered intended change applies;
  text wording and the new CLI's versioned exit-status contract remain governed
  by the v0.5 design §§7 and 9;
- the rule that omitted approval `covers` means full mechanical conformance
  scope;
- `REVIEW_RECORDED` as structural provenance only, without making the
  Foundation indeterminate merely because external provider evidence is
  absent;
- offline Foundation use without a new network, credential, provider,
  signature, or repository-control requirement;
- scoped meanings such as `offline_binding: VERIFIED`, `authority_refs`,
  `intent.authority`, review/approval locators, and recorded review classes as
  byte, reference, or process facts rather than external human authority;
- profile-classification correctness (#41) and the truth of full conformance
  as questions that this provenance state does not answer; and
- any stronger capability as optional, versioned, separately accepted, and
  integrated through the identity, serialization, and trusted-plan contracts
  owned by ADR 0002, ADR 0003, and ADR 0004.

No green v0.4.x result, `HUMAN_REVIEWED`, `CONFORMANT`, or future
`REVIEW_RECORDED` may be reinterpreted as machine proof of external human
authority.

No catalog acceptance, compatibility mapping acceptance, parity
authorization, runtime implementation, schema change, new CLI command, forge
API call, signing requirement, CODEOWNERS requirement, branch mutation, or
new profile obligation is authorized by this ADR.

## Consequences

- The Foundation can provide deterministic, portable review provenance
  without claiming facts its local trust boundary cannot know.
- Repository decisions can bind exact bytes and scope strongly enough for
  later consumption while reporting sole-owner reality honestly.
- GitHub approvals, signatures, OIDC, and attestations remain available as
  distinct evidence rather than being discarded or overpromoted.
- A future stronger verifier must expose its provider and credential
  assumptions instead of hiding them behind a generic “human verified” flag.
- The project accepts that external human-authority verification remains an
  unsupported problem in v0.5 Foundation.

## Evidence

Current validator/schema behavior, repository-governance observations,
provider facts, and the adversarial mechanism analysis are recorded in
[`issue-50-authority-provenance.md`](../../evidence/v0.5/issue-50-authority-provenance.md).
