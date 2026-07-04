from __future__ import annotations

import json

from backend import settings
from backend.domain.content_types import ContentType, framework_files_for


def read_skill(relative_path: str) -> str:
    path = settings.PROMPT_SKILLS_DIR / relative_path
    if not path.exists():
        raise FileNotFoundError(f"Missing prompt skill file: {path}")
    return path.read_text(encoding="utf-8")


def read_frameworks(content_type: ContentType) -> str:
    blocks: list[str] = []
    for path in framework_files_for(content_type):
        blocks.append(f"# Framework File: {path.name}\n\n{path.read_text(encoding='utf-8')}")
    return "\n\n---\n\n".join(blocks)


def _transcript_text(transcript: list[dict[str, str]]) -> str:
    return json.dumps(transcript, ensure_ascii=False, indent=2)


# Shared control-line contract between every phase's conversational (reply)
# agent and the separate regen agent: the reply agent decides, per turn,
# whether enough new material came in to be worth saving, and signals that
# decision inline instead of the app blindly regenerating the state file
# after every single exchange.
REGEN_SIGNAL_INSTRUCTIONS = (
    "\n\nSTATE FILE SIGNAL: You share this conversation with a separate agent "
    "whose only job is to update the state file. After you finish your visible "
    "reply, decide whether this exchange added new, substantive material worth "
    "saving (a new fact, decision, example, answer, correction, or refinement). "
    "If you are only asking a clarifying question and the user has not yet "
    "supplied anything new to save, do not trigger a save. On the very last "
    "line of your response, by itself, output exactly one of:\n"
    "[[REGEN:YES]]\n"
    "[[REGEN:NO]]\n"
    "Always include this line, exactly once, as the final line. Never explain "
    "it or mention it to the user. NEVER output the updated markdown file or "
    "outline yourself in your reply. If the user asks to update the file, "
    "just acknowledge it, confirm the change, and output [[REGEN:YES]]."
)


def ideation_intro_messages() -> list[dict[str, str]]:
    system = (
        read_skill("1-Ideation/Idea-Thinking-Partner-Skill.md")
        + "\n\nSYSTEM GUARDRAIL: Stay in Phase 1. Collect context, evidence, audience, "
        "stakes, examples, counterarguments, and raw thinking only. Never produce a "
        "structure, outline, draft, hook set, or voice-styled prose."
        + "\n\nYou are opening a brand-new session. The user has not said anything "
        "yet. Invite them to share what they want to write about — the raw topic, "
        "the spark, or the argument they're chasing. Keep it short and inviting, "
        "not a checklist. Do not ask more than one or two questions."
    )
    return [{"role": "system", "content": system}]


def ideation_reply_messages(transcript: list[dict[str, str]]) -> list[dict[str, str]]:
    system = (
        read_skill("1-Ideation/Idea-Thinking-Partner-Skill.md")
        + "\n\nSYSTEM GUARDRAIL: Stay in Phase 1. Collect context, evidence, audience, "
        "stakes, examples, counterarguments, and raw thinking only. Never produce a "
        "structure, outline, draft, hook set, or voice-styled prose. Ask 1-2 probing "
        "questions at most."
        + REGEN_SIGNAL_INSTRUCTIONS
    )
    return [{"role": "system", "content": system}, *transcript]


def ideation_regen_messages(current_file: str, delta_messages: list[dict[str, str]]) -> list[dict[str, str]]:
    system = (
        "You are the dedicated state-file regeneration agent for Phase 1 "
        "Ideation in a content production system. You are a separate agent "
        "from the conversational ideation partner \u2014 you never talk to the "
        "user. You receive the CURRENT ideation.md file plus only the NEW "
        "conversation messages that happened since the file was last "
        "regenerated. Merge the new material into the existing file: "
        "everything still useful from the current file (including manual user edits) "
        "and MERGE/APPEND the new sections or updates into it. Add or "
        "update sections for genuinely new topic, audience, reader-shift, "
        "claims, evidence, stories, data, stakes, open questions, or "
        "counterarguments found in the new messages. Do not write final prose "
        "or a section outline. Output the complete updated markdown file only "
        "\u2014 no commentary, no code fences."
    )
    user = (
        "CURRENT ideation.md:\n"
        "```markdown\n"
        f"{current_file}\n"
        "```\n\n"
        "NEW MESSAGES SINCE LAST UPDATE:\n"
        f"{_transcript_text(delta_messages)}\n\n"
        "Regenerate the complete ideation.md now."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def structure_intro_messages(content_type: ContentType, ideation_file: str) -> list[dict[str, str]]:
    system = (
        read_skill("2-Positioning/Grill-Me.md")
        + "\n\nSELECTED CONTENT TYPE: "
        + content_type.value
        + "\n\nFRAMEWORKS:\n"
        + read_frameworks(content_type)
        + "\n\nREAD-ONLY IDEATION MATERIAL:\n"
        + ideation_file
        + "\n\nSYSTEM GUARDRAIL: Ask exactly one structural question at a time. "
        "Use the framework dynamically; do not run a fixed questionnaire. Do not "
        "write final prose and do not apply voice."
        + "\n\nYou are opening Phase 2 for this project. The user has not said "
        "anything yet in this phase. Briefly acknowledge what you know from the "
        "ideation material, then ask the single most important first structural "
        "question to resolve for this content type. Keep it short."
    )
    return [{"role": "system", "content": system}]


def structure_reply_messages(
    content_type: ContentType,
    ideation_file: str,
    transcript: list[dict[str, str]],
) -> list[dict[str, str]]:
    system = (
        read_skill("2-Positioning/Grill-Me.md")
        + "\n\nSELECTED CONTENT TYPE: "
        + content_type.value
        + "\n\nFRAMEWORKS:\n"
        + read_frameworks(content_type)
        + "\n\nREAD-ONLY IDEATION MATERIAL:\n"
        + ideation_file
        + "\n\nSYSTEM GUARDRAIL: Ask exactly one structural question at a time. "
        "Use the framework dynamically; do not run a fixed questionnaire. Do not "
        "write final prose and do not apply voice."
        + REGEN_SIGNAL_INSTRUCTIONS
    )
    return [{"role": "system", "content": system}, *transcript]


def structure_regen_messages(
    content_type: ContentType,
    ideation_file: str,
    current_file: str,
    delta_messages: list[dict[str, str]],
) -> list[dict[str, str]]:
    system = (
        "You are the dedicated state-file regeneration agent for Phase 2 "
        "Structure in a content production system. You are a separate agent "
        "from the conversational structure partner \u2014 you never talk to the "
        "user. You receive the CURRENT structure.md file plus only the NEW "
        "conversation messages that happened since the file was last "
        "regenerated. Merge the new material into the existing file: DO NOT "
        "DELETE existing sections unless explicitly requested. You MUST retain "
        "everything still useful (including manual user edits) and MERGE/APPEND "
        "the new updates into it. The structure must match the "
        "selected content type and framework, and must be detailed enough to "
        "drive a WHAT-only draft, but it must not be final prose and must not "
        "include voice styling."
    )
    user = (
        f"CONTENT TYPE: {content_type.value}\n\n"
        "FRAMEWORKS:\n"
        f"{read_frameworks(content_type)}\n\n"
        "IDEATION MATERIAL:\n"
        "```markdown\n"
        f"{ideation_file}\n"
        "```\n\n"
        "CURRENT structure.md:\n"
        "```markdown\n"
        f"{current_file}\n"
        "```\n\n"
        "NEW MESSAGES SINCE LAST UPDATE:\n"
        f"{_transcript_text(delta_messages)}\n\n"
        "Regenerate the complete structure.md now."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]




def drafting_reply_messages(
    content_type: ContentType,
    ideation_file: str,
    structure_file: str,
    transcript: list[dict[str, str]],
) -> list[dict[str, str]]:
    system = (
        "You are the conversational Drafting partner in a content production system. "
        "Your goal is to work with the user to co-create and refine an EXHAUSTIVELY detailed WHAT-only draft skeleton. "
        "Keep the focus entirely on the draft structure, argument beats, key points/data, examples, transitions, "
        "and phrasing anchors. Do not write final prose. Do not apply or imitate a voice. Do not optimize for style.\n\n"
        "CONTENT BRIEF REFERENCE:\n"
        + read_skill("3-Drafting/Content-Brief.md")
        + "\n\nCONTENT-TYPE FRAMEWORKS:\n"
        + read_frameworks(content_type)
        + "\n\nREAD-ONLY IDEATION MATERIAL:\n"
        + ideation_file
        + "\n\nREAD-ONLY STRUCTURE MATERIAL:\n"
        + structure_file
        + "\n\nSYSTEM GUARDRAIL: Ask exactly one question or propose one draft section refinement at a time. "
        "Do not write final prose and do not apply voice."
        + REGEN_SIGNAL_INSTRUCTIONS
    )
    return [{"role": "system", "content": system}, *transcript]


def drafting_regen_messages(
    content_type: ContentType,
    ideation_file: str,
    structure_file: str,
    current_file: str,
    delta_messages: list[dict[str, str]],
) -> list[dict[str, str]]:
    system = (
        "You are the dedicated state-file regeneration agent for Phase 3 "
        "Drafting in a content production system. You are a separate agent "
        "from the conversational drafting partner — you never talk to the "
        "user. You receive the CURRENT draft.md file plus only the NEW "
        "conversation messages that happened since the file was last "
        "regenerated. Merge the new material into the existing file: DO NOT "
        "DELETE existing sections unless explicitly requested. You MUST retain "
        "everything still useful (including manual user edits) and MERGE/APPEND "
        "the new updates into it. The draft must match the "
        "selected content type, framework, and structure, and must be detailed enough to "
        "drive final content generation, but it must be WHAT-only draft (no final prose and "
        "no voice styling)."
    )
    user = (
        f"CONTENT TYPE: {content_type.value}\n\n"
        "FRAMEWORKS:\n"
        f"{read_frameworks(content_type)}\n\n"
        "IDEATION MATERIAL:\n"
        "```markdown\n"
        f"{ideation_file}\n"
        "```\n\n"
        "STRUCTURE MATERIAL:\n"
        "```markdown\n"
        f"{structure_file}\n"
        "```\n\n"
        "CURRENT draft.md:\n"
        "```markdown\n"
        f"{current_file}\n"
        "```\n\n"
        "NEW MESSAGES SINCE LAST UPDATE:\n"
        f"{_transcript_text(delta_messages)}\n\n"
        "Regenerate the complete draft.md now."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def drafting_initial_messages(
    content_type: ContentType,
    ideation_file: str,
    structure_file: str,
) -> list[dict[str, str]]:
    system = (
        "You are Phase 3 Drafting in a content production system. Produce an "
        "EXHAUSTIVELY detailed WHAT-only draft skeleton. Include message, argument "
        "beats, key points/data, examples, transitions, approximate length allocation, "
        "and phrasing anchors only where useful for meaning. Do not write final prose. "
        "Do not apply or imitate a voice. Do not optimize for style. This draft is the "
        "content contract that Phase 4 will later render in a selected voice.\n\n"
        "CONTENT BRIEF REFERENCE:\n"
        f"{read_skill('3-Drafting/Content-Brief.md')}\n\n"
        "CONTENT-TYPE FRAMEWORKS:\n"
        f"{read_frameworks(content_type)}"
    )
    user = (
        f"CONTENT TYPE: {content_type.value}\n\n"
        "IDEATION:\n"
        "```markdown\n"
        f"{ideation_file}\n"
        "```\n\n"
        "STRUCTURE:\n"
        "```markdown\n"
        f"{structure_file}\n"
        "```\n\n"
        "Generate the complete initial draft.md now."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def final_messages(voice_prompt: str, draft_file: str, instructions: str | None) -> list[dict[str, str]]:
    user = (
        "Write the final content by following the draft's content, order, claims, "
        "evidence, and constraints exactly. The system prompt defines HOW to write; "
        "the draft below defines WHAT to write. Do not add unsupported facts. Do not "
        "restructure the piece unless the draft explicitly allows it.\n\n"
        f"OPTIONAL INSTRUCTIONS:\n{instructions or '(none)'}\n\n"
        "DRAFT:\n"
        "```markdown\n"
        f"{draft_file}\n"
        "```\n\n"
        "Generate final_content.md now."
    )
    return [{"role": "system", "content": voice_prompt}, {"role": "user", "content": user}]
