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
    'test_ai_unavailable_keeps_words_and_no_fake_progress',
    'test_cancel_fences_old_transcript_and_late_transcript_appends_new_words',
    'test_clear_controls_never_offer_required_fields',
    'test_contextual_question_is_explicit_revision_bound_and_never_saved',
    'test_corrections_survive_back_and_reopen_without_silent_save',
    'test_education_credential_statuses_are_member_choices_in_manual_and_review',
    'test_existing_entry_correction_preserves_unspecified_values_and_permissions',
    'test_finish_is_explicit_private_and_manual_remains_available',
    'test_finish_without_unsent_input_has_no_false_reminder',
    'test_grouped_correction_preserves_dates_and_reveals_only_after_confirmation',
    'test_impact_parent_choice_survives_back_review_and_reopen',
    'test_impact_requires_owner_private_role_and_parent_refresh_after_confirmation',
    'test_leaving_recording_stops_tracks_and_holds_audio_until_explicit_transcribe',
    'test_lost_add_freezes_request_bytes_and_keeps_newer_typing',
    'test_lost_decision_and_malformed_success_retry_exact_confirmation',
    'test_lost_guide_completion_keeps_exact_choice_and_finish_is_acknowledged',
    'test_manual_dates_currentness_reload_editor_and_privacy',
    'test_manual_save_never_submits_guide_words_or_attachment',
    'test_many_proposals_are_reviewed_one_group_at_a_time_and_discard_is_not_save',
    'test_microphone_permission_failure_and_pending_leave_preserve_manual_input',
    'test_missing_or_unsupported_status_requires_choice_without_invention',
    'test_phone_narrow_keyboard_and_reduced_motion',
    'test_proposals_preserve_approximate_and_unknown_date_precision',
    'test_real_file_bytes_mixed_review_failure_and_remove_preserve_other_input',
    'test_recording_recovery_required_is_terminal_and_retains_typing',
    'test_recording_retry_keeps_original_metadata_after_second_recording',
    'test_refused_add_releases_key_and_offline_keeps_input',
    'test_repeated_question_is_suppressed_in_active_flow',
    'test_slow_add_busy_status_follows_manual_escape_and_preserves_new_typing',
    'test_story_destination_and_repeated_question_use_existing_controls',
    'test_uncertain_words_require_member_type_choice',
    'test_welcome_has_benefits_equal_actions_real_document_and_no_provider_work',
    'test_workspace_failure_is_not_treated_as_first_use',
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
