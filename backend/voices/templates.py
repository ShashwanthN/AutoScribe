from __future__ import annotations

from pathlib import Path

from backend.domain.schemas import VoiceTemplate, VoiceTemplateDetail

_TEMPLATES_DIR = Path(__file__).parent / "templates"

_REGISTRY: dict[str, tuple[str, str, str]] = {
    "product-market-fit": (
        "Product Market Fit",
        "\"Your product will fail, it's not your fault\" — a WHAT-only draft "
        "arguing that validating market fit beats fast execution.",
        "product-market-fit.md",
    ),
}


def list_templates() -> list[VoiceTemplate]:
    return [
        VoiceTemplate(id=template_id, label=label, description=description)
        for template_id, (label, description, _filename) in _REGISTRY.items()
    ]


def get_template(template_id: str) -> VoiceTemplateDetail:
    if template_id not in _REGISTRY:
        raise KeyError(template_id)
    label, description, filename = _REGISTRY[template_id]
    content = (_TEMPLATES_DIR / filename).read_text(encoding="utf-8")
    return VoiceTemplateDetail(id=template_id, label=label, description=description, content=content)
