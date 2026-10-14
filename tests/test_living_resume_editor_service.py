import hashlib
import json
import unittest
from datetime import date
from unittest.mock import MagicMock

from services.database_service import DatabaseServiceError
from services.living_resume_editor_service import (
    LivingResumeEditorConflictError,
    LivingResumeEditorService,
    LivingResumeEditorUnavailableError,
    LivingResumeEditorValidationError,
    normalize_command,
    save_mode_for_record,
    utf16_length,
)


COMMAND_ID = "00000000-0000-4000-8000-000000000001"
RECORD_KEY = "00000000-0000-4000-8000-000000000002"
PARENT_KEY = "00000000-0000-4000-8000-000000000003"
VERSION = "000000000000002a"


def role_payload(**overrides):
    payload = {
        "command_id": COMMAND_ID,
        "type": "create_role",
        "record_key": RECORD_KEY,
        "parent_key": None,
        "expected_version": None,
        "values": {
            "role_title": "Engineer",
            "employer_name": "PeerSlate",
            "location_text": None,
            "summary": "Built private tools",
            "start_date": "2026-09-06",
            "end_date": None,
            "date_precision": "month",
            "employment_type": "full_time",
            "current_role": True,
        },
    }
    payload.update(overrides)
    return payload


class GuideLocalTypeTests(unittest.TestCase):
    def test_planned_and_in_progress_guide_credentials_save_without_a_year_and_refuse_explicit_dates(self):
        from copy import deepcopy
        from uuid import uuid4
        from services.living_resume_editor_service import guide_required_fields
        from services.resume_draft_service import ResumeDraftValidationError
        from tests.mvp1_acceptance_support import SharedMvp1Fixture
        for status in ('planned', 'in_progress'):
            for kind in ('certification', 'license', 'publication'):
                with self.subTest(status=status, kind=kind):
                    shared, owner = SharedMvp1Fixture(), 'credential-status-fictional'
                    values = {'qualification_kind': kind, 'name': 'Fictional qualification',
                        'issuer': 'Fictional Institute', 'completion_status': status}
                    original = deepcopy(values)
                    self.assertEqual(guide_required_fields('credential', values), [])
                    saved = shared.draft.commit(owner, {'type': 'create_private_item',
                        'request_id': str(uuid4()), 'record_key': str(uuid4()),
                        'record_type': 'credential', 'values': values, 'guide_review': True})
                    self.assertEqual(saved['outcome'], 'created')
                    self.assertFalse(saved['publishes'])
                    current = shared.canonical.get_item(owner, saved['item']['record_key'])
                    self.assertEqual(current['values']['completion_status'], status)
                    self.assertEqual(current['values']['name'], values['name'])
                    self.assertEqual(current['values']['issuer'], values['issuer'])
                    self.assertIsNone(current['values']['issue_date'])
                    self.assertIsNone(current['values']['expiration_date'])
                    self.assertFalse(current['resume_display'])
                    self.assertFalse(current['visitor_ai'])
                    self.assertEqual(values, original)
                    before = tuple(deepcopy(store.load_owner(owner)) for store in
                        (shared.policy.repository, shared.draft.repository, shared.publication.repository))
                    for field in ('issue_date', 'expiration_date'):
                        with self.subTest(field=field):
                            supplied = {**values, field: '2030'}
                            exact = deepcopy(supplied)
                            with self.assertRaisesRegex(ResumeDraftValidationError,
                                    'cannot have issue or expiration dates'):
                                shared.draft.commit(owner, {'type': 'create_private_item',
                                    'request_id': str(uuid4()), 'record_key': str(uuid4()),
                                    'record_type': 'credential', 'values': supplied, 'guide_review': True})
                            self.assertEqual(supplied, exact)
                            self.assertEqual(before, tuple(store.load_owner(owner) for store in
                                (shared.policy.repository, shared.draft.repository, shared.publication.repository)))

    def test_noncompleted_guide_credentials_keep_membership_name_exception_and_completed_date_essential(self):
        from services.living_resume_editor_service import guide_required_fields, normalize_guide_values
        for status in ('planned', 'in_progress'):
            with self.subTest(status=status):
                values = {'qualification_kind': 'membership', 'issuer': 'Fictional Guild',
                    'completion_status': status}
                self.assertEqual(guide_required_fields('credential', values), [])
                normalized = normalize_guide_values('credential', values)
                self.assertIsNone(normalized['name'])
                self.assertIsNone(normalized['issue_date'])
                self.assertEqual(guide_required_fields('credential', {**values, 'issuer': ' '}), ['issuer'])
        for status in (None, 'completed'):
            values = {'name': 'Fictional qualification', 'issuer': 'Fictional Institute'}
            if status is not None:
                values['completion_status'] = status
            self.assertEqual(guide_required_fields('credential', values), ['issue_date'])
        for field in ('name', 'issuer'):
            values = {'name': 'Fictional qualification', 'issuer': 'Fictional Institute',
                'completion_status': 'planned', field: ' '}
            self.assertEqual(guide_required_fields('credential', values), [field])


        for status in ([], {}):
            with self.subTest(invalid_status=status):
                with self.assertRaises(LivingResumeEditorValidationError):
                    normalize_guide_values('credential', {'name': 'Fictional qualification',
                        'issuer': 'Fictional Institute', 'issue_date': '2030', 'completion_status': status})

    def test_one_guide_essentials_table_requires_only_the_approved_fields(self):
        from services import living_resume_editor_service as editor
        required = getattr(editor, "guide_required_fields", None)
        self.assertTrue(callable(required))
        cases = (("credential", {"name": "Fictional credential", "issuer": "Fictional Institute", "issue_date": "2022"}, ["name", "issuer", "issue_date"]),
            ("credential", {"qualification_kind": "publication", "name": "Fictional paper", "issuer": "Fictional Press", "issue_date": "2022"}, ["name", "issuer", "issue_date"]),
            ("credential", {"qualification_kind": "membership", "issuer": "Fictional Guild", "issue_date": "2022"}, ["issuer", "issue_date"]),
            ("education", {"institution_name": "Fictional University", "end_date": "2024"}, ["institution_name", "end_date"]),
            ("project", {"project_name": "Fictional Orchard", "summary": "Fictional work."}, ["project_name", "summary"]),
            ("skill", {"name": "Fictional skill"}, ["name"]))
        for kind, values, fields in cases:
            with self.subTest(kind=kind, values=values):
                self.assertEqual(required(kind, values), [])
                for field in fields:
                    self.assertEqual(required(kind, {**values, field: " "}), [field])

    def test_guide_years_normalize_precisely_without_invented_titles_or_optional_questions(self):
        from services import living_resume_editor_service as editor
        normalize = getattr(editor, "normalize_guide_values", None)
        self.assertTrue(callable(normalize))
        education = normalize("education", {"institution_name": "Fictional University", "end_date": "2024", "degree_name": ""})
        self.assertEqual((education["end_date"], education["date_precision"]), ("2024-01-01", "year"))
        self.assertIsNone(education["title"])
        self.assertIsNone(education["degree_name"])
        membership = normalize("credential", {"qualification_kind": "membership", "issuer": "Fictional Guild", "issue_date": "2022"})
        self.assertEqual((membership["issue_date"], membership["issue_date_precision"]), ("2022-01-01", "year"))
        self.assertIsNone(membership["name"])
        self.assertEqual(membership["completion_status"], "completed")
        with self.assertRaises(editor.GuideRequiredFieldsError) as missing:
            normalize("education", {"institution_name": "Fictional University"})
        self.assertEqual(missing.exception.missing_required_fields, ["end_date"])
        self.assertEqual(missing.exception.code, "missing_required_fields")

    def test_guide_impact_and_looking_ahead_limits_keep_original_words(self):
        from services import living_resume_editor_service as editor
        normalize = getattr(editor, "normalize_guide_values", None)
        self.assertTrue(callable(normalize))
        seventy = "  " + " \t".join(["well-tested", "café"] * 35) + "\n"
        values = {"title": "Professional summary", "wording": seventy, "classification": "work"}
        self.assertEqual(normalize("knowledge", values, section="impact_statement")["wording"], seventy.strip())
        original = {**values, "wording": seventy + " extra"}
        before = dict(original)
        with self.assertRaises(editor.GuideTextLimitError) as too_long:
            normalize("knowledge", original, section="impact_statement")
        self.assertEqual((too_long.exception.code, too_long.exception.actual_count), ("impact_statement_too_long", 71))
        self.assertEqual(original, before)
        with self.assertRaises(editor.GuideTextLimitError):
            normalize("knowledge", original, section="awards")
        ahead = {"title": "Looking Ahead", "wording": "x" * 120, "classification": "work"}
        self.assertEqual(normalize("knowledge", ahead, section="looking_ahead")["wording"], "x" * 120)
        with self.assertRaises(editor.GuideTextLimitError) as too_long:
            normalize("knowledge", {**ahead, "wording": "x" * 121}, section="looking_ahead")
        self.assertEqual(too_long.exception.actual_count, 121)

    def credential(self, **changes):
        return {"name": "Fictional qualification", "issuer": "Fictional Institute", "issue_date": "2022-01-01",
            "issue_date_precision": "year", "completion_status": "completed", **changes}

    def test_optional_qualification_kind_keeps_legacy_defaults_out_of_stored_values(self):
        from services.living_resume_editor_service import normalize_editor_values
        legacy = normalize_editor_values("credential", self.credential())
        self.assertNotIn("qualification_kind", legacy)
        self.assertIsNone(normalize_editor_values("credential", self.credential(qualification_kind=None))["qualification_kind"])
        for kind in ("certification", "license", "publication", "membership"):
            with self.subTest(kind=kind):
                values = normalize_editor_values("credential", self.credential(qualification_kind=kind))
                self.assertEqual(values["qualification_kind"], kind)
                self.assertEqual(values["issue_date"], "2022-01-01")
                self.assertEqual(values["issue_date_precision"], "year")
        with self.assertRaises(LivingResumeEditorValidationError):
            normalize_editor_values("credential", self.credential(qualification_kind="award"))

    def test_membership_needs_its_organization_and_date_but_no_invented_name(self):
        from services.living_resume_editor_service import normalize_editor_values
        values = normalize_editor_values("credential", self.credential(qualification_kind="membership", name=None))
        self.assertIsNone(values["name"])
        self.assertEqual(values["issuer"], "Fictional Institute")
        for changes in ({"issuer": None}, {"issue_date": None, "issue_date_precision": None}, {"qualification_kind": "certification"}):
            with self.subTest(changes=changes), self.assertRaises(LivingResumeEditorValidationError):
                normalize_editor_values("credential", self.credential(**{"qualification_kind": "membership", "name": None, **changes}))

    def test_untitled_education_requires_the_explicit_local_normalizer_mode(self):
        from services.living_resume_editor_service import normalize_editor_values
        original = {"institution_name": "Fictional University", "end_date": "2024-01-01",
            "date_precision": "year", "education_status": "completed"}
        with self.assertRaises(LivingResumeEditorValidationError):
            normalize_editor_values("education", original)
        values = normalize_editor_values("education", original, require_title=False)
        self.assertIsNone(values["title"])
        self.assertIsNone(values["degree_name"])
        self.assertEqual(values["end_date"], "2024-01-01")

    def test_project_minimum_optional_category_and_three_https_links(self):
        from services.living_resume_editor_service import normalize_editor_values
        minimum = {"project_name": "Fictional Orchard", "summary": "Built a small fictional demonstration."}
        values = normalize_editor_values("project", minimum)
        self.assertEqual(values["project_name"], minimum["project_name"])
        self.assertEqual(values["summary"], minimum["summary"])
        self.assertNotIn("project_category", values)
        rich = normalize_editor_values("project", {**minimum, "project_category": "software",
            "organization_name": "Fictional Institute", "project_role": "Builder",
            "project_url": "https://example.test/demo", "additional_project_urls": ["https://example.test/code", "https://example.test/paper"],
            "start_date": "2020-01-01", "end_date": "2022-01-01", "date_precision": "year"})
        self.assertEqual(rich["additional_project_urls"], ["https://example.test/code", "https://example.test/paper"])
        self.assertEqual(rich["project_category"], "software")
        self.assertEqual(rich["date_precision"], "year")
        for changes in ({"summary": "two\nlines"}, {"summary": None}, {"project_category": "invented"},
                        {"project_url": "http://example.test"}, {"project_url": "https:///missing-host"},
                        {"project_url": "https://example.test", "additional_project_urls": ["https://EXAMPLE.test"]},
                        {"additional_project_urls": ["https://a.test", "https://b.test", "https://c.test"]},
                        {"additional_project_urls": [{"url": "https://example.test"}]}, {"details": "Not an approved stored field"}):
            with self.subTest(changes=changes), self.assertRaises(LivingResumeEditorValidationError):
                normalize_editor_values("project", {**minimum, **changes})

    def test_new_fields_are_preserved_by_partial_intent_without_inventing_missing_values(self):
        from services.living_resume_editor_service import normalize_editor_intent
        self.assertEqual(normalize_editor_intent("credential", {"qualification_kind": "membership", "issuer": "Fictional Guild"}),
            {"qualification_kind": "membership", "issuer": "Fictional Guild"})
        self.assertEqual(normalize_editor_intent("project", {"summary": "Fictional work", "additional_project_urls": ["https://example.test"]}),
            {"summary": "Fictional work", "additional_project_urls": ["https://example.test"]})

    def test_project_optional_field_clears_are_not_silently_lost(self):
        from services.living_resume_editor_service import normalize_editor_values
        normalized = normalize_editor_values("project", {"project_name": "Fictional Orchard", "summary": "Fictional work.",
            "organization_name": "", "project_category": "", "project_url": "", "additional_project_urls": [],
            "start_date": None, "end_date": None})
        self.assertIsNone(normalized["organization_name"])
        self.assertIsNone(normalized["project_category"])
        self.assertIsNone(normalized["project_url"])
        self.assertEqual(normalized["additional_project_urls"], [])
        self.assertIsNone(normalized["start_date"])
        self.assertIsNone(normalized["end_date"])

    def test_sql_editor_refuses_qualification_kind_before_any_procedure(self):
        database = MagicMock()
        payload = {"command_id": COMMAND_ID, "type": "create_credential", "record_key": RECORD_KEY,
            "parent_key": None, "expected_version": None, "values": self.credential(qualification_kind="membership")}
        with self.assertRaisesRegex(LivingResumeEditorValidationError, "storage.*support"):
            LivingResumeEditorService(database).commit("fictional-owner", payload)
        database.execute_procedure.assert_not_called()


class CredentialPrecisionTests(unittest.TestCase):
    def values(self, **changes):
        return {'name':'Service Design Practitioner','issuer':'Example Institute','completion_status':'completed',
            'issue_date':'2022-06-01','issue_date_precision':'month',
            'expiration_date':'2027-06-01','expiration_date_precision':'month',**changes}

    def test_independent_precision_and_coarse_order_do_not_invent_exact_days(self):
        from services.living_resume_editor_service import normalize_editor_values
        for values in (self.values(),self.values(issue_date='2022-01-01',issue_date_precision='year',
                expiration_date='2027-06-15',expiration_date_precision='day'),
                self.values(issue_date='2022-06-15',issue_date_precision='day',
                    expiration_date='2022-06-01',expiration_date_precision='month')):
            normalized=normalize_editor_values('credential',values)
            self.assertEqual(normalized['issue_date'],values['issue_date'])
            self.assertEqual(normalized['expiration_date'],values['expiration_date'])
            for name in ('issue_date','expiration_date'):
                if values[name+'_precision']!='day': self.assertEqual(normalized[name+'_precision'],values[name+'_precision'])
        with self.assertRaises(LivingResumeEditorValidationError):
            normalize_editor_values('credential',self.values(expiration_date='2021-12-01'))
        with self.assertRaises(LivingResumeEditorValidationError):
            normalize_editor_values('credential',self.values(issue_date='2022-06-15'))

    def test_sql_editor_refuses_coarse_precision_before_procedure_execution(self):
        database=MagicMock()
        with self.assertRaisesRegex(LivingResumeEditorValidationError,'input is kept'):
            LivingResumeEditorService(database).commit('synthetic-owner',role_payload(
                type='create_credential',values=self.values()))
        database.execute_procedure.assert_not_called()


def editor_sets(*, role=True):
    return [
        [{"profile_key": PARENT_KEY, "profile_slug": "pete", "display_name": "Pete"}],
        ([{
            "record_key": RECORD_KEY,
            "role_title": "Engineer",
            "employer_name": "PeerSlate",
            "location_text": None,
            "summary": "Built private tools",
            "start_date": date(2026, 9, 1),
            "end_date": None,
            "date_precision": "month",
            "employment_type": "full_time",
            "current_role": 1,
            "row_version": bytes.fromhex(VERSION),
            "editable": 1,
            "blocked_reason": None,
        }] if role else []),
        [],
        [],
        [],
        [],
    ]


class LivingResumeEditorValidationTests(unittest.TestCase):
    def test_utf16_limits_count_non_bmp_text_as_two_units(self):
        self.assertEqual(utf16_length("a😀"), 3)

    def test_normalizes_full_role_and_hashes_exact_utf16_json(self):
        normalized, command_json, digest = normalize_command(role_payload())

        self.assertEqual(normalized["values"]["start_date"], "2026-09-01")
        self.assertEqual(json.loads(command_json), normalized)
        self.assertEqual(digest, hashlib.sha256(command_json.encode("utf-16-le")).hexdigest())

    def test_rejects_browser_control_of_any_unknown_envelope_or_value_field(self):
        cases = (
            role_payload(owner_profile_id=12),
            role_payload(values={**role_payload()["values"], "visibility": "public"}),
            role_payload(values={**role_payload()["values"], "approved_text": "unsafe"}),
        )
        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(LivingResumeEditorValidationError):
                    normalize_command(payload)

    def test_non_text_command_type_and_invalid_unicode_are_typed_validation_errors(self):
        with self.assertRaises(LivingResumeEditorValidationError):
            normalize_command(role_payload(type=[]))
        values = {**role_payload()["values"], "summary": "bad\ud800text"}
        with self.assertRaises(LivingResumeEditorValidationError):
            normalize_command(role_payload(values=values))

    def test_command_id_must_be_canonical_uuid_v4(self):
        for value in ("ABC", "AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA", "00000000-0000-1000-8000-000000000000"):
            with self.subTest(value=value):
                with self.assertRaises(LivingResumeEditorValidationError):
                    normalize_command(role_payload(command_id=value))

    def test_update_and_remove_require_parent_version_and_cannot_reparent(self):
        for payload in (
            role_payload(type="update_role", expected_version=None),
            role_payload(type="update_role", expected_version=VERSION, parent_key=PARENT_KEY),
            role_payload(type="remove_role", expected_version=VERSION, values={"role_title": "x"}),
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(LivingResumeEditorValidationError):
                    normalize_command(payload)

    def test_only_create_accomplishment_accepts_parent_key(self):
        payload = {
            "command_id": COMMAND_ID,
            "type": "create_accomplishment",
            "record_key": RECORD_KEY,
            "parent_key": PARENT_KEY,
            "expected_version": None,
            "values": {"wording": "Shipped it", "metric_value": "2x", "metric_label": None},
        }
        normalized, _, _ = normalize_command(payload)
        self.assertEqual(normalized["parent_key"], PARENT_KEY)

    def test_role_dates_and_current_role_are_consistent(self):
        cases = (
            {"start_date": None, "end_date": "2026-01-01", "current_role": False},
            {"start_date": "2026-02-01", "end_date": "2026-01-01", "current_role": False},
            {"start_date": "2026-01-01", "end_date": "2026-02-01", "current_role": True},
        )
        for changes in cases:
            values = {**role_payload()["values"], **changes}
            with self.subTest(changes=changes):
                with self.assertRaises(LivingResumeEditorValidationError):
                    normalize_command(role_payload(values=values))

    def test_credential_status_is_explicit_and_legacy_unknown_is_not_a_write_value(self):
        base = {
            "name": "Azure Fundamentals",
            "issuer": "Microsoft",
            "identifier": None,
            "issue_date": None,
            "expiration_date": None,
            "verification_url": None,
        }
        for status in (None, "unknown"):
            values = {**base, "completion_status": status}
            with self.subTest(status=status):
                with self.assertRaises(LivingResumeEditorValidationError):
                    normalize_command(role_payload(type="create_credential", values=values))

    def test_credential_completion_controls_dates_and_url(self):
        base = {
            "name": "Azure Fundamentals",
            "issuer": "Microsoft",
            "identifier": None,
            "issue_date": "2026-01-02",
            "expiration_date": None,
            "verification_url": "https://example.test/proof",
            "completion_status": "completed",
        }
        normalized, _, _ = normalize_command(role_payload(type="create_credential", values=base))
        self.assertEqual(normalized["values"]["completion_status"], "completed")
        for changes in (
            {"completion_status": "planned"},
            {"issue_date": None},
            {"verification_url": "javascript:alert(1)"},
        ):
            with self.subTest(changes=changes):
                with self.assertRaises(LivingResumeEditorValidationError):
                    normalize_command(
                        role_payload(type="create_credential", values={**base, **changes})
                    )

    def test_malformed_bracketed_verification_url_is_a_typed_validation_error(self):
        values = {
            "name": "Azure Fundamentals",
            "issuer": "Microsoft",
            "identifier": None,
            "issue_date": "2026-01-02",
            "expiration_date": None,
            "verification_url": "http://[",
            "completion_status": "completed",
        }
        with self.assertRaises(LivingResumeEditorValidationError):
            normalize_command(role_payload(type="create_credential", values=values))

    def test_eight_thousand_unit_long_fields_survive_create_and_update_normalization(self):
        long_text = "x" * 8000
        cases = (
            role_payload(values={**role_payload()["values"], "summary": long_text}),
            role_payload(
                type="update_role",
                expected_version=VERSION,
                values={**role_payload()["values"], "summary": long_text},
            ),
            role_payload(
                type="create_accomplishment",
                parent_key=PARENT_KEY,
                values={"wording": long_text, "metric_value": None, "metric_label": None},
            ),
            role_payload(
                type="update_accomplishment",
                expected_version=VERSION,
                values={"wording": long_text, "metric_value": None, "metric_label": None},
            ),
            role_payload(
                type="create_skill", values={"name": "SQL", "summary": long_text}
            ),
            role_payload(
                type="update_skill",
                expected_version=VERSION,
                values={"name": "SQL", "summary": long_text},
            ),
        )
        for payload in cases:
            with self.subTest(command_type=payload["type"]):
                normalized, command_json, _ = normalize_command(payload)
                field = "wording" if "accomplishment" in payload["type"] else "summary"
                self.assertEqual(normalized["values"][field], long_text)
                self.assertEqual(json.loads(command_json)["values"][field], long_text)

    def test_long_editor_text_rejects_over_eight_thousand_units_for_create_and_update(self):
        too_long = "x" * 8001
        cases = (
            role_payload(values={**role_payload()["values"], "summary": too_long}),
            role_payload(
                type="update_role",
                expected_version=VERSION,
                values={**role_payload()["values"], "summary": too_long},
            ),
            role_payload(
                type="create_accomplishment",
                parent_key=PARENT_KEY,
                values={"wording": too_long, "metric_value": None, "metric_label": None},
            ),
            role_payload(
                type="update_accomplishment",
                expected_version=VERSION,
                values={"wording": too_long, "metric_value": None, "metric_label": None},
            ),
            role_payload(
                type="create_skill", values={"name": "SQL", "summary": too_long}
            ),
            role_payload(
                type="update_skill",
                expected_version=VERSION,
                values={"name": "SQL", "summary": too_long},
            ),
        )
        for payload in cases:
            with self.subTest(command_type=payload["type"]):
                with self.assertRaises(LivingResumeEditorValidationError):
                    normalize_command(payload)


class LivingResumeEditorServiceTests(unittest.TestCase):
    def setUp(self):
        self.database = MagicMock()
        self.service = LivingResumeEditorService(self.database)

    def test_owner_read_has_six_strict_sections_and_explicit_capabilities(self):
        self.database.execute_procedure.return_value = editor_sets()
        editor = self.service.get_editor("owner-1")

        self.assertEqual(editor["roles"][0]["row_version"], VERSION)
        self.assertEqual(editor["roles"][0]["start_date"], "2026-09-01")
        self.assertIs(editor["roles"][0]["editable"], True)
        self.assertEqual(editor["credentials"], [])
        self.assertIn("create_credential", editor["capabilities"]["commands"])
        self.assertTrue(editor["capabilities"]["published_records_use_draft_overlay"])
        self.assertEqual(editor["roles"][0]["save_mode"], "canonical")
        self.database.execute_procedure.assert_called_once_with(
            "usp_GetOwnerLivingResumeEditor", (("@UserKey", "owner-1"),)
        )

    def test_commit_binds_only_server_identity_uuid_and_canonical_json(self):
        _, command_json, digest = normalize_command(role_payload())
        self.database.execute_procedure.side_effect = [
            [[{
                "committed": 1,
                "error_code": None,
                "command_id": COMMAND_ID,
                "request_digest": digest,
                "command_type": "create_role",
                "record_key": RECORD_KEY,
                "outcome": "created",
                "record_version": bytes.fromhex(VERSION),
                "replayed": 0,
            }]],
            editor_sets(),
        ]

        result = self.service.commit("owner-1", role_payload())

        self.assertEqual(result["receipt"]["outcome"], "created")
        self.assertEqual(result["current"]["record_key"], RECORD_KEY)
        self.database.execute_procedure.assert_any_call(
            "usp_CommitLivingResumeCommandForOwner",
            (
                ("@UserKey", "owner-1"),
                ("@CommandId", COMMAND_ID),
                ("@CommandJson", command_json),
            ),
        )

    def test_replay_returns_original_receipt_and_current_record(self):
        _, _, digest = normalize_command(role_payload())
        self.database.execute_procedure.side_effect = [
            [[{
                "committed": True,
                "error_code": None,
                "command_id": COMMAND_ID,
                "request_digest": digest,
                "command_type": "create_role",
                "record_key": RECORD_KEY,
                "outcome": "created",
                "record_version": VERSION,
                "replayed": 1,
            }]],
            editor_sets(),
        ]
        result = self.service.commit("owner-1", role_payload())
        self.assertTrue(result["receipt"]["replayed"])
        self.assertEqual(result["current"]["row_version"], VERSION)

    def test_replayed_create_keeps_original_receipt_when_record_was_later_removed(self):
        _, _, digest = normalize_command(role_payload())
        self.database.execute_procedure.side_effect = [
            [[{
                "committed": True,
                "error_code": None,
                "command_id": COMMAND_ID,
                "request_digest": digest,
                "command_type": "create_role",
                "record_key": RECORD_KEY,
                "outcome": "created",
                "record_version": VERSION,
                "replayed": 1,
            }]],
            editor_sets(role=False),
        ]
        result = self.service.commit("owner-1", role_payload())
        self.assertEqual(result["receipt"]["outcome"], "created")
        self.assertIsNone(result["current"])

    def test_changed_conflict_refreshes_only_authorized_current_state(self):
        self.database.execute_procedure.side_effect = [
            [[{
                "committed": 0,
                "error_code": "changed",
                "command_id": None,
                "request_digest": None,
                "command_type": None,
                "record_key": None,
                "outcome": None,
                "record_version": None,
                "replayed": 0,
            }]],
            editor_sets(),
        ]
        payload = role_payload(type="update_role", expected_version="0000000000000001")
        with self.assertRaises(LivingResumeEditorConflictError) as raised:
            self.service.commit("owner-1", payload)
        self.assertEqual(raised.exception.code, "changed")
        self.assertEqual(raised.exception.current["record_key"], RECORD_KEY)

    def test_removed_record_must_be_absent_after_commit(self):
        payload = role_payload(type="remove_role", expected_version=VERSION, values={})
        _, _, digest = normalize_command(payload)
        self.database.execute_procedure.side_effect = [
            [[{
                "committed": 1,
                "error_code": None,
                "command_id": COMMAND_ID,
                "request_digest": digest,
                "command_type": "remove_role",
                "record_key": RECORD_KEY,
                "outcome": "removed",
                "record_version": None,
                "replayed": 0,
            }]],
            editor_sets(role=False),
        ]
        result = self.service.commit("owner-1", payload)
        self.assertIsNone(result["current"])

    def test_database_error_markers_map_without_exposing_sql_text(self):
        cases = {
            "RESUME_EDITOR_NOT_FOUND diagnostic": "not_found",
            "RESUME_EDITOR_PROTECTED diagnostic": "protected",
            "RESUME_EDITOR_IDEMPOTENCY_CONFLICT diagnostic": "idempotency_conflict",
            "something internal": "unavailable",
        }
        for detail, code in cases.items():
            with self.subTest(detail=detail):
                cause = RuntimeError(detail)
                error = DatabaseServiceError("procedure failed")
                error.__cause__ = cause
                self.database.execute_procedure.side_effect = error
                with self.assertRaises(Exception) as raised:
                    self.service.commit("owner-1", role_payload())
                self.assertEqual(raised.exception.code, code)
                self.assertNotIn("diagnostic", str(raised.exception))
                self.database.reset_mock()

    def test_unknown_or_extra_database_shapes_fail_closed(self):
        self.database.execute_procedure.return_value = editor_sets() + [[]]
        with self.assertRaises(LivingResumeEditorUnavailableError):
            self.service.get_editor("owner-1")

    def test_malformed_database_identifiers_and_visibility_state_fail_closed(self):
        malformed_key = editor_sets()
        malformed_key[1][0]["record_key"] = "not-a-uuid"
        self.database.execute_procedure.return_value = malformed_key
        with self.assertRaises(LivingResumeEditorUnavailableError):
            self.service.get_editor("owner-1")

        contradictory_state = editor_sets()
        contradictory_state[1][0]["editable"] = 0
        self.database.execute_procedure.return_value = contradictory_state
        with self.assertRaises(LivingResumeEditorUnavailableError):
            self.service.get_editor("owner-1")

    def test_published_records_are_readable_as_draft_overlay_not_canonical_writes(self):
        rows = editor_sets()
        rows[1][0]["editable"] = 0
        rows[1][0]["blocked_reason"] = "published_or_history_bearing"
        self.database.execute_procedure.return_value = rows
        editor = self.service.get_editor("owner-1")
        role = editor["roles"][0]
        self.assertIs(role["editable"], False)
        self.assertEqual(role["blocked_reason"], "published_or_history_bearing")
        self.assertEqual(role["save_mode"], "draft_overlay")
        self.assertEqual(save_mode_for_record(role), "draft_overlay")
        self.assertTrue(editor["capabilities"]["published_records_use_draft_overlay"])
        self.assertTrue(editor["capabilities"]["canonical_commands_do_not_publish"])


if __name__ == "__main__":
    unittest.main()
