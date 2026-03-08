"""Pydantic request models for API endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class IngestTextRequest(BaseModel):
    title: str
    text: str
    author_type: str = Field(default="mine", pattern="^(mine|creator)$")
    status: str = Field(default="draft", pattern="^(draft|published)$")
    source_type: str = "pasted_text"
    platform: str | None = None
    content_type: str | None = None
    tags: list[str] = Field(default_factory=list)
    allow_duplicate: bool = False


class StyleProfileRequest(BaseModel):
    profile_name: str = "Default User Voice"


class GraphQueryRequest(BaseModel):
    query: str


class BlueprintRequest(BaseModel):
    query: str
    platform: str = "LinkedIn"
    goal: str = "authority"
    audience: str = "general"
    content_type: str = "post"


class RewriteRequest(BaseModel):
    content: str
    platform: str = "LinkedIn"
    goal: str = "authority"
    audience: str = "general"
    sound_more_like_me: float = 0.8
    creator_inspiration: str | None = None
    model: str | None = None


class GenerateRequest(BaseModel):
    topic: str
    platform: str = "LinkedIn"
    audience: str = "general"
    goal: str = "authority"
    cta_goal: str = "engagement"
    reference_content: str = ""
    model: str | None = None


class ExpandRequest(BaseModel):
    content: str
    target_format: str = "Newsletter"
    audience: str = "general"
    goal: str = "depth"
    model: str | None = None


class PlanRequest(BaseModel):
    topic: str
    platform: str = "LinkedIn"
    audience: str = "general"
    goal: str = "authority"
    weeks: int = 4
    posts_per_week: int = 3


class TopicMapRequest(BaseModel):
    topic: str
    platform: str = "LinkedIn"
    audience: str = "general"
    goal: str = "authority"


class CalendarPlanRequest(BaseModel):
    topic: str
    platform: str = "LinkedIn"
    audience: str = "general"
    goal: str = "authority"
    weeks: int = 4
    posts_per_week: int = 3


class RepurposeRequest(BaseModel):
    content: str
    topic: str = "Untitled topic"
    source_platform: str = "LinkedIn"
    target_platforms: list[str] = Field(default_factory=lambda: ["Newsletter", "Blog", "Substack"])
    audience: str = "general"
    goal: str = "authority"


class CreatorWeight(BaseModel):
    creator: str
    weight: float = 1.0


class StyleMixRequest(BaseModel):
    topic: str
    platform: str = "LinkedIn"
    audience: str = "general"
    goal: str = "authority"
    mode: str = Field(default="generate", pattern="^(generate|rewrite)$")
    content: str = ""
    creator_weights: list[CreatorWeight] = Field(default_factory=list)
    model: str | None = None


class PerformanceIngestRequest(BaseModel):
    platform: str = "LinkedIn"
    hook_text: str
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    topic: str | None = None
    creator_name: str | None = None
    source_id: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PerformanceSummaryRequest(BaseModel):
    platform: str | None = None
    limit: int = 10


class CompareStyleRequest(BaseModel):
    draft_text: str


class ExportMarkdownRequest(BaseModel):
    title: str
    body: str


class PhraseRuleRequest(BaseModel):
    rule_type: str = Field(pattern="^(banned|overused|preferred|signature)$")
    phrase: str
    weight: float = 1.0


class IntegrationPayload(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)


class SettingsRequest(BaseModel):
    key: str
    value: dict[str, Any]


class Neo4jImportRequest(BaseModel):
    clear_existing: bool = False
    dry_run: bool = False
    force: bool = False
    batch_size: int = 50


class ReindexRequest(BaseModel):
    source_id: int | None = None
