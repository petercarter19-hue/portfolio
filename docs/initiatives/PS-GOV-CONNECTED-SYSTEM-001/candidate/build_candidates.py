#!/usr/bin/env python3
"""Deterministically build the PROPOSED candidate Bible v2.7 and Roadmap v2.6.

PS-GOV-CONNECTED-SYSTEM-001 — documentation and governance only.

The candidates are produced by applying a bounded, anchored set of additions to
the *unchanged* v2.6 Bible and v2.5 Roadmap. Nothing is deleted, no section is
renumbered, and no appendix is re-lettered. Styles, headers, footers, numbering,
theme, and existing media are inherited from the source documents, so the
candidates keep the established visual system exactly.

Sources (read only, never modified):
  docs/governance/PeerSlate_Company_and_Product_Bible_v2.6.docx
  docs/governance/PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.5.docx

Outputs (this directory):
  PeerSlate_Company_and_Product_Bible_v2.7_PROPOSED.docx
  PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.6_PROPOSED.docx

Run from the repository root:
  venv/bin/python docs/initiatives/PS-GOV-CONNECTED-SYSTEM-001/candidate/build_candidates.py

The authoritative change text lives in
  ../01_CANDIDATE_BIBLE_V2_7_SOURCE.md
  ../02_CANDIDATE_ROADMAP_V2_6_SOURCE.md
This script is the renderer for that text, not a second source of truth.
"""

from __future__ import annotations

import os
import re
import shutil
import struct
import sys
import zipfile
from xml.etree import ElementTree

HERE = os.path.dirname(os.path.abspath(__file__))
PACKAGE = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(PACKAGE)))
GOV = os.path.join(ROOT, "docs", "governance")

BIBLE_SRC = os.path.join(GOV, "PeerSlate_Company_and_Product_Bible_v2.6.docx")
ROADMAP_SRC = os.path.join(
    GOV, "PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.5.docx"
)
BIBLE_OUT = os.path.join(HERE, "PeerSlate_Company_and_Product_Bible_v2.7_PROPOSED.docx")
ROADMAP_OUT = os.path.join(
    HERE, "PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.6_PROPOSED.docx"
)

# The architecture diagram is preserved with the owner handoff on the staging
# branch work/2026-07-20-next-task-board, which is pushed to origin but not yet
# merged, so it is not present on this branch. Point the build at it with:
#   PEERSLATE_CONNECTED_SYSTEM_DIAGRAM=/path/to/peerslate_connected_system_architecture.png
# or let it resolve from source/ once the staging branch merges. When the file is
# available the diagram is embedded in Bible Appendix N; when it is absent the
# appendix renders the same map as text and says so. The build never fails
# because of it, and the appendix is never silently missing its figure.
DIAGRAM = os.environ.get("PEERSLATE_CONNECTED_SYSTEM_DIAGRAM") or os.path.join(
    PACKAGE, "source", "peerslate_connected_system_architecture.png"
)

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


# --------------------------------------------------------------------------
# escaping and small XML builders
# --------------------------------------------------------------------------


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


def run(text: str, bold: bool = False, style: str | None = None) -> str:
    props = ""
    if style:
        props += f'<w:rStyle w:val="{style}"/>'
    if bold:
        props += "<w:b/>"
    rpr = f"<w:rPr>{props}</w:rPr>" if props else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{esc(text)}</w:t></w:r>'


def para(text: str, style: str | None = None, lead: str | None = None) -> str:
    """One paragraph. `lead` is rendered bold before `text`."""
    ppr = ""
    if style == "ListBullet":
        ppr = (
            '<w:pPr><w:pStyle w:val="ListBullet"/>'
            '<w:spacing w:after="50" w:line="247" w:lineRule="auto"/></w:pPr>'
        )
    elif style == "ListNumber":
        ppr = (
            '<w:pPr><w:pStyle w:val="ListNumber"/>'
            '<w:spacing w:after="50" w:line="247" w:lineRule="auto"/></w:pPr>'
        )
    elif style:
        ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>'
    body = (run(lead, bold=True) if lead else "") + run(text)
    return f"<w:p>{ppr}{body}</w:p>"


def heading(text: str, level: int = 1) -> str:
    return (
        f'<w:p><w:pPr><w:pStyle w:val="Heading{level}"/></w:pPr>'
        f"{run(text)}</w:p>"
    )


def requirement(identifier: str, text: str) -> str:
    return (
        '<w:p><w:pPr><w:pStyle w:val="Requirement"/><w:keepLines/></w:pPr>'
        f'<w:r><w:rPr><w:rStyle w:val="CodeID"/></w:rPr>'
        f'<w:t xml:space="preserve">{esc(identifier)}  </w:t></w:r>'
        f"{run(text)}</w:p>"
    )


def small_note(text: str) -> str:
    return (
        '<w:p><w:pPr><w:pStyle w:val="SmallNote"/><w:jc w:val="center"/></w:pPr>'
        f'<w:r><w:rPr><w:i/><w:sz w:val="15"/></w:rPr>'
        f'<w:t xml:space="preserve">{esc(text)}</w:t></w:r></w:p>'
    )


def callout(title: str, body: str, accent: str = "9A6819", fill: str = "FFF5DF") -> str:
    """Single-cell emphasis box matching the source documents."""
    return (
        '<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/><w:jc w:val="center"/>'
        '<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" w:firstColumn="1"'
        ' w:lastColumn="0" w:noHBand="0" w:noVBand="1"/></w:tblPr>'
        '<w:tblGrid><w:gridCol w:w="10166"/></w:tblGrid>'
        '<w:tr><w:trPr><w:jc w:val="center"/></w:trPr>'
        '<w:tc><w:tcPr><w:tcW w:w="10166" w:type="dxa"/><w:tcBorders>'
        f'<w:left w:val="single" w:sz="22" w:space="0" w:color="{accent}"/>'
        f'</w:tcBorders><w:shd w:val="clear" w:color="auto" w:fill="{fill}"/>'
        '<w:tcMar><w:top w:w="120" w:type="dxa"/><w:left w:w="160" w:type="dxa"/>'
        '<w:bottom w:w="120" w:type="dxa"/><w:right w:w="160" w:type="dxa"/>'
        "</w:tcMar></w:tcPr>"
        '<w:p><w:pPr><w:spacing w:after="40"/></w:pPr>'
        f'<w:r><w:rPr><w:b/><w:color w:val="{accent}"/><w:sz w:val="15"/></w:rPr>'
        f'<w:t xml:space="preserve">{esc(title)}</w:t></w:r></w:p>'
        '<w:p><w:pPr><w:spacing w:after="0" w:line="250" w:lineRule="auto"/></w:pPr>'
        f'<w:r><w:t xml:space="preserve">{esc(body)}</w:t></w:r></w:p>'
        "</w:tc></w:tr></w:tbl>"
    )


def status_table(label: str, lead: str, text: str, accent: str = "2D7F83",
                 label_fill: str = "E8F5F4") -> str:
    """The `LOCKED | Section status: …` two-cell band."""
    return (
        '<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/>'
        '<w:tblLayout w:type="fixed"/><w:tblLook w:val="04A0" w:firstRow="1"'
        ' w:lastRow="0" w:firstColumn="1" w:lastColumn="0" w:noHBand="0"'
        ' w:noVBand="1"/></w:tblPr>'
        '<w:tblGrid><w:gridCol w:w="1584"/><w:gridCol w:w="8496"/></w:tblGrid>'
        "<w:tr><w:trPr><w:cantSplit/></w:trPr>"
        '<w:tc><w:tcPr><w:tcW w:w="1584" w:type="dxa"/>'
        f'<w:shd w:val="clear" w:color="auto" w:fill="{label_fill}"/>'
        '<w:tcMar><w:top w:w="80" w:type="dxa"/><w:left w:w="100" w:type="dxa"/>'
        '<w:bottom w:w="80" w:type="dxa"/><w:right w:w="100" w:type="dxa"/>'
        "</w:tcMar></w:tcPr><w:p>"
        f'<w:r><w:rPr><w:b/><w:color w:val="{accent}"/><w:sz w:val="15"/></w:rPr>'
        f'<w:t xml:space="preserve">{esc(label)}</w:t></w:r></w:p></w:tc>'
        '<w:tc><w:tcPr><w:tcW w:w="8496" w:type="dxa"/>'
        '<w:shd w:val="clear" w:color="auto" w:fill="F8FAFB"/>'
        '<w:tcMar><w:top w:w="80" w:type="dxa"/><w:left w:w="100" w:type="dxa"/>'
        '<w:bottom w:w="80" w:type="dxa"/><w:right w:w="100" w:type="dxa"/>'
        "</w:tcMar></w:tcPr><w:p>"
        '<w:r><w:rPr><w:b/><w:color w:val="17324D"/><w:sz w:val="16"/></w:rPr>'
        f'<w:t xml:space="preserve">{esc(lead)} </w:t></w:r>'
        f'<w:r><w:rPr><w:sz w:val="16"/></w:rPr>'
        f'<w:t xml:space="preserve">{esc(text)}</w:t></w:r></w:p></w:tc>'
        "</w:tr></w:tbl>"
    )


def grid_table(headers: list[str], rows: list[list[str]], widths: list[int]) -> str:
    """Navy-header data table matching the source documents."""
    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    head_cells = "".join(
        f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>'
        '<w:shd w:val="clear" w:color="auto" w:fill="17324D"/>'
        '<w:tcMar><w:top w:w="90" w:type="dxa"/><w:left w:w="95" w:type="dxa"/>'
        '<w:bottom w:w="90" w:type="dxa"/><w:right w:w="95" w:type="dxa"/>'
        "</w:tcMar></w:tcPr><w:p>"
        '<w:r><w:rPr><w:b/><w:color w:val="FFFFFF"/><w:sz w:val="14"/></w:rPr>'
        f'<w:t xml:space="preserve">{esc(h)}</w:t></w:r></w:p></w:tc>'
        for h, w in zip(headers, widths)
    )
    body = ""
    for index, cells in enumerate(rows):
        fill = "FFFFFF" if index % 2 == 0 else "F8FAFB"
        body += (
            '<w:tr><w:trPr><w:cantSplit/><w:jc w:val="center"/></w:trPr>'
            + "".join(data_cell(text, w, fill) for text, w in zip(cells, widths))
            + "</w:tr>"
        )
    return (
        '<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/><w:jc w:val="center"/>'
        '<w:tblLayout w:type="fixed"/><w:tblLook w:val="04A0" w:firstRow="1"'
        ' w:lastRow="0" w:firstColumn="1" w:lastColumn="0" w:noHBand="0"'
        ' w:noVBand="1"/></w:tblPr>'
        f"<w:tblGrid>{grid}</w:tblGrid>"
        '<w:tr><w:trPr><w:tblHeader/><w:jc w:val="center"/></w:trPr>'
        f"{head_cells}</w:tr>{body}</w:tbl>"
    )


def data_cell(text: str, width: int, fill: str) -> str:
    return (
        f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/>'
        f'<w:shd w:val="clear" w:color="auto" w:fill="{fill}"/>'
        '<w:tcMar><w:top w:w="75" w:type="dxa"/><w:left w:w="95" w:type="dxa"/>'
        '<w:bottom w:w="75" w:type="dxa"/><w:right w:w="95" w:type="dxa"/>'
        "</w:tcMar></w:tcPr>"
        '<w:p><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>'
        f'<w:r><w:rPr><w:sz w:val="14"/></w:rPr>'
        f'<w:t xml:space="preserve">{esc(text)}</w:t></w:r></w:p></w:tc>'
    )


def bullets(items: list[str]) -> str:
    return "".join(para(item, "ListBullet") for item in items)


# --------------------------------------------------------------------------
# anchored editing
# --------------------------------------------------------------------------


class Doc:
    """A word/document.xml body edited through unique text anchors."""

    def __init__(self, xml: str):
        self.xml = xml
        # Every anchor is resolved after the cached table of contents so that a
        # TOC entry can never be mistaken for the body text it points at.
        last_toc = max(xml.rfind('w:val="TOC1"'), xml.rfind('w:val="TOC2"'))
        if last_toc < 0:
            raise LookupError("cached table of contents not found")
        self.body_start = xml.index("</w:p>", last_toc) + len("</w:p>")

    def _find(self, anchor: str) -> int:
        index = self.xml.find(anchor, self.body_start)
        if index < 0:
            raise LookupError(f"anchor not found in body: {anchor!r}")
        if self.xml.find(anchor, index + 1) >= 0:
            raise LookupError(f"anchor is not unique in body: {anchor!r}")
        return index

    def replace_text(self, old: str, new: str) -> None:
        if self.xml.count(old) != 1:
            raise LookupError(f"replace anchor is not unique: {old!r}")
        self.xml = self.xml.replace(old, esc(new))

    def append_to_text(self, anchor: str, suffix: str) -> None:
        """Extend an existing run's text without disturbing its formatting."""
        index = self._find(anchor)
        end = self.xml.index("</w:t>", index)
        self.xml = self.xml[:end] + esc(suffix) + self.xml[end:]

    def relabel_status_band(self, anchor: str, old_label: str, new_label: str) -> None:
        """Change the status word in the band whose body contains `anchor`."""
        index = self._find(anchor)
        needle = f"<w:t>{old_label}</w:t>"
        position = self.xml.rfind(needle, self.body_start, index)
        if position < 0:
            raise LookupError(
                f"status label {old_label!r} not found before anchor {anchor!r}"
            )
        self.xml = (
            self.xml[:position]
            + f"<w:t>{new_label}</w:t>"
            + self.xml[position + len(needle):]
        )

    def after_para(self, anchor: str, insertion: str) -> None:
        index = self._find(anchor)
        position = self.xml.index("</w:p>", index) + len("</w:p>")
        self.xml = self.xml[:position] + insertion + self.xml[position:]

    def before_para(self, anchor: str, insertion: str) -> None:
        index = self._find(anchor)
        position = self.xml.rindex("<w:p ", self.body_start, index)
        self.xml = self.xml[:position] + insertion + self.xml[position:]

    def after_table(self, anchor: str, insertion: str) -> None:
        index = self._find(anchor)
        position = self.xml.index("</w:tbl>", index) + len("</w:tbl>")
        self.xml = self.xml[:position] + insertion + self.xml[position:]

    def after_row(self, anchor: str, insertion: str) -> None:
        index = self._find(anchor)
        position = self.xml.index("</w:tr>", index) + len("</w:tr>")
        self.xml = self.xml[:position] + insertion + self.xml[position:]

    def widths_of_table_at(self, anchor: str) -> list[int]:
        index = self._find(anchor)
        start = self.xml.rindex("<w:tblGrid>", self.body_start, index)
        end = self.xml.index("</w:tblGrid>", start)
        return [int(w) for w in re.findall(r'w:gridCol w:w="(\d+)"', self.xml[start:end])]

    def rows_after(self, anchor: str, rows: list[list[str]], start_index: int = 1) -> None:
        widths = self.widths_of_table_at(anchor)
        chunk = ""
        for offset, cells in enumerate(rows):
            fill = "FFFFFF" if (start_index + offset) % 2 == 0 else "F8FAFB"
            chunk += (
                '<w:tr><w:trPr><w:cantSplit/><w:jc w:val="center"/></w:trPr>'
                + "".join(data_cell(t, w, fill) for t, w in zip(cells, widths))
                + "</w:tr>"
            )
        self.after_row(anchor, chunk)

    def append_to_body(self, insertion: str) -> None:
        """Insert immediately before the body-level final section properties."""
        position = self.xml.rindex("<w:sectPr")
        preceding = self.xml[:position].rstrip()
        if not (preceding.endswith("</w:p>") or preceding.endswith("</w:tbl>")):
            raise LookupError(
                "final sectPr is not a body-level sibling; refusing to append"
            )
        self.xml = self.xml[:position] + insertion + self.xml[position:]

    def mark_toc_dirty(self) -> None:
        needle = (
            '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
            '<w:r><w:instrText xml:space="preserve"> TOC \\o "1-2" \\h \\z \\u </w:instrText></w:r>'
        )
        if needle not in self.xml:
            raise LookupError("table-of-contents field not found")
        self.xml = self.xml.replace(
            needle,
            '<w:r><w:fldChar w:fldCharType="begin" w:dirty="true"/></w:r>'
            '<w:r><w:instrText xml:space="preserve"> TOC \\o "1-2" \\h \\z \\u </w:instrText></w:r>',
            1,
        )


def png_size(path: str) -> tuple[int, int]:
    with open(path, "rb") as handle:
        header = handle.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    return struct.unpack(">II", header[16:24])


def repack(source: str, target: str, document_xml: str, extra: dict[str, bytes],
           rels_xml: str | None = None) -> None:
    """Copy the source package, substituting document.xml and adding media."""
    with zipfile.ZipFile(source) as reader:
        items = reader.infolist()
        payload = {item.filename: reader.read(item.filename) for item in items}
    payload["word/document.xml"] = document_xml.encode("utf-8")
    if rels_xml is not None:
        payload["word/_rels/document.xml.rels"] = rels_xml.encode("utf-8")
    payload.update(extra)
    tmp = target + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as writer:
        for item in items:
            writer.writestr(item.filename, payload.pop(item.filename))
        for name, data in payload.items():
            writer.writestr(name, data)
    shutil.move(tmp, target)


# --------------------------------------------------------------------------
# candidate Bible v2.7
# --------------------------------------------------------------------------


def build_bible() -> None:
    with zipfile.ZipFile(BIBLE_SRC) as archive:
        document = archive.read("word/document.xml").decode("utf-8")
        rels = archive.read("word/_rels/document.xml.rels").decode("utf-8")
    doc = Doc(document)

    # --- front matter -----------------------------------------------------
    doc.replace_text(
        "v2.6 - Projects System Authority",
        "v2.7 - Connected System and Return-Value Authority (PROPOSED)",
    )
    doc.replace_text("July 19, 2026", "July 20, 2026")
    doc.replace_text(
        "CURRENT - OWNER-APPROVED PRODUCT, VISUAL, STORY, AND PROJECTS AUTHORITY",
        "PROPOSED - CANDIDATE AWAITING OWNER APPROVAL; v2.6 REMAINS CURRENT",
    )
    doc.replace_text(
        "v2.5 Story authority + July 19 owner Projects system decision",
        "v2.6 Projects authority + July 20 owner connected-system and return-value decision",
    )
    doc.replace_text(
        "Approval note: v2.6 is the current controlling Bible when named in "
        "CURRENT_BASELINE.yaml. It preserves the verified production, "
        "visual-integrity, and member-directed Story baseline and adds the "
        "owner-approved Projects covenant: Projects are private-first connected "
        "containers, Project Workspaces and Project Projections remain separate, "
        "canonical records are linked rather than copied, and later implementation "
        "may not become a task-management clone.",
        "Approval note: v2.7 is a CANDIDATE. It does not become controlling until "
        "Pete approves it and a separate activation change names it in "
        "CURRENT_BASELINE.yaml; v2.6 remains current until then. It preserves the "
        "entire v2.6 constitution - the verified production baseline, the "
        "visual-integrity covenant, the member-directed Story covenant, and the "
        "Projects covenant - and adds one governing decision: PeerSlate needs a "
        "stronger visible trunk, not more destinations. Every major room should "
        "feel like a focused use of the same member-owned life record, connected "
        "by canonical reference and member-directed action rather than copied "
        "facts or a new navigation forest.",
    )
    doc.replace_text(
        'This table updates automatically. If page numbers do not appear, click '
        'inside it and press F9 (or right-click and choose "Update Field").',
        "This table updates automatically. If page numbers do not appear, click "
        'inside it and press F9 (or right-click and choose "Update Field"). The '
        "v2.7 candidate adds Section 19 'Rejected for the current program' and "
        "Appendices M and N; refresh this field to list them with correct page "
        "numbers.",
    )
    doc.replace_text(
        "Authority: v2.6 is controlling when named by CURRENT_BASELINE.yaml. Prior "
        "Bible versions remain preserved as historical decision records.",
        "Authority: v2.7 is a CANDIDATE and is not controlling. v2.6 remains the "
        "controlling Bible until Pete approves v2.7 and a separate activation change "
        "names it in CURRENT_BASELINE.yaml. Prior Bible versions remain preserved as "
        "historical decision records.",
    )
    doc.relabel_status_band(
        "Authority: v2.7 is a CANDIDATE and is not controlling.", "LOCKED", "PROPOSED"
    )
    doc.replace_text(
        "Appendices (including mandatory startup, owner-understanding, and "
        "visual-integrity standards)",
        "Appendices (including mandatory startup, owner-understanding, "
        "visual-integrity, and connected-system standards)",
    )
    doc.mark_toc_dirty()

    # --- executive direction ---------------------------------------------
    doc.after_para(
        "The strongest product direction is not",
        para(
            "PeerSlate's next coherence objective is not more destinations. It is a "
            "stronger visible trunk. Every major room should feel like a focused use "
            "of the same member-owned life record. The product shall preserve each "
            "room's distinct purpose while revealing truthful origin, authorized "
            "relationships, audience or truth state, and one best continuation. "
            "Connection is created through canonical references and member-directed "
            "actions, not copied facts, generic promotion modules, or a new "
            "navigation forest."
        )
        + callout(
            "GOVERNING DECISION",
            "Every page should feel like a different use of the same life.",
        ),
    )

    # --- Section 3: principles -------------------------------------------
    doc.append_to_text(
        "not streaks, trends, vanity counts, or infinite scroll.",
        " Quiet return value explicitly includes resurfaced history, Slate Replay, "
        "and one useful next step.",
    )
    doc.rows_after(
        "PS-P-014",
        [
            [
                "PS-P-015",
                "Focused rooms, visible spine",
                "Every major room shall remain focused on its primary task while "
                "showing enough source, relationship, mode, and next-action context "
                "that it never feels orphaned from the connected Slate.",
            ],
            [
                "PS-P-016",
                "Momentum without pressure",
                "PeerSlate may create return value through useful memory, "
                "preparation, gentle prompts, and visible progress, but shall not "
                "use guilt, loss framing, public streaks, punitive recovery, "
                "artificial scarcity, or popularity pressure.",
            ],
        ],
        start_index=1,
    )

    # --- Section 4: boundaries -------------------------------------------
    doc.after_para(
        "An AI-enabled product in which deterministic controls protect",
        bullets(
            [
                "A system that connects rooms sideways by meaning and backward and "
                "forward through time.",
                "A product where a small contribution can compound into future "
                "recall, preparation, expression, and decision support.",
            ]
        ),
    )
    doc.after_para(
        "Not a product that calls fixtures",
        bullets(
            [
                'Not a collection of generic "related content" rails or promotional '
                "cross-links.",
                "Not a habit game that treats absence as failure.",
                "Not an emotional-diagnosis system derived from voice, behavior, or "
                "inferred mood.",
            ]
        ),
    )

    # --- Section 5: one connected Slate ----------------------------------
    doc.after_table(
        "AI interpretations, r",
        heading("The connected-system spine", 2)
        + para(
            "One connected Slate is not achieved only by sharing a database. The "
            "experience must make the relationship visible. Original sources enter a "
            "reviewable pipeline; confirmed records connect through governed "
            "relationships and exact-version placements; focused rooms receive only "
            "authorized context; member actions create reviewable projections or "
            "outcomes; and useful history returns through finite Home, Replay, "
            "resurfacing, and preparation. Each layer remains separately governed so "
            "connection never erases truth boundaries."
        )
        + heading("Relationship before promotion", 2)
        + para(
            "Cross-room movement must explain why another room matters in the "
            "member's current context. PeerSlate should prefer “Practice telling "
            "this result,” “See how this line was earned,” or "
            "“Return to the Moment behind this answer” over generic "
            "“Explore more” links. Relationship-rich cues are part of the "
            "product model, not marketing decoration."
        ),
    )

    # --- Section 6: connected-room contract ------------------------------
    doc.after_para(
        "This slice is the product’s reference architecture",
        heading("The connected-room contract", 2)
        + status_table(
            "LOCKED",
            "Section status:",
            "Every primary room answers the same five questions with a "
            "mode-appropriate, server-authorized payload. Exact layouts and "
            "component contracts belong in the Experience System and the "
            "Architecture and Data Standard.",
        )
        + para("Every primary room must answer, at the appropriate depth:")
        + "".join(
            para(item, "ListNumber")
            for item in [
                "What is this room helping me do?",
                "Whose space and which audience or truth state am I in?",
                "Where did this material come from?",
                "How does it relate to the larger Slate?",
                "What is the one best safe next move?",
            ]
        )
        + para(
            "The contract must support the same grammar with different authorized "
            "payloads:"
        )
        + para(
            "approved public relationships, approved projections, public-safe source "
            "context, and truthful current capability.",
            "ListBullet",
            lead="Public or permissioned mode: ",
        )
        + para(
            "private source relationships, prior work, drafts, outcomes, goals, "
            "Projects, Replay, and exact audience preview.",
            "ListBullet",
            lead="Owner mode: ",
        )
        + callout(
            "HARD BOUNDARY",
            "No private information may be retrieved and hidden in the browser. The "
            "server must authorize the relationship before it is returned. This "
            "applies the existing authorization-before-retrieval rule to connective "
            "context; it creates no exception to it.",
            accent="2D7F83",
            fill="E8F5F4",
        )
        + heading("Focused but not orphaned", 2)
        + para(
            "Task rooms such as Studio may reduce chrome while the member is "
            "answering, recording, or reviewing. Orientation and continuation should "
            "appear at natural boundaries, especially before the task and after "
            "meaningful progress, rather than interrupting the task. The default "
            "connective budget is one primary bridge and no more than two secondary "
            "paths."
        )
        + heading("The temporal spine", 2)
        + para(
            "PeerSlate connects not only across rooms but across time. When "
            "sufficient confirmed history exists, a room may reveal an earlier "
            "related Moment, a meaningful change, an unfinished thread, or a future "
            "revisit. Temporal cues must be source-linked, dismissible, "
            "non-diagnostic, and free of guilt."
        ),
    )

    # --- Section 7: connective patterns and return-value engine ----------
    doc.after_para(
        "Layout editing creates owner-scoped, versioned projection metadata.",
        heading("Connected-room patterns", 2)
        + para(
            "These are canonical experience patterns, not top-level destinations. "
            "Each appears inside an existing room. None is authorized for "
            "implementation by its presence here; each requires its own assigned "
            "package, entry gate, named visual authority, and evidence."
        )
        + grid_table(
            ["Pattern", "What it is"],
            [
                [
                    "Slate Spine",
                    "Compact orientation showing room role, one or two meaningful "
                    "relationships, and one primary next action.",
                ],
                [
                    "Backstory Drawer",
                    "Public-safe path from a selected Resume claim or Work highlight "
                    "to the context, impact, related Story or Project, and optional "
                    "practice route.",
                ],
                [
                    "Studio Return Ticket",
                    "Post-review continuation that reconnects practice to approved "
                    "support, a related question, a saved lesson, or a later retry "
                    "appropriate to the current mode.",
                ],
                [
                    "Then and Now",
                    "Source-linked temporal comparison showing change, recurrence, or "
                    "continuity without declaring identity or capability as fact.",
                ],
                [
                    "Focus Theme",
                    "A private, optional season-level intention that may tune prompts, "
                    "resurfacing, Replay, and preparation without becoming a new "
                    "destination.",
                ],
                [
                    "Progress Keepsake",
                    "A member-selected reference to a meaningful quote, clip, "
                    "before-and-now pair, Replay item, or confirmed projection. It is "
                    "not a trophy, a duplicate record, or a popularity object.",
                ],
            ],
            [2520, 7560],
        )
        + small_note(
            "As of this candidate, no connective pattern is implemented, assigned, "
            "deployed, enabled, or live. Preservation here is not implementation "
            "authorization."
        )
        + heading("The return-value engine", 2)
        + para(
            "PeerSlate's enduring return loop should be built from a tiny worthwhile "
            "contribution, immediate truthful payoff, later memory or progress value, "
            "and one gentle continuation. The preferred pattern is: small check-in or "
            "Capture, then reviewable value, then finite resurfacing or Replay, then a "
            "personalized source-linked prompt, then one optional next action. "
            "Returning after absence is treated as continuation, not failure."
        ),
    )

    # --- Section 9: voice and modality -----------------------------------
    doc.after_para(
        "Preserved v1.5.1 voice-to-value loop",
        heading("Expression-first and modality-flexible", 2)
        + para(
            "PeerSlate is expression-first and modality-flexible. Voice and text are "
            "first-class paths into the same ownership, provenance, review, "
            "correction, privacy, lifecycle, and activation architecture. Voice may "
            "become a signature medium only after it becomes a usable object: "
            "editable transcript, clear privacy state, source link, review, "
            "correction, search or retrieval support, deletion behavior, and text "
            "fallback. Voice-derived emotional cues may be offered only as optional, "
            "humble observations and never as diagnosis."
        )
        + para(
            "The following voice concepts are preserved as later candidates after "
            "usability and trust are proven. They carry no design, prototype, "
            "architecture, backlog, or release authorization:"
        )
        + bullets(
            [
                "Walk-and-Talk or Walk Mode",
                "Story Mode",
                "Voice-to-Meaning",
                "Echo Back",
                "Duet With Your Past Self",
                "Future Voice Mail",
                "Audio Subnotes",
                "Voice Keepsakes",
                "Private Growth Reels",
                "Prompt DJ or Conversation Capture",
            ]
        ),
    )

    # --- Section 11: momentum hooks and quiet delight --------------------
    doc.before_para(
        "Quiet delight and found details",
        heading("Momentum hooks, not pressure hooks", 2)
        + para(
            "PeerSlate should make return feel cumulative, warm, and useful. It may "
            "acknowledge continuity, preserved threads, reviewed history, and "
            "progress. It shall not threaten loss, shame absence, punish missed days, "
            "exaggerate praise, or turn professional growth into a public "
            "performance. “You still have the thread” is aligned; "
            "“Do not lose your streak” is not."
        ),
    )
    doc.rows_after(
        "You may want this soon",
        [
            [
                "“Welcome back. Nothing was lost.”",
                "Treats absence as continuation instead of failure.",
            ],
            [
                "“This answer is more specific than the earlier version.”",
                "Shows improvement from linked records rather than praise.",
            ],
            [
                "“Same challenge, different season.”",
                "Reveals recurrence without diagnosing the person.",
            ],
            [
                "“This result supports a story you may want to practice.”",
                "Connects confirmed work to a truthful practice route.",
            ],
            [
                "“One small contribution is enough today.”",
                "Keeps the entry cost tiny without implying obligation.",
            ],
            [
                "“This connects to a Focus Theme you chose.”",
                "Makes a member-chosen intention visible without becoming an identity "
                "label.",
            ],
        ],
        start_index=1,
    )

    # --- Section 12: architecture ----------------------------------------
    doc.after_para(
        "Preserved v1.5.1 reference: modular monolith",
        para(
            "The connected experience shall be implemented through the existing "
            "modular monolith using authorized relationship resolution, canonical "
            "references, projection services, activation contracts, and "
            "temporal-return services. A shared UI component may render the "
            "relationship, but the browser may not decide ownership, audience, source "
            "eligibility, or truth state."
        )
        + para(
            "The detailed logical contract belongs in the Architecture and Data "
            "Standard, not the Bible. The seven non-negotiable rules below are "
            "unchanged; this rule applies rules 1, 2, and 3 to connective context "
            "rather than creating an exception to any of them."
        ),
    )
    doc.after_table(
        "Premature microservices, Kubernetes, broad semantic/vector infrastructure",
        callout(
            "NO NEW SYSTEM OF RECORD",
            "The proof graph is not a separate product, destination, or database "
            "truth. It is the governed relationship and placement capability that "
            "emerges from the canonical Slate. It shall be recorded as an acceptance "
            "outcome of PS-PLACEMENT-001 and later connected-view packages rather "
            "than a new aggregate.",
        ),
    )

    # --- Section 14: mandatory requirements ------------------------------
    doc.after_para(
        "PS-CORE-VAL-004",
        requirement(
            "PS-CORE-VAL-005",
            "PeerSlate shall create return value through useful memory, preparation, "
            "reflection, and gentle continuation and shall not use guilt, loss "
            "framing, punitive streak recovery, public consistency pressure, or "
            "popularity manipulation.",
        ),
    )
    doc.after_para(
        "PS-CORE-IA-012",
        requirement(
            "PS-CORE-IA-013",
            "Every primary room shall identify its role, viewer or audience mode, "
            "applicable truth state, permitted source context, and one best next "
            "action at the appropriate depth.",
        )
        + requirement(
            "PS-CORE-IA-014",
            "Connected-room components shall use the same interaction grammar with "
            "mode-aware, server-authorized payloads and shall not retrieve private "
            "context for client-side filtering.",
        )
        + requirement(
            "PS-CORE-IA-015",
            "A focused task room shall not be interrupted by unrelated "
            "cross-promotion; connective actions shall appear at natural orientation "
            "or completion boundaries and shall default to one primary action and no "
            "more than two secondary actions.",
        )
        + requirement(
            "PS-CORE-IA-016",
            "When sufficient confirmed history exists, PeerSlate shall support "
            "finite, source-linked temporal continuity through resurfacing, Then and "
            "Now, Replay, or a related next step without guilt or diagnostic claims.",
        ),
    )
    doc.after_para(
        "PS-CORE-FR-008",
        requirement(
            "PS-CORE-FR-009",
            "An eligible deep-room completion shall provide a truthful continuation "
            "or return path appropriate to the current mode, persistence boundary, "
            "and available authorized context.",
        )
        + requirement(
            "PS-CORE-FR-010",
            "Retained voice Capture shall enter the same review and lifecycle "
            "architecture as text and shall provide editable transcript, visible "
            "privacy and source state, correction, deletion, and text fallback; "
            "optional generated titles or summaries shall remain reviewable "
            "proposals.",
        ),
    )
    doc.after_para(
        "PS-CORE-DATA-006",
        requirement(
            "PS-CORE-DATA-007",
            "Cross-room relationships, placements, Backstory links, practice links, "
            "and temporal comparisons shall reference canonical records or exact "
            "governed versions and shall not copy authoritative facts into a second "
            "room-specific truth.",
        ),
    )
    doc.after_para(
        "PS-CORE-AI-006",
        requirement(
            "PS-CORE-AI-007",
            "Personalized prompts, resurfacing suggestions, and return "
            "recommendations shall be based on authorized source context, explain "
            "their relevance when material, disclose uncertainty, and allow "
            "dismissal, correction, or “not useful” feedback.",
        ),
    )
    doc.after_para(
        "PS-CORE-NFR-007",
        requirement(
            "PS-CORE-NFR-008",
            "Connected-room elements shall preserve primary-task speed and "
            "comprehension and shall pass mobile, keyboard, screen-reader, zoom, "
            "reduced-motion, long-content, empty, restricted, stale, deleted-source, "
            "and provider-failure states.",
        )
        + requirement(
            "PS-CORE-NFR-009",
            "PeerSlate shall measure connected-system and return-value behavior "
            "through privacy-safe events that exclude private payloads and shall "
            "include guardrails for time-to-task, privacy confusion, abandonment, "
            "pressure, and cognitive overload.",
        ),
    )
    doc.after_para(
        "PS-CORE-GOV-007",
        requirement(
            "PS-CORE-GOV-008",
            "Every connective or retention idea shall have an explicit status of "
            "Locked/Current, Open, Later, Tabled, or Rejected for the current "
            "program, and no documentation or demonstration may imply implementation "
            "authorization from preservation alone.",
        ),
    )

    # --- Section 16: metrics ---------------------------------------------
    doc.rows_after(
        "Human outcomes",
        [
            [
                "Cross-room continuation",
                "Does meaningful movement occur from Resume, Story, Studio, Work, or "
                "Home into a related approved action?",
            ],
            [
                "Record reuse",
                "Do confirmed records support two or more approved placements, "
                "projections, or actions without copied facts?",
            ],
            [
                "First-minute value",
                "Does the member reach one useful result quickly?",
            ],
            [
                "Studio loop completion",
                "Does answer, review, improve or retry, and a related next action "
                "complete?",
            ],
            [
                "Return after deep-room use",
                "Does the member return after Studio, Resume, Story, or Work use?",
            ],
            [
                "Resurfaced-memory continuation",
                "Does the member open, inspect, dismiss, connect, practice, save, or "
                "act from Then and Now or Replay?",
            ],
            [
                "Voice review rate",
                "Do voice Captures reach transcript review and confirmation rather "
                "than abandonment?",
            ],
            [
                "Recovery after absence",
                "Does return and completion occur after a missed period without "
                "pressure or loss framing?",
            ],
            [
                "Connected-system comprehension",
                "Can the member explain how the current room relates to the larger "
                "Slate?",
            ],
        ],
        start_index=1,
    )
    doc.after_para(
        "Use production cost, latency, reliability, and support burden",
        bullets(
            [
                "Primary task completion time must not materially worsen.",
                "Public/private and live/planned comprehension must not decline.",
                "Added connective elements must not create visual overload, duplicate "
                "calls to action, or generic “Explore” clutter.",
                "No private relationship, source, prompt, or temporal inference may "
                "appear in public payloads.",
                "No return mechanic may be judged successful if it increases guilt, "
                "confusion, or unwanted notifications.",
            ]
        ),
    )

    # --- Section 19: decision classification -----------------------------
    doc.after_para(
        "Material user-facing completion requires both objective technical evidence",
        bullets(
            [
                "Every page should feel like a different use of the same life.",
                "Stronger trunk, not more branches.",
                "Focused rooms connected by a visible spine.",
                "Create once, place many through canonical references.",
                "Same interaction grammar, mode-aware authorized payload.",
                "One best bridge, no wall of recommendations.",
                "Relationship before promotion.",
                "Temporal continuity through memory, Replay, and useful next steps.",
                "Momentum hooks, not pressure hooks.",
                "Expression-first, modality-flexible voice and text parity.",
                "Return value must remain private-first, source-linked, finite, "
                "dismissible, and non-diagnostic.",
                "The proof graph is an outcome of canonical placement, not a new "
                "product truth.",
            ]
        ),
    )
    doc.after_para(
        "First paid capability after credits, based on observed member value.",
        bullets(
            [
                "Exact visual form and canonical name of the Slate Spine.",
                "Whether the first public connectedness pilot is a new package or an "
                "amendment to active Resume/Studio packages.",
                "Which three to five Resume achievements receive Backstory Drawers.",
                "Whether public Studio support is curated configuration or "
                "projection-backed after canonical services mature.",
                "Exact owner-mode Return Ticket actions and storage.",
                "Exact cadence and user controls for Replay and resurfacing.",
                "Whether Focus Themes are fixed, member-authored, AI-suggested, or "
                "hybrid.",
                "Whether Progress Keepsakes live inside Replay, My Slate, Story, or a "
                "private collection view.",
                "Whether a soft consistency visualization is useful without becoming "
                "a streak.",
                "Notification policy, channels, timing, and opt-in defaults.",
                "Raw-audio retention and voice-processing disclosures.",
            ]
        ),
    )
    doc.after_para(
        "PS-STORY-COMPOSER-001 — Member-directed Story composition with "
        "owner-scoped",
        bullets(
            [
                "Then and Now across Home, Story, Studio, and Work.",
                "Focus Themes.",
                "Progress Keepsakes.",
                "Prompt DNA.",
                "Signal Cards.",
                "Guided journeys or challenge-free challenges.",
                "Future Me text or voice messages.",
                "Walk-and-Talk, Story Mode, Duet With Your Past Self, Voice "
                "Keepsakes, and private growth reels.",
                "Companion or worldbuilding prototype after retention is measured.",
                "Buddy Reflection after the two-person trust loop is proven.",
            ]
        ),
    )
    doc.after_table(
        "FITSLATE",
        bullets(
            [
                "Literal pet companion.",
                "Garden, constellation, path, room, studio, or archive that grows "
                "with contribution.",
                "Public or connection-visible consistency.",
                "Social accountability beyond one trusted person.",
                "Private circles, prompt swaps, or shared themes.",
                "Mood Soundprint or prosody visualization.",
                "Celebration readback.",
                "Ambient soundscape rituals.",
            ]
        )
        + small_note(
            "Tabled means preserved for reconsideration, not authorized."
        )
        + heading("Rejected for the current program", 2)
        + para(
            "These are not necessarily banned forever. They conflict with current "
            "principles or sequencing, and the rationale is preserved in the Decision "
            "Register."
        )
        + bullets(
            [
                "Hard or loss-framed streaks.",
                "Points, badges, levels, public consistency counts, or trophy "
                "cabinets.",
                "Confetti as the default reward.",
                "Guilt reminders, “you are falling behind,” or punitive "
                "recovery.",
                "Infinite feeds, trending modules, popularity ranking, or "
                "variable-reward rails.",
                "Generic “Explore more” or “You may also like” "
                "modules without a meaningful relationship.",
                "A universal AI sidebar or a separate global Insights or Engagement "
                "destination.",
                "Automatic Resume, Story, Project, Feed, or public publication from "
                "Capture or AI.",
                "Room-specific copied facts or separate Resume/Story/Studio truth "
                "stores.",
                "Emotional diagnosis, mental-health inference, or certainty claims "
                "from voice prosody.",
                "Indefinite raw-audio retention without explicit purpose and member "
                "control.",
                "Fabricated people, counts, history, activity, insights, or "
                "cross-room relationships.",
                "Turning on currently disabled or flag-off features through "
                "documentation work.",
                "Broad public redesign before the approved entry gate.",
                "Using social mechanics to compensate for an incomplete owner loop.",
                "Expanding Projects into a task-management suite.",
            ]
        ),
    )

    # --- Appendices M and N ----------------------------------------------
    extra_media: dict[str, bytes] = {}
    diagram_block = ""
    if os.path.exists(DIAGRAM):
        width_px, height_px = png_size(DIAGRAM)
        target_cx = 6217920
        target_cy = int(target_cx * height_px / width_px)
        media_name = "word/media/image_connected_system.png"
        with open(DIAGRAM, "rb") as handle:
            extra_media[media_name] = handle.read()
        rel_id = "rIdConnectedSystem"
        rels = rels.replace(
            "</Relationships>",
            f'<Relationship Id="{rel_id}" Type="http://schemas.openxmlformats.org/'
            'officeDocument/2006/relationships/image" '
            'Target="media/image_connected_system.png"/></Relationships>',
        )
        diagram_block = (
            '<w:p><w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:drawing>'
            '<wp:inline distT="0" distB="0" distL="0" distR="0">'
            f'<wp:extent cx="{target_cx}" cy="{target_cy}"/>'
            '<wp:effectExtent l="0" t="0" r="0" b="0"/>'
            '<wp:docPr id="900" name="Connected system architecture" '
            'descr="PeerSlate connected-system loop: original source, member review, '
            "canonical Slate, authorized relationship or placement, focused room or "
            "projection, activation, outcome and learning, return value, and new "
            'contribution." title="PeerSlate connected-system architecture"/>'
            "<wp:cNvGraphicFramePr><a:graphicFrameLocks "
            'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            'noChangeAspect="1"/></wp:cNvGraphicFramePr>'
            '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            '<pic:nvPicPr><pic:cNvPr id="0" name="connected-system.png"/>'
            "<pic:cNvPicPr/></pic:nvPicPr><pic:blipFill>"
            f'<a:blip r:embed="{rel_id}"/><a:stretch><a:fillRect/></a:stretch>'
            '</pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/>'
            f'<a:ext cx="{target_cx}" cy="{target_cy}"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
            "</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>"
            + small_note(
                "Figure N-1. The connected-system loop, preserved as "
                "source/peerslate_connected_system_architecture.png with the owner "
                "handoff."
            )
        )
    else:
        diagram_block = small_note(
            "Figure N-1 is preserved as "
            "source/peerslate_connected_system_architecture.png with the owner "
            "handoff. It was not available to this build and is described in full "
            "below."
        )

    doc.append_to_body(
        heading("Appendix M - Connected-system and return-value covenant", 1)
        + para(
            "PeerSlate's hook strategy and architecture strategy are the same "
            "strategy: capture something real once, preserve what is true, connect it "
            "by reference, use it in a focused room, and return later to see what "
            "changed and take one worthwhile next step."
        )
        + heading("Constitutional acceptance rule", 2)
        + bullets(
            [
                "Every major room shows what it is for, whose space and which truth "
                "state the viewer is in, where its material came from, how it relates "
                "to the larger Slate, and one best safe next move.",
                "Connection is created by canonical reference and member-directed "
                "action. No room copies another room's authoritative facts.",
                "Public and owner modes use the same interaction grammar with "
                "different server-authorized payloads. Private context is never sent "
                "to the browser to be filtered there.",
                "A focused task is not interrupted. The default connective budget is "
                "one primary bridge and at most two secondary paths.",
                "Return value is private-first, source-linked, finite, dismissible, "
                "and non-diagnostic. Absence is continuation, not failure.",
                "The proof graph is an outcome of governed placement, not a new "
                "system of record or destination.",
            ]
        )
        + heading("Current operational control", 2)
        + para(
            "The connective patterns, mode and state behavior, and logical contract "
            "are maintained in the Experience System and the Architecture and Data "
            "Standard. As of this candidate, no connective pattern is implemented, "
            "assigned, deployed, enabled, or live. Slate Spine, Backstory Drawer, "
            "Studio Return Ticket, Then and Now, Focus Themes, and Progress Keepsakes "
            "have no manager, writer, branch, schema, route, accepted visual "
            "authority, or release. Preservation in this Bible is not implementation "
            "authorization."
        )
        + heading("Appendix N - Connected-system architecture map", 1)
        + para(
            "A high-level constitutional map only. Detailed contracts, schemas, "
            "services, and allocation belong in the Architecture and Data Standard."
        )
        + callout(
            "THE LOOP",
            "Original Source, then Member Review, then Canonical Slate, then "
            "Authorized Relationship or Placement, then Focused Room or Projection, "
            "then Activation, then Outcome, then Return Value, then New "
            "Contribution.",
        )
        + diagram_block
        + grid_table(
            ["#", "Layer", "What it holds"],
            [
                [
                    "1",
                    "Original source",
                    "Voice, text, photo, file, imported context.",
                ],
                [
                    "2",
                    "Review and canonical",
                    "Original preserved; proposal reviewed; member-confirmed Moment "
                    "and related canonical objects.",
                ],
                [
                    "3",
                    "Authorized relationship and placement",
                    "Exact-version references, provenance, lifecycle, audience, "
                    "purpose, sensitivity, and eligibility.",
                ],
                [
                    "4",
                    "Focused rooms and projections",
                    "Journal, Story, Work, Projects, Resume, Studio, Slate, Feed, and "
                    "public or permissioned views.",
                ],
                [
                    "5",
                    "Activation",
                    "Use This Moment, practice, manager or update draft, share, "
                    "export, Project connection, Story selection, next step.",
                ],
                [
                    "6",
                    "Outcome and learning",
                    "Completion, usefulness, correction, dismissal, staleness, "
                    "contradiction, revocation, deletion.",
                ],
                [
                    "7",
                    "Return value",
                    "Finite Home, recent and resurfaced Moment, Then and Now, Replay, "
                    "source-linked prompt, Focus Theme, future revisit.",
                ],
                [
                    "8",
                    "New contribution",
                    "The member captures the next Moment because the system made "
                    "prior contribution useful.",
                ],
            ],
            [720, 2520, 6840],
        )
        + para(
            "Cross-cutting controls: trusted server identity; authorization before "
            "retrieval; private-by-default storage; exact audience preview; "
            "canonical, interpretation, and projection separation; the AI proposal "
            "and evaluation lifecycle; accessibility and failure parity; privacy-safe "
            "telemetry; and feature flags, rollout, rollback, and deletion "
            "propagation."
        )
        + small_note(
            "This map describes the intended model. It is not a claim about current "
            "capability. Layers 5 through 8 are not implemented."
        )
    )

    repack(BIBLE_SRC, BIBLE_OUT, doc.xml, extra_media, rels)
    return doc.xml


# --------------------------------------------------------------------------
# candidate Roadmap v2.6
# --------------------------------------------------------------------------


def build_roadmap() -> str:
    with zipfile.ZipFile(ROADMAP_SRC) as archive:
        document = archive.read("word/document.xml").decode("utf-8")
    doc = Doc(document)

    doc.replace_text(
        "v2.5 - Projects System Architecture",
        "v2.6 - Connected-System Sequencing (PROPOSED)",
    )
    doc.replace_text("July 19, 2026", "July 20, 2026")
    doc.replace_text(
        "CURRENT - OWNER-APPROVED SEQUENCE, STORY, AND PROJECTS ARCHITECTURE",
        "PROPOSED - CANDIDATE AWAITING OWNER APPROVAL; v2.5 REMAINS CURRENT",
    )
    doc.replace_text(
        "v2.4 Story roadmap + Bible v2.6 + July 19 Projects system decision",
        "v2.5 sequencing + candidate Bible v2.7 + July 20 connected-system decision",
    )
    doc.replace_text(
        "Roadmap authority: v2.5 is the current sequence and architecture when named "
        "by CURRENT_BASELINE.yaml. Historical package IDs and release evidence remain "
        "preserved; PS-STORY-COMPOSER-001 and PS-PROJECTS-001 are planned future "
        "work, not active.",
        "Roadmap authority: v2.6 is a CANDIDATE. v2.5 remains the current sequence "
        "and architecture until Pete approves this candidate and CURRENT_BASELINE.yaml "
        "names it. Historical package IDs and release evidence remain preserved. "
        "PS-STORY-COMPOSER-001, PS-PROJECTS-001, PS-ASK-PETE-AI-001, and every "
        "connective package named in Appendix G are planned or candidate work, not "
        "active.",
    )
    doc.relabel_status_band(
        "Roadmap authority: v2.6 is a CANDIDATE.", "LOCKED", "PROPOSED"
    )
    doc.replace_text(
        "Approval note: this v2.5 roadmap preserves the verified production, "
        "visual-integrity, and member-directed Story baseline and adds the "
        "owner-approved Projects architecture: a private Project Workspace, "
        "exact-version canonical links, member-controlled lifecycle, separately "
        "versioned Project Projections, optional AI proposals, and no task-management "
        "expansion.",
        "Approval note: this v2.6 candidate preserves every v2.5 phase, package, "
        "status, release record, and production claim exactly, and adds one "
        "sequencing amendment for the connected-system and return-value direction. It "
        "advances nothing to Complete, starts nothing, and changes no live status. "
        "v2.5 remains current until Pete approves this candidate.",
    )
    doc.mark_toc_dirty()

    doc.rows_after(
        "Logged-out product/pitch homepage and public Slate/Story/Work/gated "
        "surfaces aligned to approved owner-system quality",
        [
            [
                "PS-PUBLIC-CONNECTIVE-001",
                "1 / 10 / cross-phase",
                "Public connectedness pilot",
                "CANDIDATE - not authorized, unassigned. Connected-room orientation "
                "on selected public Resume, Story, and Studio states; three to five "
                "Resume Backstory Drawers; public-safe practice bridges; a Studio "
                "Return Ticket truthful to browser-local behavior.",
            ],
            [
                "PS-CONNECTIVE-COMPONENT-001",
                "10 / cross-phase",
                "Shared connective component foundation",
                "CANDIDATE - blocked behind the public pilot. One reusable "
                "server-rendered component contract that accepts a resolved "
                "authorized view model.",
            ],
            [
                "PS-RETURN-VALUE-001",
                "9 / 10",
                "Private return-value engine",
                "CANDIDATE - blocked behind the Owner Home frontend and real "
                "confirmed history. One Capture action, one small prompt, one recent "
                "and one resurfaced Moment, one source-linked observation when "
                "warranted, one next step, and welcome-back behavior with no loss "
                "framing.",
            ],
        ],
        start_index=1,
    )
    doc.after_para(
        "Planned governed extension: PS-PROJECTS-001",
        para(
            "Appendix G carries the priority bands and entry conditions for the three "
            "candidate connective packages above. Presence in this register is not "
            "authorization: none has a manager, writer, branch, entry gate, schema, "
            "accepted mockup, or start date."
        ),
    )
    doc.after_para(
        "Do not call work Complete because the happy-path page looks polished.",
        bullets(
            [
                "Do not build a generic “related content,” “explore "
                "more,” or “you may also like” rail in place of a "
                "meaningful, authorized relationship.",
                "Do not build a streak meter, points, badges, or a loss-framed return "
                "mechanic.",
                "Do not start a connective pattern before the public pilot's entry "
                "gate, production-intent mockups, and an assigned manager and writer "
                "exist.",
                "Do not implement Then and Now before confirmed history, source "
                "authorization, contradiction handling, and correction behavior are "
                "mature.",
            ]
        ),
    )

    doc.append_to_body(
        heading("Appendix G - Connected-system and return-value direction amendment", 1)
        + callout(
            "SEQUENCING ONLY",
            "The connected-system direction is a sequencing amendment, not a new "
            "phase and not a new product tree. Every item below is documentation-stage "
            "work or a candidate package. Nothing here is authorized, assigned, "
            "scheduled, started, deployed, enabled, or live.",
        )
        + heading("Priority 0 - Do now: documentation and authority synchronization", 2)
        + grid_table(
            ["#", "Action", "State"],
            [
                [
                    "1",
                    "Create candidate Bible v2.7 with the connected-system "
                    "constitutional language.",
                    "Delivered as PROPOSED by PS-GOV-CONNECTED-SYSTEM-001.",
                ],
                [
                    "2",
                    "Update the Roadmap candidate for connected-system priorities "
                    "without changing live statuses.",
                    "Delivered as PROPOSED by this document.",
                ],
                [
                    "3",
                    "Add the high-level architecture map to the Bible appendix and the "
                    "detailed logical contract to the Architecture and Data Standard.",
                    "Delivered as PROPOSED: Bible Appendix N and package file 03.",
                ],
                [
                    "4",
                    "Add the six connective patterns to the Experience System.",
                    "Delivered as PROPOSED: package file 04.",
                ],
                [
                    "5",
                    "Add a Decision Register entry with rationale, alternatives, "
                    "risks, and supersession language.",
                    "Staged for append at activation: package file 05.",
                ],
                [
                    "6",
                    "Create the research to principle/requirement to phase/package to "
                    "artifact crosswalk.",
                    "Delivered: package file 06.",
                ],
            ],
            [720, 5400, 3960],
        )
        + heading(
            "Priority 1 - First bounded implementation candidates after explicit "
            "assignment",
            2,
        )
        + para(
            "Shared Slate Spine or connected-room orientation for selected public "
            "Resume, Story, and Studio states; three to five Resume Backstory Drawers "
            "for anchor achievements only; “Practice telling this” bridges "
            "from selected Resume claims to the exact live Studio route and its "
            "current public behavior; a public-safe “Behind this answer” "
            "relationship in Studio where support already exists; and a post-review "
            "Studio Return Ticket appropriate to public and browser-local truth.",
            lead="A. Public connectedness pilot, candidate PS-PUBLIC-CONNECTIVE-001. ",
        )
        + para(
            "Account-backed Studio history; private Journal or owner history; new "
            "persistence; new database schema unless separately approved; broad public "
            "redesign; generic related-content rails; and more than one primary and "
            "two secondary actions per state.",
            lead="Out of scope. ",
        )
        + para(
            "The repository confirms current Resume and Studio routes and active "
            "initiative boundaries; production-intent mockups are accepted; every "
            "relationship is public-safe and either curated or sourced from an "
            "approved projection; and no current package is silently reopened or "
            "modified without owner assignment.",
            lead="Entry gate. ",
        )
        + para(
            "PS-HOME-INTERVIEW-PARITY-001 remains a separate bounded package under "
            "its own manager and writer. This amendment does not expand, absorb, "
            "reassign, accelerate, or alter it. It must continue to map the accepted "
            "homepage walkthrough to the exact live Studio without changing Studio "
            "behavior or implying private history.",
            lead="B. Homepage Interview convergence. ",
        )
        + para(
            "Create one reusable server-rendered, Jinja-compatible component contract "
            "only after the public pilot is approved. It must accept resolved "
            "authorized view models rather than query arbitrary data in the template "
            "or the browser.",
            lead="C. Shared connective component foundation, candidate "
            "PS-CONNECTIVE-COMPONENT-001. ",
        )
        + heading("Priority 2 - Build next: canonical relationship foundation", 2)
        + para(
            "The connected or proof graph is an acceptance outcome of packages that "
            "already exist. It is not a new package, aggregate, or destination."
        )
        + grid_table(
            ["Package", "Contribution", "Current recorded state"],
            [
                [
                    "PS-CAPTURE-002",
                    "Lifecycle and original preservation",
                    "Complete; PR 63 / pipeline 85",
                ],
                [
                    "PS-MOMENT-001",
                    "Member-confirmed canonical Moment",
                    "Complete; PR 66 / pipeline 91",
                ],
                [
                    "PS-PLACEMENT-001",
                    "Exact-version create-once / place-many references",
                    "Backend foundation live; PR 68 / pipeline 93; no UI consumer",
                ],
                [
                    "PS-ACTION-CORE-001, PS-ACTION-STUDIO-001",
                    "Truthful continuation actions",
                    "Candidate IDs; not defined, assigned, or authorized",
                ],
            ],
            [2880, 3240, 3960],
        )
        + para("Required outcomes before the graph may be claimed:")
        + bullets(
            [
                "Correction, deletion, revocation, and audience changes propagate.",
                "Relationships never grant access by themselves.",
                "Relationship labels derive from governed types, not copied prose.",
                "Connected rooms request authorized context through shared services.",
                "Public and owner payloads use the same grammar with different "
                "permitted context.",
            ]
        )
        + heading(
            "Priority 3 - Build after Owner Home frontend and real confirmed history", 2
        )
        + para(
            "one obvious Capture action; one small prompt or check-in; one recent and "
            "one resurfaced Moment; one concise source-linked observation when "
            "warranted; one next step; and welcome-back behavior after absence with no "
            "loss framing. Do not start with a streak meter. Validate that memory, "
            "usefulness, and one clear next action create return value first.",
            lead="Private return-value engine, candidate PS-RETURN-VALUE-001 - first "
            "slice: ",
        )
        + para(
            "Implement as a Replay or Home/Story/Studio pattern only after confirmed "
            "history, source authorization, contradiction handling, and correction "
            "behavior are mature.",
            lead="Then and Now. ",
        )
        + para(
            "PS-MIA-REPLAY-001 remains the preferred finite weekly, monthly, or "
            "period narrative. It must show movement, a few Moments, missing context, "
            "and one next action rather than a dashboard of scores.",
            lead="Replay. ",
        )
        + para(
            "PS-HOME-FRONTEND-001 is activated with a writer branch pending and Owner "
            "Home remains default-off. Nothing in this band may begin while that is "
            "true.",
            lead="Blocking dependency. ",
        )
        + heading("Priority 4 - Later experiments after the return loop is proven", 2)
        + para(
            "Focus Themes as a private cross-room overlay; Progress Keepsakes as "
            "references rather than copied records or a new destination; voice delight "
            "rituals after transcript, review, privacy, retention, and failure "
            "behavior are proven; Future Voice Mail, Duet With Your Past Self, Voice "
            "Keepsakes, and private growth reels; Prompt DNA and Signal Cards after "
            "enough history and model-governance evidence exists; and optional "
            "challenge-free journeys with no failure state."
        )
        + heading("Priority 5 - On the fence: preserve for later evaluation", 2)
        + para(
            "Companion or worldbuilding layer; a private constellation, archive, path, "
            "room, garden, or trail that evolves; Buddy Reflection or trusted-person "
            "accountability; small private circles or prompt swaps; soft consistency "
            "visualization; future-self messages; soundscape pairing; and celebration "
            "readback."
        )
        + callout(
            "PRESERVED, NOT AUTHORIZED",
            "Each Priority 4 and Priority 5 idea requires an explicit hypothesis, "
            "prototype, trust review, and evidence that it strengthens the private "
            "owner loop without infantilization, distraction, privacy burden, or "
            "engagement pressure.",
        )
        + heading("Verification expectations for any derived package", 2)
        + para(
            "Route and payload tests for owner, selected person, connection, "
            "authenticated member, and public modes; cross-user negative tests and "
            "no-client-filtering evidence; exact-version reference and no-content-copy "
            "tests; deleted, revoked, stale, restricted, and unavailable source "
            "behavior; AI unsupported-claim and provider-outage behavior; "
            "browser-local versus server-persistent truth tests; mobile, keyboard, "
            "screen-reader, 200-percent zoom, reduced-motion, long-content, empty, "
            "error, and retry states; privacy-safe telemetry tests proving no private "
            "payload, transcript, answer, source content, or relationship detail leaks "
            "into logs; visual comparison to the named production-intent authority; "
            "and rollback and feature-flag behavior where applicable."
        )
        + heading("Validation scenarios", 2)
        + bullets(
            [
                "A public visitor opens a Resume Backstory, understands how it "
                "relates to Story or Studio, and sees no private material.",
                "A public Studio user finishes Review and receives a truthful Return "
                "Ticket that does not imply account-backed persistence.",
                "An owner sees the same component grammar with private authorized "
                "context and understands who can see the result.",
                "Pete and Danielle cannot retrieve each other's private "
                "relationships, prompts, history, or Returns.",
                "A deleted or revoked source disappears from downstream connection "
                "modules and Keepsakes according to policy.",
                "A user can ignore or dismiss a resurfaced item with no pressure.",
                "A user returns after an absence and completes one useful action "
                "without seeing loss language.",
                "A user can explain in plain language how the current room relates to "
                "the larger Slate.",
                "A user completes the primary room task at least as quickly as before "
                "the connective layer.",
                "AI or speech failure leaves the essential room, source inspection, "
                "and safe next action usable.",
            ]
        )
        + heading("Current control", 2)
        + para(
            "The connected-room logical contract is maintained in "
            "docs/initiatives/PS-GOV-CONNECTED-SYSTEM-001/"
            "03_ARCHITECTURE_AND_DATA_STANDARD_CONNECTED_SYSTEM.md. The connective "
            "patterns are maintained in the same package's "
            "04_EXPERIENCE_SYSTEM_CONNECTIVE_PATTERNS.md. Both are PROPOSED. No "
            "connective package is active, and no live status in this Roadmap "
            "changed."
        )
    )

    repack(ROADMAP_SRC, ROADMAP_OUT, doc.xml, {})
    return doc.xml


# --------------------------------------------------------------------------
# verification
# --------------------------------------------------------------------------


def verify(path: str, required: list[str], forbidden: list[str]) -> None:
    """Reopen the built package, parse it, and confirm its rendered text."""
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise SystemExit(f"{path}: corrupt member {bad}")
        for member in archive.namelist():
            if member.endswith(".xml") or member.endswith(".rels"):
                ElementTree.fromstring(archive.read(member))
        root = ElementTree.fromstring(archive.read("word/document.xml"))
    text = "\n".join(node.text or "" for node in root.iter(W + "t"))
    missing = [item for item in required if item not in text]
    present = [item for item in forbidden if item in text]
    if missing:
        raise SystemExit(f"{path}: missing expected text: {missing}")
    if present:
        raise SystemExit(f"{path}: forbidden text still present: {present}")
    print(f"  verified {os.path.basename(path)}: XML parses, {len(text)} chars of text")


def main() -> int:
    for source in (BIBLE_SRC, ROADMAP_SRC):
        if not os.path.exists(source):
            raise SystemExit(f"missing source document: {source}")
    print("building candidate Bible v2.7 (PROPOSED)…")
    build_bible()
    print("building candidate Roadmap v2.6 (PROPOSED)…")
    build_roadmap()

    verify(
        BIBLE_OUT,
        required=[
            "v2.7 - Connected System and Return-Value Authority (PROPOSED)",
            "PROPOSED - CANDIDATE AWAITING OWNER APPROVAL; v2.6 REMAINS CURRENT",
            "Every page should feel like a different use of the same life.",
            "Authority: v2.7 is a CANDIDATE and is not controlling.",
            "PS-P-015",
            "PS-P-016",
            "PS-CORE-VAL-005",
            "PS-CORE-IA-016",
            "PS-CORE-FR-010",
            "PS-CORE-DATA-007",
            "PS-CORE-AI-007",
            "PS-CORE-NFR-009",
            "PS-CORE-GOV-008",
            "The connected-system spine",
            "Relationship before promotion",
            "The connected-room contract",
            "Focused but not orphaned",
            "The temporal spine",
            "Connected-room patterns",
            "The return-value engine",
            "Expression-first and modality-flexible",
            "Momentum hooks, not pressure hooks",
            "Rejected for the current program",
            "Appendix M - Connected-system and return-value covenant",
            "Appendix N - Connected-system architecture map",
            "Raw-audio retention and voice-processing disclosures.",
            # v2.6 content that must survive untouched
            "Appendix L - Projects system covenant",
            "PS-CORE-GOV-014",
            "PS-P-001",
            "FitSlate is preserved as a possible future member-first extension",
            "Deep Navy Gold is the approved shared design foundation",
        ],
        forbidden=[
            "v2.6 - Projects System Authority",
            "CURRENT - OWNER-APPROVED PRODUCT, VISUAL, STORY, AND PROJECTS AUTHORITY",
        ],
    )
    verify(
        ROADMAP_OUT,
        required=[
            "v2.6 - Connected-System Sequencing (PROPOSED)",
            "PROPOSED - CANDIDATE AWAITING OWNER APPROVAL; v2.5 REMAINS CURRENT",
            "Appendix G - Connected-system and return-value direction amendment",
            "Roadmap authority: v2.6 is a CANDIDATE.",
            "PS-PUBLIC-CONNECTIVE-001",
            "PS-CONNECTIVE-COMPONENT-001",
            "PS-RETURN-VALUE-001",
            "Appendix F - Projects system direction amendment",
            "PS-PUBLIC-VISUAL-001",
        ],
        forbidden=[
            "v2.5 - Projects System Architecture",
            "CURRENT - OWNER-APPROVED SEQUENCE, STORY, AND PROJECTS ARCHITECTURE",
        ],
    )
    print("done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
