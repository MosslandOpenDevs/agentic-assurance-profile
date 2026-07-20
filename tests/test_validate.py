"""Regression tests for scripts/validate.py (self-check, adopter, drift).

Standard library only (unittest, tempfile, pathlib, subprocess, json, copy,
shutil).
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
import datetime
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parent.parent
VALIDATOR = REPO_ROOT / "scripts" / "validate.py"
SCHEMAS_DIR = REPO_ROOT / "schemas"
LITE_ASSURANCE_PATH = ".agentic-assurance/assurance.yaml"

# Fixed dates: far future for non-expired review_after, fixed past for
# expired ones. Tests must never depend on what today's date happens to be.
FUTURE_DATE = "2999-01-01"
PAST_DATE = "2000-01-01"

CURRENT_REVIEW_DATE_PLACEHOLDER = "REPLACE_WITH_REVIEW_AFTER_DATE"
LEGACY_REVIEW_DATE_PLACEHOLDER = "YYYY-MM-DD"
REVIEW_DATE_PLACEHOLDERS = (
    CURRENT_REVIEW_DATE_PLACEHOLDER,
    LEGACY_REVIEW_DATE_PLACEHOLDER,
)

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


def run_validator(
    args, env=None, timeout=120, validator=VALIDATOR, isolated=False
):
    """Run scripts/validate.py with args; return (exit_code, combined_output)."""
    completed = subprocess.run(
        [sys.executable, *( ["-I"] if isolated else []), str(validator), *args],
        capture_output=True,
        text=True,
        env=clean_env() if env is None else env,
        cwd=str(REPO_ROOT),
        timeout=timeout,
    )
    return completed.returncode, completed.stdout + completed.stderr


def workflow_step_spec(step_name):
    """Return the declared shell and body for one reusable-workflow step."""
    workflow = (
        REPO_ROOT / ".github" / "workflows" / "adopter-validate.yml"
    ).read_text(encoding="utf-8")
    marker = f"      - name: {step_name}\n"
    section = workflow[workflow.index(marker) :]
    run_marker = "        run: |\n"
    run_index = section.index(run_marker)
    preamble = section[:run_index]
    shell_prefix = "        shell: "
    shell_lines = [
        line[len(shell_prefix) :]
        for line in preamble.splitlines()
        if line.startswith(shell_prefix)
    ]
    if len(shell_lines) > 1:
        raise AssertionError(f"workflow step {step_name!r} has multiple shells")
    shell = shell_lines[0] if shell_lines else None
    body = section[run_index + len(run_marker) :]
    lines = []
    for line in body.splitlines():
        if line.startswith("      - name:"):
            break
        lines.append(line[10:] if line.startswith("          ") else line)
    script = "\n".join(lines) + "\n"
    return shell, script


def workflow_step_shell(step_name):
    """Extract one bash reusable-workflow run block for direct execution."""
    shell, script = workflow_step_spec(step_name)
    if shell is not None:
        raise AssertionError(
            f"workflow step {step_name!r} declares non-bash shell {shell!r}"
        )
    return script.replace("python -", f"{shlex.quote(sys.executable)} -", 1)


def run_workflow_step(
    step_name,
    *,
    cwd,
    env,
    timeout,
    script_replacements=(),
):
    """Execute one workflow body with the shell declared by that step."""
    shell, script = workflow_step_spec(step_name)
    for before, after in script_replacements:
        if before not in script:
            raise AssertionError(f"workflow fixture replacement not found: {before}")
        script = script.replace(before, after, 1)
    if shell is None:
        command = [
            "bash",
            "-c",
            script.replace(
                "python -", f"{shlex.quote(sys.executable)} -", 1
            ),
        ]
        return subprocess.run(
            command,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    if shell != "python -I {0}":
        raise AssertionError(
            f"workflow step {step_name!r} has unsupported test shell {shell!r}"
        )
    with tempfile.TemporaryDirectory(prefix="aap-workflow-step-") as temp_dir:
        script_path = Path(temp_dir) / "step.py"
        script_path.write_text(script, encoding="utf-8")
        return subprocess.run(
            [sys.executable, "-I", str(script_path)],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )


def write_yaml(path, document):
    """Write a fixture document as JSON, which PyYAML parses as YAML."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2), encoding="utf-8")


def write_caller_workflow(path, adoption_file=None, revision=None):
    """Write a direct reusable-workflow caller (with GitHub's unquoted `on`)."""
    if revision is None:
        revision = "a" * 40
    lines = [
        "name: assurance",
        "on:",
        "  pull_request:",
        "jobs:",
        "  assurance:",
        "    uses: MosslandOpenDevs/agentic-assurance-profile/"
        f".github/workflows/adopter-validate.yml@{revision}",
    ]
    if adoption_file is not None:
        lines.extend(
            [
                "    with:",
                f"      adoption-file: {json.dumps(adoption_file)}",
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def init_git_test_repository(path):
    path.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "tests@example.invalid"],
        cwd=path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "AAP tests"],
        cwd=path,
        check=True,
    )


def commit_test_repository(path, message):
    subprocess.run(["git", "add", "-A"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-qm", message], cwd=path, check=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def run_workflow_materializer(
    root,
    repository,
    base_sha,
    head_sha,
    adoption_file,
    caller_name="assurance.yml",
    script_replacements=(),
    env_updates=None,
):
    """Run the materializer step with the reusable workflow's caller context."""
    trusted_scripts = repository / ".assurance-profile-pin" / "scripts"
    trusted_scripts.mkdir(parents=True, exist_ok=True)
    shutil.copy2(VALIDATOR, trusted_scripts / "validate.py")
    runner_temp = root / "runner-temp"
    runner_temp.mkdir()
    env_values = {
        "BASE_SHA": base_sha,
        "HEAD_SHA": head_sha,
        "ADOPTION_FILE": adoption_file,
        "RUNNER_TEMP": str(runner_temp),
        "CALLER_REPOSITORY": "example/repo",
        "CALLER_WORKFLOW_REF": (
            f"example/repo/.github/workflows/{caller_name}@refs/pull/1/merge"
        ),
    }
    if env_updates:
        env_values.update(env_updates)
    env = clean_env(env_values)
    completed = run_workflow_step(
        "Materialize the base tree and compute the assurance diff",
        cwd=repository,
        env=env,
        timeout=60,
        script_replacements=script_replacements,
    )
    return completed, runner_temp


def workflow_policy_adoption(
    *, stage="HUMAN_REVIEWED", profiles=None, version="v0.3.2"
):
    """Canonical declaration suitable for base-materialization fixtures."""
    adoption = baseline_adoption()
    adoption["upstream"].update(
        {
            "repository": "MosslandOpenDevs/agentic-assurance-profile",
            "version": version,
            "commit": "a" * 40,
        }
    )
    adoption["profiles"] = ["core"] if profiles is None else profiles
    adoption["adoption_stage"] = stage
    if stage in ("HUMAN_REVIEWED", "CONFORMANT"):
        adoption["human_review"] = human_review_block()
    return adoption


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
        "specification_workflow": {
            "system": "minimal",
            "root": "AGENTIC_ASSURANCE.md",
        },
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


def registers_with_legacy_bare_prompts():
    """All seven direct-field prompts copied from the v0.3.x templates."""
    _adoption, registers = conformant_fixture()
    for kind, fields in LEGACY_REGISTER_FIELD_PLACEHOLDERS.items():
        registers[kind][kind][0].update(fields)
    return registers


def lite_assurance_with_legacy_bare_prompts():
    """The five v0.3.x prompts representable in the lite layout."""
    assurance = baseline_lite_assurance()
    for kind in ("invariants", "residuals"):
        assurance[kind][0].update(LEGACY_REGISTER_FIELD_PLACEHOLDERS[kind])
    assurance["defeaters"] = [
        {
            "id": "DEF-CORE-001",
            "statement": LEGACY_REGISTER_FIELD_PLACEHOLDERS["defeaters"][
                "statement"
            ],
            "status": "OPEN",
            "disclosure": "PUBLIC",
            "owner": "Alice Example",
        }
    ]
    return assurance


REGISTER_FILES = {
    "claims": "assurance/CLAIMS.yaml",
    "invariants": "assurance/INVARIANTS.yaml",
    "defeaters": "assurance/DEFEATERS.yaml",
    "residuals": "assurance/RESIDUALS.yaml",
}


def reading_order_block(adoption_reference=".agentic-assurance/adoption.yaml"):
    """Canonical visible root-file reading order with a configurable pin path."""
    return (
        "Before any material change, read:\n\n"
        "1. `AGENTIC_ASSURANCE.md`;\n"
        f"2. `{adoption_reference}`;\n"
        "3. the project system artifact and applicable non-goals;\n"
        "4. affected claims, invariants, defeaters, and residuals, where applicable;\n"
        "5. the active change specification, when applicable.\n"
    )


def build_split_project(root, adoption, registers):
    """Write a split-layout adopter fixture; return the adoption file path."""
    root = Path(root)
    (root / "AGENTIC_ASSURANCE.md").write_text(
        "# Assurance\n\n" + reading_order_block(),
        encoding="utf-8",
    )
    (root / "AGENTS.md").write_text(
        "# Agents\n\n" + reading_order_block(),
        encoding="utf-8",
    )
    (root / "assurance").mkdir(parents=True, exist_ok=True)
    (root / "assurance" / "SYSTEM.md").write_text("# System\n", encoding="utf-8")
    for kind, document in registers.items():
        write_yaml(root / REGISTER_FILES[kind], document)
    adoption_path = root / ".agentic-assurance" / "adoption.yaml"
    write_yaml(adoption_path, adoption)
    review = adoption.get("human_review")
    record = review.get("record") if isinstance(review, dict) else None
    if isinstance(record, str):
        record_path = (root / record).resolve()
        if record_path.is_relative_to(root.resolve()):
            record_path.parent.mkdir(parents=True, exist_ok=True)
            record_path.write_text("# Human review\n", encoding="utf-8")
    return adoption_path


def build_lite_project(root, adoption, assurance):
    """Write a lite-layout adopter fixture; return the adoption file path."""
    root = Path(root)
    (root / "AGENTIC_ASSURANCE.md").write_text(
        "# Assurance\n\n" + reading_order_block(),
        encoding="utf-8",
    )
    (root / "AGENTS.md").write_text(
        "# Agents\n\n" + reading_order_block(),
        encoding="utf-8",
    )
    write_yaml(root / ".agentic-assurance" / "assurance.yaml", assurance)
    adoption_path = root / ".agentic-assurance" / "adoption.yaml"
    write_yaml(adoption_path, adoption)
    review = adoption.get("human_review")
    record = review.get("record") if isinstance(review, dict) else None
    if isinstance(record, str):
        record_path = (root / record).resolve()
        if record_path.is_relative_to(root.resolve()):
            record_path.parent.mkdir(parents=True, exist_ok=True)
            record_path.write_text("# Human review\n", encoding="utf-8")
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


def copy_self_check_fixture(root):
    """Copy only the inputs consumed by the central self-check."""
    root = Path(root)
    shutil.copy2(REPO_ROOT / "VERSION", root / "VERSION")
    shutil.copytree(REPO_ROOT / "schemas", root / "schemas")
    shutil.copytree(REPO_ROOT / "templates", root / "templates")


class ValidatorTestCase(unittest.TestCase):
    """Shared helpers: temp dirs and the adopter/drift CLI wrappers."""

    def make_tmp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name)

    def adopter_profile_checkout(self):
        """A release-like checkout paired with the schemas used by tests."""
        checkout = getattr(self, "_adopter_profile_checkout", None)
        if checkout is None:
            checkout = self.make_tmp() / "profile-checkout"
            shutil.copytree(SCHEMAS_DIR, checkout / "schemas")
            (checkout / "VERSION").write_text("v0.2.0\n", encoding="utf-8")
            self._adopter_profile_checkout = checkout
        return checkout

    def run_adopter(self, project_root, adoption_path, *extra, env=None):
        checkout = self.adopter_profile_checkout()
        return run_validator(
            [
                "adopter",
                "--adoption",
                str(adoption_path),
                "--project-root",
                str(project_root),
                "--schemas",
                str(checkout / "schemas"),
                "--profile-checkout",
                str(checkout),
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
        base_lite_assurance=None,
        head_lite_assurance=None,
        base_root_setup=None,
        head_root_setup=None,
        adoption_paths=None,
        changed_nul=False,
        strict=False,
        env=None,
        timeout=120,
    ):
        root = self.make_tmp()
        write_yaml(root / "adoption.yaml", adoption)
        changed_path = root / "changed.txt"
        if changed_nul:
            encoded = [line.encode("utf-8") for line in changed]
            changed_path.write_bytes(b"\0".join(encoded) + (b"\0" if encoded else b""))
        else:
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
        if adoption_paths is not None:
            if len(adoption_paths) == 2:
                base_path, head_path = adoption_paths
                base_resolved, head_resolved = adoption_paths
            else:
                base_path, head_path, base_resolved, head_resolved = adoption_paths
            write_yaml(
                root / "adoption-path-transition.json",
                {
                    "base": base_path,
                    "head": head_path,
                    "base_resolved": base_resolved,
                    "head_resolved": head_resolved,
                },
            )
            args += [
                "--adoption-path-transition",
                str(root / "adoption-path-transition.json"),
            ]
        # The register policy diff needs both roots: the base registers are
        # materialized under --base-registers-root at the BASE declaration's
        # paths, the head registers under --project-root at the HEAD ones
        # (both fixtures use the default assurance/ layout).
        if base_registers is not None or base_lite_assurance is not None:
            base_root = root / "base-root"
            base_root.mkdir(parents=True, exist_ok=True)
            for kind, register_document in (base_registers or {}).items():
                write_yaml(base_root / REGISTER_FILES[kind], register_document)
            if base_lite_assurance is not None:
                write_yaml(
                    base_root / LITE_ASSURANCE_PATH, base_lite_assurance
                )
            if base_root_setup is not None:
                base_root_setup(base_root)
            args += ["--base-registers-root", str(base_root)]
        if head_registers is not None or head_lite_assurance is not None:
            head_root = root / "head-root"
            for kind, register_document in (head_registers or {}).items():
                write_yaml(head_root / REGISTER_FILES[kind], register_document)
            if head_lite_assurance is not None:
                write_yaml(
                    head_root / LITE_ASSURANCE_PATH, head_lite_assurance
                )
            if head_root_setup is not None:
                head_root_setup(head_root)
            head_adoption_path = head_root / ".agentic-assurance" / "adoption.yaml"
            write_yaml(head_adoption_path, adoption)
            args[2] = str(head_adoption_path)
            args += ["--project-root", str(head_root)]
        if strict:
            args.append("--strict")
        return run_validator(args, env=env, timeout=timeout)


# ---------------------------------------------------------------------------
# 1. self-check
# ---------------------------------------------------------------------------


class TestSelfCheck(ValidatorTestCase):
    def test_self_check_passes_on_repository(self):
        code, out = run_validator(["self-check", "--repo-root", str(REPO_ROOT)])
        self.assertEqual(code, 0, out)
        self.assertNotIn("ERROR:", out)

    def test_default_codeowners_covers_declared_security_policy(self):
        root = self.make_tmp()
        copy_self_check_fixture(root)
        codeowners = root / "templates" / "github" / "CODEOWNERS"
        text = codeowners.read_text(encoding="utf-8")
        text = text.replace(
            "/SECURITY.md                      @REPLACE_WITH_OWNER_OR_TEAM\n",
            "",
        )
        codeowners.write_text(text, encoding="utf-8")

        code, out = run_validator(["self-check", "--repo-root", str(root)])
        self.assertEqual(code, 1, out)
        self.assertIn("SECURITY.md", out)
        self.assertIn("lack an owner rule", out)

    def test_codeowners_coverage_requires_physical_ascii_valid_owner_rule(self):
        original = "AGENTS.md                         @REPLACE_WITH_OWNER_OR_TEAM\n"
        variants = {
            "unicode record separator": (
                "# one physical comment\u2028"
                "AGENTS.md @REPLACE_WITH_OWNER_OR_TEAM\n"
            ),
            "bare CR record separator": (
                "# one physical comment\r"
                "AGENTS.md @REPLACE_WITH_OWNER_OR_TEAM\n"
            ),
            "unicode owner separator": (
                "AGENTS.md\u00a0@REPLACE_WITH_OWNER_OR_TEAM\n"
            ),
            "invalid owner token": "AGENTS.md NOT_AN_OWNER\n",
            "double leading slash": (
                "//AGENTS.md @REPLACE_WITH_OWNER_OR_TEAM\n"
            ),
            "dot component": (
                "/./AGENTS.md @REPLACE_WITH_OWNER_OR_TEAM\n"
            ),
            "double trailing slash": (
                "AGENTS.md// @REPLACE_WITH_OWNER_OR_TEAM\n"
            ),
        }
        for label, replacement in variants.items():
            with self.subTest(label=label):
                root = self.make_tmp()
                copy_self_check_fixture(root)
                codeowners = root / "templates" / "github" / "CODEOWNERS"
                text = codeowners.read_text(encoding="utf-8")
                self.assertIn(original, text)
                codeowners.write_text(
                    text.replace(original, replacement, 1), encoding="utf-8"
                )
                code, out = run_validator(
                    ["self-check", "--repo-root", str(root)]
                )
                self.assertEqual(code, 1, out)
                self.assertIn("AGENTS.md", out)
                self.assertIn("lack an owner rule", out)

    def test_empty_mandatory_split_register_templates_fail(self):
        # Split templates are shipped as one core starter set. Schema and
        # per-entry semantics alone accept an empty list, so self-check must
        # apply the same non-vacuity obligations as adopter mode.
        for kind, filename in (
            ("invariants", "INVARIANTS.yaml"),
            ("residuals", "RESIDUALS.yaml"),
        ):
            with self.subTest(kind=kind):
                root = self.make_tmp()
                copy_self_check_fixture(root)
                write_yaml(
                    root / "templates" / filename,
                    {"version": 1, kind: []},
                )
                code, out = run_validator(["self-check", "--repo-root", str(root)])
                self.assertEqual(code, 1, out)
                self.assertIn(f"{kind} register is empty", out)

    def test_schema_invalid_register_template_has_no_semantic_ok(self):
        root = self.make_tmp()
        copy_self_check_fixture(root)
        path = root / "templates" / "INVARIANTS.yaml"
        text = path.read_text(encoding="utf-8")
        owner_line = "    owner: REPLACE_WITH_OWNER\n"
        self.assertIn(owner_line, text)
        path.write_text(text.replace(owner_line, "", 1), encoding="utf-8")
        code, out = run_validator(["self-check", "--repo-root", str(root)])
        self.assertEqual(code, 1, out)
        self.assertIn("owner", out)
        self.assertNotIn(
            "OK: semantic checks — ids unique, references resolve, statuses grounded",
            out,
        )

    def test_schema_invalid_lite_template_has_no_semantic_ok(self):
        root = self.make_tmp()
        copy_self_check_fixture(root)
        write_yaml(root / "templates" / "assurance.yaml", {})

        code, out = run_validator(["self-check", "--repo-root", str(root)])
        self.assertEqual(code, 1, out)
        self.assertIn("templates/assurance.yaml", out)
        self.assertNotIn(
            "OK: templates/assurance.yaml semantic checks", out
        )

    def test_archived_system_markers_match_the_interim_guard(self):
        root = self.make_tmp()
        copy_self_check_fixture(root)
        path = root / "templates" / "SYSTEM.md"
        text = path.read_text(encoding="utf-8")
        text = text.replace(
            "REPLACE_WITH_ARCHIVED_HISTORICAL_PURPOSE",
            "REPLACE_WITH_ARCHIVED_HISTORICAL_PURPOSE_V2",
            1,
        )
        path.write_text(text, encoding="utf-8")
        code, out = run_validator(["self-check", "--repo-root", str(root)])
        self.assertEqual(code, 1, out)
        self.assertIn("four exact interim completion guards", out)

    def test_shipped_lite_templates_without_inline_system_fail(self):
        # Both files are advertised as complete four-file starting paths. The
        # schema permits an external SYSTEM.md, but the shipped copies must not
        # silently require a fifth file.
        system_block = (
            "system: |\n"
            "  REPLACE_WITH_SYSTEM_IDENTITY_RESPONSIBILITIES_BOUNDARIES_"
            "LIMITATIONS_AND_UNKNOWNS\n"
        )
        for filename in ("assurance.minimal.yaml", "assurance.yaml"):
            with self.subTest(filename=filename):
                root = self.make_tmp()
                copy_self_check_fixture(root)
                path = root / "templates" / filename
                text = path.read_text(encoding="utf-8")
                self.assertIn(system_block, text)
                path.write_text(text.replace(system_block, "", 1), encoding="utf-8")
                code, out = run_validator(
                    ["self-check", "--repo-root", str(root)]
                )
                self.assertEqual(code, 1, out)
                self.assertIn(
                    "shipped lite template must include a non-empty "
                    "'system' section",
                    out,
                )

    def test_expanded_lite_template_keeps_documented_optional_surface(self):
        # `resolution` is a comment-only prompt and `extensions` is optional in
        # the schema, so the ordinary YAML self-check cannot pin either one.
        text = (REPO_ROOT / "templates" / "assurance.yaml").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "#     # resolution: "
            "REPLACE_WITH_HOW_THE_DEFEATER_WAS_RESOLVED_MITIGATED_OR_WITHDRAWN",
            text,
        )
        self.assertIn("\nextensions: {}\n", text)

    def test_standalone_agents_block_must_match_normative_copy(self):
        # templates/AGENTS.md explicitly promises a verbatim copy of §11.
        # A prose-only change can otherwise drift without schema coverage.
        root = self.make_tmp()
        copy_self_check_fixture(root)
        path = root / "templates" / "AGENTS.md"
        text = path.read_text(encoding="utf-8")
        text = text.replace(
            "affected claims, invariants, defeaters, and residuals",
            "all claims, invariants, defeaters, and residuals",
            1,
        )
        path.write_text(text, encoding="utf-8")
        code, out = run_validator(["self-check", "--repo-root", str(root)])
        self.assertEqual(code, 1, out)
        self.assertIn(
            "OpenDevs Agentic Assurance block differs from the normative "
            "verbatim block",
            out,
        )

        root = self.make_tmp()
        copy_self_check_fixture(root)
        path = root / "templates" / "AGENTS.md"
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r"))
        code, out = run_validator(["self-check", "--repo-root", str(root)])
        self.assertEqual(code, 1, out)
        self.assertNotIn(
            "OpenDevs block matches the normative", out
        )

        root = self.make_tmp()
        copy_self_check_fixture(root)
        for name in ("AGENTIC_ASSURANCE.md", "AGENTS.md"):
            path = root / "templates" / name
            raw = path.read_bytes()
            reading_order = b"Before any material change, read:\n\n1."
            self.assertIn(reading_order, raw)
            path.write_bytes(
                raw.replace(
                    reading_order,
                    b"Before any material change, read:\n\r1.",
                )
            )
        code, out = run_validator(["self-check", "--repo-root", str(root)])
        self.assertEqual(code, 1, out)
        self.assertIn("bare CR", out)

        root = self.make_tmp()
        copy_self_check_fixture(root)
        for name in ("AGENTIC_ASSURANCE.md", "AGENTS.md"):
            path = root / "templates" / name
            text = path.read_text(encoding="utf-8").replace(
                "Before any material change, read:",
                "Before changing anything, inspect:",
            )
            path.write_text(text, encoding="utf-8")
        code, out = run_validator(["self-check", "--repo-root", str(root)])
        self.assertEqual(code, 1, out)
        self.assertIn("canonical assurance reading order", out)


# ---------------------------------------------------------------------------
# 2. adopter baseline
# ---------------------------------------------------------------------------


class TestAdopterBaseline(ValidatorTestCase):
    def test_minimal_valid_split_core_adoption_passes(self):
        code, out = self.run_split(baseline_adoption(), baseline_registers())
        self.assertEqual(code, 0, out)
        self.assertIn("adoption file validates against adoption.schema.json", out)
        self.assertNotIn("ERROR:", out)

    def test_unusable_register_never_emits_semantic_success(self):
        root = self.make_tmp()
        adoption_path = build_split_project(
            root, baseline_adoption(), baseline_registers()
        )
        (root / REGISTER_FILES["invariants"]).write_text(
            "invariants: [\n", encoding="utf-8"
        )
        code, out = self.run_adopter(root, adoption_path)
        self.assertEqual(code, 1, out)
        self.assertIn("cannot parse", out)
        self.assertNotIn(
            "semantic checks — ids unique, references resolve, statuses grounded",
            out,
        )

    def test_full_declared_path_budget_does_not_count_implicit_defaults(self):
        adoption = baseline_adoption()
        adoption["paths"] = {
            f"custom_{index:03d}": f"policy/custom-{index:03d}.md"
            for index in range(256)
        }
        code, out = self.run_split(adoption, baseline_registers())
        self.assertEqual(code, 0, out)
        self.assertNotIn("mapping count exceeds", out)

    def test_git_backed_profile_checkout_must_match_declared_commit(self):
        root = self.make_tmp()
        checkout = root / "profile-checkout"
        init_git_test_repository(checkout)
        shutil.copytree(SCHEMAS_DIR, checkout / "schemas")
        (checkout / "scripts").mkdir()
        shutil.copy2(VALIDATOR, checkout / "scripts" / "validate.py")
        shutil.copy2(
            REPO_ROOT / "requirements-ci.txt", checkout / "requirements-ci.txt"
        )
        (checkout / "VERSION").write_text("v0.2.0\n", encoding="utf-8")
        actual_commit = commit_test_repository(checkout, "profile snapshot")

        project = root / "project"
        project.mkdir()
        adoption = baseline_adoption()
        adoption["upstream"]["commit"] = actual_commit
        adoption_path = build_split_project(
            project, adoption, baseline_registers()
        )
        args = [
            "adopter",
            "--adoption",
            str(adoption_path),
            "--project-root",
            str(project),
            "--schemas",
            str(checkout / "schemas"),
            "--profile-checkout",
            str(checkout),
        ]
        pinned_validator = checkout / "scripts" / "validate.py"
        code, out = run_validator(
            args, validator=pinned_validator, isolated=True
        )
        self.assertEqual(code, 0, out)
        self.assertIn(
            "pinned commit and consumed validation resources match", out
        )

        adoption["upstream"]["commit"] = "0" * 40
        write_yaml(adoption_path, adoption)
        code, out = run_validator(
            args, validator=pinned_validator, isolated=True
        )
        self.assertEqual(code, 1, out)
        self.assertIn("commit/checkout mismatch", out)
        self.assertIn(actual_commit, out)

        adoption["upstream"]["commit"] = actual_commit
        for relative, mutate in (
            (
                "VERSION",
                lambda path: path.write_text("v9.9.9\n", encoding="utf-8"),
            ),
            (
                "schemas/adoption.schema.json",
                lambda path: path.write_text(
                    path.read_text(encoding="utf-8") + "\n", encoding="utf-8"
                ),
            ),
            (
                "scripts/validate.py",
                lambda path: path.write_text(
                    path.read_text(encoding="utf-8") + "\n# dirty copy\n",
                    encoding="utf-8",
                ),
            ),
        ):
            with self.subTest(dirty_resource=relative):
                subprocess.run(
                    ["git", "checkout", "-q", "--", "."],
                    cwd=checkout,
                    check=True,
                )
                resource = checkout / relative
                mutate(resource)
                if relative == "VERSION":
                    adoption["upstream"]["version"] = "v9.9.9"
                else:
                    adoption["upstream"]["version"] = "v0.2.0"
                write_yaml(adoption_path, adoption)
                code, out = run_validator(
                    args, validator=pinned_validator, isolated=True
                )
                self.assertEqual(code, 1, out)
                self.assertIn(
                    "trusted validation resources differ from HEAD", out
                )

        for flag, clear_flag in (
            ("--assume-unchanged", "--no-assume-unchanged"),
            ("--skip-worktree", "--no-skip-worktree"),
        ):
            with self.subTest(hidden_index_flag=flag):
                subprocess.run(
                    ["git", "checkout", "-q", "--", "."],
                    cwd=checkout,
                    check=True,
                )
                subprocess.run(
                    ["git", "update-index", flag, "scripts/validate.py"],
                    cwd=checkout,
                    check=True,
                )
                pinned_validator.write_text(
                    pinned_validator.read_text(encoding="utf-8")
                    + "\n# hidden dirty copy\n",
                    encoding="utf-8",
                )
                adoption["upstream"]["version"] = "v0.2.0"
                write_yaml(adoption_path, adoption)
                code, out = run_validator(
                    args, validator=pinned_validator, isolated=True
                )
                self.assertEqual(code, 1, out)
                self.assertIn(
                    "assume-unchanged or skip-worktree index flags", out
                )
                subprocess.run(
                    ["git", "update-index", clear_flag, "scripts/validate.py"],
                    cwd=checkout,
                    check=True,
                )

        subprocess.run(
            ["git", "checkout", "-q", "--", "."], cwd=checkout, check=True
        )
        (checkout / "scripts" / "yaml.py").write_text(
            "raise RuntimeError('must never be imported')\n", encoding="utf-8"
        )
        adoption["upstream"]["version"] = "v0.2.0"
        write_yaml(adoption_path, adoption)
        code, out = run_validator(
            args, validator=pinned_validator, isolated=True
        )
        self.assertEqual(code, 1, out)
        self.assertIn("trusted validation resources differ from HEAD", out)
        self.assertNotIn("must never be imported", out)


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

    def test_date_placeholder_in_register_fails_at_human_reviewed(self):
        # An unfilled `review_after` date sentinel is a placeholder too — caught
        # at HUMAN_REVIEWED, like any REPLACE_WITH_ token.
        adoption = baseline_adoption()
        adoption["adoption_stage"] = "HUMAN_REVIEWED"
        adoption["human_review"] = human_review_block()
        registers = baseline_registers()
        registers["residuals"]["residuals"][0][
            "review_after"
        ] = "REPLACE_WITH_REVIEW_AFTER_DATE"
        code, out = self.run_split(adoption, registers)
        self.assertEqual(code, 1, out)
        self.assertIn("unfilled placeholder 'REPLACE_WITH_REVIEW_AFTER_DATE'", out)

    def test_date_placeholder_in_register_passes_at_draft(self):
        # DRAFT tolerates the date sentinel, exactly like REPLACE_WITH_.
        registers = baseline_registers()
        registers["residuals"]["residuals"][0][
            "review_after"
        ] = "REPLACE_WITH_REVIEW_AFTER_DATE"
        code, out = self.run_split(baseline_adoption(), registers)
        self.assertEqual(code, 0, out)

    def registers_with_legacy_review_dates(self):
        """Registers copied from the v0.3.x templates before the new sentinel."""
        registers = baseline_registers()
        registers["residuals"]["residuals"][0]["review_after"] = "YYYY-MM-DD"
        registers["defeaters"] = {
            "version": 1,
            "defeaters": [
                {
                    "id": "DEF-CORE-001",
                    "statement": "The example invariant may not cover every path",
                    "status": "OPEN",
                    "disclosure": "PUBLIC",
                    "owner": "Alice Example",
                    "review_after": "YYYY-MM-DD",
                }
            ],
        }
        return registers

    def test_legacy_date_placeholders_in_registers_pass_at_draft(self):
        # A v0.3.x adopter can upgrade its pin without first rewriting every
        # still-unfilled review date in its DRAFT registers.
        code, out = self.run_split(
            baseline_adoption(), self.registers_with_legacy_review_dates()
        )
        self.assertEqual(code, 0, out)

    def test_legacy_date_placeholders_in_registers_fail_at_human_reviewed(self):
        # Compatibility stops at the review boundary: both legacy register
        # paths are still recognized as unfilled placeholders.
        adoption = baseline_adoption()
        adoption["adoption_stage"] = "HUMAN_REVIEWED"
        adoption["human_review"] = human_review_block()
        code, out = self.run_split(
            adoption, self.registers_with_legacy_review_dates()
        )
        self.assertEqual(code, 1, out)
        self.assertIn("unfilled placeholder 'YYYY-MM-DD'", out)
        self.assertIn("$.residuals[0].review_after", out)
        self.assertIn("$.defeaters[0].review_after", out)

    def test_literal_yyyy_mm_dd_value_is_not_a_placeholder(self):
        # A literal "YYYY-MM-DD" string used as local data is not a placeholder,
        # even below a key named review_after. Cover both adoption extensions
        # and register-entry extensions at DRAFT and HUMAN_REVIEWED.
        for stage in ("DRAFT", "HUMAN_REVIEWED"):
            with self.subTest(stage=stage):
                adoption = baseline_adoption()
                adoption["extensions"] = {
                    "date_format": "YYYY-MM-DD",
                    "local_policy": {"review_after": "YYYY-MM-DD"},
                }
                if stage == "HUMAN_REVIEWED":
                    adoption["adoption_stage"] = stage
                    adoption["human_review"] = human_review_block()
                registers = baseline_registers()
                registers["residuals"]["residuals"][0]["local_metadata"] = {
                    "date_format": "YYYY-MM-DD",
                    "review_after": "YYYY-MM-DD",
                }
                code, out = self.run_split(adoption, registers)
                self.assertEqual(code, 0, out)

    def test_v03_bare_prompts_split_pass_draft_but_fail_human_reviewed(self):
        registers = registers_with_legacy_bare_prompts()
        code, out = self.run_split(baseline_adoption(), registers)
        self.assertEqual(code, 0, out)

        adoption = baseline_adoption()
        adoption["adoption_stage"] = "HUMAN_REVIEWED"
        adoption["human_review"] = human_review_block()
        code, out = self.run_split(adoption, registers)
        self.assertEqual(code, 1, out)
        for kind, fields in LEGACY_REGISTER_FIELD_PLACEHOLDERS.items():
            for field, prompt in fields.items():
                with self.subTest(kind=kind, field=field):
                    self.assertIn(
                        f"unfilled placeholder {prompt!r}",
                        out,
                    )
                    self.assertIn(f"$.{kind}[0].{field}", out)

    def test_v03_bare_prompts_lite_pass_draft_but_fail_human_reviewed(self):
        assurance = lite_assurance_with_legacy_bare_prompts()
        code, out = self.run_lite(baseline_lite_adoption(), assurance)
        self.assertEqual(code, 0, out)

        adoption = baseline_lite_adoption()
        adoption["adoption_stage"] = "HUMAN_REVIEWED"
        adoption["human_review"] = human_review_block()
        code, out = self.run_lite(adoption, assurance)
        self.assertEqual(code, 1, out)
        for kind in ("invariants", "defeaters", "residuals"):
            for field, prompt in LEGACY_REGISTER_FIELD_PLACEHOLDERS[kind].items():
                with self.subTest(kind=kind, field=field):
                    self.assertIn(f"unfilled placeholder {prompt!r}", out)
                    self.assertIn(f"$.{kind}[0].{field}", out)

    def test_v03_bare_prompts_fail_a_fully_conformant_fixture(self):
        adoption, _registers = conformant_fixture()
        registers = registers_with_legacy_bare_prompts()
        code, out = self.run_split(adoption, registers)
        self.assertEqual(code, 1, out)
        self.assertEqual(
            out.count("stage HUMAN_REVIEWED: unfilled placeholder 'Replace with"),
            7,
            out,
        )
        self.assertNotIn("stage CONFORMANT: requirements satisfied", out)

    def test_v03_bare_prompt_text_in_local_metadata_is_not_a_placeholder(self):
        # Exact legacy text is data everywhere except the seven released
        # register kind/direct-field paths.
        adoption = baseline_adoption()
        adoption["adoption_stage"] = "HUMAN_REVIEWED"
        adoption["human_review"] = human_review_block()
        all_prompts = [
            prompt
            for fields in LEGACY_REGISTER_FIELD_PLACEHOLDERS.values()
            for prompt in fields.values()
        ]
        adoption["extensions"] = {"legacy_prompt_examples": all_prompts}
        registers = baseline_registers()
        registers["residuals"]["residuals"][0]["local_metadata"] = {
            "legacy_prompt_examples": all_prompts,
            # Even a nested key matching a released direct field is local data.
            "summary": LEGACY_REGISTER_FIELD_PLACEHOLDERS["residuals"]["summary"],
        }
        code, out = self.run_split(adoption, registers)
        self.assertEqual(code, 0, out)
        self.assertNotIn("unfilled placeholder 'Replace with", out)


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
        # invariant and residual obligations (but still needs the mapped system
        # artifact) — pins the `any(profile != "archived")` scoping so a
        # mis-guard that demanded registers everywhere would be caught.
        adoption = baseline_adoption()
        adoption["profiles"] = ["archived"]
        code, out = self.run_split(adoption, {})
        self.assertEqual(code, 0, out)
        self.assertNotIn("ERROR:", out)
        self.assertNotIn("register is empty", out)

    def test_archived_without_system_fails(self):
        # Archived is exempt from invariants and residuals, but still needs a
        # mapped system artifact carrying all four section 6.6 facts.
        adoption = baseline_adoption()
        adoption["profiles"] = ["archived"]
        root = self.make_tmp()
        adoption_path = build_split_project(root, adoption, {})
        (root / "assurance" / "SYSTEM.md").unlink()
        code, out = self.run_adopter(root, adoption_path)
        self.assertEqual(code, 1, out)
        self.assertIn("SYSTEM.md missing", out)

    def test_archived_combined_with_active_profile_fails(self):
        # `archived` is exclusive: a repository with no active operation,
        # maintenance, or feature development cannot also declare an active
        # profile.
        adoption = baseline_adoption()
        adoption["profiles"] = ["core", "archived"]
        code, out = self.run_split(adoption, baseline_registers())
        self.assertEqual(code, 1, out)
        self.assertIn("'archived' cannot be combined", out)

    def test_invalid_archived_declarations_have_no_exclusivity_verdict(self):
        # The schema owns invalid declaration diagnostics. Exclusivity must
        # inspect the raw declaration, not a strings-only subset that could
        # turn [archived, 7] into a false success or duplicates into a derived
        # contradiction.
        for profiles in (
            ["archived", 7],
            ["archived", "archived"],
            ["archived", "not-a-profile"],
        ):
            with self.subTest(profiles=profiles):
                adoption = baseline_adoption()
                adoption["profiles"] = profiles
                code, out = self.run_split(adoption, {})
                self.assertEqual(code, 1, out)
                self.assertNotIn("profile 'archived' is declared exclusively", out)
                self.assertNotIn("'archived' cannot be combined", out)


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

    def test_empty_component_invariants_has_no_resolution_success(self):
        adoption = baseline_adoption()
        adoption["components"] = {
            "api": {"paths": ["src/**"], "invariants": []}
        }
        code, out = self.run_split(adoption, baseline_registers())
        self.assertEqual(code, 1, out)
        self.assertIn("$.components.api.invariants", out)
        self.assertNotIn(
            "component map: 1 component — every invariant reference resolves",
            out,
        )

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

    def test_restricted_record_is_a_bounded_non_actionable_identifier(self):
        for value in (
            "https://private.example/record?token=secret",
            "private/record",
            "owner@example.invalid",
            "private record",
            "x" * 129,
        ):
            with self.subTest(value=value):
                adoption = baseline_adoption()
                adoption["security"] = {"restricted_record": value}
                code, out = self.run_split(adoption, baseline_registers())
                self.assertEqual(code, 1, out)
                self.assertIn("$.security.restricted_record", out)

        adoption = baseline_adoption()
        adoption["security"] = {"restricted_record": "external_private_system"}
        code, out = self.run_split(adoption, baseline_registers())
        self.assertEqual(code, 0, out)

    def test_private_detail_location_is_a_bounded_non_actionable_identifier(self):
        invalid_values = (
            "https://private.example/record?token=secret",
            "private/record",
            "owner@example.invalid",
            "private record",
            "x" * 129,
        )
        for layout in ("split", "lite"):
            for value in invalid_values:
                with self.subTest(layout=layout, value=value):
                    if layout == "split":
                        registers = baseline_registers()
                        registers["residuals"]["residuals"][0][
                            "private_detail_location"
                        ] = value
                        code, out = self.run_split(
                            baseline_adoption(), registers
                        )
                    else:
                        assurance = baseline_lite_assurance()
                        assurance["residuals"][0]["private_detail_location"] = value
                        code, out = self.run_lite(
                            baseline_lite_adoption(), assurance
                        )
                    self.assertEqual(code, 1, out)
                    self.assertIn("private_detail_location", out)

        registers = baseline_registers()
        registers["residuals"]["residuals"][0][
            "private_detail_location"
        ] = "external_private_system"
        code, out = self.run_split(baseline_adoption(), registers)
        self.assertEqual(code, 0, out)

    def test_component_path_globs_are_nonblank_in_adopter_and_drift(self):
        adoption = baseline_adoption()
        adoption["components"] = {
            "app": {
                "paths": ["   "],
                "invariants": ["INV-CORE-001"],
            }
        }
        code, out = self.run_split(adoption, baseline_registers())
        self.assertEqual(code, 1, out)
        self.assertIn("$.components.app.paths[0]", out)

        code, out = self.run_drift(adoption, changed=())
        self.assertEqual(code, 1, out)
        self.assertIn("'paths' must be a non-empty list of glob strings", out)

    def test_component_path_globs_must_be_canonical_in_adopter_and_drift(self):
        malformed = (
            "../src/api/**",
            "/src/api/**",
            "./src/api/**",
            "src//api/**",
            "src/../src/api/**",
            "src/api/**/",
        )
        for path_glob in malformed:
            with self.subTest(path_glob=path_glob):
                adoption = baseline_adoption()
                adoption["components"] = {
                    "api": {
                        "paths": [path_glob],
                        "invariants": ["INV-CORE-001"],
                    }
                }
                code, out = self.run_split(adoption, baseline_registers())
                self.assertEqual(code, 1, out)
                self.assertIn("$.components.api.paths[0]", out)

                code, out = self.run_drift(
                    adoption,
                    changed=["src/api/handler.py"],
                    strict=True,
                )
                self.assertEqual(code, 1, out)
                self.assertIn("canonical repository-relative patterns", out)
                self.assertNotIn("no mapped component is touched", out)

    def test_component_routing_duplicates_keep_v03_compatibility(self):
        adoption = baseline_adoption()
        adoption["components"] = {
            "api": {
                "paths": ["src/api/**", "src/api/**"],
                "invariants": ["INV-CORE-001", "INV-CORE-001"],
            }
        }
        code, out = self.run_split(adoption, baseline_registers())
        self.assertEqual(code, 0, out)

        code, out = self.run_drift(
            adoption,
            changed=["src/api/handler.py"],
            body="Assurance impact: INV-CORE-001\n",
            strict=True,
        )
        self.assertEqual(code, 0, out)
        self.assertIn("component 'api' touched", out)

    def test_policy_path_mapping_count_and_length_are_bounded(self):
        too_many = baseline_adoption()
        too_many["paths"] = {
            f"local_{index}": f"policy/{index}.md" for index in range(257)
        }
        code, out = self.run_split(too_many, baseline_registers())
        self.assertEqual(code, 1, out)
        self.assertIn("has too many properties", out)
        code, out = self.run_drift(too_many, changed=())
        self.assertEqual(code, 1, out)
        self.assertIn("256-mapping resource limit", out)

        too_long = baseline_adoption()
        too_long["paths"] = {"system": "x" * 4097}
        code, out = self.run_split(too_long, baseline_registers())
        self.assertEqual(code, 1, out)
        self.assertIn("is too long", out)
        code, out = self.run_drift(too_long, changed=())
        self.assertEqual(code, 1, out)
        self.assertIn("4096 characters", out)

    def test_informational_component_test_globs_keep_v03_compatibility(self):
        adoption = baseline_adoption()
        adoption["components"] = {
            "api": {
                "paths": ["src/api/**"],
                "invariants": ["INV-CORE-001"],
                # `tests` is not consumed by routing in this release. Keep
                # its v0.3 string-array surface instead of imposing the
                # processed paths/invariants resource limits on inert data.
                "tests": ["tests/api/**"] * 256 + ["x" * 2_048],
            }
        }
        code, out = self.run_split(adoption, baseline_registers())
        self.assertEqual(code, 0, out)

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

    def test_every_accepted_residual_requires_a_complete_acceptance_record(self):
        complete = {
            "id": "RES-CORE-001",
            "summary": "Accepted low residual",
            "impact": "low",
            "uncertainty": "low",
            "status": "ACCEPTED",
            "disclosure": "PUBLIC",
            "owner": "Alice Example",
            "acceptance_rationale": "The bounded exposure is acceptable",
            "accepted_by": "Alice Example",
            "accepted_at": "2026-01-01",
        }
        for field in ("acceptance_rationale", "accepted_by", "accepted_at"):
            with self.subTest(field=field):
                residual = copy.deepcopy(complete)
                residual.pop(field)
                registers = baseline_registers()
                registers["residuals"]["residuals"] = [residual]
                code, out = self.run_split(baseline_adoption(), registers)
                self.assertEqual(code, 1, out)
                self.assertIn(field, out)

    def test_every_closed_defeater_requires_nonblank_resolution(self):
        base_entry = {
            "id": "DEF-CORE-001",
            "statement": "The guard may be bypassed on forks",
            "status": "OPEN",
            "disclosure": "PUBLIC",
            "owner": "Alice Example",
        }
        for status in ("MITIGATED", "RESOLVED", "WITHDRAWN"):
            for resolution in (None, "   "):
                with self.subTest(status=status, resolution=resolution):
                    entry = copy.deepcopy(base_entry)
                    entry["status"] = status
                    if resolution is not None:
                        entry["resolution"] = resolution
                    registers = baseline_registers()
                    registers["defeaters"] = {
                        "version": 1,
                        "defeaters": [entry],
                    }
                    code, out = self.run_split(baseline_adoption(), registers)
                    self.assertEqual(code, 1, out)
                    self.assertIn("resolution", out)

    def test_open_defeater_does_not_require_resolution(self):
        registers = baseline_registers()
        registers["defeaters"] = {
            "version": 1,
            "defeaters": [
                {
                    "id": "DEF-CORE-001",
                    "statement": "The guard may be bypassed on forks",
                    "status": "OPEN",
                    "disclosure": "PUBLIC",
                    "owner": "Alice Example",
                }
            ],
        }
        code, out = self.run_split(baseline_adoption(), registers)
        self.assertEqual(code, 0, out)

    def test_full_string_schema_tokens_reject_a_trailing_newline(self):
        _conformant_adoption, full_registers = conformant_fixture()

        def adoption_case(mutator):
            adoption = baseline_adoption()
            registers = copy.deepcopy(full_registers)
            mutator(adoption, registers)
            return self.run_split(adoption, registers)

        cases = {
            "upstream repository": lambda adoption, _registers: adoption[
                "upstream"
            ].__setitem__("repository", "example/assurance-profile\n"),
            "upstream commit": lambda adoption, _registers: adoption[
                "upstream"
            ].__setitem__("commit", "0" * 40 + "\n"),
            "project repository": lambda adoption, _registers: adoption[
                "project"
            ].__setitem__("repository", "example/project\n"),
            "claim id": lambda _adoption, registers: registers["claims"][
                "claims"
            ][0].__setitem__("id", "CLAIM-CORE-001\n"),
            "claim invariant reference": lambda _adoption, registers: registers[
                "claims"
            ]["claims"][0].__setitem__("invariants", ["INV-CORE-001\n"]),
            "invariant id": lambda _adoption, registers: registers["invariants"][
                "invariants"
            ][0].__setitem__("id", "INV-CORE-001\n"),
            "defeater id": lambda _adoption, registers: registers["defeaters"][
                "defeaters"
            ][0].__setitem__("id", "DEF-CORE-001\n"),
            "defeater claim reference": lambda _adoption, registers: registers[
                "defeaters"
            ]["defeaters"][0].__setitem__(
                "affected_claims", ["CLAIM-CORE-001\n"]
            ),
            "residual id": lambda _adoption, registers: registers["residuals"][
                "residuals"
            ][0].__setitem__("id", "RES-CORE-001\n"),
            "residual invariant reference": lambda _adoption, registers: registers[
                "residuals"
            ]["residuals"][0].__setitem__(
                "affected_invariants", ["INV-CORE-001\n"]
            ),
        }
        for label, mutate in cases.items():
            with self.subTest(token=label):
                code, out = adoption_case(mutate)
                self.assertEqual(code, 1, out)
                self.assertIn("does not match", out)


# ---------------------------------------------------------------------------
# 9. lite layout
# ---------------------------------------------------------------------------


class TestLiteLayout(ValidatorTestCase):
    def test_valid_lite_fixture_passes(self):
        code, out = self.run_lite(baseline_lite_adoption(), baseline_lite_assurance())
        self.assertEqual(code, 0, out)
        self.assertIn("layout 'lite' is declared with core-only profiles", out)
        self.assertNotIn("ERROR:", out)

    def test_unused_split_defaults_do_not_bind_lite_to_assurance_directory(self):
        root = self.make_tmp()
        adoption_path = build_lite_project(
            root, baseline_lite_adoption(), baseline_lite_assurance()
        )
        outside = self.make_tmp() / "outside-assurance"
        outside.mkdir()
        (root / "assurance").symlink_to(outside, target_is_directory=True)

        code, out = self.run_adopter(root, adoption_path)
        self.assertEqual(code, 0, out)
        self.assertNotIn("resolves outside the project root", out)

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
        self.assertIn("moving inline system into paths.system", out)
        self.assertIn("preserving purpose/non_goals", out)
        self.assertIn("extensions", out)
        self.assertIn("preserving IDs", out)

    def test_archived_profile_with_lite_fails(self):
        # Lite is core-only: `archived` (like any non-core profile) must use
        # the split layout — the lite schema's required fields are shaped for
        # core, not archived's PROFILE.md section 6.6 obligations.
        adoption = baseline_lite_adoption()
        adoption["profiles"] = ["archived"]
        code, out = self.run_lite(adoption, baseline_lite_assurance())
        self.assertEqual(code, 1, out)
        self.assertIn("layout 'lite' supports only the core profile", out)
        self.assertIn("four PROFILE.md section 6.6 facts", out)
        self.assertIn("optional history", out)
        self.assertIn("do not substitute", out)

    def test_templates_use_detectable_placeholder_sentinels(self):
        # Every fill-in field in the shipped assurance templates — lite and
        # split registers alike — must be a REPLACE_WITH_ sentinel, so an
        # adopter who leaves one is caught at HUMAN_REVIEWED. A bare "Replace
        # with ..." would pass that check silently (not a REPLACE_WITH_ token).
        for name in (
            "assurance.minimal.yaml",
            "assurance.yaml",
            "INVARIANTS.yaml",
            "RESIDUALS.yaml",
            "CLAIMS.yaml",
            "DEFEATERS.yaml",
        ):
            text = (REPO_ROOT / "templates" / name).read_text(encoding="utf-8")
            self.assertNotIn("Replace with ", text, name)

    def test_adoption_template_profiles_is_a_sentinel_not_a_core_default(self):
        # The copied adoption template must not ship `profiles: [core]` as a
        # concrete default (that nudges under-classification). It ships a
        # REPLACE_WITH_ sentinel — the central self-check substitutes it to a
        # valid enum, but an adopter must replace it with the classified set
        # (§4.0), so an unfilled copy fails validation.
        text = (REPO_ROOT / "templates" / "adoption.yaml").read_text(encoding="utf-8")
        self.assertIn("REPLACE_WITH_CLASSIFIED_PROFILE", text)
        self.assertNotIn("\n  - core\n", text)

    def test_adoption_with_unfilled_profile_sentinel_fails(self):
        # An adopter who copies the template and leaves the profile sentinel
        # fails — the completion guard that stops a silent `core` default.
        adoption = baseline_adoption()
        adoption["profiles"] = ["REPLACE_WITH_CLASSIFIED_PROFILE"]
        code, out = self.run_split(adoption, baseline_registers())
        self.assertEqual(code, 1, out)
        self.assertIn("unfilled placeholder 'REPLACE_WITH_CLASSIFIED_PROFILE'", out)

    def test_profile_sentinel_under_lite_does_not_advise_split(self):
        # The profile sentinel is a placeholder, not a real non-core profile,
        # so lite must not tell the adopter to "graduate to the split layout"
        # (they may well be classifying as core).
        adoption = baseline_lite_adoption()
        adoption["profiles"] = ["REPLACE_WITH_CLASSIFIED_PROFILE"]
        code, out = self.run_lite(adoption, baseline_lite_assurance())
        self.assertEqual(code, 1, out)
        self.assertIn("unfilled placeholder 'REPLACE_WITH_CLASSIFIED_PROFILE'", out)
        self.assertNotIn("graduate to the split layout", out)
        self.assertNotIn("layout 'lite' is declared with core-only profiles", out)

    def test_invalid_profile_declarations_under_lite_have_no_layout_verdict(self):
        # The adoption schema owns malformed profile diagnostics. The layout
        # checker must neither report core-only success nor advise a split for
        # an empty, unknown, duplicate, or non-string declaration.
        for profiles in ([], ["bogus"], ["core", "core"], ["core", 7]):
            with self.subTest(profiles=profiles):
                adoption = baseline_lite_adoption()
                adoption["profiles"] = profiles
                code, out = self.run_lite(adoption, baseline_lite_assurance())
                self.assertEqual(code, 1, out)
                self.assertNotIn(
                    "layout 'lite' is declared with core-only profiles", out
                )
                self.assertNotIn("layout 'lite' supports only the core profile", out)

    def test_legacy_review_date_in_lite_passes_at_draft(self):
        assurance = baseline_lite_assurance()
        assurance["residuals"][0]["review_after"] = "YYYY-MM-DD"
        code, out = self.run_lite(baseline_lite_adoption(), assurance)
        self.assertEqual(code, 0, out)

    def test_legacy_review_date_in_lite_fails_at_human_reviewed(self):
        adoption = baseline_lite_adoption()
        adoption["adoption_stage"] = "HUMAN_REVIEWED"
        adoption["human_review"] = human_review_block()
        assurance = baseline_lite_assurance()
        assurance["residuals"][0]["review_after"] = "YYYY-MM-DD"
        code, out = self.run_lite(adoption, assurance)
        self.assertEqual(code, 1, out)
        self.assertIn("unfilled placeholder 'YYYY-MM-DD'", out)
        self.assertIn("$.residuals[0].review_after", out)

    def test_archived_profile_emits_section_6_6_warning(self):
        adoption = baseline_adoption()
        adoption["profiles"] = ["archived"]
        code, out = self.run_split(adoption, {})
        self.assertEqual(code, 0, out)
        self.assertIn("WARN", out)
        self.assertIn("section 6.6", out)

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
            assurance_diff=(
                "diff --git a/assurance/INVARIANTS.yaml "
                "b/assurance/INVARIANTS.yaml\n"
                "--- a/assurance/INVARIANTS.yaml\n"
                "+++ b/assurance/INVARIANTS.yaml\n"
                "@@ -1 +1 @@\n"
                "-  evidence: old run\n"
                "+  evidence updated for INV-CORE-001\n"
            ),
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
                "diff --git a/assurance/INVARIANTS.yaml "
                "b/assurance/INVARIANTS.yaml\n"
                "--- a/assurance/INVARIANTS.yaml\n"
                "+++ b/assurance/INVARIANTS.yaml\n"
                "@@ -1,2 +1,4 @@\n"
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
            assurance_diff=(
                "diff --git a/assurance/INVARIANTS.yaml "
                "b/assurance/INVARIANTS.yaml\n"
                "--- a/assurance/INVARIANTS.yaml\n"
                "+++ b/assurance/INVARIANTS.yaml\n"
                "@@ -1,2 +0,0 @@\n"
                "-  - id: INV-CORE-001\n"
                "-    statement: removed\n"
            ),
        )
        self.assertEqual(code, 0, out)
        self.assertIn("without an assurance update", out)

    def test_assurance_diff_nested_longer_id_does_not_satisfy(self):
        # INV-CORE-001-EXT-002 is a valid ID that contains INV-CORE-001 as a
        # substring; token-boundary matching must not let it satisfy.
        code, out = self.run_drift(
            drift_adoption(),
            changed=["src/api/handler.py"],
            assurance_diff=(
                "diff --git a/assurance/INVARIANTS.yaml "
                "b/assurance/INVARIANTS.yaml\n"
                "--- a/assurance/INVARIANTS.yaml\n"
                "+++ b/assurance/INVARIANTS.yaml\n"
                "@@ -1 +1 @@\n"
                "-  - id: INV-OLD-001\n"
                "+  - id: INV-CORE-001-EXT-002\n"
            ),
        )
        self.assertEqual(code, 0, out)
        self.assertIn("without an assurance update", out)

    def test_assurance_diff_without_reference_warns(self):
        code, out = self.run_drift(
            drift_adoption(),
            changed=["src/api/handler.py"],
            assurance_diff=(
                "diff --git a/assurance/INVARIANTS.yaml "
                "b/assurance/INVARIANTS.yaml\n"
                "--- a/assurance/INVARIANTS.yaml\n"
                "+++ b/assurance/INVARIANTS.yaml\n"
                "@@ -1 +1 @@\n"
                "-  old text\n"
                "+  unrelated edit\n"
            ),
        )
        self.assertEqual(code, 0, out)
        self.assertIn("WARN:", out)
        self.assertIn("without an assurance update", out)

    def test_assurance_diff_without_reference_strict_fails(self):
        code, out = self.run_drift(
            drift_adoption(),
            changed=["src/api/handler.py"],
            assurance_diff=(
                "diff --git a/assurance/INVARIANTS.yaml "
                "b/assurance/INVARIANTS.yaml\n"
                "--- a/assurance/INVARIANTS.yaml\n"
                "+++ b/assurance/INVARIANTS.yaml\n"
                "@@ -1 +1 @@\n"
                "-  old text\n"
                "+  unrelated edit\n"
            ),
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

    def test_pr_body_explicit_impact_ids_satisfy(self):
        code, out = self.run_drift(
            drift_adoption(),
            changed=["src/api/handler.py"],
            body="Assurance impact: INV-CORE-001\n",
        )
        self.assertEqual(code, 0, out)
        self.assertIn("INV-CORE-001", out)

    def test_pr_body_nested_longer_id_does_not_satisfy(self):
        code, out = self.run_drift(
            drift_adoption(),
            changed=["src/api/handler.py"],
            body="Assurance impact: INV-CORE-001-EXT-002\n",
            strict=True,
        )
        self.assertEqual(code, 1, out)
        self.assertIn("without an assurance update", out)

    def test_assurance_diff_symlink_blob_cannot_supply_invariant_evidence(self):
        adoption = baseline_adoption()
        adoption["components"] = {
            "api": {
                "paths": ["src/api/**"],
                "invariants": ["INV-CORE-001"],
            }
        }
        code, out = self.run_drift(
            adoption,
            changed=["src/api/handler.py"],
            assurance_diff=(
                "diff --git a/assurance/SYSTEM.md b/assurance/SYSTEM.md\n"
                "new file mode 120000\n"
                "index 0000000..1111111\n"
                "--- /dev/null\n"
                "+++ b/assurance/SYSTEM.md\n"
                "@@ -0,0 +1 @@\n"
                "+../policy/INV-CORE-001.md\n"
            ),
            strict=True,
        )
        self.assertEqual(code, 1, out)
        self.assertIn("without an assurance update", out)
        self.assertNotIn("assurance update references INV-CORE-001", out)

    def test_assurance_diff_exact_deleted_line_cancels_added_move(self):
        adoption = baseline_adoption()
        adoption["components"] = {
            "api": {
                "paths": ["src/api/**"],
                "invariants": ["INV-CORE-001"],
            }
        }
        code, out = self.run_drift(
            adoption,
            changed=["src/api/handler.py"],
            assurance_diff=(
                "diff --git a/policy/old.md b/policy/old.md\n"
                "deleted file mode 100644\n"
                "--- a/policy/old.md\n"
                "+++ /dev/null\n"
                "@@ -1 +0,0 @@\n"
                "-Existing INV-CORE-001 policy line\n"
                "diff --git a/policy/new.md b/policy/new.md\n"
                "new file mode 100644\n"
                "--- /dev/null\n"
                "+++ b/policy/new.md\n"
                "@@ -0,0 +1 @@\n"
                "+Existing INV-CORE-001 policy line\n"
            ),
            strict=True,
        )
        self.assertEqual(code, 1, out)
        self.assertIn("without an assurance update", out)

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

    def test_no_impact_with_reason_accepts_crlf_body(self):
        code, out = self.run_drift(
            drift_adoption(),
            changed=["src/api/handler.py"],
            body="Assurance impact: none\r\nReason: comment-only change\r\n",
        )
        self.assertEqual(code, 0, out)
        self.assertIn("declares 'Assurance impact: none' with a reason", out)

    def test_no_impact_declaration_and_reason_are_exact_same_line_forms(self):
        bodies = (
            "Assurance impact: nonetheless\nReason: unrelated\n",
            "Assurance impact: none\nReason:\n# unrelated heading\n",
        )
        for body in bodies:
            with self.subTest(body=body):
                code, out = self.run_drift(
                    drift_adoption(),
                    changed=["src/api/handler.py"],
                    body=body,
                    strict=True,
                )
                self.assertEqual(code, 1, out)
                self.assertIn("without an assurance update", out)

    def test_leading_directives_must_follow_the_published_order(self):
        invalid_bodies = {
            "reason before impact": (
                "Reason: no effect\nAssurance impact: none\n"
            ),
            "policy before positive impact": (
                "Assurance policy change: deliberate update\n"
                "Assurance impact: INV-CORE-001\n"
            ),
            "policy before no-impact reason": (
                "Assurance impact: none\n"
                "Assurance policy change: deliberate update\n"
                "Reason: no effect\n"
            ),
            "reason after positive impact": (
                "Assurance impact: INV-CORE-001\nReason: stray reason\n"
            ),
        }
        for label, body in invalid_bodies.items():
            with self.subTest(label=label):
                code, out = self.run_drift(
                    drift_adoption(),
                    changed=["src/api/handler.py"],
                    body=body,
                    strict=True,
                )
                self.assertEqual(code, 1, out)
                self.assertIn("out of contract order", out)
                self.assertIn("without an assurance update", out)

    def test_combined_impact_reason_and_policy_sequences_remain_valid(self):
        valid_bodies = (
            (
                "Assurance impact: INV-CORE-001\n"
                "Assurance policy change: deliberate update\n"
            ),
            (
                "Assurance impact: none\n"
                "Reason: mapped invariant is unaffected\n"
                "Assurance policy change: deliberate update\n"
            ),
        )
        for body in valid_bodies:
            with self.subTest(body=body):
                code, out = self.run_drift(
                    drift_adoption(),
                    changed=["src/api/handler.py"],
                    body=body,
                    strict=True,
                )
                self.assertEqual(code, 0, out)

    def test_rename_source_path_triggers_component(self):
        # Rename semantics are computed by the CI caller, which lists both the
        # rename source and the destination in the changed-files list. The
        # validator treats each listed path independently, so a rename OUT of
        # a mapped component still routes: the source path matches the glob.
        code, out = self.run_drift(
            drift_adoption(),
            changed=["src/api/old_name.py", "src/relocated/new_name.py"],
            body="Assurance impact: INV-CORE-001\n",
        )
        self.assertEqual(code, 0, out)
        self.assertIn("component 'api' touched (1 changed file)", out)

    def test_nul_changed_paths_preserve_newlines_and_edge_spaces(self):
        adoption = baseline_adoption()
        adoption["components"] = {
            "unusual": {
                # Literal C0 controls are outside the schema's glob syntax,
                # but `?` still addresses the legal newline in a Git path.
                "paths": [" leading.txt", "src/line?break.py", "trailing.txt "],
                "invariants": ["INV-CORE-001"],
            }
        }
        code, out = self.run_drift(
            adoption,
            changed=[" leading.txt", "src/line\nbreak.py", "trailing.txt "],
            changed_nul=True,
            body="Assurance impact: INV-CORE-001\n",
        )
        self.assertEqual(code, 0, out)
        self.assertIn("component 'unusual' touched (3 changed files)", out)

    def test_path_glob_subset_matches_entire_paths(self):
        adoption = baseline_adoption()
        adoption["components"] = {
            "matcher": {
                "paths": [
                    "src/**/handler?.py",
                    "literal/[x].txt",
                    "assets/**",
                    "single/*.txt",
                ],
                "invariants": ["INV-CORE-001"],
            }
        }
        code, out = self.run_drift(
            adoption,
            changed=[
                "src/handler1.py",
                "src/a/b/handlerx.py",
                "literal/[x].txt",
                "assets/deep/image.png",
                "single/one.txt",
                "single/nested/two.txt",
                "src/a/handler-long.py",
            ],
            body="Assurance impact: INV-CORE-001\n",
        )
        self.assertEqual(code, 0, out)
        self.assertIn("component 'matcher' touched (5 changed files)", out)

    def test_overlapping_globstars_cannot_trigger_regex_backtracking(self):
        adoption = baseline_adoption()
        adoption["components"] = {
            "matcher": {
                "paths": [("**a" * 32) + "b"],
                "invariants": ["INV-CORE-001"],
            }
        }
        try:
            code, out = self.run_drift(
                adoption,
                changed=[("a" * 32) + "c"],
                timeout=3,
            )
        except subprocess.TimeoutExpired as exc:
            self.fail(f"path-glob near miss exceeded the bounded runtime: {exc}")
        self.assertEqual(code, 0, out)
        self.assertIn("no mapped component is touched", out)

    def test_drift_rejects_overlong_globs_and_changed_paths(self):
        adoption = baseline_adoption()
        adoption["components"] = {
            "matcher": {
                "paths": ["a" * 1025],
                "invariants": ["INV-CORE-001"],
            }
        }
        code, out = self.run_drift(adoption, changed=["short.txt"])
        self.assertEqual(code, 1, out)
        self.assertIn("1024-character limit", out)

        adoption["components"]["matcher"]["paths"] = ["**"]
        code, out = self.run_drift(adoption, changed=["a" * 4097])
        self.assertEqual(code, 1, out)
        self.assertIn("4096-character changed-path limit", out)

    def test_drift_rejects_noncanonical_repository_changed_paths(self):
        malformed = (
            "../src/api/handler.py",
            "/src/api/handler.py",
            "src/api/../api/handler.py",
            "././src/api/handler.py",
            "src//api/handler.py",
        )
        for changed_path in malformed:
            with self.subTest(changed_path=changed_path):
                code, out = self.run_drift(
                    drift_adoption(),
                    changed=[changed_path],
                    strict=True,
                )
                self.assertEqual(code, 1, out)
                self.assertIn(
                    "not a canonical repository-relative Git path", out
                )
                self.assertNotIn("no mapped component is touched", out)

        # Preserve the documented legacy convenience spelling while making
        # repeated prefixes fail instead of silently missing the component.
        code, out = self.run_drift(
            drift_adoption(),
            changed=["./src/api/handler.py"],
            body="Assurance impact: INV-CORE-001\n",
            strict=True,
        )
        self.assertEqual(code, 0, out)
        self.assertIn("component 'api' touched", out)


# ---------------------------------------------------------------------------
# 8. drift policy regression (--base-adoption)
# ---------------------------------------------------------------------------


def regression_base_adoption():
    adoption = baseline_adoption()
    adoption["adoption_stage"] = "CONFORMANT"
    adoption["human_review"] = human_review_block()
    adoption["human_review"]["approvals"] = [
        {
            "approver": "bob-reviewer",
            "review_url": "https://example.invalid/reviews/1",
            "at": "2026-01-02",
        }
    ]
    adoption["security"] = {
        "policy": "SECURITY.md",
        "public_assurance_root": "assurance",
        "restricted_record": "external_private_system",
    }
    adoption["issue_integration"] = {
        "stable_id_required": True,
        "public_security_issues_allowed": False,
        "closing_requires_artifact_update": True,
    }
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

    def test_policy_change_acknowledgment_accepts_crlf_body(self):
        base = baseline_adoption()
        base["components"] = {
            "api": {
                "paths": ["src/api/**"],
                "invariants": ["INV-CORE-001"],
            }
        }
        head = copy.deepcopy(base)
        del head["components"]
        code, out = self.run_drift(
            head,
            changed=(),
            body="Assurance policy change: deliberate removal\r\n",
            base_adoption=base,
        )
        self.assertEqual(code, 0, out)
        self.assertIn("acknowledged", out)

    def test_empty_policy_change_line_cannot_consume_later_prose(self):
        base = baseline_adoption()
        base["components"] = {
            "api": {
                "paths": ["src/api/**"],
                "invariants": ["INV-CORE-001"],
            }
        }
        head = copy.deepcopy(base)
        del head["components"]
        code, out = self.run_drift(
            head,
            changed=(),
            body="Assurance policy change:\n# unrelated heading\n",
            base_adoption=base,
        )
        self.assertEqual(code, 1, out)
        self.assertIn("requires an explicit 'Assurance policy change:", out)
        self.assertNotIn("acknowledged by", out)

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

    def test_adoption_declaration_move_is_a_policy_change(self):
        base = baseline_adoption()
        head = copy.deepcopy(base)
        code, out = self.run_drift(
            head,
            changed=(),
            base_adoption=base,
            adoption_paths=(
                ".agentic-assurance/adoption.yaml",
                "config/adoption-policy.conf",
            ),
        )
        self.assertEqual(code, 1, out)
        self.assertIn("adoption declaration path changed", out)

        code, out = self.run_drift(
            head,
            changed=(),
            body="Assurance policy change: move under equivalent owner controls\n",
            base_adoption=base,
            adoption_paths=(
                ".agentic-assurance/adoption.yaml",
                "config/adoption-policy.conf",
            ),
        )
        self.assertEqual(code, 0, out)
        self.assertIn("acknowledged by 'Assurance policy change:'", out)

    def test_lexically_equivalent_adoption_paths_are_not_a_move(self):
        base = baseline_adoption()
        code, out = self.run_drift(
            copy.deepcopy(base),
            changed=(),
            base_adoption=base,
            adoption_paths=(
                ".agentic-assurance/adoption.yaml",
                "config/../.agentic-assurance/adoption.yaml",
            ),
        )
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

    def test_committed_project_identity_changes_fail(self):
        for field, value in (("name", "Other Project"), ("repository", "other/repo")):
            with self.subTest(field=field):
                code, out = self.run_regression(
                    lambda head, f=field, v=value: head["project"].__setitem__(f, v)
                )
                self.assertEqual(code, 1, out)
                self.assertIn(f"project.{field} changed", out)

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

    def test_human_review_date_regression_removal_or_invalid_value_fails(self):
        for value in ("2025-12-31", None, "not-a-date"):
            with self.subTest(value=value):
                def mutate(head, replacement=value):
                    if replacement is None:
                        head["human_review"].pop("date")
                    else:
                        head["human_review"]["date"] = replacement

                code, out = self.run_regression(mutate)
                self.assertEqual(code, 1, out)
                self.assertIn("human_review.date regressed", out)

    def test_review_approval_provenance_removal_or_rewrite_fails(self):
        for mutation in ("remove", "approver", "review_url", "at"):
            with self.subTest(mutation=mutation):
                def mutate(head):
                    approvals = head["human_review"]["approvals"]
                    if mutation == "remove":
                        approvals.clear()
                    else:
                        replacements = {
                            "approver": "other-reviewer",
                            "review_url": "https://example.invalid/reviews/other",
                            "at": "2026-01-03",
                        }
                        approvals[0][mutation] = replacements[mutation]

                code, out = self.run_regression(mutate)
                self.assertEqual(code, 1, out)
                self.assertIn("approval provenance removed or rewritten", out)

    def test_review_approval_scope_rewrite_fails(self):
        for base_covers, head_covers in (
            (None, ["INV-CORE-001"]),
            (["CONFORMANCE", "INV-CORE-001"], ["INV-CORE-001"]),
            (["INV-CORE-001"], ["CONFORMANCE", "INV-CORE-001"]),
        ):
            with self.subTest(base_covers=base_covers, head_covers=head_covers):
                base = regression_base_adoption()
                base["human_review"]["approvals"].append(
                    {
                        "approver": "second-reviewer",
                        "review_url": "https://example.invalid/reviews/2",
                        "at": "2026-01-03",
                    }
                )
                approval = base["human_review"]["approvals"][0]
                if base_covers is not None:
                    approval["covers"] = base_covers
                head = copy.deepcopy(base)
                head["human_review"]["approvals"][0]["covers"] = head_covers

                code, out = self.run_drift(
                    head, changed=(), base_adoption=base
                )
                self.assertEqual(code, 1, out)
                self.assertIn("approval provenance removed or rewritten", out)
                self.assertIn("covers=", out)

    def test_explicit_full_approval_token_equals_omitted_scope(self):
        base = regression_base_adoption()
        head = copy.deepcopy(base)
        head["human_review"]["approvals"][0]["covers"] = ["CONFORMANCE"]
        code, out = self.run_drift(head, changed=(), base_adoption=base)
        self.assertEqual(code, 0, out)
        self.assertIn("no assurance policy regression", out)

    def test_adding_review_approval_provenance_is_not_a_regression(self):
        def mutate(head):
            head["human_review"]["approvals"].append(
                {
                    "approver": "second-reviewer",
                    "review_url": "https://example.invalid/reviews/2",
                    "at": "2026-01-03",
                }
            )

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

    def test_explicit_and_implicit_default_paths_are_equivalent(self):
        for explicit_on_head in (True, False):
            with self.subTest(explicit_on_head=explicit_on_head):
                base = regression_base_adoption()
                head = copy.deepcopy(base)
                target = head if explicit_on_head else base
                target["paths"] = {"system": "assurance/SYSTEM.md"}
                code, out = self.run_drift(
                    head, changed=(), base_adoption=base
                )
                self.assertEqual(code, 0, out)
                self.assertIn("no assurance policy regression", out)

    def test_lexically_equivalent_artifact_paths_are_not_regressions(self):
        for equivalent in (
            "./assurance/SYSTEM.md",
            "docs/../assurance/SYSTEM.md",
        ):
            with self.subTest(equivalent=equivalent):
                base = regression_base_adoption()
                head = copy.deepcopy(base)
                base["paths"] = {"system": "assurance/SYSTEM.md"}
                head["paths"] = {"system": equivalent}
                code, out = self.run_drift(
                    head, changed=(), base_adoption=base
                )
                self.assertEqual(code, 0, out)
                self.assertIn("no assurance policy regression", out)

    def test_extension_path_addition_is_neutral_but_removal_is_protected(self):
        base = regression_base_adoption()
        head = copy.deepcopy(base)
        head["paths"] = {"local_evidence_index": "docs/evidence-index.md"}
        code, out = self.run_drift(head, changed=(), base_adoption=base)
        self.assertEqual(code, 0, out)

        base, head = head, copy.deepcopy(head)
        del head["paths"]
        code, out = self.run_drift(head, changed=(), base_adoption=base)
        self.assertEqual(code, 1, out)
        self.assertIn("paths.local_evidence_index changed", out)

    def test_lite_dormant_path_addition_is_neutral_but_declared_base_is_protected(self):
        base = baseline_lite_adoption()
        head = copy.deepcopy(base)
        head["paths"] = {"invariants": "policy/INVARIANTS.yaml"}
        assurance = baseline_lite_assurance()
        code, out = self.run_drift(
            head,
            changed=(),
            base_adoption=base,
            base_lite_assurance=assurance,
            head_lite_assurance=assurance,
        )
        self.assertEqual(code, 0, out)
        self.assertIn("no assurance policy regression", out)

        base, head = head, copy.deepcopy(head)
        head["paths"]["invariants"] = "policy/OTHER.yaml"
        code, out = self.run_drift(
            head,
            changed=(),
            base_adoption=base,
            base_lite_assurance=assurance,
            head_lite_assurance=assurance,
        )
        self.assertEqual(code, 1, out)
        self.assertIn("paths.invariants changed", out)

    def test_lite_active_fallback_system_path_change_is_protected(self):
        base = baseline_lite_adoption()
        head = copy.deepcopy(base)
        head["paths"] = {"system": "docs/SYSTEM.md"}
        assurance = baseline_lite_assurance()
        assurance.pop("system")
        code, out = self.run_drift(
            head,
            changed=(),
            base_adoption=base,
            base_lite_assurance=assurance,
            head_lite_assurance=assurance,
        )
        self.assertEqual(code, 1, out)
        self.assertIn("paths.system changed", out)

    def test_lite_inline_system_relocation_to_fallback_is_protected(self):
        base = baseline_lite_adoption()
        head = copy.deepcopy(base)
        head["paths"] = {"system": "docs/new-system.md"}
        base_assurance = baseline_lite_assurance()
        head_assurance = copy.deepcopy(base_assurance)
        head_assurance.pop("system")

        def write_head_system(root):
            path = root / "docs" / "new-system.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# Relocated system\n", encoding="utf-8")

        code, out = self.run_drift(
            head,
            changed=(),
            base_adoption=base,
            base_lite_assurance=base_assurance,
            head_lite_assurance=head_assurance,
            head_root_setup=write_head_system,
        )
        self.assertEqual(code, 1, out)
        self.assertIn("lite system source changed", out)
        self.assertIn("inline", out)
        self.assertIn("docs/new-system.md", out)

    def test_lite_fallback_system_relocation_to_inline_is_protected(self):
        base = baseline_lite_adoption()
        base["paths"] = {"system": "docs/system.md"}
        head = copy.deepcopy(base)
        base_assurance = baseline_lite_assurance()
        base_assurance.pop("system")
        head_assurance = copy.deepcopy(base_assurance)
        head_assurance["system"] = "Now supplied inline"

        def write_mapped_system(root):
            path = root / "docs" / "system.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# Mapped system\n", encoding="utf-8")

        code, out = self.run_drift(
            head,
            changed=(),
            base_adoption=base,
            base_lite_assurance=base_assurance,
            head_lite_assurance=head_assurance,
            base_root_setup=write_mapped_system,
            head_root_setup=write_mapped_system,
        )
        self.assertEqual(code, 1, out)
        self.assertIn("lite system source changed", out)
        self.assertIn("docs/system.md", out)
        self.assertIn("inline", out)

    def test_register_policy_roots_must_be_supplied_as_a_pair(self):
        root = self.make_tmp()
        adoption = baseline_lite_adoption()
        write_yaml(root / "adoption.yaml", adoption)
        write_yaml(root / "base-adoption.yaml", adoption)
        (root / "changed.txt").write_text("", encoding="utf-8")
        base_root = root / "base-root"
        head_root = root / "head-root"
        write_yaml(base_root / LITE_ASSURANCE_PATH, baseline_lite_assurance())
        write_yaml(head_root / LITE_ASSURANCE_PATH, baseline_lite_assurance())
        common = [
            "drift",
            "--adoption",
            str(root / "adoption.yaml"),
            "--changed-files",
            str(root / "changed.txt"),
            "--pr-body",
            str(root / "missing-body.txt"),
            "--base-adoption",
            str(root / "base-adoption.yaml"),
        ]
        for lone_flag, lone_root in (
            ("--base-registers-root", base_root),
            ("--project-root", head_root),
        ):
            with self.subTest(lone_flag=lone_flag):
                code, out = run_validator(common + [lone_flag, str(lone_root)])
                self.assertEqual(code, 1, out)
                self.assertIn("must be supplied together", out)

    def test_register_policy_roots_require_base_adoption(self):
        root = self.make_tmp()
        adoption = baseline_lite_adoption()
        write_yaml(root / "adoption.yaml", adoption)
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
                "--base-registers-root",
                str(root / "base-root"),
                "--project-root",
                str(root / "head-root"),
            ]
        )
        self.assertEqual(code, 1, out)
        self.assertIn("require --base-adoption", out)

    def test_register_policy_roots_must_exist_be_directories_and_be_distinct(self):
        root = self.make_tmp()
        adoption = baseline_lite_adoption()
        write_yaml(root / "adoption.yaml", adoption)
        write_yaml(root / "base-adoption.yaml", adoption)
        (root / "changed.txt").write_text("", encoding="utf-8")
        common = [
            "drift",
            "--adoption",
            str(root / "adoption.yaml"),
            "--changed-files",
            str(root / "changed.txt"),
            "--pr-body",
            str(root / "missing-body.txt"),
            "--base-adoption",
            str(root / "base-adoption.yaml"),
        ]

        code, out = run_validator(
            common
            + [
                "--base-registers-root",
                str(root / "missing-base"),
                "--project-root",
                str(root / "missing-head"),
            ]
        )
        self.assertEqual(code, 1, out)
        self.assertIn("cannot be resolved", out)

        base_file = root / "base-file"
        head_file = root / "head-file"
        base_file.write_text("not a directory\n", encoding="utf-8")
        head_file.write_text("not a directory\n", encoding="utf-8")
        code, out = run_validator(
            common
            + [
                "--base-registers-root",
                str(base_file),
                "--project-root",
                str(head_file),
            ]
        )
        self.assertEqual(code, 1, out)
        self.assertIn("must resolve to an existing directory", out)

        shared = root / "shared-root"
        shared.mkdir()
        alias = root / "shared-alias"
        alias.symlink_to(shared, target_is_directory=True)
        for head_spelling in (shared, alias):
            with self.subTest(head_spelling=head_spelling.name):
                code, out = run_validator(
                    common
                    + [
                        "--base-registers-root",
                        str(shared),
                        "--project-root",
                        str(head_spelling),
                    ]
                )
                self.assertEqual(code, 1, out)
                self.assertIn("must resolve to distinct directories", out)

        nested = shared / "nested-head"
        nested.mkdir()
        code, out = run_validator(
            common
            + [
                "--base-registers-root",
                str(shared),
                "--project-root",
                str(nested),
            ]
        )
        self.assertEqual(code, 1, out)
        self.assertIn("ancestor/descendant overlap", out)

    def test_lite_target_binding_ignores_defaults_but_keeps_declared_paths(self):
        inline = baseline_lite_assurance()

        def setup_link(root, relative, target_name):
            target = root / "targets" / target_name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("policy target\n", encoding="utf-8")
            link = root / relative
            link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(os.path.relpath(target, link.parent))

        base = baseline_lite_adoption()
        head = copy.deepcopy(base)
        code, out = self.run_drift(
            head,
            changed=(),
            base_adoption=base,
            base_lite_assurance=inline,
            head_lite_assurance=inline,
            base_root_setup=lambda root: setup_link(
                root, "assurance/SYSTEM.md", "base-system.md"
            ),
            head_root_setup=lambda root: setup_link(
                root, "assurance/SYSTEM.md", "head-system.md"
            ),
        )
        self.assertEqual(code, 0, out)
        self.assertNotIn("paths.system resolved target changed", out)

        base["paths"] = {"invariants": "policy/INVARIANTS.yaml"}
        head = copy.deepcopy(base)
        code, out = self.run_drift(
            head,
            changed=(),
            base_adoption=base,
            base_lite_assurance=inline,
            head_lite_assurance=inline,
            base_root_setup=lambda root: setup_link(
                root, "policy/INVARIANTS.yaml", "base-invariants.yaml"
            ),
            head_root_setup=lambda root: setup_link(
                root, "policy/INVARIANTS.yaml", "head-invariants.yaml"
            ),
        )
        self.assertEqual(code, 1, out)
        self.assertIn("paths.invariants resolved target changed", out)

        fallback = baseline_lite_assurance()
        fallback.pop("system")
        base = baseline_lite_adoption()
        base["paths"] = {"system": "policy/SYSTEM.md"}
        head = copy.deepcopy(base)
        code, out = self.run_drift(
            head,
            changed=(),
            base_adoption=base,
            base_lite_assurance=fallback,
            head_lite_assurance=fallback,
            base_root_setup=lambda root: setup_link(
                root, "policy/SYSTEM.md", "base-system.md"
            ),
            head_root_setup=lambda root: setup_link(
                root, "policy/SYSTEM.md", "head-system.md"
            ),
        )
        self.assertEqual(code, 1, out)
        self.assertIn("paths.system resolved target changed", out)

    def test_public_assurance_root_change_fails(self):
        def mutate(head):
            head["security"] = {"public_assurance_root": "elsewhere"}

        code, out = self.run_regression(mutate)
        self.assertEqual(code, 1, out)
        self.assertIn("assurance policy weakened", out)
        self.assertIn("security.public_assurance_root changed", out)

    def test_security_policy_locations_are_protected(self):
        for field, value in (
            ("policy", "docs/SECURITY.md"),
            ("restricted_record", "other_private_system"),
        ):
            with self.subTest(field=field):
                code, out = self.run_regression(
                    lambda head, f=field, v=value: head["security"].__setitem__(f, v)
                )
                self.assertEqual(code, 1, out)
                self.assertIn(f"security.{field} changed", out)

    def test_lexically_equivalent_policy_paths_are_not_regressions(self):
        mutations = (
            ("review", "record", "./docs/reviews/2026-01-01.md"),
            ("security", "policy", "./SECURITY.md"),
            ("security", "public_assurance_root", "./assurance"),
        )
        for section, field, value in mutations:
            with self.subTest(section=section, field=field):
                base = regression_base_adoption()
                head = copy.deepcopy(base)
                target = (
                    head["human_review"] if section == "review" else head["security"]
                )
                target[field] = value
                code, out = self.run_drift(
                    head, changed=(), base_adoption=base
                )
                self.assertEqual(code, 0, out)
                self.assertIn("no assurance policy regression", out)

    def test_issue_integration_controls_cannot_be_silently_weakened(self):
        mutations = {
            "stable_id_required": False,
            "public_security_issues_allowed": True,
            "closing_requires_artifact_update": False,
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                code, out = self.run_regression(
                    lambda head, f=field, v=value: head["issue_integration"].__setitem__(f, v)
                )
                self.assertEqual(code, 1, out)
                self.assertIn(f"issue_integration.{field} changed", out)

    def test_material_change_workflow_changes_fail(self):
        for field, value in (("system", "existing"), ("root", ".")):
            with self.subTest(field=field):
                code, out = self.run_regression(
                    lambda head, f=field, v=value: head[
                        "specification_workflow"
                    ].__setitem__(f, v)
                )
                self.assertEqual(code, 1, out)
                self.assertIn(f"specification_workflow.{field} changed", out)


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

    def run_lite_review_date_diff(self, before, after):
        """Run the public drift CLI with both register roots in lite layout."""
        root = self.make_tmp()
        base_adoption = baseline_lite_adoption()
        head_adoption = copy.deepcopy(base_adoption)
        write_yaml(root / "base-adoption.yaml", base_adoption)
        (root / "changed.txt").write_text("", encoding="utf-8")

        base_assurance = baseline_lite_assurance()
        base_assurance["residuals"][0]["review_after"] = before
        head_assurance = copy.deepcopy(base_assurance)
        head_assurance["residuals"][0]["review_after"] = after
        base_root = root / "base-root"
        head_root = root / "head-root"
        head_adoption_path = head_root / ".agentic-assurance" / "adoption.yaml"
        write_yaml(head_adoption_path, head_adoption)
        write_yaml(
            base_root / ".agentic-assurance" / "assurance.yaml",
            base_assurance,
        )
        write_yaml(
            head_root / ".agentic-assurance" / "assurance.yaml",
            head_assurance,
        )
        return run_validator(
            [
                "drift",
                "--adoption",
                str(head_adoption_path),
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

    def test_every_affirmative_intent_reclassification_or_unset_fails(self):
        for before in ("INTENDED", "COMPATIBILITY", "DEPRECATED"):
            for after in ("UNKNOWN", "ACCIDENTAL", None):
                with self.subTest(before=before, after=after):
                    def set_base(registers, value=before):
                        registers["invariants"]["invariants"][0]["intent"] = {
                            "classification": value,
                            "authority": "owner-review-1",
                        }

                    def mutate(head, value=after):
                        intent = head["invariants"]["invariants"][0]["intent"]
                        if value is None:
                            intent.pop("classification")
                        else:
                            intent["classification"] = value

                    code, out = self.run_register_diff(
                        mutate, mutate_base=set_base
                    )
                    self.assertEqual(code, 1, out)
                    self.assertIn("intent", out)

    def test_affirmative_intent_authority_rewrite_fails(self):
        for classification in ("INTENDED", "COMPATIBILITY", "DEPRECATED"):
            with self.subTest(classification=classification):
                def set_base(registers, value=classification):
                    registers["invariants"]["invariants"][0]["intent"] = {
                        "classification": value,
                        "authority": "owner-review-1",
                    }

                def mutate(head):
                    head["invariants"]["invariants"][0]["intent"][
                        "authority"
                    ] = "owner-review-2"

                code, out = self.run_register_diff(
                    mutate, mutate_base=set_base
                )
                self.assertEqual(code, 1, out)
                self.assertIn("intent.authority changed", out)

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

    def test_recorded_residual_resolution_grounds_rewrite_fails(self):
        def set_resolved(registers):
            residual = registers["residuals"]["residuals"][0]
            residual["status"] = "RESOLVED"
            residual["resolution_note"] = "Fixed in PR 1"

        def mutate(head):
            head["residuals"]["residuals"][0][
                "resolution_note"
            ] = "Fixed somewhere else"

        code, out = self.run_register_diff(mutate, mutate_base=set_resolved)
        self.assertEqual(code, 1, out)
        self.assertIn("resolution_note changed", out)

    def test_recorded_defeater_closure_grounds_rewrite_fails(self):
        def set_closed(registers):
            registers["defeaters"] = drift_defeaters_document(
                "RESOLVED", resolution="Disproved by audit 1"
            )

        def mutate(head):
            head["defeaters"]["defeaters"][0][
                "resolution"
            ] = "Disproved by a different audit"

        code, out = self.run_register_diff(mutate, mutate_base=set_closed)
        self.assertEqual(code, 1, out)
        self.assertIn("resolution changed", out)

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

    def test_real_review_after_replaced_by_date_sentinel_fails(self):
        # Adopter-mode substitution keeps DRAFT templates usable, but the
        # policy diff must compare review-date sentinels raw: replacing a real
        # commitment with either the current or v0.3.x sentinel is a weakening.
        def schedule_base(base):
            base["residuals"]["residuals"][0]["review_after"] = "2099-01-01"

        for sentinel in REVIEW_DATE_PLACEHOLDERS:
            with self.subTest(sentinel=sentinel):
                def mutate(head):
                    head["residuals"]["residuals"][0]["review_after"] = sentinel

                code, out = self.run_register_diff(
                    mutate, mutate_base=schedule_base
                )
                self.assertEqual(code, 1, out)
                self.assertIn(
                    "residual RES-CORE-001 review_after replaced with an "
                    f"unparsable value ({sentinel!r}; was 2099-01-01)",
                    out,
                )

    def test_review_after_sentinels_repaired_to_real_date_not_flagged(self):
        for sentinel in REVIEW_DATE_PLACEHOLDERS:
            with self.subTest(sentinel=sentinel):
                def placeholder_base(base):
                    base["residuals"]["residuals"][0]["review_after"] = sentinel

                def mutate(head):
                    head["residuals"]["residuals"][0]["review_after"] = "2099-01-01"

                code, out = self.run_register_diff(
                    mutate, mutate_base=placeholder_base
                )
                self.assertEqual(code, 0, out)
                self.assertIn("no assurance policy regression", out)

    def test_review_after_sentinel_alias_migration_not_flagged(self):
        for before, after in (
            (CURRENT_REVIEW_DATE_PLACEHOLDER, LEGACY_REVIEW_DATE_PLACEHOLDER),
            (LEGACY_REVIEW_DATE_PLACEHOLDER, CURRENT_REVIEW_DATE_PLACEHOLDER),
        ):
            with self.subTest(before=before, after=after):
                def placeholder_base(base):
                    base["residuals"]["residuals"][0]["review_after"] = before

                def mutate(head):
                    head["residuals"]["residuals"][0]["review_after"] = after

                code, out = self.run_register_diff(
                    mutate, mutate_base=placeholder_base
                )
                self.assertEqual(code, 0, out)
                self.assertIn("no assurance policy regression", out)

    def test_unchanged_review_after_sentinel_not_flagged(self):
        for sentinel in REVIEW_DATE_PLACEHOLDERS:
            with self.subTest(sentinel=sentinel):
                def placeholder_base(base):
                    base["residuals"]["residuals"][0]["review_after"] = sentinel

                code, out = self.run_register_diff(
                    lambda head: None, mutate_base=placeholder_base
                )
                self.assertEqual(code, 0, out)
                self.assertIn("no assurance policy regression", out)

    def test_lite_review_after_sentinel_directions_through_cli(self):
        # Exercise the separate lite loader, not only the shared comparator:
        # aliases and repairs are neutral, while erasing a real commitment is
        # still fail-closed for either official spelling.
        neutral_transitions = [
            *[(sentinel, sentinel) for sentinel in REVIEW_DATE_PLACEHOLDERS],
            (CURRENT_REVIEW_DATE_PLACEHOLDER, LEGACY_REVIEW_DATE_PLACEHOLDER),
            (LEGACY_REVIEW_DATE_PLACEHOLDER, CURRENT_REVIEW_DATE_PLACEHOLDER),
            *[(sentinel, "2099-01-01") for sentinel in REVIEW_DATE_PLACEHOLDERS],
        ]
        for before, after in neutral_transitions:
            with self.subTest(before=before, after=after, result="neutral"):
                code, out = self.run_lite_review_date_diff(before, after)
                self.assertEqual(code, 0, out)
                self.assertIn("no assurance policy regression", out)

        for sentinel in REVIEW_DATE_PLACEHOLDERS:
            with self.subTest(
                before="2099-01-01", after=sentinel, result="regression"
            ):
                code, out = self.run_lite_review_date_diff("2099-01-01", sentinel)
                self.assertEqual(code, 1, out)
                self.assertIn("review_after replaced with an unparsable value", out)
                self.assertIn(repr(sentinel), out)

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
        self.assertNotIn(
            "OK: no assurance policy regression against the base declaration",
            out,
        )

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
        self.assertIn("must be a non-root repository-relative path", out)
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
        self.assertIn("must be a non-root repository-relative path", out)
        self.assertNotIn("cannot parse", out)


# ---------------------------------------------------------------------------
# 17. independent v0.4.0 audit regressions
# ---------------------------------------------------------------------------


class TestStrictPolicyInputs(ValidatorTestCase):
    def test_yaml_constructor_value_errors_are_controlled(self):
        for label, raw_value, expected in (
            ("invalid date", "2026-02-30", "day"),
            ("oversized integer", "9" * 5_000, "numeric token is too long"),
        ):
            with self.subTest(label=label):
                root = self.make_tmp()
                adoption = baseline_lite_adoption()
                adoption["extensions"] = {"hostile_scalar": "SCALAR_SENTINEL"}
                adoption_path = build_lite_project(
                    root, adoption, baseline_lite_assurance()
                )
                raw = json.dumps(adoption, indent=2).replace(
                    '"SCALAR_SENTINEL"', raw_value, 1
                )
                adoption_path.write_text(raw, encoding="utf-8")

                code, out = self.run_adopter(root, adoption_path)
                self.assertEqual(code, 1, out)
                self.assertIn(expected, out)
                self.assertNotIn("Traceback", out)

    def test_oversized_json_number_is_rejected_before_conversion(self):
        root = self.make_tmp()
        copy_self_check_fixture(root)
        schema_path = root / "schemas" / "adoption.schema.json"
        raw = schema_path.read_text(encoding="utf-8")
        raw = raw.replace('"minItems": 1', '"minItems": ' + "9" * 5_000, 1)
        schema_path.write_text(raw, encoding="utf-8")

        code, out = run_validator(["self-check", "--repo-root", str(root)])
        self.assertEqual(code, 1, out)
        self.assertIn("numeric token is too long", out)
        self.assertNotIn("Traceback", out)

    def test_non_string_yaml_mapping_key_is_rejected_cleanly(self):
        root = self.make_tmp()
        adoption_path = build_lite_project(
            root, baseline_lite_adoption(), baseline_lite_assurance()
        )
        raw = json.dumps(baseline_lite_adoption(), indent=2)
        adoption_path.write_text(
            raw.replace("{\n", "{\n  7: \"unexpected\",\n", 1),
            encoding="utf-8",
        )

        code, out = self.run_adopter(root, adoption_path)
        self.assertEqual(code, 1, out)
        self.assertIn("found non-string mapping key 7", out)
        self.assertNotIn("Traceback", out)

    def test_non_utf8_yaml_and_json_inputs_fail_cleanly(self):
        root = self.make_tmp()
        adoption_path = build_lite_project(
            root, baseline_lite_adoption(), baseline_lite_assurance()
        )
        adoption_path.write_bytes(b"\xff\xfe")
        code, out = self.run_adopter(root, adoption_path)
        self.assertEqual(code, 1, out)
        self.assertIn("as UTF-8", out)
        self.assertNotIn("Traceback", out)

        root = self.make_tmp()
        adoption_path = build_split_project(
            root, baseline_adoption(), baseline_registers()
        )
        (root / REGISTER_FILES["invariants"]).write_bytes(b"\xff\xfe")
        code, out = self.run_adopter(root, adoption_path)
        self.assertEqual(code, 1, out)
        self.assertIn("as UTF-8", out)
        self.assertNotIn("Traceback", out)

        root = self.make_tmp()
        copy_self_check_fixture(root)
        (root / "schemas" / "adoption.schema.json").write_bytes(b"\xff\xfe")
        code, out = run_validator(["self-check", "--repo-root", str(root)])
        self.assertEqual(code, 1, out)
        self.assertIn("as UTF-8", out)
        self.assertNotIn("Traceback", out)

        root = self.make_tmp()
        copy_self_check_fixture(root)
        (root / "VERSION").write_bytes(b"\xff\xfe")
        code, out = run_validator(["self-check", "--repo-root", str(root)])
        self.assertEqual(code, 1, out)
        self.assertIn("as UTF-8", out)
        self.assertNotIn("Traceback", out)

    def test_non_utf8_drift_auxiliary_inputs_follow_cli_contract(self):
        for target in ("changed", "body", "diff"):
            with self.subTest(target=target):
                root = self.make_tmp()
                write_yaml(root / "adoption.yaml", drift_adoption())
                (root / "changed.txt").write_text(
                    "src/api/handler.py\n", encoding="utf-8"
                )
                (root / "body.txt").write_text("", encoding="utf-8")
                (root / "assurance.diff").write_text("+ unrelated\n", encoding="utf-8")
                target_path = {
                    "changed": root / "changed.txt",
                    "body": root / "body.txt",
                    "diff": root / "assurance.diff",
                }[target]
                target_path.write_bytes(b"\xff\xfe")
                args = [
                    "drift",
                    "--adoption",
                    str(root / "adoption.yaml"),
                    "--changed-files",
                    str(root / "changed.txt"),
                    "--pr-body",
                    str(root / "body.txt"),
                    "--assurance-diff",
                    str(root / "assurance.diff"),
                    "--strict",
                ]
                code, out = run_validator(args)
                self.assertEqual(code, 1, out)
                self.assertNotIn("Traceback", out)
                if target != "body":
                    self.assertIn("as UTF-8", out)

    def test_duplicate_adoption_profile_key_is_rejected(self):
        root = self.make_tmp()
        adoption_path = build_lite_project(
            root, baseline_lite_adoption(), baseline_lite_assurance()
        )
        raw = json.dumps(baseline_lite_adoption(), indent=2)
        raw = raw[:-2] + ',\n  "profiles": ["service"]\n}\n'
        adoption_path.write_text(raw, encoding="utf-8")

        code, out = self.run_adopter(root, adoption_path)
        self.assertEqual(code, 1, out)
        self.assertIn("duplicate key 'profiles'", out)

    def test_duplicate_adoption_stage_key_is_rejected(self):
        root = self.make_tmp()
        adoption = baseline_lite_adoption()
        adoption_path = build_lite_project(
            root, adoption, baseline_lite_assurance()
        )
        raw = json.dumps(adoption, indent=2)
        raw = raw[:-2] + ',\n  "adoption_stage": "CONFORMANT",\n  "adoption_stage": "DRAFT"\n}\n'
        adoption_path.write_text(raw, encoding="utf-8")

        code, out = self.run_adopter(root, adoption_path)
        self.assertEqual(code, 1, out)
        self.assertIn("duplicate key 'adoption_stage'", out)

    def test_duplicate_nested_register_key_is_rejected(self):
        root = self.make_tmp()
        adoption_path = build_split_project(
            root, baseline_adoption(), baseline_registers()
        )
        invariant_path = root / REGISTER_FILES["invariants"]
        raw = json.dumps(baseline_registers()["invariants"], indent=2)
        raw = raw.replace(
            '"status": "UNKNOWN"',
            '"status": "VERIFIED",\n      "status": "UNKNOWN"',
            1,
        )
        invariant_path.write_text(raw, encoding="utf-8")

        code, out = self.run_adopter(root, adoption_path)
        self.assertEqual(code, 1, out)
        self.assertIn("duplicate key 'status'", out)

    def test_duplicate_json_schema_keyword_is_rejected(self):
        root = self.make_tmp()
        copy_self_check_fixture(root)
        schema_path = root / "schemas" / "adoption.schema.json"
        raw = schema_path.read_text(encoding="utf-8")
        raw = raw.replace('"minItems": 1,', '"minItems": 1,\n      "minItems": 0,', 1)
        schema_path.write_text(raw, encoding="utf-8")

        code, out = run_validator(["self-check", "--repo-root", str(root)])
        self.assertEqual(code, 1, out)
        self.assertIn("duplicate key 'minItems'", out)

    def test_duplicate_template_yaml_key_breaks_self_check(self):
        root = self.make_tmp()
        copy_self_check_fixture(root)
        template_path = root / "templates" / "adoption.yaml"
        template_path.write_text(
            template_path.read_text(encoding="utf-8")
            + "\nprofiles:\n  - core\n",
            encoding="utf-8",
        )

        code, out = run_validator(["self-check", "--repo-root", str(root)])
        self.assertEqual(code, 1, out)
        self.assertIn("duplicate key 'profiles'", out)

    def test_nonfinite_json_schema_number_is_rejected(self):
        for token, expected in (
            ("NaN", "non-finite JSON number 'NaN'"),
            ("1e9999", "outside the supported finite range"),
        ):
            with self.subTest(token=token):
                root = self.make_tmp()
                copy_self_check_fixture(root)
                schema_path = root / "schemas" / "adoption.schema.json"
                raw = schema_path.read_text(encoding="utf-8")
                raw = raw.replace('"minItems": 1', f'"minItems": {token}', 1)
                schema_path.write_text(raw, encoding="utf-8")

                code, out = run_validator(
                    ["self-check", "--repo-root", str(root)]
                )
                self.assertEqual(code, 1, out)
                self.assertIn(expected, out)

    def test_malformed_json_schemas_fail_meta_validation(self):
        mutations = {
            "negative minItems": lambda schema: schema["properties"]["profiles"].update(
                {"minItems": -1}
            ),
            "scalar required": lambda schema: schema.update({"required": "profiles"}),
            "non-object properties": lambda schema: schema.update({"properties": []}),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                root = self.make_tmp()
                copy_self_check_fixture(root)
                schema_path = root / "schemas" / "adoption.schema.json"
                schema = json.loads(schema_path.read_text(encoding="utf-8"))
                mutate(schema)
                schema_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")

                code, out = run_validator(
                    ["self-check", "--repo-root", str(root)]
                )
                self.assertEqual(code, 1, out)
                self.assertIn("invalid JSON Schema draft 2020-12", out)

    def test_schema_references_are_resolved_offline_and_fail_controlled(self):
        remote_ref = "http://127.0.0.1:9/hostile-schema"

        root = self.make_tmp()
        copy_self_check_fixture(root)
        schema_path = root / "schemas" / "adoption.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        schema["allOf"] = [*schema.get("allOf", []), {"$ref": remote_ref}]
        schema_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
        code, out = run_validator(["self-check", "--repo-root", str(root)])
        self.assertEqual(code, 1, out)
        self.assertIn("schema reference cannot be resolved offline", out)
        self.assertNotIn("Traceback", out)

        project = self.make_tmp()
        adoption_path = build_split_project(
            project, baseline_adoption(), baseline_registers()
        )
        checkout = self.adopter_profile_checkout()
        checkout_schema_path = checkout / "schemas" / "adoption.schema.json"
        checkout_schema = json.loads(
            checkout_schema_path.read_text(encoding="utf-8")
        )
        checkout_schema["allOf"] = [
            *checkout_schema.get("allOf", []),
            {"$ref": remote_ref},
        ]
        checkout_schema_path.write_text(
            json.dumps(checkout_schema, indent=2), encoding="utf-8"
        )
        code, out = self.run_adopter(project, adoption_path)
        self.assertEqual(code, 1, out)
        self.assertIn("schema reference cannot be resolved offline", out)
        self.assertNotIn("Traceback", out)

    def test_placeholder_mapping_keys_are_detected(self):
        adoption = baseline_adoption()
        adoption["components"] = {
            "REPLACE_WITH_COMPONENT": {
                "paths": ["src/**"],
                "invariants": ["INV-CORE-001"],
            }
        }
        code, out = self.run_split(adoption, baseline_registers())
        self.assertEqual(code, 1, out)
        self.assertIn("<mapping-key>", out)
        self.assertIn("REPLACE_WITH_COMPONENT", out)

        adoption = baseline_adoption()
        adoption["adoption_stage"] = "HUMAN_REVIEWED"
        adoption["human_review"] = human_review_block()
        registers = baseline_registers()
        registers["invariants"]["invariants"][0]["REPLACE_WITH_LOCAL_FIELD"] = "x"
        code, out = self.run_split(adoption, registers)
        self.assertEqual(code, 1, out)
        self.assertIn("REPLACE_WITH_LOCAL_FIELD", out)

        adoption = baseline_lite_adoption()
        adoption["adoption_stage"] = "HUMAN_REVIEWED"
        adoption["human_review"] = human_review_block()
        assurance = baseline_lite_assurance()
        assurance["extensions"] = {"REPLACE_WITH_EXTENSION_KEY": "x"}
        code, out = self.run_lite(adoption, assurance)
        self.assertEqual(code, 1, out)
        self.assertIn("REPLACE_WITH_EXTENSION_KEY", out)

    def test_workflow_inline_readers_use_the_strict_loader(self):
        workflow = (REPO_ROOT / ".github" / "workflows" / "adopter-validate.yml").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("yaml.safe_load", workflow)
        self.assertIn("from validate import", workflow)
        self.assertIn("CALLER_WORKFLOW_REF: ${{ github.workflow_ref }}", workflow)
        inline_python = [
            line.strip()
            for line in workflow.splitlines()
            if "<<'EOF'" in line and line.strip().startswith("python ")
        ]
        self.assertTrue(inline_python)
        self.assertTrue(
            all(line.startswith("python -I -") for line in inline_python),
            inline_python,
        )
        validator_calls = [
            line.strip()
            for line in workflow.splitlines()
            if "scripts/validate.py" in line and line.strip().startswith("python ")
        ]
        self.assertTrue(validator_calls)
        self.assertTrue(
            all(
                line.startswith(
                    "python -I .assurance-profile-pin/scripts/validate.py"
                )
                for line in validator_calls
            ),
            validator_calls,
        )

    def test_workflow_materializer_uses_an_isolated_python_shell(self):
        shell, script = workflow_step_spec(
            "Materialize the base tree and compute the assurance diff"
        )
        self.assertEqual(shell, "python -I {0}")
        self.assertNotIn("python -I - <<'EOF'", script)
        compile(script, "<workflow-materializer>", "exec")

    def test_workflow_rejects_unencodable_policy_paths_without_traceback(self):
        root = self.make_tmp()
        repository = root / "repo"
        init_git_test_repository(repository)
        adoption_path = ".agentic-assurance/adoption.yaml"
        adoption = workflow_policy_adoption(stage="DRAFT", version="v0.4.0")
        write_yaml(repository / adoption_path, adoption)
        write_caller_workflow(
            repository / ".github/workflows/assurance.yml",
            adoption_path,
            "a" * 40,
        )
        base_sha = commit_test_repository(repository, "valid policy path base")

        adoption["paths"] = {"custom": "\ud800"}
        write_yaml(repository / adoption_path, adoption)
        head_sha = commit_test_repository(repository, "unencodable policy path")
        completed, _ = run_workflow_materializer(
            root, repository, base_sha, head_sha, adoption_path
        )
        output = completed.stdout + completed.stderr
        self.assertNotEqual(completed.returncode, 0, output)
        self.assertIn("not a canonical, bounded", output)
        self.assertNotIn("Traceback", output)

    def test_workflow_drift_checks_out_the_exact_pr_head_tree(self):
        workflow = (
            REPO_ROOT / ".github" / "workflows" / "adopter-validate.yml"
        ).read_text(encoding="utf-8")
        drift = workflow[workflow.index("  drift:\n") :]
        checkout = drift[
            drift.index("      - name: Check out adopting repository\n") :
            drift.index("      - name: Verify workflow identity\n")
        ]
        self.assertIn(
            "ref: ${{ github.event.pull_request.head.sha }}",
            checkout,
        )
        self.assertIn("fetch-depth: 0", checkout)

    def test_workflow_identity_requires_exact_canonical_path_and_sha_ref(self):
        workflow = (
            REPO_ROOT / ".github" / "workflows" / "adopter-validate.yml"
        ).read_text(encoding="utf-8")
        self.assertEqual(workflow.count("EXPECTED_WORKFLOW_REF="), 3)
        self.assertNotIn('*"@${WORKFLOW_SHA}"', workflow)

        sha = "a" * 40
        canonical = (
            "MosslandOpenDevs/agentic-assurance-profile/"
            ".github/workflows/adopter-validate.yml"
        )
        cases = (
            (f"{canonical}@{sha}", 0),
            (f"{canonical}@refs/heads/release@{sha}", 1),
            (
                "MosslandOpenDevs/agentic-assurance-profile/"
                f".github/workflows/other.yml@{sha}",
                1,
            ),
        )
        root = self.make_tmp()
        for workflow_ref, expected_code in cases:
            with self.subTest(workflow_ref=workflow_ref):
                completed = subprocess.run(
                    [
                        "bash",
                        "-c",
                        workflow_step_shell("Verify workflow identity"),
                    ],
                    cwd=root,
                    env=clean_env(
                        {
                            "WORKFLOW_REPOSITORY": (
                                "MosslandOpenDevs/agentic-assurance-profile"
                            ),
                            "WORKFLOW_REF": workflow_ref,
                            "WORKFLOW_SHA": sha,
                        }
                    ),
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                output = completed.stdout + completed.stderr
                self.assertEqual(completed.returncode, expected_code, output)

    def test_workflow_changed_file_producer_reports_copy_source_and_destination(self):
        workflow = (
            REPO_ROOT / ".github" / "workflows" / "adopter-validate.yml"
        ).read_text(encoding="utf-8")
        step = workflow_step_shell("Compute changed files (rename-safe)")
        self.assertIn("-M -C --find-copies-harder", step)

        root = self.make_tmp()
        repository = root / "repo"
        init_git_test_repository(repository)
        source = repository / "src" / "original.py"
        source.parent.mkdir()
        source.write_text("VALUE = 1\n", encoding="utf-8")
        base_sha = commit_test_repository(repository, "copy producer base")
        destination = repository / "copied" / "new.py"
        destination.parent.mkdir()
        shutil.copy2(source, destination)
        second_destination = repository / "copied" / "second.py"
        shutil.copy2(source, second_destination)
        head_sha = commit_test_repository(repository, "retain source and copies")

        runner_temp = root / "runner-temp"
        runner_temp.mkdir()
        completed = subprocess.run(
            ["bash", "-c", step],
            cwd=repository,
            env=clean_env(
                {
                    "BASE_SHA": base_sha,
                    "HEAD_SHA": head_sha,
                    "RUNNER_TEMP": str(runner_temp),
                }
            ),
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, output)
        changed = [
            item.decode("utf-8")
            for item in (runner_temp / "changed-files.z").read_bytes().split(b"\0")
            if item
        ]
        self.assertEqual(len(changed), 3, changed)
        self.assertEqual(changed.count("src/original.py"), 1, changed)
        self.assertEqual(
            set(changed),
            {"src/original.py", "copied/new.py", "copied/second.py"},
        )

    def test_each_trusted_checkout_reserves_an_unoccupied_lstat_checked_path(self):
        workflow = (
            REPO_ROOT / ".github" / "workflows" / "adopter-validate.yml"
        ).read_text(encoding="utf-8")
        self.assertEqual(
            workflow.count("- name: Reserve trusted profile checkout destination"),
            3,
        )
        self.assertEqual(
            workflow.count("- name: Check out this workflow's profile source (trusted)"),
            3,
        )

        root = self.make_tmp()
        repository = root / "repo"
        repository.mkdir()
        outside = root / "outside-target"
        outside.mkdir()
        sentinel = outside / "keep.txt"
        sentinel.write_text("keep\n", encoding="utf-8")
        (repository / ".assurance-profile-pin").symlink_to(
            outside, target_is_directory=True
        )
        completed = subprocess.run(
            [
                "bash",
                "-c",
                workflow_step_shell(
                    "Reserve trusted profile checkout destination"
                ),
            ],
            cwd=repository,
            env=clean_env(),
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = completed.stdout + completed.stderr
        self.assertNotEqual(completed.returncode, 0, output)
        self.assertIn("Reserved profile checkout destination already exists", output)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep\n")

    def assert_layout_transition_decoy_cannot_satisfy_routing(
        self, *, base_layout
    ):
        root = self.make_tmp()
        repository = root / "repo"
        init_git_test_repository(repository)
        adoption_path = ".agentic-assurance/adoption.yaml"
        base = workflow_policy_adoption(stage="DRAFT", version="v0.4.0")
        base["components"] = {
            "app": {
                "paths": ["src/**"],
                "invariants": ["INV-CORE-001"],
            }
        }
        if base_layout == "lite":
            base["layout"] = "lite"
        write_yaml(repository / adoption_path, base)

        # Track both layouts before the transition. Only one is active on the
        # base; the other becomes active on HEAD without an assurance edit.
        # The ID is then added solely to the now-inactive old-layout file.
        registers = baseline_registers()
        for kind, document in registers.items():
            write_yaml(repository / REGISTER_FILES[kind], document)
        write_yaml(repository / LITE_ASSURANCE_PATH, baseline_lite_assurance())
        source = repository / "src" / "api.py"
        source.parent.mkdir(parents=True)
        source.write_text("VALUE = 1\n", encoding="utf-8")
        write_caller_workflow(
            repository / ".github/workflows/assurance.yml",
            adoption_path,
            "a" * 40,
        )
        base_sha = commit_test_repository(
            repository, f"{base_layout} routing base"
        )

        head = copy.deepcopy(base)
        if base_layout == "lite":
            head.pop("layout")
            inactive_path = repository / LITE_ASSURANCE_PATH
        else:
            head["layout"] = "lite"
            inactive_path = repository / REGISTER_FILES["invariants"]
        write_yaml(repository / adoption_path, head)
        source.write_text("VALUE = 2\n", encoding="utf-8")
        inactive_path.write_text(
            inactive_path.read_text(encoding="utf-8")
            + "\n# INV-CORE-001 decoy in deactivated layout\n",
            encoding="utf-8",
        )
        head_sha = commit_test_repository(repository, "switch assurance layout")

        completed, runner_temp = run_workflow_materializer(
            root, repository, base_sha, head_sha, adoption_path
        )
        output = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, output)
        assurance_diff_path = runner_temp / "assurance-diff.txt"
        assurance_diff = assurance_diff_path.read_text(encoding="utf-8")
        self.assertNotIn("decoy in deactivated layout", assurance_diff)
        self.assertNotIn(inactive_path.relative_to(repository).as_posix(), assurance_diff)

        changed_path = runner_temp / "changed-for-routing.txt"
        changed_path.write_text("src/api.py\n", encoding="utf-8")
        body_path = runner_temp / "body-for-routing.txt"
        body_path.write_text(
            "Assurance policy change: deliberate layout migration\n",
            encoding="utf-8",
        )
        code, drift_out = run_validator(
            [
                "drift",
                "--adoption",
                str(repository / adoption_path),
                "--changed-files",
                str(changed_path),
                "--pr-body",
                str(body_path),
                "--assurance-diff",
                str(assurance_diff_path),
                "--base-adoption",
                str(runner_temp / "base-adoption.yaml"),
                "--base-registers-root",
                str(runner_temp / "base-tree"),
                "--project-root",
                str(repository),
                "--adoption-path-transition",
                str(runner_temp / "adoption-path-transition.json"),
                "--strict",
            ]
        )
        self.assertEqual(code, 1, drift_out)
        self.assertIn("without an assurance update", drift_out)
        self.assertNotIn("assurance update references INV-CORE-001", drift_out)

    def test_workflow_split_to_lite_excludes_deactivated_split_evidence(self):
        self.assert_layout_transition_decoy_cannot_satisfy_routing(
            base_layout="split"
        )

    def test_workflow_lite_to_split_excludes_deactivated_lite_evidence(self):
        self.assert_layout_transition_decoy_cannot_satisfy_routing(
            base_layout="lite"
        )

    def test_repository_root_policy_bindings_do_not_widen_positive_evidence(self):
        for root_binding, root_spelling in (
            ("specification workflow", "literal"),
            ("specification workflow", "symlink"),
            ("public assurance root", "literal"),
            ("public assurance root", "symlink"),
        ):
            with self.subTest(
                root_binding=root_binding, root_spelling=root_spelling
            ):
                root = self.make_tmp()
                repository = root / "repo"
                init_git_test_repository(repository)
                adoption_path = ".agentic-assurance/adoption.yaml"
                adoption = workflow_policy_adoption(
                    stage="DRAFT", version="v0.4.0"
                )
                adoption["components"] = {
                    "app": {
                        "paths": ["src/**"],
                        "invariants": ["INV-CORE-001"],
                    }
                }
                binding_value = (
                    "." if root_spelling == "literal" else "policy-root"
                )
                if root_binding == "specification workflow":
                    adoption["specification_workflow"]["root"] = binding_value
                else:
                    adoption["security"] = {
                        "public_assurance_root": binding_value
                    }
                write_yaml(repository / adoption_path, adoption)
                if root_spelling == "symlink":
                    (repository / "policy-root").symlink_to(
                        ".", target_is_directory=True
                    )
                source = repository / "src" / "app.py"
                source.parent.mkdir()
                source.write_text("VALUE = 1\n", encoding="utf-8")
                write_caller_workflow(
                    repository / ".github/workflows/assurance.yml",
                    adoption_path,
                    "a" * 40,
                )
                base_sha = commit_test_repository(
                    repository, f"{root_binding} base"
                )

                source.write_text(
                    "VALUE = 2\n# INV-CORE-001 decoy\n", encoding="utf-8"
                )
                head_sha = commit_test_repository(
                    repository, f"{root_binding} source update"
                )
                completed, runner_temp = run_workflow_materializer(
                    root, repository, base_sha, head_sha, adoption_path
                )
                output = completed.stdout + completed.stderr
                self.assertEqual(completed.returncode, 0, output)
                assurance_diff_path = runner_temp / "assurance-diff.txt"
                assurance_diff = assurance_diff_path.read_text(encoding="utf-8")
                self.assertNotIn("+INV-CORE-001", assurance_diff)

                changed_path = runner_temp / "changed-root-binding.txt"
                changed_path.write_text("src/app.py\n", encoding="utf-8")
                body_path = runner_temp / "body-root-binding.txt"
                body_path.write_text("", encoding="utf-8")
                code, drift_out = run_validator(
                    [
                        "drift",
                        "--adoption",
                        str(repository / adoption_path),
                        "--changed-files",
                        str(changed_path),
                        "--pr-body",
                        str(body_path),
                        "--assurance-diff",
                        str(assurance_diff_path),
                        "--strict",
                    ]
                )
                self.assertEqual(code, 1, drift_out)
                self.assertIn("without an assurance update", drift_out)

    def test_workflow_symlink_dotdot_decoy_cannot_supply_evidence(self):
        root = self.make_tmp()
        repository = root / "repo"
        init_git_test_repository(repository)
        adoption_path = ".agentic-assurance/adoption.yaml"
        adoption = workflow_policy_adoption(stage="DRAFT", version="v0.4.0")
        adoption["paths"] = {"system": "alias/../system.md"}
        adoption["components"] = {
            "app": {
                "paths": ["src/**"],
                "invariants": ["INV-CORE-001"],
            }
        }
        write_yaml(repository / adoption_path, adoption)
        actual = repository / "real" / "system.md"
        actual.parent.mkdir(parents=True)
        actual.write_text("# Actual system policy\n", encoding="utf-8")
        (repository / "real" / "dir").mkdir()
        (repository / "alias").symlink_to(
            "real/dir", target_is_directory=True
        )
        source = repository / "src" / "app.py"
        source.parent.mkdir()
        source.write_text("VALUE = 1\n", encoding="utf-8")
        write_caller_workflow(
            repository / ".github/workflows/assurance.yml",
            adoption_path,
            "a" * 40,
        )
        base_sha = commit_test_repository(repository, "symlink dotdot base")

        source.write_text("VALUE = 2\n", encoding="utf-8")
        (repository / "system.md").write_text(
            "Decoy INV-CORE-001 line\n", encoding="utf-8"
        )
        head_sha = commit_test_repository(repository, "add lexical decoy")

        completed, runner_temp = run_workflow_materializer(
            root, repository, base_sha, head_sha, adoption_path
        )
        output = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, output)
        assurance_diff_path = runner_temp / "assurance-diff.txt"
        assurance_diff = assurance_diff_path.read_text(encoding="utf-8")
        self.assertNotIn("Decoy INV-CORE-001", assurance_diff)

        changed = runner_temp / "changed-for-routing.txt"
        changed.write_text("src/app.py\n", encoding="utf-8")
        code, drift_out = run_validator(
            [
                "drift",
                "--adoption",
                str(repository / adoption_path),
                "--changed-files",
                str(changed),
                "--pr-body",
                str(runner_temp / "missing-body.txt"),
                "--assurance-diff",
                str(assurance_diff_path),
                "--base-adoption",
                str(runner_temp / "base-adoption.yaml"),
                "--base-registers-root",
                str(runner_temp / "base-tree"),
                "--project-root",
                str(repository),
                "--adoption-path-transition",
                str(runner_temp / "adoption-path-transition.json"),
                "--strict",
            ]
        )
        self.assertEqual(code, 1, drift_out)
        self.assertIn("without an assurance update", drift_out)

    def test_workflow_tree_record_budget_is_shared_by_base_and_head(self):
        root = self.make_tmp()
        repository = root / "repo"
        init_git_test_repository(repository)
        adoption_path = ".agentic-assurance/adoption.yaml"
        adoption = workflow_policy_adoption(stage="DRAFT", version="v0.4.0")
        write_yaml(repository / adoption_path, adoption)
        system = repository / "assurance" / "SYSTEM.md"
        system.parent.mkdir()
        system.write_text("INV-CORE-001 base\n", encoding="utf-8")
        write_caller_workflow(
            repository / ".github/workflows/assurance.yml",
            adoption_path,
            "a" * 40,
        )
        base_sha = commit_test_repository(repository, "aggregate budget base")
        system.write_text("INV-CORE-001 changed\n", encoding="utf-8")
        head_sha = commit_test_repository(repository, "aggregate budget head")

        completed, _runner_temp = run_workflow_materializer(
            root,
            repository,
            base_sha,
            head_sha,
            adoption_path,
            script_replacements=(
                ("MAX_DISCOVERY_FILES = 100_000", "MAX_DISCOVERY_FILES = 3"),
            ),
        )
        output = completed.stdout + completed.stderr
        self.assertNotEqual(completed.returncode, 0, output)
        self.assertIn("combined merge-base and HEAD", output)
        self.assertIn("3 tracked tree records", output)

    def test_workflow_cat_file_obeys_shared_git_deadline(self):
        root = self.make_tmp()
        repository = root / "repo"
        init_git_test_repository(repository)
        adoption_path = ".agentic-assurance/adoption.yaml"
        adoption = workflow_policy_adoption(stage="DRAFT", version="v0.4.0")
        write_yaml(repository / adoption_path, adoption)
        system = repository / "assurance" / "SYSTEM.md"
        system.parent.mkdir()
        system.write_text("INV-CORE-001 base\n", encoding="utf-8")
        write_caller_workflow(
            repository / ".github/workflows/assurance.yml",
            adoption_path,
            "a" * 40,
        )
        base_sha = commit_test_repository(repository, "cat-file deadline base")
        system.write_text("INV-CORE-001 changed\n", encoding="utf-8")
        head_sha = commit_test_repository(repository, "cat-file deadline head")

        real_git = shutil.which("git")
        self.assertIsNotNone(real_git)
        wrapper_dir = root / "bin"
        wrapper_dir.mkdir()
        wrapper = wrapper_dir / "git"
        wrapper.write_text(
            f"#!{sys.executable}\n"
            "import os, sys, time\n"
            "if sys.argv[1:3] == ['cat-file', '--batch']:\n"
            "    time.sleep(5)\n"
            "    raise SystemExit(0)\n"
            f"os.execv({real_git!r}, [{real_git!r}, *sys.argv[1:]])\n",
            encoding="utf-8",
        )
        wrapper.chmod(0o755)

        completed, _runner_temp = run_workflow_materializer(
            root,
            repository,
            base_sha,
            head_sha,
            adoption_path,
            script_replacements=(
                (
                    "MAX_EVIDENCE_GIT_SECONDS = 60",
                    "MAX_EVIDENCE_GIT_SECONDS = 1",
                ),
            ),
            env_updates={
                "PATH": str(wrapper_dir) + os.pathsep + os.environ.get("PATH", "")
            },
        )
        output = completed.stdout + completed.stderr
        self.assertNotEqual(completed.returncode, 0, output)
        self.assertIn("exceeded 1 seconds", output)
        self.assertIn("reading invariant-bearing blobs", output)
        self.assertNotIn("Traceback", output)

    def test_workflow_trusted_reader_ignores_adopter_python_module_shadows(self):
        root = self.make_tmp()
        repository = root / "repo"
        repository.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
        trusted_scripts = repository / ".assurance-profile-pin" / "scripts"
        trusted_scripts.mkdir(parents=True)
        shutil.copy2(VALIDATOR, trusted_scripts / "validate.py")
        marker = root / "shadow-imported"
        (repository / "yaml.py").write_text(
            "from pathlib import Path\n"
            f"Path({str(marker)!r}).write_text('imported', encoding='utf-8')\n"
            "raise RuntimeError('adopter yaml.py was imported')\n",
            encoding="utf-8",
        )
        adoption = baseline_adoption()
        adoption["upstream"].update(
            {
                "repository": "MosslandOpenDevs/agentic-assurance-profile",
                "version": "unreleased",
                "commit": "0" * 40,
            }
        )
        write_yaml(repository / "adoption.yaml", adoption)
        output_path = root / "github-output"
        completed = subprocess.run(
            [
                "bash",
                "-c",
                workflow_step_shell("Read and verify upstream pin"),
            ],
            cwd=repository,
            env=clean_env(
                {
                    "ADOPTION_FILE": "adoption.yaml",
                    "WORKFLOW_SHA": "0" * 40,
                    "GITHUB_OUTPUT": str(output_path),
                }
            ),
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, output)
        self.assertFalse(marker.exists(), output)
        self.assertIn("version=unreleased", output_path.read_text(encoding="utf-8"))

    def test_every_workflow_head_reader_rejects_adoption_symlink_escape(self):
        root = self.make_tmp()
        repository = root / "repo"
        repository.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
        trusted_scripts = repository / ".assurance-profile-pin" / "scripts"
        trusted_scripts.mkdir(parents=True)
        shutil.copy2(VALIDATOR, trusted_scripts / "validate.py")

        outside = root / "outside-adoption.yaml"
        write_yaml(outside, baseline_adoption())
        trusted = repository / ".assurance-profile-pin" / "hidden-adoption.yaml"
        write_yaml(trusted, baseline_adoption())
        adoption_link = repository / "config" / "adoption.yaml"
        adoption_link.parent.mkdir()

        steps = (
            "Read and verify upstream pin",
            "Verify upstream pin matches this workflow",
            "Materialize the base tree and compute the assurance diff",
        )
        for target, expected in (
            (outside, "resolves outside the project root"),
            (trusted, "trusted/non-adopter data"),
        ):
            adoption_link.unlink(missing_ok=True)
            adoption_link.symlink_to(target)
            for step_name in steps:
                with self.subTest(target=target.name, step=step_name):
                    output_path = root / f"output-{target.name}-{len(step_name)}"
                    env = clean_env(
                        {
                            "ADOPTION_FILE": "config/adoption.yaml",
                            "WORKFLOW_SHA": "0" * 40,
                            "GITHUB_OUTPUT": str(output_path),
                            "BASE_SHA": "1" * 40,
                            "HEAD_SHA": "2" * 40,
                            "RUNNER_TEMP": str(root / "runner-temp"),
                        }
                    )
                    completed = run_workflow_step(
                        step_name,
                        cwd=repository,
                        env=env,
                        timeout=10,
                    )
                    output = completed.stdout + completed.stderr
                    self.assertNotEqual(completed.returncode, 0, output)
                    self.assertIn(expected, output)

    def test_every_workflow_head_reader_rejects_absolute_adoption_input(self):
        root = self.make_tmp()
        repository = root / "repo"
        repository.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
        trusted_scripts = repository / ".assurance-profile-pin" / "scripts"
        trusted_scripts.mkdir(parents=True)
        shutil.copy2(VALIDATOR, trusted_scripts / "validate.py")
        adoption_path = repository / "config" / "adoption.yaml"
        write_yaml(adoption_path, baseline_adoption())

        for step_name in (
            "Read and verify upstream pin",
            "Verify upstream pin matches this workflow",
            "Materialize the base tree and compute the assurance diff",
        ):
            with self.subTest(step=step_name):
                completed = run_workflow_step(
                    step_name,
                    cwd=repository,
                    env=clean_env(
                        {
                            "ADOPTION_FILE": str(adoption_path),
                            "WORKFLOW_SHA": "0" * 40,
                            "GITHUB_OUTPUT": str(root / "github-output"),
                            "BASE_SHA": "1" * 40,
                            "HEAD_SHA": "2" * 40,
                            "RUNNER_TEMP": str(root / "runner-temp"),
                        }
                    ),
                    timeout=10,
                )
                output = completed.stdout + completed.stderr
                self.assertNotEqual(completed.returncode, 0, output)
                self.assertIn("repository-relative lexical path", output)

    def test_workflow_rejects_version_refspec_metacharacters_before_output(self):
        root = self.make_tmp()
        repository = root / "repo"
        repository.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
        trusted_scripts = repository / ".assurance-profile-pin" / "scripts"
        trusted_scripts.mkdir(parents=True)
        shutil.copy2(VALIDATOR, trusted_scripts / "validate.py")

        adoption = baseline_adoption()
        adoption["upstream"].update(
            {
                "repository": "MosslandOpenDevs/agentic-assurance-profile",
                "version": "v0.4.0:*",
                "commit": "a" * 40,
            }
        )
        adoption_relative = "adoption\n::add-mask::PWNED.yaml"
        write_yaml(repository / adoption_relative, adoption)
        output_path = root / "github-output"
        env = clean_env(
            {
                "ADOPTION_FILE": adoption_relative,
                "WORKFLOW_SHA": "a" * 40,
                "GITHUB_OUTPUT": str(output_path),
            }
        )
        completed = subprocess.run(
            [
                "bash",
                "-c",
                workflow_step_shell("Read and verify upstream pin"),
            ],
            cwd=repository,
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = completed.stdout + completed.stderr
        self.assertNotEqual(completed.returncode, 0, output)
        self.assertIn("upstream.version must be", output)
        self.assertNotIn("\n::add-mask::PWNED", output)
        self.assertIn("\\n::add-mask::PWNED", output)
        self.assertFalse(output_path.exists(), output)

    def test_workflow_materializes_prior_declaration_after_path_move(self):
        root = self.make_tmp()
        repository = root / "repo"
        init_git_test_repository(repository)
        base = baseline_adoption()
        base["upstream"][
            "repository"
        ] = "MosslandOpenDevs/agentic-assurance-profile"
        base["adoption_stage"] = "HUMAN_REVIEWED"
        base["human_review"] = human_review_block()
        prior_relative = ".agentic-assurance/prior\n::add-mask::PWNED.conf"
        write_yaml(repository / prior_relative, base)
        # A vendored starter template has the same top-level keys but is not
        # a prior policy declaration: its commit is deliberately unfilled.
        # Discovery must ignore it instead of making a legitimate path move
        # ambiguous.
        template = copy.deepcopy(base)
        template["upstream"]["commit"] = "REPLACE_WITH_FULL_40_CHARACTER_COMMIT_SHA"
        write_yaml(repository / "templates/adoption.yaml", template)
        unrelated = copy.deepcopy(base)
        unrelated["upstream"]["repository"] = "example/not-aap"
        write_yaml(repository / "config/unrelated-policy.conf", unrelated)
        unknown_profile = copy.deepcopy(base)
        unknown_profile["profiles"] = ["unrelated-profile"]
        write_yaml(repository / "config/unknown-profile.conf", unknown_profile)
        unhashable_profile = copy.deepcopy(base)
        unhashable_profile["profiles"] = [["core"]]
        write_yaml(repository / "config/unhashable-profile.conf", unhashable_profile)
        write_caller_workflow(
            repository / ".github/workflows/assurance.yml",
            prior_relative,
            "a" * 40,
        )
        base_sha = commit_test_repository(repository, "base adoption")

        head = copy.deepcopy(base)
        head["adoption_stage"] = "DRAFT"
        old_path = repository / prior_relative
        old_path.unlink()
        write_yaml(repository / "config/adoption.yaml", head)
        write_caller_workflow(
            repository / ".github/workflows/assurance.yml",
            "config/adoption.yaml",
            "b" * 40,
        )
        head_sha = commit_test_repository(repository, "move and weaken adoption")

        completed, runner_temp = run_workflow_materializer(
            root,
            repository,
            base_sha,
            head_sha,
            "config/adoption.yaml",
        )
        output = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, output)
        self.assertIn("adoption declaration moved from", output)
        self.assertNotIn("\n::add-mask::PWNED", output)
        self.assertIn("%0A::add-mask::PWNED", output)
        materialized = json.loads(
            (runner_temp / "base-adoption.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual(materialized["adoption_stage"], "HUMAN_REVIEWED")
        transition_path = runner_temp / "adoption-path-transition.json"
        transition = json.loads(transition_path.read_text(encoding="utf-8"))
        self.assertEqual(
            transition,
            {
                "base": prior_relative,
                "head": "config/adoption.yaml",
                "base_resolved": prior_relative,
                "head_resolved": "config/adoption.yaml",
            },
        )

        (runner_temp / "changed-files.txt").write_text("", encoding="utf-8")
        code, out = run_validator(
            [
                "drift",
                "--adoption",
                str(repository / "config/adoption.yaml"),
                "--changed-files",
                str(runner_temp / "changed-files.txt"),
                "--pr-body",
                str(runner_temp / "missing-body.txt"),
                "--base-adoption",
                str(runner_temp / "base-adoption.yaml"),
                "--adoption-path-transition",
                str(transition_path),
            ]
        )
        self.assertEqual(code, 1, out)
        self.assertIn("adoption_stage downgraded", out)
        self.assertIn("adoption declaration path changed", out)

    def test_workflow_uses_base_caller_when_head_destination_already_exists(self):
        root = self.make_tmp()
        repository = root / "repo"
        init_git_test_repository(repository)

        reviewed_path = "policy/reviewed.yaml"
        destination_path = "policy/draft.yaml"
        reviewed = workflow_policy_adoption(stage="HUMAN_REVIEWED")
        draft = workflow_policy_adoption(stage="DRAFT")
        write_yaml(repository / reviewed_path, reviewed)
        write_yaml(repository / destination_path, draft)
        write_caller_workflow(
            repository / ".github/workflows/assurance.yml",
            reviewed_path,
            "a" * 40,
        )
        base_sha = commit_test_repository(repository, "reviewed base with draft decoy")

        # Only the caller input changes. The destination was already present
        # on the base, so choosing it directly would compare the decoy against
        # itself and miss the reviewed-to-draft transition.
        write_caller_workflow(
            repository / ".github/workflows/assurance.yml",
            destination_path,
            "b" * 40,
        )
        head_sha = commit_test_repository(repository, "switch caller to draft")

        completed, runner_temp = run_workflow_materializer(
            root, repository, base_sha, head_sha, destination_path
        )
        output = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, output)
        materialized = json.loads(
            (runner_temp / "base-adoption.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual(materialized["adoption_stage"], "HUMAN_REVIEWED")
        transition = json.loads(
            (runner_temp / "adoption-path-transition.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            transition,
            {
                "base": reviewed_path,
                "head": destination_path,
                "base_resolved": reviewed_path,
                "head_resolved": destination_path,
            },
        )

    def test_workflow_pin_only_update_accepts_tracked_adoption_symlink_alias(self):
        root = self.make_tmp()
        repository = root / "repo"
        init_git_test_repository(repository)

        target_path = "config/adoption.yaml"
        alias_path = ".agentic-assurance/adoption.yaml"
        write_yaml(repository / target_path, workflow_policy_adoption())
        alias = repository / alias_path
        alias.parent.mkdir(parents=True)
        alias.symlink_to("../config/adoption.yaml")
        write_caller_workflow(
            repository / ".github/workflows/assurance.yml",
            alias_path,
            "a" * 40,
        )
        base_sha = commit_test_repository(repository, "symlinked adoption base")

        write_caller_workflow(
            repository / ".github/workflows/assurance.yml",
            alias_path,
            "b" * 40,
        )
        head_sha = commit_test_repository(repository, "update reusable workflow pin")

        completed, runner_temp = run_workflow_materializer(
            root, repository, base_sha, head_sha, alias_path
        )
        output = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, output)
        self.assertNotIn("bounded declaration discovery", output.lower())
        self.assertNotIn("multiple prior AAP declarations", output)
        transition = json.loads(
            (runner_temp / "adoption-path-transition.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            transition,
            {
                "base": alias_path,
                "head": alias_path,
                "base_resolved": target_path,
                "head_resolved": target_path,
            },
        )

    def test_workflow_assurance_diff_includes_resolved_symlink_target_edit(self):
        root = self.make_tmp()
        repository = root / "repo"
        init_git_test_repository(repository)
        adoption_path = ".agentic-assurance/adoption.yaml"
        adoption = workflow_policy_adoption()
        adoption["paths"] = {"system": "assurance/SYSTEM.md"}
        write_yaml(repository / adoption_path, adoption)
        system_target = repository / "policy" / "SYSTEM.md"
        system_target.parent.mkdir(parents=True)
        system_target.write_text("# System\nbase statement\n", encoding="utf-8")
        system_alias = repository / "assurance" / "SYSTEM.md"
        system_alias.parent.mkdir(parents=True)
        system_alias.symlink_to(Path("..") / "policy" / "SYSTEM.md")
        write_caller_workflow(
            repository / ".github/workflows/assurance.yml",
            adoption_path,
            "a" * 40,
        )
        base_sha = commit_test_repository(repository, "symlinked system base")

        system_target.write_text(
            "# System\nbase statement\nINV-CORE-001 resolved target update\n",
            encoding="utf-8",
        )
        head_sha = commit_test_repository(repository, "edit resolved system target")

        completed, runner_temp = run_workflow_materializer(
            root, repository, base_sha, head_sha, adoption_path
        )
        output = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, output)
        assurance_diff = (runner_temp / "assurance-diff.txt").read_text(
            encoding="utf-8"
        )
        self.assertIn("+INV-CORE-001", assurance_diff)
        self.assertNotIn("policy/SYSTEM.md", assurance_diff)

    def test_workflow_symlink_target_name_cannot_satisfy_strict_routing(self):
        root = self.make_tmp()
        repository = root / "repo"
        init_git_test_repository(repository)
        adoption_path = ".agentic-assurance/adoption.yaml"
        adoption = workflow_policy_adoption(stage="DRAFT", version="v0.4.0")
        adoption["paths"] = {"system": "assurance/SYSTEM.md"}
        adoption["components"] = {
            "app": {
                "paths": ["src/**"],
                "invariants": ["INV-CORE-001"],
            }
        }
        write_yaml(repository / adoption_path, adoption)
        policy = repository / "policy"
        policy.mkdir()
        (policy / "old.md").write_text(
            "# Old system policy\nNo invariant token here.\n", encoding="utf-8"
        )
        (policy / "INV-CORE-001.md").write_text(
            "# New system policy\nStill no token in the prose.\n", encoding="utf-8"
        )
        system_alias = repository / "assurance" / "SYSTEM.md"
        system_alias.parent.mkdir()
        system_alias.symlink_to(Path("..") / "policy" / "old.md")
        source = repository / "src" / "app.py"
        source.parent.mkdir()
        source.write_text("VALUE = 1\n", encoding="utf-8")
        write_caller_workflow(
            repository / ".github/workflows/assurance.yml",
            adoption_path,
            "a" * 40,
        )
        base_sha = commit_test_repository(repository, "symlink routing base")

        system_alias.unlink()
        system_alias.symlink_to(Path("..") / "policy" / "INV-CORE-001.md")
        source.write_text("VALUE = 2\n", encoding="utf-8")
        head_sha = commit_test_repository(repository, "retarget system symlink")

        completed, runner_temp = run_workflow_materializer(
            root, repository, base_sha, head_sha, adoption_path
        )
        output = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, output)
        assurance_diff_path = runner_temp / "assurance-diff.txt"
        assurance_diff = assurance_diff_path.read_text(encoding="utf-8")
        self.assertNotIn("+../policy/INV-CORE-001.md", assurance_diff)

        changed = runner_temp / "changed-for-routing.txt"
        changed.write_text("src/app.py\n", encoding="utf-8")
        body = runner_temp / "body-for-routing.txt"
        body.write_text(
            "Assurance policy change: intentional symlink relocation\n",
            encoding="utf-8",
        )
        code, drift_out = run_validator(
            [
                "drift",
                "--adoption",
                str(repository / adoption_path),
                "--changed-files",
                str(changed),
                "--pr-body",
                str(body),
                "--assurance-diff",
                str(assurance_diff_path),
                "--base-adoption",
                str(runner_temp / "base-adoption.yaml"),
                "--base-registers-root",
                str(runner_temp / "base-tree"),
                "--project-root",
                str(repository),
                "--adoption-path-transition",
                str(runner_temp / "adoption-path-transition.json"),
                "--strict",
            ]
        )
        self.assertEqual(code, 1, drift_out)
        self.assertIn("without an assurance update", drift_out)
        self.assertNotIn("assurance update references INV-CORE-001", drift_out)

    def assert_workflow_unchanged_policy_relocation_is_not_evidence(
        self, *, keep_source
    ):
        root = self.make_tmp()
        repository = root / "repo"
        init_git_test_repository(repository)
        adoption_path = ".agentic-assurance/adoption.yaml"
        base = workflow_policy_adoption(stage="DRAFT", version="v0.4.0")
        base["paths"] = {"system": "policy/old.md"}
        base["components"] = {
            "app": {
                "paths": ["src/**"],
                "invariants": ["INV-CORE-001"],
            }
        }
        write_yaml(repository / adoption_path, base)
        old_policy = repository / "policy" / "old.md"
        old_policy.parent.mkdir()
        old_policy.write_text(
            "# System\nExisting INV-CORE-001 policy text.\n",
            encoding="utf-8",
        )
        source = repository / "src" / "app.py"
        source.parent.mkdir()
        source.write_text("VALUE = 1\n", encoding="utf-8")
        write_caller_workflow(
            repository / ".github/workflows/assurance.yml",
            adoption_path,
            "a" * 40,
        )
        base_sha = commit_test_repository(repository, "policy relocation base")

        head = copy.deepcopy(base)
        head["paths"]["system"] = "policy/new.md"
        write_yaml(repository / adoption_path, head)
        new_policy = repository / "policy" / "new.md"
        if keep_source:
            shutil.copy2(old_policy, new_policy)
        else:
            old_policy.rename(new_policy)
        source.write_text("VALUE = 2\n", encoding="utf-8")
        head_sha = commit_test_repository(
            repository, "copy policy" if keep_source else "rename policy"
        )

        completed, runner_temp = run_workflow_materializer(
            root, repository, base_sha, head_sha, adoption_path
        )
        output = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, output)
        assurance_diff_path = runner_temp / "assurance-diff.txt"
        assurance_diff = assurance_diff_path.read_text(encoding="utf-8")
        self.assertNotIn("+Existing INV-CORE-001 policy text.", assurance_diff)

        changed = runner_temp / "changed-for-routing.txt"
        changed.write_text("src/app.py\n", encoding="utf-8")
        body = runner_temp / "body-for-routing.txt"
        body.write_text(
            "Assurance policy change: intentional policy relocation\n",
            encoding="utf-8",
        )
        code, drift_out = run_validator(
            [
                "drift",
                "--adoption",
                str(repository / adoption_path),
                "--changed-files",
                str(changed),
                "--pr-body",
                str(body),
                "--assurance-diff",
                str(assurance_diff_path),
                "--base-adoption",
                str(runner_temp / "base-adoption.yaml"),
                "--base-registers-root",
                str(runner_temp / "base-tree"),
                "--project-root",
                str(repository),
                "--adoption-path-transition",
                str(runner_temp / "adoption-path-transition.json"),
                "--strict",
            ]
        )
        self.assertEqual(code, 1, drift_out)
        self.assertIn("without an assurance update", drift_out)
        self.assertNotIn("assurance update references INV-CORE-001", drift_out)

    def test_workflow_unchanged_policy_rename_is_not_added_evidence(self):
        self.assert_workflow_unchanged_policy_relocation_is_not_evidence(
            keep_source=False
        )

    def test_workflow_unchanged_policy_copy_is_not_added_evidence(self):
        self.assert_workflow_unchanged_policy_relocation_is_not_evidence(
            keep_source=True
        )

    def test_workflow_evidence_uses_merge_base_not_moving_base_tip(self):
        root = self.make_tmp()
        repository = root / "repo"
        init_git_test_repository(repository)
        default_branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        adoption_path = ".agentic-assurance/adoption.yaml"
        adoption = workflow_policy_adoption(stage="DRAFT", version="v0.4.0")
        adoption["paths"] = {"system": "policy/system.md"}
        adoption["components"] = {
            "app": {
                "paths": ["src/**"],
                "invariants": ["INV-CORE-001"],
            }
        }
        write_yaml(repository / adoption_path, adoption)
        policy = repository / "policy" / "system.md"
        policy.parent.mkdir()
        policy.write_text("Existing INV-CORE-001 policy line\n", encoding="utf-8")
        source = repository / "src" / "app.py"
        source.parent.mkdir()
        source.write_text("VALUE = 1\n", encoding="utf-8")
        write_caller_workflow(
            repository / ".github/workflows/assurance.yml",
            adoption_path,
            "a" * 40,
        )
        common_sha = commit_test_repository(repository, "common branch point")

        subprocess.run(
            ["git", "switch", "-qc", "pr-branch"], cwd=repository, check=True
        )
        source.write_text("VALUE = 2\n", encoding="utf-8")
        head_sha = commit_test_repository(repository, "source-only PR change")

        subprocess.run(
            ["git", "switch", "-q", default_branch], cwd=repository, check=True
        )
        self.assertEqual(
            subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repository,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip(),
            common_sha,
        )
        policy.write_text("Policy line removed on base branch\n", encoding="utf-8")
        base_tip_sha = commit_test_repository(repository, "base branch advances")
        subprocess.run(
            ["git", "switch", "-q", "pr-branch"], cwd=repository, check=True
        )

        completed, runner_temp = run_workflow_materializer(
            root, repository, base_tip_sha, head_sha, adoption_path
        )
        output = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, output)
        assurance_diff_path = runner_temp / "assurance-diff.txt"
        assurance_diff = assurance_diff_path.read_text(encoding="utf-8")
        self.assertNotIn("+INV-CORE-001", assurance_diff)

        changed = runner_temp / "changed-for-routing.txt"
        changed.write_text("src/app.py\n", encoding="utf-8")
        code, drift_out = run_validator(
            [
                "drift",
                "--adoption",
                str(repository / adoption_path),
                "--changed-files",
                str(changed),
                "--pr-body",
                str(runner_temp / "missing-body.txt"),
                "--assurance-diff",
                str(assurance_diff_path),
                "--base-adoption",
                str(runner_temp / "base-adoption.yaml"),
                "--base-registers-root",
                str(runner_temp / "base-tree"),
                "--project-root",
                str(repository),
                "--adoption-path-transition",
                str(runner_temp / "adoption-path-transition.json"),
                "--strict",
            ]
        )
        self.assertEqual(code, 1, drift_out)
        self.assertIn("without an assurance update", drift_out)

    def test_workflow_binary_blob_cannot_supply_invariant_evidence(self):
        root = self.make_tmp()
        repository = root / "repo"
        init_git_test_repository(repository)
        adoption_path = ".agentic-assurance/adoption.yaml"
        adoption = workflow_policy_adoption(stage="DRAFT", version="v0.4.0")
        adoption["specification_workflow"]["root"] = "."
        write_yaml(repository / adoption_path, adoption)
        write_caller_workflow(
            repository / ".github/workflows/assurance.yml",
            adoption_path,
            "a" * 40,
        )
        base_sha = commit_test_repository(repository, "binary evidence base")
        binary = repository / "assurance" / "evidence" / "proof.bin"
        binary.parent.mkdir(parents=True)
        binary.write_bytes(b"\x00binary INV-CORE-001 metadata\n\xff\x00")
        (binary.parent / "proof.pdf").write_bytes(
            b"\n%PDF-1.4\nINV-CORE-001 uncompressed metadata\n%%EOF\n"
        )
        head_sha = commit_test_repository(repository, "add binary evidence")

        completed, runner_temp = run_workflow_materializer(
            root, repository, base_sha, head_sha, adoption_path
        )
        output = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, output)
        assurance_diff = (runner_temp / "assurance-diff.txt").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("+INV-CORE-001", assurance_diff)

    def test_workflow_old_line_survives_text_eligibility_transition(self):
        root = self.make_tmp()
        repository = root / "repo"
        init_git_test_repository(repository)
        adoption_path = ".agentic-assurance/adoption.yaml"
        adoption = workflow_policy_adoption(stage="DRAFT", version="v0.4.0")
        adoption["paths"] = {"system": "policy/system.md"}
        write_yaml(repository / adoption_path, adoption)
        policy = repository / "policy" / "system.md"
        policy.parent.mkdir()
        policy.write_bytes(b"Existing INV-CORE-001 policy line\n\x00junk\n")
        write_caller_workflow(
            repository / ".github/workflows/assurance.yml",
            adoption_path,
            "a" * 40,
        )
        base_sha = commit_test_repository(repository, "binary-classified policy base")
        policy.write_text(
            "Existing INV-CORE-001 policy line\n", encoding="utf-8"
        )
        head_sha = commit_test_repository(repository, "remove unrelated binary byte")

        completed, runner_temp = run_workflow_materializer(
            root, repository, base_sha, head_sha, adoption_path
        )
        output = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, output)
        assurance_diff = (runner_temp / "assurance-diff.txt").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("+INV-CORE-001", assurance_diff)

    def test_workflow_attributes_cannot_hide_old_copy_source(self):
        root = self.make_tmp()
        repository = root / "repo"
        init_git_test_repository(repository)
        adoption_path = ".agentic-assurance/adoption.yaml"
        base = workflow_policy_adoption(stage="DRAFT", version="v0.4.0")
        base["paths"] = {"system": "policy/old.md"}
        write_yaml(repository / adoption_path, base)
        old_policy = repository / "policy" / "old.md"
        old_policy.parent.mkdir()
        old_policy.write_text(
            "Existing INV-CORE-001 policy line\n", encoding="utf-8"
        )
        (repository / ".gitattributes").write_text(
            "policy/old.md binary\n", encoding="utf-8"
        )
        write_caller_workflow(
            repository / ".github/workflows/assurance.yml",
            adoption_path,
            "a" * 40,
        )
        base_sha = commit_test_repository(repository, "attribute-hidden copy base")

        head = copy.deepcopy(base)
        head["paths"]["system"] = "policy/new.md"
        write_yaml(repository / adoption_path, head)
        shutil.copy2(old_policy, repository / "policy" / "new.md")
        head_sha = commit_test_repository(repository, "copy attribute-hidden policy")

        completed, runner_temp = run_workflow_materializer(
            root, repository, base_sha, head_sha, adoption_path
        )
        output = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, output)
        assurance_diff = (runner_temp / "assurance-diff.txt").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("+INV-CORE-001", assurance_diff)

    def test_workflow_git_diagnostics_are_drained_and_fail_closed(self):
        root = self.make_tmp()
        repository = root / "repo"
        init_git_test_repository(repository)
        adoption_path = ".agentic-assurance/adoption.yaml"
        adoption = workflow_policy_adoption(stage="DRAFT", version="v0.4.0")
        adoption["specification_workflow"]["root"] = "."
        write_yaml(repository / adoption_path, adoption)
        write_caller_workflow(
            repository / ".github/workflows/assurance.yml",
            adoption_path,
            "a" * 40,
        )
        base_sha = commit_test_repository(repository, "diagnostic drain base")
        marker = repository / "marker.txt"
        marker.write_text("head\n", encoding="utf-8")
        head_sha = commit_test_repository(repository, "diagnostic drain head")

        # Wrap Git so each grep emits more than ordinary pipe capacity on
        # stderr after delegating to the real binary. A stdout-first reader
        # deadlocks; the workflow's selector drain consumes both streams and
        # then fails closed on the diagnostic.
        real_git = shutil.which("git")
        self.assertIsNotNone(real_git)
        wrapper_dir = root / "bin"
        wrapper_dir.mkdir()
        wrapper = wrapper_dir / "git"
        wrapper.write_text(
            f"#!{sys.executable}\n"
            "import os, subprocess, sys\n"
            f"completed = subprocess.run([{real_git!r}, *sys.argv[1:]])\n"
            "if 'grep' in sys.argv[1:]:\n"
            "    os.write(2, b'x' * (256 * 1024))\n"
            "raise SystemExit(completed.returncode)\n",
            encoding="utf-8",
        )
        wrapper.chmod(0o755)

        completed, _runner_temp = run_workflow_materializer(
            root,
            repository,
            base_sha,
            head_sha,
            adoption_path,
            env_updates={
                "PATH": str(wrapper_dir) + os.pathsep + os.environ.get("PATH", "")
            },
        )
        output = completed.stdout + completed.stderr
        self.assertNotEqual(completed.returncode, 0, output)
        self.assertIn("Could not complete Git while locating", output)
        self.assertNotIn("Traceback", output)

    def test_workflow_symlink_to_regular_target_name_is_not_evidence(self):
        root = self.make_tmp()
        repository = root / "repo"
        init_git_test_repository(repository)
        adoption_path = ".agentic-assurance/adoption.yaml"
        adoption = workflow_policy_adoption(stage="DRAFT", version="v0.4.0")
        adoption["paths"] = {"system": "policy/spec.md"}
        write_yaml(repository / adoption_path, adoption)
        policy = repository / "policy"
        policy.mkdir()
        (policy / "INV-CORE-001").write_text(
            "Target exists without policy prose\n", encoding="utf-8"
        )
        spec = policy / "spec.md"
        spec.symlink_to("INV-CORE-001")
        write_caller_workflow(
            repository / ".github/workflows/assurance.yml",
            adoption_path,
            "a" * 40,
        )
        base_sha = commit_test_repository(repository, "symlink mode base")
        spec.unlink()
        spec.write_text("INV-CORE-001", encoding="utf-8")
        head_sha = commit_test_repository(repository, "replace symlink with regular")

        completed, runner_temp = run_workflow_materializer(
            root, repository, base_sha, head_sha, adoption_path
        )
        output = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, output)
        assurance_diff = (runner_temp / "assurance-diff.txt").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("+INV-CORE-001", assurance_diff)

    def test_workflow_regular_to_symlink_resolved_copy_is_not_evidence(self):
        root = self.make_tmp()
        repository = root / "repo"
        init_git_test_repository(repository)
        adoption_path = ".agentic-assurance/adoption.yaml"
        adoption = workflow_policy_adoption(stage="DRAFT", version="v0.4.0")
        adoption["paths"] = {"system": "policy/spec.md"}
        write_yaml(repository / adoption_path, adoption)
        policy = repository / "policy"
        policy.mkdir()
        spec = policy / "spec.md"
        spec.write_text("INV-CORE-001\n", encoding="utf-8")
        write_caller_workflow(
            repository / ".github/workflows/assurance.yml",
            adoption_path,
            "a" * 40,
        )
        base_sha = commit_test_repository(repository, "regular mode base")
        target = policy / "target.md"
        shutil.copy2(spec, target)
        spec.unlink()
        spec.symlink_to("target.md")
        head_sha = commit_test_repository(repository, "replace regular with symlink")

        completed, runner_temp = run_workflow_materializer(
            root, repository, base_sha, head_sha, adoption_path
        )
        output = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, output)
        assurance_diff = (runner_temp / "assurance-diff.txt").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("+INV-CORE-001", assurance_diff)

    def test_workflow_low_similarity_move_preserves_no_old_line_evidence(self):
        root = self.make_tmp()
        repository = root / "repo"
        init_git_test_repository(repository)
        adoption_path = ".agentic-assurance/adoption.yaml"
        base = workflow_policy_adoption(stage="DRAFT", version="v0.4.0")
        base["paths"] = {"system": "policy/old.md"}
        write_yaml(repository / adoption_path, base)
        old_policy = repository / "policy" / "old.md"
        old_policy.parent.mkdir()
        old_policy.write_text(
            "\n".join(
                [f"old surrounding line {index}" for index in range(100)]
                + ["Stable INV-CORE-001 policy line"]
            )
            + "\n",
            encoding="utf-8",
        )
        write_caller_workflow(
            repository / ".github/workflows/assurance.yml",
            adoption_path,
            "a" * 40,
        )
        base_sha = commit_test_repository(repository, "low similarity move base")

        head = copy.deepcopy(base)
        head["paths"]["system"] = "policy/new.md"
        write_yaml(repository / adoption_path, head)
        old_policy.unlink()
        (repository / "policy" / "new.md").write_text(
            "\n".join(
                [f"different surrounding line {index}" for index in range(100)]
                + ["Stable INV-CORE-001 policy line"]
            )
            + "\n",
            encoding="utf-8",
        )
        head_sha = commit_test_repository(repository, "low similarity policy move")

        completed, runner_temp = run_workflow_materializer(
            root, repository, base_sha, head_sha, adoption_path
        )
        output = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, output)
        assurance_diff = (runner_temp / "assurance-diff.txt").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("+INV-CORE-001", assurance_diff)

    def test_workflow_inline_lite_ignores_unrelated_split_symlink(self):
        root = self.make_tmp()
        repository = root / "repo"
        init_git_test_repository(repository)
        adoption_path = ".agentic-assurance/adoption.yaml"
        adoption = workflow_policy_adoption(stage="DRAFT", version="v0.4.0")
        adoption["layout"] = "lite"
        write_yaml(repository / adoption_path, adoption)
        assurance_path = repository / LITE_ASSURANCE_PATH
        write_yaml(assurance_path, baseline_lite_assurance())
        outside = root / "outside-assurance"
        outside.mkdir()
        (repository / "assurance").symlink_to(
            outside, target_is_directory=True
        )
        write_caller_workflow(
            repository / ".github/workflows/assurance.yml",
            adoption_path,
            "a" * 40,
        )
        base_sha = commit_test_repository(repository, "inline lite base")

        assurance = baseline_lite_assurance()
        assurance["purpose"] = "Updated lite purpose for INV-CORE-001"
        write_yaml(assurance_path, assurance)
        head_sha = commit_test_repository(repository, "update lite assurance")
        completed, runner_temp = run_workflow_materializer(
            root, repository, base_sha, head_sha, adoption_path
        )
        output = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, output)
        assurance_diff = (runner_temp / "assurance-diff.txt").read_text(
            encoding="utf-8"
        )
        self.assertIn("+INV-CORE-001", assurance_diff)
        self.assertNotIn(LITE_ASSURANCE_PATH, assurance_diff)

    def test_workflow_inline_lite_decoy_cannot_satisfy_strict_routing(self):
        root = self.make_tmp()
        repository = root / "repo"
        init_git_test_repository(repository)
        adoption_path = ".agentic-assurance/adoption.yaml"
        adoption = workflow_policy_adoption(stage="DRAFT", version="v0.4.0")
        adoption["layout"] = "lite"
        adoption["components"] = {
            "app": {
                "paths": ["src/**"],
                "invariants": ["INV-CORE-001"],
            }
        }
        write_yaml(repository / adoption_path, adoption)
        write_yaml(repository / LITE_ASSURANCE_PATH, baseline_lite_assurance())
        source = repository / "src" / "app.py"
        source.parent.mkdir()
        source.write_text("VALUE = 1\n", encoding="utf-8")
        decoy = repository / "assurance" / "notes.txt"
        decoy.parent.mkdir()
        decoy.write_text("ordinary notes\n", encoding="utf-8")
        write_caller_workflow(
            repository / ".github/workflows/assurance.yml",
            adoption_path,
            "a" * 40,
        )
        base_sha = commit_test_repository(repository, "inline lite routing base")

        source.write_text("VALUE = 2\n", encoding="utf-8")
        decoy.write_text("ordinary notes\nINV-CORE-001\n", encoding="utf-8")
        head_sha = commit_test_repository(repository, "source and decoy edit")
        completed, runner_temp = run_workflow_materializer(
            root, repository, base_sha, head_sha, adoption_path
        )
        output = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, output)
        assurance_diff_path = runner_temp / "assurance-diff.txt"
        assurance_diff = assurance_diff_path.read_text(encoding="utf-8")
        self.assertNotIn("assurance/notes.txt", assurance_diff)
        self.assertNotIn("+INV-CORE-001", assurance_diff)

        changed = runner_temp / "changed.txt"
        changed.write_text("src/app.py\n", encoding="utf-8")
        code, drift_out = run_validator(
            [
                "drift",
                "--adoption",
                str(repository / adoption_path),
                "--changed-files",
                str(changed),
                "--pr-body",
                str(runner_temp / "missing-body.txt"),
                "--assurance-diff",
                str(assurance_diff_path),
                "--strict",
            ]
        )
        self.assertEqual(code, 1, drift_out)
        self.assertIn("without an assurance update", drift_out)

    def test_workflow_lite_fallback_system_target_remains_in_diff(self):
        root = self.make_tmp()
        repository = root / "repo"
        init_git_test_repository(repository)
        adoption_path = ".agentic-assurance/adoption.yaml"
        adoption = workflow_policy_adoption(stage="DRAFT", version="v0.4.0")
        adoption["layout"] = "lite"
        write_yaml(repository / adoption_path, adoption)
        assurance = baseline_lite_assurance()
        assurance.pop("system")
        write_yaml(repository / LITE_ASSURANCE_PATH, assurance)
        target = repository / "policy" / "SYSTEM.md"
        target.parent.mkdir()
        target.write_text("# System\nbase\n", encoding="utf-8")
        alias = repository / "assurance" / "SYSTEM.md"
        alias.parent.mkdir()
        alias.symlink_to(Path("..") / "policy" / "SYSTEM.md")
        write_caller_workflow(
            repository / ".github/workflows/assurance.yml",
            adoption_path,
            "a" * 40,
        )
        base_sha = commit_test_repository(repository, "lite fallback base")

        target.write_text("# System\nbase\nINV-CORE-001 update\n", encoding="utf-8")
        head_sha = commit_test_repository(repository, "update lite fallback")
        completed, runner_temp = run_workflow_materializer(
            root, repository, base_sha, head_sha, adoption_path
        )
        output = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, output)
        assurance_diff = (runner_temp / "assurance-diff.txt").read_text(
            encoding="utf-8"
        )
        self.assertIn("+INV-CORE-001", assurance_diff)
        self.assertNotIn("policy/SYSTEM.md", assurance_diff)

    def test_workflow_split_ignores_unrelated_lite_symlink(self):
        root = self.make_tmp()
        repository = root / "repo"
        init_git_test_repository(repository)
        adoption_path = ".agentic-assurance/adoption.yaml"
        adoption = workflow_policy_adoption(stage="DRAFT", version="v0.4.0")
        write_yaml(repository / adoption_path, adoption)
        (repository / "AGENTIC_ASSURANCE.md").write_text(
            "# Assurance\nbase\n", encoding="utf-8"
        )
        outside = root / "outside-lite.yaml"
        outside.write_text("outside\n", encoding="utf-8")
        lite_alias = repository / LITE_ASSURANCE_PATH
        lite_alias.parent.mkdir(parents=True, exist_ok=True)
        lite_alias.symlink_to(outside)
        write_caller_workflow(
            repository / ".github/workflows/assurance.yml",
            adoption_path,
            "a" * 40,
        )
        base_sha = commit_test_repository(repository, "split base with lite decoy")

        (repository / "AGENTIC_ASSURANCE.md").write_text(
            "# Assurance\nbase\nINV-CORE-001 updated\n", encoding="utf-8"
        )
        head_sha = commit_test_repository(repository, "update split guide")
        completed, runner_temp = run_workflow_materializer(
            root, repository, base_sha, head_sha, adoption_path
        )
        output = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, output)
        assurance_diff = (runner_temp / "assurance-diff.txt").read_text(
            encoding="utf-8"
        )
        self.assertIn("+INV-CORE-001", assurance_diff)
        self.assertNotIn("AGENTIC_ASSURANCE.md", assurance_diff)

    def test_workflow_fallback_deduplicates_tracked_symlink_alias(self):
        root = self.make_tmp()
        repository = root / "repo"
        init_git_test_repository(repository)

        target_path = "config/adoption.yaml"
        alias_path = ".agentic-assurance/adoption.yaml"
        write_yaml(repository / target_path, workflow_policy_adoption())
        alias = repository / alias_path
        alias.parent.mkdir(parents=True)
        alias.symlink_to("../config/adoption.yaml")
        old_caller = repository / ".github/workflows/old-assurance.yml"
        write_caller_workflow(old_caller, alias_path, "a" * 40)
        base_sha = commit_test_repository(repository, "aliased declaration base")

        # Renaming the caller makes exact same-path recovery impossible. The
        # bounded fallback sees both the tracked target and its tracked alias;
        # they are one declaration identity, not an ambiguous pair.
        old_caller.unlink()
        write_caller_workflow(
            repository / ".github/workflows/new-assurance.yml",
            alias_path,
            "b" * 40,
        )
        head_sha = commit_test_repository(repository, "rename assurance caller")

        completed, runner_temp = run_workflow_materializer(
            root,
            repository,
            base_sha,
            head_sha,
            alias_path,
            caller_name="new-assurance.yml",
        )
        output = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, output)
        self.assertIn("bounded declaration discovery", output.lower())
        self.assertNotIn("multiple prior AAP declarations", output)
        materialized = json.loads(
            (runner_temp / "base-adoption.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual(materialized["adoption_stage"], "HUMAN_REVIEWED")
        transition = json.loads(
            (runner_temp / "adoption-path-transition.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(transition["head"], alias_path)
        self.assertIn(transition["base"], (alias_path, target_path))

    def test_workflow_fallback_discovers_legacy_mixed_profiles(self):
        root = self.make_tmp()
        repository = root / "repo"
        init_git_test_repository(repository)

        prior_path = "legacy/adoption.yaml"
        head_path = "config/adoption.yaml"
        legacy = workflow_policy_adoption(profiles=["core", "archived"])
        write_yaml(repository / prior_path, legacy)
        base_sha = commit_test_repository(repository, "legacy mixed-profile base")

        (repository / prior_path).unlink()
        write_yaml(repository / head_path, workflow_policy_adoption(profiles=["core"]))
        # The actual caller is new on HEAD, forcing the bounded identity
        # fallback against a base that predates archived exclusivity.
        write_caller_workflow(
            repository / ".github/workflows/assurance.yml", head_path, "b" * 40
        )
        head_sha = commit_test_repository(repository, "move and clean mixed profiles")

        completed, runner_temp = run_workflow_materializer(
            root, repository, base_sha, head_sha, head_path
        )
        output = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, output)
        materialized = json.loads(
            (runner_temp / "base-adoption.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual(materialized["profiles"], ["core", "archived"])
        transition = json.loads(
            (runner_temp / "adoption-path-transition.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            transition,
            {
                "base": prior_path,
                "head": head_path,
                "base_resolved": prior_path,
                "head_resolved": head_path,
            },
        )

    def test_workflow_fallback_preserves_full_historical_yaml_identity(self):
        def write_legacy_variant(path, variant):
            legacy = workflow_policy_adoption(
                stage="HUMAN_REVIEWED", version="v0.3.2"
            )
            if variant == "blank historical owner":
                legacy["project"]["human_owner"] = ""
                write_yaml(path, legacy)
            elif variant == "merge-key project":
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    """\
upstream:
  repository: MosslandOpenDevs/agentic-assurance-profile
  version: v0.3.2
  commit: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
project_defaults: &project_defaults
  name: Example Project
  repository: example/project
  human_owner: Alice Example
project:
  <<: *project_defaults
profiles: [core]
adoption_stage: HUMAN_REVIEWED
human_review:
  date: 2026-01-01
  reviewer: Alice Example
  record: docs/reviews/2026-01-01.md
specification_workflow:
  system: minimal
  root: AGENTIC_ASSURANCE.md
""",
                    encoding="utf-8",
                )
            else:
                raw = json.dumps(legacy, indent=2)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    raw.replace(
                        "{\n", '{\n  7: "historical extension",\n', 1
                    ),
                    encoding="utf-8",
                )

        for variant in (
            "blank historical owner",
            "merge-key project",
            "numeric extension key",
        ):
            with self.subTest(variant=variant):
                root = self.make_tmp()
                repository = root / "repo"
                init_git_test_repository(repository)
                prior_path = "legacy/adoption.yaml"
                head_path = "config/adoption.yaml"
                write_legacy_variant(repository / prior_path, variant)
                base_sha = commit_test_repository(
                    repository, f"{variant} reviewed base"
                )

                (repository / prior_path).unlink()
                head = workflow_policy_adoption(
                    stage="DRAFT", version="v0.4.0"
                )
                write_yaml(repository / head_path, head)
                write_caller_workflow(
                    repository / ".github/workflows/new-assurance.yml",
                    head_path,
                    "b" * 40,
                )
                head_sha = commit_test_repository(
                    repository, f"{variant} move and downgrade"
                )

                completed, runner_temp = run_workflow_materializer(
                    root,
                    repository,
                    base_sha,
                    head_sha,
                    head_path,
                    caller_name="new-assurance.yml",
                )
                output = completed.stdout + completed.stderr
                self.assertEqual(completed.returncode, 0, output)
                self.assertNotIn("policy comparison skipped", output)
                materialized = runner_temp / "base-adoption.yaml"
                self.assertTrue(materialized.is_file(), output)

                (runner_temp / "changed-empty.txt").write_bytes(b"")
                (runner_temp / "body-empty.txt").write_bytes(b"")
                code, drift_out = run_validator(
                    [
                        "drift",
                        "--adoption",
                        str(repository / head_path),
                        "--changed-files",
                        str(runner_temp / "changed-empty.txt"),
                        "--pr-body",
                        str(runner_temp / "body-empty.txt"),
                        "--base-adoption",
                        str(materialized),
                        "--adoption-path-transition",
                        str(runner_temp / "adoption-path-transition.json"),
                    ]
                )
                self.assertEqual(code, 1, drift_out)
                self.assertIn("stage downgraded", drift_out)

    def test_workflow_fallback_never_skips_unloadable_canonical_legacy_base(self):
        for variant in (
            "oversized file",
            "oversized numeric token",
            "flow JSON oversized numeric token",
            "escaped flow JSON oversized numeric token",
        ):
            with self.subTest(variant=variant):
                root = self.make_tmp()
                repository = root / "repo"
                init_git_test_repository(repository)
                prior_path = "legacy/adoption.yaml"
                head_path = "config/adoption.yaml"
                legacy = workflow_policy_adoption(
                    stage="HUMAN_REVIEWED", version="v0.3.2"
                )
                if "flow JSON" in variant:
                    raw = json.dumps(legacy, separators=(",", ":"))
                    if variant.startswith("escaped"):
                        raw = raw.replace('"upstream"', '"up\\u0073tream"', 1)
                        raw = raw.replace(
                            "agentic-assurance-profile",
                            "agentic-assurance-pro\\u0066ile",
                            1,
                        )
                    raw = raw[:-1] + ',"oversized":' + "7" * 4097 + "}\n"
                else:
                    raw = json.dumps(legacy, indent=2)
                    extension = (
                        '"oversized": "'
                        + "x" * (5 * 1024 * 1024 + 1)
                        + '"'
                        if variant == "oversized file"
                        else '"oversized": ' + "7" * 4097
                    )
                    raw = raw[:-2] + f",\n  {extension}\n}}\n"
                prior = repository / prior_path
                prior.parent.mkdir(parents=True)
                prior.write_text(raw, encoding="utf-8")
                base_sha = commit_test_repository(
                    repository, f"{variant} canonical legacy base"
                )

                prior.unlink()
                write_yaml(
                    repository / head_path,
                    workflow_policy_adoption(stage="DRAFT", version="v0.4.0"),
                )
                write_caller_workflow(
                    repository / ".github/workflows/new-assurance.yml",
                    head_path,
                    "b" * 40,
                )
                head_sha = commit_test_repository(
                    repository, f"{variant} move and downgrade"
                )

                completed, _ = run_workflow_materializer(
                    root,
                    repository,
                    base_sha,
                    head_sha,
                    head_path,
                    caller_name="new-assurance.yml",
                )
                output = completed.stdout + completed.stderr
                self.assertNotEqual(completed.returncode, 0, output)
                self.assertIn("strong canonical AAP identity", output)
                self.assertNotIn("policy comparison skipped", output)
                self.assertNotIn("Traceback", output)

    def test_workflow_historical_identity_projection_matches_yaml_semantics(self):
        canonical_upstream = """\
repository: MosslandOpenDevs/agentic-assurance-profile
version: v0.3.2
commit: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
"""
        project_and_profiles = """\
project:
  name: Example Project
  repository: example/project
  human_owner: Alice Example
profiles: [core]
"""
        huge_number = "7" * 4097
        cases = {
            "explicit escaped mapping key": (
                '? "up\\u0073tream"\n'
                ":\n"
                + "".join(
                    f"  {line}\n"
                    for line in canonical_upstream.rstrip("\n").split("\n")
                )
                + project_and_profiles
                + f"oversized: {huge_number}\n",
                True,
            ),
            "top-level and nested merge aliases": (
                "upstream-fields: &upstream-fields\n"
                + "".join(
                    f"  {line}\n"
                    for line in canonical_upstream.rstrip("\n").split("\n")
                )
                + "identity: &identity\n"
                + "  upstream:\n"
                + "    <<: *upstream-fields\n"
                + "".join(
                    f"  {line}\n"
                    for line in project_and_profiles.rstrip("\n").split("\n")
                )
                + "<<: *identity\n"
                + f"oversized: {huge_number}\n",
                True,
            ),
            "canonical duplicate wins last": (
                "upstream:\n"
                "  repository: example/not-aap\n"
                "upstream:\n"
                + "".join(
                    f"  {line}\n"
                    for line in canonical_upstream.rstrip("\n").split("\n")
                )
                + project_and_profiles
                + f"oversized: {huge_number}\n",
                True,
            ),
            "noncanonical duplicate wins last": (
                "upstream:\n"
                + "".join(
                    f"  {line}\n"
                    for line in canonical_upstream.rstrip("\n").split("\n")
                )
                + "upstream:\n"
                "  repository: example/not-aap\n"
                + project_and_profiles
                + f"oversized: {huge_number}\n",
                False,
            ),
            "quoted merge key stays ordinary": (
                "identity: &identity\n"
                "  upstream:\n"
                + "".join(
                    f"    {line}\n"
                    for line in canonical_upstream.rstrip("\n").split("\n")
                )
                + "".join(
                    f"  {line}\n"
                    for line in project_and_profiles.rstrip("\n").split("\n")
                )
                + '"<<": *identity\n'
                + f"oversized: {huge_number}\n",
                False,
            ),
            "repeated merge aliases stay projection-bounded": (
                "identity: &identity\n"
                "  upstream:\n"
                + "".join(
                    f"    {line}\n"
                    for line in canonical_upstream.rstrip("\n").split("\n")
                )
                + "".join(
                    f"  {line}\n"
                    for line in project_and_profiles.rstrip("\n").split("\n")
                )
                + "<<: ["
                + ",".join("*identity" for _ in range(100_001))
                + "]\n",
                True,
            ),
            "strong first document cannot be skipped": (
                "upstream:\n"
                + "".join(
                    f"  {line}\n"
                    for line in canonical_upstream.rstrip("\n").split("\n")
                )
                + project_and_profiles
                + "---\nunrelated: second document\n",
                True,
            ),
            "large unrelated flow data remains skippable": (
                '{"padding":"'
                + "x" * (5 * 1024 * 1024 + 1)
                + '","items":['
                + ",".join("{}" for _ in range(100_100))
                + "]}\n",
                False,
            ),
        }
        for name, (raw, must_fail_closed) in cases.items():
            with self.subTest(name=name):
                root = self.make_tmp()
                repository = root / "repo"
                init_git_test_repository(repository)
                prior_path = "legacy/adoption.yaml"
                head_path = "config/adoption.yaml"
                prior = repository / prior_path
                prior.parent.mkdir(parents=True)
                prior.write_text(raw, encoding="utf-8")
                base_sha = commit_test_repository(repository, name)

                prior.unlink()
                write_yaml(
                    repository / head_path,
                    workflow_policy_adoption(stage="DRAFT", version="v0.4.0"),
                )
                write_caller_workflow(
                    repository / ".github/workflows/new-assurance.yml",
                    head_path,
                    "b" * 40,
                )
                head_sha = commit_test_repository(repository, f"{name} head")

                completed, _ = run_workflow_materializer(
                    root,
                    repository,
                    base_sha,
                    head_sha,
                    head_path,
                    caller_name="new-assurance.yml",
                )
                output = completed.stdout + completed.stderr
                if must_fail_closed:
                    self.assertNotEqual(completed.returncode, 0, output)
                    self.assertIn("strong canonical AAP identity", output)
                    self.assertNotIn("policy comparison skipped", output)
                else:
                    self.assertEqual(completed.returncode, 0, output)
                    self.assertIn("policy comparison skipped", output)
                self.assertNotIn("Traceback", output)

    def test_workflow_historical_materialization_is_output_bounded(self):
        root = self.make_tmp()
        repository = root / "repo"
        init_git_test_repository(repository)
        prior_path = "legacy/adoption.yaml"
        head_path = "config/adoption.yaml"
        prior = repository / prior_path
        prior.parent.mkdir(parents=True)
        repeated_aliases = "".join("  - *payload\n" for _ in range(100))
        prior.write_text(
            "payload: &payload \"" + "x" * 65536 + "\"\n"
            "expanded:\n"
            + repeated_aliases
            + """\
upstream:
  repository: MosslandOpenDevs/agentic-assurance-profile
  version: v0.3.2
  commit: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
project:
  name: Example Project
  repository: example/project
  human_owner: Alice Example
profiles: [core]
profiles: [core]
adoption_stage: HUMAN_REVIEWED
specification_workflow:
  system: minimal
  root: AGENTIC_ASSURANCE.md
""",
            encoding="utf-8",
        )
        base_sha = commit_test_repository(
            repository, "amplifying historical base"
        )

        prior.unlink()
        write_yaml(
            repository / head_path,
            workflow_policy_adoption(stage="DRAFT", version="v0.4.0"),
        )
        write_caller_workflow(
            repository / ".github/workflows/new-assurance.yml",
            head_path,
            "b" * 40,
        )
        head_sha = commit_test_repository(
            repository, "move amplifying historical base"
        )

        completed, runner_temp = run_workflow_materializer(
            root,
            repository,
            base_sha,
            head_sha,
            head_path,
            caller_name="new-assurance.yml",
        )
        output = completed.stdout + completed.stderr
        self.assertNotEqual(completed.returncode, 0, output)
        self.assertIn("cannot be materialized safely", output)
        self.assertIn("exceeds 5,242,880 bytes", output)
        self.assertFalse((runner_temp / "base-adoption.yaml").exists())
        self.assertFalse((runner_temp / "base-adoption.yaml.tmp").exists())
        self.assertNotIn("Traceback", output)

    def test_workflow_fallback_normalizes_pre_v04_duplicate_key_base(self):
        root = self.make_tmp()
        repository = root / "repo"
        init_git_test_repository(repository)

        prior_path = "legacy/adoption.yaml"
        head_path = "config/adoption.yaml"
        legacy = workflow_policy_adoption(stage="DRAFT")
        legacy["human_review"] = human_review_block()
        raw = json.dumps(legacy, indent=2)
        raw = raw[:-2] + ',\n  "adoption_stage": "HUMAN_REVIEWED"\n}\n'
        prior = repository / prior_path
        prior.parent.mkdir(parents=True)
        prior.write_text(raw, encoding="utf-8")
        base_sha = commit_test_repository(repository, "duplicate-key legacy base")

        prior.unlink()
        cleaned = copy.deepcopy(legacy)
        cleaned["adoption_stage"] = "HUMAN_REVIEWED"
        write_yaml(repository / head_path, cleaned)
        write_caller_workflow(
            repository / ".github/workflows/assurance.yml", head_path, "b" * 40
        )
        head_sha = commit_test_repository(repository, "clean duplicate and move")

        completed, runner_temp = run_workflow_materializer(
            root, repository, base_sha, head_sha, head_path
        )
        output = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, output)
        self.assertIn("legacy last-key-wins semantics", output)
        materialized = json.loads(
            (runner_temp / "base-adoption.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual(materialized["adoption_stage"], "HUMAN_REVIEWED")
        transition = json.loads(
            (runner_temp / "adoption-path-transition.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            transition,
            {
                "base": prior_path,
                "head": head_path,
                "base_resolved": prior_path,
                "head_resolved": head_path,
            },
        )

    def test_workflow_fallback_rejects_current_duplicate_key_base(self):
        root = self.make_tmp()
        repository = root / "repo"
        init_git_test_repository(repository)

        prior_path = "current/adoption.yaml"
        head_path = "config/adoption.yaml"
        current = workflow_policy_adoption(stage="DRAFT", version="v0.4.0")
        raw = json.dumps(current, indent=2)
        raw = raw[:-2] + ',\n  "adoption_stage": "HUMAN_REVIEWED"\n}\n'
        prior = repository / prior_path
        prior.parent.mkdir(parents=True)
        prior.write_text(raw, encoding="utf-8")
        base_sha = commit_test_repository(repository, "invalid current-contract base")

        prior.unlink()
        cleaned = copy.deepcopy(current)
        cleaned["adoption_stage"] = "HUMAN_REVIEWED"
        cleaned["human_review"] = human_review_block()
        write_yaml(repository / head_path, cleaned)
        write_caller_workflow(
            repository / ".github/workflows/assurance.yml", head_path, "b" * 40
        )
        head_sha = commit_test_repository(repository, "clean and move declaration")

        completed, runner_temp = run_workflow_materializer(
            root, repository, base_sha, head_sha, head_path
        )
        output = completed.stdout + completed.stderr
        self.assertNotEqual(completed.returncode, 0, output)
        self.assertIn(
            "cannot be parsed under its applicable strict contract",
            output,
        )
        self.assertFalse((runner_temp / "base-adoption.yaml").exists())

    def test_workflow_fallback_fails_closed_at_declaration_candidate_budget(self):
        root = self.make_tmp()
        repository = root / "repo"
        init_git_test_repository(repository)

        for index in range(17):
            adoption = workflow_policy_adoption()
            adoption["project"]["name"] = f"Candidate {index}"
            write_yaml(repository / f"legacy/candidate-{index}.yaml", adoption)
        base_sha = commit_test_repository(repository, "ambiguous declaration base")

        head_path = "config/adoption.yaml"
        write_yaml(repository / head_path, workflow_policy_adoption())
        write_caller_workflow(
            repository / ".github/workflows/assurance.yml", head_path, "b" * 40
        )
        head_sha = commit_test_repository(repository, "add new direct caller")

        completed, runner_temp = run_workflow_materializer(
            root, repository, base_sha, head_sha, head_path
        )
        output = completed.stdout + completed.stderr
        self.assertNotEqual(completed.returncode, 0, output)
        self.assertIn("16-candidate budget", output)
        self.assertFalse((runner_temp / "base-adoption.yaml").exists())

    def test_workflow_fallback_bounds_raw_listing_and_prefilter_entries(self):
        cases = (
            (
                "listing bytes",
                (
                    "MAX_DISCOVERY_LISTING_BYTES = 64 * 1024 * 1024",
                    "MAX_DISCOVERY_LISTING_BYTES = 1",
                ),
                "raw tracked-listing byte budget",
            ),
            (
                "prefilter entries",
                (
                    "MAX_DISCOVERY_FILES = 100_000",
                    "MAX_DISCOVERY_FILES = 1",
                ),
                "tracked-entry enumeration budget",
            ),
        )
        for label, replacement, expected in cases:
            with self.subTest(limit=label):
                root = self.make_tmp()
                repository = root / "repo"
                init_git_test_repository(repository)
                # These tracked names are filtered as trusted checkout data.
                # They must still consume raw enumeration work before that
                # filter, or an attacker can make discovery unbounded there.
                trusted = repository / ".assurance-profile-pin"
                trusted.mkdir()
                (trusted / "ignored-a").write_text("a", encoding="utf-8")
                (trusted / "ignored-b").write_text("b", encoding="utf-8")
                base_sha = commit_test_repository(
                    repository, "tracked excluded discovery surface"
                )

                head_path = "config/adoption.yaml"
                write_yaml(repository / head_path, workflow_policy_adoption())
                write_caller_workflow(
                    repository / ".github/workflows/assurance.yml",
                    head_path,
                    "b" * 40,
                )
                head_sha = commit_test_repository(
                    repository, "add caller and declaration"
                )
                completed, runner_temp = run_workflow_materializer(
                    root,
                    repository,
                    base_sha,
                    head_sha,
                    head_path,
                    script_replacements=(replacement,),
                )
                output = completed.stdout + completed.stderr
                self.assertNotEqual(completed.returncode, 0, output)
                self.assertIn(expected, output)
                self.assertNotIn("Traceback", output)
                self.assertFalse((runner_temp / "base-adoption.yaml").exists())

    def test_workflow_fallback_fails_closed_at_scan_byte_budget(self):
        root = self.make_tmp()
        repository = root / "repo"
        init_git_test_repository(repository)

        # One Git object plus tracked symlink aliases creates >64 MiB of
        # lexical scan work without bloating the test repository itself.
        (repository / "blob.bin").write_bytes(b"x" * (1024 * 1024))
        aliases = repository / "aliases"
        aliases.mkdir()
        for index in range(64):
            (aliases / f"alias-{index:02d}").symlink_to("../blob.bin")
        base_sha = commit_test_repository(repository, "large discovery surface")

        head_path = "config/adoption.yaml"
        write_yaml(repository / head_path, workflow_policy_adoption())
        write_caller_workflow(
            repository / ".github/workflows/assurance.yml", head_path, "b" * 40
        )
        head_sha = commit_test_repository(repository, "add caller and adoption")

        completed, runner_temp = run_workflow_materializer(
            root, repository, base_sha, head_sha, head_path
        )
        output = completed.stdout + completed.stderr
        self.assertNotEqual(completed.returncode, 0, output)
        self.assertIn("64 MiB byte budget", output)
        self.assertFalse((runner_temp / "base-adoption.yaml").exists())

    def test_workflow_exact_caller_rejects_non_aap_base_file(self):
        root = self.make_tmp()
        repository = root / "repo"
        init_git_test_repository(repository)

        adoption_path = "config/adoption.yaml"
        non_aap = workflow_policy_adoption()
        non_aap["upstream"]["repository"] = "example/not-aap"
        write_yaml(repository / adoption_path, non_aap)
        write_caller_workflow(
            repository / ".github/workflows/assurance.yml",
            adoption_path,
            "a" * 40,
        )
        base_sha = commit_test_repository(repository, "non-AAP caller input")

        write_yaml(repository / adoption_path, workflow_policy_adoption())
        write_caller_workflow(
            repository / ".github/workflows/assurance.yml",
            adoption_path,
            "b" * 40,
        )
        head_sha = commit_test_repository(repository, "replace with AAP declaration")

        completed, runner_temp = run_workflow_materializer(
            root, repository, base_sha, head_sha, adoption_path
        )
        output = completed.stdout + completed.stderr
        self.assertNotEqual(completed.returncode, 0, output)
        self.assertIn(
            "does not contain a strong canonical AAP declaration",
            output,
        )
        self.assertFalse((runner_temp / "base-adoption.yaml").exists())

    def test_missing_pyyaml_has_an_actionable_error_without_traceback(self):
        completed = subprocess.run(
            [sys.executable, "-S", str(VALIDATOR), "--help"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=30,
        )
        output = completed.stdout + completed.stderr
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("'pyyaml' package is required", output)
        self.assertNotIn("Traceback", output)


class TestLegacyDriftMigrationCompatibility(ValidatorTestCase):
    """Base-only compatibility must permit cleanup without hiding removals."""

    LEGACY_VERSIONS = ("v0.2.1", "v0.3.2", "unreleased")

    def test_mixed_archived_cleanup_to_active_profile_is_neutral(self):
        for version in self.LEGACY_VERSIONS:
            with self.subTest(version=version):
                base = workflow_policy_adoption(
                    stage="DRAFT",
                    profiles=["core", "archived"],
                    version=version,
                )
                head = copy.deepcopy(base)
                head["profiles"] = ["core"]

                code, out = self.run_drift(
                    head,
                    changed=(),
                    base_adoption=base,
                )
                self.assertEqual(code, 0, out)
                self.assertIn("no assurance policy regression", out)
                self.assertNotIn("effective profile(s) removed", out)

    def test_mixed_archived_cleanup_to_archived_reports_active_removal(self):
        for version in self.LEGACY_VERSIONS:
            with self.subTest(version=version):
                base = workflow_policy_adoption(
                    stage="DRAFT",
                    profiles=["core", "archived"],
                    version=version,
                )
                head = copy.deepcopy(base)
                head["profiles"] = ["archived"]

                code, out = self.run_drift(
                    head,
                    changed=(),
                    base_adoption=base,
                )
                self.assertEqual(code, 1, out)
                self.assertIn("assurance policy weakened", out)
                self.assertIn("effective profile(s) removed: core", out)

    def test_duplicate_base_adoption_and_register_cleanups_remain_comparable(self):
        for version in self.LEGACY_VERSIONS:
            with self.subTest(version=version):
                root = self.make_tmp()
                base = workflow_policy_adoption(stage="DRAFT", version=version)
                head = copy.deepcopy(base)

                base_adoption_path = root / "base-adoption.yaml"
                base_raw = json.dumps(base, indent=2).replace(
                    '"adoption_stage": "DRAFT"',
                    '"adoption_stage": "HUMAN_REVIEWED",\n'
                    '  "adoption_stage": "DRAFT"',
                    1,
                )
                base_adoption_path.write_text(base_raw, encoding="utf-8")

                registers = baseline_registers()
                base_root = root / "base-root"
                head_root = root / "head-root"
                base_invariants = json.dumps(registers["invariants"], indent=2)
                base_invariants = base_invariants.replace(
                    '"status": "UNKNOWN"',
                    '"status": "VERIFIED",\n'
                    '      "status": "UNKNOWN"',
                    1,
                )
                base_invariant_path = base_root / REGISTER_FILES["invariants"]
                base_invariant_path.parent.mkdir(parents=True, exist_ok=True)
                base_invariant_path.write_text(base_invariants, encoding="utf-8")
                write_yaml(
                    base_root / REGISTER_FILES["residuals"],
                    registers["residuals"],
                )

                head_adoption_path = (
                    head_root / ".agentic-assurance" / "adoption.yaml"
                )
                write_yaml(head_adoption_path, head)
                for kind, document in registers.items():
                    write_yaml(head_root / REGISTER_FILES[kind], document)

                changed = root / "changed.txt"
                changed.write_bytes(b"")
                code, out = run_validator(
                    [
                        "drift",
                        "--adoption",
                        str(head_adoption_path),
                        "--changed-files",
                        str(changed),
                        "--pr-body",
                        str(root / "missing-body.txt"),
                        "--base-adoption",
                        str(base_adoption_path),
                        "--base-registers-root",
                        str(base_root),
                        "--project-root",
                        str(head_root),
                    ]
                )
                self.assertEqual(code, 0, out)
                self.assertIn(
                    "base adoption file: accepted pre-v0.4 duplicate-key YAML",
                    out,
                )
                self.assertIn(
                    "base register (assurance/INVARIANTS.yaml): accepted "
                    "pre-v0.4 duplicate-key YAML",
                    out,
                )
                self.assertIn("no assurance policy regression", out)
                self.assertNotIn("ERROR:", out)

    def test_earlier_pre_v04_starter_completion_and_reid_are_exempt(self):
        for version in ("v0.2.1", "unreleased"):
            with self.subTest(version=version):
                base = workflow_policy_adoption(stage="DRAFT", version=version)
                head = copy.deepcopy(base)
                head["upstream"]["version"] = "v0.4.0"
                starter = copy.deepcopy(
                    PRE_V04_REGISTER_STARTER_ENTRIES["claims"]
                )
                completed = copy.deepcopy(starter)
                completed.update(
                    {
                        "id": "CLAIM-API-001",
                        "text": "The API rejects unauthorized requests",
                        "scope": "API v1",
                        "proof_tier": "NOT_CLAIMED",
                        "owner": "Alice Example",
                    }
                )
                base_registers = {
                    "claims": {"version": 1, "claims": [starter]},
                }
                head_registers = {
                    "claims": {"version": 1, "claims": [completed]},
                }

                code, out = self.run_drift(
                    head,
                    changed=(),
                    body="Assurance policy change: upgrade to v0.4.0\n",
                    base_adoption=base,
                    base_registers=base_registers,
                    head_registers=head_registers,
                )
                self.assertEqual(code, 0, out)
                self.assertNotIn("CLAIM-EXAMPLE-001 deleted", out)
                self.assertNotIn("ERROR:", out)


class TestAdopterTrustBoundaries(ValidatorTestCase):
    def test_declared_repository_paths_reject_absolute_in_project_values(self):
        cases = ("paths.system", "specification_workflow.root", "human_review.record", "security.policy")
        for field in cases:
            with self.subTest(field=field):
                root = self.make_tmp()
                adoption, registers = conformant_fixture()
                if field == "paths.system":
                    adoption.setdefault("paths", {})["system"] = str(
                        root / "assurance" / "SYSTEM.md"
                    )
                elif field == "specification_workflow.root":
                    adoption["specification_workflow"]["root"] = str(
                        root / "AGENTIC_ASSURANCE.md"
                    )
                elif field == "human_review.record":
                    adoption["human_review"]["record"] = str(
                        root / "docs" / "reviews" / "review.md"
                    )
                else:
                    policy = root / "SECURITY.md"
                    policy.write_text("# Security\n", encoding="utf-8")
                    adoption["security"] = {"policy": str(policy)}
                adoption_path = build_split_project(root, adoption, registers)

                code, out = self.run_adopter(root, adoption_path)
                self.assertEqual(code, 1, out)
                self.assertIn("repository-relative", out)
                self.assertNotIn("Traceback", out)

    def test_security_paths_reject_traversal_and_symlink_escape(self):
        for key, value in (
            ("policy", "../../outside-policy"),
            ("public_assurance_root", "nested/../../../outside-root"),
        ):
            with self.subTest(key=key):
                adoption = baseline_adoption()
                adoption["security"] = {key: value}
                code, out = self.run_split(adoption, baseline_registers())
                self.assertEqual(code, 1, out)
                self.assertIn(f"security.{key}", out)
                self.assertIn("repository-relative", out)

        root = self.make_tmp()
        outside = self.make_tmp() / "SECURITY.md"
        outside.write_text("# Outside\n", encoding="utf-8")
        (root / "SECURITY.md").symlink_to(outside)
        adoption = baseline_adoption()
        adoption["security"] = {"policy": "SECURITY.md"}
        adoption_path = build_split_project(
            root, adoption, baseline_registers()
        )
        code, out = self.run_adopter(root, adoption_path)
        self.assertEqual(code, 1, out)
        self.assertIn("security.policy", out)
        self.assertIn("resolves outside the project root", out)

    def test_repository_root_is_valid_for_declared_directory_roots(self):
        root = self.make_tmp()
        adoption = baseline_adoption()
        adoption["specification_workflow"]["root"] = "."
        adoption["security"] = {"public_assurance_root": "."}
        adoption_path = build_split_project(
            root, adoption, baseline_registers()
        )

        code, out = self.run_adopter(root, adoption_path)
        self.assertEqual(code, 0, out)
        self.assertNotIn("ERROR:", out)

    def test_draft_review_record_rejects_escape_and_trusted_target(self):
        for target_kind in ("outside", "git"):
            with self.subTest(target_kind=target_kind):
                root = self.make_tmp()
                adoption = baseline_adoption()
                adoption["human_review"] = {"record": "docs/review.md"}
                adoption_path = build_split_project(
                    root, baseline_adoption(), baseline_registers()
                )
                write_yaml(adoption_path, adoption)
                link = root / "docs" / "review.md"
                link.parent.mkdir(parents=True, exist_ok=True)
                if target_kind == "outside":
                    target = self.make_tmp() / "review.md"
                    target.write_text("# Outside review\n", encoding="utf-8")
                else:
                    target = root / ".git" / "review.md"
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text("# Untrusted review\n", encoding="utf-8")
                link.symlink_to(target)

                code, out = self.run_adopter(root, adoption_path)
                self.assertEqual(code, 1, out)
                self.assertIn("human_review.record", out)
                expected = (
                    "resolves outside the project root"
                    if target_kind == "outside"
                    else "trusted/non-adopter data"
                )
                self.assertIn(expected, out)

    def test_inline_lite_checks_every_explicit_path_but_not_split_defaults(self):
        root = self.make_tmp()
        adoption = baseline_lite_adoption()
        adoption["paths"] = {"invariants": "nested/../../outside.yaml"}
        adoption_path = build_lite_project(
            root, adoption, baseline_lite_assurance()
        )
        code, out = self.run_adopter(root, adoption_path)
        self.assertEqual(code, 1, out)
        self.assertIn("paths.invariants", out)
        self.assertIn("repository-relative", out)

        root = self.make_tmp()
        adoption = baseline_lite_adoption()
        adoption["paths"] = {"invariants": "policy/INVARIANTS.yaml"}
        adoption_path = build_lite_project(
            root, adoption, baseline_lite_assurance()
        )
        outside = self.make_tmp() / "INVARIANTS.yaml"
        outside.write_text("not active lite policy\n", encoding="utf-8")
        (root / "policy").mkdir()
        (root / "policy" / "INVARIANTS.yaml").symlink_to(outside)
        code, out = self.run_adopter(root, adoption_path)
        self.assertEqual(code, 1, out)
        self.assertIn("paths.invariants", out)
        self.assertIn("resolves outside the project root", out)

        root = self.make_tmp()
        adoption_path = build_lite_project(
            root, baseline_lite_adoption(), baseline_lite_assurance()
        )
        outside_dir = self.make_tmp() / "unrelated-assurance"
        outside_dir.mkdir()
        (root / "assurance").symlink_to(outside_dir, target_is_directory=True)
        code, out = self.run_adopter(root, adoption_path)
        self.assertEqual(code, 0, out)
        self.assertNotIn("ERROR:", out)

    def test_omitted_profile_checkout_still_excludes_inferred_checkout(self):
        root = self.make_tmp()
        checkout = root / ".assurance-profile-pin"
        (checkout / "schemas").mkdir(parents=True)
        (checkout / "VERSION").write_text("v0.2.0\n", encoding="utf-8")
        target = checkout / "templates" / "adoption.yaml"
        write_yaml(target, baseline_adoption())
        adoption_path = build_split_project(
            root, baseline_adoption(), baseline_registers()
        )
        adoption_path.unlink()
        adoption_path.symlink_to(target)

        code, out = run_validator(
            [
                "adopter",
                "--adoption",
                str(adoption_path),
                "--project-root",
                str(root),
                "--schemas",
                str(checkout / "schemas"),
            ]
        )
        self.assertEqual(code, 1, out)
        self.assertIn("trusted/non-adopter data", out)

    def test_inferred_checkout_always_participates_in_version_comparison(self):
        root = self.make_tmp()
        checkout = self.make_tmp() / "pinned-profile"
        shutil.copytree(SCHEMAS_DIR, checkout / "schemas")
        (checkout / "VERSION").write_text("v0.3.0\n", encoding="utf-8")
        adoption_path = build_split_project(
            root, baseline_adoption(), baseline_registers()
        )

        code, out = run_validator(
            [
                "adopter",
                "--adoption",
                str(adoption_path),
                "--project-root",
                str(root),
                "--schemas",
                str(checkout / "schemas"),
            ]
        )
        self.assertEqual(code, 1, out)
        self.assertIn("version/commit mismatch", out)

    def test_adoption_symlink_into_profile_checkout_is_rejected(self):
        root = self.make_tmp()
        checkout = root / ".assurance-profile-pin"
        target = checkout / "templates" / "adoption.yaml"
        write_yaml(target, baseline_adoption())
        shutil.copytree(SCHEMAS_DIR, checkout / "schemas")
        (checkout / "VERSION").write_text("v0.2.0\n", encoding="utf-8")
        adoption_path = build_split_project(
            root, baseline_adoption(), baseline_registers()
        )
        adoption_path.unlink()
        adoption_path.symlink_to(target)

        code, out = self.run_adopter(
            root,
            adoption_path,
            "--profile-checkout",
            str(checkout),
            "--schemas",
            str(checkout / "schemas"),
        )
        self.assertEqual(code, 1, out)
        self.assertIn("trusted/non-adopter data", out)

    def test_lite_symlink_outside_project_is_rejected(self):
        root = self.make_tmp()
        outside = self.make_tmp() / "outside-assurance.yaml"
        write_yaml(outside, baseline_lite_assurance())
        adoption_path = build_lite_project(
            root, baseline_lite_adoption(), baseline_lite_assurance()
        )
        assurance_path = root / ".agentic-assurance" / "assurance.yaml"
        assurance_path.unlink()
        assurance_path.symlink_to(outside)

        code, out = self.run_adopter(root, adoption_path)
        self.assertEqual(code, 1, out)
        self.assertIn("resolves outside the project root", out)

    def test_reviewed_lite_reuses_only_the_safely_loaded_document(self):
        root = self.make_tmp()
        outside = self.make_tmp() / "outside-assurance.yaml"
        secret = "EXTERNAL_PLACEHOLDER_SECRET_MUST_NOT_BE_READ"
        assurance = baseline_lite_assurance()
        assurance["system"] = f"REPLACE_WITH_{secret}"
        write_yaml(outside, assurance)
        adoption = baseline_lite_adoption()
        adoption["adoption_stage"] = "HUMAN_REVIEWED"
        adoption["human_review"] = human_review_block()
        adoption_path = build_lite_project(
            root, adoption, baseline_lite_assurance()
        )
        assurance_path = root / LITE_ASSURANCE_PATH
        assurance_path.unlink()
        assurance_path.symlink_to(outside)

        code, out = self.run_adopter(root, adoption_path)
        self.assertEqual(code, 1, out)
        self.assertIn("resolves outside the project root", out)
        self.assertNotIn(secret, out)

    def test_case_alias_of_trusted_checkout_is_rejected_when_applicable(self):
        root = self.make_tmp()
        checkout = root / ".assurance-profile-pin"
        target = checkout / "templates" / "SYSTEM.md"
        target.parent.mkdir(parents=True)
        target.write_text("# Trusted template\n", encoding="utf-8")
        shutil.copytree(SCHEMAS_DIR, checkout / "schemas")
        (checkout / "VERSION").write_text("v0.2.0\n", encoding="utf-8")
        alias_root = root / ".ASSURANCE-PROFILE-PIN"
        try:
            same_location = alias_root.samefile(checkout)
        except OSError:
            same_location = False
        if not same_location:
            self.skipTest("filesystem is case-sensitive")

        adoption = baseline_adoption()
        adoption["paths"] = {
            "system": ".ASSURANCE-PROFILE-PIN/templates/SYSTEM.md"
        }
        adoption_path = build_split_project(
            root, adoption, baseline_registers()
        )
        write_yaml(adoption_path, adoption)
        code, out = self.run_adopter(
            root,
            adoption_path,
            "--profile-checkout",
            str(checkout),
            "--schemas",
            str(checkout / "schemas"),
        )
        self.assertEqual(code, 1, out)
        self.assertIn("trusted/non-adopter data", out)

    def test_lite_symlink_into_profile_checkout_is_rejected(self):
        root = self.make_tmp()
        checkout = root / ".assurance-profile-pin"
        target = checkout / "templates" / "assurance.yaml"
        write_yaml(target, baseline_lite_assurance())
        shutil.copytree(SCHEMAS_DIR, checkout / "schemas")
        (checkout / "VERSION").write_text("v0.2.0\n", encoding="utf-8")
        adoption_path = build_lite_project(
            root, baseline_lite_adoption(), baseline_lite_assurance()
        )
        assurance_path = root / ".agentic-assurance" / "assurance.yaml"
        assurance_path.unlink()
        assurance_path.symlink_to(target)

        code, out = self.run_adopter(
            root,
            adoption_path,
            "--profile-checkout",
            str(checkout),
            "--schemas",
            str(checkout / "schemas"),
        )
        self.assertEqual(code, 1, out)
        self.assertIn("trusted/non-adopter data", out)

    def test_broken_lite_symlink_fails_closed(self):
        root = self.make_tmp()
        adoption_path = build_lite_project(
            root, baseline_lite_adoption(), baseline_lite_assurance()
        )
        assurance_path = root / ".agentic-assurance" / "assurance.yaml"
        assurance_path.unlink()
        assurance_path.symlink_to("missing-assurance.yaml")

        code, out = self.run_adopter(root, adoption_path)
        self.assertEqual(code, 1, out)
        self.assertIn("exists but is not a readable regular file", out)

    def test_lite_symlink_loop_fails_without_traceback(self):
        root = self.make_tmp()
        adoption_path = build_lite_project(
            root, baseline_lite_adoption(), baseline_lite_assurance()
        )
        assurance_path = root / ".agentic-assurance" / "assurance.yaml"
        assurance_path.unlink()
        assurance_path.symlink_to("assurance.yaml")

        code, out = self.run_adopter(root, adoption_path)
        self.assertEqual(code, 1, out)
        self.assertTrue(
            "cannot resolve path" in out
            or "exists but is not a readable regular file" in out,
            out,
        )
        self.assertNotIn("Traceback", out)

    def test_in_project_lite_symlink_remains_valid(self):
        root = self.make_tmp()
        adoption_path = build_lite_project(
            root, baseline_lite_adoption(), baseline_lite_assurance()
        )
        assurance_path = root / ".agentic-assurance" / "assurance.yaml"
        target = root / "project-data" / "assurance.yaml"
        target.parent.mkdir(parents=True)
        assurance_path.replace(target)
        assurance_path.symlink_to(Path("..") / "project-data" / "assurance.yaml")

        code, out = self.run_adopter(root, adoption_path)
        self.assertEqual(code, 0, out)

    def test_root_instruction_symlink_into_profile_checkout_is_rejected(self):
        root = self.make_tmp()
        checkout = root / ".assurance-profile-pin"
        target = checkout / "templates" / "AGENTS.md"
        target.parent.mkdir(parents=True)
        target.write_text(
            "Read AGENTIC_ASSURANCE.md and .agentic-assurance/adoption.yaml\n",
            encoding="utf-8",
        )
        shutil.copytree(SCHEMAS_DIR, checkout / "schemas")
        (checkout / "VERSION").write_text("v0.2.0\n", encoding="utf-8")
        adoption_path = build_split_project(
            root, baseline_adoption(), baseline_registers()
        )
        agents = root / "AGENTS.md"
        agents.unlink()
        agents.symlink_to(target)

        code, out = self.run_adopter(
            root,
            adoption_path,
            "--profile-checkout",
            str(checkout),
            "--schemas",
            str(checkout / "schemas"),
        )
        self.assertEqual(code, 1, out)
        self.assertIn("trusted/non-adopter data", out)

    def test_custom_adoption_path_is_the_required_reading_order_reference(self):
        for stale_default, expected_code in ((False, 0), (True, 1)):
            with self.subTest(stale_default=stale_default):
                root = self.make_tmp()
                default_path = build_split_project(
                    root, baseline_adoption(), baseline_registers()
                )
                custom_path = root / "config" / "adoption.yaml"
                custom_path.parent.mkdir(parents=True)
                default_path.replace(custom_path)
                reference = (
                    ".agentic-assurance/adoption.yaml"
                    if stale_default
                    else "config/adoption.yaml"
                )
                (root / "AGENTIC_ASSURANCE.md").write_text(
                    "# Assurance\n\n" + reading_order_block(reference),
                    encoding="utf-8",
                )
                (root / "AGENTS.md").write_text(
                    "# Agents\n\n" + reading_order_block(reference),
                    encoding="utf-8",
                )

                code, out = self.run_adopter(root, custom_path)
                self.assertEqual(code, expected_code, out)
                if stale_default:
                    self.assertIn("then config/adoption.yaml", out)
                else:
                    self.assertIn("with assurance reading order", out)

    def test_in_project_adoption_symlink_keeps_lexical_reading_order_path(self):
        root = self.make_tmp()
        adoption_path = build_split_project(
            root, baseline_adoption(), baseline_registers()
        )
        target = root / "config" / "adoption.yaml"
        target.parent.mkdir(parents=True)
        adoption_path.replace(target)
        adoption_path.symlink_to(Path("..") / "config" / "adoption.yaml")

        code, out = self.run_adopter(root, adoption_path)
        self.assertEqual(code, 0, out)
        self.assertIn("with assurance reading order", out)

    def test_drift_rejects_register_symlink_into_workflow_checkout(self):
        root = self.make_tmp()
        base = baseline_adoption()
        head = copy.deepcopy(base)
        base_root = root / "base-root"
        head_root = root / "head-root"
        write_yaml(
            base_root / REGISTER_FILES["invariants"],
            baseline_registers()["invariants"],
        )
        target = head_root / ".assurance-profile-pin" / "templates" / "INVARIANTS.yaml"
        write_yaml(target, baseline_registers()["invariants"])
        link = head_root / REGISTER_FILES["invariants"]
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(
            Path("..")
            / ".assurance-profile-pin"
            / "templates"
            / "INVARIANTS.yaml"
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
        self.assertIn("trusted/non-adopter data", out)


class TestArchivedAndOperationalStageHardening(ValidatorTestCase):
    def archived_reviewed_fixture(self, stage="HUMAN_REVIEWED"):
        adoption = baseline_adoption()
        adoption["profiles"] = ["archived"]
        adoption["adoption_stage"] = stage
        review = human_review_block()
        if stage == "CONFORMANT":
            review["approvals"] = [
                {
                    "approver": "bob-reviewer",
                    "review_url": "https://example.invalid/reviews/1",
                    "at": "2026-01-02",
                }
            ]
        adoption["human_review"] = review
        return adoption

    def test_archived_conformant_preserves_honest_historical_registers(self):
        adoption, registers = conformant_fixture()
        adoption["profiles"] = ["archived"]
        registers["claims"]["claims"][0]["status"] = "CONTRADICTED"
        invariant = registers["invariants"]["invariants"][0]
        invariant["status"] = "CONTRADICTED"
        invariant["intent"]["classification"] = "UNKNOWN"
        invariant["intent"]["authority"] = None
        residual = registers["residuals"]["residuals"][0]
        residual["status"] = "OPEN"
        residual["review_after"] = PAST_DATE
        registers["defeaters"]["defeaters"][0]["review_after"] = PAST_DATE

        code, out = self.run_split(adoption, registers)
        self.assertEqual(code, 0, out)
        self.assertIn("stage CONFORMANT: requirements satisfied", out)
        self.assertNotIn("is CONTRADICTED", out)
        self.assertNotIn("review_after date", out)

    def test_archived_retained_verified_invariant_stays_historical(self):
        adoption, registers = conformant_fixture()
        adoption["profiles"] = ["archived"]
        invariant = registers["invariants"]["invariants"][0]
        invariant["status"] = "VERIFIED"
        invariant["severity"] = "critical"
        invariant["enforcement"] = []
        invariant["verification"] = []

        code, out = self.run_split(adoption, registers)
        self.assertEqual(code, 0, out)
        self.assertIn("stage CONFORMANT: requirements satisfied", out)
        self.assertNotIn("VERIFIED with severity critical", out)

    def test_archived_retained_acceptance_cannot_be_future_dated(self):
        adoption, registers = conformant_fixture()
        adoption["profiles"] = ["archived"]
        registers["residuals"]["residuals"][0]["accepted_at"] = "2999-01-01"

        code, out = self.run_split(adoption, registers)
        self.assertEqual(code, 1, out)
        self.assertIn("accepted_at 2999-01-01 is in the future", out)
        self.assertNotIn("requirements satisfied", out)

    def test_archived_retained_completed_dispositions_reject_placeholders(self):
        cases = ("accepted residual", "resolved residual", "closed defeater")
        for case in cases:
            with self.subTest(case=case):
                adoption, registers = conformant_fixture()
                adoption["profiles"] = ["archived"]
                residual = registers["residuals"]["residuals"][0]
                defeater = registers["defeaters"]["defeaters"][0]
                if case == "accepted residual":
                    residual["accepted_by"] = "REPLACE_WITH_ACCEPTING_HUMAN"
                    expected = "accepted_by is empty, missing, or an unfilled placeholder"
                elif case == "resolved residual":
                    residual["status"] = "RESOLVED"
                    residual["resolution_note"] = "REPLACE_WITH_RESOLUTION_GROUNDS"
                    expected = "resolution_note is empty, missing, or an unfilled placeholder"
                else:
                    defeater["status"] = "MITIGATED"
                    defeater["resolution"] = "REPLACE_WITH_RESOLUTION_GROUNDS"
                    expected = "resolution is empty, missing, or an unfilled placeholder"

                code, out = self.run_split(adoption, registers)
                self.assertEqual(code, 1, out)
                self.assertIn(expected, out)
                self.assertNotIn("requirements satisfied", out)

    def test_archived_reviewed_rejects_empty_system(self):
        root = self.make_tmp()
        adoption = self.archived_reviewed_fixture()
        adoption_path = build_split_project(root, adoption, {})
        (root / "assurance" / "SYSTEM.md").write_text(" \n", encoding="utf-8")

        code, out = self.run_adopter(root, adoption_path)
        self.assertEqual(code, 1, out)
        self.assertIn("empty or whitespace-only", out)
        self.assertNotIn("requirements satisfied", out)

    def test_archived_reviewed_rejects_shipped_system_markers(self):
        root = self.make_tmp()
        adoption = self.archived_reviewed_fixture()
        adoption_path = build_split_project(root, adoption, {})
        (root / "assurance" / "SYSTEM.md").write_text(
            "REPLACE_WITH_ARCHIVED_HISTORICAL_PURPOSE\n",
            encoding="utf-8",
        )

        code, out = self.run_adopter(root, adoption_path)
        self.assertEqual(code, 1, out)
        self.assertIn("REPLACE_WITH_ARCHIVED_HISTORICAL_PURPOSE", out)
        self.assertNotIn("requirements satisfied", out)

    def test_active_conformant_rejects_accidental_critical_invariant(self):
        adoption, registers = conformant_fixture()
        registers["invariants"]["invariants"][0]["intent"][
            "classification"
        ] = "ACCIDENTAL"

        code, out = self.run_split(adoption, registers)
        self.assertEqual(code, 1, out)
        self.assertIn("intent is ACCIDENTAL", out)

    def test_noncritical_contradiction_warns_but_keeps_conformant_verdict(self):
        adoption, registers = conformant_fixture()
        low = baseline_invariant()
        low["id"] = "INV-CORE-002"
        low["status"] = "CONTRADICTED"
        registers["invariants"]["invariants"].append(low)

        code, out = self.run_split(adoption, registers)
        self.assertEqual(code, 0, out)
        self.assertIn("WARN:", out)
        self.assertIn("INV-CORE-002 is CONTRADICTED", out)
        self.assertIn("stage CONFORMANT: requirements satisfied", out)

    def test_human_reviewed_critical_invariant_records_intent_even_if_unknown(self):
        adoption, registers = conformant_fixture()
        adoption["adoption_stage"] = "HUMAN_REVIEWED"
        adoption["human_review"].pop("approvals")
        registers["invariants"]["invariants"][0].pop("intent")

        code, out = self.run_split(adoption, registers)
        self.assertEqual(code, 1, out)
        self.assertIn("has no recorded intent.classification", out)

        registers["invariants"]["invariants"][0]["intent"] = {
            "classification": "UNKNOWN",
            "authority": None,
        }
        code, out = self.run_split(adoption, registers)
        self.assertEqual(code, 0, out)

    def test_affirmative_intent_classifications_require_human_authority(self):
        for classification in ("INTENDED", "COMPATIBILITY", "DEPRECATED"):
            with self.subTest(classification=classification):
                adoption, registers = conformant_fixture()
                adoption.pop("adoption_stage")
                adoption.pop("human_review")
                registers["invariants"]["invariants"][0]["intent"] = {
                    "classification": classification,
                    "authority": "REPLACE_WITH_INTENT_AUTHORITY",
                }
                code, out = self.run_split(adoption, registers)
                self.assertEqual(code, 1, out)
                self.assertIn(
                    f"intent.classification {classification}", out
                )
                self.assertIn("intent.authority is empty or null", out)

    def test_active_adoption_requires_material_change_workflow(self):
        adoption = baseline_adoption()
        del adoption["specification_workflow"]

        code, out = self.run_split(adoption, baseline_registers())
        self.assertEqual(code, 1, out)
        self.assertIn("specification_workflow", out)

    def test_archived_declared_workflow_must_resolve_to_real_project_content(self):
        adoption = self.archived_reviewed_fixture("CONFORMANT")
        adoption["specification_workflow"] = {
            "system": "existing",
            "root": "../../outside-does-not-exist",
        }

        code, out = self.run_split(adoption, {})
        self.assertEqual(code, 1, out)
        self.assertIn("specification_workflow.root", out)
        self.assertIn("repository-relative path", out)
        self.assertNotIn("requirements satisfied", out)

    def test_archived_valid_workflow_does_not_reactivate_component_checks(self):
        adoption = self.archived_reviewed_fixture("CONFORMANT")
        adoption["specification_workflow"] = {
            "system": "existing",
            "root": "AGENTIC_ASSURANCE.md",
        }
        adoption["components"] = {
            "historical": {
                "paths": ["src/**"],
                "invariants": ["INV-HISTORICAL-001"],
            }
        }

        code, out = self.run_split(adoption, {})
        self.assertEqual(code, 0, out)
        self.assertIn("requirements satisfied", out)
        self.assertNotIn("does not exist in the invariant register", out)

    def test_service_threat_model_must_be_nonempty(self):
        root = self.make_tmp()
        adoption = baseline_adoption()
        adoption["profiles"] = ["service"]
        adoption_path = build_split_project(root, adoption, baseline_registers())
        threat_model = root / "assurance" / "THREAT_MODEL.md"
        threat_model.parent.mkdir(parents=True, exist_ok=True)
        threat_model.write_text("", encoding="utf-8")

        code, out = self.run_adopter(root, adoption_path)
        self.assertEqual(code, 1, out)
        self.assertIn("THREAT_MODEL.md: file is empty", out)

    def test_reviewed_service_rejects_untouched_threat_model_template(self):
        root = self.make_tmp()
        adoption, registers = conformant_fixture()
        adoption["profiles"] = ["service"]
        adoption_path = build_split_project(root, adoption, registers)
        shutil.copy2(
            REPO_ROOT / "templates" / "THREAT_MODEL.md",
            root / "assurance" / "THREAT_MODEL.md",
        )

        code, out = self.run_adopter(root, adoption_path)
        self.assertEqual(code, 1, out)
        self.assertIn("unfilled placeholder", out)
        self.assertIn("threat model", out)
        self.assertNotIn("requirements satisfied", out)

    def test_reviewed_active_prose_rejects_any_generic_marker_suffix(self):
        for marker in ("REPLACE_WITH_description", "REPLACE_WITH_"):
            with self.subTest(artifact="split system", marker=marker):
                root = self.make_tmp()
                adoption, registers = conformant_fixture()
                adoption_path = build_split_project(root, adoption, registers)
                (root / "assurance" / "SYSTEM.md").write_text(
                    f"# System\n{marker}\n", encoding="utf-8"
                )
                code, out = self.run_adopter(root, adoption_path)
                self.assertEqual(code, 1, out)
                self.assertIn("unfilled placeholder 'REPLACE_WITH_'", out)
                self.assertIn("mapped system artifact", out)

            with self.subTest(artifact="service threat model", marker=marker):
                root = self.make_tmp()
                adoption, registers = conformant_fixture()
                adoption["profiles"] = ["service"]
                adoption_path = build_split_project(root, adoption, registers)
                (root / "assurance" / "THREAT_MODEL.md").write_text(
                    f"# Threat model\n{marker}\n", encoding="utf-8"
                )
                code, out = self.run_adopter(root, adoption_path)
                self.assertEqual(code, 1, out)
                self.assertIn("unfilled placeholder 'REPLACE_WITH_'", out)
                self.assertIn("threat model", out)

            with self.subTest(artifact="lite system", marker=marker):
                adoption = baseline_lite_adoption()
                adoption["adoption_stage"] = "HUMAN_REVIEWED"
                adoption["human_review"] = human_review_block()
                assurance = baseline_lite_assurance()
                assurance["system"] = f"# System\n{marker}"
                code, out = self.run_lite(adoption, assurance)
                self.assertEqual(code, 1, out)
                self.assertIn(marker, out)
                self.assertIn(LITE_ASSURANCE_PATH, out)

    def test_workflow_root_must_exist_and_be_adopter_owned(self):
        adoption = baseline_adoption()
        adoption["specification_workflow"]["root"] = "docs/missing-workflow"
        code, out = self.run_split(adoption, baseline_registers())
        self.assertEqual(code, 1, out)
        self.assertIn("does not exist", out)

        root = self.make_tmp()
        (root / "docs" / "empty-workflow").mkdir(parents=True)
        adoption = baseline_adoption()
        adoption["specification_workflow"]["root"] = "docs/empty-workflow"
        adoption_path = build_split_project(root, adoption, baseline_registers())
        code, out = self.run_adopter(root, adoption_path)
        self.assertEqual(code, 1, out)
        self.assertIn("contains no readable, non-empty UTF-8", out)

        root = self.make_tmp()
        (root / "docs" / "empty-workflow" / "empty-child").mkdir(parents=True)
        adoption = baseline_adoption()
        adoption["specification_workflow"]["root"] = "docs/empty-workflow"
        adoption_path = build_split_project(root, adoption, baseline_registers())
        code, out = self.run_adopter(root, adoption_path)
        self.assertEqual(code, 1, out)
        self.assertIn("contains no readable, non-empty UTF-8", out)

        root = self.make_tmp()
        nested_entry = root / ".specify" / "memory" / "constitution.md"
        nested_entry.parent.mkdir(parents=True)
        nested_entry.write_text("# Material change workflow\n", encoding="utf-8")
        adoption = baseline_adoption()
        adoption["specification_workflow"]["root"] = ".specify"
        adoption_path = build_split_project(root, adoption, baseline_registers())
        code, out = self.run_adopter(root, adoption_path)
        self.assertEqual(code, 0, out)
        self.assertIn("resolves to an adopter-owned path", out)

        root = self.make_tmp()
        entry = root / "docs" / "workflow.md"
        entry.parent.mkdir(parents=True)
        entry.write_bytes(b"x" * (1024 * 1024 + 1))
        adoption = baseline_adoption()
        adoption["specification_workflow"]["root"] = "docs/workflow.md"
        adoption_path = build_split_project(root, adoption, baseline_registers())
        code, out = self.run_adopter(root, adoption_path)
        self.assertEqual(code, 1, out)
        self.assertIn("1,048,576-byte entry-document limit", out)

        root = self.make_tmp()
        checkout = root / "workflow-root" / "vendor" / "profile"
        checkout.mkdir(parents=True)
        shutil.copytree(SCHEMAS_DIR, checkout / "schemas")
        (checkout / "VERSION").write_text("v0.2.0\n", encoding="utf-8")
        (checkout / "README.md").write_text(
            "# Trusted profile content\n", encoding="utf-8"
        )
        adoption = baseline_adoption()
        adoption["specification_workflow"]["root"] = "workflow-root"
        adoption_path = build_split_project(root, adoption, baseline_registers())
        code, out = self.run_adopter(
            root,
            adoption_path,
            "--profile-checkout",
            str(checkout),
            "--schemas",
            str(checkout / "schemas"),
        )
        self.assertEqual(code, 1, out)
        self.assertIn("contains no readable, non-empty UTF-8", out)

        root = self.make_tmp()
        checkout = root / ".assurance-profile-pin"
        (checkout / "workflow.md").parent.mkdir(parents=True)
        (checkout / "workflow.md").write_text("# Workflow\n", encoding="utf-8")
        shutil.copytree(SCHEMAS_DIR, checkout / "schemas")
        (checkout / "VERSION").write_text("v0.2.0\n", encoding="utf-8")
        adoption = baseline_adoption()
        adoption["specification_workflow"]["root"] = ".assurance-profile-pin/workflow.md"
        adoption_path = build_split_project(root, adoption, baseline_registers())
        code, out = self.run_adopter(
            root,
            adoption_path,
            "--profile-checkout",
            str(checkout),
            "--schemas",
            str(checkout / "schemas"),
        )
        self.assertEqual(code, 1, out)
        self.assertIn("trusted/non-adopter data", out)

        root = self.make_tmp()
        (root / ".git").mkdir()
        adoption = baseline_adoption()
        adoption["specification_workflow"]["root"] = ".git"
        adoption_path = build_split_project(root, adoption, baseline_registers())
        code, out = self.run_adopter(root, adoption_path)
        self.assertEqual(code, 1, out)
        self.assertIn("trusted/non-adopter data", out)

    def test_root_guides_must_be_nonempty_and_expose_reading_order(self):
        for content, expected in (
            ("", "empty or whitespace-only"),
            ("# Agents\n", "required visible top-level"),
        ):
            with self.subTest(content=content):
                root = self.make_tmp()
                adoption_path = build_split_project(
                    root, baseline_adoption(), baseline_registers()
                )
                (root / "AGENTS.md").write_text(content, encoding="utf-8")
                code, out = self.run_adopter(root, adoption_path)
                self.assertEqual(code, 1, out)
                self.assertIn(expected, out)

        root = self.make_tmp()
        adoption_path = build_split_project(
            root, baseline_adoption(), baseline_registers()
        )
        (root / "AGENTS.md").write_bytes(
            reading_order_block().encode("utf-8")
            + b"x" * (5 * 1024 * 1024)
        )
        code, out = self.run_adopter(root, adoption_path)
        self.assertEqual(code, 1, out)
        self.assertIn("project-text limit", out)

    def test_root_reading_order_rejects_mentions_reversal_and_hidden_blocks(self):
        canonical = reading_order_block()
        invalid_contents = {
            "unordered mention": (
                "# Agents\n\nDo not read AGENTIC_ASSURANCE.md or "
                ".agentic-assurance/adoption.yaml.\n"
            ),
            "reversed": (
                "# Agents\n\nBefore any material change, read:\n\n"
                "1. `.agentic-assurance/adoption.yaml`;\n"
                "2. `AGENTIC_ASSURANCE.md`;\n"
            ),
            "fenced example": "# Agents\n\n```markdown\n" + canonical + "```\n",
            "script": "# Agents\n\n<script>\n" + canonical + "</script>\n",
            "hidden html": "# Agents\n\n<div hidden>\n" + canonical + "</div>\n",
            "styled html": (
                '# Agents\n\n<div style="display:none">\n'
                + canonical
                + "</div>\n"
            ),
        }
        for label, content in invalid_contents.items():
            with self.subTest(label=label):
                root = self.make_tmp()
                adoption_path = build_split_project(
                    root, baseline_adoption(), baseline_registers()
                )
                (root / "AGENTS.md").write_text(content, encoding="utf-8")
                code, out = self.run_adopter(root, adoption_path)
                self.assertEqual(code, 1, out)
                self.assertIn("required visible top-level", out)

    def test_review_record_must_exist_be_nonempty_and_stay_in_project(self):
        for mutation, expected in (
            ("missing", "does not exist"),
            ("empty", "empty or whitespace-only"),
            ("outside", "must be a non-root repository-relative path"),
        ):
            with self.subTest(mutation=mutation):
                root = self.make_tmp()
                adoption, registers = conformant_fixture()
                if mutation == "outside":
                    outside = self.make_tmp() / "review.md"
                    outside.write_text("# Review\n", encoding="utf-8")
                    adoption["human_review"]["record"] = str(outside)
                adoption_path = build_split_project(root, adoption, registers)
                if mutation == "missing":
                    (root / human_review_block()["record"]).unlink()
                elif mutation == "empty":
                    (root / human_review_block()["record"]).write_text("", encoding="utf-8")
                code, out = self.run_adopter(root, adoption_path)
                self.assertEqual(code, 1, out)
                self.assertIn(expected, out)
                self.assertNotIn("requirements satisfied", out)

    def test_conformant_approval_requires_http_url_and_real_iso_time(self):
        mutations = (
            ("review_url", "reviews/1", "absolute HTTP(S) URL"),
            ("at", "YYYY-MM-DD", "ISO 8601 date or timestamp"),
            ("at", "2026-01-02T03:04:05", "ISO 8601 date or timestamp"),
        )
        for field, value, expected in mutations:
            with self.subTest(field=field):
                adoption, registers = conformant_fixture()
                adoption["human_review"]["approvals"][0][field] = value
                code, out = self.run_split(adoption, registers)
                self.assertEqual(code, 1, out)
                self.assertIn(expected, out)
                self.assertNotIn("requirements satisfied", out)

    def test_conformant_approval_accepts_rfc3339_timestamp(self):
        adoption, registers = conformant_fixture()
        adoption["human_review"]["approvals"][0]["at"] = "2026-01-02T03:04:05Z"
        code, out = self.run_split(adoption, registers)
        self.assertEqual(code, 0, out)
        self.assertIn("stage CONFORMANT: requirements satisfied", out)

    def test_conformant_approval_accepts_rfc3339_leap_second(self):
        adoption, registers = conformant_fixture()
        adoption["human_review"]["date"] = "2016-12-31"
        adoption["human_review"]["approvals"][0]["at"] = (
            "2016-12-31T23:59:60Z"
        )
        code, out = self.run_split(adoption, registers)
        self.assertEqual(code, 0, out)
        self.assertIn("stage CONFORMANT: requirements satisfied", out)

        adoption["human_review"]["approvals"][0]["at"] = (
            "2017-01-01T00:59:60+01:00"
        )
        code, out = self.run_split(adoption, registers)
        self.assertEqual(code, 0, out)
        self.assertIn("stage CONFORMANT: requirements satisfied", out)

    def test_arbitrary_second_60_is_not_an_rfc3339_leap_second(self):
        for timestamp in (
            "2026-01-01T12:34:60Z",
            "2016-12-30T23:59:60Z",
            "2016-12-31T23:58:60Z",
        ):
            with self.subTest(timestamp=timestamp):
                adoption, registers = conformant_fixture()
                adoption["human_review"]["approvals"][0]["at"] = timestamp
                code, out = self.run_split(adoption, registers)
                self.assertEqual(code, 1, out)
                self.assertIn("must be a valid ISO 8601 date", out)
                self.assertNotIn("requirements satisfied", out)

    def test_completed_human_actions_cannot_be_future_dated(self):
        mutations = (
            ("review", "2999-01-01", "human_review.date is in the future"),
            ("approval-date", "2999-01-01", "approvals[0].at is in the future"),
            (
                "approval-time",
                "2999-01-01T00:00:00Z",
                "approvals[0].at is in the future",
            ),
            (
                "approval-time-extreme",
                "9999-12-31T23:59:59-14:00",
                "approvals[0].at is in the future",
            ),
            ("acceptance", "2999-01-01", "accepted_at 2999-01-01 is in the future"),
        )
        for field, value, expected in mutations:
            with self.subTest(field=field):
                adoption, registers = conformant_fixture()
                if field == "review":
                    adoption["human_review"]["date"] = value
                elif field.startswith("approval"):
                    adoption["human_review"]["approvals"][0]["at"] = value
                else:
                    registers["residuals"]["residuals"][0]["accepted_at"] = value
                code, out = self.run_split(adoption, registers)
                self.assertEqual(code, 1, out)
                self.assertIn(expected, out)
                self.assertNotIn("requirements satisfied", out)

    def test_future_human_acts_fail_at_draft_and_with_stage_ignored(self):
        for stage, extra in (("DRAFT", ()), ("CONFORMANT", ("--ignore-stage",))):
            with self.subTest(stage=stage):
                adoption, registers = conformant_fixture()
                adoption["adoption_stage"] = stage
                adoption["human_review"]["date"] = "2999-01-01"
                adoption["human_review"]["approvals"][0]["at"] = "2999-01-01"
                code, out = self.run_split(adoption, registers, *extra)
                self.assertEqual(code, 1, out)
                self.assertIn("human_review.date is in the future", out)
                self.assertIn("approvals[0].at is in the future", out)

    def test_conformant_needs_an_approval_backing_the_recorded_review(self):
        for approval_at in (
            "2020-01-01",
            "2020-01-01T23:59:59-05:00",
            "0001-01-01T00:00:00+14:00",
        ):
            with self.subTest(approval_at=approval_at):
                adoption, registers = conformant_fixture()
                adoption["human_review"]["date"] = "2026-01-01"
                adoption["human_review"]["approvals"][0]["at"] = approval_at
                code, out = self.run_split(adoption, registers)
                self.assertEqual(code, 1, out)
                self.assertIn("on or after human_review.date", out)

        adoption, registers = conformant_fixture()
        adoption["human_review"]["date"] = "2026-01-01"
        old = copy.deepcopy(adoption["human_review"]["approvals"][0])
        old["at"] = "2020-01-01"
        adoption["human_review"]["approvals"].insert(0, old)
        code, out = self.run_split(adoption, registers)
        self.assertEqual(code, 0, out)

    def test_scoped_approval_needs_conformance_coverage_for_stage_gate(self):
        adoption, registers = conformant_fixture()
        approval = adoption["human_review"]["approvals"][0]
        approval["covers"] = ["INV-CORE-001"]
        code, out = self.run_split(adoption, registers)
        self.assertEqual(code, 1, out)
        self.assertIn("CONFORMANCE coverage token", out)

        approval["covers"].append("CONFORMANCE")
        code, out = self.run_split(adoption, registers)
        self.assertEqual(code, 0, out)

    def test_date_only_human_actions_allow_the_utc_plus_14_civil_date(self):
        latest_civil_date = (
            datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(hours=14)
        ).date().isoformat()
        adoption, registers = conformant_fixture()
        adoption["human_review"]["date"] = latest_civil_date
        adoption["human_review"]["approvals"][0]["at"] = latest_civil_date
        registers["residuals"]["residuals"][0]["accepted_at"] = latest_civil_date

        code, out = self.run_split(adoption, registers)
        self.assertEqual(code, 0, out)

    def test_review_schedule_uses_one_host_independent_civil_date(self):
        # Under the old host-local default this exact date was not yet passed
        # in Pago Pago but was passed in Kiritimati. The validator now uses one
        # UTC+14-derived civil boundary for both runs.
        review_date = datetime.datetime.now(
            ZoneInfo("Pacific/Pago_Pago")
        ).date()
        for timezone in ("Pacific/Pago_Pago", "Pacific/Kiritimati"):
            with self.subTest(surface="adopter", timezone=timezone):
                adoption, registers = conformant_fixture()
                registers["residuals"]["residuals"][0]["review_after"] = (
                    review_date.isoformat()
                )
                code, out = self.run_split(
                    adoption,
                    registers,
                    env=clean_env({"TZ": timezone}),
                )
                self.assertEqual(code, 1, out)
                self.assertIn(
                    f"review_after {review_date.isoformat()} has passed", out
                )

            with self.subTest(surface="drift", timezone=timezone):
                base = baseline_adoption()
                head = copy.deepcopy(base)
                base_registers = drift_register_fixture()
                base_registers["residuals"]["residuals"][0][
                    "review_after"
                ] = review_date.isoformat()
                head_registers = copy.deepcopy(base_registers)
                postponed = review_date + datetime.timedelta(days=30)
                head_registers["residuals"]["residuals"][0][
                    "review_after"
                ] = postponed.isoformat()
                code, out = self.run_drift(
                    head,
                    changed=(),
                    base_adoption=base,
                    base_registers=base_registers,
                    head_registers=head_registers,
                    env=clean_env({"TZ": timezone}),
                )
                self.assertEqual(code, 1, out)
                self.assertIn("review_after postponed", out)

    def test_project_identity_fields_must_be_nonblank(self):
        for field in ("name", "repository", "human_owner"):
            with self.subTest(field=field):
                adoption = baseline_adoption()
                adoption["project"][field] = "   "
                code, out = self.run_split(adoption, baseline_registers())
                self.assertEqual(code, 1, out)
                self.assertIn(f"$.project.{field}", out)


class TestDriftAuditHardening(ValidatorTestCase):
    def test_adoption_alias_retarget_is_a_policy_regression(self):
        adoption = baseline_adoption()
        alias = ".agentic-assurance/adoption.yaml"
        code, out = self.run_drift(
            adoption,
            changed=(),
            base_adoption=copy.deepcopy(adoption),
            adoption_paths=(alias, alias, "config/v1.yaml", "config/v2.yaml"),
        )
        self.assertEqual(code, 1, out)
        self.assertIn("adoption declaration symlink target changed", out)
        self.assertIn("config/v1.yaml", out)
        self.assertIn("config/v2.yaml", out)

    def test_unchanged_policy_path_cannot_silently_retarget_symlink(self):
        root = self.make_tmp()
        base_root = root / "base"
        head_root = root / "head"
        for tree, target_name in (
            (base_root, "system-v1.md"),
            (head_root, "system-v2.md"),
        ):
            target = tree / "policy" / target_name
            target.parent.mkdir(parents=True)
            target.write_text(f"# {target_name}\n", encoding="utf-8")
            alias = tree / "assurance" / "SYSTEM.md"
            alias.parent.mkdir(parents=True)
            alias.symlink_to(Path("..") / "policy" / target_name)

        adoption = baseline_adoption()
        adoption["profiles"] = ["archived"]
        write_yaml(root / "adoption.yaml", adoption)
        write_yaml(root / "base-adoption.yaml", adoption)
        (root / "changed.txt").write_bytes(b"")
        (root / "body.txt").write_text("", encoding="utf-8")
        code, out = run_validator(
            [
                "drift",
                "--adoption",
                str(root / "adoption.yaml"),
                "--changed-files",
                str(root / "changed.txt"),
                "--pr-body",
                str(root / "body.txt"),
                "--base-adoption",
                str(root / "base-adoption.yaml"),
                "--base-registers-root",
                str(base_root),
                "--project-root",
                str(head_root),
            ]
        )
        self.assertEqual(code, 1, out)
        self.assertIn("paths.system resolved target changed", out)
        self.assertIn("system-v1.md", out)
        self.assertIn("system-v2.md", out)

    def test_nonportable_base_symlink_is_uncomparable_even_with_ack(self):
        root = self.make_tmp()
        base_root = root / "base"
        head_root = root / "head"
        base_target = base_root / "policy" / "system.md"
        base_target.parent.mkdir(parents=True)
        base_target.write_text("# Historical system\n", encoding="utf-8")
        base_link = base_root / "assurance" / "SYSTEM.md"
        base_link.parent.mkdir(parents=True)
        base_link.symlink_to(base_target)
        head_system = head_root / "assurance" / "SYSTEM.md"
        head_system.parent.mkdir(parents=True)
        head_system.write_text("# Historical system\n", encoding="utf-8")

        adoption = baseline_adoption()
        adoption["profiles"] = ["archived"]
        write_yaml(root / "adoption.yaml", adoption)
        write_yaml(root / "base-adoption.yaml", adoption)
        (root / "changed.txt").write_bytes(b"")
        (root / "body.txt").write_text(
            "Assurance policy change: reviewed path handling\n",
            encoding="utf-8",
        )
        code, out = run_validator(
            [
                "drift",
                "--adoption",
                str(root / "adoption.yaml"),
                "--changed-files",
                str(root / "changed.txt"),
                "--pr-body",
                str(root / "body.txt"),
                "--base-adoption",
                str(root / "base-adoption.yaml"),
                "--base-registers-root",
                str(base_root),
                "--project-root",
                str(head_root),
            ]
        )
        self.assertEqual(code, 1, out)
        self.assertIn("baseline cannot be compared", out)
        self.assertIn("<non-portable-symlink>", out)

    def test_effective_core_inheritance_avoids_false_regressions(self):
        transitions = (
            (["core"], ["service"]),
            (["core", "service"], ["service"]),
        )
        for before, after in transitions:
            with self.subTest(before=before, after=after):
                base = baseline_adoption()
                head = copy.deepcopy(base)
                base["profiles"] = before
                head["profiles"] = after
                code, out = self.run_drift(
                    head, changed=(), base_adoption=base
                )
                self.assertEqual(code, 0, out)
                self.assertIn("no assurance policy regression", out)

    def test_removing_specialized_effective_profile_still_fails(self):
        base = baseline_adoption()
        head = copy.deepcopy(base)
        base["profiles"] = ["service"]
        head["profiles"] = ["core"]

        code, out = self.run_drift(head, changed=(), base_adoption=base)
        self.assertEqual(code, 1, out)
        self.assertIn("effective profile(s) removed: service", out)

    def test_archived_to_active_reclassification_is_explicit_but_not_a_weakening(self):
        base = baseline_adoption()
        head = copy.deepcopy(base)
        base["profiles"] = ["archived"]
        head["profiles"] = ["core"]

        code, out = self.run_drift(head, changed=(), base_adoption=base)
        self.assertEqual(code, 1, out)
        self.assertIn("assurance profile mode changed", out)
        self.assertNotIn("effective profile(s) removed: archived", out)

        code, out = self.run_drift(
            head,
            changed=(),
            body="Assurance policy change: resume active maintenance\n",
            base_adoption=base,
        )
        self.assertEqual(code, 0, out)
        self.assertIn("acknowledged", out)

    def test_active_to_archived_still_removes_active_obligations(self):
        base = baseline_adoption()
        head = copy.deepcopy(base)
        head["profiles"] = ["archived"]

        code, out = self.run_drift(head, changed=(), base_adoption=base)
        self.assertEqual(code, 1, out)
        self.assertIn("effective profile(s) removed: core", out)

    def test_malformed_head_and_base_stages_fail_closed(self):
        malformed = ("HUMAN_REVIEWD", None, ["HUMAN_REVIEWED"], {"stage": "DRAFT"})
        for value in malformed:
            with self.subTest(side="head", value=value):
                base = baseline_adoption()
                head = copy.deepcopy(base)
                head["adoption_stage"] = value
                code, out = self.run_drift(head, changed=(), base_adoption=base)
                self.assertEqual(code, 1, out)
                self.assertIn("head adoption_stage", out)
                self.assertIn("cannot be trusted", out)
                self.assertNotIn("no assurance policy regression", out)
            with self.subTest(side="base", value=value):
                base = baseline_adoption()
                head = copy.deepcopy(base)
                base["adoption_stage"] = value
                code, out = self.run_drift(head, changed=(), base_adoption=base)
                self.assertEqual(code, 1, out)
                self.assertIn("base adoption_stage", out)
                self.assertIn("cannot be trusted", out)
                self.assertNotIn("no assurance policy regression", out)

    def test_template_owner_completion_is_not_a_weakening(self):
        base = baseline_adoption()
        head = copy.deepcopy(base)
        base["project"]["human_owner"] = "REPLACE_WITH_OWNER"
        registers = drift_register_fixture()
        for document in registers.values():
            for entries in document.values():
                if isinstance(entries, list):
                    for entry in entries:
                        if isinstance(entry, dict) and "owner" in entry:
                            entry["owner"] = "REPLACE_WITH_OWNER"
        head_registers = copy.deepcopy(registers)
        for document in head_registers.values():
            for entries in document.values():
                if isinstance(entries, list):
                    for entry in entries:
                        if isinstance(entry, dict) and "owner" in entry:
                            entry["owner"] = "Alice Example"

        code, out = self.run_drift(
            head,
            changed=(),
            base_adoption=base,
            base_registers=registers,
            head_registers=head_registers,
        )
        self.assertEqual(code, 0, out)
        self.assertIn("no assurance policy regression", out)
        self.assertNotIn("owner changed", out)

    def test_v03_shipped_starter_entry_completion_is_not_a_weakening(self):
        base = baseline_adoption()
        head = copy.deepcopy(base)
        base["upstream"]["version"] = "v0.3.2"
        head["upstream"]["version"] = "v0.4.0"
        base_registers = drift_register_fixture()
        base_registers["defeaters"] = drift_defeaters_document()
        for kind in ("claims", "invariants", "defeaters", "residuals"):
            base_registers[kind][kind][0] = copy.deepcopy(
                PRE_V04_REGISTER_STARTER_ENTRIES[kind]
            )
        head_registers = copy.deepcopy(base_registers)
        head_registers["claims"]["claims"][0].update(
            {
                "id": "CLAIM-API-001",
                "text": "The API rejects unauthorized requests",
                "scope": "API",
                "proof_tier": "NOT_CLAIMED",
                "owner": "Alice Example",
            }
        )
        head_registers["invariants"]["invariants"][0].update(
            {
                "id": "INV-API-001",
                "title": "API authorization",
                "statement": "Unauthorized requests are denied",
                "scope": "API",
                "owner": "Alice Example",
                "severity": "high",
            }
        )
        head_registers["defeaters"]["defeaters"][0].update(
            {
                "id": "DEF-API-001",
                "statement": "A stale cache may bypass the guard",
                "owner": "Alice Example",
                "status": "RESOLVED",
                "review_after": FUTURE_DATE,
            }
        )
        head_registers["residuals"]["residuals"][0].update(
            {
                "id": "RES-API-001",
                "summary": "A bounded cache window remains",
                "impact": "low",
                "uncertainty": "low",
                "owner": "Alice Example",
                "status": "ACCEPTED",
                "review_after": FUTURE_DATE,
            }
        )

        code, out = self.run_drift(
            head,
            changed=(),
            body="Assurance policy change: upgrade to v0.4.0\n",
            base_adoption=base,
            base_registers=base_registers,
            head_registers=head_registers,
        )
        self.assertEqual(code, 0, out)
        self.assertNotIn("EXAMPLE-001 deleted", out)
        self.assertNotIn("severity downgraded", out)
        self.assertNotIn("ERROR:", out)

    def test_unrelated_extension_marker_cannot_exempt_completed_example_entry(self):
        base = baseline_adoption()
        head = copy.deepcopy(base)
        base["upstream"]["version"] = "v0.3.2"
        head["upstream"]["version"] = "v0.3.2"
        base_registers = drift_register_fixture()
        claim = base_registers["claims"]["claims"][0]
        claim["id"] = "CLAIM-EXAMPLE-001"
        claim["extensions"] = {"note": "REPLACE_WITH_LATER"}
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
        self.assertIn("claims entry CLAIM-EXAMPLE-001 deleted", out)

    def test_v04_base_does_not_retain_v03_starter_exemption(self):
        base = baseline_adoption()
        head = copy.deepcopy(base)
        base["upstream"]["version"] = "v0.4.0"
        head["upstream"]["version"] = "v0.4.0"
        base_registers = drift_register_fixture()
        claim = base_registers["claims"]["claims"][0]
        claim.update(
            {
                "id": "CLAIM-EXAMPLE-001",
                "text": LEGACY_REGISTER_FIELD_PLACEHOLDERS["claims"]["text"],
            }
        )
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
        self.assertIn("claims entry CLAIM-EXAMPLE-001 deleted", out)

    def test_real_owner_replaced_by_template_marker_still_fails(self):
        base = baseline_adoption()
        head = copy.deepcopy(base)
        head["project"]["human_owner"] = "REPLACE_WITH_OWNER"

        code, out = self.run_drift(head, changed=(), base_adoption=base)
        self.assertEqual(code, 1, out)
        self.assertIn("project.human_owner changed", out)

    def test_invalid_profiles_do_not_drive_derived_success_or_warnings(self):
        adoption = baseline_adoption()
        adoption["profiles"] = ["archived", "not-a-profile"]
        code, out = self.run_split(adoption, baseline_registers())
        self.assertEqual(code, 1, out)
        self.assertNotIn("profile 'archived' is declared exclusively", out)
        self.assertNotIn("profile 'archived': PROFILE.md", out)


# ---------------------------------------------------------------------------
# 11. GitHub Actions annotations
# ---------------------------------------------------------------------------


class TestGithubAnnotations(ValidatorTestCase):
    def test_workflow_plain_diagnostics_neutralize_leading_command_paths(self):
        command_path = "::warning file=README.md,line=1::FORGED.yaml"
        root = self.make_tmp()
        repository = root / "repo"
        init_git_test_repository(repository)
        trusted_scripts = repository / ".assurance-profile-pin" / "scripts"
        trusted_scripts.mkdir(parents=True)
        shutil.copy2(VALIDATOR, trusted_scripts / "validate.py")
        (repository / command_path).write_text("[unterminated", encoding="utf-8")
        output_path = root / "github-output"
        completed = subprocess.run(
            ["bash", "-c", workflow_step_shell("Read and verify upstream pin")],
            cwd=repository,
            env=clean_env(
                {
                    "ADOPTION_FILE": command_path,
                    "WORKFLOW_SHA": "a" * 40,
                    "GITHUB_OUTPUT": str(output_path),
                }
            ),
            capture_output=True,
            text=True,
            timeout=10,
        )
        pin_output = completed.stdout + completed.stderr
        self.assertNotEqual(completed.returncode, 0, pin_output)
        self.assertFalse(
            any(line.startswith("::warning file=") for line in pin_output.splitlines()),
            pin_output,
        )
        self.assertIn("adoption file ::warning", pin_output)

        base_sha = commit_test_repository(repository, "command-path base")
        (repository / command_path).write_text("[still-unterminated", encoding="utf-8")
        head_sha = commit_test_repository(repository, "command-path head")
        completed, _runner_temp = run_workflow_materializer(
            root, repository, base_sha, head_sha, command_path
        )
        materializer_output = completed.stdout + completed.stderr
        self.assertNotEqual(completed.returncode, 0, materializer_output)
        self.assertFalse(
            any(
                line.startswith("::warning file=")
                for line in materializer_output.splitlines()
            ),
            materializer_output,
        )
        self.assertIn("HEAD adoption file ::warning", materializer_output)

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

    def test_untrusted_component_text_cannot_inject_actions_or_summary_markup(self):
        component_name = "api\n::add-mask::PWNED\n| fake | <b> `"
        adoption = baseline_adoption()
        adoption["components"] = {
            component_name: {
                "paths": ["src/api/**"],
                "invariants": ["INV-CORE-001"],
            }
        }
        root = self.make_tmp()
        summary_path = root / "summary.md"
        env = clean_env(
            {
                "GITHUB_ACTIONS": "true",
                "GITHUB_STEP_SUMMARY": str(summary_path),
            }
        )
        code, out = self.run_drift(
            adoption,
            changed=["src/api/handler.py"],
            env=env,
        )
        self.assertEqual(code, 0, out)
        self.assertNotIn("\n::add-mask::PWNED", out)
        self.assertIn("\\n::add-mask::PWNED\\n", out)

        summary = summary_path.read_text(encoding="utf-8")
        self.assertNotIn("\n| fake |", summary)
        self.assertNotIn("<b>", summary)
        self.assertIn("&#124; fake &#124; &#60;b&#62; &#96;", summary)
        self.assertIn(
            "<br>&#58;&#58;add&#45;mask&#58;&#58;PWNED<br>", summary
        )

    def test_plain_output_escapes_controls_and_unpaired_surrogates(self):
        for component_name, escaped in (
            ("api\nFAKE: forged", "api\\nFAKE: forged"),
            ("api\udcff", "api\\udcff"),
        ):
            with self.subTest(component_name=repr(component_name)):
                adoption = baseline_adoption()
                adoption["components"] = {
                    component_name: {
                        "paths": ["src/api/**"],
                        "invariants": ["INV-CORE-001"],
                    }
                }
                code, out = self.run_drift(
                    adoption,
                    changed=["src/api/handler.py"],
                )
                self.assertEqual(code, 0, out)
                self.assertIn(escaped, out)
                self.assertNotIn("\nFAKE: forged", out)
                self.assertNotIn("Traceback", out)

    def test_plain_and_annotation_output_survive_ascii_stdout(self):
        adoption = baseline_adoption()
        adoption["components"] = {
            "한글": {
                "paths": ["src/api/**"],
                "invariants": ["INV-CORE-001"],
            }
        }
        env = clean_env(
            {
                "PYTHONIOENCODING": "ascii",
                "GITHUB_ACTIONS": "true",
            }
        )
        code, out = self.run_drift(
            adoption,
            changed=["src/api/handler.py"],
            env=env,
        )
        self.assertEqual(code, 0, out)
        self.assertIn("\\ud55c\\uae00", out)
        self.assertNotIn("UnicodeEncodeError", out)
        self.assertNotIn("Traceback", out)


class TestFinalSecurityRegressionCoverage(ValidatorTestCase):
    """Adversarial cases found during the final independent PR audit."""

    def run_raw_drift_adoption(self, raw_yaml, *, timeout=120):
        root = self.make_tmp()
        adoption_path = root / "adoption.yaml"
        adoption_path.write_text(raw_yaml, encoding="utf-8")
        (root / "changed.txt").write_bytes(b"")
        (root / "body.txt").write_text("", encoding="utf-8")
        return run_validator(
            [
                "drift",
                "--adoption",
                str(adoption_path),
                "--changed-files",
                str(root / "changed.txt"),
                "--pr-body",
                str(root / "body.txt"),
            ],
            timeout=timeout,
        )

    @staticmethod
    def hidden_markdown_variants(payload):
        quoted = "\n".join(f"> {line}" for line in payload.splitlines())
        indented = "\n".join(f"    {line}" for line in payload.splitlines())
        return {
            "html-comment": f"<!--\n{payload}\n-->\n",
            "backtick-fence": f"```text\n{payload}\n```\n",
            "tilde-fence": f"~~~text\n{payload}\n~~~\n",
            "raw-pre": f"<pre>\n{payload}\n</pre>\n",
            "raw-script": f"<script>\n{payload}\n</script>\n",
            "hidden-div": f"<div hidden>\n{payload}\n</div>\n",
            "styled-div": (
                f'<div style="display:none">\n{payload}\n</div>\n'
            ),
            "indented-code": f"{indented}\n",
            "blockquote-fence": f"> ```text\n{quoted}\n> ```\n",
        }

    @staticmethod
    def shipped_claim_starter():
        return copy.deepcopy(PRE_V04_REGISTER_STARTER_ENTRIES["claims"])

    def test_benign_yaml_alias_is_accepted(self):
        code, out = self.run_raw_drift_adoption(
            """\
profiles: [core]
shared: &shared
  note: benign shared metadata
first: *shared
second: *shared
"""
        )
        self.assertEqual(code, 0, out)
        self.assertIn("no component map", out)
        self.assertNotIn("YAML aliases expand beyond", out)

    def test_invalid_policy_without_components_has_no_routing_success(self):
        code, out = self.run_raw_drift_adoption(
            "profiles: [core]\nadoption_stage: NOT_A_STAGE\n"
        )
        self.assertEqual(code, 1, out)
        self.assertIn("adoption_stage", out)
        self.assertNotIn("OK: no component map", out)

    def test_yaml_alias_dag_over_budget_fails_quickly_and_cleanly(self):
        lines = ["profiles: [core]", "seed: &a0 [leaf]"]
        for level in range(1, 11):
            aliases = ", ".join([f"*a{level - 1}"] * 5)
            lines.append(f"level{level}: &a{level} [{aliases}]")
        lines.append("payload: *a10")

        code, out = self.run_raw_drift_adoption("\n".join(lines) + "\n", timeout=10)
        self.assertEqual(code, 1, out)
        self.assertIn("YAML aliases expand beyond", out)
        self.assertIn("node policy limit", out)
        self.assertNotIn("Traceback", out)

    def test_yaml_merge_key_is_rejected_before_alias_expansion(self):
        code, out = self.run_raw_drift_adoption(
            """\
profiles: [core]
defaults: &defaults
  note: shared
merged:
  <<: *defaults
""",
            timeout=10,
        )
        self.assertEqual(code, 1, out)
        self.assertIn("YAML merge keys", out)
        self.assertNotIn("Traceback", out)

    def test_legacy_base_yaml_merge_key_is_rejected_before_flattening(self):
        root = self.make_tmp()
        head = baseline_adoption()
        write_yaml(root / "head.yaml", head)
        (root / "changed.txt").write_bytes(b"")
        (root / "body.txt").write_text("", encoding="utf-8")
        (root / "base.yaml").write_text(
            """\
upstream:
  repository: example/assurance-profile
  version: v0.3.2
  commit: 0000000000000000000000000000000000000000
project:
  name: Example Project
  repository: example/project
  human_owner: Alice Example
profiles: [core]
specification_workflow:
  system: minimal
  root: AGENTIC_ASSURANCE.md
defaults: &defaults
  note: shared
merged:
  <<: *defaults
""",
            encoding="utf-8",
        )
        code, out = run_validator(
            [
                "drift",
                "--adoption",
                str(root / "head.yaml"),
                "--changed-files",
                str(root / "changed.txt"),
                "--pr-body",
                str(root / "body.txt"),
                "--base-adoption",
                str(root / "base.yaml"),
            ],
            timeout=10,
        )
        self.assertEqual(code, 1, out)
        self.assertIn("YAML merge keys", out)
        self.assertNotIn("Traceback", out)

    def test_non_json_yaml_tags_and_nonfinite_numbers_fail_closed(self):
        payloads = {
            "omap-cycle": """\
profiles: [core]
evil: !!omap
  - loop: &loop [*loop]
""",
            "binary": """\
profiles: [core]
evil: !!binary SGVsbG8=
""",
            "set": """\
profiles: [core]
evil: !!set {item: null}
""",
            "nan": """\
profiles: [core]
evil: .nan
""",
        }
        for label, raw_yaml in payloads.items():
            with self.subTest(yaml_type=label):
                code, out = self.run_raw_drift_adoption(raw_yaml, timeout=10)
                self.assertEqual(code, 1, out)
                self.assertIn("cannot process", out)
                self.assertNotIn("Traceback", out)

    def test_malformed_or_hostless_approval_url_is_a_controlled_failure(self):
        for review_url in (
            "http://[",
            "http://]",
            "http://[::1",
            "https://user@",
            "https://:80",
            "https://example.invalid:",
            "https://example.invalid:99999/review",
            "https://example.invalid/<bad>",
            "https://example.invalid/a\\b",
            "https://example.invalid/{bad}",
            "https://example.invalid/review/%FF",
            "https://example.invalid/review/%C3",
            "https://example.invalid/café",
            "https://example.invalid/a\u200db",
            "https://example.invalid/\ud800",
            "https://K.com/review",
            "https://ı.com/review",
        ):
            with self.subTest(review_url=review_url):
                adoption, registers = conformant_fixture()
                adoption["human_review"]["approvals"][0]["review_url"] = review_url

                code, out = self.run_split(adoption, registers)
                self.assertEqual(code, 1, out)
                self.assertIn("human_review.approvals", out)
                self.assertIn("review_url", out)
                self.assertNotIn("Traceback", out)
                self.assertNotIn("ValueError: Invalid IPv6 URL", out)

    def test_approval_url_with_valid_explicit_port_remains_valid(self):
        adoption, registers = conformant_fixture()
        adoption["human_review"]["approvals"][0]["review_url"] = (
            "https://review.example.invalid:8443/pull/1"
        )
        code, out = self.run_split(adoption, registers)
        self.assertEqual(code, 0, out)

        adoption["human_review"]["approvals"][0]["review_url"] = (
            "https://review.example.invalid:8443/pull/%E2%9C%93?view=full#review-1"
        )
        code, out = self.run_split(adoption, registers)
        self.assertEqual(code, 0, out)

    def test_draft_approval_shape_is_validated_without_optional_format_packages(self):
        cases = (
            (
                "at",
                "9999-99-99T99:99:99Z",
                "human_review.approvals[0].at",
            ),
            (
                "review_url",
                "https://review.example.invalid/%ZZ",
                "human_review.approvals[0].review_url",
            ),
            (
                "review_url",
                "https://review.example.invalid:99999/pull/1",
                "human_review.approvals[0].review_url",
            ),
        )
        for field, value, expected in cases:
            with self.subTest(field=field, value=value):
                adoption = baseline_adoption()
                adoption["human_review"] = {
                    "approvals": [
                        {
                            "approver": "Alice Example",
                            "review_url": "https://review.example.invalid/pull/1",
                            "at": "2026-01-01T00:00:00Z",
                        }
                    ]
                }
                adoption["human_review"]["approvals"][0][field] = value
                code, out = self.run_split(adoption, baseline_registers())
                self.assertEqual(code, 1, out)
                self.assertIn(expected, out)
                self.assertNotIn("Traceback", out)

    def test_conformant_approval_rejects_malformed_percent_escape(self):
        adoption, registers = conformant_fixture()
        adoption["human_review"]["approvals"][0]["review_url"] = (
            "https://review.example.invalid/%ZZ"
        )
        code, out = self.run_split(adoption, registers)
        self.assertEqual(code, 1, out)
        self.assertIn("human_review.approvals[0].review_url", out)

    def test_invisible_only_policy_values_cannot_satisfy_meaningful_fields(self):
        invisible = "\u200b"
        mutations = {
            "human owner": lambda adoption, registers: adoption["project"].__setitem__(
                "human_owner", invisible
            ),
            "reviewer": lambda adoption, registers: adoption["human_review"].__setitem__(
                "reviewer", invisible
            ),
            "approver": lambda adoption, registers: adoption["human_review"][
                "approvals"
            ][0].__setitem__("approver", invisible),
            "intent authority": lambda adoption, registers: registers["invariants"][
                "invariants"
            ][0]["intent"].__setitem__("authority", invisible),
            "enforcement": lambda adoption, registers: registers["invariants"][
                "invariants"
            ][0].__setitem__("enforcement", [invisible]),
            "verification": lambda adoption, registers: registers["invariants"][
                "invariants"
            ][0].__setitem__("verification", [invisible]),
            "evidence": lambda adoption, registers: registers["invariants"][
                "invariants"
            ][0].__setitem__("evidence", [invisible]),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                adoption, registers = conformant_fixture()
                mutate(adoption, registers)
                code, out = self.run_split(adoption, registers)
                self.assertEqual(code, 1, out)
                self.assertIn("no visible letter, number, punctuation, or symbol", out)
                self.assertNotIn("requirements satisfied", out)

    def test_invisible_only_required_files_do_not_count_as_content(self):
        for target in ("system", "review", "specification workflow"):
            with self.subTest(target=target):
                root = self.make_tmp()
                adoption, registers = conformant_fixture()
                if target == "specification workflow":
                    adoption["specification_workflow"]["root"] = "spec.md"
                adoption_path = build_split_project(root, adoption, registers)
                path = {
                    "system": root / "assurance" / "SYSTEM.md",
                    "review": root / adoption["human_review"]["record"],
                    "specification workflow": root / "spec.md",
                }[target]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("\u200b", encoding="utf-8")
                code, out = self.run_adopter(root, adoption_path)
                self.assertEqual(code, 1, out)
                self.assertIn("no visible meaningful content", out)
                self.assertNotIn("requirements satisfied", out)

    def test_semantic_list_items_must_not_be_blank_or_invisible(self):
        for field in ("assumptions", "limitations"):
            for value in ("", "   ", "\u200b"):
                with self.subTest(
                    register="invariants", field=field, value=repr(value)
                ):
                    adoption, registers = conformant_fixture()
                    registers["invariants"]["invariants"][0][field] = [value]
                    code, out = self.run_split(adoption, registers)
                    self.assertEqual(code, 1, out)

        for value in ("", "   ", "\u200b"):
            with self.subTest(
                register="residuals", field="mitigation", value=repr(value)
            ):
                adoption, registers = conformant_fixture()
                registers["residuals"]["residuals"][0]["mitigation"] = [value]
                code, out = self.run_split(adoption, registers)
                self.assertEqual(code, 1, out)

    def test_issue_integration_cannot_declare_normative_musts_disabled(self):
        for field, value in (
            ("public_security_issues_allowed", True),
            ("closing_requires_artifact_update", False),
        ):
            with self.subTest(field=field):
                adoption, registers = conformant_fixture()
                adoption["issue_integration"] = {field: value}
                code, out = self.run_split(adoption, registers)
                self.assertEqual(code, 1, out)
                self.assertIn(f"issue_integration.{field}", out)
                self.assertNotIn("requirements satisfied", out)

    def test_unicode_line_separator_cannot_forge_an_added_diff_line(self):
        adoption = drift_adoption()
        forged_context = (
            "diff --git a/assurance/note.md b/assurance/note.md\n"
            "index 1111111..2222222 100644\n"
            "--- a/assurance/note.md\n"
            "+++ b/assurance/note.md\n"
            "@@ -1 +1 @@\n"
            " context\u2028+INV-CORE-001\n"
        )
        code, out = self.run_drift(
            adoption,
            changed=["src/api/handler.py"],
            assurance_diff=forged_context,
            strict=True,
        )
        self.assertEqual(code, 1, out)
        self.assertIn("without an assurance update", out)
        self.assertNotIn("assurance update references INV-CORE-001", out)

    def test_bare_cr_cannot_forge_diff_or_pr_directive_records(self):
        adoption = drift_adoption()
        forged_context = (
            "diff --git a/assurance/note.md b/assurance/note.md\n"
            "index 1111111..2222222 100644\n"
            "--- a/assurance/note.md\n"
            "+++ b/assurance/note.md\n"
            "@@ -1 +1 @@\n"
            " context\r+INV-CORE-001\n"
        )
        code, out = self.run_drift(
            adoption,
            changed=["src/api/handler.py"],
            assurance_diff=forged_context,
            strict=True,
        )
        self.assertEqual(code, 1, out)
        self.assertIn("without an assurance update", out)
        self.assertNotIn("assurance update references INV-CORE-001", out)

        code, out = self.run_drift(
            adoption,
            changed=["src/api/handler.py"],
            body=(
                "Visible introduction\rAssurance impact: none\n"
                "Reason: not a leading directive\n"
            ),
            strict=True,
        )
        self.assertEqual(code, 1, out)
        self.assertIn("without an assurance update", out)

        code, out = self.run_drift(
            adoption,
            changed=["src/api/handler.py"],
            body="Assurance impact: INV-CORE-001\r",
            strict=True,
        )
        self.assertEqual(code, 1, out)
        self.assertIn("without an assurance update", out)
        self.assertNotIn("PR description declares impact on INV-CORE-001", out)

    def test_legacy_changed_file_input_splits_only_on_physical_lf(self):
        unusual_path = "src/api/part\u2028two.py"
        adoption = baseline_adoption()
        adoption["components"] = {
            "api": {
                "paths": [unusual_path],
                "invariants": ["INV-CORE-001"],
            }
        }
        code, out = self.run_drift(
            adoption,
            changed=[unusual_path],
            strict=True,
        )
        self.assertEqual(code, 1, out)
        self.assertIn("component 'api' touched", out)

    def test_unicode_casefold_cannot_forge_ascii_directives_or_html(self):
        bodies = (
            "Aſſurance impact: none\nReason: confusable keyword\n",
            "Assurance ımpact: none\nReason: confusable keyword\n",
            (
                "<ſcript>Visible introduction</ſcript>\n"
                "Assurance impact: none\n"
                "Reason: declaration is not first\n"
            ),
            (
                "<script-x>Visible introduction</script-x></script>\n"
                "Assurance impact: none\n"
                "Reason: declaration is not first\n"
            ),
        )
        for body in bodies:
            with self.subTest(body=body):
                code, out = self.run_drift(
                    drift_adoption(),
                    changed=["src/api/handler.py"],
                    body=body,
                    strict=True,
                )
                self.assertEqual(code, 1, out)
                self.assertIn("without an assurance update", out)

        base = baseline_adoption()
        head = copy.deepcopy(base)
        head["upstream"]["commit"] = "b" * 40
        code, out = self.run_drift(
            head,
            changed=(),
            base_adoption=base,
            body="Aſſurance policy change: confusable acknowledgment\n",
        )
        self.assertEqual(code, 1, out)
        self.assertIn("upstream pin changed", out)

    def test_invalid_backtick_info_string_is_visible_not_a_fence(self):
        body = (
            "``` bad`info\n"
            "Visible introduction\n"
            "```\n"
            "Assurance impact: none\n"
            "Reason: declaration is not first\n"
        )
        code, out = self.run_drift(
            drift_adoption(),
            changed=["src/api/handler.py"],
            body=body,
            strict=True,
        )
        self.assertEqual(code, 1, out)
        self.assertIn("without an assurance update", out)

    def test_vertical_tab_cannot_forge_an_html_closing_tag(self):
        for body in (
            (
                "<script>hidden</script\v>\n"
                "Assurance impact: none\n"
                "Reason: declaration remains inside the script element\n"
            ),
            (
                "<div>hidden</div\v>\n"
                "Assurance impact: none\n"
                "Reason: declaration remains inside the div element\n"
            ),
        ):
            with self.subTest(body=body):
                code, out = self.run_drift(
                    drift_adoption(),
                    changed=["src/api/handler.py"],
                    body=body,
                    strict=True,
                )
                self.assertEqual(code, 1, out)
                self.assertIn("without an assurance update", out)

    def test_visible_prose_inside_raw_html_ends_the_directive_block(self):
        body = (
            "<div>\n"
            "Visible introduction before the declaration.\n"
            "</div>\n"
            "Assurance impact: none\n"
            "Reason: no semantic change\n"
        )
        code, out = self.run_drift(
            drift_adoption(),
            changed=["src/api/handler.py"],
            body=body,
            strict=True,
        )
        self.assertEqual(code, 1, out)
        self.assertIn("without an assurance update", out)

        for visible_element in ("<hr>", '<img alt="architecture diagram">'):
            with self.subTest(visible_element=visible_element):
                code, out = self.run_drift(
                    drift_adoption(),
                    changed=["src/api/handler.py"],
                    body=(
                        f"{visible_element}\n"
                        "Assurance impact: none\n"
                        "Reason: declaration is not first\n"
                    ),
                    strict=True,
                )
                self.assertEqual(code, 1, out)
                self.assertIn("without an assurance update", out)

        for nested_visible in (
            "<div>\n<img alt=\"diagram\" />\n</div>\n",
            "<picture>\n<source srcset=\"x\"><img alt=\"diagram\">\n</picture>\n",
            "<div>\n<a><img alt=\"diagram\"></a>\n</div>\n",
        ):
            with self.subTest(nested_visible=nested_visible):
                code, out = self.run_drift(
                    drift_adoption(),
                    changed=["src/api/handler.py"],
                    body=(
                        nested_visible
                        + "Assurance impact: none\n"
                        "Reason: declaration is not first\n"
                    ),
                    strict=True,
                )
                self.assertEqual(code, 1, out)
                self.assertIn("without an assurance update", out)

        nested = (
            "<details>\n"
            "Assurance impact: none\n"
            "Reason: nested declarations are not top-level\n"
            "</details>\n"
        )
        code, out = self.run_drift(
            drift_adoption(),
            changed=["src/api/handler.py"],
            body=nested,
            strict=True,
        )
        self.assertEqual(code, 1, out)

        empty_wrapper = (
            "<div>\n"
            "   \n"
            "&nbsp;\n"
            "</div>\n"
            "Assurance impact: none\n"
            "Reason: no semantic change\n"
        )
        code, out = self.run_drift(
            drift_adoption(),
            changed=["src/api/handler.py"],
            body=empty_wrapper,
            strict=True,
        )
        self.assertEqual(code, 0, out)
        self.assertIn("declares 'Assurance impact: none'", out)

    def test_unicode_separator_cannot_create_a_leading_pr_directive(self):
        body = (
            "Visible introduction\u2028Assurance impact: none\n"
            "Reason: no semantic change\n"
        )
        code, out = self.run_drift(
            drift_adoption(),
            changed=["src/api/handler.py"],
            body=body,
            strict=True,
        )
        self.assertEqual(code, 1, out)
        self.assertIn("without an assurance update", out)

    def test_reading_order_allows_whitespace_only_blank_lines(self):
        root = self.make_tmp()
        adoption = baseline_adoption()
        adoption_path = build_split_project(
            root, adoption, baseline_registers()
        )
        for name in ("AGENTIC_ASSURANCE.md", "AGENTS.md"):
            path = root / name
            text = path.read_text(encoding="utf-8").replace(
                "Before any material change, read:\n1.",
                "Before any material change, read:\n   \n1.",
            )
            path.write_text(text, encoding="utf-8")
        code, out = self.run_adopter(root, adoption_path)
        self.assertEqual(code, 0, out)

    def test_html_entity_newlines_cannot_inject_reading_order(self):
        root = self.make_tmp()
        adoption = baseline_adoption()
        adoption_path = build_split_project(
            root, adoption, baseline_registers()
        )
        (root / "AGENTS.md").write_text(
            "<div hidden>\n"
            "&#10;Before any material change, read:"
            "&#10;1. `AGENTIC_ASSURANCE.md`;"
            "&#10;2. `.agentic-assurance/adoption.yaml`;\n"
            "</div>\n",
            encoding="utf-8",
        )
        code, out = self.run_adopter(root, adoption_path)
        self.assertEqual(code, 1, out)
        self.assertIn("AGENTS.md", out)
        self.assertIn("required visible top-level assurance reading-order", out)

    def test_self_check_scans_tracked_filename_containing_newline(self):
        root = self.make_tmp()
        copy_self_check_fixture(root)
        forbidden = "v0.1.0" + "-draft"
        unusual = root / "line\nbreak.txt"
        unusual.write_text(forbidden + "\n", encoding="utf-8")
        subprocess.run(
            ["git", "init", "-q", str(root)],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(root), "add", "--", unusual.name],
            check=True,
            capture_output=True,
        )

        code, out = run_validator(["self-check", "--repo-root", str(root)])
        self.assertEqual(code, 1, out)
        self.assertIn(forbidden, out)
        self.assertIn("contains the abolished version string", out)
        self.assertNotIn("Traceback", out)

    def test_self_check_fails_when_forbidden_token_scan_is_incomplete(self):
        root = self.make_tmp()
        copy_self_check_fixture(root)
        unreadable = root / "unreadable.txt"
        unreadable.write_text("ordinary content\n", encoding="utf-8")
        unreadable.chmod(0)
        if os.access(unreadable, os.R_OK):
            unreadable.chmod(0o600)
            self.skipTest(
                "current user can bypass mode bits; unreadable-file fixture "
                "requires an ordinary non-privileged POSIX account"
            )
        try:
            code, out = run_validator(
                ["self-check", "--repo-root", str(root)]
            )
        finally:
            unreadable.chmod(0o600)
        self.assertEqual(code, 1, out)
        self.assertIn("cannot be inspected", out)
        self.assertNotIn("OK: no repository file contains", out)

    def test_self_check_scans_binary_and_symlink_blob_bytes(self):
        forbidden = "v0.1.0" + "-draft"
        for kind in ("binary", "symlink"):
            with self.subTest(kind=kind):
                root = self.make_tmp()
                copy_self_check_fixture(root)
                subprocess.run(["git", "init", "-q", str(root)], check=True)
                if kind == "binary":
                    artifact = root / "binary.dat"
                    artifact.write_bytes(b"\xff" + forbidden.encode("ascii") + b"\x00")
                else:
                    artifact = root / "forbidden-link"
                    artifact.symlink_to(forbidden)
                subprocess.run(
                    ["git", "-C", str(root), "add", "--", artifact.name],
                    check=True,
                )
                code, out = run_validator(["self-check", "--repo-root", str(root)])
                self.assertEqual(code, 1, out)
                self.assertIn("contains the abolished version string", out)
                self.assertNotIn("Traceback", out)

    def test_version_tokens_are_ascii_semver_without_padding_or_rc_zero(self):
        invalid_versions = (
            "v٠.٤.٠",
            "v01.2.3",
            "v1.02.3",
            "v1.2.03",
            "v1.2.3-rc.0",
            "v1.2.3-rc.01",
        )
        for version in invalid_versions:
            with self.subTest(surface="VERSION", version=version):
                root = self.make_tmp()
                copy_self_check_fixture(root)
                (root / "VERSION").write_text(version + "\n", encoding="utf-8")
                code, out = run_validator(["self-check", "--repo-root", str(root)])
                self.assertEqual(code, 1, out)
                self.assertIn("VERSION file", out)

            with self.subTest(surface="adopter", version=version):
                adoption = baseline_adoption()
                adoption["upstream"]["version"] = version
                code, out = self.run_split(adoption, baseline_registers())
                self.assertEqual(code, 1, out)
                self.assertIn("$.upstream.version", out)

    def test_version_file_is_one_exact_token_line(self):
        for content in (
            "  v0.4.0  \n",
            "v0.4.0\n\n",
            "v0.4.0\t\n",
            "v0.4.0\r",
        ):
            with self.subTest(content=repr(content)):
                root = self.make_tmp()
                copy_self_check_fixture(root)
                (root / "VERSION").write_text(content, encoding="utf-8")
                code, out = run_validator(["self-check", "--repo-root", str(root)])
                self.assertEqual(code, 1, out)
                self.assertIn("VERSION file", out)

    def test_workflow_pin_reader_rejects_noncanonical_versions(self):
        root = self.make_tmp()
        repository = root / "repo"
        repository.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
        trusted_scripts = repository / ".assurance-profile-pin" / "scripts"
        trusted_scripts.mkdir(parents=True)
        shutil.copy2(VALIDATOR, trusted_scripts / "validate.py")
        output_path = root / "github-output"
        for version in ("v٠.٤.٠", "v01.2.3", "v1.2.3-rc.0"):
            with self.subTest(version=version):
                adoption = baseline_adoption()
                adoption["upstream"].update(
                    {
                        "repository": "MosslandOpenDevs/agentic-assurance-profile",
                        "version": version,
                        "commit": "a" * 40,
                    }
                )
                write_yaml(repository / "adoption.yaml", adoption)
                output_path.unlink(missing_ok=True)
                completed = subprocess.run(
                    [
                        "bash",
                        "-c",
                        workflow_step_shell("Read and verify upstream pin"),
                    ],
                    cwd=repository,
                    env=clean_env(
                        {
                            "ADOPTION_FILE": "adoption.yaml",
                            "WORKFLOW_SHA": "a" * 40,
                            "GITHUB_OUTPUT": str(output_path),
                        }
                    ),
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                output = completed.stdout + completed.stderr
                self.assertNotEqual(completed.returncode, 0, output)
                self.assertIn("upstream.version must be", output)
                self.assertFalse(output_path.exists(), output)

    @unittest.skipUnless(
        sys.platform.startswith("linux"),
        "raw non-UTF-8 filename fixture is exercised on the Linux CI filesystem",
    )
    def test_self_check_handles_tracked_non_utf8_filename(self):
        root = self.make_tmp()
        copy_self_check_fixture(root)
        forbidden = "v0.1.0" + "-draft"
        raw_name = b"non-utf8-\xff.txt"
        raw_path = os.fsencode(root) + b"/" + raw_name
        descriptor = os.open(
            raw_path,
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
            0o644,
        )
        try:
            os.write(descriptor, (forbidden + "\n").encode("utf-8"))
        finally:
            os.close(descriptor)
        subprocess.run(
            [b"git", b"init", b"-q", os.fsencode(root)],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [b"git", b"-C", os.fsencode(root), b"add", b"--", raw_name],
            check=True,
            capture_output=True,
        )

        code, out = run_validator(["self-check", "--repo-root", str(root)])
        self.assertEqual(code, 1, out)
        self.assertIn(forbidden, out)
        self.assertIn(r"non-utf8-\udcff.txt", out)
        self.assertNotIn("Traceback", out)

    def test_hidden_policy_directive_cannot_acknowledge_a_pin_change(self):
        base = baseline_adoption()
        head = copy.deepcopy(base)
        head["upstream"]["commit"] = "1" * 40
        payload = "Assurance policy change: intentionally hidden"

        for label, body in self.hidden_markdown_variants(payload).items():
            with self.subTest(container=label):
                code, out = self.run_drift(
                    head,
                    changed=(),
                    body=body,
                    base_adoption=base,
                )
                self.assertEqual(code, 1, out)
                self.assertIn("requires an explicit 'Assurance policy change:", out)
                self.assertNotIn("acknowledged by", out)

    def test_hidden_id_and_no_impact_directives_cannot_satisfy_routing(self):
        adoption = baseline_adoption()
        adoption["components"] = {
            "api": {
                "paths": ["src/api/**"],
                "invariants": ["INV-CORE-001"],
            }
        }
        payload = "\n".join(
            (
                "Assurance impact: INV-CORE-001",
                "Assurance impact: none",
                "Reason: intentionally hidden",
            )
        )

        for label, body in self.hidden_markdown_variants(payload).items():
            with self.subTest(container=label):
                code, out = self.run_drift(
                    adoption,
                    changed=["src/api/handler.py"],
                    body=body,
                    strict=True,
                )
                self.assertEqual(code, 1, out)
                self.assertIn("without an assurance update", out)
                self.assertNotIn("declares 'Assurance impact: none'", out)

    def test_invisible_or_html_only_directive_reasons_fail_closed(self):
        adoption = baseline_adoption()
        adoption["components"] = {
            "api": {
                "paths": ["src/api/**"],
                "invariants": ["INV-CORE-001"],
            }
        }
        base = baseline_adoption()
        head = copy.deepcopy(base)
        head["upstream"]["commit"] = "1" * 40
        for payload in ("\u200b", "&ZeroWidthSpace;", "<span></span>"):
            with self.subTest(directive="Reason", payload=payload):
                code, out = self.run_drift(
                    adoption,
                    changed=["src/api/handler.py"],
                    body=f"Assurance impact: none\nReason: {payload}\n",
                    strict=True,
                )
                self.assertEqual(code, 1, out)
                self.assertIn("'Reason:' line is missing", out)

            with self.subTest(directive="policy change", payload=payload):
                code, out = self.run_drift(
                    head,
                    changed=(),
                    body=f"Assurance policy change: {payload}\n",
                    base_adoption=base,
                )
                self.assertEqual(code, 1, out)
                self.assertIn("requires an explicit 'Assurance policy change:", out)
                self.assertNotIn("acknowledged by", out)

    def test_multiple_or_conflicting_impact_directives_are_rejected(self):
        adoption = baseline_adoption()
        adoption["components"] = {
            "api": {
                "paths": ["src/api/**"],
                "invariants": ["INV-CORE-001"],
            }
        }
        bodies = (
            (
                "Assurance impact: INV-CORE-001\n"
                "Assurance impact: none\nReason: no effect\n"
            ),
            (
                "Assurance impact: INV-CORE-001\n"
                "Assurance impact: INV-CORE-001\n"
            ),
            (
                "Assurance impact: not-an-id\n"
                "Assurance impact: INV-CORE-001\n"
            ),
        )
        for body in bodies:
            with self.subTest(body=body):
                code, out = self.run_drift(
                    adoption,
                    changed=["src/api/handler.py"],
                    body=body,
                    strict=True,
                )
                self.assertEqual(code, 1, out)
                self.assertIn("multiple leading 'Assurance impact:'", out)
                self.assertIn("without an assurance update", out)

        # An invalid PR-body route is irrelevant when a durable assurance
        # artifact update already satisfies the touched component, and it
        # must not make an otherwise unrelated/no-component drift run red.
        code, out = self.run_drift(
            adoption,
            changed=["src/api/handler.py"],
            body=bodies[0],
            assurance_diff=(
                "diff --git a/assurance/INVARIANTS.yaml "
                "b/assurance/INVARIANTS.yaml\n"
                "@@ -1 +1 @@\n-old\n+INV-CORE-001 updated\n"
            ),
            strict=True,
        )
        self.assertEqual(code, 0, out)

        code, out = self.run_drift(
            baseline_adoption(),
            changed=(),
            body=bodies[0],
            strict=True,
        )
        self.assertEqual(code, 0, out)

    def test_markdown_metadata_and_code_ids_cannot_satisfy_routing(self):
        adoption = baseline_adoption()
        adoption["components"] = {
            "api": {
                "paths": ["src/api/**"],
                "invariants": ["INV-CORE-001"],
            }
        }
        bodies = {
            "link-destination": (
                "[routine review](https://example.invalid/INV-CORE-001)\n"
            ),
            "html-attribute": (
                '<span data-assurance="INV-CORE-001">routine review</span>\n'
            ),
            "indented-code": "    Assurance impact: INV-CORE-001\n",
            "blockquote-fence": (
                "> ```text\n"
                "> Assurance impact: INV-CORE-001\n"
                "> ```\n"
            ),
        }
        for label, body in bodies.items():
            with self.subTest(container=label):
                code, out = self.run_drift(
                    adoption,
                    changed=["src/api/handler.py"],
                    body=body,
                    strict=True,
                )
                self.assertEqual(code, 1, out)
                self.assertIn("without an assurance update", out)

    def test_explicit_impact_line_requires_all_exact_component_ids(self):
        adoption = baseline_adoption()
        adoption["components"] = {
            "api": {
                "paths": ["src/api/**"],
                "invariants": ["INV-CORE-001", "INV-CORE-002"],
            }
        }
        for body in (
            "Assurance impact: INV-CORE-001\n",
            "Assurance impact: INV-CORE-001-EXT-002, INV-CORE-002\n",
            "The prose mentions INV-CORE-001 and INV-CORE-002.\n",
            (
                "Summary first\n\n"
                "Assurance impact: INV-CORE-001, INV-CORE-002\n"
            ),
            (
                "Assurance impact: INV-CORE-001, INV-CORE-002, "
                "not-an-invariant-id\n"
            ),
        ):
            with self.subTest(body=body):
                code, out = self.run_drift(
                    adoption,
                    changed=["src/api/handler.py"],
                    body=body,
                    strict=True,
                )
                self.assertEqual(code, 1, out)
                self.assertIn("without an assurance update", out)

        code, out = self.run_drift(
            adoption,
            changed=["src/api/handler.py"],
            body="Assurance impact: INV-CORE-001, INV-CORE-002\n",
            strict=True,
        )
        self.assertEqual(code, 0, out)

    def test_standalone_drift_rejects_malformed_component_invariant_ids(self):
        adoption = baseline_adoption()
        adoption["components"] = {
            "api": {
                "paths": ["src/api/**"],
                "invariants": ["not-an-invariant-id"],
            }
        }
        code, out = self.run_drift(adoption, changed=["src/api/handler.py"])
        self.assertEqual(code, 1, out)
        self.assertIn("invariant ID", out)

    def test_component_path_invariant_and_changed_file_count_limits(self):
        cases = {}

        too_many_components = baseline_adoption()
        too_many_components["components"] = {
            f"component-{index}": {
                "paths": [f"src/{index}/**"],
                "invariants": ["INV-CORE-001"],
            }
            for index in range(257)
        }
        cases["components"] = (
            too_many_components,
            (),
            "256-component routing limit",
        )

        too_many_paths = baseline_adoption()
        too_many_paths["components"] = {
            "api": {
                "paths": [f"src/{index}/**" for index in range(257)],
                "invariants": ["INV-CORE-001"],
            }
        }
        cases["paths"] = (too_many_paths, (), "256-path-glob limit")

        too_many_invariants = baseline_adoption()
        too_many_invariants["components"] = {
            "api": {
                "paths": ["src/api/**"],
                "invariants": [f"INV-COMP-{index:03d}" for index in range(257)],
            }
        }
        cases["invariants"] = (
            too_many_invariants,
            (),
            "256-invariant limit",
        )

        too_many_changed = baseline_adoption()
        too_many_changed["components"] = {
            "api": {
                "paths": ["src/api/**"],
                "invariants": ["INV-CORE-001"],
            }
        }
        cases["changed-files"] = (
            too_many_changed,
            tuple(f"src/file-{index}.py" for index in range(20_001)),
            "20,000-changed-file limit",
        )

        for label, (adoption, changed, diagnostic) in cases.items():
            with self.subTest(limit=label):
                code, out = self.run_drift(adoption, changed=changed)
                self.assertEqual(code, 1, out)
                self.assertIn(diagnostic, out)
                self.assertNotIn("Traceback", out)

    def test_aggregate_glob_match_work_limit(self):
        adoption = baseline_adoption()
        patterns = ["?" * 1018 + f"{index:06d}" for index in range(20)]
        adoption["components"] = {
            "expensive": {
                "paths": patterns,
                "invariants": ["INV-CORE-001"],
            }
        }
        changed = ["src/" + "a" * 90 + f"{index:03d}" for index in range(20)]

        code, out = self.run_drift(adoption, changed=changed, timeout=10)
        self.assertEqual(code, 1, out)
        self.assertIn("too much glob-matching work", out)
        self.assertIn("limit 20,000,000", out)
        self.assertNotIn("Traceback", out)

    def test_aggregate_assurance_diff_mention_work_limit(self):
        adoption = baseline_adoption()
        adoption["components"] = {
            "many-invariants": {
                "paths": ["src/api/**"],
                "invariants": [f"INV-COMP-{index:03d}" for index in range(256)],
            }
        }

        code, out = self.run_drift(
            adoption,
            changed=["src/api/handler.py"],
            assurance_diff=(
                "diff --git a/assurance/INVARIANTS.yaml "
                "b/assurance/INVARIANTS.yaml\n"
                "--- a/assurance/INVARIANTS.yaml\n"
                "+++ b/assurance/INVARIANTS.yaml\n"
                "@@ -0,0 +1 @@\n"
                "+" + ("x" * 80_000) + "\n"
            ),
            timeout=10,
        )
        self.assertEqual(code, 1, out)
        self.assertIn("too much invariant-mention scanning", out)
        self.assertIn("limit 20,000,000", out)
        self.assertNotIn("Traceback", out)

    def test_added_hunk_content_beginning_with_three_pluses_is_not_a_header(self):
        adoption = baseline_adoption()
        adoption["components"] = {
            "api": {
                "paths": ["src/api/**"],
                "invariants": ["INV-CORE-001"],
            }
        }
        assurance_diff = """\
diff --git a/assurance/INVARIANTS.yaml b/assurance/INVARIANTS.yaml
--- a/assurance/INVARIANTS.yaml
+++ b/assurance/INVARIANTS.yaml
@@ -0,0 +1 @@
+++ INV-CORE-001
"""

        code, out = self.run_drift(
            adoption,
            changed=["src/api/handler.py"],
            assurance_diff=assurance_diff,
            strict=True,
        )
        self.assertEqual(code, 0, out)
        self.assertIn("assurance update references INV-CORE-001", out)

    def test_deep_policy_json_is_a_controlled_error(self):
        root = self.make_tmp()
        adoption = baseline_adoption()
        write_yaml(root / "adoption.yaml", adoption)
        write_yaml(root / "base-adoption.yaml", adoption)
        (root / "changed.txt").write_bytes(b"")
        (root / "body.txt").write_text("", encoding="utf-8")
        # This remains parseable by CPython's decoder but exceeds the explicit
        # iterative 256-level policy budget, exercising the post-decode guard
        # rather than relying on an interpreter-specific RecursionError.
        depth = 300
        (root / "transition.json").write_text(
            "[" * depth + "0" + "]" * depth,
            encoding="utf-8",
        )

        code, out = run_validator(
            [
                "drift",
                "--adoption",
                str(root / "adoption.yaml"),
                "--changed-files",
                str(root / "changed.txt"),
                "--pr-body",
                str(root / "body.txt"),
                "--base-adoption",
                str(root / "base-adoption.yaml"),
                "--adoption-path-transition",
                str(root / "transition.json"),
            ]
        )
        self.assertEqual(code, 1, out)
        self.assertIn("nesting is too deep", out)
        self.assertNotIn("Traceback", out)

    def test_only_the_full_shipped_starter_fingerprint_is_exempt(self):
        base = baseline_adoption()
        base["upstream"]["version"] = "v0.3.2"
        head = copy.deepcopy(base)
        head["upstream"]["version"] = "v0.4.0"
        starter = self.shipped_claim_starter()

        base_registers = {
            "claims": {"version": 1, "claims": [starter]},
        }
        head_registers = {
            "claims": {"version": 1, "claims": []},
        }
        code, out = self.run_drift(
            head,
            changed=(),
            body="Assurance policy change: upgrade to v0.4.0\n",
            base_adoption=base,
            base_registers=base_registers,
            head_registers=head_registers,
        )
        self.assertEqual(code, 0, out)
        self.assertNotIn("CLAIM-EXAMPLE-001 deleted", out)

        protected_variants = {}
        partial = copy.deepcopy(starter)
        partial["text"] = "A real project claim was already recorded"
        protected_variants["partly-completed"] = partial
        extended = copy.deepcopy(starter)
        extended["extensions"] = {"note": "project-owned metadata"}
        protected_variants["extra-metadata"] = extended

        for label, protected in protected_variants.items():
            with self.subTest(starter_variant=label):
                protected_base = {
                    "claims": {"version": 1, "claims": [protected]},
                }
                code, out = self.run_drift(
                    head,
                    changed=(),
                    body="Assurance policy change: upgrade to v0.4.0\n",
                    base_adoption=base,
                    base_registers=protected_base,
                    head_registers=head_registers,
                )
                self.assertEqual(code, 0, out)
                self.assertIn("assurance policy weakened", out)
                self.assertIn("claims entry CLAIM-EXAMPLE-001 deleted", out)

    def test_starter_exemption_requires_an_actual_v04_upgrade(self):
        base = baseline_adoption()
        base["upstream"]["version"] = "v0.3.2"
        head = copy.deepcopy(base)
        starter = self.shipped_claim_starter()

        code, out = self.run_drift(
            head,
            changed=(),
            base_adoption=base,
            base_registers={
                "claims": {"version": 1, "claims": [starter]},
            },
            head_registers={
                "claims": {"version": 1, "claims": []},
            },
        )
        self.assertEqual(code, 1, out)
        self.assertIn("claims entry CLAIM-EXAMPLE-001 deleted", out)

    def test_very_long_release_version_does_not_crash_migration_check(self):
        base = baseline_adoption()
        base["upstream"]["version"] = "v0.3.2"
        head = copy.deepcopy(base)
        head["upstream"]["version"] = "v" + ("9" * 5_000) + ".0.0"
        starter = self.shipped_claim_starter()

        code, out = self.run_drift(
            head,
            changed=(),
            body="Assurance policy change: exercise bounded version parsing\n",
            base_adoption=base,
            base_registers={
                "claims": {"version": 1, "claims": [starter]},
            },
            head_registers={
                "claims": {"version": 1, "claims": []},
            },
        )
        self.assertEqual(code, 0, out)
        self.assertNotIn("CLAIM-EXAMPLE-001 deleted", out)
        self.assertNotIn("Traceback", out)

    def test_arbitrary_placeholder_cannot_create_a_two_hop_starter_exemption(self):
        base = baseline_adoption()
        base["upstream"]["version"] = "v0.3.2"
        head = copy.deepcopy(base)
        completed = self.shipped_claim_starter()
        completed.update(
            {
                "text": "The API rejects unauthorized requests",
                "scope": "API v1",
                "owner": "Alice Example",
            }
        )
        placeholder = copy.deepcopy(completed)
        placeholder["text"] = "REPLACE_WITH_ANYTHING"
        completed_registers = {
            "claims": {"version": 1, "claims": [completed]},
        }
        placeholder_registers = {
            "claims": {"version": 1, "claims": [placeholder]},
        }
        deleted_registers = {
            "claims": {"version": 1, "claims": []},
        }

        first_code, first_out = self.run_drift(
            head,
            changed=(),
            base_adoption=base,
            base_registers=completed_registers,
            head_registers=placeholder_registers,
        )
        self.assertEqual(first_code, 1, first_out)
        self.assertIn("text was replaced with a template placeholder", first_out)

        second_code, second_out = self.run_drift(
            head,
            changed=(),
            base_adoption=base,
            base_registers=placeholder_registers,
            head_registers=deleted_registers,
        )
        self.assertEqual(second_code, 1, second_out)
        self.assertIn("claims entry CLAIM-EXAMPLE-001 deleted", second_out)

    def test_core_draft_verified_critical_requires_both_mechanism_lists(self):
        for missing in ("enforcement", "verification"):
            with self.subTest(missing=missing):
                registers = baseline_registers()
                invariant = registers["invariants"]["invariants"][0]
                invariant.update(
                    {
                        "severity": "critical",
                        "status": "VERIFIED",
                        "enforcement": ["authorization guard"],
                        "verification": ["tests/test_authorization.py"],
                    }
                )
                del invariant[missing]

                code, out = self.run_split(baseline_adoption(), registers)
                self.assertEqual(code, 1, out)
                self.assertIn(
                    f"VERIFIED with severity critical but its {missing} list is empty",
                    out,
                )

    def test_service_critical_invariants_always_require_real_mechanism_refs(self):
        for missing in ("enforcement", "verification"):
            with self.subTest(missing=missing):
                root = self.make_tmp()
                adoption = baseline_adoption()
                adoption["profiles"] = ["service"]
                registers = baseline_registers()
                invariant = registers["invariants"]["invariants"][0]
                invariant.update(
                    {
                        "severity": "critical",
                        "status": "INFERRED",
                        "enforcement": ["authorization guard"],
                        "verification": ["tests/test_authorization.py"],
                    }
                )
                del invariant[missing]
                adoption_path = build_split_project(root, adoption, registers)
                (root / "assurance" / "THREAT_MODEL.md").write_text(
                    "# Threat model\n",
                    encoding="utf-8",
                )

                code, out = self.run_adopter(root, adoption_path)
                self.assertEqual(code, 1, out)
                self.assertIn("service", out)
                self.assertIn(missing, out)

        root = self.make_tmp()
        adoption = baseline_adoption()
        adoption["profiles"] = ["service"]
        registers = baseline_registers()
        registers["invariants"]["invariants"][0].update(
            {
                "severity": "critical",
                "status": "INFERRED",
                "enforcement": ["REPLACE_WITH_ENFORCEMENT_REFERENCE"],
                "verification": ["REPLACE_WITH_VERIFICATION_REFERENCE"],
            }
        )
        adoption_path = build_split_project(root, adoption, registers)
        (root / "assurance" / "THREAT_MODEL.md").write_text(
            "# Threat model\n",
            encoding="utf-8",
        )
        code, out = self.run_adopter(root, adoption_path)
        self.assertEqual(code, 1, out)
        self.assertIn("enforcement", out)
        self.assertIn("verification", out)

    def test_draft_semantics_do_not_accept_substituted_placeholders(self):
        layouts = ("split", "lite")
        for layout in layouts:
            with self.subTest(layout=layout, field="intent.authority"):
                adoption = (
                    baseline_adoption()
                    if layout == "split"
                    else baseline_lite_adoption()
                )
                if layout == "split":
                    artifact = baseline_registers()
                    invariant = artifact["invariants"]["invariants"][0]
                else:
                    artifact = baseline_lite_assurance()
                    invariant = artifact["invariants"][0]
                invariant["intent"] = {
                    "classification": "INTENDED",
                    "authority": "REPLACE_WITH_AUTHORITY",
                }
                code, out = (
                    self.run_split(adoption, artifact)
                    if layout == "split"
                    else self.run_lite(adoption, artifact)
                )
                self.assertEqual(code, 1, out)
                self.assertIn("intent.authority", out)

            with self.subTest(layout=layout, field="mechanisms"):
                adoption = (
                    baseline_adoption()
                    if layout == "split"
                    else baseline_lite_adoption()
                )
                if layout == "split":
                    artifact = baseline_registers()
                    invariant = artifact["invariants"]["invariants"][0]
                else:
                    artifact = baseline_lite_assurance()
                    invariant = artifact["invariants"][0]
                invariant.update(
                    {
                        "severity": "critical",
                        "status": "VERIFIED",
                        "enforcement": ["REPLACE_WITH_ENFORCEMENT_REFERENCE"],
                        "verification": ["REPLACE_WITH_VERIFICATION_REFERENCE"],
                    }
                )
                code, out = (
                    self.run_split(adoption, artifact)
                    if layout == "split"
                    else self.run_lite(adoption, artifact)
                )
                self.assertEqual(code, 1, out)
                self.assertIn("enforcement", out)
                self.assertIn("verification", out)

            for field, placeholder in (
                ("acceptance_rationale", "REPLACE_WITH_ACCEPTANCE_RATIONALE"),
                ("accepted_by", "REPLACE_WITH_ACCEPTOR"),
                ("accepted_at", CURRENT_REVIEW_DATE_PLACEHOLDER),
            ):
                with self.subTest(layout=layout, field=field):
                    adoption = (
                        baseline_adoption()
                        if layout == "split"
                        else baseline_lite_adoption()
                    )
                    artifact = (
                        baseline_registers()
                        if layout == "split"
                        else baseline_lite_assurance()
                    )
                    residuals = (
                        artifact["residuals"]["residuals"]
                        if layout == "split"
                        else artifact["residuals"]
                    )
                    residuals[0].update(
                        {
                            "status": "ACCEPTED",
                            "acceptance_rationale": "Owner accepted bounded risk",
                            "accepted_by": "Alice Example",
                            "accepted_at": "2026-01-01",
                            field: placeholder,
                        }
                    )
                    code, out = (
                        self.run_split(adoption, artifact)
                        if layout == "split"
                        else self.run_lite(adoption, artifact)
                    )
                    self.assertEqual(code, 1, out)
                    self.assertIn(field, out)
                    self.assertIn("unfilled placeholder", out)

            with self.subTest(layout=layout, field="resolution_note"):
                adoption = (
                    baseline_adoption()
                    if layout == "split"
                    else baseline_lite_adoption()
                )
                artifact = (
                    baseline_registers()
                    if layout == "split"
                    else baseline_lite_assurance()
                )
                residuals = (
                    artifact["residuals"]["residuals"]
                    if layout == "split"
                    else artifact["residuals"]
                )
                residuals[0].update(
                    {
                        "status": "RESOLVED",
                        "resolution_note": "REPLACE_WITH_RESOLUTION_NOTE",
                    }
                )
                code, out = (
                    self.run_split(adoption, artifact)
                    if layout == "split"
                    else self.run_lite(adoption, artifact)
                )
                self.assertEqual(code, 1, out)
                self.assertIn("resolution_note", out)
                self.assertIn("unfilled placeholder", out)

            with self.subTest(layout=layout, field="defeater.resolution"):
                adoption = (
                    baseline_adoption()
                    if layout == "split"
                    else baseline_lite_adoption()
                )
                artifact = (
                    baseline_registers()
                    if layout == "split"
                    else baseline_lite_assurance()
                )
                defeater = {
                    "id": "DEF-CORE-001",
                    "statement": "A recorded defeater",
                    "status": "OPEN",
                    "disclosure": "PUBLIC",
                    "owner": "Alice Example",
                }
                if layout == "split":
                    artifact["defeaters"] = {
                        "version": 1,
                        "defeaters": [defeater],
                    }
                else:
                    artifact["defeaters"] = [defeater]
                defeaters = (
                    artifact["defeaters"]["defeaters"]
                    if layout == "split"
                    else artifact["defeaters"]
                )
                defeaters[0].update(
                    {
                        "status": "RESOLVED",
                        "resolution": "REPLACE_WITH_RESOLUTION",
                    }
                )
                code, out = (
                    self.run_split(adoption, artifact)
                    if layout == "split"
                    else self.run_lite(adoption, artifact)
                )
                self.assertEqual(code, 1, out)
                self.assertIn("resolution", out)
                self.assertIn("unfilled placeholder", out)

    def test_control_characters_in_declared_paths_fail_without_traceback(self):
        cases = {
            "paths.system": lambda adoption: adoption.setdefault("paths", {}).update(
                {"system": "assurance/\0SYSTEM.md"}
            ),
            "specification_workflow.root": lambda adoption: adoption[
                "specification_workflow"
            ].update({"root": "docs/\0workflow.md"}),
            "human_review.record": lambda adoption: adoption["human_review"].update(
                {"record": "docs/reviews/\0review.md"}
            ),
        }
        for label, mutate in cases.items():
            with self.subTest(path_field=label):
                root = self.make_tmp()
                adoption = baseline_adoption()
                adoption["adoption_stage"] = "HUMAN_REVIEWED"
                adoption["human_review"] = human_review_block()
                adoption_path = build_split_project(
                    root, adoption, baseline_registers()
                )
                mutate(adoption)
                write_yaml(adoption_path, adoption)

                code, out = self.run_adopter(root, adoption_path)
                self.assertEqual(code, 1, out)
                self.assertIn(label.split(".")[-1], out)
                self.assertNotIn("Traceback", out)

    def test_archived_draft_rejects_empty_system(self):
        root = self.make_tmp()
        adoption = baseline_adoption()
        adoption["profiles"] = ["archived"]
        adoption_path = build_split_project(root, adoption, {})
        (root / "assurance" / "SYSTEM.md").write_text(" \n", encoding="utf-8")

        code, out = self.run_adopter(root, adoption_path)
        self.assertEqual(code, 1, out)
        self.assertIn("empty or whitespace-only", out)

    def test_reviewed_profile_and_pin_findings_stay_errors_when_acknowledged(self):
        cases = {}

        pin_base = baseline_adoption()
        pin_base["adoption_stage"] = "HUMAN_REVIEWED"
        pin_base["human_review"] = human_review_block()
        pin_head = copy.deepcopy(pin_base)
        pin_head["upstream"]["commit"] = "1" * 40
        cases["pin"] = (pin_base, pin_head, "upstream pin changed")

        profile_base = baseline_adoption()
        profile_base["profiles"] = ["archived"]
        profile_base["adoption_stage"] = "HUMAN_REVIEWED"
        profile_base["human_review"] = human_review_block()
        profile_head = copy.deepcopy(profile_base)
        profile_head["profiles"] = ["core"]
        cases["profile"] = (
            profile_base,
            profile_head,
            "assurance profile mode changed",
        )

        body = "Assurance policy change: reviewed owner accepts this change\n"
        for label, (base, head, finding) in cases.items():
            with self.subTest(finding=label):
                code, out = self.run_drift(
                    head,
                    changed=(),
                    body=body,
                    base_adoption=base,
                )
                self.assertEqual(code, 1, out)
                self.assertIn(finding, out)
                self.assertIn(
                    "acknowledged, but the base declaration is stage HUMAN_REVIEWED",
                    out,
                )


if __name__ == "__main__":
    unittest.main()
