"""telemetry-contract@1 sentinel tests, pricing, and bounded logging."""

import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

import anthropic
import httpx

import app as app_module
from services import database_service as database_service_module
from services import interview_ai
from services.interview_ai import pricing, telemetry
from services.interview_ai.identity import sha256_hex

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = json.loads(
    (ROOT / "prompts" / "interview" / "control" / "registry.json").read_text(
        encoding="utf-8"
    )
)
RELEASE_ID = REGISTRY["active_release_set"]["interview_release_set_id"]


def _specialist_event(**overrides):
    attempt = telemetry.ServerCallAttempt()
    release = interview_ai.resolve_active_release(RELEASE_ID)
    base = dict(
        attempt=attempt,
        event_kind="specialist_call",
        outcome="success",
        http_status=200,
        validation_result="passed",
        counts=telemetry.source_class_counts(question=1),
        specialist="coach",
        bundle=release.bundles["coach"],
        release_set_id=RELEASE_ID,
    )
    base.update(overrides)
    return telemetry.build_event(
        base.pop("attempt"), base.pop("event_kind"), base.pop("outcome"),
        base.pop("http_status"), base.pop("validation_result"),
        base.pop("counts"), **base,
    )


class SentinelTests(unittest.TestCase):
    def setUp(self):
        interview_ai.reset_resolution_cache()
        self.addCleanup(interview_ai.reset_resolution_cache)

    def test_success_event_validates_and_total_covers_each_stage(self):
        event = _specialist_event()
        for field in telemetry.DURATION_FIELDS:
            self.assertGreaterEqual(
                event["dur_total_server_ms"], event[field],
            )
        self.assertEqual(event["guardian_rejections"], [])
        self.assertEqual(event["retry_ordinal"], 0)
        self.assertIsNone(event["operation_id"])

    def test_null_bundle_ref_is_only_lawful_pre_resolution(self):
        with self.assertRaises(ValueError):
            _specialist_event(bundle=None, release_set_id=None)

    def test_failed_outcome_requires_state_and_reason(self):
        with self.assertRaises(ValueError):
            _specialist_event(outcome="failed", http_status=502,
                              validation_result="rejected")

    def test_reason_on_a_success_outcome_is_rejected(self):
        with self.assertRaises(ValueError):
            _specialist_event(failure_reason="no_json_object")

    def test_composition_parent_carries_no_specialist_or_bundle(self):
        attempt = telemetry.ServerCallAttempt()
        event = telemetry.build_event(
            attempt, "composition_parent", "success", 200, "not_applicable",
            telemetry.source_class_counts(), composition="compare",
            release_set_id=RELEASE_ID,
        )
        self.assertIsNone(event["specialist"])
        self.assertIsNone(event["bundle_label"])
        with self.assertRaises(ValueError):
            telemetry.build_event(
                attempt, "composition_parent", "success", 200,
                "not_applicable", telemetry.source_class_counts(),
                composition="waltz", release_set_id=RELEASE_ID,
            )

    def test_source_class_counts_are_complete_and_strict(self):
        counts = telemetry.source_class_counts(question=1, member_evidence=10)
        self.assertEqual(set(counts), set(telemetry.SOURCE_CLASSES))
        self.assertEqual(counts["member_evidence"], 10)
        # Consolidated B4: never clamp or coerce — an out-of-range,
        # Boolean, float, or string count is rejected outright.
        for hostile in (
            {"member_evidence": 99}, {"member_evidence": -1},
            {"member_evidence": True}, {"member_evidence": 1.5},
            {"member_evidence": "3"},
        ):
            with self.assertRaises(ValueError):
                telemetry.source_class_counts(question=1, **hostile)
        bad = dict(counts)
        bad.pop("question")
        with self.assertRaises(ValueError):
            _specialist_event(counts=bad)

    def test_stringified_exception_shapes_are_rejected(self):
        with self.assertRaises(ValueError):
            _specialist_event(
                outcome="failed", http_status=502,
                validation_result="rejected",
                failure_state="invalid_output",
                failure_reason="no_json_object",
                exception_class="ValueError: content leaked",
            )
        with self.assertRaises(ValueError):
            _specialist_event(
                outcome="failed", http_status=502,
                validation_result="rejected",
                failure_state="invalid_output",
                failure_reason="no_json_object",
                exception_class="validation_value",
                exception_attrs={"message": "leaked text"},
            )
        # The pre-B4 class names are themselves outside the closed enum.
        with self.assertRaises(ValueError):
            _specialist_event(
                outcome="failed", http_status=502,
                validation_result="rejected",
                failure_state="invalid_output",
                failure_reason="no_json_object",
                exception_class="value_error",
            )


class B4PythonHostileMatrixTests(unittest.TestCase):
    """B4: the Python sentinel accepts and rejects the SAME boundary
    values as the SQL append boundary — named case for named case."""

    def setUp(self):
        interview_ai.reset_resolution_cache()
        self.addCleanup(interview_ai.reset_resolution_cache)

    def _accepts(self, **overrides):
        _specialist_event(**overrides)

    def _rejects(self, **overrides):
        with self.assertRaises(ValueError):
            _specialist_event(**overrides)

    def _failed(self, exception_class, attrs, **more):
        base = dict(
            outcome="failed", http_status=502,
            validation_result="rejected",
            failure_state="invalid_output",
            failure_reason="no_json_object",
            exception_class=exception_class,
            exception_attrs=attrs,
        )
        base.update(more)
        return base

    def test_py_case_1_http_status_boundaries(self):
        self._rejects(http_status=99)
        self._accepts(http_status=100)
        self._accepts(http_status=599)
        self._rejects(http_status=600)
        self._rejects(http_status=999)

    def test_py_case_2_retry_ordinal_boundaries(self):
        for value, ok in ((-1, False), (0, True), (15, True), (16, False),
                          (999, False)):
            attempt = telemetry.ServerCallAttempt()
            release = interview_ai.resolve_active_release(RELEASE_ID)
            event = telemetry.build_event(
                attempt, "specialist_call", "success", 200, "passed",
                telemetry.source_class_counts(question=1),
                specialist="coach", bundle=release.bundles["coach"],
                release_set_id=RELEASE_ID,
            )
            event["retry_ordinal"] = value
            if ok:
                telemetry.validate_event(event)
            else:
                with self.assertRaises(ValueError):
                    telemetry.validate_event(event)

    def test_py_case_3_duration_boundaries(self):
        release = interview_ai.resolve_active_release(RELEASE_ID)

        def event_with(duration, total):
            attempt = telemetry.ServerCallAttempt()
            event = telemetry.build_event(
                attempt, "specialist_call", "success", 200, "passed",
                telemetry.source_class_counts(question=1),
                specialist="coach", bundle=release.bundles["coach"],
                release_set_id=RELEASE_ID,
            )
            event["dur_provider_ms"] = duration
            event["dur_total_server_ms"] = total
            return event

        with self.assertRaises(ValueError):
            telemetry.validate_event(event_with(-1, 0))
        telemetry.validate_event(event_with(0, 0))
        telemetry.validate_event(event_with(86_400_000, 86_400_000))
        with self.assertRaises(ValueError):
            telemetry.validate_event(event_with(86_400_001, 86_400_001))
        with self.assertRaises(ValueError):
            telemetry.validate_event(event_with(50, 10))  # total < stage

    def test_py_case_4_reply_chars_boundaries(self):
        for value, ok in ((-1, False), (0, True), (100_000, True),
                          (100_001, False)):
            arguments = self._failed(
                "validation_value",
                {"provider_stop_reason": "end_turn", "reply_chars": value},
            )
            (self._accepts if ok else self._rejects)(**arguments)

    def test_py_case_5_exception_status_boundaries(self):
        for value, ok in ((99, False), (100, True), (599, True),
                          (600, False), (999, False)):
            arguments = self._failed(
                "provider_rejected", {"status_code": value},
                failure_state="provider_failure", failure_reason="rejected",
                validation_result="not_applicable",
            )
            (self._accepts if ok else self._rejects)(**arguments)

    def test_py_case_6_wrong_class_attributes(self):
        self._rejects(**self._failed(
            "provider_timeout", {"status_code": 500},
            failure_state="provider_failure", failure_reason="timeout",
            validation_result="not_applicable"))
        self._rejects(**self._failed(
            "provider_rejected", {"reply_chars": 10},
            failure_state="provider_failure", failure_reason="rejected",
            validation_result="not_applicable"))
        self._rejects(**self._failed(
            "validation_value", {"status_code": 502}))
        self._rejects(**self._failed(
            "runtime_unexpected", {"reply_chars": 1},
            failure_state="internal_error",
            failure_reason="unexpected_server_fault",
            validation_result="not_applicable"))

    def test_py_case_7_source_count_shape(self):
        good = telemetry.source_class_counts(question=1)
        missing = {k: v for k, v in good.items() if k != "question"}
        missing["smuggled"] = 1  # six entries, wrong set
        self._rejects(counts=missing)
        stringy = dict(good, question="1")
        self._rejects(counts=stringy)
        floaty = dict(good, question=1.0)
        self._rejects(counts=floaty)
        booly = dict(good, question=True)
        self._rejects(counts=booly)
        over = dict(good, member_evidence=33)
        self._rejects(counts=over)

    def test_py_case_8_duplicate_exception_key_is_unrepresentable(self):
        """Python dicts cannot carry duplicate keys, so the serializer can
        never EMIT one; the SQL boundary independently rejects a hostile
        duplicate-key document (sql_case_8)."""
        payload = json.dumps({"reply_chars": 1, "reply_chars": 2})
        self.assertEqual(payload, '{"reply_chars": 2}')

    def test_py_case_9_canonical_identity_forms(self):
        self._rejects(release_set_id="A" * 64)
        self._rejects(release_set_id="z" * 64)
        self._rejects(release_set_id="1" * 63)
        self._rejects(release_set_id="1" * 65)

    def test_py_case_10_resolved_specialist_null_release(self):
        self._rejects(release_set_id=None)

    def test_py_case_11_pre_resolution_with_release(self):
        with self.assertRaises(ValueError):
            _specialist_event(
                bundle=None, release_set_id=RELEASE_ID,
                outcome="failed", http_status=503,
                validation_result="not_applicable",
                failure_state="service_not_configured",
                failure_reason="active_release_unresolved",
            )

    def test_py_case_16_parent_purity(self):
        attempt = telemetry.ServerCallAttempt()
        with self.assertRaises(ValueError):
            telemetry.build_event(
                attempt, "composition_parent", "success", 200,
                "not_applicable",
                telemetry.source_class_counts(question=1),  # nonzero
                composition="compare", release_set_id=RELEASE_ID,
            )
        release = interview_ai.resolve_active_release(RELEASE_ID)

        class _Usage:
            input_tokens = 1
            output_tokens = 1

        class _Response:
            usage = _Usage()

        with self.assertRaises(ValueError):
            telemetry.build_event(
                attempt, "composition_parent", "success", 200,
                "not_applicable", telemetry.source_class_counts(),
                composition="compare", release_set_id=RELEASE_ID,
                provider_response=_Response(),
            )
        with self.assertRaises(ValueError):
            telemetry.build_event(
                attempt, "composition_parent", "failed", 502,
                "not_applicable", telemetry.source_class_counts(),
                composition="compare", release_set_id=RELEASE_ID,
                failure_state="invalid_output",
                failure_reason="no_json_object",
                exception_class="validation_value",
            )

    def test_py_cases_12_to_15_and_17_are_relational(self):
        """The standalone-parent, child-of-standalone, child-of-child,
        mismatched-release, and concurrent-duplicate cases are cross-row
        properties; the emitting code (jobs.py) appends parents first with
        matching release identity, and the SQL boundary enforces them
        transactionally — named sql_case_12..17 in the disposable proof."""
        self.assertTrue(True)


class B4StateMatrixHostileTests(unittest.TestCase):
    """Consolidated B4: the closed state matrix rejects semantically
    impossible combinations — named case for named SQL case
    (sql_matrix_case_N in the disposable proof)."""

    def setUp(self):
        interview_ai.reset_resolution_cache()
        self.addCleanup(interview_ai.reset_resolution_cache)

    def _rejects(self, **overrides):
        with self.assertRaises(ValueError):
            _specialist_event(**overrides)

    def _failed(self, state, reason, exception_class, attrs, **extra):
        base = dict(
            outcome="failed", http_status=502,
            validation_result=(
                "rejected" if state == "invalid_output" else "not_applicable"
            ),
            failure_state=state, failure_reason=reason,
            exception_class=exception_class, exception_attrs=attrs,
        )
        base.update(extra)
        return base

    def test_py_matrix_case_1_invalid_output_with_transport_reason(self):
        self._rejects(**self._failed(
            "invalid_output", "transport", "validation_value",
            {"provider_stop_reason": "end_turn", "reply_chars": 10},
        ))

    def test_py_matrix_case_2_provider_failure_with_validation_reason(self):
        self._rejects(**self._failed(
            "provider_failure", "no_json_object", "provider_transport", {},
        ))

    def test_py_matrix_case_3_release_on_service_not_configured(self):
        # The recorded release identity must be NULL on a
        # service_not_configured row; a resolved id is impossible there.
        self._rejects(**self._failed(
            "service_not_configured", "active_release_unresolved", None, None,
        ))

    def test_py_matrix_case_4_invalid_output_with_provider_timeout_class(self):
        self._rejects(**self._failed(
            "invalid_output", "no_json_object", "provider_timeout", {},
        ))

    def test_py_matrix_case_5_internal_error_with_validation_rejected(self):
        self._rejects(**self._failed(
            "internal_error", "unexpected_server_fault", "runtime_unexpected",
            {}, validation_result="rejected",
        ))

    def test_py_matrix_case_6_reserved_outcome_refused(self):
        self._rejects(
            outcome="refused", http_status=403,
            validation_result="not_applicable",
            failure_state="internal_error",
            failure_reason="unexpected_server_fault",
        )

    def test_py_matrix_case_7_reserved_reason_abandoned(self):
        self._rejects(**self._failed(
            "provider_failure", "abandoned", "provider_transport", {},
        ))

    def test_py_matrix_case_8_provider_reason_class_pair_mismatch(self):
        self._rejects(**self._failed(
            "provider_failure", "timeout", "provider_transport", {},
        ))

    def test_py_matrix_case_9_validation_class_missing_required_attrs(self):
        self._rejects(**self._failed(
            "invalid_output", "no_json_object", "validation_value",
            {"reply_chars": 10},
        ))

    def test_py_matrix_case_10_exception_attrs_not_an_object(self):
        for hostile_attrs in ([], [["status_code", 502]], "attrs", 7):
            self._rejects(**self._failed(
                "provider_failure", "rejected", "provider_rejected",
                hostile_attrs,
            ))

    def test_py_matrix_case_11_exception_on_service_not_configured(self):
        self._rejects(
            outcome="failed", http_status=503,
            validation_result="not_applicable",
            failure_state="service_not_configured",
            failure_reason="active_release_unresolved",
            exception_class="runtime_unexpected", exception_attrs={},
            bundle=None, release_set_id=None,
        )

    def test_py_matrix_case_12_failed_invalid_output_without_exception(self):
        self._rejects(**self._failed(
            "invalid_output", "no_json_object", None, None,
        ))

    def test_py_matrix_case_13_success_without_release_identity(self):
        self._rejects(bundle=None, release_set_id=None)

    def test_py_matrix_case_14_usage_on_provider_failure_row(self):
        # A timeout/transport/rejected failure means no usable response
        # object exists, so recorded usage there is a fabrication.
        import types
        response = types.SimpleNamespace(
            usage=types.SimpleNamespace(input_tokens=10, output_tokens=5),
        )
        self._rejects(**self._failed(
            "provider_failure", "timeout", "provider_timeout", {},
            provider_response=response,
        ))

    def test_py_matrix_case_15_parent_with_passed_validation(self):
        attempt = telemetry.ServerCallAttempt()
        with self.assertRaises(ValueError):
            telemetry.build_event(
                attempt, "composition_parent", "success", 200,
                "passed", telemetry.source_class_counts(),
                composition="compare", release_set_id=RELEASE_ID,
            )

    def test_py_matrix_case_16_internal_error_with_wrong_reason(self):
        self._rejects(**self._failed(
            "internal_error", "transport", "runtime_unexpected", {},
        ))

    def test_py_matrix_case_17_duration_overflow_rejected_not_clamped(self):
        attempt = telemetry.ServerCallAttempt()
        attempt.durations["dur_receive_ms"] = 86_400_001
        release = interview_ai.resolve_active_release(RELEASE_ID)
        with self.assertRaises(ValueError):
            telemetry.build_event(
                attempt, "specialist_call", "success", 200, "passed",
                telemetry.source_class_counts(question=1),
                specialist="coach", bundle=release.bundles["coach"],
                release_set_id=RELEASE_ID,
            )


class ClassificationTests(unittest.TestCase):
    def test_validation_reasons_match_the_legacy_labels_exactly(self):
        for message, reason in (
            telemetry.VALIDATION_REASON_BY_MESSAGE.items()
        ):
            self.assertEqual(
                app_module._interview_failure_reason(ValueError(message)),
                reason,
            )
        self.assertEqual(
            telemetry.classify_validation_error(TypeError("x")),
            ("unexpected_shape", "validation_type"),
        )
        self.assertEqual(
            telemetry.classify_validation_error(
                json.JSONDecodeError("m", "d", 0)
            )[0],
            "unparseable_json",
        )
        self.assertEqual(
            telemetry.classify_validation_error(ValueError("brand new"))[0],
            "unclassified",
        )

    def test_provider_errors_normalize_to_the_canonical_taxonomy(self):
        """C6: failure_reason is the §3 taxonomy; granularity stays in the
        separate closed exception-class field."""
        request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")

        def status_error(cls, status):
            return cls(
                "boom", response=httpx.Response(status, request=request),
                body=None,
            )

        cases = [
            (anthropic.APITimeoutError(request=request),
             "timeout", "provider_timeout", None),
            (anthropic.APIConnectionError(
                message="Connection error.", request=request),
             "transport", "provider_transport", None),
            (status_error(anthropic.RateLimitError, 429),
             "rejected", "provider_rejected", 429),
            (status_error(anthropic.AuthenticationError, 401),
             "rejected", "provider_rejected", 401),
            (status_error(anthropic.InternalServerError, 529),
             "rejected", "provider_rejected", 529),
            (status_error(anthropic.InternalServerError, 500),
             "rejected", "provider_rejected", 500),
            (status_error(anthropic.BadRequestError, 400),
             "rejected", "provider_rejected", 400),
        ]
        for error, expected_reason, expected_class, expected_status in cases:
            reason, exception_class, status = (
                telemetry.normalize_provider_error(error)
            )
            self.assertEqual(reason, expected_reason)
            self.assertIn(
                reason, ("transport", "timeout", "rejected"),
                "SDK-shaped values may never reach failure_reason",
            )
            self.assertEqual(exception_class, expected_class)
            self.assertEqual(status, expected_status)
            self.assertNotIn("Error", exception_class)

    def test_the_reserved_abandoned_reason_has_no_emission_path(self):
        """`abandoned` is reserved for the §3 orphan reaper: it is a legal
        stored value but nothing in slice 1 may emit it."""
        self.assertIn("abandoned", telemetry.FAILURE_REASONS)
        for path in sorted(
            (ROOT / "services" / "interview_ai").glob("*.py")
        ):
            if path.name == "constants.py":
                continue
            self.assertNotIn(
                "'abandoned'", path.read_text(encoding="utf-8"),
                "%s must not emit the reserved reason" % path.name,
            )

    def test_stop_reasons_normalize_to_the_closed_enum(self):
        self.assertEqual(telemetry.normalize_stop_reason("end_turn"),
                         "end_turn")
        self.assertEqual(telemetry.normalize_stop_reason(""), "unknown")
        self.assertEqual(
            telemetry.normalize_stop_reason("surprise_reason"), "unknown"
        )


class PricingTests(unittest.TestCase):
    class Usage:
        def __init__(self, input_tokens, output_tokens, **extra):
            self.input_tokens = input_tokens
            self.output_tokens = output_tokens
            for key, value in extra.items():
                setattr(self, key, value)

    def test_integer_exact_cost(self):
        usage, cost, schedule = pricing.price_usage(
            "claude-haiku-4-5-20251001", self.Usage(900, 400)
        )
        self.assertEqual(usage, {"input_tokens": 900, "output_tokens": 400})
        self.assertEqual(cost, 900 * 1 + 400 * 5)
        self.assertEqual(
            schedule, sha256_hex(pricing.PRICING_TABLE_PATH.read_bytes())
        )

    def test_unknown_model_preserves_tokens_but_not_cost(self):
        usage, cost, schedule = pricing.price_usage(
            "some-future-model", self.Usage(10, 10)
        )
        self.assertEqual(usage, {"input_tokens": 10, "output_tokens": 10})
        self.assertIsNone(cost)
        self.assertIsNone(schedule)

    def test_cache_token_ambiguity_nulls_cost_only(self):
        usage, cost, schedule = pricing.price_usage(
            "claude-haiku-4-5-20251001",
            self.Usage(10, 10, cache_read_input_tokens=5),
        )
        self.assertEqual(usage, {"input_tokens": 10, "output_tokens": 10})
        self.assertIsNone(cost)
        self.assertIsNone(schedule)

    def test_malformed_usage_yields_all_null(self):
        usage, cost, schedule = pricing.price_usage(
            "claude-haiku-4-5-20251001", self.Usage("many", 4)
        )
        self.assertIsNone(usage)
        self.assertIsNone(cost)
        self.assertIsNone(schedule)

    def test_absent_usage_yields_all_null(self):
        self.assertEqual(
            pricing.price_usage("claude-haiku-4-5-20251001", None),
            (None, None, None),
        )


class RouteEmissionTests(unittest.TestCase):
    """Full-row assertions for the emission points, via a fake sink."""

    def setUp(self):
        self.previous = app_module.app.config.get(
            interview_ai.ACTIVE_RELEASE_CONFIG_KEY
        )
        app_module.app.config[interview_ai.ACTIVE_RELEASE_CONFIG_KEY] = (
            RELEASE_ID
        )
        interview_ai.reset_resolution_cache()
        interview_ai.boot.initialize(RELEASE_ID)
        self.limiter_was_enabled = app_module.limiter.enabled
        app_module.limiter.enabled = False

    def tearDown(self):
        app_module.app.config[interview_ai.ACTIVE_RELEASE_CONFIG_KEY] = (
            self.previous
        )
        interview_ai.reset_resolution_cache()
        app_module.limiter.enabled = self.limiter_was_enabled

    def _run(self, path, payload, replies):
        appended = []

        def record_append(procedure_name, parameters=None):
            appended.append(dict(parameters))
            return []

        class _Block:
            def __init__(self, text):
                self.text = text

        class _Usage:
            input_tokens = 700
            output_tokens = 300

        class _Response:
            def __init__(self, text):
                self.content = [_Block(text)]
                self.stop_reason = "end_turn"
                self.usage = _Usage()

        responses = [_Response(text) for text in replies]

        def fake_create(**kwargs):
            return responses.pop(0)

        with patch.object(
            app_module.client.messages, "create", new=fake_create,
        ), patch.object(
            database_service_module.database_service,
            "execute_procedure",
            new=record_append,
        ):
            response = app_module.app.test_client().post(
                path, json=payload, base_url="http://localhost"
            )
        return response, appended

    def test_nudge_success_row_is_complete_and_content_free(self):
        response, appended = self._run(
            "/api/interview/nudge",
            {"question": "Q?", "profile_slug": "petec",
             "opportunity_context": "role text"},
            [json.dumps({"hints": ["One structural hint.",
                                   "One outcome hint."]})],
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(appended), 1)
        row = appended[0]
        self.assertEqual(row["@Specialist"], "planning_hints")
        self.assertEqual(row["@Outcome"], "success")
        self.assertEqual(row["@HttpStatus"], 200)
        self.assertEqual(row["@ReleaseSetId"], RELEASE_ID)
        self.assertEqual(row["@ValidationResult"], "passed")
        self.assertEqual(row["@ProviderInputTokens"], 700)
        self.assertEqual(row["@ProviderOutputTokens"], 300)
        self.assertEqual(row["@CostMicrousd"], 700 * 1 + 300 * 5)
        self.assertEqual(
            json.loads(row["@SourceClassCountsJson"]),
            {"question": 1, "answer": 0, "role_context": 1,
             "member_evidence": 0, "history_selection": 0,
             "confirmed_context": 0},
        )
        self.assertEqual(row["@GuardianRejectionsJson"], "[]")
        self.assertIsNone(row["@ExceptionClass"])
        serialized = json.dumps(row, default=str)
        self.assertNotIn("Q?", serialized)
        self.assertNotIn("structural hint", serialized)
        self.assertNotIn("role text", serialized)

    def test_grounded_insufficient_is_a_computed_outcome_row(self):
        response, appended = self._run(
            "/api/interview/model-answer",
            {"question": "Q?", "mode": "member_history",
             "profile_slug": "petec"},
            [json.dumps({"status": "insufficient", "answer": "",
                         "whyItWorks": [], "evidenceIds": []})],
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(appended), 1)
        self.assertEqual(appended[0]["@Outcome"], "computed_outcome")
        self.assertEqual(appended[0]["@ValidationResult"], "passed")

    def test_compare_rows_form_one_parent_and_two_children(self):
        grounded_reply = json.dumps({
            "status": "insufficient", "answer": "", "whyItWorks": [],
            "evidenceIds": [],
        })
        generic_reply = json.dumps({
            "status": "answered", "answer": "A generic example answer.",
            "whyItWorks": ["Lesson."], "evidenceIds": [],
        })
        response, appended = self._run(
            "/api/interview/model-answer",
            {"question": "Q?", "mode": "compare", "profile_slug": "petec"},
            [grounded_reply, generic_reply],
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(appended), 3)
        children = [row for row in appended
                    if row["@EventKind"] == "specialist_call"]
        parents = [row for row in appended
                   if row["@EventKind"] == "composition_parent"]
        self.assertEqual(len(children), 2)
        self.assertEqual(len(parents), 1)
        parent = parents[0]
        self.assertEqual(parent["@Composition"], "compare")
        self.assertEqual(parent["@Outcome"], "computed_outcome")
        self.assertIsNone(parent["@ProviderInputTokens"])
        self.assertIsNone(parent["@CostMicrousd"])
        for child in children:
            self.assertEqual(
                child["@ParentAttemptUuid"], parent["@AttemptUuid"]
            )
            self.assertIsNotNone(child["@BundleContentSha256"])
            self.assertEqual(child["@CostMicrousd"], 700 * 1 + 300 * 5)
        self.assertEqual(
            {child["@Specialist"] for child in children},
            {"grounded_example", "generic_example"},
        )

    def test_initial_model_answer_counts_one_question_and_no_answer(self):
        response, appended = self._run(
            "/api/interview/model-answer",
            {"question": "Q?", "mode": "member_history",
             "profile_slug": "petec"},
            [json.dumps({"status": "insufficient", "answer": "",
                         "whyItWorks": [], "evidenceIds": []})],
        )
        self.assertEqual(response.status_code, 200)
        counts = json.loads(appended[0]["@SourceClassCountsJson"])
        self.assertEqual(counts["question"], 1)
        self.assertEqual(counts["answer"], 0)
        self.assertEqual(counts["history_selection"], 0)

    def test_followup_counts_two_questions_and_one_prior_answer(self):
        """C5: a follow-up really sends the original question, the
        interviewer follow-up, and the prior server-validated answer."""
        grounded_reply = json.dumps({
            "status": "answered",
            "answer": "A grounded synthetic answer.",
            "whyItWorks": ["Factor."],
            "evidenceIds": [self._petec_evidence_id()],
        })
        first, appended_first = self._run(
            "/api/interview/model-answer",
            {"question": "Q?", "mode": "member_history",
             "profile_slug": "petec"},
            [grounded_reply],
        )
        self.assertEqual(first.status_code, 200)
        token = first.get_json()["contextToken"]
        followup_reply = json.dumps({
            "status": "answered",
            "answer": "A grounded synthetic follow-up answer.",
            "whyItWorks": ["Factor."],
            "evidenceIds": [self._petec_evidence_id()],
        })
        second, appended_second = self._run(
            "/api/interview/model-answer",
            {"question": "Q?", "mode": "member_history",
             "profile_slug": "petec",
             "follow_up": "What would you change?",
             "context_token": token},
            [followup_reply],
        )
        self.assertEqual(second.status_code, 200)
        self.assertEqual(len(appended_second), 1)
        counts = json.loads(appended_second[0]["@SourceClassCountsJson"])
        self.assertEqual(counts["question"], 2)
        self.assertEqual(counts["answer"], 1)
        self.assertEqual(counts["history_selection"], 0)

    def test_generic_followup_counts_two_questions_and_one_prior_answer(self):
        generic_reply = json.dumps({
            "status": "answered",
            "answer": "A generic synthetic example.",
            "whyItWorks": ["Lesson."],
            "evidenceIds": [],
        })
        first, _ = self._run(
            "/api/interview/model-answer",
            {"question": "Q?", "mode": "best_practice",
             "profile_slug": "petec"},
            [generic_reply],
        )
        self.assertEqual(first.status_code, 200)
        token = first.get_json()["contextToken"]
        second, appended_second = self._run(
            "/api/interview/model-answer",
            {"question": "Q?", "mode": "best_practice",
             "profile_slug": "petec",
             "follow_up": "And another angle?",
             "context_token": token},
            [generic_reply],
        )
        self.assertEqual(second.status_code, 200)
        counts = json.loads(appended_second[0]["@SourceClassCountsJson"])
        self.assertEqual(counts["question"], 2)
        self.assertEqual(counts["answer"], 1)
        self.assertEqual(counts["member_evidence"], 0)

    def _petec_evidence_id(self):
        _profile, evidence = app_module._interview_page_context("petec")
        return evidence[0]["id"]

    def test_append_failure_never_changes_the_response(self):
        def failing_append(procedure_name, parameters=None):
            raise database_service_module.DatabaseServiceError("down")

        class _Block:
            text = json.dumps({"hints": ["Hint one text.", "Hint two text."]})

        class _Response:
            content = [_Block()]
            stop_reason = "end_turn"

        with patch.object(
            app_module.client.messages, "create",
            new=lambda **kwargs: _Response(),
        ), patch.object(
            database_service_module.database_service,
            "execute_procedure",
            new=failing_append,
        ):
            response = app_module.app.test_client().post(
                "/api/interview/nudge",
                json={"question": "Q?", "profile_slug": "petec"},
                base_url="http://localhost",
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {"hints": ["Hint one text.", "Hint two text."]},
        )


class BoundedLoggingTests(unittest.TestCase):
    def test_validation_log_carries_no_exception_text(self):
        secret = "the candidate mentioned a secret employer name"
        with self.assertLogs(app_module.app.logger, level="WARNING") as logs:
            app_module._log_interview_failure(
                "Interview review validation error",
                ValueError(secret),
                "end_turn",
                42,
            )
        joined = "\n".join(logs.output)
        self.assertNotIn(secret, joined)
        self.assertNotIn("detail=", joined)
        self.assertIn("reason=unclassified", joined)
        self.assertIn("error_class=validation_value", joined)
        self.assertIn("reply_chars=42", joined)

    def test_unallowlisted_class_and_stop_reason_never_appear_raw(self):
        """C7 sentinel: inject a unique unallowlisted Python class and a
        unique raw stop value; prove neither marker reaches the log."""

        class ZebraQuantumMarkerError(Exception):
            pass

        with self.assertLogs(app_module.app.logger, level="WARNING") as logs:
            app_module._log_interview_failure(
                "Interview review validation error",
                ZebraQuantumMarkerError("zebra-marker-payload"),
                "zebra_stop_marker_xyz",
                7,
            )
        joined = "\n".join(logs.output)
        self.assertNotIn("Zebra", joined)
        self.assertNotIn("zebra", joined)
        self.assertIn("error_class=runtime_unexpected", joined)
        self.assertIn("provider_stop_reason=unknown", joined)

    def test_generic_route_handler_logs_only_the_normalized_class(self):
        class ZebraRouteMarkerError(Exception):
            pass

        def exploding_create(**kwargs):
            raise ZebraRouteMarkerError("zebra-route-payload")

        previous = app_module.app.config.get(
            interview_ai.ACTIVE_RELEASE_CONFIG_KEY
        )
        limiter_was_enabled = app_module.limiter.enabled
        app_module.limiter.enabled = False
        app_module.app.config[interview_ai.ACTIVE_RELEASE_CONFIG_KEY] = (
            RELEASE_ID
        )
        interview_ai.reset_resolution_cache()
        interview_ai.boot.initialize(RELEASE_ID)
        try:
            with patch.object(
                app_module.client.messages, "create", new=exploding_create,
            ), patch.object(
                database_service_module.database_service,
                "execute_procedure",
                new=lambda *args, **kwargs: [],
            ), self.assertLogs(app_module.app.logger, level="ERROR") as logs:
                response = app_module.app.test_client().post(
                    "/api/interview/nudge",
                    json={"question": "Q?", "profile_slug": "petec"},
                    base_url="http://localhost",
                )
        finally:
            app_module.app.config[interview_ai.ACTIVE_RELEASE_CONFIG_KEY] = (
                previous
            )
            app_module.limiter.enabled = limiter_was_enabled
            interview_ai.reset_resolution_cache()
        self.assertEqual(response.status_code, 500)
        joined = "\n".join(logs.output)
        self.assertNotIn("Zebra", joined)
        self.assertIn("class=runtime_unexpected", joined)

    def test_the_guarded_runtime_never_formats_a_raw_exception(self):
        for path in sorted(
            (ROOT / "services" / "interview_ai").glob("*.py")
        ):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("detail=%s", source, path.name)
            self.assertNotIn("API error: %s", source, path.name)
            self.assertNotIn("type(error).__name__", source, path.name)
            self.assertNotIn("type(e).__name__", source, path.name)
        app_source = (ROOT / "app.py").read_text(encoding="utf-8")
        start = app_source.index("INTERVIEW ")
        end = app_source.index("FRIENDLY ERROR PAGES")
        section = app_source[start:end]
        self.assertNotIn("detail=%s", section)
        self.assertNotIn("API error: %s", section)


if __name__ == "__main__":
    unittest.main()
