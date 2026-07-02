from __future__ import annotations

from enum import Enum


class Phase(str, Enum):
    IDEATION = "ideation"
    STRUCTURE = "structure"
    DRAFTING = "drafting"
    FINAL = "final"


class PhaseFile(str, Enum):
    IDEATION = "ideation"
    STRUCTURE = "structure"
    DRAFT = "draft"
    FINAL_CONTENT = "final_content"


PHASE_ORDER: tuple[Phase, ...] = (
    Phase.IDEATION,
    Phase.STRUCTURE,
    Phase.DRAFTING,
    Phase.FINAL,
)

ADVANCE_REQUIREMENTS: dict[Phase, PhaseFile] = {
    Phase.IDEATION: PhaseFile.IDEATION,
    Phase.STRUCTURE: PhaseFile.STRUCTURE,
    Phase.DRAFTING: PhaseFile.DRAFT,
    Phase.FINAL: PhaseFile.FINAL_CONTENT,
}


def next_phase(phase: Phase) -> Phase | None:
    index = PHASE_ORDER.index(phase)
    if index >= len(PHASE_ORDER) - 1:
        return None
    return PHASE_ORDER[index + 1]


def required_file_for_advance(phase: Phase) -> PhaseFile:
    return ADVANCE_REQUIREMENTS[phase]


def is_chat_phase(phase: Phase) -> bool:
    return phase in {Phase.IDEATION, Phase.STRUCTURE}


def is_generate_phase(phase: Phase) -> bool:
    return phase in {Phase.DRAFTING, Phase.FINAL}
