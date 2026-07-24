"""Tests for scripts/aap.py — the thin ADOPTER_SNAPSHOT alpha CLI facade.

Standard library only. The facade must be behavior-preserving: for equivalent
inputs it produces the same exit code as ``validate.py adopter`` and never
drops an engine result line. These tests also pin the auto-resolution of the
low-level paths and the 0/1/2/3 exit-code contract the engine itself does not
provide.

The pinned-version and pinned-commit checks in the engine make the v0.4.0
characterization fixtures report a version/commit mismatch against the current
development checkout, so their absolute pass/fail is not the invariant here.
The invariant is that ``aap check`` and ``validate.py adopter`` agree.
"""

import argparse
import contextlib
import io
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
AAP = REPO_ROOT / "scripts" / "aap.py"
VALIDATOR = REPO_ROOT / "scripts" / "validate.py"
SCHEMAS = REPO_ROOT / "schemas"
CORPUS = REPO_ROOT / "tests" / "characterization" / "v0.4.0" / "cases"

# The four ADOPTER_SNAPSHOT seeds (the drift and self-check cases are out of
# scope for ``aap check``).
SNAPSHOT_CASES = (
    "core-lite-draft-pass",
    "core-split-draft-pass",
    "archived-reviewed-pass",
    "trust-path-traversal-block",
)

RESULT_PREFIXES = ("ERROR:", "WARN:", "OK:")


def _run(argv, cwd=None):
    return subprocess.run(
        [sys.executable, *argv],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def _run_aap(args, cwd=None):
    return _run([str(AAP), *args], cwd=cwd)


def _run_engine_adopter(project):
    adoption = project / ".agentic-assurance" / "adoption.yaml"
    return _run(
        [
            str(VALIDATOR),
            "adopter",
            "--adoption",
            str(adoption),
            "--project-root",
            str(project),
            "--schemas",
            str(SCHEMAS),
        ]
    )


def _stage(case, tmp):
    """Copy a fixture's ``project/`` outside the profile checkout.

    The engine's trust boundary requires adopter-owned artifacts to live
    outside the pinned profile checkout, so — like the characterization
    harness — the corpus is staged to a separate root before evaluation.
    """
    dest = Path(tmp) / case
    shutil.copytree(CORPUS / case / "project", dest)
    return dest


class TestFacadeEquivalence(unittest.TestCase):
    def test_snapshot_facade_matches_engine(self):
        for case in SNAPSHOT_CASES:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                project = _stage(case, tmp)
                engine = _run_engine_adopter(project)
                facade = _run_aap(["check", "--project-root", str(project)])
                self.assertEqual(
                    facade.returncode,
                    engine.returncode,
                    f"{case}: facade exit {facade.returncode} != engine "
                    f"{engine.returncode}\nengine:\n{engine.stdout}\n"
                    f"facade:\n{facade.stdout}",
                )
                # The facade must not drop or alter any engine result line.
                engine_lines = [
                    ln
                    for ln in engine.stdout.splitlines()
                    if ln.startswith(RESULT_PREFIXES)
                ]
                self.assertTrue(engine_lines, f"{case}: engine emitted no results")
                for line in engine_lines:
                    self.assertIn(line, facade.stdout, f"{case}: missing {line!r}")

    def test_auto_resolves_adoption_from_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = _stage("core-lite-draft-pass", tmp)
            explicit = _run_aap(["check", "--project-root", str(project)])
            auto = _run_aap(["check"], cwd=str(project))
            self.assertEqual(auto.returncode, explicit.returncode)
            self.assertIn("aap check:", auto.stdout)

    def test_symlinked_adoption_matches_engine(self):
        # Regression: the facade must not pre-resolve the adoption path. The
        # engine handles a symlinked adoption.yaml with distinct diagnostics;
        # collapsing the symlink here would diverge from `validate.py adopter`.
        with tempfile.TemporaryDirectory() as tmp:
            project = _stage("core-lite-draft-pass", tmp)
            adoption = project / ".agentic-assurance" / "adoption.yaml"
            real = project / ".agentic-assurance" / "real-adoption.yaml"
            adoption.rename(real)
            adoption.symlink_to(real.name)  # in-project relative symlink
            engine = _run_engine_adopter(project)
            facade = _run_aap(["check", "--project-root", str(project)])
            self.assertEqual(facade.returncode, engine.returncode)
            for line in engine.stdout.splitlines():
                if line.startswith(RESULT_PREFIXES):
                    self.assertIn(line, facade.stdout, f"missing {line!r}")


class TestExitCodeContract(unittest.TestCase):
    def test_missing_adoption_is_usage_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            res = _run_aap(["check", "--project-root", tmp])
            self.assertEqual(res.returncode, 2, res.stderr)
            self.assertIn("adoption", (res.stdout + res.stderr).lower())

    def test_missing_project_root_is_usage_error(self):
        missing = str(Path(tempfile.gettempdir()) / "aap-does-not-exist-xyz")
        res = _run_aap(["check", "--project-root", missing])
        self.assertEqual(res.returncode, 2, res.stderr)

    def test_no_subcommand_is_usage_error(self):
        res = _run_aap([])
        self.assertEqual(res.returncode, 2)

    def test_findings_case_exits_one(self):
        # trust-path-traversal-block fails closed on the traversal attempt (and
        # on the version pin), so the engine reports errors -> exit 1.
        with tempfile.TemporaryDirectory() as tmp:
            project = _stage("trust-path-traversal-block", tmp)
            res = _run_aap(["check", "--project-root", str(project)])
            self.assertEqual(res.returncode, 1, res.stdout)
            self.assertIn("FINDINGS", res.stdout)

    def test_exit_code_constants_and_mapping(self):
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        import aap

        self.assertEqual(
            (aap.EXIT_PASS, aap.EXIT_FINDINGS, aap.EXIT_USAGE, aap.EXIT_INTERNAL),
            (0, 1, 2, 3),
        )
        self.assertEqual(aap._exit_for_engine_result(0), 0)
        self.assertEqual(aap._exit_for_engine_result(1), 1)
        # An unexpected engine code surfaces as INTERNAL, never silent success.
        self.assertEqual(aap._exit_for_engine_result(5), aap.EXIT_INTERNAL)


class TestFacadeUnit(unittest.TestCase):
    """In-process tests for paths a subprocess equivalence run cannot reach on
    a dev checkout, where every fixture exits 1 on the version pin."""

    def setUp(self):
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        import aap

        self.aap = aap

    def _ns(self, **kw):
        base = dict(project_root=None, adoption=None, repo_visibility=None)
        base.update(kw)
        return argparse.Namespace(**base)

    def test_engine_zero_yields_pass_exit_and_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = _stage("core-lite-draft-pass", tmp)
            with mock.patch.object(self.aap.validate, "main", return_value=0):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    rc = self.aap.cmd_check(self._ns(project_root=str(project)))
            self.assertEqual(rc, 0)
            self.assertIn("PASS", out.getvalue())

    def test_forwards_explicit_adoption_and_visibility(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = _stage("core-lite-draft-pass", tmp)
            # Put the explicit adoption at a NON-default location so the
            # assertion distinguishes "honored the explicit --adoption" from
            # "synthesized the default .agentic-assurance/adoption.yaml".
            explicit = project / "custom-adoption.yaml"
            shutil.copy(project / ".agentic-assurance" / "adoption.yaml", explicit)
            captured = {}

            def fake_main(argv):
                captured["argv"] = argv
                return 1

            with mock.patch.object(self.aap.validate, "main", side_effect=fake_main):
                rc = self.aap.cmd_check(
                    self._ns(
                        project_root=str(project),
                        adoption=str(explicit),
                        repo_visibility="private",
                    )
                )
            self.assertEqual(rc, 1)
            argv = captured["argv"]
            self.assertEqual(argv[0], "adopter")
            self.assertEqual(argv[argv.index("--repo-visibility") + 1], "private")
            # The exact explicit path is forwarded, not the default location.
            self.assertEqual(argv[argv.index("--adoption") + 1], str(explicit))

    def test_visibility_absent_not_forwarded(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = _stage("core-lite-draft-pass", tmp)
            captured = {}

            def fake_main(argv):
                captured["argv"] = argv
                return 1

            with mock.patch.object(self.aap.validate, "main", side_effect=fake_main):
                self.aap.cmd_check(self._ns(project_root=str(project)))
            self.assertNotIn("--repo-visibility", captured["argv"])


if __name__ == "__main__":
    unittest.main()
