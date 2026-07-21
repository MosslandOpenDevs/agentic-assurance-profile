#!/usr/bin/env python3
"""Verify the offline Git-object portion of a Phase 0 acceptance decision.

This is an internal, standard-library-only verifier.  A successful result means
that the candidate, decision, corpus, ledger, and governance bytes are bound as
recorded in the local Git object database.  It does *not* prove protected-main
provenance, GitHub review state, human identity, or human authority.

The verifier deliberately supports only the first semantic-ledger decision
shape: no implementation-parity authorization and no successor decisions.
It never fetches, checks out, creates a worktree, or reads policy inputs from
the repository working tree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
from typing import Any


SHA1_RE = re.compile(r"[0-9a-f]{40}\Z")
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
DECISION_ID_RE = re.compile(r"[A-Z0-9][A-Z0-9._-]{2,127}\Z")
REPOSITORY_RE = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
INTERNAL_CONDITION_RE = re.compile(r"phase0\.internal\.[a-z0-9._-]+\Z")

MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_BLOB_BYTES = 16 * 1024 * 1024
MAX_TREE_BYTES = 64 * 1024 * 1024
MAX_TREE_FILES = 10_000
GIT_TIMEOUT_SECONDS = 20

DECISION_DIRECTORY = "docs/evidence/v0.5/oracle-decisions"
CHARACTERIZATION_DIRECTORY = "tests/characterization"
MANIFEST_NAME = "manifest.json"
LEDGER_NAME = "expected-outcomes.json"

VERIFIED_CHECKS = [
    "decision-preexists-consumer-base",
    "decision-record-history-immutable",
    "acceptance-only-tree-diff",
    "candidate-precedes-decision",
    "candidate-raw-hashes",
    "corpus-digest",
    "ledger-revision-and-scope",
    "governance-revision-bytes",
]

UNVERIFIED_EXTERNAL_PREDICATES = [
    "protected-canonical-main",
    "github-acceptance-pr-state",
    "factual-human-decision-maker",
    "factual-review-classes",
]

UNVERIFIED_PRECONDITIONS = [
    "verifier-executable-provenance",
    "git-executable-provenance",
    "local-repository-origin",
    "expected-repository-argument-authority",
]

UNVERIFIED_AUTHORITY_PREDICATES = [
    "semantic-authority-reference-validity",
    "published-release-tag-state",
    "github-release-pr-state",
    "github-release-workflow-run-state",
]


class VerificationError(Exception):
    """A controlled, fail-closed verification error."""


def fail(message: str) -> None:
    raise VerificationError(message)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def require_mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{field} must be an object")
    return value


def require_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        fail(f"{field} must be an array")
    return value


def require_string(value: Any, field: str, *, nonempty: bool = True) -> str:
    if not isinstance(value, str) or (nonempty and not value):
        fail(f"{field} must be a{' non-empty' if nonempty else ''} string")
    return value


def require_int(value: Any, field: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        fail(f"{field} must be an integer >= {minimum}")
    return value


def require_sha1(value: Any, field: str) -> str:
    value = require_string(value, field)
    if SHA1_RE.fullmatch(value) is None:
        fail(f"{field} must be a full lowercase 40-hex SHA-1")
    return value


def require_sha256(value: Any, field: str) -> str:
    value = require_string(value, field)
    if SHA256_RE.fullmatch(value) is None:
        fail(f"{field} must be a lowercase 64-hex SHA-256")
    return value


def require_ascii(value: str, field: str) -> str:
    try:
        value.encode("ascii")
    except UnicodeEncodeError:
        fail(f"{field} must contain ASCII only")
    return value


def require_repo_path(
    value: Any,
    field: str,
    *,
    allow_dot: bool = False,
) -> str:
    value = require_ascii(require_string(value, field), field)
    if allow_dot and value == ".":
        return value
    if "\\" in value or value.startswith("/"):
        fail(f"{field} must be a POSIX repository-relative path")
    path = PurePosixPath(value)
    if any(part in {"", ".", ".."} for part in path.parts):
        fail(f"{field} contains a forbidden path component")
    if path.as_posix() != value:
        fail(f"{field} is not in canonical POSIX form")
    return value


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise VerificationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_json(data: bytes, field: str) -> dict[str, Any]:
    if len(data) > MAX_JSON_BYTES:
        fail(f"{field} exceeds the {MAX_JSON_BYTES}-byte JSON limit")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        fail(f"{field} is not UTF-8 JSON: {exc}")
    try:
        value = json.loads(
            text,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=lambda token: (_ for _ in ()).throw(
                VerificationError(f"non-finite JSON value: {token}")
            ),
        )
    except VerificationError:
        raise
    except (json.JSONDecodeError, RecursionError, ValueError) as exc:
        fail(f"{field} is not strict JSON: {exc}")
    return require_mapping(value, field)


class GitObjects:
    """Read values from an existing local Git object database."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        if not self.repo_root.is_dir():
            fail("--repo-root must name an existing directory")

        selected_git = shutil.which("git")
        if selected_git is None:
            fail("cannot resolve a Git executable from PATH")
        try:
            git_executable = Path(selected_git).resolve(strict=True)
        except OSError as exc:
            fail(f"cannot resolve the selected Git executable: {exc}")
        require(
            git_executable.is_file() and os.access(git_executable, os.X_OK),
            "selected Git executable is not an executable file",
        )
        self.git_executable = git_executable

        bare = self._run(["rev-parse", "--is-bare-repository"]).stdout.strip()
        require(bare in {b"true", b"false"}, "cannot determine whether the repository is bare")
        require(bare == b"false", "bare repositories are unsupported")
        top_level_bytes = self._run(["rev-parse", "--show-toplevel"]).stdout.rstrip(
            b"\r\n"
        )
        require(top_level_bytes, "cannot determine the repository top-level")
        try:
            top_level = Path(os.fsdecode(top_level_bytes)).resolve(strict=True)
        except OSError as exc:
            fail(f"cannot resolve the repository top-level: {exc}")
        require(
            top_level == self.repo_root,
            "--repo-root must exactly name the non-bare repository top-level",
        )
        self.repository_top_level = top_level

        version_bytes = self._run(["--version"]).stdout.strip()
        require(version_bytes and len(version_bytes) <= 200, "cannot determine a bounded Git version")
        try:
            self.git_version = version_bytes.decode("ascii", "strict")
        except UnicodeDecodeError:
            fail("Git version output is not ASCII")

        shallow = self._run(["rev-parse", "--is-shallow-repository"]).stdout.strip()
        require(shallow in {b"true", b"false"}, "cannot determine whether the repository is shallow")
        require(shallow == b"false", "shallow repositories are unsupported")

    def _run(
        self,
        args: list[str],
        *,
        allowed_returncodes: tuple[int, ...] = (0,),
    ) -> subprocess.CompletedProcess[bytes]:
        # Do not inherit Git repository, object, index, namespace, shallow,
        # or config redirections from the caller. A promisor clone must fail
        # on a missing object instead of lazily contacting a remote.
        environment = {
            key: os.environ[key]
            for key in (
                "PATH",
                "PATHEXT",
                "SYSTEMROOT",
                "WINDIR",
                "COMSPEC",
                "TMPDIR",
                "TMP",
                "TEMP",
            )
            if key in os.environ
        }
        environment.update(
            {
                "LC_ALL": "C",
                "LANG": "C",
                "GIT_NO_LAZY_FETCH": "1",
                "GIT_GRAFT_FILE": os.devnull,
                "GIT_OPTIONAL_LOCKS": "0",
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_SYSTEM": os.devnull,
                "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_CONFIG_COUNT": "0",
                "GIT_TERMINAL_PROMPT": "0",
            }
        )
        command = [
            str(self.git_executable),
            "--no-replace-objects",
            "-C",
            str(self.repo_root),
            *args,
        ]
        try:
            completed = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=GIT_TIMEOUT_SECONDS,
                check=False,
                env=environment,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            fail(f"local Git object inspection failed: {exc}")
        if completed.returncode not in allowed_returncodes:
            diagnostic = completed.stderr.decode("utf-8", "replace").strip()
            if len(diagnostic) > 500:
                diagnostic = diagnostic[:500] + "..."
            fail(f"local Git command failed: {diagnostic or 'no diagnostic'}")
        return completed

    def object_type(self, oid: str) -> str:
        require_sha1(oid, "Git object ID")
        output = self._run(["cat-file", "-t", oid]).stdout
        return output.decode("ascii", "strict").strip()

    def require_commit(self, oid: str, field: str) -> None:
        require_sha1(oid, field)
        if self.object_type(oid) != "commit":
            fail(f"{field} does not identify a commit object")

    def commit_parents(self, commit: str) -> list[str]:
        self.require_commit(commit, "commit")
        line = self._run(["rev-list", "--parents", "-n", "1", commit]).stdout
        parts = line.decode("ascii", "strict").strip().split()
        require(parts and parts[0] == commit, "unexpected rev-list result")
        for parent in parts[1:]:
            require_sha1(parent, "commit parent")
        return parts[1:]

    def first_parent_contains(self, ancestor: str, descendant: str) -> bool:
        self.require_commit(ancestor, "first-parent ancestor")
        self.require_commit(descendant, "first-parent descendant")
        output = self._run(["rev-list", "--first-parent", descendant]).stdout
        return ancestor.encode("ascii") in output.splitlines()

    def first_parent_path_was_used(self, commit: str, path: str) -> bool:
        """Return whether ``path`` appeared in the first-parent history."""

        self.require_commit(commit, "path-history commit")
        path = require_repo_path(path, "path-history Git path")
        literal = f":(top,literal){path}"
        output = self._run(
            [
                "rev-list",
                "--first-parent",
                "--full-history",
                "--max-count=1",
                commit,
                "--",
                literal,
            ]
        ).stdout
        return bool(output.strip())

    def first_parent_decision_records_rewritten(self, commit: str) -> bool:
        """Return whether a canonical decision JSON was modified or deleted."""

        self.require_commit(commit, "decision-history commit")
        direct_json = f":(top,glob){DECISION_DIRECTORY}/*.json"
        output = self._run(
            [
                "log",
                "--first-parent",
                "--no-renames",
                "--format=%H",
                "--diff-filter=DMT",
                "--max-count=1",
                commit,
                "--",
                direct_json,
            ]
        ).stdout
        return bool(output.strip())

    @staticmethod
    def _parse_ls_tree(output: bytes, field: str) -> list[tuple[str, str, str, str]]:
        entries: list[tuple[str, str, str, str]] = []
        for raw in output.split(b"\0"):
            if not raw:
                continue
            try:
                metadata, raw_path = raw.split(b"\t", 1)
                mode, object_type, oid = metadata.decode("ascii").split(" ")
                path = raw_path.decode("utf-8")
            except (ValueError, UnicodeDecodeError) as exc:
                fail(f"malformed git ls-tree record for {field}: {exc}")
            require_sha1(oid, f"{field} object ID")
            entries.append((mode, object_type, oid, path))
        return entries

    def path_entry(
        self, commit: str, path: str
    ) -> tuple[str, str, str, str] | None:
        self.require_commit(commit, "path commit")
        path = require_repo_path(path, "Git path")
        literal = f":(top,literal){path}"
        output = self._run(
            ["ls-tree", "-z", "--full-tree", commit, "--", literal]
        ).stdout
        entries = self._parse_ls_tree(output, path)
        if not entries:
            return None
        if len(entries) != 1 or entries[0][3] != path:
            fail(f"Git path lookup was not exact: {path}")
        return entries[0]

    def read_blob_oid(self, oid: str, field: str) -> bytes:
        require_sha1(oid, f"{field} blob ID")
        if self.object_type(oid) != "blob":
            fail(f"{field} is not a blob")
        size_text = self._run(["cat-file", "-s", oid]).stdout
        try:
            size = int(size_text.decode("ascii", "strict").strip())
        except (ValueError, UnicodeDecodeError):
            fail(f"cannot read the size of {field}")
        if size < 0 or size > MAX_BLOB_BYTES:
            fail(f"{field} exceeds the {MAX_BLOB_BYTES}-byte blob limit")
        data = self._run(["cat-file", "blob", oid]).stdout
        require(len(data) == size, f"{field} blob size changed while reading")
        return data

    def read_regular_path(self, commit: str, path: str, field: str) -> bytes:
        entry = self.path_entry(commit, path)
        if entry is None:
            fail(f"{field} is missing at {commit}: {path}")
        mode, object_type, oid, _ = entry
        if mode != "100644" or object_type != "blob":
            fail(f"{field} must be a regular mode-100644 Git blob")
        return self.read_blob_oid(oid, field)

    def list_regular_tree(
        self,
        commit: str,
        scope: str,
        field: str,
    ) -> tuple[list[dict[str, Any]], int]:
        self.require_commit(commit, f"{field} commit")
        scope = require_repo_path(scope, f"{field} scope", allow_dot=True)
        arguments = ["ls-tree", "-r", "-z", "--full-tree", commit]
        prefix = ""
        if scope != ".":
            entry = self.path_entry(commit, scope)
            if entry is None or entry[0] != "040000" or entry[1] != "tree":
                fail(f"{field} scope is not a Git tree: {scope}")
            arguments += ["--", f":(top,literal){scope}"]
            prefix = scope + "/"
        output = self._run(arguments).stdout
        entries = self._parse_ls_tree(output, field)
        if not entries:
            fail(f"{field} contains no tracked files")
        if len(entries) > MAX_TREE_FILES:
            fail(f"{field} exceeds the {MAX_TREE_FILES}-file limit")

        records: list[dict[str, Any]] = []
        total_bytes = 0
        seen: set[str] = set()
        for mode, object_type, oid, full_path in entries:
            if mode != "100644" or object_type != "blob":
                fail(f"{field} contains unsupported Git mode/type at {full_path}")
            if prefix:
                if not full_path.startswith(prefix):
                    fail(f"{field} returned a path outside its scope")
                relative_path = full_path[len(prefix) :]
            else:
                relative_path = full_path
            relative_path = require_repo_path(relative_path, f"{field} path")
            if relative_path in seen:
                fail(f"{field} contains a duplicate path: {relative_path}")
            seen.add(relative_path)
            data = self.read_blob_oid(oid, f"{field}:{relative_path}")
            total_bytes += len(data)
            if total_bytes > MAX_TREE_BYTES:
                fail(f"{field} exceeds the {MAX_TREE_BYTES}-byte tree limit")
            records.append(
                {
                    "path": relative_path,
                    "size": len(data),
                    "sha256": sha256_bytes(data),
                }
            )
        records.sort(key=lambda item: item["path"].encode("ascii"))
        return records, total_bytes

    def root_tree_oid(self, commit: str) -> str:
        self.require_commit(commit, "root-tree commit")
        body = self._run(["cat-file", "-p", commit]).stdout
        first_line = body.splitlines()[0] if body else b""
        if not first_line.startswith(b"tree "):
            fail("commit object has no root tree")
        try:
            oid = first_line[5:].decode("ascii")
        except UnicodeDecodeError:
            fail("commit root-tree ID is not ASCII")
        require_sha1(oid, "commit root-tree ID")
        return oid

    def tag_target(self, tag_oid: str) -> str:
        require_sha1(tag_oid, "annotated tag object")
        if self.object_type(tag_oid) != "tag":
            fail("annotated_tag_object_sha1 is not a tag object")
        body = self._run(["cat-file", "-p", tag_oid]).stdout
        header, _, _message = body.partition(b"\n\n")
        lines = header.splitlines()
        object_lines = [line for line in lines if line.startswith(b"object ")]
        type_lines = [line for line in lines if line.startswith(b"type ")]
        if len(object_lines) != 1 or type_lines != [b"type commit"]:
            fail("annotated tag must point directly to one commit")
        try:
            target = object_lines[0][7:].decode("ascii")
        except UnicodeDecodeError:
            fail("annotated tag target is not ASCII")
        require_sha1(target, "annotated tag target")
        self.require_commit(target, "annotated tag target")
        return target

    def added_paths(self, parent: str, commit: str) -> list[tuple[str, str]]:
        output = self._run(
            [
                "diff-tree",
                "--no-commit-id",
                "--no-renames",
                "--name-status",
                "-r",
                "-z",
                parent,
                commit,
                "--",
            ]
        ).stdout
        parts = output.split(b"\0")
        if parts and parts[-1] == b"":
            parts.pop()
        if len(parts) % 2:
            fail("malformed git diff-tree name/status output")
        result: list[tuple[str, str]] = []
        for index in range(0, len(parts), 2):
            try:
                status = parts[index].decode("ascii")
                path = parts[index + 1].decode("utf-8")
            except UnicodeDecodeError as exc:
                fail(f"non-textual acceptance diff entry: {exc}")
            result.append((status, require_repo_path(path, "acceptance diff path")))
        return result


def check_manifest_reference(git: GitObjects, manifest: dict[str, Any]) -> None:
    reference = require_mapping(manifest.get("reference"), "manifest.reference")
    tag_oid = require_sha1(
        reference.get("annotated_tag_object_sha1"),
        "manifest.reference.annotated_tag_object_sha1",
    )
    peeled = require_sha1(
        reference.get("peeled_commit_sha1"),
        "manifest.reference.peeled_commit_sha1",
    )
    require(
        git.tag_target(tag_oid) == peeled,
        "manifest annotated tag does not peel to the recorded commit",
    )
    validator_blob = require_sha1(
        reference.get("validator_git_blob_sha1"),
        "manifest.reference.validator_git_blob_sha1",
    )
    requirements_blob = require_sha1(
        reference.get("requirements_git_blob_sha1"),
        "manifest.reference.requirements_git_blob_sha1",
    )
    validator_entry = git.path_entry(peeled, "scripts/validate.py")
    requirements_entry = git.path_entry(peeled, "requirements-ci.txt")
    require(
        validator_entry is not None
        and validator_entry[:3] == ("100644", "blob", validator_blob),
        "recorded v0.4.0 validator blob does not match the release commit",
    )
    require(
        requirements_entry is not None
        and requirements_entry[:3] == ("100644", "blob", requirements_blob),
        "recorded v0.4.0 requirements blob does not match the release commit",
    )


def verify_corpus(
    git: GitObjects,
    candidate_commit: str,
    manifest_parent: str,
    manifest: dict[str, Any],
) -> tuple[str, set[str]]:
    require(
        manifest.get("document_kind") == "phase0_fixture_manifest_scaffold",
        "unsupported manifest document_kind",
    )
    require(manifest.get("status") == "PROPOSED_NOT_ACCEPTED", "manifest self-authorizes")
    require(manifest.get("public_contract") is False, "manifest must not be public")
    require(manifest.get("coverage_complete") is False, "manifest overstates coverage")
    check_manifest_reference(git, manifest)

    root_records = require_list(manifest.get("root_records"), "manifest.root_records")
    require(root_records, "manifest.root_records must not be empty")
    verified_roots: list[dict[str, str]] = []
    root_ids: set[str] = set()
    for index, raw_record in enumerate(root_records):
        field = f"manifest.root_records[{index}]"
        record = require_mapping(raw_record, field)
        root_id = require_ascii(require_string(record.get("root_id"), f"{field}.root_id"), f"{field}.root_id")
        require(root_id not in root_ids, f"duplicate manifest root_id: {root_id}")
        root_ids.add(root_id)
        source = require_mapping(record.get("source"), f"{field}.source")
        source_kind = source.get("kind")
        if source_kind == "corpus_directory":
            commit = candidate_commit
            relative_scope = require_repo_path(
                source.get("path"), f"{field}.source.path"
            )
            # Corpus-directory sources are relative to the directory that
            # contains manifest.json, not to the repository root.
            scope = require_repo_path(
                f"{manifest_parent}/{relative_scope}",
                f"{field}.resolved_source_path",
            )
        elif source_kind == "git_commit":
            commit = require_sha1(source.get("commit_sha1"), f"{field}.source.commit_sha1")
            scope = require_repo_path(
                source.get("scope"), f"{field}.source.scope", allow_dot=True
            )
            require(scope == ".", f"{field} git_commit scope must be '.' in format v1")
            recorded_tree = require_sha1(
                source.get("git_tree_sha1"), f"{field}.source.git_tree_sha1"
            )
            require(
                git.root_tree_oid(commit) == recorded_tree,
                f"{field} Git root tree does not match",
            )
        else:
            fail(f"{field}.source.kind is unsupported")

        records, byte_count = git.list_regular_tree(commit, scope, field)
        file_count = len(records)
        expected_file_count = require_int(record.get("file_count"), f"{field}.file_count")
        expected_byte_count = require_int(record.get("byte_count"), f"{field}.byte_count")
        expected_tree_sha = require_sha256(record.get("tree_sha256"), f"{field}.tree_sha256")
        actual_tree_sha = sha256_bytes(canonical_json_bytes(records))
        require(file_count == expected_file_count, f"{field} file_count mismatch")
        require(byte_count == expected_byte_count, f"{field} byte_count mismatch")
        require(actual_tree_sha == expected_tree_sha, f"{field} tree_sha256 mismatch")
        verified_roots.append({"root_id": root_id, "tree_sha256": actual_tree_sha})

    verified_roots.sort(key=lambda item: item["root_id"].encode("ascii"))
    corpus_sha = sha256_bytes(canonical_json_bytes(verified_roots))
    digest = require_mapping(manifest.get("digest"), "manifest.digest")
    require(
        digest.get("algorithm")
        == "sha256-over-canonical-root-records-described-in-README",
        "unsupported manifest digest algorithm",
    )
    require(
        corpus_sha == require_sha256(digest.get("corpus_sha256"), "manifest.digest.corpus_sha256"),
        "manifest corpus_sha256 mismatch",
    )

    cases = require_list(manifest.get("cases"), "manifest.cases")
    case_ids: set[str] = set()
    for index, raw_case in enumerate(cases):
        case = require_mapping(raw_case, f"manifest.cases[{index}]")
        case_id = require_ascii(
            require_string(case.get("case_id"), f"manifest.cases[{index}].case_id"),
            f"manifest.cases[{index}].case_id",
        )
        require(case_id not in case_ids, f"duplicate manifest case_id: {case_id}")
        input_root = require_string(
            case.get("input_root_id"), f"manifest.cases[{index}].input_root_id"
        )
        require(input_root in root_ids, f"unknown input_root_id for case {case_id}")
        case_ids.add(case_id)
    require(case_ids, "manifest.cases must not be empty")
    return corpus_sha, case_ids


def authority_refs_resolve(
    refs: Any,
    field: str,
    authority_sources: dict[str, Any],
) -> None:
    for index, raw_ref in enumerate(require_list(refs, field)):
        ref = require_mapping(raw_ref, f"{field}[{index}]")
        source_id = require_string(ref.get("source_id"), f"{field}[{index}].source_id")
        require(source_id in authority_sources, f"{field}[{index}] has unknown source_id")
        require_string(ref.get("role"), f"{field}[{index}].role")


def verify_ledger(
    ledger: dict[str, Any],
    manifest_raw_sha256: str,
    manifest_case_ids: set[str],
) -> tuple[set[str], dict[str, bool]]:
    require(
        ledger.get("document_kind") == "phase0_expected_outcomes_scaffold",
        "unsupported ledger document_kind",
    )
    require(ledger.get("status") == "PROPOSED_NOT_ACCEPTED", "ledger self-authorizes")
    require(ledger.get("oracle") is False, "ledger must not self-declare an oracle")
    require(ledger.get("public_contract") is False, "ledger must not be public")
    require(ledger.get("acceptance_binding") is None, "candidate ledger contains an acceptance binding")
    require(
        require_sha256(
            ledger.get("fixture_manifest_raw_sha256"),
            "ledger.fixture_manifest_raw_sha256",
        )
        == manifest_raw_sha256,
        "ledger does not bind the candidate manifest bytes",
    )

    coverage = require_mapping(ledger.get("coverage"), "ledger.coverage")
    expected_coverage = {
        "phase0_matrix_complete": False,
        "semantic_projection_complete_for_selected_cases": True,
        "implementation_projection_complete_for_selected_cases": False,
    }
    require(coverage == expected_coverage, "unsupported semantic-only coverage shape")

    candidate_use = require_mapping(ledger.get("candidate_use"), "ledger.candidate_use")
    require(
        candidate_use.get("semantic_acceptance_candidate_for_selected_cases") is True,
        "ledger is not a semantic acceptance candidate",
    )
    require(
        candidate_use.get("implementation_consumable") is False,
        "ledger improperly authorizes implementation consumption",
    )

    authority_sources = require_mapping(
        ledger.get("authority_sources"), "ledger.authority_sources"
    )
    catalog = require_mapping(ledger.get("condition_catalog"), "ledger.condition_catalog")
    entries = require_list(ledger.get("entries"), "ledger.entries")
    case_ids: set[str] = set()
    used_conditions: set[str] = set()

    for index, raw_entry in enumerate(entries):
        field = f"ledger.entries[{index}]"
        entry = require_mapping(raw_entry, field)
        case_id = require_ascii(require_string(entry.get("case_id"), f"{field}.case_id"), f"{field}.case_id")
        require(case_id not in case_ids, f"duplicate ledger case_id: {case_id}")
        case_ids.add(case_id)
        require(entry.get("actual_review_classes") is None, f"{field} self-claims review classes")
        authority_refs_resolve(entry.get("authority_refs"), f"{field}.authority_refs", authority_sources)

        semantic = require_mapping(entry.get("semantic_expectation"), f"{field}.semantic_expectation")
        context = require_mapping(semantic.get("evaluation_context"), f"{field}.evaluation_context")
        require(
            context.get("evaluation_kind")
            in {"ADOPTER_SNAPSHOT", "ADOPTER_TRANSITION", "CENTRAL_SELF_CHECK"},
            f"{field} has an unsupported evaluation_kind",
        )
        selected = semantic.get("selected_semantic_result")
        require(selected in {"SATISFIED", "BLOCKED"}, f"{field} has invalid selected result")

        required_keys = require_list(
            semantic.get("required_satisfied_condition_keys"),
            f"{field}.required_satisfied_condition_keys",
        )
        local_keys: set[str] = set()
        for key_index, raw_key in enumerate(required_keys):
            key = require_string(raw_key, f"{field}.required_satisfied_condition_keys[{key_index}]")
            require(INTERNAL_CONDITION_RE.fullmatch(key) is not None, f"invalid internal condition key: {key}")
            require(key not in local_keys, f"duplicate condition key in {case_id}: {key}")
            local_keys.add(key)
            used_conditions.add(key)
            catalog_entry = require_mapping(catalog.get(key), f"condition_catalog[{key}]")
            require(
                catalog_entry.get("kind") == "REQUIRED_SATISFIED_CONDITION",
                f"required condition {key} has the wrong catalog kind",
            )

        finding_set = require_mapping(semantic.get("finding_set"), f"{field}.finding_set")
        require(finding_set.get("closed") is True, f"{field} finding_set is not closed")
        findings = require_list(finding_set.get("exact"), f"{field}.finding_set.exact")
        has_block = False
        for finding_index, raw_finding in enumerate(findings):
            finding_field = f"{field}.finding_set.exact[{finding_index}]"
            finding = require_mapping(raw_finding, finding_field)
            require(
                not any(name in finding for name in ("finding_code", "check_id", "reason_code")),
                f"{finding_field} prematurely allocates a public identity",
            )
            key = require_string(finding.get("condition_key"), f"{finding_field}.condition_key")
            require(INTERNAL_CONDITION_RE.fullmatch(key) is not None, f"invalid internal condition key: {key}")
            require(key not in local_keys, f"duplicate condition key in {case_id}: {key}")
            local_keys.add(key)
            used_conditions.add(key)
            effect = finding.get("gate_effect")
            require(effect in {"WARN", "BLOCK"}, f"{finding_field} has invalid gate_effect")
            has_block = has_block or effect == "BLOCK"
            catalog_entry = require_mapping(catalog.get(key), f"condition_catalog[{key}]")
            require(
                catalog_entry.get("kind") == "FINDING_CONDITION",
                f"finding condition {key} has the wrong catalog kind",
            )
        require(
            (selected == "BLOCKED") == has_block,
            f"{field} selected result disagrees with its closed BLOCK finding set",
        )

    require(case_ids == manifest_case_ids, "manifest and ledger case IDs differ")
    require(set(catalog) == used_conditions, "condition_catalog does not exactly close over used keys")
    for key, raw_catalog_entry in catalog.items():
        require(INTERNAL_CONDITION_RE.fullmatch(key) is not None, f"invalid catalog key: {key}")
        catalog_entry = require_mapping(raw_catalog_entry, f"condition_catalog[{key}]")
        require_string(catalog_entry.get("statement"), f"condition_catalog[{key}].statement")
        authority_refs_resolve(
            catalog_entry.get("authority_refs"),
            f"condition_catalog[{key}].authority_refs",
            authority_sources,
        )
    return case_ids, expected_coverage


def validate_decision_path(path: str) -> str:
    path = require_repo_path(path, "--decision-path")
    parent = PurePosixPath(path).parent.as_posix()
    require(parent == DECISION_DIRECTORY, "--decision-path must be directly in the Phase 0 decision directory")
    require(PurePosixPath(path).suffix == ".json", "--decision-path must name a JSON record")
    return path


def verify_release_binding(
    decision: dict[str, Any],
    manifest: dict[str, Any],
    expected_repository: str,
) -> None:
    decision_release = require_mapping(
        decision.get("reference_release_decision"),
        "decision.reference_release_decision",
    )
    manifest_reference = require_mapping(manifest.get("reference"), "manifest.reference")
    require(decision_release.get("repository") == expected_repository, "release decision repository mismatch")
    require(decision_release.get("release") == manifest_reference.get("release"), "release decision version mismatch")
    require(
        decision_release.get("annotated_tag_object_sha1")
        == manifest_reference.get("annotated_tag_object_sha1"),
        "release decision tag-object mismatch",
    )
    require(
        decision_release.get("commit_sha1") == manifest_reference.get("peeled_commit_sha1"),
        "release decision commit mismatch",
    )
    require_string(decision_release.get("release_pr_url"), "decision.reference_release_decision.release_pr_url")
    require_int(
        decision_release.get("pull_request_workflow_run_id"),
        "decision.reference_release_decision.pull_request_workflow_run_id",
        minimum=1,
    )
    classes = require_mapping(
        decision_release.get("recorded_review_classes"),
        "decision.reference_release_decision.recorded_review_classes",
    )
    require(
        classes.get("human") in {"INDEPENDENTLY_REVIEWED", "SOLE_OWNER_ATTESTED"},
        "release decision has an invalid human review class",
    )
    require(
        classes.get("automation") == "AUTOMATION_VERIFIED",
        "release decision has an invalid automation review class",
    )


def scan_for_conflicting_decisions(
    git: GitObjects,
    consumer_base: str,
    selected_path: str,
    selected_id: str,
) -> None:
    records, _ = git.list_regular_tree(
        consumer_base,
        DECISION_DIRECTORY,
        "consumer decision directory",
    )
    # list_regular_tree hashes bytes but intentionally returns relative paths;
    # read JSON records again only when their suffix is .json.
    for record in records:
        relative = record["path"]
        if not relative.endswith(".json"):
            continue
        path = f"{DECISION_DIRECTORY}/{relative}"
        data = git.read_regular_path(consumer_base, path, "consumer decision record")
        candidate = strict_json(data, f"consumer decision record {path}")
        candidate_id = candidate.get("decision_id")
        if path != selected_path and candidate_id == selected_id:
            fail("consumer base contains a duplicate decision_id")
        if candidate.get("supersedes_decision_id") == selected_id:
            fail("selected decision is superseded on the consumer base")


def verify(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root)
    expected_repository = require_string(args.expected_repository, "--expected-repository")
    require(
        REPOSITORY_RE.fullmatch(expected_repository) is not None,
        "--expected-repository must use owner/repository spelling",
    )
    consumer_base = require_sha1(args.consumer_base, "--consumer-base")
    decision_commit = require_sha1(args.decision_commit, "--decision-commit")
    decision_id = require_string(args.decision_id, "--decision-id")
    require(DECISION_ID_RE.fullmatch(decision_id) is not None, "--decision-id has invalid spelling")
    decision_path = validate_decision_path(args.decision_path)

    git = GitObjects(repo_root)
    git.require_commit(consumer_base, "--consumer-base")
    git.require_commit(decision_commit, "--decision-commit")
    require(
        git.first_parent_contains(decision_commit, consumer_base),
        "decision commit is not already on the consumer base first-parent chain",
    )
    require(
        not git.first_parent_decision_records_rewritten(consumer_base),
        "canonical decision JSON history is not append-only",
    )
    decision_parents = git.commit_parents(decision_commit)
    require(len(decision_parents) == 2, "decision commit must be a two-parent merge")
    decision_base = decision_parents[0]
    require(git.path_entry(decision_base, decision_path) is None, "decision path already existed on the acceptance base")
    require(
        not git.first_parent_path_was_used(decision_base, decision_path),
        "decision path was used earlier on the acceptance-base first-parent history",
    )
    require(
        git.added_paths(decision_base, decision_commit) == [("A", decision_path)],
        "acceptance merge must add exactly the one decision record",
    )
    decision_bytes = git.read_regular_path(decision_commit, decision_path, "decision record")
    consumer_decision_bytes = git.read_regular_path(consumer_base, decision_path, "consumer decision record")
    require(decision_bytes == consumer_decision_bytes, "decision record was modified after acceptance")
    decision = strict_json(decision_bytes, "decision record")

    require(
        "accepted" not in decision and "status" not in decision,
        "decision record contains a self-authorization field",
    )
    require(decision.get("document_kind") == "phase0_oracle_decision", "unsupported decision document_kind")
    require(decision.get("format_version") == 1, "unsupported decision format_version")
    require(decision.get("decision_id") == decision_id, "decision_id does not match the explicit selection")
    require(
        decision.get("decision") == "ACCEPT_SEMANTIC_LEDGER_REVISION",
        "only semantic-ledger acceptance is supported",
    )
    require(decision.get("parity_projection") is None, "parity projection is outside this verifier slice")
    require(
        decision.get("implementation_parity_authorized") is False,
        "implementation parity authorization is outside this verifier slice",
    )
    require(decision.get("supersedes_decision_id") is None, "successor decisions are outside this verifier slice")
    require(decision.get("successor_change") is None, "successor changes are outside this verifier slice")

    candidate = require_mapping(decision.get("candidate"), "decision.candidate")
    require(candidate.get("repository") == expected_repository, "candidate repository mismatch")
    candidate_commit = require_sha1(
        candidate.get("repository_commit_sha1"),
        "decision.candidate.repository_commit_sha1",
    )
    candidate_parents = git.commit_parents(candidate_commit)
    require(len(candidate_parents) == 2, "candidate commit must be a two-parent merge")
    require(
        git.first_parent_contains(candidate_commit, decision_base),
        "candidate commit is not earlier on the acceptance-base first-parent chain",
    )
    require(git.path_entry(candidate_commit, decision_path) is None, "candidate commit already contains the decision record")

    manifest_binding = require_mapping(candidate.get("manifest"), "decision.candidate.manifest")
    ledger_binding = require_mapping(candidate.get("ledger"), "decision.candidate.ledger")
    manifest_path = require_repo_path(manifest_binding.get("path"), "decision.candidate.manifest.path")
    ledger_path = require_repo_path(ledger_binding.get("path"), "decision.candidate.ledger.path")
    manifest_parent = PurePosixPath(manifest_path).parent.as_posix()
    require(manifest_parent.startswith(CHARACTERIZATION_DIRECTORY + "/"), "manifest path is outside characterization data")
    require(PurePosixPath(manifest_path).name == MANIFEST_NAME, "candidate manifest path must name manifest.json")
    require(PurePosixPath(ledger_path).parent.as_posix() == manifest_parent, "manifest and ledger must share a directory")
    require(PurePosixPath(ledger_path).name == LEDGER_NAME, "candidate ledger path must name expected-outcomes.json")

    manifest_bytes = git.read_regular_path(candidate_commit, manifest_path, "candidate manifest")
    ledger_bytes = git.read_regular_path(candidate_commit, ledger_path, "candidate ledger")
    manifest_raw_sha = sha256_bytes(manifest_bytes)
    ledger_raw_sha = sha256_bytes(ledger_bytes)
    require(
        manifest_raw_sha
        == require_sha256(manifest_binding.get("raw_sha256"), "decision.candidate.manifest.raw_sha256"),
        "candidate manifest raw SHA-256 mismatch",
    )
    require(
        ledger_raw_sha
        == require_sha256(ledger_binding.get("raw_sha256"), "decision.candidate.ledger.raw_sha256"),
        "candidate ledger raw SHA-256 mismatch",
    )
    manifest = strict_json(manifest_bytes, "candidate manifest")
    ledger = strict_json(ledger_bytes, "candidate ledger")

    corpus_sha, manifest_case_ids = verify_corpus(
        git,
        candidate_commit,
        manifest_parent,
        manifest,
    )
    require(
        corpus_sha
        == require_sha256(candidate.get("corpus_sha256"), "decision.candidate.corpus_sha256"),
        "decision corpus SHA-256 mismatch",
    )
    ledger_case_ids, coverage = verify_ledger(ledger, manifest_raw_sha, manifest_case_ids)

    ledger_revision = require_string(ledger.get("proposed_ledger_revision"), "ledger.proposed_ledger_revision")
    require(decision.get("ledger_revision") == ledger_revision, "decision ledger_revision mismatch")
    ledger_shape_revision = require_string(
        ledger.get("ledger_shape_revision"), "ledger.ledger_shape_revision"
    )
    require(
        decision.get("ledger_shape_revision") == ledger_shape_revision,
        "decision ledger_shape_revision mismatch",
    )
    scope = require_mapping(decision.get("scope"), "decision.scope")
    require(scope.get("coverage") == coverage, "decision coverage does not match the ledger")
    decision_case_ids_raw = require_list(scope.get("case_ids"), "decision.scope.case_ids")
    decision_case_ids: list[str] = []
    for index, value in enumerate(decision_case_ids_raw):
        decision_case_ids.append(
            require_ascii(require_string(value, f"decision.scope.case_ids[{index}]"), f"decision.scope.case_ids[{index}]")
        )
    require(len(decision_case_ids) == len(set(decision_case_ids)), "decision scope has duplicate case IDs")
    require(decision_case_ids == sorted(decision_case_ids, key=lambda value: value.encode("ascii")), "decision scope case IDs must be ASCII-byte sorted")
    require(set(decision_case_ids) == ledger_case_ids, "decision scope case IDs do not match the ledger")

    authority = require_mapping(
        decision.get("decision_authority_revision"),
        "decision.decision_authority_revision",
    )
    require(authority.get("repository") == expected_repository, "decision authority repository mismatch")
    require(
        require_sha1(authority.get("commit_sha1"), "decision.decision_authority_revision.commit_sha1")
        == decision_base,
        "decision authority revision is not the acceptance merge's first parent",
    )
    authority_path = require_repo_path(authority.get("path"), "decision.decision_authority_revision.path")
    require(authority_path == "GOVERNANCE.md", "decision authority path must be GOVERNANCE.md")
    require_string(authority.get("locator"), "decision.decision_authority_revision.locator")
    authority_bytes = git.read_regular_path(decision_base, authority_path, "decision authority revision")
    require(
        sha256_bytes(authority_bytes)
        == require_sha256(authority.get("raw_sha256"), "decision.decision_authority_revision.raw_sha256"),
        "decision authority revision raw SHA-256 mismatch",
    )

    decision_record = require_mapping(decision.get("decision_record"), "decision.decision_record")
    require_string(decision_record.get("pr_url"), "decision.decision_record.pr_url")
    require_string(decision_record.get("governing_body"), "decision.decision_record.governing_body")
    require_string(decision_record.get("decision_maker"), "decision.decision_record.decision_maker")
    require(
        decision_record.get("human_review_class")
        in {"INDEPENDENTLY_REVIEWED", "SOLE_OWNER_ATTESTED"},
        "decision record has an invalid human review class",
    )
    require(
        decision_record.get("automation_review_class") == "AUTOMATION_VERIFIED",
        "decision record has an invalid automation review class",
    )
    verify_release_binding(decision, manifest, expected_repository)
    scan_for_conflicting_decisions(git, consumer_base, decision_path, decision_id)

    return {
        "document_kind": "phase0_acceptance_binding_verification",
        "format_version": 1,
        "public_contract": False,
        "decision_id": decision_id,
        "consumer_base_sha1": consumer_base,
        "decision_commit_sha1": decision_commit,
        "candidate_commit_sha1": candidate_commit,
        "offline_binding": "VERIFIED",
        "effective_acceptance": "NOT_ESTABLISHED",
        "implementation_parity_authorized": False,
        "verified": VERIFIED_CHECKS,
        "unverified_external_predicates": UNVERIFIED_EXTERNAL_PREDICATES,
        "local_observations": {
            "verifier_executable_path": str(Path(__file__).resolve()),
            "git_executable_path": str(git.git_executable),
            "git_version": git.git_version,
            "repository_root": str(git.repository_top_level),
        },
        "unverified_preconditions": UNVERIFIED_PRECONDITIONS,
        "unverified_authority_predicates": UNVERIFIED_AUTHORITY_PREDICATES,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Verify only the offline Git-object bindings of one Phase 0 "
            "semantic-ledger acceptance decision."
        )
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--expected-repository", required=True)
    parser.add_argument("--consumer-base", required=True)
    parser.add_argument("--decision-commit", required=True)
    parser.add_argument("--decision-id", required=True)
    parser.add_argument("--decision-path", required=True)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def emit_success(result: dict[str, Any], output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(result, ensure_ascii=True, sort_keys=True, indent=2))
        return
    print("OFFLINE BINDING VERIFIED; EFFECTIVE ACCEPTANCE NOT ESTABLISHED")
    print(f"decision: {result['decision_id']}")
    print(f"candidate: {result['candidate_commit_sha1']}")
    observations = result["local_observations"]
    print(
        "observed Git: "
        f"{observations['git_executable_path']} ({observations['git_version']})"
    )
    print(f"observed verifier: {observations['verifier_executable_path']}")
    print(f"observed repository root: {observations['repository_root']}")
    print("toolchain and repository-origin preconditions remain unverified")
    print("external authority predicates remain unverified")


def emit_failure(decision_id: str, error: str, output_format: str) -> None:
    if output_format == "json":
        print(
            json.dumps(
                {
                    "document_kind": "phase0_acceptance_binding_verification",
                    "format_version": 1,
                    "public_contract": False,
                    "decision_id": decision_id,
                    "offline_binding": "REJECTED",
                    "effective_acceptance": "NOT_ESTABLISHED",
                    "error": error,
                },
                ensure_ascii=True,
                sort_keys=True,
                indent=2,
            )
        )
        return
    print(f"OFFLINE BINDING REJECTED: {error}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = verify(args)
    except VerificationError as exc:
        emit_failure(args.decision_id, str(exc), args.format)
        return 1
    except Exception as exc:  # Fail closed without exposing a traceback.
        emit_failure(
            args.decision_id,
            f"internal verification failure: {type(exc).__name__}",
            args.format,
        )
        return 1
    emit_success(result, args.format)
    return 0


if __name__ == "__main__":
    sys.exit(main())
