# Review Guide — for the human owner

**What your agent will bring you, and how to answer.**

This guide is written in English because English is the repository's canonical language, but your review does not have to happen in English: your agent should relay every question below to you in your working language, and you should answer in it. Ask for that explicitly if it doesn't happen on its own.

[ADOPTION.md §0](ADOPTION.md) tells the agent how to prepare an adoption proposal. This page is the mirror image: it tells you, the human owner, what that proposal is and what it needs from you.

## Who this is for

You are the named human owner of a repository — the person the profile's authority rules point at ([PROFILE.md §3](../PROFILE.md)). Perhaps you build software fluently but have never used words like *invariant*, *residual*, or *defeater* in this technical sense. That is the expected starting point, not a problem: every term in this guide is defined in plain language in the [Glossary](GLOSSARY.md), and nothing below assumes you know the vocabulary in advance.

## What arrives

At some point your agent finishes its archaeology of the repository and hands you an **adoption proposal**: a summary of what it found, drafts of the assurance artifacts, and a set of questions. It arrives on a branch, as an **unmerged draft pull request**. For a small active `core` repository, the project-specific assurance register content may be concentrated in `.agentic-assurance/assurance.yaml`, the lite layout of [ADOPTION.md §3.0](ADOPTION.md); the proposal still contains the four required files (`AGENTS.md`, `AGENTIC_ASSURANCE.md`, `adoption.yaml`, and `assurance.yaml`). The four active-adoption decision families below apply however the content is laid out. An `archived` adoption takes the separate, narrower path in decision 1; it does not pretend that the other three active-system decisions apply.

**Nothing in that proposal is decided yet, and the pull request must not be merged until you have answered the decisions below — merging the pull request IS your act of acceptance.** ([ADOPTION.md §4.3](ADOPTION.md))

One phrasing deserves special warning, because it has caused a real misreading. When your agent says something like *"everything is settled, commit this on a branch"* or *"task complete"*, it is talking about **its drafting work** — the documents are written, the branch is ready. It is never talking about **your decisions**, which no agent can make for you ([PROFILE.md §15](../PROFILE.md)). "The draft is done" and "this is approved" look similar in a chat window and are entirely different events. If you are unsure which one you are looking at, ask: *"is anything in here waiting on a decision from me?"*

## The owner decisions

For an active repository, the proposal reduces to four kinds of decision. For an `archived` repository, confirm the archived scope and four required historical facts under decision 1, then skip active-system decisions that genuinely do not apply. For each: what the question really means, what a good answer looks like, and what happens with your answer.

### 1. Profile scope

**The real question:** how much of the rulebook applies to this repository?

The profile has an active baseline (`core`), specialized active profiles (`service`, `trust-critical`, `data-curation`, and `agent-runtime`), and the exclusive `archived` alternative ([PROFILE.md §5](../PROFILE.md)). Your agent proposes a set; you confirm or trim it.

**A good answer for an active repository** is the smallest set that covers what the repository *genuinely is* — `[core]` if no specialized trigger fires; otherwise every fired specialized profile. Specialized profiles inherit all `core` obligations even when `core` is omitted, so `[service]` is the canonical declaration for a service-only trigger; adding `core` is permitted but changes no obligation. The agent should have proposed this set from evidence, not defaulted to `core` ([ADOPTION.md §4.0](ADOPTION.md)); your job is to confirm the triggers it fired, trim any the evidence does not support, **and add any applicable trigger the proposal missed**. This is not modesty for its own sake: every profile adds obligations the repository must meet and selects the structural and mechanically decidable gates the validator can enforce on future pushes; the remaining semantics stay with human review ([ADOPTION.md §3.6](ADOPTION.md), [§3.8](ADOPTION.md)). Selecting `trust-critical` "to be safe" when the repository makes no such claim adds mandatory claims you may not want — but *under*-selecting a repository that genuinely is trust-critical is the more dangerous error, because it quietly turns off the checks that repository needs. Trim what the evidence does not support; keep what it does; add what it missed.

**If the proposal says `archived`, use this checklist instead.** `archived` must be the only declared profile. Open the system artifact resolved from the configured adoption declaration's `paths.system` mapping (default declaration: `.agentic-assurance/adoption.yaml`; default artifact: `assurance/SYSTEM.md`) and personally confirm that it records all four facts:

- the repository is retained solely for historical reference, is not supported or intended for current use, and has no active operation, functional maintenance, or feature development;
- its historical purpose;
- its known material limitations;
- its last supported revision or release, or an explicit statement that none exists.

The current validator checks that `archived` is exclusive and that the mapped system artifact exists and is non-empty. At `HUMAN_REVIEWED` or `CONFORMANT`, it also rejects an untouched template by detecting any of the four exact shipped markers: `REPLACE_WITH_ARCHIVED_OPERATION_MAINTENANCE_AND_FEATURE_DEVELOPMENT_STATUS`, `REPLACE_WITH_ARCHIVED_HISTORICAL_PURPOSE`, `REPLACE_WITH_ARCHIVED_MATERIAL_LIMITATIONS`, and `REPLACE_WITH_ARCHIVED_LAST_SUPPORTED_REVISION_OR_RELEASE_OR_EXPLICIT_NONE`. These are completion guards only: the validator does **not** yet determine whether replacement prose actually states all four facts or whether it is truthful. Until structured content enforcement lands in [#40](https://github.com/MosslandOpenDevs/agentic-assurance-profile/issues/40), this checklist and your recorded review are the semantic backstop. If the repository is supported or intended for current use, is still operated, receives functional maintenance, or receives feature development, reject `archived` and classify the active profiles instead. Initial adoption, factual corrections, and upkeep of assurance metadata do not by themselves count as functional maintenance.

**With your answer,** the agent records the profile list in the configured adoption declaration; for `archived`, it also records the four confirmed facts in the mapped system artifact. Continuous validation holds the repository to the declared shape, while your review supplies the archived content confirmation that validation does not yet perform.

### 2. Intent confirmation of critical invariants

**The real question:** *the code does X — is X what you WANT?*

The archaeology finds behaviors: the code limits login attempts, expires sessions after an hour, rejects duplicate emails. The code proves what the system *does*; it cannot prove what you *want* ([PROFILE.md §4](../PROFILE.md)). So each critical behavior comes to you as a question, currently marked `UNKNOWN`.

**A good answer** is one plain sentence per item, using the classification that matches the decision:

- `INTENDED` — "yes, that's what I want";
- `ACCIDENTAL` — "no, that's an accident — it shouldn't do that";
- `COMPATIBILITY` — "we do not want this as the new design, but this named compatibility obligation still requires it";
- `DEPRECATED` — "support this only through the approved removal path";
- `UNKNOWN` — "I cannot decide this yet from the information available."

"Actually I want Y instead" classifies the current X honestly and creates the scoped change needed to establish Y; it does not rewrite current behavior into intended behavior. An `INTENDED`, `COMPATIBILITY`, or `DEPRECATED` answer records you as the authority for that affirmative disposition — your decision, not the code's age, supplies the authority.

**It is normal to leave some items `UNKNOWN`.** `UNKNOWN` is an honest recorded answer, not a failure grade ([Glossary §3](GLOSSARY.md)); you can confirm the five behaviors you have real opinions about and leave the rest for a later pass.

**Documents in the repository do not count as your approval.** In an agent-built repository the comments, READMEs, and design notes were mostly written by agents too — an agent citing "the docs say this is intentional" may be citing another agent. Your agent is expected to check who authored such prose before treating it as intent — and a document *without* agent markers is not necessarily human-written either, since many agents leave no trace. Either way, it is your answer in this review — not any committed text — that settles the classification and supplies any required human authority.

**Fewer is stronger.** A healthy register holds roughly 5–15 invariants — the things that must never break. If your agent brings you thirty, ask it to rank them and keep the top tier; every entry you confirm is something you will re-examine whenever a change touches it.

**With your answer,** the agent updates the intent classification in the invariants file and, for `INTENDED`, `COMPATIBILITY`, or `DEPRECATED`, records you as the human authority.

### 3. Residual disposition

**The real question:** here is a known limitation — do you carry it, or do we fix it?

The proposal will list residuals: things that are imperfect and known to be imperfect ([Glossary §1](GLOSSARY.md)). For each one you have three answers:

- **Accept** — you knowingly carry the risk. This is an explicit recorded decision: the register stores your name (`accepted_by`), the non-future date (`accepted_at`), and your reason, plus a review date after which the question comes back.
- **Reject** — you disagree that this is tolerable; it becomes work to schedule.
- **Remediate** — fix it now; the agent scopes a separate change for it.

**A good answer** is again one sentence, with a reason: "accept — we run one server and will all year" beats a bare "accept". The profile's goal is **not zero residuals but OWNED residuals** — a project with ten accepted, dated, owner-named residuals is in better shape than a project claiming to have none. What the profile prohibits is hidden limitations, not limitations ([PROFILE.md §2.8](../PROFILE.md), [§12](../PROFILE.md)).

One boundary to know: an agent can draft a residual and recommend a disposition, but it is forbidden from accepting a critical one for you ([PROFILE.md §15](../PROFILE.md)). If a critical residual shows up pre-accepted, something went wrong — say so.

**With your answer,** the agent updates the residual register: accepted items get your name, date, rationale, and review date; the rest become scheduled work.

### 4. Public claim wording

**The real question:** does this public promise say more than we can prove?

If the repository makes public claims — "your data is encrypted", "history is verifiable" — the profile requires the wording to stay within what the evidence supports ([PROFILE.md §8](../PROFILE.md)). The agent will flag claims that overreach their evidence.

**A good answer** usually doesn't delete the claim; it adds an honest limit line. "All data is encrypted" backed only by transport encryption becomes "data is encrypted in transit; at-rest encryption is not currently claimed". The claim gets smaller and becomes true.

**With your answer,** the agent records the approved wording and its limitation in the claims file — and that wording is then yours: future changes to it come back to you.

## How to answer

In plain language, in your own words, in your own working language. All of these are complete, recordable answers:

> "Yes, 10 per minute is what I want."
> "That second one is an accident — file it as something to remove."
> "Accept the single-server one; revisit if we ever scale."
> "Soften that encryption sentence the way you suggested."

The agent's job is to translate your sentences into the YAML artifacts, statuses, and dates — that direction of translation is exactly what it is good at. **You never need to edit YAML yourself** unless you want to. What matters is that the decisions are yours; the file format is clerical.

If a question is unclear, make the agent rephrase until it is a question about your product, not about the profile's vocabulary. "Should INV-003's enforcement reference be marked INFERRED?" is a bad question to bring an owner; "I found no test proving expired sessions are rejected — do you want one?" is the same question, asked properly.

## After you decide

- **Your answers become a durable review record** — not just chat history. The decisions land in the artifacts and in a review record (for example under `assurance/reviews/`), and merging the pull request becomes the durable evidence that the review happened ([ADOPTION.md §4.3](ADOPTION.md)).
- **Remediations arrive as separate, scoped pull requests** — one concern each, reviewable on its own, referencing the gap it closes ([ADOPTION.md §4.4](ADOPTION.md)). The adoption proposal itself stays a proposal; fixes don't sneak into it.
- **Accepted residuals come back to you.** Each carries a `review_after` date; when it passes, the question returns — "still true? still acceptable?" — because accepting a risk once is not accepting it forever ([PROFILE.md §12](../PROFILE.md)).
- **Advancing the adoption stage is your act** ([ADOPTION.md §3.8](ADOPTION.md)). The adoption stays `DRAFT` until you complete this review. It becomes `HUMAN_REVIEWED` when your non-future review is recorded — the stage-defined completion placeholders are gone, your name and the review record are present, that record exists in the project, and every active critical invariant has a recorded classification (`UNKNOWN` is allowed). It becomes `CONFORMANT` only when an attributable, non-future approval on or after the review date attests the full claim (`covers` omitted, or containing `CONFORMANCE`) and all applicable §6/§17 conditions are met; for an active adoption, that also means current review dates and an intent other than `UNKNOWN` or `ACCIDENTAL` for every critical invariant. The exclusive archived path uses its historical conditions instead. Only an explicit, human-approved `CONFORMANT` declaration asserts the full normative claim; a green validator check covers its mechanical subset, not its truth. Declaring a stage is a promise the validator enforces: declare one you don't meet and the build goes red.

## A worked example

A complete exchange, the size it should actually be:

> **Agent:** Two questions from the assessment.
>
> First: the code limits login attempts to 10 per minute per IP address. I found no document choosing that number, so it is currently `UNKNOWN`. Is limiting login attempts to 10 per minute per IP what you want this system to do?
>
> Second: that limit is counted in each server's own memory. Today you run one server, so it works as stated — but if you ever run two, an attacker would effectively get 20 per minute. I drafted this as a residual. Do you accept it, or should I propose a shared-counter fix?

> **Owner:** Yes, 10 per minute is what I want — record it as intended. And accept the single-server one; we'll be on one server at least through next year, but flag it for review next June.

That is a finished review of both items. The agent records the invariant as `INTENDED` with the owner as authority; the residual becomes `ACCEPTED` with the owner's name, the date, the rationale ("single-server deployment through next year"), and `review_after: 2027-06-01`. Two plain sentences from the owner; all the YAML is the agent's job.

## Related documents

- [GLOSSARY.md](GLOSSARY.md) — every term above, defined in plain language with Korean glosses
- [ADOPTION.md](ADOPTION.md) — the agent-facing adoption walk-through this guide mirrors
- [PROFILE.md](../PROFILE.md) — the normative text; §3 (your authority), §4 (classifications), §12 (residuals), §15 (what agents may never do)
- [templates/AGENTIC_ASSURANCE.md](../templates/AGENTIC_ASSURANCE.md) — the expected shape of the proposal you'll receive (§12)
