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


def baseline_registers():
    """Minimal registers for a passing core adoption: residuals only."""
    return {"residuals": {"version": 1, "residuals": [baseline_residual()]}}


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
        registers = {"residuals": {"version": 1, "residuals": []}}
        code, out = self.run_split(baseline_adoption(), registers)
        self.assertEqual(code, 1, out)
        self.assertIn("register is empty", out)
        self.assertIn("residuals register is empty", out)

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
        registers = {"residuals": {"version": 1, "residuals": [residual]}}
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

    def test_profile_beyond_core_fails(self):
        adoption = baseline_lite_adoption()
        adoption["profiles"] = ["core", "service"]
        code, out = self.run_lite(adoption, baseline_lite_assurance())
        self.assertEqual(code, 1, out)
        self.assertIn("layout 'lite' supports only the core and archived profiles", out)

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


class TestDriftRegisterPolicyDiff(ValidatorTestCase):
    """Stable-ID register diff: each test applies one mutation between the
    base and head register files. The base adoption is stage DRAFT (absent)
    and no acknowledgment is given, so findings are errors — except in the
    acknowledgment test, where the DRAFT base downgrades them to warnings."""

    def run_register_diff(self, mutate_head, body=None):
        base = baseline_adoption()
        head = copy.deepcopy(base)
        base_registers = drift_register_fixture()
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
