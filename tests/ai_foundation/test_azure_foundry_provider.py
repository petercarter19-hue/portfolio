import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from unittest import mock

from services.ai_foundation import AIRequest, Audience, Purpose, SourceVersion
from services.ai_foundation.azure_foundry import (
    AzureFoundryResponsesProvider,
    ExecutionLimitError,
    FoundryUsage,
    LunaPriceSchedule,
    ProviderUnavailableError,
    SpendLedger,
    UrllibTransport,
)

ROOT = Path(__file__).resolve().parents[2]


def request_and_sources():
    request = AIRequest(
        request_id="foundry-test",
        product="test",
        purpose=Purpose.PUBLIC_PROFILE_ANSWER,
        audience=Audience.PUBLIC,
        subject_key="synthetic:one",
        question="What is documented?",
    )
    source = SourceVersion.approved(
        source_version_key="source-v1",
        source_key="source",
        version=1,
        subject_key="synthetic:one",
        title="Synthetic source",
        content="Delivery is documented.",
        allowed_audiences=frozenset({Audience.PUBLIC}),
        allowed_purposes=frozenset({Purpose.PUBLIC_PROFILE_ANSWER}),
    )
    return request, (source,)


def answer_payload(input_tokens=608, output_tokens=478):
    answer = {
        "answer_id": "answer-one",
        "state": "supported",
        "summary": "The delivery is documented.",
        "claims": [
            {
                "claim_id": "claim-one",
                "text": "Delivery is documented.",
                "kind": "evidence",
                "state": "supported",
                "citations": [
                    {
                        "claim_id": "claim-one",
                        "source_version_key": "source-v1",
                        "start": 0,
                        "end": 23,
                        "excerpt": "Delivery is documented.",
                    }
                ],
                "limitation": None,
            }
        ],
        "follow_up_questions": [],
        "handoff": None,
        "model_name": "gpt-5.6-luna",
        "prompt_contract_version": "test-v1",
    }
    return {
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": json.dumps(answer)}],
            }
        ],
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
    }


@dataclass
class FakeResponse:
    status_code: int
    payload: object

    def json(self):
        return self.payload


class FakeTransport:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


class AzureFoundryProviderTests(unittest.TestCase):
    def provider(self, response=None, **kwargs):
        transport = FakeTransport(response or FakeResponse(200, answer_payload()))
        usages: list[FoundryUsage] = []
        ledger = kwargs.pop(
            "spend_ledger",
            SpendLedger(hard_cap_micro_usd=1_250_000, max_calls=10),
        )
        provider = AzureFoundryResponsesProvider(
            endpoint="https://synthetic.openai.azure.com",
            token_provider=lambda: "not-a-real-token",
            transport=transport,
            spend_ledger=ledger,
            usage_sink=usages.append,
            **kwargs,
        )
        return provider, transport, usages, ledger

    def test_v1_response_call_is_non_storing_and_reports_usage_only(self):
        provider, transport, usages, ledger = self.provider()
        request, sources = request_and_sources()
        result = provider.answer(request, sources)
        self.assertEqual(result["state"], "supported")
        self.assertEqual(len(transport.calls), 1)
        url, call = transport.calls[0]
        self.assertEqual(url, "https://synthetic.openai.azure.com/openai/v1/responses")
        self.assertFalse(call["json"]["store"])
        self.assertEqual(call["json"]["model"], "gpt-5.6-luna")
        self.assertEqual(call["timeout"], (5.0, 90.0))
        self.assertEqual(usages[0].input_tokens, 608)
        self.assertFalse(hasattr(usages[0], "prompt"))
        self.assertEqual(ledger.snapshot()["spent_micro_usd"], 3476)

    def test_endpoint_must_be_the_exact_azure_openai_origin_shape(self):
        rejected = (
            "http://synthetic.openai.azure.com",
            "https://openai.azure.com.evil.example",
            "https://synthetic.openai.azure.com.evil.example",
            "https://synthetic.openai.azure.com/path",
            "https://user@synthetic.openai.azure.com",
            "https://synthetic.openai.azure.com:444",
        )
        for endpoint in rejected:
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError):
                AzureFoundryResponsesProvider(
                    endpoint=endpoint,
                    token_provider=lambda: "not-a-real-token",
                    spend_ledger=SpendLedger(
                        hard_cap_micro_usd=1_250_000,
                        max_calls=1,
                    ),
                )

    def test_explicit_price_schedule_matches_measured_luna_example(self):
        price = LunaPriceSchedule()
        self.assertEqual(
            price.estimate_micro_usd(input_tokens=60_228, output_tokens=47_320),
            344_148,
        )

    def test_http_failure_is_generic_and_charges_the_reservation(self):
        provider, _, _, ledger = self.provider(
            FakeResponse(429, {"private": "ignored"})
        )
        request, sources = request_and_sources()
        with self.assertRaisesRegex(ProviderUnavailableError, "HTTP 429") as raised:
            provider.answer(request, sources)
        self.assertNotIn("private", str(raised.exception))
        self.assertEqual(ledger.snapshot()["spent_micro_usd"], 5700)

    def test_missing_token_fails_without_calling_transport(self):
        transport = FakeTransport(FakeResponse(200, answer_payload()))
        ledger = SpendLedger(hard_cap_micro_usd=20_000, max_calls=1)
        provider = AzureFoundryResponsesProvider(
            endpoint="https://synthetic.openai.azure.com",
            token_provider=lambda: "",
            transport=transport,
            spend_ledger=ledger,
        )
        request, sources = request_and_sources()
        with self.assertRaises(ProviderUnavailableError):
            provider.answer(request, sources)
        self.assertEqual(transport.calls, [])
        self.assertEqual(ledger.snapshot()["spent_micro_usd"], 5700)

    def test_dollar_cap_and_call_cap_fail_closed_before_transport(self):
        ledger = SpendLedger(hard_cap_micro_usd=5_699, max_calls=1)
        provider, transport, _, _ = self.provider(spend_ledger=ledger)
        request, sources = request_and_sources()
        with self.assertRaises(ExecutionLimitError):
            provider.answer(request, sources)
        self.assertEqual(transport.calls, [])

        ledger = SpendLedger(hard_cap_micro_usd=20_000, max_calls=1)
        provider, transport, _, _ = self.provider(spend_ledger=ledger)
        provider.answer(request, sources)
        with self.assertRaises(ExecutionLimitError):
            provider.answer(request, sources)
        self.assertEqual(len(transport.calls), 1)

    def test_input_larger_than_the_prepaid_bound_never_calls_transport(self):
        provider, transport, _, ledger = self.provider(maximum_input_tokens=100)
        request, sources = request_and_sources()
        with self.assertRaisesRegex(ExecutionLimitError, "prepaid"):
            provider.answer(request, sources)
        self.assertEqual(transport.calls, [])
        self.assertEqual(ledger.snapshot()["calls"], 0)

    def test_malformed_usage_fails_closed_without_exposing_output(self):
        payload = answer_payload()
        payload["usage"] = {"input_tokens": "secret", "output_tokens": 1}
        provider, _, _, ledger = self.provider(FakeResponse(200, payload))
        request, sources = request_and_sources()
        with self.assertRaisesRegex(ProviderUnavailableError, "usage"):
            provider.answer(request, sources)
        self.assertEqual(ledger.snapshot()["spent_micro_usd"], 5700)

    def test_runner_is_dry_by_default_even_with_an_endpoint(self):
        environment = dict(os.environ)
        for name in (
            "PEERSLATE_AZURE_QUALIFICATION_ACTIVATED",
            "PEERSLATE_AZURE_CREDIT_CONFIRMED",
            "PEERSLATE_AZURE_SPEND_AUTHORIZATION_REF",
        ):
            environment.pop(name, None)
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/run_foundry_luna_evaluations.py",
                "--endpoint",
                "https://would-not-be-called.invalid",
            ],
            cwd=ROOT,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["mode"], "dry_run")
        self.assertFalse(report["prompts_or_outputs_retained"])

    def test_authorized_runner_refuses_an_unreviewed_fixture_before_network(self):
        environment = {
            **os.environ,
            "PEERSLATE_AZURE_QUALIFICATION_ACTIVATED": "true",
            "PEERSLATE_AZURE_CREDIT_CONFIRMED": "true",
            "PEERSLATE_AZURE_SPEND_AUTHORIZATION_REF": "synthetic-owner-ref",
        }
        fixture = (
            ROOT / "tests/fixtures/azure_startup_qualification/luna_eval_cases.json"
        )
        with tempfile.TemporaryDirectory() as directory:
            copied_fixture = Path(directory) / "unreviewed-cases.json"
            copied_fixture.write_bytes(fixture.read_bytes())
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_foundry_luna_evaluations.py",
                    "--execute",
                    "--endpoint",
                    "https://would-not-be-called.invalid",
                    "--fixture",
                    str(copied_fixture),
                ],
                cwd=ROOT,
                env=environment,
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("fixed reviewed synthetic fixture", completed.stderr)


class UrllibTransportTests(unittest.TestCase):
    """The real transport is the only path that can issue a billable request.

    urllib's default redirect handler keeps the Authorization header across a
    hop and does no same-origin check, so these tests pin the two protections
    that stop an Entra access token reaching an unvalidated host.
    """

    @staticmethod
    def _request_for(url="https://example-endpoint.invalid/openai/responses"):
        captured = {}

        class _FakeResponse:
            status = 200

            def read(self, size):
                return b'{"ok": true}'

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        def fake_open(request, timeout=None):
            captured["request"] = request
            captured["timeout"] = timeout
            return _FakeResponse()

        transport = UrllibTransport()
        with mock.patch.object(urllib.request, "build_opener") as build_opener:
            build_opener.return_value = mock.Mock(open=fake_open)
            response = transport.post(
                url,
                headers={"Authorization": "Bearer secret-token"},
                json={"input": "hello"},
                timeout=(5.0, 90.0),
            )
            captured["handlers"] = build_opener.call_args.args
        captured["response"] = response
        return captured

    def test_authorization_is_sent_unredirected(self):
        captured = self._request_for()
        request = captured["request"]
        # An unredirected header is dropped by urllib before it follows a hop.
        self.assertIn("Authorization", request.unredirected_hdrs)
        self.assertEqual(
            request.unredirected_hdrs["Authorization"], "Bearer secret-token"
        )

    def test_opener_is_built_with_a_redirect_refusing_handler(self):
        captured = self._request_for()
        handlers = captured["handlers"]
        self.assertTrue(handlers, "transport must install its own handler")
        handler = handlers[0]
        self.assertTrue(issubclass(handler, urllib.request.HTTPRedirectHandler))
        # Returning None from redirect_request makes urllib raise rather than
        # follow the hop.
        self.assertIsNone(
            handler().redirect_request(
                mock.Mock(), mock.Mock(), 302, "Found", {}, "https://elsewhere.invalid"
            )
        )

    def test_redirect_status_becomes_a_provider_error(self):
        """A 3xx must not be parsed as a successful body."""
        provider = AzureFoundryResponsesProvider(
            endpoint="https://example-endpoint.openai.azure.com",
            deployment="gpt-5.6-luna",
            token_provider=lambda: "token",
            spend_ledger=SpendLedger(hard_cap_micro_usd=1_000_000, max_calls=5),
            transport=_StatusOnlyTransport(302),
        )
        request, sources = request_and_sources()
        with self.assertRaises(ProviderUnavailableError):
            provider.answer(request, sources)


class SpendReportTests(unittest.TestCase):
    """The stop-path report must not under-count what was actually charged."""

    def test_call_count_and_money_come_from_the_same_ledger(self):
        from scripts.run_foundry_luna_evaluations import _spend_fields

        ledger = SpendLedger(hard_cap_micro_usd=1_000_000, max_calls=5)
        # One call that produced a usage record.
        ledger.reserve(5_700)
        ledger.settle(reserved_micro_usd=5_700, actual_micro_usd=3_476)
        usages = [
            FoundryUsage(
                input_tokens=608,
                output_tokens=478,
                estimated_micro_usd=3_476,
                price_schedule_ref=LunaPriceSchedule().schedule_ref,
                deployment="gpt-5.6-luna",
            )
        ]
        # One call that failed after reservation: charged in full, and it never
        # reaches the usage sink.
        ledger.reserve(5_700)
        ledger.settle(reserved_micro_usd=5_700, actual_micro_usd=None)

        fields = _spend_fields(ledger, usages)
        self.assertEqual(fields["calls_billed"], 2)
        self.assertEqual(fields["calls_with_usage"], 1)
        # The dollar figure covers both calls, so the count must too.
        self.assertAlmostEqual(
            fields["estimated_cost_usd"], (3_476 + 5_700) / 1_000_000
        )


@dataclass
class _StatusOnlyTransport:
    status_code: int

    def post(self, url, *, headers, json, timeout):
        return _FakeStatusResponse(self.status_code)


@dataclass
class _FakeStatusResponse:
    status_code: int

    def json(self):
        return {}


if __name__ == "__main__":
    unittest.main()
