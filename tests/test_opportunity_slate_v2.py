"""Route and service tests for PS-OPPORTUNITY-SLATE-002 slice R1 — the
Opportunity Slate REPLACEMENT room (shell + stage-1 intake + stage-2
captured-source review).

The production application never registers ``opportunity_slate_v2`` in R1
(``app.py`` belongs to another lane, and the flag stays off everywhere), so
route tests build their own throwaway Flask app that registers the
blueprint directly — mirroring ``tests/ask_pete_direct/support.py``, the
established pattern for a blueprint app.py does not register. The database
is always a recording fake at the ``database_service`` seam; no test here
opens a connection, and none needs one. This keeps the suite fast and free
of any live-database requirement, matching how
``tests/test_opportunity_slate.py`` unit-tests
``services/opportunity_slate_service.py`` with a ``MagicMock`` database.
"""

import re
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlsplit

from flask import Blueprint, Flask, url_for
from jinja2 import Undefined

import opportunity_slate_v2_routes as routes
from services.database_service import DatabaseServiceError
from services.opportunity_slate_v2_service import (
    MAX_IDENTITY_FIELD_UNITS,
    MAX_SOURCE_TEXT_UNITS,
    OpportunitySlateV2Service,
    OpportunitySlateV2ServiceError,
    SourceIdentityView,
    WorkingSourceView,
    _optional_bounded_text,
    _serialize_identity_row,
    _serialize_working_row,
    normalize_source_key,
    utf16_length,
    validate_source_text,
)
from services.opportunity_source_intake_service import OpportunitySourceIntakeError


ROOT = Path(__file__).resolve().parents[1]
OWNER_USER_KEY = "owner-user-key-1"
OTHER_USER_KEY = "other-owner-user-key"


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _binary(value=1):
    return value.to_bytes(8, "big")


def _working_row(**overrides):
    row = {
        "working_session_key": "11111111-1111-1111-1111-111111111111",
        "workbench_state": "review_source",
        "expires_at_utc": "2999-01-01T00:00:00+00:00",
        "session_row_version": _binary(1),
        "source_key": "22222222-2222-2222-2222-222222222222",
        "current_version_number": 1,
        "confirmed_version_number": None,
        "confirmed_at_utc": None,
        "source_row_version": _binary(2),
        "capture_method": "pasted",
        "original_text": "Employer wording exactly as captured.",
        "member_corrected_text": None,
        "corrected_at_utc": None,
        "captured_at_utc": "2025-04-30T12:00:00+00:00",
    }
    row.update(overrides)
    return row


def _identity_row(**overrides):
    row = {
        "employer_name": "Meridian Aerospace",
        "role_title": "Senior Systems Engineering Manager",
        "source_type": "job_posting",
    }
    row.update(overrides)
    return row


def _review_form_data(**overrides):
    data = {
        "source_key": "22222222-2222-2222-2222-222222222222",
        "version_token": _binary(2).hex(),
        "session_key": "11111111-1111-1111-1111-111111111111",
        "session_version_token": _binary(1).hex(),
        "employer_name": "Meridian Aerospace",
        "role_title": "Senior Systems Engineering Manager",
        "corrected_text": "Employer wording exactly as captured.",
    }
    data.update(overrides)
    return data


class RecordingDatabase:
    """Records every ``first_row`` call and returns whatever the test
    queued, in order. Mirrors ``tests/ask_pete_direct/support.py``'s own
    ``RecordingDatabase`` — duplicated here rather than imported, for the
    same file-ownership reason every other duplicated test helper in this
    codebase already gives (that module belongs to a different package).
    """

    def __init__(self, rows=None, error=None):
        self.rows = list(rows or [])
        self.error = error
        self.calls = []

    def first_row(self, procedure_name, parameters=None):
        self.calls.append((procedure_name, list(parameters or [])))
        if self.error:
            raise self.error
        result = self.rows.pop(0) if self.rows else None
        if isinstance(result, Exception):
            raise result
        return result

    def parameters(self, index=0):
        return dict(self.calls[index][1])

    @property
    def procedures(self):
        return [name for name, _ in self.calls]


def _stub_auth_blueprint():
    """A minimal stand-in for the real ``auth`` blueprint so
    ``url_for('auth.sign_in', return_to=...)`` resolves inside the test
    app exactly as it does in the real one, without pulling in the real
    authentication module."""
    auth = Blueprint("auth", __name__)

    @auth.get("/auth/sign-in")
    def sign_in():
        return "sign in", 200

    return auth


class _LenientUndefined(Undefined):
    """``templates/base.html`` calls several app.py-registered Jinja
    globals (``portfolio_url(...)``, etc.) that this throwaway test app
    never registers — app.py is another lane's file and is not imported
    here. Calling or chaining off an ``Undefined`` normally raises; both
    are overridden to return another harmless ``Undefined`` instead, so
    the shared site chrome renders inert around the room this suite is
    actually testing, rather than making every render test depend on
    reimplementing app.py's own context processors.
    """

    def __call__(self, *args, **kwargs):
        return _LenientUndefined()

    def __getattr__(self, name):
        return _LenientUndefined()


def make_app(*, enabled=True, dev_user_key=OWNER_USER_KEY, rows=None, error=None):
    """Build the throwaway test app and return ``(client, database)``."""
    app = Flask(
        "opportunity_slate_v2_test_app",
        root_path=str(ROOT),
        template_folder="templates",
        static_folder="static",
    )
    app.config.update(
        TESTING=True,
        SECRET_KEY="test-only-not-a-secret",
        PEERSLATE_OPPORTUNITY_SLATE_V2_ENABLED=enabled,
        PEERSLATE_ALLOW_DEV_IDENTITY=dev_user_key is not None,
        PEERSLATE_DEV_USER_KEY=dev_user_key,
        PEERSLATE_TRUST_EASYAUTH_HEADERS=False,
    )
    app.register_blueprint(routes.opportunity_slate_v2)
    app.register_blueprint(_stub_auth_blueprint())
    app.add_url_rule("/", endpoint="home", view_func=lambda: "home")
    app.add_url_rule(
        "/peerslate-home", endpoint="peerslate_home", view_func=lambda: "home"
    )
    app.add_url_rule("/the-slate", endpoint="the_slate", view_func=lambda: "the slate")
    app.jinja_env.undefined = _LenientUndefined

    database = RecordingDatabase(rows=rows, error=error)
    service = OpportunitySlateV2Service(database=database)
    patcher = patch.object(routes, "opportunity_slate_v2_service", service)
    patcher.start()
    return app, database, patcher


def same_origin_headers(**overrides):
    headers = {"Origin": "http://localhost", "Sec-Fetch-Site": "same-origin"}
    headers.update(overrides)
    return headers


class RouteTestCase(unittest.TestCase):
    """Base case: one throwaway app per test, service seam patched and
    always restored."""

    def make_client(self, **kwargs):
        app, database, patcher = make_app(**kwargs)
        self.addCleanup(patcher.stop)
        self.app = app
        return app.test_client(), database


# ---------------------------------------------------------------------------
# No-AI-import guardrail
# ---------------------------------------------------------------------------


class NoAiImportGuardrailTests(unittest.TestCase):
    """R1 has no AI call anywhere (delegation brief: 'no AI call
    anywhere in R1 code'). Mirrors
    tests.test_opportunity_slate.NoAiCallTests exactly, applied to the v2
    files instead — a separate, lane-owned test rather than an edit to
    that existing test class."""

    def test_routes_and_service_import_no_ai_client(self):
        for relative in (
            "opportunity_slate_v2_routes.py",
            "services/opportunity_slate_v2_service.py",
        ):
            source = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(module=relative):
                self.assertNotIn("import anthropic", source)
                self.assertNotIn("messages.create", source)
                self.assertNotIn("ANTHROPIC_API_KEY", source)
                # A real import statement, not just the module name — the
                # module name legitimately appears in this file's own
                # prose explaining why it is NOT imported (R1 has no
                # interpretation/alignment step to call it for).
                self.assertNotIn("import opportunity_analysis_service", source)
                self.assertNotRegex(
                    source, r"from services\.opportunity_analysis_service import"
                )

    def test_service_does_not_import_the_legacy_service_module(self):
        """Architecture section 9 names exactly two modules the
        replacement reuses (opportunity_source_intake_service and, from
        R2, opportunity_analysis_service); services/opportunity_slate_service
        is not one of them. The v2 service is self-contained."""
        source = (ROOT / "services" / "opportunity_slate_v2_service.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("from services.opportunity_slate_service import", source)
        self.assertNotIn("import services.opportunity_slate_service", source)

    def test_routes_do_not_edit_any_legacy_opportunity_slate_file(self):
        """Belt-and-braces: the lane excludes every legacy file by name.
        This does not prove nothing changed (git history does that); it
        proves the new routes module does not itself import the legacy
        routes module, which would be a sharper, code-level violation."""
        source = (ROOT / "opportunity_slate_v2_routes.py").read_text(encoding="utf-8")
        self.assertNotIn("import opportunity_slate_routes", source)
        self.assertNotIn("from opportunity_slate_routes", source)


# ---------------------------------------------------------------------------
# Stage-2 narrow-viewport layout (CSS static assertions)
# ---------------------------------------------------------------------------


class NarrowViewportCssTests(unittest.TestCase):
    """Static assertions on static/css/opportunity-slate-v2.css. Orchestrator
    visual-parity review of the R1 candidate found two defects at a 320px
    viewport, both fixed at the source-text level here so a future edit
    cannot silently reintroduce either without a test failing first.
    """

    CSS = (ROOT / "static" / "css" / "opportunity-slate-v2.css").read_text(
        encoding="utf-8"
    )

    def test_narrow_media_query_resets_grid_row_for_main_and_rail(self):
        """Defect 1: .os2-rail and .os2-main overlapped at 320px. The
        desktop rule pins both to an explicit grid-row (independent-review
        finding, see the DOM-order comment above .os2-main/.os2-rail in the
        stylesheet), and the <=900px media query originally reset only
        grid-column, leaving the shared grid-row: 1 standing so both
        children landed in the same cell instead of stacking. Fix: the
        combined narrow-layout rule must also reset grid-row to auto so
        normal document flow (.os2-main then .os2-rail, matching DOM
        order) places them in successive rows."""
        media_match = re.search(
            r"@media \(max-width: 900px\) \{(?P<body>.*?)\n\}\n",
            self.CSS,
            re.DOTALL,
        )
        self.assertIsNotNone(media_match, "expected an <=900px media query block")
        block = media_match.group("body")

        rule_match = re.search(
            r"\.os2-main,\s*\.os2-rail\s*\{(?P<rule>[^}]*)\}",
            block,
        )
        self.assertIsNotNone(
            rule_match,
            "expected a combined .os2-main, .os2-rail rule inside the "
            "<=900px media query",
        )
        rule_body = rule_match.group("rule")
        self.assertIn(
            "grid-column: 1",
            rule_body,
            "narrow layout must still collapse both children into column 1",
        )
        self.assertIn(
            "grid-row: auto",
            rule_body,
            "narrow layout must reset grid-row to auto, or the desktop "
            "grid-row: 1 pin leaves .os2-main and .os2-rail sharing one "
            "grid cell and overlapping",
        )

    def test_default_icon_class_has_an_explicit_size_cap(self):
        """Defect 2: the Back link's arrow icon rendered at an enormous,
        unconstrained size at narrow widths. os2_icon()'s default
        classes="os2-icon" (templates/opportunity_slate_v2/_icons.html) is
        what the subheader and stage-2 footer 'Back' links both use, and
        with no width/height on the inline <svg> and no CSS rule to size
        it, a browser falls back to its native replaced-element default
        (300x150 CSS px). Every other icon call passes its own sized class
        (.os2-dictate__icon, .os2-alt-entry__icon, .os2-alt-entry__chevron)
        already covered by a rule; this pins the default case too."""
        rule_match = re.search(r"\.os2-icon\s*\{(?P<rule>[^}]*)\}", self.CSS)
        self.assertIsNotNone(
            rule_match, "expected a .os2-icon rule capping the default icon size"
        )
        rule_body = rule_match.group("rule")
        self.assertIn("width:", rule_body)
        self.assertIn("height:", rule_body)


# ---------------------------------------------------------------------------
# Service-level unit tests
# ---------------------------------------------------------------------------


class ValidationHelperTests(unittest.TestCase):
    def test_validate_source_text_requires_nonblank(self):
        with self.assertRaises(OpportunitySlateV2ServiceError) as ctx:
            validate_source_text("   ")
        self.assertEqual("required", ctx.exception.code)

    def test_validate_source_text_enforces_the_cap(self):
        with self.assertRaises(OpportunitySlateV2ServiceError) as ctx:
            validate_source_text("x" * (MAX_SOURCE_TEXT_UNITS + 1))
        self.assertEqual("too_long", ctx.exception.code)

    def test_validate_source_text_strips_surrounding_whitespace_only(self):
        cleaned = validate_source_text("  line one\n\nline two  ")
        self.assertEqual("line one\n\nline two", cleaned)

    def test_optional_bounded_text_blank_becomes_none(self):
        self.assertIsNone(_optional_bounded_text("   ", "employer name", 200))
        self.assertIsNone(_optional_bounded_text(None, "employer name", 200))

    def test_optional_bounded_text_enforces_the_cap(self):
        with self.assertRaises(OpportunitySlateV2ServiceError) as ctx:
            _optional_bounded_text("x" * 201, "employer name", MAX_IDENTITY_FIELD_UNITS)
        self.assertEqual("too_long", ctx.exception.code)

    def test_optional_bounded_text_strips_and_keeps_interior_whitespace(self):
        self.assertEqual(
            "Meridian Aerospace",
            _optional_bounded_text("  Meridian Aerospace  ", "employer name", 200),
        )

    def test_utf16_length_counts_code_units_not_characters(self):
        # A single astral-plane emoji is one Python character but two
        # UTF-16 code units — the same bound the database's DATALENGTH/2
        # check applies.
        self.assertEqual(2, utf16_length("\U0001F600"))

    def test_normalize_source_key_rejects_malformed_input_silently(self):
        self.assertIsNone(normalize_source_key("not-a-guid"))
        self.assertIsNone(normalize_source_key(None))


class WorkingSourceViewTests(unittest.TestCase):
    def test_display_text_prefers_the_correction(self):
        view = _serialize_working_row(
            _working_row(member_corrected_text="Corrected wording")
        )
        self.assertEqual("Corrected wording", view.display_text)
        self.assertTrue(view.has_correction)

    def test_display_text_falls_back_to_the_original(self):
        view = _serialize_working_row(_working_row())
        self.assertEqual("Employer wording exactly as captured.", view.display_text)
        self.assertFalse(view.has_correction)

    def test_is_confirmed_compares_confirmed_to_current_version(self):
        unconfirmed = _serialize_working_row(_working_row())
        self.assertFalse(unconfirmed.is_confirmed)
        confirmed = _serialize_working_row(
            _working_row(confirmed_version_number=1)
        )
        self.assertTrue(confirmed.is_confirmed)

    def test_row_shape_is_exact_not_loose(self):
        """A row missing a field or carrying an unexpected extra one is
        rejected outright rather than silently passed through."""
        row = _working_row()
        del row["capture_method"]
        with self.assertRaises(OpportunitySlateV2ServiceError):
            _serialize_working_row(row)

    def test_row_accepts_the_full_capture_method_enum_on_read(self):
        """The database CHECK allows 'dictated' even though this service
        never WRITES it (dictation lands as pasted text). A read must not
        be narrower than what the shared table can legitimately hold."""
        view = _serialize_working_row(_working_row(capture_method="dictated"))
        self.assertEqual("dictated", view.capture_method)


class SourceIdentityViewTests(unittest.TestCase):
    def test_serializes_a_full_row(self):
        view = _serialize_identity_row(_identity_row())
        self.assertEqual("Meridian Aerospace", view.employer_name)
        self.assertEqual("Senior Systems Engineering Manager", view.role_title)
        self.assertEqual("job_posting", view.source_type)

    def test_both_name_fields_may_be_null(self):
        view = _serialize_identity_row(
            _identity_row(employer_name=None, role_title=None)
        )
        self.assertIsNone(view.employer_name)
        self.assertIsNone(view.role_title)


class OpportunitySlateV2ServiceTests(unittest.TestCase):
    def setUp(self):
        self.database = MagicMock()
        self.service = OpportunitySlateV2Service(database=self.database)

    def test_get_working_session_for_owner_returns_none_when_no_row(self):
        self.database.first_row.return_value = None
        self.assertIsNone(self.service.get_working_session_for_owner(OWNER_USER_KEY))
        self.database.first_row.assert_called_once_with(
            "usp_GetOpportunityWorkingSessionForOwner", [("@UserKey", OWNER_USER_KEY)]
        )

    def test_get_working_session_for_owner_re_enforces_expiry_in_python(self):
        """Belt-and-braces: even if the procedure's own expiry predicate
        were ever weakened, an already-expired row must still read as
        None here."""
        self.database.first_row.return_value = _working_row(
            expires_at_utc="2000-01-01T00:00:00+00:00"
        )
        self.assertIsNone(self.service.get_working_session_for_owner(OWNER_USER_KEY))

    def test_get_working_session_requires_a_user_key(self):
        with self.assertRaises(OpportunitySlateV2ServiceError) as ctx:
            self.service.get_working_session_for_owner("")
        self.assertEqual("required", ctx.exception.code)
        self.database.first_row.assert_not_called()

    def test_save_source_for_owner_rejects_an_unbuilt_capture_method(self):
        with self.assertRaises(OpportunitySlateV2ServiceError) as ctx:
            self.service.save_source_for_owner(
                OWNER_USER_KEY, "idem-1", "role text", capture_method="dictated"
            )
        self.assertEqual("invalid", ctx.exception.code)
        self.database.first_row.assert_not_called()

    def test_save_source_for_owner_requires_an_idempotency_key(self):
        with self.assertRaises(OpportunitySlateV2ServiceError) as ctx:
            self.service.save_source_for_owner(OWNER_USER_KEY, "", "role text")
        self.assertEqual("required", ctx.exception.code)

    def test_save_source_for_owner_calls_the_unmodified_os1_procedure(self):
        self.database.first_row.return_value = {
            "outcome": "success",
            "working_session_key": "11111111-1111-1111-1111-111111111111",
            "source_key": "22222222-2222-2222-2222-222222222222",
            "version_number": 1,
            "workbench_state": "review_source",
            "session_row_version": _binary(1),
            "source_row_version": _binary(2),
        }
        result = self.service.save_source_for_owner(
            OWNER_USER_KEY, "idem-1", "role text", capture_method="uploaded"
        )
        self.assertEqual("success", result["outcome"])
        procedure_name = self.database.first_row.call_args[0][0]
        self.assertEqual("usp_SaveOpportunitySourceForOwner", procedure_name)

    def test_correct_source_for_owner_maps_changed_outcome(self):
        self.database.first_row.return_value = {
            "outcome": "changed",
            "source_row_version": None,
            "version_number": None,
        }
        with self.assertRaises(OpportunitySlateV2ServiceError) as ctx:
            self.service.correct_source_for_owner(
                OWNER_USER_KEY,
                "22222222-2222-2222-2222-222222222222",
                _binary(2).hex(),
                "corrected wording",
            )
        self.assertEqual("changed", ctx.exception.code)

    def test_correct_source_for_owner_sends_only_the_corrected_text(self):
        """Proxy for 'the correction never touches the verbatim original':
        at the service boundary, the ONLY text parameter sent is
        @CorrectedText — there is no @OriginalText/@SourceText parameter
        this call could even use to overwrite it with."""
        self.database.first_row.return_value = {
            "outcome": "success",
            "source_row_version": _binary(3),
            "version_number": 1,
        }
        self.service.correct_source_for_owner(
            OWNER_USER_KEY,
            "22222222-2222-2222-2222-222222222222",
            _binary(2).hex(),
            "corrected wording",
        )
        parameters = dict(self.database.first_row.call_args[0][1])
        self.assertEqual({"@UserKey", "@SourceKey", "@ExpectedRowVersion", "@CorrectedText"}, set(parameters))
        self.assertEqual("corrected wording", parameters["@CorrectedText"])

    def test_confirm_source_for_owner_success_shape(self):
        self.database.first_row.return_value = {
            "outcome": "success",
            "source_row_version": _binary(3),
            "confirmed_version_number": 1,
        }
        result = self.service.confirm_source_for_owner(
            OWNER_USER_KEY, "22222222-2222-2222-2222-222222222222", _binary(2).hex()
        )
        self.assertEqual(1, result["confirmed_version_number"])

    def test_delete_working_session_for_owner_maps_invalid_outcome(self):
        self.database.first_row.return_value = {
            "outcome": "invalid",
            "deleted_version_count": None,
        }
        with self.assertRaises(OpportunitySlateV2ServiceError) as ctx:
            self.service.delete_working_session_for_owner(
                OWNER_USER_KEY,
                "11111111-1111-1111-1111-111111111111",
                _binary(1).hex(),
            )
        self.assertEqual("invalid", ctx.exception.code)

    def test_save_source_identity_for_owner_success_shape(self):
        self.database.first_row.return_value = {
            "outcome": "success",
            "source_row_version": _binary(2),
        }
        result = self.service.save_source_identity_for_owner(
            OWNER_USER_KEY,
            "22222222-2222-2222-2222-222222222222",
            _binary(2).hex(),
            "Meridian Aerospace",
            "Senior Systems Engineering Manager",
        )
        self.assertEqual("success", result["outcome"])
        procedure_name, parameters = self.database.first_row.call_args[0]
        self.assertEqual("usp_SaveOpportunitySourceIdentityForOwner", procedure_name)
        parameters = dict(parameters)
        self.assertEqual("Meridian Aerospace", parameters["@EmployerName"])
        self.assertEqual(
            "Senior Systems Engineering Manager", parameters["@RoleTitle"]
        )

    def test_save_source_identity_for_owner_normalizes_blank_to_none(self):
        self.database.first_row.return_value = {
            "outcome": "success",
            "source_row_version": _binary(2),
        }
        self.service.save_source_identity_for_owner(
            OWNER_USER_KEY,
            "22222222-2222-2222-2222-222222222222",
            _binary(2).hex(),
            "   ",
            "   ",
        )
        parameters = dict(self.database.first_row.call_args[0][1])
        self.assertIsNone(parameters["@EmployerName"])
        self.assertIsNone(parameters["@RoleTitle"])

    def test_save_source_identity_for_owner_is_fenced_like_correction(self):
        """No new concurrency token is invented: an unparseable version
        token raises 'changed', exactly like every other fenced write on
        this service."""
        with self.assertRaises(OpportunitySlateV2ServiceError) as ctx:
            self.service.save_source_identity_for_owner(
                OWNER_USER_KEY,
                "22222222-2222-2222-2222-222222222222",
                "not-a-valid-token",
                "Meridian Aerospace",
                "Senior Systems Engineering Manager",
            )
        self.assertEqual("changed", ctx.exception.code)
        self.database.first_row.assert_not_called()

    def test_get_source_identity_for_owner_returns_none_for_no_row(self):
        self.database.first_row.return_value = None
        self.assertIsNone(
            self.service.get_source_identity_for_owner(
                OWNER_USER_KEY, "22222222-2222-2222-2222-222222222222"
            )
        )

    def test_get_source_identity_for_owner_returns_a_view(self):
        self.database.first_row.return_value = _identity_row()
        view = self.service.get_source_identity_for_owner(
            OWNER_USER_KEY, "22222222-2222-2222-2222-222222222222"
        )
        self.assertIsInstance(view, SourceIdentityView)
        self.assertEqual("Meridian Aerospace", view.employer_name)

    def test_every_public_method_resolves_owner_from_user_key_alone(self):
        """No method on this service accepts, derives, or forwards a
        caller-supplied owner/profile identifier — the class docstring's
        stated contract, checked mechanically via the signature rather
        than trusted to stay true by convention."""
        import inspect

        for name, method in inspect.getmembers(
            OpportunitySlateV2Service, predicate=inspect.isfunction
        ):
            if name.startswith("_"):
                continue
            parameters = list(inspect.signature(method).parameters)
            with self.subTest(method=name):
                self.assertIn("user_key", parameters)
                self.assertNotIn("owner_profile_id", parameters)
                self.assertNotIn("profile_id", parameters)


# ---------------------------------------------------------------------------
# Gate: flag, same-origin, and sign-in redirect on every endpoint
# ---------------------------------------------------------------------------


MUTATION_ENDPOINTS = (
    ("post", "/opportunity-slate/source", {"source_text": "role text"}),
    ("post", "/opportunity-slate/source/upload", {}),
    ("post", "/opportunity-slate/source/import", {"source_url": "https://example.com/job"}),
    ("post", "/opportunity-slate/source/identity", {"employer_name": "Acme"}),
    ("post", "/opportunity-slate/source/corrections", {"corrected_text": "x"}),
    ("post", "/opportunity-slate/source/confirm", {}),
    ("post", "/opportunity-slate/source/delete", {}),
)


class FlagGateTests(RouteTestCase):
    def test_flag_off_returns_404_for_the_room(self):
        client, _ = self.make_client(enabled=False)
        response = client.get("/opportunity-slate")
        self.assertEqual(404, response.status_code)

    def test_flag_off_returns_404_for_every_mutation_before_identity_is_checked(self):
        client, database = self.make_client(enabled=False, dev_user_key=None)
        for method, path, form in MUTATION_ENDPOINTS:
            with self.subTest(path=path):
                response = getattr(client, method)(
                    path, data=form, headers=same_origin_headers()
                )
                self.assertEqual(404, response.status_code)
        # Flag-off is checked before same-origin or identity, so an
        # anonymous, cross-origin request still resolves to 404 — flag-off
        # must be indistinguishable from not-found regardless of who asks.
        self.assertEqual([], database.calls)

    def test_flag_on_room_is_reachable(self):
        client, database = self.make_client(rows=[None])
        response = client.get("/opportunity-slate")
        self.assertEqual(200, response.status_code)


class AnonymousGateTests(RouteTestCase):
    def test_anonymous_get_room_redirects_to_sign_in(self):
        client, _ = self.make_client(dev_user_key=None)
        response = client.get("/opportunity-slate")
        self.assertEqual(302, response.status_code)
        self.assertIn("/auth/sign-in", response.headers["Location"])
        self.assertIn("return_to=", response.headers["Location"])

    def test_anonymous_is_redirected_on_every_mutation_endpoint(self):
        """Section 14's R1 test plan, verbatim: 'anonymous -> sign-in
        redirect on every v2 endpoint'."""
        client, database = self.make_client(dev_user_key=None)
        for method, path, form in MUTATION_ENDPOINTS:
            with self.subTest(path=path):
                response = getattr(client, method)(
                    path, data=form, headers=same_origin_headers()
                )
                self.assertEqual(302, response.status_code)
                self.assertIn("/auth/sign-in", response.headers["Location"])
        self.assertEqual([], database.calls)

    def test_return_target_is_confined_to_this_site(self):
        client, _ = self.make_client(dev_user_key=None)
        response = client.get("/opportunity-slate?step=replace")
        location = response.headers["Location"]
        self.assertIn("return_to=/opportunity-slate", location)

    def test_anonymous_post_returns_to_the_room_not_the_post_only_path(self):
        """Independent review finding: building the return target from
        request.full_path on a POST-only route sends the member, after
        sign-in, back to a GET on a path that only accepts POST — a 405,
        not the room. Every mutation route must return to ROOM_PATH
        instead, never its own path. Parses the query string rather than
        substring-matching so this is exact regardless of how the location
        header percent-encodes the value."""
        client, database = self.make_client(dev_user_key=None)
        for method, path, form in MUTATION_ENDPOINTS:
            with self.subTest(path=path):
                response = getattr(client, method)(
                    path, data=form, headers=same_origin_headers()
                )
                self.assertEqual(302, response.status_code)
                query = parse_qs(urlsplit(response.headers["Location"]).query)
                self.assertEqual(["/opportunity-slate"], query.get("return_to"))
        self.assertEqual([], database.calls)

    def test_anonymous_get_return_target_still_carries_the_full_get_path(self):
        """The POST-only fix in the sibling test above must not regress the
        existing GET behavior: a GET still returns to its own full path
        (e.g. ?step=replace), not the bare room path."""
        client, _ = self.make_client(dev_user_key=None)
        response = client.get("/opportunity-slate?step=replace")
        query = parse_qs(urlsplit(response.headers["Location"]).query)
        self.assertEqual(["/opportunity-slate?step=replace"], query.get("return_to"))


class SameOriginGuardTests(RouteTestCase):
    def test_mutation_without_origin_or_sec_fetch_site_is_refused(self):
        client, database = self.make_client()
        for method, path, form in MUTATION_ENDPOINTS:
            with self.subTest(path=path):
                response = getattr(client, method)(path, data=form)
                self.assertEqual(403, response.status_code)
        self.assertEqual([], database.calls)

    def test_cross_origin_mutation_is_refused(self):
        client, _ = self.make_client()
        response = client.post(
            "/opportunity-slate/source",
            data={"source_text": "role text"},
            headers={"Origin": "https://not-peerslate.example"},
        )
        self.assertEqual(403, response.status_code)


def _blueprint_rules():
    """The blueprint's rules, readable only once it is registered
    somewhere — mirrors
    ``tests.ask_pete_direct.test_endpoint._blueprint_rules``."""
    from flask import Flask

    probe = Flask("opportunity_slate_v2_rule_probe")
    probe.register_blueprint(routes.opportunity_slate_v2)
    return {
        rule.endpoint: rule
        for rule in probe.url_map.iter_rules()
        if rule.endpoint.startswith("opportunity_slate_v2.")
    }


class RateLimitPlanTests(unittest.TestCase):
    """The one control this blueprint cannot apply itself — app.py owns
    the Limiter instance and app.py is out of this lane — declared
    honestly. Mirrors
    ``tests.ask_pete_direct.test_endpoint.RateLimitPlanTests`` exactly,
    the established house pattern for a blueprint that cannot wire its
    own rate limit (independent review finding: nothing previously
    enforced or even asserted a limit, so a later registration could wire
    the blueprint in without ever attaching one)."""

    def test_the_plan_names_every_state_changing_endpoint_in_this_blueprint(self):
        """A route added later without a budget fails here, not in
        production."""
        state_changing = {
            endpoint
            for endpoint, rule in _blueprint_rules().items()
            if {"POST", "PUT", "PATCH", "DELETE"} & rule.methods
        }
        self.assertTrue(state_changing)
        self.assertEqual(state_changing, set(routes.PLANNED_RATE_LIMITS))

    def test_the_planned_budget_is_the_house_non_ai_write_floor_for_every_mutation(
        self,
    ):
        """R1 has no AI-calling route (architecture section 7 is entirely
        R2+), so every mutation shares one floor — the same non-AI write
        budget app.py's PS-OPPSLATE-001 loop already gives the legacy
        room's set_source/correct_source/confirm_source/delete_source."""
        self.assertEqual(7, len(routes.PLANNED_RATE_LIMITS))
        for endpoint, budget in routes.PLANNED_RATE_LIMITS.items():
            with self.subTest(endpoint=endpoint):
                self.assertEqual("30 per minute", budget)

    def test_no_parallel_limiter_was_invented_in_this_module(self):
        """No new dependency, no second unrelated counter — app.py owns
        the one Limiter instance."""
        source = (ROOT / "opportunity_slate_v2_routes.py").read_text(
            encoding="utf-8"
        )
        for forbidden in ("Limiter(", "get_remote_address", "flask_limiter"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_the_module_documents_where_the_limit_is_actually_applied(self):
        docstring = routes.__doc__
        self.assertIn("PLANNED_RATE_LIMITS", docstring)
        self.assertIn("cannot be wired from this file", docstring)
        self.assertIn("AFTER blueprint registration", docstring)
        self.assertIn("Limiter", docstring)


class LegacyIsolationTests(unittest.TestCase):
    """The v2 blueprint must be registrable and fully functional entirely
    on its own, with no shared module-level state that could bleed into
    the legacy room if both were ever imported in the same process (R5's
    eventual either/or registration)."""

    def test_v2_route_path_matches_the_architecture_and_the_legacy_path(self):
        self.assertEqual("/opportunity-slate", routes.ROOM_PATH)

    def test_v2_blueprint_name_is_distinct_from_the_legacy_blueprint(self):
        import opportunity_slate_routes as legacy

        self.assertNotEqual(
            legacy.opportunity_slate.name, routes.opportunity_slate_v2.name
        )

    def test_existing_opportunity_slate_test_suite_still_collects(self):
        """A weak proxy for 'legacy unaffected': the legacy test module
        still imports and its TestCases still load cleanly alongside this
        one in the same interpreter — proof this file's imports/patches
        have no import-time side effect on the legacy module."""
        import importlib

        import opportunity_slate_routes  # noqa: F401
        import services.opportunity_slate_service  # noqa: F401

        importlib.reload(opportunity_slate_routes)


# ---------------------------------------------------------------------------
# Headers: private, no-store, noindex on every response
# ---------------------------------------------------------------------------


class HeaderTests(RouteTestCase):
    def _assert_private_headers(self, response):
        self.assertEqual("private, no-store", response.headers.get("Cache-Control"))
        self.assertEqual(
            "noindex, nofollow, noarchive", response.headers.get("X-Robots-Tag")
        )

    def test_intake_response_headers(self):
        client, _ = self.make_client(rows=[None])
        response = client.get("/opportunity-slate")
        self._assert_private_headers(response)

    def test_flag_off_404_still_carries_private_headers(self):
        client, _ = self.make_client(enabled=False)
        response = client.get("/opportunity-slate")
        self._assert_private_headers(response)

    def test_redirect_response_still_carries_private_headers(self):
        client, _ = self.make_client(dev_user_key=None)
        response = client.get("/opportunity-slate")
        self._assert_private_headers(response)

    def test_unavailable_response_carries_retry_after(self):
        client, _ = self.make_client(error=DatabaseServiceError("down"))
        response = client.get("/opportunity-slate")
        self.assertEqual(503, response.status_code)
        self.assertEqual("5", response.headers.get("Retry-After"))
        self._assert_private_headers(response)


# ---------------------------------------------------------------------------
# Room rendering
# ---------------------------------------------------------------------------


class RoomRenderTests(RouteTestCase):
    """Every GET /opportunity-slate first calls
    usp_PurgeExpiredOpportunityWorkingData opportunistically (the room's own
    documented rule), which consumes the FIRST queued row on
    RecordingDatabase. Every fixture below therefore leads with an extra
    ``None`` for that call before the row(s) the read under test actually
    consumes.
    """

    def test_no_working_session_renders_stage_1_intake(self):
        client, _ = self.make_client(rows=[None, None])
        response = client.get("/opportunity-slate")
        self.assertEqual(200, response.status_code)
        body = response.get_data(as_text=True)
        self.assertIn("Bring in a role.", body)
        self.assertIn('name="source_text"', body)
        self.assertIn('<meta name="robots" content="noindex, nofollow, noarchive">', body)

    def test_working_session_renders_stage_2_review(self):
        client, _ = self.make_client(
            rows=[None, _working_row(), _identity_row()]
        )
        response = client.get("/opportunity-slate")
        self.assertEqual(200, response.status_code)
        body = response.get_data(as_text=True)
        self.assertIn("Review captured source", body)
        self.assertIn("Meridian Aerospace", body)
        self.assertIn("Captured role source", body)

    def test_stage_2_dom_order_puts_main_before_the_rail(self):
        """Independent review finding: architecture section 8 ('DOM order:
        main heading and dominant plane precede rails even where a rail
        sits visually left') is a binding [OBSERVED] rule. Checked on the
        rendered HTML, not just the template source, so a future template
        change that reintroduces the old order is caught here too."""
        client, _ = self.make_client(
            rows=[None, _working_row(), _identity_row()]
        )
        response = client.get("/opportunity-slate")
        body = response.get_data(as_text=True)
        main_index = body.index('class="os2-main"')
        rail_index = body.index('class="os2-rail"')
        self.assertGreater(rail_index, 0)
        self.assertLess(
            main_index,
            rail_index,
            "os2-main must precede os2-rail in the rendered DOM",
        )
        # And the dominant H1 itself lands before the rail's heading.
        h1_index = body.index("Review captured source")
        rail_heading_index = body.index("Current opportunity")
        self.assertLess(h1_index, rail_heading_index)

    def test_stage_2_identity_and_wording_maxlength_attributes_are_set(self):
        """Independent review finding: _source_review_context omitted
        max_identity_units/max_source_units, so all three maxlength
        attributes rendered as maxlength="" and the browser silently
        ignored every client-side cap. Server-side enforcement was never
        affected; this proves the client-side cap round-trips too."""
        client, _ = self.make_client(
            rows=[None, _working_row(), _identity_row()]
        )
        response = client.get("/opportunity-slate")
        body = response.get_data(as_text=True)
        self.assertIn('id="os2-employer-name"', body)
        self.assertIn('id="os2-role-title"', body)
        self.assertIn('id="os2-corrected-text"', body)
        # Exact values, not just "non-empty": 200 for the two identity
        # fields, 20000 for the captured-wording textarea.
        self.assertEqual(2, body.count('maxlength="200"'))
        self.assertIn('maxlength="20000"', body)
        self.assertNotIn('maxlength=""', body)

    def test_confirmed_source_shows_the_confirmed_label(self):
        """The rail's Captured/Confirmed label is a truth state, not
        decoration (VISUAL_AUDIT item 05)."""
        client, _ = self.make_client(
            rows=[
                None,
                _working_row(confirmed_version_number=1),
                _identity_row(),
            ]
        )
        response = client.get("/opportunity-slate")
        body = response.get_data(as_text=True)
        self.assertIn("Confirmed role source", body)
        self.assertNotIn("Captured role source", body)

    def test_no_identity_saved_yet_shows_the_honest_placeholder(self):
        client, _ = self.make_client(rows=[None, _working_row(), None])
        response = client.get("/opportunity-slate")
        body = response.get_data(as_text=True)
        self.assertIn("Employer not entered yet", body)
        self.assertIn("Role title not entered yet", body)

    def test_replace_step_shows_intake_even_with_a_working_session(self):
        client, _ = self.make_client(rows=[None, _working_row()])
        response = client.get("/opportunity-slate?step=replace")
        body = response.get_data(as_text=True)
        self.assertIn("Bring in a role.", body)
        self.assertIn('name="replace" value="1"', body)

    def test_database_error_on_read_is_a_truthful_503(self):
        client, _ = self.make_client(error=DatabaseServiceError("down"))
        response = client.get("/opportunity-slate")
        self.assertEqual(503, response.status_code)
        # Substring stops short of the apostrophe: Jinja autoescapes it to
        # &#39; in the rendered HTML, so a literal ASCII apostrophe would
        # never match the real response body.
        self.assertIn(
            "open your Opportunity Slate.",
            response.get_data(as_text=True),
        )

    def test_purge_failure_never_denies_the_room(self):
        """Maintenance-only: a purge failure must not deny the member
        their room (mirrors the legacy room's own rule)."""
        client, database = self.make_client(
            error=None, rows=[None]
        )

        def flaky_purge(user_key):
            raise DatabaseServiceError("purge unavailable")

        with patch.object(
            routes.opportunity_slate_v2_service,
            "purge_expired_working_data_for_owner",
            side_effect=flaky_purge,
        ):
            response = client.get("/opportunity-slate")
        self.assertEqual(200, response.status_code)


# ---------------------------------------------------------------------------
# Stage 1: intake (paste, upload, import)
# ---------------------------------------------------------------------------


class PasteIntakeTests(RouteTestCase):
    def test_happy_path_redirects_to_the_room(self):
        client, database = self.make_client(
            rows=[
                {
                    "outcome": "success",
                    "working_session_key": "11111111-1111-1111-1111-111111111111",
                    "source_key": "22222222-2222-2222-2222-222222222222",
                    "version_number": 1,
                    "workbench_state": "review_source",
                    "session_row_version": _binary(1),
                    "source_row_version": _binary(2),
                }
            ]
        )
        response = client.post(
            "/opportunity-slate/source",
            data={"source_text": "Employer role wording", "idempotency_key": "idem-1"},
            headers=same_origin_headers(),
        )
        self.assertEqual(302, response.status_code)
        self.assertEqual("usp_SaveOpportunitySourceForOwner", database.procedures[0])
        self.assertEqual("idem-1", database.parameters()["@IdempotencyKey"])
        self.assertEqual("pasted", database.parameters()["@CaptureMethod"])

    def test_empty_text_is_refused_before_any_database_call(self):
        client, database = self.make_client()
        response = client.post(
            "/opportunity-slate/source",
            data={"source_text": "   "},
            headers=same_origin_headers(),
        )
        self.assertEqual(400, response.status_code)
        self.assertIn("use that role text.", response.get_data(as_text=True))
        self.assertEqual([], database.calls)

    def test_oversize_text_is_refused_before_any_database_call(self):
        client, database = self.make_client()
        response = client.post(
            "/opportunity-slate/source",
            data={"source_text": "x" * (MAX_SOURCE_TEXT_UNITS + 1)},
            headers=same_origin_headers(),
        )
        self.assertEqual(400, response.status_code)
        self.assertEqual([], database.calls)

    def test_validation_failure_preserves_the_members_typed_text(self):
        client, _ = self.make_client()
        response = client.post(
            "/opportunity-slate/source",
            data={"source_text": "   "},
            headers=same_origin_headers(),
        )
        # The field is refused (blank), but a non-blank, over-length draft
        # must round-trip back into the editor rather than vanish.
        response = client.post(
            "/opportunity-slate/source",
            data={"source_text": "x" * (MAX_SOURCE_TEXT_UNITS + 500)},
            headers=same_origin_headers(),
        )
        body = response.get_data(as_text=True)
        self.assertIn("x" * 100, body)

    def test_idempotency_key_passes_through_unchanged_on_resubmission(self):
        """A double-click submits the SAME hidden idempotency_key value
        twice; the route must forward it unchanged rather than minting a
        fresh one per request, or the database-side dedup this key exists
        for could never engage."""
        client, database = self.make_client(
            rows=[
                {
                    "outcome": "existing",
                    "working_session_key": "11111111-1111-1111-1111-111111111111",
                    "source_key": "22222222-2222-2222-2222-222222222222",
                    "version_number": 1,
                    "workbench_state": "review_source",
                    "session_row_version": _binary(1),
                    "source_row_version": _binary(2),
                }
            ]
        )
        client.post(
            "/opportunity-slate/source",
            data={"source_text": "role text", "idempotency_key": "same-key-twice"},
            headers=same_origin_headers(),
        )
        self.assertEqual("same-key-twice", database.parameters()["@IdempotencyKey"])

    def test_a_conflict_outcome_is_a_409(self):
        client, _ = self.make_client(
            error=OpportunitySlateV2ServiceError("changed", code="changed")
        )
        response = client.post(
            "/opportunity-slate/source",
            data={"source_text": "role text"},
            headers=same_origin_headers(),
        )
        self.assertEqual(409, response.status_code)

    def test_database_outage_preserves_typed_replacement_and_unknown_outcome_truth(self):
        client, _ = self.make_client(error=DatabaseServiceError("outcome unknown"))
        response = client.post(
            "/opportunity-slate/source",
            data={
                "source_text": "Draft that must remain visible",
                "replace": "1",
            },
            headers=same_origin_headers(),
        )
        self.assertEqual(503, response.status_code)
        self.assertEqual("5", response.headers.get("Retry-After"))
        body = response.get_data(as_text=True)
        self.assertIn("Draft that must remain visible", body)
        self.assertIn('name="replace" value="1"', body)
        self.assertIn("could not verify whether the last change reached storage", body)


class IntakeFormBoundaryTests(RouteTestCase):
    def test_only_upload_opts_into_multipart_encoding(self):
        client, _ = self.make_client(rows=[None])
        response = client.get("/opportunity-slate")
        body = response.get_data(as_text=True)
        form_start = body.index('<form id="os2-source-form"')
        form_end = body.index(">", form_start)
        self.assertNotIn("multipart/form-data", body[form_start:form_end])
        self.assertIn('formenctype="multipart/form-data"', body)


class UploadIntakeTests(RouteTestCase):
    def test_happy_path_redirects_to_the_room(self):
        client, database = self.make_client(
            rows=[
                {
                    "outcome": "success",
                    "working_session_key": "11111111-1111-1111-1111-111111111111",
                    "source_key": "22222222-2222-2222-2222-222222222222",
                    "version_number": 1,
                    "workbench_state": "review_source",
                    "session_row_version": _binary(1),
                    "source_row_version": _binary(2),
                }
            ]
        )
        with patch.object(
            routes, "extract_uploaded_document", return_value=("Extracted text", False)
        ) as extractor:
            response = client.post(
                "/opportunity-slate/source/upload",
                data={"document": (__import__("io").BytesIO(b"content"), "role.pdf")},
                headers=same_origin_headers(),
                content_type="multipart/form-data",
            )
        self.assertEqual(302, response.status_code)
        extractor.assert_called_once()
        self.assertEqual("uploaded", database.parameters()["@CaptureMethod"])

    def test_unsupported_type_renders_the_honest_failure_card(self):
        client, database = self.make_client()
        with patch.object(
            routes,
            "extract_uploaded_document",
            side_effect=OpportunitySourceIntakeError("bad type"),
        ):
            response = client.post(
                "/opportunity-slate/source/upload",
                data={
                    "document": (__import__("io").BytesIO(b"content"), "role.exe"),
                    "source_text": "Typed draft survives upload failure",
                    "source_url": "https://example.com/draft-role",
                },
                headers=same_origin_headers(),
                content_type="multipart/form-data",
            )
        self.assertEqual(400, response.status_code)
        body = response.get_data(as_text=True)
        self.assertIn("read this document.", body)
        self.assertIn("Typed draft survives upload failure", body)
        self.assertIn("https://example.com/draft-role", body)
        self.assertEqual([], database.calls)

    def test_truncated_upload_redirects_to_the_inline_notice(self):
        client, database = self.make_client(
            rows=[
                {
                    "outcome": "success",
                    "working_session_key": "11111111-1111-1111-1111-111111111111",
                    "source_key": "22222222-2222-2222-2222-222222222222",
                    "version_number": 1,
                    "workbench_state": "review_source",
                    "session_row_version": _binary(1),
                    "source_row_version": _binary(2),
                },
            ]
        )
        with patch.object(
            routes, "extract_uploaded_document", return_value=("Extracted text", True)
        ):
            response = client.post(
                "/opportunity-slate/source/upload",
                data={"document": (__import__("io").BytesIO(b"content"), "role.pdf")},
                headers=same_origin_headers(),
                content_type="multipart/form-data",
            )
        self.assertEqual(302, response.status_code)
        self.assertIn("notice=upload-truncated", response.headers["Location"])

    def test_oversize_upload_body_is_refused_by_the_content_length_override(self):
        """The blueprint raises its own request body cap for exactly this
        route (MAX_UPLOAD_BYTES + framing headroom) rather than trusting
        the small app-wide default, mirroring the legacy room."""
        app, _database, patcher = make_app()
        self.addCleanup(patcher.stop)
        with app.test_request_context(
            "/opportunity-slate/source/upload", method="POST"
        ):
            routes._allow_bounded_document_upload()
            from flask import request

            self.assertIsNotNone(request.max_content_length)
            self.assertGreater(request.max_content_length, 2 * 1024 * 1024)


class ImportIntakeTests(RouteTestCase):
    def test_happy_path_redirects_to_the_room(self):
        client, database = self.make_client(
            rows=[
                {
                    "outcome": "success",
                    "working_session_key": "11111111-1111-1111-1111-111111111111",
                    "source_key": "22222222-2222-2222-2222-222222222222",
                    "version_number": 1,
                    "workbench_state": "review_source",
                    "session_row_version": _binary(1),
                    "source_row_version": _binary(2),
                }
            ]
        )
        with patch.object(
            routes,
            "extract_imported_link",
            return_value=("Extracted text", False, "https://example.com/job"),
        ) as extractor:
            response = client.post(
                "/opportunity-slate/source/import",
                data={"source_url": "https://example.com/job"},
                headers=same_origin_headers(),
            )
        self.assertEqual(302, response.status_code)
        extractor.assert_called_once_with("https://example.com/job")
        self.assertEqual("imported", database.parameters()["@CaptureMethod"])

    def test_ssrf_guard_failure_renders_the_honest_failure_card(self):
        """The guard itself (https-only, public-unicast pinning, redirect
        re-validation) lives entirely in the unchanged
        services/opportunity_source_intake_service.py and has its own
        dedicated test suite; this route's only job is to translate ANY
        OpportunitySourceIntakeError into the same honest card, never a
        partial save."""
        client, database = self.make_client()
        with patch.object(
            routes,
            "extract_imported_link",
            side_effect=OpportunitySourceIntakeError("private address"),
        ):
            response = client.post(
                "/opportunity-slate/source/import",
                data={
                    "source_url": "http://169.254.169.254/latest/meta-data/",
                    "source_text": "Typed draft survives import failure",
                },
                headers=same_origin_headers(),
            )
        self.assertEqual(400, response.status_code)
        body = response.get_data(as_text=True)
        self.assertIn("import that link.", body)
        self.assertIn("Typed draft survives import failure", body)
        self.assertIn("http://169.254.169.254/latest/meta-data/", body)
        self.assertEqual([], database.calls)


# ---------------------------------------------------------------------------
# Stage 2: source identity, correction, confirm, delete
# ---------------------------------------------------------------------------


class SourceIdentityRouteTests(RouteTestCase):
    def test_happy_path_preserves_the_other_visible_draft(self):
        client, database = self.make_client(
            rows=[
                _working_row(),
                _identity_row(),
                {"outcome": "success", "source_row_version": _binary(3)},
                _working_row(source_row_version=_binary(3)),
                _identity_row(),
            ]
        )
        response = client.post(
            "/opportunity-slate/source/identity",
            data=_review_form_data(corrected_text="Unsaved wording draft"),
            headers=same_origin_headers(),
        )
        self.assertEqual(200, response.status_code)
        body = response.get_data(as_text=True)
        self.assertIn("Employer and role title saved.", body)
        self.assertIn("Unsaved wording draft", body)
        self.assertEqual(
            "usp_SaveOpportunitySourceIdentityForOwner", database.procedures[2]
        )

    def test_changed_outcome_re_renders_stage_2_with_the_current_state(self):
        client, database = self.make_client(
            rows=[
                _working_row(),
                _identity_row(),
                {"outcome": "changed", "source_row_version": None},
                _working_row(),
                _identity_row(),
            ]
        )
        response = client.post(
            "/opportunity-slate/source/identity",
            data=_review_form_data(version_token="0000000000000001"),
            headers=same_origin_headers(),
        )
        self.assertEqual(409, response.status_code)
        self.assertIn("This role source changed.", response.get_data(as_text=True))

    def test_database_error_is_a_truthful_503_not_a_silent_loss(self):
        client, database = self.make_client(
            rows=[
                _working_row(),
                _identity_row(),
                DatabaseServiceError("write outcome unknown"),
                DatabaseServiceError("reload unavailable"),
            ]
        )
        response = client.post(
            "/opportunity-slate/source/identity",
            data=_review_form_data(employer_name="Attempted employer"),
            headers=same_origin_headers(),
        )
        self.assertEqual(503, response.status_code)
        body = response.get_data(as_text=True)
        self.assertIn("Attempted employer", body)
        self.assertIn("could not verify whether the last change reached storage", body)

    def test_an_oversize_employer_name_reports_the_correct_200_unit_cap(self):
        """Independent review finding: save_identity() routed every
        'too_long' code through FIELD_ERROR_MESSAGES, whose message names
        MAX_SOURCE_TEXT_UNITS (20,000, the captured-wording cap) — so an
        over-200-character Employer/Role title was told 'longer than
        20,000 characters', a false statement about a 200-unit field.
        Server-side enforcement (the service raising 'too_long' at all)
        was never wrong; only the copy was."""
        client, database = self.make_client(
            rows=[_working_row(), _identity_row(), _working_row(), _identity_row()]
        )
        response = client.post(
            "/opportunity-slate/source/identity",
            data=_review_form_data(
                employer_name="x" * (MAX_IDENTITY_FIELD_UNITS + 1)
            ),
            headers=same_origin_headers(),
        )
        self.assertEqual(400, response.status_code)
        body = response.get_data(as_text=True)
        self.assertIn("That text is longer than 200 characters.", body)
        self.assertNotIn("longer than 20,000 characters", body)
        # The oversize value is refused before the procedure call. The two
        # pre-write reads establish a safe fallback and the two post-refusal
        # reads render current stored state beside the attempted value.
        self.assertEqual(
            [
                "usp_GetOpportunityWorkingSessionForOwner",
                "usp_GetOpportunitySourceIdentityForOwner",
                "usp_GetOpportunityWorkingSessionForOwner",
                "usp_GetOpportunitySourceIdentityForOwner",
            ],
            database.procedures,
        )


class StageTwoPreloadOutageTests(RouteTestCase):
    def test_every_stage_two_mutation_preserves_posted_drafts_before_a_write(self):
        endpoints = (
            "/opportunity-slate/source/identity",
            "/opportunity-slate/source/corrections",
            "/opportunity-slate/source/confirm",
            "/opportunity-slate/source/delete",
        )
        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                client, database = self.make_client(
                    rows=[DatabaseServiceError("pre-write read unavailable")]
                )
                response = client.post(
                    endpoint,
                    data=_review_form_data(
                        employer_name="Preserved employer draft",
                        role_title="Preserved role draft",
                        corrected_text="Preserved wording draft",
                    ),
                    headers=same_origin_headers(),
                )
                self.assertEqual(503, response.status_code)
                self.assertEqual("5", response.headers.get("Retry-After"))
                body = response.get_data(as_text=True)
                self.assertIn("Review draft preserved", body)
                self.assertIn("Preserved employer draft", body)
                self.assertIn("Preserved role draft", body)
                self.assertIn("Preserved wording draft", body)
                self.assertIn("No save, confirmation, or deletion was attempted", body)
                self.assertEqual(
                    ["usp_GetOpportunityWorkingSessionForOwner"],
                    database.procedures,
                )


class CorrectionRouteTests(RouteTestCase):
    def test_happy_path_preserves_the_other_visible_draft(self):
        client, database = self.make_client(
            rows=[
                _working_row(),
                _identity_row(),
                {"outcome": "success", "source_row_version": _binary(3), "version_number": 1},
                _working_row(
                    source_row_version=_binary(3),
                    member_corrected_text="Corrected employer wording",
                ),
                _identity_row(),
            ]
        )
        response = client.post(
            "/opportunity-slate/source/corrections",
            data=_review_form_data(
                employer_name="Unsaved employer draft",
                corrected_text="Corrected employer wording",
            ),
            headers=same_origin_headers(),
        )
        self.assertEqual(200, response.status_code)
        body = response.get_data(as_text=True)
        self.assertIn("Captured wording saved.", body)
        self.assertIn("Unsaved employer draft", body)
        self.assertEqual(
            "usp_CorrectOpportunitySourceForOwner", database.procedures[2]
        )
        self.assertEqual(
            "Corrected employer wording", database.parameters(2)["@CorrectedText"]
        )

    def test_conflict_after_confirmation_is_a_409_with_current_wording(self):
        """Correction-after-confirm clears the confirmation triple at the
        database layer (PS-OPPSLATE-001's own CHECK); at this layer the
        contract under test is that a 'changed' outcome from the procedure
        surfaces as a 409 with the member's live server state re-read, not
        a silently accepted stale write."""
        client, database = self.make_client(
            rows=[
                _working_row(confirmed_version_number=1),
                _identity_row(),
                {"outcome": "changed", "source_row_version": None, "version_number": None},
                _working_row(confirmed_version_number=1),
                _identity_row(),
            ]
        )
        response = client.post(
            "/opportunity-slate/source/corrections",
            data=_review_form_data(
                version_token="0000000000000001", corrected_text="Late edit"
            ),
            headers=same_origin_headers(),
        )
        self.assertEqual(409, response.status_code)
        self.assertIn("This role source changed.", response.get_data(as_text=True))

    def test_database_failure_keeps_the_attempted_wording_visible(self):
        client, database = self.make_client(
            rows=[
                _working_row(),
                _identity_row(),
                DatabaseServiceError("write outcome unknown"),
                DatabaseServiceError("reload unavailable"),
            ]
        )
        response = client.post(
            "/opportunity-slate/source/corrections",
            data=_review_form_data(corrected_text="Attempted correction remains"),
            headers=same_origin_headers(),
        )
        self.assertEqual(503, response.status_code)
        body = response.get_data(as_text=True)
        self.assertIn("Attempted correction remains", body)
        self.assertIn("could not verify whether the last change reached storage", body)


class ConfirmRouteTests(RouteTestCase):
    def test_happy_path_redirects_to_the_room(self):
        client, database = self.make_client(
            rows=[
                _working_row(),
                _identity_row(),
                {
                    "outcome": "success",
                    "source_row_version": _binary(2),
                    "confirmed_version_number": 1,
                }
            ]
        )
        response = client.post(
            "/opportunity-slate/source/confirm",
            data=_review_form_data(),
            headers=same_origin_headers(),
        )
        self.assertEqual(302, response.status_code)
        self.assertEqual(
            "usp_ConfirmOpportunitySourceForOwner", database.procedures[2]
        )

    def test_confirm_calls_no_ai_and_creates_no_requirement_set(self):
        """R1 has no interpretation step; confirming must not do anything
        beyond recording the confirmation triple."""
        client, database = self.make_client(
            rows=[
                _working_row(),
                _identity_row(),
                {
                    "outcome": "success",
                    "source_row_version": _binary(2),
                    "confirmed_version_number": 1,
                }
            ]
        )
        client.post(
            "/opportunity-slate/source/confirm",
            data=_review_form_data(),
            headers=same_origin_headers(),
        )
        self.assertEqual(
            [
                "usp_GetOpportunityWorkingSessionForOwner",
                "usp_GetOpportunitySourceIdentityForOwner",
                "usp_ConfirmOpportunitySourceForOwner",
            ],
            database.procedures,
        )

    def test_visible_unsaved_edits_are_never_confirmed(self):
        client, database = self.make_client(
            rows=[
                _working_row(),
                _identity_row(),
                _working_row(),
                _identity_row(),
            ]
        )
        response = client.post(
            "/opportunity-slate/source/confirm",
            data=_review_form_data(corrected_text="Visible but unsaved wording"),
            headers=same_origin_headers(),
        )
        self.assertEqual(409, response.status_code)
        body = response.get_data(as_text=True)
        self.assertIn("Save your visible edits before confirming.", body)
        self.assertIn("Visible but unsaved wording", body)
        self.assertNotIn("usp_ConfirmOpportunitySourceForOwner", database.procedures)

    def test_browser_line_ending_normalization_is_not_a_false_dirty_edit(self):
        client, database = self.make_client(
            rows=[
                _working_row(original_text="Line one\nLine two"),
                _identity_row(),
                {
                    "outcome": "success",
                    "source_row_version": _binary(2),
                    "confirmed_version_number": 1,
                },
            ]
        )
        response = client.post(
            "/opportunity-slate/source/confirm",
            data=_review_form_data(corrected_text="Line one\r\nLine two"),
            headers=same_origin_headers(),
        )
        self.assertEqual(302, response.status_code)
        self.assertIn("usp_ConfirmOpportunitySourceForOwner", database.procedures)


class DeleteRouteTests(RouteTestCase):
    def test_happy_path_redirects_to_the_room(self):
        client, database = self.make_client(
            rows=[
                _working_row(),
                _identity_row(),
                {"outcome": "success", "deleted_version_count": 1},
            ]
        )
        response = client.post(
            "/opportunity-slate/source/delete",
            data={
                "session_key": "11111111-1111-1111-1111-111111111111",
                "session_version_token": _binary(1).hex(),
            },
            headers=same_origin_headers(),
        )
        self.assertEqual(302, response.status_code)
        self.assertEqual(
            "usp_DeleteOpportunityWorkingSessionForOwner", database.procedures[2]
        )

    def test_refused_delete_shows_current_stored_state(self):
        client, database = self.make_client(
            rows=[
                _working_row(),
                _identity_row(),
                {"outcome": "changed", "deleted_version_count": None},
                _working_row(),
                _identity_row(),
            ]
        )
        response = client.post(
            "/opportunity-slate/source/delete",
            data={
                "session_key": "11111111-1111-1111-1111-111111111111",
                "session_version_token": "0000000000000001",
            },
            headers=same_origin_headers(),
        )
        body = response.get_data(as_text=True)
        self.assertIn("delete request was refused", body)
        self.assertIn("current stored state is shown", body)

    def test_database_failure_on_delete_reports_unknown_outcome(self):
        client, database = self.make_client(
            rows=[
                _working_row(),
                _identity_row(),
                DatabaseServiceError("delete outcome unknown"),
                DatabaseServiceError("reload unavailable"),
            ],
        )
        response = client.post(
            "/opportunity-slate/source/delete",
            data={
                "session_key": "11111111-1111-1111-1111-111111111111",
                "session_version_token": _binary(1).hex(),
            },
            headers=same_origin_headers(),
        )
        self.assertEqual(503, response.status_code)
        self.assertIn(
            "could not verify whether the last change reached storage",
            response.get_data(as_text=True),
        )


if __name__ == "__main__":
    unittest.main()
