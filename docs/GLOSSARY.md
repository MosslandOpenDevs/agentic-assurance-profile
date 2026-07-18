# Glossary

Plain-language definitions of the profile's vocabulary, for human owners meeting these terms for the first time. The normative definitions live in [PROFILE.md](../PROFILE.md); this glossary restates them without changing them, and cites the governing section for each term. Where this glossary and PROFILE.md appear to disagree, PROFILE.md governs.

English terms are canonical throughout the profile and its artifacts. Established Korean glosses from the repository's [Korean README](../README.ko.md) appear in parentheses; use them when discussing the profile in Korean, but keep the English term in artifact files.

If you are a human owner about to review an adoption proposal, read this together with the [Review Guide](REVIEW-GUIDE.md). If you are setting up adoption mechanically, see the [Adoption Guide](ADOPTION.md).

## 1. The core chain

The profile's model is a chain ([PROFILE.md §2](../PROFILE.md)):

```text
Intent → Claims → Invariants → Enforcement → Evidence → Defeaters → Residuals → Human acceptance
```

Each link answers one question about the system. The terms below follow the chain in order.

### Intent (의도)

What the humans want the system to be: the human-owned description of purpose, users, scope, non-goals (비목표), authority, and acceptable trade-offs. Intent belongs to a named human owner, never to an agent — an agent may implement within it but may not redefine it. Example: "This is an invoicing tool for our own staff; processing payments for third parties is a non-goal." ([PROFILE.md §2.1](../PROFILE.md), [§3](../PROFILE.md))

### Claim (주장)

Something the project asserts outward — a proposition asserted to a user, operator, integrator, auditor, or the public. A claim is a promise someone else might rely on, so its wording may not exceed what the evidence supports. Example: "We never store plaintext passwords." ([PROFILE.md §2.2](../PROFILE.md), [§8](../PROFILE.md))

### Invariant (불변조건)

A proposition that must remain true across every valid state and permitted change — not a feature, but a condition no feature is allowed to break. PROFILE.md's own example: the feature is "Users may authenticate with a wallet"; the invariant is "An expired or consumed challenge cannot create a valid authenticated session." ([PROFILE.md §2.3](../PROFILE.md))

### Enforcement (강제 수단)

A mechanism that prevents or blocks violation of an invariant — a database constraint, authorization guard, cryptographic check, schema, state-machine guard, transaction boundary, or policy enforcement point. Enforcement stops the bad state from ever existing. Example: a `UNIQUE` constraint on the email column, which makes a duplicate account impossible rather than merely detectable. Not to be confused with **verification**, which checks rather than prevents — see [§2.4](#24-enforcement-vs-verification) below. ([PROFILE.md §2.4](../PROFILE.md))

### Verification (검증)

A mechanism that checks whether declared properties and controls behave as claimed — tests, static analysis, reproducible inspection, migration verification, runtime assertions, monitoring, or independent reproduction. The profile's slogan: **tests verify; controls enforce** — and a critical invariant should have both. Example: a test that replays an expired session token and asserts the request is rejected. ([PROFILE.md §2.5](../PROFILE.md))

### Evidence (증거)

A reproducible artifact linked to a bounded revision, build, release, artifact digest, or deployment — something a skeptic could re-check. An AI agent's narrative that a check passed is not evidence by itself. Example: the CI log of a test run tied to a specific commit SHA, not the sentence "all tests passed." ([PROFILE.md §2.6](../PROFILE.md), [§11](../PROFILE.md))

### Defeater (반증 요인)

A concrete reason a claim or assurance argument may be false, incomplete, stale, or inapplicable — the honest counterargument, recorded instead of hidden. Example: "The backup-restore claim was verified against a 100 MB database; production is 40 GB and a restore at that size has never been exercised." Not to be confused with a **residual** — see [§2.2](#22-defeater-vs-residual) below. ([PROFILE.md §2.7](../PROFILE.md), [§12](../PROFILE.md))

### Residual (잔차)

A known limitation, unverified assumption, accepted inconsistency, unsupported condition, or remaining doubt after a release or operational decision — what is knowingly left imperfect. The profile's stance: residuals are expected; hidden residuals are not. Example: "Rate limiting is per-server; if a second server is added, the effective global limit doubles. Accepted while we run a single server." ([PROFILE.md §2.8](../PROFILE.md), [§12](../PROFILE.md))

### Human acceptance (인간의 수용)

The named human owner's explicit, recorded decision to carry a risk or approve a contract — the end of the chain, and the one link an agent can never supply. Critical residuals must have explicit human acceptance, recorded with the accepter's name and date; an agent must not accept a critical residual on the owner's behalf. Example: the owner writes "accepted, single-server deployment is our reality this year" and the register records their name and the date. ([PROFILE.md §2](../PROFILE.md), [§3](../PROFILE.md), [§12](../PROFILE.md), [§15](../PROFILE.md))

## 2. Easily confused pairs

These four pairs cause most first-contact misreadings. Each pair is two different questions, not two strengths of the same question.

### 2.1 `VERIFIED` vs `INTENDED`

**`VERIFIED`** answers "does it demonstrably work?" — the guard exists and reproducible evidence proves it behaves as described. **`INTENDED`** answers "did a human decide this is what the system should do?" — a current human-approved specification, invariant, or decision supports the behavior. They are independent axes: a behavior can be `VERIFIED` yet intent-`UNKNOWN` — the code provably enforces a 10-per-minute rate limit, and nobody knows whether 10 was ever chosen by a human or invented by an agent. Verification is about evidence ([PROFILE.md §4](../PROFILE.md) conclusion classification); intent is about authority ([PROFILE.md §4](../PROFILE.md) behavior classification, [§3](../PROFILE.md)). Current production behavior is evidence of current behavior — not automatic proof of intended behavior.

### 2.2 Defeater vs residual

A **defeater** (반증 요인) is a concrete reason a claim might be false — an active challenge to the assurance argument that demands an answer: refute it, mitigate it, or downgrade the claim. A **residual** (잔차) is a known limitation someone decided to live with — the challenge has been examined and the remaining risk is carried, on the record. A defeater that survives scrutiny often becomes a residual once the owner accepts what it implies. Defeaters live in `DEFEATERS.yaml`; residuals in `RESIDUALS.yaml`. ([PROFILE.md §2.7–2.8](../PROFILE.md), [§12](../PROFILE.md))

### 2.3 Accept vs resolve (residual dispositions)

**Accept** (수용) records that the owner knowingly carries the risk: the residual stays real, and the register records `accepted_by` (who), `accepted_at` (when), and ideally an `acceptance_rationale` (why). **Resolve** means the risk was removed by a fix: the limitation no longer exists, and the register records a `resolution_note` pointing at the remediation. Accepting is a human decision about an unchanged world; resolving is a changed world. A residual must not be closed solely because no recent incident was observed — quiet is not a fix. See [templates/RESIDUALS.yaml](../templates/RESIDUALS.yaml) for the fields. ([PROFILE.md §12](../PROFILE.md))

Related Korean caution: **adoption** (채택) — taking the profile into a repository — and **acceptance** (수용) — an owner's decision to carry a residual — are different acts; keep the glosses distinct.

### 2.4 Enforcement vs verification

**Enforcement** (강제 수단) prevents violation: a database constraint makes the invalid state impossible. **Verification** (검증) checks that a property holds: a test tries to produce the invalid state and observes the refusal. **Tests verify; controls enforce** ([PROFILE.md §2.5](../PROFILE.md)). A test suite with no enforcing control means the invariant holds only as long as everyone keeps running (and passing) the tests; a control with no verification means nobody has checked the control actually works. A critical invariant should have both.

## 3. Status vocabularies

The fixed word lists that appear in the YAML artifacts. Values are code literals — always uppercase, always English.

### Conclusion statuses ([PROFILE.md §4](../PROFILE.md))

How well-supported a conclusion about the system is:

| Status | Meaning |
|---|---|
| `VERIFIED` | Reproducible evidence directly supports it. |
| `INFERRED` | Indirect evidence supports it. |
| `UNKNOWN` | Evidence is insufficient. |
| `CONTRADICTED` | Available evidence conflicts with it. |

**`UNKNOWN` is a first-class honest answer, not a failure.** When certainty is unavailable, the profile requires recording `UNKNOWN`, a defeater, or a residual rather than inventing confidence ([PROFILE.md §15](../PROFILE.md)). An honest `UNKNOWN` is worth more than a fabricated `VERIFIED`.

### Intent classifications ([PROFILE.md §4](../PROFILE.md))

Why an observed behavior exists:

| Status | Meaning |
|---|---|
| `INTENDED` | Supported by a current human-approved specification, invariant, or decision. |
| `ACCIDENTAL` | Known to exist but not desired. |
| `COMPATIBILITY` | Retained to preserve an explicit compatibility obligation. |
| `UNKNOWN` | Evidence is insufficient to determine intent. |
| `DEPRECATED` | Temporarily supported with an approved removal path. |

The same honesty rule applies: intent-`UNKNOWN` is a valid resting state, and only a human can move a behavior from `UNKNOWN` to `INTENDED`.

### Residual statuses ([PROFILE.md §12](../PROFILE.md); [schemas/residuals.schema.json](../schemas/residuals.schema.json))

| Status | Meaning |
|---|---|
| `OPEN` | Recorded, no disposition yet. |
| `ACCEPTED` | A named human decided to carry the risk (`accepted_by`, `accepted_at`). |
| `RESOLVED` | The limitation was removed by a fix (`resolution_note`). |

### Defeater statuses ([PROFILE.md §12](../PROFILE.md); [schemas/defeaters.schema.json](../schemas/defeaters.schema.json))

| Status | Meaning |
|---|---|
| `OPEN` | The counterargument stands unanswered. |
| `MITIGATED` | Its force is reduced but not eliminated. |
| `RESOLVED` | It was answered — refuted or fixed. |
| `WITHDRAWN` | It turned out not to apply. |

### Disclosure classes ([PROFILE.md §13](../PROFILE.md))

How publicly a piece of assurance material may appear (공개 등급):

| Class | Meaning |
|---|---|
| `PUBLIC` | Full content may live in the public repository. |
| `SUMMARY_ONLY` | Only a non-actionable summary and status are public. |
| `RESTRICTED` | Never committed to a public repository. |
| `EMBARGOED` | Held privately until remediation and coordinated disclosure. |

### Claim proof tiers ([PROFILE.md §8](../PROFILE.md))

How strong the evidence behind a claim is (증명 등급):

| Tier | Meaning |
|---|---|
| `INDEPENDENTLY_VERIFIABLE` | A third party can reproduce the result without privileged access. |
| `OPERATIONALLY_AUDITABLE` | Evidence exists but requires controlled access. |
| `OPERATOR_ATTESTED` | The claim currently depends on operator process or statement. |
| `NOT_CLAIMED` | The project explicitly declines to assert the property. |

Claim wording must not exceed the support of its evidence tier — an `OPERATOR_ATTESTED` claim may not be phrased as if it were independently verifiable.

## 4. Process terms

### Adoption (채택)

Taking the profile into a repository: pinning the upstream profile, creating the local artifacts, and running the review workflow. Creating the files alone is not adoption — adoption is complete only when the pin, human-approved intent, claims and invariants, evidence links, explicit unknowns, and residual ownership are all live in the project's normal change process. ([PROFILE.md §5](../PROFILE.md), [§16](../PROFILE.md); [ADOPTION.md §6](ADOPTION.md))

### Archaeology (고고학적 복원)

The read-only reconstruction of an existing repository that initial adoption must begin with: recovering purpose, entities, trust boundaries, claims, candidate invariants, enforcement, evidence, ambiguous behavior, defeaters, and gaps — from what actually exists, before changing anything. Example: reading the schema, migrations, tests, and CI history to reconstruct what the system enforces today, without touching functional code. ([PROFILE.md §7](../PROFILE.md); [ADOPTION.md §4.1](ADOPTION.md))

### Brownfield (기존 저장소 채택)

Adoption of a repository that already exists and already behaves — as opposed to greenfield, a repository adopting from the start. Most adoption is brownfield, which is why the archaeology stage exists: the intent behind existing behavior must be recovered and reviewed, not assumed. ([PROFILE.md §7](../PROFILE.md); [ADOPTION.md §4](ADOPTION.md))

### Conformance (적합)

The bounded statement that a specific revision or release represents its contracts, controls, evidence, counterarguments, and remaining uncertainty according to the profile. It is deliberately modest: conformance does not mean the project is universally secure or bug-free, and it is not a security certification. Example: "revision `abc1234` conforms" means its promises and its doubts are both inspectable at that revision — not that it has no bugs. ([PROFILE.md §17](../PROFILE.md), [§1](../PROFILE.md))

### Pin (고정)

Fixing the adopted profile to an exact version **and** full 40-character commit SHA in `.agentic-assurance/adoption.yaml`, so that "the profile" always means one immutable text. A floating branch like `main` is never a valid sole reference, and an agent must not move the pin silently — upgrades are explicit reviewed changes. ([PROFILE.md §16](../PROFILE.md); [ADOPTION.md §2](ADOPTION.md))

### Remediation (보완)

The fixing stage: addressing gaps, missing controls, and accepted findings through separate, scoped changes after the human intent review — never mixed into the archaeology, and for critical work, never performed by the same sole agent context that audited it. Example: a follow-up pull request that adds the missing enforcement for one invariant, referencing the gap it closes. ([PROFILE.md §7](../PROFILE.md), [§10](../PROFILE.md); [ADOPTION.md §4.4](ADOPTION.md))

### Material change (중대한 변경)

A change that affects externally visible behavior, persistent data, authentication, authorization, privacy, security, billing, governance, recommendations, classification, migration, deployment, public claims, or critical dependencies. Material changes trigger the full change workflow — intent, affected claims and invariants, before/after behavior, failure cases, migration, evidence, and expected residual impact stated before implementation. Example: changing a session-expiry rule is material; renaming an internal variable is not. ([PROFILE.md §9](../PROFILE.md))

### Provenance (근거 출처)

Who actually produced a piece of cited evidence, established from the commit record rather than assumed. In an agent-built repository, committed prose — comments, READMEs, design notes — is often agent-authored, so a document saying "this is intentional" may just be an earlier agent's narrative: check the introducing commit's authorship (`git blame`, `Co-Authored-By:` trailers) before citing prose as intent authority. Agent-authored prose describes behavior; it never establishes human intent. Authority comes from a human act — a reviewed merge, a recorded review outcome — not from who typed the text. Machine-verifiable evidence (schema constraints, response headers, command output, code behavior) does not depend on authorship. ([PROFILE.md §7](../PROFILE.md); [ADOPTION.md §4.1](ADOPTION.md))

### Two-ledger model (두 장부 모델)

Keeping two logically separate records: a **public assurance view** — a sanitized projection safe for the repository and its users — and a **restricted security record** for material that would be dangerous public: unpatched vulnerability details, privileged topology, private evidence, reporter identity. Public assurance is a projection, not the complete private security record; suspected exploitable findings route through the private channel, never a public issue. ([PROFILE.md §13](../PROFILE.md); [README](../README.md) "Two-ledger model"; [DISCLOSURE-AND-ISSUES.md](DISCLOSURE-AND-ISSUES.md))

## Related documents

- [PROFILE.md](../PROFILE.md) — the normative text every entry here cites
- [REVIEW-GUIDE.md](REVIEW-GUIDE.md) — for the human owner: what your agent will bring you, and how to answer
- [ADOPTION.md](ADOPTION.md) — the practical adoption walk-through (agent-facing)
- [templates/AGENTIC_ASSURANCE.md](../templates/AGENTIC_ASSURANCE.md) — the adopter-side entry document
- [templates/RESIDUALS.yaml](../templates/RESIDUALS.yaml) — the residual register fields referenced in §2.3
