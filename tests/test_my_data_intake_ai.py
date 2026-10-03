"""Contract tests for Luna Extra High intake extraction and matching.

Everything here runs against real service and adapter code with a
deterministic fake provider. The fake records its exact calls so tests prove
the model, effort, and strict schema the adapter demanded. Nothing here is
SQL engine proof, live provider proof, or live identity proof.
"""

from __future__ import annotations

import threading
import unittest
from contextlib import contextmanager
from uuid import uuid4

from services.ai_foundation.azure_foundry import (
    AzureFoundryResponsesProvider,
    SpendLedger,
)
from services.ai_foundation.contracts import (
    REASONING_EFFORT_XHIGH,
    Audience,
    ExtractionPurpose,
    StructuredRequest,
)
from services.ai_foundation.errors import ProviderUnavailableError
from services.my_data_extraction_adapter import (
    EXTRACTION_MODEL,
    EXTRACTION_OUTCOMES,
    EXTRACTION_RESPONSE_SCHEMA,
    EXTRACTION_SCHEMA_NAME,
    EXTRACTED_VALUE_PROPERTIES,
    EXTRACTION_VALUE_FIELDS,
    DeterministicFakeExtractionAdapter,
    ExtractionCandidate,
    ExtractionError,
    MyDataExtractionAdapter,
    validate_extraction_payload,
)
from services.resume_draft_repository import (
    InMemoryCanonicalCatalog,
    InMemoryResumeDraftRepository,
)
from services.resume_draft_service import ResumeDraftService, ResumeDraftUnavailableError
from services.resume_intake_policy import selected_policy_for_tests
from services.resume_intake_repository import InMemoryResumeIntakeRepository
from services.resume_intake_service import (
    ResumeIntakeConflictError,
    ResumeIntakeNotFoundError,
    ResumeIntakeService,
)


ROLE_VALUES = {
    "role_title": "Systems Engineer",
    "employer_name": "Northrop Grumman",
    "location_text": None,
    "summary": "Supports requirements management.",
    "start_date": "2025-01-01",
    "end_date": None,
    "date_precision": "month",
    "employment_type": "full_time",
    "current_role": True,
}


def build_service(
    *,
    repository=None,
    extraction_adapter=None,
    exclusions=None,
    document_pipeline=None,
    transcription_adapter=None,
):
    catalog = InMemoryCanonicalCatalog()
    draft_repository = InMemoryResumeDraftRepository()
    draft_service = ResumeDraftService(repository=draft_repository, catalog=catalog)
    return ResumeIntakeService(
        repository=repository or InMemoryResumeIntakeRepository(),
        draft_service=draft_service,
        policy=selected_policy_for_tests(),
        extraction_adapter=extraction_adapter,
        matching_exclusions=exclusions,
        document_pipeline=document_pipeline,
        transcription_adapter=transcription_adapter,
    )


def add_request(**kwargs):
    body = {"type": "add_submission", "request_id": str(uuid4())}
    body.update(kwargs)
    return body


def build_wired_service(*, extraction_adapter=None, exclusions=None):
    catalog = InMemoryCanonicalCatalog()
    draft_repository = InMemoryResumeDraftRepository()
    draft_service = ResumeDraftService(repository=draft_repository, catalog=catalog)
    service = ResumeIntakeService(
        repository=InMemoryResumeIntakeRepository(),
        draft_service=draft_service,
        policy=selected_policy_for_tests(),
        extraction_adapter=extraction_adapter,
        matching_exclusions=exclusions,
    )
    return service, catalog


class LooseExtractionAdapter:
    """Returns candidates without payload validation, for service fail-closed proofs."""

    def __init__(self, candidates):
        self.candidates = list(candidates)

    def extract(self, text, *, allowed_fields, shortlist, request_id=None):
        return list(self.candidates)


class PurgeWinsResumeIntakeRepository(InMemoryResumeIntakeRepository):
    """Pause the named keep thread before it enters the owner mutation guard."""

    def __init__(self):
        super().__init__()
        self.keep_waiting = threading.Event()
        self.release_keep = threading.Event()

    @contextmanager
    def owner_guard(self, owner_user_key):
        if threading.current_thread().name == "delayed-keep-separate":
            self.keep_waiting.set()
            if not self.release_keep.wait(timeout=5):
                raise AssertionError("Timed out waiting for purge to win.")
        with super().owner_guard(owner_user_key):
            yield


class ConversationSpanTests(unittest.TestCase):
    def extract(self, text, quote):
        return validate_extraction_payload({'candidates': [{
            'record_type': 'role', 'values': {'role_title': 'Systems Engineer'},
            'outcome': 'new', 'quote': quote}]}, text=text,
            allowed_fields={'role': frozenset({'role_title'})})

    def test_pdf_line_breaks_map_to_exact_original_unique_span(self):
        text = 'Career\nSystems\u00a0 Engineer\nHarbor Labs, 2021–2024\nEducation'
        row = self.extract(text, 'Systems Engineer Harbor Labs, 2021–2024')[0]
        self.assertEqual(row.quote, 'Systems\u00a0 Engineer\nHarbor Labs, 2021–2024')
        self.assertEqual(text[row.span_start:row.span_end], row.quote)

    def test_substantive_mismatch_and_two_layout_matches_still_refuse(self):
        for text, quote, code in [
                ('Systems Engineer', 'Systems Enginer', 'span_quote_mismatch'),
                ('Systems\nEngineer; Systems\tEngineer', 'Systems Engineer', 'ambiguous_quote')]:
            with self.subTest(code=code), self.assertRaises(ExtractionError) as error:
                self.extract(text, quote)
            self.assertEqual(error.exception.code, code)


class AdapterContractTests(unittest.TestCase):
    def test_outcome_vocabulary_is_closed(self):
        self.assertEqual(
            EXTRACTION_OUTCOMES,
            {"new", "equivalent", "additional_detail", "contradiction", "uncertain"},
        )

    def test_adapter_pins_model_effort_and_schema(self):
        adapter = DeterministicFakeExtractionAdapter()
        self.assertEqual(adapter.model, EXTRACTION_MODEL)
        self.assertEqual(adapter.model, "gpt-6-luna")
        self.assertEqual(adapter.reasoning_effort, "low")
        self.assertEqual(adapter.reasoning_effort, "low")
        self.assertEqual(adapter.schema_name, EXTRACTION_SCHEMA_NAME)

    def test_adapter_refuses_other_models_and_efforts(self):
        with self.assertRaises(ExtractionError):
            MyDataExtractionAdapter(provider=lambda *a, **k: {}, model="other-model")
        with self.assertRaises(ExtractionError):
            MyDataExtractionAdapter(provider=lambda *a, **k: {}, reasoning_effort="xhigh")

    def test_structured_request_refuses_unsupported_effort(self):
        with self.assertRaises(ValueError):
            StructuredRequest(
                request_id=str(uuid4()),
                product="my_data_intake",
                purpose=ExtractionPurpose.MY_DATA_INTAKE_EXTRACTION,
                audience=Audience.OWNER,
                subject_key="member",
                instructions="Extract.",
                input_text="Some material.",
                schema_name=EXTRACTION_SCHEMA_NAME,
                reasoning_effort="low",
            )

    def test_request_carries_closed_purpose_and_owner_audience(self):
        adapter = DeterministicFakeExtractionAdapter()
        request = adapter.build_request("I led the migration.")
        self.assertEqual(request.purpose, ExtractionPurpose.MY_DATA_INTAKE_EXTRACTION)
        self.assertEqual(request.audience, Audience.OWNER)
        self.assertEqual(request.reasoning_effort, "low")
        self.assertEqual(request.schema_name, EXTRACTION_SCHEMA_NAME)
        self.assertIn("I led the migration.", request.input_text)

    def test_empty_input_is_refused_before_any_call(self):
        adapter = DeterministicFakeExtractionAdapter()
        with self.assertRaises(ExtractionError):
            adapter.build_request("   ")
        self.assertEqual(adapter.calls, [])

    def test_explicit_medium_high_and_scoped_allowance_preserve_default(self):
        calls = []
        def provider(request, **kwargs):
            calls.append((request, kwargs))
            return {"candidates": []}
        for effort in ("xhigh", "medium", "high"):
            adapter = MyDataExtractionAdapter(provider, model="gpt-5.6-luna", reasoning_effort=effort)
            self.assertEqual(adapter.maximum_output_tokens, 128000)
            self.assertEqual(adapter.extract("Fictional material.", allowed_fields={}), [])
        self.assertEqual([row[0].reasoning_effort for row in calls], ["xhigh", "medium", "high"])
        self.assertEqual([row[1]["maximum_output_tokens"] for row in calls], [128000,128000,128000])
        for request, kwargs in calls[1:]:
            self.assertEqual(calls[0][0].instructions, request.instructions)
            self.assertEqual(calls[0][0].input_text, request.input_text)
            self.assertEqual(calls[0][1]["response_schema"], kwargs["response_schema"])
        self.assertEqual(MyDataExtractionAdapter().reasoning_effort, "low")

    def test_nondefault_matching_and_invalid_allowances_refuse_before_provider(self):
        calls = []
        for effort in ("medium", "high"):
            adapter = MyDataExtractionAdapter(lambda **kw: calls.append(kw), model="gpt-5.6-luna", reasoning_effort=effort)
            with self.subTest(effort=effort), self.assertRaises(ValueError):
                adapter.build_request("Material", purpose=ExtractionPurpose.MY_DATA_INTAKE_MATCHING)
        for value in (True,0,-1,128001,1.5,"128000"):
            with self.subTest(value=value), self.assertRaises(ExtractionError):
                MyDataExtractionAdapter(maximum_output_tokens=value)
        for effort in (None,True,[],{},"xhigh"):
            with self.subTest(effort=effort), self.assertRaises(ExtractionError):
                MyDataExtractionAdapter(reasoning_effort=effort)
        self.assertEqual(calls, [])

    def test_nondefault_effort_requires_owner_my_data_extraction(self):
        for effort in ("medium", "high"):
            for changes in ({"product": "unrelated"},
                            {"purpose": ExtractionPurpose.MY_DATA_INTAKE_MATCHING},
                            {"audience": Audience.PUBLIC},
                            {"audience": Audience.AUTHORIZED_RECRUITER}):
                options = dict(request_id="synthetic-scope", product="my_data_intake",
                               purpose=ExtractionPurpose.MY_DATA_INTAKE_EXTRACTION,
                               audience=Audience.OWNER, subject_key="synthetic:member",
                               instructions="Private proposal only.", input_text="Fictional material.",
                               schema_name=EXTRACTION_SCHEMA_NAME, reasoning_effort=effort)
                options.update(changes)
                with self.subTest(effort=effort, changes=changes), self.assertRaises(ValueError):
                    StructuredRequest(**options)

    def test_type_fields_are_exact_existing_canonical_editor_contract(self):
        from services.resume_intake_service import EDITOR_FIELDS
        self.assertEqual(set(EXTRACTION_VALUE_FIELDS), set(EDITOR_FIELDS) | {"unspecified"})
        for kind, fields in EDITOR_FIELDS.items():
            self.assertEqual(frozenset(EXTRACTION_VALUE_FIELDS[kind]), fields)
        self.assertEqual(EXTRACTION_VALUE_FIELDS["unspecified"], ("text",))

    def test_prompt_retains_grouping_unknown_precision_and_course_qualifiers(self):
        instructions = MyDataExtractionAdapter().build_request("Material").instructions
        for wording in ("Group each position", "classroom prototype", "internal pilot",
                        "not deployed", "not company-wide", "Missing dates remain null",
                        "otherwise null", "course completion certificate is education",
                        "unsupported", "code derives", "YYYY-01-01", "date_precision month"):
            self.assertIn(wording.lower(), instructions.lower())


class PayloadValidationTests(unittest.TestCase):
    FIELDS = {
        "role": frozenset({"role_title", "employer_name"}),
        "skill": frozenset({"name"}),
    }
    TEXT = "Systems Engineer at Northrop Grumman"

    def payload(self, **overrides):
        candidate = {
            "record_type": "role",
            "values": {"role_title": "Systems Engineer"},
            "outcome": "new",
            "span_start": 0,
            "span_end": 16,
            "quote": "Systems Engineer",
        }
        candidate.update(overrides)
        return {"candidates": [candidate]}

    def test_valid_payload_passes_with_exact_span(self):
        candidates = validate_extraction_payload(
            self.payload(), text=self.TEXT, allowed_fields=self.FIELDS
        )
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].outcome, "new")
        self.assertEqual(candidates[0].provided_fields, ("role_title",))

    def test_quote_must_match_its_span_exactly(self):
        with self.assertRaises(ExtractionError):
            validate_extraction_payload(
                self.payload(quote="Systems Enginer"),
                text=self.TEXT, allowed_fields=self.FIELDS,
            )

    def test_unknown_record_type_is_rejected(self):
        with self.assertRaises(ExtractionError):
            validate_extraction_payload(
                self.payload(record_type="hobby"),
                text=self.TEXT, allowed_fields=self.FIELDS,
            )

    def test_unknown_value_fields_are_rejected(self):
        with self.assertRaises(ExtractionError):
            validate_extraction_payload(
                self.payload(values={"role_title": "Systems Engineer", "salary": "1"}),
                text=self.TEXT, allowed_fields=self.FIELDS,
            )

    def test_null_closed_value_keys_are_ignored(self):
        candidates = validate_extraction_payload(
            self.payload(values={
                "role_title": "Systems Engineer",
                "employer_name": None,
                "text": None,
                "wording": None,
            }),
            text=self.TEXT, allowed_fields=self.FIELDS,
        )
        self.assertEqual(candidates[0].values, {"role_title": "Systems Engineer"})

    def test_unknown_outcome_is_rejected(self):
        with self.assertRaises(ExtractionError):
            validate_extraction_payload(
                self.payload(outcome="maybe"),
                text=self.TEXT, allowed_fields=self.FIELDS,
            )

    def test_equivalent_needs_a_listed_match_reference(self):
        shortlist = [{"record_key": "rec-1", "record_type": "role", "values": {}}]
        with self.assertRaises(ExtractionError):
            validate_extraction_payload(
                self.payload(outcome="equivalent"),
                text=self.TEXT, allowed_fields=self.FIELDS, shortlist=shortlist,
            )
        candidates = validate_extraction_payload(
            self.payload(outcome="equivalent", match_reference="rec-1"),
            text=self.TEXT, allowed_fields=self.FIELDS, shortlist=shortlist,
        )
        self.assertEqual(candidates[0].match_reference, "rec-1")

    def test_additional_detail_needs_a_listed_match_reference(self):
        shortlist = [{"record_key": "rec-1", "record_type": "role", "values": {}}]
        with self.assertRaises(ExtractionError) as missing:
            validate_extraction_payload(
                self.payload(outcome="additional_detail"),
                text=self.TEXT, allowed_fields=self.FIELDS, shortlist=shortlist,
            )
        self.assertEqual(missing.exception.code, "matched_needs_listed_match")
        candidates = validate_extraction_payload(
            self.payload(outcome="additional_detail", match_reference="rec-1"),
            text=self.TEXT, allowed_fields=self.FIELDS, shortlist=shortlist,
        )
        self.assertEqual(candidates[0].match_reference, "rec-1")

    def test_contradiction_needs_a_listed_match_reference(self):
        shortlist = [{"record_key": "rec-1", "record_type": "role", "values": {}}]
        with self.assertRaises(ExtractionError) as missing:
            validate_extraction_payload(
                self.payload(outcome="contradiction"),
                text=self.TEXT, allowed_fields=self.FIELDS, shortlist=shortlist,
            )
        self.assertEqual(missing.exception.code, "matched_needs_listed_match")
        candidates = validate_extraction_payload(
            self.payload(outcome="contradiction", match_reference="rec-1"),
            text=self.TEXT, allowed_fields=self.FIELDS, shortlist=shortlist,
        )
        self.assertEqual(candidates[0].match_reference, "rec-1")

    def test_unlisted_match_reference_is_rejected(self):
        with self.assertRaises(ExtractionError) as unlisted:
            validate_extraction_payload(
                self.payload(outcome="additional_detail", match_reference="rec-9"),
                text=self.TEXT, allowed_fields=self.FIELDS,
                shortlist=[{"record_key": "rec-1", "record_type": "role", "values": {}}],
            )
        self.assertEqual(unlisted.exception.code, "matched_needs_listed_match")

    def test_unique_quote_derives_same_span_and_service_candidate_shape(self):
        payload=self.payload()
        del payload["candidates"][0]["span_start"]
        del payload["candidates"][0]["span_end"]
        candidate=validate_extraction_payload(payload,text=self.TEXT,allowed_fields=self.FIELDS)[0]
        self.assertEqual((candidate.span_start,candidate.span_end,candidate.quote),(0,16,"Systems Engineer"))
        self.assertEqual(candidate.provided_fields,("role_title",))

    def test_ambiguous_nonexact_and_partial_spans_fail_closed(self):
        for text, patch, code in (
            (self.TEXT+" and Systems Engineer", {}, "ambiguous_quote"),
            (self.TEXT, {"quote":"Systems Enginer"}, "span_quote_mismatch"),
            (self.TEXT, {"span_start":0}, "invalid_span"),
        ):
            payload=self.payload()
            candidate=payload["candidates"][0]
            candidate.pop("span_start")
            candidate.pop("span_end")
            candidate.update(patch)
            with self.subTest(code=code), self.assertRaises(ExtractionError) as error:
                validate_extraction_payload(payload,text=text,allowed_fields=self.FIELDS)
            self.assertEqual(error.exception.code,code)

    def test_nullable_unknown_dates_and_boolean_current_role_are_preserved(self):
        values={"role_title":"Systems Engineer", "current_role":False, "start_date":None}
        fields={"role":frozenset(values)}
        candidate=validate_extraction_payload(self.payload(values=values),text=self.TEXT,allowed_fields=fields)[0]
        self.assertIs(candidate.values["current_role"],False)
        self.assertNotIn("start_date",candidate.values)
        values["current_role"]="false"
        with self.assertRaises(ExtractionError):
            validate_extraction_payload(self.payload(values=values),text=self.TEXT,allowed_fields=fields)


class ProviderTransportTests(unittest.TestCase):
    """The strict call actually sends effort xhigh and a strict schema."""

    def run_respond(self, transport):
        provider = AzureFoundryResponsesProvider(
            endpoint="https://example.openai.azure.com",
            token_provider=lambda: "token",
            spend_ledger=SpendLedger(hard_cap_micro_usd=10**12, max_calls=5),
        )
        provider._transport = transport
        request = StructuredRequest(
            request_id=str(uuid4()),
            product="my_data_intake",
            purpose=ExtractionPurpose.MY_DATA_INTAKE_EXTRACTION,
            audience=Audience.OWNER,
            subject_key="member",
            instructions="Extract.",
            input_text="Some material.",
            schema_name=EXTRACTION_SCHEMA_NAME,
            reasoning_effort="xhigh",
        )
        return provider.respond(request, response_schema=EXTRACTION_RESPONSE_SCHEMA)

    def test_outgoing_call_carries_xhigh_and_strict_schema(self):
        sent = {}

        class StubTransport:
            def post(self, url, *, headers, json, timeout):
                sent.update(json)
                return StubResponse()

        class StubResponse:
            status_code = 200

            def json(self):
                return {
                    "status": "completed",
                    "output": [{
                        "type": "message",
                        "content": [{
                            "type": "output_text",
                            "text": '{"candidates": []}',
                        }],
                    }],
                    "usage": {"input_tokens": 10, "output_tokens": 5},
                }

        result = self.run_respond(StubTransport())
        self.assertEqual(sent["model"], "gpt-5.6-luna")
        self.assertEqual(sent["reasoning"], {"effort": "xhigh"})
        self.assertNotIn("response_format", sent)
        text_format = sent["text"]["format"]
        self.assertEqual(text_format["type"], "json_schema")
        self.assertEqual(text_format["name"], EXTRACTION_SCHEMA_NAME)
        self.assertTrue(text_format["strict"])
        self.assertEqual(text_format["schema"], EXTRACTION_RESPONSE_SCHEMA)
        self.assertEqual(sent["store"], False)
        self.assertEqual(result.payload, {"candidates": []})
        self.assertEqual(result.model_name, "gpt-5.6-luna")

    def test_extraction_schema_is_recursively_strict(self):
        seen = []

        def walk(schema, path):
            seen.append(path)
            types = schema.get("type")
            type_names = types if isinstance(types, list) else [types]
            if "object" in type_names and "properties" in schema:
                self.assertIs(schema.get("additionalProperties"), False, path)
                self.assertEqual(
                    sorted(schema.get("required") or []),
                    sorted(schema["properties"]),
                    path,
                )
                for name, child in schema["properties"].items():
                    walk(child, f"{path}.{name}")
            if "array" in type_names and "items" in schema:
                walk(schema["items"], f"{path}[]")
            for index, branch in enumerate(schema.get("anyOf", [])):
                walk(branch, f"{path}.anyOf[{index}]")

        walk(EXTRACTION_RESPONSE_SCHEMA, "$")
        branches = EXTRACTION_RESPONSE_SCHEMA["properties"]["candidates"]["items"]["anyOf"]
        self.assertEqual(len(branches),6)
        for branch in branches:
            properties=branch["properties"]
            kind=properties["record_type"]["enum"][0]
            values=properties["values"]["properties"]
            self.assertEqual(set(values),set(EXTRACTION_VALUE_FIELDS[kind]))
            self.assertNotIn("span_start",properties)
            self.assertNotIn("span_end",properties)
            if kind=="role":
                self.assertEqual(values["current_role"]["type"],["boolean","null"])
            if kind=="skill":
                self.assertEqual(set(values),{"name","summary"})
        self.assertGreater(len(seen), 3)

    def test_provider_http_failure_is_unavailable_not_silent(self):
        class FailingTransport:
            def post(self, url, *, headers, json, timeout):
                return type("R", (), {"status_code": 500, "json": lambda s: {}})()

        with self.assertRaises(ProviderUnavailableError):
            self.run_respond(FailingTransport())


class ServiceWiringTests(unittest.TestCase):
    def setUp(self):
        self.owner = "member-a"

    def seed_role(self, service):
        receipt = service.submit(
            self.owner,
            add_request(items=[{
                "client_key": "r1", "record_type": "role", "values": dict(ROLE_VALUES),
            }]),
        )
        self.assertEqual(receipt["summary"]["saved"], 1)
        return receipt["saved_items"][0]["record_key"]

    def seed_skill(self, service):
        receipt = service.submit(
            self.owner,
            add_request(items=[{
                "client_key": "s1", "record_type": "skill",
                "values": {"name": "Requirements management"},
            }]),
        )
        self.assertEqual(receipt["summary"]["saved"], 1)
        return receipt["saved_items"][0]["record_key"]

    def test_new_extraction_becomes_a_proposal_never_a_save(self):
        fake = DeterministicFakeExtractionAdapter([{
            "record_type": "skill",
            "values": {"name": "Requirements management"},
            "outcome": "new",
            "quote": "requirements management",
            "confidence": "certain",
        }])
        service = build_service(extraction_adapter=fake, exclusions=lambda owner: set())
        receipt = service.submit(
            self.owner,
            add_request(text="I handle requirements management for the program."),
        )
        self.assertEqual(receipt["outcome"], "unresolved")
        self.assertEqual(len(receipt["proposals"]), 1)
        proposal = receipt["proposals"][0]
        self.assertEqual(proposal["kind"], "new_fact")
        self.assertEqual(proposal["record_type"], "skill")
        # The adapter was asked exactly once, at xhigh, with the strict schema.
        self.assertEqual(len(fake.calls), 1)
        call = fake.calls[0]
        self.assertEqual(call.request.reasoning_effort, "low")
        self.assertEqual(call.schema, EXTRACTION_RESPONSE_SCHEMA)
        self.assertEqual(call.request.audience, Audience.OWNER)

    def test_equivalent_extraction_stays_quiet_with_keep_separate(self):
        fake = DeterministicFakeExtractionAdapter()
        service = build_service(extraction_adapter=fake, exclusions=lambda owner: set())
        record_key = self.seed_role(service)
        text = "Systems Engineer at Northrop Grumman"
        fake.scripted.append({
            "record_type": "role",
            "values": {
                "role_title": "Systems Engineer",
                "employer_name": "Northrop Grumman",
            },
            "outcome": "equivalent",
            "quote": text,
            "match_reference": record_key,
            "confidence": "certain",
        })
        receipt = service.submit(self.owner, add_request(text=text))
        self.assertEqual(receipt["outcome"], "duplicate")
        self.assertEqual(receipt["summary"]["duplicates"], 1)
        self.assertIn("Already saved", receipt["message"])
        self.assertEqual(receipt["proposals"], [])
        row = receipt["results"][0]
        self.assertEqual(row["already_saved"], [{
            "record_key": record_key, "record_type": "role",
        }])
        self.assertEqual(len(row["keep_separate_actions"]), 1)
        keep = row["keep_separate_actions"][0]
        self.assertEqual(keep["record_type"], "role")
        self.assertTrue(keep["override_key"])
        self.assertNotIn("extracted_fields", keep)
        self.assertNotIn("values", keep)
        stored = service.repository.load_owner(self.owner)
        stored_keep = stored["receipts"][receipt["request_id"]]["result"]["results"][0]["keep_separate_actions"][0]
        self.assertEqual(stored_keep, keep)
        self.assertNotIn(text, repr(stored["receipts"][receipt["request_id"]]))
        source = next(row for row in stored["sources"].values() if row.get("text") == text)
        candidates = source["structured_values"]["_extracted_candidates"]
        self.assertEqual(candidates[0]["values"]["role_title"], "Systems Engineer")
        before = len(service._canonical_items(self.owner))
        separate = service.submit(
            self.owner,
            {
                "type": "keep_extracted_separate",
                "request_id": str(uuid4()),
                "override_key": keep["override_key"],
            },
        )
        self.assertEqual(separate["summary"]["saved"], 1)
        self.assertEqual(len(service._canonical_items(self.owner)), before + 1)
        consumed_source = service.repository.load_owner(self.owner)["sources"][source["source_key"]]
        consumed_candidate = consumed_source["structured_values"]["_extracted_candidates"][0]
        self.assertEqual(consumed_candidate["state"], "consumed")
        self.assertNotIn("values", consumed_candidate)
        # A proposed SQL round trip can retain the original mutable source JSON
        # while adding the identifier-only consumption receipt. Simulate that
        # reload shape: the receipt must still prevent a second canonical save.
        sql_like = service.repository.load_owner(self.owner)
        sql_candidate = sql_like["sources"][source["source_key"]]["structured_values"]["_extracted_candidates"][0]
        sql_candidate["state"] = "pending"
        sql_candidate["values"] = {
            "role_title": "Systems Engineer",
            "employer_name": "Northrop Grumman",
        }
        sql_candidate.pop("consumed_request_id", None)
        service.repository.save_owner(self.owner, sql_like)
        replay = service.submit(
            self.owner,
            {
                "type": "keep_extracted_separate",
                "request_id": separate["request_id"],
                "override_key": keep["override_key"],
            },
        )
        self.assertTrue(replay["replayed"])
        self.assertEqual(len(service._canonical_items(self.owner)), before + 1)
        again = service.submit(
            self.owner,
            {
                "type": "keep_extracted_separate",
                "request_id": str(uuid4()),
                "override_key": keep["override_key"],
            },
        )
        self.assertTrue(again["replayed"])
        self.assertEqual(len(service._canonical_items(self.owner)), before + 1)
        other = build_service(extraction_adapter=fake, exclusions=lambda owner: set())
        with self.assertRaises(ResumeIntakeNotFoundError):
            other.submit(
                "member-b",
                {
                    "type": "keep_extracted_separate",
                    "request_id": str(uuid4()),
                    "override_key": keep["override_key"],
                },
            )

    def test_source_purge_redacts_and_invalidates_extracted_keep_separate(self):
        fake = DeterministicFakeExtractionAdapter()
        service = build_service(extraction_adapter=fake, exclusions=lambda owner: set())
        record_key = self.seed_role(service)
        text = "Systems Engineer at Northrop Grumman"
        fake.scripted.append({
            "record_type": "role",
            "values": {
                "role_title": "Systems Engineer",
                "employer_name": "Northrop Grumman",
            },
            "outcome": "equivalent",
            "quote": text,
            "match_reference": record_key,
            "confidence": "certain",
        })
        receipt = service.submit(self.owner, add_request(text=text))
        keep = receipt["results"][0]["keep_separate_actions"][0]
        snapshot = service.repository.load_owner(self.owner)
        source_key = next(
            key for key, row in snapshot["sources"].items()
            if row.get("text") == text
        )
        service.purge_source(
            self.owner,
            {"request_id": str(uuid4()), "source_key": source_key},
        )
        snapshot = service.repository.load_owner(self.owner)
        self.assertIsNone(snapshot["sources"][source_key].get("text"))
        before = len(service._canonical_items(self.owner))
        with self.assertRaises(ResumeIntakeConflictError) as raised:
            service.submit(
                self.owner,
                {
                    "type": "keep_extracted_separate",
                    "request_id": str(uuid4()),
                    "override_key": keep["override_key"],
                },
            )
        self.assertEqual(raised.exception.error_code, "source_purged")
        self.assertEqual(len(service._canonical_items(self.owner)), before)
        snapshot = service.repository.load_owner(self.owner)
        self.assertIsNone(snapshot["sources"][source_key].get("text"))
        self.assertEqual(snapshot["sources"][source_key]["state"], "purged")
        tombstones = snapshot["sources"][source_key]["structured_values"]["_extracted_candidates"]
        self.assertEqual(tombstones[0]["state"], "invalidated")
        self.assertNotIn("values", tombstones[0])
        stored_receipt = snapshot["receipts"][receipt["request_id"]]["result"]
        self.assertNotIn("Systems Engineer", repr(stored_receipt))
        self.assertNotIn("Northrop Grumman", repr(stored_receipt))
        for source in snapshot["sources"].values():
            self.assertNotEqual(source.get("text"), text)

    def test_purge_wins_before_keep_guard_without_restore_or_canonical_write(self):
        repository = PurgeWinsResumeIntakeRepository()
        fake = DeterministicFakeExtractionAdapter()
        service = build_service(
            repository=repository,
            extraction_adapter=fake,
            exclusions=lambda owner: set(),
        )
        record_key = self.seed_role(service)
        text = "Systems Engineer at Northrop Grumman"
        fake.scripted.append({
            "record_type": "role",
            "values": {
                "role_title": "Systems Engineer",
                "employer_name": "Northrop Grumman",
            },
            "outcome": "equivalent",
            "quote": text,
            "match_reference": record_key,
            "confidence": "certain",
        })
        receipt = service.submit(self.owner, add_request(text=text))
        action = receipt["results"][0]["keep_separate_actions"][0]
        source_key = receipt["submission"]["source_keys"][0]
        keep_request_id = str(uuid4())
        before = len(service._canonical_items(self.owner))
        errors = []

        def delayed_keep():
            try:
                service.submit(
                    self.owner,
                    {
                        "type": "keep_extracted_separate",
                        "request_id": keep_request_id,
                        "override_key": action["override_key"],
                    },
                )
            except Exception as error:  # asserted after the deterministic join
                errors.append(error)

        thread = threading.Thread(target=delayed_keep, name="delayed-keep-separate")
        thread.start()
        self.assertTrue(repository.keep_waiting.wait(timeout=5))
        purged = service.purge_source(
            self.owner,
            {"request_id": str(uuid4()), "source_key": source_key},
        )
        self.assertEqual(purged["outcome"], "purged")
        repository.release_keep.set()
        thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], ResumeIntakeConflictError)
        self.assertEqual(errors[0].error_code, "source_purged")
        self.assertEqual(len(service._canonical_items(self.owner)), before)
        snapshot = repository.load_owner(self.owner)
        source = snapshot["sources"][source_key]
        self.assertEqual(source["state"], "purged")
        self.assertIsNone(source.get("text"))
        self.assertNotIn(keep_request_id, snapshot["receipts"])
        self.assertNotIn(action["override_key"], snapshot["submissions"])
        self.assertNotIn(text, repr(source.get("structured_values")))

    def test_every_pure_equivalent_action_is_independent_and_idempotent(self):
        fake = DeterministicFakeExtractionAdapter()
        service = build_service(extraction_adapter=fake, exclusions=lambda owner: set())
        role_key = self.seed_role(service)
        skill_key = self.seed_skill(service)
        role_quote = "Systems Engineer at Northrop Grumman"
        skill_quote = "Requirements management"
        fake.scripted.extend([
            {
                "record_type": "role",
                "values": {"role_title": "Systems Engineer", "employer_name": "Northrop Grumman"},
                "outcome": "equivalent", "quote": role_quote,
                "match_reference": role_key, "confidence": "certain",
            },
            {
                "record_type": "skill",
                "values": {"name": skill_quote},
                "outcome": "equivalent", "quote": skill_quote,
                "match_reference": skill_key, "confidence": "certain",
            },
        ])
        receipt = service.submit(
            self.owner, add_request(text=f"{role_quote}. {skill_quote}.")
        )
        row = receipt["results"][0]
        actions = row["keep_separate_actions"]
        self.assertEqual(len(actions), 2)
        self.assertEqual(len({action["override_key"] for action in actions}), 2)
        before = len(service._canonical_items(self.owner))
        for offset, action in enumerate(actions, start=1):
            request_id = str(uuid4())
            command = {
                "type": "keep_extracted_separate",
                "request_id": request_id,
                "override_key": action["override_key"],
            }
            saved = service.submit(self.owner, command)
            self.assertEqual(saved["summary"]["saved"], 1)
            self.assertEqual(len(service._canonical_items(self.owner)), before + offset)
            replay = service.submit(self.owner, command)
            self.assertTrue(replay["replayed"])
            self.assertEqual(len(service._canonical_items(self.owner)), before + offset)

    def test_mixed_results_keep_every_equivalent_action_and_purge_invalidates_each(self):
        fake = DeterministicFakeExtractionAdapter()
        service = build_service(extraction_adapter=fake, exclusions=lambda owner: set())
        role_key = self.seed_role(service)
        skill_key = self.seed_skill(service)
        role_quote = "Systems Engineer at Northrop Grumman"
        skill_quote = "Requirements management"
        new_quote = "Stakeholder facilitation"
        uncertain_quote = "Led something important"
        fake.scripted.extend([
            {
                "record_type": "role",
                "values": {"role_title": "Systems Engineer", "employer_name": "Northrop Grumman"},
                "outcome": "equivalent", "quote": role_quote,
                "match_reference": role_key, "confidence": "certain",
            },
            {
                "record_type": "skill", "values": {"name": skill_quote},
                "outcome": "equivalent", "quote": skill_quote,
                "match_reference": skill_key, "confidence": "certain",
            },
            {
                "record_type": "skill", "values": {"name": new_quote},
                "outcome": "new", "quote": new_quote, "confidence": "certain",
            },
            {
                "record_type": "role", "values": {"summary": uncertain_quote},
                "outcome": "uncertain", "quote": uncertain_quote,
                "confidence": "uncertain",
            },
        ])
        material = ". ".join((role_quote, skill_quote, new_quote, uncertain_quote))
        receipt = service.submit(self.owner, add_request(text=material))
        self.assertEqual(receipt["outcome"], "unresolved")
        self.assertEqual(len(receipt["proposals"]), 2)
        actions = receipt["results"][0]["keep_separate_actions"]
        self.assertEqual(len(actions), 2)
        self.assertEqual(len({action["override_key"] for action in actions}), 2)
        before = len(service._canonical_items(self.owner))
        for offset, action in enumerate(actions, start=1):
            command = {
                "type": "keep_extracted_separate",
                "request_id": str(uuid4()),
                "override_key": action["override_key"],
            }
            service.submit(self.owner, command)
            self.assertEqual(len(service._canonical_items(self.owner)), before + offset)
            self.assertTrue(service.submit(self.owner, command)["replayed"])

        purge_receipt = service.submit(self.owner, add_request(text=material))
        purge_actions = purge_receipt["results"][0]["keep_separate_actions"]
        self.assertEqual(len(purge_actions), 2)
        source_key = purge_receipt["submission"]["source_keys"][0]
        purged = service.purge_source(
            self.owner, {"request_id": str(uuid4()), "source_key": source_key}
        )
        self.assertEqual(purged["invalidated_extracted_candidates"], 2)
        for action in purge_actions:
            with self.assertRaises(ResumeIntakeConflictError) as raised:
                service.submit(
                    self.owner,
                    {
                        "type": "keep_extracted_separate",
                        "request_id": str(uuid4()),
                        "override_key": action["override_key"],
                    },
                )
            self.assertEqual(raised.exception.error_code, "source_purged")

    def test_document_equivalent_exposes_keep_separate(self):
        from tests.test_my_data_intake_sources import FakeUpload, extracted_pipeline

        fake = DeterministicFakeExtractionAdapter()
        service = build_service(
            extraction_adapter=fake,
            exclusions=lambda owner: set(),
            document_pipeline=extracted_pipeline("Systems Engineer at Northrop Grumman"),
        )
        record_key = self.seed_role(service)
        text = "Systems Engineer at Northrop Grumman"
        fake.scripted.append({
            "record_type": "role",
            "values": {"role_title": "Systems Engineer", "employer_name": "Northrop Grumman"},
            "outcome": "equivalent",
            "quote": text,
            "match_reference": record_key,
            "confidence": "certain",
        })
        receipt = service.submit(
            self.owner,
            add_request(attachments=[{
                "client_key": "doc-1",
                "kind": "document",
                "declared_content_type": "text/plain",
                "filename": "note.txt",
            }]),
            files={"doc-1": FakeUpload("text/plain", text.encode("utf-8"))},
        )
        self.assertEqual(receipt["outcome"], "duplicate")
        keep = receipt["results"][0]["keep_separate_actions"][0]
        self.assertTrue(keep["override_key"])
        separate = service.submit(
            self.owner,
            {
                "type": "keep_extracted_separate",
                "request_id": str(uuid4()),
                "override_key": keep["override_key"],
            },
        )
        self.assertEqual(separate["summary"]["saved"], 1)

    def test_recording_equivalent_exposes_keep_separate(self):
        from services.resume_intake_transcription_adapter import ResumeTranscriptionAdapter
        from tests.test_my_data_intake_sources import (
            StubTranscriber,
            recording_payload,
            wav_bytes,
        )

        fake = DeterministicFakeExtractionAdapter()
        text = "Systems Engineer at Northrop Grumman"
        service = build_service(
            extraction_adapter=fake,
            exclusions=lambda owner: set(),
            transcription_adapter=ResumeTranscriptionAdapter(
                service=StubTranscriber(text)
            ),
        )
        record_key = self.seed_role(service)
        fake.scripted.append({
            "record_type": "role",
            "values": {"role_title": "Systems Engineer", "employer_name": "Northrop Grumman"},
            "outcome": "equivalent",
            "quote": text,
            "match_reference": record_key,
            "confidence": "certain",
        })
        upload, payload = recording_payload("audio/wav", wav_bytes(), 12.0)
        transcribed = service.transcribe_recording(self.owner, upload, payload)
        receipt = service.submit(
            self.owner,
            add_request(attachments=[{
                "client_key": "clip-1",
                "kind": "recording",
                "source_key": transcribed["source_key"],
            }]),
        )
        self.assertEqual(receipt["outcome"], "duplicate")
        keep = receipt["results"][0]["keep_separate_actions"][0]
        self.assertTrue(keep["override_key"])
        separate = service.submit(
            self.owner,
            {
                "type": "keep_extracted_separate",
                "request_id": str(uuid4()),
                "override_key": keep["override_key"],
            },
        )
        self.assertEqual(separate["summary"]["saved"], 1)

    def test_structured_duplicate_carries_resubmit_payload(self):
        service = build_service()
        self.seed_role(service)
        receipt = service.submit(
            self.owner,
            add_request(items=[{
                "client_key": "r2", "record_type": "role",
                "values": dict(ROLE_VALUES),
            }]),
        )
        self.assertEqual(receipt["outcome"], "duplicate")
        row = receipt["results"][0]
        keep = row["keep_separate"]
        self.assertEqual(keep["record_type"], "role")
        self.assertEqual(keep["values"]["role_title"], "Systems Engineer")
        self.assertEqual(row["intake_source_key"] is not None, True)
        # Same request replays with its resubmit wording recovered.
        replay = service.submit(
            self.owner,
            {
                "type": "add_submission",
                "request_id": receipt["request_id"],
                "items": [{
                    "client_key": "r2", "record_type": "role",
                    "values": dict(ROLE_VALUES),
                }],
            },
        )
        self.assertTrue(replay["replayed"])
        self.assertEqual(
            replay["results"][0]["keep_separate"]["values"]["role_title"],
            "Systems Engineer",
        )
        # Malformed keep-as-separate flags never silently skip matching.
        with self.assertRaises(Exception):
            service.submit(
                self.owner,
                add_request(items=[{
                    "client_key": "r3", "record_type": "role",
                    "values": dict(ROLE_VALUES), "as_separate": "yes",
                }]),
            )

    def test_excluded_entries_never_reach_the_provider(self):
        inner = build_service(extraction_adapter=None, exclusions=lambda owner: set())
        record_key = self.seed_role(inner)
        shortlist = inner._matching_shortlist(self.owner)
        self.assertEqual(len(shortlist), 1)
        # The same member fact, excluded from private AI, compares nothing.
        excluded = build_service(
            extraction_adapter=None, exclusions=lambda owner: {record_key}
        )
        excluded.repository = inner.repository
        excluded.draft_service = inner.draft_service
        self.assertEqual(excluded._matching_shortlist(self.owner), [])

    def test_unwired_exclusions_compare_nothing(self):
        fake = DeterministicFakeExtractionAdapter()
        service = build_service(extraction_adapter=fake)
        self.seed_role(service)
        shortlist = service._matching_shortlist(self.owner)
        self.assertEqual(shortlist, [])

    def test_provider_failure_stays_truthful_retryable_and_manual(self):
        fake = DeterministicFakeExtractionAdapter()
        fake.fail_with = "provider_unavailable"
        service = build_service(extraction_adapter=fake, exclusions=lambda owner: set())
        receipt = service.submit(
            self.owner, add_request(text="I led the migration last spring.")
        )
        self.assertEqual(receipt["outcome"], "unresolved")
        row = receipt["results"][0]
        # The member's input survives as an uncertain proposal they can finish.
        self.assertEqual(len(receipt["proposals"]), 1)
        self.assertEqual(row["provider_issue"], {
            "code": "provider_unavailable", "retryable": True,
        })
        self.assertIn("unavailable right now", row["message"])
        # Exactly one attempt: no silent retry at another effort or model.
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(fake.calls[0].request.reasoning_effort, "low")

    def test_malformed_provider_payload_never_saves(self):
        class BadProvider:
            def __call__(self, request, *, response_schema):
                return {"candidates": [{"record_type": "role"}]}

        from services.my_data_extraction_adapter import MyDataExtractionAdapter
        adapter = MyDataExtractionAdapter(provider=BadProvider())
        service = build_service(extraction_adapter=adapter, exclusions=lambda o: set())
        receipt = service.submit(
            self.owner, add_request(text="Systems Engineer at Northrop Grumman")
        )
        self.assertEqual(receipt["outcome"], "unresolved")
        self.assertEqual(receipt["summary"]["saved"], 0)
        self.assertEqual(
            receipt["results"][0]["provider_issue"]["retryable"], True
        )


class MatchedTargetBindingTests(unittest.TestCase):
    """Extraction matches overlay the listed fact; unbound matches fail closed."""

    def setUp(self):
        self.owner = "member-a"

    def seed_role(self, service):
        receipt = service.submit(
            self.owner,
            add_request(items=[{
                "client_key": "r1", "record_type": "role", "values": dict(ROLE_VALUES),
            }]),
        )
        self.assertEqual(receipt["summary"]["saved"], 1)
        return receipt["saved_items"][0]["record_key"]

    def stored_proposal(self, service, presented):
        snapshot = service.repository.load_owner(self.owner)
        return snapshot["proposals"][presented["proposal_key"]]

    def role_count(self, catalog):
        return len([
            item for item in catalog.list_items(self.owner)
            if item["record_type"] == "role"
        ])

    def test_additional_detail_overlays_the_existing_canonical_fact(self):
        text = "Also based in Huntsville, Alabama"
        fake = DeterministicFakeExtractionAdapter()
        service, catalog = build_wired_service(
            extraction_adapter=fake, exclusions=lambda owner: set(),
        )
        record_key = self.seed_role(service)
        seeded = catalog.get_item(self.owner, record_key)
        fake.scripted.append({
            "record_type": "role",
            "values": {
                "role_title": ROLE_VALUES["role_title"],
                "location_text": "Huntsville, Alabama",
            },
            "outcome": "additional_detail",
            "quote": text,
            "match_reference": record_key,
            "confidence": "certain",
        })
        receipt = service.submit(self.owner, add_request(text=text))
        self.assertEqual(receipt["outcome"], "unresolved")
        proposal = receipt["proposals"][0]
        self.assertEqual(proposal["kind"], "additional_detail")
        self.assertEqual(proposal["target_key"], record_key)
        stored = self.stored_proposal(service, proposal)
        self.assertEqual(stored["target_content_token"], seeded["content_token"])
        self.assertEqual(stored["target_access_revision"], seeded["access_revision"])
        accepted = service.decide(
            self.owner,
            {
                "request_id": str(uuid4()),
                "proposal_key": proposal["proposal_key"],
                "decision": "accept",
                "confirmed_values": {"location_text": "Huntsville, Alabama"},
            },
        )
        self.assertEqual(accepted["outcome"], "saved")
        self.assertTrue(accepted["item"]["draft_overlay"])
        self.assertEqual(accepted["item"]["record_key"], record_key)
        self.assertEqual(
            accepted["item"]["proposed_values"]["location_text"],
            "Huntsville, Alabama",
        )
        self.assertEqual(self.role_count(catalog), 1)

    def test_project_amendment_keeps_existing_meaning_and_requires_confirmation(self):
        text='I also led the Beacon pilot at Northrop Grumman.'
        fake=DeterministicFakeExtractionAdapter()
        service,catalog=build_wired_service(extraction_adapter=fake,exclusions=lambda owner:set())
        key=self.seed_role(service)
        existing=catalog.get_item(self.owner,key)['values']['summary']
        fake.scripted.append({'record_type':'role','values':{'summary':'Led the Beacon pilot.'},
            'outcome':'additional_detail','quote':text,'match_reference':key,'confidence':'certain'})
        receipt=service.submit(self.owner,add_request(text=text));proposal=receipt['proposals'][0]
        self.assertEqual(proposal['target_key'],key)
        self.assertEqual(proposal['proposed_values']['summary'],existing+'\nLed the Beacon pilot.')
        self.assertEqual(catalog.get_item(self.owner,key)['values']['summary'],existing)
        service.decide(self.owner,{'request_id':str(uuid4()),'proposal_key':proposal['proposal_key'],
            'decision':'accept','confirmed_values':{'summary':proposal['proposed_values']['summary']}})
        self.assertEqual(self.role_count(catalog),1)
        self.assertEqual(service.draft_service.get_workspace(self.owner)['items'][0]['proposed_values']['summary'],
            existing+'\nLed the Beacon pilot.')

    def test_contradiction_creates_a_targeted_proposal(self):
        text = "Systems Engineer at Example Corp"
        fake = DeterministicFakeExtractionAdapter()
        service, catalog = build_wired_service(
            extraction_adapter=fake, exclusions=lambda owner: set(),
        )
        record_key = self.seed_role(service)
        fake.scripted.append({
            "record_type": "role",
            "values": {
                "role_title": ROLE_VALUES["role_title"],
                "employer_name": "Example Corp",
            },
            "outcome": "contradiction",
            "quote": text,
            "match_reference": record_key,
            "confidence": "certain",
        })
        receipt = service.submit(self.owner, add_request(text=text))
        proposal = receipt["proposals"][0]
        self.assertEqual(proposal["kind"], "contradiction")
        self.assertEqual(proposal["target_key"], record_key)
        stored = self.stored_proposal(service, proposal)
        self.assertIsNotNone(stored["target_content_token"])
        self.assertIsNotNone(stored["target_access_revision"])
        accepted = service.decide(
            self.owner,
            {
                "request_id": str(uuid4()),
                "proposal_key": proposal["proposal_key"],
                "decision": "accept",
                "confirmed_values": {"employer_name": "Example Corp"},
            },
        )
        self.assertEqual(accepted["outcome"], "saved")
        self.assertTrue(accepted["item"]["draft_overlay"])
        self.assertEqual(accepted["item"]["record_key"], record_key)
        self.assertEqual(self.role_count(catalog), 1)

    def test_acceptance_does_not_create_a_second_canonical_row(self):
        # Covered by overlay and contradiction accepts; this names the
        # canonical-count invariant Grok required as its own regression.
        text = "Also based in Huntsville, Alabama"
        fake = DeterministicFakeExtractionAdapter()
        service, catalog = build_wired_service(
            extraction_adapter=fake, exclusions=lambda owner: set(),
        )
        record_key = self.seed_role(service)
        self.assertEqual(self.role_count(catalog), 1)
        fake.scripted.append({
            "record_type": "role",
            "values": {"location_text": "Huntsville, Alabama"},
            "outcome": "additional_detail",
            "quote": text,
            "match_reference": record_key,
            "confidence": "certain",
        })
        receipt = service.submit(self.owner, add_request(text=text))
        service.decide(
            self.owner,
            {
                "request_id": str(uuid4()),
                "proposal_key": receipt["proposals"][0]["proposal_key"],
                "decision": "accept",
                "confirmed_values": {"location_text": "Huntsville, Alabama"},
            },
        )
        self.assertEqual(self.role_count(catalog), 1)
        keys = {
            item["record_key"] for item in catalog.list_items(self.owner)
            if item["record_type"] == "role"
        }
        self.assertEqual(keys, {record_key})

    def _fail_closed_receipt(self, *, match_reference, exclusions=None):
        text = "Also based in Huntsville, Alabama"
        service, catalog = build_wired_service(
            extraction_adapter=LooseExtractionAdapter([
                ExtractionCandidate(
                    record_type="role",
                    values={"location_text": "Huntsville, Alabama"},
                    outcome="additional_detail",
                    span_start=0,
                    span_end=len(text),
                    quote=text,
                    match_reference=match_reference,
                    provided_fields=("location_text",),
                    confidence="certain",
                )
            ]),
            exclusions=exclusions if exclusions is not None else (lambda owner: set()),
        )
        record_key = self.seed_role(service)
        receipt = service.submit(self.owner, add_request(text=text))
        return receipt, catalog, record_key

    def test_missing_match_reference_fails_closed(self):
        receipt, catalog, _record_key = self._fail_closed_receipt(match_reference=None)
        proposal = receipt["proposals"][0]
        self.assertEqual(proposal["kind"], "inferred_wording")
        self.assertIsNone(proposal["target_key"])
        self.assertEqual(self.role_count(catalog), 1)

    def test_unlisted_match_reference_fails_closed(self):
        receipt, catalog, _record_key = self._fail_closed_receipt(
            match_reference="not-on-the-shortlist",
        )
        proposal = receipt["proposals"][0]
        self.assertEqual(proposal["kind"], "inferred_wording")
        self.assertIsNone(proposal["target_key"])
        self.assertEqual(self.role_count(catalog), 1)

    def test_excluded_match_reference_fails_closed(self):
        text = "Also based in Huntsville, Alabama"
        inner, catalog = build_wired_service(
            extraction_adapter=None, exclusions=lambda owner: set(),
        )
        record_key = self.seed_role(inner)
        excluded = ResumeIntakeService(
            repository=inner.repository,
            draft_service=inner.draft_service,
            policy=selected_policy_for_tests(),
            extraction_adapter=LooseExtractionAdapter([
                ExtractionCandidate(
                    record_type="role",
                    values={"location_text": "Huntsville, Alabama"},
                    outcome="additional_detail",
                    span_start=0,
                    span_end=len(text),
                    quote=text,
                    match_reference=record_key,
                    provided_fields=("location_text",),
                    confidence="certain",
                )
            ]),
            matching_exclusions=lambda owner: {record_key},
        )
        receipt = excluded.submit(self.owner, add_request(text=text))
        proposal = receipt["proposals"][0]
        self.assertEqual(proposal["kind"], "inferred_wording")
        self.assertIsNone(proposal["target_key"])
        self.assertEqual(self.role_count(catalog), 1)

    def test_unreadable_catalog_fails_closed(self):
        text = "Also based in Huntsville, Alabama"
        fake = DeterministicFakeExtractionAdapter()
        service, catalog = build_wired_service(
            extraction_adapter=fake, exclusions=lambda owner: set(),
        )
        record_key = self.seed_role(service)
        fake.scripted.append({
            "record_type": "role",
            "values": {"location_text": "Huntsville, Alabama"},
            "outcome": "additional_detail",
            "quote": text,
            "match_reference": record_key,
            "confidence": "certain",
        })
        inner = service.draft_service

        class WorkspaceGate:
            def __init__(self):
                self.calls = 0

            def __getattr__(self, name):
                return getattr(inner, name)

            def get_workspace(self, owner):
                self.calls += 1
                if self.calls > 1:
                    raise ResumeDraftUnavailableError()
                return inner.get_workspace(owner)

        service.draft_service = WorkspaceGate()
        receipt = service.submit(self.owner, add_request(text=text))
        proposal = receipt["proposals"][0]
        self.assertEqual(proposal["kind"], "inferred_wording")
        self.assertIsNone(proposal["target_key"])
        self.assertEqual(self.role_count(catalog), 1)

    def test_stale_missing_content_token_fails_closed(self):
        text = "Also based in Huntsville, Alabama"
        service, catalog = build_wired_service(
            extraction_adapter=None, exclusions=lambda owner: set(),
        )
        record_key = self.seed_role(service)
        item = catalog.get_item(self.owner, record_key)
        item["content_token"] = ""
        catalog.put_item(self.owner, item)
        service._extraction_adapter = LooseExtractionAdapter([
            ExtractionCandidate(
                record_type="role",
                values={"location_text": "Huntsville, Alabama"},
                outcome="additional_detail",
                span_start=0,
                span_end=len(text),
                quote=text,
                match_reference=record_key,
                provided_fields=("location_text",),
                confidence="certain",
            )
        ])
        receipt = service.submit(self.owner, add_request(text=text))
        proposal = receipt["proposals"][0]
        self.assertEqual(proposal["kind"], "inferred_wording")
        self.assertIsNone(proposal["target_key"])
        self.assertEqual(self.role_count(catalog), 1)

    def test_target_version_conflict_uses_reconciliation_path(self):
        text = "Also based in Huntsville, Alabama"
        fake = DeterministicFakeExtractionAdapter()
        service, catalog = build_wired_service(
            extraction_adapter=fake, exclusions=lambda owner: set(),
        )
        record_key = self.seed_role(service)
        fake.scripted.append({
            "record_type": "role",
            "values": {"location_text": "Huntsville, Alabama"},
            "outcome": "additional_detail",
            "quote": text,
            "match_reference": record_key,
            "confidence": "certain",
        })
        receipt = service.submit(self.owner, add_request(text=text))
        catalog.bump_content(self.owner, record_key)
        with self.assertRaises(ResumeIntakeConflictError) as caught:
            service.decide(
                self.owner,
                {
                    "request_id": str(uuid4()),
                    "proposal_key": receipt["proposals"][0]["proposal_key"],
                    "decision": "accept",
                    "confirmed_values": {"location_text": "Huntsville, Alabama"},
                },
            )
        self.assertEqual(caught.exception.error_code, "changed")
        self.assertIn("still here", str(caught.exception))
        self.assertEqual(self.role_count(catalog), 1)



class StrengthenedExtractionTests(unittest.TestCase):
    FIELDS = {kind: frozenset(fields) for kind, fields in EXTRACTION_VALUE_FIELDS.items()}

    def candidate(self, *, values=None, quote="I use mentoring and planning.", **changes):
        candidate = {"record_type": "skill", "values": values or {"name": "mentoring"},
                     "quote": quote, "outcome": "new", "match_reference": None}
        candidate.update(changes)
        return candidate

    def validate(self, candidates, *, text="I use mentoring and planning.", shortlist=None):
        return validate_extraction_payload({"candidates": candidates}, text=text,
                                          allowed_fields=self.FIELDS, shortlist=shortlist)

    def test_repeated_word_and_whole_passage_need_unique_contiguous_context(self):
        text = "At Juniper I did mentoring. My strengths are mentoring and planning."
        with self.assertRaises(ExtractionError) as error:
            self.validate([self.candidate(quote="mentoring")], text=text)
        self.assertEqual(error.exception.code, "ambiguous_quote")
        start = text.find("mentoring")
        with self.assertRaises(ExtractionError) as error:
            self.validate([self.candidate(quote="mentoring", span_start=start,
                                          span_end=start + len("mentoring"))], text=text)
        self.assertEqual(error.exception.code, "ambiguous_quote")
        quote = "My strengths are mentoring and planning."
        result = self.validate([self.candidate(quote=quote)], text=text)
        self.assertEqual(text[result[0].span_start:result[0].span_end], quote)
        text = "Earlier: I use mentoring and planning. Later: I use mentoring and planning."
        with self.assertRaises(ExtractionError):
            self.validate([self.candidate()], text=text)
        expanded = "Later: I use mentoring and planning."
        self.assertEqual(self.validate([self.candidate(quote=expanded)], text=text)[0].quote, expanded)

    def test_exact_duplicate_normalizes_null_and_order_and_preserves_first_anchor(self):
        text = "I use mentoring and planning. These strengths include mentoring."
        first = self.candidate(values={"name": "mentoring", "summary": None})
        second = self.candidate(values={"name": "mentoring"},
                                quote="These strengths include mentoring.")
        result = self.validate([first, second], text=text)
        self.assertEqual(len(result), 1)
        self.assertEqual((result[0].span_start, result[0].quote), (0, first["quote"]))
        self.assertEqual(result[0].values, {"name": "mentoring"})
        role_quote = "I was an Analyst at Cedar."
        roles = [self.candidate(record_type="role", quote=role_quote,
                                values={"role_title": "Analyst", "employer_name": "Cedar"}),
                 self.candidate(record_type="role", quote=role_quote,
                                values={"employer_name": "Cedar", "role_title": "Analyst"})]
        self.assertEqual(len(self.validate(roles, text=role_quote)), 1)

    def test_invalid_duplicate_still_rejects_entire_raw_batch(self):
        first = self.candidate()
        for changes in ({"quote": "mentoring"}, {"quote": "not present"},
                        {"outcome": "invented"}, {"outcome": []}, {"match_reference": "not-listed"},
                        {"confidence": "invented"}, {"confidence": ["certain"]}, {"confidence": []},
                        {"confidence": False}, {"values": {"name": 3}}):
            with self.subTest(changes=changes), self.assertRaises(ExtractionError):
                self.validate([first, self.candidate(**changes)],
                              text="I use mentoring and planning. More mentoring.")

    def test_reduction_never_fuzzily_merges_meaning_types_outcomes_or_targets(self):
        shortlist = [{"record_key": key, "record_type": "skill", "values": {"name": "mentoring"}}
                     for key in ("skill-a", "skill-b")]
        candidates = [self.candidate(), self.candidate(values={"name": "Mentoring"}),
                      self.candidate(values={"name": "mentoring", "summary": "Supports peers"}),
                      self.candidate(outcome="uncertain"),
                      self.candidate(outcome="equivalent", match_reference="skill-a"),
                      self.candidate(outcome="equivalent", match_reference="skill-b"),
                      self.candidate(record_type="unspecified", values={"text": "mentoring"})]
        text = "I use mentoring and planning. I support peers."
        candidates = [{**candidate, "quote": text} for candidate in candidates]
        self.assertEqual(len(self.validate(candidates, shortlist=shortlist, text=text)), len(candidates))

    def test_distinct_jobs_at_same_employer_stay_separate(self):
        text = "At Cedar I was Analyst from2017 to2020. At Cedar I was Manager from2020 to2022."
        candidates = [self.candidate(record_type="role", quote=sentence,
            values={"employer_name": "Cedar", "role_title": title, "start_date": start})
            for sentence, title, start in (("At Cedar I was Analyst from2017 to2020.", "Analyst", "2017-01-01"),
                                          ("At Cedar I was Manager from2020 to2022.", "Manager", "2020-01-01"))]
        self.assertEqual([row.values["role_title"] for row in self.validate(candidates, text=text)], ["Analyst", "Manager"])

    def test_reduction_preserves_certainty_and_member_update_field_metadata(self):
        candidates = [self.candidate(confidence="certain"), self.candidate(confidence="uncertain"),
                      self.candidate(confidence="certain", provided_fields=["name", "summary"])]
        self.assertEqual(len(self.validate(candidates)), 3)

    def test_all_matched_outcomes_require_same_record_type(self):
        shortlist = [{"record_key": "role-a", "record_type": "role", "values": {}}]
        for outcome in ("equivalent", "additional_detail", "contradiction", "uncertain", "new"):
            with self.subTest(outcome=outcome), self.assertRaises(ExtractionError) as error:
                self.validate([self.candidate(outcome=outcome, match_reference="role-a")], shortlist=shortlist)
            self.assertEqual(error.exception.code, "matched_record_type_mismatch")

    def test_exact_reference_and_five_outcomes_preserve_only_input_values(self):
        shortlist = [{"record_key": "skill-a", "record_type": "skill", "values":
                      {"name": "mentoring", "summary": "Shortlist-only confidential wording"}}]
        candidates = [self.candidate(outcome=outcome,
                      match_reference=None if outcome == "new" else "skill-a")
                      for outcome in ("new", "equivalent", "additional_detail", "contradiction", "uncertain")]
        result = self.validate(candidates, shortlist=shortlist)
        self.assertEqual(len(result), 5)
        self.assertTrue(all(row.values == {"name": "mentoring"} for row in result))

    def test_duplicate_new_proposals_remain_member_controlled(self):
        entry = self.candidate()
        fake = DeterministicFakeExtractionAdapter([entry, dict(entry)])
        service, catalog = build_wired_service(extraction_adapter=fake, exclusions=lambda owner: set())
        owner = "synthetic-strengthening-owner"
        receipt = service.submit(owner, add_request(text=entry["quote"]))
        self.assertEqual(len(receipt["proposals"]), 1)
        self.assertEqual(receipt["outcome"], "unresolved")
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(catalog.list_items(owner), [])

    def test_model_specific_efforts_keep_luna_default_and_matching_scope(self):
        for model, efforts in (("gpt-5.6-luna", ("medium", "high", "xhigh")),
                              ("gpt-6-sol", ("low", "medium", "high"))):
            for effort in efforts:
                request = MyDataExtractionAdapter(model=model, reasoning_effort=effort).build_request("Material")
                self.assertEqual((request.model_name, request.reasoning_effort), (model, effort))
        self.assertEqual(MyDataExtractionAdapter().model, "gpt-6-luna")
        self.assertEqual(MyDataExtractionAdapter().reasoning_effort, "low")
        with self.assertRaises(ExtractionError):
            MyDataExtractionAdapter(model="gpt-6-sol", reasoning_effort="xhigh")
        with self.assertRaises(ValueError):
            MyDataExtractionAdapter(model="gpt-6-sol", reasoning_effort="low").build_request(
                "Material", purpose=ExtractionPurpose.MY_DATA_INTAKE_MATCHING)

    def test_sol_adapter_rejects_wrong_result_model(self):
        from services.ai_foundation.contracts import StructuredResult
        for model in ("eval0930-gpt-6-sol", None, "gpt-5.6-luna"):
            def wrong(request, **kwargs):
                return StructuredResult(request.request_id, request.schema_name,
                                        model, {"candidates": []}, 10, 5)
            adapter = MyDataExtractionAdapter(wrong, model="gpt-6-sol", reasoning_effort="low")
            with self.subTest(model=model), self.assertRaises(ExtractionError) as error:
                adapter.extract("Material", allowed_fields=self.FIELDS)
            self.assertEqual(error.exception.code, "model_mismatch")

if __name__ == "__main__":
    unittest.main()
