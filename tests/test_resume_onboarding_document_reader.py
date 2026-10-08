"""Real bounded reader and process-lifetime contracts; no AI/provider calls."""
from __future__ import annotations

import ctypes
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from services.resume_intake_document_adapter import ResumeDocumentAdapter
from services.resume_intake_policy import selected_policy_for_tests
from services.resume_onboarding_document_reader import (
    ResumeDocumentReadError, ResumeOnboardingDocumentReader, _run_bounded_child,
    inventory_source, load_ocr_configuration,
)
from scripts.run_resume_onboarding_acceptance import _docx, _pdf


class ResumeOnboardingDocumentReaderTests(unittest.TestCase):
    def setUp(self):
        self.limits = selected_policy_for_tests().import_limits()
        with patch.dict(os.environ, {}, clear=True):
            self.reader = ResumeOnboardingDocumentReader()

    def test_literal_text_and_table_paragraphs_are_not_escaped_or_summarized(self):
        original = 'Experience\nEngineer, A & B Labs, 2020 to 2026.\nSupported a team; I did not manage it.\n'
        for content_type, data in [('text/plain', original.encode()),
                                   ('application/vnd.openxmlformats-officedocument.wordprocessingml.document', _docx(original))]:
            result = self.reader.read(content_type, data, limits=self.limits)
            self.assertEqual(result['text'], original.strip())
            self.assertTrue(result['complete'])
            self.assertNotIn('&amp;', result['text'])
            self.assertEqual(len(result['units']), 3)

    def test_repeat_wording_has_distinct_offset_bound_units(self):
        text = 'Experience\nFirst employer.\nSupported testing.\n\nSecond employer.\nSupported testing.'
        units = inventory_source(text)
        repeated = [u for u in units if u['text'] == 'Supported testing.']
        self.assertEqual(len(repeated), 2)
        self.assertNotEqual(repeated[0]['unit_id'], repeated[1]['unit_id'])
        for unit in units:
            self.assertEqual(text[unit['span_start']:unit['span_end']], unit['text'])

    def test_selectable_columns_and_all_pages_remain_accounted(self):
        columns = ['Experience\nFirst employer.\nFirst duties.\nFirst scope.',
                   'Experience\nSecond employer.\nSecond duties.\nSecond scope.']
        result = self.reader.read('application/pdf', _pdf([columns, ['Skills\nSQL.']]), limits=self.limits)
        self.assertEqual(len(result['pages']), 2)
        self.assertLess(result['text'].index('First scope.'), result['text'].index('Second employer.'))
        self.assertIn('SQL.', result['text'])
        self.assertTrue(result['complete'])

    @staticmethod
    def _rows_pdf(rows):
        """One page of positioned runs: (x, y, text). Mirrors how word processors place right-aligned dates."""
        from pypdf import PdfWriter
        from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
        writer = PdfWriter()
        page = writer.add_blank_page(612, 792)
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
                                 NameObject("/BaseFont"): NameObject("/Helvetica"),
                                 NameObject("/Encoding"): NameObject("/WinAnsiEncoding")})
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject(
            {NameObject("/F1"): writer._add_object(font)})})
        stream = DecodedStreamObject()
        stream.set_data("\n".join("BT /F1 10 Tf 1 0 0 1 %s %s Tm <%s> Tj ET" % (x, y, text.encode("cp1252").hex())
                                  for x, y, text in rows).encode("ascii"))
        page[NameObject("/Contents")] = writer._add_object(stream)
        output = io.BytesIO(); writer.write(output)
        return output.getvalue()

    def test_right_aligned_dates_stay_on_the_line_of_their_job(self):
        # Titles on the left, dates right-aligned on the same row: one column, never two.
        jobs = [("Systems Engineer, Alpha Labs", "Jan 2019 - Present"), ("Analyst, Beta Corp", "2014 - 2018"),
                ("Technician, Gamma Works", "Mar 2009 - Dec 2013"), ("Intern, Delta Group", "2008")]
        rows = []
        for index, (title, dates) in enumerate(jobs):
            y = 740 - index * 40
            rows += [(40, y, title), (600 - 5.2 * len(dates), y, dates),
                     (50, y - 14, "Built and maintained the reporting pipeline for the team.")]
        result = self.reader.read('application/pdf', self._rows_pdf(rows), limits=self.limits)
        lines = result['text'].split('\n')
        for title, dates in jobs:
            line = next(row for row in lines if title in row)
            self.assertIn(dates, line)
        self.assertFalse(lines[-1].strip() in {dates for _, dates in jobs})

    def test_equal_width_dates_are_still_not_a_second_column(self):
        # Identical-width dates do start at one x, but they are dates, not a column of text.
        rows = []
        for index in range(5):
            y = 740 - index * 30
            rows += [(40, y, "Role %d, Employer %d" % (index, index)), (480, y, "2015 - 2019")]
        result = self.reader.read('application/pdf', self._rows_pdf(rows), limits=self.limits)
        lines = result['text'].split('\n')
        for index in range(5):
            self.assertIn("2015 - 2019", next(row for row in lines if "Role %d," % index in row))

    def test_a_real_second_column_still_keeps_each_column_together(self):
        rows = []
        for index in range(5):
            y = 740 - index * 14
            rows += [(40, y, "Left line number %d of the first column." % index),
                     (330, y, "Right line number %d of the second column." % index)]
        text = self.reader.read('application/pdf', self._rows_pdf(rows), limits=self.limits)['text']
        self.assertLess(text.index("Left line number 4"), text.index("Right line number 0"))

    def test_image_only_page_without_ocr_is_explicitly_unreadable(self):
        from pypdf import PdfWriter
        writer = PdfWriter(); writer.add_blank_page(612, 792)
        data = io.BytesIO(); writer.write(data)
        result = self.reader.read('application/pdf', data.getvalue(), limits=self.limits)
        self.assertFalse(result['complete'])
        self.assertEqual(result['reason'], 'ocr_unavailable')
        self.assertEqual(result['pages'][0]['method'], 'unreadable')

    def test_encrypted_document_and_hostile_control_do_not_return_content(self):
        from pypdf import PdfWriter
        writer = PdfWriter(); writer.add_blank_page(612, 792); writer.encrypt('private')
        output = io.BytesIO(); writer.write(output)
        with self.assertRaisesRegex(ResumeDocumentReadError, 'encrypted_document'):
            self.reader.read('application/pdf', output.getvalue(), limits=self.limits)
        with self.assertRaisesRegex(ResumeDocumentReadError, 'hostile_characters'):
            self.reader.read('text/plain', b'One\x00Two', limits=self.limits)

    def test_overflow_refuses_instead_of_claiming_complete_partial_text(self):
        from dataclasses import replace
        with self.assertRaisesRegex(ResumeDocumentReadError, 'output_truncated'):
            self.reader.read('text/plain', b'This whole fact exceeds the limit.',
                             limits=replace(self.limits, max_extracted_units=10))

    def test_configuration_requires_path_and_closed_manifest(self):
        with self.assertRaisesRegex(ResumeDocumentReadError, 'ocr_configuration_invalid'):
            load_ocr_configuration({'schema_version': 1})
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'manifest.json'
            path.write_text('{"schema_version":1,"schema_version":1}')
            with self.assertRaisesRegex(ResumeDocumentReadError, 'ocr_configuration_invalid'):
                load_ocr_configuration(str(path))

    def test_default_adapter_captures_ocr_binding_at_first_parse(self):
        adapter = ResumeDocumentAdapter()
        with patch.dict(os.environ, {}, clear=True):
            result = adapter.parse('text/plain', b'Original complete words.', selected_policy_for_tests())
        self.assertTrue(result.ok)
        self.assertIsNotNone(adapter._reader)
        with patch.dict(os.environ, {'PEERSLATE_RESUME_OCR_CONFIGURATION': 'invalid-later-swap'}):
            second = adapter.parse('text/plain', b'Second original words.', selected_policy_for_tests())
        self.assertTrue(second.ok)
        self.assertIsNone(adapter._reader.configuration)

    def test_captured_manifest_cannot_be_replaced_with_a_new_valid_runtime(self):
        with patch('services.resume_onboarding_document_reader.load_ocr_configuration',
                   side_effect=[{'manifest_sha256':'original'}, {'manifest_sha256':'replacement'}]):
            reader = ResumeOnboardingDocumentReader(configuration='explicit-manifest-path')
            with self.assertRaisesRegex(ResumeDocumentReadError, 'ocr_dependency_changed'):
                reader.read('text/plain', b'Original words.', limits=self.limits)

    def test_docx_supplemental_text_is_kept_and_embedded_content_is_not_claimed_complete(self):
        import zipfile
        output = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(_docx('Main complete fact.'))) as original, zipfile.ZipFile(output, 'w') as changed:
            for name in original.namelist():
                changed.writestr(name, original.read(name))
            changed.writestr('word/header1.xml', '<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:r><w:t>Contact header words.</w:t></w:r><w:drawing/></w:p></w:hdr>')
        result = self.reader.read('application/vnd.openxmlformats-officedocument.wordprocessingml.document', output.getvalue(), limits=self.limits)
        self.assertIn('Contact header words.', result['text'])
        self.assertFalse(result['complete'])
        self.assertEqual(result['reason'], 'embedded_content_unreadable')

    def test_receipt_does_not_duplicate_mutable_ocr_token_text(self):
        from services.resume_intake_document_adapter import DocumentParseResult
        result = DocumentParseResult(True, True, 'extracted', None, 'private words', False,
            'application/pdf', 10, 'digest', 'Read.', pages=({'page':1,'method':'ocr','tokens':[{'text':'private words'}]},))
        self.assertNotIn('private words', json.dumps(result.as_receipt()))
        self.assertTrue(result.as_receipt()['ocr_used'])

    def test_timeout_terminates_descendant_and_reader_recovers(self):
        reader_path = Path(__import__('services.resume_onboarding_document_reader', fromlist=['x']).__file__).resolve()
        with tempfile.TemporaryDirectory(prefix='peerslate-reader-timeout-test-') as temporary:
            root = Path(temporary)
            worker = root / 'synthetic_worker.py'
            worker.write_text(
                'import runpy,subprocess,sys,time\nfrom pathlib import Path\n'
                f'boundary=runpy.run_path({str(reader_path)!r})\n'
                'job=boundary["_child_memory_boundary"](1024*1024*1024)\n'
                'child=subprocess.Popen([sys.executable,"-I","-B","-c","import time;time.sleep(120)"])\n'
                f'Path({str(root / "descendant.pid")!r}).write_text(str(child.pid))\n'
                'time.sleep(120)\n', encoding='utf-8')
            with self.assertRaisesRegex(ResumeDocumentReadError, 'extraction_deadline'):
                _run_bounded_child([sys.executable, '-I', '-B', str(worker)], root, 2)
            pid = int((root / 'descendant.pid').read_text())
            if os.name == 'nt':
                kernel = ctypes.WinDLL('kernel32', use_last_error=True)
                kernel.OpenProcess.restype = ctypes.c_void_p
                kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
                kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
                kernel.CloseHandle.argtypes = [ctypes.c_void_p]
                handle = kernel.OpenProcess(0x100000, False, pid)
                if handle:
                    try:
                        self.assertEqual(kernel.WaitForSingleObject(handle, 5000), 0)
                    finally:
                        kernel.CloseHandle(handle)
            else:
                status = Path(f'/proc/{pid}/stat')
                self.assertTrue(not status.exists() or status.read_text().split()[2] == 'Z')
        recovered = self.reader.read('text/plain', b'Reader recovered without retained work.', limits=self.limits)
        self.assertTrue(recovered['complete'])


if __name__ == '__main__':
    unittest.main()
