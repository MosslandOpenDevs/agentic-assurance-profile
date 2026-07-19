"""Regression tests for scripts/validate.py (self-check, adopter, drift).

Standard library only (unittest, tempfile, pathlib, subprocess, json, copy).
The validator itself needs pyyaml + jsonschema, so every test invokes it as a
subprocess through the same interpreter that runs this suite
(``sys.executable``), asserting on exit codes and output substrings — the
actual CLI contract.

Fixtures are built programmatically in temporary directories. YAML fixture
files are written as JSON documents (JSON is valid YAML for PyYAML's
``safe_load``), which keeps scalar typing exact — a 40-zero commit SHA stays
a string — without needing pyyaml in the tests.

Coverage map (numbers refer to the suite's required-coverage list):
 1. TestSelfCheck
 2. TestAdopterBaseline
 3. TestAdopterPlaceholders
 4. TestHumanReviewedStage
 5. TestConformantStage (baseline + mutations a-g)
 6. TestConformantStage.test_ignore_stage_passes_structure_only
 7. TestDriftRouting (a-f)
 8. TestDriftPolicyRegression (a-e)
 9. TestLiteLayout
10. TestDriftRouting.test_rename_source_path_triggers_component
11. TestGithubAnnotations

v0.3.0 additions:
12. TestDriftPolicyRegression stage-proportional acknowledgment (DRAFT base
    downgrades findings to warnings; HUMAN_REVIEWED/CONFORMANT base keeps
    them errors even when acknowledged) and the adoption-level findings
    (project.human_owner, paths.*, security.public_assurance_root)
13. TestDriftRegisterPolicyDiff (--base-registers-root/--project-root
    stable-ID register diff, mutations a-h)
14. TestConformantRepoVisibility (--repo-visibility and RESTRICTED entries)
15. TestRegisterObligations (empty mandated registers)
16. TestSchemaHardening (non-empty string enforcement in the registers)
"""

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VALIDATOR = REPO_ROOT / "scripts" / "validate.py"
SCHEMAS_DIR = REPO_ROOT / "schemas"

# Fixed dates: far future for non-expired review_after, fixed past for
# expired ones. Tests must never depend on what today's date happens to be.
FUTURE_DATE = "2999-01-01"
PAST_DATE = "2000-01-01"


def clean_env(extra=None):
    """Environment without the GitHub Actions variables (annotations off)."""
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in ("GITHUB_ACTIONS", "GITHUB_STEP_SUMMARY")
    }
    if extra:
        env.update(extra)
    return env


def run_validator(args, env=None):
    """Run scripts/validate.py with args; return (exit_code, combined_output)."""
    completed = subprocess.run(
        [sys.executable, str(VALIDATOR), *args],
        capture_output=True,
        text=True,
        env=clean_env() if env is None else env,
        cwd=str(REPO_ROOT),
        timeout=120,
    )
    return completed.returncode, completed.stdout + completed.stderr


def write_yaml(path, document):
    """Write a fixture document as JSON, which PyYAML parses as YAML."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Adopter fixtures (split layout, core profile)
# ---------------------------------------------------------------------------


def baseline_adoption():
    return {
        "upstream": {
            "repository": "example/assurance-profile",
            "version": "v0.2.0",
            "commit": "0" * 40,
        },
        "project": {
            "name": "Example Project",
            "repository": "example/project",
            "human_owner": "Alice Example",
        },
        "profiles": ["core"],
    }


def baseline_residual():
    return {
        "id": "RES-CORE-001",
        "summary": "Example residual",
        "impact": "low",
        "uncertainty": "low",
        "status": "OPEN",
        "disclosure": "PUBLIC",
        "owner": "Alice Example",
    }


def baseline_invariant():
    return {
        "id": "INV-CORE-001",
        "title": "Example invariant",
        "statement": "The example property always holds",
        "severity": "low",
        "scope": "example scope",
        "status": "UNKNOWN",
        "disclosure": "PUBLIC",
        "owner": "Alice Example",
    }


def baseline_registers():
    """Minimal registers for a passing core adoption: one invariant, one residual.

    Both are obligations for every non-archived profile (PROFILE.md section 6.1)."""
    return {
        "invariants": {"version": 1, "invariants": [baseline_invariant()]},
        "residuals": {"version": 1, "residuals": [baseline_residual()]},
    }


def human_review_block():
    return {
        "date": "2026-01-01",
        "reviewer": "Alice Example",
        "record": "docs/reviews/2026-01-01.md",
    }


def conformant_fixture():
    """A fully CONFORMANT adoption: all four registers, attributable approval,
    accepted critical residual with rationale, verified critical invariant
    with evidence, future review_after dates."""
    adoption = baseline_adoption()
    adoption["adoption_stage"] = "CONFORMANT"
    review = human_review_block()
    review["approvals"] = [
        {
            "approver": "bob-reviewer",
            "review_url": "https://example.invalid/pr/1#pullrequestreview-1",
            "at": "2026-01-02",
        }
    ]
    adoption["human_review"] = review
    registers = {
        "claims": {
            "version": 1,
            "claims": [
                {
                    "id": "CLAIM-CORE-001",
                    "text": "Example claim",
                    "scope": "example scope",
                    "proof_tier": "OPERATOR_ATTESTED",
                    "status": "INFERRED",
                    "disclosure": "PUBLIC",
                    "owner": "Alice Example",
                    "invariants": ["INV-CORE-001"],
                }
            ],
        },
        "invariants": {
            "version": 1,
            "invariants": [
                {
                    "id": "INV-CORE-001",
                    "title": "Example invariant",
                    "statement": "The example property always holds",
                    "severity": "critical",
                    "scope": "example scope",
                    "status": "VERIFIED",
                    "disclosure": "PUBLIC",
                    "owner": "Alice Example",
                    "intent": {
                        "classification": "INTENDED",
                        "authority": "docs/adr/001.md",
                    },
                    "enforcement": ["ci guard"],
                    "verification": ["tests/test_example.py"],
                    "evidence": ["evidence/run-1.txt"],
                }
            ],
        },
        "defeaters": {
            "version": 1,
            "defeaters": [
                {
                    "id": "DEF-CORE-001",
                    "statement": "The guard may be bypassed on forks",
                    "status": "OPEN",
                    "disclosure": "PUBLIC",
                    "owner": "Alice Example",
                    "review_after": FUTURE_DATE,
                }
            ],
        },
        "residuals": {
            "version": 1,
            "residuals": [
                {
                    "id": "RES-CORE-001",
                    "summary": "Accepted critical residual",
                    "impact": "critical",
                    "uncertainty": "low",
                    "status": "ACCEPTED",
                    "disclosure": "PUBLIC",
                    "owner": "Alice Example",
                    "acceptance_rationale": "Cost of mitigation exceeds exposure",
                    "accepted_by": "Alice Example",
                    "accepted_at": "2026-01-01",
                    "review_after": FUTURE_DATE,
                }
            ],
        },
    }
    return adoption, registers


REGISTER_FILES = {
    "claims": "assurance/CLAIMS.yaml",
    "invariants": "assurance/INVARIANTS.yaml",
    "defeaters": "assurance/DEFEATERS.yaml",
    "residuals": "assurance/RESIDUALS.yaml",
}


def build_split_project(root, adoption, registers):
    """Write a split-layout adopter fixture; return the adoption file path."""
    root = Path(root)
    (root / "AGENTIC_ASSURANCE.md").write_text("# Assurance\n", encoding="utf-8")
    (root / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    (root / "assurance").mkdir(parents=True, exist_ok=True)
    (root / "assurance" / "SYSTEM.md").write_text("# System\n", encoding="utf-8")
    for kind, document in registers.items():
        write_yaml(root / REGISTER_FILES[kind], document)
    adoption_path = root / ".agentic-assurance" / "adoption.yaml"
    write_yaml(adoption_path, adoption)
    return adoption_path


def build_lite_project(root, adoption, assurance):
    """Write a lite-layout adopter fixture; return the adoption file path."""
    root = Path(root)
    (root / "AGENTIC_ASSURANCE.md").write_text("# Assurance\n", encoding="utf-8")
    (root / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    write_yaml(root / ".agentic-assurance" / "assurance.yaml", assurance)
    adoption_path = root / ".agentic-assurance" / "adoption.yaml"
    write_yaml(adoption_path, adoption)
    return adoption_path


def baseline_lite_assurance():
    return {
        "version": 1,
        "purpose": "Demonstrate the lite layout",
        "non_goals": ["No production guarantees"],
        "system": "A single-service example system",
        "invariants": [baseline_invariant()],
        "residuals": [baseline_residual()],
    }


def baseline_lite_adoption():
    adoption = baseline_adoption()
    adoption["layout"] = "lite"
    return adoption


class ValidatorTestCase(unittest.TestCase):
    """Shared helpers: temp dirs and the adopter/drift CLI wrappers."""

    def make_tmp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name)

    def run_adopter(self, project_root, adoption_path, *extra, env=None):
        return run_validator(
            [
                "adopter",
                "--adoption",
                str(adoption_path),
                "--project-root",
                str(project_root),
                "--schemas",
                str(SCHEMAS_DIR),
                *extra,
            ],
            env=env,
        )

    def run_split(self, adoption, registers, *extra, env=None):
        root = self.make_tmp()
        adoption_path = build_split_project(root, adoption, registers)
        return self.run_adopter(root, adoption_path, *extra, env=env)

    def run_lite(self, adoption, assurance, *extra):
        root = self.make_tmp()
        adoption_path = build_lite_project(root, adoption, assurance)
        return self.run_adopter(root, adoption_path, *extra)

    def run_drift(
        self,
        adoption,
        changed=(),
        body=None,
        assurance_diff=None,
        base_adoption=None,
        base_registers=None,
        head_registers=None,
        strict=False,
    ):
        root = self.make_tmp()
        write_yaml(root / "adoption.yaml", adoption)
        changed_path = root / "changed.txt"
        changed_path.write_text(
            "".join(line + "\n" for line in changed), encoding="utf-8"
        )
        args = [
            "drift",
            "--adoption",
            str(root / "adoption.yaml"),
            "--changed-files",
            str(changed_path),
        ]
        if body is None:
            # A missing PR body file is a valid, empty body per the contract.
            args += ["--pr-body", str(root / "missing-body.txt")]
        else:
            (root / "body.txt").write_text(body, encoding="utf-8")
            args += ["--pr-body", str(root / "body.txt")]
        if assurance_diff is not None:
            (root / "assurance.diff").write_text(assurance_diff, encoding="utf-8")
            args += ["--assurance-diff", str(root / "assurance.diff")]
        if base_adoption is not None:
            write_yaml(root / "base-adoption.yaml", base_adoption)
            args += ["--base-adoption", str(root / "base-adoption.yaml")]
        # The register policy diff needs both roots: the base registers are
        # materialized under --base-registers-root at the BASE declaration's
        # paths, the head registers under --project-root at the HEAD ones
        # (both fixtures use the default assurance/ layout).
        if base_registers is not None:
            base_root = root / "base-root"
            for kind, document in base_registers.items():
                write_yaml(base_root / REGISTER_FILES[kind], document)
            args += ["--base-registers-root", str(base_root)]
        if head_registers is not None:
            head_root = root / "head-root"
            for kind, document in head_registers.items():
                write_yaml(head_root / REGISTER_FILES[kind], document)
            args += ["--project-root", str(head_root)]
        if strict:
            args.append("--strict")
        return run_validator(args)


# ---------------------------------------------------------------------------
# 1. self-check
# ---------------------------------------------------------------------------


class TestSelfCheck(ValidatorTestCase):
    def test_self_check_passes_on_repository(self):
        code, out = run_validator(["self-check", "--repo-root", str(REPO_ROOT)])
        self.assertEqual(code, 0, out)
        self.assertNotIn("ERROR:", out)


# ---------------------------------------------------------------------------
# 2. adopter baseline
# ---------------------------------------------------------------------------


class TestAdopterBaseline(ValidatorTestCase):
    def test_minimal_valid_split_core_adoption_passes(self):
        code, out = self.run_split(baseline_adoption(), baseline_registers())
        self.assertEqual(code, 0, out)
        self.assertIn("adoption file validates against adoption.schema.json", out)
        self.assertNotIn("ERROR:", out)


# ---------------------------------------------------------------------------
# 3. adopter placeholder strictness
# ---------------------------------------------------------------------------


class TestAdopterPlaceholders(ValidatorTestCase):
    def test_placeholder_in_adoption_errors_even_at_draft(self):
        adoption = baseline_adoption()
        adoption["project"]["human_owner"] = "REPLACE_WITH_OWNER_NAME"
        code, out = self.run_split(adoption, baseline_registers())
        self.assertEqual(code, 1, out)
        self.assertIn("unfilled placeholder", out)

    def register_with_placeholder(self):
        registers = baseline_registers()
        registers["residuals"]["residuals"][0]["owner"] = "REPLACE_WITH_OWNER_NAME"
        return registers

    def test_placeholder_in_register_passes_at_draft(self):
        code, out = self.run_split(baseline_adoption(), self.register_with_placeholder())
        self.assertEqual(code, 0, out)

    def test_placeholder_in_register_fails_at_human_reviewed(self):
        adoption = baseline_adoption()
        adoption["adoption_stage"] = "HUMAN_REVIEWED"
        adoption["human_review"] = human_review_block()
        code, out = self.run_split(adoption, self.register_with_placeholder())
        self.assertEqual(code, 1, out)
        self.assertIn("stage HUMAN_REVIEWED: unfilled placeholder", out)


# ---------------------------------------------------------------------------
# 4. HUMAN_REVIEWED stage
# ---------------------------------------------------------------------------


class TestHumanReviewedStage(ValidatorTestCase):
    def test_missing_human_review_block_fails(self):
        adoption = baseline_adoption()
        adoption["adoption_stage"] = "HUMAN_REVIEWED"
        code, out = self.run_split(adoption, baseline_registers())
        self.assertEqual(code, 1, out)
        self.assertIn("human_review block is missing", out)

    def test_complete_human_review_block_passes(self):
        adoption = baseline_adoption()
        adoption["adoption_stage"] = "HUMAN_REVIEWED"
        adoption["human_review"] = human_review_block()
        code, out = self.run_split(adoption, baseline_registers())
        self.assertEqual(code, 0, out)
        self.assertIn("stage HUMAN_REVIEWED: requirements satisfied", out)


# ---------------------------------------------------------------------------
# 5 and 6. CONFORMANT stage (baseline, single mutations, --ignore-stage)
# ---------------------------------------------------------------------------


class TestConformantStage(ValidatorTestCase):
    def run_mutated(self, mutate, *extra):
        adoption, registers = conformant_fixture()
        mutate(adoption, registers)
        return self.run_split(adoption, registers, *extra)

    def test_conformant_baseline_passes(self):
        adoption, registers = conformant_fixture()
        code, out = self.run_split(adoption, registers)
        self.assertEqual(code, 0, out)
        self.assertIn("stage CONFORMANT: requirements satisfied", out)

    def test_open_critical_residual_fails(self):
        def mutate(adoption, registers):
            registers["residuals"]["residuals"][0]["status"] = "OPEN"

        code, out = self.run_mutated(mutate)
        self.assertEqual(code, 1, out)
        self.assertIn("stage CONFORMANT: residual RES-CORE-001 is OPEN", out)

    def test_contradicted_claim_fails(self):
        def mutate(adoption, registers):
            registers["claims"]["claims"][0]["status"] = "CONTRADICTED"

        code, out = self.run_mutated(mutate)
        self.assertEqual(code, 1, out)
        self.assertIn("stage CONFORMANT: claim CLAIM-CORE-001 is CONTRADICTED", out)

    def test_contradicted_critical_invariant_fails(self):
        def mutate(adoption, registers):
            registers["invariants"]["invariants"][0]["status"] = "CONTRADICTED"

        code, out = self.run_mutated(mutate)
        self.assertEqual(code, 1, out)
        self.assertIn(
            "stage CONFORMANT: critical invariant INV-CORE-001 is CONTRADICTED", out
        )

    def test_verified_critical_invariant_empty_evidence_fails(self):
        def mutate(adoption, registers):
            registers["invariants"]["invariants"][0]["evidence"] = []

        code, out = self.run_mutated(mutate)
        self.assertEqual(code, 1, out)
        self.assertIn("stage CONFORMANT", out)
        self.assertIn("is VERIFIED but its evidence list is empty", out)

    def test_restricted_disclosure_entry_fails(self):
        def mutate(adoption, registers):
            registers["defeaters"]["defeaters"][0]["disclosure"] = "RESTRICTED"

        code, out = self.run_mutated(mutate)
        self.assertEqual(code, 1, out)
        self.assertIn(
            "stage CONFORMANT: defeaters entry DEF-CORE-001 has disclosure RESTRICTED",
            out,
        )

    def test_missing_approvals_fails(self):
        def mutate(adoption, registers):
            del adoption["human_review"]["approvals"]

        code, out = self.run_mutated(mutate)
        self.assertEqual(code, 1, out)
        self.assertIn(
            "stage CONFORMANT: human_review.approvals needs at least one "
            "attributable entry",
            out,
        )

    def test_empty_review_url_approval_fails(self):
        def mutate(adoption, registers):
            adoption["human_review"]["approvals"][0]["review_url"] = ""

        code, out = self.run_mutated(mutate)
        self.assertEqual(code, 1, out)
        # Not attributable: the stage requirement fails (the adoption schema's
        # minLength violation is also reported, but the stage line must name
        # the rung of the ladder the declaration falls off).
        self.assertIn(
            "stage CONFORMANT: human_review.approvals needs at least one "
            "attributable entry",
            out,
        )

    def test_expired_review_after_fails(self):
        def mutate(adoption, registers):
            registers["residuals"]["residuals"][0]["review_after"] = PAST_DATE

        code, out = self.run_mutated(mutate)
        self.assertEqual(code, 1, out)
        # CONFORMANT elevates passed review_after dates to errors (as if
        # --strict-review-dates) and suppresses the stage OK verdict.
        self.assertIn(f"review_after {PAST_DATE} has passed", out)
        self.assertNotIn("stage CONFORMANT: requirements satisfied", out)

    def test_ignore_stage_passes_structure_only(self):
        # The CONFORMANT-violating fixture (open critical residual) passes
        # once stage enforcement is skipped: structure-only validation.
        def mutate(adoption, registers):
            registers["residuals"]["residuals"][0]["status"] = "OPEN"

        code, out = self.run_mutated(mutate, "--ignore-stage")
        self.assertEqual(code, 0, out)
        self.assertNotIn("stage CONFORMANT", out)


# ---------------------------------------------------------------------------
# 14. --repo-visibility at stage CONFORMANT (RESTRICTED entries)
# ---------------------------------------------------------------------------


class TestConformantRepoVisibility(ValidatorTestCase):
    """The CONFORMANT disclosure rule is visibility-aware: RESTRICTED
    entries are permitted (warning only) in a declared private repository,
    errors when public, and conservatively errors when the visibility is
    undeclared — with a hint naming the flag."""

    def run_restricted(self, *extra):
        adoption, registers = conformant_fixture()
        registers["defeaters"]["defeaters"][0]["disclosure"] = "RESTRICTED"
        return self.run_split(adoption, registers, *extra)

    def test_private_visibility_keeps_restricted_entry_a_warning(self):
        code, out = self.run_restricted("--repo-visibility", "private")
        self.assertEqual(code, 0, out)
        # No stage CONFORMANT disclosure error; the stage verdict holds.
        self.assertNotIn("stage CONFORMANT: defeaters entry", out)
        self.assertIn("stage CONFORMANT: requirements satisfied", out)
        # The standing structural warning remains at every stage.
        self.assertIn("WARN:", out)
        self.assertIn("verify this file is not public", out)

    def test_public_visibility_makes_restricted_entry_an_error(self):
        code, out = self.run_restricted("--repo-visibility", "public")
        self.assertEqual(code, 1, out)
        self.assertIn(
            "stage CONFORMANT: defeaters entry DEF-CORE-001 has disclosure "
            "RESTRICTED",
            out,
        )
        # A declared public repository gets no "declare it private" hint.
        self.assertNotIn("--repo-visibility private", out)

    def test_unknown_visibility_errors_and_names_the_flag(self):
        code, out = self.run_restricted()
        self.assertEqual(code, 1, out)
        self.assertIn(
            "stage CONFORMANT: defeaters entry DEF-CORE-001 has disclosure "
            "RESTRICTED",
            out,
        )
        self.assertIn("--repo-visibility private", out)


# ---------------------------------------------------------------------------
# 15. empty-register obligations
# ---------------------------------------------------------------------------


class TestRegisterObligations(ValidatorTestCase):
    """A register a profile mandates must carry at least one entry: a
    present-but-empty file is a vacuous pass and fails validation."""

    def test_empty_residuals_register_core_profile_fails(self):
        registers = baseline_registers()
        registers["residuals"]["residuals"] = []
        code, out = self.run_split(baseline_adoption(), registers)
        self.assertEqual(code, 1, out)
        self.assertIn("residuals register is empty", out)

    def test_empty_invariants_register_core_profile_fails(self):
        registers = baseline_registers()
        registers["invariants"]["invariants"] = []
        code, out = self.run_split(baseline_adoption(), registers)
        self.assertEqual(code, 1, out)
        self.assertIn("invariants register is empty", out)

    def test_missing_invariants_register_core_profile_fails(self):
        # A split `core` adopter with no invariants file at all — the register
        # is an obligation from `core`, not only from `service` (PROFILE §6.1).
        registers = {"residuals": {"version": 1, "residuals": [baseline_residual()]}}
        code, out = self.run_split(baseline_adoption(), registers)
        self.assertEqual(code, 1, out)
        self.assertIn("INVARIANTS.yaml missing", out)

    def test_empty_invariants_register_service_profile_fails(self):
        adoption = baseline_adoption()
        adoption["profiles"] = ["service"]
        registers = baseline_registers()
        registers["invariants"] = {"version": 1, "invariants": []}
        root = self.make_tmp()
        adoption_path = build_split_project(root, adoption, registers)
        # Profile 'service' also requires a threat model file.
        (root / "assurance" / "THREAT_MODEL.md").write_text(
            "# Threat model\n", encoding="utf-8"
        )
        code, out = self.run_adopter(root, adoption_path)
        self.assertEqual(code, 1, out)
        self.assertIn("register is empty", out)
        self.assertIn("invariants register is empty", out)

    def test_empty_claims_register_trust_critical_profile_fails(self):
        adoption = baseline_adoption()
        adoption["profiles"] = ["trust-critical"]
        registers = baseline_registers()
        registers["claims"] = {"version": 1, "claims": []}
        code, out = self.run_split(adoption, registers)
        self.assertEqual(code, 1, out)
        self.assertIn("register is empty", out)
        self.assertIn("claims register is empty", out)

    def test_archived_only_adoption_exempt_from_invariants_and_residuals(self):
        # An archived-only adopter (PROFILE.md section 6.6) is exempt from the
        # invariant, residual, and system obligations — pins the `any(profile
        # != "archived")` scoping so a mis-guard that demanded them everywhere
        # would be caught.
        adoption = baseline_adoption()
        adoption["profiles"] = ["archived"]
        code, out = self.run_split(adoption, {})
        self.assertEqual(code, 0, out)
        self.assertNotIn("ERROR:", out)
        self.assertNotIn("register is empty", out)


# ---------------------------------------------------------------------------
# 16. schema hardening (non-empty strings in the registers)
# ---------------------------------------------------------------------------


def hardening_invariant():
    """A schema-valid, semantically quiet invariant entry to mutate."""
    return {
        "id": "INV-CORE-001",
        "title": "Example invariant",
        "statement": "The example property always holds",
        "severity": "medium",
        "scope": "example scope",
        "status": "INFERRED",
        "disclosure": "PUBLIC",
        "owner": "Alice Example",
    }


class TestSchemaHardening(ValidatorTestCase):
    def run_invariant(self, entry):
        registers = baseline_registers()
        registers["invariants"] = {"version": 1, "invariants": [entry]}
        return self.run_split(baseline_adoption(), registers)

    def test_empty_owner_string_fails_schema(self):
        entry = hardening_invariant()
        entry["owner"] = ""
        code, out = self.run_invariant(entry)
        self.assertEqual(code, 1, out)
        self.assertIn("$.invariants[0].owner", out)

    def test_empty_enforcement_item_fails_schema(self):
        entry = hardening_invariant()
        entry["enforcement"] = [""]
        code, out = self.run_invariant(entry)
        self.assertEqual(code, 1, out)
        self.assertIn("$.invariants[0].enforcement[0]", out)

    def test_empty_defeater_statement_fails_schema(self):
        # ADOPTION.md section 3.6 names `statement` among the hardened
        # semantic fields; the defeaters schema must enforce it too.
        registers = baseline_registers()
        registers["defeaters"] = {
            "version": 1,
            "defeaters": [
                {
                    "id": "DEF-CORE-001",
                    "statement": "   ",
                    "status": "OPEN",
                    "disclosure": "PUBLIC",
                    "owner": "Alice Example",
                }
            ],
        }
        code, out = self.run_split(baseline_adoption(), registers)
        self.assertEqual(code, 1, out)
        self.assertIn("$.defeaters[0].statement", out)

    def test_whitespace_accepted_by_on_accepted_critical_residual_fails(self):
        residual = {
            "id": "RES-CORE-001",
            "summary": "Accepted critical residual",
            "impact": "critical",
            "uncertainty": "low",
            "status": "ACCEPTED",
            "disclosure": "PUBLIC",
            "owner": "Alice Example",
            "acceptance_rationale": "Cost of mitigation exceeds exposure",
            "accepted_by": "   ",
            "accepted_at": "2026-01-01",
        }
        registers = baseline_registers()
        registers["residuals"]["residuals"] = [residual]
        code, out = self.run_split(baseline_adoption(), registers)
        self.assertEqual(code, 1, out)
        self.assertIn("accepted_by", out)


# ---------------------------------------------------------------------------
# 9. lite layout
# ---------------------------------------------------------------------------


class TestLiteLayout(ValidatorTestCase):
    def test_valid_lite_fixture_passes(self):
        code, out = self.run_lite(baseline_lite_adoption(), baseline_lite_assurance())
        self.assertEqual(code, 0, out)
        self.assertIn("layout 'lite' is declared with core-only profiles", out)
        self.assertNotIn("ERROR:", out)

    def test_top_level_typo_key_fails(self):
        assurance = baseline_lite_assurance()
        assurance["invarients"] = []
        code, out = self.run_lite(baseline_lite_adoption(), assurance)
        self.assertEqual(code, 1, out)
        self.assertIn("invarients", out)

    def test_empty_purpose_fails(self):
        assurance = baseline_lite_assurance()
        assurance["purpose"] = ""
        code, out = self.run_lite(baseline_lite_adoption(), assurance)
        self.assertEqual(code, 1, out)
        self.assertIn("purpose", out)

    def test_missing_invariants_section_fails(self):
        # `invariants` is required in the lite envelope from `core` (an absent
        # section is caught by the schema, not the emptiness obligation).
        assurance = baseline_lite_assurance()
        del assurance["invariants"]
        code, out = self.run_lite(baseline_lite_adoption(), assurance)
        self.assertEqual(code, 1, out)
        self.assertIn("'invariants' is a required property", out)

    def test_empty_invariants_section_fails(self):
        assurance = baseline_lite_assurance()
        assurance["invariants"] = []
        code, out = self.run_lite(baseline_lite_adoption(), assurance)
        self.assertEqual(code, 1, out)
        self.assertIn("invariants register is empty", out)

    def test_profile_beyond_core_fails(self):
        adoption = baseline_lite_adoption()
        adoption["profiles"] = ["core", "service"]
        code, out = self.run_lite(adoption, baseline_lite_assurance())
        self.assertEqual(code, 1, out)
        self.assertIn("layout 'lite' supports only the core profile", out)

    def test_archived_profile_with_lite_fails(self):
        # Lite is core-only: `archived` (like any non-core profile) must use
        # the split layout — the lite schema's required fields are shaped for
        # core, not archived's PROFILE.md section 6.6 obligations.
        adoption = baseline_lite_adoption()
        adoption["profiles"] = ["archived"]
        code, out = self.run_lite(adoption, baseline_lite_assurance())
        self.assertEqual(code, 1, out)
        self.assertIn("layout 'lite' supports only the core profile", out)

    def test_lite_templates_use_detectable_placeholder_sentinels(self):
        # Every fill-in field in the shipped lite templates must be a
        # REPLACE_WITH_ sentinel, so an adopter who leaves one is caught at
        # HUMAN_REVIEWED. A bare "Replace with ..." would pass that check
        # silently (it is not a REPLACE_WITH_ token).
        for name in ("assurance.minimal.yaml", "assurance.yaml"):
            text = (REPO_ROOT / "templates" / name).read_text(encoding="utf-8")
            self.assertNotIn("Replace with ", text, name)

    def test_default_public_assurance_root_warns_but_passes(self):
        adoption = baseline_lite_adoption()
        adoption["security"] = {"public_assurance_root": "assurance"}
        code, out = self.run_lite(adoption, baseline_lite_assurance())
        self.assertEqual(code, 0, out)
        self.assertIn("WARN:", out)
        self.assertIn("public_assurance_root is 'assurance'", out)


# ---------------------------------------------------------------------------
# 7 and 10. drift impact routing
# ---------------------------------------------------------------------------


def drift_adoption(components=True):
    adoption = baseline_adoption()
    if components:
        adoption["components"] = {
            "api": {"paths": ["src/api/**"], "invariants": ["INV-CORE-001"]}
        }
    return adoption


class TestDriftRouting(ValidatorTestCase):
    def test_no_components_is_not_configured(self):
        code, out = self.run_drift(drift_adoption(components=False), changed=["src/x.py"])
        self.assertEqual(code, 0, out)
        self.assertIn("impact routing not configured", out)

    def test_assurance_diff_referencing_invariant_satisfies(self):
        code, out = self.run_drift(
            drift_adoption(),
            changed=["src/api/handler.py"],
            assurance_diff="+  evidence updated for INV-CORE-001\n",
        )
        self.assertEqual(code, 0, out)
        self.assertIn("assurance update references INV-CORE-001", out)

    def test_assurance_diff_context_line_does_not_satisfy(self):
        # The component's ID appearing only on an unchanged context line of
        # the unified diff (an adjacent entry was edited) is not an update
        # of that invariant.
        code, out = self.run_drift(
            drift_adoption(),
            changed=["src/api/handler.py"],
            assurance_diff=(
                "   - id: INV-CORE-001\n"
                "+  - id: INV-CORE-002\n"
                "+    statement: unrelated neighbour updated\n"
            ),
        )
        self.assertEqual(code, 0, out)
        self.assertIn("without an assurance update", out)

    def test_assurance_diff_deletion_only_does_not_satisfy(self):
        code, out = self.run_drift(
            drift_adoption(),
            changed=["src/api/handler.py"],
            assurance_diff="-  - id: INV-CORE-001\n-    statement: removed\n",
        )
        self.assertEqual(code, 0, out)
        self.assertIn("without an assurance update", out)

    def test_assurance_diff_nested_longer_id_does_not_satisfy(self):
        # INV-CORE-001-EXT-002 is a valid ID that contains INV-CORE-001 as a
        # substring; token-boundary matching must not let it satisfy.
        code, out = self.run_drift(
            drift_adoption(),
            changed=["src/api/handler.py"],
            assurance_diff="+  - id: INV-CORE-001-EXT-002\n",
        )
        self.assertEqual(code, 0, out)
        self.assertIn("without an assurance update", out)

    def test_assurance_diff_without_reference_warns(self):
        code, out = self.run_drift(
            drift_adoption(),
            changed=["src/api/handler.py"],
            assurance_diff="+  unrelated edit\n",
        )
        self.assertEqual(code, 0, out)
        self.assertIn("WARN:", out)
        self.assertIn("without an assurance update", out)

    def test_assurance_diff_without_reference_strict_fails(self):
        code, out = self.run_drift(
            drift_adoption(),
            changed=["src/api/handler.py"],
            assurance_diff="+  unrelated edit\n",
            strict=True,
        )
        self.assertEqual(code, 1, out)
        self.assertIn("ERROR:", out)
        self.assertIn("without an assurance update", out)

    def test_coarse_fallback_assurance_change_satisfies(self):
        # Without --assurance-diff, any changed file under assurance/ is the
        # coarse standalone fallback signal.
        code, out = self.run_drift(
            drift_adoption(),
            changed=["src/api/handler.py", "assurance/INVARIANTS.yaml"],
        )
        self.assertEqual(code, 0, out)
        self.assertIn("assurance artifacts updated in the same change", out)

    def test_pr_body_mentioning_all_invariants_satisfies(self):
        code, out = self.run_drift(
            drift_adoption(),
            changed=["src/api/handler.py"],
            body="Refactors the handler; covered by INV-CORE-001.\n",
        )
        self.assertEqual(code, 0, out)
        self.assertIn("PR description mentions INV-CORE-001", out)

    def test_no_impact_without_reason_does_not_satisfy(self):
        code, out = self.run_drift(
            drift_adoption(),
            changed=["src/api/handler.py"],
            body="Assurance impact: none\n",
            strict=True,
        )
        self.assertEqual(code, 1, out)
        self.assertIn("'Reason:' line is missing", out)

    def test_no_impact_with_reason_satisfies(self):
        code, out = self.run_drift(
            drift_adoption(),
            changed=["src/api/handler.py"],
            body="Assurance impact: none\nReason: comment-only change\n",
        )
        self.assertEqual(code, 0, out)
        self.assertIn("declares 'Assurance impact: none' with a reason", out)

    def test_rename_source_path_triggers_component(self):
        # Rename semantics are computed by the CI caller, which lists both the
        # rename source and the destination in the changed-files list. The
        # validator treats each listed path independently, so a rename OUT of
        # a mapped component still routes: the source path matches the glob.
        code, out = self.run_drift(
            drift_adoption(),
            changed=["src/api/old_name.py", "src/relocated/new_name.py"],
            body="Move covered by INV-CORE-001.\n",
        )
        self.assertEqual(code, 0, out)
        self.assertIn("component 'api' touched (1 changed file)", out)


# ---------------------------------------------------------------------------
# 8. drift policy regression (--base-adoption)
# ---------------------------------------------------------------------------


def regression_base_adoption():
    adoption = baseline_adoption()
    adoption["adoption_stage"] = "CONFORMANT"
    adoption["human_review"] = human_review_block()
    adoption["components"] = {
        "api": {
            "paths": ["src/api/**", "src/legacy/**"],
            "invariants": ["INV-CORE-001", "INV-CORE-002"],
        }
    }
    return adoption


class TestDriftPolicyRegression(ValidatorTestCase):
    def run_regression(self, mutate_head, body=None):
        base = regression_base_adoption()
        head = copy.deepcopy(base)
        mutate_head(head)
        return self.run_drift(head, changed=(), body=body, base_adoption=base)

    def test_stage_downgrade_fails(self):
        def mutate(head):
            head["adoption_stage"] = "DRAFT"

        code, out = self.run_regression(mutate)
        self.assertEqual(code, 1, out)
        self.assertIn("assurance policy weakened", out)
        self.assertIn("adoption_stage downgraded from CONFORMANT to DRAFT", out)

    def test_upstream_commit_change_fails(self):
        def mutate(head):
            head["upstream"]["commit"] = "1" * 40

        code, out = self.run_regression(mutate)
        self.assertEqual(code, 1, out)
        # Pin moves carry their own prefix (not a weakening per se, but they
        # demand the same explicit acknowledgment).
        self.assertIn("upstream pin changed", out)
        self.assertIn("upstream.commit changed", out)

    def test_component_removed_fails(self):
        def mutate(head):
            del head["components"]

        code, out = self.run_regression(mutate)
        self.assertEqual(code, 1, out)
        self.assertIn("component 'api' removed", out)

    def test_component_path_glob_removed_fails(self):
        def mutate(head):
            head["components"]["api"]["paths"] = ["src/api/**"]

        code, out = self.run_regression(mutate)
        self.assertEqual(code, 1, out)
        self.assertIn("path glob(s) removed: src/legacy/**", out)

    def test_component_invariant_removed_fails(self):
        def mutate(head):
            head["components"]["api"]["invariants"] = ["INV-CORE-001"]

        code, out = self.run_regression(mutate)
        self.assertEqual(code, 1, out)
        self.assertIn("invariant(s) removed: INV-CORE-002", out)

    def test_acknowledged_policy_change_draft_base_passes_with_warning(self):
        # Stage-proportional acknowledgment: when the BASE declaration is
        # stage DRAFT (absent here), 'Assurance policy change:' downgrades
        # findings to warnings.
        base = baseline_adoption()
        base["components"] = {
            "api": {
                "paths": ["src/api/**", "src/legacy/**"],
                "invariants": ["INV-CORE-001"],
            }
        }
        head = copy.deepcopy(base)
        head["components"]["api"]["paths"] = ["src/api/**"]
        code, out = self.run_drift(
            head,
            changed=(),
            body="Assurance policy change: deliberate narrowing during restructure\n",
            base_adoption=base,
        )
        self.assertEqual(code, 0, out)
        self.assertIn("WARN:", out)
        self.assertIn("acknowledged by 'Assurance policy change:'", out)
        self.assertNotIn("ERROR:", out)

    def test_acknowledged_policy_change_conformant_base_still_fails(self):
        # From stage HUMAN_REVIEWED on, findings stay errors even when
        # acknowledged: the red check is the honest signal, and merging over
        # it is the human owner's recorded decision.
        def mutate(head):
            head["adoption_stage"] = "DRAFT"

        code, out = self.run_regression(
            mutate, body="Assurance policy change: deliberate reset during restructure\n"
        )
        self.assertEqual(code, 1, out)
        self.assertIn(
            "acknowledged, but the base declaration is stage CONFORMANT", out
        )

    def test_no_changes_reports_no_regression(self):
        code, out = self.run_regression(lambda head: None)
        self.assertEqual(code, 0, out)
        self.assertIn("no assurance policy regression", out)

    def test_human_owner_change_fails(self):
        def mutate(head):
            head["project"]["human_owner"] = "Bob Example"

        code, out = self.run_regression(mutate)
        self.assertEqual(code, 1, out)
        self.assertIn("assurance policy weakened", out)
        self.assertIn(
            "project.human_owner changed from 'Alice Example' to 'Bob Example'", out
        )

    def test_human_review_reviewer_change_fails(self):
        # The review provenance the declared stage rests on: rewriting who
        # reviewed, or where the durable record lives, is a policy change.
        def mutate(head):
            head["human_review"] = {
                "date": "2026-01-01",
                "reviewer": "Mallory",
                "record": "docs/reviews/2026-01-01.md",
            }

        code, out = self.run_regression(mutate)
        self.assertEqual(code, 1, out)
        self.assertIn(
            "human_review.reviewer changed from 'Alice Example' to 'Mallory'", out
        )

    def test_human_review_record_removal_fails(self):
        def mutate(head):
            head["human_review"].pop("record")

        code, out = self.run_regression(mutate)
        self.assertEqual(code, 1, out)
        self.assertIn(
            "human_review.record changed from 'docs/reviews/2026-01-01.md' "
            "to None",
            out,
        )

    def test_human_review_date_advanced_not_flagged(self):
        # Advancing the review date is the normal re-review act, not a
        # policy change — deliberately not compared.
        def mutate(head):
            head["human_review"]["date"] = "2026-06-01"

        code, out = self.run_regression(mutate)
        self.assertEqual(code, 0, out)
        self.assertIn("no assurance policy regression", out)

    def test_paths_invariants_change_fails(self):
        def mutate(head):
            head["paths"] = {"invariants": "assurance/OTHER.yaml"}

        code, out = self.run_regression(mutate)
        self.assertEqual(code, 1, out)
        self.assertIn("assurance policy weakened", out)
        self.assertIn("paths.invariants changed", out)

    def test_public_assurance_root_change_fails(self):
        def mutate(head):
            head["security"] = {"public_assurance_root": "elsewhere"}

        code, out = self.run_regression(mutate)
        self.assertEqual(code, 1, out)
        self.assertIn("assurance policy weakened", out)
        self.assertIn("security.public_assurance_root changed", out)


# ---------------------------------------------------------------------------
# 13. drift register policy diff (--base-registers-root / --project-root)
# ---------------------------------------------------------------------------


def drift_register_fixture():
    """Base-side registers for the stable-ID policy diff.

    One critical VERIFIED invariant (INTENDED, with enforcement), one
    low-severity invariant with enforcement (whose shrinkage must NOT be
    flagged), one INDEPENDENTLY_VERIFIABLE claim, one critical residual.
    The drift register diff loads these without schema validation, but the
    entries are kept schema-valid anyway.
    """
    return {
        "claims": {
            "version": 1,
            "claims": [
                {
                    "id": "CLAIM-CORE-001",
                    "text": "Example claim",
                    "scope": "example scope",
                    "proof_tier": "INDEPENDENTLY_VERIFIABLE",
                    "status": "VERIFIED",
                    "disclosure": "PUBLIC",
                    "owner": "Alice Example",
                }
            ],
        },
        "invariants": {
            "version": 1,
            "invariants": [
                {
                    "id": "INV-CORE-001",
                    "title": "Critical invariant",
                    "statement": "The critical property always holds",
                    "severity": "critical",
                    "scope": "example scope",
                    "status": "VERIFIED",
                    "disclosure": "PUBLIC",
                    "owner": "Alice Example",
                    "intent": {
                        "classification": "INTENDED",
                        "authority": "docs/adr/001.md",
                    },
                    "enforcement": ["ci guard"],
                    "verification": ["tests/test_example.py"],
                    "evidence": ["evidence/run-1.txt"],
                },
                {
                    "id": "INV-CORE-002",
                    "title": "Low invariant",
                    "statement": "The low-severity property holds",
                    "severity": "low",
                    "scope": "example scope",
                    "status": "INFERRED",
                    "disclosure": "PUBLIC",
                    "owner": "Alice Example",
                    "enforcement": ["low guard"],
                },
            ],
        },
        "residuals": {
            "version": 1,
            "residuals": [
                {
                    "id": "RES-CORE-001",
                    "summary": "Example critical residual",
                    "impact": "critical",
                    "uncertainty": "low",
                    "status": "OPEN",
                    "disclosure": "PUBLIC",
                    "owner": "Alice Example",
                }
            ],
        },
    }


def drift_defeaters_document(status="OPEN", **extra):
    """A one-entry defeaters register document (kept schema-valid).

    The base fixture has no defeaters register, so defeater-closure and
    defeaters-register-removal tests add one via ``mutate_base``.
    """
    entry = {
        "id": "DEF-CORE-001",
        "statement": "The guard may be bypassed on forks",
        "status": status,
        "disclosure": "PUBLIC",
        "owner": "Alice Example",
    }
    entry.update(extra)
    return {"version": 1, "defeaters": [entry]}


class TestDriftRegisterPolicyDiff(ValidatorTestCase):
    """Stable-ID register diff: each test applies one mutation between the
    base and head register files. The base adoption is stage DRAFT (absent)
    and no acknowledgment is given, so findings are errors — except in the
    acknowledgment test, where the DRAFT base downgrades them to warnings."""

    def run_register_diff(
        self, mutate_head, body=None, mutate_base=None, base_stage=None
    ):
        base = baseline_adoption()
        if base_stage is not None:
            base["adoption_stage"] = base_stage
        head = copy.deepcopy(base)
        base_registers = drift_register_fixture()
        if mutate_base is not None:
            mutate_base(base_registers)
        # Head starts identical to the (possibly base-mutated) registers, then
        # the head mutation is applied — so a test can set the base state via
        # mutate_base and the head-only change via mutate_head.
        head_registers = copy.deepcopy(base_registers)
        mutate_head(head_registers)
        return self.run_drift(
            head,
            changed=(),
            body=body,
            base_adoption=base,
            base_registers=base_registers,
            head_registers=head_registers,
        )

    def test_unchanged_registers_report_no_regression(self):
        code, out = self.run_register_diff(lambda head: None)
        self.assertEqual(code, 0, out)
        self.assertIn("no assurance policy regression", out)

    def test_scalar_basis_field_does_not_crash(self):
        # The diff loads registers without schema validation, so a claim's
        # evidence/limitations may hold a non-list scalar (e.g. `evidence: 42`
        # or a YAML-coerced bool). Iterating it must not crash the gate.
        def set_scalar(registers):
            registers["claims"]["claims"][0]["evidence"] = 42
            registers["claims"]["claims"][0]["limitations"] = True

        code, out = self.run_register_diff(lambda head: None, mutate_base=set_scalar)
        self.assertNotIn("Traceback", out)
        # base == head here, so no basis removal is reported and the run passes.
        self.assertEqual(code, 0, out)

    def test_list_basis_field_replaced_by_scalar_is_removal(self):
        # A list of evidence in the base replaced by a scalar in the head
        # removes the basis entirely — reported, not crashed.
        def set_list(registers):
            registers["claims"]["claims"][0]["evidence"] = ["evidence/proof.json"]

        def to_scalar(head):
            head["claims"]["claims"][0]["evidence"] = 0

        code, out = self.run_register_diff(to_scalar, mutate_base=set_list)
        self.assertEqual(code, 1, out)
        self.assertIn("evidence item(s) removed: evidence/proof.json", out)

    def test_dot_slash_register_path_still_compared(self):
        # A register declared with a './'-prefixed path is read by the
        # validator; the workflow's base-materialization must accept the same
        # paths, or a deletion under that path would be silently missed. The
        # validator side is exercised here: with paths.claims = ./assurance/...
        # the base claim's deletion is still detected.
        base = baseline_adoption()
        base["paths"] = {"claims": "./assurance/CLAIMS.yaml"}
        head = copy.deepcopy(base)
        base_registers = drift_register_fixture()
        head_registers = copy.deepcopy(base_registers)
        head_registers["claims"]["claims"] = []
        code, out = self.run_drift(
            head,
            changed=(),
            base_adoption=base,
            base_registers=base_registers,
            head_registers=head_registers,
        )
        self.assertEqual(code, 1, out)
        self.assertIn("claims entry CLAIM-CORE-001 deleted", out)

    def test_entry_deleted_fails(self):
        def mutate(head):
            head["residuals"]["residuals"] = []

        code, out = self.run_register_diff(mutate)
        self.assertEqual(code, 1, out)
        self.assertIn("assurance policy weakened", out)
        self.assertIn("residuals entry RES-CORE-001 deleted", out)

    def test_invariant_severity_downgrade_fails(self):
        def mutate(head):
            head["invariants"]["invariants"][0]["severity"] = "low"

        code, out = self.run_register_diff(mutate)
        self.assertEqual(code, 1, out)
        self.assertIn("assurance policy weakened", out)
        self.assertIn("severity downgraded from critical to low", out)

    def test_invariant_status_verified_to_unknown_fails(self):
        def mutate(head):
            head["invariants"]["invariants"][0]["status"] = "UNKNOWN"

        code, out = self.run_register_diff(mutate)
        self.assertEqual(code, 1, out)
        self.assertIn("assurance policy weakened", out)
        self.assertIn("status weakened from VERIFIED to UNKNOWN", out)

    def test_invariant_status_verified_to_contradicted_not_flagged(self):
        # Recording a contradiction is an honesty upgrade, never gated.
        def mutate(head):
            head["invariants"]["invariants"][0]["status"] = "CONTRADICTED"

        code, out = self.run_register_diff(mutate)
        self.assertEqual(code, 0, out)
        self.assertNotIn("assurance policy weakened", out)
        self.assertIn("no assurance policy regression", out)

    def test_invariant_intent_reclassified_fails(self):
        def mutate(head):
            head["invariants"]["invariants"][0]["intent"]["classification"] = "UNKNOWN"

        code, out = self.run_register_diff(mutate)
        self.assertEqual(code, 1, out)
        self.assertIn("assurance policy weakened", out)
        self.assertIn("intent reclassified from INTENDED to UNKNOWN", out)

    def test_enforcement_removed_from_critical_invariant_fails(self):
        def mutate(head):
            head["invariants"]["invariants"][0]["enforcement"] = []

        code, out = self.run_register_diff(mutate)
        self.assertEqual(code, 1, out)
        self.assertIn("assurance policy weakened", out)
        self.assertIn("enforcement item(s) removed: ci guard", out)

    def test_enforcement_removed_from_low_invariant_not_flagged(self):
        def mutate(head):
            head["invariants"]["invariants"][1]["enforcement"] = []

        code, out = self.run_register_diff(mutate)
        self.assertEqual(code, 0, out)
        self.assertNotIn("assurance policy weakened", out)
        self.assertIn("no assurance policy regression", out)

    def test_claim_proof_tier_downgrade_fails(self):
        def mutate(head):
            head["claims"]["claims"][0]["proof_tier"] = "OPERATOR_ATTESTED"

        code, out = self.run_register_diff(mutate)
        self.assertEqual(code, 1, out)
        self.assertIn("assurance policy weakened", out)
        self.assertIn(
            "proof_tier downgraded from INDEPENDENTLY_VERIFIABLE to "
            "OPERATOR_ATTESTED",
            out,
        )

    def test_residual_impact_downgrade_fails(self):
        def mutate(head):
            head["residuals"]["residuals"][0]["impact"] = "low"

        code, out = self.run_register_diff(mutate)
        self.assertEqual(code, 1, out)
        self.assertIn("assurance policy weakened", out)
        self.assertIn("impact downgraded from critical to low", out)

    def test_acknowledged_register_weakening_draft_base_warns(self):
        # DRAFT base + 'Assurance policy change:' line: the same finding is
        # a warning and the run passes.
        def mutate(head):
            head["residuals"]["residuals"] = []

        code, out = self.run_register_diff(
            mutate, body="Assurance policy change: register cleanup after triage\n"
        )
        self.assertEqual(code, 0, out)
        self.assertIn("WARN:", out)
        self.assertIn("residuals entry RES-CORE-001 deleted", out)
        self.assertIn("acknowledged by 'Assurance policy change:'", out)
        self.assertNotIn("ERROR:", out)

    # -- v0.3.1: whole-register removal (the headline fix) -----------------

    def test_invariants_register_removed_fails(self):
        # base has an invariants register; head omits the key entirely, so no
        # INVARIANTS.yaml is written under the head root and the register
        # loads as absent (not None) — a whole-register removal, not a parse
        # error. An optional register could otherwise be deleted wholesale
        # with no finding.
        def mutate(head):
            del head["invariants"]

        code, out = self.run_register_diff(mutate)
        self.assertEqual(code, 1, out)
        self.assertIn("assurance policy weakened", out)
        self.assertIn("invariants register removed", out)
        # The former entry IDs are listed so the reviewer sees what was lost.
        self.assertIn("INV-CORE-001", out)

    def test_defeaters_register_removed_fails(self):
        # An optional register absent from the base fixture: added on the base
        # only, then removed on the head.
        def add_defeaters(base):
            base["defeaters"] = drift_defeaters_document()

        def mutate(head):
            del head["defeaters"]

        code, out = self.run_register_diff(mutate, mutate_base=add_defeaters)
        self.assertEqual(code, 1, out)
        self.assertIn("assurance policy weakened", out)
        self.assertIn("defeaters register removed", out)
        self.assertIn("DEF-CORE-001", out)

    # -- v0.3.1: unreadable head register fails closed ---------------------

    def test_unreadable_head_register_fails_closed(self):
        # A head register file that exists but cannot be parsed must not pass
        # the policy diff silently: the comparison cannot be trusted, so it is
        # reported as un-comparable. Built manually (mirroring run_drift's
        # layout) because the run_drift helper writes valid YAML — here the
        # head INVARIANTS.yaml is deliberately malformed.
        root = self.make_tmp()
        base = baseline_adoption()
        head = copy.deepcopy(base)
        write_yaml(root / "adoption.yaml", head)
        write_yaml(root / "base-adoption.yaml", base)
        (root / "changed.txt").write_text("", encoding="utf-8")

        base_root = root / "base-root"
        write_yaml(
            base_root / REGISTER_FILES["invariants"],
            drift_register_fixture()["invariants"],
        )
        head_root = root / "head-root"
        head_invariants = head_root / REGISTER_FILES["invariants"]
        head_invariants.parent.mkdir(parents=True, exist_ok=True)
        # Unclosed flow sequence under an empty key: a YAML parse error.
        head_invariants.write_text(":\n  - [unclosed\n", encoding="utf-8")

        code, out = run_validator(
            [
                "drift",
                "--adoption",
                str(root / "adoption.yaml"),
                "--changed-files",
                str(root / "changed.txt"),
                "--pr-body",
                str(root / "missing-body.txt"),
                "--base-adoption",
                str(root / "base-adoption.yaml"),
                "--base-registers-root",
                str(base_root),
                "--project-root",
                str(head_root),
            ]
        )
        self.assertEqual(code, 1, out)
        self.assertIn("cannot be compared", out)
        self.assertIn("unreadable", out)

    # -- v0.3.1: residual closed -------------------------------------------

    def test_residual_open_to_resolved_fails(self):
        def mutate(head):
            residual = head["residuals"]["residuals"][0]
            residual["status"] = "RESOLVED"
            residual["resolution_note"] = "Root cause fixed in the redesign"

        code, out = self.run_register_diff(mutate)
        self.assertEqual(code, 1, out)
        self.assertIn("assurance policy weakened", out)
        self.assertIn("residual RES-CORE-001 closed (OPEN to RESOLVED)", out)

    def test_residual_accepted_to_resolved_fails(self):
        # A high-impact ACCEPTED residual (needs a named acceptance authority
        # and date) closed to RESOLVED is still a closure — it leaves active
        # scrutiny.
        def accept_base(base):
            residual = base["residuals"]["residuals"][0]
            residual["impact"] = "high"
            residual["status"] = "ACCEPTED"
            residual["accepted_by"] = "Alice Example"
            residual["accepted_at"] = "2026-01-01"
            residual["acceptance_rationale"] = "Cost of mitigation exceeds exposure"

        def mutate(head):
            residual = head["residuals"]["residuals"][0]
            residual["status"] = "RESOLVED"
            residual["resolution_note"] = "Fully mitigated in the redesign"
            for field in ("accepted_by", "accepted_at", "acceptance_rationale"):
                residual.pop(field, None)

        code, out = self.run_register_diff(mutate, mutate_base=accept_base)
        self.assertEqual(code, 1, out)
        self.assertIn("assurance policy weakened", out)
        self.assertIn("residual RES-CORE-001 closed (ACCEPTED to RESOLVED)", out)

    def test_residual_resolved_to_open_not_flagged(self):
        # Re-opening a closed residual (RESOLVED -> OPEN) restores scrutiny;
        # it is never a weakening.
        def resolve_base(base):
            residual = base["residuals"]["residuals"][0]
            residual["status"] = "RESOLVED"
            residual["resolution_note"] = "Previously closed"

        def mutate(head):
            residual = head["residuals"]["residuals"][0]
            residual["status"] = "OPEN"
            residual.pop("resolution_note", None)

        code, out = self.run_register_diff(mutate, mutate_base=resolve_base)
        self.assertEqual(code, 0, out)
        self.assertNotIn("residual RES-CORE-001 closed", out)
        self.assertIn("no assurance policy regression", out)

    # -- v0.3.1: defeater closed -------------------------------------------

    def test_defeater_open_to_withdrawn_fails(self):
        def add_defeaters(base):
            base["defeaters"] = drift_defeaters_document()

        def mutate(head):
            defeater = head["defeaters"]["defeaters"][0]
            defeater["status"] = "WITHDRAWN"
            defeater["resolution"] = "No longer applicable after the redesign"

        code, out = self.run_register_diff(mutate, mutate_base=add_defeaters)
        self.assertEqual(code, 1, out)
        self.assertIn("assurance policy weakened", out)
        self.assertIn("defeater DEF-CORE-001 closed (OPEN to WITHDRAWN)", out)

    def test_defeater_open_to_mitigated_fails(self):
        def add_defeaters(base):
            base["defeaters"] = drift_defeaters_document()

        def mutate(head):
            defeater = head["defeaters"]["defeaters"][0]
            defeater["status"] = "MITIGATED"
            defeater["resolution"] = "A guard was added on the fork path"

        code, out = self.run_register_diff(mutate, mutate_base=add_defeaters)
        self.assertEqual(code, 1, out)
        self.assertIn("assurance policy weakened", out)
        self.assertIn("defeater DEF-CORE-001 closed (OPEN to MITIGATED)", out)

    def test_defeater_open_to_resolved_fails(self):
        def add_defeaters(base):
            base["defeaters"] = drift_defeaters_document()

        def mutate(head):
            defeater = head["defeaters"]["defeaters"][0]
            defeater["status"] = "RESOLVED"
            defeater["resolution"] = "The bypass was removed entirely"

        code, out = self.run_register_diff(mutate, mutate_base=add_defeaters)
        self.assertEqual(code, 1, out)
        self.assertIn("assurance policy weakened", out)
        self.assertIn("defeater DEF-CORE-001 closed (OPEN to RESOLVED)", out)

    # -- v0.3.1: recorded CONTRADICTED cleared -----------------------------

    def test_invariant_contradiction_cleared_fails(self):
        # Moving an invariant AWAY from a recorded CONTRADICTED is a reviewed
        # disposition; head is otherwise valid (enforcement/verification/
        # evidence carried over from the fixture).
        def contradict_base(base):
            base["invariants"]["invariants"][0]["status"] = "CONTRADICTED"

        def mutate(head):
            head["invariants"]["invariants"][0]["status"] = "VERIFIED"

        code, out = self.run_register_diff(mutate, mutate_base=contradict_base)
        self.assertEqual(code, 1, out)
        self.assertIn("assurance policy weakened", out)
        self.assertIn(
            "invariant INV-CORE-001 recorded contradiction cleared "
            "(CONTRADICTED to VERIFIED)",
            out,
        )

    def test_claim_contradiction_cleared_fails(self):
        def contradict_base(base):
            base["claims"]["claims"][0]["status"] = "CONTRADICTED"

        def mutate(head):
            head["claims"]["claims"][0]["status"] = "VERIFIED"

        code, out = self.run_register_diff(mutate, mutate_base=contradict_base)
        self.assertEqual(code, 1, out)
        self.assertIn("assurance policy weakened", out)
        self.assertIn(
            "claim CLAIM-CORE-001 recorded contradiction cleared "
            "(CONTRADICTED to VERIFIED)",
            out,
        )

    def test_claim_verified_to_contradicted_not_flagged(self):
        # Recording a contradiction on a claim is an honesty upgrade, never
        # gated (the invariant direction is covered separately above).
        def mutate(head):
            head["claims"]["claims"][0]["status"] = "CONTRADICTED"

        code, out = self.run_register_diff(mutate)
        self.assertEqual(code, 0, out)
        self.assertNotIn("assurance policy weakened", out)
        self.assertIn("no assurance policy regression", out)

    # -- v0.3.1: claim basis removal ---------------------------------------

    def test_claim_basis_items_removed_fails(self):
        # Stripping a claim's evidence, supporting invariants, or stated
        # limitations removes its assurance basis without touching its
        # wording. Each list field is flagged independently.
        def enrich_base(base):
            claim = base["claims"]["claims"][0]
            claim["evidence"] = ["evidence/claim-1.txt"]
            claim["invariants"] = ["INV-CORE-001"]
            claim["limitations"] = ["Only covers the happy path"]

        def mutate(head):
            claim = head["claims"]["claims"][0]
            claim.pop("evidence", None)
            claim.pop("invariants", None)
            claim.pop("limitations", None)

        code, out = self.run_register_diff(mutate, mutate_base=enrich_base)
        self.assertEqual(code, 1, out)
        self.assertIn("assurance policy weakened", out)
        self.assertIn(
            "claim CLAIM-CORE-001: evidence item(s) removed: evidence/claim-1.txt",
            out,
        )
        self.assertIn(
            "claim CLAIM-CORE-001: invariants item(s) removed: INV-CORE-001", out
        )
        self.assertIn(
            "claim CLAIM-CORE-001: limitations item(s) removed: "
            "Only covers the happy path",
            out,
        )

    # -- v0.3.1: stage-proportional interplay for a new finding ------------

    def test_register_removal_draft_base_acknowledged_warns(self):
        # A whole-register removal under a DRAFT base with the acknowledgment
        # line: downgraded to a warning, run passes.
        def mutate(head):
            del head["invariants"]

        code, out = self.run_register_diff(
            mutate,
            body="Assurance policy change: retire the invariants register\n",
        )
        self.assertEqual(code, 0, out)
        self.assertIn("WARN:", out)
        self.assertIn("invariants register removed", out)
        self.assertIn("acknowledged by 'Assurance policy change:'", out)
        self.assertNotIn("ERROR:", out)

    def test_register_removal_human_reviewed_base_still_fails(self):
        # The same removal with the same acknowledgment, but a HUMAN_REVIEWED
        # base: findings stay errors — enforcement is proportional to the
        # stage the base agreed to.
        def mutate(head):
            del head["invariants"]

        code, out = self.run_register_diff(
            mutate,
            body="Assurance policy change: retire the invariants register\n",
            base_stage="HUMAN_REVIEWED",
        )
        self.assertEqual(code, 1, out)
        self.assertIn("invariants register removed", out)
        self.assertIn("the base declaration is stage HUMAN_REVIEWED", out)

    # -- v0.3.2: residual acceptance is a human decision -------------------

    def test_residual_open_to_accepted_fails(self):
        # Accepting a critical residual needs a human decision; the
        # acceptance fields are trivially fabricatable strings, so the
        # transition itself must route through the review gate even when
        # the head entry is formally complete.
        def mutate(head):
            residual = head["residuals"]["residuals"][0]
            residual["status"] = "ACCEPTED"
            residual["accepted_by"] = "Alice Example"
            residual["accepted_at"] = "2026-07-01"
            residual["acceptance_rationale"] = "Cost of mitigation exceeds exposure"

        code, out = self.run_register_diff(mutate)
        self.assertEqual(code, 1, out)
        self.assertIn("assurance policy weakened", out)
        self.assertIn("residual RES-CORE-001 accepted (OPEN to ACCEPTED)", out)

    def test_residual_resolved_to_accepted_fails(self):
        # Reopening lands in ACCEPTED, not OPEN: the un-resolving is fine,
        # but arriving at an acceptance is still an acceptance decision.
        def resolve_base(base):
            residual = base["residuals"]["residuals"][0]
            residual["status"] = "RESOLVED"
            residual["resolution_note"] = "Previously closed"

        def mutate(head):
            residual = head["residuals"]["residuals"][0]
            residual["status"] = "ACCEPTED"
            residual["accepted_by"] = "Alice Example"
            residual["accepted_at"] = "2026-07-01"
            residual["acceptance_rationale"] = "Risk re-accepted after re-triage"

        code, out = self.run_register_diff(mutate, mutate_base=resolve_base)
        self.assertEqual(code, 1, out)
        self.assertIn("residual RES-CORE-001 accepted (RESOLVED to ACCEPTED)", out)

    def test_residual_acceptance_record_rewrite_fails(self):
        # Rewriting who accepted a recorded risk mutates a human decision.
        def accept_base(base):
            residual = base["residuals"]["residuals"][0]
            residual["status"] = "ACCEPTED"
            residual["accepted_by"] = "Alice Example"
            residual["accepted_at"] = "2026-01-01"
            residual["acceptance_rationale"] = "Cost of mitigation exceeds exposure"

        def mutate(head):
            head["residuals"]["residuals"][0]["accepted_by"] = "Mallory"

        code, out = self.run_register_diff(mutate, mutate_base=accept_base)
        self.assertEqual(code, 1, out)
        self.assertIn(
            "residual RES-CORE-001 accepted_by changed from 'Alice Example' "
            "to 'Mallory'",
            out,
        )

    def test_residual_acceptance_record_removal_fails(self):
        def accept_base(base):
            residual = base["residuals"]["residuals"][0]
            residual["status"] = "ACCEPTED"
            residual["accepted_by"] = "Alice Example"
            residual["accepted_at"] = "2026-01-01"
            residual["acceptance_rationale"] = "Cost of mitigation exceeds exposure"

        def mutate(head):
            head["residuals"]["residuals"][0].pop("acceptance_rationale")

        code, out = self.run_register_diff(mutate, mutate_base=accept_base)
        self.assertEqual(code, 1, out)
        self.assertIn(
            "residual RES-CORE-001 acceptance_rationale changed from "
            "'Cost of mitigation exceeds exposure' to None",
            out,
        )

    # -- v0.3.2: defeater terminal dispositions ----------------------------

    def test_defeater_mitigated_to_resolved_fails(self):
        # MITIGATED = risk reduced but not eliminated; RESOLVED asserts it
        # is gone. Upgrading the disposition is not a lateral move inside
        # one closed class.
        def add_defeaters(base):
            base["defeaters"] = drift_defeaters_document(
                status="MITIGATED", resolution="A guard was added on the fork path"
            )

        def mutate(head):
            defeater = head["defeaters"]["defeaters"][0]
            defeater["status"] = "RESOLVED"
            defeater["resolution"] = "The bypass was removed entirely"

        code, out = self.run_register_diff(mutate, mutate_base=add_defeaters)
        self.assertEqual(code, 1, out)
        self.assertIn(
            "defeater DEF-CORE-001 disposition changed (MITIGATED to RESOLVED)", out
        )

    def test_defeater_mitigated_to_withdrawn_fails(self):
        def add_defeaters(base):
            base["defeaters"] = drift_defeaters_document(
                status="MITIGATED", resolution="A guard was added on the fork path"
            )

        def mutate(head):
            defeater = head["defeaters"]["defeaters"][0]
            defeater["status"] = "WITHDRAWN"
            defeater["resolution"] = "Recorded in error; out of scope"

        code, out = self.run_register_diff(mutate, mutate_base=add_defeaters)
        self.assertEqual(code, 1, out)
        self.assertIn(
            "defeater DEF-CORE-001 disposition changed (MITIGATED to WITHDRAWN)", out
        )

    def test_defeater_resolved_to_withdrawn_not_flagged(self):
        # Both are terminal "not active" dispositions; the lateral move is
        # deliberately not gated.
        def add_defeaters(base):
            base["defeaters"] = drift_defeaters_document(
                status="RESOLVED", resolution="The bypass was removed entirely"
            )

        def mutate(head):
            head["defeaters"]["defeaters"][0]["status"] = "WITHDRAWN"

        code, out = self.run_register_diff(mutate, mutate_base=add_defeaters)
        self.assertEqual(code, 0, out)
        self.assertIn("no assurance policy regression", out)

    def test_defeater_mitigated_to_open_not_flagged(self):
        # Reopening restores scrutiny; never a weakening.
        def add_defeaters(base):
            base["defeaters"] = drift_defeaters_document(
                status="MITIGATED", resolution="A guard was added on the fork path"
            )

        def mutate(head):
            defeater = head["defeaters"]["defeaters"][0]
            defeater["status"] = "OPEN"
            defeater.pop("resolution", None)

        code, out = self.run_register_diff(mutate, mutate_base=add_defeaters)
        self.assertEqual(code, 0, out)
        self.assertIn("no assurance policy regression", out)

    # -- v0.3.2: review_after is a kept commitment -------------------------

    def test_residual_review_after_removed_fails(self):
        def schedule_base(base):
            base["residuals"]["residuals"][0]["review_after"] = "2026-12-31"

        def mutate(head):
            head["residuals"]["residuals"][0].pop("review_after")

        code, out = self.run_register_diff(mutate, mutate_base=schedule_base)
        self.assertEqual(code, 1, out)
        self.assertIn(
            "residual RES-CORE-001 review_after removed (was 2026-12-31)", out
        )

    def test_defeater_overdue_review_after_postponed_fails(self):
        # Pushing out a date that has already passed is the re-review
        # being evaded rather than done — and it is how a live overdue
        # warning would otherwise be cleared.
        def add_defeaters(base):
            base["defeaters"] = drift_defeaters_document(review_after="2020-01-01")

        def mutate(head):
            head["defeaters"]["defeaters"][0]["review_after"] = "2021-01-01"

        code, out = self.run_register_diff(mutate, mutate_base=add_defeaters)
        self.assertEqual(code, 1, out)
        self.assertIn(
            "defeater DEF-CORE-001 review_after postponed from 2020-01-01 "
            "to 2021-01-01, after the scheduled date had passed",
            out,
        )

    def test_future_review_after_rescheduled_not_flagged(self):
        # Completing a review and setting the next date is the act the
        # schedule exists to produce; a red check here would teach
        # adopters to ignore the check.
        def schedule_base(base):
            base["residuals"]["residuals"][0]["review_after"] = "2099-01-01"

        def mutate(head):
            head["residuals"]["residuals"][0]["review_after"] = "2099-06-30"

        code, out = self.run_register_diff(mutate, mutate_base=schedule_base)
        self.assertEqual(code, 0, out)
        self.assertIn("no assurance policy regression", out)

    def test_residual_review_after_unparsable_fails(self):
        def schedule_base(base):
            base["residuals"]["residuals"][0]["review_after"] = "2026-12-31"

        def mutate(head):
            head["residuals"]["residuals"][0]["review_after"] = "someday"

        code, out = self.run_register_diff(mutate, mutate_base=schedule_base)
        self.assertEqual(code, 1, out)
        self.assertIn(
            "residual RES-CORE-001 review_after replaced with an unparsable "
            "value ('someday'; was 2026-12-31)",
            out,
        )

    def test_residual_review_after_brought_forward_not_flagged(self):
        # Moving a re-review earlier strengthens scrutiny.
        def schedule_base(base):
            base["residuals"]["residuals"][0]["review_after"] = "2026-12-31"

        def mutate(head):
            head["residuals"]["residuals"][0]["review_after"] = "2026-10-01"

        code, out = self.run_register_diff(mutate, mutate_base=schedule_base)
        self.assertEqual(code, 0, out)
        self.assertIn("no assurance policy regression", out)

    def test_residual_review_after_added_not_flagged(self):
        def mutate(head):
            head["residuals"]["residuals"][0]["review_after"] = "2026-12-31"

        code, out = self.run_register_diff(mutate)
        self.assertEqual(code, 0, out)
        self.assertIn("no assurance policy regression", out)

    # -- v0.3.2: uncertainty is the second assessment axis -----------------

    def test_residual_uncertainty_downgrade_fails(self):
        def raise_base(base):
            base["residuals"]["residuals"][0]["uncertainty"] = "critical"

        def mutate(head):
            head["residuals"]["residuals"][0]["uncertainty"] = "low"

        code, out = self.run_register_diff(mutate, mutate_base=raise_base)
        self.assertEqual(code, 1, out)
        self.assertIn(
            "residual RES-CORE-001 uncertainty downgraded from critical to low", out
        )

    def test_residual_uncertainty_raised_not_flagged(self):
        # Recording more uncertainty is the conservative direction.
        def mutate(head):
            head["residuals"]["residuals"][0]["uncertainty"] = "critical"

        code, out = self.run_register_diff(mutate)
        self.assertEqual(code, 0, out)
        self.assertIn("no assurance policy regression", out)

    # -- v0.3.2: accountability and disclosure -----------------------------

    def test_owner_change_fails(self):
        def mutate(head):
            head["invariants"]["invariants"][0]["owner"] = "Mallory"

        code, out = self.run_register_diff(mutate)
        self.assertEqual(code, 1, out)
        self.assertIn(
            "invariant INV-CORE-001 owner changed from 'Alice Example' "
            "to 'Mallory'",
            out,
        )

    def test_disclosure_reclassified_not_flagged(self):
        # Disclosure is not a strength axis, the risky direction on a
        # public repository is already an error at CONFORMANT, and
        # reclassifying during triage is routine — so the policy diff
        # deliberately leaves it alone.
        def mutate(head):
            head["claims"]["claims"][0]["disclosure"] = "RESTRICTED"

        code, out = self.run_register_diff(mutate)
        self.assertEqual(code, 0, out)
        self.assertIn("no assurance policy regression", out)

    # -- v0.3.2: assurance-graph relationship lists ------------------------

    def test_claim_relationship_links_removed_fails(self):
        # A claim's defeaters/residuals lists say why it could be wrong and
        # what uncertainty remains; severing those edges is not a wording
        # change.
        def link_base(base):
            claim = base["claims"]["claims"][0]
            claim["defeaters"] = ["DEF-CORE-001"]
            claim["residuals"] = ["RES-CORE-001"]

        def mutate(head):
            claim = head["claims"]["claims"][0]
            claim.pop("defeaters")
            claim.pop("residuals")

        code, out = self.run_register_diff(mutate, mutate_base=link_base)
        self.assertEqual(code, 1, out)
        self.assertIn(
            "claim CLAIM-CORE-001: defeaters item(s) removed: DEF-CORE-001", out
        )
        self.assertIn(
            "claim CLAIM-CORE-001: residuals item(s) removed: RES-CORE-001", out
        )

    def test_low_invariant_relationship_links_removed_fails(self):
        # Relationship edges are protected at EVERY severity — unlike the
        # enforcement/verification/evidence lists, whose high/critical gate
        # is exercised above. Graph structure is not evidence volume.
        def link_base(base):
            invariant = base["invariants"]["invariants"][1]
            invariant["assumptions"] = ["Single-tenant deployment"]
            invariant["defeaters"] = ["DEF-CORE-001"]

        def mutate(head):
            invariant = head["invariants"]["invariants"][1]
            invariant.pop("assumptions")
            invariant.pop("defeaters")

        code, out = self.run_register_diff(mutate, mutate_base=link_base)
        self.assertEqual(code, 1, out)
        self.assertIn(
            "invariant INV-CORE-002: assumptions item(s) removed: "
            "Single-tenant deployment",
            out,
        )
        self.assertIn(
            "invariant INV-CORE-002: defeaters item(s) removed: DEF-CORE-001", out
        )

    def test_defeater_affected_claims_removed_fails(self):
        def add_defeaters(base):
            base["defeaters"] = drift_defeaters_document(
                affected_claims=["CLAIM-CORE-001"]
            )

        def mutate(head):
            head["defeaters"]["defeaters"][0]["affected_claims"] = []

        code, out = self.run_register_diff(mutate, mutate_base=add_defeaters)
        self.assertEqual(code, 1, out)
        self.assertIn(
            "defeater DEF-CORE-001: affected_claims item(s) removed: "
            "CLAIM-CORE-001",
            out,
        )

    def test_residual_mitigation_removed_fails(self):
        def mitigate_base(base):
            base["residuals"]["residuals"][0]["mitigation"] = [
                "Rate limiting on the export endpoint"
            ]

        def mutate(head):
            head["residuals"]["residuals"][0].pop("mitigation")

        code, out = self.run_register_diff(mutate, mutate_base=mitigate_base)
        self.assertEqual(code, 1, out)
        self.assertIn(
            "residual RES-CORE-001: mitigation item(s) removed: "
            "Rate limiting on the export endpoint",
            out,
        )

    # -- v0.3.2: intent moves off INTENDED ---------------------------------

    def test_invariant_intent_deprecated_fails(self):
        # INTENDED is the recorded human commitment; DEPRECATED (and
        # COMPATIBILITY) rewrite that decision just as UNKNOWN/ACCIDENTAL do.
        def mutate(head):
            head["invariants"]["invariants"][0]["intent"]["classification"] = (
                "DEPRECATED"
            )

        code, out = self.run_register_diff(mutate)
        self.assertEqual(code, 1, out)
        self.assertIn("intent reclassified from INTENDED to DEPRECATED", out)

    def test_invariant_intent_removed_fails(self):
        # Deleting the whole intent mapping would otherwise be the free
        # first hop: the reclassification table is pair-keyed, so a later
        # change could record any classification with no finding.
        def mutate(head):
            head["invariants"]["invariants"][0].pop("intent")

        code, out = self.run_register_diff(mutate)
        self.assertEqual(code, 1, out)
        self.assertIn(
            "invariant INV-CORE-001 intent.classification removed, emptied, "
            "or replaced with a non-string value (was INTENDED; now None)",
            out,
        )

    def test_invariant_intent_classification_emptied_fails(self):
        def mutate(head):
            head["invariants"]["invariants"][0]["intent"]["classification"] = ""

        code, out = self.run_register_diff(mutate)
        self.assertEqual(code, 1, out)
        self.assertIn("intent.classification removed, emptied, or replaced", out)

    def test_invariant_without_recorded_intent_not_flagged(self):
        # A base entry that never carried a commitment has nothing to
        # unset: the low-severity fixture invariant has no intent block.
        def mutate(head):
            head["invariants"]["invariants"][1]["title"] = "Low invariant (renamed)"

        code, out = self.run_register_diff(mutate)
        self.assertEqual(code, 0, out)
        self.assertIn("no assurance policy regression", out)

    # -- v0.3.2: duplicate head IDs fail closed ----------------------------

    def test_duplicate_head_ids_fail_closed(self):
        # by_id() is last-one-wins, so a shadow entry under a duplicated ID
        # would be invisible to the diff; the structural checks flag
        # duplicates too, but this check must not depend on a sibling job
        # being a required check. The weak copy is appended LAST so that,
        # were the per-entry diff to run on the last-one-wins view, it
        # would report a severity downgrade — asserting its absence pins
        # the fail-closed skip, not just the extra finding.
        def mutate(head):
            entries = head["invariants"]["invariants"]
            shadow = copy.deepcopy(entries[0])
            shadow["severity"] = "low"
            shadow["status"] = "UNKNOWN"
            entries.append(shadow)

        code, out = self.run_register_diff(mutate)
        self.assertEqual(code, 1, out)
        self.assertIn(
            "invariants register has duplicate ids on the head branch "
            "(INV-CORE-001)",
            out,
        )
        self.assertNotIn("severity downgraded", out)

    # -- v0.3.2: a disposition cannot be silently unset --------------------

    def test_status_removed_fails(self):
        # Deleting `status` would otherwise be a free first hop: the gated
        # transition checks would lose their baseline, and a later change
        # could arrive at ACCEPTED or a closed status with no finding on
        # either step.
        def mutate(head):
            head["residuals"]["residuals"][0].pop("status")

        code, out = self.run_register_diff(mutate)
        self.assertEqual(code, 1, out)
        self.assertIn(
            "residual RES-CORE-001 status removed, emptied, or replaced "
            "with a non-string value (was OPEN; now None)",
            out,
        )

    def test_status_emptied_fails(self):
        # An empty (or whitespace-only) status is a string, but it records
        # no disposition: it must count as unset, or it becomes the free
        # first hop the check exists to close.
        def mutate(head):
            head["claims"]["claims"][0]["status"] = "   "

        code, out = self.run_register_diff(mutate)
        self.assertEqual(code, 1, out)
        self.assertIn(
            "claim CLAIM-CORE-001 status removed, emptied, or replaced with "
            "a non-string value (was VERIFIED; now '   ')",
            out,
        )

    def test_claim_status_weakened_from_emptied_base_fails(self):
        # The second hop for claims/invariants: their weakening gate is
        # pair-keyed on a recorded base string, so the first hop must be
        # what catches an emptied status — verify the pair is closed.
        def empty_base_status(base):
            base["claims"]["claims"][0]["status"] = ""

        def mutate(head):
            head["claims"]["claims"][0]["status"] = "UNKNOWN"

        code, out = self.run_register_diff(mutate, mutate_base=empty_base_status)
        # The base recorded no disposition, so there is nothing to weaken
        # from; the hop that emptied it was itself the finding.
        self.assertEqual(code, 0, out)
        self.assertIn("no assurance policy regression", out)

    def test_contradiction_cleared_by_unsetting_reports_once(self):
        # Clearing a contradiction by deleting the status is one edit: it
        # must not be reported by both the unset check and the
        # contradiction-cleared gate.
        def contradict_base(base):
            base["claims"]["claims"][0]["status"] = "CONTRADICTED"

        def mutate(head):
            head["claims"]["claims"][0].pop("status")

        code, out = self.run_register_diff(mutate, mutate_base=contradict_base)
        self.assertEqual(code, 1, out)
        self.assertIn("status removed, emptied, or replaced", out)
        self.assertNotIn("recorded contradiction cleared", out)

    def test_ordinal_judgement_values_unset_fails(self):
        # severity/proof_tier/impact/uncertainty are compared by rank, and
        # a rank comparison needs both sides: unsetting one would be the
        # same free first hop the status check closes. severity carries a
        # second channel — the critical/high evidence gate keys on it.
        for kind, index, field, was in (
            ("invariants", 0, "severity", "critical"),
            ("claims", 0, "proof_tier", "INDEPENDENTLY_VERIFIABLE"),
            ("residuals", 0, "impact", "critical"),
            ("residuals", 0, "uncertainty", "low"),
        ):
            with self.subTest(field=field):
                def mutate(head, kind=kind, index=index, field=field):
                    head[kind][kind][index].pop(field)

                code, out = self.run_register_diff(mutate)
                self.assertEqual(code, 1, out)
                self.assertIn(
                    f"{field} removed, emptied, or replaced with a "
                    f"non-string value (was {was}; now None)",
                    out,
                )

    def test_weaker_value_after_unset_base_not_double_reported(self):
        # The pair-keyed rank check stays silent when the base has no
        # value — that hop was already reported when the value was unset,
        # so one edit never yields two findings.
        def unset_base(base):
            base["invariants"]["invariants"][0].pop("severity")

        def mutate(head):
            head["invariants"]["invariants"][0]["severity"] = "low"

        code, out = self.run_register_diff(mutate, mutate_base=unset_base)
        self.assertEqual(code, 0, out)
        self.assertIn("no assurance policy regression", out)

    def test_accepted_from_missing_base_status_fails(self):
        # The second hop of that laundering path: the base status is absent
        # (or malformed), so a gate keyed on the base value would stay
        # silent. Arriving at ACCEPTED is the reviewed event regardless of
        # what the base recorded.
        def strip_base_status(base):
            base["residuals"]["residuals"][0].pop("status")

        def mutate(head):
            residual = head["residuals"]["residuals"][0]
            residual["status"] = "ACCEPTED"
            residual["accepted_by"] = "agent-bot"
            residual["accepted_at"] = "2026-07-01"
            residual["acceptance_rationale"] = "Fabricated by an agent"

        code, out = self.run_register_diff(mutate, mutate_base=strip_base_status)
        self.assertEqual(code, 1, out)
        self.assertIn("residual RES-CORE-001 accepted (None to ACCEPTED)", out)

    def test_defeater_closed_from_non_string_base_status_fails(self):
        def add_defeaters(base):
            document = drift_defeaters_document()
            document["defeaters"][0]["status"] = ["MITIGATED"]
            base["defeaters"] = document

        def mutate(head):
            defeater = head["defeaters"]["defeaters"][0]
            defeater["status"] = "RESOLVED"
            defeater["resolution"] = "The bypass was removed entirely"

        code, out = self.run_register_diff(mutate, mutate_base=add_defeaters)
        self.assertEqual(code, 1, out)
        self.assertIn(
            "defeater DEF-CORE-001 closed (['MITIGATED'] to RESOLVED)", out
        )

    def test_unparsable_base_review_after_removal_fails(self):
        # An unparsable base value is still a recorded commitment (it can
        # predate the stricter schema, or have been pushed directly to the
        # default branch): dropping it must not fail toward silence.
        def schedule_base(base):
            base["residuals"]["residuals"][0]["review_after"] = "2026-09-01T00:00:00"

        def mutate(head):
            head["residuals"]["residuals"][0].pop("review_after")

        code, out = self.run_register_diff(mutate, mutate_base=schedule_base)
        self.assertEqual(code, 1, out)
        self.assertIn(
            "residual RES-CORE-001 review_after removed "
            "(was '2026-09-01T00:00:00')",
            out,
        )

    def test_unparsable_base_review_after_swapped_fails(self):
        # Swapping one unparsable value for another is not a repair: the
        # commitment stays unreadable to the overdue check.
        def schedule_base(base):
            base["residuals"]["residuals"][0]["review_after"] = "soonish"

        def mutate(head):
            head["residuals"]["residuals"][0]["review_after"] = "eventually"

        code, out = self.run_register_diff(mutate, mutate_base=schedule_base)
        self.assertEqual(code, 1, out)
        self.assertIn(
            "residual RES-CORE-001 review_after replaced with an unparsable "
            "value ('eventually'; was 'soonish')",
            out,
        )

    def test_unchanged_unparsable_review_after_not_flagged(self):
        # An unparsable value carried through untouched is not a new
        # weakening; the structural checks are where it gets reported.
        def schedule_base(base):
            base["residuals"]["residuals"][0]["review_after"] = "soonish"

        code, out = self.run_register_diff(lambda head: None, mutate_base=schedule_base)
        self.assertEqual(code, 0, out)
        self.assertIn("no assurance policy regression", out)

    def test_unparsable_base_review_after_repaired_not_flagged(self):
        # Repairing garbage into a real date re-enables the overdue check.
        def schedule_base(base):
            base["residuals"]["residuals"][0]["review_after"] = "soonish"

        def mutate(head):
            head["residuals"]["residuals"][0]["review_after"] = "2026-12-31"

        code, out = self.run_register_diff(mutate, mutate_base=schedule_base)
        self.assertEqual(code, 0, out)
        self.assertIn("no assurance policy regression", out)

    # -- v0.3.2: no false positives on a fully populated register ----------

    def test_identical_rich_registers_report_no_regression(self):
        # Every field the v0.3.2 checks compare, populated and unchanged:
        # the diff must stay silent. Guards the new checks against firing
        # on ordinary pull requests that touch nothing they protect.
        def enrich(registers):
            claim = registers["claims"]["claims"][0]
            claim["evidence"] = ["evidence/claim-1.txt"]
            claim["invariants"] = ["INV-CORE-001"]
            claim["limitations"] = ["Only covers the happy path"]
            claim["defeaters"] = ["DEF-CORE-001"]
            claim["residuals"] = ["RES-CORE-001"]
            invariant = registers["invariants"]["invariants"][0]
            invariant["assumptions"] = ["Single-tenant deployment"]
            invariant["limitations"] = ["Not verified under partition"]
            invariant["defeaters"] = ["DEF-CORE-001"]
            invariant["residuals"] = ["RES-CORE-001"]
            residual = registers["residuals"]["residuals"][0]
            residual["status"] = "ACCEPTED"
            residual["accepted_by"] = "Alice Example"
            residual["accepted_at"] = "2026-01-01"
            residual["acceptance_rationale"] = "Cost exceeds exposure"
            residual["mitigation"] = ["Rate limiting on the export endpoint"]
            residual["affected_claims"] = ["CLAIM-CORE-001"]
            residual["affected_invariants"] = ["INV-CORE-001"]
            residual["review_after"] = "2026-12-31"
            registers["defeaters"] = drift_defeaters_document(
                status="MITIGATED",
                resolution="A guard was added on the fork path",
                affected_claims=["CLAIM-CORE-001"],
                affected_invariants=["INV-CORE-001"],
                evidence=["evidence/defeater-1.txt"],
                review_after="2026-12-31",
            )

        code, out = self.run_register_diff(lambda head: None, mutate_base=enrich)
        self.assertEqual(code, 0, out)
        self.assertIn("no assurance policy regression", out)

    def test_new_finding_kinds_acknowledged_draft_base_warn(self):
        # The new finding kinds ride the existing stage-proportional ladder:
        # a DRAFT base plus the acknowledgment line downgrades them all.
        def enrich(registers):
            registers["residuals"]["residuals"][0]["review_after"] = "2020-01-01"

        def mutate(head):
            residual = head["residuals"]["residuals"][0]
            residual["owner"] = "Bob Example"
            residual["uncertainty"] = "unknown"
            residual["review_after"] = "2021-01-01"
            residual["status"] = "ACCEPTED"
            residual["accepted_by"] = "Bob Example"
            residual["accepted_at"] = "2026-07-01"
            residual["acceptance_rationale"] = "Accepted after re-triage"

        code, out = self.run_register_diff(
            mutate,
            body="Assurance policy change: risk re-triaged with the owner\n",
            mutate_base=enrich,
        )
        self.assertEqual(code, 0, out)
        self.assertIn("WARN:", out)
        self.assertNotIn("ERROR:", out)
        for fragment in (
            "owner changed from 'Alice Example' to 'Bob Example'",
            "uncertainty downgraded from low to unknown",
            "review_after postponed from 2020-01-01 to 2021-01-01",
            "accepted (OPEN to ACCEPTED)",
        ):
            self.assertIn(fragment, out)

    # -- v0.3.2: unusable base registers fail closed -----------------------

    def test_base_register_not_a_mapping_fails_closed(self):
        # A base register that parses cleanly but is not a mapping with the
        # register's list — exactly what `git show` used to materialize for
        # a symlinked register (the target-path string) — must be a hard
        # error, not a silent skip of the whole register's diff.
        base = baseline_adoption()
        head = copy.deepcopy(base)
        base_registers = drift_register_fixture()
        base_registers["invariants"] = "../elsewhere/INVARIANTS.yaml"
        head_registers = drift_register_fixture()
        code, out = self.run_drift(
            head,
            changed=(),
            base_adoption=base,
            base_registers=base_registers,
            head_registers=head_registers,
        )
        self.assertEqual(code, 1, out)
        self.assertIn("base register", out)
        self.assertIn("not a mapping with a 'invariants' list", out)

    def test_base_register_directory_fails_closed(self):
        # A directory (or a broken symlink) at the register's path is not
        # "absent": the register exists in some form and cannot be read, so
        # its entries must not drop silently out of the comparison.
        base = baseline_adoption()
        head = copy.deepcopy(base)
        registers = drift_register_fixture()
        root = self.make_tmp()
        base_root = root / "base-root"
        for kind in ("claims", "residuals"):
            write_yaml(base_root / REGISTER_FILES[kind], registers[kind])
        (base_root / REGISTER_FILES["invariants"]).mkdir(parents=True)
        head_root = root / "head-root"
        for kind, document in registers.items():
            write_yaml(head_root / REGISTER_FILES[kind], document)
        write_yaml(root / "adoption.yaml", head)
        write_yaml(root / "base-adoption.yaml", base)
        (root / "changed.txt").write_text("", encoding="utf-8")
        code, out = run_validator(
            [
                "drift",
                "--adoption",
                str(root / "adoption.yaml"),
                "--changed-files",
                str(root / "changed.txt"),
                "--pr-body",
                str(root / "missing-body.txt"),
                "--base-adoption",
                str(root / "base-adoption.yaml"),
                "--base-registers-root",
                str(base_root),
                "--project-root",
                str(head_root),
            ]
        )
        self.assertEqual(code, 1, out)
        self.assertIn("base register", out)
        self.assertIn("exists but is not a readable file", out)

    def test_base_register_broken_symlink_fails_closed(self):
        # A dangling symlink does not satisfy exists(); without the
        # is_symlink() branch it would read as "register absent" and its
        # entries would drop silently out of the comparison.
        base = baseline_adoption()
        head = copy.deepcopy(base)
        registers = drift_register_fixture()
        root = self.make_tmp()
        base_root = root / "base-root"
        for kind in ("claims", "residuals"):
            write_yaml(base_root / REGISTER_FILES[kind], registers[kind])
        link = base_root / REGISTER_FILES["invariants"]
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(Path("gone") / "INVARIANTS.yaml")
        head_root = root / "head-root"
        for kind, document in registers.items():
            write_yaml(head_root / REGISTER_FILES[kind], document)
        write_yaml(root / "adoption.yaml", head)
        write_yaml(root / "base-adoption.yaml", base)
        (root / "changed.txt").write_text("", encoding="utf-8")
        code, out = run_validator(
            [
                "drift",
                "--adoption",
                str(root / "adoption.yaml"),
                "--changed-files",
                str(root / "changed.txt"),
                "--pr-body",
                str(root / "missing-body.txt"),
                "--base-adoption",
                str(root / "base-adoption.yaml"),
                "--base-registers-root",
                str(base_root),
                "--project-root",
                str(head_root),
            ]
        )
        self.assertEqual(code, 1, out)
        self.assertIn("base register", out)
        self.assertIn("exists but is not a readable file", out)

    def test_lite_base_section_not_a_list_fails_closed(self):
        # The lite layout carries the registers as sections of one file; a
        # section that is not a list is as unusable as a malformed register
        # file and must be reported, not skipped.
        base = baseline_adoption()
        base["layout"] = "lite"
        head = copy.deepcopy(base)
        root = self.make_tmp()
        base_root = root / "base-root"
        write_yaml(
            base_root / ".agentic-assurance" / "assurance.yaml",
            {"version": 1, "residuals": "see the other document"},
        )
        head_root = root / "head-root"
        write_yaml(
            head_root / ".agentic-assurance" / "assurance.yaml",
            {"version": 1, "residuals": [baseline_residual()]},
        )
        write_yaml(root / "adoption.yaml", head)
        write_yaml(root / "base-adoption.yaml", base)
        (root / "changed.txt").write_text("", encoding="utf-8")
        code, out = run_validator(
            [
                "drift",
                "--adoption",
                str(root / "adoption.yaml"),
                "--changed-files",
                str(root / "changed.txt"),
                "--pr-body",
                str(root / "missing-body.txt"),
                "--base-adoption",
                str(root / "base-adoption.yaml"),
                "--base-registers-root",
                str(base_root),
                "--project-root",
                str(head_root),
            ]
        )
        self.assertEqual(code, 1, out)
        self.assertIn("section 'residuals' is not a list", out)

    def test_symlinked_base_register_compared(self):
        # The workflow materializes the base side as a git worktree, so a
        # register that is an in-tree symlink arrives as a symlink and must
        # be read through — the validator's containment check permits
        # in-root targets, and the diff must still see the base entries.
        base = baseline_adoption()
        head = copy.deepcopy(base)
        registers = drift_register_fixture()
        root = self.make_tmp()
        base_root = root / "base-root"
        write_yaml(base_root / "real" / "INVARIANTS.yaml", registers["invariants"])
        link = base_root / REGISTER_FILES["invariants"]
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(Path("..") / "real" / "INVARIANTS.yaml")
        for kind in ("claims", "residuals"):
            write_yaml(base_root / REGISTER_FILES[kind], registers[kind])
        head_registers = copy.deepcopy(registers)
        head_registers["invariants"]["invariants"] = []
        head_root = root / "head-root"
        for kind, document in head_registers.items():
            write_yaml(head_root / REGISTER_FILES[kind], document)
        write_yaml(root / "adoption.yaml", head)
        write_yaml(root / "base-adoption.yaml", base)
        (root / "changed.txt").write_text("", encoding="utf-8")
        code, out = run_validator(
            [
                "drift",
                "--adoption",
                str(root / "adoption.yaml"),
                "--changed-files",
                str(root / "changed.txt"),
                "--pr-body",
                str(root / "missing-body.txt"),
                "--base-adoption",
                str(root / "base-adoption.yaml"),
                "--base-registers-root",
                str(base_root),
                "--project-root",
                str(head_root),
            ]
        )
        self.assertEqual(code, 1, out)
        self.assertIn("invariants entry INV-CORE-001 deleted", out)

    def test_unhashable_status_does_not_crash(self):
        # The register files are loaded without schema validation (a base
        # merged before the stricter schema, or added directly to the
        # default branch, can hold any YAML type). A list-valued status must
        # not crash the diff with an unhashable-key TypeError.
        def mutate(head):
            head["invariants"]["invariants"][0]["status"] = "UNKNOWN"

        base = baseline_adoption()
        head = copy.deepcopy(base)
        base_registers = drift_register_fixture()
        base_registers["invariants"]["invariants"][0]["status"] = ["VERIFIED"]
        head_registers = copy.deepcopy(drift_register_fixture())
        mutate(head_registers)
        code, out = self.run_drift(
            head,
            changed=(),
            base_adoption=base,
            base_registers=base_registers,
            head_registers=head_registers,
        )
        self.assertNotIn("Traceback", out)
        # A non-string base status is not a recognized weakening source, so
        # the status change is simply not flagged (it does not crash).
        self.assertNotIn("status weakened", out)


class TestDriftPathTraversal(ValidatorTestCase):
    """The register diff must not read files outside the roots it is given,
    even though the `paths:` map comes from a pull-request-controlled
    adoption file (the same containment adopter mode applies)."""

    def test_absolute_head_register_path_is_contained(self):
        secret = self.make_tmp() / "outside" / "secret.txt"
        secret.parent.mkdir(parents=True)
        secret.write_text("TOPSECRET-CONTENT\n", encoding="utf-8")

        base = baseline_adoption()
        head = copy.deepcopy(base)
        head.setdefault("paths", {})["invariants"] = str(secret)
        code, out = self.run_drift(
            head,
            changed=(),
            base_adoption=base,
            base_registers={},
            head_registers={},
        )
        # The traversal path is dropped and reported; the file is never read.
        self.assertIn("resolves outside the project root", out)
        self.assertNotIn("TOPSECRET-CONTENT", out)
        self.assertNotIn("cannot parse", out)

    def test_dotdot_head_register_path_is_contained(self):
        base = baseline_adoption()
        head = copy.deepcopy(base)
        head.setdefault("paths", {})["invariants"] = "../../../../etc/hostname"
        code, out = self.run_drift(
            head,
            changed=(),
            base_adoption=base,
            base_registers={},
            head_registers={},
        )
        # A .. traversal is dropped and reported, never read/parsed.
        self.assertIn("resolves outside the project root", out)
        self.assertNotIn("cannot parse", out)


# ---------------------------------------------------------------------------
# 11. GitHub Actions annotations
# ---------------------------------------------------------------------------


class TestGithubAnnotations(ValidatorTestCase):
    def test_error_annotation_emitted_when_github_actions_set(self):
        adoption = baseline_adoption()
        adoption["project"]["human_owner"] = "REPLACE_WITH_OWNER_NAME"
        root = self.make_tmp()
        adoption_path = build_split_project(root, adoption, baseline_registers())
        env = clean_env({"GITHUB_ACTIONS": "true"})
        code, out = self.run_adopter(root, adoption_path, env=env)
        self.assertEqual(code, 1, out)
        self.assertTrue(
            any(line.startswith("::error::") for line in out.splitlines()),
            out,
        )


if __name__ == "__main__":
    unittest.main()
