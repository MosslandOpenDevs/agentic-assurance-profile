#!/usr/bin/env python3
"""Reproduce the review-only checks for the v0.5 diagnostic candidate.

This standard-library-only verifier inspects exact local Git objects and the
two proposed decision-data files.  It does not accept a catalog, authorize
runtime consumption, verify a human reviewer, or prove GitHub state.  A pass
means only that the review candidate is internally closed against the exact
v0.4 source bytes recorded by the candidate.

The verifier never fetches, checks out, imports the legacy validator, or
executes workflow content.  Python source is inspected with :mod:`ast`, and the
small GitHub Actions YAML subset used by the two bound workflows is parsed by a
bounded indentation scanner.
"""

from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
from typing import Any, Iterable, Iterator


REVIEW_SCOPE = "REVIEW_ONLY_NOT_RUNTIME_OR_ACCEPTANCE"
DEFAULT_CATALOG = "docs/evidence/v0.5/diagnostic-catalog/catalog-r1.json"
DEFAULT_MAPPING = (
    "docs/evidence/v0.5/diagnostic-catalog/legacy-v0.4.0-mapping-r1.json"
)
DEFAULT_INVENTORY = (
    "docs/evidence/v0.5/diagnostic-catalog/normalized-inventory-r1.json"
)
DEFAULT_COMPATIBILITY_CHANGES = (
    "docs/evidence/v0.5/diagnostic-catalog/compatibility-changes-r1.json"
)

MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_SOURCE_BYTES = 16 * 1024 * 1024
MAX_WORKFLOW_LINES = 20_000
MAX_LINE_BYTES = 256 * 1024
MAX_JSON_NUMBER_CHARS = 128
GIT_TIMEOUT_SECONDS = 20

SHA1_RE = re.compile(r"[0-9a-f]{40}\Z")
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
FINDING_RE = re.compile(r"F[0-9]{4}\Z")
CHECK_RE = re.compile(
    r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*(?:\.[a-z][a-z0-9]*(?:-[a-z0-9]+)*)+\Z"
)
REASON_RE = re.compile(r"[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*\Z")
SOURCE_ID_RE = re.compile(r"[a-z0-9][a-z0-9.-]{0,95}\Z")
WORKFLOW_JOB_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*\Z")

EXPECTED_DIRECT_EMITTERS = 243
EXPECTED_DIRECT_EMITTER_FUNCTIONS = 41
EXPECTED_REPORT_EMIT_RETURNS = 30
EXPECTED_REPORT_RESULTS_READS = 8
EXPECTED_PRELIMINARY_UPSTREAM_PRODUCERS = 77
EXPECTED_SUPPLEMENTAL_UPSTREAM_PRODUCERS = 7
EXPECTED_TOTAL_UPSTREAM_PRODUCERS = 84

PRELIMINARY_RETURN_FUNCTIONS = {
    "load_yaml_with_loader",
    "load_json",
    "read_changed_files",
    "policy_path_mapping_contract_error",
}
PRELIMINARY_APPEND_FUNCTIONS = {
    "adoption_policy_regressions": ("findings", "append", "regression_append"),
    "policy_path_target_regressions": (
        "findings",
        "append",
        "regression_append",
    ),
    "register_policy_regressions": (
        "findings",
        "append",
        "regression_append",
    ),
    "schema_errors": ("messages", "append", "schema_message"),
}


class VerificationError(Exception):
    """A controlled, fail-closed candidate verification error."""


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


def require_bool(value: Any, field: str) -> bool:
    if type(value) is not bool:
        fail(f"{field} must be a boolean")
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


def require_repo_path(value: Any, field: str) -> str:
    value = require_string(value, field)
    try:
        value.encode("ascii")
    except UnicodeEncodeError:
        fail(f"{field} must contain ASCII only")
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


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def review_json_bytes(value: Any) -> bytes:
    """Return the deterministic, ordinary review-evidence JSON spelling."""

    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            fail(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_bounded_json_int(token: str) -> int:
    """Reject integer tokens outside the bounded review-data number subset."""

    if len(token) > MAX_JSON_NUMBER_CHARS:
        fail("JSON integer token exceeds the bounded number length")
    try:
        return int(token)
    except ValueError as exc:
        raise VerificationError(f"invalid JSON integer: {token}") from exc


def parse_finite_json_float(token: str) -> float:
    """Reject JSON exponents that overflow Python's finite float domain."""

    if len(token) > MAX_JSON_NUMBER_CHARS:
        fail("JSON float token exceeds the bounded number length")
    try:
        value = float(token)
    except ValueError as exc:
        raise VerificationError(f"invalid JSON number: {token}") from exc
    if not math.isfinite(value):
        fail(f"non-finite JSON number: {token}")
    return value


def strict_json_bytes(data: bytes, field: str) -> dict[str, Any]:
    if len(data) > MAX_JSON_BYTES:
        fail(f"{field} exceeds the {MAX_JSON_BYTES}-byte limit")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        fail(f"{field} is not UTF-8: {exc}")
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


def read_regular_file(path: Path, field: str) -> bytes:
    try:
        metadata = path.lstat()
    except OSError as exc:
        fail(f"cannot inspect {field}: {exc}")
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        fail(f"{field} must be a regular non-symlink file")
    if metadata.st_size > MAX_JSON_BYTES:
        fail(f"{field} exceeds the {MAX_JSON_BYTES}-byte limit")
    try:
        return path.read_bytes()
    except OSError as exc:
        fail(f"cannot read {field}: {exc}")


class GitObjects:
    """Read exact objects from an existing, non-shallow local repository."""

    def __init__(self, repo_root: Path) -> None:
        try:
            self.repo_root = repo_root.resolve(strict=True)
        except OSError as exc:
            fail(f"cannot resolve --repo-root: {exc}")
        require(self.repo_root.is_dir(), "--repo-root must be a directory")
        selected = shutil.which("git")
        require(selected is not None, "cannot resolve git from PATH")
        try:
            self.git = Path(str(selected)).resolve(strict=True)
        except OSError as exc:
            fail(f"cannot resolve git executable: {exc}")
        require(self.git.is_file(), "selected git executable is not a file")
        top = self._run("rev-parse", "--show-toplevel").stdout.rstrip(b"\r\n")
        try:
            resolved_top = Path(os.fsdecode(top)).resolve(strict=True)
        except OSError as exc:
            fail(f"cannot resolve Git top-level: {exc}")
        require(
            resolved_top == self.repo_root,
            "--repo-root must exactly name the repository top-level",
        )
        shallow = self._run("rev-parse", "--is-shallow-repository").stdout.strip()
        require(shallow == b"false", "shallow repositories are unsupported")

    def _run(self, *args: str) -> subprocess.CompletedProcess[bytes]:
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
                "GIT_OPTIONAL_LOCKS": "0",
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_SYSTEM": os.devnull,
                "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_TERMINAL_PROMPT": "0",
            }
        )
        try:
            completed = subprocess.run(
                [
                    str(self.git),
                    "--no-replace-objects",
                    "-C",
                    str(self.repo_root),
                    *args,
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=GIT_TIMEOUT_SECONDS,
                check=False,
                env=environment,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            fail(f"local Git object inspection failed: {exc}")
        if completed.returncode != 0:
            diagnostic = completed.stderr.decode("utf-8", "replace").strip()
            if len(diagnostic) > 500:
                diagnostic = diagnostic[:500] + "..."
            fail(f"local Git command failed: {diagnostic or 'no diagnostic'}")
        return completed

    def object_type(self, oid: str) -> str:
        require_sha1(oid, "Git object ID")
        try:
            return self._run("cat-file", "-t", oid).stdout.decode(
                "ascii", "strict"
            ).strip()
        except UnicodeDecodeError:
            fail("Git object type is not ASCII")

    def object_size(self, oid: str, field: str) -> int:
        require_sha1(oid, f"{field}.object_id")
        raw = self._run("cat-file", "-s", oid).stdout.strip()
        try:
            value = int(raw.decode("ascii", "strict"))
        except (UnicodeDecodeError, ValueError):
            fail(f"{field} object size is not a non-negative ASCII integer")
        require(value >= 0, f"{field} object size is negative")
        return value

    def require_commit(self, oid: str, field: str) -> None:
        require_sha1(oid, field)
        require(self.object_type(oid) == "commit", f"{field} is not a commit")

    def blob(self, revision: str, path: str, field: str) -> bytes:
        self.require_commit(revision, f"{field}.revision")
        require_repo_path(path, f"{field}.path")
        blob_oid = self.ref_oid(f"{revision}:{path}")
        require(self.object_type(blob_oid) == "blob", f"{field} is not a blob")
        require(
            self.object_size(blob_oid, field) <= MAX_SOURCE_BYTES,
            f"{field} blob is too large",
        )
        data = self._run("cat-file", "blob", blob_oid).stdout
        require(len(data) <= MAX_SOURCE_BYTES, f"{field} blob exceeded its preflight size")
        return data

    def ref_oid(self, ref: str) -> str:
        raw = self._run("rev-parse", "--verify", ref).stdout.strip()
        try:
            value = raw.decode("ascii", "strict")
        except UnicodeDecodeError:
            fail(f"Git ref {ref!r} did not resolve to ASCII")
        return require_sha1(value, f"Git ref {ref}")

    def peeled_commit(self, oid: str) -> str:
        raw = self._run("rev-parse", "--verify", f"{oid}^{{commit}}").stdout.strip()
        try:
            value = raw.decode("ascii", "strict")
        except UnicodeDecodeError:
            fail("peeled commit is not ASCII")
        return require_sha1(value, "peeled commit")

    def tag_bytes(self, oid: str) -> bytes:
        require(self.object_type(oid) == "tag", "bound release object is not a tag")
        require(
            self.object_size(oid, "annotated tag") <= 1024 * 1024,
            "annotated tag object is too large",
        )
        data = self._run("cat-file", "tag", oid).stdout
        require(
            len(data) <= 1024 * 1024,
            "annotated tag object exceeded its preflight size",
        )
        return data


def find_enclosing_function(
    node: ast.AST, parents: dict[ast.AST, ast.AST]
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    current = node
    while current in parents:
        current = parents[current]
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return current
    return None


def enclosing_function(
    node: ast.AST, parents: dict[ast.AST, ast.AST]
) -> ast.FunctionDef | ast.AsyncFunctionDef:
    function = find_enclosing_function(node, parents)
    if function is not None:
        return function
    fail(f"source node at line {getattr(node, 'lineno', '?')} is outside a function")


def is_named_attribute(
    node: ast.AST, receiver: str, attribute: str
) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == receiver
        and node.attr == attribute
    )


def analyze_validator(source: bytes) -> dict[str, Any]:
    try:
        text = source.decode("utf-8")
    except UnicodeDecodeError as exc:
        fail(f"bound scripts/validate.py is not UTF-8: {exc}")
    try:
        tree = ast.parse(text, filename="scripts/validate.py")
    except (SyntaxError, ValueError, RecursionError) as exc:
        fail(f"cannot parse bound scripts/validate.py: {exc}")

    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent

    emitters: list[dict[str, Any]] = []
    emit_returns: list[int] = []
    result_reads: list[int] = []
    preliminary: list[dict[str, Any]] = []
    supplemental: list[dict[str, Any]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and is_named_attribute(
            node.func, "report", node.func.attr if isinstance(node.func, ast.Attribute) else ""
        ) and isinstance(node.func, ast.Attribute) and node.func.attr in {
            "error",
            "warn",
            "ok",
        }:
            function = enclosing_function(node, parents)
            emitters.append(
                {
                    "line": node.lineno,
                    "end_line": node.end_lineno,
                    "kind": node.func.attr,
                    "function": function.name,
                    "function_line": function.lineno,
                    "function_end_line": function.end_lineno,
                }
            )

        if (
            isinstance(node, ast.Return)
            and isinstance(node.value, ast.Call)
            and is_named_attribute(node.value.func, "report", "emit")
        ):
            emit_returns.append(node.lineno)

        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.ctx, ast.Load)
            and is_named_attribute(node, "report", "results")
        ):
            result_reads.append(node.lineno)

        if isinstance(node, ast.Return):
            function = find_enclosing_function(node, parents)
            if function is not None and function.name in PRELIMINARY_RETURN_FUNCTIONS:
                preliminary.append(
                    {
                        "line": node.lineno,
                        "end_line": node.end_lineno,
                        "kind": "return",
                        "function": function.name,
                    }
                )
            if function is not None and function.name == "read_version_file":
                value = node.value
                if (
                    isinstance(value, ast.Tuple)
                    and value.elts
                    and isinstance(value.elts[0], ast.Constant)
                    and value.elts[0].value is None
                ):
                    supplemental.append(
                        {
                            "line": node.lineno,
                            "end_line": node.end_lineno,
                            "kind": "version_error_return",
                            "function": function.name,
                        }
                    )

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            function = find_enclosing_function(node, parents)
            expected = (
                PRELIMINARY_APPEND_FUNCTIONS.get(function.name)
                if function is not None
                else None
            )
            if expected and is_named_attribute(node.func, expected[0], expected[1]):
                preliminary.append(
                    {
                        "line": node.lineno,
                        "end_line": node.end_lineno,
                        "kind": expected[2],
                        "function": function.name,
                    }
                )

        if isinstance(node, ast.ListComp):
            function = find_enclosing_function(node, parents)
            parent = parents.get(node)
            if (
                function is not None
                and function.name == "schema_errors"
                and isinstance(parent, (ast.Assign, ast.AnnAssign))
                and node.elt.lineno == node.lineno + 1
            ):
                supplemental.append(
                    {
                        "line": node.elt.lineno,
                        "end_line": node.elt.end_lineno,
                        "kind": "schema_comprehension_item",
                        "function": function.name,
                    }
                )

        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            function = find_enclosing_function(node, parents)
            if function is not None and function.name == "leading_pr_directives":
                targets: list[ast.expr]
                if isinstance(node, ast.Assign):
                    targets = node.targets
                else:
                    targets = [node.target]
                names = {
                    target.id for target in targets if isinstance(target, ast.Name)
                }
                if "order_invalid" in names and isinstance(
                    node.value, ast.Constant
                ) and node.value.value is True:
                    supplemental.append(
                        {
                            "line": node.lineno,
                            "end_line": node.end_lineno,
                            "kind": "directive_invalid_assignment",
                            "function": function.name,
                        }
                    )
                if "impact_ambiguous" in names:
                    supplemental.append(
                        {
                            "line": node.lineno,
                            "end_line": node.end_lineno,
                            "kind": "directive_ambiguity_assignment",
                            "function": function.name,
                        }
                    )

    emitters.sort(key=lambda item: int(item["line"]))
    preliminary.sort(key=lambda item: int(item["line"]))
    supplemental.sort(key=lambda item: int(item["line"]))
    emit_returns.sort()
    result_reads.sort()

    require(
        len(emitters) == EXPECTED_DIRECT_EMITTERS,
        f"AST derived {len(emitters)} direct emitters, expected {EXPECTED_DIRECT_EMITTERS}",
    )
    function_count = len(
        {
            (item["function"], item["function_line"], item["function_end_line"])
            for item in emitters
        }
    )
    require(
        function_count == EXPECTED_DIRECT_EMITTER_FUNCTIONS,
        f"AST derived {function_count} direct-emitter functions, expected "
        f"{EXPECTED_DIRECT_EMITTER_FUNCTIONS}",
    )
    levels = Counter(str(item["kind"]) for item in emitters)
    require(
        levels == Counter({"error": 195, "warn": 16, "ok": 32}),
        f"unexpected direct-emitter level counts: {dict(levels)}",
    )
    require(
        len(emit_returns) == EXPECTED_REPORT_EMIT_RETURNS,
        "unexpected number of return report.emit() paths",
    )
    require(
        len(result_reads) == EXPECTED_REPORT_RESULTS_READS,
        "unexpected number of report.results reads",
    )
    require(
        len(preliminary) == EXPECTED_PRELIMINARY_UPSTREAM_PRODUCERS,
        f"AST derived {len(preliminary)} preliminary upstream producers, expected "
        f"{EXPECTED_PRELIMINARY_UPSTREAM_PRODUCERS}",
    )
    require(
        len(supplemental) == EXPECTED_SUPPLEMENTAL_UPSTREAM_PRODUCERS,
        f"AST derived {len(supplemental)} supplemental upstream producers, expected "
        f"{EXPECTED_SUPPLEMENTAL_UPSTREAM_PRODUCERS}",
    )
    preliminary_lines = [int(item["line"]) for item in preliminary]
    supplemental_lines = [int(item["line"]) for item in supplemental]
    require(
        len(set(preliminary_lines + supplemental_lines))
        == EXPECTED_TOTAL_UPSTREAM_PRODUCERS,
        "upstream producer derivation contains duplicate physical lines",
    )

    normalized = {
        "direct_emitters": emitters,
        "preliminary_upstream_producers": preliminary,
        "supplemental_upstream_producers": supplemental,
        "report_emit_return_lines": emit_returns,
        "report_results_read_lines": result_reads,
    }
    return {
        **normalized,
        "direct_emitter_function_count": function_count,
        "direct_emitter_levels": dict(sorted(levels.items())),
        "normalized_inventory_sha256": sha256_bytes(
            canonical_json_bytes(normalized)
        ),
    }


def indentation(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def plain_yaml_scalar(raw: str, field: str) -> str:
    value = raw.strip()
    require(value != "", f"{field} must not be empty")
    # The reviewed workflows use comments only after an ASCII space.  Refuse
    # YAML features rather than guessing at them.
    if " #" in value:
        value = value.split(" #", 1)[0].rstrip()
    if value.startswith('"'):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            fail(f"unsupported quoted YAML scalar in {field}: {exc}")
        return require_string(parsed, field, nonempty=False)
    if value.startswith("'"):
        require(value.endswith("'"), f"unterminated YAML scalar in {field}")
        return value[1:-1].replace("''", "'")
    require(not value.startswith(("[", "{", "&", "*", "!")), f"unsupported YAML scalar in {field}")
    return value


def split_yaml_key(line: str, expected_indent: int, field: str) -> tuple[str, str]:
    require(indentation(line) == expected_indent, f"unexpected indentation in {field}")
    body = line[expected_indent:]
    require(":" in body, f"missing ':' in {field}")
    key, raw = body.split(":", 1)
    key = key.strip()
    require(key != "", f"empty YAML key in {field}")
    return key, raw


def parse_block_scalar(
    lines: list[str], start: int, parent_indent: int, indicator: str, field: str
) -> tuple[str, int]:
    require(indicator in {"|", "|-", "|+"}, f"unsupported block scalar in {field}")
    end = start
    collected: list[str] = []
    while end < len(lines):
        line = lines[end]
        if line.strip() and indentation(line) <= parent_indent:
            break
        collected.append(line)
        end += 1
    nonblank_indents = [indentation(line) for line in collected if line.strip()]
    require(nonblank_indents, f"empty block scalar in {field}")
    content_indent = min(nonblank_indents)
    require(content_indent > parent_indent, f"invalid block indentation in {field}")
    decoded = [
        line[content_indent:] if line.strip() else "" for line in collected
    ]
    while decoded and decoded[-1] == "":
        decoded.pop()
    value = "\n".join(decoded)
    if indicator in {"|", "|+"}:
        value += "\n"
    return value, end


def parse_workflow(source: bytes, path: str) -> dict[str, Any]:
    require(len(source) <= MAX_SOURCE_BYTES, f"workflow {path} is too large")
    try:
        text = source.decode("utf-8")
    except UnicodeDecodeError as exc:
        fail(f"workflow {path} is not UTF-8: {exc}")
    require("\x00" not in text, f"workflow {path} contains NUL")
    lines = text.splitlines()
    require(len(lines) <= MAX_WORKFLOW_LINES, f"workflow {path} has too many lines")
    for number, line in enumerate(lines, 1):
        require("\t" not in line, f"workflow {path}:{number} contains a tab")
        require(
            len(line.encode("utf-8")) <= MAX_LINE_BYTES,
            f"workflow {path}:{number} is too long",
        )
    try:
        jobs_start = next(
            index for index, line in enumerate(lines) if line == "jobs:"
        )
    except StopIteration:
        fail(f"workflow {path} has no exact top-level jobs mapping")

    job_starts: list[tuple[str, int]] = []
    for index in range(jobs_start + 1, len(lines)):
        line = lines[index]
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if indentation(line) == 0:
            break
        if indentation(line) == 2:
            key, raw = split_yaml_key(line, 2, f"{path}:{index + 1}")
            require(raw.strip() == "", f"workflow job {key!r} must be a mapping")
            require(WORKFLOW_JOB_RE.fullmatch(key) is not None, f"invalid workflow job ID {key!r}")
            job_starts.append((key, index))
    require(job_starts, f"workflow {path} has no jobs")

    jobs: list[dict[str, Any]] = []
    for ordinal, (job_id, start) in enumerate(job_starts):
        end = job_starts[ordinal + 1][1] if ordinal + 1 < len(job_starts) else len(lines)
        for index in range(start + 1, end):
            if lines[index].strip() and indentation(lines[index]) == 0:
                end = index
                break

        needs: str | None = None
        job_if: str | None = None
        continue_on_error = False
        outputs: list[dict[str, str]] = []
        steps_line: int | None = None
        index = start + 1
        while index < end:
            line = lines[index]
            if not line.strip() or line.lstrip().startswith("#"):
                index += 1
                continue
            if indentation(line) != 4:
                index += 1
                continue
            key, raw = split_yaml_key(line, 4, f"{path}:{index + 1}")
            if key == "needs":
                needs = plain_yaml_scalar(raw, f"{path}:{index + 1} needs")
            elif key == "if":
                job_if = plain_yaml_scalar(raw, f"{path}:{index + 1} if")
            elif key == "continue-on-error":
                value = plain_yaml_scalar(raw, f"{path}:{index + 1} continue-on-error")
                require(value in {"true", "false"}, "continue-on-error must be boolean")
                continue_on_error = value == "true"
            elif key == "outputs":
                output_index = index + 1
                while output_index < end:
                    output_line = lines[output_index]
                    if not output_line.strip() or output_line.lstrip().startswith("#"):
                        output_index += 1
                        continue
                    if indentation(output_line) <= 4:
                        break
                    require(indentation(output_line) == 6, f"unsupported output mapping at {path}:{output_index + 1}")
                    output_name, output_raw = split_yaml_key(
                        output_line, 6, f"{path}:{output_index + 1}"
                    )
                    outputs.append(
                        {
                            "name": output_name,
                            "expression": plain_yaml_scalar(
                                output_raw, f"{path}:{output_index + 1} output"
                            ),
                        }
                    )
                    output_index += 1
            elif key == "steps":
                require(raw.strip() == "", f"steps in {job_id} must be a sequence")
                steps_line = index
            index += 1
        require(steps_line is not None, f"workflow job {path}:{job_id} has no steps")

        step_starts: list[int] = []
        index = int(steps_line) + 1
        while index < end:
            line = lines[index]
            if not line.strip() or line.lstrip().startswith("#"):
                index += 1
                continue
            if indentation(line) <= 4:
                break
            if indentation(line) == 6 and line[6:].startswith("- "):
                step_starts.append(index)
            index += 1
        require(step_starts, f"workflow job {path}:{job_id} has no step entries")

        steps: list[dict[str, Any]] = []
        for step_ordinal, step_start in enumerate(step_starts, 1):
            step_end = (
                step_starts[step_ordinal]
                if step_ordinal < len(step_starts)
                else end
            )
            first_body = lines[step_start][8:]
            require(":" in first_body, f"malformed step at {path}:{step_start + 1}")
            first_key, first_raw = first_body.split(":", 1)
            fields: dict[str, Any] = {}
            fields[first_key.strip()] = (first_raw, step_start)
            index = step_start + 1
            while index < step_end:
                line = lines[index]
                if not line.strip() or line.lstrip().startswith("#"):
                    index += 1
                    continue
                if indentation(line) != 8:
                    index += 1
                    continue
                key, raw = split_yaml_key(line, 8, f"{path}:{index + 1}")
                require(key not in fields, f"duplicate step field {key!r} at {path}:{index + 1}")
                fields[key] = (raw, index)
                index += 1

            def optional_scalar(key: str) -> str | None:
                if key not in fields:
                    return None
                raw_value, source_index = fields[key]
                return plain_yaml_scalar(raw_value, f"{path}:{source_index + 1} {key}")

            name = optional_scalar("name")
            require(name is not None, f"step {path}:{job_id}:{step_ordinal} has no name")
            step_id = optional_scalar("id")
            step_if = optional_scalar("if")
            step_continue = False
            if "continue-on-error" in fields:
                value = optional_scalar("continue-on-error")
                require(value in {"true", "false"}, "step continue-on-error must be boolean")
                step_continue = value == "true"
            uses = optional_scalar("uses")
            run_value: str | None = None
            if "run" in fields:
                raw_run, run_index = fields["run"]
                indicator = raw_run.strip()
                if indicator.startswith("|"):
                    run_value, _ = parse_block_scalar(
                        lines,
                        run_index + 1,
                        8,
                        indicator,
                        f"{path}:{run_index + 1} run",
                    )
                else:
                    run_value = plain_yaml_scalar(
                        raw_run, f"{path}:{run_index + 1} run"
                    )
            require(
                (uses is None) != (run_value is None),
                f"step {path}:{job_id}:{step_ordinal} must have exactly one uses/run",
            )
            if uses is not None:
                execution = {"kind": "USES", "reference": uses}
            else:
                execution = {
                    "kind": "RUN",
                    "shell": optional_scalar("shell"),
                    "run_sha256": sha256_bytes(str(run_value).encode("utf-8")),
                }
            steps.append(
                {
                    "ordinal": step_ordinal,
                    "name": name,
                    "id": step_id,
                    "if": step_if,
                    "continue_on_error": step_continue,
                    "execution": execution,
                }
            )

        jobs.append(
            {
                "job_id": job_id,
                "needs": needs,
                "if": job_if,
                "continue_on_error": continue_on_error,
                "outputs": outputs,
                "steps": steps,
            }
        )

    return {
        "path": path,
        "raw_sha256": sha256_bytes(source),
        "job_count": len(jobs),
        "step_count": sum(len(job["steps"]) for job in jobs),
        "jobs": jobs,
    }


def require_unique_strings(values: Any, field: str) -> list[str]:
    result = [
        require_string(value, f"{field}[]") for value in require_list(values, field)
    ]
    require(len(result) == len(set(result)), f"{field} contains duplicates")
    return result


def walk_objects(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_objects(child)


def validate_candidate_lifecycle(value: Any, field: str) -> None:
    lifecycle = require_mapping(value, field)
    require(lifecycle.get("acceptance_binding") is None, f"{field}.acceptance_binding must be null")
    for key in (
        "implementation_consumption_allowed",
        "implementation_parity_authorized",
        "runtime_ready",
    ):
        require(lifecycle.get(key) is False, f"{field}.{key} must be false")
    require(
        lifecycle.get("effective_only_after_external_exact_byte_acceptance") is True,
        f"{field} must require external exact-byte acceptance",
    )
    require(
        lifecycle.get("review_class_derived_externally") is True,
        f"{field}.review_class_derived_externally must be true",
    )


def validate_exact_source(
    git: GitObjects,
    catalog: dict[str, Any],
    mapping: dict[str, Any],
) -> tuple[dict[str, bytes], str]:
    source_scope = require_mapping(catalog.get("source_scope"), "catalog.source_scope")
    exact_source = require_mapping(mapping.get("exact_source"), "mapping.exact_source")
    require(source_scope == exact_source, "catalog and mapping exact-source bindings differ")
    release = require_string(source_scope.get("release"), "source.release")
    tag_oid = require_sha1(
        source_scope.get("annotated_tag_object_sha1"), "source.annotated_tag_object_sha1"
    )
    commit_oid = require_sha1(source_scope.get("commit_sha1"), "source.commit_sha1")
    base_oid = require_sha1(
        source_scope.get("slice_working_base_commit_sha1"),
        "source.slice_working_base_commit_sha1",
    )
    git.require_commit(commit_oid, "source.commit_sha1")
    git.require_commit(base_oid, "source.slice_working_base_commit_sha1")
    require(git.ref_oid(f"refs/tags/{release}") == tag_oid, "release tag ref does not match bound annotated tag")
    tag_bytes = git.tag_bytes(tag_oid)
    try:
        tag_text = tag_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        fail(f"annotated tag object is not UTF-8: {exc}")
    require(f"\ntag {release}\n" in "\n" + tag_text, "annotated tag name does not match release")
    require(git.peeled_commit(tag_oid) == commit_oid, "annotated tag does not peel to bound commit")

    records = require_list(source_scope.get("exact_runtime_sources"), "source.exact_runtime_sources")
    require(len(records) == 3, "exact runtime source set must contain three files")
    sources: dict[str, bytes] = {}
    for index, raw_record in enumerate(records):
        record = require_mapping(raw_record, f"source.exact_runtime_sources[{index}]")
        path = require_repo_path(record.get("path"), f"source.exact_runtime_sources[{index}].path")
        require(path not in sources, f"duplicate exact runtime source {path}")
        expected = require_sha256(record.get("raw_sha256"), f"source hash for {path}")
        data = git.blob(commit_oid, path, f"release source {path}")
        require(sha256_bytes(data) == expected, f"release source hash mismatch for {path}")
        base_data = git.blob(base_oid, path, f"working-base source {path}")
        require(base_data == data, f"working-base source bytes differ for {path}")
        sources[path] = data
    require(
        set(sources)
        == {
            "scripts/validate.py",
            ".github/workflows/adopter-validate.yml",
            ".github/workflows/self-check.yml",
        },
        "unexpected exact runtime source path set",
    )
    return sources, commit_oid


def validate_authority_sources(
    git: GitObjects, catalog: dict[str, Any], mapping: dict[str, Any]
) -> int:
    if "authority_sources" not in catalog:
        return 0
    sources = require_mapping(catalog["authority_sources"], "catalog.authority_sources")
    contract = require_mapping(
        catalog.get("authority_reference_contract"),
        "catalog.authority_reference_contract",
    )
    closed = require_unique_strings(
        contract.get("closed_source_id_set"),
        "catalog.authority_reference_contract.closed_source_id_set",
    )
    require(set(closed) == set(sources), "authority source registry is not closed")
    require(
        contract.get("on_unregistered_source_id") == "REJECT",
        "unregistered authority source IDs must be rejected",
    )
    for source_id, raw_source in sources.items():
        require(SOURCE_ID_RE.fullmatch(source_id) is not None, f"invalid authority source ID {source_id!r}")
        source = require_mapping(raw_source, f"authority_sources.{source_id}")
        kind = require_string(source.get("kind"), f"authority_sources.{source_id}.kind")
        if kind == "EXACT_REPOSITORY_FILE":
            revision = require_sha1(source.get("revision_sha1"), f"authority source {source_id} revision")
            path = require_repo_path(source.get("path"), f"authority source {source_id} path")
            expected = require_sha256(source.get("raw_sha256"), f"authority source {source_id} hash")
            require(
                sha256_bytes(git.blob(revision, path, f"authority source {source_id}"))
                == expected,
                f"authority source hash mismatch for {source_id}",
            )
        elif kind == "SELF_COMPATIBILITY_DECISION":
            require(source.get("decision_id") == catalog.get("decision_id"), f"self authority {source_id} decision mismatch")
            require(source.get("exact_candidate_bytes_bound_only_by_later_acceptance") is True, f"self authority {source_id} must remain externally bound")
        elif kind == "EXACT_RUNTIME_SURFACE":
            exact_source = require_mapping(
                mapping.get("exact_source"), "mapping.exact_source"
            )
            tag_oid = require_sha1(
                source.get("annotated_tag_object_sha1"),
                f"authority source {source_id} tag",
            )
            revision = require_sha1(
                source.get("revision_sha1"),
                f"authority source {source_id} revision",
            )
            require(
                tag_oid == exact_source.get("annotated_tag_object_sha1")
                and revision == exact_source.get("commit_sha1"),
                f"authority source {source_id} differs from the exact runtime surface",
            )
            source_ref = require_string(
                source.get("source_ref"),
                f"authority source {source_id} source_ref",
            )
            require(
                source_ref in sources,
                f"authority source {source_id} has unknown source_ref",
            )
            referenced_source = require_mapping(
                sources[source_ref], f"authority source {source_id} source_ref"
            )
            validator_record = next(
                (
                    record
                    for record in exact_source["exact_runtime_sources"]
                    if record.get("path") == "scripts/validate.py"
                ),
                None,
            )
            require(
                referenced_source.get("kind") == "EXACT_REPOSITORY_FILE"
                and referenced_source.get("revision_sha1") == revision
                and referenced_source.get("path") == "scripts/validate.py"
                and validator_record is not None
                and referenced_source.get("raw_sha256")
                == validator_record.get("raw_sha256"),
                f"authority source {source_id} does not bind the exact validator source",
            )
        else:
            fail(f"unsupported authority source kind {kind!r}")

    reference_count = 0
    for root_name, root in (("catalog", catalog), ("mapping", mapping)):
        for obj in walk_objects(root):
            if "authority_refs" not in obj:
                continue
            refs = require_list(obj["authority_refs"], f"{root_name}.authority_refs")
            for raw_ref in refs:
                ref = require_mapping(raw_ref, f"{root_name}.authority_refs[]")
                source_id = require_string(ref.get("source_id"), f"{root_name}.authority_refs[].source_id")
                require(source_id in sources, f"unregistered authority source ID {source_id!r}")
                require_string(ref.get("locator"), f"authority locator for {source_id}")
                require("source" not in ref, "mutable/untyped authority source reference is forbidden")
                reference_count += 1
    require(reference_count > 0, "authority source registry has no references")
    return reference_count


def validate_catalog(catalog: dict[str, Any]) -> dict[str, Any]:
    require(catalog.get("document_kind") == "diagnostic_catalog_compatibility_decision_candidate", "unexpected catalog document_kind")
    require(catalog.get("review_data_format") == 1, "unsupported catalog review_data_format")
    require(catalog.get("runtime_contract") is False, "catalog must not be a runtime contract")
    decision_id = require_string(catalog.get("decision_id"), "catalog.decision_id")
    validate_candidate_lifecycle(catalog.get("candidate_lifecycle"), "catalog.candidate_lifecycle")

    catalog_meta = require_mapping(catalog.get("catalog"), "catalog.catalog")
    catalog_id = require_string(catalog_meta.get("catalog_id"), "catalog.catalog_id")
    require(catalog_meta.get("catalog_revision") == 1, "first catalog revision must be 1")
    require(catalog_meta.get("parent_catalog_revision") is None, "first catalog parent must be null")
    require(catalog_meta.get("allocation_effective_only_after_decision_acceptance") is True, "catalog allocation must require external acceptance")

    input_roles = require_unique_strings(catalog.get("semantic_input_roles"), "catalog.semantic_input_roles")
    checks_raw = require_list(catalog.get("public_checks"), "catalog.public_checks")
    checks: dict[str, dict[str, Any]] = {}
    for index, raw_check in enumerate(checks_raw):
        check = require_mapping(raw_check, f"catalog.public_checks[{index}]")
        check_id = require_string(check.get("check_id"), f"catalog.public_checks[{index}].check_id")
        require(3 <= len(check_id) <= 96 and CHECK_RE.fullmatch(check_id) is not None, f"invalid public check ID {check_id!r}")
        require(check_id not in checks, f"duplicate public check ID {check_id}")
        checks[check_id] = check
        for role in require_unique_strings(check.get("semantic_input_roles"), f"check {check_id} semantic_input_roles"):
            require(role in input_roles, f"check {check_id} uses unregistered semantic input role {role}")
    for check_id, check in checks.items():
        dependencies = require_unique_strings(check.get("proposed_dependency_check_ids"), f"check {check_id} dependencies")
        require(check_id not in dependencies, f"check {check_id} depends on itself")
        for dependency in dependencies:
            require(dependency in checks, f"check {check_id} has unknown dependency {dependency}")

    visiting: set[str] = set()
    visited: set[str] = set()
    def visit(check_id: str) -> None:
        if check_id in visiting:
            fail(f"public check dependency cycle includes {check_id}")
        if check_id in visited:
            return
        visiting.add(check_id)
        for dependency in checks[check_id]["proposed_dependency_check_ids"]:
            visit(dependency)
        visiting.remove(check_id)
        visited.add(check_id)
    for check_id in checks:
        visit(check_id)

    findings_root = require_mapping(catalog.get("findings"), "catalog.findings")
    findings_raw = require_list(findings_root.get("allocated_entries"), "catalog.findings.allocated_entries")
    findings: dict[str, dict[str, Any]] = {}
    for index, raw_finding in enumerate(findings_raw):
        finding = require_mapping(raw_finding, f"catalog.findings[{index}]")
        code = require_string(finding.get("code"), f"catalog.findings[{index}].code")
        require(FINDING_RE.fullmatch(code) is not None and code != "F0000", f"invalid finding code {code!r}")
        require(code not in findings, f"duplicate finding code {code}")
        owner = require_string(finding.get("owning_check_id"), f"finding {code} owner")
        require(owner in checks, f"finding {code} has unknown owner {owner}")
        reference = require_mapping(finding.get("reference"), f"finding {code} reference")
        require(reference.get("decision_id") == decision_id, f"finding {code} references another decision")
        require(reference.get("condition_locator") == code, f"finding {code} has mismatched locator")
        require(reference.get("external_acceptance_required") is True, f"finding {code} must require external acceptance")
        schema = require_mapping(finding.get("fact_schema"), f"finding {code} fact_schema")
        require(schema.get("closed") is True and schema.get("null_allowed") is False, f"finding {code} fact schema must be closed/non-null")
        properties = require_mapping(schema.get("properties"), f"finding {code} fact properties")
        required_keys = require_unique_strings(schema.get("required"), f"finding {code} required facts")
        require(set(required_keys) <= set(properties), f"finding {code} requires undeclared facts")
        for fact_key, raw_property in properties.items():
            require_string(fact_key, f"finding {code} fact key")
            validate_fact_property_schema(
                require_mapping(
                    raw_property,
                    f"finding {code} fact property {fact_key}",
                ),
                f"finding {code} fact property {fact_key}",
            )
        findings[code] = finding

    reasons_root = require_mapping(catalog.get("reasons"), "catalog.reasons")
    reasons_raw = require_list(reasons_root.get("allocated_entries"), "catalog.reasons.allocated_entries")
    reasons: dict[str, dict[str, Any]] = {}
    for index, raw_reason in enumerate(reasons_raw):
        reason = require_mapping(raw_reason, f"catalog.reasons[{index}]")
        code = require_string(reason.get("reason_code"), f"catalog.reasons[{index}].reason_code")
        require(len(code) <= 64 and REASON_RE.fullmatch(code) is not None, f"invalid reason code {code!r}")
        require(code not in reasons, f"duplicate reason code {code}")
        detail = require_mapping(reason.get("detail_schema"), f"reason {code} detail_schema")
        require(detail.get("closed") is True and detail.get("null_allowed") is False, f"reason {code} detail schema must be closed/non-null")
        reasons[code] = reason

    closed = require_mapping(catalog.get("closed_entry_sets"), "catalog.closed_entry_sets")
    require(closed.get("public_check_count") == len(checks), "closed public-check count mismatch")
    require(closed.get("finding_count") == len(findings), "closed finding count mismatch")
    require(closed.get("reason_count") == len(reasons), "closed reason count mismatch")
    require(closed.get("public_check_ids") == list(checks), "closed public-check ID order/set mismatch")
    require(closed.get("finding_codes") == list(findings), "closed finding code order/set mismatch")
    require(closed.get("reason_codes") == list(reasons), "closed reason code order/set mismatch")
    require(list(findings) == [f"F{number:04d}" for number in range(1, len(findings) + 1)], "first finding allocation is not contiguous from F0001")

    forbidden = set(require_unique_strings(require_mapping(catalog.get("validation_contract"), "catalog.validation_contract").get("recursive_forbidden_candidate_keys"), "catalog forbidden keys"))
    for root_name, root in (("catalog", catalog),):
        for obj in walk_objects(root):
            present = forbidden.intersection(obj)
            require(not present, f"{root_name} contains forbidden candidate key(s): {sorted(present)}")

    return {
        "decision_id": decision_id,
        "catalog_id": catalog_id,
        "catalog_revision": 1,
        "input_roles": set(input_roles),
        "checks": checks,
        "findings": findings,
        "reasons": reasons,
    }


def iter_semantic_leaves(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        if value.get("kind") in {"FINDING", "REASON", "CHECK_COMPLETION_EVIDENCE"}:
            yield value
        for child in value.values():
            yield from iter_semantic_leaves(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_semantic_leaves(child)


def validate_fact_property_schema(schema: dict[str, Any], field: str) -> None:
    """Validate the closed fact-schema subset used by this candidate."""

    fact_type = require_string(schema.get("type"), f"{field}.type")
    if fact_type == "string":
        require(
            set(schema) == {"type", "enum"},
            f"{field} string schema must contain only type and enum",
        )
        enum_values = require_unique_strings(schema.get("enum"), f"{field}.enum")
        require(enum_values, f"{field}.enum must not be empty")
    elif fact_type == "boolean":
        require(
            set(schema) == {"type"},
            f"{field} boolean schema must contain only type",
        )
    else:
        fail(f"{field} uses unsupported fact type {fact_type!r}")


def validate_fact_value(value: Any, schema: dict[str, Any], field: str) -> None:
    """Require one materialized or enumerated value to satisfy its fact schema."""

    fact_type = schema["type"]
    if fact_type == "string":
        require(isinstance(value, str), f"{field} must be a string")
    elif fact_type == "boolean":
        require(type(value) is bool, f"{field} must be a boolean")
    else:  # The catalog schema was validated before semantic bindings.
        fail(f"{field} uses unsupported fact type {fact_type!r}")
    if "enum" in schema:
        require(value in schema["enum"], f"{field} is outside the catalog enum")


FindingSourceKey = tuple[str, str | None, str | None, str | None]


def collect_finding_source_bindings(
    value: Any,
    group_id: str,
    result: dict[str, Counter[FindingSourceKey]],
    *,
    callsite_selector: str | None = None,
    variant_id: str | None = None,
    source_predicate: str | None = None,
) -> None:
    """Derive the exact catalog source-binding tuple for every mapping leaf."""

    if isinstance(value, dict):
        if "callsite_selector" in value:
            callsite_selector = require_string(
                value["callsite_selector"],
                f"semantic group {group_id} callsite selector",
            )
        if "variant_id" in value:
            variant_id = require_string(
                value["variant_id"],
                f"semantic group {group_id} variant ID",
            )
        if "source_predicate" in value:
            source_predicate = require_string(
                value["source_predicate"],
                f"semantic group {group_id} source predicate",
            )
        if "producer_predicate" in value:
            source_predicate = require_string(
                value["producer_predicate"],
                f"semantic group {group_id} producer predicate",
            )
        if value.get("kind") == "FINDING":
            code = require_string(
                value.get("finding_code"),
                f"semantic group {group_id} finding code",
            )
            result[code][
                (group_id, callsite_selector, variant_id, source_predicate)
            ] += 1
            return
        for child in value.values():
            collect_finding_source_bindings(
                child,
                group_id,
                result,
                callsite_selector=callsite_selector,
                variant_id=variant_id,
                source_predicate=source_predicate,
            )
    elif isinstance(value, list):
        for child in value:
            collect_finding_source_bindings(
                child,
                group_id,
                result,
                callsite_selector=callsite_selector,
                variant_id=variant_id,
                source_predicate=source_predicate,
            )


def validate_fact_bindings(
    leaf: dict[str, Any],
    finding: dict[str, Any],
    input_roles: set[str],
    reason_codes: set[str],
    field: str,
) -> bool:
    schema = finding["fact_schema"]
    required_keys = list(schema["required"])
    bindings = leaf.get("fact_bindings")
    if not required_keys:
        require(
            bindings is None,
            f"{field} factless finding must not carry fact bindings",
        )
        return False
    binding_object = require_mapping(bindings, f"{field}.fact_bindings")
    base_binding_keys = {
        "closed",
        "required_key_set",
        "on_missing_required_key",
        "on_extra_key",
        "on_null",
        "bindings",
    }
    cross_field_keys = {
        "cross_field_predicate",
        "on_unsatisfied_cross_field_predicate",
        "catalog_condition_predicate_ref",
    }
    expected_binding_keys = (
        base_binding_keys | cross_field_keys
        if finding.get("code") == "F0002"
        else base_binding_keys
    )
    require(
        set(binding_object) == expected_binding_keys,
        f"{field} fact bindings have an unexpected shape",
    )
    require(binding_object.get("closed") is True, f"{field} fact bindings must be closed")
    require(binding_object.get("on_missing_required_key") == "REJECT", f"{field} must reject missing facts")
    require(binding_object.get("on_extra_key") == "REJECT", f"{field} must reject extra facts")
    require(binding_object.get("on_null") == "REJECT", f"{field} must reject null facts")
    key_set = require_unique_strings(binding_object.get("required_key_set"), f"{field}.required_key_set")
    values = require_mapping(binding_object.get("bindings"), f"{field}.bindings")
    require(
        set(key_set) == set(required_keys) and set(values) == set(required_keys),
        f"{field} fact binding keys differ from catalog schema",
    )
    for key, raw_binding in values.items():
        binding = require_mapping(raw_binding, f"{field}.bindings.{key}")
        kind = require_string(binding.get("kind"), f"{field}.bindings.{key}.kind")
        property_schema = require_mapping(
            schema["properties"][key],
            f"{field}.schema.properties.{key}",
        )
        if kind == "LITERAL":
            require(
                set(binding) == {"kind", "value"},
                f"{field}.{key} literal has an unexpected shape",
            )
            require(
                "value" in binding and binding["value"] is not None,
                f"{field}.{key} literal is missing/null",
            )
            validate_fact_value(
                binding["value"], property_schema, f"{field}.{key} literal"
            )
        elif kind == "TRUSTED_CONTEXT_REF":
            require(
                set(binding)
                == {
                    "kind",
                    "semantic_input_role",
                    "field",
                    "allowed_values",
                    "on_unavailable",
                },
                f"{field}.{key} trusted-context binding has an unexpected shape",
            )
            role = require_string(binding.get("semantic_input_role"), f"{field}.{key}.semantic_input_role")
            require(role in input_roles, f"{field}.{key} uses unregistered semantic input role {role}")
            require_string(binding.get("field"), f"{field}.{key}.field")
            allowed_values = require_list(
                binding.get("allowed_values"), f"{field}.{key}.allowed_values"
            )
            require(allowed_values, f"{field}.{key}.allowed_values must not be empty")
            allowed_identities: list[bytes] = []
            for index, allowed_value in enumerate(allowed_values):
                validate_fact_value(
                    allowed_value,
                    property_schema,
                    f"{field}.{key}.allowed_values[{index}]",
                )
                allowed_identities.append(canonical_json_bytes(allowed_value))
            require(
                len(allowed_identities) == len(set(allowed_identities)),
                f"{field}.{key}.allowed_values contains duplicates",
            )
            unavailable = require_string(
                binding.get("on_unavailable"), f"{field}.{key}.on_unavailable"
            )
            if unavailable != "REJECT":
                require(
                    unavailable.startswith("REASON:")
                    and unavailable.removeprefix("REASON:") in reason_codes,
                    f"{field}.{key} has an unregistered unavailable-context reason",
                )
        elif kind == "CLOSED_SOURCE_PREDICATE_DISPATCH":
            require(
                set(binding)
                <= {
                    "kind",
                    "trusted_source",
                    "closed",
                    "ordered_first_match",
                    "variants",
                    "on_unlisted_predicate",
                }
                and {
                    "kind",
                    "trusted_source",
                    "closed",
                    "variants",
                    "on_unlisted_predicate",
                }
                <= set(binding),
                f"{field}.{key} dispatch has an unexpected shape",
            )
            require(binding.get("closed") is True, f"{field}.{key} dispatch must be closed")
            if "ordered_first_match" in binding:
                require(
                    binding["ordered_first_match"] is True,
                    f"{field}.{key} ordered_first_match must be true when present",
                )
            require(binding.get("on_unlisted_predicate") == "REJECT", f"{field}.{key} dispatch must reject unknown predicate")
            variants = require_list(binding.get("variants"), f"{field}.{key}.variants")
            require(variants, f"{field}.{key} dispatch must contain variants")
            predicates: list[str] = []
            for index, raw_variant in enumerate(variants):
                variant = require_mapping(
                    raw_variant, f"{field}.{key}.variants[{index}]"
                )
                require(
                    set(variant) == {"source_predicate", "value"},
                    f"{field}.{key}.variants[{index}] has an unexpected shape",
                )
                predicates.append(
                    require_string(
                        variant.get("source_predicate"),
                        f"{field}.{key}.variants[{index}].source_predicate",
                    )
                )
                require(
                    variant.get("value") is not None,
                    f"{field}.{key}.variants[{index}].value is null",
                )
                validate_fact_value(
                    variant["value"],
                    property_schema,
                    f"{field}.{key}.variants[{index}].value",
                )
            require(len(predicates) == len(set(predicates)), f"{field}.{key} dispatch has duplicate predicates")
            source = require_mapping(
                binding.get("trusted_source"), f"{field}.{key}.trusted_source"
            )
            require(
                set(source) == {"semantic_input_role", "field"},
                f"{field}.{key}.trusted_source has an unexpected shape",
            )
            role = require_string(source.get("semantic_input_role"), f"{field}.{key}.trusted_source.role")
            require(role in input_roles, f"{field}.{key} uses unregistered trusted source role {role}")
            require_string(source.get("field"), f"{field}.{key}.trusted_source.field")
        else:
            fail(f"{field}.{key} uses unsupported fact binding kind {kind!r}")
    return True


def validate_closed_dispatches(value: Any, field: str) -> None:
    if isinstance(value, dict):
        kind = value.get("kind")
        if isinstance(kind, str) and kind.startswith("CLOSED_"):
            require(value.get("closed") is True, f"{field} {kind} must be closed")
            rejection_keys = [key for key in value if key.startswith("on_unlisted")]
            require(rejection_keys, f"{field} {kind} lacks an unlisted-value policy")
            for key in rejection_keys:
                allowed = {"REJECT"}
                if kind == "CLOSED_SCHEMA_POINTER_DISPATCH" and key == "on_unlisted_pointer":
                    allowed.add("PROJECT_GENERIC_SCHEMA_FINDING")
                require(
                    value[key] in allowed,
                    f"{field} {kind}.{key} has an unsupported fallback",
                )
            for list_key, identity_keys in (
                ("projections", ("callsite_selector", "variant_id")),
                ("variants", ("variant_id", "source_predicate", "producer_predicate")),
                ("callsite_projections", ("callsite_selector",)),
            ):
                if list_key in value:
                    entries = require_list(value[list_key], f"{field}.{list_key}")
                    require(entries, f"{field}.{list_key} must not be empty")
                    identities: list[tuple[Any, ...]] = []
                    for raw_entry in entries:
                        entry = require_mapping(raw_entry, f"{field}.{list_key}[]")
                        identity = tuple(entry.get(key) for key in identity_keys)
                        identities.append(identity)
                    require(len(identities) == len(set(identities)), f"{field}.{list_key} has duplicate dispatch identities")
        for key, child in value.items():
            validate_closed_dispatches(child, f"{field}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_closed_dispatches(child, f"{field}[{index}]")


def validate_semantic_mapping(
    mapping: dict[str, Any],
    catalog_data: dict[str, Any],
    analysis: dict[str, Any],
    source_commit: str,
) -> dict[str, Any]:
    semantic = require_mapping(mapping.get("semantic_mapping"), "mapping.semantic_mapping")
    require(semantic.get("closed") is True, "semantic mapping must be closed")
    require(semantic.get("english_message_identity_parsing") == "FORBIDDEN", "English message parsing must be forbidden")
    require(semantic.get("on_unregistered_group") == "REJECT", "unregistered semantic groups must be rejected")
    require(semantic.get("on_overlapping_selector_predicate") == "REJECT", "overlapping selector predicates must be rejected")
    rows = require_list(semantic.get("group_rows"), "mapping.semantic_mapping.group_rows")
    claims = require_mapping(mapping.get("closure_claims"), "mapping.closure_claims")
    require(claims.get("semantic_group_set_closed") is True, "semantic group set is not closed")
    require(claims.get("semantic_group_count") == len(rows), "semantic group count mismatch")

    group_ids: list[str] = []
    direct_coverage: dict[int, list[str]] = defaultdict(list)
    upstream_group_lines: list[int] = []
    finding_leaf_count = 0
    fact_bound_leaf_count = 0
    derived_finding_bindings: dict[str, Counter[FindingSourceKey]] = defaultdict(
        Counter
    )
    for index, raw_row in enumerate(rows):
        row = require_mapping(raw_row, f"semantic group[{index}]")
        group_id = require_string(row.get("group_id"), f"semantic group[{index}].group_id")
        group_ids.append(group_id)
        selectors = require_mapping(row.get("source_selectors"), f"semantic group {group_id} selectors")
        require(selectors.get("revision") == source_commit, f"semantic group {group_id} has wrong source revision")
        require(selectors.get("path") == "scripts/validate.py", f"semantic group {group_id} has wrong source path")
        direct_lines = [require_int(line, f"semantic group {group_id} direct line", minimum=1) for line in require_list(selectors.get("direct_emitter_lines"), f"semantic group {group_id} direct lines")]
        upstream_lines = [require_int(line, f"semantic group {group_id} upstream line", minimum=1) for line in require_list(selectors.get("upstream_producer_lines"), f"semantic group {group_id} upstream lines")]
        require(len(direct_lines) == len(set(direct_lines)), f"semantic group {group_id} repeats a direct line")
        require(len(upstream_lines) == len(set(upstream_lines)), f"semantic group {group_id} repeats an upstream line")
        for line in direct_lines:
            direct_coverage[line].append(group_id)
        upstream_group_lines.extend(upstream_lines)
        predicates = require_unique_strings(selectors.get("selector_predicates"), f"semantic group {group_id} predicates")
        if len(direct_lines) + len(upstream_lines) > 1 and predicates:
            require(all(predicates), f"semantic group {group_id} has empty predicate")
        target = row.get("target")
        validate_closed_dispatches(target, f"semantic group {group_id}.target")
        collect_finding_source_bindings(
            target, group_id, derived_finding_bindings
        )
        for leaf in iter_semantic_leaves(target):
            kind = leaf["kind"]
            if kind == "FINDING":
                finding_leaf_count += 1
                code = require_string(leaf.get("finding_code"), f"semantic group {group_id} finding code")
                require(code in catalog_data["findings"], f"semantic group {group_id} has unknown finding {code}")
                finding = catalog_data["findings"][code]
                require(leaf.get("owning_check_id") == finding["owning_check_id"], f"semantic group {group_id} finding owner mismatch for {code}")
                require(leaf.get("condition_slug") == finding["condition_slug"], f"semantic group {group_id} condition slug mismatch for {code}")
                if validate_fact_bindings(
                    leaf,
                    finding,
                    catalog_data["input_roles"],
                    set(catalog_data["reasons"]),
                    f"semantic group {group_id}/{code}",
                ):
                    fact_bound_leaf_count += 1
            elif kind == "REASON":
                reason = require_string(leaf.get("reason_code"), f"semantic group {group_id} reason")
                require(reason in catalog_data["reasons"], f"semantic group {group_id} has unknown reason {reason}")
                owner_kind = require_string(leaf.get("owner_kind"), f"semantic group {group_id} reason owner kind")
                owner_id = require_string(leaf.get("owner_id"), f"semantic group {group_id} reason owner")
                if owner_kind == "CHECK":
                    require(owner_id in catalog_data["checks"], f"semantic group {group_id} has unknown check owner {owner_id}")
                elif owner_kind == "INPUT":
                    require(owner_id in catalog_data["input_roles"], f"semantic group {group_id} has unknown input owner {owner_id}")
                else:
                    require(owner_kind in {"RUN", "PROVIDER"}, f"semantic group {group_id} has invalid reason owner kind {owner_kind}")
            elif kind == "CHECK_COMPLETION_EVIDENCE":
                check_id = require_string(leaf.get("check_id"), f"semantic group {group_id} completion check")
                require(check_id in catalog_data["checks"], f"semantic group {group_id} has unknown completion check {check_id}")
                require(leaf.get("legacy_ok_text_is_completion") is False, f"semantic group {group_id} treats legacy prose as completion")
    require(len(group_ids) == len(set(group_ids)), "semantic group IDs are not unique")

    emitter_lines = {int(item["line"]) for item in analysis["direct_emitters"]}
    require(set(direct_coverage) == emitter_lines, "direct emitter source locator set is incomplete or has extras")
    overlap = require_mapping(require_mapping(mapping.get("inventory_evidence"), "mapping.inventory_evidence").get("physical_line_overlap"), "mapping physical_line_overlap")
    overlap_line = require_int(overlap.get("line"), "physical overlap line", minimum=1)
    overlap_groups = require_unique_strings(overlap.get("groups"), "physical overlap groups")
    require(overlap.get("predicates_are_disjoint") is True, "physical overlap predicates are not declared disjoint")
    for line, groups in direct_coverage.items():
        if line == overlap_line:
            require(sorted(groups) == sorted(overlap_groups) and len(groups) == 2, "documented direct-emitter overlap does not match mapping")
            for group_id in groups:
                row = rows[group_ids.index(group_id)]
                require(row["source_selectors"]["selector_predicates"], f"overlap group {group_id} lacks a predicate")
        else:
            require(len(groups) == 1, f"direct emitter line {line} is covered {len(groups)} times")

    excluded = require_list(semantic.get("excluded_internal_success_rows"), "excluded internal success rows")
    excluded_lines = [require_int(require_mapping(row, "excluded success row").get("line"), "excluded success line", minimum=1) for row in excluded]
    require(len(excluded_lines) == len(set(excluded_lines)), "excluded success rows repeat a line")
    preliminary_lines = {int(item["line"]) for item in analysis["preliminary_upstream_producers"]}
    supplemental_lines = {int(item["line"]) for item in analysis["supplemental_upstream_producers"]}
    group_upstream_set = set(upstream_group_lines)
    require(len(upstream_group_lines) == len(group_upstream_set), "an upstream producer line is multiply covered")
    require(group_upstream_set.isdisjoint(excluded_lines), "upstream group and excluded-success coverage overlap")
    require(group_upstream_set | set(excluded_lines) == preliminary_lines | supplemental_lines, "upstream producer exact-once coverage differs from AST inventory")
    evidence = require_mapping(mapping.get("inventory_evidence"), "mapping.inventory_evidence")
    require(evidence.get("supplemental_upstream_producer_lines") == sorted(supplemental_lines), "supplemental upstream producer inventory mismatch")
    require(claims.get("upstream_producer_line_count") == len(preliminary_lines | supplemental_lines), "upstream producer closure count mismatch")
    require(claims.get("direct_emitter_line_count") == len(emitter_lines), "direct emitter closure count mismatch")
    require(claims.get("required_fact_finding_leaf_count") == fact_bound_leaf_count, "required-fact finding leaf count mismatch")
    require(claims.get("required_fact_binding_set_closed") is True, "required fact binding set is not closed")

    # Catalog source bindings must reciprocally equal the exact mapping leaves,
    # including every callsite, producer variant, and source predicate.
    # Prospective negative inventory is the sole permitted empty producer set.
    group_set = set(group_ids)
    for code, finding in catalog_data["findings"].items():
        binding = require_mapping(finding.get("source_binding"), f"finding {code} source_binding")
        producer_groups = require_list(binding.get("producer_groups"), f"finding {code} producer_groups")
        if binding.get("kind") == "CLOSED_NEGATIVE_V0_4_INVENTORY_PROSPECTIVE_ALLOCATION":
            require(
                set(binding)
                == {
                    "kind",
                    "mapping_revision",
                    "v0_4_producer_present",
                    "producer_groups",
                },
                f"finding {code} negative source binding has an unexpected shape",
            )
            require(producer_groups == [] and binding.get("v0_4_producer_present") is False, f"finding {code} negative inventory is not closed")
        else:
            require(
                binding.get("kind") == "EXACT_V0_4_PRODUCER_SET"
                and set(binding) == {"kind", "mapping_revision", "producer_groups"},
                f"finding {code} source binding has an unexpected shape",
            )
            require(producer_groups, f"finding {code} has no producer groups")
        require(
            binding.get("mapping_revision") == mapping.get("mapping_revision"),
            f"finding {code} source binding uses another mapping revision",
        )
        expected_bindings: Counter[FindingSourceKey] = Counter()
        for raw_ref in producer_groups:
            ref = require_mapping(raw_ref, f"finding {code} producer ref")
            require(
                set(ref)
                == {
                    "group_id",
                    "callsite_selector",
                    "variant_id",
                    "source_predicate",
                },
                f"finding {code} producer ref has an unexpected shape",
            )
            group_id = require_string(
                ref.get("group_id"), f"finding {code} producer group"
            )
            require(group_id in group_set, f"finding {code} references unknown semantic group")
            key: FindingSourceKey = (
                group_id,
                ref.get("callsite_selector"),
                ref.get("variant_id"),
                ref.get("source_predicate"),
            )
            for field_name, value in zip(
                ("callsite_selector", "variant_id", "source_predicate"), key[1:]
            ):
                if value is not None:
                    require_string(value, f"finding {code} producer {field_name}")
            expected_bindings[key] += 1
        require(
            expected_bindings == derived_finding_bindings.get(code, Counter()),
            f"finding {code} source binding differs from exact mapping leaves",
        )

    return {
        "semantic_group_count": len(rows),
        "direct_emitter_count": len(emitter_lines),
        "direct_emitter_function_count": analysis["direct_emitter_function_count"],
        "upstream_producer_count": len(preliminary_lines | supplemental_lines),
        "finding_leaf_count": finding_leaf_count,
        "required_fact_finding_leaf_count": fact_bound_leaf_count,
        "group_ids": group_set,
    }


def validate_control_flow(mapping: dict[str, Any], analysis: dict[str, Any]) -> None:
    inventory = require_mapping(mapping.get("control_flow_inventory"), "mapping.control_flow_inventory")
    require(inventory.get("legacy_ok_text_is_positive_plan_evidence") is False, "legacy OK text must not be plan completion")
    require(inventory.get("report_emit_return_lines") == analysis["report_emit_return_lines"], "Report.emit return inventory mismatch")
    require(inventory.get("report_results_read_lines") == analysis["report_results_read_lines"], "report.results read inventory mismatch")
    claims = mapping["closure_claims"]
    require(claims.get("report_emit_return_set_closed") is True and claims.get("report_emit_return_count") == len(analysis["report_emit_return_lines"]), "Report.emit closure claim mismatch")
    require(claims.get("report_results_read_set_closed") is True and claims.get("report_results_read_count") == len(analysis["report_results_read_lines"]), "report.results closure claim mismatch")


def workflow_projection(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": value.get("path"),
        "raw_sha256": value.get("raw_sha256"),
        "job_count": value.get("job_count"),
        "step_count": value.get("step_count"),
        "jobs": value.get("jobs"),
    }


def validate_workflows(
    mapping: dict[str, Any], sources: dict[str, bytes]
) -> tuple[list[dict[str, Any]], set[tuple[str, str]]]:
    derived = [
        parse_workflow(sources[path], path)
        for path in (
            ".github/workflows/adopter-validate.yml",
            ".github/workflows/self-check.yml",
        )
    ]
    expected = [
        require_mapping(item, "mapping.workflow_surface_inventory[]")
        for item in require_list(mapping.get("workflow_surface_inventory"), "mapping.workflow_surface_inventory")
    ]
    require([workflow_projection(item) for item in expected] == derived, "workflow surface inventory differs from bounded source derivation")
    claims = mapping["closure_claims"]
    job_count = sum(int(item["job_count"]) for item in derived)
    step_count = sum(int(item["step_count"]) for item in derived)
    require(claims.get("workflow_job_set_closed") is True and claims.get("workflow_job_count") == job_count, "workflow job closure claim mismatch")
    require(claims.get("workflow_step_set_closed") is True and claims.get("workflow_step_count") == step_count, "workflow step closure claim mismatch")
    jobs = {(item["path"], job["job_id"]) for item in derived for job in item["jobs"]}
    return derived, jobs


def validate_terminal_mapping(
    mapping: dict[str, Any],
    catalog_data: dict[str, Any],
    workflow_jobs: set[tuple[str, str]],
    source_line_counts: dict[str, int],
) -> int:
    terminal = require_mapping(mapping.get("terminal_mapping"), "mapping.terminal_mapping")
    require(
        terminal.get("schema_version") == 2,
        "terminal mapping must use typed-reference schema version 2",
    )
    derived_from = require_mapping(
        terminal.get("derived_from"), "terminal derived_from"
    )
    require(
        derived_from.get("review_data_schema")
        == "aap-v0.5-terminal-crosswalk-candidate-2",
        "terminal review-data schema identity does not match schema version 2",
    )
    families = require_list(terminal.get("families"), "mapping.terminal_mapping.families")
    require(terminal.get("inventory_family_set_closed") is True, "terminal inventory family set is not closed")
    require(terminal.get("family_count") == len(families), "terminal family count mismatch")
    family_ids: list[str] = []
    provider_domains = set(require_mapping(terminal.get("provider_domains"), "terminal provider domains"))
    contract = terminal.get("typed_reference_contract")
    typed_contract = require_mapping(contract, "terminal typed_reference_contract") if contract is not None else None
    if typed_contract is not None:
        require(typed_contract.get("closed") is True, "terminal typed-reference contract is not closed")
        require(typed_contract.get("on_unregistered_or_unlisted_reference") == "REJECT", "terminal typed-reference contract must reject unknown references")

    locator_re = re.compile(r"(.+):([1-9][0-9]*)(?:-([1-9][0-9]*))?\Z")
    registered_reason_codes: set[str] = set()
    for index, raw_family in enumerate(families):
        family = require_mapping(raw_family, f"terminal family[{index}]")
        family_id = require_string(family.get("family_id"), f"terminal family[{index}].family_id")
        family_ids.append(family_id)
        require(family.get("family_inventory_included") is True, f"terminal family {family_id} is excluded")
        require(family.get("current_runtime_projection_ready") is False, f"terminal family {family_id} claims runtime readiness")
        require(family.get("current_runtime_typed_projection_available") is False, f"terminal family {family_id} claims typed runtime output")
        for provider_ref in require_unique_strings(family.get("provider_domain_refs"), f"terminal family {family_id} provider refs"):
            require(provider_ref in provider_domains, f"terminal family {family_id} has unknown provider domain {provider_ref}")
        locators = require_unique_strings(
            family.get("exact_source_locators"),
            f"terminal family {family_id} locators",
        )
        require(locators, f"terminal family {family_id} has no source locator")
        require_string(
            family.get("required_future_discriminant"),
            f"terminal family {family_id} required future discriminant",
        )
        for locator in locators:
            match = locator_re.fullmatch(locator)
            require(match is not None, f"terminal family {family_id} has invalid source locator {locator!r}")
            path = require_repo_path(match.group(1), f"terminal family {family_id} locator path")
            require(path in source_line_counts, f"terminal family {family_id} locator path is outside exact source")
            start = int(match.group(2)); end = int(match.group(3) or match.group(2))
            require(1 <= start <= end <= source_line_counts[path], f"terminal family {family_id} locator is out of range")

        if typed_contract is None:
            for reason in require_list(family.get("target_reason_codes", []), f"terminal family {family_id} target reasons"):
                require(reason in catalog_data["reasons"], f"terminal family {family_id} has unknown reason {reason}")
            finding = family.get("target_finding")
            if isinstance(finding, str) and FINDING_RE.fullmatch(finding):
                require(finding in catalog_data["findings"], f"terminal family {family_id} has unknown finding")
            continue

        for legacy_key in ("target_reason_codes", "target_check", "target_finding"):
            require(legacy_key not in family, f"terminal family {family_id} retains untyped {legacy_key}")
        owner = require_mapping(family.get("target_owner_ref"), f"terminal family {family_id} target_owner_ref")
        owner_kind = require_string(owner.get("kind"), f"terminal family {family_id} owner kind")
        require(owner_kind in typed_contract["owner_ref_kinds"], f"terminal family {family_id} has unknown owner-ref kind")
        owner_shapes = {
            "NONE": {"kind"},
            "PUBLIC_CHECK": {"kind", "check_id"},
            "WORKFLOW_JOB": {"kind", "workflow_path", "job_id"},
            "CHECK_SET_SELECTOR": {"kind", "selector"},
            "RUN_BOUNDARY_SELECTOR": {"kind", "selector"},
            "CANDIDATE_PLAN_ROLE": {"kind", "role"},
        }
        require(
            set(owner) == owner_shapes[owner_kind],
            f"terminal family {family_id} has an invalid {owner_kind} owner-ref shape",
        )
        if owner_kind == "PUBLIC_CHECK":
            require(owner.get("check_id") in catalog_data["checks"], f"terminal family {family_id} has unknown public check")
        elif owner_kind == "WORKFLOW_JOB":
            job_ref = (owner.get("workflow_path"), owner.get("job_id"))
            require(job_ref in workflow_jobs, f"terminal family {family_id} has unknown workflow job ref")
        elif owner_kind == "CHECK_SET_SELECTOR":
            require(owner.get("selector") in typed_contract["check_set_selectors"], f"terminal family {family_id} has unknown check-set selector")
        elif owner_kind == "RUN_BOUNDARY_SELECTOR":
            require(owner.get("selector") in typed_contract["run_boundary_selectors"], f"terminal family {family_id} has unknown run-boundary selector")
        elif owner_kind == "CANDIDATE_PLAN_ROLE":
            require(owner.get("role") in typed_contract["candidate_plan_roles"], f"terminal family {family_id} has unknown candidate-plan role")
        elif owner_kind == "NONE":
            require(set(owner) == {"kind"}, f"terminal family {family_id} NONE owner carries data")

        finding_ref = require_mapping(family.get("finding_source_ref"), f"terminal family {family_id} finding_source_ref")
        finding_kind = require_string(finding_ref.get("kind"), f"terminal family {family_id} finding ref kind")
        require(finding_kind in typed_contract["finding_source_ref_kinds"], f"terminal family {family_id} has unknown finding-ref kind")
        finding_shapes = {
            "NONE": {"kind"},
            "REGISTERED_FINDING": {"kind", "finding_code"},
            "FINDINGS_FROM_TYPED_SEMANTIC_RESULTS": {"kind"},
            "FINDINGS_FROM_TYPED_REPORT": {"kind"},
            "CLOSED_SOURCE_SELECTOR": {"kind", "selector"},
        }
        require(
            set(finding_ref) == finding_shapes[finding_kind],
            f"terminal family {family_id} has an invalid {finding_kind} finding-ref shape",
        )
        if finding_kind == "REGISTERED_FINDING":
            require(finding_ref.get("finding_code") in catalog_data["findings"], f"terminal family {family_id} has unknown registered finding")
        elif finding_kind == "CLOSED_SOURCE_SELECTOR":
            require(finding_ref.get("selector") in typed_contract["finding_source_selectors"], f"terminal family {family_id} has unknown finding selector")
        elif finding_kind == "NONE":
            require(set(finding_ref) == {"kind"}, f"terminal family {family_id} NONE finding ref carries data")

        reason_refs = require_list(family.get("reason_source_refs"), f"terminal family {family_id} reason_source_refs")
        for raw_ref in reason_refs:
            reason_ref = require_mapping(raw_ref, f"terminal family {family_id} reason ref")
            reason_kind = require_string(reason_ref.get("kind"), f"terminal family {family_id} reason ref kind")
            require(reason_kind in typed_contract["reason_source_ref_kinds"], f"terminal family {family_id} has unknown reason-ref kind")
            reason_shapes = {
                "REGISTERED_REASON": {"kind", "reason_code"},
                "REASON_FROM_OWNING_CHECK": {"kind"},
            }
            require(
                set(reason_ref) == reason_shapes[reason_kind],
                f"terminal family {family_id} has an invalid {reason_kind} reason-ref shape",
            )
            if reason_kind == "REGISTERED_REASON":
                require(reason_ref.get("reason_code") in catalog_data["reasons"], f"terminal family {family_id} has unknown reason")
                registered_reason_codes.add(reason_ref["reason_code"])
            elif reason_kind == "REASON_FROM_OWNING_CHECK":
                require(
                    set(reason_ref) == {"kind"},
                    f"terminal family {family_id} owning-check reason carries extra data",
                )

    require(len(family_ids) == len(set(family_ids)), "terminal family IDs are not unique")
    summary = require_mapping(
        terminal.get("coverage_summary"), "terminal coverage_summary"
    )
    require(
        summary
        == {
            "expected_family_count": len(families),
            "actual_family_count": len(families),
            "every_family_included": True,
            "every_runtime_projection_unavailable": True,
            "every_family_has_source_locator": True,
            "every_family_has_future_discriminant": True,
            "reason_code_count": len(registered_reason_codes),
            "inventory_family_set_closed": True,
            "current_runtime_projection_ready": False,
        },
        "terminal coverage summary differs from the typed family inventory",
    )
    claims = mapping["closure_claims"]
    require(claims.get("terminal_family_set_closed") is True and claims.get("terminal_family_count") == len(families), "terminal family closure claim mismatch")
    return len(families)


def validate_phase0(
    git: GitObjects,
    catalog: dict[str, Any],
    mapping: dict[str, Any],
) -> int:
    catalog_projection = require_mapping(catalog.get("phase0_selected_case_projection"), "catalog Phase0 projection")
    mapping_projection = require_mapping(mapping.get("phase0_selected_projection"), "mapping Phase0 projection")
    require(catalog_projection == mapping_projection, "catalog and mapping Phase0 projections differ")
    require(catalog_projection.get("implementation_parity_authorized") is False, "Phase0 projection must not authorize parity")
    require(
        catalog_projection.get("projection_scope")
        == "SELECTED_SEMANTIC_RESULTS_ONLY"
        and catalog_projection.get("public_check_state_bound") is False
        and catalog_projection.get("finding_set_scope")
        == "SELECTED_PHASE0_CONDITION_SET_ONLY",
        "Phase0 projection overstates its selected-condition scope",
    )
    cases = require_list(catalog_projection.get("cases"), "Phase0 cases")
    case_ids = [require_string(require_mapping(case, "Phase0 case").get("case_id"), "Phase0 case ID") for case in cases]
    require(len(case_ids) == len(set(case_ids)), "Phase0 case IDs are not unique")

    selected_projection_count = 0
    for raw_case in cases:
        case = require_mapping(raw_case, "Phase0 case")
        case_id = require_string(case.get("case_id"), "Phase0 case ID")
        require(
            case.get("finding_set_scope")
            == "SELECTED_PHASE0_CONDITION_SET_ONLY",
            f"Phase0 {case_id} overstates its finding-set scope",
        )
        for raw_projection in require_list(
            case.get("condition_projections"),
            f"Phase0 {case_id} condition projections",
        ):
            projection = require_mapping(
                raw_projection, f"Phase0 {case_id} condition projection"
            )
            projection_kind = require_string(
                projection.get("projection_kind"),
                f"Phase0 {case_id} projection kind",
            )
            if projection_kind == "SELECTED_CONDITION_SATISFIED":
                require(
                    set(projection)
                    == {
                        "internal_condition_key",
                        "projection_kind",
                        "public_check_completion",
                        "compatibility_claim",
                    },
                    f"Phase0 {case_id} selected condition has an unexpected shape",
                )
                require(
                    projection.get("public_check_completion")
                    == "DEFERRED_UNTIL_ADR_0004"
                    and projection.get("compatibility_claim")
                    == "SELECTED_PHASE0_CONDITION_ONLY",
                    f"Phase0 {case_id} selected condition claims public completion",
                )
                selected_projection_count += 1
            elif projection_kind == "FINDING":
                require(
                    "public_check_completion" not in projection,
                    f"Phase0 {case_id} finding also claims public completion",
                )
            else:
                fail(
                    f"Phase0 {case_id} has unsupported projection kind "
                    f"{projection_kind!r}"
                )
    require(
        selected_projection_count == 4,
        "Phase0 must contain exactly four selected non-completion conditions",
    )

    sources = catalog.get("authority_sources")
    require(
        isinstance(sources, dict) and "phase0-oracle-r2" in sources,
        "Phase0 projection lacks its accepted oracle authority",
    )
    authority = require_mapping(sources["phase0-oracle-r2"], "phase0 oracle authority")
    ledger_bytes = git.blob(authority["revision_sha1"], authority["path"], "Phase0 ledger authority")
    require(sha256_bytes(ledger_bytes) == authority["raw_sha256"], "Phase0 ledger authority hash mismatch")
    ledger = strict_json_bytes(ledger_bytes, "Phase0 expected-outcomes ledger")
    entries = require_list(ledger.get("entries"), "Phase0 ledger entries")
    selected = {entry["case_id"]: entry for entry in entries if isinstance(entry, dict) and entry.get("case_id") in set(case_ids)}
    require(set(selected) == set(case_ids), "Phase0 projection case set differs from accepted ledger")
    for case in cases:
        case_id = case["case_id"]
        expectation = require_mapping(selected[case_id].get("semantic_expectation"), f"Phase0 ledger {case_id} expectation")
        require(case.get("evaluation_kind") == require_mapping(expectation.get("evaluation_context"), f"Phase0 ledger {case_id} context").get("evaluation_kind"), f"Phase0 evaluation kind mismatch for {case_id}")
        satisfied_condition_keys = set(
            expectation.get("required_satisfied_condition_keys", [])
        )
        projections = require_list(
            case.get("condition_projections"), f"Phase0 {case_id} projections"
        )
        for projection in projections:
            if projection["internal_condition_key"] in satisfied_condition_keys:
                require(
                    projection.get("projection_kind")
                    == "SELECTED_CONDITION_SATISFIED",
                    f"Phase0 {case_id} turns a satisfied condition into another result kind",
                )
        expected_condition_keys = set(satisfied_condition_keys)
        finding_set = require_mapping(expectation.get("finding_set"), f"Phase0 ledger {case_id} finding_set")
        for finding in require_list(finding_set.get("exact"), f"Phase0 ledger {case_id} exact findings"):
            expected_condition_keys.add(require_mapping(finding, f"Phase0 ledger {case_id} finding")["condition_key"])
        actual_condition_keys = {projection["internal_condition_key"] for projection in projections}
        require(actual_condition_keys == expected_condition_keys, f"Phase0 condition projection mismatch for {case_id}")
        projected_findings = Counter(
            projection["code"]
            for projection in projections
            if projection.get("projection_kind") == "FINDING"
        )
        exact_findings = Counter()
        for finding in require_list(case.get("exact_findings"), f"Phase0 {case_id} exact findings"):
            exact = require_mapping(finding, f"Phase0 {case_id} exact finding")
            exact_findings[exact["code"]] += require_int(exact.get("exact_multiplicity"), f"Phase0 {case_id} finding multiplicity", minimum=1)
        require(projected_findings == exact_findings, f"Phase0 finding multiplicity mismatch for {case_id}")
    return len(cases)


def find_group(mapping: dict[str, Any], group_id: str) -> dict[str, Any]:
    rows = mapping["semantic_mapping"]["group_rows"]
    matches = [row for row in rows if row.get("group_id") == group_id]
    require(len(matches) == 1, f"expected exactly one semantic group {group_id}")
    return matches[0]


def validate_keystone_semantics(
    catalog: dict[str, Any], mapping: dict[str, Any]
) -> None:
    """Check the review's explicitly claimed high-risk semantic repairs."""

    findings = {
        finding["code"]: finding
        for finding in catalog["findings"]["allocated_entries"]
    }
    stages = ["DRAFT", "HUMAN_REVIEWED", "CONFORMANT"]
    f0002_predicate = {
        "kind": "ENUM_ORDER_RELATION",
        "left_fact": "head_stage",
        "relation": "LT",
        "right_fact": "base_stage",
        "ordered_values": stages,
        "on_unsatisfied": "REJECT_FINDING_INSTANCE",
    }
    require(
        findings["F0002"].get("condition_predicate") == f0002_predicate,
        "F0002 does not carry the exact head-stage LT base-stage predicate",
    )
    phase0_case = next(
        (
            case
            for case in catalog["phase0_selected_case_projection"]["cases"]
            if case.get("case_id") == "transition-stage-downgrade-block"
        ),
        None,
    )
    require(phase0_case is not None, "Phase0 stage-downgrade case is missing")
    phase0_projection = next(
        (
            projection
            for projection in phase0_case["condition_projections"]
            if projection.get("code") == "F0002"
        ),
        None,
    )
    require(phase0_projection is not None, "Phase0 stage-downgrade F0002 is missing")
    facts = require_mapping(
        phase0_projection.get("facts"), "Phase0 F0002 facts"
    )
    require(
        set(facts) == {"base_stage", "head_stage"}
        and facts["base_stage"] in stages
        and facts["head_stage"] in stages
        and stages.index(facts["head_stage"]) < stages.index(facts["base_stage"]),
        "Phase0 F0002 facts do not satisfy the catalog order predicate",
    )
    f0002_group = find_group(mapping, "PHASE0-F0002")
    f0002_target = require_mapping(
        f0002_group.get("target"), "PHASE0-F0002 target"
    )
    f0002_bindings = require_mapping(
        f0002_target.get("fact_bindings"), "PHASE0-F0002 fact_bindings"
    )
    require(
        f0002_bindings.get("cross_field_predicate")
        == "ADOPTION_STAGES.index(head_stage) < ADOPTION_STAGES.index(base_stage)",
        "PHASE0-F0002 cross-field predicate is not exact",
    )
    require(
        f0002_bindings.get("on_unsatisfied_cross_field_predicate") == "REJECT",
        "PHASE0-F0002 must reject an unsatisfied cross-field predicate",
    )
    predicate_ref = require_mapping(
        f0002_bindings.get("catalog_condition_predicate_ref"),
        "PHASE0-F0002 catalog predicate ref",
    )
    require(
        predicate_ref
        == {
            "finding_code": "F0002",
            "field": "condition_predicate",
            "required_exact_value": f0002_predicate,
        },
        "PHASE0-F0002 does not bind the exact catalog predicate",
    )

    allowed_f0036_groups = {
        "AUX-SCHEMA-1341",
        "U-SCHEMA-NONMEANINGFUL-1329",
    }
    f0036_binding = require_mapping(
        findings["F0036"].get("source_binding"), "F0036 source_binding"
    )
    f0036_catalog_groups = {
        require_mapping(ref, "F0036 producer ref").get("group_id")
        for ref in require_list(
            f0036_binding.get("producer_groups"), "F0036 producer groups"
        )
    }
    require(
        f0036_catalog_groups == allowed_f0036_groups,
        "F0036 catalog source binding includes a non-schema producer",
    )
    f0036_leaf_groups: list[str] = []
    for row in mapping["semantic_mapping"]["group_rows"]:
        if any(
            leaf.get("kind") == "FINDING"
            and leaf.get("finding_code") == "F0036"
            for leaf in iter_semantic_leaves(row.get("target"))
        ):
            f0036_leaf_groups.append(row["group_id"])
    require(
        set(f0036_leaf_groups) == allowed_f0036_groups
        and len(f0036_leaf_groups) == 2,
        "mapping F0036 leaves are not restricted to the two schema producers",
    )

    register_callsite = "load_yaml@3620 in check_artifacts"
    register_finding_variants: list[tuple[str, str | None, str, str | None]] = []
    for row in mapping["semantic_mapping"]["group_rows"]:
        def visit(value: Any, variant_id: str | None = None) -> None:
            if isinstance(value, dict):
                selected_variant = (
                    value.get("variant_id", variant_id)
                    if isinstance(value.get("variant_id", variant_id), str)
                    else variant_id
                )
                if value.get("callsite_selector") == register_callsite:
                    target = value.get("target")
                    if isinstance(target, dict) and target.get("kind") == "FINDING":
                        fact_value = None
                        fact_bindings = target.get("fact_bindings")
                        if isinstance(fact_bindings, dict):
                            limit_binding = fact_bindings.get("bindings", {}).get(
                                "limit_kind"
                            )
                            if isinstance(limit_binding, dict):
                                fact_value = limit_binding.get("value")
                        register_finding_variants.append(
                            (
                                row["group_id"],
                                selected_variant,
                                target.get("finding_code"),
                                fact_value,
                            )
                        )
                        require(
                            target.get("owning_check_id")
                            == "adoption.document-parse"
                            and value.get("owning_check_id")
                            == "adoption.document-parse",
                            "register YAML parse variant is not owned by adoption.document-parse",
                        )
                for child in value.values():
                    visit(child, selected_variant)
            elif isinstance(value, list):
                for child in value:
                    visit(child, variant_id)
        visit(row.get("target"))

    expected_register_variants = {
        ("U-1242", None, "F0008", "BYTE_SIZE"),
        ("U-1253", None, "F0006", None),
        ("U-1255", "YAML_SYNTAX_OR_CONSTRUCTOR_INVALID", "F0005", None),
        ("U-1255", "YAML_NUMERIC_TOKEN_LIMIT_EXCEEDED", "F0008", "NUMERIC_VALUE"),
        ("U-1257", "YAML_DATA_MODEL_INVALID", "F0007", None),
        ("U-1257", "YAML_ALIAS_EXPANSION_LIMIT_EXCEEDED", "F0008", "ALIAS_EXPANSION"),
        ("U-1257", "YAML_NODE_COUNT_LIMIT_EXCEEDED", "F0008", "NODE_COUNT"),
        ("U-1257", "YAML_RECURSION_LIMIT_EXCEEDED", "F0008", "NESTING"),
        ("U-1257", "YAML_CONSTRUCTOR_VALUE_INVALID", "F0005", None),
        ("U-1257", "YAML_CONSTRUCTOR_OVERFLOW_INVALID", "F0005", None),
    }
    require(
        set(register_finding_variants) == expected_register_variants
        and len(register_finding_variants) == len(expected_register_variants),
        "register load_yaml@3620 finding variants/facts are not the exact bounded parse set",
    )


def build_normalized_inventory(
    catalog: dict[str, Any],
    mapping: dict[str, Any],
    analysis: dict[str, Any],
    workflows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the committed, reproducible inventory from exact source bytes."""

    validator_inventory = {
        "direct_emitters": analysis["direct_emitters"],
        "direct_emitter_function_count": analysis[
            "direct_emitter_function_count"
        ],
        "direct_emitter_levels": analysis["direct_emitter_levels"],
        "preliminary_upstream_producers": analysis[
            "preliminary_upstream_producers"
        ],
        "supplemental_upstream_producers": analysis[
            "supplemental_upstream_producers"
        ],
        "report_emit_return_lines": analysis["report_emit_return_lines"],
        "report_results_read_lines": analysis["report_results_read_lines"],
    }
    payload = {
        "exact_source": mapping["exact_source"],
        "validator_inventory": validator_inventory,
        "workflow_inventory": workflows,
    }
    return {
        "document_kind": "diagnostic_candidate_normalized_inventory",
        "review_data_format": 1,
        "scope": REVIEW_SCOPE,
        "runtime_contract": False,
        "ordinary_review_evidence_only": True,
        "candidate_lifecycle": {
            "acceptance_binding": None,
            "implementation_consumption_allowed": False,
            "implementation_parity_authorized": False,
            "runtime_ready": False,
        },
        "catalog_identity": {
            "decision_id": catalog["decision_id"],
            "catalog_id": catalog["catalog"]["catalog_id"],
            "catalog_revision": catalog["catalog"]["catalog_revision"],
            "mapping_revision": mapping["mapping_revision"],
        },
        "derivation_contract": {
            "version": 1,
            "implementation": "scripts/verify_diagnostic_catalog_candidate.py",
            "dependencies": "PYTHON_STANDARD_LIBRARY_ONLY",
            "source_selection": "EXACT_LOCAL_GIT_OBJECTS_ONLY_NO_FETCH_NO_CHECKOUT",
            "validator_parser": "PYTHON_AST",
            "direct_emitter_selector": "CALL_RECEIVER_NAME_REPORT_ATTRIBUTE_ERROR_WARN_OK",
            "preliminary_upstream_selector": {
                "return_functions": sorted(PRELIMINARY_RETURN_FUNCTIONS),
                "append_functions": sorted(PRELIMINARY_APPEND_FUNCTIONS),
            },
            "supplemental_upstream_selector": [
                "schema_errors list-comprehension item",
                "read_version_file error returns",
                "leading_pr_directives invalid/ambiguous assignments",
            ],
            "workflow_parser": "BOUNDED_GITHUB_ACTIONS_INDENTATION_SUBSET",
            "workflow_block_scalars": ["|", "|-", "|+"],
            "unknown_or_unsupported_source_shape": "REJECT",
            "payload_hash_spelling": "RFC8259_ASCII_SORTED_KEYS_NO_WHITESPACE",
            "file_spelling": "UTF8_SORTED_KEYS_INDENT_2_ONE_FINAL_LF",
        },
        "payload_sha256": sha256_bytes(canonical_json_bytes(payload)),
        **payload,
    }


def write_normalized_inventory(path: Path, value: dict[str, Any]) -> bytes:
    """Write an explicitly requested deterministic review artifact."""

    data = review_json_bytes(value)
    try:
        if path.exists() or path.is_symlink():
            metadata = path.lstat()
            require(
                stat.S_ISREG(metadata.st_mode) and not stat.S_ISLNK(metadata.st_mode),
                "--write-normalized-inventory target must be a regular file",
            )
        require(
            path.parent.resolve(strict=True).is_dir(),
            "--write-normalized-inventory parent must exist",
        )
        path.write_bytes(data)
    except VerificationError:
        raise
    except OSError as exc:
        fail(f"cannot write normalized inventory: {exc}")
    return data


def validate_normalized_inventory(
    path: Path,
    expected: dict[str, Any],
    *,
    write_path: Path | None,
) -> tuple[bytes, bool]:
    written = False
    if write_path is not None:
        require(
            path.resolve() == write_path.resolve(),
            "--inventory and --write-normalized-inventory must name the same file",
        )
        data = write_normalized_inventory(write_path, expected)
        written = True
    else:
        data = read_regular_file(path, "normalized inventory")
    actual = strict_json_bytes(data, "normalized inventory")
    require(actual == expected, "committed normalized inventory differs from exact derivation")
    require(
        data == review_json_bytes(expected),
        "normalized inventory does not use its deterministic review spelling",
    )
    return data, written


def validate_compatibility_changes(
    value: dict[str, Any],
    catalog: dict[str, Any],
    mapping: dict[str, Any],
) -> int:
    require(
        value.get("document_kind")
        == "diagnostic_catalog_compatibility_change_candidate",
        "unexpected compatibility-change document_kind",
    )
    require(
        value.get("review_data_format") == 1,
        "unsupported compatibility-change review_data_format",
    )
    require(
        value.get("runtime_contract") is False,
        "compatibility-change manifest must not be a runtime contract",
    )
    require(
        value.get("decision_id") == catalog.get("decision_id"),
        "compatibility-change decision ID mismatch",
    )
    lifecycle = require_mapping(
        value.get("candidate_lifecycle"),
        "compatibility-change candidate_lifecycle",
    )
    require(
        lifecycle.get("status") == "PROPOSED_REVIEW_DATA",
        "compatibility-change manifest must remain proposed review data",
    )
    require(
        lifecycle.get("acceptance_binding") is None
        and lifecycle.get("accepted") is False,
        "compatibility-change manifest must remain unaccepted",
    )
    for key in (
        "implementation_consumption_allowed",
        "implementation_parity_authorized",
        "runtime_ready",
        "migration_notes_are_current_runtime_instructions",
    ):
        require(
            lifecycle.get(key) is False,
            f"compatibility-change lifecycle.{key} must be false",
        )
    require(
        lifecycle.get("effective_only_after_external_exact_byte_acceptance")
        is True
        and lifecycle.get("later_acceptance_required") is True,
        "compatibility changes must require later exact-byte acceptance",
    )

    catalog_ref = require_mapping(
        value.get("catalog_ref"), "compatibility-change catalog_ref"
    )
    require(
        catalog_ref
        == {
            "catalog_id": catalog["catalog"]["catalog_id"],
            "catalog_revision": catalog["catalog"]["catalog_revision"],
        },
        "compatibility-change catalog_ref mismatch",
    )
    mapping_ref = require_mapping(
        value.get("mapping_ref"), "compatibility-change mapping_ref"
    )
    require(
        mapping_ref
        == {
            "mapping_revision": mapping["mapping_revision"],
            "legacy_release": mapping["exact_source"]["release"],
            "legacy_commit_sha1": mapping["exact_source"]["commit_sha1"],
        },
        "compatibility-change mapping_ref mismatch",
    )

    expected_codes = [
        finding["code"]
        for finding in catalog["findings"]["allocated_entries"]
        if finding.get("compatibility_disposition") == "INTENDED_CHANGE_PENDING"
    ]
    closed = require_mapping(
        value.get("closed_change_set"),
        "compatibility-change closed_change_set",
    )
    require(closed.get("closed") is True, "compatibility-change set is not closed")
    require(
        closed.get("selection_predicate")
        == "catalog-r1 finding compatibility_disposition equals INTENDED_CHANGE_PENDING",
        "compatibility-change selection predicate mismatch",
    )
    require(
        closed.get("count") == len(expected_codes)
        and closed.get("exact_codes") == expected_codes,
        "compatibility-change closed code set mismatch",
    )
    for key in ("on_missing_code", "on_extra_code", "on_duplicate_code"):
        require(
            closed.get(key) == "REJECT",
            f"compatibility-change {key} must be REJECT",
        )

    authority_sources = require_mapping(
        catalog.get("authority_sources"), "catalog.authority_sources"
    )
    entries = require_list(value.get("changes"), "compatibility changes")
    codes: list[str] = []
    required_entry_keys = {
        "code",
        "legacy_state_or_collapse",
        "proposed_v0_5_distinction",
        "rationale",
        "compatibility_impact",
        "migration_note",
        "authority_locators",
    }
    for index, raw_entry in enumerate(entries):
        entry = require_mapping(raw_entry, f"compatibility change[{index}]")
        require(
            set(entry) == required_entry_keys,
            f"compatibility change[{index}] has an unexpected shape",
        )
        code = require_string(entry.get("code"), f"compatibility change[{index}].code")
        codes.append(code)
        for key in (
            "legacy_state_or_collapse",
            "proposed_v0_5_distinction",
            "rationale",
            "compatibility_impact",
            "migration_note",
        ):
            require_string(entry.get(key), f"compatibility change {code}.{key}")
        locators = require_list(
            entry.get("authority_locators"),
            f"compatibility change {code}.authority_locators",
        )
        require(locators, f"compatibility change {code} has no authority locator")
        seen_locators: set[tuple[str, str, str]] = set()
        for raw_locator in locators:
            locator = require_mapping(
                raw_locator, f"compatibility change {code} authority locator"
            )
            require(
                set(locator) == {"source_id", "artifact", "locator"},
                f"compatibility change {code} has an unexpected authority-locator shape",
            )
            source_id = require_string(
                locator.get("source_id"),
                f"compatibility change {code} authority source",
            )
            require(
                source_id in authority_sources,
                f"compatibility change {code} has unknown authority source {source_id}",
            )
            identity = (
                source_id,
                require_string(locator.get("artifact"), f"compatibility change {code} artifact"),
                require_string(locator.get("locator"), f"compatibility change {code} locator"),
            )
            require(
                identity not in seen_locators,
                f"compatibility change {code} repeats an authority locator",
            )
            seen_locators.add(identity)
    require(codes == expected_codes, "compatibility-change entries differ from the exact pending set")
    require(len(codes) == len(set(codes)) == 33, "compatibility-change set must contain exactly 33 unique codes")

    authority_contract = require_mapping(
        value.get("authority_locator_contract"),
        "compatibility-change authority_locator_contract",
    )
    require(
        authority_contract.get("registry_artifact") == "catalog-r1.json"
        and authority_contract.get("registry_field") == "authority_sources",
        "compatibility-change authority registry binding mismatch",
    )
    require(
        authority_contract.get("legacy_runtime_locator_revision_sha1")
        == mapping["exact_source"]["commit_sha1"]
        and authority_contract.get("legacy_runtime_locator_path")
        == "scripts/validate.py",
        "compatibility-change runtime authority locator mismatch",
    )
    validator_hash = next(
        source["raw_sha256"]
        for source in mapping["exact_source"]["exact_runtime_sources"]
        if source["path"] == "scripts/validate.py"
    )
    require(
        authority_contract.get("legacy_runtime_raw_sha256") == validator_hash,
        "compatibility-change runtime authority hash mismatch",
    )
    return len(entries)


def validate_review_artifact_hash_references(
    catalog: dict[str, Any],
    mapping: dict[str, Any],
    *,
    inventory_hash: str,
    compatibility_hash: str | None,
) -> None:
    """Require the exact two-artifact cross-file binding in both candidates."""

    require(compatibility_hash is not None, "compatibility-change hash is unavailable")
    expected = [
        {
            "kind": "COMPATIBILITY_CHANGE_MANIFEST",
            "path": DEFAULT_COMPATIBILITY_CHANGES,
            "raw_sha256": compatibility_hash,
        },
        {
            "kind": "NORMALIZED_SOURCE_INVENTORY",
            "path": DEFAULT_INVENTORY,
            "raw_sha256": inventory_hash,
        },
    ]
    require(
        catalog.get("review_artifact_refs") == expected,
        "catalog review_artifact_refs do not exactly bind both review artifacts",
    )
    require(
        mapping.get("review_artifact_refs") == expected,
        "mapping review_artifact_refs do not exactly bind both review artifacts",
    )


def verify(
    repo_root: Path,
    catalog_path: Path,
    mapping_path: Path,
    compatibility_changes_path: Path,
    inventory_path: Path,
    *,
    write_inventory_path: Path | None = None,
) -> dict[str, Any]:
    catalog_bytes = read_regular_file(catalog_path, "catalog candidate")
    mapping_bytes = read_regular_file(mapping_path, "mapping candidate")
    compatibility_bytes = read_regular_file(
        compatibility_changes_path, "compatibility-change candidate"
    )
    catalog = strict_json_bytes(catalog_bytes, "catalog candidate")
    mapping = strict_json_bytes(mapping_bytes, "mapping candidate")
    compatibility_changes = strict_json_bytes(
        compatibility_bytes, "compatibility-change candidate"
    )
    git = GitObjects(repo_root)

    catalog_data = validate_catalog(catalog)
    require(mapping.get("document_kind") == "legacy_v0_4_0_diagnostic_mapping_decision_candidate", "unexpected mapping document_kind")
    require(mapping.get("review_data_format") == 1, "unsupported mapping review_data_format")
    require(mapping.get("runtime_contract") is False, "mapping must not be a runtime contract")
    require(mapping.get("decision_id") == catalog_data["decision_id"], "catalog/mapping decision ID mismatch")
    require(mapping.get("mapping_revision") == 1, "unsupported mapping revision")
    validate_candidate_lifecycle(mapping.get("candidate_lifecycle"), "mapping.candidate_lifecycle")

    catalog_ref = require_mapping(mapping.get("catalog_ref"), "mapping.catalog_ref")
    require(catalog_ref.get("catalog_id") == catalog_data["catalog_id"], "mapping catalog ID mismatch")
    require(catalog_ref.get("catalog_revision") == catalog_data["catalog_revision"], "mapping catalog revision mismatch")
    require(require_sha256(catalog_ref.get("raw_sha256_review_evidence"), "mapping catalog hash") == sha256_bytes(catalog_bytes), "mapping does not bind the supplied catalog bytes")

    forbidden = set(catalog["validation_contract"]["recursive_forbidden_candidate_keys"])
    for obj in walk_objects(mapping):
        present = forbidden.intersection(obj)
        require(not present, f"mapping contains forbidden candidate key(s): {sorted(present)}")

    sources, source_commit = validate_exact_source(git, catalog, mapping)
    authority_reference_count = validate_authority_sources(git, catalog, mapping)
    analysis = analyze_validator(sources["scripts/validate.py"])
    semantic_counts = validate_semantic_mapping(
        mapping, catalog_data, analysis, source_commit
    )
    validate_control_flow(mapping, analysis)
    workflows, workflow_jobs = validate_workflows(mapping, sources)
    source_line_counts = {
        path: len(data.decode("utf-8").splitlines()) for path, data in sources.items()
    }
    terminal_count = validate_terminal_mapping(
        mapping, catalog_data, workflow_jobs, source_line_counts
    )
    phase0_count = validate_phase0(git, catalog, mapping)
    validate_keystone_semantics(catalog, mapping)
    compatibility_change_count = validate_compatibility_changes(
        compatibility_changes, catalog, mapping
    )
    expected_inventory = build_normalized_inventory(
        catalog, mapping, analysis, workflows
    )
    inventory_bytes, inventory_written = validate_normalized_inventory(
        inventory_path,
        expected_inventory,
        write_path=write_inventory_path,
    )
    if write_inventory_path is None:
        validate_review_artifact_hash_references(
            catalog,
            mapping,
            inventory_hash=sha256_bytes(inventory_bytes),
            compatibility_hash=sha256_bytes(compatibility_bytes),
        )

    return {
        "status": "PASS",
        "scope": REVIEW_SCOPE,
        "catalog_sha256": sha256_bytes(catalog_bytes),
        "mapping_sha256": sha256_bytes(mapping_bytes),
        "compatibility_changes_sha256": sha256_bytes(compatibility_bytes),
        "normalized_inventory_sha256": sha256_bytes(inventory_bytes),
        "normalized_inventory_written": inventory_written,
        "source_commit_sha1": source_commit,
        "catalog_counts": {
            "public_checks": len(catalog_data["checks"]),
            "findings": len(catalog_data["findings"]),
            "reasons": len(catalog_data["reasons"]),
        },
        "inventory_counts": {
            key: value
            for key, value in semantic_counts.items()
            if key != "group_ids"
        },
        "control_flow_counts": {
            "report_emit_returns": len(analysis["report_emit_return_lines"]),
            "report_results_reads": len(analysis["report_results_read_lines"]),
        },
        "workflow_counts": {
            "workflows": len(workflows),
            "jobs": sum(int(item["job_count"]) for item in workflows),
            "steps": sum(int(item["step_count"]) for item in workflows),
        },
        "terminal_family_count": terminal_count,
        "phase0_case_count": phase0_count,
        "compatibility_change_count": compatibility_change_count,
        "authority_reference_count": authority_reference_count,
        "normalized_inventory_payload_sha256": expected_inventory[
            "payload_sha256"
        ],
        "limitations": [
            "does not accept the candidate or authorize runtime/parity use",
            "does not verify GitHub state, reviewer identity, or human authority",
            "does not authenticate the local Git executable or object database",
        ],
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Verify the review-only v0.5 diagnostic catalog candidate."
    )
    result.add_argument("--repo-root", type=Path, default=Path.cwd())
    result.add_argument("--catalog", type=Path)
    result.add_argument("--mapping", type=Path)
    result.add_argument("--compatibility-changes", type=Path)
    result.add_argument("--inventory", type=Path)
    result.add_argument("--write-normalized-inventory", type=Path)
    result.add_argument("--json", action="store_true", dest="json_output")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    repo_root = args.repo_root
    catalog_path = args.catalog or repo_root / DEFAULT_CATALOG
    mapping_path = args.mapping or repo_root / DEFAULT_MAPPING
    compatibility_changes_path = (
        args.compatibility_changes or repo_root / DEFAULT_COMPATIBILITY_CHANGES
    )
    inventory_path = args.inventory or repo_root / DEFAULT_INVENTORY
    write_inventory_path = args.write_normalized_inventory
    if write_inventory_path is not None and args.inventory is None:
        inventory_path = write_inventory_path
    try:
        report = verify(
            repo_root,
            catalog_path,
            mapping_path,
            compatibility_changes_path,
            inventory_path,
            write_inventory_path=write_inventory_path,
        )
    except VerificationError as exc:
        if args.json_output:
            print(
                json.dumps(
                    {"status": "FAIL", "scope": REVIEW_SCOPE, "error": str(exc)},
                    ensure_ascii=True,
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
        else:
            print(f"diagnostic catalog candidate verification: FAIL: {exc}", file=sys.stderr)
        return 1
    except Exception:
        # Review input must fail closed without leaking a traceback or ambient
        # exception details. Tests exercise this boundary with malformed data.
        if args.json_output:
            print(
                json.dumps(
                    {
                        "status": "FAIL",
                        "scope": REVIEW_SCOPE,
                        "error": "unexpected internal verification failure",
                    },
                    ensure_ascii=True,
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
        else:
            print(
                "diagnostic catalog candidate verification: FAIL: "
                "unexpected internal verification failure",
                file=sys.stderr,
            )
        return 1

    if args.json_output:
        print(
            json.dumps(
                report,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    else:
        print("diagnostic catalog candidate review verification: PASS")
        print(
            "review-only: no acceptance, runtime consumption, parity, or "
            "human-authority claim"
        )
        print(
            "inventory: "
            f"{report['inventory_counts']['direct_emitter_count']} emitters in "
            f"{report['inventory_counts']['direct_emitter_function_count']} functions; "
            f"{report['inventory_counts']['upstream_producer_count']} upstream producers; "
            f"{report['inventory_counts']['semantic_group_count']} semantic groups"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
