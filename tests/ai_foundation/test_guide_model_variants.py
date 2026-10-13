"""Approved Guide variant matrix; no token or network call is needed."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
from hashlib import sha256
import json
import unittest

from services.ai_foundation import contracts
from services.ai_foundation.contracts import Audience, ExtractionPurpose, StructuredRequest
from services.ai_foundation.azure_foundry import (
    AzureFoundryResponsesProvider, LunaPriceSchedule, SolExtractionPriceSchedule,
    SolSynthesisSafetyPriceSchedule, SpendLedger, RESPONSE_IDENTITY_CONFIGURED_DEPLOYMENT,
)


class GuideVariantTests(unittest.TestCase):
    def request(self, profile="interview", **changes):
        values = dict(request_id="fictional-request", product=("my_data_intake" if profile == "extraction"
            else "resume_private_assistance"), purpose=(ExtractionPurpose.MY_DATA_INTAKE_EXTRACTION
            if profile == "extraction" else ExtractionPurpose.RESUME_CAREER_INTERVIEW), audience=Audience.OWNER,
            subject_key="fictional-owner", instructions="Private proposal only.", input_text="Fictional source material.",
            schema_name="fictional_schema", model_name="gpt-6.1-sol", reasoning_effort="medium")
        values.update(changes)
        return StructuredRequest(**values)

    def record(self, name, profile):
        getter = getattr(contracts, "guide_model_variant", None)
        self.assertTrue(callable(getter), "A closed named variant lookup is required")
        return getter(name, profile=profile)

    def validator(self):
        validator = getattr(contracts, "validate_guide_variant_bindings", None)
        self.assertTrue(callable(validator), "Settings, factory and allocation must share one record")
        return validator

    def bindings(self, record):
        cap = (105000000 if record.profile == "interview" else 30000000)
        if record.name == "turn.sol6_low": cap = 5000000
        if record.name == "organize.luna_low": cap = 6000000
        allocation = dict(variant=record.name, model=record.model_name, model_version=record.model_version,
            reasoning_effort=record.reasoning_effort, service_tier="default", scope="fictional-" + record.profile,
            maximum_calls=100, concurrent_requests=1, hard_cap_micro_usd=cap,
            reservation_micro_usd=record.reservation_micro_usd, input_tokens=record.input_tokens,
            output_tokens=record.output_tokens, input_micro_usd_per_million=record.input_micro_usd_per_million,
            output_micro_usd_per_million=record.output_micro_usd_per_million)
        contract = dict(variant=record.name, model=record.model_name, model_version=record.model_version,
            alias=record.deployment, effort=record.reasoning_effort, tier="default", wire_bytes=record.wire_bytes,
            input_tokens=record.input_tokens, output_tokens=record.output_tokens,
            safety_prices_per_million_micro_usd=[record.input_micro_usd_per_million, record.output_micro_usd_per_million])
        settings = dict(variant=record.name, endpoint="https://synthetic.openai.azure.com", deployment=record.deployment,
            provider={"maximum_input_bytes": record.wire_bytes, "maximum_input_tokens": record.input_tokens,
                      "maximum_output_tokens": record.output_tokens},
            prices={"input_micro_usd_per_million": record.input_micro_usd_per_million,
                    "output_micro_usd_per_million": record.output_micro_usd_per_million, "schedule_ref": "fictional-bound-schedule"},
            budget={key: allocation[key] for key in ("scope", "maximum_calls", "hard_cap_micro_usd", "concurrent_requests")})
        return dict(settings=settings, allocation=allocation, contract=contract)

    def test_sol61_owner_extraction_and_turn_accept_only_low_medium(self):
        for profile in ("extraction", "interview"):
            for effort in ("low", "medium"):
                with self.subTest(profile=profile, effort=effort):
                    try:
                        request = self.request(profile, reasoning_effort=effort)
                    except ValueError:
                        request = None
                    self.assertIsNotNone(request, "Approved Sol 6.1 pair must be admitted")

    def test_sol61_invalid_combinations_remain_rejected(self):
        for profile in ("extraction", "interview"):
            for changes in ({"reasoning_effort": "high"}, {"reasoning_effort": "xhigh"},
                    {"reasoning_effort": "minimal"}, {"audience": Audience.PUBLIC},
                    {"audience": Audience.AUTHORIZED_RECRUITER}, {"product": "ask_pete"},
                    {"purpose": ExtractionPurpose.MY_DATA_INTAKE_MATCHING}, {"purpose": "resume_career_interview"}):
                with self.subTest(profile=profile, changes=changes), self.assertRaises(ValueError):
                    self.request(profile, **changes)
        for effort in ("low", "medium", "xhigh"):
            with self.subTest(synthesis=effort), self.assertRaises(ValueError):
                self.request(purpose=ExtractionPurpose.RESUME_PRIVATE_SYNTHESIS, reasoning_effort=effort)
        self.request(purpose=ExtractionPurpose.RESUME_PRIVATE_SYNTHESIS, reasoning_effort="high")

    def test_six_records_have_the_exact_frozen_bounds_and_prices(self):
        expected = {
            "turn.sol6_low": ("interview", "gpt-6-sol", "eval0930-gpt-6-sol", "2026-09-22", "low", 65536, 66560, 32768, 5000000, 15000000, 824320),
            "turn.sol61_medium": ("interview", "gpt-6.1-sol", "peerslate-resume-sol61", "2026-09-29", "medium", 65536, 66560, 16384, 100000000, 100000000, 8294400),
            "turn.sol61_low": ("interview", "gpt-6.1-sol", "peerslate-resume-sol61", "2026-09-29", "low", 65536, 66560, 16384, 100000000, 100000000, 8294400),
            "organize.luna_low": ("extraction", "gpt-6-luna", "gpt-6-luna", "2026-09-22", "low", 229376, 230400, 128000, 1000000, 6000000, 998400),
            "organize.sol61_medium": ("extraction", "gpt-6.1-sol", "peerslate-resume-sol61", "2026-09-29", "medium", 73728, 74752, 24576, 100000000, 100000000, 9932800),
            "organize.sol61_low": ("extraction", "gpt-6.1-sol", "peerslate-resume-sol61", "2026-09-29", "low", 73728, 74752, 24576, 100000000, 100000000, 9932800),
        }
        for name, values in expected.items():
            with self.subTest(name=name):
                record = self.record(name, values[0])
                self.assertEqual(tuple(getattr(record, key) for key in ("profile", "model_name", "deployment", "model_version",
                    "reasoning_effort", "wire_bytes", "input_tokens", "output_tokens", "input_micro_usd_per_million",
                    "output_micro_usd_per_million", "reservation_micro_usd")), values)
                self.assertEqual(self.validator()(name, profile=values[0], **self.bindings(record)), record)

    def test_unknown_names_wrong_profiles_and_mutation_are_refused(self):
        self.record("turn.sol61_medium", "interview")
        for name, profile in ((None, "interview"), (1, "interview"), ("turn.unknown", "interview"),
                ("turn.sol61_medium", "extraction"), ("organize.sol61_low", "public")):
            with self.subTest(name=name, profile=profile), self.assertRaises(ValueError):
                contracts.guide_model_variant(name, profile=profile)
        record = self.record("turn.sol61_medium", "interview")
        with self.assertRaises(FrozenInstanceError):
            record.reasoning_effort = "high"
        with self.assertRaises(TypeError):
            contracts.GUIDE_MODEL_VARIANTS["turn.sol61_medium"] = record

    def test_single_field_binding_tampering_is_rejected(self):
        record = self.record("organize.sol61_medium", "extraction")
        bindings = self.bindings(record)
        paths = [
            ("settings", "variant"), ("settings", "deployment"),
            ("settings", "provider", "maximum_input_bytes"), ("settings", "provider", "maximum_input_tokens"),
            ("settings", "provider", "maximum_output_tokens"), ("settings", "budget", "scope"),
            ("settings", "budget", "hard_cap_micro_usd"), ("settings", "prices", "input_micro_usd_per_million"),
            ("allocation", "variant"), ("allocation", "model"), ("allocation", "model_version"),
            ("allocation", "reasoning_effort"), ("allocation", "service_tier"), ("allocation", "scope"),
            ("allocation", "reservation_micro_usd"), ("allocation", "input_tokens"), ("allocation", "output_tokens"),
            ("allocation", "output_micro_usd_per_million"),
            ("contract", "variant"), ("contract", "model"), ("contract", "model_version"),
            ("contract", "alias"), ("contract", "effort"), ("contract", "tier"),
            ("contract", "wire_bytes"), ("contract", "input_tokens"), ("contract", "output_tokens"),
            ("contract", "safety_prices_per_million_micro_usd"),
        ]
        for path in paths:
            changed = deepcopy(bindings); target = changed
            for key in path[:-1]: target = target[key]
            old = target[path[-1]]
            target[path[-1]] = old + 1 if type(old) is int else ("wrong" if type(old) is str else [1, 1])
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.validator()(record.name, profile=record.profile, **changed)

    def test_variant_request_validation_rejects_a_different_accepted_request(self):
        record = self.record("turn.sol61_medium", "interview")
        validator = getattr(contracts, "validate_guide_variant_request", None)
        self.assertTrue(callable(validator))
        self.assertEqual(validator(record.name, self.request(), profile="interview"), record)
        with self.assertRaises(ValueError):
            validator(record.name, self.request(model_name="gpt-6-sol", reasoning_effort="low"), profile="interview")

    def test_equal_valued_float_and_boolean_binding_changes_are_rejected(self):
        record = self.record("turn.sol61_medium", "interview")
        for group, key, value in (("budget", "concurrent_requests", True),
                ("budget", "hard_cap_micro_usd", 105000000.0), ("provider", "maximum_output_tokens", 16384.0)):
            changed = self.bindings(record)
            changed["settings"][group][key] = value
            with self.subTest(group=group, key=key), self.assertRaises(ValueError):
                self.validator()(record.name, profile=record.profile, **changed)

    def test_four_new_variants_use_the_bound_foundation_provider_with_fake_transport(self):
        from tests.ai_foundation.test_azure_foundry_provider import FakeTransport, FakeResponse
        schema = {"type":"object", "additionalProperties":False, "properties":{"ok":{"type":"boolean"}}, "required":["ok"]}
        for profile, prefix in (("interview", "turn"), ("extraction", "organize")):
            for effort in ("low", "medium"):
                with self.subTest(profile=profile, effort=effort):
                    record = self.record(prefix + ".sol61_" + effort, profile)
                    request = self.request(profile, reasoning_effort=effort)
                    calls = []
                    transport = FakeTransport(FakeResponse(200, {"id":"resp_fictional", "status":"completed",
                        "model":record.deployment, "model_version":record.model_version,
                        "usage":{"input_tokens":10, "output_tokens":5}, "output":[{"type":"message",
                            "content":[{"type":"output_text", "text":'{"ok":true}'}]}]}))
                    provider = AzureFoundryResponsesProvider(endpoint="https://synthetic.openai.azure.com",
                        deployment=record.deployment, model_name=record.model_name, model_version=record.model_version,
                        price_schedule=SolSynthesisSafetyPriceSchedule(), token_provider=lambda: calls.append(True) or "fictional-token",
                        transport=transport, spend_ledger=SpendLedger(hard_cap_micro_usd=record.reservation_micro_usd, max_calls=1),
                        maximum_input_bytes=record.wire_bytes, maximum_input_tokens=record.input_tokens,
                        maximum_output_tokens=record.output_tokens,
                        response_identity_mode=RESPONSE_IDENTITY_CONFIGURED_DEPLOYMENT)
                    self.validator()(record.name, profile=profile, **self.bindings(record))
                    contracts.validate_guide_variant_request(record.name, request, profile=profile)
                    result = provider.respond(request, response_schema=schema, maximum_output_tokens=record.output_tokens)
                    self.assertEqual(result.payload, {"ok":True})
                    self.assertEqual((result.model_name, result.configured_model_version), (record.model_name, record.model_version))
                    self.assertEqual((len(calls), len(transport.calls)), (1, 1))
                    self.assertEqual(transport.calls[0][1]["json"]["reasoning"], {"effort":effort})

    def test_configured_deployment_mode_still_rejects_wrong_alias_or_version(self):
        from services.ai_foundation.errors import ProviderUnavailableError
        from tests.ai_foundation.test_azure_foundry_provider import FakeTransport, FakeResponse
        record = self.record("turn.sol61_medium", "interview")
        for change in ({"model":"gpt-6.1-sol"}, {"model_version":"wrong-version"}):
            payload = {"id":"resp_fictional", "status":"completed", "model":record.deployment,
                "model_version":record.model_version, "usage":{"input_tokens":10,"output_tokens":5},
                "output":[{"type":"message", "content":[{"type":"output_text","text":'{}'}]}], **change}
            provider = AzureFoundryResponsesProvider(endpoint="https://synthetic.openai.azure.com",
                deployment=record.deployment, model_name=record.model_name, model_version=record.model_version,
                price_schedule=SolSynthesisSafetyPriceSchedule(), token_provider=lambda: "fictional-token",
                transport=FakeTransport(FakeResponse(200,payload)),
                spend_ledger=SpendLedger(hard_cap_micro_usd=record.reservation_micro_usd,max_calls=1),
                response_identity_mode=RESPONSE_IDENTITY_CONFIGURED_DEPLOYMENT)
            with self.subTest(change=change), self.assertRaises(ProviderUnavailableError):
                provider.respond(self.request(), response_schema={"type":"object","properties":{},
                    "additionalProperties":False,"required":[]})

    def test_incumbent_wire_bytes_and_request_fields_are_unchanged(self):
        self.assertEqual(tuple(StructuredRequest.__dataclass_fields__), ("request_id", "product", "purpose", "audience",
            "subject_key", "instructions", "input_text", "schema_name", "reasoning_effort", "model_name"))
        cases = [
            ("extraction", "gpt-6-luna", "gpt-6-luna", "2026-09-22", "low", ExtractionPurpose.MY_DATA_INTAKE_EXTRACTION,
             128000, LunaPriceSchedule(), "a91cb0442b64c91e06180e0991605da9909c3c1c6ef3288df0a6daa374b0b573"),
            ("interview", "gpt-6-sol", "eval0930-gpt-6-sol", "2026-09-22", "low", ExtractionPurpose.RESUME_CAREER_INTERVIEW,
             32768, SolExtractionPriceSchedule(), "dc5e8ee94a445e449656996491f6419a2733495310e7e978afb1de7c8a975583"),
            ("interview", "gpt-6.1-sol", "peerslate-resume-sol61", "2026-09-29", "high", ExtractionPurpose.RESUME_PRIVATE_SYNTHESIS,
             16384, SolSynthesisSafetyPriceSchedule(), "d87630f19a32d49caba336d6a2400200d06b409ff4dfc7ec665a02d1d54e9497"),
        ]
        schema = {"type":"object", "additionalProperties":False, "properties":{"ok":{"type":"boolean"}}, "required":["ok"]}
        for profile, model, deployment, version, effort, purpose, output, price, expected in cases:
            with self.subTest(model=model):
                request = self.request(profile, model_name=model, reasoning_effort=effort, purpose=purpose)
                provider = AzureFoundryResponsesProvider(endpoint="https://synthetic.openai.azure.com",
                    token_provider=lambda: self.fail("Wire construction must not request credentials"), deployment=deployment,
                    model_name=model, model_version=version, price_schedule=price,
                    spend_ledger=SpendLedger(hard_cap_micro_usd=20000000, max_calls=10))
                wire = provider.structured_payload(request, response_schema=schema, maximum_output_tokens=output)
                raw = json.dumps(wire, separators=(",", ":"), ensure_ascii=False).encode()
                self.assertEqual(sha256(raw).hexdigest(), expected)


if __name__ == "__main__":
    unittest.main()
