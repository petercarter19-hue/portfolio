import json
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import scripts.run_speech_quality_evaluations as speech_runner
from services.azure_speech_qualification import (
    MAX_AUDIO_SECONDS,
    MAX_PRICE_USD_PER_AUDIO_HOUR,
    PRICE_USD_PER_AUDIO_HOUR,
    TARGET_AUDIO_SECONDS,
    SpeechProgress,
    SpeechQualificationError,
    case_contract_digest,
    load_cases,
    privacy_safe_report,
    progress_from_json,
    progress_to_json,
    score_transcript,
)
from services.speech_transcription_service import (
    SpeechTranscriptionError,
    SpeechTranscriptionService,
)
from scripts.run_speech_quality_evaluations import (
    AppConfigurationMarkerStore,
    AzureCliCredential,
    EXPECTED_PROOF_AUTHORIZATION_REF,
    EXPECTED_APP_CONFIGURATION_ENDPOINT,
    EXPECTED_SPEECH_ENDPOINT,
    LAST_SUCCESS_KEY,
    MarkerStoreError,
    PROOF_CONSUMED_KEY,
    PROGRESS_KEY,
    _consume_proof_authorization,
    _create_marker_store,
    _execute_profiles,
    _preflight_speech_credential,
    _require_execution_authority,
    _validated_last_success_day,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = (
    ROOT
    / "tests"
    / "fixtures"
    / "azure_startup_qualification"
    / "speech_eval_cases.json"
)


def speech_progress(cases, results=None, attempts=None, *, day=date(2026, 9, 4)):
    results = results or {}
    if attempts is None:
        attempts = {key: result.audio_seconds for key, result in results.items()}
    return SpeechProgress(
        day=day,
        fixture_digest=case_contract_digest(cases),
        attempts=attempts,
        results=results,
    )


class MemoryMarkerStore:
    def __init__(self, initial, *, fail_on_write=None):
        self.value = initial
        self.write_count = 0
        self.fail_on_write = fail_on_write

    def write(self, _key, value, *, content_type=None):
        self.write_count += 1
        if self.write_count == self.fail_on_write:
            raise MarkerStoreError("speech_marker_write_failed")
        self.value = value


class ProofMarkerStore:
    def __init__(
        self,
        values=None,
        *,
        fail_on_read_key=None,
        fail_on_write_key=None,
        corrupt_readback_key=None,
    ):
        self.values = dict(values or {})
        self.write_count = 0
        self.operations = []
        self.fail_on_read_key = fail_on_read_key
        self.fail_on_write_key = fail_on_write_key
        self.corrupt_readback_key = corrupt_readback_key

    def read_optional(self, key):
        self.operations.append(("read_optional", key))
        if key == self.fail_on_read_key:
            raise MarkerStoreError("speech_marker_read_failed")
        value = self.values.get(key)
        if key == self.corrupt_readback_key and key in self.values:
            return value + "-corrupt"
        return value

    def write(self, key, value, *, content_type=None):
        self.write_count += 1
        self.operations.append(("write", key))
        if key == self.fail_on_write_key:
            raise MarkerStoreError("speech_marker_write_failed")
        self.values[key] = value


class FakeResourceNotFoundError(Exception):
    pass


class RecordingTranscriber:
    def __init__(self, transcripts, *, error=None):
        self.transcripts = transcripts
        self.error = error
        self.calls = []

    def transcribe(self, audio_bytes, _content_type, *, locale):
        key = audio_bytes.decode("utf-8")
        self.calls.append(key)
        if self.error:
            raise self.error
        return {"provider_transcript": self.transcripts[key]}


class FakeSpeechTranscriptionError(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def fake_audio_generator(case, directory, _target, _maximum):
    path = directory / f"{case.key}.fake"
    path.write_bytes(case.key.encode("utf-8"))
    return path, case.text, 2813


def run_main_with_marker_store(store):
    execute_profiles = mock.Mock(
        side_effect=lambda _cases, progress, **_kwargs: (
            progress,
            "speech_test_stop",
        )
    )
    emitted = []
    args = SimpleNamespace(
        fixture=FIXTURE,
        endpoint=EXPECTED_SPEECH_ENDPOINT,
        app_configuration_endpoint=EXPECTED_APP_CONFIGURATION_ENDPOINT,
        timeout_seconds=1200,
        execute=True,
    )
    with mock.patch.dict(
        os.environ,
        {
            "PEERSLATE_AZURE_SPEND_AUTHORIZATION_REF": (
                EXPECTED_PROOF_AUTHORIZATION_REF
            )
        },
        clear=True,
    ), mock.patch.object(
        speech_runner, "_arguments", return_value=args
    ), mock.patch.object(
        speech_runner, "_require_execution_authority"
    ), mock.patch.object(
        speech_runner, "_preflight_speech_credential", return_value=mock.Mock()
    ), mock.patch.object(
        speech_runner, "_create_marker_store", return_value=store
    ), mock.patch.object(
        speech_runner, "_execute_profiles", execute_profiles
    ), mock.patch.object(
        speech_runner, "_emit", side_effect=emitted.append
    ), mock.patch(
        "services.speech_transcription_service.SpeechTranscriptionService",
        return_value=mock.Mock(),
    ):
        return_code = speech_runner.main()
    return return_code, execute_profiles, emitted


class AzureSpeechQualificationTests(unittest.TestCase):
    def test_fixture_is_exact_bounded_and_product_aligned(self):
        cases = load_cases(FIXTURE)
        self.assertEqual(len(cases), 8)
        self.assertEqual(len({item.key for item in cases}), 8)
        self.assertIn("Interview Studio", {item.product for item in cases})
        self.assertIn("Opportunity Slate", {item.product for item in cases})
        self.assertEqual(TARGET_AUDIO_SECONDS, 36_900)
        self.assertEqual(MAX_AUDIO_SECONDS, 37_800)
        self.assertEqual(PRICE_USD_PER_AUDIO_HOUR, Decimal("0.10"))
        self.assertEqual(MAX_PRICE_USD_PER_AUDIO_HOUR, Decimal("0.36"))

    def test_score_reduces_transcript_to_numeric_structural_results(self):
        case = load_cases(FIXTURE)[0]
        expected = " ".join(case.text for _ in range(10))
        result = score_transcript(
            case,
            expected_text=expected,
            transcript=expected,
            audio_seconds=2814.4,
            latency_seconds=3.125,
        )
        self.assertTrue(result.quality_passed)
        self.assertEqual(result.sample_word_error_rate_milli, 0)
        self.assertEqual(result.required_term_recall_milli, 1000)
        self.assertEqual(result.token_count_ratio_milli, 1000)
        self.assertNotIn(case.text, json.dumps(result.as_dict()))

    def test_progress_round_trip_contains_no_audio_or_transcript(self):
        case = load_cases(FIXTURE)[0]
        result = score_transcript(
            case,
            expected_text=case.text,
            transcript=case.text,
            audio_seconds=2813,
            latency_seconds=2,
        )
        progress = speech_progress((case,), {case.key: result})
        encoded = progress_to_json(progress)
        decoded = progress_from_json(
            encoded,
            expected_day=date(2026, 9, 4),
            expected_fixture_digest=case_contract_digest((case,)),
        )
        self.assertEqual(decoded.results[case.key], result)
        self.assertNotIn(case.text, encoded)
        self.assertNotIn("provider_transcript", encoded.casefold())
        self.assertNotIn("audio_bytes", encoded)

    def test_old_progress_day_starts_a_fresh_empty_day(self):
        payload = json.dumps(
            {
                "schema_version": 2,
                "day": "2026-09-03",
                "fixture_digest": case_contract_digest(load_cases(FIXTURE)),
                "attempts": {},
                "results": {},
            }
        )
        cases = load_cases(FIXTURE)
        progress = progress_from_json(
            payload,
            expected_day=date(2026, 9, 4),
            expected_fixture_digest=case_contract_digest(cases),
        )
        self.assertEqual(progress.day, date(2026, 9, 4))
        self.assertEqual(progress.results, {})

    def test_malformed_or_oversized_marker_fails_closed(self):
        with self.assertRaises(SpeechQualificationError):
            progress_from_json(
                "not-json",
                expected_day=date(2026, 9, 4),
                expected_fixture_digest=case_contract_digest(load_cases(FIXTURE)),
            )
        with self.assertRaises(SpeechQualificationError):
            progress_from_json(
                "x" * 12_001,
                expected_day=date(2026, 9, 4),
                expected_fixture_digest=case_contract_digest(load_cases(FIXTURE)),
            )

    def test_same_day_progress_is_bound_to_the_full_fixture(self):
        cases = load_cases(FIXTURE)
        encoded = progress_to_json(speech_progress(cases))
        changed = list(cases)
        changed[0] = replace(changed[0], text=changed[0].text + " Changed.")
        with self.assertRaisesRegex(SpeechQualificationError, "digest"):
            progress_from_json(
                encoded,
                expected_day=date(2026, 9, 4),
                expected_fixture_digest=case_contract_digest(changed),
            )

    def test_progress_total_above_audio_ceiling_fails_closed(self):
        cases = load_cases(FIXTURE)
        results = {}
        for case in cases[:2]:
            result = score_transcript(
                case,
                expected_text=case.text,
                transcript=case.text,
                audio_seconds=MAX_AUDIO_SECONDS // 2 + 1,
                latency_seconds=1,
            )
            results[case.key] = result
        encoded = progress_to_json(
            speech_progress(cases, results)
        )
        with self.assertRaises(SpeechQualificationError):
            progress_from_json(
                encoded,
                expected_day=date(2026, 9, 4),
                expected_fixture_digest=case_contract_digest(cases),
            )

    def test_success_marker_needs_all_profiles_and_bounded_audio(self):
        cases = load_cases(FIXTURE)
        results = {}
        per_case = TARGET_AUDIO_SECONDS // len(cases)
        for case in cases:
            result = score_transcript(
                case,
                expected_text=case.text,
                transcript=case.text,
                audio_seconds=per_case,
                latency_seconds=1,
            )
            results[case.key] = result
        short = speech_progress(cases, results)
        self.assertFalse(
            privacy_safe_report(cases, short, mode="test")["success_marker_eligible"]
        )
        first = cases[0].key
        results[first] = replace(
            results[first],
            audio_seconds=results[first].audio_seconds
            + TARGET_AUDIO_SECONDS
            - short.audio_seconds,
        )
        complete = speech_progress(cases, results)
        report = privacy_safe_report(cases, complete, mode="test")
        self.assertTrue(report["success_marker_eligible"])
        self.assertTrue(report["quality_checks_passed"])
        serialized = json.dumps(report)
        self.assertNotIn(cases[0].text, serialized)

    def test_possible_billed_cost_reports_promotional_and_standard_ceilings(self):
        cases = load_cases(FIXTURE)
        progress = speech_progress(
            cases,
            attempts={cases[0].key: MAX_AUDIO_SECONDS},
        )
        report = privacy_safe_report(cases, progress, mode="test")
        self.assertEqual(report["possible_billed_audio_seconds"], 37_800)
        self.assertEqual(report["maximum_possible_cost_usd"], 1.05)
        self.assertEqual(report["maximum_standard_rate_cost_usd"], 3.78)

    def test_tampered_progress_metadata_is_not_reported(self):
        case = load_cases(FIXTURE)[0]
        result = score_transcript(
            case,
            expected_text=case.text,
            transcript=case.text,
            audio_seconds=2813,
            latency_seconds=1,
        )
        tampered = replace(result, product="private injected label")
        with self.assertRaises(SpeechQualificationError):
            privacy_safe_report(
                (case,),
                speech_progress((case,), {case.key: tampered}),
                mode="test",
            )

    def test_timeout_is_reserved_before_call_and_same_day_recovery_never_replays(self):
        cases = load_cases(FIXTURE)
        progress = speech_progress(cases)
        store = MemoryMarkerStore(progress_to_json(progress))
        timeout_transcriber = RecordingTranscriber(
            {case.key: case.text for case in cases},
            error=FakeSpeechTranscriptionError("speech_timeout"),
        )
        with tempfile.TemporaryDirectory() as directory:
            after_timeout, stop = _execute_profiles(
                cases,
                progress,
                store=store,
                transcriber=timeout_transcriber,
                temp_root=Path(directory),
                audio_generator=fake_audio_generator,
                monotonic=lambda: 1.0,
                transcription_error_type=FakeSpeechTranscriptionError,
            )
        first_key = cases[0].key
        self.assertEqual(stop, "speech_timeout")
        self.assertEqual(timeout_transcriber.calls, [first_key])
        self.assertIn(first_key, after_timeout.attempts)
        self.assertNotIn(first_key, after_timeout.results)

        recovered = progress_from_json(
            store.value,
            expected_day=date(2026, 9, 4),
            expected_fixture_digest=case_contract_digest(cases),
        )
        recovery_transcriber = RecordingTranscriber(
            {case.key: case.text for case in cases}
        )
        with tempfile.TemporaryDirectory() as directory:
            after_recovery, stop = _execute_profiles(
                cases,
                recovered,
                store=store,
                transcriber=recovery_transcriber,
                temp_root=Path(directory),
                audio_generator=fake_audio_generator,
                monotonic=lambda: 1.0,
                transcription_error_type=FakeSpeechTranscriptionError,
            )
        self.assertNotIn(first_key, recovery_transcriber.calls)
        self.assertEqual(len(recovery_transcriber.calls), 7)
        self.assertEqual(stop, "speech_attempt_outcome_ambiguous")
        report = privacy_safe_report(cases, after_recovery, mode="test")
        self.assertEqual(report["unresolved_attempts"], 1)
        self.assertLessEqual(report["possible_billed_audio_seconds"], MAX_AUDIO_SECONDS)

    def test_post_call_marker_failure_is_not_replayed_on_recovery(self):
        cases = load_cases(FIXTURE)
        progress = speech_progress(cases)
        store = MemoryMarkerStore(progress_to_json(progress), fail_on_write=2)
        first_transcriber = RecordingTranscriber(
            {case.key: case.text for case in cases}
        )
        with tempfile.TemporaryDirectory() as directory:
            in_memory, stop = _execute_profiles(
                cases,
                progress,
                store=store,
                transcriber=first_transcriber,
                temp_root=Path(directory),
                audio_generator=fake_audio_generator,
                monotonic=lambda: 1.0,
                transcription_error_type=FakeSpeechTranscriptionError,
            )
        first_key = cases[0].key
        self.assertEqual(stop, "speech_marker_write_failed")
        self.assertIn(first_key, in_memory.results)
        durable = progress_from_json(
            store.value,
            expected_day=date(2026, 9, 4),
            expected_fixture_digest=case_contract_digest(cases),
        )
        self.assertIn(first_key, durable.attempts)
        self.assertNotIn(first_key, durable.results)
        recovery_transcriber = RecordingTranscriber(
            {case.key: case.text for case in cases}
        )
        store.fail_on_write = None
        with tempfile.TemporaryDirectory() as directory:
            _execute_profiles(
                cases,
                durable,
                store=store,
                transcriber=recovery_transcriber,
                temp_root=Path(directory),
                audio_generator=fake_audio_generator,
                monotonic=lambda: 1.0,
                transcription_error_type=FakeSpeechTranscriptionError,
            )
        self.assertNotIn(first_key, recovery_transcriber.calls)

    def test_execution_authority_pins_both_exact_pathless_origins(self):
        args = mock.Mock(
            endpoint=EXPECTED_SPEECH_ENDPOINT,
            app_configuration_endpoint=EXPECTED_APP_CONFIGURATION_ENDPOINT,
            timeout_seconds=1200,
        )
        gates = {
            "PEERSLATE_AZURE_QUALIFICATION_ACTIVATED": "true",
            "PEERSLATE_AZURE_CREDIT_CONFIRMED": "true",
            "PEERSLATE_AZURE_SPEND_AUTHORIZATION_REF": EXPECTED_PROOF_AUTHORIZATION_REF,
        }
        with mock.patch.dict(os.environ, gates, clear=True), mock.patch(
            "scripts.run_speech_quality_evaluations.shutil.which",
            return_value="/usr/bin/tool",
        ):
            _require_execution_authority(args)
            for hostile in (
                "https://attacker.example",
                EXPECTED_SPEECH_ENDPOINT + "/path",
                EXPECTED_SPEECH_ENDPOINT + "?next=https://attacker.example",
                "https://user@peerslate-foundry.cognitiveservices.azure.com",
                "https://peerslate-foundry.cognitiveservices.azure.com:443",
            ):
                args.endpoint = hostile
                with self.assertRaises(SpeechQualificationError):
                    _require_execution_authority(args)
            args.endpoint = EXPECTED_SPEECH_ENDPOINT
            args.app_configuration_endpoint = "https://attacker.example"
            with self.assertRaises(SpeechQualificationError):
                _require_execution_authority(args)

    def test_transcription_adapter_refuses_hostile_redirects(self):
        credential = mock.Mock()
        credential.get_token.return_value = mock.Mock(token="opaque-token")
        session = mock.Mock()
        session.post.return_value = mock.Mock(status_code=307)
        service = SpeechTranscriptionService(
            endpoint=EXPECTED_SPEECH_ENDPOINT,
            credential=credential,
            session=session,
        )

        with self.assertRaisesRegex(SpeechTranscriptionError, "speech_failed"):
            service.transcribe(b"fictional-audio", "audio/mpeg")

        session.post.assert_called_once()
        self.assertFalse(session.post.call_args.kwargs["allow_redirects"])

    def test_sdk_marker_store_distinguishes_missing_from_read_failure(self):
        client = mock.Mock()
        store = AppConfigurationMarkerStore(
            client=client,
            setting_factory=lambda **values: SimpleNamespace(**values),
            not_found_error=FakeResourceNotFoundError,
        )
        client.get_configuration_setting.side_effect = FakeResourceNotFoundError()
        self.assertIsNone(store.read_optional(PROOF_CONSUMED_KEY))
        with self.assertRaisesRegex(MarkerStoreError, "speech_marker_read_failed"):
            store.read(PROGRESS_KEY)

        client.get_configuration_setting.side_effect = None
        client.get_configuration_setting.return_value = SimpleNamespace(
            key=PROOF_CONSUMED_KEY,
            label=None,
            value="",
        )
        self.assertEqual(store.read_optional(PROOF_CONSUMED_KEY), "")

        client.get_configuration_setting.side_effect = RuntimeError(
            "private provider diagnostic"
        )
        with self.assertRaises(MarkerStoreError) as caught:
            store.read_optional(PROOF_CONSUMED_KEY)
        self.assertEqual(str(caught.exception), "speech_marker_read_failed")
        self.assertNotIn("private", str(caught.exception))

    def test_sdk_marker_store_validates_exact_unlabeled_reads_and_writes(self):
        client = mock.Mock()
        setting_factory = mock.Mock(
            side_effect=lambda **values: SimpleNamespace(**values)
        )
        store = AppConfigurationMarkerStore(
            client=client,
            setting_factory=setting_factory,
            not_found_error=FakeResourceNotFoundError,
        )
        existing = SimpleNamespace(
            key=PROGRESS_KEY,
            label=None,
            value="bounded-progress",
        )
        client.get_configuration_setting.return_value = existing
        self.assertEqual(store.read(PROGRESS_KEY), "bounded-progress")
        client.get_configuration_setting.assert_called_once_with(
            key=PROGRESS_KEY,
            label=None,
        )

        written = SimpleNamespace(
            key=PROGRESS_KEY,
            label=None,
            value="new-progress",
        )
        client.set_configuration_setting.return_value = written
        store.write(
            PROGRESS_KEY,
            "new-progress",
            content_type="application/json",
        )
        setting_factory.assert_called_once_with(
            key=PROGRESS_KEY,
            label=None,
            value="new-progress",
            content_type="application/json",
        )
        stored_argument = client.set_configuration_setting.call_args.args[0]
        self.assertEqual(
            (
                stored_argument.key,
                stored_argument.label,
                stored_argument.value,
                stored_argument.content_type,
            ),
            (
                PROGRESS_KEY,
                None,
                "new-progress",
                "application/json",
            ),
        )

        client.get_configuration_setting.side_effect = None
        client.get_configuration_setting.return_value = SimpleNamespace(
            key=PROGRESS_KEY,
            label="unexpected",
            value="new-progress",
        )
        with self.assertRaisesRegex(MarkerStoreError, "speech_marker_read_failed"):
            store.read(PROGRESS_KEY)

    def test_marker_store_factory_uses_sdk_with_cli_workload_identity(self):
        client = mock.Mock()
        credential = mock.Mock()
        client_factory = mock.Mock(return_value=client)
        credential_factory = mock.Mock(return_value=credential)
        setting_factory = mock.Mock()
        app_configuration = SimpleNamespace(
            AzureAppConfigurationClient=client_factory,
            ConfigurationSetting=setting_factory,
        )
        identity = SimpleNamespace(AzureCliCredential=credential_factory)
        exceptions = SimpleNamespace(
            ResourceNotFoundError=FakeResourceNotFoundError
        )

        store = _create_marker_store(
            EXPECTED_APP_CONFIGURATION_ENDPOINT,
            app_configuration_import=lambda _name: app_configuration,
            identity_import=lambda _name: identity,
            exceptions_import=lambda _name: exceptions,
        )

        credential_factory.assert_called_once_with(process_timeout=45)
        client_factory.assert_called_once_with(
            base_url=EXPECTED_APP_CONFIGURATION_ENDPOINT,
            credential=credential,
        )
        self.assertIs(store.client, client)
        self.assertIs(store.setting_factory, setting_factory)

        with self.assertRaisesRegex(
            MarkerStoreError, "speech_marker_runtime_failed"
        ):
            _create_marker_store(
                EXPECTED_APP_CONFIGURATION_ENDPOINT,
                app_configuration_import=mock.Mock(
                    side_effect=ImportError("private module failure")
                ),
            )

    def test_proof_authorization_is_exact_and_consumed_once(self):
        store = ProofMarkerStore()
        with self.assertRaisesRegex(SpeechQualificationError, "invalid"):
            _consume_proof_authorization(store, "another-owner-ref")
        self.assertEqual(store.write_count, 0)

        _consume_proof_authorization(store, EXPECTED_PROOF_AUTHORIZATION_REF)
        self.assertEqual(
            store.values[PROOF_CONSUMED_KEY], EXPECTED_PROOF_AUTHORIZATION_REF
        )
        self.assertEqual(store.write_count, 1)

        with self.assertRaisesRegex(SpeechQualificationError, "consumed"):
            _consume_proof_authorization(store, EXPECTED_PROOF_AUTHORIZATION_REF)
        self.assertEqual(store.write_count, 1)

        for malformed in ("", "another-reference"):
            with self.subTest(malformed=malformed):
                malformed_store = ProofMarkerStore(
                    {PROOF_CONSUMED_KEY: malformed}
                )
                with self.assertRaisesRegex(
                    SpeechQualificationError,
                    "consumption marker is invalid",
                ):
                    _consume_proof_authorization(
                        malformed_store,
                        EXPECTED_PROOF_AUTHORIZATION_REF,
                    )
                self.assertEqual(malformed_store.write_count, 0)

    def test_empty_fresh_store_is_initialized_before_authorization_consumption(self):
        store = ProofMarkerStore()
        return_code, execute_profiles, emitted = run_main_with_marker_store(store)

        self.assertEqual(return_code, 3)
        self.assertIn(PROGRESS_KEY, store.values)
        self.assertEqual(
            store.values[PROOF_CONSUMED_KEY], EXPECTED_PROOF_AUTHORIZATION_REF
        )
        self.assertEqual(execute_profiles.call_count, 1)
        self.assertEqual(emitted[-1]["mode"], "executed")
        self.assertEqual(emitted[-1]["stop_category"], "speech_test_stop")
        self.assertLess(
            store.operations.index(("write", PROGRESS_KEY)),
            store.operations.index(("read_optional", LAST_SUCCESS_KEY)),
        )
        self.assertLess(
            store.operations.index(("read_optional", LAST_SUCCESS_KEY)),
            store.operations.index(("write", PROOF_CONSUMED_KEY)),
        )

    def test_malformed_fresh_markers_never_consume_or_enter_provider_path(self):
        today = datetime.now(timezone.utc).date()
        foreign_progress = {
            "schema_version": 2,
            "fixture_digest": "0" * 64,
            "attempts": {"foreign-profile": 1},
            "results": {"foreign-profile": {"private": "payload"}},
        }
        malformed_states = {
            "empty progress": {PROGRESS_KEY: ""},
            "stale foreign progress": {
                PROGRESS_KEY: json.dumps(
                    {
                        **foreign_progress,
                        "day": (today - timedelta(days=1)).isoformat(),
                    }
                )
            },
            "future foreign progress": {
                PROGRESS_KEY: json.dumps(
                    {
                        **foreign_progress,
                        "day": (today + timedelta(days=1)).isoformat(),
                    }
                )
            },
            "malformed success": {LAST_SUCCESS_KEY: "not-a-date"},
            "empty consumption": {PROOF_CONSUMED_KEY: ""},
        }
        for label, values in malformed_states.items():
            with self.subTest(label=label):
                store = ProofMarkerStore(values)
                return_code, execute_profiles, emitted = run_main_with_marker_store(
                    store
                )
                self.assertEqual(return_code, 2)
                self.assertEqual(execute_profiles.call_count, 0)
                self.assertEqual(emitted[-1]["mode"], "refused")
                self.assertNotIn(
                    ("write", PROOF_CONSUMED_KEY),
                    store.operations,
                )

    def test_fresh_progress_access_failures_never_consume_or_enter_provider_path(self):
        failing_stores = {
            "read": ProofMarkerStore(fail_on_read_key=PROGRESS_KEY),
            "write": ProofMarkerStore(fail_on_write_key=PROGRESS_KEY),
            "readback": ProofMarkerStore(corrupt_readback_key=PROGRESS_KEY),
        }
        for label, store in failing_stores.items():
            with self.subTest(label=label):
                return_code, execute_profiles, emitted = run_main_with_marker_store(
                    store
                )
                self.assertEqual(return_code, 2)
                self.assertEqual(execute_profiles.call_count, 0)
                self.assertEqual(emitted[-1]["mode"], "refused")
                self.assertNotIn(
                    ("write", PROOF_CONSUMED_KEY),
                    store.operations,
                )

    def test_already_complete_state_skips_without_consuming_authorization(self):
        cases = load_cases(FIXTURE)
        per_case = TARGET_AUDIO_SECONDS // len(cases)
        results = {
            case.key: score_transcript(
                case,
                expected_text=case.text,
                transcript=case.text,
                audio_seconds=per_case,
                latency_seconds=1,
            )
            for case in cases
        }
        first_key = cases[0].key
        recorded_seconds = sum(result.audio_seconds for result in results.values())
        results[first_key] = replace(
            results[first_key],
            audio_seconds=(
                results[first_key].audio_seconds
                + TARGET_AUDIO_SECONDS
                - recorded_seconds
            ),
        )
        today = datetime.now(timezone.utc).date()
        store = ProofMarkerStore(
            {
                PROGRESS_KEY: progress_to_json(
                    speech_progress(cases, results, day=today)
                ),
                LAST_SUCCESS_KEY: today.isoformat(),
            }
        )

        return_code, execute_profiles, emitted = run_main_with_marker_store(store)

        self.assertEqual(return_code, 0)
        self.assertEqual(execute_profiles.call_count, 0)
        self.assertTrue(emitted[-1]["already_complete"])
        self.assertEqual(emitted[-1]["mode"], "skipped")
        self.assertNotIn(("write", PROOF_CONSUMED_KEY), store.operations)

    def test_last_success_marker_accepts_only_canonical_nonfuture_dates(self):
        today = date(2026, 9, 15)
        self.assertEqual(
            _validated_last_success_day("2026-09-14", today),
            date(2026, 9, 14),
        )
        self.assertIsNone(_validated_last_success_day(None, today))
        for invalid in ("", "not-a-date", "2026-9-14", "2026-09-16"):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(
                SpeechQualificationError,
                "success marker is invalid",
            ):
                _validated_last_success_day(invalid, today)

    def test_proof_uses_new_progress_keys_and_preserves_legacy_markers(self):
        self.assertEqual(
            PROGRESS_KEY,
            "qualification/speech/proof-progress/"
            "2026-09-15-marker-recovery-10-5h-one-use",
        )
        self.assertEqual(
            LAST_SUCCESS_KEY,
            "qualification/speech/proof-last-success-day/"
            "2026-09-15-marker-recovery-10-5h-one-use",
        )
        self.assertEqual(
            PROOF_CONSUMED_KEY,
            "qualification/speech/proof-authorization-consumed/"
            "2026-09-15-marker-recovery-10-5h-one-use",
        )
        self.assertNotEqual(PROGRESS_KEY, "qualification/speech/progress")
        self.assertNotEqual(
            PROGRESS_KEY,
            "qualification/speech/proof-progress/2026-09-14-10-5h-one-use",
        )
        self.assertNotEqual(
            PROOF_CONSUMED_KEY,
            "qualification/speech/proof-authorization-consumed/"
            "2026-09-14-10-5h-one-use",
        )
        self.assertNotEqual(
            LAST_SUCCESS_KEY,
            "qualification/speech/last-success-day",
        )
        source = (ROOT / "scripts" / "run_speech_quality_evaluations.py").read_text(
            encoding="utf-8"
        )
        main = source[source.index("def main()") :]
        self.assertIn("store.read_optional(PROGRESS_KEY)", main)
        self.assertIn("store.read_optional(LAST_SUCCESS_KEY)", main)

    def test_credential_preflight_happens_before_proof_consumption(self):
        source = (ROOT / "scripts" / "run_speech_quality_evaluations.py").read_text(
            encoding="utf-8"
        )
        main = source[source.index("def main()") :]
        self.assertLess(
            main.index("credential = _preflight_speech_credential()"),
            main.index("store = _create_marker_store"),
        )
        self.assertLess(
            main.index("store = _create_marker_store"),
            main.index("store.read_optional(PROGRESS_KEY)"),
        )
        self.assertLess(
            main.index("store.read_optional(LAST_SUCCESS_KEY)"),
            main.index("_consume_proof_authorization(store, authorization_ref)"),
        )
        self.assertNotIn('"appconfig"', source)

        with self.assertRaisesRegex(SpeechQualificationError, "speech_auth_failed"):
            _preflight_speech_credential(
                identity_import=mock.Mock(side_effect=ImportError("missing")),
                credential_factory=mock.Mock(),
            )

    def test_cli_credential_primes_one_token_then_refreshes(self):
        responses = [
            subprocess.CompletedProcess(
                args=[], returncode=0, stdout="a" * 80, stderr=""
            ),
            subprocess.CompletedProcess(
                args=[], returncode=0, stdout="b" * 80, stderr=""
            ),
        ]
        with mock.patch(
            "scripts.run_speech_quality_evaluations.subprocess.run",
            side_effect=responses,
        ) as run:
            credential = AzureCliCredential()
            credential.prime()
            first = credential.get_token("ignored").token
            second = credential.get_token("ignored").token
        self.assertEqual(first, "a" * 80)
        self.assertEqual(second, "b" * 80)
        self.assertEqual(run.call_count, 2)

    def test_runner_is_dry_run_by_default_and_never_starts_audio_tools(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            completed = subprocess.run(
                [sys.executable, "scripts/run_speech_quality_evaluations.py"],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["mode"], "dry_run")
        self.assertEqual(report["completed_requests"], 0)
        self.assertFalse(report["success_marker_eligible"])

    def test_runner_refuses_execute_without_exact_authority_gates(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_speech_quality_evaluations.py",
                    "--execute",
                    "--endpoint",
                    "https://example.cognitiveservices.azure.com",
                    "--app-configuration-endpoint",
                    "https://example.azconfig.io",
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(completed.returncode, 2)
        report = json.loads(completed.stdout)
        self.assertEqual(report["mode"], "refused")
        self.assertNotIn("https://", completed.stdout)

    def test_registered_pipeline_keeps_speech_scheduled_off_until_proof(self):
        pipeline = (ROOT / "pipelines" / "azure-startup-qualification.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("name: qualificationSpeechProofEndpoint", pipeline)
        self.assertIn("displayName: One-time Speech proof endpoint", pipeline)
        self.assertIn("name: qualificationSpeechProofAuthorizationRef", pipeline)
        self.assertIn(
            "displayName: One-time Speech proof authorization reference",
            pipeline,
        )
        self.assertGreaterEqual(pipeline.count("default: ''"), 2)
        self.assertIn(
            "qualificationSpeechEndpoint: "
            "${{ parameters.qualificationSpeechProofEndpoint }}",
            pipeline,
        )
        self.assertIn(
            "qualificationSpeechAuthorizationRef: "
            "${{ parameters.qualificationSpeechProofAuthorizationRef }}",
            pipeline,
        )
        self.assertNotIn(EXPECTED_PROOF_AUTHORIZATION_REF, pipeline)
        self.assertIn(
            "PEERSLATE_AZURE_SPEND_AUTHORIZATION_REF: "
            "$(qualificationSpeechAuthorizationRef)",
            pipeline,
        )
        self.assertIn("azure-appconfiguration==1.9.0", pipeline)
        self.assertIn(
            "ne(variables['qualificationSpeechEndpoint'], '')",
            pipeline,
        )
        self.assertIn(
            "qualificationFoundryEndpoint: 'https://peerslate-foundry.openai.azure.com'",
            pipeline,
        )
        self.assertIn(
            "qualificationContainerRegistryEndpoint: 'https://peerslateacr.azurecr.io'",
            pipeline,
        )


if __name__ == "__main__":
    unittest.main()
