"""Required G journeys and retained C intake journeys; missing/changed/skipped tests fail."""
from pathlib import Path
import json
import os
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.run_resume_media_browser_tests import (BrowserCiError, load_selected_suite,
    execute_suite, resolve_browser_executable)

EXPECTED_METHODS = (
    'test_my_data_sharing_status_on_off_and_unavailable',
    'test_cancelled_late_transcription_preserves_newer_typed_input',
    'test_unsupported_document_storage_failure_and_rejected_scan_are_honest',
    'test_library_illustration_never_becomes_biographical_ai_evidence',
    'test_profile_then_explicit_resume_permissions_and_guest_name',
    'test_owner_b_and_guest_cannot_read_owner_a_private_preview',
    'test_saved_draft_ai_preview_is_private_and_fenced_after_provider',
    'test_intake_role_two_strengths_private_reload_and_guide',
    'test_four_permission_combinations_guest_six_questions_and_citation_revocation',
    'test_story_requires_deliberate_binding_and_display_does_not_grant_ai',
    'test_two_photo_uploads_crop_swap_private_save_publish_and_story_mask',
    'test_my_data_correction_wins_over_stale_editor_and_restore_stays_private',
    'test_separately_seeded_stage_07_story_off_ai_off',
    'test_separately_seeded_stage_09_story_on_ai_off',
    'test_cardinality_empty_resume',
    'test_cardinality_one_of_each',
    'test_cardinality_several_roles_events',
    'test_cardinality_dense_roles_education_events',
    'test_document_typed_recording_proposal_review_private_save_and_source_removal',
    'test_abuse_limit_and_provider_database_failures_preserve_question_and_publication',
    'test_foreign_entry_parent_photo_and_invalid_cursor_are_denied',
    'test_private_assistance_exclusion_is_independent_of_visitor_permissions',
    'test_thirty_day_recovery_boundary_and_failed_cleanup_retry',
    'test_lost_editor_save_response_retries_same_command_and_retains_words',
    'test_lost_publish_response_retries_exact_receipt_without_reenabling_sharing',
)

INTAKE_METHODS = (
    'test_member_dates_and_boolean_currentness_save_reload_and_editor_remain_faithful',
    'test_remove_refused_file_preserves_new_text_queued_fact_and_other_attachment',
    'test_mixed_add_reaches_flask_and_reports_a_truthful_receipt',
    'test_guide_hide_reopen_preserves_unfinished_text',
    'test_in_field_microphone_inserts_without_overwriting_typing',
    'test_mobile_composition_reflows_without_horizontal_overflow',
    'test_mixed_saved_failed_and_review_items_clear_only_acknowledged_inputs',
    'test_newer_typing_during_a_slow_add_is_never_discarded',
    'test_lost_response_retries_the_same_request_without_duplicates',
    'test_mobile_sheet_dismiss_and_reopen_preserves_queued_and_attached_input',
    'test_proposal_list_renders_empty_few_and_many',
    'test_two_hundred_percent_reflow_has_no_horizontal_overflow',
    'test_clear_affordance_never_offers_a_required_field',
    'test_lost_recording_response_retries_with_the_same_request_and_content',
    'test_earlier_recording_retry_keeps_its_request_after_a_second_recording',
    'test_lost_guide_response_retries_with_the_same_request',
    'test_education_and_credential_add_and_proposal_accept_use_member_status_choices',
    'test_impact_requires_an_owner_parent',
)


def selected_suite():
    return unittest.TestSuite([
        load_selected_suite(ROOT / 'tests/test_mvp1_acceptance_browser.py',
            'required_mvp1_acceptance_browser', 'Mvp1AcceptanceBrowserTests', EXPECTED_METHODS),
        load_selected_suite(ROOT / 'tests/test_resume_intake_browser.py',
            'required_mvp1_retained_intake_browser', 'ResumeIntakeBrowserTests', INTAKE_METHODS),
    ])


def main():
    expected = len(EXPECTED_METHODS) + len(INTAKE_METHODS)
    try:
        os.environ['PEERSLATE_CHROME'] = str(resolve_browser_executable())
        ok, summary = execute_suite(selected_suite(), expected)
    except Exception as error:
        ok, summary = False, {'status': 'fail', 'expected': expected, 'reason': str(error)}
    print('MVP1_ACCEPTANCE_BROWSER_CI_SUMMARY=' + json.dumps(summary, sort_keys=True))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
