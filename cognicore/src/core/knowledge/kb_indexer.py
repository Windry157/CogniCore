#!/usr/bin/env python3
import os
import time
import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from .obsidian_loader import ObsidianLoader
from .obsidian_chunker import ObsidianChunker, Chunk


class KnowledgeBaseIndexer:
    def __init__(self,
                 chroma_memory,
                 vault_path: str,
                 collection_name: str = "knowledge_base",
                 max_chars: int = 1500,
                 embed_batch_size: int = 10,
                 logger: Optional[logging.Logger] = None):
        self.chroma = chroma_memory
        self.vault_path = vault_path
        self.collection_name = collection_name
        self.embed_batch_size = embed_batch_size
        self.logger = logger or logging.getLogger("KnowledgeBaseIndexer")
        self.loader = ObsidianLoader(vault_path, logger)
        self.chunker = ObsidianChunker(max_chars=max_chars, logger=logger)

    def run_full_index(self) -> Dict[str, Any]:
        t0 = time.time()
        docs = self.loader.scan()
        all_chunks: List[Chunk] = []
        for doc in docs:
            try:
                chunks = self.chunker.chunk_doc(doc)
                all_chunks.extend(chunks)
            except Exception as e:
                self.logger.warning("Chunking failed %s: %s", doc.relative_path, e)

        self.logger.info("Total %d  files -> %d  chunks", len(docs), len(all_chunks))
        if not all_chunks:
            return {"status": "empty", "docs": 0, "chunks": 0, "elapsed": time.time() - t0}

        collection = self._get_or_create_collection()
        existing_ids = set(collection.get()["ids"]) if collection.count() > 0 else set()

        docs_to_delete = []
        ids_to_delete = set()
        for chunk in all_chunks:
            chunk_id = self._chunk_id(chunk)
            if chunk_id in existing_ids:
                existing_ids.discard(chunk_id)
            else:
                docs_to_delete.append(chunk)

        if existing_ids:
            collection.delete(ids=list(existing_ids))
            self.logger.info("Cleaned %d  stale chunks", len(existing_ids))

        new_count = self._batch_add(collection, docs_to_delete)
        elapsed = time.time() - t0
        result = {
            "status": "ok",
            "docs_total": len(docs),
            "chunks_total": len(all_chunks),
            "chunks_new": new_count,
            "chunks_removed": len(existing_ids),
            "elapsed_seconds": round(elapsed, 2),
        }
        self.logger.info("Indexing complete: %s", json.dumps(result, ensure_ascii=False))
        return result

    def _get_or_create_collection(self):
        try:
            return self.chroma.client.get_collection(self.collection_name)
        except Exception:
            return self.chroma.client.create_collection(
                name=self.collection_name,
                embedding_function=self.chroma.embedding_fn,
                metadata={"hnsw:space": "cosine"},
            )

    def _batch_add(self, collection, chunks: List[Chunk]):
        if not chunks:
            return 0
        count = 0
        for i in range(0, len(chunks), self.embed_batch_size):
            batch = chunks[i:i + self.embed_batch_size]
            ids = [self._chunk_id(c) for c in batch]
            texts = [c.content for c in batch]
            metadatas = []
            for c in batch:
                m = {}
                for k, v in c.metadata.items():
                    if isinstance(v, (str, int, float, bool)):
                        m[k] = v
                    else:
                        m[k] = str(v)
                m["chunk_index"] = c.chunk_index
                m["heading_level"] = c.heading_level
                m["section_title"] = c.section_title
                metadatas.append(m)
            try:
                collection.add(ids=ids, documents=texts, metadatas=metadatas)
                count += len(batch)
            except Exception as e:
                self.logger.error("Batch add failed: %s", e)
        return count

    def _chunk_id(self, chunk: Chunk) -> str:
        return f"{chunk.doc_path}::chunk_{chunk.chunk_index}"
