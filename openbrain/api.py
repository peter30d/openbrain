from fastapi import FastAPI
from pydantic import BaseModel, Field

from openbrain.service import MemoryGatewayService

app = FastAPI(title="OpenBrain Gateway", version="0.2.0")
svc = MemoryGatewayService()


class CaptureRequest(BaseModel):
    text: str
    memory_type: str = "note"
    source_surface: str = "telegram_openclaw"
    source_session_id: str | None = None
    project: str | None = None
    tags: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    people: list[str] = Field(default_factory=list)


class SearchRequest(BaseModel):
    query: str
    k: int = 5


class PromoteRequest(BaseModel):
    source_namespace: str
    title: str
    excerpt: str
    uri: str | None = None
    promotion_note: str | None = None


@app.get("/health")
def health():
    return svc.health()


@app.get("/sources/status")
def source_status():
    return svc.source_status()


@app.post("/memories/enrich-preview")
def enrich_preview(req: CaptureRequest):
    return svc.preview_enrichment(
        text_value=req.text,
        memory_type=req.memory_type,
        project=req.project,
        tags=req.tags,
        topics=req.topics,
        people=req.people,
    )


@app.post("/memories/capture")
def capture_memory(req: CaptureRequest):
    return svc.capture_memory(
        text_value=req.text,
        memory_type=req.memory_type,
        source_surface=req.source_surface,
        source_session_id=req.source_session_id,
        project=req.project,
        tags=req.tags,
        topics=req.topics,
        people=req.people,
    )


@app.post("/search/local")
def search_local(req: SearchRequest):
    return {"query": req.query, "results": svc.search_local_memory(req.query, req.k)}


@app.post("/search/brian")
def search_brian(req: SearchRequest):
    return {"query": req.query, "results": svc.search_brian(req.query, req.k)}


@app.post("/search/federated")
def search_federated(req: SearchRequest):
    return svc.federated_search(req.query, req.k)


@app.post("/external/promote")
def promote(req: PromoteRequest):
    return svc.promote_external_result(
        source_namespace=req.source_namespace,
        title=req.title,
        excerpt=req.excerpt,
        uri=req.uri,
        promotion_note=req.promotion_note,
    )

