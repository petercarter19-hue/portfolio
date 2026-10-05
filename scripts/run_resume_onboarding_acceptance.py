"""Materialize the frozen fictional layouts and run real local reader proof.

This never calls an AI provider or claims installed acceptance. Its
outputs live outside Git; expected record labels remain evaluator metadata.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import textwrap
import zipfile
import zlib
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SOURCES = ROOT / "tests/fixtures/resume_onboarding/representative_sources.json"
SOURCE_SHA256 = "a8d4ee62d10d30b197806815cf37be4e288625a389ae8d9b09b4190b2d47a460"


def _pdf(text_pages):
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, NumberObject, DecodedStreamObject
    writer = PdfWriter()
    for columns in text_pages:
        page = writer.add_blank_page(612, 792)
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                                 NameObject("/Subtype"): NameObject("/Type1"),
                                 NameObject("/BaseFont"): NameObject("/Helvetica"),
                                 NameObject("/Encoding"): NameObject("/WinAnsiEncoding")})
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
        operators = []
        for column, text in enumerate(columns):
            x, y = 40 + column * 285, 748
            for line in text.splitlines():
                for wrapped in textwrap.wrap(line, width=55 if len(columns) > 1 else 100) or [""]:
                    if y < 32:
                        raise ValueError("fixture page layout overflow")
                    encoded = wrapped.encode("cp1252", errors="strict")
                    operators.append(f"BT /F1 9 Tf 1 0 0 1 {x} {y} Tm <{encoded.hex()}> Tj ET")
                    y -= 12
        stream = DecodedStreamObject()
        stream.set_data("\n".join(operators).encode("ascii"))
        page[NameObject("/Contents")] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def _scan_image(text, rotated=False):
    # Authoring-only Pillow. The production reader uses no Pillow import.
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new("RGB", (2480, 3508), "white")
    draw = ImageDraw.Draw(image)
    font_path = Path(r"C:\Windows\Fonts\arial.ttf")
    if not font_path.is_file():
        raise RuntimeError("fixed Arial fixture font unavailable")
    font = ImageFont.truetype(str(font_path), 42)
    y = 100
    for line in text.splitlines():
        for wrapped in textwrap.wrap(line, width=90) or [""]:
            if y > 3400:
                raise ValueError("fixture scan page overflow")
            draw.text((110, y), wrapped, font=font, fill="black")
            y += 56
    return image.rotate(90, expand=True) if rotated else image


def _image_page(writer, image):
    from pypdf.generic import DictionaryObject, NameObject, NumberObject, EncodedStreamObject, DecodedStreamObject
    width, height = (792, 612) if image.width > image.height else (612, 792)
    page = writer.add_blank_page(width, height)
    stream = EncodedStreamObject()
    stream.update({NameObject("/Type"): NameObject("/XObject"), NameObject("/Subtype"): NameObject("/Image"),
                   NameObject("/Width"): NumberObject(image.width), NameObject("/Height"): NumberObject(image.height),
                   NameObject("/ColorSpace"): NameObject("/DeviceRGB"), NameObject("/BitsPerComponent"): NumberObject(8),
                   NameObject("/Filter"): NameObject("/FlateDecode")})
    stream._data = zlib.compress(image.tobytes())
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/XObject"): DictionaryObject({NameObject("/Scan"): writer._add_object(stream)})})
    content = DecodedStreamObject()
    content.set_data(f"q {width} 0 0 {height} 0 0 cm /Scan Do Q".encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(content)


def _scan_pdf(text, rotated=False, selectable_first=None):
    from pypdf import PdfReader, PdfWriter
    writer = PdfWriter()
    if selectable_first:
        writer.append(PdfReader(io.BytesIO(_pdf([[selectable_first]]))))
    image = _scan_image(text, rotated)
    try:
        _image_page(writer, image)
    finally:
        image.close()
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def _docx(text):
    ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    paragraphs = ['<w:p><w:r><w:t xml:space="preserve">' + escape(line) + '</w:t></w:r></w:p>' for line in text.splitlines()]
    # Real table cells, preserving paragraph order, without gold target labels.
    body = '<w:tbl>' + ''.join('<w:tr><w:tc>' + p + '</w:tc></w:tr>' for p in paragraphs) + '</w:tbl>'
    document = f'<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="{ns}"><w:body>{body}</w:body></w:document>'
    types = '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>'
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in (("[Content_Types].xml", types), ("word/document.xml", document)):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 4, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, content)
    return output.getvalue()


def materialize(output):
    raw = SOURCES.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("frozen fixture specification changed")
    corpus = json.loads(raw)
    if output.resolve().is_relative_to(ROOT):
        raise ValueError("acceptance output must be outside the source checkout")
    output.mkdir(parents=True, exist_ok=True)
    files = []
    for fixture in corpus["fixtures"]:
        text, format_name = fixture["source_text"], fixture["format"]
        if format_name == "txt":
            data, extension, content_type = text.encode("utf-8"), "txt", "text/plain"
        elif format_name == "docx":
            data, extension = _docx(text), "docx"
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else:
            extension, content_type = "pdf", "application/pdf"
            if fixture["id"] == "D08":
                split = text.index(fixture["units"][6]["source_text"])
                split = text.rfind("\n\n", 0, split) + 2
                data = _scan_pdf(text[split:], selectable_first=text[:split])
            elif format_name == "scanned_pdf":
                data = _scan_pdf(text, rotated=fixture["id"] == "D06")
            elif fixture["id"] in {"D01", "D05"}:
                blocks = text.split("\n\n")
                boundary = max(1, len(blocks) // 2)
                groups = ["\n\n".join(blocks[:boundary]), "\n\n".join(blocks[boundary:])]
                data = _pdf([groups] if fixture["id"] == "D05" else [[group] for group in groups])
            else:
                data = _pdf([[text]])
        path = output / (fixture["id"] + "." + extension)
        if path.exists() and path.read_bytes() != data:
            raise ValueError("materialized fixture changed: " + fixture["id"])
        path.write_bytes(data)
        files.append({"fixture": fixture["id"], "path": str(path.resolve()), "content_type": content_type,
                      "sha256": hashlib.sha256(data).hexdigest(), "expected_units": fixture["expected_unit_count"]})
    manifest = {"schema_version": 1, "synthetic": True, "source_sha256": SOURCE_SHA256, "files": files}
    (output / "materialized_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return corpus, manifest


def reader_smoke(corpus, manifest, configuration):
    from services.resume_onboarding_document_reader import ResumeOnboardingDocumentReader
    from services.resume_intake_policy import selected_policy_for_tests
    reader = ResumeOnboardingDocumentReader(configuration=configuration)
    results = []
    for fixture, descriptor in zip(corpus["fixtures"], manifest["files"]):
        result = reader.read(descriptor["content_type"], Path(descriptor["path"]).read_bytes(),
                             limits=selected_policy_for_tests().import_limits())
        normalized = re.sub(r"\s+", " ", result["text"])
        found = [unit["id"] for unit in fixture["units"] if re.sub(r"\s+", " ", unit["source_text"]) in normalized]
        results.append({"fixture": fixture["id"], "source_sha256": descriptor["sha256"],
                        "complete": result["complete"], "expected": fixture["expected_unit_count"],
                        "exact_units_found": found, "pages": result["pages"], "text": result["text"],
                        "source_units": result["units"], "ocr_configuration_sha256": result["ocr_configuration_sha256"]})
    return {"schema_version": 1, "reader_only": True, "AI_calls": 0, "placement": "not_run",
            "passed": all(r["complete"] and len(r["exact_units_found"]) == r["expected"] for r in results), "results": results}


def score_placement(corpus, manifest, evidence):
    """Score captured first responses; no gold labels enter the application.

    Evidence must be captured before corrections. Unknown, missing, duplicated
    and OCR-mismatched units keep their original zero point in the denominator.
    This evaluator does not turn a capture declaration into live-provider proof;
    the independent reviewer must verify the candidate/capture provenance.
    """
    if (type(evidence) is not dict or evidence.get('schema_version') != 1
            or evidence.get('first_pass_before_human_correction') is not True
            or not re.fullmatch(r'[0-9a-f]{40}', evidence.get('candidate_sha', ''))
            or type(evidence.get('fixtures')) is not list):
        raise ValueError('first-pass candidate evidence required')
    rows = evidence['fixtures']
    if len(rows) != len({r['fixture'] for r in rows}):
        raise ValueError('duplicate fixture capture')
    captures = {r['fixture']: r for r in rows}
    descriptors = {r['fixture']: r for r in manifest['files']}
    normalize = lambda text: re.sub(r'\s+', ' ', text or '').strip()
    scores = []
    for fixture in corpus['fixtures']:
        capture = captures.get(fixture['id']) or {}
        if capture and capture.get('source_sha256') != descriptors[fixture['id']]['sha256']:
            raise ValueError('capture bytes do not match frozen document: ' + fixture['id'])
        accounting = capture.get('source_accounting') or []
        if len(accounting) > 1:
            raise ValueError('one fresh isolated source per fixture required')
        source = accounting[0] if accounting else {}
        units = [u for u in source.get('source_units') or [] if u.get('kind') == 'content']
        units.sort(key=lambda u: u['span_start'])
        proposals = capture.get('proposals') or []
        if any((p.get('resume_conversation_v1') or {}).get('revision_of') for p in proposals):
            raise ValueError('corrected proposals are not first-pass evidence')
        matched, occurrences = {}, {}
        for gold in fixture['units']:
            text = normalize(gold['source_text'])
            ordinal = occurrences.get(text, 0); occurrences[text] = ordinal + 1
            found = [u for u in units if text in normalize(u.get('text'))]
            matched[gold['id']] = found[ordinal] if ordinal < len(found) else None
        record_anchors = {}
        for gold in fixture['units']:
            record_anchors.setdefault(gold['expected_record_id'], matched[gold['id']])
        for gold in fixture['units']:
            unit, expected_anchor = matched[gold['id']], record_anchors[gold['expected_record_id']]
            claims = [p for p in proposals if unit is not None
                and unit['unit_id'] in (p.get('resume_conversation_v1') or {}).get('unit_ids', [])
                and (p.get('binding') or {}).get('source_key') == source.get('source_key')]
            proposal = claims[0] if len(claims) == 1 else {}
            metadata = proposal.get('resume_conversation_v1') or {}
            correct = bool(unit and expected_anchor and len(claims) == 1
                and proposal.get('confidence') == 'certain'
                and proposal.get('record_type') == gold['expected_record_type']
                and metadata.get('presentation_section') == gold['expected_section']
                and metadata.get('record_anchor') == expected_anchor['unit_id'])
            scores.append({'unit_id':gold['id'], 'expected_record_id':gold['expected_record_id'],
                'expected_section':gold['expected_section'], 'correct':correct,
                'proposal_key':proposal.get('proposal_key'), 'source_unit_id':(unit or {}).get('unit_id'),
                'reason':'correct' if correct else ('source_not_exactly_matched' if unit is None else
                    'missing_or_duplicate_proposal' if len(claims) != 1 else 'section_record_or_confidence_mismatch')})
    if len(scores) != 100:
        raise ValueError('frozen denominator must remain 100')
    correct = sum(r['correct'] for r in scores)
    return {'schema_version':1, 'candidate_sha':evidence['candidate_sha'], 'first_pass':True,
        'denominator':100, 'correct':correct, 'required':95, 'passed':correct >= 95,
        'source_sha256':SOURCE_SHA256, 'capture_provenance':'requires_independent_verification',
        'AI_calls':0, 'installed_acceptance':'not_established_by_this_evaluator', 'units':scores}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--materialize", action="store_true")
    parser.add_argument("--reader-smoke", action="store_true")
    parser.add_argument("--ocr-configuration")
    parser.add_argument('--placement-evidence', type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(ROOT):
        raise ValueError('acceptance output must be outside the source checkout')
    if args.placement_evidence:
        raw = SOURCES.read_bytes()
        if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
            raise ValueError('frozen fixture specification changed')
        corpus = json.loads(raw)
        manifest = json.loads((args.output / 'materialized_manifest.json').read_text(encoding='utf-8'))
        if manifest.get('source_sha256') != SOURCE_SHA256:
            raise ValueError('materialized fixture authority mismatch')
        for row in manifest['files']:
            if hashlib.sha256(Path(row['path']).read_bytes()).hexdigest() != row['sha256']:
                raise ValueError('frozen document bytes changed')
        result = score_placement(corpus, manifest, json.loads(args.placement_evidence.read_text(encoding='utf-8')))
        (args.output / 'placement_report.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps({k:result[k] for k in ('candidate_sha','denominator','correct','required','passed','AI_calls')}))
        return 0 if result['passed'] else 1
    corpus, manifest = materialize(args.output)
    if args.reader_smoke:
        result = reader_smoke(corpus, manifest, args.ocr_configuration)
        (args.output / "reader_smoke.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps({"passed": result["passed"], "expected_units": 100,
                          "exact_units_found": sum(len(r["exact_units_found"]) for r in result["results"]),
                          "AI_calls": 0, "output": str(args.output.resolve())}))
        return 0 if result["passed"] else 1
    print(json.dumps(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
