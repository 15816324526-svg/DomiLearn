"""Create traceable practice units without rewriting confirmed textbook text."""

from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Passage, PassageSentence, PlannedSentence


_SPEAKER = re.compile(r"^([^:：]{1,55})\s*[:：]\s*(.+)$")
_ABBREVIATIONS = ("Sr.", "Sra.", "Srta.", "Dr.", "Dra.", "Ud.", "Uds.", "etc.")
_VERIFIED_OCR_FIXES = {
    "Buenos dias.": "Buenos días.",
    "Si, soy amiga de ellos.": "Sí, soy amiga de ellos.",
    "iEs cubano?": "¿Es cubano?",
}


@dataclass(frozen=True)
class PreparedUnit:
    speaker: str | None
    text: str
    source_line: int
    issue: str | None = None


def _split_sentences(line: str) -> list[str]:
    protected = line
    for index, abbreviation in enumerate(_ABBREVIATIONS):
        protected = re.sub(re.escape(abbreviation), f"\ue000{index}\ue001", protected, flags=re.I)
    parts = re.split(r"(?<=[.!?])\s+(?=[¿¡A-ZÁÉÍÓÚÜÑa-záéíóúüñ])", protected)
    restored: list[str] = []
    for part in parts:
        for index, abbreviation in enumerate(_ABBREVIATIONS):
            part = part.replace(f"\ue000{index}\ue001", abbreviation)
        if part.strip():
            restored.append(part.strip())
    return restored


def derive_units(content: str) -> list[PreparedUnit]:
    units: list[PreparedUnit] = []
    for line_number, raw_line in enumerate(content.splitlines(), 1):
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        speaker = None
        match = _SPEAKER.match(line)
        if match and len(match.group(1).split()) <= 5:
            speaker = match.group(1).strip()
            line = match.group(2).strip()
        for text in _split_sentences(line):
            text = _VERIFIED_OCR_FIXES.get(text, text)
            if len(text) < 2 or not re.search(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", text):
                continue
            issue = None
            if len(text) > 500:
                issue = "句子过长，需要人工核查断句"
            elif len(text) < 2:
                issue = "句子过短，需要人工核查"
            units.append(PreparedUnit(speaker, text, line_number, issue))
    return units


def prepare_passage(session: Session, passage: Passage) -> tuple[list[PassageSentence], list[str]]:
    existing = list(session.scalars(select(PassageSentence).where(
        PassageSentence.passage_id == passage.id,
    ).order_by(PassageSentence.ordinal)))
    if existing and any(item.preparation_issue for item in existing) and not session.scalar(
        select(PlannedSentence.id).where(PlannedSentence.source_sentence_id.in_([item.id for item in existing])).limit(1)
    ):
        for item in existing:
            session.delete(item)
        session.flush()
        existing = []
    if existing:
        for item in existing:
            corrected = _VERIFIED_OCR_FIXES.get(item.source_text)
            if corrected and not session.scalar(select(PlannedSentence.id).where(
                PlannedSentence.source_sentence_id == item.id,
            ).limit(1)):
                item.source_text = corrected
        return existing, [f"第{item.ordinal + 1}句：{item.preparation_issue}" for item in existing if item.preparation_issue]
    units = derive_units(passage.content)
    if not units:
        return [], ["课文未识别出可练习句子"]
    sentences = [PassageSentence(
        id=str(uuid4()), passage_id=passage.id, ordinal=index,
        speaker=unit.speaker, source_text=unit.text,
        source_page=passage.source_page_start, source_line=unit.source_line,
        preparation_issue=unit.issue,
    ) for index, unit in enumerate(units)]
    session.add_all(sentences)
    session.flush()
    return sentences, [f"第{index + 1}句：{unit.issue}" for index, unit in enumerate(units) if unit.issue]
