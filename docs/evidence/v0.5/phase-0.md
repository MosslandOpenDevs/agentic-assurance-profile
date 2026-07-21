# v0.5 Phase 0 evidence log

> **SCAFFOLD — NOT ACCEPTED — NOT AN ORACLE — COVERAGE INCOMPLETE**

This log accompanies the first bounded slice of issue #49. It does not mark
Phase 0 complete, supply a G1 decision, or count static engine fixtures as
adoption trials.

## Slice decision

The owner recorded the `START` decision in
[#49's bounded-slice kickoff](https://github.com/MosslandOpenDevs/agentic-assurance-profile/issues/49#issuecomment-5028818203):

- working base: `main@4ecf81cbe161281652fd543abc15d270f8656e18`;
- reference: `v0.4.0@00e2fe46d4eb01a4147f149851a48a3017cbb796`;
- effort cap: four elapsed working hours, not increasable while active;
- stop if fixture determinism requires behavior changes, the ledger becomes a
  new normative source/public contract, or the slice cannot fit the cap;
- output: a Draft PR, with any expansion requiring a new reviewed decision.

No stop condition has authorized a scope expansion. This slice changes only
documentation and test data.

## Reference identity

| Item | Identity |
|---|---|
| annotated tag object | `1373d963a098e13d2f44891e58ee8a47e285c5c3` |
| peeled release commit | `00e2fe46d4eb01a4147f149851a48a3017cbb796` |
| validator Git blob | `af5f7c39373f6dc6ced93d437cec4b972851e3a3` |
| requirements Git blob | `1fbebbbb08277b81307439866de067ebd224515b` |

The executable was run from a clean detached worktree at the peeled commit.
Current `main` was not substituted for the reference. The locked environment
used CPython 3.14.6, PyYAML 6.0.3, and jsonschema 4.26.0 installed with
`pip --require-hashes` from the release's `requirements-ci.txt`.

Candidate identities at the observed head are:

| Candidate | SHA-256 |
|---|---|
| corpus aggregate | `cb9710c7b27350e11b69450d8d4cc6bb95f0d8adb3e37ae474d3512d64d6a293` |
| raw `manifest.json` | `4cd135234698b47c9b4444ca0cb00121b1da872ff8abf4ac9ccf32015009387b` |
| raw proposed `expected-outcomes.json` | `3c404a9bbc4583a046e789da24fff207994e7fda2e9ea9d01b91b71e71992e1c` |

These are candidate byte identities, not an acceptance binding. The ledger
contains the manifest hash, while neither candidate contains its own hash.

## Seed observations

Reference execution recorded only observed exit status, level counts, empty
stderr, and selected bounded predicates. Those observations remain separate
from the authority-backed proposals in `expected-outcomes.json`.

| Case | Reference observation | Interpretation status |
|---|---|---|
| `core-split-draft-pass` | exit 0; 12 ok, 0 warn, 0 error | proposed, not accepted |
| `core-lite-draft-pass` | exit 0; 12 ok, 0 warn, 0 error | proposed, not accepted |
| `archived-reviewed-pass` | exit 0; 9 ok, 1 warn, 0 error | proposed, not accepted |
| `transition-stage-downgrade-block` | exit 1; 0 ok, 0 warn, 1 error | proposed, not accepted |
| `trust-path-traversal-block` | exit 1; 11 ok, 0 warn, 2 errors | proposed, not accepted |
| `drift-routing-strict-block` | exit 1; 0 ok, 0 warn, 1 error | proposed, not accepted |
| `central-self-check-pass` | exit 0; 25 ok, 0 warn, 0 error | proposed, not accepted |

The seven invocations were repeated from two independently copied fresh corpus
roots. The selected projection was identical in both runs, with non-normative
projection SHA-256
`9793a59d5ebd86a0e80e9bca2d890121f3168216e402f83c8a58905eab60ebd6`.
This comparison establishes reproducibility of the selected observation only;
it does not make the v0.4.0 behavior correct.

## Remaining evidence before #49 can close

The seven seeds do not yet supply a complete fixture matrix, an accepted
manifest/ledger binding, a real dogfood adopter, either required end-to-end
trial, independent operator evidence, usability metrics, or the #43 event
contract. External usability evidence remains `UNKNOWN`; this scaffold makes
no claim that v0.4.0 is easy or difficult to adopt.

A later acceptance record must live outside the candidate files and bind the
exact commit plus raw manifest and ledger SHA-256 values and the actual review
classes. Until then, no implementation PR may use this seed as an oracle or
rewrite it to approve its own difference.
