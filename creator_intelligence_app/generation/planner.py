"""Content planning engine for topic maps, calendar workflows, and repurposing."""

from __future__ import annotations

from datetime import date, timedelta


class PlannerEngine:
    @staticmethod
    def _extract_list(bundle: dict[str, object] | None, key: str, fallback: list[str]) -> list[str]:
        if not bundle:
            return fallback
        value = bundle.get(key, fallback)
        if not isinstance(value, list):
            return fallback
        cleaned: list[str] = []
        for item in value:
            if isinstance(item, dict):
                candidate = str(item.get("name") or item.get("id") or "").strip()
            else:
                candidate = str(item).strip()
            if candidate:
                cleaned.append(candidate)
        return cleaned or fallback

    @staticmethod
    def _first_monday(start: date | None = None) -> date:
        start_date = start or date.today()
        days_ahead = (0 - start_date.weekday()) % 7
        return start_date + timedelta(days=days_ahead)

    @staticmethod
    def _cadence_offsets(posts_per_week: int) -> list[int]:
        # Spread posts over weekdays (Mon-Fri) for consistency.
        templates = {
            1: [0],
            2: [0, 3],  # Mon, Thu
            3: [0, 2, 4],  # Mon, Wed, Fri
            4: [0, 1, 3, 4],  # Mon, Tue, Thu, Fri
            5: [0, 1, 2, 3, 4],  # Mon-Fri
        }
        bounded = max(1, min(int(posts_per_week), 5))
        return templates[bounded]

    def build_topic_map(
        self,
        topic: str,
        audience: str,
        goal: str,
        hook_patterns: list[str] | None = None,
        framework_patterns: list[str] | None = None,
    ) -> dict[str, object]:
        hooks = hook_patterns or [
            "The advice you keep hearing is wrong.",
            "Most people miss this because they start in the wrong place.",
            "If I had to restart from scratch, this is where I would start.",
        ]
        frameworks = framework_patterns or [
            "Hook -> Insight -> Lesson -> Action",
            "Problem -> Reframe -> Method -> CTA",
            "Myth -> Evidence -> Takeaway -> Next step",
        ]
        pillars = [
            {
                "pillar": f"Foundations of {topic}",
                "angles": [
                    f"Beginner mistakes {audience} make with {topic}",
                    f"First-principles model for {topic}",
                    f"What changed recently in {topic}",
                ],
            },
            {
                "pillar": f"Execution playbook for {topic}",
                "angles": [
                    f"Step-by-step workflow for {goal}",
                    f"Before/after case study breakdown",
                    f"Decision checklist for operators",
                ],
            },
            {
                "pillar": f"Advanced strategy in {topic}",
                "angles": [
                    "Contrarian positioning",
                    "Tradeoffs and second-order effects",
                    "Scaling patterns that hold up",
                ],
            },
        ]
        return {
            "pillars": pillars,
            "recommended_hooks": hooks[:5],
            "recommended_frameworks": frameworks[:5],
        }

    def build_calendar(
        self,
        topic: str,
        platform: str,
        weeks: int,
        posts_per_week: int,
        weekly_themes: list[str],
    ) -> list[dict[str, object]]:
        weeks = max(1, min(int(weeks), 12))
        offsets = self._cadence_offsets(posts_per_week)
        start_monday = self._first_monday()
        schedule: list[dict[str, object]] = []
        slot = 1

        for week in range(weeks):
            theme = weekly_themes[week % len(weekly_themes)]
            week_start = start_monday + timedelta(days=7 * week)
            for day_offset in offsets:
                publish_date = week_start + timedelta(days=day_offset)
                schedule.append(
                    {
                        "slot": slot,
                        "date": publish_date.isoformat(),
                        "weekday": publish_date.strftime("%A"),
                        "platform": platform,
                        "theme": theme,
                        "title_seed": f"{topic}: {theme} ({slot})",
                        "format": "short_form_post" if platform.lower() == "linkedin" else "platform_post",
                    }
                )
                slot += 1
        return schedule

    def build_repurposing_pipeline(
        self,
        topic: str,
        source_platform: str,
        target_platforms: list[str],
        hooks: list[str],
    ) -> dict[str, object]:
        targets = target_platforms or ["LinkedIn", "Newsletter", "Blog"]
        pipeline: list[dict[str, object]] = []
        for target in targets:
            if target.lower() == source_platform.lower():
                continue
            pipeline.append(
                {
                    "target_platform": target,
                    "transform_rule": f"{source_platform} -> {target}",
                    "structure": (
                        "Narrative arc + reflective sections"
                        if target.lower() in {"substack", "newsletter"}
                        else "Hook + sectioned argument + CTA"
                    ),
                    "length_guidance": (
                        "120-250 words"
                        if target.lower() == "linkedin"
                        else "700-1400 words"
                        if target.lower() in {"blog", "article", "substack"}
                        else "400-900 words"
                    ),
                    "hook_seed": hooks[len(pipeline) % max(1, len(hooks))],
                }
            )
        return {"source_platform": source_platform, "targets": pipeline}

    def plan_content_series(
        self,
        topic: str,
        platform: str = "LinkedIn",
        audience: str = "general",
        goal: str = "authority",
        weeks: int = 4,
        posts_per_week: int = 3,
        graph_patterns: dict[str, object] | None = None,
        blueprint: dict[str, object] | None = None,
    ) -> dict[str, object]:
        use_section = blueprint.get("use", {}) if isinstance(blueprint, dict) else {}
        hooks = self._extract_list(use_section if isinstance(use_section, dict) else None, "hooks", [])
        if not hooks:
            hooks = self._extract_list(graph_patterns or {}, "hooks", [])
        if not hooks:
            hooks = [
                "The advice you keep hearing is wrong.",
                "Most people miss this because they start in the wrong place.",
                "If I had to restart from scratch, this is where I would start.",
            ]

        frameworks = self._extract_list(use_section if isinstance(use_section, dict) else None, "frameworks", [])
        if not frameworks:
            frameworks = self._extract_list(graph_patterns or {}, "frameworks", [])
        if not frameworks:
            frameworks = [
                "Hook -> Insight -> Lesson -> Action",
                "Problem -> Reframe -> Method -> CTA",
                "Myth -> Evidence -> Takeaway -> Next step",
            ]

        topic_map = self.build_topic_map(
            topic=topic,
            audience=audience,
            goal=goal,
            hook_patterns=hooks,
            framework_patterns=frameworks,
        )

        weekly_themes = [
            f"Week 1: {topic} foundations",
            f"Week 2: {topic} execution",
            f"Week 3: {topic} case studies",
            f"Week 4: {topic} advanced strategies",
        ]
        calendar = self.build_calendar(
            topic=topic,
            platform=platform,
            weeks=weeks,
            posts_per_week=posts_per_week,
            weekly_themes=weekly_themes,
        )
        repurposing = self.build_repurposing_pipeline(
            topic=topic,
            source_platform=platform,
            target_platforms=["Newsletter", "Blog", "Substack"],
            hooks=hooks,
        )

        posts = [f"{topic} - draft seed #{i}" for i in range(1, (max(1, min(posts_per_week, 5)) * max(1, weeks)) + 1)]

        return {
            "topic_map": topic_map["pillars"],
            "content_angles": [angle for pillar in topic_map["pillars"] for angle in pillar.get("angles", [])][:9],
            "hooks": hooks[:5],
            "frameworks": frameworks[:5],
            "weekly_themes": weekly_themes,
            "content_calendar": calendar,
            "posts": posts,
            "repurposing_pipeline": repurposing,
        }
