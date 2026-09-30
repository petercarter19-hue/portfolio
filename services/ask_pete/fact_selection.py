"""Build public Ask Pete answers from exact, approved source passages.

Luna selects identifiers only. This module owns every visitor-facing factual
word, its source span, and the response shape. An exact span establishes
provenance; selection relevance still needs product evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
import re
from typing import Mapping

from services.ai_foundation import (
    AIRequest, AnswerClaim, AnswerKind, AnswerState, Citation, GroundedAnswer,
    HandoffProposal, HandoffReason, Purpose, SourceVersion,
)
from services.ai_foundation.errors import AnswerContractError, ProviderUnavailableError


MAX_ATOM_CHARS = 400
MAX_SELECTED_ATOMS = 8
_FIELD_LABELS = (
    "Positioning: ", "Professional summary: ", "Location: ",
    "Summary: ", "Public summary: ", "Public detail: ",
)
_LIST_SECTIONS = frozenset({
    "Public credentials", "Accomplishments", "Responsibilities", "Approved evidence",
})
_PRIVATE_REQUEST = re.compile(
    r"\b(?:passwords?|passcodes?|api[ -]?keys?|access[ -]?tokens?|secret[ -]?tokens?|"
    r"social security|ssn|(?:private|personal|home) (?:phone|email|address|credentials?|records?|journal|data)|"
    r"(?:ignore|disregard|override) (?:the |all |any |previous |prior )?"
    r"(?:approved |public )?(?:sources?|evidence|rules|instructions)|"
    r"reveal (?:your |the )?(?:system prompt|hidden instructions))\b",
    re.IGNORECASE,
)
_RANK_REQUEST = re.compile(
    r"\b(?:score|scoring|rank|ranking|hire|hiring decision|"
    r"candidate fit|fit score)\b", re.IGNORECASE,
)
_PERCENT = re.compile(r"\b\d+(?:\.\d+)?%")


@dataclass(frozen=True)
class FactAtom:
    atom_id: str
    source_version_key: str
    source_title: str
    excerpt: str
    start: int
    end: int
    section: str
    words: int

    @property
    def brief_eligible(self) -> bool:
        return (
            self.section in {"Accomplishments", "Approved evidence", "Summary", "Public summary"}
            and 12 <= self.words <= 28
            and self.excerpt.endswith((".", "!", "?"))
        )


def _selectable_prefix(line: str, section: str) -> tuple[str, str] | None:
    if line.startswith("- ") and section in _LIST_SECTIONS:
        return "- ", section
    for label in _FIELD_LABELS:
        if line.startswith(label):
            return label, label[:-2]
    return None


def build_selection_document(
    *, request: AIRequest, sources: tuple[SourceVersion, ...], subject_display_name: str,
) -> tuple[dict, dict[str, FactAtom]]:
    """Include each complete approved source line once and mark selectable spans."""

    records: list[dict] = []
    atoms: dict[str, FactAtom] = {}
    for source_index, source in enumerate(sources, start=1):
        lines = source.content.split("\n")
        offset = 0
        section = ""
        content_lines: list[dict] = []
        for line_index, line in enumerate(lines, start=1):
            if line.endswith(":") and not line.startswith("- "):
                section = line[:-1]
            entry = {"text": line}
            prefix_and_section = _selectable_prefix(line, section)
            if prefix_and_section:
                prefix, atom_section = prefix_and_section
                excerpt = line[len(prefix):]
                if (excerpt.strip() and len(excerpt) <= MAX_ATOM_CHARS
                    and not private_or_override_request(excerpt)):
                    atom_id = f"s{source_index}l{line_index}"
                    start = offset + len(prefix)
                    atoms[atom_id] = FactAtom(
                        atom_id=atom_id,
                        source_version_key=source.source_version_key,
                        source_title=source.title,
                        excerpt=excerpt,
                        start=start,
                        end=start + len(excerpt),
                        section=atom_section,
                        words=len(excerpt.split()),
                    )
                    entry.update(atom_id=atom_id, words=len(excerpt.split()))
            content_lines.append(entry)
            offset += len(line) + (1 if line_index < len(lines) else 0)
        if "\n".join(item["text"] for item in content_lines) != source.content:
            raise AnswerContractError("approved source line reconstruction failed")
        records.append({
            "source_version_key": source.source_version_key,
            "title": source.title,
            "content_lines": content_lines,
        })
    return {
        "purpose": request.purpose.value,
        "subject_display_name": subject_display_name,
        "question": request.question,
        "context_key": request.context_key,
        "approved_source_records": records,
    }, atoms


def private_or_override_request(question: str) -> bool:
    return bool(_PRIVATE_REQUEST.search(question))


def _selected_atoms(raw: Mapping, atoms: Mapping[str, FactAtom]) -> tuple[str, list[FactAtom]]:
    if not isinstance(raw, Mapping) or set(raw) != {"mode", "atom_ids"}:
        raise AnswerContractError("Luna selection fields differ")
    mode = raw["mode"]
    ids = raw["atom_ids"]
    if not isinstance(mode, str) or mode not in {"answer", "unknown", "clarify", "refuse"}:
        raise AnswerContractError("Luna selection mode differs")
    if not isinstance(ids, list) or len(ids) > MAX_SELECTED_ATOMS:
        raise AnswerContractError("Luna selection count differs")
    if any(not isinstance(atom_id, str) or atom_id not in atoms for atom_id in ids):
        raise AnswerContractError("Luna selected an unapproved fact")
    if len(ids) != len(set(ids)):
        raise AnswerContractError("Luna selected duplicate facts")
    if (mode == "answer") != bool(ids):
        raise AnswerContractError("Luna selection mode and facts differ")
    return mode, [atoms[atom_id] for atom_id in ids]


def _claim(atom: FactAtom, number: int) -> AnswerClaim:
    claim_id = f"fact-{number}"
    return AnswerClaim(
        claim_id=claim_id, text=atom.excerpt, kind=AnswerKind.EVIDENCE,
        state=AnswerState.SUPPORTED,
        citations=(Citation(
            claim_id=claim_id, source_version_key=atom.source_version_key,
            start=atom.start, end=atom.end, excerpt=atom.excerpt,
        ),),
    )


def _quoted(atom: FactAtom) -> str:
    return f"In {atom.source_title}: “{atom.excerpt}”"


def _boundary(selected: tuple[FactAtom, ...]) -> tuple[str, str, FactAtom | None]:
    metric_atom = next((atom for atom in selected if _PERCENT.search(atom.excerpt)), None)
    if metric_atom is not None and not re.search(
        r"\b(?:measured|measurement|calculated|based on)\b",
        metric_atom.excerpt, re.IGNORECASE,
    ):
        text = (
            "The cited sentence reports a percentage without explaining "
            "how that figure was measured."
        )
        return text, "The measurement method is not stated in that cited sentence.", metric_atom
    text = (
        "The cited passages do not establish how a particular role should "
        "weigh these examples."
    )
    return text, "A hiring judgment requires role context and a human reader.", None


def _recruiter_brief(
    ranked: list[FactAtom], subject_display_name: str,
) -> tuple[str, tuple[FactAtom, ...], str, str, tuple[str, str]]:
    first_name = subject_display_name.split()[0]
    eligible = [atom for atom in ranked if atom.brief_eligible]
    for proposed in combinations(eligible, 3):
        if (len({atom.source_version_key for atom in proposed}) != 3
            or len({atom.excerpt.casefold() for atom in proposed}) != 3):
            continue
        boundary, limitation, metric_atom = _boundary(proposed)
        first, second, third = proposed
        openings = (
            f"The approved public resume for {subject_display_name} gives three "
            "concrete examples of documented work. ",
            f"The public resume for {subject_display_name} records three examples. ",
        )
        endings = (
            f"A recruiter can open the linked public records and ask {first_name} "
            "for details beyond the published wording.",
            f"A recruiter can open each linked public record, check the exact "
            f"wording in context, and ask {first_name} for details beyond what "
            "the selected passages supply.",
            f"A recruiter can review the linked records and ask {first_name} for context.",
        )
        for opening in openings:
            first_paragraph = opening + _quoted(first) + " " + _quoted(second)
            base_second = _quoted(third) + " " + boundary + " "
            for ending in endings:
                summary = first_paragraph + "\n\n" + base_second + ending
                if not (100 <= len(summary.split()) <= 140 and len(summary) <= 2_000):
                    continue
                if metric_atom:
                    metric = _PERCENT.search(metric_atom.excerpt).group()
                    question_one = (
                        f"How was the reported {metric} result in "
                        f"{metric_atom.source_title} measured?"
                    )
                else:
                    question_one = (
                        f"What additional context would you add to the work "
                        f"described in {first.source_title}?"
                    )
                question_two = (
                    f"Which part of the example in {second.source_title} "
                    "best reflects your own work?"
                )
                return summary, proposed, boundary, limitation, (question_one, question_two)
    raise ProviderUnavailableError("Selected public passages cannot form a bounded brief")


def render_selection(
    *, raw: Mapping, atoms: Mapping[str, FactAtom], request: AIRequest,
    subject_display_name: str, model_name: str, prompt_version: str,
) -> GroundedAnswer:
    mode, ranked = _selected_atoms(raw, atoms)
    answer_id = f"{request.request_id}:answer"
    common = {"answer_id": answer_id, "model_name": model_name,
              "prompt_contract_version": prompt_version}
    first_name = subject_display_name.split()[0]
    if mode == "refuse" or private_or_override_request(request.question):
        return GroundedAnswer(
            state=AnswerState.REFUSED,
            summary="I can discuss only approved public professional information. I cannot answer that request.",
            **common,
        )
    if mode == "unknown":
        return GroundedAnswer(
            state=AnswerState.NOT_ESTABLISHED,
            summary=("I could not identify an approved public passage that answers "
                     "that question. The public resume remains available to review."),
            handoff=HandoffProposal(
                reason=HandoffReason.MISSING_PUBLIC_EVIDENCE,
                question="Could you clarify the requested professional detail?",
            ),
            **common,
        )
    if mode == "clarify":
        return GroundedAnswer(
            state=AnswerState.AMBIGUOUS,
            summary=("Please clarify which part of the public professional "
                     "background you mean so I can identify relevant evidence."),
            **common,
        )

    if request.purpose is Purpose.RECRUITER_BRIEF:
        summary, selected, boundary, limitation, questions = _recruiter_brief(
            ranked, subject_display_name,
        )
        claims = tuple(_claim(atom, i) for i, atom in enumerate(selected, start=1))
        claims += (AnswerClaim(
            claim_id="boundary-1", text=boundary, kind=AnswerKind.BOUNDARY,
            state=AnswerState.NOT_ESTABLISHED, limitation=limitation,
        ),)
        return GroundedAnswer(
            state=AnswerState.PARTIALLY_SUPPORTED, summary=summary, claims=claims,
            follow_up_questions=questions,
            handoff=HandoffProposal(
                reason=HandoffReason.HUMAN_JUDGMENT,
                question="Could you clarify the context behind the cited public examples?",
            ),
            **common,
        )

    selected = ranked[:4] if request.purpose is Purpose.EVIDENCE_FINDER else ranked[:3]
    if not selected:
        raise AnswerContractError("answer selection is empty")
    prefix = f"Approved public records for {subject_display_name} include: "
    if _RANK_REQUEST.search(request.question):
        prefix = (
            f"Ask {first_name} does not score or rank people; that judgment "
            "belongs to the reader. Relevant approved public records include: "
        )
    summary = prefix + " ".join(_quoted(atom) for atom in selected)
    if len(summary) > 2_000:
        raise ProviderUnavailableError("Selected public passages exceed the answer limit")
    questions: tuple[str, ...] = ()
    if request.purpose is Purpose.INTERVIEW_PREPARATION:
        source_title = selected[0].source_title
        questions = (
            f"What was your role in the work described in {source_title}?",
            f"How did you approach the work described in {source_title}?",
            "What context would help someone understand that public example more fully?",
        )
    elif request.purpose is Purpose.EVIDENCE_FINDER:
        questions = ("Which of these linked public examples would you like to explore further?",)
    return GroundedAnswer(
        state=AnswerState.SUPPORTED, summary=summary,
        claims=tuple(_claim(atom, i) for i, atom in enumerate(selected, start=1)),
        follow_up_questions=questions,
        **common,
    )
