# A three-layer starting pattern for AI coding-agent-assisted development

> **Informative status:** This guide is not part of the normative OpenDevs
> Agentic Assurance Profile. A project can use it without adopting AAP.
> Following it is not AAP adoption or conformance, and does not demonstrate
> that a system is secure, correct, complete, or fit for use.

This guide gives a portable, risk-scaled starting pattern for repositories
substantially changed by AI coding agents. It is deliberately smaller than a
complete engineering, security, or assurance program.

The file names, commands, line counts, and numeric review triggers below are
examples or project-local heuristics, not universal requirements. Reuse an
equivalent existing artifact instead of creating a parallel document. Adapt
the pattern to the repository's languages, architecture, risks, contribution
model, and deployment environment.

If a project adopts AAP, its pinned profile and local adoption artifacts
govern. The project should map useful existing material into those artifacts
rather than keep a second contract system; see [§7](#7-relationship-to-aap).

## 1. The three layers

The pattern separates three different questions:

| Layer | Question | Example artifact | What its presence does not prove |
|---|---|---|---|
| Persistent agent instructions | How should an agent work in this repository? | Root `AGENTS.md` or an equivalent repository instruction file | That the instructions were followed or that their policy is correct |
| Durable contract record | What must remain true, within which scope, and under whose authority? | Existing specification, ADR set, schema registry, or `docs/SYSTEM_CONTRACTS.md` | That the contract is enforced or verified |
| Controls, verification, and gates | What prevents a violation, checks the result, and blocks an unacceptable change? | Runtime guards and constraints, tests and analysis, required merge or release checks | That no defect, uncovered environment, or residual risk remains |

The links between the layers matter more than any suggested file name:

```text
agent instruction
  → affected contract and decision authority
  → owning enforcement boundary
  → verification and merge/release gate
  → result bound to the subject it supports, and known gaps
```

Instructions without an authorized contract can make an agent implement the
wrong intent consistently. A contract with no control or verification is a
declaration. A check with no named contract can preserve accidental behavior.

In this guide, a **contract-affecting change** is a change that may alter an
externally relied-on behavior, persisted state, a trust or authorization
boundary, a cross-component data shape, concurrency or recovery semantics, or
a final user-visible artifact. A project may use a wider definition.

## 2. Layer 1 — persistent repository instructions

A root instruction file such as `AGENTS.md` should keep the procedure an agent
needs repeatedly:

- the repository purpose and reading order;
- where canonical contracts and decisions live;
- build, test, lint, and inspection commands;
- the procedure for contract-affecting changes;
- the agent's write and execution boundaries;
- actions that require explicit human authorization; and
- stop and escalation conditions.

Per-change findings do not accumulate in this file. The current Issue, change
specification, pull request, or equivalent durable change record holds the
affected contract, search scope, evidence, open questions, and decisions.
Incident history and extended design rationale stay in the contract or
decision record, which the root instructions link rather than duplicate.

Keeping the project-local procedure readable in one screen—roughly 50 lines—is
a useful editing heuristic, not a compliance target. Do not remove mandatory
policy, adopter instructions, safety boundaries, or necessary commands merely
to meet a line count. In particular, an AAP adopter retains the root blocks
required by its pinned profile.

### 2.1 Example project-local procedure

The following block is an example to adapt, not text that every repository
should copy verbatim:

```markdown
## Contract-affecting changes

### Before implementation

- In the current Issue, specification, or pull request, name the affected
  system boundary and the property the change appears to protect. Link the
  existing approved source of intent. If authority is absent or ambiguous,
  mark the property as a candidate requiring a decision; do not promote
  observed implementation behavior to intended policy.
- Within the declared repository and integration scope, inspect the known
  production, transformation, enforcement, and consumption paths. Use `rg` or
  an equivalent repository search together with applicable route, schema,
  configuration, dependency, and external-consumer records. Record excluded
  scope and paths that could not be inspected.
- For a reproduced defect, explain which control or verification gap allowed
  it to occur or escape detection. Mark an unconfirmed explanation as a
  hypothesis, not a fact.

### Implementation and verification

- If an existing suite canonically owns the same contract, prefer strengthening
  it. Use a new suite when separation makes ownership, isolation, or failure
  diagnosis clearer.
- For a regression, exercise the relevant boundary and, where safe and
  practical, show that the check fails for the contract-related reason against
  known-bad behavior and passes against the fix. Record the exact command and
  revisions. If that comparison is not safe or reproducible, record why and
  provide the strongest available alternative verification.
- Before deleting or consolidating tests, map each distinct behavior, failure
  mode, and boundary protected by the old suite to replacement verification.
  Many-to-one and one-to-many mappings are allowed; assertion counts and
  coverage percentages alone do not establish equivalence.
- If failures recur or independently maintained implementations have diverged,
  request a bounded design review of common enforcement, shared libraries,
  generated implementations, cross-implementation contract tests, or
  deliberately retained duplication. A review trigger does not itself mandate
  refactoring or expand an urgent containment fix.

### Stop or escalate

- If unresolved product policy would materially change external behavior,
  persisted data, or a trust boundary, pause that part of the implementation
  and obtain a decision through the project's durable decision process. Batch
  non-blocking questions rather than interrupting once per finding.
- Do not replace high-impact boundary verification with a materially weaker
  proxy merely to simplify a test. If an exception is necessary, record its
  owner, reason, scope, and review or expiry condition.
- Do not hide a product behavior change inside test cleanup. Re-scope it as a
  behavior change and apply the corresponding review; keep the behavior and
  the tests that define it together when atomicity requires one change.
- Do not deploy, alter production data, access secrets, publish externally, or
  perform destructive or irreversible actions without the authority required
  by the repository.
```

Repository search cannot establish that every consumer has been found.
Reflection, dynamic routing, configuration, generated code, other
repositories, and external integrations can evade text search. Examples such
as UI, APIs, batch jobs, rendered PDFs, file adapters, or database adapters are
useful only when they exist in the system being changed. The change record
should state the inspected boundary and remaining unknowns instead of claiming
an exhaustive search.

## 3. Layer 2 — a durable contract record

Keep stable contracts in an existing canonical architecture or specification
system. If none exists, a file such as `docs/SYSTEM_CONTRACTS.md` is a workable
default. The path is illustrative: creating a second source of truth merely to
use this name makes later drift more likely.

Use a consistent record for each material contract:

| Field | Contents |
|---|---|
| Contract ID | A stable repository-local identifier |
| Contract statement | A precise, falsifiable proposition, including its conditions |
| Decision authority and status | The person or body that approved it and the decision record; otherwise clearly `candidate` or `unknown` |
| Scope and assumptions | Applicable components, versions, environments, actors, dependencies, and excluded conditions |
| Technical boundary and owner | The component or layer that owns enforcement and the responsible team or person |
| Production and transition points | Entrypoints that create or change the relevant data or state |
| Known consumers and observers | Internal and external readers, actors, outputs, and any unconfirmed consumer scope |
| Enforcement | Mechanisms that prevent or block an invalid state |
| Verification | Tests, analysis, inspection, or monitoring that checks the contract or its enforcement |
| Gate | Exact merge, release, or deployment check that blocks when applicable verification fails |
| Current evidence | Results bound to the exact subject they support—a revision, build or release, artifact digest, or deployment—with a reproducible locator and applicable execution context |
| Known gaps and review trigger | Unsupported or unchecked paths, responsible owner, and the event or date that reopens review |
| Related decisions and events | ADRs, incidents, Issues, pull requests, or restricted references that explain the contract |

An incident, commit, test, or existing implementation may show that a behavior
exists. It does not by itself prove that a human intended the behavior. The
record should distinguish an approved contract from a candidate reconstructed
by an agent.

Likewise, record `none identified` only after a stated search; use `unknown`
when the assessment has not established the answer. Silence should not be made
to mean either one.

### 3.1 Example contract record

This fictional authentication contract demonstrates the format; its domain,
paths, mechanisms, and thresholds are not generic requirements:

```markdown
### AUTH-CHALLENGE-01

- Contract statement: A server-issued challenge that is expired or already
  consumed cannot create an authenticated session.
- Decision authority and status: Approved — `<human decision record>`.
- Scope and assumptions: Interactive sign-in through the primary SQL-backed
  service; server clock is the expiry authority. Service versions before
  `<version>` are excluded.
- Technical boundary and owner: Session-issuance transaction; Identity team.
- Production and transition points: `POST /auth/challenges` creates a
  challenge; `POST /auth/sessions` consumes it.
- Known consumers and observers: Web sign-in, mobile sign-in, session audit
  exporter. External consumers beyond the published API are unknown.
- Enforcement: The session-issuance transaction atomically requires
  `used_at IS NULL` and `expires_at > evaluated_at`, marks the challenge used,
  and creates the session in one commit.
- Verification: `pytest tests/auth/test_challenge_contract.py` exercises the
  SQL adapter for expired, already-used, concurrent-reuse, and success cases.
- Gate: Required check `auth-contracts` on changes to the service and its
  challenge schema.
- Current evidence: `<run or artifact reference>` for `<full commit SHA>`,
  command `<exact command>`, environment `<image or runner version>`.
- Known gaps and review trigger: The alternate Mongo adapter has mock-only
  coverage; owner `<team>`; review before enabling that adapter in production.
- Related decisions and events: `<ADR>`, `<private incident reference>`,
  `<pull request>`.
```

The root agent instructions point to this record. They do not reproduce its
history, evidence, or open gaps.

## 4. Layer 3 — controls, verification, and change gates

Do not collapse these mechanisms into one field:

| Mechanism | Function | Examples |
|---|---|---|
| Enforcement or control | Prevents or blocks an invalid state or action | Authorization guard, state-machine transition, database constraint, schema, transaction condition, atomic compare-and-set |
| Verification | Checks whether a contract and its controls behave as stated | Contract, integration, end-to-end, property, migration, or concurrency test; static analysis; reproducible inspection |
| Gate | Stops a change or release when applicable verification fails | Required merge check, release gate, deployment policy |
| Evidence | Retained output showing what was checked for a bounded subject | Test or analysis result bound to a revision, release attestation, artifact digest, or deployment observation identified by deployment and time |

A test normally verifies behavior; it does not enforce production behavior. A
CI job may gate a change; its green status does not prove that the production
control exists, that every relevant path ran, or that no defect remains.

For a material contract, apply the following in proportion to impact and
feasibility:

1. Put enforcement at the boundary that owns the state or action.
2. Verify the contract through the relevant real boundary, not only through a
   substitute that omits the failure mode.
3. Make deterministic, relevant verification a required merge, release, or
   deployment gate where the platform supports it and the impact warrants it.
4. Treat skipped, not-run, or not-applicable verification as no result, not as
   evidence of a pass. Configure the gate so relevant events and paths cannot
   silently bypass it.
5. Bind retained evidence to the exact subject it supports: revision, build or
   release, artifact digest, or deployment. Record a reproducible locator and,
   where applicable, the command, environment, time window, and relevant
   versions. Do not treat a source revision as deployment evidence unless the
   deployment-to-revision or deployment-to-artifact binding is established.
6. When automation is impractical, a reproducible manual check can provide
   verification. Record its procedure, operator, bounded subject, result, and
   limitations.
7. Record an unavailable control, unverified adapter, flaky check, or
   non-reproducible or unowned procedure as a gap rather than describing the
   contract as protected.
8. Record any authorized exception with its decision owner, rationale, scope,
   compensating evidence, and expiry or review trigger.

### 4.1 Demonstrating regression sensitivity

For a reproduced defect, a strong regression demonstration shows both sides:

- in an isolated environment, the new check fails by reaching its
  contract-related assertion against a named known-bad revision, a controlled
  reversal of the fix, or a targeted mutation or fault injection; and
- the same check passes against the proposed revision under the recorded
  command and environment.

A missing test file, dependency failure, incompatible old build, timeout
unrelated to the contract, or setup failure is not red evidence for the
contract. Do not run exploit reproduction or destructive fault injection
against production. Keep actionable vulnerability inputs and sensitive results
in the project's restricted security channel; a public record may retain a
sanitized result.

When the comparison cannot be performed safely or reproducibly—common for
nondeterministic concurrency failures, unavailable historical dependencies,
hardware faults, or sensitive vulnerabilities—record the limitation and the
best alternative verification. Do not fabricate a red/green claim.

### 4.2 Deciding whether replacement verification is weaker

Replacing one test type with another is not automatically a weakening. A
replacement is materially weaker when, without compensating evidence, it
reduces one or more relevant dimensions:

- the real boundary or components exercised;
- the specificity of the expected-result oracle;
- the adverse, abuse, recovery, or concurrency cases covered;
- the concrete implementation or storage adapter exercised;
- fidelity to the supported runtime or deployment environment; or
- the check's ability to block an affected merge, release, or deployment.

A mock can strongly verify a caller's behavior against the mock. By itself it
does not verify a concrete database driver, transaction boundary, renderer,
exported file, external integration, or deployed configuration.

Before retiring tests, map the distinct protected behaviors, failure modes,
and boundaries to replacement verification. The mapping may be many-to-one or
one-to-many. Line counts, assertion counts, and aggregate coverage percentages
do not establish semantic equivalence.

### 4.3 Recurrence and duplicated enforcement

Repeated contract failures or materially divergent independent enforcement
points justify a bounded design review. The review considers, rather than
presupposes, the appropriate response:

- one common enforcement boundary or library;
- generated implementations from one specification;
- cross-implementation contract tests;
- deliberately retained duplication with parity evidence; or
- a local containment fix plus assigned follow-up work.

A project may adopt a local trigger such as “a second independently confirmed
recurrence after an earlier fix” or “three independently maintained production
enforcement points.” If it does, define the counting rule. Tests, generated
copies, and simple delegating wrappers normally should not count as independent
production enforcement. The threshold triggers review, not automatic
refactoring, and does not prevent an urgent containment fix when delay would
increase harm.

## 5. Change-level handoff and review

The three durable layers are connected by the current change record. For a
contract-affecting change, that record should make the following inspectable:

- the affected contract IDs, or a clearly marked candidate contract;
- the source and status of intent, including the human decision still needed;
- the repository and integration scope inspected, exclusions, and unknown
  consumers;
- controls added, removed, or changed;
- verification commands, exact results, and the revisions, builds, releases,
  artifacts, or deployments they cover;
- gate changes and any path or event on which the gate does not run;
- known gaps, exceptions, and review triggers; and
- behavior or evidence that a reviewer should challenge independently.

For high-impact changes, use review proportionate to the risk. A human reviewer
or a fresh agent context can challenge the contract, diff, and evidence without
depending solely on the implementing agent's narrative. Deterministic checks
add reproducible evidence, but are not automatically independent of the person
or agent that authored their oracle. Do not call a review or evidence
independent merely because the context is fresh; the claim needs a real
separation of basis, authority, or verification source.

An agent can draft a candidate contract and assemble evidence. It should not
invent product policy, manufacture approval, or accept material unresolved
risk for the accountable human. When sensitive security information is
involved, keep the decision and reproduction details in a restricted channel
and publish only a safe summary.

## 6. What this pattern does not cover

This starting pattern does not by itself supply:

- a threat model, security review, penetration test, or formal proof;
- complete requirements or product decision governance;
- dependency, build, release, or artifact provenance;
- production monitoring, incident response, backup, or recovery validation;
- privacy, legal, regulatory, or domain-specific controls;
- proof that every producer, consumer, integration, or environment was found;
  or
- evidence that the pattern improves outcomes in every repository.

Add the practices required by the system's actual risk. Do not describe this
three-layer pattern as a complete safety program.

## 7. Relationship to AAP

This guide is independently usable and non-normative. It also uses distinctions
that AAP makes more completely:

| Starting-pattern material | Possible AAP destination after adoption |
|---|---|
| Repository agent instructions | Root `AGENTS.md` plus the pinned adoption reading order |
| System description and contract scope | Mapped system artifact |
| Approved contract or invariant | Applicable claim or invariant register entry |
| Enforcement and verification | Separate enforcement and verification references |
| Bounded result | Evidence reference bounded to the claimed revision, release, artifact, or deployment |
| Counterexample or stale assumption | Defeater candidate |
| Known gap or unsupported condition | Residual candidate |
| Human decision and approval | Applicable authority, review, or acceptance record |

These are mapping hints, not an alternate definition of AAP fields. An adopter
follows [PROFILE.md](../PROFILE.md), starts with
[docs/ADOPTION.md](ADOPTION.md), and uses
[docs/MAPPINGS.md](MAPPINGS.md) to reuse equivalent artifacts. It should keep
existing AAP IDs rather than create a competing `Contract ID` namespace.

The root blocks, material-change workflow, human authority, evidence,
independent-review, residual, and disclosure obligations of an adopted profile
remain in force. A line-count heuristic, local test rule, or this guide cannot
weaken or replace them.
