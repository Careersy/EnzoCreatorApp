"""HTTP API routes for Creator Intelligence app."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from creator_intelligence_app.app.schemas.api import (
    BriefQuestionsRequest,
    BlueprintRequest,
    CalendarPlanRequest,
    ChatHistoryRequest,
    CompareStyleRequest,
    ExpandRequest,
    ExportMarkdownRequest,
    GenerateRequest,
    GraphQueryRequest,
    IngestTextRequest,
    IntegrationPayload,
    LibraryRequest,
    Neo4jImportRequest,
    PerformanceIngestRequest,
    PerformanceSummaryRequest,
    PlannerStateRequest,
    PhraseRuleRequest,
    PlanRequest,
    RepurposeRequest,
    ReindexRequest,
    RewriteRequest,
    SettingsRequest,
    StyleMixRequest,
    StyleProfileRequest,
    TopicMapRequest,
)
from creator_intelligence_app.app.services.bootstrap import container
from creator_intelligence_app.app.config.settings import SETTINGS


router = APIRouter(prefix="/api")


def _form_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes", "on"}


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/ingest/file")
async def ingest_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    author_type: str = Form("mine"),
    status: str = Form("draft"),
    source_type: str = Form("uploaded_file"),
    platform: str = Form("LinkedIn"),
    content_type: str = Form("post"),
    tags: str = Form(""),
    run_in_background: str = Form("false"),
    allow_duplicate: str = Form("false"),
) -> dict:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    max_bytes = max(1, SETTINGS.max_upload_mb) * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max allowed size is {SETTINGS.max_upload_mb} MB.",
        )

    saved = container.content_service.save_uploaded_file(file.filename, data)
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    background_flag = _form_bool(run_in_background)
    allow_duplicate_flag = _form_bool(allow_duplicate)

    if background_flag:
        payload = {
            "filename": file.filename,
            "author_type": author_type,
            "status": status,
            "source_type": source_type,
            "platform": platform,
            "content_type": content_type,
            "tags": tag_list,
            "allow_duplicate": allow_duplicate_flag,
        }
        job_id = container.content_service.create_job(job_type="ingest_file", payload=payload)
        background_tasks.add_task(
            container.content_service.run_file_ingestion_job,
            job_id,
            saved,
            author_type,
            status,
            source_type,
            platform,
            content_type,
            tag_list,
            allow_duplicate_flag,
        )
        return {"queued": True, "job_id": job_id, "file": file.filename}

    return container.content_service.ingest_file(
        file_path=saved,
        author_type=author_type,
        status=status,
        source_type=source_type,
        platform=platform,
        content_type=content_type,
        tags=tag_list,
        allow_duplicate=allow_duplicate_flag,
    )


@router.post("/ingest/text")
def ingest_text(req: IngestTextRequest) -> dict:
    return container.content_service.ingest_text(
        title=req.title,
        text=req.text,
        author_type=req.author_type,
        status=req.status,
        source_type=req.source_type,
        platform=req.platform,
        content_type=req.content_type,
        tags=req.tags,
        allow_duplicate=req.allow_duplicate,
    )


@router.get("/sources")
def list_sources() -> list[dict]:
    return container.content_service.list_uploaded_sources()


@router.get("/drafts")
def list_drafts(limit: int = 100) -> dict:
    return {"drafts": container.content_service.list_saved_drafts(limit=limit)}


@router.get("/jobs")
def list_jobs() -> list[dict]:
    return container.content_service.list_jobs(limit=100)


@router.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    job = container.content_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/style/extract")
def extract_style(req: StyleProfileRequest) -> dict:
    return container.content_service.extract_style_profile(profile_name=req.profile_name)


@router.post("/query/graph")
def query_graph(req: GraphQueryRequest) -> dict:
    return container.content_service.query_knowledge_graph(query=req.query)


@router.post("/query/library")
def query_library(req: LibraryRequest) -> dict:
    return container.content_service.knowledge_explorer_library(
        library_type=req.library_type,
        creator=req.creator,
        topic=req.topic,
        limit=req.limit,
    )


@router.post("/blueprint/build")
def build_blueprint(req: BlueprintRequest) -> dict:
    return container.content_service.build_style_blueprint(
        query=req.query,
        platform=req.platform,
        goal=req.goal,
        audience=req.audience,
        content_type=req.content_type,
    )


@router.post("/rewrite")
def rewrite(req: RewriteRequest) -> dict:
    return container.content_service.rewrite_content(
        content=req.content,
        platform=req.platform,
        goal=req.goal,
        audience=req.audience,
        intensity=req.sound_more_like_me,
        creator_inspiration=req.creator_inspiration,
        model=req.model,
    )


@router.post("/generate")
def generate(req: GenerateRequest) -> dict:
    return container.content_service.generate_content(
        topic=req.topic,
        platform=req.platform,
        audience=req.audience,
        goal=req.goal,
        cta_goal=req.cta_goal,
        reference_content=req.reference_content,
        model=req.model,
    )


@router.post("/brief/questions")
def brief_questions(req: BriefQuestionsRequest) -> dict:
    return container.content_service.build_brief_questions(
        mode=req.mode,
        user_request=req.user_request,
        platform=req.platform,
        model=req.model,
        max_questions=req.max_questions,
    )


@router.post("/expand")
def expand(req: ExpandRequest) -> dict:
    return container.content_service.expand_content(
        content=req.content,
        target_format=req.target_format,
        audience=req.audience,
        goal=req.goal,
        model=req.model,
    )


@router.post("/plan")
def plan(req: PlanRequest) -> dict:
    return container.content_service.plan_content_series(
        topic=req.topic,
        platform=req.platform,
        audience=req.audience,
        goal=req.goal,
        weeks=req.weeks,
        posts_per_week=req.posts_per_week,
    )


@router.post("/plan/topic-map")
def topic_map(req: TopicMapRequest) -> dict:
    return container.content_service.generate_topic_map(
        topic=req.topic,
        platform=req.platform,
        audience=req.audience,
        goal=req.goal,
    )


@router.post("/plan/calendar")
def plan_calendar(req: CalendarPlanRequest) -> dict:
    return container.content_service.plan_content_calendar(
        topic=req.topic,
        platform=req.platform,
        audience=req.audience,
        goal=req.goal,
        weeks=req.weeks,
        posts_per_week=req.posts_per_week,
    )


@router.post("/repurpose")
def repurpose(req: RepurposeRequest) -> dict:
    return container.content_service.repurpose_content(
        content=req.content,
        topic=req.topic,
        source_platform=req.source_platform,
        target_platforms=req.target_platforms,
        audience=req.audience,
        goal=req.goal,
    )


@router.post("/compare-style")
def compare_style(req: CompareStyleRequest) -> dict:
    return container.content_service.compare_draft_to_my_style(draft_text=req.draft_text)


@router.post("/export/markdown")
def export_markdown(req: ExportMarkdownRequest) -> dict:
    return container.content_service.export_to_markdown(title=req.title, body=req.body)


@router.post("/phrase-rules")
def add_phrase_rule(req: PhraseRuleRequest) -> dict:
    return container.content_service.add_phrase_rule(
        rule_type=req.rule_type,
        phrase=req.phrase,
        weight=req.weight,
    )


@router.post("/integrations/notion/sync")
def sync_notion(req: IntegrationPayload) -> dict:
    return container.content_service.sync_to_notion(req.payload)


@router.post("/integrations/github/export")
def export_github(req: IntegrationPayload) -> dict:
    return container.content_service.export_to_github(req.payload)


@router.post("/settings")
def save_settings(req: SettingsRequest) -> dict:
    container.content_service.save_settings(req.key, req.value)
    return {"saved": True, "key": req.key}


@router.get("/settings/{key}")
def get_settings(key: str) -> dict:
    value = container.content_service.get_settings(key)
    return {"key": key, "value": value}


@router.post("/chat/history")
def save_chat_history(req: ChatHistoryRequest) -> dict:
    return container.content_service.save_chat_history(req.messages)


@router.get("/chat/history")
def get_chat_history() -> dict:
    return container.content_service.get_chat_history()


@router.post("/planner/state")
def save_planner_state(req: PlannerStateRequest) -> dict:
    return container.content_service.save_planner_state(req.posts)


@router.get("/planner/state")
def get_planner_state() -> dict:
    return container.content_service.get_planner_state()


@router.get("/status")
def status() -> dict:
    return container.content_service.status_snapshot()


@router.get("/model/status")
def model_status() -> dict:
    return container.content_service.model_status()


@router.post("/neo4j/import")
def neo4j_import(req: Neo4jImportRequest) -> dict:
    return container.content_service.import_existing_knowledge_graph_to_neo4j(
        clear_existing=req.clear_existing,
        dry_run=req.dry_run,
        force=req.force,
        batch_size=req.batch_size,
    )


@router.post("/reindex")
def reindex(req: ReindexRequest) -> dict:
    return container.content_service.reindex_sources(source_id=req.source_id)


@router.get("/creators")
def list_creators() -> dict:
    return {"creators": container.content_service.list_creators(limit=100)}


@router.post("/style/mix")
def style_mix(req: StyleMixRequest) -> dict:
    return container.content_service.mix_creator_patterns_with_my_voice(
        topic=req.topic,
        platform=req.platform,
        audience=req.audience,
        goal=req.goal,
        mode=req.mode,
        content=req.content,
        creator_weights=[{"creator": item.creator, "weight": item.weight} for item in req.creator_weights],
        model=req.model,
    )


@router.post("/performance/ingest")
def performance_ingest(req: PerformanceIngestRequest) -> dict:
    return container.content_service.ingest_performance_metrics(
        platform=req.platform,
        hook_text=req.hook_text,
        views=req.views,
        likes=req.likes,
        comments=req.comments,
        shares=req.shares,
        topic=req.topic,
        creator_name=req.creator_name,
        source_id=req.source_id,
        metadata=req.metadata,
    )


@router.post("/performance/summary")
def performance_summary(req: PerformanceSummaryRequest) -> dict:
    return container.content_service.performance_summary(
        platform=req.platform,
        limit=req.limit,
    )
