#!/usr/bin/env python3
"""Build and verify owner-approved Bible v2.8 and Roadmap v2.7.

The builder performs bounded OOXML edits over the current controlled DOCX
packages. It preserves all unmodified package parts, styles, media, numbering,
headers/footers, and historical material; replaces active contradictory
paragraphs through exact anchors; appends the owner-approved amendment source;
marks the cached table of contents dirty; and verifies required/forbidden text.

Run from the repository root with the bundled document runtime:

  <bundled-python> docs/initiatives/PS-GOV-JOURNAL-SYSTEM-001/build_authority_documents.py
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
import zipfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from lxml import etree


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
GOV = ROOT / "docs" / "governance"

BIBLE_SOURCE = GOV / "PeerSlate_Company_and_Product_Bible_v2.7.docx"
BIBLE_OUTPUT = GOV / "PeerSlate_Company_and_Product_Bible_v2.8.docx"
BIBLE_AMENDMENT = HERE / "02_BIBLE_V2_8_AMENDMENT_SOURCE.md"

ROADMAP_SOURCE = GOV / "PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.6.docx"
ROADMAP_OUTPUT = GOV / "PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.7.docx"
ROADMAP_AMENDMENT = HERE / "03_ROADMAP_V2_7_AMENDMENT_SOURCE.md"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
CP_NS = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DC_NS = "http://purl.org/dc/elements/1.1/"
DCTERMS_NS = "http://purl.org/dc/terms/"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
NS = {"w": W_NS, "wp": WP_NS}


def qn(local: str) -> str:
    return f"{{{W_NS}}}{local}"


def paragraph_text(paragraph: etree._Element) -> str:
    return "".join(node.text or "" for node in paragraph.xpath(".//w:t", namespaces=NS))


def set_paragraph_text(paragraph: etree._Element, value: str) -> None:
    text_nodes = paragraph.xpath(".//w:t", namespaces=NS)
    if not text_nodes:
        run = etree.SubElement(paragraph, qn("r"))
        node = etree.SubElement(run, qn("t"))
        text_nodes = [node]
    text_nodes[0].text = value
    text_nodes[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    for node in text_nodes[1:]:
        node.text = ""


def replace_exact_paragraphs(root: etree._Element, replacements: dict[str, str]) -> None:
    paragraphs = root.xpath(".//w:p", namespaces=NS)
    by_text: dict[str, list[etree._Element]] = {}
    for paragraph in paragraphs:
        by_text.setdefault(paragraph_text(paragraph), []).append(paragraph)
    for old, new in replacements.items():
        matches = by_text.get(old, [])
        if len(matches) != 1:
            raise ValueError(
                f"expected exactly one paragraph anchor, found {len(matches)}: {old!r}"
            )
        set_paragraph_text(matches[0], new)


def replace_exact_table_rows(
    root: etree._Element,
    replacements: list[tuple[tuple[str, ...], tuple[str, ...]]],
) -> None:
    """Replace uniquely anchored table rows without changing unrelated Hold cells."""
    rows = root.xpath(".//w:tr", namespaces=NS)
    for old_cells, new_cells in replacements:
        if len(old_cells) != len(new_cells):
            raise ValueError(f"table row replacement length mismatch: {old_cells!r}")
        matches: list[etree._Element] = []
        for row in rows:
            cells = row.xpath("./w:tc", namespaces=NS)
            values = tuple(
                "".join(node.text or "" for node in cell.xpath(".//w:t", namespaces=NS))
                for cell in cells
            )
            if values == old_cells:
                matches.append(row)
        if len(matches) != 1:
            raise ValueError(
                f"expected exactly one table-row anchor, found {len(matches)}: {old_cells!r}"
            )
        cells = matches[0].xpath("./w:tc", namespaces=NS)
        for cell, value in zip(cells, new_cells, strict=True):
            paragraphs = cell.xpath("./w:p", namespaces=NS)
            if not paragraphs:
                paragraph = etree.SubElement(cell, qn("p"))
            else:
                paragraph = paragraphs[0]
            set_paragraph_text(paragraph, value)
            for extra in paragraphs[1:]:
                set_paragraph_text(extra, "")


def replace_repeated_exact_paragraphs(
    root: etree._Element,
    replacements: dict[str, tuple[str, int]],
) -> None:
    """Replace a known repeated caption/anchor and verify its exact count."""
    paragraphs = root.xpath(".//w:p", namespaces=NS)
    for old, (new, expected_count) in replacements.items():
        matches = [p for p in paragraphs if paragraph_text(p) == old]
        if len(matches) != expected_count:
            raise ValueError(
                f"expected {expected_count} repeated paragraph anchors, "
                f"found {len(matches)}: {old!r}"
            )
        for paragraph in matches:
            set_paragraph_text(paragraph, new)


def mark_exact_table_header_rows(
    root: etree._Element,
    header_rows: list[tuple[str, ...]],
) -> None:
    """Mark uniquely anchored data-table first rows as repeating headers.

    The controlled source documents also use one-cell and card-style tables for
    visual layout. Those are deliberately not marked as data-table headers.
    """
    rows = root.xpath(".//w:tr", namespaces=NS)
    for expected_cells in header_rows:
        matches: list[etree._Element] = []
        for row in rows:
            cells = row.xpath("./w:tc", namespaces=NS)
            values = tuple(
                "".join(node.text or "" for node in cell.xpath(".//w:t", namespaces=NS))
                for cell in cells
            )
            if values == expected_cells:
                matches.append(row)
        if len(matches) != 1:
            raise ValueError(
                f"expected exactly one data-table header row, "
                f"found {len(matches)}: {expected_cells!r}"
            )
        row = matches[0]
        row_properties = row.find(qn("trPr"))
        if row_properties is None:
            row_properties = etree.Element(qn("trPr"))
            row.insert(0, row_properties)
        if row_properties.find(qn("tblHeader")) is None:
            header = etree.SubElement(row_properties, qn("tblHeader"))
            header.set(qn("val"), "true")


def replace_exact_drawing_metadata(
    root: etree._Element,
    replacements: list[tuple[str, str, str | None]],
) -> None:
    """Replace uniquely anchored image descriptions and optional titles."""
    drawings = root.xpath(".//wp:docPr", namespaces=NS)
    for old_description, new_description, new_title in replacements:
        matches = [node for node in drawings if node.get("descr") == old_description]
        if len(matches) != 1:
            raise ValueError(
                f"expected exactly one drawing description anchor, "
                f"found {len(matches)}: {old_description!r}"
            )
        matches[0].set("descr", new_description)
        if new_title is not None:
            matches[0].set("title", new_title)


def new_paragraph(text: str, style: str | None = None, page_break: bool = False) -> etree._Element:
    paragraph = etree.Element(qn("p"), nsmap={"w": W_NS})
    if style or page_break:
        ppr = etree.SubElement(paragraph, qn("pPr"))
        if style:
            pstyle = etree.SubElement(ppr, qn("pStyle"))
            pstyle.set(qn("val"), style)
        if page_break:
            etree.SubElement(ppr, qn("pageBreakBefore"))
    run = etree.SubElement(paragraph, qn("r"))
    text_node = etree.SubElement(run, qn("t"))
    text_node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    text_node.text = text
    return paragraph


def clean_markdown(value: str) -> str:
    value = value.replace("**", "").replace("`", "")
    return re.sub(r"\s+", " ", value).strip()


def amendment_elements(path: Path, appendix_title: str) -> list[etree._Element]:
    lines = path.read_text(encoding="utf-8").splitlines()
    elements: list[etree._Element] = [
        new_paragraph(appendix_title, "Heading1", page_break=True)
    ]
    buffer: list[str] = []

    def flush() -> None:
        if not buffer:
            return
        elements.append(new_paragraph(clean_markdown(" ".join(buffer))))
        buffer.clear()

    for index, raw in enumerate(lines):
        line = raw.strip()
        if index == 0 and line.startswith("# "):
            continue
        if not line:
            flush()
            continue
        if line.startswith("### "):
            flush()
            elements.append(new_paragraph(clean_markdown(line[4:]), "Heading3"))
            continue
        if line.startswith("## "):
            flush()
            elements.append(new_paragraph(clean_markdown(line[3:]), "Heading2"))
            continue
        if line.startswith("- "):
            flush()
            body = clean_markdown(line[2:])
            style = "Requirement" if body.startswith("PS-") else "ListBullet"
            elements.append(new_paragraph(body, style))
            continue
        if re.match(r"^\d+\.\s", line):
            flush()
            body = clean_markdown(re.sub(r"^\d+\.\s*", "", line))
            elements.append(new_paragraph(body, "ListNumber"))
            continue
        buffer.append(line)
    flush()
    return elements


def append_before_final_sectpr(root: etree._Element, elements: list[etree._Element]) -> None:
    body = root.find(qn("body"))
    if body is None:
        raise ValueError("document body not found")
    sectpr = body.find(qn("sectPr"))
    insert_at = len(body) if sectpr is None else body.index(sectpr)
    for element in elements:
        body.insert(insert_at, element)
        insert_at += 1


def mark_toc_dirty(root: etree._Element) -> None:
    fields = root.xpath('.//w:fldChar[@w:fldCharType="begin"]', namespaces=NS)
    if not fields:
        raise ValueError("TOC/field begin marker not found")
    # Mark all field begins dirty. Word will refresh the TOC and other cached
    # navigational fields without altering visible body content in this build.
    for field in fields:
        field.set(qn("dirty"), "true")


def update_part_text(payload: bytes, replacements: dict[str, str]) -> bytes:
    root = etree.fromstring(payload)
    replace_exact_paragraphs(root, replacements)
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def update_core_properties(payload: bytes, title: str) -> bytes:
    root = etree.fromstring(payload)
    title_nodes = root.xpath("./dc:title", namespaces={"dc": DC_NS})
    if title_nodes:
        title_nodes[0].text = title
    modified_nodes = root.xpath("./dcterms:modified", namespaces={"dcterms": DCTERMS_NS})
    if modified_nodes:
        modified_nodes[0].text = datetime(2026, 7, 20, 23, 59, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
        modified_nodes[0].set(f"{{{XSI_NS}}}type", "dcterms:W3CDTF")
    revision_nodes = root.xpath("./cp:revision", namespaces={"cp": CP_NS})
    if revision_nodes:
        try:
            revision_nodes[0].text = str(int(revision_nodes[0].text or "0") + 1)
        except ValueError:
            revision_nodes[0].text = "1"
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def build(
    source: Path,
    output: Path,
    amendment: Path,
    appendix_title: str,
    replacements: dict[str, str],
    part_replacements: dict[str, dict[str, str]],
    core_title: str,
    required: list[str],
    forbidden: list[str],
    table_row_replacements: list[tuple[tuple[str, ...], tuple[str, ...]]] | None = None,
    repeated_replacements: dict[str, tuple[str, int]] | None = None,
    data_table_header_rows: list[tuple[str, ...]] | None = None,
    drawing_metadata_replacements: list[tuple[str, str, str | None]] | None = None,
) -> None:
    with zipfile.ZipFile(source) as reader:
        infos = reader.infolist()
        parts = {info.filename: reader.read(info.filename) for info in infos}

    document_root = etree.fromstring(parts["word/document.xml"])
    replace_exact_table_rows(document_root, table_row_replacements or [])
    replace_repeated_exact_paragraphs(document_root, repeated_replacements or {})
    replace_exact_paragraphs(document_root, replacements)
    mark_exact_table_header_rows(document_root, data_table_header_rows or [])
    replace_exact_drawing_metadata(
        document_root, drawing_metadata_replacements or []
    )
    append_before_final_sectpr(
        document_root, amendment_elements(amendment, appendix_title)
    )
    mark_toc_dirty(document_root)
    parts["word/document.xml"] = etree.tostring(
        document_root,
        xml_declaration=True,
        encoding="UTF-8",
        standalone=True,
    )

    for part, mapping in part_replacements.items():
        parts[part] = update_part_text(parts[part], mapping)
    if "docProps/core.xml" in parts:
        parts["docProps/core.xml"] = update_core_properties(
            parts["docProps/core.xml"], core_title
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{output.stem}-", suffix=".docx", dir=output.parent
    )
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as writer:
            for info in infos:
                writer.writestr(info, parts.pop(info.filename))
            for name, payload in parts.items():
                writer.writestr(name, payload)
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()

    verify_docx(output, required, forbidden)


def verify_docx(path: Path, required: list[str], forbidden: list[str]) -> None:
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f"corrupt DOCX member {bad} in {path}")
        xml_parts = []
        for name in archive.namelist():
            if name.endswith((".xml", ".rels")):
                payload = archive.read(name)
                etree.fromstring(payload)
                if name.endswith(".xml"):
                    root = etree.fromstring(payload)
                    xml_parts.extend(root.xpath(".//text()"))
        text = "\n".join(str(value) for value in xml_parts)
        attribute_text = "\n".join(
            value
            for name in archive.namelist()
            if name.endswith(".xml")
            for node in [etree.fromstring(archive.read(name))]
            for value in node.xpath("//@*")
        )
    for value in required:
        if value not in text:
            raise ValueError(f"required text missing from {path.name}: {value!r}")
    for value in forbidden:
        if value in text or value in attribute_text:
            raise ValueError(f"forbidden current text remains in {path.name}: {value!r}")


BIBLE_REPLACEMENTS = {
    "v2.7 - Connected System and Return-Value Authority (CURRENT)":
        "v2.8 - Universal Capture, One Journal, and Trusted Return Authority (CURRENT)",
    "CURRENT AND LOCKED - APPROVED BY THE OWNER ON JULY 20, 2026; SUPERSEDES v2.6":
        "CURRENT AND LOCKED - APPROVED BY THE OWNER ON JULY 20, 2026; SUPERSEDES v2.7",
    "v2.6 Projects authority + July 20 owner connected-system and return-value decision":
        "v2.7 connected-system authority + July 20 universal Capture, one-Journal, return-value, Ask Slate, and messaging decisions",
    "This release tightens the Bible into PeerSlate’s constitutional source of truth, separates changeable implementation material into controlled companion documents, and integrates the strongest product-vision decisions without deleting the v1.5.1 source.":
        "This release preserves PeerSlate's constitutional foundation and reconciles universal Capture, the one Journal, My Story, trusted return value, Ask Slate AI, messaging, and early legal/site readiness without changing runtime behavior.",
    "Approval note: v2.7 is CURRENT and LOCKED. Pete approved it on July 20, 2026 and the activation change named it in CURRENT_BASELINE.yaml, so it supersedes v2.6, which remains in the repository as a historical decision record. It preserves the entire v2.6 constitution - the verified production baseline, the visual-integrity covenant, the member-directed Story covenant, and the Projects covenant - and adds one governing decision: PeerSlate needs a stronger visible trunk, not more destinations. Every major room should feel like a focused use of the same member-owned life record, connected by canonical reference and member-directed action rather than copied facts or a new navigation forest.":
        "Approval note: v2.8 is CURRENT and LOCKED. Pete approved and directed its Azure activation on July 20, 2026. It supersedes v2.7, which remains preserved as history; retains the verified production, visual-integrity, Story, Projects, and connected-system covenants; and makes the corrected product loop controlling: Capture anywhere, Save one private Moment, find it in the one Journal, then use that same Moment anywhere now or later by governed reference.",
    "This table updates automatically. If page numbers do not appear, click inside it and press F9 (or right-click and choose \"Update Field\"). The v2.7 release adds Section 19 'Rejected for the current program' and Appendices M and N; refresh this field to list them with correct page numbers.":
        "This table updates automatically. If page numbers do not appear, click inside it and press F9 (or right-click and choose \"Update Field\"). The v2.8 release adds Appendix O; refresh this field to list it with correct page numbers.",
    "Authority: v2.7 is CURRENT and controlling. Pete approved it on July 20, 2026 and the activation change named it in CURRENT_BASELINE.yaml, so it supersedes v2.6. Prior Bible versions, including v2.6, remain preserved as historical decision records.":
        "Authority: v2.8 is CURRENT and controlling. Pete approved and directed its Azure activation on July 20, 2026, so it supersedes v2.7. Prior Bible versions, including v2.7, remain preserved as historical decision records.",
    "Build one coherent owner system with two unmistakable modes: a private owner workspace and a public or permissioned Slate. Prove the complete Capture → review → Journal → optional projection loop with two real accounts before expanding public surfaces, career matching, or marketplace concepts.":
        "Build one coherent owner system with two unmistakable modes: a private owner workspace and a public or permissioned Slate. Prove Capture anywhere → Save Moment → immediate private Journal → optional governed projection with two real accounts before expanding public surfaces, career matching, or marketplace concepts.",
    "Do not optimize time-on-site, streaks, public popularity, application volume, or recruiter convenience at the person’s expense.":
        "Do not optimize time-on-site, punitive daily-reset streaks, public popularity, application volume, or recruiter convenience at the person’s expense. Private truthful Momentum and purposeful acknowledgements may support the member without pressure.",
    "Use finite feeds, meaningful responses, deliberate sharing, and quiet return value—not streaks, trends, vanity counts, or infinite scroll. Quiet return value explicitly includes resurfaced history, Slate Replay, and one useful next step.":
        "Use finite feeds, meaningful responses, deliberate sharing, and quiet return value—not punitive reset/loss mechanics, trends, vanity counts, or infinite scroll. Quiet return value includes resurfaced history, Replay, private Momentum, useful prompts or rituals, source-linked observations, and one optional next step.",
    "PeerSlate may create return value through useful memory, preparation, gentle prompts, and visible progress, but shall not use guilt, loss framing, public streaks, punitive recovery, artificial scarcity, or popularity pressure.":
        "PeerSlate may create return value through useful memory, preparation, gentle prompts and rituals, private Momentum, purposeful acknowledgements, and visible progress, but shall not use guilt, reset or loss framing, public streaks, punitive recovery, artificial scarcity, meaningless rewards, or popularity pressure.",
    "Moment, Journal entry, role, project, outcome, skill, goal, source link, audience":
        "Moment, role, project, outcome, skill, goal, source link, audience, governed projection",
    "Canonical objects": "Governed system objects",
    "Journal entry": "Journal presentation metadata",
    "The private-first home for a reviewed Moment and its context, relationships, media, audience, and status.":
        "Optional curation, organization, display, purpose, and audience/publication state referencing a canonical Moment; it never copies the Moment body. Journal membership itself is derived.",
    "A member should not rewrite the same experience for Journal, Story, Work, a résumé, an interview answer, and a public post. The system preserves one source-linked canonical record and lets the member deliberately project it into different views. A projection may have purpose-specific wording, but it must remain traceable to the canonical record and cannot silently fork the facts.":
        "A member saves one source-linked canonical Moment and finds it immediately in the one Journal. Story, Work, résumé, interview, Feed, Project, Board, public Journal, and messaging may later use governed references or purpose-specific projection wording that remains traceable and cannot silently fork the facts.",
    "Bottom navigation: Home · Journal · Capture · Slate · More":
        "Signed-in navigation includes Journal as a core domain; exact routes, labels, grouping, and order remain open. Capture is a persistent global action and never a destination.",
    "Save privately in Journal.":
        "Choose Save Moment. The private Moment is immediately available in the owner's one Journal without a second Add to Journal action.",
    "Story should not display every Journal entry or imitate a recent-activity feed. It is a member-curated narrative built from the same canonical records, with unequal weight and multiple depths: a one-sentence year, defining Moment, primary highlights, month navigation, progress and outcomes, and optional deeper material.":
        "Story should not display every Journal Moment or imitate a recent-activity feed. It is a finite member-authored narrative built from the same canonical records, with unequal weight and multiple depths; Journal remains the complete chronological working record.",
    "Use clarity and calm confirmation—not confetti, streaks, or inflated praise.":
        "Use clarity and calm confirmation—not confetti, punitive reset/loss mechanics, meaningless rewards, or inflated praise. Sparse truthful private acknowledgements are permitted.",
    "PS-CORE-IA-003  PeerSlate shall provide a mobile-first composition with Home, Journal, Capture, Slate, and More, while preserving equivalent essential capability on desktop.":
        "PS-CORE-IA-003  PeerSlate shall provide a mobile-first composition with Journal as a core domain and Capture as a persistent global action rather than a destination; the exact route map remains open and desktop preserves equivalent essential capability.",
    "PS-CORE-FR-001  Universal Capture shall create an owner-scoped private draft before placement, sharing, or publication.":
        "PS-CORE-FR-001  Universal Capture shall provide one context-preserving composer and one explicit Save Moment action that creates a private source-linked canonical member-saved Moment before placement, sharing, or publication; Journal membership is immediate and derived.",
    "Whether a soft consistency visualization is useful without becoming a streak.":
        "Exact names, formulae, and visual treatment for private non-resetting Momentum and purposeful acknowledgements after anti-pressure user validation.",
    "Hard or loss-framed streaks.":
        "Daily-reset, hard, punitive, or loss-framed streak mechanics.",
    "Points, badges, levels, public consistency counts, or trophy cabinets.":
        "Meaningless points, levels, public consistency counts, leaderboards, artificial scarcity, or trophy cabinets. Sparse private acknowledgements with disclosed truthful criteria remain permitted.",
    "Journal remains a deliberate hold, not an accidental blocker and not an implied cancellation.":
        "The Journal hold is lifted. Architecture is controlling; runtime work remains deliberately gated and must not become an accidental blocker for independent packages.",
    "The connective patterns, mode and state behavior, and logical contract are maintained in the Experience System and the Architecture and Data Standard. As of this candidate, no connective pattern is implemented, assigned, deployed, enabled, or live. Slate Spine, Backstory Drawer, Studio Return Ticket, Then and Now, Focus Themes, and Progress Keepsakes have no manager, writer, branch, schema, route, accepted visual authority, or release. Preservation in this Bible is not implementation authorization.":
        "Connected patterns remain governed inside existing rooms. PS-JOURNAL-001 and PS-RETURN-VALUE-001 now provide controlling architecture for universal Capture, the one Journal, Replay/resurfacing, Momentum, Prompt/Ritual, Noticed/Mirror, Focus Themes, and Keepsakes; none is thereby claimed implemented, deployed, enabled, or live. Slate Spine, Backstory Drawer, Studio Return Ticket, and runtime slices still require assigned packages, visual authority, tests, and release evidence.",
    "The five July 18, 2026 owner-experience storyboard boards are the approved controlling reference for the signed-in dark-theme experience: Owner Home; Capture a Moment; Journal and My Slate; Story and Living Resume as connected projections; and Interview Studio / Moment Lab.":
        "The July 18, 2026 owner-experience storyboard components remain approved visual-quality references for the signed-in dark-theme experience. They do not define five required destinations: the Capture a Moment board controls the in-context composer’s quality and states, not a standalone Capture page; Journal/My Slate, Story/Living Resume, Home, and Studio retain their separately governed roles.",
    "PS-CORE-IA-006  The signed-in owner experience shall implement the approved five-board Deep Navy Gold visual baseline, preserving its hierarchy, state clarity, premium layered composition, and responsive accessibility across Home, Capture, Journal/My Slate, connected projections, and Studio/Moment Lab.":
        "PS-CORE-IA-006  The signed-in owner experience shall preserve the approved Deep Navy Gold component quality, hierarchy, state clarity, premium layered composition, and responsive accessibility. The visual references do not lock a five-destination shell; Capture is an in-context action/composer and the exact route map remains open.",
    "The five July 18 owner-experience storyboard boards are the approved controlling design reference for the dark-theme owner workspace. They shall be stored in the authoritative repository and cited by owner-experience initiatives.":
        "The July 18 owner-experience storyboard components are approved visual-quality references for the dark-theme owner workspace. Initiative packages shall cite the relevant component authority and state whether it represents a route, a view, or an in-context action; the set does not lock navigation.",
    "The following five boards are the approved controlling visual reference for the signed-in owner experience. They define intended composition, hierarchy, tone, quality, and relationship between desktop and mobile. They do not authorize illustrative sample facts as production data. The original image files shall be stored in the authoritative repository under a versioned design-reference path and cited from initiative packages.":
        "The following storyboard components are approved visual references for composition, hierarchy, tone, quality, and desktop/mobile behavior. They do not authorize sample facts, five required destinations, or a Capture route. Initiative packages shall cite the relevant component under a versioned design-reference path and record any superseding information-architecture decision.",
    "Can it strengthen Home, Capture, Journal, Slate, Work, Story, Studio, or Settings instead of adding another top-level destination?":
        "Can it strengthen Home, the in-context Capture composer, Journal, Slate, Work, Story, Studio, or Settings instead of adding another top-level destination?",
    "Member intelligence, Capture follow-up, Replay, Moment Lab, Next Chapter, and connected insights should appear inside Home, Capture, Journal, Slate, Work, Story, and Studio. They should not become a new global navigation forest.":
        "Member intelligence, Capture follow-up, Replay, Moment Lab, Next Chapter, and connected insights should appear inside Home, the in-context Capture composer, Journal, Slate, Work, Story, and Studio. They should not become a new global navigation forest.",
    "FitSlate is preserved as a possible future member-first extension of Qualification Alignment, Résumé Creator, Studio, Next Chapter, and Owner AI. It may not receive active design, prototype, architecture, backlog, or release status until the owner foundation, canonical data, authorization, core capture loop, Slate Mirror, and validation evidence are strong enough to support it.":
        "FitSlate is preserved as a possible future member-first extension of Qualification Alignment, Résumé Creator, Studio, Next Chapter, and Ask Slate AI. It may not receive active design, prototype, architecture, backlog, or release status until the owner foundation, canonical data, authorization, one-Journal loop, Slate Mirror, and validation evidence are strong enough to support it.",
    "PS-CORE-FR-002  PeerSlate shall preserve the original member input and shall show editable structured proposals before canonical promotion.":
        "PS-CORE-FR-002  PeerSlate shall preserve the original member input and allow member-authored text to Save Moment immediately. Applicable voice/transcript correction occurs inline; optional structured or AI proposals remain editable, separately identified, and unable to delay, replace, or silently rewrite the member-saved canonical Moment.",
    "Approved Capture baseline: voice or text enters one path, review precedes canonical promotion, privacy is visible, and Use This Moment follows capture.":
        "Approved Capture baseline: voice and text are first-class paths into one in-context composer; privacy is visible; applicable transcript correction and optional proposals are inline; Save Moment creates the private canonical Moment without an AI/review gate; Use This Moment follows as an optional action.",
    "Create the member review and promotion boundary from original Capture to a source-linked canonical Moment.":
        "Unify the released source and canonical-Moment foundations behind one Save Moment operation. Preserve original/revision evidence, allow applicable transcript correction inline, and keep optional proposals separate so neither review nor AI promotion delays member-authored text.",
    "A Capture record is the private owner-scoped original/source intake. It is not automatically a reviewed canonical Moment. Original input must remain preserved through correction, promotion, placement, export, and deletion policy.":
        "A technical Capture/source record may preserve private owner-scoped original input and revisions. It is not a user-facing destination. Save Moment orchestrates that provenance with one private canonical Moment in the member's authored or reviewed language; placement, export, and deletion retain their governed lifecycle.",
    "Member records a real Moment and reaches a private reviewed draft without a tour.":
        "Member opens Capture in context, records a real Moment, chooses Save Moment once, and finds the private canonical Moment immediately in only their own Journal without a tour.",
    "The Capture row is an original/source intake. Review and canonical Moment promotion remain separate work.":
        "The deployed Capture/source row and canonical Moment row remain separate technical foundations. The target Save Moment orchestration presents one member commit and does not expose a mandatory review/promotion journey.",
    "The broader safe path is split into PS-CAPTURE-002 lifecycle controls, PS-MOMENT-001 review and canonical promotion, and PS-PLACEMENT-001 create-once/place-many references.":
        "PS-CAPTURE-002, PS-MOMENT-001, and PS-PLACEMENT-001 remain released lifecycle, canonical-record, and exact-reference foundations. PS-JOURNAL-001 now unifies their safe value behind Save Moment without copying facts or requiring the member to traverse the historical package boundaries.",
    "Original Source, then Member Review, then Canonical Slate, then Authorized Relationship or Placement, then Focused Room or Projection, then Activation, then Outcome, then Return Value, then New Contribution.":
        "Capture action, then Save Moment with preserved source/version and one private canonical Moment, then derived owner Journal, then optional authorized relationship/projection, then activation/outcome/return value, then new contribution.",
    "Review and canonical":
        "Save Moment and canonical truth",
    "Original preserved; proposal reviewed; member-confirmed Moment and related canonical objects.":
        "Original/version evidence preserved; member-authored or member-reviewed language saved immediately; optional proposals remain separate; exact canonical objects and relationships stay governed.",
    "Trusted-session owner resolution; captures table; private draft state; server-enforced audience; transaction; audit-safe event; failure recovery.":
        "Trusted-session owner resolution; source/revision preservation; idempotent Save Moment transaction; private canonical Moment; derived owner-Journal query; server-enforced audience; audit-safe event; failure recovery.",
    "Mobile text/voice Capture with visible private state, cancel, transcript correction, retry, offline-safe draft explanation, and next-step review.":
        "In-context mobile text/voice composer with visible private state, cancel, transcript correction, retry, offline-safe explanation, one Save Moment action, origin return, and optional next-use shortcuts.",
    "Unit save-state tests; integration transaction test; cross-user isolation; publication-negative tests; offline/retry; accessibility; telemetry without payload.":
        "Unit Save Moment and derived-membership tests; idempotent integration transaction; cross-user isolation; publication-negative tests; offline/retry; accessibility; telemetry without payload.",
    "Pete and Danielle independently capture a Moment, explain that it is private, correct it, save it, and find the review step without a product tour.":
        "Pete and Danielle independently open Capture from eligible contexts, explain the private default, preserve or correct their language inline, choose Save Moment once, return to context, and find the saved Moment immediately in only their own Journal without an Add to Journal step.",
    "Not a conventional résumé builder, although it may create purpose-specific résumé exports from confirmed records.":
        "Not a conventional résumé builder, although it may create purpose-specific résumé exports from member-saved canonical records and governed projections.",
    "One connected Slate is not achieved only by sharing a database. The experience must make the relationship visible. Original sources enter a reviewable pipeline; confirmed records connect through governed relationships and exact-version placements; focused rooms receive only authorized context; member actions create reviewable projections or outcomes; and useful history returns through finite Home, Replay, resurfacing, and preparation. Each layer remains separately governed so connection never erases truth boundaries.":
        "One connected Slate is not achieved only by sharing a database. The experience must make the relationship visible. Save Moment preserves the authorized source/version and creates one private member-saved canonical Moment immediately; optional transcript correction and proposals remain inline and non-blocking. Governed relationships and exact-version references connect focused rooms to authorized context, while reviewable projections, outcomes, Replay, resurfacing, and preparation remain separately controlled so connection never erases truth boundaries.",
    "PeerSlate connects not only across rooms but across time. When sufficient confirmed history exists, a room may reveal an earlier related Moment, a meaningful change, an unfinished thread, or a future revisit. Temporal cues must be source-linked, dismissible, non-diagnostic, and free of guilt.":
        "PeerSlate connects not only across rooms but across time. When sufficient trusted member-saved history exists, a room may reveal an earlier related Moment, a meaningful change, an unfinished thread, or a future revisit. Temporal cues must be source-linked, dismissible, non-diagnostic, and free of guilt.",
    "After a member reviews a Moment, PeerSlate should show a small number of useful, context-aware actions rather than sending the member into another dashboard. The action must be truthful, reversible, and source-linked.":
        "After a member saves a Moment, PeerSlate may show a small finite set of useful, truthful, reversible, source-linked shortcuts without sending the member into another dashboard. Use This Moment shall also expose a complete accessible chooser of every currently supported and authorized destination or purpose; shortcuts may not hide eligible choices, and unavailable or future choices may not be implied live.",
    "Next Chapter begins with the member’s confirmed history and chosen direction. It should answer: What do I already have? What transfers? What is genuinely missing? What small real-world experiment could I run next? Qualification Alignment may help compare confirmed experience to a member-supplied role or standard, but it must remain transparent, private-first, and separate from opaque fit scoring.":
        "Next Chapter begins with the member’s trusted member-saved history and chosen direction. It should answer: What do I already have? What transfers? What is genuinely missing? What small real-world experiment could I run next? Qualification Alignment may help compare member-saved canonical experience to a member-supplied role or standard, but it must remain transparent, private-first, and separate from opaque fit scoring.",
    "Capture remains the common entry. A member confirms a Moment and then explicitly links its exact version to a Project through the governed Placement boundary.":
        "Capture remains the common entry. A member chooses Save Moment once and may later explicitly link an exact saved Moment version to a Project through the governed Placement boundary.",
    "Preserved v1.5.1 voice-to-value loop: voice and text enter the same reviewable proposal architecture.":
        "Historical v1.5.1 voice-to-value diagram retained as source context only. Bible v2.8 supersedes its mandatory proposal/review sequence: Type and Speak use the in-context composer, Save Moment creates the private canonical Moment, and applicable transcript correction or optional AI proposals remain inline and non-blocking.",
    "PeerSlate is expression-first and modality-flexible. Voice and text are first-class paths into the same ownership, provenance, review, correction, privacy, lifecycle, and activation architecture. Voice may become a signature medium only after it becomes a usable object: editable transcript, clear privacy state, source link, review, correction, search or retrieval support, deletion behavior, and text fallback. Voice-derived emotional cues may be offered only as optional, humble observations and never as diagnosis.":
        "PeerSlate is expression-first and modality-flexible. Voice and text are first-class paths into the same ownership, provenance, privacy, Save Moment, lifecycle, and activation architecture. Applicable voice transcription correction remains inline; optional proposals never delay or replace the member-saved canonical Moment. Voice may become a signature medium only when it is usable: editable transcript, clear privacy/source state, correction, search or retrieval support, deletion behavior, provider-failure handling, and text fallback. Voice-derived emotional cues may be offered only as optional, humble observations and never as diagnosis.",
    "Use confirmed structured relationships, canonical records, dates, activity, and full-text retrieval before adding semantic retrieval.":
        "Use trusted member-saved canonical records, explicit structured relationships, dates, activity, and full-text retrieval before adding semantic retrieval.",
    "PS-CORE-IA-016  When sufficient confirmed history exists, PeerSlate shall support finite, source-linked temporal continuity through resurfacing, Then and Now, Replay, or a related next step without guilt or diagnostic claims.":
        "PS-CORE-IA-016  When sufficient trusted member-saved history exists, PeerSlate shall support finite, source-linked temporal continuity through resurfacing, Then and Now, Replay, or a related next step without guilt or diagnostic claims.",
    "PS-CORE-FR-003  PeerSlate shall permit a reviewed Moment to connect to multiple approved uses without duplicating or silently diverging canonical facts.":
        "PS-CORE-FR-003  PeerSlate shall permit an exact member-saved Moment version to connect to multiple approved uses without duplicating or silently diverging canonical facts.",
    "PS-CORE-FR-010  Retained voice Capture shall enter the same review and lifecycle architecture as text and shall provide editable transcript, visible privacy and source state, correction, deletion, and text fallback; optional generated titles or summaries shall remain reviewable proposals.":
        "PS-CORE-FR-010  Retained voice Capture shall enter the same Save Moment and lifecycle architecture as text and shall provide editable transcript, visible privacy and source state, applicable inline correction, deletion, provider-failure handling, and text fallback; optional generated titles or summaries remain reviewable proposals and cannot block the saved canonical Moment.",
    "AI interpretations, résumé language, public Story copy, Feed copy, and Studio outputs may never overwrite confirmed facts, source material, dates, accomplishments, identity, ownership, audience, or publication state.":
        "AI interpretations, résumé language, public Story copy, Feed copy, and Studio outputs may never overwrite member-saved or explicitly accepted canonical facts, source material, dates, accomplishments, identity, ownership, audience, or publication state.",
    "Approved connected-view baseline: cinematic Story and disciplined Living Resume remain distinct projections of one confirmed Slate.":
        "Approved connected-view baseline: cinematic Story and disciplined Living Resume remain distinct governed projections of one member-owned canonical Slate.",
    "Figure N-1. The connected-system loop, preserved as source/peerslate_connected_system_architecture.png with the owner handoff.":
        "Figure N-1. Historical connected-system diagram preserved as source context. Its member-review gate is superseded by Appendix O: Capture action, Save Moment, one private canonical Moment, and derived Journal precede optional governed use.",
}


BIBLE_TABLE_ROW_REPLACEMENTS = [
    (
        (
            "Owner workspace",
            "Capture, understand, organize, prepare, control, correct, and decide",
            "Home, Capture, Journal, My Slate preview, Studio, Settings",
            "Another member’s private data; ambiguous publication; fake completion",
        ),
        (
            "Owner workspace",
            "Capture in context, understand, organize, prepare, control, correct, and decide",
            "Journal-centered owner domains plus a persistent/contextual Capture action; exact route map open",
            "Another member’s private data; ambiguous publication; fake completion",
        ),
    ),
    (
        (
            "1Capture",
            "2AI follow-up",
            "3Private draft",
            "4Member review",
            "5Journal",
            "6Optional projection",
        ),
        (
            "1 Capture action",
            "2 Preserve/review source inline",
            "3 Save Moment",
            "4 One private canonical Moment",
            "5 Derived one Journal",
            "6 Optional governed use/projection",
        ),
    ),
    (
        (
            "HOLD",
            "PS-JOURNAL-001",
            "Journal UI remains on hold until explicit owner authorization; backend contracts may prepare for it without shipping the Journal experience.",
        ),
        (
            "ARCHITECTURE CURRENT / RUNTIME GATED",
            "PS-JOURNAL-001",
            "The owner-authorized architecture is controlling; implementation begins only through its private-core route, data, authorization, visual, migration, rollback, accessibility, and two-member gates.",
        ),
    ),
    (
        (
            "Journal",
            "Explicitly on hold.",
            "Do not start Journal UI until owner authorization. Do not block source lifecycle, canonical Moment, projection, résumé, or Studio work that is architecturally independent.",
        ),
        (
            "Journal",
            "Architecture current; runtime gated.",
            "Start Journal product work only through PS-JOURNAL-001. Preserve independent source lifecycle, canonical Moment, projection, résumé, and Studio work.",
        ),
    ),
    (
        (
            "Canonical record",
            "Store confirmed facts and structured relationships once",
            "Moment, Journal entry, role, project, outcome, skill, goal, source link, audience",
            "Member-confirmed truth",
        ),
        (
            "Canonical record",
            "Store member-authored or explicitly accepted facts and structured relationships once",
            "Moment, Journal entry, role, project, outcome, skill, goal, source link, audience",
            "Member-owned canonical truth",
        ),
    ),
    (
        (
            "Requirement",
            "Universal Capture shall create an owner-scoped private draft before placement, sharing, or publication.",
        ),
        (
            "Requirement",
            "Save Moment shall atomically preserve the authorized source/version, create one private member-saved canonical Moment, and make it immediately available through derived owner-Journal membership before any optional placement, sharing, or publication.",
        ),
    ),
]


BIBLE_REPEATED_REPLACEMENTS = {
    "Figure H-2. Capture a Moment": (
        "Figure H-2. In-context Capture composer (visual reference, not a destination)",
        1,
    ),
    "Figure H-2. Capture a Moment39": (
        "Figure H-2. In-context Capture composer (visual reference, not a destination)39",
        1,
    ),
}


ROADMAP_REPLACEMENTS = {
    "v2.6 - Connected-System Sequencing (CURRENT)":
        "v2.7 - Journal-System Execution Sequence (CURRENT)",
    "CURRENT AND LOCKED - APPROVED BY THE OWNER ON JULY 20, 2026; SUPERSEDES v2.5":
        "CURRENT AND LOCKED - APPROVED BY THE OWNER ON JULY 20, 2026; SUPERSEDES v2.6",
    "v2.5 sequencing + Bible v2.7 + July 20 connected-system decision":
        "v2.6 sequencing + Bible v2.8 + July 20 universal Capture, one-Journal, return-value, Ask Slate, and messaging decisions",
    "Approval note: this v2.6 release preserves every v2.5 phase, package, status, release record, and production claim exactly, and adds one sequencing amendment for the connected-system and return-value direction. It advances nothing to Complete, starts nothing, and changes no live status. Pete approved it on July 20, 2026, so it supersedes v2.5, which remains in the repository as a historical record.":
        "Approval note: this v2.7 release preserves verified production and historical package evidence, supersedes inherited Capture-destination and Journal-hold sequencing, activates the detailed architecture packages, and adds a bounded execution path for private Journal, return value, Ask Slate, audience Journal, Story, and messaging. It changes no runtime status by itself. Pete approved and directed Azure activation on July 20, 2026, so it supersedes v2.6.",
    "Roadmap authority: v2.6 is CURRENT and controlling. Pete approved it on July 20, 2026 and CURRENT_BASELINE.yaml names it, so it supersedes v2.5. Historical package IDs and release evidence remain preserved. PS-STORY-COMPOSER-001, PS-PROJECTS-001, PS-ASK-PETE-AI-001, and every connective package named in Appendix G are planned or candidate work, not active.":
        "Roadmap authority: v2.7 is CURRENT and controlling. Pete approved and directed its Azure activation on July 20, 2026, so it supersedes v2.6. Historical package IDs and release evidence remain preserved. PS-JOURNAL-001 architecture is active; PS-RETURN-VALUE-001, PS-ASK-SLATE-AI-001, PS-MESSAGING-001, PS-STORY-COMPOSER-001, and PS-PROJECTS-001 remain staged as recorded and are not thereby live.",
    "Non-text Capture through shared contracts; Use This Moment; deliberate publication; two-member connection; finite Feed; owner Home; My Slate preview; later Journal when explicitly restarted":
        "Universal Capture through shared contracts; Save Moment; immediate private Journal; Use This Moment; deliberate publication; two-member authorization; finite Feed; owner Home; curated/viewer Journal after its gates",
    "Journal UI is on hold; FitSlate remains tabled":
        "Journal architecture is active and runtime-gated; FitSlate remains tabled",
    "Users, identities, profiles, Moments, Journal entries, roles, projects, outcomes, relationships, audience":
        "Users, identities, profiles, sources, Moments, Journal presentation metadata, roles, projects, outcomes, relationships, audience",
    "Primary public and authenticated navigation use one canonical model. Mobile uses Home · Journal · Capture · Slate · More.":
        "Public and authenticated navigation use one coherent model. Journal is core and Capture is a persistent action, never a destination; exact desktop/mobile routes, labels, grouping, and order remain an owner-approved route-map gate.",
    "Capture CTAs enter Capture—not a broad Feed or concept shell.":
        "Capture actions open the same context-preserving universal composer in place; they do not navigate to a Capture destination, Feed, or concept shell.",
    "Define canonical schema and migrations for users, identities, profiles, settings, onboarding, Moments/captures, Journal entries, sources/provenance, roles/projects/outcomes, relationships, audience grants, publication state, AI drafts/insights, jobs, activity/audit-safe events, and deletion/revocation.":
        "Define canonical schema and migrations for users, identities, profiles, settings, onboarding, sources/revisions, Moments, Journal presentation metadata without copied facts, roles/projects/outcomes, relationships, audience grants, publication state, AI drafts/insights, messages when activated, jobs, activity/audit-safe events, and deletion/revocation.",
    "Phase 5 has a verified private text-intake source slice under historical PS-CAPTURE-001. Review, correction lifecycle, canonical Moment promotion, placement references, and Journal are not complete. Journal UI remains on explicit hold.":
        "Phase 5 has verified private text/Voice source, Moment, and Placement foundations. The owner has lifted the Journal hold and approved universal Capture plus derived one-Journal architecture; runtime orchestration, Journal UI, curation/audience views, migration, and validation remain incomplete and gated.",
    "Prove the complete Capture → review → canonical Journal vertical slice with text as the reference and accessibility fallback.":
        "Prove Capture anywhere → one idempotent Save Moment operation → immediate private owner Journal, with Type and Speak first-class, source/version preservation, accessibility, and AI/provider fallback.",
    "Persistent Capture is visible in authenticated mobile and desktop shells.":
        "A persistent Capture action is visible in eligible authenticated mobile and desktop shells and opens the context-preserving universal composer without becoming a destination.",
    "PS-JOURNAL-001  Journal shall provide owner-scoped reviewed records with source, original language, relationships, lifecycle, search, edit, and deletion behavior.":
        "PS-JOURNAL-001  The owner's one Journal shall derive membership from every eligible member-saved canonical Moment and provide source/original language, versions, relationships, lifecycle, search/filter, edit, curation, export, and deletion without a copied Journal body or Add to Journal gate.",
    "Each explains that the initial draft is private, corrects at least one field, preserves their original language, and saves to Journal.":
        "Each explains that the Moment is private, preserves/corrects original language as needed, chooses Save Moment once, and finds it immediately in their own Journal without an Add to Journal step.",
    "Voice and text produce the same private draft/review/Journal behavior and the same audience controls.":
        "Voice and text are first-class paths through the same in-context Save Moment, source/version, immediate private Journal, lifecycle, audience, failure, and accessibility architecture.",
    "Reuse Capture contracts, states, provenance, review, and Journal promotion.":
        "Reuse source, Voice, Moment, Placement, provenance, revision, and lifecycle foundations behind one universal composer and Save Moment orchestration; Journal membership is derived, not promoted by a second action.",
    "PS-COMMUNITY-001  The current program shall exclude streaks, trends, vanity popularity, infinite scroll, job/news rails, polls, and simulated community density.":
        "PS-COMMUNITY-001  Community shall exclude punitive reset/loss mechanics, public consistency comparison, trends, vanity popularity, infinite scroll, job/news rails, filler polls, and simulated density. Private truthful Momentum belongs to the owner return-value system, not Community ranking.",
    "Choose the next authorized slice: PS-CAPTURE-MEDIA-001 or owner Home/viewer-mode work. Keep PS-JOURNAL-001 on hold until explicit restart.":
        "The Journal restart is complete. Sequence PS-JOURNAL-001 audit/allocation and private core without overlapping active Owner Home or Capture Media writers; keep media enablement and homepage parity separately gated.",
    "Do not build a streak meter, points, badges, or a loss-framed return mechanic.":
        "Do not build daily-reset/loss-framed streaks, public rank, meaningless points/levels, scarcity, or trophy spam. Private non-resetting Momentum and sparse purposeful acknowledgements with disclosed truthful criteria are permitted.",
    "Review, canonical Moment, placement; Journal hold":
        "Released source/Moment/Placement foundations; Journal architecture active, runtime gated",
    "It leaves the Journal experience on hold without freezing the architectural work that Journal will eventually consume.":
        "It preserved reusable foundations; the owner has now lifted the Journal hold and activated the controlling universal-Capture/one-Journal architecture without claiming runtime completion.",
    "At the next gate, choose between non-text Capture and owner Home/viewer-mode implementation; Journal remains on hold until expressly restarted.":
        "At the next gate, allocate the private Journal core around active Owner Home and Capture Media lanes, assign one writer, and preserve separate visual, migration, rollback, and enablement gates.",
    "Private return-value engine, candidate PS-RETURN-VALUE-001 - first slice: one obvious Capture action; one small prompt or check-in; one recent and one resurfaced Moment; one concise source-linked observation when warranted; one next step; and welcome-back behavior after absence with no loss framing. Do not start with a streak meter. Validate that memory, usefulness, and one clear next action create return value first.":
        "PS-RETURN-VALUE-001 architecture is committed and runtime staged. Build preferences/pause/suppression/provenance first, then one safe resurfaced Moment, one optional prompt/check-in, private non-resetting Momentum, one next step, and welcome-back without loss. Add member-invoked Replay next; add source-linked Noticed/Mirror only after sufficient trusted history. Purposeful private acknowledgements are permitted under disclosed real criteria; punitive reset/loss/public-ranking mechanics are not.",
    "The approved five-board owner-experience set is now the controlling dark-theme target for the signed-in product. The near-term roadmap shall implement that owner quality through shared components and real states. The broad public website remains substantially intact while the Living Resume and Interview Studio receive focused authorized refinements. A later public visual convergence initiative will bring the logged-out product/pitch homepage and public projections to comparable quality after the owner shell and core private loop are stable.":
        "The approved owner-experience storyboard components remain the controlling dark-theme quality bar, not a five-destination information architecture. Capture a Moment is an in-context composer reference rather than a page. Near-term packages shall map each relevant component to real states and separately approved routes; public projection convergence remains independently gated.",
    "PS-IA-002  The mobile authenticated shell shall expose Home, Journal, Capture, Slate, and More and shall not merely shrink desktop navigation.":
        "PS-IA-002  The mobile authenticated shell shall keep Journal central and expose a persistent/contextual Capture action without making Capture a destination. Exact route labels, grouping, and order remain an owner-approved route-map gate; mobile shall not merely shrink desktop navigation.",
    "Responsive shell prototype across homepage, signed-in Home, Journal, Capture, My Slate, viewer profile, Studio, and Settings.":
        "Responsive shell prototype across homepage, signed-in Journal-centered domains, the in-context Capture composer, My Slate/viewer projections, Studio, and Settings; exact route map remains open.",
    "Signed-in Home becomes the finite owner orientation point with Capture, drafts/review, recent/resurfaced Moment, one permitted update, and one next step.":
        "Signed-in Home may be a finite owner orientation point with a Capture action, recent/resurfaced Moment, one permitted update, and one next step. It shall not become a required Capture destination or expose a separate draft-to-Journal promotion gate.",
    "No streak, guilt, popularity, fabricated certainty, or automatic publication is introduced.":
        "No punitive reset/loss streak, guilt, public popularity pressure, fabricated certainty, or automatic publication is introduced. Optional member-chosen daily or non-daily private Momentum and sparse truthful acknowledgements remain permitted.",
    "Prototype the target mobile/desktop shell and the text-first Capture vertical slice with honest states.":
        "Prototype the target mobile/desktop shell and default-off text-first in-context composer/private-Journal slice with honest states; do not claim universal coverage until every approved eligible-origin matrix entry passes.",
    "PeerSlate saves raw input privately, shows an editable structured proposal, asks only necessary follow-up, and requires explicit approval before canonical promotion or publication.":
        "PeerSlate preserves authorized source input and lets member-authored text Save Moment immediately as one private canonical Moment. Applicable voice/transcript correction and optional structured or AI proposals stay inline, editable, and separately identified; they cannot delay or replace Save Moment. Publication remains a separate explicit action.",
    "PS-CAPTURE-002  Capture shall preserve the original input and shall display an editable structured proposal before canonical promotion.":
        "PS-CAPTURE-002  Capture shall preserve original input and support inline transcript correction where applicable. Member-authored text may Save Moment immediately; optional structured or AI proposals shall not become a mandatory pre-save promotion gate.",
    "Integration tests from capture request through private persistence, review, canonical promotion, Journal retrieval, edit, and deletion.":
        "Integration tests from in-context composer through idempotent Save Moment, source/version preservation, immediate derived owner-Journal retrieval, edit/version, archive/restore, export, deletion, provider failure, and two-member isolation; optional proposal failure cannot block or replace the saved Moment.",
    "No raw-text duplication; no Journal UI until restarted; no auth rewrite.":
        "No raw-text duplication; Journal work only through the PS-JOURNAL-001 private-core and later audience gates; no auth rewrite.",
    "Text/voice/photo/file intake, original capture, private draft, review, canonical promotion, relationships":
        "Text/voice/photo/file input, preserved source/version, Save Moment, one private canonical Moment, derived Journal, optional governed relationships",
    "Nothing else matters as much if a member cannot quickly capture a real Moment, preserve the original, understand the system’s proposal, correct it, save privately, connect it, and later find it. This slice becomes the reference architecture for voice, intelligence, Story, Work, Studio, and sharing.":
        "Nothing else matters as much if a member cannot open Capture in context, preserve the authorized source/version, Save Moment once in their own language, find it immediately in the private Journal, and optionally use it later. Applicable transcript correction and optional AI proposals stay inline and non-blocking. This slice becomes the reference architecture for voice, intelligence, Story, Work, Studio, and sharing.",
    "Save raw private draft first; ask only questions that materially improve value or safety.":
        "Save the member-authored private Moment when Save Moment is chosen; ask only non-blocking questions that materially improve value or safety, and never require optional AI enrichment before save.",
    "Explicit review/promotion state and negative tests.":
        "Explicit Save Moment, source/version, optional-proposal, and negative side-effect tests.",
    "PS-VOICE-001  Voice Capture shall enter the same owner-scoped private draft, review, canonical promotion, provenance, and audience pipeline as text.":
        "PS-VOICE-001  Voice and text shall remain first-class paths through the same owner-scoped privacy, provenance, inline correction where applicable, Save Moment, canonical Moment, derived Journal, audience, and failure architecture. Voice transcription review shall not turn member-authored text into a mandatory promotion gate.",
    "Capture review and canonical Moment promotion":
        "Save Moment orchestration over released source and canonical Moment foundations",
    "Original source → editable proposal → member-confirmed source-linked Moment":
        "Preserved source/version + member-authored or reviewed language → Save Moment → one private source-linked canonical Moment; optional proposal remains separate",
    "Reviewed canonical Moment boundary with original source preservation.":
        "Canonical Moment and source/version foundations preserved; target Save Moment removes mandatory promotion from the member journey.",
    "The next backend step is not direct placement of raw capture text into every surface. The safe sequence is original Capture source → lifecycle and correction controls → member review → source-linked canonical Moment → placement/projection references.":
        "The next backend step is not direct placement of raw input into every surface. The safe target is an in-context Capture action → Save Moment with preserved source/version and one private canonical Moment → derived owner Journal → optional exact-reference placement/projection. Applicable correction is inline; optional proposals cannot delay save.",
    "Canonical Moment review, placement references, then non-text sources or owner Home.":
        "Released canonical Moment and placement-reference foundations, then bounded non-text-source or owner-Home work; Journal private-core work is separately assigned.",
    "Run PS-MOMENT-001 to introduce member review and canonical Moment promotion.":
        "Historical sequence completed PS-MOMENT-001 to establish the source-linked canonical Moment foundation. New member-facing work follows Save Moment and one-Journal authority rather than recreating the promotion gate.",
    "The member can connect the reviewed Moment to a role, project, goal, person, skill, earlier Moment, or leave it unplaced.":
        "After Save Moment, the member can connect an exact saved canonical Moment version to a role, project, goal, person, skill, earlier Moment, or leave it unplaced.",
    "Mobile-first Capture prototype with text, private-state reassurance, follow-up, review, correction, cancel, retry, and optional relationship selection.":
        "Mobile-first in-context Type/Speak composer prototype with private-state reassurance, applicable inline transcript correction, cancel/retry, one Save Moment action, origin return, and post-save optional next-use actions.",
    "Do not build speech before the safe text Capture/review pipeline is proven.":
        "Do not expand speech before the safe text source/version, idempotent Save Moment, immediate derived private-Journal, provider-failure, and accessibility path is proven; Type and Speak remain first-class target inputs.",
    "Do not implement Then and Now before confirmed history, source authorization, contradiction handling, and correction behavior are mature.":
        "Do not implement Then and Now before sufficient trusted member-saved history, source authorization, contradiction handling, and correction behavior are mature.",
}


ROADMAP_REPEATED_REPLACEMENTS = {
    "PS-CAPTURE-001  Universal Capture shall create an owner-scoped private draft before placement, sharing, or publication.": (
        "PS-JRN-MOM-001  Save Moment shall atomically preserve the authorized source/version, create one private member-saved canonical Moment, and make it immediately available through derived owner-Journal membership before any optional placement, sharing, or publication.",
        2,
    ),
}


ROADMAP_TABLE_ROW_REPLACEMENTS = [
    (
        (
            "From concept lab to coherent shellRemove contradictory recruiter-first copy, legacy Community fixtures, duplicate navigation, decorative activity modules, and misleading states.",
            "From public profile center to owner engineSigned-in Home, Capture, Journal, My Slate preview, Studio, and Settings become the core workspace.",
        ),
        (
            "From concept lab to coherent shell Remove contradictory recruiter-first copy, legacy Community fixtures, duplicate navigation, decorative activity modules, and misleading states.",
            "From public profile center to owner engine The signed-in system becomes Journal-centered with a context-preserving Capture action; exact Home/Slate/Work/Studio/Settings route grouping remains an approved route-map decision.",
        ),
    ),
    (
        ("5", "Universal Capture and private Journal", "Complete capture-to-reviewed-record vertical slice", "3–4"),
        ("5", "Universal Capture and private Journal", "Default-off Save Moment and derived private-Journal core, then eligible-origin expansion", "3–4"),
    ),
    (
        (
            "PHASE EXITA real text-first Capture-to-Journal vertical slice passes identity, ownership, provenance, lifecycle, isolation, accessibility, retry/failure, performance, deletion, and member-validation gates. It becomes the reference contract for voice and later intelligence.",
        ),
        (
            "PHASE EXIT A default-off text-first Save Moment and derived private-Journal slice passes identity, ownership, provenance, lifecycle, isolation, accessibility, retry/failure, performance, deletion, and two-member gates. Universal Capture is not claimed until the eligible-origin matrix passes; Type and Speak remain first-class reference paths for later intelligence.",
        ),
    ),
    (
        (
            "PS-JOURNAL-001",
            "Hold",
            "Explicit owner decision.",
            "No Journal UI work until restart; backend contracts may remain Journal-ready.",
        ),
        (
            "PS-JOURNAL-001",
            "Architecture current / runtime writer unassigned",
            "Owner decision July 20, 2026.",
            "Begin only with the bounded default-off private core; public/audience Journal and return services remain separate later gates.",
        ),
    ),
    (
        (
            "Core loop",
            "A person can capture once, review privately, preserve original language, connect the Moment, and deliberately project it.",
            "Capture/Journal modules, lifecycle states, provenance, transactions, queues, accessibility, failure handling.",
        ),
        (
            "Core loop",
            "A person can open Capture in context, choose Save Moment once, preserve original language, find the private Moment immediately in Journal, and later use its exact version deliberately.",
            "Universal composer, source/version and canonical-Moment transaction, derived Journal retrieval, governed references, lifecycle, accessibility, and failure handling.",
        ),
    ),
    (
        (
            "Activation",
            "A reviewed Moment immediately becomes useful without another dashboard.",
            "Use This Moment contracts, action adapters, traceability, outcome closure.",
        ),
        (
            "Activation",
            "A member-saved canonical Moment is immediately available in Journal and can become useful without another dashboard or mandatory review gate.",
            "Use This Moment shortcuts plus a complete accessible authorized-purpose chooser, action adapters, traceability, and outcome closure.",
        ),
    ),
    (
        ("1Capture", "2Understand", "3Review", "4Connect", "5Use", "6Share selectively", "7Revisit + learn"),
        ("1 Capture action", "2 Save Moment", "3 One private Journal", "4 Understand", "5 Use by reference", "6 Share selectively", "7 Revisit + learn"),
    ),
    (
        (
            "Canonical",
            "Users, identities, profiles, Moments, Journal entries, roles, projects, outcomes, relationships, audience",
            "Member-confirmed truth and system of record.",
        ),
        (
            "Canonical",
            "Users, identities, profiles, Moments, Journal entries, roles, projects, outcomes, relationships, audience",
            "Member-owned canonical truth and system of record; member-authored or explicitly accepted facts need no second promotion gate.",
        ),
    ),
    (
        (
            "Necessary",
            "It protects a member need, principle, risk, interface, or operating outcome.",
            "Universal Capture shall create an owner-scoped private draft before publication.",
        ),
        (
            "Necessary",
            "It protects a member need, principle, risk, interface, or operating outcome.",
            "Save Moment shall create one private member-saved canonical Moment and immediate derived owner-Journal membership before any optional publication.",
        ),
    ),
    (
        ("5. Speech", "Phase 6", "Add only after the text path, private save, review, and failure behavior are safe."),
        ("5. Speech", "Phase 6", "Expand only after text source/version preservation, Save Moment, derived private Journal, provider-failure behavior, and accessibility are safe; Type and Speak remain first-class target inputs."),
    ),
    (
        ("PS-CAPTURE-001", "Universal Capture — text reference path", "Private draft, review, promotion, optional projection"),
        ("PS-CAPTURE-001", "Released private text-source foundation", "Owner-scoped source create/list, validation, audit-safe persistence, migration, and release evidence reused behind the universal composer"),
    ),
    (
        ("PS-JOURNAL-001", "Private Journal", "Owner list/detail/edit/search/delete"),
        ("PS-JOURNAL-001", "Universal composer and private Journal core", "Idempotent Save Moment, source/version plus canonical Moment, immediate derived owner list/detail/search/lifecycle, and no copied Journal body"),
    ),
    (
        ("Experience", "Persistent Capture; private state; text/voice; review; correction; cancel; optional next action."),
        ("Experience", "In-context Capture; private state; Type/Speak; applicable inline transcript correction; cancel; one Save Moment action; origin return; optional post-save next action."),
    ),
    (
        ("Architecture", "Trusted-session owner; Capture service; captures table; private draft state; transaction; policy check; idempotency."),
        ("Architecture", "Trusted-session owner; universal-composer adapter; source/version plus canonical-Moment transaction; idempotent Save Moment; derived Journal query; optional proposal isolation."),
    ),
    (
        ("Data", "Original input, owner, type, status, provenance, timestamps, proposal, relationships, audience default."),
        ("Data", "Authorized original input/source version, owner, canonical Moment and version, timestamps, private audience default, optional proposal, and exact-reference relationships; no copied Journal body."),
    ),
    (
        ("Verification", "Unit state tests; integration persistence; duplicate/retry; isolation; negative publication; accessibility; outage."),
        ("Verification", "Unit and transaction tests; immediate derived Journal retrieval; duplicate/retry and partial-failure safety; two-owner isolation; negative publication; optional-proposal/provider outage; accessibility."),
    ),
    (
        ("Validation", "Pete/Danielle capture without tour, explain privacy, correct, save, find in Journal."),
        ("Validation", "Pete and Danielle open Capture in context, explain privacy, choose Save Moment once, return to origin, and find the saved Moment immediately in only their own Journal without Add to Journal."),
    ),
]


def main() -> int:
    build(
        BIBLE_SOURCE,
        BIBLE_OUTPUT,
        BIBLE_AMENDMENT,
        "Appendix O - Universal Capture, One Journal, and Trusted Return Covenant",
        BIBLE_REPLACEMENTS,
        {
            "word/header2.xml": {
                "PeerSlate Company and Product Bible  |  Version 2.7 Connected system and return-value authority":
                    "PeerSlate Company and Product Bible  |  Version 2.8 Universal Capture, one Journal, and trusted return authority"
            },
            "word/footer1.xml": {
                "PEERSLATE • CURRENT BIBLE • JULY 20, 2026   |   1":
                    "PEERSLATE • CURRENT BIBLE v2.8 • JULY 20, 2026   |   1"
            },
            "word/footer2.xml": {
                "CURRENT AUTHORITY — CONNECTED SYSTEM, RETURN VALUE, AND MEMBER OWNERSHIP":
                    "CURRENT AUTHORITY — UNIVERSAL CAPTURE, ONE JOURNAL, TRUSTED RETURN, AND MEMBER OWNERSHIP"
            },
        },
        "PeerSlate Company and Product Bible v2.8",
        [
            "v2.8 - Universal Capture, One Journal, and Trusted Return Authority (CURRENT)",
            "Appendix O - Universal Capture, One Journal, and Trusted Return Covenant",
            "PS-CORE-CAP-001",
            "PS-CORE-JRN-001",
            "PS-CORE-USE-002",
            "complete accessible chooser",
            "Ask Slate AI is the signed-in intelligence umbrella",
            "Messaging is a committed future domain",
            "Purposeful private acknowledgements/badges",
        ],
        [
            "v2.7 - Connected System and Return-Value Authority (CURRENT)",
            "Journal UI remains on hold until explicit owner authorization",
            "Bottom navigation: Home · Journal · Capture · Slate · More",
            "Points, badges, levels, public consistency counts, or trophy cabinets.",
            "PS-CORE-IA-006  The signed-in owner experience shall implement the approved five-board",
            "3 Private draft",
            "find the review step without a product tour",
            "Explicitly on hold.",
            "and Owner AI.",
            "shall show editable structured proposals before canonical promotion",
            "review precedes canonical promotion",
            "reaches a private reviewed draft without a tour",
            "Review and canonical Moment promotion remain separate work",
            "Original Source, then Member Review, then Canonical Slate",
            "Original preserved; proposal reviewed; member-confirmed Moment",
            "After a member reviews a Moment, PeerSlate should show",
            "Universal Capture shall create an owner-scoped private draft before placement, sharing, or publication.",
            "Preserved v1.5.1 voice-to-value loop: voice and text enter the same reviewable proposal architecture.",
            "PeerSlate voice-to-value loop: voice or text capture becomes a reviewable proposal, a canonical Journal record, and an optional member-controlled projection.",
            "Approved Capture baseline: voice or text enters one path, review precedes canonical promotion, privacy is visible, and Use This Moment follows capture.",
            "PeerSlate connected-system loop: original source, member review, canonical Slate, authorized relationship or placement, focused room or projection, activation, outcome and learning, return value, and new contribution.",
        ],
        table_row_replacements=BIBLE_TABLE_ROW_REPLACEMENTS,
        repeated_replacements=BIBLE_REPEATED_REPLACEMENTS,
        data_table_header_rows=[
            ("Area", "Verified production state", "Constitutional interpretation"),
        ],
        drawing_metadata_replacements=[
            (
                "PeerSlate voice-to-value loop: voice or text capture becomes a reviewable proposal, a canonical Journal record, and an optional member-controlled projection.",
                "Historical v1.5.1 voice-to-value diagram. It shows voice or text becoming a reviewable proposal and then a Journal record. Bible v2.8 supersedes that mandatory sequence: Save Moment creates one private canonical Moment immediately; transcript correction and AI proposals are inline and optional.",
                "Historical PeerSlate voice-to-value diagram",
            ),
            (
                "Approved Capture baseline: voice or text enters one path, review precedes canonical promotion, privacy is visible, and Use This Moment follows capture.",
                "Historical Capture storyboard retained for composition only. It depicts a separate review-before-promotion flow; Bible v2.8 supersedes that interaction with an in-context composer, a single Save Moment commit, inline transcript correction when applicable, and optional Use This Moment after save.",
                "PeerSlate in-context Capture composer historical visual reference",
            ),
            (
                "PeerSlate connected-system loop: original source, member review, canonical Slate, authorized relationship or placement, focused room or projection, activation, outcome and learning, return value, and new contribution.",
                "Historical connected-system diagram retained as a high-level reference. It depicts source, member review, canonical Slate, governed use, outcome, return value, and new contribution. Bible v2.8 supersedes the review gate with Capture action, Save Moment, one private canonical Moment, and a derived Journal before optional authorized uses.",
                None,
            ),
        ],
    )
    build(
        ROADMAP_SOURCE,
        ROADMAP_OUTPUT,
        ROADMAP_AMENDMENT,
        "Appendix H - Universal Capture, One Journal, and Trusted Return Execution Amendment",
        ROADMAP_REPLACEMENTS,
        {
            "word/header2.xml": {
                "PeerSlate Product Strategy and Architecture Roadmap  |  Version 2.6 Connected-system sequencing":
                    "PeerSlate Product Strategy and Architecture Roadmap  |  Version 2.7 Journal-system execution sequence"
            },
            "word/footer1.xml": {
                "PEERSLATE • CURRENT ROADMAP • JULY 20, 2026   |   1":
                    "PEERSLATE • CURRENT ROADMAP v2.7 • JULY 20, 2026   |   1"
            },
            "word/footer2.xml": {
                "CURRENT ROADMAP — CONNECTED-SYSTEM SEQUENCING; SOURCE MATERIAL PRESERVED":
                    "CURRENT ROADMAP — JOURNAL-SYSTEM EXECUTION; VERIFIED HISTORY PRESERVED"
            },
        },
        "PeerSlate Product Strategy and Architecture Roadmap v2.7",
        [
            "v2.7 - Journal-System Execution Sequence (CURRENT)",
            "Appendix H - Universal Capture, One Journal, and Trusted Return Execution Amendment",
            "PS-GOV-JOURNAL-SYSTEM-001",
            "PS-ASK-SLATE-AI-001",
            "PS-MESSAGING-001",
            "complete accessible chooser",
            "member-saved canonical text Moments",
            "Wave B — Private Journal core",
        ],
        [
            "v2.6 - Connected-System Sequencing (CURRENT)",
            "Journal UI is on hold; FitSlate remains tabled",
            "Mobile uses Home · Journal · Capture · Slate · More.",
            "Do not build a streak meter, points, badges, or a loss-framed return mechanic.",
            "PS-IA-002 The mobile authenticated shell shall expose Home, Journal, Capture, Slate, and More",
            "Signed-in Home, Capture, Journal, My Slate preview, Studio, and Settings become the core workspace.",
            "Complete capture-to-reviewed-record vertical slice",
            "A real text-first Capture-to-Journal vertical slice",
            "No streak, guilt, popularity, fabricated certainty, or automatic publication is introduced.",
            "No Journal UI work until restart; backend contracts may remain Journal-ready.",
            "requires explicit approval before canonical promotion or publication",
            "shall display an editable structured proposal before canonical promotion",
            "private persistence, review, canonical promotion, Journal retrieval",
            "No raw-text duplication; no Journal UI until restarted; no auth rewrite.",
            "Save raw private draft first",
            "Explicit review/promotion state",
            "same owner-scoped private draft, review, canonical promotion",
            "Original source → editable proposal → member-confirmed source-linked Moment",
            "original Capture source → lifecycle and correction controls → member review",
            "Run PS-MOMENT-001 to introduce member review and canonical Moment promotion.",
            "Universal Capture shall create an owner-scoped private draft before placement, sharing, or publication.",
            "Universal Capture shall create an owner-scoped private draft before publication.",
            "Private draft, review, promotion, optional projection",
            "The member can connect the reviewed Moment",
            "1Capture",
        ],
        table_row_replacements=ROADMAP_TABLE_ROW_REPLACEMENTS,
        repeated_replacements=ROADMAP_REPEATED_REPLACEMENTS,
        data_table_header_rows=[
            ("Capability / package", "Status", "Evidence summarized", "Roadmap consequence"),
            ("Lane", "Now", "Then", "Do not cross"),
        ],
    )
    print(f"built {BIBLE_OUTPUT.relative_to(ROOT)}")
    print(f"built {ROADMAP_OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
