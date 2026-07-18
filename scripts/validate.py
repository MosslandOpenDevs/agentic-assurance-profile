#!/usr/bin/env python3
"""Validator for the OpenDevs Agentic Assurance Profile.

Dependencies: pyyaml, jsonschema (install with: pip install pyyaml jsonschema).
Requires Python 3.10 or later. Performs no network access.

Usage examples:

  Inside the central profile repository (validates the shipped templates,
  the VERSION file, and the schemas themselves):

      python scripts/validate.py self-check
      python scripts/validate.py self-check --repo-root . --json

  Inside an adopting repository, against the schemas of the pinned profile
  checkout (never the latest branch):

      python scripts/validate.py adopter \\
          --adoption .agentic-assurance/adoption.yaml \\
          --project-root . \\
          --schemas .assurance-profile-pin/schemas \\
          --profile-checkout .assurance-profile-pin

  The optional ``adoption_stage`` declared in the adoption file (absent
  means DRAFT) is self-binding: the declared stage's requirements are
  enforced as errors. ``--ignore-stage`` skips only that enforcement
  (structure-only validation).

  On a pull request, routing the change set against the optional
  ``components:`` map of the adoption file (impact routing):

      python scripts/validate.py drift \\
          --adoption .agentic-assurance/adoption.yaml \\
          --changed-files changed-files.txt \\
          --pr-body pr-body.txt

Output: human-readable lines prefixed ``ERROR:``, ``WARN:``, or ``OK:``.
Exit code is 1 if any error was reported, otherwise 0. With ``--json`` a
machine-readable summary is printed instead of the human-readable lines.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError:  # pragma: no cover
    print("ERROR: the 'jsonschema' package is required (pip install pyyaml jsonschema)")
    sys.exit(1)

JSON_SCHEMA_2020_12 = "https://json-schema.org/draft/2020-12/schema"

# The abolished pre-release version string must appear in no repository file
# (tracked or untracked-but-not-ignored), including this one, so it is
# assembled at runtime instead of written out.
FORBIDDEN_VERSION_STRING = "v0.1.0" + "-draft"

# Central repository VERSION file: "unreleased", a release tag, an -rc.N
# pre-release, or a -dev development marker. Adopter pins additionally
# forbid -dev; that stricter rule lives in schemas/adoption.schema.json.
VERSION_FILE_RE = re.compile(r"^(unreleased|v\d+\.\d+\.\d+(-rc\.\d+)?(-dev)?)$")

PLACEHOLDER_RE = re.compile(r"^REPLACE_WITH_[A-Z0-9_]+$")
PLACEHOLDER_SUBSTITUTIONS = {
    "REPLACE_WITH_FULL_40_CHARACTER_COMMIT_SHA": "0" * 40,
    "REPLACE_WITH_PINNED_VERSION": "unreleased",
    "REPLACE_WITH_OWNER_AND_REPOSITORY": "example/example",
}
DEFAULT_PLACEHOLDER_SUBSTITUTION = "placeholder"
DATE_PLACEHOLDER = "YYYY-MM-DD"
# A far-future date: substituted template dates must not trip the expired
# review_after semantic check (a template is not an overdue review).
DATE_SUBSTITUTION = "2999-01-01"

SCHEMA_FILES = (
    "adoption.schema.json",
    "claims.schema.json",
    "invariants.schema.json",
    "defeaters.schema.json",
    "residuals.schema.json",
    "assurance-lite.schema.json",
)

# Lite layout (adoption.yaml `layout: lite`): one consolidated assurance file
# instead of the split per-register files. The envelope schema types the prose
# fields; register entry shapes stay defined solely by the register schemas,
# against which the validator checks each section (no schema drift).
LITE_SCHEMA_FILE = "assurance-lite.schema.json"
LITE_ASSURANCE_PATH = ".agentic-assurance/assurance.yaml"
LITE_TEMPLATE = "assurance.yaml"
# Register sections a lite assurance file may carry, in output order.
LITE_SECTION_KINDS = ("invariants", "defeaters", "residuals")
# Lite is core-only; any other profile requires graduating to the split layout.
LITE_PROFILES = ("core", "archived")

# Artifact kind -> (schema file, default repository-relative path).
ARTIFACT_KINDS = {
    "claims": ("claims.schema.json", "assurance/CLAIMS.yaml"),
    "invariants": ("invariants.schema.json", "assurance/INVARIANTS.yaml"),
    "defeaters": ("defeaters.schema.json", "assurance/DEFEATERS.yaml"),
    "residuals": ("residuals.schema.json", "assurance/RESIDUALS.yaml"),
}

DEFAULT_PATHS = {
    "system": "assurance/SYSTEM.md",
    "invariants": "assurance/INVARIANTS.yaml",
    "claims": "assurance/CLAIMS.yaml",
    "defeaters": "assurance/DEFEATERS.yaml",
    "residuals": "assurance/RESIDUALS.yaml",
    "threat_model": "assurance/THREAT_MODEL.md",
    "evidence": "assurance/evidence",
}

PROVISIONAL_PROFILES = ("agent-runtime",)  # data-curation promoted in v0.2.0

# Adoption stages (adoption.yaml `adoption_stage`), lowest to highest. Stages
# are self-declared and self-binding: the validator enforces the declared
# stage's requirements as errors, so declaring a stage the artifacts do not
# meet fails validation. Absent means DRAFT, which adds no requirements.
ADOPTION_STAGES = ("DRAFT", "HUMAN_REVIEWED", "CONFORMANT")
# human_review fields that must be non-empty from stage HUMAN_REVIEWED on.
HUMAN_REVIEW_REQUIRED_FIELDS = ("date", "reviewer", "record")
# Fields that make a human_review.approvals entry attributable (CONFORMANT).
ATTRIBUTABLE_APPROVAL_FIELDS = ("approver", "review_url", "at")

# Register order used for deterministic semantic-check output.
REGISTER_KINDS = ("claims", "invariants", "defeaters", "residuals")

# Cross-reference fields: (source register, field name, target register).
REFERENCE_FIELDS = (
    ("claims", "invariants", "invariants"),
    ("claims", "defeaters", "defeaters"),
    ("claims", "residuals", "residuals"),
    ("invariants", "defeaters", "defeaters"),
    ("invariants", "residuals", "residuals"),
    ("defeaters", "affected_claims", "claims"),
    ("defeaters", "affected_invariants", "invariants"),
    ("residuals", "affected_claims", "claims"),
    ("residuals", "affected_invariants", "invariants"),
)

# Defeater statuses whose grounds must be recorded in `resolution`.
CLOSED_DEFEATER_STATUSES = ("RESOLVED", "MITIGATED", "WITHDRAWN")

# Impact routing (the optional `components:` map in adoption.yaml).
# A change set that touches anything under these prefixes counts as an
# assurance update for every touched component.
ASSURANCE_ARTIFACT_PREFIXES = ("assurance/", ".agentic-assurance/")
# Explicit no-impact statement in a PR description: the declaration line and
# a mandatory reason line, anywhere in the same body, in either order.
NO_IMPACT_RE = re.compile(r"^Assurance impact:\s*none", re.IGNORECASE | re.MULTILINE)
NO_IMPACT_REASON_RE = re.compile(r"^Reason:\s*\S+", re.IGNORECASE | re.MULTILINE)


class Report:
    """Collects ERROR/WARN/OK results and renders them."""

    def __init__(self) -> None:
        self.results: list[tuple[str, str]] = []

    def error(self, message: str) -> None:
        self.results.append(("error", message))

    def warn(self, message: str) -> None:
        self.results.append(("warn", message))

    def ok(self, message: str) -> None:
        self.results.append(("ok", message))

    @property
    def has_errors(self) -> bool:
        return any(level == "error" for level, _ in self.results)

    def emit(self, subcommand: str, as_json: bool) -> int:
        exit_code = 1 if self.has_errors else 0
        if as_json:
            counts = {
                level: sum(1 for lv, _ in self.results if lv == level)
                for level in ("error", "warn", "ok")
            }
            print(
                json.dumps(
                    {
                        "subcommand": subcommand,
                        "results": [
                            {"level": level, "message": message}
                            for level, message in self.results
                        ],
                        "counts": counts,
                        "exit_code": exit_code,
                    },
                    indent=2,
                )
            )
        else:
            for level, message in self.results:
                print(f"{level.upper()}: {message}")
        return exit_code


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def substitute_placeholders(node: object) -> object:
    """Replace template placeholder strings with type-appropriate dummies."""
    if isinstance(node, str):
        if node == DATE_PLACEHOLDER:
            return DATE_SUBSTITUTION
        if PLACEHOLDER_RE.match(node):
            return PLACEHOLDER_SUBSTITUTIONS.get(node, DEFAULT_PLACEHOLDER_SUBSTITUTION)
        return node
    if isinstance(node, list):
        return [substitute_placeholders(item) for item in node]
    if isinstance(node, dict):
        return {key: substitute_placeholders(value) for key, value in node.items()}
    return node


def find_placeholder_strings(node: object, path: str = "$") -> list[tuple[str, str]]:
    """Return (json_path, value) pairs for every remaining REPLACE_WITH_ token."""
    found: list[tuple[str, str]] = []
    if isinstance(node, str):
        if "REPLACE_WITH_" in node:
            found.append((path, node))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            found.extend(find_placeholder_strings(item, f"{path}[{index}]"))
    elif isinstance(node, dict):
        for key, value in node.items():
            found.extend(find_placeholder_strings(value, f"{path}.{key}"))
    return found


def normalize_yaml(node: object) -> object:
    """Map YAML-only scalar types onto the JSON data model.

    PyYAML parses an unquoted ``2026-12-31`` as ``datetime.date``; the schemas
    describe such fields as strings with ``format: date``, so dates are
    rendered back to their ISO form before validation.
    """
    if isinstance(node, datetime.datetime):
        return node.isoformat()
    if isinstance(node, datetime.date):
        return node.isoformat()
    if isinstance(node, list):
        return [normalize_yaml(item) for item in node]
    if isinstance(node, dict):
        return {key: normalize_yaml(value) for key, value in node.items()}
    return node


def load_yaml(path: Path) -> tuple[object, str | None]:
    """Load a YAML file; return (document, error_message)."""
    try:
        with path.open(encoding="utf-8") as handle:
            return normalize_yaml(yaml.safe_load(handle)), None
    except OSError as exc:
        return None, f"cannot read {path}: {exc}"
    except yaml.YAMLError as exc:
        return None, f"cannot parse {path} as YAML: {exc}"
    except RecursionError:
        return None, f"cannot process {path}: recursive YAML aliases are not supported"


def load_json(path: Path) -> tuple[object, str | None]:
    """Load a JSON file; return (document, error_message)."""
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle), None
    except OSError as exc:
        return None, f"cannot read {path}: {exc}"
    except json.JSONDecodeError as exc:
        return None, f"cannot parse {path} as JSON: {exc}"


def schema_errors(instance: object, schema: dict, label: str) -> list[str]:
    """Validate an instance against a schema; return formatted error messages."""
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    messages = []
    for error in sorted(validator.iter_errors(instance), key=lambda e: e.json_path):
        messages.append(f"{label}: {error.json_path}: {error.message}")
    return messages


def listed_files(repo_root: Path) -> list[Path]:
    """Files to scan: tracked plus untracked-but-not-ignored (fallback: walk)."""
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), "ls-files", "--cached", "--others", "--exclude-standard"],
            capture_output=True,
            text=True,
            check=True,
        )
        paths = [repo_root / line for line in completed.stdout.splitlines() if line]
        return [path for path in paths if path.is_file()]
    except (OSError, subprocess.CalledProcessError):
        return [
            path
            for path in repo_root.rglob("*")
            if path.is_file() and ".git" not in path.relative_to(repo_root).parts
        ]


def entries_with_restricted_disclosure(document: object) -> list[tuple[str, str]]:
    """Return (entry_id, disclosure) for entries classified RESTRICTED or EMBARGOED."""
    flagged: list[tuple[str, str]] = []
    if not isinstance(document, dict):
        return flagged
    for value in document.values():
        if not isinstance(value, list):
            continue
        for entry in value:
            if not isinstance(entry, dict):
                continue
            disclosure = entry.get("disclosure")
            if disclosure in ("RESTRICTED", "EMBARGOED"):
                flagged.append((str(entry.get("id", "<no id>")), disclosure))
    return flagged


def resolve_paths(adoption: dict) -> dict[str, str]:
    """Resolve artifact paths from adoption.yaml, defaulting per the profile."""
    resolved = dict(DEFAULT_PATHS)
    declared = adoption.get("paths")
    if isinstance(declared, dict):
        for key, value in declared.items():
            if isinstance(value, str):
                resolved[key] = value
    return resolved


def check_declared_paths(
    project_root: Path, paths: dict[str, str], report: Report
) -> dict[str, str]:
    """Reject declared artifact paths that resolve outside the project root.

    Absolute values or ``..`` traversal in ``paths:`` would otherwise escape
    ``--project-root`` (pathlib's ``/`` discards the left operand for absolute
    right operands). Offending keys are reported as errors and dropped so that
    no later check reads or accepts such files.
    """
    root = project_root.resolve()
    safe: dict[str, str] = {}
    for key, value in paths.items():
        if (project_root / value).resolve().is_relative_to(root):
            safe[key] = value
        else:
            report.error(f"paths.{key}: {value!r} resolves outside the project root")
    return safe


def read_version_file(path: Path) -> tuple[str | None, str | None]:
    """Read a VERSION file; return (content, error_message)."""
    try:
        return path.read_text(encoding="utf-8").strip(), None
    except OSError as exc:
        return None, f"cannot read {path}: {exc}"


def register_entries(document: object, kind: str) -> list | None:
    """Extract the entry list of a register document, or None if unusable."""
    if isinstance(document, dict) and isinstance(document.get(kind), list):
        return document[kind]
    return None


def nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def compile_path_glob(pattern: str) -> re.Pattern[str]:
    """Compile a gitwildmatch-style glob into an anchored full-path regex.

    Supported subset: ``**/`` (any leading directories, including none),
    ``**`` (anything, across directory separators), ``*`` (anything within
    one path segment), ``?`` (one character within a segment). Everything
    else matches literally. The pattern is matched against the entire
    repository-relative path (use ``fullmatch``), so ``src/auth/**`` matches
    ``src/auth/deep/nested.ts`` but not ``src/authx/file.ts``.
    """
    parts: list[str] = []
    index = 0
    while index < len(pattern):
        if pattern.startswith("**/", index):
            parts.append("(?:.*/)?")
            index += 3
        elif pattern.startswith("**", index):
            parts.append(".*")
            index += 2
        elif pattern[index] == "*":
            parts.append("[^/]*")
            index += 1
        elif pattern[index] == "?":
            parts.append("[^/]")
            index += 1
        else:
            parts.append(re.escape(pattern[index]))
            index += 1
    return re.compile("".join(parts))


def coerce_date(value: object) -> datetime.date | None:
    """Coerce a YAML date value to datetime.date, or None if it is not one.

    The loader normalizes ``datetime.date`` to ISO strings, but raw objects
    are handled too in case a caller passes an unnormalized document.
    """
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value.strip())
        except ValueError:
            return None
    return None


# ---------------------------------------------------------------------------
# Semantic checks (shared by self-check and adopter)
# ---------------------------------------------------------------------------


def check_semantics(
    registers: dict[str, list | None],
    report: Report,
    strict_review_dates: bool = False,
    today: datetime.date | None = None,
    ok_label: str = "semantic checks",
) -> None:
    """Cross-entry semantic checks over the four registers.

    ``registers`` maps a register kind to its entry list. Three states are
    encoded: key absent = the register file does not exist; value ``None`` =
    the file exists but is unusable (a load or structure error was already
    reported); value list = usable entries (placeholders substituted).

    Checks: unique IDs, cross-reference integrity, VERIFIED critical
    invariants carry enforcement and verification, INTENDED invariants carry
    intent.authority, ACCEPTED high/critical residuals carry
    acceptance_rationale, RESOLVED/closed entries carry their grounds, and
    passed review_after dates (WARN, or ERROR with ``strict_review_dates``).

    Deliberate design decision: a VERIFIED critical invariant is NOT required
    to carry intent.authority — conclusion status and intent classification
    are independent axes (PROFILE.md section 4). Authority is required by the
    INTENDED classification alone, at any severity.
    """
    if today is None:
        today = datetime.date.today()
    errors_before = sum(1 for level, _ in report.results if level == "error")

    usable = {
        kind: entries
        for kind, entries in registers.items()
        if entries is not None
    }

    def entry_label(entry: object) -> str:
        if isinstance(entry, dict) and nonempty_string(entry.get("id")):
            return entry["id"]
        return "<no id>"

    def entries_of(kind: str) -> list[dict]:
        return [entry for entry in usable.get(kind, []) if isinstance(entry, dict)]

    # 1. Duplicate IDs, within each register and across all registers.
    # Entry positions in messages are 1-based.
    first_seen: dict[str, tuple[str, int]] = {}
    for kind in REGISTER_KINDS:
        for index, entry in enumerate(usable.get(kind) or [], start=1):
            if not isinstance(entry, dict):
                continue
            entry_id = entry.get("id")
            if not nonempty_string(entry_id):
                continue
            if entry_id in first_seen:
                seen_kind, seen_index = first_seen[entry_id]
                if seen_kind == kind:
                    where = f"{kind} entry {seen_index} and {index}"
                else:
                    where = f"{seen_kind} entry {seen_index} and {kind} entry {index}"
                report.error(f"duplicate id {entry_id} ({where})")
            else:
                first_seen[entry_id] = (kind, index)

    # 2. Cross-reference integrity. A dangling reference into an existing
    # register is an error; a reference into a register whose file does not
    # exist at all (legitimate under e.g. the core profile) is a warning.
    ids_by_kind = {
        kind: {
            entry["id"]
            for entry in entries_of(kind)
            if nonempty_string(entry.get("id"))
        }
        for kind in usable
    }
    for source_kind, field, target_kind in REFERENCE_FIELDS:
        for entry in entries_of(source_kind):
            references = entry.get(field)
            if not isinstance(references, list):
                continue
            for reference in references:
                if not isinstance(reference, str):
                    continue
                if target_kind not in registers:
                    report.warn(
                        f"{source_kind} entry {entry_label(entry)}: reference to "
                        f"{reference} but no {target_kind} register exists"
                    )
                elif registers[target_kind] is None:
                    continue  # target file exists but is unusable; already reported
                elif reference not in ids_by_kind.get(target_kind, set()):
                    report.error(
                        f"{source_kind} entry {entry_label(entry)}: reference to "
                        f"{reference}, which does not exist in the "
                        f"{target_kind} register"
                    )

    # 3 and 4. Invariant checks.
    for entry in entries_of("invariants"):
        label = entry_label(entry)
        # 3. A VERIFIED critical invariant must name the mechanisms behind the
        # verdict. intent.authority is deliberately not required here (see the
        # docstring): status and intent are independent axes per PROFILE.md
        # section 4; authority is check 4's concern, keyed on INTENDED alone.
        if entry.get("status") == "VERIFIED" and entry.get("severity") == "critical":
            for list_name in ("enforcement", "verification"):
                value = entry.get(list_name)
                if not (isinstance(value, list) and value):
                    report.error(
                        f"invariant {label} is VERIFIED with severity critical "
                        f"but its {list_name} list is empty"
                    )
        # 4. INTENDED requires a recorded human authority, at any severity.
        intent = entry.get("intent")
        if isinstance(intent, dict) and intent.get("classification") == "INTENDED":
            if not nonempty_string(intent.get("authority")):
                report.error(
                    f"invariant {label} has intent.classification INTENDED "
                    "but intent.authority is empty or null"
                )

    # 5 and 6a. Residual dispositions must be grounded.
    for entry in entries_of("residuals"):
        label = entry_label(entry)
        status = entry.get("status")
        impact = entry.get("impact")
        if status == "ACCEPTED" and impact in ("high", "critical"):
            if not nonempty_string(entry.get("acceptance_rationale")):
                report.error(
                    f"residual {label} is ACCEPTED with impact {impact} "
                    "but acceptance_rationale is empty or missing"
                )
        if status == "RESOLVED" and not nonempty_string(entry.get("resolution_note")):
            report.error(
                f"residual {label} is RESOLVED but resolution_note is empty or missing"
            )

    # 6b. Closed defeaters must record how they were closed.
    for entry in entries_of("defeaters"):
        status = entry.get("status")
        if status in CLOSED_DEFEATER_STATUSES and not nonempty_string(
            entry.get("resolution")
        ):
            report.error(
                f"defeater {entry_label(entry)} is {status} "
                "but resolution is empty or missing"
            )

    # 7. Passed review_after dates (defeaters and residuals).
    for kind in ("defeaters", "residuals"):
        for entry in entries_of(kind):
            review_after = coerce_date(entry.get("review_after"))
            if review_after is not None and review_after < today:
                message = (
                    f"review_after {review_after.isoformat()} has passed — "
                    f"re-review {entry_label(entry)}"
                )
                if strict_review_dates:
                    report.error(message)
                else:
                    report.warn(message)

    errors_after = sum(1 for level, _ in report.results if level == "error")
    if errors_after == errors_before:
        report.ok(f"{ok_label} — ids unique, references resolve, statuses grounded")


def check_lite_sections(
    document: object,
    label: str,
    schemas: dict[str, dict],
    report: Report,
    schema_label_prefix: str = "",
) -> dict[str, list | None]:
    """Validate the register sections of a lite assurance document.

    Register entry shapes are defined solely by the register schemas: each
    present section is extracted into a synthetic register document
    (``{version: 1, <kind>: [...]}``) and validated against the corresponding
    register schema, so nothing is duplicated in the lite envelope schema.

    Returns the same kind -> entries mapping ``check_artifacts`` produces for
    the split layout: key absent = section absent, value ``None`` = section
    unusable, value list = usable entries. Feed it to ``check_semantics``.
    """
    registers: dict[str, list | None] = {}
    if not isinstance(document, dict):
        return registers
    for kind in LITE_SECTION_KINDS:
        if kind not in document:
            continue
        schema_name, _default = ARTIFACT_KINDS[kind]
        synthetic = {"version": 1, kind: document[kind]}
        registers[kind] = register_entries(synthetic, kind)
        schema = schemas.get(schema_name)
        if schema is None:
            report.error(
                f"{label}: section '{kind}' cannot be validated, "
                f"{schema_label_prefix}{schema_name} unusable"
            )
            continue
        errors = schema_errors(synthetic, schema, f"{label}: section '{kind}'")
        if errors:
            for message in errors:
                report.error(message)
        else:
            report.ok(
                f"{label}: section '{kind}' items validate against "
                f"{schema_label_prefix}{schema_name}"
            )
    return registers


# ---------------------------------------------------------------------------
# self-check subcommand (central repository)
# ---------------------------------------------------------------------------


def check_version_file(repo_root: Path, report: Report) -> None:
    version_path = repo_root / "VERSION"
    content, error = read_version_file(version_path)
    if error is not None:
        report.error(f"VERSION file: {error}")
        return
    if VERSION_FILE_RE.fullmatch(content):
        report.ok(f"VERSION file is '{content}'")
    else:
        report.error(
            f"VERSION file contains '{content}', which does not match "
            "'unreleased', 'vMAJOR.MINOR.PATCH', an '-rc.N' pre-release, or a '-dev' marker"
        )


def check_schemas_parse(repo_root: Path, report: Report) -> dict[str, dict]:
    schemas: dict[str, dict] = {}
    for name in SCHEMA_FILES:
        path = repo_root / "schemas" / name
        document, error = load_json(path)
        if error is not None:
            report.error(f"schemas/{name}: {error}")
            continue
        if not isinstance(document, dict):
            report.error(f"schemas/{name}: top level is not a JSON object")
            continue
        if document.get("$schema") != JSON_SCHEMA_2020_12:
            report.error(
                f"schemas/{name}: '$schema' is {document.get('$schema')!r}, "
                f"expected {JSON_SCHEMA_2020_12!r}"
            )
            continue
        report.ok(f"schemas/{name} parses and declares JSON Schema draft 2020-12")
        schemas[name] = document
    return schemas


def check_template(
    repo_root: Path, template: str, schema_name: str, schemas: dict[str, dict], report: Report
) -> object:
    """Validate one template; return the placeholder-substituted document.

    Returns None when the template cannot be loaded or the schema is
    unusable, so the caller can feed register templates to the semantic
    checks only when a document is actually available.
    """
    schema = schemas.get(schema_name)
    if schema is None:
        report.error(f"templates/{template}: cannot validate, schemas/{schema_name} unusable")
        return None
    document, error = load_yaml(repo_root / "templates" / template)
    if error is not None:
        report.error(f"templates/{template}: {error}")
        return None
    substituted = substitute_placeholders(document)
    errors = schema_errors(substituted, schema, f"templates/{template}")
    if errors:
        for message in errors:
            report.error(message)
    else:
        report.ok(
            f"templates/{template} validates against schemas/{schema_name} "
            "(placeholders substituted)"
        )
    return substituted


def check_lite_template(repo_root: Path, schemas: dict[str, dict], report: Report) -> None:
    """Validate templates/assurance.yaml through the lite-layout flow.

    Mirrors what an adopter's ``.agentic-assurance/assurance.yaml`` faces:
    envelope validation against the lite schema, per-section validation
    against the register schemas, and the shared semantic checks.
    """
    label = f"templates/{LITE_TEMPLATE}"
    schema = schemas.get(LITE_SCHEMA_FILE)
    if schema is None:
        report.error(f"{label}: cannot validate, schemas/{LITE_SCHEMA_FILE} unusable")
        return
    document, error = load_yaml(repo_root / "templates" / LITE_TEMPLATE)
    if error is not None:
        report.error(f"{label}: {error}")
        return
    substituted = substitute_placeholders(document)
    errors = schema_errors(substituted, schema, label)
    if errors:
        for message in errors:
            report.error(message)
    else:
        report.ok(
            f"{label} validates against schemas/{LITE_SCHEMA_FILE} "
            "(placeholders substituted)"
        )
    registers = check_lite_sections(
        substituted, label, schemas, report, schema_label_prefix="schemas/"
    )
    check_semantics(registers, report, ok_label=f"{label} semantic checks")


def check_forbidden_string(repo_root: Path, report: Report) -> None:
    """Check that no repository file contains the abolished version string.

    A repository file is one that is tracked or untracked-but-not-ignored
    (per .gitignore), matching ``listed_files``; the scan therefore works
    before files are committed as well as in CI.
    """
    offenders = []
    for path in listed_files(repo_root):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue  # unreadable or binary
        if FORBIDDEN_VERSION_STRING in text:
            offenders.append(path.relative_to(repo_root))
    if offenders:
        for offender in offenders:
            report.error(
                f"{offender}: contains the abolished version string "
                f"'{FORBIDDEN_VERSION_STRING}'"
            )
    else:
        report.ok(
            f"no repository file contains the abolished version string "
            f"'{FORBIDDEN_VERSION_STRING}'"
        )


def run_self_check(args: argparse.Namespace) -> int:
    report = Report()
    if args.repo_root is not None:
        repo_root = Path(args.repo_root).resolve()
    else:
        repo_root = Path(__file__).resolve().parent.parent

    check_version_file(repo_root, report)
    schemas = check_schemas_parse(repo_root, report)
    check_template(repo_root, "adoption.yaml", "adoption.schema.json", schemas, report)
    registers = {
        kind: register_entries(
            check_template(repo_root, template, schema_name, schemas, report), kind
        )
        for kind, template, schema_name in (
            ("claims", "CLAIMS.yaml", "claims.schema.json"),
            ("invariants", "INVARIANTS.yaml", "invariants.schema.json"),
            ("defeaters", "DEFEATERS.yaml", "defeaters.schema.json"),
            ("residuals", "RESIDUALS.yaml", "residuals.schema.json"),
        )
    }
    # The register templates ship together, so all four kinds are treated as
    # existing; template drift is caught by the same semantic checks that
    # adopter registers face.
    check_semantics(registers, report)
    check_lite_template(repo_root, schemas, report)
    check_forbidden_string(repo_root, report)

    return report.emit("self-check", args.json)


# ---------------------------------------------------------------------------
# adopter subcommand (adopting repository, pinned profile checkout)
# ---------------------------------------------------------------------------


def load_adopter_schemas(schemas_dir: Path, report: Report) -> dict[str, dict]:
    schemas: dict[str, dict] = {}
    for name in SCHEMA_FILES:
        document, error = load_json(schemas_dir / name)
        if error is not None:
            report.error(f"schema {name}: {error}")
        elif not isinstance(document, dict):
            report.error(f"schema {name}: top level is not a JSON object")
        else:
            schemas[name] = document
    return schemas


def check_adoption_document(
    adoption_path: Path, schemas: dict[str, dict], report: Report
) -> dict | None:
    document, error = load_yaml(adoption_path)
    if error is not None:
        report.error(f"adoption file: {error}")
        return None
    if not isinstance(document, dict):
        report.error(f"adoption file {adoption_path}: top level is not a mapping")
        return None

    # Strict: the adoption declaration must be fully filled in. No
    # placeholder substitution is applied here.
    for json_path, value in find_placeholder_strings(document):
        report.error(f"adoption file: unfilled placeholder {value!r} at {json_path}")

    schema = schemas.get("adoption.schema.json")
    if schema is None:
        report.error("adoption file: cannot validate, adoption.schema.json unusable")
    else:
        errors = schema_errors(document, schema, "adoption file")
        if errors:
            for message in errors:
                report.error(message)
        else:
            report.ok("adoption file validates against adoption.schema.json")
    return document


def check_pinned_version(adoption: dict, profile_checkout: Path, report: Report) -> None:
    upstream = adoption.get("upstream")
    pinned = upstream.get("version") if isinstance(upstream, dict) else None
    if not isinstance(pinned, str):
        report.error(
            "cannot compare pinned version with profile checkout: "
            "upstream.version is missing or not a string"
        )
        return
    declared, error = read_version_file(profile_checkout / "VERSION")
    if error is not None:
        report.error(f"profile checkout VERSION file: {error}")
        return
    if pinned == declared:
        report.ok(f"pinned version matches the profile checkout VERSION file ('{declared}')")
    else:
        report.error(
            f"version/commit mismatch: pinned version {pinned} "
            f"but pinned commit declares {declared}"
        )


def check_artifacts(
    project_root: Path, paths: dict[str, str], schemas: dict[str, dict], report: Report
) -> dict[str, list | None]:
    """Schema-validate present registers; return them for the semantic checks.

    The returned mapping holds an entry per register whose file exists:
    the entry list (placeholders substituted) when the document is usable,
    else None. Registers whose file is absent are omitted entirely, so the
    semantic checks can distinguish a dangling reference from a reference
    into a register the adopter legitimately does not keep.
    """
    registers: dict[str, list | None] = {}
    for kind, (schema_name, _default) in ARTIFACT_KINDS.items():
        relative = paths.get(kind)
        if relative is None:
            continue  # rejected by check_declared_paths; error already reported
        path = project_root / relative
        if not path.is_file():
            continue  # presence is checked per profile, not here
        document, error = load_yaml(path)
        if error is not None:
            report.error(f"{relative}: {error}")
            registers[kind] = None
            continue
        # Template placeholder values are tolerated in artifact registers so
        # that freshly copied templates validate; substitution mirrors
        # self-check. The adoption declaration itself remains strict.
        substituted = substitute_placeholders(document)
        registers[kind] = register_entries(substituted, kind)
        schema = schemas.get(schema_name)
        if schema is None:
            report.error(f"{relative}: cannot validate, {schema_name} unusable")
            continue
        errors = schema_errors(substituted, schema, relative)
        if errors:
            for message in errors:
                report.error(message)
        else:
            report.ok(f"{relative} validates against {schema_name}")
        for entry_id, disclosure in entries_with_restricted_disclosure(document):
            report.warn(
                f"{relative}: entry {entry_id} has disclosure {disclosure} — "
                "public repositories must not contain restricted material — "
                "verify this file is not public"
            )
    return registers


def check_required_files(
    project_root: Path, paths: dict[str, str], profiles: list[str], report: Report
) -> None:
    for name in ("AGENTIC_ASSURANCE.md", "AGENTS.md"):
        if (project_root / name).is_file():
            report.ok(f"{name} present at project root")
        else:
            report.error(f"{name} missing at project root")

    def require(key: str, reason: str) -> None:
        relative = paths.get(key)
        if relative is None:
            return  # rejected by check_declared_paths; error already reported
        if (project_root / relative).is_file():
            report.ok(f"{relative} present (paths.{key}, required for {reason})")
        else:
            report.error(f"{relative} missing (paths.{key}, required for {reason})")

    if any(profile != "archived" for profile in profiles):
        require("system", "non-archived profiles")
        require("residuals", "non-archived profiles")
    if "service" in profiles:
        require("invariants", "profile 'service'")
        require("threat_model", "profile 'service'")
    if "trust-critical" in profiles:
        require("claims", "profile 'trust-critical'")
        defeaters = paths.get("defeaters")
        if defeaters is not None and not (project_root / defeaters).is_file():
            report.warn(
                f"profile 'trust-critical' selected but no defeaters file at "
                f"{defeaters}"
            )


def check_adopter_warnings(project_root: Path, profiles: list[str], report: Report) -> None:
    issue_template_dir = project_root / ".github" / "ISSUE_TEMPLATE"
    if issue_template_dir.is_dir() and not (issue_template_dir / "config.yml").is_file():
        report.warn(
            ".github/ISSUE_TEMPLATE exists without config.yml — local issue "
            "templates disable the entire org default set including config.yml"
        )
    for profile in profiles:
        if profile in PROVISIONAL_PROFILES:
            report.warn(
                f"profile '{profile}' is provisional — obligations may change "
                "in a minor release"
            )


def check_lite_profiles(profiles: list[str], report: Report) -> None:
    """Layout 'lite' is core-only; richer profiles need the split layout."""
    beyond_core = [profile for profile in profiles if profile not in LITE_PROFILES]
    if beyond_core:
        listed = ", ".join(f"'{profile}'" for profile in beyond_core)
        report.error(
            f"layout 'lite' supports only the core and archived profiles, but "
            f"profiles include {listed} — graduate to the split layout "
            f"(split-out preserves IDs: move the section arrays of "
            f"{LITE_ASSURANCE_PATH} into assurance/INVARIANTS.yaml etc. "
            "and drop layout: lite)"
        )
    else:
        report.ok("layout 'lite' is declared with core-only profiles")


def check_lite_file(
    project_root: Path, schemas: dict[str, dict], report: Report
) -> tuple[dict | None, dict[str, list | None]]:
    """Load and validate the single lite assurance file.

    The path is fixed at ``.agentic-assurance/assurance.yaml`` — the lite
    layout has exactly one assurance file, next to the adoption declaration.
    Returns ``(document, registers)``: the placeholder-substituted document
    (None when missing or unusable) and the same kind -> entries mapping the
    split layout's ``check_artifacts`` returns, for ``check_semantics``.
    """
    relative = LITE_ASSURANCE_PATH
    path = project_root / relative
    if not path.is_file():
        report.error(f"{relative} missing (required by layout 'lite')")
        return None, {}
    document, error = load_yaml(path)
    if error is not None:
        report.error(f"{relative}: {error}")
        return None, {}
    # Template placeholder values are tolerated, as in the split-layout
    # registers, so a freshly copied template validates; the adoption
    # declaration itself remains strict.
    substituted = substitute_placeholders(document)
    schema = schemas.get(LITE_SCHEMA_FILE)
    if schema is None:
        report.error(f"{relative}: cannot validate, {LITE_SCHEMA_FILE} unusable")
    else:
        errors = schema_errors(substituted, schema, relative)
        if errors:
            for message in errors:
                report.error(message)
        else:
            report.ok(f"{relative} validates against {LITE_SCHEMA_FILE}")
    registers = check_lite_sections(substituted, relative, schemas, report)
    for entry_id, disclosure in entries_with_restricted_disclosure(document):
        report.warn(
            f"{relative}: entry {entry_id} has disclosure {disclosure} — "
            "public repositories must not contain restricted material — "
            "verify this file is not public"
        )
    if not isinstance(substituted, dict):
        return None, registers
    return substituted, registers


def check_lite_required_files(
    project_root: Path,
    paths: dict[str, str],
    lite_document: dict | None,
    report: Report,
) -> None:
    """Presence checks for layout 'lite'.

    AGENTIC_ASSURANCE.md and AGENTS.md stay required at the project root.
    The residuals obligation is carried by the assurance file itself (its
    schema requires the section). The system description must come from
    either the file's `system` section or an existing paths.system file.
    The split layout's per-profile file checks do not apply.
    """
    for name in ("AGENTIC_ASSURANCE.md", "AGENTS.md"):
        if (project_root / name).is_file():
            report.ok(f"{name} present at project root")
        else:
            report.error(f"{name} missing at project root")

    has_system_section = isinstance(lite_document, dict) and nonempty_string(
        lite_document.get("system")
    )
    system_relative = paths.get("system")
    has_system_file = (
        system_relative is not None and (project_root / system_relative).is_file()
    )
    if has_system_section:
        report.ok(
            f"system description present ('system' section of {LITE_ASSURANCE_PATH})"
        )
    elif has_system_file:
        report.ok(
            f"{system_relative} present (paths.system, system description "
            "for layout 'lite')"
        )
    else:
        report.error(
            "system description missing: layout 'lite' requires a 'system' "
            f"section in {LITE_ASSURANCE_PATH} or a file at paths.system"
        )


def check_component_map(
    adoption: dict, registers: dict[str, list | None], report: Report
) -> None:
    """Cross-check the optional `components:` impact-routing map.

    Shape errors are the adoption schema's concern; this check resolves the
    references: every ``components.<name>.invariants`` ID must exist in the
    loaded invariant register. ``registers`` is the same mapping the split
    layout's ``check_artifacts`` and the lite layout's ``check_lite_file``
    produce, so both layouts are covered. A register file that exists but is
    unusable was already reported; its references are skipped, and no OK line
    is claimed for the map in that case.
    """
    components = adoption.get("components")
    if not isinstance(components, dict) or not components:
        return
    register_exists = "invariants" in registers
    register_unusable = register_exists and registers["invariants"] is None
    known_ids = {
        entry["id"]
        for entry in (registers.get("invariants") or [])
        if isinstance(entry, dict) and nonempty_string(entry.get("id"))
    }
    errors_before = sum(1 for level, _ in report.results if level == "error")
    for name, component in components.items():
        if not isinstance(component, dict):
            continue  # rejected by the adoption schema; error already reported
        references = component.get("invariants")
        if not isinstance(references, list):
            continue  # rejected by the adoption schema; error already reported
        for reference in references:
            if not isinstance(reference, str):
                continue
            if not register_exists:
                report.error(
                    f"components.{name}: references invariant {reference} "
                    "but no invariant register exists"
                )
            elif register_unusable:
                continue  # register file exists but is unusable; already reported
            elif reference not in known_ids:
                report.error(
                    f"components.{name}: references invariant {reference}, "
                    "which does not exist in the invariant register"
                )
    errors_after = sum(1 for level, _ in report.results if level == "error")
    if errors_after == errors_before and not register_unusable:
        count = len(components)
        plural = "component" if count == 1 else "components"
        report.ok(
            f"component map: {count} {plural} — every invariant reference resolves"
        )


def check_adoption_stage(
    adoption: dict,
    adoption_path: Path,
    project_root: Path,
    paths: dict[str, str],
    registers: dict[str, list | None],
    report: Report,
) -> None:
    """Enforce the requirements of the self-declared ``adoption_stage``.

    Runs after every structural check. Stage DRAFT (or an absent
    ``adoption_stage``) adds no requirements and emits nothing, keeping the
    output identical to a validator without stages. Each higher stage
    includes every lower stage's requirements; an error line is prefixed
    with the stage that *introduces* the failed requirement, so a
    CONFORMANT declaration failing a HUMAN_REVIEWED requirement names the
    rung of the ladder it actually falls off.

    HUMAN_REVIEWED: no unfilled ``REPLACE_WITH_`` placeholder anywhere in
    the adoption file or any loaded register (the raw, unsubstituted
    documents are re-scanned — the split registers that exist, or the lite
    assurance file), and a ``human_review`` block with non-empty ``date``,
    ``reviewer``, and ``record``.

    CONFORMANT: additionally, every severity-critical invariant has a
    decided (non-UNKNOWN) ``intent.classification``, and
    ``human_review.approvals`` carries at least one attributable entry —
    ``approver``, ``review_url``, and ``at`` all non-empty. Passed
    ``review_after`` dates are also errors at this stage; that requirement
    is enforced inside ``check_semantics`` (as if ``--strict-review-dates``
    had been passed), so those lines carry no stage prefix — here they only
    count against the success verdict. Whether
    ``review_url`` really is an approved review by a non-author is not
    verified here — that remains a manual step (future tooling may verify
    it against the forge API).

    On success (no stage requirement violated) exactly one OK line is
    emitted: ``stage <declared>: requirements satisfied``.
    """
    stage = adoption.get("adoption_stage", "DRAFT")
    if stage == "DRAFT":
        return  # no requirements beyond the structural checks; stay silent
    if stage not in ADOPTION_STAGES:
        # The adoption schema already rejects unknown values; this guard
        # keeps stage enforcement honest when the schema itself is unusable.
        listed = ", ".join(ADOPTION_STAGES)
        report.error(
            f"adoption_stage {stage!r} is not one of {listed} — "
            "stage requirements cannot be enforced"
        )
        return
    errors_before = sum(1 for level, _ in report.results if level == "error")
    expired_review_dates = False

    # HUMAN_REVIEWED (also CONFORMANT): no unfilled placeholders anywhere in
    # the adoption file or any loaded register. The raw documents are
    # re-loaded so that the substitution tolerated by the structural checks
    # cannot mask a leftover token.
    scan_targets: list[tuple[str, Path]] = [(str(adoption_path), adoption_path)]
    if adoption.get("layout") == "lite":
        lite_path = project_root / LITE_ASSURANCE_PATH
        if lite_path.is_file():
            scan_targets.append((LITE_ASSURANCE_PATH, lite_path))
    else:
        for kind in REGISTER_KINDS:
            relative = paths.get(kind)
            if relative is None:
                continue  # rejected by check_declared_paths; already reported
            path = project_root / relative
            if path.is_file():
                scan_targets.append((relative, path))
    for label, path in scan_targets:
        document, error = load_yaml(path)
        if error is not None:
            # The structural checks already reported the load failure; this
            # line keeps the stage verdict honest instead of claiming OK.
            report.error(
                f"stage HUMAN_REVIEWED: cannot scan {label} for placeholders — {error}"
            )
            continue
        for json_path, value in find_placeholder_strings(document):
            report.error(
                f"stage HUMAN_REVIEWED: unfilled placeholder {value!r} "
                f"in {label} at {json_path}"
            )

    # HUMAN_REVIEWED (also CONFORMANT): a completed human review on record.
    human_review = adoption.get("human_review")
    if not isinstance(human_review, dict):
        needed = ", ".join(HUMAN_REVIEW_REQUIRED_FIELDS)
        report.error(
            f"stage HUMAN_REVIEWED: human_review block is missing — record "
            f"the completed review ({needed})"
        )
    else:
        for field in HUMAN_REVIEW_REQUIRED_FIELDS:
            if not nonempty_string(human_review.get(field)):
                report.error(
                    f"stage HUMAN_REVIEWED: human_review.{field} is empty or missing"
                )

    if stage == "CONFORMANT":
        # Passed review_after dates. The error lines themselves were already
        # emitted by check_semantics — stage CONFORMANT elevates them to
        # errors, as if --strict-review-dates had been passed — so they are
        # only counted against the stage verdict here, not re-reported.
        today = datetime.date.today()
        for kind in ("defeaters", "residuals"):
            for entry in registers.get(kind) or []:
                if not isinstance(entry, dict):
                    continue
                review_after = coerce_date(entry.get("review_after"))
                if review_after is not None and review_after < today:
                    expired_review_dates = True

        # Every severity-critical invariant must have a decided intent.
        # Any classification other than UNKNOWN (including ACCIDENTAL and
        # DEPRECATED) counts as decided; conclusion status stays a separate
        # axis (PROFILE.md section 4).
        for entry in registers.get("invariants") or []:
            if not isinstance(entry, dict) or entry.get("severity") != "critical":
                continue
            label = entry["id"] if nonempty_string(entry.get("id")) else "<no id>"
            intent = entry.get("intent")
            classification = (
                intent.get("classification") if isinstance(intent, dict) else None
            )
            if classification == "UNKNOWN":
                report.error(
                    f"stage CONFORMANT: critical invariant {label} intent is "
                    "UNKNOWN — decide it before declaring conformance"
                )
            elif not nonempty_string(classification):
                report.error(
                    f"stage CONFORMANT: critical invariant {label} "
                    "intent.classification is missing — decide it before "
                    "declaring conformance"
                )

        # At least one attributable approval: who approved, where the
        # durable record lives, and when. Shape errors in individual
        # entries are the adoption schema's concern; this check asks only
        # whether any fully attributable entry exists.
        approvals = (
            human_review.get("approvals") if isinstance(human_review, dict) else None
        )
        attributable = [
            entry
            for entry in (approvals if isinstance(approvals, list) else [])
            if isinstance(entry, dict)
            and all(
                nonempty_string(entry.get(field))
                for field in ATTRIBUTABLE_APPROVAL_FIELDS
            )
        ]
        if not attributable:
            fields = ", ".join(ATTRIBUTABLE_APPROVAL_FIELDS)
            report.error(
                f"stage CONFORMANT: human_review.approvals needs at least "
                f"one attributable entry ({fields})"
            )

    errors_after = sum(1 for level, _ in report.results if level == "error")
    if errors_after == errors_before and not expired_review_dates:
        report.ok(f"stage {stage}: requirements satisfied")


def run_adopter(args: argparse.Namespace) -> int:
    report = Report()
    adoption_path = Path(args.adoption)
    project_root = Path(args.project_root)
    schemas_dir = Path(args.schemas)

    schemas = load_adopter_schemas(schemas_dir, report)
    adoption = check_adoption_document(adoption_path, schemas, report)
    if adoption is None:
        return report.emit("adopter", args.json)

    if args.profile_checkout is not None:
        check_pinned_version(adoption, Path(args.profile_checkout), report)

    declared_profiles = adoption.get("profiles")
    profiles = [
        profile
        for profile in (declared_profiles if isinstance(declared_profiles, list) else [])
        if isinstance(profile, str)
    ]

    # Stage enforcement (unless --ignore-stage). Stage CONFORMANT turns
    # passed review_after dates into errors, as if --strict-review-dates had
    # been passed; the remaining stage requirements run as a dedicated block
    # after the structural checks.
    enforce_stage = not args.ignore_stage
    strict_review_dates = args.strict_review_dates or (
        enforce_stage and adoption.get("adoption_stage") == "CONFORMANT"
    )

    paths = check_declared_paths(project_root, resolve_paths(adoption), report)
    if adoption.get("layout") == "lite":
        # Lite layout: one consolidated assurance file replaces the split
        # registers. Sections face the same register schemas and the same
        # semantic checks; only the file layout differs.
        check_lite_profiles(profiles, report)
        lite_document, registers = check_lite_file(project_root, schemas, report)
        check_semantics(registers, report, strict_review_dates=strict_review_dates)
        check_lite_required_files(project_root, paths, lite_document, report)
    else:
        registers = check_artifacts(project_root, paths, schemas, report)
        check_semantics(registers, report, strict_review_dates=strict_review_dates)
        check_required_files(project_root, paths, profiles, report)
    check_component_map(adoption, registers, report)
    check_adopter_warnings(project_root, profiles, report)
    if enforce_stage:
        check_adoption_stage(
            adoption, adoption_path, project_root, paths, registers, report
        )

    return report.emit("adopter", args.json)


# ---------------------------------------------------------------------------
# drift subcommand (impact routing on pull requests)
# ---------------------------------------------------------------------------


def read_changed_files(path: Path) -> tuple[list[str] | None, str | None]:
    """Read a newline-separated changed-file list; return (paths, error)."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"cannot read {path}: {exc}"
    changed = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("./"):
            line = line[2:]
        changed.append(line)
    return changed, None


def read_pr_body(path: Path) -> str:
    """Read the PR description text; a missing or unreadable file is empty."""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def run_drift(args: argparse.Namespace) -> int:
    """Route a pull request's change set against the adoption component map.

    A component is *touched* when any of its path globs matches a changed
    file. A touched component is satisfied when the change set also touches
    assurance artifacts, when the PR description mentions every invariant ID
    mapped to the component, or when the description carries an explicit
    no-impact statement (``Assurance impact: none`` plus a mandatory
    ``Reason:`` line). Unsatisfied components warn by default and fail with
    ``--strict``. The invariant IDs come from the map itself; whether they
    exist in the register is the adopter subcommand's cross-check.
    """
    report = Report()
    adoption_path = Path(args.adoption)

    # Strict loading, as in adopter mode: an unreadable or malformed
    # adoption declaration is an error, never silently skipped.
    document, error = load_yaml(adoption_path)
    if error is not None:
        report.error(f"adoption file: {error}")
        return report.emit("drift", args.json)
    if not isinstance(document, dict):
        report.error(f"adoption file {adoption_path}: top level is not a mapping")
        return report.emit("drift", args.json)

    components = document.get("components")
    if components is None:
        report.ok("no component map — impact routing not configured")
        return report.emit("drift", args.json)
    if not isinstance(components, dict) or not components:
        report.error(
            "components: must be a non-empty mapping of component name to "
            "{paths, invariants}"
        )
        return report.emit("drift", args.json)

    changed, error = read_changed_files(Path(args.changed_files))
    if error is not None:
        report.error(f"changed-files list: {error}")
        return report.emit("drift", args.json)
    body = read_pr_body(Path(args.pr_body))

    assurance_touched = any(
        path.startswith(ASSURANCE_ARTIFACT_PREFIXES) for path in changed
    )
    no_impact_declared = NO_IMPACT_RE.search(body) is not None
    no_impact_ok = no_impact_declared and NO_IMPACT_REASON_RE.search(body) is not None

    touched_any = False
    for name, component in components.items():
        # Light structural checks so drift stays usable standalone; the full
        # shape validation lives in the adoption schema (adopter subcommand).
        if not isinstance(component, dict):
            report.error(f"component '{name}': must be a mapping with 'paths' and 'invariants'")
            continue
        path_globs = component.get("paths")
        invariant_ids = component.get("invariants")
        if not (
            isinstance(path_globs, list)
            and path_globs
            and all(nonempty_string(item) for item in path_globs)
        ):
            report.error(f"component '{name}': 'paths' must be a non-empty list of glob strings")
            continue
        if not (
            isinstance(invariant_ids, list)
            and invariant_ids
            and all(nonempty_string(item) for item in invariant_ids)
        ):
            report.error(f"component '{name}': 'invariants' must be a non-empty list of invariant IDs")
            continue

        regexes = [compile_path_glob(pattern) for pattern in path_globs]
        matched = [
            path for path in changed if any(regex.fullmatch(path) for regex in regexes)
        ]
        if not matched:
            continue
        touched_any = True
        count = len(matched)
        touched = f"component '{name}' touched ({count} changed file{'s' if count != 1 else ''})"
        ids = ", ".join(invariant_ids)
        if assurance_touched:
            report.ok(f"{touched} — assurance artifacts updated in the same change")
        elif all(invariant_id in body for invariant_id in invariant_ids):
            report.ok(f"{touched} — PR description mentions {ids}")
        elif no_impact_ok:
            report.ok(
                f"{touched} — PR description declares 'Assurance impact: none' "
                "with a reason"
            )
        else:
            message = (
                f"{touched} without assurance update, invariant mention, or a "
                f"no-impact statement — address {ids} or add "
                "'Assurance impact: none' + 'Reason: ...' to the PR description"
            )
            if no_impact_declared:
                message += (
                    " ('Assurance impact: none' was found but the mandatory "
                    "'Reason:' line is missing)"
                )
            if args.strict:
                report.error(message)
            else:
                report.warn(message)

    if not touched_any:
        count = len(changed)
        report.ok(
            f"no mapped component is touched by this change "
            f"({count} changed file{'s' if count != 1 else ''})"
        )

    return report.emit("drift", args.json)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="validate.py",
        description="Validator for the OpenDevs Agentic Assurance Profile.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    self_check = subparsers.add_parser(
        "self-check",
        help="validate the central profile repository (templates, schemas, VERSION)",
    )
    self_check.add_argument(
        "--repo-root",
        default=None,
        help="profile repository root (default: parent of this script's directory)",
    )
    self_check.add_argument(
        "--json", action="store_true", help="emit a machine-readable JSON summary"
    )
    self_check.set_defaults(handler=run_self_check)

    adopter = subparsers.add_parser(
        "adopter",
        help="validate an adopting repository against the pinned profile's schemas",
    )
    adopter.add_argument(
        "--adoption",
        required=True,
        help="path to the adoption declaration (.agentic-assurance/adoption.yaml)",
    )
    adopter.add_argument(
        "--project-root", required=True, help="root of the adopting repository"
    )
    adopter.add_argument(
        "--schemas",
        required=True,
        help="schemas directory of the pinned profile checkout (never the latest branch)",
    )
    adopter.add_argument(
        "--profile-checkout",
        default=None,
        help="root of the pinned profile checkout; enables the VERSION comparison",
    )
    adopter.add_argument(
        "--strict-review-dates",
        action="store_true",
        help="treat passed review_after dates as errors instead of warnings",
    )
    adopter.add_argument(
        "--ignore-stage",
        action="store_true",
        help="skip enforcement of the declared adoption_stage "
        "(structure-only validation; everything else is unchanged)",
    )
    adopter.add_argument(
        "--json", action="store_true", help="emit a machine-readable JSON summary"
    )
    adopter.set_defaults(handler=run_adopter)

    drift = subparsers.add_parser(
        "drift",
        help="route a pull request's changed files against the adoption "
        "component map (impact routing)",
    )
    drift.add_argument(
        "--adoption",
        required=True,
        help="path to the adoption declaration (.agentic-assurance/adoption.yaml)",
    )
    drift.add_argument(
        "--changed-files",
        required=True,
        help="file holding the newline-separated repo-relative changed paths",
    )
    drift.add_argument(
        "--pr-body",
        required=True,
        help="file holding the PR description text (missing file = empty body)",
    )
    drift.add_argument(
        "--strict",
        action="store_true",
        help="treat unsatisfied components as errors instead of warnings",
    )
    drift.add_argument(
        "--json", action="store_true", help="emit a machine-readable JSON summary"
    )
    drift.set_defaults(handler=run_drift)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
