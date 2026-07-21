#!/usr/bin/env python3
"""Promote the owner-approved v2.7 Bible and v2.6 Roadmap candidates.

The candidate generator remains the source of document structure. This bounded
activation changes approval/status language that differs between the
preserved PROPOSED candidates and the owner-approved CURRENT artifacts. It
also corrects inherited candidate header/footer version and date labels so the
rendered package identifies the activated authority consistently.
"""

from __future__ import annotations

import os
import tempfile
import zipfile
from xml.etree import ElementTree


PACKAGE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(PACKAGE)))
CANDIDATE = os.path.join(PACKAGE, "candidate")
GOVERNANCE = os.path.join(ROOT, "docs", "governance")


def replace_exact(xml: str, old: str, new: str) -> str:
    count = xml.count(old)
    if count != 1:
        raise ValueError(f"expected one activation anchor, found {count}: {old!r}")
    return xml.replace(old, new)


def relabel_status_before(xml: str, anchor: str) -> str:
    anchor_at = xml.find(anchor)
    if anchor_at < 0:
        raise ValueError(f"authority anchor not found: {anchor!r}")
    old = "<w:t>PROPOSED</w:t>"
    label_at = xml.rfind(old, 0, anchor_at)
    if label_at < 0:
        raise ValueError(f"PROPOSED authority label not found before {anchor!r}")
    return xml[:label_at] + "<w:t>LOCKED</w:t>" + xml[label_at + len(old):]


def promote(
    source: str,
    destination: str,
    replacements: list[tuple[str, str]],
    part_replacements: list[tuple[str, str, str]],
    authority_anchor: str,
    required: list[str],
    forbidden: list[str],
) -> None:
    with zipfile.ZipFile(source) as archive:
        document = archive.read("word/document.xml").decode("utf-8")

    for old, new in replacements:
        document = replace_exact(document, old, new)
    document = relabel_status_before(document, authority_anchor)

    os.makedirs(os.path.dirname(destination), exist_ok=True)
    handle, temporary = tempfile.mkstemp(
        prefix=".approved-authority-", suffix=".docx", dir=os.path.dirname(destination)
    )
    os.close(handle)
    try:
        with zipfile.ZipFile(source) as reader, zipfile.ZipFile(
            temporary, "w", zipfile.ZIP_DEFLATED
        ) as writer:
            for item in reader.infolist():
                payload = reader.read(item.filename)
                if item.filename == "word/document.xml":
                    payload = document.encode("utf-8")
                for part, old, new in part_replacements:
                    if item.filename == part:
                        payload = replace_exact(payload.decode("utf-8"), old, new).encode(
                            "utf-8"
                        )
                writer.writestr(item, payload)
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

    with zipfile.ZipFile(destination) as archive:
        if archive.testzip() is not None:
            raise ValueError(f"corrupt DOCX member: {archive.testzip()}")
        for name in archive.namelist():
            if name.endswith((".xml", ".rels")):
                ElementTree.fromstring(archive.read(name))
        text = "\n".join(
            archive.read(name).decode("utf-8")
            for name in archive.namelist()
            if name.endswith(".xml")
        )
    for value in required:
        if value not in text:
            raise ValueError(f"required approved text missing: {value!r}")
    for value in forbidden:
        if value in text:
            raise ValueError(f"proposed front-matter text survived: {value!r}")


def main() -> None:
    bible_source = os.path.join(
        CANDIDATE, "PeerSlate_Company_and_Product_Bible_v2.7_PROPOSED.docx"
    )
    bible_destination = os.path.join(
        GOVERNANCE, "PeerSlate_Company_and_Product_Bible_v2.7.docx"
    )
    bible_authority = "Authority: v2.7 is CURRENT and controlling."
    promote(
        bible_source,
        bible_destination,
        [
            (
                "v2.7 - Connected System and Return-Value Authority (PROPOSED)",
                "v2.7 - Connected System and Return-Value Authority (CURRENT)",
            ),
            (
                "PROPOSED - CANDIDATE AWAITING OWNER APPROVAL; v2.6 REMAINS CURRENT",
                "CURRENT AND LOCKED - APPROVED BY THE OWNER ON JULY 20, 2026; SUPERSEDES v2.6",
            ),
            (
                "Approval note: v2.7 is a CANDIDATE. It does not become controlling until Pete approves it and a separate activation change names it in CURRENT_BASELINE.yaml; v2.6 remains current until then. It preserves the entire v2.6 constitution - the verified production baseline, the visual-integrity covenant, the member-directed Story covenant, and the Projects covenant - and adds one governing decision: PeerSlate needs a stronger visible trunk, not more destinations. Every major room should feel like a focused use of the same member-owned life record, connected by canonical reference and member-directed action rather than copied facts or a new navigation forest.",
                "Approval note: v2.7 is CURRENT and LOCKED. Pete approved it on July 20, 2026 and the activation change named it in CURRENT_BASELINE.yaml, so it supersedes v2.6, which remains in the repository as a historical decision record. It preserves the entire v2.6 constitution - the verified production baseline, the visual-integrity covenant, the member-directed Story covenant, and the Projects covenant - and adds one governing decision: PeerSlate needs a stronger visible trunk, not more destinations. Every major room should feel like a focused use of the same member-owned life record, connected by canonical reference and member-directed action rather than copied facts or a new navigation forest.",
            ),
            (
                "Authority: v2.7 is a CANDIDATE and is not controlling. v2.6 remains the controlling Bible until Pete approves v2.7 and a separate activation change names it in CURRENT_BASELINE.yaml. Prior Bible versions remain preserved as historical decision records.",
                "Authority: v2.7 is CURRENT and controlling. Pete approved it on July 20, 2026 and the activation change named it in CURRENT_BASELINE.yaml, so it supersedes v2.6. Prior Bible versions, including v2.6, remain preserved as historical decision records.",
            ),
            (
                "The v2.7 candidate adds Section 19 'Rejected for the current program' and Appendices M and N; refresh this field to list them with correct page numbers.",
                "The v2.7 release adds Section 19 'Rejected for the current program' and Appendices M and N; refresh this field to list them with correct page numbers.",
            ),
        ],
        [
            (
                "word/document.xml",
                "This draft tightens the Bible",
                "This release tightens the Bible",
            ),
            (
                "word/header2.xml",
                "Version 2.6 Projects system authority",
                "Version 2.7 Connected system and return-value authority",
            ),
            (
                "word/footer1.xml",
                "CURRENT BIBLE • JULY 19, 2026",
                "CURRENT BIBLE • JULY 20, 2026",
            ),
            (
                "word/footer2.xml",
                "CURRENT AUTHORITY — VISUAL INTEGRITY, MEMBER-DIRECTED STORY, AND PROJECTS SYSTEM",
                "CURRENT AUTHORITY — CONNECTED SYSTEM, RETURN VALUE, AND MEMBER OWNERSHIP",
            ),
        ],
        bible_authority,
        [
            "CURRENT AND LOCKED - APPROVED BY THE OWNER ON JULY 20, 2026; SUPERSEDES v2.6",
            bible_authority,
            "Appendix M - Connected-system and return-value covenant",
            "Appendix N - Connected-system architecture map",
        ],
        [
            "v2.7 - Connected System and Return-Value Authority (PROPOSED)",
            "PROPOSED - CANDIDATE AWAITING OWNER APPROVAL; v2.6 REMAINS CURRENT",
            "Authority: v2.7 is a CANDIDATE",
            "This draft tightens the Bible",
            "Version 2.6 Projects system authority",
            "CURRENT BIBLE • JULY 19, 2026",
        ],
    )

    roadmap_source = os.path.join(
        CANDIDATE,
        "PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.6_PROPOSED.docx",
    )
    roadmap_destination = os.path.join(
        GOVERNANCE, "PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.6.docx"
    )
    roadmap_authority = "Roadmap authority: v2.6 is CURRENT and controlling."
    promote(
        roadmap_source,
        roadmap_destination,
        [
            (
                "v2.6 - Connected-System Sequencing (PROPOSED)",
                "v2.6 - Connected-System Sequencing (CURRENT)",
            ),
            (
                "PROPOSED - CANDIDATE AWAITING OWNER APPROVAL; v2.5 REMAINS CURRENT",
                "CURRENT AND LOCKED - APPROVED BY THE OWNER ON JULY 20, 2026; SUPERSEDES v2.5",
            ),
            (
                "v2.5 sequencing + candidate Bible v2.7 + July 20 connected-system decision",
                "v2.5 sequencing + Bible v2.7 + July 20 connected-system decision",
            ),
            (
                "Approval note: this v2.6 candidate preserves every v2.5 phase, package, status, release record, and production claim exactly, and adds one sequencing amendment for the connected-system and return-value direction. It advances nothing to Complete, starts nothing, and changes no live status. v2.5 remains current until Pete approves this candidate.",
                "Approval note: this v2.6 release preserves every v2.5 phase, package, status, release record, and production claim exactly, and adds one sequencing amendment for the connected-system and return-value direction. It advances nothing to Complete, starts nothing, and changes no live status. Pete approved it on July 20, 2026, so it supersedes v2.5, which remains in the repository as a historical record.",
            ),
            (
                "Roadmap authority: v2.6 is a CANDIDATE. v2.5 remains the current sequence and architecture until Pete approves this candidate and CURRENT_BASELINE.yaml names it. Historical package IDs and release evidence remain preserved. PS-STORY-COMPOSER-001, PS-PROJECTS-001, PS-ASK-PETE-AI-001, and every connective package named in Appendix G are planned or candidate work, not active.",
                "Roadmap authority: v2.6 is CURRENT and controlling. Pete approved it on July 20, 2026 and CURRENT_BASELINE.yaml names it, so it supersedes v2.5. Historical package IDs and release evidence remain preserved. PS-STORY-COMPOSER-001, PS-PROJECTS-001, PS-ASK-PETE-AI-001, and every connective package named in Appendix G are planned or candidate work, not active.",
            ),
            (
                "Delivered as PROPOSED by PS-GOV-CONNECTED-SYSTEM-001.",
                "Delivered by PS-GOV-CONNECTED-SYSTEM-001 and activated as CURRENT on July 20, 2026.",
            ),
            (
                "Delivered as PROPOSED by this document.",
                "Delivered by this document and activated as CURRENT on July 20, 2026.",
            ),
            (
                "Delivered as PROPOSED: Bible Appendix N and package file 03.",
                "Delivered: Bible Appendix N is CURRENT; package file 03 remains PROPOSED and package-local.",
            ),
            (
                "Delivered as PROPOSED: package file 04.",
                "Delivered as PROPOSED and package-local: package file 04.",
            ),
        ],
        [
            (
                "word/header2.xml",
                "Version 2.5 Projects system architecture",
                "Version 2.6 Connected-system sequencing",
            ),
            (
                "word/footer1.xml",
                "CURRENT ROADMAP • JULY 19, 2026",
                "CURRENT ROADMAP • JULY 20, 2026",
            ),
            (
                "word/footer2.xml",
                "CURRENT ROADMAP — SOURCE MATERIAL PRESERVED; PROJECTS SYSTEM DIRECTION ADOPTED",
                "CURRENT ROADMAP — CONNECTED-SYSTEM SEQUENCING; SOURCE MATERIAL PRESERVED",
            ),
            (
                "word/document.xml",
                '<w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:r><w:t xml:space="preserve">Priority 2 - Build next: canonical relationship foundation</w:t>',
                '<w:pPr><w:pStyle w:val="Heading2"/><w:pageBreakBefore/></w:pPr><w:r><w:t xml:space="preserve">Priority 2 - Build next: canonical relationship foundation</w:t>',
            ),
            (
                "word/document.xml",
                '<w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:r><w:t xml:space="preserve">Validation scenarios</w:t>',
                '<w:pPr><w:pStyle w:val="Heading2"/><w:pageBreakBefore/></w:pPr><w:r><w:t xml:space="preserve">Validation scenarios</w:t>',
            ),
            (
                "word/document.xml",
                '<w:sectPr w:rsidR="00BD588A" w:rsidSect="00034616"><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="979" w:right="1037" w:bottom="922" w:left="1037" w:header="389" w:footer="374" w:gutter="0"/><w:cols w:space="720"/><w:titlePg/><w:docGrid w:linePitch="360"/></w:sectPr></w:body>',
                '<w:sectPr w:rsidR="00BD588A" w:rsidSect="00034616"><w:headerReference w:type="even" r:id="rId9"/><w:headerReference w:type="default" r:id="rId10"/><w:footerReference w:type="default" r:id="rId11"/><w:headerReference w:type="first" r:id="rId12"/><w:footerReference w:type="first" r:id="rId13"/><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="979" w:right="1037" w:bottom="922" w:left="1037" w:header="389" w:footer="374" w:gutter="0"/><w:cols w:space="720"/><w:docGrid w:linePitch="360"/></w:sectPr></w:body>',
            ),
        ],
        roadmap_authority,
        [
            "CURRENT AND LOCKED - APPROVED BY THE OWNER ON JULY 20, 2026; SUPERSEDES v2.5",
            roadmap_authority,
            "Appendix G - Connected-system and return-value direction amendment",
            "Priority 3 - Build after Owner Home frontend and real confirmed history",
        ],
        [
            "v2.6 - Connected-System Sequencing (PROPOSED)",
            "PROPOSED - CANDIDATE AWAITING OWNER APPROVAL; v2.5 REMAINS CURRENT",
            "Roadmap authority: v2.6 is a CANDIDATE",
            "Version 2.5 Projects system architecture",
            "CURRENT ROADMAP • JULY 19, 2026",
        ],
    )

    print(f"activated {os.path.relpath(bible_destination, ROOT)}")
    print(f"activated {os.path.relpath(roadmap_destination, ROOT)}")


if __name__ == "__main__":
    main()
