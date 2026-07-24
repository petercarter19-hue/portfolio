#!/usr/bin/env python3
"""Deterministically materialize a controlled DOCX authority as Markdown.

This converter intentionally does not edit the source DOCX.  It preserves the
document-body order, headings, numbered and bulleted lists, tables, callouts,
captions, external hyperlinks, and inline images well enough for a repository
authority record.  Word-generated TOC and page-number fields are represented
as ordinary text only when they have visible cached text; they are not rebuilt.

Usage:
  python tools/convert_authority_docx_to_markdown.py \
      docs/governance/source.docx docs/governance/output.md \
      --media-dir docs/governance/authority-media/source
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Iterator

from docx import Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph
from lxml import etree


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
NS = {"w": W_NS, "r": R_NS, "a": A_NS, "wp": WP_NS}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def markdown_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("|", "\\|")


def inline_markdown(paragraph: Paragraph) -> str:
    """Render runs and external Word hyperlinks without dropping visible text."""
    rels = paragraph.part.rels
    fragments: list[str] = []
    # lxml's generated OOXML classes expose ``itertext`` differently from the
    # ordinary lxml elements and can repeat every ``w:t`` node.  Select the
    # visible text nodes directly instead.  Deliberately omit field-code text:
    # Word's generated TOC/page-number instructions are not controlling body
    # content and the cached display text is still retained when present.
    def visible_text(element) -> str:
        return "".join(element.xpath(".//w:t/text()"))

    for child in paragraph._p:
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "r":
            text = visible_text(child)
            if text:
                fragments.append(text)
        elif tag == "hyperlink":
            text = visible_text(child)
            rel_id = child.get(f"{{{R_NS}}}id")
            target = rels[rel_id].target_ref if rel_id in rels else ""
            if target and text:
                fragments.append(f"[{text}]({target})")
            elif text:
                fragments.append(text)
        elif tag in {"smartTag", "sdt", "ins", "del"}:
            text = visible_text(child)
            if text:
                fragments.append(text)
    return clean_text("".join(fragments))


def paragraph_images(paragraph: Paragraph) -> Iterator[tuple[str, str]]:
    """Yield relationship ids and useful author-supplied alt text."""
    for blip in paragraph._p.xpath(".//a:blip"):
        rel_id = blip.get(f"{{{R_NS}}}embed")
        if not rel_id:
            continue
        drawing = blip
        while drawing is not None and drawing.tag != f"{{{W_NS}}}drawing":
            drawing = drawing.getparent()
        alt = ""
        if drawing is not None:
            doc_pr = drawing.find(".//wp:docPr", namespaces=NS)
            if doc_pr is not None:
                alt = clean_text(doc_pr.get("descr") or doc_pr.get("title") or doc_pr.get("name") or "")
        yield rel_id, alt


def iter_body_blocks(document: Document) -> Iterator[Paragraph | Table]:
    parent = document.element.body
    for child in parent.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, document)
        elif isinstance(child, CT_Tbl):
            yield Table(child, document)


def list_descriptor(paragraph: Paragraph) -> tuple[bool, str, int] | None:
    """Return the list kind, Word numbering identity, and nesting level."""
    style = (paragraph.style.name or "").lower()
    ppr = paragraph._p.pPr
    num_pr = ppr.numPr if ppr is not None else None
    if num_pr is None and "list bullet" not in style and "list number" not in style:
        return None

    level = 0
    num_id = "style"
    if num_pr is not None:
        ilvl = num_pr.ilvl
        num = num_pr.numId
        level = int(ilvl.val) if ilvl is not None and ilvl.val is not None else 0
        num_id = str(num.val) if num is not None and num.val is not None else "style"

    bullet = "bullet" in style
    if "number" in style:
        bullet = False
    if num_pr is not None:
        # Word's numbering information is comparatively awkward to expose
        # through python-docx.  Existing numbered list styles reliably map to
        # decimal; unknown custom formats are represented as bullets rather
        # than inventing a number sequence.
        numbering = paragraph.part.numbering_part.element
        num = numbering.find(f".//w:num[@w:numId='{num_id}']", namespaces=NS)
        abstract_id = ""
        if num is not None:
            abstract = num.find("w:abstractNumId", namespaces=NS)
            abstract_id = abstract.get(f"{{{W_NS}}}val") if abstract is not None else ""
        fmt = ""
        if abstract_id:
            fmt_node = numbering.find(
                f".//w:abstractNum[@w:abstractNumId='{abstract_id}']/w:lvl[@w:ilvl='{level}']/w:numFmt",
                namespaces=NS,
            )
            fmt = fmt_node.get(f"{{{W_NS}}}val") if fmt_node is not None else ""
        bullet = fmt == "bullet" if fmt else bullet

    return bullet, num_id, level


def list_marker(
    descriptor: tuple[bool, str, int], counters: dict[tuple[str, int], int]
) -> tuple[str, int]:
    """Render one list marker after its contiguous-list boundary is established."""
    bullet, num_id, level = descriptor
    key = (num_id, level)
    if bullet:
        return "-", level
    counters[key] += 1
    for counter_key in list(counters):
        if counter_key[0] == num_id and counter_key[1] > level:
            counters[counter_key] = 0
    return f"{counters[key]}.", level


def is_automatic_toc_or_page_artifact(
    paragraph: Paragraph, text: str, heading: int | None
) -> bool:
    """Exclude Word-generated TOC/page-number scaffolding from authority text."""
    style = (paragraph.style.name or "").strip().lower()
    instruction = " ".join(paragraph._p.xpath(".//w:instrText/text()")).upper()
    normalized = text.casefold()

    if re.fullmatch(r"toc\s*\d+", style):
        return True
    if "TOC" in instruction or "PAGEREF" in instruction:
        return True
    if heading and normalized == "table of contents":
        return True
    if "this table updates automatically" in normalized and "page number" in normalized:
        return True
    return bool(re.fullmatch(r"\d+", text) and "PAGE" in instruction)


def is_plain_list_continuation(
    paragraph: Paragraph,
    text: str,
    style: str,
    heading: int | None,
    images: list[tuple[str, str]],
    prior_list_text: str | None,
) -> bool:
    """Recognize a wrapped Word list item stored as a plain Normal paragraph.

    Some owner-authored DOCX lists wrap a long item into a following paragraph
    instead of retaining the List Number style.  Treat it as continuation only
    when it has no paragraph properties, starts lower-case, immediately follows
    an unfinished list fragment, and carries no heading or image.  Those narrow
    conditions avoid joining genuine normal paragraphs.
    """
    return bool(
        prior_list_text
        and not prior_list_text.rstrip().endswith((".", ";", ":", "!", "?"))
        and style == "normal"
        and paragraph._p.pPr is None
        and heading is None
        and not images
        and text[:1].islower()
    )


def style_heading(paragraph: Paragraph) -> int | None:
    style = (paragraph.style.name or "").strip().lower()
    match = re.fullmatch(r"heading\s*([1-6])", style)
    if match:
        return int(match.group(1))
    if style in {"title", "subtitle"}:
        return 1 if style == "title" else 2
    return None


def table_markdown(table: Table) -> list[str]:
    rows = []
    for row in table.rows:
        cells = [markdown_escape(clean_text(cell.text)) for cell in row.cells]
        if cells:
            rows.append(cells)
    if not rows:
        return []
    width = max(len(row) for row in rows)
    rows = [row + [""] * (width - len(row)) for row in rows]
    header = rows[0]
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * width) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows[1:])
    return lines


def existing_images(repo: Path, output: Path, media_dir: Path) -> dict[str, Path]:
    result: dict[str, Path] = {}
    excluded = {output.resolve(), media_dir.resolve()}
    for candidate in repo.rglob("*"):
        if not candidate.is_file() or candidate.resolve() in excluded:
            continue
        if candidate.suffix.lower() not in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}:
            continue
        try:
            result.setdefault(sha256(candidate), candidate)
        except OSError:
            continue
    return result


def write_image(part, alt: str, output: Path, media_dir: Path, known_images: dict[str, Path]) -> tuple[str, bool]:
    media_dir.mkdir(parents=True, exist_ok=True)
    blob = part.blob
    digest = hashlib.sha256(blob).hexdigest().upper()
    source_name = Path(part.partname).name
    existing = known_images.get(digest)
    unique = False
    if existing is None:
        target = media_dir / f"{digest[:16]}-{source_name}"
        if not target.exists():
            target.write_bytes(blob)
        existing = target
        known_images[digest] = existing
        unique = True
    relative = os.path.relpath(existing, output.parent).replace(os.sep, "/")
    return f"![{markdown_escape(alt or Path(source_name).stem)}]({relative})", unique


def convert(source: Path, output: Path, media_dir: Path) -> dict[str, int | str]:
    document = Document(source)
    repo = source.parents[2]
    known_images = existing_images(repo, output, media_dir)
    lines = [
        "<!--",
        "Controlled Markdown authority materialized from frozen owner-approved DOCX.",
        f"Source: {source.as_posix()}",
        f"Source SHA-256: {sha256(source)}",
        "Generated by tools/convert_authority_docx_to_markdown.py.",
        "-->",
        "",
    ]
    counters: dict[tuple[str, int], int] = defaultdict(int)
    in_list = False
    active_list_ids: set[str] = set()
    prior_list_text: str | None = None
    stats: Counter[str] = Counter()
    for block in iter_body_blocks(document):
        if isinstance(block, Table):
            rendered = table_markdown(block)
            if rendered:
                lines.extend(rendered)
                lines.append("")
                stats["tables"] += 1
            counters.clear()
            active_list_ids.clear()
            in_list = False
            prior_list_text = None
            continue

        stats["paragraphs"] += 1
        images = list(paragraph_images(block))
        text = inline_markdown(block)
        heading = style_heading(block)
        style = (block.style.name or "").lower()
        if is_automatic_toc_or_page_artifact(block, text, heading):
            counters.clear()
            active_list_ids.clear()
            in_list = False
            prior_list_text = None
            continue
        if text:
            wrote_new_line = True
            if heading:
                lines.append(f"{'#' * heading} {text}")
                counters.clear()
                active_list_ids.clear()
                in_list = False
                prior_list_text = None
            elif "caption" in style:
                lines.append(f"*{text}*")
                stats["captions"] += 1
                counters.clear()
                active_list_ids.clear()
                in_list = False
                prior_list_text = None
            elif "quote" in style or "callout" in style or text.lower().startswith(("requirement:", "must ", "shall ")):
                lines.append(f"> {text}")
                stats["callouts"] += 1
                counters.clear()
                active_list_ids.clear()
                in_list = False
                prior_list_text = None
            else:
                descriptor = list_descriptor(block)
                if descriptor:
                    _, num_id, level = descriptor
                    if not in_list or (level == 0 and num_id not in active_list_ids):
                        counters.clear()
                        active_list_ids.clear()
                    active_list_ids.add(num_id)
                    marker = list_marker(descriptor, counters)
                    marker_text, level = marker
                    lines.append(f"{'  ' * level}{marker_text} {text}")
                    stats["list_items"] += 1
                    in_list = True
                    prior_list_text = text
                elif is_plain_list_continuation(
                    block, text, style, heading, images, prior_list_text
                ):
                    # The list item has already emitted its Markdown line and
                    # trailing blank.  Join this DOCX wrap to that line without
                    # ending the active numbering sequence.
                    lines[-2] = f"{lines[-2]} {text}"
                    prior_list_text = f"{prior_list_text} {text}"
                    wrote_new_line = False
                else:
                    lines.append(text)
                    counters.clear()
                    active_list_ids.clear()
                    in_list = False
                    prior_list_text = None
            if wrote_new_line:
                lines.append("")
        else:
            counters.clear()
            active_list_ids.clear()
            in_list = False
            prior_list_text = None
        for rel_id, alt in images:
            part = block.part.related_parts.get(rel_id)
            if part is None:
                continue
            rendered, unique = write_image(part, alt, output, media_dir, known_images)
            lines.append(rendered)
            lines.append("")
            stats["images"] += 1
            stats["unique_images"] += int(unique)
    output.parent.mkdir(parents=True, exist_ok=True)
    normalized = "\n".join(lines).rstrip() + "\n"
    output.write_text(normalized, encoding="utf-8", newline="\n")
    return {
        "source_sha256": sha256(source),
        "output_sha256": sha256(output),
        "paragraphs": stats["paragraphs"],
        "tables": stats["tables"],
        "images": stats["images"],
        "unique_images": stats["unique_images"],
        "captions": stats["captions"],
        "list_items": stats["list_items"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--media-dir", required=True, type=Path)
    args = parser.parse_args()
    print(convert(args.source, args.output, args.media_dir))


if __name__ == "__main__":
    main()
