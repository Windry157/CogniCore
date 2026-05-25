#!/usr/bin/env python3
"""
MCP Bridge: Agent Skills ↔ MCP 协议双向适配

MCP (Model Context Protocol) 是 Anthropic 推出的Model上下文协议标准.
Agent Skills 是 Anthropic 推出的Skill开放标准.
本桥接层实现两者的双向互通.
"""
import json
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field

from .schema import SkillManifest, SkillParameter, SkillCategory, make_manifest
from .registry import SkillRegistry, get_registry

logger = logging.getLogger("MCPBridge")


@dataclass
class MCPToolDefinition:
    """MCP tool definition"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Optional[Callable] = None


class MCPBridge:
    """Agent Skills ↔ MCP 双向桥接"""

    def __init__(self, registry: Optional[SkillRegistry] = None):
        self.registry = registry or get_registry()
        self._mcp_tools: Dict[str, MCPToolDefinition] = {}

    # ----- Skill -> MCP (将 Agent Skill 暴露为 MCP Tool) -----

    def export_skill_to_mcp(self, skill_id: str) -> Optional[MCPToolDefinition]:
        """将 Agent Skill 包装为 MCP tool definition"""
        manifest = self.registry.get(skill_id)
        if not manifest:
            logger.warning(f"Skill {skill_id} does not exist, cannot export to MCP")
            return None
        mcp_tool = MCPToolDefinition(
            name=manifest.id,
            description=manifest.description,
            input_schema=manifest.to_json_schema(),
        )
        self._mcp_tools[manifest.id] = mcp_tool
        return mcp_tool

    def export_all_to_mcp(self) -> List[MCPToolDefinition]:
        tools = []
        for sid in list(self.registry._skills.keys()):
            tool = self.export_skill_to_mcp(sid)
            if tool:
                tools.append(tool)
        return tools

    def get_mcp_tools(self) -> List[Dict[str, Any]]:
        """生成 MCP 协议兼容的Tool列表"""
        return [
            {
                "name": t.name,
                "description": t.description,
                "inputSchema": t.input_schema,
            }
            for t in self._mcp_tools.values()
        ]

    # ----- MCP -> Skill (将 MCP ToolRegister为 Agent Skill) -----

    def import_mcp_tool(self, tool_def: MCPToolDefinition,
                        category: str = "custom",
                        tags: Optional[List[str]] = None) -> SkillManifest:
        """将 MCP ToolRegister为 Agent Skill"""
        params = []
        if "properties" in tool_def.input_schema:
            for pname, pinfo in tool_def.input_schema["properties"].items():
                params.append(SkillParameter(
                    name=pname,
                    type=pinfo.get("type", "string"),
                    description=pinfo.get("description", ""),
                    required=pname in tool_def.input_schema.get("required", []),
                ))
        manifest = make_manifest(
            id=tool_def.name,
            name=tool_def.name,
            desc=tool_def.description,
            params=[p.__dict__ for p in params],
            category=category,
            tags=tags or ["mcp"],
        )
        manifest.mcp_enabled = True
        self.registry.register(manifest, handler=tool_def.handler)
        self._mcp_tools[tool_def.name] = tool_def
        logger.info(f"Importing skill from MCP: {tool_def.name}")
        return manifest

    # ----- MCP 协议消息Processing -----

    def handle_mcp_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        method = request.get("method", "")
        params = request.get("params", {})

        if method == "tools/list":
            return {"tools": self.get_mcp_tools()}

        if method == "tools/call":
            name = params.get("name", "")
            args = params.get("arguments", {})
            if name not in self._mcp_tools:
                return {"isError": True, "content": [{"type": "text", "text": f"未知Tool: {name}"}]}
            tool = self._mcp_tools[name]
            if tool.handler:
                try:
                    result = tool.handler(args)
                    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}
                except Exception as e:
                    return {"isError": True, "content": [{"type": "text", "text": str(e)}]}
            return {"content": [{"type": "text", "text": f"Tool {name} 无Processor"}]}

        if method == "resources/list":
            return {"resources": []}

        return {"isError": True, "content": [{"type": "text", "text": f"未知方法: {method}"}]}


_bridge: Optional[MCPBridge] = None


def get_bridge() -> MCPBridge:
    global _bridge
    if _bridge is None:
        _bridge = MCPBridge()
    return _bridge
