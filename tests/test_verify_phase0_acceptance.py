"""Tests for ``scripts/verify_phase0_acceptance.py``.

The standard-library-only black-box cases build synthetic Git repositories
with separate candidate and acceptance merges.  One shallow-safe component
case also checks the committed manifest, ledger, and local corpus roots for
contract compatibility.  Fixture hashes are calculated independently of the
verifier so the black-box tests do not share its implementation.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import runpy
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Callable, Optional


REPO_ROOT = Path(__file__).resolve().parent.parent
VERIFIER = REPO_ROOT / "scripts" / "verify_phase0_acceptance.py"
EXPECTED_REPOSITORY = "example/phase0-verifier-fixture"
DECISION_ID = "AAP-V05-P0-ORACLE-TEST-001"
DECISION_PATH = (
    "docs/evidence/v0.5/oracle-decisions/"
    "AAP-V05-P0-ORACLE-TEST-001.json"
)
REUSED_DECISION_PATH = (
    "docs/evidence/v0.5/oracle-decisions/reused-decision-id.json"
)
MANIFEST_PATH = "tests/characterization/v0.4.0/manifest.json"
LEDGER_PATH = "tests/characterization/v0.4.0/expected-outcomes.json"
CORPUS_PATH = "tests/characterization/v0.4.0/cases/core-seed"
GOVERNANCE_PATH = "GOVERNANCE.md"
LEDGER_REVISION = "synthetic-seven-seed-contract-r1"
LEDGER_SHAPE_REVISION = "phase0-synthetic-candidate-1"
CASE_ID = "core-seed-pass"
CONDITION_KEY = "phase0.internal.synthetic.core-seed-satisfied"
AUTHORITY_SOURCE_ID = "synthetic-v0.4.0-release"

VERIFIER_NAMESPACE = runpy.run_path(
    str(VERIFIER), run_name="_phase0_acceptance_verifier_component"
)


def raw_sha256(data: bytes) -> str:
    """Return the lowercase SHA-256 of exact bytes."""

    return hashlib.sha256(data).hexdigest()


def canonical_records_sha256(records: list[dict[str, object]]) -> str:
    """Hash the canonical JSON serialization used by the Phase 0 corpus."""

    encoded = json.dumps(
        records,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return raw_sha256(encoded)


def directory_tree_record(root: Path, root_id: str, source_path: str) -> dict:
    """Independently calculate one regular-file corpus root record."""

    records: list[dict[str, object]] = []
    for path in sorted(
        root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()
    ):
        metadata = path.lstat()
        relative = path.relative_to(root).as_posix()
        if stat.S_ISLNK(metadata.st_mode):
            raise AssertionError(f"synthetic corpus contains symlink: {relative}")
        if stat.S_ISDIR(metadata.st_mode):
            continue
        if not stat.S_ISREG(metadata.st_mode):
            raise AssertionError(
                f"synthetic corpus contains non-regular file: {relative}"
            )
        data = path.read_bytes()
        records.append(
            {
                "path": relative,
                "size": len(data),
                "sha256": raw_sha256(data),
            }
        )
    return {
        "root_id": root_id,
        "source": {"kind": "corpus_directory", "path": source_path},
        "file_count": len(records),
        "byte_count": sum(int(record["size"]) for record in records),
        "tree_sha256": canonical_records_sha256(records),
    }


def corpus_sha256(root_records: list[dict]) -> str:
    """Independently calculate the aggregate over root IDs and tree hashes."""

    records = sorted(
        (
            {
                "root_id": record["root_id"],
                "tree_sha256": record["tree_sha256"],
            }
            for record in root_records
        ),
        key=lambda record: record["root_id"],
    )
    return canonical_records_sha256(records)


def json_bytes(value: object) -> bytes:
    """Serialize fixture JSON deterministically, including one final newline."""

    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def repository_git_bytes(*args: str) -> bytes:
    """Read current-HEAD objects without requiring pre-HEAD history."""

    return subprocess.check_output(
        ["git", "--no-replace-objects", "-C", str(REPO_ROOT), *args],
        stdin=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        env={
            **os.environ,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_NO_LAZY_FETCH": "1",
        },
    )


def committed_file_bytes(relative: str) -> bytes:
    """Read one artifact from the current committed tree."""

    return repository_git_bytes("show", f"HEAD:{relative}")


def committed_directory_tree_record(
    scope: str,
    root_id: str,
    source_path: str,
) -> dict:
    """Independently calculate a corpus record from current-HEAD blobs."""

    output = repository_git_bytes(
        "ls-tree",
        "-r",
        "-z",
        "--full-tree",
        "HEAD",
        "--",
        f":(top,literal){scope}",
    )
    prefix = scope + "/"
    records: list[dict[str, object]] = []
    for raw_entry in output.split(b"\0"):
        if not raw_entry:
            continue
        metadata, raw_path = raw_entry.split(b"\t", 1)
        mode, object_type, oid = metadata.decode("ascii").split(" ")
        path = raw_path.decode("utf-8")
        if mode != "100644" or object_type != "blob":
            raise AssertionError(f"committed corpus has unsupported entry: {path}")
        if not path.startswith(prefix):
            raise AssertionError(f"committed corpus path escaped scope: {path}")
        relative = path[len(prefix) :]
        data = repository_git_bytes("cat-file", "blob", oid)
        records.append(
            {
                "path": relative,
                "size": len(data),
                "sha256": raw_sha256(data),
            }
        )
    records.sort(key=lambda record: str(record["path"]).encode("ascii"))
    return {
        "root_id": root_id,
        "source": {"kind": "corpus_directory", "path": source_path},
        "file_count": len(records),
        "byte_count": sum(int(record["size"]) for record in records),
        "tree_sha256": canonical_records_sha256(records),
    }


class SyntheticAcceptanceRepository:
    """Create the exact Git topology consumed by the verifier CLI."""

    def __init__(
        self,
        *,
        ledger_mutator: Optional[Callable[[dict], None]] = None,
        decision_mutator: Optional[Callable[[dict], None]] = None,
        decision_text_mutator: Optional[Callable[[str], str]] = None,
        acceptance_extra_file: bool = False,
        merge_acceptance: bool = True,
        executable_corpus_entry: bool = False,
    ) -> None:
        self._temporary = tempfile.TemporaryDirectory(
            prefix="phase0-acceptance-verifier-test-"
        )
        self.root = Path(self._temporary.name)
        self.ledger_mutator = ledger_mutator
        self.decision_mutator = decision_mutator
        self.decision_text_mutator = decision_text_mutator
        self.acceptance_extra_file = acceptance_extra_file
        self.merge_acceptance = merge_acceptance
        self.executable_corpus_entry = executable_corpus_entry
        self._build()

    def __enter__(self) -> "SyntheticAcceptanceRepository":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self._temporary.cleanup()

    def git(
        self, *args: str, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            ["git", *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
            env={
                **os.environ,
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_AUTHOR_NAME": "Phase 0 Test",
                "GIT_AUTHOR_EMAIL": "phase0-test@example.invalid",
                "GIT_COMMITTER_NAME": "Phase 0 Test",
                "GIT_COMMITTER_EMAIL": "phase0-test@example.invalid",
            },
        )
        if check and completed.returncode != 0:
            raise AssertionError(
                f"git {' '.join(args)} failed ({completed.returncode})\n"
                f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
            )
        return completed

    def rev_parse(self, revision: str = "HEAD") -> str:
        return self.git("rev-parse", revision).stdout.strip()

    def write_bytes(self, relative: str, data: bytes) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def write_text(self, relative: str, text: str) -> None:
        self.write_bytes(relative, text.encode("utf-8"))

    def write_json(self, relative: str, value: object) -> None:
        self.write_bytes(relative, json_bytes(value))

    def commit_all(self, message: str) -> str:
        self.git("add", "-A")
        self.git("-c", "commit.gpgsign=false", "commit", "-m", message)
        return self.rev_parse()

    def status_bytes(self) -> bytes:
        return subprocess.check_output(
            ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
            cwd=self.root,
            env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1"},
        )

    def _build(self) -> None:
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Phase 0 Test")
        self.git("config", "user.email", "phase0-test@example.invalid")
        self.git("config", "commit.gpgsign", "false")

        self.governance_bytes = (
            b"# Governance\n\n"
            b"## 1. Governing body\n\nSynthetic maintainers.\n\n"
            b"## 2. Decision rules\n\n"
            b"SOLE_OWNER_ATTESTED and AUTOMATION_VERIFIED are factual classes.\n"
        )
        self.write_bytes(GOVERNANCE_PATH, self.governance_bytes)
        self.write_text("README.md", "# Synthetic verifier repository\n")
        self.write_text(
            "scripts/validate.py",
            "#!/usr/bin/env python3\nprint('synthetic validator')\n",
        )
        self.write_text(
            "requirements-ci.txt",
            "# Synthetic reference lock; no dependencies are executed.\n",
        )
        self.initial_commit = self.commit_all("initial governance")
        self.git(
            "-c",
            "tag.gpgSign=false",
            "tag",
            "-a",
            "v0.4.0-test",
            "-m",
            "synthetic v0.4.0 release",
            self.initial_commit,
        )
        self.reference_tag_object = self.rev_parse("refs/tags/v0.4.0-test")
        self.validator_blob = self.rev_parse(
            f"{self.initial_commit}:scripts/validate.py"
        )
        self.requirements_blob = self.rev_parse(
            f"{self.initial_commit}:requirements-ci.txt"
        )

        self.git("checkout", "-b", "candidate")
        self.write_text(f"{CORPUS_PATH}/input.txt", "synthetic input\n")
        self.write_text(f"{CORPUS_PATH}/nested/evidence.txt", "evidence\n")
        if self.executable_corpus_entry:
            (self.root / CORPUS_PATH / "input.txt").chmod(0o755)
        root_record = directory_tree_record(
            self.root / CORPUS_PATH,
            "case-core-seed",
            "cases/core-seed",
        )
        self.corpus_digest = corpus_sha256([root_record])
        self.coverage = {
            "phase0_matrix_complete": False,
            "semantic_projection_complete_for_selected_cases": True,
            "implementation_projection_complete_for_selected_cases": False,
        }
        self.manifest = {
            "document_kind": "phase0_fixture_manifest_scaffold",
            "status": "PROPOSED_NOT_ACCEPTED",
            "public_contract": False,
            "coverage_complete": False,
            "reference": {
                "release": "v0.4.0-test",
                "annotated_tag_object_sha1": self.reference_tag_object,
                "peeled_commit_sha1": self.initial_commit,
                "validator_git_blob_sha1": self.validator_blob,
                "requirements_git_blob_sha1": self.requirements_blob,
                "network_during_execution": "forbidden",
            },
            "digest": {
                "algorithm": (
                    "sha256-over-canonical-root-records-described-in-README"
                ),
                "corpus_sha256": self.corpus_digest,
            },
            "root_records": [root_record],
            "cases": [
                {
                    "case_id": CASE_ID,
                    "input_root_id": "case-core-seed",
                }
            ],
        }
        self.manifest_bytes = json_bytes(self.manifest)
        self.write_bytes(MANIFEST_PATH, self.manifest_bytes)

        self.ledger = {
            "document_kind": "phase0_expected_outcomes_scaffold",
            "ledger_shape_revision": LEDGER_SHAPE_REVISION,
            "status": "PROPOSED_NOT_ACCEPTED",
            "oracle": False,
            "public_contract": False,
            "coverage": self.coverage,
            "proposed_ledger_revision": LEDGER_REVISION,
            "acceptance_binding": None,
            "candidate_use": {
                "semantic_acceptance_candidate_for_selected_cases": True,
                "implementation_consumable": False,
            },
            "authority_sources": {
                AUTHORITY_SOURCE_ID: {
                    "repository": EXPECTED_REPOSITORY,
                    "release": "v0.4.0-test",
                    "commit_sha1": self.initial_commit,
                }
            },
            "condition_catalog": {
                CONDITION_KEY: {
                    "kind": "REQUIRED_SATISFIED_CONDITION",
                    "statement": (
                        "The selected synthetic core seed contains its bounded "
                        "required input; this is not a complete gate claim."
                    ),
                    "authority_refs": [
                        {
                            "source_id": AUTHORITY_SOURCE_ID,
                            "role": "NORMATIVE",
                            "path": "GOVERNANCE.md",
                            "locator": "\u00a7\u00a72",
                        }
                    ],
                }
            },
            "fixture_manifest_raw_sha256": raw_sha256(self.manifest_bytes),
            "entries": [
                {
                    "case_id": CASE_ID,
                    "proposed_disposition": "PRESERVE",
                    "authority_refs": [
                        {
                            "source_id": AUTHORITY_SOURCE_ID,
                            "role": "NORMATIVE",
                            "path": "GOVERNANCE.md",
                            "locator": "\u00a7\u00a72",
                        }
                    ],
                    "actual_review_classes": None,
                    "semantic_expectation": {
                        "evaluation_context": {
                            "evaluation_kind": "ADOPTER_SNAPSHOT"
                        },
                        "selected_semantic_result": "SATISFIED",
                        "required_satisfied_condition_keys": [CONDITION_KEY],
                        "finding_set": {"closed": True, "exact": []},
                    },
                }
            ],
        }
        if self.ledger_mutator is not None:
            self.ledger_mutator(self.ledger)
        self.ledger_bytes = json_bytes(self.ledger)
        self.write_bytes(LEDGER_PATH, self.ledger_bytes)
        self.candidate_head = self.commit_all("candidate Phase 0 bytes")

        self.git("checkout", "main")
        self.git(
            "-c",
            "commit.gpgsign=false",
            "merge",
            "--no-ff",
            "candidate",
            "-m",
            "merge candidate Phase 0 bytes",
        )
        self.candidate_merge = self.rev_parse()

        self.decision = {
            "document_kind": "phase0_oracle_decision",
            "format_version": 1,
            "decision_id": DECISION_ID,
            "decision": "ACCEPT_SEMANTIC_LEDGER_REVISION",
            "ledger_revision": LEDGER_REVISION,
            "ledger_shape_revision": LEDGER_SHAPE_REVISION,
            "scope": {
                "coverage": copy.deepcopy(self.coverage),
                "case_ids": [CASE_ID],
            },
            "candidate": {
                "repository": EXPECTED_REPOSITORY,
                "repository_commit_sha1": self.candidate_merge,
                "manifest": {
                    "path": MANIFEST_PATH,
                    "raw_sha256": raw_sha256(self.manifest_bytes),
                },
                "ledger": {
                    "path": LEDGER_PATH,
                    "raw_sha256": raw_sha256(self.ledger_bytes),
                },
                "corpus_sha256": self.corpus_digest,
            },
            "decision_authority_revision": {
                "repository": EXPECTED_REPOSITORY,
                "commit_sha1": self.candidate_merge,
                "path": GOVERNANCE_PATH,
                "locator": "§§1–2",
                "raw_sha256": raw_sha256(self.governance_bytes),
            },
            "reference_release_decision": {
                "repository": EXPECTED_REPOSITORY,
                "release": "v0.4.0-test",
                "annotated_tag_object_sha1": self.reference_tag_object,
                "commit_sha1": self.initial_commit,
                "release_pr_url": "https://example.invalid/pull/0",
                "pull_request_workflow_run_id": 1,
                "recorded_review_classes": {
                    "human": "SOLE_OWNER_ATTESTED",
                    "automation": "AUTOMATION_VERIFIED",
                },
            },
            "parity_projection": None,
            "implementation_parity_authorized": False,
            "decision_record": {
                "pr_url": "https://example.invalid/pull/1",
                "governing_body": "Synthetic maintainers",
                "decision_maker": "Fixture Owner",
                "human_review_class": "SOLE_OWNER_ATTESTED",
                "automation_review_class": "AUTOMATION_VERIFIED",
            },
            "supersedes_decision_id": None,
            "successor_change": None,
            "compatibility_impact": "none",
        }
        if self.decision_mutator is not None:
            self.decision_mutator(self.decision)

        self.git("checkout", "-b", "acceptance")
        decision_text = json_bytes(self.decision).decode("utf-8")
        if self.decision_text_mutator is not None:
            decision_text = self.decision_text_mutator(decision_text)
        self.write_text(DECISION_PATH, decision_text)
        if self.acceptance_extra_file:
            self.write_text("unexpected-acceptance-change.txt", "not allowed\n")
        self.acceptance_head = self.commit_all("accept Phase 0 decision")

        if self.merge_acceptance:
            self.git("checkout", "main")
            self.git(
                "-c",
                "commit.gpgsign=false",
                "merge",
                "--no-ff",
                "acceptance",
                "-m",
                "merge acceptance-only decision",
            )
            self.decision_commit = self.rev_parse()
        else:
            self.decision_commit = self.acceptance_head

        self.write_text("consumer.txt", "consumer base\n")
        self.consumer_base = self.commit_all("consumer commit")

    def modify_accepted_record(self) -> str:
        changed = copy.deepcopy(self.decision)
        changed["compatibility_impact"] = "edited in place after acceptance"
        self.write_json(DECISION_PATH, changed)
        self.consumer_base = self.commit_all("improperly modify accepted record")
        return self.consumer_base

    def modify_then_restore_accepted_record(self) -> str:
        changed = copy.deepcopy(self.decision)
        changed["compatibility_impact"] = "temporarily edited after acceptance"
        self.write_json(DECISION_PATH, changed)
        self.commit_all("temporarily modify accepted record")
        self.write_json(DECISION_PATH, self.decision)
        self.consumer_base = self.commit_all("restore accepted record bytes")
        return self.consumer_base

    def delete_then_restore_accepted_record(self) -> str:
        (self.root / DECISION_PATH).unlink()
        self.commit_all("temporarily delete accepted record")
        self.write_json(DECISION_PATH, self.decision)
        self.consumer_base = self.commit_all("restore deleted record bytes")
        return self.consumer_base

    def add_duplicate_decision_id(self) -> str:
        duplicate_path = (
            "docs/evidence/v0.5/oracle-decisions/duplicate-decision.json"
        )
        self.write_json(duplicate_path, self.decision)
        self.consumer_base = self.commit_all("add duplicate decision ID")
        return self.consumer_base

    def decision_rebound_to(self, acceptance_base: str) -> dict:
        rebound = copy.deepcopy(self.decision)
        rebound["decision_authority_revision"]["commit_sha1"] = acceptance_base
        return rebound

    def delete_and_reaccept_decision(self) -> str:
        (self.root / DECISION_PATH).unlink()
        self.reacceptance_base = self.commit_all("delete accepted decision record")

        self.git("checkout", "-b", "reaccept-deleted-decision")
        self.write_json(
            DECISION_PATH,
            self.decision_rebound_to(self.reacceptance_base),
        )
        self.commit_all("reintroduce deleted decision record")

        self.git("checkout", "main")
        self.git(
            "-c",
            "commit.gpgsign=false",
            "merge",
            "--no-ff",
            "reaccept-deleted-decision",
            "-m",
            "merge reintroduced decision record",
        )
        self.decision_commit = self.rev_parse()
        self.write_text("consumer.txt", "consumer after reacceptance\n")
        self.consumer_base = self.commit_all("consumer after reacceptance")
        return self.consumer_base

    def reuse_decision_id_at_new_path(self) -> str:
        (self.root / DECISION_PATH).unlink()
        reuse_base = self.commit_all("delete original decision path")

        self.git("checkout", "-b", "reuse-decision-id")
        self.write_json(
            REUSED_DECISION_PATH,
            self.decision_rebound_to(reuse_base),
        )
        self.commit_all("reuse stable decision ID at a new path")

        self.git("checkout", "main")
        self.git(
            "-c",
            "commit.gpgsign=false",
            "merge",
            "--no-ff",
            "reuse-decision-id",
            "-m",
            "merge reused decision ID",
        )
        self.decision_commit = self.rev_parse()
        self.write_text("consumer.txt", "consumer after ID reuse\n")
        self.consumer_base = self.commit_all("consumer after ID reuse")
        return self.consumer_base

    def reuse_decision_id_after_type_change_round_trip(self) -> str:
        original = self.root / DECISION_PATH
        original.unlink()
        original.symlink_to("non-authoritative-symlink-target")
        self.commit_all("replace accepted decision blob with symlink")

        original.unlink()
        replacement = copy.deepcopy(self.decision)
        replacement["decision_id"] = "AAP-V05-P0-ORACLE-OTHER-002"
        self.write_json(DECISION_PATH, replacement)
        reuse_base = self.commit_all("replace symlink with a different decision")

        self.git("checkout", "-b", "reuse-id-after-type-change")
        self.write_json(
            REUSED_DECISION_PATH,
            self.decision_rebound_to(reuse_base),
        )
        self.commit_all("reuse decision ID after type-change round trip")

        self.git("checkout", "main")
        self.git(
            "-c",
            "commit.gpgsign=false",
            "merge",
            "--no-ff",
            "reuse-id-after-type-change",
            "-m",
            "merge reused ID after type change",
        )
        self.decision_commit = self.rev_parse()
        self.write_text("consumer.txt", "consumer after type-change reuse\n")
        self.consumer_base = self.commit_all("consumer after type-change reuse")
        return self.consumer_base

    def install_graft_that_skips_original_acceptance(self) -> None:
        grafts = self.root / ".git" / "info" / "grafts"
        grafts.parent.mkdir(parents=True, exist_ok=True)
        grafts.write_text(
            f"{self.reacceptance_base} {self.candidate_merge}\n",
            encoding="ascii",
        )

    def mark_repository_shallow(self) -> None:
        (self.root / ".git" / "shallow").write_text(
            self.initial_commit + "\n", encoding="ascii"
        )


class TestPhase0AcceptanceVerifier(unittest.TestCase):
    maxDiff = None

    def run_verifier(
        self,
        repository: SyntheticAcceptanceRepository,
        *,
        consumer_base: Optional[str] = None,
        decision_commit: Optional[str] = None,
        decision_id: str = DECISION_ID,
        decision_path: str = DECISION_PATH,
        repo_root: Optional[Path] = None,
        extra_env: Optional[dict[str, str]] = None,
    ) -> subprocess.CompletedProcess[str]:
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "GIT_CONFIG_NOSYSTEM": "1",
        }
        if extra_env is not None:
            env.update(extra_env)
        return subprocess.run(
            [
                sys.executable,
                str(VERIFIER),
                "--repo-root",
                str(repo_root or repository.root),
                "--expected-repository",
                EXPECTED_REPOSITORY,
                "--consumer-base",
                consumer_base or repository.consumer_base,
                "--decision-commit",
                decision_commit or repository.decision_commit,
                "--decision-id",
                decision_id,
                "--decision-path",
                decision_path,
                "--format",
                "json",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
            env=env,
        )

    def parse_payload(self, completed: subprocess.CompletedProcess[str]) -> dict:
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as error:
            self.fail(
                f"verifier did not emit JSON: {error}\n"
                f"return code: {completed.returncode}\n"
                f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
            )
        self.assertEqual(
            payload.get("document_kind"),
            "phase0_acceptance_binding_verification",
        )
        self.assertEqual(payload.get("format_version"), 1)
        self.assertIs(payload.get("public_contract"), False)
        self.assertNotIn("Traceback", completed.stdout + completed.stderr)
        return payload

    def assert_rejected(
        self, completed: subprocess.CompletedProcess[str]
    ) -> dict:
        payload = self.parse_payload(completed)
        self.assertEqual(
            completed.returncode,
            1,
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
        )
        self.assertEqual(payload.get("offline_binding"), "REJECTED")
        self.assertEqual(payload.get("effective_acceptance"), "NOT_ESTABLISHED")
        self.assertIsInstance(payload.get("error"), str)
        self.assertTrue(payload["error"].strip())
        return payload

    def assert_append_only_rejected(
        self, completed: subprocess.CompletedProcess[str]
    ) -> dict:
        payload = self.assert_rejected(completed)
        self.assertEqual(
            payload.get("error"),
            "canonical decision JSON history is not append-only",
        )
        return payload

    def test_valid_offline_binding_is_verified_but_not_effective_acceptance(
        self,
    ) -> None:
        with SyntheticAcceptanceRepository() as repository:
            before = repository.status_bytes()
            completed = self.run_verifier(repository)
            after = repository.status_bytes()

            payload = self.parse_payload(completed)
            self.assertEqual(
                completed.returncode,
                0,
                f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
            )
            self.assertEqual(payload.get("offline_binding"), "VERIFIED")
            self.assertEqual(
                payload.get("effective_acceptance"), "NOT_ESTABLISHED"
            )
            self.assertIs(payload.get("implementation_parity_authorized"), False)
            self.assertEqual(payload.get("decision_id"), DECISION_ID)
            self.assertEqual(
                payload.get("consumer_base_sha1"), repository.consumer_base
            )
            self.assertEqual(
                payload.get("decision_commit_sha1"), repository.decision_commit
            )
            self.assertEqual(
                payload.get("candidate_commit_sha1"), repository.candidate_merge
            )
            self.assertIsInstance(payload.get("verified"), list)
            self.assertEqual(
                payload.get("unverified_external_predicates"),
                [
                    "protected-canonical-main",
                    "github-acceptance-pr-state",
                    "factual-human-decision-maker",
                    "factual-review-classes",
                ],
            )
            self.assertEqual(
                payload.get("unverified_preconditions"),
                [
                    "verifier-executable-provenance",
                    "git-executable-provenance",
                    "local-repository-origin",
                    "expected-repository-argument-authority",
                ],
            )
            self.assertEqual(
                payload.get("unverified_authority_predicates"),
                [
                    "semantic-authority-reference-validity",
                    "published-release-tag-state",
                    "github-release-pr-state",
                    "github-release-workflow-run-state",
                ],
            )
            observations = payload.get("local_observations")
            self.assertIsInstance(observations, dict)
            self.assertEqual(
                observations.get("verifier_executable_path"),
                str(VERIFIER.resolve()),
            )
            self.assertEqual(
                observations.get("repository_root"),
                str(repository.root.resolve()),
            )
            self.assertTrue(Path(observations["git_executable_path"]).is_absolute())
            self.assertRegex(observations.get("git_version", ""), r"^git version ")
            self.assertEqual(before, after)

    def test_current_manifest_ledger_and_local_corpus_are_component_compatible(
        self,
    ) -> None:
        artifact_scope = "tests/characterization/v0.4.0"
        manifest_bytes = committed_file_bytes(f"{artifact_scope}/manifest.json")
        ledger_bytes = committed_file_bytes(
            f"{artifact_scope}/expected-outcomes.json"
        )
        strict_json = VERIFIER_NAMESPACE["strict_json"]
        verify_ledger = VERIFIER_NAMESPACE["verify_ledger"]
        manifest = strict_json(manifest_bytes, "current committed manifest")
        ledger = strict_json(ledger_bytes, "current committed ledger")

        self.assertEqual(
            manifest.get("document_kind"), "phase0_fixture_manifest_scaffold"
        )
        self.assertEqual(manifest.get("status"), "PROPOSED_NOT_ACCEPTED")
        self.assertIs(manifest.get("public_contract"), False)
        self.assertIs(manifest.get("coverage_complete"), False)
        self.assertEqual(
            manifest.get("digest", {}).get("algorithm"),
            "sha256-over-canonical-root-records-described-in-README",
        )
        reference = manifest.get("reference")
        self.assertIsInstance(reference, dict)
        self.assertIsInstance(reference.get("release"), str)
        for field in (
            "annotated_tag_object_sha1",
            "peeled_commit_sha1",
            "validator_git_blob_sha1",
            "requirements_git_blob_sha1",
        ):
            self.assertRegex(reference.get(field, ""), r"^[0-9a-f]{40}$")
        root_records = manifest.get("root_records")
        self.assertIsInstance(root_records, list)
        self.assertTrue(root_records)
        actual_digest_records: list[dict[str, str]] = []
        source_kind_counts = {"corpus_directory": 0, "git_commit": 0}
        root_ids: set[str] = set()
        for record in root_records:
            self.assertIsInstance(record, dict)
            root_id = record.get("root_id")
            self.assertIsInstance(root_id, str)
            self.assertTrue(root_id)
            root_id.encode("ascii")
            self.assertNotIn(root_id, root_ids)
            root_ids.add(root_id)
            self.assertIs(type(record.get("file_count")), int)
            self.assertGreaterEqual(record["file_count"], 1)
            self.assertIs(type(record.get("byte_count")), int)
            self.assertGreaterEqual(record["byte_count"], 1)
            self.assertRegex(record.get("tree_sha256", ""), r"^[0-9a-f]{64}$")
            source = record.get("source")
            self.assertIsInstance(source, dict)
            source_kind = source.get("kind")
            self.assertIn(source_kind, source_kind_counts)
            source_kind_counts[source_kind] += 1
            if source_kind == "corpus_directory":
                actual = committed_directory_tree_record(
                    f"{artifact_scope}/{source['path']}",
                    root_id,
                    source["path"],
                )
                self.assertEqual(actual, record)
                tree_sha256 = actual["tree_sha256"]
            else:
                self.assertEqual(source.get("scope"), ".")
                self.assertRegex(source.get("commit_sha1", ""), r"^[0-9a-f]{40}$")
                self.assertRegex(source.get("git_tree_sha1", ""), r"^[0-9a-f]{40}$")
                self.assertRegex(record.get("tree_sha256", ""), r"^[0-9a-f]{64}$")
                tree_sha256 = record["tree_sha256"]
            actual_digest_records.append(
                {"root_id": root_id, "tree_sha256": tree_sha256}
            )

        self.assertEqual(
            source_kind_counts,
            {"corpus_directory": 6, "git_commit": 1},
        )
        self.assertEqual(
            corpus_sha256(actual_digest_records),
            manifest["digest"]["corpus_sha256"],
        )
        cases = manifest.get("cases")
        self.assertIsInstance(cases, list)
        self.assertTrue(cases)
        manifest_case_ids: set[str] = set()
        for case in cases:
            self.assertIsInstance(case, dict)
            case_id = case.get("case_id")
            self.assertIsInstance(case_id, str)
            self.assertTrue(case_id)
            case_id.encode("ascii")
            self.assertNotIn(case_id, manifest_case_ids)
            manifest_case_ids.add(case_id)
            self.assertIn(case.get("input_root_id"), root_ids)
        ledger_case_ids, coverage = verify_ledger(
            ledger,
            raw_sha256(manifest_bytes),
            manifest_case_ids,
        )
        self.assertEqual(ledger_case_ids, manifest_case_ids)
        self.assertEqual(coverage, ledger["coverage"])

    def test_caller_git_environment_redirections_are_ignored(self) -> None:
        with SyntheticAcceptanceRepository() as repository:
            poison = repository.root / "caller-controlled-git-state"
            poison.mkdir()
            poison_config = poison / "config"
            poison_config.write_text("[broken\n", encoding="utf-8")

            completed = self.run_verifier(
                repository,
                extra_env={
                    "GIT_DIR": str(poison / "git-dir"),
                    "GIT_WORK_TREE": str(poison / "work-tree"),
                    "GIT_COMMON_DIR": str(poison / "common-dir"),
                    "GIT_OBJECT_DIRECTORY": str(poison / "objects"),
                    "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(
                        poison / "alternate-objects"
                    ),
                    "GIT_INDEX_FILE": str(poison / "index"),
                    "GIT_GRAFT_FILE": str(poison / "grafts"),
                    "GIT_SHALLOW_FILE": str(poison / "shallow"),
                    "GIT_NAMESPACE": "caller-controlled",
                    "GIT_CONFIG_GLOBAL": str(poison_config),
                    "GIT_CONFIG_SYSTEM": str(poison_config),
                    "GIT_CONFIG_COUNT": "1",
                    "GIT_CONFIG_KEY_0": "core.repositoryformatversion",
                    "GIT_CONFIG_VALUE_0": "999",
                },
            )

            payload = self.parse_payload(completed)
            self.assertEqual(completed.returncode, 0, payload)
            self.assertEqual(payload.get("offline_binding"), "VERIFIED")

    def test_every_git_call_disables_lazy_fetch_and_local_grafts(self) -> None:
        real_git = shutil.which("git")
        self.assertIsNotNone(real_git)
        with SyntheticAcceptanceRepository() as repository:
            with tempfile.TemporaryDirectory(
                prefix="phase0-git-wrapper-"
            ) as wrapper_directory:
                wrapper = Path(wrapper_directory) / "git"
                wrapper.write_text(
                    "#!/bin/sh\n"
                    'if [ "${GIT_NO_LAZY_FETCH-}" != "1" ]; then\n'
                    '  echo "GIT_NO_LAZY_FETCH=1 was not forced" >&2\n'
                    "  exit 97\n"
                    "fi\n"
                    f'if [ "${{GIT_GRAFT_FILE-}}" != {shlex.quote(os.devnull)} ]; then\n'
                    '  echo "GIT_GRAFT_FILE was not neutralized" >&2\n'
                    "  exit 98\n"
                    "fi\n"
                    f"exec {shlex.quote(real_git or '')} \"$@\"\n",
                    encoding="utf-8",
                )
                wrapper.chmod(0o755)
                expected_wrapper_path = str(wrapper.resolve())
                completed = self.run_verifier(
                    repository,
                    extra_env={
                        "PATH": (
                            wrapper_directory
                            + os.pathsep
                            + os.environ.get("PATH", "")
                        ),
                        "GIT_NO_LAZY_FETCH": "0",
                    },
                )

            payload = self.parse_payload(completed)
            self.assertEqual(completed.returncode, 0, payload)
            self.assertEqual(payload.get("offline_binding"), "VERIFIED")
            self.assertEqual(
                payload["local_observations"]["git_executable_path"],
                expected_wrapper_path,
            )

    def test_nested_repo_root_is_rejected(self) -> None:
        with SyntheticAcceptanceRepository() as repository:
            nested = repository.root / "nested" / "directory"
            nested.mkdir(parents=True)
            completed = self.run_verifier(repository, repo_root=nested)
            payload = self.assert_rejected(completed)
            self.assertEqual(
                payload.get("error"),
                "--repo-root must exactly name the non-bare repository top-level",
            )

    def test_decision_cannot_self_declare_acceptance(self) -> None:
        mutations = {
            "accepted boolean": lambda value: value.__setitem__(
                "accepted", True
            ),
            "accepted status": lambda value: value.__setitem__(
                "status", "ACCEPTED"
            ),
        }
        for label, mutation in mutations.items():
            with self.subTest(self_authorization=label):
                with SyntheticAcceptanceRepository(
                    decision_mutator=mutation
                ) as repository:
                    completed = self.run_verifier(repository)
                    self.assert_rejected(completed)

    def test_executable_corpus_entry_is_rejected(self) -> None:
        with SyntheticAcceptanceRepository(
            executable_corpus_entry=True
        ) as repository:
            completed = self.run_verifier(repository)
            self.assert_rejected(completed)

    def test_duplicate_decision_id_on_consumer_base_is_rejected(self) -> None:
        with SyntheticAcceptanceRepository() as repository:
            repository.add_duplicate_decision_id()
            completed = self.run_verifier(repository)
            self.assert_rejected(completed)

    def test_head_only_decision_is_rejected(self) -> None:
        with SyntheticAcceptanceRepository(merge_acceptance=False) as repository:
            completed = self.run_verifier(repository)
            self.assert_rejected(completed)

    def test_consumer_base_must_follow_decision_commit(self) -> None:
        with SyntheticAcceptanceRepository() as repository:
            completed = self.run_verifier(
                repository, consumer_base=repository.candidate_merge
            )
            self.assert_rejected(completed)

    def test_accepted_record_modified_later_is_rejected(self) -> None:
        with SyntheticAcceptanceRepository() as repository:
            repository.modify_accepted_record()
            completed = self.run_verifier(repository)
            self.assert_rejected(completed)

    def test_accepted_record_change_cannot_be_hidden_by_restoring_bytes(
        self,
    ) -> None:
        for label, mutation in (
            ("edit and restore", lambda repo: repo.modify_then_restore_accepted_record()),
            ("delete and restore", lambda repo: repo.delete_then_restore_accepted_record()),
        ):
            with self.subTest(history_change=label):
                with SyntheticAcceptanceRepository() as repository:
                    mutation(repository)
                    completed = self.run_verifier(repository)
                    self.assert_append_only_rejected(completed)

    def test_deleted_decision_path_cannot_be_reaccepted_as_new(self) -> None:
        with SyntheticAcceptanceRepository() as repository:
            repository.delete_and_reaccept_decision()
            completed = self.run_verifier(repository)
            self.assert_append_only_rejected(completed)

    def test_decision_id_cannot_be_reused_at_a_new_path(self) -> None:
        with SyntheticAcceptanceRepository() as repository:
            repository.reuse_decision_id_at_new_path()
            completed = self.run_verifier(
                repository,
                decision_path=REUSED_DECISION_PATH,
            )
            self.assert_append_only_rejected(completed)

    def test_type_change_round_trip_cannot_hide_decision_id_reuse(self) -> None:
        with SyntheticAcceptanceRepository() as repository:
            repository.reuse_decision_id_after_type_change_round_trip()
            completed = self.run_verifier(
                repository,
                decision_path=REUSED_DECISION_PATH,
            )
            self.assert_append_only_rejected(completed)

    def test_repository_local_graft_cannot_hide_decision_history(self) -> None:
        with SyntheticAcceptanceRepository() as repository:
            repository.delete_and_reaccept_decision()
            repository.install_graft_that_skips_original_acceptance()
            completed = self.run_verifier(repository)
            self.assert_append_only_rejected(completed)

    def test_acceptance_merge_with_extra_file_is_rejected(self) -> None:
        with SyntheticAcceptanceRepository(
            acceptance_extra_file=True
        ) as repository:
            completed = self.run_verifier(repository)
            self.assert_rejected(completed)

    def test_bound_hash_revision_and_governance_mismatches_are_rejected(
        self,
    ) -> None:
        mutations = {
            "manifest raw hash": lambda value: value["candidate"]["manifest"].__setitem__(
                "raw_sha256", "0" * 64
            ),
            "ledger raw hash": lambda value: value["candidate"]["ledger"].__setitem__(
                "raw_sha256", "1" * 64
            ),
            "corpus digest": lambda value: value["candidate"].__setitem__(
                "corpus_sha256", "2" * 64
            ),
            "ledger revision": lambda value: value.__setitem__(
                "ledger_revision", "wrong-ledger-revision"
            ),
            "governance raw hash": lambda value: value[
                "decision_authority_revision"
            ].__setitem__("raw_sha256", "3" * 64),
        }
        for label, mutation in mutations.items():
            with self.subTest(mismatch=label):
                with SyntheticAcceptanceRepository(
                    decision_mutator=mutation
                ) as repository:
                    completed = self.run_verifier(repository)
                    self.assert_rejected(completed)

    def test_duplicate_json_key_is_rejected(self) -> None:
        def duplicate_decision_id(text: str) -> str:
            needle = f'  "decision_id": "{DECISION_ID}",\n'
            self.assertIn(needle, text)
            return text.replace(needle, needle + needle, 1)

        with SyntheticAcceptanceRepository(
            decision_text_mutator=duplicate_decision_id
        ) as repository:
            completed = self.run_verifier(repository)
            self.assert_rejected(completed)

    def test_condition_catalog_must_close_over_semantic_expectations(self) -> None:
        def remove_catalog_entry(value: dict) -> None:
            value["condition_catalog"] = {}

        with SyntheticAcceptanceRepository(
            ledger_mutator=remove_catalog_entry
        ) as repository:
            completed = self.run_verifier(repository)
            self.assert_rejected(completed)

    def test_parity_authorization_and_successor_records_are_rejected(self) -> None:
        def authorize_parity(value: dict) -> None:
            value["implementation_parity_authorized"] = True

        def make_successor(value: dict) -> None:
            value["supersedes_decision_id"] = "AAP-V05-P0-ORACLE-OLDER"
            value["successor_change"] = {
                "affected_case_ids": [CASE_ID],
                "old_expected_outcomes": {CASE_ID: "SATISFIED"},
                "new_expected_outcomes": {CASE_ID: "BLOCKED"},
                "authority_refs": ["synthetic-authority"],
                "rationale": "synthetic successor",
                "compatibility_impact": "synthetic",
            }

        for label, mutation in (
            ("implementation parity", authorize_parity),
            ("successor", make_successor),
        ):
            with self.subTest(disallowed=label):
                with SyntheticAcceptanceRepository(
                    decision_mutator=mutation
                ) as repository:
                    completed = self.run_verifier(repository)
                    self.assert_rejected(completed)

    def test_missing_git_object_is_a_controlled_json_error(self) -> None:
        with SyntheticAcceptanceRepository() as repository:
            completed = self.run_verifier(
                repository, decision_commit="f" * 40
            )
            payload = self.assert_rejected(completed)
            self.assertNotIn("Traceback", payload["error"])

    def test_shallow_repository_is_rejected_before_history_verification(self) -> None:
        with SyntheticAcceptanceRepository() as repository:
            repository.mark_repository_shallow()
            completed = self.run_verifier(repository)
            self.assert_rejected(completed)

    def test_dirty_worktree_status_and_contents_are_unchanged(self) -> None:
        with SyntheticAcceptanceRepository() as repository:
            consumer = repository.root / "consumer.txt"
            consumer.write_text("dirty consumer worktree\n", encoding="utf-8")
            sentinel = repository.root / "untracked-sentinel.txt"
            sentinel.write_text("do not touch\n", encoding="utf-8")
            before_status = repository.status_bytes()
            before_consumer = consumer.read_bytes()
            before_sentinel = sentinel.read_bytes()

            completed = self.run_verifier(repository)
            payload = self.parse_payload(completed)

            self.assertEqual(completed.returncode, 0, payload)
            self.assertEqual(payload.get("offline_binding"), "VERIFIED")
            self.assertEqual(repository.status_bytes(), before_status)
            self.assertEqual(consumer.read_bytes(), before_consumer)
            self.assertEqual(sentinel.read_bytes(), before_sentinel)


if __name__ == "__main__":
    unittest.main()
