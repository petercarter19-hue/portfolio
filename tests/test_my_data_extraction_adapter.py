"""Guide adapter admission and native identity; fake provider only."""
import unittest
from unittest.mock import Mock, patch

from services.ai_foundation.contracts import Audience, ExtractionPurpose, StructuredRequest, StructuredResult
from services.my_data_extraction_adapter import MyDataExtractionAdapter, ExtractionError, EXTRACTION_SCHEMA_NAME


class GuideAdapterAdmissionTests(unittest.TestCase):
    def adapter(self, effort="medium", output=24576):
        return MyDataExtractionAdapter(Mock(),model="gpt-6.1-sol",reasoning_effort=effort,maximum_output_tokens=output)

    def test_sol61_low_medium_adapter_uses_the_fixed_organize_allowance(self):
        for effort in ("low","medium"):
            with self.subTest(effort=effort):
                adapter = self.adapter(effort)
                self.assertEqual((adapter.model,adapter.reasoning_effort,adapter.maximum_output_tokens),
                                 ("gpt-6.1-sol",effort,24576))
                adapter._provider.assert_not_called()

    def test_other_sol61_efforts_and_malformed_allowances_are_refused_before_provider(self):
        for effort in ("high","xhigh","minimal",None,True):
            with self.subTest(effort=effort), self.assertRaises(ExtractionError):
                self.adapter(effort)
        for output in (True,24576.0,0,128001):
            with self.subTest(output=output), self.assertRaises(ExtractionError):
                self.adapter(output=output)

    def test_incumbent_default_stays_native_luna_low_128000(self):
        adapter = MyDataExtractionAdapter(Mock())
        self.assertEqual((adapter.model,adapter.reasoning_effort,adapter.maximum_output_tokens),("gpt-6-luna","low",128000))
        adapter._provider.assert_not_called()

    def test_sol61_missing_model_identity_is_refused_in_both_payload_paths(self):
        adapter = self.adapter()
        request = StructuredRequest(request_id="fictional-request",product="my_data_intake",
            purpose=ExtractionPurpose.MY_DATA_INTAKE_EXTRACTION,audience=Audience.OWNER,subject_key="fictional-owner",
            instructions="Fictional guard isolation",input_text="Fictional material",schema_name=EXTRACTION_SCHEMA_NAME,
            model_name="gpt-6-luna",reasoning_effort="low")
        # Isolate the result guard while the accepted core-variant PR is in CI.
        # No fixture bypasses a real provider, wire or paid-call boundary.
        result = StructuredResult(request_id=request.request_id,schema_name=EXTRACTION_SCHEMA_NAME,model_name=None,
            payload={"candidates":[]},input_tokens=1,output_tokens=1)
        for resume in (False,True):
            provider = Mock(return_value=result); adapter._provider = provider
            with self.subTest(resume=resume),patch.object(adapter,"build_request",return_value=request), \
                    self.assertRaisesRegex(ExtractionError,"model_mismatch"):
                if resume:
                    adapter._resume_payload("Fictional material",source_units=[])
                else:
                    adapter.extract("Fictional material",allowed_fields={})
            provider.assert_called_once()



class G12AddTargetRefusalTests(unittest.TestCase):
    """Bake-off G12: a new (add) outcome never targets an existing listed record."""
    SHORTLIST = [{"record_key": "rec-1", "record_type": "role", "values": {}}]

    def test_plain_extraction_refuses_a_new_outcome_carrying_a_listed_match(self):
        from services.my_data_extraction_adapter import validate_extraction_payload
        text = "I led eight or nine people at Cedar Systems"
        raw = {"record_type": "role", "values": {"employer_name": "Cedar Systems"}, "outcome": "new",
               "span_start": 30, "span_end": len(text), "quote": "Cedar Systems", "match_reference": "rec-1"}
        fields = {"role": frozenset({"role_title", "employer_name"})}
        with self.assertRaises(ExtractionError) as refused:
            validate_extraction_payload({"candidates": [dict(raw)]}, text=text, allowed_fields=fields,
                                        shortlist=self.SHORTLIST)
        self.assertEqual(refused.exception.code, "new_needs_no_match")
        accepted = validate_extraction_payload({"candidates": [dict(raw, match_reference=None)]}, text=text,
                                               allowed_fields=fields, shortlist=self.SHORTLIST)
        self.assertEqual((accepted[0].outcome, accepted[0].match_reference), ("new", None))

    def test_resume_organize_rejects_only_that_candidate_and_keeps_its_units_unplaced(self):
        from services.my_data_extraction_adapter import RESUME_REJECTION_RULES, organize_resume_extraction
        from services.resume_intake_service import EDITOR_FIELDS
        from services.resume_onboarding_document_reader import inventory_source
        from tests.test_resume_onboarding_coverage import complete_resume_candidate
        text = "Experience\nEngineer, Cedar Systems, 2019-2021\nLed eight or nine people.\nSkills\nSQL."
        units = inventory_source(text, document=True)
        content = [unit for unit in units if unit["kind"] == "content"]
        role = complete_resume_candidate("role", {"role_title": "Engineer", "employer_name": "Cedar Systems"},
                                         content[0]["text"], content[:2], "Experience")
        role["match_reference"] = "rec-1"
        skill = complete_resume_candidate("skill", {"name": "SQL"}, "SQL.", content[2:], "Skills")
        organization = organize_resume_extraction({"candidates": [role, skill]}, text=text, source_units=units,
                                                  allowed_fields=EDITOR_FIELDS, shortlist=self.SHORTLIST)
        self.assertEqual([row["code"] for row in organization.rejections], ["new_needs_no_match"])
        # No role is made from the refused candidate; its lines stay visible as unplaced wording.
        self.assertNotIn("role", [draft["record_type"] for draft in organization.drafts])
        self.assertEqual([draft["record_type"] for draft in organization.drafts if draft["record_type"] != "unspecified"],
                         ["skill"])
        self.assertTrue({unit["unit_id"] for unit in content[:2]} <= set(organization.unplaced_unit_ids))
        self.assertTrue(all(draft["match_reference"] is None for draft in organization.drafts))
        self.assertEqual(RESUME_REJECTION_RULES["new_needs_no_match"], "matching")


if __name__ == "__main__":
    unittest.main()
