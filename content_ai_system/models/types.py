"""Core domain objects for retrieval and generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class StylePattern:
    hooks: list[str] = field(default_factory=list)
    sentence_patterns: list[str] = field(default_factory=list)
    tone_rules: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    persuasion_techniques: list[str] = field(default_factory=list)


@dataclass(slots=True)
class StyleBlueprint:
    voice: list[str]
    sentence_rules: list[str]
    hooks: list[str]
    framework: list[str]
    persuasion: list[str]
    source_creators: list[str] = field(default_factory=list)

    def to_prompt_block(self) -> str:
        sections = [
            ("Voice", self.voice),
            ("Sentence rules", self.sentence_rules),
            ("Hooks", self.hooks),
            ("Framework", self.framework),
            ("Persuasion", self.persuasion),
        ]
        lines = []
        for title, items in sections:
            lines.append(f"{title}:")
            if items:
                lines.extend(f"- {item}" for item in items)
            else:
                lines.append("- none")
        if self.source_creators:
            lines.append("Source creators:")
            lines.extend(f"- {creator}" for creator in self.source_creators)
        return "\n".join(lines)


@dataclass(slots=True)
class GenerationRequest:
    topic: str
    platform: str
    audience: str = "general"
    goal: str = "engagement"
    content_type: str = "post"
    extra_context: str | None = None


@dataclass(slots=True)
class RewriteRequest:
    content: str
    platform: str
    goal: str = "clarity"
    preserve_core_idea: bool = True


@dataclass(slots=True)
class ExpansionRequest:
    content: str
    target_format: str
    audience: str = "general"


@dataclass(slots=True)
class RetrievalResult:
    raw_graph_rows: list[dict[str, Any]]
    style_pattern: StylePattern
    related_examples: list[str] = field(default_factory=list)
