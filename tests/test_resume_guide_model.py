"""Record-driven Guide providers, explicit ongoing funding and no global switch."""
from copy import deepcopy
import importlib
import importlib.util
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from uuid import uuid4

from services.ai_foundation.contracts import guide_model_variant
from services.my_data_extraction_adapter import MyDataExtractionAdapter
from services.resume_intake_runtime import BoundedPrivateResumeProvider,BoundedResumeExtractionProvider
from tests.ai_foundation.test_azure_foundry_provider import FakeResponse,FakeTransport


class GuideModelCompositionTests(unittest.TestCase):
    def settings(self, profile, effort="medium", *, cap=None):
        name = ("turn" if profile=="interview" else "organize")+".sol61_"+effort
        record = guide_model_variant(name,profile=profile)
        cap = cap if cap is not None else (105000000 if profile=="interview" else 30000000)
        return record,{"variant":name,"endpoint":"https://synthetic.openai.azure.com","deployment":record.deployment,
            "provider":{"maximum_input_bytes":record.wire_bytes,"maximum_input_tokens":record.input_tokens,
                "maximum_output_tokens":record.output_tokens},
            "prices":{"input_micro_usd_per_million":record.input_micro_usd_per_million,
                "output_micro_usd_per_million":record.output_micro_usd_per_million,"schedule_ref":"fixture-guide-safety-not-invoice"},
            "budget":{"scope":"fixture-guide-"+profile,"maximum_calls":100,"hard_cap_micro_usd":cap,"concurrent_requests":1}}

    def port(self):
        return SimpleNamespace(validate_profile=Mock(return_value=True),reserve=Mock(return_value=None),settle_completed=Mock(return_value=None))

    def construct(self,profile,settings,*,port=None,token=None,transport=None,purpose="acceptance"):
        options = dict(settings=settings,database=Mock(),ongoing_budget_port=port,
                       token_provider=token or Mock(return_value="fixture-token"),transport=transport or Mock(),guide_budget_purpose=purpose)
        return (BoundedResumeExtractionProvider(**options) if profile=="extraction"
                else BoundedPrivateResumeProvider(profile,**options))

    def test_one_provisional_switch_point_and_purpose_specific_caps(self):
        spec = importlib.util.find_spec("services.resume_guide_model")
        self.assertIsNotNone(spec,"Guide model selection must have one explicit switch point")
        module = importlib.import_module("services.resume_guide_model")
        self.assertEqual(module.selected_guide_variant("interview").name,"turn.sol61_medium")
        self.assertEqual(module.selected_guide_variant("extraction").name,"organize.sol61_medium")
        for profile,acceptance in (("interview",105000000),("extraction",30000000)):
            record,_ = self.settings(profile)
            self.assertEqual(module.guide_budget_ceiling(profile,record.name,purpose="acceptance"),acceptance)
            self.assertEqual(module.guide_budget_ceiling(profile,record.name,purpose="evaluation"),65000000)
            with self.assertRaises(ValueError):
                module.guide_budget_ceiling(profile,record.name,purpose="unapproved")

    def test_four_named_variants_construct_without_work_and_dispatch_exact_fake_envelopes(self):
        schema = {"type":"object","properties":{"ok":{"type":"boolean"}},"required":["ok"],"additionalProperties":False}
        for profile in ("interview","extraction"):
            for effort in ("low","medium"):
                with self.subTest(profile=profile,effort=effort):
                    record,settings = self.settings(profile,effort)
                    token,port = Mock(return_value="fixture-token"),self.port()
                    transport = FakeTransport(FakeResponse(200,{"id":"resp_fixture","status":"completed",
                        "model":record.deployment,"model_version":record.model_version,"usage":{"input_tokens":10,"output_tokens":5},
                        "output":[{"type":"message","content":[{"type":"output_text","text":json.dumps({"ok":True})}]}]}))
                    provider = self.construct(profile,settings,port=port,token=token,transport=transport)
                    token.assert_not_called(); port.reserve.assert_not_called(); self.assertEqual(transport.calls,[])
                    if profile=="interview":
                        self.assertEqual(provider(owner="fixture-owner",request_id=str(uuid4()),instructions="Fictional only",
                            task="Help",context={},response_schema=schema),{"ok":True})
                    else:
                        adapter = MyDataExtractionAdapter(Mock(),model=record.model_name,reasoning_effort=effort,
                            maximum_output_tokens=record.output_tokens)
                        request = adapter.build_request("Fictional source")
                        with provider.owner_scope("fixture-owner"):
                            result = provider(request,response_schema=schema,maximum_output_tokens=record.output_tokens)
                        self.assertEqual(result.payload,{"ok":True})
                    self.assertEqual(token.call_count,1)
                    port.reserve.assert_called_once(); port.settle_completed.assert_called_once()
                    wire = transport.calls[0][1]["json"]
                    self.assertEqual((wire["model"],wire["reasoning"],wire["max_output_tokens"]),
                        (record.deployment,{"effort":effort},record.output_tokens))

    def test_new_variants_require_explicit_ongoing_port_and_do_not_enable_hosted_mode(self):
        for profile in ("interview","extraction"):
            _,settings = self.settings(profile)
            token,transport = Mock(),Mock()
            with self.subTest(profile=profile),self.assertRaises(ValueError):
                self.construct(profile,settings,token=token,transport=transport)
            token.assert_not_called(); transport.post.assert_not_called()

    def test_tampering_is_refused_before_funding_credentials_or_http(self):
        for profile in ("interview","extraction"):
            record,original = self.settings(profile)
            for change in ("extra_key","wrong_deployment","wrong_bound","cap_above_purpose","wrong_price","bad_endpoint","wrong_variant_profile"):
                settings = deepcopy(original)
                if change=="extra_key": settings["model_version"]="wrong"
                elif change=="wrong_deployment": settings["deployment"]="wrong"
                elif change=="wrong_bound": settings["provider"]["maximum_output_tokens"]+=1
                elif change=="cap_above_purpose": settings["budget"]["hard_cap_micro_usd"]+=1
                elif change=="wrong_price": settings["prices"]["input_micro_usd_per_million"]-=1
                elif change=="bad_endpoint": settings["endpoint"]="https://invalid.example"
                else: settings["variant"]="organize.sol61_medium" if profile=="interview" else "turn.sol61_medium"
                port,token,transport = self.port(),Mock(),Mock()
                with self.subTest(profile=profile,change=change),self.assertRaises(ValueError):
                    self.construct(profile,settings,port=port,token=token,transport=transport)
                port.reserve.assert_not_called(); token.assert_not_called(); transport.post.assert_not_called()

    def test_evaluation_cap_is_explicit_and_does_not_change_acceptance_ceiling(self):
        _,settings = self.settings("extraction",cap=65000000)
        with self.assertRaises(ValueError): self.construct("extraction",settings,port=self.port())
        provider = self.construct("extraction",settings,port=self.port(),purpose="evaluation")
        self.assertEqual(provider.budget["hard_cap_micro_usd"],65000000)

    def test_service_composition_carries_the_explicit_evaluation_ceiling(self):
        from services.resume_intake_runtime import build_private_resume_assistance
        _,settings = self.settings("interview",cap=105000000)
        config = {"RESUME_PRIVATE_ASSISTANCE_CONFIGURATION":{"profiles":{"interview":settings},"limits":{
            "maximum_task_bytes":20000,"maximum_input_bytes":65536,"maximum_output_bytes":100000,
            "maximum_field_bytes":8000,"proof_max_age_seconds":900}}}
        options = dict(draft_service=Mock(),catalog=Mock(),policy_repository=Mock(),database=Mock(),
            token_provider=Mock(),signer=Mock(),ongoing_budget_port=self.port(),guide_budget_purpose="evaluation")
        with self.assertRaises(ValueError): build_private_resume_assistance(config,**options)
        settings["budget"]["hard_cap_micro_usd"] = 65000000
        service = build_private_resume_assistance(config,**options)
        self.assertEqual(service.providers["interview"].budget["hard_cap_micro_usd"],65000000)


    def test_invalid_endpoint_refuses_before_port_admission(self):
        from services.resume_intake_runtime import BoundedResumeExtractionProvider
        _,settings=self.settings("extraction")
        settings["endpoint"]="http://synthetic.openai.azure.com"
        port=self.port();token=Mock();transport=Mock()
        with self.assertRaises(ValueError):
            BoundedResumeExtractionProvider(settings=settings,database=Mock(),token_provider=token,
                transport=transport,ongoing_budget_port=port)
        port.validate_profile.assert_not_called()
        port.reserve.assert_not_called();token.assert_not_called();transport.post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
