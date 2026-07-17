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
DATE_SUBSTITUTION = "2000-01-01"

SCHEMA_FILES = (
    "adoption.schema.json",
    "claims.schema.json",
    "invariants.schema.json",
    "defeaters.schema.json",
    "residuals.schema.json",
)

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

PROVISIONAL_PROFILES = ("data-curation", "agent-runtime")


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
) -> None:
    schema = schemas.get(schema_name)
    if schema is None:
        report.error(f"templates/{template}: cannot validate, schemas/{schema_name} unusable")
        return
    document, error = load_yaml(repo_root / "templates" / template)
    if error is not None:
        report.error(f"templates/{template}: {error}")
        return
    errors = schema_errors(substitute_placeholders(document), schema, f"templates/{template}")
    if errors:
        for message in errors:
            report.error(message)
    else:
        report.ok(
            f"templates/{template} validates against schemas/{schema_name} "
            "(placeholders substituted)"
        )


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
    check_template(repo_root, "CLAIMS.yaml", "claims.schema.json", schemas, report)
    check_template(repo_root, "INVARIANTS.yaml", "invariants.schema.json", schemas, report)
    check_template(repo_root, "DEFEATERS.yaml", "defeaters.schema.json", schemas, report)
    check_template(repo_root, "RESIDUALS.yaml", "residuals.schema.json", schemas, report)
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
) -> None:
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
            continue
        schema = schemas.get(schema_name)
        if schema is None:
            report.error(f"{relative}: cannot validate, {schema_name} unusable")
            continue
        # Template placeholder values are tolerated in artifact registers so
        # that freshly copied templates validate; substitution mirrors
        # self-check. The adoption declaration itself remains strict.
        errors = schema_errors(substitute_placeholders(document), schema, relative)
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

    paths = check_declared_paths(project_root, resolve_paths(adoption), report)
    check_artifacts(project_root, paths, schemas, report)
    check_required_files(project_root, paths, profiles, report)
    check_adopter_warnings(project_root, profiles, report)

    return report.emit("adopter", args.json)


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
        "--json", action="store_true", help="emit a machine-readable JSON summary"
    )
    adopter.set_defaults(handler=run_adopter)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
