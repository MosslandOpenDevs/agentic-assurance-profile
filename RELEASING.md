# Release Process

This document defines how the profile is versioned and released, the exact lifecycle of the root `VERSION` file, and the repository settings that must be in place before the first release. Decision authority over releases is defined in [GOVERNANCE.md](GOVERNANCE.md); the semantic-versioning rules that classify each change are defined in [PROFILE.md](PROFILE.md) §16.

Release identifiers have the form `vMAJOR.MINOR.PATCH`. Pre-releases have the form `vMAJOR.MINOR.PATCH-rc.N`. Numeric identifiers use ASCII decimal digits, have no leading zero unless the identifier is exactly zero, and release candidates start at `rc.1`.

## 1. The `VERSION` file lifecycle

The root [`VERSION`](VERSION) file contains exactly one token line (with at most one terminal newline and no surrounding whitespace or additional lines) and moves through exactly three states:

1. **`unreleased`** — from repository creation until the first release commit. This was the initial pre-first-release state; after the first release it remains valid only in historical pilot commits.
2. **The exact tag string** — set by the release pull request. Its branch commit may carry the candidate identifier, but only the tagged merge commit is the canonical release and adopter pin: for example `v0.1.0`, or `v0.1.0-rc.1` for a pre-release.
3. **A development identifier ending in `-dev`** — set by the first commit after tagging:
   - after a release `vX.Y.Z`, the follow-up commit sets `VERSION` to `vX.Y.(Z+1)-dev` (for example `v0.1.1-dev` immediately after `v0.1.0`);
   - after a pre-release `vX.Y.Z-rc.N`, the follow-up commit sets `VERSION` to `vX.Y.Z-dev`, because development continues toward the final `vX.Y.Z`.

The development identifier is a placeholder, not a commitment: the next release may carry a different number (for example a minor release instead of a patch), and its own release pull request sets the real string.

This lifecycle gives the `VERSION` file a precise meaning at every commit in the history:

- a commit whose `VERSION` is a bare release identifier is a release-candidate commit; it is the canonical release commit only when the matching immutable tag points to it;
- a commit whose `VERSION` ends in `-dev` lies between releases and must never be pinned;
- a commit whose `VERSION` is `unreleased` predates the first release.

Adopters may pin only commits whose `VERSION` content equals their declared `upstream.version`: the canonical commit carrying the matching immutable release tag once releases exist, or `unreleased` with a full commit SHA during the pre-first-release pilot phase. Conformance checking fails when the pinned version does not match the `VERSION` file at the pinned commit (PROFILE.md §16); `scripts/validate.py adopter` performs this comparison when given a pinned profile checkout. When that checkout carries Git metadata, it also requires `HEAD == upstream.commit`, requires the running validator to be that checkout's validator, and rejects modified, substituted, or untracked validation resources under `VERSION`, `requirements-ci.txt`, `scripts/`, and `schemas/`. A source archive without Git metadata produces an explicit warning because only its `VERSION`, not its commit identity or worktree cleanliness, can be bound mechanically. The `-dev` suffix is only ever valid in this repository's `VERSION` file, never in an adopter pin.

## 2. Release ritual

1. **Release pull request.** One pull request that:
   - moves the `## Unreleased` content of [CHANGELOG.md](CHANGELOG.md) into a new section for the release, including an **Adopter impact / upgrade actions** subsection that states what an adopting repository must do when upgrading (state "none" explicitly when nothing is required);
   - sets `VERSION` to the exact tag string;
   - updates the [SECURITY.md](SECURITY.md) supported-versions table so the new release is marked current and the release it supersedes is demoted — the security policy must never assert that a superseded release is current;
   - states the release's semver classification per PROFILE.md §16;
   - states the release's review class per [GOVERNANCE.md](GOVERNANCE.md) §2 (currently `SOLE_OWNER_ATTESTED + AUTOMATION_VERIFIED` until a second active maintainer exists), citing any external technical reviews the release incorporates — the class is a fact about the record, stated per release, not inherited silently from the standing default;
   - is reviewed per [GOVERNANCE.md](GOVERNANCE.md) — a major release requires explicit governing-body approval recorded in this pull request.
2. **Merge.** The merge commit on `main` is the release commit.
3. **Tag.** Create the tag (for example `v0.1.0`) on the merge commit. The tag string must equal the `VERSION` content at that commit. Note that the release pull request's branch commit also carries the same `VERSION` content and remains reachable as the merge's second parent — **the tag commit is the canonical adopter pin**, and the `adopter-validate` workflow rejects a release pin whose commit is not the one the tag points to.
4. **GitHub Release.** Publish a GitHub Release for the tag whose body is the CHANGELOG section for that version.
5. **Follow-up commit.** Immediately set `VERSION` to the next development identifier per §1, so that no subsequent commit can be mistaken for the release commit.

## 3. Tag immutability

A published tag is immutable. It must never be moved, deleted, or reused. A defective release is corrected by a new release under a new tag — normally the next patch version — never by re-tagging. This rule is what makes an adopter's version-plus-commit pin trustworthy, and it is enforced by the `v*` tag ruleset required in §5.

## 4. Pre-releases

Pre-releases use the identifier `vX.Y.Z-rc.N`, starting at `rc.1`, and follow the same ritual as §2 with two differences:

- the GitHub Release is marked as a pre-release;
- the CHANGELOG section may defer the full **Adopter impact / upgrade actions** subsection to the final release, but must say so explicitly.

Pre-release tags are immutable exactly like release tags. An adopter may pin a pre-release (`upstream.version: vX.Y.Z-rc.N`) under the same `VERSION`-match rule as any other pin.

## 5. Pre-first-release checklist

All of the following must be complete before the first tag (`v0.1.0-rc.1` or `v0.1.0`) is created. These are repository and organization settings; none of them are visible in the repository content alone.

1. Enable **Private Vulnerability Reporting** for this repository, as required by [SECURITY.md](SECURITY.md).
2. Enable branch protection on `main` with at least one required approving human review, per [GOVERNANCE.md](GOVERNANCE.md).
3. Create a tag ruleset protecting `v*` tags from movement, deletion, and creation outside the release process.
4. Replace the placeholder team in [.github/CODEOWNERS](.github/CODEOWNERS) with real maintainer handles and require code-owner review on protected branches.
5. Confirm [LICENSE](LICENSE) (Apache-2.0), [LICENSE-docs](LICENSE-docs) (CC-BY-4.0), and [templates/LICENSE](templates/LICENSE) (CC0-1.0) are present and unmodified.
6. Confirm the organization's `.github` repository is public, so that organization default community health files apply to repositories that rely on them (see [docs/DISCLOSURE-AND-ISSUES.md](docs/DISCLOSURE-AND-ISSUES.md) §11).
7. Run `python scripts/validate.py self-check` and confirm it reports no errors; the `self-check` workflow must be green on the release pull request.
