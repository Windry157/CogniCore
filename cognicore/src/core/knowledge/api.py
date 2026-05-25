#!/usr/bin/env python3
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field
from src.core.memory.embedding_utils import OllamaEmbeddingFunction
from src.core.memory.chromadb_memory import ChromaDBMemory
from src.core.knowledge.kb_indexer import KnowledgeBaseIndexer
from src.core.knowledge.rag_engine import RAGEngine

logger = logging.getLogger("KnowledgeAPI")
router = APIRouter(prefix="/knowledge", tags=["knowledge"])

_rag: Optional[RAGEngine] = None
_indexer: Optional[KnowledgeBaseIndexer] = None


def _get_rag() -> RAGEngine:
    global _rag
    if _rag is None:
        chroma = ChromaDBMemory(collection_name="knowledge_base")
        _rag = RAGEngine(chroma_memory=chroma)
    return _rag


def _get_indexer() -> KnowledgeBaseIndexer:
    global _indexer
    if _indexer is None:
        chroma = ChromaDBMemory(collection_name="knowledge_base")
        _indexer = KnowledgeBaseIndexer(
            chroma_memory=chroma,
            vault_path="/media/wl/D盘/Epanwj/obsidian/全能型knowledge base",
        )
    return _indexer


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=10000)
    model: Optional[str] = None
    top_k: Optional[int] = Field(default=5, ge=1, le=50)


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=5000)
    k: Optional[int] = Field(default=5, ge=1, le=50)


@router.post("/search")
async def search_knowledge(req: SearchRequest):
    rag = _get_rag()
    results = rag.search(req.query, req.k)
    return {"query": req.query, "results": results, "total": len(results)}


@router.get("/search")
async def search_knowledge_get(q: str = Query(..., min_length=1), k: int = Query(5, ge=1, le=50)):
    rag = _get_rag()
    results = rag.search(q, k)
    return {"query": q, "results": results, "total": len(results)}


@router.post("/ask")
async def ask_knowledge(req: AskRequest):
    rag = _get_rag()
    rag.top_k = req.top_k or 5
    result = rag.ask(req.question, model=req.model)
    return {
        "answer": result.answer,
        "sources": result.sources,
        "total_sources": len(result.sources),
    }


@router.post("/reindex")
async def reindex_knowledge():
    indexer = _get_indexer()
    result = indexer.run_full_index()
    return result


@router.get("/stats")
async def knowledge_stats():
    rag = _get_rag()
    try:
        collection = rag.chroma.client.get_collection(rag.collection_name)
        count = collection.count()
        return {"collection": rag.collection_name, "chunk_count": count, "status": "ok"}
    except Exception as e:
        return {"collection": rag.collection_name, "chunk_count": 0, "status": f"not_initialized: {e}"}
