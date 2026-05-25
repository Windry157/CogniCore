#!/usr/bin/env python3
import logging
import json
from typing import List, Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass, field


@dataclass
class RAGResult:
    answer: str
    sources: List[Dict[str, Any]] = field(default_factory=list)
    chunks: List[Dict[str, Any]] = field(default_factory=list)


class RAGEngine:
    def __init__(self,
                 chroma_memory,
                 ollama_base_url: str = "http://localhost:11434",
                 embed_model: str = "nomic-embed-text-v2-moe",
                 llm_model: str = "gemma4:e2b",
                 top_k: int = 5,
                 min_score: float = 0.3,
                 logger: Optional[logging.Logger] = None,
                 collection_name: str = "knowledge_base"):
        self.chroma = chroma_memory
        self.ollama_base = ollama_base_url.rstrip("/")
        self.embed_model = embed_model
        self.llm_model = llm_model
        self.top_k = top_k
        self.min_score = min_score
        self.collection_name = collection_name
        self.logger = logger or logging.getLogger("RAGEngine")
        import requests
        self.http = requests.Session()

    def search(self, query: str, k: Optional[int] = None) -> List[Dict[str, Any]]:
        k = k or self.top_k
        try:
            collection = self.chroma.client.get_collection(self.collection_name)
            results = collection.query(query_texts=[query], n_results=k)
            return self._format_results(results)
        except Exception as e:
            self.logger.error("Search failed: %s", e)
            return []

    def ask(self, query: str, k: Optional[int] = None,
            model: Optional[str] = None) -> RAGResult:
        chunks = self.search(query, k)
        if not chunks:
            return RAGResult(answer="未在knowledge base中Found相关信息.", sources=[])

        context = self._build_context(chunks)
        prompt = self._build_prompt(query, context)
        answer = self._llm_generate(prompt, model or self.llm_model)
        sources = [
            {"file": c["source"], "section": c.get("section", ""),
             "score": round(c.get("distance", 0), 4)}
            for c in chunks
        ]
        return RAGResult(answer=answer, sources=sources, chunks=chunks)

    async def ask_stream(self, query: str, model: Optional[str] = None
                         ) -> AsyncGenerator[str, None]:
        chunks = self.search(query)
        context = self._build_context(chunks) if chunks else ""
        prompt = self._build_prompt(query, context)
        try:
            import httpx
            async with httpx.AsyncClient(timeout=120) as client:
                payload = {
                    "model": model or self.llm_model,
                    "prompt": prompt,
                    "stream": True,
                }
                async with client.stream("POST",
                    f"{self.ollama_base}/api/generate", json=payload) as resp:
                    async for line in resp.aiter_lines():
                        if line.strip():
                            try:
                                data = json.loads(line)
                                token = data.get("response", "")
                                if token:
                                    yield token
                                if data.get("done"):
                                    break
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            yield f"\n\n[生成 failed: {e}]"

    def _format_results(self, results) -> List[Dict[str, Any]]:
        items = []
        if not results or not results.get("ids"):
            return items
        for i, doc_id in enumerate(results["ids"][0]):
            dist = results["distances"][0][i] if results.get("distances") else 0.0
            score = 1.0 - dist
            if score < self.min_score:
                continue
            meta = results["metadatas"][0][i] if results.get("metadatas") else {}
            items.append({
                "id": doc_id,
                "content": results["documents"][0][i] if results.get("documents") else "",
                "source": meta.get("source", ""),
                "section": meta.get("section_title", meta.get("section", "")),
                "tags": meta.get("tags", ""),
                "distance": dist,
                "score": score,
            })
        return sorted(items, key=lambda x: x["score"], reverse=True)

    def _build_context(self, chunks: List[Dict]) -> str:
        parts = []
        for i, c in enumerate(chunks[:self.top_k], 1):
            source = c.get("source", "未知Source")
            section = c.get("section", "")
            tag_info = f" [标签: {c['tags']}]" if c.get("tags") else ""
            header = f"[{i}] Source: {source}{tag_info}"
            if section:
                header += f" / {section}"
            parts.append(f"{header}\n{c.get('content', '')}")
        return "\n\n---\n\n".join(parts)

    def _build_prompt(self, query: str, context: str) -> str:
        if not context:
            return f"用户提问: {query}\n\nknowledge base中没有Found相关信息, 请基于你的知识Answer."
        return (
            f"你是一 knowledge base问答助手.请基于以下knowledge baseContentAnswer问题.\n"
            f"如果knowledge baseContent不足以Answer问题, 请如实说明.\n"
            f"在Answer末尾ListReferences.\n\n"
            f"--- knowledge baseContent ---\n{context}\n\n"
            f"--- 用户问题 ---\n{query}\n\n"
            f"请Answer:"
        )

    def _llm_generate(self, prompt: str, model: str) -> str:
        payload = {"model": model, "prompt": prompt, "stream": False, "options": {"num_predict": 2048}}
        try:
            resp = self.http.post(f"{self.ollama_base}/api/generate",
                                  json=payload, timeout=600)
            if resp.status_code == 200:
                return resp.json().get("response", "")
            return f"[Ollama Error: {resp.status_code}]"
        except Exception as e:
            return f"[请求 failed: {e}]"
