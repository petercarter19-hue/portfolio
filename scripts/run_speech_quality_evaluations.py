#!/usr/bin/env python3
"""Run the bounded, synthetic Azure Speech qualification regression suite."""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import replace
from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

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
    rounded_audio_seconds,
    score_transcript,
)

DEFAULT_FIXTURE = (
    REPOSITORY_ROOT
    / "tests"
    / "fixtures"
    / "azure_startup_qualification"
    / "speech_eval_cases.json"
)
PROGRESS_KEY = "qualification/speech/proof-progress/2026-09-14-10-5h-one-use"
LAST_SUCCESS_KEY = (
    "qualification/speech/proof-last-success-day/2026-09-14-10-5h-one-use"
)
PROOF_CONSUMED_KEY = (
    "qualification/speech/proof-authorization-consumed/2026-09-14-10-5h-one-use"
)
EXPECTED_PROOF_AUTHORIZATION_REF = (
    "session:01a09d58-4477-7b43-873a-0af993f00c85/"
    "owner-authorization:2026-09-14/azure-speech-proof-10.5h-one-use"
)
EXPECTED_SPEECH_ENDPOINT = "https://peerslate-foundry.cognitiveservices.azure.com"
EXPECTED_APP_CONFIGURATION_ENDPOINT = (
    "https://peerslate-startup-qualification.azconfig.io"
)
SPEECH_TOKEN_SCOPE = "https://cognitiveservices.azure.com/.default"


class MarkerStoreError(RuntimeError):
    """App Configuration marker access failed without exposing provider output."""


class AzureCliCredential:
    """Minimal token adapter that reuses AzureCLI task workload identity auth."""

    def __init__(self):
        self._prefetched_token = ""

    @staticmethod
    def _request_token():
        try:
            completed = subprocess.run(
                [
                    "az",
                    "account",
                    "get-access-token",
                    "--scope",
                    SPEECH_TOKEN_SCOPE,
                    "--query",
                    "accessToken",
                    "--output",
                    "tsv",
                    "--only-show-errors",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=45,
            )
        except subprocess.TimeoutExpired as error:
            raise RuntimeError("speech_auth_failed") from error
        token = completed.stdout.strip()
        if (
            completed.returncode != 0
            or not 40 <= len(token) <= 24_000
            or any(char.isspace() for char in token)
        ):
            raise RuntimeError("speech_auth_failed")
        return token

    def prime(self):
        """Acquire the first request token before consuming proof authority."""

        self._prefetched_token = self._request_token()

    def get_token(self, _scope):
        token = self._prefetched_token or self._request_token()
        self._prefetched_token = ""
        return SimpleNamespace(token=token)


def _preflight_speech_credential(
    *, identity_import=import_module, credential_factory=AzureCliCredential
):
    """Prove the runtime and first Entra token before consuming one-use authority."""

    try:
        identity_import("azure.identity")
        credential = credential_factory()
        credential.prime()
    except Exception as error:
        raise SpeechQualificationError("speech_auth_failed") from error
    return credential


class AppConfigurationMarkerStore:
    def __init__(self, endpoint: str):
        self.endpoint = endpoint

    def read(self, key: str) -> str:
        completed = subprocess.run(
            [
                "az",
                "appconfig",
                "kv",
                "show",
                "--endpoint",
                self.endpoint,
                "--key",
                key,
                "--auth-mode",
                "login",
                "--query",
                "value",
                "--output",
                "tsv",
                "--only-show-errors",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=45,
        )
        if completed.returncode != 0:
            raise MarkerStoreError("speech_marker_read_failed")
        return completed.stdout.rstrip("\r\n")

    def read_optional(self, key: str) -> str:
        completed = subprocess.run(
            [
                "az",
                "appconfig",
                "kv",
                "list",
                "--endpoint",
                self.endpoint,
                "--key",
                key,
                "--auth-mode",
                "login",
                "--fields",
                "key",
                "value",
                "--output",
                "json",
                "--only-show-errors",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=45,
        )
        if completed.returncode != 0 or len(completed.stdout) > 16_000:
            raise MarkerStoreError("speech_marker_read_failed")
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as error:
            raise MarkerStoreError("speech_marker_read_failed") from error
        if payload == []:
            return ""
        if (
            not isinstance(payload, list)
            or len(payload) != 1
            or not isinstance(payload[0], dict)
            or payload[0].get("key") != key
            or not isinstance(payload[0].get("value"), str)
        ):
            raise MarkerStoreError("speech_marker_read_failed")
        return payload[0]["value"]

    def write(self, key: str, value: str, *, content_type: str | None = None) -> None:
        command = [
            "az",
            "appconfig",
            "kv",
            "set",
            "--endpoint",
            self.endpoint,
            "--key",
            key,
            "--value",
            value,
            "--auth-mode",
            "login",
            "--yes",
            "--output",
            "none",
            "--only-show-errors",
        ]
        if content_type:
            command.extend(["--content-type", content_type])
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=45,
        )
        if completed.returncode != 0:
            raise MarkerStoreError("speech_marker_write_failed")


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run privacy-safe Azure Speech synthetic quality checks."
    )
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--endpoint", default="")
    parser.add_argument("--app-configuration-endpoint", default="")
    parser.add_argument("--timeout-seconds", type=int, default=1200)
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args()


def _require_execution_authority(args: argparse.Namespace) -> None:
    if os.getenv("PEERSLATE_AZURE_QUALIFICATION_ACTIVATED") != "true":
        raise SpeechQualificationError("qualification activation is not confirmed")
    if os.getenv("PEERSLATE_AZURE_CREDIT_CONFIRMED") != "true":
        raise SpeechQualificationError("Azure startup credit is not confirmed")
    if (
        os.getenv("PEERSLATE_AZURE_SPEND_AUTHORIZATION_REF")
        != EXPECTED_PROOF_AUTHORIZATION_REF
    ):
        raise SpeechQualificationError("speech proof authorization is invalid")
    _require_exact_origin(
        args.endpoint,
        EXPECTED_SPEECH_ENDPOINT,
        "Speech",
    )
    _require_exact_origin(
        args.app_configuration_endpoint,
        EXPECTED_APP_CONFIGURATION_ENDPOINT,
        "App Configuration",
    )
    if not 60 <= args.timeout_seconds <= 1800:
        raise SpeechQualificationError("Speech timeout is outside its safe bound")
    for executable in ("az", "espeak-ng", "ffmpeg", "ffprobe"):
        if shutil.which(executable) is None:
            raise SpeechQualificationError(f"required audio tool is unavailable: {executable}")


def _consume_proof_authorization(store, authorization_ref: str) -> None:
    if authorization_ref != EXPECTED_PROOF_AUTHORIZATION_REF:
        raise SpeechQualificationError("speech proof authorization is invalid")
    if store.read_optional(PROOF_CONSUMED_KEY):
        raise SpeechQualificationError("speech proof authorization is consumed")
    store.write(
        PROOF_CONSUMED_KEY,
        authorization_ref,
        content_type="text/plain",
    )
    if store.read_optional(PROOF_CONSUMED_KEY) != authorization_ref:
        raise SpeechQualificationError("speech proof authorization was not confirmed")


def _require_exact_origin(value: str, expected: str, label: str) -> None:
    parsed = urlsplit(value)
    expected_parsed = urlsplit(expected)
    if (
        value != expected
        or parsed.scheme != "https"
        or parsed.netloc != expected_parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise SpeechQualificationError(f"{label} endpoint is invalid")


def _run_audio_command(command: list[str], *, timeout: int = 180) -> None:
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        timeout=timeout,
    )
    if completed.returncode != 0:
        raise SpeechQualificationError("synthetic audio generation failed")


def _audio_duration(path: Path) -> float:
    completed = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    try:
        duration = float(completed.stdout.strip())
    except ValueError as error:
        raise SpeechQualificationError("synthetic audio duration is unavailable") from error
    if completed.returncode != 0 or not 1 <= duration <= MAX_AUDIO_SECONDS:
        raise SpeechQualificationError("synthetic audio duration is outside its bound")
    return duration


def _ffmpeg_filter(profile: str, duration: float) -> tuple[list[str], bool]:
    if profile == "light_noise":
        expression = (
            "[0:a]volume=0.82[voice];"
            f"anoisesrc=color=white:amplitude=0.010:duration={duration:.3f}:"
            "sample_rate=16000[noise];"
            "[voice][noise]amix=inputs=2:duration=first:dropout_transition=0"
        )
        return ["-filter_complex", expression], True
    filters = {
        "low_gain": "volume=0.30",
        "phone_band": "highpass=f=300,lowpass=f=3400,volume=0.80",
    }
    return ["-af", filters.get(profile, "volume=0.90")], False


def generate_profile_audio(case, directory: Path, target_seconds: float, maximum_seconds: float):
    """Generate one bounded transient MP3 and its exact synthetic reference text."""

    text_path = directory / f"{case.key}.txt"
    base_path = directory / f"{case.key}-base.wav"
    audio_path = directory / f"{case.key}.mp3"
    text_path.write_text(case.text + "\n", encoding="utf-8")
    _run_audio_command(
        [
            "espeak-ng",
            "-v",
            "en-us",
            "-s",
            str(case.speed_wpm),
            "-p",
            str(case.pitch),
            "-f",
            str(text_path),
            "-w",
            str(base_path),
        ]
    )
    base_duration = _audio_duration(base_path)
    repeats = math.ceil(target_seconds / base_duration)
    duration_limit = base_duration * repeats
    if duration_limit > maximum_seconds:
        raise SpeechQualificationError("speech profile would exceed its audio ceiling")
    filter_arguments, _uses_complex_filter = _ffmpeg_filter(case.profile, duration_limit)
    _run_audio_command(
        [
            "ffmpeg",
            "-v",
            "error",
            "-stream_loop",
            str(repeats - 1),
            "-i",
            str(base_path),
            "-t",
            f"{duration_limit:.3f}",
            *filter_arguments,
            "-ar",
            "16000",
            "-ac",
            "1",
            "-codec:a",
            "libmp3lame",
            "-b:a",
            "32k",
            str(audio_path),
        ],
        timeout=300,
    )
    final_duration = _audio_duration(audio_path)
    if final_duration < target_seconds or final_duration > maximum_seconds:
        raise SpeechQualificationError("generated speech profile missed its duration envelope")
    expected_text = " ".join(case.text for _ in range(repeats))
    return audio_path, expected_text, final_duration


def _emit(report: dict) -> None:
    print(json.dumps(report, sort_keys=True))


def _execute_profiles(
    cases,
    progress: SpeechProgress,
    *,
    store,
    transcriber,
    temp_root: Path,
    audio_generator=generate_profile_audio,
    monotonic=time.monotonic,
    transcription_error_type=None,
) -> tuple[SpeechProgress, str | None]:
    """Run at most one pre-recorded paid attempt per profile and UTC day."""

    if transcription_error_type is None:
        from services.speech_transcription_service import SpeechTranscriptionError

        transcription_error_type = SpeechTranscriptionError

    target_per_profile = TARGET_AUDIO_SECONDS / len(cases)
    maximum_per_profile = MAX_AUDIO_SECONDS / len(cases)
    results = dict(progress.results)
    attempts = dict(progress.attempts)
    stop_category = None
    for case in cases:
        if case.key in results:
            continue
        if case.key in attempts:
            # A prior process may have lost the provider result after the call.
            # Never replay that key on the same UTC day; continue with other
            # never-attempted profiles inside the unchanged daily ceiling.
            stop_category = stop_category or "speech_attempt_outcome_ambiguous"
            continue
        audio_path, expected_text, audio_seconds = audio_generator(
            case, temp_root, target_per_profile, maximum_per_profile
        )
        attempt_seconds = rounded_audio_seconds(audio_seconds)
        reserved = replace(
            progress,
            attempts={**attempts, case.key: attempt_seconds},
            results=dict(results),
        )
        try:
            # Durable before the paid call. If this write fails, the call is
            # not made. If the process or provider outcome becomes ambiguous,
            # later runs see the reservation and refuse to replay this case.
            store.write(
                PROGRESS_KEY,
                progress_to_json(reserved),
                content_type="application/json",
            )
        except MarkerStoreError as error:
            audio_path.unlink(missing_ok=True)
            return progress, str(error)
        progress = reserved
        attempts[case.key] = attempt_seconds
        try:
            started = monotonic()
            response = transcriber.transcribe(
                audio_path.read_bytes(), "audio/mpeg", locale="en-US"
            )
            latency = monotonic() - started
            result = score_transcript(
                case,
                expected_text=expected_text,
                transcript=response["provider_transcript"],
                audio_seconds=audio_seconds,
                latency_seconds=latency,
            )
            if result.audio_seconds != attempt_seconds:
                raise SpeechQualificationError(
                    "speech result duration does not match its attempt"
                )
            results[case.key] = result
            completed = replace(
                progress,
                attempts=dict(attempts),
                results=dict(results),
            )
            store.write(
                PROGRESS_KEY,
                progress_to_json(completed),
                content_type="application/json",
            )
            progress = completed
        except transcription_error_type as error:
            return progress, error.code
        except MarkerStoreError as error:
            # The in-memory result is useful for this one report, while the
            # durable pre-call reservation prevents a later replay.
            return completed, str(error)
        except SpeechQualificationError as error:
            return progress, str(error)
        finally:
            audio_path.unlink(missing_ok=True)
    return progress, stop_category


def main() -> int:
    args = _arguments()
    try:
        cases = load_cases(args.fixture)
    except SpeechQualificationError as error:
        _emit({"mode": "refused", "stop_category": str(error)})
        return 2
    fixture_digest = case_contract_digest(cases)
    today = datetime.now(timezone.utc).date()
    empty = SpeechProgress(
        day=today,
        fixture_digest=fixture_digest,
        attempts={},
        results={},
    )
    if not args.execute:
        _emit(privacy_safe_report(cases, empty, mode="dry_run"))
        return 0
    try:
        _require_execution_authority(args)
        from services.speech_transcription_service import (
            SpeechTranscriptionError,
            SpeechTranscriptionService,
        )

        credential = _preflight_speech_credential()
        store = AppConfigurationMarkerStore(args.app_configuration_endpoint)
        authorization_ref = os.getenv(
            "PEERSLATE_AZURE_SPEND_AUTHORIZATION_REF", ""
        )
        _consume_proof_authorization(store, authorization_ref)
        progress = progress_from_json(
            store.read(PROGRESS_KEY),
            expected_day=today,
            expected_fixture_digest=fixture_digest,
        )
        privacy_safe_report(cases, progress, mode="resume_check")
        if store.read(LAST_SUCCESS_KEY) == today.isoformat():
            report = privacy_safe_report(cases, progress, mode="skipped")
            report["already_complete"] = True
            _emit(report)
            return 0 if report["quality_checks_passed"] else 4
    except (ImportError, MarkerStoreError, SpeechQualificationError) as error:
        _emit(privacy_safe_report(cases, empty, mode="refused", stop_category=str(error)))
        return 2

    transcriber = SpeechTranscriptionService(
        endpoint=args.endpoint,
        credential=credential,
        timeout_seconds=args.timeout_seconds,
    )
    try:
        with tempfile.TemporaryDirectory(prefix="peerslate-speech-regression-") as root:
            progress, stop_category = _execute_profiles(
                cases,
                progress,
                store=store,
                transcriber=transcriber,
                temp_root=Path(root),
            )
    except SpeechTranscriptionError as error:
        stop_category = error.code
    except MarkerStoreError as error:
        stop_category = str(error)
    except SpeechQualificationError as error:
        stop_category = str(error)

    report = privacy_safe_report(
        cases,
        progress,
        mode="executed",
        stop_category=stop_category,
    )
    if report["success_marker_eligible"]:
        try:
            store.write(LAST_SUCCESS_KEY, today.isoformat())
        except MarkerStoreError as error:
            report["success_marker_eligible"] = False
            report["stop_category"] = str(error)
            _emit(report)
            return 3
    _emit(report)
    if stop_category:
        return 3
    return 0 if report["quality_checks_passed"] else 4


if __name__ == "__main__":
    raise SystemExit(main())
