#!/usr/bin/env python3
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

from .schema import (
    SkillManifest, SkillExecutionRequest, SkillExecutionResult,
    make_manifest,
)
from .registry import get_registry
from .bridge import get_bridge
from .packaging import PackageManager
from .wrapper import register_existing_skills

logger = logging.getLogger("AgentSkillsAPI")
router = APIRouter(prefix="/skills", tags=["agent-skills"])

_registry = None
_bridge = None
_pkg_mgr = None


def _init():
    global _registry, _bridge, _pkg_mgr
    if _registry is None:
        _registry = get_registry()
        _bridge = get_bridge()
        _pkg_mgr = PackageManager(registry=_registry)
        register_existing_skills(_registry)


class RegisterRequest(BaseModel):
    manifest: dict
    implementation: Optional[str] = None


class ExecuteRequest(BaseModel):
    skill_id: str = Field(..., min_length=1)
    params: dict = Field(default_factory=dict)
    session_id: str = ""
    context: Optional[dict] = None


@router.on_event("startup")
async def startup():
    _init()
    _bridge.export_all_to_mcp()


@router.get("/list")
async def list_skills(category: Optional[str] = None,
                      tags: Optional[str] = Query(None)):
    _init()
    tag_list = tags.split(",") if tags else None
    skills = _registry.list(category=category, tags=tag_list)
    return {"total": len(skills), "skills": [s.to_dict() for s in skills]}


@router.get("/search")
async def search_skills(q: str = Query(..., min_length=1)):
    _init()
    results = _registry.search(q)
    return {"query": q, "total": len(results), "skills": [s.to_dict() for s in results]}


@router.get("/get/{skill_id}")
async def get_skill(skill_id: str):
    _init()
    manifest = _registry.get(skill_id)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Skill {skill_id} does not exist")
    return manifest.to_dict()


@router.post("/register")
async def register_skill(req: RegisterRequest):
    _init()
    manifest = SkillManifest.from_dict(req.manifest)
    _registry.register(manifest)
    return {"status": "ok", "skill_id": manifest.id}


@router.delete("/unregister/{skill_id}")
async def unregister_skill(skill_id: str):
    _init()
    if _registry.unregister(skill_id):
        return {"status": "ok", "skill_id": skill_id}
    raise HTTPException(status_code=404, detail=f"Skill {skill_id} does not exist")


@router.post("/execute")
async def execute_skill(req: ExecuteRequest) -> dict:
    _init()
    request = SkillExecutionRequest(
        skill_id=req.skill_id,
        params=req.params,
        session_id=req.session_id,
        context=req.context,
    )
    result = await _registry.execute(request)
    return {
        "status": result.status,
        "output": result.output,
        "error": result.error,
        "duration_ms": result.duration_ms,
        "approval_required": result.approval_required,
    }


@router.get("/mcp-tools")
async def get_mcp_tools():
    _init()
    tools = _bridge.get_mcp_tools()
    return {"tools": tools, "total": len(tools)}


@router.get("/export/{skill_id}")
async def export_skill(skill_id: str):
    _init()
    pkg = _pkg_mgr.export_skill(skill_id)
    if not pkg:
        raise HTTPException(status_code=404, detail=f"Skill {skill_id} does not exist")
    return pkg.to_dict()


@router.post("/import")
async def import_skill(data: dict = Body(...)):
    _init()
    from .packaging import SkillPackage
    pkg = SkillPackage.from_dict(data)
    manifest = _pkg_mgr.import_from_json(pkg.to_json())
    return {"status": "ok", "skill_id": manifest.id}


@router.get("/stats")
async def skill_stats():
    _init()
    skills = _registry.list()
    categories = {}
    for s in skills:
        cat = s.category.value
        categories[cat] = categories.get(cat, 0) + 1
    return {
        "total": len(skills),
        "mcp_exported": len(_bridge._mcp_tools),
        "categories": categories,
    }
