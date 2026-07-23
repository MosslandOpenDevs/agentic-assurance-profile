"""Black-box tests for the review-only diagnostic candidate verifier."""

from __future__ import annotations

import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from typing import Callable, Optional


REPO_ROOT = Path(__file__).resolve().parent.parent
VERIFIER = REPO_ROOT / "scripts" / "verify_diagnostic_catalog_candidate.py"
CATALOG = (
    REPO_ROOT
    / "docs"
    / "evidence"
    / "v0.5"
    / "diagnostic-catalog"
    / "catalog-r1.json"
)
MAPPING = CATALOG.with_name("legacy-v0.4.0-mapping-r1.json")
COMPATIBILITY_CHANGES = CATALOG.with_name("compatibility-changes-r1.json")
NORMALIZED_INVENTORY = CATALOG.with_name("normalized-inventory-r1.json")


def json_bytes(value: object) -> bytes:
    """Serialize tampered review data without sharing verifier code."""

    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


class CandidatePair:
    """Create isolated candidate bytes while re-binding the catalog hash."""

    def __init__(
        self,
        *,
        catalog_mutator: Optional[Callable[[dict], None]] = None,
        mapping_mutator: Optional[Callable[[dict], None]] = None,
    ) -> None:
        self._temporary = tempfile.TemporaryDirectory(
            prefix="diagnostic-candidate-verifier-test-"
        )
        self.root = Path(self._temporary.name)
        catalog = copy.deepcopy(json.loads(CATALOG.read_text(encoding="utf-8")))
        mapping = copy.deepcopy(json.loads(MAPPING.read_text(encoding="utf-8")))
        if catalog_mutator is not None:
            catalog_mutator(catalog)
        catalog_data = json_bytes(catalog)
        mapping["catalog_ref"]["raw_sha256_review_evidence"] = hashlib.sha256(
            catalog_data
        ).hexdigest()
        if mapping_mutator is not None:
            mapping_mutator(mapping)
        self.catalog = self.root / "catalog.json"
        self.mapping = self.root / "mapping.json"
        self.catalog.write_bytes(catalog_data)
        self.mapping.write_bytes(json_bytes(mapping))

    def __enter__(self) -> "CandidatePair":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self._temporary.cleanup()


class DiagnosticCatalogCandidateVerifierTests(unittest.TestCase):
    maxDiff = 2000

    def run_verifier(
        self,
        *,
        catalog: Path = CATALOG,
        mapping: Path = MAPPING,
        compatibility_changes: Path = COMPATIBILITY_CHANGES,
        inventory: Path = NORMALIZED_INVENTORY,
        write_inventory: Optional[Path] = None,
        json_output: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            str(VERIFIER),
            "--repo-root",
            str(REPO_ROOT),
            "--catalog",
            str(catalog),
            "--mapping",
            str(mapping),
            "--compatibility-changes",
            str(compatibility_changes),
            "--inventory",
            str(inventory),
        ]
        if write_inventory is not None:
            command.extend(["--write-normalized-inventory", str(write_inventory)])
        if json_output:
            command.append("--json")
        return subprocess.run(
            command,
            cwd=REPO_ROOT,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

    def assert_controlled_failure(
        self, completed: subprocess.CompletedProcess[str]
    ) -> dict:
        self.assertEqual(completed.returncode, 1, completed)
        self.assertNotIn("Traceback", completed.stdout + completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(
            report["scope"], "REVIEW_ONLY_NOT_RUNTIME_OR_ACCEPTANCE"
        )
        self.assertTrue(report["error"])
        return report

    def test_exact_candidate_passes_and_reports_independent_inventory(self) -> None:
        completed = self.run_verifier()
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(
            report["scope"], "REVIEW_ONLY_NOT_RUNTIME_OR_ACCEPTANCE"
        )
        self.assertEqual(report["inventory_counts"]["direct_emitter_count"], 243)
        self.assertEqual(
            report["inventory_counts"]["direct_emitter_function_count"], 41
        )
        self.assertEqual(report["inventory_counts"]["upstream_producer_count"], 84)
        self.assertEqual(report["inventory_counts"]["semantic_group_count"], 309)
        self.assertEqual(report["control_flow_counts"]["report_emit_returns"], 30)
        self.assertEqual(report["control_flow_counts"]["report_results_reads"], 8)
        self.assertEqual(report["workflow_counts"], {"workflows": 2, "jobs": 5, "steps": 36})
        self.assertEqual(report["terminal_family_count"], 41)
        self.assertEqual(report["phase0_case_count"], 7)
        self.assertTrue(report["limitations"])

    def test_direct_source_locator_tamper_fails_closed(self) -> None:
        def tamper(mapping: dict) -> None:
            rows = mapping["semantic_mapping"]["group_rows"]
            row = next(item for item in rows if item["source_selectors"]["direct_emitter_lines"])
            row["source_selectors"]["direct_emitter_lines"][0] = 1

        with CandidatePair(mapping_mutator=tamper) as pair:
            report = self.assert_controlled_failure(
                self.run_verifier(catalog=pair.catalog, mapping=pair.mapping)
            )
        self.assertIn("direct emitter", report["error"])

    def test_unregistered_authority_source_id_fails_closed(self) -> None:
        def tamper(catalog: dict) -> None:
            catalog["public_checks"][0]["authority_refs"][0][
                "source_id"
            ] = "missing-authority-source"

        with CandidatePair(catalog_mutator=tamper) as pair:
            report = self.assert_controlled_failure(
                self.run_verifier(catalog=pair.catalog, mapping=pair.mapping)
            )
        self.assertIn("unregistered authority source", report["error"])

    def test_unregistered_terminal_reason_fails_closed(self) -> None:
        def tamper(mapping: dict) -> None:
            family = next(
                item
                for item in mapping["terminal_mapping"]["families"]
                if any(
                    ref.get("kind") == "REGISTERED_REASON"
                    for ref in item.get("reason_source_refs", [])
                )
            )
            reference = next(
                ref
                for ref in family["reason_source_refs"]
                if ref.get("kind") == "REGISTERED_REASON"
            )
            reference["reason_code"] = "NOT_REGISTERED"

        with CandidatePair(mapping_mutator=tamper) as pair:
            report = self.assert_controlled_failure(
                self.run_verifier(catalog=pair.catalog, mapping=pair.mapping)
            )
        self.assertIn("unknown reason", report["error"])

    def test_f0002_predicate_tamper_fails_closed(self) -> None:
        def tamper(catalog: dict) -> None:
            finding = next(
                item
                for item in catalog["findings"]["allocated_entries"]
                if item["code"] == "F0002"
            )
            finding["condition_predicate"]["relation"] = "LTE"

        with CandidatePair(catalog_mutator=tamper) as pair:
            report = self.assert_controlled_failure(
                self.run_verifier(catalog=pair.catalog, mapping=pair.mapping)
            )
        self.assertIn("F0002", report["error"])

    def test_catalog_source_binding_selector_tamper_fails_closed(self) -> None:
        def tamper(catalog: dict) -> None:
            finding = next(
                item
                for item in catalog["findings"]["allocated_entries"]
                if item["code"] == "F0005"
            )
            producer = finding["source_binding"]["producer_groups"][0]
            producer["callsite_selector"] = "bogus@1 in nowhere"
            producer["variant_id"] = "BOGUS_VARIANT"

        with CandidatePair(catalog_mutator=tamper) as pair:
            report = self.assert_controlled_failure(
                self.run_verifier(catalog=pair.catalog, mapping=pair.mapping)
            )
        self.assertIn("source binding differs", report["error"])

    def test_fact_literal_outside_catalog_enum_fails_closed(self) -> None:
        def tamper(mapping: dict) -> None:
            row = next(
                item
                for item in mapping["semantic_mapping"]["group_rows"]
                if item["group_id"] == "U-1242"
            )
            projection = next(
                item
                for item in row["target"]["projections"]
                if item["callsite_selector"]
                == "load_yaml@3275 in check_adoption_document"
            )
            projection["target"]["fact_bindings"]["bindings"]["limit_kind"][
                "value"
            ] = "NOT_VALID"

        with CandidatePair(mapping_mutator=tamper) as pair:
            report = self.assert_controlled_failure(
                self.run_verifier(catalog=pair.catalog, mapping=pair.mapping)
            )
        self.assertIn("outside the catalog enum", report["error"])

    def test_factless_finding_rejects_fabricated_bindings(self) -> None:
        def tamper(mapping: dict) -> None:
            row = next(
                item
                for item in mapping["semantic_mapping"]["group_rows"]
                if item["group_id"] == "U-1242"
            )
            projection = next(
                item
                for item in row["target"]["projections"]
                if item["callsite_selector"] == "load_yaml@2833 in check_template"
            )
            projection["target"]["fact_bindings"] = {
                "closed": False,
                "required_key_set": [],
                "on_missing_required_key": "ALLOW",
                "on_extra_key": "ALLOW",
                "on_null": "ALLOW",
                "bindings": {
                    "fabricated": {"kind": "LITERAL", "value": "secret"}
                },
            }

        with CandidatePair(mapping_mutator=tamper) as pair:
            report = self.assert_controlled_failure(
                self.run_verifier(catalog=pair.catalog, mapping=pair.mapping)
            )
        self.assertIn("factless finding must not carry", report["error"])

    def test_ordered_fact_dispatch_requires_true_boolean(self) -> None:
        def tamper(mapping: dict) -> None:
            row = next(
                item
                for item in mapping["semantic_mapping"]["group_rows"]
                if item["group_id"] == "PHASE0-F0003-POLICY"
            )
            row["target"]["fact_bindings"]["bindings"]["failure_kind"][
                "ordered_first_match"
            ] = "NOT_BOOLEAN"

        with CandidatePair(mapping_mutator=tamper) as pair:
            report = self.assert_controlled_failure(
                self.run_verifier(catalog=pair.catalog, mapping=pair.mapping)
            )
        self.assertIn("ordered_first_match must be true", report["error"])

    def test_phase0_positive_completion_forgery_fails_closed(self) -> None:
        def forge(projection_root: dict) -> None:
            case = next(
                item
                for item in projection_root["cases"]
                if item["case_id"] == "core-split-draft-pass"
            )
            projection = case["condition_projections"][0]
            projection.clear()
            projection.update(
                {
                    "internal_condition_key": (
                        "phase0.internal.adopter."
                        "split-core-draft-baseline-satisfied"
                    ),
                    "projection_kind": "CHECK_COMPLETION",
                    "public_check_completion": "COMPLETED",
                    "check_id": "adoption.bundle-conformance",
                    "state": {
                        "applicability": "APPLICABLE",
                        "completion": "COMPLETED",
                        "outcome": "PASS",
                    },
                }
            )

        def tamper_catalog(catalog: dict) -> None:
            forge(catalog["phase0_selected_case_projection"])

        def tamper_mapping(mapping: dict) -> None:
            forge(mapping["phase0_selected_projection"])

        with CandidatePair(
            catalog_mutator=tamper_catalog, mapping_mutator=tamper_mapping
        ) as pair:
            report = self.assert_controlled_failure(
                self.run_verifier(catalog=pair.catalog, mapping=pair.mapping)
            )
        self.assertIn("unsupported projection kind", report["error"])

    def test_f0036_non_schema_source_tamper_fails_closed(self) -> None:
        def tamper(catalog: dict) -> None:
            finding = next(
                item
                for item in catalog["findings"]["allocated_entries"]
                if item["code"] == "F0036"
            )
            finding["source_binding"]["producer_groups"].append(
                {
                    "group_id": "U-1255",
                    "callsite_selector": "load_yaml@3620 in check_artifacts",
                    "variant_id": None,
                    "source_predicate": None,
                }
            )

        with CandidatePair(catalog_mutator=tamper) as pair:
            report = self.assert_controlled_failure(
                self.run_verifier(catalog=pair.catalog, mapping=pair.mapping)
            )
        self.assertIn("F0036", report["error"])

    def test_compatibility_change_set_tamper_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="diagnostic-compatibility-change-test-"
        ) as temporary:
            path = Path(temporary) / "compatibility.json"
            value = json.loads(COMPATIBILITY_CHANGES.read_text(encoding="utf-8"))
            value["changes"][0]["migration_note"] = ""
            path.write_bytes(json_bytes(value))
            completed = self.run_verifier(compatibility_changes=path)
        report = self.assert_controlled_failure(completed)
        self.assertIn("migration_note", report["error"])

    def test_normalized_inventory_tamper_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="diagnostic-normalized-inventory-test-"
        ) as temporary:
            path = Path(temporary) / "inventory.json"
            value = json.loads(NORMALIZED_INVENTORY.read_text(encoding="utf-8"))
            value["validator_inventory"]["direct_emitter_function_count"] = 42
            path.write_bytes(json_bytes(value))
            completed = self.run_verifier(inventory=path)
        report = self.assert_controlled_failure(completed)
        self.assertIn("normalized inventory differs", report["error"])

    def test_explicit_inventory_generation_round_trips(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="diagnostic-normalized-inventory-write-test-"
        ) as temporary:
            path = Path(temporary) / "inventory.json"
            generated = self.run_verifier(
                inventory=path,
                write_inventory=path,
            )
            self.assertEqual(generated.returncode, 0, generated.stderr)
            generated_report = json.loads(generated.stdout)
            self.assertTrue(generated_report["normalized_inventory_written"])
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(),
                generated_report["normalized_inventory_sha256"],
            )
            self.assertEqual(path.read_bytes(), NORMALIZED_INVENTORY.read_bytes())

    def test_inventory_generation_does_not_require_old_cross_hashes(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "diagnostic_candidate_verifier_generation_test",
            VERIFIER,
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory(
            prefix="diagnostic-normalized-inventory-regeneration-test-"
        ) as temporary:
            path = Path(temporary) / "inventory.json"
            with mock.patch.object(
                module,
                "validate_review_artifact_hash_references",
                side_effect=AssertionError(
                    "generation must not require the previous inventory hash"
                ),
            ):
                report = module.verify(
                    REPO_ROOT,
                    CATALOG,
                    MAPPING,
                    COMPATIBILITY_CHANGES,
                    path,
                    write_inventory_path=path,
                )
        self.assertTrue(report["normalized_inventory_written"])

    def test_bound_release_source_hash_tamper_fails_closed(self) -> None:
        def tamper_catalog(catalog: dict) -> None:
            catalog["source_scope"]["exact_runtime_sources"][0][
                "raw_sha256"
            ] = "0" * 64

        def tamper_mapping(mapping: dict) -> None:
            mapping["exact_source"]["exact_runtime_sources"][0][
                "raw_sha256"
            ] = "0" * 64

        with CandidatePair(
            catalog_mutator=tamper_catalog, mapping_mutator=tamper_mapping
        ) as pair:
            report = self.assert_controlled_failure(
                self.run_verifier(catalog=pair.catalog, mapping=pair.mapping)
            )
        self.assertIn("source hash mismatch", report["error"])

    def test_runtime_authority_surface_tamper_fails_closed(self) -> None:
        def tamper(catalog: dict) -> None:
            authority = catalog["authority_sources"]["v0.4.0-runtime-surface"]
            authority["annotated_tag_object_sha1"] = "0" * 40
            authority["revision_sha1"] = "1" * 40

        with CandidatePair(catalog_mutator=tamper) as pair:
            report = self.assert_controlled_failure(
                self.run_verifier(catalog=pair.catalog, mapping=pair.mapping)
            )
        self.assertIn("differs from the exact runtime surface", report["error"])

    def test_terminal_coverage_summary_tamper_fails_closed(self) -> None:
        def tamper(mapping: dict) -> None:
            mapping["terminal_mapping"]["coverage_summary"][
                "reason_code_count"
            ] = 35

        with CandidatePair(mapping_mutator=tamper) as pair:
            report = self.assert_controlled_failure(
                self.run_verifier(catalog=pair.catalog, mapping=pair.mapping)
            )
        self.assertIn("coverage summary", report["error"])

    def test_terminal_schema_identity_tamper_fails_closed(self) -> None:
        def tamper(mapping: dict) -> None:
            mapping["terminal_mapping"]["derived_from"][
                "review_data_schema"
            ] = "aap-v0.5-terminal-crosswalk-candidate-1"

        with CandidatePair(mapping_mutator=tamper) as pair:
            report = self.assert_controlled_failure(
                self.run_verifier(catalog=pair.catalog, mapping=pair.mapping)
            )
        self.assertIn("schema identity", report["error"])

    def test_malformed_json_has_no_traceback(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="diagnostic-candidate-malformed-test-"
        ) as temporary:
            catalog = Path(temporary) / "catalog.json"
            catalog.write_bytes(b'{"duplicate": 1, "duplicate": 2}')
            completed = self.run_verifier(catalog=catalog)
        report = self.assert_controlled_failure(completed)
        self.assertIn("duplicate JSON key", report["error"])

    def test_overflowing_json_exponent_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="diagnostic-candidate-overflowing-json-test-"
        ) as temporary:
            catalog = Path(temporary) / "catalog.json"
            catalog.write_bytes(b'{"number":1e9999}')
            completed = self.run_verifier(catalog=catalog)
        report = self.assert_controlled_failure(completed)
        self.assertIn("non-finite JSON number", report["error"])

    def test_overlong_json_integer_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="diagnostic-candidate-overlong-integer-test-"
        ) as temporary:
            catalog = Path(temporary) / "catalog.json"
            catalog.write_bytes(b'{"number":' + b"1" * 129 + b"}")
            completed = self.run_verifier(catalog=catalog)
        report = self.assert_controlled_failure(completed)
        self.assertIn("integer token exceeds", report["error"])

    def test_unexpected_internal_exception_has_no_traceback_or_detail(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "diagnostic_candidate_verifier_under_test", VERIFIER
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        stdout = io.StringIO()
        stderr = io.StringIO()
        with mock.patch.object(
            module, "verify", side_effect=RuntimeError("secret internal detail")
        ), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            return_code = module.main(["--json"])
        self.assertEqual(return_code, 1)
        output = stdout.getvalue() + stderr.getvalue()
        self.assertNotIn("Traceback", output)
        self.assertNotIn("secret internal detail", output)
        report = json.loads(stdout.getvalue())
        self.assertEqual(
            report["error"], "unexpected internal verification failure"
        )

    def test_text_mode_marks_result_review_only(self) -> None:
        completed = self.run_verifier(json_output=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("review verification: PASS", completed.stdout)
        self.assertIn("review-only", completed.stdout)
        self.assertIn("243 emitters in 41 functions", completed.stdout)


if __name__ == "__main__":
    unittest.main()
