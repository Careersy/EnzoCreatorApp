"""Content OS engine to produce weekly content plans from one topic."""

from __future__ import annotations

from dataclasses import dataclass

from content_ai_system.generation.content_generator import ContentGenerator
from content_ai_system.models.types import GenerationRequest


@dataclass(slots=True)
class ContentPlan:
    topic_map: list[str]
    content_angles: list[str]
    hooks: list[str]
    weekly_themes: list[str]
    content_calendar: list[str]
    post_drafts: list[str]


class ContentOSEngine:
    def __init__(self, generator: ContentGenerator) -> None:
        self.generator = generator

    def build_plan(self, topic: str, audience: str = "general") -> ContentPlan:
        topic_map = [
            f"Foundational principles of {topic}",
            f"Common mistakes in {topic}",
            f"Case studies and examples in {topic}",
            f"Execution playbook for {topic}",
        ]
        content_angles = [
            "Contrarian take",
            "Step-by-step tutorial",
            "Framework breakdown",
            "Myth vs reality",
            "Founder-oriented implementation",
        ]
        hooks = [
            "Most people get this wrong:",
            "The overlooked truth about this topic:",
            "What changed my mind about this:",
            "If I had to restart from zero:",
        ]
        weekly_themes = [f"Week {i + 1}: {angle}" for i, angle in enumerate(content_angles[:4])]
        content_calendar = [
            f"Monday - LinkedIn post ({weekly_themes[0]})",
            f"Wednesday - LinkedIn carousel ({weekly_themes[1]})",
            f"Thursday - Newsletter ({weekly_themes[2]})",
            f"Friday - Blog article ({weekly_themes[3]})",
        ]

        post_drafts = []
        for angle in content_angles[:3]:
            req = GenerationRequest(
                topic=f"{topic} - {angle}",
                platform="LinkedIn",
                audience=audience,
                goal="authority",
                content_type="post",
            )
            post_drafts.append(self.generator.generate(req))

        return ContentPlan(
            topic_map=topic_map,
            content_angles=content_angles,
            hooks=hooks,
            weekly_themes=weekly_themes,
            content_calendar=content_calendar,
            post_drafts=post_drafts,
        )

    def generate_30_content_ideas(self, topic: str) -> list[str]:
        return [f"{topic} idea #{idx}" for idx in range(1, 31)]
