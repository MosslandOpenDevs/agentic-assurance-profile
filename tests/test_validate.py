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

    def test_acknowledged_policy_change_passes_with_warning(self):
        def mutate(head):
            head["adoption_stage"] = "DRAFT"

        code, out = self.run_regression(
            mutate, body="Assurance policy change: deliberate reset during restructure\n"
        )
        self.assertEqual(code, 0, out)
        self.assertIn("WARN:", out)
        self.assertIn("acknowledged", out)

    def test_no_changes_reports_no_regression(self):
        code, out = self.run_regression(lambda head: None)
        self.assertEqual(code, 0, out)
        self.assertIn("no assurance policy regression", out)


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
