#!/usr/bin/env python3
import os
import re
import yaml
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ObsidianDoc:
    file_path: str
    relative_path: str
    file_name: str
    content: str
    frontmatter: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    created: Optional[str] = None
    updated: Optional[str] = None
    file_size: int = 0
    mtime: float = 0.0


class ObsidianLoader:
    def __init__(self, vault_path: str, logger: Optional[logging.Logger] = None):
        self.vault_path = os.path.abspath(vault_path)
        self.logger = logger or logging.getLogger("ObsidianLoader")

    def scan(self) -> List[ObsidianDoc]:
        docs = []
        for root, dirs, files in os.walk(self.vault_path):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
            for fname in files:
                if not fname.endswith(".md"):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    doc = self._parse_file(fpath)
                    docs.append(doc)
                except Exception as e:
                    self.logger.warning("Parse failed %s: %s", fpath, e)
        self.logger.info("Scan complete: Total %d  Markdown files", len(docs))
        return docs

    def _parse_file(self, fpath: str) -> ObsidianDoc:
        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
            raw = f.read()

        stat = os.stat(fpath)
        frontmatter: Dict[str, Any] = {}
        body = raw

        if raw.startswith("---"):
            end = raw.find("---", 3)
            if end != -1:
                fm_text = raw[3:end].strip()
                try:
                    frontmatter = yaml.safe_load(fm_text) or {}
                except Exception:
                    frontmatter = {}
                body = raw[end + 3:].strip()

        tags = self._extract_tags(frontmatter, body)
        aliases = self._parse_list(frontmatter, "aliases")
        links = self._extract_links(body)

        rel = os.path.relpath(fpath, self.vault_path)
        base = os.path.basename(fpath)
        return ObsidianDoc(
            file_path=fpath,
            relative_path=rel,
            file_name=os.path.splitext(base)[0],
            content=body,
            frontmatter=frontmatter,
            tags=tags,
            aliases=aliases,
            links=links,
            created=frontmatter.get("created"),
            updated=frontmatter.get("updated"),
            file_size=stat.st_size,
            mtime=stat.st_mtime,
        )

    def _extract_tags(self, frontmatter: Dict, body: str) -> List[str]:
        tags = set()
        raw = frontmatter.get("tags", [])
        if isinstance(raw, list):
            for t in raw:
                tags.add(t.lstrip("#"))
        elif isinstance(raw, str):
            tags.add(raw.lstrip("#"))
        inline = re.findall(r"#([\w\u4e00-\u9fff/]+)", body)
        tags.update(t.replace("#", "") for t in inline)
        return sorted(tags)

    def _parse_list(self, fm: Dict, key: str) -> List[str]:
        val = fm.get(key, [])
        if isinstance(val, list):
            return [str(v) for v in val]
        if isinstance(val, str):
            return [val]
        return []

    def _extract_links(self, body: str) -> List[str]:
        return re.findall(r"\[\[([^\]]+)\]\]", body)
