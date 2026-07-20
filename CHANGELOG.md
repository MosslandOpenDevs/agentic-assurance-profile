# Changelog

All notable changes to the OpenDevs Agentic Assurance Profile will be documented here.

## Unreleased

- Documented the v0.4.x reusable-workflow event limitation: drift evaluation
  runs only for `pull_request`, so a green push or other non-pull-request run
  is not a drift verdict. Push remains outside the documented drift scope;
  applicability for other caller events remains tracked in
  [#43](https://github.com/MosslandOpenDevs/agentic-assurance-profile/issues/43).
  Documentation only; no validator or workflow behavior changes.

- Added a non-normative [v0.5 working design and delivery plan](docs/V0.5-DESIGN.md)
  that records the verified v0.4.0 baseline, separates measured architecture
  pressure from unknown adopter usability, and separates the always-required
  Foundation, evidence-gated Progressive UX, and conditional Canonical Engine
  tracks. It defines phased contracts, expected-outcome-ledger parity,
  canonical-engine go/no-go criteria, CLI authority boundaries, compatibility,
  test strategy, release blockers, and open-issue disposition. The proposal's
  lifecycle and acceptance rules are explicit. Documentation only; no profile
  obligation, schema, validator, template, or workflow behavior changes.

## v0.4.0 — 2026-07-20

A usability-focused minor: makes adoption harder to get wrong at the
entry point, turns the invariant register into a `core` obligation, and
hardens the `archived` profile (exclusivity + a required non-empty mapped
system artifact + an untouched-template guard; semantic §6.6 content
enforcement remains tracked in #40).

- **Profile classification is now an explicit first step of adoption.**
  `docs/ADOPTION.md` §4.0 ("Classify the profile first") makes profile
  selection an evidence-based finding — a cheap §5 trigger scan with
  `file:line` evidence, a bias toward escalation, an adversarial
  self-check of the cited evidence, and the classified set declared in
  `adoption.yaml`'s enforced `profiles:` field rather than only in the
  handoff prose. The prior "start at `core` / lite is the default /
  select `core` only at first" framing is flipped throughout (§0, §3.0,
  §3.2, §4.0, §5); `README.md` and `README.ko.md` route a bare "apply
  this profile" prompt into classify-first; and `PROFILE.md` §5
  clarifies that the smallest applicable set covers the system's actual
  nature. Documentation only — no schema or validator change.
- **Existing tool output has a stated position in the core model.**
  `docs/MAPPINGS.md` §5 (new, non-normative) shows how to reference what a
  repository's tools already produce — specification workflows, tests,
  scanners and code-review tools, agent change records, build attestations —
  from the registers instead of restating their results by hand. Each tool
  class is placed against what it does *not* establish, because an assurance
  argument fails when a strong answer to one question is filed as the answer
  to another: a review tool reporting no findings is coverage, not proof, and
  an agent change record is evidence of the action, not of correctness. §5.2
  binds an evidence reference to a revision, release, artifact, or deployment
  (`PROFILE.md` §11) and covers the restricted case; §5.5 states what no tool
  supplies — intent, claim wording, defeater disposition, residual acceptance
  — and that an agent-drafted record carries human authority only when the
  owner's own approval act anchors it (`PROFILE.md` §7). `README.md` and
  `README.ko.md` route to it from the "complements your existing toolchain"
  claim, which previously had nothing behind it. Documentation only — no
  schema or validator change.
- **Profile composition is now explicit and aligned with validation.**
  Every non-`archived` specialized profile implicitly inherits §6.1
  `core` obligations. For an active adopter, the canonical smallest
  declaration is `[core]` when no specialized trigger fires; otherwise it
  lists every fired specialized profile and omits `core` (an explicit
  `core` remains allowed and changes no obligation). `archived` is
  normatively exclusive, replaces §6.1–§6.5 active obligations while
  retaining the pin and root agent instructions, and records its four §6.6
  facts in the system artifact resolved from `paths.system` (default
  `assurance/SYSTEM.md`). This closes the gap where the validator enforced
  exclusivity and artifact placement more strongly than the authoritative
  profile text. The validator rejects an empty archived system artifact at
  every stage and, at `HUMAN_REVIEWED` or `CONFORMANT`, any of the four exact
  shipped archived placeholders. It still does not determine whether replacement prose states
  all four facts or is truthful; that structured semantic enforcement remains
  #40, with the owner review guide as the explicit content backstop.
- **At least one invariant is now required at `core`** (previously an
  obligation only from `service`). `PROFILE.md` §6.1, the lite envelope
  schema (`invariants` now required), and the split-layout file-presence
  and non-emptiness checks all enforce it — a repository with nothing
  that must stay true has not found its invariants yet.
- **A minimal lite template** (`templates/assurance.minimal.yaml`) ships
  the required-minimum `core` adoption — purpose, non-goals, system, one
  invariant, one residual — with only the fields an adopter must fill, so
  the full `templates/assurance.yaml` is now the expanded alternative rather
  than the default minimal starting point. The self-check validates both
  templates, so neither can drift.
- **The adoption template no longer defaults to `core`.**
  `templates/adoption.yaml` (and the copy example in
  `AGENTIC_ASSURANCE.md`) ship a `REPLACE_WITH_CLASSIFIED_PROFILE`
  sentinel in `profiles:` — the central self-check substitutes it to a
  valid enum, but an adopter who copies the template must replace it with
  the classified set or validation fails on the unfilled placeholder, so
  no adoption silently inherits a `core` default. (This is a completion
  guard; detecting a *wrong* profile against the actual code remains the
  under-classification backstop, tracked in #41.)
- **The normative stage and entry-artifact contracts are now explicit.**
  `PROFILE.md` §17 defines the cumulative `DRAFT`, `HUMAN_REVIEWED`, and
  `CONFORMANT` ladder rather than leaving its substance only in the adoption
  guide and schema descriptions. DRAFT includes applicable semantic checks;
  HUMAN_REVIEWED requires a recorded classification (UNKNOWN allowed) for
  every active critical invariant. Independently of review stage, every active
  `VERIFIED` critical invariant needs at least one enforcement and one
  verification reference; under `service`, every critical invariant needs
  both references regardless of conclusion status. A conformance claim requires an explicit
  `adoption_stage: CONFORMANT`, where no critical residual remains `OPEN`, no
  claim or critical invariant is `CONTRADICTED`, every `VERIFIED` critical
  invariant has evidence, every critical invariant has an intent other than
  `UNKNOWN` or `ACCIDENTAL`, and public repositories carry no `RESTRICTED` or
  `EMBARGOED` register entry. At every stage, placeholder substitution remains
  schema-only: it cannot fabricate an invariant mechanism or authority, a
  residual acceptance/resolution record, or a closed-defeater resolution.
  Closed defeater meanings and their mandatory non-blank disposition grounds
  are now normative in §12. §17 also distinguishes the adopter's
  human-approved full normative claim from the validator's structural and
  mechanically decidable subset. §6.1 now expressly
  requires root `AGENTIC_ASSURANCE.md` and root `AGENTS.md` reading-order
  artifacts, and defines one system-description content minimum regardless of
  lite, split, or mapped layout. The fuller §7 reconstruction remains the
  normal `SHOULD`, not a mapping-only hard requirement.
- **Input and path handling now fail closed and remain resource-bounded.**
  Duplicate mapping keys in YAML or JSON are rejected instead of silently
  using the last value. YAML merge keys are rejected before PyYAML can expand
  a merge-alias DAG; ordinary anchors and aliases remain supported under the
  logical-node bound, including for pre-v0.4 last-key-wins base comparison.
  Policy YAML is normalized to the JSON-compatible data
  model used by the schemas: binary, set/ordered-map, cyclic, and non-finite
  values are rejected, while YAML dates are normalized to ISO strings.
  Non-finite JSON constants and non-UTF-8 policy inputs are rejected; every
  policy YAML input is limited to 5,242,880 bytes and
  100,000 logical nodes after alias expansion, preventing compact alias-DAG
  denial of service. Policy JSON is limited to 10,485,760 bytes, 256 nesting
  levels, and 500,000 nodes; YAML and JSON numeric source tokens are limited to
  4,096 characters on every supported Python version. Invalid implicit YAML
  dates and other scalar-constructor failures now produce controlled diagnostics
  rather than tracebacks. Adopter-owned prose and review files read directly by
  the validator are each limited to 5,242,880 bytes: the two root assurance
  guides, mapped system artifact, required service threat model, and declared
  human-review record. The self-check matrix now includes Python 3.14 while
  retaining 3.10 as the compatibility floor. Self-check meta-validates every JSON Schema and scans
  tracked filenames losslessly even when a filename contains a newline;
  schema references use an explicit offline registry, so an unresolved or
  remote `$ref` fails with a controlled diagnostic without network access;
  malformed approval timestamps and HTTP(S) approval URLs are checked
  explicitly at every stage rather than depending on optional JSON Schema
  format packages. They produce ordinary diagnostics rather than a parser
  traceback; approval URLs must name a host, contain no user information, use
  a numeric in-range port when one is present, use a DNS/IPv4-style or
  bracketed hexadecimal IPv6 host, and contain only valid percent escapes and
  RFC 3986 path/query/fragment characters under the profile's deliberately
  narrow ASCII HTTP(S) URL grammar (percent-encoded path/query/fragment data
  must decode as UTF-8; internationalized hosts use an ASCII IDNA A-label
  spelling; the complete RFC 3986 host surface is not claimed).
  Public metadata pointers `security.restricted_record` and residual
  `private_detail_location` now share a bounded non-actionable ASCII label
  grammar (letters, digits, dot, underscore, and hyphen; at most 128
  characters), so syntactically actionable URLs, slash paths, and `@` account
  identifiers cannot pass merely because they are nonblank. The validator
  cannot determine whether an otherwise valid opaque label is itself a secret;
  never place a secret there. Replace an actionable locator with a public label
  such as `external_private_system` and keep the locator only in the restricted
  system.
  Non-empty policy strings made only of separators
  or invisible format characters are rejected with their JSON path instead of
  satisfying a required semantic value. Release identifiers use canonical
  ASCII SemVer numbers (no leading zero; release candidates start at `rc.1`),
  and `VERSION` is one exact token line with no surrounding whitespace or
  additional lines. Full-string schema tokens (repository slugs, commits, stable IDs,
  and references) use true end-of-input assertions so a final newline cannot
  bypass their grammar.
  Filesystem artifact/root fields require repository-relative lexical paths
  (an absolute spelling is rejected even when it points inside the project),
  are limited to 4,096 characters, and `paths:` is limited to 256 mappings,
  and component routing globs must use the same canonical path domain:
  absolute spellings and empty, `.` or `..` components now fail instead of
  silently matching nothing. Duplicate component globs and IDs remain accepted
  for v0.3 compatibility and count toward routing limits. Every explicitly
  carried lite mapping plus a present DRAFT review-record
  path receives the same containment/trust check as an active artifact. Every
  trust-checked artifact/root field and every active routing glob in
  `components[].paths` rejects C0 controls and DEL; `components[].tests` is
  recorded metadata, not a trust-checked or routing path field in this release.
  An inferred profile checkout becomes a trust root and its `VERSION` is
  compared with the adoption pin. A Git-backed profile checkout must also have
  `HEAD == upstream.commit`, must execute that checkout's real
  `scripts/validate.py`, and must have clean consumed validation resources at
  that HEAD (`VERSION`, `requirements-ci.txt`, `scripts/`, and `schemas/`,
  including untracked files under the resource directories). `PROFILE.md` §16
  now states explicitly that a release or pre-release SHA is the matching
  published tag's target and that a published tag cannot be deleted, moved, or
  reused; this documents the already-enforced canonical tag rule and adds no
  new adopter action or workflow behavior. An archive
  without Git metadata emits an explicit warning that only `VERSION`, not
  commit identity or resource cleanliness, was verified. Adopter artifacts must resolve
  inside the project boundary without
  resolving into Git metadata (`.git`), the pinned profile checkout, or the
  schema tree, including case- or normalization-alias spellings on filesystems
  that treat those names as identical. A rejected lite assurance path is not
  reopened by reviewed-stage placeholder scanning. Portable relative symlinks
  whose every hop remains inside the adopting project continue to work and now
  emit a CODEOWNERS warning naming the lexical path, resolved target, and
  target parent that need owner coverage. Absolute symlinks and relative
  escape-then-reentry spellings fail even when they happen to resolve inside
  HEAD, because a detached BASE worktree would give them a different identity.
- **Self-check workflow linting remains bounded.** The digest-pinned
  `actionlint` image moves from 1.7.7 to 1.7.12, and Python-only workflow
  bodies (including the multi-thousand-line materializer) run directly under
  isolated Python custom shells instead of appearing to shellcheck as bash
  heredocs. The greater-than-64-KiB materializer uses the equivalent `python3`
  shell spelling so actionlint 1.7.12 does not feed it into that release's
  pre-start Pyflakes stdin path, which can deadlock at the runner pipe limit
  (`rhysd/actionlint#650` and `rhysd/actionlint#651`); regression tests compile
  and execute the body instead. Smaller Python steps remain Pyflakes-checked.
  This is CI maintenance only; it adds no adopter action and does not change
  workflow behavior.
- **Pull-request routing is bounded and safe at its inputs and CI sinks.**
  The drift job explicitly checks out the pull request's head SHA rather than
  GitHub's default synthetic merge ref, keeping HEAD-side policy reads aligned
  with the SHA used for changed-file and evidence diffs.
  Component path globs now use a dynamic-programming matcher instead of a
  backtracking regular expression. Count and length limits are supplemented by
  20,000,000-cell aggregate glob-work and 20,000,000-unit impact-directive-scan
  budgets; the changed-file list, PR body, and assurance diff are capped at
  33,554,432, 1,048,576, and 20,971,520 bytes respectively, so many
  individually valid inputs cannot recreate an unbounded CI workload. In PR
  routing, changed-file records must be canonical repository-relative Git
  paths (with one legacy leading `./` normalized); absolute paths, escapes,
  repeated prefixes, and `.`/`..` or empty components fail closed instead of
  silently missing a component glob. In PR
  prose, impact IDs, a `none` directive and its mandatory `Reason:`, and an
  optional `Assurance policy change:` acknowledgment count only inside a
  leading top-level directive block before ordinary visible content. The block
  contains exactly one impact declaration when impact is asserted, starting
  with either `Assurance impact: INV-A, INV-B` (comma-separated exact IDs) or
  `Assurance impact: none`; duplicate, conflicting, or malformed impact lines
  invalidate the declaration. A `Reason:` or policy-change explanation must
  contain visible plain-text content; zero-width characters, entities that
  decode only to invisible characters, and empty inline HTML do not count.
  HTML comments may precede it, but arbitrary
  mentions, headings, blockquotes, links, code examples, and later directives
  do not count. Raw-HTML child prose remains visible ordinary content but can
  never become a top-level directive or reading-order line, including when an
  HTML entity decodes to a newline. Only physical LF/CRLF records delimit
  directives and diff lines; Unicode line separators remain content. A
  policy-only acknowledgment may begin the block; combined
  declarations must use the published impact → optional reason → optional
  policy order, and an out-of-order line invalidates the block. Component
  globs must contain non-whitespace text and use canonical repository-relative
  path components. Untrusted component names and verdicts are encoded before
  reaching ordinary terminal output, Actions log lines, annotations, or
  Markdown summaries, so controls and unpaired surrogates cannot forge a
  result line or crash output. The reusable
  workflow resolves every head adoption path inside the adopter project before
  reading it, rejects an absolute configured `adoption-file`, excludes Git
  metadata and the pinned profile checkout, and reserves each trusted checkout
  destination only after an `lstat` nonexistence check so an adopter symlink
  cannot redirect checkout writes. It runs all
  trusted Python readers and validators in isolated mode so adopter-root Python
  modules cannot shadow dependencies, validates
  the complete release-version grammar before writing an output or constructing
  a Git refspec, and safely encodes declaration paths in workflow commands. For
  base comparison it recovers the literal prior input from the base version of
  the actual caller identified by `github.workflow_ref`, so a file that merely
  pre-existed at a new HEAD destination cannot replace the real baseline. A
  fallback identity scan streams Git's NUL-delimited output and is fail-closed
  at 100,000 tracked records, 64 MiB of raw listing data, 64 MiB of lexical file
  surface, or 16 declaration candidates. Every tracked record is charged before
  file-type, containment, or trusted-path filters, while an in-tree symlink and its tracked target
  share one resolved declaration identity so aliases cannot create false
  ambiguity. Base/head transition metadata also binds the lexical adoption path
  to its contained resolved target; unchanged policy paths cannot be silently
  retargeted. Each job requires the exact canonical reusable-workflow path
  followed by its lowercase 40-hex `job.workflow_sha`; a suffix match cannot
  disguise a tag, branch, or different workflow. Changed-file production now invokes explicit rename and
  retained-source copy detection, reports each source/destination once, and
  caps raw name-status input before reading it. The CI assurance evidence diff
  is synthesized from exact invariant-bearing lines in regular, deterministic
  strict-text blobs reached by impact-eligible **HEAD-active** bindings. HEAD
  symlinks, gitlinks, control-heavy or invalid-UTF-8 blobs, and PDF containers
  cannot provide prose. Every exact line found anywhere in the pull request's
  merge-base tree is subtracted through a deliberately broader cancellation
  set (including binary and symlink blobs), so rename, retained copy,
  remapping, file-type/text-eligibility transition, similarity heuristics, or
  a later base-tip deletion cannot make unchanged policy look new. The
  repository-wide subtraction is conservative and the synthetic diff exposes
  only canonical IDs. Evidence enumeration deduplicates and ancestor-collapses
  pathspecs, batches them below argv limits, and drains Git's output pipes
  concurrently. All evidence Git operations, including `cat-file` blob reads,
  share one 60-second deadline. Merge-base and HEAD enumeration together share
  aggregate 64 MiB listing, 1 MiB diagnostic, and 100,000 tracked-tree-record
  bounds. Base bindings and every explicit path remain
  trust-checked for policy comparison. A workflow or public-assurance directory
  binding whose final resolved target is the repository root — whether written
  `.` or reached through a permitted in-project symlink — is also trust-checked
  but cannot contribute positive evidence, so an ID placed in ordinary source
  cannot satisfy its own routing gate. Within lite,
  moving the effective system description between the inline field and a
  mapped/default artifact is now a gated policy relocation even when `layout`
  and the dormant path spelling stay unchanged. Standalone register-policy
  comparison now also requires `--base-registers-root`, `--project-root`, and
  `--base-adoption` together; the two roots must exist, be directories, and
  resolve to distinct non-overlapping trees, so one-sided, missing, aliased,
  or ancestor/descendant-overlapping inspection fails closed. Standalone unified-diff evidence ignores added
  symlink/gitlink payloads and cancels exact deleted lines against additions.
- **The pre-v0.4 starter-row policy-diff exception is exact and migration
  scoped.** It applies only to a policy comparison that actually moves the pin
  from an `unreleased` pilot commit or v0.1.x–v0.3.x to v0.4 or later, and
  exempts only a register row equal to the complete entry object actually
  shipped in those templates. Partial completion, a changed default, extra
  project metadata, a generic `REPLACE_WITH_` string, or replacing completed
  prose with a marker cannot hide that transition or a later deletion hop. A
  comparison without that pre-v0.4 → v0.4+ pin transition, including one
  whose base is already v0.4 or later, receives no legacy exemption.
- **Pre-v0.4 declarations remain comparable while they are repaired.** For the
  reusable workflow's BASE materialization only, a canonical pre-v0.4 or
  `unreleased` base that strict parsing rejects may be reconstructed through
  the bounded historical SafeLoader data surface: duplicate keys retain
  last-key-wins behavior, merge keys are expanded only under the logical-node
  bound, and scalar legacy extension keys are normalized to collision-checked
  JSON strings. Direct standalone `--base-adoption` comparison supports only
  the narrower duplicate-key last-wins migration case and otherwise fails
  closed. This also
  preserves historically valid blank project-owner data and mixed
  active-plus-`archived` profile declarations long enough to compare their
  policy. Recursive, non-finite, oversized, colliding, or unsupported values
  still fail closed. The v0.4 head must use the strict JSON data model, remove
  duplicate/merge/non-string-key syntax, complete project identity, and choose
  either the exclusive `[archived]` profile or a valid active set;
  compatibility never validates the historical shape on HEAD.
- **Stage and policy-diff inputs now fail closed.** Explicit malformed stage
  values on either side of a drift comparison are errors rather than being
  omitted or coerced to `DRAFT`. Profile comparison uses the effective profile
  set, including the `core` inherited by specialized active profiles, so
  equivalent declarations do not report a false removal and a real inherited
  obligation cannot disappear silently. The declaration diff also protects
  committed project identity, approval provenance, specification workflow,
  security policy, restricted-record label, public-assurance root, issue
  controls, and effective
  default-normalized artifact paths; `archived` → active is a neutral explicit
  profile-mode reclassification gate. A completed `human_review.date` may
  advance for a re-review but cannot be removed, invalidated, or backdated.
- **Policy comparison now preserves its own routing and approval semantics.**
  Moving the adoption declaration is a gated policy change because the new
  path may escape existing CODEOWNERS coverage. When the configured HEAD path
  is absent on the base, the reusable workflow strict-loads tracked regular
  files regardless of extension or YAML spelling and accepts only a unique
  canonical AAP declaration signature; ambiguity fails closed. Approval
  provenance comparison now includes normalized `covers` scope (omission is
  equivalent to `[CONFORMANCE]`), so a previously full approval cannot be
  silently narrowed. Git changed paths remain NUL-separated through component
  routing, preserving embedded newlines and edge spaces. Recorded residual or
  defeater closure grounds are protected while a closed disposition remains;
  reopening still remains a non-finding. The explicit acknowledgment remains
  stage-proportional: it can downgrade a DRAFT finding to a warning, but a
  HUMAN_REVIEWED or CONFORMANT finding remains an error even when acknowledged.
- **Previously documentary active-adoption fields now have structural
  backstops.** Active declarations require a material-change
  `specification_workflow` with a project-local root; project identity and the
  required root instruction/adoption files must be non-empty; and from
  `HUMAN_REVIEWED`, `human_review.record` must resolve to an existing,
  non-empty project artifact. Review, approval, and residual-acceptance dates
  may not be in the future (date-only values allow the civil date possible in
  UTC+14), and at least one CONFORMANT approval must be on or after the review
  date. Approval URLs and dates are also checked for HTTP(S) and ISO/RFC 3339
  shape. These checks validate presence and syntax, not the truth or forge
  state of a review or approval.

#### Adopter impact / upgrade actions

- A previously conforming adoption now **fails** if it declares a
  non-archived profile but has no invariant register, or an empty one.
  The **newly affected** profiles are `core`, `data-curation`,
  `trust-critical`, and `agent-runtime` — before this release only
  `service` required an invariant, so any of these declared without
  `service` was previously conforming. Add at least one invariant (the
  properties that must remain true). Both pilot adoptions already carry
  invariants, so no live adopter is affected. See the version
  classification note below.

  upgrade.** Whether it is inline under lite or stored at `paths.system`, the
  description must identify the system being assured, its principal
  responsibilities and material boundaries, and known material limitations or
  unknowns. Fill any missing part and have the human owner review that prose.
  The validator checks presence, non-emptiness, and reviewed-stage template
  markers; it does not semantically parse those content elements, so a green
  check cannot substitute for that review.
- `layout: lite` is now **`core`-only**; `archived` (and every other
  non-`core` profile) uses the split layout. The lite envelope's
  required fields (purpose, non-goals, invariants, residuals) are shaped
  for `core`, not archived's §6.6 obligations. This **removes previously
  valid `archived` + `lite` support** — a deliberate compatibility
  change in this release, not the repair of a pre-existing bug. No live
  adopter uses `archived`. When moving from lite to an active specialized
  profile, preserve the register arrays and IDs, move inline system prose to
  `paths.system`, preserve `purpose` and `non_goals` there or in another
  owner-approved local intent artifact, and preserve or deliberately relocate
  `extensions` before dropping `layout`. A move to `archived` instead requires the owner-confirmed
  four §6.6 facts in the mapped system artifact; retained active registers are
  optional history and do not substitute for that archived record.
- Adopter files that relied on **last-key-wins duplicate YAML/JSON**, YAML merge
  keys, or non-JSON-compatible YAML values (binary, set/ordered-map, cyclic, or
  non-finite values); a non-finite JSON number; non-UTF-8 policy text; an
  artifact symlink escaping the project (including into Git metadata (`.git`)
  or the pinned profile checkout); an absolute artifact/root path or a path
  containing C0 controls or DEL; a non-canonical `components[].paths` glob
  with an empty, `.` or `..` component; an approval URL with no host, user
  information, a malformed port, or an invalid percent escape; a repository
  slug, commit, stable ID, or reference whose scalar value ends in a newline;
  or an explicitly malformed stage now fail closed. Remove duplicate and merge
  keys by materializing an explicit mapping; represent YAML policy as ordinary
  JSON-model scalars, arrays, and mappings; move artifacts into the adopting
  project; encode policy text as UTF-8; make artifact/root locations and
  component globs canonical repository-relative paths; repair URL ports and
  percent escapes; rewrite an affected schema token as a single-line scalar
  whose value has no terminal newline; and repair the stage declaration.
  The reusable workflow can still compare a direct upgrade from a pre-v0.4 or
  `unreleased` base by materializing the legacy declaration's bounded
  historical SafeLoader result long enough to detect policy weakening,
  including last-value duplicate keys, merge keys, and safely normalizable
  scalar extension keys; direct standalone comparison provides only the
  duplicate-key last-wins subset. Every file in the v0.4 head must be strict,
  unambiguous JSON-model YAML. Likewise, replace a
  legacy mixed active-plus-`archived` profile list with either `[archived]`
  alone or the complete applicable active set; the compatibility reader does
  not validate the old mixed form on the head.
  Replace an absolute or escape-and-reentry policy symlink with a portable
  relative in-repository link. When `--profile-checkout` is omitted, the VERSION-bearing root
  inferred from `--schemas` is now the same trust boundary and its `VERSION`
  must match the adopter pin. Use a real Git checkout at `upstream.commit` for
  local validation; a Git-backed checkout at another HEAD, running a different
  validator, or carrying dirty validation resources now fails, while a source
  archive warns that its commit identity and resource cleanliness cannot be
  established.
- A policy YAML file over 5,242,880 bytes or whose aliases represent more than
  100,000 logical nodes now fails. Policy JSON over 10,485,760 bytes, 256
  nesting levels, or 500,000 nodes also fails with a controlled diagnostic.
  Each directly read adopter-owned prose/review file is likewise capped at
  5,242,880 bytes: root `AGENTIC_ASSURANCE.md`, root `AGENTS.md`, the mapped
  system artifact, required service threat model, and `human_review.record`.
  Component routing is limited to 256
  components, 256 path globs and 256 invariant IDs per component, 20,000
  changed paths, 1,024 characters per glob, and 4,096 characters per changed
  path. Aggregate glob matching and impact-directive scanning each have a
  20,000,000-work-unit budget. Split an oversized policy or change, and reduce
  or narrow an oversized component map; routing input files are additionally
  capped at 33,554,432 bytes (changed paths), 1,048,576 bytes (PR body), and
  20,971,520 bytes (assurance diff). Aliases are not a way around the
  logical-node limit.
- **The `archived` profile is now partially enforced** (previously a
  no-op). `archived` must be declared **exclusively** — `[core, archived]`
  and any other active-plus-archived set is now an error, since a
  repository retained solely for historical reference, not supported or
  intended for current use, and without active operation, functional
  maintenance, or feature development cannot also carry an active obligation.
  An `archived` adoption must carry a non-empty mapped `system` artifact at
  every stage, including `DRAFT`. At `HUMAN_REVIEWED` or `CONFORMANT`, each of
  the four exact archived template markers is additionally rejected, so an
  untouched template cannot pass. This is still a
  **completion guard, not full §6.6 enforcement**: arbitrary replacement prose
  is not parsed for all four facts and is not checked for truth. Structured,
  field-level enforcement remains #40. `docs/REVIEW-GUIDE.md` makes the four
  confirmations and `paths.system` resolution an owner checklist. Initial
  adoption, factual correction, pin/stage/review upkeep, and agent-instruction
  metadata do not by themselves count as functional maintenance; code,
  dependency, or behavior work supporting current use requires reclassification.
- **Stage tightening can require adopter edits.** A `CONFORMANT` active
  adopter whose critical invariant is classified `ACCIDENTAL` must either
  record the behavior as a gap/residual rather than an invariant, choose a
  non-accidental intended classification with human authority, or lower the
  claimed stage. At HUMAN_REVIEWED, every active critical invariant now needs
  a recorded classification (`UNKNOWN` remains valid), and every affirmative
  `INTENDED`/`COMPATIBILITY`/`DEPRECATED` classification needs human authority.
  At every active stage, a severity-`critical` invariant recorded `VERIFIED`
  needs at least one enforcement and one verification reference.
  Every `ACCEPTED` residual now needs `accepted_by`, a non-future `accepted_at`,
  and `acceptance_rationale`; every `RESOLVED` residual needs
  `resolution_note`. The already-enforced rule that a `MITIGATED`, `RESOLVED`,
  or `WITHDRAWN` defeater needs non-blank `resolution` grounds is now encoded
  in its schema and labeled as status-conditional in both starter templates.
  Reviewed adopters must also add a real project-local
  review record if `human_review.record` previously named a missing or empty
  path; active adopters must declare their existing material-change workflow,
  and `specification_workflow.root` must resolve to a path that actually
  exists and carries content — a readable, non-empty UTF-8 file, or a
  directory holding at least one such file within the validator's bounded
  scan. A stub or emptied workflow directory now fails. `docs/ADOPTION.md`
  §3.6 states the exact bounds.
- **Completed human acts cannot be future-dated.** Repair a future
  `human_review.date`, approval `at`, or residual `accepted_at`. Date-only
  values allow the current civil date possible in UTC+14; timestamp values use
  their stated offset. A retained residual acceptance remains subject to this
  rule under `archived`; archiving cannot make a future-dated completed act
  valid. At CONFORMANT, ensure at least one attributable approval has a civil
  date on or after `human_review.date`. `review_after` schedules now use the
  same host-independent UTC+14 latest-civil-date boundary, so local and CI
  runners in different time zones cannot disagree about whether one has passed.
- **Scoped approvals no longer imply full conformance approval.** An approval
  with no `covers` list still attests the full claim. If `covers` is present,
  add the reserved `CONFORMANCE` token for that approval to satisfy the
  CONFORMANT gate; a list containing only individual IDs is intentionally too
  narrow.
- **Complete the newly enforced declaration and root-file fields before the
  pin upgrade.** `project.name` and `project.human_owner` must be non-blank,
  and `project.repository` must be an `owner/name` slug. Root
  `AGENTIC_ASSURANCE.md` and root `AGENTS.md` must be non-empty and contain the
  exact assurance-guide and adoption-declaration references in one canonical
  visible ordered block (hidden comments, code, and HTML do not satisfy it),
  using the same custom `adoption-file` path in both when applicable.
  Approval records need a non-blank approver, an absolute HTTP(S) review URL,
  a valid non-future date/timestamp, and full conformance scope when used for
  `CONFORMANT`; the qualifying approval's civil date must not precede the
  human-review date.

  **Every v0.3.x adoption fails this check until the block is present in both
  files**, because v0.3.2 required only that the two root files exist. In
  practice the edit is one file: the v0.3.2 `AGENTS.md` template already
  carried the block, and its `AGENTIC_ASSURANCE.md` template did not. Both
  pilot adoptions were checked against this release — `AGENTS.md` passes in
  both, `AGENTIC_ASSURANCE.md` fails in both, so each needs the block added
  there and nothing else. The block is, verbatim — substituting a custom
  `adoption-file` path for the second entry, identically in both files:

  ```text
  Before any material change, read:

  1. `AGENTIC_ASSURANCE.md`;
  2. `.agentic-assurance/adoption.yaml`;
  ```

- **`issue_integration` values are now constrained, not merely declared.**
  `public_security_issues_allowed` must be `false` and
  `closing_requires_artifact_update` must be `true`, enforced by both the
  schema (`const`) and the validator. v0.3.2 typed them as ordinary booleans
  and described the first as required only *for public repositories*, so a
  private adopter could legitimately declare `true`. It is now unconditional
  and `--repo-visibility private` does not relax it: repository visibility
  bounds who can read a finding, not whether an exploitable one may be filed
  as an ordinary Issue. An adopter that declared `public_security_issues_allowed:
  true` must set it to `false` and route potentially exploitable findings
  through a private report or Security Advisory. `PROFILE.md` §14 now states
  both values normatively, so the mechanical rule has an anchor.

- **Fill in the root guides before `HUMAN_REVIEWED`.** Because this release
  makes the two root guides required artifacts, they now carry the same
  reviewed-stage obligation as the mapped system artifact: from
  `HUMAN_REVIEWED` onward neither may contain a `REPLACE_WITH_` marker,
  including inside fenced sample blocks. Without this, an adoption could be
  declared `CONFORMANT` while the file agents are told to read first was still
  the unfilled upstream template. Both pilot adoptions already satisfy it.

- **Move pull-request directive lines into a leading block.**
  `Assurance impact:`, `Reason:`, and `Assurance policy change:` now count
  only inside a leading top-level directive block, before any ordinary visible
  content; previously they were recognized anywhere in the description.
  Update the repository's pull-request template so the directive lines come
  first, and re-edit any pull request left open across the pin upgrade — an
  acknowledgment that sits below prose stops counting the moment the pin
  moves.
- **Required service threat models now have content guards.** A service
  adopter's mapped `THREAT_MODEL` must be non-empty at every stage and, from
  HUMAN_REVIEWED, must not retain a generic `REPLACE_WITH_` template marker.
- **Default and custom declaration/artifact paths need coordinated owner
  binding.** Confirm that the effective owner-review boundary covers both root
  instruction files, the CI caller, the effective adoption declaration, every
  effective artifact location selected under `paths:` (including standard
  defaults), `specification_workflow.root`, `human_review.record`,
  `security.policy`, and `security.public_assurance_root`. Put a non-default
  `adoption-file` path in the reading order in both root files. When CODEOWNERS
  is the mechanism, merge the shipped rules for the standard locations and add
  explicit rules for every custom location; the shipped template now also
  covers its adoption template's default `SECURITY.md`. A later declaration-path
  move is now a stage-proportional policy finding, as is rewriting an existing
  approval's normalized `covers` scope. For any covered location implemented
  as a symlink, cover the lexical link itself (including
  retargeting), the resolved target, and the target's parent or containing tree;
  CODEOWNERS does not follow the validator's symlink resolution. The new
  validator warning makes that requirement visible but cannot prove that code
  owner review or branch protection is enabled.
- **Date placeholders are caught at `HUMAN_REVIEWED`.** An unfilled
  `review_after: REPLACE_WITH_REVIEW_AFTER_DATE` in a register now fails
  from `HUMAN_REVIEWED` on, like every other `REPLACE_WITH_` token. The
  pre-v0.4 `review_after: YYYY-MM-DD` sentinel remains a path-scoped
  compatibility alias: DRAFT still tolerates it in residual and defeater
  entries, while `HUMAN_REVIEWED` rejects it. A literal `YYYY-MM-DD`
  elsewhere remains ordinary adopter data. The policy diff preserves both
  sentinels as raw values, so a real re-review date cannot silently regress
  back to an unfilled placeholder. The two official sentinel spellings are
  treated as aliases during policy comparison: migration in either direction
  is neutral, while replacing a real date with either sentinel remains a
  weakening finding in split and lite layouts.
- **All seven pre-v0.4 prose starter prompts are stage-compatible without
  becoming false-green.** The exact legacy strings with the `Replace with`
  prefix in claim `text`/`scope`, invariant `title`/`statement`/`scope`, defeater
  `statement`, and residual `summary` remain tolerated at `DRAFT` but
  fail at `HUMAN_REVIEWED` and `CONFORMANT`. Stage matching is scoped to those
  original register fields regardless of the pinned base version, so identical
  literal adopter data elsewhere is not reclassified as a placeholder.
  Separately, the policy-diff exemption for deleting an otherwise unchanged
  legacy starter row applies only to an actual direct upgrade from
  `unreleased` or v0.1.x–v0.3.x to v0.4.0 or later.
- **Split-template self-check now enforces profile obligations as well as
  entry semantics.** Empty split invariant or residual starter registers
  can no longer leave the central self-check green; they are checked with
  the same non-empty `core` obligations as adopter validation and the lite
  templates.
- **The copied root-agent instruction block is now drift-guarded.** Central
  self-check extracts the normative §11 Markdown block from
  `templates/AGENTIC_ASSURANCE.md` and exact-compares it with the standalone
  `templates/AGENTS.md` copy, failing closed when markers are missing or
  duplicated. A prose-only edit can no longer invalidate the template's
  “copied verbatim” promise while leaving self-check green.
- **The expanded lite reference is complete for its documented standard
  surface without claiming to enumerate local extensions.** It now shows
  the status-conditional defeater `resolution` field and top-level `extensions`
  namespace. Template and adoption prose call it an expanded standard-field
  reference rather than “every field.”

#### Fixed — placeholder scanning and diagnostics

- **A completed artifact no longer fails for naming the marker convention.**
  The reviewed-stage prose scan matches a named `REPLACE_WITH_...` token
  rather than the bare prefix, and reports the token it found. The shipped
  `SYSTEM.md` and `THREAT_MODEL.md` instructions were reworded so a copied
  template does not carry a literal marker in its own guidance.
- **Lite prose is scanned by the same rule as split prose.** `system`,
  `purpose`, and `non_goals` in the lite envelope are prose, and now follow
  the prose rule instead of the structured-field substring rule. Identical
  text previously passed in the split layout and failed in lite, and the
  error quoted the adopter's entire paragraph instead of the token.
  Structured register fields keep the stricter substring rule.
- **A malformed tagged scalar no longer escapes as a traceback.** `!!bool`
  and `!!timestamp` values that PyYAML cannot resolve are reported as
  ordinary validation errors, preserving PyYAML's own diagnostic text, so
  `--json` output stays well-formed.
- **`intent.authority` guidance ships with the templates.** The invariant
  templates now state inline that an `INTENDED`, `COMPATIBILITY`, or
  `DEPRECATED` classification requires a named authority, matching the
  guidance already given for the residual and defeater conditionals.

#### Version classification — a recorded owner decision, not a pre-existing rule

Under the §16 in force at v0.3.2 — "Major: removes, weakens, or
materially changes an obligation" — this release would have been a
**major**. It both adds obligations that break previously conforming
adoptions and removes one previously valid capability (`archived` +
`lite`).

§16's initial-development paragraph, under which adding or tightening an
obligation before `v1.0.0` is a **minor**, was **introduced in this
release and applied to it**. That is a governing owner decision taken on
2026-07-20 and recorded here, rather than presented as a rule that
already existed; the classification of this release rests on that
decision, not on a policy that predates it.

Rationale: the profile is pre-`v1.0.0` with two adopters, both under
this organization's control, and publishing `v1.0.0` solely to carry
this change would assert an interface stability the profile does not yet
have. The paragraph states this project's `0.x` operating policy; it
does not claim that semantic versioning universally assigns every such
change to a minor release. An adopter who prefers the stricter reading
should treat this release as breaking and plan the migration below
accordingly — the required work is identical either way.

## v0.3.2 — 2026-07-19

Extends the register policy diff from "reviewed items cannot silently
disappear" (v0.3.1) to change control over every recorded human decision:
acceptance, terminal dispositions, accountability, re-review commitments,
both residual assessment axes, and the assurance-graph edges. From a
fifth external review of v0.3.1. No schema changes.

#### Adopter impact / upgrade actions

- None required. The drift job reports strictly more findings; pull
  requests that change the fields below now need the same
  stage-proportional acknowledgment as deletions and closures. Legitimate
  versions of these changes (a real acceptance, an owner handover)
  surface as findings by design — under a `DRAFT` base an `Assurance
  policy change:` line downgrades them to warnings; under a reviewed base
  stage, merging over the red check is the human owner's recorded
  decision. Routine acts that are *not* findings, deliberately:
  rescheduling a `review_after` date that has not yet passed, and
  reclassifying an entry's `disclosure`.
- Adopters whose registers are in-tree symlinks: the base side of the
  policy diff previously dropped such registers silently; they are now
  compared like regular files.

#### Fixed — register policy diff: human decisions are change-controlled

- **Residual acceptance is gated.** Any status transition into `ACCEPTED`
  is now a finding: accepting a residual risk is a human decision
  (PROFILE.md §3, §12), and the acceptance fields are self-declared
  strings — previously an agent could fabricate `accepted_by`/
  `accepted_at`/`acceptance_rationale`, flip a critical residual from
  `OPEN` to `ACCEPTED`, and turn a failing `CONFORMANT` state green with
  no finding. Rewriting or removing an existing acceptance record is
  likewise a finding.
- **A recorded judgement value cannot be silently unset.** Removing,
  emptying, or de-stringing `status` (all registers), `severity`,
  `proof_tier`, `impact`, `uncertainty`, or an `INTENDED`
  `intent.classification` is now a finding. Every weakening check is
  pair-keyed — it needs a meaningful value on both sides — so unsetting
  one was a free first hop: drop it in one pull request (nothing to
  compare, silent), record the weaker value in the next (no baseline,
  silent), while the one-step edit was an error the whole time. The
  residual/defeater disposition gates additionally fire on the head
  *arriving* at a gated status regardless of what the base recorded.
  This closes the *unset* shape of that first hop; overwriting a value
  with an unrecognized string is pair-keyed the same way and remains the
  schema enum check's job, since flagging it in the diff would also
  flag an adopter repairing a value that predates the stricter schema.
- **Defeater terminal dispositions are gated.** `MITIGATED → RESOLVED`
  and `MITIGATED → WITHDRAWN` were invisible inside the single "closed"
  class; they are now findings (an extra edge on the closed-set
  condition, so an out-of-schema base status keeps failing toward a
  finding, not toward silence). `RESOLVED ↔ WITHDRAWN` lateral moves and
  re-opening remain non-findings.
- **`review_after` is a kept commitment.** Removing it, replacing it
  with an unparsable value, or pushing it out *after the recorded date
  had already passed* are findings — that last case is the review being
  evaded rather than done, and is how a live overdue warning would
  otherwise be cleared. Rescheduling a date still in the future is the
  normal outcome of completing a review and is deliberately **not** a
  finding: putting a red check on the one act the schedule exists to
  produce would teach adopters to ignore the check. An unparsable *base*
  value still counts as a recorded commitment, so dropping it or
  swapping it for different garbage is a finding; repairing it into a
  real date is not.
- **Accountability fields are compared:** a changed entry `owner` (all
  registers); a changed `human_review.reviewer`/`human_review.record` in
  the adoption declaration (`human_review.date` is deliberately not
  compared — advancing it is the normal re-review act); and the full
  `INTENDED` intent row (`COMPATIBILITY`/`DEPRECATED` join
  `UNKNOWN`/`ACCIDENTAL`). Entry `disclosure` is deliberately **not**
  compared: it is not a strength axis, the risky direction on a public
  repository is already an error at `CONFORMANT`, and reclassifying
  during triage is routine.
- **Assurance-graph edges are protected.** Removing items from claims'
  `defeaters`/`residuals`, invariants' `assumptions`/`limitations`/
  `defeaters`/`residuals` (at every severity — edges are graph
  structure, not evidence volume), defeaters' `affected_claims`/
  `affected_invariants`/`evidence`, and residuals' `affected_claims`/
  `affected_invariants`/`mitigation` is now a finding, generalizing the
  v0.3.1 claim-basis check into a per-kind protected-list map. The
  severity-gated invariant `enforcement`/`verification`/`evidence` check
  is unchanged.
- **Residual `uncertainty` downgrades are findings**, parallel to
  `impact` — the two assessment axes were asymmetrically protected.

#### Fixed — fail-closed hardening

- **Symlinked base registers are compared.** The drift job materializes
  the base side as a detached `git worktree` instead of per-file
  `git show` writes: `git show` renders a symlink blob as its
  target-path string, so a symlinked register materialized as a regular
  file holding a path string, loaded as unusable, and silently dropped
  out of the policy diff — one innocuous pull request converting a
  register to a symlink disabled its protection for every later one. The
  base adoption declaration is read from the same worktree
  (symlink-aware, containment-checked), and a present-but-unreadable
  base declaration fails the job instead of skipping the comparison.
- **Unusable registers are hard errors on both sides.** A register file
  that parses but is not a mapping carrying the register's list — a lite
  assurance file that is not a mapping, or whose section is not a list —
  and a register path that exists but is not a readable regular file (a
  directory, a broken symlink) are reported instead of silently skipping
  that register's diff. Only a genuinely absent file still means
  "register absent".
- **Duplicate head IDs fail closed.** The diff compares by stable ID
  (last-one-wins), so a weak shadow entry under a duplicated ID was
  invisible to it; a head register with duplicate IDs is now itself a
  finding, instead of relying on the structure job being configured as a
  required check.

#### Process

- RELEASING.md: the release pull request now states the release's review
  class per GOVERNANCE.md §2 (e.g. `SOLE_OWNER_ATTESTED +
  AUTOMATION_VERIFIED`), citing any external technical reviews — the
  GOVERNANCE.md obligation that every release state its class was never
  wired into the release ritual.

## v0.3.1 — 2026-07-19

Completes the register policy diff so a base-branch, human-reviewed
assurance item cannot silently disappear regardless of the form the change
takes — deletion, whole-register removal, or a status that closes it out.
From a fourth external review of v0.3.0. No schema changes; existing
adopters see only stricter drift-job findings, and only on pull requests
that actually remove reviewed assurance.

#### Fixed — register policy diff completeness

- **Whole-register removal is now caught (was fail-open).** The diff
  skipped a register entirely when the head branch lacked it, so deleting
  an optional register file (e.g. `INVARIANTS.yaml` under the `core`
  profile, where it is not a required file) erased every reviewed entry
  with no finding. A base register missing on the head is now a
  "register removed" finding listing the former IDs; an unreadable head
  register fails closed.
- **Closing dispositions are now caught.** A residual moved to `RESOLVED`,
  a defeater moved to `MITIGATED`/`RESOLVED`/`WITHDRAWN`, and a recorded
  `CONTRADICTED` status cleared (moving *away* from `CONTRADICTED`) each
  remove a tracked concern without deleting its ID; they are now findings,
  subject to the same stage-proportional acknowledgment. Re-opening and
  recording a new contradiction remain non-findings.
- **Claim basis removal is now caught.** Removing a claim's `evidence`,
  supporting `invariants`, or `limitations` items is flagged (parallel to
  the invariant evidence-removal check) — stripping a claim's basis is a
  mechanism change, not a wording change.

#### Security

- The drift job's assurance-diff step now runs `git` with
  `--literal-pathspecs` and screens pull-request-controlled `paths:` values
  through an in-tree containment check before using them as pathspecs or
  base-tree write targets (belt-and-suspenders with the validator's
  existing containment), and fails closed if `git diff` errors instead of
  proceeding with an empty diff.

## v0.3.0 — 2026-07-19

Trust-boundary honesty and register-level policy protection, from an
external review of v0.2.1. Minor release: the register schemas now reject
empty/whitespace-only semantic strings and profile-mandated registers must
be non-empty — theoretically breaking for adopters relying on vacuous
passes (none known).

#### Adopter impact / upgrade actions

- **Caller must pin a full SHA.** The workflow now rejects callers that
  reference it by tag or branch (`job.workflow_ref` must end in the
  workflow's own 40-hex SHA). Existing SHA-pinned callers are unaffected.
- The reusable workflow targets GitHub.com only (it relies on the
  `job.workflow_*` contexts, absent on GitHub Enterprise Server).
- `--repo-visibility` (CI passes it automatically): at `CONFORMANT`,
  `RESTRICTED`/`EMBARGOED` entries are errors only in public repositories;
  private repositories keep the standing warning (fixes the v0.2.1
  conflict with ADOPTION.md's private-repository allowance).
- Registers mandated by a profile must carry at least one entry
  (`residuals` for non-archived, `invariants` for `service`, `claims` for
  `trust-critical`); register schemas reject empty/whitespace-only
  semantic strings, matching the lite envelope.

#### Security / trust boundary

- **Trusted-checkout-first:** every job first verifies the workflow's own
  identity (`job.workflow_repository` == canonical, caller pinned by full
  SHA) and checks out that exact source; the hash-locked dependencies come
  from it, and the v0.2.1 version-pinned pyyaml bootstrap is gone — no
  install precedes the trusted checkout. `upstream.commit` must equal the
  workflow's own SHA, so the trusted checkout IS the pinned profile.
- **The caller-workflow boundary is now documented honestly** (workflow
  header + ADOPTION.md §3.4): a pull request can swap the caller's `@`
  reference or the caller itself — no reusable-workflow content can defend
  that; CODEOWNERS on `.github/workflows/` (already in the adopter
  bundle), organization Actions allow-lists, and organization rulesets
  with required workflows (Team/Enterprise) are the controls, and a green
  check is an input to human review, not a tamper-proof verdict.
- `actionlint` (digest-pinned image) added to self-check.

#### Changed

- **Register-level policy regression (stable-ID base/head diff)** in the
  drift job: deleted entries; invariant severity downgrades,
  status weakening (`VERIFIED`/`INFERRED` toward `UNKNOWN` —
  `CONTRADICTED` is an honesty upgrade, never flagged), `INTENDED` intent
  reclassified, enforcement/verification/evidence removed from
  high/critical invariants; claim status weakening and proof-tier
  downgrades; residual impact downgrades. Adoption-level findings gain
  `project.human_owner`, `paths.*`, and `security.public_assurance_root`
  changes.
- **Stage-proportional acknowledgment:** `Assurance policy change:` still
  downgrades findings to warnings at base-stage `DRAFT`, but from
  `HUMAN_REVIEWED` on findings stay errors even when acknowledged — the
  acknowledgment is a self-declaration (an agent can write it), so its
  force is capped by the stage the base declaration had asserted.
- The assurance diff is scoped by the `paths:` both declarations actually
  name — custom artifact locations now count toward per-component
  satisfaction; a missing base declaration emits a notice instead of
  silently skipping.
- `human_review.approvals` remains unverified against the forge API
  (deferred); GOVERNANCE.md now defines honest review classes
  (INDEPENDENTLY_REVIEWED / SOLE_OWNER_ATTESTED / AUTOMATION_VERIFIED) and
  records that releases currently ship as SOLE_OWNER_ATTESTED +
  AUTOMATION_VERIFIED.

#### Added

- `requirements.in` (lock regeneration input) committed.
- New tests covering the register diff, stage-proportional acknowledgment,
  visibility-aware disclosure, empty-register obligations, and the schema
  hardening.

## v0.2.1 — 2026-07-18

Security hardening of the reusable adopter CI plus honest-signal fixes,
from an external review of v0.2.0. No adoption-schema changes; both pilot
registers validate identically. All behavior changes land in surface area
no current adopter occupies (no adopter declares HUMAN_REVIEWED/CONFORMANT
or ships a component map yet), which is why this is a patch release.

### Adopter impact / upgrade actions

- **Recommended upgrade.** Re-pin to `v0.2.1` (`upstream.version`,
  `upstream.commit`, and the workflow `@` reference) to pick up the CI
  trust-boundary fix.
- **Check rename:** `assurance / conformance` is now
  `assurance / declared-stage` — update branch protection if you made it a
  required check. Rationale: the check is green whenever the *declared*
  stage is met (HUMAN_REVIEWED included), so the old name could be misread
  as a conformance statement.
- **Caller `on:` update recommended** (docs/ADOPTION.md §3.4): add
  `pull_request` types `[opened, synchronize, reopened, edited,
  ready_for_review]` — the drift check reads the PR description, and
  without `edited` a later description edit leaves a stale verdict.
- The reusable workflow now requires the caller's `@` reference to equal
  `upstream.commit` (this was already the documented rule; it is now
  enforced) and validates only against the canonical upstream
  `MosslandOpenDevs/agentic-assurance-profile` — fork adopters run their
  own copy with the `CANONICAL` constant changed.

### Security

- `adopter-validate.yml` no longer checks out the validator from a
  repository named in the pull-request-mutable adoption file. The validator
  is always checked out from the canonical upstream; the declared
  repository is validated as data (must equal the canonical upstream, else
  error), the commit must be a full 40-hex SHA (checked before any
  checkout), and the caller's pinned workflow SHA must match it. This
  closes a code-execution vector where a pull request could point CI at
  attacker-controlled validator code.
- Both workflows now set `permissions: contents: read`, use
  `persist-credentials: false` on every checkout, pin every action to a
  full commit SHA, and install dependencies from a universal hash-pinned
  lock (`requirements-ci.txt`, `pip install --require-hashes`). One
  deliberate exception: each adopter-validate job first bootstraps the
  pin reader with a version-pinned (not hash-pinned)
  `pip install "pyyaml==6.0.3" --no-deps` — the lock only exists after
  the pinned checkout that the pin reader itself enables.

### Changed

- **Stage self-downgrade protection.** The pull-request drift job now
  compares the adoption declaration against the base branch: a stage
  downgrade, profile removal, layout change, upstream pin change, component
  removal, or removal of a component's path globs / invariant IDs fails the
  job unless the PR description carries an explicit
  `Assurance policy change: <why>` line (which downgrades the findings to
  warnings). A PR flipping `CONFORMANT` back to `DRAFT` no longer slips
  through as a skipped check.
- **CONFORMANT now enforces the mechanically checkable subset of PROFILE
  §17:** no `critical` residual left `OPEN`, no `CONTRADICTED` claim, no
  `CONTRADICTED` critical invariant, every `VERIFIED` critical invariant
  carries non-empty `evidence`, and `RESTRICTED`/`EMBARGOED` entries are
  errors (still warnings at lower stages). ADOPTION.md §3.8 states the
  honest boundary: revision-bound evidence and claim-vs-evidence wording
  remain the human review's responsibility.
- **Per-component drift satisfaction.** Touching some assurance file no
  longer satisfies every touched component: in CI, the assurance diff must
  reference at least one of the component's invariant IDs (PR-body mention
  and the no-impact statement are unchanged). Standalone runs without
  `--assurance-diff` keep the coarse fallback.
- **Rename-safe change detection.** Changed files are computed with
  `--name-status -z`; a rename or copy counts both source and destination,
  so code cannot move out of a mapped path unseen.
- Validator findings are now emitted as GitHub annotations
  (`::error::`/`::warning::`) inside Actions, and the drift job writes an
  impact-routing table to the job summary — warn-first findings were
  previously easy to miss in raw logs.
- Lite envelope schema tightened: unknown top-level keys are rejected (a
  typo like `invarients` fails loudly; adopter-specific keys go under the
  new `extensions` namespace), and `purpose`/`non_goals`/`system` reject
  empty or whitespace-only strings.
- New warning under `layout: lite` when `security.public_assurance_root`
  still points at the split layout's `assurance` directory.

### Added

- `tests/test_validate.py`: a fixture-based regression suite for the
  validator (stage ladder, §17 conformance checks, drift routing and
  policy regression, lite tightening), run by `self-check` on a Python
  3.10/3.12/3.13 matrix.
- `requirements-ci.txt`: universal hash-pinned dependency lock.

### Fixed

- `GOVERNANCE.md` referenced `@MosslandOpenDevs/assurance-maintainers`
  while `.github/CODEOWNERS` uses `@MosslandOpenDevs/maintainers`; both now
  name the real team.
- `templates/AGENTIC_ASSURANCE.md` §2 now instructs adopters to keep the
  concrete pin values only in `adoption.yaml` (a pin duplicated into prose
  is not validator-checked and silently goes stale — observed in a v0.2.0
  pilot).
- ADOPTION.md §3.8 no longer overstates DRAFT ("placeholders allowed
  everywhere"): the adoption declaration itself must be complete at every
  stage; the allowance covers the local registers.
- `templates/AGENTS.md` reading order is now lite-aware (non-goals and the
  system description live in `.agentic-assurance/assurance.yaml` under
  `layout: lite`, not `assurance/SYSTEM.md`).
- `templates/adoption.yaml` lite comment now notes that
  `security.public_assurance_root` should point at `.agentic-assurance`.

## v0.2.0 — 2026-07-18

The register becomes a regression gate, the safest usage becomes the
easiest usage, and a green check can no longer be misread. All three
features come from the two pilot adoptions and two external reviews of
the v0.1 line.

### Adopter impact / upgrade actions

- Re-pin is optional; existing v0.1.x pins remain valid. Upgrading
  adopters update `upstream.version`, `upstream.commit` (the v0.2.0 tag
  commit), and the workflow `@` reference in one reviewed change.
- **Required-check rename:** the reusable workflow's `validate` job is
  now `structure`, and a `conformance` check appears (skipped while the
  declared stage is DRAFT). Update branch-protection required checks
  when re-pinning.
- All new fields are optional; adoptions without `layout`, `components`,
  or `adoption_stage` behave byte-identically.
- `data-curation` is no longer provisional; `agent-runtime` remains so.

### Added

- Lite adoption layout for `core`: all assurance content in a single
  `.agentic-assurance/assurance.yaml` (purpose, non-goals, optional
  system description, and the invariant/residual/defeater registers),
  declared with the new optional `layout` field in the adoption
  declaration (`schemas/adoption.schema.json`; `split` or `lite`,
  absent means `split`). The file is described by a thin envelope
  schema (`schemas/assurance-lite.schema.json`) whose section items
  follow the existing register schemas — no duplicated item shapes;
  the validator extracts each present section, validates it against
  the pinned register schemas, and runs the existing semantic checks
  over the combined result. Lite is core-only: combining `layout: lite`
  with any profile beyond `core`/`archived` is an error, and the
  graduation to the split layout preserves every ID. Starter template
  at `templates/assurance.yaml`. The 25-file/1,867-line first-adoption
  cost observed in the pilots drops to four files for `core`.
- Impact routing: optional `components` map in the adoption declaration
  (`schemas/adoption.schema.json`), wiring repository paths
  (gitwildmatch-style globs) to the invariant IDs they protect, with an
  informational `tests` list. Documented in adoption guide §3.7 and the
  commented example block in both adopter templates; the adopter
  pull-request template documents the two-line no-impact statement
  convention (`Assurance impact: none` plus a mandatory `Reason:`).
- `drift` subcommand in `scripts/validate.py`: given a changed-file list
  and the pull-request description, checks every mapped component the
  change touches — satisfied when the change also touches assurance
  artifacts, when the description mentions every listed invariant ID, or
  when it carries the explicit no-impact statement — and reports
  unsatisfied components as WARN (exit 0) or, with `--strict`, as ERROR
  (exit 1); `--json` emits machine-readable output.
- Drift job in the reusable `adopter-validate` workflow, running the
  pinned `validate.py drift` on pull-request events only, gated by a
  new `strict-drift` input (boolean, default false). Push-event callers
  and the existing validate job are unaffected.
- Adopter-mode cross-check: every `components[].invariants` ID must
  exist in the loaded invariant register (split and lite layouts alike);
  a dangling component reference is an ERROR.
- Adoption stages: optional `adoption_stage` field in the adoption
  declaration (`schemas/adoption.schema.json`; `DRAFT`,
  `HUMAN_REVIEWED`, or `CONFORMANT`, absent means `DRAFT`). Stages are
  self-declared and self-binding: the validator enforces the declared
  stage's requirements as ERRORs, so declaring a stage the repository
  does not meet fails the build, while an absent or `DRAFT` declaration
  keeps validator output byte-identical to before. `HUMAN_REVIEWED`
  requires no unfilled `REPLACE_WITH_` placeholder in the adoption file
  or any loaded register (split or lite) and a `human_review` block
  with non-empty `date`, `reviewer`, and `record`; `CONFORMANT`
  additionally treats passed `review_after` dates as errors (as with
  `--strict-review-dates`), requires a decided (non-`UNKNOWN`)
  `intent.classification` on every severity-critical invariant, and
  requires at least one attributable approval. Documented in adoption
  guide §3.8, the review guide, the glossary, and the commented
  `adoption_stage` block in both adopter templates. New `--ignore-stage`
  flag on the `validate.py adopter` subcommand skips stage enforcement
  (structure-only validation).
- Attributable approvals: optional `human_review.approvals` array in the
  adoption declaration (`schemas/adoption.schema.json`) — entries carry
  `approver`, `review_url`, and `at`, plus optional `covers` and `rule`;
  at least one entry with all three non-empty is required at
  `CONFORMANT`. Deliberately deferred: the workflow does not yet verify
  the `review_url` via the GitHub API (approved state, author ≠
  approver); the entry is a human-reviewable claim, and the deferral is
  documented in adoption guide §3.8.
- `conformance` job in the reusable `adopter-validate` workflow: runs
  the full stage-enforcing validator (no `--ignore-stage`), and is
  skipped while the declared `adoption_stage` is `DRAFT` or absent (the
  pin-reading step now also outputs the declared stage, defaulting to
  `DRAFT`). The drift job is untouched.

### Changed

- Adoption guide restructured around lite-first `core` adoption: new
  §3.0 documents the four-file lite layout, the core-only rule, and
  the ID-preserving graduation path; §3.1–§3.5 now explicitly describe
  the split layout used from `service` upward; §3.6 documents the lite
  validation differences. The `templates/github/` issue-template bundle
  and `CODEOWNERS` are now optional at `core` — recommended when the
  repository takes external contributions, and `CODEOWNERS` wherever a
  second maintainer exists. Both READMEs and the review guide present
  the lite layout as the `core` minimum.
- CI check-name split in the reusable `adopter-validate` workflow: the
  `validate` job is renamed to `structure` (the check appears as
  "assurance / structure") and now runs the validator with
  `--ignore-stage` — a `DRAFT`-equivalent, structure-only pass/fail —
  while the new `conformance` job carries stage enforcement. Adopter
  impact: re-pinning adopters who made the old check a required status
  check must update their branch-protection settings from `validate` to
  `structure`; the split exists so a green structure check cannot be
  misread as conformance (adoption guide §3.8).

### Changed (release)

- `PROFILE.md` §5: `data-curation` promoted from provisional (exercised
  end-to-end by the second pilot; both §6.4 gaps dispositioned).
  `agent-runtime` remains provisional.
- `PROFILE.md` §17: a declared adoption stage binds — conformance
  checking MUST fail when the declared stage's requirements are not met.

## v0.1.2 — 2026-07-18

Semantic validation: an evidence-free `VERIFIED` no longer passes.
Closes the external-review finding that the schemas alone accept
formally-green, semantically-empty registers.

### Adopter impact / upgrade actions

- Optional upgrade; existing pins remain valid. Re-pinning adopters get
  seven new semantic checks — six ERROR-level (duplicate IDs; dangling
  cross-references; `VERIFIED` critical invariants without enforcement
  and verification; `INTENDED` without `intent.authority`; high-impact
  `ACCEPTED` residuals without `acceptance_rationale`; `RESOLVED`
  entries without recorded grounds) and one WARN-level (passed
  `review_after` dates; `--strict-review-dates` escalates). Both current
  pilot registers pass all seven unchanged.
- Conclusion status and intent classification remain independent axes:
  a `VERIFIED` invariant with intent `UNKNOWN` is legitimate; the new
  checks require mechanism evidence for `VERIFIED` and human authority
  for `INTENDED`, never one for the other.

### Added

- Semantic checks in `scripts/validate.py` (both subcommands; templates
  are checked in self-check too): duplicate-ID detection, cross-reference
  integrity across all nine reference fields (WARN when the referenced
  register file does not exist at all), grounded-status requirements for
  `VERIFIED`-critical, `INTENDED`, `ACCEPTED`, and `RESOLVED` entries,
  and passed-`review_after` warnings with `--strict-review-dates`.

### Changed

- Informative minimum layouts aligned with normative `PROFILE.md` §6.1
  (owner decision, 2026-07-18): `assurance/INVARIANTS.yaml` is
  recommended at `core` — it anchors the regression protection, and both
  pilots keep one — and required from the `service` profile
  (template §4, adoption guide §3.1, both READMEs).

## v0.1.1 — 2026-07-18

Post-release hardening from external review: close the gap between
creating assurance documents and binding them.

### Adopter impact / upgrade actions

- Optional upgrade — no obligations changed and no re-pin is required.
  Adopters who want the new CODEOWNERS binding copy
  `templates/github/CODEOWNERS` and follow adoption guide §3.5; existing
  pins remain valid.

### Added

- Adopter `CODEOWNERS` template (`templates/github/CODEOWNERS`) covering
  the assurance layer (`AGENTS.md`, `AGENTIC_ASSURANCE.md`,
  `.agentic-assurance/`, `assurance/`, the CI caller workflow), with the
  honest single-maintainer caveat; adoption guide §3.5 documents the
  binding steps (branch protection + code-owner review) and names the
  documents-without-binding failure mode.

### Changed

- Adoption guide §4.1 and the review guide now recommend keeping the
  invariant register at roughly 5–15 entries per repository — the things
  that must never break, not the full specification.

## v0.1.0 — 2026-07-18

First stable release of the v0.1 line. Two completed pilot adoptions
validated the full cycle end to end: a private brownfield service
(archaeology → human intent review → recorded outcomes → scoped
remediations → pin upgrade) and a public repository adopted from a bare
kick-off prompt, whose review surfaced the tag-pin and prose-provenance
rules below.

### Adopter impact / upgrade actions

- Upgrade from a `v0.1.0-rc.1` or `unreleased` pin in one reviewed change
  (ADOPTION.md §2.1): set `upstream.version` to `v0.1.0`, `upstream.commit`
  to the commit the `v0.1.0` tag points to (`git rev-list -n1 v0.1.0`),
  and the CI caller workflow `@` reference to that same SHA.
- From this release the `adopter-validate` workflow rejects a release pin
  whose commit is not the tag commit.
- The prose-provenance rule is a SHOULD-level normative addition to
  archaeology practice; existing artifacts need no changes.
- Schemas are unchanged since `v0.1.0-rc.1`.

### Added

- `adopter-validate` workflow: a release-version pin is now verified against the
  published tag — the job fails when `upstream.commit` is not the commit the tag
  points to (second-trial lesson: the release PR's branch commit carries the same
  `VERSION` content and previously validated interchangeably).

### Changed

- Adoption guide §2 and `RELEASING.md` now state that the tag commit is the
  canonical release pin, with `git rev-list -n1 vX.Y.Z` as the lookup.
- Prose-provenance rule (second-pilot lesson — an adopting agent cited an
  agent-written comment as intent authority and caught its own circular
  reasoning): `PROFILE.md` §7 now states that committed prose with
  agent-assisted authorship remains an agent narrative, that provenance
  SHOULD be checked against commit authorship, and that intent authority
  comes from a human act (a reviewed merge or recorded review outcome),
  not from who typed the text; the marker check is one-directional (an
  agent trailer disqualifies, its absence proves nothing); operationalized in the adoption guide §4.1
  (`git blame` / `Co-Authored-By` check), the `AGENTIC_ASSURANCE.md`
  template §6.2, the review guide, and a new glossary entry.

## v0.1.0-rc.1 — 2026-07-18

First tagged release candidate of the v0.1 line, after one complete
brownfield pilot adoption (archaeology → §4.3 human review → recorded
outcomes → scoped remediations).

### Adopter impact / upgrade actions

- Adopters pinned to `unreleased` commits from the pilot phase upgrade in
  one reviewed change (ADOPTION.md §2.1): set `upstream.version` to
  `v0.1.0-rc.1`, `upstream.commit` to the release commit SHA, and the CI
  caller workflow `@` reference to that same SHA.
- All schema changes are backward-compatible additions; artifacts that
  validated under earlier draft commits remain valid.
- Templates copied earlier keep working as copied; re-copying is optional.
  The branch-until-reviewed and handoff-format rules apply to future
  adoption runs.
- Pinning `version: unreleased` remains valid only for commits whose
  `VERSION` file reads `unreleased` (PROFILE.md §16).

### Added

- Initial draft profile (`PROFILE.md`).
- Public/restricted disclosure model.
- GitHub Issue and Security Advisory routing model.
- Adoption and assurance artifact templates.
- JSON Schemas for adoption declarations, claims, invariants, defeaters, and residuals (`schemas/`).
- Validator with `self-check` and `adopter` subcommands (`scripts/validate.py`).
- CI workflows: `self-check` for this repository and the reusable `adopter-validate` workflow for adopting repositories (`.github/workflows/`).
- Governance, release, and contribution documents: `GOVERNANCE.md`, `RELEASING.md`, `CONTRIBUTING.md`.
- License files for the per-path license split: `LICENSE` (Apache-2.0, code and tooling), `LICENSE-docs` (CC-BY-4.0, prose), `templates/LICENSE` (CC0-1.0, templates).
- Central repository issue forms, `config.yml`, pull request template, and `CODEOWNERS` (`.github/`).
- Adopter template bundle: `templates/github/` issue forms and pull request template, `templates/AGENTS.md`, `templates/SYSTEM.md`, `templates/THREAT_MODEL.md`.
- Adoption guide (`docs/ADOPTION.md`) and convention-mapping guide (`docs/MAPPINGS.md`).
- Root `VERSION` file recording the repository's release state.
- Optional `acceptance_rationale` and `resolution_note` fields on residual entries (`schemas/residuals.schema.json`), standardized from first-pilot usage.
- Optional `resolution` field on defeater entries (`schemas/defeaters.schema.json`), standardized from first-pilot usage.
- Optional `human_review` block in the adoption declaration (`schemas/adoption.schema.json`) recording the §4.3 intent review, standardized from first-pilot usage.
- Adoption guide §3.5: note that GitHub silently drops issue-form labels that do not exist in the repository, with an example `gh label create` loop.
- Glossary (`docs/GLOSSARY.md`): plain-language definitions of the profile's terminology, as an owner-side entry point (first-pilot lesson).
- Owner review guide (`docs/REVIEW-GUIDE.md`): the human owner's entry point for reviewing an adoption draft and making the §4.3 decisions (first-pilot lesson).

### Changed

- Unified version strings: the informal draft version identifier is abolished in favor of `unreleased` and `vMAJOR.MINOR.PATCH` release identifiers; `PROFILE.md` §16 adds pre-release naming, tag immutability, version/commit mismatch, and pre-first-release pinning rules.
- Marked the `data-curation` and `agent-runtime` profiles as provisional; while provisional, changes to their obligations are classified as minor.
- Clarified normativity: `PROFILE.md` is the normative text; README files and translations are informative.
- `SECURITY.md` scope now names templates alongside example configurations.
- Adoption guide §0 kick-off prompt and §4.3 now direct agents to keep the adoption draft on a branch as an open pull request; merging to the default branch is the human owner's act after the §4.3 review (first-pilot lesson).
- Adoption guide §3.6 now states that `RESTRICTED` entries bind repository visibility: the repository must not be made public until they are sanitized to `SUMMARY_ONLY`/`PUBLIC` or moved to the restricted record.
- Prescribed the agent→owner handoff format (adoption guide §0 kick-off prompt item 5; template `AGENTIC_ASSURANCE.md` §12): the drafting agent ends with a handoff summary in the owner's working language that states nothing is decided, lists each pending decision in plain language, and instructs that the pull request must not be merged until those decisions are made; the agent must not describe its result as "settled" or "complete" — completion language is reserved for the owner's acceptance (first-pilot lesson).
