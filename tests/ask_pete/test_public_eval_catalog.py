import json
from pathlib import Path
from unittest import TestCase

from services.ai_foundation import AnswerExpectation, AnswerState, Purpose
from services.ask_pete.classification import classify_public_purpose
from services.ask_pete.manifest import load_public_source_catalog


ROOT = Path(__file__).resolve().parents[2]
EVAL_PATH = Path(__file__).with_name("public_eval_cases.json")


class PublicEvaluationCatalogTests(TestCase):
    def test_catalog_is_complete_classifiable_and_bound_to_public_context(self) -> None:
        document = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
        self.assertEqual(document["schema_version"], "ask-pete-public-evals.v1")
        cases = document["cases"]
        self.assertGreaterEqual(len(cases), 9)
        self.assertEqual(len({case["case_id"] for case in cases}), len(cases))

        source_catalog = load_public_source_catalog(
            manifest_path=ROOT / "data" / "ai_sources" / "ask_pete_public_v1.json",
            resume_path=ROOT / "static" / "data" / "resume_data.json",
        )
        public_contexts = {
            record.locator.context_key for record in source_catalog.records
        }
        expected_fields = {
            "case_id",
            "question",
            "requested_action",
            "context_key",
            "expected_purpose",
            "allowed_states",
            "minimum_claims",
            "minimum_citations",
            "minimum_follow_ups",
            "requires_boundary",
            "requires_handoff",
        }
        for case in cases:
            self.assertEqual(set(case), expected_fields)
            purpose = classify_public_purpose(
                case["question"],
                requested_action=case["requested_action"],
            )
            self.assertIs(purpose, Purpose(case["expected_purpose"]))
            if case["context_key"] is not None:
                self.assertIn(case["context_key"], public_contexts)
            expectation = AnswerExpectation(
                allowed_states=frozenset(
                    AnswerState(value) for value in case["allowed_states"]
                ),
                minimum_claims=case["minimum_claims"],
                minimum_citations=case["minimum_citations"],
                minimum_follow_ups=case["minimum_follow_ups"],
                requires_boundary=case["requires_boundary"],
                requires_handoff=case["requires_handoff"],
            )
            self.assertTrue(expectation.allowed_states)

    def test_catalog_preserves_the_five_recruiter_quality_questions(self) -> None:
        cases = json.loads(EVAL_PATH.read_text(encoding="utf-8"))["cases"]
        case_ids = {case["case_id"] for case in cases}
        self.assertTrue(
            {
                "recruiter-brief-flagship",
                "systems-engineering-evidence",
                "measurable-results",
                "mbse-and-requirements",
                "first-interview-preparation",
            }
            <= case_ids
        )
