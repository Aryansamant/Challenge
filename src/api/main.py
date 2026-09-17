from __future__ import annotations

from functools import lru_cache

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.config import ROOT
from src.conversation.memory import SessionMemory
from src.engine import BioIntelEngine
from src.knowledge.store import corpus_documents, interventions
from src.models.schemas import ChatRequest, ChatResponse, LandProfile

FRONTEND = ROOT / "frontend"


@lru_cache(maxsize=1)
def get_engine() -> BioIntelEngine:
    return BioIntelEngine()


app = FastAPI(
    title="Darukaa BioIntel",
    description="Multi-metric biodiversity reasoning engine with hybrid RAG — not a generic chatbot.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    engine = get_engine()
    return {
        "ok": True,
        "chunks": len(engine.retriever.records),
        "interventions": len(interventions()),
        "corpus_docs": len(corpus_documents()),
    }


@app.get("/api/knowledge")
def knowledge_stats():
    engine = get_engine()
    return {
        "corpus": [
            {"id": rec["doc_id"], "title": rec["title"], "source": rec["source"]}
            for rec in {r["doc_id"]: r for r in engine.retriever.records}.values()
        ],
        "interventions": [
            {"id": item["id"], "title": item["title"], "horizon": item["time_horizon"]}
            for item in interventions()
        ],
        "retrieval": "Hybrid LSA vector search + BM25 with reciprocal rank fusion, then structured intervention filters.",
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    return get_engine().respond(request)


@app.post("/api/assess", response_model=ChatResponse)
def assess(profile: LandProfile) -> ChatResponse:
    return get_engine().respond(ChatRequest(profile=profile, message="Structured land profile submitted."))


@app.get("/api/session/{session_id}")
def session(session_id: str):
    memory = SessionMemory(session_id)
    return {"session_id": memory.session_id, "profile": memory.profile, "turns": memory.turns}


@app.get("/")
def index():
    return FileResponse(FRONTEND / "index.html")


if FRONTEND.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND), name="static")


def run():
    import uvicorn

    from src.config import settings

    uvicorn.run("src.api.main:app", host=settings.host, port=settings.port, reload=False)


if __name__ == "__main__":
    run()
