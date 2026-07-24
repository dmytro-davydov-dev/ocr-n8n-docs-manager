"""Loader for versioned prompt template files (ADR-013)."""

import re
from dataclasses import dataclass
from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
_FRONT_MATTER_RE = re.compile(r"^<!--\s*(.*?)\s*-->\s*", re.DOTALL)


@dataclass(frozen=True)
class PromptTemplate:
    prompt_id: str
    prompt_version: str
    system_prompt: str


def _load(path: Path) -> PromptTemplate:
    raw = path.read_text()
    match = _FRONT_MATTER_RE.match(raw)
    if not match:
        raise ValueError(f"Prompt template {path} is missing its front-matter comment")

    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()

    return PromptTemplate(
        prompt_id=fields["prompt_id"],
        prompt_version=fields["prompt_version"],
        system_prompt=raw[match.end() :].strip(),
    )


def load_contract_extraction_prompt() -> PromptTemplate:
    return _load(_PROMPTS_DIR / "contract_extraction_v1.md")
