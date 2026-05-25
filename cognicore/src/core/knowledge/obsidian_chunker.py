#!/usr/bin/env python3
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from .obsidian_loader import ObsidianDoc


@dataclass
class Chunk:
    content: str
    doc_path: str
    section_title: str
    heading_level: int
    chunk_index: int
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ObsidianChunker:
    def __init__(self, 
                 max_chars: int = 1500,
                 min_chars: int = 100,
                 logger: Optional[logging.Logger] = None):
        self.max_chars = max_chars
        self.min_chars = min_chars
        self.logger = logger or logging.getLogger("ObsidianChunker")

    def chunk_doc(self, doc: ObsidianDoc) -> List[Chunk]:
        sections = self._split_by_heading(doc.content)
        chunks = []
        for i, (level, title, body) in enumerate(sections):
            if not body.strip():
                continue
            sub_chunks = self._split_long_section(body, doc, title, level, i)
            chunks.extend(sub_chunks)
        return chunks

    def _split_by_heading(self, content: str) -> List[Tuple[int, str, str]]:
        pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
        lines = content.split("\n")
        sections: List[Tuple[int, str, List[str]]] = []
        current_level = 1
        current_title = "root"
        current_body: List[str] = []

        for line in lines:
            m = pattern.match(line)
            if m:
                if current_body:
                    sections.append((current_level, current_title, current_body))
                current_level = len(m.group(1))
                current_title = m.group(2).strip()
                current_body = []
                continue
            if line.strip().startswith("---") and len(line.strip()) == 3:
                continue
            current_body.append(line)

        if current_body:
            sections.append((current_level, current_title, current_body))
        return [(level, title, "\n".join(body)) for level, title, body in sections]

    def _split_long_section(self, body: str, doc: ObsidianDoc,
                            title: str, level: int, idx: int) -> List[Chunk]:
        paragraphs = re.split(r"\n\s*\n", body)
        chunks: List[Chunk] = []
        buffer: List[str] = []
        char_count = 0
        chunk_idx = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if char_count + len(para) > self.max_chars and buffer:
                merged = "\n\n".join(buffer)
                if len(merged) >= self.min_chars:
                    chunks.append(self._make_chunk(merged, doc, title, level, idx, chunk_idx))
                    chunk_idx += 1
                buffer = [para]
                char_count = len(para)
            else:
                buffer.append(para)
                char_count += len(para)

        if buffer:
            merged = "\n\n".join(buffer)
            if len(merged) >= self.min_chars or not chunks:
                chunks.append(self._make_chunk(merged, doc, title, level, idx, chunk_idx))
        return chunks

    def _make_chunk(self, content: str, doc: ObsidianDoc,
                    title: str, level: int, sec_idx: int, chunk_idx: int) -> Chunk:
        prefix = "#" * level
        full_content = f"{prefix} {title}\n\n{content}"
        created = str(doc.created) if doc.created else ""
        updated = str(doc.updated) if doc.updated else ""
        return Chunk(
            content=full_content,
            doc_path=doc.relative_path,
            section_title=title,
            heading_level=level,
            chunk_index=(sec_idx * 1000 + chunk_idx),
            tags=doc.tags,
            metadata={
                "source": doc.relative_path,
                "section": title,
                "tags": ",".join(doc.tags),
                "created": created,
                "updated": updated,
                "file_size": str(doc.file_size),
            },
        )
