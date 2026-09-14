import json
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path
from unittest import mock

from services.azure_speech_qualification import (
    MAX_AUDIO_SECONDS,
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
from scripts.run_speech_quality_evaluations import (
    AzureCliCredential,
    EXPECTED_PROOF_AUTHORIZATION_REF,
    EXPECTED_APP_CONFIGURATION_ENDPOINT,
    EXPECTED_SPEECH_ENDPOINT,
    MarkerStoreError,
    PROOF_CONSUMED_KEY,
    _consume_proof_authorization,
    _execute_profiles,
    _preflight_speech_credential,
    _require_execution_authority,
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
    def __init__(self):
        self.values = {}
        self.write_count = 0

    def read_optional(self, key):
        return self.values.get(key, "")

    def write(self, key, value, *, content_type=None):
        self.write_count += 1
        self.values[key] = value


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


class AzureSpeechQualificationTests(unittest.TestCase):
    def test_fixture_is_exact_bounded_and_product_aligned(self):
        cases = load_cases(FIXTURE)
        self.assertEqual(len(cases), 8)
        self.assertEqual(len({item.key for item in cases}), 8)
        self.assertIn("Interview Studio", {item.product for item in cases})
        self.assertIn("Opportunity Slate", {item.product for item in cases})
        self.assertEqual(TARGET_AUDIO_SECONDS, 22_500)
        self.assertEqual(MAX_AUDIO_SECONDS, 23_400)

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

    def test_credential_preflight_happens_before_proof_consumption(self):
        source = (ROOT / "scripts" / "run_speech_quality_evaluations.py").read_text(
            encoding="utf-8"
        )
        main = source[source.index("def main()") :]
        self.assertLess(
            main.index("credential = _preflight_speech_credential()"),
            main.index("_consume_proof_authorization(store, authorization_ref)"),
        )

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
        self.assertIn("default: ''", pipeline)
        self.assertIn(
            "qualificationSpeechEndpoint: "
            "${{ parameters.qualificationSpeechProofEndpoint }}",
            pipeline,
        )
        self.assertIn(
            "qualificationSpeechAuthorizationRef: "
            f"'{EXPECTED_PROOF_AUTHORIZATION_REF}'",
            pipeline,
        )
        self.assertIn(
            "PEERSLATE_AZURE_SPEND_AUTHORIZATION_REF: "
            "$(qualificationSpeechAuthorizationRef)",
            pipeline,
        )
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
