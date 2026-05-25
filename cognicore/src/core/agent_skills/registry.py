#!/usr/bin/env python3
import json
import os
import logging
from typing import Dict, Any, List, Optional, Callable, Awaitable
from datetime import datetime

from .schema import SkillManifest, SkillExecutionRequest, SkillExecutionResult, SkillCategory, SkillVisibility

logger = logging.getLogger("AgentSkillsRegistry")


class SkillRegistry:
    def __init__(self, storage_path: str = "data/skill_registry.json"):
        self.storage_path = storage_path
        self._skills: Dict[str, SkillManifest] = {}
        self._handlers: Dict[str, Callable[..., Awaitable[Any]]] = {}
        self._load()

    # ----- CRUD -----

    def register(self, manifest: SkillManifest, handler: Optional[Callable] = None) -> bool:
        if manifest.id in self._skills:
            logger.warning(f"Skill {manifest.id} exists, overwriting")
        manifest.updated_at = datetime.now().isoformat()
        self._skills[manifest.id] = manifest
        if handler:
            self._handlers[manifest.id] = handler
        self._save()
        logger.info(f"Registering skill: {manifest.id} v{manifest.version}")
        return True

    def unregister(self, skill_id: str) -> bool:
        if skill_id in self._skills:
            del self._skills[skill_id]
            self._handlers.pop(skill_id, None)
            self._save()
            logger.info(f"Unregistering skill: {skill_id}")
            return True
        return False

    def update(self, manifest: SkillManifest) -> bool:
        if manifest.id not in self._skills:
            logger.warning(f"Skill {manifest.id} does not exist, cannot update")
            return False
        manifest.updated_at = datetime.now().isoformat()
        self._skills[manifest.id] = manifest
        self._save()
        return True

    def get(self, skill_id: str) -> Optional[SkillManifest]:
        return self._skills.get(skill_id)

    def list(self, category: Optional[str] = None,
             visibility: Optional[str] = None,
             tags: Optional[List[str]] = None) -> List[SkillManifest]:
        results = list(self._skills.values())
        if category:
            results = [s for s in results if s.category.value == category]
        if visibility:
            results = [s for s in results if s.visibility.value == visibility]
        if tags:
            results = [s for s in results if any(t in s.tags for t in tags)]
        return results

    def search(self, query: str) -> List[SkillManifest]:
        q = query.lower()
        return [
            s for s in self._skills.values()
            if q in s.name.lower() or q in s.description.lower() or q in s.id.lower()
        ]

    # ----- Execution -----

    async def execute(self, request: SkillExecutionRequest) -> SkillExecutionResult:
        import time
        t0 = time.time()
        manifest = self._skills.get(request.skill_id)
        if not manifest:
            return SkillExecutionResult(
                skill_id=request.skill_id, status="error",
                error=f"Skill {request.skill_id} 未Register",
            )
        handler = self._handlers.get(request.skill_id)
        if not handler:
            return SkillExecutionResult(
                skill_id=request.skill_id, status="error",
                error=f"Skill {request.skill_id} 无执行Processor",
            )
        try:
            result = await handler(request.params, request.context or {})
            elapsed = (time.time() - t0) * 1000
            return SkillExecutionResult(
                skill_id=request.skill_id, status="ok",
                output=result, duration_ms=elapsed,
            )
        except Exception as e:
            elapsed = (time.time() - t0) * 1000
            logger.error(f"Skill execution failed {request.skill_id}: {e}")
            return SkillExecutionResult(
                skill_id=request.skill_id, status="error",
                error=str(e), duration_ms=elapsed,
            )

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        return [s.to_openai_tool() for s in self._skills.values()]

    # ----- Persistence -----

    def _save(self):
        os.makedirs(os.path.dirname(self.storage_path) or ".", exist_ok=True)
        data = {sid: m.to_dict() for sid, m in self._skills.items()}
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load(self):
        if not os.path.exists(self.storage_path):
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for sid, d in data.items():
                self._skills[sid] = SkillManifest.from_dict(d)
            logger.info(f"From {self.storage_path} Loaded {len(self._skills)}  skills")
        except Exception as e:
            logger.warning(f"Failed to load skill registry: {e}")


# Global singleton
_registry: Optional[SkillRegistry] = None


def get_registry() -> SkillRegistry:
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
    return _registry
