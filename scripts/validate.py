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
  enforced as errors. ``--ignore-stage`` skips only the stage-specific
  HUMAN_REVIEWED/CONFORMANT gates; DRAFT-equivalent baseline semantics still
  run.

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
from functools import lru_cache
import html
import json
import math
import os
import posixpath
import re
import stat
import subprocess
import sys
import unicodedata
from pathlib import Path
from urllib.parse import unquote_to_bytes, urlparse

try:
    import yaml
except ImportError:  # pragma: no cover
    print("ERROR: the 'pyyaml' package is required (pip install pyyaml jsonschema)")
    sys.exit(1)

try:
    from jsonschema import Draft202012Validator, FormatChecker
    from jsonschema.exceptions import SchemaError
    from referencing import Registry
    from referencing.exceptions import Unresolvable
except ImportError:  # pragma: no cover
    print("ERROR: the 'jsonschema' package is required (pip install pyyaml jsonschema)")
    sys.exit(1)

JSON_SCHEMA_2020_12 = "https://json-schema.org/draft/2020-12/schema"
# Passing an explicit empty registry disables jsonschema's legacy remote-ref
# retrieval path. Profile validation is deliberately offline: a schema must
# be self-contained, and an unresolved reference is an ordinary diagnostic.
OFFLINE_SCHEMA_REGISTRY = Registry()

# The abolished pre-release version string must appear in no repository file
# (tracked or untracked-but-not-ignored), including this one, so it is
# assembled at runtime instead of written out.
FORBIDDEN_VERSION_STRING = "v0.1.0" + "-draft"

# Central repository VERSION file: "unreleased", a release tag, an -rc.N
# pre-release, or a -dev development marker. Numeric identifiers follow
# SemVer's ASCII/no-leading-zero grammar, and the release process starts
# candidates at rc.1. Adopter pins additionally forbid -dev; that stricter
# rule lives in schemas/adoption.schema.json.
SEMVER_NUM = r"(?:0|[1-9][0-9]*)"
RELEASE_CANDIDATE_NUM = r"(?:[1-9][0-9]*)"
PROFILE_RELEASE_PATTERN = (
    rf"v{SEMVER_NUM}\.{SEMVER_NUM}\.{SEMVER_NUM}"
    rf"(?:-rc\.{RELEASE_CANDIDATE_NUM})?"
)
ADOPTER_VERSION_RE = re.compile(rf"(?:unreleased|{PROFILE_RELEASE_PATTERN})")
VERSION_FILE_RE = re.compile(
    rf"(?:unreleased|v{SEMVER_NUM}\.{SEMVER_NUM}\.{SEMVER_NUM}"
    rf"(?:-rc\.{RELEASE_CANDIDATE_NUM}|-dev)?)"
)

# The prose starter rows shipped throughout the pre-v0.4 contract, including
# pre-first-release pilot declarations pinned as ``unreleased``. A v0.4+
# declaration has the new detectable sentinels and must not inherit a blanket
# exemption merely by retaining an example ID.
PRE_V04_STARTER_VERSION_RE = re.compile(
    rf"v0\.[1-3]\.{SEMVER_NUM}(?:-rc\.{RELEASE_CANDIDATE_NUM})?"
)
PROFILE_RELEASE_VERSION_RE = re.compile(
    rf"v(?P<major>{SEMVER_NUM})\.(?P<minor>{SEMVER_NUM})\."
    rf"(?P<patch>{SEMVER_NUM})(?:-rc\.{RELEASE_CANDIDATE_NUM})?"
)

# Deliberately narrow ASCII HTTP(S) URL grammar for durable approval records:
# DNS/IPv4-style names or bracketed hexadecimal IPv6 literals, a numeric port,
# and RFC 3986 path/query/fragment characters. Non-ASCII data in those three
# components remains representable through valid UTF-8 percent encoding;
# internationalized hosts use an ASCII IDNA A-label spelling. Accepting raw
# IRI data would make validation depend on an unspecified conversion policy.
_URI_PCHAR = r"(?:[A-Za-z0-9._~!$&'()*+,;=:@-]|%[0-9A-Fa-f]{2})"
_DNS_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
HTTP_URL_RE = re.compile(
    rf"https?://(?:\[[0-9A-Fa-f:.]+\]|{_DNS_LABEL}(?:\.{_DNS_LABEL})*)"
    rf"(?::[0-9]+)?(?:/{_URI_PCHAR}*)*"
    rf"(?:\?(?:{_URI_PCHAR}|[/?])*)?"
    rf"(?:#(?:{_URI_PCHAR}|[/?])*)?\Z",
    re.IGNORECASE | re.ASCII,
)

PLACEHOLDER_RE = re.compile(r"^REPLACE_WITH_[A-Z0-9_]+$")
# A placeholder left in a completed prose artifact is a NAMED marker: the
# prefix followed by at least one more word character, in any case, so a
# mangled marker such as `REPLACE_WITH_description` is still caught. The bare
# prefix on its own is deliberately NOT a marker: prose legitimately quotes it
# when instructing the reader to replace placeholders, and rejecting that made
# a correctly completed template fail. The shipped templates additionally
# avoid the literal so no copied instruction can trip this at all.
PROSE_PLACEHOLDER_RE = re.compile(r"REPLACE_WITH_\w+")
ARCHIVED_SYSTEM_PLACEHOLDERS = (
    "REPLACE_WITH_ARCHIVED_OPERATION_MAINTENANCE_AND_FEATURE_DEVELOPMENT_STATUS",
    "REPLACE_WITH_ARCHIVED_HISTORICAL_PURPOSE",
    "REPLACE_WITH_ARCHIVED_MATERIAL_LIMITATIONS",
    "REPLACE_WITH_ARCHIVED_LAST_SUPPORTED_REVISION_OR_RELEASE_OR_EXPLICIT_NONE",
)
# Official review-date sentinels. v0.3.x used the bare value; v0.4.0 uses the
# detectable REPLACE_WITH_ value. Keep both as path-scoped aliases for copied
# DRAFT registers. Neither may make a real date disappear silently in a policy
# diff, and the bare alias must never be treated as a placeholder in arbitrary
# adopter data such as ``extensions.date_format``.
CURRENT_REVIEW_DATE_PLACEHOLDER = "REPLACE_WITH_REVIEW_AFTER_DATE"
LEGACY_REVIEW_DATE_PLACEHOLDER = "YYYY-MM-DD"
REVIEW_DATE_PLACEHOLDERS = frozenset(
    (CURRENT_REVIEW_DATE_PLACEHOLDER, LEGACY_REVIEW_DATE_PLACEHOLDER)
)

# Exact bare prompts shipped in the v0.3.x register templates. They are
# placeholders only at the direct entry fields where those templates placed
# them. The same prose in extensions or other local metadata is adopter data.
LEGACY_REGISTER_FIELD_PLACEHOLDERS = {
    "claims": {
        "text": "Replace with the exact user-facing or operator-facing claim.",
        "scope": "Replace with bounded system and version scope.",
    },
    "invariants": {
        "title": "Replace with a precise invariant title",
        "statement": "Replace with a proposition that must remain true.",
        "scope": "Replace with bounded system scope.",
    },
    "defeaters": {
        "statement": "Replace with a concrete reason a claim may be false or incomplete.",
    },
    "residuals": {
        "summary": "Replace with a safe summary of remaining uncertainty.",
    },
}
CURRENT_REGISTER_FIELD_PLACEHOLDERS = {
    "claims": {
        "text": "REPLACE_WITH_THE_EXACT_CLAIM",
        "scope": "REPLACE_WITH_BOUNDED_SYSTEM_AND_VERSION_SCOPE",
    },
    "invariants": {
        "title": "REPLACE_WITH_INVARIANT_TITLE",
        "statement": "REPLACE_WITH_THE_PROPOSITION_THAT_MUST_HOLD",
        "scope": "REPLACE_WITH_BOUNDED_SYSTEM_SCOPE",
    },
    "defeaters": {
        "statement": "REPLACE_WITH_A_CONCRETE_DEFEATER_REASON",
    },
    "residuals": {
        "summary": "REPLACE_WITH_RESIDUAL_SUMMARY",
    },
}
# Exact entry objects shipped by every tagged pre-v0.4 split-register template.
# Compatibility is intentionally fingerprint-based: changing even one default,
# adding local metadata, or completing one prompt turns the row into adopter
# policy and protects it from silent deletion.
PRE_V04_REGISTER_STARTER_ENTRIES = {
    "claims": {
        "id": "CLAIM-EXAMPLE-001",
        "text": LEGACY_REGISTER_FIELD_PLACEHOLDERS["claims"]["text"],
        "scope": LEGACY_REGISTER_FIELD_PLACEHOLDERS["claims"]["scope"],
        "proof_tier": "OPERATOR_ATTESTED",
        "invariants": [],
        "evidence": [],
        "limitations": [],
        "defeaters": [],
        "residuals": [],
        "status": "UNKNOWN",
        "disclosure": "PUBLIC",
        "owner": "REPLACE_WITH_OWNER",
    },
    "invariants": {
        "id": "INV-EXAMPLE-001",
        "title": LEGACY_REGISTER_FIELD_PLACEHOLDERS["invariants"]["title"],
        "statement": LEGACY_REGISTER_FIELD_PLACEHOLDERS["invariants"]["statement"],
        "severity": "critical",
        "intent": {"classification": "UNKNOWN", "authority": None},
        "scope": LEGACY_REGISTER_FIELD_PLACEHOLDERS["invariants"]["scope"],
        "assumptions": [],
        "limitations": [],
        "enforcement": [],
        "verification": [],
        "evidence": [],
        "defeaters": [],
        "residuals": [],
        "status": "UNKNOWN",
        "disclosure": "PUBLIC",
        "owner": "REPLACE_WITH_OWNER",
    },
    "defeaters": {
        "id": "DEF-EXAMPLE-001",
        "statement": LEGACY_REGISTER_FIELD_PLACEHOLDERS["defeaters"]["statement"],
        "affected_claims": [],
        "affected_invariants": [],
        "evidence": [],
        "status": "OPEN",
        "disclosure": "PUBLIC",
        "owner": "REPLACE_WITH_OWNER",
        "review_after": LEGACY_REVIEW_DATE_PLACEHOLDER,
    },
    "residuals": {
        "id": "RES-EXAMPLE-001",
        "summary": LEGACY_REGISTER_FIELD_PLACEHOLDERS["residuals"]["summary"],
        "private_detail_location": None,
        "affected_claims": [],
        "affected_invariants": [],
        "impact": "unknown",
        "uncertainty": "unknown",
        "mitigation": [],
        "status": "OPEN",
        "disclosure": "SUMMARY_ONLY",
        "owner": "REPLACE_WITH_OWNER",
        "accepted_by": None,
        "accepted_at": None,
        "review_after": LEGACY_REVIEW_DATE_PLACEHOLDER,
    },
}
# A far-future date: a substituted template review_after must not trip the
# expired-review semantic check (a template is not an overdue review).
DATE_SUBSTITUTION = "2999-01-01"
PLACEHOLDER_SUBSTITUTIONS = {
    "REPLACE_WITH_FULL_40_CHARACTER_COMMIT_SHA": "0" * 40,
    "REPLACE_WITH_PINNED_VERSION": "unreleased",
    "REPLACE_WITH_OWNER_AND_REPOSITORY": "example/example",
    # The adoption template ships this in `profiles:` so an adopter must
    # declare a classified set rather than inherit a `core` default; the
    # central self-check substitutes it to a valid enum value.
    "REPLACE_WITH_CLASSIFIED_PROFILE": "core",
    # The register templates ship this in `review_after`; self-check
    # substitutes a far-future date, but an adopter must fill a real one.
    CURRENT_REVIEW_DATE_PLACEHOLDER: DATE_SUBSTITUTION,
}
DEFAULT_PLACEHOLDER_SUBSTITUTION = "placeholder"

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
# The minimal lite template: the smallest complete core adoption, validated
# alongside the full one so it cannot drift out of validity.
LITE_MINIMAL_TEMPLATE = "assurance.minimal.yaml"
# Register sections a lite assurance file may carry, in output order.
LITE_SECTION_KINDS = ("invariants", "defeaters", "residuals")
# Lite is core-only; any other profile requires graduating to the split layout.
LITE_PROFILES = ("core",)
# The valid profiles that require the split layout (lite is core-only). Used so
# the "graduate to split" advice fires only for a real non-core profile, not
# for a placeholder or a schema-invalid value — those get their own errors.
SPLIT_ONLY_PROFILES = (
    "service",
    "trust-critical",
    "data-curation",
    "agent-runtime",
    "archived",
)
KNOWN_PROFILES = LITE_PROFILES + SPLIT_ONLY_PROFILES

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
# Bound the standalone drift surface as well as schema-validated adopters.
# The matcher below is polynomial, but explicit limits keep hostile policy
# inputs from turning a pull-request check into an avoidable resource sink.
MAX_COMPONENT_PATH_GLOB_LENGTH = 1024
MAX_CHANGED_PATH_LENGTH = 4096
MAX_COMPONENT_NAME_LENGTH = 256
MAX_INVARIANT_ID_LENGTH = 256
MAX_POLICY_PATH_MAPPINGS = 256
MAX_POLICY_PATH_LENGTH = 4096
MAX_COMPONENTS = 256
MAX_COMPONENT_PATH_GLOBS = 256
MAX_COMPONENT_INVARIANTS = 256
MAX_CHANGED_FILES = 20_000
MAX_GLOB_MATCH_WORK = 20_000_000
MAX_MENTION_SCAN_WORK = 20_000_000
MAX_CHANGED_FILE_LIST_BYTES = 32 * 1024 * 1024
MAX_PR_BODY_BYTES = 1024 * 1024
MAX_ASSURANCE_DIFF_BYTES = 20 * 1024 * 1024
# Logical nodes after following aliases, not merely nodes in the compact YAML
# graph. This stops a tiny alias DAG from representing an exponential tree.
MAX_YAML_EXPANDED_NODES = 100_000
MAX_POLICY_YAML_BYTES = 5 * 1024 * 1024
MAX_POLICY_JSON_BYTES = 10 * 1024 * 1024
MAX_POLICY_JSON_NESTING = 256
MAX_POLICY_JSON_NODES = 500_000
MAX_PROJECT_TEXT_BYTES = 5 * 1024 * 1024
# A declared workflow directory is an entry surface, not an arbitrary tree
# existence check. Bound its recursive workflow-tree index and the amount of
# candidate prose inspected while requiring at least one real entry document.
MAX_WORKFLOW_DIRECTORY_ENTRIES = 4096
MAX_WORKFLOW_DIRECTORY_DEPTH = 16
MAX_WORKFLOW_ENTRY_BYTES = 1024 * 1024
MAX_WORKFLOW_DIRECTORY_SCAN_BYTES = 8 * 1024 * 1024
# Numeric tokens are bounded independently of the enclosing file.  Python
# 3.11+ applies an interpreter-level decimal-integer limit, but supported
# 3.10 does not, and YAML also accepts non-decimal integer spellings.  Keep
# policy parsing predictable on every supported interpreter.
MAX_POLICY_NUMBER_CHARACTERS = 4096
INVARIANT_ID_RE = re.compile(r"^INV-[A-Z0-9]+(?:-[A-Z0-9]+)*-[0-9]{3}$")
# Explicit no-impact statement in a PR description: the declaration line and
# its immediately following mandatory reason inside the leading directive block.
NO_IMPACT_RE = re.compile(
    r"^Assurance impact:[ \t]*none[ \t]*$",
    re.IGNORECASE | re.ASCII | re.MULTILINE,
)
NO_IMPACT_REASON_RE = re.compile(
    r"^Reason:[ \t]*(?P<reason>[^\r\n]*)$",
    re.IGNORECASE | re.ASCII | re.MULTILINE,
)
# Positive routing uses a dedicated top-level directive rather than a free
# prose mention. The payload is parsed separately so satisfaction is a valid,
# exact ID-set membership check, not a substring match inside a link destination,
# HTML attribute, quote, or code example.
ASSURANCE_IMPACT_DIRECTIVE_RE = re.compile(
    r"^Assurance impact:[ \t]*(?P<ids>[^\r\n]+?)[ \t]*$",
    re.IGNORECASE | re.ASCII,
)
# Explicit acknowledgment that a PR deliberately weakens the assurance policy
# (stage downgrade, component removal, pin change, ...). The text after the
# colon is the reason and must be non-empty; ``leading_pr_directives`` binds it
# to the unambiguous leading block.
POLICY_ACK_RE = re.compile(
    r"^Assurance policy change:[ \t]*(?P<reason>[^\r\n]*)$",
    re.IGNORECASE | re.ASCII | re.MULTILINE,
)
HTML_COMMENT_RE = re.compile(r"<!--.*?(?:-->|$)", re.DOTALL)
NON_PROSE_HTML_BLOCK_RE = re.compile(
    r"<(?P<tag>script|style|template|textarea|pre|code)"
    r"(?=[\t\n\f\r />])[^>]*>"
    r".*?(?:</(?P=tag)[ \t\r\n\f]*>|$)",
    re.IGNORECASE | re.ASCII | re.DOTALL,
)
RAW_HTML_OPEN_LINE_RE = re.compile(
    r"<(?P<tag>[A-Za-z][A-Za-z0-9:-]*)\b[^>]*>",
    re.IGNORECASE | re.ASCII,
)
RAW_HTML_CLOSE_LINE_RE = re.compile(
    r"</(?P<tag>[A-Za-z][A-Za-z0-9:-]*)[ \t\r\n\f]*>",
    re.IGNORECASE | re.ASCII,
)
HTML_VISIBLE_ELEMENT_RE = re.compile(
    r"<(?:embed|hr|img|input)(?=[\t\n\f\r />])",
    re.IGNORECASE | re.ASCII,
)
HTML_VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}
# These void elements render visible content or a visible control.  A line
# containing one is ordinary presentation content and therefore ends the
# leading PR directive block; silently dropping it would let a later
# directive masquerade as the first visible line.
HTML_VISIBLE_VOID_ELEMENTS = {"embed", "hr", "img", "input"}

# Report level -> GitHub Actions annotation command.
GITHUB_ANNOTATION_KINDS = {"error": "error", "warn": "warning"}

# Strength orders used by the register policy diff: earlier = stronger.
# Moving right in these lists is a weakening; moving left never is.
SEVERITY_ORDER = ("critical", "high", "medium", "low")
IMPACT_ORDER = ("critical", "high", "medium", "low", "unknown")
PROOF_TIER_ORDER = (
    "INDEPENDENTLY_VERIFIABLE",
    "OPERATIONALLY_AUDITABLE",
    "OPERATOR_ATTESTED",
    "NOT_CLAIMED",
)
# Conclusion statuses whose replacement counts as a weakening. Moving TO
# CONTRADICTED is deliberately NOT a weakening — recording a contradiction
# is an honesty upgrade. Moving AWAY from a recorded CONTRADICTED is handled
# separately (clearing a contradiction is a disposition that needs review),
# so CONTRADICTED is not a key here.
STATUS_WEAKENINGS = {"VERIFIED": ("INFERRED", "UNKNOWN"), "INFERRED": ("UNKNOWN",)}
# Reclassifications away from any affirmative human intent disposition.
# INTENDED, COMPATIBILITY, and DEPRECATED each record a distinct, authoritative
# decision; moving among them or to UNKNOWN/ACCIDENTAL rewrites that decision
# and needs review. Unsetting one altogether is handled alongside in the diff.
AFFIRMATIVE_INTENT_CLASSES = ("INTENDED", "COMPATIBILITY", "DEPRECATED")
INTENT_WEAKENINGS = {
    classification: tuple(
        candidate
        for candidate in (
            "INTENDED",
            "ACCIDENTAL",
            "COMPATIBILITY",
            "UNKNOWN",
            "DEPRECATED",
        )
        if candidate != classification
    )
    for classification in AFFIRMATIVE_INTENT_CLASSES
}
# Evidence-bearing list fields whose shrinkage is a weakening on
# high/critical invariants.
INVARIANT_EVIDENCE_LISTS = ("enforcement", "verification", "evidence")
# Relationship and basis list fields protected per register kind: removing
# an item severs an assurance-graph edge (what could defeat a claim, what a
# defeater affects) or drops a stated caveat, mitigation, or assumption.
# Compared as string sets, so editing a prose item reads as removing it —
# these lists record commitments item by item, unlike the free-text
# statement/summary fields the diff leaves to human review. Protected at
# every severity: they are graph structure, not evidence volume
# (INVARIANT_EVIDENCE_LISTS keeps its high/critical gate for the latter).
PROTECTED_LIST_FIELDS = {
    "claims": ("evidence", "invariants", "limitations", "defeaters", "residuals"),
    "invariants": ("assumptions", "limitations", "defeaters", "residuals"),
    "defeaters": ("affected_claims", "affected_invariants", "evidence"),
    "residuals": ("affected_claims", "affected_invariants", "mitigation"),
}
# Recorded judgement values whose comparison is pair-keyed: the weakening
# checks need a meaningful value on both sides, so unsetting one on the head
# is itself a finding (see the diff). All are schema-required fields;
# `intent.classification` follows the same rule but is nested, so it is
# handled alongside the intent comparison rather than listed here.
GATED_VALUE_FIELDS = {
    "claims": ("status", "proof_tier"),
    "invariants": ("status", "severity"),
    "defeaters": ("status",),
    "residuals": ("status", "impact", "uncertainty"),
}
# Singular nouns used in policy-diff finding messages.
REGISTER_NOUNS = {
    "claims": "claim",
    "invariants": "invariant",
    "defeaters": "defeater",
    "residuals": "residual",
}
# Residual acceptance record: rewriting who accepted a risk, when, or why is
# a change to a recorded human decision, not housekeeping.
RESIDUAL_ACCEPTANCE_FIELDS = ("accepted_by", "accepted_at", "acceptance_rationale")
# Register statuses that mean "closed / no longer a live, tracked concern".
# Moving an entry into one of these dispositions removes it from active
# scrutiny without deleting its ID, so it needs the same acknowledgment as a
# deletion. Re-opening (moving out of these) is never a weakening.
RESIDUAL_CLOSED_STATUSES = ("RESOLVED",)
DEFEATER_CLOSED_STATUSES = ("MITIGATED", "RESOLVED", "WITHDRAWN")

REPO_VISIBILITIES = ("public", "private", "internal")

# UTC dates on which an inserted positive leap second actually occurred.
# Approval timestamps describe completed acts, so a fixed historical table is
# both stricter and sufficient; a future announced leap second cannot be used
# before it occurs and can be added in the profile release that follows it.
RFC3339_POSITIVE_LEAP_SECOND_DATES = frozenset(
    datetime.date.fromisoformat(value)
    for value in (
        "1972-06-30", "1972-12-31", "1973-12-31", "1974-12-31",
        "1975-12-31", "1976-12-31", "1977-12-31", "1978-12-31",
        "1979-12-31", "1981-06-30", "1982-06-30", "1983-06-30",
        "1985-06-30", "1987-12-31", "1989-12-31", "1990-12-31",
        "1992-06-30", "1993-06-30", "1994-06-30", "1995-12-31",
        "1997-06-30", "1998-12-31", "2005-12-31", "2008-12-31",
        "2012-06-30", "2015-06-30", "2016-12-31",
    )
)


def github_log_line(value: object) -> str:
    """Render untrusted policy text as one physical Actions log line.

    GitHub workflow commands are line-oriented. A component name containing a
    newline could otherwise terminate the ordinary ``WARN:``/``ERROR:`` line
    and start a command such as ``::add-mask::``. Keep printable text readable
    while escaping every ASCII control character and DEL.
    """
    rendered: list[str] = []
    for character in str(value):
        codepoint = ord(character)
        if character == "\r":
            rendered.append("\\r")
        elif character == "\n":
            rendered.append("\\n")
        elif character == "\t":
            rendered.append("\\t")
        elif not character.isprintable() or 0xD800 <= codepoint <= 0xDFFF:
            if codepoint <= 0xFFFF:
                rendered.append(f"\\u{codepoint:04x}")
            else:
                rendered.append(f"\\U{codepoint:08x}")
        else:
            rendered.append(character)
    line = "".join(rendered)
    # A valid international policy string must not crash a validator whose
    # stdout was configured as ASCII or another narrow legacy encoding.
    # Preserve readable text when supported and make every other code point a
    # visible backslash escape at the final line-oriented sink.
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        return line.encode(encoding, "backslashreplace").decode(encoding)
    except LookupError:  # defensive: an embedding may expose a bogus codec name
        return line.encode("utf-8", "backslashreplace").decode("utf-8")


def markdown_table_cell(value: object) -> str:
    """Render untrusted text as plain content in a GitHub Markdown table.

    Encoding every printable punctuation character prevents links, images,
    emphasis, code spans, HTML, and table delimiters rather than maintaining a
    brittle deny-list of Markdown metacharacters. Entities render as the
    original punctuation after Markdown parsing. Non-printable controls are
    shown visibly; a newline alone becomes an intentional line break.
    """
    rendered: list[str] = []
    for character in str(value):
        if character == "\n":
            rendered.append("<br>")
        elif character.isalnum() or character == " ":
            rendered.append(character)
        elif character.isprintable():
            rendered.append(f"&#{ord(character)};")
        else:
            rendered.append(f"&#92;u{ord(character):04x}")
    return "".join(rendered)


def github_command_value(value: object) -> str:
    """Percent-encode data placed after a GitHub workflow-command prefix."""
    valid_unicode = str(value).encode("utf-8", "backslashreplace").decode("utf-8")
    return (
        valid_unicode
        .replace("%", "%25")
        .replace("\r", "%0D")
        .replace("\n", "%0A")
    )


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
            # Inside GitHub Actions, errors and warnings are additionally
            # emitted as workflow annotations so they surface in the PR
            # checks UI instead of only in the raw log (warn-first drift
            # findings were otherwise easy to miss).
            in_actions = bool(os.environ.get("GITHUB_ACTIONS"))
            for level, message in self.results:
                # Policy strings are untrusted even outside Actions.  Always
                # render one physical, encodable line: otherwise a filename or
                # component name containing a control character can forge a
                # second result line, while an unpaired surrogate can crash a
                # terminal whose encoder rejects it.
                rendered = github_log_line(message)
                print(f"{level.upper()}: {rendered}")
                kind = GITHUB_ANNOTATION_KINDS.get(level)
                if in_actions and kind is not None:
                    escaped = github_command_value(message)
                    print(github_log_line(f"::{kind}::{escaped}"))
        return exit_code


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


class StrictSafeLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys.

    Assurance declarations are policy inputs. PyYAML's default last-key-wins
    behavior would let a later duplicate silently erase a profile, stage, or
    register field. YAML merge keys are rejected before PyYAML flattening so
    an alias DAG cannot expand ahead of the logical-node budget.
    """


class LegacySafeLoader(yaml.SafeLoader):
    """Pre-v0.4 migration loader with explicit last-key-wins semantics.

    It exists only for already-merged base artifacts while an adopter cleans
    up duplicate keys. Head declarations and all normal validation stay
    strict. Non-string keys and unsafe YAML types remain forbidden.
    """


class YamlComplexityError(ValueError):
    """Raised when YAML aliases exceed the bounded logical document size."""


class YamlDataModelError(ValueError):
    """Raised when safe YAML still contains a non-JSON-compatible value."""


YAML_MERGE_TAG = "tag:yaml.org,2002:merge"


def reject_yaml_merge_keys(node: yaml.nodes.MappingNode) -> None:
    """Reject ``<<`` before PyYAML expands a potentially exponential DAG.

    Policy documents use the JSON object model, which has no merge-key
    operation.  More importantly, ``SafeConstructor.flatten_mapping`` expands
    aliases before the post-construction logical-node budget can run.  A tiny
    merge DAG could therefore consume exponential work first.  Ordinary YAML
    anchors and aliases remain supported and are bounded after construction.
    """
    for key_node, _value_node in node.value:
        if key_node.tag == YAML_MERGE_TAG:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "YAML merge keys ('<<') are not supported in policy data",
                key_node.start_mark,
            )


def construct_unique_mapping(
    loader: StrictSafeLoader, node: yaml.nodes.MappingNode, deep: bool = False
) -> dict:
    reject_yaml_merge_keys(node)
    loader.flatten_mapping(node)
    mapping: dict = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found non-string mapping key {key!r}; policy YAML uses the JSON object model",
                key_node.start_mark,
            )
        try:
            duplicate = key in mapping
        except TypeError as exc:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found an unhashable mapping key",
                key_node.start_mark,
            ) from exc
        if duplicate:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


StrictSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_unique_mapping,
)


def construct_legacy_mapping(
    loader: LegacySafeLoader, node: yaml.nodes.MappingNode, deep: bool = False
) -> dict:
    """Construct a JSON-model mapping, retaining the final duplicate value."""
    reject_yaml_merge_keys(node)
    loader.flatten_mapping(node)
    mapping: dict = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found non-string mapping key {key!r}; policy YAML uses the JSON object model",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


LegacySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_legacy_mapping,
)


def construct_bounded_yaml_number(
    loader: yaml.SafeLoader, node: yaml.nodes.ScalarNode
) -> object:
    """Construct an integer or float only after bounding its source token."""
    token = loader.construct_scalar(node)
    if len(token) > MAX_POLICY_NUMBER_CHARACTERS:
        raise yaml.constructor.ConstructorError(
            "while constructing a number",
            node.start_mark,
            "numeric token is too long "
            f"(limit {MAX_POLICY_NUMBER_CHARACTERS:,} characters)",
            node.start_mark,
        )
    if node.tag == "tag:yaml.org,2002:int":
        return yaml.constructor.SafeConstructor.construct_yaml_int(loader, node)
    return yaml.constructor.SafeConstructor.construct_yaml_float(loader, node)


def construct_strict_yaml_bool(
    loader: yaml.SafeLoader, node: yaml.nodes.ScalarNode
) -> object:
    """Construct a boolean, reporting an unresolvable one as a YAML error.

    PyYAML's SafeConstructor raises a bare ``KeyError`` for an explicitly
    tagged ``!!bool`` scalar it cannot resolve. That escapes the loader's
    error handling and would kill the run with a traceback instead of a
    finding, so it is converted to the ConstructorError shape every other
    rejection uses.
    """
    try:
        return yaml.constructor.SafeConstructor.construct_yaml_bool(loader, node)
    except yaml.YAMLError:
        raise
    except Exception as exc:  # KeyError for an unresolvable boolean word
        raise yaml.constructor.ConstructorError(
            "while constructing a boolean",
            node.start_mark,
            f"could not resolve {node.value!r} as a boolean: {exc}",
            node.start_mark,
        ) from exc


def construct_strict_yaml_timestamp(
    loader: yaml.SafeLoader, node: yaml.nodes.ScalarNode
) -> object:
    """Construct a timestamp, reporting an unresolvable one as a YAML error.

    PyYAML's SafeConstructor raises ``AttributeError`` (a failed regexp match
    dereferenced as if it succeeded) for an explicitly tagged ``!!timestamp``
    scalar that is not a timestamp; same conversion rationale as
    ``construct_strict_yaml_bool``.
    """
    try:
        return yaml.constructor.SafeConstructor.construct_yaml_timestamp(loader, node)
    except yaml.YAMLError:
        raise
    except Exception as exc:  # AttributeError on a non-matching timestamp
        raise yaml.constructor.ConstructorError(
            "while constructing a timestamp",
            node.start_mark,
            f"could not resolve {node.value!r} as a timestamp: {exc}",
            node.start_mark,
        ) from exc


for policy_loader in (StrictSafeLoader, LegacySafeLoader):
    policy_loader.add_constructor(
        "tag:yaml.org,2002:int", construct_bounded_yaml_number
    )
    policy_loader.add_constructor(
        "tag:yaml.org,2002:float", construct_bounded_yaml_number
    )
    policy_loader.add_constructor(
        "tag:yaml.org,2002:bool", construct_strict_yaml_bool
    )
    policy_loader.add_constructor(
        "tag:yaml.org,2002:timestamp", construct_strict_yaml_timestamp
    )


def construct_unique_json_object(pairs: list[tuple[str, object]]) -> dict:
    """JSON object_pairs_hook that rejects duplicate member names."""
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"found duplicate key {key!r}")
        result[key] = value
    return result


def reject_nonfinite_json(value: str) -> None:
    """Reject NaN/Infinity extensions: JSON Schema files must be strict JSON."""
    raise ValueError(f"non-finite JSON number {value!r} is not permitted")


def bounded_json_integer(value: str) -> int:
    """Parse a JSON integer with the same cross-version token bound as YAML."""
    if len(value) > MAX_POLICY_NUMBER_CHARACTERS:
        raise ValueError(
            "numeric token is too long "
            f"(limit {MAX_POLICY_NUMBER_CHARACTERS:,} characters)"
        )
    return int(value)


def bounded_json_float(value: str) -> float:
    """Parse a JSON float with an explicit input-token bound."""
    if len(value) > MAX_POLICY_NUMBER_CHARACTERS:
        raise ValueError(
            "numeric token is too long "
            f"(limit {MAX_POLICY_NUMBER_CHARACTERS:,} characters)"
        )
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(
            f"JSON number {value!r} is outside the supported finite range"
        )
    return parsed


def is_generic_placeholder(value: object) -> bool:
    """Whether a string contains the profile's machine-detectable sentinel."""
    return isinstance(value, str) and "REPLACE_WITH_" in value


def committed_string(value: object) -> bool:
    """A nonblank string that represents adopter data, not a template prompt."""
    return nonempty_string(value) and not is_generic_placeholder(value)


def is_shipped_template_entry(kind: str, entry: dict) -> bool:
    """Whether a base entry is still the profile's uncommitted starter row.

    Pre-v0.4 starter rows mixed prose/owner placeholders with real enum defaults
    such as ``severity: critical``. Treating those defaults as reviewed policy
    makes completing the template look like a weakening (or its example ID
    look like a deleted commitment). Only exact equality with the full entry
    object shipped in those templates receives this narrow compatibility
    exemption. A changed default, partial completion, extra extension, or
    made-up ``REPLACE_WITH_*`` token is adopter data and cannot exempt the row
    or create a two-change deletion escape. The caller additionally limits
    this path to pre-v0.4 base declarations; once upgraded, every retained
    example ID is protected.
    """
    return entry == PRE_V04_REGISTER_STARTER_ENTRIES.get(kind)


def is_direct_register_placeholder(kind: str, field: str, value: object) -> bool:
    """Whether a protected direct field has been replaced by a prompt.

    Generic sentinels are included here even though only exact shipped prompts
    qualify a whole starter row. This closes the first hop of replacing real
    prose with a made-up marker and deleting the example-ID row later.
    """
    if is_generic_placeholder(value):
        return True
    legacy = LEGACY_REGISTER_FIELD_PLACEHOLDERS.get(kind, {}).get(field)
    return legacy is not None and value == legacy


def uses_pre_v04_starter_contract(adoption: dict) -> bool:
    """Whether a base declaration is pinned to a pre-v0.4 starter contract."""
    upstream = adoption.get("upstream")
    version = upstream.get("version") if isinstance(upstream, dict) else None
    return (
        isinstance(version, str)
        and (
            version == "unreleased"
            or PRE_V04_STARTER_VERSION_RE.fullmatch(version) is not None
        )
    )


def uses_v04_or_later_contract(adoption: dict) -> bool:
    """Whether a declaration is pinned to a released v0.4+ contract.

    ``unreleased`` is deliberately not guessed: it named pre-first-release
    pilots as well as development checkouts, so only a versioned v0.4+ head
    proves that the migration reached the contract which removed the old
    starter rows.
    """
    upstream = adoption.get("upstream")
    version = upstream.get("version") if isinstance(upstream, dict) else None
    if not isinstance(version, str):
        return False
    match = PROFILE_RELEASE_VERSION_RE.fullmatch(version)
    if match is None:
        return False
    # Avoid ``int()`` on attacker-controlled, schema-independent drift input:
    # Python deliberately rejects extremely long decimal conversions, while
    # the comparison needed here depends only on whether major is non-zero or
    # (for major zero) minor is at least four.
    major = match.group("major").lstrip("0") or "0"
    minor = match.group("minor").lstrip("0") or "0"
    if major != "0":
        return True
    return len(minor) > 1 or minor >= "4"


def is_pre_v04_to_v04_upgrade(base: dict, head: dict) -> bool:
    """Whether this comparison is the one-hop starter migration window."""
    return uses_pre_v04_starter_contract(base) and uses_v04_or_later_contract(head)


def substitute_placeholders(node: object) -> object:
    """Replace template placeholder strings with type-appropriate dummies."""
    if isinstance(node, str):
        if PLACEHOLDER_RE.match(node):
            return PLACEHOLDER_SUBSTITUTIONS.get(node, DEFAULT_PLACEHOLDER_SUBSTITUTION)
        return node
    if isinstance(node, list):
        return [substitute_placeholders(item) for item in node]
    if isinstance(node, dict):
        return {key: substitute_placeholders(value) for key, value in node.items()}
    return node


def is_review_date_placeholder(value: object) -> bool:
    """Whether ``value`` is one of the two official review-date sentinels."""
    return isinstance(value, str) and value in REVIEW_DATE_PLACEHOLDERS


def substitute_register_placeholders(
    node: object, *, preserve_review_date_placeholders: bool = False
) -> object:
    """Substitute placeholders in a register or lite assurance document.

    In addition to the current ``REPLACE_WITH_`` sentinels, v0.3.x's bare
    ``YYYY-MM-DD`` sentinel remains supported only at the two register paths
    where it shipped: ``defeaters[*].review_after`` and
    ``residuals[*].review_after``. The generic substitution helper deliberately
    does not recognize it, so identical text in adopter extensions stays data.

    Policy-diff callers set ``preserve_review_date_placeholders``: replacing a
    real re-review commitment with either the current or legacy sentinel must
    remain visibly unparsable to the weakening check, not become 2999-01-01.
    """
    substituted = substitute_placeholders(node)
    if not isinstance(node, dict) or not isinstance(substituted, dict):
        return substituted
    for kind in ("defeaters", "residuals"):
        source_entries = node.get(kind)
        target_entries = substituted.get(kind)
        if not isinstance(source_entries, list) or not isinstance(target_entries, list):
            continue
        for source_entry, target_entry in zip(source_entries, target_entries):
            if not isinstance(source_entry, dict) or not isinstance(target_entry, dict):
                continue
            review_after = source_entry.get("review_after")
            if preserve_review_date_placeholders and is_review_date_placeholder(
                review_after
            ):
                target_entry["review_after"] = review_after
            elif review_after == LEGACY_REVIEW_DATE_PLACEHOLDER:
                target_entry["review_after"] = DATE_SUBSTITUTION
    return substituted


def find_placeholder_strings(node: object, path: str = "$") -> list[tuple[str, str]]:
    """Return (json_path, value) pairs for every remaining ``REPLACE_WITH_``
    placeholder token (including the register templates' review-after date
    sentinel). A literal string such as ``YYYY-MM-DD`` used as real data — for
    example in a local ``extensions`` value — is not a placeholder."""
    found: list[tuple[str, str]] = []
    if isinstance(node, str):
        if "REPLACE_WITH_" in node:
            found.append((path, node))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            found.extend(find_placeholder_strings(item, f"{path}[{index}]"))
    elif isinstance(node, dict):
        for key, value in node.items():
            if is_generic_placeholder(key):
                found.append((f"{path}.<mapping-key>", key))
            found.extend(find_placeholder_strings(value, f"{path}.{key}"))
    return found


def find_register_placeholder_strings(node: object) -> list[tuple[str, str]]:
    """Find current and path-scoped legacy register placeholders.

    Besides generic ``REPLACE_WITH_`` tokens, this recognizes the v0.3.x
    review-date sentinel and seven bare prose prompts only at the register
    kind/direct-field paths where the released templates placed them.
    """
    found = find_placeholder_strings(node)
    if not isinstance(node, dict):
        return found
    for kind, field_placeholders in LEGACY_REGISTER_FIELD_PLACEHOLDERS.items():
        entries = node.get(kind)
        if not isinstance(entries, list):
            continue
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                continue
            review_after = entry.get("review_after")
            if (
                kind in ("defeaters", "residuals")
                and is_review_date_placeholder(review_after)
                and review_after != CURRENT_REVIEW_DATE_PLACEHOLDER
            ):
                found.append(
                    (f"$.{kind}[{index}].review_after", LEGACY_REVIEW_DATE_PLACEHOLDER)
                )
            for field, placeholder in field_placeholders.items():
                if entry.get(field) == placeholder:
                    found.append((f"$.{kind}[{index}].{field}", placeholder))
    return found


def validate_yaml_graph(node: object) -> int:
    """Validate and count the logical tree represented by a YAML graph.

    PyYAML preserves alias sharing. Memoizing each unique container's subtree
    cost keeps this calculation linear in the compact graph, while adding the
    cached cost at every reference still measures the expanded logical tree.
    Cycles, non-JSON data types, non-finite floats, and documents beyond the
    explicit budget fail before normalization or later semantic traversals.
    YAML dates and datetimes are the sole JSON-model extension accepted here;
    ``normalize_yaml`` converts them to ISO strings after this pass.
    """
    memo: dict[int, int] = {}
    active: set[int] = set()

    def count(value: object) -> int:
        value_type = type(value)
        if value is None or value_type in (bool, int, str):
            return 1
        if value_type is float:
            if not math.isfinite(value):
                raise YamlDataModelError(
                    "non-finite YAML floats are not permitted in policy data"
                )
            return 1
        if isinstance(value, (datetime.datetime, datetime.date)):
            return 1
        if value_type not in (list, dict):
            raise YamlDataModelError(
                f"YAML value type {value_type.__name__!r} is not permitted; "
                "policy YAML uses the JSON data model"
            )
        identity = id(value)
        if identity in active:
            raise YamlComplexityError("recursive YAML aliases are not supported")
        if identity in memo:
            return memo[identity]
        active.add(identity)
        total = 1
        if value_type is dict:
            for key in value:
                if type(key) is not str:
                    raise YamlDataModelError(
                        "non-string YAML mapping keys are not permitted; "
                        "policy YAML uses the JSON object model"
                    )
            total += len(value)  # mapping keys are logical scalar nodes too
            children = value.values()
        else:
            children = value
        for child in children:
            total += count(child)
            if total > MAX_YAML_EXPANDED_NODES:
                raise YamlComplexityError(
                    "YAML aliases expand beyond the "
                    f"{MAX_YAML_EXPANDED_NODES:,}-node policy limit"
                )
        active.remove(identity)
        memo[identity] = total
        return total

    return count(node)


def yaml_expanded_node_count(node: object) -> int:
    """Backward-compatible name for the validating YAML graph count."""
    return validate_yaml_graph(node)


def normalize_yaml(node: object, memo: dict[int, object] | None = None) -> object:
    """Map YAML-only scalar types onto the JSON data model.

    PyYAML parses an unquoted ``2026-12-31`` as ``datetime.date``; the schemas
    describe such fields as strings with ``format: date``, so dates are
    rendered back to their ISO form before validation.
    """
    if memo is None:
        memo = {}
    if isinstance(node, datetime.datetime):
        return node.isoformat()
    if isinstance(node, datetime.date):
        return node.isoformat()
    if type(node) is list:
        identity = id(node)
        if identity in memo:
            return memo[identity]
        normalized_list: list = []
        memo[identity] = normalized_list
        normalized_list.extend(normalize_yaml(item, memo) for item in node)
        return normalized_list
    if type(node) is dict:
        identity = id(node)
        if identity in memo:
            return memo[identity]
        normalized_dict: dict = {}
        memo[identity] = normalized_dict
        for key, value in node.items():
            normalized_dict[key] = normalize_yaml(value, memo)
        return normalized_dict
    if type(node) is float and not math.isfinite(node):
        raise YamlDataModelError(
            "non-finite YAML floats are not permitted in policy data"
        )
    if type(node) is str:
        return node
    if node is None or type(node) in (bool, int, float):
        return node
    raise YamlDataModelError(
        f"YAML value type {type(node).__name__!r} is not permitted; "
        "policy YAML uses the JSON data model"
    )


def load_yaml_with_loader(
    path: Path, loader: type[yaml.SafeLoader]
) -> tuple[object, str | None]:
    """Load bounded policy YAML with the selected safe mapping semantics."""
    try:
        size = path.stat().st_size
        if size > MAX_POLICY_YAML_BYTES:
            return None, (
                f"cannot process {path}: file is {size:,} bytes; policy YAML "
                f"is limited to {MAX_POLICY_YAML_BYTES:,} bytes"
            )
        with path.open(encoding="utf-8") as handle:
            document = yaml.load(handle, Loader=loader)
        validate_yaml_graph(document)
        return normalize_yaml(document), None
    except OSError as exc:
        return None, f"cannot read {path}: {exc}"
    except UnicodeDecodeError as exc:
        return None, f"cannot read {path} as UTF-8: {exc}"
    except yaml.YAMLError as exc:
        return None, f"cannot parse {path} as YAML: {exc}"
    except (RecursionError, ValueError, OverflowError) as exc:
        return None, f"cannot process {path}: {exc}"


def load_yaml(path: Path) -> tuple[object, str | None]:
    """Load YAML strictly; duplicate mapping keys are errors."""
    return load_yaml_with_loader(path, StrictSafeLoader)


def load_yaml_legacy(path: Path) -> tuple[object, str | None]:
    """Load pre-v0.4 base YAML with bounded last-key-wins compatibility."""
    return load_yaml_with_loader(path, LegacySafeLoader)


def load_json(path: Path) -> tuple[object, str | None]:
    """Load a JSON file; return (document, error_message)."""
    try:
        size = path.stat().st_size
        if size > MAX_POLICY_JSON_BYTES:
            return None, (
                f"cannot process {path}: file is {size:,} bytes; policy JSON "
                f"is limited to {MAX_POLICY_JSON_BYTES:,} bytes"
            )
        with path.open(encoding="utf-8") as handle:
            document = json.load(
                handle,
                object_pairs_hook=construct_unique_json_object,
                parse_constant=reject_nonfinite_json,
                parse_int=bounded_json_integer,
                parse_float=bounded_json_float,
            )
        # The C decoder can accept nesting deeper than Python's safe recursive
        # consumers. Enforce an iterative depth/node budget before JSON Schema
        # or policy code traverses the object.
        nodes = 0
        stack: list[tuple[object, int]] = [(document, 1)]
        while stack:
            value, depth = stack.pop()
            nodes += 1
            if nodes > MAX_POLICY_JSON_NODES:
                raise ValueError(
                    f"document exceeds the {MAX_POLICY_JSON_NODES:,}-node limit"
                )
            if depth > MAX_POLICY_JSON_NESTING:
                raise ValueError(
                    "nesting is too deep "
                    f"(limit {MAX_POLICY_JSON_NESTING} levels)"
                )
            if isinstance(value, dict):
                stack.extend((item, depth + 1) for item in value.values())
            elif isinstance(value, list):
                stack.extend((item, depth + 1) for item in value)
        return document, None
    except OSError as exc:
        return None, f"cannot read {path}: {exc}"
    except UnicodeDecodeError as exc:
        return None, f"cannot read {path} as UTF-8: {exc}"
    except json.JSONDecodeError as exc:
        return None, f"cannot parse {path} as JSON: {exc}"
    except ValueError as exc:
        return None, f"cannot parse {path} as strict JSON: {exc}"
    except RecursionError as exc:
        return None, f"cannot parse {path} as strict JSON: nesting is too deep ({exc})"


def schema_errors(instance: object, schema: dict, label: str) -> list[str]:
    """Validate an instance against a schema; return formatted error messages."""
    validator = Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
        registry=OFFLINE_SCHEMA_REGISTRY,
    )
    messages = [
        f"{label}: {path}: non-empty string contains no visible letter, "
        "number, punctuation, or symbol"
        for path in nonmeaningful_string_paths(instance)
    ]
    try:
        errors = sorted(validator.iter_errors(instance), key=lambda e: e.json_path)
    except Unresolvable as exc:
        messages.append(
            f"{label}: schema reference cannot be resolved offline: {exc}"
        )
        return messages
    for error in errors:
        messages.append(f"{label}: {error.json_path}: {error.message}")
    return messages


def nonmeaningful_string_paths(instance: object) -> list[str]:
    """JSON paths of non-empty strings made only of invisible/separator data."""
    found: list[str] = []
    stack: list[tuple[str, object]] = [("$", instance)]
    while stack:
        path, value = stack.pop()
        if isinstance(value, str):
            if value and not nonempty_string(value):
                found.append(path)
            continue
        if isinstance(value, list):
            stack.extend(
                (f"{path}[{index}]", item)
                for index, item in reversed(list(enumerate(value)))
            )
            continue
        if isinstance(value, dict):
            children: list[tuple[str, object]] = []
            for key, item in value.items():
                if key and not nonempty_string(key):
                    found.append(f"{path}.<mapping-key>")
                if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", key):
                    child_path = f"{path}.{key}"
                else:
                    child_path = f"{path}[{json.dumps(key, ensure_ascii=True)}]"
                children.append((child_path, item))
            stack.extend(reversed(children))
    return found


def listed_files(repo_root: Path) -> list[Path]:
    """Files to scan: tracked plus untracked-but-not-ignored (fallback: walk)."""
    try:
        completed = subprocess.run(
            [
                "git", "-C", str(repo_root), "ls-files", "-z",
                "--cached", "--others", "--exclude-standard",
            ],
            capture_output=True,
            check=True,
        )
        paths = [
            repo_root / os.fsdecode(raw)
            for raw in completed.stdout.split(b"\0")
            if raw
        ]
        # Keep symlink entries themselves. The abolished-token scan reads the
        # link payload rather than following it, including for broken or
        # out-of-tree links.
        return [path for path in paths if path.is_file() or path.is_symlink()]
    except (OSError, subprocess.CalledProcessError):
        return [
            path
            for path in repo_root.rglob("*")
            if (path.is_file() or path.is_symlink())
            and ".git" not in path.relative_to(repo_root).parts
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


def is_within(path: Path, root: Path) -> bool:
    """Whether ``path`` is ``root`` or one of its descendants."""
    return path == root or path.is_relative_to(root)


def is_same_filesystem_tree(path: Path, root: Path) -> bool:
    """Whether ``path`` is in ``root``, including filesystem-name aliases.

    Pure string/path comparison is insufficient on case-insensitive or
    normalization-insensitive filesystems: an adopter path using a differently
    cased spelling can still name the trusted checkout.  Compare every existing
    ancestor by filesystem identity as a backstop.
    """
    if is_within(path, root):
        return True
    candidate = path
    while True:
        try:
            if candidate.samefile(root):
                return True
        except (OSError, ValueError):
            pass
        parent = candidate.parent
        if parent == candidate:
            return False
        candidate = parent


def normalized_excluded_roots(paths: list[Path]) -> tuple[Path, ...]:
    """Canonical trusted roots that adopter-owned artifacts may not target."""
    unique: list[Path] = []
    for path in paths:
        try:
            resolved = path.resolve()
        except (OSError, RuntimeError, ValueError):
            # A broken/looping trusted-root symlink must not crash validation.
            # Keep its absolute lexical location as an exclusion; any adopter
            # artifact that traverses the loop is rejected by checked_project_path.
            resolved = path.absolute()
        if resolved not in unique:
            unique.append(resolved)
    return tuple(unique)


def nonportable_project_symlink(
    candidate: Path, project_root: Path
) -> tuple[str, str] | None:
    """Return the first symlink hop that cannot survive worktree relocation.

    Assurance comparisons materialize an older revision under a different
    directory. An absolute link, or a relative target that climbs above the
    repository before re-entering a checkout-shaped path, can resolve inside
    HEAD yet outside (or back into HEAD) from that detached base tree. Follow
    the lexical chain ourselves and require every hop to remain rooted without
    ever crossing the repository boundary.
    """
    try:
        resolved_root = project_root.resolve(strict=True)
        if candidate.is_absolute():
            lexical_root = (
                project_root
                if project_root.is_absolute()
                else Path.cwd() / project_root
            )
            relative = candidate.relative_to(lexical_root)
        else:
            try:
                relative = candidate.relative_to(project_root)
            except ValueError:
                relative = candidate
    except (OSError, RuntimeError, ValueError):
        return None  # the caller's ordinary containment resolution diagnoses it

    pending = list(relative.parts)
    current = resolved_root
    symlink_hops = 0
    while pending:
        component = pending.pop(0)
        if component in ("", "."):
            continue
        if component == "..":
            if current == resolved_root:
                return ("<path>", "..")
            current = current.parent
            continue
        probe = current / component
        try:
            mode = probe.lstat().st_mode
        except (FileNotFoundError, NotADirectoryError):
            # Missing content is diagnosed by the normal resolver. There can
            # be no further existing symlink below a missing component.
            return None
        except OSError:
            return None
        if not stat.S_ISLNK(mode):
            current = probe
            continue
        try:
            target = os.readlink(probe)
        except OSError:
            return None
        try:
            link_label = probe.relative_to(resolved_root).as_posix()
        except ValueError:
            link_label = os.fspath(probe)
        if os.path.isabs(target):
            return (link_label, target)
        symlink_hops += 1
        if symlink_hops > 40:
            return None  # Path.resolve reports the loop in its normal diagnostic
        pending = list(Path(target).parts) + pending
        current = probe.parent
    return None


def checked_project_path(
    candidate: Path,
    project_root: Path,
    report: Report,
    label: str,
    excluded_roots: tuple[Path, ...] = (),
) -> Path | None:
    """Resolve one adopter-controlled artifact path and enforce trust boundaries.

    Symlinks are allowed only when their final target remains inside the
    adopting project and outside the trusted profile/schema checkout. This
    preserves useful in-repository links without letting upstream templates or
    arbitrary host files satisfy adopter-owned obligations.
    """
    prohibited = next(
        (
            character
            for character in str(candidate)
            if ord(character) < 0x20 or ord(character) == 0x7F
        ),
        None,
    )
    if prohibited is not None:
        report.error(
            f"{label}: path contains prohibited control character "
            f"U+{ord(prohibited):04X}"
        )
        return None
    try:
        root = project_root.resolve()
        resolved = candidate.resolve()
    except (OSError, RuntimeError, ValueError) as exc:
        report.error(f"{label}: cannot resolve path: {exc}")
        return None
    if not is_within(resolved, root):
        report.error(f"{label}: resolves outside the project root")
        return None
    for excluded in excluded_roots:
        if is_same_filesystem_tree(resolved, excluded):
            report.error(
                f"{label}: resolves inside trusted/non-adopter data at "
                f"{excluded}; adopter-owned artifacts must live outside it"
            )
            return None
    nonportable_link = nonportable_project_symlink(candidate, project_root)
    if nonportable_link is not None:
        link, target = nonportable_link
        report.error(
            f"{label}: traverses non-portable symlink {link!r} -> {target!r}; "
            "every assurance-policy symlink target must remain inside the "
            "repository without an absolute target or an escape-and-reentry "
            "traversal"
        )
        return None
    try:
        lexical_root = Path(os.path.abspath(project_root))
        lexical = Path(os.path.abspath(candidate))
    except ValueError as exc:
        report.error(f"{label}: cannot normalize path: {exc}")
        return None
    try:
        lexical_relative = lexical.relative_to(lexical_root)
        no_in_project_link_target = root / lexical_relative
    except ValueError:
        lexical_relative = None
        no_in_project_link_target = lexical
    if no_in_project_link_target != resolved:
        try:
            lexical_label = (
                lexical_relative.as_posix()
                if lexical_relative is not None
                else lexical.relative_to(root).as_posix()
            )
            target_label = resolved.relative_to(root).as_posix()
            target_parent = resolved.parent.relative_to(root).as_posix() or "."
        except ValueError:  # containment above makes this defensive only
            lexical_label = str(lexical)
            target_label = str(resolved)
            target_parent = str(resolved.parent)
        report.warn(
            f"{label}: traverses an in-project symlink ({lexical_label!r} -> "
            f"{target_label!r}); CODEOWNERS must protect the lexical path "
            "(including retargeting), the resolved target, and its parent "
            f"directory {target_parent!r}"
        )
    return resolved


def check_declared_paths(
    project_root: Path,
    paths: dict[str, str],
    report: Report,
    excluded_roots: tuple[Path, ...] = (),
) -> dict[str, str]:
    """Reject declared artifact paths that resolve outside the project root.

    Absolute values or ``..`` traversal in ``paths:`` would otherwise escape
    ``--project-root`` (pathlib's ``/`` discards the left operand for absolute
    right operands). Offending keys are reported as errors and dropped so that
    no later check reads or accepts such files.
    """
    safe: dict[str, str] = {}
    # ``paths`` may already include the seven implicit split-layout defaults.
    # The public 256-entry budget applies to adopter-declared mappings, which
    # is checked by the schema and ``policy_path_mapping_contract_error``.
    # Do not make 256 valid custom mappings fail merely because resolving the
    # split contract adds defaults with distinct keys.
    effective_mapping_limit = MAX_POLICY_PATH_MAPPINGS + len(DEFAULT_PATHS)
    if len(paths) > effective_mapping_limit:
        report.error(
            "paths: effective mapping count exceeds the "
            f"{effective_mapping_limit}-entry limit "
            f"({MAX_POLICY_PATH_MAPPINGS} declared plus implicit defaults)"
        )
        return safe
    for key, value in paths.items():
        normalized = normalized_repository_relative_path(value)
        if normalized is None:
            report.error(
                f"paths.{key}: {value!r} must be a non-root repository-relative "
                "path that does not escape the project"
            )
            continue
        resolved = checked_project_path(
            project_root / value,
            project_root,
            report,
            f"paths.{key}: {value!r}",
            excluded_roots,
        )
        if resolved is not None:
            safe[key] = value
    return safe


def check_declared_security_paths(
    adoption: dict,
    project_root: Path,
    report: Report,
    excluded_roots: tuple[Path, ...] = (),
) -> None:
    """Apply lexical and resolved containment to declared security paths."""
    security = adoption.get("security")
    if not isinstance(security, dict):
        return
    for key, allow_root in (("policy", False), ("public_assurance_root", True)):
        value = security.get(key)
        if value is None:
            continue
        normalized = normalized_repository_relative_path(value, allow_root=allow_root)
        if normalized is None:
            root_note = " (the repository root '.' is allowed)" if allow_root else ""
            report.error(
                f"security.{key}: {value!r} must be a repository-relative path "
                f"that does not escape the project{root_note}"
            )
            continue
        checked_project_path(
            project_root / value,
            project_root,
            report,
            f"security.{key}: {value!r}",
            excluded_roots,
        )


def check_declared_review_record(
    adoption: dict,
    project_root: Path,
    report: Report,
    excluded_roots: tuple[Path, ...] = (),
) -> Path | None:
    """Apply the all-stage path boundary to a declared review record.

    Existence and content become requirements at HUMAN_REVIEWED, but merely
    carrying a path in a DRAFT declaration must never authorize an escape
    from adopter-owned repository content.
    """
    human_review = adoption.get("human_review")
    if not isinstance(human_review, dict) or "record" not in human_review:
        return None
    value = human_review.get("record")
    if normalized_repository_relative_path(value) is None:
        report.error(
            f"human_review.record: {value!r} must be a non-root "
            "repository-relative path that does not escape the project"
        )
        return None
    return checked_project_path(
        project_root / value,
        project_root,
        report,
        f"human_review.record: {value!r}",
        excluded_roots,
    )


def read_utf8_text_exact(path: Path) -> str:
    """Decode UTF-8 without Python's universal-newline translation."""
    return path.read_bytes().decode("utf-8")


def read_version_file(path: Path) -> tuple[str | None, str | None]:
    """Read one exact VERSION token, allowing one final line terminator."""
    try:
        content = read_utf8_text_exact(path)
    except OSError as exc:
        return None, f"cannot read {path}: {exc}"
    except UnicodeDecodeError as exc:
        return None, f"cannot read {path} as UTF-8: {exc}"
    # Permit one conventional LF or CRLF terminator, but never treat a bare
    # CR as a record boundary. Do not normalize spaces, tabs, or extra blank
    # lines: the pin must match the canonical single-line content exactly.
    if content.endswith("\r\n"):
        content = content[:-2]
    elif content.endswith("\n"):
        content = content[:-1]
    if "\n" in content or "\r" in content:
        return None, f"{path} must contain exactly one canonical version line"
    return content, None


def register_entries(document: object, kind: str) -> list | None:
    """Extract the entry list of a register document, or None if unusable."""
    if isinstance(document, dict) and isinstance(document.get(kind), list):
        return document[kind]
    return None


def nonempty_string(value: object) -> bool:
    """Whether text contains at least one visibly meaningful code point.

    Unicode format/control/separator characters (for example a zero-width
    space) are not human identity, evidence, authority, or prose. Letters,
    numbers, punctuation, and symbols remain valid in every language.
    """
    return isinstance(value, str) and any(
        unicodedata.category(character)[0] in ("L", "N", "P", "S")
        for character in value
    )


def read_project_text_file(
    candidate: Path,
    project_root: Path,
    report: Report,
    label: str,
    excluded_roots: tuple[Path, ...] = (),
    *,
    missing_message: str | None = None,
    require_nonempty: bool = True,
    prechecked_resolved: Path | None = None,
) -> str | None:
    """Read an adopter-owned UTF-8 file after containment/trust checks."""
    resolved = prechecked_resolved or checked_project_path(
        candidate, project_root, report, label, excluded_roots
    )
    if resolved is None:
        return None
    if not resolved.is_file():
        if candidate.is_symlink() or candidate.exists():
            report.error(f"{label}: exists but is not a readable regular file")
        else:
            report.error(missing_message or f"{label}: missing")
        return None
    try:
        size = resolved.stat().st_size
        if size > MAX_PROJECT_TEXT_BYTES:
            report.error(
                f"{label}: file exceeds the "
                f"{MAX_PROJECT_TEXT_BYTES:,}-byte project-text limit"
            )
            return None
        text = read_utf8_text_exact(resolved)
    except (OSError, UnicodeDecodeError) as exc:
        report.error(f"{label}: cannot read as UTF-8 text: {exc}")
        return None
    if require_nonempty and not nonempty_string(text):
        report.error(
            f"{label}: file is empty or whitespace-only, or contains no "
            "visible meaningful content"
        )
        return None
    return text


def visible_markdown_text(text: str) -> str:
    """Return prose outside HTML comments and fenced code blocks.

    This is intentionally a small, conservative Markdown boundary rather than
    a renderer.  Unclosed comments or fences hide the remainder so examples
    and presentation metadata cannot satisfy a normative text check.
    """
    without_comments = HTML_COMMENT_RE.sub("", text)
    without_nonprose_html = NON_PROSE_HTML_BLOCK_RE.sub("", without_comments)
    visible: list[str] = []
    fence_char: str | None = None
    fence_length = 0
    html_stack: list[str] = []
    for line in physical_text_lines(without_nonprose_html):
        candidate = line.lstrip(" ")
        indentation = len(line) - len(candidate)
        marker = re.match(r"(`{3,}|~{3,})", candidate) if indentation <= 3 else None
        if (
            marker is not None
            and marker.group(1)[0] == "`"
            and "`" in candidate[len(marker.group(1)) :]
        ):
            # CommonMark does not open a backtick fence when its info string
            # itself contains a backtick. Treat the line as visible prose.
            marker = None
        if fence_char is None:
            if marker is not None:
                fence_char = marker.group(1)[0]
                fence_length = len(marker.group(1))
                continue
            stripped = line.strip()
            closing = RAW_HTML_CLOSE_LINE_RE.fullmatch(stripped)
            opening = RAW_HTML_OPEN_LINE_RE.fullmatch(stripped)
            if html_stack:
                if HTML_VISIBLE_ELEMENT_RE.search(stripped) is not None:
                    visible.append(f"HTML content: {line}")
                    continue
                if closing is not None:
                    if closing.group("tag").lower() == html_stack[-1]:
                        html_stack.pop()
                    continue
                elif opening is not None:
                    tag = opening.group("tag").lower()
                    if tag in HTML_VISIBLE_VOID_ELEMENTS:
                        visible.append(f"HTML content: {line}")
                        continue
                    if not stripped.endswith("/>") and tag not in HTML_VOID_ELEMENTS:
                        html_stack.append(tag)
                    continue
                # Ordinary raw-HTML containers render their text content.
                # Preserve that content as visibly ordinary prose so it ends
                # the leading directive block, while marking it non-top-level
                # so a directive nested inside <div>/<details>/etc. cannot
                # satisfy the contract. Script/style/template/pre/code bodies
                # were removed in the dedicated non-prose pass above.
                rendered = html.unescape(re.sub(r"<[^>]*>", "", line))
                for rendered_line in physical_text_lines(rendered):
                    if nonempty_string(rendered_line):
                        # Prefix every decoded physical line. An HTML entity
                        # such as ``&#10;`` must not inject an unmarked line
                        # that can masquerade as top-level Markdown.
                        visible.append(f"HTML content: {rendered_line}")
                continue
            if opening is not None:
                tag = opening.group("tag").lower()
                if tag in HTML_VISIBLE_VOID_ELEMENTS:
                    visible.append(f"HTML content: {line}")
                    continue
                if not stripped.endswith("/>") and tag not in HTML_VOID_ELEMENTS:
                    html_stack.append(tag)
                # A raw-HTML wrapper is presentation, not a top-level
                # directive. Hide an empty/container wrapper line; visibly
                # rendered void elements above remain ordinary content.
                continue
            if closing is not None:
                continue
            visible.append(line)
            continue
        if (
            marker is not None
            and marker.group(1)[0] == fence_char
            and len(marker.group(1)) >= fence_length
            and candidate[len(marker.group(1)) :].strip() == ""
        ):
            fence_char = None
            fence_length = 0
    return "\n".join(visible)


def has_required_reading_order(text: str, adoption_reference: str) -> bool:
    """Whether visible top-level prose carries the canonical ordered block."""
    lines = physical_text_lines(visible_markdown_text(text))
    expected = (
        "Before any material change, read:",
        "1. `AGENTIC_ASSURANCE.md`;",
        f"2. `{adoption_reference}`;",
    )
    for index, line in enumerate(lines):
        if line != expected[0]:
            continue
        following = [
            candidate for candidate in lines[index + 1 :] if candidate.strip()
        ]
        if tuple(following[:2]) == expected[1:]:
            return True
    return False


ROOT_GUIDE_FILES = ("AGENTIC_ASSURANCE.md", "AGENTS.md")

# Lite-envelope fields that are prose, not structured register data.
LITE_PROSE_KEYS = ("system", "purpose", "non_goals")


def check_root_reading_order(
    project_root: Path,
    adoption_reference: str,
    report: Report,
    excluded_roots: tuple[Path, ...] = (),
) -> None:
    """Require nonempty root guides with the canonical visible reading order."""
    for name in ROOT_GUIDE_FILES:
        text = read_project_text_file(
            project_root / name,
            project_root,
            report,
            name,
            excluded_roots,
            missing_message=f"{name} missing at project root",
        )
        if text is None:
            continue
        if not has_required_reading_order(text, adoption_reference):
            report.error(
                f"{name}: does not contain the required visible top-level "
                "assurance reading-order block in canonical order "
                f"(AGENTIC_ASSURANCE.md, then {adoption_reference})"
            )
        else:
            report.ok(f"{name} present at project root with assurance reading order")


def check_active_specification_workflow(
    adoption: dict,
    project_root: Path,
    report: Report,
    excluded_roots: tuple[Path, ...] = (),
    *,
    required: bool = True,
) -> None:
    """Runtime backstop for a declared material-change workflow.

    Active adopters must declare one. Archived adopters may omit it, but if
    they retain the block as archival metadata it must still resolve to real,
    adopter-owned content rather than an escaping or stale template path.
    """
    workflow = adoption.get("specification_workflow")
    if workflow is None and not required:
        return
    if not isinstance(workflow, dict):
        report.error("specification_workflow is missing or not a mapping")
        return
    if not nonempty_string(workflow.get("system")):
        report.error("specification_workflow.system is missing")
    root_value = workflow.get("root")
    if not nonempty_string(root_value):
        report.error("specification_workflow.root is empty or missing")
        return
    if normalized_repository_relative_path(root_value, allow_root=True) is None:
        report.error(
            f"specification_workflow.root: {root_value!r} must be a "
            "repository-relative path that does not escape the project "
            "(the repository root '.' is allowed)"
        )
        return
    candidate = project_root / root_value
    resolved = checked_project_path(
        candidate,
        project_root,
        report,
        f"specification_workflow.root: {root_value!r}",
        excluded_roots,
    )
    if resolved is None:
        return
    if not candidate.exists():
        if candidate.is_symlink():
            report.error(
                f"specification_workflow.root: {root_value!r} is a broken symlink"
            )
        else:
            report.error(
                f"specification_workflow.root: {root_value!r} does not exist"
            )
        return
    if candidate.is_file():
        try:
            if resolved.stat().st_size > MAX_WORKFLOW_ENTRY_BYTES:
                report.error(
                    f"specification_workflow.root: {root_value!r} exceeds "
                    f"the {MAX_WORKFLOW_ENTRY_BYTES:,}-byte entry-document "
                    "limit; map a narrower entry document"
                )
                return
            content = read_utf8_text_exact(resolved)
        except (OSError, UnicodeDecodeError) as exc:
            report.error(
                f"specification_workflow.root: {root_value!r} cannot be read "
                f"as UTF-8 text: {exc}"
            )
            return
        if not nonempty_string(content):
            report.error(
                f"specification_workflow.root: {root_value!r} has no visible "
                "meaningful content"
            )
            return
    elif candidate.is_dir():
        total_entries = 0
        regular_entries: list[tuple[Path, int]] = []
        directories: list[tuple[Path, int]] = [(resolved, 0)]
        while directories:
            directory, depth = directories.pop()
            try:
                children = directory.iterdir()
                for entry in children:
                    if entry.name in (".git", ".assurance-profile-pin"):
                        continue
                    if any(
                        is_same_filesystem_tree(entry, excluded)
                        for excluded in excluded_roots
                    ):
                        continue
                    total_entries += 1
                    if total_entries > MAX_WORKFLOW_DIRECTORY_ENTRIES:
                        report.error(
                            f"specification_workflow.root: {root_value!r} has more "
                            f"than {MAX_WORKFLOW_DIRECTORY_ENTRIES:,} entries "
                            "within its bounded workflow tree; map a narrower "
                            "workflow directory or entry document"
                        )
                        return
                    try:
                        entry_stat = entry.lstat()
                    except OSError:
                        continue
                    # Never follow child symlinks: only the explicitly declared
                    # root receives the full containment/portability check.
                    if stat.S_ISDIR(entry_stat.st_mode):
                        if depth < MAX_WORKFLOW_DIRECTORY_DEPTH:
                            directories.append((entry, depth + 1))
                    elif stat.S_ISREG(entry_stat.st_mode):
                        regular_entries.append((entry, entry_stat.st_size))
            except OSError as exc:
                if directory == resolved:
                    report.error(
                        f"specification_workflow.root: {root_value!r} cannot "
                        f"be read: {exc}"
                    )
                    return
                continue

        scanned_bytes = 0
        entry_document_found = False
        for entry, entry_size in sorted(
            regular_entries,
            key=lambda item: os.fsencode(item[0].relative_to(resolved)),
        ):
            if entry_size > MAX_WORKFLOW_ENTRY_BYTES:
                continue
            scanned_bytes += entry_size
            if scanned_bytes > MAX_WORKFLOW_DIRECTORY_SCAN_BYTES:
                report.error(
                    f"specification_workflow.root: {root_value!r} requires "
                    f"more than {MAX_WORKFLOW_DIRECTORY_SCAN_BYTES // (1024 * 1024)} "
                    "MiB of entry-document inspection; map a "
                    "narrower workflow directory or entry document"
                )
                return
            try:
                entry_content = read_utf8_text_exact(entry)
            except (OSError, UnicodeDecodeError):
                continue
            if nonempty_string(entry_content):
                entry_document_found = True
                break
        if not entry_document_found:
            report.error(
                f"specification_workflow.root: {root_value!r} contains no "
                "readable, non-empty UTF-8 regular entry document within "
                f"{MAX_WORKFLOW_DIRECTORY_DEPTH} directory levels"
            )
            return
    else:
        report.error(
            f"specification_workflow.root: {root_value!r} is not a regular "
            "file or directory"
        )
        return
    report.ok(
        f"specification_workflow.root {root_value!r} resolves to an adopter-owned path"
    )


def is_http_url(value: object) -> bool:
    if not nonempty_string(value):
        return False
    # Match the profile's deliberately narrow ASCII URL surface before urllib
    # can normalize controls or accept IRI-only/raw implementation characters.
    # The grammar also makes every percent escape a complete hex triplet.
    if HTTP_URL_RE.fullmatch(value) is None:
        return False
    try:
        parsed = urlparse(value)
        hostname = parsed.hostname
        port = parsed.port  # validates numeric syntax and the 0..65535 range
    except (TypeError, ValueError):
        # Invalid bracketed IPv6 hosts raise instead of producing a partial
        # ParseResult; malformed and out-of-range ports raise on access.
        return False
    if parsed.scheme not in ("http", "https") or not hostname:
        return False
    try:
        for component in (parsed.path, parsed.query, parsed.fragment):
            unquote_to_bytes(component).decode("utf-8")
    except UnicodeDecodeError:
        # The grammar guarantees complete %XX triplets; this additionally
        # proves that encoded non-ASCII octets form real UTF-8.
        return False
    if (
        parsed.username is not None
        or parsed.password is not None
        or "@" in parsed.netloc
    ):
        # Approval records are references, never credential-bearing URLs.
        return False
    if parsed.netloc.endswith(":"):
        # urllib treats an explicitly empty port like an omitted one. Keep the
        # durable-review URL syntax unambiguous instead.
        return False
    # Access above is intentional validation even when no port was supplied.
    del port
    return True


def is_iso_date_or_datetime(value: object) -> bool:
    if not nonempty_string(value):
        return False
    text = value.strip()
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", text):
        try:
            datetime.date.fromisoformat(text)
            return True
        except ValueError:
            return False
    if not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt][0-9]{2}:[0-9]{2}:[0-9]{2}"
        r"(?:\.[0-9]+)?(?:[Zz]|[+-][0-9]{2}:[0-9]{2})",
        text,
    ):
        return False
    try:
        parse_rfc3339_datetime(text)
        return True
    except ValueError:
        return False


def parse_rfc3339_datetime(text: str) -> tuple[datetime.datetime, bool]:
    """Parse RFC 3339, accepting ``60`` only at a real UTC leap second."""
    normalized = text[:-1] + "+00:00" if text[-1:] in ("Z", "z") else text
    leap_second = normalized[17:19] == "60"
    if leap_second:
        # ``datetime`` deliberately rejects second 60. Parse the immediately
        # preceding representable second, then prove that its UTC equivalent
        # is 23:59:59 on a date where a positive leap second was inserted.
        normalized = normalized[:17] + "59" + normalized[19:]
    moment = datetime.datetime.fromisoformat(normalized)
    if leap_second:
        try:
            preceding_utc = moment.astimezone(datetime.timezone.utc)
        except (OverflowError, ValueError) as exc:
            raise ValueError("leap-second timestamp is outside UTC range") from exc
        if not (
            preceding_utc.date() in RFC3339_POSITIVE_LEAP_SECOND_DATES
            and preceding_utc.hour == 23
            and preceding_utc.minute == 59
            and preceding_utc.second == 59
        ):
            raise ValueError("second 60 is not an inserted UTC leap second")
    return moment, leap_second


def latest_current_civil_date() -> datetime.date:
    """Latest date that can currently be true in any civil time zone."""
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    return (now_utc + datetime.timedelta(hours=14)).date()


def is_future_iso_date_or_datetime(value: object) -> bool:
    """Whether a syntactically valid review date/time lies in the future."""
    if not is_iso_date_or_datetime(value):
        return False
    text = value.strip()
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", text):
        # A date has no offset. Allow UTC+14's possible one-day lead so the
        # same completed act is not accepted locally and rejected by a UTC CI
        # runner. Anything later is future-dated in every civil time zone.
        return datetime.date.fromisoformat(text) > latest_current_civil_date()
    moment, leap_second = parse_rfc3339_datetime(text)
    if leap_second:
        try:
            moment += datetime.timedelta(seconds=1)
        except OverflowError:
            # The only overflowing valid case is beyond datetime.max and is
            # necessarily later than the present.
            return True
    # Compare in the parsed moment's own fixed offset. Converting extreme
    # years (0001/9999) to UTC can overflow at the date boundary even though
    # the RFC 3339 timestamp itself is valid.
    return moment > datetime.datetime.now(datetime.timezone.utc).astimezone(
        moment.tzinfo
    )


def iso_date_component(value: object) -> datetime.date | None:
    """Civil date written in a valid ISO date or offset timestamp."""
    if not is_iso_date_or_datetime(value):
        return None
    return datetime.date.fromisoformat(value.strip()[:10])


def check_human_review_temporal_semantics(adoption: dict, report: Report) -> None:
    """Validate approval shape and reject future-dated completed human acts.

    JSON Schema ``format`` support depends on optional packages in jsonschema.
    These checks are therefore explicit and stage-independent: DRAFT cannot
    turn a malformed approval timestamp or URI into accepted policy data just
    because a format checker is unavailable in the locked environment.
    """
    review = adoption.get("human_review")
    if not isinstance(review, dict):
        return
    review_date = coerce_date(review.get("date"))
    if review_date is not None and review_date > latest_current_civil_date():
        report.error(
            "human_review.date is in the future — record a completed review "
            "only after it has occurred"
        )
    approvals = review.get("approvals")
    for index, entry in enumerate(approvals if isinstance(approvals, list) else []):
        if not isinstance(entry, dict):
            continue
        if "review_url" in entry and not is_http_url(entry.get("review_url")):
            report.error(
                f"human_review.approvals[{index}].review_url must be an "
                "absolute, syntactically valid HTTP(S) URL with a host, no "
                "user information, and a valid optional port"
            )
        if "at" in entry and not is_iso_date_or_datetime(entry.get("at")):
            report.error(
                f"human_review.approvals[{index}].at must be a valid ISO 8601 "
                "date or RFC 3339 timestamp"
            )
        elif is_future_iso_date_or_datetime(entry.get("at")):
            report.error(
                f"human_review.approvals[{index}].at is in the future — "
                "record approval only after it has occurred"
            )


def check_issue_integration_semantics(adoption: dict, report: Report) -> None:
    """Reject explicit Issue policies that contradict PROFILE sections 13-14."""
    integration = adoption.get("issue_integration")
    if not isinstance(integration, dict):
        return
    if integration.get("public_security_issues_allowed") is True:
        report.error(
            "issue_integration.public_security_issues_allowed must be false — "
            "potentially exploitable findings require private reporting"
        )
    if integration.get("closing_requires_artifact_update") is False:
        report.error(
            "issue_integration.closing_requires_artifact_update must be true — "
            "a material Issue is not resolved until its required assurance "
            "artifact, evidence, defeater, and residual updates are complete"
        )


@lru_cache(maxsize=4096)
def tokenize_path_glob(pattern: str) -> tuple[tuple[str, str | None], ...]:
    """Tokenize the supported gitwildmatch subset without using regexes."""
    tokens: list[tuple[str, str | None]] = []
    index = 0
    while index < len(pattern):
        if pattern.startswith("**/", index):
            tokens.append(("globstar_dirs", None))
            index += 3
        elif pattern.startswith("**", index):
            tokens.append(("globstar", None))
            index += 2
        elif pattern[index] == "*":
            tokens.append(("star", None))
            index += 1
        elif pattern[index] == "?":
            tokens.append(("question", None))
            index += 1
        else:
            tokens.append(("literal", pattern[index]))
            index += 1
    return tuple(tokens)


def path_glob_matches(pattern: str, path: str) -> bool:
    """Match the supported path-glob subset in bounded polynomial time.

    The prior regex translation emitted one ``.*`` per ``**``. Adversarial
    patterns with many overlapping globstars could make a backtracking regex
    take exponential time on a near miss. This dynamic program evaluates each
    token/path position once, using O(len(path)) memory.

    Supported subset: ``**/`` (any leading directories, including none),
    ``**`` (anything, across directory separators), ``*`` (anything within
    one path segment), ``?`` (one character within a segment). Everything
    else matches literally, and the entire repository-relative path must
    match.
    """
    tokens = tokenize_path_glob(pattern)
    path_length = len(path)

    # `following[i]` means the tokens already processed to the right match
    # path[i:]. With no token left, only the empty suffix matches.
    following = [False] * (path_length + 1)
    following[path_length] = True

    for kind, literal in reversed(tokens):
        current = [False] * (path_length + 1)
        if kind == "literal":
            for position in range(path_length - 1, -1, -1):
                current[position] = (
                    path[position] == literal and following[position + 1]
                )
        elif kind == "question":
            for position in range(path_length - 1, -1, -1):
                current[position] = (
                    path[position] != "/" and following[position + 1]
                )
        elif kind == "star":
            current[path_length] = following[path_length]
            for position in range(path_length - 1, -1, -1):
                current[position] = following[position] or (
                    path[position] != "/" and current[position + 1]
                )
        elif kind == "globstar":
            current[path_length] = following[path_length]
            for position in range(path_length - 1, -1, -1):
                current[position] = following[position] or current[position + 1]
        else:  # globstar_dirs
            current[path_length] = following[path_length]
            a_directory_prefix_matches = False
            for position in range(path_length - 1, -1, -1):
                if path[position] == "/" and following[position + 1]:
                    a_directory_prefix_matches = True
                current[position] = (
                    following[position] or a_directory_prefix_matches
                )
        following = current

    return following[0]


def canonical_repository_relative_glob(value: object) -> bool:
    """Whether a component glob addresses canonical Git-path input.

    Changed-file records are canonical repository-relative POSIX paths. A
    glob with an absolute spelling or an empty/``.``/``..`` component can
    never match that domain reliably, so accepting it would silently disable
    impact routing. Wildcards remain ordinary characters for this lexical
    check; only slash-delimited path structure is constrained.
    """
    if not nonempty_string(value) or posixpath.isabs(value):
        return False
    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in value):
        return False
    return all(component not in ("", ".", "..") for component in value.split("/"))


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


def check_completed_register_human_acts(
    registers: dict[str, list | None], report: Report
) -> None:
    """Reject future-dated completed register acts for every profile mode.

    Archived repositories intentionally skip active-state conclusions and
    review schedules, but a retained residual acceptance is still a claimed
    completed human act. Its date cannot become valid merely because the
    repository is archived.
    """
    residuals = registers.get("residuals")
    if not isinstance(residuals, list):
        return
    for entry in residuals:
        if not isinstance(entry, dict):
            continue
        accepted_at = coerce_date(entry.get("accepted_at"))
        if accepted_at is None or accepted_at <= latest_current_civil_date():
            continue
        label = entry.get("id") if nonempty_string(entry.get("id")) else "<no id>"
        report.error(
            f"residual {label} accepted_at {accepted_at.isoformat()} is "
            "in the future — record acceptance only after it has occurred"
        )


def check_register_disposition_grounds(
    registers: dict[str, list | None], report: Report
) -> None:
    """Ground completed residual/defeater dispositions in every profile mode.

    Archived repositories may retain old active registers as history without
    reactivating cross-reference, invariant, or review-schedule obligations.
    A retained entry that claims a completed human acceptance or resolution,
    however, cannot become true through a template placeholder.
    """
    check_completed_register_human_acts(registers, report)

    residuals = registers.get("residuals")
    for entry in residuals if isinstance(residuals, list) else []:
        if not isinstance(entry, dict):
            continue
        label = entry.get("id") if nonempty_string(entry.get("id")) else "<no id>"
        status = entry.get("status")
        if status == "ACCEPTED":
            for field in RESIDUAL_ACCEPTANCE_FIELDS:
                if not committed_string(entry.get(field)):
                    report.error(
                        f"residual {label} is ACCEPTED but {field} is empty, "
                        "missing, or an unfilled placeholder"
                    )
        if status == "RESOLVED" and not committed_string(
            entry.get("resolution_note")
        ):
            report.error(
                f"residual {label} is RESOLVED but resolution_note is empty, "
                "missing, or an unfilled placeholder"
            )

    defeaters = registers.get("defeaters")
    for entry in defeaters if isinstance(defeaters, list) else []:
        if not isinstance(entry, dict):
            continue
        status = entry.get("status")
        if status in CLOSED_DEFEATER_STATUSES and not committed_string(
            entry.get("resolution")
        ):
            label = entry.get("id") if nonempty_string(entry.get("id")) else "<no id>"
            report.error(
                f"defeater {label} is {status} but resolution is empty, "
                "missing, or an unfilled placeholder"
            )


# ---------------------------------------------------------------------------
# Semantic checks (shared by self-check and adopter)
# ---------------------------------------------------------------------------


def check_semantics(
    registers: dict[str, list | None],
    report: Report,
    strict_review_dates: bool = False,
    today: datetime.date | None = None,
    ok_label: str = "semantic checks",
    profiles: list[str] | None = None,
    emit_ok: bool = True,
) -> None:
    """Cross-entry semantic checks over the four registers.

    ``registers`` maps a register kind to its entry list. Three states are
    encoded: key absent = the register file does not exist; value ``None`` =
    the file exists but is unusable (a load or structure error was already
    reported); value list = usable raw entries. Schema-only placeholder
    substitution must not reach this function.

    ``emit_ok=False`` retains all checks while suppressing the aggregate
    success line when an enclosing document or section is already unusable.

    Checks: unique IDs, cross-reference integrity, VERIFIED critical
    invariants carry committed enforcement and verification references,
    every service critical invariant carries the same references regardless
    of conclusion, every affirmative intent disposition
    (INTENDED/COMPATIBILITY/DEPRECATED) carries committed intent.authority,
    every ACCEPTED residual carries its acceptance record, RESOLVED/closed
    entries carry their grounds, and passed review_after dates (WARN, or ERROR
    with ``strict_review_dates``).

    Deliberate design decision: a VERIFIED critical invariant is NOT required
    to carry intent.authority — conclusion status and intent classification
    are independent axes (PROFILE.md section 4). Authority is required by the
    affirmative classification alone, at any severity.
    """
    if today is None:
        # Civil review dates have no offset. Use the same host-independent
        # boundary as completed human acts so a validation result cannot flip
        # merely because the runner's local TZ differs.
        today = latest_current_civil_date()
    findings_before = sum(
        1 for level, _ in report.results if level in ("error", "warn")
    )
    complete = all(entries is not None for entries in registers.values())
    if profiles is not None and profiles != ["archived"]:
        complete = complete and all(
            kind in registers and registers[kind] is not None
            for kind in ("invariants", "residuals")
        )
        if "trust-critical" in profiles:
            complete = complete and (
                "claims" in registers and registers["claims"] is not None
            )
    check_register_disposition_grounds(registers, report)

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
        # verdict. Service-critical invariants carry the same operational
        # obligation at every conclusion status. Combine the predicates so a
        # VERIFIED service invariant produces one finding per missing field,
        # not duplicate generic and profile-specific findings.
        is_critical = entry.get("severity") == "critical"
        service_required = (
            is_critical and profiles is not None and "service" in profiles
        )
        verified_required = is_critical and entry.get("status") == "VERIFIED"
        if service_required or verified_required:
            requirement = (
                "is critical under profile 'service'"
                if service_required
                else "is VERIFIED with severity critical"
            )
            for list_name in ("enforcement", "verification"):
                value = entry.get(list_name)
                if not isinstance(value, list) or not value:
                    report.error(
                        f"invariant {label} {requirement} but its {list_name} "
                        "list is empty"
                    )
                elif not any(committed_string(item) for item in value):
                    report.error(
                        f"invariant {label} {requirement} but its {list_name} "
                        "list has no committed reference"
                    )
        # 4. Every affirmative intent disposition requires recorded human
        # authority, at any severity. COMPATIBILITY names an explicit
        # obligation and DEPRECATED an approved removal path just as INTENDED
        # names approved purpose; none can be established by an agent alone.
        intent = entry.get("intent")
        if (
            isinstance(intent, dict)
            and intent.get("classification")
            in ("INTENDED", "COMPATIBILITY", "DEPRECATED")
        ):
            if not committed_string(intent.get("authority")):
                report.error(
                    f"invariant {label} has intent.classification "
                    f"{intent.get('classification')} but intent.authority is "
                    "empty or null, or is an unfilled placeholder"
                )

    # 5. Passed review_after dates (defeaters and residuals).
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

    findings_after = sum(
        1 for level, _ in report.results if level in ("error", "warn")
    )
    if emit_ok and findings_after == findings_before and complete:
        report.ok(f"{ok_label} — ids unique, references resolve, statuses grounded")


def check_lite_sections(
    document: object,
    label: str,
    schemas: dict[str, dict],
    report: Report,
    schema_label_prefix: str = "",
    validation_document: object | None = None,
) -> dict[str, list | None]:
    """Validate the register sections of a lite assurance document.

    Register entry shapes are defined solely by the register schemas: each
    present section is extracted into a synthetic register document
    (``{version: 1, <kind>: [...]}``) and validated against the corresponding
    register schema, so nothing is duplicated in the lite envelope schema.

    ``document`` is always the raw policy document returned to semantic
    checks. ``validation_document`` may be a placeholder-substituted copy used
    only for schema validation. Returns the same kind -> entries mapping
    ``check_artifacts`` produces for the split layout: key absent = section
    absent, value ``None`` = section unusable, value list = usable raw entries.
    """
    registers: dict[str, list | None] = {}
    if not isinstance(document, dict):
        return registers
    schema_source = (
        validation_document if isinstance(validation_document, dict) else document
    )
    for kind in LITE_SECTION_KINDS:
        if kind not in document:
            continue
        schema_name, _default = ARTIFACT_KINDS[kind]
        raw_synthetic = {"version": 1, kind: document[kind]}
        schema_synthetic = {
            "version": 1,
            kind: schema_source.get(kind),
        }
        registers[kind] = register_entries(raw_synthetic, kind)
        schema = schemas.get(schema_name)
        if schema is None:
            report.error(
                f"{label}: section '{kind}' cannot be validated, "
                f"{schema_label_prefix}{schema_name} unusable"
            )
            registers[kind] = None
            continue
        errors = schema_errors(
            schema_synthetic, schema, f"{label}: section '{kind}'"
        )
        if errors:
            for message in errors:
                report.error(message)
            registers[kind] = None
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
        try:
            Draft202012Validator.check_schema(document)
        except SchemaError as exc:
            report.error(
                f"schemas/{name}: invalid JSON Schema draft 2020-12: {exc.message}"
            )
            continue
        report.ok(
            f"schemas/{name} parses and is valid JSON Schema draft 2020-12"
        )
        schemas[name] = document
    return schemas


def check_template(
    repo_root: Path, template: str, schema_name: str, schemas: dict[str, dict], report: Report
) -> object:
    """Validate one template; return the raw document for semantic checks.

    Returns None when the template cannot be loaded or the schema is
    unusable, so the caller can feed register templates to the semantic
    checks only when a document is actually available. Placeholder
    substitution is confined to schema validation: semantic checks must never
    mistake a synthetic dummy for committed adopter data.
    """
    schema = schemas.get(schema_name)
    if schema is None:
        report.error(f"templates/{template}: cannot validate, schemas/{schema_name} unusable")
        return None
    document, error = load_yaml(repo_root / "templates" / template)
    if error is not None:
        report.error(f"templates/{template}: {error}")
        return None
    substitute = (
        substitute_placeholders
        if schema_name == "adoption.schema.json"
        else substitute_register_placeholders
    )
    substituted = substitute(document)
    errors = schema_errors(substituted, schema, f"templates/{template}")
    if errors:
        for message in errors:
            report.error(message)
        return None
    else:
        report.ok(
            f"templates/{template} validates against schemas/{schema_name} "
            "(placeholders substituted)"
        )
    return document


def check_lite_template(
    repo_root: Path,
    schemas: dict[str, dict],
    report: Report,
    template: str = LITE_TEMPLATE,
) -> None:
    """Validate a lite-layout assurance template through the lite-layout flow.

    Mirrors what an adopter's ``.agentic-assurance/assurance.yaml`` faces:
    envelope validation against the lite schema, per-section validation
    against the register schemas, and the shared semantic checks. Runs for
    every shipped lite template so none can drift out of validity.
    """
    label = f"templates/{template}"
    schema = schemas.get(LITE_SCHEMA_FILE)
    if schema is None:
        report.error(f"{label}: cannot validate, schemas/{LITE_SCHEMA_FILE} unusable")
        return
    document, error = load_yaml(repo_root / "templates" / template)
    if error is not None:
        report.error(f"{label}: {error}")
        return
    substituted = substitute_register_placeholders(document)
    errors = schema_errors(substituted, schema, label)
    if errors:
        for message in errors:
            report.error(message)
    else:
        report.ok(
            f"{label} validates against schemas/{LITE_SCHEMA_FILE} "
            "(placeholders substituted)"
        )
    if template in (LITE_TEMPLATE, LITE_MINIMAL_TEMPLATE) and not (
        isinstance(substituted, dict)
        and nonempty_string(substituted.get("system"))
    ):
        report.error(
            f"{label}: shipped lite template must include a non-empty "
            "'system' section to remain a complete four-file starting path; "
            "an adopter may delete it only when adding an external SYSTEM.md"
        )
    section_errors_before = sum(
        1 for level, _ in report.results if level == "error"
    )
    registers = check_lite_sections(
        document,
        label,
        schemas,
        report,
        schema_label_prefix="schemas/",
        validation_document=substituted,
    )
    section_errors_after = sum(
        1 for level, _ in report.results if level == "error"
    )
    check_semantics(
        registers,
        report,
        ok_label=f"{label} semantic checks",
        profiles=["core"],
        emit_ok=not errors and section_errors_after == section_errors_before,
    )
    # Lite is core-only: the same non-emptiness obligations an adopter faces,
    # so a template that ships an empty `invariants: []`/`residuals: []` is
    # caught here too and cannot drift into a vacuous pass.
    check_register_obligations(["core"], registers, report)


def check_forbidden_string(repo_root: Path, report: Report) -> None:
    """Check that no repository file contains the abolished version string.

    A repository file is one that is tracked or untracked-but-not-ignored
    (per .gitignore), matching ``listed_files``; the scan therefore works
    before files are committed as well as in CI.
    """
    needle = FORBIDDEN_VERSION_STRING.encode("ascii")
    offenders = []
    unreadable: list[tuple[Path, OSError]] = []
    for path in listed_files(repo_root):
        try:
            if path.is_symlink():
                contains = needle in os.fsencode(os.readlink(path))
            else:
                contains = False
                overlap = b""
                with path.open("rb") as handle:
                    while chunk := handle.read(1024 * 1024):
                        surface = overlap + chunk
                        if needle in surface:
                            contains = True
                            break
                        overlap = surface[-(len(needle) - 1) :]
        except OSError as exc:
            unreadable.append((path, exc))
            continue
        if contains:
            offenders.append(path.relative_to(repo_root))
    if offenders:
        for offender in offenders:
            # Git permits newline and non-UTF-8 path bytes. Render them as an
            # escaped JSON string fragment so diagnostics remain valid UTF-8
            # and cannot forge a second log line.
            offender_label = json.dumps(str(offender), ensure_ascii=True)[1:-1]
            report.error(
                f"{offender_label}: contains the abolished version string "
                f"'{FORBIDDEN_VERSION_STRING}'"
            )
    for path, exc in unreadable:
        relative = path.relative_to(repo_root)
        path_label = json.dumps(str(relative), ensure_ascii=True)[1:-1]
        report.error(
            f"{path_label}: cannot be inspected for the abolished version "
            f"string: {exc}"
        )
    if not offenders and not unreadable:
        report.ok(
            f"no repository file contains the abolished version string "
            f"'{FORBIDDEN_VERSION_STRING}'"
        )


def check_agent_instruction_template_sync(repo_root: Path, report: Report) -> None:
    """Keep the standalone AGENTS template equal to its normative §11 copy.

    ``templates/AGENTS.md`` promises that its OpenDevs block is copied
    verbatim from ``templates/AGENTIC_ASSURANCE.md``. Treat that promise as a
    mechanical contract: missing or duplicated extraction markers fail closed,
    and the extracted blocks must match exactly apart from trailing newlines.
    """
    authority_path = repo_root / "templates" / "AGENTIC_ASSURANCE.md"
    standalone_path = repo_root / "templates" / "AGENTS.md"
    try:
        authority_text = read_utf8_text_exact(authority_path).replace("\r\n", "\n")
        standalone_text = read_utf8_text_exact(standalone_path).replace("\r\n", "\n")
    except (OSError, UnicodeDecodeError) as exc:
        report.error(f"agent-instruction template sync: cannot read templates: {exc}")
        return
    if "\r" in authority_text or "\r" in standalone_text:
        report.error(
            "agent-instruction template sync: templates must use physical LF "
            "or CRLF line endings; bare CR is content, not a record separator"
        )
        return

    section_marker = "## 11. Root `AGENTS.md` integration\n"
    fence_open = "```markdown\n"
    fence_close = "\n```"
    block_marker = "## OpenDevs Agentic Assurance\n"
    block_close = "\n---\n"

    if authority_text.count(section_marker) != 1:
        report.error(
            "templates/AGENTIC_ASSURANCE.md: expected exactly one §11 "
            "AGENTS integration section"
        )
        return
    authority_section = authority_text.split(section_marker, 1)[1]
    if authority_section.count(fence_open) != 1:
        report.error(
            "templates/AGENTIC_ASSURANCE.md §11: expected exactly one "
            "```markdown block"
        )
        return
    fenced_tail = authority_section.split(fence_open, 1)[1]
    if fenced_tail.count(fence_close) != 1:
        report.error(
            "templates/AGENTIC_ASSURANCE.md §11: expected exactly one closing "
            "fence for the AGENTS block"
        )
        return
    authoritative_block = fenced_tail.split(fence_close, 1)[0].rstrip("\n")

    if standalone_text.count(block_marker) != 1:
        report.error(
            "templates/AGENTS.md: expected exactly one OpenDevs Agentic "
            "Assurance block"
        )
        return
    standalone_tail = standalone_text.split(block_marker, 1)[1]
    if standalone_tail.count(block_close) != 1:
        report.error(
            "templates/AGENTS.md: expected exactly one separator after the "
            "OpenDevs Agentic Assurance block"
        )
        return
    standalone_block = (
        block_marker + standalone_tail.split(block_close, 1)[0]
    ).rstrip("\n")

    if standalone_block != authoritative_block:
        report.error(
            "templates/AGENTS.md: OpenDevs Agentic Assurance block differs "
            "from the normative verbatim block in "
            "templates/AGENTIC_ASSURANCE.md §11"
        )
    elif not has_required_reading_order(
        authoritative_block, ".agentic-assurance/adoption.yaml"
    ):
        report.error(
            "agent-instruction templates: the synchronized OpenDevs block "
            "does not contain the canonical assurance reading order"
        )
    else:
        report.ok(
            "templates/AGENTS.md OpenDevs block matches the normative "
            "templates/AGENTIC_ASSURANCE.md §11 copy"
        )


def check_archived_system_template_markers(
    repo_root: Path, report: Report
) -> None:
    """Bind the interim archived completion guard to the shipped prompts."""
    label = "templates/SYSTEM.md"
    try:
        text = read_utf8_text_exact(repo_root / label)
    except (OSError, UnicodeDecodeError) as exc:
        report.error(f"{label}: cannot inspect archived markers: {exc}")
        return
    found = re.findall(r"REPLACE_WITH_ARCHIVED_[A-Z0-9_]+", text)
    expected = set(ARCHIVED_SYSTEM_PLACEHOLDERS)
    if set(found) != expected or any(found.count(marker) != 1 for marker in expected):
        report.error(
            f"{label}: archived prompt markers must match the validator's "
            "four exact interim completion guards, once each"
        )
    else:
        report.ok(
            f"{label} archived prompts match the four interim completion guards"
        )


def check_codeowners_template(
    repo_root: Path, adoption_template: object, report: Report
) -> None:
    """Keep shipped default policy locations inside the CODEOWNERS bundle."""
    label = "templates/github/CODEOWNERS"
    path = repo_root / label
    try:
        text = read_utf8_text_exact(path)
    except (OSError, UnicodeDecodeError) as exc:
        report.error(f"{label}: cannot read as UTF-8 text: {exc}")
        return
    patterns = []

    def canonical_coverage_pattern(raw: str) -> str | None:
        """Canonical subset used to prove coverage of shipped exact paths."""
        if raw == "/":
            return raw
        if raw.startswith("//"):
            return None
        value = raw[1:] if raw.startswith("/") else raw
        if not value or "//" in value or "\\" in value:
            return None
        directory = value.endswith("/")
        body = value[:-1] if directory else value
        if not body:
            return None
        if any(component in ("", ".", "..") for component in body.split("/")):
            return None
        return body + ("/" if directory else "")

    for line in physical_text_lines(text):
        # CODEOWNERS records and field separators are physical LF/CRLF plus
        # ASCII spaces/tabs. Unicode separators must not manufacture a rule
        # or stand in for GitHub's owner separator.
        stripped = line.strip(" \t")
        if not stripped or stripped.startswith("#"):
            continue
        fields = re.split(r"[ \t]+", stripped)
        if (
            len(fields) >= 2
            and any(
                owner == "@REPLACE_WITH_OWNER_OR_TEAM"
                for owner in fields[1:]
            )
        ):
            pattern = canonical_coverage_pattern(fields[0])
            if pattern is not None:
                patterns.append(pattern)

    required = {
        "AGENTS.md",
        "AGENTIC_ASSURANCE.md",
        ".agentic-assurance/adoption.yaml",
        ".github/workflows/assurance.yml",
        ".github/CODEOWNERS",
    }
    if isinstance(adoption_template, dict):
        declared_paths = adoption_template.get("paths")
        if isinstance(declared_paths, dict):
            required.update(
                normalized
                for value in declared_paths.values()
                if (
                    normalized := normalized_repository_relative_path(value)
                )
                is not None
            )
        workflow = adoption_template.get("specification_workflow")
        if isinstance(workflow, dict):
            normalized = normalized_repository_relative_path(
                workflow.get("root"), allow_root=True
            )
            if normalized is not None and not is_generic_placeholder(normalized):
                required.add(normalized)
        human_review = adoption_template.get("human_review")
        if isinstance(human_review, dict):
            normalized = normalized_repository_relative_path(
                human_review.get("record")
            )
            if normalized is not None and not is_generic_placeholder(normalized):
                required.add(normalized)
        security = adoption_template.get("security")
        if isinstance(security, dict):
            for key, allow_root in (
                ("policy", False),
                ("public_assurance_root", True),
            ):
                normalized = normalized_repository_relative_path(
                    security.get(key), allow_root=allow_root
                )
                if normalized is not None:
                    required.add(normalized)

    def covered(relative: str) -> bool:
        if relative == ".":
            return any(pattern in ("*", "**", "/") for pattern in patterns)
        for pattern in patterns:
            if pattern.endswith("/"):
                directory = pattern[:-1]
                if relative == directory or relative.startswith(directory + "/"):
                    return True
            elif relative == pattern:
                return True
        return False

    missing = sorted(relative for relative in required if not covered(relative))
    if missing:
        report.error(
            f"{label}: default adopted policy location(s) lack an owner rule: "
            + ", ".join(missing)
        )
    else:
        report.ok(f"{label} covers every default adopted policy location")


def run_self_check(args: argparse.Namespace) -> int:
    report = Report()
    if args.repo_root is not None:
        repo_root = Path(args.repo_root).resolve()
    else:
        repo_root = Path(__file__).resolve().parent.parent

    check_version_file(repo_root, report)
    schemas = check_schemas_parse(repo_root, report)
    adoption_template = check_template(
        repo_root, "adoption.yaml", "adoption.schema.json", schemas, report
    )
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
    check_register_obligations(["core"], registers, report)
    check_lite_template(repo_root, schemas, report)
    check_lite_template(repo_root, schemas, report, LITE_MINIMAL_TEMPLATE)
    check_agent_instruction_template_sync(repo_root, report)
    check_archived_system_template_markers(repo_root, report)
    check_codeowners_template(repo_root, adoption_template, report)
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
        elif document.get("$schema") != JSON_SCHEMA_2020_12:
            report.error(
                f"schema {name}: '$schema' is {document.get('$schema')!r}, "
                f"expected {JSON_SCHEMA_2020_12!r}"
            )
        else:
            try:
                Draft202012Validator.check_schema(document)
            except SchemaError as exc:
                report.error(
                    f"schema {name}: invalid JSON Schema draft 2020-12: "
                    f"{exc.message}"
                )
                continue
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


def check_pinned_checkout_commit(
    adoption: dict, profile_checkout: Path, report: Report
) -> None:
    """Bind a Git-backed profile checkout to ``upstream.commit``.

    Release/source archives have no Git object identity, so they retain an
    explicit warning rather than pretending the VERSION comparison proves a
    commit. The documented clone-and-checkout path, including the reusable
    workflow, has Git metadata and therefore fails closed on a mismatch or an
    unusable repository.
    """
    upstream = adoption.get("upstream")
    pinned = upstream.get("commit") if isinstance(upstream, dict) else None
    if not isinstance(pinned, str):
        report.error(
            "cannot compare pinned commit with profile checkout: "
            "upstream.commit is missing or not a string"
        )
        return

    git_metadata = profile_checkout / ".git"
    if not os.path.lexists(git_metadata):
        report.warn(
            "profile checkout has no Git metadata; upstream.commit cannot be "
            "verified locally (only VERSION is bound). Use a Git clone at the "
            "declared commit for a mechanically verified pin"
        )
        return
    try:
        completed = subprocess.run(
            [
                "git",
                "-C",
                os.fspath(profile_checkout),
                "rev-parse",
                "--verify",
                "HEAD^{commit}",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        report.error(f"profile checkout commit cannot be inspected: {exc}")
        return
    actual = completed.stdout.strip().decode("ascii", errors="replace")
    if completed.returncode != 0 or re.fullmatch(r"[0-9a-f]{40}", actual) is None:
        diagnostic = completed.stderr[:4096].decode("utf-8", errors="backslashreplace")
        report.error(
            "profile checkout Git metadata is unusable; cannot verify "
            f"upstream.commit{': ' + diagnostic.strip() if diagnostic.strip() else ''}"
        )
    elif actual != pinned:
        report.error(
            f"commit/checkout mismatch: upstream.commit is {pinned} but the "
            f"profile checkout HEAD is {actual}"
        )
        return
    else:
        resource_paths = (
            "VERSION",
            "requirements-ci.txt",
            "scripts/validate.py",
            *(f"schemas/{name}" for name in SCHEMA_FILES),
        )
        status_paths = ("VERSION", "requirements-ci.txt", "scripts", "schemas")

        # The Git object identity is meaningful only if every resource this
        # run consumes comes from that object.  Merely checking HEAD lets a
        # dirty VERSION or schema claim one commit while validating with
        # another set of bytes.  Reject symlinked resource roots/files and use
        # Git's own worktree comparison so platform checkout filters remain
        # respected.
        for directory_name in ("scripts", "schemas"):
            directory = profile_checkout / directory_name
            try:
                directory_mode = directory.lstat().st_mode
            except OSError as exc:
                report.error(
                    f"profile checkout trusted resource directory "
                    f"{directory_name!r} cannot be inspected: {exc}"
                )
                return
            if not stat.S_ISDIR(directory_mode):
                report.error(
                    f"profile checkout trusted resource directory "
                    f"{directory_name!r} is not a real directory"
                )
                return
        for relative in resource_paths:
            resource = profile_checkout / relative
            try:
                resource_mode = resource.lstat().st_mode
            except OSError as exc:
                report.error(
                    f"profile checkout trusted resource {relative!r} cannot "
                    f"be inspected: {exc}"
                )
                return
            if not stat.S_ISREG(resource_mode):
                report.error(
                    f"profile checkout trusted resource {relative!r} is not "
                    "a real regular file"
                )
                return

        expected_validator = profile_checkout / "scripts" / "validate.py"
        try:
            executing_pinned_validator = Path(__file__).samefile(expected_validator)
        except (OSError, ValueError) as exc:
            report.error(
                "executing validator cannot be bound to the pinned profile "
                f"checkout: {exc}"
            )
            return
        if not executing_pinned_validator:
            report.error(
                "executing validator is not the pinned profile checkout's "
                "scripts/validate.py; run the validator from --profile-checkout"
            )
            return

        try:
            index_flags = subprocess.run(
                [
                    "git",
                    "-C",
                    os.fspath(profile_checkout),
                    "ls-files",
                    "-v",
                    "-z",
                    "--",
                    *status_paths,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=10,
            )
            status = subprocess.run(
                [
                    "git",
                    "-C",
                    os.fspath(profile_checkout),
                    "status",
                    "--porcelain=v1",
                    "-z",
                    "--untracked-files=all",
                    "--",
                    *status_paths,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            report.error(
                f"profile checkout trusted resources cannot be compared with "
                f"HEAD: {exc}"
            )
            return
        if index_flags.returncode != 0:
            diagnostic = index_flags.stderr[:4096].decode(
                "utf-8", errors="backslashreplace"
            )
            report.error(
                "profile checkout trusted-resource index flags cannot be "
                f"inspected{': ' + diagnostic.strip() if diagnostic.strip() else ''}"
            )
            return
        hidden_index_records = []
        for record in index_flags.stdout.split(b"\0"):
            if len(record) < 3 or record[1:2] != b" ":
                continue
            tag = record[:1]
            if tag == b"S" or tag.islower():
                hidden_index_records.append(record)
        if hidden_index_records:
            rendered = ", ".join(
                record.decode("utf-8", errors="backslashreplace")
                for record in hidden_index_records[:16]
            )
            if len(hidden_index_records) > 16:
                rendered += (
                    f", ... ({len(hidden_index_records)} records total)"
                )
            report.error(
                "profile checkout trusted validation resources use "
                "assume-unchanged or skip-worktree index flags and cannot be "
                f"bound to HEAD {actual}: {rendered}"
            )
            return
        if status.returncode != 0:
            diagnostic = status.stderr[:4096].decode(
                "utf-8", errors="backslashreplace"
            )
            report.error(
                "profile checkout trusted resources cannot be compared with "
                f"HEAD{': ' + diagnostic.strip() if diagnostic.strip() else ''}"
            )
            return
        dirty_records = [record for record in status.stdout.split(b"\0") if record]
        if dirty_records:
            rendered = ", ".join(
                record.decode("utf-8", errors="backslashreplace")
                for record in dirty_records[:16]
            )
            if len(dirty_records) > 16:
                rendered += f", ... ({len(dirty_records)} records total)"
            report.error(
                "profile checkout trusted validation resources differ from "
                f"HEAD {actual}: {rendered}"
            )
            return
        report.ok(
            f"pinned commit and consumed validation resources match the "
            f"profile checkout HEAD ('{actual}')"
        )


def resolve_profile_checkout(
    schemas_dir: Path,
    explicit_checkout: str | None,
    report: Report,
) -> Path | None:
    """Resolve the one trusted profile root paired with ``--schemas``.

    The checkout is a trust boundary, not merely an optional VERSION hint:
    no adopter-owned artifact may be satisfied by a template elsewhere in
    that checkout. When the caller omits ``--profile-checkout``, infer the
    conventional parent of ``.../schemas`` only if it carries VERSION.
    Otherwise fail closed and ask for the root explicitly.
    """
    try:
        schemas_root = schemas_dir.resolve()
    except (OSError, RuntimeError) as exc:
        report.error(f"schemas directory: cannot resolve path: {exc}")
        return None

    if explicit_checkout is None:
        candidate = schemas_root.parent
        if schemas_root.name != "schemas" or not (candidate / "VERSION").is_file():
            report.error(
                "cannot infer the pinned profile checkout from --schemas; "
                "pass --profile-checkout explicitly (the checkout is required "
                "to enforce the adopter/profile trust boundary)"
            )
            return None
        checkout = candidate
    else:
        try:
            checkout = Path(explicit_checkout).resolve()
        except (OSError, RuntimeError) as exc:
            report.error(f"profile checkout: cannot resolve path: {exc}")
            return None

    expected_schemas = checkout / "schemas"
    try:
        expected_schemas = expected_schemas.resolve()
    except (OSError, RuntimeError) as exc:
        report.error(f"profile checkout schemas directory: cannot resolve path: {exc}")
        return None
    if schemas_root != expected_schemas:
        report.error(
            f"--schemas resolves to {schemas_root}, but the pinned profile "
            f"checkout expects {expected_schemas}; use one checkout for both "
            "schema validation and the trust boundary"
        )
        return None
    return checkout


def check_artifacts(
    project_root: Path,
    paths: dict[str, str],
    schemas: dict[str, dict],
    report: Report,
) -> dict[str, list | None]:
    """Schema-validate present registers; return them for the semantic checks.

    The returned mapping holds an entry per register whose file exists: the
    raw entry list when the document is usable, else None. A substituted copy
    is used only for schema validation; semantic checks must see placeholders
    as uncommitted values. Registers whose file is absent are omitted entirely,
    so the semantic checks can distinguish a dangling reference from a
    reference into a register the adopter legitimately does not keep.
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
        substituted = substitute_register_placeholders(document)
        registers[kind] = register_entries(document, kind)
        schema = schemas.get(schema_name)
        if schema is None:
            report.error(f"{relative}: cannot validate, {schema_name} unusable")
            registers[kind] = None
            continue
        errors = schema_errors(substituted, schema, relative)
        if errors:
            for message in errors:
                report.error(message)
            registers[kind] = None
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
    project_root: Path,
    adoption_reference: str,
    paths: dict[str, str],
    profiles: list[str],
    report: Report,
    excluded_roots: tuple[Path, ...] = (),
) -> None:
    check_root_reading_order(
        project_root, adoption_reference, report, excluded_roots
    )

    def require(key: str, reason: str, *, nonempty_text: bool = False) -> None:
        relative = paths.get(key)
        if relative is None:
            return  # rejected by check_declared_paths; error already reported
        path = project_root / relative
        if nonempty_text:
            text = read_project_text_file(
                path,
                project_root,
                report,
                relative,
                excluded_roots,
                missing_message=f"{relative} missing (paths.{key}, required for {reason})",
            )
            if text is not None:
                report.ok(f"{relative} present (paths.{key}, required for {reason})")
        elif path.is_file():
            report.ok(f"{relative} present (paths.{key}, required for {reason})")
        else:
            report.error(f"{relative} missing (paths.{key}, required for {reason})")

    # Every adopter needs the mapped system artifact. For an active repository
    # it is the system description; for `archived`, it carries all four
    # PROFILE.md section 6.6 historical facts.
    require("system", "all adopters", nonempty_text=True)
    if any(profile != "archived" for profile in profiles):
        require("residuals", "non-archived profiles")
        require("invariants", "non-archived profiles")
    if "service" in profiles:
        require("threat_model", "profile 'service'", nonempty_text=True)
    if "trust-critical" in profiles:
        require("claims", "profile 'trust-critical'")
        defeaters = paths.get("defeaters")
        if defeaters is not None and not (project_root / defeaters).is_file():
            report.warn(
                f"profile 'trust-critical' selected but no defeaters file at "
                f"{defeaters}"
            )


def check_register_obligations(
    profiles: list[str],
    registers: dict[str, list | None],
    report: Report,
) -> None:
    """Registers a profile mandates must carry at least one entry.

    File presence alone allows a vacuous pass: a ``version: 1`` file with an
    empty array satisfies the schema and every per-entry check trivially.
    PROFILE.md requires at least one project invariant and an active residual
    register for every non-archived profile, plus public claims for
    'trust-critical' — "active" is not an empty list (a project that believes
    it has zero residual risk should record that belief as its first residual;
    a project with nothing that must stay true has not found its invariants
    yet). A register that is absent or unusable is skipped here: presence and
    load errors are reported by their own checks.
    """
    obligations = []
    if any(profile != "archived" for profile in profiles):
        obligations.append(("residuals", "non-archived profiles"))
        obligations.append(("invariants", "non-archived profiles"))
    if "trust-critical" in profiles:
        obligations.append(("claims", "profile 'trust-critical'"))
    for kind, reason in obligations:
        entries = registers.get(kind)
        if entries is None:
            continue  # absent or unusable; reported elsewhere
        if not [entry for entry in entries if isinstance(entry, dict)]:
            report.error(
                f"{kind} register is empty, but {reason} require at least "
                "one entry — an empty register passes no obligation "
                "(PROFILE.md; record the honest current state instead)"
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
                f"profile '{profile}' is provisional — before v1.0.0 its "
                "obligations may change in a minor release; at or after "
                "v1.0.0 the stable-version rules apply"
            )
    if "archived" in profiles:
        report.warn(
            "profile 'archived': PROFILE.md section 6.6's four statements "
            "(historical-reference-only status with no active operation, "
            "functional maintenance, or feature development; "
            "historical purpose; known limitations; last supported revision "
            "or release, or explicit none) "
            "receive only an interim nonempty/exact-placeholder guard — "
            "their structure and truth are not mechanically verified, so human "
            "review must confirm them in the mapped system artifact "
            "(tracked: MosslandOpenDevs/agentic-assurance-profile#40)"
        )


def validated_profile_declaration(declared_profiles: object) -> list[str] | None:
    """Return a profile list only when its complete declaration is valid.

    The adoption schema owns malformed, empty, unknown, and duplicate profile
    diagnostics. Profile-dependent checks must stay silent for those inputs so
    they never emit a success verdict (or a contradictory derived error) from
    a filtered subset of an invalid declaration.
    """
    if (
        not isinstance(declared_profiles, list)
        or not declared_profiles
        or any(not isinstance(profile, str) for profile in declared_profiles)
        or len(set(declared_profiles)) != len(declared_profiles)
        or any(profile not in KNOWN_PROFILES for profile in declared_profiles)
    ):
        return None
    return declared_profiles


def consistent_profile_declaration(declared_profiles: object) -> list[str] | None:
    """A valid profile declaration that also respects archived exclusivity."""
    profiles = validated_profile_declaration(declared_profiles)
    if profiles is None or ("archived" in profiles and len(profiles) != 1):
        return None
    return profiles


def effective_profile_set(
    declared_profiles: object, *, allow_mixed_archived: bool = False
) -> set[str]:
    """Profile obligations after implicit core inheritance is normalized.

    Pre-v0.4 schemas allowed the contradictory ``archived`` marker alongside
    active profiles. During a direct upgrade, compare the active obligations
    from that legacy list instead of making cleanup impossible. Head/current
    declarations still require archived exclusivity.
    """
    profiles = (
        validated_profile_declaration(declared_profiles)
        if allow_mixed_archived
        else consistent_profile_declaration(declared_profiles)
    )
    if profiles is None:
        return set()
    effective = set(profiles)
    if allow_mixed_archived and "archived" in effective and len(effective) > 1:
        effective.remove("archived")
    if effective != {"archived"} and effective.intersection(SPLIT_ONLY_PROFILES):
        effective.add("core")
    return effective


def declared_stage(document: dict) -> str | None:
    """Return the explicit/default stage, or None for a malformed declaration."""
    value = document.get("adoption_stage", "DRAFT")
    return value if isinstance(value, str) and value in ADOPTION_STAGES else None


def check_profile_exclusivity(declared_profiles: object, report: Report) -> None:
    """`archived` is exclusive and cannot coexist with an active profile.

    PROFILE.md sections 5 and 6.6 reserve it for a repository retained solely
    for historical reference, with no active operation, functional
    maintenance, or feature development; it replaces the others.
    """
    profiles = validated_profile_declaration(declared_profiles)
    if profiles is None:
        return
    if "archived" not in profiles:
        return
    if len(profiles) > 1:
        others = ", ".join(f"'{p}'" for p in profiles if p != "archived")
        report.error(
            f"profile 'archived' cannot be combined with an active profile "
            f"({others}) — archived means historical-reference-only, with no "
            "active operation, functional maintenance, or feature development, "
            "which contradicts any active "
            "obligation; declare 'archived' alone "
            "or drop it"
        )
    else:
        report.ok("profile 'archived' is declared exclusively")


def check_lite_profiles(declared_profiles: object, report: Report) -> None:
    """Layout 'lite' is core-only; richer profiles need the split layout."""
    # The adoption schema reports malformed/unknown/duplicate declarations.
    # Do not layer a contradictory layout verdict on top of that error: only
    # classify a declaration whose shape and values are independently valid.
    profiles = validated_profile_declaration(declared_profiles)
    if profiles is None:
        return
    beyond_core = [profile for profile in profiles if profile in SPLIT_ONLY_PROFILES]
    if beyond_core:
        listed = ", ".join(f"'{profile}'" for profile in beyond_core)
        if "archived" in beyond_core:
            guidance = (
                "reclassify in the split layout by writing the four PROFILE.md "
                "section 6.6 facts in the mapped system artifact with owner "
                "confirmation; prior active registers may remain only as "
                "optional history and do not substitute for those facts"
            )
        else:
            guidance = (
                "graduate to the split layout by preserving IDs and moving "
                "each register array, moving inline system into paths.system, "
                "preserving purpose/non_goals there or in another "
                "owner-approved local intent artifact, and preserving or "
                "relocating extensions before dropping layout: lite"
            )
        report.error(
            f"layout 'lite' supports only the core profile, but profiles "
            f"include {listed} — {guidance} (see docs/ADOPTION.md section 3.0)"
        )
    else:
        report.ok("layout 'lite' is declared with core-only profiles")


def check_lite_file(
    project_root: Path,
    schemas: dict[str, dict],
    report: Report,
    excluded_roots: tuple[Path, ...] = (),
) -> tuple[dict | None, dict[str, list | None]]:
    """Load and validate the single lite assurance file.

    The path is fixed at ``.agentic-assurance/assurance.yaml`` — the lite
    layout has exactly one assurance file, independent of any configured
    adoption-declaration path.
    Returns ``(document, registers)``: the safely loaded raw envelope (None
    when missing or unusable) and the same kind -> raw entries mapping the
    split layout's ``check_artifacts`` returns for ``check_semantics``.  The
    raw envelope is reused by later stage checks so an unsafe/rejected path is
    never reopened merely to scan it for placeholders.
    """
    relative = LITE_ASSURANCE_PATH
    path = project_root / relative
    if (
        checked_project_path(
            path, project_root, report, relative, excluded_roots
        )
        is None
    ):
        return None, {}
    if not path.is_file():
        if path.is_symlink() or path.exists():
            report.error(f"{relative}: exists but is not a readable regular file")
        else:
            report.error(f"{relative} missing (required by layout 'lite')")
        return None, {}
    document, error = load_yaml(path)
    if error is not None:
        report.error(f"{relative}: {error}")
        return None, {}
    # Template placeholder values are tolerated, as in the split-layout
    # registers, so a freshly copied template validates; the adoption
    # declaration itself remains strict.
    substituted = substitute_register_placeholders(document)
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
    registers = check_lite_sections(
        document,
        relative,
        schemas,
        report,
        validation_document=substituted,
    )
    for entry_id, disclosure in entries_with_restricted_disclosure(document):
        report.warn(
            f"{relative}: entry {entry_id} has disclosure {disclosure} — "
            "public repositories must not contain restricted material — "
            "verify this file is not public"
        )
    if not isinstance(document, dict):
        return None, registers
    return document, registers


def check_lite_required_files(
    project_root: Path,
    adoption_reference: str,
    paths: dict[str, str],
    lite_document: dict | None,
    report: Report,
    excluded_roots: tuple[Path, ...] = (),
) -> None:
    """Presence checks for layout 'lite'.

    AGENTIC_ASSURANCE.md and AGENTS.md stay required at the project root.
    The residuals obligation is carried by the assurance file itself (its
    schema requires the section). The system description must come from
    either the file's `system` section or an existing paths.system file.
    The split layout's per-profile file checks do not apply.
    """
    check_root_reading_order(
        project_root, adoption_reference, report, excluded_roots
    )

    has_system_section = isinstance(lite_document, dict) and nonempty_string(
        lite_document.get("system")
    )
    system_relative = paths.get("system")
    system_text: str | None = None
    if system_relative is not None and (project_root / system_relative).exists():
        system_text = read_project_text_file(
            project_root / system_relative,
            project_root,
            report,
            system_relative,
            excluded_roots,
        )
    has_system_file = system_text is not None
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
    complete = not register_unusable
    for name, component in components.items():
        if not isinstance(component, dict):
            complete = False
            continue  # rejected by the adoption schema; error already reported
        references = component.get("invariants")
        if not isinstance(references, list):
            complete = False
            continue  # rejected by the adoption schema; error already reported
        if not references:
            complete = False
            continue  # minItems is enforced by the adoption schema
        for reference in references:
            if not isinstance(reference, str):
                complete = False
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
    if errors_after == errors_before and complete:
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
    repo_visibility: str | None = None,
    profiles: list[str] | None = None,
    excluded_roots: tuple[Path, ...] = (),
    lite_document: dict | None = None,
    checked_review_record: Path | None = None,
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
    the adoption file or any loaded register, and no path-scoped v0.3.x
    compatibility placeholder in a loaded register: the legacy ``YYYY-MM-DD``
    ``review_after`` sentinel or any of the seven exact bare prose starter
    prompts at their original direct fields. The raw, unsubstituted documents
    are re-scanned — the split registers that exist, or the lite assurance
    file. The exclusive archived profile scans the adoption and mapped SYSTEM
    artifact instead of retained historical active registers. A
    ``human_review`` block with non-empty ``date``, ``reviewer``, and ``record``
    (pointing at a nonempty adopter-owned file) is also required.

    CONFORMANT: additionally, every severity-critical invariant has an
    eligible intent (neither UNKNOWN nor ACCIDENTAL), and
    ``human_review.approvals`` carries at least one attributable entry —
    ``approver`` non-empty, ``review_url`` an absolute HTTP(S) URL, and ``at``
    an ISO 8601 date or timestamp. Passed
    ``review_after`` dates are also errors at this stage; that requirement
    is enforced inside ``check_semantics`` (as if ``--strict-review-dates``
    had been passed), so those lines carry no stage prefix — here they only
    count against the success verdict. Whether
    ``review_url`` really is an approved review by a non-author is not
    verified here — that remains a manual step (future tooling may verify
    it against the forge API).

    CONFORMANT also enforces the mechanically checkable subset of
    PROFILE.md section 17: no critical residual left OPEN (accept it with
    rationale or resolve it), no CONTRADICTED claim, no CONTRADICTED
    critical invariant (non-critical CONTRADICTED invariants remain an
    explicit warning but do not defeat conformance), and every VERIFIED critical invariant
    carries non-empty ``evidence``. These active-register conditions do not
    apply to retained historical registers under the exclusive archived
    profile.

    RESTRICTED/EMBARGOED entries are visibility-aware at CONFORMANT:
    section 17 excludes restricted material from *public* artifacts, and
    ADOPTION.md permits RESTRICTED entries in a private repository (they
    bind its visibility). With ``repo_visibility`` "private" or "internal"
    they stay the standing warning; "public" makes them errors; ``None``
    (visibility unknown — standalone run without --repo-visibility) also
    errors, conservatively, with a message saying how to declare the
    visibility. The structural checks warn at every stage regardless.

    Conditions section 17 states but strings cannot capture (evidence bound
    to a revision, claim wording not exceeding evidence strength) remain
    the human review's responsibility.

    On HUMAN_REVIEWED or CONFORMANT success (no stage requirement violated),
    an OK line is emitted: ``stage <declared>: requirements satisfied``.
    DRAFT adds no stage-specific line; ordinary validation results still run.
    """
    stage = adoption.get("adoption_stage", "DRAFT")
    if stage == "DRAFT":
        return  # no stage-specific requirements or summary line
    if stage not in ADOPTION_STAGES:
        # The adoption schema already rejects unknown values; this guard
        # keeps stage enforcement honest when the schema itself is unusable.
        listed = ", ".join(ADOPTION_STAGES)
        report.error(
            f"adoption_stage {stage!r} is not one of {listed} — "
            "stage requirements cannot be enforced"
        )
        return
    active = profiles is not None and profiles != ["archived"]
    def entry_label(entry: dict) -> str:
        return entry["id"] if nonempty_string(entry.get("id")) else "<no id>"

    # HUMAN_REVIEWED (also CONFORMANT): no unfilled placeholders anywhere in
    # the adoption file or any loaded register. The raw documents are
    # re-loaded so that the substitution tolerated by the structural checks
    # cannot mask a leftover token.
    for json_path, value in find_placeholder_strings(adoption):
        report.error(
            f"stage HUMAN_REVIEWED: unfilled placeholder {value!r} "
            f"in {adoption_path} at {json_path}"
        )

    scan_targets: list[tuple[str, Path, bool]] = []
    if active and adoption.get("layout") == "lite":
        if isinstance(lite_document, dict):
            # `system`, `purpose`, and `non_goals` are prose carrying the same
            # obligation as split-layout SYSTEM.md, so they follow the prose
            # rule — a named REPLACE_WITH_ marker — rather than the structured
            # substring rule that is correct for IDs, owners, and scopes.
            # Without the split, identical prose passes in the split layout and
            # fails in lite, and the error quotes the adopter's whole paragraph
            # instead of the token that needs replacing.
            structured = {
                key: value
                for key, value in lite_document.items()
                if key not in LITE_PROSE_KEYS
            }
            for json_path, value in find_register_placeholder_strings(structured):
                report.error(
                    f"stage HUMAN_REVIEWED: unfilled placeholder {value!r} "
                    f"in {LITE_ASSURANCE_PATH} at {json_path}"
                )
            for key in LITE_PROSE_KEYS:
                value = lite_document.get(key)
                entries = value if isinstance(value, list) else [value]
                for index, item in enumerate(entries):
                    if not isinstance(item, str):
                        continue
                    found = PROSE_PLACEHOLDER_RE.search(item)
                    if found is None:
                        continue
                    location = (
                        f"$.{key}[{index}]"
                        if isinstance(value, list)
                        else f"$.{key}"
                    )
                    report.error(
                        "stage HUMAN_REVIEWED: unfilled placeholder "
                        f"{found.group(0)!r} in {LITE_ASSURANCE_PATH} "
                        f"at {location}"
                    )
    elif active:
        for kind in REGISTER_KINDS:
            relative = paths.get(kind)
            if relative is None:
                continue  # rejected by check_declared_paths; already reported
            path = project_root / relative
            if path.is_file():
                scan_targets.append((relative, path, True))
    for label, path, register_shaped in scan_targets:
        document, error = load_yaml(path)
        if error is not None:
            # The structural checks already reported the load failure; this
            # line keeps the stage verdict honest instead of claiming OK.
            report.error(
                f"stage HUMAN_REVIEWED: cannot scan {label} for placeholders — {error}"
            )
            continue
        find_placeholders = (
            find_register_placeholder_strings
            if register_shaped
            else find_placeholder_strings
        )
        for json_path, value in find_placeholders(document):
            report.error(
                f"stage HUMAN_REVIEWED: unfilled placeholder {value!r} "
                f"in {label} at {json_path}"
            )

    # The mapped system prose is policy-bearing too. At reviewed stages, an
    # active adopter cannot retain a generic template marker. For archived,
    # the deliberately narrower interim guard rejects only the exact four
    # shipped §6.6 markers; semantic parsing and truth verification remain #40.
    system_text: str | None = None
    system_scanned_with_lite = False
    if profiles is not None and adoption.get("layout") == "lite":
        if isinstance(lite_document, dict) and nonempty_string(
            lite_document.get("system")
        ):
            system_text = lite_document["system"]
            system_scanned_with_lite = active
    if profiles is not None and system_text is None:
        system_relative = paths.get("system")
        if system_relative is not None:
            candidate = project_root / system_relative
            if candidate.is_file():
                system_text = read_project_text_file(
                    candidate,
                    project_root,
                    report,
                    f"stage HUMAN_REVIEWED: system artifact {system_relative}",
                    excluded_roots,
                )
    if system_text is not None and not system_scanned_with_lite:
        if profiles == ["archived"]:
            for marker in ARCHIVED_SYSTEM_PLACEHOLDERS:
                if marker in system_text:
                    report.error(
                        f"stage HUMAN_REVIEWED: unfilled placeholder {marker!r} "
                        "in the mapped system artifact"
                    )
        else:
            found = PROSE_PLACEHOLDER_RE.search(system_text)
            if found is not None:
                report.error(
                    "stage HUMAN_REVIEWED: unfilled placeholder "
                    f"{found.group(0)!r} in the mapped system artifact"
                )

    # Other required active prose must also be more than an untouched
    # upstream template at reviewed stages. At present this is the service
    # threat model; keep the loop explicit so future prose obligations can be
    # added without creating another stage-specific blind spot.
    reviewed_prose: list[tuple[str, str]] = []
    if active and profiles is not None and "service" in profiles:
        threat_relative = paths.get("threat_model")
        if threat_relative is not None:
            reviewed_prose.append(("threat model", threat_relative))
    for prose_name, relative in reviewed_prose:
        candidate = project_root / relative
        if not candidate.is_file():
            continue  # required-file check reports absence/non-file shape
        text = read_project_text_file(
            candidate,
            project_root,
            report,
            f"stage HUMAN_REVIEWED: {prose_name} {relative}",
            excluded_roots,
        )
        if text is None:
            continue
        found = PROSE_PLACEHOLDER_RE.search(text)
        if found is not None:
            report.error(
                "stage HUMAN_REVIEWED: unfilled placeholder "
                f"{found.group(0)!r} in the mapped {prose_name} artifact"
            )

    # The two root guides are required of every adoption, archived included
    # (check_root_reading_order), so they carry the same obligation: an
    # untouched upstream template is not a completed adoption. Scan the raw
    # text rather than visible prose only — the declaration sample fenced in
    # `AGENTIC_ASSURANCE.md` is part of what an adopter fills in, and both
    # pilot adoptions do fill it.
    for name in ROOT_GUIDE_FILES:
        candidate = project_root / name
        if not candidate.is_file():
            continue  # check_root_reading_order reports absence/non-file shape
        text = read_project_text_file(
            candidate,
            project_root,
            report,
            f"stage HUMAN_REVIEWED: root {name}",
            excluded_roots,
        )
        if text is None:
            continue
        found = PROSE_PLACEHOLDER_RE.search(text)
        if found is not None:
            report.error(
                "stage HUMAN_REVIEWED: unfilled placeholder "
                f"{found.group(0)!r} in root {name}"
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
        review_date = human_review.get("date")
        if nonempty_string(review_date) and coerce_date(review_date) is None:
            report.error(
                "stage HUMAN_REVIEWED: human_review.date is not an ISO 8601 date"
            )
        record = human_review.get("record")
        if nonempty_string(record):
            if checked_review_record is not None:
                read_project_text_file(
                    project_root / record,
                    project_root,
                    report,
                    f"stage HUMAN_REVIEWED: human_review.record {record!r}",
                    excluded_roots,
                    missing_message=(
                        f"stage HUMAN_REVIEWED: human_review.record {record!r} "
                        "does not exist"
                    ),
                    prechecked_resolved=checked_review_record,
                )

    # A completed active review must at least record the owner's disposition
    # of every critical invariant. UNKNOWN is an honest HUMAN_REVIEWED result;
    # omission is not. CONFORMANT applies the stricter eligible-value rule.
    if active:
        for entry in registers.get("invariants") or []:
            if not isinstance(entry, dict) or entry.get("severity") != "critical":
                continue
            intent = entry.get("intent")
            classification = (
                intent.get("classification") if isinstance(intent, dict) else None
            )
            if classification not in (
                "INTENDED",
                "ACCIDENTAL",
                "COMPATIBILITY",
                "UNKNOWN",
                "DEPRECATED",
            ):
                report.error(
                    f"stage HUMAN_REVIEWED: critical invariant "
                    f"{entry_label(entry)} has no recorded intent.classification — "
                    "record UNKNOWN when the review cannot decide it"
                )

    if stage == "CONFORMANT":
        # Active conformance cannot call a behavior that is accidental an
        # invariant: route that behavior to a gap/residual instead.
        if active:
            for entry in registers.get("invariants") or []:
                if not isinstance(entry, dict) or entry.get("severity") != "critical":
                    continue
                label = entry["id"] if nonempty_string(entry.get("id")) else "<no id>"
                intent = entry.get("intent")
                classification = (
                    intent.get("classification") if isinstance(intent, dict) else None
                )
                if classification in ("UNKNOWN", "ACCIDENTAL"):
                    report.error(
                        f"stage CONFORMANT: critical invariant {label} intent is "
                        f"{classification} — classify an invariant as intended, "
                        "compatibility, or deprecated; route accidental behavior "
                        "to a gap or residual"
                    )
                elif not nonempty_string(classification):
                    report.error(
                        f"stage CONFORMANT: critical invariant {label} "
                        "intent.classification is missing — decide it before "
                        "declaring conformance"
                    )

        # Mechanically checkable subset of PROFILE.md section 17 (see the
        # docstring): un-accepted critical exposure, contradicted trust
        # statements, evidence-free verified-critical verdicts, and
        # restricted material in the public assurance view.
        if active:
            for entry in registers.get("residuals") or []:
                if not isinstance(entry, dict):
                    continue
                if entry.get("impact") == "critical" and entry.get("status") == "OPEN":
                    report.error(
                        f"stage CONFORMANT: residual {entry_label(entry)} is OPEN "
                        "with impact critical — accept it explicitly (with "
                        "rationale) or resolve it before declaring conformance "
                        "(PROFILE.md section 17)"
                    )
            for entry in registers.get("claims") or []:
                if isinstance(entry, dict) and entry.get("status") == "CONTRADICTED":
                    report.error(
                        f"stage CONFORMANT: claim {entry_label(entry)} is "
                        "CONTRADICTED — withdraw or remediate the claim before "
                        "declaring conformance (PROFILE.md section 17)"
                    )
            for entry in registers.get("invariants") or []:
                if not isinstance(entry, dict):
                    continue
                if entry.get("status") == "CONTRADICTED":
                    if entry.get("severity") == "critical":
                        report.error(
                            f"stage CONFORMANT: critical invariant "
                            f"{entry_label(entry)} is CONTRADICTED — remediate "
                            "the known violation before declaring "
                            "conformance (PROFILE.md section 17)"
                        )
                    else:
                        report.warn(
                            f"stage CONFORMANT: invariant {entry_label(entry)} is "
                            "CONTRADICTED — resolve it or route the exposure to a "
                            "residual"
                        )
                if (
                    entry.get("status") == "VERIFIED"
                    and entry.get("severity") == "critical"
                ):
                    evidence = entry.get("evidence")
                    if not (isinstance(evidence, list) and evidence):
                        report.error(
                            f"stage CONFORMANT: critical invariant "
                            f"{entry_label(entry)} is VERIFIED but its evidence "
                            "list is empty — record the evidence behind the "
                            "verdict (PROFILE.md section 17)"
                        )
        if repo_visibility not in ("private", "internal"):
            hint = (
                ""
                if repo_visibility == "public"
                else " (if this repository is private, declare it with "
                "--repo-visibility private)"
            )
            for kind in REGISTER_KINDS:
                for entry in registers.get(kind) or []:
                    if not isinstance(entry, dict):
                        continue
                    disclosure = entry.get("disclosure")
                    if disclosure in ("RESTRICTED", "EMBARGOED"):
                        report.error(
                            f"stage CONFORMANT: {kind} entry {entry_label(entry)} "
                            f"has disclosure {disclosure} — public artifacts "
                            "must not carry restricted material; keep it in "
                            "the restricted record (PROFILE.md sections 12 "
                            f"and 17){hint}"
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
            and nonempty_string(entry.get("approver"))
            and is_http_url(entry.get("review_url"))
            and is_iso_date_or_datetime(entry.get("at"))
            and not is_future_iso_date_or_datetime(entry.get("at"))
            and (
                not isinstance(human_review, dict)
                or coerce_date(human_review.get("date")) is None
                or iso_date_component(entry.get("at"))
                >= coerce_date(human_review.get("date"))
            )
            and (
                "covers" not in entry
                or (
                    isinstance(entry.get("covers"), list)
                    and "CONFORMANCE" in entry["covers"]
                )
            )
        ]
        if not attributable:
            fields = ", ".join(ATTRIBUTABLE_APPROVAL_FIELDS)
            report.error(
                f"stage CONFORMANT: human_review.approvals needs at least "
                f"one attributable entry ({fields}); review_url must be an "
                "absolute HTTP(S) URL, at must be a non-future ISO 8601 date "
                "or timestamp, and its civil date must be on or after "
                "human_review.date; omit covers for a full-conformance "
                "approval or include the CONFORMANCE coverage token"
            )

    if not report.has_errors:
        report.ok(f"stage {stage}: requirements satisfied")


def run_adopter(args: argparse.Namespace) -> int:
    report = Report()
    adoption_path = Path(args.adoption)
    project_root = Path(args.project_root)
    schemas_dir = Path(args.schemas)
    profile_checkout = resolve_profile_checkout(
        schemas_dir, args.profile_checkout, report
    )
    if profile_checkout is None:
        return report.emit("adopter", args.json)
    excluded_inputs = [profile_checkout, project_root / ".git"]
    excluded_roots = normalized_excluded_roots(excluded_inputs)

    resolved_adoption = checked_project_path(
        adoption_path,
        project_root,
        report,
        f"adoption file {adoption_path}",
        excluded_roots,
    )
    if resolved_adoption is None:
        return report.emit("adopter", args.json)
    # Root guides should name the path agents actually open, not a symlink's
    # resolved target. Containment is already enforced above on the target;
    # preserve the normalized lexical CLI path for the reading-order contract.
    try:
        adoption_reference = adoption_path.absolute().relative_to(
            project_root.absolute()
        ).as_posix()
    except ValueError:
        # Defensive fallback for unusual relative-CWD invocations; the
        # resolved path is known to be inside the project at this point.
        adoption_reference = resolved_adoption.relative_to(
            project_root.resolve()
        ).as_posix()

    schemas = load_adopter_schemas(schemas_dir, report)
    adoption = check_adoption_document(adoption_path, schemas, report)
    if adoption is None:
        return report.emit("adopter", args.json)

    check_pinned_version(adoption, profile_checkout, report)
    check_pinned_checkout_commit(adoption, profile_checkout, report)
    check_human_review_temporal_semantics(adoption, report)
    check_issue_integration_semantics(adoption, report)

    declared_profiles = adoption.get("profiles")
    profiles = consistent_profile_declaration(declared_profiles)
    check_profile_exclusivity(declared_profiles, report)
    active = profiles is not None and profiles != ["archived"]

    # Stage enforcement (unless --ignore-stage). Stage CONFORMANT turns
    # passed review_after dates into errors, as if --strict-review-dates had
    # been passed; the remaining stage requirements run as a dedicated block
    # after the structural checks.
    enforce_stage = not args.ignore_stage
    strict_review_dates = args.strict_review_dates or (
        enforce_stage
        and active
        and adoption.get("adoption_stage") == "CONFORMANT"
    )

    check_declared_security_paths(adoption, project_root, report, excluded_roots)
    checked_review_record = check_declared_review_record(
        adoption, project_root, report, excluded_roots
    )
    lite_document: dict | None = None
    if adoption.get("layout") == "lite":
        # Lite layout: one consolidated assurance file replaces the split
        # registers. Sections face the same register schemas and the same
        # semantic checks; only the file layout differs.
        check_lite_profiles(declared_profiles, report)
        # The default public_assurance_root ('assurance') points at the split
        # layout's directory; the lite assurance file lives elsewhere.
        security = adoption.get("security")
        if (
            isinstance(security, dict)
            and security.get("public_assurance_root") == "assurance"
        ):
            report.warn(
                "layout 'lite': security.public_assurance_root is 'assurance' "
                f"but the lite assurance file lives at {LITE_ASSURANCE_PATH} — "
                "point public_assurance_root at .agentic-assurance"
            )
        lite_document, registers = check_lite_file(
            project_root, schemas, report, excluded_roots
        )
        # Every explicitly carried path is subject to the repository/trust
        # boundary even when lite does not use it as an artifact location.
        # Implicit split defaults, by contrast, are not active lite paths and
        # must not make an unrelated filesystem entry fail validation.
        declared_paths = adoption.get("paths")
        declared_paths = declared_paths if isinstance(declared_paths, dict) else {}
        checked_explicit_paths = check_declared_paths(
            project_root, declared_paths, report, excluded_roots
        )
        # Split-register defaults are not active policy under the lite
        # envelope. Only the fallback system artifact is used, and even that
        # is irrelevant when the lite document supplies its inline system.
        inline_system = isinstance(lite_document, dict) and nonempty_string(
            lite_document.get("system")
        )
        if inline_system:
            paths = {}
        elif "system" in declared_paths:
            paths = (
                {"system": checked_explicit_paths["system"]}
                if "system" in checked_explicit_paths
                else {}
            )
        else:
            paths = check_declared_paths(
                project_root,
                {"system": DEFAULT_PATHS["system"]},
                report,
                excluded_roots,
            )
        if active:
            check_semantics(
                registers,
                report,
                strict_review_dates=strict_review_dates,
                profiles=profiles,
            )
        else:
            check_register_disposition_grounds(registers, report)
        if profiles is not None:
            check_lite_required_files(
                project_root,
                adoption_reference,
                paths,
                lite_document,
                report,
                excluded_roots,
            )
            check_register_obligations(profiles, registers, report)
    else:
        paths = check_declared_paths(
            project_root, resolve_paths(adoption), report, excluded_roots
        )
        registers = check_artifacts(project_root, paths, schemas, report)
        if active:
            check_semantics(
                registers,
                report,
                strict_review_dates=strict_review_dates,
                profiles=profiles,
            )
        else:
            check_register_disposition_grounds(registers, report)
        if profiles is not None:
            check_required_files(
                project_root,
                adoption_reference,
                paths,
                profiles,
                report,
                excluded_roots,
            )
            check_register_obligations(profiles, registers, report)
    if active or "specification_workflow" in adoption:
        check_active_specification_workflow(
            adoption,
            project_root,
            report,
            excluded_roots,
            required=active,
        )
    if active:
        check_component_map(adoption, registers, report)
    if profiles is not None:
        check_adopter_warnings(project_root, profiles, report)
    if enforce_stage:
        check_adoption_stage(
            adoption,
            adoption_path,
            project_root,
            paths,
            registers,
            report,
            repo_visibility=args.repo_visibility,
            profiles=profiles,
            excluded_roots=excluded_roots,
            lite_document=lite_document,
            checked_review_record=checked_review_record,
        )

    return report.emit("adopter", args.json)


# ---------------------------------------------------------------------------
# drift subcommand (impact routing on pull requests)
# ---------------------------------------------------------------------------


def read_changed_files(path: Path) -> tuple[list[str] | None, str | None]:
    """Read canonical repo-relative Git paths, preserving names verbatim.

    A NUL byte selects the unambiguous NUL-separated format used by the
    reusable workflow. The legacy newline-separated standalone format remains
    accepted, but cannot represent a filename containing a newline. Invalid
    UTF-8 fails closed because YAML component globs are Unicode strings and
    therefore cannot soundly match an undecodable Git path. One legacy ``./``
    prefix is normalized away; absolute paths, escapes, repeated prefixes, and
    non-canonical ``.``/``..`` or empty components are rejected rather than
    being allowed to evade a repository-relative component glob.
    """
    try:
        size = path.stat().st_size
        if size > MAX_CHANGED_FILE_LIST_BYTES:
            return None, (
                f"file is {size:,} bytes; changed-files input is limited to "
                f"{MAX_CHANGED_FILE_LIST_BYTES:,} bytes"
            )
        raw = path.read_bytes()
    except OSError as exc:
        return None, f"cannot read {path}: {exc}"
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        return None, f"cannot read {path} as UTF-8: {exc}"

    nul_separated = b"\0" in raw
    # Git's NUL mode is authoritative. The legacy text contract is framed by
    # physical LF/CRLF records only; Python str.splitlines() would treat NEL,
    # U+2028, and U+2029 inside a valid Git filename as forged separators.
    records = (
        text.split("\0")
        if nul_separated
        else text.replace("\r\n", "\n").split("\n")
    )
    changed = []
    for index, record in enumerate(records, start=1):
        # The producer writes a trailing NUL. Empty paths are not legal Git
        # names and empty newline records are merely separators.
        if not record:
            continue
        if len(record) > MAX_CHANGED_PATH_LENGTH:
            return None, (
                f"entry {index} exceeds the {MAX_CHANGED_PATH_LENGTH}-character "
                "changed-path limit"
            )
        line = record
        if line.startswith("./"):
            line = line[2:]
        normalized = posixpath.normpath(line)
        if (
            not line
            or posixpath.isabs(line)
            or normalized in (".", "..")
            or normalized.startswith("../")
            or normalized != line
        ):
            return None, (
                f"entry {index} is not a canonical repository-relative Git path"
            )
        changed.append(line)
        if len(changed) > MAX_CHANGED_FILES:
            return None, (
                f"list exceeds the {MAX_CHANGED_FILES:,}-changed-file limit; "
                "split the change or narrow the routing input"
            )
    return changed, None


def read_pr_body(path: Path) -> str:
    """Read the PR description text; a missing or unreadable file is empty."""
    try:
        # Preserve physical framing. The Markdown/directive parser accepts LF
        # and CRLF records; a bare CR is content, not a way to inject a new
        # top-level directive line.
        return read_utf8_text_exact(path)
    except (OSError, UnicodeDecodeError):
        return ""


def visible_pr_body(text: str) -> str:
    """Text eligible to satisfy routing directives and acknowledgments.

    HTML comments and fenced code are presentation-hidden or examples, not
    human-visible declarations. Unclosed comments/fences hide the remainder,
    matching Markdown's conservative interpretation.
    """
    return visible_markdown_text(text)


def physical_text_lines(text: str) -> list[str]:
    """Split only at physical LF/CRLF records, never Unicode separators."""
    records = text.split("\n")
    final_index = len(records) - 1
    return [
        line[:-1]
        if index < final_index and line.endswith("\r")
        else line
        for index, line in enumerate(records)
    ]


def visible_plain_text_payload(value: str) -> bool:
    """Whether a directive payload contains real visible, non-HTML content."""
    decoded = html.unescape(value)
    # Directive values are deliberately plain text.  Treat encoded or raw
    # empty elements as metadata, not as a human explanation.
    if re.search(r"<[^>]*>", decoded) is not None:
        return False
    return any(
        unicodedata.category(character)[0] in ("L", "N", "S")
        for character in decoded
    )


def leading_pr_directives(
    text: str,
) -> tuple[set[str], bool, bool, bool, bool, bool]:
    """Parse the unambiguous directive block at the start of visible prose.

    Blank lines are ignored. At column zero the only accepted sequences are
    positive impact then optional policy acknowledgment; no-impact then its
    mandatory reason then optional policy acknowledgment; or a policy-only
    acknowledgment. The first ordinary visible nonblank line ends the block.
    This deliberately small grammar prevents both presentation tricks and an
    out-of-order collection of independently valid lines from satisfying it.

    Returns ``(impact_ids, no_impact_declared, reason_present,
    policy_change_acknowledged, impact_ambiguous, order_invalid)``. Positive
    impact payloads are comma-separated exact invariant IDs. If any token is
    malformed, that whole positive line contributes no IDs. Exactly one impact
    directive is permitted; duplicate, conflicting, or separately malformed
    impact lines fail closed. The no-impact form remains a separate
    ``Assurance impact: none`` plus a visibly nonblank plain-text ``Reason:``.
    """
    impact_ids: set[str] = set()
    no_impact_declared = False
    reason_present = False
    policy_change_acknowledged = False
    impact_directive_count = 0
    order_invalid = False
    state = "start"
    for line in physical_text_lines(text):
        if not line.strip():
            continue
        is_no_impact = NO_IMPACT_RE.fullmatch(line) is not None
        impact_match = ASSURANCE_IMPACT_DIRECTIVE_RE.fullmatch(line)
        reason_match = NO_IMPACT_REASON_RE.fullmatch(line)
        policy_match = POLICY_ACK_RE.fullmatch(line)
        recognized = (
            is_no_impact
            or impact_match is not None
            or reason_match is not None
            or policy_match is not None
        )
        if not recognized:
            break

        if is_no_impact or impact_match is not None:
            impact_directive_count += 1

        if state == "start":
            if is_no_impact:
                no_impact_declared = True
                state = "need_reason"
                continue
            if impact_match is not None:
                payload = impact_match.group("ids").strip(" \t")
                identifiers = [item.strip(" \t") for item in payload.split(",")]
                if identifiers and not any(
                    INVARIANT_ID_RE.fullmatch(identifier) is None
                    for identifier in identifiers
                ):
                    impact_ids.update(identifiers)
                state = "after_positive_impact"
                continue
            if policy_match is not None:
                policy_change_acknowledged = visible_plain_text_payload(
                    policy_match.group("reason")
                )
                state = "done"
                continue
            # A Reason line cannot begin a directive block.
            order_invalid = True
            state = "invalid"
            continue

        if state == "need_reason" and reason_match is not None:
            reason_present = visible_plain_text_payload(reason_match.group("reason"))
            state = "after_reason"
            continue

        if state in ("after_positive_impact", "after_reason") and policy_match is not None:
            policy_change_acknowledged = visible_plain_text_payload(
                policy_match.group("reason")
            )
            state = "done"
            continue

        # Every other recognized continuation is out of contract: policy
        # before a declared impact, Reason before/after the wrong impact form,
        # or an additional directive after the optional policy line.
        order_invalid = True
        state = "invalid"

    impact_ambiguous = impact_directive_count > 1
    if impact_ambiguous or order_invalid:
        impact_ids.clear()
        no_impact_declared = False
        reason_present = False
        policy_change_acknowledged = False
    return (
        impact_ids,
        no_impact_declared,
        reason_present,
        policy_change_acknowledged,
        impact_ambiguous,
        order_invalid,
    )


def assurance_impact_directive_ids(text: str) -> set[str]:
    """Backward-compatible positive-ID view of ``leading_pr_directives``."""
    return leading_pr_directives(text)[0]


def added_diff_lines(diff_text: str) -> str:
    """Net-new regular-file lines in a unified diff, without ``+`` prefixes.

    Satisfaction must be judged on what the change *adds*: context lines
    would let an unrelated edit three lines away from an invariant's entry
    count as referencing it, and deletion-only changes (removing the entry)
    must not count as an update.  Exact deleted lines conservatively cancel
    identical additions, so an unchanged low-similarity move cannot become
    evidence.  Added symlink/gitlink payloads are excluded: their ``+`` lines
    describe object bindings, not assurance prose.
    """
    added: list[str] = []
    deleted: list[str] = []
    in_hunk = False
    old_mode: str | None = None
    head_mode: str | None = None
    # Unified diffs are framed by physical LF records. Unicode line-separator
    # characters are file content, not syntax: splitlines() would turn a
    # context line containing U+2028 followed by "+INV-..." into a fabricated
    # added record. Accept conventional CRLF by removing only its terminal CR.
    for line in physical_text_lines(diff_text):
        if line.startswith("diff --git "):
            in_hunk = False
            old_mode = None
            head_mode = None
            continue
        if not in_hunk:
            if line.startswith("new file mode "):
                old_mode = "000000"
                head_mode = line.rsplit(" ", 1)[-1]
            elif line.startswith("deleted file mode "):
                old_mode = line.rsplit(" ", 1)[-1]
                head_mode = "000000"
            elif line.startswith("old mode "):
                old_mode = line.rsplit(" ", 1)[-1]
            elif line.startswith("new mode "):
                head_mode = line.rsplit(" ", 1)[-1]
            elif line.startswith("index "):
                fields = line.split()
                if len(fields) == 3:
                    old_mode = fields[2]
                    head_mode = fields[2]
        if line.startswith("@@"):
            in_hunk = True
            continue
        regular_head = head_mode in (None, "100644", "100755")
        regular_old = old_mode in (None, "100644", "100755")
        if in_hunk and regular_head and line.startswith("+"):
            # Inside a hunk even a line beginning ``+++`` is content; header
            # suppression based only on the prefix dropped such additions.
            added.append(line[1:])
        elif in_hunk and regular_old and line.startswith("-"):
            deleted.append(line[1:])

    remaining_deleted: dict[str, int] = {}
    for line in deleted:
        remaining_deleted[line] = remaining_deleted.get(line, 0) + 1
    net_added: list[str] = []
    for line in added:
        if remaining_deleted.get(line, 0):
            remaining_deleted[line] -= 1
        else:
            net_added.append(line)
    return "\n".join(net_added)


@lru_cache(maxsize=4096)
def invariant_mention_re(identifier: str) -> re.Pattern[str]:
    """Compiled token-boundary matcher for a validated invariant ID."""
    return re.compile(rf"(?<![A-Z0-9-]){re.escape(identifier)}(?![A-Z0-9-])")


def mentions_id(text: str, identifier: str) -> bool:
    """Token-boundary match of a register ID inside free text.

    A plain substring test would let INV-CORE-001-EXT-002 (a valid ID)
    satisfy a requirement to mention INV-CORE-001. IDs are drawn from
    [A-Z0-9-]; the boundary excludes exactly that class.
    """
    return invariant_mention_re(identifier).search(text) is not None


def adoption_policy_regressions(
    base: dict,
    head: dict,
    adoption_path_transition: tuple[str, str, str, str] | None = None,
    *,
    allow_legacy_base_profiles: bool = False,
    base_lite_inline_system: bool | None = None,
    head_lite_inline_system: bool | None = None,
) -> list[tuple[str, str]]:
    """Assurance-significant changes of the head declaration vs the base one.

    Returns ``(kind, finding)`` pairs. Kind ``"weakened"``: declaration-path
    move, stage downgrade, active effective-profile removal, layout change,
    component removal, removal of a component's path globs or invariant IDs
    (editing a glob counts — the old glob disappears), a changed committed
    project identity, material-change workflow, security path, or
    issue-integration control, and a changed human-review provenance field or
    approval scope, or a backdated/removed completed-review date (advancing
    ``human_review.date`` is the normal re-review act). Kind ``"profile"``
    records the required explicit archived-to-active mode change
    without mislabeling it as a weakening. Kind ``"pin"``:
    any change to the upstream pin — not a weakening per se (upgrades move
    it forward), but PROFILE.md section 16 requires a pin move to be an
    explicit, dedicated change, so it demands the same acknowledgment.
    Additions are not findings.
    """
    findings: list[tuple[str, str]] = []

    if adoption_path_transition is not None:
        base_path, head_path, base_resolved, head_resolved = adoption_path_transition
        if base_path != head_path:
            findings.append(
                (
                    "weakened",
                    "adoption declaration path changed from "
                    f"{base_path!r} to {head_path!r} — moving the policy can "
                    "move it outside established review and CODEOWNERS controls",
                )
            )
        elif base_resolved != head_resolved:
            findings.append(
                (
                    "weakened",
                    "adoption declaration symlink target changed from "
                    f"{base_resolved!r} to {head_resolved!r} while the "
                    f"reviewed lexical path remained {base_path!r}",
                )
            )

    base_stage = base.get("adoption_stage", "DRAFT")
    head_stage = head.get("adoption_stage", "DRAFT")
    if (
        base_stage in ADOPTION_STAGES
        and head_stage in ADOPTION_STAGES
        and ADOPTION_STAGES.index(head_stage) < ADOPTION_STAGES.index(base_stage)
    ):
        findings.append(
            (
                "weakened",
                f"adoption_stage downgraded from {base_stage} to {head_stage}",
            )
        )

    def string_set(value: object) -> set[str]:
        if not isinstance(value, list):
            return set()
        return {
            item
            for item in value
            if isinstance(item, str) and not is_generic_placeholder(item)
        }

    removed_profiles = sorted(
        effective_profile_set(
            base.get("profiles"),
            allow_mixed_archived=allow_legacy_base_profiles,
        )
        - effective_profile_set(head.get("profiles"))
    )
    # `archived` is an exclusive mode marker, not an inherited obligation.
    # Dropping it while adding active profiles is the required path for
    # resuming operation or functional maintenance. The reverse transition
    # still removes active effective profiles and remains a finding.
    removed_profiles = [profile for profile in removed_profiles if profile != "archived"]
    if removed_profiles:
        findings.append(
            (
                "weakened",
                f"effective profile(s) removed: {', '.join(removed_profiles)}",
            )
        )
    base_declared_profiles = (
        validated_profile_declaration(base.get("profiles"))
        if allow_legacy_base_profiles
        else consistent_profile_declaration(base.get("profiles"))
    )
    head_declared_profiles = consistent_profile_declaration(head.get("profiles"))
    if (
        base_declared_profiles == ["archived"]
        and head_declared_profiles is not None
        and head_declared_profiles != ["archived"]
    ):
        findings.append(
            (
                "profile",
                "profile mode changed from archived to active "
                f"({', '.join(head_declared_profiles)}) — resuming active "
                "obligations requires an explicit reclassification",
            )
        )

    # An absent layout means the split layout; making the default explicit
    # (or dropping the explicit default) is not a change.
    base_layout = base.get("layout") or "split"
    head_layout = head.get("layout") or "split"
    if base_layout != head_layout:
        findings.append(
            ("weakened", f"layout changed from {base_layout} to {head_layout}")
        )

    # Under lite, the system obligation can be supplied either by the inline
    # field in `.agentic-assurance/assurance.yaml` or by the mapped/default
    # system artifact. Moving between those sources changes the reviewed
    # policy location even when `layout` and the dormant `paths.system`
    # spelling remain unchanged, so it needs the same explicit gate as any
    # other policy relocation. Only compare when both roots were available to
    # inspect; without them, the conservative mapped-path comparison below
    # remains the standalone fallback.
    if (
        base_layout == "lite"
        and head_layout == "lite"
        and isinstance(base_lite_inline_system, bool)
        and isinstance(head_lite_inline_system, bool)
        and base_lite_inline_system != head_lite_inline_system
    ):
        def lite_system_source_label(adoption: dict, inline: bool) -> str:
            if inline:
                return f"inline {LITE_ASSURANCE_PATH!r} system field"
            declared = adoption.get("paths")
            declared = declared if isinstance(declared, dict) else {}
            raw = declared.get("system", DEFAULT_PATHS["system"])
            normalized = (
                posixpath.normpath(raw) if committed_string(raw) else raw
            )
            return f"mapped system artifact {normalized!r}"

        before_source = lite_system_source_label(
            base, base_lite_inline_system
        )
        after_source = lite_system_source_label(
            head, head_lite_inline_system
        )
        findings.append(
            (
                "weakened",
                "lite system source changed from "
                f"{before_source} to {after_source} — moving system policy "
                "can move it outside established review and CODEOWNERS controls",
            )
        )

    base_upstream = base.get("upstream") if isinstance(base.get("upstream"), dict) else {}
    head_upstream = head.get("upstream") if isinstance(head.get("upstream"), dict) else {}
    for key in ("repository", "version", "commit"):
        before, after = base_upstream.get(key), head_upstream.get(key)
        if committed_string(before) and before != after:
            findings.append(
                (
                    "pin",
                    f"upstream.{key} changed from {before!r} to {after!r}",
                )
            )

    base_project = base.get("project") if isinstance(base.get("project"), dict) else {}
    head_project = head.get("project") if isinstance(head.get("project"), dict) else {}
    for key in ("name", "repository", "human_owner"):
        before, after = base_project.get(key), head_project.get(key)
        if committed_string(before) and before != after:
            findings.append(
                (
                    "weakened",
                    f"project.{key} changed from {before!r} to {after!r}",
                )
            )

    base_review = base.get("human_review") if isinstance(base.get("human_review"), dict) else {}
    head_review = head.get("human_review") if isinstance(head.get("human_review"), dict) else {}
    base_review_date = coerce_date(base_review.get("date"))
    head_review_date = coerce_date(head_review.get("date"))
    if base_review_date is not None and (
        head_review_date is None or head_review_date < base_review_date
    ):
        findings.append(
            (
                "weakened",
                "human_review.date regressed from "
                f"{base_review.get('date')!r} to {head_review.get('date')!r}; "
                "a completed re-review date may advance but must not be "
                "backdated, removed, or made invalid",
            )
        )
    for key in ("reviewer", "record"):
        before, after = base_review.get(key), head_review.get(key)
        comparable_before = (
            os.path.normpath(before)
            if key == "record" and committed_string(before)
            else before
        )
        comparable_after = (
            os.path.normpath(after)
            if key == "record" and committed_string(after)
            else after
        )
        if committed_string(before) and comparable_after != comparable_before:
            findings.append(
                (
                    "weakened",
                    f"human_review.{key} changed from {before!r} to {after!r}",
                )
            )

    def approval_tuples(
        review: dict,
    ) -> set[tuple[str, str, str, tuple[str, ...]]]:
        approvals = review.get("approvals")
        if not isinstance(approvals, list):
            return set()
        normalized = set()
        for entry in approvals:
            if not (
                isinstance(entry, dict)
                and all(
                    committed_string(entry.get(field))
                    for field in ATTRIBUTABLE_APPROVAL_FIELDS
                )
            ):
                continue
            covers = entry.get("covers")
            if "covers" not in entry:
                # Omission and the explicit reserved token have the same
                # full-conformance meaning (PROFILE.md section 17).
                normalized_covers = ("CONFORMANCE",)
            elif isinstance(covers, list) and all(
                committed_string(item) for item in covers
            ):
                normalized_covers = tuple(sorted(set(covers)))
            else:
                # Shape validation is the adopter job's responsibility, but
                # standalone drift must not collapse malformed scope into an
                # omitted (full) approval.
                normalized_covers = ("<INVALID_COVERS>", repr(covers))
            normalized.add(
                (
                    entry["approver"],
                    entry["review_url"],
                    entry["at"],
                    normalized_covers,
                )
            )
        return normalized

    removed_approvals = sorted(
        approval_tuples(base_review) - approval_tuples(head_review)
    )
    for approver, review_url, at, covers in removed_approvals:
        findings.append(
            (
                "weakened",
                "human_review approval provenance removed or rewritten: "
                f"approver={approver!r}, review_url={review_url!r}, at={at!r}, "
                f"covers={list(covers)!r}",
            )
        )

    # A moved artifact path can point the validator at a different (possibly
    # freshly emptied) file, and a moved public_assurance_root changes what
    # the disclosure rules bind — both are assurance-significant.
    base_paths = base.get("paths") if isinstance(base.get("paths"), dict) else {}
    head_paths = head.get("paths") if isinstance(head.get("paths"), dict) else {}
    base_effective_paths = resolve_paths(base)
    head_effective_paths = resolve_paths(head)
    # Standard paths have profile defaults in split layout. Under lite, the
    # consolidated assurance file replaces known split artifacts; only a
    # system fallback that may be active and mappings explicitly carried by
    # the reviewed base remain policy. A head-only mapping is an addition.
    protected_path_keys = set(base_paths)
    if base_layout != "lite":
        protected_path_keys.update(DEFAULT_PATHS)
    elif base_lite_inline_system is not True:
        # None means standalone drift could not safely inspect the lite file;
        # retain the conservative fallback-system gate in that case.
        protected_path_keys.add("system")
    for key in sorted(protected_path_keys):
        raw_before = base_paths.get(key)
        before = base_effective_paths.get(key)
        after = head_effective_paths.get(key)
        comparable_before = (
            os.path.normpath(before) if committed_string(before) else before
        )
        comparable_after = (
            os.path.normpath(after) if committed_string(after) else after
        )
        if (
            not is_generic_placeholder(raw_before)
            and comparable_before != comparable_after
        ):
            findings.append(
                (
                    "weakened",
                    f"paths.{key} changed from {before!r} to {after!r}",
                )
            )
    base_security = base.get("security") if isinstance(base.get("security"), dict) else {}
    head_security = head.get("security") if isinstance(head.get("security"), dict) else {}
    for key in ("policy", "restricted_record"):
        before, after = base_security.get(key), head_security.get(key)
        comparable_before = (
            os.path.normpath(before)
            if key == "policy" and committed_string(before)
            else before
        )
        comparable_after = (
            os.path.normpath(after)
            if key == "policy" and committed_string(after)
            else after
        )
        if committed_string(before) and comparable_before != comparable_after:
            findings.append(
                (
                    "weakened",
                    f"security.{key} changed from {before!r} to {after!r}",
                )
            )
    before_public_root = base_security.get("public_assurance_root")
    after_public_root = head_security.get("public_assurance_root")
    comparable_public_before = (
        os.path.normpath(before_public_root)
        if committed_string(before_public_root)
        else before_public_root
    )
    comparable_public_after = (
        os.path.normpath(after_public_root)
        if committed_string(after_public_root)
        else after_public_root
    )
    if (
        committed_string(before_public_root)
        and comparable_public_before != comparable_public_after
    ):
        findings.append(
            (
                "weakened",
                "security.public_assurance_root changed from "
                f"{before_public_root!r} to {after_public_root!r}",
            )
        )

    base_workflow = (
        base.get("specification_workflow")
        if isinstance(base.get("specification_workflow"), dict)
        else {}
    )
    head_workflow = (
        head.get("specification_workflow")
        if isinstance(head.get("specification_workflow"), dict)
        else {}
    )
    for key in ("system", "root"):
        before, after = base_workflow.get(key), head_workflow.get(key)
        comparable_before = (
            os.path.normpath(before) if key == "root" and committed_string(before) else before
        )
        comparable_after = (
            os.path.normpath(after) if key == "root" and committed_string(after) else after
        )
        if committed_string(before) and comparable_before != comparable_after:
            findings.append(
                (
                    "weakened",
                    f"specification_workflow.{key} changed from {before!r} "
                    f"to {after!r}",
                )
            )

    base_issue = (
        base.get("issue_integration")
        if isinstance(base.get("issue_integration"), dict)
        else {}
    )
    head_issue = (
        head.get("issue_integration")
        if isinstance(head.get("issue_integration"), dict)
        else {}
    )
    protected_issue_controls = {
        "stable_id_required": True,
        "public_security_issues_allowed": False,
        "closing_requires_artifact_update": True,
    }
    for key, protected_value in protected_issue_controls.items():
        before, after = base_issue.get(key), head_issue.get(key)
        if before is protected_value and after is not protected_value:
            findings.append(
                (
                    "weakened",
                    f"issue_integration.{key} changed from {before!r} "
                    f"to {after!r}",
                )
            )

    base_components = base.get("components") if isinstance(base.get("components"), dict) else {}
    head_components = head.get("components") if isinstance(head.get("components"), dict) else {}
    for name in sorted(base_components):
        if is_generic_placeholder(name):
            continue
        base_component = base_components[name]
        if not isinstance(base_component, dict):
            continue
        head_component = head_components.get(name)
        if not isinstance(head_component, dict):
            findings.append(("weakened", f"component '{name}' removed"))
            continue
        for field, noun in (("paths", "path glob(s)"), ("invariants", "invariant(s)")):
            removed = sorted(
                string_set(base_component.get(field)) - string_set(head_component.get(field))
            )
            if removed:
                findings.append(
                    ("weakened", f"component '{name}': {noun} removed: {', '.join(removed)}")
                )
    return findings


def normalized_repository_relative_path(
    value: object, *, allow_root: bool = False
) -> str | None:
    """Normalize one committed POSIX repository path, rejecting escapes."""
    if (
        not committed_string(value)
        or len(value) > MAX_POLICY_PATH_LENGTH
        or posixpath.isabs(value)
    ):
        return None
    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in value):
        return None
    normalized = posixpath.normpath(value)
    if normalized == ".":
        return "." if allow_root else None
    if normalized == ".." or normalized.startswith("../") or posixpath.isabs(normalized):
        return None
    return normalized


def policy_path_mapping_contract_error(adoption: dict) -> str | None:
    """Return a bounded-path diagnostic for schema-independent drift input."""
    declared = adoption.get("paths")
    if declared is None:
        return None
    if not isinstance(declared, dict):
        return "paths must be a mapping"
    if len(declared) > MAX_POLICY_PATH_MAPPINGS:
        return (
            f"paths exceeds the {MAX_POLICY_PATH_MAPPINGS}-mapping resource limit"
        )
    for key, value in declared.items():
        if not isinstance(value, str) or len(value) > MAX_POLICY_PATH_LENGTH:
            return (
                f"paths.{key} must be a string no longer than "
                f"{MAX_POLICY_PATH_LENGTH} characters"
            )
    return None


def lite_has_inline_system_at_root(root: Path) -> bool:
    """Read lite system prose only from contained, non-trusted project data."""
    try:
        resolved_root = root.resolve(strict=True)
        resolved = (resolved_root / LITE_ASSURANCE_PATH).resolve(strict=False)
    except (OSError, RuntimeError, ValueError):
        return False
    if not is_within(resolved, resolved_root):
        return False
    try:
        relative = resolved.relative_to(resolved_root)
    except ValueError:
        return False
    if any(
        relative == Path(excluded) or Path(excluded) in relative.parents
        for excluded in (".git", ".assurance-profile-pin")
    ):
        return False
    if not resolved.is_file():
        return False
    document, error = load_yaml(resolved)
    return (
        error is None
        and isinstance(document, dict)
        and nonempty_string(document.get("system"))
    )


def policy_artifact_bindings(
    adoption: dict, root: Path
) -> dict[str, tuple[str, str]]:
    """Policy paths as ``(normalized lexical, raw resolution spelling)``."""
    bindings: dict[str, tuple[str, str]] = {}
    declared_paths = adoption.get("paths")
    declared_paths = declared_paths if isinstance(declared_paths, dict) else {}
    if adoption.get("layout") == "lite":
        mapped_paths = dict(declared_paths)
        if (
            "system" not in mapped_paths
            and not lite_has_inline_system_at_root(root)
        ):
            mapped_paths["system"] = DEFAULT_PATHS["system"]
    else:
        mapped_paths = resolve_paths(adoption)
    for key, value in mapped_paths.items():
        normalized = normalized_repository_relative_path(value)
        if normalized is not None:
            bindings[f"paths.{key}"] = (normalized, value)

    workflow = adoption.get("specification_workflow")
    if isinstance(workflow, dict):
        normalized = normalized_repository_relative_path(
            workflow.get("root"), allow_root=True
        )
        if normalized is not None:
            bindings["specification_workflow.root"] = (
                normalized,
                workflow["root"],
            )

    human_review = adoption.get("human_review")
    if isinstance(human_review, dict):
        normalized = normalized_repository_relative_path(human_review.get("record"))
        if normalized is not None:
            bindings["human_review.record"] = (normalized, human_review["record"])

    security = adoption.get("security")
    if isinstance(security, dict):
        for key in ("policy", "public_assurance_root"):
            normalized = normalized_repository_relative_path(
                security.get(key), allow_root=key == "public_assurance_root"
            )
            if normalized is not None:
                bindings[f"security.{key}"] = (normalized, security[key])

    # These fixed entry points establish the reading order and lite contract;
    # their lexical names cannot be changed in adoption.yaml, so their target
    # identity needs an explicit comparison.
    bindings["root.AGENTIC_ASSURANCE.md"] = (
        "AGENTIC_ASSURANCE.md",
        "AGENTIC_ASSURANCE.md",
    )
    bindings["root.AGENTS.md"] = ("AGENTS.md", "AGENTS.md")
    if adoption.get("layout") == "lite":
        bindings["layout.lite"] = (LITE_ASSURANCE_PATH, LITE_ASSURANCE_PATH)
    return bindings


def resolved_policy_target(root: Path, relative: str) -> str:
    """Return a contained resolved target, or a controlled invalid sentinel."""
    candidate = root / relative
    if not os.path.lexists(candidate):
        return "<missing>"
    if nonportable_project_symlink(candidate, root) is not None:
        return "<non-portable-symlink>"
    try:
        resolved_root = root.resolve(strict=True)
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        return "<unresolvable>"
    if not is_within(resolved, resolved_root):
        return "<outside-project>"
    return resolved.relative_to(resolved_root).as_posix()


def policy_path_target_regressions(
    base: dict,
    head: dict,
    base_root: Path,
    head_root: Path,
) -> list[tuple[str, str]]:
    """Detect silent retargeting behind unchanged policy path strings.

    Lexical path changes are handled by ``adoption_policy_regressions``. This
    comparison binds a retained lexical path to its reviewed in-repository
    target, closing a symlink-retargeting gap while preserving safe aliases.
    """
    findings: list[tuple[str, str]] = []
    base_bindings = policy_artifact_bindings(base, base_root)
    head_bindings = policy_artifact_bindings(head, head_root)
    invalid = {
        "<missing>",
        "<unresolvable>",
        "<outside-project>",
        "<non-portable-symlink>",
    }
    for label, (base_relative, base_raw) in sorted(base_bindings.items()):
        head_binding = head_bindings.get(label)
        if head_binding is None:
            continue
        head_relative, head_raw = head_binding
        if head_relative != base_relative:
            continue  # lexical policy changes are already compared elsewhere
        # Resolve the original spelling.  Collapsing ``link/../target`` before
        # resolution changes its meaning when ``link`` itself is a symlink.
        base_target = resolved_policy_target(base_root, base_raw)
        # No object existed to retarget. This is normal for optional default
        # artifacts and for an upgrade that adds a previously missing required
        # artifact; the HEAD-side structural checks decide whether the new
        # snapshot is complete. Invalid *existing* base targets still fail
        # closed below.
        if base_target == "<missing>":
            continue
        if base_target in invalid:
            findings.append(
                (
                    "uncomparable",
                    f"{label} reviewed base target behind {base_relative!r} "
                    f"cannot be established ({base_target})",
                )
            )
            continue
        head_target = resolved_policy_target(head_root, head_raw)
        if head_target == "<missing>":
            findings.append(
                (
                    "weakened",
                    f"{label} target behind unchanged path "
                    f"{head_relative!r} was removed (was {base_target!r})",
                )
            )
            continue
        if head_target in invalid:
            findings.append(
                (
                    "uncomparable",
                    f"{label} HEAD target behind {head_relative!r} cannot be "
                    f"established ({head_target})",
                )
            )
            continue
        if head_target != base_target:
            findings.append(
                (
                    "weakened",
                    f"{label} resolved target changed behind unchanged path "
                    f"{base_relative!r}: {base_target!r} -> {head_target!r}",
                )
            )
    return findings


def order_index(order: tuple, value: object) -> int | None:
    """Index of a value in a strength order, or None when not a member."""
    try:
        return order.index(value)
    except ValueError:
        return None


def register_policy_regressions(
    base_registers: dict[str, list | None],
    head_registers: dict[str, list | None],
    today: datetime.date | None = None,
    allow_pre_v04_starter_entries: bool = False,
) -> list[tuple[str, str]]:
    """Weakenings of the head registers versus the base registers.

    Compared by stable ID; additions are never findings. A register present
    on the base but absent on the head is a whole-register removal finding
    (listing the former IDs) — an optional register such as defeaters under
    the core profile could otherwise be deleted wholesale with no finding;
    an unreadable head register, or a head register with duplicate IDs
    (last-one-wins would hide a weaker shadow entry), fails closed (the
    diff cannot be trusted). A register absent on the base, or unusable on
    the base, is skipped (its own errors are reported elsewhere).
    When ``allow_pre_v04_starter_entries`` is true, only a shipped example row
    whose complete prompt fingerprint is still intact is excluded from the
    baseline; callers must derive that flag from an actual pre-v0.4 base to
    v0.4+ head transition. A partly completed row remains policy, and replacing
    committed direct prose with any placeholder is itself a finding.

    Detected findings, by stable ID:
    - any register: entry deletion; whole-register removal; owner change
      (accountability transfer); a recorded judgement value unset —
      removed, emptied, or replaced with a non-string value
      (GATED_VALUE_FIELDS: status everywhere, plus severity, proof_tier,
      impact, uncertainty; unsetting one would otherwise be the free
      first hop of a laundered change); removal of items from the kind's
      protected relationship/basis lists (PROTECTED_LIST_FIELDS).
    - invariants: severity downgrade; conclusion-status weakening
      (VERIFIED/INFERRED toward UNKNOWN); an affirmative INTENDED,
      COMPATIBILITY, or DEPRECATED intent reclassified or unset, or its
      authority rewritten (same first-hop/provenance reasoning as status);
      enforcement/verification/evidence items removed from a high/critical
      invariant.
    - claims: status weakening; proof-tier downgrade.
    - invariants and claims: a recorded CONTRADICTED status cleared
      (moving to CONTRADICTED is an honesty upgrade and is never flagged;
      moving away from it is a reviewed disposition).
    - residuals: impact or uncertainty downgrade; closing (status ->
      RESOLVED); acceptance (status -> ACCEPTED — accepting a risk is a
      human decision, PROFILE.md sections 3 and 12); rewriting the
      acceptance record (accepted_by/accepted_at/acceptance_rationale), or
      rewriting resolution grounds while RESOLVED remains asserted.
    - defeaters: closing (status -> MITIGATED/RESOLVED/WITHDRAWN); a
      MITIGATED defeater moved to a terminal disposition
      (RESOLVED/WITHDRAWN); rewriting closure grounds while a closed
      disposition remains asserted.
    - defeaters and residuals: review_after removed, replaced with an
      unparsable value, or pushed out after the recorded date had
      already passed. Rescheduling a date still in the future is the
      normal outcome of doing the review, and is not flagged; nor is
      moving it earlier, adding one, or repairing an unparsable base
      value into a real date.

    The residual and defeater *disposition* gates (arrival at a closed or
    ACCEPTED status) fire regardless of the base value's type, so a
    missing or malformed base status fails toward a finding. Every other
    weakening check is pair-keyed on a meaningful value being recorded on
    both sides; for those, an unset base value is caught one hop earlier,
    when the value was removed.

    Claim/statement wording changes are deliberately not compared — that is
    the human review's terrain. Re-opening a closed residual/defeater, or
    recording a new contradiction, is never a weakening.
    """
    if today is None:
        today = latest_current_civil_date()
    findings: list[tuple[str, str]] = []

    def by_id(entries: list | None) -> dict[str, dict]:
        return {
            entry["id"]: entry
            for entry in (entries or [])
            if isinstance(entry, dict) and nonempty_string(entry.get("id"))
        }

    def duplicate_ids(entries: list | None) -> list[str]:
        """IDs that appear more than once in a register, sorted."""
        seen: set[str] = set()
        duplicates: set[str] = set()
        for entry in entries or []:
            if not (isinstance(entry, dict) and nonempty_string(entry.get("id"))):
                continue
            entry_id = entry["id"]
            if entry_id in seen:
                duplicates.add(entry_id)
            seen.add(entry_id)
        return sorted(duplicates)

    def weakened(order: tuple, before: object, after: object) -> bool:
        b, a = order_index(order, before), order_index(order, after)
        return b is not None and a is not None and a > b

    def reclassified(table: dict, before: object, after: object) -> bool:
        """True when `before` -> `after` is a listed weakening.

        The registers are loaded without schema validation (either side may
        predate the stricter schema, or the base may have merged directly to
        the default branch), so a status/classification value can be any
        YAML type. Guard the mapping lookup: a non-string ``before`` is never
        a key, so it can never name a weakening.
        """
        return isinstance(before, str) and after in table.get(before, ())

    def shown(value: object) -> str:
        """A status/field value rendered for a finding message.

        Meaningful strings render bare (matching the historical message
        format); anything else — None, a list, a bool, and an empty or
        whitespace-only string — renders as its repr, so a missing or
        malformed value never collapses into blank space in the message.
        """
        return value if nonempty_string(value) else repr(value)

    def str_items(entry: dict, field: str) -> set[str]:
        """The string items of a list-valued register field, else empty.

        The registers are unvalidated (see ``reclassified``), so a field
        that should be a list of strings may be any YAML type — a scalar
        such as ``evidence: 42`` must not crash the diff (``for x in 42``).
        Only genuine lists contribute items; anything else contributes none.
        """
        value = entry.get(field)
        if not isinstance(value, list):
            return set()
        return {
            item
            for item in value
            if isinstance(item, str) and not is_generic_placeholder(item)
        }

    for kind in REGISTER_KINDS:
        if kind not in base_registers or base_registers[kind] is None:
            continue
        base_by_id = {
            entry_id: entry
            for entry_id, entry in by_id(base_registers[kind]).items()
            if not (
                allow_pre_v04_starter_entries
                and is_shipped_template_entry(kind, entry)
            )
        }
        # Whole-register disappearance must not skip the per-ID diff silently:
        # for an optional register (e.g. defeaters under core), deleting the
        # file would otherwise erase every reviewed entry with no finding.
        if kind not in head_registers:
            if base_by_id:
                ids = ", ".join(sorted(base_by_id))
                findings.append(
                    (
                        "weakened",
                        f"{kind} register removed (was present on the base "
                        f"branch); former entries: {ids}",
                    )
                )
            continue
        if head_registers[kind] is None:
            # The head register file exists but is unusable (a load/parse
            # error, reported by the structural checks). Fail closed: the
            # policy comparison cannot be trusted, so record that rather than
            # passing the register silently.
            findings.append(
                (
                    "weakened",
                    f"{kind} register cannot be compared against the base "
                    "branch — it is unreadable on the head branch; fix it so "
                    "the policy diff can run",
                )
            )
            continue
        # Duplicate IDs on the head would make by_id() keep only the last
        # entry, hiding a weaker shadow entry under the same ID from this
        # diff (the structural checks flag duplicates too, but this check
        # must not depend on a sibling job being required). Fail closed.
        # Base-side duplicates are left last-one-wins: the base branch was
        # merged under its own checks, and flagging them here would punish
        # the head for cleaning them up.
        head_duplicates = duplicate_ids(head_registers[kind])
        if head_duplicates:
            findings.append(
                (
                    "weakened",
                    f"{kind} register has duplicate ids on the head branch "
                    f"({', '.join(head_duplicates)}) — the policy diff "
                    "compares by stable id and cannot be trusted; "
                    "deduplicate the ids",
                )
            )
            continue
        head_by_id = by_id(head_registers[kind])
        noun = REGISTER_NOUNS[kind]
        for entry_id in sorted(base_by_id):
            if entry_id not in head_by_id:
                findings.append(("weakened", f"{kind} entry {entry_id} deleted"))
                continue
            base_entry, head_entry = base_by_id[entry_id], head_by_id[entry_id]

            # Narrative changes normally remain human-review terrain, but a
            # real field changed back into a template prompt is not ordinary
            # editing. Flag that first hop so an arbitrary REPLACE_WITH_* value
            # cannot turn a committed example-ID row into a deletion-exempt
            # starter on the following pull request.
            for field in CURRENT_REGISTER_FIELD_PLACEHOLDERS.get(kind, {}):
                before, after = base_entry.get(field), head_entry.get(field)
                if committed_string(before) and is_direct_register_placeholder(
                    kind, field, after
                ):
                    findings.append(
                        (
                            "weakened",
                            f"{REGISTER_NOUNS[kind]} {entry_id} {field} was "
                            "replaced with a template placeholder",
                        )
                    )

            # Accountability, shared by every kind. An owner change is
            # flagged in both directions — neither is a "weakening" per se,
            # but both rewrite who answers for the entry, and nothing else
            # in the profile guards that field. `disclosure` is deliberately
            # NOT compared: it is not a strength axis, the risky direction
            # on a public repository is already an error at CONFORMANT, and
            # reclassifying during triage is routine.
            before, after = base_entry.get("owner"), head_entry.get("owner")
            if committed_string(before) and after != before:
                findings.append(
                    (
                        "weakened",
                        f"{noun} {entry_id} owner changed from {before!r} "
                        f"to {after!r} — an accountability transfer needs review",
                    )
                )
            # A recorded judgement value cannot be silently UNSET. Every
            # check that gates a weakening below is pair-keyed — it needs a
            # meaningful value on BOTH sides — so dropping one would
            # otherwise be a free first hop: delete the value in one change
            # (nothing to compare, silent) and record a weaker one in the
            # next (no baseline, silent), while the one-step version of the
            # same edit is a finding. All of these fields are schema-
            # required, so this also keeps the diff from depending on the
            # structural checks being configured as a required check.
            #
            # Scope, stated honestly: this closes the *unset* shape of that
            # first hop, not every shape. Overwriting a value with an
            # unrecognized string (`VERIFIED` -> `verified`) is pair-keyed
            # the same way and is left to the schema's enum check, which
            # rejects it in the adopter job. Closing it here would mean
            # flagging a recognized value replaced by an unrecognized one,
            # which must not fire when an adopter repairs a legacy value
            # that predates the stricter schema.
            for field in GATED_VALUE_FIELDS[kind]:
                before, after = base_entry.get(field), head_entry.get(field)
                if committed_string(before) and not committed_string(after):
                    findings.append(
                        (
                            "weakened",
                            f"{noun} {entry_id} {field} removed, emptied, or "
                            f"replaced with a non-string value (was {before}; "
                            f"now {shown(after)})",
                        )
                    )
            # Severed assurance-graph edges and removed caveats.
            for field in PROTECTED_LIST_FIELDS[kind]:
                removed = sorted(
                    str_items(base_entry, field) - str_items(head_entry, field)
                )
                if removed:
                    findings.append(
                        (
                            "weakened",
                            f"{noun} {entry_id}: {field} item(s) removed: "
                            f"{', '.join(removed)}",
                        )
                    )

            if kind == "invariants":
                if weakened(
                    SEVERITY_ORDER, base_entry.get("severity"), head_entry.get("severity")
                ):
                    findings.append(
                        (
                            "weakened",
                            f"invariant {entry_id} severity downgraded from "
                            f"{base_entry.get('severity')} to {head_entry.get('severity')}",
                        )
                    )
                base_intent = base_entry.get("intent") or {}
                head_intent = head_entry.get("intent") or {}
                before = (
                    base_intent.get("classification")
                    if isinstance(base_intent, dict)
                    else None
                )
                after = (
                    head_intent.get("classification")
                    if isinstance(head_intent, dict)
                    else None
                )
                if reclassified(INTENT_WEAKENINGS, before, after):
                    findings.append(
                        (
                            "weakened",
                            f"invariant {entry_id} intent reclassified from "
                            f"{before} to {after}",
                        )
                    )
                # Unsetting the recorded intent — deleting the key, the whole
                # intent mapping, or blanking the value — is the same free
                # first hop the status check above closes: the reclassified()
                # table is pair-keyed, so without this the commitment could be
                # dropped in one change and replaced in the next, both silent.
                # Keyed on all affirmative human dispositions: INTENDED,
                # COMPATIBILITY, and DEPRECATED each records a commitment.
                elif (
                    before in AFFIRMATIVE_INTENT_CLASSES
                    and not committed_string(after)
                ):
                    findings.append(
                        (
                            "weakened",
                            f"invariant {entry_id} intent.classification "
                            "removed, emptied, or replaced with a non-string "
                            f"value (was {before}; now {shown(after)}) — "
                            "unsetting a recorded intent decision needs review",
                        )
                    )
                base_authority = (
                    base_intent.get("authority")
                    if isinstance(base_intent, dict)
                    else None
                )
                head_authority = (
                    head_intent.get("authority")
                    if isinstance(head_intent, dict)
                    else None
                )
                if (
                    before in AFFIRMATIVE_INTENT_CLASSES
                    and after == before
                    and committed_string(base_authority)
                    and head_authority != base_authority
                ):
                    findings.append(
                        (
                            "weakened",
                            f"invariant {entry_id} intent.authority changed from "
                            f"{base_authority!r} to {head_authority!r} — "
                            "rewriting the human basis needs review",
                        )
                    )
                if base_entry.get("severity") in ("critical", "high"):
                    for field in INVARIANT_EVIDENCE_LISTS:
                        removed = sorted(
                            str_items(base_entry, field) - str_items(head_entry, field)
                        )
                        if removed:
                            findings.append(
                                (
                                    "weakened",
                                    f"invariant {entry_id} ({base_entry.get('severity')}): "
                                    f"{field} item(s) removed: {', '.join(removed)}",
                                )
                            )

            if kind in ("invariants", "claims"):
                before, after = base_entry.get("status"), head_entry.get("status")
                if reclassified(STATUS_WEAKENINGS, before, after):
                    findings.append(
                        (
                            "weakened",
                            f"{noun} {entry_id} status weakened from {before} to {after}",
                        )
                    )
                # Clearing a recorded contradiction (moving away from
                # CONTRADICTED) removes a known problem from the record; it
                # must be a reviewed disposition, not a silent edit. Only
                # meaningful head strings land here: an unset status is
                # already reported by the status check above, and reporting
                # both would double-count one edit.
                elif (
                    before == "CONTRADICTED"
                    and committed_string(after)
                    and after != "CONTRADICTED"
                ):
                    findings.append(
                        (
                            "weakened",
                            f"{noun} {entry_id} recorded contradiction cleared "
                            f"(CONTRADICTED to {after}) — resolving a "
                            "contradiction needs review",
                        )
                    )

            if kind == "claims":
                if weakened(
                    PROOF_TIER_ORDER,
                    base_entry.get("proof_tier"),
                    head_entry.get("proof_tier"),
                ):
                    findings.append(
                        (
                            "weakened",
                            f"claim {entry_id} proof_tier downgraded from "
                            f"{base_entry.get('proof_tier')} to {head_entry.get('proof_tier')}",
                        )
                    )
            if kind == "residuals":
                # Impact and uncertainty are the residual's two independent
                # assessment axes (PROFILE.md section 12); lowering either
                # reduces the recorded risk or claims more confidence than
                # the base branch had agreed to.
                for axis in ("impact", "uncertainty"):
                    if weakened(
                        IMPACT_ORDER, base_entry.get(axis), head_entry.get(axis)
                    ):
                        findings.append(
                            (
                                "weakened",
                                f"residual {entry_id} {axis} downgraded from "
                                f"{base_entry.get(axis)} to {head_entry.get(axis)}",
                            )
                        )
                # Closing a residual (to RESOLVED) removes a tracked risk from
                # active scrutiny. resolution_note being non-empty is a schema
                # matter; whether the closure is justified is a review matter.
                # No isinstance guard on the base status: what matters is
                # the head ARRIVING at a gated disposition. A missing or
                # non-string base value must fail toward a finding, not
                # toward silence (it would otherwise be the second hop of a
                # laundered transition).
                before, after = base_entry.get("status"), head_entry.get("status")
                if (
                    before not in RESIDUAL_CLOSED_STATUSES
                    and after in RESIDUAL_CLOSED_STATUSES
                ):
                    findings.append(
                        (
                            "weakened",
                            f"residual {entry_id} closed ({shown(before)} to "
                            f"{after}) — closing a tracked residual needs review",
                        )
                    )
                # Accepting a residual risk is an explicit human decision
                # (PROFILE.md sections 3 and 12: critical residuals need
                # explicit human acceptance, and an agent must not accept one
                # for the human owner). The acceptance fields themselves are
                # trivially fabricatable strings, so the transition must
                # route through the same review gate as a closure.
                if before != "ACCEPTED" and after == "ACCEPTED":
                    findings.append(
                        (
                            "weakened",
                            f"residual {entry_id} accepted ({shown(before)} to "
                            "ACCEPTED) — accepting a residual risk is a "
                            "human decision that needs review",
                        )
                    )
                for field in RESIDUAL_ACCEPTANCE_FIELDS:
                    before, after = base_entry.get(field), head_entry.get(field)
                    if committed_string(before) and after != before:
                        findings.append(
                            (
                                "weakened",
                                f"residual {entry_id} {field} changed from "
                                f"{before!r} to {after!r} — rewriting a "
                                "recorded acceptance needs review",
                            )
                        )
                # Preserve the grounds while the head continues to assert a
                # resolution. Re-opening is an honesty/attention increase and
                # may remove the now-withdrawn resolution assertion without
                # being mislabeled as a weakening.
                if (
                    base_entry.get("status") == "RESOLVED"
                    and head_entry.get("status") == "RESOLVED"
                ):
                    before_note = base_entry.get("resolution_note")
                    after_note = head_entry.get("resolution_note")
                    if committed_string(before_note) and after_note != before_note:
                        findings.append(
                            (
                                "weakened",
                                f"residual {entry_id} resolution_note changed "
                                f"from {before_note!r} to {after_note!r} — "
                                "rewriting recorded resolution grounds needs review",
                            )
                        )

            if kind == "defeaters":
                # Same rationale as the residual gates: no isinstance guard
                # on the base status — arriving at a closed disposition from
                # ANY non-closed base value (including a missing or
                # malformed one) is the reviewed event.
                before, after = base_entry.get("status"), head_entry.get("status")
                if (
                    before not in DEFEATER_CLOSED_STATUSES
                    and after in DEFEATER_CLOSED_STATUSES
                ):
                    findings.append(
                        (
                            "weakened",
                            f"defeater {entry_id} closed ({shown(before)} to "
                            f"{after}) — closing a defeater needs review",
                        )
                    )
                # MITIGATED means the risk is reduced but not eliminated
                # (defeaters.schema.json); RESOLVED and WITHDRAWN assert it
                # is gone or was never real. Upgrading a mitigation to a
                # terminal disposition is a materially stronger statement,
                # not a lateral move inside one "closed" class. Kept as an
                # extra edge on the set condition above (not a strict
                # transition table): an out-of-schema base status must keep
                # failing toward a finding, not toward silence.
                elif before == "MITIGATED" and after in ("RESOLVED", "WITHDRAWN"):
                    findings.append(
                        (
                            "weakened",
                            f"defeater {entry_id} disposition changed "
                            f"(MITIGATED to {after}) — closing out a "
                            "mitigated defeater needs review",
                        )
                    )
                # As above, a rewrite while a closed disposition remains is
                # protected; re-opening may remove obsolete closure prose.
                if (
                    base_entry.get("status") in DEFEATER_CLOSED_STATUSES
                    and head_entry.get("status") in DEFEATER_CLOSED_STATUSES
                ):
                    before_resolution = base_entry.get("resolution")
                    after_resolution = head_entry.get("resolution")
                    if (
                        committed_string(before_resolution)
                        and after_resolution != before_resolution
                    ):
                        findings.append(
                            (
                                "weakened",
                                f"defeater {entry_id} resolution changed from "
                                f"{before_resolution!r} to {after_resolution!r} — "
                                "rewriting recorded closure grounds needs review",
                            )
                        )

            if kind in ("defeaters", "residuals"):
                # A re-review commitment (review_after) can be kept, brought
                # forward, or rescheduled while it is still in the future —
                # completing a scheduled review and setting the next date is
                # the healthy path, and making it a finding would put a red
                # check on the one act the schedule exists to produce.
                # What cannot happen silently: dropping the commitment,
                # replacing it with a value the overdue check cannot parse,
                # or pushing out a date that has ALREADY passed — the last
                # is the review being evaded rather than done, and it is
                # exactly how a live overdue warning would be cleared.
                # Additions (no base value) are never findings. An
                # UNPARSABLE base value still counts as a recorded
                # commitment: removing it, or swapping it for different
                # garbage, is a finding; repairing it into a real date
                # re-enables the overdue check and is not.
                base_raw = base_entry.get("review_after")
                if base_raw is not None:
                    base_review = coerce_date(base_raw)
                    was = (
                        base_review.isoformat()
                        if base_review is not None
                        else repr(base_raw)
                    )
                    head_raw = head_entry.get("review_after")
                    head_review = coerce_date(head_raw)
                    if head_raw is None:
                        findings.append(
                            (
                                "weakened",
                                f"{noun} {entry_id} review_after removed "
                                f"(was {was}) — dropping a re-review "
                                "commitment needs review",
                            )
                        )
                    elif head_raw == base_raw:
                        pass  # unchanged, in whatever form it was recorded
                    elif is_review_date_placeholder(
                        base_raw
                    ) and is_review_date_placeholder(head_raw):
                        # The v0.3.x and v0.4.0 sentinels are aliases for the
                        # same unfilled DRAFT commitment. Migrating between
                        # them changes representation, not policy. A real
                        # date replaced by either sentinel still reaches the
                        # unparsable-value finding below.
                        pass
                    elif head_review is None:
                        findings.append(
                            (
                                "weakened",
                                f"{noun} {entry_id} review_after replaced "
                                f"with an unparsable value ({head_raw!r}; "
                                f"was {was})",
                            )
                        )
                    elif (
                        base_review is not None
                        and head_review > base_review
                        and base_review < today
                    ):
                        findings.append(
                            (
                                "weakened",
                                f"{noun} {entry_id} review_after postponed "
                                f"from {base_review.isoformat()} to "
                                f"{head_review.isoformat()}, after the "
                                "scheduled date had passed — an overdue "
                                "re-review is done, not deferred",
                            )
                        )
    return findings


def load_registers_from_root(
    root: Path,
    adoption: dict,
    report: Report,
    label: str,
    excluded_roots: tuple[Path, ...] = (),
    *,
    allow_legacy_yaml: bool = False,
) -> dict[str, list | None]:
    """Load the registers of an adoption declaration from a directory root.

    Used by the policy diff for both sides: the CI caller materializes the
    base branch's tree under a temporary root, and the head side reads from
    the adopting repository. Mirrors the head-side loading semantics:
    absent file = register absent; unreadable OR structurally unusable (the
    document is not a mapping carrying the register's list — e.g. a file
    that parses to a bare string) = None, and both are reported as errors —
    a register that exists but cannot be compared must never silently drop
    out of the policy diff. Lite layout reads the single assurance file's
    sections under the same rules.

    The declared ``paths:`` come from a pull-request-controlled adoption
    file, so they are run through ``check_declared_paths`` first — an
    absolute or ``..``-traversal value is dropped (and reported) exactly as
    in adopter mode, so this function never reads a file outside ``root``.
    """
    def load_register_document(path: Path) -> tuple[object, str | None]:
        document, error = load_yaml(path)
        if (
            error is not None
            and allow_legacy_yaml
            and "found duplicate key" in error
        ):
            legacy_document, legacy_error = load_yaml_legacy(path)
            if legacy_error is None:
                report.warn(
                    f"{label} ({path.relative_to(root)}): accepted pre-v0.4 "
                    "duplicate-key YAML with last-key-wins semantics for this "
                    "base-only migration comparison; clean it up in the head"
                )
                return legacy_document, None
        return document, error

    registers: dict[str, list | None] = {}
    if adoption.get("layout") == "lite":
        path = root / LITE_ASSURANCE_PATH
        if (
            checked_project_path(
                path,
                root,
                report,
                f"{label} ({LITE_ASSURANCE_PATH})",
                excluded_roots,
            )
            is None
        ):
            return {kind: None for kind in LITE_SECTION_KINDS}
        if not path.is_file():
            # Something that is not a readable regular file (a directory, a
            # broken symlink) is not "absent": fail closed, don't skip.
            if path.is_symlink() or path.exists():
                report.error(
                    f"{label} ({LITE_ASSURANCE_PATH}): exists but is not "
                    "a readable file"
                )
                return {kind: None for kind in LITE_SECTION_KINDS}
            return registers
        document, error = load_register_document(path)
        if error is not None:
            report.error(f"{label}: {error}")
            return {kind: None for kind in LITE_SECTION_KINDS}
        if not isinstance(document, dict):
            report.error(
                f"{label} ({LITE_ASSURANCE_PATH}): top level is not a mapping"
            )
            return {kind: None for kind in LITE_SECTION_KINDS}
        for kind in LITE_SECTION_KINDS:
            if kind in document:
                entries = register_entries({"version": 1, kind: document[kind]}, kind)
                if entries is None:
                    report.error(
                        f"{label} ({LITE_ASSURANCE_PATH}): section "
                        f"'{kind}' is not a list"
                    )
                registers[kind] = entries
        return registers
    paths = check_declared_paths(
        root, resolve_paths(adoption), report, excluded_roots
    )
    for kind in REGISTER_KINDS:
        relative = paths.get(kind)
        if relative is None:
            continue
        path = root / relative
        if not path.is_file():
            # A directory or broken symlink at the register's path is not
            # "absent": the register exists in some form and cannot be
            # compared — fail closed rather than dropping it from the diff.
            if path.is_symlink() or path.exists():
                report.error(
                    f"{label} ({relative}): exists but is not a readable file"
                )
                registers[kind] = None
            continue
        document, error = load_register_document(path)
        if error is not None:
            report.error(f"{label} ({relative}): {error}")
            registers[kind] = None
            continue
        entries = register_entries(document, kind)
        if entries is None:
            report.error(
                f"{label} ({relative}): not a mapping with a '{kind}' list "
                "— the register cannot be compared"
            )
        registers[kind] = entries
    return registers


def write_drift_step_summary(rows: list[tuple[str, int, str]]) -> None:
    """Append an impact-routing table to the GitHub job summary, if in CI."""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    try:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write("### Assurance impact routing\n\n")
            if not rows:
                handle.write("No mapped component is touched by this change.\n\n")
                return
            handle.write("| Component | Changed files | Result |\n|---|---|---|\n")
            for name, count, verdict in rows:
                handle.write(
                    f"| {markdown_table_cell(name)} | {count} | "
                    f"{markdown_table_cell(verdict)} |\n"
                )
            handle.write("\n")
    except OSError:
        pass  # the summary is best-effort; the log and annotations remain


def run_drift(args: argparse.Namespace) -> int:
    """Route a pull request's change set against the adoption component map.

    A component is *touched* when any of its path globs matches a changed
    file (the CI caller lists rename/copy sources as well as destinations,
    so moving code out of a mapped path still counts). A touched component
    is satisfied when the *added lines* of the assurance-artifact diff
    reference (with token boundaries) at least one of the component's
    invariant IDs (``--assurance-diff``; when
    the flag is absent — standalone use — any change under the assurance
    prefixes is accepted as the coarse fallback signal), when the PR
    description starts (at its first visible nonblank line) with a top-level
    ``Assurance impact: INV-API-001, INV-AUTH-002`` directive naming every
    invariant ID mapped to the component, or
    when the description's leading directive block carries an explicit
    no-impact statement (``Assurance impact: none`` plus a mandatory
    ``Reason:`` line).
    Unsatisfied components warn by default and fail with ``--strict``. The
    invariant IDs come from the map itself; whether they exist in the
    register is the adopter subcommand's cross-check.

    With ``--base-adoption`` (the base branch's adoption declaration), the
    head declaration is additionally screened for policy weakenings —
    declaration-path move (when ``--adoption-path-transition`` is supplied),
    stage downgrade, effective-profile removal, layout or upstream-pin change,
    approval-provenance/scope rewrite, and component removal or narrowing.
    An explicit ``Assurance policy change: <why>`` in the leading directive
    block turns findings into warnings only when the base stage is DRAFT;
    reviewed base stages stay errors. This runs before, and independently of,
    the component map (a repository with no components still gets its pin and
    stage protected).
    """
    report = Report()
    if (args.base_registers_root is None) != (args.project_root is None):
        report.error(
            "--base-registers-root and --project-root must be supplied together "
            "so both sides of the policy comparison are observable"
        )
        return report.emit("drift", args.json)
    if args.base_registers_root is not None and args.base_adoption is None:
        report.error(
            "--base-registers-root and --project-root require --base-adoption"
        )
        return report.emit("drift", args.json)
    base_registers_root: Path | None = None
    project_root: Path | None = None
    if args.base_registers_root is not None:
        resolved_roots: dict[str, Path] = {}
        for option, raw_value in (
            ("--base-registers-root", args.base_registers_root),
            ("--project-root", args.project_root),
        ):
            candidate = Path(raw_value)
            try:
                resolved = candidate.resolve(strict=True)
            except (OSError, RuntimeError, ValueError) as exc:
                report.error(f"{option} {str(candidate)!r} cannot be resolved: {exc}")
                continue
            if not resolved.is_dir():
                report.error(
                    f"{option} {str(candidate)!r} must resolve to an existing directory"
                )
                continue
            resolved_roots[option] = resolved
        if report.has_errors:
            return report.emit("drift", args.json)
        base_registers_root = resolved_roots["--base-registers-root"]
        project_root = resolved_roots["--project-root"]
        if is_same_filesystem_tree(
            base_registers_root, project_root
        ) or is_same_filesystem_tree(project_root, base_registers_root):
            report.error(
                "--base-registers-root and --project-root must resolve to "
                "distinct directories with no ancestor/descendant overlap"
            )
            return report.emit("drift", args.json)
    adoption_path = Path(args.adoption)
    validator_root = Path(__file__).resolve().parent.parent
    head_excluded_inputs: list[Path] = []
    if project_root is not None:
        head_excluded_inputs.extend(
            [project_root / ".git", project_root / ".assurance-profile-pin"]
        )
        if is_within(validator_root, project_root.resolve()):
            head_excluded_inputs.append(validator_root)
    head_excluded_roots = normalized_excluded_roots(head_excluded_inputs)

    # Strict loading, as in adopter mode: an unreadable or malformed
    # adoption declaration is an error, never silently skipped.
    document, error = load_yaml(adoption_path)
    if error is not None:
        report.error(f"adoption file: {error}")
        return report.emit("drift", args.json)
    if not isinstance(document, dict):
        report.error(f"adoption file {adoption_path}: top level is not a mapping")
        return report.emit("drift", args.json)
    check_issue_integration_semantics(document, report)
    path_mapping_error = policy_path_mapping_contract_error(document)
    if path_mapping_error is not None:
        report.error(f"head adoption file: {path_mapping_error}")
        return report.emit("drift", args.json)
    for path in nonmeaningful_string_paths(document):
        report.error(
            f"head adoption file: {path}: non-empty string contains no visible "
            "letter, number, punctuation, or symbol"
        )

    head_stage = declared_stage(document)
    if head_stage is None:
        report.error(
            f"head adoption_stage {document.get('adoption_stage')!r} is invalid; "
            f"expected one of {', '.join(ADOPTION_STAGES)} — policy comparison "
            "cannot be trusted"
        )
    head_profiles = consistent_profile_declaration(document.get("profiles"))
    if head_profiles is None:
        report.error(
            "head profiles declaration is malformed, empty, unknown, duplicate, "
            "or violates archived exclusivity — policy comparison cannot be trusted"
        )

    pr_body_path = Path(args.pr_body)
    try:
        pr_body_size = pr_body_path.stat().st_size
    except OSError:
        pr_body_size = 0  # missing/unreadable remains the documented empty body
    if pr_body_size > MAX_PR_BODY_BYTES:
        report.error(
            f"PR body is {pr_body_size:,} bytes; routing input is limited to "
            f"{MAX_PR_BODY_BYTES:,} bytes"
        )
        return report.emit("drift", args.json)
    body = visible_pr_body(read_pr_body(pr_body_path))
    (
        declared_impact_ids,
        no_impact_declared,
        no_impact_reason_present,
        policy_change_acknowledged,
        impact_directives_ambiguous,
        directive_order_invalid,
    ) = leading_pr_directives(body)

    adoption_path_transition: tuple[str, str, str, str] | None = None
    if args.adoption_path_transition is not None:
        transition, error = load_json(Path(args.adoption_path_transition))
        if error is not None:
            report.error(f"adoption path transition: {error}")
            return report.emit("drift", args.json)
        if not (
            isinstance(transition, dict)
            and all(
                nonempty_string(transition.get(field))
                for field in ("base", "head", "base_resolved", "head_resolved")
            )
        ):
            report.error(
                "adoption path transition: expected an object with non-blank "
                "string 'base', 'head', 'base_resolved', and 'head_resolved' "
                "repository-relative paths"
            )
            return report.emit("drift", args.json)

        def normalized_transition_path(value: str) -> str | None:
            # Git paths may contain newlines and other display-hostile bytes;
            # the workflow carries them through strict JSON and escapes them
            # at log sinks. NUL is the sole impossible path byte here.
            if "\0" in value or posixpath.isabs(value):
                return None
            normalized = posixpath.normpath(value)
            if (
                normalized in (".", "..")
                or normalized.startswith("../")
                or posixpath.isabs(normalized)
            ):
                return None
            return normalized

        normalized_transition = tuple(
            normalized_transition_path(transition[field])
            for field in ("base", "head", "base_resolved", "head_resolved")
        )
        if any(value is None for value in normalized_transition):
            report.error(
                "adoption path transition: lexical and resolved base/head "
                "values must be non-root paths contained in the repository"
            )
            return report.emit("drift", args.json)
        base_path, head_path, base_resolved, head_resolved = normalized_transition
        assert all(
            isinstance(value, str)
            for value in (base_path, head_path, base_resolved, head_resolved)
        )
        adoption_path_transition = (
            base_path,
            head_path,
            base_resolved,
            head_resolved,
        )
        if args.base_adoption is None:
            report.error(
                "--adoption-path-transition requires --base-adoption so the "
                "path change is bound to an actual base declaration"
            )
            return report.emit("drift", args.json)

    if args.base_adoption is not None:
        comparison_errors_before = sum(
            1 for level, _ in report.results if level == "error"
        )
        base_document, error = load_yaml(Path(args.base_adoption))
        if error is not None:
            legacy_document: object = None
            legacy_error: str | None = None
            if "found duplicate key" in error:
                legacy_document, legacy_error = load_yaml_legacy(
                    Path(args.base_adoption)
                )
            if (
                legacy_error is None
                and isinstance(legacy_document, dict)
                and uses_pre_v04_starter_contract(legacy_document)
            ):
                base_document = legacy_document
                report.warn(
                    "base adoption file: accepted pre-v0.4 duplicate-key YAML "
                    "with last-key-wins semantics for this migration comparison; "
                    "the head declaration remains strict"
                )
            else:
                report.error(f"base adoption file: {error}")
                return report.emit("drift", args.json)
        if not isinstance(base_document, dict):
            report.error("base adoption file: top level is not a mapping")
            return report.emit("drift", args.json)
        path_mapping_error = policy_path_mapping_contract_error(base_document)
        if path_mapping_error is not None:
            report.error(f"base adoption file: {path_mapping_error}")
            return report.emit("drift", args.json)
        base_stage = declared_stage(base_document)
        if base_stage is None:
            report.error(
                f"base adoption_stage {base_document.get('adoption_stage')!r} is "
                f"invalid; expected one of {', '.join(ADOPTION_STAGES)} — policy "
                "comparison cannot be trusted"
            )
        legacy_base_contract = uses_pre_v04_starter_contract(base_document)
        base_profiles = (
            validated_profile_declaration(base_document.get("profiles"))
            if legacy_base_contract
            else consistent_profile_declaration(base_document.get("profiles"))
        )
        if base_profiles is None:
            report.error(
                "base profiles declaration is malformed, empty, unknown, duplicate, "
                "or violates the applicable archived-exclusivity contract — "
                "policy comparison cannot be trusted"
            )
        policy_comparable = (
            base_stage is not None
            and head_stage is not None
            and base_profiles is not None
            and head_profiles is not None
        )
        base_lite_inline_system = None
        if (
            base_document.get("layout") == "lite"
            and base_registers_root is not None
        ):
            base_lite_inline_system = lite_has_inline_system_at_root(
                base_registers_root
            )
        head_lite_inline_system = None
        if document.get("layout") == "lite" and project_root is not None:
            head_lite_inline_system = lite_has_inline_system_at_root(project_root)
        regressions = (
            adoption_policy_regressions(
                base_document,
                document,
                adoption_path_transition=adoption_path_transition,
                allow_legacy_base_profiles=legacy_base_contract,
                base_lite_inline_system=base_lite_inline_system,
                head_lite_inline_system=head_lite_inline_system,
            )
            if policy_comparable
            else []
        )

        # Bind unchanged policy path strings to the repository objects they
        # resolved to on the reviewed base.  This comparison applies to active
        # and archived modes alike; register semantics below remain active-only.
        if (
            policy_comparable
            and base_registers_root is not None
            and project_root is not None
        ):
            regressions.extend(
                policy_path_target_regressions(
                    base_document,
                    document,
                    base_registers_root,
                    project_root,
                )
            )

        # Register-level weakenings (stable-ID diff) when the caller
        # materialized the base branch's register files.
        if (
            policy_comparable
            and base_profiles != ["archived"]
            and head_profiles != ["archived"]
            and base_registers_root is not None
            and project_root is not None
        ):
            base_registers = load_registers_from_root(
                base_registers_root,
                base_document,
                report,
                "base register",
                normalized_excluded_roots(
                    [
                        base_registers_root / ".git",
                        base_registers_root / ".assurance-profile-pin",
                    ]
                ),
                allow_legacy_yaml=legacy_base_contract,
            )
            head_registers = load_registers_from_root(
                project_root,
                document,
                report,
                "head register",
                head_excluded_roots,
            )
            regressions.extend(
                register_policy_regressions(
                    base_registers,
                    head_registers,
                    allow_pre_v04_starter_entries=is_pre_v04_to_v04_upgrade(
                        base_document, document
                    ),
                )
            )

        # Enforcement is proportional to the stage the BASE declaration had
        # agreed to (the head stage cannot be the yardstick — a downgrade PR
        # would lower it in the same change). At DRAFT an explicit
        # acknowledgment turns findings into warnings; from HUMAN_REVIEWED
        # on, findings stay errors even when acknowledged — the red check is
        # the honest signal, and merging over it remains an explicit human
        # decision.
        binding_stage = base_stage
        if policy_comparable and regressions:
            acknowledged = policy_change_acknowledged
            for kind, finding in regressions:
                if kind == "uncomparable":
                    # An invalid/missing base binding is not a deliberate
                    # weakening that a DRAFT acknowledgment can waive: there
                    # is no trustworthy baseline identity to compare. Fail
                    # closed until the policy is observable on both sides.
                    report.error(
                        "assurance policy baseline cannot be compared: "
                        f"{finding}"
                    )
                    continue
                if kind == "pin":
                    prefix = "upstream pin changed"
                    rule = (
                        "a pin move must be an explicit, dedicated change "
                        "(PROFILE.md section 16) and"
                    )
                elif kind == "profile":
                    prefix = "assurance profile mode changed"
                    rule = "reclassifying archived work as active"
                else:
                    prefix = "assurance policy weakened"
                    rule = "weakening the assurance policy"
                if acknowledged and binding_stage == "DRAFT":
                    report.warn(
                        f"{prefix}: {finding} — acknowledged by 'Assurance "
                        "policy change:' in the PR description"
                    )
                elif acknowledged:
                    report.error(
                        f"{prefix}: {finding} — acknowledged, but the base "
                        f"declaration is stage {binding_stage}: policy "
                        "gated policy findings stay errors under a reviewed "
                        "stage; merging over this red check remains an explicit "
                        "human decision"
                    )
                else:
                    order_detail = (
                        " The leading directive lines are out of contract order; "
                        "use impact, then Reason for `none`, then policy."
                        if directive_order_invalid
                        else ""
                    )
                    report.error(
                        f"{prefix}: {finding} — {rule} requires an explicit "
                        "'Assurance policy change: <why>' line in the leading "
                        "directive block of the PR description"
                        f"{order_detail}"
                    )
        elif policy_comparable and sum(
            1 for level, _ in report.results if level == "error"
        ) == comparison_errors_before:
            report.ok("no assurance policy regression against the base declaration")

    components = document.get("components")
    if components is None:
        if not report.has_errors:
            report.ok("no component map — impact routing not configured")
        return report.emit("drift", args.json)
    if not isinstance(components, dict) or not components:
        report.error(
            "components: must be a non-empty mapping of component name to "
            "{paths, invariants}"
        )
        return report.emit("drift", args.json)
    if len(components) > MAX_COMPONENTS:
        report.error(
            f"components: exceeds the {MAX_COMPONENTS}-component routing limit"
        )
        return report.emit("drift", args.json)

    changed, error = read_changed_files(Path(args.changed_files))
    if error is not None:
        report.error(f"changed-files list: {error}")
        return report.emit("drift", args.json)

    assurance_diff_added: str | None = None
    if args.assurance_diff is not None:
        try:
            assurance_diff_path = Path(args.assurance_diff)
            assurance_diff_size = assurance_diff_path.stat().st_size
            if assurance_diff_size > MAX_ASSURANCE_DIFF_BYTES:
                report.error(
                    f"assurance diff is {assurance_diff_size:,} bytes; routing "
                    f"input is limited to {MAX_ASSURANCE_DIFF_BYTES:,} bytes"
                )
                return report.emit("drift", args.json)
            assurance_diff_added = added_diff_lines(
                read_utf8_text_exact(assurance_diff_path)
            )
        except (OSError, UnicodeDecodeError) as exc:
            report.error(
                f"assurance diff: cannot read {args.assurance_diff} as UTF-8: {exc}"
            )
            return report.emit("drift", args.json)

    # Validate and bound the standalone routing surface before performing any
    # pattern/path or invariant/text cross product. The adopter schema carries
    # the same shape limits, but drift is also a public standalone subcommand.
    validated_components: list[tuple[str, list[str], list[str]]] = []
    for name, component in components.items():
        if not isinstance(name, str) or not name.strip():
            report.error("component names must be non-blank strings")
            continue
        if len(name) > MAX_COMPONENT_NAME_LENGTH:
            report.error(
                f"component name exceeds the {MAX_COMPONENT_NAME_LENGTH}-character limit"
            )
            continue
        if not isinstance(component, dict):
            report.error(
                f"component '{name}': must be a mapping with 'paths' and 'invariants'"
            )
            continue
        path_globs = component.get("paths")
        invariant_ids = component.get("invariants")
        if not (
            isinstance(path_globs, list)
            and path_globs
            and all(nonempty_string(item) for item in path_globs)
        ):
            report.error(
                f"component '{name}': 'paths' must be a non-empty list of glob strings"
            )
            continue
        if len(path_globs) > MAX_COMPONENT_PATH_GLOBS:
            report.error(
                f"component '{name}': exceeds the "
                f"{MAX_COMPONENT_PATH_GLOBS}-path-glob limit"
            )
            continue
        if any(len(item) > MAX_COMPONENT_PATH_GLOB_LENGTH for item in path_globs):
            report.error(
                f"component '{name}': path glob exceeds the "
                f"{MAX_COMPONENT_PATH_GLOB_LENGTH}-character limit"
            )
            continue
        if any(not canonical_repository_relative_glob(item) for item in path_globs):
            report.error(
                f"component '{name}': path globs must be canonical "
                "repository-relative patterns without absolute, empty, '.', "
                "or '..' path components"
            )
            continue
        if not (
            isinstance(invariant_ids, list)
            and invariant_ids
            and all(nonempty_string(item) for item in invariant_ids)
        ):
            report.error(
                f"component '{name}': 'invariants' must be a non-empty list of invariant IDs"
            )
            continue
        if len(invariant_ids) > MAX_COMPONENT_INVARIANTS:
            report.error(
                f"component '{name}': exceeds the "
                f"{MAX_COMPONENT_INVARIANTS}-invariant limit"
            )
            continue
        if any(len(item) > MAX_INVARIANT_ID_LENGTH for item in invariant_ids):
            report.error(
                f"component '{name}': invariant ID exceeds the "
                f"{MAX_INVARIANT_ID_LENGTH}-character limit"
            )
            continue
        if any(
            INVARIANT_ID_RE.fullmatch(item) is None for item in invariant_ids
        ):
            report.error(
                f"component '{name}': invariant IDs must match "
                "INV-<TOKEN>-...-<NNN> (uppercase letters, digits, and hyphens)"
            )
            continue
        validated_components.append((name, path_globs, invariant_ids))

    if report.has_errors:
        # Do not append a contradictory "no component touched" success after
        # malformed routing policy has already made the result unusable.
        return report.emit("drift", args.json)

    changed_work = sum(len(path) + 1 for path in changed)
    glob_work = sum(
        (len(pattern) + 1) * changed_work
        for _, path_globs, _ in validated_components
        for pattern in path_globs
    )
    if glob_work > MAX_GLOB_MATCH_WORK:
        report.error(
            "component routing requires too much glob-matching work "
            f"({glob_work:,} cells; limit {MAX_GLOB_MATCH_WORK:,}) — split the "
            "change or reduce/narrow the component path map"
        )
        return report.emit("drift", args.json)
    mention_work = len(body) + sum(
        # Positive PR-body routing is parsed once above and checked by exact
        # set membership. Only the assurance diff still needs one bounded
        # token search per mapped ID; include identifier length so an empty
        # diff cannot make many regex compilations look like zero work.
        sum(
            (len(invariant_id) + 1) + len(assurance_diff_added or "")
            for invariant_id in invariant_ids
        )
        for _, _, invariant_ids in validated_components
        if assurance_diff_added is not None
    )
    if mention_work > MAX_MENTION_SCAN_WORK:
        report.error(
            "component routing requires too much invariant-mention scanning "
            f"({mention_work:,} bounded work units; limit "
            f"{MAX_MENTION_SCAN_WORK:,}) — reduce the component map or the "
            "routing text/diff"
        )
        return report.emit("drift", args.json)

    # Coarse fallback signal, used only when no assurance diff was provided
    # (standalone runs): any change under the assurance prefixes satisfies
    # every touched component. In CI the caller always provides the diff,
    # and satisfaction is per component — an unrelated assurance edit no
    # longer satisfies an unrelated component.
    assurance_touched = any(
        path.startswith(ASSURANCE_ARTIFACT_PREFIXES) for path in changed
    )
    no_impact_ok = no_impact_declared and no_impact_reason_present

    summary_rows: list[tuple[str, int, str]] = []
    for name, path_globs, invariant_ids in validated_components:
        matched = [
            path
            for path in changed
            if any(path_glob_matches(pattern, path) for pattern in path_globs)
        ]
        if not matched:
            continue
        count = len(matched)
        touched = f"component '{name}' touched ({count} changed file{'s' if count != 1 else ''})"
        ids = ", ".join(invariant_ids)
        diff_mentioned = (
            [
                invariant_id
                for invariant_id in invariant_ids
                if mentions_id(assurance_diff_added, invariant_id)
            ]
            if assurance_diff_added is not None
            else []
        )
        if diff_mentioned:
            verdict = f"assurance update references {', '.join(diff_mentioned)}"
            report.ok(f"{touched} — {verdict}")
        elif assurance_diff_added is None and assurance_touched:
            verdict = "assurance artifacts updated in the same change"
            report.ok(f"{touched} — {verdict}")
        elif all(
            invariant_id in declared_impact_ids for invariant_id in invariant_ids
        ):
            verdict = (
                f"PR description's leading 'Assurance impact:' directive "
                f"routes {ids}"
            )
            report.ok(f"{touched} — {verdict}")
        elif no_impact_ok:
            verdict = "PR description declares 'Assurance impact: none' with a reason"
            report.ok(f"{touched} — {verdict}")
        else:
            verdict = "UNROUTED"
            message = (
                f"{touched} without an assurance update referencing its "
                "invariants, an explicit impact directive, or a no-impact "
                "statement "
                f"— address {ids} in the assurance artifacts or the PR "
                f"description with 'Assurance impact: {ids}' as its first "
                "visible nonblank line, "
                "or add 'Assurance impact: none' + 'Reason: ...' to the "
                "leading directive block of the PR description"
            )
            if no_impact_declared:
                message += (
                    " ('Assurance impact: none' was found but the mandatory "
                    "'Reason:' line is missing)"
                )
            if impact_directives_ambiguous:
                message += (
                    " (multiple leading 'Assurance impact:' directives were "
                    "found; exactly one is permitted for PR-body routing)"
                )
            elif directive_order_invalid:
                message += (
                    " (leading directives were out of contract order; use "
                    "impact, then 'Reason:' for none, then policy)"
                )
            if args.strict:
                report.error(message)
            else:
                report.warn(message)
        summary_rows.append((name, count, verdict))

    if not summary_rows:
        count = len(changed)
        report.ok(
            f"no mapped component is touched by this change "
            f"({count} changed file{'s' if count != 1 else ''})"
        )
    write_drift_step_summary(summary_rows)

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
        help="root of the pinned profile checkout; when omitted, its "
        "VERSION-bearing root is inferred from --schemas; the resolved root "
        "is used for VERSION comparison and the adopter/profile trust boundary",
    )
    adopter.add_argument(
        "--repo-visibility",
        choices=list(REPO_VISIBILITIES),
        default=None,
        help="the repository's visibility; private/internal keeps "
        "RESTRICTED/EMBARGOED entries a warning at stage CONFORMANT "
        "(ADOPTION.md permits them in private repositories), public or "
        "unset makes them errors",
    )
    adopter.add_argument(
        "--strict-review-dates",
        action="store_true",
        help="treat passed review_after dates as errors instead of warnings",
    )
    adopter.add_argument(
        "--ignore-stage",
        action="store_true",
        help="skip only HUMAN_REVIEWED/CONFORMANT stage-specific gates; "
        "DRAFT-equivalent baseline semantics and structural checks remain",
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
        help="file holding repo-relative changed paths; NUL-separated when it "
        "contains NUL (the lossless CI format), otherwise legacy newline-separated",
    )
    drift.add_argument(
        "--pr-body",
        required=True,
        help="file holding the PR description text (missing file = empty body)",
    )
    drift.add_argument(
        "--assurance-diff",
        default=None,
        help="file holding the diff of the assurance artifacts; a touched "
        "component is satisfied only when the diff's added lines reference "
        "one of its invariant IDs (absent: any assurance change satisfies, "
        "the coarse standalone fallback)",
    )
    drift.add_argument(
        "--base-adoption",
        default=None,
        help="the base branch's adoption declaration; enables the policy "
        "regression check (stage downgrade, pin change, component removal "
        "error unless the PR description acknowledges them; from stage "
        "HUMAN_REVIEWED on, errors even when acknowledged)",
    )
    drift.add_argument(
        "--adoption-path-transition",
        default=None,
        help="strict JSON object with base/head lexical and base_resolved/"
        "head_resolved repository-relative adoption declaration paths; with "
        "--base-adoption, moving or retargeting the policy is screened as an "
        "assurance-significant change",
    )
    drift.add_argument(
        "--base-registers-root",
        default=None,
        help="directory holding the materialized base policy artifacts at the "
        "paths the base declaration names; requires --project-root and "
        "--base-adoption, and together they enable "
        "resolved-target binding and the stable-ID register diff (deleted "
        "entries, severity/status/proof-tier/intent weakenings, evidence removal)",
    )
    drift.add_argument(
        "--project-root",
        default=None,
        help="root of the adopting repository (head side of the register diff); "
        "requires --base-registers-root and --base-adoption",
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
