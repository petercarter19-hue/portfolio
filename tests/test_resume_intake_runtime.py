"""Constructor/aggregate-budget/manual-path tests; no live calls or SQL proof."""
import copy
import json
import unittest
from uuid import uuid4

from services.ai_foundation.contracts import Audience, ExtractionPurpose, StructuredRequest
from services.ai_foundation.errors import ProviderUnavailableError
from services.my_data_extraction_adapter import EXTRACTION_MODEL
from services.resume_intake_repository import SqlResumeIntakeRepository
from services.resume_intake_runtime import (
    BoundedResumeExtractionProvider, PrivateResumeMatchingExclusions, build_hosted_resume_intake,
)
from services.resume_intake_service import ResumeIntakeUnavailableError


def settings():
    return {
        "endpoint": "https://fixture.openai.azure.com", "deployment": EXTRACTION_MODEL,
        "provider": {"maximum_input_bytes": 64000, "maximum_input_tokens": 65536, "maximum_output_tokens": 128000},
        "prices": {"input_micro_usd_per_million": 1000000, "output_micro_usd_per_million": 6000000, "schedule_ref": "explicit-safety-fixture"},
        "budget": {"scope": "mvp1-hosted-qualification-2026-09-30", "maximum_calls": 6, "hard_cap_micro_usd": 6000000, "concurrent_requests": 1},
    }


class DurableReservations:
    """Process-independent fixture shared by new provider objects."""
    def __init__(self):
        self.events, self.requests, self.prepaid, self.envelope = [], set(), 0, None
        self.active, self.finished, self.available, self.schema_ready = 0, 0, True, False

    def first_row(self, procedure, parameters=None):
        self.events.append(procedure)
        if procedure == "usp_GetResumeHostedReadiness":
            return {"schema_ready": self.schema_ready}
        params = dict(parameters or [])
        if procedure == "usp_ReserveResumeHostedExtractionForOwner":
            envelope = tuple(params[name] for name in ("@Scope", "@ReservationMicroUsd", "@MaximumCalls", "@HardCapMicroUsd", "@ConcurrentRequests"))
            if self.envelope is None:
                self.envelope = envelope
            if (not self.available or params["@UserKey"] != "member" or self.envelope != envelope
                    or len(self.requests) >= params["@MaximumCalls"]
                    or self.prepaid + params["@ReservationMicroUsd"] > params["@HardCapMicroUsd"]
                    or self.active >= params["@ConcurrentRequests"] or params["@RequestId"] in self.requests):
                return {"reserved": False}
            self.requests.add(params["@RequestId"])
            self.prepaid += params["@ReservationMicroUsd"]
            self.active += 1
            return {"reserved": True}
        if procedure == "usp_FinishResumeHostedExtractionForOwner":
            self.active -= 1
            self.finished += 1
            return {"finished": True}
        raise AssertionError(procedure)


class Transport:
    def __init__(self, database):
        self.database, self.calls, self.fail = database, 0, False

    def post(self, *args, **kwargs):
        self.calls += 1
        assert self.database.active == 1
        if self.fail:
            raise RuntimeError("private provider failure body")
        class Response:
            status_code = 200
            def json(self):
                return {"model": "gpt-6-luna", "status": "completed", "usage": {"input_tokens": 10, "output_tokens": 10},
                        "output": [{"type": "message", "content": [{"type": "output_text", "text": '{"candidates":[]}'}]}]}
        return Response()


def request(text="Private fixture material", request_id=None):
    return StructuredRequest(request_id=request_id or str(uuid4()), product="my_data_intake",
        purpose=ExtractionPurpose.MY_DATA_INTAKE_EXTRACTION, audience=Audience.OWNER,
        subject_key="member", instructions="Only supplied facts.", input_text=text,
        schema_name="fixture", reasoning_effort="low", model_name=EXTRACTION_MODEL)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.database = DurableReservations()
        self.transport = Transport(self.database)
        self.token_calls = 0

    def token(self):
        self.assertEqual(self.database.active, 1)
        self.token_calls += 1
        return "synthetic-token-not-a-credential"

    def provider(self, value=None):
        return BoundedResumeExtractionProvider(settings=value or settings(), database=self.database,
            token_provider=self.token, transport=self.transport)

    def call(self, provider, req=None):
        with provider.owner_scope("member"):
            return provider(req or request(), response_schema={"type": "object"}, maximum_output_tokens=128000)

    def test_no_constructor_io_and_sql_service_without_config(self):
        service = build_hosted_resume_intake({}, database=self.database)
        self.assertIsInstance(service.repository, SqlResumeIntakeRepository)
        self.assertIsNone(service.provider)
        self.assertIsNotNone(service.original_files)
        self.assertEqual(service.policy().max_document_bytes, 50_000_000)
        self.assertEqual(service.policy().max_recording_seconds, 300)
        self.assertEqual(self.database.events, [])
        with self.assertRaises(ResumeIntakeUnavailableError):
            service.get_workspace("member")
        self.assertEqual(self.database.events, ["usp_GetResumeHostedReadiness"])

    def test_global_six_call_limit_survives_new_provider_objects(self):
        for _ in range(6):
            self.call(self.provider())
        self.assertEqual(self.transport.calls, 6)
        self.assertEqual(self.database.prepaid, 6 * 833536)
        with self.assertRaises(ProviderUnavailableError):
            self.call(self.provider())
        self.assertEqual(self.transport.calls, 6)
        self.assertEqual(self.token_calls, 6)
        self.assertEqual(self.database.finished, 6)

    def test_unconfigured_storage_keeps_explicit_delete_pending_after_restart(self):
        from tests.test_resume_original_files import Metadata, DATA, PATH
        from services.resume_original_file_service import ResumeOriginalFileService
        from services.resume_original_file_repository import OriginalFileNotFound
        metadata = Metadata()
        key = str(uuid4())
        import hashlib
        metadata.command("member", {"type": "reserve", "original_key": key,
            "source_key": str(uuid4()), "source_version": 1, "blob_name": PATH,
            "content_type": "text/plain", "byte_length": len(DATA),
            "sha256": hashlib.sha256(DATA).hexdigest()})
        unavailable_storage = build_hosted_resume_intake({}, database=self.database).original_files.storage
        service = ResumeOriginalFileService(repository=metadata, storage=unavailable_storage)
        result = service.delete("member", key, expected_version=1, request_id=str(uuid4()))
        self.assertEqual(result["outcome"], "delete_pending")
        restarted = ResumeOriginalFileService(repository=metadata, storage=unavailable_storage)
        self.assertEqual(restarted.reconcile(), {"completed": 0, "pending": 1})
        self.assertEqual(metadata.rows[key]["blob_name"], PATH)
        with self.assertRaises(OriginalFileNotFound):
            restarted.download("member", key)

    def test_unavailable_accounting_or_missing_owner_precedes_credentials(self):
        provider = self.provider()
        with self.assertRaises(ProviderUnavailableError):
            provider(request(), response_schema={"type": "object"}, maximum_output_tokens=128000)
        self.database.available = False
        with self.assertRaises(ProviderUnavailableError):
            self.call(provider)
        self.assertEqual(self.transport.calls, 0)
        self.assertEqual(self.token_calls, 0)

    def test_full_schema_and_unicode_envelope_refusal_does_not_reserve(self):
        provider = self.provider()
        with self.assertRaises(ProviderUnavailableError):
            self.call(provider, request("\u754c" * 20000))
        with provider.owner_scope("member"), self.assertRaises(ProviderUnavailableError):
            provider(request(), response_schema={"type": "object", "description": "x" * 65000}, maximum_output_tokens=128000)
        self.assertEqual(self.database.requests, set())
        self.assertEqual(self.token_calls, 0)

    def test_failure_no_retry_no_refund_and_duplicate_request_no_redispatch(self):
        self.transport.fail = True
        provider, req = self.provider(), request()
        with self.assertRaises(ProviderUnavailableError):
            self.call(provider, req)
        self.assertEqual(self.transport.calls, 1)
        self.assertEqual(self.database.prepaid, 833536)
        with self.assertRaises(ProviderUnavailableError):
            self.call(self.provider(), req)
        self.assertEqual(self.transport.calls, 1)
        self.assertEqual(self.database.active, 1)
        self.assertEqual(self.database.finished, 0)

    def test_timeout_blocks_new_request_and_new_provider_without_refund_or_release(self):
        from unittest.mock import patch
        provider, req = self.provider(), request()
        with patch.object(self.transport, "post", side_effect=TimeoutError("private remote diagnostic")) as remote:
            with self.assertRaises(ProviderUnavailableError) as failed:
                self.call(provider, req)
            self.assertNotIn("private remote diagnostic", str(failed.exception))
            self.assertEqual(self.database.active, 1)
            self.assertEqual(self.database.finished, 0)
            self.assertEqual(self.database.prepaid, 833536)
            self.assertEqual(self.database.requests, {req.request_id})
            for next_provider in (provider, self.provider()):
                with self.assertRaises(ProviderUnavailableError):
                    self.call(next_provider, request())
            remote.assert_called_once()
        self.assertEqual(self.token_calls, 1)
        self.assertEqual(self.database.active, 1)
        self.assertEqual(self.database.prepaid, 833536)
        self.assertNotIn("usp_FinishResumeHostedExtractionForOwner", self.database.events)

    def test_successful_completion_releases_concurrency_but_keeps_full_charge(self):
        self.call(self.provider())
        self.assertEqual(self.database.active, 0)
        self.assertEqual(self.database.finished, 1)
        self.assertEqual(self.database.prepaid, 833536)
        self.call(self.provider(), request())
        self.assertEqual(self.database.active, 0)
        self.assertEqual(self.database.finished, 2)
        self.assertEqual(self.database.prepaid, 2 * 833536)
        self.assertEqual(self.transport.calls, 2)

    def test_hosted_receive_timeout_is_bounded_and_other_foundation_defaults_unchanged(self):
        from inspect import signature
        from unittest.mock import patch
        from services.ai_foundation.azure_foundry import AzureFoundryResponsesProvider
        with patch.object(self.transport, "post", wraps=self.transport.post) as remote:
            self.call(self.provider())
            remote.assert_called_once()
            self.assertEqual(remote.call_args.kwargs["timeout"], (5.0, 180.0))
        self.assertEqual(signature(AzureFoundryResponsesProvider.respond).parameters[
            "receive_timeout_seconds"].default, 90.0)
        self.assertEqual(self.database.active, 0)
        self.assertEqual(self.database.prepaid, 833536)

    def test_configuration_change_cannot_reset_shared_budget(self):
        self.call(self.provider())
        changed = settings()
        # An otherwise allowed lower envelope must not reset the immutable
        # shared scope. Above-six configurations now refuse at construction.
        changed["budget"]["maximum_calls"] = 5
        with self.assertRaises(ProviderUnavailableError):
            self.call(self.provider(changed))
        self.assertEqual(self.transport.calls, 1)

    def test_exclusions_remove_missing_deleted_and_excluded_metadata(self):
        class Policy:
            def list_entries(self, owner):
                assert owner == "member"
                return [{"entry_key": "eligible", "lifecycle": "active", "private_assistance_excluded": False},
                        {"entry_key": "excluded", "lifecycle": "active", "private_assistance_excluded": True},
                        {"entry_key": "deleted", "lifecycle": "deleted", "private_assistance_excluded": False}]
        class Catalog:
            def list_items(self, owner):
                assert owner == "member"
                return [{"record_key": key} for key in ("eligible", "excluded", "deleted", "missing")]
        exclusions = PrivateResumeMatchingExclusions(Policy(), Catalog())
        self.assertEqual(exclusions("member"), {"excluded", "deleted", "missing"})


if __name__ == "__main__":
    unittest.main()


# Named strengthened-wire follow-up only; ordinary prior22 checks are retained.
# No network, SQL engine, real identity, or model dispatch is performed here.
FROZEN_WIRE_RESULTS=[]


def _frozen_candidate():
    from pathlib import Path
    return Path(__file__).resolve().parents[1]


def _actual_provider_payload(req):
    """Pure actual Foundation wire constructor; no credential or transport."""
    from services.ai_foundation import azure_foundry as foundation
    from services.my_data_extraction_adapter import EXTRACTION_RESPONSE_SCHEMA
    provider = foundation.AzureFoundryResponsesProvider(
        endpoint="https://fixture.openai.azure.com", deployment=foundation.NATIVE_LUNA_DEPLOYMENT,
        model_name="gpt-6-luna", model_version=foundation.NATIVE_LUNA_MODEL_VERSION,
        price_schedule=foundation.LunaPriceSchedule(),
        spend_ledger=foundation.SpendLedger(hard_cap_micro_usd=998400, max_calls=1),
        token_provider=lambda: (_ for _ in ()).throw(AssertionError("credential")))
    return provider.structured_payload(req, response_schema=EXTRACTION_RESPONSE_SCHEMA,
                                       maximum_output_tokens=128000)


def _actual_provider_wire(req):
    from services.ai_foundation import azure_foundry as foundation
    return foundation._dumps_json(_actual_provider_payload(req),separators=(",", ":")).encode("utf-8")


def _prepared_payload(req):
    # Admission and transport now share the actual complete wire constructor.
    return _actual_provider_payload(req)


def _bounded_shortlist(char, target_bytes=96000):
    """Complete raw UTF8 JSON, normalized real editor fields, <=8000UTF16 summary."""
    from services.living_resume_editor_service import normalize_editor_values
    from services.my_data_extraction_adapter import _json_dumps
    def count(rows):return len(_json_dumps(rows).encode("utf-8"))
    rows=[]
    maximum_chars=8000//(len(char.encode("utf-16-le"))//2)
    while True:
        row={"record_key":f"00000000-0000-4000-8000-{len(rows)+1:012d}","record_type":"role",
             "values":normalize_editor_values("role",{"role_title":"Synthetic role","employer_name":"Synthetic employer","summary":char*maximum_chars})}
        if count(rows+[row])<=target_bytes:
            rows.append(row)
            continue
        row["values"]["summary"]=""
        available=target_bytes-count(rows+[row])
        if available<0:raise AssertionError("fixture overhead exceeds target")
        unit=len(_json_dumps(char)[1:-1].encode("utf-8"))
        row["values"]["summary"]=char*(available//unit)+"A"*(available%unit)
        row["values"]=normalize_editor_values("role",row["values"])
        rows.append(row)
        assert count(rows)==target_bytes
        return rows


def _qualification_settings():
    value=settings()
    value["provider"]={"maximum_input_bytes":229376,"maximum_input_tokens":230400,"maximum_output_tokens":128000}
    return value


class _BeforeDispatch(Exception):pass


class _AdmissionSpies:
    def __init__(self):self.reservations=self.credentials=self.transports=0
    def first_row(self,*args,**kwargs):
        self.reservations+=1
        raise _BeforeDispatch("inert SQL reservation sentinel; no database connection")
    def token(self):
        self.credentials+=1
        raise AssertionError("real credential boundary must never be reached")
    def post(self,*args,**kwargs):
        self.transports+=1
        raise AssertionError("real transport boundary must never be reached")


class FrozenWireTests(unittest.TestCase):
    def provider(self,spies):
        return BoundedResumeExtractionProvider(settings=_qualification_settings(),database=spies,
            token_provider=spies.token,transport=spies)

    def test_final_serialization_worst_cases_and_finite_admission(self):
        import hashlib
        from services.my_data_extraction_adapter import MyDataExtractionAdapter,EXTRACTION_RESPONSE_SCHEMA,_json_dumps
        adapter=MyDataExtractionAdapter()
        text="\u754c"*20000
        self.assertEqual(len(text.encode("utf-16-le"))//2,20000)
        for label,char in (("ascii","A"),("bmp_unicode","\u754c"),("nonbmp_unicode","\U0001f642"),("backslash","\\"),("quote",'"')):
            listed=_bounded_shortlist(char)
            req=adapter.build_request(text,shortlist=listed)
            wire=_actual_provider_wire(req)
            complete=_prepared_payload(req)
            self.assertEqual(complete,_actual_provider_payload(req))
            self.assertEqual(len(json.dumps(complete,separators=(",",":")).encode()),len(wire))
            spies=_AdmissionSpies();provider=self.provider(spies)
            if len(wire)<=229376:
                with provider.owner_scope("member"),self.assertRaises(_BeforeDispatch):
                    provider(req,response_schema=EXTRACTION_RESPONSE_SCHEMA,maximum_output_tokens=128000)
                self.assertEqual(spies.reservations,1)
                outcome="within_cap; stopped at inert reservation sentinel"
            else:
                with provider.owner_scope("member"),self.assertRaises(ProviderUnavailableError):
                    provider(req,response_schema=EXTRACTION_RESPONSE_SCHEMA,maximum_output_tokens=128000)
                self.assertEqual(spies.reservations,0)
                outcome="refused before SQL reservation/credentials/transport"
            self.assertEqual((spies.credentials,spies.transports),(0,0))
            FROZEN_WIRE_RESULTS.append({"case":label,"member_text_utf16_units":20000,
                "raw_shortlist_utf8_json_bytes":len(_json_dumps(listed).encode()),"records":len(listed),
                "complete_wire_bytes":len(wire),"wire_sha256":hashlib.sha256(wire).hexdigest(),
                "payload_semantics_match_prepared_admission":True,"admission":outcome,
                "real_provider_calls":0,"SQL_engine_calls":0})

    def test_exact_cap_and_cap_plus_one_before_all_side_effects(self):
        import hashlib
        from services.my_data_extraction_adapter import MyDataExtractionAdapter,EXTRACTION_RESPONSE_SCHEMA
        adapter=MyDataExtractionAdapter()
        # Member text and the complete raw96k shortlist stay inside ingress limits;
        # backslash escaping in one bounded canonical summary reaches exact wire cap.
        listed=_bounded_shortlist("A")
        row=listed[0]
        text="\u754c"*20000
        req=adapter.build_request(text,shortlist=listed)
        base=len(_actual_provider_wire(req));extra=229376-base
        if extra%2:
            text="A"+text[1:]
            req=adapter.build_request(text,shortlist=listed)
            extra=229376-len(_actual_provider_wire(req))
        self.assertGreater(extra,0);self.assertEqual(extra%2,0)
        count=extra//2
        self.assertLess(2*count,len(row["values"]["summary"]))
        row["values"]["summary"]="\\"*count+row["values"]["summary"][2*count:]
        req=adapter.build_request(text,shortlist=listed)
        self.assertEqual(len(_actual_provider_wire(req)),229376)
        spies=_AdmissionSpies();provider=self.provider(spies)
        with provider.owner_scope("member"),self.assertRaises(_BeforeDispatch):
            provider(req,response_schema=EXTRACTION_RESPONSE_SCHEMA,maximum_output_tokens=128000)
        self.assertEqual((spies.reservations,spies.credentials,spies.transports),(1,0,0))
        # Remove one ASCII tail per substituted slash to preserve the raw96k bound.
        # Its outer escaping changes by4-3=1 while the raw shortlist shrinks1byte.
        row["values"]["summary"]="\\"+row["values"]["summary"][:-3]
        req_over=adapter.build_request(text,shortlist=listed)
        self.assertEqual(len(_actual_provider_wire(req_over)),229377)
        spies=_AdmissionSpies();provider=self.provider(spies)
        with provider.owner_scope("member"),self.assertRaises(ProviderUnavailableError):
            provider(req_over,response_schema=EXTRACTION_RESPONSE_SCHEMA,maximum_output_tokens=128000)
        self.assertEqual((spies.reservations,spies.credentials,spies.transports),(0,0,0))
        FROZEN_WIRE_RESULTS.append({"case":"exact_cap_plus_one","accepted_wire_bytes":229376,
            "refused_wire_bytes":229377,"refused_wire_sha256":hashlib.sha256(_actual_provider_wire(req_over)).hexdigest(),
            "cap_plus_one_side_effects":{"SQL_reservation_attempts":0,"credential_attempts":0,"transport_attempts":0},
            "reservation_micro_usd":provider.reservation,"six_call_total_micro_usd":provider.reservation*6})
        self.assertEqual(provider.reservation,998400);self.assertEqual(provider.reservation*6,5990400)

    def test_overflow_preserves_accepted_service_manual_proposal_and_source(self):
        import importlib.util,sys
        from services.my_data_extraction_adapter import MyDataExtractionAdapter
        from services.resume_draft_repository import InMemoryCanonicalCatalog,InMemoryResumeDraftRepository
        from services.resume_draft_service import ResumeDraftService
        from services.resume_intake_repository import InMemoryResumeIntakeRepository
        from services.resume_intake_policy import SELECTED_RESUME_ONBOARDING_POLICY
        spec=importlib.util.spec_from_file_location("services.frozen_wire_intake_service",_frozen_candidate()/"services/resume_intake_service.py")
        module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
        listed=_bounded_shortlist("\U0001f642")
        class Catalog(InMemoryCanonicalCatalog):
            def list_items(self,owner):return [{**row,"content_token":"a"*64,"access_revision":1,"editable":True,"private_assistance_excluded":False} for row in listed]
        catalog=Catalog();spies=_AdmissionSpies();provider=self.provider(spies)
        service=module.ResumeIntakeService(repository=InMemoryResumeIntakeRepository(),
            draft_service=ResumeDraftService(repository=InMemoryResumeDraftRepository(),catalog=catalog),
            policy=SELECTED_RESUME_ONBOARDING_POLICY,matching_exclusions=lambda owner:set(),
            extraction_adapter=MyDataExtractionAdapter(provider=provider))
        text="\u754c"*20000
        with provider.owner_scope("member"):
            result=service.submit("member",{"type":"add_submission","request_id":str(uuid4()),"text":text},files={})
        row=result["results"][0]
        self.assertEqual(row["provider_issue"]["code"],"provider_unavailable")
        self.assertFalse(row["saved"])
        snapshot=service._load("member")
        self.assertEqual(next(iter(snapshot["sources"].values()))["text"],text)
        proposals=list(snapshot["proposals"].values())
        self.assertTrue(proposals)
        self.assertEqual(proposals[0]["proposed_values"]["text"],text)
        self.assertEqual((spies.reservations,spies.credentials,spies.transports),(0,0,0))
        FROZEN_WIRE_RESULTS.append({"case":"manual_preservation","accepted_final_service_source":True,
            "source_text_preserved_utf16_units":20000,"uncertain_manual_proposal_text_preserved":True,
            "canonical_saved":False,"provider_issue":"provider_unavailable","actual_provider_calls":0,
            "SQL_engine_calls":0})


# Selected model/private assistance integration regressions; fixtures only.
import copy
import json
import time
import unittest
from uuid import uuid4

from services.resume_intake_runtime import (
    BoundedPrivateResumeProvider, BoundedResumeExtractionProvider,
    PrivateResumeAssistanceService, SynthesisError, SYNTHESIS_SCHEMA, PROMPT,
    build_private_resume_assistance, load_owner_context,
)
from services.ai_foundation.errors import ProviderUnavailableError
from services.my_data_extraction_adapter import MyDataExtractionAdapter, EXTRACTION_RESPONSE_SCHEMA
from services.resume_draft_repository import InMemoryCanonicalCatalog, InMemoryResumeDraftRepository
from services.resume_draft_service import ResumeDraftService
from itsdangerous import URLSafeTimedSerializer

PRIVATE_KEY = '07078187-e956-43e3-9d3e-a22b260788d1'
PRIVATE_OTHER = '163429f8-dd55-4415-9f68-e4653af47a88'


def selected_private_settings(profile='synthesis'):
    return {'endpoint': 'https://fixture.openai.azure.com',
        'deployment': 'peerslate-resume-sol61' if profile == 'synthesis' else 'eval0930-gpt-6-sol',
        'provider': {'maximum_input_bytes': 65536, 'maximum_input_tokens': 66560,
                     'maximum_output_tokens': 16384 if profile == 'synthesis' else 32768},
        'prices': {'input_micro_usd_per_million': 100000000 if profile == 'synthesis' else 5000000,
                   'output_micro_usd_per_million': 100000000 if profile == 'synthesis' else 15000000,
                   'schedule_ref': 'explicit-fiction-operator-safety'},
        'budget': {'scope': 'fiction-' + profile + '-selected-v1', 'maximum_calls': 6,
                   'hard_cap_micro_usd': 50000000 if profile == 'synthesis' else 5000000,
                   'concurrent_requests': 1}}


class SelectedPrivateReservations:
    def __init__(self):
        self.events, self.active, self.requests = [], set(), set()

    def first_row(self, procedure, parameters):
        self.events.append(procedure)
        p = dict(parameters)
        key = (p['@Scope'], p['@RequestId'])
        if procedure == 'usp_ReserveResumeHostedExtractionForOwner':
            if key in self.requests or p['@Scope'] in self.active:
                return {'reserved': False}
            self.requests.add(key)
            self.active.add(p['@Scope'])
            return {'reserved': True}
        self.active.remove(p['@Scope'])
        return {'finished': True}


class SelectedPrivateTransport:
    def __init__(self, payload=None, fail=False):
        self.payload, self.fail, self.calls = payload or {'candidates': []}, fail, []

    def post(self, url, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise TimeoutError('fiction timeout')
        payload = self.payload
        model = kwargs['json']['model']
        class Response:
            status_code = 200
            def json(self):
                return {'model': model, 'status': 'completed', 'usage': {'input_tokens': 4, 'output_tokens': 4},
                    'output': [{'type': 'message', 'content': [{'type': 'output_text',
                    'text': json.dumps(payload)}]}]}
        return Response()


class Ports:
    def __init__(self):
        self.catalog = [{
            'record_key': PRIVATE_KEY, 'record_type': 'role', 'content_token': '1',
            'access_revision': 1, 'content_version': 1, 'editable': True,
            'values': {'summary': 'Built private tools'},
        }]
        self.policy = [{'entry_key': PRIVATE_KEY, 'lifecycle': 'active', 'parent_key': None,
            'private_assistance_excluded': False, 'content_version': 1, 'access_revision': 1}]
        self.version, self.saved, self.reads = 7, [], []

    def get_workspace(self, owner):
        self.reads.append(owner)
        return {'draft_version': self.version, 'capabilities': {'canonical_read': 'ok'},
                'items': copy.deepcopy(self.catalog)}

    def list_items(self, owner):
        self.reads.append(owner)
        return copy.deepcopy(self.catalog)

    def list_entries(self, owner):
        self.reads.append(owner)
        return copy.deepcopy(self.policy)

    def commit(self, owner, command):
        self.saved.append((owner, command))
        return {'publishes': False, 'workspace': self.get_workspace(owner)}


LIMITS = {'maximum_task_bytes': 20000, 'maximum_input_bytes': 65536,
    'maximum_output_bytes': 100000, 'maximum_field_bytes': 8000, 'proof_max_age_seconds': 900}




class SelectedPrivateTests(unittest.TestCase):
    def test_selected_luna_safety_rates_are_integer_and_cannot_be_lowered(self):
        value = selected_private_settings('interview')
        value['deployment'] = 'gpt-6-luna'
        value['provider'] = {'maximum_input_bytes': 229376, 'maximum_input_tokens': 230400,
                             'maximum_output_tokens': 128000}
        value['budget'].update(scope='fiction-luna-rates-v1', hard_cap_micro_usd=6000000)
        for rate in (True, 1, 999999, 1000000.0):
            value['prices'].update(input_micro_usd_per_million=rate, output_micro_usd_per_million=6000000)
            db = SelectedPrivateReservations()
            with self.subTest(rate=rate), self.assertRaises(ValueError):
                BoundedResumeExtractionProvider(settings=value, database=db,
                    token_provider=lambda: self.fail('credential'))
            self.assertEqual(db.events, [])

    def test_inconsistent_workspace_and_owner_catalog_refuses_before_provider(self):
        ports = Ports()
        original = ports.get_workspace
        def old_workspace(owner):
            workspace = original(owner)
            workspace['items'][0]['content_token'] = 'stale-token'
            return workspace
        ports.get_workspace = old_workspace
        dispatched = []
        with self.assertRaises(SynthesisError) as error:
            self.service(ports, lambda **kwargs: dispatched.append(kwargs)).generate('fiction-owner', self.command())
        self.assertEqual(error.exception.code, 'changed')
        self.assertEqual(dispatched, [])

    def test_native_low_extraction_complete_schema_default_tier_and_timeout(self):
        value = selected_private_settings('interview')
        value['deployment'] = 'gpt-6-luna'
        value['provider'] = {'maximum_input_bytes': 229376, 'maximum_input_tokens': 230400,
                             'maximum_output_tokens': 128000}
        value['prices'].update(input_micro_usd_per_million=1000000, output_micro_usd_per_million=6000000)
        value['budget'].update(scope='fiction-luna-selected-v1', hard_cap_micro_usd=6000000)
        db, transport = SelectedPrivateReservations(), SelectedPrivateTransport()
        provider = BoundedResumeExtractionProvider(settings=value, database=db,
            token_provider=lambda: 'fiction-token', transport=transport)
        adapter = MyDataExtractionAdapter(provider=provider)
        with provider.owner_scope('fiction-owner'):
            adapter.extract('Built private tools', allowed_fields={})
        wire = transport.calls[0]['json']
        self.assertEqual(wire['model'], 'gpt-6-luna')
        self.assertEqual(wire['reasoning'], {'effort': 'low'})
        self.assertEqual(wire['service_tier'], 'default')
        self.assertEqual(wire['text']['format']['schema'], EXTRACTION_RESPONSE_SCHEMA)
        self.assertEqual(transport.calls[0]['timeout'], (5.0, 180.0))
        self.assertEqual(provider.reservation, 998400)

    def test_private_selected_alias_effort_schema_and_reservation(self):
        for profile, cost, model, effort in [('synthesis', 8294400, 'peerslate-resume-sol61', 'high'),
                                             ('interview', 824320, 'eval0930-gpt-6-sol', 'low')]:
            db, transport = SelectedPrivateReservations(), SelectedPrivateTransport()
            provider = BoundedPrivateResumeProvider(profile, settings=selected_private_settings(profile), database=db,
                token_provider=lambda: 'fiction-token', transport=transport)
            self.assertEqual(db.events, [])
            provider(owner='fiction-owner', request_id=str(uuid4()), instructions='Only verified facts.',
                     task='Help', context={}, response_schema=SYNTHESIS_SCHEMA)
            wire = transport.calls[0]['json']
            self.assertEqual(provider.reservation, cost)
            self.assertEqual(wire['model'], model)
            self.assertEqual(wire['reasoning'], {'effort': effort})
            self.assertEqual(wire['service_tier'], 'default')
            self.assertEqual(transport.calls[0]['timeout'], (5.0, 180.0))
            self.assertFalse(db.active)

    def test_uncertain_new_provider_new_request_cannot_dispatch(self):
        db, failed = SelectedPrivateReservations(), SelectedPrivateTransport(fail=True)
        def provider(transport):
            return BoundedPrivateResumeProvider('synthesis', settings=selected_private_settings(), database=db,
                token_provider=lambda: 'fiction-token', transport=transport)
        args = dict(owner='fiction-owner', request_id=str(uuid4()), instructions='Facts', task='Help',
                    context={}, response_schema=SYNTHESIS_SCHEMA)
        with self.assertRaises(ProviderUnavailableError):
            provider(failed)(**args)
        fresh = SelectedPrivateTransport()
        args['request_id'] = str(uuid4())
        with self.assertRaises(ProviderUnavailableError):
            provider(fresh)(**args)
        self.assertEqual(len(failed.calls), 1)
        self.assertEqual(fresh.calls, [])
        self.assertEqual(db.active, {'fiction-synthesis-selected-v1'})

    def test_complete_wire_cap_refuses_before_reserve_and_credentials(self):
        db, transport, tokens = SelectedPrivateReservations(), SelectedPrivateTransport(), []
        provider = BoundedPrivateResumeProvider('synthesis', settings=selected_private_settings(), database=db,
            token_provider=lambda: tokens.append(True), transport=transport)
        with self.assertRaises(SynthesisError) as error:
            provider(owner='fiction-owner', request_id=str(uuid4()), instructions=PROMPT,
                task='Help', context={'text': '\\' * 40000}, response_schema=SYNTHESIS_SCHEMA)
        self.assertEqual(error.exception.code, 'input_too_large')
        self.assertEqual((db.events, tokens, transport.calls), ([], [], []))

    def test_model_config_drift_and_low_sol_rates_refuse_without_io(self):
        for field, bad in [('deployment', 'invented-sol'), ('prices', {
                'input_micro_usd_per_million': 1000000, 'output_micro_usd_per_million': 6000000,
                'schedule_ref': 'wrong-luna-price'})]:
            value = selected_private_settings('interview')
            value[field] = bad
            db = SelectedPrivateReservations()
            with self.assertRaises(ValueError):
                BoundedPrivateResumeProvider('interview', settings=value, database=db,
                                            token_provider=lambda: self.fail('credential'))
            self.assertEqual(db.events, [])

    def service(self, ports, provider):
        return PrivateResumeAssistanceService(draft_service=ports, catalog=ports,
            policy_repository=ports, providers={'synthesis': provider, 'interview': provider},
            signer=URLSafeTimedSerializer('fiction-key-only-' * 4, salt='fixture'), limits=LIMITS)

    def command(self):
        return {'request_id': str(uuid4()), 'expected_draft_version': 7, 'task': 'Improve this summary',
                'selected_targets': [{'record_key': PRIVATE_KEY, 'field': 'summary'}]}

    def proposal(self):
        return {'resume_text': 'Built private tools', 'claims': [
            {'text': 'Built private tools', 'source_id': PRIVATE_KEY, 'quote': 'Built private tools'}],
            'uncertainties': [], 'confirmation_required': True}

    def test_proposal_no_save_owner_private_and_confirmation_full_values(self):
        ports = Ports()
        ports.catalog[0]['values']['location_text'] = 'Member manual location'
        service = self.service(ports, lambda **kwargs: self.proposal())
        proposal = service.generate('fiction-owner-a', self.command())
        self.assertEqual(ports.saved, [])
        payload = {'proof': proposal['proof'], 'record_key': PRIVATE_KEY, 'field': 'summary',
                   'confirmed_text': 'My reviewed wording', 'confirm': True}
        with self.assertRaises(SynthesisError):
            service.confirm('fiction-owner-b', payload)
        result = service.confirm('fiction-owner-a', payload)
        self.assertFalse(result['publishes'])
        self.assertEqual(ports.saved[0][1]['values']['location_text'], 'Member manual location')
        self.assertEqual(ports.saved[0][1]['values']['summary'], 'My reviewed wording')
        self.assertEqual(ports.saved[0][1]['expected_access_revision'], 1)

    def test_source_changes_during_provider_refuse_release(self):
        ports = Ports()
        def provider(**kwargs):
            ports.policy[0]['private_assistance_excluded'] = True
            return self.proposal()
        with self.assertRaises(SynthesisError):
            self.service(ports, provider).generate('fiction-owner', self.command())
        self.assertEqual(ports.saved, [])

    def test_signed_preview_stale_draft_refuses_confirmation(self):
        ports = Ports()
        service = self.service(ports, lambda **kwargs: self.proposal())
        proposal = service.generate('fiction-owner', self.command())
        ports.version += 1
        with self.assertRaises(SynthesisError):
            service.confirm('fiction-owner', {'proof': proposal['proof'], 'record_key': PRIVATE_KEY,
                'field': 'summary', 'confirmed_text': 'Reviewed', 'confirm': True})
        self.assertEqual(ports.saved, [])

    def test_literal_claim_and_single_original_value_binding(self):
        ports = Ports()
        result = self.proposal()
        result['claims'][0]['text'] = 'I built tools'
        with self.assertRaises(SynthesisError):
            self.service(ports, lambda **kwargs: result).generate('fiction-owner', self.command())

    def test_actual_parent_policy_omitted_catalog_restored_and_exclusion_refuses(self):
        ports = Ports()
        ports.catalog.append({**copy.deepcopy(ports.catalog[0]), 'record_key': PRIVATE_OTHER,
            'record_type': 'accomplishment', 'values': {'wording': 'ETL pilot'}})
        ports.policy.append({**copy.deepcopy(ports.policy[0]), 'entry_key': PRIVATE_OTHER, 'parent_key': PRIVATE_KEY})
        context = load_owner_context('fiction-owner', [], draft_service=ports, catalog=ports,
                                    policy_repository=ports, maximum_input_bytes=65536)
        self.assertEqual(next(s['parent_key'] for s in context['sources'] if s['source_id'] == PRIVATE_OTHER), PRIVATE_KEY)
        ports.policy[0]['private_assistance_excluded'] = True
        with self.assertRaises(SynthesisError):
            load_owner_context('fiction-owner', [], draft_service=ports, catalog=ports,
                               policy_repository=ports, maximum_input_bytes=65536)

    def test_empty_new_member_can_interview_no_automatic_fact_save(self):
        ports = Ports()
        ports.catalog, ports.policy = [], []
        def provider(**kwargs):
            self.assertEqual(kwargs['context']['sources'], [])
            return {'response': 'Tell me about the result.', 'next_question': 'What changed?', 'candidates': []}
        result = self.service(ports, provider).interview('fiction-owner', {
            'request_id': str(uuid4()), 'expected_draft_version': 7, 'statement': 'I built a pilot.'})
        self.assertEqual(ports.saved, [])
        self.assertFalse(result['saved'])

    def test_correction_uses_server_suggestion_source_and_new_words_without_saving(self):
        ports=Ports()
        suggestion={'proposal_key':str(uuid4()),'record_type':'role','target_key':PRIVATE_KEY,
            'proposed_values':{'role_title':'Designer','employer_name':'Fictional Studio'},
            'quote':'I was a Designer at Fictional Studio in 2022.'}
        statement='The start year was 2021.'
        def provider(**kwargs):
            self.assertEqual(kwargs['context']['review_suggestion'],suggestion)
            self.assertEqual(kwargs['context']['review_material'],suggestion['quote']+'\n\n'+statement)
            self.assertIn('Return only changed fields',kwargs['instructions'])
            return {'response':'I proposed the start year.','next_question':'','candidates':[{
                'record_type':'role','outcome':'new','match_reference':None,'confidence':'certain',
                'values':{'start_date':'2021-01-01','date_precision':'year'},'quote':statement}]}
        result=self.service(ports,provider).interview('fiction-owner',{
            'request_id':str(uuid4()),'expected_draft_version':7,'statement':statement},review_proposal=suggestion)
        self.assertEqual(result['candidates'][0]['values']['date_precision'],'year')
        self.assertEqual(ports.saved,[]);self.assertFalse(result['saved']);self.assertFalse(result['publishes'])

    def test_correction_refuses_context_change_during_provider_response(self):
        ports=Ports()
        def provider(**kwargs):
            ports.catalog[0]['values']['summary']='Concurrent member edit'
            return {'response':'A proposal','next_question':'','candidates':[]}
        with self.assertRaises(SynthesisError) as caught:
            self.service(ports,provider).interview('fiction-owner',{'request_id':str(uuid4()),
                'expected_draft_version':7,'statement':'Change the wording.'},review_proposal={
                'proposal_key':str(uuid4()),'record_type':'role','quote':'Original source.'})
        self.assertEqual(caught.exception.code,'changed');self.assertEqual(ports.saved,[])

    def test_factory_distinct_immutable_scopes_and_no_io(self):
        ports, db = Ports(), SelectedPrivateReservations()
        config = {'RESUME_PRIVATE_ASSISTANCE_CONFIGURATION': {
            'profiles': {'synthesis': selected_private_settings(), 'interview': selected_private_settings('interview')}, 'limits': LIMITS}}
        result = build_private_resume_assistance(config, draft_service=ports, catalog=ports,
            policy_repository=ports, database=db, token_provider=lambda: self.fail('credential'),
            signer=URLSafeTimedSerializer('fiction-key-only-' * 4))
        self.assertEqual(db.events, [])
        self.assertEqual(set(result.providers), {'synthesis', 'interview'})
        config['RESUME_PRIVATE_ASSISTANCE_CONFIGURATION']['profiles']['interview']['budget']['scope'] = selected_private_settings()['budget']['scope']
        with self.assertRaises(ValueError):
            build_private_resume_assistance(config, draft_service=ports, catalog=ports,
                policy_repository=ports, database=db, signer=URLSafeTimedSerializer('fiction-key-only-' * 4))

    def test_existing_draft_overlay_preserves_manual_and_canonical_fields(self):
        from tests.test_resume_draft_service import role_values
        catalog = InMemoryCanonicalCatalog()
        catalog.put_item('fiction-owner', {
            'record_key': PRIVATE_KEY, 'record_type': 'role', 'content_token': '1',
            'content_version': 1, 'access_revision': 1, 'editable': False,
            'save_mode': 'draft_overlay', 'values': role_values(location_text='Original location'),
            'resume_display': True, 'visitor_ai': True, 'private_assistance_excluded': False,
        })
        draft = ResumeDraftService(repository=InMemoryResumeDraftRepository(), catalog=catalog)
        draft.commit('fiction-owner', {'type': 'save_item', 'request_id': str(uuid4()),
            'record_key': PRIVATE_KEY, 'record_type': 'role', 'values': {'location_text': 'Manual overlay location'},
            'expected_draft_version': 0, 'expected_content_token': '1', 'expected_access_revision': 1})
        ports = Ports()
        service = PrivateResumeAssistanceService(draft_service=draft, catalog=catalog,
            policy_repository=ports, providers={'synthesis': lambda **kwargs: self.proposal()},
            signer=URLSafeTimedSerializer('fiction-key-only-' * 4), limits=LIMITS)
        command = self.command()
        command['expected_draft_version'] = draft.get_workspace('fiction-owner')['draft_version']
        result = service.generate('fiction-owner', command)
        saved = service.confirm('fiction-owner', {'proof': result['proof'], 'record_key': PRIVATE_KEY,
            'field': 'summary', 'confirmed_text': 'Reviewed wording', 'confirm': True})
        values = saved['workspace']['items'][0]['proposed_values']
        self.assertEqual(values['location_text'], 'Manual overlay location')
        self.assertEqual(values['employer_name'], 'PeerSlate')
        self.assertEqual(values['role_title'], 'Engineer')
        self.assertEqual(values['summary'], 'Reviewed wording')
        self.assertFalse(saved['publishes'])
        canonical = catalog.get_item('fiction-owner', PRIVATE_KEY)
        self.assertTrue(canonical['resume_display'])
        self.assertEqual(canonical['values']['summary'], 'Built private tools')


# Compact fictional output captured from the root-owned native diagnostic.
# No provider response envelopes, encrypted reasoning, request IDs or credentials.
CAPTURED_CURRENT_ROLE_FIXTURE = {'proposal': {'resume_text': 'PRIVATE R\xc9SUM\xc9 PROPOSAL\n\nINDEPENDENT PROJECTS OR CONTRIBUTIONS\nETL pilot\nBuilt an experimental ETL pilot using Python and SQL for a fictional community dataset. No production rollout, revenue or performance improvement is established.\n\nPROFESSIONAL EXPERIENCE\nTechnical Lead\nFictional Example Harbor Systems\n2023\u2013Present\nCoordinated a three-person documentation review. No measured efficiency result is established.\n\nREVIEW REQUIRED\nThis is a private proposal only. Nothing has been saved, accepted, sent or published. Review and explicitly save selected wording.', 'claims': [{'text': 'ETL pilot', 'source_id': '540dfb6a-d53b-471d-94b1-bea2b171ec7e', 'quote': 'ETL pilot'}, {'text': 'Built an experimental ETL pilot using Python and SQL for a fictional community dataset. No production rollout, revenue or performance improvement is established.', 'source_id': '540dfb6a-d53b-471d-94b1-bea2b171ec7e', 'quote': 'Built an experimental ETL pilot using Python and SQL for a fictional community dataset. No production rollout, revenue or performance improvement is established.'}, {'text': 'Technical Lead', 'source_id': '830cef7c-c3e4-4d01-b472-86bd67607666', 'quote': 'Technical Lead'}, {'text': 'Fictional Example Harbor Systems', 'source_id': '830cef7c-c3e4-4d01-b472-86bd67607666', 'quote': 'Fictional Example Harbor Systems'}, {'text': '2023', 'source_id': '830cef7c-c3e4-4d01-b472-86bd67607666', 'quote': '2023-01-01'}, {'text': 'Present', 'source_id': '830cef7c-c3e4-4d01-b472-86bd67607666', 'quote': 'true'}, {'text': 'Coordinated a three-person documentation review. No measured efficiency result is established.', 'source_id': '830cef7c-c3e4-4d01-b472-86bd67607666', 'quote': 'Coordinated a three-person documentation review. No measured efficiency result is established.'}], 'uncertainties': ['No production rollout, revenue or performance improvement is established.', 'No measured efficiency result is established.'], 'confirmation_required': True}, 'catalog': [{'record_key': '830cef7c-c3e4-4d01-b472-86bd67607666', 'record_type': 'role', 'content_token': '0000000000000001', 'access_revision': 1, 'content_version': 1, 'editable': True, 'values': {'current_role': True, 'date_precision': 'year', 'employer_name': 'Fictional Example Harbor Systems', 'employment_type': None, 'end_date': None, 'location_text': None, 'role_title': 'Technical Lead', 'start_date': '2023-01-01', 'summary': 'Coordinated a three-person documentation review. No measured efficiency result is established.'}}, {'record_key': '540dfb6a-d53b-471d-94b1-bea2b171ec7e', 'record_type': 'knowledge', 'content_token': '0000000000000001', 'access_revision': 1, 'content_version': 1, 'editable': True, 'values': {'classification': 'personal', 'title': 'ETL pilot', 'wording': 'Built an experimental ETL pilot using Python and SQL for a fictional community dataset. No production rollout, revenue or performance improvement is established.'}}]}

class TypedCurrentRoleEvidenceTests(unittest.TestCase):
    def fixture(self):
        ports = Ports()
        ports.catalog = copy.deepcopy(CAPTURED_CURRENT_ROLE_FIXTURE['catalog'])
        ports.policy = [{'entry_key':row['record_key'], 'lifecycle':'active', 'parent_key':None,
            'private_assistance_excluded':False, 'content_version':1, 'access_revision':1}
            for row in ports.catalog]
        role = next(row for row in ports.catalog if row['record_type']=='role')
        command = {'request_id':str(uuid4()), 'expected_draft_version':ports.version,
            'task':'Prepare a concise private proposal.',
            'selected_targets':[{'record_key':role['record_key'],'field':'summary'}]}
        service = PrivateResumeAssistanceService(draft_service=ports,catalog=ports,
            policy_repository=ports,providers={'synthesis':lambda **kwargs:copy.deepcopy(CAPTURED_CURRENT_ROLE_FIXTURE['proposal'])},
            signer=URLSafeTimedSerializer('fiction-current-role-'*4,salt='fixture'),limits=LIMITS)
        return ports,role,command,service

    def test_captured_native_typed_currentness_preserves_original_year_parent_and_manual_values(self):
        ports,role,command,service=self.fixture()
        before=copy.deepcopy(ports.catalog)
        result=service.generate('fiction-owner',command)
        self.assertEqual(result['proposal'],CAPTURED_CURRENT_ROLE_FIXTURE['proposal'])
        self.assertEqual(ports.catalog,before)
        self.assertEqual(ports.saved,[])
        self.assertFalse(result['saved'])
        self.assertFalse(result['publishes'])
        self.assertEqual(role['values']['start_date'],'2023-01-01')
        self.assertEqual(role['values']['date_precision'],'year')
        self.assertIn('2023\u2013Present',result['proposal']['resume_text'])
        self.assertNotIn('2023-01-01',result['proposal']['resume_text'])
        project=next(row for row in ports.catalog if row['record_type']=='knowledge')
        self.assertIsNone(next(row for row in result['source_bindings'] if row['source_id']==project['record_key'])['parent_key'])
        self.assertIn(project['values']['wording'],result['proposal']['resume_text'])
        self.assertLess(result['proposal']['resume_text'].index('ETL pilot'),result['proposal']['resume_text'].index('PROFESSIONAL EXPERIENCE'))
        self.assertGreaterEqual(len(ports.reads),6)  # Owner context loaded and reread before release.

    def test_currentness_rejects_falsy_string_other_record_other_field_and_forged_quotes(self):
        from services.resume_intake_runtime import validate_proposal
        cases=[('false',False,'role','true','Present'),('string','true','role','true','Present'),
            ('numeric',1,'role','true','Present'),('other_record',True,'knowledge','true','Present'),
            ('wrong_case',True,'role','True','Present'),('metadata_quote',True,'role','current_role:true','Present'),
            ('wrong_truth',True,'role','false','Not current'),('spaced_quote',True,'role',' true ','Present')]
        for name,current,kind,quote,wording in cases:
            with self.subTest(case=name):
                ports,role,command,service=self.fixture()
                role['values']['current_role']=current
                role['record_type']=kind
                role['values']['other_flag']=True
                context=load_owner_context('fiction-owner',[],draft_service=ports,catalog=ports,
                    policy_repository=ports,maximum_input_bytes=65536)
                output={'resume_text':wording,'claims':[{'text':wording,'source_id':role['record_key'],'quote':quote}],
                    'uncertainties':[],'confirmation_required':True}
                context['protected_manual_text']=[]
                with self.assertRaises(SynthesisError) as caught:validate_proposal(output,context,maximum_output_bytes=100000)
                self.assertEqual(caught.exception.code,'unsupported_source_binding')
        context={'sources':[{'source_id':PRIVATE_KEY,'record_type':'role','values':{'other_flag':True,'summary':'true'}}], 'protected_manual_text':[]}
        output={'resume_text':'Present','claims':[{'text':'Present','source_id':PRIVATE_KEY,'quote':'true'}],'uncertainties':[],'confirmation_required':True}
        with self.assertRaises(SynthesisError):validate_proposal(output,context,maximum_output_bytes=100000)

    def test_false_currentness_has_only_explicit_not_current_semantics(self):
        from services.resume_intake_runtime import validate_proposal
        context={'sources':[{'source_id':PRIVATE_KEY,'record_type':'role','values':{'current_role':False}}], 'protected_manual_text':[]}
        output={'resume_text':'Not current','claims':[{'text':'Not current','source_id':PRIVATE_KEY,'quote':'false'}],'uncertainties':[],'confirmation_required':True}
        self.assertEqual(validate_proposal(output,context,maximum_output_bytes=100000),output)
        output['claims'][0]['text']='Present';output['resume_text']='Present'
        with self.assertRaises(SynthesisError):validate_proposal(output,context,maximum_output_bytes=100000)

    def test_current_role_change_during_dispatch_still_refuses_release_and_stale_confirmation(self):
        ports,role,command,service=self.fixture()
        def provider(**kwargs):
            role['values']['current_role']=False
            return copy.deepcopy(CAPTURED_CURRENT_ROLE_FIXTURE['proposal'])
        service.providers['synthesis']=provider
        with self.assertRaises(SynthesisError) as caught:service.generate('fiction-owner',command)
        self.assertEqual(caught.exception.code,'changed')
        self.assertEqual(ports.saved,[])
        ports,role,command,service=self.fixture()
        result=service.generate('fiction-owner',command)
        role['values']['current_role']=False
        with self.assertRaises(SynthesisError):service.confirm('fiction-owner',{'proof':result['proof'],'record_key':role['record_key'],
            'field':'summary','confirm':True,'confirmed_text':'Reviewed wording'})
        self.assertEqual(ports.saved,[])



# Trusted ongoing-port application seam only. This in-memory spy is NOT a
# durable ledger/proof; the installer independently owns native staging,
# cross-process accounting and persistence tests.
class _OngoingPortSpy:
    def __init__(self):
        self.validations, self.events, self.results = [], [], []
        self.active, self.spent, self.reserved = False, 0, 0
        self.admitted, self.reserve_reply, self.settle_reply = True, None, None

    def validate_profile(self, *, profile, settings, reservation):
        self.validations.append((profile, copy.deepcopy(settings), reservation))
        return self.admitted

    def reserve(self, owner, request_id, settings, reservation):
        self.events.append(('reserve', owner, request_id, copy.deepcopy(settings), reservation))
        if self.active or self.spent + reservation > settings['hard_cap_micro_usd']:
            raise ProviderUnavailableError('fiction refusal')
        self.active, self.reserved = True, reservation
        return self.reserve_reply

    def settle_completed(self, owner, request_id, scope, result):
        self.events.append(('settle', owner, request_id, scope))
        self.results.append(result)
        if self.settle_reply is not None:
            return self.settle_reply
        profile, settings, _ = self.validations[-1]
        rates = settings['prices']
        self.spent += (result.input_tokens * rates['input_micro_usd_per_million']
                       + result.output_tokens * rates['output_micro_usd_per_million'] + 999999) // 1000000
        self.active = False


class OngoingBudgetPortTests(unittest.TestCase):
    def setUp(self):
        self.db, self.port = SelectedPrivateReservations(), _OngoingPortSpy()
        self.transport, self.tokens = SelectedPrivateTransport(), []

    def configured(self, profile):
        value = _qualification_settings() if profile == 'extraction' else selected_private_settings(profile)
        value['budget']['maximum_calls'] = 100
        value['budget']['scope'] = 'fiction-ongoing-' + profile + '-v1'
        return value

    def provider(self, profile='extraction', *, port=None, value=None):
        kwargs = dict(settings=value or self.configured(profile), database=self.db,
                      token_provider=self.token, transport=self.transport,
                      ongoing_budget_port=self.port if port is None else port)
        return (BoundedResumeExtractionProvider(**kwargs) if profile == 'extraction'
                else BoundedPrivateResumeProvider(profile, **kwargs))

    def token(self):
        self.assertTrue(self.port.active)
        self.tokens.append('after-committed-reserve')
        return 'offline-placeholder'

    def call(self, provider, *, req=None, task='fiction task'):
        if isinstance(provider, BoundedResumeExtractionProvider):
            with provider.owner_scope('server-owner'):
                return provider(req or request(), response_schema={'type': 'object'}, maximum_output_tokens=128000)
        return provider(owner='server-owner', request_id=str(uuid4()), instructions='Fiction only',
                        task=task, context={}, response_schema={'type': 'object'})

    def test_default_six_only_and_exact_opt_in_ceiling(self):
        for profile in ('extraction', 'synthesis', 'interview'):
            value = self.configured(profile)
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                kwargs = dict(settings=value, database=self.db)
                (BoundedResumeExtractionProvider(**kwargs) if profile == 'extraction'
                 else BoundedPrivateResumeProvider(profile, **kwargs))
            for ceiling in (6, 99, 101, True):
                changed = copy.deepcopy(value)
                changed['budget']['maximum_calls'] = ceiling
                with self.subTest(profile=profile, ceiling=ceiling), self.assertRaises(ValueError):
                    self.provider(profile, value=changed)
        self.assertEqual(self.port.validations, [])
        self.assertEqual(self.db.events, [])

    def test_constructor_closed_methods_and_explicit_true_only(self):
        for reply in (None, False, 1, 'true'):
            self.port.admitted = reply
            with self.subTest(reply=reply), self.assertRaises(ValueError):
                self.provider()
        with self.assertRaises(ValueError):
            self.provider(port=object())
        self.assertEqual(self.tokens, [])
        self.assertEqual(self.transport.calls, [])
        self.assertEqual(self.port.events, [])
        self.assertEqual(self.db.events, [])

    def test_full_profile_validation_is_copied_and_cannot_mutate_live_settings(self):
        value = self.configured('extraction')
        original = copy.deepcopy(value)
        original_validate = self.port.validate_profile
        def mutate(**kwargs):
            reply = original_validate(**kwargs)
            kwargs['settings']['budget']['scope'] = 'forged'
            kwargs['settings']['provider']['maximum_input_bytes'] = 1
            return reply
        self.port.validate_profile = mutate
        provider = self.provider(value=value)
        self.assertEqual(value, original)
        self.assertEqual(provider.budget, original['budget'])
        self.assertEqual(provider.bounds, original['provider'])
        self.assertEqual(self.port.validations[0], ('extraction', original, 998400))
        self.assertEqual(self.tokens, [])
        self.assertEqual(self.db.events, [])

    def test_seventh_small_completed_operation_and_cap_before_credentials_all_profiles(self):
        from services.ai_foundation.contracts import StructuredResult
        for profile in ('extraction', 'synthesis', 'interview'):
            self.setUp()
            provider = self.provider(profile)
            for _ in range(7):
                self.call(provider)
            self.assertEqual(len(self.transport.calls), 7)
            self.assertEqual(len(self.port.results), 7)
            self.assertTrue(all(isinstance(result, StructuredResult) for result in self.port.results))
            self.assertFalse(self.port.active)
            self.assertEqual(self.db.events, [])
            self.port.spent = provider.budget['hard_cap_micro_usd'] - provider.reservation + 1
            with self.assertRaises(ProviderUnavailableError):
                self.call(self.provider(profile))
            self.assertEqual(len(self.tokens), 7)
            self.assertEqual(len(self.transport.calls), 7)

    def test_server_owner_is_not_taken_from_extraction_request_subject(self):
        from dataclasses import replace
        req = replace(request(), subject_key='request-selected-owner')
        self.call(self.provider(), req=req)
        reserve, settle = self.port.events
        self.assertEqual(reserve[1:3], ('server-owner', req.request_id))
        self.assertEqual(settle[1:3], ('server-owner', req.request_id))
        self.assertEqual(reserve[3], self.configured('extraction')['budget'])
        self.assertEqual(reserve[4], 998400)
        self.assertEqual(self.db.events, [])

    def test_noncommitted_reserve_return_blocks_token_and_transport(self):
        for reply in (True, 0, {}, 'committed'):
            self.setUp()
            self.port.reserve_reply = reply
            with self.subTest(reply=reply), self.assertRaises(ProviderUnavailableError):
                self.call(self.provider())
            self.assertEqual(self.tokens, [])
            self.assertEqual(self.transport.calls, [])
            self.assertEqual(self.port.results, [])
            self.assertTrue(self.port.active)

    def test_timeout_no_settlement_and_new_request_provider_remain_fenced(self):
        self.transport.fail = True
        with self.assertRaises(ProviderUnavailableError):
            self.call(self.provider())
        self.assertTrue(self.port.active)
        self.assertEqual(self.port.results, [])
        self.assertEqual(self.port.spent, 0)
        self.assertEqual(self.port.reserved, 998400)
        with self.assertRaises(ProviderUnavailableError):
            self.call(self.provider())
        self.assertEqual(len(self.tokens), 1)
        self.assertEqual(len(self.transport.calls), 1)
        self.assertEqual(self.db.events, [])

    def test_codec_failure_after_completed_transport_does_not_settle(self):
        from unittest.mock import patch
        original = self.transport.post
        def malformed(*args, **kwargs):
            response = original(*args, **kwargs)
            completed = response.json()
            completed['output'][0]['content'][0]['text'] = '{invalid-json'
            response.json = lambda: completed
            return response
        provider = self.provider()
        with self.assertRaises(ProviderUnavailableError):
            with patch.object(self.transport, 'post', side_effect=malformed):
                self.call(provider)
        self.assertTrue(self.port.active)
        self.assertEqual(self.port.results, [])
        self.assertEqual(len(self.transport.calls), 1)

    def test_wrong_result_binding_and_strict_totals_never_reach_settlement(self):
        from unittest.mock import patch
        from services.ai_foundation.azure_foundry import AzureFoundryResponsesProvider
        from services.ai_foundation.contracts import StructuredResult
        fields = [('request_id', str(uuid4())), ('schema_name', 'wrong'), ('model_name', 'gpt-6-sol'),
                  ('deployment_name', 'wrong'), ('configured_model_version', 'wrong'),
                  ('input_tokens', True), ('input_tokens', -1), ('input_tokens', 0.5),
                  ('input_tokens', 230401), ('output_tokens', True), ('output_tokens', 128001)]
        for field, value in fields:
            self.setUp()
            provider, req = self.provider(), request()
            result = StructuredResult(request_id=req.request_id, schema_name=req.schema_name,
                model_name=req.model_name, payload={}, input_tokens=4, output_tokens=4,
                deployment_name=provider.arguments['deployment'],
                configured_model_version=provider.arguments['model_version'])
            object.__setattr__(result, field, value)
            with self.subTest(field=field, value=value), patch.object(
                    AzureFoundryResponsesProvider, 'respond', return_value=result), self.assertRaises(ProviderUnavailableError):
                self.call(provider, req=req)
            self.assertTrue(self.port.active)
            self.assertEqual(self.port.results, [])
        self.setUp()
        with patch.object(AzureFoundryResponsesProvider, 'respond', return_value={}), self.assertRaises(ProviderUnavailableError):
            self.call(self.provider())
        self.assertTrue(self.port.active)

    def test_uncertain_settlement_return_never_falls_back_to_sql_or_redispatch(self):
        self.port.settle_reply = True
        with self.assertRaises(ProviderUnavailableError):
            self.call(self.provider('interview'))
        self.assertTrue(self.port.active)
        self.assertEqual(len(self.port.results), 1)
        self.assertEqual(self.port.spent, 0)
        with self.assertRaises(ProviderUnavailableError):
            self.call(self.provider('interview'))
        self.assertEqual(len(self.transport.calls), 1)
        self.assertEqual(self.db.events, [])

    def test_whole_wire_overcap_precedes_reserve_token_and_transport(self):
        for profile in ('extraction', 'interview', 'synthesis'):
            self.setUp()
            provider = self.provider(profile)
            if profile == 'extraction':
                empty = request('x')
                from dataclasses import replace
                make_request = lambda text: replace(empty, input_text=text)
                req = empty
            else:
                selected = provider.selected
                def make_request(text):
                    return StructuredRequest(request_id=str(uuid4()), product='resume_private_assistance',
                        purpose=selected['purpose'], audience=Audience.OWNER, subject_key='server-owner',
                        instructions='Fiction only', input_text=json.dumps({'task': text, 'context': {}},
                            ensure_ascii=False, separators=(',', ':')), schema_name='resume_'+profile+'_v1',
                        reasoning_effort=selected['effort'], model_name=selected['model'])
                req = make_request('')
            def wire_size(value):
                from services.ai_foundation.azure_foundry import AzureFoundryResponsesProvider, SpendLedger
                foundation = AzureFoundryResponsesProvider(**provider.arguments,
                    spend_ledger=SpendLedger(hard_cap_micro_usd=provider.reservation, max_calls=1))
                wire = foundation.structured_payload(value, response_schema={'type': 'object'},
                    maximum_output_tokens=provider.bounds['maximum_output_tokens'])
                return len(json.dumps(wire, separators=(',', ':')).encode('utf-8'))
            task = 'x' * (provider.bounds['maximum_input_bytes'] + 1 - wire_size(req)
                          + (1 if profile == 'extraction' else 0))
            req = make_request(task)
            self.assertEqual(wire_size(req), provider.bounds['maximum_input_bytes'] + 1)
            with self.subTest(profile=profile), self.assertRaises((ProviderUnavailableError, SynthesisError)):
                self.call(provider, req=req, task=task)
            self.assertEqual(self.port.events, [])
            self.assertEqual(self.tokens, [])
            self.assertEqual(self.transport.calls, [])

    def test_actual_private_factory_forwards_one_server_port_to_both_profiles(self):
        fixture = Ports()
        service = build_private_resume_assistance(
            {'RESUME_PRIVATE_ASSISTANCE_CONFIGURATION': {'profiles': {
                p: self.configured(p) for p in ('synthesis', 'interview')}, 'limits': LIMITS}},
            draft_service=fixture, catalog=fixture, policy_repository=fixture,
            database=self.db, token_provider=self.token, transport=self.transport,
            signer=URLSafeTimedSerializer('offline-signing-fixture'), ongoing_budget_port=self.port)
        self.assertEqual(set(service.providers), {'synthesis', 'interview'})
        self.assertTrue(all(p.protections is self.port for p in service.providers.values()))
        self.assertEqual({p for p, _, _ in self.port.validations}, {'synthesis', 'interview'})
        self.assertEqual(self.port.events, [])
        self.assertEqual(self.tokens, [])
        self.assertEqual(self.db.events, [])
