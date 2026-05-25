#!/usr/bin/env python3
import json
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass, field, asdict
from datetime import datetime


class SkillVisibility(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    TEAM = "team"


class SkillCategory(str, Enum):
    SYSTEM = "system"
    FILE = "file"
    NETWORK = "network"
    CODE = "code"
    DATA = "data"
    AI = "ai"
    COMMUNICATION = "communication"
    AUTOMATION = "automation"
    SECURITY = "security"
    UTILITY = "utility"
    CUSTOM = "custom"


@dataclass
class SkillParameter:
    name: str
    type: str
    description: str
    required: bool = False
    default: Any = None
    enum: Optional[List[str]] = None


@dataclass
class SkillManifest:
    id: str
    name: str
    description: str
    version: str = "1.0.0"
    author: str = ""
    category: SkillCategory = SkillCategory.UTILITY
    visibility: SkillVisibility = SkillVisibility.PRIVATE
    tags: List[str] = field(default_factory=list)
    parameters: List[SkillParameter] = field(default_factory=list)
    requires: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    mcp_enabled: bool = False
    created_at: str = ""
    updated_at: str = ""

    def to_json_schema(self) -> Dict[str, Any]:
        props = {}
        required = []
        for p in self.parameters:
            pd: Dict[str, Any] = {"type": p.type, "description": p.description}
            if p.enum:
                pd["enum"] = p.enum
            if p.default is not None:
                pd["default"] = p.default
            props[p.name] = pd
            if p.required:
                required.append(p.name)
        return {
            "type": "object",
            "properties": props,
            "required": required,
        }

    def to_openai_tool(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.id,
                "description": self.description,
                "parameters": self.to_json_schema(),
            },
        }

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillManifest":
        params = [SkillParameter(**p) if isinstance(p, dict) else p for p in data.get("parameters", [])]
        data["parameters"] = params
        if "category" in data and isinstance(data["category"], str):
            data["category"] = SkillCategory(data["category"])
        if "visibility" in data and isinstance(data["visibility"], str):
            data["visibility"] = SkillVisibility(data["visibility"])
        return cls(**data)


@dataclass
class SkillExecutionRequest:
    skill_id: str
    params: Dict[str, Any] = field(default_factory=dict)
    session_id: str = ""
    context: Optional[Dict[str, Any]] = None


@dataclass
class SkillExecutionResult:
    skill_id: str
    status: str
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    approval_required: bool = False
    approval_task_id: Optional[str] = None


def make_manifest(id: str, name: str, desc: str,
                  params: Optional[List[Dict]] = None,
                  category: str = "utility",
                  tags: Optional[List[str]] = None,
                  version: str = "1.0.0") -> SkillManifest:
    now = datetime.now().isoformat()
    plist = [SkillParameter(**p) for p in (params or [])]
    return SkillManifest(
        id=id, name=name, description=desc, version=version,
        category=SkillCategory(category),
        tags=tags or [],
        parameters=plist,
        created_at=now, updated_at=now,
    )
