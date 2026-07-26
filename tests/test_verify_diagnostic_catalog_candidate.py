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


    # ------------------------------------------------------------------
    # Semantic guards.  Each case perturbs one input and asserts the guard
    # reacts; a guard that never fires would be worse than none, because it
    # would look like coverage.
    # ------------------------------------------------------------------

    def assert_guard_failure(
        self, completed: "subprocess.CompletedProcess[str]", guard: str, fragment: str
    ) -> None:
        self.assertEqual(completed.returncode, 1, completed.stdout)
        report = json.loads(completed.stdout)
        self.assertEqual(report["status"], "FAIL")
        self.assertIn(guard, report["error"])
        self.assertIn(fragment, report["error"])

    def test_report_exposes_semantic_guard_counts(self) -> None:
        completed = self.run_verifier()
        self.assertEqual(completed.returncode, 0, completed.stderr)
        counts = json.loads(completed.stdout)["semantic_guard_counts"]
        self.assertEqual(counts["callsite_selectors_checked"], 234)
        # 358 finding bindings plus the 25 check-completion-evidence rows,
        # which bind a check directly and are subject to the same reachability
        # rule.
        self.assertEqual(counts["finding_producer_bindings_checked"], 383)
        # Pinned deliberately: this count carries the honesty property of the
        # whole mechanism.  Leaving it unpinned would let a real new defect be
        # silenced by pasting its key into the table with nothing to notice.
        self.assertEqual(counts["known_defects_recorded"], 29)

    def test_widening_allowed_kinds_retires_the_recorded_reachability_defects(
        self,
    ) -> None:
        """F0102's three adopter-side producers are recorded as unreachable.

        Allowing profile.schema-conformance to run as ADOPTER_SNAPSHOT makes
        load_adopter_schemas reachable, so the recorded defects must retire and
        the baseline must be updated rather than left stale.
        """

        def widen(catalog: dict) -> None:
            for check in catalog["public_checks"]:
                if check["check_id"] == "profile.schema-conformance":
                    check["allowed_evaluation_kinds"] = [
                        "ADOPTER_SNAPSHOT",
                        "CENTRAL_SELF_CHECK",
                    ]

        with CandidatePair(catalog_mutator=widen) as pair:
            completed = self.run_verifier(
                catalog=pair.catalog, mapping=pair.mapping
            )
        self.assert_guard_failure(
            completed, "evaluation_kind_reachability", "F0102:D-3253@3253"
        )

    def test_narrowing_allowed_kinds_strands_owned_findings(self) -> None:
        """Restricting a check to a kind its producers cannot reach fails closed.

        adoption.schema-conformance owns F0013/F0014, whose producers run only
        on the adopter path; forcing the check to CENTRAL_SELF_CHECK leaves
        them with no runnable owner.
        """

        def narrow(catalog: dict) -> None:
            for check in catalog["public_checks"]:
                if check["check_id"] == "adoption.schema-conformance":
                    check["allowed_evaluation_kinds"] = ["CENTRAL_SELF_CHECK"]

        with CandidatePair(catalog_mutator=narrow) as pair:
            completed = self.run_verifier(
                catalog=pair.catalog, mapping=pair.mapping
            )
        self.assert_guard_failure(
            completed, "evaluation_kind_reachability", "new semantic defect"
        )

    def test_relaxing_the_block_only_rule_retires_a_recorded_defect(self) -> None:
        def relax(catalog: dict) -> None:
            for entry in catalog["findings"]["allocated_entries"]:
                if entry["code"] == "F0018":
                    entry["context_effect_rules"] = [
                        {"when": "an advisory context", "gate_effect": "WARN"},
                        {
                            "when": "the registered condition is established",
                            "gate_effect": "BLOCK",
                        },
                    ]

        with CandidatePair(catalog_mutator=relax) as pair:
            completed = self.run_verifier(
                catalog=pair.catalog, mapping=pair.mapping
            )
        self.assert_guard_failure(
            completed, "gate_effect_recovery", "no longer present"
        )

    def test_new_warn_to_block_escalation_fails_closed(self) -> None:
        def escalate(catalog: dict) -> None:
            for entry in catalog["findings"]["allocated_entries"]:
                if entry["code"] == "F0030":
                    entry["context_effect_rules"] = [
                        {
                            "when": "the registered condition is established",
                            "gate_effect": "BLOCK",
                        }
                    ]

        with CandidatePair(catalog_mutator=escalate) as pair:
            completed = self.run_verifier(
                catalog=pair.catalog, mapping=pair.mapping
            )
        self.assert_guard_failure(
            completed, "gate_effect_recovery", "D-1626->F0030|warn-to-block"
        )

    def test_correcting_a_stale_selector_retires_a_recorded_defect(self) -> None:
        def correct(mapping: dict) -> None:
            for row in mapping["semantic_mapping"]["group_rows"]:
                if row["group_id"] != "U-1242":
                    continue
                for projection in (row.get("target") or {}).get("projections") or []:
                    if (
                        projection.get("callsite_selector")
                        == "load_yaml@4210 in check_stage_readiness"
                    ):
                        projection["callsite_selector"] = (
                            "load_yaml@4210 in check_adoption_stage"
                        )

        with CandidatePair(mapping_mutator=correct) as pair:
            completed = self.run_verifier(
                catalog=pair.catalog, mapping=pair.mapping
            )
        self.assert_guard_failure(
            completed, "callsite_selector_accuracy", "no longer present"
        )

    def test_dispatch_projections_resolve_at_their_own_callsite(self) -> None:
        """Reachability must use the projection's callsite, not the row's line.

        adoption.document-parse owns F0005-F0012, whose rows cite shared
        loaders (`load_yaml`, `load_json`) that every entrypoint can reach.
        Judged from those shared lines the comparison is vacuous; judged at the
        dispatched callsites the findings are adopter-only, so restricting the
        check to CENTRAL_SELF_CHECK must strand them.
        """

        def narrow(catalog: dict) -> None:
            for check in catalog["public_checks"]:
                if check["check_id"] == "adoption.document-parse":
                    check["allowed_evaluation_kinds"] = ["CENTRAL_SELF_CHECK"]

        with CandidatePair(catalog_mutator=narrow) as pair:
            completed = self.run_verifier(
                catalog=pair.catalog, mapping=pair.mapping
            )
        self.assert_guard_failure(
            completed, "evaluation_kind_reachability", "new semantic defect"
        )

    def test_missing_allowed_evaluation_kinds_cannot_bypass_the_guard(self) -> None:
        def drop(catalog: dict) -> None:
            for check in catalog["public_checks"]:
                if check["check_id"] == "adoption.schema-conformance":
                    del check["allowed_evaluation_kinds"]

        with CandidatePair(catalog_mutator=drop) as pair:
            completed = self.run_verifier(
                catalog=pair.catalog, mapping=pair.mapping
            )
        self.assertEqual(completed.returncode, 1, completed.stdout)
        self.assertIn(
            "allowed_evaluation_kinds", json.loads(completed.stdout)["error"]
        )

    def test_empty_allowed_evaluation_kinds_cannot_bypass_the_guard(self) -> None:
        def empty(catalog: dict) -> None:
            for check in catalog["public_checks"]:
                if check["check_id"] == "adoption.schema-conformance":
                    check["allowed_evaluation_kinds"] = []

        with CandidatePair(catalog_mutator=empty) as pair:
            completed = self.run_verifier(
                catalog=pair.catalog, mapping=pair.mapping
            )
        self.assertEqual(completed.returncode, 1, completed.stdout)
        self.assertIn(
            "declares no allowed_evaluation_kinds",
            json.loads(completed.stdout)["error"],
        )

    def test_inert_fact_property_cannot_silence_the_escalation_guard(self) -> None:
        """A BLOCK-only finding has no WARN rule for any fact to select."""

        def escalate(catalog: dict) -> None:
            for entry in catalog["findings"]["allocated_entries"]:
                if entry["code"] == "F0030":
                    entry["context_effect_rules"] = [
                        {
                            "when": "the registered condition is established",
                            "gate_effect": "BLOCK",
                        }
                    ]
                    entry["fact_schema"] = {
                        "closed": True,
                        "null_allowed": False,
                        "properties": {"inert": {"type": "string", "enum": ["X"]}},
                        "required": [],
                    }

        with CandidatePair(catalog_mutator=escalate) as pair:
            completed = self.run_verifier(
                catalog=pair.catalog, mapping=pair.mapping
            )
        self.assert_guard_failure(
            completed, "gate_effect_recovery", "D-1626->F0030|warn-to-block"
        )

    def test_error_demoted_to_warn_only_fails_closed(self) -> None:
        """The de-escalation rule must be able to fire, not just exist."""

        def demote(catalog: dict) -> None:
            for entry in catalog["findings"]["allocated_entries"]:
                if entry["code"] == "F0013":
                    entry["context_effect_rules"] = [
                        {
                            "when": "the registered condition is established",
                            "gate_effect": "WARN",
                        }
                    ]

        with CandidatePair(catalog_mutator=demote) as pair:
            completed = self.run_verifier(
                catalog=pair.catalog, mapping=pair.mapping
            )
        self.assert_guard_failure(
            completed, "gate_effect_recovery", "|error-to-warn"
        )

    def test_via_clause_naming_an_unknown_function_fails_closed(self) -> None:
        def tamper(mapping: dict) -> None:
            for row in mapping["semantic_mapping"]["group_rows"]:
                for projection in (row.get("target") or {}).get("projections") or []:
                    selector = projection.get("callsite_selector") or ""
                    if " via " in selector and "@" in selector.split(" via ")[1]:
                        projection["callsite_selector"] = (
                            selector.split(" via ")[0]
                            + " via totally_made_up_name@6763"
                        )
                        return

        with CandidatePair(mapping_mutator=tamper) as pair:
            completed = self.run_verifier(
                catalog=pair.catalog, mapping=pair.mapping
            )
        self.assert_guard_failure(
            completed, "callsite_selector_accuracy", "via-nonexistent"
        )

    @staticmethod
    def _set_first_selector(group_id: str, value: str):
        """Replace the first callsite selector of one semantic group."""

        def mutator(mapping: dict) -> None:
            for row in mapping["semantic_mapping"]["group_rows"]:
                if row["group_id"] != group_id:
                    continue
                projections = (row.get("target") or {}).get("projections") or []
                if projections:
                    projections[0]["callsite_selector"] = value

        return mutator

    def test_module_scope_enclosing_claim_fails_closed(self) -> None:
        """Reachable through ordinary input on a non-finding-bound selector.

        `collect_finding_source_bindings` pins only the selectors above FINDING
        leaves; U-1251's projections are not pinned, so the guard is the check
        of record for them.
        """

        with CandidatePair(
            mapping_mutator=self._set_first_selector(
                "U-1251", "compile@98 in totally_fake_fn"
            )
        ) as pair:
            completed = self.run_verifier(
                catalog=pair.catalog, mapping=pair.mapping
            )
        self.assert_guard_failure(
            completed, "callsite_selector_accuracy", "enclosing-module-scope"
        )

    def test_trailing_dot_cannot_silence_the_enclosing_claim(self) -> None:
        """One character must not disable every enclosing branch."""

        with CandidatePair(
            mapping_mutator=self._set_first_selector(
                "U-1251", "load_yaml@2833 in check_artifacts."
            )
        ) as pair:
            completed = self.run_verifier(
                catalog=pair.catalog, mapping=pair.mapping
            )
        self.assert_guard_failure(
            completed, "callsite_selector_accuracy", "enclosing-unparseable"
        )

    def test_unknown_dotted_qualifier_fails_closed(self) -> None:
        with CandidatePair(
            mapping_mutator=self._set_first_selector(
                "U-1251", "load_yaml@2833 in wrong_outer.check_artifacts"
            )
        ) as pair:
            completed = self.run_verifier(
                catalog=pair.catalog, mapping=pair.mapping
            )
        self.assert_guard_failure(
            completed, "callsite_selector_accuracy", "enclosing-qualifier"
        )

    def test_renaming_a_completion_leaf_kind_cannot_drop_coverage(self) -> None:
        """Leaf kinds carry no closed vocabulary, so the count is pinned.

        Renaming the kind previously removed the row from both the leaf
        validation and the new reachability coverage, silently.
        """

        def rename(mapping: dict) -> None:
            for row in mapping["semantic_mapping"]["group_rows"]:
                target = row.get("target") or {}
                if target.get("kind") == "CHECK_COMPLETION_EVIDENCE":
                    target["kind"] = "CHECK_COMPLETION_EVIDENCE_RENAMED"
                    return

        with CandidatePair(mapping_mutator=rename) as pair:
            completed = self.run_verifier(
                catalog=pair.catalog, mapping=pair.mapping
            )
        self.assertEqual(completed.returncode, 1, completed.stdout)
        self.assertIn(
            "check-completion evidence leaves",
            json.loads(completed.stdout)["error"],
        )

    def test_real_dotted_nesting_is_not_a_defect(self) -> None:
        """Pins the non-defect so the qualifier rule cannot over-fire."""

        spec = importlib.util.spec_from_file_location(
            "diagnostic_candidate_verifier_selector_branch_test",
            VERIFIER,
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        source = subprocess.run(
            [
                "git",
                "show",
                "00e2fe46d4eb01a4147f149851a48a3017cbb796:scripts/validate.py",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            check=True,
        ).stdout
        reach = module.analyze_semantic_reachability(source)

        def probe(selector: str) -> set:
            mapping = {
                "semantic_mapping": {
                    "group_rows": [
                        {
                            "group_id": "T",
                            "target": {"projections": [{"callsite_selector": selector}]},
                        }
                    ]
                }
            }
            defects, _ = module.guard_callsite_selector_accuracy(mapping, reach)
            return defects

        # A real nested definition must not be flagged; the qualifier rule has
        # to accept the nesting chain it was written for.
        self.assertEqual(
            probe("read_project_text_file@3669 in check_required_files.require"), set()
        )
        # And the innermost-segment comparison still holds on its own.
        self.assertEqual(probe("read_project_text_file@3669 in require"), set())

    def test_dropping_the_typed_reference_contract_cannot_bypass_terminal_checks(
        self,
    ) -> None:
        """`schema_version: 2` IS the typed regime, so its contract is required.

        Omitting it previously routed every family into the pre-typed branch,
        which skipped the legacy-key rejection and every owner, finding, reason
        and catalog-membership check.  `target_check` is validated nowhere
        else, so a family could name a check that does not exist.
        """

        def tamper(mapping: dict) -> None:
            terminal = mapping["terminal_mapping"]
            terminal.pop("typed_reference_contract", None)
            for family in terminal["families"]:
                family.pop("target_owner_ref", None)
                family.pop("finding_source_ref", None)
                family.pop("reason_source_refs", None)
                family["target_check"] = "assurance.NOT-A-REAL-CHECK"
            # Keep the coverage summary consistent, which is what made the
            # original bypass reachable.
            terminal["coverage_summary"]["reason_code_count"] = 0

        with CandidatePair(mapping_mutator=tamper) as pair:
            completed = self.run_verifier(
                catalog=pair.catalog, mapping=pair.mapping
            )
        self.assertEqual(completed.returncode, 1, completed.stdout)
        self.assertIn(
            "typed_reference_contract", json.loads(completed.stdout)["error"]
        )

    def test_condition_predicate_operand_must_be_a_declared_fact(self) -> None:
        """An operand that is not a declared fact makes the predicate unusable.

        Dropping the fact from the catalog schema and from the row's bindings
        consistently used to pass, leaving F0002's immutable predicate naming a
        value the finding can no longer carry.
        """

        def drop_fact(catalog: dict) -> None:
            for entry in catalog["findings"]["allocated_entries"]:
                if entry["code"] != "F0002":
                    continue
                schema = entry["fact_schema"]
                schema["properties"].pop("head_stage", None)
                schema["required"] = [
                    key for key in schema["required"] if key != "head_stage"
                ]

        def drop_binding(mapping: dict) -> None:
            for row in mapping["semantic_mapping"]["group_rows"]:
                if row["group_id"] != "PHASE0-F0002":
                    continue
                bindings = row["target"]["fact_bindings"]
                bindings["required_key_set"] = [
                    key
                    for key in bindings["required_key_set"]
                    if key != "head_stage"
                ]
                bindings["bindings"].pop("head_stage", None)

        with CandidatePair(
            catalog_mutator=drop_fact, mapping_mutator=drop_binding
        ) as pair:
            completed = self.run_verifier(
                catalog=pair.catalog, mapping=pair.mapping
            )
        self.assertEqual(completed.returncode, 1, completed.stdout)
        self.assertIn(
            "not a declared fact", json.loads(completed.stdout)["error"]
        )

    def test_missing_context_effect_rules_cannot_bypass_the_guard(self) -> None:
        """An absent rule list would match no effect set and silence the guard."""

        def drop(catalog: dict) -> None:
            for entry in catalog["findings"]["allocated_entries"]:
                if entry["code"] == "F0030":
                    del entry["context_effect_rules"]

        with CandidatePair(catalog_mutator=drop) as pair:
            completed = self.run_verifier(
                catalog=pair.catalog, mapping=pair.mapping
            )
        self.assertEqual(completed.returncode, 1, completed.stdout)
        self.assertIn(
            "context_effect_rules", json.loads(completed.stdout)["error"]
        )

    def test_empty_context_effect_rules_cannot_bypass_the_guard(self) -> None:
        def empty(catalog: dict) -> None:
            for entry in catalog["findings"]["allocated_entries"]:
                if entry["code"] == "F0035":
                    entry["context_effect_rules"] = []

        with CandidatePair(catalog_mutator=empty) as pair:
            completed = self.run_verifier(
                catalog=pair.catalog, mapping=pair.mapping
            )
        self.assertEqual(completed.returncode, 1, completed.stdout)
        self.assertIn(
            "declares no context_effect_rules",
            json.loads(completed.stdout)["error"],
        )

    def test_unregistered_gate_effect_fails_closed(self) -> None:
        def tamper(catalog: dict) -> None:
            for entry in catalog["findings"]["allocated_entries"]:
                if entry["code"] == "F0030":
                    entry["context_effect_rules"] = [
                        {"when": "always", "gate_effect": "ADVISORY"}
                    ]

        with CandidatePair(catalog_mutator=tamper) as pair:
            completed = self.run_verifier(
                catalog=pair.catalog, mapping=pair.mapping
            )
        self.assertEqual(completed.returncode, 1, completed.stdout)
        self.assertIn(
            "unregistered gate effect", json.loads(completed.stdout)["error"]
        )

    def test_bogus_selector_line_fails_closed(self) -> None:
        def tamper(mapping: dict) -> None:
            for row in mapping["semantic_mapping"]["group_rows"]:
                if row["group_id"] != "U-1242":
                    continue
                for projection in (row.get("target") or {}).get("projections") or []:
                    selector = projection.get("callsite_selector") or ""
                    if selector.startswith("load_yaml@4210"):
                        projection["callsite_selector"] = (
                            "load_yaml@9999 in check_adoption_stage"
                        )

        with CandidatePair(mapping_mutator=tamper) as pair:
            completed = self.run_verifier(
                catalog=pair.catalog, mapping=pair.mapping
            )
        self.assert_guard_failure(
            completed, "callsite_selector_accuracy", "new semantic defect"
        )


if __name__ == "__main__":
    unittest.main()
