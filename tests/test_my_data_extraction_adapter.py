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


if __name__ == "__main__":
    unittest.main()
