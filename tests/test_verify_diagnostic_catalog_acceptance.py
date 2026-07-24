"""Black-box tests for the internal diagnostic acceptance verifier."""

from __future__ import annotations

import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from typing import Callable, Optional


REPO_ROOT = Path(__file__).resolve().parent.parent
VERIFIER = REPO_ROOT / "scripts" / "verify_diagnostic_catalog_acceptance.py"
CANDIDATE_VERIFIER = (
    REPO_ROOT / "scripts" / "verify_diagnostic_catalog_candidate.py"
)
CONTRACT_README = (
    REPO_ROOT
    / "docs/evidence/v0.5/diagnostic-catalog/decisions/README.md"
)
ACCEPTANCE_TESTS = Path(__file__).resolve()
BASE_COMMIT = "2a08ed7d0edbd0c9463513150d78017f2207f97f"
EXPECTED_REPOSITORY = "MosslandOpenDevs/agentic-assurance-profile"
VERIFIER_CONTRACT_ID = (
    "AAP-V05-DIAGNOSTIC-CATALOG-ACCEPTANCE-OFFLINE-V1"
)
CONTRACT_README_SHA256 = (
    "db9bd46edf3d182ea5b6d379d8605d83c14e618f210a0486550a665e608e2208"
)
RECORD_ID = "AAP-V05-DIAGNOSTICS-ACCEPTANCE-001"
SUBJECT_DECISION_ID = "AAP-V05-DIAGNOSTICS-001"
DECISION_PATH = (
    "docs/evidence/v0.5/diagnostic-catalog/decisions/"
    "diagnostic-catalog-acceptance-r1.json"
)
DUPLICATE_PATH = (
    "docs/evidence/v0.5/diagnostic-catalog/decisions/"
    "duplicate-acceptance-r1.json"
)


def json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


class AcceptanceRepository:
    """Build an exact acceptance-only merge over the immutable PR #66 merge."""

    def __init__(
        self,
        *,
        record_mutator: Optional[Callable[[dict], None]] = None,
        record_text_mutator: Optional[Callable[[str], str]] = None,
        extra_file: bool = False,
        merge_acceptance: bool = True,
        merge_contract: bool = True,
        contract_verifier_suffix: bytes = b"",
    ) -> None:
        self._temporary = tempfile.TemporaryDirectory(
            prefix="diagnostic-acceptance-verifier-test-"
        )
        self.root = Path(self._temporary.name) / "repository"
        self.record_mutator = record_mutator
        self.record_text_mutator = record_text_mutator
        self.extra_file = extra_file
        self.merge_acceptance = merge_acceptance
        self.merge_contract = merge_contract
        self.contract_verifier_suffix = contract_verifier_suffix
        self._build()

    def __enter__(self) -> "AcceptanceRepository":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self._temporary.cleanup()

    def git(
        self,
        *args: str,
        check: bool = True,
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
                "GIT_AUTHOR_NAME": "Acceptance Test",
                "GIT_AUTHOR_EMAIL": "acceptance-test@example.invalid",
                "GIT_COMMITTER_NAME": "Acceptance Test",
                "GIT_COMMITTER_EMAIL": "acceptance-test@example.invalid",
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

    def write_text(self, relative: str, value: str) -> None:
        self.write_bytes(relative, value.encode("utf-8"))

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

    def _contract_artifacts(self) -> list[dict[str, str]]:
        definitions = [
            (
                "CONTRACT",
                "docs/evidence/v0.5/diagnostic-catalog/decisions/README.md",
                CONTRACT_README,
            ),
            (
                "ACCEPTANCE_VERIFIER",
                "scripts/verify_diagnostic_catalog_acceptance.py",
                VERIFIER,
            ),
            (
                "CANDIDATE_SEMANTIC_VERIFIER",
                "scripts/verify_diagnostic_catalog_candidate.py",
                CANDIDATE_VERIFIER,
            ),
            (
                "ACCEPTANCE_VERIFIER_TESTS",
                "tests/test_verify_diagnostic_catalog_acceptance.py",
                ACCEPTANCE_TESTS,
            ),
        ]
        result: list[dict[str, str]] = []
        for role, path, source in definitions:
            raw_sha256 = hashlib.sha256(
                self._contract_artifact_bytes(role, source)
            ).hexdigest()
            if role == "CONTRACT":
                raw_sha256 = CONTRACT_README_SHA256
            result.append(
                {
                    "role": role,
                    "path": path,
                    "raw_sha256": raw_sha256,
                }
            )
        return result

    def _contract_artifact_bytes(self, role: str, source: Path) -> bytes:
        data = source.read_bytes()
        if role == "ACCEPTANCE_VERIFIER":
            data += self.contract_verifier_suffix
        return data

    def _record(
        self,
        acceptance_base: str,
        verifier_contract_merge: str,
    ) -> dict:
        return {
            "document_kind": "diagnostic_catalog_acceptance_decision",
            "internal_format_version": 1,
            "record_id": RECORD_ID,
            "subject_decision_id": SUBJECT_DECISION_ID,
            "decision": "ACCEPT_FOUNDATION_DIAGNOSTIC_BASELINE",
            "verifier_contract": {
                "contract_id": VERIFIER_CONTRACT_ID,
                "repository": EXPECTED_REPOSITORY,
                "canonical_merge_commit_sha1": verifier_contract_merge,
                "artifacts": self._contract_artifacts(),
            },
            "subject": {
                "repository": EXPECTED_REPOSITORY,
                "candidate_canonical_merge_sha1": (
                    "c51b8c1cc7cb5fd343a4acf65e0cccc38356a4fe"
                ),
                "candidate_head_sha1": (
                    "f4c8f82e7d0bdfe7edd9a364d2e75a4d7af7ec67"
                ),
                "catalog": {
                    "path": (
                        "docs/evidence/v0.5/diagnostic-catalog/catalog-r1.json"
                    ),
                    "raw_sha256": (
                        "da541828f462784eeb504af1436e6c689dc7f429814a18c729e2dc48362a0cec"
                    ),
                    "catalog_id": (
                        "urn:uuid:6d6187ea-521e-4f3e-98d9-cb716877a84b"
                    ),
                    "catalog_revision": 1,
                },
                "legacy_mapping": {
                    "path": (
                        "docs/evidence/v0.5/diagnostic-catalog/"
                        "legacy-v0.4.0-mapping-r1.json"
                    ),
                    "raw_sha256": (
                        "281803836ca4034a3cf441c46b6e608434dea9245e5fa18c90e2954deac79100"
                    ),
                    "mapping_revision": 1,
                },
                "compatibility_changes": {
                    "path": (
                        "docs/evidence/v0.5/diagnostic-catalog/"
                        "compatibility-changes-r1.json"
                    ),
                    "raw_sha256": (
                        "499a7a571502d0d70289d00f2bf655673da36c73c82bfb9df4c25913b9be0f7b"
                    ),
                },
                "normalized_inventory": {
                    "path": (
                        "docs/evidence/v0.5/diagnostic-catalog/"
                        "normalized-inventory-r1.json"
                    ),
                    "raw_sha256": (
                        "aa3b9a5d30e41b2e78cb9e45c736ec697ccb04393ab6c300b82ce0e796cbc305"
                    ),
                    "role": "BOUND_REVIEW_EVIDENCE",
                },
            },
            "scope": {
                "accepted_baseline_components": [
                    "DIAGNOSTIC_IDENTITY_ALLOCATION",
                    "V0_4_SEMANTIC_MAPPING",
                    "COMPATIBILITY_CHANGE_INTENT",
                ],
                "bound_review_evidence": ["NORMALIZED_SOURCE_INVENTORY"],
                "implementation_parity_authorized": False,
                "runtime_consumption_authorized": False,
                "runtime_ready": False,
                "public_contract": False,
            },
            "authority_basis": {
                "governance": {
                    "repository": EXPECTED_REPOSITORY,
                    "commit_sha1": acceptance_base,
                    "path": "GOVERNANCE.md",
                    "locator": "§§1–3",
                    "raw_sha256": (
                        "5bc92e111440f117d4b7c1a801688889d6767217fcafdd4bdf9d0e333d9798a6"
                    ),
                },
                "accepted_adrs": [
                    {
                        "adr_id": "0002",
                        "repository": EXPECTED_REPOSITORY,
                        "acceptance_merge_commit_sha1": (
                            "a34f074ab57214d5fe924ba90c00df313cc2acb6"
                        ),
                        "path": (
                            "docs/adr/v0.5/0002-diagnostic-identities.md"
                        ),
                        "locator": "Decision",
                        "raw_sha256": (
                            "1ef92f7affec0e3031abcc7336fe68625db97e6931698e471b523ff44e8ff858"
                        ),
                    },
                    {
                        "adr_id": "0005",
                        "repository": EXPECTED_REPOSITORY,
                        "acceptance_merge_commit_sha1": (
                            "2a08ed7d0edbd0c9463513150d78017f2207f97f"
                        ),
                        "path": (
                            "docs/adr/v0.5/0005-human-review-authority.md"
                        ),
                        "locator": "Decision",
                        "raw_sha256": (
                            "688ad75c79ac0253f4b26685d2c96316e4f1c82be2647157f80f749bfec89564"
                        ),
                    },
                ],
            },
            "repository_process": {
                "pr_url": (
                    "https://github.com/MosslandOpenDevs/"
                    "agentic-assurance-profile/pull/999"
                ),
                "acceptance_base_commit_sha1": acceptance_base,
                "governing_body": "MosslandOpenDevs maintainers",
                "review_fact_source": "DURABLE_ACCEPTANCE_PR_RECORD",
            },
            "predecessor": None,
            "successor_change": None,
        }

    def _build(self) -> None:
        clone = subprocess.run(
            [
                "git",
                "clone",
                "--no-local",
                "--quiet",
                str(REPO_ROOT),
                str(self.root),
            ],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1"},
        )
        if clone.returncode != 0:
            raise AssertionError(
                f"local clone failed ({clone.returncode}): {clone.stderr}"
            )
        self.git("config", "user.name", "Acceptance Test")
        self.git("config", "user.email", "acceptance-test@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("checkout", "-B", "main", BASE_COMMIT)
        self.git("checkout", "-b", "verifier-contract")
        for artifact in self._contract_artifacts():
            source = REPO_ROOT / artifact["path"]
            self.write_bytes(
                artifact["path"],
                self._contract_artifact_bytes(artifact["role"], source),
            )
        self.commit_all("add catalog acceptance verifier contract")
        self.git("checkout", "main")
        if self.merge_contract:
            self.git(
                "-c",
                "commit.gpgsign=false",
                "merge",
                "--no-ff",
                "verifier-contract",
                "-m",
                "merge catalog acceptance verifier contract",
            )
        else:
            self.git("merge", "--squash", "verifier-contract")
            self.commit_all("squash catalog acceptance verifier contract")
        self.verifier_contract_merge = self.rev_parse()
        self.acceptance_base = self.rev_parse()
        self.record = self._record(
            self.acceptance_base,
            self.verifier_contract_merge,
        )
        if self.record_mutator is not None:
            self.record_mutator(self.record)

        self.git("checkout", "-b", "acceptance")
        record_text = json_bytes(self.record).decode("utf-8")
        if self.record_text_mutator is not None:
            record_text = self.record_text_mutator(record_text)
        self.write_text(DECISION_PATH, record_text)
        if self.extra_file:
            self.write_text("unexpected-acceptance-change.txt", "not allowed\n")
        self.acceptance_head = self.commit_all("add catalog acceptance record")

        if self.merge_acceptance:
            self.git("checkout", "main")
            self.git(
                "-c",
                "commit.gpgsign=false",
                "merge",
                "--no-ff",
                "acceptance",
                "-m",
                "merge catalog acceptance record",
            )
            self.decision_commit = self.rev_parse()
        else:
            self.decision_commit = self.acceptance_head

        self.write_text("consumer.txt", "consumer base\n")
        self.consumer_base = self.commit_all("consumer after acceptance")

    def modify_then_restore_record(self) -> None:
        changed = copy.deepcopy(self.record)
        changed["repository_process"]["governing_body"] = "Changed"
        self.write_json(DECISION_PATH, changed)
        self.commit_all("improperly modify accepted record")
        self.write_json(DECISION_PATH, self.record)
        self.consumer_base = self.commit_all("restore accepted record bytes")

    def merge_modify_then_restore_record(self) -> None:
        changed = copy.deepcopy(self.record)
        changed["repository_process"]["governing_body"] = "Changed"
        self.git("checkout", "-b", "modify-record")
        self.write_json(DECISION_PATH, changed)
        self.commit_all("improperly modify accepted record")
        self.git("checkout", "main")
        self.git(
            "-c",
            "commit.gpgsign=false",
            "merge",
            "--no-ff",
            "modify-record",
            "-m",
            "merge modified accepted record",
        )
        self.git("checkout", "-b", "restore-record")
        self.write_json(DECISION_PATH, self.record)
        self.commit_all("restore accepted record bytes")
        self.git("checkout", "main")
        self.git(
            "-c",
            "commit.gpgsign=false",
            "merge",
            "--no-ff",
            "restore-record",
            "-m",
            "merge restored accepted record",
        )
        self.consumer_base = self.rev_parse()

    def add_duplicate_record(self) -> None:
        duplicate = copy.deepcopy(self.record)
        duplicate["record_id"] = "AAP-V05-DIAGNOSTICS-ACCEPTANCE-OTHER"
        self.write_json(DUPLICATE_PATH, duplicate)
        self.consumer_base = self.commit_all("add competing subject record")

    def add_successor_record(self) -> None:
        successor = {
            "record_id": "AAP-V05-DIAGNOSTICS-ACCEPTANCE-002",
            "subject_decision_id": "AAP-V05-DIAGNOSTICS-002",
            "predecessor": {
                "record_id": RECORD_ID,
                "path": DECISION_PATH,
                "decision_merge_commit_sha1": self.decision_commit,
                "raw_sha256": hashlib.sha256(
                    json_bytes(self.record)
                ).hexdigest(),
            },
        }
        self.write_json(DUPLICATE_PATH, successor)
        self.consumer_base = self.commit_all("add successor decision record")

    def mark_shallow(self) -> None:
        (self.root / ".git" / "shallow").write_text(
            BASE_COMMIT + "\n",
            encoding="ascii",
        )


class DiagnosticCatalogAcceptanceVerifierTests(unittest.TestCase):
    maxDiff = 3000

    def run_verifier(
        self,
        repository: AcceptanceRepository,
        *,
        consumer_base: Optional[str] = None,
        decision_commit: Optional[str] = None,
        record_id: str = RECORD_ID,
        decision_path: str = DECISION_PATH,
        output_format: str = "json",
        extra_env: Optional[dict[str, str]] = None,
    ) -> subprocess.CompletedProcess[str]:
        environment = {
            **os.environ,
            "GIT_CONFIG_NOSYSTEM": "1",
        }
        environment.pop("PYTHONDONTWRITEBYTECODE", None)
        if extra_env:
            environment.update(extra_env)
        return subprocess.run(
            [
                sys.executable,
                str(VERIFIER),
                "--repo-root",
                str(repository.root),
                "--expected-repository",
                EXPECTED_REPOSITORY,
                "--consumer-base",
                consumer_base or repository.consumer_base,
                "--decision-commit",
                decision_commit or repository.decision_commit,
                "--record-id",
                record_id,
                "--decision-path",
                decision_path,
                "--format",
                output_format,
            ],
            cwd=REPO_ROOT,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
            env=environment,
        )

    def parse_payload(self, completed: subprocess.CompletedProcess[str]) -> dict:
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            self.fail(
                f"verifier did not emit JSON: {exc}\n"
                f"return code: {completed.returncode}\n"
                f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
            )
        self.assertEqual(
            payload.get("document_kind"),
            "diagnostic_catalog_acceptance_binding_verification",
        )
        self.assertEqual(payload.get("internal_format_version"), 1)
        self.assertIs(payload.get("public_contract"), False)
        self.assertNotIn("Traceback", completed.stdout + completed.stderr)
        return payload

    def assert_mismatch(
        self,
        completed: subprocess.CompletedProcess[str],
    ) -> dict:
        payload = self.parse_payload(completed)
        self.assertEqual(
            completed.returncode,
            1,
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
        )
        self.assertEqual(payload.get("offline_binding"), "NOT_VERIFIED")
        self.assertEqual(payload.get("failure_class"), "BINDING_MISMATCH")
        self.assertEqual(payload.get("effective_acceptance"), "NOT_ESTABLISHED")
        self.assertIs(payload.get("implementation_parity_authorized"), False)
        self.assertIs(payload.get("runtime_consumption_authorized"), False)
        self.assertIs(payload.get("runtime_ready"), False)
        self.assertTrue(payload.get("error"))
        return payload

    def assert_undetermined(
        self,
        completed: subprocess.CompletedProcess[str],
        *,
        failure_class: str = "ACQUISITION_UNAVAILABLE",
    ) -> dict:
        payload = self.parse_payload(completed)
        self.assertEqual(
            completed.returncode,
            3,
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
        )
        self.assertEqual(payload.get("offline_binding"), "NOT_VERIFIED")
        self.assertEqual(payload.get("failure_class"), failure_class)
        self.assertEqual(payload.get("effective_acceptance"), "NOT_ESTABLISHED")
        self.assertIs(payload.get("implementation_parity_authorized"), False)
        self.assertIs(payload.get("runtime_consumption_authorized"), False)
        self.assertIs(payload.get("runtime_ready"), False)
        self.assertTrue(payload.get("error"))
        return payload

    def assert_control_safe_text_failure(
        self,
        completed: subprocess.CompletedProcess[str],
        *,
        return_code: int,
    ) -> list[str]:
        self.assertEqual(completed.returncode, return_code, completed.stderr)
        self.assertEqual(completed.stderr, "")
        self.assertNotIn("\r", completed.stdout)
        self.assertNotIn("\x1b", completed.stdout)
        lines = completed.stdout.splitlines()
        self.assertEqual(len(lines), 4, completed.stdout)
        for line in lines:
            self.assertFalse(
                any(ord(character) < 0x20 or ord(character) == 0x7F for character in line),
                repr(line),
            )
        return lines

    def test_valid_binding_is_offline_only_and_never_authorizes_runtime(self) -> None:
        with AcceptanceRepository() as repository:
            completed = self.run_verifier(repository)
        payload = self.parse_payload(completed)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(payload["offline_binding"], "VERIFIED")
        self.assertEqual(payload["effective_acceptance"], "NOT_ESTABLISHED")
        self.assertIs(payload["implementation_parity_authorized"], False)
        self.assertIs(payload["runtime_consumption_authorized"], False)
        self.assertIs(payload["runtime_ready"], False)
        self.assertEqual(
            payload["candidate_verification"]["catalog_sha256"],
            "da541828f462784eeb504af1436e6c689dc7f429814a18c729e2dc48362a0cec",
        )
        self.assertIn(
            "factual-human-decision-maker",
            payload["unverified_external_predicates"],
        )
        self.assertIn(
            "github-subject-candidate-pr-state",
            payload["unverified_external_predicates"],
        )
        self.assertIn(
            "github-verifier-contract-pr-state",
            payload["unverified_external_predicates"],
        )
        self.assertNotIn(
            "github-candidate-pr-state",
            payload["unverified_external_predicates"],
        )
        self.assertIn(
            "branch-ruleset-codeowners-and-bypass-controls-at-event",
            payload["unverified_external_predicates"],
        )
        self.assertIn(
            "published-workflow-run-state",
            payload["unverified_authority_predicates"],
        )
        self.assertEqual(
            payload["verifier_contract_commit_sha1"],
            repository.verifier_contract_merge,
        )
        self.assertIn(
            "decision-preexists-selected-consumer-revision",
            payload["verified"],
        )
        self.assertNotIn("decision-preexists-consumer-base", payload["verified"])
        self.assertIn(
            "consumer-base-role-authority",
            payload["unverified_preconditions"],
        )
        self.assertIn(
            "consuming-change-provider-state",
            payload["unverified_preconditions"],
        )
        running_sha256 = hashlib.sha256(VERIFIER.read_bytes()).hexdigest()
        self.assertEqual(
            payload["local_observations"]["running_verifier_raw_sha256"],
            running_sha256,
        )
        self.assertEqual(
            payload["local_observations"][
                "bound_acceptance_verifier_raw_sha256"
            ],
            running_sha256,
        )
        self.assertIs(
            payload["local_observations"][
                "running_verifier_matches_bound_contract"
            ],
            True,
        )

    def test_unmerged_head_and_non_first_parent_consumer_are_rejected(self) -> None:
        with AcceptanceRepository(merge_acceptance=False) as repository:
            head_only = self.assert_mismatch(self.run_verifier(repository))
            unrelated = self.assert_mismatch(
                self.run_verifier(
                    repository,
                    consumer_base=repository.acceptance_base,
                )
            )
        self.assertIn("two-parent merge", head_only["error"])
        self.assertIn("first-parent chain", unrelated["error"])

    def test_running_verifier_drift_is_observed_but_never_authorizes(self) -> None:
        with AcceptanceRepository(
            contract_verifier_suffix=b"\n# contract-only drift fixture\n"
        ) as repository:
            completed = self.run_verifier(repository)
        payload = self.parse_payload(completed)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(payload["offline_binding"], "VERIFIED")
        self.assertIs(
            payload["local_observations"][
                "running_verifier_matches_bound_contract"
            ],
            False,
        )
        self.assertNotEqual(
            payload["local_observations"]["running_verifier_raw_sha256"],
            payload["local_observations"][
                "bound_acceptance_verifier_raw_sha256"
            ],
        )
        self.assertIs(payload["implementation_parity_authorized"], False)
        self.assertIs(payload["runtime_consumption_authorized"], False)
        self.assertIs(payload["runtime_ready"], False)

    def test_acceptance_merge_with_extra_file_is_rejected(self) -> None:
        with AcceptanceRepository(extra_file=True) as repository:
            payload = self.assert_mismatch(self.run_verifier(repository))
        self.assertIn("exactly the one decision record", payload["error"])

    def test_record_cannot_predeclare_review_class_or_runtime_authority(self) -> None:
        def predeclare(record: dict) -> None:
            record["repository_process"]["human_review_class"] = (
                "SOLE_OWNER_ATTESTED"
            )

        with AcceptanceRepository(record_mutator=predeclare) as repository:
            predeclared = self.assert_mismatch(self.run_verifier(repository))

        def authorize(record: dict) -> None:
            record["scope"]["runtime_consumption_authorized"] = True

        with AcceptanceRepository(record_mutator=authorize) as repository:
            runtime = self.assert_mismatch(self.run_verifier(repository))
        self.assertIn("predeclaration", predeclared["error"])
        self.assertIn("runtime consumption", runtime["error"])

    def test_json_number_fields_reject_boolean_type_confusion(self) -> None:
        def format_boolean(record: dict) -> None:
            record["internal_format_version"] = True

        with AcceptanceRepository(record_mutator=format_boolean) as repository:
            document_format = self.assert_mismatch(self.run_verifier(repository))

        def revision_boolean(record: dict) -> None:
            record["subject"]["catalog"]["catalog_revision"] = True

        with AcceptanceRepository(record_mutator=revision_boolean) as repository:
            catalog_revision = self.assert_mismatch(self.run_verifier(repository))
        self.assertIn("internal_format_version", document_format["error"])
        self.assertIn("catalog.catalog_revision mismatch", catalog_revision["error"])

    def test_candidate_hash_and_authority_base_tamper_are_rejected(self) -> None:
        def hash_tamper(record: dict) -> None:
            record["subject"]["catalog"]["raw_sha256"] = "0" * 64

        with AcceptanceRepository(record_mutator=hash_tamper) as repository:
            candidate = self.assert_mismatch(self.run_verifier(repository))

        def authority_tamper(record: dict) -> None:
            record["authority_basis"]["governance"]["commit_sha1"] = (
                "c51b8c1cc7cb5fd343a4acf65e0cccc38356a4fe"
            )

        with AcceptanceRepository(record_mutator=authority_tamper) as repository:
            authority = self.assert_mismatch(self.run_verifier(repository))
        self.assertIn("subject.catalog.raw_sha256", candidate["error"])
        self.assertIn("first parent", authority["error"])

    def test_verifier_contract_must_precede_the_decision(self) -> None:
        def pre_contract(record: dict) -> None:
            record["verifier_contract"][
                "canonical_merge_commit_sha1"
            ] = "c51b8c1cc7cb5fd343a4acf65e0cccc38356a4fe"

        with AcceptanceRepository(record_mutator=pre_contract) as repository:
            payload = self.assert_mismatch(self.run_verifier(repository))
        self.assertIn("first canonical first-parent introduction", payload["error"])

    def test_squashed_verifier_contract_cannot_authorize_a_decision(self) -> None:
        with AcceptanceRepository(merge_contract=False) as repository:
            payload = self.assert_mismatch(self.run_verifier(repository))
        self.assertIn(
            "verifier contract canonical merge must be a two-parent merge",
            payload["error"],
        )

    def test_adr_order_and_hash_are_closed(self) -> None:
        def reverse(record: dict) -> None:
            record["authority_basis"]["accepted_adrs"].reverse()

        with AcceptanceRepository(record_mutator=reverse) as repository:
            order = self.assert_mismatch(self.run_verifier(repository))

        def hash_tamper(record: dict) -> None:
            record["authority_basis"]["accepted_adrs"][1][
                "raw_sha256"
            ] = "1" * 64

        with AcceptanceRepository(record_mutator=hash_tamper) as repository:
            raw_hash = self.assert_mismatch(self.run_verifier(repository))
        self.assertIn("adr_id mismatch", order["error"])
        self.assertIn("raw_sha256 mismatch", raw_hash["error"])

    def test_authority_locators_are_closed(self) -> None:
        def governance_locator(record: dict) -> None:
            record["authority_basis"]["governance"]["locator"] = "Nearby text"

        with AcceptanceRepository(record_mutator=governance_locator) as repository:
            governance = self.assert_mismatch(self.run_verifier(repository))

        def adr_locator(record: dict) -> None:
            record["authority_basis"]["accepted_adrs"][0]["locator"] = "Status"

        with AcceptanceRepository(record_mutator=adr_locator) as repository:
            adr = self.assert_mismatch(self.run_verifier(repository))
        self.assertIn("governance.locator mismatch", governance["error"])
        self.assertIn("accepted_adrs[0].locator mismatch", adr["error"])

    def test_modified_then_restored_record_is_rejected(self) -> None:
        with AcceptanceRepository() as repository:
            repository.modify_then_restore_record()
            payload = self.assert_mismatch(self.run_verifier(repository))
        self.assertIn("not append-only", payload["error"])

    def test_merge_modified_then_restored_record_is_rejected(self) -> None:
        with AcceptanceRepository() as repository:
            repository.merge_modify_then_restore_record()
            payload = self.assert_mismatch(self.run_verifier(repository))
        self.assertIn("not append-only", payload["error"])

    def test_competing_subject_record_is_rejected(self) -> None:
        with AcceptanceRepository() as repository:
            repository.add_duplicate_record()
            payload = self.assert_mismatch(self.run_verifier(repository))
        self.assertIn("competing subject", payload["error"])

    def test_structured_successor_invalidates_selected_record(self) -> None:
        with AcceptanceRepository() as repository:
            repository.add_successor_record()
            payload = self.assert_mismatch(self.run_verifier(repository))
        self.assertIn("selected decision is superseded", payload["error"])

    def test_duplicate_json_key_is_rejected(self) -> None:
        def duplicate(text: str) -> str:
            return text.replace(
                '"document_kind": "diagnostic_catalog_acceptance_decision",',
                (
                    '"document_kind": "diagnostic_catalog_acceptance_decision",'
                    '\n  "document_kind": "diagnostic_catalog_acceptance_decision",'
                ),
                1,
            )

        with AcceptanceRepository(record_text_mutator=duplicate) as repository:
            payload = self.assert_mismatch(self.run_verifier(repository))
        self.assertIn("duplicate JSON key", payload["error"])

    def test_text_failure_escapes_control_bearing_record_id(self) -> None:
        malicious = "BAD\r\nFORGED\x1b[31m"
        with AcceptanceRepository() as repository:
            completed = self.run_verifier(
                repository,
                record_id=malicious,
                output_format="text",
            )
        lines = self.assert_control_safe_text_failure(
            completed,
            return_code=1,
        )
        self.assertIn(r"BAD\r\nFORGED\u001b[31m", lines[2])
        self.assertNotIn("\nFORGED", completed.stdout)

    def test_text_failure_escapes_control_bearing_duplicate_key(self) -> None:
        def duplicate_control_key(text: str) -> str:
            return text.replace(
                "{\n",
                '{\n  "bad\\n\\u001bkey": 1,\n  "bad\\n\\u001bkey": 2,\n',
                1,
            )

        with AcceptanceRepository(
            record_text_mutator=duplicate_control_key
        ) as repository:
            completed = self.run_verifier(
                repository,
                output_format="text",
            )
        lines = self.assert_control_safe_text_failure(
            completed,
            return_code=1,
        )
        self.assertIn(r"bad\n\u001bkey", lines[3])

    def test_text_failure_escapes_control_bearing_git_stderr(self) -> None:
        with AcceptanceRepository() as repository, tempfile.TemporaryDirectory(
            prefix="diagnostic-acceptance-fake-git-"
        ) as temporary:
            fake_git = Path(temporary) / "git"
            fake_git.write_text(
                "#!/bin/sh\n"
                "printf 'git failed\\n\\033[31mFORGED\\033[0m\\n' >&2\n"
                "exit 7\n",
                encoding="ascii",
            )
            fake_git.chmod(0o755)
            completed = self.run_verifier(
                repository,
                output_format="text",
                extra_env={
                    "PATH": f"{temporary}{os.pathsep}{os.environ.get('PATH', '')}",
                },
            )
        lines = self.assert_control_safe_text_failure(
            completed,
            return_code=3,
        )
        self.assertIn(r"git failed\n\u001b[31mFORGED\u001b[0m", lines[3])

    def test_usage_error_escapes_control_bearing_unknown_argument(self) -> None:
        malicious = "--forged\r\n\x1b[31mFORGED"
        completed = subprocess.run(
            [
                sys.executable,
                str(VERIFIER),
                "--repo-root",
                str(REPO_ROOT),
                "--expected-repository",
                EXPECTED_REPOSITORY,
                "--consumer-base",
                BASE_COMMIT,
                "--decision-commit",
                BASE_COMMIT,
                "--record-id",
                RECORD_ID,
                "--decision-path",
                DECISION_PATH,
                malicious,
            ],
            cwd=REPO_ROOT,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, "")
        self.assertNotIn("\r", completed.stderr)
        self.assertNotIn("\x1b", completed.stderr)
        self.assertIn(r"--forged\r\n\u001b[31mFORGED", completed.stderr)
        for line in completed.stderr.splitlines():
            self.assertFalse(
                any(
                    ord(character) < 0x20 or ord(character) == 0x7F
                    for character in line
                ),
                repr(line),
            )

    def test_malformed_git_plumbing_output_is_undetermined(self) -> None:
        with AcceptanceRepository() as repository, tempfile.TemporaryDirectory(
            prefix="diagnostic-acceptance-malformed-git-"
        ) as temporary:
            fake_git = Path(temporary) / "git"
            fake_git.write_text(
                "#!/bin/sh\nprintf 'not-a-bare-state\\n'\n",
                encoding="ascii",
            )
            fake_git.chmod(0o755)
            completed = self.run_verifier(
                repository,
                extra_env={
                    "PATH": f"{temporary}{os.pathsep}{os.environ.get('PATH', '')}",
                },
            )
        payload = self.assert_undetermined(completed)
        self.assertIn("cannot determine bare state", payload["error"])

    def test_dirty_worktree_candidate_copies_are_ignored_and_unchanged(self) -> None:
        with AcceptanceRepository() as repository:
            catalog = (
                repository.root
                / "docs/evidence/v0.5/diagnostic-catalog/catalog-r1.json"
            )
            catalog.write_text('{"forged":"worktree-only"}\n', encoding="utf-8")
            before = repository.status_bytes()
            completed = self.run_verifier(repository)
            after = repository.status_bytes()
            self.assertEqual(before, after)
            self.assertEqual(
                catalog.read_text(encoding="utf-8"),
                '{"forged":"worktree-only"}\n',
            )
        payload = self.parse_payload(completed)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(payload["offline_binding"], "VERIFIED")

    def test_default_execution_does_not_write_candidate_verifier_bytecode(self) -> None:
        with AcceptanceRepository() as repository, tempfile.TemporaryDirectory(
            prefix="diagnostic-acceptance-pycache-test-"
        ) as temporary:
            completed = self.run_verifier(
                repository,
                extra_env={"PYTHONPYCACHEPREFIX": temporary},
            )
            candidate_bytecode = [
                path
                for path in Path(temporary).rglob(
                    "verify_diagnostic_catalog_candidate*.pyc"
                )
            ]
        payload = self.parse_payload(completed)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(payload["offline_binding"], "VERIFIED")
        self.assertEqual(candidate_bytecode, [])

    def test_pr_url_rejects_ascii_controls_before_parsing(self) -> None:
        for control in ("\n", "\r", "\t"):
            with self.subTest(control=repr(control)):
                def inject(record: dict, control: str = control) -> None:
                    record["repository_process"]["pr_url"] = (
                        "https://github.com/Mossland"
                        f"{control}OpenDevs/"
                        "agentic-assurance-profile/pull/999"
                    )

                with AcceptanceRepository(record_mutator=inject) as repository:
                    payload = self.assert_mismatch(self.run_verifier(repository))
                self.assertIn("ASCII control character", payload["error"])

    def test_pr_url_rejects_noncanonical_spelling(self) -> None:
        for value in (
            (
                "HTTPS://github.com/MosslandOpenDevs/"
                "agentic-assurance-profile/pull/999"
            ),
            (
                " https://github.com/MosslandOpenDevs/"
                "agentic-assurance-profile/pull/999"
            ),
        ):
            with self.subTest(value=value):
                def replace(record: dict, value: str = value) -> None:
                    record["repository_process"]["pr_url"] = value

                with AcceptanceRepository(record_mutator=replace) as repository:
                    payload = self.assert_mismatch(self.run_verifier(repository))
                self.assertIn("canonical", payload["error"])

    def test_git_environment_redirections_are_ignored(self) -> None:
        with AcceptanceRepository() as repository:
            completed = self.run_verifier(
                repository,
                extra_env={
                    "GIT_DIR": str(repository.root / "missing-git-dir"),
                    "GIT_WORK_TREE": str(repository.root / "missing-worktree"),
                    "GIT_OBJECT_DIRECTORY": str(
                        repository.root / "missing-objects"
                    ),
                    "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(
                        repository.root / "missing-alternates"
                    ),
                    "GIT_GRAFT_FILE": str(repository.root / "fake-grafts"),
                    "GIT_REPLACE_REF_BASE": "refs/fake-replacements/",
                },
            )
        payload = self.parse_payload(completed)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(payload["offline_binding"], "VERIFIED")

    def test_shallow_repository_is_undetermined(self) -> None:
        with AcceptanceRepository() as repository:
            repository.mark_shallow()
            payload = self.assert_undetermined(self.run_verifier(repository))
        self.assertIn("shallow repositories are unsupported", payload["error"])

    def test_missing_selected_revision_object_is_undetermined(self) -> None:
        with AcceptanceRepository() as repository:
            payload = self.assert_undetermined(
                self.run_verifier(
                    repository,
                    consumer_base="0" * 40,
                )
            )
        self.assertIn("local Git command failed", payload["error"])

    def test_git_timeout_is_undetermined(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "diagnostic_acceptance_verifier_timeout_test",
            VERIFIER,
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        stdout = io.StringIO()
        argv = [
            "--repo-root",
            str(REPO_ROOT),
            "--expected-repository",
            EXPECTED_REPOSITORY,
            "--consumer-base",
            BASE_COMMIT,
            "--decision-commit",
            BASE_COMMIT,
            "--record-id",
            RECORD_ID,
            "--decision-path",
            DECISION_PATH,
            "--format",
            "json",
        ]
        with mock.patch.object(
            module.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(["git"], 20),
        ), contextlib.redirect_stdout(stdout):
            return_code = module.main(argv)
        self.assertEqual(return_code, 3)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["offline_binding"], "NOT_VERIFIED")
        self.assertEqual(payload["failure_class"], "ACQUISITION_UNAVAILABLE")
        self.assertIn("local Git object inspection failed", payload["error"])

    def test_unexpected_exception_is_redacted(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "diagnostic_acceptance_verifier_under_test",
            VERIFIER,
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        stdout = io.StringIO()
        stderr = io.StringIO()
        argv = [
            "--repo-root",
            str(REPO_ROOT),
            "--expected-repository",
            EXPECTED_REPOSITORY,
            "--consumer-base",
            BASE_COMMIT,
            "--decision-commit",
            BASE_COMMIT,
            "--record-id",
            RECORD_ID,
            "--decision-path",
            DECISION_PATH,
            "--format",
            "json",
        ]
        with mock.patch.object(
            module,
            "verify",
            side_effect=RuntimeError("secret internal detail"),
        ), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            return_code = module.main(argv)
        self.assertEqual(return_code, 3)
        output = stdout.getvalue() + stderr.getvalue()
        self.assertNotIn("Traceback", output)
        self.assertNotIn("secret internal detail", output)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(
            payload["error"],
            "unexpected internal verification failure",
        )
        self.assertEqual(payload["offline_binding"], "NOT_VERIFIED")
        self.assertEqual(payload["failure_class"], "INTERNAL_FAILURE")
        self.assertEqual(payload["effective_acceptance"], "NOT_ESTABLISHED")


if __name__ == "__main__":
    unittest.main()
