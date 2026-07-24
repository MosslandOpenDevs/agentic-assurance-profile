#!/usr/bin/env python3
"""Verify the offline binding of one diagnostic-catalog acceptance record.

This internal, standard-library-only verifier reads candidate and decision
material exclusively from exact local Git objects.  A successful result means
that the recorded Git topology, artifact bytes, candidate semantics, and
authority-document bytes are bound as recorded.  It does not prove protected
main provenance, GitHub pull-request state, a human decision maker, review
classes, credential custody, or effective acceptance.

The bounded first format supports only the initial Foundation diagnostic
baseline.  It does not authorize implementation parity or runtime consumption,
and it is not a public report or catalog contract.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
from typing import Any
from urllib.parse import urlsplit


sys.dont_write_bytecode = True

SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

from verify_diagnostic_catalog_candidate import (  # noqa: E402
    REVIEW_SCOPE as CANDIDATE_REVIEW_SCOPE,
    VerificationError as CandidateVerificationError,
    VerificationUnavailable as CandidateVerificationUnavailable,
    verify_candidate_bytes,
)


SHA1_RE = re.compile(r"[0-9a-f]{40}\Z")
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
RECORD_ID_RE = re.compile(r"[A-Z0-9][A-Z0-9._-]{2,127}\Z")
REPOSITORY_RE = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")

MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_BLOB_BYTES = 16 * 1024 * 1024
MAX_TREE_BYTES = 64 * 1024 * 1024
MAX_TREE_FILES = 10_000
MAX_JSON_NUMBER_CHARS = 128
MAX_GIT_STDOUT_BYTES = 64 * 1024 * 1024
MAX_GIT_STDERR_BYTES = 1024 * 1024
MAX_DIAGNOSTIC_CHARS = 2_000
MAX_TEXT_FIELD_CHARS = 500
GIT_TIMEOUT_SECONDS = 20

DECISION_DIRECTORY = "docs/evidence/v0.5/diagnostic-catalog/decisions"
CONTRACT_README_PATH = f"{DECISION_DIRECTORY}/README.md"
ACCEPTANCE_VERIFIER_PATH = "scripts/verify_diagnostic_catalog_acceptance.py"
CANDIDATE_VERIFIER_PATH = "scripts/verify_diagnostic_catalog_candidate.py"
ACCEPTANCE_VERIFIER_TEST_PATH = (
    "tests/test_verify_diagnostic_catalog_acceptance.py"
)
CATALOG_PATH = "docs/evidence/v0.5/diagnostic-catalog/catalog-r1.json"
MAPPING_PATH = (
    "docs/evidence/v0.5/diagnostic-catalog/"
    "legacy-v0.4.0-mapping-r1.json"
)
COMPATIBILITY_PATH = (
    "docs/evidence/v0.5/diagnostic-catalog/"
    "compatibility-changes-r1.json"
)
INVENTORY_PATH = (
    "docs/evidence/v0.5/diagnostic-catalog/"
    "normalized-inventory-r1.json"
)
GOVERNANCE_PATH = "GOVERNANCE.md"
ADR_0002_PATH = "docs/adr/v0.5/0002-diagnostic-identities.md"
ADR_0005_PATH = "docs/adr/v0.5/0005-human-review-authority.md"
ADR_0002_ACCEPTANCE_MERGE = "a34f074ab57214d5fe924ba90c00df313cc2acb6"
ADR_0005_ACCEPTANCE_MERGE = "2a08ed7d0edbd0c9463513150d78017f2207f97f"

DOCUMENT_KIND = "diagnostic_catalog_acceptance_decision"
INTERNAL_FORMAT_VERSION = 1
VERIFIER_CONTRACT_ID = "AAP-V05-DIAGNOSTIC-CATALOG-ACCEPTANCE-OFFLINE-V1"
CONTRACT_README_SHA256 = (
    "db9bd46edf3d182ea5b6d379d8605d83c14e618f210a0486550a665e608e2208"
)
INITIAL_RECORD_ID = "AAP-V05-DIAGNOSTICS-ACCEPTANCE-001"
SUBJECT_DECISION_ID = "AAP-V05-DIAGNOSTICS-001"
DECISION_KIND = "ACCEPT_FOUNDATION_DIAGNOSTIC_BASELINE"
CATALOG_ID = "urn:uuid:6d6187ea-521e-4f3e-98d9-cb716877a84b"
CANDIDATE_CANONICAL_MERGE = "c51b8c1cc7cb5fd343a4acf65e0cccc38356a4fe"
CANDIDATE_HEAD = "f4c8f82e7d0bdfe7edd9a364d2e75a4d7af7ec67"
CATALOG_SHA256 = "da541828f462784eeb504af1436e6c689dc7f429814a18c729e2dc48362a0cec"
MAPPING_SHA256 = "281803836ca4034a3cf441c46b6e608434dea9245e5fa18c90e2954deac79100"
COMPATIBILITY_SHA256 = (
    "499a7a571502d0d70289d00f2bf655673da36c73c82bfb9df4c25913b9be0f7b"
)
INVENTORY_SHA256 = "aa3b9a5d30e41b2e78cb9e45c736ec697ccb04393ab6c300b82ce0e796cbc305"
GOVERNANCE_SHA256 = "5bc92e111440f117d4b7c1a801688889d6767217fcafdd4bdf9d0e333d9798a6"
ADR_0002_SHA256 = "1ef92f7affec0e3031abcc7336fe68625db97e6931698e471b523ff44e8ff858"
ADR_0005_SHA256 = "688ad75c79ac0253f4b26685d2c96316e4f1c82be2647157f80f749bfec89564"

EXPECTED_TOP_LEVEL_KEYS = {
    "authority_basis",
    "decision",
    "document_kind",
    "internal_format_version",
    "predecessor",
    "record_id",
    "repository_process",
    "scope",
    "subject",
    "subject_decision_id",
    "successor_change",
    "verifier_contract",
}
FORBIDDEN_RECORD_KEYS = {
    "accepted",
    "automation_review_class",
    "decision_maker",
    "human_review_class",
    "status",
}
EXPECTED_BASELINE_COMPONENTS = [
    "DIAGNOSTIC_IDENTITY_ALLOCATION",
    "V0_4_SEMANTIC_MAPPING",
    "COMPATIBILITY_CHANGE_INTENT",
]
EXPECTED_BOUND_EVIDENCE = ["NORMALIZED_SOURCE_INVENTORY"]

VERIFIED_CHECKS = [
    "decision-preexists-selected-consumer-revision",
    "canonical-first-parent-decision-history-append-only",
    "acceptance-only-tree-diff",
    "verifier-contract-precedes-decision",
    "verifier-contract-artifact-raw-hashes",
    "candidate-precedes-decision",
    "candidate-merge-head-tree-identity",
    "candidate-artifact-raw-hashes",
    "candidate-semantic-closure",
    "governance-revision-bytes",
    "accepted-adr-revision-bytes",
    "negative-authorization-scope",
]
UNVERIFIED_EXTERNAL_PREDICATES = [
    "protected-canonical-main",
    "github-subject-candidate-pr-state",
    "github-verifier-contract-pr-state",
    "github-acceptance-pr-state",
    "factual-human-decision-maker",
    "factual-review-classes",
    "maintainer-eligibility",
    "substantive-authorship",
    "branch-ruleset-codeowners-and-bypass-controls-at-event",
    "github-ci-conclusions",
    "acceptance-merge-provider-provenance",
]
UNVERIFIED_PRECONDITIONS = [
    "consumer-base-role-authority",
    "consuming-change-provider-state",
    "verifier-executable-provenance",
    "candidate-verifier-executable-provenance",
    "git-executable-provenance",
    "local-repository-origin",
    "expected-repository-argument-authority",
]
UNVERIFIED_AUTHORITY_PREDICATES = [
    "governance-locator-semantic-validity",
    "adr-locator-semantic-validity",
    "provider-review-record-validity",
    "credential-and-session-custody",
    "published-release-state",
    "published-workflow-run-state",
]


class VerificationError(Exception):
    """A definite mismatch in the selected offline binding."""


class VerificationUnavailable(VerificationError):
    """The selected binding could not be fully evaluated."""


class SafeArgumentParser(argparse.ArgumentParser):
    """Keep usage failures bounded and terminal-safe."""

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(
            2,
            f"{self.prog}: error: "
            f"{safe_text(message, limit=MAX_DIAGNOSTIC_CHARS)}\n",
        )


def fail(message: str) -> None:
    raise VerificationError(message)


def unavailable(message: str) -> None:
    raise VerificationUnavailable(message)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def require_available(condition: bool, message: str) -> None:
    if not condition:
        unavailable(message)


def bounded_text(value: object, *, limit: int) -> str:
    text = str(value)
    if len(text) > limit:
        return text[:limit] + "..."
    return text


def bounded_diagnostic(value: object) -> str:
    return bounded_text(value, limit=MAX_DIAGNOSTIC_CHARS)


def safe_text(value: object, *, limit: int = MAX_TEXT_FIELD_CHARS) -> str:
    """Render one bounded, single-line, JSON-escaped text field."""

    return json.dumps(
        bounded_text(value, limit=limit),
        ensure_ascii=True,
    )


def observe_local_file_sha256(path: Path) -> str | None:
    """Return a non-authoritative local file observation when safely readable."""

    try:
        resolved = path.resolve(strict=True)
        if not resolved.is_file():
            return None
        with resolved.open("rb") as stream:
            data = stream.read(MAX_BLOB_BYTES + 1)
    except OSError:
        return None
    if len(data) > MAX_BLOB_BYTES:
        return None
    return sha256_bytes(data)


def require_exact_keys(value: dict[str, Any], expected: set[str], field: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        fail(f"{field} key set mismatch (missing={missing}, extra={extra})")


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


def require_ascii(value: str, field: str) -> str:
    try:
        value.encode("ascii")
    except UnicodeEncodeError:
        fail(f"{field} must contain ASCII only")
    return value


def require_no_ascii_controls(value: str, field: str) -> str:
    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in value):
        fail(f"{field} contains an ASCII control character")
    return value


def require_sha1(value: Any, field: str) -> str:
    value = require_string(value, field)
    if SHA1_RE.fullmatch(value) is None:
        fail(f"{field} must be a full lowercase 40-hex SHA-1")
    return value


def require_git_sha1(value: str, field: str) -> str:
    if SHA1_RE.fullmatch(value) is None:
        unavailable(f"{field} is not a full lowercase 40-hex SHA-1")
    return value


def require_sha256(value: Any, field: str) -> str:
    value = require_string(value, field)
    if SHA256_RE.fullmatch(value) is None:
        fail(f"{field} must be a lowercase 64-hex SHA-256")
    return value


def require_repo_path(value: Any, field: str, *, allow_dot: bool = False) -> str:
    value = require_ascii(require_string(value, field), field)
    if allow_dot and value == ".":
        return value
    require_no_ascii_controls(value, field)
    if value.startswith("/") or "\\" in value:
        fail(f"{field} must be a POSIX repository-relative path")
    path = PurePosixPath(value)
    if not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        fail(f"{field} contains a forbidden path component")
    if path.as_posix() != value:
        fail(f"{field} is not in canonical POSIX form")
    return value


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            fail(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_bounded_json_int(token: str) -> int:
    if len(token) > MAX_JSON_NUMBER_CHARS:
        fail("JSON integer token exceeds the bounded number length")
    try:
        return int(token)
    except ValueError as exc:
        raise VerificationError(f"invalid JSON integer: {token}") from exc


def parse_finite_json_float(token: str) -> float:
    if len(token) > MAX_JSON_NUMBER_CHARS:
        fail("JSON float token exceeds the bounded number length")
    try:
        value = float(token)
    except ValueError as exc:
        raise VerificationError(f"invalid JSON number: {token}") from exc
    if not math.isfinite(value):
        fail(f"non-finite JSON number: {token}")
    return value


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
            parse_int=parse_bounded_json_int,
            parse_float=parse_finite_json_float,
            parse_constant=lambda token: (_ for _ in ()).throw(
                VerificationError(f"non-finite JSON value: {token}")
            ),
        )
    except VerificationError:
        raise
    except (json.JSONDecodeError, RecursionError, ValueError) as exc:
        fail(f"{field} is not strict JSON: {exc}")
    return require_mapping(value, field)


def walk_mappings(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_mappings(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_mappings(child)


class GitObjects:
    """Read exact values from an existing local Git object database."""

    def __init__(self, repo_root: Path) -> None:
        try:
            self.repo_root = repo_root.resolve(strict=True)
        except OSError as exc:
            unavailable(f"cannot resolve --repo-root: {exc}")
        require(self.repo_root.is_dir(), "--repo-root must be a directory")

        selected = shutil.which("git")
        require_available(
            selected is not None,
            "cannot resolve a Git executable from PATH",
        )
        try:
            self.git_executable = Path(str(selected)).resolve(strict=True)
        except OSError as exc:
            unavailable(f"cannot resolve the selected Git executable: {exc}")
        require_available(
            self.git_executable.is_file()
            and os.access(self.git_executable, os.X_OK),
            "selected Git executable is not an executable file",
        )

        bare = self._run("rev-parse", "--is-bare-repository").stdout.strip()
        require_available(bare in {b"true", b"false"}, "cannot determine bare state")
        require_available(bare == b"false", "bare repositories are unsupported")
        top_raw = self._run("rev-parse", "--show-toplevel").stdout.rstrip(b"\r\n")
        try:
            top = Path(os.fsdecode(top_raw)).resolve(strict=True)
        except OSError as exc:
            unavailable(f"cannot resolve Git top-level: {exc}")
        require(
            top == self.repo_root,
            "--repo-root must exactly name the repository top-level",
        )

        version = self._run("--version").stdout.strip()
        require_available(
            0 < len(version) <= 200,
            "cannot determine a bounded Git version",
        )
        try:
            self.git_version = version.decode("ascii", "strict")
        except UnicodeDecodeError:
            unavailable("Git version output is not ASCII")

        shallow = self._run(
            "rev-parse",
            "--is-shallow-repository",
        ).stdout.strip()
        require_available(
            shallow in {b"true", b"false"},
            "cannot determine shallow state",
        )
        require_available(
            shallow == b"false",
            "shallow repositories are unsupported",
        )

    def _run(
        self,
        *args: str,
        allowed_returncodes: tuple[int, ...] = (0,),
    ) -> subprocess.CompletedProcess[bytes]:
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
            unavailable(f"local Git object inspection failed: {exc}")
        require_available(
            len(completed.stdout) <= MAX_GIT_STDOUT_BYTES,
            "local Git command exceeded its stdout limit",
        )
        require_available(
            len(completed.stderr) <= MAX_GIT_STDERR_BYTES,
            "local Git command exceeded its stderr limit",
        )
        if completed.returncode not in allowed_returncodes:
            diagnostic = completed.stderr.decode("utf-8", "replace").strip()
            if len(diagnostic) > 500:
                diagnostic = diagnostic[:500] + "..."
            unavailable(
                f"local Git command failed: {diagnostic or 'no diagnostic'}"
            )
        return completed

    def object_type(self, oid: str) -> str:
        require_sha1(oid, "Git object ID")
        try:
            return self._run("cat-file", "-t", oid).stdout.decode(
                "ascii", "strict"
            ).strip()
        except UnicodeDecodeError:
            unavailable("Git object type is not ASCII")

    def require_commit(self, oid: str, field: str) -> None:
        require_sha1(oid, field)
        require(self.object_type(oid) == "commit", f"{field} is not a commit")

    def commit_parents(self, commit: str) -> list[str]:
        self.require_commit(commit, "commit")
        raw = self._run("rev-list", "--parents", "-n", "1", commit).stdout
        try:
            parts = raw.decode("ascii", "strict").strip().split()
        except UnicodeDecodeError:
            unavailable("commit parent list is not ASCII")
        require_available(
            bool(parts) and parts[0] == commit,
            "unexpected rev-list result",
        )
        for parent in parts[1:]:
            require_git_sha1(parent, "commit parent")
        return parts[1:]

    def first_parent_contains(self, ancestor: str, descendant: str) -> bool:
        self.require_commit(ancestor, "first-parent ancestor")
        self.require_commit(descendant, "first-parent descendant")
        output = self._run("rev-list", "--first-parent", descendant).stdout
        try:
            revisions = [
                line.decode("ascii", "strict") for line in output.splitlines()
            ]
        except UnicodeDecodeError:
            unavailable("first-parent revision list is not ASCII")
        require_available(
            bool(revisions),
            "first-parent revision list is empty",
        )
        for revision in revisions:
            require_git_sha1(revision, "first-parent revision")
        return ancestor in revisions

    def first_parent_path_was_used(self, commit: str, path: str) -> bool:
        self.require_commit(commit, "path-history commit")
        path = require_repo_path(path, "path-history Git path")
        output = self._run(
            "rev-list",
            "--first-parent",
            "--full-history",
            "--max-count=1",
            commit,
            "--",
            f":(top,literal){path}",
        ).stdout
        return bool(output.strip())

    def first_parent_path_introduction(
        self,
        commit: str,
        path: str,
    ) -> str | None:
        self.require_commit(commit, "path-introduction commit")
        path = require_repo_path(path, "path-introduction Git path")
        output = self._run(
            "log",
            "--first-parent",
            "--no-renames",
            "--diff-filter=A",
            "--format=%H",
            "--reverse",
            commit,
            "--",
            f":(top,literal){path}",
        ).stdout
        introductions = output.splitlines()
        if not introductions:
            return None
        try:
            revisions = [
                line.decode("ascii", "strict") for line in introductions
            ]
        except UnicodeDecodeError:
            unavailable("path-introduction commit is not ASCII")
        for revision in revisions:
            require_git_sha1(revision, "path-introduction commit")
        return revisions[0]

    def first_parent_decision_records_rewritten(self, commit: str) -> bool:
        self.require_commit(commit, "decision-history commit")
        output = self._run(
            "log",
            "--first-parent",
            "--no-renames",
            "--format=%H",
            "--diff-filter=DMT",
            "--max-count=1",
            commit,
            "--",
            f":(top,glob){DECISION_DIRECTORY}/*.json",
        ).stdout
        return bool(output.strip())

    @staticmethod
    def _parse_ls_tree(
        output: bytes,
        field: str,
    ) -> list[tuple[str, str, str, str]]:
        records: list[tuple[str, str, str, str]] = []
        for raw in output.split(b"\0"):
            if not raw:
                continue
            try:
                metadata, raw_path = raw.split(b"\t", 1)
                mode, object_type, oid = metadata.decode("ascii").split(" ")
                path = raw_path.decode("utf-8")
            except (ValueError, UnicodeDecodeError) as exc:
                unavailable(f"malformed git ls-tree record for {field}: {exc}")
            require_git_sha1(oid, f"{field} object ID")
            records.append((mode, object_type, oid, path))
        return records

    def path_entry(
        self,
        commit: str,
        path: str,
    ) -> tuple[str, str, str, str] | None:
        self.require_commit(commit, "path commit")
        path = require_repo_path(path, "Git path")
        output = self._run(
            "ls-tree",
            "-z",
            "--full-tree",
            commit,
            "--",
            f":(top,literal){path}",
        ).stdout
        entries = self._parse_ls_tree(output, path)
        if not entries:
            return None
        if len(entries) != 1 or entries[0][3] != path:
            unavailable(f"Git path lookup was not exact: {path}")
        return entries[0]

    def read_blob_oid(self, oid: str, field: str) -> bytes:
        require_sha1(oid, f"{field} blob ID")
        require(self.object_type(oid) == "blob", f"{field} is not a blob")
        raw_size = self._run("cat-file", "-s", oid).stdout
        try:
            size = int(raw_size.decode("ascii", "strict").strip())
        except (ValueError, UnicodeDecodeError):
            unavailable(f"cannot read the size of {field}")
        require_available(
            0 <= size <= MAX_BLOB_BYTES,
            f"{field} exceeds the {MAX_BLOB_BYTES}-byte blob limit",
        )
        data = self._run("cat-file", "blob", oid).stdout
        require_available(
            len(data) == size,
            f"{field} blob size changed while reading",
        )
        return data

    def read_regular_path(self, commit: str, path: str, field: str) -> bytes:
        entry = self.path_entry(commit, path)
        if entry is None:
            fail(f"{field} is missing at {commit}: {path}")
        mode, object_type, oid, _ = entry
        require(
            mode == "100644" and object_type == "blob",
            f"{field} must be a regular mode-100644 Git blob",
        )
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
            require(
                entry is not None
                and entry[0] == "040000"
                and entry[1] == "tree",
                f"{field} scope is not a Git tree: {scope}",
            )
            arguments += ["--", f":(top,literal){scope}"]
            prefix = scope + "/"
        entries = self._parse_ls_tree(self._run(*arguments).stdout, field)
        require(entries, f"{field} contains no tracked files")
        require_available(
            len(entries) <= MAX_TREE_FILES,
            f"{field} exceeds the {MAX_TREE_FILES}-file limit",
        )

        result: list[dict[str, Any]] = []
        total_bytes = 0
        seen: set[str] = set()
        for mode, object_type, oid, full_path in entries:
            require(
                mode == "100644" and object_type == "blob",
                f"{field} contains unsupported Git mode/type at {full_path}",
            )
            if prefix:
                require_available(
                    full_path.startswith(prefix),
                    f"{field} returned a path outside its scope",
                )
                relative = full_path[len(prefix) :]
            else:
                relative = full_path
            relative = require_repo_path(relative, f"{field} path")
            require_available(
                relative not in seen,
                f"{field} has duplicate path {relative}",
            )
            seen.add(relative)
            data = self.read_blob_oid(oid, f"{field}:{relative}")
            total_bytes += len(data)
            require_available(
                total_bytes <= MAX_TREE_BYTES,
                f"{field} exceeds the {MAX_TREE_BYTES}-byte tree limit",
            )
            result.append(
                {
                    "path": relative,
                    "size": len(data),
                    "sha256": sha256_bytes(data),
                }
            )
        result.sort(key=lambda item: item["path"].encode("ascii"))
        return result, total_bytes

    def root_tree_oid(self, commit: str) -> str:
        self.require_commit(commit, "root-tree commit")
        body = self._run("cat-file", "-p", commit).stdout
        first_line = body.splitlines()[0] if body else b""
        require_available(
            first_line.startswith(b"tree "),
            "commit has no root tree",
        )
        try:
            oid = first_line[5:].decode("ascii", "strict")
        except UnicodeDecodeError:
            unavailable("commit root-tree ID is not ASCII")
        return require_git_sha1(oid, "commit root-tree ID")

    def added_paths(self, parent: str, commit: str) -> list[tuple[str, str]]:
        output = self._run(
            "diff-tree",
            "--no-commit-id",
            "--no-renames",
            "--name-status",
            "-r",
            "-z",
            parent,
            commit,
            "--",
        ).stdout
        parts = output.split(b"\0")
        if parts and parts[-1] == b"":
            parts.pop()
        require_available(len(parts) % 2 == 0, "malformed diff-tree output")
        result: list[tuple[str, str]] = []
        for index in range(0, len(parts), 2):
            try:
                status = parts[index].decode("ascii", "strict")
                path = parts[index + 1].decode("utf-8", "strict")
            except UnicodeDecodeError as exc:
                unavailable(f"non-textual acceptance diff entry: {exc}")
            result.append(
                (status, require_repo_path(path, "acceptance diff path"))
            )
        return result


def validate_decision_path(path: str) -> str:
    path = require_repo_path(path, "--decision-path")
    require(
        PurePosixPath(path).parent.as_posix() == DECISION_DIRECTORY,
        "--decision-path must be directly in the diagnostic decision directory",
    )
    require(
        PurePosixPath(path).suffix == ".json",
        "--decision-path must name a JSON record",
    )
    return path


def validate_pr_url(value: Any, expected_repository: str) -> str:
    value = require_no_ascii_controls(
        require_ascii(
            require_string(value, "repository_process.pr_url"),
            "repository_process.pr_url",
        ),
        "repository_process.pr_url",
    )
    parsed = urlsplit(value)
    require(
        parsed.scheme == "https"
        and parsed.hostname == "github.com"
        and parsed.port is None
        and parsed.username is None
        and parsed.password is None
        and not parsed.query
        and not parsed.fragment,
        "repository_process.pr_url must be a canonical GitHub pull-request URL",
    )
    expected_prefix = f"/{expected_repository}/pull/"
    require(
        parsed.path.startswith(expected_prefix),
        "repository_process.pr_url repository mismatch",
    )
    number = parsed.path[len(expected_prefix) :]
    require(
        number.isascii()
        and number.isdigit()
        and int(number) >= 1
        and str(int(number)) == number,
        "repository_process.pr_url must end in one canonical positive PR number",
    )
    require(
        value
        == f"https://github.com/{expected_repository}/pull/{number}",
        "repository_process.pr_url must use exact canonical spelling",
    )
    return value


def scan_for_conflicting_records(
    git: GitObjects,
    consumer_base: str,
    selected_path: str,
    selected_record_id: str,
    subject_decision_id: str,
) -> None:
    records, _ = git.list_regular_tree(
        consumer_base,
        DECISION_DIRECTORY,
        "consumer decision directory",
    )
    for record in records:
        relative = record["path"]
        if not relative.endswith(".json"):
            continue
        path = f"{DECISION_DIRECTORY}/{relative}"
        data = git.read_regular_path(
            consumer_base,
            path,
            "consumer decision record",
        )
        candidate = strict_json(data, f"consumer decision record {path}")
        if path != selected_path and candidate.get("record_id") == selected_record_id:
            fail("consumer base contains a duplicate record_id")
        if (
            path != selected_path
            and candidate.get("subject_decision_id") == subject_decision_id
        ):
            fail("consumer base contains a competing subject acceptance record")
        predecessor = candidate.get("predecessor")
        if predecessor == selected_record_id or (
            isinstance(predecessor, dict)
            and predecessor.get("record_id") == selected_record_id
        ):
            fail("selected decision is superseded on the consumer base")


def validate_artifact_binding(
    value: Any,
    field: str,
    *,
    expected_path: str,
    expected_extra: dict[str, Any],
) -> tuple[str, str]:
    binding = require_mapping(value, field)
    expected_keys = {"path", "raw_sha256", *expected_extra}
    require_exact_keys(binding, expected_keys, field)
    path = require_repo_path(binding.get("path"), f"{field}.path")
    require(path == expected_path, f"{field}.path is not the fixed artifact path")
    raw_sha = require_sha256(binding.get("raw_sha256"), f"{field}.raw_sha256")
    for key, expected in expected_extra.items():
        actual = binding.get(key)
        require(
            type(actual) is type(expected) and actual == expected,
            f"{field}.{key} mismatch",
        )
    return path, raw_sha


def validate_record(
    record: dict[str, Any],
    *,
    expected_repository: str,
    selected_record_id: str,
    decision_base: str,
) -> dict[str, Any]:
    require_exact_keys(record, EXPECTED_TOP_LEVEL_KEYS, "decision record")
    for obj in walk_mappings(record):
        present = FORBIDDEN_RECORD_KEYS.intersection(obj)
        require(
            not present,
            f"decision record contains forbidden predeclaration key(s): {sorted(present)}",
        )
    require(record.get("document_kind") == DOCUMENT_KIND, "unsupported document_kind")
    require(
        require_int(
            record.get("internal_format_version"),
            "internal_format_version",
        )
        == INTERNAL_FORMAT_VERSION,
        "unsupported internal_format_version",
    )
    record_id = require_ascii(
        require_string(record.get("record_id"), "record_id"),
        "record_id",
    )
    require(RECORD_ID_RE.fullmatch(record_id) is not None, "invalid record_id")
    require(record_id == selected_record_id, "record_id selection mismatch")
    require(record_id == INITIAL_RECORD_ID, "unsupported initial record_id")
    require(
        record.get("subject_decision_id") == SUBJECT_DECISION_ID,
        "unsupported subject_decision_id",
    )
    require(record.get("decision") == DECISION_KIND, "unsupported decision kind")
    require(record.get("predecessor") is None, "predecessor is outside format v1")
    require(
        record.get("successor_change") is None,
        "successor_change is outside format v1",
    )

    verifier_contract = require_mapping(
        record.get("verifier_contract"),
        "verifier_contract",
    )
    require_exact_keys(
        verifier_contract,
        {
            "artifacts",
            "canonical_merge_commit_sha1",
            "contract_id",
            "repository",
        },
        "verifier_contract",
    )
    require(
        verifier_contract.get("contract_id") == VERIFIER_CONTRACT_ID,
        "verifier_contract.contract_id mismatch",
    )
    require(
        verifier_contract.get("repository") == expected_repository,
        "verifier_contract.repository mismatch",
    )
    verifier_contract_merge = require_sha1(
        verifier_contract.get("canonical_merge_commit_sha1"),
        "verifier_contract.canonical_merge_commit_sha1",
    )
    contract_artifacts = require_list(
        verifier_contract.get("artifacts"),
        "verifier_contract.artifacts",
    )
    expected_contract_artifacts = [
        ("CONTRACT", CONTRACT_README_PATH),
        ("ACCEPTANCE_VERIFIER", ACCEPTANCE_VERIFIER_PATH),
        ("CANDIDATE_SEMANTIC_VERIFIER", CANDIDATE_VERIFIER_PATH),
        ("ACCEPTANCE_VERIFIER_TESTS", ACCEPTANCE_VERIFIER_TEST_PATH),
    ]
    require(
        len(contract_artifacts) == len(expected_contract_artifacts),
        "verifier_contract.artifacts cardinality mismatch",
    )
    validated_contract_artifacts: list[dict[str, str]] = []
    for index, (expected_role, expected_path) in enumerate(
        expected_contract_artifacts
    ):
        field = f"verifier_contract.artifacts[{index}]"
        artifact = require_mapping(contract_artifacts[index], field)
        require_exact_keys(artifact, {"path", "raw_sha256", "role"}, field)
        require(
            artifact.get("role") == expected_role,
            f"{field}.role mismatch",
        )
        path = require_repo_path(artifact.get("path"), f"{field}.path")
        require(path == expected_path, f"{field}.path mismatch")
        raw_sha = require_sha256(
            artifact.get("raw_sha256"),
            f"{field}.raw_sha256",
        )
        if expected_role == "CONTRACT":
            require(
                raw_sha == CONTRACT_README_SHA256,
                f"{field}.raw_sha256 mismatch",
            )
        validated_contract_artifacts.append(
            {
                "path": path,
                "raw_sha256": raw_sha,
                "role": expected_role,
            }
        )

    subject = require_mapping(record.get("subject"), "subject")
    require_exact_keys(
        subject,
        {
            "candidate_canonical_merge_sha1",
            "candidate_head_sha1",
            "catalog",
            "compatibility_changes",
            "legacy_mapping",
            "normalized_inventory",
            "repository",
        },
        "subject",
    )
    require(subject.get("repository") == expected_repository, "subject repository mismatch")
    candidate_merge = require_sha1(
        subject.get("candidate_canonical_merge_sha1"),
        "subject.candidate_canonical_merge_sha1",
    )
    candidate_head = require_sha1(
        subject.get("candidate_head_sha1"),
        "subject.candidate_head_sha1",
    )
    require(
        candidate_merge == CANDIDATE_CANONICAL_MERGE,
        "subject candidate canonical merge mismatch",
    )
    require(candidate_head == CANDIDATE_HEAD, "subject candidate head mismatch")
    catalog_path, catalog_sha = validate_artifact_binding(
        subject.get("catalog"),
        "subject.catalog",
        expected_path=CATALOG_PATH,
        expected_extra={
            "catalog_id": CATALOG_ID,
            "catalog_revision": 1,
        },
    )
    require(catalog_sha == CATALOG_SHA256, "subject.catalog.raw_sha256 mismatch")
    mapping_path, mapping_sha = validate_artifact_binding(
        subject.get("legacy_mapping"),
        "subject.legacy_mapping",
        expected_path=MAPPING_PATH,
        expected_extra={"mapping_revision": 1},
    )
    require(mapping_sha == MAPPING_SHA256, "subject.legacy_mapping.raw_sha256 mismatch")
    compatibility_path, compatibility_sha = validate_artifact_binding(
        subject.get("compatibility_changes"),
        "subject.compatibility_changes",
        expected_path=COMPATIBILITY_PATH,
        expected_extra={},
    )
    require(
        compatibility_sha == COMPATIBILITY_SHA256,
        "subject.compatibility_changes.raw_sha256 mismatch",
    )
    inventory_path, inventory_sha = validate_artifact_binding(
        subject.get("normalized_inventory"),
        "subject.normalized_inventory",
        expected_path=INVENTORY_PATH,
        expected_extra={"role": "BOUND_REVIEW_EVIDENCE"},
    )
    require(
        inventory_sha == INVENTORY_SHA256,
        "subject.normalized_inventory.raw_sha256 mismatch",
    )

    scope = require_mapping(record.get("scope"), "scope")
    require_exact_keys(
        scope,
        {
            "accepted_baseline_components",
            "bound_review_evidence",
            "implementation_parity_authorized",
            "public_contract",
            "runtime_consumption_authorized",
            "runtime_ready",
        },
        "scope",
    )
    require(
        scope.get("accepted_baseline_components") == EXPECTED_BASELINE_COMPONENTS,
        "scope.accepted_baseline_components mismatch",
    )
    require(
        scope.get("bound_review_evidence") == EXPECTED_BOUND_EVIDENCE,
        "scope.bound_review_evidence mismatch",
    )
    require(
        scope.get("implementation_parity_authorized") is False,
        "decision record improperly authorizes implementation parity",
    )
    require(
        scope.get("runtime_consumption_authorized") is False,
        "decision record improperly authorizes runtime consumption",
    )
    require(scope.get("runtime_ready") is False, "decision record claims runtime readiness")
    require(scope.get("public_contract") is False, "decision record claims a public contract")

    authority = require_mapping(record.get("authority_basis"), "authority_basis")
    require_exact_keys(
        authority,
        {"accepted_adrs", "governance"},
        "authority_basis",
    )
    governance = require_mapping(authority.get("governance"), "authority_basis.governance")
    require_exact_keys(
        governance,
        {"commit_sha1", "locator", "path", "raw_sha256", "repository"},
        "authority_basis.governance",
    )
    require(
        governance.get("repository") == expected_repository,
        "governance repository mismatch",
    )
    require(
        require_sha1(
            governance.get("commit_sha1"),
            "authority_basis.governance.commit_sha1",
        )
        == decision_base,
        "governance revision is not the acceptance merge first parent",
    )
    require(
        require_repo_path(
            governance.get("path"),
            "authority_basis.governance.path",
        )
        == GOVERNANCE_PATH,
        "governance path mismatch",
    )
    require(
        governance.get("locator") == "§§1–3",
        "authority_basis.governance.locator mismatch",
    )
    governance_sha = require_sha256(
        governance.get("raw_sha256"),
        "authority_basis.governance.raw_sha256",
    )
    require(
        governance_sha == GOVERNANCE_SHA256,
        "authority_basis.governance.raw_sha256 mismatch",
    )

    accepted_adrs = require_list(authority.get("accepted_adrs"), "authority_basis.accepted_adrs")
    require(len(accepted_adrs) == 2, "authority_basis.accepted_adrs must contain exactly ADR 0002 and ADR 0005")
    expected_adrs = [
        (
            "0002",
            ADR_0002_ACCEPTANCE_MERGE,
            ADR_0002_PATH,
            ADR_0002_SHA256,
        ),
        (
            "0005",
            ADR_0005_ACCEPTANCE_MERGE,
            ADR_0005_PATH,
            ADR_0005_SHA256,
        ),
    ]
    adr_bindings: list[dict[str, str]] = []
    for index, (adr_id, merge_commit, path, expected_sha) in enumerate(expected_adrs):
        field = f"authority_basis.accepted_adrs[{index}]"
        binding = require_mapping(accepted_adrs[index], field)
        require_exact_keys(
            binding,
            {
                "acceptance_merge_commit_sha1",
                "adr_id",
                "locator",
                "path",
                "raw_sha256",
                "repository",
            },
            field,
        )
        require(binding.get("adr_id") == adr_id, f"{field}.adr_id mismatch")
        require(binding.get("repository") == expected_repository, f"{field}.repository mismatch")
        require(
            require_sha1(
                binding.get("acceptance_merge_commit_sha1"),
                f"{field}.acceptance_merge_commit_sha1",
            )
            == merge_commit,
            f"{field}.acceptance merge mismatch",
        )
        require(
            require_repo_path(binding.get("path"), f"{field}.path") == path,
            f"{field}.path mismatch",
        )
        require(binding.get("locator") == "Decision", f"{field}.locator mismatch")
        raw_sha = require_sha256(
            binding.get("raw_sha256"),
            f"{field}.raw_sha256",
        )
        require(raw_sha == expected_sha, f"{field}.raw_sha256 mismatch")
        adr_bindings.append(
            {
                "adr_id": adr_id,
                "commit": merge_commit,
                "path": path,
                "raw_sha256": raw_sha,
            }
        )

    process = require_mapping(record.get("repository_process"), "repository_process")
    require_exact_keys(
        process,
        {
            "acceptance_base_commit_sha1",
            "governing_body",
            "pr_url",
            "review_fact_source",
        },
        "repository_process",
    )
    require(
        require_sha1(
            process.get("acceptance_base_commit_sha1"),
            "repository_process.acceptance_base_commit_sha1",
        )
        == decision_base,
        "repository_process acceptance base mismatch",
    )
    validate_pr_url(process.get("pr_url"), expected_repository)
    require(
        process.get("governing_body") == "MosslandOpenDevs maintainers",
        "repository_process.governing_body mismatch",
    )
    require(
        process.get("review_fact_source") == "DURABLE_ACCEPTANCE_PR_RECORD",
        "repository_process.review_fact_source mismatch",
    )

    return {
        "record_id": record_id,
        "verifier_contract_merge": verifier_contract_merge,
        "verifier_contract_artifacts": validated_contract_artifacts,
        "candidate_merge": candidate_merge,
        "candidate_head": candidate_head,
        "artifacts": {
            "catalog": (catalog_path, catalog_sha),
            "mapping": (mapping_path, mapping_sha),
            "compatibility": (compatibility_path, compatibility_sha),
            "inventory": (inventory_path, inventory_sha),
        },
        "governance_sha256": governance_sha,
        "adr_bindings": adr_bindings,
    }


def verify(args: argparse.Namespace) -> dict[str, Any]:
    expected_repository = require_string(
        args.expected_repository,
        "--expected-repository",
    )
    require(
        REPOSITORY_RE.fullmatch(expected_repository) is not None,
        "--expected-repository must use owner/repository spelling",
    )
    consumer_base = require_sha1(args.consumer_base, "--consumer-base")
    decision_commit = require_sha1(args.decision_commit, "--decision-commit")
    selected_record_id = require_ascii(
        require_string(args.record_id, "--record-id"),
        "--record-id",
    )
    require(
        RECORD_ID_RE.fullmatch(selected_record_id) is not None,
        "--record-id has invalid spelling",
    )
    decision_path = validate_decision_path(args.decision_path)

    git = GitObjects(Path(args.repo_root))
    git.require_commit(consumer_base, "--consumer-base")
    git.require_commit(decision_commit, "--decision-commit")
    require(
        git.first_parent_contains(decision_commit, consumer_base),
        "decision commit is not already on the selected consumer revision's "
        "first-parent chain",
    )
    require(
        not git.first_parent_decision_records_rewritten(consumer_base),
        "canonical diagnostic decision JSON history is not append-only",
    )

    decision_parents = git.commit_parents(decision_commit)
    require(len(decision_parents) == 2, "decision commit must be a two-parent merge")
    decision_base, decision_head = decision_parents
    require(
        git.root_tree_oid(decision_commit) == git.root_tree_oid(decision_head),
        "decision merge tree differs from its reviewed second-parent head",
    )
    require(
        git.path_entry(decision_base, decision_path) is None,
        "decision path already existed on the acceptance base",
    )
    require(
        not git.first_parent_path_was_used(decision_base, decision_path),
        "decision path was used earlier on acceptance-base first-parent history",
    )
    require(
        git.added_paths(decision_base, decision_commit) == [("A", decision_path)],
        "acceptance merge must add exactly the one decision record",
    )

    decision_bytes = git.read_regular_path(
        decision_commit,
        decision_path,
        "decision record",
    )
    consumer_bytes = git.read_regular_path(
        consumer_base,
        decision_path,
        "consumer decision record",
    )
    require(
        decision_bytes == consumer_bytes,
        "decision record was modified after acceptance",
    )
    record = strict_json(decision_bytes, "decision record")
    validated = validate_record(
        record,
        expected_repository=expected_repository,
        selected_record_id=selected_record_id,
        decision_base=decision_base,
    )

    verifier_contract_merge = validated["verifier_contract_merge"]
    git.require_commit(
        verifier_contract_merge,
        "verifier contract canonical merge",
    )
    verifier_contract_parents = git.commit_parents(verifier_contract_merge)
    require(
        len(verifier_contract_parents) == 2,
        "verifier contract canonical merge must be a two-parent merge",
    )
    require(
        git.root_tree_oid(verifier_contract_merge)
        == git.root_tree_oid(verifier_contract_parents[1]),
        "verifier contract merge tree differs from its reviewed second-parent head",
    )
    require(
        git.first_parent_contains(verifier_contract_merge, decision_base),
        "verifier contract merge is not earlier on the acceptance-base first-parent chain",
    )
    require(
        git.first_parent_path_introduction(
            decision_base,
            CONTRACT_README_PATH,
        )
        == verifier_contract_merge,
        "verifier contract merge is not the contract's first canonical first-parent introduction",
    )
    require(
        git.path_entry(verifier_contract_merge, decision_path) is None,
        "verifier contract merge already contains the acceptance record",
    )
    for binding in validated["verifier_contract_artifacts"]:
        data = git.read_regular_path(
            verifier_contract_merge,
            binding["path"],
            f"verifier contract artifact {binding['role']}",
        )
        require(
            sha256_bytes(data) == binding["raw_sha256"],
            f"verifier contract artifact {binding['role']} raw SHA-256 mismatch",
        )

    candidate_merge = validated["candidate_merge"]
    candidate_head = validated["candidate_head"]
    git.require_commit(candidate_merge, "subject canonical merge")
    git.require_commit(candidate_head, "subject candidate head")
    candidate_parents = git.commit_parents(candidate_merge)
    require(
        len(candidate_parents) == 2,
        "subject canonical merge must be a two-parent merge",
    )
    require(
        candidate_parents[1] == candidate_head,
        "subject candidate head is not the canonical merge second parent",
    )
    require(
        git.root_tree_oid(candidate_merge) == git.root_tree_oid(candidate_head),
        "subject canonical merge tree differs from its candidate head",
    )
    require(
        git.first_parent_contains(candidate_merge, decision_base),
        "subject canonical merge is not earlier on the acceptance-base first-parent chain",
    )
    require(
        git.first_parent_contains(candidate_merge, verifier_contract_merge),
        "subject canonical merge is not earlier on the verifier-contract first-parent chain",
    )
    require(
        git.path_entry(candidate_merge, decision_path) is None,
        "subject candidate already contains the acceptance record",
    )

    artifact_bytes: dict[str, bytes] = {}
    for name, raw_binding in validated["artifacts"].items():
        path, expected_sha = raw_binding
        data = git.read_regular_path(
            candidate_merge,
            path,
            f"subject {name} artifact",
        )
        require(
            sha256_bytes(data) == expected_sha,
            f"subject {name} artifact raw SHA-256 mismatch",
        )
        artifact_bytes[name] = data

    try:
        candidate_report = verify_candidate_bytes(
            git.repo_root,
            artifact_bytes["catalog"],
            artifact_bytes["mapping"],
            artifact_bytes["compatibility"],
            artifact_bytes["inventory"],
        )
    except CandidateVerificationUnavailable as exc:
        unavailable(f"subject candidate semantic verification unavailable: {exc}")
    except CandidateVerificationError as exc:
        fail(f"subject candidate semantic verification failed: {exc}")
    require(
        candidate_report.get("status") == "PASS"
        and candidate_report.get("scope") == CANDIDATE_REVIEW_SCOPE,
        "subject candidate semantic verifier did not return its review-only PASS",
    )

    governance_bytes = git.read_regular_path(
        decision_base,
        GOVERNANCE_PATH,
        "governance authority revision",
    )
    require(
        sha256_bytes(governance_bytes) == validated["governance_sha256"],
        "governance authority revision raw SHA-256 mismatch",
    )
    for binding in validated["adr_bindings"]:
        commit = binding["commit"]
        require(
            git.first_parent_contains(commit, decision_base),
            f"accepted ADR {binding['adr_id']} merge is not on the acceptance-base first-parent chain",
        )
        data = git.read_regular_path(
            commit,
            binding["path"],
            f"accepted ADR {binding['adr_id']}",
        )
        require(
            sha256_bytes(data) == binding["raw_sha256"],
            f"accepted ADR {binding['adr_id']} raw SHA-256 mismatch",
        )

    scan_for_conflicting_records(
        git,
        consumer_base,
        decision_path,
        selected_record_id,
        SUBJECT_DECISION_ID,
    )

    bound_acceptance_verifier_sha256 = next(
        binding["raw_sha256"]
        for binding in validated["verifier_contract_artifacts"]
        if binding["role"] == "ACCEPTANCE_VERIFIER"
    )
    running_verifier_sha256 = observe_local_file_sha256(Path(__file__))

    return {
        "document_kind": "diagnostic_catalog_acceptance_binding_verification",
        "internal_format_version": 1,
        "public_contract": False,
        "record_id": selected_record_id,
        "subject_decision_id": SUBJECT_DECISION_ID,
        "consumer_base_sha1": consumer_base,
        "decision_commit_sha1": decision_commit,
        "verifier_contract_commit_sha1": verifier_contract_merge,
        "candidate_commit_sha1": candidate_merge,
        "offline_binding": "VERIFIED",
        "effective_acceptance": "NOT_ESTABLISHED",
        "implementation_parity_authorized": False,
        "runtime_consumption_authorized": False,
        "runtime_ready": False,
        "verified": VERIFIED_CHECKS,
        "candidate_verification": {
            "scope": candidate_report["scope"],
            "catalog_sha256": candidate_report["catalog_sha256"],
            "mapping_sha256": candidate_report["mapping_sha256"],
            "compatibility_changes_sha256": candidate_report[
                "compatibility_changes_sha256"
            ],
            "normalized_inventory_sha256": candidate_report[
                "normalized_inventory_sha256"
            ],
        },
        "unverified_external_predicates": UNVERIFIED_EXTERNAL_PREDICATES,
        "local_observations": {
            "verifier_executable_path": str(Path(__file__).resolve()),
            "bound_acceptance_verifier_raw_sha256": (
                bound_acceptance_verifier_sha256
            ),
            "running_verifier_raw_sha256": running_verifier_sha256,
            "running_verifier_matches_bound_contract": (
                None
                if running_verifier_sha256 is None
                else running_verifier_sha256 == bound_acceptance_verifier_sha256
            ),
            "candidate_verifier_executable_path": str(
                SCRIPT_DIRECTORY / "verify_diagnostic_catalog_candidate.py"
            ),
            "git_executable_path": str(git.git_executable),
            "git_version": git.git_version,
            "repository_root": str(git.repo_root),
        },
        "unverified_preconditions": UNVERIFIED_PRECONDITIONS,
        "unverified_authority_predicates": UNVERIFIED_AUTHORITY_PREDICATES,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(
        prog="verify_diagnostic_catalog_acceptance.py",
        description=(
            "Verify only the offline Git-object binding of one internal "
            "diagnostic-catalog acceptance decision."
        )
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--expected-repository", required=True)
    parser.add_argument("--consumer-base", required=True)
    parser.add_argument("--decision-commit", required=True)
    parser.add_argument("--record-id", required=True)
    parser.add_argument("--decision-path", required=True)
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
    )
    return parser


def emit_success(result: dict[str, Any], output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(result, ensure_ascii=True, sort_keys=True))
        return
    print("OFFLINE CATALOG BINDING VERIFIED; EFFECTIVE ACCEPTANCE NOT ESTABLISHED")
    print(f"record_id: {safe_text(result['record_id'])}")
    print(f"decision_commit: {safe_text(result['decision_commit_sha1'])}")
    print(f"candidate_commit: {safe_text(result['candidate_commit_sha1'])}")
    print("implementation parity authorized: false")
    print("runtime consumption authorized: false")
    print("runtime ready: false")


def emit_failure(
    record_id: str,
    error: str,
    failure_class: str,
    output_format: str,
) -> None:
    safe_record_id = bounded_text(record_id, limit=MAX_TEXT_FIELD_CHARS)
    safe_error = bounded_diagnostic(error)
    result = {
        "document_kind": "diagnostic_catalog_acceptance_binding_verification",
        "internal_format_version": 1,
        "public_contract": False,
        "record_id": safe_record_id,
        "offline_binding": "NOT_VERIFIED",
        "failure_class": failure_class,
        "effective_acceptance": "NOT_ESTABLISHED",
        "implementation_parity_authorized": False,
        "runtime_consumption_authorized": False,
        "runtime_ready": False,
        "error": safe_error,
    }
    if output_format == "json":
        print(json.dumps(result, ensure_ascii=True, sort_keys=True))
        return
    if failure_class == "BINDING_MISMATCH":
        headline = "OFFLINE CATALOG BINDING MISMATCH"
    else:
        headline = "OFFLINE CATALOG BINDING EVALUATION UNDETERMINED"
    print(f"{headline}; EFFECTIVE ACCEPTANCE NOT ESTABLISHED")
    print(f"failure_class: {safe_text(failure_class)}")
    print(f"record_id: {safe_text(safe_record_id)}")
    print(f"error: {safe_text(safe_error, limit=MAX_DIAGNOSTIC_CHARS)}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = verify(args)
    except VerificationUnavailable as exc:
        emit_failure(
            args.record_id,
            str(exc),
            "ACQUISITION_UNAVAILABLE",
            args.format,
        )
        return 3
    except VerificationError as exc:
        emit_failure(
            args.record_id,
            str(exc),
            "BINDING_MISMATCH",
            args.format,
        )
        return 1
    except Exception:
        emit_failure(
            args.record_id,
            "unexpected internal verification failure",
            "INTERNAL_FAILURE",
            args.format,
        )
        return 3
    emit_success(result, args.format)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
