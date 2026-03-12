"""Main orchestration service for the Creator Intelligence app."""

from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path
from typing import Any

from creator_intelligence_app.app.config.settings import EXPORT_DIR, UPLOAD_DIR
from creator_intelligence_app.app.db.database import Database
from creator_intelligence_app.app.services.llm_client import LLMClient
from creator_intelligence_app.generation.draft_generator import DraftGenerator
from creator_intelligence_app.generation.expansion_engine import ExpansionEngine
from creator_intelligence_app.generation.planner import PlannerEngine
from creator_intelligence_app.generation.rewrite_engine import RewriteEngine
from creator_intelligence_app.graph.graph_client import GraphClient
from creator_intelligence_app.ingestion.chunking import chunk_text, token_estimate
from creator_intelligence_app.ingestion.metadata_extractor import (
    build_metadata,
    coerce_source_flags,
    detect_content_type,
    detect_platform,
)
from creator_intelligence_app.ingestion.text_ingest import extract_text_from_file
from creator_intelligence_app.integrations.github_export import GitHubExportService
from creator_intelligence_app.integrations.notion_sync import NotionSyncService
from creator_intelligence_app.retrieval.graph_retriever import GraphRetriever
from creator_intelligence_app.retrieval.hybrid_retriever import HybridRetriever
from creator_intelligence_app.retrieval.semantic_retriever import SemanticRetriever
from creator_intelligence_app.retrieval.style_matcher import StyleMatcher
from creator_intelligence_app.style.blueprint_builder import BlueprintBuilder
from creator_intelligence_app.style.creator_pattern_profiler import CreatorPatternProfiler
from creator_intelligence_app.style.scoring import StyleScorer
from creator_intelligence_app.style.user_voice_profiler import UserVoiceProfiler


class ContentIntelligenceService:
    def __init__(
        self,
        db: Database,
        graph_client: GraphClient,
        notion_service: NotionSyncService,
        github_service: GitHubExportService,
    ) -> None:
        self.db = db
        self.graph_client = graph_client
        self.notion_service = notion_service
        self.github_service = github_service

        self.semantic = SemanticRetriever(db)
        self.style_matcher = StyleMatcher(db)
        self.graph_retriever = GraphRetriever(graph_client)
        self.hybrid_retriever = HybridRetriever(self.graph_retriever, self.semantic, self.style_matcher)

        self.voice_profiler = UserVoiceProfiler()
        self.creator_profiler = CreatorPatternProfiler()
        self.blueprint_builder = BlueprintBuilder()
        self.style_scorer = StyleScorer()

        self.llm = LLMClient()
        self.rewriter = RewriteEngine(self.llm)
        self.generator = DraftGenerator(self.llm)
        self.expander = ExpansionEngine(self.llm)
        self.planner = PlannerEngine()

    def load_creator_graph(self) -> dict[str, Any]:
        return self.graph_client.load_graph()

    def _make_embedding(self, text: str) -> list[float]:
        return self.semantic.embed(text)

    @staticmethod
    def _hash_text(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def _apply_preset_weights(base: dict[str, float], preset_name: str) -> dict[str, float]:
        preset = (preset_name or "balanced").lower()
        profiles = {
            "balanced": {"user_voice": 0.65, "creator_patterns": 0.25, "platform_rules": 0.10},
            "more_me": {"user_voice": 0.78, "creator_patterns": 0.15, "platform_rules": 0.07},
            "more_structured": {"user_voice": 0.55, "creator_patterns": 0.30, "platform_rules": 0.15},
            "creator_inspired": {"user_voice": 0.48, "creator_patterns": 0.40, "platform_rules": 0.12},
            "concise": {"user_voice": 0.62, "creator_patterns": 0.23, "platform_rules": 0.15},
            "authoritative": {"user_voice": 0.60, "creator_patterns": 0.30, "platform_rules": 0.10},
            "conversational": {"user_voice": 0.72, "creator_patterns": 0.20, "platform_rules": 0.08},
        }
        merged = dict(profiles.get("balanced", {}))
        merged.update(base or {})
        preset_vals = profiles.get(preset)
        if preset_vals:
            merged = preset_vals

        total = sum(float(v) for v in merged.values()) or 1.0
        return {
            "user_voice": round(float(merged.get("user_voice", 0.65)) / total, 3),
            "creator_patterns": round(float(merged.get("creator_patterns", 0.25)) / total, 3),
            "platform_rules": round(float(merged.get("platform_rules", 0.10)) / total, 3),
        }

    @staticmethod
    def _extract_json_dict(text: str) -> dict[str, Any]:
        raw = str(text or "").strip()
        if not raw:
            return {}

        if raw.startswith("```"):
            raw = raw.replace("```json", "").replace("```", "").strip()

        try:
            loaded = json.loads(raw)
            return loaded if isinstance(loaded, dict) else {}
        except Exception:
            pass

        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            snippet = raw[start : end + 1]
            try:
                loaded = json.loads(snippet)
                return loaded if isinstance(loaded, dict) else {}
            except Exception:
                return {}
        return {}

    @staticmethod
    def _fallback_brief_questions(mode: str) -> list[dict[str, str]]:
        m = str(mode or "generate").strip().lower()
        if m == "rewrite":
            return [
                {"key": "audience", "question": "Who is this rewrite for?"},
                {"key": "goal", "question": "What outcome should this rewrite optimize for?"},
                {"key": "must_keep", "question": "Which lines or ideas must stay unchanged?"},
                {"key": "tone", "question": "What tone should I keep (for example: direct, calm, punchy)?"},
            ]
        if m == "expand":
            return [
                {"key": "audience", "question": "Who should this long-form version speak to?"},
                {"key": "goal", "question": "What should readers do or believe after reading?"},
                {"key": "depth", "question": "How deep should this go (quick read, practical guide, deep dive)?"},
                {"key": "examples", "question": "Any examples or case details you want included?"},
            ]
        return [
            {"key": "audience", "question": "Who is the exact audience for this draft?"},
            {"key": "goal", "question": "What is the primary goal of this piece?"},
            {"key": "proof", "question": "What personal story, proof, or example should I include?"},
            {"key": "constraints", "question": "Any constraints to follow (tone, length, phrases to avoid, CTA)?"},
        ]

    def build_brief_questions(
        self,
        mode: str,
        user_request: str,
        platform: str = "LinkedIn",
        model: str | None = None,
        max_questions: int = 4,
    ) -> dict[str, Any]:
        safe_mode = str(mode or "generate").strip().lower()
        fallback_questions = self._fallback_brief_questions(safe_mode)[: max(2, min(6, int(max_questions)))]
        system_prompt = (
            "You are Enzo, a senior content strategist. Your job is to ask concise briefing questions "
            "that help produce a stronger, specific draft. Return strict JSON only."
        )
        user_prompt = (
            f"Mode: {safe_mode}\n"
            f"Platform: {platform}\n"
            f"User request: {user_request}\n\n"
            f"Return JSON only with this exact shape:\n"
            "{\n"
            '  "questions": [\n'
            '    {"key":"audience","question":"..."},\n'
            '    {"key":"goal","question":"..."}\n'
            "  ]\n"
            "}\n\n"
            f"Rules:\n"
            f"- Ask 2 to {max(2, min(6, int(max_questions)))} questions.\n"
            "- Questions must be practical, short, and specific.\n"
            "- Keys must be snake_case and stable.\n"
            "- Prefer these keys when relevant: audience, goal, proof, constraints, cta_goal, tone.\n"
            "- Do not include any text outside the JSON."
        )

        completion = self.llm.complete_with_meta(system_prompt, user_prompt, model=model)
        parsed = self._extract_json_dict(completion.text)
        raw_questions = parsed.get("questions") if isinstance(parsed, dict) else None
        questions: list[dict[str, str]] = []
        if isinstance(raw_questions, list):
            for idx, item in enumerate(raw_questions):
                if not isinstance(item, dict):
                    continue
                key = str(item.get("key") or f"question_{idx + 1}").strip().lower().replace(" ", "_")
                question = str(item.get("question") or "").strip()
                if question:
                    questions.append({"key": key, "question": question})

        used_fallback = False
        if not questions:
            questions = fallback_questions
            used_fallback = True

        return {
            "mode": safe_mode,
            "platform": platform,
            "original_request": user_request,
            "questions": questions[: max(2, min(6, int(max_questions)))],
            "model_used": completion.resolved_model,
            "llm_meta": {
                "provider": completion.provider,
                "requested_model": completion.requested_model,
                "resolved_model": completion.resolved_model,
                "fallback_used": completion.fallback_used,
                "error": completion.error,
            },
            "used_fallback_questions": used_fallback,
        }

    def create_job(self, job_type: str, payload: dict[str, Any]) -> str:
        job_id = str(uuid.uuid4())
        self.db.upsert_job(job_id=job_id, job_type=job_type, status="queued", progress=0.0, payload=payload)
        return job_id

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        return self.db.get_job(job_id)

    def list_jobs(self, limit: int = 100) -> list[dict[str, Any]]:
        return self.db.list_jobs(limit=limit)

    def ingest_file(
        self,
        file_path: Path,
        author_type: str,
        status: str,
        source_type: str,
        platform: str | None,
        content_type: str | None,
        tags: list[str] | None = None,
        allow_duplicate: bool = False,
    ) -> dict[str, Any]:
        raw_text = extract_text_from_file(file_path)
        source_hash = self._hash_text(raw_text)
        existing = self.db.get_source_by_hash(source_hash)
        if existing and not allow_duplicate:
            return {
                "source_id": existing.get("id"),
                "title": existing.get("title"),
                "duplicated": True,
                "source_hash": source_hash,
                "message": "Source with identical content already exists. Set allow_duplicate=true to ingest again.",
            }
        detected_platform = detect_platform(raw_text, fallback=platform)
        detected_type = detect_content_type(raw_text, fallback=content_type)

        flags = coerce_source_flags(author_type=author_type, status=status)
        metadata = build_metadata(
            title=file_path.stem,
            source_type=source_type,
            author_type=author_type,
            platform=detected_platform,
            content_type=detected_type,
            tags=tags,
        )

        source_id = self.db.add_source(
            {
                "title": file_path.stem,
                "source_type": source_type,
                "source_hash": source_hash,
                "author_type": author_type,
                "platform": detected_platform,
                "content_type": detected_type,
                "source_path": str(file_path),
                "raw_text": raw_text,
                "metadata": metadata,
                **flags,
            }
        )

        chunks = chunk_text(raw_text)
        chunk_payload = []
        for idx, chunk in enumerate(chunks):
            chunk_payload.append(
                {
                    "chunk_index": idx,
                    "chunk_text": chunk,
                    "token_estimate": token_estimate(chunk),
                    "embedding": self._make_embedding(chunk),
                    "platform": detected_platform,
                    "content_type": detected_type,
                    "author_type": author_type,
                }
            )
        self.db.add_chunks(source_id, chunk_payload)
        self.semantic.sync_source_chunks(source_id, self.db.get_chunks_for_source(source_id))

        return {
            "source_id": source_id,
            "title": file_path.stem,
            "chunks": len(chunks),
            "source_hash": source_hash,
            "platform": detected_platform,
            "content_type": detected_type,
            "flags": flags,
        }

    def ingest_text(
        self,
        title: str,
        text: str,
        author_type: str,
        status: str,
        source_type: str,
        platform: str | None,
        content_type: str | None,
        tags: list[str] | None = None,
        allow_duplicate: bool = False,
    ) -> dict[str, Any]:
        source_hash = self._hash_text(text)
        existing = self.db.get_source_by_hash(source_hash)
        if existing and not allow_duplicate:
            return {
                "source_id": existing.get("id"),
                "title": existing.get("title"),
                "duplicated": True,
                "source_hash": source_hash,
                "message": "Source with identical content already exists. Set allow_duplicate=true to ingest again.",
            }

        detected_platform = detect_platform(text, fallback=platform)
        detected_type = detect_content_type(text, fallback=content_type)
        flags = coerce_source_flags(author_type=author_type, status=status)

        metadata = build_metadata(
            title=title,
            source_type=source_type,
            author_type=author_type,
            platform=detected_platform,
            content_type=detected_type,
            tags=tags,
        )

        source_id = self.db.add_source(
            {
                "title": title,
                "source_type": source_type,
                "source_hash": source_hash,
                "author_type": author_type,
                "platform": detected_platform,
                "content_type": detected_type,
                "source_path": None,
                "raw_text": text,
                "metadata": metadata,
                **flags,
            }
        )

        chunks = chunk_text(text)
        chunk_payload = []
        for idx, chunk in enumerate(chunks):
            chunk_payload.append(
                {
                    "chunk_index": idx,
                    "chunk_text": chunk,
                    "token_estimate": token_estimate(chunk),
                    "embedding": self._make_embedding(chunk),
                    "platform": detected_platform,
                    "content_type": detected_type,
                    "author_type": author_type,
                }
            )
        self.db.add_chunks(source_id, chunk_payload)
        self.semantic.sync_source_chunks(source_id, self.db.get_chunks_for_source(source_id))

        return {
            "source_id": source_id,
            "title": title,
            "chunks": len(chunks),
            "source_hash": source_hash,
            "platform": detected_platform,
            "content_type": detected_type,
            "flags": flags,
        }

    def run_file_ingestion_job(
        self,
        job_id: str,
        file_path: Path,
        author_type: str,
        status: str,
        source_type: str,
        platform: str | None,
        content_type: str | None,
        tags: list[str] | None,
        allow_duplicate: bool = False,
    ) -> None:
        payload = {
            "file_path": str(file_path),
            "author_type": author_type,
            "status": status,
            "source_type": source_type,
            "platform": platform,
            "content_type": content_type,
            "tags": tags or [],
            "allow_duplicate": allow_duplicate,
        }
        self.db.upsert_job(job_id=job_id, job_type="ingest_file", status="running", progress=0.1, payload=payload)
        try:
            result = self.ingest_file(
                file_path=file_path,
                author_type=author_type,
                status=status,
                source_type=source_type,
                platform=platform,
                content_type=content_type,
                tags=tags,
                allow_duplicate=allow_duplicate,
            )
            self.db.upsert_job(
                job_id=job_id,
                job_type="ingest_file",
                status="completed",
                progress=1.0,
                payload=payload,
                result=result,
            )
        except Exception as exc:  # pragma: no cover
            self.db.upsert_job(
                job_id=job_id,
                job_type="ingest_file",
                status="failed",
                progress=1.0,
                payload=payload,
                error=str(exc),
            )

    def reindex_sources(self, source_id: int | None = None) -> dict[str, Any]:
        sources = self.db.list_sources_with_text(limit=5000)
        if source_id is not None:
            sources = [s for s in sources if int(s.get("id", 0)) == int(source_id)]

        reindexed = 0
        skipped = 0
        for src in sources:
            sid = int(src.get("id"))
            raw = str(src.get("raw_text") or "")
            if not raw.strip():
                skipped += 1
                continue

            platform = src.get("platform")
            content_type = src.get("content_type")
            author_type = src.get("author_type")

            self.db.delete_chunks_for_source(sid)
            chunks = chunk_text(raw)
            chunk_payload = []
            for idx, chunk in enumerate(chunks):
                chunk_payload.append(
                    {
                        "chunk_index": idx,
                        "chunk_text": chunk,
                        "token_estimate": token_estimate(chunk),
                        "embedding": self._make_embedding(chunk),
                        "platform": platform,
                        "content_type": content_type,
                        "author_type": author_type,
                    }
                )
            self.db.add_chunks(sid, chunk_payload)
            self.semantic.sync_source_chunks(sid, self.db.get_chunks_for_source(sid))
            reindexed += 1

        return {
            "reindexed_sources": reindexed,
            "skipped_sources": skipped,
            "target_source_id": source_id,
        }

    def list_uploaded_sources(self) -> list[dict[str, Any]]:
        return self.db.list_sources(limit=300)

    def extract_style_profile(self, profile_name: str = "Default User Voice") -> dict[str, Any]:
        mine_texts = self.db.get_source_texts(is_mine=True, limit=500)
        metrics = self.voice_profiler.extract_profile(mine_texts)
        profile_id = self.db.save_style_profile(profile_name=profile_name, author_scope="mine", metrics=metrics)
        return {
            "profile_id": profile_id,
            "metrics": metrics,
        }

    def query_knowledge_graph(self, query: str) -> dict[str, Any]:
        return self.graph_client.query_natural_language(query)

    def knowledge_explorer_library(
        self,
        library_type: str = "template",
        creator: str | None = None,
        topic: str | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        relation_map = {
            "template": "USES_TEMPLATE",
            "framework": "USES_FRAMEWORK",
            "tone": "USES_TONE",
            "persuasion": "USES_PERSUASION",
            "cta": "USES_CTA_STYLE",
        }
        relation = relation_map.get(str(library_type or "template").lower(), "USES_TEMPLATE")
        payload = self.graph_client.pattern_library(
            relation_type=relation,
            creator=creator,
            topic=topic,
            limit=max(20, min(int(limit or 200), 1000)),
        )
        payload["library_type"] = str(library_type or "template").lower()
        return payload

    def build_style_blueprint(
        self,
        query: str,
        platform: str,
        goal: str,
        audience: str,
        content_type: str,
    ) -> dict[str, Any]:
        retrieval = self.hybrid_retriever.retrieve(
            query=query,
            platform=platform,
            goal=goal,
            audience=audience,
            content_type=content_type,
        )
        retrieval["performance_hooks"] = self.db.top_performing_hooks(platform=platform, limit=6)

        user_profile_record = self.db.latest_style_profile("mine")
        user_profile = (user_profile_record or {}).get("metrics", {})
        creator_profile = self.creator_profiler.summarize(retrieval.get("graph_patterns", {}))
        style_weights = self.db.get_setting("style_weighting") or {
            "user_voice": 0.65,
            "creator_patterns": 0.25,
            "platform_rules": 0.10,
        }
        blueprint_preset = self.db.get_setting("blueprint_preset") or {"name": "balanced"}
        style_weights = self._apply_preset_weights(
            style_weights,
            str(blueprint_preset.get("name", "balanced")),
        )

        blueprint = self.blueprint_builder.build(
            retrieval_bundle=retrieval,
            user_profile=user_profile,
            creator_profile=creator_profile,
            style_weights=style_weights,
        )
        blueprint["preset"] = blueprint_preset
        return {
            "retrieval": retrieval,
            "user_profile": user_profile,
            "creator_profile": creator_profile,
            "blueprint": blueprint,
        }

    def rewrite_content(
        self,
        content: str,
        platform: str,
        goal: str,
        audience: str,
        intensity: float = 0.8,
        creator_inspiration: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        query = f"Rewrite this {platform} content for {goal} audience {audience}. {creator_inspiration or ''}"
        package = self.build_style_blueprint(
            query=query,
            platform=platform,
            goal=goal,
            audience=audience,
            content_type="post",
        )

        result = self.rewriter.rewrite(
            content=content,
            platform=platform,
            goal=goal,
            audience=audience,
            blueprint=package["blueprint"],
            user_profile=package["user_profile"],
            banned_phrases=package["retrieval"].get("banned_phrases", []) + package["retrieval"].get("overused_phrases", []),
            preferred_phrases=package["retrieval"].get("preferred_phrases", []),
            model=model,
        )
        result["intensity"] = intensity
        result["original_input"] = content
        draft_id = self.db.save_draft(
            draft_type="rewrite",
            platform=platform,
            goal=goal,
            input_text=content,
            output_text=result["rewritten_version"],
            hooks=result["stronger_hooks"],
            ctas=[],
            scores=result["scores"],
            notes=result["notes"],
        )
        result["draft_id"] = draft_id
        return result

    def generate_content(
        self,
        topic: str,
        platform: str,
        audience: str,
        goal: str,
        cta_goal: str = "engagement",
        reference_content: str = "",
        model: str | None = None,
    ) -> dict[str, Any]:
        query = f"Generate {platform} content about {topic} for {audience} with goal {goal}"
        package = self.build_style_blueprint(
            query=query,
            platform=platform,
            goal=goal,
            audience=audience,
            content_type="post",
        )

        result = self.generator.generate(
            topic=topic,
            platform=platform,
            audience=audience,
            goal=goal,
            cta_goal=cta_goal,
            reference_content=reference_content,
            blueprint=package["blueprint"],
            user_profile=package["user_profile"],
            banned_phrases=package["retrieval"].get("banned_phrases", []) + package["retrieval"].get("overused_phrases", []),
            preferred_phrases=package["retrieval"].get("preferred_phrases", []),
            model=model,
        )

        draft_id = self.db.save_draft(
            draft_type="generate",
            platform=platform,
            goal=goal,
            input_text=topic,
            output_text=result["final_draft"],
            hooks=result["alternate_hooks"],
            ctas=result["cta_options"],
            scores=result["scores"],
            notes={"style_notes": result["style_notes"]},
        )
        result["draft_id"] = draft_id
        return result

    def expand_content(
        self,
        content: str,
        target_format: str,
        audience: str,
        goal: str,
        model: str | None = None,
    ) -> dict[str, Any]:
        query = f"Expand this to {target_format} for {audience}"
        package = self.build_style_blueprint(
            query=query,
            platform=target_format,
            goal=goal,
            audience=audience,
            content_type="long_form",
        )

        result = self.expander.expand(
            content=content,
            target_format=target_format,
            audience=audience,
            goal=goal,
            blueprint=package["blueprint"],
            user_profile=package["user_profile"],
            banned_phrases=package["retrieval"].get("banned_phrases", []) + package["retrieval"].get("overused_phrases", []),
            preferred_phrases=package["retrieval"].get("preferred_phrases", []),
            model=model,
        )

        draft_id = self.db.save_draft(
            draft_type="expand",
            platform=target_format,
            goal=goal,
            input_text=content,
            output_text=result["full_draft"],
            hooks=result["title_options"],
            ctas=[],
            scores=result["style_fidelity_notes"],
            notes={"outline": result["outline"]},
        )
        result["draft_id"] = draft_id
        return result

    def plan_content_series(
        self,
        topic: str,
        platform: str = "LinkedIn",
        audience: str = "general",
        goal: str = "authority",
        weeks: int = 4,
        posts_per_week: int = 3,
    ) -> dict[str, Any]:
        query = f"Plan a {weeks}-week {platform} series on {topic} for {audience} with goal {goal}"
        package = self.build_style_blueprint(
            query=query,
            platform=platform,
            goal=goal,
            audience=audience,
            content_type="post",
        )
        return self.planner.plan_content_series(
            topic=topic,
            platform=platform,
            audience=audience,
            goal=goal,
            weeks=weeks,
            posts_per_week=posts_per_week,
            graph_patterns=package["retrieval"].get("graph_patterns", {}),
            blueprint=package["blueprint"],
        )

    def generate_topic_map(
        self,
        topic: str,
        platform: str = "LinkedIn",
        audience: str = "general",
        goal: str = "authority",
    ) -> dict[str, Any]:
        series = self.plan_content_series(
            topic=topic,
            platform=platform,
            audience=audience,
            goal=goal,
            weeks=4,
            posts_per_week=3,
        )
        return {
            "topic": topic,
            "platform": platform,
            "audience": audience,
            "goal": goal,
            "topic_map": series.get("topic_map", []),
            "content_angles": series.get("content_angles", []),
            "hooks": series.get("hooks", []),
            "frameworks": series.get("frameworks", []),
        }

    def plan_content_calendar(
        self,
        topic: str,
        platform: str = "LinkedIn",
        audience: str = "general",
        goal: str = "authority",
        weeks: int = 4,
        posts_per_week: int = 3,
    ) -> dict[str, Any]:
        series = self.plan_content_series(
            topic=topic,
            platform=platform,
            audience=audience,
            goal=goal,
            weeks=weeks,
            posts_per_week=posts_per_week,
        )
        return {
            "topic": topic,
            "platform": platform,
            "audience": audience,
            "goal": goal,
            "weeks": weeks,
            "posts_per_week": posts_per_week,
            "weekly_themes": series.get("weekly_themes", []),
            "content_calendar": series.get("content_calendar", []),
            "posts": series.get("posts", []),
        }

    def repurpose_content(
        self,
        content: str,
        topic: str,
        source_platform: str,
        target_platforms: list[str],
        audience: str = "general",
        goal: str = "authority",
    ) -> dict[str, Any]:
        query = (
            f"Repurpose {source_platform} content for {', '.join(target_platforms)} "
            f"about {topic} for {audience} with goal {goal}"
        )
        package = self.build_style_blueprint(
            query=query,
            platform=source_platform,
            goal=goal,
            audience=audience,
            content_type="post",
        )
        hooks = package["blueprint"].get("use", {}).get("hooks", [])
        if not isinstance(hooks, list):
            hooks = []
        pipeline = self.planner.build_repurposing_pipeline(
            topic=topic,
            source_platform=source_platform,
            target_platforms=target_platforms,
            hooks=[str(h) for h in hooks if str(h).strip()] or [
                "Start with a stronger first line and one specific claim."
            ],
        )
        source_excerpt = content.strip().splitlines()
        seed = source_excerpt[0] if source_excerpt else topic
        variants = []
        for target in pipeline.get("targets", []):
            target_platform = str(target.get("target_platform", "Unknown"))
            variants.append(
                {
                    "target_platform": target_platform,
                    "title_seed": f"{topic} for {target_platform}",
                    "opening_seed": f"{seed}\n\nAdapted for {target_platform}.",
                    "outline": [
                        "Opening context",
                        "Core insight and evidence",
                        "Practical application",
                        "CTA adapted for platform",
                    ],
                }
            )

        return {
            "topic": topic,
            "source_platform": source_platform,
            "target_platforms": target_platforms,
            "pipeline": pipeline,
            "variants": variants,
            "style_notes": {
                "user_voice_first": True,
                "creator_patterns_secondary": True,
                "platform_rules_tertiary": True,
            },
        }

    def compare_draft_to_my_style(self, draft_text: str) -> dict[str, Any]:
        profile = self.db.latest_style_profile("mine")
        metrics = (profile or {}).get("metrics", {})
        score = self.style_scorer.score_style_match(draft_text, metrics)
        return {
            "style_similarity_score": score,
            "user_profile_used": metrics,
        }

    def export_to_markdown(self, title: str, body: str) -> dict[str, Any]:
        safe_name = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in title.lower())
        out_path = EXPORT_DIR / f"{safe_name or 'draft'}.md"
        out_path.write_text(f"# {title}\n\n{body}\n", encoding="utf-8")
        return {
            "exported": True,
            "path": str(out_path),
        }

    def sync_to_notion(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.notion_service.sync_metadata(payload)

    def export_to_github(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.github_service.export(payload)

    def add_phrase_rule(self, rule_type: str, phrase: str, weight: float = 1.0) -> dict[str, Any]:
        rule_id = self.db.add_phrase_rule(rule_type=rule_type, phrase=phrase, weight=weight)
        return {"rule_id": rule_id, "rule_type": rule_type, "phrase": phrase, "weight": weight}

    def save_uploaded_file(self, filename: str, content: bytes) -> Path:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        destination = UPLOAD_DIR / filename
        destination.write_bytes(content)
        return destination

    def save_settings(self, key: str, value: dict[str, Any]) -> None:
        self.db.upsert_setting(key, value)

    def get_settings(self, key: str) -> dict[str, Any] | None:
        return self.db.get_setting(key)

    def list_saved_drafts(self, limit: int = 100) -> list[dict[str, Any]]:
        return self.db.list_drafts(limit=limit)

    def save_chat_history(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        self.db.upsert_setting("chat_history", {"messages": messages})
        return {"saved": True, "message_count": len(messages)}

    def get_chat_history(self) -> dict[str, Any]:
        return self.db.get_setting("chat_history") or {"messages": []}

    def save_planner_state(self, posts: list[dict[str, Any]]) -> dict[str, Any]:
        self.db.upsert_setting("planner_state", {"posts": posts})
        return {"saved": True, "post_count": len(posts)}

    def get_planner_state(self) -> dict[str, Any]:
        return self.db.get_setting("planner_state") or {"posts": []}

    def import_existing_knowledge_graph_to_neo4j(
        self,
        clear_existing: bool = False,
        dry_run: bool = False,
        force: bool = False,
        batch_size: int = 50,
    ) -> dict[str, Any]:
        return self.graph_client.import_local_graph_to_neo4j(
            clear_existing=clear_existing,
            dry_run=dry_run,
            force=force,
            batch_size=batch_size,
        )

    def status_snapshot(self) -> dict[str, Any]:
        return {
            "sources": len(self.db.list_sources(limit=2000)),
            "style_profile": self.db.latest_style_profile("mine"),
            "phrase_rules": self.db.list_phrase_rules(),
            "graph_summary": self.graph_client.pattern_summary(),
            "neo4j_connectivity": self.graph_client.connection_status(),
            "neo4j_last_sync": self.db.get_setting("neo4j_graph_sync"),
            "llm": self.llm.status(),
        }

    def model_status(self) -> dict[str, Any]:
        return self.llm.status()

    def list_creators(self, limit: int = 50) -> list[str]:
        return self.graph_client.list_creators(limit=limit)

    def mix_creator_patterns_with_my_voice(
        self,
        topic: str,
        platform: str,
        audience: str,
        goal: str,
        creator_weights: list[dict[str, Any]],
        mode: str = "generate",
        content: str = "",
        model: str | None = None,
    ) -> dict[str, Any]:
        base_query = f"{mode} {platform} content about {topic} for {audience} with goal {goal}"
        retrieval = self.hybrid_retriever.retrieve(
            query=base_query,
            platform=platform,
            goal=goal,
            audience=audience,
            content_type="post",
        )
        mixed = self.graph_client.creator_mixer(creator_weights=creator_weights)
        retrieval["graph_patterns"] = {
            "records": mixed.get("records", []),
            "strongest_hooks": retrieval.get("graph_patterns", {}).get("strongest_hooks", []),
        }
        retrieval["performance_hooks"] = self.db.top_performing_hooks(platform=platform, limit=6)

        user_profile_record = self.db.latest_style_profile("mine")
        user_profile = (user_profile_record or {}).get("metrics", {})
        creator_profile = self.creator_profiler.summarize(retrieval.get("graph_patterns", {}))
        style_weights = self.db.get_setting("style_weighting") or {
            "user_voice": 0.65,
            "creator_patterns": 0.25,
            "platform_rules": 0.10,
        }
        blueprint = self.blueprint_builder.build(
            retrieval_bundle=retrieval,
            user_profile=user_profile,
            creator_profile=creator_profile,
            style_weights=style_weights,
        )

        if mode == "rewrite":
            generated = self.rewriter.rewrite(
                content=content or topic,
                platform=platform,
                goal=goal,
                audience=audience,
                blueprint=blueprint,
                user_profile=user_profile,
                banned_phrases=retrieval.get("banned_phrases", []) + retrieval.get("overused_phrases", []),
                preferred_phrases=retrieval.get("preferred_phrases", []),
                model=model,
            )
            final_text = generated.get("rewritten_version", "")
        else:
            generated = self.generator.generate(
                topic=topic,
                platform=platform,
                audience=audience,
                goal=goal,
                cta_goal="engagement",
                reference_content=content,
                blueprint=blueprint,
                user_profile=user_profile,
                banned_phrases=retrieval.get("banned_phrases", []) + retrieval.get("overused_phrases", []),
                preferred_phrases=retrieval.get("preferred_phrases", []),
                model=model,
            )
            final_text = generated.get("final_draft", "")

        return {
            "mode": mode,
            "topic": topic,
            "platform": platform,
            "audience": audience,
            "goal": goal,
            "creator_mix": mixed,
            "blueprint": blueprint,
            "output": generated,
            "final_text": final_text,
        }

    def ingest_performance_metrics(
        self,
        platform: str,
        hook_text: str,
        views: int,
        likes: int,
        comments: int,
        shares: int,
        topic: str | None = None,
        creator_name: str | None = None,
        source_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        views = int(max(0, views))
        likes = int(max(0, likes))
        comments = int(max(0, comments))
        shares = int(max(0, shares))
        engagement_score = round((likes * 1.0) + (comments * 2.0) + (shares * 3.0) + (views * 0.01), 3)

        event_id = self.db.add_performance_event(
            source_id=source_id,
            platform=platform,
            topic=topic,
            hook_text=hook_text,
            creator_name=creator_name,
            views=views,
            likes=likes,
            comments=comments,
            shares=shares,
            engagement_score=engagement_score,
            metadata=metadata or {},
        )
        self.db.upsert_hook_performance(
            hook_text=hook_text,
            platform=platform,
            views=views,
            likes=likes,
            comments=comments,
            shares=shares,
            engagement_score=engagement_score,
        )
        top = self.db.top_performing_hooks(platform=platform, limit=200)
        matched = next((row for row in top if str(row.get("hook_text")) == str(hook_text)), None)
        graph_update = {}
        if matched:
            graph_update = self.graph_client.learn_hook_engagement(
                hook_text=hook_text,
                platform=platform,
                avg_score=float(matched.get("avg_engagement_score", engagement_score)),
                event_count=int(matched.get("event_count", 1)),
            )

        return {
            "event_id": event_id,
            "engagement_score": engagement_score,
            "hook_stats": matched or {},
            "graph_update": graph_update,
        }

    def performance_summary(self, platform: str | None = None, limit: int = 10) -> dict[str, Any]:
        return {
            "top_hooks": self.db.top_performing_hooks(platform=platform, limit=limit),
            "recent_events": self.db.recent_performance_events(limit=limit),
        }
