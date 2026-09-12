"""Parametric entrance-policy checks for MVP1 increment C.

These prove the boundary, not the product decision: Resume onboarding's
numbers are synthetic fixtures, durable onboarding persistence is withheld,
and My Data's already accepted limits are represented separately.
"""

from __future__ import annotations

import unittest

from services.my_opportunities.member_import_service import _DOCX_CONTENT_TYPE
from services.resume_intake_policy import (
    ENTRANCE_MY_DATA,
    ENTRANCE_RESUME_ONBOARDING,
    FIXTURE_RESUME_ONBOARDING_POLICY,
    MY_DATA_POLICY,
    RECOMMENDED_ONBOARDING_DECISION,
    SELECTED_RESUME_ONBOARDING_POLICY,
    IntakePolicyError,
    fixture_policy_for_tests,
    resolve_policy,
    selected_policy_for_tests,
    sweep_parameters,
)


class ResumeIntakePolicyTests(unittest.TestCase):
    def test_onboarding_policy_is_an_unselected_labelled_fixture(self):
        fixture = FIXTURE_RESUME_ONBOARDING_POLICY
        self.assertEqual(fixture.entrance, ENTRANCE_RESUME_ONBOARDING)
        self.assertFalse(fixture.selected)
        self.assertTrue(fixture.fixture)
        self.assertTrue(fixture.fixture_only)
        self.assertIn("SYNTHETIC FIXTURE", fixture.label)
        self.assertIn("not selected", fixture.pending_decision)
        self.assertFalse(fixture.durable_persistence_allowed)
        document = fixture.as_document()
        self.assertFalse(document["durable_persistence_allowed"])
        self.assertFalse(document["selected"])

    def test_no_resume_onboarding_policy_is_selected_yet(self):
        self.assertIsNone(SELECTED_RESUME_ONBOARDING_POLICY)
        resolved = resolve_policy(ENTRANCE_RESUME_ONBOARDING)
        self.assertFalse(resolved.durable_persistence_allowed)

    def test_my_data_policy_is_selected_and_distinct(self):
        self.assertTrue(MY_DATA_POLICY.selected)
        self.assertFalse(MY_DATA_POLICY.fixture)
        self.assertTrue(MY_DATA_POLICY.durable_persistence_allowed)
        self.assertEqual(MY_DATA_POLICY.max_document_bytes, 10_000_000)
        self.assertEqual(MY_DATA_POLICY.max_recording_seconds, 180.0)
        self.assertEqual(MY_DATA_POLICY.draft_inactivity_days, 30)
        self.assertTrue(MY_DATA_POLICY.cleanup_audio_after_transcription)
        self.assertIn(_DOCX_CONTENT_TYPE, MY_DATA_POLICY.allowed_document_types)
        self.assertNotEqual(
            resolve_policy(ENTRANCE_MY_DATA).entrance,
            resolve_policy(ENTRANCE_RESUME_ONBOARDING).entrance,
        )

    def test_unknown_entrance_fails_closed(self):
        with self.assertRaises(IntakePolicyError):
            resolve_policy("visitor")
        with self.assertRaises(IntakePolicyError):
            resolve_policy(None)

    def test_policy_is_parametric_for_limits(self):
        tiny = fixture_policy_for_tests(max_document_bytes=32, max_recording_seconds=1.5)
        limits = tiny.import_limits()
        self.assertEqual(limits.max_upload_bytes, 32)
        self.assertEqual(tiny.max_recording_seconds, 1.5)
        self.assertEqual(limits.max_extracted_units, tiny.max_text_units)
        # The fixture's value changes; the base constant is untouched.
        self.assertEqual(
            FIXTURE_RESUME_ONBOARDING_POLICY.max_document_bytes, 10_000_000
        )

    def test_test_selected_policy_enables_durability_without_mutating_module_state(self):
        selected = selected_policy_for_tests(max_text_units=123)
        self.assertTrue(selected.durable_persistence_allowed)
        self.assertFalse(SELECTED_RESUME_ONBOARDING_POLICY is selected)
        self.assertIsNone(SELECTED_RESUME_ONBOARDING_POLICY)
        self.assertEqual(selected.max_text_units, 123)

    def test_recommendation_names_the_remaining_decision(self):
        self.assertIn("retention", RECOMMENDED_ONBOARDING_DECISION["decision"].lower())
        self.assertIn("10,000,000", RECOMMENDED_ONBOARDING_DECISION["recommendation"])
        self.assertIn("disabled", RECOMMENDED_ONBOARDING_DECISION["why_it_matters"])

    def test_audio_has_its_own_parametric_byte_ceiling(self):
        self.assertNotEqual(MY_DATA_POLICY.max_recording_bytes, MY_DATA_POLICY.max_document_bytes)
        self.assertEqual(MY_DATA_POLICY.max_recording_bytes, 20 * 1024 * 1024)
        smaller = fixture_policy_for_tests(max_recording_bytes=4096)
        self.assertEqual(smaller.max_recording_bytes, 4096)
        # The document ceiling is untouched by the audio override.
        self.assertEqual(smaller.max_document_bytes, 10_000_000)
        self.assertEqual(smaller.as_document()["max_recording_bytes"], 4096)

    def test_retention_sweep_is_unscheduled_while_onboarding_is_unselected(self):
        fixture = sweep_parameters(FIXTURE_RESUME_ONBOARDING_POLICY)
        self.assertFalse(fixture["scheduled"])
        self.assertIsNone(fixture["inactivity_days"])
        self.assertEqual(fixture["reason"], "policy_not_selected")
        self.assertEqual(fixture["entrance"], ENTRANCE_RESUME_ONBOARDING)
        selected = sweep_parameters(selected_policy_for_tests())
        self.assertTrue(selected["scheduled"])
        self.assertEqual(selected["inactivity_days"], 30)
        self.assertEqual(selected["entrance"], ENTRANCE_RESUME_ONBOARDING)
        self.assertEqual(
            sweep_parameters(MY_DATA_POLICY)["entrance"], ENTRANCE_MY_DATA
        )


if __name__ == "__main__":
    unittest.main()
