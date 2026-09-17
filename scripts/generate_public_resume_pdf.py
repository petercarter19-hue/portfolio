"""Rebuild Pete's published one-page résumé PDF from its accepted wording.

The former hand-assembled PDF had a broken xref and let long lines run past
the right page edge. This generator keeps the same text and order, wraps words
inside letter-page margins, and lets pypdf write the PDF structure.
"""

from __future__ import annotations

import argparse
import textwrap
from io import BytesIO
from pathlib import Path

from pypdf import PdfWriter
from pypdf._codecs.core_font_metrics import CORE_FONT_METRICS
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


PAGE_WIDTH = 612
PAGE_HEIGHT = 792
LEFT_MARGIN = 50
RIGHT_MARGIN = 50
BOTTOM_MARGIN = 50
TOP = 752
MAX_LINE_CHARACTERS = 96
OUTPUT = Path(__file__).resolve().parents[1] / "static/files/pete-carter-resume.pdf"

# These are the published PDF's original text lines, not a new résumé source.
# Empty entries keep the existing section breaks. Do not silently edit facts
# here to reconcile another profile or the private résumé editor.
RESUME_LINES = (
    "Pete Carter",
    "Systems Engineer | Technical Leader | MBSE & Sustainment",
    "Athens, Alabama | Huntsville Area | LinkedIn: https://www.linkedin.com/in/pete-carter19",
    "",
    "Professional Summary",
    "Systems engineer with experience across sustainment, requirements, technical coordination, reliability, MBSE, contractor oversight, and AI-enabled portfolio tools.",
    "Connects structured engineering thinking with practical execution so teams can move complex work from uncertainty to measurable outcomes.",
    "",
    "Career Impact",
    "- Supported more than $36M in contract oversight scope.",
    "- Reduced critical MICAP conditions from 16 to zero.",
    "- Improved repair and testing performance by 70%.",
    "- Reduced missing-part conditions by 52%.",
    "- Supported seven major aircraft platforms.",
    "- Completed graduate work with a 4.0 GPA.",
    "",
    "Experience",
    "U.S. Air Force | Systems Engineer / Lead Special Projects Engineer | 2021 - 2024",
    "- Supported navigation, sustainment, modernization, readiness, and special-project activities across multiple aircraft platforms.",
    "- Coordinated engineering, depot, supply, contractor, and program stakeholders.",
    "- Served in COR/ACOR responsibilities for engineering services support.",
    "",
    "L3Harris | Systems Effectiveness Engineer | 2024 - 2025",
    "- Supported reliability, maintainability, sustainment, provisioning, and MBSE-related work for complex defense systems.",
    "- Applied sustainment thinking across LORA, provisioning, spares, and supportability work.",
    "- Used systems modeling concepts to connect requirements, interfaces, and verification thinking.",
    "",
    "Northrop Grumman | Systems Engineer | 2025 - Present",
    "- Supports systems engineering work in a major defense environment.",
    "- Builds portfolio projects demonstrating Python, Flask, AI integration, structured data, and responsive frontend behavior.",
    "",
    "Core Skills",
    "Systems Engineering: requirements, architecture, interfaces, verification and validation, risk analysis, technical documentation, lifecycle thinking.",
    "MBSE / SysML: Cameo Systems Modeler, requirements packages, interface blocks, BDDs, verification relationships, logical and physical architecture.",
    "Sustainment / RAM: LORA, PSA, PSP, PSPL, FRACAS, depot analysis, GEIA-STD-0007B data, spares analysis.",
    "Leadership: contract oversight, senior-leadership briefings, contractor coordination, IPT support, schedule and performance tracking.",
    "AI / Software: Python, Flask, Claude API, HTML, CSS, JavaScript, JSON-backed portfolio content.",
    "",
    "Education",
    "B.S. Electrical Engineering, Kennesaw State University",
    "M.S. Engineering Management, University of Arkansas, 4.0 GPA",
    "Graduate Project Management Certificate, University of Arkansas",
    "Systems Engineering Ph.D., University of South Alabama, admitted with expected January 2027 start",
)

SECTION_HEADINGS = frozenset(
    {"Professional Summary", "Career Impact", "Experience", "Core Skills", "Education"}
)


def _pdf_string(value: str) -> str:
    """Escape ASCII text for a PDF literal string."""

    value.encode("ascii")
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _wrapped_lines(paragraph: str) -> list[str]:
    if not paragraph:
        return []
    lines = textwrap.wrap(
        paragraph,
        width=MAX_LINE_CHARACTERS,
        break_long_words=False,
        break_on_hyphens=False,
        subsequent_indent="  " if paragraph.startswith("- ") else "",
    )
    # Avoid stranding a single final word (the Ph.D. start-date line in the
    # accepted text is one such case) without changing the words or order.
    if len(lines) > 1 and len(lines[-1].split()) < 3:
        previous = lines[-2].split()
        final = lines[-1].split()
        while len(final) < 4 and len(previous) > 4:
            final.insert(0, previous.pop())
        lines[-2] = " ".join(previous)
        lines[-1] = ("  " if paragraph.startswith("- ") else "") + " ".join(final)
    return lines


def _font_resource(name: str) -> DictionaryObject:
    return DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject(name),
        }
    )


def _text_width(line: str, font: str, size: float) -> float:
    # pypdf ships Adobe's metrics for the same PDF core fonts used below.
    # Checking the actual glyph advances catches clipping even if prose or
    # font settings change while the character-count wrapper still passes.
    font_name = "Helvetica-Bold" if font == "F2" else "Helvetica"
    widths = CORE_FONT_METRICS[font_name].character_widths
    return size * sum(widths[character] for character in line) / 1000


def build_pdf() -> bytes:
    """Return a deterministic, structurally valid, single-page PDF."""

    writer = PdfWriter()
    page = writer.add_blank_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {
                    NameObject("/F1"): _font_resource("/Helvetica"),
                    NameObject("/F2"): _font_resource("/Helvetica-Bold"),
                }
            )
        }
    )

    y = TOP
    commands: list[str] = []
    for original in RESUME_LINES:
        if not original:
            y -= 8
            continue

        if original == "Pete Carter":
            font, size, leading = "F2", 15, 19
        elif original in SECTION_HEADINGS:
            font, size, leading = "F2", 10.5, 15
        else:
            font, size, leading = "F1", 9.3, 12

        for line in _wrapped_lines(original):
            if y < BOTTOM_MARGIN:
                raise ValueError("Résumé content exceeds the one-page printable area")
            if LEFT_MARGIN + _text_width(line, font, size) > PAGE_WIDTH - RIGHT_MARGIN:
                raise ValueError(f"Résumé line exceeds the right printable margin: {line}")
            commands.append(
                f"BT /{font} {size:g} Tf 1 0 0 1 {LEFT_MARGIN} {y:g} Tm "
                f"({_pdf_string(line)}) Tj ET"
            )
            y -= leading

    stream = DecodedStreamObject()
    stream.set_data(("\n".join(commands) + "\n").encode("ascii"))
    page.replace_contents(stream)
    writer.add_metadata({"/Title": "Pete Carter Resume"})
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify the checked-in PDF is current")
    args = parser.parse_args()
    generated = build_pdf()
    if args.check:
        if OUTPUT.read_bytes() != generated:
            parser.error(f"{OUTPUT} is not the current generated PDF")
    else:
        OUTPUT.write_bytes(generated)
        print(OUTPUT)


if __name__ == "__main__":
    main()
