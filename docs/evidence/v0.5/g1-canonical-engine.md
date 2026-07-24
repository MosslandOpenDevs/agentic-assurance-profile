# v0.5 Gate G1 — canonical engine decision record

> **DRAFT — VERDICT PENDING — NON-NORMATIVE — NOT ACCEPTED**
>
> This record marshals the go/no-go evidence for Gate G1 as defined in
> [V0.5-DESIGN.md §"Gate G1 — canonical engine go/no-go"](../../V0.5-DESIGN.md).
> It does not itself decide G1. Per the repository's decision pattern the
> recorded outcome is an owner act in
> [#56](https://github.com/MosslandOpenDevs/agentic-assurance-profile/issues/56);
> until then the verdict field below stays empty. Nothing here changes an
> adopter obligation; [PROFILE.md](../../../PROFILE.md) remains the only
> normative text.

## Question

Does v0.5 build the canonical Snapshot engine now, or ship the Foundation and
revisit the engine in a later minor? Per §G1 the recorded outcome is exactly
one of `GO(scope)`, `DEFER`, or `NO_GO`.

## Evidence against the §G1 "proceed to Phase 2" conditions

§G1 authorizes proceeding to the engine only when **all** of the following
hold. Assessed against the current `main` — `aap check` shipped in
[#69](https://github.com/MosslandOpenDevs/agentic-assurance-profile/pull/69),
the speculative acceptance verifier cut in
[#70](https://github.com/MosslandOpenDevs/agentic-assurance-profile/pull/70):

| §G1 condition | State | Basis |
|---|---|---|
| **Parity ready** — every supported fixture has a reviewed ledger entry; zero unexplained differences | **NOT MET** | The Phase-0 fixture manifest and expected-outcome ledger ([#49](https://github.com/MosslandOpenDevs/agentic-assurance-profile/issues/49)) are `PROPOSED_NOT_ACCEPTED` / `oracle: false`; no reviewed parity oracle exists. |
| **Evidence ready** — complete trial notes; ≥1 repeated problem unsolvable by docs or a CLI facade, **or** verified structural duplication / a necessary snapshot feature | **NOT MET** | One internal trial (`aap check` on the public pilot `links`); no external pilot. Its single finding — a missing `AGENTIC_ASSURANCE.md` reading-order block — is a docs/pin fix, not an engine-requiring problem. No structural-duplication measurement and no necessary snapshot-dependent feature have been produced. |
| **Spike ready** — one bounded vertical slice passes the pre-registered cases | **NOT MET** | The bounded canonical-engine spike ([#56](https://github.com/MosslandOpenDevs/agentic-assurance-profile/issues/56)) has not been pre-registered or run. |
| **Scope clean** — no new normative obligation mixed into the engine move | **N/A** | No engine move attempted. |
| **Fallback viable** — the project can still release the Phase-1 Foundation if the prototype is stopped | **MET** | The Foundation is shippable now: `aap check` (ADOPTER_SNAPSHOT) is on `main`, the v0.4 engine is unchanged, and the boundary / CI / finding work stands. |

## §G1 default and recommendation

§G1 states that when all trials are internal and usability observation is the
only GO evidence, **the default decision is `DEFER` or `NO_GO`**; and that if
any condition fails, the project should stop the full rewrite, ship the
boundary / finding / CI / CLI work as v0.5.0, collect more adoption evidence,
and revisit the engine in a later minor — "this is not a failed v0.5."

Both triggers apply here: the only GO evidence is one internal usability trial,
and three of the four applicable conditions are unmet.

**Recommended outcome: `DEFER`.** Ship the Foundation as v0.5.0; do not open the
canonical-engine track ([#56](https://github.com/MosslandOpenDevs/agentic-assurance-profile/issues/56)
spike; [#57](https://github.com/MosslandOpenDevs/agentic-assurance-profile/issues/57)
/ [#58](https://github.com/MosslandOpenDevs/agentic-assurance-profile/issues/58)
GO-conditional work) on the current evidence. `NO_GO` is also defensible if the
maintainer judges the canonical engine out of scope for the v0.5 line entirely;
`GO(scope)` is **not** available on the current evidence.

## What a future GO would require (so it cannot happen by drift)

A `GO(scope)` needs a reviewed G1 pre-registration under #56 that freezes its
acceptance cases, evidence thresholds, reviewer (distinct from the spike
implementer), and effort cap — **and** at least one of:

1. an external pilot, or a repeated problem that documentation and the CLI
   facade demonstrably cannot solve; or
2. verified structural duplication — a reproducible measurement naming the
   semantic transformation, ≥2 independent production consumers across ≥2 rule
   or workflow families, fixtures showing equivalent meaning, a preselected
   collapse threshold, and an independent approving reviewer; or
3. a proven necessary snapshot-dependent feature that neither documentation nor
   the Phase-1 facade can provide.

A scoped GO would then name only the measured seam and the exact rule families
and dependencies it authorizes; default-engine cutover remains a separate
recorded decision.

## Recorded outcome

_Pending — the maintainer records `GO(scope)` / `DEFER` / `NO_GO` in_
[#56](https://github.com/MosslandOpenDevs/agentic-assurance-profile/issues/56).
When recorded as `DEFER` or `NO_GO`, update the `G1 final record` lifecycle line
in [V0.5-DESIGN.md](../../V0.5-DESIGN.md) and freeze that design per its
lifecycle contract.

## References

- [V0.5-DESIGN.md §Gate G1](../../V0.5-DESIGN.md)
- [#56](https://github.com/MosslandOpenDevs/agentic-assurance-profile/issues/56) — Pre-register, run, and decide the bounded canonical-engine spike (G1)
- [#48](https://github.com/MosslandOpenDevs/agentic-assurance-profile/issues/48) — Deliver the Foundation, record evidence gates, and conditionally migrate the engine (umbrella)
- [#57](https://github.com/MosslandOpenDevs/agentic-assurance-profile/issues/57) / [#58](https://github.com/MosslandOpenDevs/agentic-assurance-profile/issues/58) — canonical work conditional on GO
- [#49](https://github.com/MosslandOpenDevs/agentic-assurance-profile/issues/49) — Freeze the fixture manifest, parity ledger, and adoption evidence (parity input, still Phase 0)
