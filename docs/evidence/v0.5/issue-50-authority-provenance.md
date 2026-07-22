# Issue #50 authority-provenance evidence

> **DECISION SUPPORT — NOT EXTERNAL HUMAN VERIFICATION — NOT RUNTIME BEHAVIOR**

This note supports
[ADR 0005](../../adr/v0.5/0005-human-review-authority.md). It separates
observable repository/provider facts from the authority claims they do and do
not justify.

## Bounded slice

- working base: `main@c51b8c1cc7cb5fd343a4acf65e0cccc38356a4fe`;
- effort cap: four elapsed working hours, not increasable while active;
- scope: ADR 0005, the ADR index, this evidence note, and a
  documentation-only changelog entry;
- decision: distinguish structural review provenance, exact repository
  decision provenance, factual governance classes, and external authority;
  and
- non-scope: diagnostic-catalog acceptance, compatibility-mapping acceptance,
  implementation parity, runtime behavior, validator/workflow/schema/template
  changes, public JSON spelling, canonical digest/redaction, GatePlan/CI trust,
  provider APIs, signatures, OIDC, branch mutations, and new obligations.

The slice stops rather than expanding if an honest decision requires a new
public wire state, executable verification, ADR 0003/0004 work, candidate
acceptance bytes, a normative obligation, or an unverifiable identity claim.
It was preregistered on
[issue #50](https://github.com/MosslandOpenDevs/agentic-assurance-profile/issues/50#issuecomment-5043424920)
before repository files changed.

## Current repository observations

At the working base:

- [`PROFILE.md` §7](../../../PROFILE.md) says committed prose is not human
  authority merely because it is committed. An agent marker disqualifies prose
  as intent authority, while the absence of a marker proves nothing. Authority
  comes from a human act anchoring the record.
- [`PROFILE.md` §17](../../../PROFILE.md) requires a dated review, named
  reviewer, and durable record at `HUMAN_REVIEWED`, then an attributable
  approval at `CONFORMANT`. It explicitly says the validator enforces only the
  structural and mechanically decidable subset of the full normative claim.
- [`schemas/adoption.schema.json`](../../../schemas/adoption.schema.json)
  requires the shape of `human_review` data. Its approval description says the
  validator does not dereference `review_url` or verify its approval state or
  authorship.
- [`scripts/validate.py`](../../../scripts/validate.py) checks review dates,
  required strings, in-project non-empty record existence, approval URL/time/
  scope shape, and some provenance regression. Its stage-check documentation
  states that confirming a real approved review by a non-author remains a
  manual step.
- [`V0.5-DESIGN.md` §7](../../V0.5-DESIGN.md) defines `REVIEW_RECORDED` as the
  Foundation's mechanically decidable review-record/stage result and expressly
  excludes forge actor, effective controls, signer custody, and human identity.
- [`GOVERNANCE.md`](../../../GOVERNANCE.md) separates the factual classes
  `INDEPENDENTLY_REVIEWED`, `SOLE_OWNER_ATTESTED`, and
  `AUTOMATION_VERIFIED`. It records sole-owner attestation as the honest
  current default and says agents never approve.
- [`.github/CODEOWNERS`](../../../.github/CODEOWNERS) routes governed paths to
  `@MosslandOpenDevs/maintainers`, while `GOVERNANCE.md` states that the team
  currently has one active member and that intended branch-protection controls
  and actual sole-owner review class must be reported separately.
- The PR #66 merge on the working base preserved the diagnostic candidate
  bytes on canonical `main`, but did not establish the separate exact-byte
  acceptance binding. The catalog's acceptance binding remains null and its
  parity/runtime flags remain false. ADR 0005 must not change that state.

The current implementation can therefore establish useful structural
relations but has no external authority verifier. That is an intentional
boundary to specify, not a hidden implementation gap to relabel as success.

Current repository settings, maintainer-team membership, provider review
state, and historical branch/ruleset effectiveness were not authenticated in
this documentation-only slice. A committed CODEOWNERS file is observed routing
data; it is not evidence that the provider enforced the intended settings.

### Mechanically established today

The existing schema, validator, and regression suite establish a deliberately
narrow set of facts:

- owner, reviewer, approver, and acceptance-authority values have the required
  non-blank string shape;
- the review-record path is contained in the adopter repository and resolves
  to an existing non-empty file;
- approval locators, dates/timestamps, and `covers` have valid shape and
  temporal ordering, with omitted `covers` treated as full conformance scope;
- affirmative intent has a non-blank authority reference, and an accepted
  residual has the required acceptor, date, and rationale fields; and
- drift checks protect existing review/approval tuples and selected
  authority/acceptance fields from some removal or rewrite.

The existing
[`scripts/verify_phase0_acceptance.py`](../../../scripts/verify_phase0_acceptance.py)
separately demonstrates a stronger but still scoped property. It can verify
exact Git topology, immutable record history, artifact bytes, revision and
governance binding, and report `offline_binding: VERIFIED`; it simultaneously
reports external `effective_acceptance: NOT_ESTABLISHED`. The
[`scripts/verify_diagnostic_catalog_candidate.py`](../../../scripts/verify_diagnostic_catalog_candidate.py)
verifier likewise treats its `authority_refs` as registered references rather
than human authentication. Those names must not be widened into external
authority.

### Current structural gaming surface

The following inputs are intentionally claims or structural facts rather than
authenticated authority. They are important compatibility fixtures for any
future work:

- an initial stage raise and newly added review/approval data are additions,
  not drift regressions; an agent can place a stage and review block in the
  same pull request;
- advancing `human_review.date` is the normal ungated re-review path, while
  temporal validation rejects future values and an approval earlier than the
  review date but does not bind either date to a commit;
- the test suite deliberately proves the structural `CONFORMANT` fixture with
  an `https://example.invalid/...` approval locator;
- the same `human_review.record` path can retain its spelling while its
  contents change; current validation checks containment and non-emptiness,
  not authorship, semantic truth, or a content digest;
- an unchanged old approval tuple can be replayed after later changes because
  the current approval has no reviewed-commit or diff binding;
- reviewer, approver, and `project.human_owner` are not cross-authenticated,
  `intent.authority` is not resolved, and residual `accepted_by` is not
  matched to the project owner;
- `human_review` and approval objects permit local extension keys, so a local
  `verified: true`-style assertion has no upstream authority meaning;
- pull-request body policy acknowledgement is agent-writable and may alter a
  DRAFT drift result, while reviewed-stage protection remains blocking; the
  acknowledgement itself and any merge over a red result are not authenticated
  human acts; and
- the reusable workflow has only read-only contents permission and performs no
  review API lookup.

These seams do not make the current validator incorrect: its documentation
already limits the result to the mechanical subset. They are counterexamples
to any future attempt to relabel that subset as externally verified authority.

## GitHub provider facts

The following facts were checked against GitHub's official documentation on
2026-07-22. The policy in ADR 0005 is an inference from the threat model; the
provider documentation does not itself define AAP authority.

### Pull-request reviews and protected branches

GitHub can require approving reviews, code-owner review, dismissal of stale
approvals, approval of the latest reviewable push by someone other than its
pusher, signed commits, restricted pushes, and disabled bypass. Classic branch
protection does not necessarily constrain administrators or custom bypass
roles unless configured. GitHub also prevents an author from approving their
own pull request.

Sources:

- [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
- [Approving a pull request with required reviews](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/approving-a-pull-request-with-required-reviews)

These controls can provide a strong native boundary when the relevant
control-plane and reviewer credentials are outside an agent's scope. A current
settings query, however, does not by itself prove that the same settings were
continuously effective when an older decision occurred. If an agent can use
the reviewer account's token or session, the provider records an account
action but cannot distinguish the agent's API action from the human's action.

### CODEOWNERS

GitHub uses the base branch's CODEOWNERS file to request and, when configured,
require a code-owner review. A pull request therefore cannot change only its
head CODEOWNERS file to redefine ownership for that same review. Any one listed
owner may satisfy the ordinary code-owner requirement, and owners require
write access.

Source: [About code owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)

CODEOWNERS is authorization and routing data. It does not prove that accounts
map one-to-one to distinct people, that a team has multiple active humans, or
that credentials remained outside automation control.

### Review event records

GitHub's pull-request review API exposes a review identity, account identity,
state, URL, submission time, and reviewed commit identity. Submitted reviews
can be dismissed, and review text can be updated.

Source: [REST API endpoints for pull-request reviews](https://docs.github.com/en/rest/pulls/reviews)

A future adapter should therefore bind provider-issued review and account
identifiers, the reviewed commit, the approval state observed at acceptance,
and separately observed current or dismissal state rather than trust mutable
prose or an in-repository URL alone. An adopter-recorded URL is display data:
authenticated API calls must be derived from canonical provider/repository/PR/
review IDs and an allowlisted HTTPS origin, never by sending credentials to an
arbitrary recorded URL. That would verify a narrower forge fact without
creating an SSRF or credential-exfiltration path; it would not verify human
presence or custody.

### Signed commits and tags

GitHub marks a commit or tag `Verified` when its GPG, SSH, or S/MIME signature
is successfully verified. For commits, GitHub stores a persistent verification
record and does not retroactively reverify it after later key expiry or
revocation. GitHub automatically GPG-signs web-interface commits;
authenticated bot or GitHub App commits can also be marked `Verified` under
its bot-verification rules. An SSH authentication key may be registered again
as a signing key.

Sources:

- [About commit signature verification](https://docs.github.com/en/authentication/managing-commit-signature-verification/about-commit-signature-verification)
- [Signing tags](https://docs.github.com/en/authentication/managing-commit-signature-verification/signing-tags)

A signature establishes use of a key or provider signing path. If an agent can
reach that key, SSH agent, or web session, a valid signature does not establish
human presence, understanding, or approval. Signature verification and human
authority must remain separate properties.

### OIDC and artifact attestations

GitHub Actions OIDC tokens bind workload claims such as repository, ref,
workflow revision, run, event, and actor account. Artifact attestations bind an
artifact to workflow/repository/commit provenance and can publish an immutable
transparency-log entry for public repositories.

Sources:

- [OpenID Connect reference](https://docs.github.com/en/actions/reference/security/oidc)
- [Artifact attestations](https://docs.github.com/en/actions/concepts/security/artifact-attestations)

Those mechanisms are valuable producer and artifact provenance. A valid token
or attestation from an agent-triggered authorized workflow does not establish
human review or acceptance. The OIDC actor is an account/event attribute, not
a human-presence attestation, and transparency supplies tamper evidence rather
than liveness evidence.

## Threat model and claim matrix

| Mechanism or observation | Narrow claim that may be supported | Claim that remains unsupported without another accepted anchor |
|---|---|---|
| In-repository review file | Exact bytes exist at a bound revision and meet structural rules. | A human wrote, read, or approved it. |
| Commit author/committer metadata | Git records the declared name/email and object relationship. | Real identity, human presence, or authorship of the prose. |
| Approval URL stored in adoption data | A syntactically valid locator was recorded with approver/time/scope fields. | The URL resolves, is approved rather than dismissed, binds the intended diff, or came from an eligible human. |
| Forge review event | The provider recorded a named account/event/state for a commit. | Exclusive human control of the account, informed review, or distinct real-world personhood. |
| CODEOWNERS + required review | The configured owner account/team and provider gate may constrain merge. | Multiple active humans, review quality, or historical continuous enforcement without retained evidence. |
| `SOLE_OWNER_ATTESTED` | The repository reports owner decision and no independent approval. | Independent review. |
| `INDEPENDENTLY_REVIEWED` | The repository reports an actual different human maintainer's qualifying approval. | Machine-authenticated real-world identity unless a separate anchor establishes it. |
| Valid commit/tag signature | The signature/key or provider signing path verified for the bytes. | Human presence, exclusive key custody, understanding, or approval. |
| OIDC token or artifact attestation | Workload/producer and artifact provenance under the issuer's claims. | Human review, human actor liveness, or policy acceptance. |
| Green CI | The named automation completed under its producer assumptions. | Human authority, complete semantics, or freedom from bypass/gaming. |
| Second forge account | Another account performed an event. | Another human performed it. |

### Adversary capabilities

1. **Repository-write agent.** It can change every in-repository policy file,
   decision record, lifecycle word, author field, and unsigned Git object. An
   in-repository assertion cannot be its own external trust anchor.
2. **Forge-credential-capable agent.** If it can use a maintainer/reviewer
   token or session, provider attribution to that account is not proof of human
   presence. Credential isolation must be an explicit accepted premise rather
   than an inference from the login name.
3. **Signing-capable agent.** If it can reach a signing key or provider signing
   path, valid cryptography proves the signing event but not the decision
   maker.
4. **Sole owner.** The owner cannot manufacture independent human review by
   self-approval or a second account. The honest process fact is
   `SOLE_OWNER_ATTESTED` plus separately reported automation.
5. **Mutable control plane.** Administrators, bypass actors, team membership,
   rulesets, stale-review policy, and signing configuration may change. Current
   state is not automatically historical state.
6. **Incomplete or hostile acquisition.** A shallow/missing/rewritten Git
   object set, unavailable provider, unauthenticated API result, rate limit, or
   missing audit history cannot be repaired with local prose.

## Minimal future verification boundary

ADR 0005 does not authorize this implementation, but the research identifies
the minimum boundary any successor provider capability would need to address:

- exact repository, PR, base, candidate head, reviewed commit/diff, merge
  commit/tree, and artifact-byte binding;
- stable review-event and account identities, the state observed at
  acceptance, later dismissal/revocation observations, submission time, and
  eligibility against a pinned governance roster;
- API requests derived only from canonical provider IDs and an allowlisted
  authenticated origin; arbitrary recorded URLs are never dereferenced with
  verifier credentials;
- code-owner, stale-approval, latest-push, direct-push, administrator, and
  bypass controls effective for the relevant event;
- evidence that provider and reviewer credentials/control-plane authority were
  isolated from the evaluated agent, within explicitly bounded assumptions;
- historical configuration continuity or an honest statement that only
  current configuration was observed;
- revocation, dismissal, key/account compromise, history rewrite, and
  append-only successor behavior; and
- fail-closed acquisition and typed non-completion for offline, unavailable,
  unauthorized, ambiguous, unsupported, or stale evidence.

Even if those conditions are met, the strongest default claim is that the
provider recorded an eligible account approving an exact candidate under the
controls actually checked. Human liveness, credential exclusivity, informed
semantic consent, organizational authority outside the configured roster,
and “no AI participated” remain unsupported unless a stronger accepted system
specifically establishes them.

## Decision consequences and remaining unknowns

The evidence supports a narrow decision now: keep external authority
verification unsupported in Foundation and preserve structural review
provenance as a useful but explicitly limited state.

The following remain intentionally undecided:

- provider-neutral versus GitHub-specific adapter boundaries;
- public check/reason identities and typed output for an optional external
  verifier;
- exact acceptance-record serialization, canonical digest, and redaction;
- trusted GatePlan, producer/caller status, and branch-protection projection;
- historical control-plane and audit-log retention;
- credential-isolation technology and compromise/recovery semantics;
- real-world identity, privacy, roster history, and account/person mapping;
  and
- whether any stronger capability is valuable enough to implement after
  Foundation.

Those are not gaps that this documentation-only slice may fill. They require
separate preregistered, reviewed decisions and must not become implicit adopter
obligations.

## Test implications

This documentation-only slice adds no executable tests. The full existing
[`test_validate.py`](../../../tests/test_validate.py) and
[`test_verify_phase0_acceptance.py`](../../../tests/test_verify_phase0_acceptance.py)
suites remain the compatibility oracle, including tests that:

- accept addition of review approval provenance and advancement of the review
  date without misclassifying them as regressions;
- accept the deliberately non-resolving `.invalid` approval URL on structural
  shape alone;
- keep acknowledgement at reviewed stages blocking;
- reject removal or rewrite of existing review/approval provenance; and
- prove that Phase 0 offline binding may be `VERIFIED` while effective
  acceptance remains `NOT_ESTABLISHED`.

Before any external authority adapter ships, its preregistered suite must
cover at least:

- nonexistent, wrong-origin, wrong-repository, and arbitrary recorded URLs,
  including the property that verifier credentials are never sent to them;
- same-path record rewrite, old-approval replay after a head change, wrong
  revision/scope, and same-head self-acceptance;
- dismissed/stale approvals, a latest-push mismatch, author/co-author/latest-
  pusher conflicts, roster changes, bypass, and historical-setting gaps;
- sole-owner, same-person second-account, AI, bot, external-opinion, and green
  CI cases that must never become independent human review;
- provider absence, `401`, `403`, `404`, rate limit, timeout, malformed data,
  and unsupported host as typed non-completion rather than PASS;
- signatures, OIDC, and artifact attestations remaining orthogonal to human
  authority; and
- properties that no in-repository mutation alone upgrades external authority,
  any revision/scope mutation invalidates its binding, unknown provider facts
  never coerce to success, and `SOLE_OWNER_ATTESTED` never equals
  `INDEPENDENTLY_REVIEWED`.
